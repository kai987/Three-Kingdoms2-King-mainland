/* Exercise transport quotes, two physical departures, save and arrival in the actual worker. */
import assert from 'node:assert/strict';
import {mkdir,readFile} from 'node:fs/promises';
import path from 'node:path';
import {chromium,devices} from '../tools/browser-tests/node_modules/playwright/index.mjs';

const [fixture,output]=process.argv.slice(2);
const source='lujiang',target='danyang';
const file=await readFile(fixture);
const url='http://127.0.0.1:'+Number(process.env.TK2_STATIC_TEST_PORT||18917)+'/Three-Kingdoms2-King-mainland/';
await mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chromium'});

async function dismissEvents(page){
 const modal=page.locator('#event-dialog[open]');
 for(let n=0;n<30&&await modal.isVisible();n++){
  const skip=modal.locator('[data-event-skip]');
  await (await skip.count()?skip:modal.locator('[data-event-next]')).click();
 }
}
async function active(page){
 return page.evaluate(id=>view.game.extension.logistics.convoys.filter(row=>row.source===id),source);
}
async function idle(page){
 await page.waitForFunction(()=>!document.body.classList.contains('busy')
   && !document.querySelector('#load').disabled && !orderConfirmation?.pending,null,{timeout:120000});
}
async function load(page,bytes,name){
 await page.locator('#load').click();
 await page.locator('#save-file').setInputFiles({name,mimeType:'application/json',buffer:bytes});
 await page.locator('#dialog').waitFor({state:'hidden',timeout:120000});
 await idle(page);
}
async function openLogistics(page){
 if(await page.locator('[data-domestic-dialog="logistics"]').isVisible())return;
 await page.locator('#city-jump').selectOption(source);
 const warehouse=page.locator('#city-command-tab-warehouse');
 if(!await warehouse.isVisible())await page.locator('#inspector-toggle').click();
 await warehouse.click();
 await page.locator('#city-logistics').click();
}
async function closeLogistics(page){
 await page.locator('#dialog button[data-cancel]').click();
 await page.locator('#dialog').waitFor({state:'hidden'});
}
async function advance(page){
 const turn=await page.evaluate(()=>view.game.turn);
 const controls={city:'end_turn',ai:'ai',arrivals:'arrivals',result:'settle'};
 for(let step=0;step<12;step++){
  const current=await page.evaluate(()=>({turn:view.game.turn,phase:view.game.phase,revision:view.revision}));
  if(current.phase==='city'&&current.turn>turn)return;
  const action=controls[current.phase];
  assert.ok(action,'unexpected phase during the transport exercise: '+current.phase);
  const result=await page.evaluate(kind=>command(kind,kind==='ai'?{turn:view.game.turn}:{}),action);
  await idle(page);
  const later=await page.evaluate(()=>({phase:view.game.phase,turn:view.game.turn,revision:view.revision,
    notice:document.querySelector('#notice')?.textContent}));
  assert.ok(result&&later.revision>current.revision,JSON.stringify({action,current,later}));
 }
 throw Error('The campaign did not finish the game period');
}
async function send(page,mode,locale){
 const before=await active(page);
 const capacity=page.locator('#convoy-route-quote');
 await page.locator('#convoy-route-mode').selectOption(mode);
 const expected=mode==='river'?/水陸混合/:locale==='ja'?/陸上輸送/:/陸運/;
 await page.waitForFunction(re=>new RegExp(re).test(document.querySelector('#convoy-route-quote').textContent),
     expected.source,{timeout:90000});
 const quote=await capacity.innerText();
 assert.match(quote,locale==='ja'?/総積載量 [1-9]/:/總糧容量 [1-9]/);
 assert.match(quote,locale==='ja'?/方針上限 80000/:/方針上限 80000/);
 assert.match(quote,locale==='ja'?/人員拘束 [1-9]/:/人員佔用 [1-9]/);
 if(mode==='river'){
  assert.match(quote,locale==='ja'?/総積載量 50000/:/總糧容量 50000/);
  assert.match(quote,locale==='ja'?/制約区間/:/瓶頸/);
 }
 const dialog=page.locator('#dialog');
 assert.equal(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+3),true);
 await capacity.scrollIntoViewIfNeeded();
 await dialog.screenshot({path:path.join(output,locale+'-'+mode+'.png')});
 const books=await page.evaluate(()=>view.catalog.command_books.factions.wu.remaining);
 await page.locator('#dispatch-logistics').click();
 const confirm=page.locator('#order-confirm-dialog');
 await confirm.waitFor({timeout:90000});
 assert.equal(await confirm.getAttribute('data-command-book-cost'),'1');
 await confirm.locator('#order-confirm-accept').click();
 await page.waitForFunction(({city,count})=>view.game.extension.logistics.convoys.filter(row=>row.source===city).length>count,
   {city:source,count:before.length},{timeout:120000});
 const rows=await active(page),sent=rows.at(-1);
 assert.equal(sent.journeys[0].mode,mode);
 const capacityLoad=sent.journeys[0].capacity_load;
 assert.equal(capacityLoad.total,sent.initial_cargo.grain+sent.journeys[0].supply.loaded);
 assert.ok(capacityLoad.total<=capacityLoad.limit);
 assert.equal(await page.evaluate(()=>view.catalog.command_books.factions.wu.remaining),books-1);
 return {quote,id:sent.id,officers:sent.officers,days:sent.journeys[0].quote.days,
   cargo:sent.initial_cargo.grain,rations:sent.journeys[0].supply.loaded,capacity:capacityLoad.limit};
}

try{
 for(const locale of ['zh-Hant','ja']){
  const page=await browser.newPage({...(locale==='ja'?devices['iPhone 13']:{viewport:{width:1280,height:800}})});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.addLocatorHandler(page.locator('#event-dialog[open]'),()=>dismissEvents(page));
  await page.goto(url);
  const start=page.locator('#game-loading-start');
  await start.waitFor({timeout:180000});
  await start.click();
  await page.locator('#game-loading-cover').waitFor({state:'hidden'});
  const option=page.locator('#transport-capacity-option');
  assert.equal(await option.isChecked(),false);
  await option.check();
  await page.locator('#begin').click();
  await option.waitFor({state:'hidden',timeout:120000});
  await idle(page);
  assert.equal(await page.evaluate(()=>view.game.extension.transport_capacity_rules_version),303);
  assert.equal(await page.evaluate(()=>view.game.extension.strategic_granary_rules_version),undefined);
  await load(page,file,'303-capacity-opening.json');
  await openLogistics(page);
  await page.locator('#dialog-language').selectOption(locale);
  await page.waitForFunction(lang=>document.documentElement.lang===lang,locale);
  if(locale==='ja'){
   const notice=await page.evaluate(()=>GameI18n.t('貨糧與獨立口糧超過實際路線的裝載容量。'));
   assert.match(notice,/積載上限を超えています/);
  }
  const counts=page.locator('[data-transport-capacity-summary]');
  assert.match(await counts.innerText(),/0 \/ 2/);
  const land=await send(page,'land',locale);
  await page.waitForFunction(()=>document.querySelector('[data-transport-capacity-summary]')?.textContent.includes('1 / 2'),
    null,{timeout:90000});
  assert.equal(await page.locator('#dispatch-logistics').isDisabled(),true);
  assert.match(await counts.innerText(),/1 \/ 2/);
  assert.match(await counts.innerText(),/1 \/ 1/);
  await closeLogistics(page);
  await advance(page);
  await openLogistics(page);
  const river=await send(page,'river',locale);
  assert.ok(land.officers.every(id=>!river.officers.includes(id)));
  await page.waitForFunction(()=>document.querySelector('[data-transport-capacity-summary]')?.textContent.includes('2 / 2'),
    null,{timeout:90000});
  assert.equal(await page.locator('#dispatch-logistics').isDisabled(),true);
  assert.match(await counts.innerText(),/2 \/ 2/);
  await closeLogistics(page);
  const downloadPromise=page.waitForEvent('download',{timeout:90000});
  await page.locator('#save').click();
  const download=await downloadPromise;
  const bytes=await readFile(await download.path());
  const snapshot=await active(page);
  await load(page,bytes,'transport-capacity-roundtrip.tk2.json');
  assert.deepEqual(await active(page),snapshot);
  assert.equal(await page.evaluate(city=>view.game.extension.transport_capacity.dispatches[city][1],source),1);
  for(let n=0;n<6;n++){
   const reports=await page.evaluate(({city})=>view.game.extension.logistics.reports.filter(
    row=>row.target===city&&row.kind==='transport_arrived'),{city:target});
   if([land.id,river.id].every(id=>reports.some(row=>row.details.convoy_id===id)))break;
   await advance(page);
  }
  const deliveries=await page.evaluate(({city,ids})=>view.game.extension.logistics.reports.filter(
   row=>row.target===city&&row.kind==='transport_arrived'&&ids.includes(row.details.convoy_id)),
   {city:target,ids:[land.id,river.id]});
  assert.equal(deliveries.length,2);
  assert.ok(deliveries.every(row=>row.details.grain>0));
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({locale,land,river,compactReload:true,deliveries,errors}));
  await page.close();
 }
}finally{await browser.close();}
