"""Two faction officials govern remote cities through the real shared services."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import civil_staff, domestic, logistics
from remake.officers import YearState, year_state
from campaign_fixtures import controlled_catalog


def faction_catalog(*, isolated_targets=False, empty_city=False, neutral_city=False):
    data = deepcopy(controlled_catalog().data)
    data['id'] = 'controlled-faction-offices'
    data['initial_owners']['nanjun'] = 'shu'
    data['city_income']['xiangyang'] = dict(gold=35, grain=90, reserves=0)
    data['city_income']['nanjun'] = dict(gold=100, grain=300, reserves=0)
    if empty_city:
        data['initial_officers'] = [r for r in data['initial_officers'] if r['city'] != 'nanjun']
        data['city_income']['nanjun'] = dict(gold=0, grain=0, reserves=0)
    if neutral_city:
        data['initial_owners']['nanjun'] = 'neutral'
    if isolated_targets:
        # The first city by ID cannot reach the best candidate. A city-by-city
        # loop that spends the one shared civil action too early must fail.
        data['links'] = [r for r in data['links'] if set(r) != {'xiangyang', 'nanjun'}]
        data['travel_routes'] = [r for r in data['travel_routes']
            if {r['from'], r['to']} != {'xiangyang', 'nanjun'}]
        original = controlled_catalog()
        used = {r['person_id'] for r in data['initial_officers']}
        candidates = [r for r in data['people'] if r['person_id'] not in used
            and year_state(original.definitions[r['person_id']], data['start_year']) == YearState.AVAILABLE]
        low = min(candidates, key=lambda r: r['profile']['martial_strength'])
        high = max(candidates, key=lambda r: r['profile']['martial_strength'])
        data['initial_free_officers'] = [dict(person_id=low['person_id'], city='nanjun'),
                                         dict(person_id=high['person_id'], city='xiangyang')]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'faction.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class FactionDomesticTests(unittest.TestCase):
    def game(self, *, player='shu', **options):
        game = Campaign(faction_catalog(**options))
        game.command('new', dict(faction=player, seed=2026), 0)
        return game

    def appoint(self, game, *, remote_military=False, policy=None):
        state = game.state
        ids = state.cities['xiangyang'].roster.officer_ids
        civil = max(ids, key=lambda i: state.officers[i].profile.intellect)
        military = (state.cities['nanjun'].roster.officer_ids[0] if remote_military else
                    max((i for i in ids if i != civil), key=lambda i: state.officers[i].profile.martial_strength))
        game.command('set_domestic', dict(faction='shu', civil=civil, military=military,
                                         policy=policy or {}), game.revision)
        return civil, military

    def test_one_pair_from_two_rosters_controls_both_cities_and_view_is_pure(self):
        game = self.game()
        civil, military = self.appoint(game, remote_military=True,
            policy=dict(training_enabled=True, gold_floor=0, grain_floor=0))
        state = game.state
        pool = state.extension['domestic']
        self.assertEqual(pool['schema'], 'tk2-domestic-v2')
        self.assertEqual(pool['factions']['shu']['civil'], civil)
        self.assertEqual(pool['factions']['shu']['military'], military)
        for city in pool['cities'].values():
            self.assertTrue({'civil', 'military', 'policy'}.isdisjoint(city),
                            'City ledgers cannot retain independent appointments')
        saved = game.export_save()
        for _ in range(3):
            view = domestic.view(game, state)
            self.assertTrue(view['factions']['shu']['civil_active'])
            self.assertTrue(view['factions']['shu']['military_active'])
            for key in ('xiangyang', 'nanjun'):
                self.assertEqual((view['cities'][key]['civil'], view['cities'][key]['military']),
                                 (civil, military))
                self.assertEqual(view['cities'][key]['training_preview']['gain'],
                                 2 + state.officers[military].profile.martial_strength // 25)
            self.assertIsNone(view['factions']['wei']['civil'])
            logistics.view(game, state)
        self.assertEqual(game.export_save(), saved)
        self.assertEqual(state.rng.draws, 0)
        for payload in (dict(faction='shu', military=civil),
                        dict(faction='shu', civil=True),
                        dict(faction='wei', civil=civil),
                        dict(faction='shu', civil=state.cities['nanyang'].roster.officer_ids[0]),
                        dict(city='nanjun', civil=civil)):
            before, revision = game.export_save(), game.revision
            with self.assertRaises(GameError):
                game.command('set_domestic', payload, revision)
            self.assertEqual(game.export_save(), before)
            self.assertEqual(game.revision, revision)

    def test_signed_save_cannot_assign_foreign_official_or_restore_city_offices(self):
        game = self.game()
        civil, _ = self.appoint(game)
        saved = game.export_save()
        for kind in ('foreign_office', 'city_office', 'unknown_faction'):
            altered = deepcopy(saved)
            pool = altered['state']['extension']['domestic']
            if kind == 'foreign_office':
                pool['factions']['wei']['civil'] = civil
            elif kind == 'city_office':
                pool['cities']['xiangyang']['civil'] = civil
            else:
                pool['factions']['neutral'] = deepcopy(pool['factions']['shu'])
            altered['checksum'] = digest({k: v for k, v in altered.items() if k != 'checksum'})
            before, revision = game.export_save(), game.revision
            with self.assertRaises(GameError):
                game.load_save(altered, revision)
            self.assertEqual(game.export_save(), before)
            self.assertEqual(game.revision, revision)

    def test_all_owned_cities_receive_same_civil_service_and_local_training_costs_once(self):
        game = self.game()
        civil, military = self.appoint(game, remote_military=True,
            policy=dict(training_enabled=True, gold_floor=0, grain_floor=0))
        state = game.state
        initial = {key: (c.gold, c.grain) for key, c in state.cities.items()}
        costs = {key: dict(gold=0, grain=0) for key in ('xiangyang', 'nanjun')}
        for _ in range(3):
            quotes = {key: domestic.training_preview(game, state, key) for key in costs}
            for key, quote in quotes.items():
                costs[key]['gold'] += quote['gold']
                costs[key]['grain'] += quote['grain']
            domestic.finish_faction_turn(game, state, 'shu', automatic=False)
            saved = game.export_save()
            domestic.finish_faction_turn(game, state, 'shu', automatic=False)
            self.assertEqual(game.export_save(), saved, 'One faction cannot train or earn twice in a旬')
            game._complete_turn(state)
        intellect = state.officers[civil].profile.intellect
        for key in costs:
            base = game.catalog.data['city_income'][key]
            for index, field in enumerate(('gold', 'grain')):
                bonus = base[field] * 40 * intellect // (100 * 99)
                self.assertEqual(getattr(state.cities[key], field),
                                 initial[key][index] - costs[key][field] + base[field] + bonus)
            self.assertGreater(pool_row := state.extension['domestic']['cities'][key]['morale'], 70)
            self.assertLessEqual(pool_row, 100)
        for key in ('nanyang', 'jiangxia'):
            self.assertEqual(state.extension['domestic']['cities'][key]['morale'], 70)
            base = game.catalog.data['city_income'][key]
            self.assertEqual((state.cities[key].gold, state.cities[key].grain),
                             (initial[key][0] + base['gold'], initial[key][1] + base['grain']))
        self.assertEqual(state.rng.draws, 0)
        saved = game.export_save()
        restored = Campaign(game.catalog)
        restored.load_save(json.loads(json.dumps(saved)), 0)
        self.assertEqual(restored.export_save(), saved)
        game.validate(state)

    def test_friendly_transfer_pauses_then_resumes_the_same_faction_appointment(self):
        game = self.game()
        civil, military = self.appoint(game)
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[civil],
                                     route_mode='land'), game.revision)
        state = game.state
        self.assertEqual(state.extension['domestic']['factions']['shu']['civil'], civil)
        self.assertFalse(domestic.view(game, state)['factions']['shu']['civil_active'])
        self.assertTrue(domestic.view(game, state)['factions']['shu']['military_active'])
        while state.extension['travel']['marches']:
            game._complete_turn(state)
            game.command('arrivals', {}, game.revision)
            state = game.state
        self.assertIn(civil, state.cities['nanjun'].roster.officer_ids)
        self.assertNotIn(civil, state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(state.extension['domestic']['factions']['shu']['civil'], civil)
        self.assertTrue(domestic.view(game, state)['factions']['shu']['civil_active'])
        game.validate(state)

    def test_battle_pauses_global_office_instead_of_serving_other_cities(self):
        game = self.game()
        civil, _ = self.appoint(game)
        state = game.state
        game._start_expanded_battle(state, state.cities['xiangyang'], state.cities['nanyang'], [civil])
        saved = game.export_save()
        view = domestic.view(game, state)
        self.assertFalse(view['factions']['shu']['civil_active'])
        self.assertTrue(all(not view['cities'][key]['civil_active'] for key in ('xiangyang', 'nanjun')))
        self.assertEqual(game.export_save(), saved)

    def test_zero_health_pauses_without_erasing_the_faction_appointment(self):
        game = self.game()
        civil, military = self.appoint(game)
        state = game.state
        state.officers[civil].health = 0
        domestic.synchronize(game, state)
        view = domestic.view(game, state)
        self.assertEqual(view['factions']['shu']['civil'], civil)
        self.assertFalse(view['factions']['shu']['civil_active'])
        self.assertTrue(view['factions']['shu']['military_active'])
        for key in ('xiangyang', 'nanjun'):
            self.assertEqual(view['cities'][key]['monthly_bonus_preview'], dict(gold=0, grain=0))
        state.officers[civil].health = state.officers[civil].profile.health_max
        self.assertTrue(domestic.view(game, state)['factions']['shu']['civil_active'])
        self.assertEqual(state.extension['domestic']['factions']['shu']['military'], military)
        game.validate(state)

    def test_actual_unpaid_clerk_pauses_all_cities_then_returns_after_payroll(self):
        game = self.game(empty_city=True)
        candidate = game.state.extension['civil_staff']['cities']['nanjun']['candidate']
        self.assertIsNotNone(candidate)
        ident = candidate['id']
        game.command('hire_staff', dict(city='nanjun', candidate=ident), game.revision)
        military = max(game.state.cities['xiangyang'].roster.officer_ids,
                       key=lambda i: game.state.officers[i].profile.martial_strength)
        game.command('set_domestic', dict(faction='shu', civil=ident, military=military), game.revision)
        state = game.state
        state.cities['nanjun'].gold = 0
        for _ in range(3):
            game._complete_turn(state)
        civil_staff.synchronize(game, state, monthly=True)
        employee = state.extension['civil_staff']['people'][ident]
        self.assertFalse(employee['working'])
        self.assertEqual(employee['unpaid_months'], 1)
        domestic.synchronize(game, state)
        self.assertEqual(state.extension['domestic']['factions']['shu']['civil'], ident)
        self.assertFalse(domestic.view(game, state)['factions']['shu']['civil_active'])
        for key in ('xiangyang', 'nanjun'):
            self.assertEqual(domestic.view(game, state)['cities'][key]['monthly_bonus_preview'],
                             dict(gold=0, grain=0))
        state.cities['nanjun'].gold = civil_staff.RULES['monthly_salary']
        for _ in range(3):
            game._complete_turn(state)
        civil_staff.synchronize(game, state, monthly=True)
        self.assertTrue(employee['working'])
        self.assertTrue(domestic.view(game, state)['factions']['shu']['civil_active'])
        game.validate(state)

    def test_death_removes_only_the_affected_post_and_conserves_released_troops(self):
        game = self.game()
        civil, military = self.appoint(game)
        state = game.state
        person = state.officers[civil]
        home = state.cities['xiangyang']
        released = person.troops
        person.alive, person.faction_id, person.loyalty, person.troops = False, None, 0, 0
        home.roster.officer_ids.remove(civil)
        domestic.add_reserves(game, state, home, released, morale_value=domestic.morale(state, home.id))
        domestic.synchronize(game, state)
        self.assertIsNone(state.extension['domestic']['factions']['shu']['civil'])
        self.assertEqual(state.extension['domestic']['factions']['shu']['military'], military)
        game.validate(state)

    def test_unrelated_city_capture_keeps_global_officials_but_holder_capture_revokes(self):
        game = self.game()
        civil, military = self.appoint(game)
        state = game.state
        for ident in state.cities['nanjun'].roster.officer_ids:
            state.officers[ident].faction_id = 'wei'
        state.cities['nanjun'].owner = 'wei'
        game._reconcile_factions(state)
        posts = state.extension['domestic']['factions']['shu']
        self.assertEqual((posts['civil'], posts['military']), (civil, military))
        lost_view = domestic.view(game, state)['cities']['nanjun']
        self.assertIsNone(lost_view['civil'])
        self.assertEqual(lost_view['monthly_bonus_preview'], dict(gold=0, grain=0))
        game.validate(state)
        # A separate controlled transition captures the civil official while
        # the ruler and military official remain in the other owned city.
        game = self.game()
        civil, military = self.appoint(game)
        state = game.state
        home, safe = state.cities['xiangyang'], state.cities['nanjun']
        for ident in list(home.roster.officer_ids):
            if ident != civil:
                home.roster.officer_ids.remove(ident)
                safe.roster.officer_ids.append(ident)
        home.owner = 'wei'
        state.officers[civil].faction_id = 'wei'
        game._reconcile_factions(state)
        self.assertIsNone(state.extension['domestic']['factions']['shu']['civil'])
        self.assertEqual(state.extension['domestic']['factions']['shu']['military'], military)
        game.validate(state)

    def test_neutral_city_claim_inherits_faction_offices_without_past_income(self):
        game = self.game(empty_city=True, neutral_city=True)
        civil, military = self.appoint(game,
            policy=dict(training_enabled=True, gold_floor=0, grain_floor=0))
        view = domestic.view(game, game.state)['cities']['nanjun']
        self.assertIsNone(view['civil'])
        self.assertEqual(view['monthly_bonus_preview'], dict(gold=0, grain=0))
        soldier = next(i for i in game.state.cities['xiangyang'].roster.officer_ids
                       if i not in (civil, military))
        game.command('depart', dict(source='xiangyang', target='nanjun', officers=[soldier],
                                   route_mode='land'), game.revision)
        while game.state.extension['travel']['marches']:
            game._complete_turn(game.state)
            game.command('arrivals', {}, game.revision)
        self.assertEqual(game.state.phase, 'result')
        game.command('settle', dict(battle_id=game.state.battle['id']), game.revision)
        if game.state.phase == 'arrivals':
            game.command('arrivals', {}, game.revision)
        state = game.state
        self.assertEqual(state.cities['nanjun'].owner, 'shu')
        ledger = state.extension['domestic']['cities']['nanjun']
        self.assertEqual(ledger['income_points'], 0, 'Neutral time cannot retroactively earn faction income')
        view = domestic.view(game, state)['cities']['nanjun']
        self.assertEqual((view['civil'], view['military']), (civil, military))
        self.assertGreater(view['training_preview']['gain'], 0)
        domestic.finish_faction_turn(game, state, 'shu', automatic=False)
        self.assertEqual(ledger['income_points'], state.officers[civil].profile.intellect * 2)
        saved = game.export_save()
        domestic.finish_faction_turn(game, state, 'shu', automatic=False)
        self.assertEqual(game.export_save(), saved)
        game.validate(state)

    def test_defection_revokes_one_faction_office_without_moving_the_other(self):
        game = self.game()
        civil, military = self.appoint(game)
        state = game.state
        state.cities['xiangyang'].roster.officer_ids.remove(civil)
        state.cities['nanyang'].roster.officer_ids.append(civil)
        state.officers[civil].faction_id = 'wei'
        domestic.synchronize(game, state)
        self.assertIsNone(state.extension['domestic']['factions']['shu']['civil'])
        self.assertEqual(state.extension['domestic']['factions']['shu']['military'], military)
        self.assertIsNone(state.extension['domestic']['factions']['wei']['civil'])
        for key in ('xiangyang', 'nanjun'):
            self.assertEqual(domestic.view(game, state)['cities'][key]['monthly_bonus_preview'],
                             dict(gold=0, grain=0))
        game.validate(state)

    def test_automatic_recruitment_uses_best_target_across_disconnected_owned_cities(self):
        game = self.game(isolated_targets=True)
        civil, _ = self.appoint(game, policy=dict(auto_recruit=True, auto_persuade=False,
            priority='martial', min_chance=0, budget=100, gold_floor=0))
        state = game.state
        targets = game.catalog.data['initial_free_officers']
        expected = next(game.catalog.ids[r['person_id']] for r in targets if r['city'] == 'xiangyang')
        lower = next(game.catalog.ids[r['person_id']] for r in targets if r['city'] == 'nanjun')
        self.assertGreater(state.officers[expected].profile.martial_strength,
                           state.officers[lower].profile.martial_strength)
        self.assertNotIn(expected, game._free_candidates(state, state.cities['nanjun']))
        before = state.rng.draws
        domestic.run_automatic(game, state, 'shu')
        personnel = [r for r in state.extension['domestic']['reports'] if r['kind'] == 'personnel']
        self.assertEqual(len(personnel), 1)
        self.assertEqual((personnel[0]['city'], personnel[0]['details']['id']), ('xiangyang', expected))
        self.assertEqual(state.extension['officer_actions'][str(civil)], state.turn)
        self.assertEqual(state.rng.draws, before + 1)
        saved = game.export_save()
        domestic.run_automatic(game, state, 'shu')
        self.assertEqual(game.export_save(), saved)
        game.validate(state)

    def test_ai_selects_exactly_one_pair_globally_and_uses_same_city_services(self):
        game = self.game(player='wei')
        state = game.state
        ids = [i for c in state.cities.values() if c.owner == 'shu' for i in c.roster.officer_ids]
        expected_civil = min(ids, key=lambda i: (-state.officers[i].profile.intellect,
            -state.officers[i].profile.virtue, domestic._ref_key(i)))
        expected_military = min((i for i in ids if i != expected_civil),
            key=lambda i: (-state.officers[i].profile.martial_strength,
                           -state.officers[i].profile.intellect, domestic._ref_key(i)))
        domestic.auto_assign(game, state, 'shu')
        row = state.extension['domestic']['factions']['shu']
        self.assertEqual((row['civil'], row['military']), (expected_civil, expected_military))
        self.assertNotEqual(row['civil'], row['military'])
        before = {key: c.reserves for key, c in state.cities.items()}
        domestic.finish_faction_turn(game, state, 'shu')
        for key in ('xiangyang', 'nanjun'):
            self.assertGreater(state.cities[key].reserves, before[key])
            self.assertGreater(state.extension['domestic']['cities'][key]['morale'], 60)
        self.assertEqual(row['civil'], expected_civil)
        self.assertEqual(state.rng.draws, 0)
        game.validate(state)


if __name__ == '__main__':
    unittest.main()
