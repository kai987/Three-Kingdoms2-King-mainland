"""City inspection must use the selected catalog without affecting live play."""
from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,GameError
from remake.session import CampaignSession


class CityPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        if index['schema']!='tk2-campaign-index-v1' or len(index['catalogs'])!=25:
            raise AssertionError('Expected all25 current scenarios')
        paths=[ROOT/'game/data'/p for p in index['catalogs']]
        cls.session=CampaignSession(paths)

    @classmethod
    def tearDownClass(cls):
        del cls.session

    def test_all_catalog_previews_match_actual_opening_resources_and_rosters(self):
        s=self.session;before=s.to_dict();revision=s.revision;count=0
        for key,c in s.catalogs.items():
            self.assertEqual(c.data['schema'],'tk2-campaign-v1')
            self.assertRegex(key,r'^mainland\d{3}-\d{2}$')
            g=Campaign(c);g.state=g._new(next(iter(c.factions)),2026);g.validate(g.state)
            for ident,city in g.state.cities.items():
                preview=s.preview_city(key,ident);row=preview['city']
                self.assertEqual(preview['capacity'],c.rules.city_officer_capacity)
                self.assertEqual(row['terrain'],c.map_cities[ident].get('terrain'))
                self.assertEqual((row['owner'],row['gold'],row['grain'],row['reserves']),
                                 (city.owner,city.gold,city.grain,city.reserves))
                expected=[(i,c.by_id[i]['person_id'],c.name(i),g.state.officers[i].troops) for i in city.roster.officer_ids]
                self.assertEqual([(o['id'],o['person_id'],o['name'],o['troops']) for o in row['officers']],expected)
                count+=1
        self.assertEqual(count,sum(len(c.data['active_cities']) for c in s.catalogs.values()))
        self.assertGreaterEqual(count,2700)
        self.assertEqual(s.to_dict(),before);self.assertEqual(s.revision,revision)

    def test_preview_during_ai_uses_the_selected_opening_without_mutating_live_save(self):
        s=self.session
        s.command('new',{'scenario':'mainland217-07','faction':'shu','seed':2026},s.revision)
        city=s.game.state.cities['shujun'];ident=city.roster.officer_ids[0]
        s.command('allocate',{'city':'shujun','officer':ident,'troops':500},s.revision)
        s.command('end_turn',{},s.revision);saved=s.export_save();revision=s.revision
        preview=s.preview_city('mainland217-07','shujun')
        self.assertEqual(preview['city']['officers'][0]['troops'],300)
        expected=s.game.catalog.data['initial_city_resources']['shujun']
        self.assertEqual(preview['city']['reserves'],expected['reserves'])
        another=s.preview_city('mainland225-07','jianning')
        self.assertEqual(another['city']['owner'],'nanman')
        self.assertIsNotNone(another['city']['profile'])
        self.assertEqual(s.export_save(),saved);self.assertEqual(s.revision,revision)

    def test_bad_scenario_city_and_inactive_city_are_rejected_without_changing_play(self):
        s=self.session;before=s.to_dict();revision=s.revision
        current='mainland184-02'
        inactive=next(k for k in s.catalogs[current].map_cities if k not in s.catalogs[current].data['active_cities'])
        for scenario,city in ((None,'shujun'),([],None),('unknown','shujun'),(current,None),(current,{}),(current,'unknown'),(current,inactive)):
            with self.assertRaises(GameError):s.preview_city(scenario,city)
        self.assertEqual(s.to_dict(),before);self.assertEqual(s.revision,revision)

    def test_portrait_identity_comes_from_selected_preview_not_live_roster(self):
        s=self.session
        s.command('new',{'scenario':'mainland184-02','faction':'yellow_turban','seed':2026},s.revision)
        saved=s.export_save();revision=s.revision
        selected=s.catalogs['mainland190-01']
        newcomer=next(row for row in selected.data['initial_officers'] if selected.ids[row['person_id']] not in s.game.state.officers)
        self.assertNotIn(selected.ids[newcomer['person_id']],s.game.state.officers)
        preview=s.preview_city(selected.data['id'],newcomer['city'])
        row=next(row for row in preview['city']['officers'] if row['id']==selected.ids[newcomer['person_id']])
        self.assertEqual(row['person_id'],newcomer['person_id'])
        self.assertEqual(row['name'],selected.name(row['id']))
        self.assertEqual(s.export_save(),saved);self.assertEqual(s.revision,revision)


if __name__=='__main__':unittest.main()
