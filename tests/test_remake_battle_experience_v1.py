"""Battle XP V1 golden vectors, campaign receipts and randomized invariants."""

from copy import deepcopy
from decimal import Decimal
import json
from math import isfinite
from pathlib import Path
from random import Random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import battle_experience_v1 as xp, battle_experience
from remake.campaign import Campaign
from remake.errors import GameError
from campaign_fixtures import controlled_catalog, reach_battle


ATTACK, DEFEND = xp.SIDES


def journal(attackers, defenders):
    return dict(version=1, opening=[[i, side, troops] for side, group in
                 ((ATTACK, attackers), (DEFEND, defenders)) for i, troops in group.items()], events=[])


def record(log, kind, *, day=1, **details):
    event = dict(id=len(log['events']) + 1, day=day, kind=kind, **details)
    xp.append(log, event)
    return event


def hit(log, actor, target, amount, **options):
    return record(log, 'damage', actor=actor, target=target, amount=amount, ordinary=True, **options)


def duel(log, actor, target, amount=1, maximum=100, **options):
    return record(log, 'duel', actor=actor, target=target, amount=amount, maximum=maximum, **options)


def convert(log, actor, target, amount, **options):
    return record(log, 'conversion', actor=actor, target=target, amount=amount, **options)


def force(start, size):
    return dict.fromkeys(range(start, start + size), 10_000)


def entries(report, side):
    return {row['id']: row for row in report['sides'][side]['officers']}


def table_case(kills, losses):
    log = journal(force(1, 8), force(101, 7))
    for i, loss in enumerate(losses):
        if loss:
            hit(log, 101 + i % 7, 1 + i, loss)
    total = 0
    for i, kill in enumerate(kills, 1):
        while kill:
            amount = min(kill, 10_000 - total % 10_000)
            hit(log, i, 101 + total // 10_000, amount)
            total += amount
            kill -= amount
    return xp.settle(log)[0]


class StandardCases(unittest.TestCase):
    def test_01_full_opening(self):
        log = journal(force(1, 10), force(101, 10))
        for i in range(10):
            hit(log, 1 + i, 101 + i, 50)
            hit(log, 101 + i, 1 + i, 50)
        report, _ = xp.settle(log)
        self.assertEqual((report['total_troops'], report['participants'], report['experience']), (200_000, 20, 1000))
        self.assertEqual([report['sides'][side]['experience'] for side in xp.SIDES], [500, 500])

    def test_02_zero_troop_duel(self):
        log = journal({0: 0}, {'clerk-000001': 0})
        duel(log, 0, 'clerk-000001', 50)
        report, awards = xp.settle(log)
        self.assertEqual((report['total_troops'], report['experience'], awards), (0, 2, {0: 1, 'clerk-000001': 1}))

    def test_03_idle_and_clean_retreat(self):
        log = journal(force(1, 10), force(101, 10))
        record(log, 'retreat', ident=1)
        report, awards = xp.settle(log)
        self.assertEqual((report['participants'], report['experience'], awards), (0, 0, {}))
        self.assertTrue(all(row['experience'] == 0 for side in xp.SIDES for row in entries(report, side).values()))

    def test_04_only_one_active_attacker(self):
        log = journal(force(1, 8), force(101, 3))
        for i in range(101, 104):
            hit(log, 1, i, 10_000)
        report, _ = xp.settle(log)
        result = entries(report, ATTACK)
        self.assertEqual([row['basis_points'] for row in result.values()], [10_000, *([0] * 7)])
        self.assertEqual(result[1]['troops'], 10_000)
        self.assertEqual(report['total_troops'], 40_000)

    def test_05_single_killer_golden_vector(self):
        report = table_case([30_000] + [0] * 7, [0, 500, 1000, 1500, 2000, 3000, 5000, 7000])
        attacker, defender = (report['sides'][side] for side in xp.SIDES)
        self.assertEqual((report['total_troops'], report['experience'], attacker['experience'],
                          defender['experience'], attacker['effective_weight']), (150_000, 750, 435, 315, 80))
        rows = tuple(entries(report, ATTACK).values())
        self.assertAlmostEqual(sum(row['raw'][-1] for row in rows), 34_658.358591, places=5)
        self.assertEqual([row['basis_points'] for row in rows], [5417, 532, 577, 611, 638, 682, 747, 796])
        self.assertEqual([row['experience'] for row in rows], [236, 23, 25, 26, 28, 30, 32, 35])

    def test_06_multiple_killers_golden_vector(self):
        report = table_case([10_000, 5000, 4000, 3000, 3000, 2000, 2000, 1000],
                            [5000, 500, 1000, 1500, 2000, 2500, 3000, 4500])
        self.assertEqual(report['sides'][ATTACK]['experience'], 435)
        rows = tuple(entries(report, ATTACK).values())
        self.assertEqual([row['basis_points'] for row in rows], [2380, 1355, 1229, 1092, 1117, 971, 989, 867])
        self.assertEqual([row['experience'] for row in rows], [104, 59, 53, 47, 49, 42, 43, 38])

    def test_07_conversion_exceeds_initial_deployment(self):
        log = journal(force(1, 10), force(101, 10))
        for i in range(10):
            duel(log, 1 + i, 101 + i)
        convert(log, 1, 101, 10_000)
        before = deepcopy(log)
        before['events'].pop()
        replay = xp.Replay(log)
        report, _ = xp.settle(log)
        self.assertEqual([sum(col.side == side for col in replay.columns.values()) for side in xp.SIDES], [11, 9])
        self.assertEqual(replay.total, 200_000)
        self.assertEqual(sum(replay.losses.values()), 0)
        self.assertEqual(report['experience'], xp.settle(before)[0]['experience'])
        self.assertEqual(entries(report, ATTACK)[1]['converted_troops'], 10_000)
        self.assertTrue(entries(report, DEFEND)[101]['eligible'])

    def test_08_pure_conversion(self):
        log = journal(force(1, 10), force(101, 10))
        convert(log, 1, 101, 10_000)
        report, awards = xp.settle(log)
        self.assertEqual((report['participants'], report['total_troops'], report['experience']), (2, 20_000, 100))
        self.assertEqual([report['sides'][side]['score'] for side in xp.SIDES], [22_000, 0])
        self.assertEqual(awards, {1: 90, 101: 10})
        self.assertFalse(entries(report, ATTACK)[101]['eligible'])

    def test_09_event_side_never_follows_final_side(self):
        log = journal(force(1, 2), force(101, 2))
        hit(log, 101, 1, 2000)
        hit(log, 2, 101, 1000)
        convert(log, 2, 101, 9000, day=2)
        hit(log, 101, 102, 3000, day=3)
        duel(log, 101, 102, 50, day=3)
        convert(log, 102, 101, 9000, day=4)
        hit(log, 101, 1, 1000, day=5)
        convert(log, 2, 101, 9000, day=6)
        report, awards = xp.settle(log)
        old, new = entries(report, DEFEND)[101], entries(report, ATTACK)[101]
        self.assertEqual((old['kills'], old['losses'], new['kills'], new['duel_hp']), (3000, 1000, 3000, 50))
        self.assertEqual((old['raw'][0], new['raw'][0], report['total_troops']), (1, 1, 40_000))
        self.assertEqual(awards[101], old['experience'] + new['experience'])

    def test_10_duel_defeat_is_one_loss_and_proportional(self):
        log = journal({1: 1000, 2: 1500}, {101: 6000})
        duel(log, 1, 101, 25)
        duel(log, 2, 101, 75)
        event = record(log, 'defeat', actor=2, target=101, amount=6000)
        xp.append(log, event)
        report, _ = xp.settle(log)
        defenders = entries(report, DEFEND)
        self.assertEqual((report['sides'][DEFEND]['losses'], defenders[101]['ordinary'],
                          defenders[101]['received_hp'], defenders[101]['raw'][-1]), (6000, 0, 100, 1000))
        self.assertEqual([row['kills'] for row in entries(report, ATTACK).values()], [1500, 4500])

    def test_11_return_preserves_the_same_cohort(self):
        log = journal({1: 10_000}, {101: 0})
        hit(log, 101, 1, 2000)
        record(log, 'retreat', ident=1)
        record(log, 'arrive', ident=1, side=ATTACK, amount=8000, day=2)
        duel(log, 1, 101, day=2)
        report, _ = xp.settle(log)
        row = entries(report, ATTACK)[1]
        self.assertEqual((report['total_troops'], row['losses'], row['raw'][0], row['raw'][5]), (10_000, 2000, 1, .8))

    def test_12_successive_reinforcement_cohorts(self):
        log = journal(force(1, 10), force(101, 10))
        for i in range(10):
            duel(log, 1 + i, 101 + i)
        size, pools = 0, [1000]
        for day, count in enumerate((2, 3, 5), 2):
            for i in range(count):
                record(log, 'arrive', ident=31 + size + i, side=ATTACK, amount=10_000, day=day)
            self.assertEqual(xp.settle(log)[0]['experience'], pools[-1])
            for i in range(count):
                duel(log, 31 + size + i, 101, day=day)
            size += count
            report, _ = xp.settle(log)
            self.assertEqual(report['total_troops'], 200_000 + size * 10_000)
            pools.append(report['experience'])
        self.assertEqual(pools, [1000, 1100, 1250, 1500])

    def test_13_zero_weight_small_pool_and_stable_ties(self):
        log = journal({i: 0 for i in range(1, 11)}, {101: 0})
        for i in range(11, 16):
            record(log, 'arrive', ident=i, side=ATTACK, amount=0)
        for i in range(15, 0, -1):
            record(log, 'effect', actor=i, target=101)
        settings = xp.Settings(weights=(0,) * 7)
        report, awards = xp.settle(log, settings)
        self.assertEqual((report['experience'], awards[1], awards[2], awards[101]), (2, 1, 0, 1))
        self.assertEqual(report['sides'][ATTACK]['effective_weight'], 0)
        self.assertEqual(sum(row['basis_points'] for row in entries(report, ATTACK).values()), 10_000)
        self.assertEqual(xp.apportion(10, {1: Decimal('4.6'), 2: Decimal('3.6'), 3: Decimal('1.8')}),
                         {1: 5, 2: 3, 3: 2})

    def test_13_zero_troop_conversion_and_total_wipes(self):
        log = journal({1: 500}, {101: 800, 102: 0})
        convert(log, 1, 102, 0)
        self.assertEqual(xp.settle(log)[0]['sides'][ATTACK]['score'], 2000)
        hit(log, 1, 101, 800)
        report, _ = xp.settle(log)
        self.assertEqual([report['sides'][side]['losses'] for side in xp.SIDES], [0, 800])
        record(log, 'loss', target=1, amount=500)
        report, _ = xp.settle(log)
        self.assertEqual([report['sides'][side]['losses'] for side in xp.SIDES], [500, 800])
        self.assertEqual(entries(report, ATTACK)[1]['raw'][5], 0)
        self.assertEqual(entries(report, ATTACK)[1]['raw'][-1], 0)

    def test_13_transfer_split_merge_replenish_and_early_death(self):
        log = journal({1: 8000, 2: 0}, {101: 100})
        record(log, 'loss', target=1, amount=2000)
        record(log, 'transfer', actor=1, target=2, amount=3000)
        duel(log, 2, 101)
        record(log, 'transfer', actor=2, target=1, amount=3000)
        duel(log, 1, 101)
        record(log, 'replenish', ident=1, amount=1000)
        self.assertEqual(xp.settle(log)[0]['total_troops'], 6100)
        duel(log, 1, 101)
        self.assertEqual(xp.settle(log)[0]['total_troops'], 7100)

    def test_13_invalid_and_duplicate_events_and_coefficients(self):
        for kind, fields in [('damage', dict(amount=-1, ordinary=True)),
                             ('damage', dict(amount=101, ordinary=True)),
                             ('duel', dict(amount=51, maximum=50)),
                             ('duel', dict(amount=1, maximum=0)),
                             ('duel', dict(amount=21, maximum=100, hp_before=20)),
                             ('conversion', dict(amount=200))]:
            with self.subTest(kind=kind, fields=fields):
                log = journal({1: 100}, {101: 100})
                record(log, kind, actor=1, target=101, **fields)
                with self.assertRaises(ValueError):
                    xp.settle(log)
        log = journal({1: 100}, {101: 100})
        event = hit(log, 1, 101, 10, day=2)
        xp.append(log, event)
        with self.assertRaises(ValueError):
            xp.append(log, dict(event, amount=11))
        with self.assertRaises(ValueError):
            xp.append(log, dict(event, id=4))
        record(log, 'retreat', ident=1, day=1)
        with self.assertRaises(ValueError):
            xp.settle(log)
        for options in [dict(weights=(0,) * 6), dict(conversion_troops=-1), dict(duel_received=float('inf')),
                        dict(guarantee=.3), dict(soldiers_per_point=0)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                xp.Settings(**options)


class SettlementProperties(unittest.TestCase):
    def test_1000_random_battles(self):
        rng = Random(20261124)
        for _ in range(1000):
            troops = {i: rng.randrange(10_001) for i in range(1, 1 + rng.randrange(2, 21))}
            sides = {i: ATTACK if i % 2 else DEFEND for i in troops}
            present = set(troops)
            log = journal({i: n for i, n in troops.items() if sides[i] == ATTACK},
                          {i: n for i, n in troops.items() if sides[i] == DEFEND})
            for day in range(1, rng.randrange(2, 81)):
                opponents = [(a, b) for a in sorted(present) for b in sorted(present) if sides[a] != sides[b]]
                if not opponents:
                    break
                actor, target = rng.choice(opponents)
                choice = rng.randrange(7)
                if choice == 0 and troops[target]:
                    loss = rng.randint(1, troops[target])
                    event = hit(log, actor, target, loss, day=day)
                    troops[target] -= loss
                elif choice == 1:
                    event = convert(log, actor, target, troops[target], day=day)
                    sides[target] = sides[actor]
                elif choice == 2:
                    event = record(log, 'retreat', ident=target, day=day)
                    present.remove(target)
                    record(log, 'arrive', ident=target, side=sides[target], amount=troops[target], day=day)
                    present.add(target)
                    continue
                elif choice == 3:
                    amount = rng.randrange(10_001 - troops[actor])
                    event = record(log, 'replenish', ident=actor, amount=amount, day=day)
                    troops[actor] += amount
                elif choice == 4:
                    new = len(troops) + 1
                    amount = rng.randrange(10_001)
                    troops[new], sides[new] = amount, sides[actor]
                    present.add(new)
                    event = record(log, 'arrive', ident=new, side=sides[new], amount=amount, day=day)
                else:
                    maximum = rng.randint(1, 150)
                    event = duel(log, actor, target, rng.randint(1, maximum), maximum=maximum, day=day)
                xp.append(log, event)
            result, awards = xp.settle(log)
            self.assertEqual((result, awards), xp.settle(json.loads(json.dumps(log, allow_nan=False))))
            self.assertEqual(result['experience'], sum(awards.values()))
            self.assertEqual(result['experience'], sum(side['experience'] for side in result['sides'].values()))
            self.assertTrue(all(type(n) is int and n >= 0 for n in awards.values()))
            for side in result['sides'].values():
                eligible = [row for row in side['officers'] if row['eligible']]
                self.assertEqual(side['experience'], sum(row['experience'] for row in eligible))
                self.assertEqual(sum(row['basis_points'] for row in eligible), 10_000 if eligible else 0)
                for row in side['officers']:
                    self.assertTrue(type(row['experience']) is int and row['experience'] >= 0)
                    if row['eligible']:
                        self.assertTrue(all(isfinite(value) for value in row['raw'] + row['normalized'] + row['weighted']))
                    else:
                        self.assertEqual((row['experience'], row['basis_points']), (0, 0))


class CampaignReceipt(unittest.TestCase):
    def test_awards_saved_once_through_real_settlement(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('depart', dict(source='xiangyang', target='nanyang', officers=[146]), game.revision)
        reach_battle(game)
        b = game.state.battle
        actor = b[ATTACK][0]
        target = b[DEFEND][0]
        game._attack_hit(game.state, actor, target, ATTACK)
        pending = game.command('retreat', dict(battle_id=b['id']), game.revision)['catalog']['battle_experience']
        report, awards = battle_experience.result(game.state.battle, 'pending')
        self.assertEqual(report, pending)
        restored = Campaign(game.catalog)
        self.assertEqual(restored.load_save(game.export_save(compact=True), 0)['catalog']['battle_experience'], report)
        before = {i: o.experience for i, o in restored.state.officers.items()}
        restored.command('settle', dict(battle_id=b['id']), restored.revision)
        items = restored.state.extension['events']['items']
        settled = next(row['details']['experience'] for row in reversed(items) if row['kind'] == 'battle_result')
        self.assertEqual(settled['status'], 'settled')
        for ident, amount in awards.items():
            self.assertEqual(restored.state.officers[ident].experience, min(49_999, before[ident] + 50 * amount))
        saved = restored.export_save(compact=True)
        reloaded = Campaign(game.catalog)
        reloaded.load_save(saved, 0)
        revision = reloaded.revision
        reloaded.command('settle', dict(battle_id=b['id']), revision - 1)
        self.assertEqual(reloaded.revision, revision)
        self.assertEqual(reloaded.export_save(compact=True), saved)

    def test_legacy_in_progress_retains_previous_experience_rules(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('depart', dict(source='xiangyang', target='nanyang', officers=[146]), game.revision)
        battle_id = reach_battle(game)
        battle = game.state.battle
        del battle['extended'][xp.FIELD]
        battle_experience.initialize_legacy(battle)
        restored = Campaign(game.catalog)
        restored.load_save(game.export_save(compact=True), 0)
        before = restored.state.officers[146].experience
        pending = restored.command('retreat', dict(battle_id=battle_id), restored.revision)
        self.assertNotIn('battle_experience', pending['catalog'])
        restored.command('settle', dict(battle_id=battle_id), restored.revision)
        self.assertEqual(restored.state.officers[146].experience, before + 50)

    def test_invalid_journal_rejected_without_replacing_state(self):
        game = Campaign(controlled_catalog())
        game.command('new', dict(faction='shu', seed=2026), 0)
        game.command('depart', dict(source='xiangyang', target='nanyang', officers=[146]), game.revision)
        reach_battle(game)
        record(game.state.battle['extended'][xp.FIELD], 'damage', actor=0, target=-1, amount=500, ordinary=True)
        restored = Campaign(game.catalog)
        with self.assertRaises(GameError):
            restored.load_save(game.export_save(), 0)
        self.assertIsNone(restored.state)


if __name__ == '__main__':
    unittest.main()
