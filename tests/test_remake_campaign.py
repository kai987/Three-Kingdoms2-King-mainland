"""Current campaign transactions, battles and saved progress."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, GameError, digest
from remake.officers import initialize_officer, PersonDefinition, OfficerProfile
from remake.march_supply import estimate
from campaign_fixtures import controlled_catalog, reach_battle


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(controlled_catalog())
        self.game.command('new', {'faction': 'shu', 'seed': 2026}, 0)

    def cmd(self, kind, payload=None):
        return self.game.command(kind, payload or {}, self.game.revision)

    def start(self, ident=999, troops=600, target='nanjun', source='xiangyang'):
        self.cmd('allocate', dict(city=source, officer=ident, troops=troops))
        self.cmd('depart', dict(source=source, target=target, officers=[ident]))
        return reach_battle(self.game)

    def fight(self):
        for _ in range(500):
            b = self.game.state.battle
            if self.game.state.phase == 'result':
                return b['outcome']
            actor = next(u['id'] for u in b['attackers'] if u['troops'] > 0 and u['id'] not in b['used'])
            target = next(u['id'] for u in b['defenders'] if u['troops'] > 0)
            self.cmd('attack', dict(battle_id=b['id'], actor=actor, target=target))
        self.fail('Battle did not finish')

    def test_real_high_ids_and_current_roster_rules(self):
        self.assertEqual(self.game.catalog.name(255), '阿会喃')
        self.assertEqual(self.game.catalog.name(999), '伊籍')
        self.assertEqual(len(self.game.catalog.definitions), 1027)
        self.assertEqual(len(self.game.state.officers), 7)
        self.assertEqual(self.game.catalog.rules.city_officer_capacity, 99)
        self.game.validate(self.game.state)

    def test_invalid_commands_preserve_state_rng_and_revision(self):
        original, revision = self.game.to_dict(), self.game.revision
        for kind, payload in [('allocate', dict(city='xiangyang', officer=999, troops=1000)),
                ('depart', dict(source='xiangyang', target='jiangxia', officers=[999])),
                ('depart', dict(source='xiangyang', target='nanjun', officers=[999, 999])),
                ('allocate', dict(city='nanjun', officer=255, troops=30))]:
            with self.assertRaises(ValueError):
                self.cmd(kind, payload)
            self.assertEqual(self.game.to_dict(), original)
            self.assertEqual(self.game.revision, revision)

    def test_allocating_and_queuing_conserve_soldiers_and_charge_once(self):
        ledger = self.game.state.soldiers.copy()
        self.cmd('allocate', dict(city='xiangyang', officer=999, troops=600))
        self.assertEqual(self.game.state.cities['xiangyang'].reserves, 680)
        self.assertEqual(self.game.state.rng.draws, 0)
        self.assertFalse(self.game.state.cities['xiangyang'].action_used)
        self.cmd('depart', dict(source='xiangyang', target='nanjun', officers=[999]))
        row=self.game.state.extension['travel']['marches'][0]
        self.assertEqual(self.game.state.cities['xiangyang'].grain,
                         3800-estimate(self.game.state,[999],row['quote']))
        self.assertEqual(row['supply']['consumed'],0)
        self.assertEqual(self.game.state.soldiers, ledger)
        self.assertIn(999, self.game.state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual(self.game.state.phase, 'city')

    def test_victory_and_duplicate_settlement_commit_once(self):
        battle_id = self.start(146, 999)
        self.assertEqual(self.fight(), 'victory')
        self.assertEqual(self.game.state.cities['nanjun'].owner, 'neutral')
        revision = self.game.revision
        self.cmd('settle', dict(battle_id=battle_id))
        committed = self.game.to_dict()
        self.assertEqual(self.game.state.cities['nanjun'].owner, 'shu')
        self.assertIn(146, self.game.state.cities['nanjun'].roster.officer_ids)
        self.assertNotIn(146, self.game.state.cities['xiangyang'].roster.officer_ids)
        self.game.command('settle', dict(battle_id=battle_id), revision)
        self.assertEqual(self.game.to_dict(), committed)
        self.assertEqual(self.game.state.settled_battles, [battle_id])
        self.game.validate(self.game.state)

    def test_racing_settlement_does_not_duplicate_capture(self):
        battle_id = self.start(146, 999)
        self.fight()
        revision = self.game.revision
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.game.command('settle', dict(battle_id=battle_id), revision), range(2)))
        self.assertEqual(results[0]['game'], results[1]['game'])
        self.assertEqual(self.game.revision, revision + 1)
        self.assertEqual(len(self.game.state.settled_battles), 1)

    def test_defeat_is_rout_and_preserves_identity(self):
        self.game.command('new', dict(faction='wu', seed=2026), self.game.revision)
        battle_id = self.start(178, 1, 'nanjun', 'jiangxia')
        self.assertEqual(self.fight(), 'defeat')
        self.cmd('settle', dict(battle_id=battle_id))
        self.assertEqual(self.game.state.officers[178].troops, 0)
        self.assertTrue(self.game.state.officers[178].alive)
        self.assertIn(178, self.game.state.cities['jiangxia'].roster.officer_ids)

    def test_retreat_uses_actual_losses_and_paid_supplies(self):
        self.game.command('new', dict(faction='wei', seed=2026), self.game.revision)
        battle_id = self.start(123, 480, 'xiangyang', 'nanyang')
        target = self.game.state.battle['defenders'][0]['id']
        self.cmd('attack', dict(battle_id=battle_id, actor=123, target=target))
        remaining = self.game.state.battle['attackers'][0]['troops']
        paid_grain = self.game.state.cities['nanyang'].grain
        self.cmd('retreat', dict(battle_id=battle_id))
        self.cmd('settle', dict(battle_id=battle_id))
        self.assertEqual(self.game.state.officers[123].troops, remaining)
        self.assertEqual(self.game.state.cities['nanyang'].grain, paid_grain)
        self.assertEqual(self.game.state.cities['xiangyang'].owner, 'shu')

    def test_ten_day_ai_receipt_is_idempotent(self):
        for _ in range(3):
            turn = self.game.state.turn
            self.cmd('end_turn')
            revision = self.game.revision
            self.cmd('ai', dict(turn=turn))
            after, committed = self.game.to_dict(), self.game.revision
            self.game.command('ai', dict(turn=turn), revision)
            self.assertEqual(self.game.to_dict(), after)
            self.assertEqual(self.game.revision, committed)
        self.assertEqual((self.game.state.year, self.game.state.month, self.game.state.day), (217, 12, 1))
        self.assertEqual(self.game.state.completed_ai_turns, [1, 2, 3])

    def test_midbattle_save_restores_exact_next_action_and_rng(self):
        battle_id = self.start(146, 180, 'nanyang')
        self.cmd('attack', dict(battle_id=battle_id, actor=146, target=123))
        twin = Campaign(self.game.catalog)
        twin.load_save(self.game.export_save(), 0)
        self.assertEqual(self.game.to_dict(), twin.to_dict())
        payload = dict(battle_id=battle_id, actor=146, target=123)
        self.cmd('attack', payload)
        twin.command('attack', payload, twin.revision)
        self.assertEqual(self.game.to_dict(), twin.to_dict())

    def test_bad_checksum_and_semantic_mutations_are_atomic(self):
        self.start()
        original, revision = self.game.to_dict(), self.game.revision
        for change in ('checksum', 'resource', 'battle', 'calendar', 'scenario'):
            bad = self.game.export_save()
            if change == 'checksum': bad['checksum'] = 'broken'
            elif change == 'resource': bad['state']['cities']['xiangyang']['gold'] = -1
            elif change == 'battle': bad['state']['battle']['log'] = {'invalid': True}
            elif change == 'calendar': bad['state']['calendar_cursor'] += 1
            else: bad['scenario'] = 'mainland217-07-v15'
            if change != 'checksum': bad['checksum'] = digest({k: v for k, v in bad.items() if k != 'checksum'})
            with self.assertRaises(GameError): self.game.load_save(bad, revision)
            self.assertEqual(self.game.to_dict(), original)
            self.assertEqual(self.game.revision, revision)

    def test_tactic_consumes_energy_action_and_roundtrips(self):
        battle_id = self.start(146, 400, 'nanyang')
        support = self.game.state.battle['extended']['support']['146']
        before = support['energy']
        self.cmd('tactic', dict(battle_id=battle_id, actor=146, target=123, tactic=0))
        self.assertLess(self.game.state.battle['extended']['support']['146']['energy'], before)
        self.game.validate(self.game.state)
        restored = Campaign(self.game.catalog)
        restored.load_save(self.game.export_save(), 0)
        self.assertEqual(restored.to_dict(), self.game.to_dict())

    def test_dead_officer_is_not_revived_and_retirement_receipt_is_unique(self):
        officer = self.game.state.officers[123]
        city = self.game.state.cities['nanyang']
        city.reserves += officer.troops
        officer.troops = officer.health = officer.loyalty = 0
        officer.alive = False; officer.faction_id = None
        city.roster.officer_ids.remove(123)
        self.game._reconcile_factions(self.game.state)
        for _ in range(38 * 3):
            self.game._complete_turn(self.game.state)
            self.game._spawn_eligible(self.game.state)
            self.game._reconcile_factions(self.game.state)
            self.game.validate(self.game.state)
        self.assertEqual((self.game.state.year, self.game.state.month), (221, 1))
        self.assertFalse(self.game.state.officers[123].alive)
        key = 'remove_after_death_year:san14-candidate-0124:221'
        self.assertEqual(self.game.state.year_events.count(key), 1)
        restored = Campaign(self.game.catalog)
        restored.load_save(self.game.export_save(), 0)
        self.assertEqual(restored.to_dict(), self.game.to_dict())


if __name__ == '__main__': unittest.main()
