/* Event playback is presentation-only, deduplicated and modal-safe. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {create,validEvent,eventRows,campaignKey,groupRows,KINDS}=require('../game/events.js');
const row=(id,kind='recruit_success',extra={})=>({id,kind,year:190,month:1,day:1,turn:1,person_ids:['person-a'],city_ids:['home'],factions:['shu'],details:{},audience:'player',...extra});
const staffRow=(id,kind='staff_candidate',extra={})=>row(id,kind,{person_ids:[],audience:'world',details:{staff_id:'clerk-000001',name:'王安',portrait:'clerk-1',reason:'opening'},...extra});
const supplyRow=(id,kind='march_resupplied',extra={})=>row(id,kind,{details:{unit_kind:'march',unit_id:7,
 grain:kind==='march_resupplied'?20:0,lost:kind==='march_starvation'?3:0,shortage_days:10,
 reason:kind==='march_resupplied'?'city':'shortage'},...extra});
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
 assert.equal(Object.keys(KINDS).length,39);
 assert(validEvent(row(1)));for(const bad of [{id:0},{kind:'<script>'},{month:13},{day:31},{audience:'other'},{person_ids:[3]},{details:[]},{turn:0}])assert(!validEvent({...row(1),...bad}));
 assert.deepEqual(eventRows({game:{extension:{events:{items:{}}}}}),[]);
 assert.notEqual(campaignKey(view([])),campaignKey(view([],2027)));
 const originalRows=[row(3),row(2),row(1)];const source=JSON.stringify(originalRows);assert.deepEqual(eventRows(view(originalRows)).map(x=>x.id),[1,2,3]);assert.equal(JSON.stringify(originalRows),source);
 assert.deepEqual(groupRows([row(1,'officer_appeared'),row(2,'officer_appeared'),row(3,'officer_death'),row(4,'officer_death',{turn:2})]).map(g=>g.length),[2,1,1]);
 const salary=staffRow(2,'staff_salary',{details:{amount:5,paid:0,bonus:{gold:0,grain:0,reserves:0},counts:{staff:1,total_unpaid:1,cities:1}}});
 const transport=row(8,'transport_departed',{person_ids:['clerk-000001'],city_ids:['home','enemy'],details:{convoy_id:1,gold:100,grain:300,reserves:50,lost:0,reason:'outbound'}}),work=row(9,'domestic_report',{person_ids:[],details:{gold:20,grain:30,reserves:180,morale:150,cities:30,reason:'turn'}});
 assert(validEvent(transport));assert(validEvent(work));for(const bad of [{convoy_id:0},{gold:-1},{lost:1.5},{reason:'<script>'},{unknown:1}])assert(!validEvent({...transport,details:{...transport.details,...bad}}));
 const training=fixture([work]),trainingBefore=JSON.stringify(work);for(const locale of ['zh-Hant','ja']){training.i18n.locale=locale;const message=training.events.description(work);assert(message.includes(locale==='ja'?'練度の成果は150':'訓練度成果150'));assert(!message.includes('士氣'));assert(!message.includes('士気'));}assert.equal(JSON.stringify(work),trainingBefore,'Renaming historical training reports preserves their saved numerical details');
 assert(!validEvent({...work,details:{...work.details,cities:116}}));assert(!validEvent({...work,details:{...work.details,reason:'unknown'}}));
 assert.deepEqual(groupRows([transport,{...transport,id:9},work]).map(g=>g.length),[2,1]);
 for(const kind of ['march_resupplied','march_starvation','march_retreat']){
  const sample=supplyRow(20,kind);assert(validEvent(sample));
  for(const details of [{unit_kind:'battle'},{unit_kind:[]},{unit_id:0},{unit_id:true},{grain:-1},{lost:1.5},
   {shortage_days:-1},{shortage_days:true},{reason:'<script>'},{extra:1}])assert(!validEvent({...sample,details:{...sample.details,...details}}));
  assert(!validEvent({...sample,audience:'world'}));assert(!validEvent({...sample,factions:[]}));assert(!validEvent({...sample,city_ids:[]}));
  assert(!validEvent({...sample,city_ids:['home','home']}));assert(!validEvent({...sample,person_ids:['person-a','person-a']}));
  assert(!validEvent({...sample,person_ids:Array.from({length:100},(_,i)=>'person-'+i)}));
 }
 assert(!validEvent({...supplyRow(20),details:{...supplyRow(20).details,grain:0}}));
 assert(!validEvent({...supplyRow(20,'march_starvation'),details:{...supplyRow(20,'march_starvation').details,shortage_days:0}}));
 assert(!validEvent({...supplyRow(20,'march_retreat'),details:{...supplyRow(20,'march_retreat').details,lost:1}}));
 const supplies=fixture(),supplyView=view([supplyRow(20),supplyRow(21,'march_starvation'),
  supplyRow(22,'march_resupplied',{details:{...supplyRow(22).details,unit_kind:'convoy',unit_id:8,reason:'convoy'}}),
  supplyRow(23,'march_retreat'),supplyRow(24,'march_starvation',{factions:['wei']})]),supplyBefore=JSON.stringify(supplyView);
 supplies.events.observe(supplyView,{newGame:true});supplies.drain();
 assert.deepEqual(supplies.events.snapshot().active,[20,22],'Same-turn replenishments share one read-only scene');
 assert.deepEqual(supplies.events.snapshot().pending,[[21],[23]],'AI supply events do not interrupt the player');
 assert(supplies.modal.innerHTML.includes('行軍補給到達'));assert(supplies.modal.innerHTML.includes('event-map'));
 assert(supplies.modal.innerHTML.includes('data-portrait-person="person-a"'));assert(supplies.modal.innerHTML.includes('增加隨軍糧20'));
 const supplySnapshot=supplies.events.snapshot();supplies.i18n.locale='ja';supplies.doc.emit('game-language-change');
 assert(supplies.modal.innerHTML.includes('行軍部隊への補給'));assert(supplies.modal.innerHTML.includes('携行兵糧を20補充'));
 assert.deepEqual(supplies.events.snapshot(),supplySnapshot);assert.equal(JSON.stringify(supplyView),supplyBefore);
 supplies.modal.querySelector('[data-event-next]').onclick();assert(supplies.modal.innerHTML.includes('今回の兵力損失は3'));
 assert(supplies.modal.innerHTML.includes('武将の戦死はありません'));
 supplies.modal.querySelector('[data-event-next]').onclick();assert(supplies.modal.innerHTML.includes('部隊の自動撤退'));
 assert(supplies.modal.innerHTML.includes('瞬時には戻りません'));supplies.modal.querySelector('[data-event-next]').onclick();assert(!supplies.modal.open);
 assert.equal(JSON.stringify(supplyView),supplyBefore,'Acknowledging supply, hunger and retreat never changes a save or RNG');
 assert(validEvent(staffRow(1)));assert(validEvent(salary));
 for(const details of [{staff_id:'san14-candidate-0952'},{staff_id:'clerk-000000'},{staff_id:12},{portrait:'../portrait'},{name:''},{reason:'<script>'},{amount:-1},{paid:1.5}])assert(!validEvent(staffRow(1,'staff_candidate',{details:{...staffRow(1).details,...details}})));
 assert(!validEvent(staffRow(1,'staff_candidate',{person_ids:['person-a']})));assert(!validEvent(staffRow(1,'staff_candidate',{city_ids:[]})));
 assert(!validEvent({...salary,details:{...salary.details,paid:6}}));assert(!validEvent({...salary,details:{...salary.details,bonus:{gold:0,grain:0,reserves:-1}}}));
 assert(!validEvent({...salary,details:{...salary.details,paid:1}}));assert(!validEvent({...salary,details:{...salary.details,counts:{staff:1,total_unpaid:0,cities:1}}}));
 assert(validEvent({...salary,details:{amount:1725,paid:1720,bonus:{gold:230,grain:200,reserves:80},counts:{staff:345,total_unpaid:1,cities:115}}}));
 assert.deepEqual(groupRows([staffRow(1),salary,staffRow(3),staffRow(4,'staff_candidate',{turn:2})]).map(g=>g.map(e=>e.id)),[[1,3],[2],[4]],'Interleaved staff events share one same-turn scene per kind');
 const staff=fixture(),staffView=view([staffRow(1),salary,staffRow(3,'staff_candidate',{factions:['wei'],audience:'player'}),staffRow(4,'staff_candidate',{details:{...staffRow(4).details,staff_id:'clerk-000002',name:'周平',portrait:'clerk-2'}})]);
 const staffBefore=JSON.stringify(staffView);staff.events.observe(staffView,{newGame:true});staff.drain();assert.deepEqual(staff.events.snapshot().active,[1,4]);assert.deepEqual(staff.events.snapshot().pending,[[2]],'Remote AI staff events never interrupt this player, even with a broad audience');
 assert(staff.modal.innerHTML.includes('/assets/civil-staff/clerk-1.png'));assert(staff.modal.innerHTML.includes('/assets/civil-staff/clerk-2.png'));assert(staff.modal.innerHTML.includes('架空文吏'));assert(staff.modal.innerHTML.includes('王安'));assert.equal(staff.portraitRequests.length,0,'Civil staff portraits never look up a historical person ID');
 const staffSnapshot=staff.events.snapshot();staff.i18n.locale='ja';staff.doc.emit('game-language-change');assert(staff.modal.innerHTML.includes('在地文官の推薦'));assert(staff.modal.innerHTML.includes('架空文官'));assert.deepEqual(staff.events.snapshot(),staffSnapshot);assert.equal(JSON.stringify(staffView),staffBefore);
 staff.modal.querySelector('[data-event-next]').onclick();assert(staff.modal.innerHTML.includes('金5'));assert(staff.modal.innerHTML.includes('業務を休止'));assert(staff.modal.innerHTML.includes('今月の追加収入なし'));
 staff.modal.querySelector('[data-event-next]').onclick();assert(!staff.modal.open);
 const staffDesc=fixture();staffDesc.events.observe(view([]),{baseline:true});assert(staffDesc.events.description(staffRow(1,'staff_expired',{details:{...staffRow(1).details,reason:'filled'}})).includes('編制已補足'));assert(staffDesc.events.description(staffRow(1,'staff_expired',{details:{...staffRow(1).details,reason:'owner_changed'}})).includes('所屬已變更'));assert(staffDesc.events.description(staffRow(1,'staff_allegiance',{factions:['wei','shu']})).includes('劉備勢力'));
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
 const upgrade=row(100,'city_upgraded',{year:240,month:1,day:1,audience:'world',person_ids:[],city_ids:['home'],factions:['wei'],details:{from_tier:'large',to_tier:'giant',income:{gold:90,grain:180,reserves:45}}});
 assert(validEvent(upgrade));
 for(const bad of [{to_tier:'unknown'},{from_tier:'giant'},{income:{gold:-1,grain:180,reserves:45}},{unknown:1}])assert(!validEvent({...upgrade,details:{...upgrade.details,...bad}}));
 const upgraded=fixture();upgraded.events.observe(view([]),{baseline:true});upgraded.events.observe(view([upgrade]));upgraded.drain();
 assert(upgraded.modal.open,'A city upgrade is a world event, regardless of the owning faction');assert(upgraded.modal.innerHTML.includes('都市擴建'));assert(upgraded.modal.innerHTML.includes('240年1月'));assert(upgraded.modal.innerHTML.includes('巨大都市'));assert(upgraded.modal.innerHTML.includes('event-map'));
 const upgradeSnapshot=upgraded.events.snapshot();upgraded.i18n.locale='ja';upgraded.doc.emit('game-language-change');assert(upgraded.modal.innerHTML.includes('都市の発展'));assert(upgraded.modal.innerHTML.includes('本作独自'));assert.deepEqual(upgraded.events.snapshot(),upgradeSnapshot);
 const renamed=row(101,'city_renamed',{year:219,month:1,day:1,audience:'world',person_ids:[],city_ids:['qiao'],factions:['wei'],details:{from_name:'小沛',to_name:'譙郡'}});
 assert(validEvent(renamed));
 for(const bad of [{day:11},{audience:'player'},{person_ids:['person-a']},{city_ids:[]},{factions:[]}])assert(!validEvent({...renamed,...bad}));
 for(const bad of [{from_name:'譙郡'},{from_name:''},{to_name:42},{to_name:'bad\nname'},{extra:1}])assert(!validEvent({...renamed,details:{...renamed.details,...bad}}));
 const dates=fixture(),datedView=view([renamed,{...upgrade,id:102,year:221,city_ids:['qiao'],details:{...upgrade.details,from_tier:'normal',to_tier:'large'}}]);
 datedView.catalog={...catalog,cities:[...catalog.cities,{id:'qiao',name:'譙郡',position:[700,300]}]};const datedBefore=JSON.stringify(datedView);
 dates.events.observe(datedView,{newGame:true});dates.drain();
 assert(dates.modal.innerHTML.includes('城名顯示變更'));assert(dates.modal.innerHTML.includes('data-event-history="qiao-219"'));
 assert(dates.modal.innerHTML.includes('史實背景'));assert(dates.modal.innerHTML.includes('不是史實上小沛於219年改名譙郡'));assert(dates.modal.innerHTML.includes('event-map'));
 assert(dates.modal.innerHTML.includes('https://zh.wikisource.org/zh-hant/三國志/卷32'));assert(dates.modal.innerHTML.includes('rel="noopener noreferrer"'));
 const renameSnapshot=dates.events.snapshot();dates.i18n.locale='ja';dates.doc.emit('game-language-change');assert(dates.modal.innerHTML.includes('史実の背景'));assert(dates.modal.innerHTML.includes('別の都市'));assert.deepEqual(dates.events.snapshot(),renameSnapshot);
 dates.modal.querySelector('[data-event-next]').onclick();assert(dates.modal.innerHTML.includes('data-event-history="qiao-221"'));assert(dates.modal.innerHTML.includes('五都'));assert(dates.modal.innerHTML.includes('巻2'));assert(dates.modal.innerHTML.includes('ゲーム独自の設定'));
 dates.i18n.locale='zh-Hant';dates.doc.emit('game-language-change');assert(dates.modal.innerHTML.includes('黃初二年（221年）'));assert(dates.modal.innerHTML.includes('今後每月收入'));assert.equal(JSON.stringify(datedView),datedBefore,'Historical text, locale changes and acknowledgements cannot change actual troops, stores or RNG');
 dates.modal.querySelector('[data-event-next]').onclick();dates.events.observe(datedView);dates.drain();assert(!dates.modal.open,'A dated scene is not replayed after acknowledgement');
 const hostile=fixture();hostile.events.observe(view([{...renamed,details:{from_name:'<img src=x>',to_name:'譙郡'}}]),{newGame:true});hostile.drain();assert(hostile.modal.innerHTML.includes('&lt;img src=x&gt;'));assert(!hostile.modal.innerHTML.includes('<img src=x>'));
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
 const observations=[],ctx={busy:false,view:view([]),audioOutcome:null,localAutosave:null,gameEvents:{observe:(v,o)=>observations.push([v,o])},notice(){},setBusy(v){ctx.busy=v;},render(){},setTimeout:fn=>{fn();return 1},gameAudio:{play(){}},request:async()=>view([row(1)])};vm.createContext(ctx);vm.runInContext(commandBody,ctx);assert(await ctx.command('new'));assert.equal(observations.length,1);assert.equal(observations[0][1].newGame,true);ctx.request=async()=>{throw Error('rejected')};assert.equal(await ctx.command('recruit_officer'),false);assert.equal(observations.length,1);
 assert(app.includes('gameEvents?.observe(view,{baseline:true})'));assert(app.includes('getView:()=>view,isBusy:()=>busy,isPreview:()=>!!setupPreview'));
 const html=fs.readFileSync(require('node:path').join(__dirname,'../game/index.html'),'utf8');assert(html.indexOf('/events.js')<html.indexOf('/app.js'));assert(html.includes('id="event-dialog" aria-labelledby="event-title" aria-describedby="event-description"'));
 console.log('events: 39 bilingual scenes, strict supply and city-name snapshots, dated city upgrades with historical context, local batching, read-only playback, locale continuity and immutable RNG/state passed');
})().catch(error=>{console.error(error);process.exitCode=1});
