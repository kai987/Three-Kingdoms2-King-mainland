"""Validate both variants and summarize observed worker and Playwright time."""
import csv
import json
from pathlib import Path
import math
import re
import sys

root = Path(sys.argv[1])
endpoints = ('/api/save', '/api/state')
labels = ('initial', 'after-inspection', 'after-quotes', 'after-purchase', 'after-reload')
save_only = {'after-inspection', 'after-quotes'}
runs = []
requests = []
checkpoints = []
rng_by_device = {}

def read(path):
    return json.loads(path.read_bytes())

def specs(suites):
    for suite in suites:
        yield from suite.get('specs', ())
        yield from specs(suite.get('suites', ()))

def write_csv(name, rows):
    with (root/name).open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

for device in ('desktop-chromium', 'touch-chromium'):
    for variant in ('baseline', 'save-only'):
        folder = root/f'{device}-{variant}'
        testdata = read(folder/'playwright.json')
        spec, = specs(testdata['suites'])
        assert spec['title'].startswith('actual equipment appears in city intelligence')
        test, = spec['tests']
        outcome, = test['results']
        assert test['projectName'] == device and outcome['status'] == 'passed'
        assert testdata['stats']['expected'] == 1
        assert all(testdata['stats'][key] == 0 for key in ('unexpected', 'skipped', 'flaky'))
        profile = read(folder/'equipment-profile.json')
        reads = profile['reads']
        assert tuple(row['label'] for row in reads) == labels
        for row in reads:
            assert row['saveOnly'] == (variant == 'save-only' and row['label'] in save_only)
            assert all(math.isfinite(row[key]) and row[key] >= 0 for key in ('browserMs', 'returnMs'))
            assert re.fullmatch(r'[a-f0-9]{64}', row['saveChecksum'])
        assert reads[0]['saveChecksum'] == reads[1]['saveChecksum'] == reads[2]['saveChecksum']
        assert reads[3]['saveChecksum'] == reads[4]['saveChecksum']
        rng = profile['rng']
        assert rng['initial'] and rng['initial'] == rng['purchased'] == rng['restored']
        if device in rng_by_device:
            assert rng == rng_by_device[device]
        rng_by_device[device] = rng
        for row in reads:
            checkpoints.append(dict(device=device, variant=variant, **row))
        expected = {(endpoint, row['label']) for endpoint in endpoints for row in reads
                    if endpoint == '/api/save' or not row['saveOnly']}
        observed = {}
        for row in profile['requests']:
            label = row['checkpoint']
            finish = row.get('received')
            rtt = None if finish is None else finish - row['sent']
            decode = sum(t['finished']-t['started'] for t in row['decodes'])
            if label:
                key = (row['endpoint'], label)
                assert key not in observed and rtt is not None and rtt >= 0
                assert row['status'] == 200 and row['bodyUtf16Units'] > 0 and not row['compact']
                assert len(row['decodes']) == 1 and row['decodes'][0]['method'] == 'json'
                observed[key] = (rtt, decode)
            requests.append(dict(device=device, variant=variant, document=row['document'],
                checkpoint=label or 'page', endpoint=row['endpoint'], request_id=row['id'],
                status=row.get('status'), compact=row['compact'],
                worker_rtt_ms=None if rtt is None else round(rtt, 3),
                decode_method=','.join(t['method'] for t in row['decodes']),
                decode_ms=round(decode, 3) if row['decodes'] else None,
                body_utf16_units=row.get('bodyUtf16Units')))
        assert set(observed) == expected
        metrics = dict(device=device, variant=variant, test_ms=outcome['duration'])
        for endpoint in endpoints:
            kind = endpoint.split('/')[-1]
            items = [pair for key, pair in observed.items() if key[0] == endpoint]
            metrics[kind+'_direct'] = len(items)
            metrics[kind+'_worker_ms'] = round(sum(x[0] for x in items), 3)
            metrics[kind+'_json_ms'] = round(sum(x[1] for x in items), 3)
            metrics[kind+'_page'] = sum(row['checkpoint'] is None and row['endpoint'] == endpoint
                                        for row in profile['requests'])
        pairs = [row for row in reads if row['label'] in save_only]
        metrics['all_returns_ms'] = round(sum(row['returnMs'] for row in reads), 3)
        metrics['read_only_returns_ms'] = round(sum(row['returnMs'] for row in pairs), 3)
        metrics['read_only_elapsed_ms'] = round(sum(row['browserMs']+row['returnMs'] for row in pairs), 3)
        runs.append(metrics)

write_csv('comparison.csv',runs)
write_csv('checkpoints.csv',checkpoints)
write_csv('requests.csv',requests)
print('| Device | Variant | Test (s) | Save/state test reads | Worker save/state (s) | JSON save/state (s) | Return for the two checks (s) |')
print('| --- | --- | ---: | ---: | ---: | ---: | ---: |')
for row in runs:
    print(f"| {row['device']} | {row['variant']} | {row['test_ms']/1000:.3f} | "
          f"{row['save_direct']}/{row['state_direct']} | {row['save_worker_ms']/1000:.3f}/{row['state_worker_ms']/1000:.3f} | "
          f"{row['save_json_ms']/1000:.3f}/{row['state_json_ms']/1000:.3f} | {row['read_only_returns_ms']/1000:.3f} |")
print()
print('All four targeted cases passed, with independent full saves, unchanged RNG, and exact save restoration.')
