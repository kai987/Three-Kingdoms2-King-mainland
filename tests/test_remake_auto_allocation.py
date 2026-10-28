"""Faction military officers allocate only real, local, available reserves."""
from copy import deepcopy
from dataclasses import replace
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake import command_books, domestic, logistics, treasures
from remake.campaign import Campaign, digest
from remake.errors import GameError
from test_remake_faction_domestic import faction_catalog


class AutoAllocationTests(unittest.TestCase):
    def game(self, *, player='shu', **options):
        game = Campaign(faction_catalog(**options))
        game.command('new', dict(faction=player, seed=2026), 0)
        military = 146 if options.get('empty_city', False) else 255
        if game.state.player == 'shu':
            game.command('set_domestic', dict(faction='shu', civil=439, military=military), game.revision)
        else:
            game.state.extension['domestic']['factions']['shu'].update(civil=439, military=military)
        return game

    def test_remote_official_fills_strongest_first_in_each_local_roster(self):
        game = self.game()
        state = game.state
        before = game.export_save()
        quote = domestic.allocation_preview(game, state, 'xiangyang')
        self.assertEqual(quote, dict(soldiers=1200, officers=2, remaining_reserves=0,
            assignments=[dict(id=146, **{'from': 180}, to=999, added=819),
                         dict(id=951, **{'from': 180}, to=561, added=381)]))
        view = domestic.view(game, state)
        self.assertEqual(view['cities']['xiangyang']['allocation_preview'], quote)
        self.assertEqual(view['factions']['shu']['allocation_preview'], dict(soldiers=2079, officers=3))
        self.assertEqual(game.export_save(), before, 'Preview must not mutate saves or RNG')
        resources = {key: (c.gold, c.grain, c.action_used) for key, c in state.cities.items()}
        actions, totals = deepcopy(state.extension['officer_actions']), deepcopy(state.soldiers)
        books = deepcopy(state.extension['command_books'])
        domestic.finish_faction_turn(game, state, 'shu', automatic=False)
        self.assertEqual((state.officers[146].troops, state.officers[951].troops), (999, 561))
        self.assertEqual((state.officers[255].troops, state.cities['nanjun'].reserves), (999, 321))
        self.assertEqual((state.officers[999].troops, state.officers[439].troops), (80, 120),
                         'Existing lower-ranked troops must never be recalled')
        self.assertEqual({key: (c.gold, c.grain, c.action_used) for key, c in state.cities.items()}, resources)
        self.assertEqual(state.extension['officer_actions'], actions)
        self.assertEqual(state.extension['command_books'], books,
                         'Automatic allocation is embedded work and must not spend another book')
        self.assertEqual(state.soldiers, totals)
        self.assertEqual(state.rng.draws, 0)
        self.assertEqual(state.cities['nanyang'].reserves, 1200, 'No foreign reserve pool is touched')
        self.assertEqual(state.cities['jiangxia'].reserves, 1200)
        game.validate(state)

    def test_tie_breaks_compare_intellect_virtue_health_experience_then_id(self):
        game = self.game()
        for field in ('martial_strength', 'intellect', 'virtue', 'health', 'experience', 'id'):
            with self.subTest(field=field):
                state = deepcopy(game.state)
                city = state.cities['xiangyang']
                first, second = state.officers[146], state.officers[951]
                for person in (first, second):
                    person.profile = replace(person.profile, martial_strength=80, intellect=80,
                                             virtue=80, health_max=99)
                    person.health, person.experience, person.troops = 80, 0, 0
                if field in ('martial_strength', 'intellect', 'virtue'):
                    second.profile = replace(second.profile, **{field: 81})
                elif field in ('health', 'experience'):
                    setattr(second, field, 81 if field == 'health' else 10)
                city.roster.officer_ids = [951, 146]
                city.reserves = 1
                quote = domestic.allocation_preview(game, state, city.id)
                self.assertEqual(quote['assignments'][0]['id'], 146 if field == 'id' else 951)

    def test_empty_pool_and_full_rosters_never_discard_overflow_or_create_troops(self):
        game = self.game()
        state, city = game.state, game.state.cities['xiangyang']
        for ident in city.roster.officer_ids:
            officer = state.officers[ident]
            city.reserves -= 999 - officer.troops
            officer.troops = 999
        # Build a valid abundant-reserve fixture with a matching conservation ledger.
        city.reserves = 5000
        state.soldiers['initial'] = sum(c.reserves for c in state.cities.values()) + sum(o.troops for o in state.officers.values())
        before = game.export_save()
        self.assertEqual(domestic.allocate_garrison(game, state, city.id),
                         dict(soldiers=0, officers=0, remaining_reserves=5000, assignments=[]))
        self.assertEqual(game.export_save(), before)
        city.reserves = 0
        state.soldiers['initial'] -= 5000
        self.assertEqual(domestic.allocate_garrison(game, state, city.id)['soldiers'], 0)
        game.validate(state)

    def test_receipt_and_signed_roundtrip_prevent_repeat_or_negative_reports(self):
        game = self.game()
        domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
        saved = game.export_save()
        domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
        self.assertEqual(game.export_save(), saved)
        reports = [r for r in game.state.extension['domestic']['reports'] if r['kind'] == 'allocation']
        self.assertEqual(len(reports), 2)
        restored = Campaign(game.catalog)
        restored.load_save(saved, 0)
        self.assertEqual(restored.export_save(), saved)
        for patch in (dict(soldiers=-1), dict(officers=True), dict(officers=100), dict(soldiers=1, officers=2)):
            tampered = deepcopy(saved)
            report = next(r for r in tampered['state']['extension']['domestic']['reports'] if r['kind'] == 'allocation')
            report['details'].update(patch)
            tampered['checksum'] = digest({k: v for k, v in tampered.items() if k != 'checksum'})
            with self.assertRaises(GameError):
                restored.load_save(tampered, restored.revision)
            self.assertEqual(restored.export_save(), saved)

    def test_real_departure_battle_and_zero_health_skip_unavailable_people(self):
        game = self.game()
        game.command('transfer', dict(source='xiangyang', target='nanjun', officers=[951], route_mode='land'), game.revision)
        state = game.state
        state.officers[999].health = 0
        game._start_expanded_battle(state, state.cities['xiangyang'], state.cities['nanyang'], [146])
        quote = domestic.allocation_preview(game, state, 'xiangyang')
        self.assertEqual([r['id'] for r in quote['assignments']], [439])
        original = {i: state.officers[i].troops for i in (951, 999, 146)}
        domestic.allocate_garrison(game, state, 'xiangyang')
        self.assertEqual({i: state.officers[i].troops for i in original}, original)
        self.assertEqual(state.officers[439].troops, 999)
        self.assertEqual(state.cities['xiangyang'].reserves, 321)
        treasures.synchronize(game,state)
        game.validate(state)

    def test_unavailable_military_official_pauses_every_city(self):
        game = self.game()
        game.command('transfer', dict(source='nanjun', target='xiangyang', officers=[255], route_mode='land'), game.revision)
        before = {i: o.troops for i, o in game.state.officers.items()}
        for key in ('xiangyang', 'nanjun'):
            self.assertEqual(domestic.allocation_preview(game, game.state, key)['soldiers'], 0)
        domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
        self.assertEqual({i: o.troops for i, o in game.state.officers.items()}, before)
        self.assertFalse(any(r['kind'] == 'allocation' for r in game.state.extension['domestic']['reports']))
        game.validate(game.state)

    def test_generated_clerk_receives_troops_and_unpaid_clerk_is_skipped(self):
        game = self.game(empty_city=True)
        candidate = game.state.extension['civil_staff']['cities']['nanjun']['candidate']['id']
        game.command('hire_staff', dict(city='nanjun', candidate=candidate), game.revision)
        state = game.state
        self.assertEqual(domestic.allocation_preview(game, state, 'nanjun')['assignments'][0]['id'], candidate)
        person = state.extension['civil_staff']['people'][candidate]
        person['working'] = False
        self.assertEqual(domestic.allocation_preview(game, state, 'nanjun')['soldiers'], 0)
        person['working'] = True
        domestic.allocate_garrison(game, state, 'nanjun')
        self.assertEqual((state.officers[candidate].troops, state.cities['nanjun'].reserves), (999, 201))
        game.validate(state)

    def test_new_recruits_are_allocated_in_the_same_turn_without_extra_fees(self):
        game = self.game()
        game.command('set_domestic', dict(faction='shu', policy=dict(recruit_enabled=True,
            reserve_target=1300, gold_floor=0, grain_floor=0)), game.revision)
        state = game.state
        quotes = {key: domestic.recruitment_preview(game, state, key) for key in ('xiangyang', 'nanjun')}
        before = {key: (state.cities[key].gold, state.cities[key].grain) for key in quotes}
        domestic.finish_faction_turn(game, state, 'shu')
        reports = state.extension['domestic']['reports']
        for key, quote in quotes.items():
            city = state.cities[key]
            recruit = next(r for r in reports if r['city'] == key and r['kind'] == 'recruit')
            allocation = next(r for r in reports if r['city'] == key and r['kind'] == 'allocation')
            self.assertLess(reports.index(recruit), reports.index(allocation))
            self.assertEqual((city.gold, city.grain), (before[key][0] - quote['gold'], before[key][1] - quote['grain']))
        orders = state.extension['command_books']['factions']['shu']['orders']
        self.assertEqual([r['kind'] for r in orders], ['recruit', 'recruit'])
        self.assertEqual(command_books.remaining(state, 'shu'), 1)
        self.assertEqual(state.cities['xiangyang'].reserves, 0)
        self.assertEqual(state.officers[951].troops, 661)
        game.validate(state)

    def test_explicit_reserve_transport_has_first_claim_and_escort_is_not_allocated(self):
        game = self.game()
        game.command('set_logistics', dict(city='xiangyang', policy=dict(enabled=True, target_city='nanjun',
            reserve_reserves=200, reserve_officers=2, target_reserves=3000, target_officers=3)), game.revision)
        state = game.state
        original = {i: o.troops for i, o in state.officers.items()}
        domestic.finish_faction_turn(game, state, 'shu')
        convoys = state.extension['logistics']['convoys']
        self.assertEqual(len(convoys), 1)
        self.assertEqual(convoys[0]['cargo']['reserves'], 1000)
        self.assertEqual(state.cities['xiangyang'].reserves, 0)
        allocated = sum(state.officers[i].troops - original[i] for i in state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(allocated, 200)
        for ident in convoys[0]['officers']:
            self.assertEqual(state.officers[ident].troops, original[ident])
        self.assertEqual(logistics.in_transit_reserves(state), 1000)
        game.validate(state)

    def test_shared_settlement_is_identical_for_player_and_ai_ownership(self):
        player = self.game()
        ai = self.game(player='wei')
        # The faction and local resources are identical. Only player control differs.
        for game in (player, ai):
            post = game.state.extension['domestic']['factions']['shu']
            post['civil'], post['military'] = 439, 255
        self.assertEqual(domestic.allocation_preview(player, player.state, 'xiangyang'),
                         domestic.allocation_preview(ai, ai.state, 'xiangyang'))
        for game in (player, ai):
            domestic.finish_faction_turn(game, game.state, 'shu', automatic=False)
            game.validate(game.state)
        self.assertEqual({i: o.troops for i, o in player.state.officers.items()},
                         {i: o.troops for i, o in ai.state.officers.items()})
        self.assertEqual({key: c.reserves for key, c in player.state.cities.items()},
                         {key: c.reserves for key, c in ai.state.cities.items()})


if __name__ == '__main__':
    unittest.main()
