'use strict';
const assert=require('node:assert/strict'),{create}=require('../game/view-cache.js');
const token='a'.repeat(64),cache=create();
const fixed={scenario_id:'same',scenarios:[{id:'same'}],library:[{id:1,name:'諸葛亮',virtue:99},{id:2,name:'劉備',virtue:99}]};
const view={revision:1,game:{turn:1},catalog:{names:{1:'諸葛亮'},library:[{id:1,alive:true,faction:'shu',year_state:'available',location:null},{id:2,alive:false,faction:null,year_state:'retired',location:null}]}};
const first=cache.hydrate({transport:'tk2-view-v1',catalog_token:token,static_catalog:fixed,view});
assert.equal(first.catalog.library[0].name,'諸葛亮');assert.equal(first.catalog.library[1].alive,false);
assert.equal(cache.token(),token);assert.equal(first.catalog.scenarios,fixed.scenarios,'Static data reuses its tab-local identity');
const second=cache.hydrate({transport:'tk2-view-v1',catalog_token:token,view:{...view,revision:2,catalog:{...view.catalog,library:view.catalog.library.map(p=>({...p,faction:'wei'}))}}});
assert.equal(second.catalog.library[0].faction,'wei');assert.equal(first.catalog.library[0].faction,'shu');
assert.equal(second.catalog.library[0].virtue,99);assert.equal(second.catalog.scenarios,first.catalog.scenarios);
assert.deepEqual(cache.hydrate({error:'stale'}),{error:'stale'});assert.equal(cache.hydrate(null),null);
assert.throws(()=>cache.hydrate({transport:'tk2-view-v1',catalog_token:'bad',view}));
assert.throws(()=>cache.hydrate({transport:'tk2-view-v1',catalog_token:'b'.repeat(64),view}));
assert.equal(cache.token(),token,'Rejected packets cannot advance the current token');
const dup={...view,catalog:{library:[view.catalog.library[0],view.catalog.library[0]]}};
assert.throws(()=>cache.hydrate({transport:'tk2-view-v1',catalog_token:token,view:dup}));
cache.clear();assert.equal(cache.token(),'');assert.throws(()=>cache.hydrate({transport:'tk2-view-v1',catalog_token:token,view}));
// Quote-aware packets reconstruct the same full view without retaining stale
// routes, and failed validation cannot advance or poison either cache.
const routes={xiangyang:{nanyang:{days:4,mode:'land',distance_km:120}}},quote='1'.repeat(64),routeAware=create();
const state={...view,game:{turn:1,month:11,day:1,phase:'player',player:'shu',cities:{xiangyang:{owner:'shu',gold:200}},officers:{1:{troops:300}}},catalog:{...view.catalog,travel_quotes:routes}};
const packet=(catalogToken,routeToken,nextView,staticCatalog)=>({transport:'tk2-view-v1',catalog_token:catalogToken,quote_token:routeToken,view:nextView,...(staticCatalog?{static_catalog:staticCatalog}:{})});
const expected=(staticCatalog,dynamic,travel)=>({...dynamic,catalog:{...staticCatalog,...dynamic.catalog,library:dynamic.catalog.library.map(person=>({...staticCatalog.library.find(base=>base.id===person.id),...person})),travel_quotes:travel}});
const initialFull=routeAware.hydrate(packet(token,quote,state,fixed));assert.deepEqual(initialFull,expected(fixed,state,routes));assert.equal(routeAware.token(),token+':'+quote);
const updated={...state,revision:2,game:{...state.game,day:21,phase:'ai',cities:{xiangyang:{owner:'shu',gold:25}},officers:{1:{troops:999}}},catalog:{...state.catalog}};delete updated.catalog.travel_quotes;
const withReusedQuotes=routeAware.hydrate(packet(token,quote,updated));assert.deepEqual(withReusedQuotes,expected(fixed,updated,routes));assert.equal(withReusedQuotes.catalog.travel_quotes,routes,'unchanged route context reuses the existing quotes');assert.equal(initialFull.game.day,1,'hydration preserves earlier views');
for(const badQuote of ['wrong',42,null]){
 assert.throws(()=>routeAware.hydrate(packet(token,badQuote,updated)),/route token/);assert.equal(routeAware.token(),token+':'+quote);
}
const otherToken='b'.repeat(64),otherQuote='2'.repeat(64),otherFixed={...fixed,scenario_id:'other',title:'別のシナリオ'};
assert.throws(()=>routeAware.hydrate(packet(otherToken,otherQuote,updated,otherFixed)),/Missing route quotes/,'a new quote context needs actual quotes');
assert.equal(routeAware.token(),token+':'+quote);
assert.throws(()=>routeAware.hydrate(packet(otherToken,quote,state)),/Missing view catalog/,'failed quote validation cannot install the new static catalog');
assert.throws(()=>routeAware.hydrate(packet(token,otherQuote,updated)),/Missing route quotes/,'an unknown quote token cannot reuse old quotes');
assert.equal(routeAware.token(),token+':'+quote);
const invalidRoutes={...state,catalog:{...state.catalog,travel_quotes:[]}};
assert.throws(()=>routeAware.hydrate(packet(token,otherQuote,invalidRoutes)),/Invalid route quotes/);assert.equal(routeAware.token(),token+':'+quote);
assert.equal(routeAware.hydrate(packet(token,quote,updated)).catalog.travel_quotes,routes,'failed packets leave the previous quote cache usable');
const newRoutes={xiangyang:{nanyang:{days:6,mode:'sea'}}},otherView={...state,catalog:{...state.catalog,travel_quotes:newRoutes}};
const switched=routeAware.hydrate(packet(otherToken,otherQuote,otherView,otherFixed));assert.deepEqual(switched,expected(otherFixed,otherView,newRoutes));assert.equal(routeAware.token(),otherToken+':'+otherQuote);assert.equal(switched.catalog.travel_quotes,newRoutes);
assert.throws(()=>routeAware.hydrate(packet(token,quote,updated)),/Missing route quotes/,'switching back must not use another scenario’s quote context');assert.equal(routeAware.token(),otherToken+':'+otherQuote);
const back=routeAware.hydrate(packet(token,quote,state,fixed));assert.deepEqual(back,expected(fixed,state,routes));
// Metadata remains a two-catalog LRU, independent of the single current route
// context. An evicted tab cache is recoverable by a full server packet.
routeAware.hydrate(packet(otherToken,otherQuote,otherView,otherFixed));
const thirdToken='c'.repeat(64),thirdQuote='3'.repeat(64),thirdFixed={...fixed,scenario_id:'third'};
routeAware.hydrate(packet(thirdToken,thirdQuote,state,thirdFixed));
assert.throws(()=>routeAware.hydrate(packet(token,quote,state)),/Missing view catalog/);assert.equal(routeAware.token(),thirdToken+':'+thirdQuote);
const recovered=routeAware.hydrate(packet(token,quote,state,fixed));assert.deepEqual(recovered,expected(fixed,state,routes));
routeAware.clear();assert.equal(routeAware.token(),'');
assert.throws(()=>routeAware.hydrate(packet(token,quote,updated,fixed)),/Missing route quotes/,'clearing the cache also forgets all route quotes');assert.equal(routeAware.token(),'');
assert.throws(()=>routeAware.hydrate(packet(token,quote,state)),/Missing view catalog/,'a rejected partial restoration does not install metadata');
assert.deepEqual(routeAware.hydrate(packet(token,quote,state,fixed)),expected(fixed,state,routes));
console.log('View cache: full hydration, immutable metadata/LRU, quote-context reuse, scenario switching, atomic malformed/missing-cache rejection and full recovery passed');
