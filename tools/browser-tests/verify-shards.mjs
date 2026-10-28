/* Ask the pinned Playwright runner to prove that both CI shards together
 * retain every selected acceptance case exactly once for this device. */
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import scopes from './scope.cjs';

const project=process.argv[2];
assert(['desktop-chromium','touch-chromium'].includes(project),'An explicit CI device is required');
const root=fileURLToPath(new URL('../../',import.meta.url));
const cli=fileURLToPath(new URL('./node_modules/@playwright/test/cli.js',import.meta.url));
const selection=scopes.loadBrowserScope();
const expected=selection.selectedCases.map(row=>row.title).sort();
const collect=suites=>suites.flatMap(suite=>[
 ...(suite.specs||[]).flatMap(spec=>(spec.tests||[]).map(test=>{
  assert.equal(test.projectName,project,'A different device entered this shard');
  return spec.title;
 })),...collect(suite.suites||[])
]);
const shards=[];
for(let index=1;index<=2;index++){
 const result=spawnSync(process.execPath,[cli,'test','--config','tools/browser-tests/playwright.config.mjs',
  '--project',project,'--fully-parallel','--shard',`${index}/2`,'--list','--reporter','json'],
  {cwd:root,env:process.env,encoding:'utf8',maxBuffer:8*1024*1024});
 assert.equal(result.status,0,result.stderr||'Playwright discovery failed');
 const report=JSON.parse(result.stdout);
 assert.deepEqual(report.errors,[],'Playwright discovery errors cannot be ignored');
 shards.push({index,titles:collect(report.suites)});
}
const actual=shards.flatMap(shard=>shard.titles).sort();
assert.deepEqual(actual,expected,'CI shards omitted or duplicated selected browser cases');
assert.equal(new Set(actual).size,actual.length,'A browser case appeared in two shards');
console.log(JSON.stringify({project,selected:expected.length,shards:shards.map(shard=>({index:shard.index,count:shard.titles.length})),coverage:'every selected case exactly once'}));
