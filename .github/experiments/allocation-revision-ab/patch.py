"""Instrument the same eight reads in the baseline and warm-cache variants."""
from pathlib import Path
import os

test = Path("tests/browser_ui.spec.mjs")
source = test.read_text()
title = "test('command-book confirmations and one paid city allocation flow preserve cancellation and save recovery'"
start = source.index(title)
end = source.index("\n});", start)
case = source[start:end]

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Missing or ambiguous profiling anchor: {old}")
    return text.replace(old, new)

case = replace_once(case, " await opening(page);",
    " const writeRevisionProfile=await prepareRevisionProbe(page,testInfo);\n await opening(page);")
request = {
    'baseline': "fetch('/api/state')",
    'warm': "fetch('/api/state',{tk2ViewCache:viewCache.token()})",
}[os.environ['REVISION_VARIANT']]
helper = (
    " const revision=()=>page.evaluate(async()=>{"
    f"const response=await {request};"
    "if(!response.ok)throw Error('Revision inspection failed');"
    "const body=await response.json();return(body.view||body).revision;});"
)
instrumented = (
    " const revision=()=>page.evaluate(async()=>{"
    "const sample=globalThis.__tk2AllocationRevisionProbe;"
    f"const response=await sample.request(()=>{request});"
    "if(!response.ok)throw Error('Revision inspection failed');"
    "sample.parseStart();const body=await response.json();sample.parseEnd();"
    "const revision=(body.view||body).revision;sample.finish(revision,body);return revision;});"
)
case = replace_once(case, helper, instrumented)
case = replace_once(case, " for(const ident of ids)current=await distribute(ident,'standalone-continuation');",
    " await writeRevisionProfile();\n for(const ident of ids)current=await distribute(ident,'standalone-continuation');")
probe = Path(__file__).with_name("probe.mjs").resolve().as_uri()
test.write_text(f"import {{prepareRevisionProbe}} from '{probe}';\n" + source[:start] + case + source[end:])
