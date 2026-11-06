"""Real phantom commands, completed days, cleanup and atomic save boundaries.

Controlled native-grid layouts and a waiting AI isolate each transaction. The
catalog, learned tactics, AP, RNG, damage, food, events and save validator are
real. Direct condition seeding is explicitly a precondition for cleanup tests,
not a substitute for the two-sided successful/failed cast coverage below.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from remake import battle_conditions as conditions, battle_grid, battle_supply, siege
from remake.campaign import Campaign, SeedRng, digest
from remake.errors import GameError
from campaign_fixtures import arrange_contact, arrange_tactic
from test_remake_tactical_ai import battle

WAIT = dict(kind='wait', actor=None, target=None, tactic=None, score=0)


def command(game, kind, **payload):
    return game.command(kind, payload, game.revision)


def seed_for(success=True):
    # Seed selection only; the command still calls the real SeedRng. These
    # bounds succeed/fail for either real fixture officer's retained gate.
    return next(seed for seed in range(1, 10000)
                if (SeedRng(seed).next()%100 < 5 if success
                    else SeedRng(seed).next()%100 >= 95))


def prepared(own='attackers'):
    # Suppress only automatic opening responses. Keep real identities, skills,
    # native terrain and position validation. The old shared fixture grants
    # Zhuge Liang his valid tier6; Xiahou Dun naturally knows tactic2 as well.
    with patch.object(Campaign, '_run_tactical_ai_turn', return_value=None):
        game = battle(spell=2, player='shu' if own == 'attackers' else 'wei')
    b = game.state.battle
    foe = 'defenders' if own == 'attackers' else 'attackers'
    actor, target = b[own][0], b[foe][0]
    arrange_tactic(game, 2, actor, target)
    b['extended']['tactical']['points'][own] = 20
    if own == 'defenders':
        # A real defending turn follows the already-passed attacker; retain
        # that fact so the next public wait is the same day's real boundary.
        b['extended']['tactical']['passed']['attackers'] = True
    game.validate(game.state)
    return game, actor['id'], target['id'], own, foe


def units(game, actor, target):
    b = game.state.battle
    all_units = {u['id']:u for side in battle_grid.SIDES for u in b[side]}
    return b, all_units[actor], all_units[target]


def cast(game, actor, target, tid=2, *, success=True):
    game.state.rng = SeedRng(seed_for(success))
    return command(game, 'tactic', battle_id=game.state.battle['id'],
                   actor=actor, target=target, tactic=tid)


def wait_day(game):
    # Only policy chooses WAIT. Both real side transitions, day advancement,
    # meal settlement, timeout and condition hooks still execute unchanged.
    with patch('remake.tactical_ai.choose_action', return_value=WAIT):
        return command(game, 'battle_wait', battle_id=game.state.battle['id'])


def rehash(saved):
    saved['checksum'] = digest({key:value for key,value in saved.items() if key != 'checksum'})
    return saved


class PhantomCampaignTests(unittest.TestCase):
    def test_both_sides_success_pay_four_ap_one_draw_without_other_damage_or_flags(self):
        for own, expected in (('attackers', 3), ('defenders', 2)):
            with self.subTest(side=own):
                game, actor, target, own, foe = prepared(own)
                b = game.state.battle
                b['extended']['support'][str(target)].update(stunned=1, guard=2)
                b['extended']['support'][str(actor)]['guard'] = 1
                game.state.rng = SeedRng(seed_for())
                before = deepcopy(game.state)
                expected_rng = deepcopy(before.rng)
                expected_rng.next()
                command(game, 'tactic', battle_id=b['id'], actor=actor, target=target, tactic=2)
                state, b = game.state, game.state.battle
                self.assertEqual(state.rng, expected_rng)
                self.assertEqual(b['extended']['tactical']['points'][own], 16)
                self.assertEqual(conditions.remaining(b, target), expected)
                self.assertEqual(conditions.view(b)['day'], b['round'])
                self.assertEqual(b['attackers'], before.battle['attackers'])
                self.assertEqual(b['defenders'], before.battle['defenders'])
                self.assertEqual(b['extended']['support'], before.battle['extended']['support'])
                self.assertEqual(b['extended']['supply'], before.battle['extended']['supply'])
                self.assertEqual(state.officers, before.officers)
                self.assertEqual(state.soldiers, before.soldiers)
                self.assertEqual(state.extension['command_books'], before.extension['command_books'])
                event = state.extension['events']['items'][-1]
                self.assertEqual(event['kind'], 'tactic')
                self.assertEqual(event['details'], dict(tactic=2, success=True,
                    condition='phantom', condition_count=expected))
                game.validate(state)

    def test_failed_cast_has_one_draw_and_no_new_extension_but_clears_old_target_first(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                game, actor, target, own, _ = prepared()
                b = game.state.battle
                if existing:
                    conditions.apply(b, target, own)  # Explicit prior condition fixture.
                before = deepcopy(b['extended']['support'])
                game.state.rng = SeedRng(seed_for(False))
                original_next = SeedRng.next
                # Observe the real candidate transaction at its first success
                # roll, proving the target was cleared before adjudication.
                def observing_draw(rng):
                    self.assertTrue(clearing.called)
                    candidate = clearing.call_args.args[0]
                    self.assertEqual(conditions.remaining(candidate.battle, target), 0)
                    return original_next(rng)
                with patch.object(game, '_clear_phantom', wraps=game._clear_phantom) as clearing, \
                        patch.object(SeedRng, 'next', observing_draw):
                    command(game, 'tactic', battle_id=b['id'], actor=actor, target=target, tactic=2)
                b = game.state.battle
                self.assertEqual(game.state.rng.draws, 1)
                self.assertEqual(b['extended']['tactical']['points'][own], 16)
                self.assertEqual(b['extended']['support'], before)
                self.assertEqual(conditions.remaining(b, target), 0)
                if existing:
                    self.assertEqual(conditions.view(b)['units'], {})
                else:
                    self.assertNotIn('conditions', b['extended'])
                self.assertEqual(game.state.extension['events']['items'][-1]['details'],
                    dict(tactic=2, success=False, condition='phantom', condition_count=0))
                game.validate(game.state)

    def test_rejected_before_payment_does_not_clear_target_or_spend_rng(self):
        game, actor, target, own, _ = prepared()
        b = game.state.battle
        conditions.apply(b, target, own)
        b['extended']['tactical']['points'][own] = 3
        before, revision = game.export_save(), game.revision
        with self.assertRaises(GameError):
            command(game, 'tactic', battle_id=b['id'], actor=actor, target=target, tactic=2)
        self.assertEqual(game.export_save(), before)
        self.assertEqual(game.revision, revision)

    def test_condition_blocks_public_move_atomically_but_other_targets_stay_selectable(self):
        game, actor, target, own, foe = prepared()
        info = game.view()['catalog']['battle_tactical']['actors'][str(actor)]
        destination = min(info['reachable'], key=lambda point:(point['cost'], point['y'], point['x']))
        conditions.apply(game.state.battle, actor, foe)  # Effect from a prior enemy cast.
        before = game.export_save()
        info = game.view()['catalog']['battle_tactical']['actors'][str(actor)]
        self.assertEqual(info['reachable'], [])
        self.assertIn('虛兵', info['move_reason'])
        self.assertTrue(info['can_act'])
        self.assertIn(target, info['attack_targets'])
        self.assertIn(target, info['tactic_targets']['2'])
        with self.assertRaises(GameError):
            command(game, 'battle_move', battle_id=game.state.battle['id'], actor=actor,
                    x=destination['x'], y=destination['y'])
        self.assertEqual(game.export_save(), before)

    def test_affected_attacker_enters_real_soldier_scene_clearing_only_selected_target(self):
        game, actor, target, own, foe = prepared()
        b = game.state.battle
        arrange_contact(game, b, actor, target)
        conditions.apply(b, actor, foe)
        conditions.apply(b, target, own)
        before = deepcopy(game.state.rng)
        # Actual begin() remains in place; the assertion observes its entry
        # to prove clearing occurs before the formation scene is constructed.
        original = siege.begin
        observed = []
        def observing_begin(current_game, state, acting, victim, context):
            observed.append(conditions.remaining(state.battle, victim['id']))
            return original(current_game, state, acting, victim, context)
        with patch('remake.siege.begin', side_effect=observing_begin):
            command(game, 'attack', battle_id=b['id'], actor=actor, target=target)
        b = game.state.battle
        self.assertEqual(observed, [0])
        self.assertEqual(conditions.remaining(b, actor), 2)
        self.assertEqual(conditions.remaining(b, target), 0)
        self.assertEqual(b['extended']['tactical']['points'][own], 18)
        self.assertEqual(b['extended']['siege']['mode'], 'field')
        self.assertEqual(b['extended']['siege']['stage'], 'formation')
        self.assertEqual(game.state.rng, before)
        command(game, 'siege_form', battle_id=b['id'], formation=3)
        self.assertEqual(conditions.remaining(game.state.battle, actor), 2)
        game.validate(game.state)

    def test_affected_actor_can_cast_real_phantom_without_losing_own_condition(self):
        game, actor, target, _, foe = prepared()
        conditions.apply(game.state.battle, actor, foe)
        cast(game, actor, target)
        self.assertEqual(conditions.remaining(game.state.battle, actor), 2)
        self.assertEqual(conditions.remaining(game.state.battle, target), 3)
        self.assertEqual(game.state.rng.draws, 1)
        self.assertEqual(game.state.battle['extended']['tactical']['points']['attackers'], 16)
        game.validate(game.state)

    def test_affected_actor_can_start_an_accepted_real_duel(self):
        game, actor, target, _, foe = prepared()
        arrange_contact(game, actor=actor, target=target)
        conditions.apply(game.state.battle, actor, foe)
        game.state.rng = SeedRng(seed_for())
        command(game, 'duel_start', battle_id=game.state.battle['id'], actor=actor, target=target)
        b = game.state.battle
        self.assertEqual(b['extended']['duel']['actor'], actor)
        self.assertEqual(b['extended']['duel']['target'], target)
        self.assertEqual(conditions.remaining(b, actor), 2)
        self.assertEqual(game.state.rng.draws, 1)
        self.assertEqual(b['extended']['tactical']['points']['attackers'], 18)
        game.validate(game.state)

    def test_half_day_keeps_count_then_each_real_full_day_expires_it_once(self):
        game, actor, target, _, _ = prepared()
        cast(game, actor, target)
        b = game.state.battle
        with patch.object(Campaign, '_run_tactical_ai_turn', return_value=None):
            command(game, 'battle_wait', battle_id=b['id'])
        b = game.state.battle
        self.assertEqual((b['round'], b['extended']['tactical']['side']), (1, 'defenders'))
        self.assertEqual(conditions.remaining(b, target), 3)
        self.assertEqual(conditions.view(b)['day'], 1)
        # Resume the actual AI runner with only its choice held at wait.
        with patch('remake.tactical_ai.choose_action', return_value=WAIT):
            game._run_tactical_ai_turn(game.state)
        self.assertEqual(game.state.battle['round'], 2)
        self.assertEqual(conditions.remaining(game.state.battle, target), 2)
        once = game.export_save()
        self.assertEqual(conditions.advance_daily(game.state, game.state.battle), [])
        self.assertEqual(game.export_save(), once)
        wait_day(game)
        self.assertEqual(conditions.remaining(game.state.battle, target), 1)
        wait_day(game)
        self.assertEqual(conditions.view(game.state.battle),
                         dict(schema=conditions.SCHEMA, day=4, units={}))
        self.assertTrue(any('虛兵效果消退' in text for text in game.state.battle['log']))
        game.validate(game.state)

    def test_defending_cast_loses_first_count_at_the_same_days_boundary(self):
        game, actor, target, _, _ = prepared('defenders')
        cast(game, actor, target)
        self.assertEqual(conditions.remaining(game.state.battle, target), 2)
        # Pause before the next attacker policy; do not consume a second side.
        with patch.object(Campaign, '_run_tactical_ai_turn', return_value=None):
            command(game, 'battle_wait', battle_id=game.state.battle['id'])
        b = game.state.battle
        self.assertEqual((b['round'], b['extended']['tactical']['side']), (2, 'attackers'))
        self.assertEqual(conditions.remaining(b, target), 1)
        self.assertEqual(conditions.view(b)['day'], 2)
        game.validate(game.state)

    def test_food_exhaustion_ends_battle_before_condition_tick(self):
        game, actor, target, own, _ = prepared()
        cast(game, actor, target)
        b = game.state.battle
        row = b['extended']['supply']['sides'][own]
        battle_supply.destroy(game.state, b, own, row['remaining'])
        before = deepcopy(conditions.view(b))
        rng = deepcopy(game.state.rng)
        wait_day(game)
        b = game.state.battle
        self.assertEqual((game.state.phase, b['outcome'], b['round']), ('result', 'retreat', 2))
        self.assertEqual(conditions.view(b), before)
        self.assertEqual(b['extended']['supply']['days'], 1)
        self.assertEqual(game.state.rng, rng)
        game.validate(game.state)

    def test_thirtieth_real_day_ends_before_new_phantom_is_decremented(self):
        game, actor, target, _, _ = prepared()
        for _ in range(29):
            wait_day(game)
        self.assertEqual(game.state.battle['round'], 30)
        cast(game, actor, target)
        before = deepcopy(conditions.view(game.state.battle))
        rng = deepcopy(game.state.rng)
        wait_day(game)
        b = game.state.battle
        self.assertEqual((game.state.phase, b['outcome'], b['round']), ('result', 'retreat', 31))
        self.assertEqual(b['extended']['supply']['days'], 30)
        self.assertEqual(conditions.view(b), before)
        self.assertEqual((before['day'], before['units'][str(target)]['remaining']), (30, 3))
        self.assertEqual(game.state.rng, rng)
        game.validate(game.state)

    def test_zero_bags_with_real_meal_credit_still_ticks(self):
        game, actor, target, own, _ = prepared()
        cast(game, actor, target)
        wait_day(game)
        b = game.state.battle
        row = b['extended']['supply']['sides'][own]
        self.assertGreaterEqual(row['credit_units'], battle_supply.daily_units(b, own))
        battle_supply.destroy(game.state, b, own, row['remaining'])
        self.assertEqual(row['remaining'], 0)
        credit = row['credit_units']
        wait_day(game)
        b = game.state.battle
        row = b['extended']['supply']['sides'][own]
        self.assertEqual(game.state.phase, 'battle')
        self.assertEqual((row['remaining'], row['credit_units']),
                         (0, credit-battle_supply.daily_units(b, own)))
        self.assertEqual((b['round'], conditions.remaining(b, target)), (3, 1))
        game.validate(game.state)

    def test_current_save_roundtrip_is_pure_and_continuation_is_identical(self):
        game, actor, target, _, _ = prepared()
        cast(game, actor, target)
        saved = game.export_save()
        game.view(); game.validate(game.state)
        self.assertEqual(game.export_save(), saved)
        restored = Campaign(game.catalog)
        restored.load_save(json.loads(json.dumps(saved)), 0)
        self.assertEqual(restored.export_save(), saved)
        wait_day(game); wait_day(restored)
        self.assertEqual(restored.export_save(), game.export_save())
        self.assertEqual(conditions.remaining(restored.state.battle, target), 2)

    def test_legacy_stunned_and_guard_load_without_inventing_phantom(self):
        for missing_grid in (False, True):
            with self.subTest(missing_grid=missing_grid):
                game, actor, _, _, _ = prepared()
                b = game.state.battle
                b['extended']['support'][str(actor)].update(stunned=1, guard=2)
                before = deepcopy(game.state)
                saved = game.export_save()
                if missing_grid:
                    saved['state']['battle']['extended'].pop('tactical')
                    saved['state']['battle']['extended'].pop('deployment', None)
                    rehash(saved)
                restored = Campaign(game.catalog)
                restored.load_save(saved, 0)
                self.assertNotIn('conditions', restored.state.battle['extended'])
                self.assertEqual(restored.state.battle['extended']['support'], before.battle['extended']['support'])
                self.assertEqual(restored.state.rng, before.rng)
                self.assertEqual(restored.state.officers, before.officers)
                self.assertEqual(restored.state.soldiers, before.soldiers)
                pure = restored.export_save()
                restored.view(); restored.validate(restored.state)
                self.assertEqual(restored.export_save(), pure)

    def test_rehashed_missing_grid_stale_day_and_foreign_ids_are_atomic(self):
        game, actor, target, _, _ = prepared()
        cast(game, actor, target)
        wait_day(game)
        saved, revision = game.export_save(), game.revision
        ids = {u['id'] for side in battle_grid.SIDES for u in game.state.battle[side]}
        foreign = next(i for i in game.state.officers if i not in ids)
        for problem in ('missing_grid', 'stale_day', 'future_day', 'bool_day', 'foreign_id', 'count4'):
            with self.subTest(problem=problem):
                invalid = deepcopy(saved)
                ext = invalid['state']['battle']['extended']
                if problem == 'missing_grid':
                    ext.pop('tactical'); ext.pop('deployment', None)
                elif problem == 'stale_day': ext['conditions']['day'] = 1
                elif problem == 'future_day': ext['conditions']['day'] = 3
                elif problem == 'bool_day': ext['conditions']['day'] = True
                elif problem == 'foreign_id': ext['conditions']['units'][str(foreign)] = dict(kind='phantom', remaining=1)
                else: ext['conditions']['units'][str(target)]['remaining'] = 4
                with self.assertRaises(GameError):
                    game.load_save(rehash(invalid), game.revision)
                self.assertEqual(game.export_save(), saved)
                self.assertEqual(game.revision, revision)

    def test_real_conversion_removes_condition_and_makes_officer_usable(self):
        game, actor, _, own, foe = prepared()
        b = game.state.battle
        target = next(u for u in b[foe] if u['id'] not in game.state.extension['leaders'].values())
        ident = target['id']
        arrange_tactic(game, 8, actor, target)
        game.state.officers[ident].loyalty = 30
        conditions.apply(b, ident, own)
        cast(game, actor, ident, tid=8)
        b = game.state.battle
        self.assertIn(ident, {u['id'] for u in b[own]})
        self.assertNotIn(ident, {u['id'] for u in b[foe]})
        self.assertEqual(game.state.officers[ident].faction_id, b['attacker'])
        self.assertEqual(conditions.remaining(b, ident), 0)
        self.assertTrue(game.view()['catalog']['battle_tactical']['actors'][str(ident)]['can_act'])
        game.validate(game.state)

    def test_area_damage_drops_nonselected_routed_units_condition(self):
        game, actor, target, own, foe = prepared()
        b = game.state.battle
        arrange_tactic(game, 7, actor, target)
        victim = next(u for u in b[foe] if u['id'] != target and u['troops'] <= 180)
        ident = victim['id']
        conditions.apply(b, ident, own)
        cast(game, actor, target, tid=7)
        b = game.state.battle
        victim = next(u for u in b[foe] if u['id'] == ident)
        self.assertEqual(victim['troops'], 0)
        self.assertEqual(conditions.remaining(b, ident), 0)
        self.assertNotIn(str(ident), conditions.view(b)['units'])
        game.validate(game.state)

    def test_actual_duel_hp_rout_cleans_the_defeated_units_condition(self):
        game, actor, target, own, _ = prepared()
        b = game.state.battle
        arrange_contact(game, b, actor, target)
        conditions.apply(b, target, own)
        # The opponent is already wounded. A real accepted challenge and
        # strike must route it; no HP/damage/duel-result function is mocked.
        b['extended']['support'][str(target)]['health'] = 1
        game.state.rng = SeedRng(seed_for())
        command(game, 'duel_start', battle_id=b['id'], actor=actor, target=target)
        self.assertEqual(conditions.remaining(game.state.battle, target), 3)
        game.state.rng = SeedRng(5)
        command(game, 'duel_action', battle_id=b['id'], move='strike')
        b, _, victim = units(game, actor, target)
        self.assertEqual(victim['troops'], 0)
        self.assertEqual(b['extended']['support'][str(target)]['health'], 1)
        self.assertEqual(conditions.remaining(b, target), 0)
        self.assertTrue(game.state.officers[target].alive, 'Battle HP defeat is a rout, not a fabricated historical death')
        game.validate(game.state)

    def test_shared_result_hook_cleans_an_explicitly_removed_slot(self):
        game, actor, target, own, foe = prepared()
        b = game.state.battle
        victim = next(u for u in b[foe] if u['id'] not in game.state.extension['leaders'].values())
        ident = victim['id']
        conditions.apply(b, ident, own)
        # Public damage retains routed identity slots. This explicit removal
        # boundary fixture checks the shared cleanup when another engine
        # service has actually removed a slot and its position/support rows.
        b[foe].remove(victim)
        b['extended']['support'].pop(str(ident))
        b['extended']['tactical']['positions'].pop(str(ident))
        # A real failed cast on a different live target completes the shared
        # result hook and ordinary city-governor reconciliation. The removed
        # victim is never the selected target's pre-effect clear.
        cast(game, actor, target, success=False)
        self.assertEqual(conditions.view(game.state.battle)['units'], {})
        game.validate(game.state)

    def test_self_ambush_clears_actor_not_the_ignored_enemy_target(self):
        game, actor, target, own, foe = prepared()
        b = game.state.battle
        arrange_tactic(game, 11, actor, target)
        conditions.apply(b, actor, foe)
        conditions.apply(b, target, own)
        before = deepcopy(game.state.rng)
        command(game, 'tactic', battle_id=b['id'], actor=actor, target=target, tactic=11)
        b = game.state.battle
        self.assertEqual(conditions.remaining(b, actor), 0)
        self.assertEqual(conditions.remaining(b, target), 3)
        self.assertEqual(b['extended']['ambush'], dict(actor=actor))
        self.assertEqual(b['extended']['tactical']['points'][own], 10)
        self.assertEqual(game.state.rng, before)
        game.validate(game.state)


if __name__ == '__main__':
    unittest.main()
