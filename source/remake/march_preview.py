"""Explain a selected city pair with the campaign's current route rules."""
from functools import lru_cache
import json
from pathlib import Path

from . import historical_campaigns, winter_travel, winter_weather
from .route_hazards import _python_route_allowed as route_allowed
from .route_network import available


@lru_cache(maxsize=1)
def _route_geometry():
    path = Path(__file__).resolve().parents[2] / 'game/config/route-geometry.json'
    return json.loads(path.read_text(encoding='utf-8'))['routes']


def _route_segments(data, route, source, target):
    """Project a quoted leg onto its exact compiled map curves."""
    parent = route.get('parent_route')
    geometry = _route_geometry().get(parent or route['id'])
    if geometry is None:
        return []
    if parent:
        sections = geometry['city_sections']
        chain = [geometry['from'], *(section['to'] for section in sections)]
        start, end = chain.index(source), chain.index(target)
        first, last = sorted((start, end))
        parts = [part for section in sections[first:last] for part in section['parts']]
        forward = start < end
    else:
        parts = geometry['parts']
        forward = geometry['from'] == source

    # A water link's access roads have no directional marker. The audited
    # curves of one-way corridors already follow their permitted direction.
    one_way = not route_allowed(data, route, target, source)
    if one_way and not forward:
        raise ValueError('One-way route geometry runs against the permitted direction')
    return [dict(mode=part['mode'], d=part['d'], route_id=route['id'],
                 one_way=one_way and part['mode'] == route['mode'],
                 **{'from': source, 'to': target})
            for part in (parts if forward else reversed(parts))]


def _quote_segments(data, legs):
    return [segment for leg in legs
            for segment in _route_segments(data, leg, leg['from'], leg['to'])]


def _route_restrictions(data, routes, state, source, target):
    """Find known direct corridors rejected before the path search."""
    pair = {source, target}
    date = (state.year, state.month)
    restrictions = []
    for route in routes:
        candidates = route.get('transit_variants') or (route,)
        for candidate in candidates:
            if {candidate['from'], candidate['to']} != pair:
                continue
            info = {'mode': candidate['mode'], 'from': source, 'to': target,
                    'route_id': candidate['id']}
            if not available(route, *date):
                opens = route.get('availability', {}).get('from')
                if opens and date < tuple(opens):
                    restrictions.append(dict(info, reason='not_yet_open', date=list(opens)))
                else:
                    closure = next((period for period in route.get('closures', ())
                                    if tuple(period['from']) <= date < tuple(period['to'])), None)
                    closed = dict(info, reason='closed')
                    if closure:
                        closed['date'] = list(closure['to'])
                    restrictions.append(closed)
                continue
            via = [city for city in candidate.get('via', ()) if city in state.cities]
            if via:
                if candidate['from'] != source:
                    via.reverse()
                restrictions.append(dict(info, reason='requires_stop', via=via))
            elif not route_allowed(data, candidate, source, target):
                restrictions.append({**info, 'reason': 'one_way', 'from': target, 'to': source,
                                     'segments': _route_segments(data, candidate, target, source)})
            elif winter_weather.blocked(state,candidate):
                restrictions.append(dict(info,reason='river_frozen',
                                          segments=_route_segments(data,candidate,source,target)))
    return restrictions


def _compact_quote(data, quote, **details):
    return dict(path=quote['path'], days=quote['days'], modes=quote['modes'],
                route_ids=[route['id'] for route in quote['routes']],
                segments=_quote_segments(data, quote['routes']), **details)


def _pair_quotes(game, state, source, target, direct_routes, *, own_destination):
    # Keep the command's quoted durations and modes, including seasonal effects.
    modes = {'fastest', 'land'} if own_destination else set()
    if direct_routes:
        modes.update({'fastest', *(route['mode'] for route in direct_routes)})
        if any(route.get('special') in ('yinping', 'ziwu') for route in direct_routes):
            modes.add('special')
    if game._exploration_route(source, target):
        modes.add('explore')
    for mode in game._travel_modes():
        if mode not in modes:
            continue
        quote = game._travel_path(state, source, target, state.player, mode,
                                  adjacent=not own_destination)
        if quote:
            option=_compact_quote(game.catalog.data, quote, mode=mode)
            if winter_weather.stage(state)>=2:
                option.update(days=winter_travel.quote_days(game,state,quote),
                              weather=winter_travel.preview(game,state,quote))
            yield option


def _direct_options(quotes):
    """Collapse mode aliases while keeping a selectable route command."""
    direct = {}
    for quote in quotes:
        if len(quote['path']) != 2:
            continue
        identity = (tuple(quote['route_ids']), quote['days'])
        earlier = direct.get(identity)
        if earlier is None or earlier['mode'] == 'fastest' or quote['mode'] == 'special':
            direct[identity] = quote
    return sorted(direct.values(), key=lambda quote: (quote['days'], quote['route_ids']))


def _staged_attack(game, state, source, target, known):
    """Suggest a friendly transfer followed by a known direct attack, if possible."""
    data = game.catalog.data
    candidates = set()
    for route in known:
        if target not in (route['from'], route['to']):
            continue
        via = route['to'] if route['from'] == target else route['from']
        city = state.cities.get(via)
        if (via != source and city and city.owner == state.player
                and route_allowed(data, route, via, target)):
            candidates.add(via)
    best = None
    for via in sorted(candidates):
        if game._city_occupancy(state, state.cities[via]) >= game.catalog.rules.city_officer_capacity:
            continue
        transfer = game._travel_path(state, source, via, state.player)
        if not transfer:
            continue
        attack = game._travel_path(state, via, target, state.player, adjacent=True)
        if not attack:
            continue
        days = winter_travel.quote_days(game,state,transfer)+winter_travel.quote_days(game,state,attack)
        if best is None or days < best['days']:
            best = dict(kind='staged_attack', via=via,
                        path=transfer['path'] + attack['path'][1:], days=days,
                        modes=sorted(set(transfer['modes'] + attack['modes'])),
                        segments=_quote_segments(data, transfer['routes'] + attack['routes']))
    return best


def preview(game, state, source, target, revision):
    result = dict(source=source, target=target, revision=revision,
                  status='same_city', options=[], restrictions=[], detour=None)
    if source == target:
        return result

    data = game.catalog.data
    owner = state.cities[target].owner
    if historical_campaigns.allied(state, state.player, owner):
        result['status'] = 'non_aggression'
        return result

    discovered = set(state.extension['travel']['discovered'])
    routes = data['travel_routes'] + [route for route in data.get('exploration_routes', ())
                                      if route['id'] in discovered]
    known = game._known_routes(state)
    direct_routes = [route for route in known if {route['from'], route['to']} == {source, target}
                     and route_allowed(data, route, source, target)]
    result['restrictions'] = _route_restrictions(data, routes, state, source, target)
    own_destination = owner == state.player
    quotes = list(_pair_quotes(game, state, source, target, direct_routes,
                               own_destination=own_destination))
    result['options'] = _direct_options(quotes)
    if own_destination:
        result['status'] = 'own_city'
        detour = min((quote for quote in quotes if len(quote['path']) > 2),
                     key=lambda quote: quote['days'], default=None)
        if detour:
            result['detour'] = dict(detour, kind='transfer')
    elif result['options']:
        result['status'] = 'available'
    else:
        result['status'] = 'no_direct_route'
        result['detour'] = _staged_attack(game, state, source, target, known)
    return result


def preview_transfer(game, state, source, target, ids, mode, revision):
    """Add map geometry to the same deterministic detour used at confirmation."""
    from .transfer_supply import detour

    primary = game._travel_path(state,source,target,state.player,mode,officers=ids)
    alternative = detour(game, state, source, target, ids, mode, primary)
    data = game.catalog.data

    def with_geometry(quote):
        if not quote:
            return None
        return dict(quote, segments=_quote_segments(data, quote['routes']),
                    logistics=logistics_cost(game,state,ids,quote))

    return dict(source=source, target=target, revision=revision, route_mode=mode,
                primary=with_geometry(primary), detour=with_geometry(alternative))


def logistics_cost(game, state, ids, quote, *, cargo=0, reserves=0):
    from . import logistics_rules as rules, logistics, march_supply

    parts = rules.plan(quote, march_supply.travel_rules(game))
    weighted = rules.version(state)==rules.CURRENT
    units = march_supply.ration_units(state,ids,reserves)
    divisor = march_supply.denominator() * (rules.RATION_SCALE if weighted else 1)
    dynamic=winter_weather.stage(state)>=2
    total = rules.ceil_div(units*march_supply.quoted_weight(game,state,quote,quote['days'],version=rules.version(state)),divisor)
    basic = march_supply.cost(units,0,quote['days'])
    stops = []
    progress = last = nutrition = 0
    owner = state.cities[quote['path'][0]].owner
    for index,leg in enumerate(quote['routes']):
        progress += leg['days']
        reaching = state.cities[leg['to']]
        if reaching.owner != owner and index+1 != len(quote['routes']):
            continue
        weight = (march_supply.quoted_weight(game,state,quote,progress-last,offset=last) if dynamic else
                  rules.weight(parts,last,progress-last) if weighted else progress-last)
        charge = units*weight
        needed = max(0,rules.ceil_div(charge-nutrition,divisor))
        if last:
            city=quote['path'][last_index]
            stock=state.cities[city].grain
            days=winter_travel.forecast(game,state,quote,position=last*winter_travel.QUANTA,
                                       stop=progress*winter_travel.QUANTA)[0] if dynamic else progress-last
            stops.append(dict(city=city,next=reaching.id,days=days,stock=stock,
                              required=needed,shortfall=max(0,needed-stock),
                              conditional=any(stop['shortfall'] for stop in stops)))
        nutrition += needed*divisor-charge
        last = progress
        last_index = index+1
    estimated_cargo = logistics.projected_grain(game,quote,cargo,state=state) if weighted and cargo else cargo
    result=dict(initial_grain=march_supply.estimate(state,ids,quote,reserves,game=game),
                base_grain=basic,extra_grain=total-basic,total_grain=total,cargo_loss=cargo-estimated_cargo,
                delivered_grain=estimated_cargo,refills=stops,time_ticks=rules.time_by_mode(parts),
                ticks_per_day=rules.DAY_TICKS,percent=dict(rules.MARCH_SUPPLY_PERCENT) if weighted else {},
                hazards=[leg['hazard'] for leg in quote['routes'] if leg.get('hazard')])
    if dynamic:
        result['weather']=winter_travel.preview(game,state,quote,units=units,cargo=cargo)
    return result


def preview_logistics(game,state,source,target,ids,mode,purpose,cargo,reserves,revision):
    from . import historical_campaigns, logistics
    from .transfer_supply import MINIMUM_GRAIN

    owner = state.cities[source].owner
    target_owner = state.cities[target].owner
    if purpose == 'attack' and (owner == target_owner or historical_campaigns.allied(state,owner,target_owner)):
        return dict(revision=revision,primary=None,fastest=None,minimum=None,blocked_reason='allied_destination')
    if purpose == 'convoy':
        policy = state.extension['logistics']['cities'][source]['policy']
        engine = logistics._safe_engine(game,policy)
    else:
        engine = game

    def find(which):
        return engine._travel_path(state,source,target,owner,which,adjacent=purpose=='attack',
                                   officers=ids,cargo=cargo,reserves=reserves)

    fastest = find('fastest')
    minimum = find(MINIMUM_GRAIN)
    primary = fastest if mode=='fastest' else minimum if mode==MINIMUM_GRAIN else find(mode)
    back = engine._travel_path(state,target,source,owner,'fastest')
    expected_return = None if back is None else logistics_cost(game,state,ids,back)['total_grain']
    data = game.catalog.data

    def decorate(quote):
        if quote is None:
            return None
        return dict(quote,segments=_quote_segments(data,quote['routes']),
                    logistics=dict(logistics_cost(game,state,ids,quote,cargo=cargo,reserves=reserves),
                                   return_grain=expected_return))

    return dict(revision=revision,primary=decorate(primary),fastest=decorate(fastest),
                minimum=decorate(minimum),blocked_reason=None if primary else
                'no_provisionable_route' if mode==MINIMUM_GRAIN else 'no_route')
