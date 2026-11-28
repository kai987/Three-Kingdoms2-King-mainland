"""Rebuild quantitative stage results from completed campaign artifacts."""
from argparse import ArgumentParser
from contextlib import ExitStack
import json
from pathlib import Path
from tempfile import SpooledTemporaryFile

from common import to_json
from v3041_report import CsvSpool, comparisons, emit, rate, read_run

PAIRS = (('K0', 'K2'), ('L0', 'L2'))
DETAILS = ('military-grain-request-ledger', 'military-grain-receipt-ledger',
           'unmet-military-demand', 'convoy-hunger-comparison', 'convoy-return-safety',
           'transport-efficiency-by-purpose', 'transport-demand-episodes', 'small-load-transport-audit')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('observations', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    paths = sorted(args.observations.rglob('run-v3041.json'))
    actual_cases, scores, streams = [], [], {}
    data, checks = args.out/'data', args.out/'checks'
    with ExitStack() as stack:
        for path in paths:
            proof = json.loads(path.read_bytes())
            run = proof['result']
            case, score, rows = read_run(path)
            case.update(runtime_setup_options=run.get('runtime_setup_options'), engine_sha=proof['case']['engine_sha'])
            actual_cases.append(case)
            if score is None:
                continue
            score.update(run['observed_actual_grain'])
            score.update(grain_security_books=run['whole_grain_security_books']['total'],
                urban_food_payment_rate=rate(score['city_food_paid'], score['city_food_required']),
                approved_military_grain=run['military_preparation_requested'].get('approved_sortie', 0)
                    if case['variant'] in ('K2','L2') else None,
                p95_turn_cpu=run['performance'].get('p95_turn_cpu_seconds'),
                grain_market_volume=run['whole_grain_market_volume'])
            scores.append(score)
            for key in DETAILS:
                if rows.get(key):
                    if key not in streams:
                        file = stack.enter_context(SpooledTemporaryFile(max_size=512*1024, mode='w+t', encoding='utf-8'))
                        streams[key] = CsvSpool(file)
                    streams[key].append(rows[key])
        for name, spool in streams.items():
            spool.export(data/f'{name}.csv')
    pairs, alerts = comparisons(scores, pairs_to_compare=PAIRS, extra=(
        'city_food_required', 'city_food_paid', 'city_food_missing', 'urban_food_payment_rate', 'resident_due',
        'garrison_due', 'march_food_required', 'march_food_paid', 'march_food_missing','march_hunger_losses',
        'longest_city_shortage_streak', 'grain_security_books', 'approved_military_grain', 'p95_turn_cpu',
        'transit_requested', 'transit_received'))
    for name, rows in (
        ('scenario-scores', scores), ('pairwise', pairs), ('balance-alerts', alerts),
        ('winter-grain-timely-comparison', [row for row in scores if row['requested_grain']]),
        ('winter-order-timely-comparison', [row for row in scores if row['matured_orders']]),
        ('long-term-economy-comparison', [row for row in pairs if row['wave']=='long']),
        ('holdout-comparison', [row for row in pairs if row['wave']=='holdout']),
    ):
        emit(data/f'{name}.csv', rows)
    planned = {path.stem.removesuffix('-plan'): json.loads(path.read_bytes())
               for path in sorted(args.observations.glob('*-plan.json'))}
    to_json(checks/'simulation-manifest.json', dict(planned=planned, actual=actual_cases))
    to_json(checks/'report-status.json', dict(observed=len(actual_cases), scored=len(scores), alerts=len(alerts),
        outcomes=[{key: row[key] for key in ('wave','variant','scenario','seed','strategy','outcome')}
                  for row in actual_cases]))


if __name__ == '__main__':
    main()
