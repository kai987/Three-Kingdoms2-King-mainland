"""Add timing to the pinned Playwright CDP path and one test on the runner."""
from pathlib import Path
import json

def replace(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Missing unique allocation profile anchor: {old[:125]!r}")
    return source.replace(old, new)

file = Path('tests/browser_ui.spec.mjs')
source = file.read_text()
begin = source.index("test('command-book confirmations and one paid city allocation flow preserve cancellation and save recovery',")
end = source.index("\n});", begin) + len("\n});")
test = source[begin:end]
test = replace(test, " await opening(page);",
    " const profile=await installAllocationProfile(page,testInfo);\n await opening(page);")
test = replace(test,
    " const closeFlow=async()=>{await closeDialog(page);await expect.poll(async()=>active(await read())).toBeNull();await waitIdle(page);};",
    " const closeFlow=()=>profile.close(()=>closeDialog(page),read=>expect.poll(()=>read(active)).toBeNull(),()=>waitIdle(page));")
test = replace(test,
    " const revision=()=>page.evaluate(async()=>{const response=await fetch('/api/state');if(!response.ok)throw Error('Revision inspection failed');const body=await response.json();return(body.view||body).revision;});",
    " const revision=()=>profile.revision();")
test = replace(test, " await page.reload();", " await profile.collect();\n await page.reload();")
test = replace(test, "\n});", "\n await profile.finish();\n});")

root = Path('tools/browser-tests/node_modules/playwright-core')
if json.loads((root/'package.json').read_text())['version'] != '1.64.1':
    raise ValueError('Playwright version changed')
bundle = root/'lib/coreBundle.js'
core = bundle.read_text()
a = core.index("var CRExecutionContext;")
b = core.index("// packages/playwright-core/src/server/chromium/crInput.ts", a)
region = core[a:b]
region = replace(region,
    '      async evaluateWithArguments(expression2, returnByValue, utilityScript, values, handles) {\n',
    '''      async evaluateWithArguments(expression2, returnByValue, utilityScript, values, handles) {
        const trace = returnByValue && typeof values[2] === "string" &&
          values[2].includes("__tk2AllocationProbe") ? globalThis.__tk2AllocationTrace : null;
''')
region = replace(region,
    '        return returnByValue ? parseEvaluationResultValue(remoteObject.value) : createHandle(utilityScript._context, remoteObject);',
    '''        if (trace) trace.row.cdpReceived = trace.now();
        return returnByValue ? parseEvaluationResultValue(remoteObject.value) : createHandle(utilityScript._context, remoteObject);''')

# The profiler stays outside the source checkout while the test runs.
import_url = (Path(__file__).parent/'probe.mjs').resolve().as_uri()
file.write_text(f"import {{installAllocationProfile}} from '{import_url}';\n" + source[:begin] + test + source[end:])
bundle.write_text(core[:a] + region + core[b:])
