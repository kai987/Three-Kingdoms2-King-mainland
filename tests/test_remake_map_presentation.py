"""Preview data and city labels must never rewrite a campaign/save catalog."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.map_presentation import city_names,presentation
from remake.session import CampaignSession


class MapPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']
        for folder in ('eras','eras-v3','main-scenarios','main-scenarios-v5'):
            index=json.loads((ROOT/f'game/data/{folder}/index.json').read_text())
            paths.extend(ROOT/'game/data'/p for p in index['catalogs'])
        cls.paths=paths

    def test_state_seat_city_labels_and212_name_change_are_presentation_only(self):
        s=CampaignSession(self.paths)
        expected={'shujun':'成都','jingzhao':'长安','henan':'洛阳','danyang':'建业','wei':'邺',
                  'shanyang':'昌邑','taiyuan':'晋阳','qi':'临淄','wuwei':'姑臧','jiujiang':'寿春',
                  'nanjun':'江陵','nanhai':'番禺','yan':'蓟','anping':'信都'}
        names={c['id']:c['name'] for c in s.view()['catalog']['cities']}
        self.assertEqual({k:names[k] for k in expected},expected)
        self.assertEqual(s.game.catalog.map_cities['shujun']['name'],'蜀郡')
        self.assertEqual(s.game.catalog.map_cities['danyang']['name'],'丹阳')
        self.assertEqual(names['fanyang'],'范阳') # Not the蓟 city node.
        self.assertEqual(names['yizhou'],'夷洲')
        for year,expected_name in ((190,'秣陵'),(211,'秣陵'),(212,'建业'),(238,'建业')):
            self.assertEqual(city_names(s.game.catalog,year)['danyang'],expected_name)
        self.assertEqual(s.game.catalog.map_cities['yingchuan']['name'],'颍川')
        for year,expected_name in ((184,'许县'),(220,'许县'),(221,'许昌'),(238,'许昌')):
            self.assertEqual(city_names(s.game.catalog,year)['yingchuan'],expected_name)

    def test_all39_previews_use_their_own_opening_ownership_and_active_domain(self):
        s=CampaignSession(self.paths);view=s.view()
        self.assertEqual(len(view['catalog']['scenarios']),39)
        for option in view['catalog']['scenarios']:
            c=s.catalogs[option['id']]
            self.assertEqual(option['initial_owners'],c.data['initial_owners'])
            self.assertEqual(option['active_cities'],c.data['active_cities'])
            for key in option['active_cities']:self.assertIn(key,option['initial_owners'])
            self.assertTrue(set(option['initial_owners'].values())<={*c.factions,'neutral'})
            self.assertTrue(set(c.factions)<=set(presentation()['colors']))
        self.assertIsNone(s.game.state);self.assertEqual(s.revision,0)

    def test_preview_and_alias_views_do_not_change_live_state_catalog_or_old_saves(self):
        s=CampaignSession(self.paths)
        for scenario in ('mainland217-07-v5','mainland190-01-v4','jingxiang217-v1'):
            c=s.catalogs[scenario]
            s.command('new',{'scenario':scenario,'faction':next(iter(c.factions)),'seed':2026},s.revision)
            save=s.export_save();data=deepcopy(c.data);state=s.to_dict();revision=s.revision
            s.view();s.view()
            self.assertEqual(s.revision,revision);self.assertEqual(s.to_dict(),state)
            self.assertEqual(s.export_save(),save);self.assertEqual(c.data,data)
            s.load_save(save,s.revision);self.assertEqual(s.to_dict(),state)

    def test_background_and_native_mask_are_auditable_and_rebuild_is_deterministic(self):
        meta=presentation()
        self.assertEqual(meta['colors']['neutral'],'#ffffff')
        self.assertTrue({'danyang','yingchuan','shujun','yinping'}<=set(meta['labelled_city_ids']))
        self.assertEqual(meta['background_sha256'],hashlib.sha256((ROOT/'game'/meta['background'].lstrip('/')).read_bytes()).hexdigest())
        self.assertEqual(hashlib.sha256((ROOT/'game/assets/map.png').read_bytes()).hexdigest(),
                         '30946ef6877db09f7fb44c7d0cfe729614983613619095428ff3a270c0881edd')
        plan=json.loads((ROOT/'expansion/map/city-map-city-sea-plan-v42.json').read_text())
        pixels=[[x*4-16,y*4-16] for y,row in enumerate(plan['originalSprite']['rows']) for x,value in enumerate(row) if value==6]
        self.assertEqual(meta['castle_fill_pixels'],pixels)
        files=list((ROOT/'game/data').rglob('*.json'))+[ROOT/'game/assets/map-presentation.json']
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'-B','game/build_map_presentation.py'],cwd=ROOT,check=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


if __name__=='__main__':unittest.main()
