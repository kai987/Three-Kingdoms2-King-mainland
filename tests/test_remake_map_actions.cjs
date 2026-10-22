/* Choosing a highlighted destination is a read-only UI step, never an order. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const home={id:'home',owner:'wei',roster:{officer_ids:[1]}},ally={id:'ally',owner:'wei',roster:{officer_ids:[]}},enemy={id:'enemy',owner:'wu',roster:{officer_ids:[4]}},blocked={id:'blocked',owner:'shu',roster:{officer_ids:[5]}},empty={id:'empty',owner:'neutral',roster:{officer_ids:[]}};
const view={revision:7,catalog:{travel_hazards:true,recruitable:{home:[2,3]},persuadable:{home:[4]}},game:{phase:'city',player:'wei',cities:{home,ally,enemy,blocked,empty},extension:{free_locations:{2:'home',3:'empty'},rng:123},officers:{}}};
let scrolls=0,focuses=0,renders=0,opened=[],notices=[];
const context={view,mapAction:null,busy:false,availableRouteModes:(from,to)=>['enemy','empty'].includes(to)?['land']:[],
 notice:(text='',error=false)=>notices.push({text,error}),renderMap:()=>renders++,GameI18n:{apply(){}},cityName:String,
 $:()=>({getBoundingClientRect:()=>({top:-600,bottom:-240}),scrollIntoView:()=>scrolls++}),window:{innerHeight:844},document:{querySelector:()=>({focus:()=>focuses++})},
 departure:(city,id)=>opened.push(['depart',city.id,id]),recruitOfficer:(city,id)=>opened.push(['recruit',city.id,id])};
vm.createContext(context);vm.runInContext(source.slice(source.indexOf('function actionTargetCities('),source.indexOf('function departure(')),context);
const same=value=>JSON.parse(JSON.stringify(value)),snapshot=JSON.stringify(view);
assert.deepEqual(same(context.actionTargetCities('depart',home)),['enemy','empty']);
assert.deepEqual(same(context.actionTargetCities('recruit',home)),['home','enemy','empty'],'Recruitment uses actual locations and the backend-authorized enemy IDs');
context.beginMapAction('depart',home);assert.equal(opened.length,0);assert.equal(scrolls,1);assert.equal(focuses,1);assert.equal(context.mapAction.source,'home');
context.finishMapAction('blocked');assert.equal(opened.length,0);assert(notices.at(-1).error);assert(context.mapAction);
context.finishMapAction('enemy');assert.deepEqual(opened,[['depart','home','enemy']]);assert.equal(context.mapAction,null);
context.beginMapAction('recruit',home);context.finishMapAction('empty');assert.deepEqual(opened.at(-1),['recruit','home','empty']);
context.beginMapAction('recruit',home);context.cancelMapAction();assert.equal(context.mapAction,null);
assert.equal(JSON.stringify(view),snapshot,'Target review, invalid cities and cancellation never write state/revision/RNG');
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
home.action_used=true;context.beginMapAction('depart',home);assert.equal(context.mapAction,null);delete home.action_used;
context.busy=true;context.beginMapAction('depart',home);assert.equal(context.mapAction,null);
assert(renders>=5);
console.log('map actions: legal enemy/free-city highlights, target-bound dialogs, invalid click/cancel guards, mobile map scroll/focus and immutable state passed');
