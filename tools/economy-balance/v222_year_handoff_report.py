"""Verify real convoy escorts released to their home cities at year rollover."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from csv import DictReader
from gzip import open as gzip_open
from pathlib import Path
from unittest.mock import patch
import json

from common import ROOT, to_json
from observe import run_scenario
from observer_telemetry import config
from remake import campaign, domestic, logistics, transport_emergency, winter_weather
from v222_experiments import LEVEL, Recorder, STRATEGY, source_identity
from v222_report import sha


CASES = (
    ('184-02', 211, 'J3', 838, 743, 193, 3210),
    ('208-10', 211, 'I3', 1122, 530, 221, 4410),
    ('208-10', 212, 'I3', 1082, 530, 221, 4410),
)


def daily(path, convoy, through):
    with gzip_open(path/'convoy-resolution-daily.csv.gz','rt',encoding='utf-8',newline='') as stream:
        return [row for row in DictReader(stream)
                if row['convoy_id']==str(convoy) and int(row['tick'])<=through]


def replay(args):
    root, case = args
    scene, strategy, group, convoy_id, officer_id, year, tick = case
    original = root/'observed'/f'{group}-{strategy}'/'2026'/'240'/scene
    workspace = root/'year-handoff-replay'/f'{group}-{strategy}'/scene
    settings = config(ROOT/'tools/economy-balance/observer-config.json')
    source = source_identity()
    monthly = campaign.Campaign._monthly_calendar
    advance = campaign.advance_year
    add_reserves = domestic.add_reserves
    receipt = {}

    def observe_calendar(game,state,harvest=None):
        if state.year!=year or state.year<=state.calendar_cursor:
            return monthly(game,state,harvest)
        convoy = next(row for row in logistics._pool(state)['convoys'] if row['id']==convoy_id)
        officer = state.officers[officer_id]
        assert officer_id in convoy['officers'] and officer.alive
        receipt.update(tick=tick,troops_before=officer.troops,convoy_owner=convoy['owner'])
        def observe_retirement(*args,**kwargs):
            events = advance(*args,**kwargs)
            event, = (e for e in events if e.get('runtime_id')==officer_id
                      and e['event']=='remove_after_death_year')
            receipt['calendar_event'] = deepcopy(event)
            return events

        def observe_credit(game_arg,state_arg,city,amount,*args,**kwargs):
            event = receipt.get('calendar_event')
            inspect = bool(event and 'city_credit' not in receipt
                           and city.id==event['origin_city'] and amount==event['released_troops'])
            before = city.reserves
            result = add_reserves(game_arg,state_arg,city,amount,*args,**kwargs)
            if inspect:
                receipt['city_credit']=dict(city=city.id,owner=city.owner,before=before,after=city.reserves,
                                            credited=city.reserves-before)
            return result

        with patch.object(campaign,'advance_year',observe_retirement), patch.object(domestic,'add_reserves',observe_credit):
            result = monthly(game,state,harvest)
        assert not officer.alive and officer.troops==0
        return result

    with Recorder(workspace/scene) as recorder, winter_weather.experiment(5, adjustments=winter_weather.CORRECTIONS,
            detailed=True,observe=recorder), transport_emergency.experiment(LEVEL[group]), patch.object(
                campaign.Campaign,'_monthly_calendar',observe_calendar):
        run = run_scenario(scene,2026,tick//30+1,workspace,STRATEGY[strategy],settings)
    assert run['outcome']=='complete' and receipt['troops_before']==receipt['calendar_event']['released_troops']
    assert receipt['city_credit']['credited']==receipt['troops_before']
    historical = json.loads((original/'run.json').read_text())
    assert (historical['catalog_sha256'],historical['weather_seed'])==(run['catalog_sha256'],winter_weather.seed_for(2026))
    observed = daily(original,convoy_id,tick+6)
    replayed = daily(workspace/scene,convoy_id,tick+6)
    assert observed and observed==replayed
    return dict(scenario=scene,strategy=strategy,group=group,months=240,seed=2026,convoy_id=convoy_id,
        officer_id=officer_id,catalog_sha256=run['catalog_sha256'],previous_source=historical['source_tree_sha256'],
        replay_source=source['tree_sha256'],replay_git_commit=run['head'],verified_work_and_personnel_days=len(observed),
        previous_daily_sha256=sha(original/'convoy-resolution-daily.csv.gz'),**receipt)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    with ProcessPoolExecutor(max_workers=3) as pool:
        receipts=list(pool.map(replay,[(args.root,case) for case in CASES]))
    to_json(args.root/'checks/year-handoff-receipts.json',receipts)
    for entry in receipts:
        print(entry['scenario'],entry['group'],entry['strategy'],entry['convoy_id'],
              entry['calendar_event']['person_id'],entry['city_credit'],flush=True)


if __name__=='__main__':
    main()
