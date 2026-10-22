'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const context={view:{catalog:{cities:[{position:[0,0]},{position:[20,20]},{position:[40,0]},{position:[50,50]}]}},mapPosition:c=>c.position};
vm.createContext(context);vm.runInContext(source.slice(source.indexOf('function smoothMapPath('),source.indexOf('const mapAccessKey=')),context);
const points=[[2,1],[10,5],[19,22],[30,5],[42,1]],before=JSON.stringify(points);
const d=context.landMapPath(points);
assert(d.startsWith('M0 0'));assert(d.includes('L20 20M20 20'),'An explicit city vertex is reached by the curve, not merely its control point');assert(d.endsWith('L40 0'));
assert.equal(context.landMapPath(points,{smooth:false}),'M0 0L10 5L20 20L30 5L40 0','Access roads follow their existing painted polylines');
assert.equal(context.landMapPath([[0,0],[40,40],[60,60]]),'M0 0Q40 40 50 50L60 60','Passing near a city does not insert a new junction');
assert.equal(JSON.stringify(points),before);assert.equal(context.landMapPath([]),'');
// Explicit endpoint IDs reach the named city even when the old display road
// starts beyond the small native-grid tolerance. Nearby unrelated vertices
// still cannot become junctions, and the input geometry is never rewritten.
context.view.catalog.cities=[{id:'from',position:[0,0]},{id:'to',position:[100,100]},
 {id:'nearby',position:[50,50]}];
const offset=[[12,8],[50,38],[89,94]],offsetBefore=JSON.stringify(offset);
assert.equal(context.landMapPath(offset,{smooth:false,from:'from',to:'to'}),'M0 0L50 38L100 100');
assert.equal(context.landMapPath(offset,{from:'from',to:'to'}),'M0 0Q50 38 75 69L100 100');
assert.equal(context.landMapPath(offset,{smooth:false}),'M12 8L50 38L89 94','An unrelated road is not redirected toward a nearby city');
assert.equal(JSON.stringify(offset),offsetBefore);
const approach=[[12,8],[30,20],[80,30]];
assert.equal(context.landMapPath(approach,{smooth:false,from:'from'}),'M0 0L30 20L80 30','A harbour endpoint stays a harbour when only the source city is named');
assert.equal(context.landMapPath(approach,{smooth:false,to:'to'}),'M12 8L30 20L100 100','A destination approach leaves its original port/start intact');
assert.equal(context.landMapPath(approach,{smooth:false,from:'missing'}),'M12 8L30 20L80 30','Unknown city IDs cannot fabricate a center');
// Preview scenarios supply their own board, rather than the live catalog's
// similarly named city positions. Legacy VM tests need not define preview.
context.setupPreview={map_cities:[{id:'from',position:[200,200]},{id:'to',position:[300,300]},
 {id:'via',position:[250,250]}]};
const previewPath=[[0,0],[249,248],[100,100]],previewBefore=JSON.stringify(previewPath);
assert.equal(context.landMapPath(previewPath,{from:'from',to:'to'}),'M200 200L250 250M250 250L300 300');
assert.equal(JSON.stringify(previewPath),previewBefore);context.setupPreview=null;

// Exercise the actual rendering loops with a previously drawn/deduplicated
// first approach. Anchoring uses original draw indices, not indices after a
// filter that would mistake the next port or shared junction for a city.
const part=(points,mode='land',skip=false)=>({points,mode,skip}),draws={
 single:{from:'a',to:'b',draw:[part([[11,11],[91,91]])]},
 sea:{from:'a',to:'b',draw:[part([[11,11],[20,20]],'land',true),part([[20,20],[80,80]],'sea'),part([[80,80],[91,91]])]},
 region:{from:'a',to:'b',draw:[part([[11,11],[50,50]],'land',true),part([[50,50],[91,91]])]}
};
function renderCalls(start,end,extra){
 const calls=[],ctx={preview:null,hazardous:true,activeIds:new Set(['a','b']),
  view:{catalog:{world:{},map_presentation:{expansion_connections:[],added_land_roads:[]},sea_routes:[],regional_roads:[]}},
  firstAccess:p=>!p.skip,escapeHtml:String,smoothMapPath:()=> 'SEA',
  landMapPath:(points,options)=>{calls.push({points,options});return 'LAND';},...extra};
 const at=source.indexOf(start),until=source.indexOf(end,at);assert(at>=0&&until>at);
 vm.createContext(ctx);vm.runInContext(source.slice(at,until),ctx);return calls.map(row=>JSON.parse(JSON.stringify(row)));
}
let calls=renderCalls(' const expansionRoads=',' const seaRoutes=',{view:{catalog:{world:{},map_presentation:{expansion_connections:[draws.single,draws.sea]}}}});
assert.equal(calls.length,2);assert.deepEqual(calls[0].options,{smooth:false,from:'a',to:'b'});assert.deepEqual(calls[1].options,{smooth:false,from:null,to:'b'});
assert.deepEqual(calls[1].points,[[80,80],[91,91]],'The final original approach remains the destination approach');
calls=renderCalls(' const navigableSeas=',' const regionalRoads=',{seaRoutes:[draws.sea],seaPairs:new Set(),discoveredIds:new Set()});
assert.equal(calls.length,1);assert.deepEqual(calls[0].options,{smooth:false,from:null,to:'b'});
const completeSea={...draws.sea,draw:draws.sea.draw.map(p=>({...p,skip:false}))};
calls=renderCalls(' const navigableSeas=',' const regionalRoads=',{seaRoutes:[completeSea],seaPairs:new Set(),discoveredIds:new Set()});
assert.equal(calls.length,2);assert.deepEqual(calls[0].options,{smooth:false,from:'a',to:null});assert.deepEqual(calls[1].options,{smooth:false,from:null,to:'b'});
calls=renderCalls(' const regionalRoads=',' const offsets=',{preview:{regional_roads:[draws.region]}});
assert.equal(calls.length,1);assert.deepEqual(calls[0].options,{from:null,to:'b'},'The shared mountain junction is never replaced by the source city');
const yinping={from:'yinping',to:'shujun',new_branch:[[244,448],[214,502]]};
calls=renderCalls(' const roads=',' const drawnAccess=',{extras:[['yinping','shujun']],view:{catalog:{map_presentation:{added_land_roads:[yinping]}}}});
assert.deepEqual(calls[0].options,{to:'shujun'},'The Yinping branch starts at a shared junction, not at Yinping itself');
// A presentation-only background alias updates both rendered image layers
// without rewriting the world object or changing the camera's identity key.
const world=Object.freeze({x:0,y:0,width:1352,height:1024,background:'/assets/map-navigation.png'}),worldBefore=JSON.stringify(world);
assert.equal(context.mapBackgroundHref(world.background),world.background,'Absent presentation metadata keeps the existing image');
context.view.catalog.map_presentation={road_center_corrections:{backgrounds:{'/assets/map-navigation.png':'/assets/map-road-centers.png'}}};
assert.equal(context.mapBackgroundHref(world.background),'/assets/map-road-centers.png');
assert.equal(context.mapBackgroundHref('/assets/map-basin.png'),'/assets/map-basin.png');
const cameraContext={preview:null,view:{catalog:{world}},mapBackgroundHref:context.mapBackgroundHref};
vm.createContext(cameraContext);
const worldStart=source.indexOf(' const world='),worldEnd=source.indexOf(' if(mapNavigation)',worldStart);
vm.runInContext(source.slice(worldStart,worldEnd)+'\nglobalThis.renderedWorld={world,backgroundHref,cameraKey};',cameraContext);
assert.equal(cameraContext.renderedWorld.backgroundHref,'/assets/map-road-centers.png');
assert.equal(cameraContext.renderedWorld.cameraKey,'0:0:1352:1024:/assets/map-navigation.png');
assert.equal(cameraContext.renderedWorld.world,world);assert.equal(JSON.stringify(world),worldBefore);
assert.equal((source.match(/<image href="\$\{backgroundHref\}"/g)||[]).length,2,'Base map and mountain recolor layer use the same corrected image');
assert(!source.includes('<image href="${world.background}"'));

// Existing owned castles need their outline above roads just as new castles
// do. Relying on the background outline lets dynamic center-bound paths
// paint across their black edge. Both masks keep the same native geometry.
const castleContext={active:[{id:'old',position:[100,200]},{id:'empty',position:[300,400]}],
 owners:{old:'wei',empty:'neutral'},mapPosition:c=>c.position,mapColor:id=>id==='neutral'?'#ffffff':'#0088ff',
 focused:null,preview:null,mapAction:null,cityCaption:id=>id,ownerName:id=>id,escapeHtml:String};
vm.createContext(castleContext);
const castleStart=source.indexOf(' const castles=active.map('),castleEnd=source.indexOf(' const extras=',castleStart);
assert(castleStart>=0&&castleEnd>castleStart);
vm.runInContext(source.slice(castleStart,castleEnd)+'\nglobalThis.renderedCastles=castles;',castleContext);
const rendered=castleContext.renderedCastles;
assert.equal((rendered.match(/class="castle-border"/g)||[]).length,2,'Every city redraws its full outline above roads');
assert(rendered.includes('href="#castle-outline-pixels" x="100" y="200" fill="#000"'));
assert(rendered.includes('href="#castle-outline-pixels" x="300" y="400" fill="#fff"'),'Unowned borders remain pure white');
assert(rendered.includes('href="#castle-fill-pixels" x="300" y="400" fill="#ffffff"'));
assert(source.includes('${roads}${expansionRoads}${regionalRoads}${navigableSeas}${bridges}${castles}${labels}'),'All road layers precede complete castle sprites');
console.log('road paths: semantic endpoints, preview board, native-grid junctions, untouched ports/bypasses/inputs, original draw indices, Yinping junction and presentation-only background alias and complete castles above every road layer passed');
