/* Run Python reference vectors through the exact Worker JSON/WASM transport. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const readline=require('node:readline');
const {createJsonClient}=require('../game/march-worker.js');

(async()=>{
 const root=path.resolve(__dirname,'..');
 const bytes=fs.readFileSync(path.resolve(root,process.env.MARCH_WASM_PATH||'game/wasm/march_core.wasm'));
 const {instance}=await WebAssembly.instantiate(bytes,{}),call=createJsonClient(instance);
 assert.equal(instance.exports.march_version(),1);
 const process_=spawn(process.env.PYTHON||'python3',['-B','tests/test_remake_march_core.py','--wasm-vectors'],
  {cwd:root,stdio:['ignore','pipe','pipe'],env:{...process.env,MARCH_CORE_BACKEND:'python'}});
 let errors='';process_.stderr.on('data',chunk=>errors+=chunk);
 const completion=new Promise((resolve,reject)=>{process_.once('error',reject);process_.once('close',code=>code===0?resolve():reject(new Error(`Python vectors exited${code}: ${errors}`)));});
 let contexts=null,count=0,spellingOnly=0;
 try{
  for await(const line of readline.createInterface({input:process_.stdout,crlfDelay:Infinity})){
   const row=JSON.parse(line);
   if(row.configs){contexts=row.configs.map(data=>call({op:'register',data}));continue;}
   assert.ok(contexts,'Reference configuration header missing');
   const request={...row.request};
   if(request.config!==undefined){request.context=contexts[request.config];delete request.config;}
   // The browser's JSON.stringify intentionally normalizes1.0 to1. Native
   // tests separately cover preservation/rejection of Python numeric spelling.
   if(row.label==='invalid-float-spelling'){spellingOnly++;continue;}
   let actual;
   try{actual={ok:true,value:call(request)};}catch(error){actual={ok:false,error:error.message};}
   try{assert.deepEqual(actual,row.expected);}catch(error){throw new Error(`${row.label}: ${error.message}`,{cause:error});}
   count++;
  }
  await completion;
 }catch(error){process_.kill();await completion.catch(()=>{});throw error;}
 assert.ok(count>10000,`Expected full route/month matrix, got${count}`);
 assert.equal(spellingOnly,1);
 for(const context of contexts){assert.equal(call({op:'unregister',context}),true);assert.equal(call({op:'unregister',context}),false);}
 assert.throws(()=>call({op:'batch',context:contexts[0],cities:[],month:7,discovered:[],player:'none'}),/Unknown march context/);
 assert.throws(()=>call({op:'not-an-operation'}),/Unknown march operation/);
 const before=instance.exports.memory.buffer.byteLength;
 for(let i=0;i<5000;i++)assert.deepEqual(call({op:'allocate',troops:[1,1,1],numerator:1,denominator:3}),[1,0,0]);
 const after=instance.exports.memory.buffer.byteLength;
 assert.ok(after-before<=2*65536,`ABI buffers leaked across5000 calls: ${after-before}bytes`);
 console.log(`Rust/WASM parity: ${count}Python reference vectors passed; raw ABI buffers reused; no RNG/state access.`);
})().catch(error=>{console.error(error);process.exitCode=1;});
