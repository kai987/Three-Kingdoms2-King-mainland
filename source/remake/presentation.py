"""Transient, authoritative battle animation receipts for one committed command.

These snapshots never enter the campaign, catalog, save or RNG. Recording is
disabled outside the command context and for battles not involving the player.
"""
from contextlib import contextmanager
from copy import deepcopy

SCHEMA = 'tk2-battle-presentation-v1'
# A complete 60-point enemy phase can contain many one-cell moves. Preserve
# the finite authoritative sequence; the client separately bounds playback.
MAX_SCENES = 192


@contextmanager
def capture(campaign):
    previous = getattr(campaign, '_presentation_capture', None)
    scenes = []
    campaign._presentation_capture = scenes
    try:
        yield scenes
    finally:
        if previous is None:
            del campaign._presentation_capture
        else:
            campaign._presentation_capture = previous


def snapshot(campaign, state):
    scenes = getattr(campaign, '_presentation_capture', None)
    battle = state.battle
    if (scenes is None or len(scenes) >= MAX_SCENES or battle is None
            or state.player not in (battle['attacker'], battle['defender'])):
        return None
    extended = battle['extended']
    duel = extended['duel']
    return dict(round=battle['round'], outcome=battle['outcome'],
        duel={key: duel[key] for key in ('actor', 'target', 'round')} if duel else None,
        units=[dict(id=unit['id'], side=side, troops=unit['troops'],
                    **{key: extended['support'][str(unit['id'])][key]
                       for key in ('health', 'energy', 'guard', 'stunned')})
               for side in ('attackers', 'defenders') for unit in battle[side]])


def record(campaign, state, before, *, kind, actor=None, target=None, own=None,
           counter=False, tactic=None, effect=None, success=True, skipped=False,
           move=None, reply=None, siege=None):
    if before is None:
        return
    after = snapshot(campaign, state)
    if after is None:
        return
    scene = dict(kind=kind, battle_id=state.battle['id'],
        actor=actor, target=target, own=own, counter=counter, tactic=tactic,
        effect=effect, success=success, skipped=skipped, move=move, reply=reply,
        before=before, after=after)
    if siege is not None:
        scene['siege'] = deepcopy(siege)
    campaign._presentation_capture.append(scene)


def response(view, revision, scenes):
    if not scenes:
        return view
    return dict(view, presentation=dict(schema=SCHEMA, revision=revision,
                                       scenes=deepcopy(scenes)))
