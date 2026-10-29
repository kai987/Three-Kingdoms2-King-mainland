'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const confirmation=require('../game/order-confirm.js'),{api:books,attach}=require('./fixtures/command-books.cjs');
function fixture(){
 let view=attach({revision:7,catalog:{scenario_id:'test'},game:{turn:2,player:'shu',rng:{state:99,draws:3},officers:{1:{troops:80},2:{troops:30}},cities:{chengdu:{owner:'shu'},other:{owner:'shu'}}}},3);
 const listeners=new Map(),buttons=new Map(),sounds=[];
 const original={isConnected:true,focus(){this.focused=true;}};
 const dialog={open:false,dataset:{},innerHTML:'',addEventListener(k,f){listeners.set('dialog:'+k,f);},removeEventListener(k){listeners.delete('dialog:'+k);},
  querySelector(id){if(!buttons.has(id))buttons.set(id,{focus(){this.focused=true;}});return buttons.get(id);},
  showModal(){this.open=true;},close(){this.open=false;listeners.get('dialog:close')?.();}};
 const doc={activeElement:original,visibilityState:'visible',getElementById:id=>id==='order-confirm-dialog'?dialog:null,
  addEventListener(k,f){listeners.set('doc:'+k,f);},removeEventListener(k){listeners.delete('doc:'+k);}};
 const i18n={locale:'zh-Hant',apply(){},t:(value,language)=>language==='ja'?value.replace('成都','成都'):value};
 const ui=confirmation.create({document:doc,books,getView:()=>view,cityName:id=>id==='chengdu'?'成都':'別城',i18n,onSound:cue=>sounds.push(cue)});
 return{ui,doc,dialog,buttons,listeners,sounds,original,i18n,get view(){return view;},set view(value){view=value;},click:id=>dialog.querySelector(id).onclick()};
}
(async()=>{
 const h=fixture(),before=JSON.stringify(h.view);
 for(const[kind,amount]of Object.entries(h.view.catalog.command_books.costs))if(amount>0){
  assert(confirmation.ACTIONS[kind],kind+' requires a human action name');
  for(const locale of ['zh-Hant','ja']){
   const quote=confirmation.quote(h.view,kind,{city:'chengdu'},{books,locale,cityName:()=> '成都'});
   assert.equal(quote.amount,1);assert(quote.message.includes('成都'));assert(quote.message.includes(quote.action));assert(quote.message.includes(locale==='ja'?'1枚':'1張'));
  }
 }
 let pending=h.ui.ask('allocate',{city:'chengdu',flow:null});
 assert(h.ui.pending);assert(h.dialog.open);assert.equal(h.dialog.dataset.commandBookCost,'1');
 assert(h.dialog.innerHTML.includes('將消耗1張命令書'));assert(h.dialog.innerHTML.includes('命令書1枚'));
 assert.equal(await h.ui.ask('recruit',{city:'chengdu'}),false,'A second pending action cannot replace the first confirmation');
 h.click('#order-confirm-cancel');assert.equal(await pending,false);assert(!h.ui.pending);assert(!h.dialog.open);assert(h.original.focused);
 assert.equal(JSON.stringify(h.view),before,'Opening and cancelling never mutate the campaign or RNG');
 for(const locale of ['zh-Hant','ja']){
  const batch={city:'chengdu',allocations:[{officer:1,troops:100},{officer:2,troops:25}],flow:null};
  const quote=confirmation.quote(h.view,'allocate',batch,{books,locale,cityName:()=> '成都'});
  assert.equal(quote.allocation_count,2);assert.equal(quote.allocation_delta,15);assert.equal(quote.amount,1);
  assert(quote.message.includes(locale==='ja'?'2人を一括編制':'整批編兵2名'));assert(quote.message.includes('15'));assert(quote.message.includes('成都'));
 }
 pending=h.ui.ask('recruit',{city:'chengdu'});let prevented=false;h.listeners.get('dialog:cancel')({preventDefault(){prevented=true;}});assert(prevented);assert.equal(await pending,false);
 pending=h.ui.ask('depart',{source:'chengdu',target:'other'});h.click('#order-confirm-accept');assert.equal(await pending,true);assert.equal(JSON.stringify(h.view),before,'Approval alone is read-only; the application sends the command afterwards');
 pending=h.ui.ask('recruit',{city:'chengdu'});h.view={...h.view,revision:h.view.revision+1};h.click('#order-confirm-accept');assert.equal(await pending,false,'A stale confirmation cannot execute a later campaign revision');
 pending=h.ui.ask('recruit',{city:'chengdu'});h.listeners.get('dialog:close')();assert(h.ui.pending,'An old asynchronously queued close event cannot cancel a new open prompt');h.click('#order-confirm-cancel');assert.equal(await pending,false);
 pending=h.ui.ask('recruit',{city:'chengdu'});const costs=h.view.catalog.command_books.costs;h.view.catalog.command_books.costs=null;h.click('#order-confirm-accept');assert.equal(await pending,false,'A repricing failure must settle as cancellation rather than hang');h.view.catalog.command_books.costs=costs;
 const absent={...h.view,catalog:{...h.view.catalog,command_books:null}};assert.throws(()=>confirmation.quote(absent,'recruit',{city:'chengdu'},{books}),/命令書/,'Known paid operations fail closed when pricing metadata is missing');
 pending=h.ui.ask('recruit',{city:'chengdu'});h.doc.visibilityState='hidden';h.listeners.get('doc:visibilitychange')();assert.equal(await pending,false);h.doc.visibilityState='visible';
 const row=books.row(h.view);row.used=row.total;row.remaining=0;row.allocation_flow={id:'flow-paid',city:'chengdu',source:'recruit'};
 assert.equal(await h.ui.ask('allocate',{city:'chengdu',flow:'flow-paid'}),true,'An already-paid continuation never opens a second payment prompt, even after the last book');assert(!h.dialog.open);
 assert.equal(await h.ui.ask('set_governor',{city:'chengdu'}),true);assert.equal(await h.ui.ask('attack',{}),true);assert(!h.dialog.open);
 const escaped=fixture();escaped.ui.dispose();
 const markup=confirmation.create({document:escaped.doc,books,getView:()=>escaped.view,cityName:()=>'<img onerror=bad()>',i18n:escaped.i18n});
 pending=markup.ask('recruit',{city:'chengdu'});assert(!escaped.dialog.innerHTML.includes('<img'));assert(escaped.dialog.innerHTML.includes('&lt;img'));markup.dispose();assert.equal(await pending,false);assert.equal(escaped.listeners.size,0);
 // Exercise the shipped command gate, not merely the overlay helper.
 const app=fs.readFileSync(require.resolve('../game/app.js'),'utf8'),body=app.slice(app.indexOf('async function command('),app.indexOf('\nfunction openDialog('));
 let resolve,requests=0,invalidations=0;const gate=new Promise(done=>{resolve=done;});
 const ctx={busy:false,view:{revision:9,game:{turn:1}},audioOutcome:null,battleScene:null,gameEvents:null,
  confirmOrderCommand:()=>gate,localAutosave:{status:()=>({state:'saved'}),invalidate(){invalidations++;}},
  notice(){},setBusy(value){ctx.busy=value;},render(){},gameAudio:{play(){}},setTimeout:fn=>fn(),request:async()=>{requests++;return{revision:10,game:{turn:1}};}};
 vm.createContext(ctx);vm.runInContext(body,ctx);const rejected=ctx.command('recruit',{city:'chengdu'});assert.equal(requests,0);assert.equal(invalidations,0);assert.equal(ctx.busy,false);resolve(false);assert.equal(await rejected,false);assert.equal(requests,0);assert.equal(invalidations,0);
 let approve;ctx.confirmOrderCommand=()=>new Promise(done=>{approve=done;});let sent;ctx.request=async(_path,value)=>{requests++;sent=value;return{revision:10,game:{turn:1}};};
 const payload={city:'chengdu'},accepted=ctx.command('recruit',payload);payload.city='other';assert.equal(requests,0);approve(true);assert.equal(await accepted,true);assert.equal(requests,1);assert.equal(sent.payload.city,'chengdu','The executed payload must be the one reviewed before approval');
 h.ui.dispose();assert.equal(h.listeners.size,0);
 console.log('command confirmation: all paid action labels, exact book/city/operation, cancellation/Escape/stale/hidden rejection, paid-flow continuation, escaping, read-only decisions and actual app request/autosave gating passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
