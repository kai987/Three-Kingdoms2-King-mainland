"""Insert temporary measurement hooks in the one frozen browser test."""
from pathlib import Path

test = Path("tests/browser_ui.spec.mjs")
source = test.read_text()
title = "test('command-book confirmations and one paid city allocation flow preserve cancellation and save recovery'"
start = source.index(title)
end = source.index("\n});", start)
case = source[start:end]

def replace(old, new):
    global case
    if case.count(old) != 1:
        raise ValueError(f"Missing or ambiguous profiling anchor: {old}")
    case = case.replace(old, new)

replace(
    " await opening(page);",
    " const profile=await prepareRevisionProfile(page,testInfo);\n await opening(page);",
)
replace(
    " const revision=()=>page.evaluate(async()=>{const response=await fetch('/api/state');if(!response.ok)throw Error('Revision inspection failed');const body=await response.json();return(body.view||body).revision;});",
    " await profile.attach();\n const revision=()=>profile.revision();",
)
replace(
    " for(const ident of ids)current=await distribute(ident,'standalone-continuation');",
    " await profile.finish();\n for(const ident of ids)current=await distribute(ident,'standalone-continuation');",
)
probe = Path(__file__).with_name("probe.mjs").resolve().as_uri()
test.write_text(f"import {{prepareRevisionProfile}} from '{probe}';\n" + source[:start] + case + source[end:])
