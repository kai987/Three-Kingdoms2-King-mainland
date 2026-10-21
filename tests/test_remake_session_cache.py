"""Opening metadata caching must preserve API, save and independent view data."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import digest
from remake.session import CampaignSession
import remake.session as session_module


class SessionPreviewCacheTests(unittest.TestCase):
    paths=[ROOT/'game/data/demo.json',ROOT/'game/data/main-scenarios-v5/184-02.json',
           ROOT/'game/data/main-scenarios-v13/217-07.json',ROOT/'game/data/main-scenarios-v13/263-05.json']

    def test_exact_preoptimization_view_and_save_contracts(self):
        # Canonical hashes captured from the uncached 9bf4aea implementation,
        # same four catalogs, seed2026 and command order. Include full current
        # library, seasonal route quotes and all opening previews in the view.
        cases=[(None,None,'c73335ef8d909ec50e11d7bbf7cd5f84ed940f5b74206139c9ae0784be5ca072',None),
            ('mainland184-02-v5','yellow_turban','2ea238f8c1de3c7ef65ca3ec93c5632997935d26cb6edd2d9b657aa864912f55','f4120e7a7d4e778139ed82c91650e1e36dc06bb7410c4264f84e5583e927e7e8'),
            ('mainland217-07-v13','shu','2d341c2a7f3c819685eece6a39956dd6b5988fa5a1d28fc51fc604125284af22','7ad7c1a6d02ad67be193340b9303cf1d0238a1290210ccbaa62b238c7859cd0a'),
            ('mainland263-05-v13','wei','89f7cd5f6a049f0ddf1729e4cecb99d1424831cf98c76e82c599148d4b5091eb','f9bf708b4927be8a308b62be212cb59e19a81662349d0e26f0e2d84af39f2e03')]
        session=CampaignSession(self.paths)
        for scenario,side,view_hash,save_hash in cases:
            with self.subTest(scenario=scenario):
                if scenario:
                    session.command('new',dict(scenario=scenario,faction=side,seed=2026),session.revision)
                revision=session.revision
                for _ in range(2):self.assertEqual(digest(session.view()),view_hash)
                self.assertEqual(session.revision,revision)
                if scenario:self.assertEqual(digest(session.export_save()),save_hash)

    def test_fresh_preview_containers_cannot_corrupt_cached_openings(self):
        session=CampaignSession(self.paths)
        expected=deepcopy(session.view()['catalog']['scenarios'])
        catalog_hashes={key:digest(c.data) for key,c in session.catalogs.items()}
        previews=session.view()['catalog']['scenarios'];row=previews[0]
        row['id']='corrupt';row['initial_owners']['nanyang']='corrupt'
        row['active_cities'].clear();row['city_names'].clear()
        row['map_cities'].clear();row['factions'].clear()
        row['faction_resources']['wei']['gold']=-1
        row['faction_officers']['wei']=-1;row['faction_colors']['wei']='#000000'
        previews.pop()
        self.assertEqual(session.view()['catalog']['scenarios'],expected)
        self.assertEqual({key:digest(c.data) for key,c in session.catalogs.items()},catalog_hashes)
        self.assertEqual(session.revision,0);self.assertIsNone(session.to_dict())

    def test_cached_openings_do_not_rescan_archived_catalogs(self):
        session=CampaignSession(self.paths)
        openings=deepcopy(session.view()['catalog']['scenarios'])
        def current_only(function):
            def checked(catalog,*args):
                self.assertIs(catalog,session.game.catalog,'unchanged opening metadata was rescanned')
                return function(catalog,*args)
            return checked
        with patch.object(session_module,'city_names',side_effect=current_only(session_module.city_names)), \
             patch.object(session_module,'faction_resources',side_effect=current_only(session_module.faction_resources)), \
             patch.object(session_module,'faction_officer_counts',side_effect=current_only(session_module.faction_officer_counts)), \
             patch.object(session_module,'faction_colors',side_effect=current_only(session_module.faction_colors)):
            for scenario,side in [('mainland184-02-v5','yellow_turban'),('mainland217-07-v13','shu')]:
                session.command('new',dict(scenario=scenario,faction=side,seed=2026),session.revision)
                saved=session.export_save()
                self.assertEqual(session.view()['catalog']['scenarios'],openings)
                session.load_save(saved,session.revision)
                self.assertEqual(session.view()['catalog']['scenarios'],openings)
                self.assertEqual(session.export_save(),saved)


if __name__=='__main__':unittest.main()
