#!/usr/bin/env python3
"""Archived virtue-only importer; current campaigns reject this write policy.

Use import_campaign_stats.py for the current charisma/initial-health policy.

Names are joined through the existing reviewed ROM name-glyph identity map,
never by matching portraits, ability values, runtime IDs or roster ordinals.
The reference retains all 237 raw records; only 220 unambiguous people bind.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'game'))
from officer_stat_sources import (ORIGINAL_RECORD_OFFSET, ORIGINAL_RECORD_SIZE,
                                 ORIGINAL_ROM_SHA256, validate_original_virtue)


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def import_stats(rom):
    if sha256(rom).hexdigest() != ORIGINAL_ROM_SHA256:
        raise ValueError('Different ROM; original virtue import stopped')
    identity_path = ROOT / 'game/config/portrait-identity-map.json'
    identities = json.loads(identity_path.read_text())
    people_path = ROOT / 'game/config/campaigns/people.json'
    pool = json.loads(people_path.read_text())
    if any('pre_campaign_stat_policy_v1' in person for person in pool['people'].values()):
        raise ValueError('The old virtue-only importer is archived. Use import_campaign_stats.py --check; '
                         'the retained ROM reference must not overwrite the current charisma policy.')
    records, differences = [], []
    for binding in identities['records']:
        ident, pid = binding['original_id'], binding['person_id']
        offset = ORIGINAL_RECORD_OFFSET + ident * ORIGINAL_RECORD_SIZE
        raw = rom[offset:offset + ORIGINAL_RECORD_SIZE]
        record_hash = sha256(raw).hexdigest()
        records.append(dict(original_id=ident, person_id=pid,
            transcribed_name=binding['transcribed_name'], rom_offset=offset,
            record_hex=raw.hex(' ').upper(), record_sha256=record_hash,
            virtue=raw[4], experience_raw=int.from_bytes(raw[6:8], 'little')))
        if pid is None:
            continue
        person = pool['people'][pid]
        if (person.get('virtue_design') or {}).get('status') != 'verified_original':
            person['previous_virtue_design'] = deepcopy(person['virtue_design'])
            person['previous_virtue_profile'] = dict(virtue=person['profile']['virtue'],
                basis=person['profile']['basis']['virtue'], configuration=person['configuration']['virtue'])
        previous = person['previous_virtue_profile']
        if previous['virtue'] != raw[4]:
            differences.append(dict(person_id=pid, name=person['name'], original_id=ident,
                previous=previous['virtue'], original=raw[4],
                previous_status=(person['previous_virtue_design'] or {}).get('status', 'legacy')))
        person['profile']['virtue'] = raw[4]
        person['profile']['basis']['virtue'] = 'verified_original_ROM_byte4; reviewed_exact_name_identity'
        person['configuration']['virtue'] = 'verified_original_ROM_value'
        person['virtue_design'] = dict(person_id=pid, name=person['name'], status='verified_original',
            virtue=raw[4], original_id=ident, rom_sha256=ORIGINAL_ROM_SHA256,
            rom_offset=offset + 4, record_sha256=record_hash,
            is_historical_fact=False, dimensions=None,
            identity_basis=binding['identity_basis'],
            design_rationale='採用已核對姓名身分的原版ROM「德」欄位；原版既有值優先於本作歷史評分及預設60。武、知仍採用已確定的SAN14轉換規則。',
            sources=[dict(work='三國志2超級版 NES ROM', section=f'武將記錄{ident}，+4德欄位',
                          reference='game/config/references/original-officer-stats.json')])
    reference = dict(schema='tk2-original-officer-stats-v1', rom_sha256=ORIGINAL_ROM_SHA256,
        record_offset=ORIGINAL_RECORD_OFFSET, record_size=ORIGINAL_RECORD_SIZE,
        field_policy='Only original virtue is applied; SAN14 martial/intellect and remake health/affinity/initialization remain unchanged.',
        identity_source='game/config/portrait-identity-map.json',
        identity_source_sha256=sha256(identity_path.read_bytes()).hexdigest(),
        identity_policy='Reviewed ROM name-glyph transcription and unique exact name/orthographic identity; no likeness, statistical, ordinal or runtime-ID joins.',
        original_records=237, bound_people=220, unbound_original_records=17,
        audit=dict(changed_people=len(differences),
                   prior_default_changes=sum(r['previous_status'] == 'configured_default' for r in differences),
                   prior_design_changes=sum(r['previous_status'] == 'configured_design' for r in differences),
                   unchanged_original_values=220-len(differences), differences=differences), records=records)
    validate_original_virtue(pool['people'], reference, identities)
    return pool, reference


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    pool, reference = import_stats(args.rom.read_bytes())
    outputs = {ROOT/'game/config/campaigns/people.json': pool,
               ROOT/'game/config/references/original-officer-stats.json': reference}
    for path, value in outputs.items():
        data = encode(value)
        if args.check:
            if path.read_text() != data:
                raise ValueError('Original officer import differs: ' + str(path))
        else:
            path.write_text(data)
    print(json.dumps(dict(bound=220, changed=reference['audit']['changed_people'],
                          check=args.check), ensure_ascii=False))
