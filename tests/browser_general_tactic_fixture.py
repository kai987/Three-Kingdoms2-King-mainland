"""Disclosed real208-catalog saves for near/far shared success-gate UI.

The production new/allocation/battle initializer creates the armies. Only
legal visible cells, strategist experience10000/tier6 and an ordinary starting
seed are controlled. Source profiles, routes, warehouses and RNG are unchanged.
The same real first sample is between the two literal expected thresholds.
No result is installed in the save; the browser must execute the public tactic.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_grid,events,tactic_effects,tactical_ai
from remake.campaign import SeedRng
from remake.campaign_expansion import TACTICS
from browser_soldier_fixture import _base,_positions,_save
from browser_phantom_fixture import _contact_cells


def fixtures():
    #51% at distance1,31% at distance5:I95/76,tier6/0,+10.
    seed=next(seed for seed in range(1,10000) if SeedRng(seed).next()%100==40)
    rows=[]
    for distance,percent,success in ((1,51,True),(5,31,False)):
        game,_,actor=_base(seed)
        state,battle=game.state,game.state.battle
        target=battle['defenders'][0]['id']
        state.officers[actor].experience=10000;state.officers[actor].tier=6
        first,second=_contact_cells(game,actor,target)
        if distance==5:
            field=battle_grid._field(battle)
            first=next((x,y) for y in range(battle_grid.ROWS) for x in range(battle_grid.COLUMNS)
                if max(abs(x-second[0]),abs(y-second[1]))==5
                and field['classes'][y][x] in (0,2))
            _positions(game,{actor:first,target:second})
        caster=next(unit for unit in battle['attackers'] if unit['id']==actor)
        victim=next(unit for unit in battle['defenders'] if unit['id']==target)
        assert not tactical_ai.tactic_reason(state,battle,caster,victim,'attackers','defenders',
            game.catalog.map_cities[battle['target']]['terrain'],TACTICS[2])
        preview=tactic_effects.preview(state,battle,caster,victim,'attackers','defenders',2)
        assert preview['success_percent']==percent and preview['distance']==distance
        expected=deepcopy(state.rng);assert expected.next()%100==40
        state.extension['events']=events.empty()
        rows.append(_save(game,actor=actor,target=target,distance=distance,percent=percent,
            seed=seed,sample=40,expected_rng=dict(state=expected.state,draws=expected.draws),
            expected_success=success,preview=preview,
            source='Actual208 catalog; controlled visible cells and tier6; unchanged public roll'))
    return rows


if __name__=='__main__':
    print(json.dumps(fixtures(),ensure_ascii=False,separators=(',',':')))
