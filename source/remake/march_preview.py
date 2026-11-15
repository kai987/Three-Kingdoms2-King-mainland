"""Explain a selected city pair with the campaign's current route rules."""
from . import historical_campaigns
from .route_hazards import _python_route_allowed as route_allowed
from .route_network import available


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
                restrictions.append({**info, 'reason': 'one_way', 'from': target, 'to': source})
    return restrictions


def _compact_quote(quote, **details):
    return dict(path=quote['path'], days=quote['days'], modes=quote['modes'],
                route_ids=[route['id'] for route in quote['routes']], **details)


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
            yield _compact_quote(quote, mode=mode)


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
        days = transfer['days'] + attack['days']
        if best is None or days < best['days']:
            best = dict(kind='staged_attack', via=via,
                        path=transfer['path'] + attack['path'][1:], days=days,
                        modes=sorted(set(transfer['modes'] + attack['modes'])))
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
