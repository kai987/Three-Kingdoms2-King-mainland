"""Run frozen V2.3 groups through the real campaign observer and resource hooks."""
from argparse import ArgumentParser
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import ROOT, TOOL_ROOT, git, sha256, to_csv, to_json
from observe import RecordedCampaign, run_scenario
from remake import grain_units, market_pricing, strategic_granary, winter_climate, winter_weather
from v222_experiments import STRATEGY
from v23_climate import FEATURES
from v302_audit import Audit

QUICK = ((2026, '184-02', 211), (2031, '190-01', 211), (2034, '207-09', 211),
         (2026, '208-10', 212), (2026, '263-05', 211))
FIVE = (*QUICK, (2026, '184-02', 212), (2026, '208-10', 211))
LONG = ((2026, '184-02', 211), (2026, '208-10', 211), (2026, '208-10', 212))
HOLDOUT = ((2041, '184-02', 211), (2042, '208-10', 212))
GROUPS = ('dry', 'W0', *FEATURES)


class Record:
    def __init__(self, stream):
        self.stream = stream
        self.counts = Counter()
        self.ice = Counter()
        self.transport = {}
        self.markets = Counter()
        self.weather_events = Counter()

    def write(self, kind, row):
        self.counts[kind] += 1
        self.stream.write(json.dumps(dict(kind=kind, **row), ensure_ascii=False,
                                     separators=(',', ':')) + '\n')

    def writerow(self, row):
        if row['resource'] == 'grain' and row['category'] in (
                'regular_income', 'civil_bonus', 'harvest_bonus', 'city_consumption', 'payroll'):
            self.write('warehouse_posting', row)
        if row['category'] == 'audit_mismatch':
            self.write('warehouse_error', row)

    def market(self, kind, row):
        if kind == 'stock_flow' and row['kind'] == 'restock':
            expected = row['opening_stock'] - row['overflow'] + row['restocked']
            if expected != row['stock'] or not 0 <= row['stock'] <= row['capacity']:
                raise ValueError('Monthly market restock does not balance')
            self.markets.update(restocks=1, issued=row['restocked'], overflow=row['overflow'])
            self.write('market_restock', {key:value for key,value in row.items() if key != 'kind'})
        elif kind == 'stock_flow':
            delta = row['grain'] if row['kind'] == 'sell' else -row['grain']
            if row['opening_stock'] + delta != row['stock']:
                raise ValueError('Actual market trade does not balance')
            self.markets.update(transactions=1)

    def weather(self, kind, row):
        if kind in ('agriculture_year', 'agricultural_income', 'agriculture_harvest', 'agricultural_preparation'):
            self.write(kind, row)
        elif kind == 'ice' and row['state']:
            self.ice[row['reach'], row['state']] += 1
        elif kind == 'convoy_day':
            self.weather_events.update(convoy_days=1, hungry_convoy_days=int(row['missing']>0),
                                       convoy_hunger_loss=row['hunger_loss'],
                                       ice_blocked_convoy_days=int(bool(row['ice'])))
        elif kind == 'convoy_event':
            self.weather_events[row['kind_of_event']] += 1
        elif kind == 'travel':
            self.weather_events.update(extra_military_grain=row['extra_grain'],
                                       weather_delay_work=row['delay'])

    def track_convoy(self, state, kind, row, reason, values):
        if kind == 'transport_departed' and row['target_march'] is not None and state.month in (11,12,1,2,3):
            self.transport[row['id']] = dict(convoy=row['id'], owner=row['owner'],
                source=row['source'], target=row['target'], deadline=row['journeys'][0]['arrival_turn'],
                opened=state.turn, actual=None, received=None, reason=None)
        record = self.transport.get(row['id'])
        if record is not None and record['actual'] is None and kind in ('transport_arrived','transport_returned', 'transport_lost'):
            record.update(actual=state.turn, received=values['grain'] if kind=='transport_arrived' else 0, reason=reason)
            self.write('winter_army_supply', record)

    def finish(self):
        terminal = list(self.transport.values())
        return dict(events=dict(self.counts), market=dict(self.markets), weather=dict(self.weather_events),
                    ice_days=[dict(reach=reach,status=status,days=days)
                              for (reach,status), days in sorted(self.ice.items())],
                    winter_army_orders=terminal,
                    winter_army_timely=sum(r['actual'] is not None and r['actual'] <= r['deadline'] and r['received']>0
                                           for r in terminal))


def run_case(output, case):
    wave, group, scenario, seed, strategy, months, source = case
    target = output/'campaigns'/wave/group/f'{scenario}-{seed}-{strategy}'
    result_path = target/'run-v23.json'
    if result_path.is_file():
        existing = json.loads(result_path.read_text())
        if existing['source'] == source and existing['outcome'] in ('complete','natural_end'):
            return existing
    target.mkdir(parents=True, exist_ok=True)
    mask = climate_flags(group)
    version = 221 if group == 'W0' else 0 if group == 'dry' else winter_climate.VERSION
    settings = dict(weather_rules_version=version, transport_emergency_rules_version=222)
    if mask:
        settings[winter_climate.OPTIONS] = mask
    real_command = RecordedCampaign.command
    if git('rev-parse', 'HEAD').decode().strip() != source:
        raise ValueError('Observer must start at the frozen source commit')
    with gzip.open(target/'events.jsonl.gz', 'wt', encoding='utf-8', compresslevel=2) as stream, ExitStack() as stack:
        record = Record(stream)
        audit = Audit(record)
        current = [None]

        def capture(game, kind, payload, revision):
            if kind == 'new':
                payload = dict(payload, **settings)
            with audit.command(game, kind):
                result = real_command(game, kind, payload, revision)
            current[0] = game
            state = game.state
            if state.day == 1:
                with grain_units.using(state):
                    for key, city in state.cities.items():
                        quote = market_pricing.snapshot(game, state, key)
                        record.write('market_price', dict(city=key, owner=city.owner, year=state.year, month=state.month,
                                                          turn=state.turn, buy=quote['buy'], sell=quote['sell']))
            if game.state.turn % 36 == 1 and game.state.turn > 1:
                print(f'{wave} {group} {scenario} {seed}/{strategy} turn {game.state.turn}', flush=True)
            return result

        from remake import logistics
        live_event = logistics._event

        def track(game, state, kind, row, *, lost=0, reason='outbound', amounts=None):
            record.track_convoy(state, kind, row, reason, row['cargo'] if amounts is None else amounts)
            return live_event(game, state, kind, row, lost=lost, reason=reason, amounts=amounts)

        stack.enter_context(audit.install())
        stack.enter_context(patch.object(RecordedCampaign, 'command', capture))
        stack.enter_context(patch.object(logistics, '_event', track))
        stack.enter_context(market_pricing.experiment(2))
        stack.enter_context(market_pricing.observing(record.market))
        stack.enter_context(strategic_granary.experiment(proactive=True, winter=True, relay=False))
        stack.enter_context(winter_weather.experiment(5 if version else 0,
            adjustments=winter_weather.CORRECTIONS if version else 0, detailed=True, observe=record.weather))
        result = run_scenario(scenario, seed, months, target, STRATEGY[strategy])
        game = current[0]
        if result['outcome'] in ('complete','natural_end'):
            save = game.export_save(compact=True)
            from common import HeadlessCampaign
            loaded = HeadlessCampaign(game.catalog, record_journal=False)
            loaded.load_save(save,0)
            assert loaded.export_save(compact=True) == save
            with gzip.open(target/'terminal-save.json.gz', 'wt', compresslevel=2, encoding='utf-8') as saved:
                json.dump(save, saved, ensure_ascii=False)
    if audit.errors:
        raise ValueError(f'Warehouse reconciliation mismatches: {audit.errors}')
    result.update(source=source, wave=wave, group=group, strategy=strategy, weather=version,
                  weather_seed=winter_weather.seed_for(seed) if version else None, options=mask,
                  market_stage=2, granary='302 G1', transport='D0', transshipment=False, emergency=222,
                  catalog_sha256=game.catalog.sha256, map_sha256=sha256((ROOT/'game/assets/map-campaign.png').read_bytes()),
                  measurements=record.finish(), warehouse_audit=audit.metrics(),
                  output=str(target.relative_to(output)), runner_sha256=sha256(Path(__file__).read_bytes()))
    to_json(result_path, result)
    return result


def climate_flags(group):
    return winter_climate.flags(*FEATURES[group]) if group in FEATURES else None


def cases(wave, source):
    if wave == 'smoke':
        tasks = [(group, seed, scenario, strategy, 2) for seed,scenario,strategy in (QUICK[3],)
                 for group in ('W0','W4')]
    elif wave == 'quick':
        tasks = [(group, seed, scenario, strategy, 24) for seed,scenario,strategy in QUICK
                 for group in ('W0','W1','W2','W3','W4')]
        tasks.append(('W2e', 2034, '207-09', 211, 24))
    elif wave == 'five':
        tasks = [(group, seed, scenario, strategy, 60) for seed,scenario,strategy in FIVE for group in ('W0','W4')]
        tasks.extend((group, 2026, '208-10', 212, 60) for group in ('dry','W2','W3'))
    elif wave == 'long':
        tasks = [(group, seed, scenario, strategy, 240) for seed,scenario,strategy in LONG for group in ('W0','W4')]
    else:
        tasks = [(group, seed, scenario, strategy, 60) for seed,scenario,strategy in HOLDOUT for group in ('W0','W4')]
    return [(wave, group, scenario, seed, strategy, months, source) for group,seed,scenario,strategy,months in tasks]


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('waves', nargs='+', choices=('smoke','quick','five','long','holdout'))
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, default=TOOL_ROOT/'build/winter-agriculture-v23')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('Use at least one worker')
    source = git('rev-parse','HEAD').decode().strip()
    args.output.mkdir(parents=True, exist_ok=True)
    tasks = [case for wave in args.waves for case in cases(wave, source)]
    to_json(args.output/'campaign-plan.json', tasks)
    result, failure = [], False
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_case, args.output, case): case for case in tasks}
        for future in as_completed(pending):
            try:
                row = future.result()
                result.append({k: row.get(k) for k in ('wave','group','scenario','seed','strategy','outcome',
                                                       'completed_turns','source','output','failure')})
                failure |= row['outcome'] not in ('complete','natural_end')
                print(json.dumps(result[-1], ensure_ascii=False), flush=True)
            except Exception as error:
                failure = True
                print(pending[future], repr(error), flush=True)
    to_json(args.output/'completed-campaigns.json', result)
    return int(failure)


if __name__ == '__main__':
    raise SystemExit(main())
