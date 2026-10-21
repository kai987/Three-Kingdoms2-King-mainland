/* Pure marching calculations. This worker never reads or advances game RNG. */
'use strict';
(function(root){
 function createJsonClient(instance){
  const api=instance.exports,encoder=new TextEncoder(),decoder=new TextDecoder();
  for(const name of ['march_alloc','march_call','march_result_len','march_free','march_version'])if(typeof api[name]!=='function')throw new Error('March core export missing: '+name);
  if(!(api.memory instanceof WebAssembly.Memory)||api.march_version()!==1)throw new Error('Unsupported marching core');
  return request=>{
   const bytes=encoder.encode(JSON.stringify(request)),input=api.march_alloc(bytes.length);
   let output=0,length=0;
   try{
    new Uint8Array(api.memory.buffer,input,bytes.length).set(bytes);
    output=api.march_call(input,bytes.length);length=api.march_result_len();
    const envelope=JSON.parse(decoder.decode(new Uint8Array(api.memory.buffer,output,length)));
    if(envelope.ok!==true)throw new Error(envelope.error||'March calculation failed');
    return envelope.value;
   }finally{
    if(output&&length)api.march_free(output,length);
    api.march_free(input,bytes.length);
   }
  };
 }
 if(typeof module==='object'&&module.exports){module.exports={createJsonClient};return;}
 let core=null,serial=Promise.resolve();
 async function load(){
  if(!core)core=(async()=>{
   const response=await fetch('/wasm/march_core.wasm');
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
