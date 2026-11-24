"""Structured, bounded campaign events, committed with the game transaction.

Events describe mechanics that really happened. They never generate historical
conquests, consume random numbers, or acknowledge/advance a game from the UI.
"""
from copy import deepcopy
import re
from . import historical_campaigns, observer, southern_mission, three_visits, runan_campaign
from . import grain_units
from .battle_supply import COALITION_LIMIT, denominator, MAX_BATTLE_DAILY_UNITS
from .city_development import LIMITS as DEVELOPMENT_LIMITS, POPULATION_UNIT, valid_population
from .civil_staff import PORTRAITS as CIVIL_PORTRAITS
from .payroll import CLERK_GOLD, CLERK_GRAIN
from .dated_events import FOUNDING_TROOP_TARGET
from .officers import MAX_BATTLE_PARTICIPANTS, OFFICER_TROOP_CAP, ref_sort_key, is_generated_ref

LIMIT = 100
MILESTONE_KINDS = frozenset((*historical_campaigns.EVENT_FACTIONS, *three_visits.STAGES, *southern_mission.EVENTS))
STAFF_KINDS = {'staff_candidate', 'staff_hired', 'staff_declined', 'staff_expired',
               'staff_salary', 'staff_allegiance'}
STAFF_DETAILS = {'staff_id', 'name', 'portrait', 'reason', 'amount', 'paid', 'bonus', 'counts'}
STAFF_SALARY_GRAIN = {'grain_amount', 'grain_paid'}
TRANSPORT_KINDS = {'transport_departed','transport_arrived','transport_returned','transport_weather'}
TRANSPORT_DETAILS = {'convoy_id','gold','grain','reserves','treasure','lost','reason'}
TREASURY_DETAILS = {
    'treasure_found': {'actor','amount','chance','gold'},
    'treasure_search_failed': {'actor','amount','chance','gold'},
    'treasure_sold': {'actor','amount','gold'},
    'officer_rewarded': {'actor','target','kind','amount','gain','loyalty_before','loyalty_after'},
    'governor_assigned': {'governor','mode'},
}
FACILITY_DETAILS = {
    'town_developed': {'actor','from_town','to_town','gold','grain'},
    'officer_treated': {'actor','target','gold','before','after'},
    'officer_studied': {'actor','target','gold','before','after','bonus'},
    'grain_traded': {'actor','direction','batches','grain','gold','rate','battle_id','side','destination','emergency','market_city'},
    'equipment_bought': {'actor','target','slot','item','previous','gold'},
    'prevention_improved': {'actor','gold','gain','repair','preparedness_before',
        'preparedness_after','damage_before','damage_after'},
    'city_disaster': {'disaster','gold','grain','reserves','rate','preparedness_before',
        'preparedness_after','damage_before','damage_after'},
}
CITY_DEVELOPMENT_DETAILS = {
    'city_developed': {'actor','development','gold','before','after','gain',
        'governance_before','governance_after','gain_scale'},
    'civil_unrest': {'governance','category','gold_loss','grain_loss','population_loss',
        'land_loss','industry_loss'},
}
BATTLE_SUPPLY_DETAILS = {'battle_id','side','days','grain','daily_grain','missing_units','outcome'}
BATTLE_TRADE_DETAILS = {'battle_id','side','destination'}
EQUIPMENT_DETAILS = {'actor','target','from_person','slot','item','previous','method','battle_id','chance','roll'}
SUPPLY_KINDS = {'march_resupplied', 'march_starvation', 'march_retreat'}
SUPPLY_DETAILS = {'unit_kind', 'unit_id', 'grain', 'lost', 'shortage_days', 'reason'}
SUPPLY_REASONS = {'city', 'convoy', 'cargo', 'shortage', 'route_blocked',
                  'no_friendly_city', 'origin_changed', 'target_changed', 'completed'}
DETAILS = {
    'campaign_start': {'difficulty', 'scenario_title'}, 'officer_appeared': set(),
    'recruit_success': {'actor'}, 'recruit_failure': {'actor'},
    'defection': {'from_faction', 'to_faction', 'actor'},
    'officer_death': {'released_troops'}, 'succession': {'previous'},
    'faction_ended': set(), 'city_founded': {'parent','settlement'},
    'city_upgraded': {'from_tier','to_tier','income'},
    'city_renamed': {'from_name', 'to_name'},
    'city_captured': {'previous_owner'},
    'city_harvest': {'bonuses'},
    'faction_founded': {'founding_id','reason','reserves'},
    'faction_founding_skipped': {'founding_id','reason','reserves'},
    'faction_coup': {'coup_id','reason','released_troops'},
    'faction_coup_skipped': {'coup_id','reason','released_troops'},
    **{kind: set() for kind in historical_campaigns.EVENT_FACTIONS},
    historical_campaigns.DONG_ZHUO_RELOCATION: historical_campaigns.DONG_ZHUO_RELOCATION_DETAILS,
    historical_campaigns.LONGYOU_RESPONSE: {'joined', 'governor_withdrew'},
    **dict.fromkeys((runan_campaign.FIRST_JOIN, runan_campaign.SECOND_JOIN), runan_campaign.JOIN_DETAILS),
    runan_campaign.REFUGE: runan_campaign.REFUGE_DETAILS,
    **{kind: set() for kind in three_visits.STAGES},
    southern_mission.DEPARTED: {'days', 'storm_days'},
    southern_mission.LANDED: {'can_build'},
    southern_mission.FOUNDED: {'troops', 'work_days'},
    'battle_started': {'battle_id', 'attacker', 'defender'},
    'battle_result': {'battle_id', 'outcome', 'lost', 'surrendered', 'coalition', 'experience'},
    'duel_started': set(), 'duel_result': {'result'},
    'tactic': {'tactic','success','affected_side','grain_before','grain_after','grain_loss',
               'success_percent','target_loyalty','guaranteed_failure','condition','condition_count','condition_counts',
               'qimen_phase','qimen_ticks','experience_id','experience_gain'},
    'march_weather': {'march_id', 'lost', 'risks'},
    'route_discovered': {'from', 'to'},
    'march_arrived': {'march_id', 'officers'},
    'march_returned': {'march_id', 'reason'}, 'new_year': {'year'},
    'campaign_victory': set(), 'campaign_defeat': set(),
    'ai_campaign': {'target', 'sources', 'arrival_turn', 'coordinated'},
    **{kind: set(STAFF_DETAILS) for kind in STAFF_KINDS},
    'staff_salary': STAFF_DETAILS | STAFF_SALARY_GRAIN,
    **{kind: set(TRANSPORT_DETAILS) for kind in TRANSPORT_KINDS},
    **{kind: set(SUPPLY_DETAILS) for kind in SUPPLY_KINDS},
    **TREASURY_DETAILS,
    **FACILITY_DETAILS,
    **CITY_DEVELOPMENT_DETAILS,
    'battle_supply_exhausted': BATTLE_SUPPLY_DETAILS,
    'equipment_acquired':EQUIPMENT_DETAILS,
    'domestic_report': {'gold','grain','reserves','morale','cities','reason'},
    'diplomacy_result': {'action','success','score','duration','grain','request_number','aid_reason'},
}


def _validate_coalition_result(campaign, row):
    from .allied_assault import RESOURCES
    from .march_supply import LIMIT as STOCK_LIMIT
    from .officers import BATTLE_OFFICERS_PER_SIDE

    details = row['details']
    result = details['coalition']
    if (details.get('outcome') != 'victory' or not isinstance(result, dict)
            or set(result) != {'captor', 'ally', 'troops', 'shares', 'returns'}
            or len(row['factions']) != 2):
        raise ValueError('Allied assault result fields')
    captor, ally = result['captor'], result['ally']
    if (not isinstance(captor, str) or not isinstance(ally, str)
            or captor == ally or not {captor, ally} <= set(campaign.catalog.factions)
            or row['factions'][0] not in {captor, ally} or row['factions'][1] in {captor, ally}):
        raise ValueError('Allied assault result factions')
    troops, shares, returns = (result[key] for key in ('troops', 'shares', 'returns'))
    max_troops = MAX_BATTLE_PARTICIPANTS * OFFICER_TROOP_CAP
    if (not isinstance(troops, list) or len(troops) != 2
            or any(type(qty) is not int or not 0 <= qty <= max_troops for qty in troops)
            or sum(troops) > max_troops
            or not isinstance(shares, list) or len(shares) != 2
            or any(not isinstance(share, dict) or set(share) != set(RESOURCES)
                   or any(type(qty) is not int or not 0 <= qty <= STOCK_LIMIT for qty in share.values())
                   for share in shares)
            or not isinstance(returns, list) or len(returns) > MAX_BATTLE_PARTICIPANTS
            or any(not isinstance(city, str) or city not in campaign.catalog.map_cities for city in returns)
            or len(set(returns)) != len(returns)):
        raise ValueError('Allied assault result units or stocks')


def _validate_equipment_event(row):
    from .facility_equipment import WEAPONS, ARMORS
    d=row['details']
    if (set(d)!=EQUIPMENT_DETAILS or row['audience']!='player' or len(row['city_ids'])!=1
            or len(row['factions'])!=1 or d['slot'] not in ('weapon','armor')
            or row['person_ids']!=list(dict.fromkeys([d['actor'],d['target'],d['from_person']]))):
        raise ValueError('Equipment acquisition fields')
    maximum=len(WEAPONS if d['slot']=='weapon' else ARMORS)-1
    if (any(type(d[key]) is not int or not 0<=d[key]<=maximum for key in ('item','previous'))
            or d['item']==d['previous'] or type(d['chance']) is not int or type(d['roll']) is not int):
        raise ValueError('Equipment acquisition item')
    if d['method']=='owned':
        valid=d['from_person']==d['target'] and d['battle_id'] is None and d['chance']==0 and d['roll']==-1
    else:
        valid=(d['method']=='duel' and d['actor']==d['target'] and d['from_person']!=d['target']
            and isinstance(d['battle_id'],str) and re.fullmatch(r'battle-[1-9][0-9]{0,9}',d['battle_id'])
            and d['chance'] in (30,50,100) and (d['roll']==-1 if d['chance']==100 else 0<=d['roll']<d['chance']))
    if not valid:raise ValueError('Equipment acquisition receipt')


def _validate_facility_event(row, cities):
    d, kind = row['details'], row['kind']
    fields = FACILITY_DETAILS[kind]
    if kind == 'town_developed' and 'grain' not in d:
        fields = fields - {'grain'}
    if kind == 'grain_traded':
        if not set(d) & BATTLE_TRADE_DETAILS:
            fields = fields - BATTLE_TRADE_DETAILS
        if 'emergency' not in d:
            fields = fields - {'emergency'}
        if 'market_city' not in d:
            fields = fields - {'market_city'}
    if (set(d) != fields or row['audience'] != 'player'
            or len(row['city_ids']) != 1 or len(row['factions']) != 1):
        raise ValueError('Facility event fields')
    def number(key, low, high):
        return type(d[key]) is int and low <= d[key] <= high
    people=[] if kind=='city_disaster' else list(dict.fromkeys([d['actor']]+([d['target']] if 'target' in d else [])))
    if row['person_ids'] != people or not number('gold',0,100000000):
        raise ValueError('Facility event references/price')
    if kind=='town_developed':
        valid=number('from_town',1,2) and d['to_town']==d['from_town']+1 and d['gold']>0
        if valid and 'grain' in d:
            from .facilities import TOWN_UPGRADE_COSTS
            gold, grain = TOWN_UPGRADE_COSTS[d['from_town']]
            valid = d['gold'] == gold and number('grain', grain, grain)
    elif kind in ('officer_treated','officer_studied'):
        valid=(number('before',0 if kind=='officer_treated' else 1,99 if kind=='officer_treated' else 79)
            and number('after',1,99 if kind=='officer_treated' else 89)
            and d['after']>d['before'] and d['gold']>0)
        if kind=='officer_studied':
            valid=valid and number('bonus',1,88) and 5<=d['after']-d['before']<=12
    elif kind=='grain_traded':
        batch = grain_units.amount(100)
        valid = (d['direction'] in ('buy','sell') and number('batches',1,1000)
                 and number('rate',1,100) and number('grain',1,1000 * batch))
        if 'emergency' in d:
            valid = (valid and d['emergency'] is True and d['direction'] == 'buy' and 'battle_id' not in d
                     and d['batches'] == (d['grain'] + batch - 1) // batch
                     and d['gold'] == (d['grain'] * d['rate'] + batch - 1) // batch)
        else:
            valid = valid and d['grain'] == d['batches'] * batch and d['gold'] == d['batches'] * d['rate']
        if 'battle_id' in d:
            valid=(valid and d['direction']=='buy' and d['destination']=='battle'
                and d['side'] in ('attackers','defenders') and isinstance(d['battle_id'],str)
                and re.fullmatch(r'battle-[1-9][0-9]{0,9}',d['battle_id']) is not None)
        if 'market_city' in d:
            market = d['market_city']
            valid = (valid and isinstance(market, str) and market in cities
                     and ('battle_id' in d or market == row['city_ids'][0]))
    elif kind=='equipment_bought':
        from .facility_equipment import WEAPONS, ARMORS
        maximum=len(WEAPONS if d['slot']=='weapon' else ARMORS)-1
        valid=(d['slot'] in ('weapon','armor') and number('item',0,maximum)
            and number('previous',0,maximum) and d['item']!=d['previous'] and d['gold']>0)
    else:
        valid=all(number(key,0,99) for key in ('preparedness_before','preparedness_after'))
        valid=valid and all(number(key,0,50) for key in ('damage_before','damage_after'))
        if kind=='prevention_improved':
            valid=(valid and number('gain',0,99) and number('repair',0,50) and 1<=d['gold']<=100
                and d['preparedness_after']-d['preparedness_before']==d['gain']
                and d['damage_before']-d['damage_after']==d['repair'])
        else:
            valid=(valid and d['disaster'] in ('flood','drought') and number('rate',0,100)
                and number('grain',0,100000000) and number('reserves',0,100000000)
                and d['preparedness_after']<=d['preparedness_before'] and d['damage_after']>=d['damage_before']
                and (d['gold']==0 if d['disaster']=='drought' else d['reserves']==0)
                and (d['preparedness_before']!=99 or not any(d[k] for k in ('gold','grain','reserves','rate'))))
    if not valid:
        raise ValueError('Facility event receipt')


def _validate_city_development_event(row):
    d, kind = row['details'], row['kind']
    fields = CITY_DEVELOPMENT_DETAILS[kind]
    scaled = kind == 'city_developed' and 'gain_scale' in d
    if kind == 'city_developed' and not scaled:
        fields = fields - {'gain_scale'}
    if (set(d) != fields or row['audience'] != 'player'
            or len(row['city_ids']) != 1 or len(row['factions']) != 1):
        raise ValueError('City development event fields')
    def number(key, low, high):
        return type(d[key]) is int and low <= d[key] <= high
    if kind == 'city_developed':
        population = d['development'] == 'population'
        cap = DEVELOPMENT_LIMITS['population'] if population else DEVELOPMENT_LIMITS['land']
        valid=(d['development'] in ('land','industry','population')
            and row['person_ids']==[d['actor']] and number('gold',10,26) and d['gold']%2==0
            and all(number(key,0,cap) for key in ('before','after','gain'))
            and d['after']-d['before']==d['gain']
            and all(number(key,0,100) for key in ('governance_before','governance_after')))
        if valid:
            unit = POPULATION_UNIT if population else 1
            valid=((not population or (valid_population(d['before']) and valid_population(d['after'])
                                        and (d['gain'] % unit == 0 or d['after'] == cap)))
                and (not scaled or (not population and number('gain_scale',10,10) and d['gain'] <= 5))
                and d['governance_after']==min(100,d['governance_before']+1+(d['gain']//unit >= (4 if scaled else 31)))
                and (d['gain']>0 or d['governance_after']>d['governance_before']))
    else:
        loss_fields={'population':{'population_loss'},'resources':{'gold_loss','grain_loss'},
            'development':{'land_loss','industry_loss'}}
        active=loss_fields.get(d['category']) if isinstance(d['category'],str) else None
        valid=(not row['person_ids'] and number('governance',0,49) and active is not None
            and all(number(key,0,100000000 if key in ('gold_loss','grain_loss') else
                DEVELOPMENT_LIMITS['population'] if key=='population_loss' else DEVELOPMENT_LIMITS['land'])
                and (key in active or d[key]==0) for key in
                ('gold_loss','grain_loss','population_loss','land_loss','industry_loss'))
            and d['population_loss'] % POPULATION_UNIT == 0)
    if not valid:
        raise ValueError('City development event receipt')


def _validate_battle_supply_event(row):
    d = row['details']
    if (set(d) != BATTLE_SUPPLY_DETAILS or row['audience'] != 'player'
            or not 1 <= len(row['city_ids']) <= 2 or not 1 <= len(row['factions']) <= 2
            or len(row['person_ids']) > 10 or not isinstance(d['battle_id'],str)
            or re.fullmatch(r'battle-[1-9][0-9]{0,9}',d['battle_id']) is None
            or d['side'] not in ('attackers','defenders')):
        raise ValueError('Battle supply event fields')
    for key, low, high in (('days',1,30),('grain',0,100000000),
                           ('daily_grain',1,MAX_BATTLE_DAILY_UNITS//denominator()),
                           ('missing_units',1,MAX_BATTLE_DAILY_UNITS)):
        if type(d[key]) is not int or not low <= d[key] <= high:
            raise ValueError('Battle supply event values')
    if (d['missing_units']>d['daily_grain']*denominator()
            or d['outcome'] != ('retreat' if d['side']=='attackers' else 'victory')):
        raise ValueError('Battle supply event receipt')


def _validate_treasury_event(row):
    d, kind = row['details'], row['kind']
    if (set(d) != TREASURY_DETAILS[kind] or row['audience'] != 'player'
            or len(row['city_ids']) != 1 or len(row['factions']) != 1):
        raise ValueError('Treasury event fields')
    def number(key, low, high):
        return type(d[key]) is int and low <= d[key] <= high
    if kind == 'governor_assigned':
        if (d['mode'] not in ('auto','manual') or d['mode']=='manual' and d['governor'] is None
                or row['person_ids'] != ([d['governor']] if d['governor'] is not None else [])):
            raise ValueError('Governor event identity')
    elif kind == 'officer_rewarded':
        if (row['person_ids'] != list(dict.fromkeys([d['actor'],d['target']]))
                or d['kind'] not in ('gold','treasure')
                or not number('amount',1,100 if d['kind']=='gold' else 1)
                or not number('gain',1,9) or not number('loyalty_before',0,99)
                or not number('loyalty_after',1,100)
                or d['loyalty_after']-d['loyalty_before'] != d['gain']):
            raise ValueError('Reward event receipt')
    elif kind == 'treasure_sold':
        if row['person_ids'] != [d['actor']] or not number('amount',1,99) or d['gold'] != d['amount']*100:
            raise ValueError('Treasure sale receipt')
    elif (row['person_ids'] != [d['actor']] or not number('chance',15,80)
            or type(d['amount']) is not int or d['amount'] != (1 if kind=='treasure_found' else 0)
            or type(d['gold']) is not int or d['gold'] != 20):
        raise ValueError('Treasure search receipt')


def _validate_supply_event(row):
    """Bounded historical snapshots, independent of a still-live march queue."""
    details = row['details']
    if (set(details) != SUPPLY_DETAILS or not isinstance(details['unit_kind'], str)
            or details['unit_kind'] not in {'march', 'convoy'}
            or not isinstance(details['reason'], str) or details['reason'] not in SUPPLY_REASONS
            or len(row['factions']) != 1 or row['audience'] != 'player'
            or not 1 <= len(row['city_ids']) <= 2):
        raise ValueError('March supply event fields')
    for key, low, high in (('unit_id', 1, 1000000), ('grain', 0, 100000000),
                           ('lost', 0, 100000000), ('shortage_days', 0, 10000000)):
        if type(details[key]) is not int or not low <= details[key] <= high:
            raise ValueError('March supply event values')
    if row['kind'] == 'march_resupplied' and (details['grain'] < 1 or details['lost']):
        raise ValueError('March supply receipt')
    if row['kind'] == 'march_starvation' and (details['grain'] or details['shortage_days'] < 1):
        raise ValueError('March starvation receipt')
    if row['kind'] == 'march_retreat' and (details['grain'] or details['lost']):
        raise ValueError('March retreat receipt')


def _validate_staff_event(row, city_count):
    """Staff snapshots remain independent of historical person references.

    A declined or expired candidate need not remain in the current registry;
    the committed event retains its own bounded name and shared portrait token.
    """
    details = row['details']
    if row['person_ids'] or len(row['city_ids']) != 1 or not 1 <= len(row['factions']) <= 2:
        raise ValueError('Civil staff event references')
    required = {'amount', 'paid', 'bonus', 'counts'} if row['kind'] == 'staff_salary' else {'staff_id', 'name', 'portrait', 'reason'}
    if not required <= set(details):
        raise ValueError('Civil staff event payload')
    if 'staff_id' in details:
        ident = details['staff_id']
        if (not isinstance(ident, str) or re.fullmatch(r'clerk-[0-9]{6,12}', ident) is None
                or int(ident[6:]) < 1):
            raise ValueError('Civil staff event identity')
    if 'name' in details:
        name = details['name']
        if not isinstance(name, str) or not 1 <= len(name) <= 40 or not name.strip() or not name.isprintable():
            raise ValueError('Civil staff event name')
    if 'portrait' in details and details['portrait'] not in CIVIL_PORTRAITS:
        raise ValueError('Civil staff event portrait')
    if 'reason' in details and (not isinstance(details['reason'], str)
            or re.fullmatch(r'[a-z_]{1,80}', details['reason']) is None):
        raise ValueError('Civil staff event reason')
    for field in ('amount', 'paid', 'grain_amount', 'grain_paid'):
        if field in details and (type(details[field]) is not int or not 0 <= details[field] <= 100000000):
            raise ValueError('Civil staff event amount')
    if 'bonus' in details:
        bonus = details['bonus']
        if (not isinstance(bonus, dict) or set(bonus) != {'gold', 'grain', 'reserves'}
                or any(type(value) is not int or not 0 <= value <= 100000000 for value in bonus.values())):
            raise ValueError('Civil staff event income')
    if 'counts' in details:
        counts = details['counts']
        if (not isinstance(counts, dict) or set(counts) != {'staff', 'total_unpaid', 'cities'}
                or type(counts['staff']) is not int or counts['staff'] < 1
                or type(counts['cities']) is not int or not 1 <= counts['cities'] <= city_count
                or not counts['cities'] <= counts['staff'] <= counts['cities'] * 99
                or type(counts['total_unpaid']) is not int or not 0 <= counts['total_unpaid'] <= counts['staff']):
            raise ValueError('Civil staff event counts')
    if row['kind'] != 'staff_salary':
        return
    staff = details['counts']['staff']
    unpaid = details['counts']['total_unpaid']
    paid = details['paid']
    grain_fields = STAFF_SALARY_GRAIN & details.keys()
    if paid > details['amount'] or details['amount'] != staff * CLERK_GOLD:
        raise ValueError('Civil staff event salary')
    if not grain_fields:
        if paid % CLERK_GOLD or unpaid != staff - paid // CLERK_GOLD:
            raise ValueError('Civil staff event legacy salary')
    elif (grain_fields != STAFF_SALARY_GRAIN or details['grain_amount'] != staff * CLERK_GRAIN
          or not (staff - unpaid) * CLERK_GRAIN <= details['grain_paid'] <= details['grain_amount']
          or paid < (staff - unpaid) * CLERK_GOLD
          or (unpaid == 0) != (paid == details['amount'] and details['grain_paid'] == details['grain_amount'])):
        raise ValueError('Civil staff event grain salary')


def _validate_tactic_event(row):
    d=row['details']
    base={'tactic','success'}
    if not base <= set(d) or type(d['tactic']) is not int or not 0 <= d['tactic'] <= 15 or type(d['success']) is not bool:
        raise ValueError('Tactic event result')
    extra=set(d)-base
    if not extra:
        return  # Existing committed events retain their original compact snapshot.
    if d['tactic']==2:
        if (extra!={'condition','condition_count'} or d['condition']!='phantom'
                or type(d['condition_count']) is not int
                or d['condition_count'] not in ((2,3) if d['success'] else (0,))):
            raise ValueError('Tactic phantom snapshot')
    elif d['tactic']==15:
        if d.get('condition')!='qimen':raise ValueError('Tactic qimen condition')
        if d.get('qimen_phase')=='cast':
            if (extra!={'condition','condition_count','qimen_phase'}
                    or type(d['condition_count']) is not int
                    or d['condition_count'] not in (range(5,10) if d['success'] else (0,))):
                raise ValueError('Tactic qimen cast snapshot')
        elif d.get('qimen_phase')=='daily':
            if (extra!={'condition','qimen_phase','qimen_ticks','experience_id','experience_gain'}
                    or not d['success'] or type(d['experience_id']) is not str
                    or not 1<=len(d['experience_id'])<=128 or d['experience_id'].strip()!=d['experience_id']
                    or type(d['experience_gain']) is not int or not 0<=d['experience_gain']<=2550
                    or not isinstance(d['qimen_ticks'],list) or not 1<=len(d['qimen_ticks'])<=MAX_BATTLE_PARTICIPANTS):
                raise ValueError('Tactic qimen daily snapshot')
            seen=set()
            for tick in d['qimen_ticks']:
                if (not isinstance(tick,dict) or set(tick)!={'id','before','remaining','troops_before','troops_after','loss'}
                        or type(tick['id']) is not str or not 1<=len(tick['id'])<=128
                        or tick['id'].strip()!=tick['id'] or tick['id'] in seen
                        or any(type(tick[key]) is not int for key in ('before','remaining','troops_before','troops_after','loss'))
                        or not 1<=tick['before']<=9 or tick['remaining']!=tick['before']-1
                        or not 0<=tick['troops_after']<=tick['troops_before']<=OFFICER_TROOP_CAP
                        or tick['loss']!=tick['troops_before']-tick['troops_after']
                        or not min(80,tick['troops_before'])<=tick['loss']<=min(150,tick['troops_before'])):
                    raise ValueError('Tactic qimen tick snapshot')
                seen.add(tick['id'])
        else:raise ValueError('Tactic qimen phase')
    elif d['tactic']==10:
        counts=d.get('condition_counts')
        if (extra!={'condition','condition_counts'} or d['condition']!='chain'
                or not isinstance(counts,list) or not (2<=len(counts)<=MAX_BATTLE_PARTICIPANTS if d['success'] else not counts)):
            raise ValueError('Tactic chain snapshot')
        seen=set()
        for item in counts:
            if (not isinstance(item,dict) or set(item)!={'id','remaining'}
                    or type(item['id']) is not str or not 1<=len(item['id'])<=128
                    or item['id'].strip()!=item['id'] or item['id'] in seen
                    or type(item['remaining']) is not int or not 3<=item['remaining']<=5):
                raise ValueError('Tactic chain target snapshot')
            seen.add(item['id'])
    elif d['tactic']==5:
        maximum = COALITION_LIMIT if d.get('affected_side') == 'attackers' else 100000000
        if (extra!={'affected_side','grain_before','grain_after','grain_loss'}
                or d['affected_side'] not in {'attackers','defenders'}
                or any(type(d[key]) is not int or not 0 <= d[key] <= maximum
                       for key in ('grain_before','grain_after','grain_loss'))
                or d['grain_before']-d['grain_after']!=d['grain_loss']
                or not d['success'] and d['grain_loss']!=0):
            raise ValueError('Tactic fire-arrow snapshot')
    elif d['tactic']==8:
        if (extra!={'success_percent','target_loyalty','guaranteed_failure'}
                or type(d['success_percent']) is not int or not 0 <= d['success_percent'] <= 100
                or type(d['target_loyalty']) is not int or not 0 <= d['target_loyalty'] <= 100
                or type(d['guaranteed_failure']) is not bool
                or d['guaranteed_failure']!=(d['target_loyalty']>=71)
                or d['guaranteed_failure']!=(d['success_percent']==0)
                or d['guaranteed_failure'] and d['success']):
            raise ValueError('Tactic conversion snapshot')
    else:
        raise ValueError('Tactic event effect fields')


def empty():
    return dict(next_id=1, items=[])


def emit(campaign, state, kind, *, person_ids=(), city_ids=(), factions=(), details=None, audience='player'):
    if kind not in DETAILS:
        raise ValueError('Unknown campaign event')
    events = state.extension['events']
    row = dict(id=events['next_id'], kind=kind, year=state.year, month=state.month,
        day=state.day, turn=state.turn, person_ids=list(dict.fromkeys(person_ids)),
        city_ids=list(dict.fromkeys(city_ids)), factions=list(dict.fromkeys(factions)),
        details=deepcopy(details or {}), audience=audience)
    recent = events['items']
    recent.append(row)
    if len(recent) > LIMIT:
        expired = recent.pop(0)
        if expired['kind'] in MILESTONE_KINDS:
            events.setdefault('milestones', []).append(expired)
    events['next_id'] += 1
    return row


def transition(campaign, before, after, kind, payload):
    """Diff committed domain facts; do not infer events by parsing log text."""
    person = lambda ident: after.officers[ident].person_id
    if before is None or kind == 'new':
        leader = after.extension['leaders'].get(after.player)
        observing = after.player == observer.SEAT
        emit(campaign, after, 'campaign_start',
             person_ids=[person(leader)] if leader is not None else [],
             city_ids=[c.id for c in after.cities.values() if c.owner == after.player][:1],
             factions=[] if observing else [after.player], details=dict(difficulty=after.extension['difficulty'],
             scenario_title=campaign.catalog.data['title']), audience='world' if observing else 'player')
        return
    for ident, officer in sorted(after.officers.items(), key=lambda item: ref_sort_key(item[0])):
        previous = before.officers.get(ident)
        if kind == three_visits.COMMAND and officer.person_id == three_visits.ZHUGE_LIANG:
            continue  # The Longzhong scene records its own enlistment.
        if previous is None:
            if is_generated_ref(ident):
                continue  # Hiring already emitted the independent staff snapshot.
            city = after.extension['free_locations'].get(str(ident))
            faction = officer.faction_id
            if faction:
                city = next((home.id for home in after.cities.values() if ident in home.roster.officer_ids), None)
            emit(campaign, after, 'officer_appeared', person_ids=[officer.person_id],
                 city_ids=[city] if city else [], factions=[faction] if faction else [], audience='world')
        elif previous.alive and not officer.alive:
            if runan_campaign.SCRIPTED_EXITS.get(officer.person_id) in after.extension.get(historical_campaigns.RECEIPTS, {}):
                continue  # The historical scene records the actual departure.
            homes = [city.id for city in before.cities.values() if ident in city.roster.officer_ids]
            emit(campaign, after, 'officer_death', person_ids=[officer.person_id],
                 city_ids=homes, factions=[previous.faction_id] if previous.faction_id else [],
                 details=dict(released_troops=previous.troops), audience='world')
        elif previous.faction_id != officer.faction_id and officer.faction_id in campaign.catalog.factions:
            # Only personnel changes involving this player interrupt play.
            if after.player not in (previous.faction_id, officer.faction_id):
                continue
            homes = [city.id for city in after.cities.values() if ident in city.roster.officer_ids]
            actor_id = payload.get('actor') if kind in {'recruit_officer', 'persuade_officer', 'staff_recruit'} else None
            details = dict(actor=person(actor_id)) if actor_id in after.officers else {}
            if previous.faction_id is None:
                event_kind = 'recruit_success'
            else:
                event_kind = 'defection'
                details.update(from_faction=previous.faction_id, to_faction=officer.faction_id)
            emit(campaign, after, event_kind, person_ids=[officer.person_id], city_ids=homes,
                 factions=[f for f in (previous.faction_id, officer.faction_id) if f], details=details)
    if kind in {'recruit_officer', 'persuade_officer', 'staff_recruit'}:
        ident, actor = payload.get('officer'), payload.get('actor')
        if ident in before.officers and before.officers[ident].faction_id == after.officers[ident].faction_id:
            emit(campaign, after, 'recruit_failure', person_ids=[person(ident)],
                 city_ids=[payload['city']], factions=[after.player],
                 details=dict(actor=person(actor)) if actor in after.officers else {})
    for city, value in sorted(after.cities.items()):
        if city not in before.cities:
            rule = campaign.catalog.data['city_foundings'][city]
            emit(campaign, after, 'city_founded', city_ids=[city, rule['parent']],
                 factions=[value.owner], details=dict(parent=rule['parent']), audience='world')
        elif (before.year,before.month)!=(after.year,after.month):
            from .city_economy import income_at, scale_monthly_grain, tier_at
            from .map_presentation import city_names
            if campaign.catalog.data.get('city_history', {}).get(city, {}).get('announce_name_changes') is True:
                old_name = city_names(campaign.catalog, before.year, before.month)[city]
                new_name = city_names(campaign.catalog, after.year, after.month)[city]
                if old_name != new_name:
                    emit(campaign, after, 'city_renamed', city_ids=[city], factions=[value.owner],
                         details=dict(from_name=old_name, to_name=new_name), audience='world')
            previous=tier_at(campaign.catalog.data,city,before.year,before.month)
            current=tier_at(campaign.catalog.data,city,after.year,after.month)
            if current!=previous:
                income = income_at(campaign.catalog.data,city,after.year,after.month)
                emit(campaign,after,'city_upgraded',city_ids=[city],factions=[value.owner],
                     details=dict(from_tier=previous,to_tier=current,
                                  income=scale_monthly_grain(income)),audience='world')
    for faction, leader in sorted(after.extension['leaders'].items()):
        previous = before.extension['leaders'].get(faction)
        if leader is not None and leader != previous and faction not in after.extension.get('pending_succession', {}) and kind != 'choose_successor':
            emit(campaign, after, 'succession', person_ids=[person(leader)], factions=[faction],
                 details=dict(previous=person(previous) if previous in after.officers else None), audience='world')
    for faction in after.extension['ended_factions']:
        if faction not in before.extension['ended_factions']:
            emit(campaign, after, 'faction_ended', factions=[faction], audience='world')
    if after.year > before.year:
        emit(campaign, after, 'new_year', details=dict(year=after.year), audience='world')
    old_duel = before.battle and before.battle['extended']['duel']
    duel = after.battle and after.battle['extended']['duel']
    if duel and not old_duel:
        emit(campaign, after, 'duel_started', person_ids=[person(duel['actor']), person(duel['target'])],
             city_ids=[after.battle['target']], factions=[after.battle['attacker'], after.battle['defender']])
    old_history = before.battle['extended']['duel_history'] if before.battle else []
    history = after.battle['extended']['duel_history'] if after.battle else []
    if history and history != old_history:
        result = history[-1]
        emit(campaign, after, 'duel_result', person_ids=[person(result['actor']), person(result['target'])],
             city_ids=[after.battle['target']], details=dict(result=result['result']))
    for faction, plan in sorted(after.extension['ai_strategy'].items()):
        old = before.extension.get('ai_strategy', {}).get(faction)
        target = plan['target']
        if plan['orders'] and target in after.cities and after.cities[target].owner == after.player and (
                old is None or (plan['target'], plan['created_turn']) != (old['target'], old['created_turn'])):
            emit(campaign, after, 'ai_campaign', city_ids=[target], factions=[faction],
                 details=dict(target=target, sources=list(dict.fromkeys(o['source'] for o in plan['orders'])),
                 arrival_turn=plan['arrival_turn'], coordinated=len(plan['orders']) > 1))
    if after.extension['outcome'] and after.extension['outcome'] != before.extension['outcome']:
        winner = observer.winner(after) if after.player == observer.SEAT else after.player
        emit(campaign, after, 'campaign_' + after.extension['outcome'],
             factions=[winner] if winner else [], audience='world')


def validate(campaign, state):
    events = state.extension['events']
    if not isinstance(events, dict) or set(events) - {'milestones'} != {'next_id', 'items'}:
        raise ValueError('Campaign event fields')
    if type(events['next_id']) is not int or events['next_id'] < 1:
        raise ValueError('Campaign event counter')
    rows = events['items']
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise ValueError('Campaign event bound')
    milestones = events.get('milestones', [])
    if not isinstance(milestones, list) or len(milestones) > len(MILESTONE_KINDS):
        raise ValueError('Campaign milestone bound')
    ids = []
    fields = {'id', 'kind', 'year', 'month', 'day', 'turn', 'person_ids', 'city_ids', 'factions', 'details', 'audience'}
    for row in [*milestones, *rows]:
        if not isinstance(row, dict) or set(row) != fields or row['kind'] not in DETAILS:
            raise ValueError('Campaign event identity')
        ident = row['id']
        if type(ident) is not int or not 1 <= ident < events['next_id']:
            raise ValueError('Campaign event ID')
        ids.append(ident)
        for key, low, high in [('year', 1, state.year), ('month', 1, 12), ('turn', 1, state.turn)]:
            if type(row[key]) is not int or not low <= row[key] <= high:
                raise ValueError('Campaign event date')
        if type(row['day']) is not int or row['day'] not in (1, 11, 21) or (row['year'], row['month'], row['day']) > (state.year, state.month, state.day):
            raise ValueError('Campaign event calendar')
        harvest = row['kind'] == 'city_harvest'
        for key, allowed in [('person_ids', {*campaign.catalog.definitions, *state.extension.get('civil_staff', {}).get('people', {})}), ('city_ids', campaign.catalog.map_cities),
                             ('factions', {*campaign.catalog.factions, 'neutral'})]:
            values = row[key]
            limit = len(allowed) if harvest and key == 'city_ids' else 99
            if not isinstance(values, list) or len(values) > limit or any(not isinstance(v, str) or v not in allowed for v in values) or len(set(values)) != len(values):
                raise ValueError('Campaign event references')
        if row['audience'] not in {'player', 'world'} or not isinstance(row['details'], dict) or not set(row['details']) <= DETAILS[row['kind']]:
            raise ValueError('Campaign event payload')
        coalition_receipt = row['kind'] == 'battle_result' and 'coalition' in row['details']
        def value_ok(value, depth=0):
            if depth > (4 if coalition_receipt else 3):
                return False
            if value is None or type(value) is bool:
                return True
            if type(value) is int:
                return (-1 if row['kind']=='equipment_acquired' else 0) <= value <= 2**53-1
            if isinstance(value, str):
                return len(value) <= 500
            if isinstance(value, list):
                limit = len(campaign.catalog.map_cities) if harvest else 99
                return len(value) <= limit and all(value_ok(v, depth+1) for v in value)
            if isinstance(value, dict):
                return len(value) <= 10 and all(isinstance(k, str) and len(k) <= 80 and value_ok(v, depth+1) for k, v in value.items())
            return False
        event_details = row['details']
        if row['kind'] == 'battle_result' and 'experience' in event_details:
            report = event_details['experience']
            if not isinstance(report, dict) or report.get('battle_id') != event_details.get('battle_id'):
                raise ValueError('Campaign experience receipt identity')
            event_details = {key: val for key, val in event_details.items() if key != 'experience'}
        if not value_ok(event_details):
            raise ValueError('Campaign event JSON value')
        if row['kind']=='tactic':
            _validate_tactic_event(row)
        if row['kind'] in STAFF_KINDS:
            _validate_staff_event(row, len(campaign.catalog.map_cities))
        if row['kind'] in SUPPLY_KINDS:
            _validate_supply_event(row)
        if row['kind'] in TREASURY_DETAILS:
            _validate_treasury_event(row)
        if row['kind'] in FACILITY_DETAILS:
            _validate_facility_event(row, campaign.catalog.map_cities)
        if harvest:
            bonuses = row['details'].get('bonuses')
            if (row['month'] != 10 or row['day'] != 1 or row['audience'] != 'player'
                    or row['person_ids'] or row['factions'] != [state.player] or state.player == observer.SEAT
                    or not row['city_ids'] or not isinstance(bonuses, list)
                    or len(bonuses) != len(row['city_ids'])
                    or any(type(bonus) is not int or not 0 <= bonus <= 100000000 for bonus in bonuses)):
                raise ValueError('City harvest receipts')
        if row['kind'] in CITY_DEVELOPMENT_DETAILS:
            _validate_city_development_event(row)
        if row['kind']=='battle_supply_exhausted':
            _validate_battle_supply_event(row)
        if coalition_receipt:
            _validate_coalition_result(campaign, row)
        if row['kind']=='equipment_acquired':
            _validate_equipment_event(row)
        if row['kind']=='city_founded' and 'settlement' in row['details']:
            d = row['details']
            if (d['settlement'] is not True or len(row['city_ids']) != 2
                    or d.get('parent') != row['city_ids'][1] or len(row['factions']) != 1
                    or row['factions'][0] == 'neutral' or len(row['person_ids']) != 1
                    or row['audience'] != 'world'
                    or not campaign.catalog.map_cities[row['city_ids'][0]].get('settlement_site')):
                raise ValueError('Settlement founding event')
        if row['kind']=='diplomacy_result':
            from .diplomacy import MAX_TURNS, PARAMETERS
            d = row['details']
            grain_aid = d.get('action') == 'request_grain'
            detail_fields = DETAILS[row['kind']] if grain_aid else {'action', 'success', 'score', 'duration'}
            if (set(d) != detail_fields or d['action'] not in PARAMETERS
                    or type(d['success']) is not bool or type(d['score']) is not int
                    or not 0 <= d['score'] <= 100 or type(d['duration']) is not int
                    or (not 1 <= d['duration'] <= MAX_TURNS if d['action']=='alliance' else d['duration']!=0)
                    or len(row['factions']) != 2
                    or len(row['city_ids']) != (2 if d['action']=='request_attack' else 1)
                    or len(row['person_ids']) != (2 if d['action']=='return_captives' else 1)):
                raise ValueError('Diplomacy event receipt')
            if grain_aid and (type(d['grain']) is not int or d['grain'] < 1
                    or type(d['request_number']) is not int or d['request_number'] < 1
                    or d['aid_reason'] not in ('accepted', 'relations', 'insufficient_surplus')
                    or d['success'] != (d['aid_reason'] == 'accepted')):
                raise ValueError('Grain aid event receipt')
        if row['kind'] in historical_campaigns.EVENT_FACTIONS:
            historical_campaigns.validate_event(campaign.catalog,state,row)
        if row['kind'] in three_visits.STAGES:
            three_visits.validate_event(campaign.catalog,state,row)
        if row['kind'] in southern_mission.EVENTS:
            southern_mission.validate_event(state,row)
        if row['kind'] in {'faction_founded','faction_founding_skipped'}:
            rules={r['id']:r for r in campaign.catalog.data.get('faction_foundings',[])}
            d=row['details']; rule=rules.get(d.get('founding_id'))
            if (set(d)!=DETAILS[row['kind']] or rule is None or row['audience']!='world'
                    or row['day']!=1 or [row['year'],row['month']]!=rule['date']
                    or row['city_ids']!=rule['cities'] or row['factions']!=[rule['faction']]
                    or not row['person_ids'] or not set(row['person_ids'])<=set(rule['members'])
                    or type(d['reserves']) is not int or not 0<=d['reserves']<=FOUNDING_TROOP_TARGET*len(row['person_ids'])
                    or (row['kind']=='faction_founded' and
                        (d['reason']!='formed' or rule['ruler'] not in row['person_ids']))
                    or (row['kind']=='faction_founding_skipped' and
                        (d['reason'] not in ('city_occupied','leader_unavailable') or d['reserves']))):
                raise ValueError('Dated faction founding event')
        if row['kind'] in {'faction_coup','faction_coup_skipped'}:
            rules={r['id']:r for r in campaign.catalog.data.get('faction_coups',[])}
            d=row['details'];rule=rules.get(d.get('coup_id'))
            if (set(d)!=DETAILS[row['kind']] or rule is None or row['audience']!='world'
                    or row['day']!=1 or [row['year'],row['month']]!=rule['date']
                    or row['factions']!=[rule['faction']] or row['person_ids']!=[*rule['victims'],rule['successor']]
                    or type(d['released_troops']) is not int or not 0<=d['released_troops']<=OFFICER_TROOP_CAP*len(rule['victims'])
                    or (row['kind']=='faction_coup' and (d['reason']!='executed' or not row['city_ids']))
                    or (row['kind']=='faction_coup_skipped' and
                        (d['reason']!='conditions_changed' or d['released_troops']))):
                raise ValueError('Dated faction coup event')
        if row['kind'] in TRANSPORT_KINDS:
            if (set(row['details']) != TRANSPORT_DETAILS
                    or type(row['details']['treasure']) is not int
                    or not 0 <= row['details']['treasure'] <= 99):
                raise ValueError('Transport treasure receipt')
        if row['kind']=='city_upgraded':
            from .city_economy import income_at, scale_monthly_grain, tier_at
            details=row['details']
            if (set(details)!=DETAILS[row['kind']] or len(row['city_ids'])!=1 or row['person_ids']
                    or len(row['factions'])!=1 or row['audience']!='world'):
                raise ValueError('City size event fields')
            city=row['city_ids'][0]
            previous_year,previous_month=(row['year'],row['month']-1) if row['month']>1 else (row['year']-1,12)
            base_income = income_at(campaign.catalog.data,city,row['year'],row['month'])
            # Existing receipts keep the production that was shown when issued.
            accepted_income = (base_income, scale_monthly_grain(base_income))
            if (details['from_tier']!=tier_at(campaign.catalog.data,city,previous_year,previous_month)
                    or details['to_tier']!=tier_at(campaign.catalog.data,city,row['year'],row['month'])
                    or details['from_tier']==details['to_tier'] or row['day']!=1
                    or details['income'] not in accepted_income):
                raise ValueError('City size event date or income')
        if row['kind'] == 'city_renamed':
            from .map_presentation import city_names
            details = row['details']
            if (set(details) != DETAILS[row['kind']] or len(row['city_ids']) != 1
                    or row['person_ids'] or len(row['factions']) != 1
                    or row['audience'] != 'world' or row['day'] != 1):
                raise ValueError('City name event fields')
            city = row['city_ids'][0]
            previous_year, previous_month = ((row['year'], row['month'] - 1)
                if row['month'] > 1 else (row['year'] - 1, 12))
            if (campaign.catalog.data.get('city_history', {}).get(city, {}).get('announce_name_changes') is not True
                    or details['from_name'] != city_names(campaign.catalog, previous_year, previous_month)[city]
                    or details['to_name'] != city_names(campaign.catalog, row['year'], row['month'])[city]
                    or details['from_name'] == details['to_name']):
                raise ValueError('City name event date or names')
        if row['kind'] in TRANSPORT_KINDS or row['kind']=='domestic_report':
            details=row['details']
            if set(details)!=DETAILS[row['kind']]:
                raise ValueError('Domestic/transport event fields')
            for key,value in details.items():
                if key=='reason':
                    if not isinstance(value,str) or re.fullmatch(r'[a-z_]{1,80}',value) is None:
                        raise ValueError('Domestic/transport event reason')
                elif type(value) is not int or not 0<=value<=100000000:
                    raise ValueError('Domestic/transport event value')
            if not row['city_ids'] or len(row['factions'])!=1:
                raise ValueError('Domestic/transport event references')
    recent_ids = ids[len(milestones):]
    if ids != sorted(set(ids)) or recent_ids != list(range(events['next_id']-len(rows), events['next_id'])):
        raise ValueError('Campaign event sequence')
    kinds = [row['kind'] for row in [*milestones, *rows] if row['kind'] in MILESTONE_KINDS]
    if (any(row['kind'] not in MILESTONE_KINDS for row in milestones)
            or len(kinds) != len(set(kinds)) or milestones and len(rows) != LIMIT):
        raise ValueError('Campaign milestone sequence')
