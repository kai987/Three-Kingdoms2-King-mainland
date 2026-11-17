from pathlib import Path
import csv
import json
import sys

root = Path(sys.argv[1])
load = lambda path: json.loads(Path(path).read_bytes())
case, = [r for r in load('tools/browser-tests/cases.json')['cases'] if r['id']=='opening-catalog-first']
expected = {}
for scenario in case['scenario_ids']:
    catalog = load(f"game/data/campaigns/{scenario.removeprefix('mainland')}.json")
    assert catalog['id'] == scenario
    expected[scenario] = sorted(catalog['active_cities'])
assert len(expected) == 18 and sum(map(len,expected.values())) == 2140

def specs(suites):
    for suite in suites:
        yield from suite.get('specs',[])
        yield from specs(suite.get('suites',[]))

def collect(device, mode):
    folder = root/f'{device}-{mode}'
    spec, = specs(load(folder/'playwright.json')['suites'])
    assert spec['ok'] and spec['title'] == case['title']
    test, = spec['tests']
    result, = test['results']
    assert test['projectName']==device and result['status']=='passed' and result['retry']==0
    raw = load(folder/'opening-shared-trial.json')
    assert raw['shared'] == (mode=='shared')
    views, saves, worker = [raw[k] for k in ('views','saves','workerRows')]
    assert [v['scenario'] for v in views] == [w['scenario'] for w in worker] == [None, *expected]
    assert [r['scenario'] for r in saves] == list(expected)
    assert all(sorted(r['cities'])==expected[r['scenario']] for r in saves)
    by_scenario = []
    for i,(view, row) in enumerate(zip(views, worker)):
        assert view['status'] == row['status'] == 200
        assert len(view['viewProof']) == 64
        assert bool(view['sharedToken']) == row['shared'] == raw['shared']
        assert row['shared_sent'] == view['sharedSent']
        by_scenario.append(dict(device=device,mode=mode,stage='opening' if i else 'bootstrap',scenario=view['scenario'],
                 **{k:v for k,v in row.items() if k!='scenario'}, body_bytes=view['bodyBytes'],
                 worker_roundtrip_ms=view['received']-view['sent'],browser_hydrate_ms=view['hydrateMs']))
    if raw['shared']:
        assert len({x['sharedToken'] for x in views}) == 1
        assert worker[0]['shared_sent'] and not worker[0]['shared_worker_hit']
        assert all(r['shared_worker_hit'] and r['shared_browser_hit'] and not r['shared_sent'] for r in worker[1:])
    return raw, by_scenario

summary, detail = [], []
for device in ('desktop-chromium','touch-chromium'):
    base, old_rows = collect(device,'baseline')
    shared, new_rows = collect(device,'shared')
    assert [(r['scenario'],r['input'],r['viewProof']) for r in base['views']] == [
        (r['scenario'],r['input'],r['viewProof']) for r in shared['views']], device
    assert base['saves'] == shared['saves'], device
    for rows in (old_rows,new_rows):
        detail.extend(rows)
        for stage, selected in [('bootstrap',rows[:1]),('opening',rows[1:]),('all',rows)]:
            times={key.removesuffix('_ms')+'_s':sum(row[key] for row in selected)/1000
                   for key in selected[0] if key.endswith('_ms')}
            summary.append(dict(device=device, mode=rows[0]['mode'], stage=stage,
                **times, requests=len(selected),
                body_bytes=sum(row['body_bytes'] for row in selected),
                static_worker_hits=sum(row['static_worker_hit'] for row in selected),
                shared_worker_hits=sum(row['shared_worker_hit'] for row in selected),
                shared_browser_hits=sum(row['shared_browser_hit'] for row in selected),
                shared_sent=sum(row['shared_sent'] for row in selected)))
for name, rows in [('summary.csv',summary),('scenarios.csv',detail)]:
    with (root/name).open('w',newline='') as stream:
        out=csv.DictWriter(stream,fieldnames=rows[0].keys())
        out.writeheader()
        out.writerows(rows)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('Both device pairs matched 19 ordered complete hydrated views and 18 complete saves.')
print('| Device | Mode | Opening pack (s) | Worker Python dispatch (s) | Opening reply bytes | Shared hits (Worker/browser) |')
print('| --- | --- | ---: | ---: | ---: | ---: |')
for r in summary:
    if r['stage']=='opening':
        print(f"| {r['device']} | {r['mode']} | {r['pack_s']:.3f} | {r['python_s']:.3f} | {r['body_bytes']} | "
              f"{r['shared_worker_hits']}/{r['shared_browser_hits']} |")
