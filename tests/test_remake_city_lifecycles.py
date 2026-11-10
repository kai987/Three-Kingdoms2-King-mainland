"""Month-accurate city opening without conquest replay or new resources."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest
from remake import civil_staff, domestic, facilities, logistics, treasures, city_development
from remake.map_presentation import city_names
from campaign_fixtures import advance_month as advance_calendar_month


def synchronize(game, state, **options):
    """Manual fixtures mirror transaction reconciliation without running work."""
    logistics.synchronize(game, state)
    domestic.synchronize(game, state)
    civil_staff.synchronize(game, state, **options)
    treasures.synchronize(game, state)
    facilities.synchronize(game, state)
    city_development.synchronize(game, state)


def advance_month(game):
    # Direct service fixtures bypass command-level extension reconciliation.
    advance_calendar_month(game)
    synchronize(game, game.state, checks=False)


class CityLifecycleTests(unittest.TestCase):
    def fixture(self, month=10, *, retirement_month=None):
        # A controlled fixture moves the existing future node to an imminent
        # month. It tests scheduling, not a new historical claim about新兴.
        data=json.loads((ROOT/'game/data/campaigns/207-09.json').read_text())
        data['id']='month-opening-fixture'
        data['city_foundings']['xinxing'].update(year=207,month=month)
        if retirement_month is not None:
            data['city_retirements']['xinxing'] = dict(
                year=207, month=retirement_month, parent='taiyuan', scope='scenario_opening_only')
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'fixture.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)

    def start(self,catalog,side='wu'):
        game=Campaign(catalog)
        game.command('new',dict(faction=side,seed=2026),0)
        return game

    def test_catalog_and_runtime_views_use_exact_month(self):
        catalog=self.fixture(11)
        self.assertNotIn('xinxing',catalog.active_city_ids(207))
        self.assertNotIn('xinxing',catalog.active_city_ids(207,10))
        self.assertIn('xinxing',catalog.active_city_ids(207,11))
        game=self.start(catalog)
        self.assertNotIn('xinxing',game.view()['catalog']['active_cities'])
        advance_month(game);game.validate(game.state)
        self.assertEqual((game.state.year,game.state.month),(207,10))
        self.assertNotIn('xinxing',game.state.cities)
        self.assertNotIn('xinxing',game.view()['catalog']['active_cities'])
        advance_month(game);game.validate(game.state)
        self.assertIn('xinxing',game.state.cities)
        self.assertIn('xinxing',game.view()['catalog']['active_cities'])

    def test_opening_inherits_actual_parent_owner_and_only_splits_resources(self):
        game=self.start(self.fixture())
        parent=game.state.cities['taiyuan']
        for ident in list(parent.roster.officer_ids):
            recipient=next(c for c in game.state.cities.values() if c.owner==parent.owner
                           and c.id!=parent.id and len(c.roster.officer_ids)<game.catalog.rules.city_officer_capacity)
            parent.roster.officer_ids.remove(ident);recipient.roster.officer_ids.append(ident)
        parent.owner='wu'
        synchronize(game, game.state, checks=False)
        game.validate(game.state)
        parent_before={key:getattr(parent,key) for key in ('gold','grain','reserves')}
        troops_before=sum(o.troops for o in game.state.officers.values())
        rng_before=deepcopy(game.state.rng)
        advance_month(game);game.validate(game.state)
        child=game.state.cities['xinxing']
        self.assertEqual(child.owner,'wu')
        self.assertEqual(child.roster.officer_ids,[])
        self.assertEqual(game.state.rng,rng_before)
        self.assertEqual(sum(o.troops for o in game.state.officers.values()),troops_before)
        for field in ('gold','grain','reserves'):
            parent_income=game.catalog.data['city_income']['taiyuan'][field]
            child_income=game.catalog.data['city_income']['xinxing'][field]
            self.assertEqual(getattr(parent,field)+getattr(child,field),
                             parent_before[field]+parent_income+child_income)
        snapshot=game.to_dict()
        game._open_dated_cities(game.state)
        self.assertEqual(game.to_dict(),snapshot)
        event=next(text for text in game.state.log if '新兴建置' in text)
        self.assertIn('太原当时归属',event)

    def test_pre_and_post_month_saves_reject_wrong_city_domain(self):
        catalog=self.fixture()
        game=self.start(catalog)
        before=game.export_save();loaded=Campaign(catalog)
        loaded.load_save(before,0);self.assertEqual(loaded.to_dict(),game.to_dict())
        bad=deepcopy(before)
        bad['state']['cities']['xinxing']=deepcopy(bad['state']['cities']['taiyuan'])
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises(ValueError):loaded.load_save(bad,loaded.revision)
        self.assertEqual(loaded.to_dict(),game.to_dict())
        advance_month(game);game.validate(game.state)
        after=game.export_save();loaded.load_save(after,loaded.revision)
        self.assertEqual(loaded.to_dict(),game.to_dict())
        bad=deepcopy(after);del bad['state']['cities']['xinxing']
        bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
        with self.assertRaises(ValueError):loaded.load_save(bad,loaded.revision)
        self.assertEqual(loaded.to_dict(),game.to_dict())

    def test_xindu_founding_keeps_early_history_and_if_openings_distinct(self):
        historical = Catalog(ROOT/'game/data/campaigns/207-09.json')
        alternate = Catalog(ROOT/'game/data/campaigns/197-07.json')
        self.assertNotIn('xindu', historical.active_city_ids(207, 12))
        self.assertIn('xindu', alternate.active_city_ids(197, 7))
        game = self.start(historical)
        for month in (10, 11, 12):
            advance_month(game)
            self.assertEqual((game.state.year, game.state.month), (207, month))
            self.assertNotIn('xindu', game.state.cities)
        advance_month(game)
        self.assertEqual((game.state.year, game.state.month), (208, 1))
        self.assertEqual(game.state.cities['xindu'].owner, game.state.cities['danyang'].owner)
        self.assertIn('xindu', game.view()['catalog']['active_cities'])
        game.validate(game.state)

    def test_new_opening_cannot_recreate_a_retired_city_at_month_rollover(self):
        late = self.start(self.fixture(8, retirement_month=9))
        self.assertNotIn('xinxing', late.state.cities)
        advance_month(late)
        self.assertNotIn('xinxing', late.state.cities)
        late.validate(late.state)

        early = self.start(self.fixture(10, retirement_month=11))
        advance_month(early)
        self.assertIn('xinxing', early.state.cities)
        advance_month(early)
        self.assertIn('xinxing', early.state.cities)
        early.validate(early.state)

    def test_all_opening_maps_match_recorded_foundings_and_withdrawals(self):
        data_dir = ROOT/'game/data/campaigns'
        index = json.loads((data_dir/'index.json').read_text())
        foundings = {'xindu': (208, 1), 'yidu': (208, 9), 'xinxing': (215, 1),
                     'changli': (244, 9), 'pingyang': (247, 5),
                     'linhai': (257, 2), 'linchuan': (257, 2), 'hengyang': (257, 2),
                     'xiangdong': (257, 2), 'jianping': (260, 1), 'jianan': (196, 1),
                     'wuxing': (266, 12)}
        old_counties = {'hefei', 'guangling', 'chaisang', 'xicheng', 'shangyong', 'yiling',
                        'wenshan', 'yinping', 'dangqu', 'linhe', 'tianshui', 'xiping', 'fanyang',
                        'wuchang', 'gaoliang'}
        self.assertEqual(len(index['catalogs']), 29)
        for path in index['catalogs']:
            catalog = Catalog(data_dir/Path(path).name)
            date = (catalog.data['start_year'], catalog.data['start_month'])
            active = set(catalog.data['active_cities'])
            with self.subTest(scenario=catalog.data['id']):
                self.assertEqual(active, set(catalog.active_city_ids(*date)))
                self.assertEqual(active, set(catalog.data['initial_owners']))
                self.assertLessEqual({row['city'] for row in catalog.data['initial_officers']}, active)
                self.assertLessEqual(old_counties, active)
                self.assertEqual('yiyang' in active, date < (240, 1))
                for city, founding in foundings.items():
                    alternate_xindu = city == 'xindu' and date in ((197, 7), (201, 5))
                    self.assertEqual(city in active, alternate_xindu or date >= founding, city)
                names = city_names(catalog, *date)
                for city, (boundary, early, late) in {
                    'wenshan': ((215, 1), '綿虒道', '汶山'),
                    'yinping': ((229, 1), '陰平道', '陰平'),
                    'tianshui': ((228, 1), '漢陽', '天水'),
                    'xiping': ((214, 1), '西平亭', '西平'),
                    'fanyang': ((224, 1), '涿县', '范阳'),
                    'wuchang': ((221, 4), '鄂县', '武昌'),
                    'jianan': ((260, 10), '建安县', '建安'),
                }.items():
                    if city in active:
                        self.assertEqual(names[city], late if date >= boundary else early, city)
                self.assertEqual(names['gaoliang'], '高凉')

    def test_early_county_opening_and_renames_at_live_calendar_boundaries(self):
        early = Catalog(ROOT/'game/data/campaigns/184-02.json')
        self.assertIn('wuchang', early.active_city_ids(184, 2))
        self.assertNotIn('jianan', early.active_city_ids(195, 12))
        self.assertIn('jianan', early.active_city_ids(196, 1))
        for city, previous, next_date, first_name, second_name in (
            ('wuchang', (221, 3), (221, 4), '鄂县', '武昌'),
            ('xiping', (213, 12), (214, 1), '西平亭', '西平'),
            ('jianan', (260, 9), (260, 10), '建安县', '建安'),
        ):
            with self.subTest(city=city):
                self.assertIn(city, early.active_city_ids(*previous))
                self.assertIn(city, early.active_city_ids(*next_date))
                self.assertEqual(city_names(early, *previous)[city], first_name)
                self.assertEqual(city_names(early, *next_date)[city], second_name)

    def test_former_wu_cities_change_names_after_the_fall_of_wu(self):
        catalog = Catalog(ROOT/'game/data/campaigns/263-05.json')
        for date, yiling, xindu in [((280, 1), '西陵', '新都'), ((280, 3), '西陵', '新都'),
                                    ((280, 4), '夷陵', '新安')]:
            with self.subTest(date=date):
                self.assertLessEqual({'yiling', 'xindu'}, set(catalog.active_city_ids(*date)))
                names = city_names(catalog, *date)
                self.assertEqual((names['yiling'], names['xindu']), (yiling, xindu))

    def test_current_dated_city_boundaries_match_calendar_and_roundtrip(self):
        catalog=Catalog(ROOT/'game/data/campaigns/207-09.json')
        # Exact game boundaries are explicit even where the source gives only
        # a year. October/December there are authored dates, not historical claims.
        boundaries={'linhai':(257,2),'linchuan':(257,2),
                    'jianan':(196,1),'wuxing':(266,12),'changli':(244,9),
                    'pingyang':(247,5),'hengyang':(257,2),'xiangdong':(257,2),
                    'jianping':(260,1)}
        for city,(year,month) in boundaries.items():
            with self.subTest(city=city):
                rule=catalog.data['city_foundings'][city]
                self.assertEqual((rule['year'],rule['month']),(year,month))
                previous=(year,month-1) if month>1 else (year-1,12)
                self.assertNotIn(city,catalog.active_city_ids(*previous))
                self.assertIn(city,catalog.active_city_ids(year,month))
        game=self.start(catalog)
        while (game.state.year,game.state.month)<(266,12):
            before=(game.state.year,game.state.month)
            for city,date in boundaries.items():
                self.assertEqual(city in game.state.cities,before>=date)
            advance_month(game)
            game._spawn_eligible(game.state);game._reconcile_factions(game.state)
            now=(game.state.year,game.state.month)
            if now in boundaries.values():
                game.validate(game.state)
                for city,date in boundaries.items():
                    self.assertEqual(city in game.state.cities,now>=date)
                saved=game.export_save();loaded=Campaign(catalog)
                loaded.load_save(saved,0)
                self.assertEqual(loaded.to_dict(),game.to_dict())
        self.assertTrue(set(boundaries)<=set(game.state.cities))


if __name__=='__main__':unittest.main()
