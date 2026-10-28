/* Officer comparisons, purpose-based ordering and resource-safe persistent allocation. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../game/app.js'),'utf8'),elements=new Map();
const element=selector=>{
 if(['#route-mode','#transfer-estimate'].includes(selector))return null;
 if(!elements.has(selector))elements.set(selector,{value:'',min:'',max:'',innerHTML:'',textContent:'',disabled:false});
 return elements.get(selector);
};
const p=(strength,intellect,virtue)=>({martial_strength:strength,intellect,virtue});
const officers={
 1:{health:90,troops:80,loyalty:75,profile:p(60,70,88)},
 2:{health:95,troops:30,loyalty:90,profile:p(98,65,66)},
 3:{health:85,troops:10,loyalty:80,profile:p(80,95,99)},
 4:{health:70,troops:0,loyalty:0,profile:p(70,80,91)},
 5:{health:75,troops:0,loyalty:0,profile:p(71,81,60)},
 6:{health:80,troops:0,loyalty:0,profile:p(72,82,91)},
};
const city={id:'home',owner:'wei',reserves:20,roster:{officer_ids:[1,2,3]}},away={id:'away',owner:'wei',roster:{officer_ids:[]}},enemy={id:'enemy',owner:'wu',roster:{officer_ids:[]}};
let closed=0,lastDialog,lastCommand,picked=[],requests=0;
const context={dialogGeneration:0,queueAllocationClose(){},GameOfficerChoices:require('../game/officer-choice.js'),GameOfficerSelection:require('../game/officer-selection.js'),GameI18n:{apply(){}},view:{catalog:{rules:{city_officer_capacity:99,battle_officers_per_side:10},links:[['home','enemy']],recruitable:{home:[5,6,4]},persuadable:{home:[2]}},game:{player:'wei',turn:1,cities:{home:city,away,enemy},officers,extension:{officer_actions:{}}}},$:element,name:id=>'武将'+id,escapeHtml:String,marching:()=>new Set(),capacity:()=>99,notice(){},faction:String,cityName:String,actor:null,target:null,watchRouteDialog(){},dialog:{open:true,querySelectorAll:()=>picked.map(input=>Object.assign(input,{addEventListener(){}})),close(){closed++;}},openDialog(title,body,actions,options){
 context.dialogGeneration++;lastDialog={title,body,actions,options};
 for(const match of body.matchAll(/<select id="([^"]+)"[^>]*>(.*?)<\/select>/g)){
  const options=[...match[2].matchAll(/<option value="([^"]+)"([^>]*)>/g)];
  element('#'+match[1]).value=(options.find(row=>row[2].includes('selected'))||options.find(row=>!row[2].includes('disabled')))?.[1]||'';
 }
 for(const match of body.matchAll(/<input id="([^"]+)"([^>]+)>/g)){
  const input=element('#'+match[1]);for(const attr of ['value','min','max'])input[attr]=match[2].match(new RegExp(attr+'="([^"]*)"'))?.[1]||'';
 }
 return context.dialogGeneration;
},async command(kind,payload){
 requests++;lastCommand={kind,payload};
 if(kind==='allocate'){
  const row=commandBookFixture.api.row(context.view);
  if(payload.flow===null){commandBookFixture.consume(context.view,'allocate');row.allocation_flow={id:'1:wei:home:1',city:'home',source:'allocate'};}
  else assert.equal(payload.flow,row.allocation_flow.id,'The paid server flow is included on every later distribution');
  const officer=officers[payload.officer],delta=payload.troops-officer.troops;
  assert(delta<=city.reserves);city.reserves-=delta;officer.troops=payload.troops;
 }
 return true;
}};
context.GameCommandBooks=commandBookFixture.api;commandBookFixture.attach(context.view);
vm.createContext(context);
context.isRuler=id=>context.GameOfficerChoices.isRuler(id,context.view.game.extension?.leaders);
vm.runInContext(source.slice(source.indexOf('function officerAttributes('),source.indexOf('// Classify actual runtime entry')),context);
const values=html=>[...html.matchAll(/<option value="(\d+)"/g)].map(m=>Number(m[1]));
(async()=>{
 const before=JSON.stringify(context.view.game);
 assert.deepEqual(Array.from(context.sortedOfficers([1,2,3])),[2,3,1]);
 assert.deepEqual(Array.from(context.sortedOfficers([6,5,4],'virtue')),[6,4,5],'Ties compare intellect before stable IDs, never input mutation');
 context.recruitOfficer(city);
 const actorOptions=lastDialog.body.match(/id="recruit-actor">(.*?)<\/select>/)[1];
 assert.deepEqual(values(actorOptions),[3,1,2]);assert.deepEqual(values(element('#recruit-person').innerHTML),[6,4,5]);
 element('#recruit-actor').value='2';element('#recruit-actor').onchange();assert(element('#recruit-actor-summary').textContent.includes('武98 · 知65 · 德66'));
 assert(actorOptions.includes('30兵 · 武98 · 知65 · 德66 · 体力95 · 经验— · 忠誠90'));
 element('#recruit-mode').value='persuade_officer';element('#recruit-mode').onchange();assert(element('#recruit-person').innerHTML.includes('武98 · 知65 · 德66'));
 context.departure(city);assert(lastDialog.body.includes('武98 · 知65 · 德66'));assert(lastDialog.body.indexOf('value="2"')<lastDialog.body.indexOf('value="1"'));
 context.transferCity(city);assert(lastDialog.body.includes('武98 · 知65 · 德66'));assert(lastDialog.body.includes('忠誠90'));
 assert.equal(JSON.stringify(context.view.game),before,'Reviewing and sorting choices has no game or RNG mutation');
 // A low-reserve city can use exactly its own troops plus reserves, never a negative preview.
 context.allocate(city,1);
 assert.equal(element('#allocation-officer').value,'1');assert.equal(element('#allocation-troops').max,'100');assert(element('#allocation-officer-summary').textContent.includes('武60 · 知70 · 德88'));
 const input=element('#allocation-troops');input.value='9999';input.oninput();assert.equal(input.value,'100');assert.equal(element('#allocation-preview').textContent,'确认后本城预备兵 0。');
 await element('#confirm-allocation').onclick();
 assert.equal(lastCommand.payload.troops,100);assert.equal(city.reserves,0);assert.equal(officers[1].troops,100);assert.equal(closed,0,'Successful allocation remains open');assert.equal(lastDialog.title,'编兵');assert.equal(element('#allocation-officer').value,'1','Selected officer survives refresh');assert.equal(element('#allocation-troops').value,'100');
 const paidBooks=commandBookFixture.api.row(context.view).used,paidFlow=commandBookFixture.api.activeAllocation(context.view,'home').id,paidRequests=requests;
 assert(lastDialog.actions.includes('id="allocation-next"'));
 element('#allocation-next').onclick();assert.equal(element('#allocation-officer').value,'2');assert.equal(element('#allocation-troops').value,'30');
 assert.equal(commandBookFixture.api.row(context.view).used,paidBooks);assert.equal(commandBookFixture.api.activeAllocation(context.view,'home').id,paidFlow);assert.equal(requests,paidRequests,'Next officer changes only the form, not the paid flow, books or game');
 element('#allocation-officer').value='1';element('#allocation-officer').onchange();
 // The next operation reads new resources; reducing troops returns them to reserves.
 element('#allocation-troops').value='40';element('#allocation-troops').oninput();assert.equal(element('#allocation-preview').textContent,'确认后本城预备兵 60。');
 await element('#confirm-allocation').onclick();assert.equal(city.reserves,60);assert.equal(closed,0);
 element('#allocation-officer').value='2';element('#allocation-officer').onchange();assert.equal(element('#allocation-troops').value,'30');assert.equal(element('#allocation-troops').max,'90');
 element('#allocation-troops').value='999';await element('#confirm-allocation').onclick();assert.equal(lastCommand.payload.troops,90,'Confirmation clamps pasted values even with no input event');assert.equal(city.reserves,0);
 element('#allocation-troops').value='-5';element('#allocation-troops').oninput();assert.equal(element('#allocation-troops').value,'0');
 element('#allocation-troops').value='3.9';element('#allocation-troops').oninput();assert.equal(element('#allocation-troops').value,'3');
 element('#allocation-troops').value='';element('#allocation-troops').oninput();assert.equal(element('#allocation-troops').value,'');element('#allocation-troops').onblur();assert.equal(element('#allocation-troops').value,'0');
 city.reserves=5000;context.allocate(city,1);assert.equal(element('#allocation-troops').max,'999','Game troop cap still applies with ample reserves');
 // The same normalization is used by every numeric input, including the random seed.
 const seed={min:'1',max:'4294967295',value:'999999999999'};context.bindNumberInput(seed);seed.oninput();assert.equal(seed.value,'4294967295');seed.value='-2';seed.onchange();assert.equal(seed.value,'1');seed.value='';seed.onblur();assert.equal(seed.value,'1');seed.value='Infinity';seed.onblur();assert.equal(seed.value,'1');
 assert.equal((source.match(/type="number"/g)||[]).length,2,'All current numeric controls are explicitly covered');
 assert(source.includes('bindNumberInput($(\'#seed\'))'));assert(source.includes('bindNumberInput(input,preview)'));
 assert(source.includes('<th>经</th>'));assert(source.includes('<th>德</th>'));assert(source.includes('<td>${o.virtue}</td>'));assert(source.includes('<td>${o.profile.virtue}</td>'));
 assert.equal(commandBookFixture.api.row(context.view).used,1,'One city-wide distribution pays once across multiple officers');commandBookFixture.exhaust(context.view);context.allocate(city,1);assert(element('#confirm-allocation').disabled);const beforeExhausted=requests;await element('#confirm-allocation').onclick();assert.equal(requests,beforeExhausted);
 assert(requests===3);
 const flow=commandBookFixture.api.activeAllocation(context.view,'home');context.allocate(city,1,flow.id);
 element('#allocation-troops').value=String(officers[1].troops+1);element('#allocation-troops').oninput();assert(!element('#confirm-allocation').disabled,'An already-paid distribution remains usable after the last book is spent');
 await element('#confirm-allocation').onclick();assert.equal(requests,4);assert.equal(commandBookFixture.api.row(context.view).used,commandBookFixture.api.row(context.view).total);
 assert(lastDialog.body.includes('data-command-book-cost="0"'));assert(lastDialog.actions.includes('完成配兵'));
 const oldFactions=context.view.catalog.factions;
 context.view.catalog.factions=[{id:'wei',captain:'关羽',name:'关羽',display_name:'关羽',ruler_person_id:'san14-candidate-0147'}];
 context.GamePortraits={html:(id,name)=>`<span data-portrait-person="${id}" data-portrait-name="${name}"></span>`};
 const leaderView=JSON.stringify(context.view),identity=context.factionIdentityHtml('wei');
 assert(identity.includes('data-current-faction="wei"'));assert(identity.includes('data-portrait-person="san14-candidate-0147"'));assert(identity.includes('data-portrait-name="关羽"'));assert(identity.includes('data-current-faction-label'));
 assert.equal(JSON.stringify(context.view),leaderView,'Current ruler portrait and label are read-only');context.view.catalog.factions=oldFactions;delete context.GamePortraits;
 console.log('officer controls: comparable attributes, deterministic purpose sort, numeric bounds, exact conservation and persistent allocation passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
