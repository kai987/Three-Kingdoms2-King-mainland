/* Current shipped Worker acceptance using visibly imported controlled saves.
 * The fixtures disclose their arranged positions/seed and pass the production
 * loader. All gameplay mutations below use visible UI controls, never injected
 * campaign state or a replacement damage/RNG implementation.
 */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {execFileSync} from 'node:child_process';
import {writeFile} from 'node:fs/promises';

const fixtures=new Map(),pageErrors=new WeakMap();
function fixture(kind){
 if(!fixtures.has(kind))fixtures.set(kind,JSON.parse(execFileSync(process.env.PYTHON||'python3',[
  '-B',new URL('./browser_soldier_fixture.py',import.meta.url).pathname,kind,
 ],{encoding:'utf8',maxBuffer:12*1024*1024,timeout:90_000})));
 return fixtures.get(kind);
}
test.beforeEach(async({page})=>{
 const errors=[];pageErrors.set(page,errors);
 page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
});
async function opening(page){
 await page.goto('./');await expect(page).toHaveTitle(/三國|三国/);
 await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
 await page.locator('#game-loading-start').click();await expect(page.locator('#game-loading-cover')).toBeHidden();
 await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
}
async function idle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
async function save(page){return page.evaluate(async()=>{const r=await fetch('/api/save');if(!r.ok)throw Error('Actual soldier save could not be inspected');return r.json();});}
async function read(page,withView=true){if(!withView)return {save:await save(page)};return page.evaluate(async()=>{
 const [a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);
 if(!a.ok||!b.ok)throw Error('Actual soldier state could not be inspected');
 const state=await b.json();return {save:await a.json(),view:state.view||state};
});}
async function load(page,value,name='controlled-soldier-boundary.json'){
 await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
 await idle(page);await expect(page.locator('#dialog')).toBeHidden();expect(await save(page)).toEqual(value);
}
async function dismissEvents(page){
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const events=page.locator('#event-dialog');
 for(let i=0;i<20&&await events.isVisible();i++){
  const skip=events.locator('[data-event-skip]');await(await skip.count()?skip:events.locator('[data-event-next]')).click();
 }
 await expect(events).toBeHidden();
}
async function control(page,id){
 const button=page.locator('#'+id),toggle=page.locator('#inspector-toggle');
 if(!await button.isVisible()&&await toggle.isVisible())await toggle.click();
 await expect(button).toBeEnabled();await button.click();
}
async function locale(page,value){
 const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
 await page.locator('#language').selectOption(value);await menu.locator('summary').click();
}
async function cell(page,point,touch){
 const canvas=page.locator('[data-battle-canvas]');await canvas.scrollIntoViewIfNeeded();
 const box=await canvas.boundingBox();expect(box).toBeTruthy();
 const position={x:(point.x*16+8)*box.width/496,y:(point.y*16+8)*box.height/384};
 if(touch)await canvas.tap({position});else await canvas.click({position});
}
async function animation(page,{withView=true}={}){
 await expect.poll(()=>page.evaluate(()=>!document.body.classList.contains('busy')||!!document.querySelector('[data-battle-skip]:not([hidden])')),{timeout:90_000}).toBe(true);
 const committed=await save(page),skip=page.locator('[data-battle-skip]');
 if(await skip.isVisible()){
  try{await skip.click({timeout:1000});}catch(error){if(await skip.isVisible())throw error;}
 }
 await idle(page);await dismissEvents(page);
 expect(await save(page)).toEqual(committed,'Animation completion or Skip cannot resolve another hit or draw extra random numbers');
 return read(page,withView);
}
async function waitSoldierReplay(page){
 // Poll on Node's real time while stepping only the presentation clock: two
 // real Worker RPCs may outlast a tight fixed-count loop of fake16ms ticks.
 await expect.poll(async()=>{await page.clock.runFor(16);return page.evaluate(()=>battleScene.state().scene==='soldier_step');},
  {timeout:30_000,intervals:[20,50,100]}).toBe(true);
}
async function evidence(page,testInfo,name){
 await page.screenshot({path:testInfo.outputPath(name+'.png'),fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
}
async function attach(testInfo,name,value){const body=Buffer.from(JSON.stringify(value,null,2));await writeFile(testInfo.outputPath(name+'.json'),body);await testInfo.attach(name,{body,contentType:'application/json'});}
async function nativeMarkerPixels(page,marker,position){
 // Read the live backing buffer and the shipped atlas independently. The
 // detached reference canvas never replaces or writes into the game canvas.
 return page.evaluate(async({marker,position})=>{
  const asset=path=>GamePaths.asset(path),response=await fetch(asset('/assets/battle-markers-original/index.json'));
  if(!response.ok)throw Error('Native marker manifest could not be inspected');
  const manifest=await response.json(),key=`enemy:${['平','山','水'].indexOf(marker.type)}:${marker.teams}${marker.commander?':commander':''}`;
  const frame=manifest.frames[key];if(!frame)throw Error('No native marker frame for '+key);
  const image=new Image();image.src=asset(manifest.atlas.path);await image.decode();
  const reference=document.createElement('canvas');reference.width=reference.height=64;
  const context=reference.getContext('2d',{willReadFrequently:true});context.imageSmoothingEnabled=false;
  context.drawImage(image,...frame.source_rect,0,0,64,64);
  const expected=context.getImageData(0,0,64,64).data,canvas=document.querySelector('[data-battle-canvas]');
  const actual=canvas.getContext('2d').getImageData(position.x*64,position.y*64,64,64).data;
  let differences=0;for(let i=0;i<actual.length;i+=4)if(actual[i]!==expected[i]||actual[i+1]!==expected[i+1]||actual[i+2]!==expected[i+2]||actual[i+3]!==expected[i+3])differences++;
  const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(byte=>byte.toString(16).padStart(2,'0')).join('');
  return {schema:manifest.schema,key,source:manifest.source,atlas:manifest.atlas,source_rect:frame.source_rect,
   canvas_backing:[canvas.width,canvas.height],pixels_compared:64*64,different_pixels:differences,
   actual_sha256:await hash(actual),atlas_frame_sha256:await hash(expected)};
 },{marker,position});
}
async function troopSourceEvidence(page,testInfo,library){
 const examples=['verified_original_rom','original_table_transcription','design_trait_inference','design_region_inference','retained_design','fallback_design'].map(kind=>library.find(person=>person.affinity_source?.source_kind===kind));
 expect(examples.every(Boolean)).toBe(true,'Original ROM, transcribed and explicitly designed troop assignments all disclose their provenance');
 const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
 await page.locator('#library').click();const proof=[];
 for(const person of examples){
  await page.locator('#library-search').fill(person.person_id);await expect(page.locator('.person-detail')).toHaveCount(1);await page.locator('.person-detail').click();
  for(const language of ['zh-Hant','ja']){
   await page.locator('#dialog-language').selectOption(language);
   const source=page.locator(`#dialog [data-officer-affinity-source][data-person-id="${person.person_id}"]:visible`);
   await expect(source).toHaveAttribute('data-officer-affinity-source',person.affinity_source.source_kind);await expect(source).toHaveAttribute('data-officer-affinity-code',String(person.affinity));
   await expect(source).toContainText(['平軍','山軍','水軍'][person.affinity]);
   const descriptions={verified_original_rom:['原版ROM資料','原作ROMの資料'],original_table_transcription:['原版公開表轉錄','原作公開表の転記'],design_trait_inference:['生涯特性推定（本作配置）','経歴・特性からの推定（本作設定）'],design_region_inference:['出場地域推定（本作配置）','登場地域からの推定（本作設定）'],retained_design:['沿用本作配置','既存の本作設定を継続'],fallback_design:['本作預設（資料不足）','本作の初期設定（資料不足）']};
   const description=descriptions[person.affinity_source.source_kind][language==='ja'?1:0];
   await expect(source).toContainText(description);proof.push({person_id:person.person_id,language,code:person.affinity,source_kind:person.affinity_source.source_kind,visible_text:await source.innerText()});
   if(person===examples[0])await evidence(page,testInfo,'original-troop-source-'+language);
  }
  await page.locator('#back-library').click();
 }
 await page.locator('#dialog [data-cancel]').click();await expect(page.locator('#dialog')).toBeHidden();return proof;
}

async function combatFrameSample(page,value,manifest){
 return page.evaluate(async({pieces,manifest})=>{
  const host=document.querySelector('[data-battle-scene]'),data=host.dataset;
  if(data.soldierCombatSource!=='supplemental-4x')return null;
  const actor=data.soldierAnimationActor,piece=pieces[actor],index=Number(data.soldierCombatFrame);
  if(!piece)return null;
  const action=data.soldierCombatAction,palette=piece.side==='attackers'?'friendly':'enemy';
  const row=manifest.types[piece.kind][action][palette],image=new Image();image.src=GamePaths.asset(row.path);await image.decode();
  const reference=document.createElement('canvas');reference.width=reference.height=64;
  const context=reference.getContext('2d',{willReadFrequently:true});context.imageSmoothingEnabled=false;
  if(palette==='enemy'){context.translate(64,0);context.scale(-1,1);}
  context.drawImage(image,...row.frames[index].source_rect,0,0,64,64);
  const expected=context.getImageData(0,0,64,64).data,canvas=host.querySelector('[data-battle-canvas]');
  const actual=canvas.getContext('2d').getImageData(piece.x*64,piece.y*64,64,64).data;
  let solid=0,different=0;const mismatch=[];
  for(let n=0;n<actual.length;n+=4)if(expected[n+3]===255){solid++;if(actual[n]!==expected[n]||actual[n+1]!==expected[n+1]||actual[n+2]!==expected[n+2]||actual[n+3]!==255){different++;mismatch.push([n/4%64,Math.floor(n/4/64)]);}}
  const crop=document.createElement('canvas');crop.width=crop.height=64;crop.getContext('2d').putImageData(new ImageData(actual,64,64),0,0);
  const sha=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(byte=>byte.toString(16).padStart(2,'0')).join('');
  return {key:palette+':'+piece.kind+':'+action,actor,kind:piece.kind,action,palette,index,
   phase:data.soldierCombatPhase,event_index:Number(data.soldierAnimationEvent),source:data.soldierCombatSource,
   scene_mode:data.battleSceneMode,label_mode:data.soldierLabelMode,canvas_backing:[canvas.width,canvas.height],viewport:[innerWidth,innerHeight],
   solid_pixels:solid,different_pixels:different,sha256:await sha(actual),presentation_time_ms:performance.now(),
   mismatch_bbox:mismatch.length?[Math.min(...mismatch.map(p=>p[0])),Math.min(...mismatch.map(p=>p[1])),Math.max(...mismatch.map(p=>p[0]))+1,Math.max(...mismatch.map(p=>p[1]))+1]:null,
   reference_png:different?reference.toDataURL('image/png'):null,png:crop.toDataURL('image/png')};
 },{pieces:value.pieces,manifest});
}

async function soldierLabelEvidence(page,testInfo,value){
 const scene=page.locator('[data-battle-scene]'),button=scene.locator('[data-soldier-label-toggle]');
 const before=await save(page),proof=[];
 await expect(button).toBeVisible();await expect(scene).toHaveAttribute('data-soldier-label-mode','kind');
 await expect(button).toHaveAttribute('aria-pressed','false');await expect(button).toContainText('V');
 const initial=await page.locator('[data-battle-canvas]').evaluate(canvas=>canvas.toDataURL('image/png'));
 await button.click();await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
 await expect(button).toHaveAttribute('aria-pressed','true');
 const counts=await page.locator('[data-battle-canvas]').evaluate(canvas=>canvas.toDataURL('image/png'));
 expect(counts).not.toBe(initial,'The visible canvas switches type/team labels to current soldier counts');
 for(const language of ['zh-Hant','ja']){
  await locale(page,language);await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
  await expect(button).toContainText(language==='ja'?'人数':'人數');
  await evidence(page,testInfo,value.mode+'-soldier-count-mode-'+language);
  proof.push({language,mode:await scene.getAttribute('data-soldier-label-mode'),button:await button.innerText()});
 }
 const input=page.locator('[data-siege-piece-order]').first();await input.focus();await page.keyboard.press('v');
 await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
 await page.locator('#load').click();await expect(page.locator('#dialog')).toBeVisible();await page.keyboard.press('v');
 await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');await page.keyboard.press('Escape');await expect(page.locator('#dialog')).toBeHidden();
 await button.focus();
 for(const shortcut of ['Shift+v','Control+v','Meta+v','Alt+v']){
  await page.keyboard.press(shortcut);await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
 }
 await page.keyboard.down('v');await expect(scene).toHaveAttribute('data-soldier-label-mode','kind');
 await page.keyboard.down('v');await expect(scene).toHaveAttribute('data-soldier-label-mode','kind');await page.keyboard.up('v');
 const kindHover=await soldierLabelContrast(button);
 await evidence(page,testInfo,value.mode+'-soldier-type-mode-ja');
 expect(await save(page)).toEqual(before,'Label modes, language, keyboard repeats and input focus never mutate the saved campaign or RNG');
 await button.click();await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
 const troopsHover=await soldierLabelContrast(button);
 const box=await button.boundingBox();expect(box).toBeTruthy();
 if(testInfo.project.name==='touch-chromium')expect(box.height).toBeGreaterThanOrEqual(44);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await load(page,before,'soldier-label-presentation-reset.json');
 await expect(scene).toHaveAttribute('data-soldier-label-mode','kind');await expect(button).toHaveAttribute('aria-pressed','false');
 await button.click();await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
 return {languages:proof,hover_contrast:{kind:kindHover,troops:troopsHover},button_css_size:{width:box.width,height:box.height},read_load_resets_to:'kind',saved_campaign_unchanged:true};
}

async function soldierLabelContrast(button){
 await button.hover({force:true});
 const colors=await button.evaluate(node=>{const s=getComputedStyle(node);return {foreground:s.color,background:s.backgroundColor};});
 const luminance=value=>{const rgb=value.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
 const a=luminance(colors.foreground),b=luminance(colors.background),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
 expect(ratio,'Hovered label mode has readable text in both normal and busy states').toBeGreaterThanOrEqual(4.5);
 return {...colors,ratio};
}

async function compactSoldierToolbarEvidence(page,testInfo,mode,stage,{advanceClock=false}={}){
 const original=page.viewportSize(),proof=[];
 try{
  for(const viewport of [{width:1280,height:600},{width:844,height:390}]){
   await page.setViewportSize(viewport);
   if(advanceClock)await page.clock.runFor(32);
   for(const labelMode of ['kind','troops']){
   const scene=page.locator('[data-battle-scene]');
   if(await scene.getAttribute('data-soldier-label-mode')!==labelMode)await scene.locator('[data-soldier-label-toggle]').click({force:true});
   let previous='';await expect.poll(async()=>{
    const dimensions=await scene.evaluate(host=>{const bar=host.querySelector('.nes-battle-toolbar').getBoundingClientRect(),canvas=host.querySelector('[data-battle-canvas]').getBoundingClientRect();return [bar.width,bar.height,canvas.width,canvas.height].join(':');});
    const settled=previous===dimensions;previous=dimensions;return settled;
   },{timeout:5000,intervals:[50,100,200]}).toBe(true);
   // Independent busy-layout replay also advances RAF after each resize so
   // the production journal relocation runs alongside CSS/ResizeObserver.
   const name=mode+'-'+stage+'-toolbar-'+viewport.width+'x'+viewport.height+'-'+labelMode;
   await page.screenshot({path:testInfo.outputPath(name+'.png'),fullPage:true});
   const row=await page.locator('[data-battle-scene] .nes-battle-toolbar').evaluate(toolbar=>{
    const box=node=>{const r=node.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
    return {toolbar:box(toolbar),canvas_css:box(toolbar.closest('[data-battle-scene]').querySelector('[data-battle-canvas]')),children:[...toolbar.children].filter(node=>!node.hidden&&node.getBoundingClientRect().width>0).map(node=>({text:node.textContent,box:box(node)})),document_width:document.documentElement.scrollWidth,viewport_width:innerWidth};
   });
   proof.push({viewport,label_mode:labelMode,...row});await attach(testInfo,name,row);
   expect(row.document_width,mode+' '+stage+' '+viewport.width+'px has no page overflow').toBeLessThanOrEqual(row.viewport_width);
   for(const child of row.children){
    expect(child.box.x,mode+' '+stage+' '+viewport.width+'px: '+child.text+' left boundary').toBeGreaterThanOrEqual(row.toolbar.x-.5);
    expect(child.box.right,mode+' '+stage+' '+viewport.width+'px: '+child.text+' right boundary').toBeLessThanOrEqual(row.toolbar.right+.5);
   }
   }
  }
 }finally{await page.setViewportSize(original);if(advanceClock)await page.clock.runFor(32);}
 return proof;
}

async function busySoldierToolbarReplay(page,testInfo,value,expected){
 await load(page,value.save,'independent-'+value.mode+'-busy-layout-replay.json');
 const scene=page.locator('[data-battle-scene]'),button=page.locator('#siege-step');
 if(!await button.isVisible())await page.locator('#inspector-toggle').click();await expect(button).toBeEnabled();
 await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+1000));await button.click({force:true});
 await waitSoldierReplay(page);await expect(scene).toHaveAttribute('data-soldier-combat-source','supplemental-4x');await expect(page.locator('body')).toHaveClass(/\bbusy\b/);
 const committed=await save(page);expect(committed).toEqual(expected);
 const layouts=await compactSoldierToolbarEvidence(page,testInfo,value.mode,'busy',{advanceClock:true});
 await expect(scene.locator('[data-battle-skip]')).toBeVisible();expect(await save(page)).toEqual(committed);
 await page.clock.resume();await animation(page,{withView:false});expect(await save(page)).toEqual(committed);
 return {independent_public_command_replay:true,start_rng:value.save.state.rng,committed_rng:committed.state.rng,
  equals_original_committed_save:true,layouts};
}

async function attackCycleEvidence(page,testInfo,kind='attack-cycles'){
 const value=fixture(kind);
 // Browser plugin not available in this session. This uses the repository's
 // pinned Playwright clock only for RAF presentation, never game state or RNG.
 // Install before a fresh boot because the renderer captures RAF at creation.
 if(kind==='attack-cycles')await opening(page);
 await load(page,value.save,'controlled-'+value.mode+'-both-armies-four-frame-actions.json');
 const scene=page.locator('[data-battle-scene]');await expect(scene).toHaveAttribute('data-soldier-combat-assets','ready');
 const manifest=await page.evaluate(async()=>{const r=await fetch(GamePaths.asset('/assets/soldier-combat-actions-v1/index.json'));if(!r.ok)throw Error('Four-frame action manifest missing');return r.json();});
 expect(manifest.schema).toBe('tk2-soldier-combat-actions-v1');expect(manifest.frame_size).toEqual([64,64]);expect(manifest.logical_size).toEqual([16,16]);expect(manifest.frames_per_action).toBe(4);
 const labelProof=await soldierLabelEvidence(page,testInfo,value);
 labelProof.compact_idle=await compactSoldierToolbarEvidence(page,testInfo,value.mode,'idle');
 const initial=await read(page,false),button=page.locator('#siege-step');
 if(!await button.isVisible())await page.locator('#inspector-toggle').click();await expect(button).toBeEnabled();
 await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+1000));
 await button.click({force:true});
 await waitSoldierReplay(page);
 const samples=new Map(),overlays=new Map();let committed=null,started=false,busyLabelsChecked=false;
 // 16 ms ticks are shorter than each37.5 ms phase of a real150 ms event.
 // Worker RPC remains real; the clock only prevents short frames being lost
 // to screenshot/IPC latency. Each sample reads the live backing buffer.
 for(let tick=0;tick<340;tick++){
  await page.clock.runFor(16);
  const sample=await combatFrameSample(page,value,manifest);
  if(sample){
   sample.sample_tick=tick;sample.clock_elapsed_ms=(tick+1)*16;
   started=true;
   if(!committed)committed=await read(page,false);
   if(!busyLabelsChecked){
    await expect(page.locator('body')).toHaveClass(/\bbusy\b/);
    await scene.locator('[data-soldier-label-toggle]').click({force:true});await expect(scene).toHaveAttribute('data-soldier-label-mode','kind');
    labelProof.busy_kind_hover=await soldierLabelContrast(scene.locator('[data-soldier-label-toggle]'));
    await page.keyboard.press('v');await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
    labelProof.busy_troops_hover=await soldierLabelContrast(scene.locator('[data-soldier-label-toggle]'));
    await expect(scene.locator('[data-battle-skip]')).toBeVisible();
    await evidence(page,testInfo,value.mode+'-busy-count-mode-with-skip');
    expect(await save(page)).toEqual(committed.save,'Busy animation label controls only redraw presentation');busyLabelsChecked=true;
   }
   if(!samples.has(sample.key))samples.set(sample.key,new Map());
   const frames=samples.get(sample.key),old=frames.get(sample.index);
   // At release, the real projectile can initially cross its own bow sprite.
   // Retain that evidence, then select an unobscured sample of the same pose;
   // the frame pixel requirement remains exact, with no tolerance or mask.
   if(!old||sample.different_pixels<old.different_pixels)frames.set(sample.index,sample);
   const overlayKey=sample.key+':'+sample.index;
   if(sample.different_pixels&&!overlays.has(overlayKey)){
    const name=value.mode+'-overlay-'+overlayKey.replaceAll(':','-');
    await writeFile(testInfo.outputPath(name+'-actual.png'),Buffer.from(sample.png.split(',')[1],'base64'));
    await writeFile(testInfo.outputPath(name+'-reference.png'),Buffer.from(sample.reference_png.split(',')[1],'base64'));
    const {png,reference_png,...metadata}=sample;overlays.set(overlayKey,{...metadata,
     native_projectile_may_overlap:sample.action==='ranged'&&sample.index===2});
   }
  }
  if(started&&samples.size===value.attack_sequences.length&&[...samples.values()].every(frames=>frames.size===4&&[...frames.values()].every(frame=>frame.different_pixels===0)))break;
 }
 expect(started,'Visible commands must produce an actual Worker soldier-step replay').toBe(true);
 expect(busyLabelsChecked).toBe(true);
 expect([...samples.keys()].sort()).toEqual([...value.attack_sequences].sort(),'Both army palettes render every deployed melee class plus archer ranged');
 const evidenceRows=[];
 for(const [key,frames]of samples){
  expect([...frames.keys()].sort()).toEqual([0,1,2,3],key+' presents four distinct attack phases');
  expect(new Set([...frames.values()].map(frame=>frame.sha256)).size).toBe(4,key+' has four visibly different canvas poses');
  for(const sample of frames.values()){
   const name=value.mode+'-attack-'+key.replaceAll(':','-')+'-'+sample.index+'.png';
   await writeFile(testInfo.outputPath(name),Buffer.from(sample.png.split(',')[1],'base64'));
   expect(sample.solid_pixels,key+': frame '+sample.index+' contains the visible actor').toBeGreaterThan(100);
   expect(sample.scene_mode).toBe(value.mode+'-combat');expect(sample.canvas_backing).toEqual([1024,960]);
   expect(sample.different_pixels,key+': frame '+sample.index+' exact frame and facing are drawn into the live canvas').toBe(0);
   const {png,reference_png,...metadata}=sample;evidenceRows.push(metadata);
  }
 }
 const active=committed.save.state.battle.extended.siege;
 expect(active.events).toHaveLength(16);
 const soldierLedger=[];
 for(const side of ['attackers','defenders']){
  const army=initial.save.state.battle[side],after=committed.save.state.battle[side];
  const beforeTroops=army.reduce((n,unit)=>n+unit.troops,0),afterTroops=after.reduce((n,unit)=>n+unit.troops,0);
  const reportedLoss=active.events.filter(event=>value.pieces[event.target]?.side===side&&value.pieces[event.target]?.kind!=='general').reduce((n,event)=>n+event.loss,0);
  expect(afterTroops).toBeLessThan(beforeTroops);expect(beforeTroops-afterTroops).toBe(reportedLoss,'Actual army losses equal the committed individual-soldier receipt');
  soldierLedger.push({side,before_troops:beforeTroops,after_troops:afterTroops,reported_loss:reportedLoss});
 }
 expect(committed.save.state.rng.draws-initial.save.state.rng.draws).toBe(2);
 expect(await save(page)).toEqual(committed.save,'Sampling forty visible poses never changes the committed result or RNG');
 await page.clock.resume();await animation(page,{withView:false});expect(await save(page)).toEqual(committed.save);
 await expect(scene).toHaveAttribute('data-soldier-label-mode','troops');
 await load(page,committed.save,'four-frame-actual-result-roundtrip.json');
 await expect(scene).toHaveAttribute('data-soldier-label-mode','kind');
 await evidence(page,testInfo,value.mode+'-four-frame-actions-final-counts');
 labelProof.compact_busy_replay=await busySoldierToolbarReplay(page,testInfo,value,committed.save);
 return {setup:value.setup,mode:value.mode,seed:value.seed,army_troops:value.army_troops,before_rng:initial.save.state.rng,
  after_rng:committed.save.state.rng,label_mode:{...labelProof,busy_button_and_v:true,skip_preserves:'troops'},soldier_ledger:soldierLedger,events:active.events,
  overlaid_initial_samples:[...overlays.values()],frames:evidenceRows};
}

test('field soldier formations expose ten hundred-person teams and replay actual individual orders without extra damage',async({page},testInfo)=>{
 const macro=fixture('field'),contact=fixture('contact'),touch=testInfo.project.name==='touch-chromium',proof=[];
 await page.clock.install();await opening(page);await load(page,macro.save);
 const scene=page.locator('[data-battle-scene]');await expect(scene).toHaveAttribute('data-battle-scene-mode','tactical');
 await expect(scene.locator('[data-soldier-label-toggle]')).toBeHidden();
 await expect(scene).toHaveAttribute('data-tactical-marker-style','original-native-atlas');
 const before=await read(page),markers=JSON.parse(await scene.getAttribute('data-battle-markers'));
 const types=before.view.catalog.officer_troop_types,battle=before.save.state.battle;
 expect(types.schema).toBe('tk2-officer-troop-types-view-v1');expect(types.rules_version).toBe('officer-troop-types-v1');
 expect(markers.length).toBe(before.save.state.battle.attackers.length+before.save.state.battle.defenders.length);
 for(const marker of markers){
  const metadata=types.officers[String(marker.id)],unit=battle[marker.side].find(unit=>String(unit.id)===String(marker.id));
  expect(metadata).toBeTruthy();expect([0,1,2]).toContain(metadata.code);expect(marker.type).toBe(['平','山','水'][metadata.code]);
  expect(metadata.base_code).toBe(before.save.state.officers[String(marker.id)].profile.terrain_affinity);
  expect(['verified_original_rom','original_table_transcription','design_trait_inference','design_region_inference','retained_design','fallback_design','generated_design']).toContain(metadata.source_kind);
  expect(marker.troops).toBe(unit.troops);expect(marker.teams).toBe(Math.min(10,Math.ceil(marker.troops/100)));expect(marker.teams).toBeGreaterThanOrEqual(1);expect(marker.teams).toBeLessThanOrEqual(10);
  expect(marker.commander).toBe(String(marker.id)===String(battle[marker.side][0].id));
 }
 const actorMarker=markers.find(row=>String(row.id)===String(macro.actor));expect(actorMarker.troops).toBe(1000);expect(actorMarker.teams).toBe(10);
 // The second defender is neither selected nor attackable from the selected
 // actor, so its entire64×64 native frame is free of selection overlays.
 const inspected=markers.find(row=>String(row.id)===String(battle.defenders[1].id));
 expect(String(inspected.id)).not.toBe(String(macro.target));
 const selected=await scene.getAttribute('data-battle-selected-actor');
 expect(before.view.catalog.battle_tactical.actors[selected].attack_targets.map(String)).not.toContain(String(inspected.id));
 const native=await nativeMarkerPixels(page,inspected,battle.extended.tactical.positions[String(inspected.id)]);
 expect(native.schema).toBe('tk2-battle-markers-original-v1');expect(native.source).toBe('original-chr-and-native-tactical-marker-routine');
 expect(native.pixels_compared).toBe(4096);expect(native.different_pixels).toBe(0);expect(native.actual_sha256).toBe(native.atlas_frame_sha256);
 expect(native.canvas_backing).toEqual([496*4,384*4]);
 expect(await save(page)).toEqual(before.save,'Native atlas loading, inspection and screenshots never migrate saved profiles or draw game RNG');
 await evidence(page,testInfo,'original-native-tactical-flags');
 proof.push({stage:'native-marker-atlas',native,types,markers});
 proof.push({stage:'troop-assignment-source-ui',sources:await troopSourceEvidence(page,testInfo,before.view.catalog.library)});
 expect(await save(page)).toEqual(before.save,'Viewing troop-type provenance in either language leaves baseline profiles and campaign RNG unchanged');
 await cell(page,macro.actor_cell,touch);await cell(page,macro.target_cell,touch);await control(page,'attack');await idle(page);
 await expect(scene).toHaveAttribute('data-battle-scene-mode','field-formation');
 let current=await read(page,false),row=current.save.state.battle.extended.siege;
 expect(row.mode).toBe('field');expect(row.fort).toBeNull();expect(current.save.state.rng).toEqual(before.save.state.rng);
 expect(current.save.state.battle.attackers).toEqual(before.save.state.battle.attackers);expect(current.save.state.battle.defenders).toEqual(before.save.state.battle.defenders);
 expect(row.units.filter(unit=>unit.side==='attackers')).toHaveLength(11);
 expect(row.units.filter(unit=>unit.side==='attackers'&&unit.kind!=='general').map(unit=>unit.troops)).toEqual(Array(10).fill(100));
 await expect(page.locator('[data-siege-piece-count^="a"]')).toHaveCount(11);
 const preview=current.save;await page.locator('[data-siege-formation="1"]').click();expect(await save(page)).toEqual(preview);
 await evidence(page,testInfo,'field-native-formation-ten-teams');await control(page,'siege-form');await idle(page);
 await expect(page.locator('[data-siege-piece-order]')).toHaveCount(11);
 const formed=await read(page,false);for(const input of await page.locator('[data-siege-piece-order]').all())await input.selectOption('wait');
 await page.locator('#siege-piece-a1').selectOption('advance');expect(await save(page)).toEqual(formed.save,'Per-team order drafts never mutate the game');
 await control(page,'siege-step');current=await animation(page,{withView:false});row=current.save.state.battle.extended.siege;
 expect(row.piece_orders.attackers.a1).toBe('advance');expect(row.piece_orders.attackers.a2).toBe('wait');expect(row.round).toBe(2);
 expect(row.units.map(unit=>[unit.id,unit.x,unit.y])).not.toEqual(formed.save.state.battle.extended.siege.units.map(unit=>[unit.id,unit.x,unit.y]));
 await load(page,current.save,'controlled-field-per-team-roundtrip.json');expect(await save(page)).toEqual(current.save);
 proof.push({stage:'macro-to-field',markers,round:row.round,piece_orders:row.piece_orders,events:row.events});
 for(const language of ['zh-Hant','ja']){
  await locale(page,language);await load(page,contact.save,'controlled-field-infantry-archer-cavalry-contact.json');
  await expect(scene).toHaveAttribute('data-battle-scene-mode','field-orders');await expect(page.locator('[data-siege-piece-order]')).toHaveCount(11);
  const initial=await read(page,false),step=page.locator('#siege-step');
  if(!await step.isVisible())await page.locator('#inspector-toggle').click();await expect(step).toBeEnabled();
  await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+1000));await step.click({force:true});
  await waitSoldierReplay(page);
  await expect(page.locator('[data-battle-skip]')).toBeVisible();
  expect(await page.evaluate(()=>battleScene.state().scene)).toBe('soldier_step');
  // Only the presentation clock is paused. Worker commands and their receipt
  // remain real; IPC/screenshot latency cannot miss this short native replay.
  const canvas=page.locator('[data-battle-canvas]'),first=await canvas.evaluate(node=>node.toDataURL('image/png'));
  let second=first;
  for(let frame=0;frame<8&&second===first;frame++){
   await page.clock.runFor(80);second=await canvas.evaluate(node=>node.toDataURL('image/png'));
  }
  expect(second!==first,'Actual committed attack events have visible animation frames').toBe(true);
  await writeFile(testInfo.outputPath('soldier-animation-'+language+'-a.png'),Buffer.from(first.split(',')[1],'base64'));
  await writeFile(testInfo.outputPath('soldier-animation-'+language+'-b.png'),Buffer.from(second.split(',')[1],'base64'));
  const committed=await read(page,false),active=committed.save.state.battle.extended.siege;
  expect(active).toBeTruthy();expect(active.events.length).toBeGreaterThan(0);expect(active.events.length).toBeLessThanOrEqual(44);
  expect(active.events.some(event=>event.kind==='melee'&&event.actor===contact.contact_pieces.infantry)).toBe(true);
  expect(active.events.some(event=>event.kind==='arrow'&&event.actor===contact.contact_pieces.archer)).toBe(true);
  expect(active.events.some(event=>event.kind==='melee'&&event.actor===contact.contact_pieces.cavalry)).toBe(true);
  // This controlled legal contact owns the explicit reciprocal-damage
  // property. Natural campaign movement tests also allow one-sided losses.
  for(const side of ['attackers','defenders'])expect(committed.save.state.battle[side].reduce((sum,u)=>sum+u.troops,0)).toBeLessThan(initial.save.state.battle[side].reduce((sum,u)=>sum+u.troops,0),'Both actual armies take soldier damage in this controlled reciprocal-contact case');
  expect(committed.save.state.rng.draws-initial.save.state.rng.draws).toBe(2,'Each side rolls its native attack base once, never one roll per rendered hit');
  await page.clock.resume();await animation(page,{withView:false});expect(await save(page)).toEqual(committed.save);
  await evidence(page,testInfo,'soldier-piece-counts-and-orders-'+language);proof.push({language,before_rng:initial.save.state.rng,after_rng:committed.save.state.rng,events:active.events});
 }
 proof.push({stage:'both-palettes-four-frame-melee-and-ranged',...await attackCycleEvidence(page,testInfo)});
 proof.push({stage:'castle-both-palettes-four-frame-melee-and-ranged',...await attackCycleEvidence(page,testInfo,'siege-cycles')});
 await attach(testInfo,'actual-soldier-orders-events-and-rng',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('successful battlefield conversion immediately enables an eleventh friendly officer and empty-castle occupation wins',async({page},testInfo)=>{
 const converted=fixture('conversion'),occupation=fixture('occupation'),touch=testInfo.project.name==='touch-chromium';
 await opening(page);await load(page,converted.save,'controlled-seeded-live-conversion.json');
 const before=await read(page,false),battle=before.save.state.battle;
 expect(battle.attackers).toHaveLength(10);expect(battle.defenders).toHaveLength(10);
 await page.locator(`[data-actor="${converted.actor}"]`).click();await page.locator(`[data-target="${converted.target}"]`).click();await control(page,'tactic');
 await page.locator('#tactic-choice').selectOption('8');expect(await save(page)).toEqual(before.save);
 await page.locator('#confirm-tactic').click();let current=await animation(page),after=current.save.state.battle;
 expect(after.attackers).toHaveLength(11);expect(after.defenders).toHaveLength(9);
 expect(after.attackers.find(unit=>unit.id===converted.target).troops).toBe(converted.target_troops);
 expect(after.defenders.some(unit=>unit.id===converted.target)).toBe(false);expect(current.save.state.officers[converted.target].faction_id).toBe('wei');expect(current.save.state.officers[converted.target].loyalty).toBe(converted.expected_loyalty);
 expect(after.extended.tactical.positions[converted.target]).toEqual(battle.extended.tactical.positions[converted.target]);
 expect(after.extended.support[converted.target].health).toBe(battle.extended.support[converted.target].health);
 expect(current.save.state.rng.draws-before.save.state.rng.draws).toBe(1);
 expect(current.view.catalog.battle_tactical.actors[String(converted.target)].can_act).toBe(true);
 const button=page.locator(`[data-actor="${converted.target}"]`);await expect(button).toBeVisible();await button.click();
 // Keep a point in reserve so this movement alone is inspected. Spending the
 // last point legitimately hands the turn to the AI and can cause new combat
 // RNG; that is a separate handoff behavior, not an animation side effect.
 const available=current.save.state.battle.extended.tactical.points.attackers;
 const route=current.view.catalog.battle_tactical.actors[String(converted.target)].reachable
  .filter(point=>point.cost>0&&point.cost<available).sort((a,b)=>a.cost-b.cost||a.y-b.y||a.x-b.x)[0];
 expect(route).toBeTruthy();const beforeMove=current.save;await cell(page,route,touch);await control(page,'battle-move');current=await animation(page,{withView:false});
 expect(current.save.state.battle.extended.tactical.positions[converted.target]).toEqual({x:route.x,y:route.y});expect(current.save.state.rng).toEqual(beforeMove.state.rng);
 expect(current.save.state.battle.extended.tactical.points.attackers).toBe(beforeMove.state.battle.extended.tactical.points.attackers-route.cost);
 await load(page,current.save,'controlled-live-conversion-roundtrip.json');await evidence(page,testInfo,'eleventh-officer-usable-after-conversion');
 const convertedSave=current.save;await load(page,occupation.save,'controlled-empty-enemy-castle.json');
 const prior=await read(page,false);expect(prior.save.state.battle.defenders.some(unit=>unit.troops>0)).toBe(true);
 await page.locator(`[data-actor="${occupation.actor}"]`).click();await cell(page,occupation.cell,touch);await control(page,'battle-move');current=await animation(page,{withView:false});
 expect(current.save.state.phase).toBe('result');expect(current.save.state.battle.outcome).toBe('victory');expect(current.save.state.battle.extended.occupation).toEqual({actor:occupation.actor,side:'attackers',...occupation.cell});
 expect(current.save.state.battle.defenders).toEqual(prior.save.state.battle.defenders);expect(current.save.state.rng).toEqual(prior.save.state.rng);
 expect(current.save.state.battle.extended.tactical.points.attackers).toBe(prior.save.state.battle.extended.tactical.points.attackers-occupation.cost);
 await evidence(page,testInfo,'empty-castle-occupation-victory');await control(page,'settle');await idle(page);await dismissEvents(page);
 const settled=await read(page,false);expect(settled.save.state.cities.danyang.owner).toBe('wei');
 await attach(testInfo,'battle-conversion-occupation-proof',{conversion_seed:converted.selected_seed,leader_virtue:converted.leader_virtue,expected_loyalty:converted.expected_loyalty,conversion:convertedSave,occupation:current.save,settled_owner:settled.save.state.cities.danyang.owner});
 expect(pageErrors.get(page)).toEqual([]);
});

test('native battlefield hospital rice shop and weapon shop use the current cell and real army resources',async({page},testInfo)=>{
 const cases=fixture('facilities'),proof=[];await opening(page);
 for(const [index,kind]of ['hospital','market','armory'].entries()){
  const value=cases[kind];await locale(page,index===1?'ja':'zh-Hant');await load(page,value.save,'controlled-native-'+kind+'-cell.json');
  await page.locator(`[data-actor="${value.actor}"]`).click();const before=await read(page),quote=before.view.catalog.battle_tactical.actors[String(value.actor)].facility;
  expect(quote.kind).toBe(kind);expect(quote.x).toBe(value.site.x);expect(quote.y).toBe(value.site.y);
  await control(page,'battle-facility-open');await expect(page.locator('#dialog')).toBeVisible();
  const side=before.save.state.battle.attacker===before.save.state.player?'attackers':'defenders';
  await expect(page.locator(`[data-battle-supply-side="${side}"]`)).toHaveAttribute('data-battle-grain',String(before.save.state.battle.extended.supply.sides[side].remaining));
  const payer=quote.payer_city;let merchandise=null;
  if(kind==='hospital')await page.locator('#battle-facility-treat').click();
  if(kind==='market'){
   const batches=page.locator('#battle-facility-batches');await batches.fill(String(quote.trade.max_batches+999));await expect(batches).toHaveValue(String(quote.trade.max_batches));
   await batches.fill('1');expect(await save(page)).toEqual(before.save,'Rice-shop quantities and previews never spend money or RNG');await page.locator('#battle-facility-buy-grain').click();
  }
  if(kind==='armory'){
   merchandise=quote.stock.weapon.find(item=>item.eligible&&item.price<=quote.gold);expect(merchandise).toBeTruthy();
   await page.locator('#battle-facility-slot').selectOption('weapon');await page.locator('#battle-facility-item').selectOption(String(merchandise.id));
   expect(await save(page)).toEqual(before.save,'Equipment selection and prices remain read-only until purchase');await page.locator('#battle-facility-buy-equipment').click();
  }
  await idle(page);
  if(await page.locator('#dialog').isVisible())await page.keyboard.press('Escape');
  await expect(page.locator('#dialog')).toBeHidden();await dismissEvents(page);const current=await read(page,false);
  expect(current.save.state.battle.extended.tactical).toEqual(before.save.state.battle.extended.tactical,'Village services do not spend tactical movement or move an officer');expect(current.save.state.extension.command_books).toEqual(before.save.state.extension.command_books,'Battlefield services do not spend strategic books');
  if(kind==='hospital'){
   expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-quote.medical_gold);expect(current.save.state.battle.extended.support[value.actor].health).toBeGreaterThan(before.save.state.battle.extended.support[value.actor].health);expect(current.save.state.battle.extended.support[value.actor].health).toBeLessThanOrEqual(quote.max_health);expect(current.save.state.rng.draws-before.save.state.rng.draws).toBe(1);
  }else if(kind==='market'){
   expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-quote.trade.rate);expect(current.save.state.cities[payer].grain).toBe(before.save.state.cities[payer].grain);expect(current.save.state.battle.extended.supply.sides[side].remaining).toBe(before.save.state.battle.extended.supply.sides[side].remaining+quote.trade.batch_grain);await expect(page.locator(`[data-battle-supply-side="${side}"]`)).toHaveAttribute('data-battle-grain',String(current.save.state.battle.extended.supply.sides[side].remaining));expect(current.save.state.rng).toEqual(before.save.state.rng);
  }else{
   expect(current.save.state.officers[value.actor].weapon_id).toBe(merchandise.id);expect(current.save.state.officers[value.actor].profile).toEqual(before.save.state.officers[value.actor].profile);expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-merchandise.price);expect(current.save.state.rng).toEqual(before.save.state.rng);
  }
  await evidence(page,testInfo,'native-battlefield-service-'+kind);await load(page,current.save,'controlled-'+kind+'-service-roundtrip.json');
  proof.push({kind,actor:value.actor,site:value.site,payer,before_gold:before.save.state.cities[payer].gold,after_gold:current.save.state.cities[payer].gold,before_rng:before.save.state.rng,after_rng:current.save.state.rng});
 }
 await attach(testInfo,'battlefield-village-services-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('fire arrows burn carried grain and conversion loyalty gates stay actionable with exact points, RNG and saved receipts',async({page},testInfo)=>{
 await opening(page);const proof=[];
 for(const kind of ['fire','conversion71','conversion70']){
  const value=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_tactic_effect_fixture.py',import.meta.url).pathname,kind],{encoding:'utf8',maxBuffer:12*1024*1024,timeout:90_000}));
  await load(page,value.save,'controlled-original-tactic-'+kind+'.json');
  await page.locator(`[data-actor="${value.actor}"]`).click();await page.locator(`[data-target="${value.target}"]`).click();
  const before=await read(page);await control(page,'tactic');await page.locator('#tactic-choice').selectOption(String(value.tactic));
  const forecast=page.locator('#tactic-effect-preview .tactic-effect-forecast:visible');
  await expect(forecast).toHaveAttribute('data-tactic-success',String(value.preview.success_percent));
  await expect(page.locator('#confirm-tactic')).toBeEnabled();
  if(kind==='conversion71')await expect(forecast).toContainText(/必定失敗|必ず失敗/);
  await page.locator('#dialog-language').selectOption('ja');await expect(page.locator('#tactic-effect-preview .tactic-effect-forecast[data-l10n-native="ja"]')).toBeVisible();
  if(kind==='fire')await expect(forecast).toContainText('携行兵糧');
  expect(await save(page)).toEqual(before.save,'Forecast and language changes do not roll effects or spend points');
  await evidence(page,testInfo,'original-tactic-preview-'+kind);
  await page.locator('#confirm-tactic').click();const after=await animation(page),prior=before.save.state,next=after.save.state;
  expect(next.rng.draws-prior.rng.draws).toBe(kind==='fire'?2:kind==='conversion71'?0:1);
  expect(next.battle.extended.tactical.points.attackers).toBe(prior.battle.extended.tactical.points.attackers-before.view.catalog.battle_tactical.tactic_costs[value.tactic]);
  for(const city of Object.keys(prior.cities))expect(next.cities[city].grain).toBe(prior.cities[city].grain,'Tactics do not debit distant city warehouses');
  const receipt=next.extension.events.items.filter(row=>row.kind==='tactic').at(-1);
  expect(receipt.details.success).toBe(value.expected_success);
  if(kind==='fire'){
   const a=prior.battle.extended.supply.sides.defenders,b=next.battle.extended.supply.sides.defenders,loss=a.remaining-b.remaining;
   expect(loss).toBeGreaterThanOrEqual(value.preview.grain_loss_min);expect(loss).toBeLessThanOrEqual(value.preview.grain_loss_max);expect(receipt.details.grain_loss).toBe(loss);
   expect(b.journal.at(-1)).toEqual({kind:'fire',day:prior.battle.extended.supply.days,grain:loss});
   await expect(page.locator('[data-battle-supply-side="defenders"]')).toHaveAttribute('data-battle-grain',String(b.remaining));
  }else{
   expect(receipt.details.success_percent).toBe(value.preview.success_percent);expect(receipt.details.target_loyalty).toBe(value.target_loyalty);
   expect(next.officers[value.target].faction_id).toBe(kind==='conversion70'?next.player:prior.officers[value.target].faction_id);
   if(kind==='conversion70')await expect(page.locator(`[data-actor="${value.target}"]`)).toBeEnabled();
  }
  await load(page,after.save,'controlled-original-tactic-'+kind+'-roundtrip.json');expect(await save(page)).toEqual(after.save,'Committed effect and grain destruction survive real import');
  proof.push({kind,actor:value.actor,target:value.target,preview:value.preview,receipt:receipt.details,rng_delta:next.rng.draws-prior.rng.draws});
 }
 await attach(testInfo,'original-tactic-effects-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('arrival-based deployment uses paired native zones and preserves old battle positions across language and save loads',async({page},testInfo)=>{
 await opening(page);
 const rows=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_deployment_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:12*1024*1024,timeout:90_000}));
 expect(rows[0].provenance.attacker_zone).not.toBe(rows[1].provenance.attacker_zone);
 const proof=[];
 for(const value of rows){
  await load(page,value.save,'controlled-native-arrival-'+value.source+'.json');
  const scene=page.locator('[data-battle-scene]'),label=scene.locator('[data-battle-deployment-label]');
  await expect(scene).toHaveAttribute('data-battle-deployment','native_pair');
  await expect(scene).toHaveAttribute('data-battle-approach-city',value.source);await expect(label).toBeVisible();
  const initial=await read(page);expect(initial.save.state.battle.extended.tactical.positions).toEqual(value.positions);
  await locale(page,'zh-Hant');await expect(label).toContainText('進軍');
  await locale(page,'ja');await expect(label).toContainText('側から進軍');await expect(label).toHaveAttribute('title',/原作テンプレート/);
  expect(await save(page)).toEqual(initial.save,'Inspecting paired deployment and changing language do not redeploy, spend AP or roll RNG');
  await evidence(page,testInfo,'paired-arrival-'+value.source);
  await page.locator(`[data-actor="${value.actor}"]`).click();
  const current=await read(page),board=current.view.catalog.battle_tactical;
  const destination=[...board.actors[String(value.actor)].reachable].sort((a,b)=>a.cost-b.cost||a.y-b.y||a.x-b.x)[0];
  expect(destination).toBeTruthy();await cell(page,destination,testInfo.project.name==='touch-chromium');await control(page,'battle-move');
  const moved=await animation(page);
  expect(moved.save.state.battle.extended.tactical.positions[String(value.actor)]).toEqual({x:destination.x,y:destination.y});
  expect(moved.save.state.battle.extended.deployment).toEqual(value.provenance);
  expect(moved.save.state.battle.extended.tactical.points.attackers).toBe(current.save.state.battle.extended.tactical.points.attackers-destination.cost);
  expect(moved.save.state.rng).toEqual(current.save.state.rng);
  await load(page,moved.save,'moved-native-arrival-roundtrip.json');expect(await save(page)).toEqual(moved.save);
  proof.push({arrival:value.source,provenance:value.provenance,initial:value.positions,moved_to:destination});
 }
 const boxed=rows.find(row=>row.boxed).boxed;
 await load(page,boxed.save,'controlled-friendly-surround.json');
 const blocked=(await read(page)).view.catalog.battle_tactical.actors[String(boxed.actor)];
 expect(blocked.can_act).toBe(true);expect(blocked.reachable).toEqual([]);expect(blocked.attack_targets).toEqual([]);
 expect(Object.values(blocked.tactic_targets).every(ids=>ids.length===0)).toBe(true);
 await cell(page,boxed.save.state.battle.extended.tactical.positions[String(boxed.actor)],testInfo.project.name==='touch-chromium');
 await expect(page.locator(`[data-actor="${boxed.actor}"]`)).toBeEnabled();await expect(page.locator(`[data-actor="${boxed.actor}"]`)).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('#battle-move')).toBeDisabled();await expect(page.locator('.battle-move-reason')).toContainText(/限制|占有/);
 expect(await save(page)).toEqual(boxed.save,'A surrounded officer remains inspectable without moving through allies');
 await page.locator('#load').click();
 await page.locator('#save-file').setInputFiles({name:'damaged-new-deployment.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(rows[0].missing_grid))});
 await idle(page);await expect(page.locator('#notice')).toHaveClass(/error/);await expect(page.locator('#dialog')).toBeVisible();
 expect(await save(page)).toEqual(boxed.save,'A new battle missing its coordinates is rejected rather than redeployed by legacy bootstrap');
 await page.locator('#dialog [data-cancel]').click();
 await load(page,rows[0].without_provenance,'existing-battle-without-deployment-receipt.json');
 await expect(page.locator('[data-battle-scene]')).toHaveAttribute('data-battle-deployment','retained');
 await expect(page.locator('[data-battle-deployment-label]')).toBeHidden();
 expect(await save(page)).toEqual(rows[0].without_provenance,'An existing battle without provenance is not redeployed or backfilled on load');
 await attach(testInfo,'paired-deployment-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('phantom seals only movement with bilingual counts, actual contact, daily expiry and exact saved state',async({page},testInfo)=>{
 await opening(page);
 const rows=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_phantom_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:90_000}));
 const [cast,restricted,expiry]=rows,proof=[];
 await load(page,cast.save,'controlled-phantom-cast.json');
 await page.locator(`[data-actor="${cast.actor}"]`).click();await page.locator(`[data-target="${cast.target}"]`).click();
 const original=await read(page);await control(page,'tactic');await page.locator('#tactic-choice').selectOption('2');
 const forecast=page.locator('#tactic-effect-preview .tactic-effect-forecast:visible');
 await expect(forecast).toHaveAttribute('data-tactic-success',String(cast.preview.success_percent));
 await expect(forecast).toContainText('仍可攻擊或施計');await page.locator('#dialog-language').selectOption('ja');
 await expect(forecast).toContainText('固定の行動不能ターン数ではありません');expect(await save(page)).toEqual(original.save);
 await page.locator('#confirm-tactic').click();const castResult=await animation(page);
 expect(castResult.save.state.rng.draws-original.save.state.rng.draws).toBe(1);
 expect(castResult.save.state.battle.extended.tactical.points.attackers).toBe(original.save.state.battle.extended.tactical.points.attackers-4);
 expect(castResult.save.state.battle.extended.conditions.units[String(cast.target)]).toEqual({kind:'phantom',remaining:3});
 expect(castResult.save.state.battle.extended.support).toEqual(original.save.state.battle.extended.support);
 expect(castResult.save.state.battle.attackers).toEqual(original.save.state.battle.attackers);expect(castResult.save.state.battle.defenders).toEqual(original.save.state.battle.defenders);
 await expect(page.locator(`[data-target="${cast.target}"] [data-phantom-count="3"]`)).toBeVisible();
 // The committed illustrated event uses the new count, while acknowledgement
 // and language changes cannot replay the effect or consume another sample.
 const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
 await page.locator('#event-history').click();await expect(page.locator('#event-dialog')).toBeVisible();
 await expect(page.locator('#event-description .event-facts')).toContainText('付与時カウント3');
 await page.locator('#event-dialog [data-language-picker]').selectOption('zh-Hant');await expect(page.locator('#event-description .event-facts')).toContainText('施放時計數3');
 await expect(page.locator('#event-dialog .event-person img').first()).toBeVisible();await evidence(page,testInfo,'phantom-committed-event-tc');
 await dismissEvents(page);expect(await save(page)).toEqual(castResult.save);
 proof.push({kind:'cast',count:3,rng_delta:1,event:castResult.save.state.extension.events.items.at(-1).details});

 await load(page,restricted.save,'controlled-phantom-restricted.json');
 await page.locator(`[data-actor="${restricted.actor}"]`).click();await page.locator(`[data-target="${restricted.target}"]`).click();
 const locked=await read(page);await expect(page.locator(`[data-actor="${restricted.actor}"] [data-phantom-count="3"]`)).toBeVisible();
 expect(locked.view.catalog.battle_tactical.actors[String(restricted.actor)].reachable).toEqual([]);
 await expect(page.locator('#battle-move')).toBeDisabled();await expect(page.locator('#attack')).toBeEnabled();await expect(page.locator('#duel')).toBeEnabled();
 await expect(page.locator('.battle-move-reason')).toContainText('不能移動');
 await locale(page,'ja');await expect(page.locator('.battle-move-reason')).toContainText('移動できません');
 await page.locator(`[data-actor="${restricted.actor}"]`).focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');
 await expect(page.locator('#battle-move')).toBeDisabled();expect(await save(page)).toEqual(locked.save,'Keyboard movement cannot bypass phantom');
 await evidence(page,testInfo,'phantom-locked-but-can-attack-ja');
 await control(page,'tactic');await page.locator('#tactic-choice').selectOption('0');await expect(page.locator('#confirm-tactic')).toBeEnabled();await page.locator('#confirm-tactic').click();
 const recast=await animation(page);expect(recast.save.state.battle.extended.conditions.units[String(restricted.actor)].remaining).toBe(3);
 expect(recast.save.state.battle.extended.tactical.points.defenders).toBe(locked.save.state.battle.extended.tactical.points.defenders-6);
 await control(page,'attack');await idle(page);const contact=await save(page);
 expect(contact.state.battle.extended.siege).toBeTruthy();expect(contact.state.battle.extended.conditions.units[String(restricted.actor)].remaining).toBe(3);
 expect(contact.state.rng).toEqual(recast.save.state.rng);proof.push({kind:'restricted',count:3,actual_tactic:true,contact_started:true});

 await load(page,expiry.save,'controlled-phantom-expiry.json');
 await page.locator(`[data-actor="${expiry.actor}"]`).click();await expect(page.locator(`[data-actor="${expiry.actor}"] [data-phantom-count="1"]`)).toBeVisible();
 const beforeExpiry=await read(page);await control(page,'battle-wait');const expired=await animation(page);
 expect(expired.save.state.battle.round).toBe(beforeExpiry.save.state.battle.round+1);expect(expired.save.state.rng).toEqual(beforeExpiry.save.state.rng);
 expect(expired.save.state.battle.extended.conditions).toEqual({schema:'tk2-battle-conditions-v1',day:expired.save.state.battle.round,units:{}});
 expect(expired.view.catalog.battle_tactical.actors[String(expiry.actor)].reachable.length).toBeGreaterThan(0);
 await expect(page.locator(`[data-actor="${expiry.actor}"] [data-phantom-count]`)).toHaveCount(0);
 await load(page,expired.save,'phantom-expired-roundtrip.json');expect(await save(page)).toEqual(expired.save);
 proof.push({kind:'expiry',before:1,after:0,round:expired.save.state.battle.round,rng_unchanged:true});
 await attach(testInfo,'phantom-condition-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('chain applies independent connected water counts with bilingual movement-only locks and saved expiry',async({page},testInfo)=>{
 await opening(page);
 const [cast,restricted,expiry]=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_chain_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:90_000})),proof=[];
 const restrictedCount=restricted.counts[restricted.targets.indexOf(String(restricted.target))];expect([4,5]).toContain(restrictedCount);
 await load(page,cast.save,'controlled-chain-cast.json');await page.locator(`[data-actor="${cast.actor}"]`).click();await page.locator(`[data-target="${cast.target}"]`).click();
 const before=await read(page,false);await control(page,'tactic');await page.locator('#tactic-choice').selectOption('10');
 const forecast=page.locator('#tactic-effect-preview .tactic-effect-forecast:visible');
 await expect(forecast).toContainText('3 支水上敵隊各自抽取計數 4–5');await expect(forecast).toContainText('陸地敵隊只傳遞連通');
 await page.locator('#dialog-language').selectOption('ja');await expect(forecast).toContainText('陸上の敵は接続を伝えるだけ');expect(await save(page)).toEqual(before.save);
 await page.locator('#confirm-tactic').click();const after=await animation(page,{withView:false});
 expect(after.save.state.rng.draws-before.save.state.rng.draws).toBe(4);
 expect(after.save.state.battle.extended.tactical.points.attackers).toBe(before.save.state.battle.extended.tactical.points.attackers-9);
 for(const [index,id]of cast.targets.entries()){
  expect(after.save.state.battle.extended.conditions.units[id]).toEqual({kind:'chain',remaining:cast.counts[index]});
  await expect(page.locator(`[data-target="${id}"] [data-chain-count="${cast.counts[index]}"]`)).toBeVisible();
 }
 expect(after.save.state.battle.extended.conditions.units[String(cast.bridge)]).toBeUndefined();
 expect(after.save.state.battle.extended.support).toEqual(before.save.state.battle.extended.support);
 expect(after.save.state.battle.attackers).toEqual(before.save.state.battle.attackers);expect(after.save.state.battle.defenders).toEqual(before.save.state.battle.defenders);
 const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();await page.locator('#event-history').click();
 await expect(page.locator('#event-description .event-facts')).toContainText('付与時カウント'+cast.counts.join('／'));await page.locator('#event-dialog [data-language-picker]').selectOption('zh-Hant');
 await expect(page.locator('#event-description .event-facts')).toContainText('3支水上敵隊');await expect(page.locator('#event-dialog .event-person img').first()).toBeVisible();
 await evidence(page,testInfo,'chain-independent-water-event-tc');await dismissEvents(page);expect(await save(page)).toEqual(after.save);
 proof.push({kind:'cast',targets:cast.targets,counts:cast.counts,bridge:cast.bridge,draws:4,event:after.save.state.extension.events.items.at(-1).details});
 await load(page,restricted.save,'controlled-chain-restricted.json');await page.locator(`[data-actor="${restricted.target}"]`).click();await page.locator(`[data-target="${restricted.actor}"]`).click();
 const locked=await read(page);await expect(page.locator(`[data-actor="${restricted.target}"] [data-chain-count="${restrictedCount}"]`)).toBeVisible();
 expect(locked.view.catalog.battle_tactical.actors[String(restricted.target)].reachable).toEqual([]);
 await expect(page.locator('#battle-move')).toBeDisabled();await expect(page.locator('#attack')).toBeEnabled();await expect(page.locator('#duel')).toBeEnabled();
 await locale(page,'ja');await expect(page.locator('.battle-move-reason')).toContainText('連環により移動できません');
 await page.locator(`[data-actor="${restricted.target}"]`).focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');expect(await save(page)).toEqual(locked.save);
 await evidence(page,testInfo,'chain-locked-attack-enabled-ja');
 await control(page,'tactic');await page.locator('#tactic-choice').selectOption('0');await expect(page.locator('#confirm-tactic')).toBeEnabled();await page.locator('#confirm-tactic').click();const fire=await animation(page,{withView:false});
 expect(fire.save.state.battle.extended.conditions.units[String(restricted.target)]).toEqual({kind:'chain',remaining:restrictedCount});
 await control(page,'attack');await idle(page);const contact=await save(page);expect(contact.state.battle.extended.siege).toBeTruthy();expect(contact.state.battle.extended.conditions.units[String(restricted.target)]).toEqual({kind:'chain',remaining:restrictedCount});proof.push({kind:'restricted',attack:true,tactic:true,own_lock_preserved:true});
 await load(page,expiry.save,'controlled-chain-expiry.json');await expect(page.locator(`[data-target="${expiry.target}"] [data-chain-count="1"]`)).toBeVisible();
 const expiryBefore=await read(page,false);await control(page,'battle-wait');const expired=await animation(page,{withView:false});
 expect(expired.save.state.battle.round).toBe(expiryBefore.save.state.battle.round+1);expect(expired.save.state.rng).toEqual(expiryBefore.save.state.rng);expect(expired.save.state.battle.extended.conditions.units[String(expiry.target)]).toBeUndefined();
 await expect(page.locator(`[data-target="${expiry.target}"] [data-chain-count]`)).toHaveCount(0);
 await load(page,expired.save,'chain-expired-roundtrip.json');expect(await save(page)).toEqual(expired.save);proof.push({kind:'expiry',rng_unchanged:true,round:expired.save.state.battle.round});
 await attach(testInfo,'chain-condition-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('qimen targets enemies with daily losses and experience, bilingual receipts and exact zero-troop expiry',async({page},testInfo)=>{
 await opening(page);
 const [cast,restricted,daily,expiry]=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_qimen_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:90_000})),proof=[];
 // The new spatial success gate selects a different ordinary fixture seed.
 // Preserve the actual post-cast reference and every RNG/loss assertion,
 // rather than couple presentation checks to the old seed's duration.
 const castCount=restricted.count;expect(castCount).toBeGreaterThanOrEqual(6);expect(castCount).toBeLessThanOrEqual(9);
 await load(page,cast.save,'controlled-qimen-cast.json');await page.locator(`[data-actor="${cast.actor}"]`).click();await page.locator(`[data-target="${cast.target}"]`).click();
 const before=await read(page,false);await control(page,'tactic');await page.locator('#tactic-choice').selectOption('15');
 const forecast=page.locator('#tactic-effect-preview .tactic-effect-forecast:visible');await expect(forecast).toContainText('最後一次也損兵');await page.locator('#dialog-language').selectOption('ja');await expect(forecast).toContainText('自軍の盾ではなく');expect(await save(page)).toEqual(before.save);
 await page.locator('#confirm-tactic').click();const castResult=await animation(page,{withView:false});
 expect(castResult.save.state.rng.draws-before.save.state.rng.draws).toBe(2);expect(castResult.save.state.battle.extended.tactical.points.attackers).toBe(before.save.state.battle.extended.tactical.points.attackers-10);
 expect(castResult.save.state.battle.extended.conditions.units[String(cast.target)]).toEqual({kind:'qimen',remaining:castCount});
 expect(castResult.save.state.battle.extended.support).toEqual(before.save.state.battle.extended.support);expect(castResult.save.state.battle.attackers).toEqual(before.save.state.battle.attackers);expect(castResult.save.state.battle.defenders).toEqual(before.save.state.battle.defenders);
 await expect(page.locator(`[data-target="${cast.target}"] [data-qimen-count="${castCount}"]`)).toBeVisible();proof.push({kind:'cast',draws:2,count:castCount,guard_created:false});
 await load(page,restricted.save,'controlled-qimen-restricted.json');await page.locator(`[data-actor="${restricted.locked_actor}"]`).click();await page.locator(`[data-target="${restricted.enemy}"]`).click();const locked=await read(page);
 await expect(page.locator('#battle-move')).toBeDisabled();await expect(page.locator('#attack')).toBeEnabled();await expect(page.locator('#duel')).toBeEnabled();expect(locked.view.catalog.battle_tactical.actors[String(restricted.locked_actor)].reachable).toEqual([]);
 await locale(page,'ja');await expect(page.locator('.battle-move-reason')).toContainText('奇門遁甲により移動できません');await page.locator(`[data-actor="${restricted.locked_actor}"]`).focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');expect(await save(page)).toEqual(locked.save);await evidence(page,testInfo,'qimen-enemy-lock-no-self-shield-ja');
 await control(page,'tactic');await page.locator('#tactic-choice').selectOption('0');await page.locator('#confirm-tactic').click();const fire=await animation(page,{withView:false});expect(fire.save.state.battle.extended.conditions.units[String(restricted.locked_actor)].remaining).toBe(castCount);
 await control(page,'attack');await idle(page);expect((await save(page)).state.battle.extended.siege).toBeTruthy();proof.push({kind:'restricted',attack:true,tactic:true,own_counter_preserved:true});
 for(const row of[daily,expiry]){
  await load(page,row.save,'controlled-qimen-'+row.kind+'.json');const prior=await read(page,false);await control(page,'battle-wait');const result=await animation(page,{withView:false}),expected=row.expected_daily;
  expect(result.save.state.rng).toEqual(expected.rng);expect(result.save.state.battle.round).toBe(expected.round);expect(result.save.state.officers[String(row.actor)].experience).toBe(expected.experience);expect(result.save.state.officers[String(row.actor)].tier).toBe(expected.tier);
  expect(result.save.state.officers[String(row.actor)].profile).toEqual(prior.save.state.officers[String(row.actor)].profile);expect(result.save.state.soldiers).toEqual(prior.save.state.soldiers);
  const receipt=result.save.state.extension.events.items.at(-1).details;expect(receipt).toEqual({tactic:15,success:true,condition:'qimen',qimen_phase:'daily',qimen_ticks:expected.rows,experience_id:String(row.actor),experience_gain:expected.experience_gain});
  expect(result.save.state.battle.extended.conditions.units[String(row.target)]).toEqual(expected.count?{kind:'qimen',remaining:expected.count}:undefined);
  expect(result.save.state.battle.extended.conditions.high_order).toEqual(prior.save.state.battle.extended.conditions.high_order);
  if(row.kind==='daily'){
   const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();await page.locator('#event-history').click();await expect(page.locator('#event-title')).toContainText('奇門の日界効果');await expect(page.locator('#event-description .event-facts')).toContainText('損兵合計'+expected.rows.reduce((sum,tick)=>sum+tick.loss,0));
   await page.locator('#event-dialog [data-language-picker]').selectOption('zh-Hant');await expect(page.locator('#event-title')).toContainText('奇門日界效果');await expect(page.locator('#event-description .event-facts')).toContainText('增加經驗'+expected.experience_gain);await expect(page.locator('#event-dialog .event-person img').first()).toBeVisible();await evidence(page,testInfo,'qimen-daily-committed-loss-and-xp-tc');await dismissEvents(page);expect(await save(page)).toEqual(result.save);
  }else{
   expect(prior.save.state.battle.defenders.find(u=>u.id===row.target).troops).toBe(0);expect(result.save.state.rng.draws-prior.save.state.rng.draws).toBe(1);await expect(page.locator(`[data-target="${row.target}"] [data-qimen-count]`)).toHaveCount(0);
  }
  await load(page,result.save,'qimen-'+row.kind+'-roundtrip.json');expect(await save(page)).toEqual(result.save);proof.push({kind:row.kind,rows:receipt.qimen_ticks,experience_gain:receipt.experience_gain,round:expected.round});
 }
 await attach(testInfo,'qimen-condition-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('manual deployment places sequentially in native zones with zero-cost checkpoints and defender AI handoff',async({page},testInfo)=>{
 await opening(page);
 const [attacker,defender,last]=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_manual_deployment_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:90_000})),proof=[];
 const domain=value=>{const state=structuredClone(value.state);delete state.battle.extended.placement;delete state.battle.extended.tactical.positions;return state;};
 await load(page,attacker.save,'real-arrival-attacker-placement.json');const before=await read(page);
 await expect(page.locator('[data-placement-progress]')).toHaveAttribute('data-placement-progress','0');await expect(page.locator('[data-placement-total]')).toHaveAttribute('data-placement-total','3');
 await expect(page.locator('#attack')).toHaveCount(0);await expect(page.locator('#battle-wait')).toHaveCount(0);expect(before.view.catalog.battle_tactical.can_end).toBe(false);
 expect(Object.keys(before.save.state.battle.extended.tactical.positions).sort()).toEqual(attacker.position_ids);expect(Object.values(before.view.catalog.battle_tactical.actors).every(a=>!a.can_act)).toBe(true);
 await cell(page,attacker.keyboard_point,testInfo.project.name.startsWith('touch'));await idle(page);expect(await save(page)).toEqual(before.save,'Unconfirmed pointer preview is not a saved move');
 const canvas=page.locator('[data-battle-canvas]');await canvas.focus();await page.keyboard.press('b');await page.keyboard.press('Escape');await page.keyboard.press('Shift');expect(await save(page)).toEqual(before.save);
 await cell(page,attacker.future_default,testInfo.project.name.startsWith('touch'));await evidence(page,testInfo,'manual-placement-future-default-preview-tc');expect(await save(page)).toEqual(before.save);
 // Real native Enter default actions are exercised while the key remains
 // held; autorepeat must never confirm the next officer automatically.
 await page.locator('#battle-place-confirm').focus();await page.keyboard.down('Enter');await idle(page);await expect(page.locator('[data-placement-progress]')).toHaveAttribute('data-placement-progress','1');const first=await read(page);
 expect(first.save.state.battle.extended.tactical.positions[String(attacker.actor)]).toEqual(attacker.future_default);
 expect(first.view.catalog.battle_tactical.placement.actor).toBe(attacker.expected_next.actor);expect(first.save.state.battle.extended.tactical.positions[String(attacker.expected_next.actor)]).toEqual(attacker.expected_next.default_point);
 expect(Object.keys(first.save.state.battle.extended.tactical.positions).sort()).toEqual(attacker.expected_next.position_ids);expect(domain(first.save)).toEqual(domain(before.save));
 await page.keyboard.down('Enter');await page.waitForTimeout(250);await idle(page);expect(await save(page)).toEqual(first.save,'Held Enter must not confirm a second officer');await page.keyboard.up('Enter');
 await expect.poll(()=>page.evaluate(checksum=>{const raw=localStorage.getItem('three-kingdoms-autosaves-v1');if(!raw)return false;const rows=JSON.parse(raw);return rows.items?.some(row=>JSON.parse(row.raw).checksum===checksum)||false;},first.save.checksum)).toBe(true);
 await load(page,first.save,'confirmed-placement-checkpoint.json');expect(await save(page)).toEqual(first.save);await expect(page.locator('[data-placement-progress]')).toHaveAttribute('data-placement-progress','1');
 await locale(page,'ja');await expect(page.locator('#battle-place-confirm')).toContainText('この位置で確定');await expect(page.locator('#inspector')).toContainText('未確定の配置プレビューは保存しません');
 for(let i=0;i<2;i++){await control(page,'battle-place-confirm');await idle(page);}
 const ready=await read(page);expect(ready.save.state.battle.extended.placement.confirmed).toBe(3);expect(ready.view.catalog.battle_tactical.placement.pending).toBe(false);expect(domain(ready.save)).toEqual(domain(before.save));await expect(page.locator('#battle-place-confirm')).toHaveCount(0);await expect(page.locator('#battle-wait')).toBeEnabled();
 proof.push({kind:'attacker',future_does_not_occupy:true,next_default:first.save.state.battle.extended.tactical.positions[String(attacker.expected_next.actor)],resource_domain_unchanged:true,autosave:true});
 await load(page,defender.save,'real-arrival-defender-placement.json');const defenseBefore=await read(page,false);await expect(page.locator('[data-placement-total]')).toHaveAttribute('data-placement-total','10');
 await expect(page.locator('#stage')).toContainText('相手は武力と陣型に応じて配置済み');await cell(page,defender.terrain_cells['3'],testInfo.project.name.startsWith('touch'));await control(page,'battle-place-confirm');await idle(page);const water=await read(page,false);
 expect(water.save.state.battle.extended.tactical.positions[String(defender.actor)]).toEqual(defender.terrain_cells['3']);expect(domain(water.save)).toEqual(domain(defenseBefore.save));await evidence(page,testInfo,'manual-defender-commander-water-ja');proof.push({kind:'defender',commander_left_camp:true,water_legal:true,ai_has_not_acted:true});
 await load(page,last.save,'real-defender-last-placement.json');await expect(page.locator('[data-placement-progress]')).toHaveAttribute('data-placement-progress','9');const lastBefore=await read(page,false);await control(page,'battle-place-confirm');const started=await animation(page,{withView:false});
 expect(started.save.state.battle.extended.placement.confirmed).toBe(10);expect(started.save.state.battle.round).toBe(1);expect(started.save.state.battle.extended.supply.days).toBe(0);expect(started.save.state.battle.extended.tactical.side).toBe('defenders');expect(started.save.state.battle.extended.tactical.passed.attackers).toBe(true);expect(started.save.state.battle.extended.tactical.points.attackers).toBeLessThan(lastBefore.save.state.battle.extended.tactical.points.attackers);
 await expect(page.locator('#battle-place-confirm')).toHaveCount(0);await expect(page.locator('#battle-wait')).toBeEnabled();await load(page,started.save,'completed-placement-ready-battle.json');expect(await save(page)).toEqual(started.save);proof.push({kind:'defender_last',first_attacker_ai_ran:true,round:1,food_days:0});
 await attach(testInfo,'manual-deployment-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('native AI deployment keeps commanders and grouped martial order while sharing legal cells and preserving legacy saves',async({page},testInfo)=>{
 await opening(page);
 const rows=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_ai_deployment_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:90_000})),proof=[];
 // Opening troop allocation changes which defenders make the ten-unit garrison.
 const expectedOrders={defenders:['829','99','504','714','121','980','13','379','37','464'],attackers:['50','203','119']};
 const domain=value=>{const state=structuredClone(value.state);delete state.battle.extended.placement;delete state.battle.extended.tactical.positions;return state;};
 for(const row of rows){
  await load(page,row.save,'real-native-ai-'+row.side+'.json');const before=await read(page),board=before.view.catalog.battle_tactical,plan=board.auto_deployment.sides[row.side];
  expect(plan.order).toEqual(expectedOrders[row.side]);expect(plan.groups).toEqual(row.groups);expect(plan.binding).toEqual(row.binding);expect(plan.profile).toBe(row.profile);
  expect(row.order[0]).toBe(String(before.save.state.battle[row.side][0].id));
  for(const id of row.order)expect(before.save.state.battle.extended.tactical.positions[id]).toEqual(row.expected[id]);
  await expect(page.locator('[data-ai-deployment]')).toHaveAttribute('data-ai-deployment','strategy');
  await locale(page,'zh-Hant');await expect(page.locator('[data-ai-deployment]')).toContainText('依武力與陣型');expect(await save(page)).toEqual(before.save);
  if(row.side==='defenders')await evidence(page,testInfo,'ai-grouped-defender-native-tc');
  await locale(page,'ja');await expect(page.locator('[data-ai-deployment]')).toContainText('武力と陣型');expect(await save(page)).toEqual(before.save);
  if(row.side==='attackers')await evidence(page,testInfo,'ai-grouped-attacker-native-ja');
  await control(page,'battle-place-confirm');await idle(page);const after=await read(page,false);
  expect(domain(after.save)).toEqual(domain(before.save));expect(after.save.state.battle.extended.auto_deployment).toEqual(before.save.state.battle.extended.auto_deployment);
  for(const id of row.order)expect(after.save.state.battle.extended.tactical.positions[id]).toEqual(row.expected[id]);
  await load(page,after.save,'partial-manual-with-frozen-ai.json');expect(await save(page)).toEqual(after.save);
  proof.push({side:row.side,profile:row.profile,order:plan.order,groups:plan.groups,positions:row.expected,resources_unchanged:true,roundtrip:true});
 }
 const legacy=rows[0].legacy;await load(page,legacy,'controlled-previous-ordered-defaults.json');const previous=await read(page);
 expect(previous.view.catalog.battle_tactical.auto_deployment).toBeNull();await expect(page.locator('[data-ai-deployment]')).toHaveAttribute('data-ai-deployment','legacy');
 expect(await save(page)).toEqual(legacy);await control(page,'battle-place-confirm');await idle(page);const continued=await read(page,false);
 expect(continued.save.state.battle.extended.auto_deployment).toBeUndefined();
 for(const unit of legacy.state.battle.defenders)expect(continued.save.state.battle.extended.tactical.positions[String(unit.id)]).toEqual(legacy.state.battle.extended.tactical.positions[String(unit.id)]);
 expect(domain(continued.save)).toEqual(domain(legacy));proof.push({kind:'controlled_legacy_pending',not_retrofitted:true});
 await attach(testInfo,'ai-deployment-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('general tactic forecasts share native distance and tier rules without drawing results',async({page},testInfo)=>{
 await opening(page);
 const rows=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_general_tactic_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:90_000})),proof=[];
 for(const row of rows){
  await load(page,row.save,'controlled-general-distance-'+row.distance+'.json');await page.locator(`[data-actor="${row.actor}"]`).click();await page.locator(`[data-target="${row.target}"]`).click();
  const before=await read(page),quotes=before.view.catalog.battle_tactical.actors[String(row.actor)].tactic_previews;
  expect(quotes['2'][String(row.target)]).toEqual(row.preview);
  await control(page,'tactic');const forecast=page.locator('#tactic-effect-preview .tactic-effect-forecast:visible');
  for(const tid of ['0','2']){
   await page.locator('#tactic-choice').selectOption(tid);
   await expect(forecast).toHaveAttribute('data-tactic-success',String(row.percent));
   for(const language of ['zh-Hant','ja']){
    await page.locator('#dialog-language').selectOption(language);
    await expect(forecast).toContainText(language==='ja'?'プレイヤー／AI共通':'玩家／AI共用');
    await expect(forecast).toContainText(language==='ja'?'経験等級':'經驗等級');
    if(tid==='0')await expect(forecast).toContainText(language==='ja'?`距離 ${row.distance}マス`:`距離 ${row.distance} 格`);
    expect(await save(page)).toEqual(before.save,'Changing a quote/language must not pay or sample');
   }
  }
  await evidence(page,testInfo,'general-distance-'+row.distance+'-ja');
  await page.locator('#confirm-tactic').click();const after=await animation(page);
  expect(after.save.state.rng).toEqual(row.expected_rng);expect(after.save.state.battle.extended.tactical.points.attackers).toBe(before.save.state.battle.extended.tactical.points.attackers-4);
  expect(after.save.state.extension.events.items.at(-1).details.success).toBe(row.expected_success);
  expect(after.save.state.battle.extended.conditions?.units?.[String(row.target)]?.remaining??0).toBe(row.expected_success?3:0);
  expect(after.save.state.battle.attackers).toEqual(before.save.state.battle.attackers);expect(after.save.state.battle.defenders).toEqual(before.save.state.battle.defenders);
  await load(page,after.save,'committed-general-distance-'+row.distance+'.json');expect(await save(page)).toEqual(after.save);
  proof.push({distance:row.distance,threshold:row.percent,sample:row.sample,success:row.expected_success,rng:after.save.state.rng,roundtrip:true,preview_pure:true});
 }
 await attach(testInfo,'general-tactic-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});
