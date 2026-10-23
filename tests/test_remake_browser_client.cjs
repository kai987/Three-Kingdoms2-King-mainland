'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const scripts=['paths.js','browser-engine.js'].map(name=>fs.readFileSync(require('node:path').join(__dirname,'../game',name),'utf8'));
function fixture(prefix='/Three-Kingdoms2-King-mainland/',{paths=true}={}){
 const requests=[],workers=[],timers=[],nodes=new Map(),events=[],listeners=new Map();
 function element(tag='p'){
  const node={tagName:tag.toUpperCase(),textContent:'',hidden:false,disabled:false,attributes:{},style:{},children:[],classList:{toggle(){}},setAttribute(name,value){this.attributes[name]=value;},append(...children){this.children.push(...children);},insertAdjacentElement(where,value){nodes.set(value.id,value);}};return node;
 }
 const node=element();nodes.set('notice',node);
 const document={currentScript:{src:'https://game.example'+prefix+'paths.js'},readyState:'complete',querySelector:selector=>nodes.get(selector.slice(1)),createElement:element,addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,[]);listeners.get(type).push(fn);},dispatchEvent(event){events.push(event.type);for(const fn of listeners.get(event.type)||[])fn(event);}};
 class Worker{
  constructor(url,options){this.url=String(url);this.options=options;this.messages=[];workers.push(this);}
  postMessage(message){this.messages.push(message);}
  terminate(){this.stopped=true;}
  respond(message){this.onmessage({data:message});}
 }
 const window={document,Worker,fetch:(...args)=>{requests.push(args);return Promise.resolve(new Response('{}'));}};
 const context={window,document,Worker,URL,Response,CustomEvent:class{constructor(type){this.type=type;}},setTimeout:(fn,ms)=>{const timer={fn,ms};timers.push(timer);return timer;},clearTimeout:timer=>{if(timer)timer.cancelled=true;},console};
 vm.createContext(context);for(const script of paths?scripts:scripts.slice(1))vm.runInContext(script,context);
 return{window,requests,worker:workers[0],workers,timers,node,nodes,events,document};
}
(async()=>{
 for(const prefix of ['/nested-game/','/']){
  const fallback=fixture(prefix,{paths:false});
  await fallback.window.fetch('/locales/zh-hant.json');
  assert.equal(fallback.requests[0][0],prefix+'locales/zh-hant.json','Missing optional path helper still loads language data under the project prefix');
  assert(Object.isFrozen(fallback.window.GamePaths));
  for(const path of ['https://auth.example/token','/config/cloud-save-public.json','/another-project/file'])assert.equal(fallback.window.GamePaths.asset(path),path);
 }
 const e=fixture();assert.equal(e.worker.url,'https://game.example/Three-Kingdoms2-King-mainland/browser-engine-worker.js');assert.equal(e.worker.options.type,'module');
 assert.equal(e.window.GamePaths.asset('/assets/map.png'),'/Three-Kingdoms2-King-mainland/assets/map.png');
 assert.equal(e.window.GamePaths.asset('/config/duel-appearances.json'),'/Three-Kingdoms2-King-mainland/config/duel-appearances.json');
 assert.equal(e.window.GamePaths.asset('/config/cloud-save-public.json'),'/config/cloud-save-public.json','Private configuration paths are never remapped');
 for(const path of ['https://auth.example/token','//other.example/file','#sprite','/another-project/file'])assert.equal(e.window.GamePaths.asset(path),path);
 await e.window.fetch('/assets/portraits/index.json');assert.equal(e.requests[0][0],'/Three-Kingdoms2-King-mainland/assets/portraits/index.json');
 await e.window.fetch('https://auth.example/token',{method:'POST',body:'private-auth-request'});assert.equal(e.requests[1][0],'https://auth.example/token');
 await e.window.fetch('/api/cloud-config');assert.equal(String(e.requests[2][0]),'https://game.example/Three-Kingdoms2-King-mainland/cloud-config.json');
 const count=e.requests.length,pending=e.window.fetch('/api/state');assert.equal(e.requests.length,count,'Game state is never sent to a public shared server');
 const request=e.worker.messages.at(-1);assert.equal(request.method,'GET');assert.equal(request.body,null);assert(!Object.hasOwn(request,'view_cache'),'legacy callers do not opt into compact transport');
 e.worker.respond({type:'response',id:request.id,status:200,body:'{"revision":4,"game":null}'});const response=await pending;assert.equal((await response.json()).revision,4);
 const raw='{ "kind": "allocate", "payload": {"troops":999}, "revision":4 }',command=e.window.fetch('/api/command',{method:'POST',body:raw});assert.equal(e.worker.messages.at(-1).body,raw,'JSON text is not rewritten before the Python boundary');
 e.worker.respond({type:'response',id:e.worker.messages.at(-1).id,status:409,body:'{"error":"stale revision"}'});assert.equal((await command).status,409);
 const firstCompact=e.window.fetch('/api/state',{tk2ViewCache:''}),firstCompactMessage=e.worker.messages.at(-1);
 assert.equal(firstCompactMessage.view_cache,'','an explicit empty token negotiates the first compact response');
 const compactBody='{ "revision": 4, "view_cache": {"token":"catalog-token-1","catalog":{}} }';
 e.worker.respond({type:'response',id:firstCompactMessage.id,status:200,body:compactBody});assert.equal(await(await firstCompact).text(),compactBody,'adapter preserves the Worker response JSON bytes');
 const nextCompact=e.window.fetch('/api/command',{method:'POST',body:raw,tk2ViewCache:'catalog-token-1'}),nextCompactMessage=e.worker.messages.at(-1);
 assert.equal(nextCompactMessage.view_cache,'catalog-token-1');assert.equal(nextCompactMessage.body,raw,'cache negotiation never rewrites mutating JSON');
 e.worker.respond({type:'response',id:nextCompactMessage.id,status:200,body:'{}'});await nextCompact;
 for(const settings of [{},{tk2ViewCache:null},{tk2ViewCache:42},{tk2ViewCache:false}]){
  const legacy=e.window.fetch('/api/state',settings),message=e.worker.messages.at(-1);assert(!Object.hasOwn(message,'view_cache'),'cache metadata requires an explicit string option on each request');
  e.worker.respond({type:'response',id:message.id,status:200,body:'{}'});await legacy;
 }

 const panel=e.nodes.get('game-engine-status'),[label,retry]=panel.children;
 assert(label.textContent.includes('版本清單'));assert(retry.hidden);
 e.worker.respond({type:'progress',phase:'loading',receivedBytes:2048,runtimeReady:false});assert(label.textContent.includes('2.0 KiB'));assert(label.textContent.includes('不含執行環境'));assert(!label.textContent.includes('%'),'unknown Pyodide download progress never invents percentages');
 e.window.GameI18n={locale:'ja'};e.document.dispatchEvent({type:'game-language-change'});assert(label.textContent.includes('実行環境'));assert(label.textContent.includes('実行環境を除く'));assert.equal(retry.textContent,'読み込みを再試行');
 e.worker.respond({type:'ready'});await e.window.GameBrowserEngine.whenReady();assert(e.window.GameBrowserEngine.ready);assert(panel.hidden);assert(e.events.includes('game-engine-ready'));
 assert.equal(e.window.GameBrowserEngine.retry(),false,'A running campaign is never replaced by a retry');
 const failed=fixture('/'),waiting=failed.window.fetch('/api/state'),write=failed.window.fetch('/api/command',{method:'POST',body:raw}),boot=failed.window.GameBrowserEngine.whenReady();
 failed.worker.respond({type:'fatal'});await Promise.all([assert.rejects(waiting),assert.rejects(write),assert.rejects(boot)]);assert(failed.worker.stopped);await assert.rejects(failed.window.fetch('/api/state'));
 const failurePanel=failed.nodes.get('game-engine-status');assert.equal(failed.window.GameBrowserEngine.canRetry,true);assert(!failurePanel.children[1].hidden);
 failed.node.textContent='app.js failure notice';assert(failurePanel.children[0].textContent.includes('載入失敗'),'app notices cannot remove the retry surface');
 failurePanel.children[1].onclick();assert.equal(failed.workers.length,2);assert.equal(failed.workers[1].messages.length,0,'Neither reads nor mutating commands are silently replayed');assert.equal(failed.window.GameBrowserEngine.failed,false);assert(failurePanel.children[1].hidden);
 failed.worker.respond({type:'ready'});assert(!failed.window.GameBrowserEngine.ready,'Messages from a terminated boot are ignored');
 failed.workers[1].respond({type:'ready'});await failed.window.GameBrowserEngine.whenReady();assert(failed.window.GameBrowserEngine.ready);
 failed.workers[1].onerror();assert.equal(failed.window.GameBrowserEngine.canRetry,false);assert(failurePanel.children[1].hidden);assert.equal(failed.window.GameBrowserEngine.retry(),false);assert.equal(failed.workers.length,2,'An error after ready cannot destroy and replace a campaign');await assert.rejects(failed.window.GameBrowserEngine.whenReady());
 const timeout=fixture();timeout.timers[0].fn();assert(timeout.window.GameBrowserEngine.failed);assert.equal(timeout.window.GameBrowserEngine.canRetry,true);assert.equal(timeout.timers[0].ms,180000);
 const isolated=fixture();assert.equal(isolated.worker.messages.length,0,'Each window owns a separate campaign Worker');
 console.log('Browser client: prefix/Auth/raw JSON and opt-in compact-token contracts, real-byte bilingual boot feedback, bounded boot, explicit pre-ready retry, stale-worker isolation and no running-campaign reset passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
