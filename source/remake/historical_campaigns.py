"""Dated military priorities and the Sun–Liu wartime alliance."""

GUANDU = 'historical_guandu'
ALLIANCE = 'historical_sun_liu_alliance'
SOUTH = 'historical_cao_southern_campaign'
RECEIPTS = 'historical_campaigns'

LEADERS = {
    'wei': 'san14-candidate-0521',     # Cao Cao
    'yuan_shao': 'san14-candidate-0035',
    'shu': 'san14-candidate-0952',     # Liu Bei
    'wu': 'san14-candidate-0553',      # Sun Quan
}
SUN_LIU = ('wu', 'shu')
SOUTHERN_FRONT = (('nanjun', 'wei'), ('jiangxia', 'shu'), ('wujun', 'wu'))
SOUTH_PRIORITY_UNTIL = (209, 3)
RULES = {
    # White Horse is represented by the Dong commandery node on this map.
    GUANDU: ((200, 2), (200, 10), ('yuan_shao', 'wei'),
             (('wei', 'yuan_shao'), ('dongjun', 'wei'), ('yingchuan', 'wei'))),
    ALLIANCE: ((208, 10), (208, 12), (*SUN_LIU, 'wei'), SOUTHERN_FRONT),
    SOUTH: ((208, 12), (208, 12), ('wei', *SUN_LIU), SOUTHERN_FRONT),
}
EVENT_FACTIONS = {kind: factions[:2] if kind == ALLIANCE else factions
                  for kind, (_, _, factions, _) in RULES.items()}
EVENT_CITIES = {
    GUANDU: ('dongjun', 'wei', 'yingchuan'),
    ALLIANCE: ('jiangxia', 'wujun'),
    SOUTH: ('nanjun', 'jiangxia', 'wujun'),
}
NOTES = {
    GUANDU: '袁绍与曹操在黄河沿线开战。双方依战局安排出征。',
    ALLIANCE: '孙权与刘备结盟抗曹，同盟期间两方不得相互出征。',
    SOUTH: '曹军以江陵为南下据点，战斗按实际行军和接敌结算。',
}


def _date(state):
    return state.year, state.month


def _historical(catalog):
    return (catalog.data.get('main_scenario') or {}).get('group') != 'if'


def process(game, state):
    if state.phase not in ('city', 'arrivals') or not (200 <= state.year <= 208) or not _historical(game.catalog):
        return
    now = _date(state)
    receipts = state.extension.get(RECEIPTS, {})
    for kind, (start, end, factions, holdings) in RULES.items():
        if kind in receipts or not start <= now <= end:
            continue
        if kind == SOUTH and ALLIANCE not in receipts:
            continue
        if any(city not in state.cities or state.cities[city].owner != owner for city, owner in holdings):
            continue
        leaders = state.extension['leaders']
        if any((officer := state.officers.get(leaders.get(owner))) is None
               or not officer.alive or officer.faction_id != owner
               or officer.person_id != LEADERS[owner] for owner in factions):
            continue
        state.extension.setdefault(RECEIPTS, receipts)
        receipts[kind] = state.turn
        # Launched marches remain in the travel ledger. Only the AI's future
        # objective is discarded when the political situation changes.
        for owner in EVENT_FACTIONS[kind]:
            state.extension['ai_strategy'].pop(owner, None)
        game._emit_event(state, kind, city_ids=EVENT_CITIES[kind],
                         factions=EVENT_FACTIONS[kind], audience='world',
                         person_ids=[LEADERS[owner] for owner in EVENT_FACTIONS[kind]])
        game._note(state, NOTES[kind])


def _alliance_active(state):
    if ALLIANCE not in state.extension.get(RECEIPTS, {}):
        return False
    ended = state.extension['ended_factions']
    return all(faction not in ended for faction in (*SUN_LIU, 'wei'))


def allied(state, first, second):
    return first in SUN_LIU and second in SUN_LIU and first != second and _alliance_active(state)


def alliances(state):
    return [list(SUN_LIU)] if state and _alliance_active(state) else []


def priority_factions(state):
    receipts = state.extension.get(RECEIPTS, {})
    if GUANDU in receipts and _date(state) <= RULES[GUANDU][1]:
        if not any(owner in state.extension['ended_factions'] for owner in EVENT_FACTIONS[GUANDU]):
            return EVENT_FACTIONS[GUANDU]
    if SOUTH in receipts and _date(state) <= SOUTH_PRIORITY_UNTIL and _alliance_active(state):
        return ('wei',)
    return ()


def priority_targets(state, owner, targets):
    active = priority_factions(state)
    if owner not in active:
        return set()
    opponents = SUN_LIU if active == ('wei',) else tuple(faction for faction in active if faction != owner)
    return {key for key in targets if state.cities[key].owner in opponents}


def _turn_date(catalog, turn):
    month = catalog.data['start_year'] * 12 + catalog.data['start_month'] - 1 + (turn - 1) // 3
    year, offset = divmod(month, 12)
    return year, offset + 1


def validate_state(catalog, state):
    if RECEIPTS not in state.extension:
        return
    receipts = state.extension[RECEIPTS]
    if (not _historical(catalog) or not isinstance(receipts, dict)
            or not receipts or not set(receipts) <= set(RULES)):
        raise ValueError('Historical campaign receipts')
    for kind, turn in receipts.items():
        start, end, factions, holdings = RULES[kind]
        if (type(turn) is not int or not 1 <= turn <= state.turn
                or not start <= _turn_date(catalog, turn) <= end
                or not set(factions) <= set(catalog.factions)
                or any(city not in state.cities for city, _ in holdings)
                or any(LEADERS[owner] not in catalog.ids for owner in factions)):
            raise ValueError('Historical campaign receipt')
    if SOUTH in receipts and (ALLIANCE not in receipts or receipts[ALLIANCE] > receipts[SOUTH]):
        raise ValueError('Historical alliance must precede the southern campaign')


def validate_event(catalog, state, row):
    kind = row['kind']
    turn = state.extension.get(RECEIPTS, {}).get(kind)
    factions = EVENT_FACTIONS[kind]
    if (turn is None or row['turn'] != turn or row['audience'] != 'world' or row['details']
            or (row['year'], row['month']) != _turn_date(catalog, turn)
            or row['day'] != 1 + 10 * ((turn - 1) % 3)
            or row['factions'] != list(factions) or row['city_ids'] != list(EVENT_CITIES[kind])
            or row['person_ids'] != [LEADERS[owner] for owner in factions]):
        raise ValueError('Historical campaign event')
