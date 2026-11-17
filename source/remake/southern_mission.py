"""Sun Quan's maritime mission and the optional Luzon building project."""
from math import ceil

from . import city_development, command_books, domestic, grain_units
from .errors import GameError
from .route_hazards import evaluate_leg, route_allowed

COMMAND = 'southern_mission'
DEPARTED = 'historical_wu_southern_mission'
LANDED = 'luzon_landing'
FOUNDED = 'luzon_settlement_completed'
EVENTS = (DEPARTED, LANDED, FOUNDED)
OWNER, RULER, SITE = 'wu', 'san14-candidate-0553', 'luzon'
START, END = (244, 1), (251, 12)
PORTS = {'yizhou': ('yizhou', SITE), 'kuaiji': ('kuaiji', 'yizhou', SITE)}
MIN_TROOPS = 10_000
LIMIT = 100_000_000
TURN_DAYS = 10


def _voyage(game, state, routes, port):
    path = PORTS[port]
    legs = []
    for source, target in zip(path, path[1:]):
        leg = next((row for row in routes if row['mode'] == 'sea'
                    and route_allowed(game.catalog.data, row, source, target)), None)
        if leg is None:
            return None
        legs.append(evaluate_leg(game.catalog.data, leg, source, target, state.month))
    return dict(port=port, path=list(path), wind_days=sum(leg['days'] for leg in legs),
                storm_max=20 if 6 <= state.month <= 10 else 0,
                winds=[leg['hazard']['wind'] if leg['hazard'] else 'calm' for leg in legs])


def _connections(game, state):
    routes = game._known_routes(state)
    voyages = [_voyage(game, state, routes, port) for port in PORTS
               if port in state.cities and state.cities[port].owner == OWNER]
    voyages = sorted((quote for quote in voyages if quote), key=lambda quote: (quote['wind_days'], quote['port']))
    ports = [quote['port'] for quote in voyages]
    # Draw supplies from the embarkation ports and the Wu towns that can send
    # stock to those ports over one open road or inland waterway.
    neighbors = sorted({city for port in ports for row in routes
        if row['mode'] in ('land', 'river') and port in (row['from'], row['to'])
        for city in (row['to'] if row['from'] == port else row['from'],)
        if city in state.cities and city not in ports and state.cities[city].owner == OWNER
        and route_allowed(game.catalog.data, row, city, port)})
    return voyages, [state.cities[key] for key in ports + neighbors]


def _embark(state, quote):
    storm = 0
    if quote['storm_max'] and state.rng.next() % 3 == 0:
        storm = 10 * (1 + state.rng.next() % 2)
    days = quote['wind_days'] + storm
    return dict(port=quote['port'], turn=state.turn, wind_days=quote['wind_days'],
                storm_days=storm, arrival=state.turn + ceil(days / TURN_DAYS))


def _garrisons(game, state, sources):
    absent = game._march_ids(state)
    used = state.extension['officer_actions']
    return [state.officers[ident] for city in sources for ident in city.roster.officer_ids
            if ident not in absent and used.get(str(ident)) != state.turn
            and state.officers[ident].alive]


def _stocks(sources):
    return {field: sum(getattr(city, field) for city in sources) for field in ('gold', 'grain', 'reserves')}


def _withdraw(sources, field, amount):
    for city in sources:
        taken = min(amount, getattr(city, field))
        setattr(city, field, getattr(city, field) - taken)
        amount -= taken
        if not amount:
            break
    if amount:
        raise ValueError('Incomplete maritime stock transfer')


def _pay(sources, gold, grain):
    stocks = _stocks(sources)
    if stocks['gold'] < gold or stocks['grain'] < grain:
        return False
    _withdraw(sources, 'gold', gold)
    _withdraw(sources, 'grain', grain)
    return True


def _cost(troops, days):
    denominator = grain_units.denominator()
    return ceil(troops / 1_000) * days, ((2 * troops + denominator - 1) // denominator) * days


def work_days(troops):
    return ceil(360 * MIN_TROOPS / troops)


def _available(game, state, voyages, sources):
    active = sum(officer.troops for officer in _garrisons(game, state, sources))
    maximum = min(LIMIT - state.cities[SITE].reserves, active + sum(city.reserves for city in sources))
    return dict(available_troops=maximum, active_troops=active, stocks=_stocks(sources),
                sources=[city.id for city in sources], routes=voyages,
                can_order=(state.phase == 'city' and OWNER not in state.extension['pending_succession']
                           and command_books.can_spend(state, OWNER, 'depart')))


def view(game, state):
    record = state.extension.get(COMMAND) if state and state.player == OWNER else None
    if record is None:
        return None
    result = dict(record, site=SITE, minimum=MIN_TROOPS)
    if record['stage'] in ('offer', 'sailing', 'building'):
        voyages, sources = _connections(game, state)
        result.update(_available(game, state, voyages, sources))
        result['can_order'] &= state.cities[SITE].owner == 'neutral'
    return result


def _take_troops(game, state, sources, troops):
    # Mobilize reserves first. Any remaining men come from idle garrisons.
    from_reserves = min(troops, sum(city.reserves for city in sources))
    _withdraw(sources, 'reserves', from_reserves)
    remaining = troops - from_reserves
    for officer in _garrisons(game, state, sources):
        taken = min(remaining, officer.troops)
        officer.troops -= taken
        remaining -= taken
        if not remaining:
            break
    if remaining:
        raise ValueError('Incomplete maritime mobilization')


def execute(game, state, payload):
    record = state.extension.get(COMMAND)
    if state.player != OWNER or state.phase != 'city' or not record or record['stage'] != 'offer':
        raise GameError('現在無法決定呂宋築城。')
    if state.cities[SITE].owner != 'neutral':
        raise GameError('呂宋已經設城。')
    if payload == {'action': 'decline'}:
        record['stage'] = 'declined'
        game._note(state, '呂宋暫不築城，朱應與康泰繼續南行。')
        return
    if set(payload) != {'action', 'port', 'troops'} or payload['action'] != 'build':
        raise GameError('築城指令參數無效。')
    troops = payload['troops']
    voyages, sources = _connections(game, state)
    available = _available(game, state, voyages, sources)
    maximum = available['available_troops']
    if type(troops) is not int or not MIN_TROOPS <= troops <= maximum:
        raise GameError('築城須出動至少10,000名士兵，且不可超過附近城市可動員的人數。')
    quote = next((row for row in voyages if row['port'] == payload['port']), None)
    if quote is None:
        raise GameError('所選港口無法出航。')
    if not available['can_order']:
        raise GameError('目前無法下達出航命令，請確認命令書與繼承狀態。')
    fleet = _embark(state, quote)
    gold, grain = _cost(troops, fleet['wind_days'] + fleet['storm_days'])
    if not _pay(sources, gold, grain):
        raise GameError('附近城池的金或兵糧不足，無法備妥航程物資。')
    _take_troops(game, state, sources, troops)
    command_books.spend(state, state.cities[quote['port']], 'depart')
    record.update(stage='sailing', fleet=fleet, troops=troops, worked=0, last_turn=None, paused=False)
    game._note(state, f'呂宋築城船隊啟航，載兵{troops}人。航海遇風延誤{fleet["storm_days"]}日，船隊兵力全數保留。')


def blocks_settlement(state, owner, target):
    return (owner == state.player == OWNER and target == SITE and state.cities[SITE].owner == 'neutral'
            and state.extension.get(COMMAND, {}).get('stage') in ('survey', 'offer', 'sailing', 'building'))


def in_transit_troops(state):
    record = state.extension.get(COMMAND, {})
    return record['troops'] if record.get('stage') in ('sailing', 'building') else 0


def _emit(game, state, kind, port, details):
    game._emit_event(state, kind, city_ids=[port, SITE], factions=[OWNER], details=details)


def _return_troops(game, state, record, sources):
    remaining = record['troops']
    known = {city.id for city in sources}
    destinations = sources + [city for city in state.cities.values() if city.owner == OWNER and city.id not in known]
    for city in destinations:
        before = remaining
        remaining = max(0, remaining - (LIMIT - city.reserves))
        domestic.add_reserves(game, state, city, before - remaining)
        if not remaining:
            break
    # A conquered expedition has no friendly city to receive any remaining men.
    state.soldiers['lost'] += remaining
    record.update(stage='closed', paused=False)
    game._note(state, f'呂宋已被佔領，築城中止，{record["troops"] - remaining}人轉回本方預備兵。')


def process(game, state):
    if state.player != OWNER or state.phase != 'city' or SITE not in state.cities:
        return
    island = state.cities[SITE]
    record = state.extension.get(COMMAND)
    if record is None:
        leader = state.officers.get(state.extension['leaders'].get(OWNER))
        if (not START <= (state.year, state.month) <= END or not leader or not leader.alive
                or leader.person_id != RULER
                or (game.catalog.data.get('main_scenario') or {}).get('group') == 'if'):
            return
        voyages, _ = _connections(game, state)
        if voyages:
            survey = _embark(state, voyages[0])
            state.extension[COMMAND] = dict(stage='survey', survey=survey)
            _emit(game, state, DEPARTED, survey['port'],
                  dict(days=survey['wind_days'] + survey['storm_days'], storm_days=survey['storm_days']))
        return
    stage = record['stage']
    survey = record['survey']
    if stage == 'survey' and state.turn >= survey['arrival']:
        offered = island.owner == 'neutral'
        record.update(landed=state.turn, offered=offered, stage='offer' if offered else 'closed')
        _emit(game, state, LANDED, survey['port'], dict(can_build=offered))
        return
    if stage == 'offer' and island.owner != 'neutral':
        record['stage'] = 'closed'
        return
    if stage not in ('sailing', 'building'):
        return
    fleet = record['fleet']
    if island.owner != 'neutral':
        _, sources = _connections(game, state)
        _return_troops(game, state, record, sources)
        return
    if stage == 'sailing':
        if state.turn >= fleet['arrival']:
            record.update(stage='building', last_turn=state.turn)
        return
    if state.turn <= record['last_turn']:
        return
    troops = record['troops']
    required = work_days(troops)
    step = min(TURN_DAYS, required - record['worked'])
    _, sources = _connections(game, state)
    paid = _pay(sources, *_cost(troops, step))
    record.update(last_turn=state.turn, paused=not paid)
    if not paid:
        return
    record['worked'] += step
    if record['worked'] == required:
        island.owner = OWNER
        domestic.add_reserves(game, state, island, troops)
        city_development.synchronize(game, state)
        record['stage'] = 'built'
        _emit(game, state, FOUNDED, fleet['port'], dict(troops=troops, work_days=required))
        game._note(state, f'呂宋築城完成，{troops}人轉入新城預備兵。')


def _valid_voyage(voyage, turn):
    return (isinstance(voyage, dict)
            and set(voyage) == {'port', 'turn', 'wind_days', 'storm_days', 'arrival'}
            and isinstance(voyage['port'], str) and voyage['port'] in PORTS
            and all(type(voyage[key]) is int for key in ('turn', 'wind_days', 'storm_days', 'arrival'))
            and 1 <= voyage['turn'] <= turn and 1 <= voyage['wind_days'] <= 10_000
            and voyage['storm_days'] in (0, 10, 20)
            and voyage['arrival'] == voyage['turn'] + ceil((voyage['wind_days'] + voyage['storm_days']) / TURN_DAYS))


def validate_state(catalog, state):
    if COMMAND not in state.extension:
        return
    from .historical_campaigns import _turn_date

    record = state.extension[COMMAND]
    if (state.player != OWNER or SITE not in state.cities or not isinstance(record, dict)
            or record.get('stage') not in ('survey', 'offer', 'declined', 'closed', 'sailing', 'building', 'built')
            or not _valid_voyage(record.get('survey'), state.turn)
            or not START <= _turn_date(catalog, record['survey']['turn']) <= END):
        raise ValueError('Southern mission receipt')
    stage = record['stage']
    fields = {'stage', 'survey'}
    if stage != 'survey':
        fields.update(('landed', 'offered'))
        if (type(record.get('landed')) is not int or not record['survey']['arrival'] <= record['landed'] <= state.turn
                or type(record.get('offered')) is not bool or (stage != 'closed' and not record['offered'])):
            raise ValueError('Luzon survey arrival')
    if stage in ('sailing', 'building', 'built') or 'fleet' in record:
        fields.update(('fleet', 'troops', 'worked', 'last_turn', 'paused'))
        troops, worked, last = (record.get(key) for key in ('troops', 'worked', 'last_turn'))
        if (stage not in ('sailing', 'building', 'built', 'closed') or not record['offered']
                or not _valid_voyage(record.get('fleet'), state.turn)
                or record['fleet']['turn'] < record['landed']
                or type(troops) is not int or not MIN_TROOPS <= troops <= LIMIT
                or type(worked) is not int or not 0 <= worked <= work_days(troops)
                or type(record.get('paused')) is not bool):
            raise ValueError('Luzon project manifest')
        if (last is None and (worked or record['paused'] or stage in ('building', 'built'))
                or last is not None and (type(last) is not int or stage == 'sailing'
                                         or not record['fleet']['arrival'] <= last <= state.turn
                                         or worked > (last - record['fleet']['arrival']) * TURN_DAYS)
                or (stage == 'built') != (worked == work_days(troops))):
            raise ValueError('Luzon project progress')
    if set(record) != fields:
        raise ValueError('Southern mission fields')
    events = state.extension['events']
    kinds = [row['kind'] for row in events['items'] + events.get('milestones', []) if row['kind'] in EVENTS]
    expected = [DEPARTED] + ([LANDED] if stage != 'survey' else []) + ([FOUNDED] if stage == 'built' else [])
    if sorted(kinds) != sorted(expected):
        raise ValueError('Southern mission event history')


def validate_event(state, row):
    record = state.extension.get(COMMAND)
    if not isinstance(record, dict):
        raise ValueError('Southern mission event without receipt')
    kind = row['kind']
    voyage = record.get('fleet' if kind == FOUNDED else 'survey')
    if not _valid_voyage(voyage, state.turn):
        raise ValueError('Southern mission event voyage')
    if kind == FOUNDED:
        troops = record.get('troops')
        if type(troops) is not int or troops < MIN_TROOPS:
            raise ValueError('Luzon founding event troops')
        turn, details = record.get('last_turn'), dict(troops=troops, work_days=work_days(troops))
    elif kind == LANDED:
        turn, details = record.get('landed'), dict(can_build=record.get('offered'))
    else:
        turn = voyage['turn']
        details = dict(days=voyage['wind_days'] + voyage['storm_days'], storm_days=voyage['storm_days'])
    if (row['turn'] != turn or row['audience'] != 'player' or row['person_ids']
            or row['city_ids'] != [voyage['port'], SITE] or row['factions'] != [OWNER]
            or row['details'] != details):
        raise ValueError('Southern mission event receipt')
