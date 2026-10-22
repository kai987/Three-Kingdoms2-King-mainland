/* Displayed attributes precede troop totals; pure officer labels keep troops near names. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const choices=require('../game/officer-choice.js');
const profile=(martial_strength=80,intellect=70,virtue=60)=>({martial_strength,intellect,virtue});
const person=(values={})=>({health:90,troops:100,loyalty:80,profile:profile(),...values});
const officers={
 1:person({profile:profile(81,1,1),health:1,troops:1}),
 2:person({profile:profile(80,71,1),health:1,troops:1}),
 3:person({profile:profile(80,70,61),health:1,troops:1}),
 4:person({health:91,troops:1}),
 5:person({troops:101}),
 6:person(),
 7:person({weapon_id:23,armor_id:7,experience:49999,loyalty:100}),
};
for(const officer of Object.values(officers)){Object.freeze(officer.profile);Object.freeze(officer);}
Object.freeze(officers);
const originalIds=Object.freeze([7,5,3,1,6,4,2]),before=JSON.stringify(officers);let reads=0;
assert.deepEqual(choices.sort(originalIds,id=>{reads++;return officers[id];}),[1,2,3,4,5,6,7]);
assert.equal(reads,originalIds.length,'Each ID is resolved once, independent of sort comparisons');
assert.equal(JSON.stringify(officers),before);assert.deepEqual(originalIds,[7,5,3,1,6,4,2]);
// More troops never outrank a difference in any earlier core attribute.
for(const field of ['martial_strength','intellect','virtue','health']){
 const low=person({troops:999}),high=person({troops:1});
 if(field==='health')high.health++;
 else high.profile={...high.profile,[field]:high.profile[field]+1};
 assert.deepEqual(choices.sort([9,8],id=>id===8?high:low),[8,9],field+' precedes troops');
}
// Recruitment keeps virtue primary, then intellect/martial/health/troops, then ID.
const recruitment={
 1:person({profile:profile(1,1,81),health:1,troops:1}),
 2:person({profile:profile(1,71,80),health:1,troops:1}),
 3:person({profile:profile(81,70,80),health:1,troops:1}),
 4:person({profile:profile(80,70,80),health:91,troops:1}),
 5:person({profile:profile(80,70,80),troops:101}),
 6:person({profile:profile(80,70,80)}),
 7:person({profile:profile(80,70,80)}),
};
assert.deepEqual(choices.sort([7,6,5,4,3,2,1],id=>recruitment[id],'virtue'),[1,2,3,4,5,6,7]);
for(const ids of [[7,6],[6,7]])assert.deepEqual(choices.sort(ids,id=>officers[id]),[6,7],'Complete ties use stable IDs');
assert.deepEqual(choices.sort(['10','2','1'],()=>person()),['1','2','10'],'String runtime IDs retain numeric order and original types');
assert.deepEqual(choices.sort(['x','a','b'],()=>person()),['a','b','x'],'Non-numeric test identities have deterministic code-unit order');
assert.deepEqual(choices.sort([2,1],id=>id===1?person():{profile:{},health:NaN,troops:Infinity}),[1,2]);
assert.throws(()=>choices.sort([],()=>person(),'troops'),RangeError);assert.throws(()=>choices.sort([],null),TypeError);
const guan=person({profile:profile(97,75,70),health:97,troops:300});
assert.equal(choices.label('关羽',guan),'关羽 · 300兵 · 武97 · 知75 · 德70 · 体力97');
assert.equal(choices.label('关羽',guan,{loyalty:true}),'关羽 · 300兵 · 武97 · 知75 · 德70 · 体力97 · 忠誠80');
const unchanged=JSON.stringify(guan);
assert.equal(choices.label('关羽',guan,{troops:0,health:1,loyalty:true}),'关羽 · 0兵 · 武97 · 知75 · 德70 · 体力1 · 忠誠80');
assert.equal(JSON.stringify(guan),unchanged,'Battle display overrides do not change stored troops/health');
assert.equal(choices.label('待考',{}),'待考 · —兵 · 武— · 知— · 德— · 体力—');
assert(choices.label('<名>',guan).startsWith('<名> · 300兵'),'Label remains plain text for caller HTML escaping');
// Browser and Node receive the same pure interface without document/storage/RNG dependencies.
const browser={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../game/officer-choice.js'),'utf8'),browser);
assert.equal(browser.window.GameOfficerChoices.label('关羽',guan),choices.label('关羽',guan));
assert.deepEqual(Array.from(browser.window.GameOfficerChoices.sort(originalIds,id=>officers[id])),[1,2,3,4,5,6,7]);
assert(Object.isFrozen(choices));
console.log('officer choices: name/troops-first labels, full core-stat tie order before troops, virtue recruitment, stable IDs, battle overrides and pure browser/Node interface passed');
