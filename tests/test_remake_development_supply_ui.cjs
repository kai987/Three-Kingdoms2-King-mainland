'use strict';
const assert=require('node:assert/strict');
globalThis.GameMarchSupply=require('../game/march-supply.js');
const supply=require('../game/battle-supply.js'),development=require('../game/city-development.js');
const view={catalog:{battle_supply_rules:{denominator:1000,officer_units:100,budget_days:30,limit:100000000}},game:{officers:{1:{troops:999},2:{troops:300}},cities:{home:{owner:'shu',grain:1000},stop:{owner:'shu'}}}};
const route={days:30,path:['home','stop','enemy'],routes:[{days:10},{days:20}]};
const before=JSON.stringify(view),q=supply.departure(view,view.game.cities.home,[1],route);
assert.equal(q.march_grain,11);assert.equal(q.battle_grain,33);assert.equal(q.total_grain,44);assert.equal(q.days_supported,30);
assert.equal(supply.departure(view,view.game.cities.home,[1],route,1e12).battle_grain,989);
assert.equal(supply.departure(view,view.game.cities.home,[1],route,-1).battle_grain,0);
assert.equal(supply.departure(view,{...view.game.cities.home,grain:12},[1],route).battle_grain,1);
assert.equal(JSON.stringify(view),before,'Draft estimates preserve campaign data');
assert.equal(development.summary(view,'home'),'');
view.catalog.city_development={cities:{home:{land:150,industry:150,population:50000,governance:70,eligible_actors:[1],actor_quotes:{1:{develop_land:{gold_min:18,gold_max:26,gain_min:17,gain_max:42,governance_gain_min:1,governance_gain_max:2,eligible:true}}}}}};
assert(development.summary(view,'home').includes('150'));assert(development.summary(view,'home').includes('data-l10n-native="ja"'));
assert(development.summary(view,'home','ja').includes('統治度'));
assert.equal(development.quote(view,'home',2,'develop_land'),null,'Never invent a quote for a missing actor');
const listeners=new Map(),elements=new Map();let busy=false,preview=false,submitted=0,resolve;
view.revision=1;view.catalog.scenario_id='test';view.catalog.names={1:'<bad>'};Object.assign(view.game,{player:'shu',seed:7,turn:1,phase:'city'});view.game.cities.home.gold=100;
globalThis.document={addEventListener:(k,f)=>listeners.set(k,f),removeEventListener:k=>listeners.delete(k)};
globalThis.GameFacilities=require('../game/facilities.js');globalThis.GameCommandBooks={can:()=>true,html:()=>'<p>1</p>'};
const dialog={open:false,html:'',querySelector(selector){if(selector==='[data-development-dialog]')return this.html.includes('data-development-dialog')?{}:null;return elements.get(selector)||null;}};
const i18n={locale:'zh-Hant',t:v=>v,apply(){}};
const ui=development.create({getView:()=>view,cityName:()=> '成都',dialog,i18n,isBusy:()=>busy,isPreview:()=>preview,
 openDialog(title,body,footer){dialog.open=true;dialog.html=body+footer;elements.clear();for(const match of dialog.html.matchAll(/id="([^"]+)"/g))elements.set('#'+match[1],{disabled:false});},
 command:async()=>{submitted++;return new Promise(done=>{resolve=done;});}});
(async()=>{
 ui.open('home');assert(dialog.html.includes('&lt;bad&gt;'));assert(!dialog.html.includes('<bad>'));
 const handler=elements.get('#development-confirm').onclick;
 for(const state of ['busy','preview','phase','owner','funds','actor']){
  busy=state==='busy';preview=state==='preview';view.game.phase=state==='phase'?'ai':'city';view.game.cities.home.owner=state==='owner'?'wei':'shu';view.game.cities.home.gold=state==='funds'?0:100;view.catalog.city_development.cities.home.eligible_actors=state==='actor'?[]:[1];
  await handler();assert.equal(submitted,0,state+' blocks stale UI submissions');
 }
 busy=preview=false;view.game.phase='city';view.game.cities.home.owner='shu';view.game.cities.home.gold=100;view.catalog.city_development.cities.home.eligible_actors=[1];
 ui.open('home');const click=elements.get('#development-confirm').onclick,pending=click();await click();assert.equal(submitted,1,'Double clicks cannot submit twice');
 dialog.open=false;resolve(true);await pending;assert.equal(dialog.open,false,'Async completion never reopens a closed modal');
 ui.open('home');const stale=elements.get('#development-confirm').onclick;view.game.turn++;await stale();assert.equal(submitted,1,'An old turn cannot submit');
 ui.dispose();assert(!listeners.has('game-language-change'));
 console.log('development and battle supply UI: segmented quotes, clamp/max, pure reads, bilingual stats, escaped labels, actor quotes, stale and pending guards passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
