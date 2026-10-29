"""Conditional, once-only historical openings and attested monthly retirements.

The calendar changes existing state only: no new people, resources or RNG.
Player recruitment and city ownership take precedence over a historical script.
"""
from .officers import YearState, year_state
from . import officer_relations

FOUNDING_FIELDS = {'id','faction','date','city','cities','ruler','members','required_owner',
                   'require_unaligned','scope','basis','source_urls'}
COUP_FIELDS = {'id','faction','date','ruler','successor','victims','basis','source_urls'}


def foundings(catalog):
    return catalog.data.get('faction_foundings', [])


def coups(catalog):
    return catalog.data.get('faction_coups', [])


def _date(value):
    return (isinstance(value, list) and len(value) == 2 and type(value[0]) is int
            and 1 <= value[0] <= 400 and type(value[1]) is int and 1 <= value[1] <= 12)


def validate_source(catalog):
    seen, owners = set(), set()
    for rule in foundings(catalog):
        if (not isinstance(rule, dict) or set(rule) != FOUNDING_FIELDS
                or not isinstance(rule['id'], str) or not rule['id'] or len(rule['id']) > 80
                or rule['id'] in seen or rule['faction'] in owners or not _date(rule['date'])
                or rule['faction'] not in catalog.factions or rule['city'] not in catalog.map_cities
                or not isinstance(rule['cities'], list) or not rule['cities']
                or any(not isinstance(c,str) or c not in catalog.data['active_cities'] for c in rule['cities'])
                or len(set(rule['cities'])) != len(rule['cities']) or rule['city'] not in rule['cities']
                or rule['required_owner'] != 'neutral' or rule['require_unaligned'] is not True
                or rule['scope'] != 'scenario_only' or not isinstance(rule['members'], list)
                or not rule['members'] or len(rule['members']) > 99
                or any(not isinstance(p, str) for p in rule['members'])
                or len(set(rule['members'])) != len(rule['members'])
                or rule['ruler'] not in rule['members'] or any(p not in catalog.ids for p in rule['members'])
                or catalog.data['faction_rulers'][rule['faction']] != catalog.ids[rule['ruler']]
                or catalog.factions[rule['faction']].get('available_from') != rule['date']
                or tuple(rule['date']) <= (catalog.data['start_year'], catalog.data['start_month'])
                or not isinstance(rule['source_urls'], list) or not rule['source_urls']
                or any(not isinstance(u, str) or not u.startswith('https://') for u in rule['source_urls'])):
            raise ValueError('Invalid dated faction founding')
        seen.add(rule['id']); owners.add(rule['faction'])
    for rule in coups(catalog):
        if (not isinstance(rule,dict) or set(rule)!=COUP_FIELDS
                or not isinstance(rule['id'],str) or not rule['id'] or rule['id'] in seen
                or rule['faction'] not in catalog.factions or not _date(rule['date'])
                or tuple(rule['date']) <= (catalog.data['start_year'],catalog.data['start_month'])
                or not isinstance(rule['victims'],list) or not rule['victims']
                or any(not isinstance(p,str) or p not in catalog.ids for p in rule['victims'])
                or len(set(rule['victims']))!=len(rule['victims'])
                or rule['ruler'] not in rule['victims'] or rule['successor'] not in catalog.ids
                or rule['successor'] in rule['victims'] or len(rule['victims'])>98
                or not isinstance(rule['source_urls'],list) or not rule['source_urls']
                or any(not isinstance(u,str) or not u.startswith('https://') for u in rule['source_urls'])):
            raise ValueError('Invalid dated faction coup')
        seen.add(rule['id'])
    exits = catalog.data.get('historical_exit_dates', {})
    if not isinstance(exits, dict) or any(pid not in catalog.ids or not _date(date)
                                       for pid, date in exits.items()):
        raise ValueError('Invalid historical monthly exit date')


def exit_dates(catalog):
    """Only enabled lives need receipts; excluded later catalogs remain unchanged."""
    start = (catalog.data['start_year'], catalog.data['start_month'])
    return {pid: date for pid, date in catalog.data.get('historical_exit_dates', {}).items()
            if start <= tuple(date) and catalog.data.get('era_assignments',{}).get(
                pid,{}).get('status','scenario_excluded') != 'scenario_excluded'}


def enabled(catalog):
    return bool(foundings(catalog) or coups(catalog) or exit_dates(catalog))


def dormant(catalog, state, faction):
    rule = next((r for r in foundings(catalog) if r['faction'] == faction), None)
    return rule is not None and (state is None or state.extension.get('dated_events', {}).get(
        'foundings', {}).get(rule['id'], {}).get('status') != 'formed')


def visible_factions(catalog, state=None):
    rows=[]
    for source in catalog.factions.values():
        row=dict(source)
        if dormant(catalog,state,row['id']):continue
        if state is not None:
            leader=state.extension['leaders'].get(row['id'])
            person=catalog.by_id.get(leader) or state.extension.get('civil_staff',{}).get('people',{}).get(leader)
            if person is not None:
                name=person['name']
                row.update(captain=name,ruler_id=leader,
                    ruler_person_id=state.officers[leader].person_id)
                # Polity/scenario labels remain the opening's source data.
                # A real succession changes only this live display row;
                # faction identity, colors, ownership and save data stay fixed.
                if leader!=catalog.data['faction_rulers'].get(row['id']):
                    row['name']=name
            row['display_name']=row['captain'] if '势力' in row['name'] or '勢力' in row['name'] else row['name']
        rows.append(row)
    return rows


def initialize(catalog, state):
    if enabled(catalog):
        state.extension['dated_events'] = dict(foundings={}, retirements={}, coups={})
    for rule in foundings(catalog):
        state.extension['leaders'][rule['faction']] = None


def _local_free(game, state, pid, city):
    officer = state.officers.get(game.catalog.ids[pid])
    return (officer is not None and officer.alive and officer.faction_id is None
            and officer.health > 0 and officer.troops == 0
            and state.extension['free_locations'].get(str(officer.runtime_id)) == city
            and year_state(game.person_definition(state, officer.runtime_id), state.year)
            in {YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW})


def _retire(game,state,pid):
    ident=game.catalog.ids[pid]; officer=state.officers.get(ident)
    released=officer.troops if officer is not None and officer.alive else 0
    if officer is not None and officer.alive:
        home=next((c for c in state.cities.values() if ident in c.roster.officer_ids),None)
        if released and home is None:raise ValueError('Retiring officer has no soldier destination')
        if home is not None:
            from . import domestic
            domestic.add_reserves(game,state,home,released,morale_value=domestic.morale(state,home.id))
        officer.alive=False;officer.faction_id=None;officer.loyalty=0;officer.troops=0
        for city in state.cities.values():
            if ident in city.roster.officer_ids:city.roster.officer_ids.remove(ident)
        state.extension['free_locations'].pop(str(ident),None)
    return released


def process(game, state):
    if not enabled(game.catalog):
        return
    pool = state.extension['dated_events']
    now = (state.year, state.month)
    for pid, date in exit_dates(game.catalog).items():
        if now < tuple(date) or pid in pool['retirements']:
            continue
        released=_retire(game,state,pid)
        game._note(state, f'{game.catalog.name(game.catalog.ids[pid])}于本月到达史料记载的寿命边界，释放兵员{released}归原城。')
        pool['retirements'][pid] = dict(date=list(now), turn=state.turn, released=released)
    for rule in foundings(game.catalog):
        if now < tuple(rule['date']) or rule['id'] in pool['foundings']:
            continue
        city = state.cities.get(rule['city'])
        holdings=[state.cities.get(c) for c in rule['cities']]
        reason = ('city_occupied' if any(c is None or c.owner!='neutral' or c.roster.officer_ids for c in holdings)
                  else 'leader_unavailable' if not _local_free(game, state, rule['ruler'], city.id) else 'formed')
        members, assigned = [], 0
        if reason == 'formed':
            members = [pid for pid in rule['members'] if _local_free(game, state, pid, city.id)]
            if len(members) > game.catalog.rules.city_officer_capacity:
                raise ValueError('Dated faction exceeds city capacity')
            for holding in holdings:holding.owner=rule['faction']
            for pid in members:
                ident = game.catalog.ids[pid]; officer = state.officers[ident]
                officer.faction_id = rule['faction']
                officer.loyalty = 100 if pid == rule['ruler'] else 80
                state.extension['free_locations'].pop(str(ident), None)
                city.roster.officer_ids.append(ident)
            state.extension['leaders'][rule['faction']] = game.catalog.ids[rule['ruler']]
            officer_relations.apply_faction(game,state,rule['faction'])
            for ident in sorted(city.roster.officer_ids, key=lambda i: (
                    -state.officers[i].profile.martial_strength, -state.officers[i].profile.intellect,
                    -state.officers[i].profile.virtue, i)):
                amount = min(1000-state.officers[ident].troops, city.reserves)
                state.officers[ident].troops += amount; city.reserves -= amount; assigned += amount
        pool['foundings'][rule['id']] = dict(status='formed' if reason == 'formed' else 'skipped',
            date=list(now), turn=state.turn, members=members, reserves=assigned, reason=reason)
        game._emit_event(state, 'faction_founded' if reason == 'formed' else 'faction_founding_skipped',
            city_ids=rule['cities'], factions=[rule['faction']],
            person_ids=members if reason == 'formed' else rule['members'],
            details=dict(founding_id=rule['id'], reason=reason, reserves=assigned), audience='world')
        result_text = {'formed': '势力已成立', 'city_occupied': '城池已被占领', 'leader_unavailable': '领袖已被登用、离世或不在当地待访'}[reason]
        game._note(state, f'{game.catalog.factions[rule["faction"]]["captain"]}起兵事件已结算：{result_text}。')


    for rule in coups(game.catalog):
        if now<tuple(rule['date']) or rule['id'] in pool['coups']:continue
        ids=[game.catalog.ids[p] for p in [*rule['victims'],rule['successor']]]
        holding_ids=[c.id for c in state.cities.values() if c.owner==rule['faction']]
        possible=(holding_ids and state.extension['leaders'].get(rule['faction'])==game.catalog.ids[rule['ruler']]
            and all(i in state.officers and state.officers[i].alive and
                state.officers[i].faction_id==rule['faction'] and i not in game._march_ids(state) for i in ids))
        released=0
        if possible:
            released=sum(_retire(game,state,p) for p in rule['victims'])
            leader=game.catalog.ids[rule['successor']]
            state.extension['leaders'][rule['faction']]=leader
            state.officers[leader].loyalty=100
            state.extension['pending_succession'].pop(rule['faction'],None)
            officer_relations.apply_faction(game,state,rule['faction'])
        reason='executed' if possible else 'conditions_changed'
        pool['coups'][rule['id']]=dict(status=reason,date=list(now),turn=state.turn,released_troops=released,reason=reason)
        game._emit_event(state,'faction_coup' if possible else 'faction_coup_skipped',
            city_ids=holding_ids[:99],factions=[rule['faction']],person_ids=[*rule['victims'],rule['successor']],
            details=dict(coup_id=rule['id'],reason=reason,released_troops=released),audience='world')


def validate_state(game, state):
    if not enabled(game.catalog):
        return
    pool = state.extension.get('dated_events')
    if not isinstance(pool, dict) or set(pool) != {'foundings','retirements','coups'}:
        raise ValueError('Dated event receipt fields')
    if not all(isinstance(pool[k], dict) for k in pool):
        raise ValueError('Dated event receipt domain')
    rules = {r['id']: r for r in foundings(game.catalog)}
    now = (state.year,state.month)
    due = {key for key,r in rules.items() if tuple(r['date']) <= now}
    if set(pool['foundings']) != due:
        raise ValueError('Missing or premature faction founding receipt')
    for key, row in pool['foundings'].items():
        rule=rules[key]
        if (not isinstance(row, dict) or set(row) != {'status','date','turn','members','reserves','reason'}
                or row['status'] not in ('formed','skipped') or row['date'] != rule['date']
                or type(row['turn']) is not int or row['turn'] != _event_turn(game.catalog, rule['date'])
                or not 1 <= row['turn'] <= state.turn
                or not isinstance(row['members'], list) or any(not isinstance(p, str) for p in row['members'])
                or len(set(row['members'])) != len(row['members'])
                or not set(row['members']) <= set(rule['members'])
                or type(row['reserves']) is not int or not 0 <= row['reserves'] <= 1000*len(row['members'])
                or (row['status']=='formed' and (row['reason']!='formed' or rule['ruler'] not in row['members']))
                or (row['status']=='skipped' and (row['reason'] not in ('city_occupied','leader_unavailable')
                    or row['members'] or row['reserves']))):
            raise ValueError('Invalid faction founding receipt')
    exits = exit_dates(game.catalog)
    due_exits = {pid for pid,date in exits.items() if tuple(date) <= now}
    if set(pool['retirements']) != due_exits:
        raise ValueError('Missing or premature monthly retirement receipt')
    for pid,row in pool['retirements'].items():
        officer=state.officers.get(game.catalog.ids[pid])
        if (not isinstance(row,dict) or set(row) != {'date','turn','released'} or row['date'] != exits[pid]
                or type(row['turn']) is not int or row['turn'] != _event_turn(game.catalog, exits[pid])
                or not 1 <= row['turn'] <= state.turn
                or type(row['released']) is not int or not 0 <= row['released'] <= 1000
                or officer is not None and (officer.alive or officer.faction_id is not None or officer.troops)):
            raise ValueError('Invalid monthly retirement receipt')
    coup_rules={r['id']:r for r in coups(game.catalog)}
    if set(pool['coups'])!={key for key,r in coup_rules.items() if tuple(r['date'])<=now}:
        raise ValueError('Missing or premature faction coup receipt')
    for key,row in pool['coups'].items():
        rule=coup_rules[key]
        if (not isinstance(row,dict) or set(row)!={'status','date','turn','released_troops','reason'}
                or row['status'] not in ('executed','conditions_changed') or row['reason']!=row['status']
                or row['date']!=rule['date'] or type(row['turn']) is not int
                or row['turn']!=_event_turn(game.catalog,rule['date']) or row['turn']>state.turn
                or type(row['released_troops']) is not int or not 0<=row['released_troops']<=1000*len(rule['victims'])
                or row['status']=='conditions_changed' and row['released_troops']
                or row['status']=='executed' and any(state.officers.get(game.catalog.ids[p]) is not None
                    and state.officers[game.catalog.ids[p]].alive for p in rule['victims'])):
            raise ValueError('Invalid faction coup receipt')


def _event_turn(catalog, date):
    months = (date[0]-catalog.data['start_year'])*12 + date[1]-catalog.data['start_month']
    return months*3+1
