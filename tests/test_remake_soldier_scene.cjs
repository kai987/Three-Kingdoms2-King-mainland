/* Validate untrusted transient soldier receipts without touching game state. */
'use strict';
const assert=require('node:assert/strict'),scene=require('../game/battle-scene.js');
const clone=value=>JSON.parse(JSON.stringify(value));
const units=[{id:1,side:'attackers',troops:1000,health:80,energy:18,guard:0,stunned:0},{id:2,side:'defenders',troops:1000,health:80,energy:18,guard:0,stunned:0}];
const officers={1:{profile:{terrain_affinity:0}},2:{profile:{terrain_affinity:2}}};
assert.deepEqual(scene.troopMarkers(units,officers),[{id:1,side:'attackers',type:'平',teams:10,troops:1000},{id:2,side:'defenders',type:'水',teams:10,troops:1000}]);
assert.deepEqual([0,1,99,100,101,999,1000].map(troops=>scene.troopMarkers([{...units[0],troops}],officers)[0].teams),[0,1,1,1,2,10,10]);
const snapshot={round:1,outcome:null,duel:null,units};
assert(scene.validSnapshot(snapshot));assert(!scene.validSnapshot({...snapshot,units:[{...units[0],troops:1001},units[1]]}));
const row={schema:'tk2-siege-v1',mode:'field',actor:1,target:2,fort:null,map_id:'original-09',cell:{x:8,y:9},stage:'combat',round:1,events:[],units:[
 {id:'a0',side:'attackers',kind:'general',x:1,y:5,troops:0,health:80,withdrawn:false},
 {id:'a1',side:'attackers',kind:'infantry',x:7,y:5,troops:100,health:100,withdrawn:false},
 {id:'d0',side:'defenders',kind:'general',x:14,y:5,troops:0,health:80,withdrawn:false},
 {id:'d1',side:'defenders',kind:'cavalry',x:8,y:5,troops:100,health:100,withdrawn:false},
]};
const after=clone(row);after.round++;after.units[3].troops=after.units[3].health=68;
after.events=[{kind:'melee',actor:'a1',target:'d1',from:{x:7,y:5},to:{x:8,y:5},loss:32}];
const receipt={schema:'tk2-battle-presentation-v1',revision:4,scenes:[{kind:'soldier_step',battle_id:'controlled',actor:1,target:2,own:'attackers',counter:false,tactic:null,effect:null,success:true,skipped:false,move:null,reply:null,before:snapshot,after:{...clone(snapshot),units:[units[0],{...units[1],troops:968}]},soldiers:{before:row,after}}]};
const frozen=JSON.stringify(receipt);assert(scene.validSoldiers(row));assert(scene.validSoldierScene(receipt.scenes[0]));
const resumed=clone(receipt);delete resumed.scenes[0].soldiers.before.mode;delete resumed.scenes[0].soldiers.before.events;resumed.scenes[0].soldiers.before.fort=2;resumed.scenes[0].soldiers.after.mode='siege';resumed.scenes[0].soldiers.after.fort=2;assert.equal(scene.receiptScenes(resumed,'controlled',4).length,1,'The first actual step from a released group-only siege save still animates');
assert.deepEqual(scene.receiptScenes(receipt,'controlled',4),receipt.scenes);assert.equal(JSON.stringify(receipt),frozen);
assert.deepEqual(scene.receiptScenes(receipt,'controlled',3),[],'A stale animation cannot be replayed for another command');
for(const tamper of [
 value=>delete value.soldiers.after.events,
 value=>value.soldiers.after.events[0].loss=101,
 value=>value.soldiers.after.events[0].actor='d11',
 value=>value.soldiers.after.events[0].to.x=16,
 value=>value.soldiers.after.events[0].kind='execute-code',
 value=>value.soldiers.after.units[0].side='defenders',
 value=>value.soldiers.after.units[1].troops=101,
 value=>value.soldiers.after.units.push(clone(value.soldiers.after.units[1])),
 value=>value.soldiers.after.events=Array(45).fill(value.soldiers.after.events[0]),
]){const invalid=clone(receipt);tamper(invalid.scenes[0]);assert.deepEqual(scene.receiptScenes(invalid,'controlled',4),[]);}
const converted=clone(receipt);converted.scenes[0]={...converted.scenes[0],kind:'tactic',tactic:8,effect:'surrender'};delete converted.scenes[0].soldiers;converted.scenes[0].after.units[1].side='attackers';assert.equal(scene.receiptScenes(converted,'controlled',4).length,1,'A successful surrender can change only the selected enemy side');
converted.scenes[0].success=false;assert.deepEqual(scene.receiptScenes(converted,'controlled',4),[]);
converted.scenes[0].success=true;converted.scenes[0].effect='fire';assert.deepEqual(scene.receiptScenes(converted,'controlled',4),[]);
assert(scene.duration(receipt.scenes[0])>=360);const many=clone(receipt.scenes[0]);many.soldiers.after.events=Array(44).fill(after.events[0]);assert(scene.duration(many)<=3600,'A complete soldier turn has bounded replay time');
console.log('soldier scene:1000-person marker counts, immutable current-revision receipts, per-piece event bounds, safe surrender side changes and finite playback passed');
