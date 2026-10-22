"""Deterministic battle choices over the same legal actions used by the player.

Scores describe expected effects, never sampled future results. No candidate
reads or advances the campaign RNG, and neither side receives hidden bonuses.
"""


def _support(battle, unit):
    return battle['extended']['support'][str(unit['id'])]


def _active(battle, side):
    return [unit for unit in battle[side] if unit['troops'] > 0
            and _support(battle, unit)['health'] > 0
            and str(unit['id']) not in battle['extended']['surrenders']]


def tactic_reason(state, battle, actor, target, own, foe, terrain, tactic):
    """Player-compatible legality; usefulness (e.g. an empty granary) is scored."""
    if state.phase != 'battle' or battle['outcome']:
        return '当前没有待操作的战斗。'
    if battle['extended']['duel']:
        return '请先完成或退出当前单挑。'
    if actor not in _active(battle, own) or target not in _active(battle, foe):
        return '请选择未行动的本方部队与有效敌军。'
    _, cost, effect, _ = tactic
    support = _support(battle, actor)
    if support['stunned']:
        return '该部队受扰乱，不能施计；可执行普通行动恢复。'
    if support['energy'] < cost:
        return '计略气力不足。'
    if effect in {'water', 'chain', 'flood'} and terrain != 'water':
        return '此计略需要水地形。'
    if effect == 'rock' and terrain != 'mountain':
        return '落石需要山地形。'
    if effect in {'fire', 'inferno', 'trap'} and terrain == 'water':
        return '该地形不能使用此计略。'
    if effect == 'ambush' and (actor['troops'] < 100 or battle['extended']['ambush']):
        return '设伏需要至少100兵，且当前没有伏兵。'
    return ''


def legal_tactics(state, battle, actor, target, own, foe, terrain, tactics):
    return [index for index, tactic in enumerate(tactics)
            if not tactic_reason(state, battle, actor, target, own, foe, terrain, tactic)]


def expected_attack(battle, actor, target, damage_percent=32):
    """Average all 21 ordinary damage spreads without consuming a random draw."""
    denominator = (target['martial'] + 80) * 10000
    base = actor['troops'] * (actor['martial'] + 40) * damage_percent
    guarded = _support(battle, target)['guard'] > 0
    values = [min(target['troops'], max(1, base * spread // denominator))
              for spread in range(90, 111)]
    if guarded:
        values = [max(1, value // 2) for value in values]
    return sum(values) / len(values)


def _chance(state, actor, target, effect):
    profile, opponent = state.officers[actor['id']].profile, state.officers[target['id']]
    if effect in {'ambush', 'guard'}:
        return 1.0
    if effect == 'surrender':
        return max(5, min(80, 40 + (profile.virtue - opponent.loyalty) // 2)) / 100
    return max(10, min(95, 60 + (profile.intellect - opponent.profile.intellect) // 2)) / 100


def _loss_value(unit, amount):
    # Routing a unit also removes its future actions. No fictitious troops are
    # added to the actual result; this is only a deterministic choice weight.
    return min(unit['troops'], amount) + (24 if amount >= unit['troops'] else 0)


def _tactic_value(state, battle, actor, target, own, foe, terrain, tactic, attack):
    _, cost, effect, _ = tactic
    enemies, friends = _active(battle, foe), _active(battle, own)
    profile = state.officers[actor['id']].profile
    chance = _chance(state, actor, target, effect)
    ordered = [target] + [unit for unit in enemies if unit is not target]
    threat = max((attack(enemy, friend)
                  for enemy in enemies for friend in friends), default=0)
    if effect == 'supply':
        city = state.cities[battle['target'] if foe == 'defenders' else battle['source']]
        loss = min(city.grain, max(1, city.grain // 8 + profile.intellect))
        value = loss / 12
    elif effect == 'guard':
        value = 0 if _support(battle, actor)['guard'] else min(actor['troops'], threat) * .85
    elif effect == 'ambush':
        value = max((min(enemy['troops'], profile.intellect * 2)
                     for enemy in enemies), default=0) * .85
    elif effect in {'confuse', 'chain'}:
        victims = ordered[:1 if effect == 'confuse' else 3]
        value = sum(max((attack(unit, friend)
                         for friend in friends), default=0)
                    for unit in victims if not _support(battle, unit)['stunned'])
    elif effect == 'surrender':
        value = _loss_value(target, target['troops'])
    else:
        victims = ordered[:3 if effect == 'area' else 2 if effect == 'crossbow'
                          else 20 if effect in {'flood', 'inferno'} else 1]
        value = 0
        for unit in victims:
            damage = 0 if effect == 'trap' else sum(
                min(unit['troops'], max(1, profile.intellect * 2 + spread))
                for spread in range(31)) / 31
            if effect in {'trap', 'rock'}:
                health, injury = _support(battle, unit)['health'], max(1, profile.intellect // 4)
                if health - injury <= 1:
                    damage = unit['troops']
                else:
                    # Repeated health damage matters even before the final rout.
                    damage += (unit['troops'] - damage) * injury / max(1, health - 1) * .4
            value += _loss_value(unit, damage)
            if effect == 'feint' and not _support(battle, unit)['stunned']:
                value += max((attack(unit, friend)
                              for friend in friends), default=0) * max(0, 1 - damage / unit['troops'])
    return value * chance - cost * 1.8


def candidates(state, battle, own, foe, terrain, tactics, *, damage_percent=32,
               depth=1, responding=False, used=None):
    """Enumerate real unit/target/tactic choices; ties are stable numeric IDs."""
    if state.phase != 'battle' or battle['outcome'] or battle['extended']['duel']:
        return []
    spent = set(() if responding else battle['used'] if used is None else used)
    friends, enemies = _active(battle, own), _active(battle, foe)
    # Damage averages are reused by every tactic score; the candidate search
    # stays bounded even when both sides deploy the maximum ten units.
    averages={(a['id'],t['id']):expected_attack(battle,a,t,damage_percent)
              for first,second in ((friends,enemies),(enemies,friends)) for a in first for t in second}
    attack=lambda a,t:averages[(a['id'],t['id'])]
    rows = []
    for actor in friends:
        if actor['id'] in spent:
            continue
        support = _support(battle, actor)
        for target in enemies:
            damage = 0 if support['stunned'] else attack(actor, target)
            rows.append(dict(kind='attack', actor=actor['id'], target=target['id'],
                             tactic=None, score=_loss_value(target, damage) if damage else 0))
            if depth <= 0:
                continue
            for tid in legal_tactics(state, battle, actor, target, own, foe, terrain, tactics):
                value = _tactic_value(state, battle, actor, target, own, foe, terrain,
                                      tactics[tid], attack)
                if depth >= 2:
                    # A primary action receives one real enemy response. Prefer
                    # protection/disruption when a weak unit would otherwise rout.
                    effect = tactics[tid][2]
                    danger = max((attack(enemy, actor)
                                  for enemy in enemies), default=0)
                    useful_status=(effect=='ambush' or effect=='guard' and not support['guard']
                        or effect in {'confuse','chain','feint'} and not _support(battle,target)['stunned'])
                    if not responding and useful_status:
                        value += min(actor['troops'], danger) * (.35 if effect != 'ambush' else .55)
                    if effect in {'trap', 'rock'} and _support(battle, target)['health'] <= max(1, state.officers[actor['id']].profile.intellect // 4) + 1:
                        value += 20
                rows.append(dict(kind='tactic', actor=actor['id'], target=target['id'],
                                 tactic=tid, score=value))
    return sorted(rows, key=lambda row: (-row['score'], row['actor'], row['target'],
                                        -1 if row['tactic'] is None else row['tactic']))


def choose_action(state, battle, own, foe, terrain, tactics, *, settings=None,
                  damage_percent=32, responding=False, used=None):
    settings = settings or {}
    rows = candidates(state, battle, own, foe, terrain, tactics,
                      damage_percent=damage_percent, depth=settings.get('tactic_depth', 1),
                      responding=responding, used=used)
    ordinary = next((row for row in rows if row['kind'] == 'attack'), None)
    tactical = next((row for row in rows if row['kind'] == 'tactic'), None)
    threshold = settings.get('tactic_threshold_percent', 115) / 100
    if tactical and tactical['score'] > 0 and (ordinary is None or tactical['score'] >= ordinary['score'] * threshold):
        return tactical
    return ordinary
