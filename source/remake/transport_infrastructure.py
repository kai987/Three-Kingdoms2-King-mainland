"""Optional wharf custody and escorted grain services along authored edges."""

from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import NamedTuple

from . import command_books, domestic, grain_units, logistics, logistics_rules as rules
from . import route_hazards, route_network, staging_supply, strategic_granary
from . import transport_capacity, winter_travel, winter_weather
from .errors import GameError
from .infrastructure_sites import CORRIDORS, SITES
from .officers import ref_sort_key

FIELD = 'transport_infrastructure_rules_version'
POOL = 'transport_infrastructure'
VERSION = 3042
COMMAND = 'infrastructure_order'
MAX_PLANS = 12
PER_OWNER = 2
HISTORY = 16
LEDGER_ROWS = 192
MAX_DEADLINE_DAYS = 900
STORAGE = 1_600           # Authored units. Scaling follows the save.
HANDLING = 400            # Grain per berth per calendar day.
ORDER = 'dispatch_transport'
INVALID = '交通設施或河陸接駁指令無效。'
BLOCKED = '接駁條件已改變，請重新確認報價。'
ACTIVE = {'moving', 'unloading', 'loading', 'returning', 'waiting_return'}
CARGO = ('cargo', 'bank0', 'bank1')
BALANCES = ('input', *CARGO, 'rations', 'delivery', 'meals', 'route_loss', 'weather_loss',
            'returned', 'captured', 'warehoused', 'abandoned')
TRANSFERS = {
    'dispatch_cargo': {('input','cargo')},
    'dispatch_meal': {('input','rations')},
    'unload': {('cargo','bank0'), ('cargo','bank1')},
    'load': {('bank0','cargo'), ('bank1','cargo')},
    'consume': {('rations','meals')},
    'cargo_meal': {(name,'rations') for name in CARGO},
    'route_loss': {('cargo','route_loss')},
    'weather_loss': {('cargo','weather_loss')},
    'delivery': {('cargo','delivery')},
    'return': {('cargo','returned'), ('rations','returned')},
    'seizure': {('bank0','captured'), ('bank1','captured')},
    'release_stock': {('bank0','warehoused'), ('bank1','warehoused')},
    'abandon': {('cargo','abandoned'), ('rations','abandoned')},
}
_observer = ContextVar('infrastructure_observer', default=None)


@contextmanager
def observing(callback):
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def _observe(kind, state, tick, **fields):
    callback = _observer.get()
    if callback is not None:
        callback(kind, dict(turn=state.turn, tick=tick, **deepcopy(fields)))


class Section(NamedTuple):
    start: str
    end: str
    mode: str
    parts: tuple
    region: str

    @property
    def work(self):
        return sum(p.work for p in self.parts)


def compile_routes(catalog):
    return {r['id']: r for r in catalog.data['travel_routes'] if r['id'] in CORRIDORS}


def enabled(state):
    return state is not None and POOL in state.extension


def initialize(game, state, version):
    if type(version) is not int or version not in (0, VERSION) or (
            version and (rules.version(state) != rules.CURRENT or enabled(state))):
        raise GameError(INVALID)
    if not version:
        return
    nodes = {key: dict(owner=_site_owner(state,key),seized=0,unclaimed=0,lots={})
             for ident in game.catalog.infrastructure_routes for key in CORRIDORS[ident]}
    state.extension.update({FIELD: VERSION, POOL: dict(nodes=nodes, jobs={}, history=[],
                            next_id=1, clock=(state.turn-1)*10)})


def _pool(state):
    return state.extension[POOL]


def _site_owner(state, site):
    city = state.cities.get(SITES[site][0])
    return city.owner if city else 'neutral'


def jobs(state):
    return state.extension.get(POOL, {}).get('jobs', {}).values()


def marching_ids(state):
    return {job['escort'] for job in jobs(state)}


def leg_origins(state):
    return ((job['source'], job['owner']) for job in jobs(state))


def clock(state):
    ledger = state.extension.get(POOL)
    return ledger['clock'] if ledger and ledger['jobs'] else None


def _bounds(raw, banks, source):
    forward = raw['from'] == source
    return (raw['to'] if forward else raw['from']), (banks if forward else banks[::-1])


def sections(game, route, source, month):
    """Partition the actual direction; keep the single original embark stage."""
    raw = game.catalog.infrastructure_routes[route]
    end, banks = _bounds(raw, CORRIDORS[route], source)
    leg = route_hazards.evaluate_leg(game.catalog.data, raw, source, end, month)
    parts = winter_travel.plan(game, game._quote([source, end], [leg]))
    water_start = next(i for i, part in enumerate(parts) if part.mode == 'embark' or part.mode.startswith('river_'))
    water_end = max(i for i, part in enumerate(parts) if part.mode.startswith('river_')) + 1
    if not 0 < water_start < water_end < len(parts):
        raise ValueError('Wharf work must include two nonempty land approaches')
    points = (source, *banks, end)
    regions = [game.catalog.climate.cities[SITES[key][0] if key in SITES else key]['climate_region_id']
               for key in points]
    result = tuple(Section(points[i], points[i+1], mode, span, regions[i+1]) for i, (mode, span) in
                   enumerate(zip(('land','river','land'), (parts[:water_start], parts[water_start:water_end],
                                                           parts[water_end:]))))
    if sum(s.work for s in result) != leg['days'] * winter_travel.QUANTA:
        raise ValueError('Wharf sections changed directional route work')
    return result


def _access(game, state, job, start, end):
    raw = game.catalog.infrastructure_routes[job['route']]
    cities = state.cities
    if not {raw['from'],raw['to']} <= cities.keys() or not route_network.available(raw, state.year, state.month):
        return 'road_closed'
    origin = job['target'] if job.get('returning') else job['source']
    dest = job['source'] if job.get('returning') else job['target']
    if not route_hazards.route_allowed(game.catalog.data, raw, origin, dest):
        return 'direction'
    for place in (start,end):
        if place in SITES:
            friendly = _site_owner(state, place) == job['owner']
        else:
            friendly = cities[place].owner == job['owner']
        if not friendly:
            return 'permission'
    return None


def _lot_map(state, job, account):
    if account == 'cargo':
        return job['parcels']
    site = job['banks'][int(account[-1])]
    return _pool(state)['nodes'][site]['lots'].get(str(job['id']), [])


def _store_lots(state, job, account, parcels):
    if account == 'cargo':
        job['parcels'] = parcels
        return
    site = job['banks'][int(account[-1])]
    stocks = _pool(state)['nodes'][site]['lots']
    if parcels:
        stocks[str(job['id'])] = parcels
    else:
        stocks.pop(str(job['id']), None)


def _apply(balances, source, target, amount):
    if (source != 'input' and amount > balances[source]) or amount <= 0:
        raise ValueError('Wharf debit exceeds stock')
    balances[source] += amount if source == 'input' else -amount
    balances[target] += amount


def _post(state, job, tick, kind, source, target, amount, *, city_delta=None):
    if not amount:
        return
    balances = job['balances']
    serial = job['serial'] + 1
    before = [balances[source],balances[target]]
    parents = []
    if source in CARGO:
        remainder, parcels = amount, []
        for lot, n in _lot_map(state,job,source):
            debit = min(n,remainder)
            if debit:
                parents.append([lot,debit])
                remainder -= debit
            if n>debit:
                parcels.append([lot,n-debit])
        if remainder:
            raise ValueError('Wharf physical lot is missing')
        _store_lots(state,job,source,parcels)
    if target in CARGO:
        # Stock is kept at the bank until the next completed loading operation.
        _store_lots(state,job,target,[*_lot_map(state,job,target),[serial,amount]])
    _apply(balances,source,target,amount)
    row = dict(serial=serial,tick=tick,kind=kind,source=source,target=target,grain=amount,
               before=before,after=[balances[source],balances[target]],parents=parents,city_delta=city_delta)
    job['serial'] = serial
    job['events'].append(row)
    if len(job['events'])>LEDGER_ROWS:
        first = job['events'].pop(0)
        _apply(job['prefix'],first['source'],first['target'],first['grain'])
    _observe('grain',state,tick,chain=job['id'],owner=job['owner'],route=job['route'],entry=row)


def _stock(node):
    return node['seized']+node['unclaimed']+sum(n for lots in node['lots'].values() for _,n in lots)


def _reservation(job, bank):
    """Full initial cargo reservation until its actual warehouse is cleared."""
    if job['phase'] not in ACTIVE or job['returning'] or bank not in job['banks']:
        return 0
    index = job['banks'].index(bank)
    if job['stage'] > index+1 or (job['stage']==index+1 and job['phase']=='moving'):
        return 0
    if job['cancel']:
        return job['balances'][f'bank{index}']
    return job['requested']


def _reserved(state, key):
    return sum(_reservation(job,key) for job in jobs(state))


def _node_room(state, key):
    node = _pool(state)['nodes'][key]
    return (grain_units.amount(STORAGE)-node['seized']-node['unclaimed']-_reserved(state,key))


def _wait_rate(state, region):
    return winter_travel.wait_rate(state,region) if winter_weather.movement(state) else rules.RATION_SCALE


def _rates(state, parts):
    if winter_weather.movement(state):
        return tuple(winter_travel.medium(state,p) for p in parts)
    return tuple((*winter_travel._medium(p.mode,0,0,0,False),None) for p in parts)


def _estimate(state, section):
    return winter_travel._forecast(tuple(p.work for p in section.parts), _rates(state,section.parts),
                                  _wait_rate(state,section.region))


def _estimate_clear(state, section, cargo):
    days, ration, exposure, frozen = _estimate(state,section)
    if frozen:
        return days,ration,0,frozen
    # Current-weather bound. The actual balance uses daily compounded losses.
    return days,ration,cargo-rules.cargo_loss(cargo,exposure,0)[0],None


def _city_budget(state, city, policy):
    reserved = min(staging_supply.available(state,city),strategic_granary.available(state,city))
    booked = transport_capacity.current_grain(state,city)
    return max(0,min(reserved,booked)-policy['reserve_grain'])


def _people(game, state, city, policy, absent, *, automatic):
    if policy['max_officers'] < 1 or logistics._present_count(game,state,city,absent=absent) <= policy['reserve_officers']:
        return []
    return sorted((i for i in logistics._eligible(game,state,city,absent=absent,automatic=automatic,capacity_checks=True)
                   if i != state.extension['leaders'].get(city.owner) and logistics.escort_defence(
                       game,state,city,[i],absent=absent,capacity_checks=True)),
                  key=lambda i:(state.officers[i].troops,ref_sort_key(i)))


def _shape(section):
    return dict(start=section.start,end=section.end,mode=section.mode,work=section.work,
                work_ticks=section.work//winter_travel.SPEED_UNIT)


def _cap(state, stages, policy):
    if not transport_capacity.enabled(state,'physical_capacity'):
        return policy['max_grain']
    factors = [transport_capacity.RATIOS[p.mode] for s in stages for p in s.parts
               if p.mode in transport_capacity.RATIOS]
    return min(policy['max_grain'],transport_capacity.base_capacity(state)*min(factors)//100)


def quote(game, state, owner, route, source, batches, deadline, *, escort=None, absent=None, automatic=False):
    result = {'blocked':None}
    raw = game.catalog.infrastructure_routes.get(route)
    if not enabled(state) or raw is None or source not in (raw['from'],raw['to']):
        return dict(blocked='no_facility')
    target,banks = _bounds(raw,CORRIDORS[route],source)
    if not {source,target} <= state.cities.keys() or owner == 'neutral':
        return dict(blocked='permission')
    start,end = state.cities[source],state.cities[target]
    candidate = dict(owner=owner,route=route,source=source,target=target)
    forward_access = _access(game,state,candidate,source,target)
    backward_access = _access(game,state,dict(candidate,returning=True),target,source)
    if forward_access or backward_access or any(_site_owner(state,b)!=owner for b in banks):
        return dict(blocked=forward_access or backward_access or 'permission')
    if any(type(n) is not int or n < 1 for n in batches) or not 1<=len(batches)<=2:
        return dict(blocked='load')
    amount=sum(batches)
    if amount>grain_units.amount(STORAGE):
        return dict(blocked='storage')
    active=list(jobs(state))
    from . import transshipment
    prior=[*active,*transshipment._plans(state).values()]
    if (len(prior)>=MAX_PLANS or sum(row['owner']==owner for row in prior)>=PER_OWNER
            or any(row['owner']==owner and row['target']==target for row in prior)):
        return dict(blocked='plan_limit')
    blocker=transport_capacity.dispatch_blocker(state,start)
    if blocker or not command_books.can_spend(state,owner,ORDER):
        return dict(blocked=blocker or 'books')
    if winter_weather.stage(state)>=4:
        ice=state.extension[winter_weather.POOL]['ice']
        if any(ice.get(reach['reach_id'], {}).get('state')==3 for reach in raw['river_segments']):
            return dict(blocked='frozen')
    if min(_node_room(state,key) for key in banks)<amount:
        return dict(blocked='storage')
    policy=logistics._pool(state)['cities'][source]['policy']
    absent=game._march_ids(state) if absent is None else absent
    people=_people(game,state,start,policy,absent,automatic=automatic)
    if escort is None and people:
        escort=people[0]
    if escort not in people:
        return dict(blocked='staff')
    outward=sections(game,route,source,state.month)
    backward=sections(game,route,target,state.month)
    stages=[_estimate(state,s) for s in (*outward,*backward)]
    if any(row[-1] for row in stages):
        return dict(blocked='frozen')
    units=state.officers[escort].troops+100
    # A conservative whole-day budget at both docks, plus any current
    # reservations ahead of this service. Future weather and books may change.
    loads=rules.ceil_div(amount,grain_units.amount(HANDLING))
    queue=sum(2*rules.ceil_div(_reserved(state,key),grain_units.amount(HANDLING)) for key in banks)
    wait=4*loads+queue
    stationary=sum(_wait_rate(state,s.region) for s in outward[:2])*2*loads
    stationary+=queue*max(_wait_rate(state,s.region) for s in outward[:2])
    divisor=grain_units.denominator()*rules.RATION_SCALE
    rations=rules.ceil_div(units*(sum(row[1] for row in stages)+stationary),divisor)
    planned_capacity=[_cap(state,(s,),policy) for s in outward]
    if (amount+rations > min(planned_capacity) or amount+rations > _city_budget(state,start,policy)
            or end.grain+amount>logistics.LIMIT):
        return dict(blocked='grain_or_capacity')
    now=(state.turn-1)*10
    eta=now+sum(row[0] for row in stages[:3])+wait
    end_at=eta+sum(row[0] for row in stages[3:])
    net=amount
    for s in outward:
        _,_,net,_=_estimate_clear(state,s,net)
    result.update(escort=escort, escorts=people, route=route, source=source,target=target, banks=list(banks),
                  sections=[dict(_shape(s),days=v[0],capacity=cap) for s,v,cap
                            in zip(outward,stages,planned_capacity)],
                  queue_days=queue,handling_days=4*loads,eta=eta,return_eta=end_at,
                  original_deadline=deadline,requested=amount,net=net,rations=rations,
                  command_books=3,officer_days=end_at-now,slot_days=end_at-now, gold=0)
    if eta>=deadline:
        result['blocked']='deadline'
    return result


def _dispatch(game, state, owner, offer, batches):
    ledger = _pool(state)
    ident = ledger['next_id']
    city = state.cities[offer['source']]
    tick = (state.turn-1)*10
    row = dict(id=ident, route=offer['route'], source=city.id, target=offer['target'],
               banks=offer['banks'], owner=owner, escort=offer['escort'], created=tick, month=state.month,
               deadline=offer['original_deadline'], predicted=offer['eta'], predicted_net=offer['net'],
               requested=sum(batches), phase='moving', stage=0, offset=0, at=city.id,
               returning=False, cancel=False, blocked=None, parcels=[], paid=[0],
               serial=0,credit=0,loss_remainder=0,hunger_streak=0,events=[],terminal=None,arrival=None,
               prefix=dict.fromkeys(BALANCES,0), balances=dict.fromkeys(BALANCES,0),
               metrics=dict.fromkeys(('travel','handling','waiting','return_days','hunger_days','hunger_losses'),0))
    ledger['next_id'] += 1
    ledger['jobs'][str(ident)] = row
    command_books.spend(state,city,ORDER)
    transport_capacity.record_dispatch(state,city.id)
    domestic.on_departure(game,state,[row['escort']],city.id)
    state.extension['officer_actions'][str(row['escort'])] = state.turn
    for kind, account, quantity in [('dispatch_cargo','cargo',n) for n in batches]+[
            ('dispatch_meal','rations',offer['rations'])]:
        before = city.grain
        city.grain -= quantity
        _post(state,row,tick,kind,'input',account,quantity,city_delta=[city.id,before,city.grain])
    _observe('departure',state,tick,chain=ident,owner=owner,quote=offer,books=1,
             person=row['escort'],source_grain=city.grain)


def execute(game, state, payload, owner):
    if not enabled(state) or state.phase not in ('city','ai') or not isinstance(payload,dict):
        raise GameError(INVALID)
    if state.extension.get('pending_succession', {}).get(owner):
        raise GameError(INVALID)
    ledger = _pool(state)
    action = payload.get('action')
    if action=='dispatch' and set(payload)=={'action','id','route','source','batches','deadline','escort'}:
        ident, route, source, batches, deadline, escort = (payload[k] for k in
                                                             ('id','route','source','batches','deadline','escort'))
        now=(state.turn-1)*10
        if (type(ident) is not int or ident!=ledger['next_id'] or ident>1_000_000
                or type(route) is not str or type(source) is not str or type(batches) is not list
                or not logistics._int(deadline,now+1,now+MAX_DEADLINE_DAYS)
                or type(escort) not in (int,str)):
            raise GameError(INVALID)
        offer=quote(game,state,owner,route,source,batches,deadline,escort=escort,
                    automatic=state.phase=='ai')
        if offer['blocked']:
            raise GameError(BLOCKED)
        _dispatch(game,state,owner,offer,batches)
        return
    if action=='cancel' and set(payload)=={'action','id'} and type(payload['id']) is int:
        row=ledger['jobs'].get(str(payload['id']))
        if row is not None and row['owner']==owner and not row['cancel'] and not row['returning']:
            row['cancel']=True
            _observe('cancel',state,(state.turn-1)*10,chain=row['id'],owner=owner,at=row['at'])
            return
    raise GameError(INVALID)


def _location_region(game, place):
    city = SITES[place][0] if place in SITES else place
    return game.catalog.climate.cities[city]['climate_region_id']


def _meal(game, state, row, tick, rate):
    officer=state.officers[row['escort']]
    divisor=grain_units.denominator()*rules.RATION_SCALE
    cost=max(0,(officer.troops+100)*rate-row['credit'])
    needed=rules.ceil_div(cost,divisor)
    balances=row['balances']
    if needed>balances['rations']:
        from_account='cargo' if balances['cargo'] else next((
            f'bank{i}' for i,key in enumerate(row['banks'])
            if row['at']==key and _site_owner(state,key)==row['owner'] and balances[f'bank{i}']),None)
        if from_account:
            _post(state,row,tick,'cargo_meal',from_account,'rations',
                  min(balances[from_account],needed-balances['rations']))
    paid=min(needed,balances['rations'])
    _post(state,row,tick,'consume','rations','meals',paid)
    row['credit']=max(0,row['credit']+paid*divisor-(officer.troops+100)*rate)
    lost=0
    if paid<needed:
        row['hunger_streak']+=1
        if row['hunger_streak']>=10 and not row['returning']:
            row['cancel']=True
        lost=(officer.troops+99)//100
        officer.troops-=lost
        state.soldiers['lost']+=lost
        row['metrics']['hunger_days']+=1
        row['metrics']['hunger_losses']+=lost
        if lost:
            from . import war_recovery
            war_recovery.record(state,row['owner'],row['source'],'convoy',lost)
    else:
        row['hunger_streak']=0
    _observe('meal',state,tick,chain=row['id'],owner=row['owner'],at=row['at'],required=needed,paid=paid,
             missing=needed-paid,troops_lost=lost)
    return paid


def _finish(game,state,row,tick,city=None,reason='returned'):
    ledger=_pool(state)
    if city is not None:
        balances=row['balances']
        if city.grain + balances['cargo'] + balances['rations']>logistics.LIMIT:
            row.update(phase='waiting_return',blocked='storage')
            return
        for account in ('cargo','rations'):
            amount=balances[account]
            before=city.grain
            city.grain+=amount
            _post(state,row,tick,'return',account,'returned',amount,city_delta=[city.id,before,city.grain])
    else:
        for i,site in enumerate(row['banks']):
            account=f'bank{i}'
            stored=row['balances'][account]
            _post(state,row,tick,'release_stock',account,'warehoused',stored)
            ledger['nodes'][site]['unclaimed']+=stored
        for account in ('cargo','rations'):
            _post(state,row,tick,'abandon',account,'abandoned',row['balances'][account])

    ledger['jobs'].pop(str(row['id']))
    row.update(phase='closed',terminal=dict(tick=tick,city=city.id if city else None,reason=reason))
    if city is not None:
        ident=row['escort']
        home=logistics._home(state,ident)
        if home.id!=city.id:
            home.roster.officer_ids.remove(ident)
            city.roster.officer_ids.append(ident)
        domestic.on_arrival(game,state,[ident],city.id)
        state.extension['officer_actions'][str(ident)]=state.turn
        logistics._pool(state)['receipts'][str(ident)]=state.turn+logistics.RULES['receipt_turns']
    else:
        domestic._pool(state)['unit_morale'].pop(str(row['escort']),None)
        domestic._pool(state).get('march_spirit',{}).pop(str(row['escort']),None)
    ledger['history'].append(row)
    del ledger['history'][:-HISTORY]
    _observe('terminal',state,tick,chain=row['id'],owner=row['owner'],receipt=row['terminal'],
             balances=row['balances'],books=len(row['paid']),metrics=row['metrics'],
             original_deadline=row['deadline'],actual_arrival=row['arrival'],quoted_net=row['predicted_net'],
             quoted_arrival=row['predicted'])


def _begin_return(game,state,row,tick,backward):
    place=row['at']
    if place is None:
        return
    owner=row['owner']
    if place==row['source']:
        city=state.cities[place]
        if city.owner==owner:
            _finish(game,state,row,tick,city)
            return
    first=next((i for i,s in enumerate(backward) if s.start==place),None)
    blocked='route' if first is None else _access(game,state,dict(row,returning=True),
                                                 place,backward[first].end)
    if blocked:
        if place==row['target'] and state.cities[place].owner==owner:
            city=state.cities[place]
            home=logistics._home(state,row['escort'])
            if (home.id==place or game._city_occupancy(state,city)<game.catalog.rules.city_officer_capacity):
                _finish(game,state,row,tick,city,'received_at_destination')
                return
        row.update(phase='waiting_return',blocked=blocked)
        return
    row.update(phase='returning',returning=True,stage=first,offset=0,blocked=None)
    _observe('return_started',state,tick,chain=row['id'],owner=owner,at=place,stage=first)


def _handle(game,state,row,tick,berths,outward,backward):
    site=row['at']
    account=f"bank{row['stage']}"
    if _site_owner(state,site)!=row['owner']:
        row.update(cancel=True,phase='waiting_return',blocked='permission')
        return False
    if site in berths:
        row['blocked']='queue'
        return False
    moving_on=not row['cancel']
    if row['phase']=='unloading' and moving_on:
        amount=min(row['balances']['cargo'],grain_units.amount(HANDLING))
        berths.add(site)
        _post(state,row,tick,'unload','cargo',account,amount)
        if not row['balances']['cargo']:
            row['phase']='loading'
        row['blocked']=None
        return True
    if moving_on:
        onward=outward[row['stage']+1]
        reason=_access(game,state,row,onward.start,onward.end)
        if reason or any(r[3] for r in _rates(state,onward.parts)):
            row['blocked']=reason or 'frozen'
            return False
    if moving_on and row['stage']+1 not in row['paid']:
        city=state.cities[row['source']]
        if city.owner!=row['owner'] or not command_books.can_spend(state,city.owner,ORDER):
            row['blocked']='books' if city.owner==row['owner'] else 'permission'
            return False
        command_books.spend(state,city,ORDER)
        row['paid'].append(row['stage']+1)
        _observe('book',state,tick,chain=row['id'],owner=row['owner'],city=city.id,
                 stage=row['stage']+1,amount=1)
    available=row['balances'][account]
    amount=min(available,grain_units.amount(HANDLING))
    _post(state,row,tick,'load',account,'cargo',amount)
    if amount:
        berths.add(site)
    if not row['balances'][account]:
        if moving_on:
            row.update(phase='moving',stage=row['stage']+1,offset=0,blocked=None)
        else:
            _begin_return(game,state,row,tick,backward)
    return bool(amount)


def _deliver(state,row,tick):
    city=state.cities[row['target']]
    amount=min(row['balances']['cargo'],logistics.LIMIT-city.grain)
    before=city.grain
    city.grain+=amount
    _post(state,row,tick,'delivery','cargo','delivery',amount,city_delta=[city.id,before,city.grain])
    row['arrival']=tick
    _observe('delivery',state,tick,chain=row['id'],owner=row['owner'],city=city.id,grain=amount,
             original_deadline=row['deadline'],timely=tick<row['deadline'])


def _move(game,state,row,tick,outward,backward):
    stage=(backward if row['returning'] else outward)[row['stage']]
    if not row['offset'] and row['cancel'] and not row['returning']:
        _begin_return(game,state,row,tick,backward)
        return False
    blocked=_access(game,state,row,stage.start,stage.end)
    if blocked:
        row['blocked']=blocked
        return False
    work=row['offset']
    # Nothing moves through a closed reach on its departure day.
    if not work and any(r[3] for r in _rates(state,stage.parts)):
        row['blocked']='frozen'
        return False
    result=winter_travel.day(state,stage.parts,work,rest_region=stage.region,on_leg=bool(work),
                            clear=not winter_weather.movement(state))
    _meal(game,state,row,tick,result.ration)
    cargo=row['balances']['cargo']
    normal,_=rules.cargo_loss(cargo,result.normal_cargo,row['loss_remainder'])
    loss, row['loss_remainder']=rules.cargo_loss(cargo,result.cargo,row['loss_remainder'])
    _post(state,row,tick,'route_loss','cargo','route_loss',min(loss,normal))
    _post(state,row,tick,'weather_loss','cargo','weather_loss',max(0,loss-normal))
    row['offset']+=result.moved
    row['blocked']='frozen' if result.blocked else None
    row['metrics']['travel']+=int(bool(result.moved))
    row['metrics']['waiting']+=int(not result.moved)
    row['metrics']['return_days']+=int(row['returning'])
    _observe('move',state,tick,chain=row['id'],owner=row['owner'],stage=row['stage'],
             start=stage.start,end=stage.end,mode=stage.mode,work=result.moved,offset=row['offset'],
             returning=row['returning'],blocked=row['blocked'])
    if row['offset']==stage.work:
        row['at']=stage.end
        if row['returning']:
            if row['stage']==2:
                _finish(game,state,row,tick,state.cities[stage.end])
            else:
                row.update(stage=row['stage']+1,offset=0)
        elif row['cancel']:
            _begin_return(game,state,row,tick,backward)
        elif row['stage']==2:
            _deliver(state,row,tick)
            _begin_return(game,state,row,tick,backward)
        else:
            row['phase']='unloading'
    elif row['offset']:
        row['at']=None
    return True


def prepare_day(game,state):
    """Immutable directional work is prepared once per active chain/turn."""
    return {row['id']: (sections(game,row['route'],row['source'],row['month']),
                        sections(game,row['route'],row['target'],row['month']))
            for row in jobs(state)}


def advance_day(game,state,tick,prepared):
    ledger=_pool(state)
    if tick<=ledger['clock']:
        return
    berths=set()
    for row in list(jobs(state)):
        outward,backward=prepared[row['id']]
        if tick>=row['deadline'] and row['at']!=row['target'] and not row['returning']:
            row['cancel']=True
        if row['phase'] in ('moving','returning') and _move(game,state,row,tick,outward,backward):
            continue
        if str(row['id']) not in ledger['jobs']:
            continue
        if row['at'] is not None:
            region=_location_region(game,row['at'])
        else:
            span=(backward if row['returning'] else outward)[row['stage']]
            region=span.parts[0].region
        _meal(game,state,row,tick,_wait_rate(state,region))
        if row['phase'] in ('loading','unloading'):
            worked=_handle(game,state,row,tick,berths,outward,backward)
            row['metrics']['handling' if worked else 'waiting']+=1
            _observe('handling' if worked else 'wait',state,tick,chain=row['id'],owner=row['owner'],
                     at=row['at'],stage=row['stage'],blocked=row['blocked'])
        else:
            row['metrics']['waiting']+=1
            if row['phase']=='waiting_return':
                _begin_return(game,state,row,tick,backward)
            _observe('wait',state,tick,chain=row['id'],owner=row['owner'],at=row['at'],
                     stage=row['stage'],blocked=row['blocked'])
    ledger['clock']=tick


def synchronize(game,state):
    if not enabled(state):
        return
    ledger=_pool(state)
    tick=(state.turn-1)*10
    for site,node in ledger['nodes'].items():
        owner=_site_owner(state,site)
        if node['owner']!=owner:
            for key in list(node['lots']):
                row=ledger['jobs'][key]
                account=f"bank{row['banks'].index(site)}"
                seized=row['balances'][account]
                _post(state,row,tick,'seizure',account,'captured',seized)
                node['seized']+=seized
                row.update(cancel=True,blocked='permission')
            _observe('ownership',state,tick,site=site,old_owner=node['owner'],owner=owner,seized=node['seized'])
            node['seized']+=node['unclaimed']
            node['unclaimed']=0
            node['owner']=owner
    for row in list(jobs(state)):
        escort=state.officers.get(row['escort'])
        if not escort or not escort.alive or escort.faction_id!=row['owner'] or logistics._home(state,row['escort']) is None:
            _finish(game,state,row,tick,reason='escort_unavailable')
        elif any(_site_owner(state,b)!=row['owner'] for b in row['banks']):
            row['cancel']=True
    if not ledger['jobs']:
        ledger['clock']=tick


def _direct_offer(game,state,source,target,amount,escort):
    city,destination=state.cities[source],state.cities[target]
    policy=logistics._pool(state)['cities'][source]['policy']
    found=logistics._safe_quote(game,state,city,destination,policy)
    reverse=logistics.convoy_return(game,state,city,destination,policy)
    if found is None or reverse is None:
        return None
    mode,path=found
    rations=logistics.escort_rations(game,state,[escort],path,reverse[1])
    room=_city_budget(state,city,policy)-rations
    if transport_capacity.enabled(state,'physical_capacity'):
        profile=transport_capacity.physical(game,state,path)
        room=min(room,profile['physical_capacity']-rations)
    cargo=min(amount,room,policy['max_grain'])
    if cargo<=0:
        return None
    days=winter_travel.quote_days(game,state,path)
    return dict(mode=mode,path=path['path'],net=logistics.projected_grain(game,path,cargo,state=state),
                eta=(state.turn-1)*10+rules.ceil_div(days,10)*10,books=1,rations=rations,
                officer_days=rules.ceil_div(days,10)*10+winter_travel.quote_days(game,state,reverse[1]))


def consider_ai(game,state,owner):
    """Use spare orders after current military, market and relief policies.

    A more expensive service must cover timely grain that no normal direct
    quote can cover. A reservation is not recognized as a final delivery.
    """
    owned=[(route,origin,target) for route,raw in game.catalog.infrastructure_routes.items()
           for origin,target in ((raw['from'],raw['to']),(raw['to'],raw['from']))
           if origin in state.cities and target in state.cities
           and state.cities[origin].owner==state.cities[target].owner==owner
           and logistics._pool(state)['cities'][origin]['policy']['enabled']]
    if not owned or not command_books.can_spend(state,owner,ORDER):
        return False
    from . import faction_economy, granary_demand
    plan=faction_economy.plan(game,state,owner,granary=True)
    absent=game._march_ids(state)
    now=(state.turn-1)*10
    for route,source,target in owned:
        demand=granary_demand.for_city(game,state,plan,target)
        if not demand.remaining:
            continue
        first,need=demand.remaining[0]
        amount=min(need,grain_units.amount(STORAGE))
        deadline=now+10*first
        offer=quote(game,state,owner,route,source,[amount],deadline,absent=absent,automatic=True)
        direct=None if offer['blocked'] else _direct_offer(game,state,source,target,amount,offer['escort'])
        safe_stock=(not offer['blocked'] and offer['requested']+offer['rations']<=plan.budgets[source]['exportable'])
        selected=safe_stock and offer['net']>0 and (
            direct is None or direct['eta']>=deadline or direct['net']<offer['net'])
        _observe('choice',state,now,owner=owner,source=source,target=target,route=route,
                 selected=bool(selected),relay=offer,direct=direct,
                 reason=offer['blocked'] or ('source_safety' if not safe_stock else
                                               'timely_additional_grain' if selected else 'prefer_direct'))
        if selected:
            execute(game,state,dict(action='dispatch',id=_pool(state)['next_id'],route=route,
                                    source=source,batches=[amount],deadline=deadline,
                                    escort=offer['escort']),owner)
            return True
    return False


def view(game,state,owner):
    ledger=_pool(state)
    now=(state.turn-1)*10
    nodes=[]
    offers=[]
    active=list(jobs(state))
    for route,raw in game.catalog.infrastructure_routes.items():
        for origin in (raw['from'], raw['to']):
            target,banks=_bounds(raw,CORRIDORS[route],origin)
            if origin not in state.cities or state.cities[origin].owner!=owner:
                continue
            size=min(grain_units.amount(HANDLING),state.cities[origin].grain)
            offers.append(dict(route=route,source=origin,target=target,banks=list(banks),grain=max(1,size)))
    for key,node in ledger['nodes'].items():
        anchor,geometry,position,zh,ja=SITES[key]
        present=[row for row in active if row['at']==key]
        reaches=[reach for raw in game.catalog.infrastructure_routes.values()
                 if key in CORRIDORS[raw['id']] for reach in raw['river_segments']]
        ice=state.extension.get(winter_weather.POOL,{}).get('ice',{})
        if anchor not in state.cities:
            status='inactive'
        elif not any(route_network.available(raw,state.year,state.month) for route,raw in
                     game.catalog.infrastructure_routes.items() if key in CORRIDORS[route]):
            status='road_closed'
        elif node['owner']=='neutral':
            status='permission'
        elif any(ice.get(r['reach_id'],{}).get('state')==3 for r in reaches):
            status='frozen'
        elif _stock(node)>=grain_units.amount(STORAGE):
            status='storage'
        elif not present:
            status='no_staff'
        else:
            status='working'
        nodes.append(dict(id=key,anchor=anchor,geometry=geometry,position=list(position),
                          name_tc=zh,name_ja=ja,type='river_wharf',owner=node['owner'],
                          grain=_stock(node),capacity=grain_units.amount(STORAGE),
                          promised=_reserved(state,key),unclaimed=node['unclaimed'],
                          seized=node['seized'],throughput=grain_units.amount(HANDLING),berths=1,
                          staff=[row['escort'] for row in present],queue=max(0,len(present)-1),status=status))
    orders=[deepcopy(row) for row in (*active,*reversed(ledger['history'])) if row['owner']==owner]
    for row in orders:
        del row['prefix']
        row['events']=row['events'][-12:]
    return dict(version=VERSION,nodes=nodes,offers=offers,jobs=orders,next_id=ledger['next_id'],day=now,
                capacity=grain_units.amount(STORAGE),marching_officers=[row['escort'] for row in active],
                order_costs=dict(dispatch=command_books.cost(ORDER),cancel=0))


_JOB_FIELDS = {'id','route','source','target','banks','owner','escort','created','month','deadline',
               'predicted','predicted_net','requested','phase','stage','offset','at','returning','cancel',
               'blocked','parcels','paid','serial','credit','loss_remainder','events','terminal',
               'arrival','prefix','balances','metrics','hunger_streak'}
_EVENT_FIELDS = {'serial','tick','kind','source','target','grain','before','after','parents','city_delta'}
_METRICS = {'travel','handling','waiting','return_days','hunger_days','hunger_losses'}
_BLOCKERS = {None,'storage','books','direction','route','queue','frozen','permission','road_closed'}


def _bounded(value, low=0, high=logistics.LIMIT):
    if not logistics._int(value,low,high):
        raise ValueError('Wharf numeric value')


def _amounts(value):
    if not isinstance(value,dict) or set(value)!=set(BALANCES):
        raise ValueError('Wharf ledger accounts')
    for n in value.values():
        _bounded(n)
    if sum(value[k] for k in BALANCES[1:])!=value['input']:
        raise ValueError('Wharf grain must reconcile')


def _parcels(parcels, serial, expected):
    if not isinstance(parcels,list) or len(parcels)>24:
        raise ValueError('Wharf lot count')
    ids=set()
    total=0
    for ident,amount in parcels:
        _bounded(ident,1,serial)
        _bounded(amount,1)
        if ident in ids:
            raise ValueError('Duplicate wharf lot')
        ids.add(ident)
        total+=amount
    if total!=expected:
        raise ValueError('Wharf physical stock missing')
    return ids


def _validate_events(job,now):
    baseline=job['prefix']
    balances=job['balances']
    _amounts(balances)
    _amounts(baseline)
    events=job['events']
    if not isinstance(events,list) or not 1<=len(events)<=LEDGER_ROWS:
        raise ValueError('Wharf postings')
    _bounded(job['serial'],len(events),1_000_000)
    if job['serial']==len(events) and any(baseline.values()):
        raise ValueError('Unexpected wharf prefix')
    calculated=dict(baseline)
    day=job['created']
    remaining={}
    for i,e in enumerate(events,job['serial']-len(events)+1):
        if not isinstance(e,dict) or set(e)!=_EVENT_FIELDS or type(e['serial']) is not int or e['serial']!=i:
            raise ValueError('Wharf posting identity')
        _bounded(e['tick'],day,now)
        day=e['tick']
        source,target=e['source'],e['target']
        if (source,target) not in TRANSFERS.get(e['kind'],()) or e['before']!=[calculated[source],calculated[target]]:
            raise ValueError('Wharf custody posting')
        amount=e['grain']
        _bounded(amount,1)
        _apply(calculated,source,target,amount)
        if e['after']!=[calculated[source],calculated[target]]:
            raise ValueError('Wharf custody receipt')
        parents=e['parents']
        _parcels(parents,i-1,amount if source in CARGO else 0)
        for ident,used in parents:
            prior=remaining.get(ident)
            if prior is None:
                if ident>job['serial']-len(events):
                    raise ValueError('Wharf parent lot not found')
            elif prior[0]!=source or used>prior[1]:
                raise ValueError('Wharf parent lot already consumed')
            else:
                remaining[ident]=(source,prior[1]-used)
        if target in CARGO:
            remaining[i]=(target,amount)
        delta=e['city_delta']
        if source=='input' or target in ('delivery','returned'):
            if not isinstance(delta,list) or len(delta)!=3:
                raise ValueError('Wharf external account missing')
            where,opening,closing=delta
            _bounded(opening)
            _bounded(closing)
            location=job['source'] if source=='input' else job['target'] if target=='delivery' else job['terminal']['city']
            if where!=location or closing-opening!=(-amount if source=='input' else amount):
                raise ValueError('Wharf external account difference')
        elif delta is not None:
            raise ValueError('Wharf unexpected city posting')
    if calculated!=balances:
        raise ValueError('Wharf ledger balance')
    return remaining


def validate(game,state):
    if FIELD not in state.extension and POOL not in state.extension:
        return
    if (type(state.extension.get(FIELD)) is not int or state.extension[FIELD]!=VERSION
            or rules.version(state)!=rules.CURRENT):
        raise ValueError('Wharf version')
    ledger=state.extension[POOL]
    now=(state.turn-1)*10
    if not isinstance(ledger,dict) or set(ledger)!={'nodes','jobs','history','next_id','clock'} or ledger['clock']!=now:
        raise ValueError('Wharf daily cursor')
    _bounded(ledger['next_id'],1,1_000_001)
    nodes=ledger['nodes']
    active=ledger['jobs']
    history=ledger['history']
    expected={bank for route in game.catalog.infrastructure_routes for bank in CORRIDORS[route]}
    if (not isinstance(nodes,dict) or set(nodes)!=expected or not isinstance(active,dict)
            or len(active)>MAX_PLANS or not isinstance(history,list) or len(history)>HISTORY):
        raise ValueError('Wharf entities or capacity')
    for key,node in nodes.items():
        if (not isinstance(node,dict) or set(node)!={'owner','seized','unclaimed','lots'} or node['owner']!=_site_owner(state,key)
                or not isinstance(node['lots'],dict) or not node['lots'].keys()<=active.keys()):
            raise ValueError('Wharf ownership or stock keys')
        _bounded(node['seized'],0,grain_units.amount(STORAGE))
        _bounded(node['unclaimed'],0,grain_units.amount(STORAGE))
        if any(key not in active[ident]['banks'] for ident in node['lots']):
            raise ValueError('Wharf stock stored at an unrelated location')
    from . import battle_reinforcements, transshipment
    used=logistics.marching_ids(state) | battle_reinforcements.marching_ids(state)
    used.update(o for row in state.extension['travel']['marches'] for o in row['officers'])
    used.update(u['id'] for side in ('attackers','defenders') for u in (state.battle or {}).get(side,[]))
    plans=[*active.values(),*transshipment._plans(state).values()]
    if len(plans)>MAX_PLANS or max(Counter(p['owner'] for p in plans).values(),default=0)>PER_OWNER:
        raise ValueError('Combined transshipment plan bound')
    identities=set()
    occupied=Counter()
    for job in (*active.values(),*history):
        if not isinstance(job,dict) or set(job)!=_JOB_FIELDS:
            raise ValueError('Wharf order fields')
        ident=job['id']
        _bounded(ident,1,ledger['next_id']-1)
        if ident in identities:
            raise ValueError('Duplicate wharf order')
        identities.add(ident)
        raw=game.catalog.infrastructure_routes[job['route']]
        if job['source'] not in (raw['from'],raw['to']) or job['owner'] not in game.catalog.factions or job['owner']=='neutral':
            raise ValueError('Wharf order origin')
        target,banks=_bounds(raw,CORRIDORS[job['route']],job['source'])
        if job['target']!=target or job['banks']!=list(banks):
            raise ValueError('Wharf route endpoints')
        for key,lo,hi in (('created',0,now),('month',1,12),('deadline',job['created']+1,job['created']+MAX_DEADLINE_DAYS),
                          ('requested',1,grain_units.amount(STORAGE)),('predicted_net',0,job['requested']),
                          ('predicted',job['created']+1,job['deadline']-1),('stage',0,2),
                          ('credit',0,grain_units.denominator()*rules.RATION_SCALE-1),
                          ('loss_remainder',0,rules.LOSS_SCALE-1),('hunger_streak',0,now-job['created'])):
            _bounded(job[key],lo,hi)
        if (any(type(job[key]) is not bool for key in ('cancel','returning')) or job['blocked'] not in _BLOCKERS
                or not isinstance(job['paid'],list) or not 1<=len(job['paid'])<=3
                or any(type(stage) is not int for stage in job['paid'])
                or job['paid']!=list(range(len(job['paid'])))
                or set(job['metrics'])!=_METRICS):
            raise ValueError('Wharf flags and costs')
        for amount in job['metrics'].values():
            _bounded(amount)
        if job['arrival'] is not None:
            _bounded(job['arrival'],job['created']+1,now)
        leg=sections(game,job['route'],job['target'] if job['returning'] else job['source'],job['month'])[job['stage']]
        _bounded(job['offset'],0,leg.work)
        if job['at'] is not None and job['at'] not in (job['source'],job['target'],*banks):
            raise ValueError('Wharf location')
        finished=job['phase']=='closed'
        if finished:
            if str(ident) in active or not isinstance(job['terminal'],dict) or set(job['terminal'])!={'tick','city','reason'}:
                raise ValueError('Wharf terminal')
            _bounded(job['terminal']['tick'],job['created'],now)
            if job['terminal']['reason'] not in ('returned','received_at_destination','escort_unavailable'):
                raise ValueError('Wharf outcome')
        else:
            officer=state.officers.get(job['escort'])
            if (str(ident) not in active or job['terminal'] is not None or job['phase'] not in ACTIVE
                    or job['escort'] in used or not officer or not officer.alive or officer.faction_id!=job['owner']
                    or logistics._home(state,job['escort']) is None):
                raise ValueError('Wharf escort occupancy')
            used.add(job['escort'])
            occupied[transport_capacity.origin_key(state,job['source'],job['owner'])]+=1
            if job['phase'] in ('unloading','loading') and (
                    job['returning'] or job['stage'] not in (0,1) or job['at']!=banks[job['stage']]
                    or job['offset']!=leg.work):
                raise ValueError('Wharf loading location')
            if job['phase'] in ('moving','returning') and (
                    (job['phase']=='returning')!=job['returning'] or job['offset']>=leg.work or job['at']!=(None if job['offset'] else leg.start)):
                raise ValueError('Wharf movement position')
        if finished and any(job['balances'][k] for k in (*CARGO,'rations')):
            raise ValueError('Wharf terminal retains spendable stock')
        if ((job['balances']['delivery'] and job['arrival'] is None)
                or job['balances']['input'] < job['requested']):
            raise ValueError('Wharf arrival before physical delivery')
        latest=_validate_events(job,now)
        all_lots=set()
        for account in CARGO:
            available=_lot_map(state,job,account)
            ids=_parcels(available,job['serial'],job['balances'][account])
            if all_lots & ids:
                raise ValueError('Wharf lot stored at two locations')
            all_lots.update(ids)
            if any(lot in latest and latest[lot]!=(account,amount) for lot,amount in available):
                raise ValueError('Wharf live lot receipt')
    slots=transport_capacity.activity(state)
    if any(slots[k]>transport_capacity.active_limit(state) for k in occupied):
        raise ValueError('Wharf shared city slots')
    for key,node in nodes.items():
        if (_stock(node)>grain_units.amount(STORAGE) or
                node['seized']+node['unclaimed']+_reserved(state,key)>grain_units.amount(STORAGE)):
            raise ValueError('Wharf storage or capacity reservation')
