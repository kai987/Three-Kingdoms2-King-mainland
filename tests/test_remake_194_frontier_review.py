"""The194 opening represents Cao Cao's county bridgehead without owning Chenliu.

SGZ1/7/10 and ZZTJ61 place Chenliu in the Zhang Miao/Lu Bu coalition and
preserve Juancheng, Fan and Dong'e for Cao Cao. The pre-existing Jiyin node is
an explicit county proxy, rather than a claim about the whole commandery.
Zhang Miao's allied local command is represented separately from Lu Bu's army.
"""
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))

from build_campaigns import load_sources
from remake.campaign import Campaign, Catalog, canonical
from remake.map_presentation import city_names
from remake.session import faction_officer_counts


WEI_BRIDGEHEAD = {
    'san14-candidate-0102', 'san14-candidate-0115', 'san14-candidate-0124',
    'san14-candidate-0159', 'san14-candidate-0333', 'san14-candidate-0353',
    'san14-candidate-0393', 'san14-candidate-0460', 'san14-candidate-0499',
    'san14-candidate-0510', 'san14-candidate-0514', 'san14-candidate-0518',
    'san14-candidate-0521', 'san14-candidate-0689', 'san14-candidate-0702',
    'san14-candidate-0816', 'san14-candidate-0844',
    'san14-candidate-0980',
}
LU_BU_CHENLIU = {
    'san14-candidate-0108', 'san14-candidate-0212', 'san14-candidate-0456',
    'san14-candidate-0519',
}


class Frontier194ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Read canonical sources directly, independently of release generation.
        # Movement geometry is not under test, so its release hashes are unused.
        _, sources = load_sources(timing=False)
        cls.data = next(row for row in sources if row['id'] == 'mainland194-06')
        cls.other = next(row for row in sources if row['id'] == 'mainland190-01')
        cls.temp = tempfile.TemporaryDirectory(prefix='tk2-frontier194-')
        path = Path(cls.temp.name) / '194-06.json'
        path.write_text(json.dumps(cls.data, ensure_ascii=False))
        cls.catalog = Catalog(path)
        cls.people = json.loads((ROOT / 'game/config/campaigns/people.json').read_text())['people']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def game(self):
        game = Campaign(self.catalog)
        game.command('new', dict(faction='wei', seed=2026), 0)
        return game

    def test_capital_and_city_preview_distinguish_county_proxy_from_commandery(self):
        self.assertEqual(self.data['initial_owners']['chenliu'], 'zhang_miao')
        self.assertEqual(self.data['initial_owners']['jiyin'], 'wei')
        for city in ('dongjun', 'dongping', 'shanyang'):
            self.assertEqual(self.data['initial_owners'][city], 'lubu')
        self.assertEqual(self.catalog.factions['wei']['city'], 'jiyin')
        self.assertEqual(city_names(self.catalog, 194, 6)['jiyin'], '鄄城')
        # The alias is static for this campaign, with no invented future event.
        self.assertEqual(city_names(self.catalog, 240, 1)['jiyin'], '鄄城')
        other = type('OtherCatalog', (), {'data': self.other})()
        self.assertNotEqual(city_names(other, 194, 6)['jiyin'], '鄄城')
        proxy = self.data['main_scenario']['historical_review']['local_map_proxies']['jiyin']
        self.assertEqual(proxy['represents'], ['鄄城', '范', '東阿'])
        self.assertIn('並非聲稱', self.data['city_history']['jiyin']['control_review']['note'])

    def test_owner_corrections_relocate_people_without_switching_their_allegiances(self):
        game = self.game()
        postings = {pid: ('wei', 'jiyin') for pid in WEI_BRIDGEHEAD}
        postings.update({pid: ('lubu', 'dongjun') for pid in LU_BU_CHENLIU})
        postings['san14-candidate-0671'] = ('lubu', 'dongjun')  # Chen Gong
        postings['san14-candidate-0653'] = ('zhang_miao', 'chenliu')
        postings['san14-candidate-0647'] = ('zhang_miao', 'chenliu')
        self.assertEqual(len(postings), 25)
        for pid, (faction, city) in postings.items():
            with self.subTest(person_id=pid):
                ident = self.catalog.ids[pid]
                self.assertEqual(ident, self.people[pid]['runtime_id'])
                self.assertEqual(self.catalog.by_id[ident]['profile'], self.people[pid]['profile'])
                officer = game.state.officers[ident]
                self.assertEqual(officer.faction_id, faction)
                self.assertIn(ident, game.state.cities[city].roster.officer_ids)
                assignment = self.data['era_assignments'][pid]
                self.assertEqual((assignment['city'], assignment['faction']), (city, faction))
                self.assertEqual(self.data['appearance_locations'][pid], city)
        self.assertEqual(game.state.extension['leaders']['wei'], self.catalog.ids['san14-candidate-0521'])
        self.assertEqual(faction_officer_counts(self.catalog)['wei'], 32)
        self.assertEqual(faction_officer_counts(self.catalog)['lubu'], 19)
        self.assertEqual(faction_officer_counts(self.catalog)['zhang_miao'], 2)
        self.assertEqual(len(self.data['initial_officers']), 291)
        self.assertEqual(len(self.catalog.ids), 1030)

    def test_primary_postings_and_authorial_garrisons_keep_separate_evidence(self):
        for pid in ('san14-candidate-0393', 'san14-candidate-0124',
                    'san14-candidate-0689',
                    'san14-candidate-0671'):
            review = self.data['era_assignments'][pid]['placement_review']
            self.assertEqual(review['historical_certainty'], 'primary_text_affiliation')
            self.assertIn('https://zh.wikisource.org/zh-hant/資治通鑑/卷061', review['source_urls'])
        garrison = self.data['era_assignments']['san14-candidate-0115']['placement_review']
        self.assertEqual(garrison['historical_certainty'], 'authorial_garrison_relocation')
        self.assertEqual(self.data['placement_completion']['reference_classes'],
                         dict(Counter(row['placement_review']['historical_certainty']
                                      for row in self.data['era_assignments'].values())))
        self.assertEqual(self.data['placement_completion']['bases'],
                         dict(Counter(row['placement_review']['basis']
                                      for row in self.data['era_assignments'].values())))

    def test_monthly_appearance_and_signed_reload_do_not_restore_old_postings(self):
        game = self.game()
        before = {ident: officer.faction_id for ident, officer in game.state.officers.items()}
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)
        self.assertEqual(before, {ident: officer.faction_id for ident, officer in game.state.officers.items()})
        self.assertEqual(game.state.cities['chenliu'].owner, 'zhang_miao')
        self.assertEqual(game.state.cities['jiyin'].owner, 'wei')
        self.assertIn(self.catalog.ids['san14-candidate-0521'],
                      game.state.cities['jiyin'].roster.officer_ids)
        for city in game.state.cities.values():
            self.assertLessEqual(len(city.roster.officer_ids), 99)
            for ident in city.roster.officer_ids:
                self.assertEqual(game.state.officers[ident].faction_id, city.owner)
        saved = game.export_save()
        loaded = Campaign(self.catalog)
        loaded.load_save(saved, 0)
        self.assertEqual(canonical(loaded.export_save()), canonical(saved))


if __name__ == '__main__':
    unittest.main()
