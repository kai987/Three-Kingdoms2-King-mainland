/* Fixed game operations only. No user code evaluation or cross-player state. */
import {loadPyodide} from './vendor/pyodide/pyodide.mjs';
const base=new URL('.',self.location.href),decoder=new TextDecoder('utf-8',{fatal:true});
let py,bridge,manifest;const loaded=new Set();
async function bytes(url,limit){
 const response=await fetch(new URL(url,base));if(!response.ok)throw Error('Runtime asset unavailable');
 const result=new Uint8Array(await response.arrayBuffer());if(result.length>limit)throw Error('Runtime asset too large');return result;
}
async function verified(data,expected){
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),x=>x.toString(16).padStart(2,'0')).join('');
 if(!/^[a-f0-9]{64}$/.test(expected||'')||digest!==expected)throw Error('Runtime integrity mismatch');return data;
}
function filePath(value){return typeof value==='string'&&/^\/tk2\/game\/data\/campaigns\/[A-Za-z0-9-]+\.json$/.test(value);}
async function catalog(id){
 if(loaded.has(id)){loaded.delete(id);loaded.add(id);return;}
 const row=manifest.catalogs.find(row=>row.id===id);if(!row||!filePath(row.path))return;
 const zipped=await bytes(row.url,4*1024*1024);
 const stream=new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'));
 const raw=new Uint8Array(await new Response(stream).arrayBuffer());
 if(raw.length!==row.bytes||raw.length>16*1024*1024)throw Error('Catalog size mismatch');await verified(raw,row.sha256);
 py.FS.mkdirTree('/tk2/game/data/campaigns');py.FS.writeFile(row.path,raw);loaded.add(id);
 while(loaded.size>2){
  const oldest=loaded.values().next().value;loaded.delete(oldest);
  const retired=manifest.catalogs.find(row=>row.id===oldest);if(retired&&filePath(retired.path))py.FS.unlink(retired.path);
 }
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
 manifest=JSON.parse(decoder.decode(await bytes('runtime/engine-manifest.json',1024*1024)));
 if(manifest.schema!=='tk2-browser-engine-v1'||manifest.pyodide_version!=='314.0.7'||!Array.isArray(manifest.catalogs)||manifest.catalogs.length>64)throw Error('Invalid runtime manifest');
 py=await loadPyodide({indexURL:new URL('vendor/pyodide/',base).href});
 const [bundle,previews]=await Promise.all([
  bytes(manifest.python_bundle.url,4*1024*1024).then(data=>verified(data,manifest.python_bundle.sha256)),
  bytes(manifest.previews.url,8*1024*1024).then(data=>verified(data,manifest.previews.sha256))
 ]);
 py.unpackArchive(bundle,'zip',{extractDir:'/tk2'});
 await catalog(manifest.initial_scenario);
 py.globals.set('_tk2_paths',JSON.stringify(Object.fromEntries(manifest.catalogs.map(row=>[row.id,row.path]))));
 py.globals.set('_tk2_previews',decoder.decode(previews));py.globals.set('_tk2_initial',manifest.initial_scenario);
 bridge=py.runPython(`import sys, json, os
sys.path.insert(0, '/tk2/source')
os.environ['MARCH_CORE_BACKEND'] = 'python'
from remake.browser_runtime import BrowserRuntime
BrowserRuntime(json.loads(_tk2_paths), json.loads(_tk2_previews), _tk2_initial)`);
 self.postMessage({type:'ready'});
})();
boot.catch(()=>self.postMessage({type:'fatal'}));
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
   const result=message.body===null?bridge.dispatch_json(message.path,message.method):bridge.dispatch_json(message.path,message.method,message.body);
   try{const value=result.toJs({dict_converter:Object.fromEntries});self.postMessage({type:'response',id:message.id,status:value.status,body:value.body});}finally{result.destroy();}
  }catch{self.postMessage({type:'response',id:message.id,status:503,body:'{"error":"遊戲資料載入失敗。／ゲームデータを読み込めません。"}'});}
 });
};
