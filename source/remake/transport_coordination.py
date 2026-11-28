"""Opt-in faction transport coordination. Dispatch and delivery stay with their services."""
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from itertools import groupby
from time import process_time

from . import army_relief, command_books, convoy_relief, faction_economy, logistics
from . import logistics_rules, logistics_strategy, strategic_granary, transport_emergency, transshipment
from . import transport_candidates, transport_demands
from .errors import GameError
from .transport_allocation import select
from .transport_demands import Demand

FIELD = 'transport_coordination_rules_version'
OPTIONS = 'transport_coordination_options'
POOL = 'transport_coordination'
VERSION = 3041
RECOVERY = 30411
CONSUMPTION = 30412
RECOVERY_VERSIONS = (RECOVERY, CONSUMPTION)
FEATURES = frozenset(('pagination', 'diversity', 'requote', 'reserve', 'preparation',
                      'transit', 'economics', 'incremental'))
CONSUMPTION_FEATURES = FEATURES | {'meal_priority', 'route_reuse'}
TARGETS = 12
SEARCH_TARGETS = 384
PHASES = {'urgent': 2, 'followup': 4, 'elective': 6}
KINDS = {'city', 'march', 'convoy', 'mobilization', 'winter', 'agriculture', 'storage', 'transshipment'}
PREPARATIONS = {'front_defence', 'front_reserve', 'military_candidate'}
CHANNELS = {'local', 'ordinary', 'granary', 'regional', 'army', 'convoy', 'transshipment'}
INVALID = '輸送統籌規則版本或選項無效。'
_observer = ContextVar('transport_coordination_observer', default=(None, False))


def enabled(state):
    return bool(state is not None and state.extension.get(FIELD) in (VERSION, *RECOVERY_VERSIONS))


def feature(state, name):
    return (state.extension.get(FIELD) in RECOVERY_VERSIONS
            and state.extension[POOL]['features'].get(name, False))


def transit_protection(state, owner):
    return feature(state, 'transit') and (state.extension[FIELD] != CONSUMPTION or owner != state.player)


def dated_transit_protection(state, owner):
    return state.extension.get(FIELD) == CONSUMPTION and transit_protection(state, owner)


def _features(options, names):
    return (isinstance(options, dict) and set(options) <= names
            and all(type(value) is bool for value in options.values()))


def initialize(state, version, options=None):
    names = CONSUMPTION_FEATURES if version == CONSUMPTION else FEATURES
    if (type(version) is not int or version not in (0, VERSION, *RECOVERY_VERSIONS)
            or version and logistics_rules.version(state) != logistics_rules.CURRENT
            or options is not None and (
                not isinstance(options, dict) or type(options.get('efficiency', True)) is not bool
                or (set(options) != {'efficiency'} if version == VERSION else
                    version not in RECOVERY_VERSIONS or set(options) - {'efficiency', 'features'}
                    or not _features(options.get('features', {}), names)))):
        raise GameError(INVALID)
    if version:
        options = options or {}
        ledger = dict(efficiency=options.get('efficiency', True), phases={}, episodes={}, convoys={},
                      summaries={}, completed={}, support={})
        if version in RECOVERY_VERSIONS:
            ledger['features'] = {key: options.get('features', {}).get(key, True) for key in sorted(names)}
        state.extension.update({FIELD: version, POOL: ledger})


@contextmanager
def observing(record, *, shadow=False):
    token = _observer.set((record, shadow))
    try:
        yield
    finally:
        _observer.reset(token)


def observe(event, state, **details):
    record, _ = _observer.get()
    if record is not None:
        record(event, dict(turn=state.turn, year=state.year, month=state.month, day=state.day, **details))


def shadowing(state):
    return not enabled(state) and _observer.get()[1]


def request(state, owner, city, grain, gold, turns, *, purpose='front_reserve', target=None):
    """Keep approved stock goals through an interrupted AI turn."""
    support = state.extension[POOL]['support']
    book = support.get(owner)
    if book is None or book['turn'] != state.turn:
        book = support[owner] = dict(turn=state.turn, goals={})
    goals = book['goals']
    if feature(state, 'preparation'):
        key = f'{purpose}:{target or city}'
        goals.setdefault(city, {})[key] = dict(kind=purpose, target=target, grain=grain, gold=gold,
                                              deadline=state.turn+max(1, turns))
        observe('military_preparation_request', state, owner=owner, city=city, plan=key,
                purpose=purpose, target=target, requested=grain, gold=gold, deadline=state.turn+max(1, turns))
        return
    prior_grain, prior_gold, prior_turns = goals.get(city, (0, 0, turns))
    goals[city] = [max(grain, prior_grain), max(gold, prior_gold), min(turns, prior_turns)]


def _routing_plan(game, state, owner):
    return faction_economy.plan(game, state, owner, granary=strategic_granary.enabled(state), coordinated=True)


def _transfers(game, state, owner, plan):
    if not transshipment.enabled(state):
        return
    now = army_relief._calendar_tick(state)
    for row in transshipment._plans(state).values():
        if (row['owner'] != owner or row['status'] != 'active' or not transshipment._owned(state, row)
                or not any(batch['available'] for batch in row['batches'])):
            continue
        needed = transshipment._still_needed(game, state, row, {owner: plan})
        due = min(row['original_deadline'], row['promise'])
        if due > state.turn and needed:
            yield Demand(owner, 'transshipment', row['id'], 4, now + (due-state.turn)*10, needed,
                         needed, channels=('transshipment',))


def _discover(game, state, owner, plan, priority, additional):
    army = (army_relief.Planner(game, state, owner, coordinated=True)
            if logistics_strategy.army_relief(state) and any(
                row['owner'] == owner for row in state.extension['travel']['marches']) else None)
    convoys = (convoy_relief.Planner(game, state, owner, coordinated=True)
               if transport_emergency.stage(state) >= transport_emergency.EXTERNAL_RELIEF else None)
    rows = list(transport_demands.military(game, state, army, convoys))
    rows.extend(d for key in plan.cities if (d := transport_demands.city_shortage(game, state, plan, key)) is not None)
    if priority >= 3:
        prepared = feature(state, 'preparation')
        if prepared:
            supported = transport_demands.preparations(state, plan, additional)
        else:
            supported = transport_demands.approved_orders(state, owner)
            for key, (grain, gold, due) in additional.items():
                old_grain, old_gold, old_due = supported.get(key, (0, 0, due))
                supported[key] = max(grain, old_grain), max(gold, old_gold), min(due, old_due)
        rows.extend(transport_demands.reserves(game, state, plan, supported, include_storage=priority >= 6,
                                               preparations=prepared))
        rows.extend(_transfers(game, state, owner, plan))
    return rows, army, convoys


def _timers(state, owner, found, *, phase, shadow):
    records = {} if shadow else state.extension[POOL]['episodes'].setdefault(owner, {})
    # Keep the original deadline when a shipment temporarily covers a demand.
    linked = set() if shadow else {row['key'] for row in state.extension[POOL]['convoys'].values()
                                  if row['owner'] == owner}
    if phase == 'elective':
        seen = {row.key for row in found} | linked
        for key in set(records) - seen:
            del records[key]
    dated = []
    for demand in found:
        opening, deadline = records.setdefault(demand.key, [state.turn, demand.deadline])
        dated.append(replace(demand, created=opening, original=deadline))
    return dated


def _request_view(row):
    return dict(demand_id=row.episode, owner=row.owner, target_kind=row.kind, target=row.target,
                priority=row.priority, original_deadline=row.original_deadline, deadline=row.deadline,
                requested=row.requested, reliable=row.reliable, conditional=row.conditional,
                unresolved=row.remaining, channels=row.channels, gold=row.gold, created=row.created)


def _row_view(row):
    return dict(demand_id=row.demand.episode, target_kind=row.demand.kind, demand_target=row.demand.target,
                priority=row.demand.priority, channel=row.channel, source=row.source, target=row.target,
                escorts=row.escorts, mode=row.mode, arrival=row.arrival, conservative_arrival=row.conservative_arrival,
                net=row.net, conservative_net=row.conservative_net, load=row.load, rations=row.rations, gold=row.gold,
                outward_days=row.days, return_days=row.return_days, occupation_days=row.period,
                books=row.command_books, original_deadline=row.demand.original_deadline,
                timely_net=row.original_effect)


def _commit(game, state, row):
    demand, owner = row.demand, row.demand.owner
    books = command_books.remaining(state, owner)
    source = state.cities[row.source]
    grain, gold = source.grain, source.gold
    convoy, receipt, retained = None, 0, 0
    try:
        convoy, receipt, retained = transport_candidates.commit(game, state, row)
    except GameError as error:
        failure = str(error)
    else:
        failure = 'purchased_grain_retained' if retained else None if convoy or receipt else 'no_effective_delivery'
    cost = books - command_books.remaining(state, owner)
    observe('dispatch' if not failure else 'dispatch_failed', state, owner=owner,
            convoy=convoy, immediate_received=receipt, retained_purchase=retained, reason=failure,
            books_used=cost, source_grain_before=grain, source_grain_after=source.grain,
            source_gold_before=gold, source_gold_after=source.gold, **_row_view(row))
    recovery = state.extension.get(FIELD) in RECOVERY_VERSIONS
    credit_limit = min(demand.remaining, max(row.net, row.load))
    if convoy is not None:
        link = dict(
            owner=owner, key=demand.key, demand=row.demand.episode, kind=demand.kind, target=demand.target,
            deadline=demand.original_deadline, cap=credit_limit, channel=row.channel)
        if recovery:
            link.update(current_deadline=demand.deadline, original_cap=min(credit_limit, demand.original_balance()))
        state.extension[POOL]['convoys'][str(convoy)] = link
    if receipt:
        _complete(state, owner)
        credited = min(receipt, demand.remaining)
        current = (dict(timely_current=credited if row.arrival < demand.deadline else 0,
                        current_deadline=demand.deadline, credit_basis='warehouse_receipt') if recovery else {})
        initial = min(credited, demand.original_balance()) if recovery else credited
        observe('receipt', state, owner=owner, received=receipt, credited=credited,
                unallocated=receipt-credited, tick=row.arrival, channel=row.channel, convoy=None,
                demand_id=demand.episode, target_kind=demand.kind, target=demand.target,
                original_deadline=demand.original_deadline,
                timely=initial if row.arrival < demand.original_deadline else 0, **current)
    return not failure, bool(cost), failure


def _reserved_books(state, owner):
    return sum(command_books.cost('depart') for row in state.extension['ai_strategy'].get(owner, {}).get('orders', ())
               if row['march_id'] is None and row['departure_turn'] <= state.turn
               and state.cities[row['source']].owner == owner)


def run(game, state, owner, phase):
    if (not enabled(state) and not shadowing(state) or state.phase != 'ai'
            or owner in (state.player, 'neutral') or 'logistics' not in state.extension):
        return False
    recorder, shadow = _observer.get()
    shadow = shadow and not enabled(state)
    if not shadow:
        phases = state.extension[POOL]['phases'].setdefault(owner, {})
        if phases.get(phase) == state.turn:
            return False
        phases[phase] = state.turn
    if state.extension.get(FIELD) in RECOVERY_VERSIONS:
        return _run_recovery(game, state, owner, phase)
    support = {} if shadow else state.extension[POOL]['support'].get(owner, {})
    goals = support['goals'] if support.get('turn') == state.turn else {}
    limit = PHASES[phase]
    if shadow:
        limit = 6
    efficient = not shadow and state.extension[POOL]['efficiency']
    started = process_time()
    operation = transport_candidates.Pass(game, state, owner, efficient=efficient)
    work, refused = Counter(), set()
    available_sources = set()
    plan = None
    origins = command_books.remaining(state, owner)
    demands, choices = [], []
    while True:
        if plan is None:
            plan = _routing_plan(game, state, owner)
            work['economic_plans'] += 1
            found, army, convoys = _discover(game, state, owner, plan, limit, goals)
            demands = sorted(_timers(state, owner, found, phase=phase, shadow=shadow),
                             key=lambda row: (row.priority, row.original_deadline, -row.remaining, row.key))
            actionable = [d for d in demands if d.priority <= limit and (d.remaining or d.gold)]
            chosen = actionable[:TARGETS]
            books = command_books.remaining(state, owner)
            choices = (operation.build(chosen, plan, army, convoys, refused)
                       if chosen and books and work['committed'] < TARGETS else [])
            eligible = {row.demand.key for row in choices}
            available_sources.update(row.source for row in choices)
            if recorder is not None:
                stock = transport_demands.source_stock(state, plan)
                for rank, row in enumerate(actionable):
                    reason = ('candidate_limit' if rank >= TARGETS else 'command_books' if not books else
                              None if row.key in eligible else 'no_executable_quote')
                    observe('demand', state, **_request_view(row), phase=phase, outcome=reason,
                            donor_stock=stock - (state.cities[row.target].grain if isinstance(row.target, str) else 0),
                            blockers=dict(operation.failures.get(row.key, {})))
                for row in choices:
                    observe('candidate', state, owner=owner, phase=phase, **_row_view(row))
            work['pruned_demands'] += max(0, len(actionable)-TARGETS)
        books = command_books.remaining(state, owner)
        row = select(choices, books, efficient=efficient, reserve_for_orders=_reserved_books(state, owner))
        if row is None:
            break
        if shadow:
            observe('shadow_recommendation', state, phase=phase, owner=owner, available_books=books,
                    alternatives=len(choices), **_row_view(row))
            break
        success, changed, failure = _commit(game, state, row)
        if success:
            work['committed'] += 1
        else:
            refused.add(row.key)
            work['failed'] += 1
            if failure:
                operation.failures[row.demand.key]['revalidation'] += 1
        if changed or success:
            plan = None
        else:
            choices.remove(row)
    if not shadow:
        previous = state.extension[POOL]['summaries'].get(owner, {})
        state.extension[POOL]['summaries'][owner] = dict(
            turn=state.turn, urgent=sum(row.priority <= 2 and row.remaining > 0 for row in demands),
            demand=sum(row.requested for row in demands), reliable=sum(row.reliable for row in demands),
            remaining=sum(row.remaining for row in demands), sources=len(available_sources),
            dispatched=work['committed'] + (previous.get('dispatched', 0) if previous.get('turn') == state.turn else 0),
            blockers=dict(Counter(reason for key in operation.failures for reason in operation.failures[key])))
    observe('scheduler', state, owner=owner, phase=phase, shadow=shadow, initial_books=origins,
            remaining_books=command_books.remaining(state, owner), demand_count=len(demands),
            available_sources=len(available_sources), scheduler_cpu=process_time()-started,
            **dict(operation.work + work))
    return bool(work['committed'])


def _pages(rows, paginate):
    if not paginate:
        if rows:
            yield rows[:TARGETS]
        return
    for _, tier in groupby(rows, key=lambda row: row.priority):
        same_priority = list(tier)
        for start in range(0, len(same_priority), TARGETS):
            yield same_priority[start:start+TARGETS]


def _defer_city_quote(row, now):
    """A later warehouse delivery cannot use the urgency of a missed meal."""
    return (row.demand.kind == 'city' and row.demand.priority <= 2 and row.mode
            and not any(row.conservative_arrival < due <= now + 30
                        for due, _ in row.demand.installments))


def _try_recovery(game, state, choices, books, reserve, operation, work, refused):
    while (row := select(choices, books, efficient=operation.efficient, reserve_for_orders=reserve)) is not None:
        success, spent, failure = _commit(game, state, row)
        work['committed' if success else 'failed'] += 1
        if failure:
            refused.add(row.key)
            operation.failures[row.demand.key]['revalidation'] += 1
        if success or spent:
            return True
        choices.remove(row)
    return False


def _run_recovery(game, state, owner, phase):
    ledger = state.extension[POOL]
    efficient = ledger['efficiency']
    features = ledger['features']
    meal_priority = features.get('meal_priority', False)
    support = ledger['support'].get(owner, {})
    if features['preparation'] and support and support['turn'] < state.turn:
        if _observer.get()[0] is not None:
            for city, requests in support['goals'].items():
                for key, request in requests.items():
                    observe('military_preparation_expired', state, owner=owner, city=city,
                            plan=key, purpose=request['kind'], deadline=request['deadline'], reason='new_turn')
        del ledger['support'][owner]
        support = {}
    goals = support.get('goals', {}) if support.get('turn') == state.turn else {}
    operation = transport_candidates.Pass(game, state, owner, efficient=efficient, features=features)
    memo = {} if features['incremental'] else None
    started = process_time()
    origins = command_books.remaining(state, owner)
    recorder = _observer.get()[0]
    work, refused, available_sources = Counter(), set(), set()
    while True:
        plan = faction_economy.plan(game, state, owner, granary=strategic_granary.enabled(state),
                                   coordinated=True, forecast_memo=memo)
        work['economic_plans'] += 1
        found, army, convoys = _discover(game, state, owner, plan, PHASES[phase], goals)
        demands = sorted(_timers(state, owner, found, phase=phase, shadow=False),
                         key=lambda row: (row.priority, row.deadline if features['preparation']
                                          else row.original_deadline, -row.remaining, row.key))
        actionable = [row for row in demands if row.priority <= PHASES[phase] and (row.remaining or row.gold)]
        books = command_books.remaining(state, owner)
        reserve = _reserved_books(state, owner)
        stock = transport_demands.source_stock(state, plan) if recorder is not None else 0
        outcome = 'command_books' if not books else 'dispatch_limit' if work['committed'] >= TARGETS else None
        checked, changed, deferred = set(), False, []
        operation.next_plan()
        if not outcome:
            for page in _pages(actionable, features['pagination']):
                if deferred and page[0].priority > 4:
                    changed = _try_recovery(game, state, deferred, books, reserve, operation, work, refused)
                    deferred.clear()
                    if changed:
                        break
                budget = SEARCH_TARGETS - work['checked_demands']
                if budget <= 0:
                    outcome = 'search_budget'
                    break
                page = page[:budget]
                work['checked_demands'] += len(page)
                work['pages'] += 1
                choices = operation.build(page, plan, army, convoys, refused)
                kept = choices
                if meal_priority:
                    kept = []
                    for row in choices:
                        if _defer_city_quote(row, operation.now):
                            operation.failures[row.demand.key]['after_near_term_meals'] += 1
                            work['deferred_city_quotes'] += 1
                            if phase != 'urgent':
                                deferred.append(row)
                        else:
                            kept.append(row)
                eligible = {row.demand.key for row in kept
                            if row.command_books <= books - (reserve if row.demand.priority >= 3 else 0)}
                available_sources.update(row.source for row in kept)
                checked.update(row.key for row in page)
                if recorder is not None:
                    for demand in page:
                        status = 'has_offer' if demand.key in eligible else 'checked_no_executable_quote'
                        observe('demand', state, **_request_view(demand), phase=phase, outcome=status,
                                donor_stock=stock, blockers=dict(operation.failures.get(demand.key, {})))
                    for row in choices:
                        observe('candidate', state, owner=owner, phase=phase, **_row_view(row))
                changed = _try_recovery(game, state, kept, books, reserve, operation, work, refused)
                if changed:
                    break
            if not changed and deferred:
                changed = _try_recovery(game, state, deferred, books, reserve, operation, work, refused)
        if recorder is not None:
            for demand in actionable:
                if demand.key not in checked:
                    observe('demand', state, **_request_view(demand), phase=phase,
                            outcome=outcome or ('not_checked' if changed else 'candidate_limit'),
                            donor_stock=stock, blockers={})
            for demand in demands:
                if not demand.remaining and not demand.gold:
                    observe('demand', state, **_request_view(demand), phase=phase,
                            outcome='covered_by_stock_or_expected_receipts', donor_stock=stock, blockers={})
        if not changed:
            work['pruned_demands'] += len(actionable) - len(checked)
            break
    previous = ledger['summaries'].get(owner, {})
    ledger['summaries'][owner] = dict(
        turn=state.turn, urgent=sum(row.priority <= 2 and row.remaining > 0 for row in demands),
        demand=sum(row.requested for row in demands), reliable=sum(row.reliable for row in demands),
        remaining=sum(row.remaining for row in demands), sources=len(available_sources),
        dispatched=work['committed'] + (previous.get('dispatched', 0) if previous.get('turn') == state.turn else 0),
        blockers=dict(Counter(reason for key in operation.failures for reason in operation.failures[key])))
    observe('scheduler', state, owner=owner, phase=phase, shadow=False, initial_books=origins,
            remaining_books=command_books.remaining(state, owner), demand_count=len(demands),
            available_sources=len(available_sources), scheduler_cpu=process_time()-started,
            **dict(operation.work + work))
    return bool(work['committed'])


def _complete(state, owner):
    completed = state.extension[POOL]['completed']
    completed[owner] = completed.get(owner, 0) + 1


def transport_event(state, kind, row, grain, *, tick=None):
    if not enabled(state) and not shadowing(state):
        return
    if kind == 'transport_departed':
        observe('transport_departed', state, owner=row['owner'], convoy=row['id'], source=row['source'],
                target=row['target'], escorts=row['officers'], grain=grain, gold=row['cargo']['gold'],
                reserves=row['cargo']['reserves'], target_march=row['target_march'],
                channel='granary' if 'strategic' in row else 'regional' if 'regional' in row else
                'army' if row['target_march'] is not None else 'convoy' if 'convoy_relief' in row else 'ordinary')
        return
    if not enabled(state) or kind not in ('transport_arrived', 'transport_returned', 'transport_terminal'):
        return
    link = state.extension[POOL]['convoys'].pop(str(row['id']), None)
    if link is None:
        return
    tick = army_relief._calendar_tick(state) if tick is None else tick
    kind_of_target = link['kind']
    if kind_of_target == 'transshipment':
        match = transshipment._lookup(state, row['id'])
        final = match is not None and row['target'] == match[0]['target']
    elif kind_of_target == 'march':
        final = row['target_march'] == link['target']
    elif kind_of_target == 'convoy':
        final = row.get('convoy_relief', {}).get('target') == link['target']
    else:
        final = (row['target'] == link['target'] and state.cities[row['target']].owner == link['owner'])
    delivered = final and kind == 'transport_arrived'
    credited = min(grain, link['cap']) if delivered else 0
    if delivered:
        _complete(state, link['owner'])
    timely = tick <= link['deadline'] if kind_of_target in ('march', 'convoy') else tick < link['deadline']
    details = {}
    if 'current_deadline' in link:
        due = link['current_deadline']
        at_due = tick <= due if kind_of_target in ('march', 'convoy') else tick < due
        details.update(current_deadline=due, timely_current=credited if at_due else 0,
                       credit_basis='unit_receipt' if kind_of_target in ('march', 'convoy') else 'warehouse_receipt')
    observe('receipt', state, owner=link['owner'], convoy=row['id'], received=grain, credited=credited,
            unallocated=grain-credited, tick=tick, channel=link['channel'], demand_id=link['demand'],
            target_kind=kind_of_target, target=link['target'], original_deadline=link['deadline'],
            timely=min(credited, link.get('original_cap', credited)) if timely else 0,
            outcome=kind, final_target=final, **details)


def view(state):
    if not enabled(state):
        return {}
    ledger = state.extension[POOL]
    active = Counter(row['owner'] for row in logistics._pool(state)['convoys'])
    return {owner: dict(row, books=command_books.remaining(state, owner),
                        active=active[owner], completed=ledger['completed'].get(owner, 0))
            for owner, row in ledger['summaries'].items()}


def validate(state):
    if FIELD not in state.extension and POOL not in state.extension:
        return
    ledger = state.extension.get(POOL)
    version = state.extension.get(FIELD)
    recovery = version in RECOVERY_VERSIONS
    names = CONSUMPTION_FEATURES if version == CONSUMPTION else FEATURES
    fields = {'efficiency', 'phases', 'episodes', 'convoys', 'summaries', 'completed', 'support'}
    if (not enabled(state) or type(state.extension[FIELD]) is not int
            or logistics_rules.version(state) != logistics_rules.CURRENT
            or not isinstance(ledger, dict)
            or set(ledger) != fields | ({'features'} if recovery else set())
            or recovery and (not _features(ledger['features'], names) or set(ledger['features']) != names)
            or type(ledger['efficiency']) is not bool):
        raise ValueError('Transport coordination version')
    owners = state.extension['command_books']['factions']
    for name in ('phases', 'episodes', 'summaries', 'completed', 'support'):
        if not isinstance(ledger[name], dict) or not ledger[name].keys() <= owners.keys():
            raise ValueError('Transport coordination faction')
    if any(type(value) is not int or value < 0 for value in ledger['completed'].values()):
        raise ValueError('Transport coordination completion count')
    for row in ledger['support'].values():
        if (not isinstance(row, dict) or set(row) != {'turn', 'goals'}
                or type(row['turn']) is not int or not 1 <= row['turn'] <= state.turn
                or not isinstance(row['goals'], dict) or not row['goals'].keys() <= state.cities.keys()):
            raise ValueError('Transport coordination support')
        if recovery and ledger['features']['preparation']:
            for requests in row['goals'].values():
                if not isinstance(requests, dict) or len(requests) > len(state.cities) + 3:
                    raise ValueError('Transport coordination preparation count')
                for key, item in requests.items():
                    if (not isinstance(key, str) or not isinstance(item, dict)
                            or set(item) != {'kind', 'target', 'grain', 'gold', 'deadline'}
                            or item['kind'] not in PREPARATIONS
                            or item['target'] is not None and item['target'] not in state.cities
                            or any(type(item[field]) is not int or item[field] < 0
                                   for field in ('grain', 'gold', 'deadline'))
                            or not row['turn'] < item['deadline']):
                        raise ValueError('Transport coordination preparation')
        elif any(not isinstance(values, list) or len(values) != 3 or
                 any(type(value) is not int or value < 0 for value in values)
                 for values in row['goals'].values()):
            raise ValueError('Transport coordination support amount')
    for row in ledger['phases'].values():
        if not isinstance(row, dict) or not row.keys() <= PHASES.keys() or any(
                type(value) is not int or not 1 <= value <= state.turn for value in row.values()):
            raise ValueError('Transport coordination phase')
    for owner, rows in ledger['episodes'].items():
        if not isinstance(rows, dict) or len(rows) > 10_000:
            raise ValueError('Transport coordination demand count')
        for key, date in rows.items():
            if (not key.startswith(owner+'/') or len(key) > 144 or not isinstance(date, list) or len(date) != 2
                    or type(date[0]) is not int or not 1 <= date[0] <= state.turn
                    or type(date[1]) is not int or date[1] < 0):
                raise ValueError('Transport coordination demand')
    if not isinstance(ledger['convoys'], dict) or len(ledger['convoys']) > 10_000:
        raise ValueError('Transport coordination convoy count')
    convoy_fields = {'owner', 'key', 'demand', 'kind', 'target', 'deadline', 'cap', 'channel'}
    if recovery:
        convoy_fields |= {'current_deadline', 'original_cap'}
    for ident, row in ledger['convoys'].items():
        if (not ident.isdecimal() or not isinstance(row, dict)
                or set(row) != convoy_fields
                or row['owner'] not in owners or row['kind'] not in (KINDS | PREPARATIONS if recovery else KINDS)
                or row['channel'] not in CHANNELS
                or type(row['deadline']) is not int or row['deadline'] < 0
                or type(row['cap']) is not int or not 0 <= row['cap'] <= logistics.LIMIT or
                not isinstance(row['demand'], str) or not isinstance(row['key'], str) or
                (type(row['target']) is not int if row['kind'] in ('march', 'convoy', 'transshipment')
                 else row['target'] not in state.cities)):
            raise ValueError('Transport coordination dispatch')
        if recovery and (type(row['current_deadline']) is not int or row['current_deadline'] < 0
                         or type(row['original_cap']) is not int or not 0 <= row['original_cap'] <= row['cap']):
            raise ValueError('Transport coordination demand deadline')
    fields = {'turn', 'urgent', 'demand', 'reliable', 'remaining', 'sources', 'dispatched'}
    for row in ledger['summaries'].values():
        if (not isinstance(row, dict) or set(row) != fields | {'blockers'} or
                any(type(row[key]) is not int or row[key] < 0 for key in fields) or row['turn'] > state.turn
                or not isinstance(row['blockers'], dict) or len(row['blockers']) > 100
                or any(type(count) is not int or count < 1 for count in row['blockers'].values())):
            raise ValueError('Transport coordination summary')
