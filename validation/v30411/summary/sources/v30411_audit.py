"""Audit the same real engine commands, without making decisions in the observer."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack, contextmanager
from functools import partial
import json
from pathlib import Path
from unittest.mock import patch

from common import to_csv, to_json
from remake import command_books, faction_economy, grain_market, grain_units, logistics, strategic_granary
from remake import transport_capacity, transport_coordination as coordination
from remake.campaign import digest
from v3021_checkpoints import campaign, configure
from v302_audit import Audit
from v30411_replays import checked_inputs, enable, fixed_with_trace
import v3041_replays as legacy


class TargetPostings:
    def __init__(self, targets):
        self.targets = {row['target'] for row in targets}
        self.rows = defaultdict(list)

    def writerow(self, row):
        if row['city'] in self.targets and row['resource'] in ('grain', 'ownership'):
            self.rows[row['city']].append(row)


def fixed_consumption(targets, postings, meals):
    """Report observed meals and a conservative lower bound on local buy usage."""
    for target in targets:
        owner, city = target['owner'], target['target']
        due = int(target['deadline_turn'])
        observations = meals.get((owner, city), {})
        meal = observations.get(due)
        local_stock = bought = forced_use = 0
        for event in postings.rows[city]:
            if event['turn'] >= due:
                break
            if event['resource'] == 'ownership' or event['owner'] != owner:
                local_stock = 0
                continue
            delta = event['delta']
            if delta is None:
                continue
            if delta > 0 and event['site'] == 'facilities._settle_grain_trade':
                local_stock += delta
                bought += delta
            elif delta < 0:
                if event['category'] == 'city_consumption':
                    use = max(0, -delta - max(0, event['balance_before'] - local_stock))
                    forced_use += use
                    local_stock -= use
                else:
                    # Other expenditures may have spent the purchased grain first.
                    local_stock = max(0, local_stock + delta)
        yield dict(group=target['group'], checkpoint=target['checkpoint_sha256'],
            owner=owner, city=city, deadline=due, first_gap=target['first_uncovered_grain'],
            due_meal_observed=meal is not None, required=meal['required'] if meal else None,
            paid=meal['paid'] if meal else None, actual_missing=meal['missing'] if meal else None,
            physical_receipts=target['l5_actual_reception'], local_grain_bought=bought,
            local_grain_consumed_minimum=forced_use,
            rations_through_deadline=[row for when,row in sorted(observations.items()) if when<=due])


def safety_case(task, *, output):
    postings = TargetPostings(task[2])
    audit = Audit(postings)
    capacity, dispatches, deliveries = [], [], []
    meals = defaultdict(dict)
    market_checks = Counter()
    command = legacy.winter_replay.HeadlessCampaign.command
    market_transfer, restock = grain_market.transfer, grain_market.restock
    spend_book = command_books.spend
    capacity_observer, coord_observer = transport_capacity.observing, coordination.observing
    summary = Counter()
    market_postings = Counter()
    books, market_buys = [], []

    def spend(state, city, kind):
        before = command_books.remaining(state, city.owner)
        cost = spend_book(state, city, kind)
        if cost:
            row = state.extension['command_books']['factions'][city.owner]
            books.append(dict(turn=state.turn, owner=city.owner, city=city.id, kind=kind,
                serial=len(row['orders']), spent=cost, actual=before-command_books.remaining(state, city.owner)))
        return cost

    def market_totals(state):
        return {key: row['stock'] for key, row in state.extension.get(grain_market.FIELD, {}).items()}

    def transfer(state, city, direction, grain, **details):
        before = grain_market.row(state, city)['stock']
        result = market_transfer(state, city, direction, grain, **details)
        after = grain_market.row(state, city)['stock']
        market_checks['transactions'] += 1
        expected = -grain if direction == 'buy' else grain
        market_checks['transaction_errors'] += int(after-before != expected)
        market_postings[city] += after-before
        if direction == 'buy':
            market_buys.append(dict(turn=state.turn, owner=state.cities[city].owner, city=city,
                                    grain=grain, channel=details.get('channel')))
        return result

    def replenish(game, state, regular_incomes=None):
        before = market_totals(state)
        result = restock(game, state, regular_incomes)
        after = market_totals(state)
        for key, value in after.items():
            market_postings[key] += value-before.get(key, 0)
        return result

    def observed_command(game, action, payload, rev):
        if action != 'observe_turn':
            return command(game, action, payload, rev)
        before = market_totals(game.state)
        market_postings.clear()
        with audit.command(game, action):
            result = command(game, action, payload, rev)
        after = market_totals(game.state)
        for key in before.keys() | after.keys() | market_postings.keys():
            market_checks['account_errors'] += int(after.get(key, 0) != before.get(key, 0)+market_postings[key])
        market_checks['city_command_accounts'] += len(after)
        return result

    @contextmanager
    def observe_capacity(record):
        def track(event, row):
            record(event, row)
            if event in ('departure', 'delivery', 'terminal'):
                capacity.append(dict(event=event, **row))
        with capacity_observer(track):
            yield

    @contextmanager
    def observe_coord(record, *, shadow=False):
        def track(event, row):
            record(event, row)
            if event == 'dispatch':
                dispatches.append(row)
            if event == 'receipt':
                deliveries.append(row)
        with coord_observer(track, shadow=shadow):
            yield

    def record_meal(row):
        settlement = row['turn'] + 1
        meals[row['owner'], row['city']][settlement] = dict(row, settlement_turn=settlement)

    with (audit.install(), patch.object(grain_market, 'transfer', transfer),
          patch.object(grain_market, 'restock', replenish),
          patch.object(command_books, 'spend', spend),
          patch.object(legacy.winter_replay.HeadlessCampaign, 'command', observed_command),
          patch.object(transport_capacity, 'observing', observe_capacity),
          patch.object(coordination, 'observing', observe_coord)):
        targets, _, result = fixed_with_trace(task, output=output,
            record_meal=record_meal, include_deadline_settlement=True)

    departures = [row for row in capacity if row['event']=='departure']
    limit = 2 if task[1] in ('V0','V1','V2') else 1
    summary['transport_position_overruns'] = sum(row['active'] > limit for row in departures)
    summary['repeated_origin_dispatches'] = sum(row['dispatch_count'] > 1 for row in departures)
    escrows = Counter((row['owner'], row['turn'], ident) for row in departures for ident in row['officers'])
    summary['simultaneous_escort_overlaps'] = sum(n-1 for n in escrows.values())
    summary['dispatch_book_deviation'] = sum(row['books'] != row['books_used'] for row in dispatches)
    linked = Counter(row['convoy'] for row in deliveries if row['convoy'] is not None)
    summary['duplicate_receipts'] = sum(n-1 for n in linked.values())
    summary['invalid_receipt_credits'] = sum(not 0<=row['timely']<=row['credited']<=row['received'] for row in deliveries)
    book_ids = {(row['turn'], row['owner'], row['serial']) for row in books}
    summary['duplicate_books'] = len(books)-len(book_ids)
    summary['book_posting_errors'] = sum(row['spent'] != row['actual'] for row in books)
    buying = Counter((r['turn'],r['owner'],r['city']) for r in market_buys)
    routes = {(r['turn'],r['owner'],r['source']) for r in departures
              if r['cargo']['grain'] or r['purpose'] in ('army', 'relief', 'convoy_relief')}
    use = Counter()
    for row in books:
        key = row['turn'], row['owner'], row['city']
        if row['kind']=='trade_grain' and buying[key]:
            use['market_books'] += row['actual']
            buying[key] -= 1
        elif row['kind']=='dispatch_transport' and key in routes:
            use['transport_books'] += row['actual']
        elif row['kind'] in ('resupply_march','requisition_grain'):
            use['direct_resupply_books'] += row['actual']
    effective = dict(group=task[1], checkpoint=result['fixture'], **dict(use),
        city_market_grain=sum(row['grain'] for row in market_buys
                              if not (row['channel'] or '').startswith('regional_')),
        regional_purchased_grain=sum(row['grain'] for row in market_buys
                                     if (row['channel'] or '').startswith('regional_')),
        actual_net_delivered=sum(row['cargo']['grain'] for row in capacity if row['event']=='delivery'),
        fixed_first_gap_covered=sum(min(int(row['first_uncovered_grain']),row['l5_actual_reception'])
                                    for row in targets if row['l5_actual_reception'] is not None))
    prior, reversals = defaultdict(list), []
    for row in departures:
        if row['cargo']['grain'] <= 0:
            continue
        key = row['owner'], row['source'], row['target']
        for earlier in prior[key[0], key[2], key[1]]:
            if row['turn']-earlier['turn'] <= 3:
                reversals.append(dict(group=task[1], opening=result['fixture'], owner=row['owner'],
                    source=row['source'], target=row['target'], first=earlier['id'], second=row['id'],
                    first_turn=earlier['turn'], return_direction_turn=row['turn'],
                    first_load=earlier['cargo']['grain'], reverse_load=row['cargo']['grain'],
                    first_purpose=earlier['purpose'], reverse_purpose=row['purpose']))
        prior[key].append(row)
    return dict(group=task[1], fixture=result['fixture'], sha256=result['fixture_sha256'],
                grain_account=audit.metrics(), market=dict(market_checks), safety=dict(summary),
                reversals=reversals, departures=departures, books=books, effective=effective,
                checks=result['checks'],
                consumption=list(fixed_consumption(targets, postings, meals)))


def fixed_tasks(root, index, groups):
    candidates = legacy.capacity_replay.read_csv(root/'reference/spatial-grain-capability-funnel.csv')
    origins = legacy.capacity_replay.read_csv(root/'reference/source-task-blockers.csv')
    counts = defaultdict(list)
    for row in origins:
        if int(row['surplus'])>0 and int(row['personally_qualified_available'])>0:
            for convoy, phase, received in zip(*(json.loads(row[key]) for key in
                    ('convoy_ids','phases','cargo_delivered')), strict=True):
                if phase=='returning' and received:
                    counts[row['checkpoint_sha256']].append(dict(row, original_convoy=convoy))
    return [(root/item['file'], group, [row for row in candidates if row['checkpoint_sha256']==item['sha256']],
             counts[item['sha256']]) for item in index if item['group']=='fixed' for group in groups]


def opening(stack, item, path, group):
    fixture = legacy.capacity_replay.checkpoint(path)
    configure(stack, fixture['strategy'], fixture['weather'])
    game = campaign(item['scenario'])
    game.load_save(fixture['save'], 0)
    enable(stack, game, group, None)
    return game


def reserves(root, index):
    for item in index:
        if item['group'] != 'fixed':
            continue
        with ExitStack() as stack:
            game = opening(stack, item, root/item['file'], 'U6')
            state = game.state
            with grain_units.using(state):
                for owner in sorted({city.owner for city in state.cities.values()}-{'neutral'}):
                    plan = faction_economy.plan(game, state, owner, granary=strategic_granary.enabled(state),
                                               coordinated=True)
                    for key, budget in plan.budgets.items():
                        city = state.cities[key]
                        policy = logistics._pool(state)['cities'][key]['policy']
                        components = plan.commitments.breakdown(key)
                        staged = budget.get('staging_grain', 0)
                        assert budget['reserved_grain'] == sum(components.values())
                        hard_floor = max(policy['reserve_grain'], budget['minimum_export_floor'])
                        original = max(hard_floor, budget['safety_reserve'])
                        candidate = original if budget['threatened'] or budget['front'] else hard_floor
                        yield dict(checkpoint=item['sha256'], city=key, owner=owner, stock=city.grain,
                            existing_staging=staged, approved_military=components.get('military', 0)-staged,
                            strategic_transport=components.get('granary', 0), relay=components.get('relay',0),
                            other_commitments=sum(components.values())-components.get('military',0)
                                             -components.get('granary',0)-components.get('relay',0),
                            total_hard_commitments=budget['reserved_grain'],
                            tagged_reserve=strategic_granary.reserve_grain(state,city) if strategic_granary.enabled(state) else 0,
                            policy_floor=policy['reserve_grain'], forecast_floor=budget['minimum_export_floor'],
                            next_installment=budget['next_installment'], safety_reserve=budget['safety_reserve'],
                            rear=not budget['front'] and not budget['threatened'],
                            previous_exportable=max(0,city.grain-budget['reserved_grain']-original),
                            current_exportable=max(0,city.grain-budget['reserved_grain']-candidate))


def compare(task):
    root, item = task
    path = root/item['file']
    samples = []
    for group in ('U6-full','U6'):
        with ExitStack() as stack:
            events = []
            game = opening(stack, item, path, group)
            stack.enter_context(coordination.observing(lambda event,row: events.append((event,row))
                if event in ('demand','candidate','dispatch','dispatch_failed','receipt') else None))
            snapshots = []
            for _ in range(3):
                game.command('observe_turn', {}, game.revision)
                domain = game.to_dict()
                domain['extension'][coordination.POOL]['features'].pop('incremental')
                snapshots.append((digest(domain), domain['rng']))
            samples.append((snapshots, events))
    return dict(fixture=item['label'], sha256=item['sha256'], compared_turns=len(samples[0][0]),
        domains_equal=samples[0][0]==samples[1][0], decisions_equal=samples[0][1]==samples[1][1],
        decision_events=len(samples[0][1]), result=samples[1][0])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--group',nargs='+',choices=('U0','U1','U6','V0','V1','V2'),default=('U6','V2'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    index=checked_inputs(args.inputs)
    to_csv(args.output/'donor-reserve-component-audit.csv',reserves(args.inputs,index))
    with ProcessPoolExecutor(args.workers) as pool:
        audits=list(pool.map(partial(safety_case,output=args.output),fixed_tasks(args.inputs,index,args.group)))
        checks=list(pool.map(compare,((args.inputs,item) for item in index if item['group']=='fixed')))
    to_json(args.output/'resource-safety.json',audits)
    fields = ('group','checkpoint','market_books','transport_books','direct_resupply_books','city_market_grain',
              'regional_purchased_grain','actual_net_delivered','fixed_first_gap_covered')
    to_csv(args.output/'effective-demand-per-command-book.csv', (
        {field:row['effective'].get(field,0) for field in fields} for row in audits))
    to_csv(args.output/'fixed-first-deadline-consumption.csv',
           (item for row in audits for item in row['consumption']))
    to_csv(args.output/'incremental-plan-equivalence.csv',checks)
    if any(row['reversals'] for row in audits):
        to_csv(args.output/'repeated-grain-transfer-audit.csv',(item for row in audits for item in row['reversals']))
    verified=all(row['grain_account']['city_resource_mismatches']==0 and
        not any(row['safety'].values()) and
        not row['market'].get('transaction_errors') and not row['market'].get('account_errors') for row in audits)
    return int(not (verified and all(r['domains_equal'] and r['decisions_equal'] for r in checks)))


if __name__=='__main__':
    raise SystemExit(main())
