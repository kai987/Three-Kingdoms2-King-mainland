"""City-to-city transshipment. Tags belong to grain already in a city warehouse."""
from collections import Counter, defaultdict
from copy import deepcopy

from . import command_books, historical_campaigns, logistics, logistics_rules, staging_supply
from . import march_supply, transport_capacity, transport_emergency, winter_travel
from .errors import GameError
from .officers import ref_sort_key

VERSION = 304
FIELD = 'transshipment_rules_version'
POOL = 'transshipment'
COMMAND = 'transshipment_order'
INVALID = '中轉計畫或運輸批次無效。'
BLOCKED = '中轉批次目前缺少可用糧、合資格人員、運輸位置或安全路線。'
MAX_PLANS = 12
PER_OWNER = 2
MAX_BATCHES_PER_STAGE = 2
HISTORY = 16
MAX_TURNS = 90
MODES = ('land', 'river', 'sea', 'fastest')
PURPOSES = ('shortage', 'reserve')
REASONS = {'planning', 'manual', 'ownership', 'covered', 'deadline', 'fulfilled', 'batches_exhausted'}


def enabled(state):
    return state is not None and POOL in state.extension


def initialize(state, version):
    if (type(version) is not int or version not in (0, VERSION)
            or version and logistics_rules.version(state) != logistics_rules.CURRENT):
        raise GameError('中轉運輸規則版本無效。')
    if version:
        state.extension.update({FIELD:VERSION, POOL:dict(next_id=1, plans={}, history=[], unloads=[])})


def _plans(state):
    return state.extension.get(POOL, {}).get('plans', {})


def tagged(state, owner=None):
    for plan in sorted(_plans(state).values(),key=lambda row:row['id']):
        if plan['status'] == 'active' and (owner is None or owner == plan['owner']):
            for batch in plan['batches']:
                if batch['available'] and state.cities[batch['target']].owner == plan['owner']:
                    yield plan, batch


def credit(state, city):
    return (sum(batch['available'] for _,batch in tagged(state) if batch['target'] == city)
            if enabled(state) else 0)


def _lookup(state, ident):
    for plan in _plans(state).values():
        for batch in plan['batches']:
            if batch['convoy'] == ident:
                return plan, batch
    return None


def is_batch(state, ident):
    return _lookup(state, ident) is not None


def _ids(plan):
    return (*plan['sources'], *plan['hubs'], plan['target'])


def _owned(state, plan):
    return all(key in state.cities and state.cities[key].owner == plan['owner'] for key in _ids(plan))


def _leg(plan, stage, source):
    itinerary = (*plan['hubs'], plan['target'])
    if 0 <= stage < len(itinerary) and (
            source in plan['sources'] if stage == 0 else source == itinerary[stage-1]):
        return itinerary[stage]
    return None


def _lot_release(batch, amount, kind):
    batch['available'] -= amount
    batch['released'][kind] += amount


def _close(state, plan, reason):
    for batch in plan['batches']:
        _lot_release(batch, batch['available'], 'closed')
    plan.update(status='complete' if reason == 'fulfilled' else 'cancelled', reason=reason, closed=state.turn)


def _pending(batch):
    return batch['receipt'] is None and batch['terminal'] is None


def _final_grain(plan):
    return sum(batch['receipt']['grain'] for batch in plan['batches']
               if batch['target'] == plan['target'] and batch['receipt'] is not None)


def _demand(game, state, owner, target, budgets):
    from . import faction_economy, granary_demand
    if owner not in budgets:
        budgets[owner] = faction_economy.plan(game, state, owner, granary=True)
    return granary_demand.for_city(game, state, budgets[owner], target)


def _still_needed(game, state, plan, budgets):
    target = state.cities[plan['target']]
    if plan['purpose'] == 'reserve':
        # Only projected cargo that is already bound for the final city counts.
        inbound = sum(logistics.inbound_grain(game, row, state) for row in logistics._pool(state)['convoys']
                      if row['target'] == target.id and row['owner'] == target.owner
                      and not row['delivery_done'] and row['status'] == 'outbound'
                      and row['target_march'] is None and 'convoy_relief' not in row)
        return max(0,min(plan['grain']-_final_grain(plan),plan['stock_goal']-target.grain-inbound))
    demand = _demand(game, state, plan['owner'], target.id, budgets)
    return max(0,min(plan['grain']-_final_grain(plan),sum(n for _,n in demand.remaining)))


def synchronize(game, state, *, settle_demand=False):
    if not enabled(state):
        return
    ledger = state.extension[POOL]
    budgets = {}
    for key,plan in sorted(ledger['plans'].items(),key=lambda pair:pair[1]['id']):
        if plan['status'] == 'active':
            reason = None
            if not _owned(state, plan):
                reason = 'ownership'
            elif _final_grain(plan) >= plan['grain']:
                reason = 'fulfilled'
            elif state.turn >= plan['original_deadline']:
                reason = 'deadline'
            elif (sum(b['target']==plan['target'] for b in plan['batches']) == MAX_BATCHES_PER_STAGE
                    and not any(_pending(b) and b['target']==plan['target'] for b in plan['batches'])):
                reason = 'batches_exhausted'
            elif settle_demand and not _still_needed(game,state,plan,budgets):
                # Planned intermediate arrivals never stand in for a final receipt.
                if not any(_pending(b) and b['target']==plan['target'] for b in plan['batches']):
                    reason = 'covered'
            if reason is not None:
                _close(state, plan, reason)
        if plan['status'] != 'active' and all(b['terminal'] is not None for b in plan['batches']):
            ledger['history'].append(ledger['plans'].pop(key))
    del ledger['history'][:-HISTORY]
    # Local rations, military commitments and existing granary promises are senior.
    for city, lots in _by_city(state).items():
        owner = state.cities[city].owner
        books = budgets.get(('stock',owner))
        if books is None:
            from . import faction_economy
            books = faction_economy.pending(state, owner, granary=True, transshipment_tags=False)
            budgets[('stock',owner)] = books
        room = _protectable(state, city, books)
        for _,batch in lots:
            keep = min(room, batch['available'])
            _lot_release(batch, batch['available'] - keep, 'priority')
            room -= keep


def _by_city(state):
    result = defaultdict(list)
    for plan,batch in tagged(state):
        result[batch['target']].append((plan,batch))
    return result


def _protectable(state, key, book):
    from . import strategic_granary
    city = state.cities[key]
    return max(0,min(staging_supply.available(state,city),city.grain
                     - book.amount(key) - strategic_granary.reserve_grain(state,city)))


def _create(game, state, payload, owner):
    fields = {'action','sources','hubs','target','grain','modes','purpose','promise_turns'}
    if set(payload) != fields:
        raise GameError(INVALID)
    sources,hubs,target = (payload[key] for key in ('sources','hubs','target'))
    modes,grain,purpose,turns = (payload[key] for key in ('modes','grain','purpose','promise_turns'))
    if (not isinstance(sources,list) or not 1 <= len(sources) <= MAX_BATCHES_PER_STAGE
            or not isinstance(hubs,list) or not 1 <= len(hubs) <= 2
            or not isinstance(modes,list) or len(modes) != len(hubs)+1 or any(m not in MODES for m in modes)
            or not logistics._int(grain,1,logistics.LIMIT) or purpose not in PURPOSES
            or not logistics._int(turns,2,MAX_TURNS)):
        raise GameError(INVALID)
    keys = (*sources,*hubs,target)
    if any(type(k) is not str or k not in state.cities or state.cities[k].owner != owner for k in keys):
        raise GameError(INVALID)
    if len(set(keys)) != len(keys) or len(_plans(state)) >= MAX_PLANS:
        raise GameError(INVALID)
    own = [plan for plan in _plans(state).values() if plan['owner'] == owner and plan['status'] == 'active']
    if len(own) >= PER_OWNER or any(plan['target'] == target for plan in own):
        raise GameError(INVALID)
    promise = state.turn + turns
    deadline = promise
    stock_goal = state.cities[target].grain + grain
    if purpose == 'shortage':
        demand = _demand(game,state,owner,target,{})
        if demand.first is None:
            raise GameError('目標城目前沒有未覆蓋的缺糧需求。')
        deadline = state.turn + demand.first
        grain = min(grain,sum(n for _,n in demand.remaining))
        stock_goal = None
    elif stock_goal > logistics.LIMIT:
        raise GameError(INVALID)
    ledger = state.extension[POOL]
    ident = ledger['next_id']
    if ident > 1_000_000:
        raise GameError(INVALID)
    ledger['next_id'] += 1
    ledger['plans'][str(ident)] = dict(id=ident,owner=owner,sources=list(sources),hubs=list(hubs),
        target=target,modes=list(modes),grain=grain,purpose=purpose,promise=promise,original_deadline=deadline,
        stock_goal=stock_goal,created=state.turn,status='active',reason='planning',closed=None,batches=[])


def _route(game, state, source, target, owner, mode, policy):
    outward = logistics._safe_path(game,state,source,target,owner,mode,policy)
    if outward is None or logistics._dangerous(outward,policy) or not logistics.safe_capacity_route(game,state,outward):
        return None
    return outward


def _quote(game, state, plan, stage, source, officer=None, *, needed=None):
    target = _leg(plan,stage,source)
    if (target is None or not _owned(state,plan) or plan['status'] != 'active'
            or sum(b['stage']==stage for b in plan['batches']) >= MAX_BATCHES_PER_STAGE):
        return dict(blocked='plan')
    a,b = state.cities[source],state.cities[target]
    blocker = transport_capacity.dispatch_blocker(state,a)
    if blocker:
        return dict(blocked=blocker)
    if not command_books.can_spend(state,plan['owner'],'dispatch_transport'):
        return dict(blocked='books')
    policy = logistics._pool(state)['cities'][source]['policy']
    absent = game._march_ids(state)
    if policy['max_officers'] < 1 or logistics._present_count(game,state,a,absent=absent)-1 < policy['reserve_officers']:
        return dict(blocked='escorts')
    threatened = any(row['kind']=='attack' and row['target']==a.id and row['owner']!=a.owner
                     and not historical_campaigns.allied(state,a.owner,row['owner'])
                     for row in state.extension['travel']['marches'])
    available_ids = [ident for ident in logistics._eligible(game,state,a,absent=absent,capacity_checks=True)
                     if logistics.escort_defence(game,state,a,[ident],absent=absent,threatened=threatened,
                                                 capacity_checks=True)]
    if officer is None and available_ids:
        officer = min(available_ids,key=lambda ident:(state.officers[ident].troops,ref_sort_key(ident)))
    if officer not in available_ids:
        return dict(blocked='escorts')
    lots = [batch for batch in plan['batches'] if batch['target']==source and batch['available']
            and batch['receipt']['turn'] < state.turn]
    if stage and not lots:
        return dict(blocked='waiting_for_stock')
    quote = _route(game,state,source,target,plan['owner'],plan['modes'][stage],policy)
    if quote is None or (set(quote['path'][1:-1]) & set(_ids(plan))):
        return dict(blocked='route')
    back = logistics.convoy_return(game,state,a,b,policy)
    if back is None or not logistics.safe_capacity_route(game,state,back[1]):
        return dict(blocked='route')
    rations = logistics.escort_rations(game,state,[officer],quote,back[1])
    city_available = transport_capacity.current_grain(state,a)-policy['reserve_grain']
    staged = sum(batch['available'] for batch in lots)
    available = min(staged,city_available+staged) if stage else city_available
    room = logistics.LIMIT-b.grain-logistics._inbound(state,target)['grain']
    profile = transport_capacity.physical(game,state,quote)
    limit = transport_capacity.effective_cargo(profile['physical_capacity'],rations,policy['max_grain'],available,room)
    if target==plan['target']:
        remaining = _still_needed(game,state,plan,{}) if needed is None else needed
        limit = logistics.gross_shipment(game,quote,remaining,limit,state=state) if remaining and limit else 0
    days = winter_travel.quote_days(game,state,quote)
    eta = state.turn+max(1,logistics_rules.ceil_div(days,10))
    return dict(blocked=None if limit else 'grain_or_room', officer=officer, target=target, quote=quote,
                back=back[1], lots=lots, capacity=profile['physical_capacity'], mode=plan['modes'][stage],
                max_cargo=limit, rations=rations, days=days, eta=eta, policy_grain=policy['max_grain'])


def _deadline(game, state, plan, stage, offer):
    eta = offer['eta']
    cities = (*plan['hubs'],plan['target'])
    for onward in range(stage+1,len(cities)):
        source,target = cities[onward-1:onward+1]
        policy = logistics._pool(state)['cities'][source]['policy']
        route = _route(game,state,source,target,plan['owner'],plan['modes'][onward],policy)
        if route is None:
            return None
        eta += 1+winter_travel.quote_turns(game,state,route)
    return eta


def _dispatch(game, state, payload, plan, owner):
    if set(payload) != {'action','plan','stage','source','officer','grain'}:
        raise GameError(INVALID)
    stage,source,officer,grain = (payload[k] for k in ('stage','source','officer','grain'))
    if (type(stage) is not int or type(source) is not str or type(officer) not in (int,str)
            or not logistics._int(grain,1,logistics.LIMIT)):
        raise GameError(INVALID)
    needed = _still_needed(game,state,plan,{})
    if not needed:
        raise GameError('目標城目前沒有未覆蓋的缺糧需求。')
    offer = _quote(game,state,plan,stage,source,officer,needed=needed)
    if offer['blocked'] or grain > offer['max_cargo']:
        raise GameError(BLOCKED)
    last_arrival = _deadline(game,state,plan,stage,offer)
    if last_arrival is None or last_arrival >= min(plan['original_deadline'],plan['promise']):
        raise GameError('中轉批次無法在原定期限前抵達。')
    net = logistics.projected_grain(game,offer['quote'],grain,state=state)
    if offer['target'] == plan['target'] and net > needed:
        raise GameError('本次中轉貨糧超過目標城剩餘需求。')
    parts = []
    if stage:
        debit = grain+offer['rations']
        for batch in offer['lots']:
            used = min(debit,batch['available'])
            if used:
                parts.append([batch['convoy'],used])
                debit -= used
        if debit:
            raise GameError(BLOCKED)
    cargo = dict(logistics._empty_cargo(),grain=grain)
    debits = dict(parts)
    for batch in offer['lots']:
        batch['available'] -= debits.get(batch['convoy'], 0)
    try:
        row = logistics.dispatch(game,state,dict(source=source,target=offer['target'],officers=[officer],
                                 cargo=cargo,route_mode=offer['mode']),owner,transshipment_quote=offer)
    except GameError:
        for batch in offer['lots']:
            batch['available'] += debits.get(batch['convoy'], 0)
        raise
    plan['batches'].append(dict(convoy=row['id'],stage=stage,source=source,target=offer['target'],grain=grain,
        rations=offer['rations'],capacity=offer['capacity'],books=command_books.cost('dispatch_transport'),
        officer=officer,parents=parts,turn=state.turn,eta=offer['eta'],estimated=net,receipt=None,terminal=None,
        available=0,released={'closed':0,'priority':0}, path=list(offer['quote']['path']),
        route_ids=[leg['id'] for leg in offer['quote']['routes']]))


def _unload(game,state,payload,owner):
    if (set(payload) != {'action','convoy','city','target','mode'} or type(payload['convoy']) is not int
            or payload['mode'] not in MODES):
        raise GameError(INVALID)
    city = game._owned_city(state,payload['city'])
    target = game._owned_city(state,payload['target'])
    row = next((row for row in logistics._pool(state)['convoys'] if row['id']==payload['convoy']
                and row['owner']==owner), None)
    if (row is None or not transport_capacity.enforced(state,row) or city.id==target.id
            or row['target_march'] is not None or 'convoy_relief' in row):
        raise GameError(BLOCKED)
    policy = row['route_policy']
    mode = payload['mode']
    quote = _route(game,state,city.id,target.id,owner,mode,policy)
    if quote is None:
        raise GameError(BLOCKED)
    review = transport_emergency.Review(game,state).measure(quote)
    if review is None:
        raise GameError(BLOCKED)
    from . import army_relief
    units = march_supply.ration_units(state,row['officers'],row['cargo']['reserves'])
    credit_units = row['journeys'][-1]['supply']['credit_units']
    rations = army_relief.ration_budget(units,review.weight,0,0,credit=credit_units).total
    amount = logistics.unload_for_route(game,state,row,city,target,mode,quote,rations)
    if amount is None:
        raise GameError('運輸隊須停在本方實際城池，且卸貨後能安全改道。')
    ledger = state.extension[POOL]['unloads']
    ledger.append(dict(convoy=row['id'],turn=state.turn,city=city.id,target=target.id,owner=owner,grain=amount,
        capacity=row['journeys'][-1][transport_capacity.LOAD_FIELD]['limit'],required_rations=rations))
    del ledger[:-HISTORY]


def execute(game, state, payload, owner):
    if not enabled(state) or not isinstance(payload,dict) or state.phase != 'city' or owner not in game.catalog.factions:
        raise GameError(INVALID)
    action = payload.get('action')
    if action == 'unload':
        _unload(game,state,payload,owner)
        return
    if action == 'create':
        if state.extension.get('pending_succession', {}).get(owner):
            raise GameError('请先选择继承君主。')
        _create(game, state, payload, owner)
        return
    ident = payload.get('plan')
    plan = _plans(state).get(str(ident)) if type(ident) is int else None
    if not plan or plan['owner'] != owner or plan['status'] != 'active':
        raise GameError(INVALID)
    if action == 'cancel' and set(payload) == {'action','plan'}:
        _close(state,plan,'manual')
    elif action == 'dispatch':
        game._owned_city(state,payload.get('source'))
        _dispatch(game,state,payload,plan,owner)
    else:
        raise GameError(INVALID)


def delivered(state, convoy, target, grain):
    match = _lookup(state,convoy['id'])
    if match is None:
        return
    plan,batch = match
    if batch['receipt'] is not None or batch['target'] != target.id:
        raise ValueError('Transshipment receipt identity')
    batch['receipt'] = dict(turn=state.turn,grain=grain)
    if batch['target'] != plan['target']:
        if plan['status'] == 'active' and _owned(state,plan):
            batch['available'] = grain
        else:
            batch['released']['closed'] = grain


def terminated(state, convoy, outcome, city, tick):
    match = _lookup(state,convoy['id'])
    if match is None:
        return
    _,batch = match
    if batch['terminal'] is not None:
        raise ValueError('Transshipment terminal was already recorded')
    bags = [leg['supply'] for leg in convoy['journeys']]
    batch['terminal'] = dict(tick=tick,city=city,outcome=outcome,
        cargo=logistics.grain_receipt(convoy,returned=city is not None,abandoned=city is None),
        external_rations=sum(book['received'] for book in bags)
            -sum(item['before']['grain']-item['after']['grain'] for item in convoy['cargo_ledger']
                 if item['kind'] == 'rations'),
        spent_rations=sum(book['consumed'] for book in bags),returned_rations=bags[-1]['remaining'])


def view(game,state,owner):
    ledger = state.extension[POOL]
    cities = [key for key,city in state.cities.items() if city.owner == owner]
    plans = []
    for plan in (*sorted(ledger['plans'].values(),key=lambda row:row['id']), *reversed(ledger['history'])):
        if plan['owner'] != owner:
            continue
        offers = []
        if plan['status'] == 'active':
            for stage,origins in enumerate((plan['sources'],*([city] for city in plan['hubs']))):
                for source in origins:
                    quote = _quote(game,state,plan,stage,source)
                    show = {key:val for key,val in quote.items() if key not in {'quote','back','lots'}}
                    if not quote['blocked']:
                        arrival = _deadline(game,state,plan,stage,quote)
                        show['final_eta'] = arrival
                        if arrival is None or arrival >= min(plan['original_deadline'],plan['promise']):
                            show['blocked'] = 'deadline'
                    offers.append(dict(stage=stage,source=source,**show))
        plans.append(dict(deepcopy(plan),offers=offers,final_received=_final_grain(plan)))
    unloads=[dict(row) for row in ledger['unloads'] if row['owner']==owner]
    return dict(version=VERSION,cities=cities,plans=plans,unloads=unloads,
                order_costs=dict(create=0,cancel=0,unload=0,dispatch=command_books.cost('dispatch_transport')))


_PLAN_FIELDS = {'id','owner','sources','hubs','target','modes','grain','purpose','promise','original_deadline',
                'stock_goal','created','status','reason','closed','batches'}
_BATCH_FIELDS = {'convoy','stage','source','target','grain','rations','capacity','books','officer','parents',
                 'turn','eta','estimated','receipt','terminal','available','released','path','route_ids'}


def _validate_terminal(value, batch, game, state):
    if (not isinstance(value,dict) or set(value) != {'tick','city','outcome','cargo','external_rations',
            'spent_rations','returned_rations'}
            or not logistics._int(value['tick'],(batch['turn']-1)*10,(state.turn-1)*10)
            or value['city'] is not None and value['city'] not in game.catalog.map_cities
            or value['outcome'] not in {'returned_home','received_elsewhere','surrender_settlement','no_friendly_city'}
            or any(not logistics._int(value[key],0,16*logistics.LIMIT)
                   for key in ('external_rations','spent_rations','returned_rations'))
            or not logistics.valid_grain_receipt(value['cargo'])):
        raise ValueError('Transshipment terminal receipt')
    receipt = batch['receipt']
    cargo = value['cargo']
    destinations = ('cargo_delivered','cargo_route_loss','cargo_weather_loss','cargo_abandoned','cargo_returned')
    if (cargo['cargo_dispatched'] != batch['grain'] or cargo['cargo_remaining']
            or cargo['cargo_delivered'] != (receipt['grain'] if receipt is not None else 0)
            or cargo['escort_base_grain']+cargo['escort_extra_grain'] != value['spent_rations']
            or batch['grain']+batch['rations']+value['external_rations']
                != sum(cargo[k] for k in destinations)+cargo.get('cargo_waypoint_unloaded',0)
                +value['spent_rations']+value['returned_rations']):
        raise ValueError('Transshipment terminal stock balance')


def _validate_batch(game,state,plan,batch,last,prior,active):
    integer = logistics._int
    if (not isinstance(batch,dict) or set(batch) != _BATCH_FIELDS or
            not integer(batch['stage'],0,len(plan['hubs'])) or type(batch['source']) is not str
            or _leg(plan,batch['stage'],batch['source']) != batch['target']
            or not integer(batch['convoy'], last+1, logistics._pool(state)['next_id']-1)
            or not integer(batch['grain'],1,logistics.LIMIT) or not integer(batch['rations'],0,logistics.LIMIT)
            or not integer(batch['capacity'],1,logistics.LIMIT) or batch['grain']+batch['rations'] > batch['capacity']
            or not integer(batch['books'],1,command_books.cost('dispatch_transport'))
            or type(batch['officer']) not in (int,str)
            or not integer(batch['turn'],plan['created'],state.turn)
            or not integer(batch['eta'],batch['turn']+1,plan['promise'])
            or not integer(batch['estimated'],0,batch['grain'])
            or not integer(batch['available'],0,logistics.LIMIT)
            or not isinstance(batch['released'],dict) or set(batch['released']) != {'closed','priority'}
            or any(not integer(n,0,logistics.LIMIT) for n in batch['released'].values())
            or not isinstance(batch['path'],list) or len(batch['path']) < 2
            or any(type(key) is not str or key not in game.catalog.map_cities for key in batch['path'])
            or batch['path'][0] != batch['source'] or batch['path'][-1] != batch['target']
            or len(set(batch['path'])) != len(batch['path'])
            or not isinstance(batch['route_ids'],list) or len(batch['route_ids']) != len(batch['path'])-1
            or any(type(key) is not str for key in batch['route_ids'])):
        raise ValueError('Transshipment batch identity')
    receipt = batch['receipt']
    if receipt is not None and (not isinstance(receipt,dict) or set(receipt) != {'turn','grain'}
            or not integer(receipt['turn'],batch['turn']+1,state.turn)
            or not integer(receipt['grain'],0,logistics.LIMIT)):
        raise ValueError('Transshipment delivery receipt')
    parents = batch['parents']
    if (not isinstance(parents,list) or len(parents) > MAX_BATCHES_PER_STAGE
            or any(not isinstance(pair,list) or len(pair)!=2 or type(pair[0]) is not int
                   or pair[0] not in prior or not integer(pair[1],1,batch['grain']+batch['rations'])
                   or prior[pair[0]]['stage'] != batch['stage']-1 or prior[pair[0]]['target'] != batch['source']
                   or prior[pair[0]]['receipt'] is None or prior[pair[0]]['receipt']['turn'] >= batch['turn']
                   for pair in parents) or len({pair[0] for pair in parents}) != len(parents)
            or sum(n for _,n in parents) != (batch['grain']+batch['rations'] if batch['stage'] else 0)):
        raise ValueError('Transshipment provenance')
    if batch['terminal'] is not None:
        if batch['convoy'] in active:
            raise ValueError('Active convoy already closed')
        _validate_terminal(batch['terminal'],batch,game,state)
    else:
        row = active.get(batch['convoy'])
        if (row is None or (row['owner'],row['source'],row['original_target']) !=
                (plan['owner'],batch['source'],batch['target'])
                or row['original_officers'] != [batch['officer']] or row['initial_cargo']['grain'] != batch['grain']
                or row['journeys'][0]['supply']['loaded'] != batch['rations']
                or row['journeys'][0]['quote']['path'] != batch['path']
                or [r['id'] for r in row['journeys'][0]['quote']['routes']] != batch['route_ids']
                or row['journeys'][0][transport_capacity.LOAD_FIELD]['limit'] != batch['capacity']
                or row['delivery_done'] != (receipt is not None)
                or receipt is not None and row['delivered']['grain'] != receipt['grain']):
            raise ValueError('Transshipment live convoy')


def validate(game, state):
    if FIELD not in state.extension and POOL not in state.extension:
        return
    ledger = state.extension.get(POOL)
    if (type(state.extension.get(FIELD)) is not int or state.extension[FIELD] != VERSION
            or logistics_rules.version(state) != logistics_rules.CURRENT or not isinstance(ledger,dict)
            or set(ledger) != {'next_id','plans','history','unloads'} or not logistics._int(ledger['next_id'],1,1_000_001)
            or not isinstance(ledger['plans'],dict) or len(ledger['plans'])>MAX_PLANS
            or not isinstance(ledger['history'],list) or len(ledger['history'])>HISTORY
            or not isinstance(ledger['unloads'],list) or len(ledger['unloads'])>HISTORY):
        raise ValueError('Transshipment ledger')
    active = {row['id']:row for row in logistics._pool(state)['convoys']}
    unloads = set()
    for row in ledger['unloads']:
        if (not isinstance(row,dict) or set(row)!={'convoy','turn','city','target','owner','grain','capacity','required_rations'}
                or row['owner'] not in game.catalog.factions or row['city'] not in game.catalog.map_cities
                or row['target'] not in game.catalog.map_cities or row['city']==row['target']
                or not logistics._int(row['turn'],1,state.turn)
                or not logistics._int(row['convoy'],1,logistics._pool(state)['next_id']-1)
                or not logistics._int(row['grain'],1,logistics.LIMIT)
                or not logistics._int(row['capacity'],1,logistics.LIMIT)
                or not logistics._int(row['required_rations'],0,row['capacity'])):
            raise ValueError('Transshipment waypoint receipt')
        key = row['convoy'],row['turn']
        if key in unloads:
            raise ValueError('Duplicate waypoint receipt')
        unloads.add(key)
    known_ids,convoy_ids,targets = set(),set(),set()
    owners = Counter()
    for key,plan in (*ledger['plans'].items(), *((None,plan) for plan in ledger['history'])):
        if (not isinstance(plan,dict) or set(plan) != _PLAN_FIELDS
                or not logistics._int(plan['id'],1,ledger['next_id']-1) or plan['id'] in known_ids
                or key is not None and key != str(plan['id']) or plan['owner'] not in game.catalog.factions
                or not isinstance(plan['sources'],list) or not 1 <= len(plan['sources']) <= MAX_BATCHES_PER_STAGE
                or not isinstance(plan['hubs'],list) or not 1 <= len(plan['hubs']) <= 2
                or any(type(k) is not str or k not in game.catalog.map_cities for k in _ids(plan))
                or len(set(_ids(plan))) != len(_ids(plan)) or not isinstance(plan['modes'],list)
                or len(plan['modes']) != len(plan['hubs'])+1 or any(mode not in MODES for mode in plan['modes'])
                or not logistics._int(plan['grain'],1,logistics.LIMIT) or plan['purpose'] not in PURPOSES
                or not logistics._int(plan['created'],1,state.turn)
                or not logistics._int(plan['promise'],plan['created']+2,plan['created']+MAX_TURNS)
                or not logistics._int(plan['original_deadline'],plan['created']+1,plan['created']+MAX_TURNS)
                or plan['purpose']=='reserve' and (not logistics._int(plan['stock_goal'],plan['grain'],logistics.LIMIT)
                                                  or plan['original_deadline']!=plan['promise'])
                or plan['purpose']=='shortage' and plan['stock_goal'] is not None
                or plan['status'] not in ('active','cancelled','complete') or plan['reason'] not in REASONS
                or not isinstance(plan['batches'],list) or len(plan['batches']) > (len(plan['hubs'])+1)*MAX_BATCHES_PER_STAGE):
            raise ValueError('Transshipment plan')
        known_ids.add(plan['id'])
        if plan['status'] == 'active':
            identity = plan['owner'],plan['target']
            if (identity in targets or key is None or plan['closed'] is not None or plan['reason']!='planning'
                    or not _owned(state,plan) or plan['original_deadline'] <= state.turn):
                raise ValueError('Transshipment active ownership or deadline')
            targets.add(identity)
            owners[plan['owner']] += 1
        elif not logistics._int(plan['closed'],plan['created'],state.turn) or plan['reason']=='planning':
            raise ValueError('Transshipment closure')
        prior, usage, stage_count = {}, Counter(), Counter()
        for batch in plan['batches']:
            _validate_batch(game,state,plan,batch,next(reversed(prior),0),prior,active)
            ident = batch['convoy']
            if ident in convoy_ids or key is None and batch['terminal'] is None:
                raise ValueError('Transshipment duplicate or archived active convoy')
            convoy_ids.add(ident)
            stage_count[batch['stage']] += 1
            for parent,amount in batch['parents']:
                usage[parent] += amount
            prior[ident] = batch
        if any(count>MAX_BATCHES_PER_STAGE for count in stage_count.values()):
            raise ValueError('Transshipment stage capacity')
        for ident,batch in prior.items():
            lot = batch['receipt']['grain'] if batch['receipt'] is not None and batch['target']!=plan['target'] else 0
            if (batch['available']+sum(batch['released'].values())+usage[ident] != lot
                    or plan['status']!='active' and batch['available']):
                raise ValueError('Transshipment warehouse balance')
    if any(count>PER_OWNER for count in owners.values()):
        raise ValueError('Transshipment active plan count')
    from . import faction_economy
    book = {}
    for key,lots in _by_city(state).items():
        owner = state.cities[key].owner
        if owner not in book:
            book[owner] = faction_economy.pending(state,owner,granary=True,transshipment_tags=False)
        if sum(batch['available'] for _,batch in lots) > _protectable(state,key,book[owner]):
            raise ValueError('Transshipment warehouse exceeds physical stock')
