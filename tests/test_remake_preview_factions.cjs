/* Preview city choices select the scenario owner, without writing a campaign. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const summary={innerHTML:'',get textContent(){return this.innerHTML.replace(/<[^>]*>/g,'');}},list={scrollTop:40,getBoundingClientRect:()=>({top:100,bottom:300})};
const radios=['han','wei','wu'].map((value,index)=>({value,checked:value==='han',
 closest:()=>({getBoundingClientRect:()=>({top:100+index*140,bottom:190+index*140}),closest:()=>list})}));
const cityElements=['livehome','occupied','capital','empty','unplayable'].map(city=>({dataset:{city},focus(options){assert.deepEqual(Object.keys(options),['preventScroll']);assert(options.preventScroll);}}));
const factions=[{id:'han',name:'何进',captain:'何进',city:'livehome',ruler_person_id:'san14-candidate-0001'},{id:'wei',name:'曹操',captain:'曹操',city:'capital',ruler_person_id:'san14-candidate-0002'},{id:'wu',name:'孙权',captain:'孙权',city:'occupied',ruler_person_id:'san14-candidate-0003'}];
const scenario=(year,owners)=>({id:'scenario'+year,year,month:7,factions,initial_owners:owners,faction:'han',focus:'livehome'});
const game={player:'han',phase:'city',turn:3,year:184,month:2,day:21,rng:{state:2026,draws:7},cities:{occupied:{owner:'han'},empty:{owner:'wu'}}};
let renders=0,cityRenders=0,suppressed=false;const information=[],cameraCalls=[],sounds=[];
const i18n={locale:'zh-Hant'},languageHandlers=[];
const context={setupPreview:scenario(200,{livehome:'han',capital:'wei',occupied:'wei',empty:'neutral',unplayable:'other'}),
 game,view:{revision:11,game,catalog:{library:[{id:7,person_id:'san14-candidate-0004'}]}},busy:false,mapAction:null,selectedCity:'livehome',mapMode:'custom',
 GamePortraits:require('../game/portraits.js').create({document:null,i18n}),GameI18n:i18n,
 escapeHtml:value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 mapCamera:{x:350,y:250,zoom:3},board:cityElements.map((row,index)=>({id:row.dataset.city,position:[100+index*20,200]})),
 cityName:id=>'城'+id,resourceSummary:(id,preview)=>`钱${preview.year} · ${id}`,
 $:selector=>selector==='#setup-summary'?summary:cityElements.find(row=>selector===`[data-city="${row.dataset.city}"]`),
 document:{querySelectorAll:selector=>selector==='input[name=faction]'?radios:cityElements,addEventListener:(type,handler)=>{if(type==='game-language-change')languageHandlers.push(handler);}},localAutosave:null,
 renderMap(){renders++;},renderCity(){cityRenders++;},showCityInformation:id=>information.push(id),finishMapAction(){throw Error('Preview cannot execute a map command');},
 mapPosition:city=>city.position,mapNavigation:{focus:(...args)=>cameraCalls.push(args),shouldSuppressClick:()=>suppressed},gameAudio:{play:id=>sounds.push(id)}
};
context.preview=context.setupPreview;context.owners=context.preview.initial_owners;
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function previewRulerPortrait('),source.indexOf('function renderMap(')),context);
vm.runInContext(source.match(/^document\.addEventListener\('game-language-change',.*$/m)[0],context);
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
assert(summary.innerHTML.includes('class="setup-ruler-portrait"'));assert(summary.innerHTML.includes('data-portrait-person="san14-candidate-0002"'));
assert(summary.innerHTML.indexOf('setup-ruler-portrait')<summary.innerHTML.indexOf('setup-summary-copy'),'The dated ruler portrait precedes the introduction');
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
assert(summary.innerHTML.includes('data-portrait-person="san14-candidate-0003"'),'Map selection also replaces the ruler portrait');
assert.equal(context.setPreviewFaction('wei'),true);assert.equal(context.setupPreview.focus,'capital','A radio selection retains its existing capital-focus behavior');assert.deepEqual(checked(),['wei']);
assert.equal(context.setPreviewFaction('neutral'),false);assert.deepEqual(checked(),['wei']);

// The map's city dropdown keeps its existing focus behavior, including zoom.
context.choosePreviewCity('occupied',false);assert.deepEqual(cameraCalls.at(-1),[120,200,3]);assert.equal(context.setupPreview.focus,'occupied');
assert.equal(JSON.stringify(context.mapCamera),camera);assert.equal(context.selectedCity,'livehome');assert.equal(context.mapMode,'custom');
assert.equal(JSON.stringify({view:context.view,game,seed:2026}),snapshot,'Preview clicks/radios never write campaign ownership, date, RNG, revision, player or seed');
assert(renders>0&&sounds.every(id=>id==='click'));
// A successor is identified by the dated preview, even with the same faction
// key and a previous campaign still running. Missing identity never guesses.
const later=scenario(249,{livehome:'han',capital:'wei',occupied:'wu'});
later.factions=factions.map(f=>f.id==='wei'?{...f,name:'曹魏',captain:'曹芳',ruler_person_id:'san14-candidate-0004'}:{...f});
context.setupPreview=later;context.setPreviewFaction('wei');
assert(summary.innerHTML.includes('data-portrait-person="san14-candidate-0004"'));assert(summary.innerHTML.includes('data-portrait-name="曹芳"'));
assert(!summary.innerHTML.includes('data-portrait-person="san14-candidate-0002"'),'A faction key cannot reuse its earlier ruler');
i18n.locale='ja';languageHandlers.forEach(handler=>handler());
assert(summary.innerHTML.includes('data-l10n-native="ja"'));assert(summary.innerHTML.includes('曹芳の肖像を準備中')||summary.innerHTML.includes('曹芳 · 肖像を準備中'));
assert.deepEqual(checked(),['wei']);assert.equal(context.setupPreview.focus,'capital','Language refresh retains selection and focus');
delete later.factions[1].ruler_person_id;later.faction_rulers={wei:7};context.setPreviewFaction('wei');
assert(summary.innerHTML.includes('data-portrait-person="san14-candidate-0004"'),'An explicit scenario runtime ID resolves through the catalog person-ID map');
later.faction_rulers={wei:999};context.setPreviewFaction('wei');
assert(!summary.innerHTML.includes('setup-ruler-portrait'),'An unknown ruler ID displays the introduction without a false portrait');
delete later.faction_rulers;context.setPreviewFaction('wei');
assert(!summary.innerHTML.includes('setup-ruler-portrait'),'A display name alone cannot select a portrait');
assert.equal(JSON.stringify({view:context.view,game,seed:2026}),snapshot,'Portrait and language updates do not mutate campaign state');
// Generic group names are replaced by the dated ruler's name, without
// rewriting actual polity names or selecting portraits from display text.
for(const name of ['南中勢力','南中势力','士燮势力']){
 const ruler={id:'wu',name,captain:'孟获',city:'occupied',ruler_person_id:'san14-candidate-0845'};
 context.setupPreview={...later,factions:[ruler]};
 context.setPreviewFaction('wu');
 assert.equal(context.factionDisplayName(ruler),'孟获');
 assert(summary.innerHTML.includes('<span class="setup-summary-copy">孟获 · '));assert(!summary.textContent.includes(name));
 assert(summary.innerHTML.includes('data-portrait-person="san14-candidate-0845"'));
 assert(summary.innerHTML.includes('data-portrait-name="孟获"'));
}
assert.equal(context.factionDisplayName({name:'曹魏',captain:'曹奂'}),'曹魏');
assert.equal(context.factionDisplayName(null),'');
const inherited={id:'shu',name:'刘备势力',captain:'刘禅',display_name:'刘禅',ruler_person_id:'san14-candidate-0945'};
assert.equal(context.factionDisplayName(inherited),'刘禅','Live leader display takes priority over a cached opening label');
const inheritedPortrait=context.previewRulerPortrait({faction_rulers:{shu:0}},inherited);
assert(inheritedPortrait.includes('data-portrait-person="san14-candidate-0945"'));
assert(inheritedPortrait.includes('data-portrait-name="刘禅"'),'The current ruler portrait follows its explicit person identity');
assert.equal(context.factionDisplayName({id:'shu',name:'刘备势力',captain:'刘备'}),'刘备','A separately selected historical opening never borrows the live successor');
// Exercise the shipped succession snapshots rather than a fixed faction-name
// portrait table: Wei changes Cao Cao -> Cao Fang -> Cao Huan, and late Wu is
// Sun Xiu. Each portrait uses that catalog's source person identity.
for(const [file,key,personId,captain]of [
 ['190-01','wei','san14-candidate-0521','曹操'],
 ['249-01','wei','san14-candidate-0529','曹芳'],
 ['263-05','wei','san14-candidate-0503','曹奂'],
 ['263-05','wu','san14-candidate-0548','孙休']
]){
 const catalog=JSON.parse(fs.readFileSync(require.resolve(`../game/data/campaigns/${file}.json`),'utf8'));
 const chosen=catalog.factions.find(f=>f.id===key),previousCatalog=context.view.catalog;
 context.view.catalog={library:catalog.people.map(p=>({id:p.runtime_id,person_id:p.person_id}))};
 const portrait=context.previewRulerPortrait({faction_rulers:catalog.faction_rulers},chosen);
 assert.equal(chosen.captain,captain);assert(portrait.includes(`data-portrait-person="${personId}"`));
 assert(portrait.includes(`data-portrait-name="${captain}"`));context.view.catalog=previousCatalog;
}
console.log('preview faction choices: dated owners and ruler identities, radio/map/scenario/language portrait updates, missing-identity fallback, non-capital focus, mouse/touch/keyboard, drag guard, scoped list scroll, camera and immutable campaign passed');
