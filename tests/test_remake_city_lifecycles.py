"""Month-accurate city opening without conquest replay or new resources."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest


class CityLifecycleTests(unittest.TestCase):
    def fixture(self,month=10):
        # A controlled fixture moves the existing future node to an imminent
        # month. It tests scheduling, not a new historical claim about新兴.
        data=json.loads((ROOT/'game/data/main-scenarios-v9/207-09.json').read_text())
        data['id']='month-opening-fixture'
        data['city_foundings']['xinxing'].update(year=207,month=month)
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'fixture.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)

    def start(self,catalog,side='wu'):
        game=Campaign(catalog)
        game.command('new',dict(faction=side,seed=2026),0)
        return game

    def test_catalog_and_runtime_views_use_exact_month(self):
        catalog=self.fixture(11)
        self.assertNotIn('xinxing',catalog.active_city_ids(207))
        self.assertNotIn('xinxing',catalog.active_city_ids(207,10))
        self.assertIn('xinxing',catalog.active_city_ids(207,11))
        game=self.start(catalog)
        self.assertNotIn('xinxing',game.view()['catalog']['active_cities'])
        game._complete_month(game.state);game.validate(game.state)
        self.assertEqual((game.state.year,game.state.month),(207,10))
        self.assertNotIn('xinxing',game.state.cities)
        self.assertNotIn('xinxing',game.view()['catalog']['active_cities'])
        game._complete_month(game.state);game.validate(game.state)
        self.assertIn('xinxing',game.state.cities)
        self.assertIn('xinxing',game.view()['catalog']['active_cities'])

    def test_opening_inherits_actual_parent_owner_and_only_splits_resources(self):
        game=self.start(self.fixture())
        parent=game.state.cities['taiyuan']
        for ident in list(parent.roster.officer_ids):
            recipient=next(c for c in game.state.cities.values() if c.owner==parent.owner
                           and c.id!=parent.id and len(c.roster.officer_ids)<30)
            parent.roster.officer_ids.remove(ident);recipient.roster.officer_ids.append(ident)
        parent.owner='wu'
        game.validate(game.state)
        parent_before={key:getattr(parent,key) for key in ('gold','grain','reserves')}
        troops_before=sum(o.troops for o in game.state.officers.values())
        rng_before=deepcopy(game.state.rng)
        game._complete_month(game.state);game.validate(game.state)
        child=game.state.cities['xinxing']
        self.assertEqual(child.owner,'wu')
        self.assertEqual(child.roster.officer_ids,[])
        self.assertEqual(game.state.rng,rng_before)
        self.assertEqual(sum(o.troops for o in game.state.officers.values()),troops_before)
        for field in ('gold','grain','reserves'):
            parent_income=game.catalog.data['city_income']['taiyuan'][field]
            child_income=game.catalog.data['city_income']['xinxing'][field]
            self.assertEqual(getattr(parent,field)+getattr(child,field),
                             parent_before[field]+parent_income+child_income)
        snapshot=game.to_dict()
        game._open_dated_cities(game.state)
        self.assertEqual(game.to_dict(),snapshot)
        event=next(text for text in game.state.log if '新兴建置' in text)
        self.assertIn('太原当时归属',event)

    def test_pre_and_post_month_saves_reject_wrong_city_domain(self):
        catalog=self.fixture()
        game=self.start(catalog)
        before=game.export_save();loaded=Campaign(catalog)
        loaded.load_save(before,0);self.assertEqual(loaded.to_dict(),game.to_dict())
        bad=deepcopy(before)
        bad['state']['cities']['xinxing']=deepcopy(bad['state']['cities']['taiyuan'])
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises(ValueError):loaded.load_save(bad,loaded.revision)
        self.assertEqual(loaded.to_dict(),game.to_dict())
        game._complete_month(game.state);game.validate(game.state)
        after=game.export_save();loaded.load_save(after,loaded.revision)
        self.assertEqual(loaded.to_dict(),game.to_dict())
        bad=deepcopy(after);del bad['state']['cities']['xinxing']
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises(ValueError):loaded.load_save(bad,loaded.revision)
        self.assertEqual(loaded.to_dict(),game.to_dict())

    def test_legacy_year_only_dates_still_open_in_january(self):
        catalog=Catalog(ROOT/'game/data/main-scenarios-v8/200-01.json')
        self.assertNotIn('xinxing',catalog.active_city_ids(214,12))
        self.assertIn('xinxing',catalog.active_city_ids(215))
        self.assertIn('xinxing',catalog.active_city_ids(215,1))
        game=self.start(catalog)
        # Calendar-only progression intentionally excludes conquest AI.
        while (game.state.year,game.state.month)<(215,1):game._complete_month(game.state)
        game._spawn_eligible(game.state);game._reconcile_factions(game.state)
        game.validate(game.state)
        self.assertIn('xinxing',game.state.cities)
        self.assertTrue(any('承接晋阳当时归属' in text for text in game.state.log))


if __name__=='__main__':unittest.main()
