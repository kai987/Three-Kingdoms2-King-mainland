/* Verify the shipped UI categorizes runtime entry, not an opening placement plan. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'game/app.js'),'utf8');
const options=[],choices=[],listeners=[];
const context={GameI18n:{locale:'zh-Hant'},escapeHtml:String,document:{addEventListener:(...row)=>listeners.push(row),querySelectorAll:selector=>selector.includes('data-library-choice')?choices:options}};
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
choices.push({dataset:{libraryChoice:'own',l10nNative:'zh-Hant'},textContent:''});
const menu=context.libraryEntryOptions('wei');
assert.deepEqual([...menu.matchAll(/value="([^"]+)"/g)].map(row=>row[1]),['own','serving','free','unentered','retired']);
for(const removed of ['ready','rated','default60','available','missing','pending_history','pending_capacity','pending_faction'])assert(!menu.includes(`value="${removed}"`));
assert(context.libraryEntryOptions().includes('disabled'));assert(!menu.includes('disabled'));
const serving={missing:[],alive:true,faction:'wei',year_state:'available'},free={...serving,faction:null},enemy={...serving,faction:'wu'},future={...serving,alive:null,year_state:'not_born'};
assert(context.libraryFilterMatches(serving,'own','wei'));assert(!context.libraryFilterMatches(enemy,'own','wei'));assert(!context.libraryFilterMatches(free,'own','wei'));assert(!context.libraryFilterMatches(future,'own','wei'));assert(!context.libraryFilterMatches(serving,'own',null));
assert(context.libraryFilterMatches(enemy,'serving'));assert(context.libraryFilterMatches(free,'free'));assert(context.libraryFilterMatches(future,'unentered'));assert(!context.libraryFilterMatches(future,'free'));assert(!context.libraryFilterMatches(serving,'retired'));
options.push({dataset:{libraryEntry:'pending_history',l10nNative:'zh-Hant'},textContent:''});
context.GameI18n.locale='ja';context.refreshLibraryEntryLabels();
assert.equal(options[0].textContent,'所属未確定');assert.equal(choices[0].textContent,'自勢力の武将');assert.equal(options[0].dataset.l10nNative,'ja');
context.GameI18n.locale='zh-Hant';context.refreshLibraryEntryLabels();assert.equal(options[0].textContent,'歸屬待考');assert.equal(choices[0].textContent,'我方勢力武將');
context.sourceEvidence=(tc,ja)=>tc+ja;
vm.runInContext(source.slice(source.indexOf('function virtueDescription('),source.indexOf('function showPerson(')),context);
const original=context.virtueDescription({virtue:86,virtue_design:{status:'verified_original',original_id:40,design_rationale:'ROM source verified'}});
assert(original.includes('德86 · 原版武将数值'));assert(original.includes('徳86は原作の武将データ'));assert(!original.includes('德60'));
const python=spawnSync(process.env.PYTHON||'python3',['-B','-c',`
import json,sys
from pathlib import Path
sys.path.insert(0,'source')
from remake.campaign import Campaign,Catalog
rows=[]
for date,side in [('217-07','wu'),('191-10','wei'),('201-05','wei')]:
    game=Campaign(Catalog(Path('game/data/campaigns')/(date+'.json')))
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
 assert.equal(counts.pending_history,0);assert.equal(counts.pending_capacity,0);assert.equal(counts.pending_faction,0);
 if(row.date==='217-07'){assert.equal(counts.serving,365);assert.equal(counts.free,52);}
 if(row.date==='191-10'){assert.equal(counts.serving,300);assert.equal(counts.free,96);}
 if(row.date==='201-05'){
  assert.equal(counts.serving,289);assert.equal(counts.free,127);
  assert.equal(row.library.filter(p=>context.libraryPlacementFilter(p,'entry:pending_capacity')).length,0);
 }
}
assert(context.libraryEntrySummary([],null).includes('尚未開始戰役'));
console.log('library entry: disjoint actual-roster counts, chronology/pending filters, planned-placement exclusion, locale refresh, and 3 real campaigns passed');
