"""Deterministic AI policies; no changes to player stats, resources or RNG."""
from copy import deepcopy

DIFFICULTIES = ('easy', 'normal', 'hard')
_POLICIES = {
    'easy': dict(attack_ratio_percent=150, min_attack_troops=150,
        guard_ratio_percent=40, min_guard_troops=150, max_route_loss_percent=35,
        max_route_turns=8, plan_horizon_turns=3, max_attack_sources=1,
        max_attacks=1, tactic_depth=0, tactic_threshold_percent=140),
    'normal': dict(attack_ratio_percent=125, min_attack_troops=150,
        guard_ratio_percent=30, min_guard_troops=200, max_route_loss_percent=30,
        max_route_turns=12, plan_horizon_turns=6, max_attack_sources=2,
        max_attacks=3, tactic_depth=1, tactic_threshold_percent=115),
    'hard': dict(attack_ratio_percent=110, min_attack_troops=150,
        guard_ratio_percent=25, min_guard_troops=250, max_route_loss_percent=25,
        max_route_turns=18, plan_horizon_turns=9, max_attack_sources=3,
        max_attacks=6, tactic_depth=2, tactic_threshold_percent=100),
}


def get_settings(state):
    difficulty = state.extension.get('difficulty', 'normal')
    if difficulty not in DIFFICULTIES:
        raise ValueError('Unknown campaign difficulty')
    return deepcopy(_POLICIES[difficulty])


def attack_budget(catalog, state):
    base = catalog.data['rules']['ai_max_attacks_per_turn']
    if not base:
        return 0
    difficulty = state.extension.get('difficulty', 'normal')
    get_settings(state)
    return min(12, max(1, base // 3) if difficulty == 'easy'
               else base * 2 if difficulty == 'hard' else base)


def catalog_choices():
    return [dict(id=key, **deepcopy(values)) for key, values in _POLICIES.items()]
