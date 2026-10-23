'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{create,STORAGE_KEY}=require('../game/autosave.js');
const sha='a'.repeat(64);
function game(turn=1){return {seed:37,player:'shu',year:211,month:7,day:1+(turn-1)%3*10,turn,phase:'city',rng:{state:928,draws:13}};}
function raw(state=game(),padding=''){return ' {"format":"three-kingdoms-remake-save","version":1,"catalog_sha256":"'+sha+'","scenario":"test","state":'+JSON.stringify(state).replace(/}$/,',"distance":315.0,"large":9007199254740993,"padding":"'+padding+'"}')+',"checksum":"'+sha+'"} ';}
function fixture(){
 let view={revision:1,catalog:{scenario_id:'test',title:'入蜀爭奪戰'},game:game()},exportRaw=raw(view.game),busy=false,time=1700000000000;
 const data=new Map([['three-kingdoms-save','manual-save-remains']]),writes=[],statuses=[],loads=[];
 const storage={getItem:key=>data.get(key)||null,setItem:(key,value)=>{writes.push({key,value});data.set(key,value);}};
 const options={getView:()=>view,isBusy:()=>busy,getRawSave:async()=>exportRaw,loadRawSave:async(value,guard)=>{if(!guard())return false;loads.push(value);return true;},onStatus:state=>statuses.push(state),storage,now:()=>++time};
 const autosave=create(options);
 return {autosave,storage,data,writes,statuses,loads,options,get view(){return view;},set view(value){view=value;},set raw(value){exportRaw=value;},set busy(value){busy=value;},advance(turn){view={...view,revision:view.revision+1,game:game(turn)};exportRaw=raw(view.game);}};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const app=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const commandSource=app.slice(app.indexOf('async function command('),app.indexOf('\nfunction openDialog('));
const loadSource=app.slice(app.indexOf('async function loadSave('),app.indexOf('\nfunction confirmAutosave('));
function integration({pending=false,rejected=false,nextGame=game(),phase='city'}={}){
 const captured=[],requests=[],errors=[],invalidations=[],restored=[];
 const before={revision:8,catalog:{scenario_id:'test',title:'入蜀爭奪戰'},game:{...game(),phase}},next={...before,revision:9,game:nextGame};
 const context={busy:false,view:before,audioOutcome:null,battleScene:null,gameEvents:null,setupPreview:{},selectedCity:'old',actor:1,target:2,
  SaveTransfer:require('../game/save-transfer.js'),gameAudio:{play(){}},render(){},notice(message,error){if(error)errors.push(message);},
  setBusy(value){context.busy=value;},setTimeout(fn){fn();return 1;},dialog:{close(){restored.push('close');}},
  request:async(path,body,settings)=>{requests.push({path,body,settings});if(rejected)throw Error('Rejected');return next;},
  localAutosave:{status:()=>({state:pending?'saving':'saved'}),invalidate(){invalidations.push(true);},checkpoint(reason){assert.equal(context.busy,false,'Snapshots start after the campaign command is unlocked');captured.push(reason);return Promise.resolve({ok:true});}}
 };
 vm.createContext(context);vm.runInContext(commandSource+'\n'+loadSource,context);
 return {context,captured,requests,errors,invalidations,restored,before,next};
}
(async()=>{
 // The autosave wrapper must not normalize floats, large integers or whitespace.
 const exact=fixture(),original=raw();
 assert.equal((await exact.autosave.checkpoint('new')).ok,true);
 assert.equal(JSON.parse(exact.data.get(STORAGE_KEY)).items[0].raw,original);
 assert.equal(exact.data.get('three-kingdoms-save'),'manual-save-remains');
 assert.equal(exact.writes.length,1);assert.equal((await exact.autosave.checkpoint()).skipped,'duplicate');assert.equal(exact.writes.length,1);
 assert.equal(exact.autosave.list()[0].year,211);assert.equal(exact.autosave.list()[0].scenario,'test');assert.equal(exact.autosave.list()[0].raw,undefined);
 assert(exact.autosave.statusHtml().includes('已自動儲存'));assert(exact.autosave.recoveryHtml().includes('data-autosave-recover'));
 for(let turn=2;turn<=5;turn++){exact.advance(turn);await exact.autosave.checkpoint('turn');}
 assert.deepEqual(exact.autosave.list().map(row=>row.turn),[5,4,3]);
 assert.equal(exact.autosave.status().retained,3);
 assert.deepEqual(exact.view.game.rng,{state:928,draws:13},'Recovery bookkeeping does not change campaign RNG');
 assert.equal(JSON.parse(exact.data.get(STORAGE_KEY)).items[2].raw,raw(game(3)));

 // Atomic write failures retain the previous bytes and never reject commands.
 const beforeFailure=exact.data.get(STORAGE_KEY),quota=Object.assign(Error('full'),{name:'QuotaExceededError'});
 exact.storage.setItem=()=>{throw quota;};exact.advance(6);
 assert.equal((await exact.autosave.checkpoint()).error,'quota');assert.equal(exact.data.get(STORAGE_KEY),beforeFailure);assert.equal(exact.autosave.status().state,'error');
 assert.equal(exact.data.get('three-kingdoms-save'),'manual-save-remains');
 const compact=fixture();await compact.autosave.checkpoint('new');compact.advance(2);
 const set=compact.storage.setItem;compact.storage.setItem=(key,value)=>{if(JSON.parse(value).items.length>1)throw quota;set(key,value);};
 assert.equal((await compact.autosave.checkpoint()).retained,1);assert.equal(compact.autosave.list()[0].turn,2);assert.equal(compact.autosave.status().reduced,true);
 const unavailable=create({getView:()=>compact.view,isBusy:()=>false,getRawSave:()=>raw(compact.view.game),storage:{getItem(){throw Error('blocked');}}});
 assert.equal((await unavailable.checkpoint()).error,'storage');assert.deepEqual(unavailable.list(),[]);

 // Export errors and invalid documents cannot overwrite a good recovery point.
 const broken=fixture();await broken.autosave.checkpoint();const kept=broken.data.get(STORAGE_KEY);broken.raw='{"format":"other-game"}';broken.advance(2);broken.raw='not-json';
 assert.equal((await broken.autosave.checkpoint()).error,'invalid');assert.equal(broken.data.get(STORAGE_KEY),kept);
 const late=fixture(),first=deferred(),last=deferred();let exports=0,inFlight=0,maxInFlight=0;
 const latest=create({...late.options,getRawSave:()=>{exports++;maxInFlight=Math.max(maxInFlight,++inFlight);return (exports===1?first:last).promise.finally(()=>inFlight--);}});
 const p1=latest.checkpoint('turn');late.advance(2);const p2=latest.checkpoint('turn');late.advance(3);const p3=latest.checkpoint('battle');
 assert.equal((await p2).skipped,'superseded');first.reject(Error('old request failed'));await p1;await tick();
 assert.equal(exports,2);assert.equal(maxInFlight,1);last.resolve(raw(late.view.game));assert.equal((await p3).ok,true);assert.equal(latest.list()[0].turn,3);
 assert.equal(latest.status().state,'saved');assert.equal(late.statuses.some(state=>state.state==='error'),false,'An old export failure cannot replace the newer save status');
 const stale=fixture(),pending=deferred(),staleSave=create({...stale.options,getRawSave:()=>pending.promise});
 const saving=staleSave.checkpoint();stale.advance(2);pending.resolve(raw(game(1)));assert.equal((await saving).skipped,'stale');assert.equal(stale.data.has(STORAGE_KEY),false);
 stale.busy=true;assert.equal((await staleSave.checkpoint()).skipped,'busy');stale.busy=false;
 stale.view={...stale.view,game:null};assert.equal((await staleSave.checkpoint()).skipped,'no-game');

 // Restoration always asks first, passes original bytes and rejects stale dialogs.
 const recovery=fixture();await recovery.autosave.checkpoint();const id=recovery.autosave.list()[0].id;
 assert.equal((await recovery.autosave.restore(id)).skipped,'unconfirmed');
 assert.equal((await recovery.autosave.restore(id,{confirm:()=>false})).skipped,'cancelled');assert.equal(recovery.loads.length,0);
 assert.equal((await recovery.autosave.restore(id,{confirm:()=>true})).ok,true);assert.deepEqual(recovery.loads,[original]);
 const decision=deferred(),restore=recovery.autosave.restore(id,{confirm:()=>decision.promise});recovery.advance(2);decision.resolve(true);
 assert.equal((await restore).skipped,'stale');assert.equal(recovery.loads.length,1);
 const invalidated=deferred(),restore2=recovery.autosave.restore(id,{confirm:()=>invalidated.promise});recovery.autosave.invalidate();invalidated.resolve(true);assert.equal((await restore2).skipped,'stale');
 assert.equal((await recovery.autosave.restore('unknown',{confirm:()=>true})).error,'missing');
 const failed=create({...recovery.options,loadRawSave:async()=>false});assert.equal((await failed.restore(id,{confirm:()=>true})).error,'load');
 const disposed=deferred(),inert=create({...recovery.options,getRawSave:()=>disposed.promise}),attempt=inert.checkpoint();inert.dispose();disposed.resolve(raw(recovery.view.game));assert.equal((await attempt).skipped,'stale');assert.equal((await inert.checkpoint()).skipped,'disposed');

 const japanese=create({...compact.options,locale:()=> 'ja'});assert(japanese.statusHtml().includes('自動保存済み'));assert(japanese.recoveryHtml().includes('復元ポイント'));
 const xss=fixture();xss.view.catalog.title='<img src=x onerror=alert(1)>';await xss.autosave.checkpoint();assert(!xss.autosave.recoveryHtml().includes('<img'));assert(xss.autosave.recoveryHtml().includes('&lt;img'));
 const html=fs.readFileSync(require.resolve('../game/index.html'),'utf8');assert(html.indexOf('/autosave.js')<html.indexOf('/app.js'));
 // Exercise the shipped app functions, including the unlock/invalidation order.
 for(const [kind,nextGame,expected,phase] of [
  ['new',game(),'new','city'],['end_turn',{...game(),phase:'ai'},'turn','city'],
  ['ai',game(2),'turn','ai'],['attack',{...game(),phase:'result'},'battle','battle'],
  ['settle',game(),'battle','result'],['ai',{...game(),phase:'finished'},'battle','ai']
 ]){
  const f=integration({nextGame,phase});assert.equal(await f.context.command(kind),true);assert.deepEqual(f.captured,[expected],kind);assert.equal(f.invalidations.length,1);assert.equal(f.context.view,f.next);
 }
 for(const kind of ['allocate','recruit_officer','transfer']){
  const f=integration();assert(await f.context.command(kind));assert.deepEqual(f.captured,[],kind+' does not create redundant checkpoints');
 }
 const rejected=integration({rejected:true});assert.equal(await rejected.context.command('new'),false);assert.deepEqual(rejected.captured,[]);assert.equal(rejected.context.view,rejected.before);assert.equal(rejected.errors.length,1);
 const rescheduled=integration({pending:true});assert(await rescheduled.context.command('allocate'));assert.deepEqual(rescheduled.captured,['progress'],'An interrupted turn checkpoint is retried after a noncritical command');
 const failedResume=integration({pending:true,rejected:true});assert.equal(await failedResume.context.command('allocate'),false);assert.deepEqual(failedResume.captured,['progress']);assert.equal(failedResume.context.view,failedResume.before,'A failed command only retries its previously pending progress');
 const busyCommand=integration();busyCommand.context.busy=true;assert.equal(await busyCommand.context.command('new'),false);assert.deepEqual(busyCommand.captured,[]);assert.equal(busyCommand.requests.length,0);assert.equal(busyCommand.invalidations.length,0);
 const loaded=integration();assert(await loaded.context.loadSave(original));assert.deepEqual(loaded.captured,['load']);assert.equal(loaded.requests[0].path,'/api/load');assert.equal(loaded.requests[0].body,'{"save":'+original+',"revision":8}');assert.equal(loaded.context.view,loaded.next);
 const rejectedLoad=integration({rejected:true});assert.equal(await rejectedLoad.context.loadSave(original),false);assert.deepEqual(rejectedLoad.captured,[]);assert.equal(rejectedLoad.context.view,rejectedLoad.before);assert.equal(rejectedLoad.restored.length,0);
 const interruptedLoad=integration({pending:true,rejected:true});assert.equal(await interruptedLoad.context.loadSave(original),false);assert.deepEqual(interruptedLoad.captured,['progress']);assert.equal(interruptedLoad.context.view,interruptedLoad.before);
 const staleLoad=integration();assert.equal(await staleLoad.context.loadSave(original,()=>false),false);assert.deepEqual(staleLoad.captured,[]);assert.equal(staleLoad.requests.length,0);assert.equal(staleLoad.invalidations.length,0);
 const busyLoad=integration();busyLoad.context.busy=true;assert.equal(await busyLoad.context.loadSave(original),false);assert.equal(busyLoad.requests.length,0);
 console.log('Autosave: exact JSON bytes, 3-point rotation, deduplication, quota fallback, atomic failure, serialized exports, stale request/restore protection, mandatory confirmation, manual-save isolation and bilingual recovery UI passed');
 console.log('App autosave integration: new/turn/result/settlement/load checkpoints, noncritical commands, rejected operations, busy/stale guards and in-flight retry passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
