"""Resolve physical road sections into the currently active city graph.

The map keeps one shared painted road. A road which really meets an active
city must stop there for control and daily supply; an absent city leaves the
same physical road continuous. Immutable section quotes are compiled once,
so the Python reference and Rust/WASM consume identical distances and IDs.
"""


def available(route, year=None, month=None):
    window = route.get('availability')
    if year is None:
        return True
    date = (year, month)
    if window and (('from' in window and date < tuple(window['from']))
                   or ('to' in window and date >= tuple(window['to']))):
        return False
    return not any(tuple(period['from']) <= date < tuple(period['to'])
                   for period in route.get('closures', []))


def variants(routes):
    """All immutable identities, including a bypass used before city creation."""
    for route in routes:
        yield route
        yield from route.get('transit_variants', [])


def valid_departure(route, catalog, year, month):
    """Validate a saved leg against its departure, never today's new cities."""
    return (not route.get('transit_variants') and available(route, year, month)
            and not set(route.get('via', [])).intersection(catalog.active_city_ids(year, month)))


def effective(routes, cities=None, year=None, month=None):
    """Use only consecutive active stops, never jump over a live city."""
    active = None if cities is None else set(cities)
    result = []
    for route in routes:
        if not available(route, year, month):
            continue
        sections = route.get('transit_variants')
        if not sections:
            result.append(route)
            continue
        for section in sections:
            if active is None or (section['from'] in active and section['to'] in active
                    and not active.intersection(section['via'])):
                result.append(section)
    return result
