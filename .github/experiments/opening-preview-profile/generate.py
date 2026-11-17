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
 const profile=await installOpeningProfile(page,testInfo);''')
replace(' await opening(page);', ''' const bootStarted=performance.now();
 await opening(page);
 await profile.openingReady(bootStarted);''')
replace(' for(const scenario of scenarios){', ''' for(const scenario of scenarios){
  const scenarioStarted=performance.now();''')
preview_start = body.index('  const previews=await page.evaluate')
preview_end = body.index('  for(const city of previews)', preview_start)
replace(body[preview_start:preview_end], '''  const {values:previews,metrics:previewMetrics}=await profile.previews(scenario,cities);
''')
replace('''  await page.locator('#begin').click();
  await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
  await waitIdle(page);await dismissHistoryOpening(page);
  const download=page.waitForEvent('download');await page.locator('#save').click();
  const saved=JSON.parse(await readFile(await(await download).path(),'utf8'));''', '''  const openingStarted=performance.now();
  await page.locator('#begin').click();
  await expect(page.locator('#allocate')).toBeEnabled({timeout:90_000});
  await waitIdle(page);await dismissHistoryOpening(page);
  const openingMs=performance.now()-openingStarted;
  const downloadStarted=performance.now();
  const download=page.waitForEvent('download');await page.locator('#save').click();
  const downloadedPath=await(await download).path();
  const downloadedAt=performance.now();
  const savedText=await readFile(downloadedPath,'utf8');
  const readAt=performance.now();
  const saved=JSON.parse(savedText);
  const parsedAt=performance.now();
  const downloadMs=downloadedAt-downloadStarted,saveReadMs=readAt-downloadedAt,saveJsonMs=parsedAt-readAt;
''')
replace('''  await page.locator('#main-menu').click();
  await expect(page.locator('#begin')).toBeEnabled();
 }''', '''  await page.locator('#main-menu').click();
  await expect(page.locator('#begin')).toBeEnabled();
  profile.scenario({scenario,cities:cities.length,preview:previewMetrics,openingMs,downloadMs,saveReadMs,saveJsonMs,
   saveBytes:Buffer.byteLength(savedText),scenarioMs:performance.now()-scenarioStarted});
 }''')
replace(' expect(errors.get(page)).toEqual([]);', ''' expect(errors.get(page)).toEqual([]);
 await profile.finish();''')
generated = (
    "import {installOpeningProfile} from './opening-profile-probe.mjs';\n" +
    source[:start] + body + source[end:]
)
Path('tests/opening-profile.spec.mjs').write_text(generated)
