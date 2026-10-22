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
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']
        for folder in ('eras','eras-v3','main-scenarios','main-scenarios-v5','main-scenarios-v6'):
            index=json.loads((ROOT/f'game/data/{folder}/index.json').read_text())
            paths.extend(ROOT/'game/data'/p for p in index['catalogs'])
        cls.session=CampaignSession(paths)

    def test_all_catalog_previews_match_actual_opening_resources_and_rosters(self):
        s=self.session;before=s.to_dict();revision=s.revision;count=0
        for key,c in s.catalogs.items():
            g=Campaign(c);g.command('new',{'faction':next(iter(c.factions)),'seed':2026},0)
            for ident,city in g.state.cities.items():
                preview=s.preview_city(key,ident);row=preview['city']
                self.assertEqual(preview['capacity'],c.rules.city_officer_capacity)
                self.assertEqual(row['terrain'],c.map_cities[ident].get('terrain'))
                self.assertEqual((row['owner'],row['gold'],row['grain'],row['reserves']),
                                 (city.owner,city.gold,city.grain,city.reserves))
                expected=[(i,c.by_id[i]['person_id'],c.name(i),g.state.officers[i].troops) for i in city.roster.officer_ids]
                self.assertEqual([(o['id'],o['person_id'],o['name'],o['troops']) for o in row['officers']],expected)
                count+=1
        self.assertGreater(count,4000)
        self.assertEqual(s.to_dict(),before);self.assertEqual(s.revision,revision)

    def test_preview_during_ai_uses_the_selected_opening_without_mutating_live_save(self):
        s=self.session
        s.command('new',{'scenario':'mainland217-07-v6','faction':'shu','seed':2026},s.revision)
        city=s.game.state.cities['shujun'];ident=city.roster.officer_ids[0]
        s.command('allocate',{'city':'shujun','officer':ident,'troops':500},s.revision)
        s.command('end_turn',{},s.revision);saved=s.export_save();revision=s.revision
        preview=s.preview_city('mainland217-07-v6','shujun')
        self.assertEqual(preview['city']['officers'][0]['troops'],300)
        self.assertEqual(preview['city']['reserves'],2400)
        old=s.preview_city('mainland217-07-v5','shujun')
        self.assertEqual(old['city']['reserves'],1200)
        self.assertIsNone(old['city']['profile'])
        self.assertEqual(s.export_save(),saved);self.assertEqual(s.revision,revision)

    def test_bad_scenario_city_and_inactive_city_are_rejected_without_changing_play(self):
        s=self.session;before=s.to_dict();revision=s.revision
        demo=next(key for key,c in s.catalogs.items() if len(c.data['active_cities'])==4)
        inactive=next(k for k in s.catalogs[demo].map_cities if k not in s.catalogs[demo].data['active_cities'])
        for scenario,city in ((None,'shujun'),([],None),('unknown','shujun'),(demo,None),(demo,{}),(demo,'unknown'),(demo,inactive)):
            with self.assertRaises(GameError):s.preview_city(scenario,city)
        self.assertEqual(s.to_dict(),before);self.assertEqual(s.revision,revision)

    def test_portrait_identity_comes_from_preview_catalog_when_old_save_lacks_person(self):
        s=CampaignSession([ROOT/'game/data/main-scenarios-v5/184-02.json',
                           ROOT/'game/data/main-scenarios-v14/190-01.json'])
        s.command('new',{'scenario':'mainland184-02-v5','faction':'yellow_turban','seed':2026},s.revision)
        saved=s.export_save();revision=s.revision
        selected=s.catalogs['mainland190-01-v14']
        newcomer=next(row for row in selected.data['initial_officers'] if selected.ids[row['person_id']]>=1000)
        self.assertNotIn(newcomer['person_id'],s.game.catalog.ids)
        preview=s.preview_city(selected.data['id'],newcomer['city'])
        row=next(row for row in preview['city']['officers'] if row['id']==selected.ids[newcomer['person_id']])
        self.assertEqual(row['person_id'],newcomer['person_id'])
        self.assertEqual(row['name'],selected.name(row['id']))
        self.assertEqual(s.export_save(),saved);self.assertEqual(s.revision,revision)


if __name__=='__main__':unittest.main()
