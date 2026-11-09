"""Committed diplomacy through normal campaign commands and saved state."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from remake import battle_grid, command_books, diplomacy, historical_campaigns, logistics, observer, treasures
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from campaign_fixtures import controlled_catalog, confirm_default_placement
from test_remake_battle_objectives import place as place_battle_unit


def diplomacy_catalog(*, with_convoy=False, configure=None):
    data = deepcopy(controlled_catalog().data)
    data['id'] = 'controlled-diplomacy'
    data['rules']['ai_max_attacks_per_turn'] = 1
    data['active_cities'] += ['yingchuan', 'runan']
    data['initial_owners'].update(nanjun='wu', jiangxia='shu', yingchuan='shu', runan='shu')
    for faction in data['factions']:
        if faction['id'] in {'shu', 'wu'}:
            faction['city'] = 'jiangxia' if faction['id'] == 'shu' else 'nanjun'
    officers = data['initial_officers']
    officers[1]['city'] = 'jiangxia'
    officers[5].update(city='nanjun', troops=6000)
    if with_convoy:
        data['active_cities'].append('yuzhang')
        data['initial_owners'].update(nanjun='wei', yuzhang='wu')
        next(f for f in data['factions'] if f['id'] == 'wu')['city'] = 'yuzhang'
        officers[5]['city'] = 'yuzhang'
    for row in officers:
        data['appearance_locations'][row['person_id']] = row['city']
    for city in data['active_cities']:
        data['initial_city_resources'][city] = dict(gold=2000, grain=6000, reserves=1200)
        data['city_income'][city] = dict(gold=0, grain=0, reserves=0)
    if with_convoy:
        data['initial_city_resources']['runan']['reserves'] = 2200
    for a, b in [('nanjun', 'nanyang'), ('jiangxia', 'yingchuan'), ('yingchuan', 'runan')]:
        data['links'].append([a, b])
        data['travel_routes'].append(dict(id=f'diplomacy:{a}:{b}', **{'from':a,'to':b},
            mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1))
    if configure is not None:
        configure(data)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'diplomacy.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class DiplomacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = diplomacy_catalog()

    def start(self, faction='shu'):
        game = Campaign(self.catalog)
        game.command('new', dict(faction=faction, seed=2026), 0)
        return game

    def order(self, game, action, target='wei', city='xiangyang', envoy=None, **extra):
        if envoy is None:
            envoy = next(i for i in game.state.cities[city].roster.officer_ids
                         if game.state.extension['officer_actions'].get(str(i)) != game.state.turn)
        return game.command('diplomacy', dict(action=action, city=city, envoy=envoy, target=target, **extra),
                            game.revision)

    def target(self, game, faction):
        return next(row for row in game.view()['catalog']['diplomacy']['targets'] if row['id'] == faction)

    def test_goodwill_transfers_each_gift_and_rejects_invalid_amount_atomically(self):
        self.assertEqual([diplomacy.stage(score) for score in (100, 65, 50, 35, 20, 0)],
                         ['intimate', 'friendly', 'normal', 'discord', 'hostile', 'hateful'])
        for resource, amount in [('gold', 1800), ('grain', 5800), ('treasure', 2)]:
            with self.subTest(resource=resource):
                game = self.start()
                if resource == 'treasure':
                    self.assertGreaterEqual(treasures.count(game.state, 'xiangyang'), amount)
                    stock = lambda city: treasures.count(game.state, city)
                else:
                    stock = lambda city: getattr(game.state.cities[city], resource)
                before = {city:stock(city) for city in game.state.cities}
                saved = game.export_save()
                orders = command_books.remaining(game.state, 'shu')
                with self.assertRaises(GameError):
                    self.order(game, 'goodwill', resource=resource, amount=20001)
                self.assertEqual(game.export_save(), saved)
                self.order(game, 'goodwill', resource=resource, amount=amount)
                self.assertEqual(stock('xiangyang'), before['xiangyang']-amount)
                self.assertEqual(stock('nanyang'), before['nanyang']+amount)
                self.assertEqual(sum(stock(city) for city in before), sum(before.values()))
                self.assertEqual(command_books.remaining(game.state, 'shu'), orders-1)
                score = diplomacy.relation(game.state, 'shu', 'wei')
                self.assertGreater(score, 50)
                self.assertEqual(score, diplomacy.relation(game.state, 'wei', 'shu'))
                self.assertEqual(self.target(game, 'wei')['score'], score)
                self.assertEqual(game.state.rng.draws, saved['state']['rng']['draws'])

    def test_treaty_protects_attacks_allows_transit_and_expires_after_72_turns(self):
        game = self.start()
        self.assertIsNone(game._travel_path(game.state, 'xiangyang', 'jiangxia', 'shu', 'land'))
        self.order(game, 'alliance', target='wu', duration=72)
        self.assertTrue(historical_campaigns.allied(game.state, 'wu', 'shu'))
        self.assertEqual(self.target(game, 'wu')['alliance'], {'historical':False, 'turns':72})
        save = game.export_save()
        loaded = Campaign(game.catalog)
        loaded.load_save(save, 0)
        self.assertEqual(loaded.export_save(), save)
        game = loaded
        quote = game._travel_path(game.state, 'xiangyang', 'jiangxia', 'shu', 'land')
        self.assertEqual(quote['path'], ['xiangyang', 'nanjun', 'jiangxia'])
        ids = game.state.cities['xiangyang'].roster.officer_ids
        available = [i for i in ids if game.state.extension['officer_actions'].get(str(i)) != game.state.turn]
        with self.assertRaisesRegex(GameError, '同盟'):
            game.command('depart', dict(source='xiangyang', target='nanjun', officers=available[:1]),
                         game.revision)
        self.assertEqual(game.export_save(), save)
        game.command('transfer', dict(source='xiangyang', target='jiangxia', officers=available[:1],
                                     route_mode='land'), game.revision)
        game._complete_turn(game.state)
        game.command('arrivals', {}, game.revision)
        self.assertIn(available[0], game.state.cities['jiangxia'].roster.officer_ids)
        self.assertEqual(game.state.cities['nanjun'].owner, 'wu')
        for _ in range(70):
            game._complete_turn(game.state)
        self.assertEqual(game.state.turn, 72)
        self.assertTrue(historical_campaigns.allied(game.state, 'shu', 'wu'))
        game.command('end_turn', {}, game.revision)
        game.command('ai', dict(turn=game.state.turn), game.revision)
        self.assertEqual(game.state.turn, 73)
        self.assertFalse(historical_campaigns.allied(game.state, 'shu', 'wu'))
        self.assertIsNone(game._travel_path(game.state, 'xiangyang', 'jiangxia', 'shu', 'land'))
        game.validate(game.state)

    def test_battle_settlement_captures_and_diplomacy_returns_an_officer(self):
        game = self.start()
        self.order(game, 'goodwill', city='jiangxia', resource='gold', amount=1800)
        source, target = (game.state.cities[key] for key in ('nanyang', 'xiangyang'))
        prisoner = target.roster.officer_ids[0]
        game._start_expanded_battle(game.state, source, target, source.roster.officer_ids[:1],
                                    manual_deployment=True)
        confirm_default_placement(game)
        battle = game.state.battle
        camp_x, camp_y = battle_grid._field(battle)['camp']
        # Control the late tactical positions, then let the real AI capture
        # the unoccupied fortress after the defending player's command.
        camp = {'x':camp_x,'y':camp_y}
        positions = battle['extended']['tactical']['positions']
        for unit in battle['defenders']:
            if positions[str(unit['id'])] == camp:
                place_battle_unit(game, unit, (0, 18))
        place_battle_unit(game, battle['attackers'][0], (camp_x-1, camp_y))
        game.command('battle_wait', dict(battle_id=battle['id']), game.revision)
        self.assertEqual(game.state.battle['outcome'], 'victory')
        self.assertIn('occupation', game.state.battle['extended'])
        game.command('settle', dict(battle_id=battle['id']), game.revision)
        self.assertEqual(game.state.cities['xiangyang'].owner, 'wei')
        officer = game.state.officers[prisoner]
        self.assertEqual((officer.faction_id, officer.troops), (None, 0))
        captive = game.state.extension['diplomacy']['prisoners'][str(prisoner)]
        self.assertEqual((captive['origin'], captive['captor'], captive['city']), ('shu', 'wei', 'xiangyang'))
        self.assertNotIn(str(prisoner), game.state.extension['free_locations'])
        self.assertEqual(next(row for row in game.view()['catalog']['library'] if row['id']==prisoner)['prisoner'], captive)
        game._complete_turn(game.state)
        self.assertIn(prisoner, [row['id'] for row in self.target(game, 'wei')['captives']])
        self.order(game, 'return_captives', city='jiangxia', prisoner=prisoner)
        self.assertIn(prisoner, game.state.cities['jiangxia'].roster.officer_ids)
        self.assertEqual(game.state.officers[prisoner].faction_id, 'shu')
        self.assertNotIn(str(prisoner), game.state.extension['diplomacy']['prisoners'])
        self.assertNotIn('prisoner', next(row for row in game.view()['catalog']['library'] if row['id']==prisoner))
        game.validate(game.state)

    def test_attack_request_dispatches_a_real_allied_march(self):
        game = self.start()
        self.order(game, 'goodwill', target='wu', resource='gold', amount=1800)
        self.order(game, 'alliance', target='wu', duration=12)
        self.assertIn('nanyang', self.target(game, 'wu')['attack_cities'])
        self.order(game, 'request_attack', target='wu', attack_city='nanyang')
        self.assertEqual(diplomacy.requested_target(game.state, 'wu'), 'nanyang')
        self.assertEqual(game.state.extension['travel']['marches'], [])
        game.command('end_turn', {}, game.revision)
        game.command('ai', dict(turn=game.state.turn), game.revision)
        march, = [row for row in game.state.extension['travel']['marches']
                  if row['owner']=='wu' and row['kind']=='attack' and row['target']=='nanyang']
        self.assertEqual(march['source'], 'nanjun')
        self.assertGreater(march['arrival_turn'], march['departure_turn'])
        self.assertIsNone(diplomacy.requested_target(game.state, 'wu'))
        game.validate(game.state)

    def test_surrender_preserves_city_resources_and_soldiers(self):
        game = self.start()
        def stocks():
            return {key:(city.gold,city.grain,city.reserves,treasures.count(game.state,key))
                    for key,city in game.state.cities.items()}
        initial_stocks = stocks()
        initial_soldiers = deepcopy(game.state.soldiers)
        garrison = list(game.state.cities['nanyang'].roster.officer_ids)
        self.assertTrue(self.target(game, 'wei')['actions']['surrender'])
        self.order(game, 'surrender')
        self.assertEqual(game.state.cities['nanyang'].owner, 'shu')
        self.assertEqual(game.state.cities['nanyang'].roster.officer_ids, garrison)
        self.assertTrue(all(game.state.officers[i].faction_id=='shu' for i in garrison))
        self.assertIn('wei', game.state.extension['ended_factions'])
        self.assertEqual(stocks(), initial_stocks)
        self.assertEqual(game.state.soldiers, initial_soldiers)

    def test_surrender_accounts_for_march_rations_and_convoy_cargo(self):
        game = Campaign(diplomacy_catalog(with_convoy=True))
        game.command('new', dict(faction='shu', seed=2026), 0)
        self.order(game, 'goodwill', city='jiangxia', resource='gold', amount=1800)

        def stocks():
            return {key: (city.gold, city.grain, city.reserves, treasures.count(game.state, key))
                    for key, city in game.state.cities.items()}

        initial_stocks = stocks()
        initial_soldiers = deepcopy(game.state.soldiers)
        state = game.state
        capital, origin, target = (state.cities[key] for key in ('nanyang', 'nanjun', 'xiangyang'))
        attacker = capital.roster.officer_ids[0]
        escort = origin.roster.officer_ids[0]
        game._queue_march(state, capital, target, [attacker], 'attack', mode='land')
        logistics.set_policy(game, state, dict(city=origin.id, policy=dict(reserve_officers=0)), 'wei')
        convoy = logistics.dispatch(game, state, dict(source=origin.id, target=capital.id,
            officers=[escort], cargo=dict(gold=100, grain=200, reserves=300, treasure=1), route_mode='land'), 'wei')
        self.assertGreater(state.extension['travel']['marches'][0]['supply']['remaining'], 0)
        self.assertGreater(convoy['journeys'][0]['supply']['remaining'], 0)
        self.assertEqual(convoy['cargo'], dict(gold=100, grain=200, reserves=300, treasure=1))
        treasures.synchronize(game, state)
        game.validate(state)
        self.assertTrue(self.target(game, 'wei')['actions']['surrender'])

        self.order(game, 'surrender')
        state = game.state
        self.assertEqual(stocks(), initial_stocks)
        self.assertEqual(state.soldiers, initial_soldiers)
        self.assertEqual(state.extension['travel']['marches'], [])
        self.assertEqual(state.extension['logistics']['convoys'], [])
        for ident, city in ((attacker, 'nanyang'), (escort, 'nanjun')):
            self.assertEqual(state.officers[ident].faction_id, 'shu')
            self.assertIn(ident, state.cities[city].roster.officer_ids)
        game.validate(state)

    def test_existing_save_without_diplomacy_remains_usable(self):
        game = self.start()
        save = game.export_save()
        save.pop('checksum')
        save['state']['extension'].pop('diplomacy', None)
        save['checksum'] = digest(save)
        restored = Campaign(game.catalog)
        restored.load_save(save, 0)
        self.assertEqual(restored.export_save(), save)
        self.assertEqual(self.target(restored, 'wei')['stage'], 'normal')
        self.order(restored, 'alliance', duration=3)
        self.assertTrue(historical_campaigns.allied(restored.state, 'shu', 'wei'))


class ObserverDiplomacyTests(unittest.TestCase):
    @staticmethod
    def no_departures(data):
        data['rules']['ai_max_attacks_per_turn'] = 0

    def start(self, *, configure=None, faction=observer.SEAT):
        game = Campaign(diplomacy_catalog(configure=configure))
        game.command('new', dict(faction=faction, seed=2026), 0)
        return game

    def events(self, game, action=None, factions=None):
        return [row for row in game.state.extension['events']['items']
                if row['kind'] == 'diplomacy_result'
                and (action is None or row['details']['action'] == action)
                and (factions is None or set(row['factions']) == set(factions))]

    def advance(self, game):
        turn = game.state.turn
        snapshot = {}
        complete_turn = game._complete_turn

        def complete_with_receipts(state):
            snapshot.update(
                orders=deepcopy(state.extension['command_books']['factions']),
                officer_actions=dict(state.extension['officer_actions']))
            complete_turn(state)

        # Read the existing receipt immediately before the normal turn refresh.
        with patch.object(game, '_complete_turn', side_effect=complete_with_receipts):
            game.command('observe_turn', {}, game.revision)
        self.assertEqual(game.state.turn, turn + 1)
        self.assertEqual(game.state.completed_ai_turns[-1], turn)
        self.assertIn(game.state.phase, ('city', 'finished'))
        self.assertIsNone(game.state.battle)
        events = [row for row in self.events(game) if row['turn'] == turn]
        self.assertTrue(all(row['audience'] == 'world' for row in events))
        self.assertEqual(len(events), len({row['factions'][0] for row in events}))
        for event in events:
            owner, _ = event['factions']
            self.assertIn(dict(city=event['city_ids'][0], kind='diplomacy', cost=1),
                          snapshot['orders'][owner]['orders'])
            envoy = next(i for i, o in game.state.officers.items() if o.person_id == event['person_ids'][0])
            self.assertEqual(snapshot['officer_actions'][str(envoy)], turn)
        return snapshot

    def reach_surrender_pressure(self, game):
        for _ in range(3):
            if game.state.player == observer.SEAT:
                self.advance(game)
            else:
                game.command('end_turn', {}, game.revision)
                game.command('ai', dict(turn=game.state.turn), game.revision)
        self.assertEqual(game.state.cities['nanyang'].owner, 'wei')
        diplomacy._pool(game.state)['relations']['shu|wei'] = 38

    def test_observer_replays_goodwill_and_a_finite_defensive_alliance(self):
        def configure(data):
            self.no_departures(data)
            for row in data['initial_officers']:
                if row['person_id'] == 'san14-candidate-0147':
                    row['troops'] = 8000
            # Both neighbors can benefit from coordination without meeting the
            # shared surrender ratio against a one-city faction.
            for city in ('nanyang', 'nanjun'):
                data['initial_city_resources'][city]['reserves'] = 6000
        game = self.start(configure=configure)
        self.assertEqual(diplomacy.alliances(game.state), [])
        saved = game.export_save()
        restored = Campaign(game.catalog)
        restored.load_save(saved, 0)
        for _ in range(3):
            self.advance(game)
            restored.command('observe_turn', {}, restored.revision)
            self.assertEqual(restored.export_save(), game.export_save())
            if self.events(game, 'alliance'):
                break
        alliance = self.events(game, 'alliance')[0]
        pair = alliance['factions']
        goodwill = self.events(game, 'goodwill', pair)
        self.assertTrue(goodwill)
        self.assertGreater(goodwill[0]['details']['score'], 50)
        self.assertLess(goodwill[0]['id'], alliance['id'])
        self.assertTrue(alliance['details']['success'])
        duration = alliance['details']['duration']
        self.assertGreaterEqual(duration, 1)
        self.assertLessEqual(duration, diplomacy.MAX_TURNS)
        self.assertEqual(diplomacy.expiry(game.state, *pair), alliance['turn'] + duration)

    def test_observer_ai_returns_a_captive_using_shared_officer_and_order_receipts(self):
        game = self.start(configure=self.no_departures)
        city = game.state.cities['xiangyang']
        prisoner = next(i for i in city.roster.officer_ids if i != game.state.extension['leaders']['shu'])
        officer = game.state.officers[prisoner]
        city.reserves += officer.troops
        city.roster.officer_ids.remove(prisoner)
        officer.troops = 0
        officer.faction_id = None
        self.assertTrue(diplomacy.capture(game.state, officer, city='nanyang', captor='wei', origin='shu'))
        treasures.synchronize(game, game.state)
        game.validate(game.state)
        self.advance(game)
        returned, = self.events(game, 'return_captives', ('shu', 'wei'))
        self.assertEqual(returned['factions'], ['shu', 'wei'])
        self.assertTrue(returned['details']['success'])
        self.assertEqual(returned['person_ids'][-1], officer.person_id)
        self.assertNotIn(str(prisoner), game.state.extension['diplomacy']['prisoners'])
        self.assertEqual(game.state.officers[prisoner].faction_id, 'shu')
        self.assertTrue(any(c.owner == 'shu' and prisoner in c.roster.officer_ids
                            for c in game.state.cities.values()))

    def test_observer_ai_asks_an_ally_to_launch_a_real_attack(self):
        def configure(data):
            data['initial_city_resources']['nanyang']['reserves'] = 4000
        game = self.start(configure=configure)
        # Stage a previously signed pact so the real AI turn makes the request.
        diplomatic = diplomacy._pool(game.state)
        diplomatic['relations']['shu|wu'] = diplomacy.FRIENDLY
        diplomatic['treaties']['shu|wu'] = game.state.turn + 12
        game.validate(game.state)
        self.advance(game)
        request, = self.events(game, 'request_attack', ('shu', 'wu'))
        self.assertEqual(request['factions'], ['shu', 'wu'])
        self.assertEqual(request['city_ids'][-1], 'nanyang')
        self.assertTrue(request['details']['success'])
        departure, = [row for row in game.state.extension['ai_reports']
                      if row['faction'] == 'wu' and row['city'] == 'nanjun'
                      and row['target'] == 'nanyang' and row['action'] == 'attack']
        self.assertEqual(departure['turn'], request['turn'])
        battles = [row for row in game.state.extension['events']['items']
                   if row['kind'] == 'battle_started' and row['city_ids'] == ['nanjun', 'nanyang']]
        self.assertTrue(any(row['factions'] == ['wu', 'wei'] for row in battles))
        self.assertIsNone(diplomacy.requested_target(game.state, 'wu'))

    def test_observer_ai_accepts_surrender_and_human_keeps_its_own_orders(self):
        observed = self.start(configure=self.no_departures)
        self.reach_surrender_pressure(observed)
        city = observed.state.cities['nanyang']
        roster = city.roster.officer_ids.copy()
        self.advance(observed)
        event, = self.events(observed, 'surrender', ('shu', 'wei'))
        self.assertEqual(event['factions'], ['shu', 'wei'])
        self.assertTrue(event['details']['success'])
        self.assertEqual(observed.state.cities['nanyang'].owner, 'shu')
        self.assertTrue(all(observed.state.officers[i].faction_id == 'shu' for i in roster))
        self.assertIn('wei', observed.state.extension['ended_factions'])

        game = self.start(configure=self.no_departures, faction='shu')
        self.reach_surrender_pressure(game)
        saved, revision = game.export_save(), game.revision
        with self.assertRaises(GameError):
            game.command('observe_turn', {}, revision)
        self.assertEqual(game.export_save(), saved)
        game.command('end_turn', {}, revision)
        game.command('ai', dict(turn=game.state.turn), game.revision)
        self.assertFalse(any(row['factions'][0] == 'shu' for row in self.events(game, 'surrender')))
        self.assertEqual(game.state.cities['nanyang'].owner, 'wei')

    def test_observer_rejects_manual_diplomacy_and_ai_respects_exhausted_books(self):
        game = self.start(configure=self.no_departures)
        self.reach_surrender_pressure(game)
        city = game.state.cities['xiangyang']
        payload = dict(action='surrender', city=city.id, envoy=city.roster.officer_ids[0], target='wei')
        saved, revision = game.export_save(), game.revision
        with self.assertRaises(GameError):
            game.command('diplomacy', payload, revision)
        self.assertEqual(game.revision, revision)
        self.assertEqual(game.export_save(), saved)
        while command_books.can_spend(game.state, 'shu', 'diplomacy'):
            command_books.spend(game.state, city, 'allocate')
        self.advance(game)
        self.assertFalse(any(row['factions'][0] == 'shu' for row in self.events(game, 'surrender')))
        self.assertEqual(game.state.cities['nanyang'].owner, 'wei')

    def test_observer_keeps_resources_and_orders_when_surrender_cannot_refund_grain(self):
        def configure(data):
            self.no_departures(data)
            route = next(row for row in data['travel_routes']
                         if (row['from'], row['to']) == ('nanyang', 'xiangyang'))
            route.update(distance_km=600, land_km=600, days=20)
        game = self.start(configure=configure)
        self.reach_surrender_pressure(game)
        state = game.state
        source = state.cities['nanyang']
        game._queue_march(state, source, state.cities['xiangyang'],
                          source.roster.officer_ids[:1], 'attack', 'land')
        source.grain = 100000000
        march, = state.extension['travel']['marches']
        self.assertGreater(march['arrival_turn'], state.turn + 1)
        treasures.synchronize(game, state)
        game.validate(state)
        execute = diplomacy.execute
        rejected = []

        def check_rejection(campaign, candidate, payload, owner):
            if payload['action'] != 'surrender' or owner != 'shu':
                return execute(campaign, candidate, payload, owner)
            before = campaign.to_dict(candidate)
            try:
                return execute(campaign, candidate, payload, owner)
            except GameError as error:
                self.assertIn('沒有空間收回隨軍糧', str(error))
                self.assertEqual(campaign.to_dict(candidate), before)
                rejected.append(payload)
                raise

        with patch.object(diplomacy, 'execute', side_effect=check_rejection):
            snapshot = self.advance(game)
        attempt, = rejected
        self.assertEqual(attempt['target'], 'wei')
        self.assertFalse(self.events(game, 'surrender', ('shu', 'wei')))
        self.assertNotIn('diplomacy', [row['kind'] for row in snapshot['orders']['shu']['orders']])
        self.assertNotEqual(snapshot['officer_actions'].get(str(attempt['envoy'])), state.turn)
        self.assertEqual(game.state.cities['nanyang'].owner, 'wei')
        surviving, = game.state.extension['travel']['marches']
        self.assertEqual(surviving['id'], march['id'])
        self.assertEqual(surviving['officers'], march['officers'])
        self.assertGreater(surviving['supply']['remaining'], 0)


if __name__ == '__main__':
    unittest.main()
