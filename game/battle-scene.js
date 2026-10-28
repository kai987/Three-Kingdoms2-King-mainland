/* NES-style4× rendering with native assets and separately documented new duel art.
 * The server receipts describe already committed actions. Rendering, skipping,
 * resizing and changing language never submit commands or sample game RNG. */
'use strict';
(function(root){
 const WIDTH=256,HEIGHT=240,RESOLUTION_SCALE=4,SCHEMA='tk2-battle-presentation-v1';
 const FIELD_WIDTH=496,FIELD_HEIGHT=304,FIELD_HUD=80;
 const PAPER='#ffd4c8',INK='#000000',ASSET_ROOT='/assets/battle-original/',ENHANCED_ROOT='/assets/battle-enhanced/';
 const EFFECTS=new Set(['fire','trap','strike','water','confuse','supply','feint','rock','area','chain','crossbow','surrender','ambush','flood','inferno','guard']);
 const KINDS=new Set(['move','attack','tactic','ambush','duel_start','duel_action','retreat']);
 const DUEL_ACTIONS=Object.freeze(['idle','strike','guard','feint','withdraw','desperate','hit','defeat']);
 const SOLDIER_ACTIONS=Object.freeze(['idle','march','ready','attack','guard','hit','retreat','defeat']);
 const SOLDIER_TYPES=Object.freeze({infantry:16,archer:16,cavalry:24});
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const reference=id=>Number.isInteger(id)&&id>=0&&id<1200||typeof id==='string'&&/^clerk-[0-9]{6,12}$/.test(id)&&Number(id.slice(6))>=1&&Number(id.slice(6))<=1000000&&id==='clerk-'+String(Number(id.slice(6))).padStart(6,'0');
 const bounded=(n,max)=>Number.isInteger(n)&&n>=0&&n<=max;
 const cell=value=>!!value&&bounded(value.x,30)&&bounded(value.y,18);
 function tacticalView(view){
  const battle=view?.game?.battle,saved=battle?.extended?.tactical,value=view?.catalog?.battle_tactical;
  return saved?.schema==='tk2-battle-tactical-v1'&&value?.schema==='tk2-battle-tactical-view-v1'&&value.battle_id===battle.id&&value.round===battle.round&&value.map_id===saved.map_id&&value.side===saved.side&&value.grid?.columns===31&&value.grid?.rows===19&&value.grid?.tile_size===16&&value.actors&&typeof value.actors==='object'?value:null;
 }
 function unitPosition(view,id){const value=view?.game?.battle?.extended?.tactical?.positions?.[String(id)];return cell(value)?value:null;}
 const clone=value=>JSON.parse(JSON.stringify(value));
 // Group on canonical names, before locale translation; simplified/traditional
 // spellings identify the same family, counted independently for each army.
 const COMPOUND_SURNAMES=new Set(['公孫','公仇','司馬','諸葛','夏侯','皇甫','太史','上官','歐陽','令狐','尉遲','呼延','宇文','慕容','毌丘','鮮于','閭丘','東方','南宮','軒轅','鍾離','澹臺','申屠','仲長','第五','段干','長孫','拓跋','濮陽','羊舌','百里','淳于']);
 const SURNAME_EQUIVALENTS={'孙':'孫','马':'馬','诸':'諸','欧':'歐','迟':'遲','鲜':'鮮','闾':'閭','东':'東','宫':'宮','轩':'軒','辕':'轅','钟':'鍾','离':'離','台':'臺','长':'長','阳':'陽','刘':'劉','张':'張','陈':'陳','许':'許','郑':'鄭','卫':'衛','黄':'黃','赵':'趙','邓':'鄧','庞':'龐','陆':'陸','吕':'呂','吴':'吳','严':'嚴','华':'華','韩':'韓','贾':'賈','顾':'顧','阎':'閻','韦':'韋','费':'費','乐':'樂','满':'滿','鲁':'魯','骆':'駱','钱':'錢','乔':'喬','蒋':'蔣','冯':'馮','谯':'譙','步':'歩','郤':'郄'};
 function familyName(name){
  const chars=Array.from(String(name??'').trim().normalize('NFKC')).map(c=>SURNAME_EQUIVALENTS[c]||c),compound=chars.slice(0,2).join('');
  return COMPOUND_SURNAMES.has(compound)?compound:chars[0]||'';
 }
 function markerLabels(units,nameFor,displayName=nameFor){
  const families=new Map(),names=new Map();
  for(const unit of units){const family=familyName(nameFor(unit.id));names.set(unit.id,family);if(!family)continue;let side=families.get(unit.side);if(!side){side=new Map();families.set(unit.side,side);}side.set(family,(side.get(family)||0)+1);}
  return new Map(units.map(unit=>{const chars=Array.from(String(displayName(unit.id)??'').trim());return [unit.id,(families.get(unit.side)?.get(names.get(unit.id))>1?chars.at(-1):chars[0])||''];}));
 }
 function attackStage(progress,skipped=false){
  const p=Math.max(0,Math.min(1,progress)),tick=Math.floor(p*20);
  if(skipped)return {phase:'result',shift:0,tick:0,resolved:true};
  if(p<.3)return {phase:'approach',shift:Math.round(p/.3*40),tick,resolved:false};
  if(p<.66)return {phase:'clash',shift:40+(tick%2?1:-1),tick,resolved:p>=.55};
  if(p<.88)return {phase:'recoil',shift:Math.round((.88-p)/.22*40),tick,resolved:true};
  return {phase:'result',shift:0,tick,resolved:true};
 }
 function soldierActionPose(scene,id,progress){
  const p=Number.isFinite(progress)?Math.max(0,Math.min(1,progress)):0;
  const before=scene?.before?.units?.find(u=>u.id===id),after=scene?.after?.units?.find(u=>u.id===id);
  if(!before||!after)return 'idle';
  if(p>=.55&&after.troops===0)return 'defeat';
  if(scene.kind==='retreat')return before.side===scene.own&&p<.9?'retreat':'idle';
  if(scene.skipped)return 'idle';
  if(p>=.55&&p<.73&&(after.troops<before.troops||after.health<before.health))return 'hit';
  if(scene.kind==='attack'){
   const phase=attackStage(p).phase;
   if(phase==='approach')return 'march';
   if(phase==='recoil')return 'retreat';
   if(phase==='result')return 'idle';
   if(id!==scene.actor&&before.guard>0)return 'guard';
   return p<.38||id!==scene.actor?'ready':'attack';
  }
  if(p<.22||p>=.9)return 'idle';
  if(id===scene.actor&&scene.success){
   if(scene.effect==='guard')return 'guard';
   if(scene.kind==='ambush'||['strike','crossbow','ambush'].includes(scene.effect))return 'attack';
  }
  return 'ready';
 }
 function validSnapshot(s){
  if(!s||Object.keys(s).sort().join(',')!=='duel,outcome,round,units'||!bounded(s.round,1000000)||s.round<1||![null,'victory','defeat','retreat'].includes(s.outcome)||!Array.isArray(s.units)||s.units.length>20)return false;
  const seen=new Set();
  for(const u of s.units){if(!u||Array.isArray(u)||Object.keys(u).sort().join(',')!=='energy,guard,health,id,side,stunned,troops'||!reference(u.id)||seen.has(String(u.id))||!['attackers','defenders'].includes(u.side)||!bounded(u.troops,999)||!bounded(u.health,99)||!bounded(u.energy,18)||!bounded(u.guard,2)||!bounded(u.stunned,1))return false;seen.add(String(u.id));}
  if(s.duel===null)return true;
  if(!s.duel||Object.keys(s.duel).sort().join(',')!=='actor,round,target'||!reference(s.duel.actor)||!reference(s.duel.target)||!bounded(s.duel.round,21)||s.duel.round<1)return false;
  const a=s.units.find(u=>u.id===s.duel.actor),t=s.units.find(u=>u.id===s.duel.target);return !!a&&!!t&&a.side!==t.side;
 }
 function validMovement(move){
  if(!move||Array.isArray(move)||Object.keys(move).sort().join(',')!=='cost,map_id,path'||!bounded(move.cost,60)||move.cost<1||!/^original-[0-2][0-9]$/.test(move.map_id||'')||!Array.isArray(move.path)||move.path.length<2||move.path.length>61||move.cost<move.path.length-1)return false;
  const seen=new Set();
  return move.path.every((point,index)=>{
   if(!cell(point)||Object.keys(point).sort().join(',')!=='x,y')return false;
   const key=point.x+','+point.y,previous=move.path[index-1];
   if(seen.has(key)||previous&&Math.abs(previous.x-point.x)+Math.abs(previous.y-point.y)!==1)return false;
   seen.add(key);return true;
  });
 }
 function movementStage(scene,progress){
  if(scene?.kind!=='move'||!validMovement(scene.move))return null;
  const path=scene.move.path,p=Math.max(0,Math.min(1,Number.isFinite(progress)?progress:0)),steps=path.length-1,travel=p*steps,index=Math.min(steps,Math.floor(travel)),from=path[index],to=path[Math.min(steps,index+1)],fraction=index===steps?0:Math.min(1,(travel-index)/.72);
  return {index,steps,gx:from.x,gy:from.y,x:Math.round((from.x+(to.x-from.x)*fraction)*16+8),y:Math.round((from.y+(to.y-from.y)*fraction)*16+8)};
 }
 function receiptScenes(receipt,battleId,revision){
  if(!receipt||Object.keys(receipt).sort().join(',')!=='revision,scenes,schema'||receipt.schema!==SCHEMA||receipt.revision!==revision||!Array.isArray(receipt.scenes)||receipt.scenes.length>192)return [];
  if(!receipt.scenes.every(s=>{
   if(!s||Object.keys(s).sort().join(',')!=='actor,after,battle_id,before,counter,effect,kind,move,own,reply,skipped,success,tactic,target'||!KINDS.has(s.kind)||s.battle_id!==battleId||!['attackers','defenders'].includes(s.own)||typeof s.counter!=='boolean'||typeof s.success!=='boolean'||typeof s.skipped!=='boolean'||!validSnapshot(s.before)||!validSnapshot(s.after))return false;
   if(s.before.units.length!==s.after.units.length||s.before.units.some(u=>!s.after.units.some(v=>v.id===u.id&&v.side===u.side)))return false;
   if(s.kind==='move'){const a=s.before.units.find(u=>u.id===s.actor);if(!reference(s.actor)||!a||a.side!==s.own||a.troops<=0||a.health<=0||s.target!==null||!validMovement(s.move)||s.success!==true||s.skipped!==false)return false;}
   else if(s.kind==='retreat'){if(s.actor!==null||s.target!==null)return false;}
   else{const a=s.before.units.find(u=>u.id===s.actor),t=s.before.units.find(u=>u.id===s.target);if(!reference(s.actor)||!reference(s.target)||!a||!t||a.side!==s.own||t.side===s.own)return false;}
   if(['tactic','ambush'].includes(s.kind)){if(!bounded(s.tactic,15)||!EFFECTS.has(s.effect))return false;}else if(s.tactic!==null||s.effect!==null)return false;
   if(s.kind==='duel_action'){if(!['strike','guard','feint','withdraw','desperate'].includes(s.move)||(s.move==='withdraw'?s.reply!==null:!['strike','guard','feint','desperate'].includes(s.reply)))return false;}
   else if(s.kind==='move'){if(s.reply!==null)return false;}
   else if(s.move!==null||s.reply!==null)return false;
   return true;
  }))return [];
  return clone(receipt.scenes);
 }
 function snapshot(view){
  const b=view?.game?.battle;if(!b)return null;
  return {round:b.round,outcome:b.outcome,duel:b.extended?.duel?{actor:b.extended.duel.actor,target:b.extended.duel.target,round:b.extended.duel.round}:null,
   units:['attackers','defenders'].flatMap(side=>b[side].map(u=>({id:u.id,side,troops:u.troops,health:b.extended.support[String(u.id)].health,energy:b.extended.support[String(u.id)].energy,guard:b.extended.support[String(u.id)].guard,stunned:b.extended.support[String(u.id)].stunned})))};
 }
 function changes(scene){return scene.after.units.map(u=>{const old=scene.before.units.find(a=>a.id===u.id);return old?{id:u.id,side:u.side,troops:u.troops-old.troops,health:u.health-old.health,energy:u.energy-old.energy,guard:u.guard-old.guard,stunned:u.stunned-old.stunned}:null;}).filter(x=>x&&Object.entries(x).some(([key,value])=>!['id','side'].includes(key)&&value!==0));}
 function campaignKey(view){return [view?.catalog?.scenario_id,view?.game?.player,view?.game?.seed].join(':');}
 function duration(scene){return scene.kind==='move'&&validMovement(scene.move)?Math.max(220,(scene.move.path.length-1)*140):scene.kind==='attack'&&!scene.skipped?2200:scene.kind==='duel_action'?1000:scene.kind==='tactic'?1000:scene.kind==='duel_start'?700:scene.kind==='ambush'?850:700;}
 function validAssetPath(path){return typeof path==='string'&&/^\/assets\/battle-original\/[a-zA-Z0-9_/-]+\.png$/.test(path);}
 function validEnhancedAssetPath(path){return typeof path==='string'&&/^\/assets\/battle-enhanced\/[a-z0-9_-]+\.png$/.test(path);}
 function validActionAtlas(row){
  return !!row&&validEnhancedAssetPath(row.path)&&row.width===4096&&row.height===384&&row.logical_width===128&&row.logical_height===96&&row.anchor?.x===64&&row.anchor?.y===96&&Array.isArray(row.frames)&&row.frames.length===DUEL_ACTIONS.length&&row.frames.every((f,i)=>f?.action===DUEL_ACTIONS[i]&&Array.isArray(f.source_rect)&&f.source_rect.length===4&&f.source_rect.every((v,j)=>v===[i*512,0,512,384][j]));
 }
 function validSoldierAtlas(row,size){
  const pixels=size*RESOLUTION_SCALE;
  return !!row&&validEnhancedAssetPath(row.path)&&row.facing==='right'&&row.width===pixels*SOLDIER_ACTIONS.length&&row.height===pixels&&row.logical_width===size&&row.logical_height===size&&Array.isArray(row.frames)&&row.frames.length===SOLDIER_ACTIONS.length&&row.frames.every((f,i)=>f?.action===SOLDIER_ACTIONS[i]&&Array.isArray(f.source_rect)&&f.source_rect.length===4&&f.source_rect.every((v,j)=>v===[i*pixels,0,pixels,pixels][j]));
 }
 function validSoldierLibrary(data){
  return !!(data&&data.schema==='tk2-soldier-actions-v1'&&data.scale===RESOLUTION_SCALE&&Array.isArray(data.actions)&&data.actions.length===SOLDIER_ACTIONS.length&&data.actions.every((action,i)=>action===SOLDIER_ACTIONS[i])&&data.types&&typeof data.types==='object'&&!Array.isArray(data.types)&&Object.keys(data.types).length===3&&Object.entries(SOLDIER_TYPES).every(([type,size])=>validSoldierAtlas(data.types[type]?.friendly,size)&&validSoldierAtlas(data.types[type]?.enemy,size)));
 }
 function duelActionPose(scene,id,progress){
  if(scene?.kind!=='duel_action')return 'idle';
  const move=id===scene.actor?scene.move:scene.reply,p=Math.max(0,Math.min(1,progress)),before=scene.before.units.find(u=>u.id===id),after=scene.after.units.find(u=>u.id===id);
  if(p>=.68&&after&&(after.health===0||after.troops===0&&after.health<=1))return 'defeat';
  if(p>=.54&&p<.79&&before&&after&&after.health<before.health)return 'hit';
  if(move==='withdraw')return p>=.15?'withdraw':'idle';
  if(['strike','guard','feint','desperate'].includes(move)&&p>=.18&&p<.88)return move;
  return 'idle';
 }
 function duelMotion(move,progress,bow=false){
  const p=Math.max(0,Math.min(1,progress));
  if(move==='withdraw')return -Math.round(p*38);
  if(move==='guard'||!move)return 0;
  if(move==='feint')return Math.round(Math.sin(p*Math.PI*2)*14);
  return Math.round(Math.sin(p*Math.PI)*(bow?3:move==='desperate'?34:26));
 }
 function create(options={}){
  const doc=options.document||root.document,i18n=options.i18n||root.GameI18n,portraits=options.portraits||root.GamePortraits,officerChoices=options.officerChoices||root.GameOfficerChoices,duelAppearance=options.duelAppearance||root.GameDuelAppearance,battlefields=options.battlefields||root.GameBattlefields;
  const fetcher=options.fetch||root.fetch?.bind(root),ImageType=options.Image||root.Image;
  const raf=options.requestAnimationFrame||root.requestAnimationFrame?.bind(root),caf=options.cancelAnimationFrame||root.cancelAnimationFrame?.bind(root);
  const images=new Map(),duelRendering=new Map(),duelLoadouts=new Map();let manifest=null,enhanced=null,soldiers=null,assetStatus='idle',assetsPromise=null,loadoutSignature='';
  let host=null,canvas=null,ctx=null,view=null,selection={},queue=[],key='',observed=null,playing=false,frame=null,handle=null,resolvePlay=null,resizeObserver=null,disposed=false,outcomeCue=null,animationPositions=null;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant';
  const text=(tc,ja)=>locale()==='ja'?ja:tc;
  const translate=value=>i18n?.t?i18n.t(value,locale()):String(value??'');
  const canonicalName=id=>view?.catalog?.names?.[String(id)]||options.name?.(id)||text('武將','武将');
  const person=id=>translate(options.name?.(id)||canonicalName(id));
  const reduced=()=>!!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  function loadImage(path){
   if(images.has(path))return images.get(path);
   const row={image:null,status:'loading',promise:null};images.set(path,row);
   row.promise=new Promise(resolve=>{
    if(!ImageType){row.status='unavailable';resolve(false);return;}
    const image=new ImageType();row.image=image;let timeout;
    const finish=okay=>{if(row.status!=='loading')return;clearTimeout(timeout);row.status=okay?'ready':'unavailable';resolve(okay);if(!disposed&&host?.isConnected!==false)draw();};
    image.onload=()=>finish(true);image.onerror=()=>finish(false);timeout=setTimeout(()=>finish(false),6000);image.src=root.GamePaths?.asset(path)||path;
   });return row;
  }
  function imageFor(path){if(!path)return null;const row=loadImage(path);return row.status==='ready'?row.image:null;}
  async function readManifest(url,validate){
   let timer;const controller=typeof AbortController==='function'?new AbortController():null;
   try{
    const read=(async()=>{const response=await fetcher(url,controller?{signal:controller.signal}:{});if(!response.ok)throw Error('assets');return response.json();})();
    const data=await Promise.race([read,new Promise((_,reject)=>{timer=setTimeout(()=>{controller?.abort();reject(Error('timeout'));},6000);})]);
    const paths=validate(data);if(!paths)return null;
    await Promise.all(paths.map(path=>loadImage(path).promise));return {data,paths};
   }catch{return null;}finally{clearTimeout(timer);}
  }
  async function load(){
   if(assetsPromise)return assetsPromise;
   assetStatus='loading';assetsPromise=(async()=>{
    const [native,hd]=await Promise.all([
     readManifest(ASSET_ROOT+'index.json',data=>{
      if(data?.schema!=='tk2-battle-original-v1'||!data.backgrounds||!data.sprites)return null;
      const paths=[...Object.values(data.backgrounds).map(r=>r?.path),...Object.values(data.sprites).flatMap(r=>(r?.frames||[]).map(f=>f.path))].filter(Boolean);
      return paths.length&&paths.length<=256&&paths.every(validAssetPath)?paths:null;
     }),
     readManifest(ENHANCED_ROOT+'index.json',data=>{
      if(data?.schema!=='tk2-battle-enhanced-v1'||data.scale!==RESOLUTION_SCALE||!data.backgrounds||!data.sprites||!data.duelists)return null;
      const eager=[...Object.values(data.backgrounds),...Object.values(data.sprites).flatMap(r=>r?.frames||[])],legacy=Object.values(data.duelists).flatMap(horses=>Object.values(horses||{}).flatMap(r=>r?.frames||[])),frames=[...eager,...legacy];
      if(!frames.length||frames.length>512||!frames.every(f=>f&&validEnhancedAssetPath(f.path)&&Number.isInteger(f.logical_width)&&Number.isInteger(f.logical_height)&&f.logical_width>0&&f.logical_width<=1024&&f.logical_height>0&&f.logical_height<=1024&&f.width===f.logical_width*RESOLUTION_SCALE&&f.height===f.logical_height*RESOLUTION_SCALE))return null;
      if(data.action_atlases!==undefined){if(!data.action_atlases||typeof data.action_atlases!=='object'||Array.isArray(data.action_atlases))return null;const atlases=Object.values(data.action_atlases).flatMap(horses=>Object.values(horses||{}));if(atlases.length>256||!atlases.every(validActionAtlas))return null;}
      // The cartesian atlas library is indexed here, but only the two selected
      // fighters' artwork is fetched by draw()/preloadDuelArtwork().
      return eager.map(f=>f.path);
     }),
     Promise.resolve().then(()=>duelAppearance?.load?.()).catch(()=>null),
     Promise.resolve().then(()=>battlefields?.load?.()).catch(()=>null)
    ]);
    manifest=native?.data||null;enhanced=hd?.data||null;
    // An optional bad soldier library must not disable retained backgrounds,
    // original formations or the separately validated duel artwork.
    soldiers=validSoldierLibrary(enhanced?.soldiers)?enhanced.soldiers:null;
    const paths=[...(native?.paths||[]),...(hd?.paths||[])];
    assetStatus=paths.some(path=>images.get(path)?.status==='ready')?'ready':'unavailable';
    updateText();draw();return assetStatus==='ready';
   })();return assetsPromise;
  }
  const soldierRows=()=>soldiers?Object.values(soldiers.types).flatMap(type=>[type.friendly,type.enemy]):[];
  function soldierArtworkNeedsLoad(){return soldierRows().some(row=>!images.has(row.path)||images.get(row.path).status==='loading');}
  async function preloadSoldierArtwork(){await Promise.all(soldierRows().map(row=>loadImage(row.path).promise));}
  function html(){
   const lang=locale();
   return `<div class="nes-battle" data-battle-scene data-l10n-native="${lang}"><div class="nes-battle-toolbar"><span data-battle-scene-title>${text('戰場','戦場')}</span><span data-battlefield-label></span><button type="button" data-battle-skip hidden>${text('略過演出','演出をスキップ')}</button></div><div data-duel-loadouts hidden></div><div class="nes-battle-viewport"><canvas width="1024" height="960" data-battle-canvas tabindex="0" role="img" aria-label="${text('戰場：點選旗標選將、空格預覽移動；方向鍵調整落點，Enter確認移動','戦場：旗を選び、空きマスで移動先を確認。矢印キーで調整し、Enterで移動')}"></canvas></div><p class="nes-battle-status" data-battle-caption aria-live="polite"></p><p class="visually-hidden" data-battle-description></p></div>`;
  }
  function fit(){
   const box=host?.querySelector?.('.nes-battle-viewport');if(!box||!canvas)return;
   const logicalWidth=canvas.width/RESOLUTION_SCALE||WIDTH,logicalHeight=canvas.height/RESOLUTION_SCALE||HEIGHT;
   const aspect=logicalWidth+'/'+logicalHeight;
   if(host.style&&host.style.getPropertyValue('--battle-canvas-aspect')!==aspect)host.style.setProperty('--battle-canvas-aspect',aspect);
   const layout=host?.closest?.('.battle-layout');
   if(layout?.clientWidth>660&&layout.style){
    // Size the right column from its usable height. The roster receives the
    // remaining width instead of leaving two large empty map margins.
    const desired=Math.min(logicalWidth*RESOLUTION_SCALE,Math.max(1,layout.clientWidth-248),(box.clientHeight||logicalHeight)*logicalWidth/logicalHeight);
    const size=Math.max(1,Math.floor(desired))+'px';
    if(layout.style.getPropertyValue('--battle-board-width')!==size)layout.style.setProperty('--battle-board-width',size);
    const roster=layout.querySelector?.('.battle-army-menu');if(roster&&!roster.open)roster.open=true;
   }else layout?.style?.removeProperty('--battle-board-width');
   const width=box.clientWidth||logicalWidth,height=box.clientHeight||logicalHeight;
   const scale=Math.min(RESOLUTION_SCALE,width/logicalWidth,height/logicalHeight);
   canvas.style.width=Math.max(1,Math.floor(logicalWidth*scale))+'px';canvas.style.height=Math.max(1,Math.floor(logicalHeight*scale))+'px';
  }
  function mount(element,current,selected={}){
   resizeObserver?.disconnect();host=element;view=current;selection=selected;loadoutSignature='';
   canvas=host?.querySelector?.('[data-battle-canvas]');ctx=null;
   if(canvas){canvas.width=WIDTH*RESOLUTION_SCALE;canvas.height=HEIGHT*RESOLUTION_SCALE;try{ctx=canvas.getContext('2d',{alpha:false});}catch{}canvas.onclick=clickMap;canvas.onkeydown=mapKeydown;}
   if(root.ResizeObserver&&host){resizeObserver=new root.ResizeObserver(fit);resizeObserver.observe(host.querySelector('.nes-battle-viewport')||host);}
   host?.querySelector?.('[data-battle-skip]')?.addEventListener('click',skip);
   if(host)host.dataset.sceneAssets=assetStatus;
   fit();updateText();draw();void load();return !!ctx;
  }
  function observe(kind,payload,before,after){
   const nextKey=campaignKey(after),battle=after?.game?.battle||before?.game?.battle;
   if(kind==='new'||key&&key!==nextKey){reset();}key=nextKey;
   if(!battle)return;
   const token=nextKey+':'+after.revision;if(observed===token)return;observed=token;
   queue=receiptScenes(after.presentation,battle.id,after.revision);animationPositions=null;
   if(queue.some(scene=>scene.kind==='move')){
    const tactical=after?.game?.battle?.extended?.tactical,points=new Map(Object.entries(tactical?.positions||{}).map(([id,p])=>[id,{...p}]));
    // Start from the committed final coordinates and rewind the authoritative
    // move records. This retains every earlier AI step, even if the same unit
    // moved several times during a whole-side action before attacking.
    for(const scene of [...queue].reverse())if(scene.kind==='move'){
     const path=scene.move.path,end=path.at(-1),actual=points.get(String(scene.actor));
     if(scene.move.map_id!==tactical?.map_id||!actual||actual.x!==end.x||actual.y!==end.y){queue=[];return;}
     points.set(String(scene.actor),{...path[0]});
    }
    animationPositions=points;
    if(queue[0]?.kind==='move')frame={scene:queue[0],progress:0};
   }
  }
  function rectangle(x,y,w,h,color){ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),Math.max(1,Math.round(w)),Math.max(1,Math.round(h)));}
  function line(x1,y1,x2,y2,color,width=1){
   const steps=Math.max(Math.abs(x2-x1),Math.abs(y2-y1),1);for(let t=0;t<=steps;t++)rectangle(x1+(x2-x1)*t/steps,y1+(y2-y1)*t/steps,width,width,color);
  }
  function label(value,x,y,color=INK,size=8){ctx.font=`${size}px Unifont, monospace`;ctx.textBaseline='top';ctx.fillStyle=color;ctx.fillText(String(value),Math.round(x),Math.round(y));}
  function outline(x,y,w,h,color=INK){rectangle(x,y,w,1,color);rectangle(x,y+h-1,w,1,color);rectangle(x,y,1,h,color);rectangle(x+w-1,y,1,h,color);}
  function blit(image,x,y,w=image?.width,h=image?.height,mirror=false){if(!image)return false;ctx.save();ctx.imageSmoothingEnabled=false;if(mirror){ctx.translate(Math.round(x+w),Math.round(y));ctx.scale(-1,1);ctx.drawImage(image,0,0,w,h);}else ctx.drawImage(image,Math.round(x),Math.round(y),Math.round(w),Math.round(h));ctx.restore();return true;}
  function readyFrame(kind,tick){
   for(const source of [enhanced,manifest]){
    const frames=source?.sprites?.[kind]?.frames||[],f=frames[Math.floor(tick)%Math.max(1,frames.length)],image=imageFor(f?.path);
    if(image)return {image,width:f.logical_width||image.width,height:f.logical_height||image.height};
   }return null;
  }
  function sprite(kind,x,y,tick,{mirror=false,maxWidth=32,maxHeight=32}={}){
   const row=readyFrame(kind,tick);if(!row)return false;
   const scale=Math.min(1,maxWidth/row.width,maxHeight/row.height),w=Math.round(row.width*scale),h=Math.round(row.height*scale);
   return blit(row.image,x-w/2,y-h,w,h,mirror);
  }
  function backgroundImage(kind){
   for(const source of [enhanced,manifest]){const row=source?.backgrounds?.[kind]||source?.backgrounds?.plain,image=imageFor(row?.path);if(image)return image;}return null;
  }
  function background(kind){
   const image=backgroundImage(kind);
   if(image){blit(image,0,0,256,160);return image;}
   rectangle(0,0,256,160,kind==='water'?'#1850db':'#fff0b0');return null;
  }
  function selectedField(){
   const battle=view?.game?.battle,saved=battle?.extended?.tactical,pinned=saved?.schema==='tk2-battle-tactical-v1'&&/^original-[0-2][0-9]$/.test(saved.map_id||'');
   const city=battlefields?.resolve?.(battle?.target),selected=pinned?(city?.field?.id===saved.map_id?city:battlefields?.resolveMap?.(saved.map_id)):city;
   if(!pinned&&!selected)return null;
   const field=selected?.field||{id:saved.map_id,width:FIELD_WIDTH,height:FIELD_HEIGHT,camps:[]};
   if(field.width!==FIELD_WIDTH||field.height!==FIELD_HEIGHT||!/^original-[0-2][0-9]$/.test(field.id||''))return null;
   const source=field.path?imageFor(field.path):null,image=source&&(source.naturalWidth||source.width)===FIELD_WIDTH&&(source.naturalHeight||source.height)===FIELD_HEIGHT?source:null;
   // A missing bitmap cannot change the authoritative logical board or positions.
   return {...selected,field,image,authoritative:!!pinned};
  }
  function campSlots(field){
   const cells=Array.isArray(field.camps)?field.camps:[];
   return cells.filter(cell).map(p=>({x:p.x*16+8,y:p.y*16+8}));
  }
  function positions(state){
   const out=new Map();for(const unit of state.units){const p=animationPositions?.get(String(unit.id))||unitPosition(view,unit.id);if(p)out.set(unit.id,{gx:p.x,gy:p.y,x:p.x*16+8,y:p.y*16+8});}
   if(frame?.scene.kind==='move'){const point=movementStage(frame.scene,frame.progress);if(point)out.set(frame.scene.actor,point);}return out;
  }
  function paintReachable(){
   const quote=tacticalView(view)?.actors?.[String(selection.actor)];
   for(const p of quote?.reachable||[])if(cell(p)){rectangle(p.x*16+1,p.y*16+1,14,14,'rgba(255,255,255,.18)');outline(p.x*16+1,p.y*16+1,14,14,'#a7e7ff');}
   const cursor=selection.destination;if(cell(cursor)){outline(cursor.x*16,cursor.y*16,16,16,'#ffe149');outline(cursor.x*16+1,cursor.y*16+1,14,14,INK);}
  }
  function flag(u,p,selected,enemy,attackable,marker){
   const routed=u.troops<=0||u.health<=0,color=routed?'#888888':enemy?'#b61c16':'#ffffff';rectangle(p.x-6,p.y-6,12,12,INK);rectangle(p.x-5,p.y-5,10,10,color);
   label(marker,p.x-4,p.y-4,enemy?'#ffffff':INK,8);
   if(routed){line(p.x-6,p.y-6,p.x+5,p.y+5,'#ffffff');line(p.x+5,p.y-6,p.x-6,p.y+5,'#ffffff');}
   if(attackable&&u.troops>0)outline(p.x-8,p.y-8,16,16,'#ffdf58');
   if(selected){outline(p.x-8,p.y-8,16,16,'#ffffff');outline(p.x-7,p.y-7,14,14,INK);}
  }
  function paintMap(state,field=null){
   const b=view.game.battle,own=b.attacker===view.game.player?'attackers':'defenders';
   const image=field?.image;
   if(field){
    if(image)blit(image,0,0,FIELD_WIDTH,FIELD_HEIGHT);else{rectangle(0,0,FIELD_WIDTH,FIELD_HEIGHT,'#384a2a');for(let x=0;x<=31;x++)line(x*16,0,x*16,FIELD_HEIGHT,'#71815b');for(let y=0;y<=19;y++)line(0,y*16,FIELD_WIDTH,y*16,'#71815b');}
    // Position is extracted from the original map's class5 cell. The small
    // castle is this remake's UI marker; it is not an extracted NES overlay.
    for(const p of campSlots(field.field)){
     rectangle(p.x-7,p.y-6,14,13,INK);rectangle(p.x-5,p.y-4,10,9,PAPER);
     rectangle(p.x-6,p.y-7,3,5,PAPER);rectangle(p.x-1,p.y-8,3,6,PAPER);rectangle(p.x+4,p.y-7,3,5,PAPER);
     rectangle(p.x-1,p.y+1,3,5,INK);
    }
   }
   if(field&&!playing&&!frame&&!queue.length)paintReachable();
   if(field&&frame?.scene.kind==='move'){
    const point=movementStage(frame.scene,frame.progress);
    if(point){outline(point.x-8,point.y-8,16,16,'#ffe149');outline(point.x-7,point.y-7,14,14,INK);}
   }
   const points=positions(state),markers=markerLabels(state.units,canonicalName,person),allowed=playing||frame||queue.length?[]:tacticalView(view)?.actors?.[String(selection.actor)]?.attack_targets||[],moving=frame?.scene.kind==='move'?frame.scene.actor:null;
   const live=u=>u.troops>0&&u.health>0;
   for(const u of [...state.units].sort((a,b)=>Number(live(a))-Number(live(b)))){const p=points.get(u.id);if(p)flag(u,p,moving!==null?u.id===moving:u.id===selection.actor||u.id===selection.target,u.side!==own,allowed.some(id=>String(id)===String(u.id)),markers.get(u.id));}
   if(state.outcome){const x=field?(FIELD_WIDTH-116)/2:70,y=field?(FIELD_HEIGHT-30)/2:60;rectangle(x,y,116,30,PAPER);outline(x,y,116,30);label(outcome(state.outcome),x+10,y+10,INK,12);}
  }
  function outcome(value){const own=view?.game?.battle?.attacker===view?.game?.player;return value==='victory'?(own?text('本方勝利','勝利'):text('城池失守','都市陥落')):value==='defeat'?(own?text('本方敗退','敗北'):text('守城成功','防衛成功')):text('攻方退卻','攻撃側撤退');}
  function selectedId(state,scene){return scene?.actor??(state.duel?.actor??selection.actor??state.units[0]?.id);}
  function portrait(id,x,y){
   const personId=portraits?.personId?.(view.catalog,id),entry=portraits?.entry?.(personId);let asset=portraits?.asset?portraits.asset(personId):entry,image=imageFor(asset?.path);
   if(asset&&images.get(asset.path)?.status==='unavailable'&&portraits?.failAsset?.(personId,asset.path)){asset=portraits.asset?.(personId);image=imageFor(asset?.path);}
   rectangle(x,y,32,40,INK);if(image)blit(image,x,y,32,40);else label(person(id).slice(0,2),x+5,y+12,PAPER,12);outline(x-1,y-1,34,42);
  }
  function hud(state,scene){
   rectangle(0,160,256,80,PAPER);const id=selectedId(state,scene),unit=state.units.find(u=>u.id===id),o=view.game.officers[String(id)];if(!unit||!o)return;
   portrait(id,8,168);const p=o.profile;label(person(id),48,166,INK,10);
   const loyalty=officerChoices?.loyalty?officerChoices.loyalty(o,{isRuler:officerChoices.isRuler?.(id,view.game.extension?.leaders)===true}):o.loyalty;
   for(const [column,x]of [[[[text('兵','兵'),unit.troops],[text('體','体'),unit.health],[text('經','経'),Math.floor(o.experience/50)]],48],[[[text('武','武'),p.martial_strength],[text('德','徳'),p.virtue],[text('機動','機動'),view.game.battle.extended.tactical?.points?.[unit.side]??'—']],116],[[[text('知','知'),p.intellect],[text('忠','忠'),loyalty],[text('訓練度','練度'),view.game.battle.extended.support[String(id)]?.morale??70]],184]])column.forEach(([title,value],i)=>label(title+' '+value,x,180+i*11));
   const target=scene?.target??selection.target,foe=state.units.find(u=>u.id===target);
   if(foe)label('→ '+person(target)+'  '+text('兵','兵')+' '+foe.troops,8,216);
   const caption=scene?sceneCaption(scene):text('選擇本方部隊與對手','味方部隊と相手を選択');label(caption.slice(0,31),8,229);
  }
  function fieldHud(state,scene=null){
   rectangle(0,FIELD_HEIGHT,FIELD_WIDTH,FIELD_HUD,PAPER);line(FIELD_WIDTH/2,FIELD_HEIGHT+4,FIELD_WIDTH/2,FIELD_HEIGHT+57,INK);
   const b=view.game.battle,own=b.attacker===view.game.player?'attackers':'defenders';
   const moving=scene?.kind==='move'?state.units.find(u=>u.id===scene.actor):null;
   const actor=moving?.side===own?moving:state.units.find(u=>u.id===selection.actor&&u.side===own)||state.units.find(u=>u.side===own),target=moving&&moving.side!==own?moving:state.units.find(u=>u.id===selection.target&&u.side!==own)||state.units.find(u=>u.side!==own);
   for(const [unit,x]of [[actor,0],[target,FIELD_WIDTH/2]]){
    if(!unit)continue;const o=view.game.officers[String(unit.id)];if(!o)continue;
    portrait(unit.id,x+8,FIELD_HEIGHT+8);label(person(unit.id),x+48,FIELD_HEIGHT+6,INK,11);
    const p=o.profile,loyalty=officerChoices?.loyalty?officerChoices.loyalty(o,{isRuler:officerChoices.isRuler?.(unit.id,view.game.extension?.leaders)===true}):o.loyalty;
    const columns=[[[text('兵','兵'),unit.troops],[text('體','体'),unit.health],[text('經','経'),Math.floor(o.experience/50)]],[[text('武','武'),p.martial_strength],[text('德','徳'),p.virtue],[text('機動','機動'),b.extended.tactical?.points?.[unit.side]??'—']],[[text('知','知'),p.intellect],[text('忠','忠'),loyalty],[text('訓練度','練度'),b.extended.support[String(unit.id)]?.morale??70]]];
    columns.forEach((col,i)=>col.forEach(([key,value],j)=>label(key+' '+value,x+48+i*68,FIELD_HEIGHT+20+j*11,INK,8)));
    const position=unitPosition(view,unit.id);label((unit.troops===0?text('潰散','敗走'):unit.side===own?text('本方部隊','自軍部隊'):text('對方部隊','敵軍部隊'))+(position?' · '+(position.x+1)+','+(position.y+1):''),x+8,FIELD_HEIGHT+54,INK,9);
   }
   const destination=selection.destination,quote=tacticalView(view)?.actors?.[String(selection.actor)]?.reachable?.find(p=>cell(destination)&&p.x===destination.x&&p.y===destination.y);
   label(quote?text('移動預覽：','移動先：')+(destination.x+1)+','+(destination.y+1)+' · '+text('機動','機動')+quote.cost:text('選將後點空格預覽移動，接觸敵軍才可攻擊','武将と移動先を選択。接触した敵に攻撃できます'),8,FIELD_HEIGHT+69,INK,9);
  }
  function army(unit,side,tick,progress,active){
   if(!unit)return;const amount=Math.min(12,Math.ceil(unit.troops/85)),left=side==='left',shift=active?Math.round(Math.sin(progress*Math.PI)*10)*(left?1:-1):0;
   for(let i=0;i<amount;i++){const x=(left?20:236)+(left?1:-1)*(i%4)*22+shift,y=46+Math.floor(i/4)*38;
    const kind=left?'infantry':manifest?.sprites?.infantry_enemy?'infantry_enemy':'cavalry';
    if(!sprite(kind,x,y,tick+i,{maxWidth:22,maxHeight:30})){
     // A bounded missing-asset indicator, never a substitute claimed as ROM art.
     rectangle(x-3,y-12,6,10,left?'#7c3400':'#b01818');rectangle(x-2,y-16,4,4,INK);
    }
   }
  }
  function soldierImage(atlas){
   const image=imageFor(atlas?.path);
   return image&&(image.naturalWidth||image.width)===atlas.width&&(image.naturalHeight||image.height)===atlas.height?image:null;
  }
  function soldierSprite(type,side,pose,x,y){
   const atlas=soldiers?.types?.[type]?.[side==='left'?'friendly':'enemy'],image=soldierImage(atlas),frame=atlas?.frames?.find(f=>f.action===pose);
   if(!image||!frame)return false;
   const size=atlas.logical_width,[sx,sy,sw,sh]=frame.source_rect;
   ctx.save();ctx.imageSmoothingEnabled=false;
   if(side==='right'){ctx.translate(Math.round(x+size/2),Math.round(y-size));ctx.scale(-1,1);ctx.drawImage(image,sx,sy,sw,sh,0,0,size,size);}
   else ctx.drawImage(image,sx,sy,sw,sh,Math.round(x-size/2),Math.round(y-size),size,size);
   ctx.restore();return true;
  }
  function soldierFormation(unit,side,scene,progress,shift=0){
   if(!unit||!soldiers)return false;
   const palette=side==='left'?'friendly':'enemy';
   // Keep a whole side visually coherent if any one of its three atlases fails.
   if(Object.keys(SOLDIER_TYPES).some(type=>!soldierImage(soldiers.types[type][palette])))return false;
   const pose=soldierActionPose(scene,unit.id,progress),left=side==='left';
   const groups=[['infantry',[[40,32],[40,48],[40,64],[56,80]]],['archer',[[24,96],[56,96],[56,112],[72,128]]],['cavalry',[[56,160],[88,160]]]];
   for(const [type,points]of groups){
    // Crossbow is a known tactic effect, not a new saved archer-unit class.
    const action=scene?.effect==='crossbow'&&unit.id===scene.actor&&pose==='attack'&&type!=='archer'?'ready':pose;
    // Retain the original4 infantry /4 archers /2 rear cavalry layout.
    // Stop each approaching group before its mirrored image boxes overlap;
    // outward withdrawal keeps the complete negative displacement.
    const maximum=128-Math.max(...points.map(([x])=>x))-SOLDIER_TYPES[type]/2-4;
    const advance=Math.min(shift,maximum,type==='archer'?28:Infinity);
    for(const [x,y]of points)soldierSprite(type,side,action,(left?x:256-x)+(left?advance:-advance),y);
   }
   return true;
  }
  function attackArmy(unit,side,stage,scene,progress){
   if(!unit)return;
   if(soldierFormation(unit,side,scene,progress,stage.shift))return;
   if(unit.troops<=0)return;
   const left=side==='left',kind=left?'attack_formation':'attack_formation_enemy',row=readyFrame(kind,stage.tick);
   if(row){
    // Native128×160 half-screen formations contain the original mixed spear
    // poses. Their4× source pixels are drawn into the unchanged logical scene.
    blit(row.image,(left?0:128)+(left?stage.shift:-stage.shift),0,128,160);
    return;
   }
   army(unit,side,stage.tick,.5,stage.phase!=='result');
  }
  function effects(scene,progress,tick,targetX){
   const effect=scene.kind==='ambush'?'ambush':scene.effect;if(!scene.success||scene.skipped)return;
   const y=72,flash=progress>.35&&progress<.82;
   if(scene.kind==='attack'||effect==='strike'){
    if(flash){if(!sprite('impact',targetX,y,tick,{maxWidth:28,maxHeight:30})){line(targetX-8,y-16,targetX+8,y+2,'#fff',2);line(targetX+8,y-16,targetX-8,y+2,'#d82000',2);}}
    return;
   }
   if(['fire','inferno','supply'].includes(effect))for(let i=0;i<(effect==='inferno'?11:5);i++){
    const x=targetX-24+i%5*12,fy=38+Math.floor(i/5)*42-(tick+i)%4*3;
    if(!sprite('fire',x,fy+32,tick+i,{maxWidth:24,maxHeight:36})){rectangle(x,fy,8,30,'#e64800');rectangle(x+2,fy-5,4,30,'#ffb800');rectangle(x+3,fy+5,2,20,'#fff0a0');}
   }
   else if(['water','flood'].includes(effect))for(let yy=28;yy<150;yy+=9)for(let xx=0;xx<88;xx+=8){const x=targetX-42+xx,yw=yy+((xx/8+tick)%3)*2;rectangle(x,yw,8,5,'#1850db');rectangle(x,yw,5,1,'#b8f0ff');}
   else if(effect==='rock')for(let i=0;i<7;i++){const x=targetX-24+i%3*19,ry=-24+(progress*230+i*23)%170;rectangle(x,ry,12,10,'#883800');rectangle(x+2,ry-2,6,2,'#ffb054');}
   else if(['area','crossbow','feint'].includes(effect))for(let i=0;i<(effect==='crossbow'?7:4);i++){const x=(scene.own==='attackers'?18:238)+(targetX-(scene.own==='attackers'?18:238))*progress,ay=35+i*18;if(!sprite('arrow',x,ay,tick,{maxWidth:24,maxHeight:12,mirror:scene.own!=='attackers'})){line(x-8,ay,x+5,ay,INK);line(x+5,ay,x+2,ay-3,INK);}}
   else if(effect==='guard'){const actorX=256-targetX;outline(actorX-17,30,35,69,'#00b8c0');outline(actorX-20,27,41,75,'#ffffff');}
   else if(effect==='surrender'){rectangle(targetX-3,38,1,55,INK);rectangle(targetX-2,38,22,15,'#ffffff');}
   else if(effect==='trap'){rectangle(targetX-21,103,42,12,INK);rectangle(targetX-15,107,30,6,'#7c3400');}
   else if(effect==='ambush'){for(let i=0;i<5;i++){rectangle(targetX-35+i*16,104,14,16,'#185800');const x=targetX-28+i*16,y=110-Math.sin(progress*Math.PI)*16;if(!soldierSprite('infantry',scene.own==='attackers'?'left':'right','attack',x,y))sprite('infantry',x,y,tick+i,{maxWidth:22,maxHeight:30});}}
   else if(['chain','confuse'].includes(effect))for(let i=0;i<8;i++){const x=targetX-24+(i*11+tick*3)%54,cy=25+i%4*17;outline(x,cy,5,5,i%2?'#fff':'#0068b8');}
  }
  function paintEngagement(scene,progress){
   const stage=attackStage(progress,scene.skipped),state=(scene.kind==='attack'?stage.resolved:progress>=.55)?scene.after:scene.before;background('plain');
   const actor=state.units.find(u=>u.id===scene.actor)||state.units.find(u=>u.side===scene.own),target=state.units.find(u=>u.id===scene.target)||state.units.find(u=>u.side!==scene.own),actorLeft=scene.own==='attackers',tick=Math.floor(progress*12);
   if(scene.kind==='attack'){
    attackArmy(actor,actorLeft?'left':'right',stage,scene,progress);attackArmy(target,actorLeft?'right':'left',stage,scene,progress);
    if(stage.phase==='clash')effects(scene,progress,stage.tick,actorLeft?140:116);
   }else{
    const still={shift:scene.kind==='retreat'?-Math.round(progress*38):0,tick};
    attackArmy(actor,actorLeft?'left':'right',still,scene,progress);attackArmy(target,actorLeft?'right':'left',{...still,shift:0},scene,progress);
    effects(scene,progress,tick,actorLeft?198:58);
   }
   if(scene.kind==='attack'?stage.resolved:progress>.52){
    const losses=changes(scene).filter(c=>c.troops<0||c.health<0);
    if(losses.length>2){
     // Area tactics report every actual victim, instead of overlaying their losses.
     rectangle(2,2,252,Math.ceil(losses.length/2)*12+4,PAPER);
     losses.forEach((c,i)=>label(`${person(c.id)} ${c.troops<0?text('兵','兵')+c.troops:text('體','体')+c.health}`,6+i%2*124,5+Math.floor(i/2)*12,INK,9));
    }else for(const change of losses){const x=change.id===scene.actor?(actorLeft?35:176):(actorLeft?176:35);rectangle(x-2,7,72,14,PAPER);label(change.troops<0?`${text('損兵','損耗')} ${-change.troops}`:`${text('體','体')} ${change.health}`,x,10,INK,9);}
   }
   hud(state,scene);
  }
  function bar(id,health,x,y){
   const max=view.game.officers[String(id)]?.profile.health_max||99;rectangle(x,y,80,7,'#ffffff');rectangle(x,y,Math.round(80*health/max),7,'#9c3c00');outline(x,y,80,7);
   for(let j=4;j<80;j+=4)rectangle(x+j,y,1,7,INK);
  }
  function duelProfile(id){
   const base=duelAppearance?.profile?.(view?.catalog,id)||null;if(!base)return null;
   const key=base.person_id||String(id),choice=duelLoadouts.get(key);if(!choice)return base;
   try{return duelAppearance.profile(view?.catalog,id,choice);}catch{duelLoadouts.delete(key);return base;}
  }
  function duelParticipants(){
   const queued=queue.find(s=>s.kind.startsWith('duel')),d=view?.game?.battle?.extended?.duel||frame?.scene?.before?.duel||frame?.scene?.after?.duel||queued?.before?.duel||queued?.after?.duel;
   return d?[d.actor,d.target]:[];
  }
  function chooseDuelAppearance(id,choice){
   if(playing||queue.length||!duelParticipants().includes(id)||!choice||typeof choice!=='object'||Array.isArray(choice)||Object.keys(choice).some(k=>!['weapon','horse'].includes(k)))return false;
   const base=duelAppearance?.profile?.(view?.catalog,id);if(!base)return false;
   const current=duelProfile(id),next={weapon:choice.weapon??current.weapon,horse:choice.horse??current.horse};
   for(const field of ['weapon','horse'])if(!(base[field+'_variants']||[{key:base[field]}]).some(row=>row.key===next[field]))return false;
   duelLoadouts.set(base.person_id||String(id),next);loadoutSignature='';updateText();draw();void preloadDuelArtwork();return true;
  }
  function updateLoadoutControls(){
   const box=host?.querySelector?.('[data-duel-loadouts]');if(!box)return;
   const ids=duelParticipants(),disabled=playing||queue.length>0;box.hidden=!ids.length;
   if(!ids.length){box.innerHTML='';loadoutSignature='';return;}
   const signature=JSON.stringify([ids,locale(),disabled,ids.map(id=>{const p=duelProfile(id);return p?[p.weapon,p.horse]:null;})]);if(signature===loadoutSignature)return;
   loadoutSignature=signature;const open=box.querySelector?.('details')?.open===true;
   box.innerHTML=`<details ${open?'open':''}><summary>${text('單挑裝備與坐騎（兵器依實際裝備）','一騎討ちの装備と騎馬（武器は実装備に対応）')}</summary><div class="duel-loadout-grid">${ids.map(id=>{
    const p=duelProfile(id);if(!p)return '';
    return `<fieldset><legend>${esc(person(id))}</legend>${['weapon','horse'].map(field=>{
     const rows=p[field+'_variants']||[{key:p[field],label:p[field+'_label']}];
     return `<label>${field==='weapon'?text('兵器','武器'):text('坐騎','騎馬')}<select data-duel-person="${esc(id)}" data-duel-field="${field}" ${disabled||rows.length<2?'disabled':''}>${rows.map(row=>`<option value="${esc(row.key)}" ${row.key===p[field]?'selected':''}>${esc(equipmentLabel(row.label))}</option>`).join('')}</select></label>`;
    }).join('')}</fieldset>`;
   }).join('')}</div></details>`;
   box.onchange=event=>{const node=event.target,id=ids.find(id=>String(id)===node?.dataset?.duelPerson),field=node?.dataset?.duelField;if(id!==undefined&&['weapon','horse'].includes(field))chooseDuelAppearance(id,{[field]:node.value});};
  }
  async function preloadDuelArtwork(){
   const rows=duelParticipants().map(duelProfile).filter(Boolean);
   await Promise.all(rows.map(async profile=>{
    const atlas=enhanced?.action_atlases?.[profile.weapon]?.[profile.horse];
    if(validActionAtlas(atlas)&&await loadImage(atlas.path).promise)return;
    await Promise.all((enhanced?.duelists?.[profile.weapon]?.[profile.horse]?.frames||[]).map(f=>loadImage(f.path).promise));
   }));
  }
  function duelArtworkNeedsLoad(){
   return duelParticipants().map(duelProfile).filter(Boolean).some(profile=>{
    const atlas=enhanced?.action_atlases?.[profile.weapon]?.[profile.horse];
    if(validActionAtlas(atlas)){const status=images.get(atlas.path)?.status;if(status==='ready')return false;if(status!=='unavailable')return true;}
    return (enhanced?.duelists?.[profile.weapon]?.[profile.horse]?.frames||[]).some(f=>!['ready','unavailable'].includes(images.get(f.path)?.status));
   });
  }
  function equipmentLabel(value){return typeof value==='object'?value?.[locale()]||value?.['zh-Hant']||'':translate(value);}
  function duelEquipment(profile,x,matched){
   label(matched?equipmentLabel(profile.weapon_label):text('原版備用圖','原作予備画像'),x,50,INK,6);
   label(matched?equipmentLabel(profile.horse_label):text('通用騎將','汎用騎将'),x,57,INK,6);
  }
  function duelCenter(profile,legacy,mirror){
   const atlas=enhanced?.action_atlases?.[profile?.weapon]?.[profile?.horse];
   return validActionAtlas(atlas)&&images.get(atlas.path)?.status==='ready'?legacy+(mirror?-10:10):legacy;
  }
  function duelist(profile,x,y,pose,mirror,tick=0){
   const atlas=enhanced?.action_atlases?.[profile?.weapon]?.[profile?.horse],action=validActionAtlas(atlas)?atlas.frames.find(f=>f.action===pose):null,atlasImage=action?imageFor(atlas.path):null;
   if(atlasImage){
    const [sx,sy,sw,sh]=action.source_rect,w=atlas.logical_width,h=atlas.logical_height,dx=x-(mirror?w-atlas.anchor.x:atlas.anchor.x),dy=y-atlas.anchor.y;
    ctx.save();ctx.imageSmoothingEnabled=false;
    if(mirror){ctx.translate(Math.round(dx+w),Math.round(dy));ctx.scale(-1,1);ctx.drawImage(atlasImage,sx,sy,sw,sh,0,0,w,h);}
    else ctx.drawImage(atlasImage,sx,sy,sw,sh,Math.round(dx),Math.round(dy),w,h);
    ctx.restore();return true;
   }
   const frames=enhanced?.duelists?.[profile?.weapon]?.[profile?.horse]?.frames||[],f=frames[Math.floor(tick)%Math.max(1,frames.length)],image=imageFor(f?.path);
   if(!image)return false;
   const w=f.logical_width,h=f.logical_height,scale=Math.min(1,96/w,96/h);
   const anchor=f.anchor&&Number.isFinite(f.anchor.x)&&Number.isFinite(f.anchor.y)&&f.anchor.x>=0&&f.anchor.x<=w&&f.anchor.y>=0&&f.anchor.y<=h?f.anchor:{x:w/2,y:h};
   return blit(image,x-(mirror?w-anchor.x:anchor.x)*scale,y-anchor.y*scale,w*scale,h*scale,mirror);
  }
  function paintDuel(state,scene=null,progress=0){
   rectangle(0,0,256,64,PAPER);rectangle(0,64,256,96,INK);rectangle(0,160,256,80,PAPER);
   const d=state.duel||scene?.before.duel||scene?.after.duel||{actor:scene?.actor,target:scene?.target},a=state.units.find(u=>u.id===d.actor),t=state.units.find(u=>u.id===d.target);if(!a||!t)return;
   label(person(a.id),32,17,INK,12);label(person(t.id),144,17,INK,12);bar(a.id,a.health,32,40);bar(t.id,t.health,144,40);
   const ap=duelProfile(a.id),tp=duelProfile(t.id);
   const action=scene?.kind==='duel_action',am=action?scene.move:null,tm=action?scene.reply:null,tick=Math.floor(progress*10),ax=duelCenter(ap,54,false)+duelMotion(am,progress,ap?.weapon==='bow'),tx=duelCenter(tp,202,true)-duelMotion(tm,progress,tp?.weapon==='bow');
   const aMatched=duelist(ap,ax,160,duelActionPose(scene,a.id,progress),false,tick),tMatched=duelist(tp,tx,160,duelActionPose(scene,t.id,progress),true,tick+1);
   duelRendering.set(a.id,aMatched);duelRendering.set(t.id,tMatched);
   if(!aMatched&&!sprite('duelist',ax,160,tick,{maxWidth:96,maxHeight:96}))sprite('cavalry',ax,155,tick,{maxWidth:72,maxHeight:88});
   if(!tMatched&&!sprite('duelist_enemy',tx,160,tick+1,{maxWidth:96,maxHeight:96}))sprite('duelist',tx,160,tick+1,{mirror:true,maxWidth:96,maxHeight:96});
   duelEquipment(ap,32,aMatched);duelEquipment(tp,144,tMatched);
   if(action&&scene.success&&progress>.38&&progress<.7&&changes(scene).some(c=>c.health<0)&&[am,tm].some(m=>['strike','feint','desperate'].includes(m))){line(115,95,140,131,'#fff',2);line(139,95,115,131,'#ffb800',2);}
   if(action&&progress>=.25&&progress<=.55)for(const [p,matched,move,from,to]of [[ap,aMatched,am,ax,tx],[tp,tMatched,tm,tx,ax]])if(matched&&p?.weapon==='bow'&&['strike','desperate'].includes(move)){
    const travel=(progress-.25)/.3,x=from+(to-from)*travel,direction=to>from?1:-1;line(x-direction*8,108,x+direction*6,108,'#fff0b0');line(x+direction*6,108,x+direction*2,105,'#ffffff');line(x+direction*6,108,x+direction*2,111,'#ffffff');
   }
   label(text(`第${d.round||1}合`,`第${d.round||1}合`),108,166);
   const caption=scene?sceneCaption(scene):text('選擇招式，與對手交鋒','技を選び、相手と打ち合う');label(caption.slice(0,30),8,185,INK,9);
   label(person(a.id)+' '+text('體','体')+' '+a.health,16,206);label(person(t.id)+' '+text('體','体')+' '+t.health,144,206);
   if(scene?.kind==='duel_action')label(changes(scene).filter(c=>c.health<0).map(c=>`${person(c.id)} ${c.health}`).join(' / ').slice(0,31),16,224);
  }
  function sceneCaption(scene){
   if(scene.kind==='move'){const point=movementStage(scene,frame?.scene===scene?frame.progress:0);return `${person(scene.actor)} · ${text('移動','移動')} ${point?.index??0}/${point?.steps??0} · ${text('機動','機動力')}${scene.move.cost}`;}
   if(scene.kind==='retreat')return text('部隊退卻','部隊撤退');
   const action=scene.kind==='tactic'?translate(view?.catalog?.tactics?.[scene.tactic]?.name||text('計略','計略')):
    scene.kind==='ambush'?text('十面埋伏觸發','十面埋伏が発動'):scene.kind==='duel_start'?text('單挑挑戰','一騎討ちの挑戦'):scene.kind==='duel_action'?({strike:text('突擊','突撃'),guard:text('防守','防御'),feint:text('佯攻','牽制'),desperate:text('捨命一擊','捨て身の攻撃'),withdraw:text('退出單挑','一騎討ちから退く')}[scene.move]||text('交鋒','打ち合い')):
    scene.kind==='retreat'?text('退卻','撤退'):scene.counter?text('反擊','反撃'):text('攻擊','攻撃');
   const status=scene.skipped?text('行動跳過','行動できない'):scene.success?'':scene.kind==='duel_start'?text('拒絕挑戰','挑戦を拒否'):text('未能奏效','効果なし');
   const reply=scene.kind==='duel_action'&&scene.reply?text('對手：','相手：')+({strike:text('突擊','突撃'),guard:text('防守','防御'),feint:text('佯攻','牽制'),desperate:text('捨命一擊','捨て身の攻撃')}[scene.reply]):'';
   return `${person(scene.actor)} · ${action}${reply?' / '+reply:''}${status?' · '+status:''}`;
  }
  function description(){
   const b=view?.game?.battle;if(!b)return '';
   const armies=['attackers','defenders'].map(side=>b[side].map(u=>`${person(u.id)} ${text('兵','兵')} ${u.troops} ${text('體','体')} ${b.extended.support[String(u.id)].health} ${text('訓練度','練度')} ${b.extended.support[String(u.id)].morale??70}`).join('、')).join(' / ');
   const duel=b.extended.duel,equipment=duel?[duel.actor,duel.target].map(id=>{const p=duelProfile(id);return p&&duelRendering.get(id)?[person(id),equipmentLabel(p.weapon_label),equipmentLabel(p.horse_label)].join(' '):[person(id),text('原版備用圖','原作予備画像'),text('通用騎將','汎用騎将')].join(' ');}).filter(Boolean).join(' / '):'';
   return armies+(equipment?' / '+equipment:'');
  }
  function updateText(){
   if(!host)return;host.dataset.l10nNative=locale();host.dataset.sceneAssets=assetStatus;
   updateLoadoutControls();
   const skipButton=host.querySelector('[data-battle-skip]');if(skipButton){skipButton.hidden=!playing;skipButton.textContent=text('略過演出','演出をスキップ');}
   const title=host.querySelector('[data-battle-scene-title]');if(title)title.textContent=frame?.scene?.kind==='move'?text('部隊移動','部隊の移動'):frame?.scene?.kind==='attack'?text('部隊對陣','部隊同士の戦闘'):view?.game?.battle?.extended?.duel?text('陣前單挑','一騎討ち'):text('戰場','戦場');
   const fieldLabel=host.querySelector('[data-battlefield-label]'),field=selectedField();
   if(fieldLabel){fieldLabel.textContent=field?(locale()==='ja'?field.label_ja:field.label_tc)||field.field.id:text('參考戰場','参考戦場');fieldLabel.title=field?(locale()==='ja'?field.description_ja:field.description_tc)||'':text('地圖素材載入後顯示對應城池戰場','地図素材の読み込み後に都市の戦場を表示');}
   host.dataset.battlefieldId=field?.field?.id||'';
   host.dataset.battlefieldSource=field?.binding?.kind||field?.binding?.type||'fallback';
   const quote=tacticalView(view)?.actors?.[String(selection.actor)];host.dataset.battleReachableCount=String(quote?.reachable?.length??0);host.dataset.battleSelectedActor=String(selection.actor??'');
   host.dataset.battleDestination=cell(selection.destination)?selection.destination.x+','+selection.destination.y:'';
   const movement=frame?.scene?.kind==='move'?movementStage(frame.scene,frame.progress):null;
   host.dataset.battleMoveActor=movement?String(frame.scene.actor):'';host.dataset.battleMoveStep=movement?String(movement.index):'';
   host.dataset.battleMoveX=movement?String(movement.x):'';host.dataset.battleMoveY=movement?String(movement.y):'';
   const caption=host.querySelector('[data-battle-caption]');if(caption)caption.textContent=frame?sceneCaption(frame.scene):field&&!field.image?text('戰場圖片載入中或無法載入；格位與移動規則保持不變。','戦場画像を読み込めません。座標と移動のルールは変わりません。'):text('點選本方旗標，再點可達空格預覽移動；方向鍵調整、Enter確認。','自軍の旗と移動可能な空きマスを選択。矢印キーで調整し、Enterで移動します。');
   const hidden=host.querySelector('[data-battle-description]');if(hidden)hidden.textContent=description();
  }
  function draw(){
   if(!ctx||!view?.game?.battle||host?.isConnected===false)return;
   // Render directly into the4× backing store, retaining the original logical layout.
   // This also lets128×160 portraits and32px CJK text retain their actual detail.
   const current=snapshot(view),moving=frame?.scene?.kind==='move',field=(!frame||moving)&&!current?.duel?selectedField():null;
   const width=field?FIELD_WIDTH:WIDTH,height=field?FIELD_HEIGHT+FIELD_HUD:HEIGHT;
   if(canvas.width!==width*RESOLUTION_SCALE||canvas.height!==height*RESOLUTION_SCALE){canvas.width=width*RESOLUTION_SCALE;canvas.height=height*RESOLUTION_SCALE;fit();}
   host.dataset.battleSceneMode=moving?'movement':frame?(frame.scene.kind.startsWith('duel')?'duel':'engagement'):current?.duel?'duel':'tactical';
   duelRendering.clear();ctx.setTransform(RESOLUTION_SCALE,0,0,RESOLUTION_SCALE,0,0);ctx.imageSmoothingEnabled=false;rectangle(0,0,width,height,INK);
   if(frame){const {scene,progress}=frame,state=progress<.55?scene.before:scene.after;if(scene.kind==='move'){paintMap(state,field);if(field)fieldHud(state,scene);else hud(state,scene);}else if(scene.kind.startsWith('duel'))paintDuel(state,scene,progress);else paintEngagement(scene,progress);}
   else{if(current.duel)paintDuel(current);else{paintMap(current,field);if(field)fieldHud(current);else hud(current);}}
   updateText();
  }
  function clickMap(event){
   if(playing||options.canInteract?.()===false||!canvas||!view?.game?.battle||view.game.phase!=='battle'||view.game.battle.extended.duel)return;
   const field=selectedField(),width=field?FIELD_WIDTH:WIDTH,height=field?FIELD_HEIGHT+FIELD_HUD:HEIGHT;
   const rect=canvas.getBoundingClientRect(),x=(event.clientX-rect.left)*width/rect.width,y=(event.clientY-rect.top)*height/rect.height;if(y>=(field?FIELD_HEIGHT:160))return;
   if(x<0||y<0||x>=width)return;
   const selected={x:Math.floor(x/16),y:Math.floor(y/16)};if(!cell(selected))return;
   const state=snapshot(view),own=view.game.battle.attacker===view.game.player?'attackers':'defenders',found=state.units.find(unit=>{const p=unitPosition(view,unit.id);return unit.troops>0&&unit.health>0&&p?.x===selected.x&&p?.y===selected.y;});
   if(found)options.onSelect?.(found.side===own?'actor':'target',found.id);else options.onCell?.(selected);
  }
  function mapKeydown(event){
   if(event.defaultPrevented||event.isComposing||event.ctrlKey||event.metaKey||event.altKey||playing||options.canInteract?.()===false||view?.game?.phase!=='battle'||view.game.battle?.extended?.duel||!tacticalView(view)?.actors?.[String(selection.actor)]?.can_act)return;
   const direction={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowLeft:[-1,0],ArrowRight:[1,0]}[event.key];
   if(direction){event.preventDefault();options.onNavigate?.(...direction);}
   else if(event.key==='Enter'){event.preventDefault();options.onConfirmMove?.();}
   else if(event.key==='Escape'){event.preventDefault();options.onCancelMove?.();}
  }
  function finish(playOutcome=true){if(handle!==null)caf?.(handle);handle=null;const wasPlaying=playing;playing=false;frame=null;queue=[];animationPositions=null;updateText();draw();if(wasPlaying)options.onSettled?.();if(playOutcome&&outcomeCue)options.onOutcome?.(outcomeCue);outcomeCue=null;const resolve=resolvePlay;resolvePlay=null;resolve?.();}
  function skip(){finish();}
  async function play(){
   if(disposed){finish(false);return;}
   if(!queue.length||!ctx){finish();return;}
   if(reduced()||doc?.hidden||!raf){if(!doc?.hidden){options.onSound?.(queue[0]);options.onSettled?.();}finish();return;}
   // A fast first attack must not finish before its original artwork arrives.
   if(queue.some(scene=>scene.kind!=='move')&&(assetStatus==='idle'||assetStatus==='loading')){await load();if(disposed||!queue.length||!ctx||host?.isConnected===false){finish(false);return;}}
   if(queue.some(scene=>scene.kind.startsWith('duel'))&&duelArtworkNeedsLoad()){await preloadDuelArtwork();if(disposed||!queue.length||!ctx||host?.isConnected===false){finish(false);return;}}
   if(queue.some(scene=>scene.kind!=='move'&&!scene.kind.startsWith('duel'))&&soldierArtworkNeedsLoad()){await preloadSoldierArtwork();if(disposed||!queue.length||!ctx||host?.isConnected===false){finish(false);return;}}
   // Loading may span a visibility or accessibility change. Do not start a
   // background RAF that can leave the already committed command waiting.
   if(reduced()||doc?.hidden||!raf){if(!doc?.hidden){options.onSound?.(queue[0]);options.onSettled?.();}finish();return;}
   host?.querySelector?.('[data-battle-canvas]')?.scrollIntoView?.({block:'nearest',behavior:'instant'});
   const scenes=queue.splice(0),timeScale=Math.min(1,16000/scenes.reduce((sum,scene)=>sum+duration(scene),0));playing=true;updateText();
   await new Promise(resolve=>{resolvePlay=resolve;let index=0,start=null,began=null;const tick=now=>{
    if(disposed||!playing||host?.isConnected===false||doc?.hidden){finish();return;}
    if(began===null)began=now;
    // A complete AI turn can contain many already committed moves and
    // exchanges. Keep the visible replay finite without changing its result.
    if(now-began>=16000){finish();return;}
    if(start===null){start=now;options.onSound?.(scenes[index]);}
    const scene=scenes[index],progress=Math.min(1,(now-start)/(duration(scene)*timeScale));frame={scene,progress};draw();
    if(progress>=1){if(scene.kind==='move')animationPositions?.set(String(scene.actor),{...scene.move.path.at(-1)});index++;start=null;if(index>=scenes.length){finish();return;}}
    handle=raf(tick);
   };frame={scene:scenes[0],progress:0};draw();handle=raf(tick);});
  }
  function reset(){finish(false);duelRendering.clear();duelLoadouts.clear();loadoutSignature='';observed=null;key='';view=null;selection={};resizeObserver?.disconnect();host=canvas=ctx=null;}
  function leave(){if(host||playing||queue.length)reset();}
  function changeLanguage(){updateText();draw();}
  function visibility(){if(doc?.hidden&&playing)skip();}
  function keydown(event){if(playing&&event.key==='Escape'){event.preventDefault();skip();}}
  doc?.addEventListener?.('game-language-change',changeLanguage);doc?.addEventListener?.('visibilitychange',visibility);doc?.addEventListener?.('keydown',keydown);
  function dispose(){disposed=true;reset();doc?.removeEventListener?.('game-language-change',changeLanguage);doc?.removeEventListener?.('visibilitychange',visibility);doc?.removeEventListener?.('keydown',keydown);}
  return {html,mount,observe,play,skip,reset,leave,load,dispose,chooseDuelAppearance,deferOutcome:cue=>{outcomeCue=cue;},get playing(){return playing;},state:()=>({playing,queued:queue.length,assetStatus,battleId:view?.game?.battle?.id??null,scene:frame?.scene?.kind??null})};
 }
 const api={WIDTH,HEIGHT,RESOLUTION_SCALE,create,tacticalView,unitPosition,receiptScenes,validSnapshot,validMovement,movementStage,snapshot,changes,duration,validAssetPath,validEnhancedAssetPath,validActionAtlas,validSoldierAtlas,validSoldierLibrary,SOLDIER_ACTIONS,soldierActionPose,DUEL_ACTIONS,duelActionPose,duelMotion,familyName,markerLabels,attackStage};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameBattleScene=api;
})(typeof window==='object'?window:globalThis);
