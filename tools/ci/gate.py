#!/usr/bin/env python3
"""Validate a scope plan, required job outcomes and the immutable release."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

GROUPS = frozenset(('boot', 'audio', 'map', 'scenarios', 'people', 'economy',
                    'logistics', 'battle', 'cloud', 'save'))
FLAGS = ('full', 'docs_only', 'web', 'native', 'rules', 'soak', 'resupply', 'publish')
JOBS = ('docs-check', 'source-and-browser', 'native-rules', 'scoped-tests',
        'campaign-rules', 'campaign-soak', 'web-build', 'browser-ui', 'resupply-ui')
SHA = re.compile(r'^[a-f0-9]{40}(?:[a-f0-9]{24})?$')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_plan(plan, head=None):
    if not isinstance(plan, dict) or plan.get('schema') != 'tk2-test-plan-v1':
        raise ValueError('Unknown test plan schema')
    if not SHA.fullmatch(str(plan.get('head', ''))) or head and plan['head'] != head:
        raise ValueError('Test plan belongs to a different commit')
    if plan.get('mode') not in ('docs', 'scoped', 'full'):
        raise ValueError('Unknown test plan mode')
    if any(type(plan.get(key)) is not bool for key in FLAGS):
        raise ValueError('Test plan flags must be explicit booleans')
    groups, scenarios = plan.get('groups'), plan.get('scenario_ids')
    python_groups = plan.get('python_groups')
    if (not isinstance(groups, list) or any(not isinstance(group, str) for group in groups)
            or len(set(groups)) != len(groups) or not set(groups) <= GROUPS):
        raise ValueError('Unknown or duplicate test groups')
    if (not isinstance(scenarios, list) or any(not isinstance(value, str)
            or not re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in scenarios)
            or len(set(scenarios)) != len(scenarios)):
        raise ValueError('Invalid scenario identities')
    if (not isinstance(python_groups, list) or any(not isinstance(value, str) for value in python_groups)
            or len(set(python_groups)) != len(python_groups)
            or not set(python_groups) <= {'global', 'scenarios', 'compat', 'all'}):
        raise ValueError('Invalid Python scope groups')
    if plan['docs_only'] != (plan['mode'] == 'docs') or plan['full'] != (plan['mode'] == 'full'):
        raise ValueError('Contradictory plan mode')
    if plan['docs_only']:
        if groups or scenarios or python_groups or any(plan[key] for key in FLAGS if key != 'docs_only'):
            raise ValueError('Documentation plans cannot run or publish a game release')
    elif not plan['web'] or not groups:
        raise ValueError('Runtime changes require a nonempty browser scope and a build')
    if plan['full'] and (set(groups) != GROUPS or not all(plan[key] for key in
                         ('native', 'rules', 'soak', 'resupply')) or python_groups != ['all']):
        raise ValueError('Full plans must retain every regression gate')
    if (plan['rules'] or plan['soak']) and not plan['native']:
        raise ValueError('Rules and cross-backend replays require the native reference')
    if plan['mode'] == 'scoped' and ('global' not in python_groups or 'all' in python_groups):
        raise ValueError('Scoped Python checks must retain the global contracts')
    if scenarios and 'scenarios' not in groups:
        raise ValueError('Scenario IDs require a browser scenario group')
    if set(python_groups) & {'scenarios', 'compat'} and not plan['native']:
        raise ValueError('Scenario data and save compatibility require the native reference')
    return plan


def required_jobs(plan):
    validate_plan(plan)
    return {
        'docs-check': plan['docs_only'],
        'source-and-browser': plan['web'],
        'native-rules': plan['native'],
        'scoped-tests': plan['mode'] == 'scoped',
        'campaign-rules': plan['rules'],
        'campaign-soak': plan['soak'],
        'web-build': plan['web'],
        'browser-ui': plan['web'],
        'resupply-ui': plan['resupply'],
    }


def verify_jobs(plan, needs):
    if not isinstance(needs, dict) or needs.get('scope', {}).get('result') != 'success':
        raise ValueError('Scope selection did not succeed')
    expected = required_jobs(plan)
    if set(needs) != set(JOBS) | {'scope'}:
        raise ValueError('Missing or unregistered verification jobs')
    for name, required in expected.items():
        result = needs[name].get('result')
        if required and result != 'success':
            raise ValueError(f'Required job {name} did not succeed: {result}')
        if not required and result not in ('skipped', 'success'):
            raise ValueError(f'Unexpected unsuccessful job {name}: {result}')
    return expected


def verify_artifact(root, head, expected_hash=None):
    root = Path(root)
    identity = read_json(root / 'runtime/build.json')
    if identity.get('schema') != 'tk2-static-build-v1' or identity.get('commit') != head:
        raise ValueError('Release identity does not match the tested commit')
    files = identity.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Empty release inventory')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Release contains a symlink')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(files) | {'runtime/build.json'}:
        raise ValueError('Release has missing or unexpected files')
    for name, record in files.items():
        relative = PurePosixPath(name)
        if (relative.is_absolute() or '..' in relative.parts or '\\' in name
                or not isinstance(record, dict)):
            raise ValueError('Unsafe release inventory')
        raw = (root / relative).read_bytes()
        if (type(record.get('bytes')) is not int or len(raw) != record['bytes']
                or hashlib.sha256(raw).hexdigest() != record.get('sha256')):
            raise ValueError(f'Release file changed: {name}')
    encoded = (json.dumps(files, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode()
    digest = hashlib.sha256(encoded).hexdigest()
    if digest != identity.get('content_sha256') or expected_hash and digest != expected_hash:
        raise ValueError('Release differs from the artifact used by browser acceptance')
    return identity


def summary(plan):
    required = required_jobs(plan)
    lines = ['## Test scope', '', f'Commit: `{plan["head"]}`',
             f'Mode: **{plan["mode"]}**',
             'Groups: ' + ', '.join(f'`{group}`' for group in plan['groups']),
             'Python groups: ' + ', '.join(f'`{group}`' for group in plan['python_groups']),
             'Scenarios: ' + (', '.join(f'`{value}`' for value in plan['scenario_ids']) or 'global checks / group defaults'),
             f'Publication requested: `{str(plan["publish"]).lower()}`', '',
             '| Job | Required |', '| --- | --- |']
    lines.extend(f'| {name} | {"yes" if run else "not needed for this scope"} |'
                 for name, run in required.items())
    # JSON fencing escapes filenames as data rather than rendering their Markdown.
    explanation = json.dumps({'base': plan.get('base'), 'reasons': plan.get('reasons', []),
                              'changed_files': plan.get('changed_files', [])},
                             ensure_ascii=True, indent=2).replace('`', '\\u0060')
    lines += ['', '```json', explanation, '```', '']
    return '\n'.join(lines)


def check_docs(plan, root=Path('.')):
    validate_plan(plan)
    if not plan['docs_only'] or not SHA.fullmatch(str(plan.get('base', ''))):
        raise ValueError('Documentation checks require a verified base and docs-only plan')
    root = Path(root)
    subprocess.run(['git', 'diff', '--check', plan['base'], plan['head']], cwd=root, check=True)
    changed = subprocess.check_output(['git', 'diff', '--name-only', '--diff-filter=ACMR',
                                      '-z', plan['base'], plan['head']], cwd=root).decode().split('\0')
    for name in filter(None, changed):
        path = root / name
        if path.suffix.lower() != '.md':
            raise ValueError('Non-documentation file in a documentation-only change')
        text = re.sub(r'```[\s\S]*?```', '', path.read_text(encoding='utf-8'))
        text = re.sub(r'`[^`\n]*`', '', text)
        for match in re.finditer(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', text):
            target = match.group(1).strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            linked = root / unquote(url.path).lstrip('/') if url.path.startswith('/') else path.parent / unquote(url.path)
            if not linked.exists():
                raise ValueError(f'Broken repository link in {name}: {target}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('outputs', 'summary', 'verify', 'artifact', 'docs'))
    parser.add_argument('--plan')
    parser.add_argument('--needs')
    parser.add_argument('--head')
    parser.add_argument('--root')
    parser.add_argument('--content-sha256')
    args = parser.parse_args(argv)
    if args.command == 'artifact':
        identity = verify_artifact(args.root, args.head, args.content_sha256)
        print(identity['content_sha256'])
        return 0
    plan = validate_plan(read_json(args.plan), args.head)
    if args.command == 'outputs':
        for key in FLAGS:
            print(f'{key}={str(plan[key]).lower()}')
        print(f'mode={plan["mode"]}')
    elif args.command == 'summary':
        print(summary(plan))
    elif args.command == 'docs':
        check_docs(plan)
        print('Documentation links and whitespace passed')
    else:
        verify_jobs(plan, read_json(args.needs))
        print('Every check required by this scope succeeded:', plan['head'])
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print(f'CI gate rejected: {error}', file=sys.stderr)
        raise SystemExit(1)
