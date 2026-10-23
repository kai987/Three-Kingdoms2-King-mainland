'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {shortest,reversePath}=require('../game/build_route_geometry.cjs');
const graph=new Map([
 ['a',[{to:'b',length:1,tag:'ab'},{to:'x',length:2,tag:'ax'}]],
 ['b',[{to:'c',length:1,tag:'bc'}]],['x',[{to:'c',length:2,tag:'xc'}]],['c',[]]
]);
assert.equal(shortest(graph,'a','c').length,2);
assert.deepEqual(shortest(graph,'a','c',new Set(['b'])).edges.map(e=>e.tag),['ax','xc'],'Existing road search avoids a third city when a legal junction-only path exists');
assert.equal(shortest(graph,'a','c',new Set(['b','x'])),null,'Unreachable paths are reported rather than replaced by a straight line');
assert.equal(reversePath('M1 2L3 4Q5 6 7 8L9 10'),'M9 10L7 8Q5 6 3 4L1 2');
assert.equal(reversePath(reversePath('M1 2L3 4Q5 6 7 8L9 10')),'M1 2L3 4Q5 6 7 8L9 10');
assert.throws(()=>reversePath('M0 0C1 2 3 4 5 6'),/Unsupported/);
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
 assert.doesNotThrow(()=>validateSource(appSource,Buffer.concat([Buffer.from('// Display-only metadata.\n'),app]),pin,compiled.sources,attestation),'unrelated UI changes do not rewrite campaign hashes');
 assert.throws(()=>validateSource(appSource,Buffer.from(app.toString().replace('return d+`L','return d +`L')),pin,compiled.sources,attestation),'even whitespace changes inside path functions require rebuilding geometry');
 assert.throws(()=>validateSource(appSource,Buffer.concat([Buffer.from('// Display-only metadata.\n'),app]),pin,compiled.sources,{...attestation,original_source_sha256:'0'.repeat(64)}),'an attestation cannot substitute a different baseline');
 assert.throws(()=>validateSource(compilerSource,Buffer.from('// compiler changed'),compiled.sources[compilerSource],compiled.sources,attestation),'compiler changes retain full-file validation');
 assert.equal(compiled.schema,'tk2-route-geometry-v1');assert.equal(compiled.audit.input_routes,364);assert.equal(compiled.audit.compiled_routes,364);assert.deepEqual(compiled.audit.unmatched,[]);
 for(const [id,r]of Object.entries(compiled.routes)){
  assert.equal(r.parts.length,r.mode==='sea'?3:r.mode==='river'?4:1,id);
  assert(r.parts.every(p=>p.length_px>0&&p.chord_px>0&&p.length_px+1e-4>=p.chord_px),id);
  assert(r.parts.every(p=>p.d.startsWith('M'+p.start.join(' '))),id+': ordered SVG starts at the named part origin');
  for(let n=1;n<r.parts.length;n++)assert.deepEqual(r.parts[n].start,r.parts[n-1].end,id+': complete harbour connections');
 }
 assert.deepEqual(compiled.audit.shared_city_pass_through.map(r=>r.id),['dai:fanyang:land','dai:yan:land','qi:shanyang:land']);
 const jiao=compiled.routes['hepu:jiaozhi:sea'];assert(jiao,'Known sea leg and its merged land approaches remain represented');
}
console.log('route geometry: painted-network search, blocked-city failure, reversible SVG direction, complete 364-leg geometry and explicit shared-city review passed');
