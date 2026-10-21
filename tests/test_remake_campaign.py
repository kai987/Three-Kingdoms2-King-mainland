"""Independent slice acceptance; no ROM, original core or control IR inputs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, GameError, digest
from remake.officers import OfficerProfile, PersonDefinition, initialize_officer


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(Catalog(ROOT / 'game/data/demo.json'))
        self.game.command('new', {'faction': 'shu', 'seed': 2026}, 0)

    def cmd(self, kind, payload=None):
        return self.game.command(kind, payload or {}, self.game.revision)

    def start(self, ident=999, troops=600, target='nanjun', source='xiangyang'):
        self.cmd('allocate', {'city': source, 'officer': ident, 'troops': troops})
        self.cmd('depart', {'source': source, 'target': target, 'officers': [ident]})
        return self.game.state.battle['id']

    def fight(self):
        for _ in range(150):
            b = self.game.state.battle
            if self.game.state.phase == 'result':
                return b['outcome']
            actor = next(u['id'] for u in b['attackers'] if u['troops'] > 0 and u['id'] not in b['used'])
            target = next(u['id'] for u in b['defenders'] if u['troops'] > 0)
            self.cmd('attack', {'battle_id': b['id'], 'actor': actor, 'target': target})
        self.fail('Battle did not finish')

    def test_real_runtime_ids_255_and999_and_single_ownership(self):
        self.assertEqual(self.game.catalog.name(255), '阿会喃')
        self.assertEqual(self.game.catalog.name(999), '伊籍')
        self.assertEqual(len(self.game.catalog.definitions), 1000)
        self.assertEqual(len(self.game.state.officers), 7)
        self.game.validate(self.game.state)

    def test_invalid_confirmation_is_atomic_including_rng(self):
        before, rev = self.game.to_dict(), self.game.revision
        for kind, payload in [('allocate', {'city': 'xiangyang', 'officer': 999, 'troops': 1000}),
                              ('depart', {'source': 'xiangyang', 'target': 'jiangxia', 'officers': [999]}),
                              ('depart', {'source': 'xiangyang', 'target': 'nanjun', 'officers': [999, 999]}),
                              ('allocate', {'city': 'nanjun', 'officer': 255, 'troops': 30})]:
            with self.assertRaises(ValueError):
                self.cmd(kind, payload)
            self.assertEqual(self.game.to_dict(), before)
            self.assertEqual(self.game.revision, rev)

    def test_compiling_army_conserves_soldiers_without_rng_or_action(self):
        initial = self.game.state.soldiers.copy()
        self.cmd('allocate', {'city': 'xiangyang', 'officer': 999, 'troops': 600})
        self.assertEqual(self.game.state.cities['xiangyang'].reserves, 680)
        self.assertEqual(self.game.state.rng.draws, 0)
        self.assertFalse(self.game.state.cities['xiangyang'].action_used)
        self.assertEqual(self.game.state.soldiers, initial)

    def test_victory_commits_membership_and_resources_once(self):
        ident = self.start()
        self.assertEqual(self.fight(), 'victory')
        pre = deepcopy(self.game.state)
        self.assertEqual(pre.cities['nanjun'].owner, 'neutral')
        self.assertIn(999, pre.cities['xiangyang'].roster.officer_ids)
        revision = self.game.revision
        self.cmd('settle', {'battle_id': ident})
        after = self.game.to_dict()
        self.assertEqual(self.game.state.cities['nanjun'].owner, 'shu')
        self.assertEqual(self.game.state.cities['nanjun'].roster.officer_ids, [999])
        self.assertNotIn(999, self.game.state.cities['xiangyang'].roster.officer_ids)
        self.assertIsNone(self.game.state.officers[255].faction_id)
        self.assertEqual(self.game.state.cities['nanjun'].gold, pre.cities['nanjun'].gold)
        self.game.command('settle', {'battle_id': ident}, revision)
        self.assertEqual(self.game.to_dict(), after)
        self.assertEqual(self.game.state.settled_battles, [ident])

    def test_racing_settlement_does_not_double_commit(self):
        ident = self.start()
        self.fight()
        rev = self.game.revision
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.game.command('settle', {'battle_id': ident}, rev), range(2)))
        self.assertEqual(responses[0]['game'], responses[1]['game'])
        self.assertEqual(self.game.revision, rev + 1)
        self.assertEqual(len(self.game.state.settled_battles), 1)

    def test_defeat_returns_zero_troop_officer_without_false_death(self):
        self.game.command('new', {'faction': 'wu', 'seed': 2026}, self.game.revision)
        ident = self.start(178, 1, 'nanjun', 'jiangxia')
        self.assertEqual(self.fight(), 'defeat')
        self.cmd('settle', {'battle_id': ident})
        self.assertEqual(self.game.state.cities['nanjun'].owner, 'neutral')
        self.assertIn(178, self.game.state.cities['jiangxia'].roster.officer_ids)
        self.assertEqual(self.game.state.officers[178].troops, 0)
        self.assertTrue(self.game.state.officers[178].alive)

    def test_retreat_keeps_actual_losses_and_supply_cost_once(self):
        self.game.command('new', {'faction': 'wei', 'seed': 2026}, self.game.revision)
        ident = self.start(123, 480, 'xiangyang', 'nanyang')
        self.cmd('attack', {'battle_id': ident, 'actor': 123, 'target': 146})
        remaining = self.game.state.battle['attackers'][0]['troops']
        self.cmd('retreat', {'battle_id': ident})
        self.cmd('settle', {'battle_id': ident})
        self.assertLess(remaining, 480)
        self.assertEqual(self.game.state.officers[123].troops, remaining)
        self.assertEqual(self.game.state.cities['nanyang'].grain, 3800 - 480 // 25)
        self.assertEqual(self.game.state.cities['xiangyang'].owner, 'shu')
        self.game.validate(self.game.state)

    def test_three_turns_cross_year_and_duplicate_ai_noop(self):
        for turn in range(1, 4):
            self.cmd('end_turn')
            rev = self.game.revision
            self.cmd('ai', {'turn': turn})
            after, new_rev = self.game.to_dict(), self.game.revision
            self.game.command('ai', {'turn': turn}, rev)
            self.assertEqual(self.game.to_dict(), after)
            self.assertEqual(self.game.revision, new_rev)
        s = self.game.state
        self.assertEqual((s.year, s.month, s.turn, s.calendar_cursor), (218, 2, 4, 218))
        self.assertEqual(s.completed_ai_turns, [1, 2, 3])
        self.assertTrue(s.year_events)
        self.assertEqual(len(s.year_events), len(set(s.year_events)))

    def test_midbattle_save_restores_next_rng_and_outcome(self):
        ident = self.start(146, 180, 'nanyang')
        self.cmd('attack', {'battle_id': ident, 'actor': 146, 'target': 123})
        self.assertEqual(self.game.state.phase, 'battle')
        saved = self.game.export_save()
        twin = Campaign(self.game.catalog)
        twin.load_save(saved, 0)
        self.assertEqual(self.game.to_dict(), twin.to_dict())
        payload = {'battle_id': ident, 'actor': 146, 'target': 123}
        self.cmd('attack', payload)
        twin.command('attack', payload, twin.revision)
        self.assertEqual(self.game.to_dict(), twin.to_dict())

    def test_bad_checksum_and_semantic_save_never_overwrite(self):
        original, rev = self.game.to_dict(), self.game.revision
        bad = self.game.export_save()
        bad['checksum'] = 'broken'
        with self.assertRaises(GameError):
            self.game.load_save(bad, rev)
        bad = self.game.export_save()
        bad['state']['cities']['xiangyang']['gold'] = -1
        bad['checksum'] = digest({k: v for k, v in bad.items() if k != 'checksum'})
        with self.assertRaises(GameError):
            self.game.load_save(bad, rev)
        self.assertEqual(self.game.to_dict(), original)
        self.assertEqual(self.game.revision, rev)

    def test_invalid_battle_save_or_future_event_cursor_is_rejected(self):
        self.start()
        original, rev = self.game.to_dict(), self.game.revision
        for mutation in ('battle_log', 'false_victory', 'future_event', 'skipped_month'):
            bad = self.game.export_save()
            if mutation == 'battle_log':
                bad['state']['battle']['log'] = {'bad': True}
            elif mutation == 'false_victory':
                bad['state']['battle']['outcome'] = 'victory'; bad['state']['phase'] = 'result'
            elif mutation == 'future_event':
                bad['state']['year_events'] = ['birth:san14-candidate-0001:250']
            else:
                bad['state']['month'] = 12
            bad['checksum'] = digest({k: v for k, v in bad.items() if k != 'checksum'})
            with self.assertRaises(GameError):
                self.game.load_save(bad, rev)
            self.assertEqual(self.game.to_dict(), original)
            self.assertEqual(self.game.revision, rev)

    def test_save_after_receipts_preserves_idempotency(self):
        ident = self.start()
        self.fight()
        self.cmd('settle', {'battle_id': ident})
        self.cmd('end_turn'); self.cmd('ai', {'turn': 1})
        saved = self.game.export_save()
        self.game.load_save(saved, self.game.revision)
        restored, rev = self.game.to_dict(), self.game.revision
        self.game.command('settle', {'battle_id': ident}, rev - 10)
        self.game.command('ai', {'turn': 1}, rev - 10)
        self.assertEqual(self.game.to_dict(), restored)
        self.assertEqual(self.game.revision, rev)

    def test_actual_annual_retirement_returns_troops_and_never_revives(self):
        for _ in range(40):
            self.cmd('end_turn'); self.cmd('ai', {'turn': self.game.state.turn})
        self.assertFalse(self.game.state.officers[123].alive)
        self.assertEqual(self.game.state.officers[123].troops, 0)
        self.assertNotIn(123, self.game.state.cities['nanyang'].roster.officer_ids)
        self.assertTrue(any('夏侯惇' in text and '释放兵员' in text for text in self.game.state.log))
        self.game.validate(self.game.state)

    def test_preexisting_dead_officer_crosses_retirement_with_save_and_single_receipt(self):
        self.game.command('new', {'faction': 'shu', 'seed': 314159}, self.game.revision)
        officer = self.game.state.officers[123]
        city = self.game.state.cities['nanyang']
        # Controlled legal already-dead record; ordinary demo combat only routs.
        city.reserves += officer.troops
        officer.troops = officer.health = officer.loyalty = 0
        officer.alive = False
        officer.faction_id = None
        city.roster.officer_ids.remove(123)
        self.game.validate(self.game.state)
        dead_before = deepcopy(officer)
        reserves_before = city.reserves
        ledger_before = self.game.state.soldiers.copy()
        for _ in range(37):
            self.cmd('end_turn'); self.cmd('ai', {'turn': self.game.state.turn})
        self.assertEqual((self.game.state.year, self.game.state.month), (220, 12))
        resumed = Campaign(self.game.catalog)
        resumed.load_save(self.game.export_save(), 0)
        self.assertEqual(resumed.to_dict(), self.game.to_dict())
        key = 'remove_after_death_year:san14-candidate-0124:221'
        for game in (self.game, resumed):
            game.command('end_turn', {}, game.revision)
            turn, revision = game.state.turn, game.revision
            game.command('ai', {'turn': turn}, revision)
            self.assertEqual((game.state.year, game.state.month), (221, 1))
            self.assertEqual(game.state.officers[123], dead_before)
            self.assertEqual(game.state.cities['nanyang'].reserves, reserves_before)
            self.assertEqual(game.state.soldiers, ledger_before)
            self.assertEqual(game.state.year_events.count(key), 1)
            after, current_revision = game.to_dict(), game.revision
            game.command('ai', {'turn': turn}, revision)
            self.assertEqual(game.to_dict(), after)
            self.assertEqual(game.revision, current_revision)
        self.assertEqual(resumed.to_dict(), self.game.to_dict())
        self.game.load_save(self.game.export_save(), self.game.revision)
        valid, revision = self.game.to_dict(), self.game.revision
        for bad_change in ('missing_receipt', 'revive'):
            bad = self.game.export_save()
            if bad_change == 'missing_receipt':
                bad['state']['year_events'].remove(key)
            else:
                bad['state']['officers']['123']['alive'] = True
            bad['checksum'] = digest({k: v for k, v in bad.items() if k != 'checksum'})
            with self.assertRaises(GameError):
                self.game.load_save(bad, revision)
            self.assertEqual(self.game.to_dict(), valid)
            self.assertEqual(self.game.revision, revision)
        self.cmd('end_turn'); self.cmd('ai', {'turn': self.game.state.turn})
        self.assertEqual(self.game.state.officers[123], dead_before)
        self.assertEqual(self.game.state.cities['nanyang'].reserves, reserves_before)
        self.assertEqual(self.game.state.year_events.count(key), 1)
        self.assertEqual(self.game.state.soldiers, ledger_before)

    def fixture_members(self, city_key, count):
        """Explicit synthetic test profiles only; production catalog untouched."""
        city = self.game.state.cities[city_key]
        free = [i for i in self.game.catalog.by_id if i not in self.game.state.officers]
        for ident in free[:count - len(city.roster.officer_ids)]:
            row = self.game.catalog.by_id[ident]
            person = PersonDefinition(row['person_id'], '受控测试人物', 150, 180, 280, 'controlled_test_fixture')
            profile = OfficerProfile(80, 60, 60, 60, 0)
            self.game.catalog.definitions[person.person_id] = person
            self.game.catalog.profiles[ident] = profile
            officer = initialize_officer(person, ident, profile, year=217, faction_id=city.owner,
                                         loyalty=70, troops=1, rules=self.game.catalog.rules)
            self.game.state.officers[ident] = officer
            city.roster.officer_ids.append(ident)
            self.game.state.soldiers['initial'] += 1

    def test_city20_world_invariant_and_departure10_separate(self):
        self.fixture_members('xiangyang', 20)
        self.game.validate(self.game.state)
        before = self.game.to_dict()
        with self.assertRaises(ValueError):
            self.cmd('depart', {'source': 'xiangyang', 'target': 'nanjun',
                                'officers': self.game.state.cities['xiangyang'].roster.officer_ids[:11]})
        self.assertEqual(before, self.game.to_dict())
        self.fixture_members('xiangyang', 21)
        with self.assertRaises(ValueError):
            self.game.validate(self.game.state)

    def test_nondeployed_defenders_troops_have_explicit_reserve_receiver(self):
        self.fixture_members('nanjun', 20)
        self.game.validate(self.game.state)
        ident = self.start(146, 999)
        self.assertEqual(len(self.game.state.battle['defenders']), 10)
        self.assertEqual(self.fight(), 'victory')
        reserves = self.game.state.cities['nanjun'].reserves
        self.cmd('settle', {'battle_id': ident})
        self.assertEqual(self.game.state.cities['nanjun'].reserves, reserves + 10)
        self.game.validate(self.game.state)

    def test_global_faction_and_resource_corruption_rejected(self):
        bad = deepcopy(self.game.state)
        bad.cities['nanjun'].roster.officer_ids.append(999)
        with self.assertRaises(ValueError):
            self.game.validate(bad)
        bad = deepcopy(self.game.state); bad.cities['xiangyang'].reserves -= 1
        with self.assertRaises(ValueError):
            self.game.validate(bad)


if __name__ == '__main__':
    unittest.main()
