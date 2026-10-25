"""Scenario swatches are readable display data, never historical/save edits."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.map_presentation import color_distance,color_lab,faction_colors
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
        self.assertEqual(len(self.catalogs['mainland190-01'].factions),26)
        for identity,catalog in self.catalogs.items():
            palette=faction_colors(catalog)
            self.assertEqual(set(palette),{'neutral',*catalog.factions},identity)
            self.assertEqual(palette['neutral'],'#ffffff')
            fills=[palette[key] for key in catalog.factions]
            self.assertEqual(len(fills),len(set(fills)),identity)
            for color in fills:
                # Avoid pale fills resembling neutral and dark ones merging
                # into the unmodified black pixel border.
                self.assertGreaterEqual(color_lab(color)[0],35,identity)
                self.assertGreaterEqual(color_distance(color,'#ffffff'),30,identity)
                self.assertGreaterEqual(color_distance(color,'#000000'),30,identity)
            for i,color in enumerate(fills):
                for other in fills[i+1:]:
                    self.assertGreaterEqual(color_distance(color,other),29,identity)

    def test_native_colors_remain_unchanged_when_their_spacing_is_sufficient(self):
        # Isolate the original native set; the real expanded198 palette is
        # separately checked above for every faction, including Song Jian.
        original=SimpleNamespace(factions={key:row for key,row in
            self.catalogs['mainland198-03'].factions.items() if key!='song_jian'})
        self.assertEqual(faction_colors(original),{
            'neutral':'#ffffff', 'gongsun':'#009438', 'gongsun_zan':'#f83800',
            'han_sui':'#b8f818', 'hua_xin':'#008088', 'li_jue':'#d800cc',
            'liu_biao':'#6844fc', 'liu_zhang':'#00e8d8', 'lubu':'#b8b8f8',
            'ma_teng':'#fc7460', 'shi_xie':'#e4c490', 'shu':'#f8b800',
            'wei':'#0078f8', 'wu':'#f85898', 'yuan_shao':'#a868b8',
            'yuan_shu':'#607c00', 'zhang_lu':'#b8e8b8', 'zhang_xiu':'#b87800',
            'zhang_yang':'#888888'})

    def test_larger_unknown_catalogs_keep_distinct_deterministic_visible_fills(self):
        identities=['wei','shu','wu','nanman',*(f'future_{n:02d}' for n in range(36))]
        catalog=SimpleNamespace(factions=dict.fromkeys(identities,{}))
        first=faction_colors(catalog)
        reversed_catalog=SimpleNamespace(factions=dict(reversed(list(catalog.factions.items()))))
        self.assertEqual(faction_colors(reversed_catalog),first)
        self.assertEqual(len(set(first.values())),41)
        for identity in identities:
            self.assertGreaterEqual(color_lab(first[identity])[0],35)
            self.assertGreaterEqual(color_distance(first[identity],'#ffffff'),30)
            self.assertGreaterEqual(color_distance(first[identity],'#000000'),30)

    def test_nanman_is_cyan_and_shu_gold_in_every_current_preview(self):
        current=list(self.catalogs.values())
        self.assertEqual(len(current),29)
        for catalog in current:
            palette=faction_colors(catalog)
            for key,expected in [('wei','#0078f8'),('shu','#f8b800'),('wu','#f85898')]:
                if key in catalog.factions:self.assertEqual(palette[key],expected,catalog.data['id'])
        palette=faction_colors(self.catalogs['mainland225-07'])
        self.assertEqual(palette['nanman'],'#00e8d8')
        self.assertGreater(color_distance(palette['nanman'],palette['shu']),100)

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
