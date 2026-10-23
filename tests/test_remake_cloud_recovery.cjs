/* Real bundled SDK + controlled Auth replies; no production accounts or mail. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {create}=require('../game/cloud-recovery.js');
const config={enabled:true,url:'https://test-cloud.supabase.co',publishableKey:'sb_publishable_test',slots:5,confirmationRedirectUrl:'http://127.0.0.1:8878/'};
const A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222';
const error=(expected,fn)=>assert.rejects(fn,e=>e.code===expected);
const sdkContext={console,setTimeout,clearTimeout,setInterval,clearInterval,URL,URLSearchParams,Headers,Request,Response,AbortController,AbortSignal,DOMException,TextEncoder,TextDecoder,atob,btoa,performance,structuredClone,WebSocket:globalThis.WebSocket,crypto:globalThis.crypto,fetch:globalThis.fetch};
vm.runInNewContext(fs.readFileSync(require.resolve('../game/vendor/supabase.min.js'),'utf8'),sdkContext);
const sdk=sdkContext.GameSupabase;
assert.equal(typeof sdk.createClient,'function');
(async()=>{
 // A Pages subdirectory must match the explicitly configured callback path.
 const deployed={...config,confirmationRedirectUrl:'https://game.example/Three-Kingdoms2-King-mainland/'};
 assert.equal(create(deployed,{origin:'https://game.example',pathname:'/Three-Kingdoms2-King-mainland/'}).state.enabled,true);
 for(const pathname of ['/','/another-app/','/Three-Kingdoms2-King-mainland/extra/'])
  assert.equal(create(deployed,{origin:'https://game.example',pathname}).state.enabled,false);
 assert.equal(create(deployed,{origin:'https://other.example',pathname:'/Three-Kingdoms2-King-mainland/'}).state.enabled,false);
 // Missing/wrong-origin callback config never falls back to a different app.
 for(const value of [{...config,confirmationRedirectUrl:undefined},{...config,confirmationRedirectUrl:'https://other-app.example/'}]){
  const core=create(value,{origin:'http://127.0.0.1:8878',createClient(){throw Error('must not initialize');}});
  await core.init();assert.equal(core.state.enabled,false);await error('recovery_unavailable',()=>core.request('a@example.test'));
 }
 const storageData=new Map([['tk2-cloud-auth-test-cloud','PRIVATE MAIN SESSION']]),storage={getItem:k=>storageData.get(k)||null,setItem:(k,v)=>storageData.set(k,v),removeItem:k=>storageData.delete(k)};
 const oldFetch=globalThis.fetch,calls=[],user={id:A,email:'a@example.test',aud:'authenticated',role:'authenticated',email_confirmed_at:'2026-10-23T00:00:00Z',app_metadata:{provider:'email'},user_metadata:{}};
 const encode=value=>Buffer.from(JSON.stringify(value)).toString('base64url');
 const jwt=encode({alg:'HS256',typ:'JWT'})+'.'+encode({sub:A,aud:'authenticated',exp:Math.floor(Date.now()/1000)+3600})+'.test';
 const reply=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
 let exchanged=false,updated=false;
 globalThis.fetch=async(input,options={})=>{
  const url=new URL(String(input)),body=options.body?JSON.parse(options.body):null;calls.push({path:url.pathname,method:options.method,body});
  assert.equal(url.origin,config.url);
  if(url.pathname.endsWith('/recover')){assert.equal(body.email,user.email);assert.equal(body.code_challenge_method,'s256');assert(body.code_challenge.length>=40);assert.equal(url.searchParams.get('redirect_to'),config.confirmationRedirectUrl);return reply({});}
  if(url.pathname.endsWith('/token')){assert.equal(url.searchParams.get('grant_type'),'pkce');assert.equal(body.auth_code,'test-recovery-code');assert(body.code_verifier.length>=40);exchanged=true;return reply({access_token:jwt,refresh_token:'fixture-refresh',token_type:'bearer',expires_in:3600,user});}
  if(url.pathname.endsWith('/user')&&options.method==='PUT'){assert(exchanged);assert.equal(body.password,'new-test-password');updated=true;return reply(user);}
  if(url.pathname.endsWith('/user'))return reply(user);
  if(url.pathname.endsWith('/logout'))return reply({});
  throw Error('Unexpected Auth endpoint');
 };
 const createClient=(...args)=>{
  const c=sdk.createClient(...args);
  for(const key of ['signOut','resetPasswordForEmail','exchangeCodeForSession','getUser','updateUser']){
   const method=c.auth[key].bind(c.auth);c.auth[key]=async(...input)=>{try{const result=await method(...input);if(result.error)console.error('Fixture Auth error',key,result.error.message);return result;}catch(e){console.error('Fixture Auth exception',key,e.message);throw e;}};
  }
  return c;
 };
 try{
  let clock=1000;
  const request=create(config,{origin:'http://127.0.0.1:8878',storage,createClient,now:()=>clock});
  await request.init();assert.equal(calls.length,0);await error('invalid',()=>request.request('bad'));
  await request.request(' a@example.test ');assert.equal(request.state.user,null);assert.equal(request.state.retryAt,61000);
  const before=calls.length;await error('rate_limited',()=>request.request(user.email));assert.equal(calls.length,before);
  const recovery=create(config,{origin:'http://127.0.0.1:8878',storage,createClient,callback:{code:'test-recovery-code'}});
  const state=await recovery.init();assert.equal(state.error,null);assert.equal(state.user.id,A);assert(exchanged);
  assert.equal(storageData.get('tk2-cloud-auth-test-cloud'),'PRIVATE MAIN SESSION');
  await error('invalid_password',()=>recovery.update('short'));assert.equal(updated,false);
  await recovery.update('new-test-password');assert(updated);assert.equal(recovery.state.user,null);
  assert.equal(storageData.get('tk2-cloud-auth-test-cloud'),'PRIVATE MAIN SESSION');
  assert.equal(storageData.has('tk2-cloud-recovery-test-cloud'),false);
  await error('recovery_expired',()=>recovery.update('another-password'));
 }finally{globalThis.fetch=oldFetch;}
 // A non-recovery callback and a server-side identity mismatch cannot update.
 for(const [type,verifiedId] of [['signup',A],['recovery',B]]){
  let writes=0;
  const c=create(config,{callback:{code:'test-code'},createClient:()=>({auth:{
   exchangeCodeForSession:async()=>({data:{redirectType:type,session:{user:{id:A}}}}),getUser:async()=>({data:{user:{id:verifiedId,email:'a@example.test'}}}),
   updateUser:async()=>{writes++;return {data:{user:{id:A}}};}
  }})});
  await c.init();assert.equal(c.state.error,'recovery_expired');assert.equal(c.state.user,null);
  await error('recovery_expired',()=>c.update('new-test-password'));assert.equal(writes,0);
 }
 // URL credentials are removed immediately; code and flow id go only to Auth.
 const clean=[],context={URL,window:{CloudSave:{create:()=>({state:{configured:false}})}}};
 context.window.location={href:'http://127.0.0.1:8878/?code=test-callback-code&sb_flow_id=flow1234'};
 context.window.history={state:null,replaceState:(...args)=>clean.push(args)};
 vm.runInNewContext(fs.readFileSync(require.resolve('../game/cloud-recovery.js'),'utf8'),context);
 assert.equal(clean[0][2],'/');
 const disabled=context.window.CloudRecovery.create({});await disabled.init();assert.equal(disabled.state.hasCallback,true);assert.equal(disabled.state.user,null);
 console.log('Password recovery: real SDK PKCE, separate session, email cooldown, verified identity, update/logout, invalid callbacks and URL cleanup passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
