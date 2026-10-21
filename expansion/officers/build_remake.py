#!/usr/bin/env python3
"""Build modern profile candidates from saved research, never a ROM/IR runtime."""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import csv
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.officers import (GameRules, PersonDefinition, YearState,
                             convert_profile, virtue_score, year_state)


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    data = read('data/roster-candidates.json')
    matches = read('data/original-overlap-audit.json')['matches']
    designs = read('virtue-designs.json')['profiles']
    rules_data = read('remake-rules.json')
    rules = GameRules(rules_data['city_officer_capacity'], rules_data['battle_officers_per_side'],
                      rules_data['runtime_capacity'])
    legacy_ids = {m['candidate_person_id']: m['original_officer_id'] for m in matches}
    designs_by_id = {p['person_id']: p for p in designs}
    with (ROOT / 'analysis/officer_fields/officers-decoded.csv').open(encoding='utf-8-sig', newline='') as stream:
        legacy = {int(p['id']): p for p in csv.DictReader(stream)}
    people, profiles = [], []
    assert len({p['person_id'] for p in data['officers']}) == len(data['officers'])
    for runtime_id, record in enumerate(data['officers']):
        rules.officer_id(runtime_id)
        c = record['chronology']
        person = PersonDefinition(record['person_id'], record['name_simplified'], c['game_birth_year'],
                                  c['game_appearance_year'], c['game_death_year'], c['basis'])
        people.append(person)
        legacy_id = legacy_ids.get(person.person_id)
        original = None
        if legacy_id is not None:
            original = {k: int(legacy[legacy_id][k]) for k in (
                'health', 'martial_strength', 'intellect', 'virtue', 'terrain_affinity_code')}
        design = designs_by_id.get(person.person_id)
        if design:
            assert virtue_score(design['dimensions']) == design['virtue']
        profile = convert_profile(legacy=original, virtue_design=design)
        profiles.append({
            'person_id': person.person_id, 'name': person.name, 'runtime_id': runtime_id,
            'legacy_nes_officer_id': legacy_id, 'chronology': asdict(person),
            'service_year_is_historical_first_office': False,
            'profile': asdict(profile), 'missing_required_fields': list(profile.missing),
            'base_attributes_complete': not profile.missing,
            'scenario_membership_configured': False,
            'ready_for_playable_scenario': False,
            'initialization': {'troops': 0, 'weapon_id': 0, 'armor_id': 0, 'experience': 0,
                               'tier': 0, 'loyalty': None, 'faction_id': None, 'city_id': None},
        })
    yearly = []
    for year in (184, 190, 194, 200, 207, 217, 221, 227, 230, 249, 251):
        counts = Counter(year_state(p, year).value for p in people)
        assert sum(counts.values()) == len(people)
        yearly.append({'year': year, 'total_library': len(people),
                       'states': dict(sorted(counts.items())),
                       'annual_available': counts[YearState.AVAILABLE.value],
                       'death_year_review': counts[YearState.DEATH_YEAR_REVIEW.value],
                       'actually_serving': None,
                       'note': '年表资格，不等于已入城人数；来源251假想剧本另用其状态，不套此历史年表'})
    summary = {'library_people': len(people), 'city_capacity': rules.city_officer_capacity,
               'battle_per_side': rules.battle_officers_per_side, 'battle_total': 20,
               'runtime_capacity': rules.runtime_capacity,
               'san14_abilities_sourced': 0,
               'verified_legacy_profile_crosswalks': len(legacy_ids),
               'history_informed_virtue_designs': len(designs),
               'base_attributes_complete': sum(p['base_attributes_complete'] for p in profiles),
               'base_attributes_incomplete': sum(not p['base_attributes_complete'] for p in profiles),
               'playable_scenario_memberships_configured': 0,
               'original_rom_modified': False, 'recovered_legacy_source_modified': False,
               'independent_data_model_implemented': True,
               'standalone_playable_loop_implemented': False}
    output = {'schema': 'independent-remake-officer-profiles-v1', 'summary': summary,
              'profiles': profiles}
    (HERE / 'data/remake-profiles.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    (HERE / 'data/remake-year-populations.json').write_text(json.dumps(yearly, ensure_ascii=False, indent=2) + '\n')
    with (HERE / 'data/remake-profiles.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['person_id', 'name', 'runtime_id', 'legacy_nes_officer_id', 'birth_year',
                  'service_year', 'death_year', 'health_max', 'martial_strength', 'intellect',
                  'virtue', 'terrain_affinity', 'missing_required_fields', 'ready_for_playable_scenario']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for p in profiles:
            row = {k: p[k] for k in fields[:4]}
            row.update({k: p['chronology'][k] for k in ('birth_year', 'service_year', 'death_year')})
            row.update({k: p['profile'][k] for k in ('health_max', 'martial_strength', 'intellect',
                                                  'virtue', 'terrain_affinity')})
            row['missing_required_fields'] = ';'.join(p['missing_required_fields'])
            row['ready_for_playable_scenario'] = p['ready_for_playable_scenario']
            writer.writerow(row)
    (HERE / 'remake-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
