"""Native battlefield villages backed by real campaign resources.

Manual pp34-35 identifies rice shops, weapon shops and hospitals. Coordinates
come from the recovered per-map table. Exact prices/healing use the remake's
existing facility tables; entering a village pays ordinary terrain movement,
and service use never spends a strategic command book.
"""
from .errors import GameError
from . import battle_grid, equipment, facilities
from .officers import parse_officer_ref

LIMIT = 100000000
ACTIONS = {'hospital': 'treat', 'market': 'buy_grain', 'armory': 'buy_equipment'}


def _site(battle, actor):
    row = battle['extended'].get('tactical')
    if row is None:
        return None
    point = row['positions'][str(actor['id'])]
    return next((site for site in battle_grid._field(battle).get('services', ())
                 if site['x'] == point['x'] and site['y'] == point['y']), None)


def _payer(state, battle, side):
    return state.cities[battle['source' if side == 'attackers' else 'target']]


def _town(state, battle):
    return max(2, state.extension.get('facilities', {}).get('cities', {}).get(battle['target'], {}).get('town', 2))


def _stock(state, battle, officer):
    result = {}
    reserve = state.extension.get('equipment', {}).get('reserves', {}).get(officer.person_id, {})
    for slot in ('weapon', 'armor'):
        result[slot] = [dict(row, eligible=getattr(officer, slot+'_id') != row['id']
                       and row['id'] not in reserve.get(slot, []))
                       for row in equipment.stock(_town(state, battle), slot)]
    return result


def quote(game, state, battle, actor, side, *, site=None):
    site = _site(battle, actor) if site is None else site
    if site is None:
        return None
    payer, officer = _payer(state, battle, side), state.officers[actor['id']]
    hp = battle['extended']['support'][str(actor['id'])]['health']
    result = dict(site, payer_city=payer.id, gold=payer.gold, grain=payer.grain,
        health=hp, max_health=officer.profile.health_max, actions=[ACTIONS[site['kind']]],
        stock={'weapon': [], 'armor': []}, trade=None,
        medical_gold=facilities._rule(game, 'medical_gold'))
    if site['kind'] == 'market':
        rate = facilities._rule(game, 'market_buy_rates')[str(_town(state,battle))]
        batch = facilities._rule(game, 'trade_batch_grain')
        result['trade'] = dict(rate=rate, batch_grain=batch,
            max_batches=max(0,min(facilities._rule(game,'trade_max_batches'),payer.gold//rate,(LIMIT-payer.grain)//batch)))
    if site['kind'] == 'armory':
        result['stock'] = _stock(state,battle,officer)
    return result


def execute(game, state, payload, *, side=None):
    battle = state.battle
    if (state.phase != 'battle' or not battle or payload.get('battle_id') != battle['id']
            or battle['extended']['duel'] or battle['extended'].get('siege')):
        raise GameError('目前不能使用戰場設施。')
    try:
        ident = parse_officer_ref(payload.get('actor'),game.catalog.rules)
    except (ValueError,TypeError):
        raise GameError('請選擇有效的戰場武將。') from None
    own, actor = battle_grid._unit(battle, ident)
    player = 'attackers' if battle['attacker'] == state.player else 'defenders'
    expected = player if side is None else side
    reason = battle_grid._action_reason(battle, actor, expected)
    if reason:
        raise GameError(reason)
    offer = quote(game,state,battle,actor,own)
    action = payload.get('action')
    if offer is None or action not in offer['actions']:
        raise GameError('請先移動至對應的戰場村落。')
    extra = {'batches'} if action == 'buy_grain' else {'slot','item'} if action == 'buy_equipment' else set()
    if set(payload) != {'battle_id','actor','action'} | extra:
        raise GameError('戰場設施操作參數無效。')
    payer, officer = _payer(state,battle,own), state.officers[ident]
    people = [officer.person_id]
    if action == 'treat':
        hp = battle['extended']['support'][str(ident)]
        if hp['health'] >= officer.profile.health_max:
            raise GameError('這名武將的體力已滿，無須治療。')
        gold = offer['medical_gold']
        if payer.gold < gold:
            raise GameError('本軍資金不足，操作未執行。')
        before = hp['health']
        healed = facilities._rule(game,'medical_heal_min') + state.rng.next() % (
            facilities._rule(game,'medical_heal_max')-facilities._rule(game,'medical_heal_min')+1)
        hp['health'] = min(officer.profile.health_max,before+healed)
        officer.health = max(officer.health,hp['health'])
        payer.gold -= gold
        kind = 'officer_treated'
        details = dict(actor=officer.person_id,target=officer.person_id,gold=gold,before=before,after=hp['health'])
    elif action == 'buy_grain':
        batches, trade = payload['batches'], offer['trade']
        if type(batches) is not int or not 1 <= batches <= trade['max_batches']:
            raise GameError('兵糧交易數量超出可用金錢或上限。')
        gold, grain = batches*trade['rate'], batches*trade['batch_grain']
        payer.gold -= gold; payer.grain += grain
        kind = 'grain_traded'
        details = dict(actor=officer.person_id,direction='buy',batches=batches,grain=grain,gold=gold,rate=trade['rate'])
    else:
        slot, item = payload['slot'], payload['item']
        if not isinstance(slot,str) or slot not in ('weapon','armor') or type(item) is not int:
            raise GameError('請選擇有效的武器或防具。')
        merchandise = next((row for row in offer['stock'].get(slot, []) if type(item) is int and row['id']==item and row['eligible']),None)
        if merchandise is None:
            raise GameError('這間戰場武器屋沒有可購買的這件裝備。')
        if payer.gold < merchandise['price']:
            raise GameError('本軍資金不足，操作未執行。')
        previous = equipment._give(state,officer,slot,item,'purchase')
        payer.gold -= merchandise['price']
        kind = 'equipment_bought'
        details = dict(actor=officer.person_id,target=officer.person_id,slot=slot,item=item,previous=previous,gold=merchandise['price'])
    battle['log'].append(f'{game.person_name(state,ident)}使用戰場設施，花費資金{details["gold"]}。')
    battle['log'][:] = battle['log'][-80:]
    game._emit_event(state,kind,city_ids=[payer.id],factions=[payer.owner],person_ids=people,details=details)
    return details


def ai_action(game, state, battle, actor, side, *, site=None):
    offer = quote(game,state,battle,actor,side,site=site)
    if not offer:
        return None
    base = dict(kind='facility',actor=actor['id'],target=actor['id'],tactic=None,
                battle_id=battle['id'])
    if offer['kind']=='hospital' and offer['health']<offer['max_health'] and offer['gold']>=offer['medical_gold']:
        return dict(base,action='treat',score=(offer['max_health']-offer['health'])*4+40)
    if offer['kind']=='market' and offer['grain']<500 and offer['trade']['max_batches']:
        batches=min(offer['trade']['max_batches'],(500-offer['grain']+99)//100)
        return dict(base,action='buy_grain',batches=batches,score=40)
    if offer['kind']=='armory':
        officer = state.officers[actor['id']]
        candidates = [(row['power']-equipment.item(slot,getattr(officer,slot+'_id'))['power'],slot,row)
            for slot, rows in offer['stock'].items() for row in rows if row['eligible'] and row['price']<=offer['gold']]
        if candidates:
            gain,slot,row=max(candidates,key=lambda item:(item[0],-item[2]['price'],-item[2]['id']))
            if gain>0:
                return dict(base,action='buy_equipment',slot=slot,item=row['id'],score=20+gain*4)
    return None


def seek(game,state,battle,actor,side):
    """Pure service destinations, with the same real prices and item limits.

    A hurt commander may seek a hospital; a rice or equipment stop is only
    offered while the actual balance/stock would improve. Reaching the village
    never promises payment: the next turn checks the same quote again.
    """
    result=[]
    hp=battle['extended']['support'][str(actor['id'])]['health']
    maximum=state.officers[actor['id']].profile.health_max
    current=_site(battle,actor)
    for site in battle_grid._field(battle).get('services',()):
        if site==current or (site['kind']=='hospital' and hp>max(30,maximum*2//3)):
            continue
        action=ai_action(game,state,battle,actor,side,site=site)
        if action:
            result.append(dict(site,score=action['score']))
    return result
