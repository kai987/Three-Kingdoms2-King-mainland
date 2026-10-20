#!/usr/bin/env python3
"""Build only final31 evidence; no emulator, CPU or frozen producer execution."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase31'
BASE = ROOT / 'analysis/phase30'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def pins(document):
    for group in ('source_sha256', 'source_and_validator_sha256', 'artifact_sha256',
                  'artifact_and_dependency_sha256', 'input_sha256'):
        values = document.get(group, {})
        if isinstance(values, dict):
            for path, value in values.items():
                if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
                    assert (ROOT / path).is_file() and sha(ROOT / path) == value, (group, path)


def event_objects(value):
    if isinstance(value, dict):
        if all(key in value for key in ('sequence', 'kind', 'opcode_PC', 'actual_PRG_banks')):
            yield value
        else:
            for child in value.values():
                yield from event_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from event_objects(child)


def displayed_points(original, observer, plan, observations):
    """An explicit projection, never the full-route frame denominator."""
    assert len(original) == len(observer) and original
    by = {point['frame']: point for point in original}
    other = {point['frame']: point for point in observer}
    assert len(by) == len(original) and set(by) == set(other)
    for frame, point in by.items():
        assert point['fields'] == other[frame]['fields']
        assert len(point['fields']) == len(other[frame]['fields']) == 49
    reasons = {}
    def add(frame, reason):
        for target in (frame - 1, frame, frame + 1):
            if target in by:
                reasons.setdefault(target, set()).add(reason + (' / adjacent' if target != frame else ''))
    add(min(by), 'first frame')
    add(max(by), 'last frame')
    previous = None
    for frame, point in sorted(by.items()):
        fields = point['fields']
        signature = tuple(json.dumps(fields.get(key), sort_keys=True) for key in (
            'global_007A', 'NMI_0078', 'battle_0500_0501',
            'active_human_disposition', 'raw_destination_0540'))
        if previous is not None and signature != previous:
            add(frame, 'observed main/NMI/phase/human/destination change')
        previous = signature
    for step in plan:
        add(step['start_frame'] + 1, 'ordinary input-plan boundary')
    for key in ('actual_BC46_calls', 'actual_early_JSR_boundaries',
                'commander_outcome_producer_writes', 'outcome_0514_original_writes',
                'title_Start_bypass', 'ruler_controller_writes', 'postbattle_SRAM_writes'):
        for event in event_objects(observations.get(key, [])):
            add(event['frame'], 'original event:' + key)
    return [dict(by[frame], display_selection_reasons=sorted(reasons[frame])) for frame in sorted(reasons)], [other[frame] for frame in sorted(reasons)]


def inputs():
    acceptance = read(OUT / 'acceptance/requirements.json')
    av = read(OUT / 'acceptance/verification.json')
    assert acceptance['scaffold_status'] == 'final_evidence_reviewed'
    assert len(acceptance['dimensions']) == 10
    assert all('PENDING' not in json.dumps(row['phase31_change']) for row in acceptance['dimensions'])
    source = read(OUT / 'player-disposition/validation.json')
    native = read(OUT / 'runtime/evidence.json')
    nv = read(OUT / 'runtime/validation.json')
    fields = read(OUT / 'fields-static/verification.json')
    for document in (av, source, native, nv, fields):
        assert document['status'] == 'passed'
        pins(document)
    assert source['quick'] is False
    assert source['original_CPU_parent_cases'] == 325 and source['counts'] == {'actual_caller_RTS': 317, 'strict_dependency_prefix': 8}
    assert source['source_guard_count'] == 0
    assert source['new_production_source_modules'] == 0 and source['new_gameplay_algorithm_claim'] is False
    assert len(source['cases']) == source['original_CPU_parent_cases'] == sum(source['counts'].values())
    assert source['source_original_CPU_callbacks'] == 0 and source['production_IR_interpretation'] is False
    assert all(row['source_original_CPU_callbacks'] == 0 for row in source['cases'])
    assert native['script_sha256'] == sha(ROOT / 'scripts/capture_native_postbattle_disposition.py')
    assert nv['evidence_sha256'] == sha(OUT / 'runtime/evidence.json')
    assert native['summary'] == {key: nv[key] for key in native['summary']}
    assert all(native['summary'][key] for key in (
        'all_five_complete_buffers_equal_each_frame', 'initial_API_complete_buffers_equal',
        'all_artifacts_repeat_exact', 'full_serialized_buffers_not_normalized'))
    assert native['summary']['additional_core_memory_writes'] == 0
    assert native['summary']['routes'] == 4 and native['summary']['first_original_frames'] == 2204
    assert native['summary']['all_control_frames'] == 8816 and native['summary']['fresh_process_runs'] == 16
    assert fields['source_CPU_cases'] == fields['Native_runs'] == 0
    assert fields['original_contract_CPU_cases'] == 13998
    assert fields['actual_caller_RTS_CPU_cases'] == 13992 and fields['explicit_prefix_CPU_cases'] == 6
    assert fields['model_guard_check_count'] == 29 and fields['remaining_access_count'] == 325
    assert fields['all_indirect_classification_counts'] == dict(
        proved_disjoint_auxiliary_address_domain=1201,
        possible_city_auxiliary_alias=80, unresolved_pointer_or_index_contract=245)
    routes = []
    roles = {
        'human_entries': 'human_phase_entry', 'software_inputs': 'passive_software_input',
        'actual_BC46_calls': 'actual_BC46_call_return', 'mode_targets': 'actual_mode_target',
        'actual_early_JSR_boundaries': 'actual_JSR_boundary',
        'outcome_0514_original_writes': 'all_original_0514_writes',
        'commander_outcome_producer_writes': 'commander_outcome_producer',
        'title_Start_bypass': 'ordinary_Start_bypass',
        'ruler_controller_writes': 'original_ruler_controller_write',
        'postbattle_SRAM_writes': 'postbattle_SRAM_write',
        'auxiliary_bus_events': 'auxiliary_bus_event',
        'controller_byte_reads': 'controller_read',
    }
    for record in native['routes']:
        case = record['case']
        folder = OUT / 'runtime' / case
        original = read(folder / 'original-control/checkpoints.json')
        observer = read(folder / 'observer/checkpoints.json')
        obs = read(OUT / 'runtime' / record['observations'])
        plan = read(folder / 'original-control/input-plan.json')
        assert len(original) == len(observer) == record['frames']
        points, others = displayed_points(original, observer, plan, obs)
        for point, other in zip(points, others):
            for variant, current in (('original-control', point), ('observer', other)):
                for key in ('image', 'state', 'RAM', 'SRAM'):
                    assert (folder / variant / current[key]).is_file()
            assert sha(folder / 'original-control' / point['image']) == sha(folder / 'observer' / other['image'])
        selected = {}
        for key, role in roles.items():
            for event in event_objects(obs.get(key, [])):
                sequence = event['sequence']
                if sequence not in selected:
                    selected[sequence] = dict(event, display_roles=[])
                else:
                    assert {k: v for k, v in selected[sequence].items() if k != 'display_roles'} == event
                if role not in selected[sequence]['display_roles']:
                    selected[sequence]['display_roles'].append(role)
        found = set()
        with (folder / 'observer/events.jsonl').open() as stream:
            for line in stream:
                event = json.loads(line)
                if event['sequence'] in selected:
                    assert {k: v for k, v in selected[event['sequence']].items() if k != 'display_roles'} == event
                    found.add(event['sequence'])
        assert found == set(selected)
        audio = []
        for variant in ('original-control', 'observer'):
            path = folder / variant / 'full-audio.wav'
            with wave.open(str(path), 'rb') as wav:
                assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (2, 2, 48000)
                meta = dict(sample_frames=wav.getnframes(), duration_seconds=wav.getnframes() / 48000)
            audio.append(dict(path=str(path.relative_to(OUT)), sha256=sha(path), **meta))
        compact = {key: value for key, value in obs.items() if not isinstance(value, list)}
        compact.update(actual_BC46_calls=obs['actual_BC46_calls'],
                       displayed_event_counts=dict(Counter(role for event in selected.values() for role in event['display_roles'])),
                       complete_observation_path='runtime/' + record['observations'])
        ancestry_scope = None
        if record['ancestry'].get('segmented_upstream_frames') is not None:
            ancestry_scope = dict(
                upstream_original_core_segments=record['ancestry']['upstream_original_core_runs'],
                upstream_original_core_single_run_frames=record['ancestry']['segmented_upstream_frames'],
                upstream_fresh_repeat_claim=record['ancestry']['upstream_fresh_repeat_claim'],
                new_formal_fresh_window_frames=record['frames'],
                scope='Upstream ordinary-input segmented lineage is not part of the new window fresh-repeat denominator.')
        routes.append(dict(case=case, base='runtime/' + case + '/', title=case,
                           full_route_frames=record['frames'], displayed_point_count=len(points),
                           points=points, observer_points=others, audio=audio,
                           natural_ordinary_input_route=record['natural_ordinary_input_route'],
                           controlled_ancestry=record['controlled_ancestry'], ancestry=record['ancestry'],
                           segmented_ancestry_scope=ancestry_scope,
                           events=sorted(selected.values(), key=lambda item: item['sequence']),
                           observations=compact, input_plan=plan))
    assert sum(route['full_route_frames'] for route in routes) == native['summary']['first_original_frames']
    sources = []
    for name in ('battle_scene_controller.py', 'postbattle_release_services.py', 'postbattle_early_services.py'):
        path = ROOT / 'source/recovered' / name
        sources.append(dict(name=name, path='../../source/recovered/' + name, text=path.read_text(), sha256=sha(path)))
    return dict(native=native['summary'], routes=routes, event_roles=roles,
                display_policy='first/last; observed main/NMI/phase/active-human/destination changes; input-plan boundaries; original allocation/outcome/Start/roster events; each with adjacent±1 actual frames. No hidden cap. Full route manifests remain linked.',
                source={key: source[key] for key in ('original_CPU_parent_cases', 'counts', 'source_guard_count',
                    'new_production_source_modules', 'new_gameplay_algorithm_claim', 'limits')},
                fields={key: fields[key] for key in ('original_contract_CPU_cases', 'actual_caller_RTS_CPU_cases',
                    'explicit_prefix_CPU_cases', 'model_guard_check_count', 'remaining_access_count',
                    'all_indirect_classification_counts', 'newly_proved_disjoint_all_count')},
                roster_contract=read(OUT / 'fields-static/roster-write-lifecycle-contract.json'),
                field_counterexamples={key: fields[key] for key in ('bare_BD96_counterexamples',
                    'bare_BDB8_alias_prefixes', 'controlled_nontrivial_swaps',
                    'controlled_same_value_escape_protocol', 'controlled_raw_city_future_aliases')},
                sources=sources, acceptance=acceptance)


TEMPLATE = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>阶段31 · 连续玩家处置与完整名单写入合同</title><style>__STYLE__
.native-grid>*{min-width:0}.native-data table,.scope-table{table-layout:fixed;width:100%}.native-data td,.native-data th,.scope-table td,.scope-table th{overflow-wrap:anywhere;word-break:break-word}.raw-display{max-height:430px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}.source pre{max-height:620px;overflow:auto}.source summary{overflow-wrap:anywhere}.controls{flex-wrap:wrap}.result-change{padding:12px 16px;border-left:3px solid #287254;background:#e4eddf}.chain{font:15px/1.8 ui-monospace,monospace;overflow-wrap:anywhere}
</style></head><body><header><nav><a href="../phase30/index.html">阶段30</a><a href="README.md">本轮说明</a><a href="#native">连续路线与展示点</a><a href="#events">真实调用与写入</a><a href="#source">复用完整源码</a><a href="#fields">名单字段合同</a><a href="#acceptance">十维验收</a></nav><h1>连续玩家处置与完整 BC46 名单写入</h1><p class="lede">区分原机完整路线、页面展示采样点、复用源码的新软件对照，以及独立字段合同。完整父链条件下BDB8只写名册17..26；裸入口与工作区自覆盖反例保留，城市辅助字段不强填正式名称。</p></header><div class="numbers"><span><strong id="nativeCount"></strong>fresh复跑控制帧</span><span><strong id="displayCount"></strong>明确选定展示点</span><span><strong id="sourceCount"></strong>复用Source对照案</span><span><strong>325</strong>保留候选</span></div><p class="warning">城市+1／+28..31正式名称与未知唯一服务数仍为null，整款闭包仍为false。阶段31完成后等待评估，不自动开始32。页面显示点数不等完整路线帧数；Source对照不等在同一Source实例中连续运行整段UI。</p>
<section id="native"><h2>完整原路线与明确的展示点</h2><div class="controls"><label for="routeSelect">正式路线</label><select id="routeSelect"></select><label for="checkpointSelect">选定原保存点</label><select id="checkpointSelect"></select><button id="previousPoint">前一展示点</button><button id="nextPoint">后一展示点</button></div><p id="routeScope" class="evidence-note"></p><p id="selectionScope"></p><div class="native-grid"><div class="screens"><figure><img id="originalImage" alt="固定原核心原始256×240"><figcaption>固定原核心 · 原始256×240</figcaption></figure><figure><img id="observerImage" alt="被动观察核心同帧原始256×240"><figcaption>被动观察核心 · 同帧原始256×240</figcaption></figure></div><div class="native-data"><p id="checkpointCaption"></p><table><thead><tr><th>原字段</th><th>实际保存值</th></tr></thead><tbody id="pointValues"></tbody></table><p id="pointReason" class="small"></p></div></div><p id="pointLinks"></p><div class="controls"><label for="rawField">原核心49字段</label><select id="rawField"></select><label for="observerRawField">观察核心49字段</label><select id="observerRawField"></select></div><details><summary>所选原核心字段</summary><pre id="rawFieldValue" class="raw-display"></pre></details><details><summary>所选观察核心字段</summary><pre id="observerRawFieldValue" class="raw-display"></pre></details><details><summary>本展示点全部两核字段</summary><pre id="allPointFields" class="raw-display"></pre></details><details><summary>普通输入计划与祖先准备</summary><pre id="ancestry" class="raw-display"></pre></details><div class="controls"><label for="audioVariant">完整原WAV</label><select id="audioVariant"><option value="0">固定原核心</option><option value="1">被动观察核心</option></select></div><audio id="nativeAudio" controls preload="metadata"></audio><p id="audioScope" class="small"></p><p id="nativeScope"></p><p id="manifestLinks"></p><p class="scope">五完整缓冲一致只指每条新路线自身的两核心与fresh复跑；历史绝对帧的PCM／state不声称相同，也不做归一化。固定原核心没有内部CPUtrace。被动软件快照没有捕获即时N163／PPU／APU。</p><p class="section-links"><a href="runtime/evidence.json">正式路线清单</a><a href="runtime/validation.json">完整复跑回执</a><a href="runtime/core-provenance/build.json">观察核心来源</a><a href="runtime/README.md">原机范围</a></p></section>
<section id="events"><h2>实际父链、结果生产者与同值写</h2><p>保存值0514可能只是旧scratch；只有实际原写事件能说明本窗口中的生产者。BB36／BB8C的预期返回PC与真正捕获到BB39／BB8F返回边界分开，不从压栈字节反推未观察到的返回。</p><p>自然AI窗口真实DD9E在local4写0514=1，local502捕获BB36→BC46 mode2→BB39及相同caller SP。但当时临时buffer为空：21次6FA1..6FB5为FF→FF，BC46内BDB8与城市写均0。local504的D4BA玩家回城写6171、local525的BC3C／BC43同值写另列；不把这些算成mode2非平凡分配。非空分配与完整BD96合同属于独立受控CPU域。</p><p>自然13窗口实际触及6301一次：13:D243的原指令为STA($00),Y，pointer=63FC、Y=5，逻辑写入6401=2；6301是未进位跨页dummy读。它计入auxiliary_bus_event总线类别，但不是逻辑辅助字段消费者，不沿用“aux事件0”，也不给城市+1命名。</p><div class="controls"><label for="eventRole">原事件层</label><select id="eventRole"></select><label for="eventSelect">实际记录</label><select id="eventSelect"></select><button id="previousEvent">前一事件</button><button id="nextEvent">后一事件</button></div><p id="eventScope"></p><div class="horizontal"><table class="scope-table"><thead><tr><th>序号／帧／种类</th><th>PC／地址</th><th>phase／mode／SP</th><th>原值／物理写后值</th></tr></thead><tbody id="eventCurrent"></tbody></table></div><details><summary>完整原72-u32解码记录及显示角色</summary><pre id="eventRaw" class="raw-display"></pre></details><details><summary>实际BC46调用与已捕获返回证据</summary><pre id="callProtocol" class="raw-display"></pre></details><p id="eventLinks"></p><p class="scope">read、write_attempt与dummy总线地址不是同一语义；同值store也不能按最终diff丢弃。页面只投影明确类别，全部原始事件、72-u32二进制和snapshot索引另行链接。unknown服务数量不由语法标记估算。</p></section>
<section id="source"><h2>复用三个完整源码文件，不重算首次恢复</h2><p>BattleSceneController承载原阶段13／14及其局部UI正文；PostbattleReleaseController仅替换D1F9／D20D／D299分配／释放细节，并继承普通wrapper和其余阶段；PostbattleEarlyServices承载早期A006四态caller协议。不能把继承wrapper本身冒充13／14全部实现。</p><p>本轮没有新增生产模块或首次算法恢复，实际执行复用冻结owner与前门，Source侧不执行原CPU或控制IR。325个软件case＝192新数值夹具＋2旧30受控BB36＋14旧被动＋117新31被动；117中87自然祖先／30受控祖先。317正常RTS、8故意缺服务prefix、0独立guard。这325与剩余325字段候选是两个独立分母，恰好同数。</p><p>每case使用全新Source实例；同一Native回调可对应多API层案例，不宣称一个Source实例连续跑完原机长路线。N163是共同显式软件夹具，非即时Native设备捕获。Python恢复也不等于原作者工程或可编译同一NES。</p><table class="scope-table"><thead><tr><th>独立证据域</th><th>最终计数与边界</th></tr></thead><tbody id="caseCounts"></tbody></table><p class="section-links"><a href="player-disposition/validation.json">复用Source实际矩阵</a><a href="player-disposition/README.md">Source范围</a></p>__SOURCES__</section>
<section id="fields"><h2>一个完整父链条件：BDB8只写十个名册槽</h2><p class="chain">BC65 → BD96 → BC68 ／ BD8E → BD96 → BD91 ／ BC8E → BD96 → BC91 ／ BCC9 → BD96 → BCCC</p><p>完整BC46正常mode0／1／2、当前及来源city0..29、ruler0..6、binary且无中断前提下，四caller的03分别17、17..26、18..26、17。原邻接表30行均有限负终止，BE90实际选bank16。F2AF只重建00／01且保留live03／04；BDB8每次写后才检查27，因此父链域与裸入口必须分开。</p><p>全部256个F2AF对齐word只作更宽store-address lemma，不扩大完整父链正常city域。裸03=1／27..31／255、BDB8的ZP／mirror／stack别名和rawcity125自覆盖全部保留；+27在名册外，但不是本支线的150个目标aux地址。</p><details><summary>权威父链与原字节合同</summary><pre id="rosterContract" class="raw-display"></pre></details><details><summary>异常先写、FF洞换位、同值写与真实后续自覆盖</summary><pre id="fieldCounterexamples" class="raw-display"></pre></details><p id="fieldCounts"></p><p>原CPU逻辑EA合同不等完整微周期dummy观察，不给城市+1／+28..31命名unused／padding／reserved。其他1525项权威分类／合同及raw345=104操作数／13数据／228未证控制不变。</p><p class="section-links"><a href="fields-static/README.md">独立字段说明</a><a href="fields-static/verification.json">13998原CPU／29模型检查</a><a href="fields-static/all-indirect-accesses.json">全部1526账本</a><a href="fields-static/remaining-accesses.json">325保留项</a></p></section>
<section id="acceptance"><h2>十维验收：本轮变化与保留缺口</h2><div class="controls"><label for="acceptanceSelect">验收维度</label><select id="acceptanceSelect"></select></div><div id="acceptanceDetail"></div><p class="section-links"><a href="acceptance/requirements.json">完整十维</a><a href="acceptance/request-provenance.json">11项人类原quote及协调范围</a><a href="acceptance/verification.json">验收引用检查</a><a href="investigation-checklist.json">调查清单</a></p></section><footer>阶段1..30冻结。阶段31结束后等待评估，不自动32。最终只读审计和增量包见<a href="verification.json">verification.json</a>、<a href="package-receipt.json">package-receipt.json</a>，页面不预写其通过。</footer>
<script id="evidence-data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('evidence-data').textContent),el=id=>document.getElementById(id),pretty=v=>JSON.stringify(v,null,2),hex=(v,n=4)=>v==null?'—':Number(v).toString(16).toUpperCase().padStart(n,'0');let routeIndex=0,pointIndex=0,eventIndex=0,visibleEvents=[];
function option(s,v,l){const o=document.createElement('option');o.value=v;o.textContent=l;s.append(o)}function link(p,u,l){const a=document.createElement('a');a.href=u;a.textContent=l;p.append(a)}function row(t,l,v){const tr=document.createElement('tr');for(const x of[l,v]){const td=document.createElement('td');td.textContent=typeof x==='string'?x:JSON.stringify(x);tr.append(td)}t.append(tr)}
function field(obs=false){const r=d.routes[routeIndex],p=(obs?r.observer_points:r.points)[pointIndex];el(obs?'observerRawFieldValue':'rawFieldValue').textContent=pretty(p.fields[el(obs?'observerRawField':'rawField').value])}
function point(){const r=d.routes[routeIndex],p=r.points[pointIndex],q=r.observer_points[pointIndex],f=p.fields;el('checkpointSelect').value=pointIndex;el('originalImage').src=r.base+'original-control/'+p.image;el('observerImage').src=r.base+'observer/'+q.image;el('checkpointCaption').textContent=`${r.case} · actual local${p.frame} / parent${f.parent_route_frame}`;el('pointReason').textContent='展示选择理由：'+p.display_selection_reasons.join('；');el('pointValues').replaceChildren();for(const x of[['global7A / NMI78',`${f.global_007A} / ${f.NMI_0078}`],['battle0500/0501',f.battle_0500_0501],['active human disposition',f.active_human_disposition],['buttons81..86',f.buttons_0081_0086],['raw destination0540',f.raw_destination_0540],['7 ruler controllers',f.all7_ruler_controllers],['UI roster042C..043F',f.raw_UI_roster_042C_043F],['selected flags0580..0593',f.raw_selected_flags_0580_0593],['actual saved CPU',f.actual_saved_CPU_registers],['actual saved banks',f.actual_saved_PRG_banks]])row(el('pointValues'),...x);el('pointLinks').replaceChildren();for(const [variant,current]of[['original-control',p],['observer',q]]){el('pointLinks').append(variant+'：');for(const key of['state','RAM','SRAM']){link(el('pointLinks'),r.base+variant+'/'+current[key],key);el('pointLinks').append(' · ')}}for(const [id,current,obs]of[['rawField',p,false],['observerRawField',q,true]]){const previous=el(id).value;el(id).replaceChildren();Object.keys(current.fields).forEach(key=>option(el(id),key,key));if(Object.hasOwn(current.fields,previous))el(id).value=previous;field(obs)}el('allPointFields').textContent=pretty({original:p.fields,observer:q.fields});el('previousPoint').disabled=pointIndex===0;el('nextPoint').disabled=pointIndex===r.points.length-1}
function audio(){const a=d.routes[routeIndex].audio[Number(el('audioVariant').value)];el('nativeAudio').pause();el('nativeAudio').src=a.path;el('audioScope').textContent=`原48kHz stereo16bit WAV · ${a.sample_frames}sample pairs / ${a.duration_seconds.toFixed(3)}s · SHA256 ${a.sha256}`}
function event(){const e=visibleEvents[eventIndex];el('eventSelect').value=eventIndex;el('eventCurrent').replaceChildren();if(!e){el('eventScope').textContent='此路线无该类保存事件，不补造现场。';el('eventRaw').textContent='无此类事件';el('previousEvent').disabled=el('nextEvent').disabled=true;return}const tr=document.createElement('tr');for(const x of[`${e.sequence} / local${e.frame} / ${e.kind}`,`${e.physical_bank}:${hex(e.opcode_PC)} → ${hex(e.address)}`,`${e.RAM0500_0503.slice(0,2).join('/')} ; mode${e.postbattle_mode_6F91} ; SP${hex(e.SP,2)}`,`before${e.storage_byte_before_write??'—'} / ${e.value} / after${e.physical_storage_byte_after_event??e.captured_RAM_byte_after_write??'—'}`]){const td=document.createElement('td');td.textContent=x;tr.append(td)}el('eventCurrent').append(tr);el('eventScope').textContent=e.display_roles.join(' / ')+'；实际opcode／bus时点，不由帧末指针回推。';el('eventRaw').textContent=pretty(e);el('previousEvent').disabled=eventIndex===0;el('nextEvent').disabled=eventIndex===visibleEvents.length-1}
function filterEvents(){const r=d.routes[routeIndex],role=el('eventRole').value;visibleEvents=r.events.filter(e=>role==='all'||e.display_roles.includes(role));eventIndex=0;el('eventSelect').replaceChildren();visibleEvents.forEach((e,i)=>option(el('eventSelect'),i,`${e.sequence} / f${e.frame} / ${hex(e.opcode_PC)} / ${e.display_roles.join(', ')}`));event();el('eventLinks').replaceChildren();for(const [path,label]of[['observer/events.jsonl','全部原事件'],['observer/bus-events.bin','72-u32二进制'],['observer/snapshot-index.jsonl','原snapshot索引'],['observations.json','完整观察分层']]){link(el('eventLinks'),r.base+path,label);el('eventLinks').append(' · ')}}
function route(){routeIndex=Number(el('routeSelect').value);const r=d.routes[routeIndex];pointIndex=0;el('checkpointSelect').replaceChildren();r.points.forEach((p,i)=>option(el('checkpointSelect'),i,`actual local${p.frame} · ${p.label}`));el('routeScope').textContent=`本轮完整窗口${r.full_route_frames}帧，页面明确展示${r.displayed_point_count}点；natural=${r.natural_ordinary_input_route}，controlled ancestry=${r.controlled_ancestry}。`+(r.segmented_ancestry_scope?` 上游另有${r.segmented_ancestry_scope.upstream_original_core_segments}段／${r.segmented_ancestry_scope.upstream_original_core_single_run_frames}原核单跑帧，仅保全自然祖先链，不计入本窗口fresh复跑。`:'');el('selectionScope').textContent=d.display_policy;el('ancestry').textContent=pretty({ancestry:r.ancestry,segmented_ancestry_scope:r.segmented_ancestry_scope,input_plan:r.input_plan});el('callProtocol').textContent=pretty(r.observations);el('manifestLinks').replaceChildren();for(const variant of['original-control','observer'])for(const [path,label]of[['checkpoints.json','全部保存点'],['frame-services.json','全部帧／5buffer hashes'],['input-plan.json','完整普通输入计划']]){link(el('manifestLinks'),r.base+variant+'/'+path,variant+' '+label);el('manifestLinks').append(' · ')}point();filterEvents();audio()}
d.routes.forEach((r,i)=>option(el('routeSelect'),i,r.case));option(el('eventRole'),'all','全部展示关键事件');for(const role of Object.values(d.event_roles))option(el('eventRole'),role,role);el('routeSelect').onchange=route;el('checkpointSelect').onchange=()=>{pointIndex=Number(el('checkpointSelect').value);point()};el('previousPoint').onclick=()=>{if(pointIndex){pointIndex--;point()}};el('nextPoint').onclick=()=>{if(pointIndex+1<d.routes[routeIndex].points.length){pointIndex++;point()}};el('rawField').onchange=()=>field();el('observerRawField').onchange=()=>field(true);el('audioVariant').onchange=audio;el('eventRole').onchange=filterEvents;el('eventSelect').onchange=()=>{eventIndex=Number(el('eventSelect').value);event()};el('previousEvent').onclick=()=>{if(eventIndex){eventIndex--;event()}};el('nextEvent').onclick=()=>{if(eventIndex+1<visibleEvents.length){eventIndex++;event()}};route();
el('nativeCount').textContent=d.native.all_control_frames;el('displayCount').textContent=d.routes.reduce((n,r)=>n+r.displayed_point_count,0);el('sourceCount').textContent=d.source.original_CPU_parent_cases;el('nativeScope').textContent=`${d.native.routes}路线／${d.native.first_original_frames}首跑原帧／${d.native.all_control_frames}总控制帧，${d.native.fresh_process_runs}fresh；${d.native.nonempty_repeat_checks}非空repeat／${d.native.PNG_checks}PNG／${d.native.WAV_checks}WAV。全时长不等上方页面采样点；本轮数值写0，祖先范围按路线披露。`;row(el('caseCounts'),'复用冻结Source新对照',`${d.source.original_CPU_parent_cases}案 / ${pretty(d.source.counts)} / ${d.source.source_guard_count}guards；新生产模块0，非首次算法恢复`);row(el('caseCounts'),'独立字段原CPU合同',`${d.fields.original_contract_CPU_cases}=${d.fields.actual_caller_RTS_CPU_cases}RTS+${d.fields.explicit_prefix_CPU_cases}明确前缀，另${d.fields.model_guard_check_count}模型检查；Source0／Native0`);el('rosterContract').textContent=pretty(d.roster_contract);el('fieldCounterexamples').textContent=pretty(d.field_counterexamples);el('fieldCounts').textContent='全部1526访问：1201条件不交／80可能／245未知，剩325；本轮只BDB8一处条件迁移。';
function acceptance(){const x=d.acceptance.dimensions[Number(el('acceptanceSelect').value)],box=el('acceptanceDetail');box.replaceChildren();const h=document.createElement('h3');h.textContent=x.id+' · '+x.title;box.append(h);const s=document.createElement('p');s.id='dimensionStatus';s.className='evidence-note';s.textContent=x.acceptance_status_zh;box.append(s);const scope=document.createElement('p');scope.textContent=x.current_scope;box.append(scope);const delta=document.createElement('div');delta.id='phase31Change';delta.className='result-change';for(const key of['result','remaining_gap']){const p=document.createElement('p');p.textContent=(key==='result'?'本轮变化：':'保留缺口：')+x.phase31_change[key];delta.append(p)}box.append(delta);for(const [title,key]of[['已验结果及回执','verified_results'],['待验结果','pending_results'],['验收方法','acceptance_method']]){const h=document.createElement('h3');h.textContent=title;box.append(h);const ul=document.createElement('ul');ul.id=key;for(const value of x[key]||[]){const li=document.createElement('li');if(typeof value==='string')li.textContent=value;else{li.append(value.claim+' ');link(li,'../../'+value.evidence,value.evidence)}ul.append(li)}box.append(ul)}}d.acceptance.dimensions.forEach((x,i)=>option(el('acceptanceSelect'),i,x.id+' · '+x.title));el('acceptanceSelect').onchange=acceptance;acceptance();
</script></body></html>'''


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.pre = [], [], {}
        self.active = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'pre' and attrs.get('id', '').startswith('source-code-'):
            self.active = attrs['id']
            self.pre[self.active] = ''

    def handle_data(self, text):
        if self.active:
            self.pre[self.active] += text

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.active = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    data = inputs()
    style = re.search(r'<style>(.*?)</style>', (BASE / 'index.html').read_text(), re.S)[1]
    sources = []
    for index, source in enumerate(data['sources'], 1):
        sources.append('<details class="source"><summary>' + html.escape(source['name']) +
                       '</summary><p><a href="' + source['path'] + '">完整UTF-8源码</a> · SHA256 <code>' +
                       source['sha256'] + '</code></p><pre id="source-code-' + str(index) + '">' +
                       html.escape(source['text']) + '</pre></details>')
    value = {key: item for key, item in data.items() if key != 'sources'}
    payload = json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    assert json.loads(payload) == value
    page = TEMPLATE.replace('__STYLE__', style).replace('__SOURCES__', '\n'.join(sources)).replace('__DATA__', payload)
    inspect = Inspect()
    inspect.feed(page)
    assert len(inspect.ids) == len(set(inspect.ids))
    for index, source in enumerate(data['sources'], 1):
        assert inspect.pre['source-code-' + str(index)] == source['text']
    optional = ('verification.json', 'package-receipt.json')
    missing = [link for link in inspect.links if not link.startswith(('#', 'http:', 'https:'))
               and link not in optional and not (OUT / link.split('#')[0]).exists()]
    assert not missing, missing
    node = shutil.which('node')
    assert node
    result = subprocess.run([node, '--check'], input=re.findall(r'<script>(.*?)</script>', page, re.S)[0],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    if not args.check_only:
        (OUT / 'index.html').write_text(page)
    print(json.dumps(dict(status='static_checks_passed' if args.check_only else 'built_static_checks_passed',
        HTML_created=not args.check_only, HTML_sha256=hashlib.sha256(page.encode()).hexdigest(),
        HTML_bytes=len(page.encode()), payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
        builder_sha256=sha(Path(__file__)), source_UTF8_exact=True, source_modules=3,
        unique_DOM_ids=len(inspect.ids), local_links=len(inspect.links), missing_links=missing,
        JS_syntax_passed=True, native_routes=len(data['routes']),
        full_route_first_frames=sum(route['full_route_frames'] for route in data['routes']),
        displayed_checkpoint_count=sum(len(route['points']) for route in data['routes']),
        public_fields_per_core=49, field_select_options=98,
        displayed_events=sum(len(route['events']) for route in data['routes']),
        acceptance_dimensions=10, source_CPU_cases=0, Native_runs=0)))


if __name__ == '__main__':
    main()
