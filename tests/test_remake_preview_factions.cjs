/* Preview city choices select the scenario owner, without writing a campaign. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const summary={textContent:''},list={scrollTop:40,getBoundingClientRect:()=>({top:100,bottom:300})};
const radios=['han','wei','wu'].map((value,index)=>({value,checked:value==='han',
 closest:()=>({getBoundingClientRect:()=>({top:100+index*140,bottom:190+index*140}),closest:()=>list})}));
const cityElements=['livehome','occupied','capital','empty','unplayable'].map(city=>({dataset:{city},focus(options){assert.deepEqual(Object.keys(options),['preventScroll']);assert(options.preventScroll);}}));
const factions=[{id:'han',name:'何进',city:'livehome'},{id:'wei',name:'曹操',city:'capital'},{id:'wu',name:'孙权',city:'occupied'}];
const scenario=(year,owners)=>({id:'scenario'+year,year,month:7,factions,initial_owners:owners,faction:'han',focus:'livehome'});
const game={player:'han',phase:'city',turn:3,year:184,month:2,day:21,rng:{state:2026,draws:7},cities:{occupied:{owner:'han'},empty:{owner:'wu'}}};
let renders=0,cityRenders=0,suppressed=false;const information=[],cameraCalls=[],sounds=[];
const context={setupPreview:scenario(200,{livehome:'han',capital:'wei',occupied:'wei',empty:'neutral',unplayable:'other'}),
 game,view:{revision:11,game},busy:false,mapAction:null,selectedCity:'livehome',mapMode:'custom',
 mapCamera:{x:350,y:250,zoom:3},board:cityElements.map((row,index)=>({id:row.dataset.city,position:[100+index*20,200]})),
 cityName:id=>'城'+id,resourceSummary:(id,preview)=>`钱${preview.year} · ${id}`,
 $:selector=>selector==='#setup-summary'?summary:cityElements.find(row=>selector===`[data-city="${row.dataset.city}"]`),
 document:{querySelectorAll:selector=>selector==='input[name=faction]'?radios:cityElements},
 renderMap(){renders++;},renderCity(){cityRenders++;},showCityInformation:id=>information.push(id),finishMapAction(){throw Error('Preview cannot execute a map command');},
 mapPosition:city=>city.position,mapNavigation:{focus:(...args)=>cameraCalls.push(args),shouldSuppressClick:()=>suppressed},gameAudio:{play:id=>sounds.push(id)}
};
context.preview=context.setupPreview;context.owners=context.preview.initial_owners;
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function setPreviewFaction('),source.indexOf('function renderMap(')),context);
const mapStart=source.indexOf('function renderMap('),chooseStart=source.indexOf(' const choose=(id,inspect=false)=>{',mapStart),chooseEnd=source.indexOf(' const navigationControls=',chooseStart);
assert(chooseStart>=0&&chooseEnd>chooseStart,'Use the real map city-choice handler');
vm.runInContext(source.slice(chooseStart,chooseEnd)+'\nglobalThis.choosePreviewCity=choose;',context);
const bindingStart=source.indexOf(" document.querySelectorAll('[data-city],[data-city-label]')",chooseEnd),bindingEnd=source.indexOf('\n}',bindingStart);
vm.runInContext(source.slice(bindingStart,bindingEnd),context);
const snapshot=JSON.stringify({view:context.view,game,seed:2026}),camera=JSON.stringify(context.mapCamera);
const checked=()=>radios.filter(row=>row.checked).map(row=>row.value);

// A mouse click on a non-capital changes the chosen faction and preview focus,
// using this scenario's year/month ownership instead of the running campaign.
cityElements[1].onclick({detail:1});
assert.equal(context.setupPreview.faction,'wei');assert.equal(context.setupPreview.focus,'occupied');
assert.deepEqual(checked(),['wei']);assert(summary.textContent.includes('曹操 · 2座城池 · 根据地城capital'));
assert(summary.textContent.includes('钱200 · wei'));assert.deepEqual(information,['occupied']);assert.equal(cityRenders,0);
assert.equal(JSON.stringify(context.mapCamera),camera);assert.deepEqual(cameraCalls,[],'Map clicks retain the current pan/zoom');
assert.equal(list.scrollTop,70,'Only the faction list scrolls to reveal its checked row');

// Empty cities still open city information and become focused, but cannot
// clear or replace the previously selected playable faction.
const priorSummary=summary.textContent,priorListTop=list.scrollTop;
cityElements[3].onclick({detail:1,pointerType:'touch'});
assert.equal(context.setupPreview.focus,'empty');assert.equal(context.setupPreview.faction,'wei');assert.deepEqual(checked(),['wei']);
assert.equal(summary.textContent,priorSummary);assert.equal(list.scrollTop,priorListTop);assert.equal(information.at(-1),'empty');
cityElements[4].onclick({detail:1});assert.equal(context.setupPreview.faction,'wei');assert.deepEqual(checked(),['wei'],'An owner absent from playable factions cannot uncheck the player selection');

// Enter and Space share exactly the same city selection path as pointer/touch.
for(const key of ['Enter',' ']){
 context.setupPreview.faction='han';let prevented=false;
 cityElements[1].onkeydown({key,preventDefault(){prevented=true;}});
 assert(prevented);assert.equal(context.setupPreview.faction,'wei');assert.deepEqual(checked(),['wei']);
}
const beforeDrag=JSON.stringify(context.setupPreview);suppressed=true;cityElements[0].onclick({detail:1});suppressed=false;assert.equal(JSON.stringify(context.setupPreview),beforeDrag,'A pan gesture cannot choose another faction');
context.busy=true;context.choosePreviewCity('livehome',true);context.busy=false;assert.equal(context.setupPreview.faction,'wei');

// Switching scenarios uses the new dated snapshot even when the city key and
// live campaign owner do not change; selection never uses game.cities owners.
context.setupPreview=scenario(225,{livehome:'han',capital:'wei',occupied:'wu',empty:'neutral'});context.preview=context.setupPreview;context.owners=context.preview.initial_owners;
cityElements[1].onclick({detail:1});assert.equal(context.setupPreview.faction,'wu');assert.deepEqual(checked(),['wu']);assert(summary.textContent.includes('孙权 · 1座城池'));assert(summary.textContent.includes('钱225 · wu'));
assert.equal(context.setPreviewFaction('wei'),true);assert.equal(context.setupPreview.focus,'capital','A radio selection retains its existing capital-focus behavior');assert.deepEqual(checked(),['wei']);
assert.equal(context.setPreviewFaction('neutral'),false);assert.deepEqual(checked(),['wei']);

// The map's city dropdown keeps its existing focus behavior, including zoom.
context.choosePreviewCity('occupied',false);assert.deepEqual(cameraCalls.at(-1),[120,200,3]);assert.equal(context.setupPreview.focus,'occupied');
assert.equal(JSON.stringify(context.mapCamera),camera);assert.equal(context.selectedCity,'livehome');assert.equal(context.mapMode,'custom');
assert.equal(JSON.stringify({view:context.view,game,seed:2026}),snapshot,'Preview clicks/radios never write campaign ownership, date, RNG, revision, player or seed');
assert(renders>0&&sounds.every(id=>id==='click'));
console.log('preview faction choices: dated scenario owners, actual radio/summary state, empty-city retention, non-capital focus, mouse/touch/keyboard, drag guard, scoped list scroll, camera and immutable campaign passed');
