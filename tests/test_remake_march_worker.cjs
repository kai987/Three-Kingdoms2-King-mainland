/* The browser adapter must remain read-only and reject stale Worker results. */
'use strict';
const assert=require('node:assert/strict');
const{createMarchCore,stateKey}=require('../game/march-core.js');
const{createJsonClient}=require('../game/march-worker.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
class Worker{
 constructor(){this.sent=[];this.terminated=false;}
 postMessage(value){this.sent.push(value);}
 reply(index,value,ok=true){this.onmessage({data:{id:this.sent[index].id,ok,...(ok?{value}:{error:value})}});}
 terminate(){this.terminated=true;}
}
const makeView=revision=>({revision,catalog:{scenario_id:'same-catalog',travel_rules:{},travel_quotes:{server:{days:9}}},game:{year:217,month:7,player:'shu',cities:{a:{id:'a',owner:'shu'},b:{id:'b',owner:'wei'}},extension:{travel:{discovered:['seen-route']}},rng:{state:123,calls:7}}});
(async()=>{
 const memory=new WebAssembly.Memory({initial:1}),freed=[],encoder=new TextEncoder(),decoder=new TextDecoder();let resultLength=0,malformed=false;
 const json=createJsonClient({exports:{memory,march_version:()=>1,march_alloc:()=>16,march_call:(pointer,length)=>{
  const input=JSON.parse(decoder.decode(new Uint8Array(memory.buffer,pointer,length)));
  memory.grow(1);const output=encoder.encode(JSON.stringify(malformed?{ok:false,error:'Invalid month'}:{ok:true,value:input}));
  resultLength=output.length;new Uint8Array(memory.buffer,2048,resultLength).set(output);return 2048;
 },march_result_len:()=>resultLength,march_free:(pointer,length)=>freed.push([pointer,length])}});
 assert.deepEqual(json({label:'西南季風',troops:[17,29]}),{label:'西南季風',troops:[17,29]});assert.equal(freed.length,2);assert.equal(freed[0][0],2048);assert.equal(freed[1][0],16);
 malformed=true;assert.throws(()=>json({month:13}),/Invalid month/);assert.equal(freed.length,4);
 assert.throws(()=>createJsonClient({exports:{}}),/export missing/);
 const worker=new Worker(),urls=[];
 const adapter=createMarchCore({workerFactory:()=>worker,fetcher:async url=>{urls.push(url);return{ok:true,json:async()=>({travel_rules:{},links:[['a','b']]})};}});
 const v1=makeView(1),v2=makeView(2),before=JSON.stringify(v1);v2.game.month=8;let notified=0;
 const unsubscribe=adapter.subscribe(()=>notified++);
 const old=adapter.update(v1);await tick();assert.equal(worker.sent[0].request.op,'register');worker.reply(0,7);await tick();
 assert.deepEqual(worker.sent[1].request,{op:'batch',context:7,cities:[{id:'a',owner:'shu'},{id:'b',owner:'wei'}],year:217,month:7,discovered:['seen-route'],player:'shu'});
 const newer=adapter.update(v2);await tick();assert.equal(worker.sent[2].request.context,7);
 worker.reply(2,{'a:b:fastest':{days:2}});await newer;
 assert.equal(adapter.quotesFor(v2)['a:b:fastest'].days,2);assert.equal(adapter.quotesFor(v1),null);
 worker.reply(1,{'a:b:fastest':{days:999}});await old;
 assert.equal(adapter.quotesFor(v2)['a:b:fastest'].days,2);assert.equal(notified,1);assert.equal(urls.length,1);
 await adapter.update(v2);assert.equal(worker.sent.length,3);
 const rerender=JSON.parse(JSON.stringify(v2));rerender.revision=999;rerender.game.day=21;rerender.game.phase='battle';rerender.game.turn=80;rerender.game.year=217;rerender.game.officers={1:{troops:999,health:60}};Object.assign(rerender.game.cities.a,{gold:1000,grain:5000,reserves:2000,action_used:true});
 await adapter.update(rerender);assert.equal(worker.sent.length,3,'Roster, resources, date/phase and command revision reuse the existing quote batch');assert.equal(adapter.quotesFor(rerender),adapter.quotesFor(v2));
 assert.equal(stateKey(rerender),stateKey(v2));
 const troops=[20,40],quote={routes:[{hazard:{kind:'monsoon_storm'}}]};
 const preview=adapter.survivalPreview(v2,quote,troops);await tick();assert.deepEqual(worker.sent[3].request,{op:'survival_preview',quote,troops:[20,40]});
 worker.reply(3,{minimum:[2,4],maximum:[4,8]});assert.deepEqual(await preview,{minimum:[2,4],maximum:[4,8]});assert.deepEqual(troops,[20,40]);assert.equal(JSON.stringify(v1),before);
 const stale=adapter.survivalPreview(v2,quote,troops);await tick();await adapter.update({catalog:{},game:null});worker.reply(4,{minimum:[2,4],maximum:[4,8]});assert.equal(await stale,null);
 assert.equal(adapter.quotesFor(v2),null);assert.equal(adapter.status.engine,'idle');
 const empty=adapter.update(makeView(3));await tick();worker.reply(5,{});await empty;assert.deepEqual(adapter.quotesFor(makeView(3)),{});unsubscribe();
 const failure=createMarchCore({fetcher:async()=>({ok:false}),workerFactory:()=>{throw new Error('must not start');}});await failure.update(v1);assert.equal(failure.status.engine,'fallback');assert.equal(failure.quotesFor(v1),null);
 const missing=createMarchCore({fetcher:async()=>({ok:true,json:async()=>({})}),workerFactory:()=>{throw new Error('Worker unavailable');}});await missing.update(v1);assert.equal(missing.status.engine,'fallback');
 const badWorker=new Worker(),bad=createMarchCore({workerFactory:()=>badWorker,fetcher:async()=>({ok:true,json:async()=>({})})});const broken=bad.update(v1);await tick();badWorker.reply(0,'bad core',false);await broken;assert.equal(bad.status.engine,'fallback');assert(badWorker.terminated);
 const timedWorker=new Worker(),timed=createMarchCore({workerFactory:()=>timedWorker,fetcher:async()=>({ok:true,json:async()=>({})}),timeout:5});await timed.update(v1);assert.equal(timed.status.engine,'fallback');assert(timedWorker.terminated);
 class AutoWorker extends Worker{postMessage(message){super.postMessage(message);const index=this.sent.length-1;queueMicrotask(()=>this.reply(index,message.request.op==='register'?index+1:message.request.op==='unregister'?true:{}));}}
 const routeWorker=new AutoWorker(),routeUrls=[],routeAdapter=createMarchCore({workerFactory:()=>routeWorker,fetcher:async url=>{routeUrls.push(url);return{ok:true,json:async()=>({})};}});
 const routeBase=makeView(1);routeBase.game.extension.travel.discovered=['seen-route','another-route'];await routeAdapter.update(routeBase);
 const orderOnly=JSON.parse(JSON.stringify(routeBase));orderOnly.revision=2;orderOnly.game.cities={b:orderOnly.game.cities.b,a:orderOnly.game.cities.a};orderOnly.game.extension.travel.discovered.reverse();const orderBefore=JSON.stringify(orderOnly);
 await routeAdapter.update(orderOnly);assert.equal(routeWorker.sent.filter(row=>row.request.op==='batch').length,1,'Equivalent city/discovery ordering does not repeat a batch');assert.equal(JSON.stringify(orderOnly),orderBefore,'Canonical cache keys never reorder the supplied game state');
 const changes=[
  ['year',view=>{view.game.year=218;}],['month',view=>{view.game.month=8;}],['ownership',view=>{view.game.cities.b.owner='neutral';}],
  ['city opening',view=>{view.game.cities.c={id:'c',owner:'shu'};}],['city removal',view=>{delete view.game.cities.b;}],
  ['discovered route',view=>{view.game.extension.travel.discovered.push('new-sea-route');}],
  ['player',view=>{view.game.player='wei';}],['geometry',view=>{view.catalog.travel_rules.geometry_sha256='new-geometry';}],
  ['scenario',view=>{view.catalog.scenario_id='another-scenario';}]
 ];
 for(const [reason,change]of changes){
  const changed=JSON.parse(JSON.stringify(routeBase));change(changed);const immutable=JSON.stringify(changed),count=routeWorker.sent.filter(row=>row.request.op==='batch').length;
  await routeAdapter.update(changed);assert.equal(routeWorker.sent.filter(row=>row.request.op==='batch').length,count+1,reason+' recalculates routes');assert.deepEqual(routeAdapter.quotesFor(changed),{});assert.equal(routeAdapter.quotesFor(routeBase),null);assert.equal(JSON.stringify(changed),immutable,reason+' leaves the game and RNG unchanged');
 }
 assert.equal(routeUrls.length,3,'Months, ownership, active cities, discoveries and players reuse their immutable graph; new geometry/scenarios register new graphs');
 const cachedWorker=new AutoWorker(),cached=createMarchCore({workerFactory:()=>cachedWorker,fetcher:async()=>({ok:true,json:async()=>({})})});
 const scenarioView=id=>({...makeView(1),catalog:{...makeView(1).catalog,scenario_id:id}});
 for(let i=0;i<10;i++)await cached.update(scenarioView('scenario-'+i));await tick();
 assert.equal(cached.status.contexts,8);assert.equal(cachedWorker.sent.filter(r=>r.request.op==='unregister').length,2);
 await cached.update(scenarioView('scenario-0'));await tick();assert.equal(cachedWorker.sent.filter(r=>r.request.op==='register').length,11);assert.equal(cached.status.contexts,8);
 // Eviction of a still-fetching graph skips its obsolete registration,
 // without discarding the re-registration for the same scenario.
 let release;const pendingFetch=new Promise(resolve=>release=resolve),pendingWorker=new AutoWorker();let first=true;
 const bounded=createMarchCore({workerFactory:()=>pendingWorker,fetcher:async url=>{if(first){first=false;await pendingFetch;}return{ok:true,json:async()=>({url})};}});
 const retired=bounded.update(scenarioView('pending'));
 for(let i=0;i<9;i++)await bounded.update(scenarioView('new-'+i));
 await bounded.update(scenarioView('pending'));release();await retired;await tick();
 assert.equal(bounded.status.contexts,8);assert.equal(bounded.status.engine,'wasm');assert.deepEqual(bounded.quotesFor(scenarioView('pending')),{});
 assert.equal(pendingWorker.sent.filter(r=>r.request.op==='unregister').length,2);
 let finishRegistration;
 class HeldWorker extends AutoWorker{postMessage(message){if(!this.sent.length){Worker.prototype.postMessage.call(this,message);finishRegistration=()=>this.reply(0,345);}else super.postMessage(message);}}
 const heldWorker=new HeldWorker(),held=createMarchCore({workerFactory:()=>heldWorker,fetcher:async()=>({ok:true,json:async()=>({})})});
 const oldRegistration=held.update(scenarioView('old'));await tick();
 for(let i=0;i<9;i++)await held.update(scenarioView('held-'+i));await held.update(scenarioView('old'));
 finishRegistration();await oldRegistration;await tick();
 assert.equal(held.status.engine,'wasm');assert(heldWorker.sent.some(r=>r.request.op==='unregister'&&r.request.context===345));assert.deepEqual(held.quotesFor(scenarioView('old')),{});
 // A new route geometry for the same scenario/revision must fetch and
 // register a fresh graph; neither old quotes nor a late batch can win.
 const revisedWorker=new Worker(),revisedUrls=[];
 const revised=createMarchCore({workerFactory:()=>revisedWorker,fetcher:async url=>{revisedUrls.push(url);return{ok:true,json:async()=>({travel_rules:{geometry_sha256:revisedUrls.length===1?'before':'after'}})};}});
 const geometryView=geometry=>{const view=makeView(1);view.catalog.travel_rules.geometry_sha256=geometry;return view;};
 const firstGeometry=geometryView('before'),nextGeometry=geometryView('after'),unchanged=JSON.stringify(nextGeometry);
 const firstGraph=revised.update(firstGeometry);await tick();revisedWorker.reply(0,101);await tick();
 assert.equal(revisedWorker.sent[1].request.context,101);
 const nextGraph=revised.update(nextGeometry);await tick();
 assert.equal(revised.quotesFor(firstGeometry),null);assert.equal(revised.quotesFor(nextGeometry),null);
 assert.equal(revisedWorker.sent[2].request.op,'register');assert.equal(revisedUrls.length,2);
 revisedWorker.reply(2,102);await tick();assert.equal(revisedWorker.sent[3].request.context,102);
 revisedWorker.reply(3,{'a:b:fastest':{days:4}});await nextGraph;
 revisedWorker.reply(1,{'a:b:fastest':{days:999}});await firstGraph;
 assert.equal(revised.quotesFor(nextGeometry)['a:b:fastest'].days,4);
 assert.equal(revised.quotesFor(firstGeometry),null);assert.equal(revised.status.contexts,2);
 assert.equal(JSON.stringify(nextGeometry),unchanged,'Geometry invalidation preserves game state and RNG');
 const returnToFirst=revised.update(firstGeometry);await tick();assert.equal(revisedWorker.sent[4].request.context,101);
 revisedWorker.reply(4,{});await returnToFirst;assert.equal(revisedUrls.length,2,'An existing immutable geometry graph can still be reused');
 console.log('march Worker: road-input quote caching, read-only snapshots, month/ownership/active-city/discovery/player/geometry invalidation, bounded LRU/context disposal, pending eviction, stale batches/previews, empty routes, unsupported/error/timeout fallbacks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
