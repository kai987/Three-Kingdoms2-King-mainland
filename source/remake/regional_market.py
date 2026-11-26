"""Market orders reference actual city purchases and physical transport receipts."""
from collections import Counter, defaultdict

from . import (city_economy, command_books, economic_regions, facilities, grain_market,
               logistics, logistics_rules, market_pricing as pricing, observer, staging_supply)
from .errors import GameError
from .regional_procurement import BASE, Planner, landed_cents, quota_left

COMMAND = 'regional_market_order'
KEEP_COMPLETED = 96
NO_OFFER = '目前沒有符合資金、庫存及路權的區域糧運方案。'
INVALID_ORDER = '區域市場指令無效。'
ACTIVE_ORDER = '這批糧食已有進行中的區域訂單。'
CLOSED = {'delivered','sold','failed','received_elsewhere','returned','expired','cancelled'}
PENDING = {'dispatched','awaiting_sale'}
PURPOSES = {'procurement','trade'}


def _orders(state):
    return pricing.pool(state)['orders']


def _order(state, convoy):
    return _orders(state)[str(convoy['regional']['id'])]


def _report(state, kind, item, **details):
    if pricing.observed():
        pricing.report(kind,state,order_id=item['id'],owner=item['owner'],source=item['source'],
            target=item['target'],purpose=item['purpose'],automatic=item['auto'],status=item['status'],
            convoy=item['convoy'],**details)


def _use_quota(state, city, direction, amount):
    ledger=pricing.pool(state)
    used=ledger['quotas'].setdefault(city, {})
    used[direction]=used.get(direction,0)+amount


def conflicts(state, quote):
    for item in _orders(state).values():
        if item['owner']!=quote['owner'] or item['purpose']!=quote['purpose']:
            continue
        same=item['source']==quote['source'] and item['target']==quote['target']
        if same and (item['status'] in PENDING or item['created']==state.turn):
            return True
        if quote['purpose']=='trade' and item['created']>=state.turn-2 and (
                item['source'],item['target'])==(quote['target'],quote['source']):
            return True
    return False


def start(game, state, order, *, automatic=False):
    """Buy at the source and attempt to dispatch using independently paid orders."""
    source=state.cities[order['source']]
    kind=order['purpose']
    if conflicts(state,order):
        raise GameError(ACTIVE_ORDER)
    if automatic and kind=='trade' and order['cargo']>quota_left(state,source.id,'buy'):
        raise GameError(pricing.STALE_QUOTE)
    city=facilities._city(game,state,source.id,order['owner'],service='market',kind='trade_grain')
    actor=facilities._actor(game,state,city,order['actor'])
    offer=facilities.emergency_quote(game,state,city,order['cargo'])
    if (offer['grain']!=order['cargo'] or offer['gold']!=order['gold']
            or offer['rate']!=order['rate'] or offer['grain']<=0):
        raise GameError(pricing.STALE_QUOTE)
    command_books.require(state,city.owner,2)
    ledger=pricing.pool(state)
    ident=ledger['next_id']
    if ident>1_000_000:
        raise GameError('區域市場訂單已達上限。')
    item=dict(id=ident,owner=city.owner,source=city.id,target=order['target'],actor=actor,purpose=kind,
        auto=automatic,status='purchased',created=state.turn,purchased=offer['grain'],purchase_rate=offer['rate'],
        purchase_gold=offer['gold'],estimated_net=order['net'],quoted_arrival=order['arrival_turn'],
        landed_cents=order['landed_cents'],quoted_rations=order['escort_rations'],
        reference_price=order['reference_price'],convoy=None,delivered=0,delivered_turn=None,
        sold=0,sale_gold=0,sale_rate=None,sale_turn=None,closed=None,
        destination=None,returned_cargo=0,actual_extra_rations=None,rations_used=None,
        expiry=order['arrival_turn']+9,reason=None)
    facilities._settle_grain_trade(game,state,city,actor,'buy',offer['batches'],offer['grain'],
        offer['gold'],offer['rate'],emergency=offer['grain']%BASE!=0,channel=f'regional_{kind}')
    ledger['next_id']+=1
    _orders(state)[str(ident)]=item
    if automatic and kind=='trade':
        _use_quota(state,city.id,'buy',offer['grain'])
    _report(state,'regional_purchase',item,grain=offer['grain'],gold=offer['gold'],
            rate=offer['rate'],estimated_net=order['net'],landed_cents=order['landed_cents'],
            estimated_days=order['days'],route=order['route'],route_types=order['route_types'],
            expected_rations=order['expected_rations'],reserved_rations=order['escort_rations'],
            estimated_loss=order['estimated_loss'],deadline=order['deadline'],reference_price=item['reference_price'],
            return_days=order['return_days'],return_route=order['return_route'],return_rations=order['return_rations'],
            source_stock=order['source_stock'],source_market_capacity=order['source_market_capacity'],
            transport_capacity=order['transport_capacity'])
    try:
        convoy=logistics.dispatch(game,state,dict(source=source.id,target=order['target'],officers=[actor],
                    cargo=dict(gold=0,grain=offer['grain'],reserves=0),route_mode=order['route_mode']),
                    order['owner'],emergency_grain=order['escort_rations'],regional_order=ident)
    except GameError as error:
        # The purchase was an actual exchange. The now-uncommitted grain
        # stays in this warehouse and the trader has spent only its own book.
        item.update(status='failed',reason=str(error))
        _report(state,'regional_dispatch_failed',item,grain_retained=offer['grain'],reason=str(error))
    else:
        item.update(convoy=convoy['id'],status='dispatched')
        journey=convoy['journeys'][0]
        _report(state,'regional_dispatch',item,grain=convoy['initial_cargo']['grain'],
                route=journey['quote']['path'],rations=journey['supply']['loaded'],
                estimated_arrival=journey['arrival_turn'])
    return item


def unloaded(state, convoy, target, grain):
    item=_order(state,convoy)
    if item['status']!='dispatched' or item['target']!=target.id or target.owner!=item['owner']:
        raise ValueError('Regional order delivery mismatch')
    item.update(delivered=grain,delivered_turn=state.turn,destination=target.id,
                status='awaiting_sale' if grain and item['purpose']=='trade' and state.turn<=item['expiry']
                else 'delivered' if item['purpose']=='procurement' else 'expired')
    _report(state,'regional_delivery',item,grain=grain,position=target.id,
            actual_route=convoy['journeys'][-1]['quote']['path'])


def track_cargo(row, kind, before, after):
    """Keep the purchased portion labelled through real cargo/bag transfers."""
    tagged=row['regional']
    if kind=='bag_return':
        tagged['cargo']+=tagged['bag']
        tagged['bag']=0
    elif kind=='rations':
        taken=max(0,before-after-(before-tagged['cargo']))
        tagged['cargo']-=taken
        tagged['bag']+=taken
    elif after<before:
        tagged['cargo']=tagged['cargo']*after//before


def track_meals(row, remaining):
    tagged=row['regional']
    spent=max(0,tagged['bag']-remaining)
    tagged['consumed']+=spent
    tagged['bag']-=spent


def transport_closed(state, convoy, outcome, city):
    item=_order(state,convoy)
    if item['closed'] is not None:
        raise ValueError('Duplicate regional transport closure')
    received=outcome in ('returned_home','received_elsewhere','surrender_settlement')
    receipts=logistics.grain_receipt(convoy,returned=received,
                                    abandoned=outcome=='no_friendly_city')
    meals=sum(journey['supply']['consumed'] for journey in convoy['journeys'])
    item.update(closed=state.turn,rations_used=meals,
        actual_extra_rations=meals-convoy['regional']['consumed'])
    if item['delivered_turn'] is None:
        item.update(status='returned' if outcome=='returned_home' else
                    'received_elsewhere' if received else 'failed',
                    destination=city,returned_cargo=receipts['cargo_returned'])
    _report(state,'regional_transport_closed',item,actual_city=city,close_reason=outcome,
            rations_used=meals,extra_rations=item['actual_extra_rations'],**receipts)


def forecasts(game,state,owner):
    from . import grain_relief
    return grain_relief.forecasts(game,state,owner,turns=grain_relief.RECOVERY_TURNS)


def sale_quote(game,state,item,*,automatic=False,forecast=None):
    if item['status']!='awaiting_sale' or item['purpose']!='trade':
        return None
    target=state.cities[item['target']]
    if (target.owner!=item['owner'] or not facilities._ready(state,item['owner'])
            or state.turn>item['expiry'] or not command_books.can_spend(state,item['owner'],'trade_grain')):
        return None
    if automatic and forecast is not None and forecast.zero_in is not None:
        return None
    quote=facilities._trade_quote(game,state,target,city_economy.town_level(game,state,target.id),'sell')
    grain=min(min(item['delivered'],item['purchased'])-item['sold'],quote['max_batches']*quote['batch_grain'],
              staging_supply.available(state,target)-(max(forecast.monthly,forecast.reserve)
               if automatic and forecast is not None else 0))
    if automatic:
        grain=min(grain,quota_left(state,target.id,'sell'))
    batches=max(0,grain//quote['batch_grain'])
    return dict(quote,grain=batches*quote['batch_grain'],gold=batches*quote['rate'],batches=batches)


def _sell(game,state,item,actor,offer):
    target=facilities._city(game,state,item['target'],item['owner'],service='market',kind='trade_grain')
    actor=facilities._actor(game,state,target,actor)
    receipt=facilities._settle_grain_trade(game,state,target,actor,'sell',offer['batches'],
        offer['grain'],offer['gold'],offer['rate'],channel='regional_trade')
    item.update(status='sold',sold=receipt['grain'],sale_gold=receipt['gold'],
                sale_rate=receipt['rate'],sale_turn=state.turn)
    if item['auto']:
        _use_quota(state,target.id,'sell',receipt['grain'])
    _report(state,'regional_sale',item,grain=receipt['grain'],gold=receipt['gold'],rate=receipt['rate'],
            purchase_gold=item['purchase_gold'],cash_result=receipt['gold']-item['purchase_gold'],
            remaining_grain=item['delivered']-receipt['grain'])
    return item


def execute(game,state,payload,owner):
    if pricing.stage(state)<pricing.PROCUREMENT or not facilities._ready(state,owner):
        raise GameError(INVALID_ORDER)
    action=payload.get('action')
    if action=='buy':
        if (set(payload)!={'action','source','target','qty','purpose','token'}
                or not all(isinstance(payload[key],str) for key in ('source','target','purpose','token'))
                or not type(payload['qty']) is int or not 1<=payload['qty']<=logistics.LIMIT
                or payload['purpose'] not in PURPOSES or payload['target'] not in state.cities):
            raise GameError(INVALID_ORDER)
        target=state.cities[payload['target']]
        forecast=forecasts(game,state,owner).get(target.id)
        deadline=None if forecast is None or forecast.zero_in is None else forecast.zero_in*10
        quotes,_=Planner(game,state,owner).options(target,payload['qty'],source=payload['source'],
                                                    purpose=payload['purpose'],deadline=deadline)
        offer=next((q for q in quotes if q['token']==payload['token']),None)
        if offer is None:
            raise GameError(pricing.STALE_QUOTE)
        return start(game,state,offer)
    if action not in ('sell','cancel') or type(payload.get('order')) is not int:
        raise GameError(INVALID_ORDER)
    item=_orders(state).get(str(payload['order']))
    if item is None or item['owner']!=owner or item['status']!='awaiting_sale':
        raise GameError(INVALID_ORDER)
    if action=='cancel' and set(payload)=={'action','order'}:
        item['status']='cancelled'
        _report(state,'regional_sale_cancelled',item,grain_in_warehouse=item['delivered'])
        return item
    if set(payload)!={'action','order','actor','batches','token'} or action!='sell':
        raise GameError(INVALID_ORDER)
    offer=sale_quote(game,state,item,automatic=item['auto'])
    if offer is None or offer.get('price_token')!=payload['token']:
        raise GameError(pricing.STALE_QUOTE)
    batches=payload['batches']
    if type(batches) is not int or not 1<=batches<=offer['batches']:
        raise GameError(NO_OFFER)
    return _sell(game,state,item,payload['actor'],dict(offer,batches=batches,
        grain=batches*offer['batch_grain'],gold=batches*offer['rate']))


def maintain(state):
    if not pricing.stage(state):
        return
    orders=_orders(state)
    for item in orders.values():
        if item['status']=='awaiting_sale' and (
                state.cities[item['target']].owner!=item['owner'] or item['expiry']<state.turn):
            item['status']='expired'
            _report(state,'regional_sale_expired',item,grain_in_warehouse=item['delivered'])
    present={row['regional']['id'] for row in logistics._pool(state)['convoys'] if 'regional' in row}
    done=[key for key,item in orders.items() if item['status'] in CLOSED and item['id'] not in present]
    for key in sorted(done,key=int)[:-KEEP_COMPLETED]:
        del orders[key]


def procure(game,state,owner,plan):
    """After official supply and allied aid, before local emergency purchases."""
    if pricing.stage(state)<pricing.PROCUREMENT:
        return False
    keys=plan.shortages(state,within=9)
    if not keys or not command_books.can_spend(state,owner,2):
        return False
    reviews=pricing.pool(state)['reviews']
    if reviews.get(owner)==state.turn:
        return False
    reviews[owner]=state.turn
    planner=Planner(game,state,owner,decision=plan,automatic=True)
    attempts=[]
    for key in keys:
        target,row=state.cities[key],plan.cities[key]
        requested=min(row.monthly*2,sum(gap for _,gap in row.gaps))
        if requested<=0:
            continue
        local=facilities.emergency_quote(game,state,target,requested)
        if not plan.budgets[key]['market_affordable']:
            local=dict(local,grain=0)
        if row.zero_in<=1 and (local['grain']>=requested or
                local['grain'] and not command_books.can_spend(state,owner,3)):
            continue
        quotes,rejections=planner.options(target,requested,deadline=row.zero_in*10)
        best=None
        for q in quotes:
            eta=q['arrival_turn']-state.turn
            remaining=sum(gap for when,gap in row.gaps if when>eta)
            if conflicts(state,q) or not remaining:
                continue
            if local['grain']>=requested and (not q['timely'] or q['landed_cents']>=local['rate']*100):
                continue
            # Actual grants may be late for the first instalment. Retain
            # immediate local purchasing for that bill and fund later deficits.
            if not q['timely'] and min(q['net'],remaining)*2<q['expected_rations']:
                continue
            best=q
            break
        attempts.append(dict(target=key,required=requested,deadline=row.zero_in*10,local=local['grain'],
                             candidates=len(quotes),rejections=rejections,
                             source=None if best is None else best['source']))
        if best:
            pricing.report('regional_procurement_plan',state,owner=owner,attempts=attempts,work=dict(planner.work))
            start(game,state,best,automatic=True)
            return True
    pricing.report('regional_procurement_plan',state,owner=owner,attempts=attempts,work=dict(planner.work))
    return False


def automatic_trade(game,state,owner,shortages):
    if pricing.stage(state)!=pricing.TRADE:
        return
    if shortages or not command_books.can_spend(state,owner,2):
        pricing.report('regional_trade_gate',state,owner=owner,
            reason='food_recovery' if shortages else 'command_books')
        return
    pending=[item for item in _orders(state).values() if item['owner']==owner and item['auto']
             and item['status']=='awaiting_sale']
    holding=[city for city in state.cities.values() if city.owner==owner]
    shortage_prices=[pricing.snapshot(game,state,city.id)['sell'] for city in holding
                     if quota_left(state,city.id,'sell')>=BASE
                     and grain_market.row(state,city.id)['stock']<grain_market.row(state,city.id)['monthly_supply']]
    ceiling=max(shortage_prices,default=0)
    buy_possible=any(quota_left(state,city.id,'buy')>=BASE
        and pricing.snapshot(game,state,city.id)['buy']<ceiling
        for city in holding)
    if not (pending or buy_possible):
        pricing.report('regional_trade_gate',state,owner=owner,reason='no_price_spread')
        return
    from . import faction_economy
    plan=faction_economy.plan(game,state,owner)
    if plan.shortages(state,within=9):
        pricing.report('regional_trade_gate',state,owner=owner,reason='food_recovery')
        return
    safe={key for key,row in plan.budgets.items() if not row['threatened']}
    absent=game._march_ids(state) | facilities._battle_ids(state)
    for item in pending:
        if item['target'] not in safe:
            continue
        target=state.cities[item['target']]
        offer=sale_quote(game,state,item,automatic=True,forecast=plan.cities[target.id])
        if not offer or offer['gold']<=item['purchase_gold']:
            continue
        actors=[i for i in target.roster.officer_ids if i not in absent and state.officers[i].alive
                and state.officers[i].health>0 and state.officers[i].faction_id==owner
                and state.extension.get('civil_staff',{}).get('people',{}).get(i,{}).get('working',True)]
        if actors:
            _sell(game,state,item,min(actors,key=logistics._key),offer)
            return
    if not buy_possible or not command_books.can_spend(state,owner,3):
        pricing.report('regional_trade_gate',state,owner=owner,reason='sale_not_ready' if pending else 'command_books')
        return
    planner=Planner(game,state,owner,decision=plan,automatic=True)
    targets=sorted((state.cities[key] for key in safe),key=lambda c:(
        -pricing.snapshot(game,state,c.id)['sell'],c.id))
    for target in targets:
        supply=grain_market.row(state,target.id)
        if (quota_left(state,target.id,'sell')<BASE or supply['stock']>=supply['monthly_supply']
                or any(item['target']==target.id and item['purpose']=='trade' and item['status'] in PENDING
                       for item in _orders(state).values())):
            continue
        quotes,rejections=planner.options(target,None,purpose='trade')
        offer=next((q for q in quotes if q['source'] in safe and q['economic_result_milli']>0
                    and not conflicts(state,q)),None)
        pricing.report('regional_trade_plan',state,owner=owner,target=target.id,candidates=len(quotes),
            rejections=rejections,work=dict(planner.work),source=None if offer is None else offer['source'])
        if offer:
            start(game,state,offer,automatic=True)
            return


def preview(game,state,owner,target,qty,purpose,source=None):
    city=state.cities.get(target)
    if (pricing.stage(state)<pricing.PROCUREMENT or city is None or city.owner!=owner
            or purpose not in PURPOSES or type(qty) is not int or not 1<=qty<=logistics.LIMIT
            or source is not None and (source not in state.cities or state.cities[source].owner!=owner)):
        raise GameError(INVALID_ORDER)
    forecast=forecasts(game,state,owner).get(target)
    deadline=None if forecast is None or forecast.zero_in is None else forecast.zero_in*10
    rows,reasons=Planner(game,state,owner).options(city,qty,source=source,purpose=purpose,deadline=deadline)
    return dict(quotes=[q for q in rows if not conflicts(state,q)][:24],
                reasons=reasons,local=facilities.emergency_quote(game,state,city,qty),deadline=deadline)


def view(game,state):
    if not pricing.stage(state):
        return None
    cities={}
    regions=defaultdict(Counter)
    ledger=pricing.pool(state)
    month=pricing.month_key(state)
    for key,city in state.cities.items():
        if city.owner!=state.player and state.player!=observer.SEAT:
            continue
        market=grain_market.row(state,key)
        region=economic_regions.region(key)
        regional=regions[region]
        price=pricing.snapshot(game,state,key)
        history=[row for row in ledger['history'].get(key,()) if row[0]>=month-2]
        regional.update(stock=market['stock'],supply=market['monthly_supply'],cities=1,
            bought=market['purchased'],sold=market['sold'],empty=int(not market['stock']),
            severe=int(market['stock']*4<market['monthly_supply']),
            ample=int(market['stock']>=2*market['monthly_supply']),
            bought_three=market['purchased']+sum(row[1] for row in history),
            sold_three=market['sold']+sum(row[2] for row in history))
        cities[key]=dict(owner=city.owner,region=region,stock=market['stock'],
                         capacity=market['capacity'],**price)
    orders=[]
    for item in _orders(state).values():
        if state.player!=observer.SEAT and state.player!=item['owner']:
            continue
        quote=sale_quote(game,state,item) if not item['auto'] else None
        orders.append(dict(item,offer=quote,
            cash_result=item['sale_gold']-item['purchase_gold'],remaining_grain=max(0,item['delivered']-item['sold']),
            economic_result_milli=None if item['actual_extra_rations'] is None or item['status']!='sold' else
                (item['sale_gold']-item['purchase_gold'])*BASE-item['actual_extra_rations']*item['reference_price']))
    for item in orders:
        if item['status']=='dispatched':
            regions[economic_regions.region(item['target'])].update(inbound=item['estimated_net'])
    for convoy in logistics._pool(state)['convoys']:
        if ('regional' in convoy and not convoy['delivery_done']
                and (convoy['owner']==state.player or state.player==observer.SEAT)):
            regions[economic_regions.region(convoy['original_target'])].update(
                in_transit_commodity=convoy['regional']['cargo'])
    return dict(stage=pricing.stage(state),cities=cities,labels=economic_regions.REGIONS,orders=orders,
                regions=dict(regions),order_costs=dict(buy=2,sell=1,cancel=0),max_quantity=logistics.LIMIT)


def validate(game,state):
    own_convoys=[row for row in logistics._pool(state)['convoys'] if 'regional' in row]
    if not pricing.stage(state):
        if own_convoys:
            raise ValueError('Regional convoy requires market rules')
        return
    ledger=pricing.pool(state)
    orders=ledger['orders']
    checks=ledger['reviews']
    if (not isinstance(orders,dict) or len(orders)>KEEP_COMPLETED+3*len(state.cities)
            or type(ledger['next_id']) is not int or not 1<=ledger['next_id']<=1_000_001
            or not isinstance(checks,dict) or not checks.keys()<=game.catalog.factions.keys()
            or any(type(n) is not int or not 1<=n<=state.turn for n in checks.values())):
        raise ValueError('Regional order index')
    quotas=ledger['quotas']
    if not isinstance(quotas,dict) or not quotas.keys()<=state.cities.keys():
        raise ValueError('Regional commercial quota cities')
    for city,directions in quotas.items():
        if pricing.stage(state)!=pricing.TRADE or not isinstance(directions,dict) or not directions.keys()<={'buy','sell'}:
            raise ValueError('Regional commercial quota')
        if any(type(n) is not int or not 0<n<=grain_market.row(state,city)['monthly_supply']//4 for n in directions.values()):
            raise ValueError('Regional commercial quota limit')
    seen=set()
    for row in own_convoys:
        tag=row['regional']
        limit=logistics.LIMIT
        if (not isinstance(tag,dict) or set(tag)!={'id','cargo','bag','consumed'}
                or any(type(n) is not int or not 0<=n<=limit for n in tag.values())
                or tag['id'] in seen or str(tag['id']) not in orders
                or tag['cargo']>row['cargo']['grain'] or tag['bag']>row['journeys'][-1]['supply']['remaining']
                or tag['consumed']>sum(leg['supply']['consumed'] for leg in row['journeys'])):
            raise ValueError('Regional consignment allocation')
        item=orders[str(tag['id'])]
        if ((item['source'],item['target'],item['owner'],item['convoy'],item['purchased'],item['closed'])
                !=(row['source'],row['original_target'],row['owner'],row['id'],row['initial_cargo']['grain'],None)
                or row['target_march'] is not None or 'convoy_relief' in row
                or item['delivered']!=row['delivered']['grain']):
            raise ValueError('Regional consignment receipt')
        seen.add(tag['id'])
    numbers={'id','created','purchased','purchase_rate','purchase_gold','estimated_net','quoted_arrival','landed_cents',
             'quoted_rations','reference_price','delivered','sold','sale_gold','expiry','returned_cargo'}
    optional={'convoy','delivered_turn','sale_rate','sale_turn','closed','actual_extra_rations','rations_used'}
    for key,item in orders.items():
        if (not isinstance(item,dict)
                or set(item)!=numbers|optional|{'owner','source','target','actor','purpose','auto','status','destination','reason'}
                or any(type(item[k]) is not int or not 0<=item[k]<=10*logistics.LIMIT for k in numbers)
                or any(item[k] is not None and (type(item[k]) is not int or not 0<=item[k]<=10*logistics.LIMIT) for k in optional)
                or str(item['id'])!=key or not 1<=item['id']<ledger['next_id']
                or not 1<=item['created']<=state.turn or item['quoted_arrival']<=item['created']
                or item['expiry']!=item['quoted_arrival']+9 or not 0<item['estimated_net']<=item['purchased']
                or item['owner']=='neutral' or item['owner'] not in game.catalog.factions
                or item['source']==item['target'] or any(item[k] not in state.cities for k in ('source','target'))
                or item['actor'] not in state.officers or item['purpose'] not in PURPOSES
                or type(item['auto']) is not bool or item['status'] not in PENDING|CLOSED
                or item['destination'] is not None and item['destination'] not in state.cities
                or not 1<=item['purchase_rate']<=100 or not 1<=item['reference_price']<=100
                or item['purchase_gold']!=logistics_rules.ceil_div(item['purchased']*item['purchase_rate'],BASE)
                or item['sold']>min(item['purchased'],item['delivered']) or item['sold']%BASE
                or bool(item['sold'])!=(item['status']=='sold')
                or item['sold'] and item['sale_gold']!=item['sold']*item['sale_rate']//BASE
                or item['convoy'] is None and item['status']!='failed'
                or item['convoy'] is not None and item['closed'] is None and item['id'] not in seen):
            raise ValueError('Regional order receipt')
