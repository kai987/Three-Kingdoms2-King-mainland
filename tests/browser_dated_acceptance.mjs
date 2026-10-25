/* Public controls + production HTTP transactions on controlled initial catalogs.
 * Browser plugin not available: use the repository's pinned Chromium runtime.
 * No state/save injection, private calendar call, or request interception.
 */
import {chromium,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const options={founding:'http://127.0.0.1:18921/',retirement:'http://127.0.0.1:18922/',
 coup:'http://127.0.0.1:18923/',output:'/tmp/tk2-dated-public-browser-qa',case:'all',viewport:'both'};
for(let i=2;i<process.argv.length;i+=2){
 const key=process.argv[i]?.replace(/^--/,''),value=process.argv[i+1];
 assert(Object.hasOwn(options,key)&&value,'Use --founding/--retirement/--coup BASE, --output DIR, --case all|founding|retirement|coup, --viewport both|desktop|mobile');
 options[key]=value;
}
assert(['all','founding','retirement','coup'].includes(options.case));
assert(['both','desktop','mobile'].includes(options.viewport));
for(const kind of ['founding','retirement','coup']){
 const url=new URL(options[kind]);assert.equal(url.hostname,'127.0.0.1','Keep acceptance isolated on loopback');
 assert(!['8878','18925'].includes(url.port),'Never use the live campaign or the shared QA server');
 options[kind]=url.href.endsWith('/')?url.href:url.href+'/';
}
const PEOPLE={song:'historical-song-jian',bian:'historical-bian-zhang',beigong:'historical-beigong-boyu',li:'historical-li-wenhou',han:'san14-candidate-0166'};
const PHOTO_KINDS=new Set(['faction_founded','faction_founding_skipped','faction_coup','faction_coup_skipped','officer_death','succession']);
const results=[];
await mkdir(options.output,{recursive:true});

async function idle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
async function json(page,base,route){const response=await page.request.get(new URL(route,base).href);assert.equal(response.status(),200,await response.text());return response.json();}
async function state(page,base){return json(page,base,'api/state');}
async function saved(page,base){return json(page,base,'api/save');}
const soldiers=s=>Object.values(s.cities).reduce((n,c)=>n+c.reserves,0)+Object.values(s.officers).reduce((n,p)=>n+p.troops,0);
const officer=(save,pid)=>Object.values(save.state.officers).find(p=>p.person_id===pid);

async function consumeEvents(page,base,label,scenes){
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const modal=page.locator('#event-dialog');
 for(let i=0;i<40&&await modal.isVisible();i++){
  const ids=await page.evaluate(()=>gameEvents.snapshot().active),view=await state(page,base),
   records=view.game.extension.events.items.filter(row=>ids.includes(row.id));
  assert(records.length,'Every shown scene must refer to a committed server event');
  const record=records[0],text=await modal.innerText();
  if(PHOTO_KINDS.has(record.kind)){
   const before=await saved(page,base),cursor=await page.evaluate(()=>JSON.stringify(gameEvents.snapshot()));
   const portraits=modal.locator('.event-person img');
   await expect(portraits).toHaveCount(new Set(records.flatMap(row=>row.person_ids)).size);
   await expect.poll(()=>portraits.evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth>0))).toBe(true);
   const source=await portraits.evaluateAll(images=>images.map(image=>image.getAttribute('src')));
   assert(source.every(url=>url.includes('/assets/portraits/')),'Use the real portrait manifest and assets');
   const bounds=await modal.boundingBox(),viewport=page.viewportSize();
   assert(bounds.x>=0&&bounds.y>=0&&bounds.x+bounds.width<=viewport.width+1&&bounds.y+bounds.height<=viewport.height+1,'Event dialog stays inside the viewport');
   const file=label+'-'+record.kind+'-'+record.id;
   await page.screenshot({path:join(options.output,file+'-tc.png')});
   await modal.locator('[data-language-picker]').selectOption('ja');
   await expect(modal.locator('[data-event-root]')).toHaveAttribute('data-l10n-native','ja');
   const japanese=await modal.innerText();assert.match(japanese,/[ぁ-ゖァ-ヶ]/);
   assert(!/(?:city_occupied|leader_unavailable|conditions_changed|executed)/.test(japanese),'UI does not expose internal reason codes');
   assert.equal(await page.evaluate(()=>JSON.stringify(gameEvents.snapshot())),cursor,'Changing locale preserves the scene cursor');
   assert.deepEqual(await saved(page,base),before,'Locale changes and drawing portraits never change a save or RNG');
   await page.screenshot({path:join(options.output,file+'-ja.png')});
   scenes.push({id:record.id,kind:record.kind,person_ids:record.person_ids,city_ids:record.city_ids,
    details:record.details,text,japanese,portraits:source});
   await modal.locator('[data-language-picker]').selectOption('zh-Hant');
  }
  await modal.locator('[data-event-next]').click();
 }
 await expect(modal).not.toBeVisible();
}

async function start(page,base,faction,label,scenes){
 await page.goto(base);await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
 const cover=page.locator('#game-loading-start');if(await cover.isVisible()){await expect(cover).toBeEnabled();await cover.click();}
 await expect(page.locator('#game-loading-cover')).not.toBeVisible();
 await page.locator(`input[name="faction"][value="${faction}"]`).check();
 assert.equal(await page.locator('#seed').inputValue(),'2026');
 if(label.startsWith('founding')){
  await expect(page.locator('input[name="faction"][value="bian_zhang"]')).toHaveCount(0);
  await expect(page.locator('input[name="faction"][value="song_jian"]')).toHaveCount(0);
 }
 await page.locator('#begin').click();await idle(page);await consumeEvents(page,base,label,scenes);
 const view=await state(page,base);assert.equal(view.game.player,faction);assert.equal(view.game.turn,1);
 return saved(page,base);
}

async function turn(page,base,label,scenes){
 const before=(await state(page,base)).game;
 await expect(page.locator('#end-turn')).toBeEnabled();await page.locator('#end-turn').click();await idle(page);
 for(let i=0;i<12;i++){
  await consumeEvents(page,base,label,scenes);const current=(await state(page,base)).game;
  if(current.phase==='city'&&current.turn===before.turn+1)return saved(page,base);
  if(current.phase==='ai'){await expect(page.locator('#run-ai')).toBeEnabled();await page.locator('#run-ai').click();}
  else if(current.phase==='arrivals'){await expect(page.locator('#process-arrivals')).toBeEnabled();await page.locator('#process-arrivals').click();}
  else throw Error('Unexpected actual calendar phase: '+current.phase);
  await idle(page);
 }
 throw Error('Public turn controls exceeded their bounded command budget');
}

async function acceptance(browser,kind,viewport){
 const base=options[kind],context=await browser.newContext({viewport}),page=await context.newPage(),errors=[],scenes=[];
 page.setDefaultTimeout(30_000);page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
 const label=kind+'-'+viewport.width,faction=kind==='retirement'?'shu':kind==='coup'?'bian_zhang':'han';
 try{
  const initial=await start(page,base,faction,label,scenes);let beforeMonth=initial,after;
  for(let i=0;i<3;i++){
   if(i===2)beforeMonth=await saved(page,base);
   after=await turn(page,base,label,scenes);assert.equal(after.state.turn,i+2);
   if(i<2)assert.equal(after.state.month,kind==='retirement'?9:kind==='coup'?11:10);
  }
  assert.equal(after.state.day,1);assert.equal(after.state.player,faction);
  if(kind==='founding'){
   assert.equal(after.state.year,184);assert.equal(after.state.month,11);
   assert.equal(after.state.cities.jincheng.owner,'bian_zhang');assert.equal(after.state.cities.tianshui.owner,'bian_zhang');assert.equal(after.state.cities.longxi.owner,'song_jian');
   assert.equal(after.state.extension.leaders.bian_zhang,1030);assert.equal(after.state.extension.leaders.song_jian,1024);
   for(const pid of[PEOPLE.bian,PEOPLE.beigong,PEOPLE.li,PEOPLE.han])assert.equal(officer(after,pid).faction_id,'bian_zhang');
   assert.equal(officer(after,PEOPLE.song).faction_id,'song_jian');
   assert.equal(soldiers(after.state),soldiers(initial.state),'Formations redistribute existing soldiers');
   const events=scenes.filter(scene=>scene.kind==='faction_founded');assert.equal(events.length,2);
   assert.equal(events[0].details.founding_id,'liangzhou-revolt-184-11');assert.equal(events[1].details.founding_id,'song-jian-rise-184-11');
   assert.deepEqual([...events[0].city_ids].sort(),['jincheng','tianshui']);assert.equal(events[0].person_ids.length,4);
   assert(!events[0].person_ids.includes(PEOPLE.song),'The narrative participant is not duplicated into the active Bian roster');
   for(const event of events)assert(event.details.reserves>=0&&event.details.reserves<=999*event.person_ids.length);
  }else if(kind==='retirement'){
   assert.equal(after.state.year,214);assert.equal(after.state.month,10);
   const retired=officer(after,PEOPLE.song);assert.equal(retired.alive,false);assert.equal(retired.troops,0);assert.equal(retired.faction_id,null);
   const receipt=after.state.extension.dated_events.retirements[PEOPLE.song];assert.deepEqual(receipt.date,[214,10]);assert.equal(receipt.released,officer(beforeMonth,PEOPLE.song).troops);
   assert.equal(after.state.cities.xiangyang.reserves-beforeMonth.state.cities.xiangyang.reserves,receipt.released);
   assert(scenes.some(scene=>scene.kind==='officer_death'&&scene.person_ids.includes(PEOPLE.song)));
   const pending=after.state.extension.pending_succession.shu;assert(pending&&pending.candidates.length);
   const choice=page.locator('#successor-officer');await expect(choice).toBeVisible();
   const ident=await choice.locator('option').first().getAttribute('value');await choice.selectOption(ident);
   await page.locator('#choose-successor').click();await idle(page);await consumeEvents(page,base,label,scenes);
   after=await saved(page,base);assert.equal(String(after.state.extension.leaders.shu),ident);assert(!after.state.extension.pending_succession.shu);
   assert(scenes.some(scene=>scene.kind==='succession'));await expect(page.locator('#end-turn')).toBeEnabled();
  }else{
   assert.equal(after.state.year,186);assert.equal(after.state.month,12);
   assert.equal(after.state.player,'bian_zhang');assert.equal(after.state.extension.leaders.bian_zhang,165);
   for(const pid of[PEOPLE.bian,PEOPLE.beigong,PEOPLE.li]){assert.equal(officer(after,pid).alive,false);assert.equal(officer(after,pid).troops,0);}
   assert.equal(officer(after,PEOPLE.han).faction_id,'bian_zhang');assert.equal(officer(after,PEOPLE.han).alive,true);
   assert.equal(soldiers(after.state),soldiers(initial.state),'The coup returns victims\' soldiers without generating troops');
   const coup=scenes.find(scene=>scene.kind==='faction_coup');assert(coup);assert.equal(coup.details.released_troops,900);
   assert.equal(after.state.cities.jincheng.reserves-beforeMonth.state.cities.jincheng.reserves,900);
   const current=(await state(page,base)).catalog.factions.find(row=>row.id==='bian_zhang');assert.equal(current.captain,'韩遂');
   assert(!after.state.extension.pending_succession.bian_zhang);await expect(page.locator('#end-turn')).toBeEnabled();
  }
  const beforeReview=await saved(page,base);await page.locator('#city-jump').selectOption(Object.keys(after.state.cities).find(id=>after.state.cities[id].owner===faction));
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await expect(page.locator('#event-dialog')).not.toBeVisible();
  assert.deepEqual(await saved(page,base),beforeReview,'Ordinary rendering does not repeat or acknowledge a domain transaction');
  assert.deepEqual(errors,[]);results.push({kind,viewport,base,commands:'new + three public ten-day turns'+(kind==='retirement'?' + choose_successor':''),
   date:[after.state.year,after.state.month,after.state.day],turn:after.state.turn,player:after.state.player,scenes,errors});
  await writeFile(join(options.output,label+'-save.json'),JSON.stringify(after,null,2));
  console.log(kind+' '+viewport.width+': actual new/three turns/events/save/RNG checks passed');
 }finally{await context.close();}
}

const browser=await chromium.launch({channel:'chromium',headless:true});
try{
 for(const viewport of(options.viewport==='desktop'?[{width:1280,height:800}]:options.viewport==='mobile'?[{width:390,height:844}]:[{width:1280,height:800},{width:390,height:844}])){
  for(const kind of(options.case==='all'?['founding','retirement','coup']:[options.case]))await acceptance(browser,kind,viewport);
 }
 await writeFile(join(options.output,'result.json'),JSON.stringify({browser:'Browser plugin not available; pinned Playwright Chromium',scope:'controlled initial catalogs; production HTTP sessions, public UI commands and actual domain events; no injected state',results},null,2));
}finally{await browser.close();}
