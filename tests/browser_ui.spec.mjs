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
 await expect(page.locator('#dialog-title')).toContainText('兵の編制');
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
 await expect(page.locator('#dialog-title')).toHaveText('復元の確認');
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
