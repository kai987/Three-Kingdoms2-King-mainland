"""Bounded city treasure and faction rewards, shared by players and AI.

These are remake rules, not original-game treasure formulas. Only committed
commands change assets or sample RNG. Views, governors and quotes are pure.
"""
from copy import deepcopy

from .errors import GameError
from . import command_books
from .officers import parse_officer_ref, ref_sort_key
from .city_economy import tier_at

SCHEMA = 'tk2-treasury-v1'
LIMIT = 100000000
RULES = dict(city_cap=99, search_gold=20, sell_gold_per_treasure=100,
             reward_gold_max=100, reward_gold_divisor=3000,
             reward_treasure_base=5, reward_treasure_virtue_divisor=20,
             loyalty_cap=100)
DEFAULT_POLICY = dict(enabled=False, target_loyalty=90, gold_budget=100,
                      gold_floor=100, treasure_floor=1, prefer='gold')
_FIELDS = {'schema', 'cities', 'factions', 'ledger', 'auto_turns'}
_CITY_FIELDS = {'owner', 'treasure', 'governor', 'governor_mode'}
_LEDGER_FIELDS = {'initial', 'found', 'spent', 'sold', 'lost'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _pool(state):
    return state.extension['treasury']


def _battle_ids(state):
    return {unit['id'] for side in ('attackers', 'defenders')
            for unit in (state.battle or {}).get(side, [])}


def _present(game, state, city, ident, *, unused=False):
    person = state.officers.get(ident)
    paid = state.extension.get('civil_staff', {}).get('people', {}).get(ident, {}).get('working', True)
    return bool(person is not None and ident in city.roster.officer_ids
        and city.owner != 'neutral' and person.faction_id == city.owner
        and person.alive and person.health > 0 and paid and ident not in game._march_ids(state)
        and ident not in _battle_ids(state))


def _governor(game, state, city, row=None):
    if city.owner == 'neutral':
        return None
    if (row and row['owner'] == city.owner and row['governor_mode'] == 'manual'
            and _present(game, state, city, row['governor'])):
        return row['governor']
    leader = state.extension.get('leaders', {}).get(city.owner)
    eligible = [ident for ident in city.roster.officer_ids if _present(game, state, city, ident)]
    if leader in eligible:
        return leader
    return min(eligible, key=lambda ident: (-state.officers[ident].profile.virtue,
        -state.officers[ident].profile.intellect, -state.officers[ident].health,
        ref_sort_key(ident))) if eligible else None


def empty(game, state):
    cities = {}
    for key, city in state.cities.items():
        tier = tier_at(game.catalog.data, key, state.year, state.month)
        amount = {'normal': 2, 'large': 4, 'giant': 6}[tier] if city.owner != 'neutral' else 0
        cities[key] = dict(owner=city.owner, treasure=amount,
                           governor=_governor(game, state, city), governor_mode='auto')
    owners = set(game.catalog.factions) - {'neutral'}
    return dict(schema=SCHEMA, cities=cities,
        factions={owner: deepcopy(DEFAULT_POLICY) for owner in sorted(owners)},
        ledger=dict(initial=sum(row['treasure'] for row in cities.values()),
                    found=0, spent=0, sold=0, lost=0),
        auto_turns={owner: 0 for owner in sorted(owners)})


def synchronize(game, state):
    """Reconcile actual owners and governors; never mint, spend, work or draw."""
    pool = _pool(state)
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key,
            dict(owner=city.owner, treasure=0, governor=None, governor_mode='auto'))
        if row['owner'] != city.owner:
            row.update(owner=city.owner, governor=None, governor_mode='auto')
        if row['governor_mode'] == 'manual' and not _present(game, state, city, row['governor']):
            row['governor_mode'] = 'auto'
        row['governor'] = _governor(game, state, city, row)


def count(state, city_id):
    """Read without creating a missing treasury entry."""
    return state.extension.get('treasury', {}).get('cities', {}).get(city_id, {}).get('treasure', 0)


city_count = count


def credit(state, city_id, amount, *, reason='transfer'):
    if not _int(amount, 0, 99) or reason not in {'transfer', 'found', 'initial'}:
        raise GameError('寶數變動無效。')
    if amount == 0:
        return 0
    pool = _pool(state)
    if city_id not in pool['cities'] or count(state, city_id) + amount > 99:
        raise GameError('本城寶數已達上限，請等待庫存空間。')
    counter = 'found' if reason == 'found' else 'initial' if reason == 'initial' else None
    if counter and pool['ledger'][counter] + amount > LIMIT:
        raise GameError('寶的累計數量超出上限。')
    pool['cities'][city_id]['treasure'] += amount
    if counter:
        pool['ledger'][counter] += amount
    return amount


add = credit


def debit(state, city_id, amount, *, reason='transfer'):
    if not _int(amount, 0, 99) or reason not in {'transfer', 'spent', 'sold', 'lost'}:
        raise GameError('寶數變動無效。')
    if amount == 0:
        return 0
    pool = _pool(state)
    if city_id not in pool['cities'] or amount > count(state, city_id):
        raise GameError('本城寶不足。')
    if reason != 'transfer' and pool['ledger'][reason] + amount > LIMIT:
        raise GameError('寶的累計數量超出上限。')
    pool['cities'][city_id]['treasure'] -= amount
    if reason != 'transfer':
        pool['ledger'][reason] += amount
    return amount


def record_loss(state, amount):
    """Record cargo already lost from a convoy, without debiting a city twice."""
    if not _int(amount, 0, LIMIT):
        raise GameError('寶的損失數量無效。')
    if amount:
        if _pool(state)['ledger']['lost'] + amount > LIMIT:
            raise GameError('寶的累計數量超出上限。')
        _pool(state)['ledger']['lost'] += amount


def inherit_city(state, city_id, parent_id):
    """A new node receives a quarter of actual parent stock, never new assets."""
    if city_id == parent_id or city_id not in _pool(state)['cities']:
        raise GameError('新城寶庫尚未初始化。')
    amount = count(state, parent_id) // 4
    if count(state, city_id) + amount > 99:
        raise GameError('本城寶數已達上限，請等待庫存空間。')
    debit(state, parent_id, amount)
    credit(state, city_id, amount)
    return amount


def _ready(state, owner):
    return bool(owner != 'neutral' and owner not in state.extension.get('ended_factions', [])
        and not state.extension.get('pending_succession', {}).get(owner)
        and state.phase == ('city' if owner == state.player else 'ai'))


def _city(game, state, key, owner, *, action=False, kind=1):
    if (not _ready(state, owner) or not isinstance(key, str) or key not in state.cities
            or state.cities[key].owner != owner):
        raise GameError('目前不能操作這座城的寶庫。')
    city = state.cities[key]
    if action:
        command_books.require(state, owner, kind)
    return city


def _payload(payload, fields, required):
    if not isinstance(payload, dict) or set(payload) - set(fields) or not set(required) <= set(payload):
        raise GameError('寶庫操作參數無效。')


def _actor(game, state, city, ident):
    try:
        ident = parse_officer_ref(ident, game.catalog.rules)
    except (ValueError, TypeError) as error:
        raise GameError('請選擇本城健康且在場的武將。') from error
    if not _present(game, state, city, ident, unused=True):
        raise GameError('請選擇本城健康且在場的武將。')
    return ident


def _spend_action(state, city, actor, kind):
    command_books.spend(state, city, kind)
    state.extension['officer_actions'][str(actor)] = state.turn


def _emit(game, state, kind, city, people, details):
    game._emit_event(state, kind, city_ids=[city.id],
        person_ids=[state.officers[ident].person_id for ident in dict.fromkeys(people)],
        factions=[city.owner], details=details)


def search(game, state, payload, owner):
    _payload(payload, {'city', 'actor'}, {'city', 'actor'})
    city = _city(game, state, payload['city'], owner, action=True, kind='search_treasure')
    actor = _actor(game, state, city, payload['actor'])
    if count(state, city.id) >= 99:
        raise GameError('本城寶數已達上限，搜尋未執行。')
    if city.gold < RULES['search_gold']:
        raise GameError('搜尋寶所需金錢不足。')
    profile = state.officers[actor].profile
    chance = max(15, min(80, 20 + profile.intellect // 3 + profile.virtue // 5))
    if _pool(state)['ledger']['found'] >= LIMIT:
        raise GameError('寶的累計數量超出上限。')
    success = state.rng.next() % 100 < chance
    city.gold -= RULES['search_gold']
    if success:
        credit(state, city.id, 1, reason='found')
    _spend_action(state, city, actor, 'search_treasure')
    details = dict(actor=state.officers[actor].person_id, amount=int(success), chance=chance,
                   gold=RULES['search_gold'])
    _emit(game, state, 'treasure_found' if success else 'treasure_search_failed', city, [actor], details)
    return dict(success=success, **details)


def _gold_gain(virtue, amount, gap):
    return min(gap, max(1, (amount * (50 + virtue) + 2999) // 3000))


def _reward_target(game, state, city, ident):
    ident = parse_officer_ref(ident, game.catalog.rules)
    if (not _present(game, state, city, ident)
            or ident in state.extension.get('leaders', {}).values()):
        raise GameError('只能賞賜本城在場的非君主武將。')
    if state.officers[ident].loyalty >= 100:
        raise GameError('這名武將的忠誠已達上限，賞賜未執行。')
    return ident


def reward(game, state, payload, owner):
    _payload(payload, {'city', 'officer', 'kind', 'amount'}, {'city', 'officer', 'kind', 'amount'})
    city = _city(game, state, payload['city'], owner, action=True, kind='reward_officer')
    governor = _governor(game, state, city, _pool(state)['cities'][city.id])
    actor = _actor(game, state, city, governor)
    target = _reward_target(game, state, city, payload['officer'])
    kind, amount = payload['kind'], payload['amount']
    if kind not in ('gold', 'treasure'):
        raise GameError('賞賜種類無效。')
    gap = 100 - state.officers[target].loyalty
    virtue = state.officers[actor].profile.virtue
    if kind == 'gold':
        if not _int(amount, 1, 100) or amount > city.gold:
            raise GameError('賞金必須為1至100，且不能超過本城金錢。')
        gain = _gold_gain(virtue, amount, gap)
    else:
        if type(amount) is not int or amount != 1 or count(state, city.id) < 1:
            raise GameError('每次賞賜必須使用1份寶，且本城寶足夠。')
        gain = min(gap, 5 + virtue // 20)
    before = state.officers[target].loyalty
    if kind == 'gold':
        city.gold -= amount
    else:
        debit(state, city.id, 1, reason='spent')
    state.officers[target].loyalty += gain
    _spend_action(state, city, actor, 'reward_officer')
    details = dict(actor=state.officers[actor].person_id, target=state.officers[target].person_id,
        kind=kind, amount=amount, gain=gain, loyalty_before=before,
        loyalty_after=state.officers[target].loyalty)
    _emit(game, state, 'officer_rewarded', city, [actor, target], details)
    return details


def sell(game, state, payload, owner):
    _payload(payload, {'city', 'actor', 'amount'}, {'city', 'actor', 'amount'})
    city = _city(game, state, payload['city'], owner, action=True, kind='sell_treasure')
    actor = _actor(game, state, city, payload['actor'])
    amount = payload['amount']
    if not _int(amount, 1, 99) or amount > count(state, city.id):
        raise GameError('賣寶數量必須為1至本城持有數量。')
    gold = amount * RULES['sell_gold_per_treasure']
    if city.gold + gold > LIMIT:
        raise GameError('本城金錢已達上限，賣寶未執行。')
    debit(state, city.id, amount, reason='sold')
    city.gold += gold
    _spend_action(state, city, actor, 'sell_treasure')
    details = dict(actor=state.officers[actor].person_id, amount=amount, gold=gold)
    _emit(game, state, 'treasure_sold', city, [actor], details)
    return details


def set_governor(game, state, payload, owner):
    _payload(payload, {'city', 'officer'}, {'city', 'officer'})
    city = _city(game, state, payload['city'], owner)
    ident = payload['officer']
    if ident is not None:
        ident = parse_officer_ref(ident, game.catalog.rules)
        if not _present(game, state, city, ident):
            raise GameError('太守必須為本城在場且健康的本方武將。')
    row = _pool(state)['cities'][city.id]
    row['governor_mode'] = 'auto' if ident is None else 'manual'
    row['governor'] = ident if ident is not None else _governor(game, state, city)
    details = dict(governor=state.officers[row['governor']].person_id if row['governor'] is not None else None,
                   mode=row['governor_mode'])
    _emit(game, state, 'governor_assigned', city, [row['governor']] if row['governor'] is not None else [], details)
    return details


def _validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
        raise ValueError('Treasury policy fields')
    if type(policy['enabled']) is not bool or policy['prefer'] not in ('gold', 'treasure'):
        raise ValueError('Treasury policy preferences')
    for key, low, high in (('target_loyalty', 1, 100), ('gold_budget', 0, 1000000),
                            ('gold_floor', 0, LIMIT), ('treasure_floor', 0, 99)):
        if not _int(policy[key], low, high):
            raise ValueError('Treasury policy limits')


def set_policy(game, state, payload, owner):
    _payload(payload, {'faction', 'policy'}, {'faction', 'policy'})
    if (payload['faction'] != owner or owner not in _pool(state)['factions']
            or not _ready(state, owner) or not isinstance(payload['policy'], dict)
            or set(payload['policy']) - set(DEFAULT_POLICY)):
        raise GameError('寶庫方針參數無效。')
    revised = dict(_pool(state)['factions'][owner], **payload['policy'])
    try:
        _validate_policy(revised)
    except ValueError as error:
        raise GameError('寶庫方針超出允許範圍。') from error
    _pool(state)['factions'][owner] = revised


def auto_turn(game, state, owner):
    """One deterministic faction pass, using the ordinary reward service."""
    pool = _pool(state)
    if owner not in pool['factions'] or not _ready(state, owner) or pool['auto_turns'][owner] == state.turn:
        return []
    pool['auto_turns'][owner] = state.turn
    policy = pool['factions'][owner]
    if not policy['enabled']:
        return []
    budget, results = policy['gold_budget'], []
    for _ in range(command_books.MAXIMUM):
        completed = len(results)
        for key, city in sorted(state.cities.items()):
            if city.owner != owner or not command_books.can_spend(state, owner):
                continue
            actor = _governor(game, state, city, pool['cities'][key])
            if not _present(game, state, city, actor, unused=True):
                continue
            targets = [i for i in city.roster.officer_ids if _present(game, state, city, i)
                and i not in state.extension['leaders'].values()
                and state.officers[i].loyalty < policy['target_loyalty']]
            if not targets:
                continue
            target = min(targets, key=lambda ident: (state.officers[ident].loyalty,
                -state.officers[ident].profile.virtue, -state.officers[ident].profile.intellect,
                ref_sort_key(ident)))
            maximum = min(100, budget, max(0, city.gold - policy['gold_floor']))
            kinds = ('gold', 'treasure') if policy['prefer'] == 'gold' else ('treasure', 'gold')
            for kind in kinds:
                if not command_books.can_spend(state, owner, 'reward_officer'):
                    break
                if kind == 'gold':
                    if maximum < 1:
                        continue
                    gap = policy['target_loyalty'] - state.officers[target].loyalty
                    amount = next((n for n in range(1, maximum + 1)
                        if _gold_gain(state.officers[actor].profile.virtue, n, 100) >= gap), maximum)
                else:
                    if count(state, key) <= policy['treasure_floor']:
                        continue
                    amount = 1
                results.append(reward(game, state,
                    dict(city=key, officer=target, kind=kind, amount=amount), owner))
                if kind == 'gold':
                    budget -= amount
                break
        if len(results) == completed:
            break
    return results


def ai_idle_turn(game, state, owner):
    """Choose idle work, then use exactly the same search/sale services.

    This is a caller-selected AI strategy, never an implicit player policy.
    Every accepted order uses the same bounded faction pool.
    """
    pool = _pool(state)
    if owner not in pool['factions'] or not _ready(state, owner):
        return []
    policy, results = pool['factions'][owner], []
    for _ in range(command_books.MAXIMUM):
        completed = len(results)
        for key, city in sorted(state.cities.items()):
            if city.owner != owner or not command_books.can_spend(state, owner):
                continue
            actors = [ident for ident in city.roster.officer_ids
                      if _present(game, state, city, ident, unused=True)]
            if not actors:
                continue
            actor = min(actors, key=lambda ident: (-state.officers[ident].profile.intellect,
                -state.officers[ident].profile.virtue, ref_sort_key(ident)))
            stock = count(state, key)
            if stock > policy['treasure_floor'] and city.gold < policy['gold_floor']:
                amount = min((policy['gold_floor'] - city.gold + 99) // 100,
                             stock - policy['treasure_floor'], (LIMIT - city.gold) // 100)
                if amount and command_books.can_spend(state, owner, 'sell_treasure'):
                    results.append(sell(game, state, dict(city=key, actor=actor, amount=amount), owner))
            elif (command_books.can_spend(state, owner, 'search_treasure') and stock < 2 and city.gold >= policy['gold_floor'] + RULES['search_gold']
                  and pool['ledger']['found'] < LIMIT):
                results.append(search(game, state, dict(city=key, actor=actor), owner))
        if len(results) == completed:
            break
    return results


def view(game, state):
    result = dict(schema=SCHEMA, rules=dict(RULES), cities={}, factions={}, ledger={})
    if state is None:
        return result
    pool = _pool(state)
    result['ledger'] = dict(pool['ledger'])
    result['factions'] = {owner: dict(policy=dict(policy)) for owner, policy in pool['factions'].items()}
    for key, city in state.cities.items():
        saved = pool['cities'][key]
        governor = _governor(game, state, city, saved)
        candidates = sorted((i for i in city.roster.officer_ids if _present(game, state, city, i)), key=ref_sort_key)
        actors = [i for i in candidates if _present(game, state, city, i, unused=True)]
        ready = _ready(state, city.owner) and command_books.can_spend(state, city.owner)
        actor_ready = governor in actors
        amount = count(state, key)
        gold_max = min(100, city.gold)
        targets = []
        for ident in candidates:
            target = state.officers[ident]
            if ident in state.extension['leaders'].values() or target.loyalty >= 100:
                continue
            intervals = []
            virtue = state.officers[governor].profile.virtue if governor is not None else 0
            if governor is not None:
                for gold in range(1, gold_max + 1):
                    gain = _gold_gain(virtue, gold, 100 - target.loyalty)
                    if intervals and intervals[-1]['gain'] == gain:
                        intervals[-1]['max'] = gold
                    else:
                        intervals.append(dict(min=gold, max=gold, gain=gain, loyalty=target.loyalty + gain))
            treasure_gain = min(100 - target.loyalty, 5 + virtue // 20)
            targets.append(dict(id=ident, loyalty=target.loyalty,
                gold_max=gold_max if governor is not None else 0,
                treasure_max=1 if amount and governor is not None else 0,
                gold_rewards=intervals,
                treasure_reward=dict(amount=1, gain=treasure_gain, loyalty=target.loyalty + treasure_gain)
                    if amount and governor is not None else None))
        chances = {str(i): max(15, min(80, 20 + state.officers[i].profile.intellect // 3
                                       + state.officers[i].profile.virtue // 5)) for i in actors}
        maximum = min(amount, max(0, (LIMIT - city.gold) // RULES['sell_gold_per_treasure']))
        result['cities'][key] = dict(owner=city.owner, treasure=amount, governor=governor,
            governor_mode=saved['governor_mode'], governor_candidates=candidates, eligible_actors=actors,
            can_manage=_ready(state, city.owner), search_fee=RULES['search_gold'], search_chances=chances,
            can_search=ready and command_books.can_spend(state,city.owner,'search_treasure') and bool(actors) and city.gold >= RULES['search_gold'] and amount < 99,
            can_sell=ready and command_books.can_spend(state,city.owner,'sell_treasure') and bool(actors) and maximum > 0, sell_max=maximum,
            can_reward=ready and command_books.can_spend(state,city.owner,'reward_officer') and actor_ready and bool(targets) and bool(gold_max or amount),
            reward_targets=targets)
    return result


def validate(game, state):
    pool = _pool(state)
    owners = set(game.catalog.factions) - {'neutral'}
    if not isinstance(pool, dict) or set(pool) != _FIELDS or pool['schema'] != SCHEMA:
        raise ValueError('Treasury schema')
    if not isinstance(pool['cities'], dict) or set(pool['cities']) != set(state.cities):
        raise ValueError('Treasury city domain')
    if not isinstance(pool['factions'], dict) or set(pool['factions']) != owners:
        raise ValueError('Treasury faction domain')
    for policy in pool['factions'].values():
        _validate_policy(policy)
    if not isinstance(pool['auto_turns'], dict) or set(pool['auto_turns']) != owners:
        raise ValueError('Treasury turn domain')
    if any(not _int(turn, 0, state.turn) for turn in pool['auto_turns'].values()):
        raise ValueError('Treasury automatic receipt')
    ledger = pool['ledger']
    if (not isinstance(ledger, dict) or set(ledger) != _LEDGER_FIELDS
            or any(not _int(value, 0, LIMIT) for value in ledger.values())):
        raise ValueError('Treasury asset ledger')
    for key, city in state.cities.items():
        row = pool['cities'][key]
        if (not isinstance(row, dict) or set(row) != _CITY_FIELDS or row['owner'] != city.owner
                or not _int(row['treasure'], 0, 99) or row['governor_mode'] not in ('auto', 'manual')):
            raise ValueError('Treasury city fields')
        if row['governor'] is not None:
            parse_officer_ref(row['governor'], game.catalog.rules)
        if row['governor'] != _governor(game, state, city, row):
            raise ValueError('Treasury governor availability')
        if row['governor_mode'] == 'manual' and row['governor'] is None:
            raise ValueError('Treasury manual governor')
    cargo_amounts = [convoy.get('cargo', {}).get('treasure', 0)
        for convoy in state.extension.get('logistics', {}).get('convoys', [])]
    if any(not _int(amount, 0, 99) for amount in cargo_amounts):
        raise ValueError('Treasury convoy assets')
    cargo = sum(cargo_amounts)
    present = sum(row['treasure'] for row in pool['cities'].values()) + cargo
    if present + ledger['spent'] + ledger['sold'] + ledger['lost'] != ledger['initial'] + ledger['found']:
        raise ValueError('Treasure conservation')
