"""Validate the targeted Playwright results and summarize the recorded phases."""
import csv
import json
import math
from pathlib import Path
import sys

root = Path(sys.argv[1])
endpoints = ('/api/save', '/api/state')
labels = ('initial', 'after-inspection', 'after-quotes', 'after-purchase', 'after-reload')
readonly = {'after-inspection', 'after-quotes'}
table = []

def read(path):
    return json.loads(path.read_bytes())

def specs(suites):
    for suite in suites:
        yield from suite.get('specs', ())
        yield from specs(suite.get('suites', ()))

def total(values):
    return round(sum(values), 2)

print('## Equipment checkpoint timings')
print()
print('| Device | Endpoint | Direct requests | Worker RTT (ms) | Browser JSON (ms) | Endpoint-only replay to Playwright (ms) |')
print('| --- | --- | ---: | ---: | ---: | ---: |')
notes = []
for device in ('desktop-chromium', 'touch-chromium'):
    folder = root/device
    result = read(folder/'playwright.json')
    spec, = specs(result['suites'])
    test, = spec['tests']
    outcome, = test['results']
    assert test['projectName'] == device and outcome['status'] == 'passed'
    assert result['stats']['expected'] == 1
    assert all(result['stats'][key] == 0 for key in ('unexpected', 'skipped', 'flaky'))
    data = read(folder/'equipment-profile.json')
    reads = data['reads']
    assert tuple(row['label'] for row in reads) == labels
    assert reads[0]['saveChecksum'] and reads[0]['revision'] is not None
    for read_row in reads:
        assert all(math.isfinite(n) and n >= 0 for n in (
            read_row['browserMs'], read_row['pairedMs'], *read_row['endpointMs'].values(),
        ))
        if read_row['label'] in readonly:
            assert read_row['saveChecksum'] == reads[0]['saveChecksum']
            assert read_row['revision'] == reads[0]['revision']
    probe_rows = {}
    for row in data['requests']:
        label = row['checkpoint']
        end = row.get('received')
        rtt = None if end is None else end - row['sent']
        decode = sum(item['finished'] - item['started'] for item in row['decodes'])
        assert rtt is None or rtt >= 0
        if label:
            assert (row['endpoint'],label) not in probe_rows
            assert end is not None and row['status'] == 200 and row['bodyUtf16Units'] > 0
            assert not row['compact'] and len(row['decodes']) == 1
            assert row['decodes'][0]['method'] == 'json'
            probe_rows[row['endpoint'], label] = (rtt, decode)
        table.append(dict(device=device, document=row['document'], checkpoint=label or 'page',
            endpoint=row['endpoint'], request_id=row['id'], compact=row['compact'],
            status=row.get('status'), worker_rtt_ms=None if rtt is None else round(rtt,3),
            decode_method=','.join(item['method'] for item in row['decodes']),
            decode_ms=round(decode,3) if row['decodes'] else None,
            body_utf16_units=row.get('bodyUtf16Units')))
    assert set(probe_rows) == {(endpoint,label) for endpoint in endpoints for label in labels}
    for endpoint in endpoints:
        worker = total(probe_rows[endpoint,n][0] for n in labels)
        parsed = total(probe_rows[endpoint,n][1] for n in labels)
        returned = total(row['endpointMs'][endpoint] for row in reads)
        print(f'| {device} | {endpoint} | 5 | {worker:.2f} | {parsed:.2f} | {returned:.2f} |')
    redundant = [row for row in reads if row['label'] in readonly]
    paired = total(row['pairedMs'] for row in reads)
    pairs_elapsed = total(row['browserMs']+row['pairedMs'] for row in redundant)
    repeated_state = {
        'worker_ms':total(probe_rows['/api/state',label][0] for label in readonly),
        'json_ms':total(probe_rows['/api/state',label][1] for label in readonly),
        'endpoint_replay_ms':total(row['endpointMs']['/api/state'] for row in redundant),
    }
    page_counts = {endpoint:len([row for row in data['requests'] if row['endpoint']==endpoint and row['checkpoint'] is None])
                   for endpoint in endpoints}
    notes.append((device, outcome['duration'], paired, pairs_elapsed, repeated_state, page_counts))
print()
for device, duration, paired, read_wall, state, page_counts in notes:
    print(f'- {device}: test {duration} ms, original paired returns {paired} ms, '
          f'two read-only pairs {read_wall} ms, their unused views {state}, other page request counts {page_counts}.')
with (root/'requests.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=table[0].keys())
    writer.writeheader()
    writer.writerows(table)
