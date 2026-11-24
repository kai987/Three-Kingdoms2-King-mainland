"""Conquest attribution, territorial loot, and supply conservation for joint attacks."""

import unittest

from remake import battle_experience, battle_grid, battle_supply, grain_units
from remake.campaign import Campaign
from test_remake_allied_travel import _alliance, _catalog


class AlliedSettlementTests(unittest.TestCase):
    def test_contingent_that_takes_castle_gets_city_and_ally_returns_with_its_share(self):
        catalog = _catalog(shu_days=20)
        catalog.data['initial_owners']['nanjun'] = 'shu'
        catalog.data['links'].append(['nanyang', 'nanjun'])
        catalog.data['travel_routes'].append(dict(id='controlled:nanyang:nanjun', **{
            'from': 'nanyang', 'to': 'nanjun', 'mode': 'land', 'terrain': 'plain',
            'distance_km': 30, 'land_km': 30, 'sea_km': 0, 'days': 1,
        }))
        game = Campaign(catalog)
        game.command('new', {'faction': 'shu', 'seed': 2026}, 0)
        _alliance(game)
        state = game.state
        shu_home, wu_home, target, rear = (state.cities[name] for name in
                                           ('xiangyang', 'jiangxia', 'nanyang', 'nanjun'))
        shu, wu = shu_home.roster.officer_ids[0], wu_home.roster.officer_ids[0]
        shu_home.grain -= 60
        wu_home.grain -= 90
        ration_units = grain_units.denominator()
        game._start_expanded_battle(state, shu_home, target, [shu, wu], paid=True,
            march_supply=dict(remaining=150, credit_units=0),
            coalition=dict(sources={str(shu): shu_home.id, str(wu): wu_home.id},
                           provisions={'shu': 60 * ration_units, 'wu': 90 * ration_units}))
        battle = state.battle
        wu_home.grain -= 30
        battle_supply.receive(state, battle, 'attackers', 30, contributor='wu')
        defender = battle['defenders'][0]['id']
        battle['attackers'][0]['troops'] -= 11
        battle_experience.attack(battle, defender, shu, 11)
        battle['attackers'][1]['troops'] -= 7
        battle_experience.attack(battle, defender, wu, 7)
        before_xp = {i: state.officers[i].experience for i in (shu, wu, defender)}

        # Set the exact occupation reached by Wu; the living defender will be displaced.
        x, y = battle_grid._field(battle)['camp']
        positions = battle['extended']['tactical']['positions']
        for unit in battle['defenders']:
            positions[str(unit['id'])] = dict(x=30, y=18)
        positions[str(wu)] = dict(x=x, y=y)
        battle['extended']['occupation'] = dict(actor=wu, side='attackers', x=x, y=y)
        battle['outcome'], state.phase = 'victory', 'result'
        game.validate(state)
        original = game.export_save()
        restored = Campaign(catalog)
        restored.load_save(original, 0)

        troops = [battle['attackers'][1]['troops'], battle['attackers'][0]['troops']]
        stock = {'gold': target.gold, 'grain': target.grain,
                 'reserves': target.reserves + sum(u['troops'] for u in battle['defenders'])}
        contributor_share = {key: amount * troops[1] // sum(troops) for key, amount in stock.items()}
        captor_share = {key: amount - contributor_share[key] for key, amount in stock.items()}
        defender_refund = battle['extended']['supply']['sides']['defenders']['remaining']
        rear_before = (rear.gold, rear.grain, rear.reserves)
        game.command('settle', {'battle_id': battle['id']}, game.revision)
        restored.command('settle', {'battle_id': battle['id']}, restored.revision)
        self.assertEqual(game.export_save(), restored.export_save())

        state = game.state
        target, rear = state.cities['nanyang'], state.cities['nanjun']
        self.assertEqual((target.owner, target.roster.officer_ids), ('wu', [wu]))
        self.assertIn(shu, rear.roster.officer_ids)
        self.assertNotIn(shu, state.cities['xiangyang'].roster.officer_ids)
        self.assertEqual((target.gold, target.grain, target.reserves),
                         (captor_share['gold'], captor_share['grain'] + 120 + defender_refund,
                          captor_share['reserves']))
        self.assertEqual((rear.gold, rear.grain, rear.reserves),
                         (rear_before[0] + contributor_share['gold'],
                          rear_before[1] + contributor_share['grain'] + 60,
                          rear_before[2] + contributor_share['reserves']))
        event = next(event for event in reversed(state.extension['events']['items'])
                     if event['kind'] == 'battle_result')
        self.assertEqual(event['details']['coalition'],
                         dict(captor='wu', ally='shu', troops=troops,
                              shares=[captor_share, contributor_share], returns=['nanjun']))
        self.assertEqual(state.soldiers['lost'], 18)
        report = event['details']['experience']
        attackers = report['sides']['attackers']
        self.assertEqual({row['id'] for row in attackers['officers'] if row['eligible']}, {shu, wu})
        self.assertEqual(sum(row['experience'] for row in attackers['officers']), attackers['experience'])
        for ident, before in before_xp.items():
            self.assertEqual(state.officers[ident].experience, min(49_999, before + report['applied'][str(ident)] * 50))
        game.validate(state)
        settled = game.export_save()
        game.command('settle', {'battle_id': battle['id']}, game.revision)
        self.assertEqual(game.export_save(), settled)
