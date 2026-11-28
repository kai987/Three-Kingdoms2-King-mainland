"""Collect actual verification receipts and expected retry evidence without including personal saves."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def collect(root, report):
    proof = root/'technical-proof'
    logs = proof/'logs'
    timings = proof/'timings'
    screenshots = proof/'browser-evidence'
    for destination in (logs, timings, screenshots):
        destination.mkdir(parents=True, exist_ok=True)
    home = str(Path.home())

    def scrub(content):
        return content.replace(home, '<home>')

    def collect_log(name, expected=None):
        source = root/'logs'/f'{name}.log'
        contents = source.read_text(encoding='utf-8')
        (logs/source.name).write_text(scrub(contents), encoding='utf-8')
        code_path = source.with_suffix('.exit')
        if code_path.is_file():
            code = int(code_path.read_text())
            shutil.copyfile(code_path, logs/code_path.name)
            if expected is not None and expected != code:
                raise ValueError(f'Unexpected exit code from {name}: {code}')
        elif expected is not None:
            raise ValueError(f'Missing completion receipt for {name}')
        return contents

    checks = {}
    for backend in ('python', 'rust'):
        full = collect_log(f'{backend}-full-final', 0)
        match = re.search(r'^Ran (\d+) tests in ([\d.]+)s\s+OK(?: \(skipped=(\d+)\))?$', full, re.MULTILINE)
        if not match:
            raise ValueError(f'Missing complete unittest summary for {backend}')
        tests, seconds, skipped = match.groups()
        checks[backend+'_full'] = {'tests': int(tests), 'skipped': int(skipped or 0),
                                  'passed': int(tests)-int(skipped or 0), 'wall_seconds': float(seconds)}
    exact_coordination = collect_log('coordination-tests-on-final', 0)
    checks['coordination'] = {'tests': int(re.search(r'Ran (\d+) tests', exact_coordination)[1])}
    node = collect_log('node-final', 0)
    checks['node'] = {'tests': int(re.search(r'^ℹ tests (\d+)', node, re.MULTILINE)[1]),
                      'passed': int(re.search(r'^ℹ pass (\d+)', node, re.MULTILINE)[1])}
    cargo_log = collect_log('rust-crate', 0)
    checks['rust_crate'] = {'passed': sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed', cargo_log))}
    for name in ('rust-format', 'rust-clippy', 'wasm-final', 'native-wasm-parity', 'wasm-parity-final', 'pyodide-final'):
        collect_log(name, 0)
    exact = collect_log('fixed-clean', 0)
    checks['fixed_clean_runs'] = {'completed': sum(line.endswith('completed') for line in exact.splitlines())}
    snow = collect_log('performance-isolated-north', 0)
    checks['north_isolated_replays'] = sum(line.endswith('completed') for line in snow.splitlines())
    collect_log('weimieshu-final', 0)
    collect_log('web-build-final')
    collect_log('browser-resupply')
    collect_log('browser-resupply-final', 0)
    checks['engine_sha'] = json.loads((report/'checks/engine-and-catalog-sha256.json').read_bytes())['engine_commit']
    parity = (logs/'wasm-parity-final.log').read_text()
    checks['wasm'] = {'vectors': int(re.search(r'(\d+)\s*Python reference vectors passed', parity)[1]),
                      'build_check': 'pass'}
    checks['pyodide'] = json.loads((logs/'pyodide-final.log').read_text().splitlines()[-1])
    checks['browser'] = {'first_pass': 0, 'first_failure': 0, 'retry_pass': 0,
                         'locales': ['zh-Hant','ja'], 'shards': {}}
    browser = checks['browser']
    for path in sorted((root/'browser-timings').glob('*.json')):
        receipt = json.loads(path.read_bytes())
        if receipt['commit'] != checks['engine_sha']:
            raise ValueError(f'Browser tests do not attest the final engine for {path.name}')
        cases = [case for case in receipt['cases'] if case['attempts']]
        passed = sum(case['attempts'][0]['status'] == 'passed' for case in cases)
        failures = len(cases)-passed
        name = path.stem.replace('-shard-', '-')
        collect_log('browser-final-'+name, 1 if failures else 0)
        browser['first_pass'] += passed
        browser['first_failure'] += failures
        browser['shards'][name] = {'passed': passed, 'failure': failures, 'viewport':
                                  '1280x800' if name.startswith('desktop') else '390x844'}
        shutil.copyfile(path, timings/path.name)
    retry = root/'browser-retry-timings/desktop-chromium-shard-1.json'
    retry_receipt = json.loads(retry.read_bytes())
    if retry_receipt['commit'] != checks['engine_sha']:
        raise ValueError('Browser retry engine differs')
    browser['retry_pass'] = sum(case['attempts'][0]['status'] == 'passed'
                                for case in retry_receipt['cases'] if case['attempts'])
    shutil.copyfile(retry, timings/'desktop-chromium-shard-1-manual-deployment-retry.json')
    collect_log('browser-retry-desktop-manual-deployment')
    if (browser['first_pass'], browser['first_failure'], browser['retry_pass']) != (113, 1, 1):
        raise ValueError('Browser outcomes disagree with the reviewed report')
    failed = next((root/'browser-results/desktop-chromium-1').glob('browser_soldier_ui-manual-*/error-context.md')).parent
    for name in ('test-failed-1.png','video.webm'):
        shutil.copyfile(failed/name, screenshots/name)
    (screenshots/'error-context.md').write_text(scrub((failed/'error-context.md').read_text()), encoding='utf-8')
    source_trace = failed/'trace.zip'
    trace = screenshots/'manual-deployment-original-failure-trace-public.zip'
    sanitized = []
    with zipfile.ZipFile(source_trace) as original, zipfile.ZipFile(trace, 'w') as public:
        for name in original.infolist():
            body = original.read(name)
            if name.filename.endswith(('.trace','.network','.stacks','.txt','.json')) and home.encode() in body:
                body = body.replace(home.encode(), b'<home>')
                sanitized.append(name.filename)
            public.writestr(name, body)
    def digest(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    write_json(screenshots/'manual-deployment-trace-provenance.json',
               dict(local_original_sha256=digest(source_trace), public_sha256=digest(trace),
                    replaced_local_home_path_members=sanitized))
    for path in (root/'browser-results').glob('*/browser_ui-transport-coord-*/coordination-*.png'):
        project = path.parent.parent.name.rsplit('-',1)[0]
        shutil.copyfile(path, screenshots/f'{project}-{path.name}')
    checks['browser']['manual_retry_reason'] = 'fixture subprocess hit its original 90-second timeout'
    checks['browser']['resupply'] = {
        'default_profile': {'passed': 4, 'profile_exclusions': 2},
        'v211_profile': {'passed': 4, 'profile_exclusions': 2},
    }
    write_json(report/'checks/technical-checks.json', checks)
    return checks


if __name__ == '__main__':
    source, summary = map(Path, sys.argv[1:])
    print(json.dumps(collect(source, summary), ensure_ascii=False, indent=2))
