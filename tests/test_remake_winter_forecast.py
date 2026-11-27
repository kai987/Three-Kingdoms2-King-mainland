"""Seasonal estimates are versioned, bounded and independent of actual weather."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from test_remake_winter_weather import Headless, ROOT
from remake import granary_planning, logistics_rules, route_hazards
from remake import winter_climate, winter_forecast as forecast, winter_travel as travel, winter_weather as weather
from remake.campaign import Catalog
from remake.errors import GameError


class WinterForecastTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(ROOT/'game/data/campaigns/200-01.json')

    def campaign(self,forecast_version=231,weather_version=23):
        game=Headless(self.catalog,record_journal=False)
        settings=dict(faction='observer',seed=2026,weather_rules_version=weather_version)
        if forecast_version is not None:
            settings[forecast.FIELD]=forecast_version
        game.command('new',settings,0)
        return game

    def route(self,game,*,river=False):
        for row in sorted(game._known_routes(None),key=lambda route:route['id']):
            a,b=row['from'],row['to']
            if not all(route_hazards.route_allowed(self.catalog.data,row,x,y) for x,y in ((a,b),(b,a))):
                continue
            outward=route_hazards.evaluate_leg(self.catalog.data,row,a,b,3)
            parts=travel._parts_for_leg(game,outward)
            if river:
                match=any(part.reach in self.catalog.climate.frozen_reaches for part in parts)
            else:
                match=all(part.region=='liaodong' and part.mode in forecast.LAND for part in parts)
            if match:
                returning=route_hazards.evaluate_leg(self.catalog.data,row,b,a,3)
                return game._quote([a,b],[outward]),game._quote([b,a],[returning])
        self.fail('Actual catalog route required')

    def test_opt_in_and_both_save_formats(self):
        for version in (0,22,221,23):
            game=self.campaign(None,version)
            self.assertNotIn(forecast.FIELD,game.state.extension)
            checkpoint=game.export_save(compact=True)
            loader=Headless(self.catalog,record_journal=False)
            loader.load_save(checkpoint,0)
            self.assertEqual(loader.export_save(compact=True),checkpoint)
        game=self.campaign()
        for compact in (False,True):
            loader=Headless(self.catalog,record_journal=False)
            checkpoint=game.export_save(compact=compact)
            loader.load_save(checkpoint,0)
            self.assertEqual(loader.to_dict(),game.to_dict())
            self.assertEqual(loader.export_save(compact=compact),checkpoint)
        with self.assertRaises(GameError):
            self.campaign(231,221)
        with self.assertRaises(GameError):
            self.campaign(True)

    def test_same_weather_and_agriculture_over_full_season(self):
        old,new=self.campaign(None),self.campaign()
        for tick in range(1,520):
            for game in (old,new):
                weather.advance(game,game.state,tick)
            self.assertEqual(old.state.extension[weather.POOL],new.state.extension[weather.POOL])
        self.assertEqual(old.state.rng,new.state.rng)

    def test_april_snowpack_even_when_ordinary_event_probability_is_zero(self):
        game=self.campaign()
        state=game.state
        state.month,state.day=4,1
        route,_=self.route(game)
        region=state.extension[weather.POOL]['regions']['liaodong']
        region.update(depth=30,severity=0,cold=3)
        self.assertEqual(winter_climate.snow_probability(state,'liaodong',4),0)
        outlook=forecast.estimate(game,state,route)
        self.assertGreater(outlook['expected_arrival_days'],outlook['base_days'])
        self.assertGreater(forecast.snowpack_risk(state,'liaodong'),0)
        self.assertGreater(outlook['base_ration_weight'],0)
        self.assertEqual(
            travel._medium('plain',0,2,0,True)[1],
            travel._medium('plain',2,2,0,True)[1]*100//weather.WARMTH[2])

    def test_cache_keys_include_the_published_snow_and_current_date(self):
        game=self.campaign()
        state=game.state
        state.month,state.day=3,21
        route,_=self.route(game)
        region=state.extension[weather.POOL]['regions']['liaodong']
        region.update(depth=50,severity=0,cold=2)
        before=forecast.cache_stats()['route']['hits']
        old=forecast.estimate(game,state,route)
        self.assertEqual(old,forecast.estimate(game,state,route))
        self.assertGreater(forecast.cache_stats()['route']['hits'],before)
        region.update(depth=0,cold=0)
        state.month,state.day=6,21
        new=forecast.estimate(game,state,route)
        self.assertGreater(old['expected_arrival_days'],new['expected_arrival_days'])

    def test_departure_delay_dates_return_and_cost_without_future_draws(self):
        game=self.campaign()
        state=game.state
        state.month,state.day=12,20
        route,back=self.route(game)
        before=deepcopy(game.to_dict())
        with patch.object(weather,'draw',side_effect=AssertionError), patch.object(weather,'advance',side_effect=AssertionError):
            result=forecast.trip(game,state,route,back)
            returning=forecast.estimate(game,state,back,start_in=result['expected_arrival_days'])
        self.assertEqual(game.to_dict(),before)
        self.assertEqual(result['return_departure_days'],result['expected_arrival_days'])
        self.assertEqual(result['return_ration_weight'],returning['total_ration_weight'])
        self.assertGreaterEqual(result['conservative_arrival_days'],result['expected_arrival_days'])
        self.assertEqual(result['expected_arrival_days'],sum(result[key] for key in (
            'base_days','visible_weather_extra_days','seasonal_extra_days','predicted_ice_wait_days')))
        self.assertEqual(result['total_ration_weight'],sum(result[key] for key in (
            'base_ration_weight','visible_weather_extra_weight','seasonal_extra_weight','waiting_ration_weight')))
        self.assertLess(forecast.net_cargo(10_000,result),10_000)

    def test_forecast_thaw_is_not_present_legal_navigation(self):
        game=self.campaign()
        state=game.state
        state.month,state.day=3,21
        route,_=self.route(game,river=True)
        reach=next(part.reach for part in travel.plan(game,route)
                   if part.reach in self.catalog.climate.frozen_reaches)
        state.extension[weather.POOL]['ice'][reach].update(state=3,index=6_000)
        self.assertEqual(travel.closed_at_node(state,route,0),reach)
        self.assertIsNone(granary_planning._risk(game,state,route,seasonal=True))
        expected=forecast.estimate(game,state,route)
        self.assertFalse(expected['bounded'])
        self.assertEqual(expected['currently_blocked'],reach)
        self.assertGreaterEqual(expected['expected_arrival_days'],route['days'])
        self.assertIsNotNone(granary_planning._risk(game,state,route,offset=25,seasonal=True))
        self.assertEqual(travel.closed_at_node(state,route,0),reach)

    def test_public_probabilities_are_normalized(self):
        for table in (forecast.ROAD_NORMALS,forecast.RIVER_NORMALS):
            for profile in table.values():
                for slots in profile.values():
                    self.assertEqual(len(slots),36)
                    for slot in slots:
                        joint=slot[0] if table is forecast.ROAD_NORMALS else slot
                        self.assertEqual(sum(row[-1] for row in joint),forecast.SHARES)
