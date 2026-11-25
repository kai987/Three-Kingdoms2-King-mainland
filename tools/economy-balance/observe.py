"""Measure the live observer campaign without changing its decisions or state."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from time import monotonic, process_time
import resource
import sys
import traceback
from unittest.mock import patch

from common import Catalog, ROOT, TOOL_ROOT, HeadlessCampaign, git, sha256, to_csv, to_json
from observer_hooks import Hooks
from observer_telemetry import (AIS, CITY_FIELDS, SCHEMA, StockSnapshot, Telemetry, clock_date, config,
                                sustainable_troops, tick_date, troop_manifest)
from remake import battle_supply, city_economy as economy, domestic, grain_market, grain_units, logistics, march_supply, payroll
from remake.march_core import backend_status

try:
    from remake import winter_weather
except ImportError:
    winter_weather=None  # Prior baseline source trees predate the winter observer.

SCENARIOS = ('184-02', '190-01', '200-01', '207-09', '208-10', '221-07', '263-05')
MILESTONES = (12, 36, 60, 120, 240)
METRICS = ('grain_bought', 'emergency_grain_bought', 'battle_grain_bought', 'grain_sold',
           'purchase_gold', 'sale_gold', 'markets_empty_samples', 'markets_under_batch_samples',
           'unpaid_city_turns', 'rations_missing', 'battles', 'battle_troops_lost', 'granted_aid',
           'requested_aid', 'received_aid_grain', 'raised_troops', 'recruit_gold', 'recruit_grain',
           'postbattle_recruit_gold', 'postbattle_recruit_grain', 'market_city_turns',
           'all_city_turns', 'owned_city_turns', 'active_faction_turns')
LOGISTICS = ('ai_sorties', 'battle_retreats', 'march_rations', 'march_base_rations', 'march_food_missing_days',
             'march_hunger_losses', 'convoy_rations', 'convoy_hunger_losses', 'convoy_base_rations',
             'convoy_dispatched', 'convoy_arrived', 'convoy_returned', 'convoy_grain_sent',
             'convoy_grain_arrived', 'convoy_route_grain_loss', 'convoy_cargo_rations', 'convoy_weather_grain_loss',
             'ai_recruit_quotes', 'ai_recruit_quote_capped', 'ai_sortie_quotes', 'ai_sortie_quote_blocked',
             'ai_reserve_purchases', 'strategic_aid_transports', 'requested_aid_refused',
             'battle_days', 'battle_grain_rations', 'battle_grain_burned', 'march_days', 'convoy_days',
             'convoy_land_departures', 'convoy_river_departures', 'convoy_sea_departures',
             'convoy_minimum_grain_departures', 'convoy_late_arrivals', 'convoy_failed',
             'ai_recruit_quote_rejected', 'ai_emergency_recruit_quotes')
METRICS += LOGISTICS
# These columns remain present for a stable A/D schema. Legacy weather loss,
# cargo meals, unsolicited relief and ordinary route modes all exist under V1.
WEIGHTED_ONLY = frozenset((
    'convoy_route_grain_loss', 'convoy_minimum_grain_departures',
    'ai_recruit_quotes', 'ai_recruit_quote_capped', 'ai_recruit_quote_rejected',
    'ai_emergency_recruit_quotes', 'ai_sortie_quotes', 'ai_sortie_quote_blocked',
    'ai_reserve_purchases', 'strategic_reserve_met', 'strategic_reserve_observed',
    'strategic_reserve_target',
))


def metric(values, name, weighted):
    if name in WEIGHTED_ONLY and not weighted:
        return 'not_applicable'
    value = values[name]
    return int(value) if type(value) is bool else value



class RecordedCampaign(HeadlessCampaign):
    def _emit_event(self, state, kind, **values):
        event = super()._emit_event(state, kind, **values)
        stats = self.flow[event['factions'][0]] if event['factions'] else self.flow['neutral']
        details = event['details']
        if (winter_weather and winter_weather.observing() and event['factions'] and event['city_ids']
                and kind in ('grain_traded','battle_result')):
            winter_weather.action(self,state,kind,event['city_ids'][0],owner=event['factions'][0],
                target=event['city_ids'][1] if len(event['city_ids'])>1 else None,event=details)
        if self.telemetry:
            self.telemetry.event(state, event)
        if kind == 'grain_traded':
            direction = details['direction']
            stats['grain_bought' if direction == 'buy' else 'grain_sold'] += details['grain']
            stats['purchase_gold' if direction == 'buy' else 'sale_gold'] += details['gold']
            if details.get('emergency'):
                stats['emergency_grain_bought'] += details['grain']
            if 'battle_id' in details:
                stats['battle_grain_bought'] += details['grain']
        elif kind == 'diplomacy_result' and details['action'] == 'request_grain':
            stats['requested_aid'] += 1
            if details['success']:
                stats['granted_aid'] += 1
                stats['received_aid_grain'] += details['grain']
            else:
                stats['requested_aid_refused'] += 1
        elif kind == 'battle_result':
            stats['battles'] += 1
            stats['battle_troops_lost'] += details['lost']
            stats['battle_retreats'] += details['outcome'] in ('retreat','defeat')
            supply=state.battle['extended'].get('supply') if state.battle else None
            if supply:
                stats['battle_days']+=supply['days']
                stats['battle_grain_rations']+=sum(book['consumed'] for book in supply['sides'].values())
                stats['battle_grain_burned']+=sum(battle_supply.burned(book) for book in supply['sides'].values())
            for faction in event['factions']:
                self.last_battle_turn[faction] = event['turn']
            if self.telemetry:
                attacker, defender = event['factions'][:2]
                source, target = event['city_ids']
                self.telemetry.receipt(event['factions'], state,
                    dict(battle_id=details['battle_id'], attacker=attacker, defender=defender,
                         source=source, target=target, outcome=details['outcome'], deaths=details['lost'],
                         surrendered=details['surrendered'], days=supply['days'] if supply else None,
                         rations=sum(book['consumed'] for book in supply['sides'].values()) if supply else None,
                         grain_burned=sum(battle_supply.burned(book) for book in supply['sides'].values()) if supply else None,
                         supply_settlement=supply.get('settlement') if supply else None))
        elif kind == 'city_captured':
            self.captured(event['city_ids'][0], state)
        return event

    def _report_ai(self, state, city, action, target=None):
        if action == 'attack':
            self.flow[city.owner]['ai_sorties'] += 1
        if self.telemetry and action in AIS:
            self.telemetry.action(city.owner, action)
            if action == 'recruit_soldiers':
                self.telemetry.troops(state, city.owner, 'ai_direct_recruitment',
                    target=city.id, reserves=self.catalog.data['rules']['recruit_per_action'])
        return super()._report_ai(state, city, action, target)

    def captured(self, city_id, state):
        city = state.cities[city_id]
        past = self.recovering.get(city_id)
        if past:
            self.recoveries.append(dict(past, sampled_turn=state.turn, result='recaptured', ending_grain=city.grain))
        self.recovering[city_id] = dict(scenario=self.campaign_id, city=city_id, owner=city.owner,
                                       capture_turn=state.turn, starting_grain=city.grain)


def _measure(game, month, all_sides, city_history):
    state = game.state
    factions = defaultdict(Counter)
    active = economy.stationed_troops(game, state)
    weighted = state.extension.get('logistics_rules_version') == 2
    plans={}
    if weighted:
        try:
            from remake import military_budget
        except ImportError:
            military_budget=None
        if military_budget:
            for owner in sorted({city.owner for city in state.cities.values()}-{'neutral'}):
                plans.update(military_budget.budgets(game,state,owner,stationed=active))
    identity = dict(scenario=game.campaign_id, elapsed_months=month, elapsed_turns=state.turn-1,
                    year=state.year, month=state.month, day=state.day)
    development = state.extension['city_development']['cities']
    for key, city in state.cities.items():
        record = factions[city.owner]
        market = grain_market.row(state, key)
        row = development[key]
        record.update(cities=1, population=row['population'], total_land=row['land'],
                      total_industry=row['industry'],
                      gold_stock=city.gold, grain_stock=city.grain, reserves=city.reserves,
                      market_stock=market['stock'], market_monthly_supply=market['monthly_supply'])
        owned = city.owner != 'neutral'
        income = economy.monthly_income(game, key, state) if owned else dict(grain=0, gold=0)
        wages = payroll.monthly_due(state, city) if owned else dict(grain=0, gold=0)
        town=economy.town_level(game,state,key)
        present = active.get(key, 0)
        residents = economy.civilian_grain(row['population'], town, state=state) if owned else 0
        ration = residents + (economy.garrison_grain_cost(
            game.catalog.data, key, state.year, state.month, present, city.reserves) if owned else 0)
        if game.telemetry:
            ceiling, excess = sustainable_troops(game, state, city, present,
                income['grain'], residents, wages['grain']) if owned else (None, None)
            city_troops = dict(zip(CITY_FIELDS, (present,
                sum(state.officers[ident].troops for ident in city.roster.officer_ids if state.officers[ident].alive),
                city.reserves, ceiling, excess)))
        else:
            city_troops = {}
        target=plans[key]['target'] if key in plans else None
        record.update(monthly_regular_grain=income['grain'], monthly_gold=income['gold'],
                      monthly_grain_payroll=wages['grain'], monthly_gold_payroll=wages['gold'],
                      monthly_fixed_grain=ration+wages['grain'],
                      strategic_reserve_met=int(target is not None and city.grain>=target),
                      strategic_reserve_observed=int(target is not None))
        city_history.append(dict(identity, city=key, owner=city.owner, population=row['population'],
            land=row['land'], industry=row['industry'], town=town, gold_stock=city.gold, grain_stock=city.grain,
            monthly_regular_grain=income['grain'], monthly_gold=income['gold'], market_stock=market['stock'],
            market_supply=market['monthly_supply'], unpaid_city_turns=game.city_food_shortages[key],
            food_shortage_streak=game.city_food_streak[key], max_food_shortage_streak=game.city_food_max_streak[key],
            market_zero_turns=game.city_market_zero[key], max_market_zero_streak=game.city_market_max_streak[key],
            monthly_fixed_grain=ration+wages['grain'],
            strategic_reserve_target=target if weighted else 'not_applicable', **city_troops))
    for officer in state.officers.values():
        if officer.alive and officer.faction_id in factions:
            factions[officer.faction_id].update(officers=1, active_troops=officer.troops)
    combined = Counter()
    for values in factions.values():
        combined.update(values)
    combined.update(cumulative_total_troops_lost=state.soldiers['lost'])
    flow = Counter()
    for values in game.flow.values():
        flow.update(values)

    for key, previous in list(game.recovering.items()):
        city = state.cities[key]
        town = economy.town_level(game, state, key)
        population = state.extension['city_development']['cities'][key]['population']
        ration = economy.civilian_grain(population, town, state=state) + economy.garrison_grain_cost(
            game.catalog.data, key, state.year, state.month, active.get(key, 0), city.reserves)
        if city.grain >= ration and ration and month and state.turn > previous['capture_turn']:
            game.recoveries.append(dict(previous, sampled_turn=state.turn, result='one_month_rations', ending_grain=city.grain))
            del game.recovering[key]

    for owner in sorted(set(factions) | set(game.flow)):
        values = factions[owner]
        all_sides.append(dict(identity, faction=owner, **{name:metric(values, name, weighted) for name in FAMILIES},
                              **{name:metric(game.flow[owner], name, weighted) for name in METRICS}))
    return dict(identity, **{name:metric(combined, name, weighted) for name in FAMILIES},
                troop_losses=state.soldiers['lost'], **{name:metric(flow, name, weighted) for name in METRICS})


FAMILIES = ('cities', 'population', 'total_land', 'total_industry', 'gold_stock', 'grain_stock',
            'reserves', 'market_stock', 'market_monthly_supply', 'monthly_regular_grain', 'monthly_gold',
            'monthly_grain_payroll', 'monthly_gold_payroll', 'monthly_fixed_grain', 'officers', 'active_troops',
            'strategic_reserve_met', 'strategic_reserve_observed')


def run_scenario(scenario, seed, months, output, group, settings=None, *, hash_turns=False):
    if group.startswith('G'):
        from v212_experiments import configured
        with configured(group):
            return _run_scenario(scenario, seed, months, output, group, settings, hash_turns=hash_turns)
    try:
        from remake import logistics_strategy
    except ImportError:
        if group.startswith('E'):
            raise ValueError('E groups require the V2.1 engine')
        return _run_scenario(scenario, seed, months, output, group, settings, hash_turns=hash_turns)
    stage = {'E1':1, 'E2':2, 'E3':3, 'E4':4, 'F1':4, 'F2':4, 'F3':4}.get(group,0)
    if group in {'F1','F2','F3'}:
        with logistics_strategy.experiment(stage, army=group in {'F1','F3'}, recovery=group in {'F2','F3'}):
            return _run_scenario(scenario, seed, months, output, group, settings, hash_turns=hash_turns)
    with logistics_strategy.experiment(stage):
        return _run_scenario(scenario, seed, months, output, group, settings, hash_turns=hash_turns)


def _run_scenario(scenario, seed, months, output, group, settings, *, hash_turns):
    started = monotonic()
    head=git('rev-parse','HEAD').decode().strip()
    runtime_diff=sha256(git('diff','HEAD','--binary','--','source','game','crates'))
    catalog = Catalog(ROOT / 'game' / 'data' / 'campaigns' / f'{scenario}.json')
    game = RecordedCampaign(catalog, record_journal=False)
    game.campaign_id, game.flow = scenario, defaultdict(Counter)
    game.telemetry = None
    game.city_fixed = {}
    timings, cpu_times = [], []
    staged = group.startswith('G')
    new_metrics = settings is not None and (group in {'E4','F1','F2','F3'} or staged)
    extra_metrics=None
    if new_metrics and (group=='F3' or staged):
        from observer_v212 import Measurements
        extra_metrics=Measurements()
    v211_rows=defaultdict(list)
    committed = []  # Optional verification trace on the independent command boundary.
    with_weather_observer=bool(winter_weather and winter_weather.observing())
    published_metrics=None
    if extra_metrics and winter_weather and winter_weather.detailed():
        from observer_v212 import PublishedMeasurements
        published_metrics=PublishedMeasurements()
    before_weather=[]
    def record_hash():
        committed.append(game.export_save(compact=True)['checksum'])
        if with_weather_observer and winter_weather.stage(game.state)<2:
            from remake.campaign import digest
            snapshot=game.to_dict()
            extension=snapshot['extension']
            extension.pop(winter_weather.POOL,None)
            extension.pop(winter_weather.FIELD,None)
            before_weather.append(digest(snapshot))

    game.recoveries, game.recovering = [], {}
    game.last_battle_turn = {}
    game.city_food_shortages, game.city_market_zero = Counter(), Counter()
    game.city_food_streak,game.city_food_max_streak=Counter(),Counter()
    game.city_market_streak, game.city_market_max_streak = Counter(), Counter()
    world_rows, faction_rows, city_rows = [], [], []
    real_rations, real_report = economy.settle_turn_grain, domestic._report
    real_march, real_cargo, real_event = march_supply.advance_unit, logistics._cargo_change, logistics._event

    def record_march(campaign, state, unit, journey, *args, **values):
        ledger = journey['supply']
        before = {key:ledger.get(key,0) for key in ('shortage_days','base_consumed','lost','elapsed_days')}
        start = len(ledger['starvation']) if game.telemetry else 0
        token=extra_metrics.before_meal(campaign,state,unit,journey,**values) if extra_metrics else None
        adjusted=published_metrics.before_meal(campaign,state,unit,journey,**values) if published_metrics else None
        used = real_march(campaign,state,unit,journey,*args,**values)
        if extra_metrics:
            extra_metrics.after_meal(token,journey)
        if published_metrics:
            published_metrics.after_meal(adjusted,journey)
        stats = game.flow[unit['owner']]
        is_convoy = values.get('unit_kind') == 'convoy'
        if (game.telemetry and is_convoy
                and ledger['shortage_streak'] >= march_supply.RETREAT_DAYS):
            game.telemetry.convoy_hunger.add((unit['id'], ledger['start_tick']))
        if game.telemetry and ledger['lost'] > before['lost']:
            loss_entries = ledger['starvation'][start:]
            reserve_loss = sum(row['reserves_before'] - row['reserves_after'] for row in loss_entries)
            game.telemetry.troops(state, unit['owner'], 'convoy_hunger_deaths' if is_convoy else 'march_hunger_deaths',
                journey.get('source'), journey['target'], active=ledger['lost'] - before['lost'] - reserve_loss,
                reserves=reserve_loss, reference=unit['id'])
        if is_convoy:
            stats.update(convoy_rations=used,
                         convoy_base_rations=ledger.get('base_consumed',0)-before['base_consumed']
                             if 'base_consumed' in ledger else used,
                         convoy_hunger_losses=ledger['lost']-before['lost'],
                         convoy_days=ledger['elapsed_days']-before['elapsed_days'])
        else:
            stats.update(march_rations=used,march_base_rations=ledger.get('base_consumed',0)-before['base_consumed']
                         if 'base_consumed' in ledger else used,
                         march_food_missing_days=ledger['shortage_days']-before['shortage_days'],
                         march_hunger_losses=ledger['lost']-before['lost'],
                         march_days=ledger['elapsed_days']-before['elapsed_days'])
        return used

    def record_cargo(row, kind, cargo, *args, **values):
        name = {'route_loss':'convoy_route_grain_loss','rations':'convoy_cargo_rations',
                'weather':'convoy_weather_grain_loss'}.get(kind)
        if name:
            game.flow[row['owner']][name] += row['cargo']['grain']-cargo['grain']
        return real_cargo(row,kind,cargo,*args,**values)

    def record_transport(campaign,state,kind,row,**values):
        if extra_metrics:
            extra_metrics.transport(state,kind,row,values)
        if published_metrics:
            published_metrics.transport(state,kind,row,values)
        if new_metrics and row['target_march'] is not None:
            first=row['journeys'][0]
            record_v211('army-convoys',state,stage=kind,owner=row['owner'],convoy=row['id'],
                army=row['target_march'],source=row['source'],target=row['target'],status=row['status'],
                reason=values.get('reason','outbound'),cargo=deepcopy(row['cargo']),
                initial_grain=row['initial_cargo']['grain'],escort_strength=sum(first['departure_troops'].values()),
                initial_bag=first['supply']['loaded'],receipt=logistics.grain_receipt(row,
                    returned=values.get('reason')=='returned',abandoned=values.get('reason')=='no_friendly_city'),
                actual_meal_days=sum(journey['supply']['elapsed_days'] for journey in row['journeys']),
                actual_wait_days=sum(journey['supply']['elapsed_days']-journey['supply']['route_days']
                                     for journey in row['journeys']),
                last_node=march_supply.current_city(row['journeys'][-1]),
                actual_supply_tick=row['journeys'][-1]['supply']['clock_tick'],
                plan=row.get('relief','not_applicable'))
        name = {'transport_departed':'convoy_dispatched','transport_arrived':'convoy_arrived',
                'transport_returned':'convoy_returned'}.get(kind)
        if with_weather_observer:
            journey=row['journeys'][-1]
            facts=values.get('amounts') or row['cargo']
            winter_weather.action(campaign,state,kind,row['source'],owner=row['owner'],target=row['target'],
                unit_id=row['id'],grain=facts['grain'],arrival=journey['arrival_turn'],
                blocked=journey['supply'].get('winter',{}).get('blocked'),
                reason=values.get('reason'),army=row['target_march'])
        if name:
            stats=game.flow[row['owner']]
            stats[name]+=1
            cargo = values.get('amounts') or row['cargo']
            if kind == 'transport_departed':
                stats['convoy_grain_sent']+=cargo['grain']
                first=row['journeys'][0]
                for mode in first['quote']['modes']:
                    stats['convoy_'+mode+'_departures']+=1
                stats['convoy_minimum_grain_departures']+=first['mode']=='minimum_grain'
            elif kind == 'transport_arrived':
                stats['convoy_grain_arrived']+=cargo['grain']
                stats['convoy_late_arrivals']+=game.city_food_streak[row['target']]>0
            else:
                stats['convoy_failed']+=not row['delivery_done']
        result = real_event(campaign,state,kind,row,**values)
        if game.telemetry:
            game.telemetry.transport(state, kind, row, **values)
        return result

    def observe_rations(campaign, state):
        owners = {city.owner for city in state.cities.values()} - {'neutral'}
        for owner in owners:
            game.flow[owner]['active_faction_turns'] += 1
        for city in state.cities.values():
            game.flow[city.owner]['all_city_turns'] += 1
            if city.owner != 'neutral':
                game.flow[city.owner]['owned_city_turns'] += 1
        installment = {11: 1, 21: 2, 1: 3}[state.day]
        absent = economy.absent_troops(campaign, state)
        active = economy.stationed_troops(campaign, state, absent)
        garrisons = economy.garrison_grain(campaign, state, stationed=active)
        development = state.extension['city_development']['cities']
        shortages, fixed = [], {}
        for city_id, city in state.cities.items():
            if city.owner == 'neutral':
                game.city_food_streak[city_id] = 0
                continue
            population = development[city_id]['population']
            residents = economy.civilian_grain(population, economy.town_level(campaign, state, city_id), state=state)
            due = economy.turn_rations(residents + garrisons[city_id], installment)
            if game.telemetry:
                fixed[city_id] = residents + garrisons[city_id] + payroll.monthly_due(state, city)['grain']
            if city.grain < due:
                game.flow[city.owner].update(unpaid_city_turns=1, rations_missing=due-city.grain)
                game.city_food_shortages[city_id] += 1
                game.city_food_streak[city_id] += 1
                game.city_food_max_streak[city_id] = max(game.city_food_max_streak[city_id], game.city_food_streak[city_id])
                if game.telemetry:
                    shortages.append((city, due, city.grain, city.reserves))
            else:
                game.city_food_streak[city_id] = 0
        if game.telemetry:
            game.city_fixed = fixed
            snapshot = (StockSnapshot(campaign, state, fixed, absent, settings['reserve_months'])
                        if shortages else None)
            headroom = [snapshot.other(city) for city, *_ in shortages]
            before = state.soldiers['lost']
        real_rations(campaign, state)
        if game.telemetry:
            stationed_after = economy.stationed_troops(campaign, state, absent) if shortages else {}
            measured = 0
            for (city, required, paid, reserve), other in zip(shortages, headroom):
                active_lost = active[city.id] - stationed_after[city.id]
                reserve_lost = reserve - city.reserves
                game.telemetry.row('shortages', state, owner=city.owner, city=city.id,
                    required=required, paid=paid, missing=required-paid, stationed_before=active[city.id],
                    reserves_before=reserve, active_lost=active_lost, reserve_lost=reserve_lost, **other)
                game.telemetry.troops(state, city.owner, 'city_shortage_deaths', target=city.id,
                                     active=active_lost, reserves=reserve_lost)
                game.telemetry.shortages[city.owner] += required - paid
                measured += active_lost + reserve_lost
            if state.soldiers['lost'] - before != measured:
                raise ValueError('City shortage deaths differ from the engine loss receipt')

    def observe_report(state, city, kind, **details):
        if kind == 'recruit':
            stats = game.flow[city.owner]
            stats.update(raised_troops=details['soldiers'],
                         recruit_gold=details['gold'], recruit_grain=details['grain'])
            fought = game.last_battle_turn.get(city.owner)
            if fought is not None and state.turn - fought <= 3:
                stats.update(postbattle_recruit_gold=details['gold'], postbattle_recruit_grain=details['grain'])
            if game.telemetry:
                game.telemetry.troops(state, city.owner, 'delegated_recruitment', target=city.id,
                                     reserves=details['soldiers'])
                game.telemetry.action(city.owner, 'delegated_recruitment')
                if fought is not None and state.turn - fought <= settings['postbattle_turns']:
                    game.telemetry.troops(state, city.owner, 'postbattle_recruitment', target=city.id,
                                         reserves=details['soldiers'], reference=fought)
        if game.telemetry and kind == 'allocation':
            fought = game.last_battle_turn.get(city.owner)
            if fought is not None and state.turn - fought <= settings['postbattle_turns']:
                game.telemetry.troops(state, city.owner, 'postbattle_reserve_assignment', target=city.id,
                                     active=details['soldiers'], officers=details['officers'], reference=fought)
        return real_report(state, city, kind, **details)

    def record_v211(kind,state,**values):
        v211_rows[kind].append(dict(turn=state.turn,date=f'{state.year:04d}-{state.month:02d}-{state.day:02d}',
                                    kind=kind,details=deepcopy(values)))

    outcome, failure = 'complete', None
    game.command('new', dict(faction='observer', seed=seed, difficulty='normal'), 0)
    opened = None
    if new_metrics:
        from remake.campaign import digest
        normalized=game.export_save()['state']
        normalized['extension'].pop('ai_logistics_strategy_version',None)
        opened=digest(normalized)
    with ExitStack() as hooks:
        if extra_metrics:
            extra_metrics.attach(hooks)
        if new_metrics:
            from remake import logistics_strategy
            if hasattr(logistics_strategy,'observe'):
                hooks.enter_context(patch.object(logistics_strategy,'observe',record_v211))
        if settings:
            game.telemetry = Telemetry(game, output / scenario, settings, hooks)
        with grain_units.using(game.state):
            world_rows.append(_measure(game, 0, faction_rows, city_rows))
        if hash_turns:
            record_hash()
        for obj,name,handler in ((economy,'settle_turn_grain',observe_rations),(domestic,'_report',observe_report),
            (march_supply,'advance_unit',record_march),(logistics,'_cargo_change',record_cargo),
            (logistics,'_event',record_transport)):
            hooks.enter_context(patch.object(obj,name,handler))
        try:
            from remake import military_budget
        except ImportError:
            military_budget=None  # A, B and C use their original revision.
        if military_budget is not None:
            real_recruit,real_sortie,real_buy=(military_budget.recruitment,military_budget.sortie,
                                             military_budget.buy_reserves)

            def record_recruit(campaign,state,city,requested,budget):
                accepted=real_recruit(campaign,state,city,requested,budget)
                if requested and budget:
                    game.flow[city.owner].update(ai_recruit_quotes=1,ai_recruit_quote_capped=accepted<requested,
                        ai_recruit_quote_rejected=accepted==0,ai_emergency_recruit_quotes=budget['threatened'])
                return accepted

            def record_sortie(campaign,state,city,*args,**values):
                budget=real_sortie(campaign,state,city,*args,**values)
                if with_weather_observer:
                    target,_,quote,back=args
                    winter_weather.action(campaign,state,'sortie_quote',city.id,owner=city.owner,target=target.id,
                        permitted=budget['can_depart'],required_grain=budget['required_grain'],available_grain=city.grain,
                        outbound=budget['outbound'],returning=budget['returning'],base_days=quote['days'],
                        return_reachable=back is not None)
                game.flow[city.owner].update(ai_sortie_quotes=1,ai_sortie_quote_blocked=not budget['can_depart'])
                return budget

            def record_buy(campaign,state,owner,**kwargs):
                result=real_buy(campaign,state,owner,**kwargs)
                game.flow[owner]['ai_reserve_purchases']+=result
                return result

            hooks.enter_context(patch.object(military_budget,'recruitment',record_recruit))
            hooks.enter_context(patch.object(military_budget,'sortie',record_sortie))
            hooks.enter_context(patch.object(military_budget,'buy_reserves',record_buy))
        real_ai_transport=logistics.dispatch_ai_supply

        def record_ai_transport(campaign,state,target,*args,**values):
            result=real_ai_transport(campaign,state,target,*args,**values)
            game.flow[target.owner]['strategic_aid_transports']+=bool(result)
            return result

        hooks.enter_context(patch.object(logistics,'dispatch_ai_supply',record_ai_transport))
        detailed = Hooks(game.telemetry, hooks, RecordedCampaign) if game.telemetry else None
        for turn in range(1, months * 3 + 1):
            if game.state.phase == 'finished':
                outcome = 'natural_end'
                break
            try:
                before = game.state
                turn_started, cpu_started = monotonic(), process_time()
                game.command('observe_turn', {}, game.revision)
                timings.append(monotonic() - turn_started)
                cpu_times.append(process_time()-cpu_started)
                assert game.state.turn == turn + 1
                if detailed:
                    game.telemetry.roster_moves(before, game.state)
                    detailed.flush_plans(game.state)
                    game.telemetry.finish_turn(game.state)
                if extra_metrics:
                    extra_metrics.turn(game.state)
                if published_metrics:
                    published_metrics.turn(game.state)
                if hash_turns:
                    record_hash()
                for key, city in game.state.cities.items():
                    stock = grain_market.row(game.state, key)['stock']
                    game.flow[city.owner]['market_city_turns'] += 1
                    if stock < 1000:
                        game.flow[city.owner]['markets_under_batch_samples'] += 1
                    if stock == 0:
                        game.flow[city.owner]['markets_empty_samples'] += 1
                        game.city_market_zero[key] += 1
                        game.city_market_streak[key] += 1
                        game.city_market_max_streak[key] = max(game.city_market_streak[key],
                                                               game.city_market_max_streak[key])
                    else:
                        game.city_market_streak[key] = 0
                if turn % 3:
                    continue
                month = turn // 3
                with grain_units.using(game.state):
                    world_rows.append(_measure(game, month, faction_rows, city_rows))
                if month in MILESTONES:
                    original = game.export_save(compact=True)
                    restored = HeadlessCampaign(catalog, record_journal=False)
                    restored.load_save(original, 0)
                    assert restored.export_save(compact=True) == original
                    print(f'{scenario} reached {month} months after {monotonic()-started:.1f}s', flush=True)
                if month % 6 == 0:
                    to_csv(output / scenario / 'monthly.csv', world_rows)
                    to_csv(output / scenario / 'factions.csv', faction_rows)
            except Exception as error:
                outcome = 'error'
                failure = dict(type=type(error).__name__, message=str(error), trace=traceback.format_exc())
                break
    state = game.state
    if state.turn-1 != world_rows[-1]['elapsed_turns']:
        with grain_units.using(state):
            world_rows.append(_measure(game, (state.turn-1)//3, faction_rows, city_rows))
    to_csv(output / scenario / 'monthly.csv', world_rows)
    to_csv(output / scenario / 'factions.csv', faction_rows)
    to_csv(output / scenario / 'cities.csv', city_rows)
    pending = [dict(row, sampled_turn=state.turn, result='unrecovered',
                    ending_grain=state.cities[key].grain) for key, row in game.recovering.items()]
    recovery_path=output / scenario / 'capture-recovery.csv'
    recoveries=[*game.recoveries, *pending]
    if recoveries:
        to_csv(recovery_path,recoveries)
    else:
        recovery_path.write_text('scenario,city,owner,capture_turn,starting_grain,sampled_turn,result,ending_grain\n',
                                 encoding='utf-8')
    result = dict(scenario=scenario, group=group, seed=seed, requested_months=months, completed_turns=state.turn-1,
                  full_months=(state.turn-1)//3, outcome=outcome, backend=backend_status(),
                  head=head, start_date=[catalog.data['start_year'],catalog.data['start_month'],1],
                  worktree_diff_sha256=runtime_diff,
                  rule_versions=dict(economy=state.extension.get('economy_rules_version',1),
                                     market=2 if 'grain_market' in state.extension else 1,
                                     logistics=state.extension.get('logistics_rules_version',1),
                                     ai_strategy=state.extension.get('ai_logistics_strategy_version', 'legacy')),
                  catalog_sha256=catalog.sha256, last_date=[state.year,state.month,state.day],
                  seconds=round(monotonic()-started,2), failure=failure)
    with grain_units.using(state):
        result['terminal'] = dict(
            convoy_loads=[dict(id=row['id'],status=row['status'],owner=row['owner'],source=row['source'],
                               target=row['target'],cargo_grain=row['cargo']['grain'],
                               escort_bag=row['journeys'][-1]['supply']['remaining'])
                          for row in state.extension.get('logistics',{}).get('convoys',())],
            monthly_garrison_grain=sum(economy.garrison_grain(game,state).values()))
    result['performance'] = dict(measured_turns=len(timings),
        mean_turn_seconds=round(sum(timings)/len(timings),6) if timings else None,
        max_turn_seconds=round(max(timings),6) if timings else None,
        total_turn_cpu_seconds=round(sum(cpu_times),6),
        mean_turn_cpu_seconds=round(sum(cpu_times)/len(cpu_times),6) if cpu_times else None,
        max_turn_cpu_seconds=round(max(cpu_times),6) if cpu_times else None,
        worker_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
        (1 if sys.platform == 'darwin' else 1024))
    result['parameters'] = dict(faction='observer', difficulty='normal', lifespan='historical', seed=seed,
                                record_journal=False, commands=['new', 'observe_turn'])
    if settings:
        result['telemetry'] = dict(schema=SCHEMA, config=settings, rows=game.telemetry.counts)
        result['performance']['route_queries'] = dict(game.telemetry.route_queries)
    if new_metrics:
        from remake import logistics_strategy
        runtime_source=git('rev-parse','HEAD:source').decode().strip()
        artifacts={}
        streams={'army-convoys':{'army-convoys'},'army-requests':{'relief_quote','relief_handoff',
                   'relief_cancelled','relief_replanned'},'war-recovery':{'war_recovery'}}
        if staged:
            streams.update({'escort-assignments':{'escort_assignment'}, 'pre-expedition-supply-plans':
                {'staging_node','staging_preparation'}, 'occupation-recovery':{'occupation'}})
        for file,kinds in streams.items():
            rows=sorted((row for kind in kinds for row in v211_rows.get(kind,())),
                        key=lambda item:(item['turn'],item['kind']))
            filename=output/scenario/(file+'.csv')
            if rows:
                to_csv(filename, rows)
            else:
                filename.write_text('turn,date,kind,details\n',encoding='utf-8')
            artifacts[file]=len(rows)
        strategy=dict(army_relief=group in {'F1','F3'} or staged,war_recovery=group in {'F2','F3'} or staged)
        ruleset={}
        if getattr(logistics_strategy,'CURRENT',21)==211:
            from remake import army_relief, war_recovery
            ruleset=dict(wait_days=army_relief.WAIT_DAYS,safety_percent=army_relief.SAFETY_PERCENT,
                efficiency=[army_relief.EFFICIENCY_MINIMUM,army_relief.EFFICIENCY_NORMAL,army_relief.EFFICIENCY_PREFERRED],
                maximum_late_days=army_relief.MAX_LATE_DAYS,loss_window_turns=war_recovery.RECENT_TURNS,
                forecast_turns=war_recovery.SUPPLY_HORIZON,risk=war_recovery.RISK_MULTIPLIERS,
                long_risk=war_recovery.LATER,unfunded_risk=war_recovery.UNFUNDED,
                objective_scale=war_recovery.OBJECTIVE_SCALE,front_pressure=war_recovery.FRONT_PRESSURE)
        result['v211']=dict(opening_sha256=opened, runtime_source_tree=runtime_source,
                            strategy=strategy,candidate_config=ruleset, streams=artifacts)
    if extra_metrics:
        result['v212']=extra_metrics.write(output/scenario,state)
        if staged:
            from v212_experiments import settings_for
            result['v212']['profile']=settings_for(group)
    if published_metrics:
        result['weather_aware_supply']=published_metrics.write(output/scenario,state)
    if winter_weather and winter_weather.detailed() and timings:
        from math import ceil
        result['performance']['percentiles']={}
        for label,measurements in (('wall',timings),('cpu',cpu_times)):
            series=sorted(measurements)
            result['performance']['percentiles'][label]={
                str(p):round(series[ceil(len(series)*p/100)-1],6) for p in (50,95,99)}
    if hash_turns:
        result['committed_save_sha256'] = committed
        if before_weather:
            result['without_weather_state_sha256']=before_weather
    to_json(output / scenario / 'run.json', result)
    if not with_weather_observer:
        print(result, flush=True)
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=SCENARIOS)
    parser.add_argument('--months', type=int, default=60)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--group', choices=('A','B','C','D','E1','E2','E3','E4','F1','F2','F3'), default='D')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--telemetry-config', type=Path, nargs='?', const=TOOL_ROOT / 'tools/economy-balance/observer-config.json',
                        help='Record optional detailed V2.1 observations')
    parser.add_argument('--hash-turns', action='store_true', help='Hash each committed compact save for parity checks')
    args = parser.parse_args()
    settings = config(args.telemetry_config) if args.telemetry_config else None
    if min(args.months, args.workers, args.seed) < 1:
        parser.error('months, workers and seed must be positive')
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks = [pool.submit(run_scenario, scenario, args.seed, args.months, args.output, args.group,
                             settings, hash_turns=args.hash_turns)
                 for scenario in args.scenarios]
        for result in as_completed(tasks):
            results.append(result.result())
    to_json(args.output / 'runs.json', sorted(results, key=lambda row: row['scenario']))
    return any(row['outcome'] == 'error' for row in results)


if __name__ == '__main__':
    raise SystemExit(main())
