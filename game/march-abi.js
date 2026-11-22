/* Owned UTF-8 buffers shared by both synchronous WASM callers. */
'use strict';
(function(root){
 function createRawClient(instance){
  const api=instance.exports,encoder=new TextEncoder(),decoder=new TextDecoder();
  for(const name of ['march_alloc','march_call','march_result_len','march_free','march_version'])if(typeof api[name]!=='function')throw new Error('March core export missing: '+name);
  if(!(api.memory instanceof WebAssembly.Memory)||api.march_version()!==1)throw new Error('Unsupported marching core');
  return request=>{
   const bytes=encoder.encode(request),input=api.march_alloc(bytes.length);
   let output=0,length=0;
   try{
    new Uint8Array(api.memory.buffer,input,bytes.length).set(bytes);
    output=api.march_call(input,bytes.length);length=api.march_result_len();
    return decoder.decode(new Uint8Array(api.memory.buffer,output,length));
   }finally{
    if(output&&length)api.march_free(output,length);
    api.march_free(input,bytes.length);
   }
  };
 }
 function createJsonClient(instance){
  const call=createRawClient(instance);
  return request=>{
   const envelope=JSON.parse(call(JSON.stringify(request)));
   if(envelope.ok!==true)throw new Error(envelope.error||'March calculation failed');
   return envelope.value;
  };
 }
 const api={createRawClient,createJsonClient};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.Tk2MarchABI=api;
})(globalThis);
