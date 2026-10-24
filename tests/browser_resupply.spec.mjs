/* Actual controls and HTTP domain services, with a controlled scenario input. */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {readFile} from 'node:fs/promises';

const errors=new WeakMap();
test.beforeEach(async({page})=>{
 const messages=[];errors.set(page,messages);
 page.on('pageerror',error=>messages.push(error.message));
 page.on('console',message=>{if(['error','warning'].includes(message.type()))messages.push(message.text());});
 await page.goto('./');await page.waitForSelector('#begin, #end-turn, #run-ai, #process-arrivals');
 if(!await page.locator('#begin').count())await page.locator('#main-menu').click();
 await expect(page.locator('#begin')).toBeEnabled();
 await page.locator('input[name=faction][value=shu]').check();await page.locator('#begin').click();
 await expect(page.locator('#end-turn')).toBeEnabled();await expect(page.locator('#event-dialog')).toBeVisible();await dismissEvents(page);
});
async function idle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
async function dismissEvents(page){
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const modal=page.locator('#event-dialog');
 if(await modal.isVisible()){
  const skip=modal.locator('[data-event-skip]');await (await skip.count()?skip:modal.locator('[data-event-next]')).click();
  await expect(modal).not.toBeVisible();
 }
}
async function saved(page){
 const download=page.waitForEvent('download');await page.locator('#save').click();
 return JSON.parse(await readFile(await(await download).path(),'utf8'));
}
async function nextTurn(page){
 await page.locator('#end-turn').click();await idle(page);await dismissEvents(page);
 await expect(page.locator('#run-ai')).toBeEnabled();await page.locator('#run-ai').click();
 await idle(page);await dismissEvents(page);
}
async function arrivals(page){
 if(await page.locator('#process-arrivals').isVisible()){
  await page.locator('#process-arrivals').click();await idle(page);await dismissEvents(page);
 }
}
async function openLogistics(page){
 await page.locator('#city-command-tab-warehouse').click();
 await expect(page.locator('#city-command-panel-warehouse')).toBeVisible();
 await page.locator('#city-logistics').click();
}
async function depart(page){
 await page.locator('#city-jump').selectOption('nanyang');const initial=await saved(page);
 await page.locator('#transfer').click();await page.locator('#transfer-city').selectOption('bajun');
 const ruler=String(initial.state.extension.leaders.shu),officer=page.locator(`input[name=transfer-officer]:enabled:not([value="${ruler}"])`).first();
 const ident=await officer.getAttribute('value');await officer.check();
 const food=page.locator('#transfer-supply [data-supply-loaded]'),loaded=Number(await food.getAttribute('data-supply-loaded')),
  units=initial.state.officers[ident].troops+100;
 expect(loaded).toBe(Math.ceil(units*10/1000));expect(loaded).toBeLessThan(Math.ceil(units*30/1000));
 await page.locator('#confirm-transfer').click();await idle(page);await expect(page.locator('#dialog')).not.toBeVisible();
 const after=await saved(page),column=after.state.extension.travel.marches[0];
 expect(column.quote.path).toEqual(['nanyang','nanjun','bajun']);expect(column.supply.loaded).toBe(loaded);
 return {initial,ident,column};
}

test('a real courier feeds a waiting column at a city and its escorts return home',async({page},testInfo)=>{
 const {ident,column}=await depart(page);await nextTurn(page);
 let snapshot=await saved(page),army=snapshot.state.extension.travel.marches.find(row=>row.id===column.id);
 expect(army.supply.route_days).toBe(10);expect(army.supply.remaining).toBe(0);
 await page.locator('#city-jump').selectOption('jiangxia');
 await openLogistics(page);await expect(page.locator('#rescue-target')).toBeVisible();
 await page.locator('#rescue-target').selectOption(String(column.id));
 const input=page.locator('#rescue-grain'),maximum=Number(await input.getAttribute('max'));
 expect(maximum).toBeGreaterThanOrEqual(20);
 await input.fill('999999999');await expect(input).toHaveValue(String(maximum));
 await input.fill('-1');await expect(input).toHaveValue('0');await expect(page.locator('#dispatch-rescue')).toBeDisabled();
 await page.locator('#rescue-max').click();await expect(input).toHaveValue(String(maximum));
 await input.fill('20');
 await page.locator('#dialog-language').selectOption('ja');await expect(input).toHaveValue('20');
 await expect(page.locator('[data-rescue-rule]')).toContainText('遠隔で即時加算はしません');
 await page.locator('#dialog-language').selectOption('zh-Hant');await expect(input).toHaveValue('20');
 await input.scrollIntoViewIfNeeded();
 const box=await page.locator('#dialog').boundingBox();
 expect(box.x).toBeGreaterThanOrEqual(0);expect(box.x+box.width).toBeLessThanOrEqual(page.viewportSize().width);
 await page.screenshot({path:testInfo.outputPath('resupply-selection.png')});
 await expect(page.locator('#dispatch-rescue')).toBeEnabled();await page.locator('#dispatch-rescue').click();await idle(page);
 await expect(page.locator('.domestic-saved')).toContainText('運輸隊已出發');
 await page.keyboard.press('Escape');await expect(page.locator('#dialog')).not.toBeVisible();await dismissEvents(page);
 snapshot=await saved(page);const convoy=snapshot.state.extension.logistics.convoys[0],escorts=convoy.officers.map(String);
 expect(convoy.target_march).toBe(column.id);expect(convoy.cargo.grain).toBe(20);
 expect(snapshot.state.extension.travel.marches[0].supply.received).toBe(0,'Dispatching is not remote food delivery');
 for(const escort of escorts)expect(snapshot.state.cities.jiangxia.roster.officer_ids.map(String)).toContain(escort);
 await nextTurn(page);await arrivals(page);snapshot=await saved(page);
 army=snapshot.state.extension.travel.marches.find(row=>row.id===column.id);
 expect(army.supply.received).toBeGreaterThanOrEqual(20);
 expect(army.supply.refills.some(row=>row.kind==='convoy'&&row.grain===20)).toBe(true);
 expect(army.supply.shortage_days).toBeGreaterThan(0);expect(army.supply.shortage_days).toBeLessThan(10);
 expect(army.supply.route_days).toBeGreaterThan(10);expect(army.supply.retreat_requested).toBe(false);
 expect(snapshot.state.officers[ident].alive).toBe(true);
 const returning=snapshot.state.extension.logistics.convoys.find(row=>row.id===convoy.id);
 expect(returning.delivery_done).toBe(true);expect(returning.delivered.grain).toBe(20);expect(returning.status).toBe('returning');
 expect(returning.target).toBe('jiangxia');
 for(const escort of escorts){
  expect(snapshot.state.cities.jiangxia.roster.officer_ids.map(String)).toContain(escort);
  expect(snapshot.state.cities.nanjun.roster.officer_ids.map(String)).not.toContain(escort);
 }
 await page.locator('#city-jump').selectOption('jiangxia');await openLogistics(page);
 const convoyInfo=page.locator(`[data-convoy="${convoy.id}"]`);
 await expect(convoyInfo).toContainText('押運返程中');
 await convoyInfo.scrollIntoViewIfNeeded();await expect(convoyInfo).toBeInViewport();
 await page.screenshot({path:testInfo.outputPath('resupply-rendezvous.png')});
 await page.keyboard.press('Escape');await dismissEvents(page);await nextTurn(page);await arrivals(page);
 snapshot=await saved(page);expect(snapshot.state.extension.logistics.convoys.some(row=>row.id===convoy.id)).toBe(false);
 for(const escort of escorts)expect(snapshot.state.cities.jiangxia.roster.officer_ids.map(String)).toContain(escort);
 expect(errors.get(page)).toEqual([]);
});

test('a column without rescue loses troops and begins a real return after ten shortage days',async({page},testInfo)=>{
 const {ident,column}=await depart(page);await nextTurn(page);const before=await saved(page);
 await nextTurn(page);const after=await saved(page),retreat=after.state.extension.travel.marches.find(row=>row.id===column.id);
 expect(retreat.status).toBe('returning');expect(retreat.target).toBe('nanyang');expect(retreat.journey_source).toBe('nanjun');
 expect(retreat.supply.route_days).toBe(0);expect(retreat.quote.days).toBe(10);
 expect(retreat.history.at(-1).supply.shortage_days).toBe(10);
 expect(after.state.officers[ident].troops).toBeLessThan(before.state.officers[ident].troops);
 expect(after.state.officers[ident].alive).toBe(true);
 const returnInfo=page.locator(`[data-march="${column.id}"]`);
 await expect(returnInfo.locator('[data-march-status]')).toContainText('撤退返程中',{useInnerText:true});
 await returnInfo.scrollIntoViewIfNeeded();await expect(returnInfo).toBeInViewport();
 await page.screenshot({path:testInfo.outputPath('starvation-retreat.png')});
 expect(errors.get(page)).toEqual([]);
});
