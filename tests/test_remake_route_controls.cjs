/* Actual app route controls: known-route aliases and explicit sea exploration. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const start=source.indexOf('const routeModes='),end=source.indexOf('function factionResources(',start);
assert(start>=0&&end>start,'Exercise the actual app route controls, not a copied implementation');
const controlsSource=source.slice(start,end)+'\nglobalThis.routeControls={routeModeSelect,travelQuote,availableRouteModes,routeOptionLabel,syncRouteModes};';
const routeOptions=require('../game/route-options.js');
const clone=value=>JSON.parse(JSON.stringify(value));
function freeze(value){if(value&&typeof value==='object'){for(const item of Object.values(value))freeze(item);Object.freeze(value);}return value;}
const escapeHtml=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const decode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
class Select{
 constructor(){this.dataset={};this.options=[];this._html='';this._value='';}
 set innerHTML(html){
  this._html=html;
  this.options=[...html.matchAll(/<option value="([^"]*)"([^>]*)>(.*?)<\/option>/g)].map(match=>({
   value:decode(match[1]),textContent:decode(match[3]),disabled:/\bdisabled\b/.test(match[2]),
   dataset:{routeKind:match[2].match(/data-route-kind="([^"]+)"/)?.[1]}
  }));
  // Match a native select: replacing its options selects the first one, and
  // assigning a missing value subsequently clears the selection.
  this._value=this.options[0]?.value||'';
 }
 get innerHTML(){return this._html;}
 set value(value){this._value=this.options.some(option=>option.value===String(value))?String(value):'';}
 get value(){return this._value;}
}
class Element{
 constructor(){this.hidden=false;this.textContent='';this.attributes=new Map();this.onclick=null;}
 setAttribute(name,value){this.attributes.set(name,String(value));}
 getAttribute(name){return this.attributes.get(name)??null;}
 click(){assert(!this.hidden,'A hidden exploration button cannot be activated by a user');assert.equal(typeof this.onclick,'function');this.onclick();}
}
function leg(id,from,to,mode,days,{hazard=null,land_km=mode==='land'?30:0,sea_km=mode==='sea'?120:0}={}){
 return {id,from,to,mode,days,terrain:mode==='sea'?'sea':'plain',distance_km:land_km+sea_km,
  land_km,sea_km,base_days:1,hazard,draw:[{kind:mode,points:[[1,2],[3,4]]}],provenance:{readOnly:true}};
}
function quote(path,routes){
 const days=routes.reduce((sum,route)=>sum+route.days,0);
 return {path,routes,days,months:Math.max(1,Math.ceil(days/30)),turns:Math.max(1,Math.ceil(days/10)),
  distance_km:routes.reduce((sum,route)=>sum+route.distance_km,0),grain_per_officer:routes.length*5,
  modes:[...new Set(routes.map(route=>route.mode))].sort()};
}
function table(from,to,modes){return Object.fromEntries(Object.entries(modes).map(([mode,q])=>[`${from}:${to}:${mode}`,q]));}
const direct=quote(['home','away'],[leg('home:away:land','home','away','land',7)]);
const alternate=quote(['home','pass','away'],[leg('home:pass:land','home','pass','land',25),leg('pass:away:land','pass','away','land',32)]);
const mixed=quote(['home','port','away'],[leg('home:port:land','home','port','land',8),leg('port:away:sea','port','away','sea',34,{land_km:30})]);
const unknown=quote(['home','away'],[leg('explore:home:away:sea','home','away','sea',35,{land_km:30,
 hazard:{kind:'monsoon_storm',month:7,wind:'tailwind',loss_percent_min:80,loss_percent_max:90}})]);
const pass=quote(['home','away'],[leg('home:away:ziwu','home','away','land',40,{
 hazard:{kind:'ziwu_rain',label:'子午谷暴雨：减员50%',survival_numerator:1,survival_denominator:2}})]);
const baselines=[];
function harness(quotes){
 const input=freeze(clone(quotes)),select=new Select(),field=new Element(),unavailable=new Element(),explore=new Element();
 const elements=new Map([['#route-mode',select],['#route-field',field],['#route-unavailable',unavailable],['#route-explore',explore]]);
 const saved=freeze({version:1,catalog_sha256:'current-catalog',state:{turn:17,year:217,month:7,day:11,
  rng:{state:2026,draws:3},soldiers:{initial:1200,lost:0},extension:{travel:{marches:[],discovered:[]}}}});
 const view=freeze({revision:7,game:saved.state,catalog:{travel_hazards:{},travel_quotes:input}});
 let worker=null,applies=0,refreshes=0,lastBuild=null,pair=['home','away'],preferred='fastest';
 const context={view,escapeHtml,$:selector=>{assert(elements.has(selector),`Unexpected DOM lookup: ${selector}`);return elements.get(selector);},
  MarchCore:{quotesFor:request=>{assert.equal(request,view);return worker;}},GameI18n:{apply(){applies++;}},
  GameRouteOptions:{build(quotes,settings){lastBuild={quotes,settings,result:routeOptions.build(quotes,settings)};return lastBuild.result;}}};
 vm.createContext(context);vm.runInContext(controlsSource,context);
 const api=context.routeControls;
 context.refreshRouteDialog=()=>{refreshes++;preferred=api.syncRouteModes(...pair,preferred);};
 const before=JSON.stringify({view,saved,input});
 baselines.push(()=>assert.equal(JSON.stringify({view,saved,input}),before,'Reviewing routes never mutates quote sources, saves, troops, ownership, revision or RNG'));
 return {api,input,view,saved,select,field,unavailable,explore,
  mount(from='home',to='away',mode='fastest'){
   const html=api.routeModeSelect(mode);
   assert(html.includes('id="route-field"')&&html.includes('id="route-explore"'));
   assert(html.includes('<select id="route-mode"')&&!/<option\b/.test(html),'The control starts without placeholder or disabled route modes');
   select.dataset={exploring:html.match(/data-exploring="([^"]+)"/)[1]};select.innerHTML='';pair=[from,to];preferred=mode;
   context.refreshRouteDialog();return select.value;
  },
  choose(mode){select.value=mode;assert.equal(select.value,mode,'Choose an actually visible route');preferred=select.value;context.refreshRouteDialog();},
  switchPair(from,to){pair=[from,to];context.refreshRouteDialog();return select.value;},
  worker(quotes){worker=freeze(clone(quotes));const input=worker,snapshot=JSON.stringify(input);baselines.push(()=>assert.equal(JSON.stringify(input),snapshot,'Worker quote data remain read-only'));context.refreshRouteDialog();return select.value;},
  refresh(){context.refreshRouteDialog();return select.value;},
  get build(){return lastBuild;},get applies(){return applies;},get refreshes(){return refreshes;}
 };
}

// One physical pass can be returned by three strategy aliases. Its UI has one
// plain shortest-duration option; detailed hazards belong to the estimate.
const single=harness(table('home','away',{fastest:pass,land:clone(pass),special:clone(pass)}));
single.mount();assert.equal(single.select.options.length,1);assert.equal(single.select.value,'fastest');
assert.equal(single.select.options[0].textContent,'最短日数 · 40日');
assert(!/阴平|陰平|子午谷|险道|險道/.test(single.select.innerHTML));
assert(!single.field.hidden&&single.unavailable.hidden&&single.explore.hidden);
assert.equal(single.build.quotes.fastest,single.input['home:away:fastest']);
assert.equal(single.build.result.options[0].quote,single.input['home:away:fastest'],'Group decoration keeps the original source quote reference');
single.choose('fastest');single.refresh();assert.equal(single.select.options.length,1);

// Genuine alternatives retain their different types and duration. A third
// available exploration quote is deliberately absent from normal options.
const multiple=harness(table('home','away',{fastest:mixed,land:alternate,explore:unknown}));
multiple.mount();assert.deepEqual(multiple.select.options.map(option=>option.value),['fastest','land']);
assert.deepEqual(multiple.select.options.map(option=>option.textContent),['最短日数（海陆并用） · 42日','陆路 · 57日']);
assert.deepEqual(multiple.select.options.map(option=>option.dataset.routeKind),['mixed','land']);
assert(!multiple.select.options.some(option=>option.value==='explore'));
assert(!multiple.explore.hidden);assert.equal(multiple.explore.getAttribute('aria-pressed'),'false');
multiple.choose('land');const beforeClick=multiple.refreshes;
multiple.explore.click();assert.equal(multiple.refreshes,beforeClick+1);
assert.equal(multiple.select.value,'explore');assert.deepEqual(multiple.select.options.map(option=>option.value),['explore']);
assert.equal(multiple.explore.getAttribute('aria-pressed'),'true');assert.equal(multiple.explore.textContent,'取消未知航路探索');
assert(multiple.select.options[0].textContent.includes('未知航路探索'));assert(!multiple.field.hidden);
multiple.refresh();assert.equal(multiple.select.value,'explore','Ordinary refresh preserves an explicitly entered exploration session');
multiple.explore.click();assert.notEqual(multiple.select.value,'explore');assert.equal(multiple.select.dataset.exploring,'false');
assert.deepEqual(multiple.select.options.map(option=>option.value),['fastest','land']);

// An explore-only destination does not silently turn a missing known path
// into an exploration order. The separate button is the required opt-in.
const only=harness({...table('home','away',{explore:unknown}),...table('home','other',{explore:unknown}),
 ...table('other','away',{explore:unknown})});
only.mount();assert.equal(only.select.value,'');assert.equal(only.select.options.length,0);
assert(only.field.hidden&&!only.unavailable.hidden&&!only.explore.hidden);
assert.equal(only.explore.getAttribute('aria-pressed'),'false');
only.refresh();assert.equal(only.select.value,'');
only.explore.click();assert.equal(only.select.value,'explore');assert(!only.field.hidden);
only.explore.click();assert.equal(only.select.value,'');assert(only.field.hidden);
only.explore.click();assert.equal(only.select.value,'explore');
only.switchPair('home','other');assert.equal(only.select.value,'');assert.equal(only.select.dataset.exploring,'false');
assert(only.field.hidden&&!only.explore.hidden,'Changing the target exits explicit exploration');
only.explore.click();only.switchPair('other','away');assert.equal(only.select.value,'');assert.equal(only.select.dataset.exploring,'false','Changing the source also resets explicit exploration');

// Worker hydration preserves a valid known selection, and cannot opt into
// exploration if that known selection later becomes unavailable.
const live=harness(table('home','away',{fastest:mixed,land:alternate,explore:unknown}));
live.mount();live.choose('land');assert.equal(live.select.value,'land');
live.worker(table('home','away',{land:clone(alternate),explore:clone(unknown),fastest:clone(mixed)}));
assert.equal(live.select.value,'land');assert.equal(live.build.result.options.find(option=>option.mode==='land').quote,live.build.quotes.land);
live.worker(table('home','away',{explore:unknown}));assert.equal(live.select.value,'');assert.equal(live.select.dataset.exploring,'false');
assert(live.field.hidden&&!live.explore.hidden);assert.equal(live.explore.getAttribute('aria-pressed'),'false');
live.explore.click();assert.equal(live.select.value,'explore');
live.worker(table('home','away',{fastest:direct,land:clone(direct)}));
assert.equal(live.select.value,'fastest');assert.equal(live.select.dataset.exploring,'false');assert(live.explore.hidden);
assert(!live.field.hidden&&live.unavailable.hidden,'Losing an exploration quote restores only available known routes');
live.worker({});assert.equal(live.select.value,'');assert(live.field.hidden&&!live.unavailable.hidden&&live.explore.hidden);
assert.equal(live.applies,live.refreshes,'Each regenerated option set is handed back to the active locale renderer');

// An existing mode alias may be replaced by its equivalent group value, but
// the control must still select the same real route rather than exploration.
const alias=harness(table('home','away',{fastest:mixed,land:alternate,explore:unknown}));
alias.mount();alias.choose('land');
alias.worker(table('home','away',{fastest:clone(alternate),land:alternate,explore:unknown}));
assert.equal(alias.select.options.length,1);assert.equal(alias.select.value,'fastest');assert.equal(alias.build.result.options[0].quote,alias.build.quotes.fastest);
assert.equal(alias.build.result.options[0].quote.days,57);assert.equal(alias.select.dataset.exploring,'false');

for(const check of baselines)check();
console.log('route controls: actual app helpers, one-route aliases, real alternatives, explicit exploration, target reset, Worker hydration, source references and immutable saves/RNG passed');
