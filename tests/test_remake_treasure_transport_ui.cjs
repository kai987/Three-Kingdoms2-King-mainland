/* The manual treasure form is bounded, bilingual and submits physical cargo. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict');
globalThis.GameOfficerChoices=require('../game/officer-choice.js');
const domestic=require('../game/domestic.js');
const policy={enabled:false,target_city:'front',reserve_gold:0,reserve_grain:0,reserve_reserves:0,reserve_officers:1,
 target_gold:0,target_grain:0,target_reserves:0,target_officers:0,allow_sea:false,allow_special:false,
 max_gold:0,max_grain:0,max_reserves:0,max_officers:1};
const target={target:'front',officers:[2],days:9,modes:['river'],route_mode:'river',cost_grain:3,
 max_treasure:7,target_treasure:4,can_dispatch:true,blocked_reason:null};
const state={owner:'wei',policy,inbound:{},preview:null,can_dispatch:false,blocked_reason:'disabled',
 rescue_targets:[],treasure_transport:{available:7,targets:[target]}};
const view={revision:1,game:{phase:'city',player:'wei',seed:2026,turn:1,cities:{home:{id:'home',owner:'wei'},front:{id:'front',owner:'wei'}},
 officers:{2:{troops:300}},extension:{travel:{marches:[]}}},
 catalog:{scenario_id:'mainland217-07',names:{2:'押運官'},factions:[{id:'wei',name:'魏'}],logistics:{cities:{home:state},convoys:[],reports:[]}}};
commandBookFixture.attach(view);
const nodes=new Map(),listeners=new Map(),submitted=[],i18n={locale:'zh-Hant',t:value=>value,apply(){}};
let shown,busy=false,preview=false,requestBarrier=null,renders=0;
const dialog={open:false,scrollTop:0,querySelector(selector){return selector==='[data-domestic-dialog]'?shown?{}:null:nodes.get(selector)||null;},
 querySelectorAll(){return [...nodes.values()].filter(node=>node.tag==='button');}};
const ui=domestic.create({dialog,document:{addEventListener:(kind,fn)=>listeners.set(kind,fn),removeEventListener(){}},
 i18n,getView:()=>view,cityName:id=>({home:'江夏',front:'長沙'}[id]||id),isBusy:()=>busy,isPreview:()=>preview,
 openDialog(title,body,actions){renders++;shown={title,body,actions};dialog.open=true;nodes.clear();
  for(const [,tag,id,attrs]of (body+actions).matchAll(/<(input|select|button|p)[^>]*?id="([^"]+)"([^>]*)>/g))
   nodes.set('#'+id,{tag,value:attrs.match(/value="([^"]*)"/)?.[1]||'',disabled:attrs.includes('disabled'),checked:attrs.includes('checked')});
  for(const [,id,options]of body.matchAll(/<select[^>]*id="([^"]+)"[^>]*>(.*?)<\/select>/gs)){
   const rows=[...options.matchAll(/<option value="([^"]*)"([^>]*)>/g)];nodes.get('#'+id).value=(rows.find(row=>row[2].includes('selected'))||rows[0])?.[1]||'';
  }return 1;
 },async command(kind,payload){submitted.push({kind,payload});if(requestBarrier)await requestBarrier;return true;}});
const get=id=>nodes.get('#'+id),refresh=()=>listeners.get('game-language-change')();
(async()=>{
 const original=JSON.stringify(view);
 assert(ui.open('home','logistics'));assert(shown.body.includes('運送寶'));
 assert(shown.body.includes('內河 9日'));assert(shown.body.includes('本城的寶 7/99'));
 assert.equal(get('treasure-transport-amount').value,'0');assert(get('dispatch-treasure').disabled);
 for(const [input,expected]of [['999999',7],['-2',0],['2.9',2],['NaN',0]]){
  get('treasure-transport-amount').value=input;get('treasure-transport-amount').oninput();
  assert.equal(get('treasure-transport-amount').value,String(expected));
 }
 get('treasure-transport-max').onclick();assert.equal(get('treasure-transport-amount').value,'7');
 assert(!get('dispatch-treasure').disabled);
 i18n.locale='ja';refresh();assert(shown.body.includes('宝の輸送'));assert(shown.body.includes('内河 9日'));
 assert(shown.body.includes('次の旬も受け入れ不能なら持ち帰ります'));assert.equal(get('treasure-transport-amount').value,'7');
 assert.equal(JSON.stringify(view),original,'Drafts, maxima and language changes never edit the query or move assets');
 await get('dispatch-treasure').onclick();
 assert.deepEqual(submitted.at(-1),{kind:'dispatch_transport',payload:{source:'home',target:'front',officers:[2],
  cargo:{gold:0,grain:0,reserves:0,treasure:7},route_mode:'river'}});
 assert.equal(JSON.stringify(view),original,'Confirm submits a command without locally crediting the destination');
 state.treasure_transport.available=2;refresh();get('treasure-transport-max').onclick();
 assert.equal(get('treasure-transport-amount').value,'2','A fresh source maximum wins over an older target quote');
 await get('dispatch-treasure').onclick();assert.equal(submitted.at(-1).payload.cargo.treasure,2);
 const before=submitted.length;
 target.route_mode='explore';refresh();assert(get('dispatch-treasure').disabled);await get('dispatch-treasure').onclick();
 assert.equal(submitted.length,before,'Manual treasure does not authorize exploration');
 target.route_mode='river';view.game.cities.front.owner='enemy';refresh();
 assert(get('dispatch-treasure').disabled);await get('dispatch-treasure').onclick();assert.equal(submitted.length,before);
 view.game.cities.front.owner='wei';view.game.phase='ai';refresh();
 assert(get('dispatch-treasure').disabled);await get('dispatch-treasure').onclick();assert.equal(submitted.length,before);
 view.game.phase='city';busy=true;refresh();assert(get('dispatch-treasure').disabled);busy=false;
 preview=true;refresh();assert(get('dispatch-treasure').disabled);preview=false;
 refresh();view.revision=17;get('treasure-transport-max').onclick();
 await get('dispatch-treasure').onclick();assert.equal(submitted.length,before+1,'Same-game revision changes do not invalidate a new confirmation');
 let current=submitted.length,oldConfirm=get('dispatch-treasure').onclick;
 view.game.seed=2027;view.catalog.scenario_id='different-campaign';await oldConfirm();
 assert.equal(submitted.length,current,'An old campaign confirmation cannot dispatch against a new game');
 refresh();assert(!get('dispatch-treasure'));assert(shown.body.includes('戦役が変わりました'));
 assert(ui.open('home','logistics'));get('treasure-transport-max').onclick();
 oldConfirm=get('dispatch-treasure').onclick;view.game.turn=2;await oldConfirm();
 assert.equal(submitted.length,current,'A stale turn must refresh and clear the amount before confirmation');
 refresh();assert.equal(get('treasure-transport-amount').value,'0');assert(get('dispatch-treasure').disabled);
 get('treasure-transport-max').onclick();
 let release;requestBarrier=new Promise(resolve=>{release=resolve;});
 const renderBefore=renders,request=get('dispatch-treasure').onclick();
 assert(get('dispatch-treasure').disabled);view.game.seed=2028;view.catalog.scenario_id='third-campaign';
 release();await request;requestBarrier=null;
 assert.equal(renders,renderBefore,'An asynchronous old-game response cannot reopen its dialog in a new campaign');
 refresh();assert(!get('dispatch-treasure'));
 state.treasure_transport={available:0,targets:[]};refresh();assert(!get('dispatch-treasure'));
 ui.dispose();console.log('treasure transport UI: real cargo, numeric maxima, stale stock/campaign/turn, async response, language, ownership, route and phase boundaries passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
