/* Event playback is presentation-only, deduplicated and modal-safe. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {create,validEvent,eventRows,campaignKey,groupRows,KINDS}=require('../game/events.js');
const row=(id,kind='recruit_success',extra={})=>({id,kind,year:190,month:1,day:1,turn:1,person_ids:['person-a'],city_ids:['home'],factions:['shu'],details:{},audience:'player',...extra});
const catalog={scenario_id:'mainland190-01',title:'190年',library:[{id:0,person_id:'person-a',name:'劉備'},{id:1,person_id:'person-b',name:'曹操'}],names:{0:'劉備',1:'曹操'},factions:[{id:'shu',name:'劉備勢力',city:'home'},{id:'wei',name:'曹操勢力',city:'enemy'}],cities:[{id:'home',name:'成都',position:[120,300]},{id:'enemy',name:'長安',position:[600,300]}],world:{x:0,y:0,width:1352,height:1024,background:'/assets/map-navigation.png'},map_presentation:{road_center_corrections:{backgrounds:{'/assets/map-navigation.png':'/assets/map-road-centers.png'}},castle_fill_pixels:[[0,0]],castle_outline_pixels:[[4,4]]},tactics:[{name:'火計'}]};
const view=(items,seed=2026)=>({revision:4,catalog,game:{seed,player:'shu',year:190,month:1,day:1,turn:1,rng:{state:2026,draws:0},officers:{0:{person_id:'person-a'}},extension:{events:{next_id:(items.at(-1)?.id||0)+1,items}}}});
class Target{
 constructor(){this.events=new Map();}
 addEventListener(name,fn){if(!this.events.has(name))this.events.set(name,new Set());this.events.get(name).add(fn);}
 removeEventListener(name,fn){this.events.get(name)?.delete(fn);}
 emit(name){for(const fn of this.events.get(name)||[])fn({type:name});}
}
class Modal extends Target{
 constructor(){super();this.open=false;this.html='';this.shows=0;this.closes=0;this.focuses=0;this.buttons=new Map();}
 set innerHTML(value){this.html=value;this.buttons.clear();for(const selector of ['[data-event-next]','[data-event-skip]'])if(value.includes(selector.slice(1,-1)))this.buttons.set(selector,{onclick:null,focus:()=>{this.focuses++}});}
 get innerHTML(){return this.html;}
 querySelector(selector){return this.buttons.get(selector)||null;}
 showModal(){this.open=true;this.shows++;}
 close(){this.open=false;this.closes++;this.emit('close');}
}
function fixture(items=[]){
 const modal=new Modal(),parent=new Target(),doc=new Target(),tasks=[],header={textContent:'',setAttribute(k,v){this[k]=v}},i18n={locale:'zh-Hant',t:value=>value};
 doc.querySelector=selector=>selector==='#event-history'?header:null;parent.open=false;
 let current=view(items),busy=false,preview=false;
 const portraitRequests=[],portraits={entry:id=>id==='person-a'?{path:'/assets/portraits/original/001.png'}:null,html(id,name){portraitRequests.push([id,name]);return `<span data-portrait-person="${id}"><img src="/assets/portraits/original/001.png"></span>`;}};
 const events=create({document:doc,modal,parentDialog:parent,i18n,portraits,getView:()=>current,isBusy:()=>busy,isPreview:()=>preview,schedule:fn=>tasks.push(fn)});
 const drain=()=>{let guard=0;while(tasks.length){assert(guard++<20,'No polling loop while modal/busy');tasks.shift()();}};
 return{events,modal,parent,doc,i18n,header,portraitRequests,drain,setView:v=>{current=v;},setBusy:v=>{busy=v;},setPreview:v=>{preview=v;}};
}
(async()=>{
 assert.equal(Object.keys(KINDS).length,23);
 assert(validEvent(row(1)));for(const bad of [{id:0},{kind:'<script>'},{month:13},{day:31},{audience:'other'},{person_ids:[3]},{details:[]},{turn:0}])assert(!validEvent({...row(1),...bad}));
 assert.deepEqual(eventRows({game:{extension:{events:{items:{}}}}}),[]);
 assert.notEqual(campaignKey(view([])),campaignKey(view([],2027)));
 const originalRows=[row(3),row(2),row(1)];const source=JSON.stringify(originalRows);assert.deepEqual(eventRows(view(originalRows)).map(x=>x.id),[1,2,3]);assert.equal(JSON.stringify(originalRows),source);
 assert.deepEqual(groupRows([row(1,'officer_appeared'),row(2,'officer_appeared'),row(3,'officer_death'),row(4,'officer_death',{turn:2})]).map(g=>g.length),[2,1,1]);
 const f=fixture([row(1)]),before=view([row(1)]);f.events.observe(before,{baseline:true});f.drain();assert.equal(f.modal.shows,0);assert.equal(f.events.snapshot().cursor,1);
 const changed=view([row(1),row(2,'tactic',{details:{tactic:0,success:false}})]),unchanged=JSON.stringify(changed);f.events.observe(changed);f.drain();assert(f.modal.open);assert.deepEqual(f.events.snapshot().active,[2]);assert(f.modal.innerHTML.includes('未能奏效'));assert(f.modal.innerHTML.includes('火計'));assert(f.modal.innerHTML.includes('/assets/map-road-centers.png'));assert(f.modal.innerHTML.includes('data-portrait-person="person-a"'));assert(!f.modal.innerHTML.includes('？'));assert.equal(JSON.stringify(changed),unchanged);assert.equal(f.modal.focuses,1);
 f.events.observe(changed);f.drain();assert.deepEqual(f.events.snapshot().pending,[]);assert.equal(f.modal.shows,1);
 const activeSnapshot=f.events.snapshot();f.i18n.locale='ja';f.doc.emit('game-language-change');assert(f.modal.innerHTML.includes('計略の発動'));assert(f.modal.innerHTML.includes('効果はありませんでした'));assert.equal(f.header.textContent,'出来事の記録');assert.deepEqual(f.events.snapshot(),activeSnapshot);assert.equal(JSON.stringify(changed),unchanged);
 f.modal.querySelector('[data-event-next]').onclick();assert(!f.modal.open);f.drain();assert.equal(f.modal.shows,1);
 // Fresh campaign deliberately plays the opening; all same-turn appearances
 // share one scene, while unrelated AI personnel never becomes an auto-popup.
 const opening=view([row(1,'campaign_start'),row(2,'officer_appeared',{audience:'world'}),row(3,'officer_appeared',{audience:'world'}),row(4,'recruit_success',{audience:'world',factions:['wei']}),row(5,'faction_ended',{audience:'world',factions:['wei']})]);
 f.events.observe(opening,{newGame:true});f.drain();assert.deepEqual(f.events.snapshot().active,[1]);assert.deepEqual(f.events.snapshot().pending,[[2,3],[5]]);assert(f.modal.innerHTML.includes('1/3'));
 f.modal.querySelector('[data-event-next]').onclick();assert.deepEqual(f.events.snapshot().active,[2,3]);assert(f.modal.innerHTML.includes('2/3'));assert.equal(f.modal.shows,2,'Advancing an event does not close/reopen native modal');
 f.modal.querySelector('[data-event-skip]').onclick();assert(!f.modal.open);assert.deepEqual(f.events.snapshot().pending,[]);
 f.events.observe(opening);f.drain();assert(!f.modal.open,'Skipped events do not replay on the next render');
 // Rollback/load establishes a fresh baseline even when the same scenario,
 // player and seed have older event IDs. Historical playback remains explicit.
 f.setView(before);f.events.observe(before,{baseline:true});f.drain();assert(!f.modal.open);assert.equal(f.events.snapshot().cursor,1);assert(f.events.history());f.modal.emit('close');f.drain();assert(f.events.snapshot().historyMode);assert(f.modal.innerHTML.includes('出来事の記録'));f.modal.close();f.events.observe(before);f.drain();assert(!f.modal.open);
 const g=fixture();g.events.observe(view([]),{baseline:true});g.setBusy(true);g.events.observe(view([row(1)]));g.drain();assert(!g.modal.open);assert.equal(g.events.snapshot().pending.length,1);g.setBusy(false);g.parent.open=true;g.events.pump();g.drain();assert(!g.modal.open);g.parent.open=false;g.setPreview(true);g.parent.emit('close');g.drain();assert(!g.modal.open);g.setPreview(false);g.events.pump();g.drain();assert(g.modal.open);g.modal.emit('cancel');g.modal.close();g.drain();assert(!g.modal.open);assert.deepEqual(g.events.snapshot().pending,[]);
 // Retained server window may start beyond the cursor; process every new row
 // once, without requiring contiguous IDs or parsing mutable battle text logs.
 const h=fixture();h.events.observe(view([row(10)]),{baseline:true});h.events.observe(view([row(90,'march_arrived'),row(91,'march_arrived')]));h.drain();assert.deepEqual(h.events.snapshot().active,[90,91]);assert.equal(h.events.snapshot().cursor,91);h.events.observe(view([row(2)]));h.drain();assert(!h.modal.open,'Counter rollback is treated as a new baseline');assert.equal(h.events.snapshot().cursor,2);
 const safe=row(3,'duel_result',{details:{result:'<img src=x onerror=alert(1)>'},person_ids:['missing-person'],city_ids:['not-a-city']});h.events.observe(view([row(2),safe]));h.drain();assert(h.modal.innerHTML.includes('&lt;img'));assert(!h.modal.innerHTML.includes('<img src=x'));assert(!h.modal.innerHTML.includes('portrait-placeholder'));assert(h.modal.innerHTML.includes('event-map'));
 for(const kind of Object.keys(KINDS))assert.equal(typeof h.events.description(row(99,kind,{details:{tactic:0,outcome:'victory',lost:30,coordinated:true},factions:['wei','shu']})),'string');
 const ai=h.events.description(row(99,'ai_campaign',{factions:['wei','shu'],details:{coordinated:true}}));assert(ai.includes('曹操勢力'));assert(!ai.startsWith('劉備勢力'));
 const capture=h.events.description(row(99,'city_captured',{factions:['wei','shu']}));assert(capture.includes('改為曹操勢力'));assert(!capture.includes('改為劉備勢力'));
 const founded=h.events.description(row(99,'city_founded',{city_ids:['home','enemy']}));assert(founded.startsWith('成都依年代建置'));assert(founded.includes('承接長安'));
 const returned=reason=>h.events.description(row(99,'march_returned',{city_ids:['home','enemy'],details:{reason}}));
 assert(returned('army_lost').includes('帶兵全損'));assert(returned('army_lost').includes('武將返回成都原編制'));assert(!returned('army_lost').includes('返回長安'));
 assert(returned('target_changed').includes('目的城長安已易主'));assert(returned('target_changed').includes('保留在成都'));
 assert(returned('route_blocked').includes('途中城池易主'));assert(returned('route_blocked').includes('返回成都'));
 assert(returned('origin_changed').includes('出發城成都失陷'));assert(!returned('origin_changed').includes('返回成都'));
 assert(!returned('unknown_internal_reason').includes('unknown_internal_reason'));
 h.i18n.locale='ja';assert(returned('army_lost').includes('全兵力を失いました'));assert(returned('army_lost').includes('成都の元の所属部隊へ戻り'));assert(returned('target_changed').includes('目的都市長安'));assert(returned('route_blocked').includes('経由都市'));assert(returned('origin_changed').includes('出発都市成都の陥落'));
 const noNames=fixture();noNames.events.observe({...view([row(1)]),catalog:{...catalog,library:[],names:{}}},{baseline:true});const hiddenIds=noNames.events.description(row(99,'defection',{person_ids:['secret-person-id'],city_ids:['secret-city-id'],factions:['secret-faction-id']}));assert(!hiddenIds.includes('secret-'));assert(hiddenIds.includes('未具名武將'));assert(hiddenIds.includes('未具名勢力'));
 const returnScene=fixture();returnScene.events.observe(view([row(1,'march_returned',{city_ids:['home','enemy'],details:{reason:'target_changed'}})]),{newGame:true});returnScene.drain();assert(returnScene.modal.innerHTML.includes('viewBox="0 214 288 172"'),'Return illustration centers the departure city');
 h.events.dispose();h.events.observe(view([row(5)]),{newGame:true});h.drain();assert(!h.modal.open);
 // Shipped command integration observes only successful responses. No ACK
 // command, RNG draw, or form-state mutation is part of event playback.
 const app=fs.readFileSync(require('node:path').join(__dirname,'../game/app.js'),'utf8'),commandBody=app.slice(app.indexOf('async function command('),app.indexOf('\nfunction openDialog('));
 const observations=[],ctx={busy:false,view:view([]),audioOutcome:null,gameEvents:{observe:(v,o)=>observations.push([v,o])},notice(){},setBusy(v){ctx.busy=v;},render(){},setTimeout:fn=>{fn();return 1},gameAudio:{play(){}},request:async()=>view([row(1)])};vm.createContext(ctx);vm.runInContext(commandBody,ctx);assert(await ctx.command('new'));assert.equal(observations.length,1);assert.equal(observations[0][1].newGame,true);ctx.request=async()=>{throw Error('rejected')};assert.equal(await ctx.command('recruit_officer'),false);assert.equal(observations.length,1);
 assert(app.includes('gameEvents?.observe(view,{baseline:true})'));assert(app.includes('getView:()=>view,isBusy:()=>busy,isPreview:()=>!!setupPreview'));
 const html=fs.readFileSync(require('node:path').join(__dirname,'../game/index.html'),'utf8');assert(html.indexOf('/events.js')<html.indexOf('/app.js'));assert(html.includes('id="event-dialog" aria-labelledby="event-title" aria-describedby="event-description"'));
 console.log('events: 23 bilingual scenes, stable-ID portraits/map, grouped queues, successful-command-only observation, load baselines, modal/busy/preview guards, locale continuity, skip/history and immutable RNG/state passed');
})().catch(error=>{console.error(error);process.exitCode=1});
