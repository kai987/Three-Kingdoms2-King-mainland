"""Dated local factions keep primary evidence separate from opening estimates."""
from collections import Counter
from copy import deepcopy
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
    'historical-beigong-boyu': (1028, '北宫伯玉'),
    'historical-li-wenhou': (1029, '李文侯'),
    'historical-bian-zhang': (1030, '边章'),
}
SONG_OPENINGS = {
    'mainland188-06', 'mainland190-01', 'mainland191-10', 'mainland194-06',
    'mainland196-06', 'mainland197-07', 'mainland198-03', 'mainland200-01',
    'mainland201-05', 'mainland202-06', 'mainland207-09', 'mainland208-10',
    'mainland209-06', 'mainland210-11', 'mainland211-07-tongguan',
    'mainland212-06', 'mainland212-12',
}
SONG_IF_OPENINGS = {'mainland197-07', 'mainland201-05', 'mainland209-06',
                    'mainland210-11', 'mainland212-06'}
# These released garrisons move without inheriting the replacement city owner.
# Keep explicit IDs: names are not unique person identities.
RELOCATED = {
    'mainland190-01': ('san14-candidate-0693', 'san14-candidate-0804'),
    'mainland191-10': ('san14-candidate-0693', 'san14-candidate-0804', 'san14-candidate-0969'),
    'mainland194-06': ('san14-candidate-0760', 'san14-candidate-0804', 'san14-candidate-0867'),
    'mainland196-06': ('san14-candidate-0760', 'san14-candidate-0804', 'san14-candidate-0867'),
    'mainland197-07': ('san14-candidate-0166', 'san14-candidate-0475', 'san14-candidate-0760',
                       'san14-candidate-0804', 'san14-candidate-0867'),
    'mainland198-03': ('san14-candidate-0757', 'san14-candidate-0766', 'san14-candidate-0804',
                       'san14-candidate-0867'),
    'mainland200-01': ('san14-candidate-0757', 'san14-candidate-0766', 'san14-candidate-0804',
                       'san14-candidate-0867'),
    'mainland201-05': ('san14-candidate-0474', 'san14-candidate-0760', 'san14-candidate-0864'),
    'mainland202-06': ('san14-candidate-0757', 'san14-candidate-0766', 'san14-candidate-0804',
                       'san14-candidate-0867'),
    'mainland207-09': ('san14-candidate-0757', 'san14-candidate-0766', 'san14-candidate-0804',
                       'san14-candidate-0867'),
    'mainland208-10': ('san14-candidate-0757', 'san14-candidate-0766', 'san14-candidate-0804',
                       'san14-candidate-0867'),
    'mainland209-06': ('san14-candidate-0166', 'san14-candidate-0475', 'san14-candidate-0757',
                       'san14-candidate-0766', 'san14-candidate-0804', 'san14-candidate-0867'),
    'mainland210-11': ('san14-candidate-0030', 'san14-candidate-0474', 'san14-candidate-0693',
                       'san14-candidate-0760', 'san14-candidate-0770', 'san14-candidate-0864',
                       'san14-candidate-0969'),
    'mainland211-07-tongguan': ('san14-candidate-0474', 'san14-candidate-0757',
                                'san14-candidate-0864'),
    'mainland212-06': ('san14-candidate-0475',),
    'mainland212-12': ('san14-candidate-0429',),
}


class SongJianLuXingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Canonical sources, rather than release artifacts, are the input.
        _, rows = load_sources(timing=False)
        cls.data = {row['id']: row for row in rows}
        cls.temp = tempfile.TemporaryDirectory(prefix='tk2-local-revolt-')
        cls.catalogs = {}
        for key in SONG_OPENINGS | {'mainland184-02', 'mainland263-05'}:
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

    def test_seven_new_identities_keep_1024_to_1030_without_reusing_wei_li_tong(self):
        catalog = self.catalogs['mainland263-05']
        self.assertEqual(len(catalog.ids), 1030)
        self.assertEqual(len(catalog.ids), len(self.data['mainland263-05']['era_assignments']))
        self.assertEqual(len(set(catalog.ids.values())), len(catalog.ids))
        self.assertNotIn(1005, catalog.by_id)
        for pid, (ident, name) in PEOPLE.items():
            with self.subTest(person_id=pid):
                self.assertEqual(catalog.ids[pid], ident)
                self.assertEqual(catalog.name(ident), name)
                self.assertEqual(catalog.by_id[ident]['person_id'], pid)
                self.assertEqual(catalog.profiles[ident].virtue, 60)
        wei_li_tong = catalog.ids['san14-candidate-0911']
        self.assertEqual(catalog.name(wei_li_tong), '李通')
        self.assertNotEqual(wei_li_tong, catalog.ids['historical-li-tong-jiaozhi'])

    def test_184_local_people_are_free_before_two_separate_conditional_winter_foundings(self):
        catalog = self.catalogs['mainland184-02']
        data = catalog.data
        free = {row['person_id']: row['city'] for row in data['initial_free_officers']}
        initial = {row['person_id'] for row in data['initial_officers']}
        expected = {'historical-song-jian': 'longxi', 'historical-beigong-boyu': 'jincheng',
                    'historical-li-wenhou': 'jincheng', 'historical-bian-zhang': 'jincheng',
                    'san14-candidate-0166': 'jincheng'}
        for pid, city in expected.items():
            with self.subTest(person_id=pid):
                self.assertEqual(free[pid], city)
                self.assertNotIn(pid, initial)
                plan = data['era_assignments'][pid]
                self.assertEqual((plan['status'], plan['faction'], plan['city']), ('free', None, city))
                self.assertEqual(plan['appearance_plan']['status'], 'free')
                self.assertEqual(data['initial_owners'][city], 'neutral')
        for fid in ('song_jian', 'bian_zhang'):
            self.assertEqual(catalog.factions[fid]['available_from'], [184, 11])
            self.assertEqual(faction_officer_counts(catalog)[fid], 0)
            self.assertEqual(faction_resources(catalog)[fid]['cities'], 0)
        events = {row['faction']: row for row in data['faction_foundings']}
        self.assertEqual(events['song_jian']['members'], ['historical-song-jian'])
        self.assertEqual(events['bian_zhang']['members'],
                         ['historical-bian-zhang', 'historical-beigong-boyu',
                          'historical-li-wenhou', 'san14-candidate-0166'])
        self.assertEqual(events['bian_zhang']['cities'], ['jincheng', 'tianshui'])
        self.assertEqual(events['song_jian']['cities'], ['longxi'])
        self.assertEqual(data['faction_rulers']['bian_zhang'], 1030)
        self.assertNotIn('beigong_boyu', catalog.factions)
        for event in events.values():
            self.assertEqual(event['date'], [184, 11])
            self.assertEqual(event['required_owner'], 'neutral')
            self.assertIs(event['require_unaligned'], True)
        song = data['era_assignments']['historical-song-jian']['placement_review']
        self.assertIn('不預設獨立政權', song['note'])
        self.assertIn('已登用或城池已被占領', song['note'])
        self.assertIn('https://zh.wikisource.org/zh-hant/後漢書/卷72', song['source_urls'])
        coup, = data['faction_coups']
        self.assertEqual((coup['faction'], coup['date'], coup['successor']),
                         ('bian_zhang', [186, 12], 'san14-candidate-0166'))
        self.assertEqual(coup['victims'], ['historical-bian-zhang', 'historical-beigong-boyu',
                                         'historical-li-wenhou'])
        self.assertTrue(all(pid not in data['historical_exit_dates'] for pid in coup['victims']))

    def test_184_dong_zhuo_relocation_and_han_sui_disarming_preserve_all_soldiers(self):
        game = self.opening('mainland184-02', 'dong_zhuo')
        state = game.state
        self.assertEqual(game.catalog.factions['dong_zhuo']['city'], 'anding')
        self.assertEqual(state.cities['anding'].owner, 'dong_zhuo')
        self.assertEqual(state.cities['tianshui'].owner, 'neutral')
        self.assertEqual(state.cities['tianshui'].roster.officer_ids, [])
        self.assertEqual(len(state.cities['anding'].roster.officer_ids), 14)
        for ident in state.cities['anding'].roster.officer_ids:
            self.assertEqual(state.officers[ident].faction_id, 'dong_zhuo')
            self.assertEqual(state.officers[ident].troops, 300)
            plan = game.catalog.data['era_assignments'][state.officers[ident].person_id]
            self.assertEqual((plan['faction'], plan['city']), ('dong_zhuo', 'anding'))
        self.assertEqual(state.cities['wuwei'].reserves, 1560)
        self.assertIsNone(state.officers[165].faction_id)
        self.assertEqual(state.officers[165].troops, 0)
        self.assertEqual(state.extension['free_locations']['165'], 'jincheng')
        self.assertEqual(state.soldiers['initial'], 194760)
        self.assertEqual(sum(c.reserves for c in state.cities.values())
                         + sum(o.troops for o in state.officers.values()), 194760)
        self.assertEqual(len(game.catalog.data['initial_officers']), 136)
        self.assertEqual(len(game.catalog.data['initial_free_officers']), 155)
        game.validate(state)

    def test_seventeen_lifetime_openings_include_five_if_and_keep_longxi_name(self):
        self.assertEqual(len(SONG_OPENINGS), 17)
        actual = {key for key, data in self.data.items()
                  if any(row['person_id'] == 'historical-song-jian'
                         for row in data['initial_officers'])}
        self.assertEqual(actual, SONG_OPENINGS)
        fictional = {key for key in actual if self.data[key]['main_scenario'].get('fictional')
                     or self.data[key]['main_scenario'].get('group') == 'if'}
        self.assertEqual(fictional, SONG_IF_OPENINGS)
        for key, catalog in self.catalogs.items():
            self.assertEqual(city_names(catalog, catalog.data['start_year'],
                                        catalog.data['start_month'])['longxi'], '陇西')
        for key in sorted(SONG_OPENINGS):
            with self.subTest(campaign=key):
                catalog = self.catalogs[key]
                self.assertEqual(catalog.data['initial_owners']['longxi'], 'song_jian')
                self.assertEqual(catalog.factions['song_jian']['city'], 'longxi')
                self.assertEqual(catalog.data['faction_rulers']['song_jian'], 1024)
                self.assertEqual(faction_officer_counts(catalog)['song_jian'], 1)
                self.assertEqual(faction_resources(catalog)['song_jian']['cities'], 1)
                plan = catalog.data['era_assignments']['historical-song-jian']
                self.assertEqual(plan['appearance_plan']['end'], [214, 9])
                self.assertEqual(plan['placement_review']['historical_death_date'], [214, 10])
                game = self.opening(key, 'song_jian')
                self.assertEqual(game.state.extension['leaders']['song_jian'], 1024)
                self.assertEqual(game.state.cities['longxi'].roster.officer_ids, [1024])
                self.assertEqual(game.state.officers[1024].faction_id, 'song_jian')
                self.assertEqual(game.state.officers[1024].loyalty, 100)
                game.validate(game.state)

    def test_57_relocated_garrisons_keep_their_factions_and_212_free_people_stay_unaligned(self):
        self.assertEqual(sum(map(len, RELOCATED.values())), 57)
        for key, people in RELOCATED.items():
            data = self.data[key]
            initial = {row['person_id']: row for row in data['initial_officers']}
            owner = 'wei' if key == 'mainland212-12' else 'ma_teng'
            for pid in people:
                with self.subTest(campaign=key, person_id=pid):
                    plan = data['era_assignments'][pid]
                    self.assertEqual((plan['faction'], plan['city']), (owner, 'tianshui'))
                    self.assertEqual(initial[pid]['city'], 'tianshui')
                    self.assertEqual(plan['posting_reference']['city'], 'tianshui')
                    self.assertEqual(plan['appearance_plan']['city'], 'tianshui')
                    self.assertEqual(data['appearance_locations'][pid], 'tianshui')
                    self.assertTrue(all(w['city'] != 'longxi'
                                        for w in data['appearance_windows'].get(pid, [])))
                    self.assertEqual(plan['placement_review']['historical_certainty'],
                                     'authorial_garrison_relocation')
            self.assertLessEqual(Counter(row['city'] for row in data['initial_officers'])['tianshui'], 13)
        game = self.opening('mainland212-12', 'song_jian')
        free = [row['person_id'] for row in game.catalog.data['initial_free_officers']
                if row['city'] == 'longxi']
        self.assertEqual(len(free), 9)
        for pid in free:
            ident = game.catalog.ids[pid]
            self.assertIsNone(game.state.officers[ident].faction_id)
            self.assertEqual(game.state.extension['free_locations'][str(ident)], 'longxi')

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
        self.assertEqual(data['era_assignments']['historical-tang-pu']['placement_review']['reference_date'],
                         [264, 9])
        self.assertIsNone(data['era_assignments']['historical-li-tong-jiaozhi']['placement_review']['reference_date'])

    def test_explicit_scenario_scope_prevents_unreviewed_future_appearance(self):
        for key, data in self.data.items():
            for pid in PEOPLE:
                with self.subTest(campaign=key, person_id=pid):
                    row = data['era_assignments'][pid]
                    free = key == 'mainland184-02' and pid in {
                        'historical-song-jian', 'historical-beigong-boyu', 'historical-li-wenhou',
                        'historical-bian-zhang'}
                    serving = (pid == 'historical-song-jian' and key in SONG_OPENINGS) or (
                        key == 'mainland263-05' and pid in {
                            'historical-lu-xing', 'historical-tang-pu', 'historical-li-tong-jiaozhi'})
                    if free or serving:
                        self.assertEqual(row['status'], 'free' if free else 'serving')
                        self.assertTrue(data['appearance_windows'][pid])
                    else:
                        self.assertEqual(row['status'], 'scenario_excluded')
                        self.assertEqual(row['appearance_plan']['status'], 'excluded')
                        self.assertEqual(data['appearance_windows'][pid], [])
                        self.assertIsNone(row['faction'])
                        self.assertIsNone(row['city'])
            self.assertEqual(data['placement_completion']['reference_classes'], dict(Counter(
                row['placement_review']['historical_certainty'] for row in data['era_assignments'].values())))
            self.assertEqual(data['placement_completion']['bases'], dict(Counter(
                row['placement_review']['basis'] for row in data['era_assignments'].values())))

    def test_real_start_allocation_and_signed_reload_preserve_identity_rng_and_membership(self):
        for key, faction, ruler, city in (
                ('mainland188-06', 'song_jian', 1024, 'longxi'),
                ('mainland212-12', 'song_jian', 1024, 'longxi'),
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

    def test_complete_historical_audit_uses_runtime_identity_and_separates_future_factions(self):
        spec = spec_from_file_location('tk2_local_faction_history_audit',
                                       ROOT / 'tools/scenario-history/audit.py')
        audit = module_from_spec(spec)
        spec.loader.exec_module(audit)
        report = audit.compile_report()
        self.assertEqual(len(report['scenarios']), 23)
        rows = {row['id']: row for row in report['scenarios']}
        for key, fid, pid, name in (
                ('mainland190-01', 'song_jian', 'historical-song-jian', '宋建'),
                ('mainland263-05', 'lu_xing', 'historical-lu-xing', '吕兴'),
                ('mainland263-05', 'wu', 'san14-candidate-0548', '孙休')):
            with self.subTest(campaign=key, faction=fid):
                faction = next(row for row in rows[key]['factions'] if row['id'] == fid)
                self.assertEqual((faction['person_id'], faction['ruler']), (pid, name))
                catalog = self.catalogs[key]
                self.assertEqual(catalog.factions[fid]['captain'], name)
                self.assertEqual(catalog.data['faction_rulers'][fid], catalog.ids[pid])
        opening_factions = {row['id'] for row in rows['mainland184-02']['factions']}
        self.assertNotIn('song_jian', opening_factions)
        self.assertNotIn('bian_zhang', opening_factions)
        self.assertEqual(len(opening_factions), 9)
        self.assertEqual({row['id'] for row in rows['mainland184-02']['future_factions']},
                         {'song_jian', 'bian_zhang'})
        self.assertEqual(len(rows['mainland184-02']['scheduled_faction_foundings']), 2)
        self.assertEqual(len(rows['mainland184-02']['scheduled_faction_coups']), 1)
        self.assertEqual(rows['mainland184-02']['initial_soldier_total'], 194760)
        adaptations = report['fictional_adaptations']
        self.assertEqual({row['id'] for row in adaptations}, SONG_IF_OPENINGS)
        self.assertTrue(all(row['fictional'] for row in adaptations))
        self.assertTrue(SONG_IF_OPENINGS <= set(report['fictional_excluded']))
        self.assertEqual(report['fictional_adaptation_summary']['new_factions'], 5)

    def test_audit_rejects_premature_ownership_recruitment_or_changed_founding_month(self):
        spec = spec_from_file_location('tk2_local_faction_audit_negative',
                                       ROOT / 'tools/scenario-history/audit.py')
        audit = module_from_spec(spec)
        spec.loader.exec_module(audit)
        data = self.data['mainland184-02']
        decision = next(row for row in json.loads(
            (ROOT / 'game/config/references/scenario-history-review.json').read_text())['scenarios']
                        if row['id'] == 'mainland184-02')
        defined = {row['id']: row for row in data['factions']}
        visible = {fid: row for fid, row in defined.items() if fid not in {'song_jian', 'bian_zhang'}}
        people, opening = audit.opening_people(data, set(data['active_cities']), visible)
        self.assertEqual(len(audit.review_foundings(data, decision, people, opening, defined, visible)), 2)
        for change in ('month', 'owner', 'secondary_city', 'recruited', 'visible', 'plan'):
            with self.subTest(change=change):
                changed_data, changed_decision = deepcopy(data), deepcopy(decision)
                changed_opening, changed_visible = deepcopy(opening), deepcopy(visible)
                if change == 'month':
                    changed_decision['scheduled_faction_foundings'][0]['date'] = [184, 10]
                elif change == 'owner':
                    changed_data['initial_owners']['longxi'] = 'han'
                elif change == 'secondary_city':
                    changed_data['initial_owners']['tianshui'] = 'han'
                elif change == 'recruited':
                    changed_opening['historical-song-jian']['faction'] = 'han'
                elif change == 'visible':
                    changed_visible['song_jian'] = defined['song_jian']
                else:
                    changed_data['era_assignments']['historical-song-jian']['status'] = 'serving'
                with self.assertRaises(ValueError):
                    audit.review_foundings(changed_data, changed_decision, people, changed_opening,
                                           defined, changed_visible)

    def test_audit_rejects_unconditional_coup_deaths_or_a_different_successor(self):
        spec = spec_from_file_location('tk2_local_coup_audit_negative',
                                       ROOT / 'tools/scenario-history/audit.py')
        audit = module_from_spec(spec)
        spec.loader.exec_module(audit)
        data = self.data['mainland184-02']
        decision = next(row for row in json.loads(
            (ROOT / 'game/config/references/scenario-history-review.json').read_text())['scenarios']
                        if row['id'] == 'mainland184-02')
        people = {row['person_id']: row for row in data['people']}
        defined = {row['id']: row for row in data['factions']}
        self.assertEqual(len(audit.review_coups(data, decision, people, defined)), 1)
        for change in ('exit', 'successor', 'conditional'):
            with self.subTest(change=change):
                changed_data, changed_decision = deepcopy(data), deepcopy(decision)
                if change == 'exit':
                    changed_data['historical_exit_dates']['historical-beigong-boyu'] = [186, 12]
                elif change == 'successor':
                    changed_decision['scheduled_faction_coups'][0]['successor'] = 'historical-song-jian'
                else:
                    changed_decision['scheduled_faction_coups'][0]['conditional_not_unconditional_death'] = False
                with self.assertRaises(ValueError):
                    audit.review_coups(changed_data, changed_decision, people, defined)


if __name__ == '__main__':
    unittest.main()
