"""Authoritative original terrain/AP, legal paths and deterministic tactical AI."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import battle_grid as grid
from remake.campaign import SeedRng
from remake.campaign_expansion import TACTICS
from remake.errors import GameError
from remake.tactical_ai import candidates, choose_action, tactic_reason, maximum_tactic


def fixture(attackers=1, defenders=2):
    units = {side: [dict(id=i, troops=500, start=500, martial=80)
        for i in (range(1, attackers+1) if side == 'attackers' else range(101, 101+defenders))]
        for side in grid.SIDES}
    ids = [unit['id'] for side in grid.SIDES for unit in units[side]]
    state = SimpleNamespace(player='shu', phase='battle', rng=SeedRng(2026),
        officers={i: SimpleNamespace(profile=SimpleNamespace(terrain_affinity=0,
            martial_strength=80, intellect=80, virtue=80), loyalty=80,
            person_id='san14-candidate-0440', tier=6) for i in ids},
        cities={'test-source': SimpleNamespace(grain=1000), 'test-target': SimpleNamespace(grain=1000)})
    game = SimpleNamespace(catalog=SimpleNamespace(map_cities={'test-target': {'terrain': 'water'}}))
    battle = dict(id='battle-1', target='test-target', source='test-source', attacker='shu', defender='wei',
        round=1, used=[], outcome=None, **units,
        extended=dict(support={str(i): dict(health=80, energy=0, guard=0, stunned=0) for i in ids},
            duel=None, surrenders={}, ambush=None))
    grid.initialize(game, state, battle)
    return game, state, battle


def plain():
    return dict(classes=[[2]*grid.COLUMNS for _ in range(grid.ROWS)], camp=(28, 9))


def position(battle, ident, x, y):
    battle['extended']['tactical']['positions'][str(ident)] = dict(x=x, y=y)


class BattleGridTests(unittest.TestCase):
    def test_all_thirty_original_grids_and_all_city_bindings_are_reused(self):
        maps, cities = grid._library()
        self.assertEqual(len(maps), 30)
        self.assertEqual(len(cities), 115)
        self.assertEqual(grid.field_id('test-target'), 'original-09')
        self.assertEqual(grid.field_id('shujun'), cities['shujun'])
        for row in maps.values():
            self.assertEqual((len(row['classes'][0]), len(row['classes'])), (31, 19))
            self.assertTrue(set(cell for line in row['classes'] for cell in line) <= set(range(6)))

    def test_native_shared_point_table_boundaries_and_caps(self):
        self.assertEqual([grid.daily_points(i*1000) for i in range(10)], list(grid.DAILY_POINTS))
        self.assertEqual([grid.point_cap(i*1000) for i in range(10)], list(grid.POINT_CAPS))
        self.assertEqual((grid.daily_points(999), grid.daily_points(1000)), (10, 16))
        self.assertEqual((grid.daily_points(9990), grid.point_cap(9990)), (42, 60))
        self.assertEqual((grid.daily_points(10000),grid.point_cap(20000)),(42,60))
        for bad in (-1, True, '1000', 20001):
            with self.assertRaises(ValueError):
                grid.daily_points(bad)

    def test_all_affinities_use_native_599_600_boundary_and_positive_costs(self):
        _, state, battle = fixture()
        actor = battle['attackers'][0]
        # Isolate all three raw cost rows from the fixture's historical
        # Zhuge Liang identity, whose verified original type now wins.
        state.officers[actor['id']].person_id='controlled-cost-table'
        expected = [((2, 3, 1, 3, 3, 4), (3, 4, 2, 5, 5, 6)),
                    ((3, 3, 2, 5, 2, 4), (5, 4, 3, 6, 3, 6)),
                    ((3, 3, 2, 2, 4, 4), (5, 4, 3, 3, 6, 6))]
        for affinity, rows in enumerate(expected):
            state.officers[actor['id']].profile.terrain_affinity = affinity
            for troops, row in zip((599, 600), rows):
                actor['troops'] = troops
                self.assertEqual(tuple(grid.movement_cost(state, actor, c) for c in range(6)), row)
                self.assertTrue(all(cost > 0 for cost in row), 'Water and mountains are costly, not impassable')

    def test_deployment_is_distinct_camp_first_and_rng_free(self):
        game, state, battle = fixture(10, 10)
        before_rng = deepcopy(vars(state.rng))
        first = deepcopy(battle['extended']['tactical'])
        grid.initialize(game, state, battle)
        self.assertEqual(battle['extended']['tactical'], first)
        self.assertEqual(vars(state.rng), before_rng)
        self.assertEqual(len({(p['x'], p['y']) for p in first['positions'].values()}), 20)
        camp = grid._field(battle)['camp']
        self.assertEqual(first['positions']['101'], dict(zip(('x', 'y'), camp)))
        grid.validate(game, state, battle)

    def test_dijkstra_uses_cheaper_real_terrain_not_screen_or_manhattan_cost(self):
        game, state, battle = fixture()
        state.officers[1].person_id='controlled-plain-path'
        position(battle, 1, 1, 1)
        position(battle, 101, 20, 10)
        position(battle, 102, 21, 10)
        field = plain()
        field['classes'][1][2:4] = [3, 3]
        before = deepcopy((battle, vars(state.rng)))
        with patch.object(grid, '_field', return_value=field):
            quote = grid.move_quote(game, state, battle, 1, 4, 1)
            self.assertEqual(quote['cost'], 5)
            self.assertEqual(quote, grid.move_quote(game, state, battle, 1, 4, 1))
            self.assertTrue(all(abs(a['x']-b['x'])+abs(a['y']-b['y']) == 1
                for a, b in zip(quote['path'], quote['path'][1:])))
            self.assertFalse(any(point in (dict(x=2, y=1), dict(x=3, y=1)) for point in quote['path']))
        self.assertEqual((battle, vars(state.rng)), before)

    def test_invalid_destinations_and_exhaustion_reject_without_any_mutation(self):
        game, state, battle = fixture()
        position(battle, 1, 1, 1)
        position(battle, 101, 2, 1)
        with patch.object(grid, '_field', return_value=plain()):
            for x, y in ((-1, 0), (31, 0), (0, 19), (True, 1), (1, 1), (2, 1)):
                before = deepcopy(battle)
                with self.assertRaises(GameError):
                    grid.move(game, state, battle, 1, x, y)
                self.assertEqual(battle, before)
            battle['extended']['tactical']['points']['attackers'] = 0
            before = deepcopy(battle)
            with self.assertRaises(GameError):
                grid.move(game, state, battle, 1, 1, 2)
            self.assertEqual(battle, before)

    def test_same_unit_moves_repeatedly_then_attacks_using_shared_points(self):
        game, state, battle = fixture()
        state.officers[1].person_id='controlled-plain-repeat'
        position(battle, 1, 1, 1)
        position(battle, 101, 4, 1)
        with patch.object(grid, '_field', return_value=plain()):
            grid.move(game, state, battle, 1, 2, 1)
            battle['used'] = [1]  # Activity receipts do not lock a tactical unit.
            grid.move(game, state, battle, 1, 3, 1)
        self.assertEqual(battle['extended']['tactical']['points']['attackers'], 8)
        self.assertEqual(grid.attack_reason(battle, 1, 101, 'attackers'), '')
        grid.spend(battle, 'attackers', grid.ATTACK_COST)
        self.assertEqual(battle['extended']['tactical']['points']['attackers'], 6)
        self.assertEqual(state.rng.draws, 0)

    def test_contact_is_four_neighbors_and_wrong_side_cannot_act(self):
        _, _, battle = fixture()
        position(battle, 1, 5, 5)
        for x, y, legal in ((6, 5, True), (5, 6, True), (6, 6, False), (8, 5, False)):
            position(battle, 101, x, y)
            self.assertEqual(not bool(grid.attack_reason(battle, 1, 101, 'attackers')), legal)
        position(battle, 101, 6, 5)
        battle['extended']['tactical']['side'] = 'defenders'
        self.assertTrue(grid.attack_reason(battle, 1, 101, 'attackers'))

    def test_passes_carry_points_once_both_sides_finish_one_battle_day(self):
        _, state, battle = fixture()
        row = battle['extended']['tactical']
        row['points'].update(attackers=19, defenders=25)
        first = grid.end_side(state, battle)
        self.assertFalse(first['advanced_day'])
        self.assertEqual((row['side'], battle['round']), ('defenders', 1))
        second = grid.end_side(state, battle)
        self.assertTrue(second['advanced_day'])
        self.assertEqual((row['side'], battle['round']), ('attackers', 2))
        self.assertEqual(row['points'], dict(attackers=20, defenders=26))
        self.assertEqual(row['passed'], dict(attackers=False, defenders=False))
        battle['round'] = 30
        grid.end_side(state, battle)
        self.assertTrue(grid.end_side(state, battle)['timed_out'])

    def test_routed_and_surrendered_units_release_cells_and_overlap_is_live_only(self):
        game, state, battle = fixture()
        position(battle, 1, 1, 1)
        position(battle, 101, 2, 1)
        target = battle['defenders'][0]
        target['troops'] = 0
        battle['extended']['surrenders']['101'] = 500
        with patch.object(grid, '_field', return_value=plain()):
            grid.move(game, state, battle, 1, 2, 1)
        grid.validate(game, state, battle)
        target['troops'] = 500
        battle['extended']['surrenders'].clear()
        with self.assertRaises(ValueError):
            grid.validate(game, state, battle)

    def test_all_sixteen_real_tile_qualifiers_ignore_obsolete_personal_energy(self):
        game, state, battle = fixture()
        actor, target = battle['attackers'][0], battle['defenders'][0]
        for tid, tactic in enumerate(TACTICS):
            with self.subTest(tactic=tid):
                position(battle, 1, 5, 5)
                position(battle, 101, 6, 5)
                position(battle, 102, 7, 5)
                field = plain()
                battle['extended']['tactical']['points']['attackers'] = 20
                if tid in (0, 1, 2, 3, 7):
                    field['classes'][5][6] = 0
                if tid in (4, 10, 12):
                    field['classes'][5][6] = field['classes'][5][7] = 3
                if tid == 6:
                    field['classes'][5][6] = 5
                if tid == 9:
                    field['classes'][5][5] = 4
                if tid == 11:
                    field['classes'][5][5] = 0
                if tid == 13:
                    field['classes'][5][5] = 5
                with patch.object(grid, '_field', return_value=field):
                    self.assertEqual(tactic_reason(state, battle, actor, target, 'attackers', 'defenders',
                        'water', tactic), '')
                battle['extended']['tactical']['points']['attackers'] = grid.TACTIC_COSTS[tid]-1
                self.assertTrue(grid.tactic_range_reason(battle, actor, target, tid))

    def test_learnability_uses_original_intellect_bands_and_only_explicit_special_people(self):
        _, state, _ = fixture()
        officer = state.officers[1]
        officer.person_id = 'unlisted-high-intellect'
        for intellect, expected in ((0, 1), (39, 1), (40, 3), (59, 3), (60, 5),
                                     (74, 5), (75, 7), (84, 7), (85, 9), (99, 9)):
            officer.profile.intellect = intellect
            self.assertEqual(maximum_tactic(officer), expected)
        officer.profile.intellect = 20
        for person, tiers in (
            ('san14-candidate-0689', [(2, 1), (3, 11), (7, 11)]),
            ('san14-candidate-0095', [(3, 11), (4, 13), (7, 13)]),
            ('san14-candidate-0828', [(3, 11), (4, 13), (5, 14), (7, 14)]),
            ('san14-candidate-0440', [(3, 11), (4, 13), (5, 14), (6, 15), (7, 15)]),
        ):
            officer.person_id = person
            for tier, expected in tiers:
                officer.tier = tier
                self.assertEqual(maximum_tactic(officer), expected, (person, tier))

    def test_saved_point_ceiling_uses_opening_army_not_reduced_live_troops(self):
        game, state, battle = fixture(attackers=3)
        row = battle['extended']['tactical']
        self.assertEqual(grid.point_cap(sum(unit['start'] for unit in battle['attackers'])), 26)
        row['points']['attackers'] = 26
        for unit in battle['attackers']:
            unit['troops'] = 1
        grid.validate(game, state, battle)
        row['points']['attackers'] = 27
        with self.assertRaisesRegex(ValueError, 'opening army cap'):
            grid.validate(game, state, battle)

    def test_cross_and_connected_area_use_exact_spatial_order_and_camp_barriers(self):
        _, _, battle = fixture(defenders=7)
        for ident, point in [(101, (5, 5)), (102, (4, 5)), (103, (6, 5)), (104, (5, 4)),
                             (105, (5, 6)), (106, (7, 5)), (107, (5, 7))]:
            position(battle, ident, *point)
        field = plain()
        for x, y in ((5, 5), (4, 5), (5, 4), (7, 5), (5, 7)):
            field['classes'][y][x] = 3
        field['classes'][6][5] = 5
        with patch.object(grid, '_field', return_value=field):
            ids = lambda tid: [u['id'] for u in grid.affected_units(battle, 101, tid, 'defenders')]
            self.assertEqual(ids(7), [101, 102, 103, 104, 105])
            self.assertEqual(ids(10), [101, 102, 104, 106])
            self.assertEqual(ids(12), [101, 102, 104, 106])
            self.assertEqual(ids(14), [101, 103, 102, 104, 106])
            self.assertEqual(ids(13), [101])

    def test_modern_ai_moves_to_contact_then_reuses_actor_and_waits_when_exhausted(self):
        game, state, battle = fixture(defenders=1)
        state.officers[1].person_id='controlled-plain-ai-path'
        position(battle, 1, 1, 1)
        position(battle, 101, 8, 1)
        battle['extended']['tactical']['points']['attackers'] = 8
        before = deepcopy((battle, vars(state.rng)))
        with patch.object(grid, '_field', return_value=plain()):
            choice = choose_action(state, battle, 'attackers', 'defenders', 'plain', TACTICS,
                settings={'tactic_depth': 0})
            self.assertEqual(choice['kind'], 'move')
            self.assertEqual((battle, vars(state.rng)), before)
            self.assertEqual(choice, choose_action(state, battle, 'attackers', 'defenders', 'plain', TACTICS,
                settings={'tactic_depth': 0}))
            grid.move(game, state, battle, choice['actor'], choice['x'], choice['y'])
            battle['used'] = [1]
            next_choice = choose_action(state, battle, 'attackers', 'defenders', 'plain', TACTICS,
                settings={'tactic_depth': 0})
            self.assertEqual((next_choice['kind'], next_choice['actor']), ('attack', 1))
            grid.spend(battle, 'attackers', 2)
            self.assertEqual(choose_action(state, battle, 'attackers', 'defenders', 'plain', TACTICS)['kind'], 'wait')
        self.assertEqual(state.rng.draws, 0)

    def test_guard_score_excludes_remote_armies_and_danger_to_another_friendly_unit(self):
        _, state, battle = fixture(defenders=2)
        position(battle, 1, 5, 5)
        position(battle, 101, 9, 5)
        position(battle, 102, 20, 10)
        battle['defenders'][0]['troops'] = 1
        battle['defenders'][1].update(troops=999, start=999)
        before = deepcopy((battle, vars(state.rng)))
        with patch.object(grid, '_field', return_value=plain()):
            rows = candidates(state, battle, 'attackers', 'defenders', 'plain', TACTICS, depth=2)
            guard = next(row for row in rows if row['actor'] == 1 and row['tactic'] == 15)
            self.assertLessEqual(guard['score'], 0)
            choice = choose_action(state, battle, 'attackers', 'defenders', 'plain', TACTICS,
                                   settings={'tactic_depth': 2})
            self.assertNotEqual(choice['tactic'], 15)
        self.assertEqual((battle, vars(state.rng)), before)
        _, state, battle = fixture(attackers=2, defenders=1)
        position(battle, 1, 5, 5)
        position(battle, 2, 10, 5)
        position(battle, 101, 9, 5)
        with patch.object(grid, '_field', return_value=plain()):
            rows = candidates(state, battle, 'attackers', 'defenders', 'plain', TACTICS, depth=2)
        self.assertLessEqual(next(row['score'] for row in rows if row['actor'] == 1 and row['tactic'] == 15), 0)
        self.assertGreater(next(row['score'] for row in rows if row['actor'] == 2 and row['tactic'] == 15), 0)

    def test_view_is_read_only_and_exposes_authoritative_targets_not_client_geometry(self):
        game, state, battle = fixture(defenders=1)
        position(battle, 1, 5, 5)
        position(battle, 101, 6, 5)
        before = deepcopy((battle, vars(state.rng)))
        with patch.object(grid, '_field', return_value=plain()):
            result = grid.view(game, state, battle)
        self.assertEqual(result['schema'], 'tk2-battle-tactical-view-v1')
        self.assertEqual(result['actors']['1']['attack_targets'], [101])
        self.assertEqual(result['actors']['1']['duel_targets'], [101])
        self.assertTrue(result['actors']['1']['reachable'])
        result['points']['attackers'] = 0
        self.assertEqual((battle, vars(state.rng)), before)


if __name__ == '__main__':
    unittest.main()
