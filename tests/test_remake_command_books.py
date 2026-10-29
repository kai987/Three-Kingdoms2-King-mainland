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
            self.cmd('allocate', dict(city='xiangyang', officer=999, troops=1001))
        self.assertEqual(self.game.export_save(), before)

    def test_city_wide_distribution_pays_once_across_multiple_officers(self):
        city = self.game.state.cities['xiangyang']
        first, second = city.roster.officer_ids[:2]
        before = deepcopy(self.game.state)
        self.cmd('allocate', dict(city=city.id, officer=first,
            troops=before.officers[first].troops + 20, flow=None))
        active = books.active_allocation(self.game.state, 'shu', city.id)
        self.assertIsNotNone(active)
        self.cmd('allocate', dict(city=city.id, officer=second,
            troops=before.officers[second].troops + 30, flow=active['id']))
        self.assertEqual(books.remaining(self.game.state, 'shu'), books.remaining(before, 'shu') - 1)
        self.assertEqual(self.game.state.cities[city.id].reserves, before.cities[city.id].reserves - 50)
        self.assertEqual(self.game.state.rng, before.rng)
        row = self.game.state.extension['command_books']['factions']['shu']
        self.assertEqual(len(row['orders']), 1)
        self.assertEqual(row['orders'][0]['allocation_flow'], active['id'])
        self.game.validate(self.game.state)

    def test_confirmed_batch_commits_all_officers_and_pays_only_one_book(self):
        before = deepcopy(self.game.state)
        city = before.cities['xiangyang']
        first, second, unchanged = city.roster.officer_ids[:3]
        self.cmd('allocate', dict(city=city.id, allocations=[
            dict(officer=first, troops=1000), dict(officer=second, troops=0),
            dict(officer=unchanged, troops=before.officers[unchanged].troops)], flow=None))
        state = self.game.state
        self.assertEqual((state.officers[first].troops, state.officers[second].troops), (1000, 0))
        delta = 1000 - before.officers[first].troops - before.officers[second].troops
        self.assertEqual(state.cities[city.id].reserves, city.reserves - delta)
        self.assertEqual(state.soldiers, before.soldiers)
        self.assertEqual(state.rng, before.rng)
        row = state.extension['command_books']['factions']['shu']
        self.assertEqual((row['used'], len(row['orders'])), (1, 1))
        active = books.active_allocation(state, 'shu', city.id)
        self.assertEqual(row['orders'][0], dict(city=city.id, kind='allocate', cost=1,
                                              allocation_flow=active['id']))
        self.game.validate(state)

    def test_zero_sum_batch_reassigns_without_temporary_negative_reserves(self):
        state = self.game.state
        city = state.cities['xiangyang']
        state.soldiers['initial'] -= city.reserves
        city.reserves = 0
        first, second = city.roster.officer_ids[:2]
        total = state.officers[first].troops + state.officers[second].troops
        before = deepcopy(state)
        # The increase comes first, but the whole confirmation is one exchange.
        self.cmd('allocate', dict(city=city.id, allocations=[
            dict(officer=first, troops=total), dict(officer=second, troops=0)]))
        self.assertEqual(self.game.state.cities[city.id].reserves, 0)
        self.assertEqual((self.game.state.officers[first].troops,
                          self.game.state.officers[second].troops), (total, 0))
        self.assertEqual(books.remaining(self.game.state, 'shu'), books.remaining(before, 'shu') - 1)
        self.assertEqual(self.game.state.soldiers, before.soldiers)
        self.assertEqual(self.game.state.rng, before.rng)
        self.game.validate(self.game.state)

    def test_unchanged_batch_and_capability_views_do_not_charge_or_open_a_flow(self):
        city = self.game.state.cities['xiangyang']
        before = self.game.export_save()
        for _ in range(2):
            self.cmd('allocate', dict(city=city.id, allocations=[
                dict(officer=i, troops=self.game.state.officers[i].troops)
                for i in city.roster.officer_ids], flow=None))
            self.assertEqual(self.game.view()['catalog']['command_books']['allocation_batch'], 'confirm-v1')
            self.assertEqual(self.game.export_save(), before)
            self.assertIsNone(books.active_allocation(self.game.state, 'shu'))
        for _ in range(3):
            self.cmd('recruit', dict(city=city.id))
        before = self.game.export_save()
        self.cmd('allocate', dict(city=city.id, allocations=[
            dict(officer=city.roster.officer_ids[0],
                 troops=self.game.state.officers[city.roster.officer_ids[0]].troops)]))
        self.assertEqual(self.game.export_save(), before, 'No-op confirmation also needs no available book')

    def test_invalid_batches_reject_every_entry_before_payment_or_mutation(self):
        city = self.game.state.cities['xiangyang']
        first, second = city.roster.officer_ids[:2]
        valid = dict(officer=first, troops=200)
        payloads = [dict(city=city.id, allocations=rows) for rows in (
            None, {}, [], [valid] * 100, [valid, valid], [valid, None],
            [valid, dict(officer=second)], [valid, dict(officer=second, troops=200, extra=True)],
            [valid, dict(officer=second, troops=True)], [valid, dict(officer=True, troops=200)],
            [valid, dict(officer=second, troops=-1)], [valid, dict(officer=second, troops=1001)],
            [valid, dict(officer=1200, troops=200)],
            [valid, dict(officer=self.game.state.cities['nanyang'].roster.officer_ids[0], troops=200)]
        )]
        payloads.extend([dict(city=city.id, allocations=[valid], officer=first),
                         dict(city=city.id, allocations=[valid], troops=200),
                         dict(city=city.id, allocations=[valid], flow='forged')])
        before, revision = self.game.export_save(), self.game.revision
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises((GameError, ValueError)):
                    self.cmd('allocate', payload)
                self.assertEqual(self.game.export_save(), before)
                self.assertEqual(self.game.revision, revision)

    def test_batch_checks_combined_reserves_and_rejects_marching_members(self):
        city = self.game.state.cities['xiangyang']
        first, second = city.roster.officer_ids[:2]
        before, revision = self.game.export_save(), self.game.revision
        with self.assertRaises(GameError):
            self.cmd('allocate', dict(city=city.id, allocations=[
                dict(officer=first, troops=1000), dict(officer=second, troops=1000)]))
        self.assertEqual(self.game.export_save(), before)
        self.assertEqual(self.game.revision, revision)
        self.cmd('depart', dict(source=city.id, target='nanyang', officers=[second]))
        before, revision = self.game.export_save(), self.game.revision
        with self.assertRaises(GameError):
            self.cmd('allocate', dict(city=city.id, allocations=[
                dict(officer=first, troops=200), dict(officer=second, troops=0)]))
        self.assertEqual(self.game.export_save(), before)
        self.assertEqual(self.game.revision, revision)

    def test_paid_recruitment_batch_survives_save_and_uses_existing_flow_once(self):
        self.cmd('recruit', dict(city='xiangyang', allocation_flow=True))
        state = self.game.state
        first, second = state.cities['xiangyang'].roster.officer_ids[:2]
        active = books.active_allocation(state, 'shu')
        before = deepcopy(state)
        payload = dict(city='xiangyang', allocations=[
            dict(officer=first, troops=state.officers[first].troops + 20),
            dict(officer=second, troops=state.officers[second].troops + 30)], flow=active['id'])
        revision = self.game.revision
        self.cmd('allocate', payload)
        self.assertEqual(books.remaining(self.game.state, 'shu'), books.remaining(before, 'shu'))
        self.assertEqual(self.game.state.cities['xiangyang'].reserves, before.cities['xiangyang'].reserves - 50)
        self.assertEqual(self.game.state.rng, before.rng)
        saved = self.game.export_save()
        clone = Campaign(self.game.catalog)
        clone.load_save(json.loads(json.dumps(saved)), 0)
        self.assertEqual(clone.export_save(), saved)
        self.assertEqual(books.active_allocation(clone.state, 'shu'), active)
        with self.assertRaises(GameError):
            self.game.command('allocate', payload, revision)
        self.assertEqual(self.game.export_save(), saved)
        self.cmd('allocation_close', dict(city='xiangyang', flow=active['id']))
        closed, revision = self.game.export_save(), self.game.revision
        with self.assertRaises(GameError):
            self.cmd('allocate', payload)
        self.assertEqual(self.game.export_save(), closed)
        self.assertEqual(self.game.revision, revision)

    def test_last_book_pays_one_whole_batch_and_paid_flow_covers_later_confirmation(self):
        for _ in range(2):
            self.cmd('recruit', dict(city='xiangyang'))
        first, second = self.game.state.cities['xiangyang'].roster.officer_ids[:2]
        self.cmd('allocate', dict(city='xiangyang', allocations=[
            dict(officer=first, troops=200), dict(officer=second, troops=220)], flow=None))
        self.assertEqual(books.remaining(self.game.state, 'shu'), 0)
        active = books.active_allocation(self.game.state, 'shu')
        before, revision = self.game.export_save(), self.game.revision
        changed = dict(city='xiangyang', allocations=[dict(officer=first, troops=201)])
        with self.assertRaises(GameError):
            self.cmd('allocate', changed)
        self.assertEqual(self.game.export_save(), before)
        self.assertEqual(self.game.revision, revision)
        self.cmd('allocate', dict(changed, flow=active['id']))
        self.assertEqual(books.remaining(self.game.state, 'shu'), 0)
        self.assertEqual(len(self.game.state.extension['command_books']['factions']['shu']['orders']), 3)
        self.game.validate(self.game.state)

    def test_no_change_invalid_and_duplicate_requests_never_buy_a_new_flow(self):
        city = self.game.state.cities['xiangyang'];ident = city.roster.officer_ids[0]
        before = self.game.export_save()
        self.cmd('allocate', dict(city=city.id, officer=ident,
            troops=self.game.state.officers[ident].troops, flow=None))
        self.assertEqual(self.game.export_save(), before)
        self.assertIsNone(books.active_allocation(self.game.state, 'shu'))
        for troops in (-1, 1001, True):
            with self.assertRaises((GameError, ValueError)):
                self.cmd('allocate', dict(city=city.id, officer=ident, troops=troops, flow=None))
            self.assertEqual(self.game.export_save(), before)
        revision = self.game.revision
        payload = dict(city=city.id, officer=ident, troops=200, flow=None)
        self.game.command('allocate', payload, revision)
        paid = self.game.export_save()
        with self.assertRaises(GameError):self.game.command('allocate', payload, revision)
        self.assertEqual(self.game.export_save(), paid)

    def test_last_book_covers_remaining_city_distribution_but_not_a_new_flow(self):
        for _ in range(2):self.cmd('recruit', dict(city='xiangyang'))
        first, second = self.game.state.cities['xiangyang'].roster.officer_ids[:2]
        self.cmd('allocate', dict(city='xiangyang', officer=first, troops=200, flow=None))
        active = books.active_allocation(self.game.state, 'shu')
        self.assertEqual(books.remaining(self.game.state, 'shu'), 0)
        self.cmd('allocate', dict(city='xiangyang', officer=second, troops=250, flow=active['id']))
        paid = self.game.export_save()
        for flow in (None, 'invented-credit'):
            with self.assertRaises(GameError):
                self.cmd('allocate', dict(city='xiangyang', officer=second, troops=251, flow=flow))
            self.assertEqual(self.game.export_save(), paid)
        self.game.validate(self.game.state)

    def test_paid_recruitment_opens_the_same_distribution_without_second_charge(self):
        city = self.game.state.cities['xiangyang'];ident = city.roster.officer_ids[0]
        before = deepcopy(self.game.state)
        self.cmd('recruit', dict(city=city.id, allocation_flow=True))
        active = books.active_allocation(self.game.state, 'shu')
        self.assertEqual(active['source'], 'recruit')
        self.cmd('allocate', dict(city=city.id, officer=ident,
            troops=before.officers[ident].troops + 100, flow=active['id']))
        self.assertEqual(books.remaining(self.game.state, 'shu'), books.remaining(before, 'shu') - 1)
        self.assertEqual(self.game.state.cities[city.id].reserves, before.cities[city.id].reserves)
        self.assertEqual(self.game.state.cities[city.id].gold, before.cities[city.id].gold - 20)
        self.assertEqual(self.game.state.cities[city.id].grain, before.cities[city.id].grain - 30)

    def test_close_and_reopen_are_scoped_and_delayed_close_cannot_end_new_flow(self):
        ident = self.game.state.cities['xiangyang'].roster.officer_ids[0]
        self.cmd('allocate', dict(city='xiangyang', officer=ident, troops=200, flow=None))
        previous = books.active_allocation(self.game.state, 'shu')
        self.cmd('allocation_close', dict(city='xiangyang', flow=previous['id']))
        self.assertIsNone(books.active_allocation(self.game.state, 'shu'))
        before = self.game.export_save()
        with self.assertRaises(GameError):
            self.cmd('allocate', dict(city='xiangyang', officer=ident, troops=201, flow=previous['id']))
        self.assertEqual(self.game.export_save(), before)
        self.cmd('allocate', dict(city='xiangyang', officer=ident, troops=201, flow=None))
        current = books.active_allocation(self.game.state, 'shu')
        self.assertNotEqual(current['id'], previous['id'])
        before = self.game.export_save()
        self.cmd('allocation_close', dict(city='xiangyang', flow=previous['id']))
        self.assertEqual(self.game.export_save(), before)
        self.assertEqual(books.remaining(self.game.state, 'shu'), 1)

    def test_flow_survives_raw_save_and_expires_on_real_commands_and_turn(self):
        ident = self.game.state.cities['xiangyang'].roster.officer_ids[0]
        self.cmd('allocate', dict(city='xiangyang', officer=ident, troops=200, flow=None))
        active = books.active_allocation(self.game.state, 'shu')
        saved = json.loads(json.dumps(self.game.export_save()))
        clone = Campaign(self.game.catalog);clone.load_save(saved, 0)
        self.assertEqual(clone.export_save(), saved)
        clone.command('allocate', dict(city='xiangyang', officer=ident, troops=201, flow=active['id']), clone.revision)
        self.assertEqual(books.remaining(clone.state, 'shu'), 2)
        self.cmd('set_domestic', dict(faction='shu', policy={'auto_recruit': False}))
        self.assertIsNone(books.active_allocation(self.game.state, 'shu'))
        self.assertEqual(books.remaining(self.game.state, 'shu'), 2)
        self.cmd('allocate', dict(city='xiangyang', officer=ident, troops=201, flow=None))
        self.game._complete_turn(self.game.state)
        self.assertIsNone(books.active_allocation(self.game.state, 'shu'))
        self.assertNotIn('allocation', self.game.state.extension['command_books']['factions']['shu'])

    def test_flow_cannot_move_payment_to_another_city_or_faction(self):
        from test_remake_facility_campaign import facility_catalog
        game = Campaign(facility_catalog());game.command('new', dict(faction='shu', seed=2026), 0)
        city = game.state.cities['xiangyang'];other = game.state.cities['nanjun']
        ident = city.roster.officer_ids[0]
        game.command('allocate', dict(city=city.id, officer=ident, troops=200, flow=None), game.revision)
        active = books.active_allocation(game.state, 'shu')
        before = game.export_save()
        with self.assertRaises(GameError):
            game.command('allocate', dict(city=other.id, officer=other.roster.officer_ids[0],
                troops=200, flow=active['id']), game.revision)
        self.assertEqual(game.export_save(), before)
        enemy = game.state.cities['nanyang']
        with self.assertRaises(GameError):
            game.command('allocate', dict(city=enemy.id, officer=enemy.roster.officer_ids[0],
                troops=200, flow=active['id']), game.revision)
        self.assertEqual(game.export_save(), before)

    def test_forged_or_broken_flow_receipts_are_rejected_atomically(self):
        ident = self.game.state.cities['xiangyang'].roster.officer_ids[0]
        self.cmd('allocate', dict(city='xiangyang', officer=ident, troops=200, flow=None))
        saved = self.game.export_save()
        for edit in (
                lambda r:r['allocation'].update(serial=2),
                lambda r:r['allocation']['active'].update(receipt=True),
                lambda r:r['allocation']['active'].update(id='invented'),
                lambda r:r['allocation']['active'].update(city='nanyang'),
                lambda r:r['orders'][0].update(kind='transfer'),
                lambda r:r['orders'][0].pop('allocation_flow'),
                lambda r:r.pop('allocation')):
            changed = deepcopy(saved)
            edit(changed['state']['extension']['command_books']['factions']['shu'])
            changed['checksum'] = digest({k:v for k,v in changed.items() if k!='checksum'})
            with self.assertRaises(GameError):self.game.load_save(changed, self.game.revision)
            self.assertEqual(self.game.export_save(), saved)

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
                lambda pool: pool['factions']['shu'].update(allocation=None),
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
