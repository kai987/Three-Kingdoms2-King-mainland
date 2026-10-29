"""Reviewed ruler/officer ties, applied only at explicit allegiance transitions.

The dated pairs are remake loyalty policy, not measurements from the historical
sources. Reading a relation never repairs saved loyalty or advances game RNG.
"""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import urlsplit

from .officers import appearance_values

SCHEMA = 'tk2-officer-relations-v1'
RULES_VERSION = 'officer-relations-v1'
VIEW_SCHEMA = 'tk2-officer-relations-view-v1'
KINDS = frozenset(('parent_child', 'sibling', 'uncle_nephew', 'cousin',
                   'adopted', 'affinal', 'trust'))
FIELDS = {'id', 'ruler_id', 'person_id', 'kind', 'reason', 'sources'}


def _year(value):
    return type(value) is int and 1 <= value <= 400


def validate(data):
    if (not isinstance(data, dict) or data.get('schema') != SCHEMA
            or data.get('rules_version') != RULES_VERSION
            or not isinstance(data.get('records'), list)
            or not isinstance(data.get('exceptions'), list)):
        raise ValueError('Invalid officer relationship policy')
    seen = set()
    for blocked, rows in ((False, data['records']), (True, data['exceptions'])):
        for row in rows:
            required = FIELDS if blocked else FIELDS | {'floor'}
            if (not isinstance(row, dict) or not required <= set(row)
                    or set(row) - required - {'start_year', 'end_year'}
                    or any(not isinstance(row.get(key), str) or not row[key].strip()
                           for key in ('id', 'ruler_id', 'person_id'))
                    or row['id'] in seen or row['ruler_id'] == row['person_id']
                    or row.get('kind') not in KINDS
                    or not isinstance(row.get('reason'), dict)
                    or set(row['reason']) != {'zh', 'ja'}
                    or any(not isinstance(value, str) or not value.strip()
                           for value in row['reason'].values())
                    or not isinstance(row.get('sources'), list) or not row['sources']
                    or any(not isinstance(url, str) or urlsplit(url).scheme not in {'http', 'https'}
                           or not urlsplit(url).netloc for url in row['sources'])
                    or any(not _year(row[key]) for key in ('start_year', 'end_year') if key in row)
                    or row.get('start_year', 1) > row.get('end_year', 400)
                    or (not blocked and (type(row.get('floor')) is not int
                                         or not 1 <= row['floor'] <= 99))):
                raise ValueError('Invalid officer relationship record')
            seen.add(row['id'])
    return data


@lru_cache(maxsize=1)
def policy():
    path = Path(__file__).resolve().parents[2] / 'game/config/references/officer-relations-v1.json'
    return validate(json.loads(path.read_text(encoding='utf-8')))


def validate_catalog(catalog):
    """Relationships bind exact canonical people, including scenario exclusions."""
    for group in ('records', 'exceptions'):
        for row in policy()[group]:
            if row['ruler_id'] not in catalog.ids or row['person_id'] not in catalog.ids:
                raise ValueError('Unknown officer relationship identity')


def relation(ruler_id, person_id, year):
    """Return one dated directed tie; an explicit exception takes precedence."""
    if not _year(year):
        raise ValueError('Invalid officer relationship year')
    data = policy()
    for blocked, group in ((True, 'exceptions'), (False, 'records')):
        matches = [row for row in data[group]
                   if row['ruler_id'] == ruler_id and row['person_id'] == person_id
                   and row.get('start_year', 1) <= year <= row.get('end_year', 400)]
        if matches:
            # Several independently attested ties can coexist. A deterministic
            # strongest floor avoids additive stacking; exceptions always win.
            row = min(matches, key=lambda item: (-item.get('floor', 0), item['id']))
            return dict(deepcopy(row), floor=0 if blocked else row['floor'], blocked=blocked)
    return None


def _raised(value, metadata):
    return max(value, min(99, metadata['floor'])) if metadata and not metadata['blocked'] else value


def opening_values(catalog, ident, *, faction_id=None, is_ruler=False):
    """One read-only source of opening health/loyalty for previews and new games."""
    values = appearance_values(catalog.profiles[ident], catalog.by_id[ident].get('initialization'),
                               faction_id=faction_id, is_ruler=is_ruler)
    if faction_id is None or is_ruler:
        return values
    leader = catalog.data['faction_rulers'].get(faction_id)
    leader_row = catalog.by_id.get(leader)
    opening = next((row for row in catalog.data['initial_officers']
                    if row['person_id'] == leader_row['person_id']), None) if leader_row else None
    if (opening is None or not opening.get('ruler')
            or catalog.data['initial_owners'].get(opening['city']) != faction_id):
        return values
    metadata = relation(leader_row['person_id'], catalog.by_id[ident]['person_id'], catalog.data['start_year'])
    values['loyalty'] = _raised(values['loyalty'], metadata)
    return values


def current(state, ident):
    """Resolve the actual living ruler, never the scenario's former ruler."""
    officer = state.officers.get(ident)
    if officer is None or not officer.alive or officer.faction_id is None:
        return None
    leader_id = state.extension.get('leaders', {}).get(officer.faction_id)
    leader = state.officers.get(leader_id)
    if (leader is None or leader_id == ident or not leader.alive
            or leader.faction_id != officer.faction_id):
        return None
    return relation(leader.person_id, officer.person_id, state.year)


def apply(game, state, ident):
    """Call only after an actual opening/allegiance/ruler transition commits."""
    metadata = current(state, ident)
    if metadata:
        officer = state.officers[ident]
        officer.loyalty = _raised(officer.loyalty, metadata)
    return metadata


def apply_faction(game, state, faction):
    for ident, officer in state.officers.items():
        if officer.alive and officer.faction_id == faction:
            apply(game, state, ident)


def view(game, state):
    """Explanatory metadata is separate from each officer's current loyalty."""
    return dict(schema=VIEW_SCHEMA, rules_version=RULES_VERSION,
                officers={str(ident): metadata for ident in state.officers
                          if (metadata := current(state, ident)) is not None} if state else {})
