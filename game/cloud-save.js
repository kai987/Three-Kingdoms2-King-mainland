/* Account-private raw-text saves. Game state and RNG stay in the existing engine. */
'use strict';
(function(root){
 const TABLE='tk2_cloud_saves',MAX_BYTES=2*1024*1024-128;
 const META='save_id,slot,label,revision,scenario,game_year,game_month,game_turn,save_sha256,created_at,updated_at';
 const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 const HEX=/^[0-9a-f]{64}$/;
 class CloudError extends Error{
  constructor(code){super(code);this.name='CloudSaveError';this.code=code;}
 }
 const fail=code=>{throw new CloudError(code);};
 function publicKey(key){
  if(typeof key!=='string')return false;
  if(/^sb_publishable_[a-zA-Z0-9_-]+$/.test(key))return true;
  try{return JSON.parse(root.atob(key.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).role==='anon';}catch{return false;}
 }
 function validConfig(config){
  try{const url=new URL(config?.url);return config.enabled===true&&config.slots===5&&
   url.protocol==='https:'&&/^[a-z0-9-]+\.supabase\.co$/.test(url.hostname)&&
   !url.username&&!url.password&&!url.port&&!url.search&&!url.hash&&url.pathname==='/'&&publicKey(config.publishableKey);
  }catch{return false;}
 }
 function mapped(error,auth=false){
  if(error instanceof CloudError)return error;
  const code=String(error?.code||''),status=Number(error?.status||0);
  if(code==='23505'||code==='PT409'||status===409)return new CloudError('conflict');
  if(code==='email_not_confirmed')return new CloudError('email_unconfirmed');
  if(status===429||code==='over_request_rate_limit'||code==='over_email_send_rate_limit')return new CloudError('rate_limited');
  if(code==='weak_password')return new CloudError('invalid');
  if(error?.name==='AbortError')return new CloudError('session_changed');
  if(error instanceof TypeError||error?.name==='AuthRetryableFetchError'||status>=500||
    (!status&&/fetch|network|load failed|aborterror|aborted/i.test(String(error?.message||'')))||
    code==='PGRST000'||code==='PGRST001'||code==='PGRST002'||code==='PGRST003')return new CloudError('network');
  if(status===401||code==='PGRST301'||code==='PGRST303'||code==='refresh_token_not_found'||code==='session_not_found')return new CloudError('auth_required');
  if(auth)return new CloudError('auth_failed');
  if(code==='23514'||code==='22023'||code==='22P02'||code==='23502')return new CloudError('invalid');
  // Raw provider messages may contain request data. Only stable codes reach UI.
  return new CloudError('unavailable');
 }
 function rawSave(raw){
  if(typeof raw!=='string'||new TextEncoder().encode(raw).length>MAX_BYTES)fail('invalid');
  let save;try{save=JSON.parse(raw);}catch{fail('invalid');}
  const s=save?.state;
  if(!save||save.format!=='three-kingdoms-remake-save'||save.version!==1||
    typeof save.scenario!=='string'||!save.scenario.length||save.scenario.length>120||
    !HEX.test(save.checksum)||!HEX.test(save.catalog_sha256)||!s||typeof s!=='object'||Array.isArray(s)||
    !Number.isInteger(s.year)||s.year<1||s.year>400||!Number.isInteger(s.month)||s.month<1||s.month>12||
    !Number.isSafeInteger(s.turn)||s.turn<0)fail('invalid');
  return save; // Validation only: never encode this value as the stored save.
 }
 function metadata(row){
  if(!row||!UUID.test(row.save_id)||!Number.isInteger(row.slot)||row.slot<1||row.slot>5||
    !Number.isSafeInteger(row.revision)||row.revision<1||typeof row.label!=='string'||
    typeof row.scenario!=='string'||!HEX.test(row.save_sha256)||
    !Number.isInteger(row.game_year)||!Number.isInteger(row.game_month)||!Number.isSafeInteger(row.game_turn)||
    typeof row.created_at!=='string'||typeof row.updated_at!=='string')fail('invalid');
  return Object.fromEntries(META.split(',').map(key=>[key,row[key]]));
 }
 function credentials(email,password){
  if(typeof email!=='string'||email.length>320||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())||
    typeof password!=='string'||password.length<1||password.length>1024)fail('invalid');
  return {email:email.trim(),password};
 }
 function create(config,options={}){
  const configured=validConfig(config),listeners=new Set(),pending=new Set();
  const timeoutMs=Number.isInteger(options.timeoutMs)&&options.timeoutMs>0&&options.timeoutMs<=60000?options.timeoutMs:20000;
  let client=null,ready=false,user=null,authBusy=false,authMode=null,epoch=0,intent=0,initializing=null;
  const state=()=>Object.freeze({configured,ready,user:user?Object.freeze({...user}):null,authBusy,slots:5});
  const notify=()=>{for(const callback of listeners){try{callback(state());}catch{}}};
  const invalidate=()=>{epoch++;for(const controller of pending)controller.abort();};
  const applySession=session=>{
   const value=session?.user;
   const next=value&&typeof value.id==='string'&&UUID.test(value.id)?{id:value.id,email:typeof value.email==='string'?value.email:''}:null;
   if(authMode==='signOut'&&next)return;
   if(user?.id!==next?.id)invalidate();
   user=next;notify();
  };
  async function deadline(promise,onTimeout=()=>{}){
   let timer;
   try{return await Promise.race([promise,new Promise((_resolve,reject)=>{
    timer=setTimeout(()=>{onTimeout();reject(new CloudError('network'));},timeoutMs);
   })]);}finally{clearTimeout(timer);}
  }
  async function timedFetch(input,settings={}){
   if(typeof root.fetch!=='function')fail('unavailable');
   const controller=new AbortController(),external=settings.signal;
   let timedOut=false;
   const abort=()=>controller.abort();
   if(external?.aborted)abort();else external?.addEventListener('abort',abort,{once:true});
   try{return await deadline(root.fetch(input,{...settings,signal:controller.signal}),()=>{timedOut=true;abort();});}
   catch(error){if(timedOut)fail('network');throw error;}
   finally{external?.removeEventListener('abort',abort);}
  }
  function ensureClient(){
   if(!configured)fail('unavailable');
   if(!client){
    const factory=options.createClient||root.GameSupabase?.createClient;
    if(typeof factory!=='function')fail('unavailable');
    const ref=new URL(config.url).hostname.split('.')[0];
    try{
     client=factory(config.url,config.publishableKey,{global:{fetch:timedFetch},auth:{storageKey:'tk2-cloud-auth-'+ref,
      persistSession:true,autoRefreshToken:true,detectSessionInUrl:false,
      ...(options.storage?{storage:options.storage}:{})}});
     // This callback stays synchronous; awaiting SDK methods here can deadlock Auth.
     client.auth.onAuthStateChange((_event,session)=>applySession(session));
    }catch(error){client=null;throw mapped(error);}
   }
   return client;
  }
  async function init(){
   if(!configured){ready=true;notify();return state();}
   if(initializing){await initializing;return state();}
   initializing=(async()=>{
    const start=epoch,startIntent=intent;
    try{
     const c=ensureClient(),result=await deadline(c.auth.getSession());
     if(result.error)throw mapped(result.error,true);
     // A storage/auth event or explicit login supersedes a pending session read.
     if(start===epoch&&startIntent===intent)applySession(result.data?.session);
     return state();
    }catch(error){throw mapped(error,true);}
    finally{ready=true;notify();}
   })();
   try{await initializing;return state();}finally{initializing=null;}
  }
  async function authCall(kind,email,password){
   const c=ensureClient();if(authBusy)fail('busy');
   if(kind==='signUp'&&user)fail('invalid');
   const input=kind==='signOut'?undefined:credentials(email,password);
   authBusy=true;authMode=kind;const token=++intent;invalidate();
   if(kind==='signOut')user=null;
   notify();
   try{
    const result=await(kind==='signOut'?c.auth.signOut({scope:'local'}):
     kind==='signIn'?c.auth.signInWithPassword(input):c.auth.signUp(input));
    if(token!==intent)fail('session_changed');
    if(result.error)throw mapped(result.error,true);
    if(kind==='signOut'){applySession(null);return;}
    const session=result.data?.session||null;
    if(kind==='signIn'&&!session)fail('auth_failed');
    applySession(session);
    return {needsConfirmation:kind==='signUp'&&!session,user:state().user};
   }catch(error){throw mapped(error,true);}
   finally{if(token===intent){authBusy=false;authMode=null;notify();}}
  }
  function operation(){
   ensureClient();if(!ready||authBusy)fail('busy');if(!user)fail('auth_required');
   const captured={epoch,id:user.id,controller:new AbortController()};pending.add(captured.controller);
   return captured;
  }
  const assertCurrent=op=>{if(op.epoch!==epoch||op.id!==user?.id)fail('session_changed');if(op.timedOut)fail('network');};
  function slotValue(slot){if(!Number.isInteger(slot)||slot<1||slot>5)fail('invalid');return slot;}
  function revisionValue(revision,saveId,insert=false){
   if(!Number.isSafeInteger(revision)||revision<(insert?0:1)||revision>=Number.MAX_SAFE_INTEGER||
    (revision>0&&!UUID.test(saveId))||(revision===0&&saveId!==null&&saveId!==undefined))fail('invalid');
  }
  const withSignal=(query,op)=>typeof query.abortSignal==='function'?query.abortSignal(op.controller.signal):query;
  async function perform(callback){
   const op=operation();
   try{const result=await deadline(callback(op),()=>{op.timedOut=true;op.controller.abort();});assertCurrent(op);return result;}
   catch(error){assertCurrent(op);throw mapped(error);}
   finally{pending.delete(op.controller);}
  }
  async function response(query,op){
   const result=await withSignal(query,op);assertCurrent(op);
   if(result.error)throw mapped(result.error);
   return result.data;
  }
  async function list(){return perform(async op=>{
   const rows=await response(client.from(TABLE).select(META).eq('user_id',op.id).order('slot'),op);
   if(!Array.isArray(rows)||rows.length>5)fail('invalid');
   return rows.map(metadata);
  });}
  async function read(slot){
   slotValue(slot);
   return perform(async op=>{
    const row=await response(client.from(TABLE).select(META+',save_text').eq('user_id',op.id).eq('slot',slot).maybeSingle(),op);
    if(!row)fail('not_found');
    const meta=metadata(row);if(meta.slot!==slot)fail('invalid');rawSave(row.save_text);
    if(!root.crypto?.subtle)fail('unavailable');
    const digest=await root.crypto.subtle.digest('SHA-256',new TextEncoder().encode(row.save_text));
    assertCurrent(op);
    const hash=Array.from(new Uint8Array(digest),n=>n.toString(16).padStart(2,'0')).join('');
    if(hash!==meta.save_sha256)fail('invalid');
    return {...meta,save_text:row.save_text};
   });
  }
  async function write(slot,label,raw,expectedRevision,expectedSaveId=null){
   slotValue(slot);revisionValue(expectedRevision,expectedSaveId,true);rawSave(raw);
   if(typeof label!=='string'||!label.trim()||Array.from(label.trim()).length>80||/[\u0000-\u001f\u007f]/.test(label))fail('invalid');
   return perform(async op=>{
    let query;
    if(expectedRevision===0)query=client.from(TABLE).insert({user_id:op.id,slot,label:label.trim(),save_text:raw,revision:1});
    else query=client.from(TABLE).update({label:label.trim(),save_text:raw,revision:expectedRevision+1})
     .eq('user_id',op.id).eq('slot',slot).eq('save_id',expectedSaveId).eq('revision',expectedRevision);
    const row=await response(query.select(META).maybeSingle(),op);
    if(!row)fail('conflict');
    const result=metadata(row);
    if(result.slot!==slot||result.revision!==expectedRevision+1||
     (expectedRevision>0&&result.save_id!==expectedSaveId))fail('invalid');
    return result;
   });
  }
  async function remove(slot,expectedRevision,expectedSaveId){
   slotValue(slot);revisionValue(expectedRevision,expectedSaveId);
   return perform(async op=>{
    const row=await response(client.from(TABLE).delete().eq('user_id',op.id).eq('slot',slot)
     .eq('save_id',expectedSaveId).eq('revision',expectedRevision).select('save_id,slot,revision').maybeSingle(),op);
    if(!row)fail('conflict');
    return {slot,save_id:row.save_id,revision:row.revision};
   });
  }
  return Object.freeze({get state(){return state();},init,signIn:(email,password)=>authCall('signIn',email,password),
   signUp:(email,password)=>authCall('signUp',email,password),signOut:()=>authCall('signOut'),list,read,write,remove,
   subscribe(callback){if(typeof callback!=='function')fail('invalid');listeners.add(callback);callback(state());return()=>listeners.delete(callback);}});
 }
 const api=Object.freeze({create,CloudError,MAX_BYTES});
 if(typeof module==='object'&&module.exports)module.exports=api;else root.CloudSave=api;
})(typeof window==='object'?window:globalThis);
