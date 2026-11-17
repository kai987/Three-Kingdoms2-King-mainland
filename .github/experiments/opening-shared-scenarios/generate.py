from pathlib import Path

source = Path('tests/browser_ui.spec.mjs').read_text()
start = source.index('async function verifyOpeningBatch(')
end = source.index("\ntest('first batch of real Worker openings", start)
body = source[start:end]

def replace(old, new):
    global body
    assert body.count(old) == 1, old
    body = body.replace(old, new)

replace(' test.setTimeout(600_000);', ''' test.setTimeout(600_000);
 const trial=await installOpeningTrial(page,testInfo);''')
replace(' await opening(page);', ''' await Promise.all([trial.attach(),opening(page)]);
 await trial.capture(null);''')
replace("  const saved=JSON.parse(await readFile(await(await download).path(),'utf8'));", """  const originalSave=await readFile(await(await download).path(),'utf8');
  const saved=JSON.parse(originalSave);
  await trial.capture(scenario);
  trial.save(scenario,cities,originalSave);""")
replace(' expect(errors.get(page)).toEqual([]);', ''' expect(errors.get(page)).toEqual([]);
 await trial.finish();''')
prefix = "import {installOpeningTrial} from './opening-shared-probe.mjs';\n"
Path('tests/opening-shared-profile.spec.mjs').write_text(prefix+source[:start]+body+source[end:])
