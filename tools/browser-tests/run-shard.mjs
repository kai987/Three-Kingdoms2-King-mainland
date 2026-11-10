/* Run one reviewed weighted bin with the same pinned runner and case registry. */
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {mkdirSync,writeFileSync} from 'node:fs';
import scopes from './scope.cjs';
import shards from './case-shards.cjs';
const [project,rawIndex,...extra]=process.argv.slice(2),index=Number(rawIndex);
assert(shards.PROJECTS.includes(project)&&rawIndex===String(index)&&Number.isInteger(index)&&index>=1&&index<=shards.COUNT,'usage: run-shard.mjs device shard [--list]');
assert(extra.length===0||extra.length===1&&extra[0]==='--list','Unknown shard runner arguments');
const selection=scopes.loadBrowserScope(),bin=shards.selectedShard(selection,project,index);
console.error(JSON.stringify({project,shard:index,estimated_ms:bin.estimated_ms,cases:bin.cases.map(row=>row.id),unmeasured:bin.unmeasured}));
if(!bin.cases.length){
 console.error('Selected scope has no cases in this bin; coverage remains checked across all bins.');
 if(!extra.length){const folder=fileURLToPath(new URL('../../build/browser-timings/',import.meta.url));mkdirSync(folder,{recursive:true});writeFileSync(folder+project+'-shard-'+index+'.json',JSON.stringify({schema:'tk2-browser-case-timings-v1',commit:process.env.GITHUB_SHA||null,project,shard:index,started_at:new Date().toISOString(),status:'passed',cases:[]},null,2)+'\n');}
 process.exit(0);
}
const root=fileURLToPath(new URL('../../',import.meta.url)),cli=fileURLToPath(new URL('./node_modules/@playwright/test/cli.js',import.meta.url));
const args=[cli,'test','--config','tools/browser-tests/playwright.config.mjs','--project',project,'--fully-parallel','--grep',shards.grep(bin.cases),...(extra.length?['--list','--reporter','json']:[])];
const result=spawnSync(process.execPath,args,{cwd:root,env:{...process.env,BROWSER_PROJECT:project,BROWSER_SHARD:String(index)},stdio:'inherit'});
if(result.error)throw result.error;process.exit(result.status??1);
