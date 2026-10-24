"""Generated people share real roster, battle, inheritance and save services."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, digest
from remake import civil_staff, treasures
from remake.errors import GameError
from remake.officers import (parse_officer_ref, deserialize_officer_ref,
    ref_sort_key, select_deployment, year_state, YearState, advance_year, CityRoster)
from test_remake_civil_staff_campaign import staff_catalog


class GeneratedOfficerTests(unittest.TestCase):
    def new(self):
        game = Campaign(staff_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        ident = game.state.extension['civil_staff']['cities']['nanjun']['candidate']['id']
        game.command('hire_staff', dict(city='nanjun', candidate=ident), game.revision)
        return game, ident

    def cmd(self, game, kind, **payload):
        return game.command(kind, payload, game.revision)

    def reset_turn(self, game):
        game._complete_turn(game.state)
        game._reconcile_factions(game.state)
        civil_staff.synchronize(game, game.state, monthly=game.state.day == 1)
        treasures.synchronize(game, game.state)
        game.validate(game.state)

    def test_bounded_namespace_never_aliases_historical_integers(self):
        for value in (True, -1, 1200, '123', 'clerk-0', 'clerk-000000',
                      'clerk-0000001', 'clerk-1000001', 'clerk-000001/../x'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_officer_ref(value)
        self.assertEqual(parse_officer_ref('clerk-000001'), 'clerk-000001')
        self.assertEqual(deserialize_officer_ref('123'), 123)
        self.assertEqual(deserialize_officer_ref('clerk-000001'), 'clerk-000001')
        self.assertEqual(sorted(['clerk-000002', 2, 'clerk-000001', 1], key=ref_sort_key),
                         [1, 2, 'clerk-000001', 'clerk-000002'])

    def test_hire_adds_one_normal_person_with_fixed_profile_and_chronology(self):
        game, ident = self.new()
        person = game.state.officers[ident]
        self.assertEqual(person.runtime_id, ident)
        self.assertEqual(person.person_id, ident)
        self.assertNotIn(ident, game.catalog.by_id)
        self.assertEqual(len(game.catalog.definitions), 1023)
        self.assertEqual((person.loyalty, person.troops, person.experience), (80, 0, 0))
        self.assertEqual(game.state.cities['nanjun'].roster.officer_ids, [ident])
        self.assertEqual(game._city_occupancy(game.state, game.state.cities['nanjun']), 1)
        definition = game.person_definition(game.state, ident)
        self.assertIn(year_state(definition, game.state.year), {YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW})
        self.assertGreaterEqual(game.state.year - definition.birth_year, 20)
        self.assertGreater(definition.death_year, game.state.year)
        saved = game.export_save()
        self.assertEqual(saved['state']['officers'][ident]['runtime_id'], ident)
        loaded = Campaign(game.catalog)
        loaded.load_save(saved, 0)
        self.assertEqual(loaded.export_save(), saved)
        self.assertEqual(game.state.rng.draws, 0)

    def test_normal_allocation_battle_duel_and_result_grow_generated_runtime(self):
        game, ident = self.new()
        initial = deepcopy(game.state.soldiers)
        self.cmd(game, 'allocate', city='nanjun', officer=ident, troops=999)
        self.assertEqual(select_deployment(game.state.cities['nanjun'].roster, [ident], game.state.officers), (ident,))
        self.assertEqual(game.state.soldiers, initial)
        self.reset_turn(game)
        game._start_expanded_battle(game.state, game.state.cities['nanjun'],
                                   game.state.cities['jiangxia'], [ident])
        game.validate(game.state)
        saved = game.export_save()
        loaded = Campaign(game.catalog)
        loaded.load_save(saved, 0)
        self.assertEqual(loaded.export_save(), saved)
        battle = game.state.battle
        target = battle['defenders'][0]['id']
        self.cmd(game, 'duel_start', battle_id=battle['id'], actor=ident, target=target)
        if game.state.battle['extended']['duel']:
            self.cmd(game, 'duel_action', battle_id=battle['id'], move='withdraw')
        if game.state.phase == 'battle':
            self.cmd(game, 'retreat', battle_id=battle['id'])
        self.cmd(game, 'settle', battle_id=battle['id'])
        person = game.state.officers[ident]
        self.assertGreater(person.experience, 0)
        self.assertIn(ident, game.state.cities['nanjun'].roster.officer_ids)
        current = sum(c.reserves for c in game.state.cities.values()) + sum(o.troops for o in game.state.officers.values())
        self.assertEqual(current + game.state.soldiers['lost'], initial['initial'] + game.state.soldiers['recruited'])

    def test_generated_only_faction_survives_and_player_selects_successor(self):
        game, ident = self.new()
        for city in game.state.cities.values():
            for key in list(city.roster.officer_ids):
                officer = game.state.officers[key]
                if officer.faction_id != 'shu' or key == ident:
                    continue
                city.reserves += officer.troops
                officer.troops = 0
                officer.alive = False
                officer.faction_id = None
                officer.loyalty = 0
                city.roster.officer_ids.remove(key)
        game._reconcile_factions(game.state)
        game.validate(game.state)
        self.assertNotIn('shu', game.state.extension['ended_factions'])
        self.assertEqual(game.state.extension['pending_succession']['shu']['candidates'], [ident])
        before = game.export_save()
        with self.assertRaises(GameError):
            self.cmd(game, 'end_turn')
        self.assertEqual(game.export_save(), before)
        self.cmd(game, 'choose_successor', officer=ident)
        self.assertEqual(game.state.extension['leaders']['shu'], ident)
        self.assertEqual(game.state.officers[ident].loyalty, 100)
        self.assertFalse(game.state.extension['pending_succession'])

    def test_normal_transfer_preserves_generated_stats_id_and_paid_salary_identity(self):
        game, ident = self.new()
        self.cmd(game, 'allocate', city='nanjun', officer=ident, troops=321)
        self.reset_turn(game)
        before = deepcopy(game.state.officers[ident])
        self.cmd(game, 'transfer', source='nanjun', target='xiangyang', officers=[ident])
        saved = game.export_save()
        clone = Campaign(game.catalog)
        clone.load_save(saved, 0)
        self.assertEqual(clone.export_save(), saved)
        arrival = game.state.extension['travel']['marches'][0]['arrival_turn']
        while game.state.turn < arrival:
            self.reset_turn(game)
        self.cmd(game, 'arrivals')
        self.assertEqual(game.state.officers[ident], before)
        self.assertNotIn(ident, game.state.cities['nanjun'].roster.officer_ids)
        self.assertIn(ident, game.state.cities['xiangyang'].roster.officer_ids)
        person = game.state.extension['civil_staff']['people'][ident]
        self.assertEqual((person['city'], person['owner']), ('xiangyang', 'shu'))

    def test_city_capture_uses_real_generated_retreat_instead_of_automatic_defection(self):
        game, ident = self.new()
        self.cmd(game, 'allocate', city='nanjun', officer=ident, troops=20)
        self.reset_turn(game)
        game._start_expanded_battle(game.state, game.state.cities['jiangxia'],
            game.state.cities['nanjun'], [178])
        game.validate(game.state)
        battle = game.state.battle['id']
        self.cmd(game, 'retreat', battle_id=battle)
        self.cmd(game, 'settle', battle_id=battle)
        self.assertEqual(game.state.cities['nanjun'].owner, 'wu')
        self.assertEqual(game.state.officers[ident].faction_id, 'shu')
        self.assertIn(ident, game.state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(game.state.extension['civil_staff']['people'][ident]['city'], 'xiangyang')

    def test_generated_lifespan_uses_normal_annual_release_and_never_revives(self):
        game, ident = self.new()
        self.cmd(game, 'allocate', city='nanjun', officer=ident, troops=321)
        definition = game.person_definition(game.state, ident)
        officer = deepcopy(game.state.officers[ident])
        roster = CityRoster('nanjun', [ident], game.catalog.rules)
        records = advance_year([definition], {ident: officer}, [roster],
            definition.death_year, definition.death_year + 1)
        self.assertFalse(officer.alive)
        self.assertEqual(officer.troops, 0)
        self.assertEqual(roster.officer_ids, [])
        self.assertEqual(len(records), 1)
        self.assertEqual((records[0]['released_troops'], records[0]['origin_city']), (321, 'nanjun'))
        again = advance_year([definition], {ident: officer}, [roster],
            definition.death_year + 1, definition.death_year + 2)
        self.assertEqual(again, ())
        self.assertFalse(officer.alive)

    def test_generated_save_profile_alias_or_equipment_corruption_is_atomic(self):
        game, ident = self.new()
        saved = game.export_save()
        for field in ('profile', 'runtime_id', 'weapon_id'):
            invalid = deepcopy(saved)
            person = invalid['state']['officers'][ident]
            if field == 'profile': person['profile']['martial_strength'] += 1
            elif field == 'runtime_id': person['runtime_id'] = 1023
            else: person['weapon_id'] = 29
            invalid['checksum'] = digest({k: v for k, v in invalid.items() if k != 'checksum'})
            with self.subTest(field=field), self.assertRaises(GameError):
                game.load_save(invalid, game.revision)
            self.assertEqual(game.export_save(), saved)


if __name__ == '__main__':
    unittest.main()
