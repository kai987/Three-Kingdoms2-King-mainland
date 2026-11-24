"""Agriculture V2 grain market settlement and its transactional boundaries."""
from copy import deepcopy
from random import Random
import unittest

from campaign_fixtures import advance_month
from remake import battle_grid, battle_services, battle_supply, city_economy, domestic
from remake import economy_rules, facilities, grain_market
from remake.campaign import Campaign
from remake.errors import GameError
import test_remake_battle_objectives as objectives
from test_remake_battle_objectives import command, place
from test_remake_facilities import fixture
from test_remake_facility_campaign import facility_catalog

CITY = 'xiangyang'


def dated_month(state):
    return 12 * state.year + state.month - 1


class GrainMarketTests(unittest.TestCase):
    def start(self, month=4, disasters=False):
        game = Campaign(facility_catalog(month=month, disasters=disasters))
        command(game, 'new', faction='shu', seed=2026)
        return game

    def test_jiangxia_supply_and_towns_reference(self):
        for town, production, monthly, capacity in ((1, 12456, 5982, 17946),
                                                     (2, 18980, 11490, 34470),
                                                     (3, 27400, 20440, 61320)):
            self.assertEqual(grain_market.supply(town, production), monthly)
            market = grain_market._restock(0, monthly, 2400)
            self.assertEqual((market['stock'], market['capacity']), (monthly, capacity))

    def test_transaction_conserves_stock_and_rejects_stale_commands(self):
        game = self.start(month=2)
        state = game.state
        city = state.cities[CITY]
        state.extension['facilities']['cities'][CITY]['town'] = 1
        market = state.extension[grain_market.FIELD]
        market[CITY] = grain_market._restock(0, 5982, dated_month(state))
        before_cities = city.gold, city.grain
        quote = facilities._trade_quote(game, state, city, 1, 'buy')
        self.assertEqual((quote['rate'], quote['max_batches']), (11, 5))
        rev = game.revision
        order = dict(city=CITY, actor=146, direction='buy', batches=5)
        command(game, 'trade_grain', **order)
        state = game.state
        city, market = state.cities[CITY], grain_market.row(state, CITY)
        self.assertEqual((city.gold, city.grain, market['stock']), (before_cities[0]-55, before_cities[1]+5000, 982))
        saved = game.export_save()
        with self.assertRaises(GameError):
            game.command('trade_grain', order, rev)
        self.assertEqual(game.export_save(), saved)
        quote = facilities._trade_quote(game, state, city, 1, 'buy')
        self.assertEqual((quote['max_batches'], quote['blocked_reason']), (0, 'market_empty'))

        actor = facilities.view(game, state)['cities'][CITY]['eligible_actors'][0]
        result = facilities.buy_emergency_grain(game, state, CITY, actor, 'shu', 2500)
        self.assertEqual((result['grain'], result['gold'], market['stock']), (982, 11, 0))
        self.assertEqual(city.grain + market['stock'], before_cities[1] + 5982)
        # The next turn makes the same personnel available. No purchase can
        # spend a command, gold or an event ID while the shared market is empty.
        state.extension['officer_actions'].pop(str(actor))
        snapshot = deepcopy(state)
        blocked = facilities.buy_emergency_grain(game, state, CITY, actor, 'shu', 2500)
        self.assertEqual(blocked['blocked_reason'], 'market_empty')
        self.assertEqual(state, snapshot)
        game.validate(state)
        restored = Campaign(game.catalog)
        restored.load_save(game.export_save(compact=True), 0)
        self.assertEqual(restored.to_dict(), game.to_dict())

    def test_restock_caps_overflow_idempotent_and_monthly_income_reused(self):
        self.assertEqual(grain_market._restock(4000, 6000, 2400)['stock'], 10000)
        self.assertEqual(grain_market._restock(17_000, 6000, 2400)['restocked'], 1000)
        self.assertEqual(grain_market._restock(19_000, 6000, 2400)['overflow'], 1000)
        game = self.start()
        state = game.state
        first = deepcopy(state.extension[grain_market.FIELD])
        grain_market.initialize(game, state)
        self.assertEqual(state.extension[grain_market.FIELD], first)
        town = state.extension['facilities']['cities'][CITY]['town']
        state.extension['facilities']['cities'][CITY]['town'] = 1
        previous = grain_market.row(state, CITY)
        previous['stock'] = previous['capacity']
        previous['sold'] = previous['capacity'] - previous['restocked']
        old_stock = previous['stock']
        state.extension['city_development']['cities'][CITY]['population'] = 1000
        state.extension['facilities']['cities'][CITY]['damage'] = 50
        income_row = state.extension['domestic']['cities'][CITY]
        income_row.update(income_points=99, income_rate_units=domestic._civil_income_units(99))
        reserve = city_economy.monthly_income(game, CITY, state)['grain']
        self.assertEqual(town, 3)
        advance_month(game)
        market = grain_market.row(game.state, CITY)
        self.assertEqual(market['monthly_supply'], grain_market.supply(1, reserve))
        self.assertEqual(market['opening_stock'], old_stock)
        self.assertEqual(market['overflow'], max(0, old_stock-market['capacity']))
        self.assertEqual(market['stock'], market['capacity'])
        snapshot = game.export_save()
        grain_market.restock(game, game.state)
        self.assertEqual(game.export_save(), snapshot)

    def test_upgrade_reprices_without_refill_and_flood_drought_change_next_supply(self):
        for month, disaster in ((5, 'flood'), (8, 'drought')):
            with self.subTest(disaster=disaster):
                game = self.start(month, disasters=True)
                state = game.state
                city = state.cities[CITY]
                facilities_before = state.extension['facilities']['cities'][CITY]
                facilities_before.update(town=1, preparedness=0)
                game.catalog.data['facility_rules'].update(flood_plain_chance=100,
                    flood_mountain_chance=100, drought_chance=100)
                market_before = deepcopy(grain_market.row(state, CITY))
                quote_before = facilities._trade_quote(game, state, city, 1, 'buy')
                command(game, 'develop_town', city=CITY, actor=146)
                state = game.state
                city = state.cities[CITY]
                quote_after = facilities._trade_quote(game, state, city, 2, 'buy')
                self.assertEqual(quote_after['rate'], quote_before['rate']-1)
                self.assertEqual(grain_market.row(state, CITY), market_before)
                predicted = city_economy.monthly_income(game, CITY, state)['grain']
                advance_month(game)
                self.assertEqual(grain_market.row(game.state, CITY)['monthly_supply'], grain_market.supply(2, predicted))
                self.assertGreater(game.state.extension['facilities']['cities'][CITY]['damage'], 0)
                next_supply = grain_market.supply(2, city_economy.monthly_income(game, CITY, game.state)['grain'])
                self.assertLess(next_supply, grain_market.row(game.state, CITY)['monthly_supply'])
                advance_month(game)
                self.assertEqual(grain_market.row(game.state, CITY)['monthly_supply'], next_supply)

    def test_city_and_coalition_battle_share_physical_inventory(self):
        game, ally, player = objectives.CoalitionBattleTests().ready()
        state, battle = game.state, game.state.battle
        site = next(row for row in battle_grid._field(battle)['services'] if row['kind'] == 'market')
        target = battle['target']
        market = state.extension[grain_market.FIELD]
        month = dated_month(state)
        market[target] = grain_market._restock(0, 10_000, month)
        # The defender buys 3,000 through the genuine city service, before
        # battle. The fixture preserves the already established battle setup.
        defender_city = state.cities[target]
        defender = battle['defenders'][0]['id']
        with_battle = battle
        faction = state.player
        state.battle, state.phase, state.player = None, 'city', defender_city.owner
        facilities.trade(game, state, dict(city=target, actor=defender, direction='buy', batches=3), defender_city.owner)
        state.battle, state.phase, state.player = with_battle, 'battle', faction
        self.assertEqual(market[target]['stock'], 7000)
        books = deepcopy(state.extension['command_books'])
        town = state.extension['facilities']['cities'][target]['town']
        rate = facilities.market_rate(game, max(2, town), 'buy', state.month, state=state)

        for ident, side, batches, pay_city in ((ally, 'attackers', 2, 'jiangxia'),
                                              (defender, 'defenders', 4, target),
                                              (player, 'attackers', 1, CITY)):
            officer = next(row for row in battle[side] if row['id'] == ident)
            place(game, officer, (site['x'], site['y']))
            battle['extended']['tactical']['side'] = side
            payer = state.cities[pay_city]
            before = payer.gold, payer.grain
            available = battle_supply.available(state, battle, side)
            quote = battle_services.quote(game, state, battle, officer, side)['trade']
            self.assertEqual(quote['market_stock'], market[target]['stock'])
            if ident == player:
                snapshot = deepcopy(state)
                with self.assertRaisesRegex(GameError, '市場'):
                    battle_services.execute(game, state,
                        dict(battle_id=battle['id'], actor=ident, action='buy_grain', batches=2), side=side)
                self.assertEqual(state, snapshot)
            result = battle_services.execute(game, state,
                dict(battle_id=battle['id'], actor=ident, action='buy_grain', batches=batches), side=side)
            event = state.extension['events']['items'][-1]
            self.assertEqual((event['city_ids'], event['details']['market_city'], event['details']['side']),
                             ([pay_city], target, side))
            self.assertEqual(payer.gold, before[0]-batches*rate)
            self.assertEqual(payer.grain, before[1])
            self.assertEqual(battle_supply.available(state, battle, side), available+batches*1000)
            self.assertEqual(result['grain'], batches*1000)
        self.assertEqual(market[target]['stock'], 0)
        self.assertEqual(books, state.extension['command_books'])
        game.validate(state)
        costs = deepcopy(market[target])
        for unit in battle['defenders']:
            unit['troops'] = 0
        state.phase, battle['outcome'] = 'result', 'victory'
        command(game, 'settle', battle_id=battle['id'])
        self.assertNotEqual(game.state.cities[target].owner, defender_city.owner)
        self.assertEqual(grain_market.row(game.state, target), costs)

    def test_neutral_markets_use_only_base_supply(self):
        game = Campaign(facility_catalog())
        command(game, 'new', faction='shu', seed=2026)
        state = game.state
        neutral = next((key for key, city in state.cities.items() if city.owner == 'neutral'), None)
        # All controlled fixture cities can be owned. Use the real Red Cliffs
        # catalog if so, rather than fabricating a neutral tax ledger.
        if neutral is None:
            from pathlib import Path
            from remake.campaign import Catalog
            game = Campaign(Catalog(Path(__file__).resolve().parents[1] / 'game/data/campaigns/208-10.json'))
            command(game, 'new', faction='shu', seed=2026)
            state = game.state
            neutral = next(key for key, city in state.cities.items() if city.owner == 'neutral')
        town = city_economy.town_level(game, state, neutral)
        self.assertEqual(grain_market.row(state, neutral)['stock'], (1000, 2000, 4000)[town-1])

    def test_1200_seeded_market_transactions_and_rollover_conserve_resources(self):
        rng = Random(8902)
        for index in range(1200):
            game, state = fixture()
            state.extension[economy_rules.FIELD] = economy_rules.CURRENT
            city = state.cities['capital']
            town = state.extension['facilities']['cities']['capital']['town'] = rng.randrange(1, 4)
            state.month = rng.randrange(1, 13)
            remaining, monthly = rng.randrange(50_000), rng.randrange(1000, 20_000)
            market = grain_market._restock(remaining, monthly, dated_month(state))
            state.extension[grain_market.FIELD] = {key: grain_market._restock(0, 1000, dated_month(state))
                for key in state.cities}
            state.extension[grain_market.FIELD][city.id] = market
            grain_market.validate(state)
            self.assertEqual(market, grain_market._restock(remaining, monthly, dated_month(state)))
            city.gold = rng.choice((0, 60, 4000, 100_000_000))
            city.grain = rng.choice((500, 3000, 10_000, 100_000_000))
            direction = 'buy' if index % 2 else 'sell'
            quote = facilities._trade_quote(game, state, city, town, direction)
            rate = quote['rate']
            if direction == 'buy':
                maximum = min(city.gold//rate, (facilities.LIMIT-city.grain)//1000, market['stock']//1000)
            else:
                maximum = min(city.grain//1000, (facilities.LIMIT-city.gold)//rate,
                              (market['capacity']-market['stock'])//1000)
            self.assertEqual(quote['max_batches'], maximum)
            gold_before, food_before = city.gold, city.grain + market['stock']
            count = rng.randint(1, maximum) if maximum else 1
            order = dict(city=city.id, actor=2, direction=direction, batches=count)
            if not maximum:
                snapshot = deepcopy(state)
                with self.assertRaises(GameError):
                    facilities.trade(game, state, order, city.owner)
                self.assertEqual(state, snapshot)
            else:
                facilities.trade(game, state, order, city.owner)
                self.assertEqual(city.grain + market['stock'], food_before)
                self.assertEqual(city.gold, gold_before + count*rate*(1 if direction == 'sell' else -1))
            grain_market.validate(state)


if __name__ == '__main__':
    unittest.main()
