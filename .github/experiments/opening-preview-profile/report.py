from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import csv
import json
import sys

folder = Path(sys.argv[1])
registry = json.loads(Path('tools/browser-tests/cases.json').read_bytes())
case, = [row for row in registry['cases'] if row['id'] == 'opening-catalog-first']
scenarios = case['scenario_ids']
catalog = {}
for scenario in scenarios:
    data = json.loads(Path(f"game/data/campaigns/{scenario.removeprefix('mainland')}.json").read_bytes())
    assert data['id'] == scenario
    catalog[scenario] = set(data['active_cities'])
assert len(scenarios) == 18 and sum(map(len, catalog.values())) == 2140

def specs(suites):
    for suite in suites:
        yield from suite.get('specs', [])
        yield from specs(suite.get('suites', []))

def identity(path):
    query = parse_qs(urlsplit(path).query, strict_parsing=True)
    return query['scenario'][0], query['city'][0]

def seconds(rows, key):
    return sum(row[key] for row in rows) / 1000

def interval(rows, start, end):
    return sum(row[end]-row[start] for row in rows) / 1000

def collect(device):
    data = json.loads((folder/device/'opening-profile.json').read_bytes())
    execution = json.loads((folder/device/'playwright.json').read_bytes())
    spec, = specs(execution['suites'])
    assert spec['title'] == case['title'] and spec['ok']
    test, = spec['tests']
    result, = test['results']
    assert test['projectName'] == device and result['status'] == 'passed' and result['retry'] == 0
    measured = data['scenarios']
    assert [row['scenario'] for row in measured] == scenarios
    assert all(row['cities'] == len(catalog[row['scenario']]) for row in measured)
    city_requests = [row for row in data['pageRows'] if row['path'].startswith('/api/city-preview?')]
    direct = [row for row in city_requests if row['explicit']]
    ui = [row for row in city_requests if not row['explicit']]
    assert Counter(identity(row['path']) for row in direct) == Counter(
        (scenario, city) for scenario, cities in catalog.items() for city in cities)
    worker = {row['id']:row for row in data['workerRows']['completed']}
    assert len(worker) == len(data['workerRows']['completed'])
    assert all(row['status'] == worker[row['id']]['status'] == 200 and worker[row['id']]['path'] == row['path']
               for row in direct)
    raw_saves = [row for row in data['pageRows'] if row['path'] == '/api/save']
    measured_saves = [worker[row['id']] for row in raw_saves if row['id'] in worker]
    assert all(row['status'] == 200 for row in measured_saves)
    preview = [row['preview'] for row in measured]
    received_ui = [row for row in ui if row.get('received') is not None]
    timed_ui = [worker[row['id']] for row in received_ui if row['id'] in worker]
    direct_worker = [worker[row['id']] for row in direct]
    phases = dict(device=device, playwright_s=result['duration']/1000,
        measured_case_s=data['elapsedMs']/1000, initial_opening_s=data['bootMs']/1000,
        scenarios=len(measured), city_requests=len(city_requests), direct_city_requests=len(direct),
        ui_city_requests=len(ui), ui_city_replies=len(received_ui), ui_city_replies_worker_timed=len(timed_ui),
        direct_worker_s=interval(direct_worker, 'entered', 'exited'),
        ui_worker_s=interval(timed_ui, 'entered', 'exited'),
        worker_round_trip_s=interval(direct, 'sent', 'received'),
        browser_fetch_s=seconds(preview, 'fetchMs'), browser_json_s=seconds(preview, 'jsonMs'),
        browser_evaluate_s=seconds(preview, 'callbackMs'),
        playwright_return_s=seconds(preview, 'returnMs'), evaluate_total_s=seconds(preview, 'evaluateMs'),
        open_scenarios_s=seconds(measured, 'openingMs'),
        save_download_s=seconds(measured, 'downloadMs'),
        save_file_read_s=seconds(measured, 'saveReadMs'), save_json_s=seconds(measured, 'saveJsonMs'),
        save_requests=len(raw_saves), save_requests_worker_timed=len(measured_saves),
        save_worker_s=interval(measured_saves, 'entered', 'exited'),
        clock_sample_rtt_ms=data['clock']['rttMs'])
    by_scenario = []
    for row in measured:
        scenario = row['scenario']
        selected = [a for a in direct if identity(a['path'])[0] == scenario]
        by_scenario.append(dict(device=device, scenario=scenario, count=len(selected),
            worker_s=interval([worker[a['id']] for a in selected], 'entered', 'exited'),
            worker_round_trip_s=interval(selected, 'sent', 'received'),
            browser_json_s=row['preview']['jsonMs']/1000,
            playwright_return_s=row['preview']['returnMs']/1000,
            evaluate_s=row['preview']['evaluateMs']/1000, open_s=row['openingMs']/1000,
            save_download_s=row['downloadMs']/1000, save_file_read_s=row['saveReadMs']/1000,
            save_json_s=row['saveJsonMs']/1000, scenario_s=row['scenarioMs']/1000))
    return phases, by_scenario

def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        out = csv.DictWriter(stream, fieldnames=rows[0])
        out.writeheader()
        out.writerows({key: round(value,3) if isinstance(value,float) else value
                       for key,value in row.items()} for row in rows)

totals, details = [], []
for device in ('desktop-chromium', 'touch-chromium'):
    summary, rows = collect(device)
    totals.append(summary)
    details.extend(rows)
write_csv(folder/'summary.csv',totals)
write_csv(folder/'scenarios.csv',details)
(folder/'summary.json').write_text(json.dumps(totals,indent=2)+'\n')
print('| Device | Cases (s) | City requests (explicit/UI) | Preview Worker (s) | Browser JSON (s) | Playwright return (s) | Scenario opening (s) | Save download/read/parse (s) |')
print('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |')
for row in totals:
    print(f"| {row['device']} | {row['playwright_s']:.2f} | {row['direct_city_requests']}/{row['ui_city_requests']} | "
          f"{row['direct_worker_s']:.2f} | {row['browser_json_s']:.2f} | {row['playwright_return_s']:.2f} | "
          f"{row['open_scenarios_s']:.2f} | "
          f"{row['save_download_s']+row['save_file_read_s']+row['save_json_s']:.2f} |")
