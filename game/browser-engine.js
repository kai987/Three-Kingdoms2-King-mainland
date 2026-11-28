/* Static-host adapter: every tab owns its own campaign Worker, never a public API. */
'use strict';
(function(root){
 const entry=document.currentScript,base=new URL('.',entry.src),network=root.fetch.bind(root);
 const workerVersion=entry.dataset?.workerSha256;
 const recoveryTimeout=30_000;
 // A cached HTML shell or interrupted optional helper must not prevent the
 // language fetches from starting. Keep the same public-asset-only boundary
 // as paths.js; Auth, private configuration and other project URLs pass through.
 if(!root.GamePaths){
  const asset=value=>typeof value==='string'&&(['/config/duel-appearances.json','/config/battlefield-city-bindings.json'].includes(value)||/^\/(?:assets|locales|wasm|vendor)\//.test(value)||/^\/[A-Za-z0-9-]+\.js$/.test(value))?new URL('.'+value,base).pathname:value;
  root.GamePaths=Object.freeze({asset,base:base.href});
 }

 const pending=new Map();let worker,sequence=0,generation=0,failed=false,ready=false,everReady=false,bootTimer,phase='manifest',progress={},panel,label,retryButton,version='',versionLabel,sharedScenarios=false;
 let readyPromise,resolveReady,rejectReady,recovering=false;
 const copy={
  'zh-Hant':{manifest:'讀取遊戲版本清單……',loading:'下載遊戲資料並準備執行環境……',initializing:'初始化戰役規則……',failed:'遊戲載入失敗。請檢查連線，再重試載入。',stopped:'遊戲執行已中斷。請重新整理頁面，並讀取已儲存的進度。',retry:'重試載入',runtime:'執行環境',working:'準備中',done:'已就緒',bytes:'遊戲資料已讀取',excludes:'不含執行環境',retrying:'正在重試下載'},
  ja:{manifest:'ゲームのバージョン情報を確認しています……',loading:'ゲームデータのダウンロードと実行環境の準備中です……',initializing:'戦役ルールを初期化しています……',failed:'ゲームを読み込めません。接続を確認して、もう一度お試しください。',stopped:'ゲームの実行が中断されました。ページを再読み込みし、保存済みの進行状況を読み込んでください。',retry:'読み込みを再試行',runtime:'実行環境',working:'準備中',done:'準備完了',bytes:'ゲームデータの読み込み量',excludes:'実行環境を除く',retrying:'ダウンロードを再試行中'}
 };
 function status(){
  if(!panel){
   const notice=document.querySelector('#notice');if(!notice)return;
   panel=document.createElement('p');panel.id='game-engine-status';panel.setAttribute('role','status');panel.setAttribute('aria-live','polite');
   panel.style.cssText='grid-area:notice;padding:8px 16px;background:var(--paper,#ffd4c8);border:2px solid #000;display:flex;flex-wrap:wrap;gap:12px;align-items:center';
   label=document.createElement('span');label.style.whiteSpace='pre-line';
   retryButton=document.createElement('button');retryButton.type='button';retryButton.onclick=()=>retry();
   panel.append(label,retryButton);notice.insertAdjacentElement('afterend',panel);
  }
  const locale=root.GameI18n?.locale==='ja'?'ja':'zh-Hant',words=copy[locale];panel.setAttribute('data-l10n-native',locale);
  panel.hidden=ready;panel.style.display=ready?'none':'flex';panel.classList.toggle('error',failed);
  retryButton.textContent=words.retry;retryButton.hidden=!failed||everReady;retryButton.disabled=!failed||everReady;
  label.textContent=failed?(everReady?words.stopped:words.failed):words[phase]||words.loading;
  if(!failed&&phase==='loading'){
   label.textContent+=`\n${words.runtime}：${progress.runtimeReady?words.done:words.working}`;
   if(Number.isSafeInteger(progress.receivedBytes)&&progress.receivedBytes>0)label.textContent+=` · ${words.bytes} ${(progress.receivedBytes/1024).toFixed(1)} KiB（${words.excludes}）`;
   if(progress.retrying)label.textContent+=` · ${words.retrying}`;
  }
  root.GameLoadingCover?.attachStatus?.(panel);
  root.GameLoadingCover?.update?.({phase,ready,failed,canRetry:failed&&!everReady,...progress,version});
  if(version){
   const host=document.querySelector('#utility-menu .utility-panel');
   if(host&&!versionLabel){versionLabel=document.createElement('small');versionLabel.id='game-build-version';host.append(versionLabel);}
   if(versionLabel){versionLabel.textContent=(locale==='ja'?'バージョン ':'版本 ')+version.slice(0,7);versionLabel.setAttribute('data-l10n-native',locale);}
   document.documentElement?.setAttribute('data-game-build',version);
  }
 }
 const unavailable=()=>new Error('遊戲尚未就緒，請重試載入。／ゲームを読み込めません。再試行してください。');
 function emit(type){document.dispatchEvent(new CustomEvent(type));}
 function fail(token){
  if(token!==generation||failed)return;failed=true;ready=false;clearTimeout(bootTimer);worker?.terminate();status();rejectReady(unavailable());
  for(const row of pending.values())row.reject(unavailable());pending.clear();emit('game-engine-error');
 }
 function newWorker(){
  const address=new URL('browser-engine-worker.js',base);
  if(/^[a-f0-9]{64}$/.test(workerVersion||''))address.searchParams.set('v',workerVersion);
  return new Worker(address,{type:'module'});
 }
 function receiveResponse(requests,message){
  if(message.type!=='response'||!requests.has(message.id))return;
  const request=requests.get(message.id);
  if(Number.isInteger(message.status)&&message.status>=200&&message.status<600&&typeof message.body==='string')
   request.resolve(new Response(message.body,{status:message.status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}}));
  else request.reject(unavailable());
 }
 function sendRequest(target,requests,request,signal){
  return new Promise((resolve,reject)=>{
   if(signal?.aborted){reject(unavailable());return;}
   const id=++sequence;
   const cleanup=()=>{
    requests.delete(id);
    signal?.removeEventListener('abort',abort);
   };
   const abort=()=>{cleanup();reject(unavailable());};
   requests.set(id,{
    resolve:reply=>{cleanup();resolve(reply);},
    reject:error=>{cleanup();reject(error);}
   });
   signal?.addEventListener('abort',abort,{once:true});
   try{target.postMessage({type:'request',id,...request});}catch{abort();}
  });
 }
 function listenActive(target,token){
  target.onerror=()=>fail(token);
  target.onmessage=event=>{
   if(token!==generation||failed)return;
   const message=event.data||{};
   if(message.type==='progress'&&!ready){
    if(['manifest','loading','initializing'].includes(message.phase)){phase=message.phase;progress=message;status();}return;
   }
   if(message.type==='ready'){ready=true;everReady=true;phase='ready';sharedScenarios=message.shared_scenarios===true;version=/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/.test(message.build_commit||'')?message.build_commit:'';clearTimeout(bootTimer);status();resolveReady();emit('game-engine-ready');return;}
   if(message.type==='fatal'){fail(token);return;}
   receiveResponse(pending,message);
  };
 }
 function start(){
  const token=++generation;failed=false;ready=false;phase='manifest';progress={};version='';sharedScenarios=false;
  readyPromise=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});readyPromise.catch(()=>{});
  status();bootTimer=setTimeout(()=>fail(token),180000);
  try{worker=newWorker();listenActive(worker,token);}catch{fail(token);}
 }
 function waitForReplacement(target,requests,controller){
  const signal=controller.signal;
  return new Promise((resolve,reject)=>{
   const abort=()=>reject(unavailable());
   signal.addEventListener('abort',abort,{once:true});
   target.onerror=()=>controller.abort();
   target.onmessage=event=>{
    const message=event.data||{};
    if(message.type==='fatal'){controller.abort();return;}
    if(message.type==='ready'){
     signal.removeEventListener('abort',abort);
     resolve(message);
     return;
    }
    receiveResponse(requests,message);
   };
  });
 }
 function observerCheckpoint(game,turn){
  return game?.player==='observer'&&(game.turn===turn||game.turn===turn+1)
   &&(game.phase==='city'||game.phase==='finished');
 }
 async function recoverObserver(failure,active,request,turn){
  if(!ready||failed||!version||recovering||pending.size||worker!==active)return failure;
  recovering=true;
  const controller=new AbortController();
  const signal=controller.signal;
  const timeout=setTimeout(()=>controller.abort(),recoveryTimeout);
  const requests=new Map();
  let replacement;
  try{
   const command=JSON.parse(request.body);
   if(command?.kind!=='observe_turn')return failure;
   const snapshot=await sendRequest(active,pending,{path:'/api/save?compact=1',method:'GET',body:null},signal);
   if(!snapshot.ok)return failure;
   const raw=await snapshot.text();
   const save=JSON.parse(raw);
   if(!observerCheckpoint(save.state,turn))return failure;

   // Keep the current Worker alive until the same build has verified the save and the outcome.
   replacement=newWorker();
   const hello=await waitForReplacement(replacement,requests,controller);
   if(hello.build_commit!==version||(hello.shared_scenarios===true)!==sharedScenarios)return failure;
   const viewCache=typeof request.view_cache==='string'?{view_cache:request.view_cache}:{};
   // A newly booted Worker has an empty session at revision zero.
   const restored=await sendRequest(replacement,requests,{path:'/api/load',method:'POST',
    body:root.SaveTransfer.loadBody(raw,0),...viewCache},signal);
   if(!restored.ok)return failure;
   const state=await restored.clone().json();
   const view=state.view??state;
   if(view.game?.turn!==save.state.turn||view.game.phase!==save.state.phase||
      view.game.player!=='observer'||!Number.isSafeInteger(view.revision))return failure;

   let result=restored;
   if(save.state.turn===turn&&save.state.phase==='city'){
    result=await sendRequest(replacement,requests,{...request,
     body:JSON.stringify({...command,revision:view.revision})},signal);
    if(!result.ok)return failure;
    const data=await result.clone().json();
    const game=(data.view??data).game;
    if(!observerCheckpoint(game,turn)||(game.turn===turn&&game.phase!=='finished'))return failure;
   }
   if(signal.aborted||worker!==active||failed)return failure;
   listenActive(replacement,++generation);
   worker=replacement;
   active.terminate();
   return result;
  }catch{
   return failure;
  }finally{
   clearTimeout(timeout);
   if(replacement&&replacement!==worker)replacement.terminate();
   recovering=false;
  }
 }
 function retry(){if(!failed||everReady)return false;start();return true;}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',status,{once:true});
 document.addEventListener('game-language-change',status);
 function apiPath(input){
  if(typeof input==='string'&&input.startsWith('/api/'))return input;
  const url=new URL(typeof input==='string'?input:input.url,base);
  return url.origin===base.origin&&url.pathname.startsWith(base.pathname+'api/')?'/'+url.pathname.slice(base.pathname.length)+url.search:null;
 }
 root.fetch=function(input,settings={}){
  let path;try{path=apiPath(input);}catch{return network(input,settings);}
  if(path==='/api/cloud-config')return network(new URL('cloud-config.json',base),settings);
  if(path){
   if(failed)return Promise.reject(unavailable());
   if(recovering||pending.size>=16)return Promise.reject(new Error('操作中です。／請稍候。'));
   const method=(settings.method||'GET').toUpperCase(),body=settings.body??null;
   const request={path,method,body,...(typeof settings.tk2ViewCache==='string'?{view_cache:settings.tk2ViewCache}:{})};
   const active=worker;
   const response=sendRequest(active,pending,request);
   const turn=settings.tk2ObserverTurn;
   if(path==='/api/command'&&method==='POST'&&Number.isSafeInteger(turn)&&turn>=1)
    return response.then(reply=>reply.status===500?recoverObserver(reply,active,request,turn):reply);
   return response;
  }
  return network(typeof input==='string'?root.GamePaths.asset(input):input,settings);
 };
 root.GameBrowserEngine=Object.freeze({get ready(){return ready;},get failed(){return failed;},get phase(){return phase;},get sharedScenarios(){return sharedScenarios;},get version(){return version;},get canRetry(){return failed&&!everReady;},retry,whenReady:()=>failed?Promise.reject(unavailable()):readyPromise});
 start();
})(window);
