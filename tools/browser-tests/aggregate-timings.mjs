/* Only parse reports from the exact current run; never execute artifact code. */
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,lstatSync} from 'node:fs';
import path from 'node:path';
import scopes from './scope.cjs';
import weighted from './case-shards.cjs';
import reports from './duration-reports.cjs';
const [folder,...args]=process.argv.slice(2);assert(folder&&args.length===2&&args[0]==='--head','usage: aggregate-timings.mjs folder --head COMMIT');
const root=path.resolve(folder),selection=scopes.loadBrowserScope(),values=[];
for(const project of weighted.PROJECTS)for(let index=1;index<=weighted.COUNT;index++){
 const file=path.join(root,`${project}-shard-${index}.json`),info=lstatSync(file);assert(info.isFile()&&!info.isSymbolicLink()&&info.size<=1024*1024,'Only bounded regular timing data files are accepted');
 values.push(JSON.parse(readFileSync(file,'utf8')));
}
const {summary,suggested}=reports.aggregate(values,selection,args[1]);
writeFileSync(path.join(root,'summary.json'),JSON.stringify(summary,null,2)+'\n');
writeFileSync(path.join(root,'summary.md'),reports.markdown(summary));
writeFileSync(path.join(root,'suggested-case-durations.json'),JSON.stringify(suggested,null,2)+'\n');
console.log(JSON.stringify({commit:summary.commit,selected_cases:summary.selected_cases,executions:summary.executions,coverage:summary.coverage,shards:summary.shards}));
