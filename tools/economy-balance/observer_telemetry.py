"""Read-only receipts for the balance runner. Nothing here is loaded by the game."""
from collections import Counter, defaultdict
import csv
from heapq import heappop, heappush
import json

from common import _csv_cell
from remake import city_economy as economy, grain_units, historical_campaigns, logistics
from remake.route_hazards import evaluate_leg, route_allowed
from remake.route_network import effective

SCHEMA = 'tk2-observer-v21'
FILES = {
    'shortages': ('owner city required paid missing stationed_before reserves_before active_lost reserve_lost '
                  'other_city_stock other_stock reserve_surplus legal_route_surplus '
                  'timely_new_shipment headroom_basis'),
    'supply-requests': ('request_id channel owner target source requested_grain requested_gold '
                        'deadline_turn route_eligible_expected_grain can_arrive_before_zero_grain candidates '
                        'result reason convoy_ids delivery_allocations'),
    'convoys': ('convoy_id owner source target original_target target_march stage reason '
                'dispatched_date expected_arrival_date expected_arrival_turn expected_grain '
                'actual_arrival_date actual_route_date actual_grain grain_loaded cargo_reserves officers route'),
    'troop-flows': 'owner source target kind active reserves count officers reference',
    'battles': ('battle_id attacker defender source target outcome deaths surrendered days rations '
                'grain_burned'),
    'route-changes': ('unit_kind unit_id owner source old_target new_target reason status '
                      'old_remaining_days new_days old_remaining_grain new_grain old_path new_path'),
    'war-quotes': ('stage plan_key owner source target mode officers troops grain gold '
                   'quote_days outcome reasons required_grain required_gold budget'),
    'war-quote-groups': 'plan_key owner target evaluations passed blocked reasons',
    'war-plans': 'plan_id owner target created_turn planned_orders stage',
    'action-capacity': ('owner status no_action_streak qualifies reasons actions forecast_runway '
                        'actual_shortage_grain remaining_books'),
}
CITY_FIELDS = (
    'stationed_active_troops', 'city_registered_active_troops', 'city_reserve_troops',
    'sustainable_stationed_troops', 'stationed_troops_above_sustainable',
)
AIS = ('attack', 'transfer', 'recruit_officer', 'staff_recruit', 'hire_staff',
       'recruit_soldiers', 'persuade_officer')
SUPPLY_FAILURES = frozenset({'shortage', 'ration_shortage'})


def config(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data) != {'schema', 'reserve_months', 'postbattle_turns', 'action_capacity'} or data['schema'] != SCHEMA:
        raise ValueError('Unknown observer configuration')
    levels = data['reserve_months']
    if levels != [1, 3, 6] or type(data['postbattle_turns']) is not int or data['postbattle_turns'] < 0:
        raise ValueError('Invalid reserve horizons or postbattle window')
    capacity = data['action_capacity']
    flags = ('consider_blocked_offensive', 'consider_incoming_enemy')
    limits = ('report_streak_at', 'shortage_warning_turns', 'minimum_grain_gap', 'reserve_rest_months')
    if (set(capacity) != set(flags + limits)
            or any(type(capacity[key]) is not bool for key in flags)
            or any(type(capacity[key]) is not int or capacity[key] < 1 for key in limits)):
        raise ValueError('Invalid action-capacity criteria')
    return data


def clock_date(state):
    return [state.year, state.month, state.day]


def tick_date(game, day):
    start = game.catalog.data
    absolute = start['start_year'] * 360 + (start['start_month'] - 1) * 30 + day
    year, rest = divmod(absolute, 360)
    month, date = divmod(rest, 30)
    return [year, month + 1, date + 1]


def troop_manifest(state, ids):
    return {str(ident): state.officers[ident].troops for ident in ids if ident in state.officers}


def sustainable_troops(game, state, city, active, production, residents, wages):
    """Invert the current garrison rule at fixed population/reserves/wages."""
    available = production - residents - wages
    under = (city.id, state.year, state.month)
    garrison = economy.garrison_grain_cost
    if garrison(game.catalog.data, *under, 0, city.reserves) > available:
        return 0, active
    low, high = 0, max(1, available * grain_units.denominator() * 2, active + 1)
    while low < high:
        probe = (low + high + 1) // 2
        if garrison(game.catalog.data, *under, probe, city.reserves) <= available:
            low = probe
        else:
            high = probe - 1
    return low, max(0, active - low)


def nearest_legal_days(state, incoming, target, permissions):
    """One reverse search for all candidate donors of the same route policy."""
    distances = {}
    queue = [(0, target)]
    while queue:
        days, here = heappop(queue)
        if here in distances:
            continue
        distances[here] = days
        for source, duration in incoming.get(here, ()):
            if source not in distances and permissions[state.cities[source].owner]:
                heappush(queue, (days + duration, source))
    return distances


class StockSnapshot:
    """Shared pre-settlement stocks and directed travel graphs for one ration installment."""
    def __init__(self, game, state, fixed, absent, month_levels):
        self.game, self.state = game, state
        self.fixed = fixed
        self.by_owner = defaultdict(dict)
        self.room = {}
        self.graphs = {}
        self.transit = {}
        self.route_rows = None
        self.levels = month_levels
        pool = state.extension.get('logistics', {})
        busy = {row['source'] for row in pool.get('convoys', ())}
        for key, city in state.cities.items():
            if key not in fixed:
                continue
            self.by_owner[city.owner][key] = city.grain
            ledger = pool.get('cities', {}).get(key)
            if not ledger or key in busy or ledger['last_dispatch_turn'] == state.turn:
                continue
            policy = ledger['policy']
            if (not policy['max_officers'] or not policy['max_grain']
                    or historical_campaigns.hold_longyou_garrison(game, state, city)):
                continue
            ids = [ident for ident in city.roster.officer_ids if ident not in absent
                   and state.officers[ident].alive and state.officers[ident].faction_id == city.owner]
            if len(ids) <= policy['reserve_officers']:
                continue
            from remake import domestic
            appointed = domestic.appointments(state, city.owner)
            officers = {appointed.get('civil'), appointed.get('military')}
            if not any(ident not in officers and state.officers[ident].health > 0
                       and pool['receipts'].get(str(ident), 0) <= state.turn for ident in ids):
                continue
            hand = min(policy['max_grain'], max(0, city.grain - policy['reserve_grain']))
            if hand:
                self.room[key] = (hand, (policy['allow_sea'], policy['allow_special']))

    def graph(self, permissions):
        if permissions not in self.graphs:
            game, state = self.game, self.state
            data = game.catalog.data
            policy = dict(zip(('allow_sea', 'allow_special'), permissions))
            if self.route_rows is None:
                discovered = set(state.extension['travel']['discovered'])
                self.route_rows = effective(data['travel_routes'] + [
                    row for row in data.get('exploration_routes', ()) if row['id'] in discovered
                ], state.cities, state.year, state.month)
            incoming = defaultdict(list)
            for raw in self.route_rows:
                if not logistics._permitted_route(game, policy, raw):
                    continue
                a, b = raw['from'], raw['to']
                # Dated city founding can leave a raw route on the map before
                # its endpoint exists in the campaign state.
                if a not in state.cities or b not in state.cities:
                    continue
                for source, target in ((a, b), (b, a)):
                    if route_allowed(data, raw, source, target):
                        leg = evaluate_leg(data, raw, source, target, state.month)
                        if not logistics._dangerous({'routes': [leg]}, policy):
                            incoming[target].append((source, leg['days']))
            self.graphs[permissions] = incoming
        return self.graphs[permissions]

    def other(self, city):
        stocks = {key: stock for key, stock in self.by_owner[city.owner].items() if key != city.id}
        surplus, legal = dict.fromkeys(map(str, self.levels), 0), dict.fromkeys(map(str, self.levels), 0)
        routes = {}
        if city.owner not in self.transit:
            self.transit[city.owner] = {
                owner: historical_campaigns.transit_allowed(self.state, city.owner, owner)
                for owner in self.by_owner.keys() | {'neutral'}
            }
        transit = self.transit[city.owner]
        for key, stock in stocks.items():
            room, policy = self.room.get(key, (0, None))
            excess = {str(m): max(0, stock - m * self.fixed[key]) for m in self.levels}
            for level, amount in excess.items():
                surplus[level] += amount
            if room and excess[str(self.levels[0])]:
                if policy not in routes:
                    routes[policy] = nearest_legal_days(self.state, self.graph(policy), city.id, transit)
                if key in routes[policy]:
                    for level, amount in excess.items():
                        legal[level] += min(room, amount)
        return dict(other_city_stock=stocks, other_stock=sum(stocks.values()),
                    reserve_surplus=surplus, legal_route_surplus=legal, timely_new_shipment=0,
                    headroom_basis='pre_settlement_route_eligible_gross')


class Telemetry:
    def __init__(self, game, path, settings, stack):
        self.game, self.settings = game, settings
        self.current = []
        self.writers = {}
        self.counts = dict.fromkeys(FILES, 0)
        self.actions = defaultdict(Counter)
        self.blockers = defaultdict(Counter)
        self.feasible_offense = set()
        self.shortages = Counter()
        self.outlooks = {}
        self.streak = Counter()
        self.dispatched = {}
        self.convoy_hunger = set()
        self.request_stack = []
        self.month_rollover = False
        self.request_number = 0
        path.mkdir(parents=True, exist_ok=True)
        for name, columns in FILES.items():
            handle = stack.enter_context((path / (name + '.csv')).open('w', encoding='utf-8', newline=''))
            keys = ['turn', 'year', 'month', 'day', *columns.split()]
            writer = csv.DictWriter(handle, fieldnames=keys, lineterminator='\n')
            writer.writeheader()
            self.writers[name] = writer

    def row(self, table, state, **data):
        self.current.append((table, dict(turn=state.turn, year=state.year, month=state.month,
                                         day=state.day, **data)))

    def action(self, owner, name):
        self.actions[owner][name] += 1

    def troops(self, state, owner, kind, source=None, target=None, *, active=0, reserves=0,
               count=None, officers=None, reference=None):
        if count is None:
            count = active + reserves
        if count or officers:
            self.row('troop-flows', state, owner=owner, kind=kind, source=source, target=target,
                     active=active, reserves=reserves, count=count, officers=officers, reference=reference)

    def receipt(self, key, state, data):
        self.row('battles', state, **data)
        for owner in key:
            self.action(owner, 'battle')

    def event(self, state, receipt):
        kind, details = receipt['kind'], receipt['details']
        if kind == 'grain_traded':
            owner = receipt['factions'][0]
            if details['direction'] == 'buy' and details['grain']:
                if details.get('emergency'):
                    self.action(owner, 'emergency_grain_purchase')
                elif 'battle_id' not in details:
                    self.action(owner, 'city_grain_purchase')
        elif kind == 'city_developed' and details['gain'] > 0:
            self.action(receipt['factions'][0], 'develop_' + details['development'])
        elif kind == 'city_captured':
            self.action(receipt['factions'][0], 'city_captured')

    def transport(self, state, kind, convoy, *, lost=0, reason='outbound', amounts=None):
        if kind == 'transport_weather':
            risk = next(row for row in reversed(convoy['journeys'][-1]['risks']) if row['applied'])
            reserve_loss = risk['before']['cargo'] - risk['after']['cargo']
            self.troops(state, convoy['owner'], 'convoy_route_hazard_deaths', convoy['source'], convoy['target'],
                        active=lost - reserve_loss, reserves=reserve_loss, reference=convoy['id'])
            return
        if kind not in ('transport_departed', 'transport_arrived', 'transport_returned'):
            return
        from remake import march_supply

        ident = convoy['id']
        journey = convoy['journeys'][-1]
        quote = journey['quote']
        actual_route_date = None
        origin, target = convoy['source'], convoy['target']
        if kind == 'transport_departed':
            estimated = convoy['cargo']['grain']
            if state.extension.get('logistics_rules_version') == 2:
                estimated = logistics.projected_grain(self.game, quote, estimated)
            self.dispatched[ident] = (clock_date(state), journey['arrival_turn'],
                                      tick_date(self.game, (state.turn - 1) * 10 + quote['days']), estimated)
            stage, actual_grain = 'departed', None
            self.troops(state, convoy['owner'], 'convoy_departed', origin, target,
                        active=sum(journey['departure_troops'].values()), reserves=convoy['cargo']['reserves'],
                        officers=journey['departure_troops'], reference=ident)
        elif kind == 'transport_arrived':
            stage, actual_grain = 'delivered', amounts['grain']
            delivered_tick = march_supply._completion_tick(journey['supply'], quote['days'])
            ledger = convoy['cargo_ledger']
            if convoy['target_march'] is not None and ledger and ledger[-1]['kind'] == 'army_supply':
                delivered_tick = ledger[-1]['day']
                target = ledger[-1]['reference']['city']
            if delivered_tick is not None:
                actual_route_date = tick_date(self.game, delivered_tick)
            if actual_grain:
                self.action(convoy['owner'], 'grant_grain')
            if convoy['target_march'] is None:
                self.troops(state, convoy['owner'], 'convoy_reserves_delivered', origin, target,
                            reserves=amounts['reserves'], reference=ident)
        elif reason in ('returned', 'no_friendly_city'):
            stage, actual_grain = ('docked' if reason == 'returned' else 'abandoned'), None
            completed = march_supply._completion_tick(journey['supply'], quote['days'])
            if completed is not None:
                actual_route_date = tick_date(self.game, completed)
        else:
            stage, actual_grain = 'return_ordered', None
        dispatched, eta, physical_eta, estimate = self.dispatched.get(ident, (None,) * 4)
        self.row('convoys', state, convoy_id=ident, owner=convoy['owner'], source=origin, target=target,
                 original_target=convoy['original_target'], target_march=convoy['target_march'],
                 stage=stage, reason=reason, dispatched_date=dispatched, expected_arrival_date=physical_eta,
                 expected_arrival_turn=eta, expected_grain=estimate,
                 actual_arrival_date=clock_date(state) if stage == 'delivered' else None,
                 actual_route_date=actual_route_date, actual_grain=actual_grain,
                 grain_loaded=convoy['initial_cargo']['grain'], cargo_reserves=convoy['cargo']['reserves'],
                 officers=troop_manifest(state, convoy['officers']), route=quote['path'])
        if lost:
            self.troops(state, convoy['owner'], 'convoy_abandoned_reserve_deaths', origin, target,
                        reserves=lost, reference=ident)
        if stage in ('abandoned', 'docked'):
            self.dispatched.pop(ident, None)

    def roster_moves(self, previous, current):
        old = {ident: (key, city.owner) for key, city in previous.cities.items() for ident in city.roster.officer_ids}
        batches = defaultdict(dict)
        for key, city in current.cities.items():
            for ident in city.roster.officer_ids:
                start = old.get(ident)
                if start is None or start == (key, city.owner):
                    continue
                origin, previous_owner = start
                kind = 'officer_city_change' if previous_owner == city.owner else 'officer_allegiance_change'
                batches[city.owner, origin, key, kind][str(ident)] = current.officers[ident].troops
        for (owner, source, target, kind), people in batches.items():
            self.troops(current, owner, kind, source, target, active=sum(people.values()), officers=people)

    def finish_turn(self, state):
        from remake import command_books
        owners = {city.owner for city in state.cities.values()} - {'neutral'}
        travel = state.extension.get('travel', {}).get('marches', [])
        hostile = {row['target'] for row in travel if row['kind'] == 'attack' and row.get('status') != 'returning'}
        attacked = {state.cities[key].owner for key in hostile if key in state.cities}
        outbound = {row['owner'] for row in travel if row.get('status') == 'outbound'}
        inbound = {row['owner'] for row in state.extension.get('logistics', {}).get('convoys', ())
                   if row['status'] == 'outbound'}
        config = self.settings['action_capacity']
        holdings = defaultdict(list)
        for city in state.cities.values():
            holdings[city.owner].append(city)
        for owner in sorted(owners):
            runway, warned = self.outlooks.get(owner, (None, None))
            reasons = []
            shortage = self.shortages[owner]
            if shortage >= config['minimum_grain_gap']:
                reasons.append('actual_shortage')
            if warned is not None and warned <= config['shortage_warning_turns']:
                reasons.append('forecast_shortage')
            if config['consider_incoming_enemy'] and owner in attacked:
                reasons.append('incoming_hostile_column')
            if (config['consider_blocked_offensive'] and self.blockers[owner]
                    and owner not in self.feasible_offense):
                reasons.extend(sorted(self.blockers[owner]))
            orders = state.extension.get('ai_strategy', {}).get(owner, {}).get('orders', ())
            committed = any(order['departure_turn'] >= state.turn and order['march_id'] is None for order in orders)
            productive = bool(self.actions[owner]) or owner in outbound or owner in inbound or committed
            resting = (runway is not None and runway > config['shortage_warning_turns'] and not shortage
                       and owner not in attacked and (warned is None or warned > config['shortage_warning_turns']))
            holding = holdings[owner]
            building_reserves = bool(holding) and any(
                city.grain < self.game.city_fixed.get(city.id, 0) * config['reserve_rest_months']
                for city in holding) and not any(reason in ('actual_shortage', 'forecast_shortage',
                                                           'incoming_hostile_column') for reason in reasons)
            if productive:
                status = 'acting_or_committed'
            elif not reasons:
                status = 'peace_or_no_unmet_need'
            elif resting or building_reserves:
                status = 'resting_or_building_reserves'
            else:
                status = 'blocked'
            self.streak[owner] = self.streak[owner] + 1 if status == 'blocked' else 0
            self.row('action-capacity', state, owner=owner, status=status,
                     no_action_streak=self.streak[owner], qualifies=self.streak[owner] >= config['report_streak_at'],
                     reasons=reasons, actions=dict(self.actions[owner]), forecast_runway=runway,
                     actual_shortage_grain=shortage, remaining_books=command_books.remaining(state, owner))
        for owner in self.streak.keys() - owners:
            del self.streak[owner]
        for table, row in self.current:
            keys = self.writers[table].fieldnames
            extra = row.keys() - keys
            if extra:
                raise ValueError(f'Unexpected {table} columns: {sorted(extra)}')
            self.writers[table].writerow({key: _csv_cell(row.get(key)) for key in keys})
            self.counts[table] += 1
        self.current.clear()
        self.actions.clear()
        self.blockers.clear()
        self.feasible_offense.clear()
        self.shortages.clear()
        self.outlooks.clear()
