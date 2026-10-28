/* Independent civil identity, effective city capacity and read-only bilingual UI. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const staff=require('../game/civil-staff.js');
globalThis.GameOfficerChoices=require('../game/officer-choice.js');
const person={id:'clerk-000001',name:'陳文',portrait:'clerk-1',specialty:'commerce',profile:{martial_strength:20,intellect:56,virtue:60,health_max:70},health:70,troops:0,experience:0,offered_month:2280,expires_month:2283};
const row={target:2,minimum:2,limit:2,count:0,staff_count:0,officer_count:0,occupancy:0,effective_count:0,need:2,candidate:person,employees:[],can_hire:true,can_reject:true,blocked_reason:'',monthly_salary:0,cooldown_until_month:2280};
const view={game:{player:'shu',phase:'city',rng:{state:2026,draws:0},officers:{},cities:{home:{id:'home',owner:'shu',roster:{officer_ids:[]}},away:{id:'away',owner:'shu',roster:{officer_ids:[1,2]}}}},catalog:{rules:{city_officer_capacity:99},civil_staff:{current_month:2280,rules:{hire_gold:60,monthly_salary:5},cities:{home:row},people:[],faction_counts:{shu:0}}}};
commandBookFixture.attach(view);
const original=JSON.stringify(view);
assert.equal(staff.month(2280),'190年1月');assert.equal(staff.month(2291,'ja'),'190年12月');assert.equal(staff.month(2292),'191年1月');assert.equal(staff.month(-1),'—');
assert.equal(staff.count(view,'home'),0);assert.equal(staff.occupancy(view,'home'),0);assert.equal(staff.occupancy(view,view.game.cities.away),2);
assert(staff.attributes({...person,experience:49999}).includes('經999'));assert(staff.attributes({...person,experience:50},'ja').includes('経1'));
for(const locale of ['zh-Hant','ja']){
 assert(staff.attributes({...person,loyalty:100,is_ruler:true},locale).includes('忠--'));
 assert(staff.attributes({...person,loyalty:100},locale).includes('忠100'));
 assert(staff.attributes({...person,loyalty:100,is_ruler:true},locale,false).includes('忠100'),'Current role overrides a stale record flag');
}
assert(staff.portrait(person).includes('/assets/civil-staff/enhanced/clerk-1.png'));assert(staff.portrait(person,'ja').includes('架空の文吏'));
for(const portrait of ['clerk-4','../clerk-1','clerk-1?x=1','https://evil.example/p.png','" onerror="alert(1)'])assert(!staff.portrait({...person,portrait}).includes('<img'));
assert(staff.summary(view,'home',{bilingual:true}).includes('data-locale-only="ja"'));assert(staff.summary(view,'home').includes('合計 0/99人'));
assert.equal(JSON.stringify(view),original,'Every pure presentation helper is read-only');

const elements=new Map(),listeners=new Map();let currentDialog,callCount=0,nextResult=false,busy=false,preview=false;
const dialog={open:false,scrollTop:27,querySelector(selector){if(selector==='[data-civil-staff-dialog]')return currentDialog?.body.includes('data-civil-staff-dialog')?{}:null;return elements.get(selector)||null;}};
const i18n={locale:'zh-Hant',t:value=>value,apply(){}};
const doc={addEventListener:(type,handler)=>listeners.set(type,handler),removeEventListener:(type,handler)=>{if(listeners.get(type)===handler)listeners.delete(type);}};
let submitted;
const equipmentCalls=[];
globalThis.GameEquipment={summary(current,id,options){equipmentCalls.push({current,id,options});return `<div data-staff-equipment="${id}">引擎裝備摘要</div>`;}};
const ui=staff.create({document:doc,dialog,i18n,getView:()=>view,cityName:id=>id==='home'?'成都':'江州',isBusy:()=>busy,isPreview:()=>preview,openDialog(title,body,actions){
 currentDialog={title,body,actions};dialog.open=true;elements.clear();
 const html=body+actions;
 for(const [,id,attrs]of html.matchAll(/<(?:button|input|select)[^>]*?id="([^"]+)"([^>]*)>/g))elements.set('#'+id,{disabled:attrs.includes('disabled'),value:attrs.match(/value="([^"]*)"/)?.[1]||'',focus(){},setSelectionRange(){}});
 for(const [,id,options]of html.matchAll(/<select[^>]*id="([^"]+)"[^>]*>(.*?)<\/select>/gs)){
  const choices=[...options.matchAll(/<option value="([^"]*)"([^>]*)>/g)];elements.get('#'+id).value=(choices.find(row=>row[2].includes('selected'))||choices[0])?.[1]||'';
 }
 return ++callCount;
},async command(kind,payload){submitted={kind,payload};return typeof nextResult==='function'?nextResult(kind,payload):nextResult;}});

(async()=>{
 assert(ui.open('home'));assert.equal(currentDialog.title,'地方文吏 · 成都');assert(!elements.get('#hire-civil-staff').disabled,'A zero-officer city may hire without an actor');
 assert.equal(equipmentCalls.length,0,'An un-hired candidate has no actual held equipment to render');
 assert(currentDialog.body.includes('武20 · 知56 · 德60'));assert(currentDialog.body.includes('190年4月'));assert(currentDialog.body.includes('讀檔不重抽'));
 assert(currentDialog.body.includes('雇用費資金60；每人每月薪俸資金5。'),'Hiring and ongoing salary use explicit canonical resource labels');assert(!currentDialog.body.includes('金薪俸'));
 await elements.get('#hire-civil-staff').onclick();assert.deepEqual(submitted,{kind:'hire_staff',payload:{city:'home',candidate:'clerk-000001'}});assert(dialog.open);assert(currentDialog.body.includes('role="alert"'),'A rejected command stays in its dialog with feedback');
 assert.equal(JSON.stringify(view),original,'Viewing and an unsuccessful transaction never mutate the save or combat RNG');
 const beforeRequests=JSON.stringify(submitted);busy=true;await elements.get('#hire-civil-staff').onclick();busy=false;assert.equal(JSON.stringify(submitted),beforeRequests);
 preview=true;listeners.get('game-language-change')();assert(elements.get('#hire-civil-staff').disabled);const priorSubmission=JSON.stringify(submitted);await elements.get('#hire-civil-staff').onclick();assert.equal(JSON.stringify(submitted),priorSubmission,'A scenario preview never hires in the existing campaign');preview=false;
 row.can_hire=false;row.blocked_reason='city_full';listeners.get('game-language-change')();assert(elements.get('#hire-civil-staff').disabled);const callsBefore=callCount;await elements.get('#hire-civil-staff').onclick();assert.equal(callCount,callsBefore,'Even an invoked disabled handler cannot submit an illegal hire');
 row.can_hire=true;row.blocked_reason='';nextResult=()=>{
  row.candidate=null;row.count=row.staff_count=row.occupancy=row.effective_count=1;
  const employee={...person,city:'home',owner:'shu',hired_month:2280,paid_month:2280,unpaid_months:0,working:true};
  row.employees=[employee];row.monthly_salary=5;view.catalog.civil_staff.people=[employee];view.catalog.civil_staff.faction_counts.shu=1;
  row.searchable_staff=[employee,{...employee,id:'clerk-000002',name:'王質',profile:{...employee.profile,intellect:65}}];row.search_targets=[{id:7,name:'歷史候選',martial_strength:52,intellect:60,virtue:85,troops:0,experience:100}];row.can_search=true;row.search_blocked_reason='';return true;
 };
 listeners.get('game-language-change')();await elements.get('#hire-civil-staff').onclick();assert(!currentDialog.actions.includes('id="hire-civil-staff"'));assert(currentDialog.body.includes('履職中'));assert(currentDialog.body.includes('經2'));
 assert(currentDialog.body.includes('data-staff-equipment="clerk-000001"'));assert.equal(equipmentCalls.at(-1).current,view);assert.deepEqual(equipmentCalls.at(-1).options,{locale:'zh-Hant',bilingual:false,compact:true});
 const nextCandidate={...person,id:'clerk-000003'};row.candidate=nextCandidate;equipmentCalls.length=0;const beforeCard=JSON.stringify(view);ui.open('home');assert.deepEqual(equipmentCalls.map(call=>call.id),['clerk-000001'],'Only hired employees receive the shared equipment card, even alongside a new candidate');assert.equal(JSON.stringify(view),beforeCard,'Equipment card inspection never changes employee/candidate state or RNG');row.candidate=null;
 assert.equal(elements.get('#staff-search-actor').value,'clerk-000002','Purpose sorting prefers intellect when civil virtue ties');
 elements.get('#staff-search-actor').value='clerk-000001';elements.get('#staff-search-actor').onchange();
 i18n.locale='ja';listeners.get('game-language-change')();assert(currentDialog.body.includes('雇用費は資金60、一人の月額俸給は資金5。'));assert.equal(elements.get('#staff-search-actor').value,'clerk-000001');assert(currentDialog.title.includes('成都'));assert(currentDialog.body.includes('架空の文吏'));assert(currentDialog.body.includes('原作')===false);assert(currentDialog.body.includes('既存の成功判定'));assert.equal(dialog.scrollTop,27);
 for(const [reason,tc,ja]of [['no_available_staff','本城沒有可行動且正常履職的文吏。','この都市に行動可能で勤務中の文吏がいません。'],['no_historical_candidate','本城與可訪問的鄰城目前沒有可登用的歷史武將。','現在、この都市と訪問可能な隣接都市には登用できる歴史武将がいません。']]){
  row.can_search=false;row.search_blocked_reason=reason;
  i18n.locale='zh-Hant';listeners.get('game-language-change')();assert(currentDialog.body.includes(tc));assert(elements.get('#staff-search-confirm').disabled);
  i18n.locale='ja';listeners.get('game-language-change')();assert(currentDialog.body.includes(ja));assert(elements.get('#staff-search-confirm').disabled);
 }
 row.can_search=true;row.search_blocked_reason='';listeners.get('game-language-change')();
 nextResult=true;await elements.get('#staff-search-confirm').onclick();assert.deepEqual(submitted,{kind:'staff_recruit',payload:{city:'home',actor:'clerk-000001',officer:7}},'The civil actor stays a string; only the historical target uses its original number');
 view.catalog.library=[{id:1},{id:2},{id:3}];
 equipmentCalls.length=0;const beforeRegistry=JSON.stringify(view);ui.openRegistry();assert(currentDialog.body.includes('歴史人物3人とは別'));assert(currentDialog.body.includes('data-staff-equipment="clerk-000001"'));assert.deepEqual(equipmentCalls.map(call=>call.id),['clerk-000001']);assert.equal(equipmentCalls[0].options.locale,'ja');assert.equal(JSON.stringify(view),beforeRegistry);const input=elements.get('#staff-search');input.value='陳';input.selectionStart=1;input.oninput();i18n.locale='zh-Hant';listeners.get('game-language-change')();assert.equal(elements.get('#staff-search').value,'陳');assert(currentDialog.body.includes('陳文'));assert(currentDialog.body.includes('與3名歷史人物分開登記'));
 // A generated successor is masked by the live ruler map, in cards, registry
 // and searchable officer labels; being100 loyal alone is not enough.
 const employee=row.employees[0];employee.loyalty=100;employee.is_ruler=true;
 view.game.extension={leaders:{shu:employee.id,ended:null}};
 for(const locale of ['zh-Hant','ja']){
  i18n.locale=locale;ui.open('home');assert(currentDialog.body.includes(staff.attributes(employee,locale,true)));
  ui.openRegistry();assert(currentDialog.body.includes(staff.attributes(employee,locale,true)));
  const stored=JSON.stringify(view);listeners.get('game-language-change')();assert.equal(JSON.stringify(view),stored,'Ruler display never mutates generated officer membership, loyalty or RNG');
 }
 view.game.extension.leaders.shu='clerk-000002';ui.openRegistry();assert(!currentDialog.body.includes('忠--'));assert(currentDialog.body.includes('忠100'),'Former generated rulers display their actual loyalty despite a stale is_ruler field');
 const equipmentWidget=globalThis.GameEquipment;delete globalThis.GameEquipment;ui.open('home');assert(!currentDialog.body.includes('data-staff-equipment='),'Older isolated fixtures without the optional equipment renderer keep working');globalThis.GameEquipment=equipmentWidget;
 delete view.game.extension;delete employee.loyalty;delete employee.is_ruler;
 dialog.open=false;const closedCount=callCount;i18n.locale='ja';listeners.get('game-language-change')();assert.equal(callCount,closedCount,'Locale changes never reopen a closed panel');
 ui.dispose();assert(!listeners.has('game-language-change'));assert.equal(ui.open('home'),false);

 // The actual roster and transfer controls count civil employees against 99,
 // while historical IDs and the ten-person combat deployment remain separate.
 const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8'),context={view,capacity:()=>99};vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('function cityOccupancy('),source.indexOf('function officerChoiceText(')),context);
 row.officer_count=98;row.staff_count=1;row.occupancy=99;assert.equal(context.cityOccupancy(view.game.cities.home),99);
 assert(source.includes('full=cityOccupancy(city)>=capacity()'));assert(source.includes('slots=Math.max(0,capacity()-cityOccupancy(view.game.cities[destination]))'));
 assert(source.includes('id="civil-staff"'));assert(source.includes('id="library-staff"'));assert(source.includes('data-faction-staff'));
 console.log('civil staff UI: separate identities, zero-officer hiring, immutable inspection, salary/attributes, safe portraits, capacity, bilingual drafts, refusal handling and historical recruitment passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
