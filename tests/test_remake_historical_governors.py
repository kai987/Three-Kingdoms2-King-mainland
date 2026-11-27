from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from remake.campaign import Campaign, Catalog
from remake.map_presentation import city_names
from remake.session import CampaignSession


CAMPAIGNS = ROOT / "game/data/campaigns"


class HistoricalOpeningGovernorsTests(unittest.TestCase):
    def test_each_opening_applies_reviewed_resident_governors(self):
        paths = sorted(CAMPAIGNS.glob('[0-9]*.json'))
        self.assertEqual(len(paths), 29)
        for path in paths:
            with self.subTest(scenario=path.stem):
                catalog = Catalog(path)
                game = Campaign(catalog)
                state = game._new('observer', 2026)
                appointments = catalog.data['initial_governors']
                self.assertTrue(appointments)
                for city, post in appointments.items():
                    ident = catalog.ids[post['person_id']]
                    row = state.extension['treasury']['cities'][city]
                    self.assertEqual((row['governor'], row['governor_mode']), (ident, 'historical'))
                    self.assertIn(ident, state.cities[city].roster.officer_ids)
                    self.assertEqual(state.officers[ident].faction_id, state.cities[city].owner)

    def test_longyou_names_and_staff_before_the_expedition(self):
        session = CampaignSession([CAMPAIGNS / '219-07.json', CAMPAIGNS / '227-02.json'])
        early = session.catalogs['mainland219-07']
        later = session.catalogs['mainland227-02']
        self.assertEqual(city_names(early, 219, 7)['tianshui'], '漢陽')
        self.assertEqual(city_names(later, 227, 2)['tianshui'], '天水')
        for city, governor, staff in [('longxi', 'san14-candidate-0851', 'historical-ma-yong-longxi'),
                                      ('tianshui', 'san14-candidate-0764', 'san14-candidate-0408')]:
            row = session.preview_city('mainland227-02', city)['city']
            self.assertEqual(row['governor'], later.ids[governor])
            self.assertIn(staff, {officer['person_id'] for officer in row['officers']})
        officer = later.profiles[later.ids['san14-candidate-0408']]
        self.assertEqual((officer.martial_strength, officer.intellect, officer.virtue), (51, 38, 39))
