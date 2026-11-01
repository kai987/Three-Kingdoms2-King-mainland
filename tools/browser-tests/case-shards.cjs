/* Deterministic duration-weighted partitioning; never removes selected cases.
 * Timing baselines are reviewed repository data, not downloaded executable input. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const PROJECTS=Object.freeze(['desktop-chromium','touch-chromium']),COUNT=2;
const BASELINE=JSON.parse(fs.readFileSync(path.join(__dirname,'case-durations.json'),'utf8'));
function validateBaseline(value){
 if(value?.schema!=='tk2-browser-duration-baseline-v1'||!value.projects||typeof value.projects!=='object'||Array.isArray(value.projects))throw Error('Unknown browser duration baseline');
 if(!Number.isSafeInteger(value.default_duration_ms)||value.default_duration_ms<1||value.default_duration_ms>3600000)throw Error('Invalid default browser duration');
 if(Object.keys(value.projects).sort().join(',')!==[...PROJECTS].sort().join(','))throw Error('Duration baseline must name both exact devices');
 for(const rows of Object.values(value.projects)){
  if(!rows||typeof rows!=='object'||Array.isArray(rows))throw Error('Invalid browser duration rows');
  for(const[id,ms]of Object.entries(rows))if(!/^[a-z][a-z0-9-]+$/.test(id)||!Number.isSafeInteger(ms)||ms<1||ms>3600000)throw Error('Invalid browser case duration');
 }
 return value;
}
function partition(cases,project,{baseline=BASELINE,count=COUNT}={}){
 validateBaseline(baseline);
 if(!PROJECTS.includes(project)||!Number.isSafeInteger(count)||count<1||count>16)throw Error('Invalid browser shard device/count');
 if(!Array.isArray(cases)||!cases.length||new Set(cases.map(r=>r.id)).size!==cases.length)throw Error('A shard requires unique selected cases');
 const weights=baseline.projects[project],measured=id=>Object.prototype.hasOwnProperty.call(weights,id),duration=row=>measured(row.id)?weights[row.id]:baseline.default_duration_ms;
 const bins=Array.from({length:count},(_,i)=>({index:i+1,estimated_ms:0,cases:[],unmeasured:[]}));
 for(const row of [...cases].sort((a,b)=>duration(b)-duration(a)||(a.id<b.id?-1:a.id>b.id?1:0))){
  if(!/^[a-z][a-z0-9-]+$/.test(row.id)||typeof row.title!=='string'||!row.title)throw Error('Invalid selected browser case');
  const next=[...bins].sort((a,b)=>a.estimated_ms-b.estimated_ms||a.index-b.index)[0];
  next.cases.push(row);next.estimated_ms+=duration(row);if(!measured(row.id))next.unmeasured.push(row.id);
 }
 // Keep discovery/replay order stable inside each bin; scheduling weights do
 // not alter what a test does or its scenario/seed/timeout.
 const order=new Map(cases.map((row,i)=>[row.id,i]));for(const bin of bins)bin.cases.sort((a,b)=>order.get(a.id)-order.get(b.id));
 return bins;
}
function grep(cases){const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return cases.length?'(?:'+cases.map(row=>'\\b'+escape(row.title)+'$').join('|')+')':'(?!)';}
function selectedShard(selection,project,index,options){
 if(!Number.isInteger(index)||index<1||index>(options?.count??COUNT))throw Error('Invalid browser shard index');
 return partition(selection.selectedCases,project,options)[index-1];
}
module.exports={PROJECTS,COUNT,BASELINE,validateBaseline,partition,grep,selectedShard};
