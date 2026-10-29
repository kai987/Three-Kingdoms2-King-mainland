"""Immediate battlefield conversions with an auditable original deployment.

The original C886..C91D flips a battlefield slot rather than deleting it, and
calls A006 using the receiving ruler's virtue.  City rosters are explicit in
this remake, so a converted officer also moves to a real friendly home with
capacity.  The twenty initially deployed identities remain the entire battle.
"""
from .errors import GameError
from .officers import recruitment_loyalty

FIELDS = {'original_side', 'original_city', 'home', 'side'}


def home(state, battle, side):
    owner = battle['attacker' if side == 'attackers' else 'defender']
    preferred = battle['source' if side == 'attackers' else 'target']
    cities = sorted((city for city in state.cities.values() if city.owner == owner),
                    key=lambda city: (city.id != preferred, city.id))
    return next((city for city in cities
        if len(city.roster.officer_ids) < city.roster.rules.city_officer_capacity), None)


def reason(state, battle, target, side):
    extension = getattr(state, 'extension', {})
    if target['id'] in extension.get('leaders', {}).values():
        return '君主不能被籠絡。'
    # Isolated tactical scoring fixtures need not provide strategic rosters.
    if all(hasattr(city, 'roster') for city in state.cities.values()) and home(state, battle, side) is None:
        return '本方城池已滿員，無法接納歸降武將。'
    return ''


def convert(game, state, battle, actor, target, own, foe):
    failure = reason(state, battle, target, own)
    if failure:
        raise GameError(failure)
    destination = home(state, battle, own)
    if destination is None:
        raise GameError('本方城池已滿員，無法接納歸降武將。')
    origin = next(city for city in state.cities.values() if target['id'] in city.roster.officer_ids)
    records = battle['extended'].setdefault('defections', {})
    previous = records.get(str(target['id']))
    records[str(target['id'])] = dict(
        original_side=previous['original_side'] if previous else foe,
        original_city=previous['original_city'] if previous else battle['source' if foe == 'attackers' else 'target'],
        home=destination.id, side=own)
    origin.roster.officer_ids.remove(target['id'])
    destination.roster.officer_ids.append(target['id'])
    officer = state.officers[target['id']]
    officer.faction_id = destination.owner
    leader = state.extension['leaders'].get(destination.owner)
    virtue = state.officers[leader].profile.virtue if leader in state.officers else state.officers[actor['id']].profile.virtue
    officer.loyalty = recruitment_loyalty(virtue, officer.loyalty)
    battle[foe].remove(target)
    battle[own].append(target)
    # used is the player's activity receipt, not a prohibition on acting again.
    battle['used'][:] = [ident for ident in battle['used'] if ident != target['id']]
    if (battle['extended'].get('ambush') or {}).get('actor') == target['id']:
        battle['extended']['ambush'] = None
    support = battle['extended']['support'][str(target['id'])]
    support['stunned'] = support['guard'] = 0
    state.extension['officer_actions'][str(target['id'])] = state.turn
    battle['log'].append(f'{game.person_name(state,target["id"])}接受籠絡，立即加入本軍；忠誠{officer.loyalty}。')
    battle['log'][:] = battle['log'][-80:]


def validate(game, state, battle):
    records = battle['extended'].get('defections', {})
    if not isinstance(records, dict) or len(records) > 20:
        raise ValueError('Invalid battlefield conversion ledger')
    units = {str(unit['id']): (side, unit) for side in ('attackers','defenders') for unit in battle[side]}
    original_counts = {'attackers': 0, 'defenders': 0}
    for key, (side, unit) in units.items():
        record = records.get(key)
        if record is None:
            original_counts[side] += 1
            continue
        if (not isinstance(record, dict) or set(record) != FIELDS
                or record['original_side'] not in original_counts or record['side'] != side
                or record['original_city'] != battle['source' if record['original_side']=='attackers' else 'target']
                or record['home'] not in state.cities):
            raise ValueError('Invalid battlefield conversion identity')
        owner = battle['attacker' if side=='attackers' else 'defender']
        city = state.cities[record['home']]
        officer = state.officers[unit['id']]
        if (city.owner != owner or officer.faction_id != owner
                or unit['id'] not in city.roster.officer_ids
                or unit['id'] in state.extension['leaders'].values()):
            raise ValueError('Invalid converted officer ownership')
        original_counts[record['original_side']] += 1
    if (set(records) - set(units) or original_counts['attackers']<1
            or any(n > game.catalog.rules.battle_officers_per_side for n in original_counts.values())):
        raise ValueError('Battle conversions exceed original deployment')


def home_for(battle, unit, side):
    record = battle['extended'].get('defections', {}).get(str(unit['id']))
    return record['home'] if record else battle['source' if side=='attackers' else 'target']
