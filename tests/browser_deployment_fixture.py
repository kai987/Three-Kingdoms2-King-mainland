"""Disclosed initial-battle fixtures for paired native deployment UI acceptance.

Use real190 catalogs, officers, warehouses and the shared battle-start service.
The attack is staged directly at that service, not claimed as a natural march.
All subsequent movement, language and save/load interactions use the shipped UI.
"""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest
from copy import deepcopy


def fixture(source):
    game=Campaign(Catalog(ROOT/'game/data/campaigns/190-01.json'))
    owner=game.catalog.data['initial_owners'][source]
    game.command('new',dict(faction=owner,seed=2026),game.revision)
    city=game.state.cities[source]
    ids=[i for i in city.roster.officer_ids if game.state.officers[i].health>0 and game.state.officers[i].troops>0][:10]
    game._start_expanded_battle(game.state,city,game.state.cities['henan'],ids)
    game.validate(game.state)
    initial=game.export_save()
    b=game.state.battle
    proof=dict(source=source,target=b['target'],actor=b['attackers'][0]['id'],save=initial,
               positions=deepcopy(b['extended']['tactical']['positions']),provenance=deepcopy(b['extended']['deployment']))
    damaged=deepcopy(initial)
    damaged['state']['battle']['extended'].pop('tactical')
    damaged['checksum']=digest({key:value for key,value in damaged.items()if key!='checksum'})
    proof['missing_grid']=damaged
    b['extended'].pop('deployment')
    game.validate(game.state)
    proof['without_provenance']=game.export_save()
    if len(b['attackers'])>=5:
        # Keep the surrounded-unit UI regression explicit: native placement
        # no longer happens to box a friendly officer in every new battle.
        b['extended']['deployment']=deepcopy(proof['provenance'])
        points=[(2,2),(1,2),(3,2),(2,1),(2,3)]
        for unit,(x,y) in zip(b['attackers'],points):
            b['extended']['tactical']['positions'][str(unit['id'])]=dict(x=x,y=y)
        game.validate(game.state)
        proof['boxed']=dict(actor=b['attackers'][0]['id'],save=game.export_save())
    return proof


if __name__=='__main__':
    print(json.dumps([fixture(source)for source in('yingchuan','nanyang')],ensure_ascii=False))
