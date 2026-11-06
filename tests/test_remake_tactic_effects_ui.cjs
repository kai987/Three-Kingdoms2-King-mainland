'use strict';
const assert=require('node:assert/strict'),effects=require('../game/tactic-effects.js'),events=require('../game/events.js');
const fire={schema:'tk2-tactic-effect-preview-v1',tactic:5,success_percent:60,affected_side:'defenders',grain_before:200,grain_loss_min:38,grain_loss_max:46};
const refusal={schema:'tk2-tactic-effect-preview-v1',tactic:8,success_percent:0,target_loyalty:71,guaranteed_failure:true};
const view={catalog:{battle_tactical:{tactic_costs:[6,5,4,6,7,8,8,8,10],actors:{1:{tactic_previews:{5:{2:fire},8:{2:refusal}}}}}}};
const snapshot=JSON.stringify(view);
assert(effects.summary(view,1,2,5).includes('敵軍隨軍糧 200'));
assert(effects.summary(view,1,2,5).includes('携行兵糧 200'));
assert(effects.summary(view,1,2,8,{locale:'ja'}).includes('機動力10'));
assert(effects.summary(view,1,2,8).includes('必定失敗'));
assert.equal(effects.summary(view,1,3,8),'');assert.equal(JSON.stringify(view),snapshot,'Forecast rendering is read-only');
for(const patch of [{schema:'bad'},{success_percent:-1},{success_percent:101},{grain_loss_max:201},{grain_before:'200'},{affected_side:'other'}]){const broken=structuredClone(view);Object.assign(broken.catalog.battle_tactical.actors[1].tactic_previews[5][2],patch);assert.equal(effects.forecast(broken,1,2,5),null);}
const event=details=>({id:1,kind:'tactic',year:217,month:7,day:1,turn:1,person_ids:['actor','target'],city_ids:['city'],factions:['wei','wu'],audience:'player',details});
const burned={tactic:5,success:true,affected_side:'defenders',grain_before:200,grain_after:158,grain_loss:42};
const failed={tactic:8,success:false,success_percent:0,target_loyalty:71,guaranteed_failure:true};
assert(events.validEvent(event({tactic:5,success:false})),'Retain genuine compact historical snapshots');
assert(events.validEvent(event(burned)));assert(events.validEvent(event(failed)));
for(const patch of [{grain_after:159},{grain_loss:-1},{success:false},{tactic:8},{extra:0},{affected_side:'city'}])assert(!events.validEvent(event({...burned,...patch})),JSON.stringify(patch));
for(const patch of [{success:true},{success_percent:1},{target_loyalty:70},{guaranteed_failure:false},{success_percent:true}])assert(!events.validEvent(event({...failed,...patch})),JSON.stringify(patch));
for(const source of [burned,failed])for(const key of Object.keys(source)){const missing={...source};delete missing[key];assert(!events.validEvent(event(missing)),'Partial snapshot '+key);}
const phantom={schema:'tk2-tactic-effect-preview-v1',tactic:2,success_percent:60,condition:'phantom',condition_count:3,target_count:0};
const statusView=structuredClone(view);statusView.catalog.battle_tactical.actors[1].tactic_previews[2]={2:phantom};
statusView.game={battle:{extended:{conditions:{schema:'tk2-battle-conditions-v1',day:1,units:{1:{kind:'phantom',remaining:3},2:{kind:'phantom',remaining:2}}}}}};
const statusBefore=JSON.stringify(statusView);
assert(effects.summary(statusView,1,2,2).includes('仍可攻擊或施計'));assert(effects.summary(statusView,1,2,2,{locale:'ja'}).includes('固定の行動不能ターン数ではありません'));
assert(effects.summary(statusView,1,2,0).includes('data-phantom-clear-preview="2"'),'Other tactics disclose clearing before failure too');
assert(effects.summary(statusView,1,2,11).includes('data-phantom-clear-preview="3"'),'Ambush addresses actual self, never the ignored enemy parameter');
for(const patch of [{condition:'stun'},{condition_count:1},{condition_count:true},{target_count:-1},{target_count:10}]){const broken=structuredClone(statusView);Object.assign(broken.catalog.battle_tactical.actors[1].tactic_previews[2][2],patch);assert.equal(effects.forecast(broken,1,2,2),null);}
assert.equal(JSON.stringify(statusView),statusBefore,'Status rendering never advances the clock or removes a condition');
for(const details of [{tactic:2,success:true,condition:'phantom',condition_count:3},{tactic:2,success:true,condition:'phantom',condition_count:2},{tactic:2,success:false,condition:'phantom',condition_count:0}])assert(events.validEvent(event(details)));
for(const patch of [{condition:'chain'},{condition_count:true},{condition_count:1},{condition_count:0},{success:false},{extra:1}])assert(!events.validEvent(event({tactic:2,success:true,condition:'phantom',condition_count:3,...patch})));
console.log('tactic forecasts: original conversion threshold, carried-grain intervals, bilingual cost disclosure, invalid-data rejection, strict committed snapshots and pure reads passed');
// Connected water targets retain BFS order and independent duration ranges.
const chain={schema:'tk2-tactic-effect-preview-v1',tactic:10,success_percent:74,condition:'chain',count_min:4,count_max:5,target_ids:['9','2','7']};
const chainView=structuredClone(statusView);chainView.catalog.battle_tactical.actors[1].tactic_previews[10]={2:chain};
chainView.game.battle.extended.conditions.units[2]={kind:'chain',remaining:5};
const chainBefore=JSON.stringify(chainView);
assert(effects.summary(chainView,1,2,10).includes('3 支水上敵隊各自抽取計數 4–5'));
assert(effects.summary(chainView,1,2,10,{locale:'ja'}).includes('陸上の敵は接続を伝えるだけ'));
assert(effects.summary(chainView,1,2,2).includes('data-chain-clear-preview="5"'),'Phantom can target and disclose clearing an existing chain5');
assert(effects.forecast(chainView,1,2,2));
assert(effects.summary(chainView,1,2,11).includes('data-phantom-clear-preview="3"'),'Self-target remains distinct');
for(const patch of [{condition:'phantom'},{count_min:2},{count_max:6},{count_min:true},{target_ids:['2']},{target_ids:['2','2']},{target_ids:['2',3]},{target_ids:Array.from({length:21},(_,i)=>String(i))}]){const broken=structuredClone(chainView);Object.assign(broken.catalog.battle_tactical.actors[1].tactic_previews[10][2],patch);assert.equal(effects.forecast(broken,1,2,10),null,JSON.stringify(patch));}
assert.equal(JSON.stringify(chainView),chainBefore,'Chain forecasts do not draw or modify the saved state');
const chained={tactic:10,success:true,condition:'chain',condition_counts:[{id:'9',remaining:5},{id:'2',remaining:4}]};
assert(events.validEvent(event(chained)));assert(events.validEvent(event({tactic:10,success:false,condition:'chain',condition_counts:[]})));assert(events.validEvent(event({tactic:10,success:true})),'Old compact chain events remain accepted');
for(const patch of [{condition:'phantom'},{success:false},{condition_counts:[]},{condition_counts:[{id:'2',remaining:3}]},{condition_counts:[{id:'2',remaining:3},{id:'2',remaining:4}]},{condition_counts:[{id:2,remaining:3},{id:'3',remaining:4}]},{condition_counts:[{id:'2',remaining:2},{id:'3',remaining:4}]},{condition_counts:[{id:'2',remaining:true},{id:'3',remaining:4}]},{condition_counts:[{id:'2',remaining:3,extra:0},{id:'3',remaining:4}]},{extra:0}])assert(!events.validEvent(event({...chained,...patch})),JSON.stringify(patch));
for(const key of Object.keys(chained)){const partial=structuredClone(chained);delete partial[key];assert(!events.validEvent(event(partial)),'Incomplete chain snapshot '+key);}
console.log('chain forecasts: BFS target order, independent side ranges, mixed state clears and strict bilingual event snapshots passed');

for(const length of [11,20]){
 const expanded=structuredClone(chainView);expanded.catalog.battle_tactical.actors[1].tactic_previews[10][2].target_ids=Array.from({length},(_,i)=>String(i));
 assert(effects.forecast(expanded,1,2,10),'Converted armies may exceed ten original-side units');
 assert(events.validEvent(event({...chained,condition_counts:Array.from({length},(_,i)=>({id:String(i),remaining:4}))})));
}
assert(!events.validEvent(event({...chained,condition_counts:Array.from({length:21},(_,i)=>({id:String(i),remaining:4}))})));
const qimen={schema:'tk2-tactic-effect-preview-v1',tactic:15,success_percent:80,condition:'qimen',count_min:6,count_max:9,daily_loss_min:80,daily_loss_max:150,source_present:true};
const qView=structuredClone(chainView);qView.catalog.battle_tactical.actors[1].tactic_previews[15]={2:qimen};qView.game.battle.extended.conditions.units[2]={kind:'qimen',remaining:9};
const qBefore=JSON.stringify(qView);
assert(effects.summary(qView,1,2,15).includes('最後一次也損兵'));assert(effects.summary(qView,1,2,15,{locale:'ja'}).includes('自軍の盾ではなく'));
assert(effects.summary(qView,1,2,2).includes('data-qimen-clear-preview="9"'));assert(effects.forecast(qView,1,2,2));
for(const patch of [{condition:'guard'},{count_min:4},{count_max:8},{daily_loss_min:79},{daily_loss_max:151},{source_present:1}]){const bad=structuredClone(qView);Object.assign(bad.catalog.battle_tactical.actors[1].tactic_previews[15][2],patch);assert.equal(effects.forecast(bad,1,2,15),null);}
assert.equal(JSON.stringify(qView),qBefore);
const qcast={tactic:15,success:true,condition:'qimen',qimen_phase:'cast',condition_count:9};
assert(events.validEvent(event(qcast)));assert(events.validEvent(event({...qcast,success:false,condition_count:0})));
for(const patch of [{condition_count:4},{condition_count:10},{condition_count:true},{qimen_phase:'daily'},{success:false},{extra:1}])assert(!events.validEvent(event({...qcast,...patch})));
const qtick={id:'2',before:1,remaining:0,troops_before:99,troops_after:0,loss:99};
const qdaily={tactic:15,success:true,condition:'qimen',qimen_phase:'daily',qimen_ticks:[qtick],experience_id:'1',experience_gain:0};
assert(events.validEvent(event(qdaily)));assert(events.validEvent(event({...qdaily,qimen_ticks:[{...qtick,troops_before:0,loss:0}]})));
for(const patch of [{success:false},{experience_gain:2551},{experience_gain:true},{qimen_ticks:[]},{qimen_ticks:[qtick,qtick]},{qimen_ticks:[{...qtick,remaining:1}]},{qimen_ticks:[{...qtick,troops_after:1}]},{qimen_ticks:[{...qtick,loss:79,troops_before:79,troops_after:0,extra:1}]}])assert(!events.validEvent(event({...qdaily,...patch})),JSON.stringify(patch));
console.log('Qimen: bilingual enemy forecasts, source pause, high count clears and strict cast/daily receipts passed');
