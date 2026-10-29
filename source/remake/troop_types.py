"""Read-only effective troop types, separate from saved baseline profiles.

This explicit rules layer changes future tactical movement and visible flags;
it does not migrate saved profiles, random state or frozen strategic routes.
"""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path

SCHEMA='tk2-officer-troop-types-v1'
VIEW_SCHEMA='tk2-officer-troop-types-view-v1'
RULES_VERSION='officer-troop-types-v1'
SOURCE_KINDS=frozenset(('verified_original_rom','original_table_transcription',
    'design_trait_inference','design_region_inference','retained_design','fallback_design'))


def _valid_code(value):
    return type(value)is int and value in (0,1,2)


def validate(data):
    if (not isinstance(data,dict) or data.get('schema')!=SCHEMA
            or data.get('rules_version')!=RULES_VERSION
            or data.get('original_field',{}).get('byte_index')!=11
            or data.get('original_field',{}).get('record_offset')!=139280
            or data.get('original_field',{}).get('bits')!=[2,3]
            or not isinstance(data.get('records'),dict)):
        raise ValueError('Invalid troop-type policy')
    rows=data['records']
    raw=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    if sha256(raw).hexdigest()!=data.get('records_sha256'):
        raise ValueError('Troop-type policy record checksum')
    originals=set()
    for pid,row in rows.items():
        if (not isinstance(pid,str) or not isinstance(row,dict) or row.get('person_id')!=pid
                or not _valid_code(row.get('code')) or not _valid_code(row.get('base_code'))
                or row.get('source_kind')not in SOURCE_KINDS):
            raise ValueError('Invalid effective troop-type row')
        if row['source_kind']=='verified_original_rom':
            original=row.get('original_id');byte=row.get('byte11')
            if (type(original)is not int or not 0<=original<237 or original in originals
                    or type(byte)is not int or not 0<=byte<=255
                    or row.get('rom_offset')!=139280+original*12+11
                    or ((byte>>2)&3)!=row['code'] or row.get('raw_code')!=row['code']):
                raise ValueError('Invalid original troop-type evidence')
            originals.add(original)
    if len(rows)!=data.get('counts',{}).get('people') or len(originals)!=221:
        raise ValueError('Troop-type policy coverage')
    return data


@lru_cache(maxsize=1)
def policy():
    path=Path(__file__).resolve().parents[2]/'game/config/references/officer-troop-types-v1.json'
    return validate(json.loads(path.read_text()))


def effective_affinity(person_id,base):
    if not _valid_code(base):
        raise ValueError('Invalid baseline troop affinity')
    row=policy()['records'].get(person_id)
    return row['code'] if row is not None else base


def metadata(person_id,base):
    code=effective_affinity(person_id,base)
    row=policy()['records'].get(person_id)
    result=dict(person_id=person_id,code=code,base_code=base,
        source_kind=row['source_kind'] if row else 'generated_design' if str(person_id).startswith('clerk-') else 'fallback_design')
    if row and row.get('original_id')is not None:
        result['original_id']=row['original_id']
    return result


def view(game,state):
    data=policy()
    return dict(schema=VIEW_SCHEMA,rules_version=RULES_VERSION,records_sha256=data['records_sha256'],
        source_policy='verified_original_rom_then_reviewed_transcription_then_labelled_static_design',
        saved_profile_policy='preserve_baseline_profile; effective_type_controls_future_tactical_movement_and_display',
        kinds=deepcopy(data['kinds']),
        officers={str(ident):metadata(officer.person_id,officer.profile.terrain_affinity)
                  for ident,officer in state.officers.items()}if state else {})
