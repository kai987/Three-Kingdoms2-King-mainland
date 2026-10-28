'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {shortest,reversePath,splitAtCityVertices,partitionCityPieces,shortestVia,renderSourceHash}=require('../game/build_route_geometry.cjs');
const graph=new Map([
 ['a',[{to:'b',length:1,tag:'ab'},{to:'x',length:2,tag:'ax'}]],
 ['b',[{to:'c',length:1,tag:'bc'}]],['x',[{to:'c',length:2,tag:'xc'}]],['c',[]]
]);
assert.equal(shortest(graph,'a','c').length,2);
assert.deepEqual(shortest(graph,'a','c',new Set(['b'])).edges.map(e=>e.tag),['ax','xc'],'Existing road search avoids a third city when a legal junction-only path exists');
assert.equal(shortest(graph,'a','c',new Set(['b','x'])),null,'Unreachable paths are reported rather than replaced by a straight line');
assert.deepEqual(shortestVia(graph,['a','x','c']).edges.map(e=>e.tag),['ax','xc'],'A reviewed corridor uses actual existing road junctions instead of another shorter corridor');
assert.equal(shortestVia(graph,['a','b','x','c']),null,'An unreachable reviewed corridor fails closed');
assert.throws(()=>shortestVia(graph,['a','missing','c']),/Invalid reviewed/);
assert.throws(()=>shortestVia(graph,['a','b','a','c']),/Invalid reviewed/);
assert.equal(reversePath('M1 2L3 4Q5 6 7 8L9 10'),'M9 10L7 8Q5 6 3 4L1 2');
assert.equal(reversePath(reversePath('M1 2L3 4Q5 6 7 8L9 10')),'M1 2L3 4Q5 6 7 8L9 10');
assert.throws(()=>reversePath('M0 0C1 2 3 4 5 6'),/Unsupported/);
const cities=new Set(['3,4','9,10']);
assert.deepEqual(splitAtCityVertices('M1 2L3 4Q5 6 7 8L9 10L11 12',cities),['M1 2L3 4','M3 4Q5 6 7 8L9 10','M9 10L11 12']);
assert.deepEqual(splitAtCityVertices('M1 2Q3 4 7 8',cities),['M1 2Q3 4 7 8'],'A city used only as a curve control point is not an actual transit');
assert.throws(()=>splitAtCityVertices('M0 0C1 2 3 4 5 6',cities),/Unsupported/);
const transitPieces=[{d:'ab',reverse:false},{d:'bc',reverse:true},{d:'cd',reverse:false}];
const transitMeasures=new Map([['ab',{start:[0,0],end:[1,0]}],['bc',{start:[2,0],end:[1,0]}],['cd',{start:[2,0],end:[3,0]}]]);
assert.deepEqual(partitionCityPieces('a','d',transitPieces,transitMeasures,new Map([['0,0','a'],['1,0','b'],['3,0','d']])).map(s=>({from:s.from,to:s.to,pieces:s.pieces.map(p=>p.d)})),[{from:'a',to:'b',pieces:['ab']},{from:'b',to:'d',pieces:['bc','cd']}]);
assert.throws(()=>partitionCityPieces('a','missing',transitPieces,transitMeasures,new Map([['0,0','a'],['1,0','b'],['3,0','d']])),/does not terminate/);
const root=path.resolve(__dirname,'..'),file=path.join(root,'game/config/route-geometry.json');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const appSource='game/app.js',compilerSource='game/build_route_geometry.cjs';
function rendererProjection(source){
 const text=source.toString('utf8'),start='function smoothMapPath(',end='function mapBackgroundHref(';
 assert.equal(text.split(start).length,2,'unique start of compiler-extracted renderer');
 assert.equal(text.split(end).length,2,'unique end of compiler-extracted renderer');
 assert(text.indexOf(start)<text.indexOf(end),'ordered renderer projection bounds');
 return Buffer.from(text.slice(text.indexOf(start),text.indexOf(end)),'utf8');
}
function validateSource(name,source,expected,sources,attestation){
 if(sha(source)===expected)return;
 assert.equal(name,appSource,name+': full source pin remains required');
 assert.deepEqual(Object.keys(attestation).sort(),['schema','source','original_source_sha256','compiler','compiler_sha256','start','end','projection_sha256','projection_bytes','baseline_commit'].sort());
 assert.equal(attestation.schema,'tk2-route-render-source-v1');
 assert.equal(attestation.source,appSource);assert.equal(attestation.compiler,compilerSource);
 assert.equal(attestation.original_source_sha256,expected,'attestation belongs to the frozen original source');
 assert.equal(attestation.compiler_sha256,sources[compilerSource],'the exact compiler still determines the projected range');
 assert.match(expected,/^[a-f0-9]{64}$/);assert.match(attestation.compiler_sha256,/^[a-f0-9]{64}$/);
 assert.equal(attestation.start,'function smoothMapPath(');assert.equal(attestation.end,'function mapBackgroundHref(');
 assert.match(attestation.baseline_commit,/^[a-f0-9]{40}$/);
 assert.match(attestation.projection_sha256,/^[a-f0-9]{64}$/);
 assert(Number.isSafeInteger(attestation.projection_bytes)&&attestation.projection_bytes>0);
 const projection=rendererProjection(source);
 assert.equal(projection.length,attestation.projection_bytes,'the complete extracted input is unchanged');
 assert.equal(sha(projection),attestation.projection_sha256,'every compiler-extracted renderer byte is unchanged');
}
if(fs.existsSync(file)){
 const compiled=JSON.parse(fs.readFileSync(file));
 const attestation=JSON.parse(fs.readFileSync(path.join(root,'game/config/route-render-source.json')));
 for(const [name,hash]of Object.entries(compiled.sources))validateSource(name,fs.readFileSync(path.join(root,name)),hash,compiled.sources,attestation);
 const app=fs.readFileSync(path.join(root,appSource)),pin=compiled.sources[appSource];
 const compiler=fs.readFileSync(path.join(root,compilerSource));
 assert.equal(renderSourceHash(Buffer.concat([Buffer.from('// Display-only metadata.\n'),app]),compiler,attestation),pin,'A scenario rebuild retains the attested unchanged renderer');
 assert.equal(renderSourceHash(app,Buffer.concat([compiler,Buffer.from('// compiler changed')]),attestation),sha(app),'Compiler drift requires a new full source pin');
 const changedRenderer=Buffer.from(app.toString().replace('return d+`L','return d +`L'));
 assert.equal(renderSourceHash(changedRenderer,compiler,attestation),sha(changedRenderer),'Renderer drift never reuses the previous projection');
 assert.doesNotThrow(()=>validateSource(appSource,Buffer.concat([Buffer.from('// Display-only metadata.\n'),app]),pin,compiled.sources,attestation),'unrelated UI changes do not rewrite campaign hashes');
 assert.throws(()=>validateSource(appSource,Buffer.from(app.toString().replace('return d+`L','return d +`L')),pin,compiled.sources,attestation),'even whitespace changes inside path functions require rebuilding geometry');
 assert.throws(()=>validateSource(appSource,Buffer.concat([Buffer.from('// Display-only metadata.\n'),app]),pin,compiled.sources,{...attestation,original_source_sha256:'0'.repeat(64)}),'an attestation cannot substitute a different baseline');
 assert.throws(()=>validateSource(compilerSource,Buffer.from('// compiler changed'),compiled.sources[compilerSource],compiled.sources,attestation),'compiler changes retain full-file validation');
 const catalog=JSON.parse(fs.readFileSync(path.join(root,'game/data/campaigns/217-07.json'))),declared=[...catalog.travel_routes,...catalog.exploration_routes],byId=new Map(declared.map(route=>[route.id,route]));
 assert.equal(compiled.schema,'tk2-route-geometry-v1');assert.equal(compiled.audit.input_routes,declared.length);assert.equal(compiled.audit.compiled_routes,declared.length);assert.deepEqual(compiled.audit.unmatched,[]);
 assert.deepEqual(Object.keys(compiled.routes).sort(),[...byId.keys()].sort(),'Every declared road and water leg is compiled once');
 for(const [id,r]of Object.entries(compiled.routes)){
  assert.equal(r.parts.length,r.mode==='sea'?3:r.mode==='river'?byId.get(id).river_segments.length+2:1,id);
  assert(r.parts.every(p=>p.length_px>=0&&p.chord_px>=0&&p.length_px+1e-4>=p.chord_px&&(p.length_px>0&&p.chord_px>0||p.mode==='land'&&p.length_px===0&&p.chord_px===0)),id+': only an approach already at its port can have zero length');
  assert(r.parts.every(p=>p.d.startsWith('M'+p.start.join(' '))),id+': ordered SVG starts at the named part origin');
  for(let n=1;n<r.parts.length;n++)assert.deepEqual(r.parts[n].start,r.parts[n-1].end,id+': complete harbour connections');
 }
 for(const reviewed of compiled.audit.shared_city_pass_through){assert(byId.has(reviewed.id));assert(reviewed.via.length);assert(reviewed.via.every(id=>catalog.cities.some(c=>c.id===id)));assert.match(reviewed.policy,/Logical transit required/);}
 for(const [id,r]of Object.entries(compiled.routes))if(r.mode==='land'){
  assert(r.city_sections.length>0,id+': every land leg has explicit city sections');
  assert.equal(r.city_sections[0].from,r.from);assert.equal(r.city_sections.at(-1).to,r.to);
  for(let n=0;n<r.city_sections.length;n++){
   const section=r.city_sections[n];assert.notEqual(section.from,section.to,id);
   assert.equal(section.parts.length,1);assert.equal(section.parts[0].mode,'land');
   assert.deepEqual(section.parts[0].start,catalog.cities.find(c=>c.id===section.from).position,id);
   assert.deepEqual(section.parts[0].end,catalog.cities.find(c=>c.id===section.to).position,id);
   if(n)assert.equal(section.from,r.city_sections[n-1].to,id+': transit sections connect');
  }
  assert(Math.abs(r.city_sections.reduce((sum,s)=>sum+s.parts[0].length_px,0)-r.parts[0].length_px)<.00001,id+': splitting neither duplicates nor discards road distance');
 }
 for(const id of ['henan:hongnong:land','hedong:henei:land','hedong:shangdang:land'])assert.equal(compiled.routes[id].city_sections.length,1,id+': independent historic corridor avoids false city detours');
 const jiao=compiled.routes['hepu:jiaozhi:sea'];assert(jiao,'Known sea leg and its merged land approaches remain represented');
}
console.log('route geometry: painted-network search, blocked-city failure, reversible SVG direction, complete declared leg geometry and explicit shared-city review passed');
