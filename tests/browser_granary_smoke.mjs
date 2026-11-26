/* Real desktop and touch acceptance against the packaged static worker. */
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {chromium} from '../tools/browser-tests/node_modules/playwright/index.mjs';

const [fixture,output]=process.argv.slice(2);
const version=Number(process.env.TK2_GRANARY_TEST_VERSION||302);
const candidate=version===3021;
const url=`http://127.0.0.1:${Number(process.env.TK2_STATIC_TEST_PORT||18917)}/Three-Kingdoms2-King-mainland/`;
const file=await readFile(fixture);
await mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chromium',headless:true});

async function idle(page){
 await page.waitForFunction(()=>document.querySelector('#load')&&!document.querySelector('#load').disabled,null,{timeout:120000});
}
async function dismissEvents(page){
 const modal=page.locator('#event-dialog');
 for(let n=0;n<30&&await modal.isVisible();n++){
  const skip=modal.locator('[data-event-skip]');
  await (await skip.count()?skip:modal.locator('[data-event-next]')).click();
 }
}
async function inspect(page,city){
 const info=page.locator(`[data-inspected-city="${city}"]`);
 await page.locator('#city-jump').selectOption(city);
 const control=page.locator('#city-information');
 if(!await control.isVisible())await page.locator('#inspector-toggle').click();
 await control.click();
 await info.waitFor({timeout:90000});
 await info.locator('#city-information-strategic-granary').click();
 const granary=page.locator('[data-strategic-granary]');
 await granary.waitFor();
 return granary;
}
async function economicState(page){
 return page.evaluate(()=>({
  revision:view.revision, source:view.game.cities.wujun.grain,target:view.game.cities.kuaiji.grain,
  sourceGold:view.game.cities.wujun.gold,market:view.game.extension.grain_market.wujun.stock,
  rng:view.game.rng,books:view.catalog.command_books.factions.wu.remaining
 }));
}
try{
 for(const [locale,viewport] of [['zh-Hant',{width:1280,height:800}],['ja',{width:390,height:844}]]){
  const page=await browser.newPage({viewport,hasTouch:locale==='ja',isMobile:locale==='ja'});
  const errors=[],warnings=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',entry=>{
   if(entry.type()==='error')errors.push(entry.text());
   if(entry.type()==='warning')warnings.push(entry.text());
  });
  await page.addLocatorHandler(page.locator('#event-dialog[open]'),()=>dismissEvents(page));
  await page.goto(url);
  const start=page.locator('#game-loading-start');
  await start.waitFor({timeout:180000});
  await start.click();
  await page.locator('#game-loading-cover').waitFor({state:'hidden'});
  assert.equal(page.url(),url);
  assert.match(await page.title(),/三國·大陸戰役|三国志・大陸戦役/);
  const experiment=page.locator('#strategic-granary-option');
  assert.equal(await experiment.isChecked(),false);
  for(const id of ['strategic-granary-candidate','strategic-dispatch','strategic-winter','strategic-relay']){
   assert.equal(await page.locator(`#${id}-option`).isDisabled(),true);
  }
  await experiment.check();
  if(candidate)await page.locator('#strategic-granary-candidate-option').check();
  await page.locator('#strategic-dispatch-option').check();
  await page.locator('#begin').click();
  await experiment.waitFor({state:'hidden',timeout:120000});
  await idle(page);
  assert.equal(await page.evaluate(()=>view.game.extension.strategic_granary_rules_version),version);
  assert.deepEqual(await page.evaluate(()=>view.game.extension.strategic_granary.features),
    {proactive:true,relay:false,winter:false,...(candidate?{coordination:true,return_safety:true}:{})});
  assert.equal(await page.evaluate(()=>view.game.extension.regional_market_rules_version),undefined);

  await page.locator('#load').click();
  await page.locator('#save-file').setInputFiles({name:'granary-controlled-fixture.json',mimeType:'application/json',buffer:file});
  await page.locator('#dialog').waitFor({state:'hidden',timeout:120000});
  await idle(page);
  const target='kuaiji';
  const panel=await inspect(page,target);
  const dialog=page.locator('#dialog');
  await page.locator('#dialog-language').selectOption(locale);
  await page.waitForFunction(lang=>document.documentElement.lang===lang,locale);
  assert.match(await dialog.locator('#dialog-title').innerText(),locale==='ja'?/戦略備蓄/:/戰略糧倉/);
  assert.equal(await panel.locator('tbody tr').count(),9);
  if(candidate){
   assert.match(await panel.innerText(),locale==='ja'?/補給後も残る不足量/:/未覆蓋缺口/);
  }
  assert.equal(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+3),true);
  await panel.locator('#granary-source').selectOption('wujun');
  await panel.locator('#granary-transfer-amount').fill('4000');
  const before=await economicState(page);
  await panel.locator('#granary-transfer-form button[type=submit]').click();
  const quote=panel.locator('[data-granary-quote="0"]'),first=panel.locator('#granary-preview-quotes li').first();
  await quote.waitFor({timeout:90000});
  assert.deepEqual(await economicState(page),before);
  assert.match(await first.innerText(),locale==='ja'?/往路.+復路/s:/去程.+返程/s);
  await quote.scrollIntoViewIfNeeded();
  await dialog.screenshot({path:path.join(output,`granary-${locale}-quote.png`)});
  await quote.click();
  const order=panel.locator('[data-granary-order="1"]');
  await order.waitFor({timeout:90000});
  const held=await economicState(page);
  assert.equal(held.source,before.source);
  assert.equal(held.target,before.target);
  assert.equal(held.books,before.books);

  await order.locator('[data-granary-dispatch]').click();
  const approval=page.locator('#order-confirm-dialog');
  await approval.waitFor();
  assert.equal(await approval.getAttribute('data-command-book-cost'),'1');
  await approval.locator('#order-confirm-accept').click();
  await page.waitForFunction(()=>view.game.extension.strategic_granary.orders['1']?.convoy_id>0,null,{timeout:90000});
  const sent=await economicState(page);
  const record=await page.evaluate(()=>view.game.extension.strategic_granary.orders['1']);
  assert.equal(sent.source,before.source-record.load-record.rations);
  assert.equal(sent.target,before.target);
  assert.equal(sent.sourceGold,before.sourceGold);
  assert.equal(sent.market,before.market);
  assert.equal(sent.books,before.books-1);
  if(candidate)await panel.getByRole('heading',{name:locale==='ja'?'輸送中の荷糧':'在途到貨'}).waitFor();
  assert.equal(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+3),true);
  await order.scrollIntoViewIfNeeded();
  await dialog.screenshot({path:path.join(output,`granary-${locale}-dispatched.png`)});
  await page.keyboard.press('Escape');
  await idle(page);
  if(!await page.locator('#end-turn').isVisible())await page.locator('#inspector-toggle').click();
  const turn=await page.evaluate(()=>view.game.turn),started=performance.now();
  await page.locator('#end-turn').click();
  await page.locator('#run-ai').click({timeout:90000});
  await page.waitForFunction(old=>view.game.turn>old,turn,{timeout:120000});
  await idle(page);
  const overview=await page.locator('vite-error-overlay, #webpack-dev-server-client-overlay').count();
  assert.equal(overview,0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({locale,viewport,url,title:await page.title(),version,forecastRows:9,realOrder:record,
   turnWaitMilliseconds:Math.round(performance.now()-started),horizontalOverflow:false,
   phase:await page.evaluate(()=>view.game.phase),errors,warnings}));
  await page.close();
 }
}finally{await browser.close();}
