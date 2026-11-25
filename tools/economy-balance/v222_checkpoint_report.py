"""Continue verified real V2.2.1 checkpoints under each candidate configuration."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
import csv
import gzip
import io
import json

from common import Catalog, HeadlessCampaign, ROOT, to_json
from remake import logistics, march_supply, transport_emergency, winter_weather
from v222_reproduce import CASES


ANCHORS = {77:920, 2:40, 45:980}
SHAPE = {77:12, 2:9, 45:9}


def replay(item):
    root, ident, level = item
    scenario, seed, origin, final, _ = CASES[ident]
    input_path = root/'baseline'/f'convoy-{ident}'/f'checkpoint-{ANCHORS[ident]}.json.gz'
    with gzip.open(input_path,'rt',encoding='utf-8') as file:
        saved=json.load(file)
    game=HeadlessCampaign(Catalog(ROOT/'game/data/campaigns'/f'{scenario}.json'),record_journal=False)
    game.load_save(saved,0)
    with transport_emergency.experiment(level):
        transport_emergency.initialize(game.state)
    game.validate(game.state)
    levels=('I3','J1','J2','J3')
    rows=[]
    events=[]
    def observe(kind,payload):
        if kind in ('emergency_decision','emergency_plan','convoy_terminal',
                    'convoy_relief_request','convoy_relief_delivery') and payload['convoy_id']==ident:
            events.append(dict(kind=kind, **deepcopy(payload)))
    with winter_weather.experiment(5,adjustments=winter_weather.CORRECTIONS,observe=observe):
        for turn in range(SHAPE[ident]+1):
            state=game.state
            row=next((r for r in logistics._pool(state)['convoys'] if r['id']==ident),None)
            values=dict(tick=(state.turn-1)*10,date=[state.year,state.month,state.day],active=row is not None)
            if row is not None:
                if (row['source'],row['original_target'])!=(origin,final):
                    raise ValueError(f'Unexpected identity for archived convoy {ident}')
                journey=row['journeys'][-1]
                supply=journey['supply']
                values.update(owner=row['owner'],position=march_supply.current_city(journey),
                    last_node=march_supply.last_city(journey),status=row['status'],reason=row['reason'],
                    target=row['target'],route=journey['quote']['path'],route_work=supply.get('winter',{}).get('work',0),
                    bag=supply['remaining'],cargo=row['cargo'],
                    escort=sum(state.officers[i].troops for i in row['officers']),officers=list(row['officers']),
                    shortage=sum(j['supply']['shortage_days'] for j in row['journeys']),
                    lost=sum(j['supply']['lost'] for j in row['journeys']),
                    emergency=row.get('emergency'))
            rows.append(deepcopy(values))
            if state.phase=='finished' or turn==SHAPE[ident]:
                break
            game.command('observe_turn',{},game.revision)
    result=dict(convoy=ident,scenario=scenario,seed=seed,version=levels[level],source=origin,target=final,
        start_tick=ANCHORS[ident],checkpoint_sha256=saved['checksum'],catalog_sha256=game.catalog.sha256,
        turns=rows,events=events,checked_final_save=False)
    final_save=game.export_save(compact=True)
    reloaded=HeadlessCampaign(game.catalog,record_journal=False)
    reloaded.load_save(final_save,0)
    if reloaded.export_save(compact=True)!=final_save:
        raise ValueError(f'Checkpoint save mismatch for {ident}/{level}')
    result['checked_final_save']=True
    to_json(root/'checkpoints'/f'convoy-{ident}-{levels[level]}.json',result)
    return ident,levels[level],len(rows),rows[-1]['active'],rows[-1].get('lost'),len(events)


def baseline_matches(root, bundle):
    results=[]
    with ZipFile(bundle) as z:
        for ident,(scenario, seed, origin, target, _) in CASES.items():
            prefix=f'observed/matrix/I3-212/{seed}/60/{scenario}/'
            with z.open(prefix+'transport-progress-daily.csv.gz') as source, gzip.open(
                    root/'baseline'/f'convoy-{ident}'/scenario/'transport-progress-daily.csv.gz',
                    'rt',encoding='utf-8',newline='') as replay:
                original=csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=source),encoding='utf-8',newline=''))
                history=[r for r in original if r['convoy']==str(ident)]
                replicate=[r for r in csv.DictReader(replay) if r['convoy']==str(ident)]
            if not history or replicate!=history:
                raise ValueError(f'Archived per-day replay differs for convoy {ident}')
            results.append(dict(convoy=ident,scenario=scenario,seed=seed,source=origin,target=target,rows=len(history),
                                identical=True,archive_member=prefix+'transport-progress-daily.csv.gz'))
    to_json(root/'historical-replay-checks.json',results)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args()
    baseline_matches(args.root,args.previous)
    cases=[(args.root,ident,level) for ident in CASES for level in range(4)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(replay,cases):
            print(*row,flush=True)


if __name__=='__main__':
    main()
