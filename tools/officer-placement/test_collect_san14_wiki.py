"""Offline boundary checks for the fact-only source collector."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('collector',Path(__file__).with_name('collect_san14_wiki.py'))
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ScenarioCollectorTests(unittest.TestCase):
    def test_html_and_pukiwiki_cells_parse_the_same_facts(self):
        html='<table><tr><td>211年7月　潼関の戦い</td><td>44</td><td>太守</td><td><a>洛陽</a></td><td><span>曹操</span></td><td>左将軍</td></tr></table>'
        wiki='|[[211年7月　潼関の戦い]]|44|太守|[[洛陽]]|BGCOLOR(#11f):COLOR(white):曹操|左将軍|'
        a,_,af=module.parsed_rows(html);b,_,bf=module.parsed_rows(wiki)
        self.assertEqual(af,'html_tables');self.assertEqual(bf,'pukiwiki_text')
        self.assertEqual(module.scenario_rows(a),module.scenario_rows(b))
        self.assertEqual(module.scenario_rows(a)[0]['ruler'],'曹操')

    def test_date_match_does_not_merge_distinct_titles_or_certify_unknown_fiction(self):
        rows=[['211年7月　潼関の戦い','44','太守','洛陽','曹操','左将軍'],
              ['211年7月　架空の章','44','在野','洛陽','-','-'],
              ['211年13月　invalid','44','太守','洛陽','曹操','左将軍']]
        parsed=module.scenario_rows(rows)
        self.assertEqual(len(parsed),2)
        self.assertNotEqual(parsed[0]['title'],parsed[1]['title'])
        self.assertEqual(parsed[1]['status'],'free')
        self.assertIsNone(parsed[1]['ruler'])
        self.assertEqual(parsed[1]['fiction_marker'],'not_classified')

    def test_same_names_require_explicit_qualified_index_links(self):
        person=dict(person_id='san14-candidate-0651',name_japanese='張南',name_traditional='張南')
        with self.assertRaisesRegex(RuntimeError,'Qualified same-name'):
            module.candidate_url(person,{'張南':{module.BASE+module.quote('張南(蜀)',safe='')}})
        url,method=module.candidate_url(person,{'張南':{module.BASE+module.quote('張南(袁)',safe='')}})
        self.assertTrue(url.endswith(module.quote('張南(袁)',safe='')))
        self.assertEqual(method,'explicit_qualified_homonym_index_link')

    def test_rate_limit_stops_network_and_records_retry_after(self):
        gate=module.RateGate(interval=3)
        gate.stop({'retry-after':'120'})
        self.assertEqual(gate.rate_limit['retry_after_seconds'],120)
        with self.assertRaisesRegex(RuntimeError,'paused after HTTP429'):
            gate.wait()
        with tempfile.TemporaryDirectory() as path:
            with patch.object(module.subprocess,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'No checked cache'):
                    module.fetch(module.BASE+'missing',Path(path),offline=True)
                run.assert_not_called()

    def test_unique_identity_keeps_chronology_disagreements_but_homonym_requires_review(self):
        body=('<table><tr><th>曹仁(ソウジン)</th><th>字</th><th>生年</th><th>登場</th><th>没年</th></tr>'
              '<tr><td></td><td>子孝</td><td>169</td><td>187</td><td>223</td></tr></table>'
              '<table><tr><td>211年7月　潼関の戦い</td><td>44</td><td>太守</td><td>洛陽</td><td>曹操</td><td>左将軍</td></tr></table>').encode()
        person=dict(person_id='san14-test',name_japanese='曹仁',name_traditional='曹仁',name_simplified='曹仁',
                    chronology=dict(game_birth_year=168,game_appearance_year=187,game_death_year=223))
        metadata=dict(response_sha256=module.sha(body),retrieved_at='2026-10-22T00:00:00+00:00',bytes=len(body))
        with patch.object(module,'fetch',return_value=(body,metadata)):
            row=module.collect(person,module.BASE+'test','unique_exact_name_officer_index_link',{(211,7)},Path('/unused'),True)
            self.assertEqual(row['chronology_disagreements']['birth'],dict(existing=168,wiki=169))
            self.assertEqual(person['chronology']['game_birth_year'],168)
            with self.assertRaisesRegex(RuntimeError,'Same-name page chronology mismatch'):
                module.collect(person,module.BASE+'test','explicit_qualified_homonym_index_link',{(211,7)},Path('/unused'),True)


if __name__=='__main__':unittest.main()
