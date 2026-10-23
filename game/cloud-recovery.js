/* Password recovery has a separate PKCE client; it never imports a game login. */
'use strict';
(function(root){
 const saveApi=root.CloudSave||(typeof module==='object'&&module.exports?require('./cloud-save.js'):null);
 const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 const fail=code=>{const e=new Error(code);e.code=code;throw e;};
 function callbackFrom(location,history){
  if(!location?.href)return null;
  try{
   const url=new URL(location.href),codes=url.searchParams.getAll('code');
   if(!codes.length)return null;
   const flows=url.searchParams.getAll('sb_flow_id');
   const valid=codes.length===1&&/^[a-zA-Z0-9_-]{8,512}$/.test(codes[0])&&flows.length<=1&&(!flows.length||/^[a-zA-Z0-9_-]{1,128}$/.test(flows[0]));
   url.searchParams.delete('code');url.searchParams.delete('sb_flow_id');
   history?.replaceState(history.state,'',url.pathname+url.search+url.hash);
   return valid?{code:codes[0],flowId:flows[0]||null}:{invalid:true};
  }catch{return {invalid:true};}
 }
 const initialCallback=callbackFrom(root.location,root.history);
 function mapped(error){
  const code=error?.code,status=Number(error?.status||0);
  if(['invalid','busy','recovery_unavailable','recovery_expired','session_changed','network'].includes(code))return code;
  if(status===429||/rate_limit/.test(code||''))return 'rate_limited';
  if(code==='same_password')return 'password_unchanged';
  if(code==='weak_password')return 'invalid_password';
  if(status===401||/expired|flow_state|pkce|code_verifier|bad_code|session_not_found/.test(code||''))return 'recovery_expired';
  return status>=500||error instanceof TypeError||['AuthRetryableFetchError','AbortError','TimeoutError'].includes(error?.name)?'network':'recovery_expired';
 }
 function create(config,options={}){
  const configured=!!saveApi?.create(config).state.configured;
  const redirect=configured&&config.confirmationRedirectUrl?new URL(config.confirmationRedirectUrl):null;
  const origin=options.origin||root.location?.origin;
  const pathname=options.pathname||root.location?.pathname||'/';
  const enabled=!!redirect&&(!origin||redirect.origin===origin)&&redirect.pathname===pathname&&redirect.pathname.endsWith('/')&&!redirect.search;
  const callback=options.callback===undefined?initialCallback:options.callback;
  const listeners=new Set();let client=null,ready=false,busy=false,user=null,error=null,retryAt=0,initialized=null,consumed=false;
  const now=()=>typeof options.now==='function'?options.now():Date.now();
  const state=()=>Object.freeze({enabled,ready,busy,user:user?Object.freeze({...user}):null,error,retryAt,hasCallback:!!callback});
  const notify=()=>{for(const fn of listeners){try{fn(state());}catch{}}};
  const timeoutMs=Number.isInteger(options.timeoutMs)&&options.timeoutMs>0&&options.timeoutMs<=60000?options.timeoutMs:20000;
  async function bounded(promise){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Object.assign(new Error('network'),{code:'network'})),timeoutMs);})]);}finally{clearTimeout(timer);}}
  function ensure(){
   if(!enabled)fail('recovery_unavailable');
   if(!client){
    const factory=options.createClient||root.GameSupabase?.createClient;if(typeof factory!=='function')fail('recovery_unavailable');
    client=factory(config.url,config.publishableKey,{global:{fetch:async(input,settings={})=>{
     const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
     try{return await root.fetch(input,{...settings,signal:controller.signal});}finally{clearTimeout(timer);}
    }},auth:{storageKey:'tk2-cloud-recovery-'+new URL(config.url).hostname.split('.')[0],
     flowType:'pkce',persistSession:true,autoRefreshToken:false,detectSessionInUrl:false,...(options.storage?{storage:options.storage}:{})}});
   }
   return client;
  }
  async function call(work){
   if(busy)fail('busy');busy=true;error=null;notify();
   try{return await work();}catch(e){const code=mapped(e);error=code;fail(code);}finally{busy=false;notify();}
  }
  async function verified(c,id){
   const result=await bounded(c.auth.getUser());if(result.error)throw result.error;
   const u=result.data?.user;if(!u||!UUID.test(u.id)||u.id!==id||typeof u.email!=='string')fail('recovery_expired');
   return {id:u.id,email:u.email};
  }
  async function init(){
   if(ready)return state();if(initialized){await initialized;return state();}
   initialized=(async()=>{
    try{
     if(callback&&!consumed){consumed=true;await call(async()=>{
      if(callback.invalid)fail('recovery_expired');
      const c=ensure(),result=await bounded(c.auth.exchangeCodeForSession(callback.code,callback.flowId?{flowId:callback.flowId}:undefined));
      if(result.error)throw result.error;
      if(result.data?.redirectType!=='recovery'||!result.data.session?.user?.id)fail('recovery_expired');
      user=await verified(c,result.data.session.user.id);
     });}
    }catch{/* The UI exposes only the stable recovery error, never provider text. */}
    finally{ready=true;notify();}
   })();await initialized;return state();
  }
  async function request(email){
   if(typeof email!=='string'||email.length>254||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))fail('invalid');
   if(user)fail('busy');if(now()<retryAt)fail('rate_limited');
   return call(async()=>{
    const c=ensure();
    const signedOut=await bounded(c.auth.signOut({scope:'local'}));if(signedOut.error)throw signedOut.error;
    retryAt=now()+60000;
    const result=await bounded(c.auth.resetPasswordForEmail(email.trim(),{redirectTo:redirect.href}));if(result.error)throw result.error;
    return {requested:true};
   });
  }
  async function update(password){
   if(typeof password!=='string'||password.length<8||password.length>256)fail('invalid_password');
   const captured=user;if(!captured)fail('recovery_expired');
   return call(async()=>{
    const c=ensure();await verified(c,captured.id);if(user!==captured)fail('session_changed');
    const result=await bounded(c.auth.updateUser({password}));if(result.error)throw result.error;
    if(result.data?.user?.id!==captured.id)fail('session_changed');
    user=null;
    // A password update is successful even if subsequent session cleanup is offline.
    try{await bounded(c.auth.signOut({scope:'local'}));}catch{}
    return {passwordUpdated:true};
   });
  }
  async function cancel(){return call(async()=>{
   if(client){const result=await bounded(client.auth.signOut({scope:'local'}));if(result.error)throw result.error;}
   user=null;error=null;
  });}
  return Object.freeze({get state(){return state();},init,request,update,cancel,subscribe(fn){listeners.add(fn);fn(state());return()=>listeners.delete(fn);}});
 }
 const api={create};if(typeof module==='object'&&module.exports)module.exports=api;else root.CloudRecovery=api;
})(typeof window==='object'?window:globalThis);
