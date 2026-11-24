"""Immediate battlefield conversions with an auditable original deployment.

The original C886..C91D flips a battlefield slot rather than deleting it, and
calls A006 using the receiving ruler's virtue.  City rosters are explicit in
this remake, so a converted officer also moves to a real friendly home with
capacity. Conversions retain their original deployment or reinforcement identity.
"""
from .errors import GameError
from .officers import MAX_BATTLE_PARTICIPANTS, recruitment_loyalty
from . import battle_experience, battle_reinforcements, officer_relations

FIELDS = {'original_side', 'original_city', 'home', 'side'}


def home(state, battle, side, *, actor=None):
    owner = battle['attacker' if side == 'attackers' else 'defender']
    preferred = battle['source' if side == 'attackers' else 'target']
    if actor is not None and ('coalition' in battle['extended'] and side == 'attackers'
                              or battle_reinforcements.FIELD in battle['extended']):
        owner = state.officers[actor['id']].faction_id
        preferred = home_for(battle, actor, side)
    cities = sorted((city for city in state.cities.values() if city.owner == owner),
                    key=lambda city: (city.id != preferred, city.id))
    return next((city for city in cities
        if len(city.roster.officer_ids) < city.roster.rules.city_officer_capacity), None)


def reason(state, battle, target, side, *, actor=None):
    extension = getattr(state, 'extension', {})
    if target['id'] in extension.get('leaders', {}).values():
        return '君主不能被籠絡。'
    # Isolated tactical scoring fixtures need not provide strategic rosters.
    if all(hasattr(city, 'roster') for city in state.cities.values()) and home(state, battle, side, actor=actor) is None:
        return '本方城池已滿員，無法接納歸降武將。'
    return ''


def convert(game, state, battle, actor, target, own, foe):
    failure = reason(state, battle, target, own, actor=actor)
    if failure:
        raise GameError(failure)
    destination = home(state, battle, own, actor=actor)
    if destination is None:
        raise GameError('本方城池已滿員，無法接納歸降武將。')
    battle_experience.convert(battle,actor,target,foe)
    origin = next(city for city in state.cities.values() if target['id'] in city.roster.officer_ids)
    records = battle['extended'].setdefault('defections', {})
    previous = records.get(str(target['id']))
    records[str(target['id'])] = dict(
        original_side=previous['original_side'] if previous else foe,
        original_city=previous['original_city'] if previous else _original_home(battle, target, foe),
        home=destination.id, side=own)
    origin.roster.officer_ids.remove(target['id'])
    destination.roster.officer_ids.append(target['id'])
    officer = state.officers[target['id']]
    officer.faction_id = destination.owner
    leader = state.extension['leaders'].get(destination.owner)
    virtue = state.officers[leader].profile.virtue if leader in state.officers else state.officers[actor['id']].profile.virtue
    officer.loyalty = recruitment_loyalty(virtue, officer.loyalty)
    officer_relations.apply(game,state,target['id'])
    battle[foe].remove(target)
    battle[own].append(target)
    # used is the player's activity receipt, not a prohibition on acting again.
    battle['used'][:] = [ident for ident in battle['used'] if ident != target['id']]
    if (battle['extended'].get('ambush') or {}).get('actor') == target['id']:
        battle['extended']['ambush'] = None
    support = battle['extended']['support'][str(target['id'])]
    support['stunned'] = support['guard'] = 0
    from . import battle_conditions
    battle_conditions.clear(battle,target['id'])
    state.extension['officer_actions'][str(target['id'])] = state.turn
    battle['log'].append(f'{game.person_name(state,target["id"])}接受籠絡，立即加入本軍；忠誠{officer.loyalty}。')
    battle['log'][:] = battle['log'][-80:]


def validate(game, state, battle):
    records = battle['extended'].get('defections', {})
    if not isinstance(records, dict) or len(records) > MAX_BATTLE_PARTICIPANTS:
        raise ValueError('Invalid battlefield conversion ledger')
    units = {str(unit['id']): (side, unit) for side in ('attackers','defenders') for unit in battle[side]}
    original_counts = {'attackers': 0, 'defenders': 0}
    reinforcements = battle_reinforcements.joined(battle)
    for key, (side, unit) in units.items():
        record = records.get(key)
        if record is None:
            if key not in reinforcements:
                original_counts[side] += 1
            continue
        if (not isinstance(record, dict) or set(record) != FIELDS
                or record['original_side'] not in original_counts or record['side'] != side
                or record['original_city'] != _original_home(battle, unit, record['original_side'])
                or record['home'] not in state.cities):
            raise ValueError('Invalid battlefield conversion identity')
        city = state.cities[record['home']]
        officer = state.officers[unit['id']]
        coalition = battle['extended'].get('coalition')
        owners = (coalition['provisions'] if coalition and side == 'attackers'
                  else (battle['attacker' if side == 'attackers' else 'defender'],))
        if (city.owner not in owners and (battle_reinforcements.FIELD not in battle['extended']
                or battle_reinforcements.side_for(state, battle, city.owner) != side)
                or officer.faction_id != city.owner
                or unit['id'] not in city.roster.officer_ids
                or unit['id'] in state.extension['leaders'].values()):
            raise ValueError('Invalid converted officer ownership')
        if key not in reinforcements:
            original_counts[record['original_side']] += 1
    if (set(records) - set(units) or original_counts['attackers']<1
            or any(n > game.catalog.rules.battle_officers_per_side for n in original_counts.values())):
        raise ValueError('Battle conversions exceed original deployment')


def _original_home(battle, unit, side):
    reinforcement = battle_reinforcements.joined(battle).get(str(unit['id']))
    if reinforcement is not None:
        return reinforcement['home']
    if side == 'defenders':
        return battle['target']
    sources = battle['extended'].get('coalition', {}).get('sources', {})
    return sources.get(str(unit['id']), battle['source'])


def home_for(battle, unit, side):
    record = battle['extended'].get('defections', {}).get(str(unit['id']))
    return record['home'] if record else _original_home(battle, unit, side)
