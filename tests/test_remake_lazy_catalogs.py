"""Archive registration is lightweight; accessing a known archive is exact."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,GameError,canonical
from remake.session import CampaignSession,_CatalogRegistry,_catalog_header_id


class LazyCatalogTests(unittest.TestCase):
    current_path=ROOT/'game/data/main-scenarios-v15/217-07.json'
    archive_path=ROOT/'game/data/main-scenarios-v14/217-07.json'

    def test_default_constructor_preserves_order_default_game_and_preview_contract(self):
        with patch('remake.session.Catalog',wraps=Catalog) as build:
            session=CampaignSession([self.archive_path,self.current_path])
            self.assertEqual(build.call_count,2)
            self.assertEqual(session.game.catalog.data['id'],'mainland217-07-v15')
            first=session._scenario_previews()
            self.assertEqual([row['id'] for row in first],list(session.catalogs))
            self.assertEqual([row['archived'] for row in first],[True,False])
            self.assertEqual([row['capacity'] for row in first],[30,99])
            first[0]['initial_owners'].clear()
            first[1]['faction_resources']['wei']['gold']=-1
            second=session._scenario_previews()
            self.assertTrue(second[0]['initial_owners'])
            self.assertGreaterEqual(second[1]['faction_resources']['wei']['gold'],0)
            self.assertEqual(build.call_count,2)

    def test_registration_previews_and_membership_do_not_construct_archive(self):
        with patch('remake.session.Catalog',wraps=Catalog) as build:
            session=CampaignSession([self.current_path],archived_paths=[self.archive_path])
            self.assertEqual(build.call_count,1)
            self.assertEqual(len(session.catalogs),2)
            self.assertIn('mainland217-07-v14',session.catalogs)
            self.assertEqual(set(session.catalogs.keys()),{'mainland217-07-v14','mainland217-07-v15'})
            self.assertIsNone(session.catalogs.get('../../unregistered.json'))
            view=session.view()
            self.assertEqual([row['id'] for row in view['catalog']['scenarios']],['mainland217-07-v15'])
            self.assertFalse(view['catalog']['scenarios'][0]['archived'])
            self.assertEqual(build.call_count,1)
            preview=session.preview_city('mainland217-07-v14','henan')
            self.assertEqual(preview['capacity'],30)
            self.assertEqual(build.call_count,2)
            archived=session.catalogs['mainland217-07-v14']
            self.assertIs(session.catalogs.get('mainland217-07-v14'),archived)
            self.assertEqual(archived.sha256,hashlib.sha256(self.archive_path.read_bytes()).hexdigest())
            session._scenario_previews()
            self.assertEqual(build.call_count,2)

    def test_legacy_save_roundtrip_preserves_raw_catalog_rng_and_capacity(self):
        old=Campaign(Catalog(self.archive_path))
        old.command('new',dict(faction='wei',seed=93871),0)
        saved=old.export_save()
        with patch('remake.session.Catalog',wraps=Catalog) as build:
            session=CampaignSession([self.current_path],archived_paths=[self.archive_path])
            session.load_save(saved,0)
            self.assertEqual(build.call_count,2)
            self.assertEqual(canonical(session.export_save()),canonical(saved))
            self.assertEqual(session.game.catalog.sha256,old.catalog.sha256)
            self.assertEqual(session.game.catalog.rules.city_officer_capacity,30)
            self.assertEqual(session.game.state.rng.state,old.state.rng.state)
            self.assertEqual(session.game.state.rng.draws,old.state.rng.draws)
            before=canonical(session.export_save())
            bad=dict(saved,scenario=str(self.current_path))
            with self.assertRaises(GameError):session.load_save(bad,session.revision)
            with self.assertRaises(GameError):session.preview_city('../../unregistered.json','henan')
            self.assertEqual(canonical(session.export_save()),before)
            self.assertEqual(build.call_count,2)

    def test_root_header_fast_path_late_id_and_invalid_headers(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'archive.json'
            path.write_text(json.dumps({'id':'first-id','payload':'x'*20000}),encoding='utf8')
            with patch('remake.session.json.load',side_effect=AssertionError('full JSON parse on fast path')):
                self.assertEqual(_catalog_header_id(path),'first-id')
            path.write_text(json.dumps({'payload':{'id':'nested-wrong-id','long':'x'*20000},'id':'late-id'}),encoding='utf8')
            self.assertEqual(_catalog_header_id(path),'late-id')
            for data in ['[]','{}','{"payload":{"id":"nested-id"}}','{"id":null}','{"id":[]}','{"id":"../../arbitrary.json"}','{"id" "bad"}']:
                path.write_text(data,encoding='utf8')
                with self.subTest(data=data),self.assertRaises(ValueError):_catalog_header_id(path)

    def test_lazy_archive_rechecks_actual_root_id_and_never_opens_request_paths(self):
        current=Catalog(self.current_path)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'registered.json'
            path.write_text('{"id":"registered-id","payload":[]}',encoding='utf8')
            registry=_CatalogRegistry([current],[path])
            with patch('remake.session.Catalog',side_effect=AssertionError('unregistered path read')) as build:
                with self.assertRaises(KeyError):registry[str(self.archive_path)]
                self.assertIsNone(registry.get('missing-id'))
                self.assertEqual(build.call_count,0)
            with patch('remake.session.Catalog',return_value=type('Changed',(),{'data':{'id':'different-id'}})()) as build:
                with self.assertRaisesRegex(ValueError,'id changed'):registry['registered-id']
                self.assertNotIn('registered-id',registry._loaded)
                self.assertEqual(build.call_count,1)


if __name__=='__main__':unittest.main()
