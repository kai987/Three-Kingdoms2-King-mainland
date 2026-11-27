# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: browser_soldier_ui.spec.mjs >> qimen targets enemies with daily losses and experience, bilingual receipts and exact zero-troop expiry
- Location: tests/browser_soldier_ui.spec.mjs:732:1

# Error details

```
Test timeout of 240000ms exceeded.
```

```
Error: expect(locator).not.toHaveClass(expected) failed

Locator: locator('body')
Expected pattern: not /\bbusy\b/
Received string: "wide-map-layout busy"

Call log:
  - Expect "not toHaveClass" locator('body') with timeout 30000ms
  - waiting for locator('body')
    5 × locator resolved to <body class="wide-map-layout busy">…</body>
      - unexpected value "wide-map-layout busy"
  - Test timeout of 240000ms exceeded.

```

```yaml
- banner:
  - heading "三国志・大陸戦役" [level=1]
  - paragraph: 234年2月上旬 第1回合 · 1旬10日 · 中級
  - region "報告"
  - navigation "セーブとルール"
- main:
  - region "戦略地図"
  - complementary "現在の操作"
- dialog "ロード":
  - heading "ロード" [level=2]
  - text: 言語
  - combobox "表示言語を切り替え"
  - button "このブラウザのセーブを読む" [disabled]
  - text: セーブファイルを選択
  - button "セーブファイルを選択"
  - paragraph: 無効なセーブでは現在の進行状況を保持します。
  - status: 自動保存済み：234年2月 · 秋風五丈原 · 234年2月上旬 · 第1旬 · 11/28 06:31
  - heading "自動保存の復元ポイント" [level=3]
  - paragraph: 戦役ごとに最大3件、全体で最大4 MiBを保存します。容量が足りないときは各戦役の最新の復元ポイントを優先します。復元ポイントを選ぶと確認画面が開きます。
  - group "戦役 1 · 234年2月 · 秋風五丈原 · 蜀漢"
  - status
  - button "取消"
```

# Test source

```ts
  1   | /* Current shipped Worker acceptance using visibly imported controlled saves.
  2   |  * The fixtures disclose their arranged positions/seed and pass the production
  3   |  * loader. All gameplay mutations below use visible UI controls, never injected
  4   |  * campaign state or a replacement damage/RNG implementation.
  5   |  */
  6   | import {test,expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
  7   | import {execFileSync} from 'node:child_process';
  8   | import {writeFile} from 'node:fs/promises';
  9   |
  10  | const fixtures=new Map(),pageErrors=new WeakMap();
  11  | function fixture(kind){
  12  |  if(!fixtures.has(kind))fixtures.set(kind,JSON.parse(execFileSync(process.env.PYTHON||'python3',[
  13  |   '-B',new URL('./browser_soldier_fixture.py',import.meta.url).pathname,kind,
  14  |  ],{encoding:'utf8',maxBuffer:12*1024*1024,timeout:90_000})));
  15  |  return fixtures.get(kind);
  16  | }
  17  | test.beforeEach(async({page})=>{
  18  |  const errors=[];pageErrors.set(page,errors);
  19  |  page.on('pageerror',error=>errors.push(error.message));
  20  |  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  21  | });
  22  | async function opening(page){
  23  |  await page.goto('./');await expect(page).toHaveTitle(/三國|三国/);
  24  |  await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});
  25  |  await page.locator('#game-loading-start').click();await expect(page.locator('#game-loading-cover')).toBeHidden();
  26  |  await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
  27  | }
> 28  | async function idle(page){await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);}
      |                                                                  ^ Error: expect(locator).not.toHaveClass(expected) failed
  29  | async function save(page){return page.evaluate(async()=>{const r=await fetch('/api/save');if(!r.ok)throw Error('Actual soldier save could not be inspected');return r.json();});}
  30  | async function read(page,withView=true,{openingTroopSources,facilityActor,tacticId}={}){
  31  |  if(!withView)return {save:await save(page)};
  32  |  return page.evaluate(async({sourceKinds,facilityActor,tacticId})=>{
  33  |   const [a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);
  34  |   if(!a.ok||!b.ok)throw Error('Actual soldier state could not be inspected');
  35  |   const state=await b.json(),save=await a.json(),view=state.view||state;
  36  |   if(facilityActor!==undefined){
  37  |    const id=String(facilityActor),facility=view.catalog.battle_tactical.actors[id].facility;
  38  |    return {save,view:{catalog:{battle_tactical:{actors:{[id]:{facility}}}}}};
  39  |   }
  40  |   if(tacticId!==undefined){
  41  |    const cost=view.catalog.battle_tactical.tactic_costs[tacticId];
  42  |    return {save,view:{catalog:{battle_tactical:{tactic_costs:{[tacticId]:cost}}}}};
  43  |   }
  44  |   if(!sourceKinds)return {save,view};
  45  |
  46  |   const host=document.querySelector('[data-battle-scene]'),selected=host.dataset.battleSelectedActor;
  47  |   const {officer_troop_types:types,battle_tactical:tactical,library}=view.catalog;
  48  |   const officers=Object.fromEntries(JSON.parse(host.dataset.battleMarkers).map(marker=>{
  49  |    const id=String(marker.id),row=types.officers[id];
  50  |    return [id,row&&{code:row.code,base_code:row.base_code,source_kind:row.source_kind}];
  51  |   }));
  52  |   const examples=sourceKinds.map(kind=>library.find(person=>person.affinity_source?.source_kind===kind))
  53  |    .filter(Boolean).map(({person_id,affinity,affinity_source})=>({person_id,affinity,affinity_source:{source_kind:affinity_source.source_kind}}));
  54  |   return {save,view:{catalog:{
  55  |    officer_troop_types:{schema:types.schema,rules_version:types.rules_version,officers},
  56  |    battle_tactical:{actors:{[selected]:{attack_targets:tactical.actors[selected].attack_targets}}},
  57  |    library:examples,
  58  |   }}};
  59  |  },{sourceKinds:openingTroopSources,facilityActor,tacticId});
  60  | }
  61  | async function load(page,value,name='controlled-soldier-boundary.json'){
  62  |  await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
  63  |  await idle(page);await expect(page.locator('#dialog')).toBeHidden();expect(await save(page)).toEqual(value);
  64  | }
  65  | async function dismissEvents(page){
  66  |  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  67  |  const events=page.locator('#event-dialog');
  68  |  for(let i=0;i<20&&await events.isVisible();i++){
  69  |   const skip=events.locator('[data-event-skip]');await(await skip.count()?skip:events.locator('[data-event-next]')).click();
  70  |  }
  71  |  await expect(events).toBeHidden();
  72  | }
  73  | async function openBattleHistoryEntry(page,event){
  74  |  const menu=page.locator('#utility-menu');
  75  |  if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
  76  |  await page.locator('#event-history').click();
  77  |  const dialog=page.locator('#event-dialog');
  78  |  await dialog.locator('[data-event-history-filter]').selectOption('battle');
  79  |  await dialog.locator('[data-event-history-entry="'+event.id+'"]').click();
  80  |  await expect(dialog.locator('[data-event-kind]')).toHaveAttribute('data-event-kind',event.kind);
  81  |  return dialog;
  82  | }
  83  | async function closeBattleHistoryEntry(dialog){
  84  |  await dialog.locator('[data-event-history-back]').click();
  85  |  await dialog.locator('[data-event-history-close]').click();
  86  |  await expect(dialog).toBeHidden();
  87  | }
  88  | async function control(page,id){
  89  |  const button=page.locator('#'+id),toggle=page.locator('#inspector-toggle');
  90  |  if(!await button.isVisible()&&await toggle.isVisible())await toggle.click();
  91  |  await expect(button).toBeEnabled();await button.click();
  92  | }
  93  | async function locale(page,value){
  94  |  const menu=page.locator('#utility-menu');if(await menu.getAttribute('open')===null)await menu.locator('summary').click();
  95  |  await page.locator('#language').selectOption(value);await menu.locator('summary').click();
  96  | }
  97  | async function cell(page,point,touch){
  98  |  const canvas=page.locator('[data-battle-canvas]');await canvas.scrollIntoViewIfNeeded();
  99  |  const box=await canvas.boundingBox();expect(box).toBeTruthy();
  100 |  const position={x:(point.x*16+8)*box.width/496,y:(point.y*16+8)*box.height/384};
  101 |  if(touch)await canvas.tap({position});else await canvas.click({position});
  102 | }
  103 | async function animation(page,{withView=true}={}){
  104 |  await expect.poll(()=>page.evaluate(()=>!document.body.classList.contains('busy')||!!document.querySelector('[data-battle-skip]:not([hidden])')),{timeout:90_000}).toBe(true);
  105 |  const committed=await save(page),skip=page.locator('[data-battle-skip]');
  106 |  if(await skip.isVisible()){
  107 |   try{await skip.click({timeout:1000});}catch(error){if(await skip.isVisible())throw error;}
  108 |  }
  109 |  await idle(page);await dismissEvents(page);
  110 |  const settled=await read(page,withView);
  111 |  expect(settled.save).toEqual(committed,'Animation completion or Skip cannot resolve another hit or draw extra random numbers');
  112 |  return settled;
  113 | }
  114 | async function waitSoldierReplay(page){
  115 |  // Poll on Node's real time while stepping only the presentation clock: two
  116 |  // real Worker RPCs may outlast a tight fixed-count loop of fake16ms ticks.
  117 |  await expect.poll(async()=>{await page.clock.runFor(16);return page.evaluate(()=>battleScene.state().scene==='soldier_step');},
  118 |   {timeout:30_000,intervals:[20,50,100]}).toBe(true);
  119 | }
  120 | async function evidence(page,testInfo,name){
  121 |  await page.screenshot({path:testInfo.outputPath(name+'.png'),fullPage:true});
  122 |  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  123 | }
  124 | async function attach(testInfo,name,value){const body=Buffer.from(JSON.stringify(value,null,2));await writeFile(testInfo.outputPath(name+'.json'),body);await testInfo.attach(name,{body,contentType:'application/json'});}
  125 | async function nativeMarkerPixels(page,marker,position){
  126 |  // Read the live backing buffer and the shipped atlas independently. The
  127 |  // detached reference canvas never replaces or writes into the game canvas.
  128 |  return page.evaluate(async({marker,position})=>{
```
