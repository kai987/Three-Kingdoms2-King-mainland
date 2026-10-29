"""Two faction offices, bounded automatic tasks and conserved city training degree.

The serialized morale/unit_morale keys remain stable for current campaign saves;
these values represent training degree, not the original temporary morale tactic.

This is an authorial adaptation of the agreed rules, not SAN14's formulas.
Only committed faction-turn and calendar hooks perform work. Views are pure.
"""
from copy import deepcopy

from .errors import GameError
from . import command_books
from .officers import parse_officer_ref

SCHEMA = 'tk2-domestic-v2'
RULES = dict(max_income_bonus_percent=40, personnel_gold=60, persuasion_gold=100,
             training_initial_morale=70, recruit_morale=50, training_per_1000_gold=1,
             training_per_1000_grain=2, automatic_retry_turns=3)
DEFAULT_POLICY = dict(auto_recruit=False, auto_persuade=False, priority='best', envoy=None,
    min_chance=20, budget=100, excluded_targets=[], recruit_enabled=False,
    reserve_target=2000, recruit_budget=50, training_enabled=False,
    gold_floor=100, grain_floor=200, task_order=['personnel', 'recruit', 'transport'])
_CITY_FIELDS = {'owner', 'morale', 'income_month', 'income_points', 'last_work_turn',
                'last_auto_turn', 'last_income_month'}
_FACTION_FIELDS = {'civil', 'military', 'policy'}
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


def _new_faction():
    return dict(civil=None, military=None, policy=deepcopy(DEFAULT_POLICY))


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


def _owned_ids(state, owner):
    return {ident for city in state.cities.values() if city.owner == owner
            for ident in city.roster.officer_ids}


def _retained(game, state, owner, ident):
    person = state.officers.get(ident)
    if (person is None or not person.alive or person.faction_id != owner
            or owner in state.extension.get('ended_factions', [])
            or not any(c.owner == owner for c in state.cities.values())):
        return False
    # A travelling officer keeps the office even if the old home falls before
    # arrival. Work remains paused until an owned city can host the officer.
    battling = ({u['id'] for side in ('attackers', 'defenders') for u in state.battle[side]}
                if state.battle else set())
    return ident in _owned_ids(state, owner) or ident in _marching(game, state) or ident in battling


def _present(game, state, city, ident, *, unused=False):
    """A central official may work for any city of the same faction remotely."""
    person = state.officers.get(ident)
    paid = state.extension.get('civil_staff', {}).get('people', {}).get(ident, {}).get('working', True)
    battling = ({u['id'] for side in ('attackers', 'defenders') for u in state.battle[side]}
                if state.battle else set())
    return bool(person is not None and ident in _owned_ids(state, city.owner) and person.alive
                and person.faction_id == city.owner and person.health > 0 and paid
                and ident not in _marching(game, state) and ident not in battling)


def synchronize(game, state):
    """Reconcile faction appointments and city ledgers without work or RNG."""
    pool = _pool(state)
    for owner in game.catalog.factions:
        if owner == 'neutral':
            continue
        post = pool['factions'].setdefault(owner, _new_faction())
        for field in ('civil', 'military'):
            if post[field] is not None and not _retained(game, state, owner, post[field]):
                post[field] = None
        envoy = post['policy']['envoy']
        if envoy is not None and not _retained(game, state, owner, envoy):
            post['policy']['envoy'] = None
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(state, city))
        if row['owner'] != city.owner:
            # The training degree stays with the garrison. Previous-owner
            # earned income cannot be paid to a conquering faction.
            row.update(owner=city.owner, income_month=_month(state), income_points=0,
                       last_income_month=_month(state), last_work_turn=0, last_auto_turn=0)
    travelling = {str(i) for i in _marching(game, state)}
    battle = state.battle
    if battle:
        travelling.update(str(u['id']) for key in ('attackers', 'defenders') for u in battle[key])
    for ident in list(pool['unit_morale']):
        ref = next((key for key in state.officers if str(key) == ident), None)
        if ref is None or not state.officers[ref].alive or ident not in travelling:
            pool['unit_morale'].pop(ident)
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
    for field in ('civil', 'military'):
        if field in payload:
            ident = payload[field]
            if ident is not None and (type(ident) not in (int, str)
                    or ident != row[field] and not _present(game, state, city, ident)):
                raise GameError('请选择本势力健康且未出征的委任官。')
            revised[field] = ident
    if revised['civil'] is not None and revised['civil'] == revised['military']:
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
    for ident in ids:
        values[str(ident)] = morale(state, city_id)


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


def _income(game, city_id, state=None):
    value = game.catalog.data.get('city_income', {}).get(city_id,
        dict(gold=game.catalog.data['rules'].get('monthly_gold_income', 0),
             grain=game.catalog.data['rules'].get('monthly_grain_income', 0), reserves=0))
    if state is not None:
        from .city_economy import income_at
        from .facilities import adjusted_income
        value=adjusted_income(state,city_id,income_at(game.catalog.data,city_id,state.year,state.month) or value)
    return value


def month_rollover(game, state):
    """After the date advances; add only the previous month's earned bonus."""
    synchronize(game, state)
    current = _month(state)
    summary = dict(gold=0, grain=0, reserves=0, morale=0, cities=0, reason='month')
    first_city = None
    for key, city in state.cities.items():
        row = _pool(state)['cities'][key]
        if row['last_income_month'] >= current:
            continue
        points = row['income_points'] if row['income_month'] == current - 1 else 0
        base = _income(game, key, state)
        bonus = {field: min(LIMIT - getattr(city, field), int(base[field]) * 40 * points // (100 * 99 * 6))
                 for field in ('gold', 'grain')}
        if city.owner == 'neutral':
            bonus = dict(gold=0, grain=0)
        for field, amount in bonus.items():
            setattr(city, field, getattr(city, field) + amount)
        row.update(income_month=current, income_points=0, last_income_month=current)
        if any(bonus.values()):
            _report(state, city, 'income', **bonus)
            if city.owner == state.player:
                first_city = first_city or key
                summary['cities'] += 1
                summary['gold'] += bonus['gold']
                summary['grain'] += bonus['grain']
    if first_city is not None:
        game._emit_event(state, 'domestic_report', city_ids=[first_city], factions=[state.player], details=summary)


def recruitment_preview(game, state, city_id):
    city, row = state.cities[city_id], _pool(state)['cities'][city_id]
    post = appointments(state, city.owner)
    ident, policy = post.get('military'), post.get('policy', DEFAULT_POLICY)
    if ident is None or not _present(game, state, city, ident):
        return dict(soldiers=0, gold=0, grain=0)
    strength = state.officers[ident].profile.martial_strength
    available_gold = min(max(0, city.gold - policy['gold_floor']), policy['recruit_budget'])
    available_grain = max(0, city.grain - policy['grain_floor'])
    unit_gold = 20 - strength // 10
    amount = min(100 + strength, max(0, policy['reserve_target'] - city.reserves),
                 available_gold * 100 // unit_gold, available_grain * 100 // 30,
                 LIMIT - city.reserves)
    return dict(soldiers=amount, gold=(amount * unit_gold + 99) // 100,
                grain=(amount * 30 + 99) // 100)


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
    if city.gold - post['policy']['gold_floor'] < units or city.grain - post['policy']['grain_floor'] < units * 2:
        return dict(gain=0, gold=0, grain=0)
    gain = min(100 - row['morale'], 2 + state.officers[ident].profile.martial_strength // 25)
    return dict(gain=gain, gold=units, grain=units * 2)


def allocation_preview(game, state, city_id):
    """Plan local reserve assignments without drawing RNG or changing the state.

    A faction official manages every owned city, but troops stay in their own
    city. Existing troops are retained; only the unassigned reserve is filled
    into each eligible officer in ability order, up to the requested 1000 cap.
    """
    city = state.cities[city_id]
    result = dict(soldiers=0, officers=0, remaining_reserves=city.reserves, assignments=[])
    if not city.reserves:
        return result
    official = appointments(state, city.owner).get('military')
    if official is None or not _present(game, state, city, official):
        return result
    available = [state.officers[i] for i in city.roster.officer_ids
                 if state.officers[i].troops < 1000 and _present(game, state, city, i)]
    available.sort(key=lambda officer: (-officer.profile.martial_strength,
        -officer.profile.intellect, -officer.profile.virtue, -officer.health,
        -officer.experience, _ref_key(officer.runtime_id)))
    for officer in available:
        amount = min(result['remaining_reserves'], max(0, 1000 - officer.troops))
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


def allocate_garrison(game, state, city_id, *, record=True):
    """Apply the shared player/AI allocation plan; no fees or action are spent."""
    quote = allocation_preview(game, state, city_id)
    if quote['soldiers']:
        city = state.cities[city_id]
        for assignment in quote['assignments']:
            state.officers[assignment['id']].troops = assignment['to']
        city.reserves = quote['remaining_reserves']
        if record:
            _report(state, city, 'allocation', soldiers=quote['soldiers'], officers=quote['officers'])
    return quote


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
    """AI chooses one faction pair; all work uses the ordinary shared service."""
    row = appointments(state, owner)
    cities = sorted((c for c in state.cities.values() if c.owner == owner), key=lambda c: c.id)
    if not row or not cities or owner in state.extension.get('ended_factions', []):
        return
    available = [i for i in _owned_ids(state, owner) if _present(game, state, cities[0], i)]
    civil = [i for i in available if i != row['military']]
    if row['civil'] is None and civil:
        row['civil'] = min(civil, key=lambda i: (-state.officers[i].profile.intellect,
            -state.officers[i].profile.virtue, _ref_key(i)))
    remaining = [i for i in available if i != row['civil']]
    if row['military'] is None and remaining:
        row['military'] = min(remaining, key=lambda i: (-state.officers[i].profile.martial_strength,
            -state.officers[i].profile.intellect, _ref_key(i)))
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
        state.extension['officer_actions'][str(ident)] = state.turn
        _report(state, city, 'hire_staff', staff_id=candidate_id, gold=civil_staff.RULES['hire_gold'])
        if owner != state.player:
            game._report_ai(state, city, 'hire_staff', candidate_id)
        return True
    return False


def run_automatic(game, state, owner):
    """Spend the faction's remaining orders under the shared policy, once per turn."""
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
    for task in policy['task_order']:
        if task == 'personnel':
            # Rank across the entire faction before committing. Lexical city
            # order must not consume the only civil action on a weaker target.
            for _ in range(command_books.MAXIMUM):
                if not command_books.can_spend(state, owner):
                    break
                choices = faction_personnel_targets(game, state, owner, eligible)
                if not choices:
                    break
                choice = choices[0]
                _personnel(game, state, state.cities[choice['city']], choice)
            if policy['auto_recruit'] and 'civil_staff' in state.extension:
                for _ in range(command_books.MAXIMUM):
                    if not _hire_staff(game, state, owner, eligible):
                        break
        elif task == 'recruit' and policy['recruit_enabled']:
            for _ in range(command_books.MAXIMUM):
                remaining = command_books.remaining(state, owner)
                for key in eligible:
                    city = state.cities[key]
                    if not command_books.can_spend(state, owner, 'recruit'):
                        break
                    quote = recruitment_preview(game, state, key)
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
            for key in eligible:
                if command_books.can_spend(state, owner, 'dispatch_transport'):
                    logistics.auto_dispatch_city(game, state, key)


def finish_faction_turn(game, state, owner, *, automatic=True):
    """After manual commands and before the calendar advances, once per city."""
    if automatic:
        run_automatic(game, state, owner)
        from . import facilities
        facilities.synchronize(game,state)
        facilities.auto_turn(game,state,owner)
        from . import treasures
        treasures.synchronize(game,state)
        treasures.auto_turn(game,state,owner)
    synchronize(game, state)
    summary = dict(gold=0, grain=0, reserves=0, morale=0, cities=0, reason='turn')
    first_city = None
    post = appointments(state, owner)
    if not post:
        return
    policy = post['policy']
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
            row.update(income_month=_month(state), income_points=0)
        ident = post['civil']
        if ident is not None and _present(game, state, city, ident):
            duty = 1 if state.extension['officer_actions'].get(str(ident)) == state.turn else 2
            row['income_points'] = min(594, row['income_points'] + state.officers[ident].profile.intellect * duty)
        # Active jobs, including explicitly configured reserve transports, have
        # first claim. Assign only the local remainder before training it.
        allocate_garrison(game, state, key)
        if policy['training_enabled']:
            quote = training_preview(game, state, key)
            if quote['gain']:
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
    for owner, post in pool['factions'].items():
        city_ids = sorted(key for key, city in state.cities.items() if city.owner == owner)
        city = state.cities[city_ids[0]] if city_ids else None
        row = deepcopy(post)
        row.update(civil_active=city is not None and post['civil'] is not None and _present(game, state, city, post['civil']),
            military_active=city is not None and post['military'] is not None and _present(game, state, city, post['military']),
            eligible_officers=sorted((i for i in _owned_ids(state, owner)
                                     if city is not None and _present(game, state, city, i)), key=_ref_key),
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
        row['monthly_bonus_preview'] = {field: int(base[field]) * 40 * intellect // (100 * 99) for field in ('gold', 'grain')}
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
    if not isinstance(pool, dict) or set(pool) != {'schema', 'factions', 'cities', 'unit_morale', 'attempts', 'reports'} or pool['schema'] != SCHEMA:
        raise ValueError('Domestic schema')
    owners = set(game.catalog.factions) - {'neutral'}
    if not isinstance(pool['factions'], dict) or set(pool['factions']) != owners:
        raise ValueError('Domestic factions')
    for owner, post in pool['factions'].items():
        if not isinstance(post, dict) or set(post) != _FACTION_FIELDS:
            raise ValueError('Domestic faction offices')
        for field in ('civil', 'military'):
            ident = post[field]
            if ident is not None and (type(ident) not in (int, str) or not _retained(game, state, owner, ident)):
                raise ValueError('Domestic appointment identity')
        if post['civil'] is not None and post['civil'] == post['military']:
            raise ValueError('Domestic dual appointment')
        _validate_policy(game, state, post['policy'])
        envoy = post['policy']['envoy']
        if envoy is not None and not _retained(game, state, owner, envoy):
            raise ValueError('Domestic envoy ownership')
    if not isinstance(pool['cities'], dict) or set(pool['cities']) != set(state.cities):
        raise ValueError('Domestic cities')
    for key, city in state.cities.items():
        row = pool['cities'][key]
        if not isinstance(row, dict) or set(row) != _CITY_FIELDS or row['owner'] != city.owner:
            raise ValueError('Domestic city ledger')
        if not _integer(row['morale'], 0, 100) or not _integer(row['income_points'], 0, 594):
            raise ValueError('Domestic morale/income')
        for field in ('income_month', 'last_income_month'):
            if not _integer(row[field], 0, _month(state)):
                raise ValueError('Domestic income month')
        for field in ('last_work_turn', 'last_auto_turn'):
            if not _integer(row[field], 0, state.turn):
                raise ValueError('Domestic turn receipt')
    if not isinstance(pool['unit_morale'], dict) or len(pool['unit_morale']) > len(state.officers):
        raise ValueError('Domestic unit morale')
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
        if row['kind'] == 'allocation' and (not _integer(details['soldiers'], 1, 1000 * game.catalog.rules.city_officer_capacity)
                or not _integer(details['officers'], 1, game.catalog.rules.city_officer_capacity)
                or details['officers'] > details['soldiers']):
            raise ValueError('Domestic allocation report')
