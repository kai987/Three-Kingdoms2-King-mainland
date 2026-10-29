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
 await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+100));await button.click({force:true});
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
 await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+100));
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
  expect(marker.troops).toBe(unit.troops);expect(marker.teams).toBe(Math.ceil(marker.troops/100));expect(marker.teams).toBeGreaterThanOrEqual(1);expect(marker.teams).toBeLessThanOrEqual(10);
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
  await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+100));await step.click({force:true});
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
 const before=await read(page),battle=before.save.state.battle;
 expect(battle.attackers).toHaveLength(10);expect(battle.defenders).toHaveLength(10);
 await page.locator(`[data-actor="${converted.actor}"]`).click();await page.locator(`[data-target="${converted.target}"]`).click();await control(page,'tactic');
 await page.locator('#tactic-choice').selectOption('8');expect((await read(page)).save).toEqual(before.save);
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
 expect(route).toBeTruthy();const beforeMove=current.save;await cell(page,route,touch);await control(page,'battle-move');current=await animation(page);
 expect(current.save.state.battle.extended.tactical.positions[converted.target]).toEqual({x:route.x,y:route.y});expect(current.save.state.rng).toEqual(beforeMove.state.rng);
 expect(current.save.state.battle.extended.tactical.points.attackers).toBe(beforeMove.state.battle.extended.tactical.points.attackers-route.cost);
 await load(page,current.save,'controlled-live-conversion-roundtrip.json');await evidence(page,testInfo,'eleventh-officer-usable-after-conversion');
 const convertedSave=current.save;await load(page,occupation.save,'controlled-empty-enemy-castle.json');
 const prior=await read(page);expect(prior.save.state.battle.defenders.some(unit=>unit.troops>0)).toBe(true);
 await page.locator(`[data-actor="${occupation.actor}"]`).click();await cell(page,occupation.cell,touch);await control(page,'battle-move');current=await animation(page);
 expect(current.save.state.phase).toBe('result');expect(current.save.state.battle.outcome).toBe('victory');expect(current.save.state.battle.extended.occupation).toEqual({actor:occupation.actor,side:'attackers',...occupation.cell});
 expect(current.save.state.battle.defenders).toEqual(prior.save.state.battle.defenders);expect(current.save.state.rng).toEqual(prior.save.state.rng);
 expect(current.save.state.battle.extended.tactical.points.attackers).toBe(prior.save.state.battle.extended.tactical.points.attackers-occupation.cost);
 await evidence(page,testInfo,'empty-castle-occupation-victory');await control(page,'settle');await idle(page);await dismissEvents(page);
 const settled=await read(page);expect(settled.save.state.cities.danyang.owner).toBe('wei');
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
  const payer=quote.payer_city;let merchandise=null;
  if(kind==='hospital')await page.locator('#battle-facility-treat').click();
  if(kind==='market'){
   const batches=page.locator('#battle-facility-batches');await batches.fill(String(quote.trade.max_batches+999));await expect(batches).toHaveValue(String(quote.trade.max_batches));
   await batches.fill('1');expect((await read(page)).save).toEqual(before.save,'Rice-shop quantities and previews never spend money or RNG');await page.locator('#battle-facility-buy-grain').click();
  }
  if(kind==='armory'){
   merchandise=quote.stock.weapon.find(item=>item.eligible&&item.price<=quote.gold);expect(merchandise).toBeTruthy();
   await page.locator('#battle-facility-slot').selectOption('weapon');await page.locator('#battle-facility-item').selectOption(String(merchandise.id));
   expect((await read(page)).save).toEqual(before.save,'Equipment selection and prices remain read-only until purchase');await page.locator('#battle-facility-buy-equipment').click();
  }
  await idle(page);
  if(await page.locator('#dialog').isVisible())await page.keyboard.press('Escape');
  await expect(page.locator('#dialog')).toBeHidden();await dismissEvents(page);const current=await read(page);
  expect(current.save.state.battle.extended.tactical).toEqual(before.save.state.battle.extended.tactical,'Village services do not spend tactical movement or move an officer');expect(current.save.state.extension.command_books).toEqual(before.save.state.extension.command_books,'Battlefield services do not spend strategic books');
  if(kind==='hospital'){
   expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-quote.medical_gold);expect(current.save.state.battle.extended.support[value.actor].health).toBeGreaterThan(before.save.state.battle.extended.support[value.actor].health);expect(current.save.state.battle.extended.support[value.actor].health).toBeLessThanOrEqual(quote.max_health);expect(current.save.state.rng.draws-before.save.state.rng.draws).toBe(1);
  }else if(kind==='market'){
   expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-quote.trade.rate);expect(current.save.state.cities[payer].grain).toBe(before.save.state.cities[payer].grain+quote.trade.batch_grain);expect(current.save.state.rng).toEqual(before.save.state.rng);
  }else{
   expect(current.save.state.officers[value.actor].weapon_id).toBe(merchandise.id);expect(current.save.state.officers[value.actor].profile).toEqual(before.save.state.officers[value.actor].profile);expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-merchandise.price);expect(current.save.state.rng).toEqual(before.save.state.rng);
  }
  await evidence(page,testInfo,'native-battlefield-service-'+kind);await load(page,current.save,'controlled-'+kind+'-service-roundtrip.json');
  proof.push({kind,actor:value.actor,site:value.site,payer,before_gold:before.save.state.cities[payer].gold,after_gold:current.save.state.cities[payer].gold,before_rng:before.save.state.rng,after_rng:current.save.state.rng});
 }
 await attach(testInfo,'battlefield-village-services-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});
