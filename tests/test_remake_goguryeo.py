"""Goguryeo's opening territory and dated line of succession."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake import diplomacy
from remake.campaign import Campaign, Catalog


CAMPAIGNS = ROOT / 'game/data/campaigns'
RULERS = (
    ((179, 1), 'historical-goguryeo-gogukcheon', 1057),
    ((197, 5), 'historical-goguryeo-sansang', 1058),
    ((227, 5), 'historical-goguryeo-dongcheon', 1059),
    ((248, 9), 'historical-goguryeo-jungcheon', 1060),
)
RETAINER_OPENINGS = {
    '184-02': {'gyesu', 'queen-u'},
    '197-07': {'gyesu', 'queen-u', 'ugeo', 'yeonin', 'annyu', 'eulpaso'},
    '227-02': {'queen-u', 'goyuru'},
    '238-01': {'myeongnim-eosu', 'bak-wigeo'},
    '249-01': {'myeongnim-eosu', 'bak-wigeo', 'miru', 'yu-okgu', 'dayu'},
    '263-05': {'miru', 'yu-okgu', 'dayu', 'eumu', 'myeongnim-holdo'},
}


class Headless(Campaign):
    def view(self):
        return {'revision': self.revision}


class GoguryeoOpeningTests(unittest.TestCase):
    def start(self, path):
        game = Headless(Catalog(path))
        game.command('new', {'faction': 'goguryeo', 'seed': 2026}, 0)
        return game

    def test_all_openings_are_playable_with_one_capital_and_one_land_link(self):
        index = json.loads((CAMPAIGNS / 'index.json').read_text())
        openings = json.loads((ROOT / 'game/config/campaigns/city-expansion-openings.json').read_text())['scenarios']
        self.assertEqual(len(index['catalogs']), 29)
        for path in index['catalogs']:
            with self.subTest(scenario=path):
                game = self.start(ROOT / 'game/data' / path)
                state = game.state
                date = (state.year, state.month)
                _, person_id, runtime_id = next(row for row in reversed(RULERS) if row[0] <= date)
                self.assertEqual(game.catalog.ids[person_id], runtime_id)
                self.assertEqual(state.extension['leaders']['goguryeo'], runtime_id)
                self.assertEqual(game.catalog.factions['goguryeo']['city'], 'guonei')
                self.assertEqual(state.cities['guonei'].owner, 'goguryeo')
                self.assertIn(runtime_id, state.cities['guonei'].roster.officer_ids)
                self.assertTrue(all(state.officers[oid].faction_id == 'goguryeo'
                                    for oid in state.cities['guonei'].roster.officer_ids))
                self.assertEqual(state.officers[runtime_id].profile.terrain_affinity, 1)
                self.assertGreater(state.officers[runtime_id].troops, 0)
                self.assertEqual(game._neighbors('guonei', state), ['xuantu'])
                self.assertEqual(state.cities['xuantu'].owner, openings[game.catalog.data['id']]['owners']['xuantu'])
                self.assertEqual(diplomacy.allied(state, 'goguryeo', 'wei'), date == (238, 1))

    def test_retainers_match_their_service_windows_and_sources(self):
        for filename, expected in RETAINER_OPENINGS.items():
            with self.subTest(scenario=filename):
                game = self.start(CAMPAIGNS / (filename + '.json'))
                state = game.state
                roster = set(state.cities['guonei'].roster.officer_ids) - {state.extension['leaders']['goguryeo']}
                people = {state.officers[oid].person_id for oid in roster}
                self.assertEqual(people, {'historical-goguryeo-' + key for key in expected})
                for pid in people:
                    era = game.catalog.data['era_assignments'][pid]
                    self.assertEqual((era['status'], era['city']), ('serving', 'guonei'))
                    self.assertTrue(era['placement_review']['source_urls'])
        data = Catalog(CAMPAIGNS / '238-01.json').data
        pid = 'historical-goguryeo-nyuyu'
        self.assertEqual(data['appearance_windows'][pid][0]['start'], [245, 1])
        self.assertEqual(data['historical_exit_dates'][pid], [246, 10])
        late = Catalog(CAMPAIGNS / '249-01.json').data
        self.assertEqual(late['era_assignments'][pid]['status'], 'dead')
        self.assertEqual(late['appearance_windows'][pid], [])

    def test_dongcheon_appears_and_accepts_the_crown_in_may_227(self):
        game = self.start(CAMPAIGNS / '227-02.json')
        state = game.state
        self.assertEqual(state.extension['leaders']['goguryeo'], 1058)
        self.assertNotIn(1059, state.officers)
        while state.month < 5:
            game._complete_turn(state)
            game._reconcile_factions(state)
            game.validate(state)
        self.assertFalse(state.officers[1058].alive)
        self.assertEqual(state.extension['pending_succession']['goguryeo']['recruit'],
                         {'officer': 1059, 'city': 'guonei', 'declined': []})
        game.command('choose_successor', {'officer': 1059}, game.revision)
        self.assertEqual(game.state.extension['leaders']['goguryeo'], 1059)
        self.assertEqual(game.state.officers[1059].faction_id, 'goguryeo')
        self.assertNotIn('goguryeo', game.state.extension['pending_succession'])


if __name__ == '__main__':
    unittest.main()
