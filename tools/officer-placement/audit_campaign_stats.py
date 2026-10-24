#!/usr/bin/env python3
"""Deterministically audit all current scenario openings, previews and saves.

Expected values are derived independently from the retained factual references,
not from the runtime appearance_values helper.  Only the report is written;
no server, player session, campaign source or save file is modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign
from remake.session import CampaignSession

REPORT = ROOT / 'docs/officer-stat-scenarios-v1.json'
SEED = 2026
CANONICAL_FIELDS = ('person_id', 'runtime_id', 'name', 'birth_year', 'service_year',
                    'death_year', 'chronology_basis')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def expected_free_people(catalog):
    """Derive dated eligible free IDs directly from opening/window data."""
    data = catalog.data
    year, month = data['start_year'], data['start_month']
    serving = {row['person_id'] for row in data['initial_officers']}
    free = {row['person_id']: row['city'] for row in data.get('initial_free_officers', [])}
    active = set(data['active_cities'])
    for row in data['people']:
        pid = row['person_id']
        if pid in serving or pid in free:
            continue
        if any(row['profile'][field] is None for field in
               ('health_max', 'martial_strength', 'intellect', 'virtue', 'terrain_affinity')):
            continue
        city = data['appearance_locations'].get(pid)
        windows = data.get('appearance_windows', {}).get(pid)
        resolve_death_year = False
        if windows is not None:
            current = next((window for window in windows if tuple(window['start'])
                            <= (year, month) <= tuple(window['end'])), None)
            if current is None:
                continue
            city = current['city']
            resolve_death_year = current.get('resolve_death_year') is True
        birth, service, death = (row[field] for field in ('birth_year', 'service_year', 'death_year'))
        if None in (birth, service, death) or birth > year or service > year or death < year:
            continue
        if death == year and not resolve_death_year:
            continue
        if city in active:
            free[pid] = city
    return free


def loyalty_expectation(source, faction, ruler):
    if faction is None:
        return 0, 'free'
    if ruler:
        return 100, 'ruler'
    if source is None:
        return 80, 'no_source_default'
    if source['loyalty'] is None:
        return 80, 'source_ruler_marker_default'
    if faction in source['faction_ids']:
        return source['loyalty'], 'source_context_applied'
    return 80, 'source_context_mismatch_default'


def audit():
    index_path = ROOT / 'game/data/campaigns/index.json'
    index = read(index_path)
    people_path = ROOT / 'game/config/campaigns/people.json'
    source_path = ROOT / 'game/config/references/cnblogs-officer-stats.json'
    abilities_path = ROOT / 'game/config/references/san14-abilities.json'
    people = read(people_path)['people']
    reference = read(source_path)
    sources = {row['person_id']: row for row in reference['records'] if row['person_id']}
    abilities = {row['person_id']: row['stats'] for row in read(abilities_path)['abilities']}
    check(len(index['catalogs']) == 29, 'Expected 29 current scenarios')
    check(len(people) == 1023 and len(abilities) == 1000 and len(sources) == 223,
          'Unexpected factual reference coverage')
    session = CampaignSession([ROOT / 'game/data' / name for name in index['catalogs']])
    source_index = read(ROOT / 'game/config/campaigns/index.json')
    scenario_sources = {entry['id']: read(ROOT / 'game/config/campaigns' / entry['file'])
                        for entry in source_index['scenarios']}
    scenarios = []
    totals = Counter()
    for scenario_id, catalog in session.catalogs.items():
        data = catalog.data
        check(catalog.rules.city_officer_capacity == 99, scenario_id + ': city capacity changed')
        check(catalog.rules.battle_officers_per_side == 10, scenario_id + ': battle capacity changed')
        check(set(catalog.definitions) == set(people), scenario_id + ': canonical person set changed')
        override = scenario_sources[scenario_id].get('people_overrides', {})
        check(not (set(override) - {'update'}), scenario_id + ': unsupported person override shape')
        overrides = override.get('update', {})
        check(set(overrides) <= set(people), scenario_id + ': unknown person override')
        date_overrides = []
        charisma_count = fallback_count = 0
        for pid, canonical_person in people.items():
            person = catalog.by_id[catalog.ids[pid]]
            patch = overrides.get(pid, {})
            check(not (set(patch) - {'set'}), scenario_id + ': unsupported individual override shape')
            expected_identity = {field: patch.get('set', {}).get(field, canonical_person[field])
                                 for field in CANONICAL_FIELDS}
            check(all(person[field] == expected_identity[field] for field in CANONICAL_FIELDS),
                  scenario_id + ': canonical person identity/date mismatch: ' + pid)
            check(all(person[field] == canonical_person[field]
                      for field in ('person_id', 'runtime_id', 'name')),
                  scenario_id + ': a scenario overrode stable identity: ' + pid)
            changed_dates = {field: dict(canonical=canonical_person[field], scenario=person[field])
                             for field in ('birth_year', 'service_year', 'death_year', 'chronology_basis')
                             if person[field] != canonical_person[field]}
            if changed_dates:
                date_overrides.append(dict(person_id=pid, name=person['name'], fields=changed_dates))
            source = sources.get(pid)
            health = source['health'] if source else 80
            prior_cap = canonical_person['pre_campaign_stat_policy_v1']['profile']['health_max']
            expected_virtue = min(99, abilities[pid]['charisma']) if pid in abilities else 60
            charisma_count += pid in abilities
            fallback_count += pid not in abilities
            check(person['profile']['virtue'] == expected_virtue,
                  scenario_id + ': incorrect charisma/default virtue: ' + pid)
            check(person['profile']['source_stats'] == canonical_person['profile']['source_stats'],
                  scenario_id + ': source abilities changed: ' + pid)
            check(person['initialization']['health'] == health
                  and person['profile']['health_max'] == max(prior_cap, health),
                  scenario_id + ': incorrect independent health/cap policy: ' + pid)
            if source:
                expected_source = dict(value=source['loyalty'], display=source['loyalty_display'],
                    source_faction_label=source['faction_label'], faction_ids=source['faction_ids'],
                    reference='game/config/references/cnblogs-officer-stats.json',
                    source_row_id=source['source_row_id'])
                check(person['initialization']['source_loyalty'] == expected_source,
                      scenario_id + ': initial loyalty provenance changed: ' + pid)
            else:
                check(person['initialization']['source_loyalty'] is None,
                      scenario_id + ': unbound source incorrectly applied: ' + pid)
        check((charisma_count, fallback_count) == (1000, 23), scenario_id + ': virtue coverage changed')
        player = next(iter(catalog.factions))
        session.command('new', dict(scenario=scenario_id, faction=player, seed=SEED), session.revision)
        game, state = session.game, session.game.state
        check(set(state.cities) == set(data['active_cities']), scenario_id + ': active cities changed')
        starts = {row['person_id']: row for row in data['initial_officers']}
        expected_free = expected_free_people(catalog)
        actual_people = {officer.person_id for officer in state.officers.values()}
        check(not (set(starts) & set(expected_free)), scenario_id + ': serving/free collision')
        check(actual_people == set(starts) | set(expected_free), scenario_id + ': opening population changed')
        counts = Counter()
        changes = []
        expected_rosters = {city: [] for city in state.cities}
        for pid, row in starts.items():
            expected_rosters[row['city']].append(catalog.ids[pid])
        for city_id, city in state.cities.items():
            check(city.owner == data['initial_owners'][city_id], scenario_id + ': opening ownership changed')
            check(city.roster.officer_ids == expected_rosters[city_id], scenario_id + ': opening roster changed')
            check(len(city.roster.officer_ids) <= 99, scenario_id + ': city over capacity')
        for ident, officer in sorted(state.officers.items()):
            pid, person = officer.person_id, people[officer.person_id]
            row, source = starts.get(pid), sources.get(pid)
            ruler = bool(row and row.get('ruler'))
            role = 'ruler' if ruler else 'serving' if row else 'free'
            city = row['city'] if row else expected_free[pid]
            faction = data['initial_owners'][city] if row else None
            expected_health = source['health'] if source else 80
            expected_loyalty, reason = loyalty_expectation(source, faction, ruler)
            prior_health = person['pre_campaign_stat_policy_v1']['profile']['health_max']
            prior_loyalty = 100 if ruler else 80 if row else 0
            check((officer.runtime_id, ident) == (person['runtime_id'], person['runtime_id']),
                  scenario_id + ': runtime person ID changed: ' + pid)
            check(officer.faction_id == faction, scenario_id + ': officer ownership changed: ' + pid)
            check(officer.health == expected_health and officer.loyalty == expected_loyalty,
                  scenario_id + ': independent runtime health/loyalty mismatch: ' + pid)
            check(officer.profile.virtue == (min(99, abilities[pid]['charisma']) if pid in abilities else 60),
                  scenario_id + ': runtime virtue mismatch: ' + pid)
            if row is None:
                check(state.extension['free_locations'][str(ident)] == city,
                      scenario_id + ': free appearance city changed: ' + pid)
            counts[role] += 1
            if reason not in ('ruler', 'free'):
                counts[reason] += 1
            counts['initial_health_changed'] += officer.health != prior_health
            counts['health_cap_increased'] += officer.profile.health_max > prior_health
            counts['ordinary_loyalty_changed'] += role == 'serving' and officer.loyalty != 80
            if officer.health != prior_health or officer.loyalty != prior_loyalty:
                changes.append(dict(person_id=pid, runtime_id=ident, name=person['name'], role=role,
                    city=city, faction=faction, source_row_id=source['source_row_id'] if source else None,
                    previous_initial_health=prior_health, initial_health=officer.health,
                    previous_health_max=prior_health, health_max=officer.profile.health_max,
                    previous_loyalty=prior_loyalty, loyalty=officer.loyalty, loyalty_reason=reason))
        saved = session.export_save()
        saved_bytes = canonical(saved)
        rng_before = (state.rng.state, state.rng.draws)
        for city_id, city in state.cities.items():
            response = session.preview_city(scenario_id, city_id)
            preview = response['city']
            check((response['scenario'], response['year'], response['month'], response['capacity'])
                  == (scenario_id, state.year, state.month, 99), scenario_id + ': preview date/capacity mismatch')
            check(preview['owner'] == city.owner, scenario_id + ': preview owner mismatch')
            check(all(preview[field] == getattr(city, field) for field in ('gold', 'grain', 'reserves')),
                  scenario_id + ': preview stocks mismatch')
            check([row['id'] for row in preview['officers']] == city.roster.officer_ids,
                  scenario_id + ': preview roster mismatch')
            for row in preview['officers']:
                officer = state.officers[row['id']]
                check((row['person_id'], row['health'], row['loyalty'], row['virtue'], row['troops'])
                      == (officer.person_id, officer.health, officer.loyalty, officer.profile.virtue, officer.troops),
                      scenario_id + ': preview officer attributes mismatch')
                check(row['is_ruler'] == bool(starts[officer.person_id].get('ruler')),
                      scenario_id + ': preview ruler role mismatch')
        check(rng_before == (state.rng.state, state.rng.draws), scenario_id + ': previews consumed RNG')
        check(canonical(session.export_save()) == saved_bytes, scenario_id + ': previews mutated the save')
        twin = Campaign(catalog)
        twin.load_save(saved, 0)
        check(canonical(twin.export_save()) == saved_bytes, scenario_id + ': save roundtrip changed state')
        check(all((officer.health, officer.loyalty) == (twin.state.officers[ident].health, twin.state.officers[ident].loyalty)
                  for ident, officer in state.officers.items()), scenario_id + ': save roundtrip reset officer attributes')
        result = dict(scenario=scenario_id, title=data['title'], year=state.year, month=state.month,
            player=player, seed=SEED, cities=len(state.cities), serving=counts['serving'] + counts['ruler'],
            rulers=counts['ruler'], ordinary_serving=counts['serving'], free=counts['free'],
            total_instantiated=len(state.officers), initial_health_changed=counts['initial_health_changed'],
            health_cap_increased=counts['health_cap_increased'],
            ordinary_loyalty_changed=counts['ordinary_loyalty_changed'],
            source_context_applied=counts['source_context_applied'],
            source_context_mismatch_defaults=counts['source_context_mismatch_default'],
            source_ruler_marker_nonruler_defaults=counts['source_ruler_marker_default'],
            no_source_loyalty_defaults=counts['no_source_default'],
            virtue_coverage=dict(san14_charisma=charisma_count, missing_charisma_default60=fallback_count),
            city_capacity=99, battle_capacity=10,
            preview_cities_checked=len(state.cities), preview_officers_checked=len(starts),
            preview_rng_unchanged=True, preview_save_bytes_unchanged=True,
            save_roundtrip_bytes_equal=True, save_health_loyalty_preserved=True,
            canonical_ids_match=True, declared_source_dates_match=True,
            declared_person_date_overrides=date_overrides, opening_ownership_rosters_match=True,
            rng=dict(state=state.rng.state, draws=state.rng.draws),
            opening_save_sha256=hashlib.sha256(saved_bytes).hexdigest(), changed_people=changes)
        for field in ('cities', 'serving', 'rulers', 'ordinary_serving', 'free', 'total_instantiated',
                      'initial_health_changed', 'health_cap_increased', 'ordinary_loyalty_changed',
                      'source_context_applied', 'source_context_mismatch_defaults',
                      'source_ruler_marker_nonruler_defaults', 'no_source_loyalty_defaults',
                      'preview_cities_checked', 'preview_officers_checked'):
            totals[field] += result[field]
        scenarios.append(result)
    return dict(schema='tk2-officer-stat-scenario-audit-v1', policy_id='campaign-officer-stats-v1',
        seed=SEED, scenario_count=len(scenarios),
        methodology='Fresh normal-difficulty game in every catalog. Expected health/loyalty are independently '
                    'derived from the pinned cnblogs reference and explicit faction context; virtue is checked '
                    'against retained SAN14 numerical facts. Every city preview is compared with runtime state '
                    'without RNG/save mutation, then the complete save is loaded into a fresh same-version campaign.',
        scope='Opening verification only, not historical certification of existing placements or a migration of older saves. '
              'Changed-person lists contain initial health/loyalty changes only; full virtue changes are in officer-stat-changes-v1.json.',
        references=dict(people='game/config/campaigns/people.json',
            cnblogs='game/config/references/cnblogs-officer-stats.json',
            cnblogs_archive_sha256=reference['source']['archive_sha256'],
            cnblogs_factual_records_sha256=reference['source']['factual_records_sha256'],
            san14='game/config/references/san14-abilities.json'),
        summary=dict(totals), scenarios=scenarios)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check the report byte-for-byte without writing')
    args = parser.parse_args()
    report = audit()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.check:
        check(REPORT.read_text(encoding='utf-8') == rendered, 'Scenario-stat audit report is stale')
    else:
        REPORT.write_text(rendered, encoding='utf-8')
    print(json.dumps(dict(check=args.check, scenarios=report['scenario_count'], **report['summary']), ensure_ascii=False))


if __name__ == '__main__':
    main()
