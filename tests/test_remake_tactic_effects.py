"""Source fire-arrow/conversion formulas, paid effects and replayable grain."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from remake import battle_grid, battle_supply, tactic_effects, tactical_ai
from remake.campaign import Campaign, SeedRng, digest
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from campaign_fixtures import arrange_tactic
from test_remake_tactical_ai import battle, actors
from test_remake_battle_supply import direct_battle, advance_day


def command(game, kind, **payload):
    return game.command(kind, payload, game.revision)


def prepared(tid, side='attackers'):
    # Hold only automatic opening responses so each side's actual paid command
    # can be checked independently. Cells, rosters and validators remain real.
    with patch.object(Campaign, '_run_tactical_ai_turn', return_value=None):
        game = battle(spell=tid, player='shu' if side == 'attackers' else 'wei')
    b = game.state.battle
    foe = 'defenders' if side == 'attackers' else 'attackers'
    actor, target = b[side][0], b[foe][0]
    if tid == 8:
        target = next(unit for unit in b[foe] if unit['id'] not in game.state.extension['leaders'].values())
    arrange_tactic(game, tid, actor, target)
    # A legal carried AP balance avoids an unrelated automatic side response.
    b['extended']['tactical']['side'] = side
    b['extended']['tactical']['points'][side] = 20
    game.validate(game.state)
    return game, actor, target, side, foe


def seed_for(predicate):
    return next(seed for seed in range(1, 10000) if predicate(SeedRng(seed).next()%100))


class TacticFormulaTests(unittest.TestCase):
    def test_conversion_all_loyalty_and_tier_boundaries(self):
        # Independently calculated boundary vectors for the recovered formula;
        # these are not new CPU/original-instruction execution experiments.
        vectors = (
            ((40, 50, 2, 0, 2), 69),
            ((40, 50, 2, 30, 2), 69),  # Last60-base loyalty, plus9.
            ((40, 50, 2, 31, 2), 39),  # First30-base loyalty, plus9.
            ((40, 50, 2, 50, 2), 39),
            ((40, 50, 2, 51, 2), 19),  # First10-base loyalty, plus9.
            ((40, 50, 2, 70, 2), 19),
            ((40, 50, 2, 71, 2), 0),
            ((40, 50, 2, 100, 2), 0),  # Internal ruler loyalty sentinel.
            ((4, 5, 0, 30, 0), 60),   # Knowledge+virtue9: no whole ten.
            ((5, 5, 0, 30, 0), 61),   # Exactly10.
            ((5, 6, 0, 30, 0), 61),   #11 still contributes only1.
            ((44, 55, 0, 30, 0), 69), #99 contributes9.
            ((45, 55, 0, 30, 0), 70), #100 contributes10.
            ((40, 50, 4, 50, 1), 45), # Three positive tiers add6.
            ((40, 50, 1, 50, 4), 39), # A negative tier gap subtracts nothing.
            ((0, 0, 0, 70, 7), 10),
            ((99, 99, 7, 30, 0), 93), # Maximum19 stat points+14 tier points.
            ((99, 99, 7, 70, 0), 43),
            ((99, 99, 7, 71, 0), 0),  # Guaranteed failure precedes bonuses.
        )
        for inputs, expected in vectors:
            with self.subTest(inputs=inputs):
                self.assertEqual(tactic_effects.conversion_threshold(*inputs), expected)

    def test_fire_separate_floors_all_rolls_and_saturating_requested_amount(self):
        # Hand-calculated recovered-formula vectors, not a CPU oracle. Keep the
        # expected amounts literal so production arithmetic is not its own test.
        vectors = (
            ((0, 0, 0), 0),
            ((0, 99, 4), 19),  # Requested loss; the separate ledger clamps to0.
            ((1, 0, 4), 0),
            ((1, 99, 0), 19),  # Requested loss can exceed the actual one grain.
            ((11, 9, 4), 2),   #1.54 and1.8 floor separately to1+1, not3.
            ((199, 14, 3), 27),#25.87 and2.8 floor to25+2, not28.
            ((100, 4, 0), 10),
            ((100, 5, 0), 11),
            ((100, 9, 0), 11),
            ((100, 10, 0), 12),
            ((101, 26, 0), 15),# All five accepted percentage rolls.
            ((101, 26, 1), 16),
            ((101, 26, 2), 17),
            ((101, 26, 3), 18),
            ((101, 26, 4), 19),
            ((65535, 99, 0), 6572),
            ((65535, 99, 1), 7227),
            ((65535, 99, 2), 7883),
            ((65535, 99, 3), 8538),
            ((65535, 99, 4), 9193),
            ((battle_supply.LIMIT, 99, 0), 10000019),
            ((battle_supply.LIMIT, 99, 4), 14000019),
        )
        for inputs, expected in vectors:
            with self.subTest(inputs=inputs):
                self.assertEqual(tactic_effects.fire_arrow_requested(*inputs), expected)
        for args in ((True, 99, 0), (-1, 99, 0), (1, 100, 0), (1, 99, 5), (1, 99, -1), (1, 99, 0.0)):
            with self.assertRaises(ValueError):
                tactic_effects.fire_arrow_requested(*args)
        for args in ((True, 99, 0, 30, 0), (99, 99, 8, 30, 0), (99, 99, 0, 101, 0)):
            with self.assertRaises(ValueError):
                tactic_effects.conversion_threshold(*args)


class FireArrowCampaignTests(unittest.TestCase):
    def test_pure_legacy_and_current_preview_never_loads_or_draws(self):
        for legacy in (False, True):
            game, actor, target, own, foe = prepared(5)
            if legacy:
                del game.state.battle['extended']['supply']
            before = game.export_save()
            with patch.object(SeedRng, 'next', side_effect=AssertionError('preview RNG')):
                quote = tactic_effects.preview(game.state, game.state.battle, actor, target, own, foe, 5)
                info = battle_supply.view(game.state, game.state.battle)
            self.assertEqual(quote['schema'], tactic_effects.SCHEMA)
            self.assertEqual(quote['affected_side'], foe)
            self.assertLessEqual(quote['grain_loss_min'], quote['grain_loss_mean'])
            self.assertLessEqual(quote['grain_loss_mean'], quote['grain_loss_max'])
            self.assertEqual(info['sides'][foe]['burned'], 0)
            self.assertEqual(game.export_save(), before)
            restored = Campaign(game.catalog)
            restored.load_save(before, 0)
            self.assertEqual(restored.export_save(), before)

    def test_both_sides_burn_only_opponent_bags_after_success_with_two_draws(self):
        for own in battle_supply.SIDES:
            with self.subTest(side=own):
                game, actor, target, own, foe = prepared(5, own)
                state, b = game.state, game.state.battle
                chance = tactic_effects.success_chance(state,b,actor,target)
                state.rng = SeedRng(seed_for(lambda roll: roll < chance))
                expected_rng = deepcopy(state.rng)
                self.assertLess(expected_rng.next()%100, chance)
                factor = expected_rng.next()%5
                before = deepcopy(state)
                grain = battle_supply.available(state, b, foe)
                loss = min(grain, tactic_effects.fire_arrow_requested(grain, state.officers[actor['id']].profile.intellect, factor))
                command(game, 'tactic', battle_id=b['id'], actor=actor['id'], target=target['id'], tactic=5)
                state, current = game.state, game.state.battle
                self.assertEqual(state.rng, expected_rng)
                self.assertEqual(state.cities, before.cities, 'A battlefield fire must not burn either city warehouse')
                self.assertEqual(current['attackers'], before.battle['attackers'])
                self.assertEqual(current['defenders'], before.battle['defenders'])
                self.assertEqual(current['extended']['support'], before.battle['extended']['support'])
                self.assertEqual(current['extended']['supply']['sides'][own], before.battle['extended']['supply']['sides'][own])
                row = current['extended']['supply']['sides'][foe]
                self.assertEqual(row['remaining'], grain-loss)
                self.assertEqual((row['credit_units'], row['consumed'], row['received']), (0, 0, 0))
                self.assertEqual(battle_supply.burned(row), loss)
                self.assertEqual(current['extended']['tactical']['points'][own], 12)
                event = state.extension['events']['items'][-1]
                self.assertEqual(event['details'], dict(tactic=5, success=True, affected_side=foe,
                    grain_before=grain, grain_after=grain-loss, grain_loss=loss))
                game.validate(state)
                frozen = game.export_save()
                restored = Campaign(game.catalog)
                restored.load_save(frozen, 0)
                self.assertEqual(restored.export_save(), frozen)

    def test_failure_pays_eight_ap_and_draws_no_percentage_factor(self):
        game, actor, target, own, foe = prepared(5)
        state, b = game.state, game.state.battle
        chance = tactic_effects.success_chance(state,b,actor,target)
        state.rng = SeedRng(seed_for(lambda roll: roll >= chance))
        before = deepcopy(state)
        command(game, 'tactic', battle_id=b['id'], actor=actor['id'], target=target['id'], tactic=5)
        state = game.state
        self.assertEqual(state.rng.draws, before.rng.draws+1)
        self.assertEqual(state.battle['extended']['supply'], before.battle['extended']['supply'])
        self.assertEqual(state.cities, before.cities)
        self.assertEqual(state.battle['extended']['tactical']['points'][own], 12)
        details = state.extension['events']['items'][-1]['details']
        self.assertFalse(details['success'])
        self.assertEqual((details['grain_loss'], details['grain_before']), (0, details['grain_after']))

    def test_empty_grain_success_still_draws_factor_without_empty_receipt(self):
        game, actor, target, own, foe = prepared(5)
        b, state = game.state.battle, game.state
        row = b['extended']['supply']['sides'][foe]
        battle_supply.destroy(state, b, foe, row['remaining'])
        journal = deepcopy(row['journal'])
        state.rng = SeedRng(seed_for(lambda roll: roll < tactic_effects.general_chance(state.officers[actor['id']], state.officers[target['id']])))
        command(game, 'tactic', battle_id=b['id'], actor=actor['id'], target=target['id'], tactic=5)
        self.assertEqual(game.state.rng.draws, 2)
        self.assertEqual(game.state.battle['extended']['supply']['sides'][foe]['journal'], journal)
        self.assertEqual(game.state.extension['events']['items'][-1]['details']['grain_loss'], 0)


class ConversionCampaignTests(unittest.TestCase):
    def test_loyal71_and_above_is_payable_failure_with_no_rng_or_transfer(self):
        for loyalty in (71, 80, 99, 100):
            game, actor, target, own, foe = prepared(8)
            state, b = game.state, game.state.battle
            state.officers[target['id']].loyalty = loyalty
            before = deepcopy(state)
            self.assertEqual(tactical_ai.tactic_reason(state, b, actor, target, own, foe, 'plain', TACTICS[8]), '')
            with patch.object(SeedRng, 'next', side_effect=AssertionError('Guaranteed conversion failure must not draw')):
                quote = tactic_effects.preview(state, b, actor, target, own, foe, 8)
                command(game, 'tactic', battle_id=b['id'], actor=actor['id'], target=target['id'], tactic=8)
            current = game.state
            self.assertEqual(quote['success_percent'], 0)
            self.assertEqual(quote['failure_rng_draws'], 0)
            self.assertEqual(current.rng, before.rng)
            self.assertEqual(current.officers, before.officers)
            self.assertEqual(current.cities, before.cities)
            self.assertEqual(current.battle[foe], before.battle[foe])
            self.assertEqual(current.battle['extended']['tactical']['points'][own], 10)
            details = current.extension['events']['items'][-1]['details']
            self.assertEqual(details, dict(tactic=8, success=False, success_percent=0,
                                          target_loyalty=loyalty, guaranteed_failure=True))
            game.validate(current)

    def test_loyal70_uses_one_draw_and_same_immediate_conversion_service(self):
        for passed in (False, True):
            game, actor, target, own, foe = prepared(8)
            state, b = game.state, game.state.battle
            state.officers[target['id']].loyalty = 70
            chance = tactic_effects.conversion_chance(state.officers[actor['id']], state.officers[target['id']])
            state.rng = SeedRng(seed_for(lambda roll: (roll < chance) == passed))
            before = deepcopy(state)
            command(game, 'tactic', battle_id=b['id'], actor=actor['id'], target=target['id'], tactic=8)
            current = game.state
            self.assertEqual(current.rng.draws, 1)
            self.assertEqual(current.battle['extended']['tactical']['points'][own], 10)
            self.assertEqual(target['id'] in [unit['id'] for unit in current.battle[own]], passed)
            self.assertEqual(sum(unit['troops'] for side in battle_supply.SIDES for unit in current.battle[side]),
                             sum(unit['troops'] for side in battle_supply.SIDES for unit in before.battle[side]))
            self.assertEqual(current.battle['extended']['supply'], before.battle['extended']['supply'])
            event = next(item for item in reversed(current.extension['events']['items']) if item['kind'] == 'tactic')
            self.assertEqual(event['details']['success_percent'], chance)
            game.validate(current)

    def test_ai_excludes_guaranteed_failure_without_removing_player_legality(self):
        game, actor, target, own, foe = prepared(8)
        state, b = game.state, game.state.battle
        for unit in b[foe]:
            state.officers[unit['id']].loyalty = 80
        before = deepcopy(state)
        with patch.object(SeedRng, 'next', side_effect=AssertionError('AI lookahead')):
            self.assertIn(8, tactical_ai.legal_tactics(state, b, actor, target, own, foe, 'plain', TACTICS))
            rows = tactical_ai.candidates(state, b, own, foe, 'plain', TACTICS, depth=2)
            choice = tactical_ai.choose_action(state, b, own, foe, 'plain', TACTICS)
        self.assertFalse(any(row['kind'] == 'tactic' and row['tactic'] == 8 for row in rows))
        self.assertFalse(choice and choice['kind'] == 'tactic' and choice['tactic'] == 8)
        self.assertEqual(state, before)


class BurnLedgerTests(unittest.TestCase):
    def test_fire_market_meals_credit_and_settlement_conserve_actual_grain(self):
        game = direct_battle()
        state, b = game.state, game.state.battle
        row = b['extended']['supply']['sides']['attackers']
        world = sum(city.grain for city in state.cities.values())+sum(side['remaining'] for side in b['extended']['supply']['sides'].values())
        advance_day(game)
        credit = row['credit_units']
        self.assertEqual(battle_supply.destroy(state, b, 'attackers', 2), 2)
        self.assertEqual(row['credit_units'], credit)
        # This direct delivery isolates the ledger; physical market payment and
        # city debit use the separately covered shared battlefield facility.
        battle_supply.receive(state, b, 'attackers', 5)
        world += 5
        self.assertEqual(battle_supply.destroy(state, b, 'attackers', 100), row['loaded']-1-2+5)
        self.assertEqual(row['credit_units'], credit)
        self.assertEqual(battle_supply.destroy(state, b, 'attackers', 100), 0)
        self.assertEqual(row['loaded']+row['received'], row['consumed']+row['remaining']+battle_supply.burned(row))
        battle_supply.validate(state, b)
        while state.phase == 'battle':
            advance_day(game)
        self.assertEqual((b['outcome'], b['extended']['withdrawn']), ('retreat', 'attackers'))
        consumed = sum(side['consumed'] for side in b['extended']['supply']['sides'].values())
        destroyed = sum(battle_supply.burned(side) for side in b['extended']['supply']['sides'].values())
        command(game, 'settle', battle_id=b['id'])
        self.assertEqual(sum(city.grain for city in game.state.cities.values())+consumed+destroyed, world)
        self.assertEqual(battle_supply.settle(game, game.state, b), b['extended']['supply']['settlement'])

    def test_tampered_fire_balances_clocks_and_duplicate_counter_are_atomic(self):
        game = direct_battle()
        b = game.state.battle
        battle_supply.destroy(game.state, b, 'defenders', 2)
        saved = game.export_save()
        for mutation in ('negative', 'bool', 'overdraw', 'day', 'balance', 'counter'):
            with self.subTest(mutation=mutation):
                invalid = deepcopy(saved)
                row = invalid['state']['battle']['extended']['supply']['sides']['defenders']
                if mutation == 'negative':row['journal'][0]['grain'] = -1
                elif mutation == 'bool':row['journal'][0]['grain'] = True
                elif mutation == 'overdraw':row['journal'][0]['grain'] = row['loaded']+1
                elif mutation == 'day':row['journal'][0]['day'] = 1
                elif mutation == 'balance':row['remaining'] += 1
                else:row['burned'] = 2
                invalid['checksum'] = digest({key: value for key, value in invalid.items() if key != 'checksum'})
                with self.assertRaises(GameError):
                    game.load_save(invalid, game.revision)
                self.assertEqual(game.export_save(), saved)
        # Invalid arguments do not even initialize an old missing ledger.
        del b['extended']['supply']
        before = deepcopy(game.state)
        for value in (-1, True, '1', 1.0, battle_supply.LIMIT+1):
            with self.assertRaises(ValueError):battle_supply.destroy(game.state, b, 'attackers', value)
        self.assertEqual(game.state, before)


if __name__ == '__main__':
    unittest.main()
