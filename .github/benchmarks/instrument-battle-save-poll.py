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
if variant == 'baseline':
    add("async function tacticalRead(page){return page.evaluate(async()=>{const[a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);if(!a.ok||!b.ok)throw Error('Tactical inspection failed');const value=await b.json();return{save:await a.json(),view:value.view||value};});}",
        """async function tacticalRead(page,placementStage){
 return page.evaluate(async stage=>{
  const [saveResponse,stateResponse]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);
  if(!saveResponse.ok||!stateResponse.ok)throw Error('Tactical inspection failed');
  const value=await stateResponse.json(),view=value.view||value,save=await saveResponse.json();
  return {save,view};
 },placementStage);
}""")
    add("const before=await tacticalRead(page),placement=before.view.catalog.battle_tactical.placement;",
        "const before=await tacticalRead(page,'before'),placement=before.view.catalog.battle_tactical.placement;")
    add("const current=await tacticalRead(page);\n expect(current.save).toEqual(saved,'Reading the completed tactical preview cannot commit another action');",
        "const current=await tacticalRead(page,'after');\n expect(current.save).toEqual(saved,'Reading the completed tactical preview cannot commit another action');")

old = """async function tacticalRead(page,placementStage){
 return page.evaluate(async stage=>{
  const [saveResponse,stateResponse]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);
  if(!saveResponse.ok||!stateResponse.ok)throw Error('Tactical inspection failed');
  const value=await stateResponse.json(),view=value.view||value,save=await saveResponse.json();"""
new = """async function tacticalRead(page,placementStage){
 const evalStarted=profileClock.now();
 const result=await page.evaluate(async stage=>{
  const profile=window.__battleSaveProfile;
  const sample=stage?{stage,began:performance.now()}:null;
  if(sample){profile.placementReads.push(sample);profile.placementRequest=sample;}
  const responses=Promise.all([fetch('/api/save'),fetch('/api/state')]);
  if(sample)profile.placementRequest=null;
  const [saveResponse,stateResponse]=await responses;
  if(!saveResponse.ok||!stateResponse.ok)throw Error('Tactical inspection failed');
  if(sample)sample.stateParseStart=performance.now();
  const value=await stateResponse.json(),view=value.view||value;
  if(sample)sample.stateParseEnd=sample.saveParseStart=performance.now();
  const save=await saveResponse.json();
  if(sample)sample.saveParseEnd=performance.now();
  const reply=()=>{
"""
add(old, new)
add(" },placementStage);\n}", """  };
  const output=reply();
  if(sample)sample.done=performance.now();
  return output;
 },placementStage);
 const evalReceived=profileClock.now();
 if(placementStage)battleProfile.recordPlacement(page,placementStage,result,evalStarted,evalReceived);
 return result;
}""")

original = text
for old, new in reversed(edits):
    assert original.count(new) == 1
    original = original.replace(new, old)
assert original == path.read_text()
path.write_text(text)
