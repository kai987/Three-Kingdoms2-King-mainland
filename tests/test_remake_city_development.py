"""Authentic integer formulas, pure reads and paid shared city development."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
sys.path.insert(0, str(ROOT/'tests'))
from remake import capital_openings, city_development as development, command_books, large_city_population
from remake import domestic, economy_rules, treasures
from test_remake_economy_v2 import reference_adjusted
from remake.errors import GameError
from remake.campaign import Campaign, Catalog
from remake.city_economy import income_at, tier_at
from remake.session import CampaignSession
from test_remake_facilities import fixture
from test_remake_civil_staff_campaign import staff_catalog


class SequenceRng:
    def __init__(self, values):
        self.values = list(values)
        self.draws = 0

    def next(self):
        value = self.values[self.draws]
        self.draws += 1
        return value

    def __eq__(self, other):
        return isinstance(other, SequenceRng) and self.__dict__ == other.__dict__


def setup():
    game, state = fixture()
    state.extension[economy_rules.FIELD] = economy_rules.CURRENT
    game.catalog.data['city_income'] = {key: dict(gold=120, grain=400, reserves=100) for key in state.cities}
    state.extension['city_development'] = development.empty(game, state)
    return game, state


class DevelopmentTests(unittest.TestCase):
    def refuse(self, game, state, payload, owner='one'):
        before = deepcopy(state)
        with self.assertRaises((GameError, ValueError, TypeError)):
            development.execute(game, state, payload, owner)
        self.assertEqual(before, state)

    def test_missing_extension_views_quotes_and_income_are_pure(self):
        game, state = setup()
        del state.extension['city_development']
        before = deepcopy(state)
        view = development.view(game, state)
        self.assertEqual(view['cities']['capital']['population'], 150000)
        self.assertEqual(view['cities']['enemy']['population'], 100000)
        self.assertEqual(view['cities']['border']['population'], 50000)
        self.assertEqual(set(view['cities']['capital']['actor_quotes']), {'1', '2', '3', '4', '5', '7'})
        self.assertEqual(view['cities']['enemy']['actor_quotes'], {})
        self.assertEqual(development.quote(game, state, 'capital', 1, 'develop_land')['gold_min'], 18)
        development.validate(game, state)
        for city in state.cities:
            base = game.catalog.data['city_income'][city]
            town = state.extension['facilities']['cities'][city]['town']
            opening = view['cities'][city]
            expected = dict(base, grain=reference_adjusted(base['grain'], opening['population'], town,
                                                           opening['land'], opening['land'], 60, 60))
            self.assertEqual(development.adjust_income(game, state, city, base), expected)
        self.assertEqual(before, state)

    def test_intellect_gold_bands_and_exact_effect_floor_order(self):
        game, state = setup()
        for actor, expected in ((2, (10, 18)), (3, (14, 22)), (1, (18, 26))):
            offer = development.quote(game, state, 'capital', actor, 'develop_land')
            self.assertEqual((offer['gold_min'], offer['gold_max']), expected)
        # Intellect90, cost26, R17: floor(26*.9)=23; floor(23*1.7)=39.
        state.rng = SequenceRng([4, 7])
        details = development.execute(game, state, dict(city='capital', actor=1, kind='develop_land'), 'one')
        self.assertEqual(details, dict(actor='person-1', development='land', gold=26,
            before=450, after=454, gain=4, governance_before=70, governance_after=72, gain_scale=10))
        self.assertEqual(state.cities['capital'].gold, 974)
        self.assertEqual(state.rng.draws, 2)
        self.assertEqual(state.events[-1]['kind'], 'city_developed')
        self.assertEqual(command_books.remaining(state, 'one'), 2)
        development.validate(game, state)

    def test_governor_bonus_rates_appointment_and_all_development_quotes(self):
        game, state = setup()
        state.extension['treasury'] = treasures.empty(game, state)
        governor = state.officers[1]
        treasures.set_governor(game, state, dict(city='capital', officer=1), 'one')
        profile = governor.profile
        for intellect, bonus in ((59, 0), (60, 5), (74, 5), (75, 10), (89, 10),
                                 (90, 11), (91, 12), (98, 19), (99, 20)):
            with self.subTest(intellect=intellect):
                governor.profile = replace(profile, intellect=intellect)
                offer = development.quote(game, state, 'capital', 3, 'develop_land')
                self.assertEqual(offer['governor_bonus_percent'], bonus)
        governor.profile = profile

        state.officers[5].profile = replace(state.officers[5].profile, intellect=99)
        treasures.set_governor(game, state, dict(city='capital', officer=5), 'one')
        for kind, minimum, maximum in (('develop_land', 2, 5), ('develop_industry', 2, 5),
                                        ('develop_population', 900, 2200)):
            with self.subTest(kind=kind):
                state.rng = SequenceRng([4, 7])
                saved = deepcopy(state)
                offer = development.view(game, state)['cities']['capital']['actor_quotes']['1'][kind]
                self.assertEqual(state, saved)
                self.assertEqual(offer['intellect'], 90)
                self.assertEqual(offer['governor_bonus_percent'], 20)
                self.assertEqual((offer['gain_min'], offer['gain_max']), (minimum, maximum))
                result = development.execute(game, state, dict(city='capital', actor=1, kind=kind), 'one')
                self.assertEqual((result['gain'], result['gold'], state.rng.draws), (maximum, 26, 2))

        city = state.extension['city_development']['cities']['capital']
        city['population'] = development.LIMITS['population'] - 100
        capped = development.quote(game, state, 'capital', 1, 'develop_population')
        self.assertEqual((capped['gain_min'], capped['gain_max']), (100, 100))
        state.extension['travel']['marches'] = [dict(officers=[5])]
        self.assertEqual(development.quote(game, state, 'capital', 1, 'develop_land')['governor_bonus_percent'], 11)

    def test_quote_extrema_equal_exhaustive_effects_for_every_intellect_and_cap_boundary(self):
        game, state = setup()
        row = state.extension['city_development']['cities']['capital']
        rng = deepcopy(state.rng)
        # The production profile domain is1..99; include0/100 as calculation
        # boundaries without weakening the real officer-profile validator.
        with patch.object(development, '_profile') as profile:
            for intellect in range(101):
                profile.return_value = SimpleNamespace(intellect=intellect)
                costs = development._gold_choices(intellect)
                for kind, field in development.ACTIONS.items():
                    quantum = 100 if field == 'population' else 1
                    cap = development.LIMITS[field]
                    boundaries = (0, 1, 30, 31, 32, 50) if field == 'population' else range(6)
                    before_values = {0, cap//quantum//2*quantum,
                        *(max(0, cap-units*quantum) for units in boundaries)}
                    for before in before_values:
                        row[field] = before
                        # Independent oracle over every cost and effect roll.
                        outcomes = []
                        for cost in costs:
                            for roll in range(10, 18):
                                units = max(1, (cost*intellect//100)*roll//10)
                                if field == 'population':
                                    units = max(1, units//2)
                                else:
                                    units = min(5, (units + 9) // 10)
                                outcomes.append(min(units*quantum, cap-before))
                        for governance in (0, 49, 50, 70, 98, 99, 100):
                            row['governance'] = governance
                            offer = development.quote(game, state, 'capital', 1, kind)
                            threshold = 3100 if field == 'population' else 4
                            governance_gains = [min(100, governance+1+(gain >= threshold))-governance for gain in outcomes]
                            context = (intellect, kind, before, governance)
                            self.assertEqual((offer['gain_min'], offer['gain_max']),
                                             (min(outcomes), max(outcomes)), context)
                            self.assertEqual((offer['governance_gain_min'], offer['governance_gain_max']),
                                             (min(governance_gains), max(governance_gains)), context)
        self.assertEqual(state.rng, rng, 'Exhaustive quote checks must not draw campaign RNG')

    def test_same_city_same_actor_can_spend_more_than_one_order(self):
        game, state = setup()
        state.rng = SequenceRng([0, 0, 0, 0, 0, 0])
        for _ in range(3):
            development.execute(game, state, dict(city='capital', actor=1, kind='develop_industry'), 'one')
        self.assertEqual(command_books.remaining(state, 'one'), 0)
        self.assertEqual(state.rng.draws, 6)
        self.refuse(game, state, dict(city='capital', actor=1, kind='develop_industry'))

    def test_population_units_and_actual_cap_governance(self):
        game, state = setup()
        row = state.extension['city_development']['cities']['capital']
        state.rng = SequenceRng([4, 7, 4, 7, 4, 7])
        result = development.execute(game, state, dict(city='capital', actor=1, kind='develop_population'), 'one')
        self.assertEqual(result['gain'], 1900)  # floor(39/2) hundreds.
        self.assertEqual(result['governance_after'], 71)
        row.update(land=998, governance=98)
        result = development.execute(game, state, dict(city='capital', actor=1, kind='develop_land'), 'one')
        self.assertEqual((result['gain'], result['governance_after']), (1, 99))
        result = development.execute(game, state, dict(city='capital', actor=1, kind='develop_land'), 'one')
        self.assertEqual((result['gain'], result['governance_after']), (0, 100))
        self.refuse(game, state, dict(city='capital', actor=1, kind='develop_land'))

    def test_refusals_precede_initialization_draws_and_payment(self):
        game, state = setup()
        del state.extension['city_development']
        payload = dict(city='capital', actor=1, kind='develop_land')
        for malformed in ({}, {**payload, 'amount': 99}, {**payload, 'kind': 'patrol'},
                          {**payload, 'actor': True}, {**payload, 'actor': '1'},
                          {**payload, 'city': 'enemy'}, {**payload, 'actor': 6}):
            self.refuse(game, state, malformed)
        state.cities['capital'].gold = 25
        self.refuse(game, state, payload)
        state.cities['capital'].gold = 1000
        state.extension['travel']['marches'] = [dict(officers=[1])]
        self.refuse(game, state, payload)
        state.extension['travel']['marches'] = []
        state.battle = dict(attackers=[dict(id=1)], defenders=[])
        self.refuse(game, state, payload)
        state.battle = None
        state.officers[1].health = 0
        self.refuse(game, state, payload)

    def test_income_independent_production_fields_and_difficulty(self):
        game, state = setup()
        row = state.extension['city_development']['cities']['capital']
        base = dict(gold=120, grain=400, reserves=100)
        opening = dict(base, grain=reference_adjusted(400, 150_000, 3, 450, 450, 60, 60))
        for difficulty in ('easy', 'normal', 'hard'):
            state.extension['difficulty'] = difficulty
            self.assertEqual(development.adjust_income(game, state, 'capital', base), opening)
        state.extension['difficulty'] = 'normal'
        row['land'] += 60
        changed = development.adjust_income(game, state, 'capital', base)
        self.assertGreater(changed['grain'], opening['grain'])
        self.assertEqual(changed['gold'], base['gold'])
        self.assertEqual(changed['reserves'], base['reserves'])
        for difficulty in ('easy', 'normal', 'hard'):
            state.extension['difficulty'] = difficulty
            self.assertEqual(development.adjust_income(game, state, 'capital', base), changed)
        row['population'] *= 2
        self.assertEqual(development.adjust_income(game, state, 'capital', base)['reserves'], 200)
        row['population'] = 0
        self.assertEqual(development.adjust_income(game, state, 'capital', base), dict(gold=0, grain=0, reserves=0))
        for governance, tax in ((0, 50), (50, 50), (51, 60), (70, 60), (71, 70), (80, 70),
                                (81, 80), (90, 80), (91, 90), (99, 90), (100, 100)):
            self.assertEqual(development.tax_rate(governance), tax)
        self.assertEqual(base, dict(gold=120, grain=400, reserves=100))

    def test_grain_uses_continuous_population_and_town_caps_regardless_of_opening_population(self):
        game, state = setup()
        city = state.extension['city_development']['cities']['capital']
        facility = state.extension['facilities']['cities']['capital']
        for town, cap in ((1, 50_000), (2, 90_000), (3, 150_000)):
            facility['town'] = town
            for population in (0, 1_900, 2_000, 3_900, 4_000, cap - 100, cap, 200_000, cap - 2_100):
                with self.subTest(town=town, population=population):
                    city['population'] = population
                    expected = reference_adjusted(400, population, town, 450, 450, 60, 60)
                    for opening_population in (8_000, 157_000):
                        city['baseline']['population'] = opening_population
                        income = development.adjust_income(game, state, 'capital', {'grain': 400})
                        self.assertEqual(income['grain'], expected)

    def test_negative_events_exact_floor_order_and_separate_categories(self):
        for category, roll in (('population', 0), ('resources', 1), ('development', 2)):
            with self.subTest(category=category):
                game, state = setup()
                row = state.extension['city_development']['cities']['capital']
                row.update(governance=19, population=15900, land=159, industry=175)
                state.cities['capital'].gold = 159
                state.cities['capital'].grain = 175
                state.month += 1
                state.rng = SequenceRng([49, roll])
                result = development.month_rollover(game, state)
                self.assertEqual(len(result), 1)
                details = result[0]
                self.assertEqual(details['category'], category)
                self.assertEqual(state.rng.draws, 2)
                expected = dict(population_loss=3600, gold_loss=0, grain_loss=0, land_loss=0, industry_loss=0) if category == 'population' else dict(population_loss=0, gold_loss=72, grain_loss=80, land_loss=0, industry_loss=0) if category == 'resources' else dict(population_loss=0, gold_loss=0, grain_loss=0, land_loss=72, industry_loss=80)
                self.assertEqual({key: details[key] for key in expected}, expected)
                self.assertEqual(row['cooldown'], 6)
                before = deepcopy(state)
                self.assertEqual(development.month_rollover(game, state), [])
                self.assertEqual(before, state)
                for _ in range(6):
                    state.month += 1
                    self.assertEqual(development.month_rollover(game, state), [])
                self.assertEqual(row['cooldown'], 0)
                self.assertEqual(state.rng.draws, 2)

    def test_population_loss_at_cap_retains_valid_partial_hundred(self):
        game, state = setup()
        row = state.extension['city_development']['cities']['capital']
        row.update(population=1_999_999, governance=19)
        state.month += 1
        state.rng = SequenceRng([0, 0])
        result, = development.month_rollover(game, state)
        self.assertEqual((result['population_loss'], row['population']), (499_600, 1_500_399))
        development.validate(game, state)

    def test_chance_strict_boundary_and_neutral_or_stable_no_draw(self):
        for governance, threshold in ((49, 5), (39, 10), (29, 30), (19, 50)):
            game, state = setup()
            state.extension['city_development']['cities']['capital']['governance'] = governance
            state.rng = SequenceRng([threshold])
            state.month += 1
            self.assertEqual(development.month_rollover(game, state), [])
            self.assertEqual(state.rng.draws, 1)
        game, state = setup()
        state.extension['city_development']['cities']['neutral']['governance'] = 0
        state.month += 1
        state.rng = SequenceRng([])
        self.assertEqual(development.month_rollover(game, state), [])
        self.assertEqual(state.rng.draws, 0)

    def test_disasters_reuse_residual_and_do_not_draw_or_touch_governance(self):
        game, state = setup()
        row = state.extension['city_development']['cities']['capital']
        before_draws = state.rng.draws
        self.assertEqual(development.on_disaster(game, state, 'capital', 'drought', 10), dict(land_loss=45, industry_loss=0))
        self.assertEqual(development.on_disaster(game, state, 'capital', 'flood', 10), dict(land_loss=40, industry_loss=45))
        self.assertEqual((row['land'], row['industry'], row['governance']), (365, 405, 70))
        self.assertEqual(state.rng.draws, before_draws)

    def test_ai_uses_each_remaining_book_and_never_acts_for_player(self):
        game, state = setup()
        before = deepcopy(state)
        self.assertEqual(development.auto_turn(game, state, 'one'), [])
        self.assertEqual(before, state)
        state.phase = 'ai'
        orders = command_books.remaining(state, 'two')
        state.rng = SequenceRng([4, 7] * orders)
        direct = deepcopy(state)
        result = development.auto_turn(game, state, 'two')
        self.assertEqual(len(result), orders)
        self.assertEqual(command_books.remaining(state, 'two'), 0)
        for receipt in result:
            kind = next(kind for kind, field in development.ACTIONS.items() if field == receipt['development'])
            development.execute(game, direct, dict(city='enemy', actor=6, kind=kind), 'two')
            self.assertEqual(receipt['gold'], direct.events[-1]['details']['gold'])
        self.assertEqual(state.cities['enemy'].gold, direct.cities['enemy'].gold)
        self.assertEqual(state.extension['city_development']['cities'], direct.extension['city_development']['cities'])
        before = deepcopy(state)
        self.assertEqual(development.auto_turn(game, state, 'two'), [])
        self.assertEqual(before, state)

    def test_ai_repairs_its_weak_industry_before_other_development(self):
        game, state = setup()
        state.phase = 'ai'
        city = state.extension['city_development']['cities']['enemy']
        city['industry'] = 2
        state.rng = SequenceRng([0, 0] * command_books.remaining(state, 'two'))

        result = development.auto_turn(game, state, 'two')

        self.assertEqual(result[0]['development'], 'industry')
        self.assertGreater(city['industry'], 2)
        self.assertEqual(command_books.remaining(state, 'two'), 0)

    def test_ownership_preserves_metrics_and_validation_rejects_tampered_schema(self):
        game, state = setup()
        row = state.extension['city_development']['cities']['capital']
        row.update(land=900, population=987600, governance=31)
        state.cities['capital'].owner = 'two'
        development.synchronize(game, state)
        self.assertEqual((row['owner'], row['land'], row['population'], row['governance']), ('two', 900, 987600, 31))
        development.validate(game, state)
        for key, value in (('population', 2_000_000), ('population', 12345), ('land', True), ('cooldown', 7),
                           ('baseline', dict(row['baseline'], governance=99))):
            candidate = deepcopy(state)
            candidate.extension['city_development']['cities']['capital'][key] = value
            with self.assertRaises(ValueError):
                development.validate(game, candidate)
        game.catalog.data['city_development_rules'] = dict(enabled=False)
        self.refuse(game, state, dict(city='enemy', actor=6, kind='develop_land'), 'two')


class DevelopmentCampaignTests(unittest.TestCase):
    def test_development_reaches_exact_population_cap_and_round_trips_save(self):
        catalog = Catalog(ROOT/'game/data/campaigns/217-07.json')
        game = Campaign(catalog)
        game.state = game._new('shu', 2026)
        ledger = game.state.extension['city_development']['cities']
        ledger['shujun']['population'] = 1_999_900
        offer = development.quote(game, game.state, 'shujun', 439, 'develop_population')
        self.assertEqual((offer['gain_min'], offer['gain_max']), (99, 99))
        game.command('develop_population', dict(city='shujun', actor=439), 0)
        saved = game.export_save()
        event = next(row for row in saved['state']['extension']['events']['items'] if row['kind'] == 'city_developed')
        self.assertEqual((event['details']['before'], event['details']['after'], event['details']['gain']),
                         (1_999_900, 1_999_999, 99))
        restored = Campaign(catalog)
        restored.load_save(json.loads(json.dumps(saved)), 0)
        self.assertEqual(restored.export_save(), saved)

    def test_legacy_city_development_save_keeps_progress_and_income_baseline(self):
        path = ROOT/'game/data/campaigns/221-07.json'
        catalog = Catalog(path)
        legacy = Campaign(catalog)
        legacy.state = legacy._new('shu', 2026)
        pool = legacy.state.extension['city_development']
        pool['schema'] = 'tk2-city-development-v1'
        for key, row in pool['cities'].items():
            size = {'normal': 1, 'large': 2, 'giant': 3}[catalog.data['city_profiles'][key]['tier']]
            baseline = development.opening_view(catalog, key, schema=development.LEGACY_SCHEMA)
            row.update(baseline, baseline=baseline.copy())
        old_row = pool['cities']['shujun']
        old_row.update(land=482, population=151300, governance=72)
        save = legacy.export_save()
        restored = Campaign(catalog)
        with patch.object(restored, 'view', return_value={}):
            restored.load_save(json.loads(json.dumps(save)), 0)
        development.synchronize(restored, restored.state)
        self.assertEqual(restored.export_save(), save)
        self.assertEqual(restored.state.extension['city_development']['cities']['shujun'], old_row)
        self.assertNotEqual(development.opening_view(catalog, 'shujun'), old_row['baseline'])
        income = income_at(catalog.data, 'shujun', 221, 7)
        self.assertGreater(development.adjust_income(restored, restored.state, 'shujun', income)['grain'],
                           income['grain'])

    def test_luoyang_fixed_opening_preserves_previous_saves(self):
        directory = ROOT/'game/data/campaigns'
        early = ('184-02', '188-06', '190-01')
        for scenario in (*early, '191-10', '221-07', '263-05'):
            with self.subTest(scenario=scenario):
                catalog = Catalog(directory/f'{scenario}.json')
                faction = catalog.data['initial_owners']['henan']
                game = Campaign(catalog)
                game.state = game._new(faction, 2026)
                pool = game.state.extension['city_development']
                baseline = pool['cities']['henan']['baseline']
                self.assertEqual(pool['cities']['henan']['population'], baseline['population'])
                if scenario in early:
                    self.assertEqual(development.opening_view(catalog, 'henan')['population'], 203_100)
                    self.assertEqual(baseline['population'], 203_100)
                    repeated = game._new(faction, 7)
                    self.assertEqual(repeated.extension['city_development']['cities']['henan']['baseline'],
                                     baseline)
                    self.assertEqual(game.state.rng.draws, 0)
                save = game.export_save()
                restored = Campaign(catalog)
                with patch.object(restored, 'view', return_value={}):
                    restored.load_save(json.loads(json.dumps(save)), 0)
                self.assertEqual(restored.export_save(), save)

                for schema in (development.PREVIOUS_SCHEMA, development.SEEDED_SCHEMA):
                    with self.subTest(schema=schema):
                        old = development.empty(game, game.state, schema=schema)
                        old_luoyang = old['cities']['henan']
                        self.assertNotEqual(old_luoyang['baseline']['population'], baseline['population'])
                        old_luoyang['population'] += 500
                        game.state.extension['city_development'] = old
                        save = game.export_save()
                        with patch.object(restored, 'view', return_value={}):
                            restored.load_save(json.loads(json.dumps(save)), restored.revision)
                        development.synchronize(restored, restored.state)
                        self.assertEqual(restored.export_save(), save)

    def test_historical_openings_preserve_previous_population_baselines(self):
        catalog = Catalog(ROOT/'game/data/campaigns/249-01.json')
        game = Campaign(catalog)
        game.state = game._new(catalog.data['initial_owners']['danyang'], 2026)
        large_city_baselines = development.empty(game, game.state, schema=development.LARGE_CITY_SCHEMA)['cities']
        old_catalog = Catalog(ROOT/'game/data/campaigns/249-01.json')
        older_game = Campaign(old_catalog)
        with patch.object(capital_openings, 'opening', return_value={}):
            older_game.state = older_game._new(catalog.data['initial_owners']['danyang'], 2026)
        self.assertNotEqual(older_game.state.cities['henan'].gold, game.state.cities['henan'].gold)
        self.assertNotEqual(older_game.state.extension['facilities'], game.state.extension['facilities'])
        large = set(large_city_population.OPENINGS)
        for schema, capitals_and_giants in (
                (development.LUOYANG_SCHEMA, {'henan', 'jingzhao', 'wei', 'yingchuan', 'shujun', 'danyang'}),
                (development.GIANT_CITY_SCHEMA, {'henan', 'jingzhao'}),
                (development.CAPITAL_SCHEMA, set()),
                (development.LARGE_CITY_SCHEMA, set())):
            with self.subTest(schema=schema):
                if schema in (development.CAPITAL_SCHEMA, development.LARGE_CITY_SCHEMA):
                    older_game.state = deepcopy(game.state)
                old = development.empty(older_game, older_game.state, schema=schema)
                for key, row in old['cities'].items():
                    differs = {field for field in development.LIMITS
                               if row['baseline'][field] != large_city_baselines[key]['baseline'][field]}
                    if key in large and schema != development.LARGE_CITY_SCHEMA:
                        self.assertEqual(differs, {'population'}, key)
                    else:
                        self.assertEqual(bool(differs), key in capitals_and_giants, key)
                    if differs or row['population'] % 1000 == 0:
                        row['population'] += 500
                older_game.state.extension['city_development'] = old
                save = older_game.export_save()
                restored = Campaign(catalog)
                with patch.object(restored, 'view', return_value={}):
                    restored.load_save(json.loads(json.dumps(save)), 0)
                development.synchronize(restored, restored.state)
                self.assertEqual(restored.export_save(), save)

    def test_dated_opening_estimates_preserve_v8_through_v10_saves(self):
        catalog = Catalog(ROOT/'game/data/campaigns/200-01.json')
        game = Campaign(catalog)
        game.state = game._new(catalog.data['initial_owners']['qiao'], 2026)
        for schema, city in ((development.HUNDRED_PLACE_SCHEMA, 'hefei'),
                             (development.ORDINARY_CITY_SCHEMA, 'xijun'),
                             (development.COMMANDERY_SCHEMA, 'guonei')):
            with self.subTest(schema=schema):
                old = development.empty(game, game.state, schema=schema)
                old['cities'][city]['population'] += 500
                self.assertNotEqual(old['cities'][city]['baseline'], development.opening_view(catalog, city))
                game.state.extension['city_development'] = old
                save = game.export_save()
                restored = Campaign(catalog)
                with patch.object(restored, 'view', return_value={}):
                    restored.load_save(json.loads(json.dumps(save)), 0)
                development.synchronize(restored, restored.state)
                self.assertEqual(restored.export_save(), save)

    def test_real_ai_turn_executes_the_same_paid_development_and_seeded_effect(self):
        data = deepcopy(staff_catalog(free=False).data)
        data['city_development_rules'].update(enabled=True, ai_enabled=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'actual-development-ai.json'
            path.write_text(json.dumps(data, ensure_ascii=False))
            game = Campaign(Catalog(path))
        with patch.object(game, 'view', return_value={}):
            game.command('new', dict(faction='wu', seed=2026), 0)
        # Leave actual staff hiring active, but reserve competing troop/reward
        # orders so a productive development opportunity genuinely exists.
        domestic.appointments(game.state, 'shu')['policy']['reserve_target'] = 0
        game.state.extension['treasury']['factions']['shu']['enabled'] = False
        # Exercise the full strategic AI turn. Only aggregate response rendering
        # is omitted; appointments, budget competition and commands are real.
        real_execute = development.execute
        calls = []

        def compare_service(current_game, state, payload, owner):
            expected = deepcopy(state)
            before_gold = state.cities[payload['city']].gold
            before_books = command_books.remaining(state, owner)
            before_draws = state.rng.draws
            actual = real_execute(current_game, state, payload, owner)
            expected_receipt = real_execute(current_game, expected, payload, owner)
            self.assertEqual(actual, expected_receipt)
            self.assertEqual(state, expected)
            self.assertEqual(state.cities[payload['city']].gold, before_gold-actual['gold'])
            self.assertEqual(command_books.remaining(state, owner), before_books-1)
            self.assertEqual(state.rng.draws, before_draws+2)
            self.assertNotEqual(owner, state.player)
            calls.append((owner, deepcopy(payload)))
            return actual

        with patch.object(development, 'execute', side_effect=compare_service), \
                patch.object(game, 'view', return_value={}):
            turn = game.state.turn
            game.command('end_turn', {}, game.revision)
            self.assertEqual(game.state.phase, 'ai')
            while game.state.phase == 'ai':
                game.command('ai', dict(turn=turn), game.revision)
        self.assertTrue(calls, 'A real faction AI must actually commit development, not just quote it')
        self.assertGreater(len(calls), len({owner for owner, _ in calls}),
                           'A faction with remaining orders can develop more than once')
        game.validate(game.state)

    def test_all_29_opening_income_previews_and_three_saved_developments(self):
        paths = [path for path in sorted((ROOT/'game/data/campaigns').glob('*.json')) if path.name != 'index.json']
        self.assertEqual(len(paths), 29)
        session = CampaignSession(paths)
        examples, reviewed_baselines = {}, {}
        ordinary_cities = set()
        commanderies = json.loads((ROOT/'game/config/campaigns/commandery-history.json').read_text())
        new_commanderies = set(commanderies['new_sites'])
        dated_additions = new_commanderies | {'guonei', 'guangwei'}
        guangwei_series_start = development._ORDINARY_CITY_OPENINGS['guangwei'][0][0]
        for path in paths:
            with self.subTest(scenario=path.stem):
                catalog = session.catalogs['mainland' + path.stem]
                game = Campaign(catalog)
                # Full aggregate response serialization is exercised once per
                # opening below. Skip only repeated unrelated UI quote builds;
                # real copy transactions, event validation and saves still run.
                with patch.object(game, 'view', return_value={}):
                    game.command('new', dict(faction=next(iter(catalog.factions)), seed=2026), 0)
                before = game.export_save()
                view = game.view()['catalog']['city_development']
                self.assertEqual(set(view['cities']), set(game.state.cities))
                for field in development.LIMITS:
                    self.assertGreater(len({row[field] for row in view['cities'].values()}), 10)
                named = ('henan', 'jingzhao', 'wei', 'yingchuan', 'shujun', 'danyang', 'wenshan',
                         'hefei', 'jiangxia', 'xincheng', 'wuyuan', 'shuofang', 'yunzhong')
                additional_openings = sorted(dated_additions & game.state.cities.keys())
                for key in dict.fromkeys((*named, *large_city_population.OPENINGS, *additional_openings)):
                    preview = session.preview_city(catalog.data['id'], key)['city']
                    baseline = view['cities'][key]['baseline']
                    self.assertEqual(preview['city_development'], baseline)
                    self.assertEqual(preview['income'], view['cities'][key]['income'])
                    examples[path.stem, key] = baseline
                    if key in ('henan', 'jingzhao'):
                        city = game.state.cities[key]
                        for field in ('gold', 'grain'):
                            self.assertEqual(preview[field], getattr(city, field))
                        for field in ('town', 'preparedness', 'damage'):
                            self.assertEqual(preview['facilities'][field], game.state.extension['facilities']['cities'][key][field])
                        active = sum(game.state.officers[ident].troops for ident in city.roster.officer_ids)
                        self.assertEqual(sum(officer['troops'] for officer in preview['officers']), active)
                        base = income_at(catalog.data, key, game.state.year, game.state.month)
                        damage = preview['facilities']['damage']
                        base['grain'] = reference_adjusted(base['grain'], baseline['population'],
                            preview['facilities']['town'], baseline['land'], baseline['land'], 60, 60)
                        expected_income = {field: amount * (100-damage) // 100 for field, amount in base.items()}
                        expected_income['grain'] *= 2
                        self.assertEqual(preview['income'], expected_income)
                for key, row in view['cities'].items():
                    expected = development.opening_view(catalog, key, seed=game.state.seed)
                    self.assertEqual({field: row[field] for field in development.LIMITS}, expected)
                    previous = development.opening_view(catalog, key, schema=development.CAPITAL_SCHEMA)
                    reviewed = development.opening_view(catalog, key, schema=development.LARGE_CITY_SCHEMA)
                    previous_population_format = development.opening_view(catalog, key, schema=development.HUNDRED_PLACE_SCHEMA)
                    reviewed_baselines[path.stem, key] = reviewed
                    changed = {field for field in development.LIMITS if reviewed[field] != previous[field]}
                    if key not in large_city_population.OPENINGS or (key == 'qiao' and path.stem < '221-01'):
                        self.assertFalse(changed, key)
                    else:
                        self.assertTrue(changed <= {'population'}, key)
                    population = reviewed['population']
                    delta = previous_population_format['population'] - population
                    self.assertIn(delta, range(100, 1000, 100) if population % 1000 == 0 else (0,))
                    self.assertEqual({field: expected[field] for field in development.LIMITS if field != 'population'},
                                     {field: reviewed[field] for field in development.LIMITS if field != 'population'})
                    date = (game.state.year, game.state.month)
                    # Yongyang predates the dated Guangwei population series at this site.
                    pre_guangwei = key == 'guangwei' and date < guangwei_series_start
                    early_changan = key == 'jingzhao' and date <= (190, 1)
                    if key in new_commanderies:
                        old = development.opening_view(catalog, key, schema=development.ORDINARY_CITY_SCHEMA)
                        self.assertNotEqual(expected['population'], old['population'])
                        self.assertNotEqual(expected['population'] % 1000, 0)
                    elif key == 'guonei' or pre_guangwei or early_changan:
                        old = development.opening_view(catalog, key, schema=development.COMMANDERY_SCHEMA)
                        self.assertEqual(expected['population'] == old['population'],
                                         key == 'jingzhao' and date == (190, 1), (path.stem, key))
                    elif tier_at(catalog.data, key, *date) == 'normal' and key not in ('wuchang', 'luzon'):
                        ordinary_cities.add(key)
                        self.assertIn(key, development._ORDINARY_CITY_OPENINGS)
                        anchors = development._ORDINARY_CITY_OPENINGS[key]
                        self.assertTrue(anchors[0][0] <= date <= anchors[-1][0], (path.stem, key))
                        self.assertNotEqual(expected['population'] % 1000, 0, (path.stem, key))
                    else:
                        self.assertEqual(expected, previous_population_format, (path.stem, key))
                    base = income_at(catalog.data, key, game.state.year, game.state.month)
                    facility = game.state.extension['facilities']['cities'][key]
                    damage = facility['damage']
                    grain = reference_adjusted(base['grain'], expected['population'], facility['town'],
                                               expected['land'], expected['land'], 60, 60)
                    adjusted = dict(base, grain=grain)
                    expected_income = {field: amount * (100-damage) // 100 for field, amount in adjusted.items()}
                    expected_income['grain'] *= 2
                    self.assertEqual(row['income'], expected_income)
                    self.assertEqual(development.adjust_income(game, game.state, key, base), adjusted)
                    self.assertEqual(row['baseline'], expected)
                self.assertEqual(game.export_save(), before)
                restored = Campaign(catalog)
                with patch.object(restored, 'view', return_value={}):
                    restored.load_save(json.loads(json.dumps(before)), 0)
                self.assertEqual(restored.export_save(), before)
                game = restored
                # Use the scenario's genuine resident actor and stock/command
                # budget; no roster/resource mutation or skipped chronology.
                choice = next((key, actor) for key, row in view['cities'].items()
                              for actor in row['eligible_actors']
                              if all(row['actor_quotes'][str(actor)][kind]['eligible'] for kind in development.ACTIONS))
                key, actor = choice
                for kind, field in development.ACTIONS.items():
                    previous = deepcopy(game.state.extension['city_development']['cities'][key])
                    with patch.object(game, 'view', return_value={}):
                        game.command(kind, dict(city=key, actor=actor), game.revision)
                    game.validate(game.state)
                    current = game.state.extension['city_development']['cities'][key]
                    self.assertGreater(current[field], previous[field])
                    self.assertGreaterEqual(current['governance'], previous['governance'])
                    restored = Campaign(catalog)
                    with patch.object(restored, 'view', return_value={}):
                        restored.load_save(json.loads(json.dumps(game.export_save())), 0)
                    self.assertEqual(restored.export_save(), game.export_save())
                    # The next development really runs on the restored state.
                    game = restored
                self.assertEqual(game.state.rng.draws, before['state']['rng']['draws']+6)
        self.assertEqual(ordinary_cities, set(development._ORDINARY_CITY_OPENINGS))
        self.assertEqual(examples['200-01', 'hefei']['population'], 1_300)
        self.assertEqual(examples['202-06', 'hefei']['population'], 8_700)
        self.assertEqual(examples['200-01', 'qiao']['population'], 23_700)
        self.assertGreater(examples['219-07', 'jiangxia']['population'], examples['208-10', 'jiangxia']['population'])
        for field in development.LIMITS:
            self.assertLess(examples['191-10', 'henan'][field], examples['184-02', 'henan'][field])
            self.assertLess(examples['191-10', 'henan'][field], examples['221-07', 'henan'][field])
        recovery = [examples[path.stem, 'henan']['population'] for path in paths
                    if path.stem >= '191-10']
        self.assertEqual(recovery, sorted(set(recovery)))
        self.assertEqual((recovery[0], recovery[-1]), (6_900, 198_200))
        self.assertEqual(examples['191-10', 'jingzhao']['population'], 207_500)
        self.assertEqual(reviewed_baselines['196-06', 'jingzhao']['population'], 86_000)
        for key, expected in {
            'wei': {'202-06': 107_000, '207-09': 75_000, '219-07': 137_000, '263-05': 127_000},
            'yingchuan': {'196-06': 59_000, '200-01': 93_000, '219-07': 142_000, '263-05': 111_000},
            'shujun': {'194-06': 152_000, '227-02': 193_000, '263-05': 205_000},
            'danyang': {'184-02': 24_000, '212-06': 50_000, '249-01': 146_000, '263-05': 175_000},
            'bajun': {'184-02': 49_000, '227-02': 68_500, '263-05': 88_000},
            'hanzhong': {'215-08': 93_300, '219-07': 33_000, '263-05': 72_000},
            'jiujiang': {'200-01': 56_000, '249-01': 111_000, '263-05': 73_000},
            'kuaiji': {'196-06': 61_000, '197-07': 58_000, '263-05': 101_000},
            'nanjun': {'207-09': 89_000, '221-07': 83_000, '227-02': 74_000, '263-05': 104_000},
            'nanyang': {'184-02': 68_000, '198-03': 49_000, '263-05': 93_000},
            'qiao': {'200-01': 55_300, '221-07': 71_400, '263-05': 87_000},
            'wuchang': {'184-02': 29_000, '227-02': 91_000, '234-02': 79_000, '263-05': 97_000},
            'wujun': {'184-02': 64_000, '200-01': 76_000, '263-05': 109_000},
            'xiangyang': {'207-09': 112_000, '208-10': 97_000, '263-05': 111_000},
        }.items():
            for scenario, population in expected.items():
                self.assertEqual(reviewed_baselines[scenario, key]['population'], population, (scenario, key))
        for field in ('land', 'industry', 'population'):
            self.assertGreater(examples['184-02', 'shujun'][field], examples['184-02', 'wenshan'][field])


if __name__ == '__main__':
    unittest.main()
