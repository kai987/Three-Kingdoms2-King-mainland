"""Reproducible controlled tactical runs through the existing observer engine."""
from copy import copy, deepcopy
from dataclasses import replace
from fractions import Fraction
from math import ceil
from concurrent.futures import ProcessPoolExecutor
from statistics import median, mean, quantiles

from common import HeadlessCampaign, open_game, to_csv
from remake import battle_experience, battle_reinforcements, battle_supply, grain_units
from remake.campaign import SeedRng

MATCHES = ((5000, 5000), (10000, 10000), (30000, 30000), (50000, 50000),
           (100000, 100000), (30000, 50000), (50000, 100000))
SOURCE, TARGET = 'jiangxia', 'nanjun'
BASE_SEED = 2026000
_BENCH = None


def setup(catalog):
    # Keep real terrain and effects. Isolate two forces from the surrounding AI
    # by using the engine's existing no-auto-attack rule in the fixture only.
    fixture = copy(catalog)
    fixture.data = dict(catalog.data, rules=dict(catalog.data['rules'], ai_max_attacks_per_turn=0))
    fixture.profiles = dict(catalog.profiles)
    state = open_game(fixture, BASE_SEED).state
    groups = []
    for key in (SOURCE, TARGET):
        city = state.cities[key]
        groups.append(tuple(sorted(city.roster.officer_ids)[:10]))
    for ident in groups[0] + groups[1]:
        profile = replace(state.officers[ident].profile, martial_strength=75, intellect=75,
                          virtue=70, terrain_affinity=0, health_max=90)
        fixture.profiles[ident] = profile
        officer = state.officers[ident]
        officer.profile, officer.health, officer.loyalty = profile, 90, 100
        officer.experience, officer.tier, officer.weapon_id, officer.armor_id = 0, 0, 0, 0
    for key in (SOURCE, TARGET):
        state.cities[key].grain = 500_000
        state.cities[key].gold = 0
        state.extension['domestic']['cities'][key]['morale'] = 70
    return fixture, state, groups


def _begin(fixture):
    global _BENCH
    _BENCH = setup(fixture)


def trial(job):
    attacker_total, defender_total, seed = job
    catalog, base, groups = _BENCH
    state = deepcopy(base)
    game = HeadlessCampaign(catalog, record_journal=False)
    state.seed, state.rng = seed, SeedRng(seed)
    deployed = []
    with grain_units.using(state):
        for key, group, strength in zip((SOURCE, TARGET), groups, (attacker_total, defender_total)):
            city = state.cities[key]
            original = sum(state.officers[i].troops for i in city.roster.officer_ids)
            for ident in city.roster.officer_ids:
                state.officers[ident].troops = 0
            deployed_ids = group[:ceil(strength / 10_000)]
            minimum, extra = divmod(strength, len(deployed_ids))
            for index, ident in enumerate(deployed_ids):
                state.officers[ident].troops = minimum + (index < extra)
            state.soldiers['initial'] += strength - original
            deployed.append(deployed_ids)
        game._start_expanded_battle(state, state.cities[SOURCE], state.cities[TARGET], deployed[0], paid=True)
        battle = state.battle
        game._resolve_ai_battle(state)
        supply = battle['extended']['supply']
        assert supply['settlement'] is not None
        assert state.battle is None and battle['outcome'] is not None
        debrief = result(catalog, battle, supply, deployed, job)
        return debrief


def outcome_reason(battle, supply):
    shortages = [side for side, row in supply['sides'].items()
                 if any(entry.get('missing', 0) for entry in row['journal'])]
    if shortages:
        return 'attacker_supply_exhausted' if 'attackers' in shortages else 'defender_supply_exhausted'
    if battle['extended'].get('withdrawn'):
        if battle['round'] > battle_supply.BUDGET_DAYS:
            return 'time_limit'
        return 'withdrew_' + battle['extended']['withdrawn']
    if battle['outcome'] == 'victory' and any(u['troops'] > 0 for u in battle['defenders']):
        return 'captured_objective'
    return {'victory': 'defense_without_active_units', 'defeat': 'attack_without_active_units',
            'retreat': 'both_without_active_units'}.get(battle['outcome'], battle['outcome'])


def result(catalog, battle, supply, deployed, job):
    attacker_total, defender_total, seed = job
    row = dict(case='controlled_real_tactical_ai', seed=seed, source_city_id=SOURCE,
               target_city_id=TARGET, attackers_initial=attacker_total, defenders_initial=defender_total,
               days_elapsed=min(battle_supply.BUDGET_DAYS, battle['round']),
               days_charged=supply['days'], outcome=battle['outcome'],
               termination=outcome_reason(battle, supply), reinforcements=len(battle_reinforcements.joined(battle)))
    experience, awards = battle_experience.result(battle, 'settled')
    row.update(experience_total_pool=experience['experience'], experience_awarded=sum(awards.values()),
               maximum_individual_experience=max(awards.values(), default=0))
    final = {unit['id']: unit for side in battle_supply.SIDES for unit in battle[side]}
    settled = {entry['side']: entry for entry in supply['settlement']}
    for side, initial, ids in zip(battle_supply.SIDES, job[:2], deployed):
        units = battle[side]
        origin_survivors = sum(final[i]['troops'] for i in ids)
        surrendered_troops = sum(battle['extended']['surrenders'].get(str(i),0) for i in ids)
        loss = initial - origin_survivors - surrendered_troops
        loyal_survivors = sum(u['troops'] for u in units if u['id'] in ids)
        replacement_count = initial - loyal_survivors
        provisions = supply['sides'][side]
        ration = provisions['consumed']
        burn = battle_supply.burned(provisions)
        assert provisions['loaded'] + provisions['received'] == settled[side]['grain'] + ration + burn
        escaped = side == battle['extended'].get('withdrawn')
        defected = sum(not any(unit['id'] == i for unit in units) and str(i) not in battle['extended']['surrenders'] for i in ids)
        cfg = catalog.data['rules']
        actions = ceil(Fraction(replacement_count, cfg['recruit_per_action']))
        row.update({f'{side}_{key}': val for key, val in dict(
            final=sum(u['troops'] for u in units), original_force_survivors=origin_survivors,
            original_side_survivors=loyal_survivors, original_side_replacement_count=replacement_count,
            surrendered_troops=surrendered_troops,
            losses=loss, loss_rate=loss/initial, initial_officers=len(ids), grain_rations=ration,
            grain_loaded=provisions['loaded'], grain_received=provisions['received'],
            grain_burned=burn, grain_remaining=settled[side]['grain'],
            grain_stored=settled[side]['stored'], grain_lost_at_settlement=settled[side]['lost'],
            defeated=sum(u['troops'] == 0 and str(u['id']) not in battle['extended']['surrenders'] for u in units),
            withdrawing=sum(u['troops'] > 0 for u in units) if escaped else 0, defected_out=defected,
            surrendered=sum(str(i) in battle['extended']['surrenders'] for i in ids),
            replacement_manual_actions=actions, replacement_gold=actions*cfg['recruit_gold_per_100'],
            replacement_grain=actions*grain_units.amount(cfg['recruit_grain_per_100']),
        ).items()})
    return row


def describe(rows):
    for attackers, defenders in MATCHES:
        bucket = [row for row in rows if (row['attackers_initial'], row['defenders_initial']) == (attackers, defenders)]
        for field, value in bucket[0].items():
            if not isinstance(value, (int, float)) or field in ('seed', 'attackers_initial', 'defenders_initial'):
                continue
            values = [row[field] for row in bucket]
            p10, *_, p90 = quantiles(values, n=10, method='inclusive') if len(values) > 1 else [values[0]] * 9
            yield dict(attackers_initial=attackers, defenders_initial=defenders, metric=field, n=len(values),
                       mean=mean(values), median=median(values), min=min(values), p10=p10, p90=p90, max=max(values))


def export(path, catalog, replicates, workers, opening_seed):
    jobs = [(a, d, opening_seed*1000 + i*replicates + k) for i, (a, d) in enumerate(MATCHES)
            for k in range(replicates)]
    if workers == 1:
        _begin(catalog)
        rows = [trial(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_begin, initargs=(catalog,)) as pool:
            rows = list(pool.map(trial, jobs, chunksize=2))
        _begin(catalog)
    assert all(trial(jobs[i*replicates]) == rows[i*replicates] for i in range(len(MATCHES)))
    to_csv(path / 'battle-simulation-results.csv', rows)
    to_csv(path / 'battle-simulation-statistics.csv', describe(rows))
    return dict(battle_trials=len(rows), full_receipts_reproduced=len(MATCHES),
                fixture_cities=[SOURCE, TARGET], automatic_reinforcement=False)
