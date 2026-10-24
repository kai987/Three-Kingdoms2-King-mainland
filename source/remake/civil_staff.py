"""Local civil staff: a separate, deterministic pool outside historical IDs.

Only committed game transactions call synchronization. Views and validation do
not draw randomness, generate people, collect salaries or emit events.
"""
from copy import deepcopy
from hashlib import sha256
import re

from .errors import GameError
from .officers import (OfficerProfile, PersonDefinition, initialize_officer,
                       is_generated_ref, year_state, YearState)


SCHEMA = 'tk2-civil-staff-v1'
RULES = dict(hire_gold=60, monthly_salary=5, candidate_months=3,
             cooldown_months=3, shortage_months=2, ordinary_target=2,
             large_target=3, single_probability=60, large_probability=30,
             guaranteed_after_misses=3, income_bonus_cap_percent=15)
SPECIALTIES = ('commerce', 'farming', 'recruitment')
PORTRAITS = ('clerk-1', 'clerk-2', 'clerk-3')
_ID = re.compile(r'clerk-([0-9]{6,12})\Z')
_CITY_FIELDS = {'owner', 'owner_since_tick', 'shortage_since_month',
                'zero_since_tick', 'last_checked_month', 'misses',
                'cooldown_until_month', 'candidate'}
_RECORD_FIELDS = {'id', 'name', 'portrait', 'specialty', 'profile', 'health',
                  'troops', 'experience', 'offered_month', 'expires_month'}
_EMPLOYEE_FIELDS = _RECORD_FIELDS | {'city', 'owner', 'hired_month', 'paid_month',
                                    'unpaid_months', 'working', 'action_turn'}
_SURNAMES = tuple('王李張劉陳楊黃趙吳周徐孫馬朱胡郭何高林羅鄭梁謝宋唐許韓馮鄧曹彭曾蕭田董袁潘于蔣蔡杜葉程魏蘇呂丁任沈姚盧姜崔鍾譚陸汪范金石廖賈夏韋傅方白孟康秦江尹薛閻段雷侯龍史陶黎賀顧毛郝龔邵萬錢嚴洪武莫孔向湯')
_FIRST = tuple('文子仲公伯元明承景世德思正安永建成士志清廣俊紹興定昌守尚仁')
_LAST = tuple('安平和明成良遠達信義謙寧恭敬賢章方直裕修勤慎誠敏通順泰寬宏忠')


def month_index(state):
    return state.year * 12 + state.month - 1


def _tick(state):
    return month_index(state) * 3 + (state.day - 1) // 10


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _step(value):
    value ^= (value << 13) & 0xffffffff
    value ^= value >> 17
    value ^= (value << 5) & 0xffffffff
    return value & 0xffffffff


def _seed(value):
    return int.from_bytes(sha256(value.encode('utf-8')).digest()[:4], 'little') or 1


def _draw(pool):
    rng = pool['rng']
    rng['state'] = _step(rng['state'])
    rng['draws'] += 1
    return rng['state']


def target(campaign, city_id):
    tier = campaign.catalog.data.get('city_profiles', {}).get(city_id, {}).get('tier')
    return RULES['large_target'] if tier in {'large', 'giant'} else RULES['ordinary_target']


def _historical_count(state, city):
    return sum(not is_generated_ref(ident) and ident in state.officers and state.officers[ident].alive
               for ident in city.roster.officer_ids)


def city_count(state, city_id):
    pool = state.extension.get('civil_staff', {})
    city = state.cities.get(city_id)
    return sum(is_generated_ref(ident) and ident in state.officers and state.officers[ident].alive
               for ident in city.roster.officer_ids) if city else 0


def city_occupancy(state, city):
    """Capacity counts the actual roster, not projected arrivals."""
    return len(city.roster.officer_ids)


def _effective_count(state, city):
    ids = {i for i in city.roster.officer_ids if i in state.officers and state.officers[i].alive}
    # A marching officer remains in the source roster. Only a friendly transfer
    # arriving within three ten-day turns also covers the destination's need.
    for march in state.extension.get('travel', {}).get('marches', []):
        if (march.get('kind') == 'transfer' and march.get('target') == city.id
                and march.get('owner') == city.owner
                and state.turn <= march.get('arrival_turn', -1) <= state.turn + 3):
            path = march.get('quote', {}).get('path', [march.get('source'), city.id])
            if (not path or path[0] not in state.cities or state.cities[path[0]].owner != city.owner
                    or any(key not in state.cities or state.cities[key].owner not in {city.owner, 'neutral'} for key in path)):
                continue
            ids.update(i for i in march['officers'] if i in state.officers and state.officers[i].alive)
    # Transport escorts unload and return home; they never fill a permanent
    # administrative post in the receiving city.
    return len(ids)


def _ledger(state, city):
    m, tick = month_index(state), _tick(state)
    count = _historical_count(state, city)
    return dict(owner=city.owner, owner_since_tick=tick,
                shortage_since_month=m, zero_since_tick=tick if count == 0 else None,
                last_checked_month=None, misses=0, cooldown_until_month=0,
                candidate=None)


def empty(campaign, state):
    """A valid save skeleton; no candidates, income, events or random draws."""
    pool = dict(schema=SCHEMA,
                rng=dict(state=_seed(f'{SCHEMA}:appearance:{state.seed}'), draws=0),
                next_id=1, cities={key: _ledger(state, city) for key, city in state.cities.items()},
                people={}, last_payroll_month=month_index(state))
    for key, city in state.cities.items():
        if _historical_count(state, city) >= target(campaign, key):
            pool['cities'][key]['shortage_since_month'] = None
    return pool


def initialize(campaign, state):
    if 'civil_staff' in state.extension:
        raise ValueError('Civil staff already initialized')
    state.extension['civil_staff'] = empty(campaign, state)
    synchronize(campaign, state, opening=True)


def _immutable_record(campaign, state, number):
    """Independent per-ID source; validation can verify generated attributes."""
    random = _seed(f'{SCHEMA}:person:{state.seed}:{number}')

    def draw():
        nonlocal random
        random = _step(random)
        return random

    names = {row['name'] for row in campaign.catalog.by_id.values()}
    for _ in range(100):
        name = _SURNAMES[draw() % len(_SURNAMES)] + _FIRST[draw() % len(_FIRST)] + _LAST[draw() % len(_LAST)]
        if name not in names:
            break
    else:
        raise ValueError('Civil staff name pool unavailable')
    health = 60 + draw() % 21
    return dict(id=f'clerk-{number:06d}', name=name,
                portrait=PORTRAITS[draw() % len(PORTRAITS)],
                specialty=SPECIALTIES[draw() % len(SPECIALTIES)],
                profile=dict(health_max=health, martial_strength=10 + draw() % 26,
                             intellect=40 + draw() % 26, virtue=60))


def definition(person):
    """Fixed fictional adulthood and life window, anchored to the offer date."""
    value = _seed(f'{SCHEMA}:life:{person["id"]}:{person["name"]}')
    service = person['offered_month'] // 12
    birth = max(1, service - 20 - value % 16)
    death = min(400, birth + 60 + (value >> 8) % 16)
    return PersonDefinition(person['id'], person['name'], birth, service, death,
                            'fictional_generated_life; not_historical')


def officer_profile(person):
    profile = person['profile']
    affinity = _seed(f'{SCHEMA}:affinity:{person["id"]}:{person["name"]}') % 3
    return OfficerProfile(**profile, terrain_affinity=affinity,
        source_stats={}, basis={key: 'fixed_generated_profile; not_historical'
        for key in ('health_max', 'martial_strength', 'intellect', 'virtue', 'terrain_affinity')})


def runtime_view(state, person):
    result = deepcopy(person)
    officer = state.officers.get(person['id'])
    if officer is not None:
        result.update(profile=dict(health_max=officer.profile.health_max,
            martial_strength=officer.profile.martial_strength,
            intellect=officer.profile.intellect, virtue=officer.profile.virtue,
            terrain_affinity=officer.profile.terrain_affinity), health=officer.health,
            troops=officer.troops, experience=officer.experience, loyalty=officer.loyalty,
            alive=officer.alive, faction_id=officer.faction_id,
            weapon_id=officer.weapon_id, armor_id=officer.armor_id,
            chronology=dict(birth_year=definition(person).birth_year,
                service_year=definition(person).service_year, death_year=definition(person).death_year))
    else:
        result.update(loyalty=None, alive=True, faction_id=None)
    return result


def sync_people(state):
    """Location/owner are views of normal officer membership, never city capture."""
    pool = state.extension['civil_staff']
    locations = {ident: city.id for city in state.cities.values() for ident in city.roster.officer_ids}
    for ident, person in pool['people'].items():
        officer = state.officers.get(ident)
        if officer is None:
            continue
        owner = officer.faction_id or 'neutral'
        if person['owner'] != owner:
            person['working'] = False
        person['owner'] = owner
        person['city'] = locations.get(ident, state.extension.get('free_locations', {}).get(ident, person['city']))
        person['action_turn'] = state.extension.get('officer_actions', {}).get(ident, 0)
        if not officer.alive or officer.faction_id in (None, 'neutral'):
            person['working'] = False


def _person_details(person, **extra):
    return dict(staff_id=person['id'], name=person['name'],
                portrait=person['portrait'], **extra)


def _emit(campaign, state, kind, city, *, person=None, factions=None, **details):
    factions = factions if factions is not None else [city.owner]
    if state.player not in factions:
        return
    if person is not None:
        details = _person_details(person, **details)
    campaign._emit_event(state, kind, city_ids=[city.id], person_ids=[],
                         factions=factions,
                         details=details, audience='world')


def _offer(campaign, state, city, row, reason):
    pool = state.extension['civil_staff']
    number = pool['next_id']
    if number > 1000000:
        return
    person = _immutable_record(campaign, state, number)
    pool['next_id'] += 1
    m = month_index(state)
    person.update(health=person['profile']['health_max'], troops=0, experience=0,
                  offered_month=m, expires_month=m + RULES['candidate_months'])
    row['candidate'] = person
    row['misses'] = 0
    _emit(campaign, state, 'staff_candidate', city, person=person, reason=reason)


def _in_battle(state, city_id):
    return bool(state.battle and city_id in (state.battle['source'], state.battle['target']))


def _active(campaign, state, city):
    return city.owner in campaign.catalog.factions and city.owner not in state.extension.get('ended_factions', [])


def _expire(campaign, state, city, row, reason, *, cooldown=True):
    person = row['candidate']
    if person is None:
        return
    row['candidate'] = None
    if cooldown:
        row['cooldown_until_month'] = max(row['cooldown_until_month'], month_index(state) + RULES['cooldown_months'])
    _emit(campaign, state, 'staff_expired', city, person=person, reason=reason)


def _base_income(campaign, city_id):
    rules = campaign.catalog.data['rules']
    return campaign.catalog.data.get('city_income', {}).get(city_id,
        dict(gold=rules.get('monthly_gold_income', 0), grain=rules.get('monthly_grain_income', 0), reserves=0))


def _payroll(campaign, state):
    pool, m = state.extension['civil_staff'], month_index(state)
    if pool['last_payroll_month'] == m:
        return
    pool['last_payroll_month'] = m
    summary = dict(amount=0, paid=0, bonus=dict(gold=0, grain=0, reserves=0),
                   counts=dict(staff=0, total_unpaid=0, cities=0))
    first_city = None
    sync_people(state)
    for key, city in sorted(state.cities.items()):
        employees = sorted((p for p in pool['people'].values() if p['city'] == key
            and p['id'] in city.roster.officer_ids and state.officers[p['id']].alive
            and state.officers[p['id']].faction_id == city.owner), key=lambda p: p['id'])
        if not employees:
            continue
        if not _active(campaign, state, city):
            for person in employees:
                person['working'] = False
            continue
        paid = 0
        base = _base_income(campaign, key)
        contributions = dict(gold=0, grain=0, reserves=0)
        for person in employees:
            if city.gold < RULES['monthly_salary']:
                person['unpaid_months'] += 1
                person['working'] = False
                continue
            city.gold -= RULES['monthly_salary']
            paid += RULES['monthly_salary']
            person.update(paid_month=m, unpaid_months=0, working=True)
            field = dict(commerce='gold', farming='grain', recruitment='reserves')[person['specialty']]
            # The delegation system replaces this legacy per-person bonus.
            if 'domestic' not in state.extension:
                contributions[field] += int(base.get(field, 0)) * (2 + person['profile']['intellect'] // 20) // 100
        bonus = {field: min(amount, int(base.get(field, 0)) * RULES['income_bonus_cap_percent'] // 100)
                 for field, amount in contributions.items()}
        for field, amount in bonus.items():
            setattr(city, field, getattr(city, field) + amount)
        state.soldiers['recruited'] += bonus['reserves']
        if city.owner == state.player:
            first_city = first_city or city
            summary['amount'] += len(employees) * RULES['monthly_salary']
            summary['paid'] += paid
            for field, amount in bonus.items():
                summary['bonus'][field] += amount
            summary['counts']['staff'] += len(employees)
            summary['counts']['total_unpaid'] += sum(not p['working'] for p in employees)
            summary['counts']['cities'] += 1
    if first_city is not None:
        _emit(campaign, state, 'staff_salary', first_city, **summary)


def synchronize(campaign, state, *, opening=False, monthly=False, checks=True):
    """Synchronize after a successful command; never call from a GET/view.

    Arrival phases postpone only monthly candidate checks. Payroll still runs
    once, then the arrivals command can complete the previously deferred check.
    """
    pool = state.extension['civil_staff']
    m, tick = month_index(state), _tick(state)
    sync_people(state)
    for key, city in sorted(state.cities.items()):
        row = pool['cities'].setdefault(key, _ledger(state, city))
        if row['owner'] != city.owner:
            previous = row['owner']
            row.update(owner=city.owner, owner_since_tick=tick,
                       shortage_since_month=m, zero_since_tick=None, misses=0)
            _expire(campaign, state, city, row, 'owner_changed', cooldown=False)
        count = _effective_count(state, city)
        limit = target(campaign, key)
        if count >= limit:
            row.update(shortage_since_month=None, zero_since_tick=None, misses=0)
            _expire(campaign, state, city, row, 'filled')
        else:
            if row['shortage_since_month'] is None:
                row['shortage_since_month'] = m
            if count == 0:
                if row['zero_since_tick'] is None:
                    row['zero_since_tick'] = tick
            else:
                row['zero_since_tick'] = None
        if row['candidate'] and row['candidate']['expires_month'] <= m:
            _expire(campaign, state, city, row, 'expired')
        if not _active(campaign, state, city):
            _expire(campaign, state, city, row, 'inactive', cooldown=False)
    if not checks:
        return
    if monthly:
        _payroll(campaign, state)
    if state.phase in {'arrivals', 'finished'}:
        return
    if not opening and state.day != 1:
        return
    for key, city in sorted(state.cities.items()):
        row = pool['cities'][key]
        if row['last_checked_month'] == m:
            continue
        row['last_checked_month'] = m
        count, limit = _effective_count(state, city), target(campaign, key)
        if (not _active(campaign, state, city) or _in_battle(state, key)
                or count >= limit or row['candidate'] is not None
                or row['cooldown_until_month'] > m
                or city_count(state, key) >= limit
                or city_occupancy(state, city) >= campaign.catalog.rules.city_officer_capacity):
            continue
        if opening and count == 0:
            _offer(campaign, state, city, row, 'opening')
            continue
        if count == 0:
            if tick - max(row['owner_since_tick'], row['zero_since_tick']) >= 3:
                _offer(campaign, state, city, row, 'empty_city')
            continue
        if row['shortage_since_month'] is None or m - row['shortage_since_month'] < RULES['shortage_months']:
            continue
        # The ordinary observation window first gives existing historical
        # candidates time to be recruited. There is no permanent global block.
        if row['misses'] >= RULES['guaranteed_after_misses']:
            _offer(campaign, state, city, row, 'guaranteed')
        elif _draw(pool) % 100 < (RULES['single_probability'] if count == 1 else RULES['large_probability']):
            _offer(campaign, state, city, row, 'ordinary')
        else:
            row['misses'] += 1


def _blocked_reason(campaign, state, city, owner):
    pool = state.extension['civil_staff']
    row = pool['cities'][city.id]
    if city.owner != owner or not _active(campaign, state, city):
        return 'not_owned'
    if (owner == state.player and state.phase != 'city') or (owner != state.player and state.phase != 'ai'):
        return 'wrong_phase'
    if _in_battle(state, city.id):
        return 'battle'
    if city.action_used:
        return 'action_used'
    if row['candidate'] is None or row['candidate']['expires_month'] <= month_index(state):
        return 'no_candidate'
    if city_occupancy(state, city) >= campaign.catalog.rules.city_officer_capacity:
        return 'city_full'
    if city_count(state, city.id) >= target(campaign, city.id):
        return 'staff_limit'
    if _effective_count(state, city) >= target(campaign, city.id):
        return 'not_needed'
    if city.gold < RULES['hire_gold']:
        return 'insufficient_gold'
    return None


_ERRORS = dict(not_owned='请选择本方城池。', wrong_phase='当前不能雇用地方文吏。',
    battle='交战城池不能雇用地方文吏。', action_used='这座城本回合已行动。',
    no_candidate='本城暂无有效的文吏候选。', city_full='本城人员已达容量上限。',
    staff_limit='本城地方文吏已达上限。', not_needed='本城编制已足，无需补充文吏。',
    insufficient_gold='雇用地方文吏需要60金钱。')


def hire(campaign, state, city_id, candidate_id, owner):
    if not isinstance(city_id, str) or city_id not in state.cities:
        raise GameError('请选择本方城池。')
    city = state.cities[city_id]
    reason = _blocked_reason(campaign, state, city, owner)
    if reason:
        raise GameError(_ERRORS[reason])
    pool = state.extension['civil_staff']
    row = pool['cities'][city_id]
    candidate = row['candidate']
    if not isinstance(candidate_id, str) or candidate_id != candidate['id']:
        raise GameError('文吏候选已更新，请重新选择。')
    person = deepcopy(candidate)
    person.update(city=city_id, owner=owner, hired_month=month_index(state),
                  paid_month=month_index(state), unpaid_months=0, working=True, action_turn=0)
    pool['people'][person['id']] = person
    state.officers[person['id']] = initialize_officer(definition(person), person['id'],
        officer_profile(person), year=state.year, faction_id=owner, loyalty=80, rules=campaign.catalog.rules,
        resolve_death_year=True)
    city.roster.officer_ids.append(person['id'])
    row['candidate'] = None
    row['cooldown_until_month'] = month_index(state) + RULES['cooldown_months']
    row['misses'] = 0
    city.gold -= RULES['hire_gold']
    city.action_used = True
    _emit(campaign, state, 'staff_hired', city, person=person, amount=RULES['hire_gold'], reason='hired')
    return person


def reject(campaign, state, city_id, candidate_id, owner):
    if not isinstance(city_id, str) or city_id not in state.cities:
        raise GameError('请选择本方城池。')
    city = state.cities[city_id]
    if (city.owner != owner or not _active(campaign, state, city)
            or (owner == state.player and state.phase != 'city')
            or (owner != state.player and state.phase != 'ai') or _in_battle(state, city.id)):
        raise GameError('当前不能谢绝地方文吏。')
    row = state.extension['civil_staff']['cities'][city_id]
    person = row['candidate']
    if person is None or not isinstance(candidate_id, str) or candidate_id != person['id'] or person['expires_month'] <= month_index(state):
        raise GameError('文吏候选已更新，请重新选择。')
    row['candidate'] = None
    row['cooldown_until_month'] = month_index(state) + RULES['cooldown_months']
    row['misses'] = 0
    _emit(campaign, state, 'staff_declined', city, person=person, reason='declined')


def view(campaign, state):
    result = dict(rules=deepcopy(RULES), current_month=month_index(state) if state else
                  campaign.catalog.data['start_year'] * 12 + campaign.catalog.data['start_month'] - 1,
                  cities={}, people=[], faction_counts={key: 0 for key in campaign.catalog.factions})
    if state is None or 'civil_staff' not in state.extension:
        return result
    pool = state.extension['civil_staff']
    for key, city in state.cities.items():
        row = pool['cities'][key]
        employees = sorted((runtime_view(state, p) for p in pool['people'].values()
            if p['id'] in city.roster.officer_ids and state.officers[p['id']].alive), key=lambda p: p['id'])
        count, effective, limit = len(employees), _effective_count(state, city), target(campaign, key)
        reason = _blocked_reason(campaign, state, city, state.player)
        rejectable = (row['candidate'] is not None and row['candidate']['expires_month'] > month_index(state)
                      and city.owner == state.player and state.phase == 'city' and not _in_battle(state, key))
        free = campaign._free_candidates(state, city) if city.owner == state.player else []
        available = any(p['working'] and p['health'] > 0 and p['action_turn'] != state.turn for p in employees)
        result['cities'][key] = dict(target=limit, minimum=limit, limit=limit, count=count,
            staff_count=count, officer_count=_historical_count(state, city),
            occupancy=city_occupancy(state, city), effective_count=effective,
            need=max(0, limit-effective), candidate=deepcopy(row['candidate']), employees=employees,
            can_hire=reason is None, blocked_reason=reason,
            can_reject=rejectable, monthly_salary=count * RULES['monthly_salary'],
            cooldown_until_month=row['cooldown_until_month'],
            can_search=bool(available and free and city.owner == state.player and state.phase == 'city'
                            and not city.action_used and not _in_battle(state, key)
                            and city.gold >= campaign.catalog.data['rules']['recruit_officer_gold']
                            and city_occupancy(state, city) < campaign.catalog.rules.city_officer_capacity),
            search_targets=list(free))
        if city.owner in result['faction_counts']:
            result['faction_counts'][city.owner] += count
        result['people'].extend(employees)
    result['people'] = [runtime_view(state, p) for p in pool['people'].values()]
    return result


def validate(campaign, state):
    pool = state.extension['civil_staff']
    if (not isinstance(pool, dict) or set(pool) != {'schema', 'rng', 'next_id', 'cities', 'people', 'last_payroll_month'}
            or pool['schema'] != SCHEMA):
        raise ValueError('Civil staff pool schema')
    m, tick = month_index(state), _tick(state)
    if (not isinstance(pool['rng'], dict) or set(pool['rng']) != {'state', 'draws'}
            or not _int(pool['rng']['state'], 1, 0xffffffff)
            or not _int(pool['rng']['draws'], 0, 100000000)
            or not _int(pool['next_id'], 1, 1000001)
            or not _int(pool['last_payroll_month'], 0, m)
            or not isinstance(pool['cities'], dict) or set(pool['cities']) != set(state.cities)
            or not isinstance(pool['people'], dict) or len(pool['people']) > 100000):
        raise ValueError('Civil staff state bounds')
    seen = set()

    def record(person, employee=False):
        fields = _EMPLOYEE_FIELDS if employee else _RECORD_FIELDS
        if not isinstance(person, dict) or set(person) != fields:
            raise ValueError('Civil staff person fields')
        match = _ID.fullmatch(person['id']) if isinstance(person['id'], str) else None
        if match is None or person['id'] in seen:
            raise ValueError('Civil staff ID')
        number = int(match.group(1))
        if not 1 <= number < pool['next_id'] or person['id'] != f'clerk-{number:06d}':
            raise ValueError('Civil staff sequence')
        seen.add(person['id'])
        expected = _immutable_record(campaign, state, number)
        if any(person.get(key) != value for key, value in expected.items()):
            raise ValueError('Civil staff generated identity/profile')
        if (not _int(person['health'], 0, person['profile']['health_max'])
                or type(person['troops']) is not int or person['troops'] != 0
                or type(person['experience']) is not int or person['experience'] != 0
                or not _int(person['offered_month'], 0, m)
                or person['expires_month'] != person['offered_month'] + RULES['candidate_months']):
            raise ValueError('Civil staff noncombat state')
        if employee:
            if (person['city'] not in state.cities or person['owner'] not in {*campaign.catalog.factions, 'neutral'}
                    or not _int(person['hired_month'], person['offered_month'], min(m, person['expires_month']-1))
                    or not _int(person['paid_month'], person['hired_month'], m)
                    or not _int(person['unpaid_months'], 0, m-person['hired_month'])
                    or type(person['working']) is not bool
                    or not _int(person['action_turn'], 0, state.turn)):
                raise ValueError('Civil staff employment')
        elif person['expires_month'] <= m:
            raise ValueError('Civil staff expired candidate')

    for key, city in state.cities.items():
        row = pool['cities'][key]
        if (not isinstance(row, dict) or set(row) != _CITY_FIELDS or row['owner'] != city.owner
                or not _int(row['owner_since_tick'], 0, tick)
                or row['shortage_since_month'] is not None and not _int(row['shortage_since_month'], 0, m)
                or row['zero_since_tick'] is not None and not _int(row['zero_since_tick'], 0, tick)
                or row['last_checked_month'] is not None and not _int(row['last_checked_month'], 0, m)
                or not _int(row['misses'], 0, RULES['guaranteed_after_misses'])
                or not _int(row['cooldown_until_month'], 0, m+RULES['cooldown_months'])):
            raise ValueError('Civil staff city ledger')
        if row['candidate'] is not None:
            record(row['candidate'])
        if city_occupancy(state, city) > campaign.catalog.rules.city_officer_capacity:
            raise ValueError('Civil staff combined city capacity')
    for key, person in pool['people'].items():
        if key != person.get('id'):
            raise ValueError('Civil staff registry identity')
        record(person, employee=True)
        officer = state.officers.get(key)
        from .facilities import learned_profile
        if officer is None or officer.person_id != key or officer.profile != learned_profile(state,key,officer_profile(person)):
            raise ValueError('Civil staff runtime identity/profile')
        actual_city = next((c.id for c in state.cities.values() if key in c.roster.officer_ids),
            state.extension.get('free_locations', {}).get(key, person['city']))
        if person['city'] != actual_city or person['owner'] != (officer.faction_id or 'neutral'):
            raise ValueError('Civil staff runtime location/owner')
        if not officer.alive and person['working']:
            raise ValueError('Dead generated officer is working')
    if {i for i in state.officers if is_generated_ref(i)} != set(pool['people']):
        raise ValueError('Generated runtime/registry set')
