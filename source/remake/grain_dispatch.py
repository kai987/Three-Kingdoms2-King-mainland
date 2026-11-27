"""Faction relief. Quotes are planning data and every load uses logistics.dispatch."""
from collections import Counter, defaultdict

from . import city_economy, command_books, domestic, facilities, faction_economy
from . import historical_campaigns, logistics, logistics_strategy, strategic_granary, transport_capacity, winter_travel
from .errors import GameError
from .officers import ref_sort_key


def _donors(game, state, plan):
    owner = plan.owner
    pool = state.extension['logistics']
    active = transport_capacity.activity(state)
    absent = city_economy.absent_troops(game, state)
    posts = domestic.appointments(state, owner)
    reserved_officers = {posts.get('civil'), posts.get('military'), state.extension['leaders'].get(owner)}
    for order in state.extension['ai_strategy'].get(owner, {}).get('orders', ()):
        if order['march_id'] is None and order['departure_turn'] >= state.turn:
            reserved_officers.update(order['officers'])
    groups, excluded = defaultdict(list), {}
    for key, budget in plan.budgets.items():
        city, ledger = state.cities[key], pool['cities'][key]
        policy=transport_capacity.ai_policy(state,owner,ledger['policy'],automatic=transport_capacity.automation(state,owner))
        minimum = max(policy['reserve_grain'], budget['minimum_export_floor'])
        if budget['threatened']:
            minimum = max(minimum, budget['safety_reserve'])
        if transport_capacity.dispatch_blocker(state,city,active):
            excluded[key] = 'source_convoy_limit'
        elif (not policy['max_grain'] or not policy['max_officers']
              or historical_campaigns.hold_longyou_garrison(game, state, city)):
            excluded[key] = 'source_policy'
        elif city.grain - budget['reserved_grain'] <= minimum:
            excluded[key] = 'source_minimum_reserve'
        else:
            present = [ident for ident in city.roster.officer_ids if ident not in absent
                       and state.officers[ident].alive and state.officers[ident].faction_id == owner]
            escorts = [ident for ident in present if ident not in reserved_officers
                       and state.officers[ident].health > 0
                       and state.extension['officer_actions'].get(str(ident)) != state.turn
                       and pool['receipts'].get(str(ident), 0) <= state.turn]
            if transport_capacity.enabled(state):
                eligible=set(logistics._eligible(game,state,city,absent=absent))
                escorts=[ident for ident in escorts if ident in eligible and logistics.escort_defence(
                    game,state,city,[ident],threatened=budget['threatened'])]
            if len(present) <= policy['reserve_officers'] or not escorts:
                excluded[key] = 'no_eligible_escort'
                continue
            escort = min(escorts, key=lambda ident: (state.officers[ident].troops, ref_sort_key(ident)))
            groups[policy['allow_sea'], policy['allow_special']].append((key, escort, policy, minimum))
    return groups, excluded


def _reverse_shipments(state, owner):
    logistics_pool = state.extension['logistics']
    return {(row['target'], row['source']) for row in logistics_pool['convoys']
            if row['owner'] == owner and row['status'] == 'outbound' and not row['delivery_done']} | {
        (row['target'], row['source']) for row in logistics_pool['reports']
        if row['owner'] == owner and row['kind'] == 'transport_arrived' and row['details']['grain']
        and row['turn'] >= state.turn - 2}


def _options(game, state, plan, keys):
    owner = plan.owner
    groups, failures = _donors(game, state, plan)
    reverse = _reverse_shipments(state, owner)
    detailed = logistics_strategy.enabled(state, logistics_strategy.TRANSPORT)
    candidates, rejected = defaultdict(list), {key: Counter(
        reason for source, reason in failures.items() if source != key) for key in keys}
    for donors in groups.values():
        pairs = {(source, target) for source, _, policy, _ in donors for target in keys
                 if source != target and (source, target) not in reverse
                 and policy['target_city'] in (None, target)}
        if not pairs:
            continue
        quotes = logistics._supply_routes(game, state, owner,
            sorted(pairs | {(target, source) for source, target in pairs}), donors[0][2])
        for source, escort, policy, minimum in donors:
            city = state.cities[source]
            stock = city.grain - plan.budgets[source]['reserved_grain']
            for target in keys:
                if source == target:
                    continue
                if (source, target) not in pairs:
                    rejected[target]['reverse_shipment' if (source, target) in reverse else 'source_policy'] += 1
                    continue
                there = state.cities[target]
                outward = logistics._safe_options(game, state, city, there, policy, quotes=quotes)
                backward = logistics._safe_options(game, state, there, city, policy, quotes=quotes)
                if not outward or not backward:
                    rejected[target]['no_legal_route' if not outward else 'no_legal_return'] += 1
                    continue
                # Actual unloaded convoys choose the fastest legal route
                # home. Price that full route, not just its first checkpoint.
                physical=transport_capacity.enabled(state,'physical_capacity')
                for mode, quote in outward if detailed or physical else outward[:1]:
                    rations = logistics.escort_rations(game,state,[escort],quote,backward[0][1])
                    gross = min(policy['max_grain'], stock - minimum - rations)
                    if physical:
                        from . import staging_supply
                        available=min(stock-minimum,staging_supply.available(state,city)-policy['reserve_grain'])
                        gross=transport_capacity.loading(game,state,owner,policy,quote,rations,available,logistics.LIMIT,
                            automatic=transport_capacity.automation(state,owner))['max_cargo']
                    if gross <= 0:
                        rejected[target]['insufficient_escort_rations'] += 1
                        continue
                    net = logistics.projected_grain(game, quote, gross)
                    if not net:
                        rejected[target]['no_net_delivery'] += 1
                        continue
                    back_days=winter_travel.quote_days(game,state,backward[0][1]) if transport_capacity.enabled(
                        state,'throughput_ranking') else 0
                    candidates[target].append((source, escort, mode, quote, rations, gross, net, minimum,back_days))
    return candidates, rejected


def dispatch(game, state, owner, *, plan=None):
    """Return actual requests and execution outcomes for the diagnostic observer."""
    if 'logistics' not in state.extension:
        return []
    detailed = logistics_strategy.enabled(state, logistics_strategy.TRANSPORT)
    plan = plan if plan is not None else faction_economy.plan(game, state, owner)
    keys = plan.shortages(state)
    candidate_demand = strategic_granary.candidate(state)
    if strategic_granary.enabled(state) and not candidate_demand:
        # Pending manual orders may be superseded by a real emergency; a
        # shipped ordinary receipt is already in the dated forecast.
        keys = [key for key in keys if plan.cities[key].zero_in <= 1 or
                not any(order['target'] == key for order in strategic_granary.commitments(state))]
    if not keys:
        return []
    budgets = plan.budgets
    civil = domestic.appointments(state, owner).get('civil')
    blocker = ('no_command_books_remaining' if not command_books.can_spend(state, owner, 'dispatch_transport')
               else 'no_available_civil_officer'
               if not domestic._present(game, state, state.cities[keys[0]], civil) else None)
    candidates, rejected = _options(game, state, plan, keys) if not blocker else ({}, {})
    local_orders = min(2, sum(budgets[key]['current_shortfall'] > 0 and budgets[key]['market_affordable'] > 0
                              for key in keys))
    used = set()
    records = []
    for key in keys:
        forecast = plan.cities[key]
        budget = budgets[key]
        stock = max(0, state.cities[key].grain - budget['reserved_grain'])
        queue = candidates.get(key, ())
        shortage = sum(gap for turn, gap in forecast.gaps if turn <= 3)
        issue = dict(target=key, owner=owner, grain=shortage, deadline=forecast.zero_in,
                     candidates=[], allocations=[], failures=dict(rejected.get(key, ())),
                     reason=blocker)
        for source, escort, mode, quote, rations, gross, net, minimum, _ in queue:
            issue['candidates'].append(dict(source=source, route_mode=mode, days=quote['days'],
                arrival_turn=state.turn+quote['turns'], expected_capacity=net,
                timely=quote['turns'] < forecast.zero_in))
        records.append(issue)
        # The earliest missed installment stays visible. A longer convoy
        # may still cover later bills, while purchases/allied aid cover today.
        horizon = faction_economy.HORIZON if detailed else 3
        past = []
        if candidate_demand:
            from . import granary_demand
            past.extend(forecast.conditional_receipts.items())
            past.extend(granary_demand.held_deliveries(game, state, plan, key))
        while not blocker and command_books.can_spend(state, owner, 'dispatch_transport'):
            if command_books.remaining(state, owner) < command_books.cost('dispatch_transport') + local_orders:
                issue['reason'] = 'books_reserved_for_immediate_relief'
                break
            gaps, balances, _ = faction_economy.balance(stock, forecast.timeline, past)
            priority = []
            for candidate in queue:
                source, escort, mode, quote, rations, gross, net, minimum, back_days = candidate
                if source in used:
                    continue
                arrival = quote['turns']
                payable = sum(gap for turn, gap in gaps if arrival < turn <= horizon)
                # Do not send a perfunctory load when a forecast already
                # covers every installment after the convoy would arrive.
                if not payable:
                    continue
                room = logistics.LIMIT - balances[min(len(balances), arrival)-1]
                amount = min(payable,net,room)
                if not amount:
                    continue
                timely = arrival < forecast.zero_in
                if not timely and amount*2 < rations:
                    issue['failures']['late_load_below_escort_cost'] = 1
                    continue
                # A usable late load still ranks behind all timely rescue.
                rank = (not timely, quote['days'], -amount, gross-net+rations, source, mode)
                if transport_capacity.enabled(state,'throughput_ranking'):
                    out=winter_travel.quote_days(game,state,quote)
                    wait=(-out)%10+(-back_days)%10
                    rank=(not timely,*transport_capacity.priority(amount,rations,out,back_days,wait,1,
                        logistics.RULES['receipt_turns'],gross-net+rations),source,mode)
                priority.append((rank, candidate, amount))
            if not priority:
                break
            _, candidate, amount = min(priority, key=lambda row: row[0])
            source, escort, mode, quote, rations, gross, _, minimum, _ = candidate
            load = logistics.gross_shipment(game,quote,amount,gross)
            used.add(source)
            city = state.cities[source]
            item = faction_economy.Commitment(f"rescue:{state.turn}:{key}", owner, source,
                key, load+rations, min(2, forecast.zero_in), state.turn, state.turn)
            if city.owner != owner or not plan.commitments.reserve(item, city.grain-minimum):
                issue['failures']['reservation_conflict'] = issue['failures'].get('reservation_conflict', 0)+1
                continue
            try:
                convoy = logistics.dispatch(game, state, dict(source=source, target=key,
                    officers=[escort], cargo=dict(gold=0, grain=load, reserves=0), route_mode=mode),
                    owner, emergency_grain=rations)
            except GameError as error:
                issue['failures'][str(error)] = issue['failures'].get(str(error), 0)+1
                continue
            finally:
                plan.commitments.release(item)
            actual = convoy['journeys'][-1]['quote']
            net = logistics.projected_grain(game, actual, load)
            past.append((actual['turns'], net))
            available = city.grain - plan.budgets[source]['reserved_grain']
            released = max(0, min(load+rations, plan.budgets[source]['target'] - available))
            issue['allocations'].append(dict(convoy_id=convoy['id'], source=source,
                grain=load, escort_rations=rations, expected_grain=net, depart_turn=state.turn,
                arrival_turn=state.turn+actual['turns'], released_reserve=released,
                release_reason='emergency_relief' if released else None, donor_grain=available,
                donor_required_floor=minimum))
        if not issue['allocations'] and not issue['reason']:
            if not command_books.can_spend(state, owner, 'dispatch_transport'):
                issue['reason'] = 'no_command_books_remaining'
            elif queue:
                issue['reason'] = 'no_effective_delivery' if not shortage else 'late_or_no_uncovered_installment'
            else:
                issue['reason'] = 'no_executable_source'
    return records


def recover(game, state, owner, plan, *, only=None):
    """Commit locally affordable purchases if dated receipts will be too late."""
    bought = []
    if not facilities._ready(state, owner):
        return bought
    absent = city_economy.absent_troops(game, state)
    for key in plan.shortages(state) if only is None else only:
        city, forecast = state.cities[key], plan.cities[key]
        due = sum(missing for eta, missing in forecast.gaps if eta <= 3)
        if not due:
            continue
        amount = min(forecast.monthly * 2, due)
        offer = facilities.emergency_quote(game, state, city, amount)
        actors = [ident for ident in city.roster.officer_ids if ident not in absent
                  and facilities._resident(game, state, city, ident, working=True, healthy=True)]
        reason = (None if command_books.can_spend(state, owner, 'trade_grain') else 'no_command_books_remaining')
        reason = reason or (offer['blocked_reason'] if not offer['grain'] else None)
        if not actors:
            reason = reason or 'no_eligible_buyer'
        row = dict(target=key, owner=owner, grain=amount, bought=0, reason=reason)
        if not reason:
            actor = min(actors, key=lambda ident: (-state.officers[ident].profile.intellect,ref_sort_key(ident)))
            try:
                result = facilities.buy_emergency_grain(game, state, key, actor, owner, amount)
            except GameError as error:
                row['reason'] = str(error)
            else:
                row['bought'] = result['grain']
        bought.append(row)
    return bought
