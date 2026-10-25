/* Run the real map renderer against a small DOM: scene hits must retain it. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const GameMapRenderCache=require('../game/map-render-cache.js');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
class Element{
 constructor(dataset={}){this.dataset=dataset;this.attributes={};this.classes=new Set();this.classList={toggle:(name,on)=>on?this.classes.add(name):this.classes.delete(name)};this.disabled=false;}
 setAttribute(name,value){this.attributes[name]=String(value);}
 focus(){this.focused=true;}
}
function environment(){
 const counts={writes:0,attaches:0,destroys:0,paths:0,city:0,information:[]};
 const elements=new Map([['date',new Element()],['inspector',new Element()]]);let cityElements=[],markup='';
 const stage=new Element();elements.set('stage',stage);
 Object.defineProperty(stage,'innerHTML',{get:()=>markup,set:value=>{
  counts.writes++;markup=value;
  for(const id of [...elements.keys()])if(!['stage','date','inspector'].includes(id))elements.delete(id);
  for(const match of value.matchAll(/\bid="([^"]+)"/g))elements.set(match[1],new Element());
  cityElements=[...value.matchAll(/\bdata-city(?:-label)?="([^"]+)"/g)].map(match=>new Element({[match[0].startsWith('data-city-label')?'cityLabel':'city']:match[1]}));
 }});
 const game={year:200,month:1,day:1,turn:1,phase:'city',cities:{a:{id:'a',owner:'wei',reserves:100},b:{id:'b',owner:'neutral'}},officers:{1:{troops:300}},rng:{draws:0}};
 const presentation={colors:{wei:'#00f',wu:'#f00',neutral:'#fff'},castle_fill_pixels:[[0,0]],castle_outline_pixels:[[-4,-4]],
  city_names:{},labelled_city_ids:['a','b'],added_land_roads:[{from:'a',to:'b',new_branch:[[100,100],[200,200]]}],expansion_connections:[]};
 const catalog={scenario_id:'scenario-200',cities:[{id:'a',name:'甲',position:[100,100]},{id:'b',name:'乙',position:[200,200]}],active_cities:['a','b'],
  city_profiles:{a:{tier:'giant'},b:{tier:'large'}},
  factions:[{id:'wei',name:'曹操'},{id:'wu',name:'孫權'}],world:{x:0,y:0,width:1352,height:1024,background:'/map.png'},map_presentation:presentation,
  road_additions:[['a','b']],travel_hazards:true,sea_routes:[],discovered_routes:[],regional_roads:[],scenarios:[]};
 const context={view:{game,catalog},setupPreview:null,selectedCity:'a',busy:false,mapMode:'all',cityLabels:'major',mapAction:null,
  mapCamera:null,mapCameraKey:'',mapNavigation:null,GameMapRenderCache,GameI18n:{locale:'zh-Hant'},
  GameCalendar:{text:d=>`${d.year}-${d.month}-${d.day}`,iso:d=>`${d.year}-${d.month}-${d.day}`,period:day=>String(day)},
  $:selector=>selector.startsWith('#')?elements.get(selector.slice(1)):cityElements.find(el=>selector===`[data-city="${el.dataset.city}"]`),
  document:{querySelectorAll:selector=>{assert.equal(selector,'[data-city],[data-city-label]');return cityElements;}},
  escapeHtml:String,mapPosition:city=>city.position,mapBackgroundHref:value=>value,
  cityName:id=>(context.setupPreview?.city_names||Object.fromEntries(context.view.catalog.cities.map(c=>[c.id,c.name])))[id],
  cityCaption:id=>context.cityName(id),mapColor:id=>context.view.catalog.map_presentation.colors[id]||'#fff',
  landMapPath:points=>{counts.paths++;return 'M'+points.map(p=>p.join(' ')).join('L');},smoothMapPath:points=>'M'+points.map(p=>p.join(' ')).join('L'),
  mapAccessKey:points=>JSON.stringify(points),mapBridgeLayer:()=>'',setPreviewFaction(){},
  gameAudio:{play(){}},renderCity(){counts.city++;},showCityInformation:id=>counts.information.push(id),finishMapAction(){},cancelMapAction(){},
  MapNavigation:{attach(svg,{initial,onChange}){
   counts.attaches++;let camera={x:150,y:150,zoom:1,...initial};
   const notify=()=>onChange({...camera});notify();
   return {destroy(){counts.destroys++;},shouldSuppressClick:()=>false,snapshot:()=>({...camera}),
    focus(x,y,zoom){camera={x,y,zoom};notify();},reset(){camera={x:150,y:150,zoom:1};notify();},zoomBy(factor){camera.zoom*=factor;notify();}};
  }}
 };
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('function factionDisplayName('),source.indexOf('function setPreviewFaction(')),context);
 vm.runInContext(source.slice(source.indexOf('function renderMap(){'),source.indexOf('\nasync function showCityInformation(')),context);
 return {context,counts,elements,stage,cities:()=>cityElements,render:()=>context.renderMap(),markup:()=>markup};
}
const env=environment(),{context,counts,elements}=env;
env.render();const svg=elements.get('world-map'),nav=context.mapNavigation,city=env.cities()[0],zoom=elements.get('map-zoom-in');
city.focus();const camera=JSON.stringify(context.mapCamera);assert.equal(counts.writes,1);assert.equal(counts.paths,1);
// Native/Worker responses may replace the complete state object. Training,
// recruitment, reserve allocation, resources and RNG do not alter the scene.
context.view=JSON.parse(JSON.stringify(context.view));
context.view.game.cities.a.reserves=0;context.view.game.officers[1].troops=400;context.view.game.rng.draws=9;context.view.revision=22;
env.render();assert.equal(elements.get('world-map'),svg);assert.equal(env.cities()[0],city);assert(city.focused);
assert.equal(context.mapNavigation,nav);assert.equal(elements.get('map-zoom-in'),zoom);assert.equal(JSON.stringify(context.mapCamera),camera);
assert.deepEqual([counts.writes,counts.paths,counts.attaches,counts.destroys],[1,1,1,0],'No SVG parsing, road construction or navigation observer/listener recreation on a scene hit');
// Reused controls receive current state, including phase transitions whose
// map stays identical. A stale closure would incorrectly render a city menu.
context.view.game={...context.view.game,phase:'ai'};env.render();env.cities()[0].onclick({detail:1});
assert.equal(counts.city,0);assert.deepEqual(counts.information,['a']);assert.equal(elements.get('world-map'),svg);
context.busy=true;env.render();assert.equal(elements.get('city-jump').disabled,true);context.busy=false;env.render();assert.equal(elements.get('city-jump').disabled,false);
// A camera gesture itself retains the node; a changed view mode is accounted
// for on the next render, and subsequent same-mode renders are reused again.
context.mapNavigation.zoomBy(2);const panned=JSON.stringify(context.mapCamera);env.render();
assert.notEqual(elements.get('world-map'),svg);assert.equal(JSON.stringify(context.mapCamera),panned);
const afterMode=elements.get('world-map');env.render();assert.equal(elements.get('world-map'),afterMode);
function invalidates(label,change){
 const before=elements.get('world-map'),attached=counts.attaches,destroyed=counts.destroys;change();env.render();
 assert.notEqual(elements.get('world-map'),before,label);assert.equal(counts.attaches,attached+1,label);assert.equal(counts.destroys,destroyed+1,label);
 const current=elements.get('world-map');env.render();assert.equal(elements.get('world-map'),current,`${label}: next unchanged scene reuses DOM`);
}
invalidates('year',()=>context.view.game.year++);
invalidates('month',()=>context.view.game.month++);
invalidates('period/day',()=>context.view.game.day=11);
invalidates('ownership',()=>context.view.game.cities.b.owner='wu');assert(env.markup().includes('data-owner="wu"'));
invalidates('owner name',()=>context.view.catalog.factions[1].name='孫堅');assert(env.markup().includes('孫堅'));
invalidates('faction color',()=>context.view.catalog.map_presentation.colors.wu='#f0f');assert(env.markup().includes('fill="#f0f"'));
invalidates('historical name',()=>context.view.catalog.cities[1].name='新乙');assert(env.markup().includes('新乙'));
invalidates('city positions',()=>context.view.catalog.cities[1].position=[210,220]);
invalidates('label layout',()=>context.view.catalog.city_label_offsets={b:[20,-20,'start']});
invalidates('selected city and its major label',()=>context.selectedCity='b');
invalidates('label mode',()=>context.cityLabels='none');assert(!env.markup().includes('data-city-label'));
invalidates('city scale',()=>context.view.catalog.city_profiles.a.tier='normal');
invalidates('language',()=>context.GameI18n.locale='ja');
invalidates('city action highlight',()=>context.mapAction={source:'a',kind:'depart',targets:['b']});assert(env.markup().includes('data-action-eligible="true"'));
invalidates('action target change',()=>context.mapAction.targets=['a']);
invalidates('action cancellation',()=>context.mapAction=null);
invalidates('discovered sea route',()=>context.view.catalog.discovered_routes.push({id:'new',from:'a',to:'b',draw:[{mode:'sea',points:[[100,100],[200,200]]}]}));assert(env.markup().includes('data-discovered-route="new"'));
invalidates('route geometry in place',()=>context.view.catalog.discovered_routes[0].draw[0].points[1]=[220,220]);
invalidates('road geometry',()=>context.view.catalog.map_presentation.added_land_roads[0].new_branch[1]=[205,205]);
invalidates('active city set',()=>context.view.catalog.active_cities=['a']);assert(!env.markup().includes('data-city="b"'));
// Inactive historical nodes also exist in the native background. Restore only
// their original sprite pixels from the audited ground, below roads and cities.
invalidates('inactive native castle mask',()=>Object.assign(context.view.catalog.map_presentation,
 {inactive_castle_ids:['b'],inactive_castle_ground:'/assets/map-city-ground.png'}));
assert(env.markup().includes('data-inactive-city="b"'));
assert(env.markup().includes('href="/assets/map-city-ground.png"'));
assert(env.markup().indexOf('data-inactive-city="b"')<env.markup().indexOf('data-city="a"'));
assert(env.markup().includes('clip-path="url(#inactive-castle-b)"'));
invalidates('historical city reappears',()=>context.view.catalog.active_cities=['a','b']);
assert(!env.markup().includes('data-inactive-city="b"'));
invalidates('world/background',()=>context.view.catalog.world={...context.view.catalog.world,width:1400,background:'/next.png'});
assert.equal(context.mapCamera.zoom,1,'A changed world retains the existing reset-to-fit rule');
const preview={id:'preview-225',year:225,month:7,day:1,initial_owners:{a:'wu',b:'wei'},factions:context.view.catalog.factions,
 map_cities:context.view.catalog.cities,active_cities:['a','b'],city_names:{a:'甲',b:'乙'},faction:'wu',focus:'a',world:context.view.catalog.world};
invalidates('preview board',()=>context.setupPreview=preview);
invalidates('preview selected faction',()=>preview.faction='wei');assert(env.markup().includes('preview-owned'));
invalidates('preview date',()=>preview.month=8);
invalidates('return from preview',()=>context.setupPreview=null);
// The stage can be replaced by battle or an error screen. A signature alone
// must never cause a detached map to be reused, or skip navigation reattach.
const key=GameMapRenderCache.key({a:1}),first={},second={};GameMapRenderCache.remember(first,key);
assert(GameMapRenderCache.matches(first,key));assert(!GameMapRenderCache.matches(second,key));assert(!GameMapRenderCache.matches(null,key));
env.stage.innerHTML='<section id="battle"></section>';env.render();assert(elements.get('world-map'));
context.mapNavigation=null;const prior=elements.get('world-map');env.render();assert.notEqual(elements.get('world-map'),prior);
const legacy=environment();delete legacy.context.GameMapRenderCache;legacy.render();legacy.render();assert.equal(legacy.counts.writes,2,'A previously cached HTML shell without the optional module retains legacy map rendering');
// Every city footprint is cleared and repainted from the same canonical road
// geometry before sprites. Unopened cities keep their center junctions.
const roadBedEnv=environment(),roadView=roadBedEnv.context.view;
roadView.catalog.map_presentation.city_road_bed={schema:'tk2-city-road-bed-v1',ground:'/assets/map-city-ground.png',path:'M100 100L200 200'};
roadView.catalog.map_presentation.inactive_castle_ids=['b'];roadView.catalog.map_presentation.inactive_castle_ground='/assets/map-city-ground.png';
roadView.catalog.active_cities=['a'];const roadState=JSON.stringify(roadView.game);roadBedEnv.render();const bedMarkup=roadBedEnv.markup();
assert(bedMarkup.includes('data-city-road-bed'));assert(bedMarkup.includes('x="200" y="200" width="4" height="4"'),'The absent city remains a masked road junction');
assert(bedMarkup.includes('data-inactive-city="b"'));assert(!bedMarkup.includes('class="city-hit unowned'));
assert(bedMarkup.includes('d="M100 100L200 200"'));assert(bedMarkup.indexOf('data-city-road-bed')<bedMarkup.indexOf('class="city-hit'));
assert.equal(JSON.stringify(roadView.game),roadState);
// Shared reaches are independent of which endpoint lists them first. Keep
// truly different curves, even if they use the same two harbour endpoints.
const riverEnv=environment(),riverPoints=[[100,100],[150,130],[200,200]];
riverEnv.context.view.catalog.river_routes=[
 {id:'ab',from:'a',to:'b',draw:[{mode:'river',reach_id:'shared',points:riverPoints}]},
 {id:'ba',from:'b',to:'a',draw:[{mode:'river',reach_id:'shared',points:[...riverPoints].reverse()}]},
 {id:'other',from:'a',to:'b',draw:[{mode:'river',reach_id:'other',points:[[100,100],[170,120],[200,200]]}]}
];riverEnv.render();assert.equal((riverEnv.markup().match(/class="river-lane"/g)||[]).length,2);
assert.equal((riverEnv.markup().match(/data-river-reach="shared"/g)||[]).length,1);
// Scale filters are exact catalog tiers; selecting an ordinary or newly added
// city must not leak its label into the giant/large modes. Cycling is UI only.
const filtered=environment(),filteredView=filtered.context.view;
filteredView.catalog.cities.push({id:'c',name:'丙',position:[300,300]});
filteredView.catalog.active_cities.push('c');filteredView.catalog.added_city_ids=['c'];
filteredView.catalog.city_profiles.c={tier:'normal'};filtered.context.selectedCity='c';
const stateBefore=JSON.stringify(filteredView.game),labels=()=>[...filtered.markup().matchAll(/data-city-label="([^"]+)"/g)].map(match=>match[1]);
filtered.render();assert.deepEqual(labels(),['a','b','c']);
for(const[mode,expected,compact]of [['giant',['a'],'名：巨'],['large',['b'],'名：大'],['all',['a','b','c'],'名：全'],['none',[],'名：隐'],['major',['a','b','c'],'名：主']]){
 filtered.elements.get('map-labels').onclick();assert.equal(filtered.context.cityLabels,mode);assert.deepEqual(labels(),expected,mode);
 assert(filtered.markup().includes(`data-label-mode="${mode}"`));assert(filtered.markup().includes(compact));
}
filtered.context.setupPreview={id:'different-year',year:225,month:7,day:1,initial_owners:{a:'wei',b:'wu',c:'neutral'},factions:filteredView.catalog.factions,
 map_cities:filteredView.catalog.cities,active_cities:['a','b','c'],city_names:{a:'甲',b:'乙',c:'丙'},faction:'wu',focus:'c',
 city_profiles:{a:{tier:'normal'},b:{tier:'giant'},c:{tier:'large'}},added_city_ids:['a']};
filtered.context.cityLabels='giant';filtered.render();assert.deepEqual(labels(),['b'],'A different scenario uses its own scale metadata');
filtered.context.GameI18n.locale='ja';filtered.render();assert.deepEqual(labels(),['b']);assert.equal(filtered.context.cityLabels,'giant');
filtered.elements.get('map-labels').onclick();assert.deepEqual(labels(),['c']);
filtered.context.GameI18n.locale='zh-Hant';filtered.render();assert.deepEqual(labels(),['c']);
assert.equal(JSON.stringify(filteredView.game),stateBefore,'City label modes, preview and language changes never alter campaign state/RNG');
console.log('map render cache: same-scene SVG/control/focus/navigation reuse, current-snapshot handlers, full visual invalidation, new routes and battle/stage recovery passed');
