"""Events describe committed facts; reading/dismissing them cannot play a turn."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, GameError, digest
from remake.difficulty import attack_budget, get_settings
from remake.events import LIMIT, STAFF_KINDS, SUPPLY_KINDS, empty, emit, transition, validate as validate_events
from campaign_fixtures import controlled_catalog, reach_battle, arrange_contact


def new_game(seed=2026, difficulty='normal'):
    game = Campaign(controlled_catalog())
    game.command('new', dict(faction='shu', seed=seed, difficulty=difficulty), 0)
    return game


class CampaignEventsTests(unittest.TestCase):
    def test_difficulty_only_changes_policy_and_is_saved(self):
        snapshots = []
        for difficulty in ('easy', 'normal', 'hard'):
            game = new_game(difficulty=difficulty)
            state = game.to_dict()
            self.assertEqual(state['extension']['difficulty'], difficulty)
            self.assertEqual(state['extension']['events']['items'][0]['kind'], 'campaign_start')
            self.assertEqual(state['extension']['events']['items'][0]['details']['difficulty'], difficulty)
            snapshots.append({k: v for k, v in state.items() if k != 'extension'})
            twin = Campaign(game.catalog)
            twin.load_save(game.export_save(), 0)
            self.assertEqual(game.export_save(), twin.export_save())
            settings = get_settings(game.state)
            settings['tactic_depth'] = 100
            self.assertNotEqual(get_settings(game.state)['tactic_depth'], 100)
            # The zero-attack controlled catalog remains zero in all modes.
            self.assertEqual(attack_budget(game.catalog, game.state), 0)
            game.catalog.data['rules']['ai_max_attacks_per_turn'] = 3
            self.assertEqual(attack_budget(game.catalog, game.state), {'easy': 1, 'normal': 3, 'hard': 6}[difficulty])
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])

    def test_invalid_new_and_failed_actions_never_commit_events_or_rng(self):
        game = new_game()
        before, revision = game.export_save(), game.revision
        for difficulty in ('unknown', None, False, ['hard']):
            with self.assertRaises(GameError):
                game.command('new', dict(faction='shu', seed=2026, difficulty=difficulty), revision)
            self.assertEqual(game.export_save(), before)
            self.assertEqual(game.revision, revision)
        with self.assertRaises(GameError):
            game.command('depart', dict(source='xiangyang', target='xiangyang', officers=[146]), revision)
        self.assertEqual(game.export_save(), before)
        for _ in range(3):
            game.view()
        self.assertEqual(game.export_save(), before)

    def test_recruit_outcomes_use_real_changes_and_stable_person_ids(self):
        outcomes = set()
        for seed in range(1, 51):
            game = new_game(seed)
            # Make the existing neutral officer available for a real visit;
            # this retains the catalog identity and all existing soldiers.
            target = game.state.cities['nanjun'].roster.officer_ids.pop()
            officer = game.state.officers[target]
            officer.faction_id = None
            game.state.cities['nanjun'].reserves += officer.troops
            officer.troops = 0
            officer.loyalty = 0
            game.state.extension['free_locations'][str(target)] = 'xiangyang'
            game.validate(game.state)
            game.command('recruit_officer', dict(city='xiangyang', actor=146, officer=target), game.revision)
            event = game.state.extension['events']['items'][-1]
            expected = 'recruit_success' if officer.person_id in [game.state.officers[i].person_id for i in game.state.cities['xiangyang'].roster.officer_ids] else 'recruit_failure'
            self.assertEqual(event['kind'], expected)
            self.assertEqual(event['person_ids'], [officer.person_id])
            self.assertEqual(event['details']['actor'], game.state.officers[146].person_id)
            outcomes.add(expected)
            twin = Campaign(game.catalog)
            twin.load_save(game.export_save(), 0)
            self.assertEqual(twin.export_save(), game.export_save())
            if len(outcomes) == 2:
                break
        self.assertEqual(outcomes, {'recruit_success', 'recruit_failure'})

    def test_battle_capture_result_and_duplicate_receipt_emit_once(self):
        game = new_game()
        game.command('allocate', dict(city='xiangyang', officer=146, troops=999), game.revision)
        game.command('depart', dict(source='xiangyang', target='nanjun', officers=[146]), game.revision)
        battle_id = reach_battle(game)
        # Isolate event/receipt semantics on actual native adjacent cells.
        arrange_contact(game)
        self.assertIn('battle_started', [e['kind'] for e in game.state.extension['events']['items']])
        for _ in range(50):
            if game.state.phase == 'result':
                break
            battle = game.state.battle
            game.command('attack', dict(battle_id=battle_id, actor=146, target=battle['defenders'][0]['id']), game.revision)
        self.assertEqual(game.state.phase, 'result')
        revision = game.revision
        game.command('settle', dict(battle_id=battle_id), revision)
        events = game.state.extension['events']['items']
        capture = [e for e in events if e['kind'] == 'city_captured']
        self.assertEqual(len(capture), 1)
        self.assertEqual(capture[0]['factions'], ['shu', 'neutral'])
        self.assertEqual(len([e for e in events if e['kind'] == 'battle_result']), 1)
        after = game.export_save()
        game.command('settle', dict(battle_id=battle_id), revision)
        self.assertEqual(game.export_save(), after)

    def test_queue_bound_and_tampered_event_saves_are_atomic(self):
        game = new_game()
        for _ in range(LIMIT + 2):
            game._emit_event(game.state, 'new_year', details=dict(year=game.state.year), audience='world')
        game.validate(game.state)
        events = game.state.extension['events']
        self.assertEqual(len(events['items']), LIMIT)
        self.assertEqual(events['items'][-1]['id'] + 1, events['next_id'])
        before, revision = game.export_save(), game.revision
        for mutate in ('duplicate', 'future', 'person', 'kind', 'payload', 'difficulty'):
            bad = deepcopy(before)
            row = bad['state']['extension']['events']['items'][-1]
            if mutate == 'duplicate':
                row['id'] -= 1
            elif mutate == 'future':
                row['year'] += 1
            elif mutate == 'person':
                row['person_ids'] = ['unknown-person']
            elif mutate == 'kind':
                row['kind'] = 'invented_history'
            elif mutate == 'payload':
                row['details']['html'] = '<script>bad</script>'
            else:
                bad['state']['extension']['difficulty'] = 'impossible'
            bad['checksum'] = digest({k: v for k, v in bad.items() if k != 'checksum'})
            with self.assertRaises(GameError):
                game.load_save(bad, revision)
            self.assertEqual(game.export_save(), before)
            self.assertEqual(game.revision, revision)

    def test_current_catalog_save_initializes_preferences_without_replaying_history(self):
        game = new_game()
        saved = game.export_save()
        for key in ('difficulty', 'ai_strategy', 'events'):
            saved['state']['extension'].pop(key)
        saved['checksum'] = digest({k: v for k, v in saved.items() if k != 'checksum'})
        twin = Campaign(game.catalog)
        twin.load_save(saved, 0)
        restored = twin.to_dict()
        self.assertEqual(restored['extension']['difficulty'], 'normal')
        self.assertEqual(restored['extension']['events'], dict(next_id=1, items=[]))
        self.assertEqual(restored['extension']['ai_strategy'], {})
        for key in saved['state']:
            if key != 'extension':
                self.assertEqual(restored[key], saved['state'][key])

    def test_supply_snapshots_survive_completed_columns_and_reject_invalid_saved_receipts(self):
        game = new_game()
        for unit_kind in ('march', 'convoy'):
            for kind in ('march_resupplied','march_starvation','march_retreat'):
                details = dict(unit_kind=unit_kind,unit_id=42,grain=20 if kind=='march_resupplied' else 0,
                    lost=3 if kind=='march_starvation' else 0,shortage_days=10,
                    reason='city' if kind=='march_resupplied' else 'shortage')
                game._emit_event(game.state,kind,city_ids=['xiangyang'],factions=['shu'],details=details)
        self.assertEqual({row['kind'] for row in game.state.extension['events']['items'][1:]},SUPPLY_KINDS)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertFalse(game.state.extension['logistics']['convoys'])
        game.validate(game.state)
        saved = game.export_save()
        twin = Campaign(game.catalog);twin.load_save(saved,0)
        self.assertEqual(twin.export_save(),saved,'Event snapshots never depend on a currently active convoy ID')
        for field,value in [('unit_kind','battle'),('unit_kind',[]),('unit_id',0),('unit_id',True),
                            ('grain',1),('lost',1),('shortage_days',-1),('shortage_days',True),
                            ('reason','<img src=x onerror=alert(1)>'),('extra',0)]:
            with self.subTest(field=field,value=value):
                bad = deepcopy(saved)
                bad['state']['extension']['events']['items'][-1]['details'][field] = value
                bad['checksum'] = digest({k:v for k,v in bad.items() if k!='checksum'})
                with self.assertRaises((ValueError,GameError)):
                    game.load_save(bad,game.revision)
                self.assertEqual(game.export_save(),saved)

    def test_supply_receipts_aggregate_within_a_command_and_keep_committed_ids_immutable(self):
        game=new_game()
        original=deepcopy(game.state.rng)
        def supply_only(state,payload):
            for grain in (4,6):
                game._supply_event(state,'march_resupplied',unit_kind='march',unit_id=42,
                    city='xiangyang',owner='shu',grain=grain,reason='convoy')
        with patch.object(game,'_allocate',supply_only):
            game.command('allocate',{},game.revision)
            receipts=[row for row in game.state.extension['events']['items'] if row['kind']=='march_resupplied']
            self.assertEqual(len(receipts),1)
            self.assertEqual(receipts[0]['details']['grain'],10)
            committed=deepcopy(receipts[0])
            game.command('allocate',{},game.revision)
        receipts=[row for row in game.state.extension['events']['items'] if row['kind']=='march_resupplied']
        self.assertEqual(len(receipts),2,'A second same-turn command needs a new event ID for live playback')
        self.assertEqual(receipts[0],committed)
        self.assertGreater(receipts[1]['id'],receipts[0]['id'])
        self.assertEqual(receipts[1]['details']['grain'],10)
        self.assertEqual(game.state.rng,original)


class CivilStaffEventTests(unittest.TestCase):
    def fixture(self):
        campaign = SimpleNamespace(catalog=SimpleNamespace(
            definitions={'historical-person': None}, map_cities={'home': None},
            factions={'shu': None, 'wei': None}, data={'title': 'Test campaign'}))
        state = SimpleNamespace(year=190, month=1, day=1, turn=1, player='shu', battle=None,
            officers={1: SimpleNamespace(person_id='historical-person', alive=True, faction_id=None)},
            cities={'home': SimpleNamespace(id='home', roster=SimpleNamespace(officer_ids=[]))},
            extension=dict(events=empty(), free_locations={}, leaders={}, ended_factions=[],
                           ai_strategy={}, outcome=None))
        return campaign, state

    def personal(self):
        return dict(staff_id='clerk-000001', name='王安', portrait='clerk-1', reason='opening')

    def test_all_staff_scenes_keep_snapshot_identity_separate_from_historical_pool(self):
        campaign, state = self.fixture()
        for kind in sorted(STAFF_KINDS):
            details = self.personal()
            if kind == 'staff_salary':
                details = dict(amount=10, paid=5, bonus=dict(gold=5, grain=0, reserves=0),
                               counts=dict(staff=2, total_unpaid=1, cities=1))
            emit(campaign, state, kind, city_ids=['home'], factions=['shu'], details=details, audience='world')
        before = deepcopy(state.extension['events'])
        validate_events(campaign, state)
        self.assertEqual(before, state.extension['events'])
        self.assertTrue(all(not event['person_ids'] for event in before['items']))
        self.assertEqual(len(before['items']), 6)
        # Expired/declined IDs are retained in the event snapshot, and are not
        # required to be active employees or candidates in a mutable registry.
        self.assertFalse(hasattr(state, 'civil_staff'))

    def test_tampered_staff_references_portraits_money_and_salary_are_rejected(self):
        campaign, state = self.fixture()
        emit(campaign, state, 'staff_candidate', city_ids=['home'], factions=['shu'],
             details=self.personal(), audience='world')
        original = deepcopy(state.extension['events'])
        cases = [('staff_id', 'historical-person'), ('staff_id', 'clerk-000000'),
                 ('staff_id', 1), ('name', ''), ('name', '王\x00安'),
                 ('portrait', '../original/001'), ('amount', -1), ('paid', True),
                 ('reason', '<script>')]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                state.extension['events'] = deepcopy(original)
                state.extension['events']['items'][0]['details'][key] = value
                with self.assertRaisesRegex(ValueError, 'Civil staff|Campaign event JSON'):
                    validate_events(campaign, state)
        for key, value in [('person_ids', ['historical-person']), ('city_ids', []), ('factions', [])]:
            state.extension['events'] = deepcopy(original)
            state.extension['events']['items'][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Civil staff'):
                validate_events(campaign, state)
        state.extension['events'] = empty()
        emit(campaign, state, 'staff_salary', city_ids=['home'], factions=['shu'], details=dict(
            amount=10, paid=5, bonus=dict(gold=0, grain=0, reserves=0), counts=dict(staff=2, total_unpaid=1, cities=1)))
        salary = deepcopy(state.extension['events'])
        for key, value in [('paid', 11), ('amount', 9), ('bonus', dict(gold=0, grain=0, reserves=-1)),
                           ('counts', dict(staff=4, total_unpaid=1, cities=1)), ('paid', 4),
                           ('counts', dict(staff=2, total_unpaid=0, cities=1))]:
            state.extension['events'] = deepcopy(salary)
            state.extension['events']['items'][0]['details'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Civil staff|Campaign event JSON'):
                validate_events(campaign, state)

    def test_monthly_salary_summary_can_cover_the_whole_faction_in_one_event(self):
        campaign, state = self.fixture()
        emit(campaign, state, 'staff_salary', city_ids=['home'], factions=['shu'], details=dict(
            amount=1725, paid=1720, bonus=dict(gold=230, grain=200, reserves=80),
            counts=dict(staff=345, total_unpaid=1, cities=115)))
        validate_events(campaign, state)
        self.assertEqual(len(state.extension['events']['items']), 1)

    def test_staff_executed_historical_recruitment_emits_one_safe_success_or_failure(self):
        for success in (False, True):
            campaign, before = self.fixture()
            after = deepcopy(before)
            if success:
                after.officers[1].faction_id = 'shu'
                after.cities['home'].roster.officer_ids.append(1)
            transition(campaign, before, after, 'staff_recruit',
                       dict(actor='clerk-000001', officer=1, city='home'))
            events = after.extension['events']['items']
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['kind'], 'recruit_success' if success else 'recruit_failure')
            self.assertEqual(events[0]['person_ids'], ['historical-person'])
            self.assertEqual(events[0]['details'], {})
            validate_events(campaign, after)


if __name__ == '__main__':
    unittest.main()
