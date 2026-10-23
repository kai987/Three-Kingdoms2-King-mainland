/* Shipped HTML + Worker + Pyodide in isolated Chromium contexts.
 * Campaign changes use visible controls, never injected game state.
 */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {readFile} from 'node:fs/promises';

const errors=new WeakMap();
test.beforeEach(async({page})=>{
 const observed=[];errors.set(page,observed);
 page.on('pageerror',error=>observed.push(error.message));
 page.on('console',message=>{if(message.type()==='error')observed.push(message.text());});
});
async function opening(page){
 await page.goto('./');
 await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
 await expect(page.locator('#game-engine-status')).toBeHidden();
 await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
}
async function closeDialog(page){await page.keyboard.press('Escape');await expect(page.locator('#dialog')).not.toBeVisible();}
async function openAllocation(page){await page.locator('#allocate').click();await expect(page.locator('#allocation-troops')).toBeVisible();}
async function waitIdle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
async function setTroops(page,value){
 await page.locator('#allocation-troops').fill(String(value));
 await page.locator('#confirm-allocation').click();
 await waitIdle(page);
 await expect(page.locator('#allocation-troops')).toHaveValue(String(value));
 await expect(page.locator('#dialog')).toBeVisible();
}

test('dialogs, language, limits, save/load and automatic recovery use the real campaign',async({page},testInfo)=>{
 await opening(page);
 await page.locator('#scenario').selectOption('mainland217-07');
 const shu=page.locator('input[name=faction][value=shu]');
 await expect(shu).toHaveCount(1);await shu.check();
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
 await page.reload();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
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
 await context.route('**/runtime/engine-manifest.json',async route=>{
  if(++manifestRequests===1)await route.fulfill({status:404,body:'controlled browser acceptance failure'});
  else await route.continue();
 });
 await page.goto('./');
 const retry=page.locator('#game-engine-status button');
 await expect(retry).toBeVisible();await expect(page.locator('#begin')).toHaveCount(0);
 await retry.click();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
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
 await page.locator('#transfer').click();
 await expect(page.locator('#transfer-city')).toBeVisible();
 await page.locator('#transfer-city').selectOption(target);
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
 expect(column.quote.routes.every(leg=>leg.mode==='land'&&!leg.hazard)).toBe(true);
 const units=initial.state.officers[officerText].troops+100;
 expect(loaded).toBe(Math.ceil(units*column.quote.days/1000));
 expect(column.supply).toMatchObject({loaded,consumed:0,remaining:loaded,elapsed_days:0});
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
 const elapsed=Math.min(10,column.quote.days),consumed=Math.ceil(units*elapsed/1000);
 expect(marched.supply).toMatchObject({loaded,consumed,remaining:loaded-consumed,elapsed_days:elapsed});
 // No delegate was appointed and no monthly income is due: all food spent
 // this turn comes out of the travelling bag, never the origin store again.
 expect(next.state.extension.domestic.factions.shu.civil).toBeNull();
 expect(next.state.extension.domestic.factions.shu.military).toBeNull();
 expect(next.state.cities[source].grain).toBe(departing.state.cities[source].grain);
 expect(next.state.cities[source].owner).toBe('shu');
 await expect(live).toHaveAttribute('data-supply-loaded',String(loaded));
 await expect(live).toHaveAttribute('data-supply-consumed',String(consumed));
 await expect(live).toHaveAttribute('data-supply-remaining',String(loaded-consumed));
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
 for(const [mode,count] of [['giant',4],['large',12],['all',110],['none',0],['major',majorCount]]){
  await labels.click();await expect(labels).toHaveAttribute('data-label-mode',mode);await expect(names).toHaveCount(count);
 }
 await labels.click();await labels.click();
 await page.locator('#scenario').selectOption('mainland225-07');
 await expect(labels).toHaveAttribute('data-label-mode','large');await expect(names).toHaveCount(13);
 await page.locator('#scenario').selectOption('mainland217-07');await expect(names).toHaveCount(12);
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
