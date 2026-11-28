"""Reconcile fixed acceptance evidence before launching the 24-month pairs."""
from argparse import ArgumentParser
from collections import Counter
import csv
import json
from pathlib import Path

from common import to_json


SAFETY = ('city_resource_mismatches', 'market_transaction_errors', 'market_account_errors',
          'transport_position_overruns', 'repeated_origin_dispatches', 'simultaneous_escort_overlaps',
          'dispatch_book_deviation', 'duplicate_receipts', 'invalid_receipt_credits',
          'duplicate_books', 'book_posting_errors')


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('performance', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--engine', required=True)
    args = parser.parse_args()
    root = args.report
    safety = read(root/'resource-safety.csv')
    comparisons = {r['pair']: r for r in read(root/'fixed-first-meal-paired-effect.csv')}
    return_slot = Counter(r['group'] for r in read(root/'returning-slot-coverage-recovery.csv'))
    south = read(root/'southern-checkpoint-results.csv')
    baxi = {row['group']: row for row in read(root/'baxi-city-and-army-balance.csv') if row['march_id'] == '282'}
    perf = {(r['group'], r['checkpoint']): r for r in read(args.performance)}
    equivalence = read(root/'scheduler-decision-equivalence.csv')
    archival_identity = read(root/'old-rule-equivalence.csv')
    same = len(equivalence)==10 and all(
        all(r[key]=='true' for key in ('hashes', 'formal_candidate_sequence', 'transport_receipts'))
        for r in equivalence)
    old_same = len(archival_identity)==20 and all(
        r['state_equal']=='true' and r['rng_equal']=='true' for r in archival_identity)
    counts = Counter(r['group'] for r in safety)
    if set(counts) != {'K0','K1','K2','L0','L1','L2'} or set(counts.values()) != {5}:
        raise ValueError('Expected five independent checkpoints for each of six fixed groups')
    if set(return_slot) != counts.keys() or set(return_slot.values()) != {23}:
        raise ValueError('Missing returning positions in the fixed matrix')
    if len(south) != 8*len(counts) or len(perf) != 5*4:
        raise ValueError('Missing southern or timed checkpoints')
    errors = {key: sum(int(r[key]) for r in safety) for key in SAFETY}
    evidence = {}
    accepted = []
    for background, before, after, expected in (('D0', 'K0', 'K2', 2769), ('D2', 'L0', 'L2', 2330)):
        pair = comparisons[f'{before}-{after}']
        prior, latest = (sum(int(row['missing']) for row in south if row['group'] == group)
                         for group in (before, after))
        consumption = int(pair['after_missing_grain'])
        army_safe = int(baxi[after]['city_missing']) == int(baxi[after]['losses']) == 0
        north = float(perf[after,'north-snow']['p95'])/float(perf[before,'north-snow']['p95'])
        alerts = [dict(checkpoint=name, p95_change_percent=100*(float(r['p95'])/float(
            perf[before,name]['p95'])-1)) for (variant, name), r in perf.items()
            if variant==after and float(r['p95'])>float(perf[before,name]['p95'])*1.30]
        admitted = (not any(errors.values()) and same and old_same and int(pair['new_shortages'])==0
            and consumption < int(pair['before_missing_grain']) and consumption<=expected and latest<prior
            and army_safe and north<=1.30)
        if admitted:
            accepted.append(background)
        evidence[background] = dict(fixed_pair=pair, southern_shortage_before=prior, southern_shortage_after=latest,
            exact_baxi_march_and_city_safe=army_safe, north_snow_p95_ratio=north, performance_warnings=alerts,
            qualified_for_24_month_observation=admitted)
    result = dict(stage='fixed', engine_sha=args.engine, errors=errors, exact_prior_runs_preserved=old_same,
        pure_cache_equivalence=same, admitted_backgrounds=accepted, evidence=evidence,
        scope='24-month matched observation; later balances require their own stage evidence')
    to_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
