"""Current opening caches preserve saves, RNG and independent response containers."""
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
    paths=[ROOT/'game/data/campaigns'/f'{date}.json' for date in ('184-02','190-01','263-05','217-07')]

    def test_repeated_current_views_and_save_roundtrip_keep_exact_state(self):
        session=CampaignSession(self.paths)
        baseline=digest(session.view())
        self.assertEqual(digest(session.view()),baseline)
        self.assertIsNone(session.to_dict())
        for scenario,side in [('mainland184-02','yellow_turban'),('mainland217-07','shu'),('mainland263-05','wei')]:
            with self.subTest(scenario=scenario):
                session.command('new',dict(scenario=scenario,faction=side,seed=2026),session.revision)
                saved=session.export_save();state=deepcopy(session.to_dict());revision=session.revision
                rng=deepcopy(session.game.state.rng);baseline=digest(session.view())
                self.assertEqual(digest(session.view()),baseline)
                self.assertEqual(session.revision,revision);self.assertEqual(session.to_dict(),state)
                self.assertEqual(session.game.state.rng,rng)
                session.load_save(saved,revision)
                self.assertEqual(session.export_save(),saved);self.assertEqual(session.to_dict(),state)
                self.assertEqual(session.game.state.rng,rng)
                self.assertEqual(session.game.catalog.data['schema'],'tk2-campaign-v1')
                self.assertNotIn('content_generation',session.game.catalog.data)
                self.assertTrue(all('archived' not in row for row in session.view()['catalog']['scenarios']))

    def test_fresh_preview_containers_cannot_corrupt_cached_openings(self):
        session=CampaignSession(self.paths)
        expected=deepcopy(session.view()['catalog']['scenarios'])
        catalog_hashes={key:digest(c.data) for key,c in session.catalogs.items()}
        previews=session.view()['catalog']['scenarios'];row=previews[0];side=next(iter(row['faction_resources']))
        row['id']='corrupt';row['initial_owners']['nanyang']='corrupt'
        row['active_cities'].clear();row['city_names'].clear()
        row['map_cities'].clear();row['factions'].clear()
        row['faction_resources'][side]['gold']=-1
        row['faction_officers'][side]=-1;row['faction_colors'][side]='#000000'
        previews.pop()
        self.assertEqual(session.view()['catalog']['scenarios'],expected)
        self.assertEqual({key:digest(c.data) for key,c in session.catalogs.items()},catalog_hashes)
        self.assertEqual(session.revision,0);self.assertIsNone(session.to_dict())

    def test_cached_openings_do_not_rescan_other_scenarios(self):
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
            for scenario,side in [('mainland184-02','yellow_turban'),('mainland217-07','shu')]:
                session.command('new',dict(scenario=scenario,faction=side,seed=2026),session.revision)
                saved=session.export_save()
                self.assertEqual(session.view()['catalog']['scenarios'],openings)
                session.load_save(saved,session.revision)
                self.assertEqual(session.view()['catalog']['scenarios'],openings)
                self.assertEqual(session.export_save(),saved)


if __name__=='__main__':unittest.main()
