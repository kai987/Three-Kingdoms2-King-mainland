"""Frozen retainer decisions reject coherent drift, not just malformed JSON.

Small offline fixtures exercise failures without rewriting the accepted table.
The integration test also validates all real catalogues when the new reference
is present; it never rewrites generated game files or the authored reference.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'retainer_affiliation_audit_tests', ROOT / 'tools/scenario-history/retainer_audit.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
SOURCE = 'https://zh.wikisource.org/wiki/三國志/卷15'


def person(pid, runtime, name):
    return dict(person_id=pid, runtime_id=runtime, name=name,
        birth_year=170, service_year=190, death_year=230,
        chronology_basis='explicit_authorial_game_window_not_exact_historical_dates',
        chronology_design=dict(precision=dict(birth_year='authorial_estimate',
            service_year='attested_career_window_authorial_opening',
            death_year='authorial_exit_boundary_not_exact_death'), basis='活躍期間を参考に本作の登場期間を推定。'),
        profile=dict(virtue=60, health_max=80, martial_strength=60, intellect=60,
            terrain_affinity=1, source_stats={}, basis={key: 'explicit_authorial_game_design'
                for key in ('virtue', 'health_max', 'martial_strength', 'intellect', 'terrain_affinity')}),
        initialization=dict(health=80, default_loyalty=80, source_loyalty=None),
        configuration=dict(is_historical_measurement=False),
        virtue_design=dict(source_charisma=None, is_historical_fact=False),
        ability_source=dict(kind='historical_authorial_game_design', source_urls=[SOURCE]))


def fixture():
    order = ['old-ruler-a', 'old-ruler-b', 'old-retainer', 'new-retainer']
    people = {pid: person(pid, i, pid) for i, pid in enumerate(order, 1)}
    canonical = dict(schema='tk2-campaign-people-v1', order=order, people=people)
    era = {}
    for pid, faction, city, status in (
            (order[0], 'a', 'ca', 'serving'), (order[1], 'b', 'cb', 'serving'),
            (order[2], 'a', 'ca', 'serving'), (order[3], None, 'cb', 'free')):
        era[pid] = dict(status=status, faction=faction, city=city, planning_complete=True,
            placement_review=dict(basis='reviewed_retainer', historical_certainty='regional_proxy'),
            appearance_plan=dict(status=status, city=city, start=[200, 1], end=[230, 12]))
    data = dict(id='mainland200-01', title='Test', start_year=200, start_month=1, officer_count=4, city_count=2,
        main_scenario=dict(fictional=False), people=list(deepcopy(people).values()),
        cities=[dict(id='ca', name='A'), dict(id='cb', name='B')], active_cities=['ca', 'cb'],
        initial_owners=dict(ca='a', cb='b'), faction_rulers=dict(a=1, b=2),
        factions=[dict(id='a', city='ca', captain=order[0], initial_officers=2),
                  dict(id='b', city='cb', captain=order[1], initial_officers=1)],
        initial_officers=[dict(person_id=order[0], city='ca', troops=300, ruler=True),
                          dict(person_id=order[1], city='cb', troops=300, ruler=True),
                          dict(person_id=order[2], city='ca', troops=100, ruler=False)],
        initial_free_officers=[dict(person_id=order[3], city='cb')],
        era_assignments=era, appearance_windows={pid: [] for pid in order},
        initial_resources=dict(gold=100, grain=300, reserves=200),
        initial_city_resources={}, placement_completion=dict(schema='tk2-placement-completion-v1',
            complete=True, pending=0, capacity=99, people=4, future_plans=0,
            bases=dict(reviewed_retainer=4), reference_classes=dict(regional_proxy=4)),
        coverage=dict(library=4, configured_profiles=4, health_configured=4, affinity_configured=4,
            placement_plans=4, initial_serving=3, planned_serving=3, initial_free=1,
            planned_max_city_roster=2, future_plans=0, san14_charisma_profiles=0,
            default_virtue_profiles=4, pending_profiles=0, pending_capacity=0,
            pending_history=0, pending_faction=0, pending_factions=[]))
    note = dict(note='地域代理は月別駐地の史証ではありません。', source_urls=[SOURCE], certainty='regional_proxy')
    decision = dict(id=data['id'], date=[200, 1], fictional=False, notes=[],
        factions=[dict(id='a', city='ca', ruler=1, person_ids=sorted([order[0], order[2]]), **note),
                  dict(id='b', city='cb', ruler=2, person_ids=[order[1]], **note)],
        changes=[dict(person_id=order[3], before=dict(status='scenario_excluded', faction=None,
                city=None, ruler=False, troops=0),
            after=dict(status='free', faction=None, city='cb', ruler=False, troops=0), **note)],
        chronology=[dict(person_id=order[3], **{key: people[order[3]][key]
                        for key in AUDIT.CHRONOLOGY_FIELDS}, **note)],
        material=dict(gold=200, grain=600, soldiers=1100),
        owners_sha256=AUDIT.digest(data['initial_owners']),
        faction_rulers_sha256=AUDIT.digest(data['faction_rulers']))
    review = dict(schema='tk2-retainer-affiliation-review-v1', revision='fixture-v1', base_commit='f65d3ab',
        base_person_count=3, person_count=4, base_people_snapshot_sha256=AUDIT.digest(dict(
            order=order[:3], people={pid: people[pid] for pid in order[:3]})),
        new_people=[dict(person_id=order[3], name=order[3], runtime_id=4, birth_year=170,
            service_year=190, death_year=230, note='未確定年は本作の推定です。', source_urls=[SOURCE])],
        scope_factions=['a', 'b'], scenarios=[decision])
    return canonical, data, review


class RetainerAuditNegativeTests(unittest.TestCase):
    def setUp(self):
        self.canonical, self.data, self.review = fixture()
        self.decision = self.review['scenarios'][0]
        self.constants = patch.multiple(AUDIT, EXPECTED_BASE_PEOPLE=3, EXPECTED_PEOPLE=4,
            EXPECTED_SCENARIOS=1, EXPECTED_HISTORICAL=1, EXPECTED_FICTIONAL=0,
            EXPECTED_SCOPE=2, FIRST_NEW_RUNTIME=4)
        self.constants.start()
        self.addCleanup(self.constants.stop)

    def checked(self):
        people, order, _ = AUDIT.check_people(self.canonical, self.review)
        return AUDIT.check_catalog(self.data, self.decision, people, order, ['a', 'b'])

    def test_accepted_reference_and_complete_plan_fixture_pass(self):
        result = self.checked()
        self.assertEqual(result['material'], self.decision['material'])
        self.assertEqual(len(result['factions']), 2)
        self.assertEqual(result['changes'][0]['before'], self.decision['changes'][0]['before'])

    def test_coherent_wrong_affiliation_rejected_even_with_correct_totals(self):
        row = self.data['initial_officers'][2]
        row['city'] = 'cb'
        era = self.data['era_assignments']['old-retainer']
        era.update(faction='b', city='cb')
        era['appearance_plan']['city'] = 'cb'
        self.data['factions'][0]['initial_officers'] = 1
        self.data['factions'][1]['initial_officers'] = 2
        with self.assertRaisesRegex(ValueError, 'frozen retainer roster differs'):
            self.checked()

    def test_missing_or_duplicate_frozen_roster_is_rejected(self):
        for roster in (['old-ruler-a'], ['old-ruler-a', 'old-retainer', 'old-retainer']):
            with self.subTest(roster=roster):
                self.decision['factions'][0]['person_ids'] = roster
                with self.assertRaisesRegex(ValueError, 'frozen retainer roster differs'):
                    self.checked()

    def test_one_extra_resource_or_carried_soldier_is_rejected(self):
        for field in ('gold', 'grain', 'reserves'):
            with self.subTest(field=field):
                self.data['initial_city_resources'] = dict(ca=dict(gold=100, grain=300, reserves=200))
                self.data['initial_city_resources']['ca'][field] += 1
                with self.assertRaisesRegex(ValueError, 'material conservation differs'):
                    self.checked()
        self.data['initial_city_resources'] = {}
        self.data['initial_officers'][2]['troops'] += 1
        with self.assertRaisesRegex(ValueError, 'material conservation differs'):
            self.checked()

    def test_inactive_city_resources_are_not_counted(self):
        self.data['initial_city_resources']['closed'] = dict(gold=99999, grain=99999, reserves=99999)
        self.checked()

    def test_all_placement_counters_and_coverage_are_checked(self):
        for field in ('bases', 'reference_classes'):
            original = deepcopy(self.data['placement_completion'][field])
            self.data['placement_completion'][field][next(iter(original))] += 1
            with self.assertRaisesRegex(ValueError, 'placement counter is stale'):
                self.checked()
            self.data['placement_completion'][field] = original
        for field in self.data['coverage']:
            original = deepcopy(self.data['coverage'][field])
            self.data['coverage'][field] = ['pending'] if isinstance(original, list) else original + 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.checked()
            self.data['coverage'][field] = original

    def test_new_runtime_id_cannot_reuse_or_skip_old_identity(self):
        for runtime in (3, 5):
            with self.subTest(runtime=runtime):
                self.canonical['people']['new-retainer']['runtime_id'] = runtime
                with self.assertRaisesRegex(ValueError, 'runtime identities'):
                    self.checked()

    def test_entire_old_person_object_is_frozen_not_only_identity(self):
        person = self.canonical['people']['old-retainer']
        for key in ('virtue', 'intellect', 'health_max'):
            before = person['profile'][key]
            person['profile'][key] += 1
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'objects/order changed'):
                self.checked()
            person['profile'][key] = before
        person['new_undocumented_field'] = True
        with self.assertRaisesRegex(ValueError, 'objects/order changed'):
            self.checked()

    def test_compiled_stats_cannot_override_canonical_source(self):
        self.data['people'][2]['initialization']['default_loyalty'] = 99
        with self.assertRaisesRegex(ValueError, 'identity/profile/provenance differs'):
            self.checked()

    def test_new_default_attributes_and_provenance_cannot_claim_source_stats(self):
        for key, bad in (('virtue', 70), ('health_max', 90), ('source_stats', dict(charisma=60))):
            original = deepcopy(self.canonical['people']['new-retainer']['profile'][key])
            self.canonical['people']['new-retainer']['profile'][key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'authorial V60/H80'):
                self.checked()
            self.canonical['people']['new-retainer']['profile'][key] = original
        self.canonical['people']['new-retainer']['configuration']['is_historical_measurement'] = True
        with self.assertRaisesRegex(ValueError, 'must not claim historical measurements'):
            self.checked()

    def test_wang_jian_is_the_only_closed_source_health_exception(self):
        pid = AUDIT.WANG_JIAN_PERSON
        row = self.canonical['people'].pop('new-retainer')
        row.update(person_id=pid, name='王建')
        row['initialization'].update(health=42, source_loyalty=deepcopy(AUDIT.WANG_JIAN_LOYALTY_SOURCE))
        row['configuration']['health'] = 'cnblogs_initial_health_with_remake_compatibility_cap'
        row['profile'].update(martial_strength=24, intellect=75)
        row['ability_source'].update(kind='historical_career_with_reviewed_original_game_stats',
            original_numeric_reference=dict(reference='game/config/references/cnblogs-officer-stats.json',
                source_row_id='cnblogs-line-0229', martial_strength=24, intellect=75,
                health=42, loyalty=59, original_virtue=41))
        self.canonical['people'][pid] = row
        self.canonical['order'][-1] = pid
        frozen = self.review['new_people'][0]
        frozen.update(person_id=pid, name='王建', health=42, source_stat_person=pid)
        with patch.object(AUDIT, 'WANG_JIAN_RUNTIME', 4):
            AUDIT.check_people(self.canonical, self.review)
            for key, bad in (('source_row_id', 'cnblogs-line-0001'), ('value', 80), ('faction_ids', ['gongsun'])):
                source = row['initialization']['source_loyalty']
                old = deepcopy(source[key])
                source[key] = bad
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact source0229'):
                    AUDIT.check_people(self.canonical, self.review)
                source[key] = old

    def test_missing_duplicate_and_inactive_plans_are_rejected(self):
        self.data['people'].append(deepcopy(self.data['people'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate person_id'):
            self.checked()
        self.data['people'].pop()
        self.data['era_assignments'].pop('old-retainer')
        with self.assertRaisesRegex(ValueError, 'exactly one era and appearance plan'):
            self.checked()
        self.data['era_assignments']['old-retainer'] = deepcopy(self.data['era_assignments']['old-ruler-a'])
        self.data['initial_officers'].pop()
        with self.assertRaisesRegex(ValueError, 'active era person missing'):
            self.checked()

    def test_runtime_catalogue_population_counters_cannot_lag_the_pool(self):
        for field in ('officer_count', 'city_count'):
            old = self.data[field]
            self.data[field] -= 1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field + ' is stale'):
                self.checked()
            self.data[field] = old

    def test_wrong_after_chronology_owner_and_ruler_hashes_are_rejected(self):
        self.decision['changes'][0]['after']['city'] = 'ca'
        with self.assertRaisesRegex(ValueError, 'change.after differs'):
            self.checked()
        self.decision['changes'][0]['after']['city'] = 'cb'
        self.decision['chronology'][0]['death_year'] = 229
        with self.assertRaisesRegex(ValueError, 'chronology differs'):
            self.checked()
        self.decision['chronology'][0]['death_year'] = 230
        for field in ('owners_sha256', 'faction_rulers_sha256'):
            original = self.decision[field]
            self.decision[field] = '0' * 64
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.checked()
            self.decision[field] = original

    def test_if_opening_requires_an_explicit_exception_note(self):
        self.data['main_scenario']['fictional'] = self.decision['fictional'] = True
        with self.assertRaisesRegex(ValueError, 'IF premise/exception notes required'):
            self.checked()
        self.decision['notes'] = ['仮想シナリオの勝利前提を維持。']
        self.checked()

    def test_future_plans_count_both_catalogue_vocabularies_and_windows_are_unique(self):
        self.data['initial_free_officers'] = []
        era = self.data['era_assignments']['new-retainer']
        era['status'] = 'future'
        era['appearance_plan'].update(status='future', start=[201, 1])
        window = dict(start=[201, 1], end=[230, 12], city='cb')
        self.data['appearance_windows']['new-retainer'] = [window]
        self.data['coverage']['initial_free'] = 0
        self.decision['changes'][0]['after']['status'] = 'future'
        with self.assertRaisesRegex(ValueError, 'placement completion summary differs'):
            self.checked()
        self.data['coverage']['future_plans'] = 1
        self.data['placement_completion']['future_plans'] = 1
        self.checked()
        self.data['appearance_windows']['new-retainer'].append(deepcopy(window))
        with self.assertRaisesRegex(ValueError, 'duplicate appearance windows'):
            self.checked()

    def test_report_check_rejects_stale_bytes_and_never_rewrites_inputs(self):
        with tempfile.TemporaryDirectory(prefix='tk2-retainer-audit-') as directory:
            root = Path(directory)
            ref, people_path = root / 'reference.json', root / 'people.json'
            catalog_dir, report_dir = root / 'catalogs', root / 'reports'
            catalog_dir.mkdir()
            for path, value in ((ref, self.review), (people_path, self.canonical),
                    (catalog_dir / '200-01.json', self.data),
                    (catalog_dir / 'index.json', dict(catalogs=['campaigns/200-01.json']))):
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            inputs = {path: path.read_bytes() for path in (ref, people_path, *catalog_dir.iterdir())}
            with patch('builtins.print'):
                AUDIT.main(['--write', '--reference', str(ref), '--people', str(people_path),
                            '--catalog-dir', str(catalog_dir), '--report-dir', str(report_dir)])
            self.assertEqual(set(path.name for path in report_dir.iterdir()),
                             {AUDIT.REPORT_JSON.name, AUDIT.REPORT_MD.name})
            json_path, md_path = report_dir / AUDIT.REPORT_JSON.name, report_dir / AUDIT.REPORT_MD.name
            AUDIT.check(ref, catalog_dir, people_path, json_path, md_path)
            md_path.write_bytes(md_path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'report is stale'):
                AUDIT.check(ref, catalog_dir, people_path, json_path, md_path)
            self.assertEqual({path: path.read_bytes() for path in inputs}, inputs)
            self.assertTrue(md_path.read_bytes().endswith(b'\n\n'))


class RealRetainerAuditIntegrationTests(unittest.TestCase):
    def test_all_29_real_openings_match_frozen_retainer_reference(self):
        if not AUDIT.REFERENCE.exists():
            self.skipTest('Authored retainer reference not yet installed')
        report = AUDIT.build_report()
        self.assertEqual(report['summary']['scenarios'], 29)
        self.assertEqual(report['summary']['people'], 1052)
        self.assertEqual(report['summary']['new_people'], 22)
        self.assertEqual(report['summary']['historical'], 23)
        self.assertEqual(report['summary']['fictional'], 6)


if __name__ == '__main__':
    unittest.main()
