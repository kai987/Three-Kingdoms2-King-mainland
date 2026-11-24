"""Record actual combat contribution and apportion experience once at settlement."""

from fractions import Fraction
from math import isqrt

from . import battle_experience_v1 as v1
from .officers import OFFICER_TROOP_CAP, integer, ref_sort_key


FIELD = 'experience_contributions'
V1_FIELD = v1.FIELD
SIDES = ('attackers', 'defenders')
RAW_PER_POINT = 50
MAX_POINTS = 50


initialize = v1.initialize


def initialize_legacy(battle):
    battle['extended'][FIELD] = dict(officers={}, conversions={}, injured=False, voluntary_withdrawal=False)


def _row(ledger, ident):
    return ledger['officers'].setdefault(str(ident), dict(damage=0))


def _opposing(battle, actor, target):
    return any(unit['id'] == target for unit in battle['attackers']) != any(
        unit['id'] == actor for unit in battle['attackers'])


def attack(battle, actor, target, losses=0, *, injured=False, ordinary=True, cause='attack'):
    """Commit an attributed attack after actual troop loss is known."""
    if V1_FIELD in battle['extended']:
        if losses and _opposing(battle, actor, target):
            v1.record(battle, 'damage', actor=actor, target=target, amount=losses, ordinary=ordinary, cause=cause)
        elif losses:
            v1.record(battle, 'loss', target=target, amount=losses, cause=cause)
        return
    ledger = battle['extended'].get(FIELD)
    if ledger is None:
        return
    _row(ledger, actor)['damage'] += losses
    _row(ledger, target)
    ledger['injured'] |= injured


def effect(battle, actor, target):
    v1.record(battle, 'effect', actor=actor, target=target)


def duel_hit(battle, state, actor, target, hp_before, hp_after):
    if hp_after < hp_before:
        # The engine stores 1 HP for a routed general. A hit that caused that
        # rout exhausted the remaining effective HP.
        remaining = 0 if hp_after == 1 else hp_after
        v1.record(battle, 'duel', actor=actor, target=target, amount=hp_before-remaining,
                  maximum=state.officers[target].profile.health_max, hp_before=hp_before)


def duel_defeat(battle, actor, target, amount, *, opposing):
    if V1_FIELD in battle['extended']:
        if opposing:
            events = battle['extended'][V1_FIELD]['events']
            cause = next((event['id'] for event in reversed(events)
                          if event['kind'] == 'duel' and event['actor'] == actor and event['target'] == target), None)
            v1.record(battle, 'defeat', actor=actor, target=target, amount=amount, cause_event=cause)
        elif amount:
            # The tactical unit is cleared immediately after this receipt.
            v1.record(battle, 'defeat_self', target=target, amount=amount, cause='duel_self_damage')
    elif opposing:
        attack(battle, actor, target, amount)


def arrive(battle, side, unit):
    v1.record(battle, 'arrive', ident=unit['id'], side=side, amount=unit['troops'])


def depart(battle, ident):
    v1.record(battle, 'retreat', ident=ident)


def withdraw_side(battle):
    if V1_FIELD in battle['extended']:
        for unit in battle[battle['extended']['withdrawn']]:
            if str(unit['id']) not in battle['extended']['surrenders']:
                depart(battle, unit['id'])


def voluntary_withdrawal(battle):
    withdraw_side(battle)
    ledger = battle['extended'].get(FIELD)
    if ledger is not None:
        ledger['voluntary_withdrawal'] = True


def _original_side(battle, ident, current):
    return battle['extended'].get('defections', {}).get(str(ident), {}).get('original_side', current)


def convert(battle, actor, target, foe):
    if V1_FIELD in battle['extended']:
        v1.record(battle, 'conversion', actor=actor['id'], target=target['id'], amount=target['troops'])
        return
    ledger = battle['extended'].get(FIELD)
    if ledger is None:
        return
    attack(battle, actor['id'], target['id'])
    # Credit each original enemy unit only once. A turncoat cannot repeatedly
    # earn or generate conversion shares by switching back and forth.
    if _original_side(battle, target['id'], foe) == foe:
        total = sum(unit['troops'] for unit in battle[foe])
        ledger['conversions'].setdefault(str(target['id']), dict(
            actor=str(actor['id']), troops=target['troops'], enemy_total=total))


def _median_twice(values):
    ordered = sorted(values)
    size = len(ordered)
    return ordered[(size - 1) // 2] + ordered[size // 2]


def _strength(state, units):
    profiles = [state.officers[unit['id']].profile for unit in units]
    troops = [unit['start'] for unit in units]
    return (sum(troops), _median_twice(troops), *(
        _median_twice(getattr(profile, field) for profile in profiles)
        for field in ('martial_strength', 'intellect', 'virtue')))


def _side_budget(state, battle, groups):
    from .battle_reinforcements import joined
    reinforcements = joined(battle)
    first, second = (_strength(state, [unit for unit in groups[side] if str(unit['id']) not in reinforcements])
                     for side in SIDES)
    balance = advantage = Fraction()
    for a, b, weight in zip(first, second, (4, 3, 1, 1, 1)):
        if max(a, b):
            balance += Fraction(weight * min(a, b), max(a, b))
            advantage += Fraction(weight * (a - b), max(a, b))
        else:
            balance += weight
    balance /= 10
    advantage /= 10
    winner = {'victory': 1, 'defeat': -1}.get(battle['outcome'], 0)
    # 10,000 evenly matched soldiers on each side start at 40 points per
    # side. A smaller opponent, weaker typical unit, or weaker median stats
    # all reduce the pool. An upset raises it for both sides equally.
    points = (Fraction(isqrt(first[0] * second[0]), 250)
              * (1 + balance) / 2 * (1 - winner * advantage / 4))
    sizes = [len(groups[side]) for side in SIDES]
    return min(MAX_POINTS * min(sizes), max(max(sizes), int(points + Fraction(1, 2))))


def _weight(unit, entries, surrendered, enemy_troops):
    row = entries.get(str(unit['id']), {})
    damage = row.get('damage', 0)
    lost = unit['start'] - unit['troops'] - surrendered.get(str(unit['id']), 0)
    if damage:
        quality = Fraction(damage, damage + lost)
        return 2 + Fraction(8 * damage, max(1, enemy_troops)) * (1 + 2 * quality)
    if lost:
        return Fraction(unit['start'] - lost, unit['start'])
    return Fraction(5, 4) if row else Fraction(1)


def _distribute(amount, weights, limits, totals):
    """Allocate by largest remainders, redistributing points above the cap."""
    while amount:
        eligible = {ident: weight for ident, weight in weights.items() if totals[ident] < limits[ident]}
        if not eligible:
            break
        total_weight = sum(eligible.values())
        if not total_weight:
            eligible = dict.fromkeys(eligible, Fraction(1))
            total_weight = len(eligible)
        quotas = {ident: amount * weight / total_weight for ident, weight in eligible.items()}
        capped = [ident for ident, quota in quotas.items() if quota >= limits[ident] - totals[ident]]
        if capped:
            for ident in capped:
                amount -= limits[ident] - totals[ident]
                totals[ident] = limits[ident]
            continue
        floors = {ident: int(quota) for ident, quota in quotas.items()}
        remainder = amount - sum(floors.values())
        order = sorted(quotas, key=lambda ident: (floors[ident] - quotas[ident], ref_sort_key(ident)))
        for ident, points in floors.items():
            totals[ident] += points
        for ident in order[:remainder]:
            totals[ident] += 1
        return 0
    return amount


def awards(state, battle, losses):
    """Return integer points of displayed experience for the original rosters."""
    ledger = battle['extended'][FIELD]
    groups = {side: [] for side in SIDES}
    for side in SIDES:
        for unit in battle[side]:
            groups[_original_side(battle, unit['id'], side)].append(unit)
    if not all(groups.values()):
        return {}
    if ledger['voluntary_withdrawal'] and not losses and not ledger['injured']:
        return {unit['id']: 1 for units in groups.values() for unit in units}

    budget = _side_budget(state, battle, groups)
    totals = {unit['id']: 1 for units in groups.values() for unit in units}
    limits = dict.fromkeys(totals, MAX_POINTS)
    surrendered = battle['extended']['surrenders']
    for side, foe in zip(SIDES, reversed(SIDES)):
        ids = {str(unit['id']): unit['id'] for unit in groups[side]}
        bonus_weights = {}
        for conversion in ledger['conversions'].values():
            actor = ids.get(conversion['actor'])
            if actor is not None:
                bonus_weights[actor] = bonus_weights.get(actor, Fraction()) + Fraction(
                    conversion['troops'], conversion['enemy_total'])
        remaining = budget - len(ids)
        # A conversion moving half the enemy's standing troops reserves half
        # the side's budget for its initiator, before normal combat shares.
        bonuses = {ident: max(Fraction(), budget * share - totals[ident])
                   for ident, share in bonus_weights.items()}
        bonus = min(remaining, int(sum(bonuses.values())))
        unused = _distribute(bonus, bonuses, limits, totals)
        enemy_troops = sum(unit['start'] for unit in groups[foe])
        weights = {}
        for unit in groups[side]:
            ident = unit['id']
            # The captured share already pays for a conversion-only effort.
            # Actual damage can still earn part of the combat remainder.
            weights[ident] = (Fraction() if ident in bonuses and bonuses[ident]
                              and not ledger['officers'][str(ident)]['damage'] else
                              _weight(unit, ledger['officers'], surrendered, enemy_troops))
        _distribute(remaining - bonus + unused, weights, limits, totals)
    return totals


def result(battle, status):
    report, awards = v1.settle(battle['extended'][V1_FIELD])
    report.update(battle_id=battle['id'], status=status)
    return report, awards


def archive_report(report, applied):
    """Persist display scores without changing the checksum across JSON clients."""
    def encode(value):
        if type(value) is float:
            return str(value)
        if isinstance(value, list):
            return [encode(item) for item in value]
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        return value

    return dict(encode(report), applied=applied)


def validate_load(battle):
    if V1_FIELD not in battle['extended']:
        return
    replay = v1.Replay(battle['extended'][V1_FIELD])
    deployed = {unit['id']: side for side in SIDES for unit in battle[side]}
    present = {ident for ident, column in replay.columns.items() if column.present}
    if (FIELD in battle['extended'] or replay.day > battle['round']
            or not present <= deployed.keys() <= replay.columns.keys()
            or any(replay.columns[ident].side != side for ident, side in deployed.items())):
        raise ValueError('Experience journal and battle disagree')


def validate(battle):
    if FIELD not in battle['extended']:
        return
    ledger = battle['extended'][FIELD]
    if (not isinstance(ledger, dict) or set(ledger) != {'officers', 'conversions', 'injured', 'voluntary_withdrawal'}
            or type(ledger['injured']) is not bool or type(ledger['voluntary_withdrawal']) is not bool
            or ledger['voluntary_withdrawal'] and battle['extended']['withdrawn'] not in SIDES):
        raise ValueError('Invalid battle experience ledger')
    units = {str(unit['id']): (side, unit) for side in SIDES for unit in battle[side]}
    casualties = sum(unit['start'] - unit['troops'] - battle['extended']['surrenders'].get(key, 0)
                     for key, (_, unit) in units.items())
    entries, conversions = ledger['officers'], ledger['conversions']
    for records in (entries, conversions):
        if not isinstance(records, dict) or not records.keys() <= units.keys():
            raise ValueError('Invalid experience participants')
    for entry in entries.values():
        if not isinstance(entry, dict) or set(entry) != {'damage'}:
            raise ValueError('Invalid experience contribution')
        integer(entry['damage'], 0, casualties, 'attributed battle losses')
    if sum(entry['damage'] for entry in entries.values()) > casualties:
        raise ValueError('Battle damage counted more than once')
    for key, record in conversions.items():
        if (not isinstance(record, dict) or set(record) != {'actor', 'troops', 'enemy_total'}
                or not isinstance(record['actor'], str) or record['actor'] not in entries or key not in entries
                or key not in battle['extended'].get('defections', {}) or record['actor'] == key):
            raise ValueError('Invalid conversion experience')
        integer(record['troops'], 1, units[key][1]['start'], 'converted troops')
        integer(record['enemy_total'], record['troops'], len(units) * OFFICER_TROOP_CAP, 'conversion army size')
