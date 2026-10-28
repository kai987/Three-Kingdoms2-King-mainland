/* The UI consumes authoritative movement/target quotes; it never finds paths. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const scene=require('../game/battle-scene.js'),source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const points={attackers:10,defenders:16};
const battle={id:'battle-9',round:2,used:[7],extended:{tactical:{schema:'tk2-battle-tactical-v1',map_id:'original-15',side:'attackers',points,positions:{7:{x:0,y:0},8:{x:30,y:18}}}}};
const row={can_act:true,reason:'',reachable:[{x:1,y:0,cost:3},{x:0,y:1,cost:2}],attack_targets:[8],duel_targets:[],tactic_targets:{0:[8]},attack_reasons:{},duel_reasons:{8:'尚未接觸'},tactic_reasons:{0:{}}};
const view={revision:8,game:{phase:'battle',player:'wei',battle,rng:{state:98,draws:4}},catalog:{battle_tactical:{schema:'tk2-battle-tactical-view-v1',battle_id:battle.id,map_id:'original-15',round:2,grid:{columns:31,rows:19,tile_size:16},side:'attackers',points,caps:{attackers:20,defenders:26},can_end:true,attack_cost:2,duel_cost:2,tactic_costs:Array(16).fill(6),actors:{7:row}}}};
const commands=[],context={view,actor:7,target:8,busy:false,battleDestination:null,GameBattleScene:scene,GameI18n:{locale:'zh-Hant'},escapeHtml:v=>String(v),gameAudio:{play(){}},renderBattle(){context.renders++;},renders:0,command:async(kind,payload)=>{commands.push({kind,payload});return true;}};
vm.createContext(context);vm.runInContext(source.slice(source.indexOf('function battleText('),source.indexOf('function tactics(')),context);
const snapshot=JSON.stringify(view);
assert.equal(context.battleTactical(),view.catalog.battle_tactical);assert.equal(context.battlePosition(7),battle.extended.tactical.positions[7]);
assert(context.battleTargetAllowed('attack'),'The backend target list, not a copied client distance rule, is authoritative');
assert(!context.battleTargetAllowed('duel'));assert.equal(context.battleActionReason('duel'),'尚未接觸');
assert.equal(context.tacticUnavailable({id:0},battle),'');assert.equal(context.tacticUnavailable({id:1},battle),'目前無法施放此計略。');
context.selectBattleCell({x:1,y:0});assert.equal(context.battleMoveQuote().cost,3);
assert.equal(commands.length,0,'Selecting a destination previews only');
(async()=>{
 assert(await context.confirmBattleMove());assert.deepEqual(JSON.parse(JSON.stringify(commands)),[{kind:'battle_move',payload:{battle_id:'battle-9',actor:7,x:1,y:0}}]);
 assert(await context.confirmBattleMove(),'The same officer is not locked by legacy b.used');assert.equal(commands.length,2);
 context.selectBattleCell({x:2,y:0});assert.equal(context.battleMoveQuote(),null);assert.equal(await context.confirmBattleMove(),false);assert.equal(commands.length,2);
 const previous=context.battleDestination;context.selectBattleCell({x:31,y:0});assert.equal(context.battleDestination,previous);context.selectBattleCell({x:.1,y:0});assert.equal(context.battleDestination,previous);
 context.battleDestination=null;context.navigateBattleCell(-1,-1);assert.deepEqual(JSON.parse(JSON.stringify(context.battleDestination)),{x:0,y:0});
 context.selectBattleCell({x:30,y:18});context.navigateBattleCell(1,1);assert.deepEqual(JSON.parse(JSON.stringify(context.battleDestination)),{x:30,y:18});
 context.selectBattleUnit('actor',7);assert.equal(context.battleDestination,null);context.selectBattleCell({x:1,y:0});
 context.busy=true;const renders=context.renders;context.selectBattleCell({x:0,y:1});assert.equal(context.renders,renders);assert.equal(await context.confirmBattleMove(),false);context.busy=false;
 row.can_act=false;assert.equal(await context.confirmBattleMove(),false);row.can_act=true;
 view.game.phase='result';assert(!context.battleTargetAllowed('attack'));assert.equal(await context.confirmBattleMove(),false);view.game.phase='battle';
 assert.equal(JSON.stringify(view),snapshot,'Selections, navigation, confirmations and labels never mutate the supplied game/RNG; only the command callback owns execution');
 for(const change of [v=>{v.catalog.battle_tactical.battle_id='other';},v=>{v.catalog.battle_tactical.map_id='original-01';},v=>{v.catalog.battle_tactical.round++;},v=>{v.catalog.battle_tactical.side='defenders';},v=>{v.catalog.battle_tactical.grid.rows=20;},v=>{v.game.battle.extended.tactical.schema='wrong';}]){const bad=JSON.parse(snapshot);change(bad);assert.equal(scene.tacticalView(bad),null);}
 for(const value of [{x:-1,y:0},{x:31,y:0},{x:0,y:19},{x:0,y:.5},null]){const bad=JSON.parse(snapshot);bad.game.battle.extended.tactical.positions[7]=value;assert.equal(scene.unitPosition(bad,7),null);}
 console.log('battle controls: authoritative positions/targets/costs, repeated same-officer commands, preview-only selection, invalid/busy/phase boundaries, bounded directional cursor and zero local state/RNG writes passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
