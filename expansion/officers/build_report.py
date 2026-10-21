"""Create the reviewable map/roster handoff without changing game runtime data."""
from pathlib import Path
from html import escape
import json,re,os
from urllib.parse import quote

HERE=Path(__file__).parent
ROOT=HERE.parent.parent
MAP=ROOT/'expansion/map'
OUT=ROOT/'outputs/01a1316a-d5cf-7641-8d98-1e47c65dfb1c'
read=lambda f:json.loads((HERE/f).read_text())
roster=read('data/roster-candidates.json');audit=read('data/dedup-audit.json');original=read('data/original-overlap-audit.json');mapping=read('field-mapping.json');scenarios=read('data/scenario-availability-summary.json')
remake=read('remake-summary.json');virtue_designs=read('virtue-designs.json')['profiles']
mainland=json.loads((ROOT/'game/data/eras-v3/217.json').read_text())['coverage']
links=json.loads((MAP/'city-map-city-sea-links-v42.json').read_text())
source=(MAP/'city-map-city-sea-preview-v42.html').read_text()
maphtml=re.search(r'<div id="map">.*</div></body>',source,re.S).group(0).removesuffix('</body>')
style=(MAP/'report.css').read_text()
legacy={m['candidate_person_id']:m['original_officer_id'] for m in original['matches']}
payload=[]
for p in roster['officers']:
 c=p['chronology']
 payload.append({'id':p['person_id'],'number':p['official_list_number'],'name':p['name_simplified'],'traditional':p['name_traditional'],
  'aliases':p['search_aliases']+[p['name_japanese'],p['reading_japanese']],
  'disambiguator':p['disambiguator'],'birth':c['game_birth_year'],'appearance':c['game_appearance_year'],'death':c['game_death_year'],
  'sourceName':c['source_name'],'flags':p['review_flags'],'legacyId':legacy.get(p['person_id']),
  'scenarios':{k:{'status':s['status'],'raw':s['raw']} for k,s in p['scenario_states'].items()}})
def uri(p):return escape(quote(os.path.relpath(p,HERE).replace(os.sep,"/")),quote=True)
def json_script(o):return json.dumps(o,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
mappingrows=[]
for f in mapping['fields']:
 mappingrows.append('<tr>'+''.join('<td>'+escape(str(x or ''))+'</td>' for x in [f['label_zh'],f['source_field'],f['original_storage'],f['conversion'],mapping['status_legend'].get(f['status'],f['status']),f['notes']])+'</tr>')
homonyms=[]
for group in audit['homonyms']:
 for m in group['members']:
  homonyms.append('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in [group['name'],m['official_list_number'],m['birth'],m['death'],m['disambiguator']])+'</tr>')
ships=[]
for r in links['routes']:
 a=r.get('from',r.get('fromCity',r.get('from_city')));z=r.get('to',r.get('toCity',r.get('to_city')))
 # Exact route schema is retained in the source data; visible labels come from its own name.
 label=r.get('name') or r.get('label') or '城际海路'
 ships.append('<li>'+escape(label)+'</li>')
virtue_rows=[]
for design in virtue_designs:
 source=design['sources'][0]
 virtue_rows.append('<tr><td>'+escape(design['name'])+'</td><td>'+str(design['virtue'])+'</td><td>'+escape(design['design_rationale'])+'</td><td><a href="'+escape(source['url'],quote=True)+'" target="_blank" rel="noreferrer">'+escape(source['section'])+'</a></td></tr>')
template=r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>城际航道与千人武将候选 · v42</title><style>
__STYLE__
html{scroll-behavior:smooth}.map-viewport{max-width:1356px;width:100%}.section-links{display:flex;gap:20px;flex-wrap:wrap;margin:12px 0 20px}.tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:14px 0}.tools label{display:flex;align-items:center;gap:6px}.tools input,.tools select,.pager button{font:inherit;border:1px solid #a18b72;background:#fffdf7;color:#322b22;padding:7px 9px;border-radius:3px}.tools input[type=search]{width:260px}.tools input[type=number]{width:90px}.tools select{max-width:100%}.pager{display:flex;align-items:center;gap:16px;margin:12px 0}.pager button:disabled{opacity:.4}.row-note{display:block;font-size:12px;color:#6e5d4b;line-height:1.5}.muted{color:#685845;font-size:14px}.warning{background:#f7e8cd;border-left:3px solid #98703d;padding:12px 16px}.ships{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.ships figure{margin:0}.ships img{max-width:100%;image-rendering:pixelated;border:1px solid #9c856b}.ships figcaption{font-size:14px}.downloads{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0}#people-table{min-width:900px}#people-table td{vertical-align:top}#people-table td:first-child{font-variant-numeric:tabular-nums}.search-status{min-height:22px}#mapping-table{min-width:1040px}#mapping-table td{max-width:360px;font-size:14px}summary{cursor:pointer;font-weight:650}details{margin:16px 0}.count-line{font-size:18px;line-height:1.7}button{cursor:pointer}nav{flex-wrap:wrap}@media(max-width:800px){.ships{grid-template-columns:1fr}.tools{align-items:flex-start}.tools input[type=search]{width:210px}.tools select{max-width:300px}.count-line{font-size:16px}}
</style><main><h1>城际航道与千人武将候选</h1>
<p>航道改为完整的城池之间连接：陆地用实线道路，海上用虚线，登陆后再接到目的城。武将部分先建立候选库、年代资料与字段映射。</p>
<div class="section-links"><a href="#map-section">城际航道</a><a href="#officers">千人名单</a><a href="#mapping">字段映射</a><a href="#dedup">去重与来源</a><a href="__XLSX__">下载完整表格</a></div>
<h2 id="remake-rules">已确定的重制版人物规则</h2>
<p class="count-line" data-remake-capacity="20">每城 <b>20 人</b>，战场每方 <b>10 人（含主将）</b>，全场最多20人。总库1000人，按出生、出仕/登场、死亡年份分别管理。</p>
<p>武力对应原作“武”，智力对应“知”；兼容数值1—99，来源100保留原值并映射99。德独立参考史料设定；其余初始值按本作人物与剧本配置。来源“登场年”是SAN14游戏设定，不能当成已证实的首次任官年份。</p>
<p>新登场人物0兵、基础短剣和絹巾、经验0；体力按明确人物基准满值初始化。在野忠诚0、君主100，仕官者用剧本配置，招募与俘虏分别使用原规则。体力、适性或能力缺失时列为待配置。</p>
<p class="warning">阶段1的原版基线仍为8人；扩展战役现已整理1000人的SAN14第三方数值资料，__MAINLAND_READY__人属性齐全，__MAINLAND_PENDING__人仍待配置，217年7月开局__MAINLAND_SERVING__人仕官；体力和适性已覆盖1000人，剩余缺项为德。<a href="http://127.0.0.1:8878/">打开本地96城战役</a>；须先按仓库说明启动游戏服务。该试制版尚非完整千人正式战役。</p>
<details><summary>首批5人的德设计与史料依据</summary><p>按恤民35%、公正30%、操守20%、信义15%加权。维度与分值是游戏设计解释，使用生涯综合档，不是史料给出的客观数值，也不直接等同魅力。其余人物不自动补分。</p><div class="table-wrap"><table id="virtue-design-table"><thead><tr><th>人物</th><th>德</th><th>设计说明</th><th>史料</th></tr></thead><tbody>__VIRTUE_ROWS__</tbody></table></div></details>
<div class="downloads"><a href="../../game/data/eras-v3/217.json">当前战役人物配置</a><a href="data/san14-abilities.json">千人武力与智力来源表</a><a href="__REMAKE_RULES__">重制版规则</a><a href="__REMAKE_PROFILES__">1000人初始化资料</a><a href="__REMAKE_CSV__">初始化资料CSV</a><a href="__REMAKE_YEARS__">年度人数</a><a href="__REMAKE_PLAN__">分阶段实现计划</a></div>
<h2 id="map-section">城池—陆路—航道—陆路—城池</h2>
<nav><label><input id="river-toggle" type="checkbox" checked> 河流</label><label><input id="land-toggle" type="checkbox" checked> 陆路与岸边接驳</label><label><input id="sea-toggle" type="checkbox" checked> 海上航道</label><a href="__MAP_PNG__">完整样图</a></nav>
<div class="map-viewport">__MAP_HTML__</div>
<p>7 条城际关系连接 11 座沿海城池；共用海段只画一遍。主图继续使用原版 32 × 32 城标，不显示城名。航线已从原先的近海端点接回城池，陆海交界保留短登陆段。</p>
<div class="ships"><figure><a href="__SEA_NORTH__"><img src="__SEA_NORTH__" alt="北方城际海路与接驳陆路"></a><figcaption>吴郡、辽东与北海、乐浪、带方</figcaption></figure><figure><a href="__SEA_ISLAND__"><img src="__SEA_ISLAND__" alt="会稽到夷洲的城际海路与陆路"></a><figcaption>会稽—夷洲</figcaption></figure><figure><a href="__SEA_SOUTH__"><img src="__SEA_SOUTH__" alt="珠官朱崖交趾日南的海陆完整连接"></a><figcaption>珠官、朱崖、交趾与日南</figcaption></figure></div>
<p class="muted">港位、接驳道路与具体航迹为游戏示意。沿用原先史料方向；交趾—日南保留为图内南向延伸示意。<a href="__SEA_DATA__">城际关系与依据</a>。</p>

<h2 id="officers">千人候选名单与年代</h2>
<p class="count-line">库内保留 <b>1000 位独立候选人物</b>，共有 <b>994 种姓名文本</b>。5 组同名涉及 11 人，均保留独立身份。</p>
<p>已整理全部 1000 人的生年、登场年、卒年，以及 10 个剧本的状态。姓名以<a href="https://www.gamecity.com.tw/sangokushi14/officers-list.html" target="_blank" rel="noreferrer">光荣特库摩官方名单</a>为基准；年代与剧本状态来自<a href="https://xgodgame.blogspot.com/2020/02/14_9.html" target="_blank" rel="noreferrer">玩家整理的 SAN14 游戏设定表</a>，历史生卒仍待逐人核定。</p>
<div class="downloads"><a href="__XLSX__">完整 Excel 表格</a><a href="__ROSTER_CSV__">名单 CSV</a><a href="__CHRONO_CSV__">年代表 CSV</a><a href="__SCENARIO_CSV__">10 剧本状态 CSV</a><a href="__MAPPING_CSV__">字段映射 CSV</a></div>
<div class="tools"><label>检索 <input id="officer-search" type="search" placeholder="姓名、异写、人物ID" autocomplete="off"></label><label>查看 <select id="scenario-select"><option value="year">按参考年份</option></select></label><label>年份 <input id="year-select" type="number" min="1" max="400" step="1" value="230"></label><label>状态 <select id="status-select"></select></label></div>
<p id="year-note" class="muted"></p><p id="result-count" class="search-status" aria-live="polite"></p>
<div class="table-wrap"><table id="people-table"><thead><tr><th>来源序号</th><th>姓名</th><th>同名辨识／来源差异</th><th>生年</th><th>登场</th><th>卒年</th><th>当前状态</th><th>原版ID<br><small>已确认</small></th></tr></thead><tbody></tbody></table></div>
<div class="pager"><button id="prev-page" type="button">上一页</button><span id="page-label"></span><button id="next-page" type="button">下一页</button></div>
<p class="muted">“参考年份”按来源生卒与登场年筛选，卒年当年单列待核；不等同已制作的游戏剧本。选择具体来源剧本时，保留原表状态。251 年英雄集结是跨年代假想剧本。来源序号为官方网页顺序，不是原游戏运行ID。</p>

<h2 id="mapping">字段映射</h2>
<p>共 29 项。武力对应武，智力对应知；徳采用独立史料参考的游戏设计规则。体力、忠诚、兵力、装备、经验按本作初始化；逐人能力和必要人物配置缺失时保持待补齐。</p>
<div class="table-wrap"><table id="mapping-table"><thead><tr><th>字段</th><th>来源</th><th>原作含义／存储</th><th>转换规则</th><th>状态</th><th>备注</th></tr></thead><tbody>__MAPPING_ROWS__</tbody></table></div>
<p>千人库采用独立人物ID。后续若按 1200 人容量开发，需要 16 位运行ID，并迁移原版的亲族、特殊武将、招募与继承引用。当前交付的是名单、规则和地图数据，尚未把数值写入游戏。</p>

<h2 id="dedup">去重结果与待核项</h2>
<p>不能把姓名相同当作同一个人。下面五组均保留原官方独立条目；两个年代来源表重复列出的同一批人物只计一遍。</p>
<div class="table-wrap"><table><thead><tr><th>同名</th><th>来源序号</th><th>游戏生年</th><th>游戏卒年</th><th>辨识</th></tr></thead><tbody>__HOMONYM_ROWS__</tbody></table></div>
<p>4 处跨来源姓名差异单独保留核对标记，不作为已证实的史实别名：閔純／關純、羊衜／羊（来源截断）、楊白／楊柏、綸直／倫直。</p>
<p class="warning">本轮确认的是候选库内的 <b>1000 人</b>。原版 237 人中，当前已有姓名转写可核对的 8 人已匹配，另外 229 人尚未建立完整人物对照，因此暂不报合并原版后的总人数或净新增人数。</p>
<details><summary>资料与下载说明</summary><p>Excel 包含候选名单、可修改参考年份的年代筛选、10 剧本原始状态、29 项字段映射和去重核对。CSV／JSON保留稳定人物ID、来源原文与核对标记，供下一步开发使用。</p><p><a href="__ROSTER_JSON__">完整候选 JSON</a> · <a href="__DEDUP_JSON__">去重记录</a> · <a href="__ORIGINAL_JSON__">原版对照记录</a> · <a href="__SOURCES_JSON__">来源快照与哈希</a> · <a href="__MAPPING_JSON__">字段映射 JSON</a></p></details>
<footer>2026-10-21 · v42 城际航道与武将候选整理<br><a href="__MAP_VALIDATION__">地图检查</a> · <a href="__WORKBOOK_VALIDATION__">表格检查</a></footer></main>
<script>
const PEOPLE=__PEOPLE_JSON__,SCENARIOS=__SCENARIOS_JSON__,STATE_LABELS={serving:'仕官',free:'在野',undiscovered:'未发现',not_appeared:'未登场',dead:'已卒'};
const box=document.querySelector('.map-viewport'),map=document.querySelector('#map');function resize(){const s=Math.min(1,box.clientWidth/1352);map.style.transform='scale('+s+')';box.style.height=(1024*s+4)+'px'}new ResizeObserver(resize).observe(box);resize();for(const[id,layer]of[['river-toggle','historic-rivers'],['land-toggle','shared-roads'],['sea-toggle','historical-sea-routes']])document.querySelector('#'+id).addEventListener('change',e=>document.querySelector('[data-layer="'+layer+'"]').style.display=e.target.checked?'':'none');
const search=document.querySelector('#officer-search'),scenario=document.querySelector('#scenario-select'),year=document.querySelector('#year-select'),status=document.querySelector('#status-select'),tbody=document.querySelector('#people-table tbody');let page=0;const PAGE_SIZE=30;
for(const s of SCENARIOS){const o=document.createElement('option');o.value=s.scenario_id;o.textContent=s.year+' '+s.source_label+(s.historical_timeline?'':'（假想）');scenario.append(o);}
function annualState(p,y){if(!Number.isInteger(y)||y<1||y>400)return'参考年待填';if(p.birth==null||p.appearance==null||p.death==null)return'年代待核';if(y<p.birth)return'未出生';if(y<p.appearance)return'未登场';if(y>p.death)return'已过卒年';if(y===p.death)return'卒年边界待核';return'年表可登场';}
function currentState(p){return scenario.value==='year'?annualState(p,Number(year.value)):STATE_LABELS[p.scenarios[scenario.value].status]||'来源状态待核';}
function setupMode(){const isYear=scenario.value==='year';year.disabled=!isYear;const s=SCENARIOS.find(s=>s.scenario_id===scenario.value);if(s)year.value=s.year;const options=isYear?['全部','年表可登场','卒年边界待核','未出生','未登场','已过卒年','年代待核']:['全部','仕官','在野','未发现','未登场','已卒'];status.replaceChildren(...options.map(x=>{const o=document.createElement('option');o.value=o.textContent=x;return o;}));document.querySelector('#year-note').textContent=isYear?'年度参考：卒年当年单列待核；这是来源游戏年表，不是史实生卒认证。':s.historical_timeline?'按来源剧本的实际记录显示，不以年龄公式覆盖。':'英雄集结为跨年代假想剧本，按原表保留1000人，不按生卒年剔除。';page=0;render();}
function render(){if(scenario.value==='year'){const y=Number(year.value);document.querySelector('#year-note').textContent=Number.isInteger(y)&&y>=1&&y<=400?'年度参考：卒年当年单列待核；这是来源游戏年表，不是史实生卒认证。':'请填写1—400之间的整数参考年份。';}const q=search.value.trim().toLocaleLowerCase(),filtered=PEOPLE.filter(p=>(!q||[p.name,p.traditional,p.id,p.number,p.disambiguator,p.sourceName,...p.aliases].join(' ').toLocaleLowerCase().includes(q))&&(status.value==='全部'||currentState(p)===status.value));const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));page=Math.min(page,pages-1);const rows=filtered.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);tbody.replaceChildren();
for(const p of rows){const tr=document.createElement('tr');tr.dataset.personId=p.id;const values=[p.number,p.name,p.disambiguator||'',p.birth,p.appearance,p.death,currentState(p),p.legacyId==null?'待核':p.legacyId];values.forEach((v,i)=>{const td=document.createElement('td');td.textContent=v==null?'待核':String(v);if(i===1){if(p.traditional!==p.name){const small=document.createElement('small');small.className='row-note';small.textContent=p.traditional;td.append(small);}const small=document.createElement('small');small.className='row-note';small.textContent=p.id;td.append(small);}if(i===2&&p.flags.some(f=>f!=='same_name_different_source_people_retained')){const small=document.createElement('small');small.className='row-note';small.textContent='来源写作「'+p.sourceName+'」，差异待核';td.append(small);}tr.append(td);});tbody.append(tr);}
document.querySelector('#result-count').textContent='符合条件 '+filtered.length+' 人 / 候选库 '+PEOPLE.length+' 人';document.querySelector('#result-count').dataset.filteredCount=filtered.length;document.querySelector('#page-label').textContent=(page+1)+' / '+pages;document.querySelector('#prev-page').disabled=page===0;document.querySelector('#next-page').disabled=page>=pages-1;}
search.addEventListener('input',()=>{page=0;render();});year.addEventListener('input',()=>{page=0;render();});status.addEventListener('change',()=>{page=0;render();});scenario.addEventListener('change',setupMode);document.querySelector('#prev-page').addEventListener('click',()=>{page--;render();});document.querySelector('#next-page').addEventListener('click',()=>{page++;render();});setupMode();
</script></html>'''
replacements={
 '__MAINLAND_READY__':str(mainland['configured_profiles']),'__MAINLAND_PENDING__':str(mainland['pending_profiles']),'__MAINLAND_SERVING__':str(mainland['initial_serving']),
 '__STYLE__':style,'__MAP_HTML__':maphtml,'__PEOPLE_JSON__':json_script(payload),'__SCENARIOS_JSON__':json_script(roster['scenarios']),
 '__MAPPING_ROWS__':''.join(mappingrows),'__HOMONYM_ROWS__':''.join(homonyms),
 '__VIRTUE_ROWS__':''.join(virtue_rows),'__REMAKE_RULES__':uri(HERE/'remake-rules.json'),
 '__REMAKE_PROFILES__':uri(HERE/'data/remake-profiles.json'),'__REMAKE_CSV__':uri(HERE/'data/remake-profiles.csv'),
 '__REMAKE_YEARS__':uri(HERE/'data/remake-year-populations.json'),'__REMAKE_PLAN__':uri(ROOT/'docs/remake-implementation-plan.md'),
 '__XLSX__':uri(OUT/'千人武将候选名单与字段映射.xlsx'),'__MAP_PNG__':uri(MAP/'city-map-96-city-sea-v42.png'),
 '__SEA_NORTH__':uri(MAP/'city-map-city-sea-north-v42.png'),'__SEA_ISLAND__':uri(MAP/'city-map-city-sea-island-v42.png'),'__SEA_SOUTH__':uri(MAP/'city-map-city-sea-south-v42.png'),
 '__SEA_DATA__':uri(MAP/'city-map-city-sea-links-v42.json'),'__ROSTER_CSV__':uri(HERE/'data/roster-candidates.csv'),
 '__CHRONO_CSV__':uri(HERE/'data/chronology-candidates.csv'),'__SCENARIO_CSV__':uri(HERE/'data/scenario-states.csv'),
 '__MAPPING_CSV__':uri(HERE/'field-mapping.csv'),'__ROSTER_JSON__':uri(HERE/'data/roster-candidates.json'),
 '__DEDUP_JSON__':uri(HERE/'data/dedup-audit.json'),'__ORIGINAL_JSON__':uri(HERE/'data/original-overlap-audit.json'),
 '__SOURCES_JSON__':uri(HERE/'source/san14-source-manifest.json'),'__MAPPING_JSON__':uri(HERE/'field-mapping.json'),
 '__MAP_VALIDATION__':uri(MAP/'city-map-city-sea-validation-v42.json'),'__WORKBOOK_VALIDATION__':uri(OUT/'workbook-validation.json')}
for k,value in replacements.items():template=template.replace(k,value)
assert not re.search(r'__[A-Z_]+__',template)
(HERE/'index.html').write_text(template)
summary={'candidate_people':len(payload),'distinct_name_strings':audit['unique_traditional_name_strings'],'same_name_people':audit['same_name_people'],
 'chronology_records':len(payload),'scenario_cells':10000,'field_mapping_rows':len(mapping['fields']),
 'original_count':237,'original_identified_matches':8,'original_pending':229,'confirmed_net_new_people':None,
 'map_relations':links['checks']['cityToCityRelations'],'game_runtime_modified':False,
 'remake_rules':remake,'mainland_campaign':mainland,
 'workbook':str((OUT/'千人武将候选名单与字段映射.xlsx').relative_to(ROOT)),'report':str((HERE/'index.html').relative_to(ROOT))}
(HERE/'delivery-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
