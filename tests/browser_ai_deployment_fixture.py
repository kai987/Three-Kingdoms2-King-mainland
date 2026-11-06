"""Current217 real arrivals plus an explicitly controlled legacy pending shape.

Opening AI groups/positions are production results. The legacy row deliberately
removes the optional new receipt and restores the previous ordered defaults;
it is not presented as a captured historical save or an original ROM scene.
All exports pass the real loader, with no changes to AP, grain, RNG or troops.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import battle_auto_deployment,battle_deployment,battle_grid
from remake.campaign import Campaign,canonical
from browser_manual_deployment_fixture import _checked_save
from test_remake_manual_deployment_campaign import ManualDeploymentCampaignTests


def fixtures():
    ManualDeploymentCampaignTests.setUpClass()
    case=ManualDeploymentCampaignTests('test_public_attacker_arrival_reserves_real_bags_once_and_does_not_start_ai')
    rows=[]
    for player,side,groups in [('shu','defenders',[0,1,1,1,2,2,3,3,3,4]),('wei','attackers',[0,1,2])]:
        game,_,_,before=case.arrived(player,count=3)
        assert game.state.rng==before.rng
        battle=game.state.battle;view=battle_auto_deployment.view(game,game.state,battle)['sides'][side]
        assert view['groups']==groups
        expected=deepcopy(battle_auto_deployment.initial_positions(game,battle,side))
        old=battle_deployment.placement_zone(game.catalog,battle,battle_grid._field(battle),side)['defaults']
        legacy={str(unit['id']):point for unit,point in zip(battle[side],old)}
        assert expected!=legacy
        row=_checked_save(game,kind='ai_'+side,side=side,expected=expected,
            groups=groups,order=view['order'],binding=view['binding'],profile=view['profile'])
        if player=='shu':
            previous=Campaign(game.catalog);previous.load_save(row['save'],previous.revision)
            previous.state.battle['extended'].pop('auto_deployment')
            previous.state.battle['extended']['tactical']['positions'].update(deepcopy(legacy))
            previous.validate(previous.state)
            row['legacy']=_checked_save(previous,kind='controlled_legacy_pending',side=side,expected=legacy)['save']
            assert canonical(row['legacy'])!=canonical(row['save'])
        rows.append(row)
    return rows


if __name__=='__main__':
    print(json.dumps(fixtures(),ensure_ascii=False,separators=(',',':')))
