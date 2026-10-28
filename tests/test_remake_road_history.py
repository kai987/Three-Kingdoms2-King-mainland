"""History distinguishes attested corridors, dated works and uncertain dates."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
from road_history import apply_history, validate_availability, validate_closures, validate_reference


class RoadHistoryReference(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / 'game/config/road-history.json').read_text())

    def test_attached_dates_preserve_inventory_and_match_all_copies_without_mutating_reference(self):
        identity = 'yuyang:liaoxi:lulong:land'
        data = dict(travel_routes=[dict(id=identity, mode='land')],
                    river_routes=[], sea_routes=[], exploration_routes=[])
        reference = deepcopy(self.spec)
        apply_history(data, self.spec)
        self.assertEqual(self.spec, reference)
        self.assertEqual(len(data['travel_routes']), 1)
        self.assertEqual(data['travel_routes'][0]['availability'], {'from': [207, 7]})
        self.assertIn('此前從未存在', data['travel_routes'][0]['history']['review']['basis_tc'])
        self.assertEqual(data['road_history']['schema'], 'tk2-road-history-v1')

    def test_first_record_and_uncertain_restoration_are_not_false_exact_opening_dates(self):
        ids = ['qiao:jiujiang:river', 'shujun:yuexi:land']
        data = dict(travel_routes=[dict(id=i) for i in ids])
        apply_history(data, self.spec)
        self.assertTrue(all('availability' not in row for row in data['travel_routes']))
        chronology = data['travel_routes'][1]['history']['review']['chronology']
        self.assertEqual(chronology['restoration_interval_years'], [239, 254])
        self.assertFalse(chronology['exact_year_known'])
        self.assertFalse(chronology['exact_month_known'])

    def test_excluded_upper_military_navigation_cannot_silently_reappear(self):
        for identity in ('tianshui:fufeng:river', 'wenshan:shujun:river'):
            with self.subTest(route=identity), self.assertRaisesRegex(ValueError, 'Unverified military navigation'):
                apply_history(dict(travel_routes=[dict(id=identity)]), self.spec)

    def test_unknown_sources_malformed_or_empty_date_windows_are_rejected(self):
        for value in (None, {}, {'from': [207, 0]}, {'from': [True, 7]},
                      {'from': [207, 7], 'to': [207, 7]}, {'from': [208, 1], 'to': [207, 7]},
                      {'from': [207, 7], 'guess': True}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_availability(value)
        for value in ({'from': [207, 7]}, {'to': [240, 1]}, {'from': [207, 7], 'to': [240, 1]}):
            validate_availability(value)
        bad = deepcopy(self.spec)
        next(iter(bad['route_reviews'].values()))['source_ids'] = ['not-a-source']
        with self.assertRaisesRegex(ValueError, 'Unknown reviewed road source'):
            validate_reference(bad)

    def test_conflicting_availability_fails_before_overwriting_authored_rules(self):
        data = dict(travel_routes=[dict(id='yuyang:liaoxi:lulong:land', availability={'from': [184, 1]})])
        with self.assertRaisesRegex(ValueError, 'Conflicting historical route availability'):
            apply_history(data, self.spec)

    def test_attested_july207_flood_is_one_documented_game_window_not_recurring_probability(self):
        data = dict(travel_routes=[dict(id='liaoxi:yuyang:land')])
        apply_history(data, self.spec)
        route = data['travel_routes'][0]
        self.assertEqual(route['closures'], [{'from': [207, 7], 'to': [207, 8]}])
        self.assertIn('並非史料明言八月已復通', route['history']['review']['basis_tc'])
        self.assertNotIn('availability', route)

    def test_unbounded_or_overlapping_closures_fail_validation(self):
        for value in ([], {}, [{'from': [207, 7]}],
                      [{'from': [207, 7], 'to': [207, 9]}, {'from': [207, 8], 'to': [207, 10]}]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_closures(value)
        validate_closures([{'from': [207, 7], 'to': [207, 8]}])


if __name__ == '__main__':
    unittest.main()
