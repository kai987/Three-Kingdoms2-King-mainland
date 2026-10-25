'use strict';
/* Exercise shipped worker boot with real streams, gzip, SHA and bounded fake Pyodide. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {webcrypto,createHash}=require('node:crypto'),{gzipSync}=require('node:zlib');
const source=fs.readFileSync(path.join(__dirname,'../game/browser-engine-worker.js'),'utf8').replace(/^import \{loadPyodide\} from .*;\n/m,'');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
async function until(test){for(let count=0;count<80;count++){if(test())return;await flush();}throw Error('Worker fixture did not reach the expected checkpoint');}
function fixture({gateRuntime=false,failures={},mutateManifest,changeAsset,respond}={}){
 const bundle=Buffer.from('verified-python-archive'),preview=Buffer.from('[]'),assets=new Map(),rows=['first','second','third'].map(id=>{
  const raw=Buffer.from(JSON.stringify({id,exact_bytes:'save identity stays unchanged'}));assets.set(`runtime/catalogs/${id}.json.gz`,gzipSync(raw));return{id,url:`runtime/catalogs/${id}.json.gz`,path:`/tk2/game/data/campaigns/${id}.json`,sha256:sha(raw),bytes:raw.length};
 });
 const manifest={schema:'tk2-browser-engine-v1',build_commit:'a'.repeat(40),pyodide_version:'314.0.7',python_bundle:{url:'runtime/python.zip',sha256:sha(bundle)},previews:{url:'runtime/scenario-previews.json',sha256:sha(preview)},catalogs:rows,initial_scenario:'first'};
 mutateManifest?.(manifest);assets.set('runtime/engine-manifest.json',Buffer.from(JSON.stringify(manifest)));assets.set('runtime/python.zip',bundle);assets.set('runtime/scenario-previews.json',preview);changeAsset?.(assets);
 const messages=[],requests=[],writes=new Map(),removed=[],dispatches=[],compactDispatches=[],timers=[],unpacked=[];let runCount=0,releaseRuntime;
 const result=(revision,compact=false)=>({toJs:()=>({status:200,body:JSON.stringify({revision,game:null,...(compact?{view_cache:{token:'verified-catalog-token'}}:{})})}),destroy(){}});
 const bridge={dispatch_json(...args){dispatches.push(args);return result(dispatches.length);},dispatch_compact_json(...args){compactDispatches.push(args);return result(compactDispatches.length,true);}};
 const py={FS:{mkdirTree(){},writeFile(name,raw){writes.set(name,Buffer.from(raw));},unlink(name){removed.push(name);writes.delete(name);}},globals:{set(){}},unpackArchive(raw,type,options){unpacked.push({raw:Buffer.from(raw),type,options});},runPython(){runCount++;return bridge;}};
 const loadPyodide=()=>gateRuntime?new Promise(resolve=>{releaseRuntime=()=>resolve(py);}):Promise.resolve(py);
 const self={location:{href:'https://game.example/repo/browser-engine-worker.js'},postMessage:message=>messages.push(message)};
 const fetch=async(address,options)=>{
  const url=new URL(address),name=url.pathname.replace('/repo/','');requests.push({name,url,options});
  const attempt=requests.filter(row=>row.name===name).length;if(respond){const result=respond(name,attempt,options);if(result)return result;}
  if((failures[name]||0)>=attempt)return new Response('temporarily unavailable',{status:503});
  if(!assets.has(name))return new Response('missing',{status:404});return new Response(assets.get(name));
 };
 const context={self,loadPyodide,fetch,TextEncoder,TextDecoder,URL,Response,Blob,DecompressionStream,AbortController,Uint8Array,crypto:webcrypto,console,
  setTimeout(fn,ms){const timer={fn,ms,active:true};timers.push(timer);if(ms<30000)queueMicrotask(()=>{if(timer.active){timer.active=false;fn();}});return timer;},clearTimeout(timer){timer.active=false;}};
 vm.createContext(context);vm.runInContext(source+'\nglobalThis.workerTest={boot,catalog,loaded,assetUrl};',context);
 return{...context.workerTest,self,messages,requests,writes,removed,dispatches,compactDispatches,timers,unpacked,manifest,assets,get runCount(){return runCount;},releaseRuntime:()=>releaseRuntime()};
}
(async()=>{
 const concurrent=fixture({gateRuntime:true});await until(()=>concurrent.requests.length===4);
 assert.deepEqual(concurrent.requests.map(row=>row.name).sort(),['runtime/engine-manifest.json','runtime/python.zip','runtime/scenario-previews.json','runtime/catalogs/first.json.gz'].sort(),'all verified startup assets download before Pyodide resolves');
 const manifestRequest=concurrent.requests.find(row=>row.name==='runtime/engine-manifest.json');
 assert.equal(manifestRequest.options.cache,'no-store');assert.match(manifestRequest.url.searchParams.get('t'),/^\d+$/,'public manifest URL bypasses a stale CDN key');
 for(const row of [concurrent.manifest.python_bundle,concurrent.manifest.previews,concurrent.manifest.catalogs[0]]){
  const request=concurrent.requests.find(request=>request.name===row.url);
  assert.equal(request.url.searchParams.get('v'),row.sha256,'verified assets use expected SHA as their reusable cache identity');
  assert.notEqual(request.options.cache,'no-store');assert(!request.url.searchParams.has('t'));
 }
 assert.equal(concurrent.runCount,0);assert.equal(concurrent.writes.size,0,'no data is installed before all assets and the runtime are ready');
 assert(!concurrent.requests.some(row=>row.name.includes('second')||row.name.includes('third')),'other scenarios stay lazy');
 concurrent.releaseRuntime();await concurrent.boot;assert.equal(concurrent.runCount,1);assert.equal(concurrent.messages.find(row=>row.type==='ready').build_commit,concurrent.manifest.build_commit);assert.equal(concurrent.unpacked.length,1);
 assert(concurrent.messages.some(row=>row.phase==='manifest'));assert(concurrent.messages.some(row=>row.phase==='loading'&&row.receivedBytes>0));assert(concurrent.messages.some(row=>row.phase==='initializing'));assert(!concurrent.messages.some(row=>'percent' in row));
 const downloaded=concurrent.requests.reduce((sum,row)=>sum+concurrent.assets.get(row.name).length,0);assert.equal(concurrent.messages.find(row=>row.phase==='initializing').receivedBytes,downloaded,'reported game-data bytes count actual fetched data and exclude the runtime');
 assert.equal(concurrent.writes.get(concurrent.manifest.catalogs[0].path).length,concurrent.manifest.catalogs[0].bytes);
 const initialCount=concurrent.requests.length;await concurrent.catalog('first');assert.equal(concurrent.requests.length,initialCount,'resident catalog is not downloaded twice');
 await concurrent.catalog('second');await concurrent.catalog('first');await concurrent.catalog('third');
 assert.equal(concurrent.loaded.size,2);assert.deepEqual([...concurrent.loaded],['first','third'],'two-item catalog cache retains least recently used semantics');assert.deepEqual(concurrent.removed,[concurrent.manifest.catalogs[1].path]);
 const raw='{ "kind": "new", "payload": {"scenario":"second"} }';
 concurrent.self.onmessage({data:{type:'request',id:1,path:'/api/command',method:'POST',body:raw}});await until(()=>concurrent.messages.some(row=>row.type==='response'&&row.id===1));
 assert.equal(concurrent.dispatches.at(-1)[2],raw,'mutating request text is passed unchanged');
 concurrent.self.onmessage({data:{type:'request',id:2,path:'/api/state',method:'GET',body:null}});await until(()=>concurrent.messages.some(row=>row.type==='response'&&row.id===2));assert.equal(concurrent.dispatches.at(-1).length,2,'GET still omits JsNull body');
 assert.equal(concurrent.compactDispatches.length,0,'legacy callers never enter the compact Python boundary');
 concurrent.self.onmessage({data:{type:'request',id:3,path:'/api/state',method:'GET',body:null,view_cache:''}});await until(()=>concurrent.messages.some(row=>row.type==='response'&&row.id===3));
 assert.deepEqual(concurrent.compactDispatches.at(-1),['/api/state','GET','',''],'first compact GET uses an empty body instead of JsNull and an empty known token');
 assert.equal(concurrent.dispatches.length,2);assert.equal(JSON.parse(concurrent.messages.find(row=>row.id===3).body).view_cache.token,'verified-catalog-token');
 concurrent.self.onmessage({data:{type:'request',id:4,path:'/api/command',method:'POST',body:raw,view_cache:'verified-catalog-token'}});await until(()=>concurrent.messages.some(row=>row.type==='response'&&row.id===4));
 assert.deepEqual(concurrent.compactDispatches.at(-1),['/api/command','POST',raw,'verified-catalog-token'],'subsequent compact commands retain raw body and pass the known token unchanged');
 assert.equal(concurrent.compactDispatches.length,2);assert.equal(concurrent.dispatches.length,2,'compact dispatch does not replay the same command through the legacy boundary');
 concurrent.self.onmessage({data:{type:'request',id:5,path:'/api/state',method:'GET',body:null,view_cache:42}});await until(()=>concurrent.messages.some(row=>row.type==='response'&&row.id===5));
 assert.equal(concurrent.dispatches.at(-1).length,2);assert.equal(concurrent.compactDispatches.length,2,'non-string cache metadata falls back to the legacy contract');

 const retried=fixture({failures:{'runtime/python.zip':2}});await retried.boot;assert.equal(retried.requests.filter(row=>row.name==='runtime/python.zip').length,3);assert.equal(retried.runCount,1);assert(retried.messages.some(row=>row.retrying));assert(retried.timers.every(timer=>!timer.active));
 const unavailable=fixture({failures:{'runtime/python.zip':9}});await assert.rejects(unavailable.boot);assert.equal(unavailable.requests.filter(row=>row.name==='runtime/python.zip').length,3,'transient retries stop after three attempts');assert.equal(unavailable.runCount,0);assert(unavailable.messages.some(row=>row.type==='fatal'));
 const missing=fixture({respond:name=>name==='runtime/python.zip'?new Response('missing',{status:404}):undefined});await assert.rejects(missing.boot);assert.equal(missing.requests.filter(row=>row.name==='runtime/python.zip').length,1,'permanent HTTP failures are not retried');
 const wrong=fixture({changeAsset:assets=>assets.set('runtime/python.zip',Buffer.from('tampered'))});await assert.rejects(wrong.boot,/integrity/);assert.equal(wrong.runCount,0);assert.equal(wrong.writes.size,0);assert.equal(wrong.requests.filter(row=>row.name==='runtime/python.zip').length,1,'SHA mismatch requires visible user retry rather than accepting corrupt data');
 const escaped=fixture({mutateManifest:manifest=>{manifest.python_bundle.url='https://outside.example/python.zip';}});await assert.rejects(escaped.boot,/asset/);assert.equal(escaped.requests.length,1,'runtime manifest cannot redirect downloads to an external origin');
 for(const value of ['runtime/../python.zip','runtime/catalogs/../python.zip','runtime//python.zip','runtime/python.zip?v=forged','runtime/python.zip#fragment'])assert.throws(()=>concurrent.assetUrl(value,'b'.repeat(64)),/asset/,'versioning cannot bypass canonical path checks');
 assert.throws(()=>concurrent.assetUrl('runtime/python.zip','forged?redirect=other'),/integrity/);
 const previous=fixture({mutateManifest:manifest=>{delete manifest.build_commit;}});await previous.boot;assert.equal(previous.messages.find(row=>row.type==='ready').build_commit,null,'an older manifest works without inventing a running version');
 const invalidVersion=fixture({mutateManifest:manifest=>{manifest.build_commit='not-a-commit';}});await assert.rejects(invalidVersion.boot,/version/);assert.equal(invalidVersion.runCount,0);
 const badCatalog=fixture({mutateManifest:manifest=>{manifest.catalogs[0].bytes++;}});await assert.rejects(badCatalog.boot,/size mismatch/);assert.equal(badCatalog.runCount,0);assert.equal(badCatalog.writes.size,0);
 let cancelled=false;
 const large=fixture({respond:name=>name==='runtime/python.zip'?new Response(new ReadableStream({start(controller){for(let i=0;i<65;i++)controller.enqueue(new Uint8Array(65536));},cancel(){cancelled=true;}})):undefined});await assert.rejects(large.boot,/too large/);assert(cancelled,'oversize streamed assets are cancelled before concatenation');assert.equal(large.requests.filter(row=>row.name==='runtime/python.zip').length,1);assert.equal(large.runCount,0);
 console.log('Browser worker boot: fresh manifest, reusable SHA URLs, actual running version, canonical boundaries, verified parallel startup, bounded retries/streams/LRU and unchanged dispatch passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
