"""Events describe committed facts; reading/dismissing them cannot play a turn."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, GameError, digest
from remake.difficulty import attack_budget, get_settings
from remake.events import LIMIT
from campaign_fixtures import controlled_catalog, reach_battle


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


if __name__ == '__main__':
    unittest.main()
