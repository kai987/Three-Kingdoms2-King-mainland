"""Preview compression is lossless and independent of campaign/save identity."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.preview_transport import pack, unpack


class PreviewTransportTests(unittest.TestCase):
    def fixture(self):
        return [dict(id='s'+str(i), title='劇本'+str(i), river_routes=[dict(x=x, y=x+1) for x in range(300)],
                     initial_owners={'city': str(i)}, city_history={'city': {'name': '城'+str(i)}})
                for i in range(4)]

    def test_lossless_and_smaller_without_cross_scenario_mutation(self):
        original = self.fixture()
        before = deepcopy(original)
        wire = pack(original)
        self.assertEqual(unpack(wire), original)
        self.assertEqual(original, before)
        self.assertLess(len(json.dumps(wire)), len(json.dumps(original)) * .5)
        decoded = unpack(wire)
        decoded[0]['river_routes'][0]['x'] = -100
        self.assertEqual(decoded[1]['river_routes'][0]['x'], 0)
        self.assertEqual(unpack(wire), original)
        self.assertEqual(pack(original), wire)

    def test_malformed_references_are_rejected(self):
        wire = pack(self.fixture())
        cases = []
        for index in [-1, 999, True, '0']:
            changed = deepcopy(wire)
            changed['rows'][0]['refs']['river_routes'] = index
            cases.append(changed)
        changed = deepcopy(wire)
        changed['rows'][0]['values']['river_routes'] = []
        cases.append(changed)
        changed = deepcopy(wire)
        changed['shared'][0]['field'] = 'initial_owners'
        cases.append(changed)
        for value in cases:
            with self.subTest(value=value['rows'][0]['refs']):
                with self.assertRaises(ValueError):
                    unpack(value)

    def test_expansion_budget_and_known_ids_precede_copying(self):
        wire = pack(self.fixture())
        with patch('remake.preview_transport.MAX_EXPANDED_BYTES', 100), patch('remake.preview_transport.deepcopy') as copy:
            with self.assertRaisesRegex(ValueError, 'budget'):
                unpack(wire)
            copy.assert_not_called()
        with patch('remake.preview_transport.deepcopy') as copy:
            with self.assertRaisesRegex(ValueError, 'known scenarios'):
                unpack(wire, expected_ids={'unlisted'})
            copy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
