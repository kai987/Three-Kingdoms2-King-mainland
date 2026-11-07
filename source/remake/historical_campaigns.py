"""Conditional historical fronts and their wartime alliances."""

GUANDU = 'historical_guandu'
ALLIANCE = 'historical_sun_liu_alliance'
SOUTH = 'historical_cao_southern_campaign'
TONGGUAN = 'historical_tongguan'
YILING = 'historical_yiling'
ALLIANCE_ENDED = 'historical_sun_liu_alliance_ended'
ALLIANCE_CONTINUING = 'sun_liu_continuing_alliance'
RECEIPTS = 'historical_campaigns'

LEADERS = {
    'wei': 'san14-candidate-0521',     # Cao Cao
    'yuan_shao': 'san14-candidate-0035',
    'shu': 'san14-candidate-0952',     # Liu Bei
    'wu': 'san14-candidate-0553',      # Sun Quan
    'ma_teng': 'san14-candidate-0769', # Ma Chao in 211
    'han_sui': 'san14-candidate-0166',
}
SUN_LIU = ('wu', 'shu')
GUANZHONG_COALITION = ('ma_teng', 'han_sui')
JINGZHOU_OPENING = 'mainland219-07'
JINGZHOU_RUPTURE = (219, 10)
JINGZHOU_FRONT = (('nanjun', 'yidu', 'badong'), ('jiangxia', 'nanjun', 'yidu'))
SOUTHERN_FRONT = (('nanjun', 'wei'), ('jiangxia', 'shu'), ('wujun', 'wu'))
SOUTH_PRIORITY_UNTIL = (209, 3)
YILING_FRONT = (('badong', 'shu'), ('yidu', 'wu'), ('nanjun', 'wu'))
RULES = {
    # White Horse is represented by the Dong commandery node on this map.
    GUANDU: ((200, 2), (200, 10), ('yuan_shao', 'wei'),
             (('wei', 'yuan_shao'), ('dongjun', 'wei'), ('yingchuan', 'wei'))),
    ALLIANCE: ((208, 10), (208, 12), (*SUN_LIU, 'wei'), SOUTHERN_FRONT),
    SOUTH: ((208, 12), (208, 12), ('wei', *SUN_LIU), SOUTHERN_FRONT),
    TONGGUAN: ((211, 7), (211, 9), ('wei', *GUANZHONG_COALITION),
               (('hongnong', 'wei'), ('jingzhao', 'wei'), ('fengyi', 'ma_teng'),
                ('fufeng', 'ma_teng'), ('jincheng', 'han_sui'))),
    YILING: ((221, 7), (222, 6), ('shu', 'wu'), YILING_FRONT),
}
EVENT_FACTIONS = {kind: factions[:2] if kind == ALLIANCE else factions
                  for kind, (_, _, factions, _) in RULES.items()}
EVENT_FACTIONS[ALLIANCE_ENDED] = SUN_LIU
EVENT_CITIES = {
    GUANDU: ('dongjun', 'wei', 'yingchuan'),
    ALLIANCE: ('jiangxia', 'wujun'),
    SOUTH: ('nanjun', 'jiangxia', 'wujun'),
    TONGGUAN: ('hongnong', 'fengyi', 'jingzhao', 'fufeng', 'jincheng'),
    YILING: ('badong', 'yidu', 'nanjun'),
}
NOTES = {
    GUANDU: '袁绍与曹操在黄河沿线开战。双方依战局安排出征。',
    ALLIANCE: '孙权与刘备结盟抗曹，同盟期间两方不得相互出征。',
    SOUTH: '曹军以江陵为南下据点，战斗按实际行军和接敌结算。',
    TONGGUAN: '曹操西征，马超、韩遂在关中联合抗曹。',
    YILING: '刘备准备东征，战事由实际行军和交战决定。',
    ALLIANCE_ENDED: '荆州局势生变，孙刘同盟解除。',
}


def _date(state):
    return state.year, state.month


def _historical(catalog):
    return (catalog.data.get('main_scenario') or {}).get('group') != 'if'


def _holds(state, holdings):
    return all(city in state.cities and state.cities[city].owner == owner
               for city, owner in holdings)


def _has_leaders(state, factions):
    leaders = state.extension['leaders']
    for owner in factions:
        officer = state.officers.get(leaders.get(owner))
        if (officer is None or not officer.alive or officer.faction_id != owner
                or officer.person_id != LEADERS[owner]):
            return False
    return True


def _jingzhou_front(game, state):
    west, east = JINGZHOU_FRONT
    for source in west:
        if not _holds(state, ((source, 'shu'),)):
            continue
        neighbors = game._neighbors(source, state)
        for target in east:
            if target in neighbors and _holds(state, ((target, 'wu'),)):
                return source, target
    return ()


def _record(game, state, receipts, kind, cities):
    state.extension.setdefault(RECEIPTS, receipts)
    receipts[kind] = state.turn
    factions = EVENT_FACTIONS[kind]
    # Launched marches retain their original travel receipts.
    for owner in factions:
        state.extension['ai_strategy'].pop(owner, None)
    game._emit_event(state, kind, city_ids=cities, factions=factions, audience='world',
                     person_ids=[LEADERS[owner] for owner in factions])
    game._note(state, NOTES[kind])


def process(game, state):
    if state.phase not in ('city', 'arrivals') or not (200 <= state.year <= 222) or not _historical(game.catalog):
        return
    now = _date(state)
    receipts = state.extension.get(RECEIPTS, {})
    if (game.catalog.data['id'] == JINGZHOU_OPENING and (219, 7) <= now < JINGZHOU_RUPTURE
            and ALLIANCE_CONTINUING not in receipts and _has_leaders(state, SUN_LIU)
            and _jingzhou_front(game, state)):
        # This opening inherits the existing pact rather than reenacting 208.
        state.extension.setdefault(RECEIPTS, receipts)
        receipts[ALLIANCE_CONTINUING] = state.turn
        for owner in SUN_LIU:
            state.extension['ai_strategy'].pop(owner, None)
    if JINGZHOU_RUPTURE <= now <= RULES[YILING][1] and _alliance_active(state) and _has_leaders(state, SUN_LIU):
        if front := _jingzhou_front(game, state):
            _record(game, state, receipts, ALLIANCE_ENDED, front)
    for kind, (start, end, factions, holdings) in RULES.items():
        if kind in receipts or not start <= now <= end:
            continue
        if kind == SOUTH and ALLIANCE not in receipts:
            continue
        if not _holds(state, holdings) or not _has_leaders(state, factions):
            continue
        if kind == YILING and _alliance_active(state):
            _record(game, state, receipts, ALLIANCE_ENDED, ('badong', 'yidu'))
        _record(game, state, receipts, kind, EVENT_CITIES[kind])


def _alliance_active(state):
    receipts = state.extension.get(RECEIPTS, {})
    if ALLIANCE_ENDED in receipts or not (ALLIANCE in receipts or ALLIANCE_CONTINUING in receipts):
        return False
    ended = state.extension['ended_factions']
    return all(faction not in ended for faction in (*SUN_LIU, 'wei'))


def _tongguan_active(state):
    return (TONGGUAN in state.extension.get(RECEIPTS, {}) and _date(state) <= RULES[TONGGUAN][1]
            and not any(owner in state.extension['ended_factions'] for owner in EVENT_FACTIONS[TONGGUAN]))


def allied(state, first, second):
    if first == second:
        return False
    return ((first in SUN_LIU and second in SUN_LIU and _alliance_active(state))
            or (first in GUANZHONG_COALITION and second in GUANZHONG_COALITION and _tongguan_active(state)))


def alliances(state):
    if state is None:
        return []
    return [list(pair) for pair in (SUN_LIU, GUANZHONG_COALITION) if allied(state, *pair)]


def _priority_event(state):
    receipts = state.extension.get(RECEIPTS, {})
    ended = state.extension.get('ended_factions', ())
    if GUANDU in receipts and _date(state) <= RULES[GUANDU][1] and not any(
            owner in ended for owner in EVENT_FACTIONS[GUANDU]):
        return GUANDU
    if SOUTH in receipts and _date(state) <= SOUTH_PRIORITY_UNTIL and _alliance_active(state):
        return SOUTH
    if _tongguan_active(state):
        return TONGGUAN
    if YILING in receipts and _date(state) <= RULES[YILING][1] and not any(
            owner in ended for owner in EVENT_FACTIONS[YILING]):
        return YILING
    return None


def priority_factions(state):
    event = _priority_event(state)
    if event in (SOUTH, YILING):
        return EVENT_FACTIONS[event][:1]
    return EVENT_FACTIONS.get(event, ())


def priority_targets(state, owner, targets):
    event = _priority_event(state)
    if owner not in priority_factions(state):
        return set(), None
    opponents = [faction for faction in EVENT_FACTIONS[event]
                 if faction != owner and not allied(state, owner, faction)]
    eligible = {key for key in targets if state.cities[key].owner in opponents}
    if event == YILING:
        eligible &= {'yidu', 'nanjun'}
        # Let the army concentrate and resupply at Badong when it is too
        # weak to move on Yidu this turn.
        if 'yidu' in eligible:
            return {'yidu'}, 'yidu'
    first = 'jiangxia' if event == SOUTH else 'fengyi' if event == TONGGUAN and owner == 'wei' else None
    return eligible, first if first in eligible else None


def _turn_date(catalog, turn):
    month = catalog.data['start_year'] * 12 + catalog.data['start_month'] - 1 + (turn - 1) // 3
    year, offset = divmod(month, 12)
    return year, offset + 1


def validate_state(catalog, state):
    if RECEIPTS not in state.extension:
        return
    receipts = state.extension[RECEIPTS]
    if (not _historical(catalog) or not isinstance(receipts, dict)
            or not receipts or not set(receipts) <= {*EVENT_FACTIONS, ALLIANCE_CONTINUING}):
        raise ValueError('Historical campaign receipts')
    for kind, turn in receipts.items():
        if type(turn) is not int or not 1 <= turn <= state.turn:
            raise ValueError('Historical campaign receipt turn')
        date = _turn_date(catalog, turn)
        if kind == ALLIANCE_CONTINUING:
            if (catalog.data['id'] != JINGZHOU_OPENING or not (219, 7) <= date < JINGZHOU_RUPTURE
                    or ALLIANCE in receipts or not set((*SUN_LIU, 'wei')) <= set(catalog.factions)):
                raise ValueError('Inherited Sun–Liu alliance receipt')
            continue
        if kind == ALLIANCE_ENDED:
            start_turn = receipts.get(ALLIANCE, receipts.get(ALLIANCE_CONTINUING))
            if (type(start_turn) is not int or start_turn >= turn
                    or not JINGZHOU_RUPTURE <= date <= RULES[YILING][1]):
                raise ValueError('Sun–Liu alliance dissolution receipt')
            continue
        start, end, factions, holdings = RULES[kind]
        if (not start <= date <= end
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
    cities = row['city_ids']
    if kind == ALLIANCE_ENDED:
        cities_ok = (len(cities) == 2 and cities[0] != cities[1]
                     and all(city in side for city, side in zip(cities, JINGZHOU_FRONT)))
    else:
        cities_ok = cities == list(EVENT_CITIES[kind])
    if (type(turn) is not int or row['turn'] != turn or row['audience'] != 'world' or row['details']
            or (row['year'], row['month']) != _turn_date(catalog, turn)
            or row['day'] != 1 + 10 * ((turn - 1) % 3)
            or row['factions'] != list(factions) or not cities_ok
            or row['person_ids'] != [LEADERS[owner] for owner in factions]):
        raise ValueError('Historical campaign event')
