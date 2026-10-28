"""City services and disaster preparation shared by players and AI.

Facility access follows the town's actual development.  All previews are pure;
only committed services and a once-per-month disaster settlement sample RNG.
Unverified balance parameters remain explicit, replaceable rules.
"""
from copy import deepcopy
from dataclasses import replace

from .errors import GameError
from . import command_books
from .officers import parse_officer_ref, deserialize_officer_ref, ref_sort_key, is_generated_ref
from .city_economy import tier_at

SCHEMA = 'tk2-facilities-v1'
LIMIT = 100000000
RULES = dict(town_cap=3, preparedness_cap=99, damage_cap=50,
    initial_preparedness=40, development_per_level_gold=100, medical_gold=50,
    medical_heal_min=35, medical_heal_max=45, study_cap=89,
    study_bands=[[30,30,5,9],[60,20,8,12],[79,10,6,10]],
    prevention_cost_bands=[[50,10,13],[80,13,16],[99,16,19]],
    prevention_effect_min=6, prevention_effect_max=10,
    market_buy_rates={'1':11,'2':10,'3':9}, market_sell_rates={'1':7,'2':8,'3':9},
    trade_batch_grain=100, trade_max_batches=1000,
    flood_months=[5, 6], drought_months=[8, 9], flood_plain_chance=12,
    flood_mountain_chance=6, drought_chance=12, disaster_base_rate=10,
    disasters_enabled=True)
DEFAULT_POLICY = dict(enabled=False, gold_budget=200, gold_floor=100,
    grain_floor=200, grain_target=2000, target_preparedness=70, heal_below=60,
    auto_prevent=True, auto_treat=True, auto_develop=False, auto_study=False,
    auto_trade=False, auto_equip=False)
_FIELDS = {'schema', 'cities', 'factions', 'study', 'last_disaster_month', 'auto_turns'}
_CITY_FIELDS = {'owner', 'town', 'preparedness', 'damage'}
_BOOL_POLICY = {'enabled', 'auto_prevent', 'auto_treat', 'auto_develop',
                'auto_study', 'auto_trade', 'auto_equip'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _month(state):
    return state.year * 12 + state.month - 1


def _pool(state):
    return state.extension['facilities']


def _rule(game, key):
    return game.catalog.data.get('facility_rules', {}).get(key, RULES[key])


def _validate_rules(game):
    override=game.catalog.data.get('facility_rules',{})
    if not isinstance(override,dict) or set(override)-set(RULES):
        raise ValueError('Facilities rule fields')
    rules=dict(RULES,**override)
    if type(rules['disasters_enabled']) is not bool:
        raise ValueError('Facilities disaster switch')
    for key,low,high in (('initial_preparedness',0,99),('development_per_level_gold',1,LIMIT),
            ('medical_gold',1,LIMIT),('medical_heal_min',1,99),('medical_heal_max',1,99),
            ('prevention_effect_min',1,100),('prevention_effect_max',1,100),
            ('trade_batch_grain',1,LIMIT),('trade_max_batches',1,1000000),
            ('flood_plain_chance',0,100),('flood_mountain_chance',0,100),
            ('drought_chance',0,100),('disaster_base_rate',0,100)):
        if not _int(rules[key],low,high):
            raise ValueError('Facilities numeric rule')
    for key,value in (('town_cap',3),('preparedness_cap',99),('damage_cap',50),('study_cap',89),
            ('trade_batch_grain',100),('trade_max_batches',1000)):
        if type(rules[key]) is not int or rules[key]!=value:
            raise ValueError('Facilities fixed rule boundary')
    if (rules['medical_heal_min']>rules['medical_heal_max']
            or rules['prevention_effect_min']>rules['prevention_effect_max']):
        raise ValueError('Facilities reversed random range')
    for key in ('flood_months','drought_months'):
        values=rules[key]
        if (not isinstance(values,list) or any(not _int(month,1,12) for month in values)
                or len(set(values))!=len(values)):
            raise ValueError('Facilities disaster months')
    if set(rules['flood_months'])&set(rules['drought_months']):
        raise ValueError('Facilities ambiguous disaster month')
    for key,thresholds,width in (('study_bands',[30,60,79],4),('prevention_cost_bands',[50,80,99],3)):
        bands=rules[key]
        if not isinstance(bands,list) or len(bands)!=3:
            raise ValueError('Facilities service bands')
        for row,threshold in zip(bands,thresholds):
            if (not isinstance(row,list) or len(row)!=width
                    or any(not _int(value,1,LIMIT) for value in row) or row[0]!=threshold
                    or (width==4 and not 1<=row[2]<=row[3]<=99)
                    or (width==3 and not 1<=row[1]<=row[2]<=100)):
                raise ValueError('Facilities invalid service band')
    if rules['study_bands']!=RULES['study_bands']:
        raise ValueError('Facilities fixed study bands')
    for key in ('market_buy_rates','market_sell_rates'):
        rates=rules[key]
        if (not isinstance(rates,dict) or set(rates)!={'1','2','3'}
                or any(not _int(value,1,100) for value in rates.values())):
            raise ValueError('Facilities market rates')
    if max(rules['market_sell_rates'].values())>min(rules['market_buy_rates'].values()):
        raise ValueError('Facilities unsupported arbitrage rates')
    regions=game.catalog.data.get('facility_disaster_cities',{})
    if not isinstance(regions,dict) or set(regions)-{'flood','drought'}:
        raise ValueError('Facilities disaster region fields')
    for values in regions.values():
        if (not isinstance(values,list) or any(not isinstance(value,str) or value not in game.catalog.map_cities for value in values)
                or len(set(values))!=len(values)):
            raise ValueError('Facilities disaster region identities')


def _new_city(city, town=1, preparedness=None):
    return dict(owner=city.owner, town=town,
        preparedness=RULES['initial_preparedness'] if preparedness is None else preparedness, damage=0)


def empty(game, state):
    return dict(schema=SCHEMA,
        cities={key: _new_city(city, {'normal': 1, 'large': 2, 'giant': 3}[
            tier_at(game.catalog.data, key, state.year, state.month)],_rule(game,'initial_preparedness'))
            for key, city in state.cities.items()},
        factions={owner: deepcopy(DEFAULT_POLICY) for owner in sorted(game.catalog.factions) if owner != 'neutral'},
        study={}, last_disaster_month=_month(state),
        auto_turns={owner: 0 for owner in sorted(game.catalog.factions) if owner != 'neutral'})


def synchronize(game, state):
    """Keep actual construction across conquests, without doing work or draws."""
    for key, city in state.cities.items():
        row = _pool(state)['cities'].setdefault(key, _new_city(city,preparedness=_rule(game,'initial_preparedness')))
        row['owner'] = city.owner


def learned_profile(state, ident, base):
    bonus = state.extension.get('facilities', {}).get('study', {}).get(str(ident), 0)
    if not bonus:
        return base
    basis=deepcopy(base.basis)
    basis['intellect']='source_initial_plus_campaign_school_learning'
    return replace(base, intellect=base.intellect + bonus,
        basis=basis, source_stats=deepcopy(base.source_stats))


def _base_profile(game, state, ident):
    if is_generated_ref(ident):
        from .civil_staff import officer_profile
        return officer_profile(state.extension['civil_staff']['people'][ident])
    return game.catalog.profiles[ident]


def _battle_ids(state):
    return {unit['id'] for side in ('attackers', 'defenders')
        for unit in (state.battle or {}).get(side, [])}


def _resident(game, state, city, ident, *, working=False, unused=False, healthy=False):
    officer = state.officers.get(ident)
    return bool(officer is not None and ident in city.roster.officer_ids
        and officer.alive and city.owner != 'neutral' and officer.faction_id == city.owner
        and (not healthy or officer.health > 0) and ident not in game._march_ids(state)
        and ident not in _battle_ids(state)
        and (not working or state.extension.get('civil_staff', {}).get('people', {}).get(ident, {}).get('working', True)))


def _ready(state, owner):
    return bool(owner != 'neutral' and owner not in state.extension.get('ended_factions', [])
        and not state.extension.get('pending_succession', {}).get(owner)
        and state.phase == ('city' if owner == state.player else 'ai'))


def _city(game, state, key, owner, *, action=True, service=None, kind=1):
    if (not _ready(state, owner) or not isinstance(key, str) or key not in state.cities
            or state.cities[key].owner != owner):
        raise GameError('目前不能操作這座城的設施。')
    city = state.cities[key]
    if action:
        command_books.require(state, owner, kind)
    if service in ('school', 'armory') and _pool(state)['cities'][key]['town'] < 2:
        raise GameError('本城尚未開放這項設施，請先開發町。')
    return city


def _payload(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise GameError('設施操作參數無效。')


def _ref(game, value):
    try:
        return parse_officer_ref(value, game.catalog.rules)
    except (TypeError, ValueError) as error:
        raise GameError('請選擇有效的本城武將。') from error


def _actor(game, state, city, value):
    ident = _ref(game, value)
    if not _resident(game, state, city, ident, working=True, unused=True, healthy=True):
        raise GameError('請選擇本城健康、在場且可任職的執行武將。')
    return ident


def _target(game, state, city, value, *, study=False):
    ident = _ref(game, value)
    if not _resident(game, state, city, ident, working=study, unused=study, healthy=study):
        raise GameError('請選擇符合條件且在本城的目標武將。')
    return ident


def _charge(state, city, actor, gold, target=None, *, kind):
    if not _int(gold, 0, LIMIT) or city.gold < gold:
        raise GameError('本城金錢不足，操作未執行。')
    command_books.spend(state, city, kind)
    city.gold -= gold
    for ident in (actor, target):
        if ident is not None:
            state.extension['officer_actions'][str(ident)] = state.turn


def _emit(game, state, kind, city, people, details):
    game._emit_event(state, kind, city_ids=[city.id], factions=[city.owner],
        person_ids=[state.officers[ident].person_id for ident in dict.fromkeys(people)], details=details)


def develop(game, state, payload, owner):
    _payload(payload, {'city', 'actor'})
    city = _city(game, state, payload['city'], owner, kind='develop_town')
    actor = _actor(game, state, city, payload['actor'])
    row = _pool(state)['cities'][city.id]
    before = row['town']
    if before >= 3:
        raise GameError('本城町等級已達上限。')
    gold = _rule(game, 'development_per_level_gold') * (before + 1)
    _charge(state, city, actor, gold, kind='develop_town')
    row['town'] += 1
    details = dict(actor=state.officers[actor].person_id, from_town=before, to_town=row['town'], gold=gold)
    _emit(game, state, 'town_developed', city, [actor], details)
    return details


def treat(game, state, payload, owner):
    _payload(payload, {'city', 'actor', 'officer'})
    city = _city(game, state, payload['city'], owner, service='hospital', kind='treat_officer')
    actor = _actor(game, state, city, payload['actor'])
    target = _target(game, state, city, payload['officer'])
    officer = state.officers[target]
    if officer.health >= officer.profile.health_max:
        raise GameError('這名武將的體力已滿，無須治療。')
    gold = _rule(game, 'medical_gold')
    if city.gold < gold:
        raise GameError('本城金錢不足，操作未執行。')
    before = officer.health
    healing = _rule(game, 'medical_heal_min') + state.rng.next() % (
        _rule(game, 'medical_heal_max') - _rule(game, 'medical_heal_min') + 1)
    _charge(state, city, actor, gold, target, kind='treat_officer')
    officer.health = min(officer.profile.health_max, before + healing)
    details = dict(actor=state.officers[actor].person_id, target=officer.person_id,
        gold=gold, before=before, after=officer.health)
    _emit(game, state, 'officer_treated', city, [actor, target], details)
    return details


def _study_quote(game, state, officer):
    intellect = officer.profile.intellect
    band = next((row for row in _rule(game,'study_bands') if intellect<=row[0]),None)
    if band is None:
        return None
    _,gold,low,high=band
    bonus = _pool(state)['study'].get(str(officer.runtime_id), 0)
    return dict(id=officer.runtime_id, before=intellect, gain_min=low, gain_max=high,
        after_min=min(_rule(game,'study_cap'), intellect + low),
        after_max=min(_rule(game,'study_cap'), intellect + high), gold=gold, bonus=bonus)


def study(game, state, payload, owner):
    _payload(payload, {'city', 'actor', 'officer'})
    city = _city(game, state, payload['city'], owner, service='school', kind='study_officer')
    actor = _actor(game, state, city, payload['actor'])
    target = _target(game, state, city, payload['officer'], study=True)
    officer, quote = state.officers[target], _study_quote(game, state, state.officers[target])
    if quote is None:
        raise GameError('這名武將的知已達學問所修學上限。')
    if city.gold < quote['gold']:
        raise GameError('本城金錢不足，操作未執行。')
    after = min(_rule(game,'study_cap'), quote['before'] + quote['gain_min'] + state.rng.next() % (
        quote['gain_max'] - quote['gain_min'] + 1))
    _charge(state, city, actor, quote['gold'], target, kind='study_officer')
    bonus = quote['bonus'] + after - quote['before']
    _pool(state)['study'][str(target)] = bonus
    officer.profile = learned_profile(state,target,_base_profile(game,state,target))
    details = dict(actor=state.officers[actor].person_id, target=officer.person_id,
        gold=quote['gold'], before=quote['before'], after=after, bonus=bonus)
    _emit(game, state, 'officer_studied', city, [actor, target], details)
    return details


def _trade_quote(game, city, town, direction):
    rate = _rule(game,'market_buy_rates' if direction == 'buy' else 'market_sell_rates')[str(town)]
    batch,cap=_rule(game,'trade_batch_grain'),_rule(game,'trade_max_batches')
    maximum = (min(cap, city.gold // rate, (LIMIT - city.grain) // batch) if direction == 'buy'
        else min(cap, city.grain // batch, (LIMIT - city.gold) // rate))
    return dict(rate=rate, max_batches=max(0, maximum), batch_grain=batch)


def trade(game, state, payload, owner):
    _payload(payload, {'city', 'actor', 'direction', 'batches'})
    city = _city(game, state, payload['city'], owner, service='market', kind='trade_grain')
    actor = _actor(game, state, city, payload['actor'])
    direction, batches = payload['direction'], payload['batches']
    if direction not in ('buy', 'sell'):
        raise GameError('請選擇買入或賣出兵糧。')
    quote = _trade_quote(game, city, _pool(state)['cities'][city.id]['town'], direction)
    if not _int(batches, 1, quote['max_batches']):
        raise GameError('兵糧交易數量超出可用庫存或上限。')
    gold, grain = batches * quote['rate'], batches * quote['batch_grain']
    if direction == 'buy':
        _charge(state, city, actor, gold, kind='trade_grain')
        city.grain += grain
    else:
        _charge(state, city, actor, 0, kind='trade_grain')
        city.gold += gold
        city.grain -= grain
    details = dict(actor=state.officers[actor].person_id, direction=direction,
        batches=batches, grain=grain, gold=gold, rate=quote['rate'])
    _emit(game, state, 'grain_traded', city, [actor], details)
    return details


def _equipment():
    from . import equipment
    return equipment


def buy(game, state, payload, owner):
    _payload(payload, {'city', 'actor', 'officer', 'slot', 'item'})
    city = _city(game, state, payload['city'], owner, service='armory', kind='buy_equipment')
    actor = _actor(game, state, city, payload['actor'])
    target = _target(game, state, city, payload['officer'])
    slot, ident = payload['slot'], payload['item']
    if slot not in ('weapon', 'armor') or not _int(ident, 0, len(_equipment().WEAPONS)-1 if slot == 'weapon' else len(_equipment().ARMORS)-1):
        raise GameError('請選擇有效的武器或防具。')
    merchandise = _equipment().purchase_quote(game,state,city,target,slot,ident)
    officer, field = state.officers[target], slot + '_id'
    previous = getattr(officer, field)
    if previous == ident:
        raise GameError('這名武將已持有這件裝備。')
    _charge(state, city, actor, merchandise['price'], target, kind='buy_equipment')
    _equipment().claim_purchase(game,state,city,target,slot,ident)
    details = dict(actor=state.officers[actor].person_id, target=officer.person_id,
        slot=slot, item=ident, previous=previous, gold=merchandise['price'])
    _emit(game, state, 'equipment_bought', city, [actor, target], details)
    return details


def _prevention_quote(game, city, row, officer):
    intellect = officer.profile.intellect
    _,low,high=next(band for band in _rule(game,'prevention_cost_bands') if intellect<=band[0])
    gain_min = ((low * intellect // 100) * _rule(game,'prevention_effect_min')) // 10
    gain_max = ((high * intellect // 100) * _rule(game,'prevention_effect_max')) // 10
    repair_min = min(row['damage'], max(1, gain_min // 2))
    repair_max = min(row['damage'], max(1, gain_max // 2))
    return dict(gold_min=low, gold_max=high, gain_min=min(99-row['preparedness'], gain_min),
        gain_max=min(99-row['preparedness'], gain_max),
        preparedness_min=min(99, row['preparedness']+gain_min),
        preparedness_max=min(99, row['preparedness']+gain_max),
        damage_min=max(0, row['damage']-repair_max), damage_max=max(0, row['damage']-repair_min),
        can_prevent=city.gold >= high and (row['preparedness'] < 99 or row['damage'] > 0))


def prevent(game, state, payload, owner):
    _payload(payload, {'city', 'actor'})
    city = _city(game, state, payload['city'], owner, kind='improve_prevention')
    actor = _actor(game, state, city, payload['actor'])
    row = _pool(state)['cities'][city.id]
    quote = _prevention_quote(game, city, row, state.officers[actor])
    if row['preparedness'] == 99 and not row['damage']:
        raise GameError('本城防災已滿且沒有災損，無須整備。')
    if city.gold < quote['gold_max']:
        raise GameError('本城金錢不足以支付防災最高報價，操作未執行。')
    gold = quote['gold_min'] + state.rng.next() % (quote['gold_max']-quote['gold_min']+1)
    effect = _rule(game,'prevention_effect_min') + state.rng.next() % (
        _rule(game,'prevention_effect_max')-_rule(game,'prevention_effect_min')+1)
    raw_gain = ((gold * state.officers[actor].profile.intellect // 100) * effect) // 10
    before_p, before_d = row['preparedness'], row['damage']
    gain, repair = min(99-before_p, raw_gain), min(before_d, max(1, raw_gain//2))
    _charge(state, city, actor, gold, kind='improve_prevention')
    row.update(preparedness=before_p+gain, damage=before_d-repair)
    details = dict(actor=state.officers[actor].person_id, gold=gold, gain=gain, repair=repair,
        preparedness_before=before_p, preparedness_after=row['preparedness'],
        damage_before=before_d, damage_after=row['damage'])
    _emit(game, state, 'prevention_improved', city, [actor], details)
    return details


def _validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY):
        raise ValueError('Facility policy fields')
    if any(type(policy[key]) is not bool for key in _BOOL_POLICY):
        raise ValueError('Facility policy switches')
    for key, low, high in (('gold_budget', 0, 1000000), ('gold_floor', 0, LIMIT),
            ('grain_floor', 0, LIMIT), ('grain_target', 0, LIMIT), ('target_preparedness', 0, 99),
            ('heal_below', 1, 99)):
        if not _int(policy[key], low, high):
            raise ValueError('Facility policy limits')
    if policy['grain_target'] < policy['grain_floor']:
        raise ValueError('Facility target below reserve floor')


def set_policy(game, state, payload, owner):
    _payload(payload, {'faction', 'policy'})
    if (not _ready(state, owner) or payload['faction'] != owner
            or owner not in _pool(state)['factions'] or not isinstance(payload['policy'], dict)
            or set(payload['policy'])-set(DEFAULT_POLICY)):
        raise GameError('設施方針參數無效。')
    revised = dict(_pool(state)['factions'][owner], **payload['policy'])
    try:
        _validate_policy(revised)
    except (ValueError, TypeError) as error:
        raise GameError('設施方針超出允許範圍或目標低於保留量。') from error
    _pool(state)['factions'][owner] = revised


def adjusted_income(state, city_id, income):
    damage = state.extension.get('facilities', {}).get('cities', {}).get(city_id, {}).get('damage', 0)
    return {key: value * (100-damage) // 100 for key, value in income.items()}


def _disaster_band(preparedness):
    # Residual proportion of a separate base disaster, not the whole warehouse.
    if preparedness == 99:
        return 0, 10, 15
    if preparedness >= 80:
        return 20, 7, 12
    if preparedness >= 50:
        return 40, 5, 10
    if preparedness >= 20:
        return 60, 1, 5
    return (80, 0, 0) if preparedness else (100, 0, 0)


def month_rollover(game, state):
    pool, month = _pool(state), _month(state)
    if pool['last_disaster_month'] >= month:
        return []
    pool['last_disaster_month'] = month
    if not _rule(game, 'disasters_enabled'):
        return []
    kind = ('flood' if state.month in _rule(game, 'flood_months') else
            'drought' if state.month in _rule(game, 'drought_months') else None)
    if kind is None:
        return []
    configured = game.catalog.data.get('facility_disaster_cities', {})
    allowed = set(configured[kind]) if kind in configured else set(state.cities)
    results = []
    for key, city in sorted(state.cities.items()):
        if city.owner == 'neutral' or key not in allowed:
            continue
        terrain = game.catalog.map_cities[key].get('terrain', 'plain')
        chance = (_rule(game, 'flood_mountain_chance') if terrain == 'mountain'
            else _rule(game, 'flood_plain_chance')) if kind == 'flood' else _rule(game, 'drought_chance')
        if state.rng.next() % 100 >= chance:
            continue
        row = pool['cities'][key]
        before_p, before_d = row['preparedness'], row['damage']
        residual, low, high = _disaster_band(before_p)
        rate = _rule(game, 'disaster_base_rate') * residual // 100
        gold = city.gold * rate // 100 if kind == 'flood' else 0
        grain = city.grain * rate // 100
        reserves = city.reserves * rate // 100 if kind == 'drought' else 0
        drop = low + state.rng.next() % (high-low+1) if high else 0
        city.gold -= gold
        city.grain -= grain
        city.reserves -= reserves
        state.soldiers['lost'] += reserves
        row.update(preparedness=max(0, before_p-drop), damage=min(50, before_d+rate))
        details = dict(disaster=kind, gold=gold, grain=grain, reserves=reserves, rate=rate,
            preparedness_before=before_p, preparedness_after=row['preparedness'],
            damage_before=before_d, damage_after=row['damage'])
        _emit(game, state, 'city_disaster', city, [], details)
        results.append(dict(city=key, **details))
    return results


def auto_turn(game, state, owner):
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
            actors = [i for i in city.roster.officer_ids
                if _resident(game, state, city, i, working=True, unused=True, healthy=True)]
            if not actors:
                continue
            actor = min(actors, key=lambda i: (-state.officers[i].profile.intellect,
                -state.officers[i].profile.virtue, ref_sort_key(i)))
            row, available = pool['cities'][key], min(budget, max(0, city.gold-policy['gold_floor']))
            choice = None
            prevention = _prevention_quote(game, city, row, state.officers[actor])
            if (command_books.can_spend(state, owner, 'improve_prevention') and policy['auto_prevent'] and (row['damage'] or row['preparedness'] < policy['target_preparedness'])
                    and prevention['gold_max'] <= available
                    and (prevention['gain_max'] > 0 or row['damage'])):
                choice = (prevent, dict(city=key, actor=actor))
            patients = [i for i in city.roster.officer_ids if _resident(game, state, city, i)
                and state.officers[i].health < min(policy['heal_below'], state.officers[i].profile.health_max)]
            if choice is None and command_books.can_spend(state, owner, 'treat_officer') and policy['auto_treat'] and patients and _rule(game, 'medical_gold') <= available:
                patient = min(patients, key=lambda i: (state.officers[i].health, ref_sort_key(i)))
                choice = (treat, dict(city=key, actor=actor, officer=patient))
            if choice is None and command_books.can_spend(state, owner, 'trade_grain') and policy['auto_trade']:
                buy_quote, sell_quote = (_trade_quote(game, city, row['town'], direction) for direction in ('buy','sell'))
                batches = min(buy_quote['max_batches'], available // buy_quote['rate'],
                    max(0, policy['grain_target']-city.grain+buy_quote['batch_grain']-1)//buy_quote['batch_grain'])
                if city.grain < policy['grain_target'] and batches > 0:
                    choice = (trade, dict(city=key, actor=actor, direction='buy', batches=batches))
                elif city.gold < policy['gold_floor'] and city.grain > policy['grain_target']:
                    batches = min(sell_quote['max_batches'], (city.grain-policy['grain_target'])//sell_quote['batch_grain'],
                        (policy['gold_floor']-city.gold+sell_quote['rate']-1)//sell_quote['rate'])
                    if batches:
                        choice = (trade, dict(city=key, actor=actor, direction='sell', batches=batches))
            if choice is None and policy['auto_equip'] and row['town'] >= 2:
                people = sorted((i for i in city.roster.officer_ids if _resident(game,state,city,i)),
                    key=lambda i: (-state.officers[i].profile.martial_strength, ref_sort_key(i)))
                for target in people:
                    for slot in ('weapon','armor'):
                        current = _equipment().item(slot, getattr(state.officers[target], slot+'_id'))
                        officer = state.officers[target]
                        field = 'attack' if slot == 'weapon' else 'defense'
                        old_effect = _equipment().duel_adjustment(officer.weapon_id,officer.armor_id,
                            officer.profile.martial_strength)[field]
                        def effect(item):
                            return _equipment().duel_adjustment(
                                item['id'] if slot == 'weapon' else officer.weapon_id,
                                item['id'] if slot == 'armor' else officer.armor_id,
                                officer.profile.martial_strength)[field]
                        owned=[item for item in _equipment().owned_for(game,state,target)
                            if item['slot']==slot and effect(item)>old_effect]
                        if owned and command_books.can_spend(state, owner, 'equip_owned'):
                            item=min(owned,key=lambda item:(-effect(item),item['id']))
                            choice=(_equipment().equip_owned,dict(city=key,actor=actor,officer=target,slot=slot,item=item['id']))
                            break
                        offers = [item for item in _equipment().shop_stock(game,state,city,slot)
                            if 0 <= item['price'] <= available and item['id'] != current['id']
                            and target in item['eligible_targets'] and effect(item) > old_effect]
                        if offers and command_books.can_spend(state, owner, 'buy_equipment'):
                            item = min(offers,key=lambda item: (-effect(item),item['price'],item['id']))
                            choice = (buy, dict(city=key, actor=actor, officer=target, slot=slot, item=item['id']))
                            break
                    if choice:
                        break
            if choice is None and command_books.can_spend(state, owner, 'develop_town') and policy['auto_develop'] and row['town'] < 3:
                if _rule(game,'development_per_level_gold')*(row['town']+1) <= available:
                    choice = (develop, dict(city=key,actor=actor))
            if choice is None and command_books.can_spend(state, owner, 'study_officer') and policy['auto_study'] and row['town'] >= 2:
                students = [i for i in actors if (quote := _study_quote(game,state,state.officers[i])) is not None
                    and quote['gold'] <= available]
                if students:
                    target = min(students,key=lambda i:(state.officers[i].profile.intellect,ref_sort_key(i)))
                    choice = (study,dict(city=key,actor=actor,officer=target))
            if choice is not None:
                before = city.gold
                receipt = choice[0](game,state,choice[1],owner)
                budget -= max(0,before-city.gold)
                results.append(dict(city=key,**receipt))
        if len(results) == completed:
            break
    return results


def view(game, state):
    result = dict(schema=SCHEMA, rules=deepcopy(RULES), cities={}, factions={},
        equipment_catalog={slot:deepcopy(list(rows)) for slot,rows in
            (('weapon',_equipment().WEAPONS),('armor',_equipment().ARMORS))})
    if state is None:
        return result
    pool = _pool(state)
    result['rules'].update(deepcopy(game.catalog.data.get('facility_rules',{})))
    result['factions'] = {owner: dict(policy=deepcopy(policy)) for owner,policy in pool['factions'].items()}
    for key, city in state.cities.items():
        row = pool['cities'][key]
        residents = sorted((i for i in city.roster.officer_ids if _resident(game,state,city,i)),key=ref_sort_key)
        actors = [i for i in residents if _resident(game,state,city,i,working=True,unused=True,healthy=True)]
        ready = _ready(state,city.owner) and command_books.can_spend(state,city.owner) and bool(actors)
        patients = [dict(id=i,before=state.officers[i].health,
            heal_min=_rule(game,'medical_heal_min'),heal_max=_rule(game,'medical_heal_max'),
            after_min=min(state.officers[i].profile.health_max,state.officers[i].health+_rule(game,'medical_heal_min')),
            after_max=min(state.officers[i].profile.health_max,state.officers[i].health+_rule(game,'medical_heal_max')),
            gold=_rule(game,'medical_gold'),can_treat=ready and command_books.can_spend(state,city.owner,'treat_officer') and city.gold>=_rule(game,'medical_gold'))
            for i in residents if state.officers[i].health<state.officers[i].profile.health_max]
        students = []
        if row['town']>=2:
            for i in actors:
                quote=_study_quote(game,state,state.officers[i])
                if quote is not None:
                    students.append(dict(quote,can_study=ready and command_books.can_spend(state,city.owner,'study_officer') and city.gold>=quote['gold']))
        stock = {slot:[] for slot in ('weapon','armor')}
        if row['town']>=2 and city.owner==state.player:
            for slot in stock:
                for item in _equipment().shop_stock(game,state,city,slot):
                    targets=item['eligible_targets']
                    stock[slot].append(dict(item,eligible_targets=targets,
                        can_buy=ready and command_books.can_spend(state,city.owner,'buy_equipment') and bool(targets) and city.gold>=item['price']))
        development_gold=_rule(game,'development_per_level_gold')*(row['town']+1) if row['town']<3 else 0
        prevention={str(i):dict(_prevention_quote(game,city,row,state.officers[i]),
            can_prevent=ready and command_books.can_spend(state,city.owner,'improve_prevention') and _prevention_quote(game,city,row,state.officers[i])['can_prevent']) for i in actors}
        result['cities'][key]=dict(owner=city.owner,town=row['town'],preparedness=row['preparedness'],damage=row['damage'],
            services=['hospital','market']+(['school','armory'] if row['town']>=2 else []),
            can_manage=_ready(state,city.owner),can_act=ready,eligible_actors=actors,
            patients=patients,students=students,equipment_targets=residents,stock=stock,
            develop=dict(from_town=row['town'],to_town=min(3,row['town']+1),gold=development_gold,
                can_develop=ready and command_books.can_spend(state,city.owner,'develop_town') and row['town']<3 and city.gold>=development_gold),
            trade={direction:_trade_quote(game,city,row['town'],direction) for direction in ('buy','sell')},
            prevention_quotes=prevention)
    return result


def validate(game, state):
    _validate_rules(game)
    pool = _pool(state)
    if not isinstance(pool,dict) or set(pool)!=_FIELDS or pool['schema']!=SCHEMA:
        raise ValueError('Facilities schema')
    if not isinstance(pool['cities'],dict) or set(pool['cities'])!=set(state.cities):
        raise ValueError('Facilities city domain')
    owners=set(game.catalog.factions)-{'neutral'}
    if not isinstance(pool['factions'],dict) or set(pool['factions'])!=owners:
        raise ValueError('Facilities policy domain')
    for policy in pool['factions'].values():
        _validate_policy(policy)
    if not isinstance(pool['auto_turns'],dict) or set(pool['auto_turns'])!=owners:
        raise ValueError('Facilities automatic receipt domain')
    if any(not _int(turn,0,state.turn) for turn in pool['auto_turns'].values()):
        raise ValueError('Facilities automatic receipt')
    if not _int(pool['last_disaster_month'],game.catalog.data.get('start_year',state.year)*12+
            game.catalog.data.get('start_month',state.month)-1,_month(state)):
        raise ValueError('Facilities monthly receipt')
    for key,city in state.cities.items():
        row=pool['cities'][key]
        if (not isinstance(row,dict) or set(row)!=_CITY_FIELDS or row['owner']!=city.owner
                or not _int(row['town'],1,3) or not _int(row['preparedness'],0,99) or not _int(row['damage'],0,50)):
            raise ValueError('Facilities city fields')
    if not isinstance(pool['study'],dict) or len(pool['study'])>len(state.officers):
        raise ValueError('Facilities study domain')
    for key,bonus in pool['study'].items():
        ident=deserialize_officer_ref(key,game.catalog.rules)
        if ident not in state.officers or not _int(bonus,1,89):
            raise ValueError('Facilities study reference')
        base=_base_profile(game,state,ident)
        if base.intellect>=80 or bonus>89-base.intellect or state.officers[ident].profile!=learned_profile(state,ident,base):
            raise ValueError('Facilities learned profile')
