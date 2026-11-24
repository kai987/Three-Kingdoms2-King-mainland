"""Observe committed engine receipts and the return values of actual AI evaluations."""
from collections import Counter
from contextlib import contextmanager
from functools import wraps
from unittest.mock import patch

from observer_telemetry import SUPPLY_FAILURES, troop_manifest
from remake import (battle_reinforcements, city_economy, command_books, diplomacy, domestic, grain_relief,
                    logistics, march_supply, strategic_ai, transfer_supply)
from remake.errors import GameError

# The baseline checkout has no V2 military-budget module or weighted route ledger.
try:
    from remake import logistics_rules, military_budget
except ImportError:
    logistics_rules = military_budget = None


def quote_grain(game, state, quote, troops, officers, reserves=0):
    if logistics_rules is None or logistics_rules.version(state) != logistics_rules.CURRENT:
        return march_supply.cost(troops, officers, quote['days'], reserves)
    return march_supply.quote_supply(quote, troops, officers, reserves, game=game,
                                     version=logistics_rules.CURRENT)


def budget_reasons(game, state, city, plan, return_routes=()):
    """Attribute rejected V2 budgets to the unaffordable increments of the real quote."""
    if plan['can_depart']:
        return []
    reasons = []
    if not plan['safe_return']:
        reasons.append('return_route_restricted' if return_routes else 'return_route_unreachable')
    stock = city.grain
    for name, amount in (('outbound_grain', plan['outbound']), ('battle_grain', plan['battle']),
                         ('return_grain', plan['returning'] or 0), ('contingency_grain', plan['safety'])):
        if amount and stock < amount:
            reasons.append(name)
        stock -= amount
    ration = city_economy.turn_rations(plan['home'], (state.day - 1) // 10 + 1)
    if ration and stock < ration:
        reasons.append('garrison_grain')
    # These are the same two funding branches as sortie(): the immediate cash
    # in the city and the full month after expected ordinary city income.
    expected_grain = city_economy.monthly_income(game, city.id, state)['grain']
    if city.grain + expected_grain < plan['total']:
        funded = city.grain + expected_grain - plan['immediate']
        if plan['home'] and funded < plan['home'] and 'garrison_grain' not in reasons:
            reasons.append('garrison_grain')
        if plan['replacement_grain'] and funded - plan['home'] < plan['replacement_grain']:
            reasons.append('replacement_grain')
    if city.gold < plan['required_gold']:
        reasons.append('replacement_gold' if plan['replacement_gold'] else 'other_gold_obligation')
    return reasons or ['other_budget_limit']


def leg_remaining(game, state, journey, troops, count, reserves=0):
    quote = journey['quote']
    progress = journey['supply']['route_days']
    days = max(0, quote['days'] - progress)
    if logistics_rules is None or logistics_rules.version(state) != logistics_rules.CURRENT:
        return days, march_supply.cost(troops, count, days, reserves)
    parts = logistics_rules.plan(quote, game.catalog.data['travel_rules'])
    weight = logistics_rules.weight(parts, progress, days)
    cost = logistics_rules.ceil_div((troops + 100 * count + reserves) * weight,
                                   march_supply.denominator() * logistics_rules.RATION_SCALE)
    return days, cost


class Hooks:
    def __init__(self, tracker, stack, campaign_class):
        self.t = tracker
        self.game = tracker.game
        self.stack = stack
        self.pending_routes = {}
        self.attack = []
        self.plans = {}
        self.engine_plans = {}
        self.war_depth = 0
        self.aborted = set()
        self.first_return_cause = {}
        self.transfer_call = []
        for obj, handlers in (
            (logistics, {'dispatch': self.dispatch, 'dispatch_ai_supply': self.ai_supply,
                         '_safe_quote': self.safe_supply_route, '_begin_journey': self.convoy_reroute,
                         '_return': self.convoy_return}),
            (grain_relief, {'dispatch': self.emergency, 'forecasts': self.forecast, '_deliveries': self.deliveries,
                            'recovery': self.recovery}),
            (diplomacy, {'_request_grain': self.allied_request}),
            (domestic, {'add_reserves': self.reserves}),
            (strategic_ai.StrategicAI, {'plan': self.plan, 'attack_option': self.attack_option, 'safe': self.safe_attack,
                                       'provisioned': self.provisioned, 'war_budget': self.war_budget,
                                       'depart': self.depart}),
            (transfer_supply, {'detour': self.transfer_detour}),
            (campaign_class, {'_monthly_calendar': self.monthly, '_recruit': self.manual_recruit,
                              '_queue_march': self.depart_march, '_arrivals': self.arrivals,
                              '_apply_march_risks': self.weather, '_resolve_supply_retreats': self.march_reroute}),
            (battle_reinforcements, {'advance_returns': self.reinforcement_returns}),
        ):
            for name, handler in handlers.items():
                if hasattr(obj, name):
                    self.hook(obj, name, handler)

    def hook(self, obj, name, handler):
        real = getattr(obj, name)

        @wraps(real)
        def observed(*args, **kwargs):
            return handler(real, *args, **kwargs)

        self.stack.enter_context(patch.object(obj, name, observed))

    @contextmanager
    def request(self, channel, owner, target=None):
        request = dict(channel=channel, owner=owner, target=target, successful=[], errors=[],
                       evaluated=[], forecasts={}, deliveries=None)
        self.t.request_stack.append(request)
        try:
            yield request
        finally:
            self.t.request_stack.pop()

    def write_request(self, state, request, *, target, grain, gold=None, deadline=None,
                      source=None, candidates=None, result, reason=None, ids=(),
                      routed=None, timely=None, allocations=None):
        self.t.request_number += 1
        self.t.row('supply-requests', state, request_id=self.t.request_number,
                   channel=request['channel'], owner=request['owner'], target=target, source=source,
                   requested_grain=grain, requested_gold=gold, deadline_turn=deadline,
                   route_eligible_expected_grain=routed, can_arrive_before_zero_grain=timely,
                   candidates=candidates, result=result, reason=reason, convoy_ids=list(ids),
                   delivery_allocations=allocations)

    def dispatch(self, real, game, state, payload, owner, **kwargs):
        parent = self.t.request_stack[-1] if self.t.request_stack else None
        target, source = payload.get('target'), payload.get('source')
        cargo = payload.get('cargo', {})
        try:
            convoy = real(game, state, payload, owner, **kwargs)
        except GameError as error:
            if parent is not None:
                parent['errors'].append((target, source, str(error)))
            else:
                self.write_request(state, {'channel': 'individual_convoy', 'owner': owner},
                                   target=target, source=source, grain=cargo.get('grain'),
                                   gold=cargo.get('gold'), result='failed', reason=str(error))
            raise
        if parent is not None:
            parent['successful'].append((target, source, convoy['id']))
        else:
            self.write_request(state, {'channel': 'individual_convoy', 'owner': owner},
                               target=target, source=source, grain=cargo['grain'], gold=cargo['gold'],
                               result='dispatched', ids=[convoy['id']])
        if cargo['grain']:
            self.t.action(owner, 'grain_shipment')
        return convoy

    def forecast(self, real, game, state, owner, **kwargs):
        result = real(game, state, owner, **kwargs)
        if self.t.request_stack:
            request = self.t.request_stack[-1]
            if request['channel'] == 'city_emergency' and request['owner'] == owner and not request['forecasts']:
                request['forecasts'] = result
        return result

    def deliveries(self, real, game, state, owner, projections, targets):
        result = real(game, state, owner, projections, targets)
        if self.t.request_stack and self.t.request_stack[-1]['channel'] == 'city_emergency':
            self.t.request_stack[-1]['deliveries'] = result
        return result

    def emergency(self, real, game, state, owner):
        with self.request('city_emergency', owner) as request:
            result = real(game, state, owner)
        projections = request['forecasts']
        deliveries = request['deliveries']
        for target in grain_relief._shortages(projections):
            forecast = projections[target]
            issued = [row for row in request['successful'] if row[0] == target]
            errors = [reason for key, _, reason in request['errors'] if key == target]
            legs = deliveries.get(target, ()) if deliveries is not None else ()
            donors = [dict(source=leg[3], route_mode=leg[5], days=leg[1],
                           arrival_turn=state.turn + leg[0], expected_capacity=-leg[2],
                           timely=leg[0] < forecast.zero_in) for leg in legs]
            # A target that is already at zero cannot be rescued before its
            # first exhaustion. The same request may still receive a late load.
            routed = sum(row['expected_capacity'] for row in donors) if deliveries is not None else 'not_collected'
            timely = (sum(row['expected_capacity'] for row in donors if row['timely'])
                      if deliveries is not None else 0 if forecast.zero_in == 0 else 'not_collected')
            need = max((gap for _, gap in forecast.gaps), default=0)
            if not need and not issued:
                continue  # Forecast methods also supply informational empty-granary markers.
            if issued:
                outcome, reason = 'dispatched', None
            elif errors:
                outcome, reason = 'failed', errors
            elif not command_books.can_spend(state, owner, 'dispatch_transport'):
                outcome, reason = 'failed', 'no_command_books_remaining'
            elif not donors:
                outcome = 'failed'
                reason = ('no_eligible_routed_donor' if deliveries is not None else
                          'no_available_delivery_or_civil_officer')
            else:
                outcome, reason = 'failed', 'no_load_scheduled'
            self.write_request(state, request, target=target, grain=need,
                               deadline=state.turn + forecast.zero_in, candidates=donors, routed=routed, timely=timely,
                               source=issued[0][1] if len(issued) == 1 else None,
                               result=outcome, reason=reason, ids=[row[2] for row in issued])
        return result

    def ai_supply(self, real, game, state, target, gold_goal, grain_goal, **kwargs):
        owner = target.owner
        pool = state.extension.get('logistics')
        need = logistics.supply_shortages(state, target, gold_goal, grain_goal) if pool else (gold_goal, grain_goal)
        if not any(need):
            return real(game, state, target, gold_goal, grain_goal, **kwargs)
        eligible = (pool is not None and state.phase == 'ai' and owner != state.player
                    and command_books.can_spend(state, owner, 'dispatch_transport'))
        with self.request('strategic_supply', owner, target.id) as request:
            result = real(game, state, target, gold_goal, grain_goal, **kwargs)
        routes = request['evaluated']
        max_turns = kwargs.get('max_turns')
        if result:
            reason = None
        elif not eligible:
            reason = 'dispatch_unavailable_or_no_command_books'
        elif request['errors']:
            reason = [error for _, _, error in request['errors']]
        elif routes and not any(row['turns'] is not None for row in routes):
            reason = 'no_usable_route'
        elif max_turns is not None and routes and all(row['turns'] is None or row['turns'] > max_turns for row in routes):
            reason = 'delivery_deadline'
        elif not routes:
            reason = 'no_eligible_donor'
        else:
            reason = 'no_fundable_delivery'
        issued = request['successful']
        self.write_request(state, request, target=target.id, grain=need[1], gold=need[0],
                           deadline=state.turn + max_turns if max_turns is not None else None,
                           candidates=routes, source=issued[0][1] if issued else None,
                           result='dispatched' if result else 'failed', reason=reason,
                           ids=[row[2] for row in issued])
        return result

    def allied_request(self, real, game, state, owner, ally, city, amount):
        before = {key: donor.grain for key, donor in state.cities.items() if donor.owner == ally}
        result = real(game, state, owner, ally, city, amount)
        success, _, details = result
        allocations = {key: grain - state.cities[key].grain for key, grain in before.items()
                       if grain != state.cities[key].grain}
        if sum(allocations.values()) != (amount if success else 0):
            raise ValueError('Allied grain transfer disagrees with the immediate engine receipt')
        self.write_request(state, {'channel': 'allied_grain', 'owner': owner},
                           target=city.id, grain=amount, candidates={'ally': ally},
                           source=next(iter(allocations)) if len(allocations) == 1 else None,
                           result='delivered_immediately' if success else 'refused',
                           reason=details['aid_reason'], allocations=allocations)
        if success:
            self.t.action(owner, 'allied_grain_received')
        return result

    def safe_supply_route(self, real, game, state, source, target, policy, **kwargs):
        result = real(game, state, source, target, policy, **kwargs)
        if self.t.request_stack:
            request = self.t.request_stack[-1]
            if request['channel'] == 'strategic_supply' and request['target'] == target.id:
                request['evaluated'].append(dict(source=source.id, turns=result[1]['turns'] if result else None,
                                                 days=result[1]['days'] if result else None))
        return result

    def recovery(self, real, game, state, owner, *args, **kwargs):
        result = real(game, state, owner, *args, **kwargs)
        runway, warnings = result
        self.t.outlooks[owner] = runway, min((row.zero_in for row in warnings.values()), default=None)
        return result

    def monthly(self, real, game, *args, **kwargs):
        self.t.month_rollover = True
        try:
            return real(game, *args, **kwargs)
        finally:
            self.t.month_rollover = False

    def reserves(self, real, game, state, city, *args, **kwargs):
        before = city.reserves
        value = real(game, state, city, *args, **kwargs)
        if self.t.month_rollover and kwargs.get('recruited'):
            self.t.troops(state, city.owner, 'natural_monthly_reserves', target=city.id,
                          reserves=city.reserves - before)
        return value

    def manual_recruit(self, real, game, state, payload):
        city = state.cities.get(payload.get('city'))
        before = city.reserves if city else 0
        value = real(game, state, payload)
        self.t.troops(state, city.owner, 'manual_recruitment', target=city.id, reserves=city.reserves - before)
        return value

    def transfer_detour(self, real, game, state, source, target, ids, mode, primary):
        alternative = real(game, state, source, target, ids, mode, primary)
        if self.transfer_call:
            self.transfer_call[-1].append((primary, alternative))
        return alternative

    def depart_march(self, real, game, state, source, target, ids, kind, mode='fastest', **kwargs):
        trace = []
        self.transfer_call.append(trace)
        try:
            value = real(game, state, source, target, ids, kind, mode, **kwargs)
        except GameError:
            if trace and trace[-1][1] is None:
                self.route(state, 'march', None, source.owner, source.id, target.id, target.id,
                           'insufficient_supply_for_detour', 'no_route', trace[-1][0], None, ids)
            raise
        finally:
            self.transfer_call.pop()
        row = state.extension['travel']['marches'][-1]
        if kind == 'transfer':
            self.t.troops(state, source.owner, 'transfer_departed', source.id, target.id,
                          active=sum(row['departure_troops'].values()), officers=row['departure_troops'],
                          reference=row['id'])
        self.t.action(source.owner, kind + '_dispatched')
        if trace and trace[-1][1] and trace[-1][0] != trace[-1][1]:
            self.route(state, 'march', row['id'], source.owner, source.id, target.id, target.id,
                       'insufficient_checkpoint_supply', 'rerouted', *trace[-1], ids)
        return value

    def route(self, state, kind, ident, owner, source, old_target, new_target, reason, status,
              old, new, ids, *, supply=None, reserves=0):
        troops = sum(troop_manifest(state, ids).values())
        if old and supply:
            old_days, old_grain = leg_remaining(self.game, state, dict(quote=old, supply=supply),
                                                troops, len(ids), reserves)
        else:
            old_days = old['days'] if old else None
            old_grain = quote_grain(self.game, state, old, troops, len(ids), reserves) if old else None
        self.t.row('route-changes', state, unit_kind=kind, unit_id=ident, owner=owner, source=source,
                   old_target=old_target, new_target=new_target, reason=reason, status=status,
                   old_remaining_days=old_days, new_days=new['days'] if new else None,
                   old_remaining_grain=old_grain,
                   new_grain=quote_grain(self.game, state, new, troops, len(ids), reserves) if new else None,
                   old_path=old['path'] if old else None, new_path=new['path'] if new else None)
        if kind == 'march' and ident is not None and status == 'rerouted':
            self.pending_routes[kind, ident] = (reason, new_target)

    def convoy_reroute(self, real, game, state, row, here, target, mode, quote, *, status, reason):
        previous, old_target = row['journeys'][-1], row['target']
        result = real(game, state, row, here, target, mode, quote, status=status, reason=reason)
        if reason != 'escort_return':
            self.route(state, 'convoy', row['id'], row['owner'], here, old_target, target,
                       reason, 'rerouted' if result else row['reason'], previous['quote'], quote,
                       row['officers'], supply=previous['supply'], reserves=row['cargo']['reserves'])
        return result

    def convoy_return(self, real, game, state, row, reason):
        previous, old_target = row['journeys'][-1], row['target']
        ident = row['id']
        supply = previous['supply']
        hungry = (reason in SUPPLY_FAILURES or reason == 'retreat'
                  and (ident, supply['start_tick']) in self.t.convoy_hunger
                  and row['reason'] not in ('route_blocked', 'target_changed', 'army_missing'))
        result = real(game, state, row, reason)
        returned = row['status'] == 'returning' or row not in state.extension['logistics']['convoys']
        if not row['delivery_done'] and returned:
            first = self.first_return_cause.setdefault(ident, 'shortage' if hungry else reason)
            if hungry and ident not in self.aborted:
                self.aborted.add(ident)
                status = 'aborted_for_supply' if first == 'shortage' else 'return_interrupted_for_supply'
                self.route(state, 'convoy', ident, row['owner'], previous['source'], old_target,
                           row['target'], reason, status, previous['quote'], None,
                           row['officers'], supply=supply, reserves=row['cargo']['reserves'])
        return result

    def march_reroute(self, real, game, state):
        columns = state.extension['travel']['marches']
        marked = [(row, row['quote'], row['supply'], row['target'], row['reason'])
                  for row in columns if row['supply']['retreat_requested']]
        result = real(game, state)
        live = {row['id'] for row in columns}
        for row, old, supply, target, old_reason in marked:
            if row['id'] not in live:
                self.route(state, 'march', row['id'], row['owner'], old['path'][0], target, None,
                           old_reason, 'immediate_dock', old, None, row['officers'], supply=supply)
            elif row['quote'] is not old:
                self.route(state, 'march', row['id'], row['owner'], row['quote']['path'][0], target,
                           row['target'], row['reason'], 'rerouted', old, row['quote'],
                           row['officers'], supply=supply)
            elif row['reason'] == 'no_return_route' and old_reason != row['reason']:
                self.route(state, 'march', row['id'], row['owner'], old['path'][0], target, None,
                           old_reason, 'no_return_route', old, None, row['officers'], supply=supply)
        return result

    def arrivals(self, real, game, state, payload):
        marches = state.extension['travel']['marches']
        pending = {row['id']: row for row in marches if ('march', row['id']) in self.pending_routes}
        value = real(game, state, payload)
        live = {row['id'] for row in state.extension['travel']['marches']}
        for ident, row in pending.items():
            if ident in live:
                continue
            reason, destination = self.pending_routes.pop(('march', ident))
            arrived = any(ident in state.cities[destination].roster.officer_ids for ident in row['officers'])
            self.route(state, 'march', ident, row['owner'], row['source'], destination, destination,
                       reason, 'arrived' if arrived else 'closed_without_docking', None, None, ())
        return value

    def weather(self, real, game, state, row):
        before = state.soldiers['lost']
        result = real(game, state, row)
        self.t.troops(state, row['owner'], 'march_route_hazard_deaths', row['source'], row['target'],
                      active=state.soldiers['lost'] - before, reference=row['id'])
        return result

    def reinforcement_returns(self, real, game, state):
        returning = state.extension.get(battle_reinforcements.RETURNS, ())
        people = [(row, troop_manifest(state, row['officers'])) for row in returning if row.get('rations')]
        result = real(game, state)
        for row, before in people:
            loss = sum(before.values()) - sum(troop_manifest(state, row['officers']).values())
            self.t.troops(state, row['owner'], 'reinforcement_return_hunger_deaths',
                          row['target'], row['source'], active=loss)
        return result

    def attack_option(self, real, ai, city, target, *, require_grain=True):
        if not require_grain:
            return real(ai, city, target, require_grain=False)
        context = dict(city=city, target=target, stage='candidate', evaluated=[])
        self.attack.append(context)
        try:
            result = real(ai, city, target, require_grain=True)
            if result is not None:
                self.t.feasible_offense.add(city.owner)
            if not context['evaluated'] and result is None:
                self.war_eval(ai.state, city, target, 'candidate', None, (), None, ['insufficient_force_or_slots'])
            return result
        finally:
            self.attack.pop()

    def safe_attack(self, real, ai, quote, ids):
        result = real(ai, quote, ids)
        if self.attack and not self.war_depth:
            context = self.attack[-1]
            if context['stage'] == 'candidate' or not result:
                context['evaluated'].append(result)
            if not result:
                reason = ('route_unreachable' if quote is None else
                          'route_time_limit' if quote['turns'] > ai.settings['max_route_turns'] else 'route_risk_limit')
                self.war_eval(ai.state, context['city'], context['target'], context['stage'], None,
                              ids, quote, [reason])
        return result

    def provisioned(self, real, ai, city, ids, quote):
        result = real(ai, city, ids, quote)
        if self.attack and city.id == self.attack[-1]['city'].id:
            ctx = self.attack[-1]
            if not result or not getattr(ai, 'military_budget', False):
                self.war_eval(ai.state, city, ctx['target'], ctx['stage'], None, ids, quote,
                              [] if result else ['outbound_grain'])
        return result

    def war_budget(self, real, ai, city, target, ids, quote):
        self.war_depth += 1
        try:
            result = real(ai, city, target, ids, quote)
        finally:
            self.war_depth -= 1
        if result is not None:
            stage = self.attack[-1]['stage'] if self.attack else 'support_quote'
            alternatives = ai.return_quotes.get((target.id, city.id, city.owner), ())
            self.war_eval(ai.state, city, target, stage, None, ids, quote,
                          budget_reasons(self.game, ai.state, city, result, alternatives), result)
        return result

    def depart(self, real, ai, city, plan):
        options = [order for order in plan['orders'] if order['source'] == city.id
                   and order['march_id'] is None and order['departure_turn'] <= ai.state.turn]
        if not options:
            return real(ai, city, plan)
        target = ai.state.cities.get(options[0]['target'])
        if target is None:
            return real(ai, city, plan)
        self.attack.append(dict(city=city, target=target, stage='departure', evaluated=[]))
        try:
            result = real(ai, city, plan)
            for row in options:
                if row not in plan['orders']:
                    self.war_eval(ai.state, city, target, 'scheduled_order', row.get('mode'),
                                  row['officers'], None, ['scheduled_order_cancelled'])
                elif row['march_id'] is not None:
                    self.record_plan(ai.state, city.owner, plan, 'dispatched')
            return result
        finally:
            self.attack.pop()

    def war_eval(self, state, city, target, stage, mode, ids, quote, reasons, budget=None):
        key = city.owner, target.id
        label = f'{state.turn}:{city.owner}:{target.id}'
        counts, encountered = self.plans.setdefault(key, (Counter(), Counter()))
        counts.update(evaluations=1, blocked=int(bool(reasons)), passed=int(not reasons))
        encountered.update(reasons)
        self.t.blockers[city.owner].update(reasons)
        self.t.row('war-quotes', state, stage=stage, plan_key=label, owner=city.owner,
                   source=city.id, target=target.id, mode=mode or (quote['modes'] if quote else None),
                   officers=list(ids), troops=sum(troop_manifest(state, ids).values()),
                   grain=city.grain, gold=city.gold, quote_days=quote['days'] if quote else None,
                   outcome='blocked' if reasons else 'passed', reasons=reasons,
                   required_grain=budget['required_grain'] if budget else None,
                   required_gold=budget['required_gold'] if budget else None, budget=budget)

    def record_plan(self, state, owner, plan, stage):
        orders, target = plan.get('orders'), plan.get('target')
        if not orders or not target:
            return
        ident = f"{owner}:{plan['created_turn']}:{target}"
        if stage in self.engine_plans.setdefault(ident, set()):
            return
        self.engine_plans[ident].add(stage)
        membership = [{key: order[key] for key in ('source', 'officers', 'mode', 'departure_turn', 'arrival_turn')}
                      for order in orders]
        self.t.row('war-plans', state, plan_id=ident, owner=owner, target=target,
                   created_turn=plan['created_turn'], planned_orders=membership, stage=stage)

    def plan(self, real, ai, owner):
        result = real(ai, owner)
        self.record_plan(ai.state, owner, result, 'assembled')
        return result

    def flush_plans(self, state):
        for (owner, target), row in sorted(self.plans.items()):
            counts, reasons = row
            self.t.row('war-quote-groups', state, plan_key=f'{state.turn-1}:{owner}:{target}', owner=owner,
                       target=target, evaluations=counts['evaluations'], passed=counts['passed'],
                       blocked=counts['blocked'], reasons=dict(reasons))
        self.plans.clear()
