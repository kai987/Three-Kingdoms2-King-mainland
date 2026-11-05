"""Source-based cultivation, industry and population development.

Original integer development/tax/low-governance calculations are retained.
Opening metrics, monthly relative production and disaster links are explicit
remake adaptations; see docs/city-development-rules.md. Reads never initialize
the extension, debit stocks, or advance the campaign random generator.
"""
from copy import deepcopy

from . import command_books
from .city_economy import income_at, tier_at
from .errors import GameError
from .officers import ref_sort_key

SCHEMA = 'tk2-city-development-v1'
LIMITS = dict(land=999, industry=999, population=999900, governance=100)
ACTIONS = dict(develop_land='land', develop_industry='industry', develop_population='population')
DEFAULTS = {tier: dict(land=150*size, industry=150*size,
                       population=50000*size, governance=70)
            for tier, size in (('normal', 1), ('large', 2), ('giant', 3))}
RULES = dict(enabled=True, unrest_enabled=True, ai_enabled=True, ai_gold_floor=100)
_POOL_FIELDS = {'schema', 'cities', 'last_month', 'auto_turns'}
_CITY_FIELDS = {'owner', 'land', 'industry', 'population', 'governance', 'baseline', 'cooldown'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _month(state):
    return state.year*12 + state.month-1


def _rules(game):
    values = game.catalog.data.get('city_development_rules', {})
    if not isinstance(values, dict) or set(values)-set(RULES):
        raise ValueError('City development rule fields')
    result = dict(RULES, **values)
    if any(type(result[key]) is not bool for key in ('enabled', 'unrest_enabled', 'ai_enabled')):
        raise ValueError('City development boolean rule')
    if not _int(result['ai_gold_floor'], 0, 1000000000):
        raise ValueError('City development AI gold floor')
    return result


def _metrics(row):
    if (not isinstance(row, dict) or set(row) != set(LIMITS)
            or any(not _int(row[key], 0, cap) for key, cap in LIMITS.items())
            or row['population'] % 100):
        raise ValueError('City development metrics')


def opening_view(catalog, city_id):
    """Opening data uses the scenario date, never the current conquered tier."""
    if not isinstance(city_id, str) or city_id not in catalog.map_cities:
        raise ValueError('Unknown city development opening identity')
    data = catalog.data
    configured = data.get('initial_city_development', {})
    if (not isinstance(configured, dict) or set(configured)-set(catalog.map_cities)):
        raise ValueError('City development opening identities')
    override = configured.get(city_id, {})
    if not isinstance(override, dict) or set(override)-set(LIMITS):
        raise ValueError('City development opening fields')
    tier = tier_at(data, city_id, data['start_year'], data['start_month'])
    row = dict(DEFAULTS[tier], **override)
    _metrics(row)
    if row['population'] == 0:
        raise ValueError('City development opening population must be positive')
    return row


def _new_city(game, city):
    opening = opening_view(game.catalog, city.id)
    return dict(owner=city.owner, **opening, baseline=deepcopy(opening), cooldown=0)


def empty(game, state):
    _rules(game)
    return dict(schema=SCHEMA, cities={key: _new_city(game, city) for key, city in state.cities.items()},
                last_month=_month(state),
                auto_turns={owner: 0 for owner in sorted(game.catalog.factions) if owner != 'neutral'})


def synchronize(game, state):
    """Commit-time initialization; conquests retain the developed property."""
    if 'city_development' not in state.extension:
        state.extension['city_development'] = empty(game, state)
    pool = state.extension['city_development']
    for key, city in state.cities.items():
        row = pool['cities'].setdefault(key, _new_city(game, city))
        row['owner'] = city.owner
    for key in set(pool['cities'])-set(state.cities):
        del pool['cities'][key]
    for owner in game.catalog.factions:
        if owner != 'neutral':
            pool['auto_turns'].setdefault(owner, 0)


def _row(game, state, key):
    pool = state.extension.get('city_development')
    return pool['cities'][key] if pool is not None else _new_city(game, state.cities[key])


def tax_rate(governance):
    if not _int(governance, 0, 100):
        raise ValueError('City development governance')
    return 50 if governance <= 50 else 60 if governance <= 70 else 70 if governance <= 80 else 80 if governance <= 90 else 90 if governance < 100 else 100


def _production(row, field, difficulty):
    if difficulty not in ('easy', 'normal', 'hard'):
        raise ValueError('Unknown campaign difficulty')
    # Difficulty remains an AI-policy choice in this remake. Original normal
    # production coefficients apply identically to all players and factions.
    base, divisor = 60, 3
    # Factors, without original integer wrapping; divisors cancel in the ratio.
    return (row['population']//100) * (base + row[field]//divisor) * tax_rate(row['governance'])


def adjust_income(game, state, city_id, income):
    """Scale established dated production relative to immutable opening data."""
    result = dict(income)
    if not _rules(game)['enabled']:
        return result
    row = _row(game, state, city_id)
    baseline = row['baseline']
    difficulty = state.extension.get('difficulty', 'normal')
    for resource, field in (('gold', 'industry'), ('grain', 'land')):
        if resource in result:
            numerator, denominator = _production(row, field, difficulty), _production(baseline, field, difficulty)
            result[resource] = result[resource] * numerator // denominator
    if 'reserves' in result:
        result['reserves'] = result['reserves'] * row['population'] // baseline['population']
    return result


def _gold_choices(intellect):
    start = 10 if intellect <= 50 else 14 if intellect <= 80 else 18
    return tuple(range(start, start+9, 2))


def _effect(gold, intellect, roll, field, before):
    units = max(1, (gold*intellect//100)*roll//10)
    if field == 'population':
        units = max(1, units//2)*100
    return min(units, LIMITS[field]-before)


def _profile(game, state, actor):
    return game.person_profile(state, actor) if hasattr(game, 'person_profile') else state.officers[actor].profile


def _quote(game, state, city, actor, kind, owner):
    from .facilities import _ready, _resident
    field = ACTIONS[kind]
    row = _row(game, state, city.id)
    officer = state.officers.get(actor)
    intellect = _profile(game, state, actor).intellect if officer is not None else 0
    choices = _gold_choices(intellect)
    # Integer floors, population halving and the remaining-cap clamp are all
    # monotone in cost/R. The two corners equal the old40-outcome extrema.
    gain_min = _effect(choices[0], intellect, 10, field, row[field])
    gain_max = _effect(choices[-1], intellect, 17, field, row[field])
    threshold = 3100 if field == 'population' else 31
    governance = row['governance']
    governance_min = min(100, governance+1+(gain_min >= threshold))-governance
    governance_max = min(100, governance+1+(gain_max >= threshold))-governance
    reason = ('disabled' if not _rules(game)['enabled'] else
              'city_unavailable' if city.owner != owner or not _ready(state, owner) else
              'actor_unavailable' if not _resident(game, state, city, actor, working=True, healthy=True) else
              'at_capacity' if row[field] == LIMITS[field] and row['governance'] == 100 else
              'command_books' if not command_books.can_spend(state, owner) else
              'gold' if city.gold < choices[-1] else None)
    return dict(kind=kind, development=field, actor=actor, intellect=intellect,
                gold_min=choices[0], gold_max=choices[-1], gain_min=gain_min, gain_max=gain_max,
                governance_gain_min=governance_min, governance_gain_max=governance_max, eligible=reason is None, reason=reason)


def quote(game, state, city_id, actor, kind, owner=None):
    if not isinstance(kind, str) or kind not in ACTIONS or not isinstance(city_id, str) or city_id not in state.cities:
        raise GameError('都市開發參數無效。')
    from .officers import parse_officer_ref
    try:
        actor = parse_officer_ref(actor, game.catalog.rules)
    except (TypeError, ValueError) as error:
        raise GameError('請選擇有效的本城武將。') from error
    return _quote(game, state, state.cities[city_id], actor, kind, state.player if owner is None else owner)


def execute(game, state, payload, owner):
    """One accepted operation consumes one shared order and two seeded draws."""
    if not isinstance(payload, dict) or set(payload) != {'city', 'actor', 'kind'}:
        raise GameError('都市開發參數無效。')
    offer = quote(game, state, payload['city'], payload['actor'], payload['kind'], owner)
    if not offer['eligible']:
        raise GameError({'disabled': '本戰役未啟用都市開發。', 'at_capacity': '開發與統治度已達上限。',
                         'gold': '本城資金不足，請備妥報價上限。', 'command_books': '本勢力命令書不足。'}
                        .get(offer['reason'], '請選擇本城健康、在場且可任職的執行武將。'))
    # Eligibility precedes every write/draw; Campaign commands execute on copies.
    synchronize(game, state)
    city = state.cities[payload['city']]
    row = state.extension['city_development']['cities'][city.id]
    field, actor = offer['development'], offer['actor']
    cost = _gold_choices(offer['intellect'])[state.rng.next()%5]
    gain = _effect(cost, offer['intellect'], 10+state.rng.next()%8, field, row[field])
    before, governance = row[field], row['governance']
    command_books.spend(state, city, payload['kind'])
    city.gold -= cost
    row[field] += gain
    row['governance'] = min(100, governance+1+(gain >= (3100 if field == 'population' else 31)))
    state.extension['officer_actions'][str(actor)] = state.turn
    details = dict(actor=state.officers[actor].person_id, development=field, gold=cost,
                   before=before, after=row[field], gain=gain,
                   governance_before=governance, governance_after=row['governance'])
    game._emit_event(state, 'city_developed', city_ids=[city.id], factions=[owner],
                     person_ids=[state.officers[actor].person_id], details=details)
    return details


def on_disaster(game, state, city_id, kind, severity):
    """Existing facility disaster residual percent also damages development.

    No new random draws; preparedness has already reduced this severity. This
    physical-development link is a remake adaptation, not the unrest algorithm.
    """
    if kind not in ('flood', 'drought') or not _int(severity, 0, 100):
        raise ValueError('City development disaster')
    if not _rules(game)['enabled'] or 'city_development' not in state.extension:
        return dict(land_loss=0, industry_loss=0)
    row = state.extension['city_development']['cities'][city_id]
    land = row['land']*severity//100
    industry = row['industry']*severity//100 if kind == 'flood' else 0
    row['land'] -= land
    row['industry'] -= industry
    return dict(land_loss=land, industry_loss=industry)


def month_rollover(game, state):
    if 'city_development' not in state.extension:
        return []
    pool, month = state.extension['city_development'], _month(state)
    if pool['last_month'] >= month:
        return []
    pool['last_month'] = month
    rules = _rules(game)
    if not rules['enabled'] or not rules['unrest_enabled']:
        return []
    results = []
    for key, city in sorted(state.cities.items()):
        row = pool['cities'][key]
        if city.owner == 'neutral':
            continue
        if row['cooldown']:
            row['cooldown'] -= 1
            continue
        governance = row['governance']
        index = 3 if governance < 20 else 2 if governance < 30 else 1 if governance < 40 else 0 if governance < 50 else -1
        if index < 0 or state.rng.next()%100 >= (5, 10, 30, 50)[index]:
            continue
        row['cooldown'] = 6
        category = ('population', 'resources', 'development')[state.rng.next()%3]
        losses = dict(gold_loss=0, grain_loss=0, population_loss=0, land_loss=0, industry_loss=0)
        if category == 'population':
            loss = (row['population']//100//16)*(1, 2, 3, 4)[index]*100
            row['population'] -= loss
            losses['population_loss'] = loss
        elif category == 'resources':
            for resource in ('gold', 'grain'):
                loss = getattr(city, resource)//16*(4, 6, 7, 8)[index]
                setattr(city, resource, getattr(city, resource)-loss)
                losses[resource+'_loss'] = loss
        else:
            for field in ('land', 'industry'):
                loss = row[field]//16*(4, 6, 7, 8)[index]
                row[field] -= loss
                losses[field+'_loss'] = loss
        details = dict(governance=governance, category=category, **losses)
        game._emit_event(state, 'civil_unrest', city_ids=[key], factions=[city.owner], person_ids=[], details=details)
        results.append(dict(city=key, **details))
    return results


def auto_turn(game, state, owner):
    """AI selects a weak productive field, using the very same paid service."""
    from .facilities import _ready, _resident
    rules = _rules(game)
    if (owner == state.player or not rules['enabled'] or not rules['ai_enabled']
            or not _ready(state, owner) or not command_books.can_spend(state, owner)):
        return []
    synchronize(game, state)
    pool = state.extension['city_development']
    if pool['auto_turns'].get(owner) == state.turn:
        return []
    pool['auto_turns'][owner] = state.turn
    options = []
    for key, city in sorted(state.cities.items()):
        if city.owner != owner:
            continue
        actors = [ident for ident in city.roster.officer_ids if _resident(game, state, city, ident, working=True, healthy=True)]
        if not actors:
            continue
        actor = min(actors, key=lambda ident: (-_profile(game, state, ident).intellect, ref_sort_key(ident)))
        row = pool['cities'][key]
        for kind, field in ACTIONS.items():
            offer = quote(game, state, key, actor, kind, owner)
            if offer['eligible'] and city.gold-offer['gold_max'] >= rules['ai_gold_floor']:
                # Cross-products keep ordering deterministic and avoid floats.
                weakness = row[field]*10000//max(1, row['baseline'][field])
                options.append((row['governance'], weakness, key, kind, actor))
    if not options:
        return []
    _, _, key, kind, actor = min(options)
    return [dict(city=key, **execute(game, state, dict(city=key, kind=kind, actor=actor), owner))]


def view(game, state):
    result = dict(schema=SCHEMA, enabled=_rules(game)['enabled'], limits=dict(LIMITS), cities={})
    if state is None:
        return result
    from .facilities import _resident
    for key, city in state.cities.items():
        row = _row(game, state, key)
        interactive = city.owner == state.player and state.phase == 'city'
        actors = sorted((ident for ident in city.roster.officer_ids
                         if interactive and _resident(game, state, city, ident, working=True, healthy=True)), key=ref_sort_key)
        quotes = {str(actor): {kind: _quote(game, state, city, actor, kind, state.player) for kind in ACTIONS} for actor in actors}
        best = min(actors, key=lambda ident: (-_profile(game, state, ident).intellect, ref_sort_key(ident))) if actors else None
        base_income = income_at(game.catalog.data, key, state.year, state.month) or dict(gold=0, grain=0, reserves=0)
        result['cities'][key] = dict(owner=city.owner, **{field: row[field] for field in LIMITS},
            baseline=deepcopy(row['baseline']), cooldown=row['cooldown'], tax_rate=tax_rate(row['governance']),
            eligible_actors=actors, actor_quotes=quotes,
            actions=deepcopy(quotes[str(best)]) if best is not None else {},
            income=adjust_income(game, state, key, base_income))
    return result


def validate(game, state):
    _rules(game)
    # A previous-format campaign is readable without rewriting a single byte.
    if 'city_development' not in state.extension:
        return
    pool = state.extension['city_development']
    if (not isinstance(pool, dict) or set(pool) != _POOL_FIELDS or pool['schema'] != SCHEMA
            or not isinstance(pool['cities'], dict) or set(pool['cities']) != set(state.cities)):
        raise ValueError('City development schema')
    opening_month = game.catalog.data['start_year']*12+game.catalog.data['start_month']-1
    if not _int(pool['last_month'], opening_month, _month(state)):
        raise ValueError('City development monthly receipt')
    owners = set(game.catalog.factions)-{'neutral'}
    if (not isinstance(pool['auto_turns'], dict) or set(pool['auto_turns']) != owners
            or any(not _int(turn, 0, state.turn) for turn in pool['auto_turns'].values())):
        raise ValueError('City development AI receipt')
    for key, city in state.cities.items():
        row = pool['cities'][key]
        if not isinstance(row, dict) or set(row) != _CITY_FIELDS or row['owner'] != city.owner or not _int(row['cooldown'], 0, 6):
            raise ValueError('City development city fields')
        _metrics({field: row[field] for field in LIMITS})
        if row['baseline'] != opening_view(game.catalog, key):
            raise ValueError('City development immutable opening reference')
