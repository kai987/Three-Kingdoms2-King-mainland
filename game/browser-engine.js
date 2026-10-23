/* Static-host adapter: every tab owns its own campaign Worker, never a public API. */
'use strict';
(function(root){
 const base=new URL('.',document.currentScript.src),network=root.fetch.bind(root);
 // A cached HTML shell or interrupted optional helper must not prevent the
 // language fetches from starting. Keep the same public-asset-only boundary
 // as paths.js; Auth, private configuration and other project URLs pass through.
 if(!root.GamePaths){
  const asset=value=>typeof value==='string'&&(value==='/config/duel-appearances.json'||/^\/(?:assets|locales|wasm|vendor)\//.test(value)||/^\/[A-Za-z0-9-]+\.js$/.test(value))?new URL('.'+value,base).pathname:value;
  root.GamePaths=Object.freeze({asset,base:base.href});
 }

 const pending=new Map();let worker,sequence=0,generation=0,failed=false,ready=false,everReady=false,bootTimer,phase='manifest',progress={},panel,label,retryButton;
 let readyPromise,resolveReady,rejectReady;
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
 }
 const unavailable=()=>new Error('遊戲尚未就緒，請重試載入。／ゲームを読み込めません。再試行してください。');
 function emit(type){document.dispatchEvent(new CustomEvent(type));}
 function fail(token){
  if(token!==generation||failed)return;failed=true;ready=false;clearTimeout(bootTimer);worker?.terminate();status();rejectReady(unavailable());
  for(const row of pending.values())row.reject(unavailable());pending.clear();emit('game-engine-error');
 }
 function start(){
  const token=++generation;failed=false;ready=false;phase='manifest';progress={};
  readyPromise=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});readyPromise.catch(()=>{});
  status();bootTimer=setTimeout(()=>fail(token),180000);
  try{worker=new Worker(new URL('browser-engine-worker.js',base),{type:'module'});}catch{fail(token);return;}
  worker.onerror=()=>fail(token);
  worker.onmessage=event=>{
   if(token!==generation||failed)return;
   const message=event.data||{};
   if(message.type==='progress'&&!ready){
    if(['manifest','loading','initializing'].includes(message.phase)){phase=message.phase;progress=message;status();}return;
   }
   if(message.type==='ready'){ready=true;everReady=true;phase='ready';clearTimeout(bootTimer);status();resolveReady();emit('game-engine-ready');return;}
   if(message.type==='fatal'){fail(token);return;}
   if(message.type!=='response'||!pending.has(message.id))return;
   const request=pending.get(message.id);pending.delete(message.id);
   if(Number.isInteger(message.status)&&message.status>=200&&message.status<600&&typeof message.body==='string')
    request.resolve(new Response(message.body,{status:message.status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}}));
   else request.reject(unavailable());
  };
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
   if(pending.size>=16)return Promise.reject(new Error('操作中です。／請稍候。'));
   const method=(settings.method||'GET').toUpperCase(),body=settings.body??null,id=++sequence;
   return new Promise((resolve,reject)=>{
    pending.set(id,{resolve,reject});
    try{worker.postMessage({type:'request',id,path,method,body,...(typeof settings.tk2ViewCache==='string'?{view_cache:settings.tk2ViewCache}:{})});}catch{pending.delete(id);reject(unavailable());}
   });
  }
  return network(typeof input==='string'?root.GamePaths.asset(input):input,settings);
 };
 root.GameBrowserEngine=Object.freeze({get ready(){return ready;},get failed(){return failed;},get phase(){return phase;},get canRetry(){return failed&&!everReady;},retry,whenReady:()=>failed?Promise.reject(unavailable()):readyPromise});
 start();
})(window);
