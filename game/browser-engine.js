/* Static-host adapter: every tab owns its own campaign Worker, never a public API. */
'use strict';
(function(root){
 const base=new URL('.',document.currentScript.src),network=root.fetch.bind(root);
 const worker=new Worker(new URL('browser-engine-worker.js',base),{type:'module'});
 const pending=new Map();let sequence=0,failed=false,ready=false,bootTimer;
 function status(error=false){
  const node=document.querySelector('#notice');if(!node)return;
  node.classList.toggle('error',error);
  node.textContent=error?'遊戲載入失敗，請重新整理後再試。／ゲームを読み込めません。再読み込みしてください。':
   ready?'':'首次載入需下載遊戲資料，請稍候。／初回はゲームデータをダウンロードします。しばらくお待ちください。';
 }
 const unavailable=()=>new Error('遊戲尚未就緒，請重新整理後再試。／ゲームを再読み込みしてください。');
 function fail(){
  if(failed)return;failed=true;clearTimeout(bootTimer);worker.terminate();status(true);
  for(const row of pending.values())row.reject(unavailable());pending.clear();
 }
 worker.onerror=fail;
 worker.onmessage=event=>{
  const message=event.data||{};
  if(message.type==='ready'){ready=true;clearTimeout(bootTimer);status();return;}
  if(message.type==='fatal'){fail();return;}
  if(message.type!=='response'||!pending.has(message.id))return;
  const request=pending.get(message.id);pending.delete(message.id);
  if(Number.isInteger(message.status)&&message.status>=200&&message.status<600&&typeof message.body==='string')
   request.resolve(new Response(message.body,{status:message.status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}}));
  else request.reject(unavailable());
 };
 bootTimer=setTimeout(fail,180000);
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>status(failed),{once:true});else status();
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
    try{worker.postMessage({type:'request',id,path,method,body});}catch{pending.delete(id);reject(unavailable());}
   });
  }
  return network(typeof input==='string'?root.GamePaths.asset(input):input,settings);
 };
 root.GameBrowserEngine=Object.freeze({get ready(){return ready;},get failed(){return failed;}});
})(window);
