"""Deterministic opening garrisons, separate from officer membership and dates.

Only people who already occur in ``initial_officers`` are placed.  A source
city is evidence about a game's opening posting, not a claim that the posting
is independently attested history.  Missing cities use the authored frontier
rule; they are never invented source postings or a change of allegiance.
"""
from collections import Counter, defaultdict
from copy import deepcopy


# These are board conversions, matching the source-city vocabulary used by the
# existing offline era builders.  County seats absent from the board remain
# explicit proxies and do not qualify as exact source-city postings.
SOURCE_CITY_ALIASES = dict(zip(
    '上庸 下邳 交趾 北平 北海 南海 南皮 吳 壽春 天水 安定 宛 小沛 平原 廣陵 廬江 建安 建寧 建業 成都 新野 晉陽 會稽 柴桑 桂陽 梓潼 武威 武陵 永安 汝南 江夏 江州 江陵 洛陽 漢中 濮陽 薊 襄平 襄陽 許昌 鄴 長安 長沙 陳留 雲南 零陵'.split(),
    'xincheng xiapi jiaozhi yuyang beihai nanhai bohai wujun jiujiang tianshui anding nanyang qiao pingyuan donghai lujiang kuaiji jianning danyang shujun nanyang taiyuan kuaiji yuzhang guiyang zitong wuwei wuling badong runan jiangxia bajun nanjun henan hanzhong dongjun yan liaodong xiangyang yingchuan wei jingzhao changsha chenliu yunnan lingling'.split()))
SOURCE_CITY_ALIASES.update(dict(zip(
    '吴 寿春 广陵 庐江 建宁 建业 晋阳 会稽 桂阳 洛阳 汉中 濮阳 蓟 襄阳 许昌 邺 长安 长沙 陈留 云南 零陵'.split(),
    'wujun jiujiang donghai lujiang jianning danyang taiyuan kuaiji guiyang henan hanzhong dongjun yan xiangyang yingchuan wei jingzhao changsha chenliu yunnan lingling'.split())))
PROXY_SOURCE_CITIES = frozenset(('小沛', '廣陵', '广陵', '建安', '新野', '北平', '柴桑'))


def apply_postings(data, *, capacity=None, source_aliases=None, proxy_names=None):
    """Place an existing opening roster and return its auditable decisions.

    The caller must finish territorial/faction edits first.  Each person's
    existing city owner fixes their faction; a contradictory ``era_assignment``
    is an error.  Rulers stay in their faction seat and the already reviewed
    227 Qian Zhao appointment is retained.  Exact matching source cities are
    filled next.  Remaining officers go to the least populated friendly city
    bordering another nonneutral faction, over every currently active link.
    If there is no enemy frontier, or it is full, owned interior cities provide
    a capacity-safe fallback.  Neutrals do not create an enemy frontier.

    Planning and validation precede mutation, so an impossible allocation leaves
    the input untouched.  Ordering depends on stable person and city IDs only.
    Free/future/dead people, identities, profiles, armies and affiliations are
    not created or changed.  ``capacity`` defaults to the catalog's own rule.
    """
    capacity = data.get('rules', {}).get('city_officer_capacity', 30) if capacity is None else capacity
    if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
        raise ValueError('City officer capacity must be a positive integer')
    cities = {row['id']: row for row in data['cities']}
    active = set(data.get('active_cities', cities))
    owners = data['initial_owners']
    factions = {row['id']: row for row in data['factions']}
    assignments = data.get('era_assignments', {})
    rows = data['initial_officers']
    identities = [row['person_id'] for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate opening officer identity')
    free = {row['person_id'] for row in data.get('initial_free_officers', [])}
    if free.intersection(identities):
        raise ValueError('An officer cannot be both serving and free')
    if not active.issubset(cities):
        raise ValueError('Unknown active city')

    aliases = dict(SOURCE_CITY_ALIASES)
    aliases.update({row['name']: key for key, row in cities.items()})
    if source_aliases is not None:
        aliases.update(source_aliases)
    proxies = PROXY_SOURCE_CITIES if proxy_names is None else frozenset(proxy_names)
    members = defaultdict(list)
    side_by_person = {}
    for row in rows:
        pid = row['person_id']
        if row['city'] not in active:
            raise ValueError('Opening officer occupies an inactive city: ' + pid)
        side = owners.get(row['city'])
        if side not in factions or side == 'neutral':
            raise ValueError('Opening officer has no enabled faction: ' + pid)
        declared = assignments.get(pid, {}).get('faction')
        if declared is not None and declared != side:
            raise ValueError('Officer affiliation contradicts opening city owner: ' + pid)
        side_by_person[pid] = side
        members[side].append(row)

    frontier = defaultdict(set)
    for edge in data.get('links', []):
        a, b = edge
        if a not in active or b not in active:
            continue
        oa, ob = owners.get(a), owners.get(b)
        if oa in factions and ob in factions and oa != ob and 'neutral' not in (oa, ob):
            frontier[oa].add(a)
            frontier[ob].add(b)

    counts = Counter()
    planned = {}
    records = {}
    modes = Counter()
    source_counts = Counter()
    owned_by_side = {}

    def place(row, city, basis, **extra):
        if counts[city] >= capacity:
            raise ValueError('Pinned/source city exceeds capacity: ' + city)
        pid = row['person_id']
        planned[pid] = city
        counts[city] += 1
        modes[basis] += 1
        record = dict(person_id=pid, faction=side_by_person[pid], origin=row['city'],
                      city=city, basis=basis, source_city=assignments.get(pid, {}).get('source_city'))
        record.update(extra)
        records[pid] = record

    # Rulers and the explicitly attested appointment cannot be displaced by
    # source-priority or frontier balancing.
    for side in sorted(members):
        owned = sorted(key for key in active if owners.get(key) == side)
        owned_by_side[side] = owned
        if len(members[side]) > len(owned) * capacity:
            raise ValueError('Not enough owned roster seats for faction: ' + side)
        seat = factions[side]['city']
        if seat not in owned:
            raise ValueError('Faction ruler seat is not owned: ' + side)
        for row in sorted(members[side], key=lambda row: row['person_id']):
            if row.get('ruler'):
                place(row, seat, 'retained_faction_ruler_seat')
        for row in sorted(members[side], key=lambda row: row['person_id']):
            pid = row['person_id']
            posting = assignments.get(pid, {}).get('posting_reference') or {}
            if pid not in planned and posting.get('basis') == 'attested_yanmen_post_227':
                city = posting['city']
                if city in owned:
                    place(row, city, 'attested_yanmen_post_227', prior_posting=deepcopy(posting))
            primary = assignments.get(pid, {}).get('historical_posting_reference') or {}
            if pid not in planned and primary.get('basis') == 'primary_referenced_career_posting':
                city = primary.get('city')
                if city in owned and counts[city] < capacity:
                    place(row, city, 'primary_referenced_career_posting', prior_posting=deepcopy(primary))

    pending = defaultdict(list)
    for side in sorted(members):
        for row in sorted(members[side], key=lambda row: row['person_id']):
            pid = row['person_id']
            if pid in planned:
                continue
            assignment = assignments.get(pid, {})
            source = assignment.get('source_city')
            city = source if source in cities else aliases.get(source)
            if not source:
                reason = 'missing_source_city'
            elif city is None:
                reason = 'unmapped_source_city'
            elif source in proxies:
                reason = 'source_board_proxy_not_exact_city'
            elif city not in active:
                reason = 'source_city_inactive'
            elif owners.get(city) != side:
                reason = 'source_city_not_owned_by_faction'
            elif counts[city] >= capacity:
                reason = 'source_city_full'
            else:
                reason = 'matched_source_city'
            source_counts[reason] += 1
            if reason == 'matched_source_city':
                basis = ('reviewed_SAN14_source_city_to_board' if assignment.get('source_city_reference')
                         else 'source_snapshot_city_to_board')
                place(row, city, basis, source_disposition=reason,
                      source_reference=deepcopy(assignment.get('source_city_reference')))
            else:
                pending[side].append((row, reason, city))

    for side in sorted(pending):
        border = sorted(frontier[side])
        owned = owned_by_side[side]
        for row, reason, source_target in pending[side]:
            options = [key for key in border if counts[key] < capacity]
            if options:
                basis = 'authored_enemy_frontier_balanced'
            else:
                options = [key for key in owned if counts[key] < capacity]
                basis = ('authored_frontier_full_owned_capacity_fallback' if border
                         else 'authored_no_enemy_frontier_owned_balance')
            if not options:
                raise ValueError('No remaining owned roster capacity for faction: ' + side)
            city = min(options, key=lambda key: (counts[key], key))
            place(row, city, basis, source_disposition=reason, source_board_city=source_target)

    # All validation succeeded.  Preserve row order and every nonlocation field.
    locations = data.setdefault('appearance_locations', {})
    for row in rows:
        pid = row['person_id']
        row['city'] = planned[pid]
        locations[pid] = planned[pid]
        if pid in assignments:
            assignment = assignments[pid]
            assignment.update(city=planned[pid], placement_basis=records[pid]['basis'],
                              posting_reference=deepcopy(records[pid]))
    if 'coverage' in data:
        data['coverage']['planned_max_city_roster'] = max(counts.values(), default=0)
    audit = dict(schema='opening-garrison-postings-v1', capacity=capacity,
                 source_policy='source_city_same_faction_before_authored_frontier_balance',
                 frontier_policy='active_route_adjacent_other_enabled_nonneutral_faction',
                 modes=dict(sorted(modes.items())), source_counts=dict(sorted(source_counts.items())),
                 postings=[records[pid] for pid in sorted(records)],
                 factions={side: dict(officers=len(members[side]), frontier_cities=sorted(frontier[side]),
                                     city_rosters={key: counts[key] for key in owned_by_side[side]})
                           for side in sorted(members)})
    return audit
