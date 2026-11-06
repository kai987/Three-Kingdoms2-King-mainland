"""Real208-catalog saves for connected-water chain acceptance.

Controlled native cells, experience tier3 for an actual special-group caster,
seed and player-side handoffs expose the rule without editing map pixels,
profiles, troop totals or random outputs. All chain counts come from a real
public cast; expiry comes from actual public day-boundary waits with the AI
policy held at WAIT only during fixture preparation. Production validation and
canonical save round trips remain enabled. This is not a historical opening.
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
from browser_soldier_fixture import _base,_save

WAIT=dict(kind='wait',actor=None,target=None,tactic=None,score=0)

def command(game,kind,**payload):return game.command(kind,payload,game.revision)
def near(point):
    x,y=point
    return[(a,b)for a,b in((x+1,y),(x-1,y),(x,y+1),(x,y-1))
           if 0<=a<battle_grid.COLUMNS and 0<=b<battle_grid.ROWS]

def layout(game,actor):
    b=game.state.battle;field=battle_grid._field(b);classes=field['classes']
    water=lambda p:classes[p[1]][p[0]]==3
    sites={(s['x'],s['y'])for s in field['services']}|{field['camp']}
    choices=[]
    for y in range(battle_grid.ROWS):
        for x in range(battle_grid.COLUMNS):
            center=(x,y)
            if not water(center):continue
            for second in near(center):
                if not water(second):continue
                for bridge in near(second):
                    if bridge==center or classes[bridge[1]][bridge[0]]in(3,5):continue
                    for leaf in near(bridge):
                        if not water(leaf)or leaf in(center,second)or any(leaf in near(p)for p in(center,second)):continue
                        for source in near(center):
                            if source in(center,second,bridge,leaf)or source in sites or classes[source[1]][source[0]]!=2:continue
                            choices.append((source,center,second,bridge,leaf))
    if not choices:raise AssertionError('No native water-water-land-water chain with a plain caster')
    source,center,second,bridge,leaf=choices[len(choices)//2]
    victims=b['defenders'][:4];assigned={actor:source,**{u['id']:p for u,p in zip(victims,(center,second,bridge,leaf))}}
    cluster={source,center,second,bridge,leaf};avoid=cluster|{q for p in cluster for q in near(p)}
    positions=b['extended']['tactical']['positions'];used=set(assigned.values())
    for side in battle_grid.SIDES:
        for u in b[side]:
            point=assigned.get(u['id'])
            if point is None:
                point=next((x,y)for y in range(battle_grid.ROWS)for x in range(battle_grid.COLUMNS)
                           if(x,y)not in used|avoid|sites)
            positions[str(u['id'])]=dict(zip(('x','y'),point));used.add(point)
    return victims[0],victims[2],source,center

def checked(game,**metadata):
    game.state.extension['events']=events.empty()
    row=_save(game,**metadata)
    other=Campaign(game.catalog);other.load_save(row['save'],other.revision)
    assert canonical(other.export_save())==canonical(row['save'])
    return row

def fixtures():
    for seed in range(1,100):
        game,_,actor=_base(seed);b=game.state.battle
        # The original special-group caster genuinely unlocks ID10 at tier3.
        officer=game.state.officers[actor];officer.experience=3500;officer.tier=3
        assert tactical_ai.maximum_tactic(officer)>=10
        target,bridge,source,center=layout(game,actor)
        reason=tactical_ai.tactic_reason(game.state,b,next(u for u in b['attackers']if u['id']==actor),target,'attackers','defenders','water',TACTICS[10]);assert not reason,reason
        caster=next(u for u in b['attackers']if u['id']==actor)
        q=tactic_effects.preview(game.state,b,caster,target,'attackers','defenders',10)
        rng=deepcopy(game.state.rng)
        if rng.next()%100>=q['success_percent']:continue
        counts=[4+rng.next()%2 for _ in q['target_ids']]
        if len(set(counts))!=2:continue
        break
    else:raise AssertionError('No ordinary successful seed with distinct water counts')
    assert len(q['target_ids'])==3 and str(bridge['id'])not in q['target_ids']
    common=dict(seed=seed,actor=actor,target=target['id'],bridge=bridge['id'],targets=q['target_ids'],counts=counts,
        setup='real208 catalog/native cells; caster tier3; arranged seed/cells/side handoffs; actual cast and expiry waits',
        actor_cell=dict(zip(('x','y'),source)),target_cell=dict(zip(('x','y'),center)))
    cast=checked(game,kind='cast',preview=q,**common)
    with patch.object(game,'_run_tactical_ai_turn',return_value=None):
        command(game,'tactic',battle_id=b['id'],actor=actor,target=target['id'],tactic=10)
    assert game.state.rng==rng
    actual=game.state.battle
    for ident,count in zip(q['target_ids'],counts):assert actual['extended']['conditions']['units'][ident]==dict(kind='chain',remaining=count)
    assert conditions.remaining(actual,bridge['id'])==0
    game.state.player=actual['defender'];row=actual['extended']['tactical'];row['side']='defenders';row['passed'].update(attackers=True,defenders=False);actual['used']=[]
    restricted=checked(game,kind='restricted',**common)
    board=battle_grid.view(game,game.state,actual)['actors'][str(target['id'])]
    assert not board['reachable']and actor in board['attack_targets']and actor in board['duel_targets']and actor in board['tactic_targets']['0']
    game=Campaign(game.catalog);game.load_save(cast['save'],game.revision)
    with patch('remake.tactical_ai.choose_action',return_value=WAIT):
        command(game,'tactic',battle_id=game.state.battle['id'],actor=actor,target=target['id'],tactic=10)
        while conditions.remaining(game.state.battle,target['id'])>1:
            command(game,'battle_wait',battle_id=game.state.battle['id'])
    actual=game.state.battle;actual['extended']['tactical']['points']['defenders']=0
    expiry=checked(game,kind='expiry',remaining=1,**common)
    other=Campaign(game.catalog);other.load_save(expiry['save'],other.revision)
    command(other,'battle_wait',battle_id=actual['id'])
    assert conditions.remaining(other.state.battle,target['id'])==0
    return[cast,restricted,expiry]

if __name__=='__main__':print(json.dumps(fixtures(),ensure_ascii=False,separators=(',',':')))
