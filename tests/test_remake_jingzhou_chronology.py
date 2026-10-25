"""Reviewed Jingzhou dates in opening catalogs, views and continuing campaigns.

Month boundaries are authored game dates where the historical source gives only
a year. The 209-06 opening's Cao ownership is an explicit scenario exception.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Campaign, Catalog
from remake import civil_staff, domestic, logistics
from remake.map_presentation import city_names
from remake.session import CampaignSession
from campaign_fixtures import advance_month


CAMPAIGNS = ROOT / 'game/data/campaigns'


def catalog(chapter):
    return Catalog(CAMPAIGNS / f'{chapter}.json')


def start(chapter, faction=None, *, city_disasters=True):
    source = catalog(chapter)
    if not city_disasters:
        # Chronology-only replay: preserve the catalog used by other cases.
        data = deepcopy(source.data)
        data.setdefault('facility_rules', {})['disasters_enabled'] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'chronology.json'
            path.write_text(json.dumps(data, ensure_ascii=False))
            source = Catalog(path)
    game = Campaign(source)
    faction = faction or next(iter(game.catalog.factions))
    game.command('new', dict(faction=faction, seed=2026), 0)
    return game


class JingzhouChronologyTests(unittest.TestCase):
    def test_names_resolve_month_boundaries_in_every_catalog(self):
        dates = [((210, 11), 'yidu', '临江'),
                 ((210, 12), 'yidu', '宜都'),
                 ((221, 12), 'yiyang', '章陵'),
                 ((222, 1), 'yiyang', '义阳')]
        for path in sorted(CAMPAIGNS.glob('*.json')):
            if path.name == 'index.json':
                continue
            chapter = Catalog(path)
            for date, city, expected in dates:
                with self.subTest(chapter=path.stem, date=date, city=city):
                    self.assertEqual(city_names(chapter, *date)[city], expected)

    def test_session_uses_current_month_and_preserves_opening_preview(self):
        session = CampaignSession([CAMPAIGNS / '210-11.json'])
        session.command('new', dict(faction='wu', seed=2026), 0)
        before = session.view()
        self.assertEqual(next(c['name'] for c in before['catalog']['cities']
                              if c['id'] == 'yidu'), '临江')
        advance_month(session.game)
        after = session.view()
        self.assertEqual((after['game']['year'], after['game']['month']), (210, 12))
        self.assertEqual(next(c['name'] for c in after['catalog']['cities']
                              if c['id'] == 'yidu'), '宜都')
        opening = next(s for s in after['catalog']['scenarios']
                       if s['id'] == session.game.catalog.data['id'])
        self.assertEqual(opening['city_names']['yidu'], '临江')

    def test_linjiang_opens_in_september_208_not_in_earlier_chapters(self):
        chapter = catalog('207-09')
        self.assertNotIn('yidu', chapter.active_city_ids(208, 8))
        self.assertIn('yidu', chapter.active_city_ids(208, 9))
        rule = chapter.data['city_foundings']['yidu']
        self.assertEqual((rule['year'], rule['month']), (208, 9))
        self.assertNotIn('yidu', start('207-09', 'wu').state.cities)
        self.assertIn('yidu', start('208-10', 'wu').state.cities)

    def test_early_han_chapters_do_not_backdate_liu_biao_rule(self):
        for chapter in ('184-02', '188-06'):
            with self.subTest(chapter=chapter):
                game = start(chapter)
                self.assertNotIn('liu_biao', game.catalog.factions)
                self.assertEqual(game.state.cities['yiyang'].owner, 'neutral')
                self.assertNotIn('liu_biao',
                                 {c.owner for c in game.state.cities.values()})
                game.validate(game.state)

    def test_zhangling_belongs_to_liu_biao_in_his_existing_era_chapters(self):
        for chapter in ('191-10', '194-06', '200-01'):
            with self.subTest(chapter=chapter):
                game = start(chapter, 'liu_biao')
                self.assertEqual(game.catalog.data['initial_owners']['yiyang'],
                                 'liu_biao')
                self.assertEqual(game.state.cities['yiyang'].owner, 'liu_biao')
                self.assertEqual(city_names(game.catalog, game.state.year,
                                            game.state.month)['yiyang'], '章陵')
                game.validate(game.state)

    def test_207_zhangling_keeps_liu_bei_playable_with_explicit_exception(self):
        game = start('207-09', 'shu')
        self.assertEqual(game.state.cities['yiyang'].owner, 'shu')
        note = game.catalog.data['city_history']['yiyang']['opening']['note']
        self.assertRegex(note, r'刘备|劉備')
        self.assertRegex(note, r'用户|使用者|user')
        self.assertRegex(note, r'例外|保留|playable')
        game.validate(game.state)

    def test_cao_linjiang_openings_and_liu_yidu_opening(self):
        # The later 209-06 DLC is an authored alternative opening, rather than
        # a replayed historical conquest overriding an already running campaign.
        for chapter in ('208-10', '209-06'):
            with self.subTest(chapter=chapter):
                game = start(chapter, 'wei')
                self.assertEqual(game.catalog.data['initial_owners']['yidu'], 'wei')
                self.assertEqual(game.state.cities['yidu'].owner, 'wei')
                self.assertEqual(city_names(game.catalog, game.state.year,
                                            game.state.month)['yidu'], '临江')
                game.validate(game.state)
        game = start('212-12', 'shu')
        self.assertEqual(game.state.cities['yidu'].owner, 'shu')
        self.assertEqual(city_names(game.catalog, 212, 12)['yidu'], '宜都')
        game.validate(game.state)

    def test_abolition_removes_yiyang_only_from_later_new_openings(self):
        for chapter in ('249-01', '263-05'):
            with self.subTest(chapter=chapter):
                game = start(chapter, 'wu')
                self.assertNotIn('yiyang', game.catalog.data['active_cities'])
                self.assertNotIn('yiyang', game.catalog.active_city_ids(
                    game.state.year, game.state.month))
                self.assertNotIn('yiyang', game.state.cities)
                self.assertNotIn('yiyang', game.view()['catalog']['active_cities'])
                self.assertFalse(any(row['city'] == 'yiyang'
                                     for row in game.catalog.data['initial_officers']))
                session = CampaignSession([CAMPAIGNS / f'{chapter}.json'])
                with self.assertRaises(ValueError):
                    session.preview_city(game.catalog.data['id'], 'yiyang')
                game.validate(game.state)

    def test_continuing_217_campaign_keeps_its_city_after_240(self):
        game = start('217-07', 'wu', city_disasters=False)
        city = game.state.cities['yiyang']
        original_owner = city.owner
        original_rng = game.state.rng.state, game.state.rng.draws
        while (game.state.year, game.state.month) < (240, 2):
            advance_month(game)
            game._reconcile_factions(game.state)
            logistics.synchronize(game, game.state)
            domestic.synchronize(game, game.state)
            civil_staff.synchronize(game, game.state, checks=False)
            self.assertIs(game.state.cities['yiyang'], city)
            self.assertEqual(city.owner, original_owner)
        self.assertEqual((game.state.year, game.state.month), (240, 2))
        self.assertIn('yiyang', game.view()['catalog']['active_cities'])
        self.assertEqual((game.state.rng.state, game.state.rng.draws), original_rng)
        game.validate(game.state)
        restored = Campaign(game.catalog)
        restored.load_save(game.export_save(), 0)
        self.assertEqual(restored.to_dict(), game.to_dict())


if __name__ == '__main__':
    unittest.main()
