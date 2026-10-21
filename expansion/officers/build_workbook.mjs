import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';

const base=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(base,'../..');
const out=path.join(root,'outputs','01a1316a-d5cf-7641-8d98-1e47c65dfb1c');
await fs.mkdir(out,{recursive:true});
const read=async f=>JSON.parse(await fs.readFile(path.join(base,f),'utf8'));
if(process.argv.includes('--preview-mapping')||process.argv.includes('--update-mapping-only')){
 const target=path.join(out,'千人武将候选名单与字段映射.xlsx');
 const existing=await SpreadsheetFile.importXlsx(await FileBlob.load(target));
 const mapping=await read('field-mapping.json'),fields=existing.worksheets.getItem('字段映射');
 const checks=path.join(root,'build/remake-workbook-checks');await fs.mkdir(checks,{recursive:true});
 if(process.argv.includes('--preview-mapping')){
  const detail=process.argv.includes('--detail');
  const preview=await existing.render({sheetName:'字段映射',range:detail?'A14:H19':'A1:F13',scale:1,format:'png'});
  const file=path.join(checks,detail?'mapping-detail.png':'mapping-before.png');
  await fs.writeFile(file,new Uint8Array(await preview.arrayBuffer()));
  console.log(JSON.stringify({preview:file}));process.exit(0);
 }
 const preservedNames=['候选名单','剧本年代','去重与来源'];
 const signature=()=>JSON.stringify(preservedNames.map(n=>{const r=existing.worksheets.getItem(n).getUsedRange();return{name:n,values:r.values,formulas:r.formulas};}));
 const before=signature();
 fields.getRange('A4').values=[['每城20人；战场每方10人含主将。总人物库与当年出生、出仕、死亡状态分开。']];
 fields.getRange('A5').values=[['武力对应武，智力对应知；德依史料独立设定；其他初始值按本作人物与剧本配置。']];
 const width=[20,28,32,34,65,26,60,62],weight=s=>[...String(s)].reduce((n,c)=>n+(c.charCodeAt(0)>255?2:1),0);
 mapping.fields.forEach((f,i)=>{
  const values=[f.label_zh,f.source_field,f.target_field,f.original_storage,f.conversion,mapping.status_legend[f.status]||f.status,f.notes||'',f.evidence.join('\n')];
  fields.getRange('A'+(i+9)+':H'+(i+9)).values=[values];
  const lines=Math.max(...values.map((v,j)=>String(v).split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(weight(line)/(width[j]-2))),0)));
  fields.getRange('A'+(i+9)+':H'+(i+9)).format.rowHeight=Math.max(34,lines*15+9);
 });
 await existing.recalculate();
 if(signature()!==before)throw new Error('Unrelated sheet values/formulas changed');
 const errors=await existing.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:1400});
 const snapshot=await existing.inspect({kind:'table',range:'字段映射!A4:F19',include:'values',tableMaxRows:16,tableMaxCols:6,maxChars:3000});
 await fs.writeFile(path.join(checks,'mapping-inspection.ndjson'),snapshot.ndjson);
 const preview=await existing.render({sheetName:'字段映射',range:'A1:F13',scale:1,format:'png'});
 await fs.writeFile(path.join(checks,'mapping-after.png'),new Uint8Array(await preview.arrayBuffer()));
 const output=await SpreadsheetFile.exportXlsx(existing);await output.save(target);
 await fs.writeFile(path.join(out,'workbook-remake-validation.json'),JSON.stringify({mappingRows:mapping.fields.length,cityCapacity:20,battlePerSide:10,unrelatedSheetValuesAndFormulasPreserved:true,formulaErrorScan:errors.ndjson,sourceStatsImported:false},null,2)+'\n');
 console.log(JSON.stringify({mappingRows:mapping.fields.length,unrelatedSheetsPreserved:true,formulaErrorScan:errors.ndjson}));process.exit(0);
}
const data=await read('data/roster-candidates.json'),audit=await read('data/dedup-audit.json'),legacy=await read('data/original-overlap-audit.json'),mapping=await read('field-mapping.json'),scenarioSummary=await read('data/scenario-availability-summary.json');
const people=data.officers,legacyByPerson=new Map(legacy.matches.map(r=>[r.candidate_person_id,r.original_officer_id]));
const wb=Workbook.create();
const roster=wb.worksheets.add('候选名单'),scenarios=wb.worksheets.add('剧本年代'),fields=wb.worksheets.add('字段映射'),review=wb.worksheets.add('去重与来源');
const brown='#5A4637',text='#242424',cream='#F7F1E6',amber='#FFF0CF';
function setup(sheet,last){sheet.showGridLines=false;sheet.getRange('A1:'+last).format.font={name:'Arial',size:11,color:text};sheet.getRange('A1:'+last).format.verticalAlignment='center';sheet.getRange('A1:'+last).format.rowHeight=23;}
function title(sheet,txt){sheet.getRange('A2').values=[[txt]];sheet.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:brown};sheet.getRange('A2:K2').format.borders={bottom:{style:'thin',color:'#AC927B'}};sheet.getRange('A2:K2').format.rowHeight=30;}
function heading(sheet,range){sheet.getRange(range).format={fill:brown,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:32};}
function widths(sheet,list){for(const[col,width]of Object.entries(list))sheet.getRange(col+':'+col).format.columnWidth=width;}
function table(sheet,range,name){const t=sheet.tables.add(range,true,name);t.style='TableStyleLight1';t.showFilterButton=true;return t;}
const flagLabel={same_name_different_source_people_retained:'同名异人，保留',name_variant_requires_historical_review:'来源异写待核',third_party_name_truncated:'来源姓名截断'};
const notesFor=p=>p.review_flags.map(f=>flagLabel[f]||f).join('；');
const stateLabels={serving:'仕官',free:'在野',undiscovered:'未发现',not_appeared:'未登场',dead:'已卒'};

setup(roster,'O1008');title(roster,'千人武将候选名单与年代');roster.tabColor=brown;
roster.getRange('A4:B5').values=[['候选人物',null],['不同姓名',audit.unique_traditional_name_strings]];
roster.getRange('B4').formulas=[['=COUNTA(M9:M1008)']];
roster.getRange('D4:E5').values=[['参考年份',230],['卒年边界待核',null]];
roster.getRange('F4:G5').values=[['年表可登场',null],['同名人数',audit.same_name_people]];
roster.getRange('G4').formulas=[['=IF(OR($E$4="",NOT(ISNUMBER($E$4)),$E$4<1,$E$4>400),"参考年待填",COUNTIFS(H9:H1008,"年表可登场"))']];
roster.getRange('E5').formulas=[['=IF(OR($E$4="",NOT(ISNUMBER($E$4)),$E$4<1,$E$4>400),"参考年待填",COUNTIFS(H9:H1008,"卒年边界待核"))']];
roster.getRange('E4').format.fill=amber;roster.getRange('E4').dataValidation={rule:{type:'whole',operator:'between',formula1:1,formula2:400}};
roster.getRange('A6').values=[['生年、登场、卒年为第三方整理的SAN14游戏设定。参考年可修改，卒年当年单列待核。']];roster.getRange('A6').format.font={name:'Arial',size:11,italic:true,color:'#655548'};
const headers=['官方序号','简体姓名','繁体姓名','同名辨识','生年','登场年','卒年','参考年状态','原版ID','年代依据','核对标记','来源原名','人物ID','日文名','日文读音'];
roster.getRange('A8:O8').values=[headers];
const rows=people.map(p=>[p.official_list_number,p.name_simplified,p.name_traditional,p.disambiguator||'',p.chronology.game_birth_year,p.chronology.game_appearance_year,p.chronology.game_death_year,null,legacyByPerson.has(p.person_id)?legacyByPerson.get(p.person_id):null,'SAN14游戏设定',notesFor(p),p.chronology.source_name,p.person_id,p.name_japanese,p.reading_japanese]);
roster.getRange('A9:O1008').values=rows;
roster.getRange('H9').formulas=[['=IF(OR($E$4="",NOT(ISNUMBER($E$4)),$E$4<1,$E$4>400),"参考年待填",IF(OR(E9="",F9="",G9=""),"年代待核",IF($E$4<E9,"未出生",IF($E$4<F9,"未登场",IF($E$4>G9,"已过卒年",IF($E$4=G9,"卒年边界待核","年表可登场"))))))']];roster.getRange('H9:H1008').fillDown();
table(roster,'A8:O1008','OfficerCandidates');heading(roster,'A8:O8');
widths(roster,{A:10,B:13,C:13,D:36,E:9,F:9,G:9,H:19,I:10,J:21,K:28,L:14,M:30,N:14,O:24});
roster.getRange('A9:A1008').setNumberFormat('0');roster.getRange('E9:G1008').setNumberFormat('0');roster.getRange('I9:I1008').setNumberFormat('0');
roster.getRange('E9:G1008').format.horizontalAlignment='right';roster.getRange('A9:A1008').format.horizontalAlignment='right';
roster.getRange('H9:H1008').conditionalFormats.add('containsText',{text:'待核',format:{fill:amber,font:{color:'#7A3D11'}}});
roster.getRange('H9:H1008').conditionalFormats.add('containsText',{text:'待填',format:{fill:amber,font:{color:'#7A3D11'}}});
roster.getRange('K9:K1008').conditionalFormats.add('containsText',{text:'来源',format:{fill:amber}});
roster.freezePanes.freezeRows(8);roster.freezePanes.freezeColumns(3);

setup(scenarios,'L1008');title(scenarios,'原始剧本登场状态');
scenarios.getRange('A4').values=[['251年英雄集结为跨年代假想剧本。其他剧本按来源状态保留，不用生年加15推算。']];
scenarios.getRange('A5').values=[['原文：统治者姓名表示仕官；城市(未)表示未发现；城市(-)表示未登场；x表示已卒。']];
const scHeaders=['官方序号','姓名',...data.scenarios.map(s=>s.year+' '+s.source_label+(s.historical_timeline?'':'（假想）'))];
scenarios.getRange('A8:L8').values=[scHeaders];
scenarios.getRange('A9:L1008').values=people.map(p=>[p.official_list_number,p.name_simplified,...data.scenarios.map(s=>p.scenario_states[s.scenario_id].raw)]);
table(scenarios,'A8:L1008','ScenarioStates');heading(scenarios,'A8:L8');
widths(scenarios,{A:10,B:13,C:17,D:17,E:17,F:17,G:17,H:17,I:17,J:17,K:17,L:22});
scenarios.getRange('A9:A1008').setNumberFormat('0');scenarios.freezePanes.freezeRows(8);scenarios.freezePanes.freezeColumns(2);

setup(fields,'H40');title(fields,'字段映射与导入边界');
fields.getRange('A4').values=[['每城20人；战场每方10人含主将。总人物库与当年出生、出仕、死亡状态分开。']];
fields.getRange('A5').values=[['武力对应武，智力对应知；德依史料独立设定；其他初始值按本作人物与剧本配置。']];
fields.getRange('A8:H8').values=[['字段','来源字段','目标字段','原版存储','转换规则','方案状态','备注','证据']];
fields.getRange('A9:H'+(8+mapping.fields.length)).values=mapping.fields.map(f=>[f.label_zh,f.source_field,f.target_field,f.original_storage,f.conversion,mapping.status_legend[f.status]||f.status,f.notes||'',f.evidence.join('\n')]);
table(fields,'A8:H'+(8+mapping.fields.length),'FieldMapping');heading(fields,'A8:H8');
widths(fields,{A:20,B:28,C:32,D:34,E:65,F:26,G:60,H:62});fields.getRange('A9:H'+(8+mapping.fields.length)).format.wrapText=true;fields.getRange('A9:H'+(8+mapping.fields.length)).format.verticalAlignment='top';
const mapWidths=[20,28,32,34,65,26,60,62],weightedLength=s=>[...String(s)].reduce((n,c)=>n+(c.charCodeAt(0)>255?2:1),0);
mapping.fields.forEach((f,i)=>{const values=[f.label_zh,f.source_field,f.target_field,f.original_storage,f.conversion,mapping.status_legend[f.status]||f.status,f.notes||'',f.evidence.join('\n')],lines=Math.max(...values.map((v,j)=>String(v).split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(weightedLength(line)/(mapWidths[j]-2))),0)));fields.getRange('A'+(i+9)+':H'+(i+9)).format.rowHeight=Math.max(34,lines*15+9);});
fields.freezePanes.freezeRows(8);fields.freezePanes.freezeColumns(1);

setup(review,'H76');title(review,'去重、同名与资料来源');
review.getRange('A4:B11').values=[['官方独立记录',audit.official_rows],['保留候选人物',audit.candidate_people_after_entity_aware_dedup],['不同姓名文本',audit.unique_traditional_name_strings],['同名组数',audit.same_name_groups],['同名人物',audit.same_name_people],['确认重复人物剔除',audit.confirmed_duplicate_person_entries_removed],['年代覆盖',1000],['历史生卒逐人认证',0]];
review.getRange('D4').values=[['按独立人物ID保留，同名不删人。']];
review.getRange('D6').values=[['第二张年代表重复列同一1000人，不计新增。']];
review.getRange('D8').values=[['历史生卒待逐人核对；表中是游戏设定。']];
review.getRange('A14:F14').values=[['同名','官方序号','人物ID','生年','卒年','辨识']];
const homonyms=audit.homonyms.flatMap(g=>g.members.map(m=>[g.name,m.official_list_number,m.person_id,m.birth,m.death,m.disambiguator]));review.getRange('A15:F'+(14+homonyms.length)).values=homonyms;heading(review,'A14:F14');
review.getRange('A29:E29').values=[['官方序号','官方姓名','年代来源姓名','处理','史实别名已认证']];
review.getRange('A30:E33').values=audit.explicit_name_discrepancy_crosswalks.map(x=>[x.official_list_number,x.official_name,x.chronology_name,x.reason==='third_party_name_truncated'?'保留截断来源原文':'按同序对齐，异写待核','否']);heading(review,'A29:E29');
review.getRange('A36:B40').values=[['原版记录数',legacy.original_officer_count],['有姓名转写可核对',legacy.original_name_transcriptions_available],['已确认匹配',legacy.matched_original_name_transcriptions],['原版身份待核',legacy.original_unresolved_count],['确认净新增人数','待原版全量身份核对']];
review.getRange('D36').values=[['原237人尚有229人身份待核，暂不计算净新增。']];
review.getRange('A43:D43').values=[['原版ID','已转写姓名','官方序号','候选人物ID']];
review.getRange('A44:D51').values=legacy.matches.map(x=>[x.original_officer_id,x.original_transcribed_name,x.official_list_number,x.candidate_person_id]);heading(review,'A43:D43');
review.getRange('A54:C54').values=[['来源','范围','链接']];
review.getRange('A55:C58').values=[['光荣特库摩官方繁中名单','1000条姓名与公开顺序','https://www.gamecity.com.tw/sangokushi14/officers-list.html'],['光荣特库摩官方日文名单','日文名与读音','https://www.gamecity.ne.jp/sangokushi14/officers-list.html'],['X GOD GAME玩家整理表','游戏年代与10剧本状态','https://xgodgame.blogspot.com/2020/02/14_9.html'],['本工程原版解析','原作字段与已转写姓名','source/recovered/officers.py；scripts/make_portal.py']];heading(review,'A54:C54');
widths(review,{A:23,B:27,C:43,D:47,E:22,F:54,G:3,H:14});review.getRange('D4:F8').format.wrapText=true;review.getRange('D4:F8').format.rowHeight=30;review.getRange('D36:F38').format.wrapText=true;review.getRange('D36:F38').format.rowHeight=36;review.getRange('C55:F58').format.wrapText=true;review.getRange('A55:F58').format.rowHeight=38;
review.getRange('A15:F25').format.rowHeight=28;review.getRange('F15:F25').format.wrapText=true;review.getRange('A30:E33').format.rowHeight=32;review.getRange('D30:D33').format.wrapText=true;

const expectedForYear=year=>people.reduce((a,p)=>{const c=p.chronology;let s=typeof year!=='number'||year<1||year>400?'参考年待填':c.game_birth_year==null||c.game_appearance_year==null||c.game_death_year==null?'年代待核':year<c.game_birth_year?'未出生':year<c.game_appearance_year?'未登场':year>c.game_death_year?'已过卒年':year===c.game_death_year?'卒年边界待核':'年表可登场';a[s]=(a[s]||0)+1;return a;},{});
await wb.recalculate();
const tests=[];for(const year of[184,null,0,230]){roster.getRange('E4').values=[[year]];await wb.recalculate();const status=roster.getRange('H9:H1008').values.map(r=>r[0]),actual=status.reduce((a,s)=>(a[s]=(a[s]||0)+1,a),{}),expected=expectedForYear(year);if(JSON.stringify(Object.entries(actual).sort())!==JSON.stringify(Object.entries(expected).sort()))throw new Error('Year filter mismatch '+year+' '+JSON.stringify(actual));tests.push({year,counts:actual});}
roster.getRange('E4').values=[[230]];await wb.recalculate();
const inspected=await wb.inspect({kind:'table',range:'候选名单!A4:I12',include:'values,formulas',tableMaxRows:9,tableMaxCols:9,maxChars:2500});
await fs.writeFile(path.join(out,'workbook-inspection.ndjson'),inspected.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'final formula error scan',maxChars:1600});
await fs.writeFile(path.join(out,'workbook-error-scan.ndjson'),errors.ndjson);
for(const[sheetName,range,file]of[['候选名单','A1:I18','candidate-preview.png'],['剧本年代','A1:F18','scenarios-preview.png'],['字段映射','A1:F13','mapping-preview.png'],['去重与来源','A1:F25','dedup-preview.png'],['去重与来源','A29:F58','sources-preview.png']]){if(process.argv.includes('--refresh-changed-only')&&file==='scenarios-preview.png')continue;const preview=await wb.render({sheetName,range,scale:1.5,format:'png'});await fs.writeFile(path.join(out,file),new Uint8Array(await preview.arrayBuffer()));}
const output=await SpreadsheetFile.exportXlsx(wb),target=path.join(out,'千人武将候选名单与字段映射.xlsx');await output.save(target);
await fs.writeFile(path.join(out,'workbook-validation.json'),JSON.stringify({output:target,officers:people.length,uniqueNames:audit.unique_traditional_name_strings,homonymPeople:homonyms.length,mappingRows:mapping.fields.length,scenarioCells:people.length*data.scenarios.length,yearFilterTests:tests,remainingLegacyIdentities:legacy.original_unresolved_count,originalGameModified:false,formulaErrorScan:errors.ndjson},null,2)+'\n');
console.log(JSON.stringify({output:target,officers:people.length,uniqueNames:audit.unique_traditional_name_strings,mappingRows:mapping.fields.length,yearFilterTests:tests,formulaErrorScan:errors.ndjson}));
