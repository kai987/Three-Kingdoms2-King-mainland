#!/usr/bin/env node
/* Real WebAssembly + CPU replay of the shipped, isolated browser campaign. */
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const build=path.resolve(root,process.argv[2]||'build/web');
const runtimeDirectory=path.join(root,'tools/web-runtime/node_modules/pyodide');
const sha=value=>createHash('sha256').update(value).digest('hex');
const decode=bytes=>new TextDecoder('utf-8',{fatal:true}).decode(bytes);
const jsonFile=name=>JSON.parse(fs.readFileSync(name,'utf8'));
const manifest=jsonFile(path.join(build,'runtime/engine-manifest.json'));
assert.equal(manifest.schema,'tk2-browser-engine-v1');
assert.equal(manifest.pyodide_version,'314.0.7');
assert.equal(jsonFile(path.join(runtimeDirectory,'package.json')).version,manifest.pyodide_version);
assert.equal(manifest.catalogs.length,29,'the release includes all 29 scenarios');
function artifact(url){
 assert.equal(typeof url,'string');
 const resolved=path.resolve(build,url);
 assert(resolved.startsWith(build+path.sep),'runtime artifacts stay inside the build');
 return fs.readFileSync(resolved);
}
const bundle=artifact(manifest.python_bundle.url),previewBytes=artifact(manifest.previews.url);
assert.equal(sha(bundle),manifest.python_bundle.sha256,'shipped Python bundle integrity');
assert.equal(sha(previewBytes),manifest.previews.sha256,'shipped opening preview integrity');
const previews=JSON.parse(decode(previewBytes));
assert.equal(previews.length,29);
const initial=manifest.initial_scenario;
const another=manifest.catalogs.find(row=>row.id!==initial)?.id;
assert(another,'a second scenario is required for the lazy switching check');
const catalogs=new Map();
for(const identity of [initial,another]){
 const row=manifest.catalogs.find(row=>row.id===identity);
 assert.match(row.path,/^\/tk2\/game\/data\/campaigns\/[a-zA-Z0-9-]+\.json$/);
 const bytes=gunzipSync(artifact(row.url));
 assert.equal(bytes.length,row.bytes);
 assert.equal(sha(bytes),row.sha256,'decompressed catalog retains its exact save identity');
 assert.equal(JSON.parse(decode(bytes)).id,row.id);
 catalogs.set(identity,{row,bytes});
}

const referenceScript=String.raw`
from hashlib import sha256
import json, os, pathlib, sys, tempfile, zipfile
request=json.load(sys.stdin)
os.environ['MARCH_CORE_BACKEND']='python'
with tempfile.TemporaryDirectory(prefix='tk2-cpu-replay-') as directory:
    mount=pathlib.Path(directory)
    with zipfile.ZipFile(request['bundle']) as archive:
        archive.extractall(mount)
    sys.path.insert(0,str(mount/'source'))
    from remake.browser_runtime import BrowserRuntime
    catalog_paths={row['id']:str(mount/row['path'].removeprefix('/tk2/'))
                   for row in request['manifest']['catalogs']}
    for row in request['catalogs']:
        target=pathlib.Path(catalog_paths[row['id']])
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(pathlib.Path(row['raw']).read_bytes())
    previews=json.loads(pathlib.Path(request['previews']).read_text(encoding='utf-8'))
    engines={key:BrowserRuntime(catalog_paths,previews,request['manifest']['initial_scenario'])
             for key in ('primary','isolated')}
    results=[]
    for operation in request['trace']:
        bridge=engines[operation['instance']]
        # Missing optional body matches the browser's GET calling convention.
        response=(bridge.dispatch_json(operation['path'],operation['method'],operation['body'])
                  if 'body' in operation else
                  bridge.dispatch_json(operation['path'],operation['method']))
        semantic=json.dumps(json.loads(response['body']),sort_keys=True,ensure_ascii=False,allow_nan=False)
        results.append(dict(status=response['status'],
                            response_semantic_sha256=sha256(semantic.encode('utf-8')).hexdigest(),
                            **({'save':response['body']} if operation['path']=='/api/save' and response['status']==200 else {})))
    final=engines['primary'].dispatch_json('/api/save')
    assert final['status']==200
    print(json.dumps(dict(results=results,save=final['body'],
                         rng=json.loads(final['body'])['state']['rng']),ensure_ascii=False))
`;

let py,responseSemantic;
const bridges=new Map(),trace=[],wasmResults=[];
function request(pathname,{method='GET',body,instance='primary',status=200}={}){
 const bridge=bridges.get(instance);assert(bridge,'known isolated runtime instance');
 const operation={instance,path:pathname,method,...(body===undefined?{}:{body})};
 if(body!==undefined)assert.equal(typeof body,'string','POST bodies remain JSON text');
 // JS null is JsNull in Pyodide 314, not Python None. Omit body for reads.
 const result=body===undefined?bridge.dispatch_json(pathname,method):bridge.dispatch_json(pathname,method,body);
 let response;
 try{response=result.toJs({dict_converter:Object.fromEntries});}finally{result.destroy();}
 assert.equal(typeof response.body,'string');
 assert.equal(response.status,status,`${instance} ${method} ${pathname}: ${response.body.slice(0,300)}`);
 trace.push(operation);
 wasmResults.push({status:response.status,response_semantic_sha256:responseSemantic(response.body),
  ...(pathname==='/api/save'&&status===200?{save:response.body}:{})});
 return response.body;
}
function state(instance='primary'){return JSON.parse(request('/api/state',{instance}));}
function command(view,kind,payload={}){
 return JSON.parse(request('/api/command',{method:'POST',
  body:JSON.stringify({kind,payload,revision:view.revision})}));
}
function load(raw,revision){
 // Preserve the exported save text inside the request; avoid a parse/stringify
 // pass like the production JSON-file and cloud-slot import path.
 return JSON.parse(request('/api/load',{method:'POST',body:`{"save":${raw},"revision":${revision}}`}));
}
function unchangedFailure(pathname,settings){
 const before=request('/api/save');
 request(pathname,settings);
 assert.equal(request('/api/save'),before,'rejected operations retain every saved byte and RNG draw');
}
function createBridge(name){
 const value=py.runPython(`BrowserRuntime(json.loads(_tk2_paths), json.loads(_tk2_previews), _tk2_initial)`);
 bridges.set(name,value);
}

const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'tk2-wasm-smoke-'));
try{
 console.log('browser engine smoke: loading real Pyodide 314.0.7 WebAssembly from local pinned assets');
 const {loadPyodide}=await import(pathToFileURL(path.join(runtimeDirectory,'pyodide.mjs')).href);
 py=await loadPyodide({indexURL:runtimeDirectory+path.sep});
 assert.equal(py.version,manifest.pyodide_version);
 py.unpackArchive(new Uint8Array(bundle),'zip',{extractDir:'/tk2'});
 for(const {row,bytes} of catalogs.values()){
  py.FS.mkdirTree(path.posix.dirname(row.path));
  py.FS.writeFile(row.path,new Uint8Array(bytes));
 }
 py.globals.set('_tk2_paths',JSON.stringify(Object.fromEntries(manifest.catalogs.map(row=>[row.id,row.path]))));
 py.globals.set('_tk2_previews',decode(previewBytes));
 py.globals.set('_tk2_initial',initial);
 py.runPython(`import sys, json, os
sys.path.insert(0, '/tk2/source')
os.environ['MARCH_CORE_BACKEND'] = 'python'
from remake.browser_runtime import BrowserRuntime
from hashlib import sha256
def _tk2_response_semantic(body):
    return sha256(json.dumps(json.loads(body),sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()`);
 responseSemantic=py.globals.get('_tk2_response_semantic');
 const tacticalData=JSON.parse(py.runPython(`from remake.battle_grid import _library as _battle_library
from remake.tactical_ai import _learnability as _battle_learnability
json.dumps({'maps':len(_battle_library()[0]),'cities':len(_battle_library()[1]),
            'special_people':len(_battle_learnability()[1])})`));
 assert.deepEqual(tacticalData,{maps:30,cities:115,special_people:21},
  'Actual WebAssembly loads the same original battlefield and tactic tables as native Python');
 createBridge('primary');createBridge('isolated');
 const isolatedMenu=state('isolated');
 assert.equal(isolatedMenu.game,null);
 assert.equal(isolatedMenu.catalog.scenarios.length,29);
 let view=state();
 assert.equal(view.game,null);
 assert.equal(view.catalog.scenarios.length,29);
 assert.deepEqual(view.catalog.scenarios.map(row=>row.id),previews.map(row=>row.id));
 const opening=previews.find(row=>row.id===initial);
 const eligible=opening.factions.map(row=>row.id).filter(id=>opening.faction_officers[id]>=2&&opening.faction_resources[id]?.cities>0);
 assert(eligible.length,'initial scenario contains a playable force with multiple officers');
 const faction=eligible.includes('shu')?'shu':eligible[0];
 view=command(view,'new',{scenario:initial,faction,seed:20261023,difficulty:'normal'});
 assert.equal(view.game.player,faction);
 assert.equal(view.game.phase,'city');
 assert.deepEqual(state('isolated'),isolatedMenu,'another instance is still an untouched menu');
 const openingSave=request('/api/save'),openingRng=JSON.parse(openingSave).state.rng;
 const ownCity=Object.values(view.game.cities).find(city=>city.owner===faction&&city.reserves>0&&city.roster.officer_ids.some(id=>view.game.officers[id].troops<999));
 assert(ownCity,'the chosen force can meaningfully allocate reserve troops');
 const preview=JSON.parse(request('/api/city-preview?'+new URLSearchParams({scenario:initial,city:ownCity.id})));
 assert.equal(preview.city.id,ownCity.id);
 assert.equal(request('/api/save'),openingSave,'opening inspection cannot change RNG or state');
 assert.deepEqual(JSON.parse(request('/api/save')).state.rng,openingRng);
 const officer=ownCity.roster.officer_ids.find(id=>view.game.officers[id].troops<999);
 const originalTroops=view.game.officers[officer].troops;
 const amount=Math.min(7,ownCity.reserves,999-originalTroops);
 assert(amount>0);
 view=command(view,'allocate',{city:ownCity.id,officer,troops:originalTroops+amount});
 assert.equal(view.game.officers[officer].troops,originalTroops+amount);
 assert.equal(view.game.cities[ownCity.id].reserves,ownCity.reserves-amount);
 const allocated=request('/api/save');
 view=load(allocated,view.revision);
 assert.equal(request('/api/save'),allocated,'raw save import/export is byte-identical');

 const startTurn=view.game.turn;
 view=command(view,'end_turn');
 let aiCalls=0,battleSettlements=0;
 for(let step=0;step<48&&!(view.game.phase==='city'&&view.game.turn>startTurn);step++){
  switch(view.game.phase){
   case 'ai':view=command(view,'ai',{turn:view.game.turn});aiCalls++;break;
   case 'arrivals':view=command(view,'arrivals');break;
   case 'battle':view=command(view,'retreat',{battle_id:view.game.battle.id});break;
   case 'result':view=command(view,'settle',{battle_id:view.game.battle.id});battleSettlements++;break;
   default:assert.fail(`unexpected campaign phase during bounded turn advancement: ${view.game.phase}`);
  }
 }
 assert(aiCalls>0,'real AI decisions execute in WebAssembly');
 assert.equal(view.game.phase,'city','bounded AI and battle settlement returns to strategy');
 assert.equal(view.game.turn,startTurn+1,'exactly one ten-day turn advances');
 const afterTurn=request('/api/save');
 assert(JSON.parse(afterTurn).state.rng.draws>openingRng.draws,'AI consumes the actual deterministic random stream');
 unchangedFailure('/api/python',{status:404});
 unchangedFailure('/api/command',{method:'POST',status:409,
  body:JSON.stringify({kind:'allocate',payload:{city:ownCity.id,officer,troops:999},revision:view.revision-1})});
 unchangedFailure('/api/command',{method:'POST',status:400,
  body:`{"kind":"ai","kind":"end_turn","payload":{},"revision":${view.revision}}`});
 const corrupted=JSON.parse(afterTurn);corrupted.checksum='0'.repeat(64);
 unchangedFailure('/api/load',{method:'POST',status:400,
  body:JSON.stringify({save:corrupted,revision:view.revision})});
 assert.equal(request('/api/save'),afterTurn);

 const otherOpening=previews.find(row=>row.id===another);
 const otherFaction=otherOpening.factions.find(row=>otherOpening.faction_officers[row.id]>0&&otherOpening.faction_resources[row.id]?.cities>0)?.id;
 assert(otherFaction,'second scenario includes a force with officers');
 view=command(view,'new',{scenario:another,faction:otherFaction,seed:20261023});
 assert.equal(view.catalog.scenario_id,another);
 assert.equal(JSON.parse(request('/api/save')).scenario,another);
 view=load(afterTurn,view.revision);
 assert.equal(view.catalog.scenario_id,initial);
 const finalSave=request('/api/save');
 assert.equal(finalSave,afterTurn,'returning from another scenario restores the exact original save');
 assert.deepEqual(state('isolated'),isolatedMenu,'all primary commands leave the other instance untouched');
 assert.equal(JSON.parse(request('/api/march-status')).engine,'python');

 // Exercise the real optional wire path, not only the legacy bridge used by
 // CPU replay. Hydration must reconstruct the same complete current view.
 const {default:wireModule}=await import(pathToFileURL(path.join(root,'game/view-cache.js')).href);
 const wireClient=wireModule.create(),fullView=state(),beforeWire=request('/api/save');
 function compactView(token){
  const result=bridges.get('primary').dispatch_compact_json('/api/state','GET','',token);
  try{const response=result.toJs({dict_converter:Object.fromEntries});assert.equal(response.status,200);return {raw:response.body,packet:JSON.parse(response.body)};}finally{result.destroy();}
 }
 const initialWire=compactView('');assert.deepEqual(wireClient.hydrate(initialWire.packet),fullView);
 const cachedWire=compactView(wireClient.token());assert(!('static_catalog' in cachedWire.packet));
 assert.deepEqual(wireClient.hydrate(cachedWire.packet),fullView);
 assert.equal(request('/api/save'),beforeWire,'Compact reads retain every saved byte and RNG draw');
 assert(Buffer.byteLength(cachedWire.raw)<Buffer.byteLength(JSON.stringify(fullView))*.6,'Cached responses omit the immutable catalog');
 console.log('browser view cache: real WASM full/cached hydration matches legacy state and exact save bytes');
 console.log(`browser engine smoke: ${trace.length} real requests, one AI turn, ${battleSettlements} battle settlements; replaying identical trace on CPU Python`);
 // Snapshot the verified build inputs so a concurrent build cannot change the
 // reference interpreter's sources or catalog identities during this check.
 const bundlePath=path.join(temporary,'python.zip'),previewsPath=path.join(temporary,'previews.json');
 fs.writeFileSync(bundlePath,bundle);fs.writeFileSync(previewsPath,previewBytes);
 const referenceCatalogs=[];
 for(const [identity,{bytes}] of catalogs){
  const raw=path.join(temporary,identity+'.json');fs.writeFileSync(raw,bytes);referenceCatalogs.push({id:identity,raw});
 }
 const reference=spawnSync(process.env.PYTHON||'python3',['-B','-c',referenceScript],{
  cwd:root,input:JSON.stringify({bundle:bundlePath,previews:previewsPath,manifest,catalogs:referenceCatalogs,trace}),
  encoding:'utf8',maxBuffer:32*1024*1024,timeout:180000,
  env:{...process.env,MARCH_CORE_BACKEND:'python',PYTHONDONTWRITEBYTECODE:'1'}
 });
 assert.ifError(reference.error);
 assert.equal(reference.status,0,reference.stderr);
 const cpu=JSON.parse(reference.stdout);
 assert.equal(cpu.results.length,wasmResults.length);
 for(let index=0;index<wasmResults.length;index++){
  const expected=wasmResults[index],actual=cpu.results[index],operation=trace[index];
  const label=`request ${index+1}: ${operation.instance} ${operation.method} ${operation.path}`;
  assert.equal(actual.status,expected.status,label+' status');
  assert.equal(actual.response_semantic_sha256,expected.response_semantic_sha256,label+' JSON response semantics');
  if('save' in expected)assert(actual.save===expected.save,label+' exact save text');
 }
 assert(cpu.save===finalSave,'final raw save agrees across CPython and real Python WebAssembly');
 const rng=JSON.parse(finalSave).state.rng;
 assert.deepEqual(cpu.rng,rng,'final RNG state and draw count agree');
 console.log(JSON.stringify({ok:true,pyodide:py.version,previews:previews.length,catalogs:catalogs.size,
  requests:trace.length,ai_turns:1,battle_settlements:battleSettlements,
  save_sha256:sha(finalSave),rng,cpu_save_bytes_equal:true}));
}finally{
 for(const bridge of bridges.values())bridge.destroy();
 responseSemantic?.destroy();
 fs.rmSync(temporary,{recursive:true,force:true});
}
