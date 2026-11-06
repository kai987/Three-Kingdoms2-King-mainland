"""Pure, source-qualified effects for fire arrows and battlefield conversion.

B243/B6F0 fire-arrow arithmetic and B72B conversion thresholds are recovered
from the pinned original. General success probability and the campaign's
seeded modulo sampling remain explicit remake adaptations. These helpers never
initialize supply, spend maneuver points or advance random state.
"""
from .march_supply import LIMIT
from .officers import experience_tier

SCHEMA = 'tk2-tactic-effect-preview-v1'


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


def general_chance(actor, target):
    """Retained remake B7BE substitute, without unproven environment mapping."""
    return max(10, min(95, 60+(actor.profile.intellect-target.profile.intellect)//2))


def preview(state, battle, actor, target, own, foe, tid):
    """Pure actor/target quote; legality and maneuver payment remain separate."""
    if type(tid) is not int or tid not in (2, 5, 8):
        return None
    from . import battle_supply
    caster, opponent = state.officers[actor['id']], state.officers[target['id']]
    if tid == 2:
        from . import battle_conditions
        return dict(schema=SCHEMA,tactic=2,success_percent=general_chance(caster,opponent),
                    failure_without_rng=False,failure_rng_draws=1,success_rng_draws=1,
                    condition='phantom',condition_count=battle_conditions.duration(own),
                    target_count=battle_conditions.remaining(battle,target['id']))
    if tid == 8:
        chance = conversion_chance(caster, opponent)
        return dict(schema=SCHEMA, tactic=8, success_percent=chance, failure_without_rng=chance == 0,
                    failure_rng_draws=0 if chance == 0 else 1, success_rng_draws=0 if chance == 0 else 1,
                    target_loyalty=opponent.loyalty, guaranteed_failure=chance == 0)
    grain = battle_supply.available(state, battle, foe)
    losses = [min(grain, fire_arrow_requested(grain, caster.profile.intellect, roll)) for roll in range(5)]
    return dict(schema=SCHEMA, tactic=5, success_percent=general_chance(caster, opponent),
                failure_without_rng=False, failure_rng_draws=1, success_rng_draws=2,
                affected_side=foe, grain_before=grain, grain_loss_min=losses[0],
                grain_loss_max=losses[-1], grain_loss_mean=sum(losses)/5)
