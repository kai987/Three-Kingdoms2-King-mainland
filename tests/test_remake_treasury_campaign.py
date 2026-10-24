"""Current campaign integration, including views, ownership and saved rewards."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake.campaign import Campaign, Catalog, digest
from remake.city_economy import tier_at
from remake.errors import GameError
from remake.session import CampaignSession
from remake import treasures
from campaign_fixtures import controlled_catalog, reach_battle


def altered_catalog(change):
    data = deepcopy(controlled_catalog().data)
    change(data)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'treasury.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class TreasuryCampaignTests(unittest.TestCase):
    def game(self, catalog=None, seed=2026):
        game = Campaign(catalog or controlled_catalog())
        game.command('new', dict(faction='shu', seed=seed), 0)
        return game

    def cmd(self, game, command, **payload):
        return game.command(command, payload, game.revision)

    def fails(self, game, command, **payload):
        before, revision, journal = game.export_save(), game.revision, deepcopy(game.journal)
        with self.assertRaises((GameError, ValueError)):
            self.cmd(game, command, **payload)
        self.assertEqual(game.export_save(), before)
        self.assertEqual(game.revision, revision)
        self.assertEqual(game.journal, journal)

    def test_all_29_openings_and_previews_match_treasure_without_sampling_or_mutating(self):
        index = json.loads((ROOT / 'game/data/campaigns/index.json').read_text())
        self.assertEqual(len(index['catalogs']), 29)
        session = CampaignSession([ROOT / 'game/data' / name for name in index['catalogs']])
        neutral = owned = 0
        for catalog in session.catalogs.values():
            with self.subTest(scenario=catalog.data['id']):
                faction = next(iter(catalog.factions))
                session.command('new', dict(scenario=catalog.data['id'], faction=faction,
                                            seed=2026), session.revision)
                game, state = session.game, session.game.state
                original, revision = session.export_save(), session.revision
                self.assertEqual(state.rng.draws, 0)
                total = 0
                for key, city in state.cities.items():
                    expected = 0 if city.owner == 'neutral' else {
                        'normal': 2, 'large': 4, 'giant': 6}[tier_at(catalog.data, key, state.year, state.month)]
                    self.assertEqual(treasures.count(state, key), expected)
                    self.assertEqual(session.preview_city(catalog.data['id'], key)['city']['treasure'], expected)
                    total += expected
                    neutral += city.owner == 'neutral'
                    owned += city.owner != 'neutral'
                self.assertEqual(state.extension['treasury']['ledger'],
                                 dict(initial=total, found=0, spent=0, sold=0, lost=0))
                one, two = session.view(), session.view()
                self.assertEqual(one['catalog']['treasury'], two['catalog']['treasury'])
                one['catalog']['treasury']['factions'][faction]['policy']['enabled'] = True
                next(iter(one['catalog']['treasury']['cities'].values()))['treasure'] = 99
                self.assertEqual(session.export_save(), original)
                self.assertEqual(session.revision, revision)
                game.validate(state)
        self.assertGreater(neutral, 0)
        self.assertGreater(owned, 0)

    def test_reward_command_changes_only_paid_gold_loyalty_actions_and_receipt(self):
        game = self.game()
        city = game.state.cities['xiangyang']
        target = 146
        game.state.officers[target].loyalty = 20
        before = game.to_dict()
        governor = game.state.extension['treasury']['cities'][city.id]['governor']
        amount, virtue = 100, game.state.officers[governor].profile.virtue
        expected = max(1, (amount * (50 + virtue) + 2999) // 3000)
        self.cmd(game, 'reward_officer', city=city.id, officer=target, kind='gold', amount=amount)
        after = game.to_dict()
        self.assertEqual(after['rng'], before['rng'])
        self.assertEqual(after['soldiers'], before['soldiers'])
        expected_people = deepcopy(before['officers'])
        expected_people[str(target)]['loyalty'] += expected
        self.assertEqual(after['officers'], expected_people)
        expected_cities = deepcopy(before['cities'])
        expected_cities[city.id]['gold'] -= amount
        expected_cities[city.id]['action_used'] = True
        self.assertEqual(after['cities'], expected_cities)
        self.assertEqual(after['extension']['treasury'], before['extension']['treasury'])
        self.assertEqual(after['extension']['officer_actions'], {str(governor): game.state.turn})
        event = after['extension']['events']['items'][-1]
        self.assertEqual(event['kind'], 'officer_rewarded')
        self.assertEqual(event['details']['gain'], expected)
        self.assertEqual(event['person_ids'], [game.state.officers[governor].person_id,
                                               game.state.officers[target].person_id])
        self.fails(game, 'reward_officer', city=city.id, officer=target, kind='gold', amount=1)
        game.validate(game.state)

    def test_malformed_or_unavailable_commands_preserve_entire_transaction(self):
        game = self.game()
        ruler = game.state.extension['leaders']['shu']
        for kind, payload in (
            ('reward_officer', dict(city='xiangyang', officer=ruler, kind='gold', amount=10)),
            ('reward_officer', dict(city='xiangyang', officer=146, kind='gold', amount=0)),
            ('reward_officer', dict(city='xiangyang', officer=146, kind='gold', amount=True)),
            ('reward_officer', dict(city='xiangyang', officer=146, kind='treasure', amount=2)),
            ('reward_officer', dict(city='xiangyang', officer=146, kind='gold', amount=1, extra=1)),
            ('search_treasure', dict(city='nanyang', actor=123)),
            ('search_treasure', dict(city='xiangyang', actor=123)),
            ('search_treasure', dict(city='xiangyang', actor=True)),
            ('sell_treasure', dict(city='xiangyang', actor=146, amount=100)),
            ('set_governor', dict(city='xiangyang', officer=123)),
            ('set_treasury_policy', dict(faction='wei', policy={'enabled': True})),
            ('set_treasury_policy', dict(faction='shu', policy={'gold_budget': -1})),
        ):
            with self.subTest(command=kind, payload=payload):
                self.fails(game, kind, **payload)

    def test_search_and_save_load_replay_keep_exact_next_rng_and_treasure(self):
        for seed in (1, 2):
            with self.subTest(seed=seed):
                game = self.game(seed=seed)
                before = game.export_save()
                rng = deepcopy(game.state.rng)
                actor = 146
                profile = game.state.officers[actor].profile
                chance = max(15, min(80, 20 + profile.intellect // 3 + profile.virtue // 5))
                success = rng.next() % 100 < chance
                self.cmd(game, 'search_treasure', city='xiangyang', actor=actor)
                self.assertEqual(game.state.rng, rng)
                self.assertEqual(treasures.count(game.state, 'xiangyang'),
                    before['state']['extension']['treasury']['cities']['xiangyang']['treasure'] + int(success))
                self.assertEqual(game.state.extension['events']['items'][-1]['kind'],
                                 'treasure_found' if success else 'treasure_search_failed')
                saved = game.export_save()
                twin = Campaign(game.catalog)
                twin.load_save(saved, 0)
                self.assertEqual(twin.export_save(), saved)
                for current in (game, twin):
                    turn = current.state.turn
                    self.cmd(current, 'end_turn')
                    self.cmd(current, 'ai', turn=turn)
                self.assertEqual(game.export_save(), twin.export_save())
                self.assertEqual(game.state.rng, twin.state.rng)

    def test_treasury_and_event_tampering_is_rejected_on_real_save_load(self):
        game = self.game()
        self.cmd(game, 'reward_officer', city='xiangyang', officer=146, kind='treasure', amount=1)
        saved, revision = game.export_save(), game.revision
        for mutation in (
            lambda value: value['state']['extension']['treasury']['ledger'].update(spent=0),
            lambda value: value['state']['extension']['treasury']['cities']['xiangyang'].update(treasure=True),
            lambda value: value['state']['extension']['treasury']['cities']['xiangyang'].update(governor=123),
            lambda value: value['state']['extension']['events']['items'][-1]['details'].update(gain=0),
        ):
            bad = deepcopy(saved)
            mutation(bad)
            bad['checksum'] = digest({key: value for key, value in bad.items() if key != 'checksum'})
            with self.assertRaises(GameError):
                game.load_save(bad, revision)
            self.assertEqual(game.export_save(), saved)
            self.assertEqual(game.revision, revision)

    def test_player_and_ai_auto_rewards_use_same_service_and_preview_formula(self):
        player = self.game()
        self.cmd(player, 'set_treasury_policy', faction='shu',
                 policy=dict(enabled=True, target_loyalty=99, gold_budget=37, gold_floor=100))
        target = 146
        player.state.officers[target].loyalty = 20
        ai = Campaign(player.catalog)
        ai.load_save(player.export_save(), 0)
        ai.state.player, ai.state.phase = 'wu', 'ai'
        with patch.object(treasures, 'reward', wraps=treasures.reward) as service:
            player_result = treasures.auto_turn(player, player.state, 'shu')
            ai_result = treasures.auto_turn(ai, ai.state, 'shu')
        self.assertEqual(service.call_count, 2)
        self.assertEqual(player_result, ai_result)
        self.assertEqual(player.state.officers, ai.state.officers)
        self.assertEqual(player.state.cities, ai.state.cities)
        self.assertEqual(player.state.extension['treasury'], ai.state.extension['treasury'])
        self.assertEqual(player.state.rng, ai.state.rng)
        self.assertLessEqual(sum(r['amount'] for r in player_result if r['kind'] == 'gold'), 37)
        player.validate(player.state)
        ai.validate(ai.state)

    def test_dated_city_inherits_a_quarter_once_without_initial_mint_or_rng(self):
        def setup(data):
            data['city_foundings'] = {'wuchang': dict(year=217, month=12, parent='jiangxia', resource_divisor=4)}
        game = self.game(altered_catalog(setup))
        treasures.credit(game.state, 'jiangxia', 7, reason='found')
        before = deepcopy(game.state.extension['treasury']['ledger'])
        inherit = treasures.inherit_city
        def checked_inherit(state, *args):
            rng = deepcopy(state.rng)
            result = inherit(state, *args)
            self.assertEqual(state.rng, rng, 'City inheritance itself must never sample campaign RNG')
            return result
        with patch.object(treasures, 'inherit_city', side_effect=checked_inherit) as service:
            for _ in range(3):
                turn = game.state.turn
                self.cmd(game, 'end_turn')
                self.cmd(game, 'ai', turn=turn)
            service.assert_called_once_with(game.state, 'wuchang', 'jiangxia')
        self.assertEqual((game.state.year, game.state.month, game.state.day), (217, 12, 1))
        self.assertEqual(game.state.cities['wuchang'].owner, game.state.cities['jiangxia'].owner)
        self.assertEqual(treasures.count(game.state, 'wuchang'), 2)
        self.assertEqual(treasures.count(game.state, 'jiangxia'), 7)
        self.assertEqual(game.state.extension['treasury']['ledger'], before)
        game._open_dated_cities(game.state)
        self.assertEqual(treasures.count(game.state, 'wuchang'), 2)
        self.assertEqual(treasures.count(game.state, 'jiangxia'), 7)
        game.validate(game.state)
        twin = Campaign(game.catalog)
        twin.load_save(game.export_save(), 0)
        self.assertEqual(game.export_save(), twin.export_save())

    def test_actual_capture_preserves_treasure_and_uses_present_new_governor(self):
        game = self.game()
        treasures.credit(game.state, 'nanjun', 3, reason='found')
        ledger = deepcopy(game.state.extension['treasury']['ledger'])
        self.cmd(game, 'allocate', city='xiangyang', officer=146, troops=999)
        self.cmd(game, 'depart', source='xiangyang', target='nanjun', officers=[146])
        battle_id = reach_battle(game)
        for _ in range(500):
            battle = game.state.battle
            if game.state.phase == 'result':
                break
            actor = next(row['id'] for row in battle['attackers'] if row['troops'] > 0 and row['id'] not in battle['used'])
            target = next(row['id'] for row in battle['defenders'] if row['troops'] > 0)
            self.cmd(game, 'attack', battle_id=battle_id, actor=actor, target=target)
        self.assertEqual(game.state.battle['outcome'], 'victory')
        self.cmd(game, 'settle', battle_id=battle_id)
        row = game.state.extension['treasury']['cities']['nanjun']
        self.assertEqual((row['owner'], row['treasure'], row['governor_mode']), ('shu', 3, 'auto'))
        self.assertIn(row['governor'], game.state.cities['nanjun'].roster.officer_ids)
        self.assertEqual(game.state.extension['treasury']['ledger'], ledger)
        game.validate(game.state)

    def test_succession_replaces_dead_manual_governor_with_actual_chosen_ruler(self):
        game = self.game()
        ruler = game.state.extension['leaders']['shu']
        self.cmd(game, 'set_governor', city='xiangyang', officer=ruler)
        person, city = game.state.officers[ruler], game.state.cities['xiangyang']
        city.reserves += person.troops
        person.troops, person.alive, person.faction_id, person.loyalty = 0, False, None, 0
        city.roster.officer_ids.remove(ruler)
        game._reconcile_factions(game.state)
        pending = game.state.extension['pending_succession']['shu']
        self.assertEqual(game.state.extension['treasury']['cities'][city.id]['governor_mode'], 'auto')
        self.assertEqual(game.state.extension['treasury']['cities'][city.id]['governor'], pending['provisional'])
        self.fails(game, 'reward_officer', city=city.id, officer=146, kind='gold', amount=1)
        choice = pending['candidates'][-1]
        self.cmd(game, 'choose_successor', officer=choice)
        self.assertEqual(game.state.extension['treasury']['cities'][city.id]['governor'], choice)
        self.assertEqual(game.state.officers[choice].loyalty, 100)
        self.fails(game, 'reward_officer', city=city.id, officer=choice, kind='gold', amount=1)
        game.validate(game.state)


if __name__ == '__main__':
    unittest.main()
