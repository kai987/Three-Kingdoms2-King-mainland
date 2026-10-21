#!/usr/bin/env python3
"""Append reviewed historical people and career windows to immutable v12 starts.

Profiles are authored remake values, not invented SAN14 exports. Existing
identities/abilities, map, ownership, city capacity and saves remain untouched.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from urllib.parse import unquote

from build_campaigns import read, write
from build_dlc_campaigns import finish_audits
from remake.officers import OfficerProfile, PersonDefinition, YearState, year_state, virtue_score


FOLDER = 'main-scenarios-v13/'
NOTES = [
    '人物庫保留原有1000人，追加有原典身分依據的人物；同人異名不重複計數。',
    '追加人物的武、知、體力與適性為本作設計值；未具充分德行記錄者沿用用戶指定德60。',
    '新增年表含明列的遊戲估計；退場年不冒充史實卒年，原典記載與估計分開保存。',
    '逐篇補入有來源的任職窗口；連續任職及IF延續屬本作推定，駐城仍按容量及邊境防務分配。',
    '在籍、在野、未到出仕年、歸屬待考及容量不足分開統計；沒有把總人物庫全部塞入開局。',
    '新增人物僅在本篇已啟用勢力的生涯窗口內登場；未來以在野待訪，不強制歷史轉屬。',
    '新增資料只用於新開v13戰役；每城30人、出戰10人、地圖及既有存檔保持原規則。',
]


def eligible(person, year):
    return year_state(PersonDefinition(person['person_id'], person['name'], person['birth_year'],
        person['service_year'], person['death_year'], person['chronology_basis']), year)


def window_active(window, date):
    return tuple(window['from']) <= date <= tuple(window['to'])


def new_people(spec, original):
    known = {label for p in original for label in [p['name'], *p.get('aliases', [])]}
    originals = {p['person_id']: p for p in original}
    for alias in spec['excluded_duplicates']:
        person = originals[alias['existing_person_id']]
        if alias['existing_name'] not in {person['name'], *person.get('aliases', [])}:
            raise ValueError('Excluded alias does not identify an existing person')
        known.add(alias['name'])
    runtime_start = max(p['runtime_id'] for p in original) + 1
    default = read('game/config/virtue-completion.json')['default_policy']
    people = []
    for i, entry in enumerate(spec['people']):
        labels = {entry['name'], *entry['aliases'], entry['name_japanese']}
        if known & labels:
            raise ValueError('Duplicate historical name/alias: ' + entry['name'])
        known.update(labels)
        dates, raw = entry['chronology'], entry['profile']
        end = dates['death_year'] if dates['death_year'] is not None else dates['retirement_year']
        virtue = deepcopy(entry['virtue_design'])
        if virtue.get('dimensions') is None:
            if raw['virtue'] != 60:
                raise ValueError('Unreviewed virtue must follow the explicit60 policy')
            virtue = deepcopy(default)
        else:
            if virtue_score(virtue['dimensions']) != raw['virtue']:
                raise ValueError('Inconsistent authored virtue dimensions')
            sources = [dict(s, work='晉書' if '晉書' in unquote(s['url']) else '三國志',
                section=unquote(s['url']).rsplit('/', 1)[-1]) for s in entry['sources']]
            virtue.update(status='configured_design', sources=sources, design_rationale=virtue['basis'])
        profile = OfficerProfile(raw['health_max'], raw['martial_strength'], raw['intellect'],
            raw['virtue'], raw['terrain_affinity'], {}, deepcopy(raw['basis']))
        # Stable suffixes survive rejected duplicates; never recycle their ID.
        ident = runtime_start + int(entry['person_id'].rsplit('-', 1)[-1]) - 1
        person = dict(person_id=entry['person_id'], name=entry['name'], runtime_id=ident,
            birth_year=dates['birth_year'], service_year=dates['service_year'], death_year=end,
            chronology_basis='historical_career_with_explicit_game_estimates; ' + dates['basis'],
            chronology_design=deepcopy(dates), profile=asdict(profile), aliases=sorted(labels),
            virtue_design=virtue, configuration=dict(health='remake_default80',
                affinity='explicit_role_region_game_design', virtue=profile.basis['virtue'],
                is_historical_measurement=False),
            ability_source=dict(kind='historical_authorial_game_design',
                source_urls=[s['url'] for s in entry['sources']],
                notes=dates['basis'] + ' ' + entry['identity_note'], source_name=entry['name_japanese']))
        eligible(person, dates['service_year'])
        people.append(person)
    if len(people) != spec['new_count'] or len({p['person_id'] for p in people}) != len(people):
        raise ValueError('Expansion count/identity mismatch')
    return people


def build_catalog(previous, additions, spec, review):
    data = deepcopy(previous)
    data.update(id=previous['id'].replace('-v12', '-v13'), content_generation=13,
        officer_count=len(previous['people'])+len(additions))
    data['people'].extend(deepcopy(additions))
    data['additional_person_aliases'] = {r['existing_person_id']: [r['name']]
        for r in spec['excluded_duplicates']}
    if data['officer_count'] > data['rules']['runtime_capacity']:
        raise ValueError('Expansion exceeds configured runtime slots')
    by_pid = {p['person_id']: p for p in data['people']}
    factions = {f['id']: f for f in data['factions']}
    date = data['start_year'], data['start_month']
    initial, free = data['initial_officers'], data['initial_free_officers']
    assignments, locations = data['era_assignments'], data['appearance_locations']
    audit = dict(schema='officer-opening-audit-v13', previous_catalog=previous['id'],
        added_people=len(additions), restored_memberships=[], added_serving=[], pending=[], conflicts=[],
        future_locations=[], historical_transfers=[])
    counts = Counter(data['initial_owners'][r['city']] for r in initial)
    limit = {side: sum(owner==side for owner in data['initial_owners'].values())*
        data['rules']['city_officer_capacity'] for side in factions}

    def place(pid, side, rule, *, new=False):
        person = by_pid[pid]
        ys = eligible(person, date[0])
        if ys not in (YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW):
            return False
        old = assignments.get(pid, {})
        if old.get('status') in ('scenario_excluded', 'pending_capacity'):
            return False
        serving = next((r for r in initial if r['person_id']==pid), None)
        if serving:
            current = data['initial_owners'][serving['city']]
            if current != side:
                audit['conflicts'].append(dict(person_id=pid, current=current, requested=side))
            return False
        if not new and old.get('status') not in ('pending_history', 'pending_faction', 'pending_location', 'free'):
            return False
        if side not in factions:
            return False
        if counts[side] >= limit[side]:
            assignments[pid] = dict(old, status='pending_capacity', city=None, faction=side,
                reason='本篇所屬勢力的30人城池席位不足，沒有轉成在野刷入。')
            free[:] = [r for r in free if r['person_id'] != pid]
            locations.pop(pid, None)
            audit['pending'].append(dict(person_id=pid, reason='capacity', faction=side))
            return False
        free[:] = [r for r in free if r['person_id'] != pid]
        city = factions[side]['city']
        initial.append(dict(person_id=pid, city=city, troops=300, ruler=False,
            resolve_death_year=ys==YearState.DEATH_YEAR_REVIEW))
        counts[side] += 1
        basis = 'historical_expansion_career_window' if new else 'reviewed_career_window_v13'
        proof = dict(basis=basis, sources=deepcopy(rule.get('sources', [])),
            note=rule.get('basis') or rule.get('membership_basis'),
            fictional_continuity_adaptation=bool(data['main_scenario'].get('fictional')))
        assignments[pid] = dict(old, status='serving', source_status='serving',
            source_ruler=factions[side]['captain'], source_city=None, faction=side, city=city,
            year_state=ys.value, placement_basis='authored_enemy_frontier_balanced',
            death_year_resolved=ys==YearState.DEATH_YEAR_REVIEW,
            reason=None, membership_revision=None, posting_reference=None,
            membership_resolution=dict(basis=basis, override=dict(basis=proof['note'])),
            career_review=proof)
        locations[pid] = city
        audit['added_serving' if new else 'restored_memberships'].append(
            dict(person_id=pid, name=person['name'], faction=side, proof=proof))
        return True

    for rule in review.get('historical_transfers', []):
        if data['main_scenario'].get('fictional') or not tuple(rule['from_date']) <= date <= tuple(rule['to_date']):
            continue
        pid, side = rule['person_id'], rule['to_faction']
        row = next((r for r in initial if r['person_id']==pid), None)
        if (row is None or row.get('ruler') or by_pid[pid]['name'] != rule['name']
                or side not in factions or data['initial_owners'][row['city']] != rule['from_faction']
                or counts[side] >= limit[side]):
            raise ValueError('Historical transfer precondition failed: ' + pid)
        before = deepcopy(assignments[pid])
        row['city'] = factions[side]['city']
        counts[rule['from_faction']] -= 1;counts[side] += 1
        assignments[pid].update(faction=side, city=row['city'], source_city=None,
            source_status='serving', source_ruler=factions[side]['captain'],
            membership_revision=dict(reason=rule['basis'], sources=rule['sources']),
            posting_reference=None, membership_resolution=dict(basis='reviewed_transition',
                override=dict(basis=rule['basis'])))
        locations[pid] = row['city']
        audit['historical_transfers'].append(dict(person_id=pid, name=by_pid[pid]['name'],
            before_faction=rule['from_faction'], after_faction=side,
            before_assignment=before, sources=rule['sources'], basis=rule['basis']))

    for rule in review['entries']:
        pid = rule['person_id']
        if pid not in by_pid or by_pid[pid]['name'] != rule['name']:
            raise ValueError('Reviewed identity/name mismatch')
        if tuple(rule['from_date']) <= date <= tuple(rule['to_date']):
            place(pid, rule['faction'], rule)

    appearance_windows = {}
    # Fill only individually reviewed future locations that the old adapter
    # omitted. Existing future plans and all excluded/capacity cases are kept.
    present = {r['person_id'] for r in initial+free}
    for rule in review['entries']:
        pid, side = rule['person_id'], rule['faction']
        if (pid in present or pid in previous['appearance_locations'] or side not in factions
                or tuple(rule['to_date']) < date
                or assignments[pid]['status'] in ('scenario_excluded', 'pending_capacity')):
            continue
        city = factions[side]['city']
        locations[pid] = city
        appearance_windows.setdefault(pid, []).append(dict(start=rule['from_date'],
            end=rule['to_date'], city=city))
        audit['future_locations'].append(dict(person_id=pid, faction=side, city=city,
            basis='reviewed_career_window_future_free_appearance_not_forced_service'))
    for entry, person in zip(spec['people'], additions):
        pid = person['person_id'];ys = eligible(person, date[0])
        valid = [w for w in entry['membership_windows'] if w['faction'] in factions]
        current = next((w for w in valid if window_active(w, date)), None)
        disabled = next((w for w in entry['membership_windows'] if window_active(w, date)
            and w['faction'] not in factions), None)
        assignments[pid] = dict(status='chronology_excluded' if ys not in (YearState.AVAILABLE,
            YearState.DEATH_YEAR_REVIEW) else 'pending_history', source_status='unreviewed',
            source_ruler=None, source_city=None, year_state=ys.value, faction=None, city=None,
            placement_basis=None, reason='未在本篇已啟用勢力的生涯窗口內，不自動刷成在野。',
            death_year_resolved=False, posting_reference=None, membership_revision=None)
        if disabled and ys in (YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW):
            assignments[pid].update(status='pending_faction', disabled_source_faction=disabled['faction'],
                reason='原典所屬陣營未在本篇啟用，沒有按城池顏色改投或刷成在野。')
        if current:
            place(pid, current['faction'], dict(current, sources=entry['sources']), new=True)
        # Future entries follow the existing free-appearance rule, only within
        # explicitly configured career windows; absence is never a random spawn.
        windows = []
        if assignments[pid]['status'] != 'pending_capacity':
            for w in valid:
                if tuple(w['to']) < date:
                    continue
                city = w['city']
                while city in data['city_foundings'] and tuple(w['from']) < (
                        data['city_foundings'][city]['year'], data['city_foundings'][city].get('month', 1)):
                    city = data['city_foundings'][city]['parent']
                if city not in {c['id'] for c in data['cities']}:
                    raise ValueError('Unlocated expansion window: ' + pid)
                # A documented career appearing and ending in the same year
                # would otherwise never spawn under the annual review rule.
                # This local opt-in does not change old catalogs or revive IDs.
                windows.append(dict(start=list(w['from']), end=list(w['to']), city=city,
                    resolve_death_year=person['service_year']==person['death_year']))
            if windows:
                locations[pid] = assignments[pid]['city'] or windows[0]['city']
        appearance_windows[pid] = windows
    data['appearance_windows'] = appearance_windows
    data['officer_expansion'] = audit
    finish_audits(data)
    statuses = Counter(r['status'] for r in assignments.values())
    data['coverage'].update(library=data['officer_count'], configured_profiles=data['officer_count'],
        health_configured=data['officer_count'], affinity_configured=data['officer_count'],
        new_historical_people=len(additions), pending_profiles=0,
        history_designs_total=sum((p.get('virtue_design') or {}).get('status')=='configured_design'
            for p in data['people']), new_history_profiles=sum(p['virtue_design']['status']=='configured_design'
            for p in additions),
        default_virtue_profiles=sum((p.get('virtue_design') or {}).get('status')=='configured_default'
            for p in data['people']), pending_history=statuses['pending_history'],
        pending_faction=statuses['pending_faction'], pending_capacity=statuses['pending_capacity'])
    data['coverage']['pending_factions'] = sorted({r['disabled_source_faction'] for r in assignments.values()
        if r.get('disabled_source_faction')})
    data['design_notes'] = [n for n in data['design_notes'] if '千人' not in n]+NOTES
    data['main_scenario']['membership_basis'] = data['main_scenario'].get('membership_basis',
        data['era_metadata'].get('membership_basis', 'retained_v12_membership')) + '; source_referenced_v13_career_windows_and_explicit_new_person_game_design'
    data['era_metadata']['main_scenario'] = deepcopy(data['main_scenario'])
    return data


def build():
    spec = read('game/config/officer-expansion-v13.json')
    review = read('game/config/roster-review-v13.json')
    index = read('game/data/main-scenarios-v12/index.json')
    baseline = read('game/data/' + index['catalogs'][0])
    additions = new_people(spec, baseline['people'])
    paths, summary = [], []
    for path in index['catalogs']:
        old = read('game/data/' + path)
        data = build_catalog(old, additions, spec, review)
        name = FOLDER + path.rsplit('/', 1)[-1]
        write('game/data/' + name, data);paths.append(name)
        summary.append(dict(id=data['id'], year=data['start_year'], month=data['start_month'],
            library=data['officer_count'], serving=len(data['initial_officers']),
            free=len(data['initial_free_officers']), restored=len(data['officer_expansion']['restored_memberships']),
            new_serving=len(data['officer_expansion']['added_serving']),
            pending_history=data['coverage']['pending_history'], pending_capacity=data['coverage']['pending_capacity'],
            factions={f['id']:f['initial_officers'] for f in data['factions']}))
    result = dict(schema='main-scenario-index-v1', catalogs=paths, default='mainland217-07-v13', summary=summary)
    write('game/data/'+FOLDER+'index.json', result)
    return result


if __name__=='__main__':
    import json
    result=build();print(json.dumps(dict(catalogs=len(result['catalogs']), default=result['default'])))
