'use strict';
const assert=require('node:assert/strict');
const {api,attach,consume,exhaust}=require('./fixtures/command-books.cjs');
const view=attach({catalog:{},game:{player:'wei',turn:3,rng:{state:77,draws:2},cities:{first:{owner:'wei',action_used:true},second:{owner:'wei'},enemy:{owner:'wu'}}}},3);
const snapshot=JSON.stringify(view);
assert.equal(api.row(view).remaining,3);assert(api.can(view,'recruit'));assert(api.can(view,'allocate'));assert.equal(api.cost(view,'allocate'),1);
assert.equal(api.summary(view), '命令書 剩餘 3/3');assert.equal(api.summary(view,{locale:'ja',kind:'recruit'}),'命令書 残り 3/3 · 今回消費 1枚');
assert(api.html(view,{kind:'allocate'}).includes('data-command-book-cost="1"'));assert(api.html(view).includes('data-command-books-total="3"'));
assert.equal(JSON.stringify(view),snapshot,'Read-only source rows, render, descriptions and prices never consume game state or RNG');
for(let i=0;i<3;i++){assert(api.can(view,'recruit'));consume(view,'recruit');}
assert.equal(api.row(view).remaining,0);assert(!api.can(view,'recruit'));assert(!api.can(view,'allocate'));
assert(api.can(view,'set_governor'));assert(api.can(view,'set_facility_policy'));assert(api.can(view,'reject_staff'));
assert(api.reason(view,'recruit').includes('剩餘0'));assert(api.reason(view,'recruit','ja').includes('残り0枚'));assert.equal(api.reason(view,'set_governor'),'');
assert.equal(api.row(view,'wu').remaining,3,'Other factions own independent books');
for(const change of [v=>{v.catalog.command_books.turn++;},v=>{v.catalog.command_books.schema='old';},v=>{v.catalog.command_books.factions.wei.remaining=-1;},v=>{v.catalog.command_books.factions.wei.used=.5;},v=>{v.catalog.command_books.factions.wei.total=99;}]){
 const bad=JSON.parse(snapshot);change(bad);assert.equal(api.row(bad),null);assert(!api.can(bad,'recruit'));assert(api.reason(bad,'recruit').includes('命令書'));
}
assert.equal(api.cost(view,'unknown'),null);assert(!api.can(view,'unknown'));
const malformed=JSON.parse(snapshot);malformed.catalog.command_books.costs.recruit='<script>';assert.equal(api.cost(malformed,'recruit'),null);assert(!api.html(malformed,{kind:'recruit'}).includes('<script>'));
assert.equal(api.summary({}), '');
const paid=JSON.parse(snapshot);exhaust(paid);
paid.catalog.command_books.factions.wei.allocation_flow={id:'3:wei:first:1',city:'first',source:'recruit'};
const continuation={city:'first',flow:'3:wei:first:1'};
assert.equal(api.cost(paid,'allocate',continuation),0);assert(api.can(paid,'allocate',continuation));
assert.equal(api.reason(paid,'allocate','ja',continuation),'');
assert(api.html(paid,{kind:'allocate',...continuation}).includes('data-command-book-cost="0"'));
assert(!api.html(paid,{kind:'allocate',...continuation,locale:'ja'}).includes('今旬は使い切りました'));
for(const options of [{city:'first',flow:null},{city:'first'},{city:'second',flow:continuation.flow},{city:'first',flow:'stale'}]){
 assert.equal(api.cost(paid,'allocate',options),1);assert(!api.can(paid,'allocate',options),'Only the matching city and paid flow continue for free');
}
assert.equal(api.cost(paid,'allocate',{...continuation,owner:'wu'}),1,'A different faction cannot borrow this allocation payment');
assert.equal(api.activeAllocation(paid,'first').id,continuation.flow);assert.equal(api.activeAllocation(paid,'second'),null);
assert.equal(api.cost(paid,'allocation_close'),0);
// Exercise the real dialog's deferred close hook, including confirmation and
// save/load races; callbacks may never close a replacement paid allocation.
const fs=require('node:fs'),vm=require('node:vm'),source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const timers=[],closed=[],dialogContext={view:paid,GameCommandBooks:api,busy:false,
 allocationCloseEpoch:0,allocationDialogContext:{city:'first',flow:continuation.flow},
 orderConfirmation:{pending:false},setTimeout(callback){timers.push(callback);},
 command:async(kind,payload)=>{closed.push({kind,payload});return true;}};
vm.createContext(dialogContext);
vm.runInContext(source.slice(source.indexOf('function resetAllocationDialogs('),source.indexOf('async function confirmOrderCommand('))+
 source.slice(source.indexOf('function queueAllocationClose('),source.indexOf('function openDialog(')),dialogContext);
dialogContext.queueAllocationClose({city:'first',flow:null});assert.equal(timers.length,0);
dialogContext.queueAllocationClose({city:'first',flow:continuation.flow});assert.equal(closed.length,0,'Dialog close schedules rather than changes game state synchronously');
dialogContext.busy=true;timers.shift()();assert.equal(closed.length,0);assert.equal(timers.length,1);
dialogContext.busy=false;dialogContext.orderConfirmation.pending=true;timers.shift()();assert.equal(closed.length,0,'A pending paid-order confirmation cannot discard the close callback');
dialogContext.orderConfirmation.pending=false;timers.shift()();assert.equal(closed.length,1);assert.equal(closed[0].kind,'allocation_close');assert.equal(closed[0].payload.flow,continuation.flow);
dialogContext.queueAllocationClose({city:'first',flow:continuation.flow});paid.catalog.command_books.factions.wei.allocation_flow.id='replacement';timers.shift()();assert.equal(closed.length,1,'Old exact IDs cannot close replacement workflows');
dialogContext.queueAllocationClose({city:'first',flow:'replacement'});dialogContext.resetAllocationDialogs();timers.shift()();assert.equal(closed.length,1,'Loading or starting a campaign cancels old callbacks, even when a saved flow ID matches');assert.equal(dialogContext.allocationDialogContext,null);
view.catalog.command_books.turn=4;view.game.turn=4;attach(view,3);assert.equal(api.row(view).remaining,3);
exhaust(view);assert.equal(api.row(view).used,3);
console.log('command books UI: authoritative shared pools/costs, same-city eligibility, allocation spending, faction isolation, exhaustion/free management, bilingual output, invalid/stale data and zero RNG/state writes passed');
