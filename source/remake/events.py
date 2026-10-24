"""Structured, bounded campaign events, committed with the game transaction.

Events describe mechanics that really happened. They never generate historical
conquests, consume random numbers, or acknowledge/advance a game from the UI.
"""
from copy import deepcopy
import re
from .officers import ref_sort_key, is_generated_ref

LIMIT = 100
STAFF_KINDS = {'staff_candidate', 'staff_hired', 'staff_declined', 'staff_expired',
               'staff_salary', 'staff_allegiance'}
STAFF_DETAILS = {'staff_id', 'name', 'portrait', 'reason', 'amount', 'paid', 'bonus', 'counts'}
TRANSPORT_KINDS = {'transport_departed','transport_arrived','transport_returned','transport_weather'}
TRANSPORT_DETAILS = {'convoy_id','gold','grain','reserves','treasure','lost','reason'}
TREASURY_DETAILS = {
    'treasure_found': {'actor','amount','chance','gold'},
    'treasure_search_failed': {'actor','amount','chance','gold'},
    'treasure_sold': {'actor','amount','gold'},
    'officer_rewarded': {'actor','target','kind','amount','gain','loyalty_before','loyalty_after'},
    'governor_assigned': {'governor','mode'},
}
SUPPLY_KINDS = {'march_resupplied', 'march_starvation', 'march_retreat'}
SUPPLY_DETAILS = {'unit_kind', 'unit_id', 'grain', 'lost', 'shortage_days', 'reason'}
SUPPLY_REASONS = {'city', 'convoy', 'cargo', 'shortage', 'route_blocked',
                  'no_friendly_city', 'origin_changed', 'target_changed', 'completed'}
DETAILS = {
    'campaign_start': {'difficulty', 'scenario_title'}, 'officer_appeared': set(),
    'recruit_success': {'actor'}, 'recruit_failure': {'actor'},
    'defection': {'from_faction', 'to_faction', 'actor'},
    'officer_death': {'released_troops'}, 'succession': {'previous'},
    'faction_ended': set(), 'city_founded': {'parent'},
    'city_upgraded': {'from_tier','to_tier','income'},
    'city_renamed': {'from_name', 'to_name'},
    'city_captured': {'previous_owner'},
    'battle_started': {'battle_id', 'attacker', 'defender'},
    'battle_result': {'battle_id', 'outcome', 'lost', 'surrendered'},
    'duel_started': set(), 'duel_result': {'result'},
    'tactic': {'tactic', 'success'},
    'march_weather': {'march_id', 'lost', 'risks'},
    'route_discovered': {'from', 'to'},
    'march_arrived': {'march_id', 'officers'},
    'march_returned': {'march_id', 'reason'}, 'new_year': {'year'},
    'campaign_victory': set(), 'campaign_defeat': set(),
    'ai_campaign': {'target', 'sources', 'arrival_turn', 'coordinated'},
    **{kind: set(STAFF_DETAILS) for kind in STAFF_KINDS},
    **{kind: set(TRANSPORT_DETAILS) for kind in TRANSPORT_KINDS},
    **{kind: set(SUPPLY_DETAILS) for kind in SUPPLY_KINDS},
    **TREASURY_DETAILS,
    'domestic_report': {'gold','grain','reserves','morale','cities','reason'},
}


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


def _validate_staff_event(row):
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
    if 'portrait' in details and details['portrait'] not in {'clerk-1', 'clerk-2', 'clerk-3'}:
        raise ValueError('Civil staff event portrait')
    if 'reason' in details and (not isinstance(details['reason'], str)
            or re.fullmatch(r'[a-z_]{1,80}', details['reason']) is None):
        raise ValueError('Civil staff event reason')
    for field in ('amount', 'paid'):
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
                or type(counts['staff']) is not int or not 1 <= counts['staff'] <= 11385
                or type(counts['cities']) is not int or not 1 <= counts['cities'] <= 115
                or not counts['cities'] <= counts['staff'] <= counts['cities'] * 99
                or type(counts['total_unpaid']) is not int or not 0 <= counts['total_unpaid'] <= counts['staff']):
            raise ValueError('Civil staff event counts')
    if row['kind'] == 'staff_salary' and (details['paid'] > details['amount']
            or details['amount'] != details['counts']['staff'] * 5
            or details['paid'] % 5 != 0
            or details['counts']['total_unpaid'] != details['counts']['staff'] - details['paid'] // 5):
        raise ValueError('Civil staff event salary')


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
    events['items'].append(row)
    events['items'][:] = events['items'][-LIMIT:]
    events['next_id'] += 1
    return row


def transition(campaign, before, after, kind, payload):
    """Diff committed domain facts; do not infer events by parsing log text."""
    person = lambda ident: after.officers[ident].person_id
    if before is None or kind == 'new':
        leader = after.extension['leaders'].get(after.player)
        emit(campaign, after, 'campaign_start',
             person_ids=[person(leader)] if leader is not None else [],
             city_ids=[c.id for c in after.cities.values() if c.owner == after.player][:1],
             factions=[after.player], details=dict(difficulty=after.extension['difficulty'],
             scenario_title=campaign.catalog.data['title']))
        return
    for ident, officer in sorted(after.officers.items(), key=lambda item: ref_sort_key(item[0])):
        previous = before.officers.get(ident)
        if previous is None:
            if is_generated_ref(ident):
                continue  # Hiring already emitted the independent staff snapshot.
            city = after.extension['free_locations'].get(str(ident))
            emit(campaign, after, 'officer_appeared', person_ids=[officer.person_id],
                 city_ids=[city] if city else [], audience='world')
        elif previous.alive and not officer.alive:
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
            from .city_economy import tier_at,income_at
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
                emit(campaign,after,'city_upgraded',city_ids=[city],factions=[value.owner],
                     details=dict(from_tier=previous,to_tier=current,
                                  income=income_at(campaign.catalog.data,city,after.year,after.month)),audience='world')
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
        emit(campaign, after, 'campaign_' + after.extension['outcome'], factions=[after.player], audience='world')


def validate(campaign, state):
    events = state.extension['events']
    if not isinstance(events, dict) or set(events) != {'next_id', 'items'}:
        raise ValueError('Campaign event fields')
    if type(events['next_id']) is not int or events['next_id'] < 1:
        raise ValueError('Campaign event counter')
    rows = events['items']
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise ValueError('Campaign event bound')
    ids = []
    fields = {'id', 'kind', 'year', 'month', 'day', 'turn', 'person_ids', 'city_ids', 'factions', 'details', 'audience'}
    for row in rows:
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
        for key, allowed in [('person_ids', {*campaign.catalog.definitions, *state.extension.get('civil_staff', {}).get('people', {})}), ('city_ids', campaign.catalog.map_cities),
                             ('factions', {*campaign.catalog.factions, 'neutral'})]:
            values = row[key]
            if not isinstance(values, list) or len(values) > 99 or any(not isinstance(v, str) or v not in allowed for v in values) or len(set(values)) != len(values):
                raise ValueError('Campaign event references')
        if row['audience'] not in {'player', 'world'} or not isinstance(row['details'], dict) or not set(row['details']) <= DETAILS[row['kind']]:
            raise ValueError('Campaign event payload')
        def value_ok(value, depth=0):
            if depth > 3:
                return False
            if value is None or type(value) is bool:
                return True
            if type(value) is int:
                return 0 <= value <= 2**53-1
            if isinstance(value, str):
                return len(value) <= 500
            if isinstance(value, list):
                return len(value) <= 99 and all(value_ok(v, depth+1) for v in value)
            if isinstance(value, dict):
                return len(value) <= 10 and all(isinstance(k, str) and len(k) <= 80 and value_ok(v, depth+1) for k, v in value.items())
            return False
        if not value_ok(row['details']):
            raise ValueError('Campaign event JSON value')
        if row['kind'] in STAFF_KINDS:
            _validate_staff_event(row)
        if row['kind'] in SUPPLY_KINDS:
            _validate_supply_event(row)
        if row['kind'] in TREASURY_DETAILS:
            _validate_treasury_event(row)
        if row['kind'] in TRANSPORT_KINDS:
            if (set(row['details']) != TRANSPORT_DETAILS
                    or type(row['details']['treasure']) is not int
                    or not 0 <= row['details']['treasure'] <= 99):
                raise ValueError('Transport treasure receipt')
        if row['kind']=='city_upgraded':
            from .city_economy import tier_at,income_at
            details=row['details']
            if (set(details)!=DETAILS[row['kind']] or len(row['city_ids'])!=1 or row['person_ids']
                    or len(row['factions'])!=1 or row['audience']!='world'):
                raise ValueError('City size event fields')
            city=row['city_ids'][0]
            previous_year,previous_month=(row['year'],row['month']-1) if row['month']>1 else (row['year']-1,12)
            if (details['from_tier']!=tier_at(campaign.catalog.data,city,previous_year,previous_month)
                    or details['to_tier']!=tier_at(campaign.catalog.data,city,row['year'],row['month'])
                    or details['from_tier']==details['to_tier'] or row['day']!=1
                    or details['income']!=income_at(campaign.catalog.data,city,row['year'],row['month'])):
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
    if ids != sorted(set(ids)) or ids and ids != list(range(events['next_id']-len(ids), events['next_id'])):
        raise ValueError('Campaign event sequence')
