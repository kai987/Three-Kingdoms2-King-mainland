"""Real217 public-arrival saves for sequential manual-deployment UI checks.

Reuse the campaign integration driver's real departure/arrival and ordinary
ten-day preparation. Defender setup explicitly hands the departure interface
to Shu then restores Wei; this is not a claim about natural AI dispatch. No
catalog, officer profile, route, field, AP, food ledger or RNG result is edited.
Only historical event presentation is cleared at export. Every exported save
is accepted by the production loader and remains canonically byte-identical.

Reference-next metadata comes from a discarded production-loaded game and one
actual public battle_place command. Defender-last is reached by nine actual
public confirmations at the engine's current default, with no opening AI call.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_deployment,battle_grid,battle_placement,events
from remake.campaign import Campaign,canonical
from browser_soldier_fixture import _save
from test_remake_manual_deployment_campaign import ManualDeploymentCampaignTests,command


def _checked_save(game,**metadata):
    game.state.extension['events']=events.empty()
    row=_save(game,**metadata)
    loaded=Campaign(game.catalog);loaded.load_save(row['save'],loaded.revision)
    assert canonical(loaded.export_save()).encode()==canonical(row['save']).encode()
    return row


def _details(game):
    battle=game.state.battle;view=battle_placement.view(game,game.state,battle)
    assert view and view['pending']
    actor=view['actor'];positions=battle['extended']['tactical']['positions']
    default=deepcopy(positions[str(actor)])
    pairs={(point['x'],point['y'])for point in view['cells']}
    keyboard=next((dict(x=x,y=y)for x,y in((default['x']+1,default['y']),
        (default['x']-1,default['y']),(default['x'],default['y']+1),(default['x'],default['y']-1))
        if(x,y)in pairs),None)
    field=battle_grid._field(battle)
    terrains={str(kind):next((deepcopy(point)for point in view['cells']
                              if field['classes'][point['y']][point['x']]==kind),None)
              for kind in(3,4)}
    return dict(actor=actor,side=view['side'],confirmed=view['confirmed'],total=view['total'],
        default_point=default,keyboard_point=keyboard,terrain_cells=terrains,
        position_ids=sorted(positions),bounds=deepcopy(view['bounds']),seed=game.state.seed,
        source_city=battle['source'],target_city=battle['target'])


def _first_scene(case,player,kind):
    game,_,_,before=case.arrived(player,count=3)
    assert game.state.rng==before.rng
    metadata=_details(game);battle=game.state.battle
    assert metadata['confirmed']==0 and metadata['keyboard_point']is not None
    zone=battle_deployment.placement_zone(game.catalog,battle,battle_grid._field(battle),metadata['side'])
    allowed=battle_placement.view(game,game.state,battle)['cells']
    future=next(deepcopy(point)for point in zone['defaults']
                if point!=metadata['default_point']and point in allowed)
    metadata['future_default']=future
    metadata['future_default_index']=zone['defaults'].index(future)
    row=_checked_save(game,kind=kind,setup='217-07 actual catalog; public departure/arrival, controlled ten-day clock; sequential pending human deployment',**metadata)
    reference=Campaign(game.catalog);reference.load_save(row['save'],reference.revision)
    rng=deepcopy(reference.state.rng)
    command(reference,'battle_place',battle_id=battle['id'],actor=metadata['actor'],**future)
    after=battle_placement.view(reference,reference.state,reference.state.battle)
    after_positions=reference.state.battle['extended']['tactical']['positions']
    assert after['pending']and after['confirmed']==1
    current=deepcopy(after_positions[str(after['actor'])])
    assert current==metadata['default_point'],'Next unit must rescan the now-vacant first native candidate'
    assert reference.state.rng==rng
    row['expected_next']=dict(actor=after['actor'],default_point=current,
        position_ids=sorted(after_positions),confirmed=after['confirmed'],pending=after['pending'])
    return row


def _defender_last(case):
    game,_,_,before=case.arrived('wei',count=3)
    assert game.state.rng==before.rng
    battle=game.state.battle
    total=len(battle['extended']['placement']['order'])
    assert total==10
    with patch.object(game,'_run_tactical_ai_turn',side_effect=AssertionError('No AI before the tenth confirmation')):
        for _ in range(total-1):
            details=_details(game)
            command(game,'battle_place',battle_id=battle['id'],actor=details['actor'],**details['default_point'])
    metadata=_details(game);battle=game.state.battle
    assert metadata['confirmed']==9
    row=_checked_save(game,kind='defender_last',
        setup='217-07 actual catalog; public arrival and nine real public confirmations at native defaults; opening attacker AI has not run',
        **metadata)
    row['before_ai']=dict(battle=deepcopy(battle),rng=asdict(game.state.rng),
        soldiers=deepcopy(game.state.soldiers),command_books=deepcopy(game.state.extension['command_books']))
    return row


def fixtures():
    ManualDeploymentCampaignTests.setUpClass()
    case=ManualDeploymentCampaignTests('test_public_attacker_arrival_reserves_real_bags_once_and_does_not_start_ai')
    return[_first_scene(case,'shu','attacker'),_first_scene(case,'wei','defender'),_defender_last(case)]


if __name__=='__main__':
    print(json.dumps(fixtures(),ensure_ascii=False,separators=(',',':')))
