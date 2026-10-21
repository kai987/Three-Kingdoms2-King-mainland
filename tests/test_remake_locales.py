"""Offline display conversion and historical proper-name protection."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_locales', ROOT / 'game/build_locales.py')
locales = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locales)


class TraditionalLocaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/locales/zh-hant.json').read_text())

    def traditional(self, text):
        for stage in self.data['stages']:
            text = locales.convert(text, stage)
        return text

    def test_ui_place_and_officer_names_use_traditional_with_context(self):
        for original, expected in [
            ('三国·大陆战役', '三國·大陸戰役'),
            ('选择武将，确认出征，预备兵与粮食', '選擇武將，確認出征，預備兵與糧食'),
            ('阴平、成都、长安、洛阳、建业、山阴、郁林', '陰平、成都、長安、洛陽、建業、山陰、鬱林'),
            ('于禁、于吉、刘辟、钟会、钟繇、范疆', '于禁、于吉、劉辟、鍾會、鍾繇、范疆'),
        ]:
            with self.subTest(original=original):
                self.assertEqual(self.traditional(original), expected)

    def test_conversion_keeps_numbers_identifiers_and_urls(self):
        source = 'fca4d51 mainland217-07-v11 7.5 120 80–90% https://www.gamecity.com.tw/'
        self.assertEqual(self.traditional(source), source)

    def test_bundled_opencc_sources_match_pinned_revision_and_license(self):
        source = ROOT / 'game/locales/opencc'
        info = json.loads((source / 'source.json').read_text())
        self.assertEqual(self.data['source_revision'], info['revision'])
        self.assertEqual(info['license'], 'Apache-2.0')
        for filename, file_info in info['files'].items():
            self.assertEqual(hashlib.sha256((source / filename).read_bytes()).hexdigest(), file_info['sha256'])

    def test_offline_rebuild_is_deterministic_without_touching_catalogs(self):
        path = ROOT / 'game/locales/zh-hant.json'
        before = path.read_bytes()
        catalogs = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'game/data').rglob('*.json')}
        locales.build()
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(all(hashlib.sha256(p.read_bytes()).hexdigest() == value for p, value in catalogs.items()))


if __name__ == '__main__':
    unittest.main()
