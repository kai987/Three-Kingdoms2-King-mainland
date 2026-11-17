from pathlib import Path
import csv
import json
import sys

out = Path(sys.argv[1])
load = lambda path: json.loads(Path(path).read_bytes())
case, = [r for r in load('tools/browser-tests/cases.json')['cases'] if r['id']=='opening-catalog-first']
expected = {}
for scenario in case['scenario_ids']:
    catalog = load(f"game/data/campaigns/{scenario.removeprefix('mainland')}.json")
    assert catalog['id'] == scenario
    expected[scenario] = sorted(catalog['active_cities'])
assert len(expected) == 18 and sum(map(len,expected.values())) == 2140

def all_specs(suites):
    for suite in suites:
        yield from suite.get('specs',[])
        yield from all_specs(suite.get('suites',[]))

def measure(device):
    p = out/device
    test = load(p/'playwright.json')
    spec, = all_specs(test['suites'])
    assert spec['title']==case['title'] and spec['ok']
    case_result, = spec['tests']
    result, = case_result['results']
    assert case_result['projectName']==device and result['status']=='passed' and result['retry']==0
    profile = load(p/'opening-start-profile.json')
    worker = {r['id']: r for r in profile['workerRows']}
    python = {r['scenario']: r for r in profile['python']}
    assert len(profile['rows']) == len(worker) == len(python) == 18
    assert [r['scenario'] for r in profile['rows']] == list(expected)
    rows = []
    for row in profile['rows']:
        scenario = row['scenario']
        assert sorted(row['cities']) == expected[scenario]
        b = row['browser']
        w = worker[b['id']]
        py = python[scenario]
        assert b['status'] == w['status'] == 200
        assert len(py['new_ms']) == len(py['view_ms']) == len(py['decorate_ms']) == len(py['session_ms']) == len(py['catalog_ms']) == len(py['pack_ms']) == len(py['encode_ms']) == 1
        assert b['eventOpens'] and b['eventCloses'] and b['renders'] and b['sawBusy']
        assert b['click'] <= b['sent'] <= b['received'] <= b['eventOpens'][0] <= b['eventCloses'][-1]
        assert abs(row['totalMs']-sum(row[k] for k in ('clickMs','idleMs','eventWaitMs','eventDismissMs'))) < 0.01
        view = sum(py['view_ms'])+sum(py['decorate_ms'])
        session = sum(py['session_ms'])
        init = session-view
        assert init >= sum(py['new_ms']) and w['ms']+2 >= py['dispatch_ms']
        assert w['scenario'] == scenario and w['dispatch'] >= w['entered']
        queue = w['dispatch']-w['entered']
        assert w['ms'] + 2 >= py['dispatch_ms'] + w['jsCatalogMs'] + queue
        rows.append(dict(device=device,scenario=scenario,cities=len(row['cities']),opening_ms=row['totalMs'],
            click_ms=row['clickMs'],playwright_wait_idle_ms=row['idleMs'],event_wait_visible_ms=row['eventWaitMs'],
            event_dismiss_ms=row['eventDismissMs'], worker_inside_ms=w['ms'], worker_roundtrip_ms=b['received']-b['sent'],
            worker_initialize_ms=init, construct_state_ms=sum(py['new_ms']), worker_initial_view_ms=view,
            worker_other_ms=w['ms']-session, worker_queue_ms=queue,
            js_catalog_ms=w['jsCatalogMs'], python_catalog_ms=sum(py['catalog_ms']),
            worker_pack_ms=sum(py['pack_ms']), worker_json_encode_ms=sum(py['encode_ms']),
            worker_unattributed_ms=w['ms']-session-queue-w['jsCatalogMs']-sum(
                py['catalog_ms']+py['pack_ms']+py['encode_ms']),
            app_render_ms=sum(r['end']-r['start'] for r in b['renders']), render_calls=len(b['renders']),
            browser_layout_ms=row['layoutMs'],browser_style_ms=row['styleMs'],
            browser_reply_to_busy_clear_ms=b['busyCleared']-b['received'],
            browser_busy_clear_to_event_ms=b['eventOpens'][0]-b['busyCleared'],
            browser_event_open_to_close_ms=b['eventCloses'][-1]-b['eventOpens'][0]))
    summary={key:sum(r[key] for r in rows)/1000 for key in rows[0] if key.endswith('_ms')}
    summary={key.removesuffix('_ms')+'_s':value for key,value in summary.items()}
    summary.update(device=device,case_s=result['duration']/1000,opening_count=len(rows),
                   cities=sum(r['cities'] for r in rows), render_calls=sum(r['render_calls'] for r in rows))
    return summary,rows

summary, detail = [], []
for device in ('desktop-chromium','touch-chromium'):
    row, rows = measure(device)
    summary.append(row)
    detail.extend(rows)
for name, rows in [('summary.csv',summary),('scenarios.csv',detail)]:
    with (out/name).open('w',newline='') as handle:
        csvout=csv.DictWriter(handle,fieldnames=rows[0].keys())
        csvout.writeheader()
        csvout.writerows({key:round(value,4) if isinstance(value,float) else value
                          for key,value in row.items()} for row in rows)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('| Device | Start total (s) | Worker init (s) | Initial view (s) | App render (s) | Wait for event after idle (s) | Event dismissal (s) |')
print('| --- | ---: | ---: | ---: | ---: | ---: | ---: |')
for r in summary:
    print(f"| {r['device']} | {r['opening_s']:.2f} | {r['worker_initialize_s']:.2f} | {r['worker_initial_view_s']:.2f} | "
          f"{r['app_render_s']:.2f} | {r['event_wait_visible_s']:.2f} | {r['event_dismiss_s']:.2f} |")
