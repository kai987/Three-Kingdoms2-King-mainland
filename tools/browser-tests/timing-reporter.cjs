/* Machine-readable per-case cost, with no game inputs, screenshots or secrets. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const scopes=require('./scope.cjs'),shards=require('./case-shards.cjs');
class TimingReporter{
 constructor(options={}){this.rows=new Map();this.started=new Date().toISOString();this.outputDir=options.outputDir||path.resolve(__dirname,'../../build/browser-timings');}
 onTestEnd(test,result){
  const project=test.parent.project()?.name,row=scopes.CASE_REGISTRY.cases.find(row=>row.title===test.title);
  if(!shards.PROJECTS.includes(project)||!row)throw Error('Unregistered browser timing case/device');
  const key=project+'\0'+row.id;
  if(!this.rows.has(key))this.rows.set(key,{project,id:row.id,title:row.title,duration_ms:0,attempts:[]});
  const record=this.rows.get(key),duration=Math.max(0,Math.round(result.duration));
  record.duration_ms+=duration;record.attempts.push({retry:result.retry,status:result.status,duration_ms:duration});
 }
 onEnd(result){
  const project=process.env.BROWSER_PROJECT,index=process.env.BROWSER_SHARD;
  if(project!==undefined&&!shards.PROJECTS.includes(project)||index!==undefined&&!/^[12]$/.test(index))throw Error('Invalid browser timing artifact identity');
  const folder=path.resolve(this.outputDir);fs.mkdirSync(folder,{recursive:true});
  const name=project&&index?`${project}-shard-${index}.json`:'local.json';
  const data={schema:'tk2-browser-case-timings-v1',commit:process.env.GITHUB_SHA||null,project:project||null,shard:index?Number(index):null,started_at:this.started,status:result.status,cases:[...this.rows.values()]};
  fs.writeFileSync(path.join(folder,name),JSON.stringify(data,null,2)+'\n');
 }
}
module.exports=TimingReporter;
