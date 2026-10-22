/* NES-style4× rendering with native assets and separately documented new duel art.
 * The server receipts describe already committed actions. Rendering, skipping,
 * resizing and changing language never submit commands or sample game RNG. */
'use strict';
(function(root){
 const WIDTH=256,HEIGHT=240,RESOLUTION_SCALE=4,SCHEMA='tk2-battle-presentation-v1';
 const PAPER='#ffd4c8',INK='#000000',ASSET_ROOT='/assets/battle-original/',ENHANCED_ROOT='/assets/battle-enhanced/';
 const EFFECTS=new Set(['fire','trap','strike','water','confuse','supply','feint','rock','area','chain','crossbow','surrender','ambush','flood','inferno','guard']);
 const KINDS=new Set(['attack','tactic','ambush','duel_start','duel_action','retreat']);
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const reference=id=>Number.isInteger(id)&&id>=0&&id<1200||typeof id==='string'&&/^clerk-[0-9]{6,12}$/.test(id)&&Number(id.slice(6))>=1&&Number(id.slice(6))<=1000000&&id==='clerk-'+String(Number(id.slice(6))).padStart(6,'0');
 const bounded=(n,max)=>Number.isInteger(n)&&n>=0&&n<=max;
 const clone=value=>JSON.parse(JSON.stringify(value));
 // Group on canonical names, before locale translation; simplified/traditional
 // spellings of a surname identify the same family on either side of battle.
 const COMPOUND_SURNAMES=new Set(['公孫','司馬','諸葛','夏侯','皇甫','太史','上官','歐陽','令狐','尉遲','呼延','宇文','慕容','毌丘','鮮于','閭丘','東方','南宮','軒轅','鍾離','澹臺','申屠','仲長','第五','段干','長孫','拓跋','濮陽','羊舌','百里','淳于']);
 const SURNAME_EQUIVALENTS={'孙':'孫','马':'馬','诸':'諸','欧':'歐','迟':'遲','鲜':'鮮','闾':'閭','东':'東','宫':'宮','轩':'軒','辕':'轅','钟':'鍾','离':'離','台':'臺','长':'長','阳':'陽','刘':'劉','张':'張','陈':'陳','许':'許','郑':'鄭','卫':'衛','黄':'黃','赵':'趙','邓':'鄧','庞':'龐','陆':'陸','吕':'呂','吴':'吳','严':'嚴','华':'華','韩':'韓','贾':'賈','顾':'顧','阎':'閻','韦':'韋','费':'費','乐':'樂','满':'滿','鲁':'魯','骆':'駱','钱':'錢','乔':'喬','蒋':'蔣','冯':'馮','谯':'譙','步':'歩','郤':'郄'};
 function familyName(name){
  const chars=Array.from(String(name??'').trim().normalize('NFKC')).map(c=>SURNAME_EQUIVALENTS[c]||c),compound=chars.slice(0,2).join('');
  return COMPOUND_SURNAMES.has(compound)?compound:chars[0]||'';
 }
 function markerLabels(units,nameFor,displayName=nameFor){
  const families=new Map(),names=new Map();
  for(const unit of units){const family=familyName(nameFor(unit.id));names.set(unit.id,family);if(family)families.set(family,(families.get(family)||0)+1);}
  return new Map(units.map(unit=>{const chars=Array.from(String(displayName(unit.id)??'').trim());return [unit.id,(families.get(names.get(unit.id))>1?chars.at(-1):chars[0])||''];}));
 }
 function attackStage(progress,skipped=false){
  const p=Math.max(0,Math.min(1,progress)),tick=Math.floor(p*20);
  if(skipped)return {phase:'result',shift:0,tick:0,resolved:true};
  if(p<.3)return {phase:'approach',shift:Math.round(p/.3*40),tick,resolved:false};
  if(p<.66)return {phase:'clash',shift:40+(tick%2?1:-1),tick,resolved:p>=.55};
  if(p<.88)return {phase:'recoil',shift:Math.round((.88-p)/.22*40),tick,resolved:true};
  return {phase:'result',shift:0,tick,resolved:true};
 }
 function validSnapshot(s){
  if(!s||Object.keys(s).sort().join(',')!=='duel,outcome,round,units'||!bounded(s.round,1000000)||s.round<1||![null,'victory','defeat','retreat'].includes(s.outcome)||!Array.isArray(s.units)||s.units.length>20)return false;
  const seen=new Set();
  for(const u of s.units){if(!u||Array.isArray(u)||Object.keys(u).sort().join(',')!=='energy,guard,health,id,side,stunned,troops'||!reference(u.id)||seen.has(String(u.id))||!['attackers','defenders'].includes(u.side)||!bounded(u.troops,999)||!bounded(u.health,99)||!bounded(u.energy,18)||!bounded(u.guard,2)||!bounded(u.stunned,1))return false;seen.add(String(u.id));}
  if(s.duel===null)return true;
  if(!s.duel||Object.keys(s.duel).sort().join(',')!=='actor,round,target'||!reference(s.duel.actor)||!reference(s.duel.target)||!bounded(s.duel.round,21)||s.duel.round<1)return false;
  const a=s.units.find(u=>u.id===s.duel.actor),t=s.units.find(u=>u.id===s.duel.target);return !!a&&!!t&&a.side!==t.side;
 }
 function receiptScenes(receipt,battleId,revision){
  if(!receipt||Object.keys(receipt).sort().join(',')!=='revision,scenes,schema'||receipt.schema!==SCHEMA||receipt.revision!==revision||!Array.isArray(receipt.scenes)||receipt.scenes.length>24)return [];
  if(!receipt.scenes.every(s=>{
   if(!s||Object.keys(s).sort().join(',')!=='actor,after,battle_id,before,counter,effect,kind,move,own,reply,skipped,success,tactic,target'||!KINDS.has(s.kind)||s.battle_id!==battleId||!['attackers','defenders'].includes(s.own)||typeof s.counter!=='boolean'||typeof s.success!=='boolean'||typeof s.skipped!=='boolean'||!validSnapshot(s.before)||!validSnapshot(s.after))return false;
   if(s.before.units.length!==s.after.units.length||s.before.units.some(u=>!s.after.units.some(v=>v.id===u.id&&v.side===u.side)))return false;
   if(s.kind==='retreat'){if(s.actor!==null||s.target!==null)return false;}
   else{const a=s.before.units.find(u=>u.id===s.actor),t=s.before.units.find(u=>u.id===s.target);if(!reference(s.actor)||!reference(s.target)||!a||!t||a.side!==s.own||t.side===s.own)return false;}
   if(['tactic','ambush'].includes(s.kind)){if(!bounded(s.tactic,15)||!EFFECTS.has(s.effect))return false;}else if(s.tactic!==null||s.effect!==null)return false;
   if(s.kind==='duel_action'){if(!['strike','guard','feint','withdraw'].includes(s.move)||(s.move==='withdraw'?s.reply!==null:!['strike','guard','feint'].includes(s.reply)))return false;}
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
 function duration(scene){return scene.kind==='attack'&&!scene.skipped?2200:scene.kind==='duel_action'?1000:scene.kind==='tactic'?1000:scene.kind==='duel_start'?700:scene.kind==='ambush'?850:700;}
 function validAssetPath(path){return typeof path==='string'&&/^\/assets\/battle-original\/[a-zA-Z0-9_/-]+\.png$/.test(path);}
 function validEnhancedAssetPath(path){return typeof path==='string'&&/^\/assets\/battle-enhanced\/[a-z0-9_-]+\.png$/.test(path);}
 function create(options={}){
  const doc=options.document||root.document,i18n=options.i18n||root.GameI18n,portraits=options.portraits||root.GamePortraits,officerChoices=options.officerChoices||root.GameOfficerChoices,duelAppearance=options.duelAppearance||root.GameDuelAppearance;
  const fetcher=options.fetch||root.fetch?.bind(root),ImageType=options.Image||root.Image;
  const raf=options.requestAnimationFrame||root.requestAnimationFrame?.bind(root),caf=options.cancelAnimationFrame||root.cancelAnimationFrame?.bind(root);
  const images=new Map(),terrainSlots=new Map(),duelRendering=new Map();let manifest=null,enhanced=null,assetStatus='idle',assetsPromise=null;
  let host=null,canvas=null,ctx=null,view=null,selection={},queue=[],key='',observed=null,playing=false,frame=null,handle=null,resolvePlay=null,resizeObserver=null,disposed=false,outcomeCue=null;
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
    image.onload=()=>finish(true);image.onerror=()=>finish(false);timeout=setTimeout(()=>finish(false),6000);image.src=path;
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
      const frames=[...Object.values(data.backgrounds),...Object.values(data.sprites).flatMap(r=>r?.frames||[]),...Object.values(data.duelists).flatMap(horses=>Object.values(horses||{}).flatMap(r=>r?.frames||[]))];
      if(!frames.length||frames.length>512||!frames.every(f=>f&&validEnhancedAssetPath(f.path)&&Number.isInteger(f.logical_width)&&Number.isInteger(f.logical_height)&&f.logical_width>0&&f.logical_width<=1024&&f.logical_height>0&&f.logical_height<=1024&&f.width===f.logical_width*RESOLUTION_SCALE&&f.height===f.logical_height*RESOLUTION_SCALE))return null;
      return frames.map(f=>f.path);
     }),
     Promise.resolve().then(()=>duelAppearance?.load?.()).catch(()=>null)
    ]);
    manifest=native?.data||null;enhanced=hd?.data||null;
    const paths=[...(native?.paths||[]),...(hd?.paths||[])];
    assetStatus=paths.some(path=>images.get(path)?.status==='ready')?'ready':'unavailable';
    updateText();draw();return assetStatus==='ready';
   })();return assetsPromise;
  }
  function html(){
   const lang=locale();
   return `<div class="nes-battle" data-battle-scene data-l10n-native="${lang}"><div class="nes-battle-toolbar"><span data-battle-scene-title>${text('戰場','戦場')}</span><button type="button" data-battle-skip hidden>${text('略過演出','演出をスキップ')}</button></div><div class="nes-battle-viewport"><canvas width="1024" height="960" data-battle-canvas role="img" aria-label="${text('原版像素戰場，請使用部隊按鈕選將','原作ドットの戦場。部隊ボタンで武将を選択できます')}"></canvas></div><p class="nes-battle-status" data-battle-caption aria-live="polite"></p><p class="visually-hidden" data-battle-description></p></div>`;
  }
  function fit(){
   const box=host?.querySelector?.('.nes-battle-viewport');if(!box||!canvas)return;
   const width=box.clientWidth||256,height=box.clientHeight||240;
   let scale=Math.min(width/WIDTH,height/HEIGHT);if(scale>=2)scale=Math.floor(scale);
   canvas.style.width=Math.max(1,Math.floor(WIDTH*scale))+'px';canvas.style.height=Math.max(1,Math.floor(HEIGHT*scale))+'px';
  }
  function mount(element,current,selected={}){
   resizeObserver?.disconnect();host=element;view=current;selection=selected;
   canvas=host?.querySelector?.('[data-battle-canvas]');ctx=null;
   if(canvas){canvas.width=WIDTH*RESOLUTION_SCALE;canvas.height=HEIGHT*RESOLUTION_SCALE;try{ctx=canvas.getContext('2d',{alpha:false});}catch{}canvas.onclick=clickMap;}
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
   queue=receiptScenes(after.presentation,battle.id,after.revision);
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
  function plainSlots(image,side){
   const cache=(image?.src||'fallback')+':'+side;if(terrainSlots.has(cache))return terrainSlots.get(cache);
   let pixels=null;
   if(image&&doc?.createElement){try{const sample=doc.createElement('canvas');sample.width=256;sample.height=160;const c=sample.getContext('2d');c.imageSmoothingEnabled=false;c.drawImage(image,0,0,256,160);pixels=c.getImageData(0,0,256,160).data;}catch{}}
   const candidates=[];
   for(let gy=0;gy<10;gy++)for(let gx=0;gx<16;gx++){
    if(side==='attackers'?gx>6:gx<9)continue;
    let obstacles=0;
    if(pixels)for(let y=gy*16;y<gy*16+16;y+=2)for(let x=gx*16;x<gx*16+16;x+=2){const i=(y*256+x)*4,r=pixels[i],g=pixels[i+1],b=pixels[i+2];if(b>r*1.4&&b>g*1.2||r+g+b<110)obstacles++;}
    candidates.push({x:gx*16+8,y:gy*16+8,obstacles,distance:Math.abs(gx-(side==='attackers'?2:13))+Math.abs(gy-4)*.7});
   }
   candidates.sort((a,b)=>a.obstacles-b.obstacles||a.distance-b.distance||a.y-b.y||a.x-b.x);
   const result=candidates.slice(0,10).sort((a,b)=>a.y-b.y||a.x-b.x);terrainSlots.set(cache,result);return result;
  }
  function positions(state,image){
   const out=new Map();for(const side of ['attackers','defenders']){const points=plainSlots(image,side);state.units.filter(u=>u.side===side).forEach((u,i)=>out.set(u.id,points[i]));}return out;
  }
  function flag(u,p,selected,enemy,used,marker){
   const color=u.troops===0?'#888888':enemy?'#b61c16':'#ffffff';rectangle(p.x-6,p.y-6,12,12,INK);rectangle(p.x-5,p.y-5,10,10,color);
   label(marker,p.x-4,p.y-4,enemy?'#ffffff':INK,8);
   if(u.troops===0){line(p.x-6,p.y-6,p.x+5,p.y+5,'#ffffff');line(p.x+5,p.y-6,p.x-6,p.y+5,'#ffffff');}
   if(used&&u.troops>0)rectangle(p.x+3,p.y+3,3,3,'#505050');
   if(selected){outline(p.x-8,p.y-8,16,16,'#ffffff');outline(p.x-7,p.y-7,14,14,INK);}
  }
  function paintMap(state){
   const b=view.game.battle,own=b.attacker===view.game.player?'attackers':'defenders';
   const image=background('tactical'),points=positions(state,image),markers=markerLabels(state.units,canonicalName,person);
   for(const u of state.units){const p=points.get(u.id);if(p)flag(u,p,u.id===selection.actor||u.id===selection.target,u.side!==own,b.used.includes(u.id),markers.get(u.id));}
   if(state.outcome){rectangle(70,60,116,30,PAPER);outline(70,60,116,30);label(outcome(state.outcome),80,70,INK,12);}
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
   for(const [column,x]of [[[[text('兵','兵'),unit.troops],[text('體','体'),unit.health],[text('經','経'),Math.floor(o.experience/50)]],48],[[[text('武','武'),p.martial_strength],[text('德','徳'),p.virtue],[text('氣','気'),unit.energy]],116],[[[text('知','知'),p.intellect],[text('忠','忠'),loyalty],[text('訓練度','練度'),view.game.battle.extended.support[String(id)]?.morale??70]],184]])column.forEach(([title,value],i)=>label(title+' '+value,x,180+i*11));
   const target=scene?.target??selection.target,foe=state.units.find(u=>u.id===target);
   if(foe)label('→ '+person(target)+'  '+text('兵','兵')+' '+foe.troops,8,216);
   const caption=scene?sceneCaption(scene):text('選擇本方部隊與對手','味方部隊と相手を選択');label(caption.slice(0,31),8,229);
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
  function attackArmy(unit,side,stage){
   if(!unit||unit.troops<=0)return;
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
   else if(effect==='ambush'){for(let i=0;i<5;i++){rectangle(targetX-35+i*16,104,14,16,'#185800');sprite('infantry',targetX-28+i*16,110-Math.sin(progress*Math.PI)*16,tick+i,{maxWidth:22,maxHeight:30});}}
   else if(['chain','confuse'].includes(effect))for(let i=0;i<8;i++){const x=targetX-24+(i*11+tick*3)%54,cy=25+i%4*17;outline(x,cy,5,5,i%2?'#fff':'#0068b8');}
  }
  function paintEngagement(scene,progress){
   const stage=attackStage(progress,scene.skipped),state=(scene.kind==='attack'?stage.resolved:progress>=.55)?scene.after:scene.before;background('plain');
   const actor=state.units.find(u=>u.id===scene.actor)||state.units.find(u=>u.side===scene.own),target=state.units.find(u=>u.id===scene.target)||state.units.find(u=>u.side!==scene.own),actorLeft=scene.own==='attackers',tick=Math.floor(progress*12);
   if(scene.kind==='attack'){
    attackArmy(actor,actorLeft?'left':'right',stage);attackArmy(target,actorLeft?'right':'left',stage);
    if(stage.phase==='clash')effects(scene,progress,stage.tick,actorLeft?140:116);
   }else{
    army(actor,actorLeft?'left':'right',tick,progress,!scene.skipped);army(target,actorLeft?'right':'left',tick+1,0,false);
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
  function duelProfile(id){return duelAppearance?.profile?.(view?.catalog,id)||null;}
  function equipmentLabel(value){return typeof value==='object'?value?.[locale()]||value?.['zh-Hant']||'':translate(value);}
  function duelEquipment(profile,x,matched){
   label(matched?equipmentLabel(profile.weapon_label):text('原版備用圖','原作予備画像'),x,50,INK,6);
   label(matched?equipmentLabel(profile.horse_label):text('通用騎將','汎用騎将'),x,57,INK,6);
  }
  function duelist(profile,x,y,tick,mirror){
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
   const action=scene?.kind==='duel_action'&&scene.move!=='withdraw',approach=action?Math.round(Math.sin(progress*Math.PI)*26):0,tick=Math.floor(progress*10);
   const aMatched=duelist(ap,54+approach,160,tick,false),tMatched=duelist(tp,202-approach,160,tick+1,true);
   duelRendering.set(a.id,aMatched);duelRendering.set(t.id,tMatched);
   if(!aMatched&&!sprite('duelist',54+approach,160,tick,{maxWidth:96,maxHeight:96}))sprite('cavalry',54+approach,155,tick,{maxWidth:72,maxHeight:88});
   if(!tMatched&&!sprite('duelist_enemy',202-approach,160,tick+1,{maxWidth:96,maxHeight:96}))sprite('duelist',202-approach,160,tick+1,{mirror:true,maxWidth:96,maxHeight:96});
   duelEquipment(ap,32,aMatched);duelEquipment(tp,144,tMatched);
   if(action&&progress>.38&&progress<.7){line(115,95,140,131,'#fff',2);line(139,95,115,131,'#ffb800',2);}
   label(text(`第${d.round||1}合`,`第${d.round||1}合`),108,166);
   const caption=scene?sceneCaption(scene):text('選擇招式，與對手交鋒','技を選び、相手と打ち合う');label(caption.slice(0,30),8,185,INK,9);
   label(person(a.id)+' '+text('體','体')+' '+a.health,16,206);label(person(t.id)+' '+text('體','体')+' '+t.health,144,206);
   if(scene?.kind==='duel_action')label(changes(scene).filter(c=>c.health<0).map(c=>`${person(c.id)} ${c.health}`).join(' / ').slice(0,31),16,224);
  }
  function sceneCaption(scene){
   if(scene.kind==='retreat')return text('部隊退卻','部隊撤退');
   const action=scene.kind==='tactic'?translate(view?.catalog?.tactics?.[scene.tactic]?.name||text('計略','計略')):
    scene.kind==='ambush'?text('十面埋伏觸發','十面埋伏が発動'):scene.kind==='duel_start'?text('單挑挑戰','一騎討ちの挑戦'):scene.kind==='duel_action'?({strike:text('突擊','突撃'),guard:text('防守','防御'),feint:text('佯攻','牽制'),withdraw:text('退出單挑','一騎討ちから退く')}[scene.move]||text('交鋒','打ち合い')):
    scene.kind==='retreat'?text('退卻','撤退'):scene.counter?text('反擊','反撃'):text('攻擊','攻撃');
   const status=scene.skipped?text('行動跳過','行動できない'):scene.success?'':scene.kind==='duel_start'?text('拒絕挑戰','挑戦を拒否'):text('未能奏效','効果なし');
   const reply=scene.kind==='duel_action'&&scene.reply?text('對手：','相手：')+({strike:text('突擊','突撃'),guard:text('防守','防御'),feint:text('佯攻','牽制')}[scene.reply]):'';
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
   const skipButton=host.querySelector('[data-battle-skip]');if(skipButton){skipButton.hidden=!playing;skipButton.textContent=text('略過演出','演出をスキップ');}
   const title=host.querySelector('[data-battle-scene-title]');if(title)title.textContent=frame?.scene?.kind==='attack'?text('部隊對陣','部隊同士の戦闘'):view?.game?.battle?.extended?.duel?text('陣前單挑','一騎討ち'):text('戰場','戦場');
   const caption=host.querySelector('[data-battle-caption]');if(caption)caption.textContent=frame?sceneCaption(frame.scene):assetStatus==='unavailable'?text('原版素材載入失敗，仍可使用部隊名單操作。','原作素材を読み込めません。部隊一覧から操作できます。'):text('點選戰場旗標或部隊名單選將；兵數以實際結算為準。','戦場の旗か部隊一覧から選択できます。兵数は実際の精算結果です。');
   const hidden=host.querySelector('[data-battle-description]');if(hidden)hidden.textContent=description();
  }
  function draw(){
   if(!ctx||!view?.game?.battle||host?.isConnected===false)return;
   // Render directly into the4× backing store, retaining the original logical layout.
   // This also lets128×160 portraits and32px CJK text retain their actual detail.
   duelRendering.clear();ctx.setTransform(RESOLUTION_SCALE,0,0,RESOLUTION_SCALE,0,0);ctx.imageSmoothingEnabled=false;rectangle(0,0,WIDTH,HEIGHT,INK);
   if(frame){const {scene,progress}=frame,state=progress<.55?scene.before:scene.after;if(scene.kind.startsWith('duel'))paintDuel(state,scene,progress);else paintEngagement(scene,progress);}
   else{const state=snapshot(view);if(state.duel)paintDuel(state);else{paintMap(state);hud(state);}}
   updateText();
  }
  function clickMap(event){
   if(playing||!canvas||!view?.game?.battle||view.game.phase!=='battle'||view.game.battle.extended.duel)return;
   const rect=canvas.getBoundingClientRect(),x=(event.clientX-rect.left)*256/rect.width,y=(event.clientY-rect.top)*240/rect.height;if(y>=160)return;
   const state=snapshot(view),image=backgroundImage('tactical'),points=positions(state,image),own=view.game.battle.attacker===view.game.player?'attackers':'defenders';
   const found=state.units.map(u=>({u,p:points.get(u.id)})).filter(r=>r.p&&Math.abs(r.p.x-x)<=9&&Math.abs(r.p.y-y)<=9).sort((a,b)=>Math.hypot(a.p.x-x,a.p.y-y)-Math.hypot(b.p.x-x,b.p.y-y))[0];
   if(!found||found.u.troops<=0||found.u.side===own&&view.game.battle.used.includes(found.u.id))return;
   options.onSelect?.(found.u.side===own?'actor':'target',found.u.id);
  }
  function finish(playOutcome=true){if(handle!==null)caf?.(handle);handle=null;const wasPlaying=playing;playing=false;frame=null;queue=[];updateText();draw();if(wasPlaying)options.onSettled?.();if(playOutcome&&outcomeCue)options.onOutcome?.(outcomeCue);outcomeCue=null;const resolve=resolvePlay;resolvePlay=null;resolve?.();}
  function skip(){finish();}
  async function play(){
   if(disposed){finish(false);return;}
   if(!queue.length||!ctx){finish();return;}
   if(reduced()||doc?.hidden||!raf){if(!doc?.hidden){options.onSound?.(queue[0]);options.onSettled?.();}finish();return;}
   // A fast first attack must not finish before its original artwork arrives.
   if(assetStatus==='idle'||assetStatus==='loading'){await load();if(disposed||!queue.length||!ctx||host?.isConnected===false){finish(false);return;}}
   // Loading may span a visibility or accessibility change. Do not start a
   // background RAF that can leave the already committed command waiting.
   if(reduced()||doc?.hidden||!raf){if(!doc?.hidden){options.onSound?.(queue[0]);options.onSettled?.();}finish();return;}
   host?.querySelector?.('[data-battle-canvas]')?.scrollIntoView?.({block:'nearest',behavior:'instant'});
   const scenes=queue.splice(0);playing=true;updateText();
   await new Promise(resolve=>{resolvePlay=resolve;let index=0,start=null;const tick=now=>{
    if(disposed||!playing||host?.isConnected===false||doc?.hidden){finish();return;}
    if(start===null){start=now;options.onSound?.(scenes[index]);}
    const scene=scenes[index],progress=Math.min(1,(now-start)/duration(scene));frame={scene,progress};draw();
    if(progress>=1){index++;start=null;if(index>=scenes.length){finish();return;}}
    handle=raf(tick);
   };frame={scene:scenes[0],progress:0};draw();handle=raf(tick);});
  }
  function reset(){finish(false);duelRendering.clear();observed=null;key='';view=null;selection={};resizeObserver?.disconnect();host=canvas=ctx=null;}
  function leave(){if(host||playing||queue.length)reset();}
  function changeLanguage(){updateText();draw();}
  function visibility(){if(doc?.hidden&&playing)skip();}
  function keydown(event){if(playing&&event.key==='Escape'){event.preventDefault();skip();}}
  doc?.addEventListener?.('game-language-change',changeLanguage);doc?.addEventListener?.('visibilitychange',visibility);doc?.addEventListener?.('keydown',keydown);
  function dispose(){disposed=true;reset();doc?.removeEventListener?.('game-language-change',changeLanguage);doc?.removeEventListener?.('visibilitychange',visibility);doc?.removeEventListener?.('keydown',keydown);}
  return {html,mount,observe,play,skip,reset,leave,load,dispose,deferOutcome:cue=>{outcomeCue=cue;},get playing(){return playing;},state:()=>({playing,queued:queue.length,assetStatus,battleId:view?.game?.battle?.id??null,scene:frame?.scene?.kind??null})};
 }
 const api={WIDTH,HEIGHT,RESOLUTION_SCALE,create,receiptScenes,validSnapshot,snapshot,changes,duration,validAssetPath,validEnhancedAssetPath,familyName,markerLabels,attackStage};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameBattleScene=api;
})(typeof window==='object'?window:globalThis);
