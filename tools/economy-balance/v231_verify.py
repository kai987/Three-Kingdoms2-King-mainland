"""Reconcile the portable report, checksums and actual supply ledgers."""
from argparse import ArgumentParser
from collections import Counter
import csv
from hashlib import file_digest
import json
from math import isclose
from pathlib import Path
from zipfile import ZipFile


KEY=('wave','group','scenario','seed','strategy')


def records(path):
    with path.open(encoding='utf-8',newline='') as stream:
        yield from csv.DictReader(stream)


def sha256(path):
    with path.open('rb') as stream:
        return file_digest(stream,'sha256').hexdigest()


def identity(row):
    return tuple(row[k] for k in KEY)


def compare_rate(row,column,numerator,denominator):
    if denominator:
        assert isclose(float(row[column]),100*numerator/denominator),(identity(row),column)
    else:
        assert row[column]=='null',(identity(row),column)


def summary(root):
    data=root/'data'
    manifest=json.loads((data/'validation-manifest.json').read_text())
    for item in manifest['files']:
        member=root/item['path']
        assert member.stat().st_size==item['bytes'] and sha256(member)==item['sha256'],item['path']
    checksum_file=root/'SHA256SUMS.txt'
    for line in checksum_file.read_text().splitlines():
        expected,relative=line.split('  ',1)
        assert sha256(root/relative)==expected,relative
    needs={}
    totals={}
    for row in records(data/'military-grain-request-ledger.csv'):
        episode=(*identity(row),row['episode'])
        assert episode not in needs,episode
        needs[episode]=Counter(requested=int(row['requested_grain']),timely=int(row['timely_received_grain']),
                               late=int(row['late_received_grain']),remaining=int(row['remaining_unmet_grain']))
        assert needs[episode]['requested']==sum(needs[episode][k] for k in ('timely','late','remaining')),episode
        if row['winter']=='true':
            aggregate=totals.setdefault(identity(row),Counter())
            aggregate.update(requests=1,received=needs[episode]['timely'],requested=needs[episode]['requested'])
    credits={}
    for row in records(data/'military-grain-receipt-ledger.csv'):
        episode=(*identity(row),row['episode'])
        credited=int(row['credited'])
        assert needs[episode] and 0<credited<=int(row['actual']),episode
        kind='timely' if row['timely']=='true' else 'late'
        credits.setdefault(episode,Counter())[kind]+=credited
    for episode,need in needs.items():
        assert all((credits.get(episode) or Counter())[k]==need[k] for k in ('timely','late')),episode
    for row in records(data/'winter-grain-timely-comparison.csv'):
        total=totals.get(identity(row),Counter())
        assert int(row['requests'])==total['requests'],identity(row)
        assert int(row['requested_grain'])==total['requested'],identity(row)
        assert int(row['timely_received_grain'])==total['received'],identity(row)
        compare_rate(row,'timely_grain_rate',total['received'],total['requested'])
        compare_rate(row,'timely_order_rate',int(row['timely_positive_receipt_orders']),int(row['matured_orders']))
    n=0
    for row in records(data/'forecast-double-count-audit.csv'):
        assert row['exact_cost_split']=='true',row['seed']
        n+=1
    state=json.loads((data/'report-status.json').read_text())
    assert n>=240 and state['warehouse_mismatches']==0
    print(json.dumps(dict(files=len(manifest['files']),episodes=len(needs),
                          fixed_routes=n,requested_runs=state['required_campaign_runs'],
                          completed_runs=state['required_campaign_runs']-len(state['missing_runs'])),ensure_ascii=False))


def archives(folder):
    verification=json.loads((folder/'archive-index.json').read_text())
    for entry in verification['archives']:
        path=folder/entry['file']
        assert path.stat().st_size==entry['bytes']<100_000_000
        assert sha256(path)==entry['sha256']
        with ZipFile(path) as source:
            assert source.testzip() is None and len(source.namelist())==entry['files']
            manifest=next(name for name in source.namelist() if name.endswith('/SHA256SUMS.txt'))
            for line in source.read(manifest).decode().splitlines():
                checksum,member=line.split('  ',1)
                with source.open(member) as stream:
                    assert file_digest(stream,'sha256').hexdigest()==checksum,member
    print(json.dumps(dict(archives=len(verification['archives']),members=len(verification['files']))))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('summary_root',type=Path)
    parser.add_argument('--archives',type=Path)
    args=parser.parse_args()
    summary(args.summary_root)
    if args.archives:
        archives(args.archives)
