/* Presentation-only portrait lookup. Runtime IDs never become NES byte IDs. */
'use strict';
(function(root){
 const INDEX='/assets/portraits/index.json',SIZES=new Set(['roster','library','battle','duel','detail']);
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const pathPattern=/^\/assets\/portraits\/(?:original|generated)\/[A-Za-z0-9_-]+\.png$/;
 const enhancedPathPattern=/^\/assets\/portraits\/enhanced\/[A-Za-z0-9_-]{1,128}\.png$/;
 const personPattern=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
 function validIndex(value){
  if(!value||value.schema!=='tk2-portraits-v1'||!Number.isInteger(value.width)||value.width<1||value.width>256||
   !Number.isInteger(value.height)||value.height<1||value.height>256||!value.people||typeof value.people!=='object'||Array.isArray(value.people))throw new Error('Invalid portrait index');
  const people=Object.create(null);
  for(const[id,row]of Object.entries(value.people)){
   if(!personPattern.test(id)||!row||!['nes_original','generated'].includes(row.kind)||!pathPattern.test(row.path)||
    (row.kind==='nes_original'&&(!Number.isInteger(row.original_id)||row.original_id<0||row.original_id>236)))throw new Error('Invalid portrait entry');
   const entry={path:row.path,kind:row.kind,original_id:row.kind==='nes_original'?row.original_id:null};
   if(Object.prototype.hasOwnProperty.call(row,'enhanced')){
    const variant=row.enhanced;
    if(!variant||typeof variant!=='object'||Array.isArray(variant)||typeof variant.path!=='string'||!enhancedPathPattern.test(variant.path)||variant.width!==128||variant.height!==160)throw new Error('Invalid enhanced portrait entry');
    entry.enhanced=Object.freeze({path:variant.path,width:variant.width,height:variant.height});
   }
   people[id]=Object.freeze(entry);
  }
  return Object.freeze({schema:value.schema,width:value.width,height:value.height,people:Object.freeze(people)});
 }
 function create(options={}){
  const doc=options.document||root.document,i18n=options.i18n||root.GameI18n,fetcher=options.fetch||root.fetch?.bind(root);
  const timeout=Number.isFinite(options.timeoutMs)&&options.timeoutMs>0?options.timeoutMs:10000;
  const catalogMaps=new WeakMap(),failedPaths=new Set(),generated=new Map();let index=null,loading=null,status='idle',attached=false;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant';
  const text=(tc,ja)=>locale()==='ja'?ja:tc;
  const labelName=value=>i18n?.t?i18n.t(String(value??''),locale()):String(value??'');
  function personId(catalog,runtimeId){
   if(typeof runtimeId==='string'&&/^clerk-[0-9]{6,12}$/.test(runtimeId))return runtimeId;
   if(!catalog||typeof catalog!=='object'||!Array.isArray(catalog.library))return null;
   let map=catalogMaps.get(catalog);
   if(!map){map=new Map(catalog.library.filter(p=>p&&typeof p.person_id==='string').map(p=>[String(p.id),p.person_id]));catalogMaps.set(catalog,map);}
   return map.get(String(runtimeId))||null;
  }
  function registerGenerated(pool){
   generated.clear();const people=Array.isArray(pool?.people)?pool.people:Object.values(pool?.people||{});
   for(const person of people){if(!/^clerk-[0-9]{6,12}$/.test(person?.id||'')||!/^clerk-[123]$/.test(person?.portrait||''))continue;
    generated.set(person.id,Object.freeze({path:`/assets/civil-staff/${person.portrait}.png`,kind:'generated',fictional:true,width:32,height:40,original_id:null}));}
  }
  function entry(id){return typeof id==='string'?(generated.get(id)||index?.people[id]||null):null;}
  function selectedAsset(row){
   if(!row)return null;
   if(row.enhanced&&!failedPaths.has(row.enhanced.path))return{...row.enhanced,enhanced:true};
   return failedPaths.has(row.path)?null:{path:row.path,width:row.width||index?.width||32,height:row.height||index?.height||40,enhanced:false};
  }
  function description(row,enhanced=false){
   if(!row)return text(status==='idle'||status==='loading'?'肖像準備中':'肖像待補',status==='idle'||status==='loading'?'肖像を準備中':'肖像は未設定です');
   if(row.fictional)return text('架空武將・共用原版像素肖像','架空の武将・共通の原作ドット肖像');
   if(enhanced)return row.kind==='nes_original'?text('原版像素肖像・明暗強化','原作のドット肖像・陰影強化'):text('新增繪製肖像・明暗強化・非史實容貌','新規制作の肖像・陰影強化・史実の容貌ではありません');
   return row.kind==='nes_original'?text('原版像素肖像','原作のドット肖像'):text('新增繪製肖像・非史實容貌','新規制作の肖像・史実の容貌ではありません');
  }
  function contents(id,rawName,source){
   const row=entry(id),asset=selectedAsset(row),available=!!asset,name=labelName(rawName),width=asset?.width||index?.width||32,height=asset?.height||index?.height||40;
   const missing=row&&!available?text('肖像載入失敗','肖像を読み込めませんでした'):description(null);
   const alt=available?`${name}${text('的肖像','の肖像')}`:`${name} · ${missing}`;
   const image=available?`<img data-portrait-image src="${escape(asset.path)}" width="${width}" height="${height}" alt="${escape(alt)}" loading="lazy" decoding="async" draggable="false">`:
    `<span class="portrait-placeholder" role="img" aria-label="${escape(alt)}"><span aria-hidden="true">？</span></span>`;
   return `<span class="portrait-frame">${image}</span>${source?`<span class="portrait-source" data-l10n-native="${locale()}">${escape(available?description(row,asset.enhanced):missing)}</span>`:''}`;
  }
  function html(id,name,{size='roster',source=false}={}){
   if(!SIZES.has(size))size='roster';
   const safeId=typeof id==='string'&&personPattern.test(id)?id:'';
   return `<span class="officer-portrait portrait-${size}" data-portrait-person="${escape(safeId)}" data-portrait-name="${escape(name)}" data-portrait-source="${source?'1':'0'}" data-l10n-native="${locale()}">${contents(safeId,name,source)}</span>`;
  }
  function refresh(surface=doc){
   if(!surface?.querySelectorAll)return;
   for(const node of surface.querySelectorAll('[data-portrait-person]')){
    node.setAttribute('data-l10n-native',locale());
    node.innerHTML=contents(node.dataset.portraitPerson,node.dataset.portraitName,node.dataset.portraitSource==='1');
   }
  }
  function imageError(event){
   const image=event.target;if(!image?.hasAttribute?.('data-portrait-image'))return;
   const frame=image.closest?.('[data-portrait-person]'),row=entry(frame?.dataset?.portraitPerson);
   if(!row)return;
   const attempted=image.getAttribute?.('src')||selectedAsset(row)?.path;
   if(attempted!==row.path&&attempted!==row.enhanced?.path)return;
   failedPaths.add(attempted);refresh();
  }
  function attach(){
   if(attached||!doc?.addEventListener)return;attached=true;
   doc.addEventListener('error',imageError,true);
   doc.addEventListener('game-language-change',()=>refresh());
  }
  function load(){
   if(loading)return loading;
   status='loading';attach();
   loading=(async()=>{
    const controller=new AbortController();let timer;
    try{
     if(typeof fetcher!=='function')throw new Error('Portrait index unavailable');
     const read=(async()=>{const response=await fetcher(INDEX,{signal:controller.signal});if(!response.ok)throw new Error('Portrait index unavailable');return validIndex(await response.json());})();
     index=await Promise.race([read,new Promise((_resolve,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error('Portrait index timeout'));},timeout);})]);
     status='ready';refresh();return true;
    }catch{status='unavailable';refresh();return false;}
    finally{clearTimeout(timer);}
   })();
   return loading;
  }
  return Object.freeze({load,html,personId,entry,registerGenerated,refresh,imageError,get status(){return status;}});
 }
 if(typeof module==='object'&&module.exports)module.exports={create,validIndex};else root.GamePortraits=create();
})(typeof window==='object'?window:globalThis);
