/* UI availability must agree with the actual rule handler, not a copied table. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{spawnSync}=require('node:child_process'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const output=spawnSync(process.env.PYTHON||'python3',['-B','-c',String.raw`
from copy import deepcopy
from pathlib import Path
import sys,json
sys.path.insert(0,'source')
from remake.campaign import Campaign,Catalog,GameError
from remake.campaign_expansion import TACTICS
catalog=Catalog(Path('game/data/campaigns/217-07.json'))
rows=[]
for terrain in ('plain','mountain','water'):
    game=Campaign(catalog);game.command('new',{'faction':'shu','seed':2026},0)
    source=next(c for c in game.state.cities.values() if c.owner=='shu' and c.roster.officer_ids)
    actor=next(i for i in source.roster.officer_ids if game.state.officers[i].troops>0)
    destination=next(c for c in game.state.cities.values() if c.owner not in ('shu','neutral') and c.roster.officer_ids and catalog.map_cities[c.id]['terrain']==terrain)
    # Controlled battle entry uses current identities/geography. It does not
    # claim that these non-adjacent scenes were reached by natural campaign play.
    game._start_expanded_battle(game.state,source,destination,[actor])
    base=deepcopy(game.state)
    for variant in ('normal','no_points','stunned','small_army','existing_ambush'):
        for tid,tactic in enumerate(TACTICS):
            game.state=deepcopy(base);b=game.state.battle
            if variant=='no_points':b['extended']['tactical']['points']['attackers']=0
            if variant=='stunned':b['extended']['support'][str(actor)]['stunned']=1
            if variant=='small_army':b['attackers'][0]['troops']=99
            if variant=='existing_ambush':b['extended']['ambush']={'actor':actor}
            snapshot=deepcopy(b);quote=game.view()['catalog']['battle_tactical'];reason=''
            try:game._tactic(game.state,{'battle_id':b['id'],'actor':actor,'target':b['defenders'][0]['id'],'tactic':tid})
            except GameError as exc:reason=str(exc)
            rows.append(dict(terrain=terrain,variant=variant,actor=actor,battle=snapshot,target=b['defenders'][0]['id'],quote=quote,tactic=dict(id=tid,cost=tactic[1],effect=tactic[2]),reason=reason))
print(json.dumps(rows,ensure_ascii=False))
`],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024});
assert.equal(output.status,0,output.stderr);
const rows=JSON.parse(output.stdout),source=fs.readFileSync(path.join(root,'game/app.js'),'utf8');
const context={view:{catalog:{}},actor:null,target:null};vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function tacticUnavailable('),source.indexOf('function tactics(')),context);
for(const row of rows){
 context.actor=row.actor;context.target=row.target;context.view.catalog.battle_tactical=row.quote;
 const before=JSON.stringify(row.battle);
 assert.equal(context.tacticUnavailable(row.tactic,row.battle),row.reason,`${row.terrain}/${row.variant}/${row.tactic.id}`);
 assert.equal(JSON.stringify(row.battle),before,'Reading availability never changes the battle');
}
assert.equal(rows.length,240);
console.log(`tactic boundaries: ${rows.length} current-backend comparisons across all16 tactics, strategic terrain labels, shared AP, stun, troop minimum and existing ambush passed`);
