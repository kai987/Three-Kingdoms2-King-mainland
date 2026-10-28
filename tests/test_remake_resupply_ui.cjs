/* Actual logistics forms: local rescue drafts never invent a remote delivery. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
globalThis.GameOfficerChoices=require('../game/officer-choice.js');
globalThis.GameMarchSupply=require('../game/march-supply.js');
const domestic=require('../game/domestic.js'),supply=globalThis.GameMarchSupply;
const policy={enabled:false,target_city:'front',reserve_gold:0,reserve_grain:0,reserve_reserves:0,reserve_officers:1,
 target_gold:0,target_grain:300,target_reserves:0,target_officers:0,allow_sea:false,allow_special:false,
 max_gold:0,max_grain:50,max_reserves:0,max_officers:1};
const route={days:20,path:['home','empty','depot','front'],routes:[{days:7},{days:3},{days:10}],distance_km:200};
const ration={loaded:10,received:5,consumed:15,remaining:0,elapsed_days:14,route_days:10,waiting:true,
 shortage_days:4,shortage_streak:4,lost:36,retreat_requested:false};
const column={id:7,source:'home',target:'front',owner:'wei',officers:[1],quote:route,supply:ration,arrival_turn:3};
const target={march_id:7,location_city:'depot',next_city:'front',city:'depot',target_city:'front',
 quote:{days:5,path:['home','depot'],routes:[{days:5}]},route_mode:'land',officers:[2],
 max_grain:50,needed_grain:30,cost_grain:2,can_dispatch:true,blocked_reason:null,eta_turn:2};
const blocked={...target,march_id:8,can_dispatch:false,blocked_reason:'no_route',max_grain:0,officers:[],city:null,quote:null};
const view={revision:1,game:{phase:'city',player:'wei',turn:2,officers:{1:{troops:900},2:{troops:300}},
 cities:{home:{id:'home',owner:'wei',roster:{officer_ids:[1,2]}},empty:{id:'empty',owner:'neutral'},
  depot:{id:'depot',owner:'wei'},front:{id:'front',owner:'wei'}},extension:{travel:{marches:[column,{...column,id:8}]}}},
 catalog:{names:{1:'先鋒',2:'押運官'},factions:[{id:'wei',name:'魏'}],logistics:{
  cities:{home:{owner:'wei',policy,inbound:{},preview:null,can_dispatch:false,blocked_reason:'disabled',rescue_targets:[target,blocked]}},
  convoys:[{id:3,source:'home',target:'home',original_target:'front',owner:'wei',officers:[2],
   target_march:7,status:'returning',delivery_done:true,delivered:{gold:0,grain:30,reserves:0},cargo:{gold:0,grain:0,reserves:0},
   journeys:[{quote:route,supply:ration}]}],reports:[]}}};
commandBookFixture.attach(view);
const elements=new Map(),listeners=new Map(),submitted=[],i18n={locale:'zh-Hant',t:value=>value,apply(){}};
let shown,busy=false,preview=false;
const dialog={open:false,scrollTop:0,querySelector(selector){return selector==='[data-domestic-dialog]'?shown?{}:null:elements.get(selector)||null;},
 querySelectorAll(){return [...elements.values()].filter(node=>node.tag==='button');}};
const cityName=id=>({home:'成都',empty:'無主城',depot:'江州',front:'前線'}[id]||id);
const ui=domestic.create({dialog,document:{addEventListener:(type,listener)=>listeners.set(type,listener),removeEventListener(){}},
 i18n,getView:()=>view,cityName,isBusy:()=>busy,isPreview:()=>preview,
 openDialog(title,body,actions){shown={title,body,actions};dialog.open=true;elements.clear();
  for(const [,tag,id,attrs]of (body+actions).matchAll(/<(input|select|button|p)[^>]*?id="([^"]+)"([^>]*)>/g))elements.set('#'+id,{tag,value:attrs.match(/value="([^"]*)"/)?.[1]||'',disabled:attrs.includes('disabled'),checked:attrs.includes('checked')});
  for(const [,id,options]of body.matchAll(/<select[^>]*id="([^"]+)"[^>]*>(.*?)<\/select>/gs)){
   const rows=[...options.matchAll(/<option value="([^"]*)"([^>]*)>/g)];elements.get('#'+id).value=(rows.find(row=>row[2].includes('selected'))||rows[0])?.[1]||'';
  }return 1;
 },async command(kind,payload){submitted.push({kind,payload});return true;}});
const get=id=>elements.get('#'+id),refresh=()=>listeners.get('game-language-change')();
(async()=>{
 const original=JSON.stringify(view);
 assert(ui.open('home','logistics'));assert(shown.body.includes('向在途部隊送糧'));
 assert(shown.body.includes('江州'));assert(shown.body.includes('首段口糧'));
 assert.equal(get('rescue-grain').value,'30');assert(!get('dispatch-rescue').disabled);
 assert(shown.body.includes('押運返程中'));assert(shown.body.includes('已卸貨'));assert(shown.body.includes('等待4日'));
 assert(shown.body.includes('剩餘0'));assert(shown.body.includes('斷糧減員36'));
 target.location_city=null;column.supply.route_days=12;refresh();
 assert(shown.body.includes('目前位置：江州 → 前線（2/10日）'),'On-road parties show their real leg progress rather than a blank location');
 target.location_city='depot';column.supply.route_days=10;refresh();
 get('rescue-grain').value='999999999999';get('rescue-grain').oninput();assert.equal(get('rescue-grain').value,'50');
 get('rescue-grain').value='-8';get('rescue-grain').onblur();assert.equal(get('rescue-grain').value,'0');assert(get('dispatch-rescue').disabled);
 get('rescue-max').onclick();assert.equal(get('rescue-grain').value,'50');assert(!get('dispatch-rescue').disabled);
 i18n.locale='ja';refresh();assert.equal(get('rescue-grain').value,'50');assert.equal(get('rescue-target').value,'7');
 assert(shown.body.includes('行軍部隊へ兵糧を輸送'));assert(shown.body.includes('遠隔で即時加算はしません'));
 assert(shown.body.includes('護送隊の帰還中'));assert(shown.body.includes('荷下ろし済み'));assert(shown.body.includes('待機4日'));
 assert.equal(JSON.stringify(view),original,'Draft changes, language changes and status views do not move food or troops');
 await get('dispatch-rescue').onclick();
 assert.deepEqual(submitted.at(-1),{kind:'dispatch_transport',payload:{source:'home',target:'depot',target_march:7,
  officers:[2],cargo:{gold:0,grain:50,reserves:0},route_mode:'land'}});
 assert(!('target_city'in submitted.at(-1).payload),'Rescue selection does not rewrite the saved city policy');
 // A service-provided inland route is legal for both rendezvous rescue and
 // ordinary frontline cargo. Viewing and confirming only submit the payload;
 // the local UI never applies food, troop or policy edits to the game query.
 target.route_mode='river';const riverRescueBefore=JSON.stringify(view);refresh();
 assert(!get('dispatch-rescue').disabled);assert.equal(JSON.stringify(view),riverRescueBefore);
 await get('dispatch-rescue').onclick();
 assert.deepEqual(submitted.at(-1),{kind:'dispatch_transport',payload:{source:'home',target:'depot',target_march:7,
  officers:[2],cargo:{gold:0,grain:50,reserves:0},route_mode:'river'}});
 assert.equal(JSON.stringify(view),riverRescueBefore,'An inland rescue confirmation does not mutate the read-only query');
 const logistics=view.catalog.logistics.cities.home;
 logistics.can_dispatch=true;logistics.blocked_reason=null;
 logistics.preview={target:'front',officers:[2],cargo:{gold:10,grain:35,reserves:20},route_mode:'river',
  quote:{days:6},cost_grain:3};
 const riverCargoBefore=JSON.stringify(view);refresh();assert(!get('dispatch-logistics').disabled);
 await get('dispatch-logistics').onclick();
 assert.deepEqual(submitted.at(-1),{kind:'dispatch_transport',payload:{source:'home',target:'front',
  officers:[2],cargo:{gold:10,grain:35,reserves:20},route_mode:'river'}});
 assert.equal(JSON.stringify(view),riverCargoBefore,'An inland cargo confirmation does not mutate the read-only query');
 const knownCount=submitted.length;target.route_mode='explore';logistics.preview.route_mode='explore';refresh();
 assert(get('dispatch-rescue').disabled);await get('dispatch-rescue').onclick();await get('dispatch-logistics').onclick();
 assert.equal(submitted.length,knownCount,'Recognizing inland routes must not authorize unknown-route exploration');
 target.route_mode='land';logistics.preview=null;logistics.can_dispatch=false;logistics.blocked_reason='disabled';refresh();
 const count=submitted.length;
 get('rescue-target').value='8';get('rescue-target').onchange();assert(get('dispatch-rescue').disabled);assert.equal(get('rescue-grain').value,'0');
 await get('dispatch-rescue').onclick();assert.equal(submitted.length,count);assert(shown.body.includes('既知の経路がありません'));
 get('rescue-target').value='7';get('rescue-target').onchange();assert.equal(get('rescue-grain').value,'30');
 for(const phase of ['ai','battle','result']){view.game.phase=phase;refresh();assert(get('dispatch-rescue').disabled);await get('dispatch-rescue').onclick();assert.equal(submitted.length,count);}
 view.game.phase='city';preview=true;refresh();assert(get('dispatch-rescue').disabled);await get('dispatch-rescue').onclick();assert.equal(submitted.length,count);preview=false;
 view.game.extension.travel.marches[0].owner='shu';refresh();await get('dispatch-rescue').onclick();assert.equal(submitted.length,count,'A stale friendly target cannot become an enemy delivery');
 view.game.extension.travel.marches[0].owner='wei';target.max_grain=12;refresh();assert.equal(get('rescue-grain').value,'12','A changed authoritative supply limit clamps the retained draft');
 target.can_dispatch=false;target.blocked_reason='command_books';refresh();assert(get('dispatch-rescue').disabled);
 target.can_dispatch=true;target.blocked_reason=null;view.catalog.logistics.cities.home.rescue_targets=[];refresh();assert(!get('dispatch-rescue'));assert(shown.body.includes('補給対象の自軍行軍部隊はいません'));
 busy=true;assert.equal(ui.open('home','logistics'),false);ui.dispose();

 // Exercise the actual app budget and status helpers, including a delayed
 // march whose nominal arrival turn has passed but has not reached its city.
 const app=fs.readFileSync(require.resolve('../game/app.js'),'utf8'),start=app.indexOf('function marchStatusHtml('),end=app.indexOf('function departureBudget(',start),
  escapeHtml=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 const context={view,GameMarchSupply:supply,cityName,escapeHtml};vm.createContext(context);vm.runInContext(app.slice(start,end),context);
 assert.equal(context.marchGrain([1],route),10,'The actual game UI loads only through the friendly depot, not the whole20-day journey');
 assert(context.marchPositionHtml(column).includes('江州'));assert(context.marchSupplyHtml(ration).includes('data-supply-shortage="4"'));
 view.game.turn=99;assert(context.marchStatusHtml(column).includes('等待補給／接收'));
 column.supply.retreat_requested=true;assert(context.marchStatusHtml(column).includes('撤退返程中'));
 assert(context.marchSupplyHtml(column.supply).includes('撤退が発動'));
 console.log('resupply UI: actual first-stage budget, authoritative rescue choices, numeric clamps, bilingual drafts, rendezvous payload, escort return, shortage status and stale/phase guards passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
