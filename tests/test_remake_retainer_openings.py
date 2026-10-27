"""Source-reviewed retainers must reach real campaign rosters and current saves.

The tables pin the approved historical/IF choices independently of the source
merger. Dates and regional proxies are game mappings, not complete monthly
garrison records. The released 1,030 identities remain a frozen prefix.
"""
from hashlib import sha256
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
from remake.session import CampaignSession, faction_officer_counts


NEW_IDS = (
    'historical-zhao-chong', 'historical-sun-kang', 'historical-xu-xi',
    'historical-mao-hui', 'historical-liu-yi-yuzhang',
    'historical-yang-yi-liaodong', 'historical-su-shu-liaodong',
    'historical-sun-zong-liaodong', 'historical-liu-yuan-liaodong',
    'historical-gongsun-heng', 'historical-wang-zan-xuantu',
    'historical-guo-xin-liaodong', 'historical-liu-fu-liaodong',
    'historical-wang-jian-liaodong', 'historical-wei-yan-liaodong',
    'historical-bi-sheng', 'historical-gongsun-xiu',
    'historical-qu-jing-cangwu', 'historical-heng-yi-cangwu',
    'historical-qian-bo-cangwu', 'historical-gongchou-cheng',
    'historical-sun-xiang',
)
GONGSUN_233 = NEW_IDS[6:11]
GONGSUN_238 = NEW_IDS[11:17]
WU_JU_STAFF = NEW_IDS[17:20]


class RetainerOpeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, sources = load_sources(timing=False)
        cls.sources = {row['id'].removeprefix('mainland'): row for row in sources}
        cls.temp = tempfile.TemporaryDirectory(prefix='tk2-retainer-openings-')
        cls.paths, cls.catalogs = {}, {}
        for chapter, data in cls.sources.items():
            path = Path(cls.temp.name) / (chapter + '.json')
            path.write_text(json.dumps(data, ensure_ascii=False))
            cls.paths[chapter], cls.catalogs[chapter] = path, Catalog(path)
        cls.pool = json.loads((ROOT / 'game/config/campaigns/people.json').read_text())
        cls.people = cls.pool['people']
        cls.review = json.loads((ROOT / 'game/config/references/retainer-affiliation-review.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def game(self, chapter, faction=None):
        catalog = self.catalogs[chapter]
        game = Campaign(catalog)
        game.command('new', dict(faction=faction or next(iter(catalog.factions)), seed=20261027), 0)
        return game

    def assert_posting(self, chapter, pid, faction, city, *, ruler=False):
        game, catalog = self.game(chapter), self.catalogs[chapter]
        ident = catalog.ids[pid]
        officer = game.state.officers[ident]
        self.assertTrue(officer.alive)
        self.assertEqual(officer.faction_id, faction)
        memberships = [key for key, value in game.state.cities.items()
                       if ident in value.roster.officer_ids]
        if faction is None:
            self.assertEqual(memberships, [])
            self.assertEqual(game.state.extension['free_locations'][str(ident)], city)
        else:
            self.assertEqual(memberships, [city])
            self.assertEqual(game.state.cities[city].owner, faction)
            self.assertEqual(game.state.extension['leaders'][faction] == ident, ruler)
        self.assertEqual(self.sources[chapter]['era_assignments'][pid]['faction'], faction)
        self.assertEqual(self.sources[chapter]['era_assignments'][pid]['city'], city)
        return game

    def test_append_only_ids_preserve_every_released_person_and_all29_plans(self):
        self.assertEqual(len(self.sources), 29)
        self.assertEqual(len(self.people), 1052)
        self.assertEqual(tuple(self.pool['order'][1030:]), NEW_IDS)
        self.assertEqual([self.people[pid]['runtime_id'] for pid in NEW_IDS], list(range(1031, 1053)))
        before = self.pool['order'][:1030]
        frozen = dict(order=before, people={pid: self.people[pid] for pid in before})
        digest = sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=False,
                                  separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(digest, self.review['base_people_snapshot_sha256'])
        self.assertEqual(self.people['historical-bian-zhang']['runtime_id'], 1030)
        self.assertNotIn(1005, {p['runtime_id'] for p in self.people.values()})
        for chapter, catalog in self.catalogs.items():
            with self.subTest(chapter=chapter):
                self.assertEqual(tuple(catalog.ids), tuple(self.pool['order']))
                self.assertEqual(set(catalog.data['era_assignments']), set(self.people))
                self.assertEqual(set(catalog.data['appearance_windows']), set(self.people))
                self.assertEqual(catalog.rules.city_officer_capacity, 99)
                self.assertEqual(catalog.rules.battle_officers_per_side, 10)

    def test_190_and191_independent_lords_receive_their_named_retainers(self):
        for chapter in ('190-01', '191-10'):
            for pid, faction, city in (
                ('san14-candidate-0016', 'bao_xin', 'dongping'),
                ('san14-candidate-0709', 'zhang_miao', 'chenliu'),
                ('historical-zhao-chong', 'zhang_miao', 'chenliu'),
            ):
                with self.subTest(chapter=chapter, person=pid):
                    self.assert_posting(chapter, pid, faction, city)
        self.assert_posting('190-01', 'san14-candidate-0159', 'wang_kuang', 'henei')

    def test_hua_xin_and_zang_ba_are_independent_not_borrowed_sun_or_lu_armies(self):
        for chapter in ('196-06', '197-07', '198-03'):
            self.assert_posting(chapter, 'historical-liu-yi-yuzhang', 'hua_xin', 'yuzhang')
            self.assertEqual(faction_officer_counts(self.catalogs[chapter])['hua_xin'], 2)
        for chapter in ('197-07', '198-03'):
            for pid in NEW_IDS[1:4]:
                with self.subTest(chapter=chapter, person=pid):
                    self.assert_posting(chapter, pid, 'zang_ba', 'donghai')
            self.assertEqual(faction_officer_counts(self.catalogs[chapter])['zang_ba'], 7)
        for pid in ('historical-xu-xi', 'historical-mao-hui'):
            self.assert_posting('196-06', pid, None, 'donghai')

    def test_early_sun_followers_and_later_sun_xiang_career_remain_distinct(self):
        for pid in ('san14-candidate-0289', 'san14-candidate-0543'):
            self.assert_posting('188-06', pid, 'sun_jian', 'changsha')
        self.assertEqual(faction_officer_counts(self.catalogs['188-06'])['sun_jian'], 7)
        for pid in ('san14-candidate-0572', 'san14-candidate-0567'):
            self.assert_posting('188-06', pid, None, 'wujun')
        for chapter in ('190-01', '191-10'):
            for pid in ('historical-gongchou-cheng', 'historical-sun-xiang'):
                self.assert_posting(chapter, pid, 'sun_jian', 'changsha')
        self.assert_posting('194-06', 'historical-sun-xiang', 'yuan_shu', 'jiujiang')
        self.assert_posting('198-03', 'historical-sun-xiang', 'yuan_shu', 'runan')

    def test_wu_ju_staff_and_qian_bo_later_office_respect_years(self):
        for chapter in ('207-09', '208-10'):
            for pid in WU_JU_STAFF:
                self.assert_posting(chapter, pid, 'wu_ju', 'cangwu')
            self.assertEqual(faction_officer_counts(self.catalogs[chapter])['wu_ju'], 4)
        for chapter in ('211-07-tongguan', '212-12', '221-07', '225-07'):
            game = self.game(chapter)
            self.assertNotIn(self.catalogs[chapter].ids['historical-heng-yi-cangwu'], game.state.officers)
        for chapter in ('221-07', '225-07', '227-02'):
            self.assert_posting(chapter, 'historical-qian-bo-cangwu', 'wu', 'gaoliang')

    def test_gongsun_courtiers_have_single_id_and_real_city_membership(self):
        for pid in GONGSUN_233:
            self.assert_posting('234-02', pid, 'gongsun', 'liaodong')
        for pid in GONGSUN_233 + GONGSUN_238:
            self.assert_posting('238-01', pid, 'gongsun', 'liaodong')
        game = self.game('238-01', 'gongsun')
        self.assertEqual(faction_officer_counts(self.catalogs['238-01'])['gongsun'], 15)
        self.assertEqual(len(game.state.cities['liaodong'].roster.officer_ids), 13)
        self.assertEqual(len([p for p in self.people.values() if p['name'] in ('柳甫', '柳浦')]), 1)
        self.assertEqual(self.people['historical-heng-yi-cangwu']['chronology_design']['historical_death_year'], 211)
        for pid in ('historical-liu-fu-liaodong', 'historical-wang-jian-liaodong',
                    'historical-bi-sheng', 'historical-gongsun-xiu'):
            row = next(r for r in self.sources['238-01']['initial_officers'] if r['person_id'] == pid)
            self.assertTrue(row['resolve_death_year'])

    def test_reviewed_existing_postings_and_jiaozhi_namesake_are_not_reverted(self):
        self.assert_posting('212-12', 'san14-candidate-0263', 'gongsun', 'liaodong')
        for pid in ('san14-candidate-0259', 'san14-candidate-0693'):
            self.assert_posting('212-12', pid, 'zhang_lu', 'hanzhong')
        self.assert_posting('212-12', 'san14-candidate-0867', 'wei', 'anding')
        for pid in ('san14-candidate-0259', 'san14-candidate-0693', 'san14-candidate-0830'):
            self.assert_posting('215-08', pid, None, 'hanzhong')
        self.assert_posting('221-07', 'san14-candidate-0475', 'wei', 'jingzhao')
        self.assert_posting('225-07', 'san14-candidate-0096', 'nanman', 'jianning')
        self.assert_posting('263-05', 'historical-li-tong-jiaozhi', 'lu_xing', 'jiaozhi')
        self.assertNotEqual(self.people['historical-li-tong-jiaozhi']['runtime_id'],
                            self.people['san14-candidate-0911']['runtime_id'])

    def test_all29_runtime_openings_conserve_material_and_have_no_duplicate_officers(self):
        materials = {row['id']: row['material'] for row in self.review['scenarios']}
        for chapter, catalog in self.catalogs.items():
            with self.subTest(chapter=chapter):
                game = self.game(chapter)
                memberships = [ident for city in game.state.cities.values()
                               for ident in city.roster.officer_ids]
                self.assertEqual(len(memberships), len(set(memberships)))
                self.assertTrue(all(len(c.roster.officer_ids) <= 99 for c in game.state.cities.values()))
                expected = materials[catalog.data['id']]
                self.assertEqual(sum(c.gold for c in game.state.cities.values()), expected['gold'])
                self.assertEqual(sum(c.grain for c in game.state.cities.values()), expected['grain'])
                soldiers = sum(c.reserves for c in game.state.cities.values()) + sum(
                    o.troops for o in game.state.officers.values() if o.faction_id is not None)
                self.assertEqual(soldiers, expected['soldiers'])
                initial = {catalog.ids[r['person_id']] for key in ('initial_officers', 'initial_free_officers')
                           for r in catalog.data[key]}
                self.assertEqual(set(game.state.officers), initial)
                for pid in NEW_IDS:
                    person, ident = catalog.by_id[catalog.ids[pid]], catalog.ids[pid]
                    if ident in initial:
                        self.assertLessEqual(person['birth_year'], game.state.year)
                        self.assertLessEqual(person['service_year'], game.state.year)
                        self.assertGreaterEqual(person['death_year'], game.state.year)
                game.validate(game.state)

    def test_new_stats_use_authored_defaults_except_sourced_wang_jian_health(self):
        for pid in NEW_IDS:
            with self.subTest(person=pid):
                person = self.people[pid]
                self.assertEqual(person['profile']['virtue'], 60)
                self.assertEqual(person['profile']['health_max'], 80)
                self.assertEqual(person['initialization']['health'], 42 if pid == 'historical-wang-jian-liaodong' else 80)
                self.assertIsNone(person['virtue_design']['source_charisma'])
                self.assertTrue(person['chronology_design']['precision'])
                self.assertTrue(person['chronology_design']['basis'])
        wang = self.people['historical-wang-jian-liaodong']
        self.assertEqual((wang['profile']['martial_strength'], wang['profile']['intellect']), (24, 75))
        self.assertEqual(wang['initialization']['source_loyalty']['value'], 59)
        self.assertEqual(wang['initialization']['source_loyalty']['faction_ids'], [])
        game = self.game('238-01')
        officer = game.state.officers[self.catalogs['238-01'].ids['historical-wang-jian-liaodong']]
        self.assertEqual((officer.health, officer.loyalty), (42, 80))

    def test_early_campaign_can_reach_late_same_year_service_and_death_once(self):
        # Isolate the real appearance service at exact date boundaries. This
        # catches a window that exists in metadata but cannot create its person
        # because service and death share238 and the review flag was omitted.
        late = ('historical-wang-jian-liaodong', 'historical-bi-sheng',
                'historical-gongsun-xiu')
        catalog = self.catalogs['184-02']
        for year in (237, 238, 239):
            with self.subTest(year=year):
                game = self.game('184-02')
                game.state.year, game.state.month = year, 1
                rng = game.state.rng.state, game.state.rng.draws
                game._spawn_eligible(game.state)
                for pid in late:
                    ident = catalog.ids[pid]
                    if year == 238:
                        self.assertIn(ident, game.state.officers)
                        self.assertIsNone(game.state.officers[ident].faction_id)
                        self.assertEqual(game.state.extension['free_locations'][str(ident)], 'liaodong')
                        self.assertEqual(game.state.officers[ident].health,
                                         42 if pid == 'historical-wang-jian-liaodong' else 80)
                    else:
                        self.assertNotIn(ident, game.state.officers)
                saved = canonical(game.export_save())
                game._spawn_eligible(game.state)
                self.assertEqual(canonical(game.export_save()), saved)
                self.assertEqual((game.state.rng.state, game.state.rng.draws), rng)

    def test_actual_previews_and_signed_saves_preserve_rosters_rng_and_reconciliation(self):
        for chapter, faction, city in (
            ('190-01', 'zhang_miao', 'chenliu'), ('188-06', 'sun_jian', 'changsha'),
            ('198-03', 'zang_ba', 'donghai'), ('207-09', 'wu_ju', 'cangwu'),
            ('238-01', 'gongsun', 'liaodong'), ('263-05', 'lu_xing', 'jiaozhi'),
        ):
            with self.subTest(chapter=chapter):
                session = CampaignSession([self.paths[chapter]])
                session.command('new', dict(scenario='mainland' + chapter, faction=faction, seed=20261027), 0)
                game, catalog = session.game, self.catalogs[chapter]
                saved, rng = canonical(session.export_save()), (game.state.rng.state, game.state.rng.draws)
                preview = session.preview_city('mainland' + chapter, city)['city']
                self.assertEqual([row['id'] for row in preview['officers']], game.state.cities[city].roster.officer_ids)
                self.assertEqual(preview['owner'], faction)
                self.assertEqual(canonical(session.export_save()), saved)
                self.assertEqual((game.state.rng.state, game.state.rng.draws), rng)
                payload = session.export_save()
                twin = Campaign(catalog)
                twin.load_save(payload, 0)
                self.assertEqual(canonical(twin.export_save()), canonical(game.export_save()))
                postings = {i: o.faction_id for i, o in twin.state.officers.items()}
                twin._spawn_eligible(twin.state)
                twin._reconcile_factions(twin.state)
                twin.validate(twin.state)
                self.assertEqual({i: o.faction_id for i, o in twin.state.officers.items()}, postings)


if __name__ == '__main__':
    unittest.main()
