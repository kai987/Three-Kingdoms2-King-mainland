"""Two city offices, bounded automatic tasks and conserved training degree.

The serialized morale/unit_morale keys remain stable for current campaign saves;
these values represent training degree, not the original temporary morale tactic.

This is an authorial adaptation of the agreed rules, not SAN14's formulas.
Only committed faction-turn and calendar hooks perform work. Views are pure.
"""
from copy import deepcopy
from math import ceil

from .errors import GameError
from .officers import parse_officer_ref

SCHEMA = 'tk2-domestic-v1'
RULES = dict(max_income_bonus_percent=40, personnel_gold=60, persuasion_gold=100,
             training_initial_morale=70, recruit_morale=50, training_per_1000_gold=1,
             training_per_1000_grain=2, automatic_retry_turns=3)
DEFAULT_POLICY = dict(auto_recruit=False, auto_persuade=False, priority='best', envoy=None,
    min_chance=20, budget=100, excluded_targets=[], recruit_enabled=False,
    reserve_target=2000, recruit_budget=50, training_enabled=False,
    gold_floor=100, grain_floor=200, task_order=['personnel', 'recruit', 'transport'])
_CITY_FIELDS = {'owner', 'civil', 'military', 'morale', 'policy', 'income_month',
                'income_points', 'last_work_turn', 'last_auto_turn', 'last_income_month'}
_REPORT_FIELDS = {'turn', 'city', 'owner', 'kind', 'details'}
_REPORT_KINDS = {'income', 'recruit', 'training', 'personnel', 'policy', 'hire_staff'}
LIMIT = 100000000


def _ref_key(value):
    return (0, value) if type(value) is int else (1, str(value))


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _month(state):
    return state.year * 12 + state.month - 1


def _new_city(state, city):
    return dict(owner=city.owner, civil=None, military=None, morale=70,
                policy=deepcopy(DEFAULT_POLICY), income_month=_month(state), income_points=0,
                last_work_turn=0, last_auto_turn=0, last_income_month=_month(state))


def empty(game, state):
    return dict(schema=SCHEMA, cities={key: _new_city(state, city) for key, city in state.cities.items()},
                unit_morale={}, attempts={}, reports=[])


def _pool(state):
    return state.extension['domestic']


def _report(state, city, kind, **details):
    reports = _pool(state)['reports']
    reports.append(dict(turn=state.turn, city=city.id, owner=city.owner, kind=kind, details=details))
    reports[:] = reports[-100:]


def _marching(game, state):
    return game._march_ids(state)


def _present(game, state, city, ident, *, unused=False):
    person = state.officers.get(ident)
    paid = state.extension.get('civil_staff', {}).get('people', {}).get(ident, {}).get('working', True)
    return bool(person is not None and ident in city.roster.officer_ids and person.alive
                and person.faction_id == city.owner and person.health > 0
                and paid
                and ident not in _marching(game, state)
                and (not unused or state.extension['officer_actions'].get(str(ident)) != state.turn))


def synchronize(game, state):
    """Reconcile appointments and new cities, without doing work or drawing RNG."""
    pool = _pool(state)
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(state, city))
        if row['owner'] != city.owner:
            row.update(owner=city.owner, civil=None, military=None,
                       policy=deepcopy(DEFAULT_POLICY), income_month=_month(state), income_points=0,
                       last_income_month=_month(state), last_work_turn=0, last_auto_turn=0)
        for field in ('civil', 'military'):
            ident = row[field]
            person = state.officers.get(ident)
            if ident is not None and (person is None or not person.alive
                    or person.faction_id != city.owner or ident not in city.roster.officer_ids):
                row[field] = None
        ident = row['policy']['envoy']
        if ident is not None and (ident not in state.officers or not state.officers[ident].alive
                or state.officers[ident].faction_id != city.owner or ident not in city.roster.officer_ids):
            row['policy']['envoy'] = None
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
    if (not isinstance(payload, dict) or set(payload) - {'city', 'civil', 'military', 'policy'}
            or not isinstance(payload.get('city'), str) or payload['city'] not in state.cities):
        raise GameError('内政委任参数无效。')
    city = state.cities[payload['city']]
    if city.owner != owner or owner == 'neutral' or state.phase not in {'city', 'ai'}:
        raise GameError('请选择战略阶段的本方城池。')
    row = _pool(state)['cities'][city.id]
    revised = deepcopy(row)
    for field in ('civil', 'military'):
        if field in payload:
            ident = payload[field]
            if ident is not None and (type(ident) not in (int, str)
                    or ident != row[field] and not _present(game, state, city, ident)):
                raise GameError('请选择本城健康且未出征的委任官。')
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
            raise GameError('请选择本城健康且未出征的使者。')
    _pool(state)['cities'][city.id] = revised
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


def _income(game, city_id):
    return game.catalog.data.get('city_income', {}).get(city_id,
        dict(gold=game.catalog.data['rules'].get('monthly_gold_income', 0),
             grain=game.catalog.data['rules'].get('monthly_grain_income', 0), reserves=0))


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
        base = _income(game, key)
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
    ident, policy = row['military'], row['policy']
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
    ident = row['military']
    if ident is None or not _present(game, state, city, ident) or row['morale'] >= 100:
        return dict(gain=0, gold=0, grain=0)
    soldiers = _garrison_troops(game, state, city)
    if not soldiers:
        return dict(gain=0, gold=0, grain=0)
    units = (soldiers + 999) // 1000
    if city.gold - row['policy']['gold_floor'] < units or city.grain - row['policy']['grain_floor'] < units * 2:
        return dict(gain=0, gold=0, grain=0)
    gain = min(100 - row['morale'], 2 + state.officers[ident].profile.martial_strength // 25)
    return dict(gain=gain, gold=units, grain=units * 2)


def _chance(actor, target, method):
    if method == 'recruit_officer':
        return max(15, min(95, 35 + actor.profile.virtue // 2 + actor.profile.intellect // 5 - target.profile.virtue // 5))
    return max(5, min(75, 50 + (actor.profile.virtue - target.loyalty) // 2
                      + (actor.profile.intellect - target.profile.intellect) // 4))


def personnel_targets(game, state, city_id):
    city, row = state.cities[city_id], _pool(state)['cities'][city_id]
    policy = row['policy']
    if row['civil'] is None or not _present(game, state, city, row['civil'], unused=True):
        return []
    choices = []
    attempts = _pool(state)['attempts'].get(city.owner, {})
    for method, enabled, candidates, actor_id, fee in (
            ('recruit_officer', policy['auto_recruit'], game._free_candidates(state, city), row['civil'], game.catalog.data['rules']['recruit_officer_gold']),
            ('persuade_officer', policy['auto_persuade'], game._persuadable(state, city),
             row['civil'] if policy['envoy'] is None else policy['envoy'], game.catalog.data['rules']['persuade_officer_gold'])):
        if not enabled or fee > policy['budget'] or city.gold - fee < policy['gold_floor']:
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

    def sort_key(choice):
        target = state.officers[choice['id']].profile
        stats = [target.martial_strength, target.intellect, target.virtue]
        primary = {'martial': stats[0], 'intellect': stats[1], 'virtue': stats[2]}.get(policy['priority'])
        ranking = sorted(stats, reverse=True) if primary is None else [primary, *sorted(stats, reverse=True)]
        location = state.extension['free_locations'].get(str(choice['id']))
        distance = 0 if location == city_id else 1
        return (*(-value for value in ranking), -choice['chance'], distance, _ref_key(choice['id']), choice['method'])
    return sorted(choices, key=sort_key)


def _personnel(game, state, city):
    if game._city_occupancy(state, city) >= game.catalog.rules.city_officer_capacity:
        return False
    choices = personnel_targets(game, state, city.id)
    if not choices:
        return False
    choice = choices[0]
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
    """AI chooses appointments; the work below is exactly the player service."""
    if 'logistics' in state.extension:
        from . import logistics
        fronts = {c.id for c in logistics._fronts(game, state, owner)}
    else:
        fronts = set()
    for key, city in state.cities.items():
        if city.owner != owner:
            continue
        row = _pool(state)['cities'][key]
        available = [i for i in city.roster.officer_ids if _present(game, state, city, i)]
        civil = [i for i in available if i != row['military']]
        if row['civil'] is None and civil:
            row['civil'] = min(civil, key=lambda i: (-state.officers[i].profile.intellect,
                -state.officers[i].profile.virtue, _ref_key(i)))
        remaining = [i for i in available if i != row['civil']]
        if row['military'] is None and remaining:
            row['military'] = min(remaining, key=lambda i: (-state.officers[i].profile.martial_strength,
                -state.officers[i].profile.intellect, _ref_key(i)))
        row['policy'].update(auto_recruit=True, auto_persuade=True, recruit_enabled=True,
                             training_enabled=True)
        row['policy']['task_order'] = ['recruit', 'personnel', 'transport'] if key in fronts else ['transport', 'personnel', 'recruit']
    if 'logistics' in state.extension:
        from . import logistics
        logistics.prepare_ai(game, state, owner)


prepare_ai = auto_assign


def run_automatic(game, state, owner):
    """Use at most the city's remaining active action; no extra AI action."""
    synchronize(game, state)
    if owner != state.player:
        auto_assign(game, state, owner)
    if owner not in game.catalog.factions or owner in state.extension.get('ended_factions', []):
        return
    for key, city in sorted(state.cities.items()):
        if city.owner != owner:
            continue
        row = _pool(state)['cities'][key]
        if row['last_auto_turn'] == state.turn:
            continue
        row['last_auto_turn'] = state.turn
        if city.action_used:
            continue
        for task in row['policy']['task_order']:
            if task == 'personnel':
                if _personnel(game, state, city):
                    break
                if row['policy']['auto_recruit'] and 'civil_staff' in state.extension:
                    from . import civil_staff
                    candidate = state.extension['civil_staff']['cities'][key]['candidate']
                    if candidate and city.gold - 60 >= row['policy']['gold_floor'] and row['policy']['budget'] >= 60:
                        try:
                            civil_staff.hire(game, state, key, candidate['id'], city.owner)
                        except GameError:
                            pass
                        else:
                            _report(state, city, 'hire_staff', staff_id=candidate['id'], gold=60)
                            if city.owner != state.player:
                                game._report_ai(state, city, 'hire_staff', candidate['id'])
                            break
            elif task == 'recruit' and row['policy']['recruit_enabled']:
                quote = recruitment_preview(game, state, key)
                if quote['soldiers']:
                    city.gold -= quote['gold']
                    city.grain -= quote['grain']
                    add_reserves(game, state, city, quote['soldiers'], recruited=True)
                    city.action_used = True
                    _report(state, city, 'recruit', **quote)
                    break
            elif task == 'transport' and 'logistics' in state.extension:
                from . import logistics
                if logistics.auto_dispatch_city(game, state, key):
                    break


def finish_faction_turn(game, state, owner, *, automatic=True):
    """After manual commands and before the calendar advances, once per city."""
    if automatic:
        run_automatic(game, state, owner)
    synchronize(game, state)
    summary = dict(gold=0, grain=0, reserves=0, morale=0, cities=0, reason='turn')
    first_city = None
    for key, city in sorted(state.cities.items()):
        if city.owner != owner:
            continue
        row = _pool(state)['cities'][key]
        if row['last_work_turn'] == state.turn:
            continue
        row['last_work_turn'] = state.turn
        affected = False
        if city.owner == state.player and row['policy']['recruit_enabled']:
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
        ident = row['civil']
        if ident is not None and _present(game, state, city, ident):
            duty = 1 if state.extension['officer_actions'].get(str(ident)) == state.turn else 2
            row['income_points'] = min(594, row['income_points'] + state.officers[ident].profile.intellect * duty)
        if row['policy']['training_enabled']:
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
    result = dict(rules=deepcopy(RULES), cities={}, reports=[])
    if state is None or 'domestic' not in state.extension:
        return result
    pool = _pool(state)
    result['reports'] = deepcopy([row for row in pool['reports'] if row['owner'] == state.player])
    for key, city in state.cities.items():
        row = deepcopy(pool['cities'][key])
        row.update(civil_active=row['civil'] is not None and _present(game, state, city, row['civil']),
            military_active=row['military'] is not None and _present(game, state, city, row['military']),
            eligible_officers=sorted((i for i in city.roster.officer_ids if _present(game, state, city, i, unused=True)), key=_ref_key),
            recruit_preview=recruitment_preview(game, state, key),
            training_preview=training_preview(game, state, key),
            personnel_targets=personnel_targets(game, state, key) if city.owner == state.player else [])
        base = _income(game, key)
        intellect = state.officers[row['civil']].profile.intellect if row['civil_active'] else 0
        row['monthly_bonus_preview'] = {field: int(base[field]) * 40 * intellect // (100 * 99) for field in ('gold', 'grain')}
        result['cities'][key] = row
    return result


def validate(game, state):
    pool = _pool(state)
    if not isinstance(pool, dict) or set(pool) != {'schema', 'cities', 'unit_morale', 'attempts', 'reports'} or pool['schema'] != SCHEMA:
        raise ValueError('Domestic schema')
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
        for field in ('civil', 'military'):
            ident = row[field]
            if ident is not None and (type(ident) not in (int, str) or ident not in state.officers
                    or ident not in city.roster.officer_ids or not state.officers[ident].alive
                    or state.officers[ident].faction_id != city.owner):
                raise ValueError('Domestic appointment identity')
        if row['civil'] is not None and row['civil'] == row['military']:
            raise ValueError('Domestic dual appointment')
        _validate_policy(game, state, row['policy'])
        envoy = row['policy']['envoy']
        if envoy is not None and (envoy not in city.roster.officer_ids
                or not state.officers[envoy].alive or state.officers[envoy].faction_id != city.owner):
            raise ValueError('Domestic envoy ownership')
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
            hire_staff={'staff_id', 'gold'})[row['kind']]
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
