"""Reproduce the archived V2.2.1 convoy identities and capture real node state."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from copy import copy
from pathlib import Path
from unittest.mock import patch
import gzip
import hashlib
import json

from common import ROOT, TOOL_ROOT, to_json
from observe import RecordedCampaign, run_scenario
from observer_telemetry import config
from v221_experiments import TransportRecorder
from remake import historical_campaigns, logistics, march_supply, staging_supply, winter_transport, winter_weather

CASES = {
    77: ('207-09', 2028, 'shujun', 'hongnong', (910, 920, 980, 1050, 1180, 1800)),
    2: ('208-10', 2026, 'henan', 'guangling', (40, 50, 550, 930, 1560, 1580)),
    45: ('184-02', 2026, 'shujun', 'badong', (970, 980, 1230, 1390, 1800)),
}


def record(game, state, row):
    journey = row['journeys'][-1]
    book = journey['supply']
    here = march_supply.current_city(journey)
    city = state.cities[here] if here is not None else None
    units = march_supply.ration_units(state, row['officers'], row['cargo']['reserves'])
    available = book['remaining']+row['cargo']['grain']
    result = dict(tick=book['clock_tick'], date=[state.year,state.month,state.day],
        owner=row['owner'], source=row['source'], original_target=row['original_target'],
        journey_source=journey['source'], target=row['target'], here=here, units=units,
        officers={str(i): state.officers[i].troops for i in row['officers']},
        remaining_work=journey['quote']['days']*644000-book.get('winter',{}).get('work',0),
        bag=book['remaining'], cargo=row['cargo'], ice=book.get('winter',{}).get('blocked'),
        status=row['status'], reason=row['reason'], delivery_done=row['delivery_done'],
        route=journey['quote']['path'], shortage_days=book['shortage_days'],
        local=None, possible_nodes=[], relief_origins=[], home=None)
    if city is None:
        return result
    origin = copy(city)
    origin.owner = row['owner']
    same_owner = city.owner == row['owner']
    result['local'] = dict(owner=city.owner, grain=city.grain, supplies_allowed=same_owner,
        transit_allowed=historical_campaigns.transit_allowed(state,row['owner'],city.owner),
        exportable=winter_transport.city_stock(game,state,city,staging_supply.available(state,city))
        if same_owner else 0,
        receipt_blocker=logistics._receiving_blocker(game,state,row,city,returning=True) if same_owner else 'not_owned')
    for target in sorted(state.cities.values(), key=lambda item: item.id):
        if target.owner != row['owner']:
            continue
        selected = logistics._safe_quote(game,state,origin,target,row['route_policy'])
        if selected is None:
            if target.id == row['source']:
                result['home'] = dict(reachable=False,owner=target.owner)
            continue
        budget = winter_transport.protected_cost(game,state,selected[1],units,credit=book['credit_units'])
        receiving = logistics._receiving_blocker(game,state,row,target,returning=True)
        point = dict(city=target.id, path=selected[1]['path'], receiving_blocker=receiving,
                     covered=available>=budget['meal']+budget['safety'], **budget)
        if target.id == row['source']:
            result['home'] = point
        if budget['days'] is not None:
            result['possible_nodes'].append(point)
    result['possible_nodes'].sort(key=lambda item:(item['days'],item['meal'],item['city']))
    result['possible_nodes'] = result['possible_nodes'][:8]
    if same_owner:
        for donor in sorted(state.cities.values(), key=lambda item:item.id):
            if donor.owner != row['owner'] or donor.id==city.id:
                continue
            policy=logistics._pool(state)['cities'][donor.id]
            surplus=winter_transport.city_stock(game,state,donor,staging_supply.available(state,donor))
            result['relief_origins'].append(dict(city=donor.id,surplus=surplus,
                free_escort_count=len(logistics._eligible(game,state,donor)),
                present=logistics._present_count(game,state,donor),
                keep=policy['policy']['reserve_officers'],
                active_source=any(x['source']==donor.id for x in logistics._pool(state)['convoys'])))
    return result


def replay(convoy, output):
    scenario, seed, source, target, ticks = CASES[convoy]
    root = output / f'convoy-{convoy}'
    found = []
    command = RecordedCampaign.command
    def observe_command(game, *args, **kwargs):
        view = command(game, *args, **kwargs)
        tick = (game.state.turn-1)*10
        if tick not in ticks:
            return view
        row = next((item for item in logistics._pool(game.state)['convoys'] if item['id']==convoy),None)
        if row is None:
            found.append(dict(tick=tick, active=False))
            return view
        if (row['source'],row['original_target']) != (source,target):
            raise ValueError(f'Historical convoy {convoy} identity does not match')
        found.append(record(game,game.state,row))
        if tick in ticks[:3]:
            with gzip.open(root / f'checkpoint-{tick}.json.gz','wt',encoding='utf-8') as file:
                json.dump(game.export_save(compact=True),file,ensure_ascii=False,separators=(',',':'))
        to_json(root/'node-decisions.json',found)
        return view

    root.mkdir(parents=True, exist_ok=True)
    settings = config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    with patch.object(RecordedCampaign,'command',observe_command), TransportRecorder(root/scenario) as recorder:
        with winter_weather.experiment(5,adjustments=winter_weather.CORRECTIONS,detailed=True,observe=recorder):
            result=run_scenario(scenario,seed,60,root,'G4al',settings)
    if result['outcome']!='complete' or not any(row.get('active',True) for row in found):
        raise ValueError(f'Historical replay failed for {convoy}: {result.get("failure")}')
    to_json(root/'node-decisions.json',found)
    return convoy, len(found), result['head']


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--convoy', type=int, choices=CASES, action='append')
    args=parser.parse_args()
    if Path(ROOT).name != 'Three-Kingdoms2-King-mainland':
        parser.error('select the verified historical runtime with TK2_OBSERVER_RUNTIME_ROOT')
    ids=args.convoy or list(CASES)
    with ProcessPoolExecutor(max_workers=len(ids)) as pool:
        for convoy, count, head in pool.map(replay,ids,[args.output]*len(ids)):
            print(convoy,count,head,flush=True)


if __name__=='__main__':
    main()
