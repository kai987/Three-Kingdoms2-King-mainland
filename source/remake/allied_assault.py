"""Claim a captured city and split its stores between two allied armies."""

from . import battle_allegiance, domestic
from .march_supply import LIMIT


RESOURCES = ('gold', 'grain', 'reserves')


def capture_actor(state, battle):
    extended = battle['extended']
    eligible = [unit for unit in battle['attackers'] if str(unit['id']) not in extended['surrenders']
                and state.officers[unit['id']].alive]
    claimants = ((extended.get('occupation') or {}).get('actor'), extended.get('capture_actor'))
    for ident in claimants:
        if any(unit['id'] == ident for unit in eligible):
            return ident
    return next((unit['id'] for unit in eligible if unit['troops'] > 0), None)


def _destinations(game, state, target, owner, candidates):
    adjacent = set(game._neighbors(target.id, state))
    for nearby in (True, False):
        routes = []
        for city in candidates:
            if (city.id in adjacent) != nearby:
                continue
            quote = game._travel_path(state, target.id, city.id, owner, adjacent=nearby)
            if quote:
                routes.append((quote['days'], quote['distance_km'], city.id))
        for _, _, city_id in sorted(routes):
            yield state.cities[city_id]


def _return_officers(game, state, battle, target, owner, ids):
    if not ids:
        return []
    capacity = game.catalog.rules.city_officer_capacity
    returning = set(ids)
    candidates = [city for city in state.cities.values() if city.owner == owner
                  and len(returning.difference(city.roster.officer_ids)) <= capacity - game._city_occupancy(state, city)]
    destination = next(_destinations(game, state, target, owner, candidates), None)
    homes = {ident: state.cities[battle_allegiance.home_for(battle, {'id': ident}, 'attackers')]
             for ident in ids}
    if destination is None:
        # All units retained their original roster slots while away.
        return sorted({home.id for home in homes.values()})
    for ident, home in homes.items():
        if home.id != destination.id:
            home.roster.officer_ids.remove(ident)
            destination.roster.officer_ids.append(ident)
    domestic.on_arrival(game, state, ids, destination.id)
    return [destination.id]


def settle_capture(game, state, battle, target, captor, selected):
    """Settle the assisting faction's officers and actual shares of city stock."""
    provisions = battle['extended']['coalition']['provisions']
    ally = next(owner for owner in provisions if owner != captor)
    returning = [ident for ident in selected if state.officers[ident].faction_id == ally]
    returns = _return_officers(game, state, battle, target, ally, returning)
    troops = [sum(state.officers[ident].troops for ident in selected
                  if state.officers[ident].faction_id == owner) for owner in (captor, ally)]
    total = sum(troops)
    desired = {resource: getattr(target, resource) * troops[1] // total if total else 0
               for resource in RESOURCES}
    storage = [state.cities[city_id] for city_id in returns]
    if any(desired[resource] > sum(max(0, LIMIT - getattr(city, resource)) for city in storage)
           for resource in RESOURCES):
        rear = [city for city in state.cities.values() if city.owner == ally and city.id not in returns]
        storage.extend(_destinations(game, state, target, ally, rear))
    ally_share = {}
    for resource in RESOURCES:
        stock = getattr(target, resource)
        remaining = desired[resource]
        paid = 0
        for city in storage:
            amount = min(remaining, max(0, LIMIT - getattr(city, resource)))
            setattr(city, resource, getattr(city, resource) + amount)
            paid += amount
            remaining -= amount
        setattr(target, resource, stock - paid)
        ally_share[resource] = paid
    return dict(captor=captor, ally=ally, troops=troops,
                shares=[{resource: getattr(target, resource) for resource in RESOURCES}, ally_share],
                returns=returns)
