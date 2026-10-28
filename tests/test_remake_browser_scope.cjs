/* Pure Node coverage of scope selection; no optional Playwright dependency. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawnSync}=require('node:child_process');
const scopes=require('../tools/browser-tests/scope.cjs');
const source=fs.readFileSync(path.join(__dirname,'browser_ui.spec.mjs'),'utf8'),known=scopes.knownScenarioIds();
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'tk2-browser-scope-'));
const plan=(groups,scenario_ids=[],extra={})=>({full:false,mode:'scoped',groups,scenario_ids,...extra});
let count=0;
function load(value,options={}){
 const file=path.join(directory,'plan-'+(++count)+'.json');fs.writeFileSync(file,JSON.stringify(value));
 return scopes.loadBrowserScope({planPath:file,...options});
}
try{
 const full=scopes.loadBrowserScope({planPath:''});
 assert.equal(full.full,true);assert.equal(full.selectedCases.length,27);
 assert.deepEqual(new Set(scopes.readCaseTitles(source)),new Set(scopes.CASE_REGISTRY.cases.map(row=>row.title)));
 const union=new Set();
 for(const group of scopes.CANONICAL_GROUPS){
  const selection=load(plan([group]));assert(selection.selectedCases.length>0,group+' must retain its registered coverage');
  for(const row of selection.selectedCases)union.add(row.id);
 }
 assert.deepEqual(union,new Set(full.selectedCases.map(row=>row.id)),'The canonical groups cover the same complete suite as full mode');
 assert.deepEqual(load(plan([...scopes.CANONICAL_GROUPS])).selectedCases.map(row=>row.id),full.selectedCases.map(row=>row.id),'A shared app change requesting all groups retains every full-suite case');
 const boot=load(plan(['boot'])),audio=load(plan(['audio']));
 const expected=['title-cover','recovery-title','dialogs-save','boot-retry'];
 assert.deepEqual(boot.selectedCases.map(row=>row.id),expected);assert.deepEqual(audio.selectedCases.map(row=>row.id),expected);
 const battle=new Set(load(plan(['battle'])).selectedCases.map(row=>row.id));
 assert(boot.selectedCases.every(row=>!battle.has(row.id)),'Boot and audio changes never pull unrelated battle acceptance');
 for(const group of ['economy','people','logistics','save'])assert(load(plan([group],['mainland217-07'])).selectedCases.some(row=>row.id==='command-books'));
 for(const group of ['battle','map','save'])assert(load(plan([group],['mainland208-10'])).selectedCases.some(row=>row.id==='battle-movement'));
 assert(battle.has('battle-layout'),'Battle changes exercise the real battlefield controls');
 for(const group of ['map','save'])assert(load(plan([group],['mainland208-10'])).selectedCases.some(row=>row.id==='battle-layout'));
 assert(!load(plan(['battle'],['mainland217-07'])).selectedCases.some(row=>row.id==='battle-layout'),'The fixed natural battle does not broaden unrelated scenario-local checks');
 for(const row of full.selectedCases){
  assert(full.grep.test('desktop-chromium browser_ui.spec.mjs '+row.title));
  assert.equal(boot.grep.test('touch-chromium browser_ui.spec.mjs '+row.title),expected.includes(row.id));
 }
 const local=load(plan(['scenarios'],['mainland184-02'],{schema:'shared-plan',head:'opaque-provenance',web:{enabled:true}}));
 assert.deepEqual(local.selectedCases.map(row=>row.id),['opening-catalog']);
 assert.deepEqual(scopes.selectScenarioIds(known,local),['mainland184-02'],'A local scenario plan cannot silently expand the deep opening loop to all 29');
 assert.deepEqual(scopes.selectScenarioIds(known,full),known);
 const historical=load(plan(['scenarios'],['mainland188-06']));
 assert.deepEqual(historical.selectedCases.map(row=>row.id),['han-sui-shu','opening-catalog']);
 assert.deepEqual(scopes.selectScenarioIds(known,historical),['mainland188-06']);
 assert.throws(()=>scopes.selectScenarioIds(known.filter(id=>id!=='mainland184-02'),local),/absent from the real menu/);
 assert.throws(()=>load(plan(['not-a-group'])),/unknown groups/);
 assert.throws(()=>load(plan(['scenarios'],['mainland999-01'])),/unknown scenario_ids/);
 assert.throws(()=>load(plan(['boot','boot'])),/unique string array/);
 assert.throws(()=>load(plan(['boot'],['mainland184-02','mainland184-02'])),/unique string array/);
 assert.throws(()=>load(plan(['logistics'],['mainland184-02'])),/selects no browser cases/);
 assert.throws(()=>load({full:false,mode:'docs',groups:[],scenario_ids:[]}),/docs-only plan has no browser suite/);
 assert.throws(()=>load({full:true,mode:'scoped',groups:[],scenario_ids:[]}),/full and mode must agree/);
 assert.throws(()=>load(plan(['boot']),{source:source+"\ntest('unregistered acceptance',async()=>{});\n"}),/unregistered acceptance case/,'Completeness is checked before a boot-only grep can conceal a new case');
 assert.throws(()=>load(plan(['boot']),{source:source.replace(/^test\(/m,'test.skip(')}),/cannot use test.skip/);
 assert.throws(()=>load(plan(['boot']),{source:source.replace(/^test\('([^']+)'/m,'test(`dynamic case`')}),/literal registered title/);
 const registry=JSON.parse(JSON.stringify(scopes.CASE_REGISTRY));registry.cases.pop();
 assert.throws(()=>load(plan(['boot']),{registry}),/unregistered acceptance case/);
 const broken=path.join(directory,'broken.json');fs.writeFileSync(broken,'{bad');
 assert.throws(()=>scopes.loadBrowserScope({planPath:broken}),/cannot read plan JSON/);
 const cli=spawnSync(process.execPath,[path.join(__dirname,'../tools/browser-tests/scope.cjs'),'--plan',broken],{encoding:'utf8'});
 assert.notEqual(cli.status,0);assert(cli.stderr.includes('Browser test scope:'));
 console.log('browser scopes: all 27 cases registered before grep, full/group union, bounded boot/audio, scenario-local deep openings, opaque plan provenance and fail-closed unknown/empty/invalid plans passed');
}finally{fs.rmSync(directory,{recursive:true,force:true});}
