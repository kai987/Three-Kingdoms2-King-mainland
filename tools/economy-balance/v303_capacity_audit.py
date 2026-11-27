"""Audit real route stages and replay the fixed transport demand checkpoints."""
from argparse import ArgumentParser
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from copy import deepcopy
import csv
import gzip
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic, process_time

from common import ROOT, catalog_paths, git, open_game, Catalog, to_csv, to_json
from remake import command_books, grain_units, granary_planning, logistics, logistics_rules
from remake import strategic_granary, transport_capacity, winter_travel
from remake.campaign import canonical
from v3021_capacity import view
from v3021_checkpoints import campaign, configure
from v303_experiments import options


def read_csv(path):
    with path.open(encoding='utf-8',newline='') as handle:
        return list(csv.DictReader(handle))


def checkpoint(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def replay_context(stack, fixture, group):
    configure(stack,fixture['strategy'],fixture['weather'])
    game=campaign(fixture['scenario'])
    game.load_save(fixture['save'],0)
    if options(group) is not None:
        stack.enter_context(transport_capacity.fixed_replay(game.state,options(group)))
    return game


def census(out):
    rows=[]
    for location in catalog_paths():
        game=open_game(Catalog(location),2026)
        state=game.state
        operating=deepcopy(state)
        transport_capacity.initialize(operating,303,options('C4'))
        with grain_units.using(operating):
            for owner in sorted({city.owner for city in operating.cities.values()}-{'neutral'}):
                logistics.prepare_ai(game,operating,owner)
        rules=game.catalog.data['travel_rules']
        routes,_,prepare=game._python_route_graph(state,scoped=({},{}))
        groups=defaultdict(set)
        by_route=[]
        for raw in routes:
            for a,b in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                if a not in state.cities or b not in state.cities:
                    continue
                leg,days=prepare(raw,a,b)
                if leg is None:
                    continue
                source,target=state.cities[a],state.cities[b]
                if source.owner==target.owner and source.owner in game.catalog.factions:
                    groups[source.owner].add((b,a))
                by_route.append((source,target,leg,days))
        allowed={'allow_sea':True,'allow_special':True}
        paired={owner:logistics._supply_routes(game,state,owner,sorted(pairs),allowed)
                for owner,pairs in groups.items()}
        for source,target,leg,days in by_route:
            a,b,owner=source.id,target.id,source.owner
            policy=logistics._pool(state)['cities'][a]['policy']
            quote=game._quote([a,b],[leg])
            profile=transport_capacity.physical(game,state,quote)
            cap=profile['physical_capacity']
            same_faction=owner==target.owner and owner in paired
            permit=logistics._permitted_route(game,policy,leg)
            source_routes=paired.get(owner,{})
            back=next((choice for choice in (source_routes.get(f'{b}:{a}:land'),
                      source_routes.get(f'{b}:{a}:fastest')) if choice is not None
                      and all(logistics._permitted_route(game,policy,item) for item in choice['routes'])),None)
            roster=logistics._eligible(game,state,source,automatic=True) if same_faction else []
            roster=[ident for ident in roster if ident!=state.extension['leaders'].get(owner)]
            escort=min(roster,key=lambda i:(state.officers[i].troops,logistics._key(i)),default=None)
            if same_faction and logistics._present_count(game,state,source)<=policy['reserve_officers']:
                escort=None
            free=max(0,transport_capacity.current_grain(state,source)-policy['reserve_grain']) if same_faction else None
            rations=None
            limit=None
            keeps_stock=all(getattr(source,key)>=policy['reserve_'+key] for key in ('gold','reserves','grain'))
            if back and permit and escort is not None and keeps_stock:
                rations=logistics.escort_rations(game,state,[escort],quote,back)
                if command_books.can_spend(state,owner,'dispatch_transport'):
                    limit=transport_capacity.effective_cargo(cap,rations,policy['max_grain'],free,
                                                               logistics.LIMIT-target.grain)
            ai_source=operating.cities[a]
            prepared=logistics._pool(operating)['cities'][a]['policy']
            ai_policy=transport_capacity.ai_policy(operating,owner,prepared,automatic=True)
            ai_return=next((choice for choice in (source_routes.get(f'{b}:{a}:land'),
                            source_routes.get(f'{b}:{a}:fastest')) if choice is not None
                            and all(logistics._permitted_route(game,ai_policy,item) for item in choice['routes'])),None)
            ai_roster=logistics._eligible(game,operating,ai_source,automatic=True) if same_faction else []
            ai_escort=min(ai_roster,key=lambda i:(operating.officers[i].troops,logistics._key(i)),default=None)
            ai_policy_max=transport_capacity.policy_limit(operating,owner,ai_policy,profile,automatic=True)
            eligible=(same_faction and ai_policy['enabled'] and logistics._permitted_route(game,ai_policy,leg)
                      and not logistics._dangerous(quote,ai_policy) and ai_return is not None and ai_escort is not None
                      and not logistics._dangerous(ai_return,ai_policy) and keeps_stock
                      and logistics._present_count(game,operating,ai_source)>ai_policy['reserve_officers']
                      and command_books.can_spend(operating,owner,'dispatch_transport'))
            ai_rations=None
            ai_cargo=None
            if eligible:
                ai_rations=logistics.escort_rations(game,operating,[ai_escort],quote,ai_return)
                ai_cargo=transport_capacity.effective_cargo(cap,ai_rations,ai_policy_max,free,logistics.LIMIT-target.grain)
            rows.append(dict(scenario=location.stem,map_route=leg['id'],source=a,target=b,
                source_owner=owner,target_owner=target.owner,catalog_mode=leg['mode'],mode=profile['mode'],
                physical_stages=[{'kind':kind,'ticks':ticks,'location':place}
                    for kind,ticks,place in logistics_rules.leg_parts(leg,rules,locations=True)],
                physical_capacity=cap,old_policy_max=policy['max_grain'],
                physical_capacity_vs_policy=None if cap is None else cap-policy['max_grain'],
                operating_v302_policy_max=prepared['max_grain'],candidate_ai_policy_max=ai_policy_max,
                candidate_ai_potential=ai_cargo,candidate_ai_rations=ai_rations,
                candidate_ai_expected_net=None if ai_cargo is None else logistics.projected_grain(
                    game,quote,ai_cargo,state=operating),
                candidate_ai_legal_return=bool(ai_return),
                bottleneck=profile['bottleneck'],days=days,outbound_policy_permits=permit,same_faction=same_faction,
                origin_grain_available=free,candidate_escort=escort,independent_rations=rations,
                potential_cargo=limit,expected_net=None if limit is None else logistics.projected_grain(
                    game,quote,limit,state=state),has_legal_return=bool(back),
                return_path=None if back is None else back['path'],
                return_days=None if back is None else winter_travel.quote_days(game,state,back)))
        print(f"{location.stem} {len(by_route)} directional links",flush=True)
    to_csv(out/'transport-capacity-by-route.csv',rows)
    to_csv(out/'mixed-route-bottlenecks.csv',[row for row in rows if row['mode']=='mixed'])


def returning_offers(game,fixed,tracked):
    state=game.state
    sources=defaultdict(list)
    for row in tracked:
        sources[row['owner']].append(row)
    targets=defaultdict(dict)
    for row in fixed:
        targets[row['owner']][row['target']]=row
    result=[]
    for owner,records in sorted(sources.items()):
        plan=granary_planning._plan(game,state,owner)
        network=granary_planning.Network(game,state,owner,plan,automatic=True)
        upcoming=targets[owner]
        unique_sources=sorted({row['source'] for row in records})
        offers=network.collect(list(upcoming),sources=unique_sources)
        by_source=defaultdict(list)
        for target in sorted(offers):
            need=upcoming[target]
            past=state.turn+int(need['first_uncovered_in'])
            for route in offers[target]:
                offered=network.shipment(route,int(need['first_uncovered_grain']),past)
                if (offered and offered['timely'] and offered['net']>=strategic_granary.RULES['minimum_load']
                        and offered['rations']*100<=offered['net']*strategic_granary.RULES['maximum_ration_percent']):
                    by_source[route['source']].append({key:offered[key] for key in
                        ('target','mode','load','net','rations','escort','arrival_turn','deadline','path',
                         'free','limit','return_days')})
        for row in records:
            key=row['source']
            ledger=logistics._pool(state)['cities'][key]
            city=state.cities[key]
            donor,donor_block=network._donor(key,0)
            _,available,excluded=network._eligible(city,ledger['policy'])
            result.append(dict(owner=owner,source=key,original_convoy=row['original_convoy'],
                initial_stock=city.grain,original_surplus=int(row['surplus']),
                original_available=int(row['personally_qualified_available']),
                active=transport_capacity.active_count(state,city),
                dispatch_remaining=transport_capacity.dispatch_limit(state)-transport_capacity.dispatch_count(state,key),
                eligible=list(available),excluded=excluded,donor_qualified=donor is not None,
                blocker=donor_block,available_commands=command_books.remaining(state,owner),
                timely_quotes=by_source[key]))
    return result


def fixed_replay(spec, *, include_deadline_settlement=False):
    path,group,fixed,tracked=spec
    fixture=checkpoint(path)
    check_hash=sha256(path.read_bytes()).hexdigest()
    start=fixture['turn']
    deadline={(row['owner'],row['target']):start+int(row['first_uncovered_in']) for row in fixed}
    stop=max(deadline.values())-int(not include_deadline_settlement)
    delivered,departures=defaultdict(list),{}
    replay=[]

    def observe(event,row):
        if event=='departure':
            departures[row['id']]=row
        if event=='delivery' and row['id'] in departures:
            goal=(row['owner'],row['target'])
            purpose=departures[row['id']]['purpose']
            # AI demand is evaluated before the following turn. Deliveries on
            # the deadline turn are late, matching the archived definition.
            if goal in deadline and row['turn']<deadline[goal] and purpose in ('ordinary','strategic','regional'):
                delivered[goal].append(dict(row,departed=departures[row['id']]['turn'],
                    mode=departures[row['id']]['profile']['mode'],purpose=purpose))

    with ExitStack() as stack:
        game=replay_context(stack,fixture,group)
        before=sha256(canonical(game.to_dict()).encode()).hexdigest()
        with grain_units.using(game.state):
            calculated,_,_=view(game,fixture,check_hash)
            source_options=returning_offers(game,fixed,tracked)
        after=sha256(canonical(game.to_dict()).encode()).hexdigest()
        if before!=after:
            raise ValueError('Fixed state forecast changed the domain state')
        by_target={(row['owner'],row['target']):row for row in calculated}
        if set(by_target)!=set(deadline):
            raise ValueError(f'Historical fixed target set differs for {path.name} {group}')
        stack.enter_context(transport_capacity.observing(observe))
        while game.state.turn<stop:
            was=game.state.turn
            wall,cpu=monotonic(),process_time()
            game.command('observe_turn',{},game.revision)
            wall,cpu=monotonic()-wall,process_time()-cpu
            after=game.to_dict()
            replay.append(dict(turn=game.state.turn,wall=wall,cpu=cpu,rng=after['rng'],
                sha256=sha256(canonical(after).encode()).hexdigest()))
            if game.state.turn==was:
                break
        for row in calculated:
            key=row['owner'],row['target']
            receipts=delivered[key]
            finished=game.state.turn>=deadline[key]-1
            row.update(group=group,seed=fixture['seed'],weather=fixture['weather'],deadline_turn=deadline[key],
                       l5_replay_end_turn=game.state.turn,
                       l5_actual_reception=sum(item['cargo']['grain'] for item in receipts) if finished else None,
                       l5_strategic_reception=sum(item['cargo']['grain'] for item in receipts
                           if item['purpose']=='strategic') if finished else None,l5_actual_receipts=receipts)
        source_receipts=defaultdict(list)
        target_due={key:int(row['first_uncovered_grain']) for key,row in
                    (((row['owner'],row['target']),row) for row in fixed)}
        for key,rows in delivered.items():
            for row in rows:
                source_receipts[row['owner'],row['source']].append(dict(convoy=row['id'],target=row['target'],
                    purpose=row['purpose'],grain=row['cargo']['grain'],turn=row['turn'],demand=target_due[key]))
        for row in source_options:
            key=row['owner'],row['source']
            row.update(group=group,scenario=fixture['scenario'],strategy=fixture['strategy'],
                       start_turn=start,checkpoint_sha256=check_hash,replay_end_turn=game.state.turn,
                       actual_shipments=source_receipts[key])
    print(f'{path.name} {group}: {len(calculated)} targets, {len(replay)} turns',flush=True)
    return calculated,source_options,dict(group=group,fixture=path.name,scenario=fixture['scenario'],
        turn=start,strategy=fixture['strategy'],seed=fixture['seed'],weather=fixture['weather'],
        fixture_sha256=check_hash,forecast_state_sha256=before,checks=replay)


def fixed(args, *, replay=fixed_replay):
    origins=read_csv(args.prior/'source-task-blockers.csv')
    cases=read_csv(args.prior/'spatial-grain-capability-funnel.csv')
    samples=[]
    for row in origins:
        if int(row['surplus'])<=0 or int(row['personally_qualified_available'])<=0:
            continue
        for convoy,phase,received in zip(*(json.loads(row[key]) for key in
                ('convoy_ids','phases','cargo_delivered')),strict=True):
            if phase=='returning' and received:
                samples.append(dict(row,original_convoy=convoy))
    if len(cases)!=89 or len(samples)!=23:
        raise ValueError(f'Expected 89 fixed targets and 23 returning shipments, got {len(cases)}, {len(samples)}')
    tasks=[]
    selected=set()
    for path in args.checkpoints:
        identity=sha256(path.read_bytes()).hexdigest()
        rows=[row for row in cases if row['checkpoint_sha256']==identity]
        observed=[row for row in samples if row['checkpoint_sha256']==identity]
        if not rows:
            raise ValueError(f'No historical fixed case found for {path.name}')
        selected.add(identity)
        tasks.extend((path,group,rows,observed) for group in args.groups)
    if selected!={row['checkpoint_sha256'] for row in cases}:
        raise ValueError('One or more archived fixed checkpoints are missing')
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        reports=list(pool.map(replay,tasks))
    targets=[row for block,_,_ in reports for row in block]
    by_source=[row for _,block,_ in reports for row in block]
    to_csv(args.output/'transport-capability-funnel.csv',targets)
    to_csv(args.output/'capacity-counterfactual.csv',by_source)
    to_json(args.output/'fixed-capacity-replay-traces.json',[row for _,_,row in reports])
    to_json(args.output/'fixed-replay-inputs.json',dict(
        source=git('rev-parse','HEAD').decode().strip(),targets=len(cases),returning_samples=len(samples),
        archived_csv={name:sha256((args.prior/name).read_bytes()).hexdigest() for name in
                      ('source-task-blockers.csv','spatial-grain-capability-funnel.csv')}))


def main():
    parser=ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='phase',required=True)
    route=sub.add_parser('census')
    route.add_argument('output',type=Path)
    audit=sub.add_parser('fixed')
    audit.add_argument('prior',type=Path)
    audit.add_argument('output',type=Path)
    audit.add_argument('checkpoints',nargs='+',type=Path)
    audit.add_argument('--groups',nargs='+',default=['C0','C1','C2','C3','C4'])
    audit.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.phase=='census':
        census(args.output)
    else:
        fixed(args)


if __name__=='__main__':
    main()
