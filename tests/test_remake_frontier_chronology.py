"""Keep the Hetao opening previews and live calendar in agreement."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))

from remake import civil_staff
from remake.city_economy import TIER_MULTIPLIERS
from remake.events import transition, validate
from remake.session import CampaignSession


CAMPAIGNS = ROOT / 'game/data/campaigns'
CITIES = ('shuofang', 'wuyuan', 'yunzhong')
PARENT_CITIES = dict(zip(CITIES, ('anding', 'xihe', 'yanmen')))
RESOURCE_FIELDS = ('gold', 'grain', 'reserves')
COUNTY_NAMES = ('临戎', '九原', '云中旧城')
NEUTRAL = ('neutral', 'neutral', 'neutral')
EXPECTED_OWNERS = {
    '184-02': ('han', 'han', 'han'),
    '188-06': NEUTRAL,
    '190-01': NEUTRAL,
    '191-10': NEUTRAL,
    **dict.fromkeys(('194-06', '196-06', '197-07', '198-03', '200-01', '201-05'),
                    ('neutral', 'yuan_shao', 'yuan_shao')),
    '202-06': ('neutral', 'gao_gan', 'gao_gan'),
    **dict.fromkeys(('207-09', '208-10', '209-06', '210-11', '211-07-tongguan', '212-12'),
                    ('neutral', 'wei', 'wei')),
    '212-06': ('neutral', 'cao_zhang', 'wei'),
    **dict.fromkeys(('215-08', '217-07', '219-07', '221-07', '225-07', '227-02', '234-02'), NEUTRAL),
    **dict.fromkeys(('235-01', '238-01', '249-01', '263-05'), ('wei', 'neutral', 'neutral')),
}


class FrontierChronologyTests(unittest.TestCase):
    def test_all_opening_previews_match_reviewed_owners_names_and_economies(self):
        paths = sorted(path for path in CAMPAIGNS.glob('*.json') if path.name != 'index.json')
        self.assertEqual({path.stem for path in paths}, set(EXPECTED_OWNERS))
        session = CampaignSession(paths)
        previews = {row['id']: row for row in session.view()['catalog']['scenarios']}
        for chapter, owners in EXPECTED_OWNERS.items():
            opening = previews[f'mainland{chapter}']
            data = session.catalogs[opening['id']].data
            year = opening['year']
            names = ('朔方', '五原', '云中') if year < 215 else (
                COUNTY_NAMES if year < 235 else ('朔方', *COUNTY_NAMES[1:]))
            for city, name, owner in zip(CITIES, names, owners):
                with self.subTest(chapter=chapter, city=city):
                    self.assertIn(city, opening['active_cities'])
                    self.assertEqual(opening['city_names'][city], name)
                    detail = session.preview_city(opening['id'], city)['city']
                    self.assertEqual(opening['initial_owners'][city], owner)
                    self.assertEqual(detail['owner'], owner)
                    self.assertEqual(detail['history']['opening']['owner'], owner)
                    if owner != 'neutral':
                        faction = next(row for row in opening['factions'] if row['id'] == owner)
                        self.assertEqual(detail['owner_name'], faction['name'])
                    else:
                        label = '河套地方部众（中立）'
                        self.assertEqual(opening['city_history'][city]['neutral_label'], label)
                        self.assertEqual(detail['owner_name'], label)
                    outpost = 215 <= year and (city != 'shuofang' or year < 235)
                    self.assertEqual(detail['profile'].get('kind') == 'frontier_outpost', outpost)
                    self.assertEqual(bool(detail['frontier_outpost']), outpost)
                    stocks = {field: detail[field] for field in RESOURCE_FIELDS}
                    self.assertGreater(min(detail['income'].values()), 0)
                    if outpost:
                        zero = dict.fromkeys(RESOURCE_FIELDS, 0)
                        self.assertEqual(stocks, zero)
                    else:
                        parent = PARENT_CITIES[city]
                        scale = TIER_MULTIPLIERS[data['city_profiles'][parent]['tier']]
                        self.assertEqual(stocks, {field: data['initial_city_resources'][parent][field] // (2 * scale)
                                                  for field in RESOURCE_FIELDS})
                        self.assertGreater(min(stocks.values()), 0)

    def test_opening_stocks_match_preview_and_new_campaign(self):
        chapters = ('184-02', '225-07', '235-01')
        session = CampaignSession([CAMPAIGNS / f'{chapter}.json' for chapter in chapters])
        for chapter, faction in (('184-02', 'han'), ('225-07', 'wei'), ('235-01', 'wei')):
            scenario = f'mainland{chapter}'
            session.command('new', dict(scenario=scenario, faction=faction, seed=7521), session.revision)
            for city in CITIES:
                with self.subTest(chapter=chapter, city=city):
                    preview = session.preview_city(scenario, city)['city']
                    active = session.game.state.cities[city]
                    self.assertEqual(tuple(getattr(active, field) for field in RESOURCE_FIELDS),
                                     tuple(preview[field] for field in RESOURCE_FIELDS))

    def test_live_date_boundaries_preserve_territory_and_emit_once(self):
        for chapter, year, renamed in (('212-12', 215, dict(zip(CITIES, COUNTY_NAMES))),
                                       ('234-02', 235, {'shuofang': '朔方'})):
            with self.subTest(year=year):
                session = CampaignSession([CAMPAIGNS / f'{chapter}.json'])
                session.command('new', dict(faction='shu', seed=7521, lifespan='none'), 0)
                game = session.game
                state = game.state
                while (state.year, state.month, state.day) < (year - 1, 12, 21):
                    game._complete_turn(state)
                city = state.cities['shuofang']
                city.owner, city.gold, city.grain, city.reserves = 'shu', 60, 80, 0
                before = deepcopy(state)
                game._complete_turn(state)
                transition(game, before, state, 'ai', {})
                civil_staff.synchronize(game, state, checks=False)
                self.assertEqual((state.year, state.month, state.day), (year, 1, 1))
                self.assertIs(state.cities['shuofang'], city)
                self.assertEqual(city.owner, 'shu')
                self.assertGreater(city.gold, 60)
                self.assertGreater(city.grain, 80)
                self.assertGreater(city.reserves, 0)
                receipts = [row for row in state.extension['events']['items'] if row['kind'] == 'city_renamed'
                            and row['city_ids'][0] in CITIES]
                self.assertEqual({row['city_ids'][0]: row['details']['to_name'] for row in receipts}, renamed)
                self.assertEqual(len(receipts), len(renamed))
                validate(game, state)
                view = session.view()['catalog']
                self.assertEqual(set(view['frontier_outposts']), set(CITIES) if year == 215 else set(CITIES[1:]))


if __name__ == '__main__':
    unittest.main()
