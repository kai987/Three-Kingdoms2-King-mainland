"""Dated exact-person loyalty policy and real allegiance transaction coverage."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests')]
from remake import dated_events, domestic, officer_relations
from remake.campaign import Campaign, Catalog, SeedRng
from remake.session import CampaignSession
from remake.strategic_ai import StrategicAI
from remake.view_transport import ViewTransport
from campaign_fixtures import controlled_catalog, arrange_contact
from campaign_dated_fixtures import dated_catalog, BIAN, HAN
from test_remake_tactical_ai import battle, successful_rng

RULER = 'san14-candidate-0952'
TARGET = 'san14-candidate-0005'
NEXT = 'san14-candidate-0147'


def row(ruler=RULER, person=TARGET, *, ident='controlled-tie', floor=96, **extra):
    return dict(id=ident, ruler_id=ruler, person_id=person, kind='parent_child',
                floor=floor, reason=dict(zh='受控測試關係', ja='制御されたテスト関係'),
                sources=['https://example.org/controlled-evidence'], **extra)


def source(records=None, exceptions=None):
    return dict(schema=officer_relations.SCHEMA, rules_version=officer_relations.RULES_VERSION,
                records=[row()] if records is None else records,
                exceptions=[] if exceptions is None else exceptions)


def command(game, action, **payload):
    return game.command(action, payload, game.revision)


def release(game, ident, *, city='xiangyang', retire=False):
    """Make an explicit controlled state change while conserving all soldiers."""
    state = game.state
    officer = state.officers[ident]
    home = next(c for c in state.cities.values() if ident in c.roster.officer_ids)
    home.roster.officer_ids.remove(ident)
    home.reserves += officer.troops
    officer.troops = 0
    officer.loyalty = 0
    officer.faction_id = None
    officer.alive = not retire
    if not retire:
        state.extension['free_locations'][str(ident)] = city


class PolicyTests(unittest.TestCase):
    def test_audit_oracle_independently_applies_floors_and_exception_precedence(self):
        spec = importlib.util.spec_from_file_location('relation_audit_oracle',
            ROOT / 'tools/officer-placement/audit_campaign_stats.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        policy = source([row(start_year=200, end_year=210)])
        self.assertEqual(audit.relationship_expectation(policy, RULER, TARGET, 200, 17)[0], 96)
        self.assertEqual(audit.relationship_expectation(policy, RULER, TARGET, 210, 99)[0], 99)
        self.assertEqual(audit.relationship_expectation(policy, RULER, TARGET, 211, 17), (17, None))
        exception = row(ident='audit-exception', start_year=205)
        exception.pop('floor')
        policy['exceptions'].append(exception)
        value, metadata = audit.relationship_expectation(policy, RULER, TARGET, 205, 17)
        self.assertEqual(value, 17)
        self.assertTrue(metadata['blocked'])

    def test_rejects_invalid_pairs_dates_sources_and_universal100(self):
        officer_relations.validate(source())
        for change in (dict(floor=100), dict(floor=True), dict(kind='same_surname'),
                       dict(person_id=RULER), dict(sources=[]), dict(sources=['javascript:alert(1)']),
                       dict(start_year=220, end_year=219), dict(start_year=True), dict(reason={'zh': '缺日文'})):
            bad = source()
            bad['records'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                officer_relations.validate(bad)
        bad = source()
        bad['records'].append(deepcopy(bad['records'][0]))
        with self.assertRaises(ValueError):
            officer_relations.validate(bad)

    def test_year_bounds_are_inclusive_and_exception_blocks_without_inventing_ties(self):
        tie = row(start_year=200, end_year=210)
        exception = row(ident='rivalry', start_year=205, end_year=207)
        exception.pop('floor')
        with patch.object(officer_relations, 'policy', return_value=source([tie], [exception])):
            for year in (199, 211):
                self.assertIsNone(officer_relations.relation(RULER, TARGET, year))
            for year in (200, 204, 208, 210):
                self.assertEqual(officer_relations.relation(RULER, TARGET, year)['floor'], 96)
            for year in (205, 207):
                self.assertTrue(officer_relations.relation(RULER, TARGET, year)['blocked'])
            self.assertIsNone(officer_relations.relation(TARGET, RULER, 204))
            self.assertIsNone(officer_relations.relation(RULER, 'same-surname-other-person', 204))

    def test_current_requires_exact_living_ruler_and_same_faction_and_keeps_earned100(self):
        people = {1: SimpleNamespace(person_id=RULER, faction_id='one', alive=True, loyalty=100),
                  2: SimpleNamespace(person_id=TARGET, faction_id='one', alive=True, loyalty=17),
                  3: SimpleNamespace(person_id=NEXT, faction_id='one', alive=True, loyalty=80)}
        state = SimpleNamespace(officers=people, year=217, extension={'leaders': {'one': 1}})
        with patch.object(officer_relations, 'policy', return_value=source()):
            officer_relations.apply(None, state, 2)
            self.assertEqual(people[2].loyalty, 96)
            people[2].loyalty = 100
            officer_relations.apply(None, state, 2)
            self.assertEqual(people[2].loyalty, 100)
            state.extension['leaders']['one'] = 3
            self.assertIsNone(officer_relations.current(state, 2))
            state.extension['leaders']['one'] = 1
            people[1].alive = False
            self.assertIsNone(officer_relations.current(state, 2))
            people[1].alive = True
            people[2].faction_id = 'other'
            self.assertIsNone(officer_relations.current(state, 2))
            people[2].faction_id = None
            people[2].loyalty = 0
            officer_relations.apply(None, state, 2)
            self.assertEqual(people[2].loyalty, 0)

    def test_exception_never_lowers_existing_loyalty_or_forces_betrayal(self):
        exception = row(ident='controlled-exception')
        exception.pop('floor')
        with patch.object(officer_relations, 'policy', return_value=source(exceptions=[exception])):
            game = Campaign(controlled_catalog())
            command(game, 'new', faction='shu', seed=2026)
            target = game.catalog.ids[TARGET]
            for value in (17, 99, 100):
                game.state.officers[target].loyalty = value
                before = game.export_save()
                metadata = officer_relations.apply(game, game.state, target)
                self.assertTrue(metadata['blocked'])
                self.assertEqual(game.export_save(), before)


class RuntimeRelationTests(unittest.TestCase):
    def setUp(self):
        self.policy = source()
        self.mock = patch.object(officer_relations, 'policy', return_value=self.policy)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def game(self, player='shu'):
        game = Campaign(controlled_catalog())
        command(game, 'new', faction=player, seed=2026)
        return game

    def test_opening_uses_floor_and_view_is_detached_without_repairing_current17(self):
        game = self.game()
        target = game.catalog.ids[TARGET]
        self.assertEqual(game.state.officers[target].loyalty, 96)
        self.assertEqual(game.state.officers[game.catalog.ids[NEXT]].loyalty, 99)
        self.assertEqual(game.state.officers[game.catalog.ids[RULER]].loyalty, 100)
        game.state.officers[target].loyalty = 17
        game.state.officers[target].health -= 3
        saved = game.export_save()
        with patch.object(SeedRng, 'next', side_effect=AssertionError('read drew RNG')):
            metadata = game.view()['catalog']['officer_relations']['officers'][str(target)]
            self.assertEqual(metadata['ruler_id'], RULER)
            self.assertEqual(metadata['person_id'], TARGET)
            metadata['reason']['zh'] = 'caller mutation'
            game._reconcile_factions(game.state)
            clone = Campaign(game.catalog)
            clone.load_save(saved, 0)
            self.assertEqual(clone.export_save(), saved)
        self.assertEqual(game.export_save(), saved)
        self.assertNotEqual(self.policy['records'][0]['reason']['zh'], 'caller mutation')
        self.assertNotIn('officer_relations', saved['state']['extension'])

    def test_successful_recruitment_uses_receiving_ruler_with_one_original_draw(self):
        game = self.game()
        target = game.catalog.ids[TARGET]
        release(game, target)
        successful_rng(game.state)
        draws = game.state.rng.draws
        command(game, 'recruit_officer', city='xiangyang', actor=game.catalog.ids[RULER], officer=target)
        self.assertEqual(game.state.officers[target].loyalty, 96)
        self.assertEqual(game.state.officers[target].faction_id, 'shu')
        self.assertEqual(game.state.rng.draws, draws + 1)

    def test_successful_defection_uses_actual_receiving_leader(self):
        game = self.game()
        target = game.catalog.ids[TARGET]
        game.state.cities['xiangyang'].roster.officer_ids.remove(target)
        game.state.cities['nanyang'].roster.officer_ids.append(target)
        game.state.officers[target].faction_id = 'wei'
        game.state.officers[target].loyalty = 30
        successful_rng(game.state)
        command(game, 'persuade_officer', city='xiangyang', actor=game.catalog.ids[RULER], officer=target)
        self.assertEqual(game.state.officers[target].loyalty, 96)
        self.assertEqual(game.state.rng.draws, 1)

    def test_domestic_ai_and_legacy_ai_recruitment_share_relation_policy(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                game = self.game('wei')
                target = game.catalog.ids[TARGET]
                release(game, target)
                successful_rng(game.state)
                if legacy:
                    StrategicAI(game, game.state).personnel_or_recruit(game.state.cities['xiangyang'])
                else:
                    domestic._personnel(game, game.state, game.state.cities['xiangyang'],
                        dict(id=target, method='recruit_officer', actor=game.catalog.ids[RULER], chance=95))
                self.assertEqual(game.state.officers[target].loyalty, 96)
                self.assertEqual(game.state.rng.draws, 1)

    def test_battle_conversion_uses_policy_without_an_extra_draw(self):
        game = battle(spell=8)
        current = game.state.battle
        actor = current['attackers'][0]
        target = next(unit for unit in current['defenders'] if unit['id'] == game.catalog.ids[TARGET])
        arrange_contact(game, actor=actor, target=target)
        game.state.officers[target['id']].loyalty = 30
        successful_rng(game.state)
        command(game, 'tactic', battle_id=current['id'], actor=actor['id'], target=target['id'], tactic=8)
        self.assertEqual(game.state.officers[target['id']].loyalty, 96)
        self.assertEqual(game.state.rng.draws, 1)
        self.assertIn(target['id'], game.state.cities['xiangyang'].roster.officer_ids)
        game.validate(game.state)

    def test_rewards_and_ordinary_transfer_do_not_reapply_floor(self):
        game = self.game()
        target = game.catalog.ids[TARGET]
        game.state.officers[target].loyalty = 17
        command(game, 'reward_officer', city='xiangyang', officer=target, kind='gold', amount=1)
        self.assertEqual(game.state.officers[target].loyalty, 18)
        destination = game.state.cities['nanjun']
        destination.owner = 'shu'
        for ident in destination.roster.officer_ids:
            game.state.officers[ident].faction_id = 'shu'
        command(game, 'transfer', source='xiangyang', target='nanjun', officers=[target])
        self.assertEqual(game.state.officers[target].loyalty, 18)
        game.view()
        self.assertEqual(game.state.officers[target].loyalty, 18)

    def test_player_succession_waits_for_confirmation_and_is_not_reapplied(self):
        game = self.game()
        target = game.catalog.ids[TARGET]
        self.policy['records'] = [row(ruler=NEXT, floor=97)]
        game.state.officers[target].loyalty = 17
        release(game, game.catalog.ids[RULER], retire=True)
        game._reconcile_factions(game.state)
        self.assertIn('shu', game.state.extension['pending_succession'])
        self.assertEqual(game.state.officers[target].loyalty, 17)
        transport = ViewTransport()
        provisional_wire = transport.pack(game.view(), game.catalog.sha256)
        command(game, 'choose_successor', officer=game.catalog.ids[NEXT])
        self.assertEqual(game.state.officers[target].loyalty, 97)
        self.assertEqual(game.view()['catalog']['officer_relations']['officers'][str(target)]['ruler_id'], NEXT)
        confirmed_wire = transport.pack(game.view(), game.catalog.sha256, provisional_wire['catalog_token'])
        self.assertNotIn('officer_relations', provisional_wire['static_catalog'])
        self.assertEqual(confirmed_wire['view']['catalog']['officer_relations']['officers'][str(target)]['ruler_id'], NEXT)
        game.state.officers[target].loyalty = 17
        game._reconcile_factions(game.state)
        game.view()
        self.assertEqual(game.state.officers[target].loyalty, 17)

    def test_ai_succession_applies_once_to_its_actual_ruler(self):
        game = self.game('wei')
        target = game.catalog.ids[TARGET]
        self.policy['records'] = [row(ruler=game.state.officers[ident].person_id,
                                      ident=f'successor-{ident}', floor=97)
                                  for ident in game.state.cities['xiangyang'].roster.officer_ids
                                  if ident not in {target, game.catalog.ids[RULER]}]
        game.state.officers[target].loyalty = 17
        release(game, game.catalog.ids[RULER], retire=True)
        before = deepcopy(game.state.rng)
        game._reconcile_factions(game.state)
        self.assertEqual(game.state.officers[target].loyalty, 97)
        self.assertNotIn('shu', game.state.extension['pending_succession'])
        self.assertEqual(game.state.rng, before)
        game.state.officers[target].loyalty = 17
        game._reconcile_factions(game.state)
        self.assertEqual(game.state.officers[target].loyalty, 17)

    def test_dated_founding_and_coup_apply_once_without_rng(self):
        self.policy['records'] = [row(ruler=BIAN, person=HAN, floor=94)]
        game = Campaign(dated_catalog('founding'))
        command(game, 'new', faction='han', seed=2026)
        game.state.year, game.state.month = 184, 11
        before = deepcopy(game.state.rng)
        dated_events.process(game, game.state)
        target = game.catalog.ids[HAN]
        self.assertEqual(game.state.officers[target].loyalty, 94)
        game.state.officers[target].loyalty = 17
        dated_events.process(game, game.state)
        self.assertEqual(game.state.officers[target].loyalty, 17)
        self.assertEqual(game.state.rng, before)

        self.policy['records'] = []
        catalog = dated_catalog('coup')
        catalog.data['initial_officers'].append(dict(person_id=NEXT, city='jincheng', troops=0, ruler=False))
        game = Campaign(catalog)
        command(game, 'new', faction='bian_zhang', seed=2026)
        # The controlled coup retires Bian Zhang, Beigong Boyu and Li Wenhou;
        # an existing living ordinary member receives a tie to the new ruler.
        rule = game.catalog.data['faction_coups'][0]
        candidate = game.state.officers[game.catalog.ids[NEXT]]
        candidate.loyalty = 17
        self.policy['records'] = [row(ruler=rule['successor'], person=candidate.person_id, floor=95)]
        game.state.year, game.state.month = rule['date']
        before = deepcopy(game.state.rng)
        dated_events.process(game, game.state)
        self.assertEqual(candidate.loyalty, 95)
        candidate.loyalty = 17
        dated_events.process(game, game.state)
        self.assertEqual(candidate.loyalty, 17)
        self.assertEqual(game.state.rng, before)


class PublishedPolicyTests(unittest.TestCase):
    def test_published_records_bind_exact_people_and_keep_liuguanzhang_baselines(self):
        data = officer_relations.policy()
        officer_relations.validate(data)
        catalog = Catalog(ROOT / 'game/data/campaigns/190-01.json')
        officer_relations.validate_catalog(catalog)
        self.assertGreater(len(data['records']), 0)
        self.assertTrue(data['exceptions'])
        for pid, minimum in (('san14-candidate-0147', 99), ('san14-candidate-0656', 98)):
            values = officer_relations.opening_values(catalog, catalog.ids[pid], faction_id='shu')
            self.assertGreaterEqual(values['loyalty'], minimum)

    def test_all29_openings_and_previews_match_and_load_and_views_do_not_change_saved_values(self):
        index = json.loads((ROOT / 'game/data/campaigns/index.json').read_text())
        self.assertEqual(len(index['catalogs']), 29)
        session = CampaignSession([ROOT / 'game/data' / name for name in index['catalogs']])
        for scenario, catalog in session.catalogs.items():
            with self.subTest(scenario=scenario):
                faction = next(row['id'] for row in dated_events.visible_factions(catalog))
                session.command('new', dict(scenario=scenario, faction=faction, seed=2026), session.revision)
                game = session.game
                before = game.export_save()
                for city in {row['city'] for row in catalog.data['initial_officers']}:
                    for displayed in session.preview_city(scenario, city)['city']['officers']:
                        officer = game.state.officers[displayed['id']]
                        self.assertEqual((displayed['health'], displayed['loyalty']), (officer.health, officer.loyalty))
                self.assertEqual(game.export_save(), before)
                target = next((ident for ident, officer in game.state.officers.items()
                               if officer.alive and officer.faction_id is not None
                               and ident not in game.state.extension['leaders'].values()), None)
                self.assertIsNotNone(target)
                game.state.officers[target].loyalty = 17
                saved = game.export_save()
                with patch.object(SeedRng, 'next', side_effect=AssertionError('read drew RNG')):
                    game.view()
                    clone = Campaign(catalog)
                    clone.load_save(saved, 0)
                    self.assertEqual(clone.export_save(), saved)
                self.assertEqual(game.export_save(), saved)


if __name__ == '__main__':
    unittest.main()
