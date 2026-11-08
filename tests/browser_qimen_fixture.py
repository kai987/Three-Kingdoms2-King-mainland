"""Disclosed real234-catalog Qimen saves for visible browser acceptance.

Use actual Shu officers from Hanzhong, actual neighboring Wei Fufeng and its
unaltered original08 grid. Nanyang is neither a Hanzhong neighbor nor staffed
in234-02, so it cannot provide a production-valid battle for this fixture.
The direct battle initializer is a controlled starting boundary, not a claim
about a natural march or historical deployment. Source profiles, warehouses,
map and route data remain unchanged. The disclosed setup grants Zhuge Liang
experience10000/tier6, arranges legal neighboring plain cells, moves bystanders
away, and selects an ordinary starting seed whose actual success draw passes.

Every condition, day, periodic hit and experience award comes from real public
commands. Restricted explicitly hands the human interface to the affected
defender; daily/expiry set defending AP to 0 to isolate the next public wait.
Expiry preparation starts the target at one soldier and chooses WAIT policy
while real turns, grain, clocks, damage and RNG continue. Historical events
are cleared only at export. No
condition counts, day cursors, grain ledger or random results are assigned.
Every save validates and round-trips canonically through the production loader.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_conditions as conditions,battle_grid,events,tactic_effects,tactical_ai
from remake.campaign import Campaign,Catalog,canonical
from remake.campaign_expansion import TACTICS
from browser_soldier_fixture import _positions,_save

ACTOR=439
TARGET_CITY='fufeng'
WAIT=dict(kind='wait',actor=None,target=None,tactic=None,score=0)


def _command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


def _plain_contact(game,target):
    battle=game.state.battle;field=battle_grid._field(battle)
    sites={(site['x'],site['y'])for site in field['services']}|{field['camp']}
    candidates=sorted(((x,y)for y in range(1,battle_grid.ROWS-1)
                       for x in range(1,battle_grid.COLUMNS-1)),
                      key=lambda point:(abs(point[0]-15)+abs(point[1]-9),point[1],point[0]))
    first,second=next(((x,y),(x+1,y))for x,y in candidates
        if field['classes'][y][x]==field['classes'][y][x+1]==2
        and(x,y)not in sites and(x+1,y)not in sites)
    # Explicitly keep every bystander out of the contact cluster, rather than
    # depend on whichever native default deployment happens not to collide.
    moves={ACTOR:first,target:second};used={first,second}
    for side in battle_grid.SIDES:
        for unit in battle[side]:
            if unit['id']in moves:continue
            point=next((x,y)for y in range(battle_grid.ROWS)for x in range(battle_grid.COLUMNS)
                if(x,y)not in used|sites
                and min(abs(x-p[0])+abs(y-p[1])for p in(first,second))>=6)
            moves[unit['id']]=point;used.add(point)
    _positions(game,moves)
    return first,second


def _prepared():
    catalog=Catalog(ROOT/'game/data/campaigns/234-02.json')
    for seed in range(1,100):
        game=Campaign(catalog)
        _command(game,'new',faction='shu',seed=seed)
        state=game.state;source=state.cities['hanzhong']
        assert ACTOR in source.roster.officer_ids
        assert state.cities[TARGET_CITY].owner=='wei'
        assert TARGET_CITY in game._neighbors(source.id,state)
        marching=game._march_ids(state)
        available=[ident for ident in source.roster.officer_ids if ident not in marching
                   and state.officers[ident].troops>0 and state.officers[ident].health>0]
        assert ACTOR in available and len(available)>=4
        # Four real opening units keep the 10AP cast observable before a
        # forced pass. No extra AP is fabricated.
        ids=[ACTOR]+[ident for ident in available if ident!=ACTOR][:3]
        # Explicit controlled learned tier, without changing the source profile.
        state.officers[ACTOR].experience=10000;state.officers[ACTOR].tier=6
        game._start_expanded_battle(state,source,state.cities[TARGET_CITY],ids)
        battle=state.battle
        assert state.phase=='battle'and len(battle['defenders'])>=2
        assert battle['extended']['tactical']['points']['attackers']>10
        target=battle['defenders'][0]['id']
        first,second=_plain_contact(game,target)
        caster=next(unit for unit in battle['attackers']if unit['id']==ACTOR)
        victim=next(unit for unit in battle['defenders']if unit['id']==target)
        reason=tactical_ai.tactic_reason(state,battle,caster,victim,'attackers','defenders',
            game.catalog.map_cities[battle['target']]['terrain'],TACTICS[15])
        assert not reason,reason
        preview=tactic_effects.preview(state,battle,caster,victim,'attackers','defenders',15)
        next_rng=deepcopy(state.rng)
        if next_rng.next()%100<preview['success_percent']:
            assert 'conditions'not in battle['extended']
            game.validate(state)
            return game,target,first,second,preview
    raise AssertionError('No real starting seed passed the retained Qimen gate')


def _checked_save(game,**metadata):
    game.state.extension['events']=events.empty()
    result=_save(game,**metadata)
    loaded=Campaign(game.catalog);loaded.load_save(result['save'],loaded.revision)
    assert canonical(loaded.export_save()).encode()==canonical(result['save']).encode()
    return result


def _clone(game,saved):
    clone=Campaign(game.catalog);clone.load_save(saved,clone.revision)
    return clone


def _next_daily(game,saved,target):
    """Observe the actual next production wait in a discarded reference game."""
    reference=_clone(game,saved)
    before=deepcopy(reference.state.rng)
    _command(reference,'battle_wait',battle_id=reference.state.battle['id'])
    state,battle=reference.state,reference.state.battle
    assert state.phase=='battle'
    assert state.rng.draws==before.draws+1
    daily=next(event['details']for event in reversed(state.extension['events']['items'])
               if event['kind']=='tactic'and event['details'].get('qimen_phase')=='daily')
    rows=deepcopy(daily['qimen_ticks'])
    assert len(rows)==1 and rows[0]['id']==str(target)
    return dict(round=battle['round'],rng=asdict(state.rng),experience=state.officers[ACTOR].experience,
        tier=state.officers[ACTOR].tier,experience_gain=daily['experience_gain'],rows=rows,
        count=conditions.remaining(battle,target),
        troops=next(unit['troops']for unit in battle['defenders']if unit['id']==target)),reference


def fixtures():
    game,target,first,second,preview=_prepared();battle=game.state.battle
    shared=dict(actor=ACTOR,target=target,preview=preview,seed=game.state.seed,
        actor_cell=dict(zip(('x','y'),first)),target_cell=dict(zip(('x','y'),second)),
        source_city=battle['source'],target_city=battle['target'],
        setup='234-02 actual catalog; Hanzhong Shu to adjacent staffed Wei Fufeng; controlled XP10000/tier6, plain contact, bystanders and actual successful seed')
    cast=_checked_save(game,kind='cast',count=0,controlled_side='attackers',**shared)
    before_profile=deepcopy(game.state.officers[ACTOR].profile)
    expected_rng=deepcopy(game.state.rng);expected_rng.next();expected_rng.next()
    _command(game,'tactic',battle_id=battle['id'],actor=ACTOR,target=target,tactic=15)
    battle=game.state.battle
    assert game.state.rng==expected_rng
    assert conditions.kind(battle,target)=='qimen'
    count=conditions.remaining(battle,target)
    assert 6<=count<=9 and battle['round']==1
    assert game.state.officers[ACTOR].profile==before_profile

    # Keep the actual post-cast attacking game for daily/expiry. The restricted
    # clone explicitly changes human side, not the already-paid effect.
    post_cast=game.export_save();restricted_game=_clone(game,post_cast)
    restricted_battle=restricted_game.state.battle
    restricted_game.state.player=restricted_battle['defender']
    row=restricted_battle['extended']['tactical']
    row['side']='defenders';row['passed'].update(attackers=True,defenders=False)
    restricted_battle['used']=[]  # New human's activity receipt after handoff.
    actor_view=battle_grid.view(restricted_game,restricted_game.state,restricted_battle)['actors'][str(target)]
    assert actor_view['move_reason']and not actor_view['reachable']
    assert ACTOR in actor_view['attack_targets']and ACTOR in actor_view['duel_targets']
    assert ACTOR in actor_view['tactic_targets']['0']
    restricted=_checked_save(restricted_game,kind='restricted',count=count,
        locked_actor=target,enemy=ACTOR,controlled_side='defenders',**shared)

    battle=game.state.battle;battle['extended']['tactical']['points']['defenders']=0
    daily=_checked_save(game,kind='daily',count=count,controlled_side='attackers',defender_ap=0,**shared)
    daily['expected_daily'],_= _next_daily(game,daily['save'],target)
    assert daily['expected_daily']['count']==count-1

    # Stage a one-soldier survivor for this specific zero-troop regression.
    # The real public waits then apply all damage, draws, XP and expiry.
    next(unit for unit in battle['defenders'] if unit['id']==target)['troops']=1
    while conditions.remaining(game.state.battle,target)>1:
        with patch('remake.tactical_ai.choose_action',return_value=WAIT):
            _command(game,'battle_wait',battle_id=game.state.battle['id'])
        assert game.state.phase=='battle'
    battle=game.state.battle
    assert conditions.kind(battle,target)=='qimen'and conditions.remaining(battle,target)==1
    assert next(unit for unit in battle['defenders'] if unit['id']==target)['troops']==0
    battle['extended']['tactical']['points']['defenders']=0
    expiry=_checked_save(game,kind='expiry',count=1,controlled_side='attackers',defender_ap=0,**shared)
    expiry['expected_daily'],expired=_next_daily(game,expiry['save'],target)
    assert expiry['expected_daily']['count']==0
    assert conditions.kind(expired.state.battle,target)is None
    # Even a zero-men original slot consumes its final real periodic sample.
    assert expiry['expected_daily']['rows'][0]['remaining']==0
    assert game.state.officers[ACTOR].profile==before_profile
    return[cast,restricted,daily,expiry]


if __name__=='__main__':
    print(json.dumps(fixtures(),ensure_ascii=False,separators=(',',':')))
