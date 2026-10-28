"""Shared faction orders, conserved receipts and current-save initialization."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import command_books as books
from campaign_fixtures import controlled_catalog


class CommandBooks(unittest.TestCase):
    def setUp(self):
        self.game = Campaign(controlled_catalog())
        self.cmd('new', dict(faction='shu', seed=2026))

    def cmd(self, kind, payload=None):
        return self.game.command(kind, payload or {}, self.game.revision)

    def test_original_table_is_exact_and_expanded_map_keeps_the_original_cap(self):
        evidence = json.loads((ROOT / 'game/config/references/original-command-books-v1.json').read_text())
        self.assertEqual(list(books.TOTAL_BY_CITIES), evidence['original_table']['values'])
        self.assertEqual(books.total(0), 0)
        self.assertEqual([books.total(n) for n in (1, 3, 4, 5, 6, 8, 9, 13, 17, 20, 24, 28, 30, 115)],
                         [3, 3, 4, 5, 7, 7, 8, 9, 10, 11, 12, 13, 13, 13])
        for invalid in (-1, True, 1.2, '3', 513):
            with self.assertRaises(ValueError):
                books.total(invalid)

    def test_whole_faction_pool_can_be_spent_repeatedly_in_one_city(self):
        start = deepcopy(self.game.state)
        city = start.cities['xiangyang']
        total = books.remaining(start, 'shu')
        for used in range(1, total + 1):
            self.cmd('recruit', dict(city=city.id))
            self.assertEqual(books.remaining(self.game.state, 'shu'), total - used)
            self.assertTrue(self.game.state.cities[city.id].action_used)
        current = self.game.state.cities[city.id]
        self.assertEqual(current.reserves, city.reserves + 100 * total)
        self.assertEqual(current.gold, city.gold - 20 * total)
        self.assertEqual(current.grain, city.grain - 30 * total)
        self.assertEqual(self.game.state.rng.draws, start.rng.draws)
        self.assertEqual(books.remaining(self.game.state, 'wei'), books.remaining(start, 'wei'))

    def test_exhausted_pool_rejects_atomically_and_management_is_still_available(self):
        for _ in range(books.remaining(self.game.state, 'shu')):
            self.cmd('recruit', dict(city='xiangyang'))
        before, revision = self.game.export_save(), self.game.revision
        for kind, payload in (
                ('recruit', dict(city='xiangyang')),
                ('allocate', dict(city='xiangyang', officer=999, troops=300)),
                ('depart', dict(source='xiangyang', target='nanjun', officers=[999]))):
            with self.assertRaises(GameError):
                self.cmd(kind, payload)
            self.assertEqual(self.game.export_save(), before)
            self.assertEqual(self.game.revision, revision)
        self.cmd('set_domestic', dict(faction='shu', policy={'auto_recruit': False}))
        self.assertEqual(books.remaining(self.game.state, 'shu'), 0)

    def test_manual_assignment_is_one_order_and_invalid_assignment_is_not_charged(self):
        total = books.remaining(self.game.state, 'shu')
        self.cmd('allocate', dict(city='xiangyang', officer=999, troops=300))
        self.assertEqual(books.remaining(self.game.state, 'shu'), total - 1)
        before = self.game.export_save()
        with self.assertRaises((ValueError, GameError)):
            self.cmd('allocate', dict(city='xiangyang', officer=999, troops=1000))
        self.assertEqual(self.game.export_save(), before)

    def test_new_turn_replaces_remaining_orders_instead_of_accumulating(self):
        self.cmd('recruit', dict(city='xiangyang'))
        rng = deepcopy(self.game.state.rng)
        self.game._complete_turn(self.game.state)
        self.assertEqual(self.game.state.turn, 2)
        self.assertEqual(self.game.state.day, 11)
        self.assertEqual(books.remaining(self.game.state, 'shu'), 3)
        self.assertEqual(self.game.state.extension['command_books']['turn'], 2)
        self.assertEqual(self.game.state.extension['command_books']['factions']['shu']['orders'], [])
        self.assertEqual(self.game.state.rng, rng)
        self.game.validate(self.game.state)

    def test_views_do_not_refill_and_save_round_trip_preserves_the_balance(self):
        self.cmd('recruit', dict(city='xiangyang'))
        raw = self.game.export_save()
        for _ in range(3):
            view = self.game.view()
            self.assertEqual(view['catalog']['command_books']['factions']['shu']['remaining'], 2)
            self.assertEqual(self.game.export_save(), raw)
        self.game.load_save(raw, self.game.revision)
        self.assertEqual(self.game.export_save(), raw)

    def test_current_catalog_legacy_import_accounts_for_already_used_cities_once(self):
        self.cmd('recruit', dict(city='xiangyang'))
        raw = self.game.export_save()
        raw['version'] = 1
        del raw['state']['extension']['command_books']
        raw['checksum'] = digest({k: v for k, v in raw.items() if k != 'checksum'})
        self.game.load_save(raw, self.game.revision)
        row = self.game.state.extension['command_books']['factions']['shu']
        self.assertEqual((row['legacy_used'], row['used'], books.remaining(self.game.state, 'shu')), (1, 1, 2))
        current = self.game.export_save()
        self.game.load_save(current, self.game.revision)
        self.assertEqual(self.game.export_save(), current)

    def test_present_but_invalid_book_ledger_is_rejected_without_reset(self):
        self.cmd('recruit', dict(city='xiangyang'))
        original = self.game.export_save()
        for edit in (
                lambda pool: pool.update(turn=2),
                lambda pool: pool['factions']['shu'].update(used=0),
                lambda pool: pool['factions']['shu'].update(total=99),
                lambda pool: pool['factions']['shu'].update(city_count=28, total=13),
                lambda pool: pool['factions']['shu']['orders'][0].update(cost=True),
                lambda pool: pool['factions'].pop('wei')):
            raw = deepcopy(original)
            edit(raw['state']['extension']['command_books'])
            raw['checksum'] = digest({k: v for k, v in raw.items() if k != 'checksum'})
            with self.assertRaises(GameError):
                self.game.load_save(raw, self.game.revision)
            self.assertEqual(self.game.export_save(), original)

    def test_current_format_never_imports_a_missing_ledger_as_a_legacy_balance(self):
        for _ in range(3):
            self.cmd('recruit', dict(city='xiangyang'))
        original = self.game.export_save()
        self.assertEqual(original['version'], 2)
        raw = deepcopy(original)
        del raw['state']['extension']['command_books']
        raw['checksum'] = digest({k: v for k, v in raw.items() if k != 'checksum'})
        with self.assertRaises(GameError):
            self.game.load_save(raw, self.game.revision)
        self.assertEqual(self.game.export_save(), original)
        raw = deepcopy(original)
        raw['version'] = 1
        raw['checksum'] = digest({k: v for k, v in raw.items() if k != 'checksum'})
        with self.assertRaises(GameError):
            self.game.load_save(raw, self.game.revision)
        self.assertEqual(self.game.export_save(), original)

    def test_pool_is_shared_between_cities_and_fixed_until_the_next_refresh(self):
        state = self.game.state
        source, other = state.cities['xiangyang'], state.cities['nanjun']
        original_owner = other.owner
        other.owner = 'shu'
        books.spend(state, source, 'recruit')
        books.spend(state, other, 'recruit')
        self.assertEqual(books.remaining(state, 'shu'), 1)
        self.assertEqual(state.extension['command_books']['factions']['shu']['city_count'], 1)
        other.owner = original_owner
        self.game.validate(state)

    def test_all_29_openings_use_the_same_read_only_budget_service(self):
        count = 0
        for path in sorted((ROOT / 'game/data/campaigns').glob('*.json')):
            if path.name == 'index.json':
                continue
            campaign = Campaign(Catalog(path))
            faction = next(row['id'] for row in campaign.catalog.data['factions']
                           if row['id'] != 'neutral' and row['id'] in campaign.catalog.data['initial_owners'].values())
            campaign.command('new', dict(faction=faction, seed=2026), 0)
            before = campaign.export_save()
            for owner in campaign.catalog.factions:
                owned = sum(c.owner == owner for c in campaign.state.cities.values())
                self.assertEqual(books.remaining(campaign.state, owner), books.total(owned))
            self.assertEqual(campaign.view()['catalog']['command_books']['refresh_days'], 10)
            self.assertEqual(campaign.export_save(), before)
            count += 1
        self.assertEqual(count, 29)


if __name__ == '__main__':
    unittest.main()
