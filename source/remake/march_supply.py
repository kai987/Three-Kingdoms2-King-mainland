"""Deterministic daily food, real checkpoints and auditable starvation."""
from copy import deepcopy
from . import logistics_rules as rules
from .grain_units import denominator
from .historical_campaigns import transit_allowed
from .officers import OFFICER_TROOP_CAP

OFFICER_UNITS=100
LIMIT=100000000
MAX_DAILY_UNITS=LIMIT+99*(OFFICER_TROOP_CAP+OFFICER_UNITS)
MAX_TRAVELLING_SOLDIERS=LIMIT+99*OFFICER_TROOP_CAP
SCHEMA='tk2-segment-supply-v2'
WEIGHTED_SCHEMA='tk2-segment-supply-v3'
RETREAT_DAYS=10
_FIELDS={'schema','troops','officers','reserves','elapsed_days','route_days','loaded','received',
 'consumed','remaining','from_cargo','returned_to_cargo','credit_units','start_tick','clock_tick',
 'closed_tick','last_turn','waiting','shortage_days','shortage_streak','lost','retreat_requested',
 'refills','starvation','periods','ration_manifests'}
_WEIGHTED_FIELDS={'initial_credit','base_consumed'}


def cost(troops,officers,days,reserves=0):
    return ((troops+100*officers+reserves)*days + denominator() - 1)//denominator()


required_grain=cost


def book_version(supply):
    return rules.CURRENT if supply['schema']==WEIGHTED_SCHEMA else rules.LEGACY


def book_denominator(supply):
    return denominator() * (rules.RATION_SCALE if book_version(supply)==rules.CURRENT else 1)


def travel_rules(game):
    return game.catalog.data.get('travel_rules', {}) if game is not None else {}


def ration_units(state, ids, reserves=0):
    return sum(state.officers[i].troops for i in ids) + OFFICER_UNITS * len(ids) + reserves


def route_weight(quote, days, *, offset=0, game=None, version=rules.LEGACY):
    if version==rules.LEGACY:
        return days
    return rules.weight(rules.plan(quote, travel_rules(game)), offset, days)


def quote_supply(quote,total_troops,officer_count,reserves=0,*,game=None,version=rules.LEGACY,days=None):
    days=quote['days'] if days is None else days
    denominator_units=denominator() * (rules.RATION_SCALE if version==rules.CURRENT else 1)
    return rules.ceil_div((total_troops + OFFICER_UNITS*officer_count + reserves) *
                          route_weight(quote,days,game=game,version=version),denominator_units)


def next_supply_days(state,quote,owner,route_days=0):
    if 'routes' not in quote:return max(0,quote['days']-route_days)
    total=0
    for index,leg in enumerate(quote['routes']):
        total+=leg['days']
        if total>route_days and (state.cities[quote['path'][index+1]].owner==owner
                                or index==len(quote['routes'])-1):
            return total-route_days
    return 0


def initial_days(state,quote,owner=None):
    if 'path' not in quote:return quote['days']
    return next_supply_days(state,quote,owner or state.cities[quote['path'][0]].owner)


def estimate(state,ids,quote,reserves=0,*,game=None,version=None):
    version=rules.version(state) if version is None else version
    return quote_supply(quote,sum(state.officers[i].troops for i in ids),len(ids),reserves,
                        version=version,game=game,days=initial_days(state,quote))


def remaining_requirement(game,state,journey,*,minimum_days=0,reserves=0):
    supply,quote=journey['supply'],journey['quote']
    progress=supply['route_days']
    days=next_supply_days(state,quote,journey['owner'],progress)
    version=book_version(supply)
    unit_scale=rules.RATION_SCALE if version==rules.CURRENT else 1
    travel_weight=route_weight(quote,days,offset=progress,game=game,version=version)
    travel_weight+=max(0,minimum_days-days)*unit_scale
    # Legacy rescue dispatches used the whole quoted ration even when the
    # receiving column already had fractional credit in its own bag.
    credit=supply['credit_units'] if version==rules.CURRENT else 0
    return max(0,rules.ceil_div(ration_units(state,journey['officers'],reserves)*travel_weight-credit,
                               book_denominator(supply)))


def create(state,ids,quote,reserves=0,*,game=None,from_cargo=False,initial_grain=None,previous=None,credit=0):
    version=rules.version(state) if previous is None else book_version(previous)
    loaded=estimate(state,ids,quote,reserves,game=game,version=version) if initial_grain is None else initial_grain
    tick=(state.turn-1)*10
    supply=dict(schema=SCHEMA,troops=sum(state.officers[i].troops for i in ids),officers=len(ids),
        reserves=reserves,elapsed_days=0,route_days=0,loaded=loaded,received=0,consumed=0,
        remaining=loaded,from_cargo=loaded if from_cargo else 0,returned_to_cargo=0,credit_units=0,
        start_tick=tick,clock_tick=tick,closed_tick=None,last_turn=state.turn,waiting=False,
        shortage_days=0,shortage_streak=0,lost=0,retreat_requested=False,refills=[],starvation=[],periods=[],
        ration_manifests=[dict(tick=tick+1,troops={str(i):state.officers[i].troops for i in ids},reserves=reserves)])
    if version==rules.CURRENT:
        credit=previous['credit_units'] if previous else credit
        supply.update(schema=WEIGHTED_SCHEMA,credit_units=credit,initial_credit=credit,base_consumed=0)
    return supply


def current_city(journey):
    progress=journey['supply']['route_days']
    if progress==0:return journey['quote']['path'][0]
    total=0
    for index,leg in enumerate(journey['quote']['routes']):
        total+=leg['days']
        if progress==total:return journey['quote']['path'][index+1]
        if progress<total:return None
    return journey['quote']['path'][-1] if progress==journey['quote']['days'] else None


def next_city(journey):
    total=0
    for index,leg in enumerate(journey['quote']['routes']):
        total+=leg['days']
        if total>journey['supply']['route_days']:return journey['quote']['path'][index+1]
    return None


def last_city(journey):
    total=0;found=journey['quote']['path'][0]
    for index,leg in enumerate(journey['quote']['routes']):
        total+=leg['days']
        if total>journey['supply']['route_days']:break
        found=journey['quote']['path'][index+1]
    return found


def receive(supply,grain,source_kind,source_id,turn):
    if type(grain)is not int or grain<0 or source_kind not in {'city','convoy','cargo'}:
        raise ValueError('Invalid ration delivery')
    if not grain:return 0
    if supply['closed_tick'] is not None or supply['remaining']+grain>LIMIT:
        raise ValueError('Closed or overflowing ration inventory')
    supply['received']+=grain;supply['remaining']+=grain
    supply['refills'].append(dict(tick=supply['clock_tick'],turn=turn,kind=source_kind,
                                  source=source_id,grain=grain))
    return grain


def close(supply,turn):
    supply['closed_tick']=(turn-1)*10


def _meal(supply,units,weighted=None):
    divisor=book_denominator(supply)
    charge=units if weighted is None else units*weighted
    prior=supply['credit_units']
    used=min(supply['remaining'],rules.ceil_div(max(0,charge-prior),divisor))
    available=prior+used*divisor
    missing=max(0,charge-available)
    if weighted is not None:
        basic=units*rules.RATION_SCALE
        supply['base_consumed']+=min(used,rules.ceil_div(max(0,basic-prior),divisor))
    supply['credit_units']=max(0,available-charge)
    supply['remaining']-=used;supply['consumed']+=used;supply['elapsed_days']+=1
    if missing:
        supply['shortage_days']+=1;supply['shortage_streak']+=1
        if supply['shortage_streak']>=RETREAT_DAYS:supply['retreat_requested']=True
    else:supply['shortage_streak']=0
    return used,missing


def _record(supply,tick,meal):
    turn=(tick-1)//10+2
    if not supply['periods'] or supply['periods'][-1]['turn']!=turn:
        supply['periods'].append(dict(turn=turn,days=[]))
    supply['periods'][-1]['days'].append(meal)
    supply['clock_tick']=tick;supply['last_turn']=tick//10+1


def _completion_tick(supply,days):
    """The physical arrival day, independent of a mutable waiting flag."""
    if days==0:return supply['start_tick']
    progress=0
    for index,period in enumerate(supply['periods']):
        for offset,meal in enumerate(period['days']):
            if meal is not None:progress+=meal[2]
            if progress>=days:return supply['start_tick']+index*10+offset+1
    return None


def advance_unit(game,state,unit,journey,through_turn=None,*,unit_kind='march',cargo=None,
                 on_cargo_change=None,on_cargo_day=None,absolute_tick=None,parts=None):
    supply=journey['supply'];quote=journey['quote']
    target=absolute_tick if absolute_tick is not None else ((through_turn or state.turn)-1)*10
    if supply['closed_tick'] is not None:return 0
    weighted=book_version(supply)==rules.CURRENT
    if weighted and parts is None:
        parts=rules.plan(quote,travel_rules(game))
    divisor=book_denominator(supply)
    spent=0
    for tick in range(supply['clock_tick']+1,target+1):
        if supply['route_days']>=quote['days'] and not supply['waiting']:
            arrived=_completion_tick(supply,quote['days'])
            if arrived is not None and tick<=((arrived+9)//10)*10:
                _record(supply,tick,None);continue
            # A unit still queued in a later ten-day period is waiting even
            # if its arrival handler has not yet marked it explicitly.
            supply['waiting']=True
        ids=[i for i in unit['officers'] if i in state.officers and state.officers[i].alive
             and state.officers[i].faction_id==unit['owner']]
        troops=sum(state.officers[i].troops for i in ids)
        reserves=cargo['reserves'] if cargo is not None else 0
        units=troops+100*len(ids)+reserves
        manifest=dict(tick=tick,troops={str(i):state.officers[i].troops for i in ids},reserves=reserves)
        previous=supply['ration_manifests'][-1]
        if previous['troops']!=manifest['troops'] or previous['reserves']!=reserves:
            if previous['tick'] == tick:
                # The scheduled first meal can follow a roster change in the
                # departure turn. Keep one meal manifest for that day.
                supply['ration_manifests'][-1] = manifest
            else:
                supply['ration_manifests'].append(manifest)
        city_id=current_city(journey)
        progress=supply['route_days']
        distance=next_supply_days(state,quote,unit['owner'],supply['route_days'])
        if weighted:
            leg_budget=rules.weight(parts,progress,distance)
            budget=leg_budget or (10 if progress>=quote['days'] else 1)*rules.RATION_SCALE
        else:
            leg_budget=distance
            budget=10 if progress>=quote['days'] else max(1,distance)
        wanted=max(0,rules.ceil_div(units*budget-supply['credit_units'],divisor)-supply['remaining'])
        if wanted and city_id and state.cities[city_id].owner==unit['owner']:
            city=state.cities[city_id];amount=min(wanted,city.grain,LIMIT-supply['remaining'])
            if amount:
                city.grain-=amount;receive(supply,amount,'city',city_id,state.turn);wanted-=amount
                # At most one combined city receipt event per unit/city/turn.
                game._supply_event(state,'march_resupplied',unit_kind=unit_kind,unit_id=unit['id'],
                    city=city_id,owner=unit['owner'],grain=amount,lost=0,
                    shortage_days=supply['shortage_streak'],reason='city')
        if wanted and cargo is not None and cargo['grain']:
            amount=min(wanted,cargo['grain'],LIMIT-supply['remaining'])
            if on_cargo_change is None:raise ValueError('Cargo ration debit needs its transport ledger')
            on_cargo_change('rations',dict(cargo,grain=cargo['grain']-amount),tick)
            receive(supply,amount,'cargo',unit['id'],state.turn)
        upcoming = next_city(journey) if city_id is not None else None
        blocked=(upcoming is not None and upcoming!=quote['path'][-1]
                 and not transit_allowed(state,unit['owner'],state.cities[upcoming].owner))
        if blocked:supply['retreat_requested']=True;unit['reason']='route_blocked'
        enough=supply['remaining']*divisor+supply['credit_units']>=units*leg_budget
        moving=(supply['route_days']<quote['days'] and not blocked and not unit.get('hold')
                and not (supply['retreat_requested'] and city_id is not None and unit.get('status')!='returning')
                and (city_id is None or enough or unit.get('status')=='returning'))
        moving_or_on_leg=moving or city_id is None
        rate=rules.weight(parts,progress,1) if weighted and moving_or_on_leg else (
            rules.RATION_SCALE if weighted else None)
        used,missing=_meal(supply,units,rate);spent+=used
        if moving:supply['route_days']+=1
        supply['waiting']=(not moving and supply['route_days']<quote['days']) or (
            supply['waiting'] and supply['route_days']>=quote['days'])
        if missing:
            before={str(i):state.officers[i].troops for i in ids}
            after={key:max(0,n-(n+99)//100) for key,n in before.items()}
            for ident in ids:state.officers[ident].troops=after[str(ident)]
            reserve_after=max(0,reserves-(reserves+99)//100)
            lost=sum(before.values())-sum(after.values())+reserves-reserve_after
            if cargo is not None and reserve_after!=reserves:
                if on_cargo_change is None:raise ValueError('Cargo hunger needs its transport ledger')
                on_cargo_change('starvation',dict(cargo,reserves=reserve_after),tick)
            supply['starvation'].append(dict(tick=tick,
                after_risks=sum(bool(r['applied']) for r in journey.get('risks',[])),
                before=before,after=after,reserves_before=reserves,reserves_after=reserve_after,lost=lost))
            supply['lost']+=lost;state.soldiers['lost']+=lost
        if on_cargo_day is not None and weighted and moving_or_on_leg:
            on_cargo_day(rules.weight(parts,progress,1,rates=rules.CARGO_GRAIN_LOSS_BPS),tick)
        _record(supply,tick,[units,used,int(moving),missing])
        if tick%10==0:
            recent=[r for r in supply['starvation'] if tick-10<r['tick']<=tick]
            if recent:
                game._supply_event(state,'march_starvation',unit_kind=unit_kind,unit_id=unit['id'],
                    city=current_city(journey) or last_city(journey),owner=unit['owner'],grain=0,
                    lost=sum(r['lost'] for r in recent),shortage_days=max(1,supply['shortage_streak']),reason='shortage')
    return spent


def consume(supply,departure_turn,quote,through_turn,*,game=None):
    """Pure meal-rounding helper; gameplay uses the shared daily service."""
    spent=0
    parts=rules.plan(quote,travel_rules(game)) if book_version(supply)==rules.CURRENT else None
    for tick in range(supply['clock_tick']+1,(through_turn-1)*10+1):
        if supply['route_days']>=quote['days']:_record(supply,tick,None);continue
        units=supply['troops']+100*supply['officers']+supply['reserves']
        rate=rules.weight(parts,supply['route_days'],1) if parts is not None else None
        used,missing=_meal(supply,units,rate);supply['route_days']+=1;spent+=used
        _record(supply,tick,[units,used,1,missing])
    return spent


def process_march_supply(game,state,through_turn=None):
    through_turn=state.turn if through_turn is None else through_turn;target=(through_turn-1)*10
    rows=state.extension.get('travel',{}).get('marches',[])
    convoys=state.extension.get('logistics',{}).get('convoys',[])
    clocks=[r['supply']['clock_tick'] for r in rows]+[r['journeys'][-1]['supply']['clock_tick'] for r in convoys]
    if not clocks or min(clocks)>=target:return 0
    used=0
    from . import logistics
    plans={}
    def plan_for(journey):
        if book_version(journey['supply'])!=rules.CURRENT:
            return None
        key=id(journey)
        if key not in plans:
            plans[key]=rules.plan(journey['quote'],travel_rules(game))
        return plans[key]
    for tick in range(min(clocks)+1,target+1):
        for row in list(rows):
            if row['supply']['clock_tick']<tick:
                used+=advance_unit(game,state,row,row,through_turn,absolute_tick=tick,parts=plan_for(row))
        for row in list(convoys):
            if row['journeys'][-1]['supply']['clock_tick']<tick:
                used+=logistics.advance_supply(game,state,row,through_turn,absolute_tick=tick,
                                              parts=plan_for(row['journeys'][-1]))
        logistics.rendezvous(game,state,tick=tick)
    for row in rows:
        remaining=row['quote']['days']-row['supply']['route_days']
        row['arrival_turn']=through_turn+max(1,(remaining+9)//10) if remaining else through_turn
    return used


def validate(supply,quote,departure_turn,state_turn,*,game=None,version=None):
    if not isinstance(supply,dict) or supply.get('schema') not in (SCHEMA,WEIGHTED_SCHEMA):
        raise ValueError('Segment supply fields')
    actual_version=book_version(supply)
    weighted=actual_version==rules.CURRENT
    fields=_FIELDS | _WEIGHTED_FIELDS if weighted else _FIELDS
    if set(supply)!=fields or version is not None and actual_version!=version:
        raise ValueError('Segment supply fields or rules')
    divisor=book_denominator(supply)
    max_missing=MAX_DAILY_UNITS * (max(rules.MARCH_SUPPLY_PERCENT.values())*rules.DAY_TICKS if weighted else 1)
    parts=rules.plan(quote,travel_rules(game)) if weighted else None
    nodes={}
    if 'path' in quote:
        nodes[0]=quote['path'][0]
        distance=0
        for index,leg in enumerate(quote['routes']):
            distance+=leg['days'];nodes[distance]=quote['path'][index+1]
    numbers=fields-{'schema','waiting','retreat_requested','refills','starvation','periods','closed_tick','ration_manifests'}
    if any(type(supply[k])is not int or not 0<=supply[k]<=
           (MAX_TRAVELLING_SOLDIERS if k=='lost' else LIMIT) for k in numbers):
        raise ValueError('Segment supply integers')
    if any(type(supply[k])is not bool for k in ('waiting','retreat_requested')):
        raise ValueError('Segment supply flags')
    closed=supply['closed_tick']
    if closed is not None and (type(closed)is not int or not supply['start_tick']<=closed<=(state_turn-1)*10):
        raise ValueError('Segment supply closed clock')
    end=(state_turn-1)*10 if closed is None else closed
    if (supply['start_tick']!=(departure_turn-1)*10 or supply['clock_tick']!=end
        or supply['last_turn']!=end//10+1 or supply['credit_units']>=divisor
        or supply.get('initial_credit',0)>=divisor
        or supply['route_days']>quote['days'] or supply['officers']>99
        or supply['troops']>supply['officers']*OFFICER_TROOP_CAP or supply['from_cargo']>supply['loaded']):
        raise ValueError('Segment supply clock or manifest')
    refills=supply['refills']
    if not isinstance(refills,list) or len(refills)>100000:raise ValueError('Segment supply refill list')
    for row in refills:
        if (not isinstance(row,dict) or set(row)!={'tick','turn','kind','source','grain'}
            or type(row['tick'])is not int or not supply['start_tick']<=row['tick']<=end
            or type(row['turn'])is not int or not 1<=row['turn']<=state_turn
            or row['kind'] not in {'city','convoy','cargo'} or type(row['source']) not in (str,int)
            or type(row['grain'])is not int or not 1<=row['grain']<=LIMIT):
            raise ValueError('Segment supply refill receipt')
    periods=supply['periods']
    if not isinstance(periods,list) or len(periods)!=(end-supply['start_tick'])//10:
        raise ValueError('Segment supply service periods')
    manifests=supply['ration_manifests']
    if not isinstance(manifests,list) or not manifests or len(manifests)>100000:
        raise ValueError('Segment ration manifests')
    previous_tick=supply['start_tick']
    for manifest in manifests:
        if (not isinstance(manifest,dict) or set(manifest)!={'tick','troops','reserves'}
            or type(manifest['tick'])is not int or not previous_tick<manifest['tick']<=max(end,supply['start_tick']+1)
            or not isinstance(manifest['troops'],dict) or len(manifest['troops'])>99
            or any(not isinstance(k,str) or type(v)is not int or not 0<=v<=OFFICER_TROOP_CAP for k,v in manifest['troops'].items())
            or type(manifest['reserves'])is not int or not 0<=manifest['reserves']<=LIMIT):
            raise ValueError('Segment ration manifest fields')
        previous_tick=manifest['tick']
    if manifests[0]['tick']!=supply['start_tick']+1:
        raise ValueError('Segment initial ration clock')
    elapsed=progress=paid=base_paid=shortage=streak=manifest_index=0;hungry_ticks=[]
    credit=supply.get('initial_credit',0)
    inventory=supply['loaded'];receipt_index=0
    ordered=sorted(refills,key=lambda r:r['tick'])
    positions={supply['start_tick']:0}
    completed=supply['start_tick'] if quote['days']==0 else None
    for index,period in enumerate(periods):
        if (not isinstance(period,dict) or set(period)!={'turn','days'}
            or period['turn']!=departure_turn+index+1 or not isinstance(period['days'],list) or len(period['days'])!=10):
            raise ValueError('Segment supply period clock')
        for offset,meal in enumerate(period['days']):
            tick=supply['start_tick']+index*10+offset+1
            # A receipt at day N is available for day N+1. This covers both
            # city top-ups before a meal and rendezvous after that day's move.
            while receipt_index<len(ordered) and ordered[receipt_index]['tick']<tick:
                inventory+=ordered[receipt_index]['grain'];receipt_index+=1
            if meal is None:
                if (completed is None or tick>((completed+9)//10)*10):
                    raise ValueError('Travelling or waiting unit skipped its daily meal')
                positions[tick]=progress
                continue
            if (not isinstance(meal,list) or len(meal)!=4
                    or any(type(n)is not int or not 0<=n<=bound
                           for n,bound in zip(meal,(MAX_DAILY_UNITS,LIMIT,1,max_missing)))):
                raise ValueError('Segment supply daily meal')
            units,used,moved,missing=meal
            charge=units
            if weighted:
                rate=rules.weight(parts,progress,1) if moved or nodes and progress not in nodes else rules.RATION_SCALE
                charge*=rate
                base_paid+=min(used,rules.ceil_div(max(0,units*rules.RATION_SCALE-credit),divisor))
            balance=credit+used*divisor-charge+missing
            while manifest_index+1<len(manifests) and manifests[manifest_index+1]['tick']<=tick:
                manifest_index+=1
            actual=manifests[manifest_index]
            if units!=sum(actual['troops'].values())+100*len(actual['troops'])+actual['reserves']:
                raise ValueError('Segment ration units do not match travelling people')
            if moved not in (0,1) or missing>charge or not 0<=balance<divisor or missing and balance:
                raise ValueError('Segment supply meal arithmetic')
            if used>inventory:raise ValueError('Meal spent grain before it was delivered')
            inventory-=used
            credit=balance;elapsed+=1;progress+=moved;paid+=used
            positions[tick]=progress
            if progress>quote['days']:raise ValueError('Daily movement passed the destination')
            if progress==quote['days'] and completed is None:completed=tick
            if missing:shortage+=1;streak+=1;hungry_ticks.append(tick)
            else:streak=0
    if nodes:
        for receipt in refills:
            if receipt['kind']=='city' and nodes.get(positions.get(receipt['tick']))!=receipt['source']:
                raise ValueError('City supplied a unit that was elsewhere')
    hunger=supply['starvation']
    if not isinstance(hunger,list) or len(hunger)!=len(hungry_ticks):raise ValueError('Segment supply hunger ledger')
    lost=0
    for tick,row in zip(hungry_ticks,hunger):
        if (not isinstance(row,dict) or set(row)!={'tick','after_risks','before','after','reserves_before','reserves_after','lost'}
            or row['tick']!=tick or type(row['after_risks'])is not int or not 0<=row['after_risks']<=OFFICER_TROOP_CAP
            or not isinstance(row['before'],dict) or not isinstance(row['after'],dict)
            or set(row['before'])!=set(row['after']) or len(row['before'])>99
            or any(not isinstance(k,str) or type(v)is not int or not 0<=v<=OFFICER_TROOP_CAP for k,v in row['before'].items())
            or any(type(v)is not int or v!=max(0,row['before'][k]-(row['before'][k]+99)//100) for k,v in row['after'].items())
            or type(row['reserves_before'])is not int or not 0<=row['reserves_before']<=LIMIT
            or type(row['reserves_after'])is not int or row['reserves_after']!=max(0,row['reserves_before']-(row['reserves_before']+99)//100)
            or row['lost']!=sum(row['before'].values())-sum(row['after'].values())+row['reserves_before']-row['reserves_after']):
            raise ValueError('Segment supply hunger arithmetic')
        lost+=row['lost']
    if (supply['elapsed_days']!=elapsed or supply['route_days']!=progress or supply['credit_units']!=credit
        or supply['consumed']!=paid or weighted and supply['base_consumed']!=base_paid
        or supply['shortage_days']!=shortage or supply['shortage_streak']!=streak
        or supply['lost']!=lost or supply['received']!=sum(r['grain'] for r in refills)
        or supply['remaining']+paid+supply['returned_to_cargo']!=supply['loaded']+supply['received']):
        raise ValueError('Segment supply inventory accounting')


def validate_departures(supply,quote,*,returning=False,game=None):
    """Require the next physical leg's food before an outbound node departure.

    Historical ownership may change after a journey. The runtime budgets as far
    as the next friendly supply city; this owner-independent lower bound checks
    only the immediately following leg, which every normal departure must fund.
    A retreat may deliberately leave without enough food to reach safety.
    """
    if returning:return
    weighted=book_version(supply)==rules.CURRENT
    divisor=book_denominator(supply)
    parts=rules.plan(quote,travel_rules(game)) if weighted else None
    starts={};distance=0
    for leg in quote['routes']:
        starts[distance]=rules.weight(parts,distance,leg['days']) if weighted else leg['days']
        distance+=leg['days']
    receipts={}
    for row in supply['refills']:
        receipts[row['tick']]=receipts.get(row['tick'],0)+row['grain']
    inventory=supply['loaded'];credit=supply.get('initial_credit',0);progress=0;tick=supply['start_tick']
    for period in supply['periods']:
        for meal in period['days']:
            inventory+=receipts.get(tick,0);tick+=1
            if meal is None:continue
            units,used,moved,missing=meal
            if moved and progress in starts and inventory*divisor+credit<units*starts[progress]:
                raise ValueError('Outbound departure cannot fund its next physical leg')
            inventory-=used
            charge=units
            if weighted:
                rate=rules.weight(parts,progress,1) if moved or progress<quote['days'] and progress not in starts else rules.RATION_SCALE
                charge*=rate
            credit=max(0,credit+used*divisor-charge+missing)
            progress+=moved


def validate_strength_manifests(supply,manifest,risks,dead_keys=(),reserves_at=None):
    """Bind meal weights to actual departure, hunger and arrived weather facts."""
    dead=set(dead_keys)
    if (supply['clock_tick'] == supply['start_tick']
            and supply['ration_manifests'][0]['troops'] != manifest):
        raise ValueError('Initial meal strength differs from departure')
    progress=0;positions={supply['start_tick']:0}
    for index,period in enumerate(supply['periods']):
        for offset,meal in enumerate(period['days']):
            tick=supply['start_tick']+index*10+offset+1
            if meal is not None:progress+=meal[2]
            positions[tick]=progress
    for packet in supply['ration_manifests']:
        prior=dict(manifest);risk_count=0
        def weather(until):
            nonlocal risk_count
            while risk_count<until:
                risk=risks[risk_count]
                if not risk['applied']:raise ValueError('Meal strength uses unapplied weather')
                prior.update({k:v for k,v in risk['after'].items() if k!='cargo'})
                risk_count+=1
        for receipt in supply['starvation']:
            if receipt['tick']>=packet['tick']:break
            weather(receipt['after_risks']);prior.update(receipt['after'])
        # A weather-adjusted meal is legal only after the force physically
        # completed its route. The raw risk before/after arithmetic is checked
        # separately by the enclosing army/convoy validator.
        route_complete=positions.get(packet['tick']-1,0)==supply['route_days']
        if route_complete:
            weather(sum(bool(r['applied']) for r in risks))
        removed=set(prior)-set(packet['troops'])
        if (set(packet['troops'])-set(prior) or not removed<=dead
                or any(prior[k]!=n for k,n in packet['troops'].items())):
            raise ValueError('Meal strength is not an actual travelling manifest')
        expected_reserves=reserves_at(packet['tick']) if reserves_at is not None else 0
        if packet['reserves']!=expected_reserves:
            raise ValueError('Meal reserves differ from the transport ledger')
