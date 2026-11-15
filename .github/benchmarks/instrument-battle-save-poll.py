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
original = text
for old, new in reversed(edits):
    assert original.count(new) == 1
    original = original.replace(new, old)
assert original == path.read_text()
path.write_text(text)
