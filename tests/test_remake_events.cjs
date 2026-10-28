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
function fixture(items=[],{originalUI,portraits:providedPortraits}={}){
 const modal=new Modal(),parent=new Target(),doc=new Target(),tasks=[],header={textContent:'',setAttribute(k,v){this[k]=v}},i18n={locale:'zh-Hant',t:value=>value};
 doc.querySelector=selector=>selector==='#event-history'?header:null;parent.open=false;
 let current=view(items),busy=false,preview=false;
 const portraitRequests=[],portraits={entry:id=>id==='person-a'?{path:'/assets/portraits/original/001.png'}:null,html(id,name){portraitRequests.push([id,name]);return `<span data-portrait-person="${id}"><img src="/assets/portraits/original/001.png"></span>`;}};
 const events=create({document:doc,modal,parentDialog:parent,i18n,portraits:providedPortraits||portraits,originalUI,getView:()=>current,isBusy:()=>busy,isPreview:()=>preview,schedule:fn=>tasks.push(fn)});
 const drain=()=>{let guard=0;while(tasks.length){assert(guard++<20,'No polling loop while modal/busy');tasks.shift()();}};
 return{events,modal,parent,doc,i18n,header,portraitRequests,drain,setView:v=>{current=v;},setBusy:v=>{busy=v;},setPreview:v=>{preview=v;}};
}
(async()=>{
 assert.equal(Object.keys(KINDS).length,56);
 const founding=(id,kind='faction_founded',extra={})=>row(id,kind,{year:184,month:11,day:1,turn:28,audience:'world',
  person_ids:['historical-beigong-boyu','historical-li-wenhou'],city_ids:['jincheng'],factions:['beigong_boyu'],
  details:{founding_id:'liangzhou-revolt-184-11',reason:kind==='faction_founded'?'formed':'leader_unavailable',reserves:kind==='faction_founded'?1200:0},...extra});
 const formed=founding(1),skipped=founding(2,'faction_founding_skipped');
 assert(validEvent(formed));assert(validEvent(skipped));
 assert(validEvent({...formed,city_ids:['jincheng','tianshui']}),'A joint founding may concern two cities');
 assert(validEvent({...formed,details:{...formed.details,reserves:0}}),'An empty existing reserve still permits a zero-troop founding');
 assert(validEvent({...formed,details:{...formed.details,reserves:1998}}));
 for(const event of [formed,skipped]){
  for(const change of [{day:11},{audience:'player'},{city_ids:[]},{city_ids:['jincheng','longxi','home']},{city_ids:['jincheng','jincheng']},{city_ids:['']},
   {factions:[]},{factions:['beigong_boyu','song_jian']},{factions:['']},{person_ids:[]},
   {person_ids:['historical-beigong-boyu','historical-beigong-boyu']},{person_ids:['']},
   {person_ids:Array.from({length:100},(_,i)=>'historical-'+i)}])assert(!validEvent({...event,...change}));
  for(const change of [{founding_id:''},{founding_id:'x'.repeat(81)},{founding_id:'<script>'},{founding_id:1},
   {reason:'unknown'},{reserves:-1},{reserves:1.5},{reserves:true},{extra:1}])assert(!validEvent({...event,details:{...event.details,...change}}));
  for(const key of ['founding_id','reason','reserves']){const details={...event.details};delete details[key];assert(!validEvent({...event,details}));}
 }
 assert(!validEvent({...formed,details:{...formed.details,reserves:1999}}));
 assert(!validEvent({...formed,details:{...formed.details,reason:'city_occupied'}}));
 assert(!validEvent({...skipped,details:{...skipped.details,reason:'formed'}}));
 assert(!validEvent({...skipped,details:{...skipped.details,reserves:1}}));
 const song=founding(3,'faction_founded',{person_ids:['historical-song-jian'],city_ids:['longxi'],factions:['song_jian'],details:{founding_id:'song-jian-rise-184-11',reason:'formed',reserves:999}});
 assert(validEvent(song));assert(!validEvent({...song,details:{...song.details,reserves:1000}}));
 const occupied={...song,id:4,kind:'faction_founding_skipped',details:{...song.details,reason:'city_occupied',reserves:0}};
 const recruits=[{person_id:'historical-beigong-boyu',name:'北宮伯玉'},{person_id:'historical-li-wenhou',name:'李文侯'},{person_id:'historical-song-jian',name:'宋建'}],portraitCalls=[];
 const revoltCatalog={...catalog,scenario_id:'mainland184-02',library:[...catalog.library,...recruits],
  cities:[...catalog.cities,{id:'jincheng',name:'金城',position:[240,160]},{id:'longxi',name:'隴西',position:[320,240]}],
  // A skipped future faction is absent from the selectable/active roster.
  scheduled_factions:[{id:'beigong_boyu',name:'北宮伯玉勢力',city:'jincheng'},{id:'song_jian',name:'宋建勢力',city:'longxi'}]};
 const revoltView={...view([formed,skipped,song,occupied]),catalog:revoltCatalog},revoltBefore=JSON.stringify(revoltView),revolt=fixture([],{portraits:{
  entry:id=>recruits.some(p=>p.person_id===id)?{path:'/assets/portraits/generated/'+id+'.png'}:null,
  html(id,name){portraitCalls.push([id,name]);return `<img data-portrait-person="${id}" src="/assets/portraits/generated/${id}.png" alt="${name}">`;}
 }});
 revolt.setView(revoltView);revolt.events.observe(revoltView,{newGame:true});revolt.drain();
 assert.deepEqual(revolt.events.snapshot().active,[1]);assert.deepEqual(revolt.events.snapshot().pending,[[2],[3],[4]],'World founding results interrupt all players once, including skipped future factions');
 assert(revolt.modal.innerHTML.includes('地方勢力起兵'));assert(revolt.modal.innerHTML.includes('原有預備兵編入1200兵'));assert(revolt.modal.innerHTML.includes('每人至多999兵'));
 assert(revolt.modal.innerHTML.includes('event-map'));assert(revolt.modal.innerHTML.includes('<rect '),'Revolt illustrations reuse current pixel castle geometry');
 assert(revolt.modal.innerHTML.includes('data-portrait-person="historical-beigong-boyu"'));assert(revolt.modal.innerHTML.includes('data-portrait-person="historical-li-wenhou"'));
 assert(revolt.modal.innerHTML.includes('data-event-history="liangzhou-184"'));assert(revolt.modal.innerHTML.includes('後漢書/卷8'));assert(revolt.modal.innerHTML.includes('上旬不是史料確切起事日'));
 assert(revolt.modal.innerHTML.includes('rel="noopener noreferrer"'));const revoltSnapshot=revolt.events.snapshot();
 revolt.i18n.locale='ja';revolt.doc.emit('game-language-change');assert(revolt.modal.innerHTML.includes('地方勢力の挙兵'));assert(revolt.modal.innerHTML.includes('予備兵から1200'));assert(revolt.modal.innerHTML.includes('史実の背景'));assert(revolt.modal.innerHTML.includes('共に将軍'));
 assert.deepEqual(revolt.events.snapshot(),revoltSnapshot);assert.equal(JSON.stringify(revoltView),revoltBefore);
 revolt.modal.querySelector('[data-event-next]').onclick();assert(revolt.modal.innerHTML.includes('挙兵の不成立'));assert(revolt.modal.innerHTML.includes('北宮伯玉は金城'));assert(revolt.modal.innerHTML.includes('登用済み'));assert(!revolt.modal.innerHTML.includes('beigong_boyu'));
 revolt.modal.querySelector('[data-event-next]').onclick();assert(revolt.modal.innerHTML.includes('data-event-history="song-jian-184"'));assert(revolt.modal.innerHTML.includes('建国した正確な月は不明'));assert(revolt.modal.innerHTML.includes('別の勢力として処理'));assert(revolt.modal.innerHTML.includes('三國志/卷09'));assert(revolt.modal.innerHTML.includes('data-portrait-person="historical-song-jian"'));
 revolt.i18n.locale='zh-Hant';revolt.doc.emit('game-language-change');assert(revolt.modal.innerHTML.includes('十一月不是已證的建國月'));
 revolt.modal.querySelector('[data-event-next]').onclick();assert(revolt.modal.innerHTML.includes('宋建原定於隴西起兵'));assert(revolt.modal.innerHTML.includes('城池已易主'));assert(!revolt.modal.innerHTML.includes('song_jian'));
 revolt.modal.querySelector('[data-event-next]').onclick();revolt.events.observe(revoltView);revolt.drain();assert(!revolt.modal.open,'Acknowledged or skipped founding results do not repeat on ordinary render');
 assert.equal(JSON.stringify(revoltView),revoltBefore,'Revolt display, language changes and acknowledgement never edit troops, ownership, event receipts or RNG');
 assert(revolt.events.history());revolt.drain();assert(revolt.modal.innerHTML.includes('地方勢力起兵'));assert.equal(JSON.stringify(revoltView),revoltBefore);revolt.events.dispose();
 const coupPeople=['historical-bian-zhang','historical-beigong-boyu','historical-li-wenhou','san14-candidate-0166'],
  coup=row(5,'faction_coup',{year:186,month:12,day:1,turn:103,audience:'world',person_ids:coupPeople,city_ids:['jincheng','tianshui'],factions:['bian_zhang'],details:{coup_id:'han-sui-coup-186-12',reason:'executed',released_troops:1200}}),
  coupSkip={...coup,id:6,kind:'faction_coup_skipped',city_ids:[],details:{...coup.details,reason:'conditions_changed',released_troops:0}};
 assert(validEvent(coup));assert(validEvent(coupSkip));assert(validEvent({...coup,details:{...coup.details,released_troops:0}}));assert(validEvent({...coup,details:{...coup.details,released_troops:2997}}));
 for(const event of[coup,coupSkip]){
  for(const change of[{day:11},{audience:'player'},{person_ids:coupPeople.slice(0,3)},{person_ids:[...coupPeople,'person-a']},
   {person_ids:[...coupPeople.slice(0,3),coupPeople[0]]},{city_ids:['jincheng','jincheng']},{city_ids:['']},{city_ids:Array.from({length:100},(_,i)=>'city-'+i)},{factions:[]},{factions:['bian_zhang','shu']},{factions:['']}])assert(!validEvent({...event,...change}));
  for(const change of[{coup_id:''},{coup_id:'x'.repeat(81)},{coup_id:'<script>'},{coup_id:3},{reason:'unknown'},
   {released_troops:-1},{released_troops:true},{released_troops:1.5},{extra:1}])assert(!validEvent({...event,details:{...event.details,...change}}));
  for(const key of['coup_id','reason','released_troops']){const details={...event.details};delete details[key];assert(!validEvent({...event,details}));}
 }
 assert(!validEvent({...coup,city_ids:[]}));assert(!validEvent({...coup,details:{...coup.details,released_troops:2998}}));assert(!validEvent({...coup,details:{...coup.details,reason:'conditions_changed'}}));
 assert(!validEvent({...coupSkip,details:{...coupSkip.details,reason:'executed'}}));assert(!validEvent({...coupSkip,details:{...coupSkip.details,released_troops:1}}));
 const coupNames=['邊章','北宮伯玉','李文侯','韓遂'],coupCatalog={...revoltCatalog,
  library:[...revoltCatalog.library,...coupPeople.filter(id=>!revoltCatalog.library.some(p=>p.person_id===id)).map(id=>({person_id:id,name:coupNames[coupPeople.indexOf(id)]}))],
  cities:[...revoltCatalog.cities,{id:'tianshui',name:'天水',position:[400,220]}],
  factions:[...catalog.factions,{id:'bian_zhang',name:'韓遂勢力',captain:'韓遂',city:'jincheng'}],scheduled_factions:[{id:'bian_zhang',name:'邊章勢力',captain:'邊章',city:'jincheng'}]},
  coupView={...view([coup,coupSkip]),catalog:coupCatalog},coupBefore=JSON.stringify(coupView),coupPlayback=fixture([],{portraits:{
   entry:id=>coupPeople.includes(id)?{path:'/assets/portraits/generated/'+id+'.png'}:null,
   html(id,name){return `<span data-portrait-person="${id}">${name}</span>`;}
  }});
 coupPlayback.setView(coupView);coupPlayback.events.observe(coupView,{newGame:true});coupPlayback.drain();
 assert(coupPlayback.modal.innerHTML.includes('勢力內部奪權'));assert(coupPlayback.modal.innerHTML.includes('韓遂奪取原勢力主導權並自立'));assert(coupPlayback.modal.innerHTML.includes('釋放兵員1200'));assert(coupPlayback.modal.innerHTML.includes('data-event-history="han-sui-186"'));
 for(const id of coupPeople)assert(coupPlayback.modal.innerHTML.includes(`data-portrait-person="${id}"`));
 assert(coupPlayback.modal.innerHTML.includes('另記邊章病卒'));assert(coupPlayback.modal.innerHTML.includes('不是三書一致記載'));assert(coupPlayback.modal.innerHTML.includes('也不主張韓遂史實稱王'));assert(coupPlayback.modal.innerHTML.includes('資治通鑑/卷058'));
 const coupSnapshot=coupPlayback.events.snapshot();coupPlayback.i18n.locale='ja';coupPlayback.doc.emit('game-language-change');assert(coupPlayback.modal.innerHTML.includes('勢力内の政変'));assert(coupPlayback.modal.innerHTML.includes('韓遂が元の勢力の主導権を奪って自立'));assert(coupPlayback.modal.innerHTML.includes('配下兵1200'));assert(coupPlayback.modal.innerHTML.includes('辺章の病死'));assert.deepEqual(coupPlayback.events.snapshot(),coupSnapshot);
 coupPlayback.modal.querySelector('[data-event-next]').onclick();assert(coupPlayback.modal.innerHTML.includes('政変の不成立'));assert(coupPlayback.modal.innerHTML.includes('殺害や強制的な所属変更を行いません'));assert(!coupPlayback.modal.innerHTML.includes('conditions_changed'));
 coupPlayback.modal.querySelector('[data-event-next]').onclick();coupPlayback.events.observe(coupView);coupPlayback.drain();assert(!coupPlayback.modal.open);assert.equal(JSON.stringify(coupView),coupBefore,'A coup popup and acknowledgement never kill, transfer or release troops themselves');coupPlayback.events.dispose();
 const acquired=row(1,'equipment_acquired',{person_ids:['person-a','person-b'],details:{actor:'person-a',target:'person-a',from_person:'person-b',slot:'weapon',item:6,previous:0,method:'duel',battle_id:'battle-1',chance:30,roll:29}});
 assert(validEvent(acquired));
 for(const change of [{roll:30},{chance:101},{item:29},{previous:6},{method:'owned'},{battle_id:'battle-0'}])assert(!validEvent({...acquired,details:{...acquired.details,...change}}));
 const reserved=row(2,'equipment_acquired',{details:{actor:'person-a',target:'person-a',from_person:'person-a',slot:'weapon',item:15,previous:0,method:'owned',battle_id:null,chance:0,roll:-1}});assert(validEvent(reserved));
 assert(!validEvent({...reserved,person_ids:['person-b']}));
 assert(validEvent(row(1)));for(const bad of [{id:0},{kind:'<script>'},{month:13},{day:31},{audience:'other'},{person_ids:[3]},{details:[]},{turn:0}])assert(!validEvent({...row(1),...bad}));
 assert.deepEqual(eventRows({game:{extension:{events:{items:{}}}}}),[]);
 assert.notEqual(campaignKey(view([])),campaignKey(view([],2027)));
 const originalRows=[row(3),row(2),row(1)];const source=JSON.stringify(originalRows);assert.deepEqual(eventRows(view(originalRows)).map(x=>x.id),[1,2,3]);assert.equal(JSON.stringify(originalRows),source);
 assert.deepEqual(groupRows([row(1,'officer_appeared'),row(2,'officer_appeared'),row(3,'officer_death'),row(4,'officer_death',{turn:2})]).map(g=>g.length),[2,1,1]);
 const facilityRows=[
  row(1,'town_developed',{details:{actor:'person-a',from_town:1,to_town:2,gold:200}}),
  row(2,'officer_treated',{details:{actor:'person-a',target:'person-a',gold:50,before:40,after:80}}),
  row(3,'officer_studied',{details:{actor:'person-a',target:'person-a',gold:10,before:79,after:88,bonus:9}}),
  row(4,'grain_traded',{details:{actor:'person-a',direction:'buy',batches:3,grain:300,gold:30,rate:10}}),
  row(5,'equipment_bought',{details:{actor:'person-a',target:'person-a',slot:'weapon',item:4,previous:0,gold:250}}),
  row(6,'prevention_improved',{details:{actor:'person-a',gold:18,gain:12,repair:4,preparedness_before:60,preparedness_after:72,damage_before:4,damage_after:0}}),
  row(7,'city_disaster',{person_ids:[],details:{disaster:'drought',gold:0,grain:80,reserves:40,rate:4,preparedness_before:60,preparedness_after:54,damage_before:0,damage_after:4}})
 ];
 for(const r of facilityRows){assert(validEvent(r));assert(!validEvent({...r,details:{...r.details,extra:1}}));assert(!validEvent({...r,details:{...r.details,gold:-1}}));}
 assert(!validEvent({...facilityRows[6],details:{...facilityRows[6].details,preparedness_before:99}}));
 assert(!validEvent({...facilityRows[3],details:{...facilityRows[3].details,grain:301}}));
 assert(!validEvent({...facilityRows[2],details:{...facilityRows[2].details,before:80}}));
 const sites=fixture(),sitesView=view([...facilityRows,{...facilityRows[5],id:8,factions:['wei']}]);const sitesBytes=JSON.stringify(sitesView);
 sites.events.observe(sitesView,{newGame:true});sites.drain();assert(sites.modal.innerHTML.includes('event-facility'));assert(sites.modal.innerHTML.includes('町等級')||sites.modal.innerHTML.includes('城町'));
 for(let n=0;n<5;n++)sites.modal.querySelector('[data-event-next]').onclick();
 assert(sites.modal.innerHTML.includes('60 → 72'));sites.i18n.locale='ja';sites.doc.emit('game-language-change');assert(sites.modal.innerHTML.includes('防災整備'));
 sites.modal.querySelector('[data-event-next]').onclick();assert(sites.modal.innerHTML.includes('干ばつ'));assert(!sites.events.snapshot().pending.length);assert.equal(JSON.stringify(sitesView),sitesBytes);sites.events.dispose();
 const reward=row(1,'officer_rewarded',{person_ids:['person-a','person-b'],details:{actor:'person-a',target:'person-b',kind:'gold',amount:100,gain:5,loyalty_before:80,loyalty_after:85}});
 assert(validEvent(reward));
 for(const bad of [{amount:101},{gain:0},{gain:6},{loyalty_after:101},{loyalty_before:80.5},{kind:'evil'}])assert(!validEvent({...reward,details:{...reward.details,...bad}}));
 assert(!validEvent({...reward,person_ids:['person-b']}));
 const found=row(2,'treasure_found',{details:{actor:'person-a',amount:1,chance:60,gold:20}});
 assert(validEvent(found));assert(!validEvent({...found,details:{...found.details,chance:99}}));
 assert(validEvent(row(3,'treasure_search_failed',{details:{actor:'person-a',amount:0,chance:60,gold:20}})));
 assert(validEvent(row(4,'treasure_sold',{details:{actor:'person-a',amount:2,gold:200}})));
 assert(!validEvent(row(4,'treasure_sold',{details:{actor:'person-a',amount:2,gold:201}})));
 assert(validEvent(row(5,'governor_assigned',{person_ids:[],details:{governor:null,mode:'auto'}})));
 assert(!validEvent(row(5,'governor_assigned',{person_ids:[],details:{governor:null,mode:'manual'}})));
 const gifts=fixture();gifts.parent.open=true;
 const giftView=view([reward,{...reward,id:2,factions:['wei']},{...found,id:3}]);const giftBytes=JSON.stringify(giftView);
 gifts.events.observe(giftView,{newGame:true});gifts.drain();assert(!gifts.modal.open);
 gifts.parent.open=false;gifts.parent.emit('close');gifts.drain();assert.deepEqual(gifts.events.snapshot().active,[1]);
 assert(gifts.modal.innerHTML.includes('80 → 85'));assert(gifts.modal.innerHTML.includes('event-treasure'));assert(gifts.modal.innerHTML.includes('曹操'));
 gifts.i18n.locale='ja';gifts.doc.emit('game-language-change');assert(gifts.modal.innerHTML.includes('武将への褒美'));assert(gifts.modal.innerHTML.includes('資金100'));
 gifts.modal.querySelector('[data-event-next]').onclick();assert.deepEqual(gifts.events.snapshot().active,[3]);
 assert(gifts.modal.innerHTML.includes('宝の発見'));assert.equal(JSON.stringify(giftView),giftBytes);gifts.events.dispose();
 const salary=staffRow(2,'staff_salary',{details:{amount:5,paid:0,bonus:{gold:0,grain:0,reserves:0},counts:{staff:1,total_unpaid:1,cities:1}}});
 const transport=row(8,'transport_departed',{person_ids:['clerk-000001'],city_ids:['home','enemy'],details:{convoy_id:1,gold:100,grain:300,reserves:50,treasure:2,lost:0,reason:'outbound'}}),work=row(9,'domestic_report',{person_ids:[],details:{gold:20,grain:30,reserves:180,morale:150,cities:30,reason:'turn'}});
 // Verified art is selected by event kind for both the player's automatic
 // queue and AI history. Playback still consumes only copied event snapshots.
 const artCalls=[],originalUI={
  scene(id,{locale,className}){artCalls.push(['scene',id,locale,className]);return `<img class="${className}" data-original-scene="${id}" src="/assets/original-ui/${id}.png" alt="${locale==='ja'?'原版の挿絵':'原版插圖'}">`;},
  icon(id,{locale,className}){artCalls.push(['icon',id,locale,className]);return `<img class="${className}" data-original-icon="${id}" src="/assets/original-ui/${id}.png" alt="${locale==='ja'?'原版の入口アイコン':'原版入口圖示'}">`;}
 };
 const sale=row(10,'treasure_sold',{details:{actor:'person-a',amount:2,gold:200}}),artExamples=[
  [facilityRows[4],'scene','armory'],[facilityRows[3],'scene','market'],[sale,'scene','market'],
  [transport,'scene','sortie'],[facilityRows[1],'icon','facility-hospital'],[facilityRows[2],'icon','facility-school']
 ];
 for(const [event,type,id]of artExamples){
  const state=view([event]),bytes=JSON.stringify(state),visual=fixture([event],{originalUI});
  visual.events.observe(state,{newGame:true});visual.drain();
  assert(visual.modal.innerHTML.includes(`data-original-${type}="${id}"`),event.kind+' selects the corresponding verified art');
  assert(visual.modal.innerHTML.includes('event-art-original original-ui-frame'));
  assert(!visual.modal.innerHTML.includes('event-map'));assert(!visual.modal.innerHTML.includes('event-facility'));assert(!visual.modal.innerHTML.includes('event-treasure'));
  assert(visual.modal.innerHTML.includes('event-location'));assert(visual.modal.innerHTML.includes('成都'));
  if(event.person_ids.includes('person-a'))assert(visual.modal.innerHTML.indexOf('event-original-stage')<visual.modal.innerHTML.indexOf('event-people'),'Portraits follow the scene rather than obscuring it');
  if(event.kind==='transport_departed')assert(visual.modal.innerHTML.includes('data-event-art-use="remake-adaptation"'));
  if(type==='icon')assert(visual.modal.innerHTML.includes(event.kind==='officer_treated'?'醫館 · 武將療傷':'學問所 · 武將進修'));
  const cursor=visual.events.snapshot();visual.i18n.locale='ja';visual.doc.emit('game-language-change');
  assert(visual.modal.innerHTML.includes(type==='scene'?'原版の挿絵':'原版の入口アイコン'));assert.deepEqual(visual.events.snapshot(),cursor);
  assert(!visual.modal.innerHTML.includes('尚待核實'));assert(!visual.modal.innerHTML.includes('本作での転用'));
  visual.modal.querySelector('[data-event-next]').onclick();visual.events.observe(state);visual.drain();assert(!visual.modal.open,'Acknowledged art does not repeat');
  assert(visual.events.history());visual.drain();assert(visual.modal.innerHTML.includes(`data-original-${type}="${id}"`));
  visual.modal.querySelector('[data-event-next]').onclick();assert.equal(JSON.stringify(state),bytes,'Display, locale, acknowledgement and replay preserve resources and RNG');visual.events.dispose();
 }
 assert(artCalls.every(([type,id,locale,className])=>['zh-Hant','ja'].includes(locale)&&className===(type==='scene'?'event-original-scene':'event-original-icon')));
 const aiArt={...facilityRows[4],id:9,factions:['wei']},batchedArt=view([facilityRows[3],{...facilityRows[3],id:8},aiArt]),batchedVisual=fixture([],{originalUI});
 const batchBytes=JSON.stringify(batchedArt);batchedVisual.setView(batchedArt);batchedVisual.events.observe(batchedArt,{newGame:true});batchedVisual.drain();
 assert.deepEqual(batchedVisual.events.snapshot().active,[4,8]);assert.deepEqual(batchedVisual.events.snapshot().pending,[]);assert(batchedVisual.modal.innerHTML.includes('共2項'));
 assert.equal((batchedVisual.modal.innerHTML.match(/data-original-scene=/g)||[]).length,1,'Same-kind batches retain a single scene');
 batchedVisual.modal.querySelector('[data-event-next]').onclick();assert(batchedVisual.events.history());batchedVisual.drain();batchedVisual.modal.querySelector('[data-event-next]').onclick();assert(batchedVisual.modal.innerHTML.includes('data-original-scene="armory"'),'AI history uses the same scene mapping');
 assert.equal(JSON.stringify(batchedArt),batchBytes);batchedVisual.events.dispose();
 for(const missing of [undefined,{}, {scene:()=>'',icon:()=>''}]){
  const fallback=fixture([facilityRows[4]],{originalUI:missing});fallback.events.observe(view([facilityRows[4]]),{newGame:true});fallback.drain();assert(fallback.modal.innerHTML.includes('event-map'));assert(fallback.modal.innerHTML.includes('event-facility'));fallback.events.dispose();
 }
 for(const event of [acquired,row(11,'battle_started'),facilityRows[6],found]){
  const fallback=fixture([event],{originalUI});fallback.events.observe(view([event]),{newGame:true});fallback.drain();assert(fallback.modal.innerHTML.includes('event-map'));assert(!fallback.modal.innerHTML.includes('event-art-original'),'Unverified event scenes retain their existing fallback');fallback.events.dispose();
 }
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
 const observations=[],ctx={busy:false,view:view([]),audioOutcome:null,localAutosave:null,confirmOrderCommand:async()=>true,gameEvents:{observe:(v,o)=>observations.push([v,o])},notice(){},setBusy(v){ctx.busy=v;},render(){},setTimeout:fn=>{fn();return 1},gameAudio:{play(){}},request:async()=>view([row(1)])};vm.createContext(ctx);vm.runInContext(commandBody,ctx);assert(await ctx.command('new'));assert.equal(observations.length,1);assert.equal(observations[0][1].newGame,true);ctx.request=async()=>{throw Error('rejected')};assert.equal(await ctx.command('recruit_officer'),false);assert.equal(observations.length,1);
 assert(app.includes('gameEvents?.observe(view,{baseline:true})'));assert(app.includes('getView:()=>view,isBusy:()=>busy,isPreview:()=>!!setupPreview'));
 const html=fs.readFileSync(require('node:path').join(__dirname,'../game/index.html'),'utf8');assert(html.indexOf('/events.js')<html.indexOf('/app.js'));assert(html.includes('id="event-dialog" aria-labelledby="event-title" aria-describedby="event-description"'));
 console.log('events: 56 bilingual scenes, strict coup/founding/supply/city-name snapshots, dated historical context, local batching, read-only playback, locale continuity and immutable RNG/state passed');
})().catch(error=>{console.error(error);process.exitCode=1});
