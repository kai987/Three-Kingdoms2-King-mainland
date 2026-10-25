"""New local factions keep primary evidence separate from opening estimates."""
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))

from build_campaigns import load_sources
from remake.campaign import Campaign, Catalog, canonical
from remake.map_presentation import city_names
from remake.session import faction_officer_counts, faction_resources


PEOPLE = {
    'historical-song-jian': (1024, '宋建'),
    'historical-lu-xing': (1025, '吕兴'),
    'historical-tang-pu': (1026, '唐谱'),
    'historical-li-tong-jiaozhi': (1027, '李统'),
}


class SongJianLuXingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Canonical sources, rather than release artifacts, are the input.
        _, rows = load_sources(timing=False)
        cls.data = {row['id']: row for row in rows}
        cls.temp = tempfile.TemporaryDirectory(prefix='tk2-local-revolt-')
        cls.catalogs = {}
        for key in ('mainland184-02', 'mainland263-05'):
            path = Path(cls.temp.name) / (key + '.json')
            path.write_text(json.dumps(cls.data[key], ensure_ascii=False))
            cls.catalogs[key] = Catalog(path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def opening(self, key, faction):
        game = Campaign(self.catalogs[key])
        game.command('new', dict(faction=faction, seed=20261025), 0)
        return game

    def test_four_new_identities_do_not_reuse_wei_li_tong_or_other_runtime_ids(self):
        catalog = self.catalogs['mainland263-05']
        self.assertEqual(len(catalog.ids), len(self.data['mainland263-05']['era_assignments']))
        self.assertEqual(len(set(catalog.ids.values())), len(catalog.ids))
        for pid, (ident, name) in PEOPLE.items():
            with self.subTest(person_id=pid):
                self.assertEqual(catalog.ids[pid], ident)
                self.assertEqual(catalog.name(ident), name)
                self.assertEqual(catalog.by_id[ident]['person_id'], pid)
                # Missing SAN14 charisma follows the explicit default60 rule.
                self.assertEqual(catalog.profiles[ident].virtue, 60)
        wei_li_tong = catalog.ids['san14-candidate-0911']
        self.assertEqual(catalog.name(wei_li_tong), '李通')
        self.assertNotEqual(wei_li_tong, catalog.ids['historical-li-tong-jiaozhi'])

    def test_song_jian_is_a_disclosed_early_fuhan_proxy_with_no_invented_retinue(self):
        catalog = self.catalogs['mainland184-02']
        data = catalog.data
        self.assertEqual(data['initial_owners']['longxi'], 'song_jian')
        self.assertEqual(catalog.factions['song_jian']['city'], 'longxi')
        self.assertEqual(city_names(catalog, 184, 2)['longxi'], '枹罕')
        # The same map node does not silently become Fuhan in other campaigns.
        other = type('OtherCatalog', (), {'data': self.data['mainland190-01']})()
        self.assertNotEqual(city_names(other, 190, 1)['longxi'], '枹罕')
        self.assertEqual(faction_officer_counts(catalog)['song_jian'], 1)
        rows = [row['person_id'] for row in data['initial_officers']
                if data['initial_owners'][row['city']] == 'song_jian']
        self.assertEqual(rows, ['historical-song-jian'])
        review = data['era_assignments']['historical-song-jian']['placement_review']
        self.assertEqual(review['historical_certainty'], 'authorial_early_appearance_region_proxy')
        self.assertIsNone(review['reference_date'])
        self.assertIn('184年冬', review['attestation_period'])
        self.assertIn('提前', review['note'])
        self.assertIn('整個隴西郡', review['note'])
        self.assertIn('https://zh.wikisource.org/zh-hant/後漢書/卷72', review['source_urls'])

    def test_lu_xing_owns_responding_regions_without_annexing_hepu_or_wei_reinforcements(self):
        catalog = self.catalogs['mainland263-05']
        data = catalog.data
        self.assertEqual(catalog.factions['lu_xing']['city'], 'jiaozhi')
        self.assertEqual(data['faction_rulers']['lu_xing'], 1025)
        self.assertEqual(faction_officer_counts(catalog)['lu_xing'], 3)
        self.assertEqual(faction_resources(catalog)['lu_xing']['cities'], 3)
        for key in ('jiaozhi', 'jiuzhen', 'rinan'):
            self.assertEqual(data['initial_owners'][key], 'lu_xing')
            self.assertNotIn('neutral_label', data['city_history'][key])
        self.assertEqual(data['initial_owners']['hepu'], 'wu')
        expected = {'historical-lu-xing': 'jiaozhi', 'historical-tang-pu': 'jiaozhi',
                    'historical-li-tong-jiaozhi': 'jiuzhen'}
        actual = {row['person_id']: row['city'] for row in data['initial_officers']
                  if data['initial_owners'][row['city']] == 'lu_xing'}
        self.assertEqual(actual, expected)
        self.assertNotEqual(data['era_assignments']['san14-candidate-0110']['faction'], 'lu_xing')
        revolt = data['era_assignments']['historical-lu-xing']['placement_review']
        self.assertEqual(revolt['reference_date'], [263, 5])
        self.assertEqual(revolt['historical_certainty'], 'primary_text_month_regional_mapping')
        for pid in ('historical-tang-pu', 'historical-li-tong-jiaozhi'):
            review = data['era_assignments'][pid]['placement_review']
            self.assertEqual(review['historical_certainty'], 'authorial_retinue_window')
            self.assertIn('推定', review['note'])
        tang = data['era_assignments']['historical-tang-pu']['placement_review']
        self.assertEqual(tang['reference_date'], [264, 9])
        self.assertIn('不能證明263年五月', tang['note'])
        li = data['era_assignments']['historical-li-tong-jiaozhi']['placement_review']
        self.assertIsNone(li['reference_date'])
        self.assertIn('年代', li['note'])

    def test_explicit_scenario_scope_prevents_unreviewed_future_appearance(self):
        for key, data in self.data.items():
            for pid in PEOPLE:
                with self.subTest(campaign=key, person_id=pid):
                    row = data['era_assignments'][pid]
                    enabled = (key == 'mainland184-02' and pid == 'historical-song-jian') or (
                        key == 'mainland263-05' and pid != 'historical-song-jian')
                    if enabled:
                        self.assertEqual(row['status'], 'serving')
                        self.assertTrue(data['appearance_windows'][pid])
                    else:
                        self.assertEqual(row['status'], 'scenario_excluded')
                        self.assertEqual(row['appearance_plan']['status'], 'excluded')
                        self.assertEqual(data['appearance_windows'][pid], [])
                        self.assertIsNone(row['faction'])
                        self.assertIsNone(row['city'])
        for key in ('mainland184-02', 'mainland263-05'):
            data = self.data[key]
            self.assertEqual(data['placement_completion']['reference_classes'], dict(Counter(
                row['placement_review']['historical_certainty'] for row in data['era_assignments'].values())))
            self.assertEqual(data['placement_completion']['bases'], dict(Counter(
                row['placement_review']['basis'] for row in data['era_assignments'].values())))

    def test_real_start_allocation_and_signed_reload_preserve_identity_rng_and_membership(self):
        for key, faction, ruler, city in (
                ('mainland184-02', 'song_jian', 1024, 'longxi'),
                ('mainland263-05', 'lu_xing', 1025, 'jiaozhi')):
            with self.subTest(campaign=key):
                game = self.opening(key, faction)
                state = game.state
                self.assertEqual(state.extension['leaders'][faction], ruler)
                self.assertEqual(state.officers[ruler].loyalty, 100)
                self.assertIn(ruler, state.cities[city].roster.officer_ids)
                total = state.cities[city].reserves + state.officers[ruler].troops
                target = min(999, total)
                game.command('allocate', dict(city=city, officer=ruler, troops=target), game.revision)
                self.assertEqual(game.state.officers[ruler].troops, target)
                self.assertEqual(game.state.cities[city].reserves, total-target)
                members = {ident: officer.faction_id for ident, officer in game.state.officers.items()}
                game._spawn_eligible(game.state)
                game._reconcile_factions(game.state)
                game.validate(game.state)
                self.assertEqual(members, {ident: officer.faction_id for ident, officer in game.state.officers.items()})
                saved = game.export_save()
                loaded = Campaign(game.catalog)
                loaded.load_save(saved, 0)
                self.assertEqual(canonical(loaded.export_save()), canonical(saved))
                self.assertEqual(loaded.state.rng, game.state.rng)
                self.assertEqual(loaded.state.player, faction)
                for other_city in loaded.state.cities.values():
                    self.assertLessEqual(len(other_city.roster.officer_ids), 99)
                    for ident in other_city.roster.officer_ids:
                        self.assertEqual(loaded.state.officers[ident].faction_id, other_city.owner)

    def test_complete_historical_audit_uses_runtime_identity_not_person_list_position(self):
        # Runtime1005 is deliberately unused. New1024+ identities therefore
        # cannot be resolved with people[runtime_id] or enumerate(people).
        spec = spec_from_file_location('tk2_local_faction_history_audit',
                                       ROOT / 'tools/scenario-history/audit.py')
        audit = module_from_spec(spec)
        spec.loader.exec_module(audit)
        report = audit.compile_report()
        self.assertEqual(len(report['scenarios']), 23)
        rows = {row['id']: row for row in report['scenarios']}
        for key, fid, pid, name in (
                ('mainland184-02', 'song_jian', 'historical-song-jian', '宋建'),
                ('mainland263-05', 'lu_xing', 'historical-lu-xing', '吕兴'),
                ('mainland263-05', 'wu', 'san14-candidate-0548', '孙休')):
            with self.subTest(campaign=key, faction=fid):
                faction = next(row for row in rows[key]['factions'] if row['id'] == fid)
                self.assertEqual((faction['person_id'], faction['ruler']), (pid, name))
                catalog = self.catalogs[key]
                self.assertEqual(catalog.factions[fid]['captain'], name)
                self.assertEqual(catalog.data['faction_rulers'][fid], catalog.ids[pid])


if __name__ == '__main__':
    unittest.main()
