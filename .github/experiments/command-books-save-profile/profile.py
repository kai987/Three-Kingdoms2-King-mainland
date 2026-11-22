import csv
import json
import math
from pathlib import Path
from statistics import median
import sys


TITLE = 'faction command books can all be spent in one city and survive save reload'
DEVICES = ('desktop-chromium', 'touch-chromium')
METRICS = ('worker_ms', 'response_bridge_ms', 'json_ms', 'playwright_return_ms',
           'evaluate_ms', 'byte_count_ms')


def patch():
    path = Path('tests/browser_ui.spec.mjs')
    before = path.read_text()
    marker = f"test('{TITLE}',async({{page}},testInfo)=>{{\n"
    if before.count(marker) != 1:
        raise ValueError('Cannot locate the original command-books test')
    prefix, body = before.split(marker)
    case, separator, suffix = body.partition('\n});\n')
    before_read = 'const current=await read(),row=budget(current);'
    if not separator or case.count(before_read) != 1 or 'for(let index=0;index<total;index++){' not in case:
        raise ValueError('Cannot locate the spending loop')
    # Return the complete save, leaving every command and assertion intact.
    start = ' const profile=await (await import(process.env.TK2_COMMAND_BOOKS_PROBE)).profileCommandBooks(page,testInfo);\n'
    updated = case.replace(before_read, 'const current=await profile.read(index+1),row=budget(current);')
    path.write_text(prefix + marker + start + updated + '\n await profile.finish();' + separator + suffix)


def suite_specs(suites):
    for suite in suites:
        yield from suite.get('specs', [])
        yield from suite_specs(suite.get('suites', []))


def single_file(folder, name):
    matches = list(folder.rglob(name))
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one {name} in {folder}')
    return json.loads(matches[0].read_text())


def report(directory):
    lines = [
        'Each row covers the 26 original full-save reads inside the spending loop.',
        'Worker is postMessage to reply event. JSON is native Response.json() including body decoding.',
        'Playwright return is the elapsed time from just before returning the entire save in the page to its receipt in Node.',
        '',
        '| Device | Requests | Bytes total | Bytes min–max | Worker | Browser JSON | Playwright return | Evaluate total | Case total |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    with (directory / 'request-timings.csv').open('w', newline='') as handle:
        keys = ['device', 'round', 'bytes', 'browser_ms', *METRICS]
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        details = []
        for device in DEVICES:
            folder = directory / device
            result = single_file(folder, 'playwright.json')
            specs = list(suite_specs(result['suites']))
            if len(specs) != 1 or specs[0]['title'] != TITLE or len(specs[0]['tests']) != 1:
                raise ValueError(f'Unexpected test selection for {device}')
            test = specs[0]['tests'][0]
            attempts = test['results']
            if test['projectName'] != device or len(attempts) != 1 or attempts[0]['status'] != 'passed':
                raise ValueError(f'{device} did not pass exactly once')
            rows = single_file(folder, 'command-books-timings.json')
            if [r['round'] for r in rows] != list(range(1, 27)):
                raise ValueError(f'{device} does not have 26 ordered replies')
            for row in rows:
                if not isinstance(row['bytes'], int) or row['bytes'] <= 0 or any(
                    not math.isfinite(row[k]) or row[k] < (-2 if k == 'playwright_return_ms' else 0)
                    for k in ('browser_ms', *METRICS)
                ):
                    raise ValueError(f'Invalid timing sample for {device}')
                writer.writerow(dict(device=device, **row))
            proof = single_file(folder, 'command-books-identity-and-ledgers.json')
            if (proof['spent']['used'] != 26 or len(proof['spent']['orders']) != 26 or
                    proof['next']['used'] != 0 or proof['rng_before'] != proof['rng_after_spending']):
                raise ValueError(f'Missing original save evidence for {device}')
            sizes = [row['bytes'] for row in rows]
            totals = {k: sum(row[k] for row in rows) for k in METRICS}
            def seconds(key):
                return f'{totals[key]/1000:.3f}s'

            lines.append(
                f'| {device} | 26 | {sum(sizes):,} | {min(sizes):,}–{max(sizes):,} | '
                f'{seconds("worker_ms")} | {seconds("json_ms")} | {seconds("playwright_return_ms")} | '
                f'{seconds("evaluate_ms")} | {attempts[0]["duration"]/1000:.3f}s |'
            )
            details.append(f'{device} per-read medians (ms): ' + ', '.join(
                f'{k}={median(r[k] for r in rows):.3f}' for k in METRICS
            ))
    lines.extend(['', *details])
    text = '\n'.join(lines) + '\n'
    (directory / 'summary.md').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    if sys.argv[1:] == ['patch']:
        patch()
    elif len(sys.argv) == 3 and sys.argv[1] == 'report':
        report(Path(sys.argv[2]))
    else:
        raise SystemExit('Usage: profile.py patch | report OUTPUT_DIRECTORY')
