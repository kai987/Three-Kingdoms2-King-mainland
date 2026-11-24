"""Runan's two rendezvous, counterattacks and retreat in the Guandu campaign."""
from . import command_books, officer_relations
from .errors import GameError
from .officers import OFFICER_TROOP_CAP, recruitment_loyalty, transfer_officers

SCENARIO = 'mainland200-01'
RUNAN = 'runan'
REFUGE_CITY = 'yiyang'
LIU_BIAO_SEAT = 'xiangyang'
UPRISING = 'historical_runan_uprising'
FIRST_JOIN = 'historical_runan_liu_pi_joins'
SECOND_JOIN = 'historical_runan_gong_du_joins'
CAI_SENT = 'runan_cai_yang_sent'
CAI_DEFEATED = 'historical_runan_cai_yang_defeated'
CAO_EXPEDITION = 'historical_runan_cao_expedition'
REFUGE = 'historical_runan_liu_biao_refuge'
JULY = (200, 7)
SEPTEMBER = (201, 9)
LIU_BEI = 'san14-candidate-0952'
LIU_PI = 'san14-candidate-0958'
GONG_DU = 'san14-candidate-0208'
YUAN_SHAO = 'san14-candidate-0035'
CAO_CAO = 'san14-candidate-0521'
CAI_YANG = 'historical-cai-yang-runan'
LIU_BIAO = 'san14-candidate-0953'
CAI_YANG_ID = 1199
LOCAL_RECRUITS = 500
PEOPLE = {
    UPRISING: (LIU_PI, YUAN_SHAO, LIU_BEI),
    FIRST_JOIN: (LIU_BEI, LIU_PI),
    SECOND_JOIN: (LIU_BEI, GONG_DU),
    CAI_DEFEATED: (LIU_BEI, GONG_DU, CAI_YANG),
    CAO_EXPEDITION: (CAO_CAO, LIU_BEI, GONG_DU),
    REFUGE: (LIU_BEI, LIU_BIAO, GONG_DU),
}
FACTIONS = {
    **dict.fromkeys((UPRISING, FIRST_JOIN, SECOND_JOIN), ('yuan_shao', 'shu', 'wei')),
    **dict.fromkeys((CAI_DEFEATED, CAO_EXPEDITION), ('wei', 'shu', 'yuan_shao')),
    REFUGE: ('shu', 'liu_biao', 'wei'),
}
CITIES = {**dict.fromkeys(PEOPLE, (RUNAN,)), REFUGE: (RUNAN, REFUGE_CITY)}
NOTES = {
    UPRISING: '汝南黄巾刘辟起兵响应袁绍，袁绍遣刘备率部往援。',
    FIRST_JOIN: '刘备率军抵达汝南，与刘辟所部会合抗曹。',
    SECOND_JOIN: '刘备再至汝南，与龚都所部合兵。',
    CAI_DEFEATED: '刘备与龚都所部守住汝南，蔡阳在这次征讨中战死。',
    CAO_EXPEDITION: '建安六年秋，曹操亲率所部向汝南进军。',
    REFUGE: '刘备退出汝南，刘表接纳其部驻防荆州。龚都部众溃散，其本人下落不明。',
}
JOIN_DETAILS = {'troops', 'deployed'}
REFUGE_DETAILS = {'dispersed'}
SCRIPTED_EXITS = {CAI_YANG: CAI_DEFEATED, GONG_DU: REFUGE}


def configure_catalog(data):
    """Supply the two historical roster corrections only in the Guandu opening."""
    if data['id'] != SCENARIO:
        return
    people = data['people']
    existing = [row for row in people
                if row['runtime_id'] == CAI_YANG_ID or row['person_id'] == CAI_YANG]
    if existing and [(row['runtime_id'], row['person_id']) for row in existing] != [(CAI_YANG_ID, CAI_YANG)]:
        raise ValueError('Runan officer identity is already in use')
    gong = next((row for row in people if row['person_id'] == GONG_DU), None)
    if gong is None:
        return  # A reduced test catalog may leave out the Runan cast.
    source = 'https://zh.wikisource.org/zh-hant/資治通鑑/卷064'
    gong['death_year'] = 201
    gong['chronology_basis'] = '《資治通鑑》載建安六年曹操擊汝南時龔都部眾散去，龔都下落不詳。201年是本劇本的退場界線。'
    gong['chronology_design'] = dict(historical_death_year=None, last_attested_year=201, retirement_year=201)
    for row in data.get('initial_free_officers', ()):
        if row['person_id'] == GONG_DU:
            row['resolve_death_year'] = False
    if existing:
        return  # A catalog derived from a loaded catalog already includes Cai Yang.
    cai_source = 'https://zh.wikisource.org/zh-hant/三國志/卷32'
    people.append(dict(
        person_id=CAI_YANG, runtime_id=CAI_YANG_ID, name='蔡阳', aliases=['蔡陽', '蔡揚', '蔡扬', 'さいよう'],
        birth_year=165, service_year=200, death_year=201,
        chronology_basis='《三國志·先主傳》記蔡陽奉曹操命討劉備而戰死。出生年為遊戲估值，出仕年用本劇本開局。',
        chronology_design=dict(historical_birth_year=None, historical_death_year=201),
        profile=dict(health_max=80, martial_strength=62, intellect=47, virtue=60, terrain_affinity=0),
        virtue_design=dict(status='configured_default', virtue=60),
        ability_source=dict(kind='historical_authorial_game_design', source_urls=[cai_source, source],
                            notes='蔡陽奉曹操之命進攻汝南，為劉備一方所破。能力值採本作相容尺度，德按缺少數值時的60設定。')))
    data['officer_count'] += 1
    data['appearance_locations'][CAI_YANG] = 'yingchuan'
    data.setdefault('appearance_windows', {})[CAI_YANG] = [
        dict(start=list(JULY), end=[201, 9], city='yingchuan', faction='wei', resolve_death_year=True)]
    basis = 'historical_runan_campaign'
    certainty = 'historical_career_with_opening_station_inference'
    data['era_assignments'][CAI_YANG] = dict(
        source_status='historical_named_supplement', status='future', year_state='available',
        faction='wei', city='yingchuan', death_year_resolved=False,
        placement_basis=basis, planning_complete=True, posting_reference=None,
        placement_review=dict(basis=basis, historical_certainty=certainty, source_urls=[cai_source],
                              note='遊戲安排七月起在曹軍出仕，準備汝南征討。'),
        appearance_plan=dict(start=list(JULY), end=[201, 9], city='yingchuan', status='future', basis=basis))
    if completion := data.get('placement_completion'):
        completion['people'] += 1
        completion['future_plans'] += 1
        completion['reference_classes'][certainty] = completion['reference_classes'].get(certainty, 0) + 1
        completion['bases'][basis] = 1
    if coverage := data.get('coverage'):
        for key in ('library', 'configured_profiles', 'health_configured', 'affinity_configured',
                    'default_virtue_profiles', 'new_historical_people', 'placement_plans', 'future_plans'):
            if key in coverage:
                coverage[key] += 1
    from .equipment import build_initials
    data['equipment_initial'].update(build_initials(people[-1:], ()))


def migrate_calendar(catalog, state):
    """Keep already-retired Gong Du retired in a save from the earlier roster."""
    if catalog.data['id'] != SCENARIO:
        return
    previous = f'remove_after_death_year:{GONG_DU}:201'
    officer = state.officers.get(catalog.ids.get(GONG_DU))
    if previous in state.year_events and officer is not None and not officer.alive:
        state.year_events.remove(previous)
        if state.calendar_cursor > 201:
            current = f'remove_after_death_year:{GONG_DU}:202'
            if current not in state.year_events:
                state.year_events.append(current)


def _date(state):
    return state.year, state.month


def _is_ruler(state, faction, person):
    ident = state.extension['leaders'].get(faction)
    officer = state.officers.get(ident)
    return bool(officer and officer.alive and officer.person_id == person and officer.faction_id == faction)


def _commander(game, state):
    commander = state.officers.get(game.catalog.ids.get(LIU_BEI))
    if not commander or not commander.alive or commander.health <= 0:
        return None
    owner = commander.faction_id
    if (owner == 'shu' and _is_ruler(state, 'shu', LIU_BEI)
            or owner == 'yuan_shao' and _is_ruler(state, 'yuan_shao', YUAN_SHAO)):
        return commander
    return None


def _local_officer(game, state, target, person, *, unavailable=None):
    ident = game.catalog.ids.get(person)
    officer = state.officers.get(ident)
    if officer is None or not officer.alive or officer.health <= 0:
        return None
    if officer.faction_id is None and state.extension['free_locations'].get(str(ident)) == target.id:
        return officer
    # A Cao recruit still stationed locally may take part in the historical revolt.
    if (officer.faction_id == target.owner == 'wei' and ident in target.roster.officer_ids
            and ident != state.extension['leaders'].get('wei')):
        unavailable = game._march_ids(state) if unavailable is None else unavailable
        if ident not in unavailable:
            return officer
    return None


def process(game, state, receipts):
    """Commit the July uprising once on the shared strategic event boundary."""
    from .historical_campaigns import _record, allied

    if game.catalog.data['id'] != SCENARIO or _date(state) != JULY or UPRISING in receipts:
        return
    target = state.cities.get(RUNAN)
    commander = _commander(game, state)
    if (commander is None or target is None or target.owner != 'wei'
            or not _is_ruler(state, 'wei', CAO_CAO) or not _is_ruler(state, 'yuan_shao', YUAN_SHAO)
            or allied(state, 'yuan_shao', 'wei') or allied(state, commander.faction_id, 'wei')
            or not _local_officer(game, state, target, LIU_PI)):
        return
    _record(game, state, receipts, UPRISING, (RUNAN,))


def dispatch(game, state):
    """Post each named expedition once it can travel and feed its army."""
    from .historical_campaigns import RECEIPTS, _record, allied

    if game.catalog.data['id'] != SCENARIO:
        return
    receipts = state.extension.get(RECEIPTS, {})
    if (UPRISING not in receipts or RUNAN not in state.cities or REFUGE in receipts
            or SECOND_JOIN in receipts and _date(state) > (201, 12)):
        return
    commander = _commander(game, state)
    target = state.cities[RUNAN]
    if commander is None or allied(state, commander.faction_id, 'wei'):
        return
    unavailable = game._march_ids(state)
    if (FIRST_JOIN not in receipts and target.owner == 'wei' and _is_ruler(state, 'yuan_shao', YUAN_SHAO)
            and not allied(state, 'yuan_shao', 'wei')
            and _local_officer(game, state, target, LIU_PI, unavailable=unavailable)):
        _send(game, state, target, commander, unavailable)
        return
    if (SECOND_JOIN not in receipts or target.owner != commander.faction_id
            or not _is_ruler(state, 'wei', CAO_CAO)
            or not _runan_defenders(game, state, target, commander, unavailable)):
        return
    now = _date(state)
    if CAI_SENT not in receipts and now <= SEPTEMBER:
        officer = state.officers.get(game.catalog.ids.get(CAI_YANG))
        if officer and officer.alive and officer.faction_id == 'wei' and _send(game, state, target, officer, unavailable):
            receipts[CAI_SENT] = state.turn
    elif CAI_DEFEATED in receipts and CAO_EXPEDITION not in receipts and SEPTEMBER <= now <= (201, 12):
        cao = state.officers[game.catalog.ids[CAO_CAO]]
        if _send(game, state, target, cao, unavailable):
            _record(game, state, receipts, CAO_EXPEDITION, (RUNAN,))


def _runan_defenders(game, state, target, commander, unavailable):
    gong = game.catalog.ids[GONG_DU]
    return {commander.runtime_id, gong} <= set(target.roster.officer_ids) - unavailable


def _send(game, state, target, commander, unavailable):
    owner, ident = commander.faction_id, commander.runtime_id
    used = state.extension['officer_actions']
    if (ident in unavailable or commander.health <= 0 or used.get(str(ident)) == state.turn
            or owner in state.extension['pending_succession']):
        return False
    home = next((city for city in state.cities.values()
                 if city.owner == owner and ident in city.roster.officer_ids), None)
    if home is None:
        return False
    neighbors = game._neighbors(RUNAN, state)
    if home.id not in neighbors:
        if not command_books.can_spend(state, owner, 'transfer'):
            return False
        destinations = []
        for key in neighbors:
            staging = state.cities[key]
            if staging.owner != owner or game._city_occupancy(state, staging) >= game.catalog.rules.city_officer_capacity:
                continue
            route = game._travel_path(state, home.id, key, owner, 'fastest')
            if route:
                destinations.append((route['days'], key))
        if destinations:
            try:
                game._queue_march(state, home, state.cities[min(destinations)[1]], [ident], 'transfer', 'fastest')
            except GameError:
                pass
        return False
    if not command_books.can_spend(state, owner, 'depart'):
        return False
    joint = game._allied_attack_info(state, target, owner)
    if joint and not joint['remaining']:
        return False
    troops, reserves = commander.troops, home.reserves
    if not troops:
        if not reserves:
            return False
        commander.troops = min(LOCAL_RECRUITS, reserves)
        home.reserves -= commander.troops
    try:
        game._queue_march(state, home, target, [ident], 'attack', 'fastest')
    except GameError:
        commander.troops, home.reserves = troops, reserves
        return False
    if owner != state.player:
        game._report_ai(state, home, 'attack', target.id)
    return True


def join_on_arrival(game, state, target, columns, *, battle_slots=0):
    """Only a completed Liu Bei column can trigger either local enlistment."""
    if target.id != RUNAN or game.catalog.data['id'] != SCENARIO:
        return None
    from .historical_campaigns import RECEIPTS, _record

    receipts = state.extension.get(RECEIPTS, {})
    if UPRISING not in receipts or SECOND_JOIN in receipts:
        return None
    commander = _commander(game, state)
    if commander is None or target.owner not in ('wei', commander.faction_id):
        return None
    owner, ident = commander.faction_id, commander.runtime_id
    column = next((row for row in columns if row['owner'] == owner and row['quote']['path'][0] != RUNAN
                   and ident in row['officers']), None)
    joined_turn = receipts.get(FIRST_JOIN)
    if column is None or (joined_turn is not None and state.turn <= joined_turn):
        return None
    kind, person = (FIRST_JOIN, LIU_PI) if joined_turn is None else (SECOND_JOIN, GONG_DU)
    officer = _local_officer(game, state, target, person)
    muster = target if target.owner == owner else state.cities[column['source']]
    if (officer is None or muster.owner != owner
            or game._city_occupancy(state, muster) >= game.catalog.rules.city_officer_capacity):
        return None
    recruit = officer.runtime_id
    if officer.faction_id == 'wei':
        target.roster.officer_ids.remove(recruit)
    else:
        del state.extension['free_locations'][str(recruit)]
    officer.faction_id = owner
    officer.loyalty = recruitment_loyalty(commander.profile.virtue, officer.loyalty)
    previous = officer.troops
    officer.troops = max(previous, LOCAL_RECRUITS)
    state.soldiers['recruited'] += officer.troops - previous
    muster.roster.officer_ids.append(recruit)
    state.extension['officer_actions'][str(recruit)] = state.turn
    officer_relations.apply(game, state, recruit)
    deployed = battle_slots > 0
    _record(game, state, receipts, kind, (RUNAN,), details=dict(troops=officer.troops, deployed=deployed))
    return (recruit, muster.id) if deployed else None


def settle_cai_defeat(game, state, battle):
    if (game.catalog.data['id'] != SCENARIO or battle['target'] != RUNAN
            or battle['attacker'] != 'wei' or battle['outcome'] != 'defeat'):
        return
    from .dated_events import _retire
    from .historical_campaigns import RECEIPTS, _record

    receipts = state.extension.get(RECEIPTS, {})
    if CAI_SENT not in receipts or CAI_DEFEATED in receipts:
        return
    cai = game.catalog.ids[CAI_YANG]
    officer = state.officers.get(cai)
    target = state.cities[RUNAN]
    leader = _commander(game, state)
    if (officer and officer.alive and officer.faction_id == 'wei'
            and any(unit['id'] == cai for unit in battle['attackers'])
            and leader and target.owner == leader.faction_id == battle['defender']
            and _runan_defenders(game, state, target, leader, game._march_ids(state))):
        _retire(game, state, CAI_YANG)
        _record(game, state, receipts, CAI_DEFEATED, (RUNAN,))


def refuge_plan(game, state, battle):
    """Liu Biao can offer a posting only while he still holds the approach."""
    if (game.catalog.data['id'] != SCENARIO or battle['target'] != RUNAN
            or battle['attacker'] != 'wei'):
        return None
    from .historical_campaigns import RECEIPTS

    receipts = state.extension.get(RECEIPTS, {})
    if CAO_EXPEDITION not in receipts or REFUGE in receipts:
        return None
    cao = game.catalog.ids[CAO_CAO]
    if not any(unit['id'] == cao for unit in battle['attackers']) or not _is_ruler(state, 'wei', CAO_CAO):
        return None
    target = state.cities[RUNAN]
    refuge = state.cities.get(REFUGE_CITY)
    host = state.cities.get(LIU_BIAO_SEAT)
    leader = _commander(game, state)
    if (leader is None or leader.faction_id != target.owner
            or refuge is None or host is None or refuge.owner != host.owner
            or host.owner != 'liu_biao' or not _is_ruler(state, 'liu_biao', LIU_BIAO)):
        return None
    unavailable = game._march_ids(state)
    if (not _runan_defenders(game, state, target, leader, unavailable)
            or unavailable.intersection(refuge.roster.officer_ids)
            or game._city_occupancy(state, host) + len(refuge.roster.officer_ids) > game.catalog.rules.city_officer_capacity
            or not game._travel_path(state, RUNAN, REFUGE_CITY, 'liu_biao')):
        return None
    members = set(target.roster.officer_ids) - unavailable - {game.catalog.ids[GONG_DU]}
    if leader.faction_id == 'yuan_shao':
        if 'shu' not in state.extension['ended_factions']:
            return None
        opening = game.catalog.data['initial_owners']
        retainers = {game.catalog.ids[row['person_id']] for row in game.catalog.data['initial_officers']
                     if opening[row['city']] == 'shu'}
        members &= retainers | {leader.runtime_id, game.catalog.ids[LIU_PI]}
    return leader.runtime_id, [ident for ident in target.roster.officer_ids if ident in members]


def settle_refuge(game, state, plan):
    from . import diplomacy
    from .dated_events import _retire
    from .historical_campaigns import RECEIPTS, _record

    ruler, members = plan
    target, refuge, host = (state.cities[key] for key in (RUNAN, REFUGE_CITY, LIU_BIAO_SEAT))
    gong = state.officers[game.catalog.ids[GONG_DU]]
    dispersed = gong.troops
    state.soldiers['lost'] += dispersed
    gong.troops = 0
    _retire(game, state, GONG_DU)
    transfer_officers(refuge.roster, host.roster, list(refuge.roster.officer_ids))
    transfer_officers(target.roster, refuge.roster, members)
    refuge.owner = 'shu'
    ended = state.extension['ended_factions']
    if 'shu' in ended:
        ended.remove('shu')
    for ident in members:
        state.officers[ident].faction_id = 'shu'
        state.extension['officer_actions'][str(ident)] = state.turn
    state.extension['leaders']['shu'] = ruler
    state.officers[ruler].loyalty = 100
    officer_relations.apply_faction(game, state, 'shu')
    pool = diplomacy._pool(state)
    pair = diplomacy._pair('shu', 'liu_biao')
    pool['relations'][pair] = max(diplomacy.FRIENDLY, pool['relations'].get(pair, 0))
    pool['treaties'][pair] = max(state.turn + 36, pool['treaties'].get(pair, 0))
    receipts = state.extension[RECEIPTS]
    _record(game, state, receipts, REFUGE, CITIES[REFUGE], details=dict(dispersed=dispersed))


def valid_receipt(catalog, kind, turn, date, receipts):
    if catalog.data['id'] != SCENARIO or RUNAN not in catalog.map_cities:
        return False
    if kind == CAI_SENT:
        second = receipts.get(SECOND_JOIN)
        return type(second) is int and second <= turn and date <= SEPTEMBER and CAI_YANG in catalog.ids
    if (any(city not in catalog.map_cities for city in CITIES[kind])
            or any(faction not in catalog.factions for faction in FACTIONS[kind])
            or any(person not in catalog.ids for person in PEOPLE[kind])):
        return False
    if kind == UPRISING:
        return date == JULY
    uprising = receipts.get(UPRISING)
    if type(uprising) is not int or uprising > turn or date < JULY:
        return False
    if kind == FIRST_JOIN:
        return True
    parents = {SECOND_JOIN: FIRST_JOIN, CAI_DEFEATED: CAI_SENT,
               CAO_EXPEDITION: CAI_DEFEATED, REFUGE: CAO_EXPEDITION}
    parent = receipts.get(parents[kind])
    if type(parent) is not int or not uprising <= parent <= turn:
        return False
    if kind == CAO_EXPEDITION:
        return SEPTEMBER <= date <= (201, 12)
    return parent < turn


def valid_details(kind, details):
    if kind == REFUGE:
        return (set(details) == REFUGE_DETAILS and type(details['dispersed']) is int
                and 0 <= details['dispersed'] <= OFFICER_TROOP_CAP)
    if kind not in (FIRST_JOIN, SECOND_JOIN):
        return details == {}
    return (set(details) == JOIN_DETAILS and type(details['troops']) is int
            and LOCAL_RECRUITS <= details['troops'] <= OFFICER_TROOP_CAP
            and type(details['deployed']) is bool)
