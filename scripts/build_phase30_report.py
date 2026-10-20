#!/usr/bin/env python3
"""Build the final phase30 evidence page; never run CPU/core or old producers."""
from pathlib import Path
from html.parser import HTMLParser
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase30'
BASE = ROOT / 'analysis/phase29'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pins(document):
    for key in ('source_sha256', 'source_and_validator_sha256', 'artifact_sha256',
                'artifact_and_dependency_sha256', 'input_sha256'):
        values = document.get(key, {})
        if isinstance(values, dict):
            for path, value in values.items():
                if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
                    assert (ROOT / path).is_file() and sha(ROOT / path) == value, (key, path)


def event_objects(value):
    """Only full, original decoded event objects; wrappers remain linked separately."""
    if isinstance(value, dict):
        if all(key in value for key in ('sequence', 'opcode_PC', 'actual_PRG_banks', 'kind')):
            yield value
        else:
            for item in value.values():
                yield from event_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from event_objects(item)


def inputs():
    native = read(OUT / 'runtime/evidence.json')
    nv = read(OUT / 'runtime/validation.json')
    observations = read(OUT / 'runtime/early-lifecycle-observations.json')
    source = read(OUT / 'early-services/validation.json')
    integration = read(OUT / 'source-integration.json')
    context = read(OUT / 'context/verification.json')
    fields = read(OUT / 'fields-static/verification.json')
    ledger = read(OUT / 'fields-static/analysis-summary.json')
    acceptance = read(OUT / 'acceptance/requirements.json')
    av = read(OUT / 'acceptance/verification.json')
    for document in (native, nv, source, integration, context, fields, av):
        assert document['status'] == 'passed'
        pins(document)
    assert nv['evidence_sha256'] == sha(OUT / 'runtime/evidence.json')
    assert native['script_sha256'] == sha(ROOT / 'scripts/capture_native_postbattle_early.py')
    assert source['quick'] is False
    assert source['controlled_cases'] == 1506
    assert source['passive_software_caller_cases'] == 40
    assert source['original_CPU_parent_cases'] == 1546
    assert source['counts'] == {'actual_caller_RTS': 1540, 'strict_dependency_prefix': 6}
    assert source['original_CPU_parent_cases'] == source['controlled_cases'] + source['passive_software_caller_cases']
    assert sum(source['counts'].values()) == source['original_CPU_parent_cases']
    assert source['source_guard_count'] == 11
    assert integration['inherited_regression_cases'] == 115
    assert integration['new_controlled_AI_stage0_cases'] == 2
    assert integration['new_early_caller_cases'] == 14
    assert integration['comparison_counts'] == {'actual_caller_RTS': 130, 'actual_nonlocal_return': 1}
    assert integration['new_early_targets'] == {'40966': 4, '47795': 4, '47809': 2, '47933': 2, '48198': 2}
    assert integration['new_early_ancestries'] == {'natural_ancestry': 7, 'controlled_ancestry': 7}
    assert integration['original_CPU_parent_cases'] == 117 + integration['new_early_caller_cases']
    assert sum(integration['comparison_counts'].values()) == integration['original_CPU_parent_cases']
    assert integration['guard_count'] == 4
    assert source['source_original_CPU_callbacks'] == integration['source_original_CPU_callbacks'] == 0
    assert source['production_IR_interpretation'] is integration['production_IR_interpretation'] is False
    assert context['check_count'] == 41
    assert fields['original_contract_CPU_cases'] == 7188 and fields['source_CPU_cases'] == 0
    assert fields['actual_caller_RTS_CPU_cases'] == 7172 and fields['explicit_prefix_CPU_cases'] == 16
    assert fields['model_guard_check_count'] == 21 and fields['newly_proved_disjoint_all_count'] == 2
    assert fields['all_indirect_classification_counts'] == {
        'proved_disjoint_auxiliary_address_domain': 1200,
        'possible_city_auxiliary_alias': 81,
        'unresolved_pointer_or_index_contract': 245,
    }
    assert fields['remaining_access_count'] == 326
    for key, value in dict(routes=3, original_first_frames=48, all_control_frames=192,
                           fresh_process_runs=12, original_checkpoints=48,
                           nonempty_artifact_repeat_checks=879, PNG_checks=96,
                           WAV_checks=6, observer_events=179547,
                           full_software_snapshots=138, early_public_software_inputs=14,
                           actual_BB8C_calls=2, actual_BB36_calls=0,
                           actual_BC46_mode0_calls=1, actual_BC46_mode1_calls=1,
                           actual_BC46_mode2_calls=0, changed_early_city_roster_bytes=4,
                           ECEE_immediate_returns=2, phase3_fresh_hold_callbacks=23,
                           phase3_completion_callbacks=1, additional_core_memory_writes=0).items():
        assert nv[key] == value and native['summary'][key] == value, key
    assert all(nv[key] for key in ('all_five_complete_buffers_equal_each_frame',
                                  'all_complete_initial_API_buffers_equal',
                                  'all_artifacts_repeat_exact',
                                  'full_serialized_buffers_not_normalized'))
    assert acceptance['scaffold_status'] == 'final_evidence_reviewed'
    assert len(acceptance['dimensions']) == 10
    assert all('PENDING' not in json.dumps(row['phase30_change']) for row in acceptance['dimensions'])
    route_specs = [
        ('natural-stage0-human', '自然阶段0：交给原人类处置UI',
         '自然母状态独立续行8帧；本轮与已证祖先数值准备0。进入原human13，并没有在这8帧内连续执行后续人类UI。'),
        ('natural-stage1-mode0', '自然阶段1：BB8C → BC46 mode0',
         '自然母状态独立续行32帧；本轮与已证祖先准备0。原BB8C调用mode0，四个名单槽FF→8、191、51、167；这不是在野录用。'),
        ('controlled-stage0-human', '受控祖先分窗：原BB8C mode1',
         '受控祖先续行8帧；继承19字节已知准备，更早legacy范围未完全建立，本轮新增写0。窗口实际包括BB8C mode1，不因路线名推断执行了BB36。'),
    ]
    routes = []
    for case, title, scope in route_specs:
        folder = OUT / 'runtime' / case
        original = read(folder / 'original-control/checkpoints.json')
        observer = read(folder / 'observer/checkpoints.json')
        lifecycle = next(row for row in observations['routes'] if row['case'] == case)
        assert len(original) == len(observer)
        for a, b in zip(original, observer):
            assert a['frame'] == b['frame'] and a['fields'] == b['fields']
            assert len(a['fields']) == len(b['fields']) == 35
            for variant, point in (('original-control', a), ('observer', b)):
                for key in ('image', 'state', 'RAM', 'SRAM'):
                    assert (folder / variant / point[key]).is_file()
            assert sha(folder / 'original-control' / a['image']) == sha(folder / 'observer' / b['image'])
        selected = {}
        roles = {
            'early_original_entries': 'early_stage_entry',
            'public_early_software_inputs': 'actual_software_input',
            'actual_BC46_calls': 'actual_BC46_JSR_and_entry',
            'mode_targets': 'original_mode_dispatch',
            'controller_byte_reads': 'actual_controller_read',
            'original_mode_writes': 'original_mode_write',
            'early_SRAM_writes': 'early_SRAM_store',
            'early_city_roster_writes': 'early_city_roster_store',
            'phase2_ECEE_immediate_returns': 'ECEE_immediate_request_RTS',
            'phase3_fresh_hold_callbacks': 'fresh_stage3_hold',
            'phase3_completion_callbacks': 'fresh_stage3_completion',
        }
        for key, role in roles.items():
            for event in event_objects(lifecycle[key]):
                sequence = event['sequence']
                if sequence not in selected:
                    selected[sequence] = dict(event, display_roles=[])
                else:
                    assert {k: v for k, v in selected[sequence].items() if k != 'display_roles'} == event
                if role not in selected[sequence]['display_roles']:
                    selected[sequence]['display_roles'].append(role)
        # Every displayed event is checked against the complete formal raw decode.
        found = set()
        with (folder / 'observer/events.jsonl').open() as handle:
            for line in handle:
                event = json.loads(line)
                if event['sequence'] in selected:
                    assert {k: v for k, v in selected[event['sequence']].items() if k != 'display_roles'} == event
                    found.add(event['sequence'])
        assert found == set(selected)
        audio = []
        for variant in ('original-control', 'observer'):
            path = folder / variant / 'full-audio.wav'
            with wave.open(str(path), 'rb') as handle:
                assert (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) == (2, 2, 48000)
                meta = dict(sample_frames=handle.getnframes(), duration_seconds=handle.getnframes() / 48000)
            audio.append(dict(path=str(path.relative_to(OUT)), sha256=sha(path), **meta))
        # Full event dictionaries are embedded once; this compact index retains
        # original wrapper contracts and sequence references without duplication.
        def compact(value):
            if isinstance(value, dict):
                if all(k in value for k in ('sequence', 'opcode_PC', 'actual_PRG_banks', 'kind')):
                    return dict(sequence=value['sequence'], frame=value['frame'], opcode_PC=value['opcode_PC'])
                return {k: compact(v) for k, v in value.items()}
            if isinstance(value, list):
                return [compact(v) for v in value]
            return value
        routes.append(dict(case=case, title=title, scope=scope, base='runtime/' + case + '/',
                           points=original, observer_points=observer, audio=audio,
                           events=sorted(selected.values(), key=lambda event: event['sequence']),
                           lifecycle=compact(lifecycle), ancestry=native['case_ancestry'][case]))
    assert [len(route['points']) for route in routes] == [8, 32, 8]
    sources = []
    for name in ('postbattle_early_services.py', 'postbattle_early_integration.py'):
        path = ROOT / 'source/recovered' / name
        sources.append(dict(name=name, path='../../source/recovered/' + name,
                            text=path.read_text(), sha256=sha(path)))
    source_summary = {key: source[key] for key in (
        'original_CPU_parent_cases', 'controlled_cases', 'passive_software_caller_cases',
        'counts', 'source_guard_count')}
    root_summary = {key: integration[key] for key in (
        'original_CPU_parent_cases', 'inherited_regression_cases', 'new_controlled_AI_stage0_cases',
        'new_early_caller_cases', 'new_early_targets', 'new_early_ancestries', 'comparison_counts', 'guard_count')}
    field_summary = {key: fields[key] for key in (
        'original_contract_CPU_cases', 'counts', 'actual_caller_RTS_CPU_cases', 'explicit_prefix_CPU_cases',
        'model_guard_check_count', 'remaining_access_count', 'all_indirect_classification_counts',
        'newly_proved_disjoint_all_count')}
    return dict(native=native['summary'], routes=routes, source=source_summary, integration=root_summary,
                fields=field_summary, ledger=ledger,
                selected_field_contracts=read(OUT / 'fields-static/selected-accesses.json'),
                name_lifecycle=read(OUT / 'fields-static/name-pointer-lifecycle-contract.json'),
                branches=read(OUT / 'context/early-stage-branches-and-callers.json'),
                boundaries=read(OUT / 'context/ruler-and-name-pointer-boundaries.json'),
                credit=read(OUT / 'context/historical-credit-and-return-erratum.json'),
                context_checks=context['check_count'], sources=sources, acceptance=acceptance)


TEMPLATE = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>阶段30 · 战后前两态与姓名指针合同</title><style>__STYLE__
.native-grid>*{min-width:0}.native-data table{table-layout:fixed;width:100%}.native-data td,.native-data th{overflow-wrap:anywhere;word-break:break-word}.source pre{max-height:620px}.raw-display{max-height:420px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}.result-change{padding:12px 16px;border-left:3px solid #287254;background:#e4eddf}.chain{font:15px/1.8 ui-monospace,monospace;overflow-wrap:anywhere}.controls{flex-wrap:wrap}.scope-table{table-layout:fixed;width:100%}.scope-table td,.scope-table th{overflow-wrap:anywhere}.source summary{overflow-wrap:anywhere}
</style></head><body><header><nav><a href="../phase29/index.html">阶段29</a><a href="README.md">本轮说明</a><a href="#native">三段原机分窗</a><a href="#events">即时调用与写入</a><a href="#context">父链与边界</a><a href="#source">完整源码</a><a href="#fields">两项条件合同</a><a href="#acceptance">十维验收</a></nav><h1>战后前两态：人类交接、AI名单与真实返回</h1><p class="lede">补齐A006四态服务中的阶段0／1精确协议，保留原人类13／14状态交接。独立验证完整CC29姓名ROM指针，仅在声明入口域内排除两项城市辅助别名；不把裸指针、raw硬件或整款闭包一并算作完成。</p></header><div class="numbers"><span><strong id="nativeCount"></strong>两核心fresh复跑控制帧</span><span><strong id="sourceCount"></strong>Source原CPU对照案</span><span><strong>2</strong>本轮条件排除</span><span><strong>326</strong>仍保留候选</span></div><p class="warning">城市+1／+28..31正式含义、未知服务总数仍为null，整款闭包仍为false。两个自然窗口之间1519帧的人类UI没有在本轮连续重跑。旧BC46玩法不是首次恢复；阶段30结束后等待评估，不自动开始阶段31。</p>
<section id="native"><h2>三段实际分窗：同帧原图与35个原字段</h2><div class="controls"><label for="routeSelect">正式路线</label><select id="routeSelect"></select><label for="checkpointSelect">实际原帧</label><select id="checkpointSelect"></select><button id="previousPoint">前一帧</button><button id="nextPoint">后一帧</button></div><p id="routeScope" class="evidence-note"></p><div class="native-grid"><div class="screens"><figure><img id="originalImage" alt="固定原核心256×240画面"><figcaption>固定原核心 · 原始256×240</figcaption></figure><figure><img id="observerImage" alt="独立观察核心同帧原画面"><figcaption>独立观察核心 · 同帧原始256×240</figcaption></figure></div><div class="native-data"><p id="checkpointCaption"></p><table><thead><tr><th>字段／实际时点</th><th>原保存值</th></tr></thead><tbody id="pointValues"></tbody></table><p id="pointHashes" class="small"></p></div></div><p id="pointLinks"></p><div class="controls"><label for="rawField">原核心35字段</label><select id="rawField"></select><label for="observerRawField">观察核心35字段</label><select id="observerRawField"></select></div><details><summary>所选原核心字段</summary><pre id="rawFieldValue" class="raw-display"></pre></details><details><summary>所选观察核心字段</summary><pre id="observerRawFieldValue" class="raw-display"></pre></details><details><summary>本帧两核心全部字段</summary><pre id="allPointFields" class="raw-display"></pre></details><details><summary>母状态、继承准备与分窗范围</summary><pre id="ancestry" class="raw-display"></pre></details><div class="controls"><label for="audioVariant">本路线完整原WAV</label><select id="audioVariant"><option value="0">固定原核心</option><option value="1">独立观察核心</option></select></div><audio id="nativeAudio" controls preload="metadata"></audio><p id="audioScope" class="small"></p><p id="nativeScope"></p><p class="scope">五缓冲一致指这次新窗口内部两核心与fresh复跑，不声称和冻结29相同历史绝对帧的RAM／PCM／state逐字重现；母档导入后的调用日程不同，记录没有做归一化。</p><p class="section-links"><a href="runtime/README.md">原机范围</a><a href="runtime/evidence.json">正式清单</a><a href="runtime/validation.json">12次fresh回执</a><a href="runtime/core-provenance/build.json">观察核心来源</a></p></section>
<section id="events"><h2>真实BB8C调用、名单写入及后续fade回调</h2><p>Native看到BB8C→BC46→BB8F的mode0／1；自然mode0实际把城名单四槽FF改为8、191、51、167。BB36→BC46→BB39与mode2另有受控OriginalCPU对照，没有在这三段原机分窗中出现。collector21次写与城名单4次写分开，不把名单重分配说成在野录用。</p><div class="controls"><label for="eventRole">实际事件层</label><select id="eventRole"><option value="all">全部关键事件</option><option value="early_stage_entry">阶段0／1入口</option><option value="actual_software_input">实际NEW5软件输入</option><option value="actual_BC46_JSR_and_entry">BB8C真实JSR与BC46入口</option><option value="actual_controller_read">君主controller读取</option><option value="original_mode_write">原mode写入</option><option value="original_mode_dispatch">原mode分派目标</option><option value="early_city_roster_store">城市名单四次写入</option><option value="early_SRAM_store">名单与collector SRAM写入</option><option value="ECEE_immediate_request_RTS">ECEE即时请求与RTS</option><option value="fresh_stage3_hold">后续新阶段3保持</option><option value="fresh_stage3_completion">后续新阶段3完成</option></select><label for="eventSelect">原记录</label><select id="eventSelect"></select><button id="previousEvent">前一事件</button><button id="nextEvent">后一事件</button></div><p id="eventScope"></p><div class="horizontal"><table class="scope-table"><thead><tr><th>序号／帧／事件</th><th>原PC／地址</th><th>phase／mode／SP</th><th>原值／物理字节</th></tr></thead><tbody id="eventCurrent"></tbody></table></div><details><summary>完整原观察事件与显示分层</summary><pre id="eventRaw" class="raw-display"></pre></details><details><summary>本路线调用／返回／写入索引（序号链接原事件）</summary><pre id="lifecycle" class="raw-display"></pre></details><p id="eventLinks"></p><p class="scope">固定原核心没有内部CPUtrace；独立观察核心保存选定opcode／bus事件与完整软件快照，快照不等于即时N163／PPU／APU。逻辑有效地址与dummy总线读取分开。ECEE当帧返回，23次hold是后续新BBA0回调；一次fade完成不把所有输入的完成时间固定为21帧。</p><p class="section-links"><a href="runtime/early-lifecycle-observations.json">全部早期生命周期记录</a></p></section>
<section id="context"><h2>父链、栈返回与raw边界</h2><p class="chain">13:D4F0 JSR CC29 → D4F3 LDY28 → D4F5 EE07/A006 → 8:BAB3 → BAC1／BB3D →（AI）BC46 → 真实caller返回 → INC0501；human分支保留原13／14交接</p><p>阶段0真实call为BB36、压入BB38、返回BB39；阶段1为BB8C、压入BB8E、返回BB8F。旧高层标记BB37／BB8D在新文档中更正，冻结旧文件不改。只有实际正常返回才能推进，未解决dependency、非局部转移或重启不能算作普通RTS。</p><details><summary>阶段0／1完整条件与实际返回点</summary><pre id="branchContext" class="raw-display"></pre></details><details><summary>F368正常七君主与raw7..15／硬件边界</summary><pre id="boundaryContext" class="raw-display"></pre></details><details><summary>旧玩法512案、旧父256 bypass与本轮credit</summary><pre id="creditContext" class="raw-display"></pre></details><p>正常ruler0..6与raw索引7..15分列；raw8命中5F20必须有真实硬件读输入。EE07恢复代码pair但保留数据页副作用；服务缺失保持原call／owner／generator，不伪造ready或返回。</p><p class="section-links"><a href="context/README.md">只读context说明</a><a href="context/verification.json">41静态检查／0CPU／0Native</a><a href="context/original-ranges.asm">原字节与+16B文件偏移</a></p></section>
<section id="source"><h2>四态服务与统一前门：两份完整可读源码</h2><p>本轮410原位置／912codeB与6B分派表是精确协议恢复；BC46玩法已经有冻结具名源码，不计首次还原。阶段2／3继承既有精确服务。正常域和显式硬件夹具按回执验收；人类13／14交接维持原行为，服务四态闭合不等于整款闭包。</p><table class="scope-table"><thead><tr><th>独立证据域</th><th>计数与范围</th></tr></thead><tbody id="caseCounts"></tbody></table><p>子域受控案、复用29的26份软件输入与新30实际输入分列。Root另有115继承回归及2个BB36受控前门案；同一软件输入不能跨层相加成独立现场。Source生产不执行原CPU或控制IR，原模拟器音画另记；这些Python文件不是原作者工程或可编译同一NES的完整项目。</p><p class="section-links"><a href="early-services/validation.json">EarlyServices最终矩阵</a><a href="early-services/README.md">Source边界</a><a href="source-integration.json">Root完整前门对照</a></p>__SOURCES__</section>
<section id="fields"><h2>完整CC29姓名指针：两处有条件不交</h2><p>完整入口实际执行F25F31选择bank17，正常ruler0..6读取原首将rawbyte，再按rawID0..255完整计算8DB4+13×ID。CC92与CCAC在Y=0读取ROM8DB4..9AB3；没有把超出237个正式姓名记录的rawID截断。完整构造、逐包重设、写域与进位合同支持两处条件不交。</p><p>裸CCAA指针6001／601C／601F反例仍保留；裸CC6D、rawruler7..15、带IRQ或decimal输入不纳入同一合同。逻辑地址证明不代表每个微周期总线地址；这两处Y=0读取本身没有额外跨页dummy。7188案是独立OriginalCPU合同，Source病例0、Native帧0。</p><details><summary>两项原访问与权威地址合同</summary><pre id="selectedFields" class="raw-display"></pre></details><details><summary>完整生命周期、因子化依据与排除前提</summary><pre id="nameContract" class="raw-display"></pre></details><p id="fieldCounts"></p><p>城市+1／+28..31正式含义仍为null；两项条件排除不是padding、reserved或unused证明。其余1524项及raw345原账本不变：104操作数、13已知数据、228未证入口。</p><p class="section-links"><a href="fields-static/README.md">独立合同说明</a><a href="fields-static/verification.json">7188原CPU／21模型检查</a><a href="fields-static/all-indirect-accesses.json">全部1526项</a><a href="fields-static/remaining-accesses.json">326保留项</a><a href="fields-static/logical-vs-dummy-bus-contracts.json">逻辑与dummy边界</a></p></section>
<section id="acceptance"><h2>十维验收：本轮变化、已验与未决</h2><div class="controls"><label for="acceptanceSelect">验收维度</label><select id="acceptanceSelect"></select></div><div id="acceptanceDetail"></div><p class="section-links"><a href="acceptance/README.md">要求与来源</a><a href="acceptance/requirements.json">最终十维数据</a><a href="acceptance/verification.json">跨回执检查</a><a href="investigation-checklist.json">调查清单</a></p></section><footer>阶段1..29冻结。阶段30仅在声明范围内新增早期协议与姓名指针合同；结束后等待评估，不自动开始31。最终总审计与增量归档见 <a href="verification.json">verification.json</a>、<a href="package-receipt.json">package-receipt.json</a>，页面不预先宣布通过。</footer>
<script id="evidence-data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('evidence-data').textContent),el=id=>document.getElementById(id),pretty=v=>JSON.stringify(v,null,2),hex=(v,n=4)=>v==null?'—':Number(v).toString(16).toUpperCase().padStart(n,'0');let routeIndex=1,pointIndex=0,eventIndex=0,visibleEvents=[];
function option(s,v,l){const o=document.createElement('option');o.value=v;o.textContent=l;s.append(o)}function link(p,u,l){const a=document.createElement('a');a.href=u;a.textContent=l;p.append(a)}function row(t,l,v){const tr=document.createElement('tr');for(const x of[l,v]){const td=document.createElement('td');td.textContent=typeof x==='string'?x:JSON.stringify(x);tr.append(td)}t.append(tr)}
function field(observer=false){const r=d.routes[routeIndex],p=(observer?r.observer_points:r.points)[pointIndex];el(observer?'observerRawFieldValue':'rawFieldValue').textContent=pretty(p.fields[el(observer?'observerRawField':'rawField').value])}
function point(){const r=d.routes[routeIndex],p=r.points[pointIndex],q=r.observer_points[pointIndex],f=p.fields;el('checkpointSelect').value=pointIndex;el('originalImage').src=r.base+'original-control/'+p.image;el('observerImage').src=r.base+'observer/'+q.image;el('checkpointCaption').textContent=`${r.title} · local${p.frame} / parent${f.parent_route_frame}`;el('pointValues').replaceChildren();for(const x of[['global7A / NMI78',`${f.global_007A} / ${f.NMI_0078}`],['battle0500/0501',f.battle_0500_0501],['side0504 / mode6F91 / 050B',`${f.early_side_0504} / ${f.early_mode_6F91} / ${f.early_050B}`],['outcome0514 / turn0506',`${f.outcome_0514} / ${f.turn_0506}`],['工作名单6FA1..6FB4',f.early_working_officers_6FA1_6FB4],['本城完整raw32',f.active_city_raw32],['原保存CPU寄存器',f.actual_saved_CPU_registers],['帧末实际PRG页',f.actual_saved_PRG_banks],['fade87..8A',f.fade_0087_008A],['PPU jobs7D..80',f.ppu_flags_007D_0080],['影子字节DE..E5',f.shadow_bank_bytes_00DE_00E5]])row(el('pointValues'),...x);el('pointLinks').replaceChildren();for(const [v,c]of[['original-control',p],['observer',q]]){el('pointLinks').append(v+'：');for(const k of['state','RAM','SRAM']){link(el('pointLinks'),r.base+v+'/'+c[k],k);el('pointLinks').append(' · ')}}el('pointHashes').textContent=`完整state${f.whole_serialized_state_bytes}B；本帧PCM${f.PCM_bytes}B，累计${f.PCM_stop_byte}B。全部公开字段两核心逐值相等。`;for(const [id,c,isObserver]of[['rawField',p,false],['observerRawField',q,true]]){const old=el(id).value;el(id).replaceChildren();Object.keys(c.fields).forEach(k=>option(el(id),k,k));if(Object.hasOwn(c.fields,old))el(id).value=old;field(isObserver)}el('allPointFields').textContent=pretty({original:p.fields,observer:q.fields});el('previousPoint').disabled=pointIndex===0;el('nextPoint').disabled=pointIndex===r.points.length-1}
function audio(){const a=d.routes[routeIndex].audio[Number(el('audioVariant').value)];el('nativeAudio').pause();el('nativeAudio').src=a.path;el('audioScope').textContent=`原48kHz stereo16bit WAV · ${a.sample_frames} sample pairs / ${a.duration_seconds.toFixed(3)}秒 · SHA256 ${a.sha256}`}
function event(){const e=visibleEvents[eventIndex];el('eventSelect').value=eventIndex;el('eventCurrent').replaceChildren();if(!e){el('eventScope').textContent='此路线没有该类保存事件，不补造轨迹。';el('eventRaw').textContent='无此类事件';el('previousEvent').disabled=el('nextEvent').disabled=true;return}const tr=document.createElement('tr');for(const x of[`${e.sequence} / local${e.frame} / ${e.kind}`,`${e.physical_bank}:${hex(e.opcode_PC)} → ${hex(e.address)}`,`${e.RAM0500_0503.slice(0,2).join('/')} ; mode${e.postbattle_mode_6F91} ; SP${hex(e.SP,2)}`,`before${e.storage_byte_before_write??'—'} / value${e.value} / after${e.physical_storage_byte_after_event??e.captured_RAM_byte_after_write??'—'}`]){const td=document.createElement('td');td.textContent=x;tr.append(td)}el('eventCurrent').append(tr);el('eventScope').textContent=e.display_roles.join(' / ')+'；原opcode／bus记录，frame-end指针不可替代此时点。';el('eventRaw').textContent=pretty(e);el('previousEvent').disabled=eventIndex===0;el('nextEvent').disabled=eventIndex===visibleEvents.length-1}
function filterEvents(){const r=d.routes[routeIndex],role=el('eventRole').value;visibleEvents=r.events.filter(e=>role==='all'||e.display_roles.includes(role));eventIndex=0;el('eventSelect').replaceChildren();visibleEvents.forEach((e,i)=>option(el('eventSelect'),i,`${e.sequence} / local${e.frame} / ${hex(e.opcode_PC)} / ${e.display_roles.join(', ')}`));event();el('eventLinks').replaceChildren();for(const [path,label]of[['observer/events.jsonl','全部原解码事件'],['observer/bus-events.bin','原被动观察ABI'],['observer/snapshot-index.jsonl','完整软件快照索引']]){link(el('eventLinks'),r.base+path,label);el('eventLinks').append(' · ')}}
function route(){routeIndex=Number(el('routeSelect').value);const r=d.routes[routeIndex];pointIndex=0;el('checkpointSelect').replaceChildren();r.points.forEach((p,i)=>option(el('checkpointSelect'),i,`local${p.frame} · ${p.label}`));el('routeScope').textContent=r.scope;el('ancestry').textContent=pretty(r.ancestry);el('lifecycle').textContent=pretty(r.lifecycle);point();filterEvents();audio()}
d.routes.forEach((r,i)=>option(el('routeSelect'),i,r.title));el('routeSelect').value=routeIndex;el('routeSelect').onchange=route;el('checkpointSelect').onchange=()=>{pointIndex=Number(el('checkpointSelect').value);point()};el('previousPoint').onclick=()=>{if(pointIndex){pointIndex--;point()}};el('nextPoint').onclick=()=>{if(pointIndex+1<d.routes[routeIndex].points.length){pointIndex++;point()}};el('rawField').onchange=()=>field();el('observerRawField').onchange=()=>field(true);el('audioVariant').onchange=audio;el('eventRole').onchange=filterEvents;el('eventSelect').onchange=()=>{eventIndex=Number(el('eventSelect').value);event()};el('previousEvent').onclick=()=>{if(eventIndex){eventIndex--;event()}};el('nextEvent').onclick=()=>{if(eventIndex+1<visibleEvents.length){eventIndex++;event()}};route();
el('nativeCount').textContent=d.native.all_control_frames;el('sourceCount').textContent=d.source.original_CPU_parent_cases+d.integration.original_CPU_parent_cases;el('nativeScope').textContent=`三分窗${d.native.original_first_frames}首跑帧／${d.native.all_control_frames}控制帧，${d.native.fresh_process_runs}fresh；${d.native.nonempty_artifact_repeat_checks}非空复跑检查／${d.native.PNG_checks}PNG／${d.native.WAV_checks}WAV；${d.native.observer_events}原事件／${d.native.full_software_snapshots}软件snapshot。本轮新增写0，12imports／0新cold；祖先自然／受控分别披露。`;el('branchContext').textContent=pretty(d.branches);el('boundaryContext').textContent=pretty(d.boundaries);el('creditContext').textContent=pretty(d.credit);el('selectedFields').textContent=pretty(d.selected_field_contracts);el('nameContract').textContent=pretty(d.name_lifecycle);el('fieldCounts').textContent=`全1526访问：1200条件不交／81可能／245未知，余326；本轮只变更2项。独立原CPU合同${d.fields.original_contract_CPU_cases}=${d.fields.actual_caller_RTS_CPU_cases}RTS+${d.fields.explicit_prefix_CPU_cases}显式前缀，另${d.fields.model_guard_check_count}模型／前提检查。`;row(el('caseCounts'),'新EarlyServices',`${d.source.original_CPU_parent_cases}案 / ${pretty(d.source.counts)} / ${d.source.source_guard_count}guards；受控${d.source.controlled_cases}，软件输入${d.source.passive_software_caller_cases}（含旧29的26份）`);row(el('caseCounts'),'Root统一前门',`${d.integration.original_CPU_parent_cases}案 / ${pretty(d.integration.comparison_counts)} / ${d.integration.guard_count}guards；115继承+2新受控+${d.integration.new_early_caller_cases}新30输入`);row(el('caseCounts'),'独立指针合同',`${d.fields.original_contract_CPU_cases}原CPU / ${d.fields.model_guard_check_count}模型检查；Source0／Native0，4份旧D4F0输入只到D4F3前缀`);row(el('caseCounts'),'只读context',`${d.context_checks}checks；Source CPU Native均0，不重复计旧玩法512或旧父256`);
function acceptance(){const x=d.acceptance.dimensions[Number(el('acceptanceSelect').value)],box=el('acceptanceDetail');box.replaceChildren();const h=document.createElement('h3');h.textContent=x.id+' · '+x.title;box.append(h);const s=document.createElement('p');s.id='dimensionStatus';s.className='evidence-note';s.textContent=x.acceptance_status_zh||x.acceptance_status;box.append(s);const p=document.createElement('p');p.textContent=x.current_scope;box.append(p);const delta=document.createElement('div');delta.className='result-change';delta.id='phase30Change';for(const k of['result','remaining_gap']){const p=document.createElement('p');p.textContent=(k==='result'?'本轮变化：':'仍待验：')+x.phase30_change[k];delta.append(p)}box.append(delta);for(const [title,key]of[['已验结果及回执','verified_results'],['待验结果','pending_results'],['验收方法','acceptance_method']]){const h=document.createElement('h3');h.textContent=title;box.append(h);const ul=document.createElement('ul');ul.id=key;for(const v of x[key]||[]){const li=document.createElement('li');if(typeof v==='string')li.textContent=v;else{li.append(v.claim+' ');link(li,'../../'+v.evidence,v.evidence)}ul.append(li)}box.append(ul)}}d.acceptance.dimensions.forEach((x,i)=>option(el('acceptanceSelect'),i,x.id+' · '+x.title));el('acceptanceSelect').onchange=acceptance;acceptance();
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
    payload = json.dumps({key: value for key, value in data.items() if key != 'sources'},
                         ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    assert json.loads(payload) == {key: value for key, value in data.items() if key != 'sources'}
    page = TEMPLATE.replace('__STYLE__', style).replace('__SOURCES__', '\n'.join(sources)).replace('__DATA__', payload)
    inspect = Inspect()
    inspect.feed(page)
    assert len(inspect.ids) == len(set(inspect.ids))
    for index, source in enumerate(data['sources'], 1):
        assert inspect.pre['source-code-' + str(index)] == source['text']
    optional = ('verification.json', 'package-receipt.json')
    missing = [url for url in inspect.links if not url.startswith(('#', 'http:', 'https:'))
               and url not in optional and not (OUT / url.split('#')[0]).exists()]
    assert not missing, missing
    node = shutil.which('node')
    assert node
    result = subprocess.run([node, '--check'], input=re.findall(r'<script>(.*?)</script>', page, re.S)[0],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    if not args.check_only:
        (OUT / 'index.html').write_text(page)
    print(json.dumps(dict(status='static_checks_passed' if args.check_only else 'built_static_checks_passed',
                          HTML_created=not args.check_only,
                          HTML_sha256=hashlib.sha256(page.encode()).hexdigest(), HTML_bytes=len(page.encode()),
                          payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                          builder_sha256=sha(Path(__file__)), source_UTF8_exact=True, source_modules=2,
                          unique_DOM_ids=len(inspect.ids), local_links=len(inspect.links), missing_links=missing,
                          JS_syntax_passed=True, native_routes=3,
                          native_points=sum(len(route['points']) for route in data['routes']),
                          public_fields_per_core=35, field_select_options=70,
                          embedded_events=sum(len(route['events']) for route in data['routes']),
                          acceptance_dimensions=10, source_CPU_cases=0, Native_runs=0,
                          phase30_new_static_exclusions=2)))


if __name__ == '__main__':
    main()
