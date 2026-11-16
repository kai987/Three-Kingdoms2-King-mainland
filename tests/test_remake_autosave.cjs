'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{create,STORAGE_KEY,MAX_STORAGE_BYTES}=require('../game/autosave.js');
const sha='a'.repeat(64);
function game(turn=1){return {seed:37,player:'shu',year:211,month:7,day:1+(turn-1)%3*10,turn,phase:'city',rng:{state:928,draws:13}};}
function raw(state=game(),padding=''){return ' {"format":"three-kingdoms-remake-save","version":1,"catalog_sha256":"'+sha+'","scenario":"test","state":'+JSON.stringify(state).replace(/}$/,',"distance":315.0,"large":9007199254740993,"padding":"'+padding+'"}')+',"checksum":"'+sha+'"} ';}
function fixture(){
 let view={revision:1,catalog:{scenario_id:'test',title:'入蜀爭奪戰',factions:[{id:'shu',name:'蜀漢'}]},game:game()},exportRaw=raw(view.game),busy=false,time=1700000000000;
 const data=new Map([['three-kingdoms-save','manual-save-remains']]),writes=[],statuses=[],loads=[];
 const storage={getItem:key=>data.get(key)||null,setItem:(key,value)=>{writes.push({key,value});data.set(key,value);}};
 const options={getView:()=>view,isBusy:()=>busy,getRawSave:async()=>exportRaw,loadRawSave:async(value,guard)=>{if(!guard())return false;loads.push(value);return true;},onStatus:state=>statuses.push(state),storage,now:()=>++time};
 const autosave=create(options);
 return {autosave,storage,data,writes,statuses,loads,options,get view(){return view;},set view(value){view=value;},set raw(value){exportRaw=value;},set busy(value){busy=value;},advance(turn){view={...view,revision:view.revision+1,game:game(turn)};exportRaw=raw(view.game);}};
}
const campaignA='a'.repeat(32),campaignB='b'.repeat(32),campaignC='c'.repeat(32),campaignD='d'.repeat(32);
function stepCampaign(fixture,campaignId,turn,padding=''){
 const state={...game(turn),extension:{campaign_id:campaignId}};
 fixture.view={...fixture.view,revision:fixture.view.revision+1,game:state};
 fixture.raw=raw(state,padding);
 return fixture.autosave.checkpoint(turn===1?'new':'turn');
}
function savedRows(fixture){return JSON.parse(fixture.data.get(STORAGE_KEY)).items;}
function checkpoints(rows){
 return rows.map(row=>{
  const state=JSON.parse(row.raw).state;
  return [state.extension.campaign_id,state.turn];
 }).sort(([leftId,leftTurn],[rightId,rightTurn])=>leftId.localeCompare(rightId)||rightTurn-leftTurn);
}
function oldRecoveryPoint(state,i){
 const savedAt=1699999999000+i;
 return {id:`${savedAt}-${i}`,savedAt,scenario:'test',title:'入蜀爭奪戰',reason:'turn',raw:raw(state)};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const app=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const commandSource=app.slice(app.indexOf('async function command('),app.indexOf('\nfunction openDialog('));
const loadSource=app.slice(app.indexOf('function showSaveLoadError('),app.indexOf('\nfunction confirmAutosave('));
function integration({pending=false,rejected=false,previousGame=game(),nextGame=game(),phase='city',saveGate}={}){
 const captured=[],requests=[],errors=[],invalidations=[],restored=[];
 const before={revision:8,catalog:{scenario_id:'test',title:'入蜀爭奪戰'},game:{...previousGame,phase}},next={...before,revision:9,game:nextGame};
 const context={busy:false,observerYearSaving:false,view:before,audioOutcome:null,battleScene:null,gameEvents:null,setupPreview:{},selectedCity:'old',actor:1,target:2,confirmOrderCommand:async()=>true,
  clearDialogueFeedback(){},setObserverPlaying(){},SaveTransfer:require('../game/save-transfer.js'),gameAudio:{play(){}},render(){},notice(message,error){if(error)errors.push(message);},
  setBusy(value){context.busy=value;},setTimeout(fn){fn();return 1;},dialog:{close(){restored.push('close');}},
  request:async(path,body,settings)=>{requests.push({path,body,settings});if(rejected)throw Error('Rejected');return next;},
  localAutosave:{status:()=>({state:pending?'saving':'saved'}),invalidate(){invalidations.push(true);},checkpoint(reason){assert.equal(context.busy,false,'Snapshots start after the campaign command is unlocked');captured.push(reason);return saveGate?.promise||Promise.resolve({ok:true});}}
 };
 vm.createContext(context);vm.runInContext(commandSource+'\n'+loadSource,context);
 return {context,captured,requests,errors,invalidations,restored,before,next};
}
(async()=>{
 const current=fixture(),currentRaw=raw().replace('"version":1','"version":2');current.raw=currentRaw;
 assert.equal((await current.autosave.checkpoint('new')).ok,true);
 assert.equal(JSON.parse(current.data.get(STORAGE_KEY)).items[0].raw,currentRaw);
 assert.equal((await current.autosave.restore(current.autosave.list()[0].id,{confirm:()=>true})).ok,true);
 assert.equal(current.loads[0],currentRaw,'Current-format recovery must preserve the exact order ledger bytes');
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

 // Reusing the scenario, player and seed still creates two separate rotations.
 const paired=fixture();
 for(const [id,turn]of [[campaignA,1],[campaignA,2],[campaignB,1],[campaignA,3],[campaignB,2],[campaignA,4]]){
  assert.equal((await stepCampaign(paired,id,turn)).ok,true);
 }
 assert.equal(JSON.parse(paired.data.get(STORAGE_KEY)).version,2);
 assert.deepEqual(checkpoints(savedRows(paired)),[[campaignA,4],[campaignA,3],[campaignA,2],[campaignB,2],[campaignB,1]]);
 const reopened=create({...paired.options,locale:()=> 'ja'});
 assert.equal(reopened.list().length,5);
 const recoveryGroups=reopened.recoveryHtml();
 const legends=[...recoveryGroups.matchAll(/<fieldset data-autosave-campaign><legend>([^<]+)<\/legend>/g)].map(match=>match[1]);
 assert.equal(legends.length,2);
 assert.equal(new Set(legends).size,2,'Recovery groups distinguish campaigns with the same settings');
 assert(legends.every(title=>title.includes('蜀漢')));
 assert(!recoveryGroups.includes(campaignA),'Recovery controls do not expose internal campaign identifiers');
 assert(!recoveryGroups.includes(campaignB));
 const batchB=savedRows(paired).find(row=>JSON.parse(row.raw).state.extension.campaign_id===campaignB);
 assert.equal((await reopened.restore(batchB.id,{confirm:()=>true})).ok,true);
 assert.equal(paired.loads[0],batchB.raw,'A checkpoint from another campaign still loads its exact raw save');

 // Atomic write failures retain the previous bytes and never reject commands.
 const beforeFailure=exact.data.get(STORAGE_KEY),quota=Object.assign(Error('full'),{name:'QuotaExceededError'});
 exact.storage.setItem=()=>{throw quota;};exact.advance(6);
 assert.equal((await exact.autosave.checkpoint()).error,'quota');assert.equal(exact.data.get(STORAGE_KEY),beforeFailure);assert.equal(exact.autosave.status().state,'error');
 assert.equal(exact.data.get('three-kingdoms-save'),'manual-save-remains');
 const compact=fixture();await compact.autosave.checkpoint('new');compact.advance(2);
 const set=compact.storage.setItem;compact.storage.setItem=(key,value)=>{if(JSON.parse(value).items.length>1)throw quota;set(key,value);};
 assert.equal((await compact.autosave.checkpoint()).retained,1);assert.equal(compact.autosave.list()[0].turn,2);assert.equal(compact.autosave.status().reduced,true);

 // Migrate the existing container on write, keeping old IDs and save bytes.
 const legacy=fixture(),oldRows=[
  oldRecoveryPoint({...game(3),extension:{difficulty:'hard'}},3),
  oldRecoveryPoint({...game(2),extension:{lifespan:'none'}},2),
  oldRecoveryPoint(game(1),1),
 ];
 const oldContainer=JSON.stringify({version:1,items:oldRows});
 legacy.data.set(STORAGE_KEY,oldContainer);
 const migrated=create(legacy.options);
 assert.deepEqual(migrated.list().map(row=>row.id),oldRows.map(row=>row.id));
 assert.equal(legacy.writes.length,0,'Opening the recovery view does not rewrite legacy data');
 assert.equal((await migrated.restore(oldRows[1].id,{confirm:()=>true})).ok,true);
 assert.equal(legacy.loads[0],oldRows[1].raw);
 const legacySet=legacy.storage.setItem;
 legacy.storage.setItem=()=>{throw quota;};
 legacy.advance(4);
 assert.equal((await migrated.checkpoint('turn')).error,'quota');
 assert.equal(legacy.data.get(STORAGE_KEY),oldContainer,'A failed migration retains the complete old container');
 legacy.storage.setItem=legacySet;
 assert.equal((await migrated.checkpoint('turn')).ok,true);
 assert.equal(JSON.parse(legacy.data.get(STORAGE_KEY)).version,2);
 const migratedRows=savedRows(legacy);
 for(const old of oldRows)assert.equal(migratedRows.find(row=>row.id===old.id).raw,old.raw);
 assert.equal(legacy.data.get('three-kingdoms-save'),'manual-save-remains');

 // Recent checkpoints within one campaign yield to older campaigns' only recovery point.
 // Japanese text makes a character-count limit observably different from the UTF-8 byte limit.
 assert.equal(MAX_STORAGE_BYTES,4*1024*1024);
 const utf8=fixture(),large='糧'.repeat(400000);
 for(const [id,turn]of [[campaignB,1],[campaignA,1],[campaignA,2],[campaignC,1]]){
  assert.equal((await stepCampaign(utf8,id,turn,large)).ok,true);
 }
 assert.deepEqual(checkpoints(savedRows(utf8)),[[campaignA,2],[campaignB,1],[campaignC,1]]);
 assert.equal((await stepCampaign(utf8,campaignD,1,large)).ok,true);
 assert.deepEqual(checkpoints(savedRows(utf8)),[[campaignA,2],[campaignC,1],[campaignD,1]],'Oldest campaign is evicted only when four separate latest points cannot fit');
 for(const write of utf8.writes)assert(Buffer.byteLength(write.value,'utf8')<=MAX_STORAGE_BYTES);

 // The same priority applies when localStorage enforces a tighter quota than the application cap.
 const browserQuota=fixture(),quotaSet=browserQuota.storage.setItem;
 browserQuota.storage.setItem=(key,value)=>{if(JSON.parse(value).items.length>3)throw quota;quotaSet(key,value);};
 for(const [id,turn]of [[campaignB,1],[campaignA,1],[campaignA,2],[campaignC,1]]){
  assert.equal((await stepCampaign(browserQuota,id,turn)).ok,true);
 }
 assert.deepEqual(checkpoints(savedRows(browserQuota)),[[campaignA,2],[campaignB,1],[campaignC,1]]);
 assert.equal(browserQuota.autosave.status().reduced,true);
 assert.equal((await stepCampaign(browserQuota,campaignD,1)).ok,true);
 assert.deepEqual(checkpoints(savedRows(browserQuota)),[[campaignA,2],[campaignC,1],[campaignD,1]]);

 // Two browser tabs share this key. Resolve writes under the same lock, even at the same timestamp.
 const shared=fixture(),lockNames=[];let tail=Promise.resolve();
 const locks={request(name,write){lockNames.push(name);const queued=tail.then(write);tail=queued;return queued;}};
 const openTab=campaignId=>{
  const state={...game(),extension:{campaign_id:campaignId}};
  return create({...shared.options,locks,now:()=>1700000000000,getView:()=>({...shared.view,game:state}),getRawSave:async()=>raw(state)});
 };
 const clients=[openTab(campaignA),openTab(campaignB)];
 const simultaneous=await Promise.all(clients.map(client=>client.checkpoint('new')));
 assert(simultaneous.every(result=>result.ok));
 assert.deepEqual(lockNames,[STORAGE_KEY,STORAGE_KEY]);
 assert.equal(new Set(savedRows(shared).map(row=>row.id)).size,2,'Timestamp overlap cannot give distinct campaigns the same restore control');
 assert.deepEqual(checkpoints(savedRows(shared)),[[campaignA,1],[campaignB,1]]);

 const blocked=fixture(),releaseLock=deferred();let lockRequested=false;
 const waiting=create({...blocked.options,locks:{request(_name,write){lockRequested=true;return releaseLock.promise.then(write);}}});
 const deferredWrite=waiting.checkpoint();await tick();
 assert.equal(lockRequested,true);
 blocked.advance(2);releaseLock.resolve();
 assert.equal((await deferredWrite).skipped,'stale');
 assert.equal(blocked.writes.length,0);
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
 const sameSettings=integration();let cryptoCalls=0;
 sameSettings.context.crypto={getRandomValues(bytes){assert.equal(bytes.length,16);return bytes.fill(++cryptoCalls);}};
 const settings={scenario:'test',faction:'shu',seed:2026,difficulty:'normal',lifespan:'historical'};
 assert.equal(await sameSettings.context.command('new',settings),true);
 assert.equal(await sameSettings.context.command('new',settings),true);
 assert.deepEqual(sameSettings.requests.map(({body})=>body.payload.seed),[2026,2026]);
 assert.deepEqual(sameSettings.requests.map(({body})=>body.payload.campaign_id),['01'.repeat(16),'02'.repeat(16)]);
 assert.equal(Object.hasOwn(settings,'campaign_id'),false);
 assert.equal(await sameSettings.context.command('allocate'),true);
 assert.equal(cryptoCalls,2,'Only a new campaign receives a new identifier');
 for(const kind of ['allocate','recruit_officer','transfer']){
  const f=integration();assert(await f.context.command(kind));assert.deepEqual(f.captured,[],kind+' does not create redundant checkpoints');
 }
 const rejected=integration({rejected:true});assert.equal(await rejected.context.command('new'),false);assert.deepEqual(rejected.captured,[]);assert.equal(rejected.context.view,rejected.before);assert.equal(rejected.errors.length,1);
 const rescheduled=integration({pending:true});assert(await rescheduled.context.command('allocate'));assert.deepEqual(rescheduled.captured,['progress'],'An interrupted turn checkpoint is retried after a noncritical command');
 const failedResume=integration({pending:true,rejected:true});assert.equal(await failedResume.context.command('allocate'),false);assert.deepEqual(failedResume.captured,['progress']);assert.equal(failedResume.context.view,failedResume.before,'A failed command only retries its previously pending progress');
 const busyCommand=integration();busyCommand.context.busy=true;assert.equal(await busyCommand.context.command('new'),false);assert.deepEqual(busyCommand.captured,[]);assert.equal(busyCommand.requests.length,0);assert.equal(busyCommand.invalidations.length,0);
 const loaded=integration();assert(await loaded.context.loadSave(original));assert.deepEqual(loaded.captured,['load']);assert.equal(loaded.requests[0].path,'/api/load');assert.equal(loaded.requests[0].body,'{"save":'+original+',"revision":8}');assert.equal(loaded.context.view,loaded.next);
 const observerDecember={...game(35),player:'observer',month:12,day:21};
 const observerJanuary={...observerDecember,turn:36,year:212,month:1,day:1};
 const gate=deferred(),annual=integration({previousGame:observerDecember,nextGame:observerJanuary,saveGate:gate});
 const advance=annual.context.command('observe_turn');await tick();
 assert.deepEqual(annual.captured,['observer-year']);assert.equal(annual.context.observerYearSaving,true);
 assert.equal(await annual.context.command('observe_turn'),false,'The next observed turn waits for the annual snapshot');
 assert.equal(await annual.context.loadSave(original),false,'A concurrent restore cannot discard an annual snapshot');
 gate.resolve({ok:true});assert.equal(await advance,true);assert.equal(annual.context.observerYearSaving,false);
 for(const [kind,nextGame] of [['new',observerJanuary],['observe_turn',{...observerJanuary,turn:37,day:11}],['observe_turn',{...observerJanuary,turn:37,phase:'finished'}]]){
  const f=integration({previousGame:observerJanuary,nextGame});assert(await f.context.command(kind));assert.deepEqual(f.captured,[],kind+' in the same observed year');
 }
 const observerLoad=integration({nextGame:observerJanuary});assert(await observerLoad.context.loadSave(original));assert.deepEqual(observerLoad.captured,[]);
 const rejectedLoad=integration({rejected:true});assert.equal(await rejectedLoad.context.loadSave(original),false);assert.deepEqual(rejectedLoad.captured,[]);assert.equal(rejectedLoad.context.view,rejectedLoad.before);assert.equal(rejectedLoad.restored.length,0);
 const interruptedLoad=integration({pending:true,rejected:true});assert.equal(await interruptedLoad.context.loadSave(original),false);assert.deepEqual(interruptedLoad.captured,['progress']);assert.equal(interruptedLoad.context.view,interruptedLoad.before);
 const staleLoad=integration();assert.equal(await staleLoad.context.loadSave(original,()=>false),false);assert.deepEqual(staleLoad.captured,[]);assert.equal(staleLoad.requests.length,0);assert.equal(staleLoad.invalidations.length,0);
 const busyLoad=integration();busyLoad.context.busy=true;assert.equal(await busyLoad.context.loadSave(original),false);assert.equal(busyLoad.requests.length,0);
 console.log('Autosave: exact JSON bytes, campaign-scoped rotation, legacy migration, UTF-8 budget, prioritized quota fallback, atomic failure, serialized exports, stale request/restore protection, manual-save isolation and bilingual recovery UI passed');
 console.log('App autosave integration: new/turn/result/settlement/load checkpoints, noncritical commands, rejected operations, busy/stale guards and in-flight retry passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
