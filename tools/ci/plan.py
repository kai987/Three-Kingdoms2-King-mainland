#!/usr/bin/env python3
"""Plan conservative CI scopes from an immutable, trustworthy Git baseline.

This selects work; it does not replace canonical rebuild, fingerprint or report
validation. An unsupported path/identity/baseline always selects full checks.
Main pushes never use event.before or HEAD^ as a deployment baseline.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = 'tk2-test-plan-v1'
GROUPS = ('boot', 'audio', 'map', 'scenarios', 'people', 'economy',
          'logistics', 'battle', 'cloud', 'save')
BASE_GROUPS = {'boot', 'cloud'}
INDEX = 'game/config/campaigns/index.json'
SCENARIO = re.compile(r'game/config/campaigns/scenarios/([0-9]{3})-([0-9]{2})(?:-([a-z][a-z0-9]*(?:-[a-z0-9]+)*))?\.json\Z')
CATALOG = re.compile(r'game/data/campaigns/([^/]+)\.json\Z')
SHA = re.compile(r'[a-f0-9]{40}\Z')
UI = {
    'loading-cover': {'boot', 'audio'}, 'audio': {'boot', 'audio'},
    'browser-engine': set(GROUPS), 'browser-engine-worker': set(GROUPS),
    'paths': set(GROUPS), 'layout': set(GROUPS),
    'map-navigation': {'map'}, 'map-render-cache': {'map'}, 'map-terrain': {'map'},
    'portraits': {'people', 'scenarios'}, 'officer-choice': {'people', 'scenarios'},
    'officer-selection': {'people', 'scenarios', 'battle', 'logistics'}, 'civil-staff': {'people', 'economy'},
    'equipment': {'people', 'economy', 'battle'}, 'equipment-ui': {'people', 'economy'},
    'facilities': {'people', 'economy', 'battle'}, 'facilities-ui': {'people', 'economy', 'battle'}, 'treasury': {'economy', 'logistics'},
    'domestic': {'economy', 'logistics'}, 'march-supply': {'logistics'},
    'route-options': {'map', 'logistics'}, 'events': {'scenarios', 'economy', 'battle'},
    'calendar': {'scenarios', 'economy'}, 'battle-scene': {'battle'}, 'battlefields': {'battle', 'map'},
    'command-books': set(GROUPS),
    'duel-appearance': {'battle', 'people'}, 'cloud-save': {'cloud'},
    'cloud-save-ui': {'cloud'}, 'cloud-recovery': {'cloud'}, 'autosave': {'save'},
    'save-transfer': {'save'}, 'view-cache': set(GROUPS),
    'original-ui': set(GROUPS), 'command-menu': set(GROUPS),
}
GLOBAL_UI = {'game/app.js', 'game/style.css', 'game/i18n.js', 'game/index.html'}
DERIVED_REPORTS = {
    'docs/officer-stat-scenarios-v1.json',
    'docs/scenario-history-audit-20261025.json',
    'docs/ruler-affiliation-audit-20261027.json',
    'docs/retainer-affiliation-audit-20261027.json',
}
SMALL_UI_TESTS = {
    'tests/test_remake_loading_cover.cjs', 'tests/test_remake_site_icon.py',
    'tests/test_remake_audio.cjs', 'tests/test_remake_audio_assets.py',
    'tests/test_remake_audio_commands.cjs', 'tests/test_remake_browser_boot.cjs',
    'tests/test_remake_browser_client.cjs',
}
SHARED_SCENARIO_FIELDS = {
    'rules', 'cities', 'links', 'world', 'city_coordinates', 'added_city_ids',
    'travel_rules', 'travel_routes', 'travel_hazards', 'sea_routes', 'sea_links',
    'exploration_routes', 'river_routes', 'regional_roads', 'road_additions',
    'calendar_rules', 'treasury_rules', 'facility_rules', 'equipment_rules',
    'equipment_initial', 'city_foundings', 'city_retirements', 'city_scale_rules',
}


class Uncertain(ValueError):
    pass


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=30)
    if result.returncode:
        raise Uncertain('Git metadata unavailable: ' + args[0])
    return result.stdout


def commit(repo, value):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise Uncertain('Missing trusted commit')
    resolved = git(repo, 'rev-parse', '--verify', '--end-of-options', value + '^{commit}').decode().strip()
    if not SHA.fullmatch(resolved):
        raise Uncertain('Invalid commit identity')
    return resolved


def blob(repo, revision, path):
    return git(repo, 'show', revision + ':' + path)


def document(repo, revision, path):
    try:
        return json.loads(blob(repo, revision, path))
    except (ValueError, UnicodeError) as error:
        raise Uncertain('Invalid JSON: ' + path) from error


def source_index(repo, revision):
    data = document(repo, revision, INDEX)
    if not isinstance(data, dict) or data.get('schema') != 'tk2-campaign-sources-v1':
        raise Uncertain('Unrecognized canonical scenario index')
    entries = data.get('scenarios')
    if not isinstance(entries, list) or not entries:
        raise Uncertain('Missing canonical scenario inventory')
    mapping, ids = {}, set()
    for row in entries:
        if not isinstance(row, dict) or not isinstance(row.get('file'), str):
            raise Uncertain('Invalid canonical scenario entry')
        path = 'game/config/campaigns/' + row['file']
        match = SCENARIO.fullmatch(path)
        if match is None:
            raise Uncertain('Unrecognized scenario source path')
        year, month, variant = match.groups()
        ident = 'mainland' + year + '-' + month + ('-' + variant if variant else '')
        if (row.get('id') != ident or type(row.get('year')) is not int
                or type(row.get('month')) is not int or not 1 <= row['month'] <= 12
                or (row['year'], row['month']) != (int(year), int(month))
                or path in mapping or ident in ids):
            raise Uncertain('Inconsistent canonical scenario identity')
        mapping[path] = ident
        ids.add(ident)
    if data.get('default') not in ids:
        raise Uncertain('Unrecognized default scenario identity')
    return mapping


def changes(repo, base, head):
    fields = git(repo, 'diff', '--name-status', '-z', '--find-renames', base, head).decode('utf-8').split('\0')
    rows, index = [], 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        if not re.fullmatch(r'[ACDMRTUXB][0-9]*', status):
            raise Uncertain('Unrecognized Git change status')
        count = 2 if status[0] in 'RC' else 1
        if index + count > len(fields) or any(not name for name in fields[index:index + count]):
            raise Uncertain('Truncated Git change inventory')
        names = fields[index:index + count]
        rows.append((status, names))
        index += count
    return rows


def docs_path(path):
    return bool(re.fullmatch(r'README(?:[A-Za-z0-9_.-]*)\.md', path)
                or re.fullmatch(r'docs/(?:[^/]+/)*[^/]+\.md', path))


def stripped(data, *paths):
    value = deepcopy(data)
    for path in paths:
        parent = value
        for key in path[:-1]:
            if not isinstance(parent, dict):
                break
            parent = parent.get(key)
        if isinstance(parent, dict):
            parent.pop(path[-1], None)
    return value


def rule_overrides(source):
    """A local filename cannot hide edits to shared board/math contracts."""
    patch = source.get('overrides', {})
    if not isinstance(patch, dict) or any(key not in ('set', 'update', 'delete') for key in patch):
        raise Uncertain('Invalid local scenario patch')
    replacements, updates, removals = patch.get('set', {}), patch.get('update', {}), patch.get('delete', [])
    if not isinstance(replacements, dict) or not isinstance(updates, dict) or not isinstance(removals, list):
        raise Uncertain('Invalid local scenario patch operations')
    return {key: (key in replacements, replacements.get(key), key in updates,
                  updates.get(key), key in removals) for key in SHARED_SCENARIO_FIELDS}


def fingerprint_only(repo, base, head, path, source_paths):
    before, after = document(repo, base, path), document(repo, head, path)
    if path == 'game/config/route-geometry.json':
        if stripped(before, ('sources',)) != stripped(after, ('sources',)):
            return False
        old, new = before.get('sources'), after.get('sources')
        if not isinstance(old, dict) or not isinstance(new, dict):
            raise Uncertain('Invalid route source fingerprints')
        if old.keys() != new.keys():
            return False
        touched = {key for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
        if not touched or not touched <= source_paths:
            return False
        for name in touched:
            if name in new and new[name] != hashlib.sha256(blob(repo, head, name)).hexdigest():
                raise Uncertain('Stale route source fingerprint: ' + name)
        return True
    key = ('sources', 'catalogs') if path.endswith('map-bridges.json') else ('road_bridges', 'sources', 'catalogs')
    return stripped(before, key) == stripped(after, key)


def make_plan(repo, base, head='HEAD', *, event_name='local', event=None,
              ref=None, force_full=False, publish=False):
    """Return a JSON-only plan; no remote operations or file writes occur here."""
    event = event if isinstance(event, dict) else {}
    reference = ref or event.get('ref', '')
    reasons, changed, selected, groups = [], [], set(), set(BASE_GROUPS)
    full, native, resupply = bool(force_full or event_name == 'schedule'), False, False
    resolved_head, resolved_base = str(head or ''), None
    base_map, head_map, rows = {}, {}, []
    if full:
        reasons.append('Explicit full verification' if force_full else 'Scheduled full verification')
    try:
        resolved_head = commit(repo, head)
        try:
            head_map = source_index(repo, resolved_head)
        except Uncertain:
            # Markdown-only changes do not need to load campaign data. Any
            # non-doc path below still requires a recognized scenario index.
            head_map = {}
        candidate = base
        if event_name == 'pull_request' and not candidate:
            candidate = event.get('pull_request', {}).get('base', {}).get('sha')
        resolved_base = commit(repo, candidate)
        if event_name == 'pull_request':
            resolved_base = commit(repo, git(repo, 'merge-base', resolved_base, resolved_head).decode().strip())
        git(repo, 'merge-base', '--is-ancestor', resolved_base, resolved_head)
        rows = changes(repo, resolved_base, resolved_head)
        changed = sorted({path for _, paths in rows for path in paths})
        if not changed:
            raise Uncertain('Empty diff cannot establish a scoped verification plan')
        if not full and all(docs_path(path) for path in changed):
            return dict(schema=SCHEMA, head=resolved_head, base=resolved_base,
                        mode='docs', full=False, docs_only=True, web=False,
                        native=False, rules=False, soak=False, resupply=False,
                        groups=[], scenario_ids=[], publish=False,
                        python_groups=[],
                        affected_scenario_ids=[], removed_scenario_ids=[],
                        reasons=['Only whitelisted Markdown documentation changed'], changed_files=changed)
        base_map = source_index(repo, resolved_base)
        if not head_map:
            raise Uncertain('Unrecognized head scenario index')
        source_paths = {path for path in changed if SCENARIO.fullmatch(path)}
        for path in source_paths:
            recognized = False
            source_values = []
            for revision, mapping in ((resolved_base, base_map), (resolved_head, head_map)):
                if path not in mapping:
                    continue
                value = document(repo, revision, path)
                if (not isinstance(value, dict) or value.get('schema') != 'tk2-campaign-override-v1'
                        or value.get('id') != mapping[path]):
                    raise Uncertain('Scenario source differs from canonical index: ' + path)
                selected.add(mapping[path])
                recognized = True
                source_values.append(value)
            if not recognized:
                raise Uncertain('Unindexed scenario source: ' + path)
            if len(source_values) == 2 and rule_overrides(source_values[0]) != rule_overrides(source_values[1]):
                full = True
                reasons.append('Local scenario overrides shared board or rule contracts: ' + path)
        derived_catalogs = []
        for path in changed:
            if docs_path(path):
                continue
            if path in source_paths:
                groups.add('scenarios')
                native = True
                reasons.append('Scenario-local source: ' + path)
            elif path == 'game/data/campaigns/index.json':
                old, new = document(repo, resolved_base, path), document(repo, resolved_head, path)
                if (old.get('catalogs') != new.get('catalogs') or old.get('default') != new.get('default')
                        or old.get('schema') != new.get('schema')):
                    full = True
                    reasons.append('Derived scenario inventory/default changed')
                groups.add('scenarios')
            elif CATALOG.fullmatch(path):
                derived_catalogs.append(path)
                groups.add('scenarios')
            elif path == 'game/config/route-geometry.json':
                if fingerprint_only(repo, resolved_base, resolved_head, path, source_paths):
                    groups.update(('map', 'scenarios'))
                    native = True
                    reasons.append('Route source fingerprints only; retain global artifact and save compatibility checks')
                else:
                    full = True
                    reasons.append('Shared route geometry changed')
            elif path == 'game/config/references/scenario-history-review.json':
                old, new = document(repo, resolved_base, path), document(repo, resolved_head, path)
                if any(not isinstance(value, dict) or value.get('schema') != 'tk2-scenario-history-review-v1'
                       or not isinstance(value.get('scenarios'), list) for value in (old, new)):
                    raise Uncertain('Unrecognized historical scenario decision index')
                indexes = []
                for value, mapping in ((old, base_map), (new, head_map)):
                    records = value['scenarios']
                    ids = [row.get('id') for row in records if isinstance(row, dict)]
                    if len(ids) != len(records) or len(set(ids)) != len(ids) or not set(ids) <= set(mapping.values()):
                        raise Uncertain('Unindexed historical scenario decision')
                    indexes.append(dict(zip(ids, records)))
                if old.get('fictional_excluded') != new.get('fictional_excluded'):
                    full = True
                    reasons.append('Historical/fictional scenario inventory changed')
                selected.update(ident for ident in indexes[0].keys() | indexes[1].keys()
                                if indexes[0].get(ident) != indexes[1].get(ident))
                groups.add('scenarios')
                reasons.append('Historical decision ledger; retain global report consistency checks')
            elif path in ('game/assets/map-bridges.json', 'game/assets/map-presentation.json'):
                if fingerprint_only(repo, resolved_base, resolved_head, path, source_paths):
                    reasons.append('Generated map catalog fingerprints only')
                    groups.add('map')
                else:
                    groups.update(('map', 'scenarios'))
                    reasons.append('Shared map presentation changed: ' + path)
            elif (path == 'game/config/battlefield-city-bindings.json'
                  or path.startswith(('game/assets/battlefields/', 'tools/battlefields/'))):
                groups.update(('battle', 'map'))
                reasons.append('Original battlefield artwork or display-only city binding: ' + path)
            elif (path.startswith(('source/remake/', 'crates/', 'tools/ci/', '.github/'))
                  or path.startswith('game/config/') or path in ('game/build_campaigns.py', 'game/build_web.py', 'game/serve.py')
                  or path.endswith(('requirements.txt', 'pyproject.toml', 'Cargo.toml', 'Cargo.lock'))):
                full = True
                reasons.append('Shared rules, compiler, configuration or CI input: ' + path)
            elif path in GLOBAL_UI or path.startswith('game/locales/'):
                groups.update(GROUPS)
                resupply = True
                reasons.append('Global browser UI: ' + path)
            elif path.startswith('game/') and '/' not in path[5:] and Path(path).suffix in ('.js', '.css'):
                module = Path(path).stem
                if module in ('march-core', 'march-worker'):
                    full = True
                    reasons.append('Shared native/route adapter: ' + path)
                elif module in UI:
                    groups.update(UI[module])
                    resupply |= 'logistics' in UI[module]
                    reasons.append('Browser module: ' + path)
                else:
                    raise Uncertain('Unrecognized browser module: ' + path)
            elif path.startswith(('game/assets/loading/', 'art/loading-cover-', 'art/site-icon-')) or path in (
                    'game/favicon.ico', 'game/favicon.svg') or re.fullmatch(r'game/assets/site-icon-[0-9]+\.png', path):
                groups.update(('boot', 'audio'))
                reasons.append('Standalone cover or site icon: ' + path)
            elif path.startswith('game/assets/audio/'):
                groups.update(('boot', 'audio'))
                reasons.append('Original audio asset: ' + path)
            elif path.startswith(('game/assets/battle-', 'game/assets/duel-')):
                groups.update(('battle', 'people'))
                reasons.append('Battle artwork: ' + path)
            elif path.startswith(('game/assets/portraits/', 'game/assets/civil-portraits/')):
                groups.update(('people', 'scenarios'))
                reasons.append('Portrait asset: ' + path)
            elif path.startswith(('game/assets/equipment-icons/', 'game/assets/original-ui/')):
                groups.update(('people', 'economy', 'battle'))
                reasons.append('Equipment/original UI asset: ' + path)
            elif path in DERIVED_REPORTS:
                groups.add('scenarios')
                reasons.append('Generated scenario audit; retain global report consistency checks')
            elif path == 'tests/browser_resupply.spec.mjs' or path == 'tests/browser_resupply_fixture.py':
                groups.add('logistics')
                resupply = True
            elif path == 'tests/browser_ui.spec.mjs':
                groups.update(GROUPS)
                resupply = True
            elif path in SMALL_UI_TESTS:
                groups.update(('boot', 'audio'))
                reasons.append('Cover/audio/browser bootstrap regression: ' + path)
            else:
                raise Uncertain('Unrecognized changed path: ' + path)
        # The source index is structural, including removed/renamed IDs. Keep
        # both inventories visible in full plans for removed-ID negative checks.
        if INDEX in changed or set(base_map.values()) != set(head_map.values()):
            full = True
            reasons.append('Canonical scenario inventory/date/default changed')
        for path in derived_catalogs:
            identities = set()
            values = []
            for revision, mapping in ((resolved_base, base_map), (resolved_head, head_map)):
                expected = {ident for source, ident in mapping.items()
                            if Path(source).name == Path(path).name}
                if not expected:
                    continue
                value = document(repo, revision, path)
                if not isinstance(value, dict) or value.get('id') not in expected:
                    raise Uncertain('Generated catalog differs from indexed identity: ' + path)
                identities.add(value['id'])
                values.append(value)
            if not identities:
                raise Uncertain('Unindexed generated catalog: ' + path)
            if len(values) == 2 and stripped(values[0], ('travel_rules', 'geometry_sha256')) == stripped(values[1], ('travel_rules', 'geometry_sha256')):
                native = True
                reasons.append('Generated catalog identity fingerprint only: ' + path)
            else:
                if not identities <= selected:
                    full = True
                    reasons.append('Generated gameplay data changed without its local canonical source: ' + path)
                selected.update(identities)
                native = True
        if not full and not selected and native:
            # Compatibility fixtures use217 even when its identity changed only
            # transitively; a zero-ID backend plan would accidentally omit it.
            selected.add('mainland217-07') if 'mainland217-07' in head_map.values() else selected.update(head_map.values())
    except (Uncertain, OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
        full = True
        reasons.append('Fail closed: ' + str(error))
    affected = sorted(selected)
    removed = sorted(set(base_map.values()) - set(head_map.values()))
    if full:
        groups = set(GROUPS)
        native = resupply = True
        selected = set()
    elif 'scenarios' in groups and not selected:
        selected.update(head_map.values())
    elif not selected <= set(head_map.values()):
        full = True
        groups = set(GROUPS)
        native = resupply = True
        selected = set()
        reasons.append('Retired/unknown scenario selection requires full verification')
    should_publish = event_name == 'push' and reference == 'refs/heads/main'
    should_publish |= bool(publish and force_full and event_name == 'workflow_dispatch'
                           and reference == 'refs/heads/main')
    if publish and not (force_full and event_name == 'workflow_dispatch' and reference == 'refs/heads/main'):
        reasons.append('Explicit publish ignored outside manual full verification on main')
    return dict(schema=SCHEMA, head=resolved_head, base=resolved_base,
                mode='full' if full else 'scoped', full=full, docs_only=False,
                web=True, native=native, rules=full, soak=full, resupply=resupply,
                groups=[name for name in GROUPS if name in groups],
                python_groups=['all'] if full else ['global', 'scenarios', 'compat'] if native else ['global'],
                scenario_ids=sorted(selected), affected_scenario_ids=affected,
                removed_scenario_ids=removed, publish=bool(should_publish),
                reasons=list(dict.fromkeys(reasons)), changed_files=changed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base')
    parser.add_argument('--head', default=os.environ.get('GITHUB_SHA', 'HEAD'))
    parser.add_argument('--event-name', default=os.environ.get('GITHUB_EVENT_NAME', 'local'))
    parser.add_argument('--event-path', default=os.environ.get('GITHUB_EVENT_PATH'))
    parser.add_argument('--ref', default=os.environ.get('GITHUB_REF'))
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--force-full', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(argv)
    event, event_error = {}, None
    if args.event_path:
        try:
            event = json.loads(Path(args.event_path).read_text())
            if not isinstance(event, dict):
                raise ValueError('Event must be an object')
        except (OSError, ValueError) as error:
            event_error = 'Invalid event metadata: ' + str(error)
    full = args.force_full or args.event_name == 'schedule' or event_error is not None
    base = args.base
    lookup_error = None
    if not base and args.event_name == 'push' and (args.ref or event.get('ref')) == 'refs/heads/main' and not full:
        try:
            from published_base import resolve_published_base
            base = resolve_published_base(args.repository, exclude_head=commit(Path.cwd(), args.head))['sha']
        except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, TypeError, KeyError, AttributeError) as error:
            lookup_error = str(error)
    plan = make_plan(Path.cwd(), base, args.head, event_name=args.event_name,
                     event=event, ref=args.ref, force_full=full, publish=args.publish)
    for reason in (event_error, lookup_error):
        if reason:
            plan['reasons'].append(reason)
    print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
