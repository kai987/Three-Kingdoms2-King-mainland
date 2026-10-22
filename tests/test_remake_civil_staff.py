"""Civil staff supplement real local shortages without spending historical IDs."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import civil_staff as staff
from remake.errors import GameError
from remake.officers import GameRules


class CampaignFixture:
    def __init__(self):
        self.catalog = SimpleNamespace(
            factions={'one': {}, 'two': {}},
            by_id={i: dict(name=f'历史人物{i}') for i in range(1200)},
            rules=GameRules(),
            data=dict(city_profiles={'capital': {'tier': 'giant'}},
                      rules=dict(recruit_officer_gold=60, monthly_gold_income=100,
                                 monthly_grain_income=200),
                      city_income={key: dict(gold=100, grain=200, reserves=100)
                                   for key in ('empty', 'one', 'capital', 'neutral')}))

    def _emit_event(self, state, kind, **values):
        state.events.append(deepcopy(dict(kind=kind, **values)))

    def _free_candidates(self, state, city):
        return state.extension.get('test_free', {}).get(city.id, [])


def fixture():
    game = CampaignFixture()
    officers = {i: SimpleNamespace(alive=True) for i in range(6)}
    cities = {key: SimpleNamespace(id=key, owner='one',
                  roster=SimpleNamespace(officer_ids=ids), gold=1000,
                  grain=1000, reserves=1000, action_used=False)
              for key, ids in [('empty', []), ('one', [0]), ('capital', [1, 2])]}
    cities['neutral'] = SimpleNamespace(id='neutral', owner='neutral',
        roster=SimpleNamespace(officer_ids=[]), gold=1000, grain=1000,
        reserves=1000, action_used=False)
    state = SimpleNamespace(seed=2026, year=190, month=1, day=1, turn=1,
        player='one', phase='city', battle=None, cities=cities, officers=officers,
        rng=SimpleNamespace(state=2026, draws=0), soldiers={'recruited': 0},
        extension={'ended_factions': [], 'travel': {'marches': []}}, events=[])
    state.extension['civil_staff'] = staff.empty(game, state)
    return game, state


def advance_month(state, count=1):
    absolute = staff.month_index(state) + count
    state.year, month = divmod(absolute, 12)
    state.month = month + 1
    state.day = 1
    state.turn += 3 * count
    for city in state.cities.values():
        city.action_used = False


def open_and_hire(game, state, key='empty'):
    staff.synchronize(game, state, opening=True)
    row = state.extension['civil_staff']['cities'][key]
    return staff.hire(game, state, key, row['candidate']['id'], state.cities[key].owner)


class CivilStaffTests(unittest.TestCase):
    def test_opening_empty_city_offer_is_fixed_and_separate_from_every_historical_id(self):
        game, state = fixture()
        history, combat_rng = deepcopy(state.officers), deepcopy(state.rng)
        before = deepcopy(state)
        skeleton = staff.empty(game, state)
        self.assertEqual(state, before)
        self.assertFalse(skeleton['people'])
        self.assertTrue(all(row['candidate'] is None for row in skeleton['cities'].values()))
        state.extension['civil_staff']['next_id'] = 5001
        staff.synchronize(game, state, opening=True)
        pool = state.extension['civil_staff']
        candidate = pool['cities']['empty']['candidate']
        self.assertEqual(candidate['id'], 'clerk-005001')
        self.assertEqual(candidate['profile']['virtue'], 60)
        self.assertTrue(10 <= candidate['profile']['martial_strength'] <= 35)
        self.assertTrue(40 <= candidate['profile']['intellect'] <= 65)
        self.assertIsNone(pool['cities']['one']['candidate'])
        self.assertIsNone(pool['cities']['capital']['candidate'])
        self.assertIsNone(pool['cities']['neutral']['candidate'])
        self.assertEqual(state.officers, history)
        self.assertEqual(state.rng, combat_rng)
        self.assertEqual(pool['rng']['draws'], 0)
        self.assertEqual(state.events[0]['person_ids'], [])
        self.assertEqual(state.events[0]['audience'], 'world')
        frozen = deepcopy(state)
        staff.synchronize(game, state, opening=True)
        self.assertEqual(state, frozen)
        staff.validate(game, state)

    def test_marching_roster_and_confirmed_near_arrivals_prevent_false_empty_city_offer(self):
        game, state = fixture()
        state.cities['one'].roster.officer_ids.append(3)
        state.extension['travel']['marches'] = [dict(kind='transfer', source='one',
            target='empty', owner='one', officers=[0, 3], arrival_turn=state.turn+3)]
        staff.synchronize(game, state, opening=True)
        rows = staff.view(game, state)['cities']
        self.assertEqual(rows['one']['effective_count'], 2)
        self.assertEqual(rows['empty']['effective_count'], 2)
        self.assertIsNone(rows['one']['candidate'])
        self.assertIsNone(rows['empty']['candidate'])
        self.assertEqual(rows['empty']['occupancy'], 0, 'Arrival forecasts never reserve actual staff slots twice')
        game, state = fixture()
        state.extension['travel']['marches'] = [dict(kind='transfer', source='one',
            target='empty', owner='two', officers=[0], arrival_turn=state.turn+1)]
        staff.synchronize(game, state, opening=True)
        self.assertIsNotNone(staff.view(game, state)['cities']['empty']['candidate'])

    def test_hire_without_officer_actor_is_atomic_and_uses_city_action_money_and_capacity(self):
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        city = state.cities['empty']
        candidate = state.extension['civil_staff']['cities']['empty']['candidate']
        for ident, owner, phase, gold in [('wrong', 'one', 'city', 1000),
                                        (candidate['id'], 'two', 'city', 1000),
                                        (candidate['id'], 'one', 'battle', 1000),
                                        (candidate['id'], 'one', 'city', 59)]:
            state.phase, city.gold = phase, gold
            before = deepcopy(state)
            with self.assertRaises(GameError):
                staff.hire(game, state, 'empty', ident, owner)
            self.assertEqual(state, before)
        state.phase, city.gold = 'city', 1000
        city.roster.officer_ids = list(range(99))
        state.officers.update({i: SimpleNamespace(alive=True) for i in range(99)})
        with self.assertRaisesRegex(GameError, '容量'):
            staff.hire(game, state, 'empty', candidate['id'], 'one')
        city.roster.officer_ids.clear()
        historical = deepcopy(state.officers)
        person = staff.hire(game, state, 'empty', candidate['id'], 'one')
        self.assertEqual(city.gold, 940)
        self.assertTrue(city.action_used)
        self.assertEqual(staff.city_count(state, city.id), 1)
        self.assertEqual(staff.city_occupancy(state, city), 1)
        self.assertEqual(person['troops'], 0)
        self.assertEqual(person['experience'], 0)
        self.assertEqual(state.officers, historical)
        self.assertEqual(person['action_turn'], 0)
        with self.assertRaises(GameError):
            staff.hire(game, state, 'empty', candidate['id'], 'one')
        staff.synchronize(game, state)
        staff.validate(game, state)

    def test_two_month_observation_different_probabilities_and_fourth_check_guarantee(self):
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        with patch.object(staff, '_draw', return_value=99) as draw:
            advance_month(state)
            staff.synchronize(game, state, monthly=True)
            self.assertEqual(draw.call_count, 0)
            for _ in range(3):
                advance_month(state)
                staff.synchronize(game, state, monthly=True)
            self.assertEqual(draw.call_count, 6, 'Ordinary one-person and large two-person cities each get one monthly roll')
            self.assertIsNone(state.extension['civil_staff']['cities']['one']['candidate'])
            advance_month(state)
            staff.synchronize(game, state, monthly=True)
            self.assertEqual(draw.call_count, 6, 'The fourth eligible check is guaranteed without another roll')
        for key in ('one', 'capital'):
            self.assertIsNotNone(state.extension['civil_staff']['cities'][key]['candidate'])
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        advance_month(state, 2)
        with patch.object(staff, '_draw', return_value=50):
            staff.synchronize(game, state, monthly=True)
        self.assertIsNotNone(state.extension['civil_staff']['cities']['one']['candidate'])
        self.assertIsNone(state.extension['civil_staff']['cities']['capital']['candidate'])

    def test_expiry_rejection_and_filled_roster_clear_offer_with_persistent_cooldown(self):
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        initial = state.extension['civil_staff']['cities']['empty']['candidate']['id']
        advance_month(state, 3)
        staff.synchronize(game, state, monthly=True)
        row = state.extension['civil_staff']['cities']['empty']
        self.assertIsNone(row['candidate'])
        self.assertEqual(row['cooldown_until_month'], staff.month_index(state)+3)
        frozen = deepcopy(state)
        staff.synchronize(game, state, monthly=True)
        self.assertEqual(state, frozen)
        advance_month(state, 3)
        staff.synchronize(game, state, monthly=True)
        self.assertNotEqual(row['candidate']['id'], initial)
        candidate = row['candidate']['id']
        state.cities['empty'].action_used = True
        gold = state.cities['empty'].gold
        staff.reject(game, state, 'empty', candidate, 'one')
        self.assertTrue(state.cities['empty'].action_used)
        self.assertEqual(state.cities['empty'].gold, gold)
        self.assertIsNone(row['candidate'])
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        state.cities['empty'].roster.officer_ids = [3, 4]
        staff.synchronize(game, state)
        self.assertIsNone(state.extension['civil_staff']['cities']['empty']['candidate'])
        self.assertEqual(state.events[-1]['details']['reason'], 'filled')

    def test_new_owner_or_new_zero_count_waits_at_least_thirty_days(self):
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        state.day, state.turn = 11, 2
        state.cities['neutral'].owner = 'one'
        staff.synchronize(game, state)
        self.assertIsNone(state.extension['civil_staff']['cities']['neutral']['candidate'])
        advance_month(state)
        staff.synchronize(game, state, monthly=True)
        self.assertIsNone(state.extension['civil_staff']['cities']['neutral']['candidate'])
        advance_month(state)
        staff.synchronize(game, state, monthly=True)
        self.assertIsNotNone(state.extension['civil_staff']['cities']['neutral']['candidate'])
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        state.day, state.turn = 11, 2
        state.officers[0].alive = False
        state.cities['one'].roster.officer_ids.clear()
        staff.synchronize(game, state)
        advance_month(state)
        staff.synchronize(game, state, monthly=True)
        self.assertIsNone(state.extension['civil_staff']['cities']['one']['candidate'])
        advance_month(state)
        staff.synchronize(game, state, monthly=True)
        self.assertIsNotNone(state.extension['civil_staff']['cities']['one']['candidate'])

    def test_salary_bonus_and_soldier_ledger_are_once_per_month_and_unpaid_staff_pause(self):
        game, state = fixture()
        person = open_and_hire(game, state)
        city = state.cities['empty']
        advance_month(state)
        before = (city.gold, city.grain, city.reserves, state.soldiers['recruited'])
        staff.synchronize(game, state, monthly=True)
        field = dict(commerce='gold', farming='grain', recruitment='reserves')[person['specialty']]
        base = dict(gold=100, grain=200, reserves=100)
        bonus = base[field]*(2+person['profile']['intellect']//20)//100
        expected = dict(gold=before[0]-5, grain=before[1], reserves=before[2])
        expected[field] += bonus
        self.assertEqual((city.gold, city.grain, city.reserves), tuple(expected.values()))
        self.assertEqual(state.soldiers['recruited']-before[3], bonus if field == 'reserves' else 0)
        salary = next(row for row in reversed(state.events) if row['kind'] == 'staff_salary')
        self.assertEqual(salary['details']['amount'], 5)
        self.assertEqual(salary['details']['paid'], 5)
        self.assertEqual(salary['details']['counts'], dict(staff=1, total_unpaid=0, cities=1))
        frozen = deepcopy(state)
        staff.synchronize(game, state, monthly=True)
        self.assertEqual(state, frozen)
        advance_month(state)
        city.gold = 0
        before = (city.gold, city.grain, city.reserves)
        staff.synchronize(game, state, monthly=True)
        self.assertFalse(person['working'])
        self.assertEqual(person['unpaid_months'], 1)
        self.assertEqual((city.gold, city.grain, city.reserves), before)
        advance_month(state)
        city.gold = 5
        staff.synchronize(game, state, monthly=True)
        self.assertTrue(person['working'])
        self.assertEqual(person['unpaid_months'], 0)
        staff.validate(game, state)

    def test_employees_follow_city_allegiance_without_becoming_historical_officers(self):
        game, state = fixture()
        person = open_and_hire(game, state)
        history = deepcopy(state.officers)
        state.cities['empty'].owner = 'two'
        staff.synchronize(game, state)
        self.assertEqual(person['owner'], 'two')
        self.assertFalse(person['working'])
        self.assertEqual(staff.view(game, state)['faction_counts'], {'one': 0, 'two': 1})
        event = next(row for row in reversed(state.events) if row['kind'] == 'staff_allegiance')
        self.assertEqual(event['factions'], ['one', 'two'])
        self.assertEqual(state.officers, history)
        staff.validate(game, state)

    def test_players_and_ai_use_same_hire_and_payroll_with_no_remote_event_flood(self):
        game, state = fixture()
        state.cities['empty'].owner = 'two'
        state.extension['civil_staff'] = staff.empty(game, state)
        staff.synchronize(game, state, opening=True)
        row = state.extension['civil_staff']['cities']['empty']
        self.assertIsNotNone(row['candidate'])
        self.assertFalse(any(event['city_ids'] == ['empty'] for event in state.events))
        state.phase = 'ai'
        candidate = row['candidate']['id']
        gold = state.cities['empty'].gold
        person = staff.hire(game, state, 'empty', candidate, 'two')
        self.assertEqual(state.cities['empty'].gold, gold-60)
        self.assertEqual(person['owner'], 'two')
        self.assertFalse(state.events)
        advance_month(state)
        staff.synchronize(game, state, monthly=True)
        self.assertEqual(state.cities['empty'].gold, gold-65 +
                         (4 if person['specialty'] == 'commerce' and person['profile']['intellect'] < 60 else
                          5 if person['specialty'] == 'commerce' else 0))
        self.assertFalse(any(event['kind'] == 'staff_salary' for event in state.events))
        staff.validate(game, state)

    def test_views_and_repeated_save_equivalent_state_do_not_consume_any_rng(self):
        game, state = fixture()
        staff.synchronize(game, state, opening=True)
        advance_month(state, 2)
        staff.synchronize(game, state, monthly=True)
        self.assertGreater(state.extension['civil_staff']['rng']['draws'], 0)
        self.assertEqual(vars(state.rng), dict(state=2026, draws=0))
        before = deepcopy(state)
        first = staff.view(game, state)
        second = staff.view(game, state)
        self.assertEqual(first, second)
        self.assertEqual(state, before)
        clone = deepcopy(state)
        staff.synchronize(game, clone, monthly=True)
        self.assertEqual(clone, state)
        first['cities']['empty']['candidate']['name'] = 'changed'
        self.assertEqual(state, before)

    def test_arrival_phase_defers_candidate_roll_but_not_once_only_payroll(self):
        game, state = fixture()
        person = open_and_hire(game, state)
        advance_month(state, 2)
        state.phase = 'arrivals'
        with patch.object(staff, '_draw', return_value=0) as draw:
            staff.synchronize(game, state, monthly=True)
            self.assertEqual(draw.call_count, 0)
            self.assertEqual(state.extension['civil_staff']['last_payroll_month'], staff.month_index(state))
            self.assertEqual(person['paid_month'], staff.month_index(state))
            self.assertNotEqual(state.extension['civil_staff']['cities']['one']['last_checked_month'], staff.month_index(state))
            state.phase = 'city'
            staff.synchronize(game, state)
            self.assertGreater(draw.call_count, 0)
            self.assertIsNotNone(state.extension['civil_staff']['cities']['one']['candidate'])
            gold = state.cities['empty'].gold
            staff.synchronize(game, state, monthly=True)
            self.assertEqual(state.cities['empty'].gold, gold)
        staff.validate(game, state)

    def test_zero_city_without_history_and_full_historical_guard_are_independent_conditions(self):
        game, state = fixture()
        # A reachable historical free officer cannot prevent the zero-actor
        # city from getting its one opening administrative hire opportunity.
        state.extension['test_free'] = {'empty': [5]}
        staff.synchronize(game, state, opening=True)
        self.assertIsNotNone(state.extension['civil_staff']['cities']['empty']['candidate'])
        person = staff.hire(game, state, 'empty', state.extension['civil_staff']['cities']['empty']['candidate']['id'], 'one')
        state.cities['empty'].action_used = False
        self.assertTrue(staff.view(game, state)['cities']['empty']['can_search'])
        person['working'] = False
        self.assertFalse(staff.view(game, state)['cities']['empty']['can_search'])

    def test_mid_command_ownership_sync_never_runs_monthly_checks_or_payroll(self):
        game, state = fixture()
        person = open_and_hire(game, state)
        advance_month(state, 2)
        state.cities['empty'].owner = 'two'
        before_money = {key: city.gold for key, city in state.cities.items()}
        before_random = deepcopy(state.extension['civil_staff']['rng'])
        before_payroll = state.extension['civil_staff']['last_payroll_month']
        staff.synchronize(game, state, monthly=True, checks=False)
        self.assertEqual(person['owner'], 'two')
        self.assertEqual({key: city.gold for key, city in state.cities.items()}, before_money)
        self.assertEqual(state.extension['civil_staff']['rng'], before_random)
        self.assertEqual(state.extension['civil_staff']['last_payroll_month'], before_payroll)
        self.assertIsNone(state.extension['civil_staff']['cities']['one']['candidate'])
        staff.validate(game, state)

    def test_generated_values_identity_noncombat_and_capacity_tampering_are_rejected(self):
        game, state = fixture()
        open_and_hire(game, state)
        staff.synchronize(game, state)
        staff.validate(game, state)
        for change in ('profile', 'troops', 'id', 'owner', 'counter', 'rng', 'fields'):
            bad = deepcopy(state)
            pool = bad.extension['civil_staff']
            person = next(iter(pool['people'].values()))
            if change == 'profile':person['profile']['intellect'] += 1
            elif change == 'troops':person['troops'] = 1
            elif change == 'id':person['id'] = 'san14-candidate-0001'
            elif change == 'owner':person['owner'] = 'two'
            elif change == 'counter':pool['next_id'] = 1
            elif change == 'rng':pool['rng']['state'] = True
            elif change == 'fields':person['hidden'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                staff.validate(game, bad)


if __name__ == '__main__':
    unittest.main()
