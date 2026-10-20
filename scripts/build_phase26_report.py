#!/usr/bin/env python3
"""Build the phase26 evidence portal from formal frozen inputs only.

This program reads receipts, original media, Source text and static contracts.
It does not execute the ROM, recovered Source, CPU validators or earlier producers.
"""
from pathlib import Path
from html.parser import HTMLParser
import argparse, hashlib, html, json, re, shutil, subprocess, wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase26'
def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def checkpins(data):
    for key in ('source_sha256', 'source_and_validator_sha256', 'artifact_sha256', 'artifact_and_dependency_sha256', 'input_sha256'):
        pins = data.get(key)
        if isinstance(pins, dict):
            for path, value in pins.items():
                if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
                    p = ROOT / path
                    assert p.is_file() and sha(p) == value, (key, path)

def inputs():
    native = read(OUT/'runtime/evidence.json')
    nv = read(OUT/'runtime/validation.json')
    source = read(OUT/'deployment/validation.json')
    integration = read(OUT/'source-integration.json')
    static = read(OUT/'fields-static/analysis-summary.json')
    contracts = read(OUT/'fields-static/verification.json')
    context = read(OUT/'context/verification.json')
    ownership = read(OUT/'context/owner-and-caller-chain.json')
    completion = read(OUT/'context/completion-contracts.json')
    denominators = read(OUT/'context/stable-denominators.json')
    erratum = read(OUT/'context/historical-wording-erratum.json')
    acceptance = read(OUT/'acceptance/requirements.json')
    av = read(OUT/'acceptance/verification.json')
    for doc in (native, nv, source, integration, contracts, context, av):
        assert doc['status'] == 'passed'
        checkpins(doc)
    assert source.get('quick') is False, 'Final complete Source matrix is required'
    assert len(acceptance['dimensions']) == 10
    for dim in acceptance['dimensions']:
        assert dim.get('phase26_change') and 'PENDING' not in json.dumps(dim['phase26_change']), dim['id']
    assert static['all_indirect_access_count'] == 1526
    assert static['remaining_access_count'] == 335
    assert static['all_indirect_classification_counts'] == {'proved_disjoint_auxiliary_address_domain':1191,'possible_city_auxiliary_alias':81,'unresolved_pointer_or_index_contract':254}
    assert static['newly_proved_disjoint_all_count'] == 4
    selected = read(OUT/'fields-static/selected-accesses.json')['accesses']
    target = {0xB272,0xB278,0xB290,0xB296}
    assert {r['cpu'] for r in selected} == target
    accesses = []
    aux = {0x6000+32*i+offset for i in range(30) for offset in (1,28,29,30,31)}
    for row in selected:
        contract = row['address_contract']; words = contract['whole_pointer_values']; ys = contract['Y_values']
        logical = {(p+y)&65535 for p in words for y in ys}
        assert not logical & aux
        assert contract['auxiliary_address_intersection_count'] == 0
        assert row['whole_pointer_values'] == words and row['Y_values'] == ys
        accesses.append(dict(physical_bank=row['physical_bank'],cpu=row['cpu'],raw_hex=row['raw_hex'],classification=row['classification'],pointer_count=len(words),Y_count=len(ys),logical_address_count=len(logical),auxiliary_intersection=0,requirements=contract['required_execution_contract']))
    observations = read(OUT/'runtime/deployment-observations.json')
    points = read(OUT/'runtime/original-control/checkpoints.json')
    other = read(OUT/'runtime/observer/checkpoints.json')
    assert len(points) == len(other) == 160
    assert [p['frame'] for p in points] == list(range(1,161))
    for a,b in zip(points,other):
        assert a['frame'] == b['frame'] and a['fields'] == b['fields']
        for variant,p in (('original-control',a),('observer',b)):
            for key in ('image','state','RAM','SRAM'):
                assert (OUT/'runtime'/variant/p[key]).is_file()
        assert sha(OUT/'runtime/original-control'/a['image']) == sha(OUT/'runtime/observer'/b['image'])
    audio = []
    for variant in ('original-control','observer'):
        path = OUT/'runtime'/variant/'full-audio.wav'
        with wave.open(str(path),'rb') as stream:
            assert stream.getnchannels()==2 and stream.getsampwidth()==2 and stream.getframerate()==48000
            meta=dict(channels=2,sample_rate=48000,sample_frames=stream.getnframes(),duration_seconds=stream.getnframes()/48000)
        audio.append(dict(path=str(path.relative_to(OUT)),sha256=sha(path),**meta))
    # Keep a small exact event subset. Complete raw stream stays linked, not embedded.
    events = observations['full_software_entries'] + observations['logical_coordinate_reads']
    events += [r['following_original_store'] for r in observations['logical_read_to_unit_store_pairs']]
    events = sorted({e['sequence']:e for e in events}.values(), key=lambda e:e['sequence'])
    assert len(observations['full_software_entries']) == 3
    assert {e['opcode_PC'] for e in observations['full_software_entries']} == {0xB130,0xB1B0,0xB2AE}
    assert observations['logical_coordinate_read_count'] == 8
    assert not observations['city_auxiliary_bus_events']
    assert observations['untaken_formation_entries'] == [0xB312]
    assert all(e['actual_PRG_banks']==[6,8,9,31] and e['data_physical_bank']==6 for e in observations['logical_coordinate_reads'])
    sources=[]
    for name in ('deployment_pointer_services.py','deployment_pointer_integration.py'):
        path=ROOT/'source/recovered'/name
        sources.append(dict(name=name,path='../../source/recovered/'+name,text=path.read_text(),sha256=sha(path)))
    owner_rows=[]
    for owner in ownership['owners']:
        owner_rows.append(owner)
    return dict(native=native['summary'],points=points,audio=audio,events=events,observations=observations,source={k:source[k]for k in ('original_CPU_parent_cases','counts','source_guard_count')},integration={k:integration[k]for k in ('original_CPU_parent_cases','counts','guard_count')},contracts={k:contracts[k]for k in ('original_contract_CPU_cases','actual_caller_RTS_CPU_cases','constructor_prefix_CPU_cases','bare_access_counterexample_prefix_CPU_cases','model_guard_check_count')},static=static,accesses=accesses,ownership=ownership,completion=completion,denominators=denominators,erratum=erratum,sources=sources,acceptance=acceptance)

TEMPLATE = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>阶段26 · G107部署指针与真实开战</title><style>__STYLE__
.native-grid{grid-template-columns:548px minmax(0,1fr)}.native-grid>*{min-width:0}.native-data table{table-layout:fixed;width:100%}.native-data th,.native-data td{overflow-wrap:anywhere;word-break:break-word}.screens{gap:20px}img{border:0;outline:1px solid #64746a}.small{font-size:13px}.source pre{max-height:620px}.raw-display{max-height:400px}.result-change{padding:12px 16px;border-left:3px solid #287254;background:#e4eddf}.context-result{white-space:pre-wrap;overflow-wrap:anywhere}.controls input{min-width:220px}.chain{font:15px/1.8 ui-monospace,monospace;overflow-wrap:anywhere}.data-row{border-bottom:1px solid #ccd4cb}.data-row summary{font:14px/1.65 ui-monospace,monospace;padding:10px 0}.data-row pre{max-height:380px}@media(max-width:1120px){.native-grid{grid-template-columns:1fr}}@media(max-width:700px){.screens{gap:16px}.controls input{min-width:0;width:100%}}
</style></head><body><header><nav><a href="../phase25/index.html">阶段25</a><a href="README.md">本轮说明</a><a href="#native">原机开战</a><a href="#events">即时坐标</a><a href="#context">调用与返回</a><a href="#source">完整源码</a><a href="#acceptance">十维验收</a></nav><h1>G107：完整部署指针与真实开战</h1><p class="lede">从自然保存点普通确认开战，核对数据银行、完整坐标指针和场上单位写入。B1B0已有具名源码；本轮重构两段formation正文，并为四个间接读取建立完整调用者合同。本页只展示已保存证据，不运行模拟游戏。</p></header>
<div class="numbers"><span><strong id="nativeCount"></strong>两核心各fresh双跑控制帧</span><span><strong id="sourceCount"></strong>Source原CPU对照案</span><span><strong>4</strong>新增有条件不交访问</span><span><strong>335</strong>剩余候选访问</span></div>
<p class="warning">城市 <code>+1</code>、<code>+28..31</code> 的正式含义仍未知。静态不交证明只限完整producer、普通无中断返回及原始映射合同；裸入口和raw越界反例仍保留。原机路线只走第一侧，不代表第二侧已自然覆盖。</p>
<section id="native"><h2>同一次自然开战：原核心与独立观察核心</h2><div class="controls"><label for="checkpointSelect">实际原帧／保存点</label><select id="checkpointSelect"></select><button id="previousPoint">前一帧</button><button id="nextPoint">后一帧</button></div><p>母状态为冻结阶段11真实冷路线的frame5626；本轮导入一次，普通A35帧再松开125帧，零新增或继承数值准备。本轮本身不是冷启动。</p><div class="native-grid"><div class="screens"><figure><img id="originalImage" alt="固定原核心原始256×240画面"><figcaption>固定原核心 · 原始256×240</figcaption></figure><figure><img id="observerImage" alt="独立被动观察核心同帧原始画面"><figcaption>独立观察核心 · 同帧原始256×240</figcaption></figure></div><div class="native-data"><p id="checkpointCaption"></p><table><thead><tr><th>实际字段</th><th>保存值</th></tr></thead><tbody id="pointValues"></tbody></table><p id="pointHashes" class="small"></p></div></div><p id="pointLinks"></p><div class="controls"><label for="rawField">全部公开字段</label><select id="rawField"></select><label for="audioVariant">完整原录音</label><select id="audioVariant"><option value="0">固定原核心</option><option value="1">独立观察核心</option></select></div><details><summary>所选字段原始值</summary><pre id="rawFieldValue" class="raw-display"></pre></details><details><summary>该帧完整字段JSON</summary><pre id="allPointFields" class="raw-display"></pre></details><audio id="nativeAudio" controls preload="metadata"></audio><p id="audioScope" class="small"></p><p id="nativeScope" class="evidence-note"></p><p class="section-links"><a href="runtime/README.md">原机来源与边界</a><a href="runtime/validation.json">四fresh复跑回执</a><a href="runtime/evidence.json">完整清单</a><a href="runtime/core-provenance/build.json">独立观察核心来源</a><a href="runtime/original-control/input-plan.json">普通输入</a></p></section>
<section id="events"><h2>local139：即时指针、数据银行、原写入</h2><p>真实controller gates为[3,0]：第一侧进入 <code>B130→B1B0→B2AE</code>；第二侧 <code>B312</code>未走。八次逻辑坐标读取的即时PRG页为 <code>[6,8,9,31]</code>，数据来自physical6。帧末ZP和银行可能已被后续服务改写，不能倒推earlier read。</p><div class="controls"><label for="eventSelect">关键原事件</label><select id="eventSelect"></select><button id="previousEvent">前一事件</button><button id="nextEvent">后一事件</button></div><p id="eventScope"></p><div class="horizontal"><table><thead><tr><th>序号／帧／种类</th><th>原opcode／地址</th><th>即时值与backing</th><th>完整指针／实际银行</th></tr></thead><tbody id="eventCurrent"></tbody></table></div><details><summary>该事件完整原字段</summary><pre id="eventRaw" class="raw-display"></pre></details><details><summary>八组原读取→之后单位写入</summary><pre id="readStorePairs" class="raw-display"></pre></details><p class="section-links"><a href="runtime/deployment-observations.json">精确配对与入口</a><a href="runtime/observer/events.jsonl">全部解码事件</a><a href="runtime/observer/bus-events.bin">原44-u32 ABI流</a><a href="runtime/observer/snapshot-index.jsonl">三份完整软件快照索引</a></p><p class="scope">固定原核心没有内部CPUtrace；只有独立被动核心提供选定opcode/bus事件。完整软件快照不含即时N163/PPU/APU；CPU与Source共同N163是显式夹具。logical有效地址与寻址dummy总线读分列，零auxiliary事件只是这160帧的有限负观测。</p></section>
<section id="context"><h2>真实owner与完成边界</h2><p class="chain">fixed31 E18B → selector $28（十进制40）→ pair8/9 A003 → B130 → B1B0 → B2AE 或 B312</p><p><code>0500==11</code>时原E18B改走pair12/13 A006单挑结果路径，绕过这里的部署。E18B终点 <code>E066</code>是main-loop边界，不能计caller RTS。新统一工厂仅接管pair8/9五个明确入口，其余调用沿冻结阶段25父owner。</p><div class="controls"><label for="contextSearch">entry／caller／owner搜索</label><input id="contextSearch" type="search" placeholder="B1B0、B2AE、B312、E066"><label for="contextKind">合同种类</label><select id="contextKind"><option value="all">全部</option><option value="entry">入口owner</option><option value="caller">真实局部caller</option><option value="boundary">完成边界</option></select></div><p id="contextCount"></p><div id="contextRows"></div><p class="scope">正常完成必须有status=returned，实际PC和SP都等于该ServiceCall真实caller值。waiting/dependency、strict prefix、非局部返回、reset与E066各自保留；不能写ready、伪栈或仅改PC/SP来宣称完成。</p><p class="section-links"><a href="context/README.md">只读调用索引</a><a href="context/owner-and-caller-chain.json">完整入口与原字节</a><a href="context/completion-contracts.json">返回与mapper合同</a><a href="context/stable-denominators.json">稳定分母与历史scope</a><a href="context/verification.json">15项静态检查／0CPU／0Native</a></p></section>
<section id="contracts"><h2>四个read，完整word域与裸入口分开</h2><p>稳定1526间接位置：1191条件不交、81可能别名、254未知；候选339→335。新排除仅 <code>8:B272/B278/B290/B296</code>。完整formation先重建20/21，保留rawcity0..255、全部byte模板偏移及Y0..255，两个真实callsite构成读取前必经cut。不能将旧profile指针或独立low/high投影拼成新城市地址。</p><table><thead><tr><th>原read</th><th>权威完整pointer／Y域</th><th>逻辑有效地址与aux交集</th></tr></thead><tbody id="contractRows"></tbody></table><p>第一侧offset为32×byte mod256；第二侧为34×byte mod256。冻结阶段11/25文档的“36B”是历史文字错误，本轮单独更正；既有源码已执行34×，不算新算法首次发现。正常0..29城市读bank6 ROM；完整raw域含RAM镜像及第二侧2000..200E潜在IO，只证明地址域，不执行缺硬件输入的IO、不推断合法游戏城市。</p><p class="section-links"><a href="fields-static/deployment-pointer-postconditions.json">完整producer／mapper／必经cut</a><a href="fields-static/selected-accesses.json">四项权威合同</a><a href="fields-static/all-indirect-accesses.json">1526逐项账本</a><a href="fields-static/remaining-accesses.json">335项保留候选</a><a href="fields-static/logical-vs-dummy-bus-contracts.json">逻辑与条件dummy</a><a href="context/historical-wording-erratum.json">34×历史文字更正</a></p></section>
<section id="source"><h2>已有命名控制，新增可读formation重构</h2><p><code>B1B0 assign_strategies_and_positions</code>继续继承冻结的battle_setup_ai；两段formation合计92原位置、187字节改为具名直接函数。新Source不解释原CPU或控制IR，真实服务未完成就保留依赖。本轮不是将整个旧799位置模块重新计为首次恢复。</p><table><thead><tr><th>独立证据域</th><th>实际计数与scope</th></tr></thead><tbody id="caseCounts"></tbody></table><p class="section-links"><a href="deployment/validation.json">Source实际对照</a><a href="deployment/README.md">具名服务与raw输入</a><a href="source-integration.json">统一工厂对照</a><a href="fields-static/verification.json">独立原CPU合同</a><a href="fields-static/README.md">合同前提</a></p>__SOURCES__</section>
<section id="acceptance"><h2>十维验收：本轮变化与待验范围</h2><p>Source、原字节重建、静态合同和Native分别验收；恢复Python不是原作者工程，也未证明由高级源码编译同一NES。硬件音画仍由原核心合成，整体未知服务数量与完成百分比都不强填。</p><div class="controls"><label for="acceptanceSelect">验收维度</label><select id="acceptanceSelect"></select></div><div id="acceptanceDetail"></div><p class="section-links"><a href="acceptance/README.md">十维要求与来源</a><a href="acceptance/requirements.json">结构化验收</a><a href="acceptance/verification.json">引用核查</a><a href="investigation-checklist.json">本轮调查清单</a></p></section>
<footer>阶段1..25冻结产物继续保留。本轮为依赖既有版本的小增量，不改原ROM、固定核心或旧ZIP。最终总审计、归档与解压结果分别见 <a href="verification.json">verification.json</a>、<a href="package-receipt.json">package-receipt.json</a>；页面不预先宣布它们通过。</footer>
<script id="evidence-data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('evidence-data').textContent),el=id=>document.getElementById(id),pretty=v=>JSON.stringify(v,null,2),hex=(v,n=4)=>v==null?'—':Number(v).toString(16).toUpperCase().padStart(n,'0');let pointIndex=138,eventIndex=3;
function option(s,v,l){const o=document.createElement('option');o.value=v;o.textContent=l;s.append(o)}function link(p,u,l){const a=document.createElement('a');a.href=u;a.textContent=l;p.append(a)}function row(t,l,v){const tr=document.createElement('tr');for(const x of[l,v]){const td=document.createElement('td');td.textContent=typeof x==='string'?x:JSON.stringify(x);tr.append(td)}t.append(tr)}
function field(){el('rawFieldValue').textContent=pretty(d.points[pointIndex].fields[el('rawField').value])}
function point(){const p=d.points[pointIndex],f=p.fields;el('checkpointSelect').value=pointIndex;el('originalImage').src='runtime/original-control/'+p.image;el('observerImage').src='runtime/observer/'+p.image;el('checkpointCaption').textContent=`local${p.frame} · ${p.label}`;el('pointValues').replaceChildren();for(const pair of[['global7A / NMI78',`${f.global_007A} / ${f.NMI_0078}`],['battle0500/0501',f.battle_0500_0501],['原保存CPU寄存器',f.actual_saved_CPU_registers],['帧末实际PRG页',f.actual_saved_PRG_banks],['0507两君主packed原byte',f.raw_packed_0507],['战场城市050E / 邻城052A',`${f.battle_city_050E} / ${f.neighbor_city_052A}`],['策略6FA1..6FB4',f.strategies_6FA1_6FB4],['单位ID0664[20]',f.officer_ids_0664],['单位X0600[20]',f.unit_x_0600],['单位Y0614[20]',f.unit_y_0614],['profile counts6F99..6FA0',f.profile_counts_6F99_6FA0],['帧末DE/DF原selector',f.frame_end_raw_bank_selectors_DE_DF]])row(el('pointValues'),...pair);el('pointLinks').replaceChildren();for(const v of['original-control','observer']){el('pointLinks').append(v+'：');for(const k of['state','RAM','SRAM']){link(el('pointLinks'),'runtime/'+v+'/'+p[k],k);el('pointLinks').append(' · ')}}el('pointHashes').textContent=`完整state ${f.whole_serialized_state_bytes}B；本帧PCM ${f.PCM_bytes}B；累计PCM止点${f.PCM_stop_byte}。`;const old=el('rawField').value;el('rawField').replaceChildren();Object.keys(f).forEach(k=>option(el('rawField'),k,k));if(Object.hasOwn(f,old))el('rawField').value=old;field();el('allPointFields').textContent=pretty(f);el('previousPoint').disabled=pointIndex===0;el('nextPoint').disabled=pointIndex===d.points.length-1}
function audio(){const a=d.audio[Number(el('audioVariant').value)];el('nativeAudio').pause();el('nativeAudio').src=a.path;el('audioScope').textContent=`原48kHz stereo16bit WAV · ${a.sample_frames} sample pairs · ${a.duration_seconds.toFixed(3)}秒 · SHA256 ${a.sha256}`}
d.points.forEach((p,i)=>option(el('checkpointSelect'),i,`local${p.frame} · ${p.label}`));el('checkpointSelect').onchange=()=>{pointIndex=Number(el('checkpointSelect').value);point()};el('previousPoint').onclick=()=>{if(pointIndex){pointIndex--;point()}};el('nextPoint').onclick=()=>{if(pointIndex+1<d.points.length){pointIndex++;point()}};el('rawField').onchange=field;el('audioVariant').onchange=audio;point();audio();
function event(){const e=d.events[eventIndex];el('eventSelect').value=eventIndex;el('eventCurrent').replaceChildren();const tr=document.createElement('tr');for(const v of[`${e.sequence} / local${e.frame} / ${e.kind}`,`${e.physical_bank}:${hex(e.opcode_PC)} → ${hex(e.address)}`,`value=${e.value}; backing=${e.physical_storage_byte_after_event??'未记录'}`,`20/21=${hex(e.pointer_0020_0021)}; PRG=${e.actual_PRG_banks.join('/')}; SP=${hex(e.SP,2)}`]){const td=document.createElement('td');td.textContent=v;tr.append(td)}el('eventCurrent').append(tr);el('eventScope').textContent=e.logical_coordinate_read?`逻辑坐标读取；实际data bank${e.data_physical_bank}，ROM文件偏移${hex(e.data_ROM_offset,6)}（含16B头）。`:e.kind==='opcode_boundary'?'真正被动opcode入口；稀疏软件快照不等于瞬时设备状态。':'原写入尝试；用physical backing与之后原RAM共同核对。';el('eventRaw').textContent=pretty(e);el('previousEvent').disabled=eventIndex===0;el('nextEvent').disabled=eventIndex===d.events.length-1}
d.events.forEach((e,i)=>option(el('eventSelect'),i,`${e.sequence} / local${e.frame} / ${e.physical_bank}:${hex(e.opcode_PC)} / ${e.kind}`));el('eventSelect').onchange=()=>{eventIndex=Number(el('eventSelect').value);event()};el('previousEvent').onclick=()=>{if(eventIndex){eventIndex--;event()}};el('nextEvent').onclick=()=>{if(eventIndex+1<d.events.length){eventIndex++;event()}};event();el('readStorePairs').textContent=pretty(d.observations.logical_read_to_unit_store_pairs);
const ns=d.native;el('nativeCount').textContent=ns.all_control_frames;el('sourceCount').textContent=d.source.original_CPU_parent_cases+d.integration.original_CPU_parent_cases;el('nativeScope').textContent=`一条自然续行路线160帧，两核心各fresh双跑${ns.all_control_frames}控制帧；${ns.nonempty_artifact_repeat_checks}份非空artifact复跑检查、${ns.PNG_checks}张原PNG、${ns.WAV_checks}份原WAV。完整初始及逐帧RAM/SRAM/RGB/PCM/未归一化state五缓冲相等。独立核${ns.observer_events}条事件、${ns.full_software_snapshots}份完整软件snapshot；Source病例0。`;
const contexts=d.ownership.owners.map(x=>({kind:'entry',title:`8:${hex(x.entry??x.target)} · ${x.current26_owner}`,data:x}));for(const c of d.ownership.local_calls)contexts.push({kind:'caller',title:`${hex(c.JSR_call_PC)} → ${c.callee_function}`,data:c});contexts.push({kind:'boundary',title:'E18B → E066/main11 bypass',data:d.ownership.parent_branch},{kind:'boundary',title:'正常caller RTS',data:d.completion.normal_caller_RTS});for(const b of d.completion.not_normal_RTS)contexts.push({kind:'boundary',title:b.kind,data:b});
function context(){const q=el('contextSearch').value.trim().toUpperCase(),kind=el('contextKind').value,rows=contexts.filter(r=>(kind==='all'||r.kind===kind)&&(!q||(r.title+' '+pretty(r.data)).toUpperCase().includes(q)));el('contextRows').replaceChildren();for(const r of rows){const box=document.createElement('details');box.className='data-row';const h=document.createElement('summary');h.textContent=r.title;box.append(h);const p=document.createElement('pre');p.textContent=pretty(r.data);box.append(p);el('contextRows').append(box)}el('contextCount').textContent=`${rows.length}条入口／caller／边界合同；不是全局未知服务数量。`};el('contextSearch').oninput=context;el('contextKind').onchange=context;context();
for(const a of d.accesses){const tr=document.createElement('tr');for(const value of[`${a.physical_bank}:${hex(a.cpu)} / ${a.raw_hex}`,`${a.pointer_count} complete words × ${a.Y_count} Y值`,`${a.logical_address_count} logicalEA；aux交集${a.auxiliary_intersection}`]){const td=document.createElement('td');td.textContent=value;tr.append(td)}el('contractRows').append(tr)}
row(el('caseCounts'),'新Source服务',`${d.source.original_CPU_parent_cases}案；${pretty(d.source.counts)}；${d.source.source_guard_count}guards`);row(el('caseCounts'),'统一工厂',`${d.integration.original_CPU_parent_cases}案；${pretty(d.integration.counts)}；${d.integration.guard_count}guards`);row(el('caseCounts'),'独立原CPU静态合同',`${d.contracts.original_contract_CPU_cases}案：${d.contracts.actual_caller_RTS_CPU_cases}RTS / ${d.contracts.constructor_prefix_CPU_cases}构造prefix / ${d.contracts.bare_access_counterexample_prefix_CPU_cases}裸read反例prefix；${d.contracts.model_guard_check_count}模型guards；Source0`);row(el('caseCounts'),'只读context',`15checks；新Source/CPU/Native均0。冻结旧2326案只比较1972RAM+8192SRAM，保留原scope。`);
function acceptance(){const x=d.acceptance.dimensions[Number(el('acceptanceSelect').value)],box=el('acceptanceDetail');box.replaceChildren();const h=document.createElement('h3');h.textContent=x.id+' · '+x.title;box.append(h);const s=document.createElement('p');s.id='dimensionStatus';s.className='evidence-note';s.textContent=x.acceptance_status_zh||x.acceptance_status;box.append(s);const p=document.createElement('p');p.textContent=x.current_scope;box.append(p);const delta=document.createElement('div');delta.className='result-change';delta.id='phase26Change';for(const key of['result','remaining_gap']){const p=document.createElement('p');p.textContent=(key==='result'?'本轮变化：':'仍待验：')+x.phase26_change[key];delta.append(p)}box.append(delta);for(const [title,key]of[['已验结果与回执','verified_results'],['待验结果','pending_results'],['验收方法','acceptance_method']]){const h=document.createElement('h3');h.textContent=title;box.append(h);const ul=document.createElement('ul');ul.id=key;for(const v of x[key]||[]){const li=document.createElement('li');if(typeof v==='string')li.textContent=v;else{li.append(v.claim+' ');link(li,'../../'+v.evidence,v.evidence)}ul.append(li)}box.append(ul)}}d.acceptance.dimensions.forEach((x,i)=>option(el('acceptanceSelect'),i,x.id+' · '+x.title));el('acceptanceSelect').onchange=acceptance;acceptance();
</script></body></html>'''

class Inspect(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.links=[]; self.ids=[]; self.pre={}; self.active=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if tag=='pre' and a.get('id','').startswith('source-code-'): self.active=a['id']; self.pre[self.active]=''
    def handle_data(self,value):
        if self.active: self.pre[self.active]+=value
    def handle_endtag(self,tag):
        if tag=='pre': self.active=None

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--check-only',action='store_true'); a=p.parse_args()
    data=inputs()
    style=re.search(r'<style>(.*?)</style>',(ROOT/'analysis/phase24/index.html').read_text(),re.S).group(1)
    modules=[]
    for i,s in enumerate(data['sources'],1):
        modules.append('<details class="source"><summary>'+html.escape(s['name'])+'</summary><p><a href="'+s['path']+'">完整UTF-8源文件</a> · SHA256 <code>'+s['sha256']+'</code></p><pre id="source-code-'+str(i)+'">'+html.escape(s['text'])+'</pre></details>')
    payload={k:v for k,v in data.items() if k!='sources'}
    page=TEMPLATE.replace('__STYLE__',style).replace('__SOURCES__','\n'.join(modules)).replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
    qa=Inspect(); qa.feed(page); assert len(qa.ids)==len(set(qa.ids))
    for i,s in enumerate(data['sources'],1): assert qa.pre['source-code-'+str(i)]==s['text']
    # Aggregate/ZIP receipts are produced after browser acceptance, not silently claimed now.
    future={'verification.json','package-receipt.json'}
    missing=[u for u in qa.links if not u.startswith(('#','http:','https:')) and u not in future and not (OUT/u.split('#')[0]).exists()]
    assert not missing, missing
    js=re.findall(r'<script>(.*?)</script>',page,re.S)[0]; node=shutil.which('node'); assert node
    r=subprocess.run([node,'--check'],input=js,text=True,capture_output=True); assert r.returncode==0,r.stderr
    if not a.check_only: (OUT/'index.html').write_text(page)
    print(json.dumps(dict(status='static_checks_passed' if a.check_only else 'built_static_checks_passed',HTML_created=not a.check_only,HTML_sha256=hashlib.sha256(page.encode()).hexdigest(),HTML_bytes=len(page.encode()),source_UTF8_exact=True,source_modules=2,unique_DOM_ids=len(qa.ids),local_links=len(qa.links),missing_links=missing,JS_syntax_passed=True,native_routes=1,native_points=len(data['points']),embedded_events=len(data['events']),selected_accesses=len(data['accesses']),acceptance_dimensions=len(data['acceptance']['dimensions']),source_CPU_cases=0,Native_runs=0)))

if __name__=='__main__': main()
