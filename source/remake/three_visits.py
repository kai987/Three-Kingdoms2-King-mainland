"""Player-driven continuation of Xu Shu's historical recommendation."""

from dataclasses import replace

from . import historical_campaigns, officer_relations
from .errors import GameError
from .officers import (YearState, appearance_values, initialize_officer,
                       recruitment_loyalty, year_state)


COMMAND = 'three_visits'
RECOMMENDATION = 'historical_three_visits'
STAGES = ('historical_three_visits_first', 'historical_three_visits_second',
          'historical_longzhong')
NOTES = ('刘备初访隆中，诸葛亮不在。', '刘备再访隆中，又未见到诸葛亮。',
         '刘备三访隆中，诸葛亮献隆中对，随后加入刘备势力。')
OWNER = 'shu'
SITE = 'xiangyang'
OPENING_CITY = 'yiyang'
LIU_BEI = historical_campaigns.LEADERS[OWNER]
ZHUGE_LIANG = historical_campaigns.ZHUGE_LIANG
START, END, *_ = historical_campaigns.RULES[RECOMMENDATION]


def _early_entry(person, year):
    if person.person_id == ZHUGE_LIANG and year == START[0] and person.service_year == END[0]:
        return replace(person, service_year=year)
    return person


def runtime_definition(state, person):
    if person.person_id == ZHUGE_LIANG and len(state.extension.get(COMMAND, ())) == len(STAGES):
        return _early_entry(person, state.year)
    return person


def _joinable(game, state, ident):
    person = game.catalog.definitions.get(ZHUGE_LIANG)
    if (person is None or game.catalog.profiles[ident].missing
            or year_state(_early_entry(person, state.year), state.year) != YearState.AVAILABLE):
        return False
    officer = state.officers.get(ident)
    return officer is None or (officer.alive and officer.faction_id is None
                               and str(ident) in state.extension['free_locations'])


def view(game, state):
    if (state is None or state.player != OWNER or not START <= (state.year, state.month) <= END
            or RECOMMENDATION not in state.extension.get(historical_campaigns.RECEIPTS, {})):
        return None
    visits = state.extension.get(COMMAND, ())
    leader_id = game.catalog.ids[LIU_BEI]
    leader = state.officers.get(leader_id)
    home = next((city for city in state.cities.values()
                 if city.owner == OWNER and leader_id in city.roster.officer_ids), None)
    completed = len(visits)
    next_visit = completed + 1 if completed < len(STAGES) else None
    reason = None
    if next_visit is not None:
        if (state.phase != 'city' or home is None or leader is None or not leader.alive or leader.health < 1
                or state.extension['leaders'].get(OWNER) != leader_id or leader_id in game._march_ids(state)):
            reason = 'leader_unavailable'
        elif visits and visits[-1]['turn'] == state.turn:
            reason = 'wait_turn'
        elif not _joinable(game, state, game.catalog.ids.get(ZHUGE_LIANG)):
            reason = 'zhuge_unavailable'
        elif next_visit == len(STAGES) and game._city_occupancy(state, home) >= game.catalog.rules.city_officer_capacity:
            reason = 'city_full'
    return dict(completed_visits=completed, next_visit=next_visit,
                city=home.id if home else OPENING_CITY, can_visit=next_visit is not None and reason is None,
                reason=reason)


def _recruit(game, state, city):
    ident = game.catalog.ids[ZHUGE_LIANG]
    officer = state.officers.get(ident)
    if officer is None:
        profile = game.catalog.profiles[ident]
        person = _early_entry(game.catalog.definitions[ZHUGE_LIANG], state.year)
        officer = initialize_officer(person, ident, profile, year=state.year, rules=game.catalog.rules,
                                     **appearance_values(profile, game.catalog.by_id[ident].get('initialization')))
        state.officers[ident] = officer
    leader = state.officers[game.catalog.ids[LIU_BEI]]
    officer.faction_id = OWNER
    officer.loyalty = recruitment_loyalty(leader.profile.virtue, officer.loyalty)
    city.roster.officer_ids.append(ident)
    officer_relations.apply(game, state, ident)
    state.extension['free_locations'].pop(str(ident), None)
    state.extension['officer_actions'][str(ident)] = state.turn


def execute(game, state, payload):
    visit = payload.get('visit')
    if set(payload) != {'visit'} or type(visit) is not int or not 1 <= visit <= len(STAGES):
        raise GameError('拜访指令参数无效。')
    offer = view(game, state)
    if offer is None or not offer['can_visit'] or visit != offer['next_visit']:
        raise GameError('目前无法进行这次隆中拜访。')
    city = state.cities[offer['city']]
    state.extension.setdefault(COMMAND, []).append(dict(turn=state.turn, city=city.id))
    if visit == len(STAGES):
        _recruit(game, state, city)
    game._emit_event(state, STAGES[visit - 1], person_ids=[LIU_BEI, ZHUGE_LIANG],
                     city_ids=[city.id, SITE], factions=[OWNER])
    game._note(state, NOTES[visit - 1])


def validate_state(catalog, state):
    if COMMAND not in state.extension:
        return
    visits = state.extension[COMMAND]
    recommendation = state.extension.get(historical_campaigns.RECEIPTS, {}).get(RECOMMENDATION)
    if (state.player != OWNER or type(recommendation) is not int or not isinstance(visits, list)
            or not 1 <= len(visits) <= len(STAGES)):
        raise ValueError('Three Visits history')
    previous_turn = recommendation - 1
    for visit in visits:
        if (not isinstance(visit, dict) or set(visit) != {'turn', 'city'} or type(visit['turn']) is not int
                or not previous_turn < visit['turn'] <= state.turn or not isinstance(visit['city'], str)):
            raise ValueError('Three Visits record')
        date = historical_campaigns._turn_date(catalog, visit['turn'])
        if not START <= date <= END or visit['city'] not in catalog.active_city_ids(*date):
            raise ValueError('Three Visits date or city')
        previous_turn = visit['turn']
    if len(visits) == len(STAGES) and catalog.ids.get(ZHUGE_LIANG) not in state.officers:
        raise ValueError('Missing Longzhong recruit')
    rows = state.extension['events']['items']
    retained = [row['kind'] for row in rows if row['kind'] in STAGES]
    if len(retained) != len(set(retained)):
        raise ValueError('Duplicate Three Visits event')
    for kind, visit in zip(STAGES, visits):
        # Older snapshots can be evicted from the bounded event history.
        if (kind not in retained and (not rows or rows[0]['id'] == 1 or rows[0]['turn'] < visit['turn'])):
            raise ValueError('Missing Three Visits event')


def validate_event(catalog, state, row):
    visits = state.extension.get(COMMAND, ())
    index = STAGES.index(row['kind'])
    if (not isinstance(visits, list) or index >= len(visits) or not isinstance(visits[index], dict)
            or visits[index].get('turn') != row['turn'] or row['audience'] != 'player' or row['details']
            or row['factions'] != [OWNER] or row['person_ids'] != [LIU_BEI, ZHUGE_LIANG]
            or row['city_ids'] != list(dict.fromkeys([visits[index].get('city'), SITE]))
            or (row['year'], row['month']) != historical_campaigns._turn_date(catalog, row['turn'])
            or row['day'] != 1 + 10 * ((row['turn'] - 1) % 3)):
        raise ValueError('Three Visits event')
