"""Scenario swatches are readable display data, never historical/save edits."""
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.map_presentation import color_distance,color_oklab,faction_colors
from remake.session import CampaignSession


class FactionPaletteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs={}
        index=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        if index['schema']!='tk2-campaign-index-v1' or len(index['catalogs'])!=29:
            raise AssertionError('Expected29 current campaign catalogs')
        for name in index['catalogs']:
            path=ROOT/'game/data'/name
            data=json.loads(path.read_text())
            if data['schema']!='tk2-campaign-v1':raise AssertionError('Unexpected campaign schema')
            cls.catalogs[data['id']]=SimpleNamespace(data={'id':data['id']},
                factions={row['id']:row for row in data['factions']})

    def test_all_current_scenarios_have_separated_visible_fills(self):
        self.assertEqual(len(self.catalogs),29)
        self.assertEqual(len(self.catalogs['mainland190-01'].factions),27)
        self.assertIn('zhang_miao',self.catalogs['mainland190-01'].factions)
        for identity,catalog in self.catalogs.items():
            palette=faction_colors(catalog)
            self.assertEqual(set(palette),{'neutral',*catalog.factions},identity)
            self.assertEqual(palette['neutral'],'#ffffff')
            fills=[palette[key] for key in catalog.factions]
            self.assertEqual(len(fills),len(set(fills)),identity)
            for color in fills:
                # Avoid pale fills resembling neutral and dark ones merging
                # into the unmodified black pixel border.
                self.assertGreaterEqual(color_oklab(color)[0],.43,identity)
                self.assertGreaterEqual(color_distance(color,'#ffffff'),.15,identity)
            for first,other in combinations(catalog.factions,2):
                self.assertGreaterEqual(color_distance(palette[first],palette[other]),.14,
                                        (identity,first,other,palette[first],palette[other]))

    def test_song_jian_has_clear_contrast_with_dong_zhuo_and_liu_yan(self):
        # The old pale greens looked alike at castle size even with a distinct RGB value.
        early=faction_colors(self.catalogs['mainland188-06'])
        self.assertGreaterEqual(color_distance(early['song_jian'],early['dong_zhuo']),.24)
        self.assertGreaterEqual(color_distance(early['song_jian'],early['liu_yan']),.20)

    def test_faction_colors_remain_stable_across_all_current_scenarios(self):
        colors={}
        for scenario,catalog in self.catalogs.items():
            for faction,color in faction_colors(catalog).items():
                if faction in colors:
                    self.assertEqual(color,colors[faction],f'{scenario}/{faction}')
                colors[faction]=color
        for predecessor,successor in [('liu_yan','liu_zhang'),('sun_jian','wu'),
                                      ('zhang_ji','zhang_xiu'),('yuan_shao','yuan_shang')]:
            self.assertEqual(colors[predecessor],colors[successor],successor)
        self.assertEqual(colors['liu_yan'],'#00e8d8')
        self.assertNotEqual(colors['liu_zhang'],colors['shu'])
        self.assertEqual(len({colors[faction] for faction in ('yuan_shang','yuan_tan','yuan_xi')}),3)

    def test_native_subset_keeps_the_fills_of_the_expanded_scenario(self):
        full=self.catalogs['mainland198-03']
        subset=SimpleNamespace(factions={key:row for key,row in full.factions.items()
                                          if key not in {'song_jian','zang_ba'}})
        self.assertEqual(len(subset.factions),18)
        palette=faction_colors(full)
        self.assertEqual(faction_colors(subset),{key:palette[key] for key in ['neutral',*subset.factions]})

    def test_new_zhang_miao_and_zang_ba_have_present_distinct_colors(self):
        for chapter,faction in (('mainland190-01','zhang_miao'),
                                ('mainland197-07','zang_ba'),
                                ('mainland198-03','zang_ba')):
            with self.subTest(chapter=chapter,faction=faction):
                catalog=self.catalogs[chapter]
                self.assertIn(faction,catalog.factions)
                palette=faction_colors(catalog)
                self.assertIn(faction,palette)
                for other,color in palette.items():
                    if other!=faction:
                        self.assertNotEqual(palette[faction],color,other)
                        self.assertGreaterEqual(color_distance(palette[faction],color),.14,other)
                reordered=SimpleNamespace(factions=dict(reversed(list(catalog.factions.items()))))
                self.assertEqual(faction_colors(reordered),palette)

    def test_larger_unknown_catalogs_keep_distinct_deterministic_visible_fills(self):
        identities=['wei','shu','wu','nanman',*(f'future_{n:02d}' for n in range(36))]
        catalog=SimpleNamespace(factions=dict.fromkeys(identities,{}))
        first=faction_colors(catalog)
        reversed_catalog=SimpleNamespace(factions=dict(reversed(list(catalog.factions.items()))))
        self.assertEqual(faction_colors(reversed_catalog),first)
        self.assertEqual(len(set(first.values())),41)
        for identity in identities:
            self.assertGreaterEqual(color_oklab(first[identity])[0],.43)
            self.assertGreaterEqual(color_distance(first[identity],'#ffffff'),.15)

    def test_nanman_is_cyan_and_shu_gold_in_every_current_preview(self):
        current=list(self.catalogs.values())
        self.assertEqual(len(current),29)
        for catalog in current:
            palette=faction_colors(catalog)
            for key,expected in [('wei','#0078f8'),('shu','#f8b800'),('wu','#f85898')]:
                if key in catalog.factions:self.assertEqual(palette[key],expected,catalog.data['id'])
        palette=faction_colors(self.catalogs['mainland225-07'])
        self.assertEqual(palette['nanman'],'#00e8d8')
        self.assertGreater(color_distance(palette['nanman'],palette['shu']),.24)

    def test_reordering_unknown_factions_and_mutated_result_do_not_change_palette(self):
        catalog=self.catalogs['mainland190-01']
        original=faction_colors(catalog)
        reordered=SimpleNamespace(factions=dict(reversed(list(catalog.factions.items()))))
        self.assertEqual(faction_colors(reordered),original)
        result=faction_colors(catalog);result['shu']='#ffffff'
        self.assertEqual(faction_colors(catalog),original)
        unknown=SimpleNamespace(factions={'new_b':{},'wei':{},'new_a':{}})
        first=faction_colors(unknown)
        self.assertEqual(first,faction_colors(SimpleNamespace(factions=dict(reversed(list(unknown.factions.items()))))))
        self.assertEqual(len(set(first.values())),4)
        self.assertEqual(unknown.factions,{'new_b':{},'wei':{},'new_a':{}})

    def test_current_save_and_previews_keep_the_same_palette_without_mutation(self):
        paths=[ROOT/'game/data/campaigns'/f'{date}.json' for date in ('184-02','190-01','225-07')]
        session=CampaignSession(paths)
        catalogs={key:deepcopy(c.data) for key,c in session.catalogs.items()}
        preview=session.view()
        for row in preview['catalog']['scenarios']:
            self.assertEqual(row['faction_colors'],faction_colors(session.catalogs[row['id']]))
        self.assertEqual(session.revision,0);self.assertIsNone(session.game.state)
        session.command('new',{'scenario':'mainland184-02','faction':'han','seed':2026},session.revision)
        saved=session.export_save();revision=session.revision
        palette=session.view()['catalog']['faction_colors']
        session.view();session.view()
        self.assertEqual(session.export_save(),saved);self.assertEqual(session.revision,revision)
        session.load_save(saved,revision)
        self.assertEqual(session.view()['catalog']['faction_colors'],palette)
        self.assertEqual({key:c.data for key,c in session.catalogs.items()},catalogs)


if __name__=='__main__':unittest.main()
