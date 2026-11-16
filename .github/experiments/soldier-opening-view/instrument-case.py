"""Temporarily add the same opening-read timing to either test variant."""
from pathlib import Path
import sys

path = Path("tests/browser_soldier_ui.spec.mjs")
variant = sys.argv[1]
source = path.read_text()


def replace(old, new):
    global source
    if source.count(old) != 1:
        raise ValueError(f"Expected unique test anchor: {old}")
    source = source.replace(old, new)


replace("import {writeFile} from 'node:fs/promises';",
        "import {writeFile} from 'node:fs/promises';\n"
        "import {observeOpeningWorker,measureOpening} from '../.github/experiments/soldier-opening-view/probe.mjs';")
replace(" await page.clock.install();await opening(page);await load(page,macro.save);",
        " await observeOpeningWorker(page);\n await page.clock.install();await opening(page);await load(page,macro.save);")

request = "const [a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);\n"
check = "if(!a.ok||!b.ok)throw Error('Actual soldier state could not be inspected');\n"
parser = ("const probe=globalThis.__tk2OpeningProfile;\n"
          "if(probe){probe.browser.entry=probe.clock();probe.capturing=true;}\n"
          "const requests=[fetch('/api/save'),fetch('/api/state')];\n"
          "if(probe)probe.capturing=false;\n"
          "const [a,b]=await Promise.all(requests);\n"
          + check +
          "const state=await (probe?probe.parse('state',b):b.json());\n"
          "const save=await (probe?probe.parse('save',a):a.json());\n"
          "const view=state.view||state;\n")

if variant == 'baseline':
    replace(request+" "+check+" const state=await b.json();return {save:await a.json(),view:state.view||state};",
            parser+" return probe?probe.wrap({save,view}):{save,view};")
    replace("const before=await read(page),markers=", "const before=await measureOpening(page,testInfo,()=>read(page)),markers=")
elif variant == 'optimized':
    replace(request+"  "+check+"  const state=await b.json(),save=await a.json(),view=state.view||state;\n"
            "  if(!sourceKinds)return {save,view};",
            parser+"  if(!sourceKinds)return {save,view};")
    replace("  return {save,view:{catalog:{", "  const result={save,view:{catalog:{")
    replace("   library:examples,\n  }}};", "   library:examples,\n  }}};\n  return probe?probe.wrap(result):result;")
    replace("const before=await read(page,true,{openingTroopSources:troopSourceKinds}),markers=",
            "const before=await measureOpening(page,testInfo,()=>read(page,true,{openingTroopSources:troopSourceKinds})),markers=")
else:
    raise ValueError(variant)
path.write_text(source)
