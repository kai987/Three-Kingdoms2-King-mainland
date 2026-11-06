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
for(const patch of [{condition:'stun'},{condition_count:1},{condition_count:true},{target_count:-1},{target_count:4}]){const broken=structuredClone(statusView);Object.assign(broken.catalog.battle_tactical.actors[1].tactic_previews[2][2],patch);assert.equal(effects.forecast(broken,1,2,2),null);}
assert.equal(JSON.stringify(statusView),statusBefore,'Status rendering never advances the clock or removes a condition');
for(const details of [{tactic:2,success:true,condition:'phantom',condition_count:3},{tactic:2,success:true,condition:'phantom',condition_count:2},{tactic:2,success:false,condition:'phantom',condition_count:0}])assert(events.validEvent(event(details)));
for(const patch of [{condition:'chain'},{condition_count:true},{condition_count:1},{condition_count:0},{success:false},{extra:1}])assert(!events.validEvent(event({tactic:2,success:true,condition:'phantom',condition_count:3,...patch})));
console.log('tactic forecasts: original conversion threshold, carried-grain intervals, bilingual cost disclosure, invalid-data rejection, strict committed snapshots and pure reads passed');
