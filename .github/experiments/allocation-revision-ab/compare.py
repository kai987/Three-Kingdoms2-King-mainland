"""Verify the four test runs and report the eight observations per run."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
metrics = []
report = {}
expected_identity = {
    'paid-allocation-raw-save.json': 'e445f091c8dac5181f0d2e446900532856e01553e64d67648ebd59d4d12265f2',
    'paid-allocation-three-officer-ledgers.json': 'fbee45f994fea0433ee0092b24d1f5ef3c9c43d6a2aadb78332fc7e9da12978b',
}

def load(path):
    return json.loads(path.read_bytes())

def specs(suites):
    for suite in suites:
        yield from suite.get('specs', ())
        yield from specs(suite.get('suites', ()))

for device in ('desktop', 'touch'):
    for variant in ('baseline', 'warm'):
        evidence = root / f'{device}-chromium-{variant}'
        result = load(evidence/'playwright.json')
        assert result['stats']['expected'] == 1
        assert all(result['stats'][key] == 0 for key in ('unexpected', 'skipped', 'flaky'))
        spec, = specs(result['suites'])
        test, = spec['tests']
        outcome, = test['results']
        assert outcome['status'] == 'passed'
        for name, digest in expected_identity.items():
            assert hashlib.sha256((evidence/name).read_bytes()).hexdigest() == digest
        ledger = load(evidence/'paid-allocation-three-officer-ledgers.json')
        atomic, = (entry for entry in ledger if entry['source'] == 'three-local-drafts-final-atomic-confirmation')
        assert (atomic['revision_before'], atomic['revision_after'], len(atomic['batch'])) == (6, 7, 3)
        assert all(atomic[key] is True for key in (
            'next_preserved_save_and_revision',
            'cancel_confirmation_preserved_all_drafts',
            'closing_unpaid_draft_preserved_save_and_revision',
        ))
        rows = load(evidence/'allocation-revision-ab.json')
        assert len(rows) == len({row['id'] for row in rows}) == 8
        assert [row['revision'] for row in rows] == [6, 6, 6, 6, 6, 6, 7, 7]
        worker_ms = parse_ms = 0
        for position, row in enumerate(rows, 1):
            assert row['status'] == 200
            assert row['sent'] <= row['received'] <= row['parseStart'] <= row['parseEnd']
            assert row['bodyUtf16Units'] > 0
            if variant == 'warm':
                assert re.fullmatch(r'[0-9a-f]{64}:[0-9a-f]{64}',row['cacheToken'])
                assert row['transport'] == 'tk2-view-v1'
                assert not row['staticCatalog'] and not row['travelQuotes']
            else:
                assert row['cacheToken'] is None and row['transport'] is None
                assert not row['staticCatalog'] and row['travelQuotes']
            worker = row['received'] - row['sent']
            parse = row['parseEnd'] - row['parseStart']
            worker_ms += worker
            parse_ms += parse
            metrics.append(dict(
                device=device, variant=variant, read=position, id=row['id'],
                revision=row['revision'], utf16_units=row['bodyUtf16Units'],
                worker_ms=round(worker,3), json_parse_ms=round(parse,3),
                test_ms=outcome['duration'],
            ))
        report[device,variant] = (
            sum(row['bodyUtf16Units'] for row in rows), worker_ms, parse_ms, outcome['duration'],
        )

print('| Device | Variant | UTF-16 units (8 reads) | Worker RTT (ms) | JSON parse (ms) | Test (ms) |')
print('| --- | --- | ---: | ---: | ---: | ---: |')
for (device,variant),(units,worker,parse,test) in report.items():
    print(f'| {device} | {variant} | {units} | {worker:.1f} | {parse:.1f} | {test} |')
print()
print('All four runs passed and matched the original save and allocation ledger hashes.')
print('All eight fresh Worker replies matched per device: 6, 6, 6, 6, 6, 6, 7, 7.')
with (root/'revision-timings.csv').open('w', newline='') as out:
    writer=csv.DictWriter(out,fieldnames=metrics[0].keys())
    writer.writeheader()
    writer.writerows(metrics)
