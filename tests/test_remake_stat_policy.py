"""Current charisma, sourced first-appearance health and contextual loyalty."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
sys.path.insert(0, str(ROOT / 'game'))
import officer_stat_sources
from remake.campaign import Campaign, Catalog
from remake.officers import appearance_values, recruitment_loyalty
from remake.session import CampaignSession
from campaign_fixtures import controlled_catalog, advance_month


def read(path):
    return json.loads((ROOT / path).read_text())


class PublicWangJianIdentityReviewTests(unittest.TestCase):
    """One contextual identity closes without changing any source facts."""
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('public_wang_jian_stat_review',
            ROOT / 'tools/officer-placement/import_campaign_stats.py')
        cls.importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.importer)
        cls.pool = read('game/config/campaigns/people.json')
        cls.reference = read('game/config/references/cnblogs-officer-stats.json')
        cls.pid = 'historical-wang-jian-liaodong'

    def test_all_237_factual_rows_and_other236_bindings_are_unchanged(self):
        self.assertEqual(self.importer.factual_digest(self.reference['records']),
                         self.importer.FACTUAL_RECORDS_SHA256)
        unchanged = [row for row in self.reference['records']
                     if row['source_row_id'] != 'cnblogs-line-0229']
        # Frozen from f65d3ab; includes all previous223 bindings and13 unbound
        # records, not only the numerical source columns.
        self.assertEqual(sha256(json.dumps(unchanged, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            '7da3c26e10809ae70d76f2bb27454c2e1d8cf72e339c1cb0c0e0614cf5a682e4')
        self.importer.validate_reference(self.reference, self.pool['people'])

    def test_wang_jian_context_joins_only_liaodong_person_not_a_namesake(self):
        people = deepcopy(self.pool['people'])
        people['unrelated-tang-wang-jian'] = dict(name='王建', aliases=['王建'])
        facts = [{key: row[key] for key in self.importer.FACTUAL_FIELDS}
                 for row in self.reference['records']]
        bound = self.importer.bind_records(facts, people)
        row = next(row for row in bound if row['source_row_id'] == 'cnblogs-line-0229')
        self.assertEqual((row['person_id'], row['identity_status'], row['faction_ids']),
                         (self.pid, 'reviewed_context_identity', []))
        self.assertEqual((row['original_appearance'], row['city_label'], row['health'],
                          row['martial_strength'], row['intellect'], row['loyalty'], row['virtue']),
                         ('196', '辽东', 42, 24, 75, 59, 41))
        people[self.pid]['name'] = 'wrong person'
        with self.assertRaisesRegex(ValueError, 'Reviewed identity changed'):
            self.importer.bind_records(facts, people)

    def test_policy_applies_initial42_not_cap_and_keeps_contextual59_unapplied(self):
        before = deepcopy(self.pool)
        result = self.importer.apply_policy(self.pool, self.reference)
        self.assertEqual(self.pool, before, 'The policy helper must not mutate its input')
        person = result['people'][self.pid]
        self.assertEqual(person['initialization'], dict(schema='tk2-officer-initialization-v1',
            health=42, default_loyalty=80, source_loyalty=dict(value=59, display='59',
            source_faction_label='袁绍右侧空城', faction_ids=[],
            reference='game/config/references/cnblogs-officer-stats.json',
            source_row_id='cnblogs-line-0229')))
        self.assertEqual((person['profile']['health_max'], person['profile']['virtue']), (80, 60))
        for field in ('birth_year', 'service_year', 'death_year'):
            self.assertEqual(person[field], before['people'][self.pid][field])
        from remake.officers import OfficerProfile
        profile = OfficerProfile(**person['profile'])
        self.assertEqual(appearance_values(profile, person['initialization'], faction_id='gongsun'),
                         dict(health=42, loyalty=80))
        self.assertEqual(appearance_values(profile, person['initialization'])['loyalty'], 0)
        self.assertEqual({pid: result['people'][pid] for pid in before['order'][:1030]},
                         {pid: before['people'][pid] for pid in before['order'][:1030]})

    def test_source_values_context_and_closed_metadata_cannot_be_forged(self):
        for field in ('health', 'lifespan_year', 'faction_ids', 'bound_people'):
            reference = deepcopy(self.reference)
            row = next(row for row in reference['records'] if row['source_row_id'] == 'cnblogs-line-0229')
            if field == 'faction_ids':
                row[field] = ['gongsun']
            elif field == 'bound_people':
                reference[field] = 223
            else:
                row[field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.importer.validate_reference(reference, self.pool['people'])


class CampaignStatPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = read('game/config/campaigns/people.json')['people']
        cls.reference = read('game/config/references/cnblogs-officer-stats.json')
        cls.rows = {row['person_id']: row for row in cls.reference['records'] if row['person_id'] is not None}
        cls.abilities = {row['person_id']: row['stats']
            for row in read('game/config/references/san14-abilities.json')['abilities']}

    def test_all1000_charisma_values_win_and_only52_missing_values_use60(self):
        self.assertEqual(len(self.people), 1052)
        self.assertEqual(len(self.abilities), 1000)
        missing = set(self.people) - set(self.abilities)
        self.assertEqual(len(missing), 52)
        for pid, person in self.people.items():
            with self.subTest(person=pid):
                prior = person['pre_campaign_stat_policy_v1']
                self.assertIn('profile', prior)
                self.assertIn('configuration', prior)
                self.assertIn('virtue_design', prior)
                self.assertIn('initialization', prior)
                if pid in self.abilities:
                    source = self.abilities[pid]
                    self.assertEqual(person['profile']['source_stats']['charisma'], source['charisma'])
                    self.assertEqual(person['profile']['virtue'], min(99, source['charisma']))
                    self.assertEqual(person['virtue_design']['status'], 'san14_charisma')
                    for field in ('martial_strength', 'intellect'):
                        self.assertEqual(person['profile'][field], prior['profile'][field])
                else:
                    self.assertEqual(person['profile']['virtue'], 60)
                    self.assertEqual(person['virtue_design']['status'], 'configured_default')
                self.assertEqual(person['virtue_design']['policy_id'], 'campaign-officer-stats-v1')
                self.assertFalse(person['virtue_design']['is_historical_fact'])
                self.assertEqual(person['profile']['terrain_affinity'], prior['profile']['terrain_affinity'])
        self.assertEqual(self.people['san14-candidate-0231']['profile']['virtue'], 77)
        self.assertEqual(self.people['san14-candidate-0952']['profile']['virtue'], 99)

    def test_237_source_rows_keep224_reviewed_bindings_without_fuzzy_joining(self):
        self.assertEqual(self.reference['schema'], 'tk2-cnblogs-officer-stats-v1')
        rows = self.reference['records']
        self.assertEqual(len(rows), 237)
        self.assertEqual(len(self.rows), 224)
        self.assertEqual(sum(row['person_id'] is None for row in rows), 13)
        self.assertEqual(self.reference['identity_counts'], dict(
            reviewed_exact_name=212, reviewed_spelling=9, reviewed_context_identity=3, unbound=13))
        self.assertEqual(len({row['source_row_id'] for row in rows}), 237)
        self.assertEqual(len({row['source_line'] for row in rows}), 237)
        for row in rows:
            self.assertRegex(row['source_line_sha256'], r'^[a-f0-9]{64}$')
            self.assertEqual(row['source_row_id'], f"cnblogs-line-{row['source_line']:04d}")
            self.assertEqual(row['name'], row['source_name'].replace('★', '').replace('▲', ''))
            if row['loyalty_display'] == '--':
                self.assertIsNone(row['loyalty'])
            else:
                self.assertEqual(int(row['loyalty_display']), row['loyalty'])

    def test_original_health_is_initial_value_and_remake_cap_is_separate(self):
        for pid, person in self.people.items():
            with self.subTest(person=pid):
                policy = person['initialization']
                prior_cap = person['pre_campaign_stat_policy_v1']['profile']['health_max']
                self.assertEqual(policy['schema'], 'tk2-officer-initialization-v1')
                self.assertEqual(policy['default_loyalty'], 80)
                expected_health = self.rows[pid]['health'] if pid in self.rows else 80
                self.assertEqual(policy['health'], expected_health)
                self.assertEqual(person['profile']['health_max'], max(prior_cap, expected_health))
                if pid not in self.rows:
                    self.assertIsNone(policy['source_loyalty'])
                    continue
                source, raw = policy['source_loyalty'], self.rows[pid]
                self.assertEqual(source['value'], raw['loyalty'])
                self.assertEqual(source['display'], raw['loyalty_display'])
                self.assertEqual(source['source_faction_label'], raw['faction_label'])
                self.assertEqual(source['source_row_id'], raw['source_row_id'])
                self.assertEqual(source['reference'], 'game/config/references/cnblogs-officer-stats.json')
                self.assertIsInstance(source['faction_ids'], list)
                self.assertEqual(len(source['faction_ids']), len(set(source['faction_ids'])))
                self.assertEqual(source['faction_ids'], raw['faction_ids'])

    def test_contextual_loyalty_does_not_treat_original_ruler_marker_as100(self):
        catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')
        numeric_contexts = ruler_markers = unmatched = 0
        for pid, person in self.people.items():
            profile = catalog.profiles[catalog.ids[pid]]
            policy = person['initialization']
            source = policy['source_loyalty']
            self.assertEqual(appearance_values(profile, policy)['loyalty'], 0)
            self.assertEqual(appearance_values(profile, policy, faction_id='wei', is_ruler=True)['loyalty'], 100)
            self.assertEqual(appearance_values(profile, policy, faction_id='unrelated-faction')['loyalty'], 80)
            if source is None:
                unmatched += 1
            elif source['value'] is None:
                ruler_markers += 1
                for side in ('wei', 'shu', 'wu'):
                    self.assertEqual(appearance_values(profile, policy, faction_id=side)['loyalty'], 80)
            else:
                for side in source['faction_ids']:
                    numeric_contexts += 1
                    self.assertEqual(appearance_values(profile, policy, faction_id=side)['loyalty'], source['value'])
        self.assertGreater(numeric_contexts, 0)
        self.assertGreater(ruler_markers, 0)
        self.assertEqual(unmatched, 828)

    def test_offline_validator_rejects_old_virtue_and_forged_source_initialization(self):
        officer_stat_sources.validate_campaign_stats(self.people, self.reference)
        pid = 'san14-candidate-0231'
        for field in ('virtue', 'initial_health', 'loyalty', 'faction_context'):
            people = deepcopy(self.people)
            person = people[pid]
            if field == 'virtue':
                person['profile']['virtue'] = 86
            elif field == 'initial_health':
                person['initialization']['health'] += 1
            elif field == 'loyalty':
                person['initialization']['source_loyalty']['value'] = 1
            else:
                person['initialization']['source_loyalty']['faction_ids'].append('unrelated-faction')
            with self.subTest(field=field), self.assertRaises(ValueError):
                officer_stat_sources.validate_campaign_stats(people, self.reference)

    def test_all29_openings_and_previews_use_the_same_health_and_loyalty_rules(self):
        index = read('game/data/campaigns/index.json')
        self.assertEqual(len(index['catalogs']), 29)
        session = CampaignSession([ROOT / 'game/data' / name for name in index['catalogs']])
        matches = mismatches = free = 0
        for catalog in session.catalogs.values():
            with self.subTest(scenario=catalog.data['id']):
                self.assertEqual(catalog.rules.city_officer_capacity, 99)
                self.assertEqual(catalog.rules.battle_officers_per_side, 10)
                faction = next(iter(catalog.factions))
                session.command('new', dict(scenario=catalog.data['id'], faction=faction, seed=2026), session.revision)
                game = session.game
                starts = {catalog.ids[row['person_id']]: row for row in catalog.data['initial_officers']}
                for ident, officer in game.state.officers.items():
                    person = catalog.by_id[ident]
                    policy = person['initialization']
                    row = starts.get(ident)
                    self.assertEqual(officer.health, policy['health'])
                    if row is None:
                        self.assertEqual(officer.loyalty, 0)
                        free += 1
                    else:
                        source = policy['source_loyalty'] or {}
                        expected = (100 if row.get('ruler') else source['value']
                            if source.get('value') is not None and officer.faction_id in source['faction_ids'] else 80)
                        self.assertEqual(officer.loyalty, expected)
                        if not row.get('ruler') and source.get('value') is not None:
                            if officer.faction_id in source['faction_ids']:
                                matches += 1
                            else:
                                mismatches += 1
                saved = session.export_save()
                for city in {row['city'] for row in catalog.data['initial_officers'][:8]}:
                    preview = session.preview_city(catalog.data['id'], city)['city']
                    for person in preview['officers']:
                        actual = game.state.officers[person['id']]
                        self.assertEqual((person['health'], person['loyalty']), (actual.health, actual.loyalty))
                self.assertEqual(session.export_save(), saved)
        self.assertGreater(matches, 0)
        self.assertGreater(mismatches, 0)
        self.assertGreater(free, 0)

    def test_load_and_views_preserve_existing_damage_and_loyalty_instead_of_reinitializing(self):
        game = Campaign(Catalog(ROOT / 'game/data/campaigns/217-07.json'))
        game.command('new', dict(faction='wei', seed=2026), 0)
        ident = next(i for i, p in game.state.officers.items()
            if p.faction_id == 'wei' and i not in game.state.extension['leaders'].values())
        officer = game.state.officers[ident]
        officer.health = max(1, officer.health - 7)
        officer.loyalty = 17
        original = game.export_save()
        twin = Campaign(game.catalog)
        twin.load_save(original, 0)
        twin.view()
        self.assertEqual(twin.export_save(), original)
        self.assertEqual(twin.state.officers[ident].loyalty, 17)
        self.assertEqual(twin.state.officers[ident].health, officer.health)
        self.assertEqual(recruitment_loyalty(99, 80), 90,
                         'This stage does not replace the existing post-recruitment loyalty formula')

    def test_future_free_appearance_uses_source_initial_health_and_no_faction_loyalty(self):
        data = controlled_catalog().data
        starts = {row['person_id'] for row in data['initial_officers']}
        person = next(p for p in data['people'] if p['person_id'] not in starts
            and type(p['service_year']) is int and p['service_year'] <= 217
            and type(p['death_year']) is int and p['death_year'] > 220
            and p['initialization']['health'] < p['profile']['health_max'])
        pid = person['person_id']
        data['appearance_windows'][pid] = [dict(start=[218, 1], end=[220, 12], city='nanyang')]
        data['appearance_locations'][pid] = 'nanyang'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'future.json'
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
            game = Campaign(Catalog(path))
        game.command('new', dict(faction='wei', seed=2026), 0)
        ident = game.catalog.ids[pid]
        self.assertNotIn(ident, game.state.officers)
        advance_month(game)
        advance_month(game)
        self.assertIn(ident, game.state.officers)
        self.assertEqual(game.state.officers[ident].loyalty, 0)
        self.assertEqual(game.state.officers[ident].health, person['initialization']['health'],
                         'A newly appeared officer must not receive an immediate extra monthly heal')
        advance_month(game)
        self.assertEqual(game.state.officers[ident].health,
            min(person['profile']['health_max'], person['initialization']['health'] + data['rules']['monthly_heal']))


if __name__ == '__main__':
    unittest.main()
