/* Parse data-only CI reports and retain complete selected-case coverage. */
'use strict';
const assert=require('node:assert/strict'),weighted=require('./case-shards.cjs');
function aggregate(reports,selection,head,{baseline=weighted.BASELINE}={}){
 assert(/^[a-f0-9]{40}$/.test(head),'Timing reports require an exact source commit');
 assert.equal(reports.length,weighted.PROJECTS.length*weighted.COUNT,'Every device/shard timing report is required');
 const seen=new Set(),totals=[],cases=[];
 for(const report of reports){
  assert.equal(report.schema,'tk2-browser-case-timings-v1');assert.equal(report.commit,head,'Timing report belongs to another commit');
  assert(weighted.PROJECTS.includes(report.project));assert(Number.isInteger(report.shard)&&report.shard>=1&&report.shard<=weighted.COUNT);
  const identity=report.project+':'+report.shard;assert(!seen.has(identity),'Duplicate device/shard timing report');seen.add(identity);
  assert.equal(report.status,'passed','A failed or interrupted run cannot supply a successful timing baseline');
  const bin=weighted.selectedShard(selection,report.project,report.shard,{baseline});
  assert(Array.isArray(report.cases));assert.deepEqual(report.cases.map(row=>row.id).sort(),bin.cases.map(row=>row.id).sort(),'Observed timings omitted or duplicated weighted cases');
  let total=0;
  for(const row of report.cases){
   const canonical=bin.cases.find(c=>c.id===row.id);assert.equal(row.project,report.project);assert.equal(row.title,canonical.title);
   assert(Number.isSafeInteger(row.duration_ms)&&row.duration_ms>=0&&row.duration_ms<=86400000);
   assert(Array.isArray(row.attempts)&&row.attempts.length>=1&&row.attempts.length<=16);
   let sum=0;
   row.attempts.forEach((attempt,index)=>{
    assert.equal(attempt.retry,index,'Retry history must remain ordered and complete');
    assert(['passed','failed','timedOut','skipped','interrupted'].includes(attempt.status));
    assert(Number.isSafeInteger(attempt.duration_ms)&&attempt.duration_ms>=0&&attempt.duration_ms<=3600000);sum+=attempt.duration_ms;
   });
   assert.equal(row.attempts.at(-1).status,'passed','Selected browser cases must actually pass, not skip');
   assert.equal(sum,row.duration_ms);total+=sum;cases.push({...row,shard:report.shard});
  }
  totals.push({project:report.project,shard:report.shard,cases:report.cases.length,cost_multiplier:weighted.costMultiplier(baseline,report.project,report.shard)/1000,estimated_ms:bin.estimated_ms,observed_case_ms:total,unmeasured:bin.unmeasured});
 }
 for(const project of weighted.PROJECTS){
  const rows=cases.filter(row=>row.project===project);
  assert.deepEqual(rows.map(row=>row.id).sort(),selection.selectedCases.map(row=>row.id).sort(),'Every selected case must appear once per device');
 }
 const suggested=JSON.parse(JSON.stringify(baseline));
 suggested.source={commit:head,basis:'Passing per-case CI reports; reviewed before replacing the committed scheduling baseline',automatically_applied:false};
 // Weights are case costs on the reference runner. Undo this run's assigned
 // slot cost so later suggestions do not count the slower runner twice.
 for(const row of cases)suggested.projects[row.project][row.id]=Math.max(1,Math.min(3600000,Math.round(row.duration_ms*1000/weighted.costMultiplier(baseline,row.project,row.shard))));
 return {summary:{schema:'tk2-browser-duration-summary-v1',commit:head,baseline_source:baseline.source,coverage:'every selected case exactly once per device',selected_cases:selection.selectedCases.length,executions:cases.length,shards:totals.sort((a,b)=>a.project.localeCompare(b.project)||a.shard-b.shard),cases},suggested};
}
function markdown(summary){
 const rows=['## Browser case timings','','Case-duration totals exclude checkout, browser installation and artifact upload. Estimates apply the reviewed shard cost factor to normalized case weights.','','| Device | Shard | Cases | Cost factor | Estimated s | Observed case s |','| --- | ---: | ---: | ---: | ---: | ---: |'];
 for(const row of summary.shards)rows.push(`| ${row.project} | ${row.shard} | ${row.cases} | ${row.cost_multiplier} | ${Math.round(row.estimated_ms/1000)} | ${Math.round(row.observed_case_ms/1000)} |`);
 rows.push('','All selected cases were observed exactly once per device. New cases use the explicit default cost until their measurements are reviewed.','The suggested baseline is an artifact; it never changes test selection automatically.','');return rows.join('\n');
}
module.exports={aggregate,markdown};
