"""Verify the archived convoy cases and retain their actual evidence."""
from argparse import ArgumentParser
from collections import Counter
from contextlib import ExitStack
from hashlib import sha256
from io import TextIOWrapper
from pathlib import Path
import csv
import gzip
import json
import zipfile

from common import to_csv, to_json
from v302_experiments import PRIOR

CONVOYS = frozenset({1723,1902,2095})


def archived(archive, output):
    validation = json.loads(archive.read('data/validation-manifest.json'))
    results = []
    with ExitStack() as stack:
        opened = {}
        for item in validation['archived_convoys']:
            path = Path(item['archive'])
            ident = item['convoy']
            if not path.is_file():
                results.append(dict(convoy=ident,status='not_verified',reason='original_archive_missing',
                                    required=str(path), member=item['member']))
                continue
            if path not in opened:
                expected = item['archive_sha256']
                with path.open('rb') as stream:
                    import hashlib
                    actual = hashlib.file_digest(stream,'sha256').hexdigest()
                if actual != expected:
                    raise ValueError(f'Archive SHA-256 differs for {path}')
                opened[path] = stack.enter_context(zipfile.ZipFile(path))
            raw = opened[path].read(item['member'])
            actual = sha256(raw).hexdigest()
            if actual != item['member_sha256']:
                raise ValueError(f'Historical convoy {ident} checksum mismatch')
            folder = output/f'convoy-{ident}'
            folder.mkdir(parents=True,exist_ok=True)
            target=folder/Path(item['member']).name
            target.write_bytes(raw)
            results.append(dict(convoy=ident,status='archived_receipt_verified',archive=str(path),member=item['member'],
                                archive_sha256=item['archive_sha256'],member_sha256=actual,
                                copied=str(target.relative_to(output))))
    for member in ('convoy-1706.json','node-decisions.json','regression-check.json'):
        raw=archive.read('historical/convoy-1706/'+member)
        folder=output/'convoy-1706'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/member).write_bytes(raw)
    return results


def hunger_cases(archive,output):
    case = 'observed/w221/R2-211/2026/240/184-02/'
    flows = dict()
    for file in ('convoy-survival.csv','convoy-terminal-events.csv','convoy-events.csv',
                 'transport-progress-daily.csv.gz','emergency-transport-decisions.csv',
                 'convoy-ledger.csv.gz','convoy-resolution-daily.csv.gz','emergency-local-refills.csv'):
        with ExitStack() as stack:
            body = stack.enter_context(archive.open(case+file))
            data = stack.enter_context(gzip.GzipFile(fileobj=body)) if file.endswith('.gz') else body
            stream = stack.enter_context(TextIOWrapper(data,encoding='utf-8',newline=''))
            reader = csv.DictReader(stream)
            rows = [row for row in reader if int(row.get('convoy_id',row.get('convoy')) or 0) in CONVOYS]
            if rows:
                to_csv(output/f'184-02-convoy-evidence/{Path(file).stem.removesuffix(".csv")}.csv',rows)
            flows[file] = rows
    outcomes = {int(row['convoy_id']):row for row in flows['convoy-survival.csv']}
    if set(outcomes) != CONVOYS:
        raise ValueError('Missing 184-02 historical convoy evidence')
    return [dict(convoy=ident,status='archived_receipt_verified',
                 archive=case,return_hunger=int(outcome['escort_hunger_loss'])+int(outcome['reserve_hunger_loss']),
                 actual_end=outcome['terminal_status'],actual_city=outcome['actual_position'],
                 original_escort=int(outcome['initial_escort']),living_escort=int(outcome['current_escort']))
            for ident,outcome in sorted(outcomes.items())]


def main():
    cli=ArgumentParser(description=__doc__)
    cli.add_argument('output',type=Path)
    cli.add_argument('--prior',type=Path,default=PRIOR)
    cli.add_argument('--disabled-replay',type=Path)
    args=cli.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.prior) as archive:
        rows=archived(archive,args.output)+hunger_cases(archive,args.output)
    new = args.disabled_replay/'regression-check.json' if args.disabled_replay else None
    old=args.output/'convoy-1706/regression-check.json'
    if new and new.is_file():
        fields=('terminal','owners','departure_alternative','loss')
        legacy, replay = (json.loads(path.read_text()) for path in (old,new))
        matches={key:legacy[key]==replay[key] for key in fields}
        state='matched' if all(matches.values()) else 'different'
        (args.output/'convoy-1706/v302-disabled-regression-check.json').write_bytes(new.read_bytes())
    else:
        state,matches='pending_or_not_verified',{}
    to_json(args.output/'historical-convoys.json',dict(
        records=rows, disabled_1706=dict(status=state, fields=matches),
        scope='Archived receipts plus any newly completed disabled replay; distinct from feature-on controlled tests.'))
    print(json.dumps(dict(counts=dict(Counter(row['status'] for row in rows)),disabled_1706=state),ensure_ascii=False))


if __name__=='__main__':
    main()
