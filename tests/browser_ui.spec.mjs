/* Shipped HTML + Worker + Pyodide in isolated Chromium contexts.
 * Campaign changes use visible controls, never injected game state.
 */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {readFile,mkdir} from 'node:fs/promises';
import {join} from 'node:path';

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

async function historyScreenshot(page,testInfo,name){
 const directory=process.env.TK2_HISTORY_SCREENSHOTS;
 if(directory)await mkdir(directory,{recursive:true});
 const path=directory?join(directory,`${testInfo.project.name}-${name}.png`):testInfo.outputPath(`${name}.png`);
 await page.screenshot({path,fullPage:true});
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
