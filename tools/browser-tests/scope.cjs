/* Fail-closed dependency selection for the immutable browser acceptance suite. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'../..');
const CANONICAL_GROUPS=Object.freeze(['boot','audio','map','scenarios','people','economy','logistics','battle','cloud','save']);
const CASE_REGISTRY=JSON.parse(fs.readFileSync(path.join(__dirname,'cases.json'),'utf8'));
const SOURCE_FILES=Object.freeze(['tests/browser_ui.spec.mjs','tests/browser_soldier_ui.spec.mjs']);
function acceptanceSource(root=ROOT){return SOURCE_FILES.map(file=>fs.readFileSync(path.join(root,file),'utf8')).join('\n');}
const fail=message=>{throw new Error('Browser test scope: '+message);};
function strings(value,label,{allowed=null,nonempty=false}={}){
 if(!Array.isArray(value)||value.some(item=>typeof item!=='string'||!item)||new Set(value).size!==value.length||nonempty&&!value.length)fail(label+' must be a'+(nonempty?' nonempty':'')+' unique string array');
 if(allowed)for(const item of value)if(!allowed.includes(item))fail('unknown '+label+' value '+JSON.stringify(item));
 return value;
}
function knownScenarioIds(root=ROOT){
 const index=JSON.parse(fs.readFileSync(path.join(root,'game/data/campaigns/index.json'),'utf8'));
 const ids=index.summary?.map(row=>row.id);strings(ids,'canonical scenario_ids',{nonempty:true});return ids;
}
function readCaseTitles(source){
 const starts=/^\s*test(?:\.(only|skip|fixme))?\s*\(/gm,titles=[];let match;
 while((match=starts.exec(source))){
  if(match[1])fail('acceptance cases cannot use test.'+match[1]);
  const rest=source.slice(starts.lastIndex),literal=/^\s*('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")\s*,/.exec(rest);
  if(!literal)fail('every acceptance case requires a literal registered title');
  const token=literal[1],inner=token.slice(1,-1);
  // Titles are data, never evaluated JavaScript. Decode ordinary JS string
  // escapes so quoting style does not weaken the completeness check.
  const title=inner.replace(/\\(u\{[a-fA-F0-9]+\}|u[a-fA-F0-9]{4}|x[a-fA-F0-9]{2}|[^])/g,(_,code)=>{
   if(code.startsWith('u{'))return String.fromCodePoint(parseInt(code.slice(2,-1),16));
   if(code[0]==='u'||code[0]==='x')return String.fromCharCode(parseInt(code.slice(1),16));
   return({n:'\n',r:'\r',t:'\t',b:'\b',f:'\f',v:'\v','0':'\0'})[code]??code;
  });
  titles.push(title);
 }
 if(!titles.length)fail('no acceptance cases were found');
 if(new Set(titles).size!==titles.length)fail('duplicate acceptance case title');
 return titles;
}
function validateRegistry(source,{registry=CASE_REGISTRY,scenarioIds=knownScenarioIds()}={}){
 if(registry?.schema!=='tk2-browser-cases-v1'||!Array.isArray(registry.cases)||!registry.cases.length)fail('invalid case registry');
 const ids=new Set(),titles=new Set();
 for(const row of registry.cases){
  if(!row||typeof row.id!=='string'||!/^[a-z][a-z0-9-]+$/.test(row.id)||ids.has(row.id))fail('invalid or duplicate registry id');
  if(typeof row.title!=='string'||!row.title||titles.has(row.title))fail('invalid or duplicate registry title');
  ids.add(row.id);titles.add(row.title);strings(row.groups,'groups',{allowed:CANONICAL_GROUPS,nonempty:true});strings(row.scenario_ids,'scenario_ids',{allowed:scenarioIds});
  if(!['unbound','fixed','catalog','selected'].includes(row.scenario_scope))fail('unknown scenario_scope for '+row.id);
  if(row.scenario_scope==='fixed'&&!row.scenario_ids.length)fail('fixed case has no scenario_ids: '+row.id);
 }
 const actual=readCaseTitles(source);
 for(const title of actual)if(!titles.has(title))fail('unregistered acceptance case '+JSON.stringify(title));
 for(const title of titles)if(!actual.includes(title))fail('registry case missing from source '+JSON.stringify(title));
 return registry.cases;
}
function validatePlan(plan,scenarioIds=knownScenarioIds()){
 if(!plan||typeof plan!=='object'||Array.isArray(plan))fail('plan must be a JSON object');
 if(typeof plan.full!=='boolean'||!['docs','scoped','full'].includes(plan.mode))fail('plan requires full:boolean and mode:docs|scoped|full');
 strings(plan.groups,'groups',{allowed:CANONICAL_GROUPS});strings(plan.scenario_ids,'scenario_ids',{allowed:scenarioIds});
 if(plan.full!==(plan.mode==='full'))fail('full and mode must agree');
 if(plan.mode==='docs'&&(plan.groups.length||plan.scenario_ids.length))fail('docs plan cannot request browser groups or scenarios');
 // Other fields belong to the shared CI planner and remain opaque provenance.
 return{...plan,groups:[...plan.groups],scenario_ids:[...plan.scenario_ids]};
}
function selectCases(plan,cases=CASE_REGISTRY.cases){
 if(plan.full)return [...cases];
 if(plan.mode==='docs')return [];
 const groups=new Set(plan.groups),scenarios=new Set(plan.scenario_ids);
 return cases.filter(row=>row.groups.some(group=>groups.has(group))&&(!scenarios.size||row.scenario_scope==='unbound'||row.scenario_scope==='selected'||row.scenario_scope==='fixed'&&row.scenario_ids.some(id=>scenarios.has(id))));
}
function selectScenarioIds(available,selection){
 strings(available,'available scenario_ids',{nonempty:true});
 const requested=selection.full?[]:selection.plan.scenario_ids;
 for(const id of requested)if(!available.includes(id))fail('requested scenario is absent from the real menu: '+id);
 const selected=requested.length?available.filter(id=>requested.includes(id)):[...available];
 if(!selected.length)fail('opening scenario selection is empty');return selected;
}
function loadBrowserScope({planPath=process.env.TK2_TEST_PLAN,root=ROOT,source,registry=CASE_REGISTRY}={}){
 const scenarioIds=knownScenarioIds(root);
 // Validate every source case before selecting a grep. Even CLI --grep cannot
 // conceal a new unregistered case, removed case, duplicate, or skipped case.
 const cases=validateRegistry(source??acceptanceSource(root),{registry,scenarioIds});
 let raw;
 if(planPath){
  const file=path.resolve(planPath);if(fs.statSync(file).size>1024*1024)fail('plan exceeds 1 MiB');
  try{raw=JSON.parse(fs.readFileSync(file,'utf8'));}catch(error){fail('cannot read plan JSON: '+error.message);}
 }else raw={full:true,mode:'full',groups:[...CANONICAL_GROUPS],scenario_ids:[]};
 const plan=validatePlan(raw,scenarioIds),selectedCases=selectCases(plan,cases);
 if(!selectedCases.length)fail(plan.mode==='docs'?'docs-only plan has no browser suite; do not launch Playwright':'requested plan selects no browser cases');
 const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 const grep=new RegExp('(?:'+selectedCases.map(row=>'\\b'+escape(row.title)+'$').join('|')+')');
 return{plan,full:plan.full,selectedCases,scenarioIds,grep};
}
module.exports={CANONICAL_GROUPS,CASE_REGISTRY,SOURCE_FILES,acceptanceSource,knownScenarioIds,readCaseTitles,validateRegistry,validatePlan,selectCases,selectScenarioIds,loadBrowserScope};
if(require.main===module){
 try{
  const args=process.argv.slice(2);if(args.length&&!(args.length===2&&args[0]==='--plan'))fail('usage: node scope.cjs [--plan path.json]');
  const selection=loadBrowserScope({planPath:args[1]||process.env.TK2_TEST_PLAN});
  process.stdout.write(JSON.stringify({full:selection.full,mode:selection.plan.mode,groups:selection.plan.groups,scenario_ids:selection.plan.scenario_ids,cases:selection.selectedCases.map(row=>({id:row.id,title:row.title})),grep:selection.grep.source},null,2)+'\n');
 }catch(error){process.stderr.write(error.message+'\n');process.exitCode=1;}
}
