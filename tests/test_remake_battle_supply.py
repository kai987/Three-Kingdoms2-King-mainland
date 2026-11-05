"""Carried food closes the march, battle, market and settlement accounts."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign
from remake import battle_supply, march_supply
from remake.errors import GameError
from remake.march_core import using_backend
from campaign_fixtures import controlled_catalog, reach_battle
import test_remake_battle_objectives as objectives

WAIT = dict(kind='wait', actor=None, target=None, tactic=None, score=0)


def command(game, kind, **payload):
    return game.command(kind, payload, game.revision)


def new():
    game = Campaign(controlled_catalog())
    command(game, 'new', faction='shu', seed=2026)
    return game


def direct_battle(*, attacker_grain=None, defender_grain=None):
    game = new()
    state = game.state
    source, target = state.cities['xiangyang'], state.cities['nanyang']
    if attacker_grain is not None:
        # The old direct-entry strategic expense is separate from real bags.
        source.grain = max(1, state.officers[146].troops//25) + attacker_grain
    if defender_grain is not None:
        target.grain = defender_grain
    game._start_expanded_battle(state, source, target, [146])
    return game


def advance_day(game):
    battle = game.state.battle
    battle['round'] += 1
    return battle_supply.end_day(game, game.state, battle)


class BattleSupplyTests(unittest.TestCase):
    def test_departure_quotes_are_pure_have_a_low_food_default_and_strict_maximum(self):
        game = new(); state = game.state
        route = game._travel_path(state, 'xiangyang', 'nanyang', 'shu', 'fastest', adjacent=True)
        state.cities['xiangyang'].grain = 4
        before = deepcopy(state)
        quote = battle_supply.departure_quote(state, [146], route)
        self.assertEqual(quote['march_grain'], 1)
        self.assertEqual(quote['battle_grain_default'], 3)
        self.assertEqual(quote['battle_grain_max'], 3)
        self.assertEqual(quote['total_grain'], 4)
        self.assertEqual(state, before)
        self.assertEqual(battle_supply.departure_quote(state,[146],route,battle_grain=0)['total_grain'],1)
        for invalid in (-1, 4, True, '3', 3.0):
            with self.subTest(invalid=invalid), self.assertRaises(GameError):
                battle_supply.departure_quote(state,[146],route,battle_grain=invalid)
        self.assertEqual(state, before)

    def test_attack_arrival_transfers_exact_march_balance_and_fractional_credit(self):
        game = new(); source = game.state.cities['xiangyang']
        initial = source.grain
        command(game,'depart',source=source.id,target='nanyang',officers=[146])
        march = deepcopy(game.state.extension['travel']['marches'][0])
        self.assertEqual(march['supply']['loaded'], 10)  # 1 march + 9 battle
        self.assertEqual(game.state.cities[source.id].grain, initial-10)
        reach_battle(game)
        row = game.state.battle['extended']['supply']['sides']['attackers']
        self.assertEqual((row['loaded'],row['initial_credit']), (9,720))
        self.assertEqual(game.state.cities[source.id].grain, initial-10)
        self.assertEqual(game.state.battle['extended']['supply']['sides']['defenders']['loaded'],18)
        game.validate(game.state)

    def test_friendly_transfer_has_only_the_existing_march_budget(self):
        game = new(); state = game.state
        state.cities['nanjun'].owner = 'shu'
        source = state.cities['xiangyang']; before = source.grain
        game._queue_march(state,source,state.cities['nanjun'],[146],'transfer')
        row = state.extension['travel']['marches'][0]
        self.assertEqual(row['supply']['loaded'],march_supply.estimate(state,[146],row['quote']))
        self.assertEqual(before-source.grain,row['supply']['loaded'])

    def test_explicit_attack_budget_and_rejected_overload_are_atomic(self):
        game = new(); before = game.export_save()
        for invalid in (-1,3800,True,'2'):
            with self.subTest(invalid=invalid), self.assertRaises(GameError):
                command(game,'depart',source='xiangyang',target='nanyang',officers=[146],battle_grain=invalid)
            self.assertEqual(game.export_save(),before)
        command(game,'depart',source='xiangyang',target='nanyang',officers=[146],battle_grain=0)
        self.assertEqual(game.state.extension['travel']['marches'][0]['supply']['loaded'],1)

    def test_daily_charges_keep_fractional_credit_and_follow_actual_survivors(self):
        game = direct_battle(); battle = game.state.battle
        row = battle['extended']['supply']['sides']['attackers']
        start = row['remaining']; rng = deepcopy(game.state.rng)
        for _ in range(3):
            advance_day(game)
        self.assertEqual(row['consumed'],1)
        self.assertEqual(row['credit_units'],160)  # 1000-3*(180+100)
        battle['attackers'][0]['troops'] = 50
        for _ in range(4):
            advance_day(game)
        self.assertEqual(row['consumed'],2)
        self.assertEqual(row['credit_units'],560)
        self.assertEqual(row['remaining'],start-2)
        before = deepcopy(battle['extended']['supply'])
        battle_supply.end_day(game,game.state,battle)
        self.assertEqual(battle['extended']['supply'],before,'Repeated day hook must not charge twice')
        self.assertEqual(game.state.rng,rng)
        battle_supply.validate(game.state,battle)

    def test_real_side_pass_charges_once_without_strategic_orders_or_randomness(self):
        game = direct_battle(); before = deepcopy(game.state)
        with patch('remake.tactical_ai.choose_action',return_value=WAIT):
            command(game,'battle_wait',battle_id=game.state.battle['id'])
        battle = game.state.battle
        self.assertEqual(battle['round'],2)
        self.assertEqual(battle['extended']['supply']['days'],1)
        for side in battle_supply.SIDES:
            self.assertEqual(battle['extended']['supply']['sides'][side]['consumed'],1)
        self.assertEqual(game.state.extension['command_books'],before.extension['command_books'])
        self.assertEqual(game.state.rng,before.rng)
        game.validate(game.state)

    def test_empty_armies_withdraw_by_identical_rules_and_ties_favor_the_defender(self):
        for attack, defend, side, outcome in ((0,30,'attackers','retreat'),
                (30,0,'defenders','victory'),(0,0,'attackers','retreat')):
            with self.subTest(side=side,attack=attack,defend=defend):
                game = direct_battle(attacker_grain=attack,defender_grain=defend)
                rng = deepcopy(game.state.rng)
                advance_day(game)
                battle = game.state.battle
                self.assertEqual(battle['outcome'],outcome)
                self.assertEqual(battle['extended']['withdrawn'],side)
                self.assertEqual(game.state.phase,'result')
                self.assertEqual(game.state.rng,rng)
                event = game.state.extension['events']['items'][-1]
                self.assertEqual(event['kind'],'battle_supply_exhausted')
                self.assertEqual(event['details']['side'],side)
                battle_supply.validate(game.state,battle)

    def test_legacy_view_and_load_never_charge_or_give_free_grain(self):
        game = direct_battle(); game.state.battle['extended'].pop('supply')
        before = game.export_save(); cities = deepcopy(game.state.cities)
        info = battle_supply.view(game.state,game.state.battle)
        self.assertFalse(info['initialized'])
        self.assertIsNone(info['sides']['attackers']['grain'])
        game.view(); game.view()
        restored = Campaign(game.catalog); restored.load_save(before,0)
        self.assertEqual(restored.export_save(),before)
        self.assertEqual(restored.state.cities,cities)
        with patch('remake.tactical_ai.choose_action',return_value=WAIT):
            command(restored,'battle_wait',battle_id=restored.state.battle['id'])
        row = restored.state.battle['extended']['supply']['sides']['attackers']
        self.assertEqual(cities['xiangyang'].grain-restored.state.cities['xiangyang'].grain,row['loaded'])
        self.assertEqual(row['loaded'],9)
        restored.validate(restored.state)

    def test_rejected_legacy_command_rolls_back_even_its_lazy_loading(self):
        game = direct_battle(); battle = game.state.battle
        battle['extended'].pop('supply')
        before = game.export_save()
        with self.assertRaises(GameError):
            command(game,'attack',battle_id=battle['id'],actor=146,target=battle['defenders'][0]['id'])
        self.assertEqual(game.export_save(),before)

    def test_both_markets_add_only_to_the_army_and_keep_prices_and_rng(self):
        for side in battle_supply.SIDES:
            with self.subTest(side=side):
                game,battle,actor = objectives.BattleServiceTests().ready('market',side=side)
                game.state.player=battle['attacker' if side=='attackers' else 'defender']
                before = deepcopy(game.state)
                command(game,'battle_facility',battle_id=battle['id'],actor=actor['id'],action='buy_grain',batches=2)
                current = game.state.battle['extended']['supply']['sides'][side]
                old = before.battle['extended']['supply']['sides'][side]
                self.assertEqual(current['remaining'],old['remaining']+200)
                self.assertEqual(current['received'],200)
                self.assertEqual({k:c.grain for k,c in game.state.cities.items()},
                                 {k:c.grain for k,c in before.cities.items()})
                self.assertEqual(game.state.rng,before.rng)
                self.assertEqual(game.state.extension['command_books'],before.extension['command_books'])
                game.validate(game.state)

    def test_successful_battle_returns_both_physical_balances_once(self):
        game = direct_battle(); state = game.state; battle = state.battle
        before = sum(city.grain for city in state.cities.values())
        remaining = sum(row['remaining'] for row in battle['extended']['supply']['sides'].values())
        for unit in battle['defenders']:
            unit['troops'] = 0
        battle['outcome']='victory'; state.phase='result'
        ident = battle['id']
        command(game,'settle',battle_id=ident)
        self.assertEqual(sum(city.grain for city in game.state.cities.values()),before+remaining)
        self.assertEqual(game.state.cities['nanyang'].owner,'shu')
        self.assertEqual(game.state.cities['nanyang'].grain,state.cities['nanyang'].grain+remaining)
        saved = game.export_save()
        command(game,'settle',battle_id=ident)
        self.assertEqual(game.export_save(),saved)

    def test_retreat_returns_to_actual_friendly_home_not_a_captured_origin(self):
        game = direct_battle(); state = game.state; battle = state.battle
        original = state.cities['xiangyang']; home = state.cities['nanjun']
        home.owner='shu'; original.owner='wu'
        original.roster.officer_ids.remove(146);home.roster.officer_ids.append(146)
        battle['outcome']='retreat';battle['extended']['withdrawn']='attackers'
        original_before,home_before = original.grain,home.grain
        remaining = battle['extended']['supply']['sides']['attackers']['remaining']
        report = battle_supply.settle(game,state,battle)
        self.assertEqual(original.grain,original_before)
        self.assertEqual(home.grain,home_before+remaining)
        self.assertEqual(report[0]['city'],home.id)
        before = deepcopy(state.cities)
        self.assertEqual(battle_supply.settle(game,state,battle),report)
        self.assertEqual(state.cities,before)

    def test_defender_withdrawal_keeps_its_bags_and_annihilation_leaves_spoils(self):
        for routed in (False,True):
            with self.subTest(routed=routed):
                game = direct_battle(); state = game.state; battle = state.battle
                target, home = state.cities['nanyang'],state.cities['nanjun']
                home.owner='wei'
                defender=battle['defenders'][0]
                target.roster.officer_ids.remove(defender['id'])
                home.roster.officer_ids.append(defender['id'])
                if routed:
                    defender['troops']=0
                target.owner='shu'
                # Match the real conquest's final rosters before grain return.
                state.cities['xiangyang'].roster.officer_ids.remove(146)
                target.roster.officer_ids.append(146)
                battle['outcome']='victory'
                battle['extended']['withdrawn']='defenders' if not routed else None
                old_target,old_home=target.grain,home.grain
                attackers=battle['extended']['supply']['sides']['attackers']['remaining']
                defenders=battle['extended']['supply']['sides']['defenders']['remaining']
                report=battle_supply.settle(game,state,battle)
                self.assertEqual(target.grain-old_target,attackers+(defenders if routed else 0))
                self.assertEqual(home.grain-old_home,0 if routed else defenders)
                self.assertEqual(report[1]['city'],target.id if routed else home.id)

    def test_overflow_is_explicit_loss_and_legacy_results_never_get_refunds(self):
        game = direct_battle(); state = game.state; battle = state.battle
        battle['outcome']='retreat';battle['extended']['withdrawn']='attackers'
        state.cities['xiangyang'].grain = battle_supply.LIMIT
        remaining = battle['extended']['supply']['sides']['attackers']['remaining']
        report = battle_supply.settle(game,state,battle)
        self.assertEqual((report[0]['stored'],report[0]['lost']),(0,remaining))
        battle['extended'].pop('supply'); before = deepcopy(state.cities)
        self.assertEqual(battle_supply.settle(game,state,battle),[])
        self.assertEqual(state.cities,before)

    def test_tampered_receipts_are_rejected_atomically_and_partial_days_resume(self):
        game = direct_battle()
        with patch('remake.tactical_ai.choose_action',return_value=WAIT):
            command(game,'battle_wait',battle_id=game.state.battle['id'])
        saved = game.export_save()
        restored = Campaign(game.catalog); restored.load_save(saved,0)
        self.assertEqual(restored.export_save(),saved)
        for field in ('remaining','consumed','credit_units'):
            bad = deepcopy(game.state)
            bad.battle['extended']['supply']['sides']['attackers'][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                game.validate(bad)
        bad = deepcopy(game.state)
        bad.battle['extended']['supply']['sides']['defenders']['journal'][0]['units'] += 1000
        with self.assertRaises(ValueError):
            game.validate(bad)
        self.assertEqual(game.export_save(),saved)

    def test_current_development_march_hunger_and_settlement_have_full_backend_parity(self):
        """Current services stay enabled outside every historical oracle context."""
        games = [Campaign(controlled_catalog()),Campaign(controlled_catalog())]
        backends = ('python','rust')

        def dispatch(kind, **payload):
            for index, backend in enumerate(backends):
                with using_backend(backend):
                    command(games[index],kind,**payload)
                    saved=games[index].export_save()
                # Every actual command crosses into the other backend through
                # the complete same-catalog JSON save, without normalization.
                with using_backend(backends[1-index]):
                    restored=Campaign(games[index].catalog)
                    restored.load_save(deepcopy(saved),0)
                    self.assertEqual(restored.export_save(),saved)
                    self.assertEqual(restored.state.rng,games[index].state.rng)
                games[index]=restored
            self.assertEqual(games[0].to_dict(),games[1].to_dict())
            self.assertEqual(games[0].export_save(),games[1].export_save())
            self.assertEqual(games[0].state.rng,games[1].state.rng)

        dispatch('new',faction='shu',seed=2026)
        land=games[0].state.extension['city_development']['cities']['xiangyang']['land']
        dispatch('develop_land',city='xiangyang',actor=999)
        self.assertGreater(games[0].state.extension['city_development']['cities']['xiangyang']['land'],land)
        dispatch('depart',source='xiangyang',target='nanyang',officers=[146],battle_grain=0)
        self.assertEqual(games[0].state.extension['travel']['marches'][0]['supply']['loaded'],1)
        for _ in range(30):
            state=games[0].state
            if state.phase=='battle':break
            if state.phase=='city':dispatch('end_turn')
            elif state.phase=='ai':dispatch('ai',turn=state.turn)
            elif state.phase=='arrivals':dispatch('arrivals')
            else:self.fail('Unexpected actual campaign transition: '+state.phase)
        else:self.fail('The real departure never reached battle')
        self.assertIn('supply',games[0].state.battle['extended'])
        self.assertEqual(games[0].state.battle['extended']['supply']['sides']['attackers']['initial_credit'],720)
        with patch('remake.tactical_ai.choose_action',return_value=WAIT):
            for _ in range(3):
                dispatch('battle_wait',battle_id=games[0].state.battle['id'])
        self.assertEqual(games[0].state.phase,'result')
        self.assertEqual(games[0].state.battle['outcome'],'retreat')
        self.assertEqual(games[0].state.battle['extended']['supply']['days'],3)
        dispatch('settle',battle_id=games[0].state.battle['id'])
        self.assertIsNone(games[0].state.battle)


if __name__ == '__main__':
    unittest.main()
