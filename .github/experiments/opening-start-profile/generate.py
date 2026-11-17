from pathlib import Path

source = Path('tests/browser_ui.spec.mjs').read_text()
helper = '''async function dismissHistoryOpening(page){
 const events=page.locator('#event-dialog');
 await expect(events).toBeVisible();
'''
assert source.count(helper) == 1
source = source.replace(helper, '''async function dismissHistoryOpening(page,onVisible){
 const events=page.locator('#event-dialog');
 await expect(events).toBeVisible();
 onVisible?.();
''')
start = source.index('async function verifyOpeningBatch(')
end = source.index("\ntest('first batch of real Worker openings", start)
body = source[start:end]

def replace(old, new):
    global body
    assert body.count(old) == 1, old
    body = body.replace(old, new)

replace(' test.setTimeout(600_000);', ''' test.setTimeout(600_000);
 const startProfile=await installStartProfile(page,testInfo);''')
replace(' await opening(page);', ''' await opening(page);
 await startProfile.attach();''')
replace('''  await page.locator('#begin').click();
  await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
  await waitIdle(page);await dismissHistoryOpening(page);''', '''  const chromiumBefore=await startProfile.arm(scenario);
  const startAt=performance.now();
  await page.locator('#begin').click();
  const clickReturnedAt=performance.now();
  await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
  await waitIdle(page);
  const idleAt=performance.now();
  let observedEventAt;
  await dismissHistoryOpening(page,()=>{observedEventAt=performance.now();});
  const dismissedAt=performance.now();
  await startProfile.scenario({
   scenario,cities, totalMs:dismissedAt-startAt,
   clickMs:clickReturnedAt-startAt, idleMs:idleAt-clickReturnedAt,
   eventWaitMs:observedEventAt-idleAt, eventDismissMs:dismissedAt-observedEventAt,
  },chromiumBefore);''')
replace(' expect(errors.get(page)).toEqual([]);', ''' expect(errors.get(page)).toEqual([]);
 await startProfile.finish();''')
generated = "import {installStartProfile} from './opening-start-probe.mjs';\n" + source[:start] + body + source[end:]
Path('tests/opening-start-profile.spec.mjs').write_text(generated)
