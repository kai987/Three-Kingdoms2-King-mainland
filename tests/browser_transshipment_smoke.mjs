/* Exercise real 304 custody and compact recovery in the published Worker. */
import assert from 'node:assert/strict';
import {mkdir,readFile} from 'node:fs/promises';
import path from 'node:path';
import {chromium,devices} from '../tools/browser-tests/node_modules/playwright/index.mjs';

const [fixture,output]=process.argv.slice(2);
assert.ok(fixture&&output,'Provide a generated 304 save fixture and screenshot directory');
const bytes=await readFile(fixture);
const root='http://127.0.0.1:'+Number(process.env.TK2_STATIC_TEST_PORT||18939)+'/Three-Kingdoms2-King-mainland/';
await mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chromium'});

async function idle(page){
 await page.waitForFunction(()=>!document.body.classList.contains('busy')
   && !document.querySelector('#load').disabled,null,{timeout:120000});
}
async function dismiss(page){
 const modal=page.locator('#event-dialog[open]');
 for(let i=0;await modal.isVisible()&&i<25;i++){
  const skip=modal.locator('[data-event-skip]');
  await (await skip.count()?skip:modal.locator('[data-event-next]')).click();
 }
}
async function load(page,file){
 await idle(page);
 await page.locator('#load').click();
 await page.locator('#save-file').setInputFiles({name:'transshipment-exercise.tk2.json',mimeType:'application/json',buffer:file});
 await page.locator('#dialog').waitFor({state:'hidden',timeout:120000});
 await idle(page);
}
async function panel(page){
 await page.locator('#city-jump').selectOption('yulin');
 const compact=page.locator('#inspector-compact-information');
 if(await compact.isVisible())await compact.click();
 else await page.locator('#city-information').click();
 await page.locator('#city-information-transshipment').click();
 return page.locator('[data-transshipment]');
}
async function state(page){
 return page.evaluate(()=>view.game.extension.transshipment.plans['1']);
}

try{
 for(const locale of ['zh-Hant','ja']){
  const touch=locale==='ja';
  const page=await browser.newPage(touch?devices['iPhone 13']:{viewport:{width:1280,height:800}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  await page.addLocatorHandler(page.locator('#event-dialog[open]'),()=>dismiss(page));
  const response=await page.goto(root);
  assert.equal(response.status(),200);
  await page.locator('#game-loading-start').click({timeout:180000});
  assert.equal(await page.locator('#transshipment-option').isChecked(),false);
  await load(page,bytes);
  await panel(page);
  await page.locator('#dialog-language').selectOption(locale);
  await page.waitForFunction(language=>document.documentElement.lang===language,locale);
  const area=page.locator('[data-transshipment]');
  assert.equal(await area.isVisible(),true);
  assert.match(await area.innerText(),touch?/実入庫/:/實際入倉/);
  const before=await state(page);
  assert.equal(before.batches.length,2);
  assert.ok(before.batches.every(b=>b.receipt?.grain>0));
  const river=area.locator('form[data-ts-send="1:2"]');
  assert.equal(await river.isVisible(),true);
  assert.match(await river.locator('..').innerText(),/100,000/);
  await page.locator('#dialog').screenshot({path:path.join(output,locale+'-collected.png')});
  await river.locator('button[type="submit"]').click();
  const confirmation=page.locator('#order-confirm-dialog');
  await confirmation.waitFor({timeout:90000});
  assert.equal(await confirmation.getAttribute('data-command-book-cost'),'1');
  await confirmation.locator('#order-confirm-accept').click();
  await page.waitForFunction(()=>view.game.extension.transshipment.plans['1'].batches.length===3,
   null,{timeout:120000});
  await idle(page);
  const sent=await state(page), water=sent.batches.at(-1);
  assert.ok(water.grain>50000);
  assert.equal(water.parents.length,2);
  assert.equal(water.parents.reduce((sum,p)=>sum+p[1],0),water.grain+water.rations);
  assert.equal(water.receipt,null);
  assert.equal(await page.locator('#dialog').evaluate(el=>el.scrollWidth <= el.clientWidth+3),true);
  await page.locator('#dialog').screenshot({path:path.join(output,locale+'-river-dispatched.png')});
  await page.locator('#dialog button[data-cancel]').click();
  const download=page.waitForEvent('download',{timeout:90000});
  await page.locator('#save').click();
  const file=await download;
  await load(page,await readFile(await file.path()));
  assert.deepEqual(await state(page),sent);
  await panel(page);
  assert.match(await area.innerText(),touch?/到着待ち/:/等待實際到貨/);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({locale,url:page.url(),title:await page.title(),viewport:page.viewportSize(),
   feederReceipts:before.batches.map(b=>b.receipt.grain),waterCargo:water.grain,waterRations:water.rations,
   actualRouteCapacity:water.capacity,saveRoundtrip:true,consoleErrors:errors}));
  await page.close();
 }
}finally{await browser.close();}
