"""Read-only potential by layer at captured public campaign states."""
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import ExitStack
import gzip
from hashlib import sha256
import json
from pathlib import Path

from common import to_csv
from remake import command_books, faction_economy, grain_units, granary_demand, granary_planning
from remake import logistics, strategic_granary as reserve
from v3021_checkpoints import campaign, configure


def view(game, checkpoint, file_hash):
    state = game.state
    capacities, custody, blocked_sources = [], [], []
    owners = sorted({city.owner for city in state.cities.values()}-{'neutral'})
    for owner in owners:
        plan = granary_planning._plan(game,state,owner)
        for key in plan.budgets:
            city = state.cities[key]
            row = reserve.protection(state,city,book=plan.commitments)
            label = reserve.reserve_grain(state,city)
            custody.append(dict(scenario=checkpoint['scenario'],strategy=checkpoint['strategy'],turn=state.turn,
                checkpoint_sha256=file_hash, owner=owner,city=key,stock=city.grain,recorded_reserve=label,
                overlapping_tag=max(0,label-row['strategic']), **row))
        targets = plan.shortages(state,within=faction_economy.HORIZON)
        if not targets:
            continue
        network = granary_planning.Network(game,state,owner,plan,automatic=True)
        choices = network.collect(targets)
        convoys = defaultdict(list)
        for row in logistics._pool(state)['convoys']:
            if row['owner']==owner:
                convoys[row['source']].append(row)
        for key,row in plan.budgets.items():
            city = state.cities[key]
            info = logistics._pool(state)['cities'][key]
            policy = info['policy']
            tasks = convoys[key]
            if tasks or info['last_dispatch_turn']==state.turn:
                minimum = max(policy['reserve_grain'],row['next_installment'],plan.cities[key].reserve,
                    network.profiles[key]['target'],reserve.reserve_grain(state,city),
                    row['safety_reserve'] if row['threatened'] else 0)
                _, escorts, exclusions = network._eligible(city,policy)
                blocked_sources.append(dict(scenario=checkpoint['scenario'],strategy=checkpoint['strategy'],
                    turn=state.turn,checkpoint_sha256=file_hash,owner=owner,source=key,
                    convoy_ids=[task['id'] for task in tasks], phases=[task['status'] for task in tasks],
                    cargo_delivered=[task['delivery_done'] for task in tasks],
                    dispatched_this_turn=info['last_dispatch_turn']==state.turn,stock=city.grain,
                    surplus=max(0,city.grain-row['reserved_grain']-minimum),
                    personally_qualified_available=len(escorts),exclusions=exclusions))
        for target in targets:
            current = state.cities[target]
            demand = granary_demand.for_city(game,state,plan,target)
            due = demand.first
            if due is None:
                continue
            first_bill = dict(demand.remaining)[due]
            horizon_need = demand.after(0)[1]
            books = command_books.remaining(state,owner)//command_books.cost('dispatch_transport')
            surplus = {}
            by_policy = defaultdict(list)
            for key,row in plan.budgets.items():
                if key == target:
                    continue
                city = state.cities[key]
                policy = logistics._pool(state)['cities'][key]['policy']
                minimum = max(policy['reserve_grain'],row['next_installment'],plan.cities[key].reserve,
                    network.profiles[key]['target'],reserve.reserve_grain(state,city),
                    row['safety_reserve'] if row['threatened'] else 0)
                grain = max(0,city.grain-row['reserved_grain']-minimum)
                if grain and policy['target_city'] in (None,target):
                    signature = policy['allow_sea'],policy['allow_special']
                    by_policy[signature].append((key,policy))
                    surplus[key] = grain
            legal = set()
            for entries in by_policy.values():
                requests = [(a,b) for key,_ in entries for a,b in ((key,target),(target,key))]
                quotes = logistics._supply_routes(game,state,owner,requests,entries[0][1])
                for key,policy in entries:
                    source = state.cities[key]
                    if (logistics._safe_options(game,state,source,current,policy,quotes=quotes)
                            and logistics._safe_options(game,state,current,source,policy,quotes=quotes)):
                        legal.add(key)
            gross_by_source, timely_net = defaultdict(int), defaultdict(int)
            for route in choices.get(target,()):
                source = route['source']
                gross_by_source[source] = max(gross_by_source[source],route['limit'])
                offer = network.shipment(route,horizon_need,state.turn+due)
                if (offer and offer['timely'] and offer['net']>=reserve.RULES['minimum_load']
                        and offer['rations']*100<=offer['net']*reserve.RULES['maximum_ration_percent']):
                    timely_net[source] = max(timely_net[source],min(offer['net'],first_bill))
            capacities.append(dict(scenario=checkpoint['scenario'],strategy=checkpoint['strategy'],turn=state.turn,
                checkpoint_sha256=file_hash,owner=owner,target=target,first_uncovered_in=due,
                first_uncovered_grain=first_bill,
                l0_faction_stock=sum(state.cities[key].grain for key in plan.budgets),
                l0_other_city_stock=sum(state.cities[key].grain for key in plan.budgets if key!=target),
                l1_donor_surplus=sum(surplus.values()),l2_legal_outbound_surplus=sum(surplus[key] for key in legal),
                l3_qualified_gross=sum(sorted(gross_by_source.values(),reverse=True)[:books]),
                l3_distinct_sources=len(gross_by_source),
                l4_estimated_net_upper_bound=min(first_bill,
                    sum(sorted(timely_net.values(),reverse=True)[:books])),
                l4_distinct_sources=len(timely_net),available_transport_commands=books,
                candidate_rejection_marks=dict(network.rejected[target])))
    return capacities,custody,blocked_sources


def replay_receipts(checkpoint, capacities):
    if not capacities:
        return
    start = checkpoint['turn']
    deadline = {(row['owner'],row['target']): start+row['first_uncovered_in'] for row in capacities}
    last_observation = max(deadline.values())-1
    receipts = defaultdict(list)

    def observe(event, row):
        if event != 'order_delivered' or row['priority'] != 'proactive' or row['dispatch_turn'] < start:
            return
        key = row['owner'],row['target']
        if key in deadline and row['delivered_turn'] < deadline[key]:
            receipts[key].append({'order':row['id'],'convoy':row['convoy_id'],'source':row['source'],
                                  'turn':row['delivered_turn'],'grain':row['delivered_grain']})

    # Advance a fresh copy of the checkpoint. The forecasting pass stays read-only.
    game = campaign(checkpoint['scenario'])
    with ExitStack() as stack:
        configure(stack,checkpoint['strategy'],checkpoint['weather'])
        stack.enter_context(reserve.observing(observe))
        game.load_save(checkpoint['save'],0)
        while game.state.turn < last_observation:
            before=game.state.turn
            game.command('observe_turn',{},game.revision)
            if game.state.turn == before:
                break
    for row in capacities:
        key = row['owner'],row['target']
        complete = game.state.turn >= deadline[key]-1
        row.update(l5_actual_reception=sum(item['grain'] for item in receipts[key]) if complete else None,
                   l5_replay_end_turn=game.state.turn,l5_actual_receipts=receipts[key])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('checkpoints',type=Path,nargs='+')
    args=parser.parse_args()
    caps, reservations, blockades = [], [], []
    for fixture in args.checkpoints:
        with gzip.open(fixture,'rt',encoding='utf-8') as stream:
            checkpoint = json.load(stream)
        game = campaign(checkpoint['scenario'])
        game.load_save(checkpoint['save'],0)
        assert game.state.extension[reserve.FIELD] == reserve.VERSION
        before = game.export_save()['checksum']
        with grain_units.using(game.state):
            c,r,blocks = view(game,checkpoint,sha256(fixture.read_bytes()).hexdigest())
        assert game.export_save()['checksum'] == before
        replay_receipts(checkpoint,c)
        caps += c
        reservations += r
        blockades += blocks
    if caps:
        to_csv(args.output/'spatial-grain-capability-funnel.csv',caps)
    to_csv(args.output/'reserve-overlap-audit.csv',reservations)
    if blockades:
        to_csv(args.output/'source-task-blockers.csv',blockades)


if __name__=='__main__':
    main()
