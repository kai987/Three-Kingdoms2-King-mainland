/* Pure marching calculations. This worker never reads or advances game RNG. */
'use strict';
(function(root){
 if(typeof module==='object'&&module.exports){module.exports=require('./march-abi.js');return;}
 importScripts('march-abi.js');
 const {createJsonClient}=root.Tk2MarchABI;
 let core=null,serial=Promise.resolve();
 async function load(){
  if(!core)core=(async()=>{
   const response=await fetch(typeof location==='object'?new URL('wasm/march_core.wasm',location.href).href:'/wasm/march_core.wasm');
   if(!response.ok)throw new Error('March core unavailable');
   const {instance}=await WebAssembly.instantiate(await response.arrayBuffer(),{});
   return createJsonClient(instance);
  })();
  return core;
 }
 root.onmessage=event=>{
  const {id,request}=event.data||{};
  // The raw ABI result length belongs to one call. Keep calls serial even when
  // several route dialogs request previews while a batch is being prepared.
  serial=serial.then(async()=>{
   try{root.postMessage({id,ok:true,value:(await load())(request)});}
   catch(error){root.postMessage({id,ok:false,error:String(error.message||error)});}
  });
 };
})(typeof self==='object'?self:globalThis);
