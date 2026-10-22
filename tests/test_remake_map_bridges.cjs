'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {findWaterRuns,bridgePath}=require('../game/build_map_bridges.cjs');
const sample=(start,end,step=.5)=>Array.from({length:41},(_,i)=>({x:i*step,y:8,water:i*step>=start&&i*step<=end}));
const source=sample(7,11),snapshot=JSON.stringify(source),run=findWaterRuns(source);
assert.equal(run.length,1);assert.equal(run[0].water_length,4.5);assert.deepEqual(run[0].points[0],[5.5,8]);assert.deepEqual(run[0].points.at(-1),[12.5,8]);
assert.equal(bridgePath(run[0].points),'M5.5 8L12.5 8');assert.equal(JSON.stringify(source),snapshot);
assert.deepEqual(findWaterRuns(sample(0,11)),[],'A path starting at a harbour does not bridge the sea');
assert.deepEqual(findWaterRuns(sample(7,20)),[],'A path ending at a harbour does not bridge the sea');
assert.deepEqual(findWaterRuns(sample(7,7)),[],'One isolated blue sample is not a river crossing');
const two=sample(3,6);two.forEach(p=>{p.water ||= p.x>=13&&p.x<=16;});assert.equal(findWaterRuns(two).length,2);
const curve=source.map(p=>({...p,y:p.x*p.x/100}));const curved=findWaterRuns(curve)[0];
assert(bridgePath(curved.points).split('L').length>2,'A bridge follows its actual curved road across water');

const app=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const context={view:{catalog:{map_presentation:{road_bridges:{baked:['b1'],bridges:{b1:{d:'M1 2L4 5'},b2:{d:'M6 7L8 9'}},by_path:{LAND:['b1','b2'],SEA:['b2']},style:[{stroke:'#51371e',width:5.4},{stroke:'#e9bf7a',width:2.8}]}}}},escapeHtml:String};
vm.createContext(context);const start=app.indexOf('function mapBridgeLayer('),end=app.indexOf('const mapAccessKey=',start);vm.runInContext(app.slice(start,end),context);
let html=context.mapBridgeLayer(['<path class="road-underlay" d="LAND"/><path class="road-line" d="LAND"/>','<path class="road-underlay" d="LAND"/>']);
assert.equal((html.match(/data-river-bridge="b1"/g)||[]).length,1,'A shared baked/dynamic bridge draws once');
assert.equal((html.match(/data-river-bridge="b2"/g)||[]).length,1);assert(html.includes('stroke="#51371e" stroke-width="5.4"'));assert(html.includes('stroke="#e9bf7a" stroke-width="2.8"'));
assert(!context.mapBridgeLayer(['<path class="coastal-lane" d="SEA"/>']).includes('data-river-bridge="b2"'),'Sea-lane geometry never requests a bridge');
assert(!context.mapBridgeLayer([]).includes('data-river-bridge="b2"'),'An inactive dynamic road does not show its bridge');
context.view.catalog.map_presentation={};assert.equal(context.mapBridgeLayer([]),'','Absent optional metadata retains legacy display');
assert(app.includes('${regionalRoads}${navigableSeas}${bridges}${castles}${labels}'),'Every bridge remains below complete castle sprites');
const metadata=require('node:path').resolve(__dirname,'../game/assets/map-bridges.json');
if(fs.existsSync(metadata)){
 const data=JSON.parse(fs.readFileSync(metadata));assert.equal(data.schema,'tk2-map-bridges-v1');assert.deepEqual(data.world,[0,0,1352,1024]);
 for(const id of data.baked)assert(data.bridges[id]);for(const ids of Object.values(data.by_path))for(const id of ids)assert(data.bridges[id]);
 assert(data.audit.route_bridges['bajun:zangke']?.length>0,'Zangke–Jiangzhou river crossing has a bridge');
 assert(data.audit.route_bridges['fuling:zangke']?.length>0,'Zangke–Fuling river crossing has a bridge');
 assert(data.audit.baked_bridges>0);assert(data.audit.dynamic_bridge_paths>0);
}
console.log('map bridges: exact water runs/banks, curved paths, harbour exclusions, shared crossings, native bridge style, active land roads and castles above bridges passed');
