"""Read-only strategy for the same diplomacy orders available to players."""
from collections import defaultdict

from . import command_books, diplomacy, historical_campaigns
from .officers import ref_sort_key

TREATY_TURNS = 12
REPEAT_TURNS = 3
SURRENDER_GRACE_TURNS = 3
SURRENDER_MAX_CITIES = 3
GIFT_RESERVE = {'gold': 500, 'grain': 2000}


def _envoy_key(state, city, envoy):
    officer = state.officers[envoy['id']]
    return (-(envoy['intellect'] + envoy['virtue']), officer.troops, city, ref_sort_key(envoy['id']))


def _recent_order(state, owner, target, action):
    return any(row['kind'] == 'diplomacy_result'
               and row['turn'] > state.turn - REPEAT_TURNS
               and row['factions'] == [owner, target]
               and row['details']['action'] == action
               for row in state.extension['events']['items'])


def _frontiers(ai):
    holdings, borders = defaultdict(list), defaultdict(set)
    for city in ai.state.cities.values():
        if city.owner == 'neutral':
            continue
        holdings[city.owner].append(city)
        borders[city.owner].update(neighbor.id for neighbor in ai.neighbors(city)
                                  if neighbor.owner not in (city.owner, 'neutral'))
    return holdings, borders


def _gift(state, cities, target_cities, current, desired):
    """Give only surplus and stop at the smallest amount that meets the goal."""
    choices = []
    for city in cities:
        source = state.cities[city['id']]
        envoy = min(city['envoys'], key=lambda row: _envoy_key(state, source.id, row))
        for resource, reserve in GIFT_RESERVE.items():
            stock = getattr(source, resource)
            maximum = min(stock // 2, stock - reserve, city['limits'][resource],
                          max(100000000 - getattr(other, resource) for other in target_cities))
            if maximum <= 0:
                continue
            gain = lambda amount: diplomacy.gift_gain(resource, amount, envoy['intellect'], envoy['virtue'])
            _, unit = diplomacy.LIMITS[resource]
            achieved = min(desired, current + gain(maximum))
            if achieved <= current:
                continue
            thresholds = (1, *range(2 * unit, maximum, unit))
            amount = next((size for size in thresholds if current + gain(size) >= achieved), maximum)
            # Equivalent units, then the lower fraction of the donor's stock.
            choices.append((-achieved, amount * 1000 // unit, amount * 1000 // stock,
                            _envoy_key(state, source.id, envoy), resource, amount, source.id, envoy['id']))
    if choices:
        _, _, _, _, resource, amount, city, envoy = min(choices)
        return dict(city=city, envoy=envoy, resource=resource, amount=amount)
    return None


def _request_target(ai, target, enemy_owners, marches, ally_cities, historical_targets):
    """Ask for an attack the ally can supply against one of our border rivals."""
    state = ai.state
    if (target['id'] == state.player or not ai.budget
            or not command_books.can_spend(state, target['id'], 'depart')):
        return None
    eligible = [state.cities[key] for key in target['attack_cities']
                if state.cities[key].owner in enemy_owners and (target['id'], key) not in marches
                and (not historical_targets or key in historical_targets)]
    ranked = sorted(((ai.attack_requirement(city), city.id, city) for city in eligible),
                    key=lambda row: row[:2])
    # Inspect the three easiest fronts. Route quotes are expensive in large campaigns.
    for required, key, city in ranked[:3]:
        for source in ally_cities:
            if not any(neighbor.id == key for neighbor in ai.neighbors(source)):
                continue
            option = ai.attack_option(source, city)
            if option and option['survivors'] >= required:
                return key
    return None


def orders(ai, owner):
    """Return deterministic proposals. Only the shared service can commit them."""
    game, state = ai.game, ai.state
    books = state.extension['command_books']['factions'].get(owner)
    if (not books or owner == state.player or not command_books.can_spend(state, owner, 'diplomacy')
            or any(row['kind'] == 'diplomacy' for row in books['orders'])):
        return []
    options = diplomacy.command_options(game, state, owner)
    if not options['can_command']:
        return []
    cities = options['cities']
    city, envoy = min(((city['id'], envoy) for city in cities for envoy in city['envoys']),
                      key=lambda pair: _envoy_key(state, *pair))
    base = dict(city=city, envoy=envoy['id'])

    holdings, borders = _frontiers(ai)
    border_owners = {faction: {state.cities[key].owner for key in keys} for faction, keys in borders.items()}
    historical_fronts = {faction: historical_campaigns.priority_targets(state, faction, keys)[0]
                         for faction, keys in borders.items()}
    historical_opponents = {faction: {state.cities[key].owner for key in keys}
                            for faction, keys in historical_fronts.items()}
    powers = {faction: diplomacy.faction_power(state, owned) for faction, owned in holdings.items()}
    active = {(march['owner'], march['target']) for march in state.extension['travel']['marches']
              if march['kind'] == 'attack' and march['status'] == 'outbound'}
    hostile_pairs = {(attacker, state.cities[key].owner) for attacker, key in active}
    own_borders = border_owners.get(owner, set())
    discretionary = command_books.remaining(state, owner) > command_books.cost('diplomacy')
    proposals = []

    def add(rank, target, action, **fields):
        proposals.append((rank, target, dict(base, action=action, target=target) | fields))

    for option in options['targets']:
        target, actions, score = option['id'], option['actions'], option['score']
        protected_front = (target in historical_opponents.get(owner, set())
                           or owner in historical_opponents.get(target, set()))
        recent = lambda action: _recent_order(state, owner, target, action)
        can_gift = actions['goodwill'] and discretionary and not recent('goodwill')
        if actions['return_captives']:
            captives = (state.officers[row['id']] for row in option['captives'])
            captive = min(captives, key=lambda row: (
                -(row.profile.martial_strength + row.profile.intellect + row.profile.virtue),
                ref_sort_key(row.runtime_id)))
            if diplomacy.can_recover(score, envoy['intellect'], envoy['virtue']):
                add(0, target, 'return_captives', prisoner=captive.runtime_id)
            elif can_gift:
                desired = next(value for value in range(score + 1, 101)
                               if diplomacy.can_recover(value, envoy['intellect'], envoy['virtue']))
                gift = _gift(state, cities, holdings[target], score, desired)
                if gift:
                    add(3, target, 'goodwill', **gift)
                # Do not propose a second gift for the same pair.
                can_gift = False
        if (actions['surrender'] and target in own_borders and not protected_front
                and state.turn > SURRENDER_GRACE_TURNS and len(holdings[target]) <= SURRENDER_MAX_CITIES):
            lost_city = any(key in state.cities and initial == target and state.cities[key].owner != target
                            for key, initial in game.catalog.data['initial_owners'].items())
            if lost_city or score < diplomacy.NORMAL:
                add(1, target, 'surrender')
        if not discretionary:
            continue
        if actions['request_attack'] and not recent('request_attack'):
            attack_city = _request_target(ai, option, own_borders, active, holdings[target],
                                          historical_fronts.get(target, set()))
            if attack_city:
                add(2, target, 'request_attack', attack_city=attack_city)
        if (protected_front or target not in own_borders
                or (owner, target) in hostile_pairs or (target, owner) in hostile_pairs):
            continue
        common_rivals = {rival for rival in own_borders & border_owners.get(target, set())
                         if powers[rival] >= max(powers[owner], powers[target])
                         and not historical_campaigns.allied(state, owner, rival)
                         and not historical_campaigns.allied(state, target, rival)}
        if not common_rivals:
            continue
        # A treaty needs a third enemy. Two remaining sides cannot renew it.
        if can_gift and score < diplomacy.FRIENDLY:
            gift = _gift(state, cities, holdings[target], score, diplomacy.FRIENDLY)
            if gift:
                add(4, target, 'goodwill', **gift)
        if actions['alliance']:
            add(5, target, 'alliance', duration=TREATY_TURNS)

    return [payload for _, _, payload in sorted(proposals, key=lambda row: row[:2])]
