/* New receipts remain strict, bilingual and presentation-only. */
'use strict';
const assert=require('node:assert/strict');
const events=require('../game/events.js'),dialogue=require('../game/dialogue.js');
const clone=value=>JSON.parse(JSON.stringify(value));
const row=(kind,details,extra={})=>({id:1,kind,year:190,month:1,day:1,turn:1,person_ids:['person-a'],city_ids:['home'],factions:['shu'],audience:'player',details,...extra});
const developed=row('city_developed',{actor:'person-a',development:'land',gold:26,before:950,after:990,gain:40,governance_before:60,governance_after:62});
const unrest=row('civil_unrest',{governance:19,category:'population',gold_loss:0,grain_loss:0,population_loss:400,land_loss:0,industry_loss:0},{person_ids:[]});
const exhausted=row('battle_supply_exhausted',{battle_id:'battle-12',side:'attackers',days:3,grain:0,daily_grain:10,missing_units:2500,outcome:'retreat'},{person_ids:[],city_ids:['home','enemy'],factions:['shu','wei']});
const traded=row('grain_traded',{actor:'person-a',direction:'buy',batches:3,grain:300,gold:30,rate:10,battle_id:'battle-3',side:'attackers',destination:'battle'});
function rejectDetails(event,changes){
 for(const change of changes)assert.equal(events.validEvent({...event,details:{...event.details,...change}}),false,JSON.stringify(change));
 for(const field of Object.keys(event.details)){const details={...event.details};delete details[field];assert.equal(events.validEvent({...event,details}),false,'Missing '+field);}
}
for(const event of [developed,unrest,exhausted,traded]){
 assert(events.validEvent(event),event.kind);
 for(const change of [{audience:'world'},{city_ids:[]},{factions:[]},{city_ids:['']},{factions:['']},{person_ids:['']}])assert(!events.validEvent({...event,...change}),event.kind+JSON.stringify(change));
}
for(const change of [{development:'industry'},
 {before:999,after:999,gain:0,governance_after:61},
 {governance_before:100,governance_after:100},
 {development:'population',before:999800,after:999900,gain:100,governance_before:99,governance_after:100}])assert(events.validEvent({...developed,details:{...developed.details,...change}}));
rejectDetails(developed,[{development:'town'},{development:[]},{gold:true},{gold:9},{gold:11},{gold:28},{after:991},{after:1000,gain:50},{gain:-1},{governance_after:61},{governance_before:true},{actor:'other'},{extra:1},
 {before:999,after:999,gain:0,governance_before:100,governance_after:100},
 {development:'population',before:95000,after:95101,gain:101,governance_after:61}]);
for(const change of [{population_loss:0},{category:'resources',population_loss:0,gold_loss:100,grain_loss:200},{category:'development',population_loss:0,land_loss:40,industry_loss:20}])assert(events.validEvent({...unrest,details:{...unrest.details,...change}}));
rejectDetails(unrest,[{category:'riot'},{category:{}},{category:'__proto__'},{governance:50},{governance:true},{population_loss:401},{population_loss:-100},{gold_loss:1},{population_loss:1000000},{extra:1}]);
assert(events.validEvent({...exhausted,details:{...exhausted.details,side:'defenders',outcome:'victory'}}));
assert(events.validEvent({...exhausted,details:{...exhausted.details,daily_grain:202,missing_units:202000}}));
rejectDetails(exhausted,[{battle_id:'battle-0'},{battle_id:'<script>'},{side:'attacker'},{days:0},{days:31},{days:true},{grain:-1},{daily_grain:0},{daily_grain:203},{missing_units:0},{missing_units:10001},{daily_grain:202,missing_units:202001},{outcome:'victory'},{extra:1}]);
const cityTrade=clone(traded);for(const key of ['battle_id','side','destination'])delete cityTrade.details[key];assert(events.validEvent(cityTrade));
rejectDetails(traded,[{direction:'sell'},{side:'attackers<script>'},{destination:'city'},{battle_id:'battle-01'},{grain:299},{extra:1}]);

const base={catalog:{scenario_id:'event-test',library:[{person_id:'person-a',name:'劉備'}],cities:[{id:'home',name:'成都',position:[200,300]},{id:'enemy',name:'長安',position:[500,300]}],factions:[{id:'shu',name:'劉備'},{id:'wei',name:'曹操'}],world:{x:0,y:0,width:1352,height:1024,background:'/assets/map-navigation.png'}},game:{seed:1,player:'shu',officers:{0:{person_id:'person-a'}},extension:{leaders:{shu:0},events:{next_id:1,items:[]}}}};
class Modal{
 constructor(){this.open=false;this.innerHTML='';}
 addEventListener(){}removeEventListener(){}querySelector(){return {focus(){}};}
 showModal(){this.open=true;}close(){this.open=false;}
}
const originalUI={icon:id=>`<img data-existing-icon="${id}">`,scene:id=>`<img data-existing-scene="${id}">`};
const snapshots=JSON.stringify([developed,unrest,exhausted,traded,base]),random=Math.random;
Math.random=()=>{throw Error('Event presentation must not draw RNG');};
try{
 for(const language of ['zh-Hant','ja']){
  const i18n={locale:language,t:value=>value},describer=events.create({i18n});describer.observe(base,{baseline:true});
  for(const event of [developed,unrest,exhausted,traded]){
   const text=describer.description(event),lines=dialogue.event(event,base,language,i18n);
   assert(text.length&&!text.includes('undefined'));assert.equal(lines.length,2);assert(lines.every(line=>line.text&&!line.text.includes('undefined')));
   if(language==='ja')assert(/[ぁ-ゖァ-ヶ]/u.test(text)&&lines.every(line=>/[ぁ-ゖァ-ヶ]/u.test(line.text)));
  }
  assert(describer.description(developed).includes('950 → 990'));
  assert(describer.description(unrest).includes(language==='ja'?'都市の所属は変わりません':'城池歸屬未變'));
  assert(describer.description(exhausted).includes('2.5'));
  assert(describer.description(exhausted).includes(language==='ja'?'撤退':'撤退'));
  assert(describer.description({...exhausted,details:{...exhausted.details,side:'defenders',outcome:'victory'}}).includes(language==='ja'?'攻撃側が勝利':'攻方獲勝'));
  assert(describer.description(traded).includes(language==='ja'?'都市の兵糧在庫は増えていません':'城內兵糧未增加'));
  assert(dialogue.event(traded,base,language,i18n)[0].text.includes(language==='ja'?'携行分':'隨軍糧隊'));
  describer.dispose();
  for(const [event,icon] of [[developed,'command-city'],[unrest,'command-city'],[exhausted,'command-warehouse']]){
   const modal=new Modal(),tasks=[],doc={addEventListener(){},removeEventListener(){},querySelector(){return null;}};
   let current=clone(base);
   const controller=events.create({i18n,document:doc,modal,parentDialog:{open:false},originalUI,dialogue,getView:()=>current,schedule:fn=>tasks.push(fn)});
   controller.observe(current,{baseline:true});while(tasks.length)tasks.shift()();
   current=clone(base);current.game.extension.events={next_id:2,items:[event]};controller.observe(current);while(tasks.length)tasks.shift()();
   assert(modal.open);assert(modal.innerHTML.includes(`data-existing-icon="${icon}"`));assert(modal.innerHTML.includes('data-dialogue-exchange'));
   const state=JSON.stringify(current);controller.clear();assert(controller.history());while(tasks.length)tasks.shift()();assert.equal(JSON.stringify(current),state);controller.dispose();
  }
 }
 for(const action of ['develop_land','develop_industry','develop_population'])assert.equal(dialogue.COMMANDS[action],'event');
 assert.deepEqual([...dialogue.EVENT_KINDS].sort(),Object.keys(events.KINDS).sort());
 assert.equal(JSON.stringify([developed,unrest,exhausted,traded,base]),snapshots);
}finally{Math.random=random;}
console.log('economy/supply events: strict snapshots, bilingual outcomes, existing artwork and read-only playback passed');
