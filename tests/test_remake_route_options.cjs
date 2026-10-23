/* Known routes stay concise; unknown sea travel always needs explicit intent. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const routes=require('../game/route-options.js');
const leg=(id,from='a',to='b',mode='land',extra={})=>({id,from,to,mode,...extra});
const quote=(legs,{days=10,distance=300,path:cityPath=['a','b'],modes=[...new Set(legs.map(row=>row.mode))]}={})=>({path:cityPath,routes:legs,days,distance_km:distance,modes});
const plain=quote([leg('road')]),pass=quote([leg('pass','a','b','land',{special:'ziwu'})],{days:15}),sea=quote([leg('sea','a','b','sea',{sea_km:300,land_km:0})],{days:8}),unknown=quote([leg('explore:a:b','a','b','sea',{sea_km:350,land_km:0})],{days:20});
const copy=value=>JSON.parse(JSON.stringify(value));
const modes=options=>options.map(row=>row.mode);
// Mode aliases describe one physical path, not multiple choices. Preferred
// aliases select that group's canonical mode; input insertion order is ignored.
let result=routes.build({land:copy(plain),fastest:plain},{preferred:'land'});
assert.equal(result.options.length,1);assert.equal(result.value,'fastest');assert.deepEqual(result.options[0].aliases,['fastest','land']);assert.equal(result.knownCount,1);assert.equal(result.options[0].quote,plain);assert.equal(result.options[0].kind,'land');assert.equal(result.options[0].indexWithinKind,1);assert.equal(result.options[0].kindCount,1);assert(result.options[0].shortest);
// Independent land routes remain distinct even when endpoints/city paths match.
result=routes.build({fastest:plain,land:copy(plain),special:pass});
assert.deepEqual(modes(result.options),['fastest','special']);assert.deepEqual(result.options.map(row=>[row.kind,row.indexWithinKind,row.kindCount,row.shortest]),[['land',1,2,true],['land',2,2,false]]);
assert.equal(routes.build({fastest:plain,special:pass},{preferred:'special'}).value,'special');
// Alternatives sort by duration, distance, then fixed canonical mode order.
result=routes.build({land:plain,fastest:sea,sea:copy(sea),special:pass});
assert.deepEqual(modes(result.options),['fastest','land','special']);assert.deepEqual(result.options[0].aliases,['fastest','sea']);assert.equal(result.options[0].kind,'sea');assert.equal(result.options[0].kindCount,1);assert.equal(result.knownCount,3);assert.equal(routes.build({fastest:sea,sea:copy(sea),land:plain},{preferred:'sea'}).value,'fastest');
result=routes.build({land:quote([leg('long')],{days:10,distance:400}),fastest:plain,special:quote([leg('short')],{days:10,distance:200})});
assert.deepEqual(modes(result.options),['special','fastest','land']);assert(result.options.every(row=>row.shortest));
result=routes.build({sea:quote([leg('tie-sea','a','b','sea')]),special:quote([leg('tie-pass')]),land:quote([leg('tie-road')]),fastest:quote([leg('tie-fast')])});
assert.deepEqual(modes(result.options),['fastest','land','special','sea']);
// A sea leg can itself include a land approach. Its modes array remains ['sea']
// in real quotes, so classification must inspect the leg's land/sea distances.
const shore=quote([leg('shore','a','b','sea',{land_km:40,sea_km:260})]);
result=routes.build({fastest:shore,sea:copy(shore)});assert.equal(result.options[0].kind,'mixed');
const combined=quote([leg('road','a','c'),leg('water','c','b','sea')],{path:['a','c','b']});
assert.equal(routes.build({fastest:combined}).options[0].kind,'mixed');
// Inland navigation is a separate physical option. Land approaches do not
// label a river as an ocean voyage or apply a sea-only presentation warning.
const riverLeg=leg('river','a','b','river',{land_km:20,sea_km:0,river_km:280,flow:'upstream',
 river_segments:[{river:'yangtze',direction:'upstream',distance_km:180,speed_km_per_day:30},
  {river:'xiang',direction:'upstream',distance_km:100,speed_km_per_day:30}]});
const river=quote([riverLeg],{days:11});river.river_km=280;
result=routes.build({fastest:plain,land:copy(plain),river});
assert.deepEqual(modes(result.options),['fastest','river']);assert.equal(result.knownCount,2);
assert.deepEqual(result.options.map(row=>[row.kind,row.indexWithinKind,row.kindCount]),[['land',1,1],['river',1,1]]);
result=routes.build({fastest:river,river:copy(river),land:plain},{preferred:'river'});
assert.equal(result.knownCount,2);assert.equal(result.value,'fastest');assert.deepEqual(result.options[1].aliases,['fastest','river']);
assert.equal(result.options[1].kind,'river');assert.equal(result.options[1].shortest,false);
assert.equal(routes.build({river}).value,'river');
const riverRoad=quote([leg('road','a','c'),{...riverLeg,from:'c'}],{path:['a','c','b']});
assert.equal(routes.build({fastest:riverRoad}).options[0].kind,'river');
const riverSea=quote([riverLeg,leg('ocean','b','c','sea',{sea_km:200})],{path:['a','b','c']});
result=routes.build({fastest:riverSea,river:copy(riverSea)});
assert.equal(result.options[0].kind,'river_sea');assert.equal(result.options[0].kindCount,1);assert.equal(result.options[0].indexWithinKind,1);
assert.equal(routes.build({river:quote([],{modes:['river']})}).options[0].kind,'river');
// The same route IDs and rounded total days cannot erase flow direction or
// segment speed differences. Object key order remains presentation-neutral.
const reorderedRiver=copy(river);
reorderedRiver.routes[0].river_segments=reorderedRiver.routes[0].river_segments.map(s=>({speed_km_per_day:s.speed_km_per_day,distance_km:s.distance_km,direction:s.direction,river:s.river}));
assert.equal(routes.build({fastest:river,river:reorderedRiver}).knownCount,1);
for(const edit of [
 q=>{q.routes[0].flow='downstream';},q=>{q.routes[0].river_km+=1;},
 q=>{q.routes[0].river_segments[0].direction='downstream';},q=>{q.routes[0].river_segments[0].speed_km_per_day=60;},
 q=>{q.routes[0].river_segments.reverse();},q=>{q.river_km+=1;}
]){const changed=copy(river);edit(changed);assert.equal(routes.build({fastest:river,river:changed}).knownCount,2);}
const secondRiver=copy(river);secondRiver.routes[0].id='second-river';
result=routes.build({fastest:river,river:secondRiver});
assert.deepEqual(result.options.map(row=>[row.kind,row.indexWithinKind,row.kindCount]),[['river',1,2],['river',2,2]]);
// Direction, ordered legs, route IDs, mode, special treatment and city path all
// contribute to identity; coincident city centers cannot erase a real option.
const variants=[
 quote([leg('other')]),quote([leg('road','b','a')]),quote([leg('road','a','b','sea')]),
 quote([leg('road','a','b','land',{special:'yinping'})]),quote([leg('road')],{path:['a','c','b']})
];
for(const alternative of variants)assert.equal(routes.build({fastest:plain,land:alternative}).knownCount,2);
const ordered=[leg('one','a','c'),leg('two','c','b')];
assert.equal(routes.build({fastest:quote(ordered),land:quote([...ordered].reverse())}).knownCount,2);
// Shared IDs and a shared path cannot hide different costs or settlement risk.
// Decorative geometry is irrelevant; nested hazard keys are canonicalized.
const riskA={kind:'storm',loss:{minimum:80,maximum:90},seasons:[7,8,9]},riskB={seasons:[7,8,9],loss:{maximum:90,minimum:80},kind:'storm'};
const hazardRoad=quote([leg('risky','a','b','land',{hazard:riskA,draw:{points:[[1,2],[3,4]],color:'tan'}})]);
const reorderRoad=quote([leg('risky','a','b','land',{hazard:riskB,draw:{color:'tan',points:[[1,2],[3,4]]},geo:{lng:1,lat:2},history:{label:'decorative'}})]);
assert.equal(routes.build({fastest:hazardRoad,land:reorderRoad}).knownCount,1,'Object key order and presentation metadata do not create routes');
const changedHazard=copy(hazardRoad);changedHazard.routes[0].hazard.loss.maximum=95;
assert.equal(routes.build({fastest:hazardRoad,land:changedHazard}).knownCount,2);
for(const field of ['terrain','days','distance_km','land_km','sea_km','river_km','base_days']){
 const changed=copy(plain);changed.routes[0][field]=field==='terrain'?'mountain':12;
 assert.equal(routes.build({fastest:plain,land:changed}).knownCount,2,`Different leg ${field} remains distinct`);
}
for(const field of ['days','turns','distance_km','grain_per_officer']){
 const changed=copy(plain);changed[field]=(plain[field]||0)+5;
 assert.equal(routes.build({fastest:plain,land:changed}).knownCount,2,`Different quote ${field} remains distinct`);
}
// Unknown sea paths cannot leak into normal options or be selected by a stale
// preference. Entering and leaving exploration is explicit presentation state.
result=routes.build({fastest:plain,explore:unknown},{preferred:'explore'});assert.deepEqual(modes(result.options),['fastest']);assert.equal(result.value,'fastest');assert.equal(result.canExplore,true);assert.equal(result.exploring,false);
result=routes.build({fastest:plain,land:copy(plain),explore:unknown},{exploring:true});assert.deepEqual(modes(result.options),['explore']);assert.equal(result.value,'explore');assert.equal(result.knownCount,1);assert.equal(result.exploring,true);assert.equal(result.options[0].kind,'sea');assert.deepEqual(result.options[0].aliases,['explore']);
result=routes.build({fastest:plain,explore:unknown},{preferred:'explore',exploring:false});assert.equal(result.value,'fastest');assert.equal(result.exploring,false);
result=routes.build({fastest:plain},{preferred:'explore',exploring:true});assert.equal(result.value,'fastest');assert.equal(result.canExplore,false);assert.equal(result.exploring,false);
result=routes.build({explore:unknown});assert.deepEqual(result.options,[]);assert.equal(result.value,'');assert.equal(result.knownCount,0);assert(result.canExplore);assert(!result.exploring);
result=routes.build({explore:unknown},{exploring:true});assert.deepEqual(modes(result.options),['explore']);assert.equal(result.knownCount,0);assert(result.exploring);
assert.deepEqual(routes.build({explore:unknown},{exploring:'true'}).options,[],'Truthy non-boolean values never authorize exploration');
result=routes.build({}, {exploring:true});assert.deepEqual(result,{options:[],value:'',knownCount:0,canExplore:false,exploring:false});
assert.deepEqual(routes.build({fastest:null,land:undefined,sea:false,explore:null}),result);
// Building choices has no campaign/RNG references and never mutates any input.
function freeze(value){if(value&&typeof value==='object'){Object.freeze(value);for(const item of Object.values(value))freeze(item);}return value;}
const inputs=freeze({fastest:copy(plain),land:copy(plain),special:copy(pass),sea:copy(sea),explore:copy(unknown)}),before=JSON.stringify(inputs);
routes.build(inputs,{preferred:'land'});routes.build(inputs,{exploring:true});assert.equal(JSON.stringify(inputs),before);
const first=routes.build(inputs),second=routes.build(inputs);first.options[0].aliases.push('made-up');assert(!second.options[0].aliases.includes('made-up'));
// The same small module serves a browser global and the Node unit tests.
const browser={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../game/route-options.js'),'utf8'),browser);assert.deepEqual(Array.from(browser.window.GameRouteOptions.build({fastest:plain}).options,row=>row.mode),['fastest']);assert(Object.isFrozen(routes));
console.log('route choices: physical-path aliases, independent alternatives, directed identity, route kinds, stable sorting, explicit exploration, fallback and immutable browser/Node interface passed');
