"""Execute controlled but fully settled V3.0.4 comparisons on the real map."""
from argparse import ArgumentParser
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from resource import RUSAGE_SELF, getrusage
import sys
from tempfile import TemporaryDirectory
from time import process_time
from unittest.mock import patch

from common import ROOT, TOOL_ROOT, git, to_csv, to_json
from remake import grain_units, logistics, transport_capacity, transshipment
from remake.campaign import Catalog
from v303_replay_checks import physical_controls

sys.path.insert(0,str(TOOL_ROOT/'tests'))
from test_remake_transshipment import FEEDERS, HUBS, TARGET, Headless, advance, create, dispatch, offer, plan, world


def measure(group, *, ends_at_river=False):
    game = world(granary=302)
    hubs = HUBS[:1] if ends_at_river else HUBS
    destination = HUBS[1] if ends_at_river else TARGET
    # Both controls share the same explicit 303 flags and the same city state.
    state = game.state
    state.extension[transport_capacity.POOL]['features']['concurrency'] = False
    opening = game.to_dict()
    opening['extension'].pop(transshipment.POOL)
    opening['extension'].pop(transshipment.FIELD)
    if group=='E0':
        state.extension.pop(transshipment.POOL)
        state.extension.pop(transshipment.FIELD)
    from remake.campaign import digest
    actions, samples, events = [], [], []
    quotes = 0
    base = logistics._safe_path

    def query(*args,**kw):
        nonlocal quotes
        quotes += 1
        return base(*args,**kw)

    def observe(event,row):
        if event in ('departure','delivery','terminal'):
            events.append(dict(event=event,**row))

    def step():
        if transshipment.enabled(game.state):
            for hub in hubs:
                stock=game.state.cities[hub].grain
                samples.append(dict(turn=game.state.turn,city=hub,actual_stock=stock,
                    tagged_stock=transshipment.credit(game.state,hub),physical_capacity=logistics.LIMIT,
                    free_room=max(0,logistics.LIMIT-stock)))
        advance(game)

    def wait(fn):
        for _ in range(24):
            if fn():
                return
            step()
        raise ValueError('Timed out waiting for an actual delivery or a dispatch slot')

    start = process_time()
    with transport_capacity.observing(observe), patch.object(logistics,'_safe_path',query):
        if group=='E1':
            create(game,hubs=hubs,modes=('land','river') if ends_at_river else ('land','river','land'),
                   target=destination)
            for source in FEEDERS:
                quote = offer(game,0,source)
                actions.append(dispatch(game,0,source,quote['max_cargo'])['convoy'])
            wait(lambda: all(row['receipt'] is not None for row in plan(game)['batches']))
            roundtrip = []
            for compact in (False, True):
                saved=game.export_save(compact=compact)
                restored=Headless(game.catalog,record_journal=False)
                restored.load_save(saved,0)
                assert saved==restored.export_save(compact=compact)
                roundtrip.append(dict(compact=compact,checksum=saved['checksum']))
            step()
            actions.append(dispatch(game,1,'yulin',offer(game,1,'yulin')['max_cargo'])['convoy'])
            wait(lambda: plan(game)['batches'][2]['receipt'] is not None)
            step()
            if ends_at_river:
                wait(lambda: all(row['terminal'] is not None for row in plan(game)['batches']))
                if transshipment.credit(game.state,'yulin'):
                    raise ValueError('The short comparison left tagged stock available to dispatch')
                game.command(transshipment.COMMAND,dict(action='cancel',plan=1),game.revision)
            else:
                for _ in range(2):
                    wait(lambda: offer(game,2,'cangwu')['blocked'] is None)
                    actions.append(dispatch(game,2,'cangwu',offer(game,2,'cangwu')['max_cargo'])['convoy'])
            wait(lambda: bool(game.state.extension[transshipment.POOL]['history']))
            closed=game.state.extension[transshipment.POOL]['history'][-1]
        else:
            closed=None
            roundtrip=[]
            for origin in FEEDERS:
                with grain_units.using(game.state):
                    state=game.state
                    source,target=state.cities[origin],state.cities[destination]
                    policy=logistics._pool(state)['cities'][origin]['policy']
                    path=logistics._safe_path(game,state,origin,destination,'wu','fastest',policy)
                    back=logistics.convoy_return(game,state,source,target,policy)
                    actor=min(logistics._eligible(game,state,source),key=lambda i:(state.officers[i].troops,logistics._key(i)))
                    cap=logistics.capacity_quote(game,state,source,target,[actor],path,100_000,0,back[1])
                assert not cap['blocked_reason']
                game.command('dispatch_transport',dict(source=origin,target=destination,officers=[actor],
                    route_mode='fastest',cargo=dict(grain=cap['max_cargo'],gold=0,reserves=0)),game.revision)
                actions.append(logistics._pool(game.state)['convoys'][-1]['id'])
            wait(lambda: not logistics._pool(game.state)['convoys'])
    elapsed = round(process_time()-start,6)
    departure = {r['id']:r for r in events if r['event']=='departure'}
    receipts = {r['id']:r for r in events if r['event']=='delivery'}
    terminals = {r['id']:r for r in events if r['event']=='terminal'}
    if not (len(actions)==len(departure)==len(receipts)==len(terminals)):
        raise ValueError('The comparison did not settle all configured orders')
    for ident in actions:
        cargo=terminals[ident]['cargo_receipt']
        bag=terminals[ident]['rations']
        assert logistics.valid_grain_receipt(cargo)
        assert bag['loaded']+bag['received']==sum(bag[key] for key in ('consumed','to_cargo','remaining'))
    final=sum(r['cargo']['grain'] for r in receipts.values() if r['target']==destination)
    books=sum(row['command_books'] for row in departure.values())
    work=sum(row['cargo']['grain'] for row in receipts.values())
    officer_days=0
    for ident,row in departure.items():
        end=terminals[ident]
        cycle=end['end_tick']-(row['turn']-1)*10
        cooldown=0 if end['reusable_turn'] is None else max(0,(end['reusable_turn']-1)*10-end['end_tick'])
        officer_days+=sum(type(i) is int for i in row['officers'])*cycle
        officer_days+=sum(type(i) is int for i in end['received_officers'])*cooldown
    result=dict(group=group,source=git('rev-parse','HEAD').decode().strip(),
                case='pearl_ends_at_river_controlled' if ends_at_river else 'pearl_real_routes_controlled',
                destination=destination,
                opening_sha256=digest(opening),seed=2026,catalog_sha256=game.catalog.sha256,
                candidate_303=opening['extension'][transport_capacity.POOL]['features'],
                commands=books,final_grain=final,transport_handling=work,
                first_final_day=(min(r['turn'] for r in receipts.values() if r['target']==destination)-1)*10,
                last_final_day=(max(r['turn'] for r in receipts.values() if r['target']==destination)-1)*10,
                ration_consumed=sum(r['ration_spent'] for r in terminals.values()),
                transport_losses=sum(r['cargo_receipt']['cargo_route_loss']+r['cargo_receipt']['cargo_weather_loss']
                                     for r in terminals.values()),
                officer_days_including_cooldown=officer_days,
                final_net_per_officer_day=None if not officer_days else final/officer_days,
                final_net_per_command=final/books,stage_quotes=quotes,cpu_seconds=elapsed,
                process_peak_rss=getrusage(RUSAGE_SELF).ru_maxrss,
                peak_tagged_warehouse_grain=max((r['tagged_stock'] for r in samples),default=0),
                turn_boundary_tagged_grain_days=sum(r['tagged_stock']*10 for r in samples),
                observed_transit=events,plan=closed,save_roundtrips=roundtrip,warehouse_samples=samples)
    return result


def controlled_sea():
    source,hub,target='hepu','jiaozhi','yulin'
    data=deepcopy(Catalog(ROOT/'game/data/campaigns/227-02.json').data)
    for raw in data['travel_routes']:
        if raw['id'] == 'hepu:jiaozhi:sea':
            raw['land_km'] = 0
            raw['distance_km'] = raw['sea_km']
            raw['timing_geometry']['parts'] = [part for part in raw['timing_geometry']['parts'] if part['mode']=='sea']
            break
    else:
        raise ValueError('Controlled sea route template missing')
    with TemporaryDirectory() as folder:
        config=Path(folder)/'controlled-pure-sea.json'
        config.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        game=world(capacity=False)
        game.catalog=Catalog(config)
        city=game.state.cities[source]
        city.grain=220_000
        game.command('set_logistics',dict(city=source,policy=dict(allow_sea=True,max_grain=150_000,
                     reserve_grain=0,reserve_officers=0)),game.revision)
        game.command(transshipment.COMMAND,dict(action='create',sources=[source],hubs=[hub],target=target,
            modes=['sea','land'],grain=150_000,purpose='reserve',promise_turns=30),game.revision)
        cap=offer(game,0,source)
        if cap.get('capacity')!=150_000 or cap['max_cargo']+cap['rations']!=150_000:
            raise ValueError(f'Controlled sea offer: {cap.get("blocked")}, cap {cap.get("capacity")}')
        sent=dispatch(game,0,source,cap['max_cargo'])
        game.validate(game.state)
        return dict(controlled=True,uses_natural_pure_sea=False,cargo=sent['grain'],rations=sent['rations'],
                    actual_dispatched_total=sent['grain']+sent['rations'],capacity=sent['capacity'])


def run(output):
    results=[measure('E0'),measure('E1')]
    if results[0]['opening_sha256']!=results[1]['opening_sha256']:
        raise ValueError('The two control worlds have different openings')
    to_json(output/'controlled-route-results.json',results)
    controls=dict(pearl=physical_controls(),sea=controlled_sea())
    to_json(output/'physical-controls.json',controls)
    to_csv(output/'end-to-end-delivery-comparison.csv',[
        {k:v for k,v in row.items() if k not in ('observed_transit','plan','save_roundtrips','warehouse_samples')}
        for row in results])
    to_csv(output/'hub-capacity-utilization.csv',[
        dict(row,tagged_utilization=row['tagged_stock']/row['physical_capacity'])
        for row in results[1]['warehouse_samples']])
    batches=results[1]['plan']['batches']
    to_csv(output/'transshipment-plan-ledger.csv',batches)
    to_csv(output/'transshipment-receipt-ledger.csv',[dict(convoy=row['convoy'],source=row['source'],
        target=row['target'],received=row['receipt']['grain'],turn=row['receipt']['turn'],parents=row['parents']) for row in batches])
    to_csv(output/'hub-stock-postings.csv',[dict(hub=row['target'],convoy=row['convoy'],
        received=row['receipt']['grain'],consumed_by_later_stages=sum(amount for leg in batches for parent,amount in leg['parents']
                    if parent==row['convoy']),released=sum(row['released'].values())) for row in batches if row['target']!=TARGET])
    to_csv(output/'batch-consolidation.csv',[row for row in batches if len(row['parents'])>1])
    to_csv(output/'batch-splitting.csv',[row for row in batches if row['stage']==2])
    print(json.dumps(dict(controls=controls['sea'],comparison=[{k:r[k] for k in (
        'group','final_grain','last_final_day','commands','ration_consumed','transport_losses')} for r in results]),ensure_ascii=False))


def short_comparison(output):
    results=[measure('E0',ends_at_river=True),measure('E1',ends_at_river=True)]
    if results[0]['opening_sha256']!=results[1]['opening_sha256']:
        raise ValueError('The two short controls have different openings')
    to_json(output/'short-chain-comparison.json',results)
    columns=('group','case','destination','final_grain','last_final_day','commands','ration_consumed',
             'transport_losses','officer_days_including_cooldown','final_net_per_officer_day','final_net_per_command')
    values=[{key:row[key] for key in columns} for row in results]
    to_csv(output/'short-chain-comparison.csv',values)
    print(json.dumps(values,ensure_ascii=False))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--short',action='store_true')
    args=parser.parse_args()
    (short_comparison if args.short else run)(args.output)
