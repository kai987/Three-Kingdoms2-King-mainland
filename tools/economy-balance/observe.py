"""Measure the live observer campaign without changing its decisions or state."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import ExitStack
from pathlib import Path
from time import monotonic
import traceback
from unittest.mock import patch

from common import Catalog, ROOT, HeadlessCampaign, git, sha256, to_csv, to_json
from remake import battle_supply, city_economy as economy, domestic, grain_market, logistics, march_supply, payroll
from remake.march_core import backend_status

SCENARIOS = ('184-02', '190-01', '200-01', '207-09', '208-10', '221-07', '263-05')
MILESTONES = (12, 36, 60, 120, 240)
METRICS = ('grain_bought', 'emergency_grain_bought', 'battle_grain_bought', 'grain_sold',
           'purchase_gold', 'sale_gold', 'markets_empty_samples', 'markets_under_batch_samples',
           'unpaid_city_turns', 'rations_missing', 'battles', 'battle_troops_lost', 'granted_aid',
           'requested_aid', 'received_aid_grain', 'raised_troops', 'recruit_gold', 'recruit_grain',
           'postbattle_recruit_gold', 'postbattle_recruit_grain', 'market_city_turns')
LOGISTICS = ('ai_sorties', 'battle_retreats', 'march_rations', 'march_base_rations', 'march_food_missing_days',
             'march_hunger_losses', 'convoy_rations', 'convoy_hunger_losses',
             'convoy_dispatched', 'convoy_arrived', 'convoy_returned', 'convoy_grain_sent',
             'convoy_grain_arrived', 'convoy_route_grain_loss', 'convoy_cargo_rations', 'convoy_weather_grain_loss',
             'ai_recruit_quotes', 'ai_recruit_quote_capped', 'ai_sortie_quotes', 'ai_sortie_quote_blocked',
             'ai_reserve_purchases', 'strategic_aid_transports', 'requested_aid_refused',
             'battle_days', 'battle_grain_rations', 'battle_grain_burned', 'march_days', 'convoy_days',
             'convoy_land_departures', 'convoy_river_departures', 'convoy_sea_departures',
             'convoy_minimum_grain_departures', 'convoy_late_arrivals', 'convoy_failed',
             'ai_recruit_quote_rejected', 'ai_emergency_recruit_quotes')
METRICS += LOGISTICS


class RecordedCampaign(HeadlessCampaign):
    def _emit_event(self, state, kind, **values):
        event = super()._emit_event(state, kind, **values)
        stats = self.flow[event['factions'][0]] if event['factions'] else self.flow['neutral']
        details = event['details']
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
        elif kind == 'city_captured':
            self.captured(event['city_ids'][0], state)
        return event

    def _report_ai(self, state, city, action, target=None):
        if action == 'attack':
            self.flow[city.owner]['ai_sorties'] += 1
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
    plans={}
    if state.extension.get('logistics_rules_version') == 2:
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
        ration=(economy.civilian_grain(row['population'],town,state=state)+economy.garrison_grain_cost(
            game.catalog.data,key,state.year,state.month,active.get(key,0),city.reserves)) if owned else 0
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
            monthly_fixed_grain=ration+wages['grain'], strategic_reserve_target=target))
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
        all_sides.append(dict(identity, faction=owner, **{name:values[name] for name in FAMILIES},
                              **{name:game.flow[owner][name] for name in METRICS}))
    return dict(identity, **{name:combined[name] for name in FAMILIES},
                troop_losses=state.soldiers['lost'], **{name:flow[name] for name in METRICS})


FAMILIES = ('cities', 'population', 'total_land', 'total_industry', 'gold_stock', 'grain_stock',
            'reserves', 'market_stock', 'market_monthly_supply', 'monthly_regular_grain', 'monthly_gold',
            'monthly_grain_payroll', 'monthly_gold_payroll', 'monthly_fixed_grain', 'officers', 'active_troops',
            'strategic_reserve_met', 'strategic_reserve_observed')


def run_scenario(scenario, seed, months, output, group):
    started = monotonic()
    head=git('rev-parse','HEAD').decode().strip()
    runtime_diff=sha256(git('diff','HEAD','--binary','--','source','game','crates'))
    catalog = Catalog(ROOT / 'game' / 'data' / 'campaigns' / f'{scenario}.json')
    game = RecordedCampaign(catalog, record_journal=False)
    game.campaign_id, game.flow = scenario, defaultdict(Counter)
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
        used = real_march(campaign,state,unit,journey,*args,**values)
        stats = game.flow[unit['owner']]
        if values.get('unit_kind') == 'convoy':
            stats.update(convoy_rations=used,convoy_hunger_losses=ledger['lost']-before['lost'],
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
        name = {'transport_departed':'convoy_dispatched','transport_arrived':'convoy_arrived',
                'transport_returned':'convoy_returned'}.get(kind)
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
        return real_event(campaign,state,kind,row,**values)

    def observe_rations(campaign, state):
        installment = {11: 1, 21: 2, 1: 3}[state.day]
        garrisons = economy.garrison_grain(campaign, state)
        for city_id, city in state.cities.items():
            if city.owner == 'neutral':
                continue
            population = state.extension['city_development']['cities'][city_id]['population']
            residents = economy.civilian_grain(population, economy.town_level(campaign, state, city_id), state=state)
            due = economy.turn_rations(residents + garrisons[city_id], installment)
            if city.grain < due:
                game.flow[city.owner].update(unpaid_city_turns=1, rations_missing=due-city.grain)
                game.city_food_shortages[city_id] += 1
                game.city_food_streak[city_id]+=1
                game.city_food_max_streak[city_id]=max(game.city_food_max_streak[city_id],game.city_food_streak[city_id])
            else:
                game.city_food_streak[city_id]=0
        real_rations(campaign, state)

    def observe_report(state, city, kind, **details):
        if kind == 'recruit':
            stats = game.flow[city.owner]
            stats.update(raised_troops=details['soldiers'],
                         recruit_gold=details['gold'], recruit_grain=details['grain'])
            fought = game.last_battle_turn.get(city.owner)
            if fought is not None and state.turn - fought <= 3:
                stats.update(postbattle_recruit_gold=details['gold'], postbattle_recruit_grain=details['grain'])
        return real_report(state, city, kind, **details)

    outcome, failure = 'complete', None
    game.command('new', dict(faction='observer', seed=seed, difficulty='normal'), 0)
    world_rows.append(_measure(game, 0, faction_rows, city_rows))
    with ExitStack() as hooks:
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
                game.flow[city.owner].update(ai_sortie_quotes=1,ai_sortie_quote_blocked=not budget['can_depart'])
                return budget

            def record_buy(campaign,state,owner):
                result=real_buy(campaign,state,owner)
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
        for turn in range(1, months * 3 + 1):
            if game.state.phase == 'finished':
                outcome = 'natural_end'
                break
            try:
                game.command('observe_turn', {}, game.revision)
                assert game.state.turn == turn + 1
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
                                     logistics=state.extension.get('logistics_rules_version',1)),
                  catalog_sha256=catalog.sha256, last_date=[state.year,state.month,state.day],
                  seconds=round(monotonic()-started,2), failure=failure)
    to_json(output / scenario / 'run.json', result)
    print(result, flush=True)
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=SCENARIOS)
    parser.add_argument('--months', type=int, default=60)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--group', choices='ABCDE', default='D')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if min(args.months, args.workers, args.seed) < 1:
        parser.error('months, workers and seed must be positive')
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks = [pool.submit(run_scenario, scenario, args.seed, args.months, args.output, args.group)
                 for scenario in args.scenarios]
        for result in as_completed(tasks):
            results.append(result.result())
    to_json(args.output / 'runs.json', sorted(results, key=lambda row: row['scenario']))
    return any(row['outcome'] == 'error' for row in results)


if __name__ == '__main__':
    raise SystemExit(main())
