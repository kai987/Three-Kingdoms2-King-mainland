/* Fixed game operations only. No user code evaluation or cross-player state. */
import {loadPyodide} from './vendor/pyodide/pyodide.mjs';
const base=new URL('.',self.location.href),decoder=new TextDecoder('utf-8',{fatal:true});
let py,bridge,manifest,booting=true,stage='manifest',receivedBytes=0,runtimeReady=false;const loaded=new Set();
function progress(extra={}){if(booting)self.postMessage({type:'progress',phase:stage,receivedBytes,runtimeReady,...extra});}
function assetUrl(value){
 if(typeof value!=='string'||!/^runtime\/[A-Za-z0-9_./-]+$/.test(value))throw Error('Invalid runtime asset');
 const url=new URL(value,base);if(url.origin!==base.origin||!url.pathname.startsWith(base.pathname+'runtime/'))throw Error('Invalid runtime asset');return url;
}
async function boundedBytes(response,limit,count=false){
 const size=Number(response.headers?.get('content-length'));if(size>limit)throw Error('Runtime asset too large');
 if(!response.body?.getReader){const raw=new Uint8Array(await response.arrayBuffer());if(raw.length>limit)throw Error('Runtime asset too large');if(count){receivedBytes+=raw.length;progress();}return raw;}
 const reader=response.body.getReader(),chunks=[];let length=0,lastProgress=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit){await reader.cancel();throw Error('Runtime asset too large');}chunks.push(value);if(count){receivedBytes+=value.byteLength;if(receivedBytes-lastProgress>=65536){lastProgress=receivedBytes;progress();}}}}
 finally{reader.releaseLock();}
 const raw=new Uint8Array(length);let offset=0;for(const chunk of chunks){raw.set(chunk,offset);offset+=chunk.byteLength;}if(count)progress();return raw;
}
async function bytes(url,limit){
 const address=assetUrl(url);
 for(let attempt=0;attempt<3;attempt++){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
  try{
   const response=await fetch(address,{signal:controller.signal});
   if(!response.ok){const error=Error('Runtime asset unavailable');error.retryable=response.status===408||response.status===429||response.status>=500;throw error;}
   return await boundedBytes(response,limit,true);
  }catch(error){
   controller.abort();clearTimeout(timer);
   if(attempt===2||error.retryable===false||error.message==='Runtime asset too large')throw error;
   progress({retrying:true});await new Promise(resolve=>setTimeout(resolve,500*(attempt+1)));
  }finally{clearTimeout(timer);}
 }
}
async function verified(data,expected){
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),x=>x.toString(16).padStart(2,'0')).join('');
 if(!/^[a-f0-9]{64}$/.test(expected||'')||digest!==expected)throw Error('Runtime integrity mismatch');return data;
}
function filePath(value){return typeof value==='string'&&/^\/tk2\/game\/data\/campaigns\/[A-Za-z0-9_-]+\.json$/.test(value);}
async function catalogData(row){
 const zipped=await bytes(row.url,4*1024*1024);
 const stream=new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'));
 const raw=await boundedBytes(new Response(stream),16*1024*1024);
 if(raw.length!==row.bytes)throw Error('Catalog size mismatch');await verified(raw,row.sha256);return raw;
}
function installCatalog(row,raw){
 py.FS.mkdirTree('/tk2/game/data/campaigns');py.FS.writeFile(row.path,raw);loaded.add(row.id);
 while(loaded.size>2){
  const oldest=loaded.values().next().value;loaded.delete(oldest);
  const retired=manifest.catalogs.find(row=>row.id===oldest);if(retired&&filePath(retired.path))py.FS.unlink(retired.path);
 }
}
async function catalog(id){
 if(loaded.has(id)){loaded.delete(id);loaded.add(id);return;}
 const row=manifest.catalogs.find(row=>row.id===id);if(!row||!filePath(row.path))return;
 installCatalog(row,await catalogData(row));
}
function requestedScenario(path,body){
 const url=new URL(path,'https://game.invalid');
 if(['/api/city-preview','/api/march-config'].includes(url.pathname))return url.searchParams.get('scenario');
 try{const value=typeof body==='string'?JSON.parse(body):body;
  if(url.pathname==='/api/command'&&value?.kind==='new')return value.payload?.scenario;
  if(url.pathname==='/api/load')return value?.save?.scenario;
 }catch{/* Invalid JSON is rejected by the Python request boundary. */}
 return null;
}
const boot=(async()=>{
 progress();manifest=JSON.parse(decoder.decode(await bytes('runtime/engine-manifest.json',1024*1024)));
 if(manifest.schema!=='tk2-browser-engine-v1'||manifest.pyodide_version!=='314.0.7'||!Array.isArray(manifest.catalogs)||!manifest.catalogs.length||manifest.catalogs.length>64)throw Error('Invalid runtime manifest');
 const identities=new Set();for(const row of manifest.catalogs){
  if(!row||typeof row.id!=='string'||!/^[A-Za-z0-9_-]+$/.test(row.id)||identities.has(row.id)||!filePath(row.path)||!Number.isSafeInteger(row.bytes)||row.bytes<1||row.bytes>16*1024*1024||!/^[a-f0-9]{64}$/.test(row.sha256||''))throw Error('Invalid catalog manifest');
  identities.add(row.id);assetUrl(row.url);
 }
 const initial=manifest.catalogs.find(row=>row.id===manifest.initial_scenario);if(!initial)throw Error('Invalid initial scenario');
 assetUrl(manifest.python_bundle?.url);assetUrl(manifest.previews?.url);
 stage='loading';progress();
 // Only verified game assets run in parallel with Pyodide. No campaign or RNG
 // exists until every asset has passed its size and SHA checks.
 const [runtime,bundle,previews,initialData]=await Promise.all([
  loadPyodide({indexURL:new URL('vendor/pyodide/',base).href}).then(value=>{runtimeReady=true;progress();return value;}),
  bytes(manifest.python_bundle.url,4*1024*1024).then(data=>verified(data,manifest.python_bundle.sha256)),
  bytes(manifest.previews.url,8*1024*1024).then(data=>verified(data,manifest.previews.sha256)),
  catalogData(initial)
 ]);
 py=runtime;stage='initializing';progress();py.unpackArchive(bundle,'zip',{extractDir:'/tk2'});installCatalog(initial,initialData);
 py.globals.set('_tk2_paths',JSON.stringify(Object.fromEntries(manifest.catalogs.map(row=>[row.id,row.path]))));
 py.globals.set('_tk2_previews',decoder.decode(previews));py.globals.set('_tk2_initial',manifest.initial_scenario);
 bridge=py.runPython(`import sys, json, os
sys.path.insert(0, '/tk2/source')
os.environ['MARCH_CORE_BACKEND'] = 'python'
from remake.browser_runtime import BrowserRuntime
BrowserRuntime(json.loads(_tk2_paths), json.loads(_tk2_previews), _tk2_initial)`);
 booting=false;self.postMessage({type:'ready'});
})();
boot.catch(()=>{booting=false;self.postMessage({type:'fatal'});});
let queue=Promise.resolve();
self.onmessage=event=>{
 const message=event.data||{};
 if(message.type!=='request'||!Number.isSafeInteger(message.id)||typeof message.path!=='string'||message.path.length>1024||!['GET','POST'].includes(message.method)||message.body!==null&&typeof message.body!=='string')return;
 queue=queue.then(async()=>{
  try{
   await boot;
   if(message.body!==null&&new TextEncoder().encode(message.body).length>2*1024*1024){self.postMessage({type:'response',id:message.id,status:413,body:'{"error":"Request too large"}'});return;}
   const scenario=requestedScenario(message.path,message.body);if(scenario)await catalog(scenario);
   // Pyodide314 preserves JS null as JsNull; omit the optional Python body
   // argument for GET rather than accidentally submitting a nonempty body.
   const result=typeof message.view_cache==='string'
    ?bridge.dispatch_compact_json(message.path,message.method,message.body??'',message.view_cache)
    :message.body===null?bridge.dispatch_json(message.path,message.method):bridge.dispatch_json(message.path,message.method,message.body);
   try{const value=result.toJs({dict_converter:Object.fromEntries});self.postMessage({type:'response',id:message.id,status:value.status,body:value.body});}finally{result.destroy();}
  }catch{self.postMessage({type:'response',id:message.id,status:503,body:'{"error":"遊戲資料載入失敗。／ゲームデータを読み込めません。"}'});}
 });
};
