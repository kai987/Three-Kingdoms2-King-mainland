"""Check original virtue against retained ROM bytes and reviewed identities.

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
        virtue = person['profile']['virtue']
        design = person.get('virtue_design') or {}
        if (virtue != raw[4] or design.get('status') != 'verified_original'
                or design.get('virtue') != virtue or design.get('original_id') != ident
                or design.get('rom_sha256') != ORIGINAL_ROM_SHA256
                or design.get('rom_offset') != row['rom_offset'] + 4
                or design.get('record_sha256') != row['record_sha256']):
            raise ValueError('Original virtue was overwritten: ' + pid)
    if len(bound) != 220:
        raise ValueError('Reviewed original person coverage differs')
    return bound
