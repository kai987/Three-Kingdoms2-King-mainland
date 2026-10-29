/* City capacity follows the selected catalog; deployment remains a separate limit. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'game/app.js'),'utf8');
const elements=new Map(),element=selector=>{
 if(selector==='#transfer-estimate'||selector==='#route-mode')return null;
 if(!elements.has(selector))elements.set(selector,{innerHTML:'',value:'',disabled:false,attributes:{},classList:{add(){},remove(){}},setAttribute(key,value){this.attributes[key]=String(value);},focus(){this.focused=true;}});
 return elements.get(selector);
};
let picked=[],lastDialog=null,lastNotice=null,lastCommand=null;
const officers=Object.fromEntries(Array.from({length:99},(_,id)=>[id,{health:90,loyalty:80,experience:0,troops:300,profile:{martial_strength:80,intellect:70,virtue:60}}]));
const home={id:'home',owner:'wei',gold:100,grain:1000,reserves:999,action_used:false,roster:{officer_ids:Object.keys(officers).map(Number)}},away={id:'away',owner:'wei',roster:{officer_ids:[]}},enemy={id:'enemy',owner:'wu',roster:{officer_ids:[]}};
officers[100]={...officers[0],faction_id:null};
const context={refreshPersonnelDialogue(){},clearDialogueFeedback(){},GameOfficerChoices:require('../game/officer-choice.js'),GameOfficerSelection:require('../game/officer-selection.js'),GameI18n:{apply(){}},view:{catalog:{rules:{city_officer_capacity:99,battle_officers_per_side:10,expanded_campaign:true},city_profiles:{},city_income:{},map_presentation:{city_names:{}},links:[['home','enemy']],recruitable:{home:[100]},persuadable:{home:[]}},game:{player:'wei',turn:1,cities:{home,away,enemy},officers,extension:{officer_actions:{}}}},selectedCity:'home',actor:null,target:null,$:element,escapeHtml:String,name:id=>'武将'+id,portraitHtml:()=>'<i></i>',faction:String,cityName:String,periodCityName:String,cityEconomyNote:()=>'',resourceSummary:()=>'',marching:()=>new Set(),watchRouteDialog(){},notice(text,error){lastNotice={text,error};},command(kind,payload){lastCommand={kind,payload};return Promise.resolve(true);},render(){},dialog:{querySelectorAll:()=>picked.map(input=>Object.assign(input,{addEventListener(){}})),close(){}},openDialog(title,body){lastDialog={title,body};element('#departure-target').value='enemy';element('#transfer-city').value='away';element('#recruit-mode').value='recruit_officer';}};
context.GameCommandBooks=commandBookFixture.api;commandBookFixture.attach(context.view);
vm.createContext(context);
context.isRuler=id=>context.GameOfficerChoices.isRuler(id,context.view.game.extension?.leaders);
vm.runInContext(source.slice(source.indexOf('const capacity='),source.indexOf('\nconst marching=')),context);
vm.runInContext(source.slice(source.indexOf('function officerAttributes('),source.indexOf('// Classify actual runtime entry')),context);
async function weightedTransferChecks(){
 const nodes=new Map(),get=selector=>{
  if(!nodes.has(selector))nodes.set(selector,{innerHTML:'',textContent:'',value:'',disabled:false});
  return nodes.get(selector);
 };
 const people=Object.fromEntries([999,0,300].map((troops,id)=>[id,{alive:true,health:80,troops,
  loyalty:80,experience:0,profile:{martial_strength:90-id,intellect:70,virtue:60}}]));
 const origin={id:'home',owner:'wei',grain:10,roster:{officer_ids:[0,1,2]}},destination={id:'away',owner:'wei',roster:{officer_ids:[]}},
  full={id:'full',owner:'wei',roster:{officer_ids:[3,4,5]}},blocked={id:'blocked',owner:'wei',roster:{officer_ids:[]}};
 const quotes={};
 for(const to of ['away','full'])for(const [mode,days]of [['fastest',20],['land',20],['sea',30],['explore',20]])quotes[`home:${to}:${mode}`]={days};
 let inputs=[],submitted=null;
 const fixture={GameOfficerChoices:require('../game/officer-choice.js'),GameOfficerSelection:require('../game/officer-selection.js'),
  GameMarchSupply:require('../game/march-supply.js'),GameI18n:{apply(){}},capacity:()=>3,$:get,
  view:{catalog:{travel_rules:{},rules:{city_officer_capacity:3}},game:{player:'wei',turn:1,officers:people,
   cities:{home:origin,away:destination,full,blocked},extension:{officer_actions:{}}}},
  escapeHtml:String,name:id=>'武将'+id,cityName:String,isRuler:()=>false,marching:()=>new Set(),
  routeModeSelect:()=>'<select id="route-mode"></select>',
  syncRouteModes(from,to,preferred){const mode=quotes[`${from}:${to}:${preferred}`]?preferred:quotes[`${from}:${to}:fastest`]?'fastest':'';get('#route-mode').value=mode;return mode;},
  travelQuote:(from,to,mode)=>quotes[`${from}:${to}:${mode}`],travelEstimate:()=>'<p>Actual route estimate</p>',
  previewSurvivors(){},watchRouteDialog(){},notice(){},
  command(kind,payload){submitted={kind,payload};return Promise.resolve(true);},
  dialog:{close(){},querySelectorAll(selector){return selector.includes(':checked')?inputs.filter(input=>input.checked):inputs;}},
  openDialog(title,body){
   inputs=[...body.matchAll(/<input type="checkbox" name="transfer-officer" value="([^"]+)"([^>]*)>/g)].map(match=>({
    value:match[1],checked:/\bchecked\b/.test(match[2]),disabled:/\bdisabled\b/.test(match[2]),
    addEventListener(type,handler){this[type]=handler;}
   }));
   get('#transfer-city').value='away';get('#route-mode').value='fastest';
  }
 };
 fixture.GameCommandBooks=commandBookFixture.api;commandBookFixture.attach(fixture.view);
 vm.createContext(fixture);vm.runInContext(source.slice(source.indexOf('function officerAttributes('),source.indexOf('// Classify actual runtime entry')),fixture);
 const checked=()=>inputs.filter(input=>input.checked).map(input=>Number(input.value)),input=id=>inputs.find(input=>Number(input.value)===id),
  click=id=>{const row=input(id);assert(!row.disabled,'User can only activate affordable eligible officers');row.checked=!row.checked;row.change();},
  supply=amount=>assert(get('#transfer-supply').innerHTML.includes(`data-supply-loaded="${amount}"`));
 const before=JSON.stringify(fixture.view.game);
 fixture.transferCity(origin);
 assert(input(0).disabled,'999 troops plus the officer need 22 grain for 20 days, not the old five-grain person fee');
 assert(!input(1).disabled&&!input(2).disabled,'Zero-troop officers and smaller units use their actual lower food budget');
 assert(get('#confirm-transfer').disabled);
 click(1);supply(2);assert(!input(2).disabled);
 click(2);supply(10);assert.deepEqual(checked(),[1,2]);assert(!get('#confirm-transfer').disabled,'The exact combined loading budget can be submitted');
 get('#route-mode').value='sea';get('#route-mode').onchange();
 assert.deepEqual(checked(),[1],'A longer route trims the latest selection instead of submitting an unaffordable convoy');supply(3);
 assert(input(0).disabled&&input(2).disabled);
 get('#route-mode').value='explore';get('#route-mode').onchange();
 assert(get('#confirm-transfer').disabled,'An affordable zero-troop group still cannot explore unknown sea routes');
 click(2);supply(10);assert(!get('#confirm-transfer').disabled);
 get('#transfer-city').value='full';get('#transfer-city').onchange();
 assert.deepEqual(checked(),[]);assert(inputs.every(row=>row.disabled));assert(get('#confirm-transfer').disabled,'Destination space is independent of the grain limit');
 get('#transfer-city').value='away';get('#transfer-city').onchange();
 get('#route-mode').value='fastest';get('#route-mode').onchange();click(1);click(2);supply(10);
 get('#transfer-city').value='blocked';get('#transfer-city').onchange();
 assert.deepEqual(checked(),[]);assert(inputs.every(row=>row.disabled));assert(get('#confirm-transfer').disabled);
 assert.equal(get('#transfer-supply').innerHTML,'','A disconnected destination must clear the previous route\'s loading estimate');
 get('#transfer-city').value='away';get('#transfer-city').onchange();click(1);click(2);
 await get('#confirm-transfer').onclick();assert.equal(submitted.kind,'transfer');assert.deepEqual(Array.from(submitted.payload.officers),[1,2]);
 assert.equal(submitted.payload.route_mode,'fastest');assert.equal(JSON.stringify(fixture.view.game),before,'Weighted selection and confirmation do not change saves or grain before a command response');
}
(async()=>{
 const before=JSON.stringify(context.view.game);
 context.renderCity();
 assert(element('#inspector').innerHTML.includes('id="recruit-officer" disabled'),'A full city cannot start another recruitment');
 assert(element('#inspector').innerHTML.includes('驻城 99/99；每方出战上限10人。'));
 assert.equal((element('#inspector').innerHTML.match(/data-city-roster-officer=/g)||[]).length,99,'Every city member remains reachable in the concise roster');
 assert(element('#inspector').innerHTML.includes('id="city-information"'),'The complete roster and attributes remain reachable through city information');
 assert(!element('#inspector').innerHTML.includes('class="roster-table"'),'The narrow sidebar does not repeat the full attribute table');
 assert.equal((element('#inspector').innerHTML.match(/role="tab" /g)||[]).length,4);
 assert(element('#inspector').innerHTML.includes('id="city-command-tab-army" data-city-command-group="army" role="tab" aria-controls="city-command-panel-army" aria-selected="true" tabindex="0"'),'Army is the default active, keyboard reachable group');
 for(const key of ['city','warehouse','town'])assert(new RegExp(`id="city-command-panel-${key}"[^>]* hidden`).test(element('#inspector').innerHTML),'Inactive command panels stay present and hidden');
 const originalCatalog={...context.view.catalog},iconCalls=[],visits=[];
 Object.assign(context.view.catalog,{scenario_id:'test-campaign',facilities:{},treasury:{},domestic:{},civil_staff:{}});
 context.view.game.seed=2026;
 context.GameOriginalUI={icon(id,options){iconCalls.push([id,options.decorative]);return `<i data-command-icon="${id}" aria-hidden="true"></i>`;}};
 context.facilitiesInterface=()=>({open(...args){visits.push(args);}});
 context.renderCity();
 assert.deepEqual(iconCalls,[['command-city',true],['command-army',true],['command-warehouse',true],['command-town',true]],'Each group uses the corresponding verified original category icon');
 for(const id of ['allocate','depart','transfer','recruit','recruit-officer','civil-staff','city-domestic','city-civic','city-treasury','city-logistics','city-facilities','end-turn'])assert(element('#inspector').innerHTML.includes(`id="${id}"`),'Existing guarded action remains reachable: '+id);
 context.selectCityCommandGroup(home,'town');
 assert.equal(element('#city-command-panel-town').hidden,false);assert.equal(element('#city-command-panel-army').hidden,true);
 assert.equal(element('#city-command-tab-town').attributes['aria-selected'],'true');assert.equal(element('#city-command-tab-town').tabIndex,0);assert.equal(element('#city-command-tab-army').tabIndex,-1);
 context.renderCity();assert.equal(context.cityCommandGroup(home),'town','Selection survives a view refresh');
 assert.equal(context.cityCommandGroup(away),'army','A new city starts at Army');context.selectCityCommandGroup(away,'city');assert.equal(context.cityCommandGroup(home),'town','City selections are independent');
 let prevented=false;element('#city-command-tab-town').onkeydown({key:'Home',preventDefault(){prevented=true;}});assert(prevented);assert.equal(context.cityCommandGroup(home),'city');assert(element('#city-command-tab-city').focused,'Arrow/Home/End navigation transfers focus to the selected tab');
 element('#city-command-tab-city').onkeydown({key:'ArrowDown',preventDefault(){}});assert.equal(context.cityCommandGroup(home),'army','Down advances one position in the horizontal command row');
 element('#city-command-tab-army').onkeydown({key:'ArrowRight',preventDefault(){}});assert.equal(context.cityCommandGroup(home),'warehouse');
 element('#city-command-tab-warehouse').onkeydown({key:'ArrowUp',preventDefault(){}});assert.equal(context.cityCommandGroup(home),'army','Up moves one position back in the horizontal command row');
 element('#city-command-tab-army').onkeydown({key:'ArrowLeft',preventDefault(){}});assert.equal(context.cityCommandGroup(home),'city');
 element('#city-command-tab-city').onkeydown({key:'ArrowLeft',preventDefault(){}});assert.equal(context.cityCommandGroup(home),'town','The ends wrap within the same row');
 element('#city-command-tab-town').onkeydown({key:'End',preventDefault(){}});assert.equal(context.cityCommandGroup(home),'town');
 context.view.game.seed=2027;assert.equal(context.cityCommandGroup(home),'army','Another campaign has its own selection');context.view.game.seed=2026;assert.equal(context.cityCommandGroup(home),'town');
 element('#city-facilities').onclick();element('#city-civic').onclick();
 assert.equal(visits[0][0],'home');assert.equal(visits[0].length,1,'Town uses the normal facility entry');assert.equal(visits[1][0],'home');assert.equal(visits[1][1].section,'civic','City opens development and prevention directly');
 const navigationState=JSON.parse(JSON.stringify(context.view.game));delete navigationState.seed;
 assert.equal(JSON.stringify(navigationState),before,'Tab navigation and facility entry do not issue game commands or change runtime state');
 delete context.view.game.seed;context.view.catalog=originalCatalog;delete context.GameOriginalUI;
 context.recruitOfficer(home);assert(lastDialog.body.includes('最多99人。'));
 context.transferCity(home);assert(lastDialog.body.includes('目的城仍最多99人。'));assert(lastDialog.body.includes('0/99人'));
 // Transferring an entire roster is independent of the battle deployment limit.
 picked=Array.from({length:99},(_,value)=>({value:String(value)}));await element('#confirm-transfer').onclick();
 assert.equal(lastCommand.kind,'transfer');assert.equal(lastCommand.payload.officers.length,99);
 element('#allocation-officer').value='0';element('#allocation-troops').value='300';context.allocate(home);assert(lastDialog.body.includes('max="1000"'),'Troop input uses troop limits, not city membership capacity');
 assert.equal((lastDialog.body.match(/<option value=/g)||[]).length,99);
 context.departure(home);assert(lastDialog.body.includes('选择1—10名武将'));assert.equal((lastDialog.body.match(/name="depart-officer"/g)||[]).length,99);
 picked=Array.from({length:11},(_,value)=>({value:String(value)}));element('#review-departure').onclick();
 assert.equal(lastNotice.error,true);assert.equal(lastDialog.title,'选择出征名单','11 members may not enter a battle from a 99-member city');
 picked=picked.slice(0,10);element('#review-departure').onclick();assert.equal(lastDialog.title,'出征确认');await element('#confirm-departure').onclick();assert.equal(lastCommand.kind,'depart');assert.equal(lastCommand.payload.officers.length,10);
 assert.equal(JSON.stringify(context.view.game),before,'Rendering and uncommitted confirmation never mutate runtime state');
 // Display reads the supplied capacity, rather than freezing 99 into UI copy.
 context.view.catalog.rules.city_officer_capacity=30;home.roster.officer_ids=home.roster.officer_ids.slice(0,30);
 context.renderCity();assert(element('#inspector').innerHTML.includes('驻城 30/30；每方出战上限10人。'));
 context.transferCity(home);assert(lastDialog.body.includes('目的城仍最多30人。'));
 const remembered=Object.fromEntries(Object.entries(officers).map(([id,o])=>[id,o.health]));
 for(const o of Object.values(officers))o.health=0;
 context.renderCity();
 for(const id of ['depart','recruit-officer','transfer'])assert(new RegExp(`id="${id}"[^>]*disabled`).test(element('#inspector').innerHTML),'No healthy actor: '+id);
 for(const[id,health]of Object.entries(remembered))officers[id].health=health;
 const gold=home.gold,grain=home.grain;home.gold=0;home.grain=0;context.renderCity();
 assert(/id="recruit" disabled/.test(element('#inspector').innerHTML),'Resource shortage disables reserve recruitment before spending');home.gold=gold;home.grain=grain;
 // Shipped Japanese patterns interpolate both capacities instead of freezing 30.
 const patterns=JSON.parse(fs.readFileSync(path.join(root,'game/locales/ui-ja.json'),'utf8')).patterns;
 const japanese=value=>{const row=patterns.find(row=>new RegExp(row.pattern,row.flags||'u').test(value));assert(row,'Missing translated capacity pattern: '+value);return value.replace(new RegExp(row.pattern,row.flags||'u'),row.replacement);};
 for(const limit of [30,99]){
  assert.equal(japanese(`驻城 ${limit}/${limit}；每方出战上限10人。`),`在籍 ${limit}/${limit}人。出陣は各軍10人まで。`);
  assert.equal(japanese(`每城${limit}人；每方出战最多10人，包含主将。`),`1都市${limit}人まで。主将を含め各軍10人まで出陣できます。`);
 }
 // The current server's complete scenario list is displayed directly.
 Object.assign(context,{gameAudio:{setScene(){}},setupPreview:null,busy:false,mapMode:'all',mapColor:()=> '#fff',renderMap(){},document:{querySelector:selector=>selector==='meta[name="game-campaign-count"]'?{content:'29'}:null,querySelectorAll:()=>[],addEventListener(){}},GameI18n:{locale:'zh-Hant'}});
 context.view.catalog.scenarios=Array.from({length:29},(_,i)=>({id:`mainland${184+i}-01`,title:`本篇${i+1}`,year:184+i,month:1,cities:115,capacity:99,serving:1,free:0,configured:1023,initial_owners:{home:'wei'},factions:[{id:'wei',city:'home',name:'曹操勢力',captain:'曹操'}],main_scenario:{group:i<23?'custom':'if',fictional:i>=23,summary:'目前本篇配置'}}));
 context.view.catalog.scenario_id=context.view.catalog.scenarios[3].id;
 vm.runInContext(source.slice(source.indexOf("let campaignDifficulty="),source.indexOf("const $=")),context);
 vm.runInContext(source.slice(source.indexOf('function selectFaction('),source.indexOf('function renderMap(')),context);
 context.selectFaction();
 const menu=element('#inspector').innerHTML;
 assert.equal((menu.match(/<option value="mainland/g)||[]).length,29);
 assert.equal((menu.match(/<optgroup /g)||[]).length,2);
 assert(menu.includes('<optgroup label="史实">'));assert(menu.includes('<optgroup label="假想">'));
 assert(menu.includes('mainland187-01" selected'));assert(menu.includes('每城99人'));
 assert(!menu.includes('旧存档'));assert(!menu.includes('旧版战役配置'));
 assert(menu.includes('继续当前战役'),'Current running campaign still has a return control');
 assert(menu.includes('data-scenario-count="29"'));assert(!menu.includes('id="scenario-version-warning"'));
 const previous=JSON.stringify(context.view.game);
 context.view.catalog.scenarios=context.view.catalog.scenarios.slice(0,25);context.selectFaction();
 const stale=element('#inspector').innerHTML;
 assert(stale.includes('data-scenario-count="25"')&&stale.includes('id="scenario-version-warning"'));
 assert(stale.includes('本頁版本應有29篇')&&stale.includes('https://kai987.github.io/Three-Kingdoms2-King-mainland/'));
 assert.equal(JSON.stringify(context.view.game),previous,'Detecting an outdated local catalogue cannot reset the running campaign');
 await weightedTransferChecks();
 // Exercise city capacity and deployment as independent configured rules.
 const python=spawnSync(process.env.PYTHON||'python3',['-B','-c',`
import sys
from types import SimpleNamespace
sys.path.insert(0,'source')
from remake.officers import GameRules,CityRoster,select_deployment,transfer_officers,CapacityError
modern=GameRules(99,10,1200);smaller=GameRules(30,10,1200)
roster=CityRoster('home',list(range(99)),modern);roster.validate()
officers={i:SimpleNamespace(runtime_id=i,alive=True,health=90,troops=300,faction_id='wei') for i in range(99)}
assert select_deployment(roster,range(10),officers)==tuple(range(10))
try:select_deployment(roster,range(11),officers)
except ValueError:pass
else:raise AssertionError('99-person city allowed 11-person deployment')
destination=CityRoster('away',[],modern);transfer_officers(roster,destination,list(range(99)));assert len(destination.officer_ids)==99
extra=CityRoster('extra',[100],modern)
try:transfer_officers(extra,destination,[100])
except CapacityError:pass
else:raise AssertionError('100th member accepted')
assert extra.officer_ids==[100] and len(destination.officer_ids)==99
try:CityRoster('smaller',list(range(31)),smaller).validate()
except CapacityError:pass
else:raise AssertionError('configured smaller capacity ignored')
`],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
 assert.equal(python.status,0,python.stderr||python.stdout);
 console.log('capacity UI: original four-group commands, keyboard focus and city/campaign selection, unchanged action guards, concise 99-member roster, 10-member deployment, weighted daily ration selection, route/destination limits, exploration guards and atomic overflow passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
