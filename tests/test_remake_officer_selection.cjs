/* Selection capacity guards keep selected members removable and permanent blockers intact. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const selection=require('../game/officer-selection.js');
class Checkbox{
 constructor(value,{checked=false,disabled=false}={}){this.value=String(value);this.checked=checked;this.disabled=disabled;this.listeners=new Map();}
 addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);this.listeners.get(type).push(fn);}
 change(checked,{force=false}={}){if(this.disabled&&!force)return false;this.checked=checked;for(const fn of this.listeners.get('change')||[])fn({target:this});return true;}
}
const ids=controller=>controller.selectedIds();
// Actual ten-member deployment: the eleventh eligible member is disabled,
// while the ten selected members remain enabled so any one can be removed.
const deployed=Array.from({length:15},(_,id)=>new Checkbox(id)),blocked=new Checkbox(100,{disabled:true}),events=[];
const controls=selection.bind([...deployed,blocked],{limit:10,onChange:s=>events.push(s)});
assert.equal(events.length,1);assert.deepEqual(events[0],{ids:[],count:0,limit:10,trimmedIds:[]});
for(let id=0;id<10;id++)assert(deployed[id].change(true));
assert.equal(ids(controls).length,10);assert(deployed.slice(0,10).every(input=>!input.disabled));assert(deployed.slice(10).every(input=>input.disabled));assert(blocked.disabled);
assert.equal(deployed[10].change(true),false);assert.equal(ids(controls).length,10);
assert(deployed[4].change(false));assert(deployed.filter((_,i)=>i!==4).every(input=>!input.disabled));assert(blocked.disabled);assert.equal(events.at(-1).count,9);
assert(deployed[10].change(true));assert.equal(ids(controls).length,10);assert(deployed[4].disabled);assert(!deployed[10].disabled);
// A destination capacity shrink removes the latest chosen members, not the
// strongest/first displayed member; returned IDs retain the original DOM order.
const transfer=[new Checkbox(1),new Checkbox(2),new Checkbox(3),new Checkbox(4)],updates=[];
const moving=selection.bind(transfer,{limit:4,onChange:s=>updates.push(s)});
transfer[2].change(true);transfer[0].change(true);transfer[3].change(true);
assert.deepEqual(ids(moving),[1,3,4]);
const shrunk=moving.setLimit(2);assert.deepEqual(shrunk.trimmedIds,[4]);assert.deepEqual(ids(moving),[1,3]);assert(transfer[3].disabled&&!transfer[0].disabled&&!transfer[2].disabled);
const smaller=moving.setLimit(1);assert.deepEqual(smaller.trimmedIds,[1]);assert.deepEqual(ids(moving),[3]);
moving.setLimit(3);assert(transfer.every(input=>!input.disabled));
assert(transfer[1].change(true));assert.deepEqual(ids(moving),[2,3]);
const full=moving.setLimit(0);assert.deepEqual(full.trimmedIds,[2,3]);assert.deepEqual(ids(moving),[]);assert(transfer.every(input=>input.disabled));
moving.setLimit(99);assert(transfer.every(input=>!input.disabled));
// Restored drafts trim the final DOM selections deterministically. A stale
// checked unavailable officer is cleared without ever becoming selectable.
const draft=[new Checkbox(9,{checked:true}),new Checkbox(8,{checked:true}),new Checkbox(7,{checked:true}),new Checkbox(6,{checked:true,disabled:true})];
const restored=selection.bind(draft,{limit:2});assert.deepEqual(ids(restored),[9,8]);assert.equal(draft[2].checked,false);assert.equal(draft[3].checked,false);assert(draft[3].disabled);
restored.setLimit(20);assert(!draft[2].disabled);assert(draft[3].disabled);
// A forged/programmatic extra selection cannot bypass capacity. Normal updates
// also reconcile direct checkbox edits before confirmation, without events.
restored.setLimit(1);assert.deepEqual(ids(restored),[9]);draft[2].change(true,{force:true});assert.deepEqual(ids(restored),[9]);assert.equal(draft[2].checked,false);
draft[0].checked=false;draft[1].checked=true;restored.update();assert.deepEqual(ids(restored),[8]);assert(draft[0].disabled);assert(!draft[1].disabled);
const external=ids(restored);external.push(999);assert.deepEqual(ids(restored),[8],'Returned IDs never expose internal selection storage');
// Optional eligibility may become stricter while a dialog is open; captured
// permanent blockers stay blocked even when dynamic eligibility later allows.
let healthy=true;const changing=[new Checkbox(1),new Checkbox(2,{disabled:true})];
const dynamic=selection.bind(changing,{limit:2,isEligible:input=>input.value!=='1'||healthy});changing[0].change(true);healthy=false;dynamic.refresh();assert.deepEqual(ids(dynamic),[]);assert(changing[0].disabled&&changing[1].disabled);healthy=true;dynamic.update();assert(!changing[0].disabled&&changing[1].disabled);
// Callback-driven route estimates can reapply the current limit safely. A
// subsequent genuine limit change is reported after the current callback.
let controller,callbackCount=0;const recursion=[new Checkbox(1),new Checkbox(2)];
controller=selection.bind(recursion,{limit:2,onChange:s=>{callbackCount++;if(controller)controller.setLimit(s.limit);}});assert.equal(callbackCount,1);recursion[0].change(true);assert.equal(callbackCount,2);controller.refresh();assert.equal(callbackCount,2);
let nested;const nesting=[new Checkbox(1),new Checkbox(2)],seen=[];
nested=selection.bind(nesting,{limit:2,onChange:s=>{seen.push(s.limit);if(nested&&s.count===2&&s.limit===2)nested.setLimit(1);}});nesting[0].change(true);nesting[1].change(true);assert.deepEqual(seen,[2,2,2,1]);assert.deepEqual(ids(nested),[1]);
for(const bad of [-4,NaN,Infinity]){moving.setLimit(bad);assert.equal(moving.update().limit,0);assert(transfer.every(input=>input.disabled));}
moving.setLimit(2.9);assert.equal(moving.update().limit,2);
const excluded=new Checkbox(44);selection.bind([excluded],{limit:1,isEligible:()=>0});assert(excluded.disabled);
const empty=selection.bind([],{limit:0});assert.deepEqual(ids(empty),[]);assert.equal(empty.setLimit(99).count,0);
// No browser globals or game objects are required by this DOM-only binder.
const browser={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../game/officer-selection.js'),'utf8'),browser);const native=browser.window.GameOfficerSelection.bind([new Checkbox(10)],{limit:1});assert.deepEqual(Array.from(native.selectedIds()),[]);assert(Object.isFrozen(selection));
console.log('officer selection: ten-member limit, checked uncheck, permanent blockers, destination shrink, latest-pick trimming, zero capacity, estimates and browser/Node interface passed');
