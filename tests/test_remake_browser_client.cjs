'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const scripts=['paths.js','browser-engine.js'].map(name=>fs.readFileSync(require('node:path').join(__dirname,'../game',name),'utf8'));
function fixture(prefix='/Three-Kingdoms2-King-mainland/'){
 const requests=[],workers=[],timers=[],node={textContent:'',classList:{toggle(){}}};
 const document={currentScript:{src:'https://game.example'+prefix+'paths.js'},readyState:'complete',querySelector:()=>node};
 class Worker{
  constructor(url,options){this.url=String(url);this.options=options;this.messages=[];workers.push(this);}
  postMessage(message){this.messages.push(message);}
  terminate(){this.stopped=true;}
  respond(message){this.onmessage({data:message});}
 }
 const window={document,Worker,fetch:(...args)=>{requests.push(args);return Promise.resolve(new Response('{}'));}};
 const context={window,document,Worker,URL,Response,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){},console};
 vm.createContext(context);for(const script of scripts)vm.runInContext(script,context);
 return{window,requests,worker:workers[0],timers,node};
}
(async()=>{
 const e=fixture();assert.equal(e.worker.url,'https://game.example/Three-Kingdoms2-King-mainland/browser-engine-worker.js');assert.equal(e.worker.options.type,'module');
 assert.equal(e.window.GamePaths.asset('/assets/map.png'),'/Three-Kingdoms2-King-mainland/assets/map.png');
 assert.equal(e.window.GamePaths.asset('/config/duel-appearances.json'),'/Three-Kingdoms2-King-mainland/config/duel-appearances.json');
 assert.equal(e.window.GamePaths.asset('/config/cloud-save-public.json'),'/config/cloud-save-public.json','Private configuration paths are never remapped');
 for(const path of ['https://auth.example/token','//other.example/file','#sprite','/another-project/file'])assert.equal(e.window.GamePaths.asset(path),path);
 await e.window.fetch('/assets/portraits/index.json');assert.equal(e.requests[0][0],'/Three-Kingdoms2-King-mainland/assets/portraits/index.json');
 await e.window.fetch('https://auth.example/token',{method:'POST',body:'private-auth-request'});assert.equal(e.requests[1][0],'https://auth.example/token');
 await e.window.fetch('/api/cloud-config');assert.equal(String(e.requests[2][0]),'https://game.example/Three-Kingdoms2-King-mainland/cloud-config.json');
 const count=e.requests.length,pending=e.window.fetch('/api/state');assert.equal(e.requests.length,count,'Game state is never sent to a public shared server');
 const request=e.worker.messages.at(-1);assert.equal(request.method,'GET');assert.equal(request.body,null);
 e.worker.respond({type:'response',id:request.id,status:200,body:'{"revision":4,"game":null}'});const response=await pending;assert.equal((await response.json()).revision,4);
 const raw='{ "kind": "allocate", "payload": {"troops":999}, "revision":4 }',command=e.window.fetch('/api/command',{method:'POST',body:raw});assert.equal(e.worker.messages.at(-1).body,raw,'JSON text is not rewritten before the Python boundary');
 e.worker.respond({type:'response',id:e.worker.messages.at(-1).id,status:409,body:'{"error":"stale revision"}'});assert.equal((await command).status,409);
 e.worker.respond({type:'ready'});assert(e.window.GameBrowserEngine.ready);assert.equal(e.node.textContent,'');
 const failed=fixture('/'),waiting=failed.window.fetch('/api/state');failed.worker.respond({type:'fatal'});await assert.rejects(waiting);assert(failed.worker.stopped);await assert.rejects(failed.window.fetch('/api/state'));
 const isolated=fixture();assert.equal(isolated.worker.messages.length,0,'Each window owns a separate campaign Worker');
 console.log('Browser client: project-prefix assets, unchanged external Auth, tab isolation, fixed local API dispatch, raw command bytes, revision errors and boot failure passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
