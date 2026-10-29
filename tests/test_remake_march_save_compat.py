"""Real eight-case save/RNG baselines and cross-backend campaign compatibility.

The large arithmetic/vector ABI matrix stays in test_remake_march_core.py.
The primary v2 goldens pin complete saves and states without normalization.
A separate, declared migration comparison preserves the unchanged v1 evidence.
"""
from copy import deepcopy
from contextlib import nullcontext
from hashlib import sha256
import json
import unittest
from test_remake_march_core import (ROOT, CASES, HeadlessCampaign as Campaign, Catalog, canonical,
    campaign_fixture, campaign_result, using_backend)
import test_remake_march_core as matrix
from remake import officer_relations
from unittest.mock import patch


CHECKPOINTS = ('before', 'preview', 'queued', 'arrived')
BASELINE_PATH = ROOT / 'tests/fixtures/march-python-baseline-v2-command-books.json'


def baselines():
    current = json.loads(BASELINE_PATH.read_text())
    if current['schema'] != 'tk2-march-command-books-golden-v2':
        raise AssertionError('Unexpected march baseline schema')
    previous_bytes = (ROOT / current['previous']['path']).read_bytes()
    if sha256(previous_bytes).hexdigest() != current['previous']['sha256']:
        raise AssertionError('The retained pre-command-book reference was changed')
    if set(current['cases']) != {case[0] for case in CASES}:
        raise AssertionError('The reference must cover every real march case')
    return current, json.loads(previous_bytes)


class HistoricalOpeningInputTests(unittest.TestCase):
    def test_historical_fixture_changes_only_intentional_initial_loyalty(self):
        original = officer_relations.opening_values
        # Bypass only the fixture context for one current-policy control game.
        with patch.object(matrix, 'pre_relationship_opening', side_effect=nullcontext):
            current = campaign_fixture(CASES[0])
        historical = campaign_fixture(CASES[0])
        self.assertIs(officer_relations.opening_values, original,
                      'Historical inputs must not disable later allegiance rules')
        expected, retained = current.to_dict(), historical.to_dict()
        differences = []
        adjusted = deepcopy(retained)
        for ident, officer in expected['officers'].items():
            before = retained['officers'][ident]['loyalty']
            if before != officer['loyalty']:
                self.assertLess(before, officer['loyalty'])
                self.assertLessEqual(officer['loyalty'], 99)
                differences.append(ident)
                adjusted['officers'][ident]['loyalty'] = officer['loyalty']
        self.assertTrue(differences, 'The control must exercise real relationship floors')
        self.assertEqual(canonical(adjusted), canonical(expected),
                         'Every field except reviewed initial loyalty must remain exact')
        self.assertEqual(current.catalog.sha256, historical.catalog.sha256)
        self.assertEqual(current.state.rng, historical.state.rng)


class MarchReferenceBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline, cls.previous = baselines()
        with using_backend('python'):
            cls.actual = {case[0]: campaign_result(case,
                legacy_catalog_sha256=cls.baseline['previous']['catalog_sha256'])
                for case in CASES}

    def test_current_python_campaign_save_and_rng_hashes(self):
        for name, actual in self.actual.items():
            with self.subTest(case=name):
                self.assertEqual(canonical(actual), canonical(self.baseline['cases'][name]))
                for stage in CHECKPOINTS:
                    self.assertEqual(actual[stage]['save_version'], 2)

    def test_migration_preserves_complete_legacy_state_march_rules_and_rng(self):
        for name, actual in self.actual.items():
            previous = self.previous[name]
            with self.subTest(case=name):
                self.assertEqual(actual['quote'], previous['quote'])
                self.assertEqual(actual['troops'], previous['troops'])
                for stage in CHECKPOINTS:
                    # This supplemental copy removes only the added order pool
                    # and restores the old envelope version/catalog identity.
                    # Complete current hashes remain pinned in the test above.
                    proof = actual[stage]['legacy_compatibility']
                    self.assertEqual(proof, {key: previous[stage][key] for key in ('state', 'save')}, stage)
                    for key in ('rng', 'soldiers', 'turn'):
                        self.assertEqual(actual[stage][key], previous[stage][key], (stage, key))

    def test_march_time_rations_refill_risk_and_preview_contracts(self):
        physical = {
            # days, departure grain, total consumed, risk survival fraction
            'plain': (14, 11, 17, None),
            'yinping': (32, 39, 39, (1, 3)),
            'ziwu-rain': (48, 58, 58, (50, 100)),
            'ziwu-dry': (24, 29, 29, (80, 100)),
            'sea-tail': (8, 10, 10, (11, 100)),
            'sea-head': (32, 39, 39, (11, 100)),
            'sea-calm': (9, 11, 11, None),
            'explore': (18, 22, 22, (11, 100)),
        }
        for name, actual in self.actual.items():
            with self.subTest(case=name):
                self.assertEqual(actual['before'], actual['preview'], 'Repeated previews must be read only')
                queued = actual['queued']['march_projection']['travel']['marches'][0]
                march = actual['march_before_arrival']
                supply = march['supply']
                days, loaded, consumed, risk = physical[name]
                self.assertEqual(queued['quote'], actual['quote'])
                self.assertEqual(actual['quote']['days'], days)
                self.assertEqual(supply['route_days'], days)
                self.assertEqual(supply['elapsed_days'], days)
                self.assertEqual(supply['loaded'], loaded)
                self.assertEqual(supply['consumed'], consumed)
                source = queued['source']
                before_grain = actual['before']['march_projection']['grain'][source]
                queued_grain = actual['queued']['march_projection']['grain'][source]
                self.assertEqual(before_grain - queued_grain, loaded)
                self.assertEqual(supply['loaded'] + supply['received'], supply['consumed'] + supply['remaining'])
                self.assertEqual(supply['received'], 6 if name == 'plain' else 0)
                self.assertEqual((supply['shortage_days'], supply['lost']), (0, 0))
                self.assertEqual([(item['survival_numerator'], item['survival_denominator'])
                                  for item in march['risks']], [] if risk is None else [risk])
                self.assertTrue(all(not item['applied'] for item in march['risks']))
                self.assertFalse(actual['arrived']['march_projection']['travel']['marches'])


class MarchCampaignNativeCompatibilityTests(unittest.TestCase):
    setUpClass = classmethod(matrix.MarchNativeParityTests.setUpClass.__func__)

    def test_three_natural_ai_ten_day_turns_preserve_each_command_state_save_and_rng(self):
        catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')
        reference_game, native_game = Campaign(catalog), Campaign(catalog)
        transcript, phases, saw_march = [], set(), False

        def dispatch(kind, payload):
            nonlocal saw_march
            with using_backend('python'):
                reference_game.command(kind, deepcopy(payload), reference_game.revision)
                expected_state = canonical(reference_game.to_dict())
                expected_save = canonical(reference_game.export_save())
            with using_backend('rust'):
                native_game.command(kind, deepcopy(payload), native_game.revision)
                actual_state = canonical(native_game.to_dict())
                actual_save = canonical(native_game.export_save())
            transcript.append((kind, payload))
            label = f'command{len(transcript)}: {kind} {payload}'
            self.assertEqual(actual_state, expected_state, label)
            self.assertEqual(actual_save, expected_save, label)
            self.assertEqual(native_game.revision, reference_game.revision, label)
            self.assertEqual(native_game.journal, reference_game.journal, label)
            self.assertEqual((native_game.state.rng.state, native_game.state.rng.draws),
                             (reference_game.state.rng.state, reference_game.state.rng.draws), label)
            saw_march |= bool(reference_game.state.extension['travel']['marches'])

        dispatch('new', dict(faction='wu', seed=2026))
        for _ in range(100):
            state = reference_game.state
            phases.add(state.phase)
            if state.turn >= 4 and state.phase == 'city':
                break
            if state.phase == 'city':
                kind, payload = 'end_turn', {}
            elif state.phase == 'ai':
                kind, payload = 'ai', {'turn': state.turn}
            elif state.phase == 'arrivals':
                kind, payload = 'arrivals', {}
            elif state.phase == 'battle':
                kind, payload = 'retreat', {'battle_id': state.battle['id']}
            elif state.phase == 'result':
                kind, payload = 'settle', {'battle_id': state.battle['id']}
            else:
                self.fail(f'Unexpected natural replay phase: {state.phase}; commands={transcript}')
            dispatch(kind, payload)
        else:
            self.fail(f'Natural AI replay exceeded100commands: {transcript}')
        self.assertEqual((reference_game.state.year, reference_game.state.month, reference_game.state.day), (217, 8, 1))
        self.assertTrue({'ai', 'arrivals'} <= phases)
        self.assertTrue(saw_march, 'Natural AI must queue a real march')
        self.assertGreater(reference_game.state.rng.draws, 0)

    def test_full_campaigns_and_cross_backend_pending_save_loads_match_reference(self):
        baseline, _ = baselines()
        for backend, alternate in (('rust', 'python'), ('python', 'rust')):
            with using_backend(backend):
                for case in CASES:
                    with self.subTest(backend=backend, case=case[0]):
                        actual = campaign_result(case, alternate,
                            legacy_catalog_sha256=baseline['previous']['catalog_sha256'])
                        self.assertEqual(canonical(actual), canonical(baseline['cases'][case[0]]))


if __name__ == '__main__':
    unittest.main()
