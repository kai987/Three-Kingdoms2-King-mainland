/* CAS, identity changes and byte-preserving cloud transfers, without a network. */
'use strict';
const assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const {create,MAX_BYTES}=require('../game/cloud-save.js');
const A='11111111-1111-4111-8111-111111111111',B='22222222-2222-4222-8222-222222222222';
const config={enabled:true,url:'https://test-cloud.supabase.co',publishableKey:'sb_publishable_test',slots:5};
const hash=text=>createHash('sha256').update(text).digest('hex');
const raw='{"format":"three-kingdoms-remake-save","version":1,"scenario":"mainland217-07","catalog_sha256":"'+'a'.repeat(64)+'","checksum":"'+'b'.repeat(64)+'","state":{"year":217,"month":7,"turn":1,"march_distance":315.0,"negative_zero":-0.0,"extra_large":9007199254740993,"note":"臺灣😀"}}';
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
function fake(db=new Map(),id=A){
 let session=id?{user:{id,email:(id===A?'a':'b')+'@example.test'},access_token:'private-token'}:null,callback;
 const api={db,calls:[],options:null,next:null,hold:null,signupConfirmation:true};
 function event(value){session=value;callback?.(value?'SIGNED_IN':'SIGNED_OUT',value);}
 const auth={
  onAuthStateChange(cb){callback=cb;return {data:{subscription:{unsubscribe(){callback=null;}}}};},
  async getSession(){if(api.sessionHold)await api.sessionHold.promise;return {data:{session},error:null};},
  async signInWithPassword(input){api.calls.push({kind:'login',email:input.email});if(input.password==='bad')return {error:{code:'invalid_credentials',status:400,message:'private password bad'}};event({user:{id:input.email.startsWith('b')?B:A,email:input.email}});return {data:{session},error:null};},
  async signUp(input){api.calls.push({kind:'signup',email:input.email,...(input.options?{options:input.options}:{})});if(api.signupError)return {error:api.signupError};if(api.signupConfirmation)return {data:{user:{id:A,email:input.email},session:null},error:null};event({user:{id:A,email:input.email}});return {data:{session},error:null};},
  async resend(input){api.calls.push({kind:'resend',...input});if(api.resendHold)await api.resendHold.promise;return {data:{},error:api.resendError||null};},
  async signOut(input){api.calls.push({kind:'logout',scope:input.scope});event(null);return {error:null};}
 };
 let serial=0;
 class Query{
  constructor(){this.kind='select';this.filters=[];this.fields='*';this.single=false;}
  select(fields){this.fields=fields;return this;}
  eq(key,value){this.filters.push([key,value]);return this;}
  order(key){this.orderKey=key;return this;}
  maybeSingle(){this.single=true;return this;}
  abortSignal(signal){this.signal=signal;return this;}
  insert(value){this.kind='insert';this.value=value;return this;}
  update(value){this.kind='update';this.value=value;return this;}
  delete(){this.kind='delete';return this;}
  then(resolve,reject){return this.run().then(resolve,reject);}
  async run(){
   const owner=session?.user?.id;
   api.calls.push({kind:this.kind,fields:this.fields,filters:this.filters,value:this.value,signal:this.signal});
   if(api.next){const value=api.next;api.next=null;if(value instanceof Error)throw value;return value;}
   if(api.hold){const hold=api.hold;api.hold=null;hold.started.resolve();await hold.release.promise;}
   if(!owner)return {data:null,error:{code:'42501',status:403}};
   let rows=[...db.values()].filter(row=>row.user_id===owner&&this.filters.every(([key,value])=>row[key]===value));
   const err=code=>({data:null,error:{code}});
   const finish=all=>({data:this.single?(all[0]||null):all,error:null});
   const project=row=>Object.fromEntries(this.fields.split(',').map(key=>[key,row[key]]));
   if(this.kind==='insert'){
    if(this.value.user_id!==owner)return err('42501');
    const key=owner+':'+this.value.slot;if(db.has(key))return err('23505');
    const save=JSON.parse(this.value.save_text),now='2026-10-22T00:00:00.000Z';
    const row={...this.value,save_id:'00000000-0000-4000-8000-'+String(++serial).padStart(12,'0'),scenario:save.scenario,
     game_year:save.state.year,game_month:save.state.month,game_turn:save.state.turn,save_sha256:hash(this.value.save_text),created_at:now,updated_at:now};
    db.set(key,row);return finish([project(row)]);
   }
   if(this.kind==='update'){
    for(const row of rows){if(this.value.revision!==row.revision+1)return err('PT409');Object.assign(row,this.value);row.save_sha256=hash(row.save_text);}
    return finish(rows.map(project));
   }
   if(this.kind==='delete'){for(const row of rows)db.delete(row.user_id+':'+row.slot);return finish(rows.map(project));}
   if(this.orderKey)rows.sort((a,b)=>a[this.orderKey]-b[this.orderKey]);
   return finish(rows.map(project));
  }
 }
 api.createClient=(url,key,options)=>{api.options={url,key,...options};return {auth,from(table){assert.equal(table,'tk2_cloud_saves');return new Query();}};};
 api.changeUser=value=>event(value?{user:{id:value,email:'changed@example.test'}}:null);
 return api;
}
const code=(expected,callback)=>assert.rejects(callback,error=>{assert.equal(error.code,expected);assert.equal(error.message,expected);return true;});
async function ready(api=fake()){const core=create(config,{createClient:api.createClient});await core.init();return {core,api};}
(async()=>{
 // Invalid/missing config disables cloud without affecting any local state.
 for(const value of [{}, {...config,enabled:false},{...config,url:'http://test-cloud.supabase.co'},
  {...config,url:'https://attacker.example'},{...config,publishableKey:'sb_secret_admin'},
  ...['http://example.com/','https://user:password@example.com/','https://example.com/#token','javascript:alert(1)','not a URL'].map(confirmationRedirectUrl=>({...config,confirmationRedirectUrl}))]){
  const disabled=create(value,{createClient(){throw Error('must not initialize');}});await disabled.init();assert.equal(disabled.state.configured,false);assert.equal(disabled.state.ready,true);await code('unavailable',()=>disabled.list());
 }
 const {core,api}=await ready();
 assert.deepEqual(core.state.user,{id:A,email:'a@example.test'});
 assert.equal(api.options.auth.storageKey,'tk2-cloud-auth-test-cloud');
 assert.deepEqual([api.options.auth.persistSession,api.options.auth.autoRefreshToken,api.options.auth.detectSessionInUrl],[true,true,false]);
 assert.equal(api.calls.length,0,'init performs no cloud save writes or reads');
 // A failed/missing SDK cannot leave the account UI waiting indefinitely.
 const missing=create(config,{createClient(){throw Error('SDK missing');}});
 await code('unavailable',()=>missing.init());assert.equal(missing.state.ready,true);
 const initializingApi=fake(),sessionHold=deferred();initializingApi.sessionHold=sessionHold;
 const initializing=create(config,{createClient:initializingApi.createClient});
 const init1=initializing.init(),init2=initializing.init();sessionHold.resolve();
 assert.equal((await init1).ready,true);assert.equal((await init2).ready,true);
 const blockedApi=fake();blockedApi.sessionHold=deferred();
 const blocked=create(config,{createClient:blockedApi.createClient,timeoutMs:10});
 await code('network',()=>blocked.init());assert.equal(blocked.state.ready,true);
 blockedApi.sessionHold.resolve();
 const states=[],unsubscribe=core.subscribe(state=>states.push(state));assert.equal(states.length,1);
 assert.equal(Object.isFrozen(core.state),true);assert.equal(Object.isFrozen(core.state.user),true);
 const first=await core.write(1,'舊版行軍',raw,0);
 assert.equal(first.revision,1);assert.equal(first.slot,1);assert.equal('save_text' in first,false);
 assert.equal(api.db.get(A+':1').save_text,raw);assert.ok(api.db.get(A+':1').save_text.includes('315.0'));
 const rows=await core.list();assert.equal(rows.length,1);assert.equal('save_text' in rows[0],false);
 assert.equal(api.calls.at(-1).fields.includes('save_text'),false,'list fetches metadata only');
 const loaded=await core.read(1);assert.equal(loaded.save_text,raw);assert.equal(loaded.save_sha256,hash(raw));
 assert.ok(loaded.save_text.includes('-0.0'));assert.ok(loaded.save_text.includes('9007199254740993'));
 await code('conflict',()=>core.write(1,'insert race',raw,0));
 await code('invalid',()=>core.write(1,'missing identity',raw,first.revision));
 const second=await core.write(1,'更新',raw,first.revision,first.save_id);assert.equal(second.revision,2);
 await code('conflict',()=>core.write(1,'stale',raw,first.revision,first.save_id));
 await code('conflict',()=>core.remove(1,first.revision,first.save_id));
 await core.remove(1,second.revision,second.save_id);
 const recreated=await core.write(1,'重建',raw,0);assert.notEqual(recreated.save_id,first.save_id);assert.equal(recreated.revision,1);
 await code('conflict',()=>core.write(1,'ABA overwrite',raw,1,first.save_id));
 await code('conflict',()=>core.remove(1,1,first.save_id));
 assert.equal(api.db.get(A+':1').label,'重建');
 for(const value of [null,'[]','null','{','{}',raw.replace('"month":7','"month":13'),raw+' '.repeat(MAX_BYTES)])await code('invalid',()=>core.write(2,'invalid',value,0));
 await code('invalid',()=>core.write(6,'slot',raw,0));
 await code('invalid',()=>core.write(2,'\nlabel',raw,0));
 await code('invalid',()=>core.write(2,'a'.repeat(81),raw,0));
 await code('invalid',()=>core.write(2,'revision',raw,Number.MAX_SAFE_INTEGER,first.save_id));
 api.db.get(A+':1').save_sha256='c'.repeat(64);await code('invalid',()=>core.read(1));api.db.get(A+':1').save_sha256=hash(raw);
 api.next=new TypeError('Failed to fetch private token');await code('network',()=>core.list());assert.equal(core.state.user.id,A);
 api.next={data:null,error:{message:'TypeError: Failed to fetch sensitive raw'}};await code('network',()=>core.list());
 api.next={data:null,error:{code:'PGRST301',status:401,message:'secret token'}};await code('auth_required',()=>core.list());
 api.next={data:null,error:{code:'42501',message:'permission denied: private data'}};await code('unavailable',()=>core.list());
 // Stale asynchronous reads must not expose a previous account's save.
 const hold={started:deferred(),release:deferred()};api.hold=hold;
 const pending=core.read(1);await hold.started.promise;api.changeUser(B);hold.release.resolve();await code('session_changed',()=>pending);
 assert.equal(core.state.user.id,B);assert.equal((await core.list()).length,0);
 await code('not_found',()=>core.read(1));
 // A sent request may finish for its original account, but cannot write to the
 // new account or have its result accepted after an identity change.
 api.changeUser(A);const holdWrite={started:deferred(),release:deferred()};api.hold=holdWrite;
 const oldWrite=core.write(4,'original account',raw,0);await holdWrite.started.promise;
 api.changeUser(B);holdWrite.release.resolve();await code('session_changed',()=>oldWrite);
 assert.equal(api.db.has(B+':4'),false);assert.equal((await core.list()).length,0);
 // An earlier operation is invalidated even if a same-account login happens.
 api.changeUser(A);const hold2={started:deferred(),release:deferred()};api.hold=hold2;
 const pending2=core.list();await hold2.started.promise;await core.signIn('a@example.test','correct');hold2.release.resolve();await code('session_changed',()=>pending2);
 await code('auth_failed',()=>core.signIn('a@example.test','bad'));
 assert.equal(core.state.authBusy,false);
 api.next={data:null,error:{code:'PT409'}};await code('conflict',()=>core.write(2,'race',raw,0));
 await core.signOut();assert.equal(core.state.user,null);assert.equal(api.calls.at(-1).scope,'local');await code('auth_required',()=>core.list());
 const signup=await core.signUp('a@example.test','correct');assert.equal(signup.needsConfirmation,true);assert.equal(core.state.user,null);
 api.signupConfirmation=false;const confirmed=await core.signUp('a@example.test','correct');assert.equal(confirmed.needsConfirmation,false);assert.equal(core.state.user.id,A);
 await code('invalid',()=>core.signUp('a@example.test','correct'));
 unsubscribe();const count=states.length;await core.signOut();assert.equal(states.length,count);
 // Confirmation resend is explicit, password-free, throttled, and never saves.
 let clock=1000;const mailApi=fake(new Map(),null),mail=create(config,{createClient:mailApi.createClient,now:()=>clock});await mail.init();
 assert.equal(mailApi.calls.length,0);
 for(const [provider,expected] of [['email_address_not_authorized','email_delivery_unavailable'],['email_provider_disabled','registration_disabled'],['signup_disabled','registration_disabled']]){
  mailApi.signupError={code:provider,status:400,message:'private recipient and provider details'};
  await code(expected,()=>mail.signUp('person@example.test','password123'));assert.equal(mail.state.authBusy,false);assert.equal(mail.state.user,null);
 }
 mailApi.signupError=null;await mail.signUp('person@example.test','password123');assert.equal(mail.state.confirmationRetryAt,61000);
 const countBeforeResend=mailApi.calls.length;await code('rate_limited',()=>mail.resendConfirmation('person@example.test'));assert.equal(mailApi.calls.length,countBeforeResend);
 clock=61000;await code('invalid',()=>mail.resendConfirmation('invalid'));
 const resent=await mail.resendConfirmation(' person@example.test ');assert.equal(resent.needsConfirmation,true);assert.equal(mail.state.user,null);
 assert.deepEqual(mailApi.calls.at(-1),{kind:'resend',type:'signup',email:'person@example.test'});
 assert.equal(mail.state.confirmationRetryAt,121000);await code('rate_limited',()=>mail.resendConfirmation('person@example.test'));
 clock=121000;mailApi.resendError={code:'over_email_send_rate_limit',status:429,message:'private provider limit'};
 await code('rate_limited',()=>mail.resendConfirmation('person@example.test'));assert.equal(mail.state.confirmationRetryAt,181000);
 clock=181000;mailApi.resendError={code:'email_address_not_authorized',status:400};await code('email_delivery_unavailable',()=>mail.resendConfirmation('person@example.test'));
 mailApi.resendError=null;mailApi.resendHold=deferred();const staleResend=mail.resendConfirmation('person@example.test');
 mailApi.changeUser(B);mailApi.resendHold.resolve();await code('session_changed',()=>staleResend);assert.equal(mail.state.user.id,B);
 await code('invalid',()=>mail.resendConfirmation('person@example.test'));
 assert(mailApi.calls.every(call=>['signup','resend'].includes(call.kind)),'email actions never access cloud save rows');
 // A deployer may explicitly configure an allowlisted callback; no origin is guessed.
 for(const url of ['https://game.example/confirm','http://127.0.0.1:8878/','http://localhost:8878/','http://[::1]:8878/']){
  const redirectApi=fake(new Map(),null),redirectCore=create({...config,confirmationRedirectUrl:url},{createClient:redirectApi.createClient,now:()=>clock});
  await redirectCore.init();await redirectCore.signUp('person@example.test','password123');assert.equal(redirectApi.calls.at(-1).options.emailRedirectTo,url);
  clock+=60000;await redirectCore.resendConfirmation('person@example.test');assert.equal(redirectApi.calls.at(-1).options.emailRedirectTo,url);
 }
 // Two independent device clients share cloud data, while each owns its Auth state.
 const db=new Map(),device1=await ready(fake(db)),device2=await ready(fake(db));
 const saved=await device1.core.write(3,'跨裝置',raw,0);assert.equal((await device2.core.read(3)).save_text,raw);
 const stale=(await device2.core.list())[0];await device1.core.write(3,'新版',raw,saved.revision,saved.save_id);
 await code('conflict',()=>device2.core.write(3,'舊版',raw,stale.revision,stale.save_id));
 assert.equal(db.get(A+':3').label,'新版');
 // A stalled SDK/fetch is bounded; network failures are not retried as writes.
 const timeoutApi=fake(),timeoutCore=create(config,{createClient:timeoutApi.createClient,timeoutMs:10});await timeoutCore.init();
 const timeoutHold={started:deferred(),release:deferred()};timeoutApi.hold=timeoutHold;
 const timedList=timeoutCore.list();await timeoutHold.started.promise;await code('network',()=>timedList);
 assert.equal(timeoutApi.calls.length,1);assert.equal(timeoutApi.calls[0].signal.aborted,true);
 timeoutHold.release.resolve();
 const ordinaryFetch=globalThis.fetch;let timedFetchAborted=false;
 try{
  globalThis.fetch=(_input,settings)=>new Promise((_resolve,reject)=>settings.signal.addEventListener('abort',()=>{timedFetchAborted=true;reject(new DOMException('aborted','AbortError'));}));
  await code('network',()=>timeoutApi.options.global.fetch('https://test-cloud.supabase.co/auth/v1/token'));
  assert.equal(timedFetchAborted,true);
 }finally{globalThis.fetch=ordinaryFetch;}
 console.log('Cloud saves: raw JSON, 5-slot CAS/ABA, cross-device reads, Auth isolation, stale-session and failure checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
