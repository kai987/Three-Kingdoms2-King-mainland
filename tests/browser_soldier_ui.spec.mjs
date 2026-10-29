/* Current shipped Worker acceptance using visibly imported controlled saves.
 * The fixtures disclose their arranged positions/seed and pass the production
 * loader. All gameplay mutations below use visible UI controls, never injected
 * campaign state or a replacement damage/RNG implementation.
 */
import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import {execFileSync} from 'node:child_process';
import {writeFile} from 'node:fs/promises';

const fixtures=new Map(),pageErrors=new WeakMap();
function fixture(kind){
 if(!fixtures.has(kind))fixtures.set(kind,JSON.parse(execFileSync(process.env.PYTHON||'python3',[
  '-B',new URL('./browser_soldier_fixture.py',import.meta.url).pathname,kind,
 ],{encoding:'utf8',maxBuffer:12*1024*1024,timeout:90_000})));
 return fixtures.get(kind);
}
test.beforeEach(async({page})=>{
 const errors=[];pageErrors.set(page,errors);
 page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
});
async function opening(page){
 await page.goto('./');await expect(page).toHaveTitle(/三國|三国/);
 await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
 await page.locator('#game-loading-start').click();await expect(page.locator('#game-loading-cover')).toBeHidden();
 await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
}
async function idle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
async function save(page){return page.evaluate(async()=>{const r=await fetch('/api/save');if(!r.ok)throw Error('Actual soldier save could not be inspected');return r.json();});}
async function read(page,withView=true){if(!withView)return {save:await save(page)};return page.evaluate(async()=>{
 const [a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);
 if(!a.ok||!b.ok)throw Error('Actual soldier state could not be inspected');
 const state=await b.json();return {save:await a.json(),view:state.view||state};
});}
async function load(page,value,name='controlled-soldier-boundary.json'){
 await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
 await idle(page);await expect(page.locator('#dialog')).toBeHidden();expect(await save(page)).toEqual(value);
}
async function dismissEvents(page){
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const events=page.locator('#event-dialog');
 for(let i=0;i<20&&await events.isVisible();i++){
  const skip=events.locator('[data-event-skip]');await(await skip.count()?skip:events.locator('[data-event-next]')).click();
 }
 await expect(events).toBeHidden();
}
async function control(page,id){
 const button=page.locator('#'+id),toggle=page.locator('#inspector-toggle');
 if(!await button.isVisible()&&await toggle.isVisible())await toggle.click();
 await expect(button).toBeEnabled();await button.click();
}
async function locale(page,value){
 const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
 await page.locator('#language').selectOption(value);await menu.locator('summary').click();
}
async function cell(page,point,touch){
 const canvas=page.locator('[data-battle-canvas]');await canvas.scrollIntoViewIfNeeded();
 const box=await canvas.boundingBox();expect(box).toBeTruthy();
 const position={x:(point.x*16+8)*box.width/496,y:(point.y*16+8)*box.height/384};
 if(touch)await canvas.tap({position});else await canvas.click({position});
}
async function animation(page,{withView=true}={}){
 await expect.poll(()=>page.evaluate(()=>!document.body.classList.contains('busy')||!!document.querySelector('[data-battle-skip]:not([hidden])')),{timeout:90_000}).toBe(true);
 const committed=await save(page),skip=page.locator('[data-battle-skip]');
 if(await skip.isVisible()){
  try{await skip.click({timeout:1000});}catch(error){if(await skip.isVisible())throw error;}
 }
 await idle(page);await dismissEvents(page);
 expect(await save(page)).toEqual(committed,'Animation completion or Skip cannot resolve another hit or draw extra random numbers');
 return read(page,withView);
}
async function evidence(page,testInfo,name){
 await page.screenshot({path:testInfo.outputPath(name+'.png'),fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
}
async function attach(testInfo,name,value){await testInfo.attach(name,{body:Buffer.from(JSON.stringify(value,null,2)),contentType:'application/json'});}

test('field soldier formations expose ten hundred-person teams and replay actual individual orders without extra damage',async({page},testInfo)=>{
 const macro=fixture('field'),contact=fixture('contact'),touch=testInfo.project.name==='touch-chromium',proof=[];
 await opening(page);await load(page,macro.save);
 const scene=page.locator('[data-battle-scene]');await expect(scene).toHaveAttribute('data-battle-scene-mode','tactical');
 const before=await read(page,false),markers=JSON.parse(await scene.getAttribute('data-battle-markers'));
 expect(markers.length).toBe(before.save.state.battle.attackers.length+before.save.state.battle.defenders.length);
 for(const marker of markers){expect(['平','山','水']).toContain(marker.type);expect(marker.teams).toBe(Math.ceil(marker.troops/100));expect(marker.teams).toBeGreaterThanOrEqual(1);expect(marker.teams).toBeLessThanOrEqual(10);}
 const actorMarker=markers.find(row=>String(row.id)===String(macro.actor));expect(actorMarker.troops).toBe(1000);expect(actorMarker.teams).toBe(10);
 await cell(page,macro.actor_cell,touch);await cell(page,macro.target_cell,touch);await control(page,'attack');await idle(page);
 await expect(scene).toHaveAttribute('data-battle-scene-mode','field-formation');
 let current=await read(page,false),row=current.save.state.battle.extended.siege;
 expect(row.mode).toBe('field');expect(row.fort).toBeNull();expect(current.save.state.rng).toEqual(before.save.state.rng);
 expect(current.save.state.battle.attackers).toEqual(before.save.state.battle.attackers);expect(current.save.state.battle.defenders).toEqual(before.save.state.battle.defenders);
 expect(row.units.filter(unit=>unit.side==='attackers')).toHaveLength(11);
 expect(row.units.filter(unit=>unit.side==='attackers'&&unit.kind!=='general').map(unit=>unit.troops)).toEqual(Array(10).fill(100));
 await expect(page.locator('[data-siege-piece-count^="a"]')).toHaveCount(11);
 const preview=current.save;await page.locator('[data-siege-formation="1"]').click();expect(await save(page)).toEqual(preview);
 await evidence(page,testInfo,'field-native-formation-ten-teams');await control(page,'siege-form');await idle(page);
 await expect(page.locator('[data-siege-piece-order]')).toHaveCount(11);
 const formed=await read(page,false);for(const input of await page.locator('[data-siege-piece-order]').all())await input.selectOption('wait');
 await page.locator('#siege-piece-a1').selectOption('advance');expect(await save(page)).toEqual(formed.save,'Per-team order drafts never mutate the game');
 await control(page,'siege-step');current=await animation(page,{withView:false});row=current.save.state.battle.extended.siege;
 expect(row.piece_orders.attackers.a1).toBe('advance');expect(row.piece_orders.attackers.a2).toBe('wait');expect(row.round).toBe(2);
 expect(row.units.map(unit=>[unit.id,unit.x,unit.y])).not.toEqual(formed.save.state.battle.extended.siege.units.map(unit=>[unit.id,unit.x,unit.y]));
 await load(page,current.save,'controlled-field-per-team-roundtrip.json');expect(await save(page)).toEqual(current.save);
 proof.push({stage:'macro-to-field',markers,round:row.round,piece_orders:row.piece_orders,events:row.events});
 for(const language of ['zh-Hant','ja']){
  await locale(page,language);await load(page,contact.save,'controlled-field-infantry-archer-cavalry-contact.json');
  await expect(scene).toHaveAttribute('data-battle-scene-mode','field-orders');await expect(page.locator('[data-siege-piece-order]')).toHaveCount(11);
  const initial=await read(page,false);await control(page,'siege-step');
  await expect(page.locator('[data-battle-skip]')).toBeVisible();
  expect(await page.evaluate(()=>battleScene.state().scene)).toBe('soldier_step');
  // Locator.screenshot waits for fonts/layout and can finish after this short
  // committed replay. Sample the read-only canvas buffer immediately while
  // the actual RAF is playing, without injecting a clock or campaign state.
  const canvas=page.locator('[data-battle-canvas]'),first=await canvas.evaluate(node=>node.toDataURL('image/png'));
  let second=first;
  for(let frame=0;frame<8&&second===first;frame++){
   await page.waitForTimeout(80);second=await canvas.evaluate(node=>node.toDataURL('image/png'));
  }
  expect(second).not.toBe(first,'Actual committed attack events have visible animation frames');
  await writeFile(testInfo.outputPath('soldier-animation-'+language+'-a.png'),Buffer.from(first.split(',')[1],'base64'));
  await writeFile(testInfo.outputPath('soldier-animation-'+language+'-b.png'),Buffer.from(second.split(',')[1],'base64'));
  const committed=await read(page,false),active=committed.save.state.battle.extended.siege;
  expect(active).toBeTruthy();expect(active.events.length).toBeGreaterThan(0);expect(active.events.length).toBeLessThanOrEqual(44);
  expect(active.events.some(event=>event.kind==='melee'&&event.actor===contact.contact_pieces.infantry)).toBe(true);
  expect(active.events.some(event=>event.kind==='arrow'&&event.actor===contact.contact_pieces.archer)).toBe(true);
  expect(active.events.some(event=>event.kind==='melee'&&event.actor===contact.contact_pieces.cavalry)).toBe(true);
  // This controlled legal contact owns the explicit reciprocal-damage
  // property. Natural campaign movement tests also allow one-sided losses.
  for(const side of ['attackers','defenders'])expect(committed.save.state.battle[side].reduce((sum,u)=>sum+u.troops,0)).toBeLessThan(initial.save.state.battle[side].reduce((sum,u)=>sum+u.troops,0),'Both actual armies take soldier damage in this controlled reciprocal-contact case');
  expect(committed.save.state.rng.draws-initial.save.state.rng.draws).toBe(2,'Each side rolls its native attack base once, never one roll per rendered hit');
  await animation(page,{withView:false});expect(await save(page)).toEqual(committed.save);
  await evidence(page,testInfo,'soldier-piece-counts-and-orders-'+language);proof.push({language,before_rng:initial.save.state.rng,after_rng:committed.save.state.rng,events:active.events});
 }
 await attach(testInfo,'actual-soldier-orders-events-and-rng',proof);expect(pageErrors.get(page)).toEqual([]);
});

test('successful battlefield conversion immediately enables an eleventh friendly officer and empty-castle occupation wins',async({page},testInfo)=>{
 const converted=fixture('conversion'),occupation=fixture('occupation'),touch=testInfo.project.name==='touch-chromium';
 await opening(page);await load(page,converted.save,'controlled-seeded-live-conversion.json');
 const before=await read(page),battle=before.save.state.battle;
 expect(battle.attackers).toHaveLength(10);expect(battle.defenders).toHaveLength(10);
 await page.locator(`[data-actor="${converted.actor}"]`).click();await page.locator(`[data-target="${converted.target}"]`).click();await control(page,'tactic');
 await page.locator('#tactic-choice').selectOption('8');expect((await read(page)).save).toEqual(before.save);
 await page.locator('#confirm-tactic').click();let current=await animation(page),after=current.save.state.battle;
 expect(after.attackers).toHaveLength(11);expect(after.defenders).toHaveLength(9);
 expect(after.attackers.find(unit=>unit.id===converted.target).troops).toBe(converted.target_troops);
 expect(after.defenders.some(unit=>unit.id===converted.target)).toBe(false);expect(current.save.state.officers[converted.target].faction_id).toBe('wei');expect(current.save.state.officers[converted.target].loyalty).toBe(converted.expected_loyalty);
 expect(after.extended.tactical.positions[converted.target]).toEqual(battle.extended.tactical.positions[converted.target]);
 expect(after.extended.support[converted.target].health).toBe(battle.extended.support[converted.target].health);
 expect(current.save.state.rng.draws-before.save.state.rng.draws).toBe(1);
 expect(current.view.catalog.battle_tactical.actors[String(converted.target)].can_act).toBe(true);
 const button=page.locator(`[data-actor="${converted.target}"]`);await expect(button).toBeVisible();await button.click();
 // Keep a point in reserve so this movement alone is inspected. Spending the
 // last point legitimately hands the turn to the AI and can cause new combat
 // RNG; that is a separate handoff behavior, not an animation side effect.
 const available=current.save.state.battle.extended.tactical.points.attackers;
 const route=current.view.catalog.battle_tactical.actors[String(converted.target)].reachable
  .filter(point=>point.cost>0&&point.cost<available).sort((a,b)=>a.cost-b.cost||a.y-b.y||a.x-b.x)[0];
 expect(route).toBeTruthy();const beforeMove=current.save;await cell(page,route,touch);await control(page,'battle-move');current=await animation(page);
 expect(current.save.state.battle.extended.tactical.positions[converted.target]).toEqual({x:route.x,y:route.y});expect(current.save.state.rng).toEqual(beforeMove.state.rng);
 expect(current.save.state.battle.extended.tactical.points.attackers).toBe(beforeMove.state.battle.extended.tactical.points.attackers-route.cost);
 await load(page,current.save,'controlled-live-conversion-roundtrip.json');await evidence(page,testInfo,'eleventh-officer-usable-after-conversion');
 const convertedSave=current.save;await load(page,occupation.save,'controlled-empty-enemy-castle.json');
 const prior=await read(page);expect(prior.save.state.battle.defenders.some(unit=>unit.troops>0)).toBe(true);
 await page.locator(`[data-actor="${occupation.actor}"]`).click();await cell(page,occupation.cell,touch);await control(page,'battle-move');current=await animation(page);
 expect(current.save.state.phase).toBe('result');expect(current.save.state.battle.outcome).toBe('victory');expect(current.save.state.battle.extended.occupation).toEqual({actor:occupation.actor,side:'attackers',...occupation.cell});
 expect(current.save.state.battle.defenders).toEqual(prior.save.state.battle.defenders);expect(current.save.state.rng).toEqual(prior.save.state.rng);
 expect(current.save.state.battle.extended.tactical.points.attackers).toBe(prior.save.state.battle.extended.tactical.points.attackers-occupation.cost);
 await evidence(page,testInfo,'empty-castle-occupation-victory');await control(page,'settle');await idle(page);await dismissEvents(page);
 const settled=await read(page);expect(settled.save.state.cities.danyang.owner).toBe('wei');
 await attach(testInfo,'battle-conversion-occupation-proof',{conversion_seed:converted.selected_seed,leader_virtue:converted.leader_virtue,expected_loyalty:converted.expected_loyalty,conversion:convertedSave,occupation:current.save,settled_owner:settled.save.state.cities.danyang.owner});
 expect(pageErrors.get(page)).toEqual([]);
});

test('native battlefield hospital rice shop and weapon shop use the current cell and real army resources',async({page},testInfo)=>{
 const cases=fixture('facilities'),proof=[];await opening(page);
 for(const [index,kind]of ['hospital','market','armory'].entries()){
  const value=cases[kind];await locale(page,index===1?'ja':'zh-Hant');await load(page,value.save,'controlled-native-'+kind+'-cell.json');
  await page.locator(`[data-actor="${value.actor}"]`).click();const before=await read(page),quote=before.view.catalog.battle_tactical.actors[String(value.actor)].facility;
  expect(quote.kind).toBe(kind);expect(quote.x).toBe(value.site.x);expect(quote.y).toBe(value.site.y);
  await control(page,'battle-facility-open');await expect(page.locator('#dialog')).toBeVisible();
  const payer=quote.payer_city;let merchandise=null;
  if(kind==='hospital')await page.locator('#battle-facility-treat').click();
  if(kind==='market'){
   const batches=page.locator('#battle-facility-batches');await batches.fill(String(quote.trade.max_batches+999));await expect(batches).toHaveValue(String(quote.trade.max_batches));
   await batches.fill('1');expect((await read(page)).save).toEqual(before.save,'Rice-shop quantities and previews never spend money or RNG');await page.locator('#battle-facility-buy-grain').click();
  }
  if(kind==='armory'){
   merchandise=quote.stock.weapon.find(item=>item.eligible&&item.price<=quote.gold);expect(merchandise).toBeTruthy();
   await page.locator('#battle-facility-slot').selectOption('weapon');await page.locator('#battle-facility-item').selectOption(String(merchandise.id));
   expect((await read(page)).save).toEqual(before.save,'Equipment selection and prices remain read-only until purchase');await page.locator('#battle-facility-buy-equipment').click();
  }
  await idle(page);
  if(await page.locator('#dialog').isVisible())await page.keyboard.press('Escape');
  await expect(page.locator('#dialog')).toBeHidden();await dismissEvents(page);const current=await read(page);
  expect(current.save.state.battle.extended.tactical).toEqual(before.save.state.battle.extended.tactical,'Village services do not spend tactical movement or move an officer');expect(current.save.state.extension.command_books).toEqual(before.save.state.extension.command_books,'Battlefield services do not spend strategic books');
  if(kind==='hospital'){
   expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-quote.medical_gold);expect(current.save.state.battle.extended.support[value.actor].health).toBeGreaterThan(before.save.state.battle.extended.support[value.actor].health);expect(current.save.state.battle.extended.support[value.actor].health).toBeLessThanOrEqual(quote.max_health);expect(current.save.state.rng.draws-before.save.state.rng.draws).toBe(1);
  }else if(kind==='market'){
   expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-quote.trade.rate);expect(current.save.state.cities[payer].grain).toBe(before.save.state.cities[payer].grain+quote.trade.batch_grain);expect(current.save.state.rng).toEqual(before.save.state.rng);
  }else{
   expect(current.save.state.officers[value.actor].weapon_id).toBe(merchandise.id);expect(current.save.state.officers[value.actor].profile).toEqual(before.save.state.officers[value.actor].profile);expect(current.save.state.cities[payer].gold).toBe(before.save.state.cities[payer].gold-merchandise.price);expect(current.save.state.rng).toEqual(before.save.state.rng);
  }
  await evidence(page,testInfo,'native-battlefield-service-'+kind);await load(page,current.save,'controlled-'+kind+'-service-roundtrip.json');
  proof.push({kind,actor:value.actor,site:value.site,payer,before_gold:before.save.state.cities[payer].gold,after_gold:current.save.state.cities[payer].gold,before_rng:before.save.state.rng,after_rng:current.save.state.rng});
 }
 await attach(testInfo,'battlefield-village-services-proof',proof);expect(pageErrors.get(page)).toEqual([]);
});
