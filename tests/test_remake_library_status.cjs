/* Verify the shipped UI categorizes runtime entry, not an opening placement plan. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'game/app.js'),'utf8');
const options=[],listeners=[];
const context={GameI18n:{locale:'zh-Hant'},escapeHtml:String,document:{addEventListener:(...row)=>listeners.push(row),querySelectorAll:()=>options}};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('// Classify actual runtime entry'),source.indexOf('function personStatus(p)')),context);
const status=p=>context.libraryEntryStatus({missing:[],alive:null,year_state:'available',...p});
assert.equal(status({alive:true,faction:'wei',year_state:'dead',era_assignment:{status:'pending_history'}}),'serving');
assert.equal(status({alive:true,faction:null,location:'henan',era_assignment:{status:'serving'}}),'free');
assert.equal(status({alive:false,faction:'wei',era_assignment:{status:'serving'}}),'retired');
assert.equal(status({year_state:'not_born',era_assignment:{status:'pending_history'}}),'not_born');
assert.equal(status({year_state:'not_appeared',era_assignment:{status:'serving'}}),'not_appeared');
assert.equal(status({year_state:'death_year_review'}),'death_review');
assert.equal(status({year_state:'death_year_review',era_assignment:{status:'pending_capacity',death_year_resolved:true}}),'pending_capacity');
assert.equal(status({era_assignment:{status:'serving',city:'henan',faction:'wei'}}),'unentered');
assert.equal(status({era_assignment:{status:'free',city:'henan'}}),'unentered');
assert(context.libraryPlacementFilter({missing:['virtue'],alive:null,year_state:'available'},'entry:unentered'));
assert.equal(listeners[0][0],'game-language-change');
options.push({dataset:{libraryEntry:'pending_history',l10nNative:'zh-Hant'},textContent:''});
context.GameI18n.locale='ja';context.refreshLibraryEntryLabels();
assert.equal(options[0].textContent,'所属未確定');assert.equal(options[0].dataset.l10nNative,'ja');
context.GameI18n.locale='zh-Hant';context.refreshLibraryEntryLabels();assert.equal(options[0].textContent,'歸屬待考');
const python=spawnSync(process.env.PYTHON||'python3',['-B','-c',`
import json,sys
from pathlib import Path
sys.path.insert(0,'source')
from remake.campaign import Campaign,Catalog
rows=[]
for date,side in [('217-07','wu'),('191-10','wei'),('201-05','wei')]:
    game=Campaign(Catalog(Path('game/data/main-scenarios-v13')/(date+'.json')))
    game.state=game._new(side,2026)
    game.validate(game.state)
    rows.append(dict(date=date,library=game._expanded_catalog_view(game.state)['library']))
print(json.dumps(rows,ensure_ascii=False))
`],{cwd:root,encoding:'utf8',maxBuffer:16*1024*1024,env:{...process.env,MARCH_CORE_BACKEND:'python',PYTHONDONTWRITEBYTECODE:'1'}});
if(python.status!==0)throw new Error(python.stderr||'Runtime fixture generation failed');
const rows=JSON.parse(python.stdout);
for(const row of rows){
 const before=JSON.stringify(row.library),counts=JSON.parse(JSON.stringify(context.libraryEntryCounts(row.library)));
 assert.equal(Object.values(counts).reduce((a,b)=>a+b,0),1023,'Every identity must be counted exactly once');
 assert.equal(JSON.stringify(row.library),before,'Classification must not mutate the library');
 const serving=row.library.filter(p=>p.alive===true&&p.faction!==null).length,free=row.library.filter(p=>p.alive===true&&p.faction===null).length;
 assert.equal(counts.serving,serving);assert.equal(counts.free,free);
 const [year,month]=row.date.split('-').map(Number),summary=context.libraryEntrySummary(row.library,{year,month});
 assert(summary.includes('data-locale-only="zh-Hant"'));assert(summary.includes('data-locale-only="ja"'));assert(summary.includes(`已登場 ${serving+free}／總庫 1023`));
 if(row.date==='217-07')assert.deepEqual(counts,{serving:361,free:50,not_born:117,not_appeared:132,retired:352,death_review:5,pending_history:2,pending_capacity:0,pending_faction:4,scenario_excluded:0,missing:0,unknown:0,unentered:0});
 if(row.date==='191-10')assert.equal(counts.pending_history,206);
 if(row.date==='201-05'){
  assert.equal(counts.pending_capacity,14);
  assert.equal(row.library.filter(p=>context.libraryPlacementFilter(p,'entry:pending_capacity')).length,14);
 }
}
assert(context.libraryEntrySummary([],null).includes('尚未開始戰役'));
console.log('library entry: disjoint actual-roster counts, chronology/pending filters, planned-placement exclusion, locale refresh, and 3 real campaigns passed');
