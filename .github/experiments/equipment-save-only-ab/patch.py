"""Attach the timing probe to equipment's existing five checkpoints."""
from pathlib import Path
import os

test = Path("tests/browser_ui.spec.mjs")
source = test.read_text()
title = "test('actual equipment appears in city intelligence and person details"
start = source.index(title)
end = source.index("\n});", start)
case = source[start:end]

def augment(old, new):
    global case
    if case.count(old) != 1:
        raise ValueError(f"Missing or ambiguous equipment anchor: {old}")
    case = case.replace(old, new)

augment(" await opening(page);", " const profile=await installEquipmentProfile(page,testInfo);\n await opening(page);")
augment(
    " const read=()=>page.evaluate(async()=>{const a=await fetch('/api/save'),b=await fetch('/api/state');if(!a.ok||!b.ok)throw new Error('Equipment read-only state failed');const value=await b.json();return {save:await a.json(),view:value.view||value};});",
    " const read=label=>profile.read(label);",
)
for original, tagged in (
    ("initial=await read()", "initial=await read('initial')"),
    ("let after=await read()", "let after=await read('after-purchase')"),
    ("const restored=await read()", "const restored=await read('after-reload')"),
):
    augment(original, tagged)
for label, assertion in (
    ('after-inspection', 'Equipment inspection'),
    ('after-quotes', 'Shop quotes'),
):
    sub = "expect(%s).toEqual(initial.save,'" + assertion
    if os.environ['EQUIPMENT_VARIANT'] == 'baseline':
        augment(sub % "(await read()).save", sub % f"(await read('{label}')).save")
    else:
        augment(sub % "await tacticalSave(page)", sub % f"await profile.save('{label}')")
augment("await page.reload();await enterScenarioMenu(page);", "await profile.beforeReload();await page.reload();await enterScenarioMenu(page);")
augment("expect(errors.get(page)).toEqual([]);", "expect(errors.get(page)).toEqual([]);await profile.finish({initial:initial.save.state.rng,purchased:after.save.state.rng,restored:restored.save.state.rng});")
probe = Path(__file__).with_name("probe.mjs").resolve().as_uri()
test.write_text(f"import {{installEquipmentProfile}} from '{probe}';\n" + source[:start] + case + source[end:])
