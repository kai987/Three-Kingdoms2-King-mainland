"""Check retained ROM evidence and the current sourced campaign stat policy.

This offline validator never opens a ROM. The importer creates its reference
from the pinned user ROM; gameplay and ordinary builds need only that source.
Martial strength/intellect deliberately retain the separate SAN14 conversion.
"""
from hashlib import sha256


ORIGINAL_ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ORIGINAL_RECORD_OFFSET = 0x22010
ORIGINAL_RECORD_SIZE = 12


def validate_original_virtue(people, reference, identities):
    if (reference.get('schema') != 'tk2-original-officer-stats-v1'
            or reference.get('rom_sha256') != ORIGINAL_ROM_SHA256
            or identities.get('rom_sha256') != ORIGINAL_ROM_SHA256):
        raise ValueError('Original officer source ROM differs')
    records = reference['records']
    bindings = {r['original_id']: r['person_id'] for r in identities['records']}
    if len(records) != 237 or len(bindings) != 237:
        raise ValueError('Original officer record coverage differs')
    seen, bound = set(), set()
    for row in records:
        ident = row['original_id']
        if type(ident) is not int or not 0 <= ident < 237 or ident in seen:
            raise ValueError('Invalid original officer identity')
        seen.add(ident)
        raw = bytes.fromhex(row['record_hex'])
        if (len(raw) != ORIGINAL_RECORD_SIZE
                or row['rom_offset'] != ORIGINAL_RECORD_OFFSET + ident * ORIGINAL_RECORD_SIZE
                or row['record_sha256'] != sha256(raw).hexdigest()
                or row['virtue'] != raw[4] or row['experience_raw'] != int.from_bytes(raw[6:8], 'little')
                or row['person_id'] != bindings[ident]):
            raise ValueError('Original officer reference bytes differ')
        pid = row['person_id']
        if pid is None:
            continue
        if pid in bound or pid not in people:
            raise ValueError('Duplicate or absent original person binding')
        bound.add(pid)
        person = people[pid]
        archived = person.get('pre_campaign_stat_policy_v1')
        if archived is not None:
            design = archived.get('virtue_design') or {}
            if (archived.get('profile', {}).get('virtue') != raw[4]
                    or design.get('status') != 'verified_original'
                    or design.get('virtue') != raw[4] or design.get('original_id') != ident
                    or design.get('rom_sha256') != ORIGINAL_ROM_SHA256
                    or design.get('rom_offset') != row['rom_offset'] + 4
                    or design.get('record_sha256') != row['record_sha256']):
                raise ValueError('Retained original virtue evidence differs: ' + pid)
    if len(bound) != 221:
        raise ValueError('Reviewed original person coverage differs')
    return bound


def validate_campaign_stats(people, reference, abilities=None):
    """Offline builds fail if an era override changes the new common policy.

    The public source is retained as numerical facts with row-level provenance;
    it is a third-party transcription, not an official export or a historical
    measurement. Only explicitly reviewed identities participate in the join.
    """
    from remake.officers import OfficerProfile, appearance_values
    records = reference.get('records')
    if not isinstance(records, list) or len(records) != 237:
        raise ValueError('Public original officer reference coverage differs')
    matched, seen = {}, set()
    for row in records:
        key = row.get('source_row_id')
        if not isinstance(key, str) or key in seen:
            raise ValueError('Public original officer row identity differs')
        seen.add(key)
        pid = row.get('person_id')
        if pid is not None:
            if pid in matched or pid not in people:
                raise ValueError('Duplicate or absent public officer identity')
            if not str(row.get('identity_status', '')).startswith('reviewed_'):
                raise ValueError('Unreviewed public officer identity')
            matched[pid] = row
    ability_by_id = {row['person_id']: row['stats'] for row in (abilities or {}).get('abilities', [])}
    if abilities is not None and len(ability_by_id) != 1000:
        raise ValueError('SAN14 ability reference coverage differs')
    sourced = defaults = 0
    for pid, person in people.items():
        profile = person['profile']
        raw = profile['source_stats']
        old = person.get('pre_campaign_stat_policy_v1')
        if not isinstance(old, dict) or not isinstance(old.get('profile'), dict):
            raise ValueError('Previous stat policy checkpoint missing: ' + pid)
        if any(profile[key] != old['profile'][key] for key in
               ('martial_strength', 'intellect', 'terrain_affinity', 'source_stats')):
            raise ValueError('Unrequested officer ability changed: ' + pid)
        if abilities is not None and pid in ability_by_id and raw != ability_by_id[pid]:
            raise ValueError('SAN14 source abilities differ: ' + pid)
        charisma = raw.get('charisma')
        design = person.get('virtue_design') or {}
        if charisma is not None:
            if type(charisma) is not int or not 1 <= charisma <= 100:
                raise ValueError('Invalid SAN14 charisma: ' + pid)
            if (profile['virtue'] != min(99, charisma)
                    or design.get('status') != 'san14_charisma'
                    or design.get('virtue') != profile['virtue']):
                raise ValueError('SAN14 charisma virtue was overwritten: ' + pid)
            sourced += 1
        else:
            if profile['virtue'] != 60 or design.get('status') != 'configured_default':
                raise ValueError('Missing-charisma default differs: ' + pid)
            defaults += 1
        origin = matched.get(pid)
        initial = person.get('initialization')
        if not isinstance(initial, dict):
            raise ValueError('Initial health and loyalty policy missing: ' + pid)
        health = origin['health'] if origin is not None else 80
        if (type(health) is not int or not 1 <= health <= 99
                or initial.get('health') != health
                or initial.get('default_loyalty') != 80
                or profile['health_max'] != max(old['profile']['health_max'], health)):
            raise ValueError('Initial health or retained recovery cap differs: ' + pid)
        loyalty = initial.get('source_loyalty')
        if origin is None:
            if loyalty is not None:
                raise ValueError('Unsourced original loyalty: ' + pid)
        elif (not isinstance(loyalty, dict)
                or loyalty.get('source_row_id') != origin['source_row_id']
                or loyalty.get('value') != origin['loyalty']
                or loyalty.get('display') != origin['loyalty_display']
                or loyalty.get('source_faction_label') != origin['faction_label']
                or loyalty.get('faction_ids') != origin['faction_ids']
                or loyalty.get('reference') != 'game/config/references/cnblogs-officer-stats.json'):
            raise ValueError('Original loyalty source differs: ' + pid)
        typed = OfficerProfile(**profile)
        appearance_values(typed, initial)
    if (sourced, defaults) != (1000, len(people) - 1000):
        raise ValueError('Current charisma/default policy coverage differs')
    return dict(charisma=sourced, default=defaults, original_health=len(matched))
