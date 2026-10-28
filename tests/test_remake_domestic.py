"""Faction offices, local cost boundaries, saved receipts and automatic targets."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import domestic, logistics
from remake.officers import YearState, year_state
from campaign_fixtures import controlled_catalog


def domestic_catalog():
    data = deepcopy(controlled_catalog().data)
    data['id'] = 'controlled-domestic'
    data['initial_owners']['nanjun'] = 'shu'
    data['initial_officers'] = [r for r in data['initial_officers'] if r['city'] != 'nanjun']
    already = {r['person_id'] for r in data['initial_officers']}
    source = controlled_catalog()
    candidates = [r for r in data['people'] if r['person_id'] not in already
        and year_state(source.definitions[r['person_id']], data['start_year']) == YearState.AVAILABLE]
    martial = max(candidates, key=lambda r: r['profile']['martial_strength'])
    intellect = max((r for r in candidates if r['person_id'] != martial['person_id']),
                    key=lambda r: r['profile']['intellect'])
    data['initial_free_officers'] = [dict(person_id=r['person_id'], city='nanjun') for r in (martial, intellect)]
    # Isolate turn logic from any fortuitous persuasion targets.
    data['rules']['persuade_officer_gold'] = 100000000
    data['city_income']['xiangyang'] = dict(gold=100, grain=300, reserves=0)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'domestic.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class DomesticTests(unittest.TestCase):
    def game(self):
        game = Campaign(domestic_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        return game

    def appoint(self, game, policy=None):
        ids = game.state.cities['xiangyang'].roster.officer_ids
        civil = max(ids, key=lambda i: game.state.officers[i].profile.intellect)
        military = max((i for i in ids if i != civil), key=lambda i: game.state.officers[i].profile.martial_strength)
        game.command('set_domestic', dict(faction='shu', civil=civil, military=military,
            policy=policy or {}), game.revision)
        return civil, military

    def fails(self, game, payload):
        before, revision = game.export_save(), game.revision
        with self.assertRaises((GameError, ValueError)):
            game.command('set_domestic', payload, revision)
        self.assertEqual(game.export_save(), before)
        self.assertEqual(game.revision, revision)

    def test_distinct_roles_malformed_policies_and_pure_bilingual_inputs(self):
        game = self.game()
        a, b = self.appoint(game)
        for payload in (
                dict(faction='shu', military=a), dict(faction='shu', civil=True),
                dict(faction=[], civil=a), dict(faction='shu', policy={'budget': -1}),
                dict(faction='shu', policy={'task_order': ['personnel'] * 3}),
                dict(faction='shu', policy={'excluded_targets': [a, a]}),
                dict(faction='shu', policy={'envoy': True}),
                dict(faction='shu', policy={'unknown': True})):
            self.fails(game, payload)
        before = game.export_save()
        for _ in range(3):
            domestic.view(game, game.state)
            logistics.view(game, game.state)
        self.assertEqual(game.export_save(), before)
        self.assertEqual(game.state.rng.draws, 0)

    def test_three_real_ten_day_duties_add_exact_monthly_bonus_once(self):
        game = self.game()
        civil, _ = self.appoint(game)
        intellect = game.state.officers[civil].profile.intellect
        city = game.state.cities['xiangyang']
        start = city.gold, city.grain
        for _ in range(3):
            domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
            snapshot = game.export_save()
            domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
            self.assertEqual(game.export_save(), snapshot)
            game._complete_turn(game.state)
        bonus = (100 * 40 * intellect // (100 * 99), 300 * 40 * intellect // (100 * 99))
        self.assertEqual((city.gold, city.grain), (start[0] + 100 + bonus[0], start[1] + 300 + bonus[1]))
        snapshot = game.export_save()
        domestic.month_rollover(game, game.state)
        self.assertEqual(game.export_save(), snapshot)
        self.assertEqual(len([e for e in game.state.extension['events']['items']
            if e['kind'] == 'domestic_report' and e['details']['reason'] == 'month']), 1)
        game.validate(game.state)

    def test_recruiting_costs_reserve_target_morale_and_training_are_bounded(self):
        game = self.game()
        _, military = self.appoint(game, dict(recruit_enabled=True, training_enabled=True,
            reserve_target=1300, gold_floor=0, grain_floor=0))
        city, row = game.state.cities['xiangyang'], game.state.extension['domestic']['cities']['xiangyang']
        strength = game.state.officers[military].profile.martial_strength
        quote = domestic.recruitment_preview(game, game.state, city.id)
        self.assertEqual(quote['soldiers'], 100)
        self.assertEqual(quote['gold'], 20 - strength // 10)
        before = city.gold, city.grain, city.reserves, game.state.soldiers['recruited']
        troops_before = sum(game.state.officers[i].troops for i in city.roster.officer_ids)
        expected_recruited = sum(domestic.recruitment_preview(game, game.state, key)['soldiers']
            for key, c in game.state.cities.items() if c.owner == 'shu')
        domestic.finish_faction_turn(game, game.state, 'shu')
        self.assertEqual(city.reserves + sum(game.state.officers[i].troops for i in city.roster.officer_ids),
                         before[2] + troops_before + 100)
        self.assertEqual(game.state.soldiers['recruited'], before[3] + expected_recruited)
        self.assertLess(city.gold, before[0]); self.assertLess(city.grain, before[1])
        self.assertTrue(0 <= row['morale'] <= 100)
        self.assertTrue(city.action_used)
        saved = game.export_save()
        domestic.finish_faction_turn(game, game.state, 'shu')
        self.assertEqual(game.export_save(), saved)
        row['morale'] = 100
        self.assertEqual(domestic.training_preview(game, game.state, city.id), dict(gain=0, gold=0, grain=0))
        city.gold, city.grain = 0, 0
        game.state.extension['domestic']['factions']['shu']['policy']['reserve_target'] = 2000
        self.assertEqual(domestic.recruitment_preview(game, game.state, city.id)['soldiers'], 0)
        self.assertGreaterEqual(city.gold, 0); self.assertGreaterEqual(city.grain, 0)

    def test_personnel_ranks_real_abilities_and_reuses_actual_fee_and_rng(self):
        game = self.game()
        civil, _ = self.appoint(game, dict(auto_recruit=True, auto_persuade=True, gold_floor=0, min_chance=0))
        row = game.state.extension['domestic']['factions']['shu']
        candidates = domestic.personnel_targets(game, game.state, 'xiangyang')
        self.assertTrue(candidates)
        self.assertTrue(all(r['method'] == 'recruit_officer' for r in candidates), 'Unaffordable custom persuasion fee must not pass a hardcoded100 budget')
        for priority, field in [('martial', 'martial_strength'), ('intellect', 'intellect'), ('virtue', 'virtue')]:
            row['policy']['priority'] = priority
            choices = domestic.personnel_targets(game, game.state, 'xiangyang')
            self.assertEqual(getattr(game.state.officers[choices[0]['id']].profile, field),
                max(getattr(game.state.officers[c['id']].profile, field) for c in choices))
        chosen = domestic.faction_personnel_targets(game, game.state, 'shu')[0]
        gold = sum(c.gold for c in game.state.cities.values() if c.owner == 'shu')
        draws = game.state.rng.draws
        game.command('end_turn', {}, game.revision)
        self.assertEqual(game.state.rng.draws, draws + 2)
        self.assertEqual(sum(c.gold for c in game.state.cities.values() if c.owner == 'shu'), gold - 180)
        orders = game.state.extension['command_books']['factions']['shu']['orders']
        self.assertEqual([row['kind'] for row in orders], ['recruit_officer', 'recruit_officer', 'hire_staff'])
        self.assertEqual(game.state.extension['command_books']['factions']['shu']['used'], 3)
        self.assertEqual(game.state.extension['officer_actions'][str(civil)], game.state.turn)
        self.assertFalse(domestic.can_attempt(game.state, 'shu', chosen['id']))
        self.assertNotIn(chosen['id'], [r['id'] for r in domestic.personnel_targets(game, game.state, 'xiangyang')])
        game.validate(game.state)

    def test_manual_order_leaves_only_the_remaining_shared_budget_for_automatic_work(self):
        game = self.game()
        self.appoint(game, dict(auto_recruit=True, recruit_enabled=True, training_enabled=False))
        city = game.state.cities['xiangyang']
        game.command('recruit', dict(city=city.id), game.revision)
        city = game.state.cities['xiangyang']
        before = city.gold, city.grain, city.reserves, game.state.rng.draws
        troops_before = sum(game.state.officers[i].troops for i in city.roster.officer_ids)
        domestic.finish_faction_turn(game, game.state, 'shu')
        self.assertEqual((city.gold, city.grain), before[:2])
        self.assertEqual(city.reserves + sum(game.state.officers[i].troops for i in city.roster.officer_ids),
                         before[2] + troops_before, 'Free passive allocation cannot duplicate a used city action')
        self.assertFalse(any(r['city'] == city.id and r['kind'] in {'recruit', 'personnel'}
            for r in game.state.extension['domestic']['reports']))
        self.assertEqual(game.state.rng.draws, before[3] + 2,
            'The two remaining orders allow two target attempts in another owned city')
        self.assertEqual(game.state.extension['command_books']['factions']['shu']['used'], 3)

    def test_appointments_pause_on_march_and_income_is_half_when_actor_busy(self):
        game = self.game()
        civil, _ = self.appoint(game)
        row = game.state.extension['domestic']['cities']['xiangyang']
        game.state.extension['officer_actions'][str(civil)] = game.state.turn
        domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
        self.assertEqual(row['income_points'], game.state.officers[civil].profile.intellect)
        game._complete_turn(game.state)
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[civil], route_mode='land'), game.revision)
        row = game.state.extension['domestic']['cities']['xiangyang']
        before = row['income_points']
        domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
        self.assertEqual(row['income_points'], before)
        self.assertFalse(domestic.view(game, game.state)['cities']['xiangyang']['civil_active'])

    def test_paused_offices_and_envoy_do_not_block_unrelated_policy_updates(self):
        game = self.game()
        civil, military = self.appoint(game)
        game.command('set_domestic', dict(faction='shu', policy=dict(envoy=civil)), game.revision)
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[civil], route_mode='land'), game.revision)
        game.command('set_domestic', dict(faction='shu', civil=civil, military=military,
            policy=dict(budget=250, envoy=civil)), game.revision)
        row = game.state.extension['domestic']['factions']['shu']
        self.assertEqual(row['policy']['budget'], 250)
        self.assertEqual(row['civil'], civil)
        self.assertFalse(domestic.view(game, game.state)['cities']['xiangyang']['civil_active'])
        game.validate(game.state)

    def test_boolean_envoy_cannot_alias_an_existing_integer_person(self):
        game = self.game()
        # Python dictionary membership considers True == 1; strict person-ref
        # parsing must reject it even when such a historical ID exists.
        game.state.officers[1] = game.state.officers[999]
        self.assertIn(True, game.state.officers)
        policy = deepcopy(domestic.DEFAULT_POLICY)
        policy['envoy'] = True
        with self.assertRaises(ValueError):
            domestic._validate_policy(game, game.state, policy)

    def test_historical_id_zero_remains_a_valid_explicit_envoy(self):
        game = self.game()
        civil, _ = self.appoint(game)
        envoy = deepcopy(game.state.officers[999]); envoy.runtime_id = 0
        game.state.officers[0] = envoy
        city = game.state.cities['xiangyang']; city.roster.officer_ids.append(0)
        game.catalog.data['rules']['persuade_officer_gold'] = 100
        row = game.state.extension['domestic']['factions']['shu']
        row['policy'].update(auto_persuade=True, envoy=0, min_chance=0)
        with patch.object(game, '_persuadable', return_value=[123]):
            targets = domestic.personnel_targets(game, game.state, city.id)
        self.assertTrue(targets)
        self.assertEqual(targets[0]['actor'], 0)
        self.assertNotEqual(targets[0]['actor'], civil)

    def test_saved_receipts_and_signed_tampering_reject_atomically(self):
        game = self.game()
        self.appoint(game, dict(training_enabled=True))
        domestic.finish_faction_turn(game, game.state, 'shu')
        saved = game.export_save()
        loaded = Campaign(game.catalog); loaded.load_save(saved, 0)
        self.assertEqual(loaded.export_save(), saved)
        for change in ('morale', 'income', 'dual', 'receipt', 'policy'):
            altered = deepcopy(saved)
            row = altered['state']['extension']['domestic']['cities']['xiangyang']
            if change == 'morale': row['morale'] = 101
            elif change == 'income': row['income_points'] = 595
            elif change == 'dual':
                offices = altered['state']['extension']['domestic']['factions']['shu']
                offices['military'] = offices['civil']
            elif change == 'receipt': row['last_work_turn'] += 1
            else: altered['state']['extension']['domestic']['factions']['shu']['policy']['budget'] = -1
            altered['checksum'] = digest({k: v for k, v in altered.items() if k != 'checksum'})
            before = loaded.export_save()
            with self.assertRaises(GameError): loaded.load_save(altered, loaded.revision)
            self.assertEqual(loaded.export_save(), before)


if __name__ == '__main__':
    unittest.main()
