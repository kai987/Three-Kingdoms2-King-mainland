"""Conditional historical campaigns and diplomacy."""

from .officers import transfer_officers
from .historical_chapters import CHAPTERS

GUANDU = 'historical_guandu'
ALLIANCE = 'historical_sun_liu_alliance'
SOUTH = 'historical_cao_southern_campaign'
MARRIAGE = 'historical_sun_liu_marriage'
TONGGUAN = 'historical_tongguan'
YILING = 'historical_yiling'
HEFEI = 'historical_hefei'
HEFEI_DEFENSE = 'historical_hefei_defense'
HANZHONG_PREPARATION = 'historical_hanzhong_preparation'
HANZHONG = 'historical_hanzhong'
DINGJUN = 'historical_dingjun'
NANZHONG = 'historical_nanzhong'
LIAODONG = 'historical_liaodong'
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
LIU_SHAN = 'san14-candidate-0945'
CAO_RUI = 'san14-candidate-0501'
MENG_HUO = 'san14-candidate-0845'
GONGSUN_YUAN = 'san14-candidate-0262'
ZHANG_LIAO = 'san14-candidate-0663'
LADY_SUN = 'san14-candidate-0565'
FA_ZHENG = 'san14-candidate-0827'
HUANG_ZHONG = 'san14-candidate-0271'
XIAHOU_YUAN = 'san14-candidate-0114'
ZHUGE_LIANG = 'san14-candidate-0440'
SIMA_YI = 'san14-candidate-0344'
SUN_LIU = ('wu', 'shu')
GUANZHONG_COALITION = ('ma_teng', 'han_sui')
JINGZHOU_OPENING = 'mainland219-07'
JINGZHOU_RUPTURE = (219, 10)
JINGZHOU_FRONT = (('nanjun', 'yidu', 'badong'), ('jiangxia', 'nanjun', 'yidu'))
SOUTHERN_FRONT = (('nanjun', 'wei'), ('jiangxia', 'shu'), ('wujun', 'wu'))
SOUTH_PRIORITY_UNTIL = (209, 3)
YILING_FRONT = (('badong', 'shu'), ('yidu', 'wu'), ('nanjun', 'wu'))
HANZHONG_HOLDINGS = (('hanzhong', 'wei'),)
RULES = {
    # White Horse is represented by the Dong commandery node on this map.
    GUANDU: ((200, 2), (200, 10), ('yuan_shao', 'wei'),
             (('wei', 'yuan_shao'), ('dongjun', 'wei'), ('yingchuan', 'wei'))),
    ALLIANCE: ((208, 10), (208, 12), (*SUN_LIU, 'wei'), SOUTHERN_FRONT),
    SOUTH: ((208, 12), (208, 12), ('wei', *SUN_LIU), SOUTHERN_FRONT),
    MARRIAGE: ((209, 12), (209, 12), ('shu', 'wu'), ()),
    TONGGUAN: ((211, 7), (211, 9), ('wei', *GUANZHONG_COALITION),
               (('hongnong', 'wei'), ('jingzhao', 'wei'), ('fengyi', 'ma_teng'),
                ('fufeng', 'ma_teng'), ('jincheng', 'han_sui'))),
    YILING: ((221, 7), (222, 6), ('shu', 'wu'), YILING_FRONT),
    HEFEI: ((215, 8), (215, 10), ('wu', 'wei'), (('hefei', 'wei'),)),
    HANZHONG_PREPARATION: ((217, 7), (217, 12), ('shu', 'wei'), HANZHONG_HOLDINGS),
    HANZHONG: ((218, 1), (219, 5), ('shu', 'wei'), HANZHONG_HOLDINGS),
    NANZHONG: ((225, 3), (225, 9), ('shu', 'nanman'),
               (('jianning', 'nanman'), ('zangke', 'nanman'))),
    LIAODONG: ((238, 1), (238, 8), ('wei', 'gongsun'),
               (('liaoxi', 'wei'), ('liaodong', 'gongsun'))),
    **{kind: (row.start, row.end, tuple(owner for owner, _ in row.leaders), row.holdings)
       for kind, row in CHAPTERS.items()},
}
RULE_LEADERS = {
    NANZHONG: (LIU_SHAN, MENG_HUO),
    LIAODONG: (CAO_RUI, GONGSUN_YUAN),
    **{kind: tuple(person for _, person in row.leaders) for kind, row in CHAPTERS.items()},
}
REQUIRED_OFFICERS = {
    HEFEI: ((ZHANG_LIAO, 'wei'),),
    HANZHONG_PREPARATION: ((FA_ZHENG, 'shu'),),
    NANZHONG: ((ZHUGE_LIANG, 'shu'),),
    LIAODONG: ((SIMA_YI, 'wei'),),
    **{kind: row.officers for kind, row in CHAPTERS.items()},
}
# The first side is the attacking faction. A connected, still-held approach
# is enough to start the event, even if another approach changed hands.
FRONTS = {
    HEFEI: (('danyang', 'lujiang'), ('hefei',)),
    HANZHONG_PREPARATION: (('zitong', 'baxi', 'jiameng'), ('hanzhong',)),
    HANZHONG: (('zitong', 'baxi', 'jiameng'), ('hanzhong',)),
    NANZHONG: (('zhuti', 'yuexi', 'yongchang', 'fuling', 'bajun'), ('jianning', 'zangke', 'yunnan')),
    LIAODONG: (('liaoxi',), ('liaodong',)),
    **{kind: (row.approaches, row.targets) for kind, row in CHAPTERS.items() if row.targets},
}
FRONT_PRIORITIES = (HEFEI, HANZHONG, NANZHONG, LIAODONG,
                    *(kind for kind, row in CHAPTERS.items() if row.targets))
FIRST_EVENT_YEAR = min(start[0] for start, _, _, _ in RULES.values())
LAST_EVENT_YEAR = max(end[0] for _, end, _, _ in RULES.values())
BATTLE_STAGES = {
    HEFEI_DEFENSE: (HEFEI, RULES[HEFEI][:2], 'hefei', None, ZHANG_LIAO),
    DINGJUN: (HANZHONG, ((219, 1), (219, 5)), 'hanzhong', HUANG_ZHONG, XIAHOU_YUAN),
}
EVENT_FACTIONS = {kind: factions[:2] if kind == ALLIANCE else factions
                  for kind, (_, _, factions, _) in RULES.items()}
EVENT_FACTIONS[ALLIANCE_ENDED] = SUN_LIU
EVENT_FACTIONS[HEFEI_DEFENSE] = ('wei', 'wu')
EVENT_FACTIONS[DINGJUN] = ('shu', 'wei')
EVENT_CITIES = {
    GUANDU: ('dongjun', 'wei', 'yingchuan'),
    ALLIANCE: ('jiangxia', 'wujun'),
    SOUTH: ('nanjun', 'jiangxia', 'wujun'),
    TONGGUAN: ('hongnong', 'fengyi', 'jingzhao', 'fufeng', 'jincheng'),
    YILING: ('badong', 'yidu', 'nanjun'),
    HEFEI: ('danyang', 'lujiang', 'hefei'),
    HEFEI_DEFENSE: ('hefei',),
    HANZHONG_PREPARATION: ('zitong', 'baxi', 'hanzhong'),
    HANZHONG: ('zitong', 'baxi', 'hanzhong'),
    DINGJUN: ('hanzhong',),
    NANZHONG: ('jianning', 'zangke', 'yunnan'),
    LIAODONG: ('liaoxi', 'liaodong'),
    **{kind: row.cities for kind, row in CHAPTERS.items()},
}
EVENT_PEOPLE = {
    MARRIAGE: (LEADERS['shu'], LADY_SUN, LEADERS['wu']),
    HEFEI: (LEADERS['wu'], LEADERS['wei'], ZHANG_LIAO),
    HEFEI_DEFENSE: (ZHANG_LIAO, LEADERS['wu']),
    HANZHONG_PREPARATION: (LEADERS['shu'], LEADERS['wei'], FA_ZHENG),
    DINGJUN: (HUANG_ZHONG, XIAHOU_YUAN),
    NANZHONG: (ZHUGE_LIANG, MENG_HUO),
    LIAODONG: (CAO_RUI, SIMA_YI, GONGSUN_YUAN),
    **{kind: row.people for kind, row in CHAPTERS.items()},
}
NOTES = {
    GUANDU: '袁绍与曹操在黄河沿线开战。双方依战局安排出征。',
    ALLIANCE: '孙权与刘备结盟抗曹，同盟期间两方不得相互出征。',
    SOUTH: '曹军以江陵为南下据点，战斗按实际行军和接敌结算。',
    MARRIAGE: '刘备与孙夫人联姻，孙尚香转属刘备。',
    TONGGUAN: '曹操西征，马超、韩遂在关中联合抗曹。',
    YILING: '刘备准备东征，战事由实际行军和交战决定。',
    ALLIANCE_ENDED: '荆州局势生变，孙刘同盟解除。',
    HEFEI: '孙权准备进兵合淝，诸军筹粮待发。',
    HEFEI_DEFENSE: '吴军抵达合肥，张辽随守军迎战。',
    HANZHONG_PREPARATION: '法正向刘备献策，蜀军筹备争夺汉中。',
    HANZHONG: '刘备筹划进兵汉中，魏军据守汉中。',
    DINGJUN: '黄忠和夏侯渊在汉中战场交锋。',
    NANZHONG: '诸葛亮与孟获在南中对峙，战事由实际交战决定。',
    LIAODONG: '曹叡下诏讨辽东，司马懿所在的魏军准备进兵襄平。',
    **{kind: row.note for kind, row in CHAPTERS.items()},
}


def _date(state):
    return state.year, state.month


def _historical(catalog):
    return (catalog.data.get('main_scenario') or {}).get('group') != 'if'


def _holds(state, holdings):
    return all(city in state.cities and state.cities[city].owner == owner
               for city, owner in holdings)


def _leader_ids(factions, kind=None):
    return RULE_LEADERS[kind] if kind in RULE_LEADERS else tuple(LEADERS[owner] for owner in factions)


def _event_people(kind):
    return EVENT_PEOPLE[kind] if kind in EVENT_PEOPLE else _leader_ids(EVENT_FACTIONS[kind])


def _has_leaders(state, factions, kind=None):
    leaders = state.extension['leaders']
    for owner, person_id in zip(factions, _leader_ids(factions, kind)):
        officer = state.officers.get(leaders.get(owner))
        if (officer is None or not officer.alive or officer.faction_id != owner
                or officer.person_id != person_id):
            return False
    return True


def _in_service(game, state, kind):
    for person, faction in REQUIRED_OFFICERS.get(kind, ()):
        officer = state.officers.get(game.catalog.ids.get(person))
        if officer is None or not officer.alive or officer.faction_id != faction:
            return False
    return True


def _front_open(game, state, kind):
    if kind not in FRONTS:
        return True
    approaches, targets = FRONTS[kind]
    # Xiapi has a campaign objective but no legal approach at its opening.
    if not approaches:
        return True
    attacker, defender = EVENT_FACTIONS[kind][:2]
    enemy_cities = {city for city in targets if _holds(state, ((city, defender),))}
    return any(_holds(state, ((source, attacker),))
               and enemy_cities.intersection(game._neighbors(source, state)) for source in approaches)


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


def _marriage_transfer(game, state):
    if (state.phase != 'city' or not _alliance_active(state)
            or any(side in state.extension['pending_succession'] for side in SUN_LIU)):
        return ()
    ident = game.catalog.ids.get(LADY_SUN)
    officer = state.officers.get(ident)
    leader = state.extension['leaders']['shu']
    if (officer is None or not officer.alive or officer.faction_id != 'wu'
            or game._march_ids(state).intersection((ident, leader))):
        return ()
    source = next((city for city in state.cities.values()
                   if city.owner == 'wu' and ident in city.roster.officer_ids), None)
    target = next((city for city in state.cities.values()
                   if city.owner == 'shu' and leader in city.roster.officer_ids), None)
    if source is None or target is None or game._city_occupancy(state, target) >= game.catalog.rules.city_officer_capacity:
        return ()
    transfer_officers(source.roster, target.roster, [ident])
    officer.faction_id = 'shu'
    return source.id, target.id


def _record(game, state, receipts, kind, cities):
    state.extension.setdefault(RECEIPTS, receipts)
    receipts[kind] = state.turn
    factions = EVENT_FACTIONS[kind]
    # Launched marches retain their original travel receipts.
    if kind not in BATTLE_STAGES and kind != HANZHONG_PREPARATION:
        for owner in factions:
            state.extension['ai_strategy'].pop(owner, None)
    game._emit_event(state, kind, city_ids=cities, factions=factions, audience='world',
                     person_ids=_event_people(kind))
    game._note(state, NOTES[kind])


def process(game, state):
    if (state.phase not in ('city', 'arrivals') or not FIRST_EVENT_YEAR <= state.year <= LAST_EVENT_YEAR
            or not _historical(game.catalog)):
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
        if any(city not in state.cities for city in EVENT_CITIES.get(kind, ())):
            continue
        if (not _holds(state, holdings) or not _has_leaders(state, factions, kind)
                or not _in_service(game, state, kind) or not _front_open(game, state, kind)):
            continue
        if kind == YILING and _alliance_active(state):
            _record(game, state, receipts, ALLIANCE_ENDED, ('badong', 'yidu'))
        cities = _marriage_transfer(game, state) if kind == MARRIAGE else EVENT_CITIES[kind]
        if cities:
            _record(game, state, receipts, kind, cities)


def process_battle(game, state):
    receipts = state.extension.get(RECEIPTS)
    if not receipts or state.phase != 'battle':
        return
    battle = state.battle
    for kind, (parent, (start, end), city, attacker, defender) in BATTLE_STAGES.items():
        if kind in receipts or parent not in receipts or not start <= _date(state) <= end:
            continue
        if (battle['target'] != city
                or (battle['attacker'], battle['defender']) != EVENT_FACTIONS[parent]):
            continue
        if not _has_leaders(state, EVENT_FACTIONS[parent], parent):
            continue
        attacking = {state.officers[unit['id']].person_id for unit in battle['attackers']}
        defending = {state.officers[unit['id']].person_id for unit in battle['defenders']}
        if (attacker is None or attacker in attacking) and defender in defending:
            _record(game, state, receipts, kind, (city,))


def _alliance_active(state):
    receipts = state.extension.get(RECEIPTS, {})
    if ALLIANCE_ENDED in receipts or not (ALLIANCE in receipts or ALLIANCE_CONTINUING in receipts):
        return False
    ended = state.extension['ended_factions']
    return all(faction not in ended for faction in (*SUN_LIU, 'wei'))


def _tongguan_active(state):
    return (TONGGUAN in state.extension.get(RECEIPTS, {}) and _date(state) <= RULES[TONGGUAN][1]
            and not any(owner in state.extension['ended_factions'] for owner in EVENT_FACTIONS[TONGGUAN]))


def historical_allied(state, first, second):
    if first == second:
        return False
    return ((first in SUN_LIU and second in SUN_LIU and _alliance_active(state))
            or (first in GUANZHONG_COALITION and second in GUANZHONG_COALITION and _tongguan_active(state)))


def alliances(state):
    if state is None:
        return []
    from . import diplomacy
    scripted = [list(pair) for pair in (SUN_LIU, GUANZHONG_COALITION) if historical_allied(state, *pair)]
    return scripted + [pair for pair in diplomacy.alliances(state) if not historical_allied(state, *pair)]


def allied(state, first, second):
    from . import diplomacy
    return historical_allied(state, first, second) or (first != second and diplomacy.allied(state, first, second))


def transit_allowed(state, owner, other):
    return other in {owner, 'neutral'} or allied(state, owner, other)


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
    for kind in FRONT_PRIORITIES:
        if kind in receipts and _date(state) <= RULES[kind][1] and not any(
                owner in ended for owner in EVENT_FACTIONS[kind]):
            return kind
    return None


def priority_factions(state):
    event = _priority_event(state)
    if event in (SOUTH, YILING, *FRONT_PRIORITIES):
        return EVENT_FACTIONS[event][:1]
    return EVENT_FACTIONS.get(event, ())


def priority_targets(state, owner, targets):
    event = _priority_event(state)
    if owner not in priority_factions(state):
        return set(), None
    sides = EVENT_FACTIONS[event][:2] if event in FRONT_PRIORITIES else EVENT_FACTIONS[event]
    opponents = [faction for faction in sides
                 if faction != owner and not allied(state, owner, faction)]
    eligible = {key for key in targets if state.cities[key].owner in opponents}
    if event in FRONT_PRIORITIES:
        front = FRONTS[event][1]
        eligible.intersection_update(front)
        return eligible, next((city for city in front if city in eligible), None)
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
        if kind in BATTLE_STAGES:
            parent, (start, end), city, _, _ = BATTLE_STAGES[kind]
            parent_turn = receipts.get(parent)
            if (type(parent_turn) is not int or parent_turn > turn or not start <= date <= end
                    or city not in state.cities or any(person not in catalog.ids for person in _event_people(kind))):
                raise ValueError('Historical battle receipt')
            continue
        start, end, factions, holdings = RULES[kind]
        if (not start <= date <= end
                or not set(factions) <= set(catalog.factions)
                or any(city not in state.cities for city in EVENT_CITIES.get(kind, ()))
                or any(city not in state.cities for city, _ in holdings)
                or any(person not in catalog.ids for person in (*_leader_ids(factions, kind), *_event_people(kind)))):
            raise ValueError('Historical campaign receipt')
    if SOUTH in receipts and (ALLIANCE not in receipts or receipts[ALLIANCE] > receipts[SOUTH]):
        raise ValueError('Historical alliance must precede the southern campaign')
    if MARRIAGE in receipts and (ALLIANCE not in receipts or receipts[ALLIANCE] >= receipts[MARRIAGE]):
        raise ValueError('Historical alliance must precede the marriage')


def validate_event(catalog, state, row):
    kind = row['kind']
    turn = state.extension.get(RECEIPTS, {}).get(kind)
    factions = EVENT_FACTIONS[kind]
    cities = row['city_ids']
    if kind == ALLIANCE_ENDED:
        cities_ok = (len(cities) == 2 and cities[0] != cities[1]
                     and all(city in side for city, side in zip(cities, JINGZHOU_FRONT)))
    elif kind == MARRIAGE:
        cities_ok = len(cities) == 2 and cities[0] != cities[1]
    else:
        cities_ok = cities == list(EVENT_CITIES[kind])
    if (type(turn) is not int or row['turn'] != turn or row['audience'] != 'world' or row['details']
            or (row['year'], row['month']) != _turn_date(catalog, turn)
            or row['day'] != 1 + 10 * ((turn - 1) % 3)
            or row['factions'] != list(factions) or not cities_ok
            or row['person_ids'] != list(_event_people(kind))):
        raise ValueError('Historical campaign event')
