"""Paired V3.0.2 observation with actual resource and transport receipts."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack
from functools import lru_cache
from pathlib import Path
import csv
import gzip
import json
import traceback
import zipfile
from unittest.mock import patch

from common import ROOT as RUNTIME_ROOT, TOOL_ROOT, sha256, to_json
from observe import RecordedCampaign, run_scenario
from observer_telemetry import config
from remake import grain_units, market_pricing, transport_emergency, winter_weather
from v221_experiments import source_identity
from v222_experiments import Recorder as TransportRecorder, STRATEGY
from v301_experiments import (CITY_FIELDS, FIRST, LONG, REGION_FIELDS, TRANSACTION_FIELDS,
                               WINTER, JsonLines, RegionalRecorder, capture_warehouse_postings)
from v302_audit import Audit

ROOT = TOOL_ROOT / 'build/strategic-granary-v302'
GROUPS = ('S0', 'S1', 'S2', 'S3', 'S3-no-winter', 'S4')
WAVES = ('rapid', 'dry', 'winter', 'long', 'holdout', 'smoke')
SETTINGS = TOOL_ROOT/'tools/economy-balance/observer-config.json'
PRIOR = Path.home()/'Downloads/three-kingdoms-regional-economy-v301-validation-repacked.zip'



@lru_cache(maxsize=1)
def prior_manifest():
    with zipfile.ZipFile(PRIOR) as archive:
        data = json.loads(archive.read('data/simulation-manifest.json'))
    return {(row['seed'],row['scenario'],row['strategy'],row['weather']):row['weather_seed']
            for row in data['simulations']}


@lru_cache(maxsize=1)
def map_sha():
    return sha256((RUNTIME_ROOT/'game/assets/map-campaign.png').read_bytes())


def _weather_seed(seed,scene,policy,weather):
    actual = winter_weather.seed_for(seed) if weather else None
    prior = prior_manifest().get((seed,scene,policy,weather),actual) if PRIOR.is_file() else actual
    if prior != actual:
        raise ValueError('Archived weather seed differs from the new run')
    return actual

def cases(wave, groups):
    if wave == 'rapid':
        samples = [(2026,'208-10',211,0), (2026,'208-10',211,221),
                   (2026,'184-02',211,221), (2026,'263-05',211,221), (2031,'190-01',212,221)]
        months = 12
    elif wave == 'dry':
        samples = [(seed,scene,211,0) for seed,scene in FIRST]
        months = 60
    elif wave == 'winter':
        samples = [(seed,scene,policy,221) for seed,scene in WINTER for policy in (211,212)]
        months = 60
    elif wave == 'long':
        samples = [(seed,scene,211,221) for seed,scene in LONG]
        months = 240
    elif wave == 'holdout':
        samples = [(2034,'207-09',211,221)]
        months = 60
    else:
        from common import catalog_paths
        samples = [(2026,scene.stem,211,221) for scene in catalog_paths()]
        months = 1
    return [(wave,group,seed,scene,policy,weather,months)
            for seed,scene,policy,weather in samples for group in groups]


def case_dir(root, case):
    wave, group, seed, scene, strategy, weather, months = case
    return root/'observed'/wave/f'w{weather}'/group/str(strategy)/str(seed)/str(months)/scene


def _csv(stack, folder, name, fields):
    path = folder/name
    options = dict(encoding='utf-8', newline='')
    stream = stack.enter_context(gzip.open(path, 'wt', compresslevel=2, **options) if path.suffix == '.gz'
                                 else path.open('w', **options))
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    return writer


def run(root, case, *, granary_options=None, progress=False, capacity_options=None,
        economy_background=None, instrument=None):
    wave, group, seed, scene, policy, weather, months = case
    dest = case_dir(root, case)
    complete = dest/'run-v302.json'
    if complete.is_file():
        return json.loads(complete.read_text())
    raw = dest.parent/'_working'/scene
    raw.mkdir(parents=True, exist_ok=True)
    identity = source_identity()
    case_data = dict(wave=wave, group=group, seed=seed, scenario=scene, strategy=policy, weather=weather,
        weather_seed=_weather_seed(seed,scene,policy,weather), requested_months=months,
        market_stage=0 if group == 'S0' else 2, source=identity['head'], tree_sha256=identity['tree_sha256'],
        emergency=222 if weather else 0, output=str(dest.relative_to(root)), map_sha256=map_sha(),
        reserve_options=(None if group in ('S0','S1') else dict(version=302,proactive=group in GROUPS[3:],
            winter=bool(weather) and group in ('S3','S4'), relay=group=='S4')))
    if granary_options is not None:
        case_data['reserve_options'] = granary_options
    if economy_background is not None:
        case_data.update(transport_capacity_options=capacity_options,economy_background=economy_background)
        if economy_background=='G0':
            case_data['reserve_options']=None
    try:
        with TransportRecorder(raw) as transport, ExitStack() as stack:
            writers = {}
            for name, fields in (
                    ('market-stock-flow.csv.gz', TRANSACTION_FIELDS), ('city-market-prices.csv.gz', CITY_FIELDS),
                    ('market-price-changes.csv.gz', CITY_FIELDS), ('regional-market-daily.csv.gz', REGION_FIELDS),
                    ('regional-market-monthly.csv', REGION_FIELDS)):
                writers[name] = _csv(stack, raw, name, fields)
            def jsonl(name):
                return JsonLines(stack.enter_context(gzip.open(raw/name, 'wt', compresslevel=2, encoding='utf-8')))
            writers['regional-orders.jsonl'] = jsonl('regional-orders.jsonl.gz')
            strategic_stream = jsonl('strategic-granary-events.jsonl.gz')
            if economy_background is not None:
                from remake import transport_capacity
                capacity_stream=jsonl('transport-capacity-events.jsonl.gz')
                stack.enter_context(transport_capacity.observing(
                    lambda event,row: capacity_stream.writerow(dict(event=event,**row))))
            audit_stream = _csv(stack, raw, 'warehouse-postings.csv.gz',
                'command turn year month day city owner resource balance_before balance_after delta category site'.split())
            audit = Audit(audit_stream)
            stack.enter_context(audit.install())
            recorder = RegionalRecorder(writers)
            original = RecordedCampaign.command
            def capture(game, action, payload, revision):
                with audit.command(game, action):
                    if action=='new' and capacity_options is not None:
                        payload=dict(payload,transport_capacity_rules_version=303,
                                     transport_capacity_options=capacity_options)
                    result = recorder.attach(game, action, payload, revision)
                if progress and game.state.turn % 30 == 0:
                    print(f'{wave} {group} {scene} {seed} p{policy} w{weather}: turn {game.state.turn}', flush=True)
                return result
            stack.enter_context(patch.object(RecordedCampaign, '_v301_command', original, create=True))
            stack.enter_context(patch.object(RecordedCampaign, 'command', capture))
            stack.enter_context(market_pricing.observing(recorder.event))
            capture_warehouse_postings(stack)
            stack.enter_context(market_pricing.experiment(case_data['market_stage']))
            stack.enter_context(winter_weather.experiment(5 if weather else 0,
                adjustments=winter_weather.CORRECTIONS if weather else 0, detailed=True, observe=transport))
            stack.enter_context(transport_emergency.experiment(3 if weather else 0))
            if case_data['reserve_options'] is not None:
                from remake import strategic_granary
                options = {key:value for key,value in case_data['reserve_options'].items()
                           if key != 'version' or value != 302}
                stack.enter_context(strategic_granary.experiment(**options))
                stack.enter_context(strategic_granary.observing(
                    lambda event,row: strategic_stream.writerow(dict(event=event,**row))))
            if instrument is not None:
                instrument(stack, raw)
            result = run_scenario(scene, seed, months, raw.parent, STRATEGY[policy], config(SETTINGS))
        if result['outcome'] in ('complete','natural_end'):
            result['transport_survival'] = transport.summary(result['terminal']['convoy_loads'],
                result['completed_turns']*10, dict(start_year=result['start_date'][0], start_month=result['start_date'][1]))
        result['audit'] = audit.metrics()
        result['market_streams'] = dict(recorder.counts)
    except Exception as exc:
        (raw/'exception.txt').write_text(traceback.format_exc(), encoding='utf-8')
        result = dict(outcome='exception', failure=str(exc))
    result.update(case_data)
    to_json(raw/'run-v302.json',result)
    raw.rename(dest)
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('waves',nargs='+',choices=WAVES)
    parser.add_argument('--groups',nargs='+',choices=GROUPS,default=GROUPS[:4])
    parser.add_argument('--scenarios',nargs='+')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=Path,default=ROOT)
    parser.add_argument('--smoke-group',choices=GROUPS,default='S3')
    args = parser.parse_args()
    matrix = [case for wave in args.waves for case in cases(wave, (args.smoke_group,) if wave=='smoke' else args.groups)
              if not args.scenarios or case[3] in args.scenarios]
    to_json(args.output/f'planned-{"-".join(args.waves)}-{"-".join(args.groups)}.json',matrix)
    with ProcessPoolExecutor(args.workers) as pool:
        futures = {pool.submit(run,args.output,case):case for case in matrix}
        failed = []
        for future in as_completed(futures):
            row = future.result()
            print(json.dumps({key:row.get(key) for key in
                ('wave','group','scenario','seed','weather','strategy','outcome','full_months','seconds','failure')},
                ensure_ascii=False),flush=True)
            if row['outcome'] != 'complete' or row.get('audit',{}).get('city_resource_mismatches'):
                failed.append(futures[future])
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
