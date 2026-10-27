#!/usr/bin/env python3
"""Validate the frozen retainer review without modifying game data.

Compiled catalogues and canonical people are inputs, never regenerated here.
The authored reference retains the pre-change evidence. --write writes only
the JSON/Japanese reports; --check compares their exact bytes without writes.
Regional game proxies and estimated dates are not primary-source postings.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace

# Read-only checking must not leave import caches in the checkout even when
# the caller omits Python's -B flag.
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ruler_audit import (city_names, date_parts, indexed, is_fictional,
                         material_totals, read, require, text, urls)
from remake.dated_events import validate_source, visible_factions

REFERENCE = ROOT / 'game/config/references/retainer-affiliation-review.json'
CATALOG_DIR = ROOT / 'game/data/campaigns'
PEOPLE = ROOT / 'game/config/campaigns/people.json'
REPORT_JSON = ROOT / 'docs/retainer-affiliation-audit-20261027.json'
REPORT_MD = ROOT / 'docs/retainer-affiliation-audit-20261027.md'
EXPECTED_BASE_PEOPLE = 1030
EXPECTED_PEOPLE = 1052
EXPECTED_SCENARIOS = 29
EXPECTED_HISTORICAL = 23
EXPECTED_FICTIONAL = 6
EXPECTED_SCOPE = 25
FIRST_NEW_RUNTIME = 1031
WANG_JIAN_PERSON = 'historical-wang-jian-liaodong'
WANG_JIAN_RUNTIME = 1044
WANG_JIAN_LOYALTY_SOURCE = dict(value=59, display='59', source_faction_label='袁绍右侧空城',
    faction_ids=[], reference='game/config/references/cnblogs-officer-stats.json',
    source_row_id='cnblogs-line-0229')
STATE_FIELDS = ('status', 'faction', 'city', 'ruler', 'troops')
CHRONOLOGY_FIELDS = ('birth_year', 'service_year', 'death_year', 'chronology_basis')
CHRONOLOGY_OVERRIDES = {*CHRONOLOGY_FIELDS, 'chronology_design', 'scenario_chronology_override'}


def digest(value):
    """Canonical JSON digest; independent of source indentation/key order."""
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':')).encode('utf-8')).hexdigest()


def source_note(row, label, *, required=True):
    text(row.get('note'), label + ' note')
    urls(row.get('source_urls'), label, required=required)


def check_people(canonical, review):
    order, people = canonical.get('order'), canonical.get('people')
    require(canonical.get('schema') == 'tk2-campaign-people-v1'
            and isinstance(order, list) and isinstance(people, dict),
            'Canonical person source shape differs')
    require(len(order) == EXPECTED_PEOPLE and len(set(order)) == len(order)
            and set(order) == set(people), 'Canonical person count/identity differs')
    require(review.get('base_person_count') == EXPECTED_BASE_PEOPLE
            and review.get('person_count') == EXPECTED_PEOPLE,
            'Frozen person count differs')
    base_order = order[:EXPECTED_BASE_PEOPLE]
    snapshot = dict(order=base_order, people={pid: people[pid] for pid in base_order})
    require(digest(snapshot) == review.get('base_people_snapshot_sha256'),
            'Released 1030-person objects/order changed from frozen snapshot')
    additions = indexed(review.get('new_people'), 'person_id', 'New people')
    require(len(additions) == EXPECTED_PEOPLE - EXPECTED_BASE_PEOPLE
            and set(additions) == set(order[EXPECTED_BASE_PEOPLE:]),
            'New person identities differ from frozen append list')
    runtime_ids = [people[pid].get('runtime_id') for pid in order]
    require(all(type(value) is int for value in runtime_ids)
            and len(set(runtime_ids)) == len(runtime_ids),
            'Canonical runtime identities are invalid/duplicated')
    require(runtime_ids[EXPECTED_BASE_PEOPLE:] == list(range(
                FIRST_NEW_RUNTIME, FIRST_NEW_RUNTIME + len(additions))),
            'New runtime identities must append 1031..1052 without renumbering')
    for pid in order:
        require(people[pid].get('person_id') == pid,
                'Canonical person identity mismatch: ' + str(pid))
    for pid, frozen in additions.items():
        person, label = people[pid], 'New person ' + pid
        for key in ('name', 'runtime_id', 'birth_year', 'service_year', 'death_year'):
            require(frozen.get(key) == person.get(key), label + ': frozen ' + key + ' differs')
        source_note(frozen, label)
        profile, init = person.get('profile', {}), person.get('initialization', {})
        require(profile.get('virtue') == 60 and profile.get('health_max') == 80
                and profile.get('source_stats') == {}, label + ': require authorial V60/H80 and empty source_stats')
        if pid == WANG_JIAN_PERSON:
            require(person['runtime_id'] == WANG_JIAN_RUNTIME and person['name'] == '王建'
                    and frozen.get('health') == 42 and frozen.get('source_stat_person') == pid,
                    label + ': frozen Wang Jian source exception differs')
            require(init.get('health') == 42 and init.get('default_loyalty') == 80
                    and init.get('source_loyalty') == WANG_JIAN_LOYALTY_SOURCE
                    and person.get('configuration', {}).get('health')
                    == 'cnblogs_initial_health_with_remake_compatibility_cap',
                    label + ': Wang Jian requires exact source0229 health42/contextual loyalty59')
        else:
            require(init.get('health') == 80 and init.get('default_loyalty') == 80
                    and init.get('source_loyalty') is None
                    and frozen.get('health', 80) == 80 and not frozen.get('source_stat_person'),
                    label + ': require initial health80/loyalty80 without invented source loyalty')
        require(person.get('configuration', {}).get('is_historical_measurement') is False,
                label + ': game ratings must not claim historical measurements')
        virtue = person.get('virtue_design', {})
        require(virtue.get('source_charisma') is None
                and virtue.get('is_historical_fact') is False,
                label + ': default virtue must not claim source charisma')
        ability = person.get('ability_source', {})
        if pid == WANG_JIAN_PERSON:
            require(ability.get('kind') == 'historical_career_with_reviewed_original_game_stats'
                    and ability.get('original_numeric_reference') == dict(
                        reference='game/config/references/cnblogs-officer-stats.json',
                        source_row_id='cnblogs-line-0229', martial_strength=24, intellect=75,
                        health=42, loyalty=59, original_virtue=41)
                    and profile.get('martial_strength') == 24 and profile.get('intellect') == 75,
                    label + ': reviewed original0229 ability provenance differs')
        else:
            require('authorial' in ability.get('kind', '')
                    and ability.get('original_numeric_reference') is None,
                    label + ': authorial ability provenance required')
        urls(ability.get('source_urls'), label + ' ability', required=True)
        require(set(frozen['source_urls']) <= set(ability['source_urls']),
                label + ': frozen historical sources missing from ability provenance')
        design = person.get('chronology_design')
        require(isinstance(design, dict) and isinstance(design.get('precision'), dict),
                label + ': explicit chronology_design precision required')
        text(design.get('basis'), label + ' chronology design basis')
        for key in ('birth_year', 'service_year', 'death_year'):
            text(design['precision'].get(key), label + ' chronology precision ' + key)
        for key in ('virtue', 'health_max', 'martial_strength', 'intellect', 'terrain_affinity'):
            text(profile.get('basis', {}).get(key), label + ' rating basis ' + key)
    return people, order, additions


def checked_state(row, label):
    require(isinstance(row, dict) and set(row) == set(STATE_FIELDS),
            label + ': complete status/faction/city/ruler/troops required')
    require(type(row['ruler']) is bool and type(row['troops']) is int and row['troops'] >= 0,
            label + ': invalid ruler/troop state')
    return row


def check_catalog(data, decision, canonical_people, order, scope, presentation=None):
    ident = data.get('id')
    require(isinstance(ident, str) and ident == decision.get('id'), 'Scenario identity differs')
    label = ident + ': '
    actual_date = [data['start_year'], data['start_month']]
    require(date_parts(decision.get('date'), ident) == actual_date, label + 'frozen date differs')
    require(type(decision.get('fictional')) is bool and decision['fictional'] == is_fictional(data),
            label + 'historical/IF classification differs')
    notes = decision.get('notes')
    require(isinstance(notes, list) and all(isinstance(note, str) and note.strip() for note in notes),
            label + 'review notes must be text')
    require(not decision['fictional'] or bool(notes), label + 'IF premise/exception notes required')
    people = indexed(data.get('people'), 'person_id', ident + ' people')
    by_runtime = indexed(data['people'], 'runtime_id', ident + ' runtime identities')
    require(list(people) == order, label + 'all canonical people must retain order and one plan each')
    require(data.get('officer_count') == len(people), label + 'catalogue officer_count is stale')
    eras, windows = data.get('era_assignments'), data.get('appearance_windows')
    require(isinstance(eras, dict) and set(eras) == set(people)
            and isinstance(windows, dict) and set(windows) == set(people),
            label + 'every person requires exactly one era and appearance plan')
    for pid, person in people.items():
        require({k: v for k, v in person.items() if k not in CHRONOLOGY_OVERRIDES}
                == {k: v for k, v in canonical_people[pid].items() if k not in CHRONOLOGY_OVERRIDES},
                label + 'compiled person identity/profile/provenance differs: ' + pid)
        era = eras[pid]
        require(era.get('planning_complete') is True
                and isinstance(era.get('appearance_plan'), dict) and bool(era['appearance_plan'])
                and isinstance(windows[pid], list), label + 'incomplete person plan: ' + pid)
        require(era.get('status') in ('serving', 'free', 'chronology_excluded', 'scenario_excluded',
                                     'future', 'dead', 'closed_career'),
                label + 'pending/unknown person state: ' + pid)
        plan = era['appearance_plan']
        require(plan.get('status') in ('serving', 'free', 'future_free', 'excluded',
                                      'future', 'dead', 'closed_career', 'scenario_excluded'),
                label + 'unknown appearance plan state: ' + pid)
        require(len({digest(window) for window in windows[pid]}) == len(windows[pid]),
                label + 'duplicate appearance windows: ' + pid)
        for window in windows[pid]:
            require(isinstance(window, dict), label + 'invalid appearance window: ' + pid)
            start = date_parts(window.get('start'), label + pid + ' window start')
            end = date_parts(window.get('end'), label + pid + ' window end')
            require(start <= end, label + 'reversed appearance window: ' + pid)
        if plan['status'] in ('future_free', 'future'):
            require(era['status'] in ('chronology_excluded', 'future') and bool(windows[pid])
                    and date_parts(plan.get('start'), label + pid + ' future start') > actual_date,
                    label + 'incomplete future appearance plan: ' + pid)
        if plan['status'] in ('excluded', 'dead', 'closed_career', 'scenario_excluded'):
            require(era['status'] in ('chronology_excluded', 'scenario_excluded', 'dead', 'closed_career')
                    and not windows[pid],
                    label + 'excluded person has active appearance plan: ' + pid)
        if era['status'] in ('serving', 'free'):
            require(plan['status'] == era['status'] and plan.get('city') == era.get('city'),
                    label + 'active appearance plan differs: ' + pid)
        for key in ('basis', 'historical_certainty'):
            text(era.get('placement_review', {}).get(key), label + 'placement provenance ' + pid)

    active = set(data['active_cities'])
    cities = indexed(data['cities'], 'id', ident + ' cities')
    require(data.get('city_count') == len(cities), label + 'catalogue city_count is stale')
    require(len(active) == len(data['active_cities']) and active <= set(cities),
            label + 'invalid active cities')
    factions = indexed(data['factions'], 'id', ident + ' factions')
    static = SimpleNamespace(data=data, factions=factions, map_cities=cities,
                             ids={pid: person['runtime_id'] for pid, person in people.items()})
    validate_source(static)
    visible = {row['id']: row for row in visible_factions(static)}
    require(set(data['faction_rulers']) == set(factions), label + 'faction/ruler definitions differ')
    require(all(data['initial_owners'].get(city) in {*visible, 'neutral'} for city in active),
            label + 'unknown/dormant active-city owner')
    require(digest(data['initial_owners']) == decision.get('owners_sha256'),
            label + 'frozen city owners differ')
    require(digest(data['faction_rulers']) == decision.get('faction_rulers_sha256'),
            label + 'frozen faction ruler identities differ')
    opening, city_counts = {}, Counter()
    for status, field in (('serving', 'initial_officers'), ('free', 'initial_free_officers')):
        for row in data[field]:
            pid, city = row.get('person_id'), row.get('city')
            require(pid in people and pid not in opening,
                    label + 'duplicate/unknown opening person: ' + str(pid))
            require(city in active, label + 'opening officer at inactive city: ' + pid)
            faction = data['initial_owners'][city] if status == 'serving' else None
            require(status != 'serving' or faction in visible,
                    label + 'serving officer without active city owner: ' + pid)
            troops = row.get('troops', 0)
            require(type(troops) is int and troops >= 0, label + 'invalid officer troops: ' + pid)
            state = dict(status=status, faction=faction, city=city,
                         ruler=bool(row.get('ruler')), troops=troops)
            require(all(eras[pid].get(key) == state[key] for key in ('status', 'faction', 'city')),
                    label + 'opening/era affiliation differs: ' + pid)
            require(status != 'free' or (not state['ruler'] and troops == 0),
                    label + 'free officer has troops/ruler flag: ' + pid)
            opening[pid] = state
            if status == 'serving':
                city_counts[city] += 1
    require({pid for pid, era in eras.items() if era['status'] in ('serving', 'free')} == set(opening),
            label + 'active era person missing from opening roster')
    require(max(city_counts.values(), default=0) <= 99, label + 'city exceeds 99-person capacity')
    ruler_people = set()
    for fid, faction in factions.items():
        runtime = data['faction_rulers'][fid]
        require(runtime in by_runtime and faction.get('captain') == by_runtime[runtime]['name'],
                label + 'faction captain is not canonical ruler: ' + fid)
        if fid in visible:
            pid, city = by_runtime[runtime]['person_id'], faction['city']
            require(city in active and data['initial_owners'][city] == fid,
                    label + 'ruler capital owner differs: ' + fid)
            require(pid in opening and opening[pid]['status'] == 'serving'
                    and opening[pid]['faction'] == fid and opening[pid]['city'] == city
                    and opening[pid]['ruler'], label + 'ruler not flagged at its own capital: ' + fid)
            ruler_people.add(pid)
        require(faction.get('initial_officers') == sum(
                    row['faction'] == fid for row in opening.values()),
                label + 'faction officer count is stale: ' + fid)
    require({pid for pid, state in opening.items() if state['ruler']} == ruler_people,
            label + 'extraneous/missing opening ruler flags')
    reviewed_factions = indexed(decision.get('factions'), 'id', ident + ' reviewed factions')
    require(set(reviewed_factions) == set(factions) & set(scope),
            label + 'scope faction roster coverage differs')
    faction_rows = []
    for fid, frozen in sorted(reviewed_factions.items()):
        require(frozen.get('city') == factions[fid]['city']
                and frozen.get('ruler') == data['faction_rulers'][fid],
                label + 'frozen faction capital/ruler differs: ' + fid)
        roster = sorted(pid for pid, state in opening.items() if state['faction'] == fid)
        require(frozen.get('person_ids') == roster, label + 'frozen retainer roster differs: ' + fid)
        # Unchanged/dormant roster snapshots can be structure-only evidence.
        # Empty references must never turn into a claim of attested retainers.
        source_note(frozen, label + fid, required=False)
        text(frozen.get('certainty'), label + fid + ' certainty')
        faction_rows.append(dict(frozen, captain=factions[fid]['captain'],
                                 names=[people[pid]['name'] for pid in roster],
                                 dormant=fid not in visible))

    reviews = [era['placement_review'] for era in eras.values()]
    counts = dict(reference_classes=dict(Counter(row['historical_certainty'] for row in reviews)),
                  bases=dict(Counter(row['basis'] for row in reviews)))
    completion, coverage = data['placement_completion'], data['coverage']
    for key, expected in counts.items():
        require(completion.get(key) == expected, label + 'placement counter is stale: ' + key)
    future = sum(era['appearance_plan'].get('status') in ('future_free', 'future') for era in eras.values())
    require(completion.get('schema') == 'tk2-placement-completion-v1'
            and completion.get('complete') is True and completion.get('pending') == 0
            and completion.get('capacity') == 99 and completion.get('people') == len(people)
            and completion.get('future_plans') == future,
            label + 'placement completion summary differs')
    charisma = sum(person['profile'].get('source_stats', {}).get('charisma') is not None
                   for person in people.values())
    expected_coverage = dict(library=len(people), configured_profiles=len(people),
        health_configured=len(people), affinity_configured=len(people), placement_plans=len(people),
        initial_serving=len(data['initial_officers']), planned_serving=len(data['initial_officers']),
        initial_free=len(data['initial_free_officers']), planned_max_city_roster=max(city_counts.values(), default=0),
        future_plans=future, san14_charisma_profiles=charisma, default_virtue_profiles=len(people)-charisma,
        pending_profiles=0, pending_capacity=0, pending_history=0, pending_faction=0)
    for key, expected in expected_coverage.items():
        require(coverage.get(key) == expected, label + 'coverage counter is stale: ' + key)
    optional_coverage = dict(
        san14_abilities=sum(bool(person['profile'].get('source_stats')) for person in people.values()),
        original_initial_health_profiles=sum(person.get('configuration', {}).get('health', '').startswith(
            'cnblogs_initial_health') for person in people.values()),
        retained_original_reference_profiles=sum(person.get('pre_campaign_stat_policy_v1', {}).get(
            'virtue_design', {}).get('status') == 'verified_original' for person in people.values()),
        original_virtue_profiles=0, history_designs_total=0)
    for key, expected in optional_coverage.items():
        if key in coverage:
            require(coverage[key] == expected, label + 'coverage counter is stale: ' + key)
            expected_coverage[key] = expected
    require(coverage.get('pending_factions') == [], label + 'pending factions remain')
    if 'new_historical_people' in coverage:
        require(coverage['new_historical_people'] == len(people)-charisma,
                label + 'coverage counter is stale: new_historical_people')
    material = material_totals(data, active)
    require(decision.get('material') == material, label + 'active-world material conservation differs')

    changes = indexed(decision.get('changes'), 'person_id', ident + ' reviewed changes')
    change_rows = []
    for pid, change in changes.items():
        require(pid in people, label + 'unknown change person: ' + pid)
        before = checked_state(change.get('before'), label + pid + ' before')
        after = checked_state(change.get('after'), label + pid + ' after')
        current = opening.get(pid, dict(status=eras[pid]['status'], faction=eras[pid].get('faction'),
                    city=eras[pid].get('city'), ruler=False, troops=0))
        require(after == current, label + 'frozen change.after differs: ' + pid)
        require(before != after, label + 'recorded change is empty: ' + pid)
        source_note(change, label + pid + ' change')
        text(change.get('certainty'), label + pid + ' certainty')
        change_rows.append(dict(change, name=people[pid]['name']))
    chronology = indexed(decision.get('chronology'), 'person_id', ident + ' chronology')
    chronology_rows = []
    for pid, frozen in chronology.items():
        require(pid in people, label + 'unknown chronology person: ' + pid)
        require(all(key in frozen and frozen[key] == people[pid].get(key) for key in CHRONOLOGY_FIELDS),
                label + 'frozen chronology differs: ' + pid)
        source_note(frozen, label + pid + ' chronology')
        chronology_rows.append(dict(frozen, name=people[pid]['name']))
    return dict(id=ident, date=actual_date, title=data['title'], fictional=decision['fictional'],
                factions=faction_rows, changes=change_rows, chronology=chronology_rows, material=material,
                placement_counts=counts, coverage=expected_coverage, notes=notes,
                city_names=city_names(data, presentation or {}),
                owners_sha256=decision['owners_sha256'], faction_rulers_sha256=decision['faction_rulers_sha256'])


def build_report(reference_path=REFERENCE, catalog_dir=CATALOG_DIR, people_path=PEOPLE):
    reference_path, catalog_dir, people_path = map(Path, (reference_path, catalog_dir, people_path))
    review, canonical = read(reference_path), read(people_path)
    require(review.get('schema') == 'tk2-retainer-affiliation-review-v1', 'Unknown retainer review schema')
    text(review.get('revision'), 'Review revision')
    text(review.get('base_commit'), 'Frozen base commit')
    people, order, additions = check_people(canonical, review)
    raw_scope = review.get('scope_factions')
    require(isinstance(raw_scope, list), 'Frozen scope faction list required')
    scope = [row.get('id') if isinstance(row, dict) else row for row in raw_scope]
    require(len(scope) == EXPECTED_SCOPE and len(set(scope)) == len(scope)
            and all(isinstance(fid, str) and fid for fid in scope), 'Require 25 unique scope factions')
    decisions = indexed(review.get('scenarios'), 'id', 'Reviewed scenarios')
    require(len(decisions) == EXPECTED_SCENARIOS, 'Require all 29 reviewed scenarios')
    paths = read(catalog_dir / 'index.json').get('catalogs')
    require(isinstance(paths, list) and len(paths) == EXPECTED_SCENARIOS
            and len(set(paths)) == len(paths), 'Require 29 unique compiled catalogues')
    require(all(isinstance(path, str) and path == 'campaigns/' + Path(path).name
                and Path(path).suffix == '.json' for path in paths), 'Invalid compiled catalogue filename')
    presentation_path = ROOT / 'game/assets/map-presentation.json'
    presentation = read(presentation_path)['city_names']
    results, seen = [], set()
    for filename in paths:
        path = catalog_dir / Path(filename).name
        data = read(path)
        ident = data.get('id')
        require(ident in decisions and ident not in seen, 'Unknown/duplicate compiled scenario: ' + str(ident))
        require(Path(filename).stem == ident.removeprefix('mainland'), 'Catalogue filename differs: ' + ident)
        seen.add(ident)
        result = check_catalog(data, decisions[ident], people, order, scope, presentation)
        result['catalog_sha256'] = sha256(path.read_bytes()).hexdigest()
        results.append(result)
    require(seen == set(decisions), 'Compiled/reviewed scenario set differs')
    results.sort(key=lambda row: (*row['date'], row['id']))
    summary = Counter(scenarios=len(results), people=len(people), new_people=len(additions))
    for row in results:
        summary.update(historical=int(not row['fictional']), fictional=int(row['fictional']),
                       faction_openings=len(row['factions']), changes=len(row['changes']),
                       chronology=len(row['chronology']))
    require(summary['historical'] == EXPECTED_HISTORICAL and summary['fictional'] == EXPECTED_FICTIONAL,
            'Require 23 historical and six separately reviewed IF openings')
    return dict(schema='tk2-retainer-affiliation-audit-v1', revision=review['revision'],
        base_commit=review['base_commit'], review_sha256=sha256(reference_path.read_bytes()).hexdigest(),
        canonical_people_sha256=sha256(people_path.read_bytes()).hexdigest(),
        base_people_snapshot_sha256=review['base_people_snapshot_sha256'],
        summary=dict(summary), scope_factions=scope, new_people=list(additions.values()),
        limits=review.get('limits', [
            '地域代理は地図上の表現で、当月の実際の駐地や郡全体の支配を証明しません。',
            '生没年不詳の人物は登場・退出の推定境界を明記し、原典の確定年月と区別します。',
            '宋建など、史料に配下の実名が残らない勢力へ架空の歴史人物を補充しません。',
            '追加人物の徳60・忠80は本作の設定値です。初期体力は王建のみ原表42、ほか21人は80、回復上限は全員80です。'
            '王建の原表忠59は所属文脈が空のため公孫氏への忠には適用せず、原表徳41も徳60を覆しません。']),
        material_definition='開放都市の資金・兵糧、予備兵と在籍武将の帯兵合計。基準は固定レビューの変更前総量。',
        stat_policy='追加人物はSAN14魅力の出典がないため徳60。初期体力は王建のみ原表cnblogs-line-0229の42、'
                    'ほかは80、回復上限は全員80。王建の原表忠59は所属対象が空なので公孫氏臣としても忠80。'
                    '196年登場・249年寿命や原表徳41は保持資料であり、史実年代や本作徳へ転用しない。',
        scenarios=results)


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def markdown(report):
    def links(row):
        return '、'.join(f'[史料{i}]({url})' for i, url in enumerate(row['source_urls'], 1))

    def state(row, names):
        status = dict(serving='在籍', free='在野', chronology_excluded='年代対象外',
                      scenario_excluded='本開幕対象外').get(row['status'], row['status'])
        return f"{status} / {row['faction'] or '—'} / {names.get(row['city'], row['city']) or '—'} / {'君主' if row['ruler'] else '一般'} / 帯兵{row['troops']}"

    count = report['summary']
    lines = ['# 独立勢力の配下・年代レビュー（2026年10月27日）', '',
        f"全{count['scenarios']}開幕を固定の[判定表](../game/config/references/retainer-affiliation-review.json)と照合した記録です。"
        f"人物庫{count['people']}人、追加{count['new_people']}人、配置記録延べ{count['changes']}件を対象にします。", '',
        '配置記録には各開幕での新規人物庫への追加・開幕対象外も含み、全件が新たな在籍や別人の増加ではありません。', '',
        '所属の史料確認、推定した登場期間、地図上の地域代理、仮想シナリオの例外を区別します。'
        '**全人物の正確な月別駐地を史料で確定したという意味ではありません。**', '',
        '`--write` はこの資料と[詳細JSON](retainer-affiliation-audit-20261027.json)だけを生成し、'
        '`--check` は入力と資料を一切変更せずバイト単位で照合します。変更前欄は固定証拠であり再生成しません。', '',
        '## 留保と共通ルール', '']
    lines += ['- ' + str(note) for note in report['limits']]
    lines += ['', report['stat_policy'], '', '資源保存の定義：' + report['material_definition'], '', '## 追加人物', '',
        '| 人物 / 固定ID | 実行時ID | 生年 / 登場年 / 退出年 | 根拠と留保 |', '| --- | ---: | --- | --- |']
    for person in report['new_people']:
        values = (f"{person['name']} (`{person['person_id']}`)", person['runtime_id'],
                  f"{person['birth_year']} / {person['service_year']} / {person['death_year']}",
                  person['note'] + ' ' + links(person))
        lines.append('| ' + ' | '.join(map(cell, values)) + ' |')
    for row in report['scenarios']:
        lines += ['', f"## {row['date'][0]}年{row['date'][1]}月・{row['title']}（{'仮想' if row['fictional'] else '史実'}）", '']
        lines += ['- ' + note for note in row['notes']]
        material = row['material']
        lines += ['', f"保存総量：資金{material['gold']}・兵糧{material['grain']}・兵員{material['soldiers']}。", '',
            '| 勢力 / 君主 | 本拠 | 配下（君主を含む） | 判定と留保 |', '| --- | --- | --- | --- |']
        for faction in row['factions']:
            values = (f"{faction['id']} / {faction['captain']}" + ('〔後日起兵〕' if faction['dormant'] else ''),
                      row['city_names'].get(faction['city'], faction['city']), '、'.join(faction['names']) or '—',
                      f"{faction['certainty']}：{faction['note']} {links(faction)}")
            lines.append('| ' + ' | '.join(map(cell, values)) + ' |')
        lines += ['', '### 人物ごとの配置変更', '', '| 人物 / 固定ID | 変更前 | 変更後 | 根拠と留保 |',
                  '| --- | --- | --- | --- |']
        for change in row['changes']:
            values = (f"{change['name']} (`{change['person_id']}`)", state(change['before'], row['city_names']),
                      state(change['after'], row['city_names']),
                      f"{change['certainty']}：{change['note']} {links(change)}")
            lines.append('| ' + ' | '.join(map(cell, values)) + ' |')
        if not row['changes']:
            lines += ['| — | — | — | 今回の配置変更なし。現状維持も、全駐地を史料が証明した認定ではありません。 |']
        if row['chronology']:
            lines += ['', '### 年代の個別照合', '', '| 人物 | 生年 / 登場年 / 退出年 | 根拠と留保 |', '| --- | --- | --- |']
            for chrono in row['chronology']:
                values = (f"{chrono['name']} (`{chrono['person_id']}`)",
                          f"{chrono['birth_year']} / {chrono['service_year']} / {chrono['death_year']}",
                          f"{chrono['chronology_basis']}：{chrono['note']} {links(chrono)}")
                lines.append('| ' + ' | '.join(map(cell, values)) + ' |')
    return '\n'.join(lines).rstrip() + '\n'


def rendered_files(report):
    return {REPORT_JSON.name: json.dumps(report, ensure_ascii=False, indent=2) + '\n',
            REPORT_MD.name: markdown(report)}


def check(reference_path=REFERENCE, catalog_dir=CATALOG_DIR, people_path=PEOPLE,
          report_json=REPORT_JSON, report_md=REPORT_MD):
    report = build_report(reference_path, catalog_dir, people_path)
    outputs = rendered_files(report)
    for path, name in ((Path(report_json), REPORT_JSON.name), (Path(report_md), REPORT_MD.name)):
        require(path.is_file() and path.read_bytes() == outputs[name].encode('utf-8'),
                'Retainer affiliation report is stale: ' + str(path))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--write', action='store_true', help='Write only the two report documents')
    modes.add_argument('--check', action='store_true', help='Read-only byte comparison of both reports')
    parser.add_argument('--reference', type=Path, default=REFERENCE)
    parser.add_argument('--catalog-dir', type=Path, default=CATALOG_DIR)
    parser.add_argument('--people', type=Path, default=PEOPLE)
    parser.add_argument('--report-dir', type=Path, default=REPORT_JSON.parent)
    args = parser.parse_args(argv)
    if args.check:
        report = check(args.reference, args.catalog_dir, args.people,
                       args.report_dir / REPORT_JSON.name, args.report_dir / REPORT_MD.name)
    else:
        report = build_report(args.reference, args.catalog_dir, args.people)
        if args.write:
            args.report_dir.mkdir(parents=True, exist_ok=True)
            for name, body in rendered_files(report).items():
                (args.report_dir / name).write_bytes(body.encode('utf-8'))
    print(json.dumps(report['summary'], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Retainer audit failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
