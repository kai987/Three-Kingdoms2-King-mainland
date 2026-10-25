"""Four dated DLC openings and separately dated Tongguan/entry-into-Shu campaigns."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
sys.path.insert(0, str(ROOT / 'source'))
import build_campaigns as builder
from remake.campaign import Catalog
from remake.session import CampaignSession

EXPECTED = {
    'mainland198-03': (198, 3, '呂布討伐戰'),
    'mainland202-06': (202, 6, '河北爭亂'),
    'mainland211-07-tongguan': (211, 7, '潼關之戰'),
    'mainland215-08': (215, 8, '合淝之戰'),
}


class DlcCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ROOT / 'game/data/campaigns/index.json').read_text())
        cls.paths = [ROOT / 'game/data' / name for name in cls.index['catalogs']]
        cls.catalogs = {c.data['id']: c for c in map(Catalog, cls.paths)}

    def test_four_official_dlc_dates_and_two_kinds_cover_every_current_opening(self):
        self.assertEqual(len(self.catalogs), 29)
        class CampaignCount(HTMLParser):
            count = None
            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == 'meta' and attributes.get('name') == 'game-campaign-count':
                    self.count = int(attributes['content'])
        page = CampaignCount()
        page.feed((ROOT / 'game/index.html').read_text())
        self.assertEqual(page.count, len(self.catalogs), 'Stale-service warnings must use the published scenario count')
        self.assertEqual(self.index['default'], 'mainland217-07')
        fictional = {key for key, c in self.catalogs.items()
                     if c.data['main_scenario'].get('fictional', False)}
        self.assertEqual(len(fictional), 6)
        for key, (year, month, title) in EXPECTED.items():
            with self.subTest(scenario=key):
                data = self.catalogs[key].data
                self.assertEqual((data['start_year'], data['start_month']), (year, month))
                self.assertIn(title, data['title'])
                self.assertNotIn(key, fictional)
                meta = data['main_scenario']
                sources = [meta.get('official_source', ''), *meta.get('source_urls', [])]
                self.assertIn('https://www.gamecity.com.tw/sangokushi14/scenario.html', sources)
                self.assertEqual(len(data['people']), 1023)
                self.assertEqual(data['rules']['city_officer_capacity'], 99)
                self.assertEqual(data['rules']['battle_officers_per_side'], 10)

    def test_tongguan_and_entry_into_shu_keep_their_dates_through_new_and_save_restore(self):
        session = CampaignSession(self.paths)
        previews = {row['id']: row for row in session.view()['catalog']['scenarios']}
        entry, tongguan = 'mainland212-12', 'mainland211-07-tongguan'
        self.assertNotIn('mainland211-07', previews)
        self.assertIn('入蜀', previews[entry]['title'])
        self.assertIn('潼關', previews[tongguan]['title'])
        for key, date in ((entry, (212, 12)), (tongguan, (211, 7))):
            self.assertEqual((previews[key]['year'], previews[key]['month']), date)
        self.assertNotEqual(self.catalogs[entry].sha256, self.catalogs[tongguan].sha256)
        for selected, other, faction, date in ((entry, tongguan, 'shu', (212, 12)),
                                               (tongguan, entry, 'ma_teng', (211, 7))):
            with self.subTest(scenario=selected):
                session.command('new', dict(scenario=selected, faction=faction, seed=2026), session.revision)
                self.assertEqual((session.game.state.year, session.game.state.month), date)
                saved = json.loads(json.dumps(session.export_save(), ensure_ascii=False))
                session.command('new', dict(scenario=other, faction='shu', seed=2026), session.revision)
                self.assertEqual(session.game.catalog.data['id'], other)
                session.load_save(saved, session.revision)
                self.assertEqual(session.game.catalog.data['id'], selected)
                self.assertEqual((session.game.state.year, session.game.state.month), date)
                self.assertEqual(session.export_save(), saved)

    def test_canonical_build_retimes_entry_into_shu_without_removing_tongguan(self):
        with tempfile.TemporaryDirectory() as folder:
            index = builder.build(output=Path(folder))
            self.assertEqual(len(index['catalogs']), 29)
            self.assertNotIn('campaigns/211-07.json', index['catalogs'])
            self.assertFalse((Path(folder) / '211-07.json').exists())
            for stem, title, date in [('212-12', '入蜀', (212, 12)),
                                      ('211-07-tongguan', '潼關', (211, 7))]:
                data = json.loads((Path(folder) / f'{stem}.json').read_text())
                self.assertEqual(data['id'], 'mainland' + stem)
                self.assertEqual((data['start_year'], data['start_month']), date)
                self.assertIn(title, data['title'])
                self.assertIn(f'campaigns/{stem}.json', index['catalogs'])

    def test_variant_source_rejects_path_traversal_and_mismatched_identity_or_date(self):
        source = ROOT / 'game/config/campaigns'
        original_index = json.loads((source / 'index.json').read_text())
        entry = next(e for e in original_index['scenarios']
                     if e['id'] == 'mainland211-07-tongguan')
        valid = json.loads((source / entry['file']).read_text())
        with tempfile.TemporaryDirectory() as folder:
            temporary = Path(folder)
            for name in ('people.json', 'shared.json'):
                shutil.copyfile(source / name, temporary / name)
            (temporary / 'scenarios').mkdir()
            target = temporary / entry['file']
            index_path = temporary / 'index.json'
            index = dict(schema='tk2-campaign-sources-v1', default=entry['id'], scenarios=[entry])
            index_path.write_text(json.dumps(index))
            target.write_text(json.dumps(valid))
            with patch.object(builder, 'SOURCE', temporary):
                self.assertEqual(builder.load_sources(timing=False)[1][0]['id'], entry['id'])
                for bad_file in ('../211-07-tongguan.json', 'scenarios/211-07-../secret.json',
                                 'scenarios/211-07-Tongguan.json'):
                    broken = deepcopy(index)
                    broken['scenarios'][0]['file'] = bad_file
                    index_path.write_text(json.dumps(broken))
                    with self.subTest(file=bad_file), self.assertRaises(ValueError):
                        builder.load_sources(timing=False)
                index_path.write_text(json.dumps(index))
                for field, value in [('scenario_variant', 'other'), ('start_month', 8),
                                     ('id', 'mainland212-12')]:
                    broken = deepcopy(valid)
                    broken['overrides']['set'][field] = value
                    target.write_text(json.dumps(broken))
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        builder.load_sources(timing=False)


if __name__ == '__main__':
    unittest.main()
