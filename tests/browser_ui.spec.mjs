/* Shipped HTML + Worker + Pyodide in isolated Chromium contexts.
 * Campaign changes use visible controls, never injected game state.
 */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import browserScopes from '../tools/browser-tests/scope.cjs';
import {approveVisibleOrders} from './browser_order_confirm.mjs';

const browserScope=browserScopes.loadBrowserScope();

const errors=new WeakMap();
test.beforeEach(async({page},testInfo)=>{
 const observed=[];errors.set(page,observed);
 page.on('pageerror',error=>observed.push(error.message));
 page.on('console',message=>{if(message.type()==='error')observed.push(message.text());});
 if(testInfo.title!=='command-book confirmations and one paid city allocation flow preserve cancellation and save recovery')await approveVisibleOrders(page);
});
async function opening(page){
 await page.goto('./');
 await enterScenarioMenu(page);
 await expect(page.locator('#game-engine-status')).toBeHidden();
 await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
}
async function enterScenarioMenu(page){
 await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
 const start=page.locator('#game-loading-start');await expect(start).toBeVisible();await expect(start).toBeEnabled();
 await start.click();await expect(page.locator('#game-loading-cover')).toBeHidden();
 await expect.poll(()=>page.locator('#inspector').evaluate(node=>!!node.closest('[inert]'))).toBe(false);
}
async function closeDialog(page){
 // Escape dismisses the topmost equipment tooltip before its parent dialog.
 const tooltip=page.locator('#game-equipment-tooltip');
 if(await tooltip.isVisible()){await page.keyboard.press('Escape');await expect(tooltip).toBeHidden();}
 await page.keyboard.press('Escape');await expect(page.locator('#dialog')).not.toBeVisible();
}
async function assertOriginalEventArt(page,modal,kind){
 const mapped={equipment_bought:['scene','armory','event-armory-interior'],grain_traded:['scene','market','event-market-interior'],treasure_sold:['scene','market','event-market-interior'],transport_departed:['scene','sortie','event-sortie'],officer_treated:['icon','facility-hospital','facility-hospital'],officer_studied:['icon','facility-school','facility-school']};
 const [type,name,asset]=mapped[kind],image=modal.locator(`img.event-original-${type}[data-original-ui="${asset}"]`);
 await expect(modal.locator('[data-event-art]')).toHaveAttribute('data-event-art',`${type}-${name}`);await expect(image).toBeVisible();
 await expect.poll(()=>image.evaluate(node=>node.complete&&node.naturalWidth>0)).toBe(true);
 const source=new URL(await image.getAttribute('src'),page.url()),expected=new URL(`assets/original-ui/${asset}-4x.png`,page.url());
 expect(source.origin).toBe(new URL(page.url()).origin);expect(source.pathname).toBe(expected.pathname);expect(source.pathname).toContain('/Three-Kingdoms2-King-mainland/assets/original-ui/');
 await expect(image).toHaveAttribute('data-original-ui-provenance','original-capture-derived');await expect(image).toHaveAttribute('alt',/原版/);
 const ja=await page.locator('html').getAttribute('lang')==='ja',captions={
  equipment_bought:ja?/武具店.*購入/:/武具店.*購置/,grain_traded:ja?/市場.*兵糧.*取引/:/市場.*米糧交易/,
  treasure_sold:ja?/市場.*宝.*売却/:/市場.*寶物出售/,transport_departed:ja?/輸送隊.*出発/:/運輸隊出發/,
  officer_treated:ja?/医館.*治療/:/醫館.*療傷/,officer_studied:ja?/学問所.*学習/:/學問所.*進修/
 };
 await expect(modal.locator('.event-art-caption')).toContainText(captions[kind]);await expect(modal.locator('.event-map')).toHaveCount(0);await expect(modal.locator('.event-facility')).toHaveCount(0);
}
async function assertFacilityFooter(page,action){
 const footer=page.locator('.facility-footer'),confirm=page.locator('#'+action),cancel=footer.locator('[data-cancel]');
 for(const scroll of ['bottom','top']){
  await page.locator('[data-facilities-dialog]').evaluate((node,edge)=>{node.scrollTop=edge==='bottom'?node.scrollHeight:0;},scroll);
  for(const control of [footer,confirm,cancel]){
   await expect(control).toBeInViewport();const r=await control.evaluate(node=>{const box=node.getBoundingClientRect();return {top:box.top,bottom:box.bottom,viewport:innerHeight};});
   expect(r.top).toBeGreaterThanOrEqual(0);expect(r.bottom).toBeLessThanOrEqual(r.viewport+1);
  }
 }
}
async function clickCityCommand(page,id){
 const group={allocate:'army',depart:'army',transfer:'army',recruit:'army','recruit-officer':'city','civil-staff':'city','city-domestic':'city','city-civic':'city','city-treasury':'warehouse','city-logistics':'warehouse','city-facilities':'town'}[id];
 if(group){const tab=page.locator('#city-command-tab-'+group);if(await tab.getAttribute('aria-selected')!=='true')await tab.click();await expect(page.locator('#city-command-panel-'+group)).toBeVisible();}
 await page.locator('#'+id).click();
}
async function openAllocation(page){await clickCityCommand(page,'allocate');await expect(page.locator('#allocation-troops')).toBeVisible();}
async function waitIdle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
async function setTroops(page,value){
 await page.locator('#allocation-troops').fill(String(value));
 await page.locator('#confirm-allocation').click();
 await waitIdle(page);
 await expect(page.locator('#allocation-troops')).toHaveValue(String(value));
 await expect(page.locator('#dialog')).toBeVisible();
}
async function tacticalRead(page){return page.evaluate(async()=>{const[a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);if(!a.ok||!b.ok)throw Error('Tactical inspection failed');const value=await b.json();return{save:await a.json(),view:value.view||value};});}
async function tacticalSave(page){return page.evaluate(async()=>{const response=await fetch('/api/save');if(!response.ok)throw Error('Tactical raw save inspection failed');return response.json();});}
async function tacticalDismiss(page){
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 for(let i=0;i<20&&await page.locator('#event-dialog').isVisible();i++){const modal=page.locator('#event-dialog'),skip=modal.locator('[data-event-skip]');await(await skip.count()?skip:modal.locator('[data-event-next]')).click();}
 await expect(page.locator('#event-dialog')).toBeHidden();
}
async function tacticalControl(page,id){
 const button=page.locator('#'+id);if(!await button.isVisible()&&await page.locator('#inspector-toggle').isVisible())await page.locator('#inspector-toggle').click();await button.click();
}
async function tacticalSettle(page,{returnToMacro=false}={}){
 await expect.poll(()=>page.evaluate(()=>!document.body.classList.contains('busy')||!!document.querySelector('[data-battle-skip]:not([hidden])')),{timeout:90_000}).toBe(true);
 const skip=page.locator('[data-battle-skip]');
 if(await skip.isVisible())try{await skip.click({timeout:1000});}catch(error){if(await skip.isVisible()||!await page.evaluate(()=>!document.body.classList.contains('busy')))throw error;}
 // A one-cell transition can naturally finish between the visibility probe
 // and Playwright's stable click. Its disappearance is a completed replay,
 // while a still-visible but unclickable Skip control remains a real failure.
 await waitIdle(page);await tacticalDismiss(page);
 if(returnToMacro){
  // An AI contact is now a pending soldier battle rather than an instant
  // aggregate reply. Close only through its ordinary visible Withdraw action
  // so the finite enemy AP phase can resume and finish honestly.
  for(let count=0;count<32;count++){
   const pending=await page.evaluate(async()=>{const r=await fetch('/api/save');const s=(await r.json()).state;return !!s.battle?.extended?.siege;});
   if(!pending)return;
   await tacticalControl(page,'siege-withdraw');await tacticalSettle(page);
  }
  throw Error('Enemy contact did not return to the tactical map within its AP bound');
 }
}
async function tacticalSoldierRound(page){
 const before=await tacticalSave(page),round=before.state.battle.extended.siege.round;
 await tacticalControl(page,'siege-step');
 await expect.poll(()=>page.evaluate(async previous=>{const r=await fetch('/api/save'),s=(await r.json()).state,b=s.battle;return !b?.extended?.siege||!!b.extended.duel||b.extended.siege.round>previous;},round)).toBe(true);
 const committed=await tacticalSave(page);await tacticalSettle(page);
 expect(await tacticalSave(page)).toEqual(committed,'Playing or skipping a committed soldier round cannot apply its damage or RNG twice');
 return {save:await tacticalSave(page)};
}
async function tacticalSoldierExchange(page,{bothSides=false,anySide=false,testInfo=null,label='soldier-contact'}={}){
 const opened={save:await tacticalSave(page)},battle=opened.save.state.battle,pending=battle.extended.siege;
 expect(pending).toBeTruthy();const own=battle.attacker===opened.save.state.player?'attackers':'defenders',foe=own==='attackers'?'defenders':'attackers';
 await expect(page.locator('[data-battle-scene]')).toHaveAttribute('data-battle-scene-mode',pending.mode==='field'?'field-formation':'siege-formation');
 const formation=page.locator('[data-siege-formation="3"]');if(await formation.count())await formation.click();
 await tacticalControl(page,'siege-form');await waitIdle(page);
 for(const input of await page.locator('[data-siege-piece-order]').all())await input.selectOption(['a0','d0'].includes(await input.getAttribute('data-siege-piece-order'))?'wait':'advance');
 let current={save:await tacticalSave(page)},rounds=0;
 const troops=(save,side)=>save.state.battle[side].reduce((sum,u)=>sum+u.troops,0);
 const total=save=>troops(save,own)+troops(save,foe);
 while(rounds<12&&current.save.state.battle.extended.siege&&
   (anySide?total(current.save)===total(opened.save):troops(current.save,foe)===troops(opened.save,foe)||bothSides&&troops(current.save,own)===troops(opened.save,own))){
  if(current.save.state.battle.extended.duel){await tacticalControl(page,'duel-withdraw');await tacticalSettle(page);current={save:await tacticalSave(page)};continue;}
  current=await tacticalSoldierRound(page);rounds++;
 }
 if(anySide)expect(total(current.save)).toBeLessThan(total(opened.save),'The natural contact commits actual soldier casualties; stronger ranged armies may inflict one-sided losses');
 else expect(troops(current.save,foe)).toBeLessThan(troops(opened.save,foe),'Actual opposing hundred-person squads take committed contact damage');
 if(bothSides)expect(troops(current.save,own)).toBeLessThan(troops(opened.save,own),'The surviving enemy squads also attack during the same soldier encounter');
 expect(current.save.state.battle.extended.tactical.points).toEqual(battle.extended.tactical.points,'Soldier rounds do not charge a second tactical attack');
 if(current.save.state.battle.extended.siege){
  if(testInfo)await historyScreenshot(page,testInfo,label);
  const raw=JSON.stringify(current.save);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'pending-soldier-contact.json',mimeType:'application/json',buffer:Buffer.from(raw)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();
  expect(await tacticalSave(page)).toEqual(current.save,'The pending encounter, piece positions, casualties and RNG survive the production raw-save loader');
  await tacticalControl(page,'siege-withdraw');await tacticalSettle(page,{returnToMacro:true});
 }
 await expect(page.locator('[data-battle-scene]')).toHaveAttribute('data-battle-scene-mode','tactical');
 return tacticalRead(page);
}
async function tacticalCell(page,point,touch=false){
 const canvas=page.locator('[data-battle-canvas]');await canvas.scrollIntoViewIfNeeded();const box=await canvas.boundingBox();expect(box).toBeTruthy();
 const position={x:(point.x*16+8)*box.width/496,y:(point.y*16+8)*box.height/384};
 if(touch)await canvas.tap({position});else await canvas.click({position});
}
async function tacticalOpening(page){
 await opening(page);await page.locator('#scenario').selectOption('mainland208-10');await page.locator('input[name=faction][value=wei]').check();
 const seed=page.locator('#seed');await seed.evaluate(node=>{for(let parent=node.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;});await seed.fill('2026');
 await page.locator('#begin').click();await waitIdle(page);await tacticalDismiss(page);
 await page.locator('#city-jump').selectOption('jiujiang');await clickCityCommand(page,'depart');await page.locator('#city-jump').selectOption('danyang');
 await expect(page.locator('#departure-target')).toHaveValue('danyang');const officers=page.locator('input[name=depart-officer]:enabled');expect(await officers.count()).toBeGreaterThanOrEqual(10);
 for(let i=0;i<10;i++)await officers.nth(i).check();await page.locator('#review-departure').click();await page.locator('#confirm-departure').click();await waitIdle(page);await tacticalDismiss(page);
 for(const id of ['end-turn','run-ai','process-arrivals']){await page.locator('#'+id).click();await waitIdle(page);await tacticalDismiss(page);}
 await expect(page.locator('[data-battle-scene]')).toHaveAttribute('data-battle-scene-mode','tactical');return tacticalRead(page);
}
async function tacticalApproach(page,{touch=false,preferred=null,max=18}={}){
 const trace=[];
 for(let step=0;step<max;step++){
  const state=await tacticalRead(page),b=state.view.game.battle,board=state.view.catalog.battle_tactical;expect(state.view.game.phase).toBe('battle');
  const own=b.attacker===state.view.game.player?'attackers':'defenders';
  const rows=Object.entries(board.actors).filter(([,row])=>row.can_act),canContact=row=>row.attack_targets.length&&board.points[own]>board.attack_cost,
   direct=rows.find(([id,row])=>(preferred===null||String(preferred)===id)&&canContact(row))||rows.find(([,row])=>canContact(row));
  if(direct){const[id,row]=direct;console.log('tactical contact',page.viewportSize().width,{round:b.round,actor:id,target:row.attack_targets[0],points:board.points});await tacticalCell(page,b.extended.tactical.positions[id],touch);await page.locator(`[data-target="${row.attack_targets[0]}"]`).click();return{state,actor:Number.isNaN(Number(id))?id:Number(id),target:row.attack_targets[0],trace};}
  const foe=own==='attackers'?'defenders':'attackers',enemies=b[foe].filter(unit=>unit.troops>0&&b.extended.support[unit.id].health>0);
  const choices=[];
  for(const[id,row]of rows){
   const source=b.extended.tactical.positions[id],distance=point=>Math.min(...enemies.map(unit=>{const p=b.extended.tactical.positions[unit.id];return Math.abs(p.x-point.x)+Math.abs(p.y-point.y);}));
   for(const point of row.reachable)if(point.cost<board.points[own]&&distance(point)<distance(source)&&!(point.x===board.camp.x&&point.y===board.camp.y))choices.push({id,point,distance:distance(point),preferred:String(preferred)===id});
  }
  choices.sort((a,b)=>Number(b.preferred)-Number(a.preferred)||a.distance-b.distance||a.point.cost-b.point.cost||String(a.id).localeCompare(String(b.id)));
  const move=choices[0];
  console.log('tactical approach',page.viewportSize().width,{step,round:b.round,points:board.points,action:move?{actor:move.id,...move.point,distance:move.distance}:'end-side'});
  if(move){await tacticalCell(page,b.extended.tactical.positions[move.id],touch);await tacticalCell(page,move.point,touch);await tacticalControl(page,'battle-move');trace.push({kind:'move',actor:move.id,...move.point});}
  else{await tacticalControl(page,'battle-wait');trace.push({kind:'wait',round:b.round});}
  await tacticalSettle(page,{returnToMacro:true});
 }
 throw Error('No real contact reached within the bounded movement exercise: '+JSON.stringify(trace));
}

test('pixel loading cover animates, plays the original title and waits for Start before the 184 chooser',async({page,context},testInfo)=>{
 // Browser plugin not available: exercise the shipped static shell and real
 // Worker with network checkpoints, without injecting campaign state.
 let releaseManifest,releasePositions,positionsRequested;
 const manifestGate=new Promise(resolve=>{releaseManifest=resolve;});
 const positionsGate=new Promise(resolve=>{releasePositions=resolve;});
 const positionsSeen=new Promise(resolve=>{positionsRequested=resolve;});
 const titleRequests=[];page.on('request',request=>{if(new URL(request.url()).pathname.endsWith('/assets/audio/original/title.mp3'))titleRequests.push(request.url());});
 await context.route('**/runtime/engine-manifest.json*',async route=>{await manifestGate;await route.continue();});
 await context.route('**/assets/city-positions.json*',async route=>{positionsRequested();await positionsGate;await route.continue();});
 await page.emulateMedia({reducedMotion:'no-preference'});
 try{
  await page.goto('./');await expect(page).toHaveTitle('三國·大陸戰役');
  const cover=page.locator('#game-loading-cover'),rider=cover.locator('.loading-cover-rider');
  await expect(cover).toBeVisible();await expect(cover).toHaveAttribute('data-phase','manifest');
  await expect(cover.locator('#game-loading-title')).toHaveText('三國志Ⅱ');
  await expect(cover.locator('.loading-cover-scenario')).toContainText('184年');
  for(const [selector,kind] of [['link[rel="icon"][href*="favicon.ico"]','ico'],['link[rel="icon"][type="image/svg+xml"]','svg'],['link[rel="apple-touch-icon"]','touch']]){
   const address=new URL(await page.locator(selector).getAttribute('href'),page.url());
   expect(address.pathname).toContain('/Three-Kingdoms2-King-mainland/');expect(address.searchParams.get('v')).toMatch(/^[a-f0-9]{64}$/);
   const icon=await page.request.get(address.href);expect(icon.status()).toBe(200);const bytes=await icon.body();
   if(kind==='ico'){expect(bytes.readUInt16LE(2)).toBe(1);expect(bytes.readUInt16LE(4)).toBe(4);}
   else if(kind==='svg')expect(bytes.toString()).toContain('shape-rendering="crispEdges"');
   else{expect(bytes.readUInt32BE(16)).toBe(180);expect(bytes.readUInt32BE(20)).toBe(180);}
  }
  await expect(page.locator('#begin')).toHaveCount(0);
  await expect.poll(()=>cover.locator('.loading-cover-art').evaluate(node=>node.complete&&node.naturalWidth>0)).toBe(true);
  await expect.poll(()=>rider.locator('img').evaluateAll(nodes=>nodes.every(node=>node.complete&&node.naturalWidth===384))).toBe(true);
  const runningTime=await rider.locator('img').first().evaluate(node=>node.getAnimations()[0]?.currentTime);
  expect(typeof runningTime).toBe('number');
  await expect.poll(()=>rider.locator('img').first().evaluate(node=>node.getAnimations()[0]?.currentTime)).toBeGreaterThan(runningTime);
  // Read the real CSS timeline above before controlling only this diagnostic
  // presentation. Pausing the parent march prevents the screenshot crop from
  // moving; seeking both sprite timelines removes CI capture-scheduling races.
  const seekFrames=async fraction=>cover.evaluate(async(node,value)=>{
   const animations=node.getAnimations({subtree:true});
   for(const animation of animations)animation.pause();
   await Promise.all(animations.map(animation=>animation.ready));
   for(const animation of animations){
    const duration=Number(animation.effect.getTiming().duration);
    if(!Number.isFinite(duration)||duration<=0)throw Error('Cover CSS animation has no finite duration');
    animation.currentTime=animation.animationName==='loading-cover-frame'?duration*value:0;
   }
   return animations.map(animation=>({name:animation.animationName,state:animation.playState,time:animation.currentTime}));
  },fraction);
  const firstTimings=await seekFrames(0);
  expect(firstTimings.filter(animation=>animation.name==='loading-cover-frame')).toHaveLength(8);
  expect(firstTimings.every(animation=>animation.state==='paused')).toBe(true);
  await expect(rider.locator('img').nth(0)).toHaveCSS('opacity','1');
  await expect(rider.locator('img').nth(1)).toHaveCSS('opacity','0');
  const riderBounds=await rider.boundingBox();expect(riderBounds).not.toBeNull();
  const firstFrame=await page.screenshot({path:testInfo.outputPath('loading-rider-frame-a.png'),clip:riderBounds,animations:'allow'});
  const secondTimings=await seekFrames(.75);
  await expect(rider.locator('img').nth(0)).toHaveCSS('opacity','0');
  await expect(rider.locator('img').nth(1)).toHaveCSS('opacity','1');
  expect(await rider.boundingBox()).toEqual(riderBounds);
  const secondFrame=await page.screenshot({path:testInfo.outputPath('loading-rider-frame-b.png'),clip:riderBounds,animations:'allow'});
  expect(secondFrame.equals(firstFrame)).toBe(false);
  await testInfo.attach('loading-css-animation-timings',{body:Buffer.from(JSON.stringify({runningTime,firstTimings,secondTimings},null,2)),contentType:'application/json'});
  await cover.evaluate(async node=>{
   const animations=node.getAnimations({subtree:true});for(const animation of animations)animation.play();
   await Promise.all(animations.map(animation=>animation.ready));
  });
  await expect.poll(()=>rider.locator('img').first().evaluate(node=>node.getAnimations()[0]?.playState)).toBe('running');
  await page.screenshot({path:testInfo.outputPath('loading-cover-animated.png'),fullPage:false,animations:'allow'});
  const bounds=await cover.evaluate(node=>({width:node.scrollWidth,viewport:innerWidth,title:node.querySelector('h1').getBoundingClientRect().width}));
  expect(bounds.width).toBeLessThanOrEqual(bounds.viewport);expect(bounds.title).toBeLessThanOrEqual(bounds.viewport);
  await page.emulateMedia({reducedMotion:'reduce'});await expect(cover).toHaveAttribute('data-motion','still');
  const motion=await cover.locator('.loading-cover-march,.loading-cover-frame').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).animationName));
  expect(motion.every(name=>name==='none')).toBe(true);
  await page.screenshot({path:testInfo.outputPath('loading-cover-reduced-motion.png'),fullPage:false});
  releaseManifest();
  await expect.poll(()=>page.evaluate(()=>window.GameBrowserEngine?.ready),{timeout:180_000}).toBe(true);
  await positionsSeen;
  // The Worker is ready while the first render still waits on its real map
  // request. Engine readiness must not expose an empty, unusable app shell.
  await expect(cover).toBeVisible();await expect(cover).toHaveAttribute('data-phase','initializing');
  await expect(page.locator('#begin')).toHaveCount(0);
  await expect(cover.locator('.loading-cover-message')).toContainText('準備戰役畫面');
  releasePositions();await expect(page.locator('#begin')).toBeEnabled({timeout:90_000});
  await expect(cover).toBeVisible();await expect(cover).toHaveAttribute('data-phase','ready');
  const start=page.locator('#game-loading-start'),sound=page.locator('#game-loading-sound');
  await expect(start).toBeVisible();await expect(start).toBeEnabled();await expect(start).toHaveText('開始遊戲');
  await expect(sound).toBeVisible();await expect(sound).toBeEnabled();await expect(page.locator('#game-loading-audio-note')).toBeVisible();
  await expect.poll(()=>page.locator('#inspector').evaluate(node=>!!node.closest('[inert]'))).toBe(true);
  expect(await page.evaluate(()=>gameAudio.getStatus().unlocked)).toBe(false);
  await sound.click();
  await expect.poll(()=>page.evaluate(()=>({scene:gameAudio.getStatus().scene,source:gameAudio.getStatus().musicSource,playing:gameAudio.getStatus().playing,unlocked:gameAudio.getStatus().unlocked,coverActive:gameAudio.getStatus().coverActive}))).toEqual({scene:'menu',source:'original',playing:true,unlocked:true,coverActive:true});
  expect(titleRequests.length).toBeGreaterThan(0);
  await expect(sound).toHaveAttribute('aria-pressed','true');
  await expect(sound).toHaveCSS('background-color','rgb(248, 216, 120)');
  await expect(sound).toHaveCSS('color','rgb(24, 16, 0)');
  await page.screenshot({path:testInfo.outputPath('loading-cover-ready-title-music.png'),fullPage:false});
  await start.click();await expect(cover).toBeHidden();
  await expect.poll(()=>page.locator('#inspector').evaluate(node=>!!node.closest('[inert]'))).toBe(false);
  await expect.poll(()=>page.evaluate(()=>gameAudio.getStatus().coverActive)).toBe(false);
  await expect(page.locator('#game-engine-status')).toBeHidden();
  await expect(page.locator('#scenario')).toHaveValue('mainland184-02');
  await expect(page.locator('#map-date')).toHaveAttribute('datetime','0184-02-01');
  await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
  await expect(page.locator('#allocate')).toHaveCount(0);
  expect(await page.evaluate(async()=>{const response=await fetch('/api/state');const value=await response.json();return(value.view||value).game;})).toBeNull();
  await page.screenshot({path:testInfo.outputPath('loading-cover-dismissed-184.png'),fullPage:false});
  // A language preference chosen in the real menu also applies to the next
  // title screen. Enter activates its native button without starting a war.
  await page.locator('#utility-menu summary').click();await page.locator('#language').selectOption('ja');
  await page.reload();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
  await expect(cover).toBeVisible();await expect(cover).toHaveAttribute('data-phase','ready');
  await expect(start).toHaveText('ゲーム開始');await expect(start).toBeEnabled();
  await page.screenshot({path:testInfo.outputPath('loading-cover-ready-ja.png'),fullPage:false});
  await start.focus();await page.keyboard.press('Enter');await expect(cover).toBeHidden();
  await expect(page.locator('#scenario')).toHaveValue('mainland184-02');await expect(page.locator('#allocate')).toHaveCount(0);
  expect(await page.evaluate(async()=>{const response=await fetch('/api/state');const value=await response.json();return(value.view||value).game;})).toBeNull();
  expect(errors.get(page)).toEqual([]);
 }finally{releaseManifest();releasePositions();}
});

test('recovery callback waits for title Start',async({page},testInfo)=>{
 // A three-character callback is invalid in the real local parser (<8).
 // It fails before creating a recovery SDK client; no provider is mocked,
 // no valid authorization code is supplied, and no account write is attempted.
 const requests=[];page.on('request',request=>requests.push({url:request.url(),method:request.method()}));
 await page.goto('./?code=bad');await expect(page).toHaveTitle('三國·大陸戰役');
 await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
 await expect.poll(()=>page.evaluate(()=>typeof appInitialized!=='undefined'&&appInitialized)).toBe(true);
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 expect(new URL(page.url()).searchParams.has('code')).toBe(false);
 const cover=page.locator('#game-loading-cover'),dialog=page.locator('#dialog');
 await expect(cover).toBeVisible();await expect(cover).toHaveAttribute('data-phase','ready');
 await expect(dialog).not.toBeVisible();expect(await dialog.evaluate(node=>node.open)).toBe(false);
 const readOpening=()=>page.evaluate(async()=>{const response=await fetch('/api/state');const value=await response.json(),state=value.view||value;return{game:state.game,revision:state.revision};});
 const before=await readOpening();expect(before.game).toBeNull();
 await page.screenshot({path:testInfo.outputPath('recovery-callback-waits-on-title.png'),fullPage:false});
 const start=page.locator('#game-loading-start');await expect(start).toBeEnabled();await start.click();
 await expect(cover).toBeHidden();await expect(dialog).toBeVisible();await expect(dialog.locator('[data-cloud-panel]')).toBeVisible();
 await expect(dialog.locator('#cloud-status')).toContainText('重設連結已失效或不屬於此瀏覽器');
 expect(await dialog.evaluate(node=>!!node.closest('[inert]'))).toBe(false);
 await page.screenshot({path:testInfo.outputPath('recovery-expired-after-title-start.png'),fullPage:false});
 await dialog.locator('.dialog-actions [data-cancel]').click();await expect(dialog).not.toBeVisible();
 await expect(page.locator('#scenario')).toHaveValue('mainland184-02');await expect(page.locator('#begin')).toBeEnabled();
 await expect(page.locator('#allocate')).toHaveCount(0);expect(await readOpening()).toEqual(before);
 const origin=new URL(page.url()).origin;
 expect(requests.filter(request=>{const url=new URL(request.url);return url.hostname.endsWith('.supabase.co')&&url.pathname.startsWith('/auth/v1/');})).toEqual([]);
 expect(requests.filter(request=>new URL(request.url).origin!==origin)).toEqual([]);
 expect(requests.filter(request=>!['GET','HEAD'].includes(request.method))).toEqual([]);
 expect(errors.get(page)).toEqual([]);
});

test('city road beds survive hidden castles, shared inland reaches draw once and ruler portraits stay centered',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland207-09');await page.locator('input[name=faction][value=shu]').check();
 const portrait=page.locator('#setup-summary .portrait-frame');await portrait.scrollIntoViewIfNeeded();
 const aligned=await page.locator('#setup-summary').evaluate(node=>{const a=node.querySelector('.portrait-frame').getBoundingClientRect(),b=node.querySelector('.setup-summary-copy').getBoundingClientRect();return {portrait:(a.top+a.bottom)/2,copy:(b.top+b.bottom)/2,height:a.height};});
 expect(aligned.height).toBe(40);expect(Math.abs(aligned.portrait-aligned.copy)).toBeLessThan(.6);
 await historyScreenshot(page,testInfo,'ruler-portrait-centered',{fullPage:false});
 const map=page.locator('#world-map');await expect(map.locator('[data-city-road-bed]')).toHaveCount(1);await expect(map.locator('.city-hit[data-city=yidu]')).toHaveCount(0);await expect(map.locator('[data-inactive-city=yidu]')).toHaveCount(1);
 // Inspect the actual displayed background after the mountain-art replacement.
 // A correct hydrology source alone does not prove that players can see it.
 await expect.poll(()=>page.evaluate(async()=>await GameMapTerrain.controller.ready)).toBe(true);
 const visibleWater=await map.evaluate(async svg=>{
  const background=[...svg.children].find(node=>node.localName==='image');
  const href=background.getAttribute('href'),image=new Image();image.src=href;await image.decode();
  const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(image,0,0);
  return {href,points:[[316,462],[328,486],[340,494],[352,506],[360,516],[362,526],[370,536],[160,480],[160,498]].map(([x,y])=>({x,y,rgba:[...ctx.getImageData(x,y,1,1).data]}))};
 });
 expect(visibleWater.href).toMatch(/\/assets\/map-western-range\.png(?:\?|$)/);
 for(const point of visibleWater.points)expect(point.rgba,`Visible river at ${point.x},${point.y}`).toEqual([0,42,248,255]);
 await expect(map.locator('#city-road-bed-mask rect[x="647"][y="472"]')).toHaveCount(1);
 const paths=await map.locator('[data-city-road-bed] > g > path').last().getAttribute('d');expect(paths).toMatch(/(?:M|L)647 472/);expect(paths).toMatch(/(?:M|L)695 346/);expect(paths).toMatch(/(?:M|L)620 346/);
 const reachKeys=await map.locator('path.river-lane').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('data-river-reach')));expect(reachKeys.length).toBeGreaterThan(15);expect(reachKeys.every(Boolean)).toBe(true);expect(new Set(reachKeys).size).toBe(reachKeys.length);
 const layers=await map.evaluate(svg=>{const nodes=[...svg.children];return {bed:nodes.findIndex(n=>n.hasAttribute('data-city-road-bed')),firstCastle:nodes.findIndex(n=>n.classList.contains('city-hit'))};});expect(layers.bed).toBeLessThan(layers.firstCastle);
 // Diagnostic camera changes affect only SVG presentation in this isolated
 // browser. They never inject campaign state, move cities or execute orders.
 const originalBox=await map.getAttribute('viewBox');await map.scrollIntoViewIfNeeded();
 for(const[name,box]of [['luoyang-hongnong-roads','550 300 220 120'],['linjiang-absent-road-junction','590 420 180 150']]){
  await map.evaluate((svg,viewBox)=>svg.setAttribute('viewBox',viewBox),box);const path=join(testInfo.outputDir,name+'.png');await map.screenshot({path});await testInfo.attach(name,{path,contentType:'image/png'});
 }
 const hidden=await page.addStyleTag({content:'#world-map .city-hit,#world-map .map-city-name{visibility:hidden}'});const emptyPath=join(testInfo.outputDir,'road-junction-without-city-icons.png');await map.screenshot({path:emptyPath});await testInfo.attach('road-junction-without-city-icons',{path:emptyPath,contentType:'image/png'});await hidden.evaluate(node=>node.remove());await map.evaluate((svg,viewBox)=>svg.setAttribute('viewBox',viewBox),originalBox);
 await page.locator('#begin').click();await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);await expect(page.locator('#map-date')).toHaveAttribute('datetime','0207-09-01');await expect(page.locator('#world-map [data-city-road-bed]')).toHaveCount(1);
 expect(errors.get(page)).toEqual([]);
});

test('dialogs, language, limits, save/load and automatic recovery use the real campaign',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 const shu=page.locator('input[name=faction][value=shu]');
 await expect(shu).toHaveCount(1);await shu.check();
 const selectedPortrait=page.locator('#setup-summary .setup-ruler-portrait [data-portrait-person]');await expect(selectedPortrait).toHaveAttribute('data-portrait-person','san14-candidate-0952');await selectedPortrait.scrollIntoViewIfNeeded();await expect.poll(()=>selectedPortrait.locator('img').evaluate(node=>node.complete&&node.naturalWidth>0)).toBe(true);
 await historyScreenshot(page,testInfo,'selected-faction-ruler',{fullPage:false});
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);
 // A real new campaign presents its illustrated opening event before commands.
 // Acknowledge that visible modal instead of forcing clicks through its backdrop.
 const openingEvent=page.locator('#event-dialog');
 await expect(openingEvent).toBeVisible();
 await expect(openingEvent.locator('#event-title')).not.toBeEmpty();
 await expect(openingEvent.locator('.event-art svg')).toBeVisible();
 const dismissBatch=openingEvent.locator('[data-event-skip]');
 await (await dismissBatch.count()?dismissBatch:openingEvent.locator('[data-event-next]')).click();
 await expect(openingEvent).not.toBeVisible();
 await expect(page.locator('.city-command-tabs [role=tab]')).toHaveCount(4);
 const boxes=await page.locator('.city-command-tabs [role=tab]').evaluateAll(nodes=>nodes.map(node=>{const r=node.getBoundingClientRect();return {top:r.top,width:r.width,height:r.height};}));expect(Math.max(...boxes.map(r=>r.top))-Math.min(...boxes.map(r=>r.top))).toBeLessThanOrEqual(1);for(const box of boxes){expect(box.width).toBeGreaterThanOrEqual(44);expect(box.height).toBeGreaterThanOrEqual(44);}
 expect(await page.locator('#inspector .resources dt').allTextContents()).toEqual(['資金','兵糧','預備兵']);
 const pairs=await page.locator('#inspector .resources .resource-pair').evaluateAll(nodes=>nodes.map(node=>{const a=node.querySelector('dt').getBoundingClientRect(),b=node.querySelector('dd').getBoundingClientRect();return{a:a.top,b:b.top};}));expect(pairs).toHaveLength(3);for(const pair of pairs)expect(Math.abs(pair.a-pair.b)).toBeLessThanOrEqual(3);
 for(const icon of await page.locator('.city-command-tabs img[data-original-ui]').all()){
  await expect(icon).toBeVisible();await expect.poll(()=>icon.evaluate(node=>node.complete&&node.naturalWidth>0)).toBe(true);
 }
 await page.locator('#city-command-tab-army').focus();await page.keyboard.press('End');
 await expect(page.locator('#city-command-tab-town')).toBeFocused();await expect(page.locator('#city-command-panel-town')).toBeVisible();
 await page.keyboard.press('Home');await expect(page.locator('#city-command-tab-city')).toBeFocused();
 await page.keyboard.press('ArrowRight');await expect(page.locator('#city-command-tab-army')).toBeFocused();
 if(testInfo.project.name==='touch-chromium'){
  const toggle=page.locator('#inspector-toggle');await expect(toggle).toBeVisible();await expect(toggle).toHaveAttribute('aria-expanded','true');
  await toggle.click();await expect(page.locator('#inspector')).toBeHidden();await expect(toggle).toHaveAttribute('aria-expanded','false');
  await page.locator('#inspector-compact-information').click();await expect(page.locator('.city-information')).toBeVisible();await closeDialog(page);
  await expect(page.locator('#inspector')).toBeHidden();await toggle.click();await expect(page.locator('#inspector')).toBeVisible();
 }
 if(testInfo.project.name==='desktop-chromium'){
  const originalViewport=page.viewportSize();await page.setViewportSize({width:1280,height:720});
  await expect(page.locator('#recruit')).toBeInViewport();
  const boundary=await page.locator('#recruit').evaluate(node=>({bottom:node.getBoundingClientRect().bottom,footer:document.querySelector('#city-command-footer').getBoundingClientRect().top}));
  expect(boundary.bottom).toBeLessThanOrEqual(boundary.footer);
  await historyScreenshot(page,testInfo,'original-city-commands',{fullPage:false});await page.setViewportSize(originalViewport);
 }else await historyScreenshot(page,testInfo,'original-city-commands',{fullPage:false});
 const city=await page.locator('#city-jump').inputValue();
 await page.locator('#load').click();
 await expect(page.locator('[data-autosave-recover]').first()).toBeVisible();
 await closeDialog(page);

 await openAllocation(page);
 const officer=await page.locator('#allocation-officer').inputValue();
 const original=Number(await page.locator('#allocation-troops').inputValue());
 expect(original).toBeGreaterThan(0);
 const maximum=await page.locator('#allocation-troops').getAttribute('max');
 await page.locator('#allocation-troops').fill('999999999');
 await expect(page.locator('#allocation-troops')).toHaveValue(maximum);
 await page.locator('#allocation-max').click();
 await expect(page.locator('#allocation-troops')).toHaveValue(maximum);
 await page.locator('#dialog-language').selectOption('ja');
 await expect(page.locator('html')).toHaveAttribute('lang','ja');
 await expect(page.locator('#dialog-title')).toContainText('兵の編制',{useInnerText:true});
 expect(await page.locator('#inspector .resources dt').allTextContents()).toEqual(['資金','兵糧','予備兵']);
 await expect(page.locator('#allocation-officer')).toHaveValue(officer);
 await page.locator('#dialog-language').selectOption('zh-Hant');
 await expect(page.locator('html')).toHaveAttribute('lang','zh-Hant');
 await expect(page.locator('#allocation-officer')).toHaveValue(officer);
 await closeDialog(page);

 const downloaded=page.waitForEvent('download');
 await page.locator('#save').click();
 const baseline=await readFile(await(await downloaded).path(),'utf8');
 expect(JSON.parse(baseline).format).toBe('three-kingdoms-remake-save');
 await openAllocation(page);await setTroops(page,0);await closeDialog(page);
 await page.locator('#load').click();await page.locator('#load-local').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 await page.locator('#city-jump').selectOption(city);
 await openAllocation(page);await page.locator('#allocation-officer').selectOption(officer);
 await expect(page.locator('#allocation-troops')).toHaveValue(String(original));
 await setTroops(page,0);await closeDialog(page);
 await page.locator('#load').click();
 await page.locator('[data-autosave-recover]').first().click();
 await expect(page.locator('#recover-confirm')).toBeVisible();
 await page.locator('#dialog-language').selectOption('ja');
 await expect(page.locator('#dialog-title')).toHaveText('復元の確認',{useInnerText:true});
 await page.locator('#recover-cancel').click();
 await expect(page.locator('[data-autosave-recover]').first()).toBeVisible();
 await page.locator('[data-autosave-recover]').first().click();
 await page.locator('#recover-confirm').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 await page.locator('#city-jump').selectOption(city);
 await openAllocation(page);await page.locator('#allocation-officer').selectOption(officer);
 await expect(page.locator('#allocation-troops')).toHaveValue(String(original));
 await closeDialog(page);
 // Compare another visible export, rather than accepting matching labels alone.
 const restoredDownload=page.waitForEvent('download');await page.locator('#save').click();
 const restored=await readFile(await(await restoredDownload).path(),'utf8');
 expect(restored).toBe(baseline);
 await page.locator('#load').click();
 await page.locator('#save-file').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{}')});
 await expect(page.locator('#notice')).not.toBeEmpty();
 await expect(page.locator('#notice')).toHaveClass(/\berror\b/);
 await expect(page.locator('#dialog')).toBeVisible();
 await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);
 await closeDialog(page);
 const rejectedDownload=page.waitForEvent('download');await page.locator('#save').click();
 expect(await readFile(await(await rejectedDownload).path(),'utf8')).toBe(baseline);
 // A new Worker after reload must recover from browser storage, not old memory.
 await page.reload();await enterScenarioMenu(page);
 await page.locator('#load').click();await page.locator('[data-autosave-recover]').first().click();
 await page.locator('#recover-confirm').click();await waitIdle(page);
 await expect(page.locator('#dialog')).not.toBeVisible();
 const reloadedDownload=page.waitForEvent('download');await page.locator('#save').click();
 expect(await readFile(await(await reloadedDownload).path(),'utf8')).toBe(baseline);
 await page.locator('#load').click();
 await page.screenshot({path:testInfo.outputPath('save-recovery.png'),fullPage:true});
 expect(errors.get(page)).toEqual([]);
});

test('map mouse/touch pan and zoom stay bounded without accidental city inspection',async({page},testInfo)=>{
 await opening(page);
 const map=page.locator('#world-map');
 await expect(map).toHaveAttribute('data-zoom','1');
 await expect(page.locator('#map-zoom-out')).toBeDisabled();
 for(let step=0;step<3;step++)await page.locator('#map-zoom-in').click();
 const before=await map.getAttribute('viewBox'),box=await map.boundingBox();
 const x=box.x+box.width*.5,y=box.y+box.height*.4;
 if(testInfo.project.use.hasTouch){
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
  for(let step=1;step<=8;step++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+step*6,y:y+step*3}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await expect(map).not.toHaveAttribute('viewBox',before);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{id:1,x:x-20,y},{id:2,x:x+20,y}]});
  for(let step=1;step<=7;step++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{id:1,x:x-20-step*10,y},{id:2,x:x+20+step*10,y}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await expect(map).toHaveAttribute('data-zoom','4');
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{id:1,x:x-90,y},{id:2,x:x+90,y}]});
  for(let step=1;step<=8;step++){const radius=90-step*10.75;await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{id:1,x:x-radius,y},{id:2,x:x+radius,y}]});}
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await expect(map).toHaveAttribute('data-zoom','1');await cdp.detach();
 }else{
  await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+48,y+24,{steps:8});await page.mouse.up();
  await expect(map).not.toHaveAttribute('viewBox',before);
  for(let step=0;step<5;step++)await page.mouse.wheel(0,-1200);
  await expect(map).toHaveAttribute('data-zoom','4');
  for(let step=0;step<5;step++)await page.mouse.wheel(0,1200);
  await expect(map).toHaveAttribute('data-zoom','1');
 }
 await expect(page.locator('#dialog')).not.toBeVisible();
 for(let step=0;step<8;step++){
  if(await page.locator('#map-zoom-in').isDisabled())break;
  await page.locator('#map-zoom-in').click();
 }
 await expect(map).toHaveAttribute('data-zoom','4');
 await expect(page.locator('#map-zoom-in')).toBeDisabled();
 await page.locator('#all-map').click();
 await expect(map).toHaveAttribute('data-zoom','1');
 await expect(page.locator('#map-zoom-out')).toBeDisabled();
 await map.locator('.city-hit').first().focus();await page.keyboard.press('Enter');
 await expect(page.locator('#dialog')).toBeVisible();
 await expect(page.locator('#dialog-title')).not.toBeEmpty();await closeDialog(page);
 const width=await page.evaluate(()=>({body:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth}));
 expect(width.body).toBeLessThanOrEqual(width.viewport);
 await page.screenshot({path:testInfo.outputPath('map-navigation.png'),fullPage:true});
 expect(errors.get(page)).toEqual([]);
});

test('failed manifest has an explicit retry starting a fresh real Worker',async({page,context},testInfo)=>{
 let manifestRequests=0;
 await context.route('**/runtime/engine-manifest.json*',async route=>{
  if(++manifestRequests===1)await route.fulfill({status:404,body:'controlled browser acceptance failure'});
  else await route.continue();
 });
 await page.goto('./');
 const retry=page.locator('#game-engine-status button');
 await expect(retry).toBeVisible();await expect(page.locator('#begin')).toHaveCount(0);
 await retry.click();await enterScenarioMenu(page);
 await expect(page.locator('#game-engine-status')).toBeHidden();expect(manifestRequests).toBe(2);
 await page.screenshot({path:testInfo.outputPath('boot-retried.png'),fullPage:true});
 expect(errors.get(page).filter(message=>!message.includes('404'))).toEqual([]);
});

test('daily marching grain loads once and consumes actual days through visible transfer controls',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=shu]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);
 const dismissEvents=async()=>{
  const events=page.locator('#event-dialog');
  if(await events.isVisible()){
   const skip=events.locator('[data-event-skip]');
   await (await skip.count()?skip:events.locator('[data-event-next]')).click();
   await expect(events).not.toBeVisible();
  }
 };
 const exported=async()=>{
  const download=page.waitForEvent('download');
  await page.locator('#save').click();
  return JSON.parse(await readFile(await(await download).path(),'utf8'));
 };
 await dismissEvents();
 await page.locator('#city-jump').selectOption('shujun');
 const initial=await exported(),source='shujun',target='bajun';
 expect(initial.state.extension.domestic.factions.shu.civil).toBeNull();
 expect(initial.state.extension.domestic.factions.shu.military).toBeNull();
 expect(initial.state.day).toBe(1);
 const startingGrain=initial.state.cities[source].grain;
 await clickCityCommand(page,'transfer');
 await expect(page.locator('#transfer-city')).toBeVisible();
 await page.locator('#transfer-city').selectOption(target);
 const landOption=page.locator('#route-mode option[data-route-kind=land]');
 await expect(landOption).toHaveCount(1);await page.locator('#route-mode').selectOption(await landOption.getAttribute('value'));
 const leader=String(initial.state.extension.leaders.shu);
 const officer=page.locator(`input[name=transfer-officer]:enabled:not([value="${leader}"])`).first();
 const officerText=await officer.getAttribute('value');
 expect(officerText).toBeTruthy();
 expect(initial.state.officers[officerText].alive).toBe(true);
 await officer.check();
 const preview=page.locator('#transfer-supply [data-supply-loaded]');
 await expect(preview).toHaveCount(1);
 const loaded=Number(await preview.getAttribute('data-supply-loaded'));
 expect(loaded).toBeGreaterThan(0);
 await expect(preview).toHaveAttribute('data-supply-consumed','0');
 await expect(preview).toHaveAttribute('data-supply-remaining',String(loaded));
 await expect(page.locator('#confirm-transfer')).toBeEnabled();
 await page.locator('#confirm-transfer').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const departing=await exported();
 const column=departing.state.extension.travel.marches.find(row=>row.source===source&&row.target===target);
 expect(column).toBeTruthy();
 expect(column.officers.map(String)).toEqual([officerText]);
 expect(departing.state.officers[officerText].health).toBe(initial.state.officers[officerText].health);
 expect(departing.state.officers[officerText].loyalty).toBe(initial.state.officers[officerText].loyalty);
 expect(column.quote.routes.every(leg=>leg.mode==='land'&&!leg.hazard)).toBe(true);
 const units=initial.state.officers[officerText].troops+100;
 let firstStage=0;
 for(let index=0;index<column.quote.routes.length;index++){
  firstStage+=column.quote.routes[index].days;
  if(initial.state.cities[column.quote.path[index+1]]?.owner===initial.state.player)break;
 }
 expect(firstStage).toBeLessThan(column.quote.days);
 expect(loaded).toBe(Math.ceil(units*firstStage/1000));
 expect(column.supply).toMatchObject({loaded,received:0,consumed:0,remaining:loaded,elapsed_days:0,route_days:0});
 expect(departing.state.cities[source].grain).toBe(startingGrain-loaded);
 const live=page.locator(`[data-march="${column.id}"] [data-supply-loaded]`);
 await expect(live).toHaveAttribute('data-supply-loaded',String(loaded));
 await expect(live).toHaveAttribute('data-supply-consumed','0');
 await expect(live).toHaveAttribute('data-supply-remaining',String(loaded));
 await page.locator('#end-turn').click();await waitIdle(page);
 await dismissEvents();
 await expect(page.locator('#run-ai')).toBeVisible();
 await page.locator('#run-ai').click();await waitIdle(page);await dismissEvents();
 await expect(page.locator('#run-ai')).not.toBeVisible();
 const next=await exported();
 expect(next.state.turn).toBe(departing.state.turn+1);
 expect([next.state.year,next.state.month,next.state.day]).toEqual([217,7,11]);
 const marched=next.state.extension.travel.marches.find(row=>row.id===column.id);
 expect(marched).toBeTruthy();
 const elapsed=Math.min(10,column.quote.days),consumed=Math.ceil(units*elapsed/1000),received=marched.supply.received;
 expect(marched.supply).toMatchObject({loaded,consumed,remaining:loaded+received-consumed,elapsed_days:elapsed,route_days:elapsed,shortage_days:0,lost:0});
 expect(next.state.officers[officerText].health).toBe(initial.state.officers[officerText].health);
 expect(next.state.officers[officerText].loyalty).toBe(initial.state.officers[officerText].loyalty);
 expect(received).toBe(marched.supply.refills.reduce((sum,row)=>sum+row.grain,0));
 // No delegate was appointed and no monthly income is due: all food spent
 // this turn comes out of the travelling bag, never the origin store again.
 expect(next.state.extension.domestic.factions.shu.civil).toBeNull();
 expect(next.state.extension.domestic.factions.shu.military).toBeNull();
 expect(next.state.cities[source].grain).toBe(departing.state.cities[source].grain);
 expect(next.state.cities[source].owner).toBe('shu');
 await expect(live).toHaveAttribute('data-supply-loaded',String(loaded));
 await expect(live).toHaveAttribute('data-supply-consumed',String(consumed));
 await expect(live).toHaveAttribute('data-supply-remaining',String(loaded+received-consumed));
 await expect(live).toHaveAttribute('data-supply-route-days',String(elapsed));
 await expect(live).toHaveAttribute('data-supply-shortage','0');
 await live.scrollIntoViewIfNeeded();
 await page.screenshot({path:testInfo.outputPath('daily-march-grain.png'),fullPage:true});
 expect(errors.get(page)).toEqual([]);
});

test('city size labels and the report adapt to available space while retaining map controls',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 const labels=page.locator('#map-labels'),names=page.locator('[data-city-label]');
 await expect(labels).toHaveAttribute('data-label-mode','major');
 const majorCount=await names.count();
 for(const [mode,count] of [['giant',4],['large',10],['all',110],['none',0],['major',majorCount]]){
  await labels.click();await expect(labels).toHaveAttribute('data-label-mode',mode);await expect(names).toHaveCount(count);
 }
 await labels.click();await labels.click();
 await page.locator('#scenario').selectOption('mainland225-07');
 await expect(labels).toHaveAttribute('data-label-mode','large');await expect(names).toHaveCount(12);
 await page.locator('#scenario').selectOption('mainland217-07');await expect(names).toHaveCount(10);
 await page.locator('#map-zoom-in').click();
 const zoom=await page.locator('#world-map').getAttribute('data-zoom');
 const city=await page.locator('#city-jump').inputValue();
 const geometry=()=>page.evaluate(()=>{
  const rect=selector=>{const r=document.querySelector(selector).getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
  return{docked:document.querySelector('.topbar').contains(document.querySelector('.journal')),reports:document.querySelectorAll('#journal').length,restarts:document.querySelectorAll('#restart').length,header:rect('.topbar'),heading:rect('.topbar-heading'),nav:rect('.topbar nav'),report:rect('.journal'),stage:rect('#stage'),main:rect('main'),side:rect('#inspector'),scrollWidth:document.documentElement.scrollWidth,width:innerWidth};
 });
 for(const viewport of [{width:1920,height:1080},{width:1440,height:900},{width:1280,height:800}]){
  await page.setViewportSize(viewport);
  await expect.poll(async()=>(await geometry()).docked).toBe(true);
  const g=await geometry();
  expect(g.reports).toBe(1);expect(g.restarts).toBe(1);
  expect(g.heading.right).toBeLessThanOrEqual(g.report.x);
  expect(g.report.right).toBeLessThanOrEqual(g.nav.x);
  expect(g.report.bottom).toBeLessThanOrEqual(g.header.bottom);
  expect(Math.abs(g.stage.bottom-g.main.bottom)).toBeLessThan(2);
  expect(Math.abs((g.stage.width-8)/(g.stage.height-8)-1352/1024)).toBeLessThan(.002);
  expect(g.side.width).toBeLessThan(viewport.width*.4);
  await expect(page.locator('#world-map')).toHaveAttribute('data-zoom',zoom);
  await expect(page.locator('#city-jump')).toHaveValue(city);
 }
 await page.locator('#utility-menu summary').click();await page.locator('#language').selectOption('ja');
 await expect(labels).toHaveAttribute('title','都市名：大都市');
 await page.locator('#utility-menu summary').click();
 await expect.poll(async()=>(await geometry()).docked).toBe(true);
 await page.screenshot({path:testInfo.outputPath('wide-report-map.png'),fullPage:true});
 for(const viewport of [{width:1280,height:850},{width:1024,height:768},{width:1000,height:768},{width:390,height:844},{width:844,height:390}]){
  await page.setViewportSize(viewport);
  await expect.poll(async()=>(await geometry()).docked).toBe(false);
  await expect(page.locator('.game-layout>.journal')).toHaveCount(1);
  const g=await geometry();expect(g.reports).toBe(1);expect(g.restarts).toBe(1);expect(g.scrollWidth).toBeLessThanOrEqual(g.width);
  if(viewport.width<=1000)expect(g.report.y).toBeGreaterThanOrEqual(g.side.bottom);
  await expect(page.locator('#world-map')).toHaveAttribute('data-zoom',zoom);
  await expect(labels).toHaveAttribute('data-label-mode','large');
 }
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:testInfo.outputPath('compact-report-map.png'),fullPage:true});
 await page.setViewportSize({width:1440,height:900});
 await expect(page.locator('.topbar>.journal')).toHaveCount(1);
 await expect(page.locator('#world-map')).toHaveAttribute('data-zoom',zoom);
 await labels.click();await expect(labels).toHaveAttribute('data-label-mode','all');
 await page.locator('#utility-menu summary').click();await page.locator('#language').selectOption('zh-Hant');
 await expect(labels).toHaveAttribute('title','城名：全部');
 await page.locator('#utility-menu summary').click();
 expect(errors.get(page)).toEqual([]);
});

async function historyScreenshot(page,testInfo,name,{fullPage=true}={}){
 const directory=process.env.TK2_HISTORY_SCREENSHOTS;
 if(directory)await mkdir(directory,{recursive:true});
 const path=directory?join(directory,`${testInfo.project.name}-${name}.png`):testInfo.outputPath(`${name}.png`);
 await page.screenshot({path,fullPage});
}

async function dismissHistoryOpening(page){
 const events=page.locator('#event-dialog');
 await expect(events).toBeVisible();
 const skip=events.locator('[data-event-skip]');
 await (await skip.count()?skip:events.locator('[data-event-next]')).click();
 await expect(events).not.toBeVisible();
}

test('Jingzhou historical openings show Zhangling and playable Jingnan prefects',async({page},testInfo)=>{
 await opening(page);
 await expect(page).toHaveTitle('三國·大陸戰役');
 const marker=id=>page.locator(`#world-map .city-hit[data-city="${id}"]`);
 for(const scenario of ['mainland191-10','mainland200-01']){
  await page.locator('#scenario').selectOption(scenario);
  await expect(marker('yiyang')).toHaveAttribute('data-owner','liu_biao');
  await expect(marker('yiyang')).toHaveAttribute('aria-label',/章陵/);
  await expect(page.locator('#city-jump option[value=yiyang]')).toContainText('章陵');
  await expect(marker('yidu')).toHaveCount(0);
  await expect(page.locator('#city-jump option[value=yidu]')).toHaveCount(0);
  expect(await marker('yiyang').locator('.castle-fill').getAttribute('fill')).toBe(
   await marker('xiangyang').locator('.castle-fill').getAttribute('fill'));
  // Real preview lookup through the city selector also chooses Liu Biao.
  await page.locator('#city-jump').selectOption('yiyang');
  await expect(page.locator('.city-information[data-inspected-city=yiyang]')).toBeVisible();
  await expect(page.locator('#dialog-title')).toContainText('章陵');
  await expect(page.locator('.city-information-owner')).toContainText('劉表');
  await expect(page.locator('input[name=faction][value=liu_biao]')).toBeChecked();
  await closeDialog(page);
  if(scenario==='mainland191-10')await historyScreenshot(page,testInfo,'191-unfounded-linjiang-preview');
 }

 await page.locator('#scenario').selectOption('mainland208-10');
 const prefects=[['changsha','han_xuan','韓玄',3,['黃忠','魏延']],['wuling','jin_xuan','金旋',2,['鞏志']],
  ['guiyang','zhao_fan','趙範',3,['陳應','鮑隆']],['lingling','liu_du','劉度',3,['劉賢','邢道榮']]];
 const fills=[];
 for(const[city,side,name,count,officers]of prefects){
  await expect(page.locator(`input[name=faction][value=${side}]`)).toHaveCount(1);
  await expect(page.locator(`input[name=faction][value=${side}]`).locator('..')).toContainText(name);
  await expect(marker(city)).toHaveAttribute('data-owner',side);
  await expect(marker(city)).toHaveAttribute('aria-label',new RegExp(name));
  const fill=await marker(city).locator('.castle-fill').getAttribute('fill');
  expect(fill).not.toBe('#ffffff');fills.push(fill);
  await page.locator('#city-jump').selectOption(city);
  const detail=page.locator(`.city-information[data-inspected-city="${city}"]`);
  await expect(detail).toHaveAttribute('data-information-mode','preview');
  await expect(detail.locator('.roster-table tbody tr')).toHaveCount(count);
  await expect(detail.locator('.city-information-owner')).toContainText(name);
  for(const officer of officers)await expect(detail.locator('.roster-table tbody tr').filter({hasText:officer})).toHaveCount(1);
  await closeDialog(page);
 }
 expect(new Set(fills).size).toBe(4);
 await expect(marker('yidu')).toHaveAttribute('data-owner','wei');
 await expect(marker('yidu')).toHaveAttribute('aria-label',/臨江/);
 await expect(page.locator('#city-jump option[value=yidu]')).toContainText('臨江');
 expect(await marker('yidu').locator('.castle-fill').getAttribute('fill')).toBe('#0078f8');
 await page.locator('input[name=faction][value=han_xuan]').check();
 await historyScreenshot(page,testInfo,'red-cliffs-prefects-preview');
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#city-jump')).toHaveValue('changsha');
 await expect(page.locator('#inspector .owner')).toContainText('韓玄');
 await expect(page.locator('#inspector [data-city-roster-officer]')).toHaveCount(3);
 // Keyboard activation exercises the map's accessible city button on both
 // viewports, without forced clicks through the compact map toolbar.
 await marker('changsha').focus();await page.keyboard.press('Enter');
 const information=page.locator('.city-information[data-inspected-city=changsha]');
 await expect(information).toHaveAttribute('data-information-mode','live');
 await expect(information).toBeVisible();
 const ruler=information.locator('.roster-table tbody tr').filter({hasText:'韓玄'});
 await expect(ruler).toHaveCount(1);await expect(ruler.locator('td').nth(5)).toHaveText('--');
 await expect(information.locator('.roster-table tbody tr').filter({hasText:'黃忠'})).toHaveCount(1);
 await expect(information.locator('.roster-table tbody tr').filter({hasText:'魏延'})).toHaveCount(1);
 await page.locator('#dialog-language').selectOption('ja');
 await expect(page.locator('html')).toHaveAttribute('lang','ja');
 await expect(ruler.locator('td').nth(5)).toHaveText('--');
 await expect(page.locator('#dialog-title')).toContainText('長沙');
 await historyScreenshot(page,testInfo,'han-xuan-live-information-ja');
 await ruler.locator('td').nth(5).scrollIntoViewIfNeeded();
 await expect(ruler.locator('td').nth(5)).toBeInViewport();
 await historyScreenshot(page,testInfo,'han-xuan-loyalty-ja');
 await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});

test('Jingzhou dated names and withdrawn cities match previews and live campaigns',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland212-12');
 await expect(page.locator('#city-jump option[value=yidu]')).toContainText('宜都');
 await expect(page.locator('#world-map .city-hit[data-city=yidu]')).toHaveAttribute('aria-label',/宜都/);
 await expect(page.locator('#city-jump option[value=yiyang]')).toContainText('章陵');
 for(const scenario of ['mainland249-01','mainland263-05']){
  await page.locator('#scenario').selectOption(scenario);
  await expect(page.locator('#world-map .city-hit[data-city=yiyang]')).toHaveCount(0);
  await expect(page.locator('#world-map [data-city-label=yiyang]')).toHaveCount(0);
  await expect(page.locator('#city-jump option[value=yiyang]')).toHaveCount(0);
  await expect(page.locator('#city-jump option[value=yidu]')).toContainText('宜都');
 }
 await historyScreenshot(page,testInfo,'263-withdrawn-yiyang-preview');
 await page.locator('#scenario').selectOption('mainland249-01');
 await page.locator('input[name=faction][value=wei]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#world-map .city-hit[data-city=yiyang]')).toHaveCount(0);
 await expect(page.locator('#city-jump option[value=yiyang]')).toHaveCount(0);
 await page.locator('#main-menu').click();
 await expect(page.locator('#scenario')).toHaveValue('mainland249-01');
 await expect(page.locator('#world-map .city-hit[data-city=yiyang]')).toHaveCount(0);
 await page.locator('#utility-menu summary').click();
 await page.locator('#language').selectOption('ja');
 await expect(page.locator('html')).toHaveAttribute('lang','ja');
 await page.locator('#utility-menu summary').click();
 await expect(page.locator('#city-jump option[value=yidu]')).toContainText('宜都');
 await historyScreenshot(page,testInfo,'249-live-return-to-menu-ja');
 expect(errors.get(page)).toEqual([]);
});

test('four DLC openings share two translated categories and preserve the separately dated Shu campaign',async({page},testInfo)=>{
 await opening(page);
 const scenarios=page.locator('#scenario'),groups=scenarios.locator('optgroup');
 await expect(groups).toHaveCount(2);
 expect(await groups.evaluateAll(nodes=>nodes.map(node=>node.label))).toEqual(['史實','假想']);
 const marker=id=>page.locator(`#world-map .city-hit[data-city="${id}"]`);
 // Retiming the custom Shu campaign must preserve the independently selected
 // July 211 Tongguan opening and its separate lazy catalog identity.
 await expect(scenarios.locator('option[value="mainland212-12"]')).toContainText('入蜀爭奪戰');
 await expect(scenarios.locator('option[value="mainland211-07-tongguan"]')).toContainText('潼關之戰');
 await scenarios.selectOption('mainland212-12');
 await expect(scenarios.locator('option:checked')).toContainText('入蜀爭奪戰');
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0212-12-01');
 await expect(marker('fengyi')).toHaveAttribute('data-owner','wei');
 await expect(scenarios.locator('optgroup[label="假想"] option[value="mainland209-06"]')).toHaveCount(1);
 for(const[id,title,date,city,owner]of[
  ['mainland198-03','呂布討伐戰','0198-03-01','xiapi','lubu'],
  ['mainland215-08','合淝之戰','0215-08-01','hanzhong','wei'],
  ['mainland211-07-tongguan','潼關之戰','0211-07-01','tianshui','ma_teng'],
  ['mainland202-06','河北爭亂','0202-06-01','wei','yuan_shang'],
 ]){
  await scenarios.selectOption(id);
  await expect(scenarios.locator('option:checked')).toContainText(title);
  await expect(scenarios.locator(`optgroup[label="史實"] option[value="${id}"]`)).toHaveCount(1);
  await expect(page.locator('#map-date')).toHaveAttribute('datetime',date);
  await expect(marker(city)).toHaveAttribute('data-owner',owner);
  await expect(page.locator(`input[name=faction][value="${owner}"]`)).toHaveCount(1);
  if(id==='mainland211-07-tongguan'){
   await expect(marker('fengyi')).toHaveAttribute('data-owner','ma_teng');
   await expect(marker('fufeng')).toHaveAttribute('data-owner','ma_teng');
   await expect(marker('jingzhao')).toHaveAttribute('data-owner','wei');
  }
  if(id==='mainland202-06')for(const[city,owner]of[['beihai','yuan_tan'],['yan','yuan_xi'],['taiyuan','gao_gan']]){
   await expect(marker(city)).toHaveAttribute('data-owner',owner);
   await expect(page.locator(`input[name=faction][value="${owner}"]`)).toHaveCount(1);
  }
  await historyScreenshot(page,testInfo,`${id}-opening-tc`);
 }
 const faction=page.locator('input[name=faction][value="yuan_shang"]');
 await faction.check();
 await page.locator('#utility-menu summary').click();
 await page.locator('#language').selectOption('ja');
 await expect(page.locator('html')).toHaveAttribute('lang','ja');
 expect(await groups.evaluateAll(nodes=>nodes.map(node=>node.label))).toEqual(['史実','仮想']);
 await expect(scenarios).toHaveValue('mainland202-06');
 await expect(faction).toBeChecked();
 await expect(page.locator('#setup-summary')).toContainText('開始時の所属を表示中です。');
 await expect(scenarios.locator('option[value="mainland198-03"]')).toContainText('呂布討伐戦');
 await expect(scenarios.locator('option[value="mainland202-06"]')).toContainText('河北争乱');
 await expect(scenarios.locator('option[value="mainland215-08"]')).toContainText('合肥の戦い');
 await expect(scenarios.locator('option[value="mainland211-07-tongguan"]')).toContainText('潼関の戦い');
 await page.locator('#utility-menu summary').click();
 await historyScreenshot(page,testInfo,'dlc-two-categories-hebei-ja');
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0202-06-01');
 await expect(page.locator('#city-jump')).toHaveValue('wei');
 await expect(page.locator('#inspector .owner')).toContainText('袁尚');
 const exportSave=async()=>{
  const download=page.waitForEvent('download');await page.locator('#save').click();
  return readFile(await(await download).path(),'utf8');
 };
 const baseline=await exportSave(),saved=JSON.parse(baseline);
 expect(saved.scenario).toBe('mainland202-06');
 expect(saved.state.player).toBe('yuan_shang');
 expect(saved.state.year).toBe(202);expect(saved.state.month).toBe(6);expect(saved.state.day).toBe(1);
 expect(saved.state.cities.wei.owner).toBe('yuan_shang');
 await page.locator('#main-menu').click();
 await expect(scenarios).toHaveValue('mainland202-06');
 await scenarios.selectOption('mainland211-07-tongguan');
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0211-07-01');
 await page.locator('#load').click();await page.locator('#load-local').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0202-06-01');
 await expect(page.locator('#inspector .owner')).toContainText('袁尚');
 expect(await exportSave()).toBe(baseline);
 await page.locator('#main-menu').click();
 await expect(scenarios).toHaveValue('mainland202-06');
 await page.locator('#utility-menu summary').click();
 await page.locator('#language').selectOption('zh-Hant');
 await expect(page.locator('html')).toHaveAttribute('lang','zh-Hant');
 expect(await groups.evaluateAll(nodes=>nodes.map(node=>node.label))).toEqual(['史實','假想']);
 await expect(scenarios).toHaveValue('mainland202-06');await expect(faction).toBeChecked();
 await page.locator('#utility-menu summary').click();
 await historyScreenshot(page,testInfo,'dlc-hebei-save-reloaded-tc');
 // Starting the date-suffixed variant exercises the shipped lazy catalog
 // manifest and Worker, beyond the immutable setup preview checked above.
 await scenarios.selectOption('mainland211-07-tongguan');
 await page.locator('input[name=faction][value="ma_teng"]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0211-07-01');
 await expect(page.locator('#city-jump')).toHaveValue('wuwei');
 await expect(page.locator('#inspector .owner')).toContainText('馬超');
 await openAllocation(page);
 await expect(page.locator('#allocation-officer option')).not.toHaveCount(0);
 await expect(page.locator('#allocation-officer')).toContainText('馬超');
 await historyScreenshot(page,testInfo,'dlc-tongguan-playable-officers-tc');
 await closeDialog(page);
 const variant=JSON.parse(await exportSave());
 expect(variant.scenario).toBe('mainland211-07-tongguan');
 expect(variant.state.player).toBe('ma_teng');
 expect(variant.state.year).toBe(211);expect(variant.state.month).toBe(7);expect(variant.state.day).toBe(1);
 expect(variant.state.cities.fengyi.owner).toBe('ma_teng');
 expect(errors.get(page)).toEqual([]);
});

test('Han Sui and the December 212 Shu opening remain playable with reviewed frontier ownership',async({page},testInfo)=>{
 // Browser plugin not available: use the repository's pinned Playwright client.
 // Scenario menu -> faction/color preview -> real Worker campaign -> exported
 // opening state; all campaign changes below use visible controls only.
 await opening(page);await expect(page).toHaveTitle('三國·大陸戰役');
 const scenarios=page.locator('#scenario'),marker=id=>page.locator(`#world-map .city-hit[data-city="${id}"]`);
 const exportSave=async()=>{
  const download=page.waitForEvent('download');await page.locator('#save').click();
  return JSON.parse(await readFile(await(await download).path(),'utf8'));
 };
 await scenarios.selectOption('mainland211-07-tongguan');
 const han=page.locator('input[name=faction][value=han_sui]');
 await expect(han).toHaveCount(1);await han.check();
 await expect(han.locator('..')).toContainText('韓遂');
 await expect(marker('jincheng')).toHaveAttribute('data-owner','han_sui');
 const hanFill=await marker('jincheng').locator('.castle-fill').getAttribute('fill');
 expect(hanFill).toBe(await han.locator('..').locator('.faction-swatch rect').getAttribute('fill'));
 expect(hanFill).not.toBe('#ffffff');
 expect(hanFill).not.toBe(await marker('tianshui').locator('.castle-fill').getAttribute('fill'));
 expect(hanFill).not.toBe(await marker('jingzhao').locator('.castle-fill').getAttribute('fill'));
 for(const city of ['wudu','yinping']){
  await expect(marker(city)).toHaveAttribute('data-owner','neutral');
  await expect(marker(city).locator('.castle-fill')).toHaveAttribute('fill','#ffffff');
 }
 await page.locator('#utility-menu summary').click();await page.locator('#language').selectOption('ja');
 await expect(page.locator('html')).toHaveAttribute('lang','ja');
 await expect(scenarios.locator('option:checked')).toContainText('潼関の戦い');
 await expect(han).toBeChecked();await expect(han.locator('..')).toContainText('韓遂');
 await page.locator('#utility-menu summary').click();
 await historyScreenshot(page,testInfo,'tongguan-han-sui-frontier-preview-ja');
 await page.locator('#begin').click();await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0211-07-01');
 await expect(page.locator('#inspector .owner')).toContainText('韓遂');
 await expect(page.locator('#inspector [data-city-roster-officer]').filter({hasText:'韓遂'})).toHaveCount(1);
 const tongguan=await exportSave();
 expect(tongguan.scenario).toBe('mainland211-07-tongguan');expect(tongguan.state.player).toBe('han_sui');
 expect(tongguan.state.cities.jincheng.owner).toBe('han_sui');
 for(const city of ['wudu','yinping'])expect(tongguan.state.cities[city].owner).toBe('neutral');
 await page.locator('#main-menu').click();await expect(page.locator('#begin')).toBeEnabled();
 await expect(scenarios.locator('option[value="mainland211-07"]')).toHaveCount(0);
 await scenarios.selectOption('mainland212-12');await page.locator('input[name=faction][value=shu]').check();
 await expect(scenarios.locator('option:checked')).toContainText('入蜀争奪戦');
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0212-12-01');
 for(const city of ['jiameng','fuxian'])await expect(marker(city)).toHaveAttribute('data-owner','shu');
 await expect(marker('danyang')).toHaveAttribute('data-owner','wu');
 await expect(marker('danyang')).toHaveAttribute('aria-label',/建業/);
 await page.locator('#utility-menu summary').click();await page.locator('#language').selectOption('zh-Hant');
 await expect(page.locator('html')).toHaveAttribute('lang','zh-Hant');
 await expect(scenarios.locator('option:checked')).toContainText('入蜀爭奪戰');
 await expect(page.locator('input[name=faction][value=shu]')).toBeChecked();
 await page.locator('#utility-menu summary').click();
 await page.locator('#begin').click();await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0212-12-01');
 await historyScreenshot(page,testInfo,'shu-december-212-live-tc');
 const shu=await exportSave();expect(shu.scenario).toBe('mainland212-12');expect(shu.state.player).toBe('shu');
 expect([shu.state.year,shu.state.month,shu.state.day]).toEqual([212,12,1]);
 for(const city of ['jiameng','fuxian'])expect(shu.state.cities[city].owner).toBe('shu');
 expect(shu.state.cities.danyang.owner).toBe('wu');

 // Reuse this browser and Worker for the earlier dated frontier corrections;
 // neither an obsolete rebel faction nor a captured capital can persist.
 await page.locator('#main-menu').click();await expect(page.locator('#begin')).toBeEnabled();
 await scenarios.selectOption('mainland188-06');
 await expect(page.locator('input[name=faction][value=ou_xing]')).toHaveCount(0);
 const sun=page.locator('input[name=faction][value=sun_jian]');
 await expect(sun).toHaveCount(1);await sun.check();
 await expect(marker('changsha')).toHaveAttribute('data-owner','sun_jian');
 await page.locator('#city-jump').selectOption('changsha');
 const changsha=page.locator('.city-information[data-inspected-city=changsha]');
 await expect(changsha).toHaveAttribute('data-information-mode','preview');
 await expect(changsha.locator('.roster-table tbody tr')).toHaveCount(7);
 for(const name of ['孫堅','程普','黃蓋','韓當','朱治','吳景','孫河'])await expect(changsha.locator('.roster-table tbody tr').filter({hasText:name})).toHaveCount(1);
 await closeDialog(page);await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0188-06-01');
 await expect(page.locator('#inspector .owner')).toContainText('孫堅');
 await expect(page.locator('#inspector [data-city-roster-officer]')).toHaveCount(7);
 const sunOpening=await exportSave();expect(sunOpening.state.player).toBe('sun_jian');
 expect(sunOpening.state.cities.changsha.owner).toBe('sun_jian');
 expect(sunOpening.state.cities.changsha.roster.officer_ids.map(id=>sunOpening.state.officers[id].person_id).sort()).toEqual(
  ["san14-candidate-0551", "san14-candidate-0703", "san14-candidate-0247", "san14-candidate-0176", "san14-candidate-0390", "san14-candidate-0289", "san14-candidate-0543"].sort());
 expect(Object.values(sunOpening.state.officers).some(officer=>officer.person_id==='san14-candidate-0065')).toBe(false);
 await historyScreenshot(page,testInfo,'188-sun-jian-live-tc');

 await page.locator('#main-menu').click();await expect(page.locator('#begin')).toBeEnabled();
 await scenarios.selectOption('mainland194-06');await page.locator('input[name=faction][value=wei]').check();
 await expect(marker('jiyin')).toHaveAttribute('data-owner','wei');
 await expect(marker('jiyin')).toHaveAttribute('aria-label',/鄄城/);
 // Zhang Miao's allied army is independently selectable, rather than an
 // ordinary Lü Bu garrison. Cao Cao still opens in the Juancheng proxy.
 await expect(marker('chenliu')).toHaveAttribute('data-owner','zhang_miao');
 const zhangMiao=page.locator('input[name=faction][value=zhang_miao]');
 await expect(zhangMiao).toHaveCount(1);await zhangMiao.check();
 await expect(page.locator('#setup-summary')).toContainText('張邈');
 await expect(page.locator('#setup-summary [data-portrait-person]')).toHaveAttribute('data-portrait-person','san14-candidate-0653');
 await page.locator('input[name=faction][value=wei]').check();
 await page.locator('#begin').click();await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0194-06-01');
 await expect(page.locator('#city-jump')).toHaveValue('jiyin');
 await expect(page.locator('#inspector .owner')).toContainText('曹操');
 const yanOpening=await exportSave();expect(yanOpening.state.player).toBe('wei');
 expect(yanOpening.state.cities.jiyin.owner).toBe('wei');expect(yanOpening.state.cities.chenliu.owner).toBe('zhang_miao');
 expect(yanOpening.state.extension.leaders.zhang_miao).toBe(652);
 expect(yanOpening.state.officers[652].person_id).toBe('san14-candidate-0653');
 expect(yanOpening.state.officers[652].faction_id).toBe('zhang_miao');
 expect(yanOpening.state.officers[652].loyalty).toBe(100);
 expect(yanOpening.state.cities.chenliu.roster.officer_ids).toContain(652);
 await historyScreenshot(page,testInfo,'194-yan-frontier-live-tc');
 expect(errors.get(page)).toEqual([]);
});

test('dated Xiaopei Qiao names and city scales appear in real scenario information',async({page},testInfo)=>{
 await opening(page);
 for(const[scenario,name,scale]of[
  ['mainland217-07','小沛','普通城'],
  ['mainland219-07','譙郡','普通城'],
  ['mainland221-07','譙郡','大城'],
 ]){
  await page.locator('#scenario').selectOption(scenario);
  await expect(page.locator('#city-jump option[value=qiao]')).toContainText(name);
  await page.locator('#city-jump').selectOption('qiao');
  const info=page.locator('.city-information[data-inspected-city=qiao]');
  await expect(info).toBeVisible();
  await expect(page.locator('#dialog-title')).toContainText(name);
  await expect(info.locator('p.small').filter({hasText:/地形/})).toContainText(scale);
  await closeDialog(page);
 }
 await page.locator('#city-jump').selectOption('dongjun');
 const puyang=page.locator('.city-information[data-inspected-city=dongjun]');
 await expect(puyang).toBeVisible();
 await expect(page.locator('#dialog-title')).toContainText('濮陽');
 await expect(puyang.locator('p.small').filter({hasText:/地形/})).toContainText('普通城');
 await page.locator('#dialog-language').selectOption('ja');
 await expect(puyang.locator('p.small').filter({hasText:/地形/})).toContainText('通常都市');
 await historyScreenshot(page,testInfo,'qiao-dated-scale-puyang-normal-ja');
 await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});

test('Jiangxia Changsha offers distinct inland water and land routes through real WASM and saved commands',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 await expect(page.locator('#world-map [data-river-route]')).not.toHaveCount(0);
 await expect(page.locator('#world-map [data-regional-road="jiangxia-changsha"]')).not.toHaveCount(0);
 await page.locator('input[name=faction][value=wu]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await page.locator('#city-jump').selectOption('jiangxia');
 await expect.poll(()=>page.evaluate(()=>MarchCore.status.engine)).toBe('wasm');
 const exportSave=async()=>{
  const download=page.waitForEvent('download');await page.locator('#save').click();
  return readFile(await(await download).path(),'utf8');
 };
 const initial=JSON.parse(await exportSave());
 await clickCityCommand(page,'transfer');
 await expect(page.locator('#transfer-city')).toBeVisible();
 await page.locator('#transfer-city').selectOption('changsha');
 const select=page.locator('#route-mode'),river=select.locator('option[data-route-kind=river]');
 await expect(river).toHaveCount(1);
 await expect(select.locator('option[data-route-kind=land]')).toHaveCount(1);
 await expect(select.locator('option')).toHaveCount(2);
 const mode=await river.getAttribute('value');
 await select.selectOption(mode);
 await expect(page.locator('#transfer-estimate .river-flow-info')).toBeVisible();
 await expect(page.locator('#transfer-estimate .river-flow-info')).toContainText('逆流',{useInnerText:true});
 await expect(page.locator('#transfer-estimate .river-flow-info')).toContainText('20',{useInnerText:true});
 await expect(page.locator('#transfer-estimate .river-flow-info')).toContainText('22.5',{useInnerText:true});
 await expect(page.locator('#transfer-estimate .route-risks')).toHaveCount(0);
 const officer=page.locator('input[name=transfer-officer]:enabled').first();
 const ident=await officer.getAttribute('value');await officer.check();
 await page.locator('#dialog-language').selectOption('ja');
 await expect(select).toHaveValue(mode);
 await expect(page.locator('#transfer-estimate .river-flow-info')).toContainText('上り',{useInnerText:true});
 await expect(river).toContainText('内陸水路');
 await historyScreenshot(page,testInfo,'river-upstream-select-ja');
 await page.locator('#confirm-transfer').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const departing=await exportSave(),saved=JSON.parse(departing);
 const column=saved.state.extension.travel.marches.find(row=>row.source==='jiangxia'&&row.target==='changsha');
 expect(column).toBeTruthy();expect(column.officers.map(String)).toEqual([ident]);
 expect(column.quote.modes).toEqual(['river']);expect(column.risks).toEqual([]);
 expect(column.quote.routes[0].flow).toBe('upstream');
 expect(column.quote.routes[0].hazard).toBeNull();
 const riverSegments=column.quote.routes[0].river_segments;
 expect(riverSegments[0].speed_km_per_day).toBe(20);expect(riverSegments.length).toBeGreaterThan(1);
 expect(riverSegments.slice(1).every(row=>row.speed_key==='xiang'&&row.speed_km_per_day===22.5)).toBe(true);
 expect(new Set(riverSegments.map(row=>row.reach_id)).size).toBe(riverSegments.length);
 expect(saved.state.rng).toEqual(initial.state.rng);
 expect(saved.state.officers[ident].troops).toBe(initial.state.officers[ident].troops);
 await page.reload();await enterScenarioMenu(page);
 await page.locator('#load').click();await page.locator('#load-local').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 expect(await exportSave()).toBe(departing);
 await expect(page.locator('#world-map [data-river-route]')).not.toHaveCount(0);
 await historyScreenshot(page,testInfo,'river-march-save-reloaded');
 await page.locator('#city-jump').selectOption('jiangxia');
 for(let step=0;step<3;step++)await page.locator('#map-zoom-in').click();
 const directory=process.env.TK2_HISTORY_SCREENSHOTS;
 if(directory)await mkdir(directory,{recursive:true});
 await page.locator('#world-map').screenshot({path:directory?
  join(directory,`${testInfo.project.name}-river-land-route-map.png`):testInfo.outputPath('river-land-route-map.png')});
 expect(errors.get(page)).toEqual([]);
});

test('scenario totals and DLC labels stay bilingual while island history remains neutral',async({page},testInfo)=>{
 await opening(page);
 const select=page.locator('#scenario'),counter=page.locator('#scenario-count');
 await expect(select.locator('option')).toHaveCount(29);
 await expect(select.locator('optgroup')).toHaveCount(2);
 await expect(counter).toHaveAttribute('data-scenario-count','29');
 await expect(counter).toContainText(/史實\s*23/,{useInnerText:true});
 await expect(counter).toContainText(/假想\s*6/,{useInnerText:true});
 await expect(select.locator('option[data-scenario-dlc]')).toHaveCount(7);
 const dlcIds=['mainland198-03','mainland202-06','mainland211-07-tongguan','mainland215-08'];
 for(const id of dlcIds){
  await expect(select.locator(`option[value="${id}"][data-scenario-dlc]`)).toContainText('DLC');
  await expect(select.locator(`optgroup[label="史實"] option[value="${id}"]`)).toHaveCount(1);
 }
 await expect(page.locator('#scenario-version-warning')).toHaveCount(0);
 await select.selectOption('mainland202-06');
 await page.locator('#utility-menu summary').click();
 await page.locator('#language').selectOption('ja');
 await expect(select).toHaveValue('mainland202-06');
 await expect(counter).toContainText(/史実\s*23/,{useInnerText:true});
 await expect(counter).toContainText(/仮想\s*6/,{useInnerText:true});
 await expect(select.locator('optgroup')).toHaveCount(2);
 await expect(select.locator('option[data-scenario-dlc]')).toHaveCount(7);
 for(const id of dlcIds)await expect(select.locator(`option[value="${id}"][data-scenario-dlc]`)).toContainText('DLC');
 await page.locator('#language').selectOption('zh-Hant');
 await page.locator('#utility-menu summary').click();
 await select.selectOption('mainland217-07');
 for(const id of ['zhuya','yizhou']){
  const marker=page.locator(`#world-map .city-hit[data-city="${id}"]`);
  await expect(marker).toHaveAttribute('data-owner','neutral');
  await expect(marker).toHaveAttribute('aria-label',/島嶼.*中立/);
  await page.locator('#city-jump').selectOption(id);
  const info=page.locator(`.city-information[data-inspected-city="${id}"]`);
  await expect(info).toBeVisible();
  await expect(info.locator('.city-information-owner')).toContainText(/島嶼.*中立/,{useInnerText:true});
  await expect(info.locator('.city-information-owner')).not.toContainText('漢郡',{useInnerText:true});
  const island=info.locator(`[data-island-status="${id}"]`);
  await expect(island).toContainText('中立',{useInnerText:true});
  await expect(island).toContainText(/遠征|渡海/,{useInnerText:true});
  for(const date of id==='zhuya'?['239年','242年7月']:['230年1月','231年2月'])
   await expect(island).toContainText(date,{useInnerText:true});
  const history=info.locator('.city-history');
  await history.locator(':scope > summary').click();
  await expect(history.locator('a[href^="https://"]')).not.toHaveCount(0);
  await expect(history).toContainText(id==='zhuya'?/孫權|孫吳|聶友|陸凱/:/孫權|孫吳|衛溫/,{useInnerText:true});
  await expect(history).toContainText(/中立|持續|常設|統治|管轄/,{useInnerText:true});
  await historyScreenshot(page,testInfo,`${id}-historical-neutral-tc`);
  await page.locator('#dialog-language').selectOption('ja');
  await expect(info.locator('.city-information-owner')).toContainText('中立',{useInnerText:true});
  await expect(info.locator('.city-information-owner')).not.toContainText('漢郡',{useInnerText:true});
  await expect(island).toContainText('中立',{useInnerText:true});
  await expect(island).toContainText(/遠征|渡海/,{useInnerText:true});
  for(const date of id==='zhuya'?['239年','242年7月']:['230年1月','231年2月'])
   await expect(island).toContainText(date,{useInnerText:true});
  await historyScreenshot(page,testInfo,`${id}-historical-neutral-ja`);
  await page.locator('#dialog-language').selectOption('zh-Hant');
  await closeDialog(page);
 }
 expect(errors.get(page)).toEqual([]);
});

test('a stale local API menu warns without restarting or changing its campaign',async({page,context},testInfo)=>{
 const api=[];
 await page.exposeFunction('__recordScenarioApi',row=>api.push(row));
 // Entry scripts carry a content hash query; match their pathname so this
 // old-API fixture still wraps the actual shipped client.
 await context.route(url=>url.pathname.endsWith('/app.js'),async route=>{
  const response=await route.fetch();
  const prefix=`'use strict';\n(() => {
   const original=window.fetch.bind(window);
   const excluded=new Set(['mainland198-03','mainland202-06','mainland211-07-tongguan','mainland215-08']);
   window.fetch=async function(input,settings={}){
    const result=await original(input,settings);
    const path=typeof input==='string'?input:new URL(input.url,location.href).pathname;
    if(path.startsWith('/api/'))await window.__recordScenarioApi({path,method:settings.method||'GET'});
    if(path!=='/api/state')return result;
    const value=await result.clone().json(),catalog=value.static_catalog||value.catalog;
    if(Array.isArray(catalog?.scenarios))catalog.scenarios=catalog.scenarios.filter(row=>!excluded.has(row.id));
    return new Response(JSON.stringify(value),{status:result.status,headers:result.headers});
   };
  })();\n`;
  await route.fulfill({response,body:prefix+await response.text()});
 });
 await opening(page);
 const readState=()=>page.evaluate(async()=>{
  const response=await fetch('/api/state');
  const value=await response.json();
  const state=value.view||value;
  return {game:state.game,revision:state.revision};
 });
 const before=await readState();
 const select=page.locator('#scenario'),warning=page.locator('#scenario-version-warning');
 await expect(select.locator('option')).toHaveCount(25);
 await expect(select.locator('optgroup')).toHaveCount(2);
 await expect(page.locator('#scenario-count')).toHaveAttribute('data-scenario-count','25');
 await expect(warning).toBeVisible();
 await expect(warning).toContainText('目前服務仍載入舊版25篇劇本',{useInnerText:true});
 await expect(warning).toContainText('本頁版本應有29篇',{useInnerText:true});
 await expect(warning).toContainText('請先儲存進度',{useInnerText:true});
 const link=warning.locator('a[data-update-game]');
 await expect(link).toHaveAttribute('href','https://kai987.github.io/Three-Kingdoms2-King-mainland/');
 await historyScreenshot(page,testInfo,'stale-25-api-warning-tc');
 await page.locator('#utility-menu summary').click();
 await page.locator('#language').selectOption('ja');
 await expect(warning).toBeVisible();
 await expect(warning).toContainText(/ローカル|旧版|古い/,{useInnerText:true});
 await expect(select.locator('option')).toHaveCount(25);
 await expect(select.locator('optgroup')).toHaveCount(2);
 await expect(link).toHaveAttribute('href','https://kai987.github.io/Three-Kingdoms2-King-mainland/');
 await page.locator('#utility-menu summary').click();
 await historyScreenshot(page,testInfo,'stale-25-api-warning-ja');
 expect(await readState()).toEqual(before);
 expect(before.game).toBeNull();
 expect(api.filter(row=>row.method!=='GET')).toEqual([]);
 expect(api.some(row=>['/api/command','/api/load'].includes(row.path))).toBe(false);
 await expect(page.locator('#begin')).toBeEnabled();
 expect(errors.get(page)).toEqual([]);
});

test('all 29 real Worker openings keep preview and live initial health and faction-scoped loyalty aligned',async({page},testInfo)=>{
 test.setTimeout(600_000);
 const people=JSON.parse(await readFile(new URL('../game/config/campaigns/people.json',import.meta.url),'utf8')).people;
 const known=[['san14-candidate-0952',78,99],['san14-candidate-0521',82,96],
  ['san14-candidate-0656',99,44],['san14-candidate-0147',97,94]];
 for(const[pid,health,virtue]of known){
  expect(people[pid].initialization.health).toBe(health);
  expect(people[pid].profile.virtue).toBe(virtue);
 }
 const relations=JSON.parse(await readFile(new URL('../game/config/references/officer-relations-v1.json',import.meta.url),'utf8'));
 const loyalty=(person,owner,ruler,catalog,pid)=>{
  if(ruler)return 100;if(!owner)return 0;
  const baseline=Number.isInteger(person.initialization.source_loyalty?.value)&&person.initialization.source_loyalty.faction_ids.includes(owner)?person.initialization.source_loyalty.value:80;
  const leader=catalog.people.find(row=>row.runtime_id===catalog.faction_rulers[owner])?.person_id;
  const active=row=>row.ruler_id===leader&&row.person_id===pid&&(row.start_year??0)<=catalog.start_year&&(row.end_year??9999)>=catalog.start_year;
  const floors=relations.exceptions.some(active)?[]:relations.records.filter(active).map(row=>row.floor);
  return Math.max(baseline,...floors);
 };
 await opening(page);
 const availableScenarios=await page.locator('#scenario option').evaluateAll(rows=>rows.map(row=>row.value));
 expect(availableScenarios).toHaveLength(29);
 const scenarios=browserScopes.selectScenarioIds(availableScenarios,browserScope);
 await testInfo.attach('opening-scenario-scope',{body:Buffer.from(JSON.stringify({full:browserScope.full,scenario_ids:scenarios},null,2)),contentType:'application/json'});
 let checkedServing=0,checkedFree=0,expectedServing=0,expectedFree=0;
 for(const scenario of scenarios){
  const catalog=JSON.parse(await readFile(new URL(`../game/data/campaigns/${scenario.slice('mainland'.length)}.json`,import.meta.url),'utf8'));
  expect(catalog.id).toBe(scenario);
  const servingPeople=catalog.initial_officers.map(row=>row.person_id).sort(),freePeople=catalog.initial_free_officers.map(row=>row.person_id).sort();
  expectedServing+=servingPeople.length;expectedFree+=freePeople.length;
  await page.locator('#scenario').selectOption(scenario);
  const cities=await page.locator('#city-jump option').evaluateAll(rows=>rows.map(row=>row.value));
  // Read-only previews are served by the shipped Worker. They neither create a
  // campaign nor consume RNG; new campaigns below use only visible controls.
  const previews=await page.evaluate(async({scenario,cities})=>{
   const values=[];
   for(const city of cities){
    const response=await fetch('/api/city-preview?'+new URLSearchParams({scenario,city}));
    if(!response.ok)throw new Error(`Opening preview failed: ${scenario}/${city}`);
    values.push((await response.json()).city);
   }
   return values;
  },{scenario,cities});
  for(const city of previews)for(const officer of city.officers){
   const person=people[officer.person_id];
   assert.equal(officer.health,person.initialization.health,`${scenario}/${officer.person_id} preview health`);
   assert.equal(officer.loyalty,loyalty(person,city.owner,officer.is_ruler,catalog,officer.person_id),`${scenario}/${officer.person_id} preview loyalty`);
   assert.equal(officer.virtue,person.profile.virtue,`${scenario}/${officer.person_id} preview virtue`);
  }
  const addedRuler={
   'mainland188-06':['song_jian','historical-song-jian','longxi'],
   'mainland225-07':['nanman','san14-candidate-0845','jianning'],
   'mainland263-05':['lu_xing','historical-lu-xing','jiaozhi'],
   'mainland238-01':['gongsun','san14-candidate-0262','liaodong']
  }[scenario];
  for(const faction of catalog.factions.filter(row=>!row.available_from&&/[势勢]力/.test(row.name))){
   const label=page.locator(`.faction-choice:has(input[value="${faction.id}"]) .faction-choice-heading>span`).first();
   const captain=await page.evaluate(name=>GameI18n.t(name),faction.captain);
   await expect(label).toHaveText(captain);
  }
  const representative=previews.find(city=>city.id===addedRuler?.[2])||previews.find(city=>city.officers.length);
  expect(representative).toBeTruthy();
  await page.locator('#city-jump').selectOption(representative.id);
  const info=page.locator(`.city-information[data-inspected-city="${representative.id}"]`);
  await expect(info).toHaveAttribute('data-information-mode','preview');
  const first=representative.officers[0],row=info.locator('.roster-table tbody tr').first();
  await expect(row.locator('td').nth(5)).toHaveText(first.is_ruler?'--':String(first.loyalty));
  await expect(row.locator('td').nth(7)).toHaveText(String(first.health));
  await closeDialog(page);
  if(addedRuler){
   const[side,personId]=addedRuler;
   await page.locator(`input[name=faction][value="${side}"]`).check();
   const portrait=page.locator('#setup-summary [data-portrait-person]');
   await expect(portrait).toHaveAttribute('data-portrait-person',personId);
   await expect(portrait).toHaveAttribute('data-portrait-name',catalog.factions.find(row=>row.id===side).captain);
   await expect.poll(()=>portrait.locator('img').evaluate(image=>image.complete&&image.naturalWidth===128&&image.naturalHeight===160)).toBe(true);
   await page.locator('#utility-menu summary').click();await page.locator('#language').selectOption('ja');
   await expect(portrait).toHaveAttribute('data-portrait-person',personId);
   const rulerName={song_jian:'宋建',nanman:'孟獲',lu_xing:'呂興',gongsun:'公孫淵'}[side];
   await expect(page.locator('#setup-summary .setup-summary-copy')).toContainText(rulerName);
   await page.locator('#utility-menu summary').click();
   await page.locator('#setup-summary').scrollIntoViewIfNeeded();
   await historyScreenshot(page,testInfo,`${scenario}-ruler-and-faction`);
   await page.locator('#utility-menu summary').click();
   await page.locator('#language').selectOption('zh-Hant');await page.locator('#utility-menu summary').click();
  }
  await page.locator('#begin').click();
  await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
  await waitIdle(page);await dismissHistoryOpening(page);
  const download=page.waitForEvent('download');await page.locator('#save').click();
  const saved=JSON.parse(await readFile(await(await download).path(),'utf8'));
  expect(saved.scenario).toBe(scenario);
  if(addedRuler)expect(saved.state.player).toBe(addedRuler[0]);
  expect([saved.state.year,saved.state.month,saved.state.day]).toEqual([catalog.start_year,catalog.start_month,1]);
  await expect(page.locator('#map-date')).toHaveAttribute('datetime',`${String(catalog.start_year).padStart(4,'0')}-${String(catalog.start_month).padStart(2,'0')}-01`);
  expect(Object.keys(saved.state.cities).sort()).toEqual([...catalog.active_cities].sort());
  const mapOwners=await page.locator('#world-map .city-hit').evaluateAll(nodes=>Object.fromEntries(nodes.map(node=>[node.dataset.city,node.dataset.owner])));
  for(const city of previews){
   const live=saved.state.cities[city.id],resources=catalog.initial_city_resources?.[city.id]||catalog.initial_resources;
   expect(live.owner).toBe(catalog.initial_owners[city.id]);
   for(const key of ['gold','grain','reserves'])expect(live[key],`${scenario}/${city.id} initial ${key}`).toBe(resources[key]);
   expect(live.roster.officer_ids.map(id=>saved.state.officers[id].person_id).sort()).toEqual(catalog.initial_officers.filter(officer=>officer.city===city.id).map(officer=>officer.person_id).sort());
   expect(mapOwners[city.id],`${scenario}/${city.id} visible map ownership`).toBe(live.owner);
  }
  const liveOfficers=Object.values(saved.state.officers);
  expect(liveOfficers.filter(officer=>officer.faction_id).map(officer=>officer.person_id).sort()).toEqual(servingPeople);
  expect(liveOfficers.filter(officer=>!officer.faction_id).map(officer=>officer.person_id).sort()).toEqual(freePeople);
  const leaders=new Set(Object.values(saved.state.extension.leaders).map(String));
  for(const[ident,officer]of Object.entries(saved.state.officers)){
   const person=people[officer.person_id];
   assert.ok(person,`${scenario}/${officer.person_id} historical identity`);
   assert.equal(officer.health,person.initialization.health,`${scenario}/${officer.person_id} live health`);
   assert.ok(officer.profile.health_max>=officer.health,`${scenario}/${officer.person_id} live health cap`);
   assert.equal(officer.loyalty,loyalty(person,officer.faction_id,leaders.has(ident),catalog,officer.person_id),`${scenario}/${officer.person_id} live loyalty`);
   assert.equal(officer.profile.virtue,person.profile.virtue,`${scenario}/${officer.person_id} live virtue`);
   if(officer.faction_id)checkedServing++;else checkedFree++;
  }
  for(const city of previews)for(const officer of city.officers){
   const live=saved.state.officers[officer.id];
   assert.equal(live.health,officer.health,`${scenario}/${officer.person_id} preview-live health`);
   assert.equal(live.loyalty,officer.loyalty,`${scenario}/${officer.person_id} preview-live loyalty`);
  }
  if(scenario==='mainland238-01'){
   // New retainers must be commandable people, with their bound 128×160
   // portrait in the actual detail dialog, not merely reference-file rows.
   const roster=saved.state.cities.liaodong.roster.officer_ids;
   expect(roster).toHaveLength(13);
   expect(Object.values(saved.state.officers).filter(row=>row.faction_id==='gongsun')).toHaveLength(15);
   for(const pid of ['historical-wang-jian-liaodong','historical-gongsun-xiu','historical-bi-sheng']){
    const [officerId,officer]=Object.entries(saved.state.officers).find(([,row])=>row.person_id===pid);
    expect(officer.faction_id).toBe('gongsun');expect(roster).toContain(Number(officerId));
   }
   const [wangId,wang]=Object.entries(saved.state.officers).find(([,row])=>row.person_id==='historical-wang-jian-liaodong');
   expect([wang.health,wang.profile.martial_strength,wang.profile.intellect,wang.profile.virtue,wang.loyalty]).toEqual([42,24,75,60,80]);
   const details=page.locator('#city-roster-'+wangId);
   if(!await details.isVisible())await page.locator('details:has(#city-roster-'+wangId+') > summary').click();
   await details.click();await expect(page.locator('#dialog-title')).toContainText('王建');
   const portrait=page.locator('#dialog [data-portrait-person="historical-wang-jian-liaodong"] img');
   await expect(portrait).toBeVisible();
   await expect.poll(()=>portrait.evaluate(image=>image.complete&&image.naturalWidth===128&&image.naturalHeight===160)).toBe(true);
   await historyScreenshot(page,testInfo,'238-new-retainer-original-wang-jian-tc');
   await page.locator('#dialog-language').selectOption('ja');
   await expect(portrait).toBeVisible();await historyScreenshot(page,testInfo,'238-new-retainer-original-wang-jian-ja');
   await closeDialog(page);
   const current=await page.evaluate(async()=>await(await fetch('/api/save')).json());
   expect(current).toEqual(saved);
  }
  await page.locator('#main-menu').click();
  await expect(page.locator('#begin')).toBeEnabled();
 }
 // Historical affiliation reviews legitimately change memberships; each live
 // Worker opening must retain the complete authored roster without omissions.
 expect(checkedServing).toBe(expectedServing);expect(checkedFree).toBe(expectedFree);
 await historyScreenshot(page,testInfo,'all-29-initial-stat-openings');
 expect(errors.get(page)).toEqual([]);
});

test('officer encyclopedia distinguishes initial body, remake cap and contextual loyalty in both languages',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=shu]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 await page.locator('#utility-menu summary').click();await page.locator('#library').click();
 await expect(page.locator('#dialog')).toContainText('魅力',{useInnerText:true});
 for(const[pid,health,sourceLoyalty,virtue]of[
  ['san14-candidate-0952',78,'--',99],['san14-candidate-0521',82,'--',96],
  ['san14-candidate-0656',99,'98',44],['san14-candidate-0147',97,'99',94]]){
  await page.locator('#library-search').fill(pid);
  await expect(page.locator('.person-detail')).toHaveCount(1);
  await page.locator('.person-detail').click();
  const summary=page.locator(`.person-initial-stats[data-initial-stat-source="${pid}"]:visible`);
  await expect(summary.locator('[data-initial-health]')).toHaveText(String(health));
  await expect(summary.locator('[data-source-loyalty]')).toHaveText(sourceLoyalty);
  await expect(page.locator('.person-profile-summary')).toContainText(new RegExp(`德\\s*${virtue}`),{useInnerText:true});
  await expect(summary).toContainText('不代表原版最大體力',{useInnerText:true});
  await expect(summary).toContainText('同勢力移動及讀檔不會重置',{useInnerText:true});
  if(pid==='san14-candidate-0952')await expect(summary.locator('[data-current-loyalty]')).toHaveText('--');
  await page.locator('#dialog-language').selectOption('ja');
  await expect(summary.locator('[data-initial-health]')).toHaveText(String(health));
  await expect(summary.locator('[data-source-loyalty]')).toHaveText(sourceLoyalty);
  await expect(summary).toContainText('原作の最大体力を表す値ではありません',{useInnerText:true});
  await expect(summary).toContainText('同勢力内の移動とロード',{useInnerText:true});
  if(pid==='san14-candidate-0952'){
   await expect(summary.locator('[data-current-loyalty]')).toHaveText('--');
   await historyScreenshot(page,testInfo,'liubei-original-body-loyalty-ja');
  }
  await page.locator('#dialog-language').selectOption('zh-Hant');
  await page.locator('#back-library').click();
 }
 await closeDialog(page);
 if(!await page.locator('#rules').isVisible())await page.locator('#utility-menu summary').click();
 await page.locator('#rules').click();
 const rules=page.locator('.rules-body');
 await expect(rules).toContainText('德採SAN14魅力',{useInnerText:true});
 await expect(rules).not.toContainText('德行記錄',{useInnerText:true});
 await historyScreenshot(page,testInfo,'rules-current-stat-policy-tc');
 await page.locator('#dialog-language').selectOption('ja');
 await expect(rules).toContainText('徳はSAN14の魅力に対応',{useInnerText:true});
 await expect(rules).not.toContainText(/德行記錄|徳行の記録/,{useInnerText:true});
 await historyScreenshot(page,testInfo,'rules-current-stat-policy-ja');
 await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});

test('successful recruitment preserves source initial body and applies dynamic personnel loyalty',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland184-02');
 await page.locator('input[name=faction][value=han]').check();
 await page.locator('.setup-options > summary').click();
 await page.locator('.seed-settings > summary').click();
 await page.locator('#seed').fill('2026');await page.locator('#begin').click();
 await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 const exportSave=async()=>{
  const download=page.waitForEvent('download');await page.locator('#save').click();
  return JSON.parse(await readFile(await(await download).path(),'utf8'));
 };
 const original=await exportSave(),target='463';
 expect(original.state.officers[target]).toMatchObject({person_id:'san14-candidate-0464',health:66,loyalty:0,faction_id:null});
 expect(original.state.officers[target].profile.health_max).toBe(80);
 await page.locator('#city-jump').selectOption('wei');
 await clickCityCommand(page,'recruit-officer');
 if(!await page.locator('#recruit-person').isVisible()){
  await page.locator('#world-map .city-hit[data-city=wei]').focus();await page.keyboard.press('Enter');
 }
 await expect(page.locator('#recruit-person')).toBeVisible();
 await page.locator('#recruit-actor').selectOption('931');
 await page.locator('#recruit-person').selectOption(target);
 await expect(page.locator('#recruit-person-summary')).toContainText('66',{useInnerText:true});
 await page.locator('#confirm-officer').click();await waitIdle(page);
 const events=page.locator('#event-dialog');
 if(await events.isVisible()){
  const skip=events.locator('[data-event-skip]');
  await (await skip.count()?skip:events.locator('[data-event-next]')).click();
  await expect(events).not.toBeVisible();
 }
 const recruited=await exportSave();
 expect(recruited.state.officers[target]).toMatchObject({health:66,loyalty:77,faction_id:'han'});
 expect(recruited.state.cities.wei.roster.officer_ids.map(String)).toContain(target);
 expect(recruited.state.officers[target].profile.health_max).toBe(80);
 await page.locator('#utility-menu summary').click();await page.locator('#library').click();
 await page.locator('#library-search').fill('san14-candidate-0464');
 await page.locator('.person-detail').click();
 const info=page.locator('.person-initial-stats:visible');
 await expect(info.locator('[data-initial-health]')).toHaveText('66');
 await expect(info.locator('[data-health-maximum]')).toHaveText('80');
 await expect(info.locator('[data-current-health]')).toHaveText('66');
 await expect(info.locator('[data-current-loyalty]')).toHaveText('77');
 await historyScreenshot(page,testInfo,'shenpei-recruited-body66-cap80-tc');
 await page.locator('#dialog-language').selectOption('ja');
 await expect(info.locator('[data-current-health]')).toHaveText('66');
 await expect(info.locator('[data-current-loyalty]')).toHaveText('77');
 await historyScreenshot(page,testInfo,'shenpei-recruited-body66-cap80-ja');
 await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});

test('treasury drafts, governor rewards, treasure sale and search use real saved state and illustrated events',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=shu]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#city-treasury')).toBeEnabled({timeout:90_000});
 await waitIdle(page);await dismissHistoryOpening(page);
 const save=()=>page.evaluate(async()=>{
  const response=await fetch('/api/save');if(!response.ok)throw new Error('Read-only treasury save failed');return response.json();
 });
 const currentTreasury=()=>page.evaluate(async()=>{
  const response=await fetch('/api/state'),value=await response.json();return (value.view||value).catalog.treasury;
 });
 const open=async city=>{
  await page.locator('#city-jump').selectOption(city);await clickCityCommand(page,'city-treasury');
  await expect(page.locator(`[data-treasury-dialog][data-treasury-city="${city}"]`)).toBeVisible();
 };
 const events=async name=>{
  await closeDialog(page);
  const event=page.locator('#event-dialog');await expect(event).toBeVisible();
  if(name==='sale')await assertOriginalEventArt(page,event,'treasure_sold');else await expect(event.locator('.event-treasure')).toBeVisible();
  await expect(event.locator('#event-title')).not.toBeEmpty();
  if(name==='reward'){
   for(let step=0;step<10&&!/賞賜武將|武将への褒美/.test(await event.locator('#event-title').innerText());step++){
    await event.locator('[data-event-next]').click();await expect(event).toBeVisible();
   }
   await expect(event.locator('#event-title')).toContainText(/賞賜武將|武将への褒美/);
  }
  await historyScreenshot(page,testInfo,`treasury-${name}-event`);
  if(name==='reward'){
   await event.locator('.event-treasure').scrollIntoViewIfNeeded();
   await expect(event.locator('.event-treasure')).toBeInViewport();
   await historyScreenshot(page,testInfo,'treasury-reward-event-viewport',{fullPage:false});
  }
  const skip=event.locator('[data-event-skip]');await (await skip.count()?skip:event.locator('[data-event-next]')).click();
  await expect(event).not.toBeVisible();
 };
 const home='shujun';await page.locator('#city-jump').selectOption(home);
 const initial=await save();
 expect(initial.state.extension.treasury.cities[home].treasure).toBe(6);
 await clickCityCommand(page,'city-treasury');
 await expect(page.locator('#dialog [data-city-treasure]')).toHaveText('6');
 await expect(page.locator('#dialog-title')).toBeInViewport();
 const dimensions=await page.locator('#dialog').evaluate(node=>({scrollTop:node.scrollTop,scrollHeight:node.scrollHeight,clientHeight:node.clientHeight,scrollWidth:node.scrollWidth,clientWidth:node.clientWidth,top:node.getBoundingClientRect().top,bottom:node.getBoundingClientRect().bottom,viewport:window.innerHeight}));
 expect(dimensions.scrollTop).toBe(0);expect(dimensions.top).toBeGreaterThanOrEqual(0);expect(dimensions.bottom).toBeLessThanOrEqual(dimensions.viewport+1);
 expect(dimensions.scrollHeight).toBeGreaterThan(dimensions.clientHeight);expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth+1);
 await historyScreenshot(page,testInfo,'treasury-opening-viewport',{fullPage:false});
 const target=await page.locator('#treasury-reward-officer').inputValue();
 expect(target).not.toBe('');
 expect(Object.values(initial.state.extension.leaders).map(String)).not.toContain(target);
 const selectedLabel=page.locator('#treasury-reward-officer option:checked');
 await expect(selectedLabel).toContainText(/兵.*武.*知.*德.*忠.*體/);
 await page.locator('#treasury-reward-amount').fill('999999');
 await expect(page.locator('#treasury-reward-amount')).toHaveValue('100');
 await page.locator('#treasury-reward-kind').selectOption('treasure');
 await page.locator('#treasury-reward-amount').fill('999999');
 await expect(page.locator('#treasury-reward-amount')).toHaveValue('1');
 await page.locator('#treasury-reward-max').click();
 await expect(page.locator('#treasury-reward-amount')).toHaveValue('1');
 await page.locator('#treasury-policy-enabled').check();
 await page.locator('#treasury-policy-budget').fill('201');
 await page.locator('#treasury-policy-prefer').selectOption('treasure');
 await page.locator('#dialog-language').selectOption('ja');
 await expect(page.locator('#dialog-title')).toContainText('宝と褒美');
 await expect(page.locator('#treasury-reward-amount')).toHaveValue('1');
 await expect(page.locator('#treasury-policy-budget')).toHaveValue('201');
 await expect(page.locator('#treasury-policy-enabled')).toBeChecked();
 expect(await save()).toEqual(initial,'Inventory inspection, max buttons and language/policy drafts must not change state or RNG');
 await historyScreenshot(page,testInfo,'treasury-drafts-ja');
 // A faction may reward its own governor. Assignment is separate from the
 // reward and must leave the city's and officer's action available.
 await page.locator('#treasury-governor').selectOption(target);
 await page.locator('#treasury-set-governor').click();await waitIdle(page);
 await expect(page.locator('[data-treasury-dialog]')).toBeVisible();
 await expect(page.locator('#treasury-policy-budget')).toHaveValue('201');
 const appointed=await save();
 expect(appointed.state.extension.treasury.cities[home]).toMatchObject({governor:Number(target),governor_mode:'manual',treasure:6});
 expect(appointed.state.cities[home].action_used).toBe(false);
 expect(appointed.state.rng).toEqual(initial.state.rng);
 await page.locator('#treasury-reward-officer').selectOption(target);
 const gain=Number(await page.locator('#treasury-reward-preview').getAttribute('data-gain'));
 const loyalty=Number(await page.locator('#treasury-reward-preview').getAttribute('data-loyalty'));
 expect(gain).toBeGreaterThan(0);expect(loyalty).toBeLessThanOrEqual(100);
 await page.locator('#treasury-reward').click();await waitIdle(page);
 await expect(page.locator('[data-treasury-dialog]')).toBeVisible();
 await expect(page.locator('#dialog [data-city-treasure]')).toHaveText('5');
 const rewarded=await save();
 expect(rewarded.state.extension.command_books.factions.shu.used).toBe(appointed.state.extension.command_books.factions.shu.used+1);
 if(loyalty<100)await expect(page.locator('#treasury-reward')).toBeEnabled();
 expect(rewarded.state.officers[target].loyalty).toBe(loyalty);
 expect(rewarded.state.officers[target].loyalty).toBe(initial.state.officers[target].loyalty+gain);
 expect(rewarded.state.officers[target].health).toBe(initial.state.officers[target].health);
 expect(rewarded.state.cities[home].gold).toBe(initial.state.cities[home].gold);
 expect(rewarded.state.cities[home].action_used).toBe(true);
 expect(rewarded.state.extension.officer_actions[target]).toBe(rewarded.state.turn);
 expect(rewarded.state.rng).toEqual(initial.state.rng,'A reward uses no RNG draw');
 await expect(page.locator('#treasury-policy-budget')).toHaveValue('201');
 await page.locator('#treasury-save-policy').click();await waitIdle(page);
 const policy=await save();
 expect(policy.state.extension.treasury.factions.shu).toMatchObject({enabled:true,target_loyalty:90,gold_budget:201,prefer:'treasure'});
 await historyScreenshot(page,testInfo,'treasury-self-governor-reward-ja');
 await events('reward');
 const beforeSale=await save(),saleRows=await currentTreasury();
 const saleCity=Object.keys(saleRows.cities).find(id=>id!==home&&beforeSale.state.cities[id].owner==='shu'&&saleRows.cities[id].can_sell);
 expect(saleCity).toBeTruthy();await open(saleCity);
 const maximum=await page.locator('#treasury-sell-amount').getAttribute('max');
 await page.locator('#treasury-sell-amount').fill('999999');
 await expect(page.locator('#treasury-sell-amount')).toHaveValue(maximum);
 await page.locator('#treasury-sell-max').click();
 await expect(page.locator('#treasury-sell-amount')).toHaveValue(maximum);
 await page.locator('#treasury-sell').click();await waitIdle(page);
 const sold=await save(),amount=Number(maximum);
 expect(sold.state.extension.treasury.cities[saleCity].treasure).toBe(beforeSale.state.extension.treasury.cities[saleCity].treasure-amount);
 expect(sold.state.cities[saleCity].gold).toBe(beforeSale.state.cities[saleCity].gold+amount*100);
 expect(sold.state.rng).toEqual(beforeSale.state.rng);
 await expect(page.locator('#treasury-sell')).toBeDisabled();await events('sale');
 const beforeSearch=await save(),searchRows=await currentTreasury();
 const searchCity=Object.keys(searchRows.cities).find(id=>beforeSearch.state.cities[id].owner==='shu'&&searchRows.cities[id].can_search);
 expect(searchCity).toBeTruthy();await open(searchCity);
 await expect(page.locator('#treasury-search-preview')).toContainText(/成功率/);
 await page.locator('#treasury-search').click();await waitIdle(page);
 const searched=await save(),found=searched.state.extension.treasury.cities[searchCity].treasure-beforeSearch.state.extension.treasury.cities[searchCity].treasure;
 expect([0,1]).toContain(found);
 expect(searched.state.cities[searchCity].gold).toBe(beforeSearch.state.cities[searchCity].gold-20);
 expect(searched.state.rng.draws).toBe(beforeSearch.state.rng.draws+1);
 expect(searched.state.extension.command_books.factions.shu.used).toBe(beforeSearch.state.extension.command_books.factions.shu.used+1);
 await expect(page.locator('#treasury-search')).toBeEnabled();await events('search');
 expect(errors.get(page)).toEqual([]);
});

test('manual treasure transport preserves cargo, rations and saved travel while automatic support is disabled',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=shu]').check();await page.locator('#begin').click();
 await expect(page.locator('#city-logistics')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);
 const state=()=>page.evaluate(async()=>{const r=await fetch('/api/save');if(!r.ok)throw new Error('Read-only convoy save failed');return r.json();});
 const source='shujun',target='bajun';await page.locator('#city-jump').selectOption(source);
 const before=await state();expect(before.state.extension.treasury.cities[source].treasure).toBe(6);expect(before.state.extension.treasury.cities[target].treasure).toBe(4);
 expect(before.state.extension.logistics.cities[source].policy.enabled).toBe(false);
 await clickCityCommand(page,'city-logistics');await expect(page.locator('[data-treasure-transport]')).toBeVisible();
 await expect(page.locator('#logistics-enabled')).not.toBeChecked();
 await page.locator('#treasure-transport-target').selectOption(target);
 const expectedTransport=await page.evaluate(async([source,target])=>{const response=await fetch('/api/state');if(!response.ok)throw new Error('Treasure transport quote unavailable');const body=await response.json(),view=body.view||body;return view.catalog.logistics.cities[source].treasure_transport.targets.find(row=>row.target===target);},[source,target]);
 expect(expectedTransport.can_dispatch).toBe(true);expect(expectedTransport.days).toBeGreaterThan(0);
 await page.locator('#treasure-transport-amount').fill('999999');await expect(page.locator('#treasure-transport-amount')).toHaveValue('6');
 await page.locator('#treasure-transport-max').click();await expect(page.locator('#treasure-transport-amount')).toHaveValue('6');
 await page.locator('#dialog-language').selectOption('ja');await expect(page.locator('#treasure-transport-amount')).toHaveValue('6');
 expect(await state()).toEqual(before,'A manual shipment preview and language change cannot move treasure or consume RNG');
 await expect(page.locator('#dispatch-treasure')).toBeEnabled();await page.locator('#dispatch-treasure').click();await waitIdle(page);
 const departing=await state(),convoy=departing.state.extension.logistics.convoys.find(row=>row.source===source&&row.target===target);
 expect(convoy).toMatchObject({owner:'shu',status:'outbound',officers:[595],cargo:{gold:0,grain:0,reserves:0,treasure:6},delivery_done:false});
 const quote=convoy.journeys[0].quote;
 expect(quote.days).toBe(expectedTransport.days);expect(quote.modes).toEqual(expectedTransport.modes);
 let stageDays=0;for(let index=0;index<quote.routes.length;index++){stageDays+=quote.routes[index].days;if(before.state.cities[quote.path[index+1]]?.owner==='shu')break;}
 const units=convoy.officers.reduce((sum,id)=>sum+before.state.officers[id].troops+100,0),rations=Math.ceil(units*stageDays/1000);
 expect(rations).toBe(expectedTransport.cost_grain);
 expect(convoy.journeys[0].supply).toMatchObject({loaded:rations,consumed:0,remaining:rations});
 expect(departing.state.cities[source].grain).toBe(before.state.cities[source].grain-rations);
 expect(departing.state.extension.treasury.cities[source].treasure).toBe(0);
 expect(departing.state.extension.treasury.cities[target].treasure).toBe(4,'Cargo is not delivered instantly');
 expect(departing.state.rng).toEqual(before.state.rng,'This safe land dispatch has no weather RNG draw');
 expect(departing.state.extension.logistics.cities[source].policy.enabled).toBe(false);
 await historyScreenshot(page,testInfo,'treasure-convoy-departure-ja');
 await closeDialog(page);
 const event=page.locator('#event-dialog');await expect(event).toBeVisible();await assertOriginalEventArt(page,event,'transport_departed');
 await expect(event.locator('#event-description')).toContainText(/宝6|寶6/,{useInnerText:true});
 const skip=event.locator('[data-event-skip]');await (await skip.count()?skip:event.locator('[data-event-next]')).click();await expect(event).not.toBeVisible();
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#load-local').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const restored=page.waitForEvent('download');await page.locator('#save').click();expect(await readFile(await(await restored).path(),'utf8')).toBe(raw);
 await page.locator('#city-jump').selectOption(source);await clickCityCommand(page,'city-logistics');
 await expect(page.locator('#dialog')).toContainText(/宝\s*6|寶\s*6/,{useInnerText:true});
 await historyScreenshot(page,testInfo,'treasure-convoy-restored-ja');await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});

test('facility visits, trade, study, equipment, prevention and town development share bounded real actions and saves',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=shu]').check();await page.locator('#begin').click();
 await expect(page.locator('#city-facilities')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);
 await page.locator('#city-command-tab-town').scrollIntoViewIfNeeded();
 await page.locator('#city-command-tab-town').click();
 await historyScreenshot(page,testInfo,'original-command-groups',{fullPage:false});
 const read=()=>page.evaluate(async()=>{
  const saved=await fetch('/api/save'),shown=await fetch('/api/state');
  if(!saved.ok||!shown.ok)throw new Error('Read-only facility view failed');
  const value=await shown.json();return {save:await saved.json(),facilities:(value.view||value).catalog.facilities};
 });
 const chooseCity=(snapshot,predicate)=>Object.entries(snapshot.facilities.cities).find(([id,row])=>row.owner==='shu'&&row.can_act&&predicate(row,snapshot.save.state.cities[id]));
 const open=async id=>{await page.locator('#city-jump').selectOption(id);await clickCityCommand(page,'city-facilities');await expect(page.locator(`[data-facilities-dialog][data-facilities-city="${id}"]`)).toBeVisible();};
 const events=async(label,kind)=>{
  await closeDialog(page);const modal=page.locator('#event-dialog');await expect(modal).toBeVisible();
  await expect(modal.locator('#event-title')).not.toBeEmpty();
  if(['officer_treated','officer_studied','grain_traded','equipment_bought'].includes(kind))await assertOriginalEventArt(page,modal,kind);else{await expect(modal.locator('.event-map')).toBeVisible();await expect(modal.locator('.event-facility')).toBeVisible();}
  const latest=await read();expect(latest.save.state.extension.events.items.some(row=>row.kind===kind)).toBe(true);
  await historyScreenshot(page,testInfo,`facility-${label}-event`,{fullPage:false});
  const skip=modal.locator('[data-event-skip]');await (await skip.count()?skip:modal.locator('[data-event-next]')).click();await expect(modal).not.toBeVisible();
 };
 let before=await read();const clinic=chooseCity(before,row=>row.town===1&&row.patients.some(p=>p.can_treat))||chooseCity(before,row=>row.patients.some(p=>p.can_treat));
 expect(clinic).toBeTruthy();const basic=chooseCity(before,row=>row.town===1);expect(basic).toBeTruthy();await open(basic[0]);
 for(const service of ['school','armory']){
  const tab=page.locator('#facility-tab-'+service);await expect(tab).toBeDisabled();await expect(tab).toHaveAttribute('aria-describedby','facility-unavailable-'+service);await expect(page.locator('#facility-unavailable-'+service)).toContainText(/本城尚未設置|この都市には未設置/);
 }
 await assertFacilityFooter(page,'facility-treat');await page.locator('.facility-footer [data-cancel]').focus();await page.keyboard.press('Enter');await expect(page.locator('#dialog')).not.toBeVisible();await expect(page.locator('#city-facilities')).toBeFocused();
 expect((await read()).save).toEqual(before.save,'Disabled tabs and cancelling cannot spend resources or draw RNG');await open(clinic[0]);
 await expect(page.locator('#dialog-title')).toBeInViewport();
 const dimensions=await page.locator('#dialog').evaluate(node=>({top:node.getBoundingClientRect().top,bottom:node.getBoundingClientRect().bottom,viewport:innerHeight,scrollTop:node.scrollTop,scrollWidth:node.scrollWidth,clientWidth:node.clientWidth}));
 expect(dimensions.top).toBeGreaterThanOrEqual(0);expect(dimensions.bottom).toBeLessThanOrEqual(dimensions.viewport+1);expect(dimensions.scrollTop).toBe(0);expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth+1);
 await expect(page.locator('.facility-service-tabs [role=tab]')).toHaveCount(4);await expect(page.locator('#facility-develop')).toHaveCount(0);await expect(page.locator('#facility-prevent')).toHaveCount(0);
 await assertFacilityFooter(page,'facility-treat');await page.locator('.facility-footer [data-cancel]').focus();await page.keyboard.press('Tab');await expect(page.locator('#facility-treat')).toBeFocused();await page.keyboard.press('Shift+Tab');await expect(page.locator('.facility-footer [data-cancel]')).toBeFocused();
 await historyScreenshot(page,testInfo,'facilities-opening-viewport',{fullPage:false});
 const patient=await page.locator('#facility-patient').inputValue(),actor=await page.locator('#facility-actor').inputValue(),clinicQuote=clinic[1].patients.find(row=>String(row.id)===patient);
 expect(clinicQuote.can_treat).toBe(true);await expect(page.locator('#facility-patient option:checked')).toContainText(/兵.*武.*知.*德.*忠.*體/);
 await page.locator('#facility-civic-entry').click();await page.locator('#facility-civic-policy').click();await page.locator('.facility-policy > summary').click();await page.locator('#facility-policy-gold_budget').fill('321');
 await page.locator('#facility-policy-grain_floor').fill('5000');await page.locator('#facility-policy-grain_target').fill('1');
 await expect(page.locator('#facility-policy-grain_target')).toHaveValue('5000');
 await page.locator('#dialog-language').selectOption('ja');await expect(page.locator('#dialog-title')).toContainText('町と都市');
 await expect(page.locator('#facility-policy-gold_budget')).toHaveValue('321');await expect(page.locator('.facility-policy')).toHaveAttribute('open','');
 expect((await read()).save).toEqual(before.save,'Facility inspection, policy drafts and language must not spend or draw RNG');
 await page.locator('#facility-tab-hospital').click();await assertFacilityFooter(page,'facility-treat');await page.locator('#facility-treat').focus();await page.keyboard.press('Enter');await waitIdle(page);let after=await read();
 expect(after.save.state.cities[clinic[0]].gold).toBe(before.save.state.cities[clinic[0]].gold-clinicQuote.gold);
 expect(after.save.state.officers[patient].health).toBeGreaterThanOrEqual(clinicQuote.after_min);expect(after.save.state.officers[patient].health).toBeLessThanOrEqual(clinicQuote.after_max);
 expect(after.save.state.rng.draws).toBe(before.save.state.rng.draws+1);
 expect(after.save.state.cities[clinic[0]].action_used).toBe(true);expect(after.save.state.extension.officer_actions[actor]).toBe(after.save.state.turn);
 expect(after.save.state.extension.command_books.factions.shu.used).toBe(before.save.state.extension.command_books.factions.shu.used+1);await page.locator('#facility-civic-entry').click();await page.locator('#facility-civic-prevention').click();await expect(page.locator('.facility-footer [data-command-book-cost]')).toHaveAttribute('data-command-book-cost','1');await page.locator('#facility-civic-policy').click();await expect(page.locator('#facility-policy-gold_budget')).toHaveValue('321');
 await page.locator('#facility-save-policy').click();await waitIdle(page);const configured=await read();
 expect(configured.save.state.extension.facilities.factions.shu).toMatchObject({enabled:false,gold_budget:321,grain_floor:5000,grain_target:5000});
 expect(configured.save.state.rng).toEqual(after.save.state.rng);await events('clinic-ja','officer_treated');
 before=await read();const market=chooseCity(before,row=>row.town===1&&row.trade.buy.max_batches>1&&row.eligible_actors.length>1)||chooseCity(before,row=>row.trade.buy.max_batches>1&&row.eligible_actors.length>1);expect(market).toBeTruthy();await open(market[0]);
 await page.locator('#facility-tab-market').click();await page.locator('#facility-trade-batches').fill('999999999');
 await expect(page.locator('#facility-trade-batches')).toHaveValue(String(market[1].trade.buy.max_batches));await page.locator('#facility-trade-max').click();
 const batches=Math.min(2,market[1].trade.buy.max_batches);await page.locator('#facility-trade-batches').fill(String(batches));
 const marketActor=await page.locator('#facility-actor').inputValue(),visitorChoice=await page.locator('#facility-actor option').evaluateAll((options,current)=>options.map(option=>({value:option.value,name:option.textContent.split(' · ')[0]})).find(option=>option.value!==current),marketActor);
 expect(visitorChoice).toBeTruthy();const visitorPerson=before.save.state.officers[visitorChoice.value].person_id;
 await page.locator('#facility-actor').selectOption(visitorChoice.value);await expect(page.locator('#facility-actor')).toBeFocused();await expect(page.locator('.facility-visitor strong')).toHaveText(visitorChoice.name);await expect(page.locator('.facility-visitor [data-portrait-person]')).toHaveAttribute('data-portrait-person',visitorPerson);await expect(page.locator('#facility-trade-batches')).toHaveValue(String(batches));expect((await read()).save).toEqual(before.save,'Changing the market actor refreshes the visitor without spending or altering RNG');
 await page.locator('#dialog-language').selectOption('zh-Hant');
 await expect(page.locator('#facility-trade-batches')).toHaveValue(String(batches));expect((await read()).save).toEqual(before.save);
 await assertFacilityFooter(page,'facility-trade');await page.locator('#facility-trade').click();await waitIdle(page);after=await read();
 expect(after.save.state.cities[market[0]].gold).toBe(before.save.state.cities[market[0]].gold-batches*market[1].trade.buy.rate);
 expect(after.save.state.cities[market[0]].grain).toBe(before.save.state.cities[market[0]].grain+batches*market[1].trade.buy.batch_grain);expect(after.save.state.rng).toEqual(before.save.state.rng);
 expect(after.save.state.extension.command_books.factions.shu.used).toBe(before.save.state.extension.command_books.factions.shu.used+1);await events('market-tc','grain_traded');
 before=await read();const school=chooseCity(before,row=>row.services.includes('school')&&row.students.some(s=>s.can_study));expect(school).toBeTruthy();await open(school[0]);await page.locator('#facility-tab-school').click();
 const student=await page.locator('#facility-student').inputValue(),studyQuote=school[1].students.find(row=>String(row.id)===student);expect(studyQuote.can_study).toBe(true);
 await expect(page.locator('#facility-study-preview')).toContainText(String(studyQuote.gold));await assertFacilityFooter(page,'facility-study');await page.locator('#facility-study').click();await waitIdle(page);after=await read();
 const learned=after.save.state.officers[student].profile.intellect;
 expect(learned).toBeGreaterThanOrEqual(studyQuote.after_min);expect(learned).toBeLessThanOrEqual(studyQuote.after_max);
 expect(after.save.state.cities[school[0]].gold).toBe(before.save.state.cities[school[0]].gold-studyQuote.gold);expect(after.save.state.rng.draws).toBe(before.save.state.rng.draws+1);
 expect(after.save.state.extension.facilities.study[student]).toBe((before.save.state.extension.facilities.study[student]||0)+learned-studyQuote.before);
 expect(after.save.state.extension.command_books.factions.shu.used).toBe(before.save.state.extension.command_books.factions.shu.used+1);await events('school-tc','officer_studied');
 before=await read();const armory=chooseCity(before,row=>row.services.includes('armory')&&row.stock.weapon.some(item=>item.can_buy&&item.eligible_targets.length));expect(armory).toBeTruthy();await open(armory[0]);await page.locator('#facility-tab-armory').click();
 await page.locator('#facility-tab-armory').focus();
 for(const [service,action]of [['hospital','facility-treat'],['school','facility-study'],['market','facility-trade'],['armory','facility-equipment-buy']]){
  await page.keyboard.press('ArrowRight');await expect(page.locator('#facility-tab-'+service)).toBeFocused();await expect(page.locator('#facility-tab-'+service)).toHaveAttribute('aria-selected','true');await assertFacilityFooter(page,action);
 }
 await page.keyboard.press('End');await expect(page.locator('#facility-tab-market')).toBeFocused();await page.keyboard.press('Home');await expect(page.locator('#facility-tab-armory')).toBeFocused();
 expect((await read()).save).toEqual(before.save,'Four-tab keyboard navigation only updates the selected service');
 const item=armory[1].stock.weapon.find(item=>item.can_buy&&item.eligible_targets.length),recipient=String(item.eligible_targets[0]);
 await page.locator('#facility-equipment-officer').selectOption(recipient);await page.locator('#facility-equipment-item').selectOption(String(item.id));
 await expect(page.locator('#facility-equipment-buy')).toBeEnabled();await assertFacilityFooter(page,'facility-equipment-buy');await page.locator('#facility-equipment-buy').click();await waitIdle(page);after=await read();
 expect(after.save.state.officers[recipient].weapon_id).toBe(item.id);expect(after.save.state.cities[armory[0]].gold).toBe(before.save.state.cities[armory[0]].gold-item.price);expect(after.save.state.rng).toEqual(before.save.state.rng);
 expect(after.save.state.extension.command_books.factions.shu.used).toBe(before.save.state.extension.command_books.factions.shu.used+1);await events('equipment-tc','equipment_bought');
 before=await read();const prevention=chooseCity(before,row=>Object.values(row.prevention_quotes).some(q=>q.can_prevent));expect(prevention).toBeTruthy();await open(prevention[0]);await page.locator('#facility-civic-entry').click();await page.locator('#facility-civic-prevention').click();
 const engineer=await page.locator('#facility-actor').inputValue(),preventionQuote=prevention[1].prevention_quotes[engineer];expect(preventionQuote.can_prevent).toBe(true);
 await expect(page.locator('#facility-prevention-preview')).toContainText(String(preventionQuote.gold_min));await page.locator('#dialog-language').selectOption('ja');expect((await read()).save).toEqual(before.save);
 await page.locator('#facility-prevent').click();await waitIdle(page);after=await read();
 const protectedCity=after.save.state.extension.facilities.cities[prevention[0]],expense=before.save.state.cities[prevention[0]].gold-after.save.state.cities[prevention[0]].gold;
 expect(expense).toBeGreaterThanOrEqual(preventionQuote.gold_min);expect(expense).toBeLessThanOrEqual(preventionQuote.gold_max);
 expect(protectedCity.preparedness).toBeGreaterThanOrEqual(preventionQuote.preparedness_min);expect(protectedCity.preparedness).toBeLessThanOrEqual(preventionQuote.preparedness_max);
 expect(protectedCity.damage).toBeGreaterThanOrEqual(preventionQuote.damage_min);expect(protectedCity.damage).toBeLessThanOrEqual(preventionQuote.damage_max);expect(after.save.state.rng.draws).toBe(before.save.state.rng.draws+2);
 expect(after.save.state.extension.command_books.factions.shu.used).toBe(before.save.state.extension.command_books.factions.shu.used+1);await events('prevention-ja','prevention_improved');
 before=await read();const town=chooseCity(before,row=>row.develop.can_develop);expect(town).toBeTruthy();await open(town[0]);await page.locator('#facility-civic-entry').click();
 await page.locator('#facility-develop').click();await waitIdle(page);after=await read();
 expect(after.save.state.extension.facilities.cities[town[0]].town).toBe(town[1].develop.to_town);expect(after.save.state.cities[town[0]].gold).toBe(before.save.state.cities[town[0]].gold-town[1].develop.gold);expect(after.save.state.rng).toEqual(before.save.state.rng);
 expect(after.save.state.extension.command_books.factions.shu.used).toBe(before.save.state.extension.command_books.factions.shu.used+1);await expect(page.locator('#facility-tab-school')).toBeEnabled();await expect(page.locator('#facility-tab-armory')).toBeEnabled();await events('development-ja','town_developed');
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#load-local').click();await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const restored=page.waitForEvent('download');await page.locator('#save').click();expect(await readFile(await(await restored).path(),'utf8')).toBe(raw);
 const loaded=await read();expect(loaded.save.state.officers[student].profile.intellect).toBe(learned);expect(loaded.save.state.officers[recipient].weapon_id).toBe(item.id);
 expect(errors.get(page)).toEqual([]);
});

test('a natural August drought shows bilingual illustrated losses and preserves the actual soldier ledger',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=wei]').check();await page.locator('#begin').click();
 await expect(page.locator('#city-facilities')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);
 const read=()=>page.evaluate(async()=>{const a=await fetch('/api/save'),b=await fetch('/api/state');if(!a.ok||!b.ok)throw new Error('Read-only disaster state failed');const result=await b.json(),view=result.view||result;return {save:await a.json(),income:view.catalog.city_income};});
 const original=await read();expect(original.save.state.month).toBe(7);expect(original.save.state.player).toBe('wei');
 const dismiss=async()=>{const modal=page.locator('#event-dialog');if(await modal.isVisible()){const skip=modal.locator('[data-event-skip]');await (await skip.count()?skip:modal.locator('[data-event-next]')).click();await expect(modal).not.toBeVisible();}};
 let current=original,steps=0;
 for(;steps<60;steps++){
  current=await read();if(current.save.state.month>=8)break;
  await dismiss();const phase=current.save.state.phase;
  if(phase==='city')await page.locator('#end-turn').click();
  else if(phase==='ai')await page.locator('#run-ai').click();
  else if(phase==='arrivals')await page.locator('#process-arrivals').click();
  else if(phase==='battle'){
   await page.locator('#retreat').click();await expect(page.locator('#confirm-retreat')).toBeVisible();await page.locator('#confirm-retreat').click();
  }else if(phase==='result')await page.locator('#settle').click();
  else throw new Error('The natural drought campaign unexpectedly finished before August: '+phase);
  await waitIdle(page);
 }
 expect(steps).toBeLessThan(60);expect(current.save.state.year).toBe(217);expect(current.save.state.month).toBe(8);expect(current.save.state.day).toBe(1);
 const all=current.save.state.extension.events.items.filter(event=>event.kind==='city_disaster'&&event.year===217&&event.month===8),own=all.filter(event=>event.factions.includes('wei'));
 expect(own.length).toBeGreaterThan(0);expect(own.every(event=>event.details.disaster==='drought')).toBe(true);
 const unique=own.map(event=>event.city_ids[0]);expect(new Set(unique).size).toBe(unique.length);
 for(const event of own){
  const details=event.details,city=event.city_ids[0],actual=current.save.state.extension.facilities.cities[city];
  expect(details.gold).toBe(0);expect(details.grain).toBeGreaterThanOrEqual(0);expect(details.reserves).toBeGreaterThanOrEqual(0);
  expect(actual.preparedness).toBe(details.preparedness_after);expect(actual.damage).toBe(details.damage_after);expect(actual.damage).toBeGreaterThan(0);
  for(const resource of ['gold','grain','reserves'])expect(current.income[city][resource]).toBe(Math.floor(original.income[city][resource]*(100-actual.damage)/100));
 }
 const live=current.save.state,currentSoldiers=Object.values(live.cities).reduce((sum,c)=>sum+c.reserves,0)+Object.values(live.officers).reduce((sum,o)=>sum+o.troops,0)+(live.extension.logistics?.convoys||[]).reduce((sum,c)=>sum+c.cargo.reserves,0);
 expect(currentSoldiers+live.soldiers.lost).toBe(live.soldiers.initial+live.soldiers.recruited);
 expect(live.soldiers.lost).toBeGreaterThanOrEqual(all.reduce((sum,event)=>sum+event.details.reserves,0));
 expect(live.extension.facilities.last_disaster_month).toBe(217*12+8-1);
 const modal=page.locator('#event-dialog');await expect(modal).toBeVisible();
 for(let count=0;count<50&&!/城池災情|都市の災害/.test(await modal.locator('#event-title').innerText());count++){
  await modal.locator('[data-event-next]').click();await expect(modal).toBeVisible();
 }
 await expect(modal.locator('#event-title')).toContainText(/城池災情|都市の災害/);await expect(modal.locator('.event-facility')).toBeVisible();
 await expect(modal.locator('#event-description')).toContainText('旱災',{useInnerText:true});
 await expect(modal.locator('#event-description > p')).toHaveCount(own.length);
 await historyScreenshot(page,testInfo,'natural-drought-tc',{fullPage:false});
 await modal.locator('[data-language-picker]').selectOption('ja');await expect(modal.locator('#event-title')).toContainText('都市の災害');await expect(modal.locator('#event-description')).toContainText('干ばつ',{useInnerText:true});
 expect((await read()).save).toEqual(current.save,'Reading and translating a real disaster receipt never reapplies losses or draws RNG');
 await historyScreenshot(page,testInfo,'natural-drought-ja',{fullPage:false});
 const skip=modal.locator('[data-event-skip]');await (await skip.count()?skip:modal.locator('[data-event-next]')).click();await expect(modal).not.toBeVisible();
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#load-local').click();await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const restored=page.waitForEvent('download');await page.locator('#save').click();expect(await readFile(await(await restored).path(),'utf8')).toBe(raw);
 expect((await read()).save).toEqual(current.save,'Loading an August save cannot settle the same monthly drought twice');
 expect(errors.get(page)).toEqual([]);
});

test('actual equipment appears in city intelligence and person details with server weight previews, exclusive initial gear and saved replacements',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');await page.locator('input[name=faction][value=shu]').check();
 const preview=await page.evaluate(async()=>{const response=await fetch('/api/city-preview?'+new URLSearchParams({scenario:'mainland217-07',city:'shujun'}));if(!response.ok)throw new Error('Initial equipment preview failed');return (await response.json()).city;});
 const previewLiu=preview.officers.find(person=>person.person_id==='san14-candidate-0952');expect(previewLiu).toBeTruthy();expect(previewLiu.equipment.scope).toBe('initial');
 expect(previewLiu.equipment.weapon.name_tc).toContain('雙股劍');
 await page.locator('#city-jump').selectOption('shujun');const previewInfo=page.locator('.city-information[data-inspected-city=shujun]');await expect(previewInfo).toBeVisible();
 const previewGear=previewInfo.locator(`[data-officer-equipment="${previewLiu.id}"]:visible`);await expect(previewGear).toHaveAttribute('data-equipment-scope','initial');await expect(previewGear).toContainText(previewLiu.equipment.weapon.name_tc);await expect(previewGear).toContainText(previewLiu.equipment.armor.name_tc);await closeDialog(page);
 await page.locator('#begin').click();await expect(page.locator('#city-facilities')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);
 const read=()=>page.evaluate(async()=>{const a=await fetch('/api/save'),b=await fetch('/api/state');if(!a.ok||!b.ok)throw new Error('Equipment read-only state failed');const value=await b.json();return {save:await a.json(),view:value.view||value};});
 const signed=value=>value>0?'+'+value:String(value),initial=await read();const liu=initial.view.catalog.library.find(person=>person.person_id==='san14-candidate-0952');expect(liu).toBeTruthy();
 const current=initial.view.catalog.equipment.officers[String(liu.id)];expect(current.scope).toBe('current');expect(current.weapon.name_tc).toContain('雙股劍');expect(initial.save.state.officers[liu.id].weapon_id).toBe(current.weapon.id);
 const home=Object.values(initial.save.state.cities).find(city=>city.roster.officer_ids.includes(liu.id));expect(home).toBeTruthy();
 const inspect=async city=>{const marker=page.locator(`#world-map .city-hit[data-city="${city}"]`);await marker.focus();await page.keyboard.press('Enter');const info=page.locator(`.city-information[data-inspected-city="${city}"]`);await expect(info).toBeVisible();return info;};
 const info=await inspect(home.id),cityGear=info.locator(`[data-officer-equipment="${liu.id}"]:visible`);await expect(cityGear).toHaveAttribute('data-equipment-scope','current');await expect(cityGear).toContainText(current.weapon.name_tc);await expect(cityGear.locator('[data-equipment-effects]')).toHaveCount(0);const weaponTip=cityGear.locator('button[data-equipment-slot=weapon]');expect(await weaponTip.innerText()).toBe(current.weapon.name_tc);if(testInfo.project.name==='touch-chromium')await weaponTip.tap();else await weaponTip.hover();const tip=page.locator('#game-equipment-tooltip');await expect(tip).toBeVisible();await expect(tip).toHaveJSProperty('popover','manual');await expect(tip.locator('[data-equipment-stat=attack_bonus]')).toContainText(`單挑攻擊${signed(current.attack_bonus)}`);await expect(tip.locator('[data-equipment-stat=defense_bonus]')).toContainText(`防禦${signed(current.defense_bonus)}`);const bounds=await tip.evaluate(node=>{const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:innerWidth,height:innerHeight,open:node.matches(':popover-open')};});expect(bounds.open).toBe(true);expect(bounds.left).toBeGreaterThanOrEqual(0);expect(bounds.right).toBeLessThanOrEqual(bounds.width);expect(bounds.top).toBeGreaterThanOrEqual(0);expect(bounds.bottom).toBeLessThanOrEqual(bounds.height);await historyScreenshot(page,testInfo,'equipment-tooltip-city',{fullPage:false});await page.keyboard.press('Escape');await expect(tip).toBeHidden();await expect(page.locator('#dialog')).toBeVisible();await closeDialog(page);
 const person=async id=>{if(!await page.locator('#library').isVisible())await page.locator('#utility-menu summary').click();await page.locator('#library').click();await page.locator('#library-search').fill(id);await expect(page.locator('.person-detail')).toHaveCount(1);await page.locator('.person-detail').click();};
 await person('san14-candidate-0952');const detailed=page.locator(`#dialog [data-officer-equipment="${liu.id}"]:visible`);await expect(detailed).toContainText(current.weapon.name_tc);await expect(detailed).toContainText(current.armor.name_tc);await expect(detailed.locator('[data-equipment-details]')).not.toHaveAttribute('open','');await expect(detailed.locator('[data-equipment-weight]')).toBeHidden();await detailed.locator('[data-equipment-details] > summary').click();await expect(detailed.locator('[data-equipment-details]')).toHaveAttribute('open','');await expect(detailed.locator('[data-equipment-weight]')).toContainText(String(current.total_weight));await expect(detailed.locator('[data-equipment-retreat]')).toContainText(String(current.retreat_health_max));await expect(detailed.locator('[data-equipment-retreat]')).toContainText(`${current.retreat_chance}%`);
 await expect(detailed).toContainText('不改寫基礎武、知、德');await page.locator('#dialog-language').selectOption('ja');await expect(detailed).toContainText(current.weapon.name_ja);await expect(detailed).toContainText('現在の装備');if(await detailed.locator('[data-equipment-details]').getAttribute('open')===null)await detailed.locator('[data-equipment-details] > summary').click();await expect(detailed.locator('[data-equipment-weight]')).toBeVisible();await expect(detailed).toContainText('命中補正');await historyScreenshot(page,testInfo,'actual-equipment-detail-ja',{fullPage:false});await page.locator('#dialog-language').selectOption('zh-Hant');await closeDialog(page);
 expect((await read()).save).toEqual(initial.save,'Equipment inspection and translation never alter base stats, holdings or RNG');
 const candidates=[];
 for(const[city,row]of Object.entries(initial.view.catalog.facilities.cities))if(row.owner==='shu'&&row.can_act&&row.services.includes('armory')){
  for(const item of row.stock.weapon||[])if(item.can_buy)for(const ident of item.eligible_targets||[]){const quote=item.preview_by_officer?.[String(ident)];if(quote?.eligible===true&&initial.view.catalog.equipment.officers[String(ident)]?.weapon.id!==item.id)candidates.push({city,item,ident,quote,preferred:String(ident)===String(liu.id)});}
 }
 candidates.sort((a,b)=>Number(b.preferred)-Number(a.preferred)||a.item.price-b.item.price);const selection=candidates[0];expect(selection).toBeTruthy();
 await page.locator('#city-jump').selectOption(selection.city);await clickCityCommand(page,'city-facilities');await page.locator('#facility-tab-armory').click();await page.locator('#facility-equipment-officer').selectOption(String(selection.ident));await page.locator('#facility-equipment-item').selectOption(String(selection.item.id));
 expect((await page.locator('#facility-equipment-item option').allTextContents()).join(' ')).not.toMatch(/強度|重量|強さ|重さ/);await expect(page.locator('#facility-equipment-preview')).toContainText('資金');const oldIcon=page.locator(`#dialog [data-officer-equipment="${selection.ident}"] img[data-equipment-slot=weapon]`),oldSource=await oldIcon.getAttribute('src');const offerIcon=page.locator('[data-facility-selected-equipment] img');await expect(offerIcon).toHaveAttribute('data-equipment-key',`weapon:${selection.item.id}`);await expect.poll(()=>offerIcon.evaluate(node=>node.complete&&node.naturalWidth===128&&node.naturalHeight===128)).toBe(true);const comparison=page.locator(`[data-equipment-comparison="${selection.ident}"]`);await expect(comparison).toBeVisible();await expect(comparison).toHaveAttribute('data-equipment-eligible','true');await expect(comparison.locator('[data-equipment-compare=attack_bonus]')).toContainText(`${signed(selection.quote.before.attack_bonus)} → ${signed(selection.quote.after.attack_bonus)}`);
 await expect(comparison.locator('[data-equipment-comparison-details]')).not.toHaveAttribute('open','');await expect(comparison.locator('[data-equipment-compare=initiative_base]')).toBeHidden();await comparison.locator('[data-equipment-comparison-details] > summary').click();await expect(comparison.locator('[data-equipment-comparison-details]')).toHaveAttribute('open','');await expect(comparison.locator('[data-equipment-compare=initiative_base]')).toBeVisible();
 await expect(comparison.locator('[data-equipment-compare=total_weight]')).toContainText(`${selection.quote.before.total_weight} → ${selection.quote.after.total_weight}`);await expect(comparison.locator('[data-equipment-compare=initiative_base]')).toContainText(`${selection.quote.before.initiative_base} → ${selection.quote.after.initiative_base}`);await expect(comparison.locator('[data-equipment-compare=retreat_chance]')).toContainText(`${selection.quote.before.retreat_chance} → ${selection.quote.after.retreat_chance}%`);
 await page.locator('[data-equipment-guide] > summary').click();const guide=page.locator('[data-equipment-guide]');await expect(guide.locator('[data-special-equipment]')).toHaveCount(initial.view.catalog.equipment.special.length);await expect(guide).toContainText('取得條件');
 await page.locator('#dialog-language').selectOption('ja');await expect(guide).toHaveAttribute('open','');await expect(guide).toContainText('入手条件');await expect(page.locator('#facility-equipment-officer')).toHaveValue(String(selection.ident));await expect(page.locator('#facility-equipment-item')).toHaveValue(String(selection.item.id));await expect(page.locator('[data-equipment-comparison]')).toContainText('一騎討ちの攻撃');await historyScreenshot(page,testInfo,'equipment-shop-weight-comparison-ja',{fullPage:false});
 expect((await read()).save).toEqual(initial.save,'Shop quotes, unlock conditions and language remain read-only');await page.locator('#facility-equipment-buy').click();await waitIdle(page);let after=await read();
 expect(after.save.state.officers[selection.ident].weapon_id).toBe(selection.item.id);expect(after.save.state.officers[selection.ident].profile).toEqual(initial.save.state.officers[selection.ident].profile);expect(after.save.state.cities[selection.city].gold).toBe(initial.save.state.cities[selection.city].gold-selection.item.price);expect(after.save.state.rng).toEqual(initial.save.state.rng);
 expect(after.view.catalog.equipment.officers[String(selection.ident)].attack_bonus).toBe(selection.quote.after.attack_bonus);await expect(page.locator('#facility-equipment-buy')).toBeDisabled();await closeDialog(page);
 const events=page.locator('#event-dialog');await expect(events).toBeVisible();await assertOriginalEventArt(page,events,'equipment_bought');const skip=events.locator('[data-event-skip]');await(await skip.count()?skip:events.locator('[data-event-next]')).click();await expect(events).not.toBeVisible();
 const updated=await inspect(selection.city);await page.locator('#dialog-language').selectOption('zh-Hant');const changed=updated.locator(`[data-officer-equipment="${selection.ident}"]:visible`);await expect(changed).toContainText(selection.item.name_tc);const newIcon=changed.locator('img[data-equipment-slot=weapon]');await expect(newIcon).toHaveAttribute('data-equipment-key',`weapon:${selection.item.id}`);await expect(newIcon).toHaveAttribute('data-original-ui-provenance','remake-equipment-icon');expect(await newIcon.getAttribute('src')).not.toBe(oldSource);await expect.poll(()=>newIcon.evaluate(node=>node.complete&&node.naturalWidth===128)).toBe(true);await changed.locator('button[data-equipment-slot=weapon]').click();await expect(page.locator('#game-equipment-tooltip')).toContainText(`單挑攻擊${signed(selection.quote.after.attack_bonus)}`);await page.keyboard.press('Escape');await historyScreenshot(page,testInfo,'equipment-after-purchase',{fullPage:false});await closeDialog(page);
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#load-local').click();await waitIdle(page);const restored=await read();expect(restored.save).toEqual(JSON.parse(raw));expect(restored.view.catalog.equipment.officers[String(selection.ident)].weapon.id).toBe(selection.item.id);
 expect(restored.view.catalog.equipment.officers[String(selection.ident)].attack_bonus).toBe(selection.quote.after.attack_bonus);expect(errors.get(page)).toEqual([]);
});

test('castle contact opens a siege page for attack and retaliation without replaying saved damage',async({page},testInfo)=>{
 // Explicit legal contact fixture imported through the visible loader. The
 // real Worker owns formation, group orders, movement, casualties and saves.
 const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_siege_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:4*1024*1024}));
 const raw=JSON.stringify(fixture.save),touch=testInfo.project.name==='touch-chromium';await opening(page);
 const imported=async(value)=>{await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'controlled-castle-contact.json',mimeType:'application/json',buffer:Buffer.from(value)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();};
 const scene=page.locator('[data-battle-scene]'),canvas=page.locator('[data-battle-canvas]'),proof=[];
 for(const language of ['zh-Hant','ja']){
  if(language==='ja'){const menu=page.locator('#utility-menu');await menu.locator('summary').click();await page.locator('#language').selectOption('ja');await menu.locator('summary').click();}
  await imported(raw);await expect(scene).toHaveAttribute('data-battle-scene-mode','tactical');
  const before=await tacticalRead(page);expect(before.save).toEqual(fixture.save);const b=before.save.state.battle;
  await tacticalCell(page,b.extended.tactical.positions[fixture.actor],touch);await tacticalCell(page,fixture.cell,touch);await tacticalControl(page,'attack');await waitIdle(page);
  await expect(scene).toHaveAttribute('data-battle-scene-mode','siege-formation');await expect(scene).toHaveAttribute('data-battle-siege-fort',String(fixture.fort));
  await expect(scene).toHaveAttribute('data-siege-asset-source','original-native-capture');await expect(canvas).toHaveJSProperty('width',1024);await expect(canvas).toHaveJSProperty('height',960);
  const pending=await tacticalSave(page),initial=pending.state.battle.extended.siege;
  expect(pending.state.rng).toEqual(before.save.state.rng);for(const side of ['attackers','defenders'])expect(pending.state.battle[side]).toEqual(b[side]);
  expect(pending.state.battle.extended.tactical.points.attackers).toBe(b.extended.tactical.points.attackers-2);expect(pending.state.battle.extended.tactical.points.defenders).toBe(b.extended.tactical.points.defenders);
  await expect(page.locator('[data-siege-formation]')).toHaveCount(4);await page.locator('[data-siege-formation="3"]').click();expect(await tacticalSave(page)).toEqual(pending,'Formation preview is not a paid game command');
  await historyScreenshot(page,testInfo,'original-siege-formations-'+language);await tacticalControl(page,'siege-form');await waitIdle(page);
  const formed=await tacticalSave(page);expect(formed.state.battle.extended.siege.formations.attackers).toBe(3);expect(formed.state.battle.extended.siege.stage).toBe('orders');expect(formed.state.rng).toEqual(pending.state.rng);
  await page.locator('.siege-group-orders > summary').click();
  for(const kind of ['infantry','archer','cavalry','general'])await expect(page.locator('#siege-order-'+kind)).toBeVisible();
  await page.locator('#siege-order-general').selectOption('wait');await page.locator('#siege-order-archer').selectOption('wait');expect(await tacticalSave(page)).toEqual(formed);
  let progressed=(await tacticalSoldierRound(page)).save;expect(progressed.state.battle.extended.siege.round).toBe(2);
  expect(progressed.state.battle.extended.siege.units.map(u=>[u.id,u.x,u.y])).not.toEqual(formed.state.battle.extended.siege.units.map(u=>[u.id,u.x,u.y]));
  expect(progressed.state.battle.extended.tactical.points).toEqual(pending.state.battle.extended.tactical.points);await historyScreenshot(page,testInfo,'original-siege-orders-'+language);
  const mid=JSON.stringify(progressed);await imported(mid);expect(await tacticalSave(page)).toEqual(progressed,'Loading restores the exact pending piece positions, orders and RNG');
  const roundBeforeAuto=progressed.state.battle.extended.siege.round;await tacticalControl(page,'siege-run');await expect.poll(async()=>{const saved=await tacticalSave(page);return saved.state.battle.extended.siege?.round??999;}).toBeGreaterThan(roundBeforeAuto);await tacticalControl(page,'siege-run');await waitIdle(page);
  await expect(page.locator('#siege-run')).toHaveText(language==='ja'?'交戦を進める':'開始交戰');const paused=await tacticalSave(page);await page.waitForTimeout(700);expect(await tacticalSave(page)).toEqual(paused,'Pausing stops the automatic command loop');
  const shortcut=page.locator('.siege-group-orders');if(await shortcut.getAttribute('open')===null)await shortcut.locator('summary').click();
  await page.locator('#siege-order-infantry').selectOption('retreat');progressed=(await tacticalSoldierRound(page)).save;
  const infantries=progressed.state.battle.extended.siege.units.filter(piece=>piece.side==='attackers'&&piece.kind==='infantry');
  expect(infantries.length).toBeGreaterThan(0);for(const piece of infantries)expect(progressed.state.battle.extended.siege.piece_orders.attackers[piece.id]).toBe('retreat','The group shortcut submits the real order for each infantry squad after pausing');
  for(let step=0;step<16&&progressed.state.battle.extended.siege&&progressed.state.rng.draws===pending.state.rng.draws;step++){
   progressed=(await tacticalSoldierRound(page)).save;
  }
  expect(progressed.state.rng.draws).toBeGreaterThan(pending.state.rng.draws);expect(progressed.state.battle.extended.tactical.points).toEqual(pending.state.battle.extended.tactical.points);
  if(progressed.state.battle.extended.siege){
   await historyScreenshot(page,testInfo,'original-siege-contact-'+language);await tacticalControl(page,'siege-withdraw');await waitIdle(page);
  }
  const completed=await tacticalSave(page);expect(completed.state.battle.extended.siege).toBeUndefined();
  await imported(JSON.stringify(completed));expect(await tacticalSave(page)).toEqual(completed);await expect(page.locator('[data-battle-skip]')).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);proof.push({language,initial,formed:formed.state.battle.extended.siege,progressed:progressed.state.battle.extended.siege,points:completed.state.battle.extended.tactical.points,before_rng:pending.state.rng,after_rng:completed.state.rng});
 }
 await testInfo.attach('siege-authoritative-proof',{body:Buffer.from(JSON.stringify(proof,null,2)),contentType:'application/json'});expect(errors.get(page)).toEqual([]);
});

test('city-specific battlefield keeps both armies visible and supports real battle controls',async({page},testInfo)=>{
 // Natural 208 campaign, shipped Worker and public commands only. Independent
 // controlled-input acceptance also exercises Wuling and Chengdu locally.
 const read=()=>page.evaluate(async()=>{const r=await fetch('/api/save');if(!r.ok)throw Error('Battle save inspection failed');return r.json();});
 const dismiss=async()=>{
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  for(let count=0;count<20&&await page.locator('#event-dialog').isVisible();count++){
   const modal=page.locator('#event-dialog'),skip=modal.locator('[data-event-skip]');
   await(await skip.count()?skip:modal.locator('[data-event-next]')).click();
  }
  await expect(page.locator('#event-dialog')).toBeHidden();
 };
 const command=async id=>{
  const button=page.locator('#'+id);
  if(!await button.isVisible()&&await page.locator('#inspector-toggle').isVisible())await page.locator('#inspector-toggle').click();
  await button.click();
 };
 const language=async value=>{
  const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
  await page.locator('#language').selectOption(value);await menu.locator('summary').click();
 };
 const fields=[];page.on('response',response=>{if(/\/assets\/battlefields\/(?:index\.json|original-15\.png)$/.test(new URL(response.url()).pathname))fields.push({url:response.url(),status:response.status()});});
 await tacticalOpening(page);
 const scene=page.locator('[data-battle-scene]'),canvas=page.locator('[data-battle-canvas]'),roster=page.locator('.battle-army-menu');
 await expect(scene).toHaveAttribute('data-battle-scene-mode','tactical');await expect(scene).toHaveAttribute('data-battlefield-id','original-15');
 await expect(scene).toHaveAttribute('data-battlefield-source','same_label_association');await expect(canvas).toHaveJSProperty('width',1984);await expect(canvas).toHaveJSProperty('height',1536);
 await expect(page.locator('[data-battlefield-label]')).toHaveAttribute('title',/ROM/);
 expect((await read()).state.battle.target).toBe('danyang');expect(await page.evaluate(()=>GameBrowserEngine.ready)).toBe(true);
 expect(fields.some(row=>row.url.includes('/Three-Kingdoms2-King-mainland/assets/battlefields/original-15.png')&&row.status===200)).toBe(true);
 const geometry=await page.evaluate(()=>{
  const rect=node=>{const r=node.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
  return{roster:rect(document.querySelector('.battle-army-menu')),map:rect(document.querySelector('[data-battle-canvas]')),lists:[...document.querySelectorAll('[data-unit-list]')].map(n=>({...rect(n),content:n.scrollHeight})),overflow:document.documentElement.scrollWidth>innerWidth,wide:document.querySelector('.battle-layout').clientWidth>660};
 });
 expect(geometry.overflow).toBe(false);
 if(geometry.wide)expect(geometry.roster.right).toBeLessThanOrEqual(geometry.map.x+1);
 else expect(geometry.map.bottom).toBeLessThanOrEqual(geometry.roster.y+1);
 for(const list of geometry.lists){
  expect(list.y).toBeGreaterThanOrEqual(geometry.roster.y);expect(list.bottom).toBeLessThanOrEqual(geometry.roster.bottom+1);expect(list.height).toBeGreaterThan(80);expect(list.content).toBeGreaterThan(list.height);
 }
 const firstList=page.locator('[data-unit-list=friendly]'),otherList=page.locator('[data-unit-list=hostile]');
 const unchanged=await read(),actor=firstList.locator('[data-actor]:enabled').last();await actor.scrollIntoViewIfNeeded();
 const actorId=await actor.getAttribute('data-actor'),position=await page.evaluate(()=>({page:scrollY,list:document.querySelector('[data-unit-list=friendly]').scrollTop}));await actor.click();
 await expect(page.locator(`[data-actor="${actorId}"]`)).toHaveAttribute('aria-pressed','true');await expect(page.locator(`[data-actor="${actorId}"]`)).toHaveCSS('background-color','rgb(0, 0, 0)');
 expect(await page.evaluate(()=>({page:scrollY,list:document.querySelector('[data-unit-list=friendly]').scrollTop}))).toEqual(position);
 await expect(page.locator(`[data-actor="${actorId}"]`)).toBeFocused();
 const target=otherList.locator('[data-target]:enabled').last(),targetId=await target.getAttribute('data-target');await target.click();await expect(page.locator(`[data-target="${targetId}"]`)).toHaveAttribute('aria-pressed','true');
 if(!geometry.wide){await roster.locator('summary').click();await expect(roster).not.toHaveAttribute('open','');await roster.locator('summary').click();await expect(roster).toHaveAttribute('open','');}
 expect(await read()).toEqual(unchanged,'Roster controls never consume a game action or draw RNG');
 await canvas.scrollIntoViewIfNeeded();await historyScreenshot(page,testInfo,'battle-full-map-and-roster');
 await language('ja');await expect(scene).toHaveAttribute('data-l10n-native','ja');await expect(page.locator('[data-unit-list=friendly]')).toContainText('武');await historyScreenshot(page,testInfo,'battle-japanese');await language('zh-Hant');expect(await read()).toEqual(unchanged);
 const contact=await tacticalApproach(page,{touch:testInfo.project.name==='touch-chromium',preferred:actorId});await expect(page.locator('#attack')).toBeEnabled();
 const beforeContact=await read();await command('attack');await waitIdle(page);const pending=await read();
 await expect(scene).toHaveAttribute('data-battle-scene-mode',pending.state.battle.extended.siege.mode==='field'?'field-formation':'siege-formation');await expect(canvas).toHaveJSProperty('width',1024);await expect(canvas).toHaveJSProperty('height',960);
 expect(pending.state.rng).toEqual(beforeContact.state.rng);expect(pending.state.battle.attackers).toEqual(beforeContact.state.battle.attackers);expect(pending.state.battle.defenders).toEqual(beforeContact.state.battle.defenders);
 const committed=(await tacticalSoldierExchange(page,{testInfo,label:'battle-native-soldier-contact'})).save;
 expect(committed.state.battle.extended.tactical.points).toEqual(pending.state.battle.extended.tactical.points,'The complete soldier encounter uses only the original attack payment');
 await expect(canvas).toHaveJSProperty('width',1984);await expect(canvas).toHaveJSProperty('height',1536);const updated=await tacticalRead(page),survivor=updated.view.game.battle.attackers.find(unit=>String(unit.id)===String(contact.actor));if(survivor?.troops>0)await expect(page.locator(`[data-actor="${contact.actor}"]`)).toBeEnabled();
 const snapshot=await read(),download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');expect(JSON.parse(raw)).toEqual(snapshot);
 await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'battle-acceptance.json',mimeType:'application/json',buffer:Buffer.from(raw)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();expect(await read()).toEqual(snapshot);
 await expect(canvas).toHaveJSProperty('width',1984);await expect(page.locator('[data-battle-skip]')).toBeHidden();
 await testInfo.attach('battle-layout-and-assets',{body:Buffer.from(JSON.stringify({geometry,fields},null,2)),contentType:'application/json'});
 expect(errors.get(page)).toEqual([]);
});

test('authoritative tactical movement, shared points and contact attacks persist with a missing battlefield image',async({page},testInfo)=>{
 const touch=testInfo.project.name==='touch-chromium',initial=await tacticalOpening(page),b=initial.view.game.battle,board=initial.view.catalog.battle_tactical;
 expect(board.schema).toBe('tk2-battle-tactical-view-v1');expect(b.extended.tactical.schema).toBe('tk2-battle-tactical-v1');expect(board.grid).toEqual({columns:31,rows:19,tile_size:16});
 const own=b.attacker===initial.view.game.player?'attackers':'defenders',foe=own==='attackers'?'defenders':'attackers';
 const chosen=b[own].filter(unit=>board.actors[unit.id]?.reachable.length>0).sort((a,b)=>b.martial-a.martial||b.troops-a.troops)[0],id=chosen.id,scene=page.locator('[data-battle-scene]'),canvas=page.locator('[data-battle-canvas]');
 await expect(page.locator('#attack')).toBeDisabled();
 const boxed=b[own].find(unit=>{const q=board.actors[unit.id];return q?.can_act&&q.reachable.length===0&&q.attack_targets.length===0&&!Object.values(q.tactic_targets).some(ids=>ids.length);});expect(boxed).toBeTruthy();expect(boxed.id).not.toBe(id);
 await tacticalCell(page,b.extended.tactical.positions[boxed.id],touch);await expect(page.locator(`[data-actor="${boxed.id}"]`)).toBeEnabled();await expect(page.locator(`[data-actor="${boxed.id}"]`)).toHaveAttribute('aria-pressed','true');await expect(page.locator('#battle-move')).toBeDisabled();await expect(page.locator('.battle-move-reason')).toContainText('限制');expect(await tacticalSave(page)).toEqual(initial.save,'A surrounded unit stays inspectable and cannot bypass occupied cells');
 await tacticalCell(page,b.extended.tactical.positions[id],touch);await expect(page.locator(`[data-actor="${id}"]`)).toHaveAttribute('aria-pressed','true');await expect(scene).toHaveAttribute('data-battle-selected-actor',String(id));
 const selected={save:await tacticalSave(page),view:initial.view},row=selected.view.catalog.battle_tactical.actors[id];expect(row.reachable.length).toBeGreaterThan(0);expect(row.attack_targets).toEqual([]);await expect(scene).toHaveAttribute('data-battle-reachable-count',String(row.reachable.length));
 const occupied=new Set(Object.values(b.extended.tactical.positions).map(p=>p.x+','+p.y)),reachable=new Set(row.reachable.map(p=>p.x+','+p.y));let invalid;
 for(let y=0;y<19&&!invalid;y++)for(let x=0;x<31;x++)if(!occupied.has(x+','+y)&&!reachable.has(x+','+y)){invalid={x,y};break;}
 expect(invalid).toBeTruthy();await tacticalCell(page,invalid,touch);await expect(page.locator('#battle-move')).toBeDisabled();expect(await tacticalSave(page)).toEqual(selected.save,'Unreachable destination inspection cannot submit a move or draw RNG');
 const origin=b.extended.tactical.positions[id],first=[...row.reachable].sort((a,b)=>a.cost-b.cost||a.y-b.y||a.x-b.x).find(p=>Math.abs(p.x-origin.x)+Math.abs(p.y-origin.y)>=4&&p.cost<board.points[own]-4);expect(first).toBeTruthy();await tacticalCell(page,first,touch);await expect(page.locator('#battle-move-preview')).toHaveAttribute('data-battle-move-cost',String(first.cost));await expect(page.locator('#battle-move')).toBeEnabled();
 for(const button of await page.locator('[data-battle-nav],#battle-move').all()){const rect=await button.boundingBox();expect(rect.height).toBeGreaterThanOrEqual(44);expect(rect.width).toBeGreaterThanOrEqual(44);}
 const right=page.locator('[data-battle-nav=right]');if(touch)await right.tap();else await right.click();await expect(page.locator('#battle-move-preview')).toHaveAttribute('data-battle-move-x',String(Math.min(30,first.x+1)));expect(await tacticalSave(page)).toEqual(selected.save,'Directional adjustment previews only');
 await tacticalControl(page,'battle-cancel-move');await expect(page.locator('#battle-move')).toBeDisabled();expect(await tacticalSave(page)).toEqual(selected.save,'Cancelling the destination never spends points');
 if(!touch){
  await page.locator(`[data-actor="${id}"]`).click();
  for(const key of ['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'])await page.keyboard.press(key);
  await expect(scene).toHaveAttribute('data-battle-destination',origin.x+','+origin.y);
  await page.keyboard.press('Escape');await expect(page.locator('#battle-move')).toBeDisabled();expect(await tacticalSave(page)).toEqual(selected.save,'Roster-focused four-key movement previews and Escape do not consume state');
 }
 const menu=page.locator('#utility-menu');await menu.locator('summary').click();await page.locator('#language').selectOption('ja');await menu.locator('summary').click();await expect(page.locator('.battle-ap')).toContainText('共有機動力');expect(await tacticalSave(page)).toEqual(selected.save,'Language and selection preserve all state/RNG');
 await tacticalCell(page,first,touch);await historyScreenshot(page,testInfo,'tactical-reachable-preview-ja');
 await page.evaluate(()=>{window.__tacticalMotion=[];window.__tacticalMotionObserver=new MutationObserver(()=>{const node=document.querySelector('[data-battle-scene]');if(node?.dataset.battleSceneMode==='movement'&&window.__tacticalMotion.length<120){const point={actor:node.dataset.battleMoveActor,x:Number(node.dataset.battleMoveX),y:Number(node.dataset.battleMoveY),step:Number(node.dataset.battleMoveStep)},last=window.__tacticalMotion.at(-1);if(!last||Object.keys(point).some(key=>point[key]!==last[key]))window.__tacticalMotion.push(point);}});window.__tacticalMotionObserver.observe(document.querySelector('#stage'),{childList:true,subtree:true,attributes:true,attributeFilter:['data-battle-scene-mode','data-battle-move-actor','data-battle-move-step','data-battle-move-x','data-battle-move-y']});});
 if(touch)await tacticalControl(page,'battle-move');else{await page.locator(`[data-actor="${id}"]`).focus();await page.keyboard.press('Enter');}
 await expect.poll(()=>page.evaluate(({id,origin,first})=>window.__tacticalMotion.some(p=>p.actor===String(id)&&(p.x!==origin.x*16+8||p.y!==origin.y*16+8)&&(p.x!==first.x*16+8||p.y!==first.y*16+8)),{id,origin,first})).toBe(true);
 const firstMotion=await page.evaluate(()=>{window.__tacticalMotionObserver.disconnect();return window.__tacticalMotion;});await tacticalSettle(page);
 const moved=await tacticalRead(page);expect(moved.save.state.battle.extended.tactical.positions[id]).toEqual({x:first.x,y:first.y});expect(moved.save.state.battle.extended.tactical.points[own]).toBe(selected.save.state.battle.extended.tactical.points[own]-first.cost);expect(moved.save.state.rng).toEqual(selected.save.state.rng);await expect(page.locator(`[data-actor="${id}"]`)).toBeEnabled();
 const another=[...moved.view.catalog.battle_tactical.actors[id].reachable].sort((a,b)=>a.cost-b.cost||a.y-b.y||a.x-b.x).find(p=>p.cost<moved.view.catalog.battle_tactical.points[own]-2);expect(another).toBeTruthy();
 await tacticalCell(page,another,touch);await tacticalControl(page,'battle-move');await tacticalSettle(page);const twice={save:await tacticalSave(page)};
 expect(twice.save.state.battle.extended.tactical.positions[id]).toEqual({x:another.x,y:another.y});expect(twice.save.state.battle.extended.tactical.points[own]).toBe(moved.save.state.battle.extended.tactical.points[own]-another.cost);expect(twice.save.state.rng).toEqual(moved.save.state.rng);
 const beforeEnemy=twice.save.state.battle.extended.tactical.positions;await tacticalControl(page,'battle-wait');await tacticalSettle(page,{returnToMacro:true});const enemyTurn={save:await tacticalSave(page)};
 expect(enemyTurn.save.state.battle.round).toBe(twice.save.state.battle.round+1);expect(b[foe].some(unit=>JSON.stringify(enemyTurn.save.state.battle.extended.tactical.positions[unit.id])!==JSON.stringify(beforeEnemy[unit.id]))).toBe(true,'The enemy actually moves on its whole-side turn');
 let contact=await tacticalApproach(page,{touch,preferred:id});
 await expect(page.locator('#attack')).toBeEnabled();const beforeAttack=contact.state,actorId=contact.actor;await historyScreenshot(page,testInfo,'tactical-contact-ja');
 await tacticalControl(page,'attack');await waitIdle(page);const pendingAttack=await tacticalSave(page);
 await expect(scene).toHaveAttribute('data-battle-scene-mode',pendingAttack.state.battle.extended.siege.mode==='field'?'field-formation':'siege-formation');
 expect(pendingAttack.state.rng).toEqual(beforeAttack.save.state.rng);expect(pendingAttack.state.battle[foe]).toEqual(beforeAttack.save.state.battle[foe]);expect(pendingAttack.state.battle[own]).toEqual(beforeAttack.save.state.battle[own]);
 // Reciprocal infantry/archer/cavalry damage has its explicit controlled
 // current-engine assertion in browser_soldier_ui. This natural300-vs1000
 // march must also accept a lawful one-sided ranged defeat.
 const committed=await tacticalSoldierExchange(page,{anySide:true,testInfo,label:'tactical-soldier-retaliation-ja'});
 expect(committed.save.state.battle.extended.tactical.points[own]).toBe(beforeAttack.save.state.battle.extended.tactical.points[own]-beforeAttack.view.catalog.battle_tactical.attack_cost);
 const totalTroops=save=>[own,foe].reduce((sum,side)=>sum+save.state.battle[side].reduce((n,u)=>n+u.troops,0),0);
 expect(totalTroops(committed.save)).toBeLessThan(totalTroops(beforeAttack.save),'The real contact causes committed casualties without assuming equal-strength armies');
 const survivor=committed.save.state.battle[own].find(unit=>String(unit.id)===String(actorId)),alive=survivor.troops>0&&committed.save.state.battle.extended.support[actorId].health>0;
 await expect(page.locator(`[data-actor="${actorId}"]`))[alive?'toBeEnabled':'toBeDisabled']();
 const inspectActorId=alive?actorId:committed.save.state.battle[own].find(unit=>unit.troops>0&&committed.save.state.battle.extended.support[unit.id].health>0).id;
 let attackCount=1;const more=committed.view.catalog.battle_tactical.actors[actorId];if(more.attack_targets.length&&committed.save.state.battle.extended.tactical.points[own]>2){
  await page.locator(`[data-actor="${actorId}"]`).click();await page.locator(`[data-target="${more.attack_targets[0]}"]`).click();await tacticalControl(page,'attack');await waitIdle(page);
  expect((await tacticalSave(page)).state.battle.extended.siege).toBeTruthy();await tacticalControl(page,'siege-withdraw');await tacticalSettle(page,{returnToMacro:true});attackCount++;
 }else if(!more.attack_targets.length)await expect(page.locator('#attack')).toBeDisabled();
 const saved={save:await tacticalSave(page)},download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');expect(JSON.parse(raw)).toEqual(saved.save);
 await page.route('**/assets/battlefields/original-15.png*',route=>route.fulfill({status:200,contentType:'image/png',body:Buffer.from('deliberately undecodable test image')}));
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'tactical-grid-acceptance.json',mimeType:'application/json',buffer:Buffer.from(raw)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();
 const restored={save:await tacticalSave(page)};expect(restored.save).toEqual(saved.save,'Raw save reload retains every coordinate, AP balance, commander and RNG value');await expect(scene).toHaveAttribute('data-battlefield-id','original-15');await expect(canvas).toHaveJSProperty('width',1984);await expect(canvas).toHaveJSProperty('height',1536);await expect(page.locator('[data-battle-caption]')).toContainText('座標と移動のルールは変わりません');
 const position=restored.save.state.battle.extended.tactical.positions[inspectActorId];await tacticalCell(page,position,touch);await expect(page.locator(`[data-actor="${inspectActorId}"]`)).toHaveAttribute('aria-pressed','true');expect(await tacticalSave(page)).toEqual(saved.save,'The neutral-grid fallback keeps exact click coordinates');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await historyScreenshot(page,testInfo,'tactical-image-failure-same-grid');
 const identity=await page.evaluate(async()=>{const build=await(await fetch(new URL('runtime/build.json',location.href))).json();return{worker:GameBrowserEngine.version,commit:build.commit,content_sha256:build.content_sha256,url:location.href};});
 for(const[label,value]of [['initial',initial.save],['first-move',moved.save],['two-moves',twice.save],['enemy-turn',enemyTurn.save],['restored',restored.save]]){const file=testInfo.outputPath('tactical-'+label+'.json');await writeFile(file,JSON.stringify(value));await testInfo.attach('tactical-'+label,{path:file,contentType:'application/json'});}
 const proof=testInfo.outputPath('tactical-identity-and-actions.json');await writeFile(proof,JSON.stringify({identity,contact_armies:{actor_troops:beforeAttack.save.state.battle[own].find(unit=>String(unit.id)===String(actorId)).troops,target_troops:beforeAttack.save.state.battle[foe].find(unit=>String(unit.id)===String(contact.target)).troops},actor:id,attack_actor:actorId,attack_count:attackCount,inspected_survivor:inspectActorId,movement_frames:firstMotion,first_move:first,second_move:another,contact_trace:contact.trace,points_before:initial.save.state.battle.extended.tactical.points,points_after:saved.save.state.battle.extended.tactical.points,positions_after:saved.save.state.battle.extended.tactical.positions},null,2));await testInfo.attach('tactical-identity-and-actions',{path:proof,contentType:'application/json'});
 expect(errors.get(page)).toEqual([]);
});

test('faction command books can all be spent in one city and survive save reload',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');await page.locator('input[name=faction][value=shu]').check();
 await page.locator('#begin').click();await waitIdle(page);await dismissHistoryOpening(page);
 const dismiss=async()=>{await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));const modal=page.locator('#event-dialog');if(await modal.isVisible()){const skip=modal.locator('[data-event-skip]');await(await skip.count()?skip:modal.locator('[data-event-next]')).click();await expect(modal).toBeHidden();}};
 const read=()=>page.evaluate(async()=>{const response=await fetch('/api/save');if(!response.ok)throw Error('Command-book save inspection failed');return response.json();});
 const budget=save=>save.state.extension.command_books.factions.shu;
 const counter=page.locator('#inspector [data-command-books]');
 await page.locator('#city-jump').selectOption('shujun');
 const initial=await read(),total=budget(initial).total;
 expect(total).toBeGreaterThan(1);expect(total).toBeLessThanOrEqual(13);expect(budget(initial).used).toBe(0);
 await expect(counter).toHaveAttribute('data-command-books-remaining',String(total));await expect(counter).toHaveAttribute('data-command-books-total',String(total));
 await clickCityCommand(page,'recruit');await expect(page.locator('#dialog [data-command-book-cost]')).toHaveAttribute('data-command-book-cost','1');
 await page.locator('#dialog-language').selectOption('ja');await expect(page.locator('#dialog [data-command-books]')).toContainText('命令書',{useInnerText:true});
 await expect(page.locator('#dialog [data-command-books]')).toContainText('今回消費 1枚',{useInnerText:true});await expect(counter).toContainText('残り',{useInnerText:true});
 await closeDialog(page);expect(await read()).toEqual(initial,'Cancellation and language changes cannot spend books or RNG');
 for(let index=0;index<total;index++){
  await clickCityCommand(page,'recruit');await page.locator('#confirm-recruit').click();await waitIdle(page);await expect(page.locator('#allocation-officer')).toBeVisible();await closeDialog(page);await waitIdle(page);
  const current=await read(),row=budget(current);
  expect(current.state.turn).toBe(initial.state.turn);expect(row.used).toBe(index+1);expect(row.total).toBe(total);
  expect(row.orders).toHaveLength(index+1);expect(row.orders.every(order=>order.city==='shujun'&&order.kind==='recruit'&&order.cost===1)).toBe(true);
  expect(current.state.cities.shujun.reserves).toBe(initial.state.cities.shujun.reserves+(index+1)*100);
  expect(current.state.cities.shujun.gold).toBe(initial.state.cities.shujun.gold-(index+1)*20);expect(current.state.cities.shujun.grain).toBe(initial.state.cities.shujun.grain-(index+1)*30);
  expect(current.state.rng).toEqual(initial.state.rng);await expect(counter).toHaveAttribute('data-command-books-remaining',String(total-index-1));
  if(index+1<total)await expect(page.locator('#recruit')).toBeEnabled();
 }
 await expect(page.locator('#recruit')).toBeDisabled();await expect(page.locator('#allocate')).toBeDisabled();await expect(counter).toContainText('使い切りました',{useInnerText:true});
 const spent=await read(),other=Object.values(spent.state.cities).find(city=>city.owner==='shu'&&city.id!=='shujun');expect(other).toBeTruthy();
 await page.locator('#city-jump').selectOption(other.id);await page.locator('#city-command-tab-army').click();await expect(counter).toHaveAttribute('data-command-books-remaining','0');await expect(page.locator('#recruit')).toBeDisabled();
 await clickCityCommand(page,'city-civic');await page.locator('#facility-civic-policy').click();await expect(page.locator('#facility-save-policy')).toBeEnabled();await expect(page.locator('.facility-footer [data-command-book-cost]')).toHaveAttribute('data-command-book-cost','0');
 const beforePolicy=await read();await page.locator('#facility-save-policy').click();await waitIdle(page);const policy=await read();
 expect(budget(policy)).toEqual(budget(beforePolicy));expect(policy.state.rng).toEqual(beforePolicy.state.rng);await closeDialog(page);
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'spent-command-books.json',mimeType:'application/json',buffer:Buffer.from(raw)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();
 expect(await read()).toEqual(JSON.parse(raw),'Reload never grants the already-spent command books a second time');await expect(counter).toHaveAttribute('data-command-books-remaining','0');
 const noOverflow=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);expect(noOverflow).toBe(true);await historyScreenshot(page,testInfo,'command-books-one-city-exhausted');
 await page.locator('#end-turn').click();await waitIdle(page);await dismiss();await page.locator('#run-ai').click();await waitIdle(page);await dismiss();
 if(await page.locator('#process-arrivals').isVisible()){await page.locator('#process-arrivals').click();await waitIdle(page);await dismiss();}
 const next=await read();expect(next.state.turn).toBe(initial.state.turn+1);expect(budget(next).used).toBe(0);expect(budget(next).orders).toEqual([]);
 await expect(counter).toHaveAttribute('data-command-books-remaining',String(budget(next).total));await historyScreenshot(page,testInfo,'command-books-next-turn');
 const identity=await page.evaluate(async()=>{const response=await fetch(new URL('runtime/build.json',location.href));const build=await response.json();return{worker:GameBrowserEngine.version,commit:build.commit,content_sha256:build.content_sha256,url:location.href};});
 for(const [label,save]of [['initial',initial],['next-turn',next]]){const file=testInfo.outputPath('command-books-'+label+'-save.json');await writeFile(file,JSON.stringify(save));await testInfo.attach('command-books-'+label+'-save',{path:file,contentType:'application/json'});}
 const spentFile=testInfo.outputPath('command-books-spent-raw-save.json');await writeFile(spentFile,raw);await testInfo.attach('command-books-spent-raw-save',{path:spentFile,contentType:'application/json'});
 const proof=testInfo.outputPath('command-books-identity-and-ledgers.json');await writeFile(proof,JSON.stringify({identity,initial:budget(initial),spent:budget(JSON.parse(raw)),next:budget(next),rng_before:initial.state.rng,rng_after_spending:spent.state.rng},null,2));await testInfo.attach('command-books-identity-and-ledgers',{path:proof,contentType:'application/json'});
 expect(errors.get(page)).toEqual([]);
});

test('command-book confirmations and one paid city allocation flow preserve cancellation and save recovery',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');await page.locator('input[name=faction][value=shu]').check();await page.locator('#begin').click();await waitIdle(page);await tacticalDismiss(page);await page.locator('#city-jump').selectOption('shujun');
 const read=()=>page.evaluate(async()=>{const response=await fetch('/api/save');if(!response.ok)throw Error('Save inspection failed');return response.json();});
 const budget=save=>save.state.extension.command_books.factions.shu,active=save=>budget(save).allocation?.active??null;
 const modal=page.locator('#order-confirm-dialog'),initial=await read(),allocations=[];
 const closeFlow=async()=>{await closeDialog(page);await expect.poll(async()=>active(await read())).toBeNull();await waitIdle(page);};
 const accept=async(kind)=>{await expect(modal).toBeVisible();await expect(modal).toHaveAttribute('data-command-book-kind',kind);await expect(modal).toHaveAttribute('data-command-book-cost','1');await modal.locator('#order-confirm-accept').click();await waitIdle(page);await expect(modal).toBeHidden();};
 await clickCityCommand(page,'recruit');await page.locator('#confirm-recruit').click();await expect(modal).toBeVisible();await expect(modal.locator('#order-confirm-message')).toContainText('成都');
 expect(await read()).toEqual(initial,'A payment prompt cannot spend resources, books or RNG before approval');
 await page.locator('#order-confirm-language').selectOption('ja');await expect(modal.locator('#order-confirm-message')).toContainText('命令書1枚',{useInnerText:true});await historyScreenshot(page,testInfo,'command-book-confirmation-ja');
 for(const button of await modal.locator('button').all()){const rect=await button.boundingBox();expect(rect.width).toBeGreaterThanOrEqual(44);expect(rect.height).toBeGreaterThanOrEqual(44);}
 await page.keyboard.press('Escape');await expect(modal).toBeHidden();await expect(page.locator('#confirm-recruit')).toBeVisible();expect(await read()).toEqual(initial,'Escape returns to the original form without committing its command');
 await page.locator('#confirm-recruit').click();await accept('recruit');await expect(page.locator('#allocation-officer')).toBeVisible();
 let current=await read();expect(budget(current).used).toBe(1);expect(active(current)).toBeTruthy();expect(budget(current).orders[0].kind).toBe('recruit');expect(current.state.cities.shujun.reserves).toBe(initial.state.cities.shujun.reserves+100);
 await expect(page.locator('#dialog [data-command-book-cost]')).toHaveAttribute('data-command-book-cost','0');
 const ids=(await page.locator('#allocation-officer option').evaluateAll(nodes=>nodes.map(node=>node.value))).slice(0,3);expect(ids).toHaveLength(3);
 const distribute=async(ident,source)=>{
  const before=await read(),troops=before.state.officers[ident].troops,next=troops+1;
  expect(next).toBeLessThanOrEqual(1000);expect(before.state.cities.shujun.reserves).toBeGreaterThan(0);
  await page.locator('#allocation-officer').selectOption(ident);await page.locator('#allocation-troops').fill(String(next));await page.locator('#confirm-allocation').click();await waitIdle(page);await expect(page.locator('#allocation-officer')).toBeVisible();await expect(modal).toBeHidden();
  const after=await read();expect(after.state.officers[ident].troops).toBe(next);expect(after.state.cities.shujun.reserves).toBe(before.state.cities.shujun.reserves-1);expect(budget(after).used).toBe(budget(before).used);expect(active(after)).toEqual(active(before));expect(after.state.rng).toEqual(before.state.rng);expect(after.state.cities.shujun.reserves+after.state.cities.shujun.roster.officer_ids.reduce((sum,id)=>sum+after.state.officers[id].troops,0)).toBe(before.state.cities.shujun.reserves+before.state.cities.shujun.roster.officer_ids.reduce((sum,id)=>sum+before.state.officers[id].troops,0));allocations.push({source,officer:ident,troops_before:troops,troops_after:next,books_used:budget(after).used,flow:active(after).id,reserves:after.state.cities.shujun.reserves});return after;
 };
 for(const ident of ids)current=await distribute(ident,'recruit-continuation');expect(budget(current).used).toBe(1);await closeFlow();
 // A new unpaid draft can be browsed and discarded without even closing a
 // server flow. The current selection and every officer input stay local.
 const revision=()=>page.evaluate(async()=>{const response=await fetch('/api/state');if(!response.ok)throw Error('Revision inspection failed');const body=await response.json();return(body.view||body).revision;});
 await openAllocation(page);const untouched=await read(),unpaidRevision=await revision(),discarded=await page.locator('#allocation-officer').inputValue();
 await expect(page.locator('#confirm-allocation')).toBeDisabled();await page.locator('#allocation-troops').fill(String(untouched.state.officers[discarded].troops+1));await page.locator('#allocation-next').click();
 expect(await read()).toEqual(untouched);expect(await revision()).toBe(unpaidRevision);await expect(modal).toBeHidden();await closeDialog(page);await waitIdle(page);
 expect(await read()).toEqual(untouched);expect(await revision()).toBe(unpaidRevision,'Closing an unpaid draft sends no allocation_close command');
 await openAllocation(page);await page.locator('#allocation-officer').selectOption(discarded);await expect(page.locator('#allocation-troops')).toHaveValue(String(untouched.state.officers[discarded].troops));
 const beforeNew=await read(),beforeRevision=await revision(),batch=[];
 for(const ident of ids){
  const next=beforeNew.state.officers[ident].troops+1;expect(next).toBeLessThanOrEqual(1000);
  await page.locator('#allocation-officer').selectOption(ident);await page.locator('#allocation-troops').fill(String(next));await page.locator('#allocation-next').click();
  expect(await read()).toEqual(beforeNew,'Next stores only a draft; troops, reserves, books and RNG remain untouched');await expect(modal).toBeHidden();batch.push({officer:ident,troops:next});
 }
 expect(await revision()).toBe(beforeRevision,'Multiple Next/select actions never issue a state-changing request');
 await expect(page.locator('#allocation-draft-status')).toContainText('3',{useInnerText:true});await expect(page.locator('#allocation-draft-status')).not.toContainText('<span');
 for(const item of batch){await page.locator('#allocation-officer').selectOption(item.officer);await expect(page.locator('#allocation-troops')).toHaveValue(String(item.troops));}
 await page.locator('#confirm-allocation').click();await expect(modal).toBeVisible();await expect(modal.locator('#order-confirm-message')).toContainText('3');
 expect(await read()).toEqual(beforeNew);await modal.locator('#order-confirm-cancel').click();expect(await read()).toEqual(beforeNew);expect(await revision()).toBe(beforeRevision);
 for(const item of batch){await page.locator('#allocation-officer').selectOption(item.officer);await expect(page.locator('#allocation-troops')).toHaveValue(String(item.troops));}
 await page.locator('#confirm-allocation').click();await accept('allocate');await expect(page.locator('#allocation-officer')).toBeVisible();current=await read();
 expect(budget(current).used).toBe(2);expect(current.state.cities.shujun.reserves).toBe(beforeNew.state.cities.shujun.reserves-3);expect(current.state.rng).toEqual(beforeNew.state.rng);
 for(const item of batch)expect(current.state.officers[item.officer].troops).toBe(item.troops);
 expect(await revision()).toBe(beforeRevision+1,'The entire three-officer batch is one atomic command');await expect(page.locator('#confirm-allocation')).toBeDisabled();
 allocations.push({source:'three-local-drafts-final-atomic-confirmation',batch,revision_before:beforeRevision,revision_after:await revision(),books_before:budget(beforeNew).used,books_after:budget(current).used,reserves_before:beforeNew.state.cities.shujun.reserves,reserves_after:current.state.cities.shujun.reserves,unpaid_navigation_checksum:beforeNew.checksum,next_preserved_save_and_revision:true,cancel_confirmation_preserved_all_drafts:true,closing_unpaid_draft_preserved_save_and_revision:true});
 for(const ident of ids)current=await distribute(ident,'standalone-continuation');expect(budget(current).used).toBe(2);await historyScreenshot(page,testInfo,'allocation-three-officers-one-book');await closeFlow();
 const remaining=budget(await read()).remaining??(budget(await read()).total-budget(await read()).used);
 for(let i=0;i<remaining;i++){
  await clickCityCommand(page,'recruit');await page.locator('#confirm-recruit').click();await accept('recruit');await expect(page.locator('#allocation-officer')).toBeVisible();
  if(i+1<remaining)await closeFlow();
 }
 current=await read();expect(budget(current).used).toBe(budget(current).total);expect(active(current)).toBeTruthy();
 for(const ident of ids)current=await distribute(ident,'last-book-continuation');
 await historyScreenshot(page,testInfo,'allocation-last-book-paid-flow');
 const raw=await page.evaluate(async()=>{const response=await fetch('/api/save');if(!response.ok)throw Error('Raw save export failed');return response.text();});expect(JSON.parse(raw)).toEqual(current);
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'paid-city-allocation.json',mimeType:'application/json',buffer:Buffer.from(raw)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();await page.locator('#city-jump').selectOption('shujun');
 expect(await read()).toEqual(JSON.parse(raw));await expect(page.locator('#continue-allocation')).toBeEnabled();await page.locator('#continue-allocation').click();await expect(page.locator('#dialog [data-command-book-cost]')).toHaveAttribute('data-command-book-cost','0');await distribute(ids[0],'loaded-continuation');await closeFlow();
 await expect(page.locator('#allocate')).toBeDisabled();await expect(page.locator('#recruit')).toBeDisabled();await expect(page.locator('#continue-allocation')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors.get(page)).toEqual([]);
 const file=testInfo.outputPath('paid-allocation-raw-save.json');await writeFile(file,raw);await testInfo.attach('paid-allocation-raw-save',{path:file,contentType:'application/json'});
 const evidence=testInfo.outputPath('paid-allocation-three-officer-ledgers.json');await writeFile(evidence,JSON.stringify(allocations,null,2));await testInfo.attach('paid-allocation-three-officer-ledgers',{path:evidence,contentType:'application/json'});
});

test('succession updates live faction names and ruler portraits while historical previews and saves stay intact',async({page},testInfo)=>{
 const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B',new URL('./browser_ruler_fixture.py',import.meta.url).pathname],{encoding:'utf8',maxBuffer:4*1024*1024}));
 await opening(page);
 const load=async(raw,name)=>{await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(raw)});await waitIdle(page);await expect(page.locator('#dialog')).toBeHidden();};
 const inspect=async selector=>{const control=page.locator(selector);if(!await control.isVisible()&&await page.locator('#inspector-toggle').isVisible())await page.locator('#inspector-toggle').click();await expect(control).toBeVisible();return control;};
 const currentLabel=name=>page.evaluate(value=>GameI18n.t(value),name);
 const language=async locale=>{const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();await page.locator('#language').selectOption(locale);await menu.locator('summary').click();};
 await load(JSON.stringify(fixture.save),'controlled-current-succession.json');await tacticalDismiss(page);
 const choice=await inspect('#successor-officer');await choice.selectOption(String(fixture.selected.id));await page.locator('#choose-successor').click();await waitIdle(page);
 const after=await tacticalSave(page);expect(after.state.extension.leaders[fixture.owner]).toBe(fixture.selected.id);expect(after.state.extension.pending_succession[fixture.owner]).toBeUndefined();expect(after.state.rng).toEqual(fixture.save.state.rng);expect(after.state.cities).toEqual(fixture.save.state.cities);expect(after.scenario).toBe(fixture.save.scenario);expect(after.catalog_sha256).toBe(fixture.save.catalog_sha256);
 await expect(page.locator('#event-dialog')).toBeVisible();await expect(page.locator('#event-description')).toContainText(await currentLabel(fixture.selected.name));await tacticalDismiss(page);
 await page.locator('#city-jump').selectOption(fixture.city);
 const identity=page.locator(`[data-current-faction="${fixture.owner}"]`),portrait=identity.locator(`[data-portrait-person="${fixture.selected.person_id}"]`);
 const verifyLive=async()=>{
  const label=await currentLabel(fixture.selected.name);await expect(identity.locator('[data-current-faction-label]')).toContainText(label);await expect(portrait).toBeVisible();await expect(portrait).toHaveAttribute('data-portrait-name',fixture.selected.name);await expect.poll(()=>portrait.locator('img').evaluate(node=>node.complete&&node.naturalWidth>0)).toBe(true);
  await expect(page.locator(`#city-jump option[value="${fixture.city}"]`)).toContainText(label);
  await expect(page.locator(`#world-map [data-city="${fixture.city}"]`)).toHaveAttribute('aria-label',new RegExp(label));
  const ledger=page.locator('.faction-ledger');if(await ledger.getAttribute('open')===null)await ledger.locator('summary').click();await expect(ledger.locator(`[data-faction-resources="${fixture.owner}"] th`)).toContainText(label);
  await(await inspect('#city-information')).click();await expect(page.locator('.city-information-owner')).toContainText(label);await closeDialog(page);
  expect(await tacticalSave(page)).toEqual(after,'Names, portraits, map ownership, city information and bilingual viewing do not modify the save or RNG');
  return label;
 };
 for(const locale of ['zh-Hant','ja']){
  await language(locale);await inspect('[data-current-faction-label]');await verifyLive();await historyScreenshot(page,testInfo,'successor-owner-'+locale);
  const face=await portrait.boundingBox(),text=await identity.locator('[data-current-faction-label]').boundingBox();expect(Math.abs(face.y+face.height/2-text.y-text.height/2)).toBeLessThanOrEqual(2);
  await page.locator('#main-menu').click();await page.locator('#scenario').selectOption(fixture.save.scenario);await page.locator(`input[name=faction][value="${fixture.owner}"]`).check();
  const historical=page.locator('#setup-summary');await expect(historical.locator(`[data-portrait-person="${fixture.previous.person_id}"]`)).toBeVisible();await expect(historical).toContainText(await currentLabel(fixture.previous.name));await expect(historical.locator(`[data-portrait-person="${fixture.selected.person_id}"]`)).toHaveCount(0);expect(await tacticalSave(page)).toEqual(after,'A historical preview never rewrites the running ruler or faction');
  await page.locator('#cancel-setup').click();await inspect('[data-current-faction-label]');await verifyLive();
 }
 const raw=await page.evaluate(async()=>{const response=await fetch('/api/save');if(!response.ok)throw Error('Successor raw save failed');return response.text();});expect(JSON.parse(raw)).toEqual(after);
 await page.reload();await enterScenarioMenu(page);await load(raw,'actual-successor-roundtrip.json');await page.locator('#city-jump').selectOption(fixture.city);await inspect('[data-current-faction-label]');await verifyLive();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors.get(page)).toEqual([]);
 const file=testInfo.outputPath('actual-successor-raw-save.json');await writeFile(file,raw);await testInfo.attach('actual-successor-raw-save',{path:file,contentType:'application/json'});
});

test('dialogue exchanges and dated family loyalty remain bilingual without replaying or changing saved state',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=wei]').check();
 await page.locator('#begin').click();await waitIdle(page);
 const read=()=>page.evaluate(async()=>await(await fetch('/api/save')).json());
 const original=await read(),event=page.locator('#event-dialog');
 await expect(event).toBeVisible();await expect(event.locator('[data-dialogue-exchange] .dialogue-turn')).toHaveCount(2);
 await expect(event.locator('[data-dialogue-person="san14-candidate-0521"]')).toBeVisible();
 await expect(event.locator('.event-facts')).not.toBeEmpty();
 await event.locator('[data-language-picker]').selectOption('ja');
 await expect(event.locator('[data-dialogue-exchange]')).toHaveAttribute('data-l10n-native','ja');
 await expect(event.locator('.dialogue-words').last()).toContainText('諸将');
 expect(await read()).toEqual(original);
 await historyScreenshot(page,testInfo,'dialogue-opening-ja',{fullPage:false});
 await event.locator('[data-language-picker]').selectOption('zh-Hant');await tacticalDismiss(page);
 const [id,officer]=Object.entries(original.state.officers).find(([,row])=>row.person_id==='san14-candidate-0526');
 expect(officer.loyalty).toBeGreaterThanOrEqual(95);
 const city=Object.values(original.state.cities).find(row=>row.roster.officer_ids.includes(Number(id))).id;
 await page.locator('#city-jump').selectOption(city);
 if(await page.locator('#dialog').isVisible())await closeDialog(page);
 const details=page.locator('#city-roster-'+id);
 if(!await details.isVisible())await page.locator('details:has(#city-roster-'+id+') > summary').click();
 await details.click();
 const basis=page.locator(`#dialog [data-officer-relation="${id}"]:not([hidden])`);
 await expect(basis).toContainText('任用忠誠基準95');await expect(basis.locator('a')).not.toHaveCount(0);
 await page.locator('#dialog-language').selectOption('ja');await expect(basis).toContainText('任用時の忠誠基準95');
 await historyScreenshot(page,testInfo,'family-loyalty-basis-ja',{fullPage:false});
 expect(await read()).toEqual(original);
 await closeDialog(page);await openAllocation(page);
 await page.locator('#allocation-officer').selectOption(id);
 const current=await read(),maximum=Number(await page.locator('#allocation-troops').getAttribute('max'));
 const amount=Math.min(maximum,officer.troops+1);expect(amount).toBeGreaterThan(officer.troops);
 await page.locator('#allocation-troops').fill(String(amount));await page.locator('#confirm-allocation').click();await waitIdle(page);
 await expect(page.locator('#dialog')).toBeVisible();
 await closeDialog(page);
 await expect(page.locator('#journal [data-command-feedback="allocate"] .dialogue-turn')).toHaveCount(2);
 const after=await read();expect(after.state.officers[id].troops).toBe(amount);expect(after.state.rng).toEqual(current.state.rng);
 await historyScreenshot(page,testInfo,'dialogue-command-feedback',{fullPage:false});
 const preview=page.locator('#journal [data-dialogue-open]');
 const bounds=await preview.evaluate(node=>({height:node.getBoundingClientRect().height,available:document.querySelector('#journal').clientHeight}));
 expect(bounds.height).toBeLessThanOrEqual(bounds.available);
 await preview.click();await expect(page.locator('#dialog [data-locale-only="ja"] .dialogue-turn')).toHaveCount(2);
 await expect(page.locator('#dialog [data-locale-only="ja"] .dialogue-words').last()).toContainText('編制');
 await page.locator('#dialog-language').selectOption('zh-Hant');await expect(page.locator('#dialog-title')).toHaveText('軍情對白',{useInnerText:true});
 await expect(page.locator('#dialog [data-locale-only="zh-Hant"] .dialogue-words').last()).toContainText('編兵');
 await historyScreenshot(page,testInfo,'dialogue-command-expanded',{fullPage:false});
 expect(await read()).toEqual(after);await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});
