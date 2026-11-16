"""Historical succession preferences keyed by the ruler's canonical identity.

Ordinary vacancies use these preferences when a recorded successor is available.
The opening roster and save format are independent of this policy.
"""
from collections import defaultdict

from . import officer_relations
from .officers import parse_officer_ref


def _person(number):
    return f'san14-candidate-{number:04d}'


# The source catalogs preserve the game transcription and its save hash.
# Wu 59 places Sun Deng's designation in 221, after Sun Quan was made king.
# Wu 47–48 place Sun Liang's accession in 252, after his 250 designation.
_EARLIER_APPEARANCES = {
    _person(570): (223, (221, 11)),
    _person(578): (253, (252, 1)),
}
_SUN_QUAN_DEATH = (252, 4)


def apply_appearance_corrections(data):
    """Use reviewed heir dates while keeping each scenario's location and roster."""
    corrections = {}
    for person in data['people']:
        entry = _EARLIER_APPEARANCES.get(person['person_id'])
        if entry is None:
            continue
        source_year, start = entry
        if person['service_year'] != source_year:
            continue
        pid = person['person_id']
        person['service_year'] = start[0]
        person['chronology_basis'] = 'historical_succession_appearance_correction'
        corrections[pid] = (source_year, start[0])
        for window in data.get('appearance_windows', {}).get(pid, ()):
            if window['start'] == [source_year, 1]:
                window['start'] = list(start)
        plan = data.get('era_assignments', {}).get(pid, {}).get('appearance_plan') or {}
        if plan.get('start') == [source_year, 1]:
            plan['start'] = list(start)
    return corrections


def migrate_appearance_receipts(catalog, state):
    """Move only the two corrected service-year receipts in pre-existing saves."""
    opening = catalog.data['start_year']
    for pid, (old, new) in catalog.appearance_year_corrections.items():
        old_key = f'service_eligible:{pid}:{old}'
        new_key = f'service_eligible:{pid}:{new}'
        old_due = opening < old <= state.calendar_cursor
        new_due = opening < new <= state.calendar_cursor
        if old_due and state.year_events.count(old_key) == 1 and new_key not in state.year_events:
            state.year_events.remove(old_key)
            if new_due:
                state.year_events.append(new_key)
        elif new_due and not old_due and new_key not in state.year_events and old_key not in state.year_events:
            state.year_events.append(new_key)


def process_ruler_death(game, state):
    """Settle Sun Quan's documented death month for a surviving Wu court."""
    if state.year != _SUN_QUAN_DEATH[0] or state.month < _SUN_QUAN_DEATH[1]:
        return
    if state.extension.get('lifespan') == 'none':
        return
    pid = _person(553)
    ident = game.catalog.ids.get(pid)
    ruler = state.officers.get(ident)
    if ruler is None or not ruler.alive or ruler.faction_id not in {'wu', 'sun_jian'}:
        return
    if state.extension['leaders'].get(ruler.faction_id) != ident:
        return
    from .dated_events import _retire
    released = _retire(game, state, pid)
    game._note(state, f'{game.person_name(state, ident)}于本月到达史料记载的寿命边界，释放兵员{released}归原城。')


# Chen Shou, Records of the Three Kingdoms, chapters 2–4, 6, 8, 31–36, 46–48, 59.
# Each pair is a rostered nominee, and the earliest month they can be admitted
# directly from a free roster in a city the faction still holds, if documented.
_SUCCESSORS = {
    ('wei', _person(526)): ((501, (226, 5)), (533, None)),  # Cao Pi → Cao Rui, Cao Lin
    ('wei', _person(501)): ((529, (239, 1)),),  # Cao Rui → adopted son Cao Fang
    ('wei', _person(529)): ((530, (254, 10)),),  # Cao Fang → Cao Mao
    ('wei', _person(530)): ((503, (260, 6)),),  # Cao Mao → Cao Huan
    ('shu', _person(952)): ((945, (223, 5)), (924, None), (964, None)),  # Liu Bei's sons
    ('wu', _person(557)): ((553, (200, 4)),),  # Sun Ce → younger brother Sun Quan
    ('wu', _person(578)): ((548, (258, 10)),),  # Sun Liang → older brother Sun Xiu
    ('wu', _person(548)): ((554, (264, 7)),),  # Sun Xiu → nephew Sun Hao
    ('liu_yan', _person(925)): ((938, (194, 12)),),  # Liu Yan → Liu Zhang
    ('liu_biao', _person(953)): ((946, (208, 8)), (929, None)),  # Liu Cong, then Liu Qi
    ('yuan_shao', _person(35)): ((34, (202, 5)), (37, None)),  # Yuan Shang, then Yuan Tan
    ('gongsun', _person(268)): ((264, (204, 12)),),  # Gongsun Du → Gongsun Kang
    ('gongsun', _person(264)): ((263, None),),  # Gongsun Kang → younger brother Gongsun Gong
    ('ma_teng', _person(771)): ((769, (208, 12)),),  # Ma Chao took command of his father's troops
    ('zhang_ji', _person(638)): ((625, (196, 12)),),  # Zhang Ji → kinsman Zhang Xiu
}


def _order(faction, ruler, now):
    if faction == 'sun_jian':
        faction = 'wu'
    if faction == 'wu' and ruler == _person(551):
        # In a continuous campaign the surviving Sun faction can pass to Sun Ce.
        return ((557, None),)
    if faction == 'wei' and ruler == _person(521):
        eldest = (510, None)
        heir = (526, (220, 1))
        other_sons = ((515, None), (516, None), (531, None), (500, None))
        first = (eldest, heir) if now < (217, 10) else (heir, eldest)
        return first + other_sons
    if faction == 'shu' and ruler == _person(945) and now >= (238, 1):
        return ((943, (238, 1)), (941, None))  # Crown prince Liu Xuan, then Liu Chen
    if faction == 'wu' and ruler == _person(553):
        if now >= (250, 11):
            return ((578, (252, 1)),)  # Sun Liang has already been named crown prince
        if (242, 1) <= now < (250, 8):
            return ((542, (242, 1)),)  # Sun He until his deposition
        if (221, 1) <= now < (242, 1):
            return ((570, (221, 1)),)  # Sun Deng was crown prince until his death
    return _SUCCESSORS.get((faction, ruler), ())


def nominee_city(game, state, faction, ident):
    """Return the nominee’s own-faction city if it can admit them."""
    officer = state.officers.get(ident)
    if officer is None or not officer.alive or officer.faction_id is not None:
        return None
    location = state.extension['free_locations'].get(str(ident))
    city = state.cities.get(location)
    if city and city.owner == faction and game._city_occupancy(state, city) < game.catalog.rules.city_officer_capacity:
        return city
    return None


def admit_nominee(game, state, faction, ident):
    """Retain a serving nominee or admit a documented free nominee in place."""
    officer = state.officers.get(ident)
    if officer is not None and officer.alive and officer.faction_id == faction:
        return True
    city = nominee_city(game, state, faction, ident)
    if city is None:
        return False
    state.officers[ident].faction_id = faction
    city.roster.officer_ids.append(ident)
    del state.extension['free_locations'][str(ident)]
    return True


def historical_order(game, state, faction, previous):
    ruler = state.officers.get(previous)
    if ruler is None:
        return ()
    now = (state.year, state.month)
    return tuple((game.catalog.ids.get(_person(number)), admission)
                 for number, admission in _order(faction, ruler.person_id, now))


def preferred_successor(game, state, faction, previous, alive, *, excluded=()):
    now = (state.year, state.month)
    for ident, admission in historical_order(game, state, faction, previous):
        if ident in excluded:
            continue
        if ident in alive:
            return ident
        if admission is not None and now >= admission and nominee_city(game, state, faction, ident):
            return ident
    return None


def validate_recruit_offer(game, state, faction, pending):
    previous = pending['previous']
    ruler = state.officers.get(previous)
    recruit = pending['recruit']
    if (ruler is None or ruler.alive or state.extension['leaders'][faction] != previous
            or pending['provisional'] is not None or pending['previous_loyalty'] != 0
            or not isinstance(recruit, dict) or set(recruit) != {'officer', 'city', 'declined'}
            or not isinstance(recruit['declined'], list)):
        raise ValueError('Invalid succession recruitment offer')
    ident = parse_officer_ref(recruit['officer'], game.catalog.rules)
    declined = [parse_officer_ref(candidate, game.catalog.rules) for candidate in recruit['declined']]
    now = (state.year, state.month)
    historical = {candidate for candidate, admission in historical_order(game, state, faction, previous)
                  if admission is not None and now >= admission}
    city = nominee_city(game, state, faction, ident)
    alive = [candidate for candidate, officer in state.officers.items()
             if officer.alive and officer.faction_id == faction]
    if (pending['candidates'] != [ident] or city is None or city.id != recruit['city']
            or len(declined) != len(set(declined)) or not set(declined) <= historical
            or preferred_successor(game, state, faction, previous, alive, excluded=declined) != ident):
        raise ValueError('Invalid succession recruitment candidate')


# Blood ties not represented by a matching row in the loyalty policy.
_ADDITIONAL_FAMILY = (
    ('parent_child', 521, 500), ('parent_child', 500, 503),  # 三国志 卷4・20
    ('parent_child', 521, 509), ('parent_child', 521, 520), ('parent_child', 521, 502),  # 後漢書 卷10下
    ('cousin', 521, 511),  # 三国志 卷9
    ('sibling', 551, 567),  # 三国志 卷51
    ('sibling', 553, 565),  # 三国志 卷32・36
    ('parent_child', 553, 580), ('parent_child', 553, 582),  # 三国志 卷50
    ('parent_child', 553, 573), ('parent_child', 542, 554),  # 三国志 卷48・59
    ('parent_child', 264, 262),  # 三国志 卷8
    ('sibling', 736, 743), ('uncle_nephew', 736, 727), ('grandparent', 736, 741),  # 三国志 卷6
)


_BLOOD_KINDS = {'parent_child', 'sibling', 'uncle_nephew', 'cousin', 'grandparent'}


def _family_rows():
    policy = officer_relations.policy()
    # The dated loyalty exceptions can still document a real blood relationship.
    for group in ('records', 'exceptions'):
        for row in policy[group]:
            if row['kind'] in _BLOOD_KINDS:
                yield row['kind'], row['ruler_id'], row['person_id']
    for kind, first, second in _ADDITIONAL_FAMILY:
        yield kind, _person(first), _person(second)


def parent_child_pairs():
    """Reviewed directed pairs shared with first-appearance placement."""
    return sorted({(parent, child) for kind, parent, child in _family_rows() if kind == 'parent_child'})


def family_priorities(state, previous, alive):
    """Rank verified blood relatives already serving, regardless of the former ruler's loyalty ties."""
    ruler = state.officers.get(previous)
    if ruler is None:
        return {}
    parents, children = defaultdict(set), defaultdict(set)
    ties = {kind: defaultdict(set) for kind in _BLOOD_KINDS - {'parent_child'}}
    for kind, first, second in _family_rows():
        if kind == 'parent_child':
            parents[second].add(first)
            children[first].add(second)
        else:
            ties[kind][first].add(second)
            ties[kind][second].add(first)

    def siblings(person):
        return (ties['sibling'][person] | {child for parent in parents[person]
                                          for child in children[parent]}) - {person}

    person = ruler.person_id
    brothers_and_sisters = siblings(person)
    aunts_and_uncles = {aunt for parent in parents[person] for aunt in siblings(parent)}
    close = parents[person] | children[person] | brothers_and_sisters
    extended = (ties['uncle_nephew'][person] | ties['grandparent'][person] | aunts_and_uncles
                | {child for sibling in brothers_and_sisters for child in children[sibling]}
                | {grandparent for parent in parents[person] for grandparent in parents[parent]}
                | {grandchild for child in children[person] for grandchild in children[child]})
    cousins = ties['cousin'][person] | {child for aunt in aunts_and_uncles for child in children[aunt]}
    rank = dict.fromkeys(cousins, 2) | dict.fromkeys(extended, 1) | dict.fromkeys(close, 0)
    rank.pop(person, None)
    return {ident: rank[pid] for ident in alive
            if (pid := state.officers[ident].person_id) in rank}
