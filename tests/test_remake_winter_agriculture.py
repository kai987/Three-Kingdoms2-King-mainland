"""Versioned winter weather, once-only agriculture and calendar accounting."""
from collections import Counter
from copy import deepcopy
import json
from random import Random
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from test_remake_winter_weather import Headless, ROOT

from remake import city_economy, facilities, faction_economy, grain_market, grain_units
from remake import winter_agriculture as agriculture
from remake import winter_climate as climate
from remake import winter_weather as weather
from remake.campaign import Catalog
from remake.errors import GameError


def weather_world(seed, version=23, *, month=11, flags=None):
    game = SimpleNamespace(catalog=SimpleNamespace(data={'start_year':184, 'start_month':month,
                                                             'calendar_rules':{'month_days':30}},
                                                    climate=SimpleNamespace(frozen_reaches={})))
    state = SimpleNamespace(seed=seed, year=184, month=month, extension={})
    weather.initialize(game, state, version, options=flags)
    return game, state


def full_ledger(state, score, *, finalized):
    pool = state.extension[weather.POOL]
    ledger = agriculture.begin_day(pool, (184, 11, 1), 1, complete_start=True)
    ledger['regions']['liaodong']['spring_cold_days'] = score//2
    ledger['regions']['liaodong']['spring_deep_snow_days'] = score%2
    if finalized:
        agriculture.finalize(ledger, agricultural=True)
    return ledger


class WinterAgriculture(TestCase):
    def test_winter_probability_and_distribution_keep_ten_day_slots(self):
        r = Random(23)
        _, candidate = weather_world(23)
        _, legacy = weather_world(23, 221)
        _, w1 = weather_world(23, flags=climate.flags('monthly_snow_probability'))
        for index in range(1000):
            region, month = r.choice(tuple(climate.REGIONS)), r.randrange(1, 13)
            old_months, old_chance, _, _ = climate.REGIONS[region]
            expected = climate.SNOW_PROBABILITIES[region][climate.WINTER_MONTHS.index(month)] if month in climate.WINTER_MONTHS else 0
            self.assertEqual(climate.snow_probability(candidate, region, month), expected)
            self.assertEqual(climate.snow_probability(legacy, region, month), old_chance if month in old_months else 0)
            self.assertEqual(climate.cold_normal(w1, region, month), climate.cold_normal(legacy, region, month))
            strengths = climate.severity_distribution(candidate, region)
            self.assertEqual(sum(strengths), 100)
            slot = index % 3
            snow, first, last = weather._snow_event(weather.seed_for(index+1), region, 185, month, slot,
                                                    expected, strengths, False)
            if snow:
                duration = last-first+1
                self.assertTrue(weather.DURATION[snow][0] <= duration <= weather.DURATION[snow][1])
                self.assertTrue(slot*10 < first <= last <= (slot+1)*10)
            self.assertEqual(bool(snow),weather.draw(weather.seed_for(index+1),region,185,month,slot,'snow',100)<expected)
            expected_exposure = sum(bp for _, _, bp in climate.seasonal_exposure(candidate, region, month))
            self.assertTrue(0 <= expected_exposure <= 10_000)

    def test_legacy_mask_matches_every_legacy_region_and_ice_field(self):
        new_game, fitted = weather_world(573, flags=climate.flags())
        old_game, original = weather_world(573, 221)
        for tick in range(1,241):
            weather.advance(new_game, fitted, tick)
            weather.advance(old_game, original, tick)
            a, b = (x.extension[weather.POOL] for x in (fitted,original))
            for key in b['regions']:
                self.assertEqual(b['regions'][key], {field:a['regions'][key][field] for field in b['regions'][key]})
            self.assertEqual(a['ice'],b['ice'])

    def test_actual_days_caps_partial_start_and_no_duplicates(self):
        copies = 0
        for seed in range(4,9):
            game, state = weather_world(seed)
            for tick in range(1,241):
                weather.advance(game,state,tick)
                snapshot = json.loads(json.dumps(state.extension))
                weather.advance(game,state,tick)
                self.assertEqual(state.extension,snapshot)
                versions = state.extension[weather.POOL]
                for region,row in versions['regions'].items():
                    self.assertTrue(0 <= row['depth'] <= climate.snow_depth_limit(state,region))
                copies += 1
            ledger = agriculture.ledger(state)
            self.assertTrue(ledger['finalized'] and ledger['complete_start'])
            for key in ('liaodong','northern_frontier','northwest','qinling_highlands'):
                self.assertGreater(ledger['regions'][key]['winter_snow_days'],0)
                self.assertEqual(versions['regions'][key]['depth'],0)
        self.assertGreaterEqual(copies,1000)
        self.assertEqual(weather.MELT[3],0)
        game, state = weather_world(23, month=2)
        for tick in range(1,121):
            weather.advance(game,state,tick)
        ledger = agriculture.ledger(state)
        self.assertFalse(ledger['complete_start'])
        self.assertEqual({row['agriculture_multiplier'] for row in ledger['regions'].values()},{100})
        self.assertEqual({row['agriculture_status'] for row in ledger['regions'].values()},{'insufficient'})

    def test_exceptional_wave_merges_daily_snow(self):
        _, seed = min((length, seed) for seed in range(1,250)
                      for first,last in (weather._exceptional_wave(weather.seed_for(seed),184),)
                      if first for length in (last-first+1,))
        game,state = weather_world(seed,flags={'exceptional_cold_wave':True})
        per_day = Counter()
        with weather.experiment(5,observe=lambda kind,row: per_day.update({(row['region'],row['tick']):row['severity']})
                                if kind=='region' else None):
            for tick in range(1,211):
                weather.advance(game,state,tick)
        ledger = agriculture.ledger(state)
        wave_days = {ledger['regions'][name]['exceptional_cold_days'] for name in climate.WAVE_REGIONS}
        self.assertEqual(len(wave_days),1)
        self.assertTrue(2 <= wave_days.pop() <= 4)
        for name in climate.WAVE_REGIONS:
            total = sum(climate.SNOWFALL[level] for (region,_),level in per_day.items() if region==name)
            self.assertEqual(ledger['regions'][name]['total_snowfall_units'],total)
        self.assertFalse(ledger['regions']['lingnan']['snow_cover_days'])

    def test_frozen_multipliers_apply_once_after_integer_production(self):
        rng = Random(2034)
        game,state = weather_world(2026)
        game.catalog.climate.cities={'liaodong':{'climate_region_id':'liaodong'}}
        scores = (0,11,15,19)
        factors = (100,95,90,85)
        for _ in range(1000):
            score, factor = rng.choice(tuple(zip(scores,factors)))
            grain = rng.randrange(100_000)
            month = rng.randrange(1,13)
            state.extension[weather.POOL]['agriculture'] = None
            full_ledger(state,score,finalized=True)
            with patch.object(city_economy,'_normal_income',return_value=dict(grain=grain,gold=20,reserves=7)):
                actual = city_economy.monthly_income(game,'liaodong',state,date=(185,month))
                self.assertEqual(actual['grain'],grain*(factor if month in agriculture.MONTHS else 100)//100)
                self.assertEqual((actual['gold'],actual['reserves']),(20,7))
        for factor, score in ((90,15), (103,0)):
            state.extension[weather.POOL]['agriculture'] = None
            ledger=full_ledger(state,score,finalized=False)
            if factor==103:
                ledger['regions']['liaodong'].update(total_snowfall_units=66,winter_snow_cover_days=95,final_snow_tick=152)
            agriculture.finalize(ledger,True)
            annual=sum(10_000*agriculture.multiplier(state,'liaodong',(185,month))//100 for month in range(1,13))
            self.assertEqual(annual,{90:116_000,103:121_200}[factor])

    def test_forecast_separates_pending_risk_and_known_income(self):
        game,state = weather_world(23)
        state.year,state.month,state.day = 185,5,11
        state.cities = {'liaodong':SimpleNamespace(id='liaodong', reserves=0, grain=0)}
        city=state.cities['liaodong']
        game.catalog.climate.cities={'liaodong':{'climate_region_id':'liaodong'}}
        pending=full_ledger(state,15,finalized=False)
        row=dict(residents=13_000,garrison=0,active=0,wage_grain=0,fixed=13_000,safety_reserve=0)
        def quote(date):
            return city_economy.monthly_income(game,'liaodong',state,date=date)
        with patch.object(city_economy,'_normal_income',side_effect=lambda *args:dict(grain=10_000,gold=0,reserves=0)), \
                patch.object(faction_economy.domestic,'earned_grain',return_value=0):
            before=deepcopy(state.extension)
            provisional=faction_economy._forecast(game,state,city,row,{},0,9,quote((185,6)))
            self.assertEqual(provisional.timeline[1][0],10_000)
            self.assertIsNotNone(provisional.agricultural_risk)
            self.assertEqual(state.extension,before)
            agriculture.finalize(pending,True)
            forecast=faction_economy._forecast(game,state,city,row,{},0,9,quote((185,6)))
            self.assertEqual(forecast.timeline[1][0],9_000)
            self.assertIsNone(forecast.agricultural_risk)

    def test_market_and_september_use_adjusted_regular_once(self):
        catalog=Catalog(ROOT/'game/data/campaigns/208-10.json')
        game=Headless(catalog,record_journal=False)
        game.command('new',dict(faction='wu',seed=17,weather_rules_version=23),0)
        state=game.state
        target='liaodong'
        city=state.cities[target]
        city.owner='wu'
        state.year,state.month = 209,9
        ledger=agriculture.begin_day(state.extension[weather.POOL],(208,11,1),1,complete_start=True)
        ledger['regions']['liaodong']['spring_cold_days']=8
        agriculture.finalize(ledger,True)
        history=state.extension['facilities']['harvest']
        history['disasters'].pop(target,None)
        stocks = city.grain
        with grain_units.using(state), patch.object(city_economy,'_normal_income',
                side_effect=lambda *args:dict(grain=10_000,gold=0,reserves=0)), \
                patch('remake.domestic.earned_grain',return_value=100):
            self.assertEqual(facilities.harvest_bonus(game,state,city),(9_000+100)*facilities.HARVEST_PERCENT//100)
            grain_market.restock(game,state)
            row=deepcopy(grain_market.row(state,target))
            grain_market.restock(game,state)
            self.assertEqual(row,grain_market.row(state,target))
            self.assertEqual(row['monthly_supply'],grain_market.supply(city_economy.town_level(game,state,target),9_000))
        self.assertEqual(city.grain,stocks)

    def test_new_versions_are_opt_in_and_save_roundtrip_is_read_only(self):
        catalog=Catalog(ROOT/'game/data/campaigns/208-10.json')
        for options in ({},{'weather_rules_version':22},{'weather_rules_version':221},
                        {'weather_rules_version':23,'weather_options':{'exceptional_cold_wave':True}}):
            game=Headless(catalog,record_journal=False)
            game.command('new',dict(faction='wu',seed=3,**options),0)
            initial=game.to_dict()
            for compact in (False,True):
                save=game.export_save(compact=compact)
                if compact:
                    self.assertEqual(save['state']['extension'].get(weather.FIELD),23 if options.get(weather.FIELD)==23 else None)
                same=Headless(catalog,record_journal=False)
                same.load_save(save,0)
                self.assertEqual(same.export_save(compact=compact),save)
                self.assertEqual(same.to_dict(),initial)
            self.assertEqual(game.to_dict(),initial)
        game=Headless(catalog,record_journal=False)
        with self.assertRaises(GameError):
            game.command('new',dict(faction='wu',seed=1,weather_rules_version=221,weather_options={'regional_snow_depth':True}),0)
