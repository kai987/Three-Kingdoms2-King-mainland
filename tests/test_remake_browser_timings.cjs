/* Timing weights may change execution order, never case coverage or gameplay. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const scopes=require('../tools/browser-tests/scope.cjs'),weighted=require('../tools/browser-tests/case-shards.cjs'),reports=require('../tools/browser-tests/duration-reports.cjs');
const Reporter=require('../tools/browser-tests/timing-reporter.cjs');
const clone=value=>JSON.parse(JSON.stringify(value)),selection=scopes.loadBrowserScope({planPath:''}),head='a'.repeat(40);
for(const project of weighted.PROJECTS){
 const first=weighted.partition(selection.selectedCases,project),second=weighted.partition([...selection.selectedCases].reverse(),project);
 assert.deepEqual(first.map(bin=>bin.cases.map(row=>row.id).sort()),second.map(bin=>bin.cases.map(row=>row.id).sort()),'Input ordering cannot change weighted bin membership');
 const ids=first.flatMap(bin=>bin.cases.map(row=>row.id));assert.equal(new Set(ids).size,ids.length);assert.deepEqual([...ids].sort(),selection.selectedCases.map(row=>row.id).sort());
 assert(first.every(bin=>bin.cases.filter(row=>scopes.OPENING_CASES.includes(row.id)).length<=1),'The two full opening batches must run on different shards');
 const peak=Math.max(...first.map(bin=>bin.estimated_ms)),floor=Math.min(...first.map(bin=>bin.estimated_ms));assert(peak-floor<120000,'Measured full-suite bins should be within the explicit default case budget');
 assert(first.every(bin=>bin.cases.every(row=>new RegExp(weighted.grep(bin.cases)).test('p file '+row.title))));
 const tiny=weighted.partition(selection.selectedCases.slice(0,1),project);assert.equal(tiny[0].cases.length,1);assert.equal(tiny[1].cases.length,0);assert(!new RegExp(weighted.grep([])).test(selection.selectedCases[0].title));
}
const fresh={id:'new-case-without-history',title:'A new acceptance case with (punctuation) and $ data'};
const newBin=weighted.partition([fresh],'desktop-chromium')[0];assert.deepEqual(newBin.unmeasured,[fresh.id]);assert.equal(newBin.estimated_ms,120000);assert(new RegExp(weighted.grep([fresh])).test(fresh.title));assert(!new RegExp(weighted.grep([fresh])).test('A new acceptance case with punctuation and $ data'));
assert.equal(weighted.partition([{id:'constructor',title:'A valid registry ID that is also an inherited property'}],'desktop-chromium')[0].estimated_ms,120000);
for(const mutate of [b=>b.projects={x:{}},b=>b.default_duration_ms=0,b=>b.projects['desktop-chromium']['bad/key']=30,b=>b.projects['touch-chromium']['new-id']=-1]){const bad=clone(weighted.BASELINE);mutate(bad);assert.throws(()=>weighted.validateBaseline(bad));}
for(const costs of [null,[],{'unknown-device':[1000,1280]},{'touch-chromium':[1000]},{'touch-chromium':[1000,0]},{'touch-chromium':[1000,1280.5]},{'touch-chromium':[1000,2001]}]){const bad=clone(weighted.BASELINE);bad.shard_cost_multipliers=costs;assert.throws(()=>weighted.validateBaseline(bad));}
const unequal=clone(weighted.BASELINE);unequal.shard_cost_multipliers={'touch-chromium':Array.from({length:weighted.COUNT},(_,i)=>i+1===weighted.COUNT?2000:1000)};
const equalCases=Array.from({length:4*(weighted.COUNT-1)+2},(_,i)=>({id:`timed-case-${i}`,title:`Synthetic independent acceptance case ${i}`}));
unequal.projects['touch-chromium']=Object.fromEntries(equalCases.map(row=>[row.id,10000]));
const balanced=weighted.partition(equalCases,'touch-chromium',{baseline:unequal});
assert.deepEqual(balanced.map(bin=>bin.cases.length),Array.from({length:weighted.COUNT},(_,i)=>i+1===weighted.COUNT?2:4),'A twice-as-slow runner needs less work, not half the reference cost');
assert(balanced.every(bin=>bin.estimated_ms===40000));
assert.deepEqual(balanced.flatMap(bin=>bin.cases.map(row=>row.id)).sort(),equalCases.map(row=>row.id).sort());
assert.throws(()=>weighted.partition(equalCases,'touch-chromium',{baseline:unequal,count:weighted.COUNT===2?3:2}),'Measured slot costs cannot silently spread to unmeasured slots');
const equalCosts=clone(weighted.BASELINE);delete equalCosts.shard_cost_multipliers;
assert.deepEqual(weighted.partition(selection.selectedCases,'desktop-chromium'),weighted.partition(selection.selectedCases,'desktop-chromium',{baseline:equalCosts}),'Touch calibration cannot change desktop membership');
assert.throws(()=>weighted.partition(selection.selectedCases,'other-browser'));assert.throws(()=>weighted.selectedShard(selection,'desktop-chromium',0));
function samples(selected=selection){return weighted.PROJECTS.flatMap(project=>weighted.partition(selected.selectedCases,project).map(bin=>({schema:'tk2-browser-case-timings-v1',commit:head,project,shard:bin.index,status:'passed',cases:bin.cases.map(row=>({project,id:row.id,title:row.title,duration_ms:10,attempts:[{retry:0,status:'passed',duration_ms:10}]}))})));}
const sample=samples(),result=reports.aggregate(sample,selection,head);assert.equal(result.summary.executions,selection.selectedCases.length*2);assert.equal(result.suggested.source.automatically_applied,false);assert(reports.markdown(result.summary).includes('checkout'));
for(const report of sample)for(const row of report.cases)assert.equal(result.suggested.projects[report.project][row.id],Math.round(row.duration_ms*1000/weighted.costMultiplier(weighted.BASELINE,report.project,report.shard)),'Suggested case weights must undo the assigned runner cost instead of compounding it');
for(const mutate of [r=>r.pop(),r=>r[1]=r[0],r=>r[0].commit='b'.repeat(40),r=>r[0].cases.pop(),r=>r[0].cases.push(r[0].cases[0]),r=>r[0].cases[0].duration_ms=11,r=>r[0].cases[0].attempts[0].status='skipped',r=>r[0].status='failed']){const bad=clone(sample);mutate(bad);assert.throws(()=>reports.aggregate(bad,selection,head));}
const tiny={selectedCases:selection.selectedCases.slice(0,1)};assert.equal(reports.aggregate(samples(tiny),tiny,head).summary.executions,2,'Empty scoped bins retain explicit reports and do not invent executions');
// Exercise the actual reporter lifecycle without launching a browser or game.
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'tk2-browser-timings-')),reporter=new Reporter({outputDir:directory}),row=selection.selectedCases[0],test={title:row.title,parent:{project:()=>({name:'desktop-chromium'})}};
reporter.onTestEnd(test,{retry:0,status:'failed',duration:4});reporter.onTestEnd(test,{retry:1,status:'passed',duration:6});
const record=[...reporter.rows.values()][0];assert.equal(record.duration_ms,10);assert.equal(record.attempts.length,2);assert.throws(()=>reporter.onTestEnd({...test,title:'Unregistered'},{retry:0,status:'passed',duration:1}));
const priorProject=process.env.BROWSER_PROJECT,priorShard=process.env.BROWSER_SHARD,priorHead=process.env.GITHUB_SHA;
try{
 process.env.BROWSER_PROJECT='desktop-chromium';process.env.BROWSER_SHARD='1';process.env.GITHUB_SHA=head;reporter.onEnd({status:'passed'});
 const stored=JSON.parse(fs.readFileSync(path.join(directory,'desktop-chromium-shard-1.json'),'utf8'));
 assert.equal(stored.commit,head);assert.equal(stored.schema,'tk2-browser-case-timings-v1');assert.equal(stored.cases[0].duration_ms,10);assert.deepEqual(stored.cases[0].attempts.map(a=>a.status),['failed','passed']);
}finally{for(const [key,value]of [['BROWSER_PROJECT',priorProject],['BROWSER_SHARD',priorShard],['GITHUB_SHA',priorHead]]){if(value===undefined)delete process.env[key];else process.env[key]=value;}fs.rmSync(directory,{recursive:true,force:true});}
const fixtures=fs.mkdtempSync(path.join(os.tmpdir(),'tk2-browser-timing-gate-'));
try{
 for(const value of sample)fs.writeFileSync(path.join(fixtures,`${value.project}-shard-${value.shard}.json`),JSON.stringify(value));
 const script=path.resolve(__dirname,'../tools/browser-tests/aggregate-timings.mjs'),args=[script,fixtures,'--head',head],env={...process.env,TK2_TEST_PLAN:''};
 const result=spawnSync(process.execPath,args,{encoding:'utf8',env});assert.equal(result.status,0,result.stderr);assert.equal(JSON.parse(result.stdout).executions,selection.selectedCases.length*2);
 assert.equal(JSON.parse(fs.readFileSync(path.join(fixtures,'summary.json'),'utf8')).coverage,'every selected case exactly once per device');
 const missing=path.join(fixtures,'touch-chromium-shard-2.json');fs.unlinkSync(missing);assert.notEqual(spawnSync(process.execPath,args,{encoding:'utf8',env}).status,0,'The real aggregate command must reject a missing report');
 const outside=path.join(fixtures,'outside.json');fs.writeFileSync(outside,JSON.stringify(sample.at(-1)));fs.symlinkSync(outside,missing);assert.notEqual(spawnSync(process.execPath,args,{encoding:'utf8',env}).status,0,'A symlink cannot replace a bounded regular timing artifact');
}finally{fs.rmSync(fixtures,{recursive:true,force:true});}
console.log('browser timings: reviewed weighted bins, deterministic membership, complete coverage, new-case fallback, empty scopes, retry cost and hostile/missing report rejection passed');
