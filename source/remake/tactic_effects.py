"""Pure original arithmetic for shared tactic gates and audited effects.

B243/B6F0 fire-arrow arithmetic and B72B conversion thresholds are recovered
from the pinned original. All actors share the original player bonus10; the
AI-only original difficulty bonus is not imported. The campaign's seeded modulo
sampling and nonspatial legacy gate remain adaptations. These helpers never
initialize supply, spend maneuver points or advance random state.
"""
from .march_supply import LIMIT
from .officers import experience_tier

SCHEMA = 'tk2-tactic-effect-preview-v1'
GENERAL_TACTICS = tuple(tid for tid in range(16) if tid not in (8,11))
DISTANCE_BYTES = (15,10,5,0,251,246)  # physical12 B85A, original signed-looking bytes.


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Invalid tactic '+label)
    return value


def conversion_threshold(intellect, virtue, actor_tier, loyalty, target_tier):
    """Original B72B, for bounded remake profiles and level indices0..7.

    Loyalty>=71 fails before sampling, after the caller has paid its AP. The
    original's byte-carry corner cases cannot arise in this0..99 stat domain.
    """
    for value, label in ((intellect, 'intellect'), (virtue, 'virtue')):
        _integer(value, 0, 99, label)
    _integer(loyalty, 0, 100, 'loyalty')  # Current rulers may carry the internal100 sentinel.
    _integer(actor_tier, 0, 7, 'actor tier')
    _integer(target_tier, 0, 7, 'target tier')
    if loyalty >= 71:
        return 0
    base = 60 if loyalty < 31 else 30 if loyalty < 51 else 10
    return base+(intellect+virtue)//10+2*max(actor_tier-target_tier, 0)


def fire_arrow_requested(grain, intellect, roll):
    """B251..B2C6: two separately floored terms, before saturation."""
    _integer(grain, 0, LIMIT, 'army grain')
    _integer(intellect, 0, 99, 'intellect')
    _integer(roll, 0, 4, 'fire-arrow roll')
    return grain*(10+roll)//100+intellect//5


def _tier(officer):
    value = getattr(officer, 'tier', None)
    return experience_tier(getattr(officer, 'experience', 0)) if value is None else value


def conversion_chance(actor, target):
    return conversion_threshold(actor.profile.intellect, actor.profile.virtue,
                                _tier(actor), target.loyalty, _tier(target))


def general_threshold(intellect,target_intellect,actor_tier,target_tier,distance):
    """B7BE with the original player's bonus10 shared by player and AI.

    Preserve byte additions and the final sign test. Legal high intellect and
    level inputs can set bit7:127 clamps to95, but128 becomes5, not95. No draw
    is possible at distance>=6. Original AI difficulty bonuses5/10/20 are a
    controller-specific difference deliberately excluded from this shared rule.
    """
    _integer(intellect,0,99,'intellect')
    _integer(target_intellect,0,99,'target intellect')
    _integer(actor_tier,0,7,'actor tier')
    _integer(target_tier,0,7,'target tier')
    _integer(distance,0,255,'distance')
    if distance>=6:
        return 0
    value=(DISTANCE_BYTES[distance]+max(intellect-target_intellect,0))&255
    value=(value+2*max(actor_tier-target_tier,0))&255
    value=(value+10)&255
    if value&128:
        value=0
    return max(5,min(95,value))


def general_chance(actor,target,*,distance=None):
    """Explicit-distance native gate, or the unchanged nongrid legacy model."""
    if distance is None:
        return max(10,min(95,60+(actor.profile.intellect-target.profile.intellect)//2))
    return general_threshold(actor.profile.intellect,target.profile.intellect,
                             _tier(actor),_tier(target),distance)


def _distance(battle,actor,target):
    row=battle.get('extended',{}).get('tactical')
    if row is None:
        return None
    positions=row['positions']
    first,second=positions[str(actor['id'])],positions[str(target['id'])]
    for point in (first,second):
        _integer(point['x'],0,30,'visible x')
        _integer(point['y'],0,18,'visible y')
    # The authoritative grid has already removed packed metadata row15.
    return max(abs(first['x']-second['x']),abs(first['y']-second['y']))


def success_chance(state,battle,actor,target):
    """Shared pure quote for actual effects, AI estimates and UI forecasts."""
    return general_chance(state.officers[actor['id']],state.officers[target['id']],
                          distance=_distance(battle,actor,target))


def preview(state, battle, actor, target, own, foe, tid):
    """Pure actor/target quote; legality and maneuver payment remain separate."""
    if type(tid) is not int or tid not in (*GENERAL_TACTICS,8):
        return None
    from . import battle_supply
    caster, opponent = state.officers[actor['id']], state.officers[target['id']]
    chance=success_chance(state,battle,actor,target) if tid!=8 else conversion_chance(caster,opponent)
    common=dict(schema=SCHEMA,tactic=tid,success_percent=chance)
    if tid!=8:
        distance=_distance(battle,actor,target)
        common['success_gate']='legacy_nonspatial' if distance is None else 'shared_native'
        if distance is not None:
            common.update(distance=distance,shared_bonus=10)
    if tid not in (2,5,8,10,15):
        return common
    if tid == 2:
        from . import battle_conditions
        return dict(common,
                    failure_without_rng=chance==0,failure_rng_draws=int(chance>0),success_rng_draws=int(chance>0),
                    condition='phantom',condition_count=battle_conditions.duration(own),
                    target_count=battle_conditions.remaining(battle,target['id']))
    if tid == 10:
        from . import battle_conditions, battle_grid
        targets=[str(unit['id']) for unit in battle_grid.affected_units(battle,target,tid,foe)]
        return dict(common,
                    failure_without_rng=chance==0,failure_rng_draws=int(chance>0),success_rng_draws=1+len(targets) if chance else 0,
                    condition='chain',count_min=battle_conditions.chain_duration(own,0),
                    count_max=battle_conditions.chain_duration(own,1),target_ids=targets)
    if tid == 15:
        from . import battle_conditions
        return dict(common,
                    failure_without_rng=chance==0,failure_rng_draws=int(chance>0),success_rng_draws=2 if chance else 0,
                    condition='qimen',count_min=battle_conditions.qimen_duration(own,0),
                    count_max=battle_conditions.qimen_duration(own,3),daily_loss_min=80,daily_loss_max=150,
                    source_present=battle_conditions.qimen_source(state,battle) is not None)
    if tid == 8:
        chance = conversion_chance(caster, opponent)
        return dict(schema=SCHEMA, tactic=8, success_percent=chance, failure_without_rng=chance == 0,
                    failure_rng_draws=0 if chance == 0 else 1, success_rng_draws=0 if chance == 0 else 1,
                    target_loyalty=opponent.loyalty, guaranteed_failure=chance == 0)
    grain = battle_supply.available(state, battle, foe)
    losses = [min(grain, fire_arrow_requested(grain, caster.profile.intellect, roll)) for roll in range(5)]
    return dict(common,
                failure_without_rng=chance==0, failure_rng_draws=int(chance>0), success_rng_draws=2 if chance else 0,
                affected_side=foe, grain_before=grain, grain_loss_min=losses[0],
                grain_loss_max=losses[-1], grain_loss_mean=sum(losses)/5)
