/* Local recovery points keep engine JSON bytes intact and never upload to cloud. */
'use strict';
(function(root){
 const STORAGE_KEY='three-kingdoms-autosaves-v1',MAX_BYTES=2*1024*1024,LIMIT=3;
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function envelope(raw){
  if(typeof raw!=='string'||new TextEncoder().encode(raw).length>MAX_BYTES)throw Error('invalid');
  const value=JSON.parse(raw);
  if(!value||value.format!=='three-kingdoms-remake-save'||![1,2].includes(value.version)||typeof value.scenario!=='string'||!value.scenario||value.scenario.length>160||!value.state||typeof value.state!=='object'||Array.isArray(value.state)||!['catalog_sha256','checksum'].every(key=>typeof value[key]==='string'&&/^[a-f0-9]{64}$/.test(value[key])))throw Error('invalid');
  return value;
 }
 function fingerprint(view){
  if(!view?.game)return null;
  const g=view.game;
  return JSON.stringify([view.revision,view.catalog?.scenario_id,g.seed,g.player,g.year,g.month,g.day,g.turn,g.phase,g.battle?.id]);
 }
 function matches(value,view){
  const a=value.state,b=view.game;
  return value.scenario===view.catalog?.scenario_id&&['seed','player','year','month','day','turn','phase'].every(key=>a[key]===b[key]);
 }
 function create(options={}){
  const getView=options.getView||(()=>null),isBusy=options.isBusy||(()=>false),now=options.now||Date.now;
  let storage;try{storage=Object.hasOwn(options,'storage')?options.storage:root.localStorage;}catch{storage=null;}
  let epoch=0,serial=0,running=false,queued=null,disposed=false,state={state:'idle',latest:null,retained:0};
  const bindings=new WeakMap();
  const locale=()=>((typeof options.locale==='function'?options.locale():options.locale)||root.GameI18n?.locale)==='ja'?'ja':'zh-Hant';
  const text=(tc,ja)=>locale()==='ja'?ja:tc;
  const translate=value=>root.GameI18n?.t?root.GameI18n.t(String(value??''),locale()):String(value??'');
  function read(){
   if(!storage)throw Error('storage');
   const raw=storage.getItem(STORAGE_KEY);if(!raw)return [];
   let value;try{value=JSON.parse(raw);}catch{return [];}
   if(value?.version!==1||!Array.isArray(value.items))return [];
   return value.items.slice(0,LIMIT).filter(row=>{
    try{const save=envelope(row.raw);return typeof row.id==='string'&&/^[0-9]+-[0-9]+$/.test(row.id)&&Number.isFinite(row.savedAt)&&row.savedAt>=0&&row.scenario===save.scenario&&typeof row.title==='string'&&row.title.length<=300&&typeof row.reason==='string'&&row.reason.length<=40;}catch{return false;}
   });
  }
  function metadata(row){
   const g=envelope(row.raw).state;
   return {id:row.id,savedAt:row.savedAt,scenario:row.scenario,title:row.title,reason:row.reason,year:g.year,month:g.month,day:g.day,turn:g.turn,phase:g.phase,player:g.player};
  }
  function list(){try{return read().map(metadata);}catch{return [];}}
  function notify(value){
   if(disposed)return;
   state={...value};refresh();
   try{options.onStatus?.(status());}catch{/* Status presentation cannot interrupt the campaign. */}
  }
  function status(){return {...state,latest:state.latest?{...state.latest}:null};}
  const initial=list();state={state:initial.length?'saved':'idle',latest:initial[0]||null,retained:initial.length};
  function current(item){return !disposed&&item.token===epoch&&!isBusy()&&fingerprint(getView())===item.fingerprint;}
  function errorKind(error){return error?.name==='QuotaExceededError'||[22,1014].includes(error?.code)?'quota':error?.message==='invalid'?'invalid':'storage';}
  async function run(item){
   running=true;let result;
   try{
    if(!current(item)){result={ok:false,skipped:'stale'};return;}
    notify({...state,state:'saving',reason:item.reason});
    const raw=await options.getRawSave();
    if(!current(item)){result={ok:false,skipped:'stale'};return;}
    let value;try{value=envelope(raw);}catch{throw Error('invalid');}
    if(!matches(value,item.view)){result={ok:false,skipped:'stale'};return;}
    const previous=read();
    if(previous[0]?.raw===raw){
     notify({state:'saved',latest:metadata(previous[0]),retained:previous.length});result={ok:true,skipped:'duplicate'};return;
    }
    const savedAt=now(),row={id:String(savedAt)+'-'+String(++serial),savedAt,scenario:value.scenario,title:String(item.view.catalog?.title||value.scenario).slice(0,300),reason:item.reason,raw};
    let rows=[row,...previous].slice(0,LIMIT),lastError;
    // setItem is atomic: on quota failure the previous recovery points survive.
    // A smaller retained set can still fit without deleting a manual save.
    while(rows.length){
     try{storage.setItem(STORAGE_KEY,JSON.stringify({version:1,items:rows}));lastError=null;break;}
     catch(error){lastError=error;if(errorKind(error)!=='quota')break;rows=rows.slice(0,-1);}
    }
    if(lastError)throw lastError;
    notify({state:'saved',latest:metadata(row),retained:rows.length,reduced:rows.length<Math.min(LIMIT,previous.length+1)});
    result={ok:true,id:row.id,retained:rows.length};
   }catch(error){
    if(current(item))notify({...state,state:'error',error:errorKind(error),reason:item.reason});
    result={ok:false,error:errorKind(error)};
   }finally{
    item.resolve(result||{ok:false,skipped:'stale'});running=false;
    if(queued){const next=queued;queued=null;void run(next);}
    else if(!disposed&&state.state==='saving'){
     const rows=list();notify({state:rows.length?'saved':'idle',latest:rows[0]||null,retained:rows.length});
    }
   }
  }
  function checkpoint(reason='turn'){
   if(disposed)return Promise.resolve({ok:false,skipped:'disposed'});
   const view=getView(),key=fingerprint(view);
   if(!key||isBusy())return Promise.resolve({ok:false,skipped:!key?'no-game':'busy'});
   const token=++epoch;
   return new Promise(resolve=>{
    const item={token,view,fingerprint:key,reason:String(reason).slice(0,40),resolve};
    if(running){queued?.resolve({ok:false,skipped:'superseded'});queued=item;}else void run(item);
   });
  }
  function invalidate(){epoch++;queued?.resolve({ok:false,skipped:'stale'});queued=null;}
  function label(row){
   const period=({1:['上旬','上旬'],11:['中旬','中旬'],21:['下旬','下旬']}[row.day]||[String(row.day)+'日',String(row.day)+'日'])[locale()==='ja'?1:0];
   const date=Number.isFinite(row.savedAt)?new Date(row.savedAt).toLocaleString(locale()==='ja'?'ja-JP':'zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}):'';
   return `${translate(row.title)} · ${row.year}年${row.month}月${period} · ${text('第','第')}${row.turn}${text('旬','旬')} · ${date}`;
  }
  function statusText(){
   if(state.state==='saving')return text('正在自動儲存……','自動保存中……');
   if(state.state==='error')return text('自動儲存未完成，戰役仍可繼續。請手動下載存檔。','自動保存できませんでした。戦役は続行できます。手動でセーブファイルを保存してください。');
   if(state.latest)return text('已自動儲存：','自動保存済み：')+label(state.latest)+(state.reduced?text('（空間不足，保留較少恢復點）','（空き容量不足のため復元ポイントを削減）'):'');
   return text('每旬結束、戰鬥結算後自動儲存，僅保留在此瀏覽器。','旬の終了・戦闘結果の確定後に、このブラウザーだけに自動保存します。');
  }
  function statusHtml(){return `<span class="small" data-autosave-status data-l10n-native="${locale()}" role="status" aria-live="polite">${escape(statusText())}</span>`;}
  function recoveryBody(){
   const rows=list();
   return `<h3>${text('自動儲存恢復點','自動保存の復元ポイント')}</h3><p class="small">${text('保留最近3份；空間不足時會減少份數。恢復前會再次確認，不會自動覆寫目前戰役或手動存檔。','直近3件を保持し、空き容量が足りない場合は件数を減らします。復元前に確認し、現在の戦役や手動セーブを自動では上書きしません。')}</p>${rows.length?`<div class="save-actions">${rows.map(row=>`<button type="button" data-autosave-recover="${escape(row.id)}">${escape(label(row))}</button>`).join('')}</div>`:`<p class="small">${text('尚無自動儲存恢復點。','自動保存の復元ポイントはまだありません。')}</p>`}<p class="small" data-autosave-recovery-message role="status" aria-live="polite"></p>`;
  }
  function recoveryHtml(){return `<section data-autosave-recovery data-l10n-native="${locale()}">${recoveryBody()}</section>`;}
  function refresh(container=root.document){
   if(!container?.querySelectorAll)return;
   for(const node of container.querySelectorAll('[data-autosave-status]')){node.textContent=statusText();node.setAttribute('data-l10n-native',locale());}
   for(const node of container.querySelectorAll('[data-autosave-recovery]')){node.innerHTML=recoveryBody();node.setAttribute('data-l10n-native',locale());}
  }
  async function restore(id,{confirm}={}){
   if(disposed||isBusy())return {ok:false,skipped:'busy'};
   const key=fingerprint(getView());let row;
   try{row=read().find(value=>value.id===id);}catch{return {ok:false,error:'storage'};}
   if(!row)return {ok:false,error:'missing'};
   // An explicit confirmation is mandatory. The caller owns the visible dialog.
   if(typeof confirm!=='function')return {ok:false,skipped:'unconfirmed'};
   const entry=metadata(row),token=epoch;
   let approved;try{approved=await confirm(entry,text('恢復此自動存檔？目前未保存的進度將被取代。','この自動セーブを復元しますか？現在の未保存の進行は置き換えられます。'));}catch{return {ok:false,skipped:'cancelled'};}
   if(!approved)return {ok:false,skipped:'cancelled'};
   const guard=()=>!disposed&&!isBusy()&&fingerprint(getView())===key&&epoch===token;
   if(!guard())return {ok:false,skipped:'stale'};
   // Invalidate delayed exports before handing the original bytes to validation.
   invalidate();const restoreEpoch=epoch;
   const loadGuard=()=>!disposed&&!isBusy()&&fingerprint(getView())===key&&epoch===restoreEpoch;
   try{const loaded=await options.loadRawSave(row.raw,loadGuard);return loaded?{ok:true,id}:{ok:false,error:'load'};}
   catch{return {ok:false,error:'load'};}
  }
  function bindRecovery(container,{confirm}={}){
   if(!container?.addEventListener)return;
   const existing=bindings.get(container);if(existing){existing.confirm=confirm;return;}
   const binding={confirm};bindings.set(container,binding);
   container.addEventListener('click',async event=>{
    const button=event.target.closest?.('[data-autosave-recover]');if(!button||!container.contains(button))return;
    button.disabled=true;
    const result=await restore(button.dataset.autosaveRecover,{confirm:binding.confirm});
    button.disabled=false;
    const message=container.querySelector('[data-autosave-recovery-message]');
    if(message&&!result.ok)message.textContent=result.skipped==='cancelled'?'':result.skipped==='stale'?text('進度已更新，請重新選擇恢復點。','進行が更新されました。復元ポイントを選び直してください。'):text('無法恢復，當前戰役未被此操作取代。','復元できませんでした。この操作による戦役の置き換えは行っていません。');
   });
  }
  function dispose(){invalidate();disposed=true;}
  return {checkpoint,list,status,statusText,statusHtml,recoveryHtml,bindRecovery,restore,refresh,invalidate,dispose};
 }
 const api={create,STORAGE_KEY,LIMIT};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameAutosave=api;
})(typeof window==='object'?window:globalThis);
