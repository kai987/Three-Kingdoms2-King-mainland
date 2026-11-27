"""Two faction offices, bounded automatic tasks and conserved city training degree.

The serialized morale/unit_morale keys remain stable for current campaign saves;
these values represent training degree, not the original temporary morale tactic.

This is an authorial adaptation of the agreed rules, not SAN14's formulas.
Only committed commands and calendar hooks perform work. Views are pure.
"""
from copy import deepcopy

from . import grain_units
from .city_economy import absent_troops, monthly_income as _income
from .errors import GameError
from . import command_books
from .officers import OFFICER_TROOP_CAP, parse_officer_ref

SCHEMA = 'tk2-domestic-v2'
RULES = dict(max_income_bonus_percent=50, personnel_gold=60, persuasion_gold=100,
             training_initial_morale=70, recruit_morale=50, training_per_1000_gold=1,
             training_per_1000_grain=2, automatic_retry_turns=3)
DEFAULT_POLICY = dict(auto_recruit=False, auto_persuade=False, priority='best', envoy=None,
    min_chance=20, budget=100, excluded_targets=[], recruit_enabled=False,
    reserve_target=2000, recruit_budget=50, training_enabled=False,
    gold_floor=100, grain_floor=200, task_order=['personnel', 'recruit', 'transport'])
_CITY_FIELDS = {'owner', 'morale', 'income_month', 'income_points', 'last_work_turn',
                'last_auto_turn', 'last_income_month'}
_CITY_INCOME_FIELDS = {'income_extra_units', 'income_rate_units'}
_INCOME_DUTIES_PER_MONTH = 6
_LOW_INCOME_FULL_RATE_INTELLECT = 59
_INCOME_UNITS_PER_PERCENT = 2 * 99 * _LOW_INCOME_FULL_RATE_INTELLECT
_RECRUIT_GOLD_RATES = ((1, 50, 20, 18), (51, 79, 17, 11), (80, 94, 10, 6), (95, 99, 5, 0))
_OFFICES = ('civil', 'military')
_OFFICE_STATS = {'civil': ('intellect', 'virtue'), 'military': ('martial_strength', 'intellect')}
_LEGACY_FACTION_FIELDS = {*_OFFICES, 'policy'}
_FACTION_FIELDS = _LEGACY_FACTION_FIELDS | {'manual_offices'}
_REPORT_FIELDS = {'turn', 'city', 'owner', 'kind', 'details'}
_REPORT_KINDS = {'income', 'recruit', 'training', 'personnel', 'policy', 'hire_staff', 'allocation'}
LIMIT = 100000000


def _ref_key(value):
    return (0, value) if type(value) is int else (1, str(value))


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _month(state):
    return state.year * 12 + state.month - 1


def _new_city(state, city):
    return dict(owner=city.owner, morale=70, income_month=_month(state), income_points=0,
                last_work_turn=0, last_auto_turn=0, last_income_month=_month(state))


def _reset_income(row, month):
    row.update(income_month=month, income_points=0)
    row.pop('income_rate_units', None)
    row.pop('income_extra_units', None)


def _new_faction():
    return dict(civil=None, military=None, manual_offices=[], policy=grain_units.policy(DEFAULT_POLICY))


def empty(game, state):
    return dict(schema=SCHEMA,
                factions={owner: _new_faction() for owner in game.catalog.factions if owner != 'neutral'},
                cities={key: _new_city(state, city) for key, city in state.cities.items()},
                unit_morale={}, attempts={}, reports=[])


def _pool(state):
    return state.extension['domestic']


def _report(state, city, kind, **details):
    reports = _pool(state)['reports']
    reports.append(dict(turn=state.turn, city=city.id, owner=city.owner, kind=kind, details=details))
    reports[:] = reports[-100:]


def _marching(game, state):
    return game._march_ids(state)


def appointments(state, owner):
    """The one canonical pair for a faction; no per-city appointment mirrors."""
    return state.extension.get('domestic', {}).get('factions', {}).get(owner, {})


def officers_reserved_for_duty(state, owner):
    post = appointments(state, owner)
    # A player's automatic appointments can be refilled when an escort leaves.
    roles = post.get('manual_offices', _OFFICES) if owner == state.player else _OFFICES
    return {post[role] for role in roles if post.get(role) is not None}


def _owned_ids(state, owner):
    return {ident for city in state.cities.values() if city.owner == owner
            for ident in city.roster.officer_ids}


def _office_rosters(state):
    rosters = {}
    ended = set(state.extension.get('ended_factions', []))
    for city in state.cities.values():
        if city.owner not in ended and city.owner != 'neutral':
            rosters.setdefault(city.owner, set()).update(city.roster.officer_ids)
    return rosters


def _away_officers(game, state):
    return _marching(game, state) | {
        unit['id'] for side in ('attackers', 'defenders') for unit in (state.battle or {}).get(side, [])}


def _retained(state, owner, ident, residents, away):
    person = state.officers.get(ident)
    return (residents is not None and person is not None and person.alive and person.faction_id == owner
            and (ident in residents or ident in away))


def _working(state, owner, ident):
    person = state.officers.get(ident)
    paid = state.extension.get('civil_staff', {}).get('people', {}).get(ident, {}).get('working', True)
    return bool(person is not None and person.alive and person.faction_id == owner and person.health > 0 and paid)


def _present(game, state, city, ident, *, unused=False):
    """A central official may work for any city of the same faction remotely."""
    return (_working(state, city.owner, ident) and ident in _owned_ids(state, city.owner)
            and ident not in _away_officers(game, state))


def migrate_appointments(state):
    """Former player posts with an incumbent were explicitly appointed."""
    posts = _pool(state)['factions']
    if not all(isinstance(post, dict) and set(post) == _LEGACY_FACTION_FIELDS for post in posts.values()):
        return False
    for owner, post in posts.items():
        post['manual_offices'] = [field for field in _OFFICES if owner == state.player and post[field] is not None]
    return True


def _appoint(state, owner, post, residents, away):
    manual = [field for field in post['manual_offices']
              if post[field] is None or _retained(state, owner, post[field], residents, away)]
    available = {ident for ident in (residents or ()) if ident not in away and _working(state, owner, ident)}
    available.difference_update(post[field] for field in manual)
    for field in _OFFICES:
        if field in manual:
            continue
        stats = _OFFICE_STATS[field]
        post[field] = min(available, default=None, key=lambda ident: (
            tuple(-getattr(state.officers[ident].profile, stat) for stat in stats), _ref_key(ident)))
        available.discard(post[field])
    post['manual_offices'] = manual


def _refresh_faction_offices(game, state, owner):
    _appoint(state, owner, appointments(state, owner), _owned_ids(state, owner), _away_officers(game, state))


def synchronize(game, state):
    """Reconcile faction appointments and city ledgers without work or RNG."""
    pool = _pool(state)
    residents, away = _office_rosters(state), _away_officers(game, state)
    for owner in game.catalog.factions:
        if owner == 'neutral':
            continue
        post = pool['factions'].setdefault(owner, _new_faction())
        _appoint(state, owner, post, residents.get(owner), away)
        envoy = post['policy']['envoy']
        if envoy is not None and not _retained(state, owner, envoy, residents.get(owner), away):
            post['policy']['envoy'] = None
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(state, city))
        if row['owner'] != city.owner:
            # The training degree stays with the garrison. Previous-owner
            # earned income cannot be paid to a conquering faction.
            row.update(owner=city.owner, last_income_month=_month(state), last_work_turn=0, last_auto_turn=0)
            _reset_income(row, _month(state))
    travelling = {str(i) for i in away}
    for ident in list(pool['unit_morale']):
        ref = next((key for key in state.officers if str(key) == ident), None)
        if ref is None or not state.officers[ref].alive or ident not in travelling:
            pool['unit_morale'].pop(ident)
            pool.get('march_spirit', {}).pop(ident, None)
    cutoff = max(0, state.turn - 12)
    for faction in list(pool['attempts']):
        rows = pool['attempts'][faction]
        for key in list(rows):
            if rows[key]['turn'] < cutoff:
                rows.pop(key)
        if not rows:
            pool['attempts'].pop(faction)


def _validate_policy(game, state, policy):
    if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
        raise ValueError('Domestic policy fields')
    for key in ('auto_recruit', 'auto_persuade', 'recruit_enabled', 'training_enabled'):
        if type(policy[key]) is not bool:
            raise ValueError('Domestic policy boolean')
    if policy['priority'] not in {'best', 'martial', 'intellect', 'virtue'}:
        raise ValueError('Domestic target priority')
    if (not isinstance(policy['task_order'], list) or len(policy['task_order']) != 3
            or set(policy['task_order']) != {'personnel', 'recruit', 'transport'}):
        raise ValueError('Domestic task order')
    if not _integer(policy['min_chance'], 0, 95):
        raise ValueError('Domestic minimum chance')
    for key in ('budget', 'recruit_budget'):
        if not _integer(policy[key], 0, 1000000):
            raise ValueError('Domestic budget')
    for key in ('reserve_target', 'gold_floor', 'grain_floor'):
        if not _integer(policy[key], 0, LIMIT):
            raise ValueError('Domestic resource target')
    if policy['envoy'] is not None:
        parse_officer_ref(policy['envoy'], game.catalog.rules)
        if policy['envoy'] not in state.officers:
            raise ValueError('Domestic envoy reference')
    ids = policy['excluded_targets']
    if (not isinstance(ids, list) or len(ids) > 2048
            or any(type(i) not in (int, str) for i in ids)
            or len(ids) != len(set(ids)) or any(i not in state.officers for i in ids)):
        raise ValueError('Domestic excluded targets')
    for ident in ids:
        parse_officer_ref(ident, game.catalog.rules)


def set_policy(game, state, payload, owner):
    if (not isinstance(payload, dict) or set(payload) - {'faction', 'civil', 'military', 'policy'}
            or payload.get('faction') != owner or not isinstance(payload.get('faction'), str)
            or owner not in _pool(state)['factions']):
        raise GameError('内政委任参数无效。')
    cities = sorted((c for c in state.cities.values() if c.owner == owner), key=lambda c: c.id)
    if not cities or owner == 'neutral' or state.phase not in {'city', 'ai'}:
        raise GameError('请在战略阶段设置本势力内政官。')
    city = cities[0]
    row = _pool(state)['factions'][owner]
    revised = deepcopy(row)
    manual = set(row['manual_offices'])
    for field in _OFFICES:
        if field in payload:
            ident = payload[field]
            if ident == 'auto':
                manual.discard(field)
                continue
            if ident is not None and (type(ident) not in (int, str)
                    or ident != row[field] and not _present(game, state, city, ident)):
                raise GameError('请选择本势力健康且未出征的委任官。')
            revised[field] = ident
            manual.add(field)
    if len(manual) == len(_OFFICES) and revised['civil'] is not None and revised['civil'] == revised['military']:
        raise GameError('同一武将不能兼任两个内政岗位。')
    if 'policy' in payload:
        patch = payload['policy']
        if not isinstance(patch, dict) or set(patch) - set(DEFAULT_POLICY):
            raise GameError('自动内政方针无效。')
        revised['policy'].update(deepcopy(patch))
        try:
            _validate_policy(game, state, revised['policy'])
        except (ValueError, TypeError) as error:
            raise GameError('自动内政方针无效。') from error
        envoy = revised['policy']['envoy']
        if (envoy is not None and 'envoy' in patch and envoy != row['policy']['envoy']
                and not _present(game, state, city, envoy)):
            raise GameError('请选择本势力健康且未出征的使者。')
    revised['manual_offices'] = [field for field in _OFFICES if field in manual]
    _appoint(state, owner, revised, _owned_ids(state, owner), _away_officers(game, state))
    _pool(state)['factions'][owner] = revised
    _report(state, city, 'policy', civil=revised['civil'], military=revised['military'])


def morale(state, city_id):
    return state.extension.get('domestic', {}).get('cities', {}).get(city_id, {}).get('morale', 70)


def unit_morale(game, state, ident):
    saved = state.extension.get('domestic', {}).get('unit_morale', {}).get(str(ident))
    if saved is not None:
        return saved
    city = next((c for c in state.cities.values() if ident in c.roster.officer_ids), None)
    return morale(state, city.id) if city is not None else 70


def on_departure(game, state, ids, city_id):
    if 'domestic' not in state.extension:
        return
    values = _pool(state)['unit_morale']
    spirit = state.extension.get('city_development', {}).get('cities', {}).get(city_id, {}).get('garrison_spirit', 100)
    for ident in ids:
        values[str(ident)] = morale(state, city_id)
        if spirit < 100:
            _pool(state).setdefault('march_spirit', {})[str(ident)] = spirit


def _garrison_troops(game, state, city, *, exclude=()):
    marching, excluded = _marching(game, state), set(exclude)
    return city.reserves + sum(state.officers[i].troops for i in city.roster.officer_ids
        if i not in marching and i not in excluded and state.officers[i].alive)


def add_reserves(game, state, city, amount, morale_value=50, *, recruited=False):
    if not _integer(amount, 0, LIMIT) or not _integer(morale_value, 0, 100):
        raise ValueError('Domestic reserves/morale addition')
    if amount:
        if 'domestic' in state.extension:
            before = _garrison_troops(game, state, city)
            _pool(state)['cities'][city.id]['morale'] = (
                before * morale(state, city.id) + amount * morale_value) // (before + amount)
        city.reserves += amount
        if recruited:
            state.soldiers['recruited'] += amount


def on_arrival(game, state, ids, city_id):
    """Call after roster transfer; exclude the arrived troops from old strength."""
    if 'domestic' not in state.extension:
        return
    city, values = state.cities[city_id], _pool(state)['unit_morale']
    amount = sum(state.officers[i].troops for i in ids if state.officers[i].alive)
    if amount:
        before = _garrison_troops(game, state, city, exclude=ids)
        incoming = sum(state.officers[i].troops * values.get(str(i), 70) for i in ids if state.officers[i].alive)
        _pool(state)['cities'][city_id]['morale'] = (before * morale(state, city_id) + incoming) // (before + amount)
    for ident in ids:
        values.pop(str(ident), None)
        _pool(state).get('march_spirit', {}).pop(str(ident), None)


def _civil_income_units(intellect):
    if intellect < 60:
        return 5 * intellect * (_INCOME_UNITS_PER_PERCENT // _LOW_INCOME_FULL_RATE_INTELLECT)
    if intellect < 95:
        return (5 + intellect - 60) * _INCOME_UNITS_PER_PERCENT
    return (80 + 5 * (intellect - 95)) * (_INCOME_UNITS_PER_PERCENT // 2)


def _earned_income_units(row):
    if 'income_rate_units' in row:
        return row['income_rate_units']
    # Earlier saves stored base points, with any high-intellect bonus in units of 1/198%.
    return (80 * row['income_points'] + row.get('income_extra_units', 0)) * (_INCOME_UNITS_PER_PERCENT // 198)


def _income_bonus(base, units):
    denominator = 100 * _INCOME_UNITS_PER_PERCENT * _INCOME_DUTIES_PER_MONTH
    return {field: int(base[field]) * units // denominator for field in ('gold', 'grain')}


def earned_grain(state, city_id, income):
    row = _pool(state)['cities'][city_id]
    units = _earned_income_units(row) if row['income_month'] == _month(state) else 0
    return _income_bonus(income, units)['grain']


def month_rollover(game, state, *, regular_incomes=None):
    """After the date advances; add only the previous month's earned bonus."""
    synchronize(game, state)
    current = _month(state)
    summary = dict(gold=0, grain=0, reserves=0, morale=0, cities=0, reason='month')
    first_city = None
    for key, city in state.cities.items():
        row = _pool(state)['cities'][key]
        if row['last_income_month'] >= current:
            continue
        units = 0
        if city.owner != 'neutral' and row['income_month'] == current - 1:
            units = _earned_income_units(row)
        bonus = {}
        if units:
            base = _income(game, key, state) if regular_incomes is None else regular_incomes[key]
            bonus = {field: min(LIMIT - getattr(city, field), amount)
                     for field, amount in _income_bonus(base, units).items()}
        for field, amount in bonus.items():
            setattr(city, field, getattr(city, field) + amount)
        _reset_income(row, current)
        row['last_income_month'] = current
        if any(bonus.values()):
            _report(state, city, 'income', **bonus)
            if city.owner == state.player:
                first_city = first_city or key
                summary['cities'] += 1
                summary['gold'] += bonus['gold']
                summary['grain'] += bonus['grain']
    if first_city is not None:
        game._emit_event(state, 'domestic_report', city_ids=[first_city], factions=[state.player], details=summary)


def _recruit_gold_per_100(strength):
    for lower, upper, high_price, low_price in _RECRUIT_GOLD_RATES:
        if lower <= strength <= upper:
            span = upper - lower
            numerator = high_price * (upper - strength) + low_price * (strength - lower)
            return (2 * numerator + span) // (2 * span)
    raise ValueError('Recruitment martial strength')


def recruitment_preview(game, state, city_id, *, budget=None):
    city, row = state.cities[city_id], _pool(state)['cities'][city_id]
    post = appointments(state, city.owner)
    ident, policy = post.get('military'), post.get('policy', DEFAULT_POLICY)
    if ident is None or not _present(game, state, city, ident):
        return dict(soldiers=0, gold=0, grain=0)
    strength = state.officers[ident].profile.martial_strength
    available_gold = min(max(0, city.gold - policy['gold_floor']), policy['recruit_budget'])
    available_grain = max(0, city.grain - policy['grain_floor'])
    unit_gold = _recruit_gold_per_100(strength)
    gold_capacity = available_gold * 100 // unit_gold if unit_gold else LIMIT
    unit_grain = grain_units.amount(30)
    amount = min(100 + strength, max(0, policy['reserve_target'] - city.reserves),
                 gold_capacity, available_grain * 100 // unit_grain,
                 LIMIT - city.reserves)
    if budget is not None:
        from . import military_budget
        amount=military_budget.recruitment(game,state,city,amount,budget)
    return dict(soldiers=amount, gold=(amount * unit_gold + 99) // 100,
                grain=(amount * unit_grain + 99) // 100)


def training_preview(game, state, city_id):
    city, row = state.cities[city_id], _pool(state)['cities'][city_id]
    post = appointments(state, city.owner)
    ident = post.get('military')
    if ident is None or not _present(game, state, city, ident) or row['morale'] >= 100:
        return dict(gain=0, gold=0, grain=0)
    soldiers = _garrison_troops(game, state, city)
    if not soldiers:
        return dict(gain=0, gold=0, grain=0)
    units = (soldiers + 999) // 1000
    grain = grain_units.amount(units * 2)
    if city.gold - post['policy']['gold_floor'] < units or city.grain - post['policy']['grain_floor'] < grain:
        return dict(gain=0, gold=0, grain=0)
    gain = min(100 - row['morale'], 2 + state.officers[ident].profile.martial_strength // 25)
    return dict(gain=gain, gold=units, grain=grain)


def _allocation_priority(officer):
    return (-officer.profile.martial_strength, -officer.profile.intellect,
            -officer.profile.virtue, -officer.health, -officer.experience,
            _ref_key(officer.runtime_id))


def allocation_preview(game, state, city_id, *, max_added=None, held=None):
    """Plan local reserve assignments without drawing RNG or changing the state.

    A faction official manages every owned city, but troops stay in their own
    city. Existing troops are retained; only the unassigned reserve is filled
    into each eligible officer in ability order, up to the troop cap.
    """
    city = state.cities[city_id]
    result = dict(soldiers=0, officers=0, remaining_reserves=city.reserves, assignments=[])
    if not city.reserves:
        return result
    official = appointments(state, city.owner).get('military')
    if official is None or not _present(game, state, city, official):
        return result
    available = [state.officers[i] for i in city.roster.officer_ids
                 if i!=held and state.officers[i].troops < OFFICER_TROOP_CAP and _present(game, state, city, i)]
    available.sort(key=_allocation_priority)
    for officer in available:
        amount = min(result['remaining_reserves'], OFFICER_TROOP_CAP - officer.troops)
        if max_added is not None:
            amount = min(amount, max(0, max_added - result['soldiers']))
        if not amount:
            continue
        result['assignments'].append(dict(id=officer.runtime_id, **{'from': officer.troops},
                                          to=officer.troops + amount, added=amount))
        result['soldiers'] += amount
        result['officers'] += 1
        result['remaining_reserves'] -= amount
        if not result['remaining_reserves']:
            break
    return result


def allocate_garrison(game, state, city_id, *, record=True, max_added=None, held=None):
    """Apply the shared player/AI allocation plan; no fees or action are spent."""
    quote = allocation_preview(game, state, city_id, max_added=max_added,held=held)
    if quote['soldiers']:
        city = state.cities[city_id]
        apply_allocation(state,city,{row['id']:row['to'] for row in quote['assignments']})
        from . import war_recovery
        war_recovery.record(state,city.owner,city.id,'allocation',quote['soldiers'])
        if record:
            _report(state, city, 'allocation', soldiers=quote['soldiers'], officers=quote['officers'])
    return quote


def apply_allocation(state,city,changes):
    """Apply the same local active/reserve balance for player and AI orders."""
    change=sum(troops-state.officers[ident].troops for ident,troops in changes.items())
    for ident,troops in changes.items():
        state.officers[ident].troops=troops
    city.reserves-=change


def rebalance_changed_garrisons(game, before, state):
    """Reassign local soldiers once after the command's roster changes settle."""
    before_absent = absent_troops(game, before)
    after_absent = absent_troops(game, state)
    presence_changes = before_absent ^ after_absent
    staff = state.extension['civil_staff']['people']
    for city in state.cities.values():
        if city.owner == 'neutral' or not city.roster.officer_ids:
            continue
        prior = before.cities.get(city.id)
        if (prior and prior.owner == city.owner
                and prior.roster.officer_ids == city.roster.officer_ids
                and presence_changes.isdisjoint(city.roster.officer_ids)):
            continue
        stationed = set(city.roster.officer_ids) - after_absent
        if (prior and prior.owner == city.owner
                and stationed == set(prior.roster.officer_ids) - before_absent):
            continue
        members = [state.officers[ident] for ident in city.roster.officer_ids if ident in stationed]
        eligible = sorted((officer for officer in members if officer.health > 0
                           and staff.get(officer.runtime_id, {}).get('working', True)),
                          key=_allocation_priority)
        if not eligible:
            continue
        remaining = sum(officer.troops for officer in members)
        moved = recipients = 0
        for officer in eligible:
            troops = min(OFFICER_TROOP_CAP, remaining)
            if troops > officer.troops:
                moved += troops - officer.troops
                recipients += 1
            officer.troops = troops
            remaining -= troops
        eligible_ids = {officer.runtime_id for officer in eligible}
        for officer in members:
            if officer.runtime_id not in eligible_ids:
                # At the reserve limit, leave any excess with its officer.
                retained = min(officer.troops, max(0, city.reserves + remaining - LIMIT))
                officer.troops = retained
                remaining -= retained
        city.reserves += remaining
        if moved:
            _report(state, city, 'allocation', soldiers=moved, officers=recipients)


def _chance(actor, target, method):
    if method == 'recruit_officer':
        return max(15, min(95, 35 + actor.profile.virtue // 2 + actor.profile.intellect // 5 - target.profile.virtue // 5))
    return max(5, min(75, 50 + (actor.profile.virtue - target.loyalty) // 2
                      + (actor.profile.intellect - target.profile.intellect) // 4))


def _target_key(state, policy, choice, city_id):
    target = state.officers[choice['id']].profile
    stats = [target.martial_strength, target.intellect, target.virtue]
    primary = {'martial': stats[0], 'intellect': stats[1], 'virtue': stats[2]}.get(policy['priority'])
    ranking = sorted(stats, reverse=True) if primary is None else [primary, *sorted(stats, reverse=True)]
    location = state.extension['free_locations'].get(str(choice['id']))
    distance = 0 if location == city_id else 1
    return (*(-value for value in ranking), -choice['chance'], distance,
            _ref_key(choice['id']), choice['method'], city_id)


def personnel_targets(game, state, city_id):
    from .historical_campaigns import allied

    city = state.cities[city_id]
    row = appointments(state, city.owner)
    if not row or not command_books.can_spend(state, city.owner) or game._city_occupancy(state, city) >= game.catalog.rules.city_officer_capacity:
        return []
    policy = row['policy']
    if row['civil'] is None or not _present(game, state, city, row['civil']):
        return []
    choices = []
    attempts = _pool(state)['attempts'].get(city.owner, {})
    for method, enabled, candidates, actor_id, fee in (
            ('recruit_officer', policy['auto_recruit'], game._free_candidates(state, city), row['civil'], game.catalog.data['rules']['recruit_officer_gold']),
            ('persuade_officer', policy['auto_persuade'], game._persuadable(state, city),
             row['civil'] if policy['envoy'] is None else policy['envoy'], game.catalog.data['rules']['persuade_officer_gold'])):
        if not enabled or not command_books.can_spend(state, city.owner, method) or fee > policy['budget'] or city.gold - fee < policy['gold_floor']:
            continue
        if not _present(game, state, city, actor_id, unused=True):
            continue
        actor = state.officers[actor_id]
        for ident in candidates:
            if ident in policy['excluded_targets']:
                continue
            if (method == 'persuade_officer' and city.owner != state.player
                    and allied(state, city.owner, state.officers[ident].faction_id)):
                continue
            receipt = attempts.get(str(ident))
            if receipt and (receipt['turn'] == state.turn or receipt['retry_turn'] > state.turn):
                continue
            chance = _chance(actor, state.officers[ident], method)
            if chance >= policy['min_chance']:
                choices.append(dict(id=ident, method=method, actor=actor_id, chance=chance))
    return sorted(choices, key=lambda choice: _target_key(state, policy, choice, city_id))


def faction_personnel_targets(game, state, owner, city_ids=None):
    policy = appointments(state, owner).get('policy', DEFAULT_POLICY)
    allowed = set(city_ids) if city_ids is not None else None
    choices = [dict(choice, city=key) for key, city in state.cities.items()
               if city.owner == owner and (allowed is None or key in allowed)
               for choice in personnel_targets(game, state, key)]
    if choices and owner != state.player:
        # A captive returned this turn should have time to rejoin their faction.
        returned = {event['person_ids'][-1] for event in state.extension['events']['items']
                    if event['turn'] == state.turn and event['kind'] == 'diplomacy_result'
                    and event['details']['action'] == 'return_captives' and event['details']['success']}
        choices = [choice for choice in choices
                   if choice['method'] != 'persuade_officer' or state.officers[choice['id']].person_id not in returned]
        fields = ('martial_strength', 'intellect', 'virtue')
        roster = [officer.profile for officer in state.officers.values()
                  if officer.alive and officer.faction_id == owner]
        deficit = [100 - sum(getattr(profile, field) for profile in roster) // max(1, len(roster))
                   for field in fields]

        def ai_rank(choice):
            profile = state.officers[choice['id']].profile
            contribution = max(need * getattr(profile, field) for field, need in zip(fields, deficit))
            return -contribution * choice['chance'], _target_key(state, policy, choice, choice['city'])

        choices.sort(key=ai_rank)
    else:
        choices.sort(key=lambda choice: _target_key(state, policy, choice, choice['city']))
    # A target may be approachable from several friendly cities. Only publish
    # its best affordable approach for each actor/method, never duplicate rolls.
    seen = set()
    result = []
    for choice in choices:
        token = choice['actor'], choice['id'], choice['method']
        if token not in seen:
            seen.add(token)
            result.append(choice)
    return result


def _personnel(game, state, city, choice=None):
    if game._city_occupancy(state, city) >= game.catalog.rules.city_officer_capacity:
        return False
    choices = personnel_targets(game, state, city.id) if choice is None else [choice]
    if not choices:
        return False
    choice = {k: v for k, v in choices[0].items() if k != 'city'}
    actor = state.officers[choice['actor']]
    if choice['method'] == 'recruit_officer':
        game._attempt_recruitment(state, city, actor, choice['id'])
        if state.officers[choice['id']].faction_id == city.owner:
            _refresh_faction_offices(game, state, city.owner)
    else:
        game._attempt_defection(state, city, actor, choice['id'])
        game._reconcile_factions(state)
    success = state.officers[choice['id']].faction_id == city.owner
    attempts = _pool(state)['attempts'].setdefault(city.owner, {})
    attempts[str(choice['id'])] = dict(turn=state.turn,
        retry_turn=state.turn if success else state.turn + RULES['automatic_retry_turns'])
    _report(state, city, 'personnel', **choice, success=success,
            gold=game.catalog.data['rules']['recruit_officer_gold' if choice['method'] == 'recruit_officer' else 'persuade_officer_gold'])
    if city.owner != state.player:
        action = ('staff_recruit' if isinstance(choice['actor'], str) else 'recruit_officer') if choice['method'] == 'recruit_officer' else 'persuade_officer'
        game._report_ai(state, city, action, str(choice['id']))
    return True


def can_attempt(state, owner, ident):
    if 'domestic' not in state.extension:
        return True
    row = _pool(state)['attempts'].get(owner, {}).get(str(ident))
    return row is None or row['turn'] != state.turn


def record_attempt(state, owner, ident, success):
    if 'domestic' in state.extension:
        _pool(state)['attempts'].setdefault(owner, {})[str(ident)] = dict(turn=state.turn,
            retry_turn=state.turn if success else state.turn + RULES['automatic_retry_turns'])


def auto_assign(game, state, owner):
    """Enable AI work policies for the current faction appointments."""
    row = appointments(state, owner)
    if not row or owner in state.extension.get('ended_factions', []) or not any(
            city.owner == owner for city in state.cities.values()):
        return
    row['policy'].update(auto_recruit=True, auto_persuade=True, recruit_enabled=True, training_enabled=True)
    if 'logistics' in state.extension:
        from . import logistics
        fronts = {c.id for c in logistics._fronts(game, state, owner)}
        row['policy']['task_order'] = (['recruit', 'personnel', 'transport'] if fronts
                                       else ['transport', 'personnel', 'recruit'])
        logistics.prepare_ai(game, state, owner)


prepare_ai = auto_assign


def _hire_staff(game, state, owner, city_ids):
    """The central civil officer can hire at most one local candidate per turn."""
    from . import civil_staff
    post = appointments(state, owner)
    ident, policy = post.get('civil'), post.get('policy', DEFAULT_POLICY)
    candidates = []
    for key in city_ids:
        city = state.cities[key]
        if (not command_books.can_spend(state, owner, 'hire_staff') or ident is None or not _present(game, state, city, ident, unused=True)
                or game._city_occupancy(state, city) >= game.catalog.rules.city_officer_capacity):
            continue
        candidate = state.extension['civil_staff']['cities'][key]['candidate']
        fee = civil_staff.RULES['hire_gold']
        if candidate and city.gold - fee >= policy['gold_floor'] and policy['budget'] >= fee:
            stats = candidate['profile']
            values = [stats['martial_strength'], stats['intellect'], stats['virtue']]
            primary = {'martial': values[0], 'intellect': values[1], 'virtue': values[2]}.get(policy['priority'])
            rank = sorted(values, reverse=True) if primary is None else [primary, *sorted(values, reverse=True)]
            candidates.append((tuple(-v for v in rank), key, candidate['id']))
    for _, key, candidate_id in sorted(candidates):
        city = state.cities[key]
        try:
            civil_staff.hire(game, state, key, candidate_id, owner)
        except GameError:
            continue
        _refresh_faction_offices(game, state, owner)
        state.extension['officer_actions'][str(ident)] = state.turn
        _report(state, city, 'hire_staff', staff_id=candidate_id, gold=civil_staff.RULES['hire_gold'])
        if owner != state.player:
            game._report_ai(state, city, 'hire_staff', candidate_id)
        return True
    return False


def prioritize_grain(game, state, owner, outlook=None, *, economy_plan=None):
    from . import (diplomacy, faction_economy, grain_dispatch, grain_relief, logistics_strategy,
                   military_budget, strategic_granary)

    strategic = strategic_granary.enabled(state)
    if state.phase == 'ai' and owner != state.player and (logistics_strategy.enabled(state) or strategic):
        def rebuild():
            return faction_economy.plan(game,state,owner,granary=strategic)

        plan = economy_plan if economy_plan is not None else rebuild()
        if strategic:
            urgent = plan.shortages(state,within=1)
            if urgent and any(row['bought'] for row in grain_dispatch.recover(game,state,owner,plan,only=urgent)):
                plan = rebuild()
        requests = grain_dispatch.dispatch(game, state, owner, plan=plan)
        if any(row['allocations'] for row in requests):
            plan = rebuild()
        if plan.shortages(state) and diplomacy.request_available_grain(game, state, owner):
            plan = rebuild()
        from . import regional_market
        if strategic:
            from . import granary_planning
            granary_planning.refresh_reserves(game,state,owner,plan)
            if granary_planning.dispatch(game,state,owner,plan):
                plan = rebuild()
        if regional_market.procure(game,state,owner,plan):
            plan = rebuild()
        purchases = grain_dispatch.recover(game, state, owner, plan)
        if any(row['bought'] for row in purchases):
            plan = rebuild()
        _, remaining = plan.outlook(state)
        # Run local trade before elective military development. Leave
        # imminent cities to the emergency quote and its partial lots.
        military_budget.buy_reserves(game, state, owner, outlook=plan.budgets)
        later = {key: row for key, row in remaining.items() if row.zero_in > grain_relief.WARNING_TURNS}
        if later:
            grain_relief.invest(game, state, owner, (None, later))
        return plan.outlook(state)

    if outlook is None:
        outlook = grain_relief.recovery(game, state, owner)
    post = appointments(state, owner)
    if post and post['civil'] is not None:
        grain_relief.dispatch(game, state, owner)
        if outlook[1] and _present(game, state, state.cities[next(iter(outlook[1]))], post['civil']):
            updated = grain_relief.recovery(game, state, owner)
            if (grain_relief.imminent_shortages(updated[1])
                    and diplomacy.request_available_grain(game, state, owner)):
                updated = grain_relief.recovery(game, state, owner)
            grain_relief.invest(game, state, owner, updated)
        if military_budget.enabled(state) and state.phase=='ai' and owner!=state.player:
            military_budget.buy_reserves(game,state,owner)
    return outlook


def run_automatic(game, state, owner, *, outlook=None, economy_plan=None):
    """Spend the faction's remaining orders under the shared policy, once per turn."""
    from . import faction_economy, grain_relief, logistics_strategy, military_budget

    synchronize(game, state)
    if owner not in game.catalog.factions or owner == 'neutral' or owner in state.extension.get('ended_factions', []):
        return
    if owner != state.player:
        auto_assign(game, state, owner)
    post = appointments(state, owner)
    if not post:
        return
    policy = post['policy']
    eligible = []
    for key, city in sorted(state.cities.items()):
        if city.owner != owner:
            continue
        row = _pool(state)['cities'][key]
        if row['last_auto_turn'] == state.turn:
            continue
        row['last_auto_turn'] = state.turn
        eligible.append(key)
    if eligible and owner == state.player:
        outlook = prioritize_grain(game, state, owner, outlook)
    statewide, shortages = outlook or (None, {})
    food_priority = grain_relief.imminent_shortages(shortages)
    discretionary_cities = [key for key in eligible if key not in food_priority]
    for task in policy['task_order']:
        if task == 'personnel':
            # Rank across the entire faction before committing. Lexical city
            # order must not consume the only civil action on a weaker target.
            for _ in range(command_books.MAXIMUM):
                if not command_books.can_spend(state, owner):
                    break
                choices = faction_personnel_targets(game, state, owner, discretionary_cities)
                if not choices:
                    break
                choice = choices[0]
                _personnel(game, state, state.cities[choice['city']], choice)
            if policy['auto_recruit'] and 'civil_staff' in state.extension:
                for _ in range(command_books.MAXIMUM):
                    if not _hire_staff(game, state, owner, discretionary_cities):
                        break
        elif task == 'recruit' and policy['recruit_enabled']:
            budgeted=military_budget.enabled(state) and owner!=state.player
            if statewide is not None and not budgeted:
                continue
            managed = logistics_strategy.enabled(state, logistics_strategy.GARRISON) and owner != state.player
            budgets = (economy_plan.budgets if managed and economy_plan is not None else
                       faction_economy.plan(game, state, owner).budgets if managed else
                       military_budget.budgets(game, state, owner) if budgeted else {})
            for _ in range(command_books.MAXIMUM):
                remaining = command_books.remaining(state, owner)
                for key in eligible:
                    budget=budgets.get(key)
                    if key in shortages and not (budget and budget['threatened']):
                        continue
                    city = state.cities[key]
                    if not command_books.can_spend(state, owner, 'recruit'):
                        break
                    quote = recruitment_preview(game,state,key,budget=budget)
                    if quote['soldiers']:
                        city.gold -= quote['gold']
                        city.grain -= quote['grain']
                        add_reserves(game, state, city, quote['soldiers'], recruited=True)
                        command_books.spend(state, city, 'recruit')
                        _report(state, city, 'recruit', **quote)
                if command_books.remaining(state, owner) == remaining:
                    break
        elif task == 'transport' and 'logistics' in state.extension:
            from . import logistics
            plans = (economy_plan.budgets if economy_plan is not None else
                     military_budget.budgets(game, state, owner)
                     if military_budget.enabled(state) and owner != state.player else None)
            from . import transport_emergency
            if (transport_emergency.stage(state)>=transport_emergency.EXTERNAL_RELIEF
                    and any(row['owner']==owner and row.get('emergency',{}).get('status') in ('waiting_for_supply','no_feasible_exit')
                            for row in logistics._pool(state)['convoys'])):
                from . import convoy_relief
                support=convoy_relief.Planner(game,state,owner)
                support.dispatch_one([state.cities[key] for key in discretionary_cities],plans or {})
            relief_planner = None
            if logistics_strategy.army_relief(state):
                from . import army_relief
                relief_planner = army_relief.Planner(game,state,owner)
            for key in discretionary_cities:
                if command_books.can_spend(state, owner, 'dispatch_transport'):
                    logistics.auto_dispatch_city(game,state,key,plans=plans,relief_planner=relief_planner)


def finish_faction_turn(game, state, owner, *, automatic=True, outlook=None):
    """After manual commands and before the calendar advances, once per city."""
    from . import faction_economy, grain_relief, logistics_strategy, military_budget, strategic_granary
    strategic = strategic_granary.enabled(state)
    planned = (logistics_strategy.enabled(state) or strategic) and owner not in (state.player, 'neutral')
    economy_plan = faction_economy.plan(game, state, owner, granary=strategic) if planned else None
    if economy_plan is not None:
        outlook = economy_plan.outlook(state)
        if logistics_strategy.enabled(state, logistics_strategy.GARRISON):
            for key, budget in economy_plan.budgets.items():
                logistics_strategy.pressure(state, 'cities', key, budget['excess_troops'] > 0)
    if outlook is None:
        outlook = grain_relief.recovery(game, state, owner)
    statewide, shortages = outlook
    hold_grain = {key for key, city in state.cities.items() if city.owner == owner} if statewide is not None else shortages
    food_priority = grain_relief.imminent_shortages(shortages)
    if automatic:
        run_automatic(game, state, owner, outlook=outlook, economy_plan=economy_plan)
        from . import facilities
        facilities.synchronize(game,state)
        if military_budget.enabled(state) and owner!=state.player:
            budgets = economy_plan.budgets if economy_plan is not None else military_budget.budgets(game,state,owner)
            unfilled = {key for key, budget in budgets.items() if budget['deficit'] or budget.get('reserved_grain')}
            hold_grain = set(hold_grain) | unfilled
        facilities.auto_turn(game, state, owner, hold_grain=hold_grain, food_priority=food_priority,
                             allow_stockpiling=(owner == state.player or not grain_units.current_rations()))
        from . import treasures
        treasures.synchronize(game,state)
        treasures.auto_turn(game, state, owner, food_priority=food_priority)
        if owner != state.player:
            from . import city_development, regional_market
            regional_market.automatic_trade(game,state,owner,shortages)
            treasures.ai_idle_turn(game, state, owner, food_priority=food_priority)
            city_development.auto_turn(game, state, owner, shortages=shortages)
    synchronize(game, state)
    summary = dict(gold=0, grain=0, reserves=0, morale=0, cities=0, reason='turn')
    first_city = None
    relief_needed=False
    if logistics_strategy.staging(state) and economy_plan is not None:
        relief_needed=any(row['owner']==owner and not row['supply']['retreat_requested']
                          for row in state.extension['travel']['marches'])
    post = appointments(state, owner)
    if not post:
        return
    policy = post['policy']
    from . import logistics
    frontiers = {city.id for city in logistics._fronts(game, state, owner)} if hold_grain else set()
    for key, city in sorted(state.cities.items()):
        if city.owner != owner:
            continue
        row = _pool(state)['cities'][key]
        if row['last_work_turn'] == state.turn:
            continue
        row['last_work_turn'] = state.turn
        affected = False
        if city.owner == state.player and policy['recruit_enabled']:
            receipt = next((r for r in reversed(_pool(state)['reports']) if r['turn'] == state.turn
                and r['city'] == key and r['kind'] == 'recruit'), None)
            if receipt is not None:
                first_city = first_city or key
                affected = True
                summary['reserves'] += receipt['details']['soldiers']
                summary['gold'] += receipt['details']['gold']
                summary['grain'] += receipt['details']['grain']
        if row['income_month'] != _month(state):
            _reset_income(row, _month(state))
        ident = post['civil']
        if ident is not None and _present(game, state, city, ident):
            duty = 1 if state.extension['officer_actions'].get(str(ident)) == state.turn else 2
            intellect = state.officers[ident].profile.intellect
            points = min(intellect * duty, 99 * _INCOME_DUTIES_PER_MONTH - row['income_points'])
            if points:
                row['income_rate_units'] = _earned_income_units(row) + _civil_income_units(intellect) * points // intellect
                row['income_points'] += points
                row.pop('income_extra_units', None)
        # Active jobs, including explicitly configured reserve transports, have
        # first claim. Assign only the local remainder before training it.
        if key not in hold_grain or key in frontiers:
            cap = budget = None
            if economy_plan is not None and logistics_strategy.enabled(state, logistics_strategy.GARRISON):
                budget = economy_plan.budgets[key]
                # Other orders may already have changed local stock or reserves.
                budget = dict(budget, **faction_economy.capacity(game, state, city, budget))
                cap = faction_economy.allocation_limit(game, state, city, budget)
            held=None
            if logistics_strategy.staging(state) and economy_plan is not None:
                from . import escort_planning
                held=escort_planning.preserves_escort(game,state,city,shortages,budget,relief_needed)
            allocate_garrison(game, state, key, max_added=cap,held=held)
        if key not in hold_grain and policy['training_enabled']:
            quote = training_preview(game, state, key)
            if quote['gain'] and (not strategic or quote['grain'] <= strategic_granary.available(state,city)):
                city.gold -= quote['gold']
                city.grain -= quote['grain']
                row['morale'] += quote['gain']
                _report(state, city, 'training', **quote, morale=row['morale'])
                if city.owner == state.player:
                    first_city = first_city or key
                    affected = True
                    summary['morale'] += quote['gain']
                    summary['gold'] += quote['gold']
                    summary['grain'] += quote['grain']
        if city.owner == state.player and affected:
            summary['cities'] += 1
    if first_city is not None:
        game._emit_event(state, 'domestic_report', city_ids=[first_city], factions=[state.player], details=summary)


def view(game, state):
    result = dict(rules=deepcopy(RULES), scope='faction', factions={}, cities={}, reports=[])
    if state is None or 'domestic' not in state.extension:
        return result
    pool = _pool(state)
    result['reports'] = deepcopy([row for row in pool['reports'] if row['owner'] == state.player])
    residents, away = _office_rosters(state), _away_officers(game, state)
    for owner, post in pool['factions'].items():
        city_ids = sorted(key for key, city in state.cities.items() if city.owner == owner)
        available = {ident for ident in residents.get(owner, ())
                     if ident not in away and _working(state, owner, ident)}
        row = deepcopy(post)
        row.update(civil_active=post['civil'] in available,
            military_active=post['military'] in available, eligible_officers=sorted(available, key=_ref_key),
            city_ids=city_ids, monthly_bonus_preview=dict(gold=0, grain=0),
            recruit_preview=dict(soldiers=0, gold=0, grain=0), training_preview=dict(gain=0, gold=0, grain=0),
            allocation_preview=dict(soldiers=0, officers=0),
            personnel_targets=faction_personnel_targets(game, state, owner) if owner == state.player else [])
        result['factions'][owner] = row
    for key, city in state.cities.items():
        post = result['factions'].get(city.owner, {})
        row = deepcopy(pool['cities'][key])
        row.update(civil=post.get('civil'), military=post.get('military'),
            civil_active=post.get('civil_active', False), military_active=post.get('military_active', False),
            recruit_preview=recruitment_preview(game, state, key), training_preview=training_preview(game, state, key),
            allocation_preview=allocation_preview(game, state, key),
            personnel_targets=personnel_targets(game, state, key) if city.owner == state.player else [])
        base = _income(game, key, state)
        intellect = state.officers[row['civil']].profile.intellect if row['civil_active'] else 0
        row['monthly_bonus_preview'] = _income_bonus(base, _civil_income_units(intellect) * _INCOME_DUTIES_PER_MONTH)
        result['cities'][key] = row
        if post:
            for field in ('monthly_bonus_preview', 'recruit_preview', 'training_preview'):
                for resource, amount in row[field].items():
                    post[field][resource] += amount
            for field in ('soldiers', 'officers'):
                post['allocation_preview'][field] += row['allocation_preview'][field]
    return result


def validate(game, state):
    pool = _pool(state)
    if not isinstance(pool, dict) or set(pool) - {'march_spirit'} != {'schema', 'factions', 'cities', 'unit_morale', 'attempts', 'reports'} or pool['schema'] != SCHEMA:
        raise ValueError('Domestic schema')
    owners = set(game.catalog.factions) - {'neutral'}
    if not isinstance(pool['factions'], dict) or set(pool['factions']) != owners:
        raise ValueError('Domestic factions')
    residents, away = _office_rosters(state), _away_officers(game, state)
    for owner, post in pool['factions'].items():
        if not isinstance(post, dict) or set(post) != _FACTION_FIELDS:
            raise ValueError('Domestic faction offices')
        manual = post['manual_offices']
        if not isinstance(manual, list) or manual != [field for field in _OFFICES if field in manual]:
            raise ValueError('Domestic appointment modes')
        roster = residents.get(owner)
        for field in _OFFICES:
            ident = post[field]
            if ident is not None and (type(ident) not in (int, str) or not _retained(state, owner, ident, roster, away)):
                raise ValueError('Domestic appointment identity')
        if post['civil'] is not None and post['civil'] == post['military']:
            raise ValueError('Domestic dual appointment')
        _validate_policy(game, state, post['policy'])
        envoy = post['policy']['envoy']
        if envoy is not None and not _retained(state, owner, envoy, roster, away):
            raise ValueError('Domestic envoy ownership')
    if not isinstance(pool['cities'], dict) or set(pool['cities']) != set(state.cities):
        raise ValueError('Domestic cities')
    for key, city in state.cities.items():
        row = pool['cities'][key]
        if (not isinstance(row, dict) or set(row) - _CITY_INCOME_FIELDS != _CITY_FIELDS
                or _CITY_INCOME_FIELDS <= row.keys() or row['owner'] != city.owner):
            raise ValueError('Domestic city ledger')
        if (not _integer(row['morale'], 0, 100)
                or not _integer(row['income_points'], 0, 99 * _INCOME_DUTIES_PER_MONTH)
                or not _integer(row.get('income_extra_units', 0), 0, 20 * row['income_points'])
                or not _integer(row.get('income_rate_units', 0), 0,
                                50 * _INCOME_UNITS_PER_PERCENT * row['income_points'] // 99)):
            raise ValueError('Domestic morale/income')
        for field in ('income_month', 'last_income_month'):
            if not _integer(row[field], 0, _month(state)):
                raise ValueError('Domestic income month')
        for field in ('last_work_turn', 'last_auto_turn'):
            if not _integer(row[field], 0, state.turn):
                raise ValueError('Domestic turn receipt')
    if not isinstance(pool['unit_morale'], dict) or len(pool['unit_morale']) > len(state.officers):
        raise ValueError('Domestic unit morale')
    spirit = pool.get('march_spirit', {})
    if (not isinstance(spirit, dict) or not spirit.keys() <= pool['unit_morale'].keys()
            or any(not _integer(v, 0, 99) for v in spirit.values())):
        raise ValueError('Invalid march spirit')
    keys = {str(i) for i in state.officers}
    if any(key not in keys or not _integer(value, 0, 100) for key, value in pool['unit_morale'].items()):
        raise ValueError('Domestic unit morale identity')
    if not isinstance(pool['attempts'], dict) or set(pool['attempts']) - set(game.catalog.factions):
        raise ValueError('Domestic attempt factions')
    for owner, rows in pool['attempts'].items():
        if not isinstance(rows, dict) or len(rows) > len(state.officers):
            raise ValueError('Domestic attempt bounds')
        for key, receipt in rows.items():
            if (key not in keys or not isinstance(receipt, dict) or set(receipt) != {'turn', 'retry_turn'}
                    or not _integer(receipt['turn'], 1, state.turn)
                    or not _integer(receipt['retry_turn'], receipt['turn'], receipt['turn'] + 3)):
                raise ValueError('Domestic attempt receipt')
    if not isinstance(pool['reports'], list) or len(pool['reports']) > 100:
        raise ValueError('Domestic report bounds')
    for row in pool['reports']:
        if (not isinstance(row, dict) or set(row) != _REPORT_FIELDS or row['kind'] not in _REPORT_KINDS
                or row['city'] not in state.cities or row['owner'] not in game.catalog.factions
                or not _integer(row['turn'], 1, state.turn) or not isinstance(row['details'], dict)):
            raise ValueError('Domestic report')
        details = row['details']
        fields = dict(income={'gold', 'grain'}, recruit={'soldiers', 'gold', 'grain'},
            training={'gain', 'gold', 'grain', 'morale'}, policy={'civil', 'military'},
            personnel={'id', 'method', 'actor', 'chance', 'success', 'gold'},
            hire_staff={'staff_id', 'gold'}, allocation={'soldiers', 'officers'})[row['kind']]
        if set(details) != fields:
            raise ValueError('Domestic report details')
        for field in fields & {'gold', 'grain', 'soldiers'}:
            if not _integer(details[field], 0, LIMIT):
                raise ValueError('Domestic report resource')
        for field in fields & {'civil', 'military', 'actor', 'id', 'staff_id'}:
            if details[field] is not None and (type(details[field]) not in (int, str) or details[field] not in state.officers):
                raise ValueError('Domestic report person')
        if row['kind'] == 'personnel' and (details['method'] not in {'recruit_officer', 'persuade_officer'}
                or not _integer(details['chance'], 0, 95) or type(details['success']) is not bool):
            raise ValueError('Domestic report attempt')
        if row['kind'] == 'training' and (not _integer(details['gain'], 1, 5)
                or not _integer(details['morale'], details['gain'], 100)):
            raise ValueError('Domestic report morale')
        if row['kind'] == 'allocation' and (not _integer(details['soldiers'], 1, OFFICER_TROOP_CAP * game.catalog.rules.city_officer_capacity)
                or not _integer(details['officers'], 1, game.catalog.rules.city_officer_capacity)
                or details['officers'] > details['soldiers']):
            raise ValueError('Domestic allocation report')
