"""Behavioral acceptance for modern officer state, without a ROM or emulator."""
from copy import deepcopy
from pathlib import Path
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.officers import (CapacityError, CityRoster, GameRules, OfficerProfile,
    PersonDefinition, YearState, advance_year, captured_loyalty, compatible_stat,
    convert_profile, experience_tier, initialize_officer, recruitment_loyalty,
    select_deployment, transfer_officers, virtue_score, year_state)


def person(ident='person-1', *, birth=150, service=180, death=240):
    return PersonDefinition(ident, ident, birth, service, death)


def active(ident, **options):
    return initialize_officer(person(str(ident)), ident, OfficerProfile(80, 70, 65, 60, 0),
                              year=200, faction_id='wei', loyalty=70, troops=100, **options)


class ModernRosterTests(unittest.TestCase):
    def test_99_city_members_do_not_expand_battle_capacity(self):
        city = CityRoster('luoyang', list(range(99)))
        registry = {i: active(i) for i in range(99)}
        before = deepcopy((city, registry))
        self.assertEqual(select_deployment(city, range(89, 99), registry), tuple(range(89, 99)))
        with self.assertRaises(ValueError):
            select_deployment(city, range(11), registry)
        self.assertEqual((city, registry), before)  # Selection/cancel never spends or removes.

    def test_full_destination_rejects_whole_transaction(self):
        source = CityRoster('changan', [255, 999])
        destination = CityRoster('luoyang', list(range(99)))
        before = deepcopy((source, destination))
        with self.assertRaises(CapacityError):
            transfer_officers(source, destination, [255, 999])
        self.assertEqual((source, destination), before)

    def test_transfer_98_to99_and_valid_id255(self):
        source = CityRoster('changan', [255, 999])
        target = CityRoster('luoyang', list(range(98)))
        self.assertEqual(transfer_officers(source, target, [255]), (255,))
        self.assertEqual(source.officer_ids, [999])
        self.assertEqual(len(target.officer_ids), 99)
        self.assertEqual(target.officer_ids[-1], 255)
        self.assertEqual(len(set(source.officer_ids + target.officer_ids)), 100)
        with self.assertRaises(CapacityError):
            transfer_officers(source, target, [999])

    def test_invalid_batch_has_no_partial_side_effects(self):
        source, target = CityRoster('a', [255, 999]), CityRoster('b', [])
        for invalid in ([255, 7], [255, 255]):
            with self.assertRaises(ValueError):
                transfer_officers(source, target, invalid)
            self.assertEqual(source.officer_ids, [255, 999])
            self.assertEqual(target.officer_ids, [])
        self.assertEqual(transfer_officers(source, source, [255]), ())

    def test_no_duplicate_or_out_of_domain_ids(self):
        for values in ([1, 1], [65535], [1200], [True]):
            with self.assertRaises(ValueError):
                CityRoster('a', values)
        with self.assertRaises(CapacityError):
            CityRoster('a', list(range(100)))

    def test_all_1000_library_ids_remain_distinct(self):
        rules = GameRules()
        ids = [rules.officer_id(i) for i in range(1000)]
        self.assertEqual(len(set(ids)), 1000)
        self.assertNotEqual(ids[255], ids[999])
        city = CityRoster('a', [0, 255, 999])
        self.assertEqual(select_deployment(city, [999, 255], {i: active(i) for i in city.officer_ids}),
                         (999, 255))


class ChronologyTests(unittest.TestCase):
    def test_birth_service_death_are_separate(self):
        p = person(birth=190, service=217, death=225)
        expected = {189: YearState.NOT_BORN, 190: YearState.NOT_APPEARED,
                    205: YearState.NOT_APPEARED, 217: YearState.AVAILABLE,
                    224: YearState.AVAILABLE, 225: YearState.DEATH_YEAR_REVIEW,
                    226: YearState.DEAD}
        for y, state in expected.items():
            self.assertEqual(year_state(p, y), state)

    def test_missing_dates_and_bad_input_are_not_zero(self):
        self.assertEqual(year_state(person(service=None), 200), YearState.UNKNOWN)
        self.assertEqual(year_state(person(birth=None), 250), YearState.DEAD)
        for y in (0, None, True, 200.5):
            with self.assertRaises(ValueError):
                year_state(person(), y)
        with self.assertRaises(ValueError):
            person(service=149)

    def test_death_year_requires_explicit_scenario_resolution(self):
        p = person(death=200)
        profile = OfficerProfile(80, 70, 60, 50, 0)
        with self.assertRaises(ValueError):
            initialize_officer(p, 255, profile, year=200)
        self.assertTrue(initialize_officer(p, 255, profile, year=200, resolve_death_year=True).alive)

    def test_annual_death_removes_roster_once_and_preserves_resource_event(self):
        p = person('255', death=200)
        officer = initialize_officer(p, 255, OfficerProfile(80, 70, 60, 50, 0),
                                     year=199, faction_id='wei', loyalty=80, troops=123)
        city = CityRoster('luoyang', [255])
        self.assertEqual(advance_year([p], {255: officer}, [city], 199, 200), ())
        result = advance_year([p], {255: officer}, [city], 200, 201)
        self.assertEqual(result[0]['released_troops'], 123)
        self.assertEqual(result[0]['origin_city'], 'luoyang')
        self.assertFalse(officer.alive)
        self.assertIsNone(officer.faction_id)
        self.assertEqual(city.officer_ids, [])
        self.assertEqual(advance_year([p], {255: officer}, [city], 201, 202), ())

    def test_birth_and_service_events_do_not_create_or_revive_people(self):
        born = person('new', birth=200, service=205, death=240)
        dead = active(0)
        dead.alive = False
        registry = {0: dead}
        result = advance_year([person('0'), born], registry, [], 199, 205)
        self.assertEqual([(e['year'], e['event']) for e in result], [(200, 'birth'), (205, 'service_eligible')])
        self.assertEqual(len(registry), 1)
        self.assertFalse(dead.alive)

    def test_already_dead_retirement_boundary_has_receipt_without_resource_effect(self):
        p = person('255', death=200)
        officer = initialize_officer(p, 255, OfficerProfile(80, 70, 60, 50, 0), year=199)
        officer.alive = False
        officer.health = 0
        before = deepcopy(officer)
        events = advance_year([p], {255: officer}, [], 200, 201)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event'], 'remove_after_death_year')
        self.assertTrue(events[0]['already_dead'])
        self.assertEqual(events[0]['released_troops'], 0)
        self.assertIsNone(events[0]['origin_city'])
        self.assertEqual(officer, before)
        repeated = advance_year([p], {255: officer}, [], 200, 201)
        self.assertEqual(repeated, events)  # Receipt discovery is read-only for this record.
        self.assertEqual(officer, before)
        self.assertEqual(advance_year([p], {255: officer}, [], 201, 202), ())

    def test_registry_preconditions_fail_before_death_effects(self):
        p = person('0', death=200)
        officer = active(0)
        a, b = CityRoster('a', [0]), CityRoster('b', [0])
        with self.assertRaises(ValueError):
            advance_year([p], {0: officer}, [a, b], 200, 201)
        self.assertTrue(officer.alive)
        self.assertEqual(a.officer_ids, [0])

    def test_real_1000_population_reconciles(self):
        data = json.loads((ROOT / 'game/config/references/san14-roster.json').read_text())['officers']
        people = [PersonDefinition(p['person_id'], p['name_simplified'], p['chronology']['game_birth_year'],
                  p['chronology']['game_appearance_year'], p['chronology']['game_death_year']) for p in data]
        states = [year_state(p, 230) for p in people]
        self.assertEqual(len(people), 1000)
        self.assertEqual(states.count(YearState.AVAILABLE), 326)
        self.assertEqual(states.count(YearState.DEATH_YEAR_REVIEW), 12)
        self.assertEqual(len({p.person_id for p in people}), 1000)


class InitializationTests(unittest.TestCase):
    def test_direct_stat_mapping_preserves100_source(self):
        p = convert_profile(san14_stats={'martial_strength': 100, 'intellect': 85, 'charisma': 99})
        self.assertEqual((p.martial_strength, p.intellect), (99, 85))
        self.assertEqual(p.source_stats['martial_strength'], 100)
        self.assertEqual(p.virtue, 99)
        self.assertIsNone(p.health_max)
        with self.assertRaises(ValueError):
            compatible_stat(0)

    def test_no_guessing_and_new_appearance_initialization(self):
        missing = convert_profile(san14_stats={'martial_strength': 80, 'intellect': 90})
        with self.assertRaisesRegex(ValueError, 'health_max'):
            initialize_officer(person(), 999, missing, year=200)
        profile = OfficerProfile(75, 80, 90, 70, 2)
        o = initialize_officer(person(), 999, profile, year=200)
        self.assertEqual((o.health, o.loyalty, o.troops, o.weapon_id, o.armor_id, o.experience, o.tier),
                         (75, 0, 0, 0, 0, 0, 0))
        ruler = initialize_officer(person(), 999, profile, year=200, faction_id='shu', is_ruler=True)
        self.assertEqual(ruler.loyalty, 100)
        with self.assertRaises(ValueError):
            initialize_officer(person(), 999, profile, year=200, faction_id='shu')

    def test_equipment_troops_and_xp_boundaries(self):
        p = person()
        profile = OfficerProfile(75, 80, 90, 70, 2)
        self.assertEqual(initialize_officer(p,0,profile,year=200,faction_id='wei',loyalty=70,troops=1000).troops,1000)
        for options in ({'troops': 1001}, {'weapon_id': 29}, {'armor_id': 8}, {'experience': 50000}):
            with self.assertRaises(ValueError):
                initialize_officer(p, 0, profile, year=200, **options)
        self.assertEqual(experience_tier(999), 0)
        self.assertEqual(experience_tier(1000), 1)
        self.assertEqual(experience_tier(15000), 7)
        with self.assertRaises(ValueError):
            OfficerProfile(75, 80, 90, 70, 3)

    def test_charisma_precedes_legacy_and_design_without_removing_generic_fallback(self):
        design = dict(status='configured_design', sources=[dict(work='Historical assessment')],
                      dimensions=dict(care=90, fairness=90, integrity=90, trust=90))
        profile = convert_profile(san14_stats={'charisma': 100}, legacy=dict(virtue=86),
                                  virtue_design=design)
        self.assertEqual(profile.virtue, 99)
        self.assertEqual(profile.source_stats['charisma'], 100)
        self.assertEqual(profile.basis['virtue'], 'SAN14.charisma; max99 compatibility scale')
        self.assertEqual(convert_profile(san14_stats={'charisma': 1},
                                        virtue_design=design).virtue, 1)
        self.assertEqual(convert_profile(legacy=dict(virtue=86),
                                        virtue_design=design).virtue, 86)
        self.assertEqual(convert_profile(virtue_design=design).virtue, 90)
        with self.assertRaises(ValueError):
            virtue_score({'care': 90})

    def test_loyalty_rules_keep_wrap_clamp_and_capture_boundaries(self):
        for virtue, previous, expected in [(60, 0, 76), (60, 70, 10), (60, 76, 10),
                (60, 77, 90), (99, 80, 90), (99, 69, 10), (1, 70, 10), (1, 71, 90)]:
            self.assertEqual(recruitment_loyalty(virtue, previous), expected)
        for previous, expected in [(0, 10), (25, 26), (50, 51), (75, 26), (100, 10)]:
            self.assertEqual(captured_loyalty(previous), expected)

    def test_modern_runtime_imports_in_directory_without_rom_or_ir(self):
        with tempfile.TemporaryDirectory() as directory:
            shutil.copytree(ROOT / 'source/remake', Path(directory) / 'remake',
                            ignore=shutil.ignore_patterns('__pycache__'))
            code = ('from remake.officers import *; '
                    'assert GameRules().city_officer_capacity==99; '
                    'assert GameRules().officer_id(999)==999; '
                    'assert year_state(PersonDefinition("a","a",190,217,225),217)==YearState.AVAILABLE')
            subprocess.run([sys.executable, '-c', code], cwd=directory, check=True,
                           env=dict(os.environ, PYTHONPATH=directory, PYTHONDONTWRITEBYTECODE='1'))


if __name__ == '__main__':
    unittest.main()
