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
const context={refreshPersonnelDialogue(){},dialogGeneration:0,queueAllocationClose(){},GameOfficerChoices:require('../game/officer-choice.js'),GameOfficerSelection:require('../game/officer-selection.js'),GameI18n:{apply(){}},view:{catalog:{rules:{city_officer_capacity:99,battle_officers_per_side:10},links:[['home','enemy']],recruitable:{home:[5,6,4]},persuadable:{home:[2]}},game:{player:'wei',turn:1,cities:{home:city,away,enemy},officers,extension:{officer_actions:{}}}},$:element,name:id=>'武将'+id,escapeHtml:String,marching:()=>new Set(),capacity:()=>99,notice(){},faction:String,cityName:String,actor:null,target:null,watchRouteDialog(){},dialog:{open:true,querySelectorAll:()=>picked.map(input=>Object.assign(input,{addEventListener(){}})),close(){closed++;}},openDialog(title,body,actions,options){
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
  assert(Array.isArray(payload.allocations));assert(!Object.hasOwn(payload,'officer'));
  const delta=payload.allocations.reduce((sum,item)=>sum+item.troops-officers[item.officer].troops,0);
  assert(delta<=city.reserves);city.reserves-=delta;for(const item of payload.allocations)officers[item.officer].troops=item.troops;
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
 // Navigation saves draft values only: no command, book, reserve or RNG mutation.
 context.allocate(city,1);
 assert.equal(element('#allocation-officer').value,'1');assert.equal(element('#allocation-troops').max,'100');assert(element('#allocation-officer-summary').textContent.includes('武60 · 知70 · 德88'));
 const initial=JSON.stringify(context.view),input=element('#allocation-troops');
 input.value='9999';input.oninput();assert.equal(input.value,'100');assert.equal(element('#allocation-preview').textContent,'确认后本城预备兵 0。');
 await element('#allocation-next').onclick();assert.equal(element('#allocation-officer').value,'2');assert.equal(input.value,'30');assert.equal(input.max,'30','One shared reserve budget includes all officer drafts');
 input.value='0';input.oninput();await element('#allocation-next').onclick();assert.equal(element('#allocation-officer').value,'3');assert.equal(input.max,'40');
 element('#allocation-officer').value='1';element('#allocation-officer').onchange();assert.equal(input.value,'100','Dropdown revisits preserve earlier drafts');
 assert.equal(JSON.stringify(context.view),initial);assert.equal(requests,0,'Next and dropdown never call the server');
 await element('#confirm-allocation').onclick();
 assert.equal(requests,1);assert.equal(lastCommand.payload.flow,null);assert.equal(lastCommand.payload.allocations.length,2);
 assert.equal(city.reserves,30);assert.equal(officers[1].troops,100);assert.equal(officers[2].troops,0);assert.equal(closed,0,'Final success keeps allocation open');
 assert.equal(element('#allocation-officer').value,'1');assert.equal(input.value,'100');assert(element('#confirm-allocation').disabled,'No changed draft cannot be resubmitted');
 const paidFlow=commandBookFixture.api.activeAllocation(context.view,'home').id;
 assert.equal(commandBookFixture.api.row(context.view).used,1);
 input.value='40';input.oninput();await element('#allocation-next').onclick();input.value='999';await element('#confirm-allocation').onclick();
 assert.equal(officers[1].troops,40);assert.equal(officers[2].troops,90);assert.equal(city.reserves,0);assert.equal(lastCommand.payload.flow,paidFlow);assert.equal(commandBookFixture.api.row(context.view).used,1,'Later batches reuse the exact paid city flow');
 // Bounds clamp before a switch even when paste does not fire an input event.
 input.value='-5';input.oninput();assert.equal(input.value,'0');input.value='3.9';input.oninput();assert.equal(input.value,'3');input.value='';input.oninput();assert.equal(input.value,'');input.onblur();assert.equal(input.value,'0');
 city.reserves=5000;context.allocate(city,1);assert.equal(input.max,'1000');input.value='99999';await element('#allocation-next').onclick();element('#allocation-officer').value='1';element('#allocation-officer').onchange();assert.equal(input.value,'1000');assert.equal(officers[1].troops,40,'Next stores a capped draft without allocating soldiers');
 // Closing and opening anew discards unconfirmed drafts.
 context.allocate(city,1);assert.equal(input.value,'40');assert(element('#confirm-allocation').disabled);
 const seed={min:'1',max:'4294967295',value:'999999999999'};context.bindNumberInput(seed);seed.oninput();assert.equal(seed.value,'4294967295');seed.value='-2';seed.onchange();assert.equal(seed.value,'1');seed.value='';seed.onblur();assert.equal(seed.value,'1');seed.value='Infinity';seed.onblur();assert.equal(seed.value,'1');
 assert.equal((source.match(/type="number"/g)||[]).length,3,'All current numeric controls are explicitly covered');
 assert(source.includes('id="battle-facility-batches" type="number" min="1" max="${trade.max_batches}"'));
 assert(source.includes('Math.min(trade.max_batches,Math.max(1,Math.trunc(Number(input.value)||1)))'));
 assert(source.includes('bindNumberInput($(\'#seed\'))'));assert(source.includes('bindNumberInput(input,preview)'));
 assert(source.includes('<th>经</th>'));assert(source.includes('<th>德</th>'));assert(source.includes('<td>${o.virtue}</td>'));assert(source.includes('<td>${o.profile.virtue}</td>'));
 commandBookFixture.exhaust(context.view);context.allocate(city,1);input.value='45';input.oninput();assert(element('#confirm-allocation').disabled);const exhaustedRequests=requests;await element('#allocation-next').onclick();assert.equal(requests,exhaustedRequests,'Navigation remains free with no books');
 context.allocate(city,1,paidFlow);input.value='45';input.oninput();assert(!element('#confirm-allocation').disabled);await element('#confirm-allocation').onclick();assert.equal(officers[1].troops,45);assert.equal(commandBookFixture.api.row(context.view).remaining,0);assert(lastDialog.body.includes('data-command-book-cost="0"'));
 // Declining payment or failing submission preserves the complete draft;
 // rapid confirmations submit at most one immutable batch.
 commandBookFixture.attach(context.view,3);context.allocate(city,1);
 input.value='50';await element('#allocation-next').onclick();input.value='95';input.oninput();
 const beforeConfirm=JSON.stringify(context.view),originalCommand=context.command;
 let attempts=0,resolveConfirm;
 context.command=async()=>{attempts++;return false;};await element('#confirm-allocation').onclick();assert.equal(attempts,1);assert.equal(input.value,'95');assert.equal(JSON.stringify(context.view),beforeConfirm);
 element('#allocation-officer').value='1';element('#allocation-officer').onchange();assert.equal(input.value,'50');
 context.command=()=>{attempts++;return new Promise(resolve=>{resolveConfirm=resolve;});};
 const pending=element('#confirm-allocation').onclick();assert(element('#allocation-next').disabled);assert(element('#allocation-officer').disabled);await element('#confirm-allocation').onclick();assert.equal(attempts,2);
 resolveConfirm(false);await pending;assert.equal(input.value,'50');assert(!element('#allocation-next').disabled);assert.equal(JSON.stringify(context.view),beforeConfirm);
 context.command=originalCommand;await element('#confirm-allocation').onclick();assert.equal(officers[1].troops,50);assert.equal(officers[2].troops,95);assert.equal(commandBookFixture.api.row(context.view).used,1);
 const staleClosures=[];context.queueAllocationClose=value=>staleClosures.push(value);
 const staleFlow=commandBookFixture.api.activeAllocation(context.view,'home').id;context.allocate(city,1,staleFlow);input.value='51';input.oninput();
 let finishStale;context.command=(kind,payload)=>new Promise(resolve=>{finishStale=async()=>resolve(await originalCommand(kind,payload));});
 const staleSubmission=element('#confirm-allocation').onclick();context.allocate(city,3);await finishStale();await staleSubmission;
 assert.equal(element('#allocation-officer').value,'3','A completed older dialog cannot replace a newer officer selection');assert.equal(staleClosures.length,1);assert.equal(staleClosures[0].flow,staleFlow,'Only the completed exact paid flow is queued for safe closure');context.command=originalCommand;
 const oldFactions=context.view.catalog.factions;
 context.view.catalog.factions=[{id:'wei',captain:'关羽',name:'关羽',display_name:'关羽',ruler_person_id:'san14-candidate-0147'}];
 context.GamePortraits={html:(id,name)=>`<span data-portrait-person="${id}" data-portrait-name="${name}"></span>`};
 const leaderView=JSON.stringify(context.view),identity=context.factionIdentityHtml('wei');
 assert(identity.includes('data-current-faction="wei"'));assert(identity.includes('data-portrait-person="san14-candidate-0147"'));assert(identity.includes('data-portrait-name="关羽"'));assert(identity.includes('data-current-faction-label'));
 assert.equal(JSON.stringify(context.view),leaderView,'Current ruler portrait and label are read-only');context.view.catalog.factions=oldFactions;delete context.GamePortraits;
 console.log('officer controls: comparable attributes, deterministic purpose sort, numeric bounds, exact conservation and persistent allocation passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
