"""Add profiling to the test runner's copy of the existing Playwright spec."""
from pathlib import Path
import sys

path = Path('tests/browser_ui.spec.mjs')
text = path.read_text()
edits = []


def add(old, new):
    global text
    assert text.count(old) == 1, old
    edits.append((old, new))
    text = text.replace(old, new)


add("const browserScope=browserScopes.loadBrowserScope();", """import {performance as profileClock} from 'node:perf_hooks';
import * as battleProfile from '../.github/benchmarks/battle-save-poll.mjs';

const browserScope=browserScopes.loadBrowserScope();
test.beforeEach(({page},info)=>battleProfile.install(page,info.title));
test.afterEach(({page},info)=>battleProfile.record(page,info));""")
add("const pending=await page.evaluate(async()=>{const r=await fetch('/api/save');const s=(await r.json()).state;return !!s.battle?.extended?.siege;});",
    """const pending=await page.evaluate(async()=>{
    const profile=window.__battleSaveProfile,probe=profile.poll('macro-poll');
    const r=await fetch('/api/save');const s=(await r.json()).state,decision=!!s.battle?.extended?.siege;
    profile.finish(probe,decision);return decision;
   });""")
variant, = sys.argv[1:]
assert variant in ('baseline', 'response')
if variant == 'baseline':
    add("const before=await tacticalSave(page),round=before.state.battle.extended.siege.round;",
        """const before=await tacticalSave(page),round=before.state.battle.extended.siege.round;
 const roundStarted=await battleProfile.beginRound(page);""")
    add("await expect.poll(()=>page.evaluate(async previous=>{const r=await fetch('/api/save'),s=(await r.json()).state,b=s.battle;return !b?.extended?.siege||!!b.extended.duel||b.extended.siege.round>previous;},round)).toBe(true);",
        """const pollStarted=profileClock.now();
 await expect.poll(()=>page.evaluate(async previous=>{
  const profile=window.__battleSaveProfile,probe=profile.poll('round-poll');
  const r=await fetch('/api/save'),s=(await r.json()).state,b=s.battle;
  const decision=!b?.extended?.siege||!!b.extended.duel||b.extended.siege.round>previous;
  profile.finish(probe,decision);return decision;
 },round)).toBe(true);
 battleProfile.phase(page,'commit-wait',pollStarted);""")
else:
    add("const revision=await page.evaluate(()=>view.revision);",
        """const revision=await page.evaluate(()=>view.revision);
 const roundStarted=await battleProfile.beginRound(page);""")
    add("await waitForSoldierStep(page,{battleId:battle.id,round:battle.extended.siege.round,revision});",
        """const observed=profileClock.now();
 await waitForSoldierStep(page,{battleId:battle.id,round:battle.extended.siege.round,revision});
 battleProfile.phase(page,'commit-wait',observed);""")
add("Playing or skipping a committed soldier round cannot apply its damage or RNG twice');\n return {save:settled};",
    """Playing or skipping a committed soldier round cannot apply its damage or RNG twice');
 await battleProfile.finishRound(page,roundStarted,before,committed,settled);
 return {save:settled};""")
add("async function tacticalOpening(page){\n await opening(page);await page.locator('#scenario').selectOption('mainland208-10');",
    """async function tacticalOpening(page){
 const openingStarted=profileClock.now();
 await opening(page);battleProfile.phase(page,'opening',openingStarted);
 const marchStarted=profileClock.now();
 await page.locator('#scenario').selectOption('mainland208-10');""")
add(" // The tactical scene also hosts sequential pre-battle placement. Complete",
    """ battleProfile.phase(page,'march-through-arrivals',marchStarted);
 const placementStarted=profileClock.now();
 // The tactical scene also hosts sequential pre-battle placement. Complete""")
add("expect(current.save.state.extension.command_books).toEqual(before.save.state.extension.command_books);\n return current;",
    """expect(current.save.state.extension.command_books).toEqual(before.save.state.extension.command_books);
 battleProfile.phase(page,'manual-placement',placementStarted);
 return current;""")
add("await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'tactical-grid-acceptance.json'",
    """await battleProfile.snapshot(page);
 await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'tactical-grid-acceptance.json'""")
add(" await page.goto('./');\n await enterScenarioMenu(page);",
    """ await battleProfile.measure(page,'document-navigation',()=>page.goto('./'));
 await enterScenarioMenu(page);""")
add("async function enterScenarioMenu(page){\n await expect(page.locator('#begin')).toBeEnabled({timeout:180_000});",
    """async function enterScenarioMenu(page){
 await battleProfile.measure(page,'scenario-ready',()=>expect(page.locator('#begin')).toBeEnabled({timeout:180_000}));""")
add(" await expect.poll(()=>page.evaluate(()=>!document.body.classList.contains('busy')||!!document.querySelector('[data-battle-skip]:not([hidden])')),{timeout:90_000}).toBe(true);",
    """ const settleStarted=profileClock.now();
 await battleProfile.measure(page,'wait-skip-or-idle',()=>expect.poll(()=>page.evaluate(()=>!document.body.classList.contains('busy')||!!document.querySelector('[data-battle-skip]:not([hidden])')),{timeout:90_000}).toBe(true));""")
add(" await waitIdle(page);await tacticalDismiss(page);\n if(returnToMacro){",
    """ await waitIdle(page);
 battleProfile.phase(page,'settle-before-event-dismiss',settleStarted);
 await tacticalDismiss(page);
 if(returnToMacro){""")
add("async function tacticalDismiss(page){",
    """async function tacticalDismiss(page){
 return battleProfile.measure(page,'event-dismiss',()=>tacticalDismissActions(page));
}
async function tacticalDismissActions(page){""")
add(" const marchStarted=profileClock.now();",
    """ const setupStarted=profileClock.now();""")
add(" await page.locator('#city-jump').selectOption('jiujiang');await clickCityCommand(page,'depart');",
    """ battleProfile.phase(page,'start-campaign',setupStarted);
 const marchStarted=profileClock.now();
 await page.locator('#city-jump').selectOption('jiujiang');await clickCityCommand(page,'depart');""")
add(" for(const id of ['end-turn','run-ai','process-arrivals']){await page.locator('#'+id).click();await waitIdle(page);await tacticalDismiss(page);}",
    """ for(const id of ['end-turn','run-ai','process-arrivals'])await battleProfile.measure(page,id,async()=>{
  await page.locator('#'+id).click();await waitIdle(page);await tacticalDismiss(page);
 });""")
add(" const before=await tacticalRead(page),placement=before.view.catalog.battle_tactical.placement;",
    """ const before=await battleProfile.measure(page,'placement-initial-read',()=>tacticalRead(page)),placement=before.view.catalog.battle_tactical.placement;""")
add("  await tacticalControl(page,'battle-place-confirm');await waitIdle(page);await tacticalDismiss(page);\n  saved=await tacticalSave(page);",
    """  await battleProfile.measure(page,'placement-confirm',async()=>{
   await tacticalControl(page,'battle-place-confirm');await waitIdle(page);
  });
  await tacticalDismiss(page);
  saved=await battleProfile.measure(page,'placement-checkpoint',()=>tacticalSave(page));""")
add(" const current=await tacticalRead(page);\n expect(current.save).toEqual(saved,",
    """ const current=await battleProfile.measure(page,'placement-final-read',()=>tacticalRead(page));
 expect(current.save).toEqual(saved,""")
add("async function tacticalApproach(page,{touch=false,preferred=null,max=18}={}){",
    """async function tacticalApproach(page,options){
 return battleProfile.measure(page,'tactical-approach',()=>tacticalApproachActions(page,options));
}
async function tacticalApproachActions(page,{touch=false,preferred=null,max=18}={}){""")
add("async function tacticalSoldierExchange(page,{bothSides=false,anySide=false,testInfo=null,label='soldier-contact'}={}){",
    """async function tacticalSoldierExchange(page,options){
 return battleProfile.measure(page,'soldier-exchange',()=>tacticalSoldierExchangeActions(page,options));
}
async function tacticalSoldierExchangeActions(page,{bothSides=false,anySide=false,testInfo=null,label='soldier-contact'}={}){""")
add(" const committed=await tacticalSave(page);await tacticalSettle(page);\n const settled=await tacticalSave(page);",
    """ const committed=await battleProfile.measure(page,'round-committed-save',()=>tacticalSave(page));await tacticalSettle(page);
 const settled=await battleProfile.measure(page,'round-settled-save',()=>tacticalSave(page));""")
add(" await page.screenshot({path,fullPage});",
    """ await battleProfile.measure(page,'screenshot',()=>page.screenshot({path,fullPage}));""")
add(" await page.reload();await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'tactical-grid-acceptance.json'",
    """ const reloadStarted=profileClock.now();
 await battleProfile.measure(page,'document-reload',()=>page.reload());await enterScenarioMenu(page);await page.locator('#load').click();await page.locator('#save-file').setInputFiles({name:'tactical-grid-acceptance.json'""")
add(" const restored={save:await tacticalSave(page)};expect(restored.save).toEqual(saved.save,'Raw save reload retains every coordinate, AP balance, commander and RNG value');",
    """ const restored={save:await tacticalSave(page)};
 battleProfile.phase(page,'reload-and-restore',reloadStarted);
 expect(restored.save).toEqual(saved.save,'Raw save reload retains every coordinate, AP balance, commander and RNG value');""")

original = text
for old, new in reversed(edits):
    assert original.count(new) == 1
    original = original.replace(new, old)
assert original == path.read_text()
path.write_text(text)
