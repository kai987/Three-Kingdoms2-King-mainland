/* Exercise the opt-in, city climate display and file roundtrip using the real Worker. */
import assert from 'node:assert/strict';
import {mkdir,readFile} from 'node:fs/promises';
import path from 'node:path';
import {chromium,devices} from '../tools/browser-tests/node_modules/playwright/index.mjs';

const output=process.argv[2];
const useForecast=process.argv.includes('--forecast');
assert.ok(output,'Provide an external screenshot directory');
const address='http://127.0.0.1:'+Number(process.env.TK2_STATIC_TEST_PORT||18973)+'/Three-Kingdoms2-King-mainland/';
await mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chromium'});

async function idle(page){
 await page.waitForFunction(()=>!document.body.classList.contains('busy')&&!document.querySelector('#load').disabled,
   null,{timeout:120_000});
}
async function dismiss(page){
 const modal=page.locator('#event-dialog[open]');
 for(let i=0;await modal.isVisible()&&i<25;i++){
  const skip=modal.locator('[data-event-skip]');
  await (await skip.count()?skip:modal.locator('[data-event-next]')).click();
 }
}
async function cityWeather(page, locale){
 await page.locator('#city-jump').selectOption('liaodong');
 const compact=page.locator('#inspector-compact-information');
 if(await compact.isVisible())await compact.click();else await page.locator('#city-information').click();
 await page.locator('#dialog-language').selectOption(locale);
 await page.waitForFunction(language=>document.documentElement.lang===language,locale);
 const panel=page.locator('[data-city-weather]');
 await panel.waitFor({state:'visible'});
 await panel.locator('[data-agricultural-climate] summary').click();
 return panel;
}

async function transferForecast(page, japanese){
 await page.keyboard.press('Escape');
 await page.locator('#city-jump').selectOption('henan');
 await page.locator('#city-command-tab-army').click();
 await page.locator('#transfer').click();
 const target=page.locator('#transfer-city');
 await target.waitFor({state:'visible'});
 const destinations=await target.locator('option').evaluateAll(rows=>rows.filter(row=>row.value&&!row.disabled).map(row=>row.value));
 assert.ok(destinations.length);
 await target.selectOption(destinations.includes('hongnong')?'hongnong':destinations[0]);
 await page.locator('input[name=transfer-officer]:enabled').first().check();
 const quote=page.locator('[data-seasonal-forecast]');
 await quote.waitFor({state:'visible',timeout:120_000});
 const caption=await quote.innerText();
 assert.match(caption,japanese?/季節予報 \d+ 日・慎重な見積り \d+ 日/:/季節預估 \d+ 日 · 保守預估 \d+ 日/);
 assert.match(await page.locator('[data-weather-route-quote]').innerText(),japanese?/現在の天候/:/按目前天氣/);
 assert.match(caption,japanese?/結氷リスク \d+%/:/冰封風險 \d+%/);
 await quote.screenshot({path:path.join(output,(japanese?'ja':'zh-Hant')+'-route-forecast.png')});
 await page.keyboard.press('Escape');
 return caption;
}

try{
 for(const locale of ['zh-Hant','ja']){
  const touch=locale==='ja';
  const page=await browser.newPage(touch?devices['iPhone 13']:{viewport:{width:1280,height:800}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  await page.addLocatorHandler(page.locator('#event-dialog[open]'),()=>dismiss(page));
  const response=await page.goto(address);
  assert.equal(response.status(),200);
  await page.locator('#game-loading-start').click({timeout:180_000});
  const option=page.locator('#winter-climate-option'),wave=page.locator('#winter-cold-wave-option');
  const forecast=page.locator('#winter-forecast-option');
  assert.equal(await option.isChecked(),false);
  assert.equal(await wave.isEnabled(),false);
  assert.equal(await forecast.isEnabled(),false);
  assert.equal(await forecast.isChecked(),false);
  await page.locator('#winter-weather-option').check();
  await option.check();
  assert.equal(await page.locator('#winter-weather-option').isChecked(),false);
  assert.equal(await wave.isEnabled(),true);
  assert.equal(await wave.isChecked(),false);
  assert.equal(await forecast.isEnabled(),true);
  if(useForecast)await forecast.check();
  await page.locator('#begin').click();
  await page.waitForFunction(()=>view.game?.extension?.weather_rules_version===23,null,{timeout:120_000});
  await idle(page);
  assert.equal(await page.evaluate(()=>view.game.extension.weather_forecast_version),useForecast?231:undefined);
  let panel=await cityWeather(page,locale);
  assert.match(await panel.innerText(),touch?/積雪指数 \d+\/50/:/積雪指數 \d+\/50/);
  assert.match(await panel.innerText(),touch?/今月の降雪確率は1旬あたり/:/本月每旬降雪機率/);
  assert.match(await panel.innerText(),touch?/観測期間不足/:/觀測期不足/);
  assert.doesNotMatch(await panel.innerText(),touch?/年間の生産補正/:/年度產糧倍率/);
  if(useForecast){
   assert.match(await panel.locator('[data-snowpack-outlook]').innerText(),touch?/積雪・降雪リスク予測 \d+%/:/預估道路雪況風險 \d+%/);
   assert.match(await panel.locator('[data-agriculture-risk]').innerText(),touch?/実際の補正は未確定/:/實際倍率待定/);
  }
  assert.equal(await page.locator('#dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+3),true);
  await panel.screenshot({path:path.join(output,locale+'-winter-agriculture.png')});
  const weather=await page.evaluate(()=>view.game.extension.winter_weather);
  const forecastText=useForecast?await transferForecast(page,touch):null;
  if(!useForecast)await page.keyboard.press('Escape');
  const saving=page.waitForEvent('download',{timeout:120_000});
  await page.locator('#save').click();
  const file=await saving;
  await page.locator('#load').click();
  await page.locator('#save-file').setInputFiles({name:'v23-climate.tk2.json',mimeType:'application/json',
   buffer:await readFile(await file.path())});
  await page.locator('#dialog').waitFor({state:'hidden',timeout:120_000});
  await idle(page);
  assert.deepEqual(await page.evaluate(()=>view.game.extension.winter_weather),weather);
  assert.equal(await page.evaluate(()=>view.game.extension.weather_forecast_version),useForecast?231:undefined);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({locale,url:page.url(),title:await page.title(),viewport:page.viewportSize(),
   optIn:true,forecastOptIn:useForecast,forecastText,coldWaveDefault:false,dailyLedgerRoundtrip:true,consoleErrors:errors}));
  await page.close();
 }
}finally{await browser.close();}
