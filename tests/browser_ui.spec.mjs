/* Shipped HTML + Worker + Pyodide in isolated Chromium contexts.
 * Campaign changes use visible controls, never injected game state.
 */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {readFile,mkdir} from 'node:fs/promises';
import {join} from 'node:path';
import assert from 'node:assert/strict';

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
 const prefects=[['changsha','han_xuan','韓玄'],['wuling','jin_xuan','金旋'],
  ['guiyang','zhao_fan','趙範'],['lingling','liu_du','劉度']];
 const fills=[];
 for(const[city,side,name]of prefects){
  await expect(page.locator(`input[name=faction][value=${side}]`)).toHaveCount(1);
  await expect(page.locator(`input[name=faction][value=${side}]`).locator('..')).toContainText(name);
  await expect(marker(city)).toHaveAttribute('data-owner',side);
  await expect(marker(city)).toHaveAttribute('aria-label',new RegExp(name));
  const fill=await marker(city).locator('.castle-fill').getAttribute('fill');
  expect(fill).not.toBe('#ffffff');fills.push(fill);
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
 await expect(page.locator('#inspector .roster-table tbody tr')).toHaveCount(2);
 // Keyboard activation exercises the map's accessible city button on both
 // viewports, without forced clicks through the compact map toolbar.
 await marker('changsha').focus();await page.keyboard.press('Enter');
 const information=page.locator('.city-information[data-inspected-city=changsha]');
 await expect(information).toHaveAttribute('data-information-mode','live');
 await expect(information).toBeVisible();
 const ruler=information.locator('.roster-table tbody tr').filter({hasText:'韓玄'});
 await expect(ruler).toHaveCount(1);await expect(ruler.locator('td').nth(5)).toHaveText('--');
 await expect(information.locator('.roster-table tbody tr').filter({hasText:'黃忠'})).toHaveCount(1);
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
 await page.locator('#scenario').selectOption('mainland211-07');
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

test('four DLC openings share two translated categories and preserve distinct same-month campaigns',async({page},testInfo)=>{
 await opening(page);
 const scenarios=page.locator('#scenario'),groups=scenarios.locator('optgroup');
 await expect(groups).toHaveCount(2);
 expect(await groups.evaluateAll(nodes=>nodes.map(node=>node.label))).toEqual(['史實','假想']);
 const marker=id=>page.locator(`#world-map .city-hit[data-city="${id}"]`);
 // Both July 211 campaigns must remain individually selectable; a shared
 // date is not a scenario ID and must never replace the existing opening.
 await expect(scenarios.locator('option[value="mainland211-07"]')).toContainText('入蜀爭奪戰');
 await expect(scenarios.locator('option[value="mainland211-07-tongguan"]')).toContainText('潼關之戰');
 await scenarios.selectOption('mainland211-07');
 await expect(scenarios.locator('option:checked')).toContainText('入蜀爭奪戰');
 await expect(page.locator('#map-date')).toHaveAttribute('datetime','0211-07-01');
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
 await page.locator('#transfer').click();
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
 expect(column.quote.routes[0].river_segments.map(row=>row.speed_km_per_day)).toEqual([20,22.5]);
 expect(saved.state.rng).toEqual(initial.state.rng);
 expect(saved.state.officers[ident].troops).toBe(initial.state.officers[ident].troops);
 await page.reload();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
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
 await context.route('**/app.js',async route=>{
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
 const loyalty=(person,owner,ruler)=>ruler?100:!owner?0:
  Number.isInteger(person.initialization.source_loyalty?.value)&&person.initialization.source_loyalty.faction_ids.includes(owner)?person.initialization.source_loyalty.value:80;
 await opening(page);
 const scenarios=await page.locator('#scenario option').evaluateAll(rows=>rows.map(row=>row.value));
 expect(scenarios).toHaveLength(29);
 let checkedServing=0,checkedFree=0;
 for(const scenario of scenarios){
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
   assert.equal(officer.loyalty,loyalty(person,city.owner,officer.is_ruler),`${scenario}/${officer.person_id} preview loyalty`);
   assert.equal(officer.virtue,person.profile.virtue,`${scenario}/${officer.person_id} preview virtue`);
  }
  const representative=previews.find(city=>city.officers.length);
  expect(representative).toBeTruthy();
  await page.locator('#city-jump').selectOption(representative.id);
  const info=page.locator(`.city-information[data-inspected-city="${representative.id}"]`);
  await expect(info).toHaveAttribute('data-information-mode','preview');
  const first=representative.officers[0],row=info.locator('.roster-table tbody tr').first();
  await expect(row.locator('td').nth(5)).toHaveText(first.is_ruler?'--':String(first.loyalty));
  await expect(row.locator('td').nth(7)).toHaveText(String(first.health));
  await closeDialog(page);
  await page.locator('#begin').click();
  await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
  await waitIdle(page);await dismissHistoryOpening(page);
  const download=page.waitForEvent('download');await page.locator('#save').click();
  const saved=JSON.parse(await readFile(await(await download).path(),'utf8'));
  expect(saved.scenario).toBe(scenario);
  const leaders=new Set(Object.values(saved.state.extension.leaders).map(String));
  for(const[ident,officer]of Object.entries(saved.state.officers)){
   const person=people[officer.person_id];
   assert.ok(person,`${scenario}/${officer.person_id} historical identity`);
   assert.equal(officer.health,person.initialization.health,`${scenario}/${officer.person_id} live health`);
   assert.ok(officer.profile.health_max>=officer.health,`${scenario}/${officer.person_id} live health cap`);
   assert.equal(officer.loyalty,loyalty(person,officer.faction_id,leaders.has(ident)),`${scenario}/${officer.person_id} live loyalty`);
   assert.equal(officer.profile.virtue,person.profile.virtue,`${scenario}/${officer.person_id} live virtue`);
   if(officer.faction_id)checkedServing++;else checkedFree++;
  }
  for(const city of previews)for(const officer of city.officers){
   const live=saved.state.officers[officer.id];
   assert.equal(live.health,officer.health,`${scenario}/${officer.person_id} preview-live health`);
   assert.equal(live.loyalty,officer.loyalty,`${scenario}/${officer.person_id} preview-live loyalty`);
  }
  await page.locator('#main-menu').click();
  await expect(page.locator('#begin')).toBeEnabled();
 }
 // This stat-only update must retain all existing opening memberships.
 expect(checkedServing).toBe(8854);expect(checkedFree).toBe(2320);
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
 await page.locator('#recruit-officer').click();
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
  await page.locator('#city-jump').selectOption(city);await page.locator('#city-treasury').click();
  await expect(page.locator(`[data-treasury-dialog][data-treasury-city="${city}"]`)).toBeVisible();
 };
 const events=async name=>{
  await closeDialog(page);
  const event=page.locator('#event-dialog');await expect(event).toBeVisible();
  await expect(event.locator('.event-treasure')).toBeVisible();
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
 await page.locator('#city-treasury').click();
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
 await expect(page.locator('#treasury-reward')).toBeDisabled();
 await expect(page.locator('#dialog [data-city-treasure]')).toHaveText('5');
 const rewarded=await save();
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
 await expect(page.locator('#treasury-search')).toBeDisabled();await events('search');
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
 await page.locator('#city-logistics').click();await expect(page.locator('[data-treasure-transport]')).toBeVisible();
 await expect(page.locator('#logistics-enabled')).not.toBeChecked();
 await page.locator('#treasure-transport-target').selectOption(target);
 await page.locator('#treasure-transport-amount').fill('999999');await expect(page.locator('#treasure-transport-amount')).toHaveValue('6');
 await page.locator('#treasure-transport-max').click();await expect(page.locator('#treasure-transport-amount')).toHaveValue('6');
 await page.locator('#dialog-language').selectOption('ja');await expect(page.locator('#treasure-transport-amount')).toHaveValue('6');
 expect(await state()).toEqual(before,'A manual shipment preview and language change cannot move treasure or consume RNG');
 await expect(page.locator('#dispatch-treasure')).toBeEnabled();await page.locator('#dispatch-treasure').click();await waitIdle(page);
 const departing=await state(),convoy=departing.state.extension.logistics.convoys.find(row=>row.source===source&&row.target===target);
 expect(convoy).toMatchObject({owner:'shu',status:'outbound',officers:[595],cargo:{gold:0,grain:0,reserves:0,treasure:6},delivery_done:false});
 expect(convoy.journeys[0].quote.days).toBe(45);
 expect(convoy.journeys[0].supply).toMatchObject({loaded:4,consumed:0,remaining:4});
 expect(departing.state.cities[source].grain).toBe(before.state.cities[source].grain-4);
 expect(departing.state.extension.treasury.cities[source].treasure).toBe(0);
 expect(departing.state.extension.treasury.cities[target].treasure).toBe(4,'Cargo is not delivered instantly');
 expect(departing.state.rng).toEqual(before.state.rng,'This safe land dispatch has no weather RNG draw');
 expect(departing.state.extension.logistics.cities[source].policy.enabled).toBe(false);
 await historyScreenshot(page,testInfo,'treasure-convoy-departure-ja');
 await closeDialog(page);
 const event=page.locator('#event-dialog');await expect(event).toBeVisible();await expect(event.locator('.event-art svg')).toBeVisible();
 await expect(event.locator('#event-description')).toContainText(/宝6|寶6/,{useInnerText:true});
 const skip=event.locator('[data-event-skip]');await (await skip.count()?skip:event.locator('[data-event-next]')).click();await expect(event).not.toBeVisible();
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');
 await page.reload();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});await page.locator('#load').click();await page.locator('#load-local').click();
 await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const restored=page.waitForEvent('download');await page.locator('#save').click();expect(await readFile(await(await restored).path(),'utf8')).toBe(raw);
 await page.locator('#city-jump').selectOption(source);await page.locator('#city-logistics').click();
 await expect(page.locator('#dialog')).toContainText(/宝\s*6|寶\s*6/,{useInnerText:true});
 await historyScreenshot(page,testInfo,'treasure-convoy-restored-ja');await closeDialog(page);
 expect(errors.get(page)).toEqual([]);
});

test('facility visits, trade, study, equipment, prevention and town development share bounded real actions and saves',async({page},testInfo)=>{
 await opening(page);await page.locator('#scenario').selectOption('mainland217-07');
 await page.locator('input[name=faction][value=shu]').check();await page.locator('#begin').click();
 await expect(page.locator('#city-facilities')).toBeEnabled({timeout:90_000});await waitIdle(page);await dismissHistoryOpening(page);
 const read=()=>page.evaluate(async()=>{
  const saved=await fetch('/api/save'),shown=await fetch('/api/state');
  if(!saved.ok||!shown.ok)throw new Error('Read-only facility view failed');
  const value=await shown.json();return {save:await saved.json(),facilities:(value.view||value).catalog.facilities};
 });
 const chooseCity=(snapshot,predicate)=>Object.entries(snapshot.facilities.cities).find(([id,row])=>row.owner==='shu'&&row.can_act&&predicate(row,snapshot.save.state.cities[id]));
 const open=async id=>{await page.locator('#city-jump').selectOption(id);await page.locator('#city-facilities').click();await expect(page.locator(`[data-facilities-dialog][data-facilities-city="${id}"]`)).toBeVisible();};
 const events=async(label,kind)=>{
  await closeDialog(page);const modal=page.locator('#event-dialog');await expect(modal).toBeVisible();
  await expect(modal.locator('#event-title')).not.toBeEmpty();await expect(modal.locator('.event-map')).toBeVisible();await expect(modal.locator('.event-facility')).toBeVisible();
  const latest=await read();expect(latest.save.state.extension.events.items.some(row=>row.kind===kind)).toBe(true);
  await historyScreenshot(page,testInfo,`facility-${label}-event`,{fullPage:false});
  const skip=modal.locator('[data-event-skip]');await (await skip.count()?skip:modal.locator('[data-event-next]')).click();await expect(modal).not.toBeVisible();
 };
 let before=await read();const clinic=chooseCity(before,row=>row.town===1&&row.patients.some(p=>p.can_treat))||chooseCity(before,row=>row.patients.some(p=>p.can_treat));
 expect(clinic).toBeTruthy();await open(clinic[0]);
 await expect(page.locator('#dialog-title')).toBeInViewport();
 const dimensions=await page.locator('#dialog').evaluate(node=>({top:node.getBoundingClientRect().top,bottom:node.getBoundingClientRect().bottom,viewport:innerHeight,scrollTop:node.scrollTop,scrollWidth:node.scrollWidth,clientWidth:node.clientWidth}));
 expect(dimensions.top).toBeGreaterThanOrEqual(0);expect(dimensions.bottom).toBeLessThanOrEqual(dimensions.viewport+1);expect(dimensions.scrollTop).toBe(0);expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth+1);
 await historyScreenshot(page,testInfo,'facilities-opening-viewport',{fullPage:false});
 const patient=await page.locator('#facility-patient').inputValue(),actor=await page.locator('#facility-actor').inputValue(),clinicQuote=clinic[1].patients.find(row=>String(row.id)===patient);
 expect(clinicQuote.can_treat).toBe(true);await expect(page.locator('#facility-patient option:checked')).toContainText(/兵.*武.*知.*德.*忠.*體/);
 await page.locator('.facility-policy > summary').click();await page.locator('#facility-policy-gold_budget').fill('321');
 await page.locator('#facility-policy-grain_floor').fill('5000');await page.locator('#facility-policy-grain_target').fill('1');
 await expect(page.locator('#facility-policy-grain_target')).toHaveValue('5000');
 await page.locator('#dialog-language').selectOption('ja');await expect(page.locator('#dialog-title')).toContainText('施設と防災');
 await expect(page.locator('#facility-policy-gold_budget')).toHaveValue('321');await expect(page.locator('.facility-policy')).toHaveAttribute('open','');
 expect((await read()).save).toEqual(before.save,'Facility inspection, policy drafts and language must not spend or draw RNG');
 await page.locator('#facility-treat').click();await waitIdle(page);let after=await read();
 expect(after.save.state.cities[clinic[0]].gold).toBe(before.save.state.cities[clinic[0]].gold-clinicQuote.gold);
 expect(after.save.state.officers[patient].health).toBeGreaterThanOrEqual(clinicQuote.after_min);expect(after.save.state.officers[patient].health).toBeLessThanOrEqual(clinicQuote.after_max);
 expect(after.save.state.rng.draws).toBe(before.save.state.rng.draws+1);
 expect(after.save.state.cities[clinic[0]].action_used).toBe(true);expect(after.save.state.extension.officer_actions[actor]).toBe(after.save.state.turn);
 await expect(page.locator('#facility-treat')).toBeDisabled();await expect(page.locator('#facility-prevent')).toBeDisabled();await expect(page.locator('#facility-policy-gold_budget')).toHaveValue('321');
 await page.locator('#facility-save-policy').click();await waitIdle(page);const configured=await read();
 expect(configured.save.state.extension.facilities.factions.shu).toMatchObject({enabled:false,gold_budget:321,grain_floor:5000,grain_target:5000});
 expect(configured.save.state.rng).toEqual(after.save.state.rng);await events('clinic-ja','officer_treated');
 before=await read();const market=chooseCity(before,row=>row.town===1&&row.trade.buy.max_batches>1)||chooseCity(before,row=>row.trade.buy.max_batches>1);expect(market).toBeTruthy();await open(market[0]);
 await page.locator('#facility-service').selectOption('market');await page.locator('#facility-trade-batches').fill('999999999');
 await expect(page.locator('#facility-trade-batches')).toHaveValue(String(market[1].trade.buy.max_batches));await page.locator('#facility-trade-max').click();
 const batches=Math.min(2,market[1].trade.buy.max_batches);await page.locator('#facility-trade-batches').fill(String(batches));await page.locator('#dialog-language').selectOption('zh-Hant');
 await expect(page.locator('#facility-trade-batches')).toHaveValue(String(batches));expect((await read()).save).toEqual(before.save);
 await page.locator('#facility-trade').click();await waitIdle(page);after=await read();
 expect(after.save.state.cities[market[0]].gold).toBe(before.save.state.cities[market[0]].gold-batches*market[1].trade.buy.rate);
 expect(after.save.state.cities[market[0]].grain).toBe(before.save.state.cities[market[0]].grain+batches*market[1].trade.buy.batch_grain);expect(after.save.state.rng).toEqual(before.save.state.rng);
 await expect(page.locator('#facility-trade')).toBeDisabled();await events('market-tc','grain_traded');
 before=await read();const school=chooseCity(before,row=>row.services.includes('school')&&row.students.some(s=>s.can_study));expect(school).toBeTruthy();await open(school[0]);await page.locator('#facility-service').selectOption('school');
 const student=await page.locator('#facility-student').inputValue(),studyQuote=school[1].students.find(row=>String(row.id)===student);expect(studyQuote.can_study).toBe(true);
 await expect(page.locator('#facility-study-preview')).toContainText(String(studyQuote.gold));await page.locator('#facility-study').click();await waitIdle(page);after=await read();
 const learned=after.save.state.officers[student].profile.intellect;
 expect(learned).toBeGreaterThanOrEqual(studyQuote.after_min);expect(learned).toBeLessThanOrEqual(studyQuote.after_max);
 expect(after.save.state.cities[school[0]].gold).toBe(before.save.state.cities[school[0]].gold-studyQuote.gold);expect(after.save.state.rng.draws).toBe(before.save.state.rng.draws+1);
 expect(after.save.state.extension.facilities.study[student]).toBe((before.save.state.extension.facilities.study[student]||0)+learned-studyQuote.before);
 await expect(page.locator('#facility-study')).toBeDisabled();await events('school-tc','officer_studied');
 before=await read();const armory=chooseCity(before,row=>row.services.includes('armory')&&row.stock.weapon.some(item=>item.can_buy&&item.eligible_targets.length));expect(armory).toBeTruthy();await open(armory[0]);await page.locator('#facility-service').selectOption('armory');
 const item=armory[1].stock.weapon.find(item=>item.can_buy&&item.eligible_targets.length),recipient=String(item.eligible_targets[0]);
 await page.locator('#facility-equipment-officer').selectOption(recipient);await page.locator('#facility-equipment-item').selectOption(String(item.id));
 await expect(page.locator('#facility-equipment-buy')).toBeEnabled();await page.locator('#facility-equipment-buy').click();await waitIdle(page);after=await read();
 expect(after.save.state.officers[recipient].weapon_id).toBe(item.id);expect(after.save.state.cities[armory[0]].gold).toBe(before.save.state.cities[armory[0]].gold-item.price);expect(after.save.state.rng).toEqual(before.save.state.rng);
 await expect(page.locator('#facility-equipment-buy')).toBeDisabled();await events('equipment-tc','equipment_bought');
 before=await read();const prevention=chooseCity(before,row=>Object.values(row.prevention_quotes).some(q=>q.can_prevent));expect(prevention).toBeTruthy();await open(prevention[0]);
 const engineer=await page.locator('#facility-actor').inputValue(),preventionQuote=prevention[1].prevention_quotes[engineer];expect(preventionQuote.can_prevent).toBe(true);
 await expect(page.locator('#facility-prevention-preview')).toContainText(String(preventionQuote.gold_min));await page.locator('#dialog-language').selectOption('ja');expect((await read()).save).toEqual(before.save);
 await page.locator('#facility-prevent').click();await waitIdle(page);after=await read();
 const protectedCity=after.save.state.extension.facilities.cities[prevention[0]],expense=before.save.state.cities[prevention[0]].gold-after.save.state.cities[prevention[0]].gold;
 expect(expense).toBeGreaterThanOrEqual(preventionQuote.gold_min);expect(expense).toBeLessThanOrEqual(preventionQuote.gold_max);
 expect(protectedCity.preparedness).toBeGreaterThanOrEqual(preventionQuote.preparedness_min);expect(protectedCity.preparedness).toBeLessThanOrEqual(preventionQuote.preparedness_max);
 expect(protectedCity.damage).toBeGreaterThanOrEqual(preventionQuote.damage_min);expect(protectedCity.damage).toBeLessThanOrEqual(preventionQuote.damage_max);expect(after.save.state.rng.draws).toBe(before.save.state.rng.draws+2);
 await expect(page.locator('#facility-prevent')).toBeDisabled();await events('prevention-ja','prevention_improved');
 before=await read();const town=chooseCity(before,row=>row.develop.can_develop);expect(town).toBeTruthy();await open(town[0]);
 await page.locator('#facility-develop').click();await waitIdle(page);after=await read();
 expect(after.save.state.extension.facilities.cities[town[0]].town).toBe(town[1].develop.to_town);expect(after.save.state.cities[town[0]].gold).toBe(before.save.state.cities[town[0]].gold-town[1].develop.gold);expect(after.save.state.rng).toEqual(before.save.state.rng);
 await expect(page.locator('#facility-develop')).toBeDisabled();await expect(page.locator('#facility-service option[value=school]')).toHaveCount(1);await expect(page.locator('#facility-service option[value=armory]')).toHaveCount(1);await events('development-ja','town_developed');
 const download=page.waitForEvent('download');await page.locator('#save').click();const raw=await readFile(await(await download).path(),'utf8');
 await page.reload();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});await page.locator('#load').click();await page.locator('#load-local').click();await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
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
 await page.reload();await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});await page.locator('#load').click();await page.locator('#load-local').click();await waitIdle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const restored=page.waitForEvent('download');await page.locator('#save').click();expect(await readFile(await(await restored).path(),'utf8')).toBe(raw);
 expect((await read()).save).toEqual(current.save,'Loading an August save cannot settle the same monthly drought twice');
 expect(errors.get(page)).toEqual([]);
});
