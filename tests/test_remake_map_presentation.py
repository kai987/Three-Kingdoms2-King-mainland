"""Preview data and city labels must never rewrite a campaign/save catalog."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
sys.path.insert(0,str(ROOT/'game'))
from remake.map_presentation import city_names,presentation
from remake.session import CampaignSession
from build_map_presentation import road_center_corrections
from road_centers import build as build_road_centers


class MapPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        if index['schema']!='tk2-campaign-index-v1' or len(index['catalogs'])!=29:
            raise AssertionError('Expected29 current campaign catalogs')
        cls.paths=[ROOT/'game/data'/p for p in index['catalogs']]

    def test_state_seat_city_labels_and212_name_change_are_presentation_only(self):
        # This assertion covers late-era names; the public menu now starts184.
        s=CampaignSession(self.paths, initial_scenario='mainland217-07')
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

    def test_all_current_previews_use_their_own_opening_ownership_and_active_domain(self):
        s=CampaignSession(self.paths);view=s.view()
        self.assertEqual(len(view['catalog']['scenarios']),29)
        for option in view['catalog']['scenarios']:
            c=s.catalogs[option['id']]
            self.assertEqual(option['initial_owners'],c.data['initial_owners'])
            self.assertEqual(option['active_cities'],c.data['active_cities'])
            for key in option['active_cities']:self.assertIn(key,option['initial_owners'])
            self.assertTrue(set(option['initial_owners'].values())<={*c.factions,'neutral'})
            self.assertEqual(set(option['faction_colors']),{*c.factions,'neutral'})
            self.assertEqual(option['faction_colors']['neutral'],'#ffffff')
        self.assertIsNone(s.game.state);self.assertEqual(s.revision,0)

    def test_preview_and_alias_views_do_not_change_current_state_catalog_or_saves(self):
        s=CampaignSession([ROOT/'game/data/campaigns'/f'{date}.json' for date in ('184-02','190-01','217-07')])
        for scenario in ('mainland217-07','mainland190-01','mainland184-02'):
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
        source=json.loads((ROOT/'game/config/map-source.json').read_text())
        self.assertEqual(source['schema'],'tk2-map-source-v1')
        ground_sha=hashlib.sha256((ROOT/'game/map-source/hydrology-ground.png').read_bytes()).hexdigest()
        self.assertEqual(meta['inactive_castle_ground_sha256'],ground_sha)
        self.assertEqual(meta['inactive_castle_ids'],['yiyang','yidu'])
        self.assertEqual(meta['inactive_castle_ground'],'/assets/map-city-ground.png')
        base=deepcopy(meta);base.pop('road_center_corrections');base.pop('road_bridges');base.pop('inactive_castle_ground_sha256');base.pop('city_road_bed')
        self.assertEqual(source['presentation'],base)
        self.assertEqual(set(source['approved_asset_sha256']),
                         {'map.png','map-basin.png','map-campaign.png','map-clean.png','map-navigation.png','map-road-centers.png'})
        for name,expected in source['approved_asset_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'game/assets'/name).read_bytes()).hexdigest(),expected,name)
        sprite=source['native_castle_sprite'];self.assertEqual((sprite['width'],sprite['height']),(8,8))
        pixels=[[x*4-16,y*4-16] for y,row in enumerate(sprite['rows']) for x,value in enumerate(row) if value==6]
        self.assertEqual(meta['castle_fill_pixels'],pixels)
        outline=[[x*4-16,y*4-16] for y,row in enumerate(sprite['rows']) for x,value in enumerate(row) if value==2]
        self.assertEqual(meta['castle_outline_pixels'],outline)
        self.assertEqual(json.loads((ROOT/'game/assets/city-positions.json').read_text()),source['anchors'])
        files=self.paths+[ROOT/'game/data/campaigns/index.json',ROOT/'game/assets/map-presentation.json',ROOT/'game/assets/city-positions.json']
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'-B','game/build_map_presentation.py'],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'-B','game/build_map_anchors.py'],cwd=ROOT,check=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})

    def test_native_road_corrections_bind_current_sources_and_keep_runtime_audit_compact(self):
        source=json.loads((ROOT/'game/config/map-source.json').read_text())
        meta=presentation()['road_center_corrections']
        actual=road_center_corrections(ROOT,source['approved_asset_sha256'])
        self.assertEqual(meta,actual)
        self.assertEqual(meta['schema'],'tk2-road-center-corrections-v1')
        self.assertEqual(meta['backgrounds'],{'/assets/map-navigation.png':'/assets/map-road-centers.png'})
        self.assertEqual(len(meta['hubs']),58)
        self.assertEqual(meta['summary'],dict(reviewed_hubs=58,visible_hubs=12,changed_segments=334,
                                             deleted_spokes=165,protected_hubs=0))
        for field in ('ground','provenance','protected_hubs','changes','removed_obsolete_paths','mask_d','paint_d','corridor_repairs'):
            self.assertNotIn(field,meta,'The compact center audit does not duplicate full source metadata')
        for hub in meta['hubs']:
            self.assertEqual(set(hub),{'city','center','old_hub'})
        shared=json.loads((ROOT/'game/config/campaigns/shared.json').read_text())
        positions={city['id']:city['position'] for city in shared['catalog']['cities']}
        full=build_road_centers(json.loads((ROOT/'game/config/road-centers.json').read_text()),positions)
        bed=presentation()['city_road_bed']
        self.assertEqual(bed['schema'],'tk2-city-road-bed-v1')
        self.assertEqual(bed['ground'],'/assets/map-city-ground.png')
        self.assertEqual(bed['path'],full['paint_d'])
        self.assertEqual(bed['repair_path'],full['mask_d'])
        self.assertEqual(len(full['hubs']),meta['summary']['reviewed_hubs'])
        self.assertEqual(len(full['protected_hubs']),meta['summary']['protected_hubs'])
        self.assertEqual(len(full['changes']),meta['summary']['changed_segments'])
        self.assertEqual(sum(row['deleted'] for row in full['changes']),meta['summary']['deleted_spokes'])
        self.assertEqual([row['index'] for row in full['removed_obsolete_paths']],[4,339])
        rows={row['index']:row for row in full['changes']}
        self.assertEqual(rows[55]['new_points'][-1],[434,270])
        self.assertTrue(rows[61]['deleted'])
        self.assertEqual(rows[62]['new_points'][0],[434,270])
        for name in ('map-navigation.png','map-road-centers.png'):
            raw=(ROOT/'game/assets'/name).read_bytes()
            self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual((int.from_bytes(raw[16:20],'big'),int.from_bytes(raw[20:24],'big')),(1352,1024))
        catalog_files=self.paths+[ROOT/'game/data/campaigns/index.json']
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in catalog_files}
        road_center_corrections(ROOT,source['approved_asset_sha256'])
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in catalog_files})

    def test_stale_road_render_sources_positions_assets_and_pins_are_rejected(self):
        source=json.loads((ROOT/'game/config/map-source.json').read_text())
        manifest_path='game/map-source/road-centers-render.json'
        required=('game/config/road-centers.json','game/config/campaigns/shared.json',
                  'game/assets/map-navigation.png','game/map-source/road-ground.png',
                  'game/assets/map-road-centers.png',manifest_path,
                  'game/config/water-corrections.json','game/map-source/water-render.json',
                  'game/map-source/hydrology-ground.png','game/map-source/terrain-under-water.png',
                  'game/map-source/historic-water.svg','game/map-source/sea-shadow.svg')
        originals={name:(ROOT/name).read_bytes() for name in required}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,raw in originals.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            manifest=json.loads(originals[manifest_path])
            for field in ('source_sha256','positions_sha256','baseline_sha256','ground_sha256','output_sha256','water_render_sha256'):
                with self.subTest(field=field):
                    altered=dict(manifest);altered[field]='0'*64
                    (root/manifest_path).write_text(json.dumps(altered))
                    with self.assertRaisesRegex(ValueError,field):
                        road_center_corrections(root,source['approved_asset_sha256'])
            (root/manifest_path).write_bytes(originals[manifest_path])
            for name,field in (('game/assets/map-navigation.png','baseline_sha256'),
                               ('game/map-source/road-ground.png','ground_sha256'),
                               ('game/assets/map-road-centers.png','output_sha256')):
                with self.subTest(asset=name):
                    (root/name).write_bytes(originals[name]+b'changed')
                    with self.assertRaisesRegex(ValueError,field):
                        road_center_corrections(root,source['approved_asset_sha256'])
                    (root/name).write_bytes(originals[name])
            shared=json.loads(originals['game/config/campaigns/shared.json'])
            shared['catalog']['cities'][0]['position'][0]+=1
            (root/'game/config/campaigns/shared.json').write_text(json.dumps(shared))
            with self.assertRaisesRegex(ValueError,'positions_sha256'):
                road_center_corrections(root,source['approved_asset_sha256'])
            (root/'game/config/campaigns/shared.json').write_bytes(originals['game/config/campaigns/shared.json'])
            pins=dict(source['approved_asset_sha256']);pins['map-road-centers.png']='0'*64
            with self.assertRaisesRegex(ValueError,'approved map pins'):
                road_center_corrections(root,pins)

    def test_water_corrections_are_bound_to_current_sources(self):
        source=json.loads((ROOT/'game/config/map-source.json').read_text())
        water=json.loads((ROOT/'game/map-source/water-render.json').read_text())
        config=json.loads((ROOT/'game/config/water-corrections.json').read_text())
        self.assertEqual(config['wei']['junction'],[639,326])
        self.assertEqual(config['wei']['points'][-1],config['wei']['junction'])
        self.assertEqual(set(water['stats']['clippedMouthPixels']),{'yellow','yangtze','huai','pearl','red'})
        self.assertTrue(all(n>0 for n in water['stats']['clippedMouthPixels'].values()))
        self.assertGreater(water['stats']['seaShadowMaskPixels'],0)
        actual=road_center_corrections(ROOT,source['approved_asset_sha256'])
        self.assertEqual(actual['render']['water_render_sha256'],hashlib.sha256((ROOT/'game/map-source/water-render.json').read_bytes()).hexdigest())
        bridges=presentation()['road_bridges']
        self.assertEqual(bridges['sources']['ground'],water['output'])
        self.assertTrue(bridges['audit']['route_bridges']['bajun:zangke'])
        self.assertTrue(bridges['audit']['route_bridges']['fuling:zangke'])


if __name__=='__main__':unittest.main()
