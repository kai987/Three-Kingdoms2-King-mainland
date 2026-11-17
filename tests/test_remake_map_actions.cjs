/* Destination inspection, route previews and cancellation are read-only. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const home={id:'home',owner:'wei',grain:100,roster:{officer_ids:[1]}},ally={id:'ally',owner:'wei',roster:{officer_ids:[]}},enemy={id:'enemy',owner:'wu',roster:{officer_ids:[4]}},blocked={id:'blocked',owner:'shu',roster:{officer_ids:[5]}},empty={id:'empty',owner:'neutral',roster:{officer_ids:[]}};
const view={revision:7,catalog:{rules:{battle_officers_per_side:10},travel_hazards:true,recruitable:{home:[2,3]},persuadable:{home:[4]}},game:{phase:'city',player:'wei',cities:{home,ally,enemy,blocked,empty},extension:{free_locations:{2:'home',3:'empty'},rng:123},officers:{1:{troops:100}}}};
view.catalog.travel_quotes={'home:enemy:land':{days:3},'home:empty:land':{days:5}};
commandBookFixture.attach(view);
let scrolls=0,focuses=0,renders=0,opened=[],notices=[];
const heading={focus:()=>focuses++},detail={scrollTop:0},next={parentElement:{}};
const elements={
 '#stage':{getBoundingClientRect:()=>({top:-600,bottom:-240}),scrollIntoView:()=>scrolls++},
 '#map-march-preview':{dataset:{}},'#map-march-heading':heading,'#map-march-detail':detail,
 '#continue-map-departure':next,'#city-jump':{}
};
const context={view,mapAction:null,busy:false,MarchCore:{quotesFor:()=>null},
 notice:(text='',error=false)=>notices.push({text,error}),renderMap:()=>renders++,GameI18n:{apply(){},t:String},cityName:String,
 escapeHtml:String,battleText:(_,ja)=>ja,officerUnavailable:()=>false,URLSearchParams,
 $:selector=>elements[selector],window:{innerHeight:844},document:{querySelector:()=>({focus:()=>focuses++})},
 departure:(city,id)=>opened.push(['depart',city.id,id]),recruitOfficer:(city,id)=>opened.push(['recruit',city.id,id])};
context.request=async path=>{
 const {pathname,searchParams}=new URL(path,'https://test.invalid');
 const source=searchParams.get('source'),target=searchParams.get('target'),revision=Number(searchParams.get('revision'));
 assert.equal(pathname,'/api/march-preview');assert.equal(source,'home');assert.equal(revision,view.revision);
 const status=view.catalog.non_aggression?'non_aggression':target==='blocked'?'no_direct_route':'available';
 const options=status==='available'?[{mode:'land',path:[source,target],days:3}]:[];
 return {source,target,revision,status,options,restrictions:[]};
};
context.hasCommandBook=kind=>commandBookFixture.api.can(view,kind);context.commandBookReason=kind=>commandBookFixture.api.reason(view,kind);
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('const routeModes='),source.indexOf('function factionResources(')),context);
vm.runInContext(source.slice(source.indexOf('function departureLimit('),source.indexOf('function departure(')),context);
function testSupplyOverlay(){
 const path=(route_id,from,to,d,one_way=false)=>({route_id,from,to,d,one_way});
 const shared=path('river','port','away','M30 40L240 40',true);
 const primary=path('low-stock','home','port','M10 10L30 40');
 const bypass=path('stocked','home','port','M10 10L60 70L30 40');
 const arrows=[];
 const layer={innerHTML:'',querySelectorAll(selector){
  assert.equal(selector,'[data-march-directed]');
  const found=this.innerHTML.match(/data-from="(.*?)" data-to="(.*?)" data-march-shared data-march-directed/g)||[];
  return found.map(()=>({dataset:shared,querySelector:()=>({getTotalLength:()=>210,getPointAtLength:x=>({x:x+30,y:40})}),
   insertAdjacentHTML:(where,html)=>arrows.push({where,html})}));
 }};
 const result={options:[{segments:[primary,shared]}],supplyShortage:true,supplyDetour:{segments:[bypass,shared]}};
 const before=JSON.stringify(result);
 context.renderMapMarchRoutes(result,layer,'transfer-supply-map-arrow');
 const groups=[...layer.innerHTML.matchAll(/<g data-march-map-kind="([^"]+)"[^>]+>[\s\S]*?<\/g>/g)];
 assert.deepEqual(groups.map(row=>row[1]),['supply-shortage','supply-shortage','supply-detour','supply-detour']);
 assert(groups[1][0].includes('data-march-shared')&&groups[3][0].includes('data-march-shared'));
 assert(groups[1][0].includes('map-march-line-bed')&&!groups[3][0].includes('map-march-line-bed'));
 assert(!groups[1][0].includes('data-march-directed')&&groups[3][0].includes('data-march-directed'));
 assert.equal(arrows.length,1);
 assert.match(arrows[0].html,/data-from="port" data-to="away".*marker-end="url\(#transfer-supply-map-arrow\)"/);
 assert.equal(JSON.stringify(result),before);
 context.renderMapMarchRoutes(null,layer);
 assert.equal(layer.innerHTML,'');
}
async function test(){
 testSupplyOverlay();
 const same=value=>JSON.parse(JSON.stringify(value)),snapshot=JSON.stringify(view);
 assert.deepEqual(same(context.actionTargetCities('depart',home)),['enemy','empty']);
 view.catalog.allied_attacks={enemy:{remaining:0}};
 assert.deepEqual(same(context.actionTargetCities('depart',home)),['empty'],'A full allied attack has no free slots');
 delete view.catalog.allied_attacks;
 assert.deepEqual(same(context.actionTargetCities('recruit',home)),['home','enemy','empty'],'Recruitment uses actual locations and the backend-authorized enemy IDs');
 context.beginMapAction('depart',home);assert.equal(opened.length,0);assert.equal(scrolls,1);assert.equal(focuses,1);assert.equal(context.mapAction.source,'home');
 await context.finishMapAction('blocked');assert.equal(opened.length,0);assert.match(detail.innerHTML,/no_direct_route/);assert(next.parentElement.hidden);
 await context.finishMapAction('enemy',true);assert.equal(opened.length,0);assert.equal(focuses,2);
 assert.match(detail.innerHTML,/陸路 · 3日/);assert.equal(next.disabled,false);
 next.onclick();assert.deepEqual(opened,[['depart','home','enemy']]);assert.equal(context.mapAction,null);
 context.beginMapAction('recruit',home);context.finishMapAction('empty');assert.deepEqual(opened.at(-1),['recruit','home','empty']);
 context.beginMapAction('recruit',home);context.cancelMapAction();assert.equal(context.mapAction,null);
 assert.equal(JSON.stringify(view),snapshot,'Target review, invalid cities and cancellation never write state/revision/RNG');
 // A live alliance removes an otherwise reachable target from the map, even if
 // an old highlighted button is selected after the relationship changes.
 context.beginMapAction('depart',home);
 view.catalog.non_aggression=[['wu','wei']];
 assert.deepEqual(same(context.actionTargetCities('depart',home)),['empty']);
 const openedBeforeAllianceClick=opened.length;
 await context.finishMapAction('enemy');
 assert.equal(opened.length,openedBeforeAllianceClick);assert.match(detail.innerHTML,/non_aggression/);assert(next.parentElement.hidden);
 context.cancelMapAction();
 context.beginMapAction('depart',home);assert.deepEqual(same(context.mapAction.targets),['empty']);context.cancelMapAction();
 delete view.catalog.non_aggression;
 // A sole local candidate opens directly without a map focus/highlight step.
 const oldFree=view.catalog.recruitable.home,oldEnemy=view.catalog.persuadable.home;
 view.catalog.recruitable.home=[2];view.catalog.persuadable.home=[];
 const priorRenders=renders,priorFocus=focuses;
 context.beginMapAction('recruit',home);
 assert.equal(context.mapAction,null);assert.deepEqual(opened.at(-1),['recruit','home','home']);assert.equal(renders,priorRenders);assert.equal(focuses,priorFocus);
 // A sole remote candidate still needs a deliberate highlighted city choice.
 view.catalog.recruitable.home=[3];context.beginMapAction('recruit',home);assert.deepEqual(same(context.mapAction.targets),['empty']);context.cancelMapAction();
 view.catalog.recruitable.home=[];const openedBefore=opened.length;context.beginMapAction('recruit',home);assert.equal(opened.length,openedBefore);assert.equal(context.mapAction,null);assert(notices.at(-1).text.includes('暂无'));
 view.catalog.recruitable.home=oldFree;view.catalog.persuadable.home=oldEnemy;
 assert.equal(JSON.stringify(view),snapshot,'The direct local shortcut also leaves state and RNG untouched');
 home.action_used=true;context.beginMapAction('depart',home);assert(context.mapAction,'An earlier order in the same city does not block the shared pool');context.cancelMapAction();delete home.action_used;
 commandBookFixture.exhaust(view);context.beginMapAction('depart',home);assert(context.mapAction);
 await context.finishMapAction('enemy');assert.match(detail.innerHTML,/命令書/);assert(next.disabled);
 context.continueMapDeparture();assert.equal(opened.length,openedBefore);context.cancelMapAction();
 commandBookFixture.attach(view);
 // A slower reply from the previous destination cannot replace the new selection.
 const request=context.request;
 let finishFirst;
 context.request=path=>path.includes('target=blocked')?new Promise(resolve=>{finishFirst=async()=>resolve(await request(path));}):request(path);
 context.beginMapAction('depart',home);
 const first=context.finishMapAction('blocked');
 await context.finishMapAction('enemy');
 await finishFirst();await first;
 assert.match(detail.innerHTML,/available/);assert.equal(context.mapAction.selection.id,'enemy');context.cancelMapAction();
 context.busy=true;context.beginMapAction('depart',home);assert.equal(context.mapAction,null);
 assert(renders>=5);
 console.log('map actions: blocked and available route previews, target-bound dialogs, command-book guards, mobile map scroll/focus, shared supply overlay arrows and immutable state passed');
}
test().catch(error=>{console.error(error);process.exitCode=1;});
