"""Pure arrival-aware planning over the audited native deployment rectangles.

Native neighboring template pairs take priority. Expanded regional associations
use an explicitly authorial direction choice, never a fabricated NESW code.
The caller owns new-battle initialization; existing positions are not inputs to
the metadata validator and this module never changes a battle or draws RNG.
"""
from functools import lru_cache
import json
from pathlib import Path

SCHEMA = 'tk2-battle-deployment-v1'
FIELDS = {'schema','arrival_city','target_map','arrival_map','paired_source_map',
          'attacker_zone','defender_zone','policy'}
POLICIES = ('native_pair','regional_direction')
COLUMNS, ROWS = 31,19
SIDES = ('defenders','attackers')
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


@lru_cache(maxsize=1)
def _library():
    root = Path(__file__).resolve().parents[2]
    reference = json.loads((root/'game/config/references/original-battle-deployment-v1.json').read_text())
    bindings = json.loads((root/'game/config/battlefield-city-bindings.json').read_text())
    expected = {f'original-{index:02d}' for index in range(30)}
    _require(reference.get('schema') == 'tk2-original-battle-deployment-v1'
        and reference.get('rom_sha256') == ROM_SHA and set(reference.get('cities',{})) == expected
        and bindings.get('schema') == 'tk2-battlefield-city-bindings-v1',
        'Invalid native deployment library')
    maps = {city:row['map_id'] for city,row in bindings['cities'].items()}
    _require(all(value in expected for value in maps.values()),'Invalid native deployment binding')
    return reference['cities'],maps


def _field(field, city):
    _require(isinstance(field,dict),'Invalid deployment field')
    classes,camp = field.get('classes'),field.get('camp')
    _require(isinstance(classes,(list,tuple)) and len(classes) == ROWS
        and all(isinstance(row,(list,tuple)) and len(row) == COLUMNS
            and all(type(value) is int and 0 <= value <= 5 for value in row) for row in classes)
        and isinstance(camp,(list,tuple)) and len(camp) == 2
        and type(camp[0]) is int and 0 <= camp[0] < COLUMNS
        and type(camp[1]) is int and 0 <= camp[1] < ROWS,
        'Invalid deployment field geometry')
    native = city['sides']['defenders']['zones'][0]['default_points'][0]
    native_y = native['packed_y']-int(native['packed_y'] >= 16)
    _require(tuple(camp) == (native['x'],native_y) and classes[camp[1]][camp[0]] == 5,
        'Deployment field differs from its native target template')
    return tuple(camp)


def _position(city):
    point = city.get('position')
    # Controlled catalogs may omit presentation coordinates. The documented
    # no-arrival-geometry tie-break then applies instead of inventing geography.
    return tuple(point) if (isinstance(point,(list,tuple)) and len(point) == 2
        and all(type(value) is int for value in point)) else None


def _rectangle_vector(zone, camp):
    bounds = zone['bounds']
    xs = range(max(0,bounds['min_x']),min(COLUMNS,bounds['max_x_exclusive']))
    ys = [y-int(y >= 16) for y in range(max(0,bounds['min_packed_y']),
           min(20,bounds['max_packed_y_exclusive'])) if y != 15]
    _require(bool(xs) and bool(ys),'Empty visible deployment rectangle')
    # Doubled centers make the angle comparison entirely integer arithmetic.
    vector = xs[0]+xs[-1]-2*camp[0],ys[0]+ys[-1]-2*camp[1]
    _require(vector != (0,0),'Deployment edge rectangle is centered on the castle')
    return vector


def _better_direction(candidate, previous):
    """Compare cosines exactly; the common arrival-vector norm cancels."""
    dot,norm = candidate
    old_dot,old_norm = previous
    sign,old_sign = (dot > 0)-(dot < 0),(old_dot > 0)-(old_dot < 0)
    if sign != old_sign:
        return sign > old_sign
    if not sign:
        return False
    left,right = dot*dot*old_norm,old_dot*old_dot*norm
    return left > right if sign > 0 else left < right


def _selection(catalog, battle, field, arrival_city):
    cities,bindings = _library()
    target_map = bindings.get(battle['target'])
    if target_map is None:
        return None
    _require(type(arrival_city) is str and arrival_city in catalog.map_cities
        and battle['target'] in catalog.map_cities,'Invalid deployment arrival city')
    city = cities[target_map]
    camp = _field(field,city)
    arrival_map = bindings.get(arrival_city)
    native_source = int(arrival_map.removeprefix('original-')) if arrival_map else None
    pair = next((row for row in city['neighbors']
        if row['source_original_city_index'] == native_source),None)
    policy = 'native_pair' if pair is not None else 'regional_direction'
    if pair is None:
        target_point,arrival_point = _position(catalog.map_cities[battle['target']]),_position(catalog.map_cities[arrival_city])
        vector = ((arrival_point[0]-target_point[0],arrival_point[1]-target_point[1])
                  if arrival_point is not None and target_point is not None else (0,0))
        best = None
        # Duplicate rectangles and exactly equal angles use the lowest original
        # neighboring city index, independent of JSON order or unit ordering.
        for row in sorted(city['neighbors'],key=lambda value:value['source_original_city_index']):
            zone = city['sides']['attackers']['zones'][row['attacker_zone_index']]
            dx,dy = _rectangle_vector(zone,camp)
            score = dx*vector[0]+dy*vector[1],dx*dx+dy*dy
            if best is None or _better_direction(score,best):
                best,pair = score,row
    _require(pair is not None,'Native deployment target has no arrival templates')
    provenance = dict(schema=SCHEMA,arrival_city=arrival_city,target_map=target_map,
        arrival_map=arrival_map,paired_source_map=f"original-{pair['source_original_city_index']:02d}",
        attacker_zone=pair['attacker_zone_index'],defender_zone=pair['defender_zone_index'],policy=policy)
    zones = {side:city['sides'][side]['zones'][pair[singular+'_zone_index']]
        for side,singular in (('attackers','attacker'),('defenders','defender'))}
    return provenance,zones


def _cells(zone):
    bounds,seen,result = zone['bounds'],set(),[]
    for point in zone['default_points']:
        x,y = point['x'],point['packed_y']
        if (not 0 <= x < COLUMNS or not 0 <= y < 20 or y == 15
                or not bounds['min_x'] <= x < bounds['max_x_exclusive']
                or not bounds['min_packed_y'] <= y < bounds['max_packed_y_exclusive']):
            continue
        key = x,y-int(y >= 16)
        if key not in seen:
            result.append(key)
            seen.add(key)
    return result


def plan(catalog, battle, field, *, arrival_city=None):
    """Return fresh positions/provenance, or None for an unknown target ID.

    The optional arrival city is the penultimate city of the actual route,
    not necessarily battle.source. This planner is for newly created armies
    of at most ten units each. It refuses to propose new positions for an
    already initialized tactical battle. Metadata validation is separate.
    """
    if battle['target'] not in _library()[1]:
        return None  # Keep the existing controlled-test anchor fallback intact.
    _require('tactical' not in battle.get('extended',{}),
        'Cannot redeploy an initialized tactical battle')
    arrival_city = battle['source'] if arrival_city is None else arrival_city
    provenance,zones = _selection(catalog,battle,field,arrival_city)
    identities = []
    for side in SIDES:
        units = battle[side]
        _require(isinstance(units,list) and len(units) <= 10,'Invalid initial deployment army size')
        for unit in units:
            ident = unit.get('id') if isinstance(unit,dict) else None
            _require(type(ident) is int and ident >= 0 or type(ident) is str and 0 < len(ident) <= 128,
                'Invalid initial deployment unit identity')
            identities.append(str(ident))
    _require(bool(battle['attackers']) and len(identities) == len(set(identities)),
        'Invalid or duplicate initial deployment units')
    occupied,positions = set(),{}
    for side in SIDES:
        cells = [cell for cell in _cells(zones[side]) if cell not in occupied]
        _require(len(cells) >= len(battle[side]),'Insufficient native deployment candidates')
        for unit,(x,y) in zip(battle[side],cells):
            positions[str(unit['id'])] = dict(x=x,y=y)
            occupied.add((x,y))
    return dict(positions=positions,provenance=provenance)


def validate_provenance(catalog, battle, field, record):
    """Validate the closed receipt without consulting any live unit positions.

    Movement, casualties and immediate conversions must not regenerate an
    army or change its recorded approach. Old battles may simply omit this
    optional receipt; the caller must not create one while loading a save.
    """
    _require(type(record) is dict and set(record) == FIELDS
        and record['schema'] == SCHEMA and record['policy'] in POLICIES
        and type(record['attacker_zone']) is int and 0 <= record['attacker_zone'] <= 3
        and type(record['defender_zone']) is int and 0 <= record['defender_zone'] <= 1,
        'Invalid deployment provenance fields')
    selected = _selection(catalog,battle,field,record['arrival_city'])
    _require(selected is not None and record == selected[0],'Deployment provenance does not match its arrival')
