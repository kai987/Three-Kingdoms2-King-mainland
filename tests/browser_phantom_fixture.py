"""Disclosed real208-catalog saves for visible phantom-condition acceptance.

These are controlled UI fixtures, not historical deployments or natural AI
results. The existing soldier fixture supplies actual armies through new /
allocate and the shared battle initializer. Only legal positions, starting
seeds and explicit player/side handoffs are arranged here. Catalog profiles,
warehouses, field templates and images are not rewritten. Events are cleared
only to isolate these screens from retrospective opening/event dialogs.

Restricted follows a real public successful attacking cast; no condition
counter is fabricated. Expiry follows a real defending cast and a real public
wait through the first full-day boundary. AI response is held only while that
fixture is constructed, then defenderAP is explicitly set to0 to isolate the
browser's next wait/pass/day boundary. Clocks, grain bags and condition counts
are never assigned directly. Every save validates and round-trips byte-for-
byte in canonical form through the unchanged production loader.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_conditions as conditions,battle_grid,events,tactic_effects,tactical_ai
from remake.campaign import Campaign,canonical
from remake.campaign_expansion import TACTICS
from browser_soldier_fixture import _base,_positions,_save


def _command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def _contact_cells(game,actor,target):
    """Adjacent target forest/mountain, source forest/plain: both fire and contact."""
    battle=game.state.battle;field=battle_grid._field(battle)
    sites={(site['x'],site['y'])for site in field['services']}|{field['camp']}
    candidates=sorted(((x,y)for y in range(1,battle_grid.ROWS-1)
                       for x in range(1,battle_grid.COLUMNS-1)),
                      key=lambda point:(abs(point[0]-15)+abs(point[1]-9),point[1],point[0]))
    first,second=next(((nx,ny),(x,y))for x,y in candidates
        if field['classes'][y][x]in(0,4)and(x,y)not in sites
        for nx,ny in((x-1,y),(x+1,y),(x,y-1),(x,y+1))
        if 0<=nx<battle_grid.COLUMNS and 0<=ny<battle_grid.ROWS
        and field['classes'][ny][nx]in(0,2)and(nx,ny)not in sites)
    _positions(game,{actor:first,target:second})
    return first,second


def _prepared(own):
    """Find an ordinary starting seed, then preserve its real command draw."""
    foe='defenders'if own=='attackers'else'attackers'
    # New/allocate currently draw no RNG. Build with the selected real seed
    # anyway and verify the actual next draw, rather than overwrite the RNG.
    for seed in range(1,100):
        game,_,strategist=_base(seed)
        state,battle=game.state,game.state.battle
        if own=='attackers':
            actor=strategist
            target=battle['defenders'][0]['id']
        else:
            actor=max(battle['defenders'],key=lambda unit:(
                state.officers[unit['id']].profile.intellect,-unit['id']))['id']
            target=strategist
        first,second=_contact_cells(game,actor,target)
        state.player=battle['attacker']if own=='attackers'else battle['defender']
        row=battle['extended']['tactical']
        row['side']=own;row['passed'][own]=False;row['passed'][foe]=own=='defenders'
        caster=next(unit for unit in battle[own]if unit['id']==actor)
        victim=next(unit for unit in battle[foe]if unit['id']==target)
        reason=tactical_ai.tactic_reason(state,battle,caster,victim,own,foe,
            game.catalog.map_cities[battle['target']]['terrain'],TACTICS[2])
        assert not reason,reason
        preview=tactic_effects.preview(state,battle,caster,victim,own,foe,2)
        next_rng=deepcopy(state.rng)
        if next_rng.next()%100<preview['success_percent']:
            assert 'conditions'not in battle['extended']
            return game,actor,target,first,second,preview
    raise AssertionError('No ordinary controlled seed succeeded for phantom')


def _checked_save(game,**metadata):
    game.state.extension['events']=events.empty()
    row=_save(game,**metadata)
    loaded=Campaign(game.catalog)
    loaded.load_save(row['save'],loaded.revision)
    assert canonical(loaded.export_save()).encode()==canonical(row['save']).encode()
    return row


def fixtures():
    game,actor,target,first,second,preview=_prepared('attackers')
    battle=game.state.battle
    shared=dict(seed=game.state.seed,
        setup='208-10 real catalog; controlled adjacent cells, seed and player/side handoff',
        source_city=battle['source'],target_city=battle['target'])
    cast=_checked_save(game,kind='cast',actor=actor,target=target,preview=preview,
        actor_cell=dict(zip(('x','y'),first)),target_cell=dict(zip(('x','y'),second)),
        controlled_side='attackers',**shared)
    assert 'conditions'not in cast['save']['state']['battle']['extended']

    expected=deepcopy(game.state.rng);expected.next()
    _command(game,'tactic',battle_id=battle['id'],actor=actor,target=target,tactic=2)
    battle=game.state.battle;row=battle['extended']['tactical']
    assert game.state.rng==expected
    assert conditions.remaining(battle,target)==3
    game.state.player=battle['defender']
    row['side']='defenders';row['passed'].update(attackers=True,defenders=False)
    # used is the previous human side's activity receipt, not an action lock;
    # an explicit player handoff also starts that human's own empty receipt.
    battle['used']=[]
    board=battle_grid.view(game,game.state,battle)['actors'][str(target)]
    assert board['move_reason']and not board['reachable']
    assert actor in board['attack_targets']and actor in board['duel_targets']
    assert actor in board['tactic_targets']['0']
    restricted=_checked_save(game,kind='restricted',actor=target,target=actor,remaining=3,
        actor_cell=dict(zip(('x','y'),second)),target_cell=dict(zip(('x','y'),first)),
        controlled_side='defenders',**shared)

    game,caster,affected,first,second,preview=_prepared('defenders')
    battle=game.state.battle
    expected=deepcopy(game.state.rng);expected.next()
    # The wait itself is real: it increments the round, feeds both armies and
    # scans the new condition once. Only the newly active enemy AI is held.
    with patch.object(game,'_run_tactical_ai_turn',return_value=None):
        _command(game,'tactic',battle_id=battle['id'],actor=caster,target=affected,tactic=2)
        assert conditions.remaining(game.state.battle,affected)==2
        _command(game,'battle_wait',battle_id=battle['id'])
    battle=game.state.battle;row=battle['extended']['tactical']
    assert game.state.rng==expected
    assert battle['round']==2 and conditions.remaining(battle,affected)==1
    game.state.player=battle['attacker']
    assert row['side']=='attackers'and not any(row['passed'].values())
    row['points']['defenders']=0
    expiry=_checked_save(game,kind='expiry',actor=affected,target=caster,remaining=1,
        actor_cell=dict(zip(('x','y'),second)),target_cell=dict(zip(('x','y'),first)),
        seed=game.state.seed,controlled_side='attackers',defender_ap=0,
        setup='208-10 real catalog; controlled cells/seed/side; real defending cast and wait; setup-only AI hold; defenderAP0 isolates next day',
        source_city=battle['source'],target_city=battle['target'])
    # Independently prove the shipped next public wait really expires it;
    # discard this reference game, preserving the exported count1 fixture.
    reference=Campaign(game.catalog)
    reference.load_save(expiry['save'],reference.revision)
    _command(reference,'battle_wait',battle_id=battle['id'])
    assert reference.state.phase=='battle'and reference.state.battle['round']==3
    assert conditions.remaining(reference.state.battle,affected)==0
    assert battle_grid.view(reference,reference.state,reference.state.battle)['actors'][str(affected)]['reachable']
    return[cast,restricted,expiry]


if __name__=='__main__':
    print(json.dumps(fixtures(),ensure_ascii=False,separators=(',',':')))
