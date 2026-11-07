"""Controlled actual-catalog saves for visible fire-arrow/conversion UI checks.

This is not a natural historical opening or AI result. The existing soldier
fixture creates real208-10 armies using public allocation and the ordinary
battle initializer. This fixture arranges legal noncastle cells and, only for
the two conversion scenes, explicitly sets one non-ruler's current loyalty to
71 or70. Source catalog profiles, cities, portraits and ROM remain untouched.
The production loader verifies every export; browsers import the checksummed
JSON through the visible save-file control without page-state injection.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tests')]
from remake import tactic_effects, tactical_ai
from remake.campaign import SeedRng
from remake.campaign_expansion import TACTICS
from browser_soldier_fixture import _base, _contact, _save


def fixture(kind='fire'):
    if kind not in ('fire', 'conversion71', 'conversion70'):
        raise ValueError('Unknown controlled tactic-effect scene')
    tid = 5 if kind == 'fire' else 8
    loyalty = None if kind == 'fire' else 71 if kind == 'conversion71' else 70
    game, _, actor = _base(20261029)

    def prepare(current):
        battle = current.state.battle
        if tid == 5:
            target = battle['defenders'][0]['id']
        else:
            target = next(unit['id'] for unit in battle['defenders']
                          if unit['id'] not in current.state.extension['leaders'].values())
            current.state.officers[target].loyalty = loyalty
        first, second = _contact(current, actor, target)
        caster = next(unit for unit in battle['attackers'] if unit['id'] == actor)
        victim = next(unit for unit in battle['defenders'] if unit['id'] == target)
        reason = tactical_ai.tactic_reason(current.state, battle, caster, victim,
            'attackers', 'defenders', current.catalog.map_cities[battle['target']]['terrain'], TACTICS[tid])
        if reason:
            raise AssertionError('Controlled scene must use a real legal tactic: '+reason)
        return target, first, second, tactic_effects.preview(current.state, battle, caster,
            victim, 'attackers', 'defenders', tid)

    target, first, second, quote = prepare(game)
    if quote['success_percent']:
        # Pick a documented ordinary starting seed whose real first success
        # roll passes. No future roll is written into the browser or save.
        expected_rng = deepcopy(game.state.rng)
        if expected_rng.next()%100 >= quote['success_percent']:
            seed = next(seed for seed in range(1, 10000)
                        if SeedRng(seed).next()%100 < quote['success_percent'])
            game, _, actor = _base(seed)
            target, first, second, quote = prepare(game)
    return _save(game, kind=kind, tactic=tid, actor=actor, target=target,
        actor_cell=dict(x=first[0], y=first[1]), target_cell=dict(x=second[0], y=second[1]),
        source='208-10 actual campaign; explicitly controlled legal cells and stated current loyalty',
        target_loyalty=game.state.officers[target].loyalty, seed=game.state.seed,
        preview=quote, expected_success=bool(quote['success_percent']))


if __name__ == '__main__':
    print(json.dumps(fixture(sys.argv[1] if len(sys.argv) > 1 else 'fire'),
                     ensure_ascii=False, separators=(',', ':')))
