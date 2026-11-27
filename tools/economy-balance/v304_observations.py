"""Record actual decisions and derive the end-to-end city transshipment account."""
from argparse import ArgumentParser
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

from common import TOOL_ROOT, to_csv, to_json
from remake import command_books, grain_units, logistics, transshipment, winter_weather
from remake.errors import GameError

sys.path.insert(0,str(TOOL_ROOT/'tests'))
from test_remake_transshipment import FEEDERS, TARGET, advance, create, dispatch, offer, plan, wait_for, world


def feeder_cases():
    game = world(weather=True)
    create(game)
    for origin in FEEDERS:
        dispatch(game,0,origin,20_000)
    advance(game,2)
    # First convoy has arrived; the second must still be represented as in transit.
    a,b = plan(game)['batches']
    staged = transshipment.credit(game.state,'yulin')
    assert a['receipt'] and b['receipt'] is None and staged==a['receipt']['grain']
    partial = dict(turn=game.state.turn,received=deepcopy(a['receipt']),in_transit=b['convoy'],
                   visible_stock=staged,eligible_to_load=offer(game,1,'yulin')['max_cargo'])
    assert partial['eligible_to_load'] < staged
    wait_for(game,lambda: all(row['receipt'] is not None for row in plan(game)['batches']))
    advance(game)
    water=offer(game,1,'yulin')
    reach=water['quote']['routes'][0]['river_segments'][0]['reach_id']
    ice=game.state.extension[winter_weather.POOL]['ice']
    original=ice.get(reach)
    ice[reach]=dict(original or {},state=3)
    frozen=dict(turn=game.state.turn,reach=reach,ice_state=ice[reach]['state'],
        blocked=offer(game,1,'yulin')['blocked'],hub_stock=game.state.cities['yulin'].grain)
    assert frozen['blocked']=='route'
    if original is None:
        del ice[reach]
    else:
        ice[reach]=original
    saves=[]
    for compact in (False,True):
        save=game.export_save(compact=compact)
        saves.append(dict(compact=compact,checksum=save['checksum']))
    stock=game.state.cities['yulin'].grain
    reserved=transshipment.credit(game.state,'yulin')
    cargo=deepcopy([row['cargo'] for row in logistics._pool(game.state)['convoys']])
    game.command(transshipment.COMMAND,dict(action='cancel',plan=1),game.revision)
    after=[row['cargo'] for row in logistics._pool(game.state)['convoys']]
    assert cargo==after and game.state.cities['yulin'].grain==stock
    closed=dict(case='manual',turn=game.state.turn,stock_before=stock,
        stock_after=game.state.cities['yulin'].grain,reserved_before=reserved,
        reserved_after=transshipment.credit(game.state,'yulin'),
        live_convoys_after=len(after),cargo_unchanged=cargo==after)
    return partial,frozen,closed,saves


def unload_case():
    game = world()
    create(game)
    for origin in FEEDERS:
        dispatch(game,0,origin,offer(game,0,origin)['max_cargo'])
    wait_for(game,lambda: all(b['receipt'] is not None for b in plan(game)['batches']))
    advance(game)
    convoy=dispatch(game,1,'yulin',offer(game,1,'yulin')['max_cargo'])['convoy']
    def row():
        return next(item for item in logistics._pool(game.state)['convoys'] if item['id']==convoy)
    current=row()
    # Hold the genuine loaded convoy at its origin before any travel, as
    # route_capacity would do if its next journey no longer fits.
    current.update(status='waiting',reason='route_capacity')
    current['journeys'][-1]['supply']['waiting']=True
    grain=game.state.cities['yulin'].grain
    previous=current['cargo']['grain']+current['journeys'][-1]['supply']['remaining']
    books=command_books.remaining(game.state,'wu')
    wrong=dict(action='unload',convoy=convoy,city='hepu',target='cangwu',mode='land')
    before=game.export_save()
    try:
        game.command(transshipment.COMMAND,wrong,game.revision)
    except GameError:
        assert game.export_save()==before
    else:
        raise ValueError('A remote city accepted a waypoint unloading')
    game.command(transshipment.COMMAND,dict(wrong,city='yulin'),game.revision)
    entry=dict(game.state.extension[transshipment.POOL]['unloads'][-1])
    assert game.state.cities['yulin'].grain-grain==entry['grain']
    assert previous==entry['grain']+entry['capacity']
    assert command_books.remaining(game.state,'wu')==books
    assert logistics.valid_grain_receipt(logistics.grain_receipt(row()))
    return dict(entry,controlled_waiting=True,wrong_remote_city_rejected=True,
        before_physical_load=previous,after_physical_load=entry['capacity'],
        real_stock_delta=game.state.cities['yulin'].grain-grain,
        path=row()['journeys'][-1]['quote']['path'],command_cost=books-command_books.remaining(game.state,'wu'))


def source_capture_case():
    game = world()
    create(game)
    dispatch(game,0,FEEDERS[0],20_000)
    advance(game)
    state=game.state
    captured=state.cities[FEEDERS[1]]
    captured.owner='wei'
    with grain_units.using(state):
        transshipment.synchronize(game,state)
    current=plan(game)
    assert current['reason']=='ownership'
    assert all(not batch['available'] for batch in current['batches'])
    return dict(case='source_change',turn=state.turn,source=captured.id,new_owner=captured.owner,
                plan_reason=current['reason'],present_hub_stock=state.cities['yulin'].grain,
                live_convoys=len(logistics._pool(state)['convoys']),tag_released=sum(
                    batch['released']['closed'] for batch in current['batches']))


def summarize(result, output):
    previous, pilot = result
    if previous['opening_sha256']!=pilot['opening_sha256'] or previous['candidate_303']!=pilot['candidate_303']:
        raise ValueError('The experiments must share their opening state and transport flags')
    current=pilot['plan']
    consumed=Counter()
    observed={row['id']:row for row in pilot['observed_transit'] if row['event']=='departure'}
    stages,deadlines,slots=[],[],[]
    account=Counter()
    for row in current['batches']:
        ident=row['convoy']
        terminal=row['terminal']
        actual=row['receipt']
        cargo=terminal['cargo']
        if not row['stage']:
            account.update(origin_cargo=row['grain'],origin_rations=row['rations'])
        account.update(external_ration_draw=terminal['external_rations'],
            travel_and_wait_rations=terminal['spent_rations'],route_loss=cargo['cargo_route_loss'],
            weather_loss=cargo['cargo_weather_loss'],returned_grain=cargo['cargo_returned']+terminal['returned_rations'],
            abandoned_grain=cargo['cargo_abandoned'],unloaded_grain=cargo.get('cargo_waypoint_unloaded',0))
        if row['target']==current['target']:
            account['final_received']+=actual['grain']
        else:
            account['tag_left_at_hub']+=row['available']+sum(row['released'].values())
        if row['stage'] and sum(amount for _,amount in row['parents'])!=row['grain']+row['rations']:
            raise ValueError('A later convoy was funded by less than its actual load')
        for parent,amount in row['parents']:
            consumed[parent]+=amount
        event=observed[ident]
        stages.append(dict(convoy=ident,stage=row['stage'],source=row['source'],target=row['target'],
            route_mode=event['profile']['mode'],gross_cargo=row['grain'],ration_loaded=row['rations'],
            physical_capacity=row['capacity'],actual_received=actual['grain'],route_loss=cargo['cargo_route_loss'],
            weather_loss=cargo['cargo_weather_loss'],ration_consumed=terminal['spent_rations'],
            final_destination=row['target']==current['target'],capacity_utilization=(row['grain']+row['rations'])/row['capacity']))
        deadlines.append(dict(stage=row['stage'],convoy=ident,purpose=current['purpose'],
            dispatch_turn=row['turn'],estimate_turn=row['eta'],actual_turn=actual['turn'],
            promise_turn=current['promise'],first_shortage_turn=None,
            target=row['target'],timely_to_plan_deadline=actual['turn']<current['original_deadline'],
            final_economic_receipt=row['target']==current['target']))
        slots.append(dict(convoy=ident,owner=event['owner'],parent_city=event['source'],
            dispatch_turn=event['turn'],active_after_dispatch=event['active'],dispatches_after=event['dispatch_count'],
            release_tick=terminal['tick'],officers=event['officers'],escort_troops=event['escort_troops']))
    for row in current['batches']:
        if row['target']!=current['target']:
            assert row['receipt']['grain']==consumed[row['convoy']]+row['available']+sum(row['released'].values())
    inputs=('origin_cargo','origin_rations','external_ration_draw')
    account['residual']=sum(account[key] for key in inputs)-sum(v for k,v in account.items() if k not in inputs)
    if account['residual'] or pilot['final_grain']!=account['final_received']:
        raise ValueError('The end-to-end grain account does not close')
    to_json(output/'end-to-end-grain-account.json',account)
    to_csv(output/'transshipment-stage-throughput.csv',stages)
    to_csv(output/'transshipment-deadline-comparison.csv',deadlines)
    to_csv(output/'parent-origin-slot-usage.csv',slots)
    return account


def run(raw,output):
    result=json.loads(raw.read_text(encoding='utf-8'))
    grain=summarize(result,output)
    partial,frozen,closed,saves=feeder_cases()
    unload=unload_case()
    source_capture=source_capture_case()
    history=result[1]['plan']
    slotted=dict(case=history['reason'],turn=history['closed'],stock_before=None,stock_after=None,
        reserved_before=None,reserved_after=0,live_convoys_after=0,cargo_unchanged=None)
    to_csv(output/'transshipment-cancellation.csv',[closed,slotted])
    to_csv(output/'capacity-unload-and-reroute.csv',[unload])
    to_json(output/'control-edge-cases.json',dict(partial=partial,frozen=frozen,unload=unload,
        source_capture=source_capture,manual_cancellation=closed,saves=saves))
    print(json.dumps(dict(grain_balance=grain,partial=partial,frozen=frozen,unload=unload,
                          source_capture=source_capture),ensure_ascii=False))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    run(args.results,args.output)
