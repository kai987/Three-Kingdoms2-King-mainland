"""Faction diplomacy, captives and treaties in the ten-day campaign."""
from . import command_books, logistics, officer_relations, treasures
from .errors import GameError
from .officers import deserialize_officer_ref, parse_officer_ref, ref_sort_key, recruitment_loyalty

KEY = 'diplomacy'
MAX_TURNS = 72
REQUEST_TURNS = 6
NORMAL = 50
FRIENDLY = 65
STAGES = ((85, 'intimate'), (FRIENDLY, 'friendly'), (NORMAL, 'normal'),
          (35, 'discord'), (20, 'hostile'), (0, 'hateful'))
LIMITS = {'gold': (5000, 100), 'grain': (20000, 400), 'treasure': (9, 1)}
PARAMETERS = {
    'goodwill': {'resource', 'amount'},
    'alliance': {'duration'},
    'return_captives': {'prisoner'},
    'request_attack': {'attack_city'},
    'surrender': set(),
}


def _pool(state):
    return state.extension.setdefault(KEY, dict(relations={}, treaties={}, prisoners={}, requests={}))


def _section(state, name):
    return state.extension.get(KEY, {}).get(name, {})


def _pair(first, second):
    return '|'.join(sorted((first, second)))


def relation(state, first, second):
    return _section(state, 'relations').get(_pair(first, second), NORMAL)


def stage(score):
    return next(name for lower, name in STAGES if score >= lower)


def expiry(state, first, second):
    treaties = _section(state, 'treaties')
    if not treaties or not isinstance(first, str) or not isinstance(second, str):
        return None
    end = treaties.get(_pair(first, second), 0)
    if end and end > state.turn and not any(f in state.extension['ended_factions'] for f in (first, second)):
        return end
    return None


def allied(state, first, second):
    return expiry(state, first, second) is not None


def alliances(state):
    return [key.split('|') for key in sorted(_section(state, 'treaties'))
            if allied(state, *key.split('|'))]


def _change_relation(state, first, second, delta):
    key = _pair(first, second)
    score = max(0, min(100, relation(state, first, second) + delta))
    _pool(state)['relations'][key] = score
    return score


def _rupture_now(state, pair):
    from . import historical_campaigns
    return (pair == _pair(*historical_campaigns.SUN_LIU)
            and state.extension.get(historical_campaigns.RECEIPTS, {}).get(historical_campaigns.ALLIANCE_ENDED) == state.turn)


def battle_relations(game, state, battle):
    first, second = battle['attacker'], battle['defender']
    if first in game.catalog.factions and second in game.catalog.factions and first != second:
        _change_relation(state, first, second, -12)


def capture(state, officer, *, city, captor, origin):
    if origin == 'neutral' or captor == 'neutral' or captor == origin:
        return False
    _pool(state)['prisoners'][str(officer.runtime_id)] = dict(
        city=city, captor=captor, origin=origin, loyalty=officer.loyalty)
    return True


def synchronize(game, state):
    data = state.extension.get(KEY)
    if data is None:
        return
    ended = state.extension['ended_factions']
    for key in list(data['treaties']):
        pair = key.split('|')
        if not expiry(state, *pair) or _rupture_now(state, key):
            del data['treaties'][key]
    for key, row in list(data['prisoners'].items()):
        ident = deserialize_officer_ref(key, game.catalog.rules)
        officer = state.officers[ident]
        if not officer.alive or row['origin'] in ended or row['captor'] in ended or state.cities[row['city']].owner != row['captor']:
            if officer.alive:
                state.extension['free_locations'][key] = row['city']
            del data['prisoners'][key]
    for ally, row in list(data['requests'].items()):
        if not requested_target(state, ally):
            del data['requests'][ally]


def requested_target(state, ally):
    from .historical_campaigns import allied as has_alliance
    row = _section(state, 'requests').get(ally)
    if row is None or row['until'] <= state.turn or not has_alliance(state, row['requester'], ally):
        return None
    city = state.cities[row['city']]
    if (city.owner != row['enemy'] or has_alliance(state, ally, city.owner)
            or has_alliance(state, row['requester'], city.owner)):
        return None
    if any(march['id'] > row['after_march'] and march['owner'] == ally
           and march['kind'] == 'attack' and march['target'] == city.id
           for march in state.extension['travel']['marches']):
        return None
    return city.id


def _holdings(state, owner):
    return sorted((city for city in state.cities.values() if city.owner == owner), key=lambda city: city.id)


def _envoys(state, city, travelling):
    return [state.officers[i] for i in sorted(city.roster.officer_ids, key=ref_sort_key)
            if i not in travelling and state.officers[i].alive and state.officers[i].health > 0
            and state.extension['officer_actions'].get(str(i)) != state.turn]


def _prisoners(game, state, owner, target):
    return [(deserialize_officer_ref(key, game.catalog.rules), row)
            for key, row in _section(state, 'prisoners').items()
            if row['origin'] == owner and row['captor'] == target]


def _return_city(game, state, cities):
    return next((city for city in cities if game._city_occupancy(state, city) < game.catalog.rules.city_officer_capacity), None)


def _can_surrender(state, score, cities, enemy):
    if score < 20:
        return False
    def power(holdings):
        return sum(1000 + city.reserves + sum(state.officers[i].troops for i in city.roster.officer_ids)
                   for city in holdings)
    ratio = 2 if score >= FRIENDLY else 3
    return len(cities) >= ratio * len(enemy) and power(cities) >= ratio * power(enemy)


def _options(game, state, owner, target, own, other):
    from . import historical_campaigns
    historical = historical_campaigns.historical_allied(state, owner, target)
    end = expiry(state, owner, target)
    pact = dict(historical=historical, turns=end-state.turn if end else None) if historical or end else None
    score = relation(state, owner, target)
    if historical:
        score = max(FRIENDLY, score)
    prisoners = _prisoners(game, state, owner, target)
    attacks = set()
    if pact and score >= FRIENDLY:
        for city in other:
            for key in game._neighbors(city.id, state):
                enemy = state.cities.get(key)
                if (enemy and enemy.owner not in {owner, target, 'neutral'}
                        and not historical_campaigns.allied(state, target, enemy.owner)
                        and not historical_campaigns.allied(state, owner, enemy.owner)):
                    attacks.add(key)
    return dict(id=target, stage=stage(score), score=score, alliance=pact, attack_cities=sorted(attacks),
                captives=[dict(id=i, name=game.person_name(state, i)) for i, _ in prisoners],
                actions=dict(goodwill=score<100, alliance=pact is None and score>=NORMAL
                             and not _rupture_now(state, _pair(owner, target)),
                             return_captives=bool(prisoners and _return_city(game, state, own)),
                             request_attack=bool(attacks and not requested_target(state, target)),
                             surrender=pact is None and _can_surrender(state, score, own, other)))


def view(game, state):
    result = dict(max_turns=MAX_TURNS, can_command=False, cities=[], targets=[])
    if state is None or state.player not in game.catalog.factions or state.phase != 'city':
        return result
    owner = state.player
    own = _holdings(state, owner)
    if not own:
        return result
    travelling = game._march_ids(state)
    for city in own:
        envoys = [dict(id=o.runtime_id, name=game.person_name(state, o.runtime_id),
                       intellect=o.profile.intellect, virtue=o.profile.virtue)
                  for o in _envoys(state, city, travelling)]
        if envoys:
            limits = {key: min(limit, treasures.count(state, city.id) if key=='treasure' else getattr(city, key))
                      for key, (limit, _) in LIMITS.items()}
            result['cities'].append(dict(id=city.id, envoys=envoys, limits=limits))
    by_owner = {}
    for city in state.cities.values():
        if city.owner not in {owner, 'neutral'}:
            by_owner.setdefault(city.owner, []).append(city)
    result['targets'] = [_options(game, state, owner, target, own, sorted(cities, key=lambda c: c.id))
                         for target, cities in sorted(by_owner.items())]
    result['can_command'] = bool(result['cities'] and result['targets'] and command_books.can_spend(state, owner, 'diplomacy')
                                 and owner not in state.extension['pending_succession'])
    return result


def _goodwill(state, city, envoy, target, other, score, payload):
    kind, amount = payload['resource'], payload['amount']
    if type(kind) is not str or kind not in LIMITS or type(amount) is not int or not 1 <= amount <= LIMITS[kind][0]:
        raise GameError('請選擇有效的禮品數量。')
    leader = state.extension['leaders'][target]
    destinations = sorted(other, key=lambda c: (leader not in c.roster.officer_ids, c.id))
    if kind == 'treasure':
        dest = next((c for c in destinations if treasures.count(state, c.id) + amount <= 99), None)
        if dest is None or treasures.count(state, city.id) < amount:
            raise GameError('寶物不足，或對方沒有足夠的庫存空間。')
        treasures.debit(state, city.id, amount)
        treasures.credit(state, dest.id, amount)
    else:
        dest = next((c for c in destinations if getattr(c, kind)+amount <= 100000000), None)
        if dest is None or getattr(city, kind) < amount:
            raise GameError('資源不足，或對方沒有足夠的庫存空間。')
        setattr(city, kind, getattr(city, kind)-amount)
        setattr(dest, kind, getattr(dest, kind)+amount)
    gift_weight = amount // LIMITS[kind][1] if kind != 'treasure' else 3*amount
    gain = min(25, max(1, gift_weight) + (envoy.profile.intellect+envoy.profile.virtue)//60)
    return _change_relation(state, city.owner, target, gain + score - relation(state, city.owner, target))


def _return_prisoner(game, state, owner, target, envoy, own, score, payload):
    try:
        ident = parse_officer_ref(payload['prisoner'], game.catalog.rules)
    except (TypeError, ValueError):
        raise GameError('請選擇對方扣留的本方武將。') from None
    row = dict(_prisoners(game, state, owner, target)).get(ident)
    home = _return_city(game, state, own)
    if row is None or home is None:
        raise GameError('請選擇對方扣留的本方武將並保留接收空位。')
    officer = state.officers[ident]
    if score + (envoy.profile.intellect+envoy.profile.virtue)//5 < 65:
        return False, officer.person_id
    home.roster.officer_ids.append(ident)
    officer.faction_id = owner
    officer.loyalty = min(99, row['loyalty'])
    officer_relations.apply(game, state, ident)
    state.extension['officer_actions'][str(ident)] = state.turn
    del _pool(state)['prisoners'][str(ident)]
    return True, officer.person_id


def _accept_surrender(game, state, owner, target, other):
    leader = state.officers[state.extension['leaders'][owner]]
    marches = state.extension['travel']['marches']
    for march in list(marches):
        if march['owner'] != target:
            continue
        grain = march['supply']['remaining']
        candidates = sorted(other, key=lambda city: (city.id != march['source'], city.id))
        dest = next((city for city in candidates if city.grain+grain <= 100000000), None)
        if dest is None:
            raise GameError('對方城池沒有空間收回隨軍糧，無法完成受降。')
        dest.grain += grain
        marches.remove(march)
    logistics.settle_surrender(game, state, target, other)
    for city in other:
        city.owner = owner
        for ident in city.roster.officer_ids:
            officer = state.officers[ident]
            officer.faction_id = owner
            officer.loyalty = recruitment_loyalty(leader.profile.virtue, officer.loyalty)
            officer_relations.apply(game, state, ident)
            state.extension['officer_actions'][str(ident)] = state.turn
    game._prune_marches(state)
    game._reconcile_factions(state)


def execute(game, state, payload, owner):
    action = payload.get('action')
    if type(action) is not str or action not in PARAMETERS or set(payload) != {'action','city','envoy','target'} | PARAMETERS[action]:
        raise GameError('外交指令參數無效。')
    city_id, target = payload['city'], payload['target']
    if (state.phase != 'city' or type(city_id) is not str or city_id not in state.cities
            or state.cities[city_id].owner != owner or owner not in game.catalog.factions
            or owner in state.extension['pending_succession']
            or type(target) is not str or target == owner or target not in game.catalog.factions):
        raise GameError('目前無法派遣外交使者。')
    city = state.cities[city_id]
    try:
        ident = parse_officer_ref(payload['envoy'], game.catalog.rules)
    except (TypeError, ValueError):
        raise GameError('請選擇可行動的本城使者。') from None
    own, other = _holdings(state, owner), _holdings(state, target)
    available = {o.runtime_id:o for o in _envoys(state, city, game._march_ids(state))}
    if ident not in available or not other:
        raise GameError('請選擇可行動的本城使者及仍有城池的勢力。')
    envoy = available[ident]
    option = _options(game, state, owner, target, own, other)
    if not option['actions'][action]:
        raise GameError('目前外交感情或戰局條件不符合。')
    command_books.spend(state, city, 'diplomacy')
    state.extension['officer_actions'][str(ident)] = state.turn
    score, success, duration, person, attack_city = option['score'], True, 0, None, None
    if action == 'goodwill':
        score = _goodwill(state, city, envoy, target, other, score, payload)
    elif action == 'alliance':
        duration = payload['duration']
        if type(duration) is not int or not 1 <= duration <= MAX_TURNS:
            raise GameError('同盟期限須介於1與72旬之間。')
        _pool(state)['treaties'][_pair(owner, target)] = state.turn + duration
    elif action == 'return_captives':
        success, person = _return_prisoner(game, state, owner, target, envoy, own, score, payload)
    elif action == 'request_attack':
        attack_city = payload['attack_city']
        if attack_city not in option['attack_cities']:
            raise GameError('請選擇盟軍可出征的第三方城池。')
        _pool(state)['requests'][target] = dict(requester=owner, city=attack_city,
            enemy=state.cities[attack_city].owner, until=state.turn+REQUEST_TURNS,
            after_march=state.extension['travel']['counter'])
        state.extension['ai_strategy'].pop(target, None)
    else:
        _accept_surrender(game, state, owner, target, other)
    result = '達成' if success else '遭拒'
    names = {'goodwill':'親善','alliance':'同盟','return_captives':'歸還俘虜',
             'request_attack':'請求攻擊','surrender':'勸告投降'}
    game._note(state, f'{game.person_name(state, ident)}向{game.faction_name(state, target)}提出{names[action]}，結果：{result}。')
    game._emit_event(state, 'diplomacy_result', person_ids=list(dict.fromkeys([envoy.person_id]+([person] if person else []))),
        city_ids=[city_id]+([attack_city] if attack_city else []), factions=[owner,target],
        details=dict(action=action, success=success, score=score, duration=duration), audience='player')


def validate(game, state):
    if KEY not in state.extension:
        return
    data = state.extension[KEY]
    factions = set(game.catalog.factions) - {'neutral'}
    if (not isinstance(data, dict) or set(data) != {'relations','treaties','prisoners','requests'}
            or any(not isinstance(section, dict) for section in data.values())):
        raise ValueError('Invalid diplomacy records')
    for name, cap in (('relations',100), ('treaties',state.turn+MAX_TURNS)):
        for key, value in data[name].items():
            pair = key.split('|')
            if (len(pair)!=2 or pair[0]>=pair[1] or not set(pair)<=factions or type(value) is not int
                    or not (state.turn+1 if name=='treaties' else 0)<=value<=cap):
                raise ValueError('Invalid diplomatic relation or treaty')
    for key, row in data['prisoners'].items():
        ident = deserialize_officer_ref(key, game.catalog.rules)
        officer = state.officers.get(ident)
        if (not isinstance(row, dict) or set(row) != {'city','captor','origin','loyalty'}
                or row['city'] not in state.cities or state.cities[row['city']].owner != row['captor']
                or row['captor']==row['origin'] or not {row['captor'],row['origin']}<=factions
                or any(f in state.extension['ended_factions'] for f in (row['captor'],row['origin']))
                or not officer or not officer.alive or officer.faction_id is not None or officer.troops != 0
                or key in state.extension['free_locations']
                or type(row['loyalty']) is not int or not 0<=row['loyalty']<=100):
            raise ValueError('Invalid diplomatic prisoner')
    for key, row in data['requests'].items():
        if (not isinstance(row, dict) or set(row) != {'requester','city','enemy','until','after_march'}
                or row['city'] not in state.cities or len({key,row['requester'],row['enemy']})!=3
                or not {key,row['requester'],row['enemy']}<=factions
                or type(row['until']) is not int or not state.turn<row['until']<=state.turn+REQUEST_TURNS
                or type(row['after_march']) is not int or not 0<=row['after_march']<=state.extension['travel']['counter']
                or requested_target(state,key)!=row['city']):
            raise ValueError('Invalid allied attack request')
