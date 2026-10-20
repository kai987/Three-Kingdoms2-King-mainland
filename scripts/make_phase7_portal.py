#!/usr/bin/env python3
"""Generate a compact phase7 evidence portal from current receipts; no emulator."""
from pathlib import Path
import hashlib
from html.parser import HTMLParser
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase7'
sys.path.insert(0, str(ROOT))
from source.recovered.game_enums import TACTIC_NAMES


def read(name, optional=False):
    path = OUT / name
    if optional and not path.exists():
        return {}
    return json.loads(path.read_text())


def image_url(name):
    path = OUT / name
    if not path.exists() or not path.stat().st_size:
        raise ValueError(f'Missing/empty native screenshot: {path}')
    return name + '?sha=' + hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def receipt(name):
    row = read(name, True)
    keep = ('status', 'case_count', 'rom_cpu_case_count', 'rom_oracle_case_count',
            'source_guard_case_count', 'source_only_guard_count', 'failed_count',
            'counts', 'status_counts', 'instruction_ir_total', 'instruction_ir_coverage',
            'static_instruction_matches', 'original_complete_routine_case_count',
            'original_prefix_or_suffix_case_count', 'actual_ROM_CPU_comparison_count',
            'native_core_field_comparison_count', 'source_original_code_calls',
            'natural_core_field_comparisons', 'scope', 'contract', 'limits', 'limitations')
    return {key: row[key] for key in keep if key in row}


def entry_summary(row):
    result = {key: row[key] for key in ('name', 'entry', 'bank', 'file', 'instruction_count')}
    result.update(branch_count=len(row.get('conditions', [])),
                  reachable_control_write_count=len(row.get('control_writes', [])),
                  external_calls=row.get('external_calls', []))
    return result


class StaticHTML(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = []; self.links = []; self.images = []; self.details = []
    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs: self.ids.append(attrs['id'])
        if tag == 'a' and 'href' in attrs: self.links.append(attrs['href'])
        if tag == 'img' and 'src' in attrs: self.images.append(attrs['src'])
        if tag == 'details': self.details.append(attrs)


def main():
    catalog = read('controller/state-catalog.json')
    decision = read('decisions/evidence.json')
    native = read('runtime/natural-turn/validation.json')
    cpu = read('runtime/cpu-call/validation.json')
    native_repeat = read('runtime/natural-turn/repeat-validation.json')
    cpu_repeat = read('runtime/cpu-call/repeat-validation.json')
    checkpoints = []
    for point in native['checkpoints']:
        row = {key: value for key, value in point.items() if key != 'units'}
        actor = next((unit for unit in point['units'] if unit['slot'] == 1), None)
        row['unit1'] = actor
        row['movement_cost_6F97'] = (OUT / ('runtime/natural-turn/' + point['label'] + '-sram.bin')).read_bytes()[0xF97]
        row['image'] = image_url('runtime/natural-turn/' + point['label'] + '.png')
        checkpoints.append(row)
    predicate_notes = [
        '目标折算地形class为0或2。', '目标折算地形class为0或4。',
        '目标折算地形class为0或4。', '目标折算地形class为0或4。',
        '目标折算地形class为3。', '目标槽为0或10。',
        '目标class5，目标四邻居的低7位某个等于actor槽。',
        '目标class0/4，存在非FF且bit7=1的邻居。',
        '目标class不是5，目标忠诚byte3低于50。',
        'actor class4/5，与目标相邻，且目标class5。',
        '目标class3，存在非FF、bit7=1且class3的邻居。',
        'actor class0；其byte9非0或byte8≥100；当前方04D8缓存组首字节为FF。',
        '目标class3，存在非FF、bit7=1且class3的邻居。',
        'actor class5；actor四邻居中某值XOR80等于目标槽。',
        '目标class不是5，存在非FF、bit7=1且class不是5的邻居。',
        '目标class不是5；武或知≥85；byte9≥2且byte8≥188，保持原逐字节条件。',
    ]
    data = {
        'catalog': {key: catalog[key] for key in ('entry', 'trampoline_entry', 'entry_file',
                    'trampoline_raw_hex', 'control_fields', 'request_modes', 'inline_tables',
                    'instruction_count', 'scope', 'inline_audit')},
        'entries': [entry_summary(row) for row in catalog['entries']],
        'decision': {key: decision[key] for key in ('scopes', 'fields', 'cost_tables',
                     'important_quirks', 'boundaries', 'secondary_request_provenance')},
        'predicates': predicate_notes, 'tactic_names': list(TACTIC_NAMES),
        'receipts': {key: receipt(path) for key, path in {
            'controller': 'controller/validation.json', 'decisions': 'decisions/validation.json',
            'exchange': 'exchange/validation.json', 'integration': 'source-integration.json'}.items()},
        'runtime': {'checkpoints': checkpoints, 'frames': native['frames'],
                    'coordinate_commits': native['coordinate_commits'],
                    'action_point_charges': native['action_point_charges'],
                    'RAM_injections': native['RAM_injections'], 'SRAM_injections': native['SRAM_injections'],
                    'readiness_or_ack_injection': native['readiness_or_ack_injection'],
                    'input_plan': native['input_plan'], 'core': native['core'], 'limits': native['limits'],
                    'native_repeat_checks': native_repeat['nonempty_artifact_checks'],
                    'full_frame_fields_equal': native_repeat['full_frame_fields_equal'],
                    'cpu': {key: cpu[key] for key in ('case_count', 'instruction_count',
                            'unique_instruction_starts', 'seeded_call', 'native_field_comparisons',
                            'native_instruction_trace', 'decision_entry_events', 'limits')},
                    'cpu_repeat_checks': cpu_repeat['nonempty_artifact_checks']},
    }
    html = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>战术AI：提案与行动交接 · 第七轮逆向证据</title>
<style>*{box-sizing:border-box}html{scroll-behavior:smooth}body{background:#f6f5f1;color:#242721;font:16px/1.65 system-ui,sans-serif;margin:0}main{max-width:1180px;margin:auto;padding:32px 24px}h1{font-size:32px;line-height:1.3}h2{margin-top:36px;scroll-margin-top:16px}h3{font-size:19px}a{color:#285641}nav{display:flex;gap:18px;flex-wrap:wrap;border-block:1px solid #c9ccbe;padding:14px 0}code{font:13px/1.5 ui-monospace,monospace}button,select,input{font:inherit;padding:8px;border:1px solid #a9b49a;background:white;color:inherit;margin:4px 12px 4px 0;max-width:100%}input[type=number]{width:115px}input[type=range]{width:100%;margin:8px 0}.note{border-left:4px solid #a18a3b;padding-left:16px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}.metric{border-block:1px solid #c9ccbe;padding:12px 0}.metric strong{display:block;font-size:27px}.metric small{display:block}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:9px;border-bottom:1px solid #d9ddce;vertical-align:top}th{background:#eceee6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eceee6;padding:16px;font:13px/1.6 ui-monospace,monospace}small,figcaption{color:#64695e}img{image-rendering:pixelated;max-width:100%;height:auto}.screens,.two{display:grid;grid-template-columns:1fr 1fr;gap:24px}.screens figure{margin:0}.screens img{width:100%;max-width:512px}figcaption{font-size:14px}summary{cursor:pointer;padding:10px 0}footer{border-top:1px solid #c9ccbe;margin-top:36px;padding-top:16px;color:#64695e}.steps{display:flex;gap:16px;flex-wrap:wrap;list-style:none;padding:0}.steps li{flex:1;min-width:170px;border-top:2px solid #a9b49a;padding-top:10px}.compact{margin:10px 0}.fields{display:grid;grid-template-columns:repeat(4,1fr);gap:8px 16px}.fields div{border-bottom:1px solid #d9ddce;padding:8px 0}.fields strong{display:block;font-size:20px}details{margin:8px 0}.tag{color:#285641}p{margin:12px 0}@media(max-width:700px){main{padding:20px 16px}h1{font-size:26px}.metrics{grid-template-columns:1fr}.screens,.two{grid-template-columns:1fr}.fields{grid-template-columns:1fr 1fr}}</style></head>
<body><main><small>第七轮 · 原ROM只读 · 控制源码、独立算法与原核心回放</small><h1>战术AI：从决策提案到行动提交</h1><nav><a href="../index.html">总入口</a><a href="README.md">本轮报告</a><a href="../phase6/index.html">阶段6</a><a href="../../source/README.md">源码说明</a><a href="#controller">控制器</a><a href="#decisions">决策规则</a><a href="#exchange">提案交接</a><a href="#runtime">原核心回放</a></nav>
<p class="note">global4选择bank8/9的A000→A02D产生提案，NMI3战斗控制器随后消费提案。global使用 <code>007A &amp; 1F</code>，NMI使用 <code>0078 &amp; 0F</code>。<strong>本页浏览原表、字段计算与已有截图，不运行游戏或模拟器。</strong></p><div class="metrics" id="metrics"></div><p id="integration-summary"></p>
<h2 id="controller">1 · 有界合作控制器</h2><p>A02D根据6F8B返回、处理第二阶段或扫描20槽。跳过inactive、异侧和空武将；合格actor按6FA1低4位进入8项策略表。策略正式名称尚未确认，保留0..7编号；16项计略predicate另有独立表。</p>
<label for="request-phase">6F8B请求：</label><select id="request-phase"><option value="0">0 · 扫描并产生提案</option><option value="1">1 · B933已部署缓存效果</option><option value="255">FF · 当前无请求，直接返回</option></select><pre id="request-detail" class="compact"></pre>
<label for="catalog-domain">原表：</label><select id="catalog-domain"><option value="strategy">8项策略</option><option value="predicate">16项计略predicate</option><option value="other">4个控制入口</option></select><label for="catalog-entry">入口：</label><select id="catalog-entry"></select><pre id="entry-summary" class="compact"></pre><p id="controller-proof"></p><details><summary>所选入口的目录摘要与inline表证据</summary><pre id="entry-json"></pre></details>
<p><a href="controller/state-catalog.json">完整目录</a> · <a href="controller/control.asm">原汇编</a> · <a href="controller/validation.json">控制CPU回执</a> · <a href="../../source/recovered/tactical_ai_control.py">tactical_ai_control.py</a></p>
<h2 id="decisions">2 · 可读决策：两个轴的贪心选择</h2><ol class="steps"><li><strong>① 比较两个轴</strong><br>朝目标的横／纵方向；位移较大者先，相等时纵向先。</li><li><strong>② 取得两份报价</strong><br>检查原坐标边界、地形／适性和AP；再按费用稳定排序。</li><li><strong>③ 查看占位</strong><br>可负担空位产生status0；指定策略可进入相邻攻击fallback。</li><li><strong>④ 只写提案</strong><br>方向6F8D、费用6F97；此时不改坐标、不扣AP。</li></ol>
<p>该算法未搜索完整路径。字节差使用原SBC/BPL行为；已位于目标仍可能向下，反向记忆被复制但本段未用于筛选。occupied fallback仅允许完整策略byte等于1或5，高位flags不能忽略。</p>
<h3>AI移动报价表</h3><p>原代码连读同一武将byte8两次：byte8&lt;3使用第二表，否则第一表；byte9不参与选表。它与玩家的063C兵量缓存选表不同。</p>
<label for="quote-class">折算地形class：</label><select id="quote-class"></select><label for="quote-affinity">byte11适性：</label><select id="quote-affinity"></select><label for="quote-byte8">兵字段byte8：</label><input id="quote-byte8" type="number" min="0" max="255" value="32"><label for="quote-ap">当前AP：</label><input id="quote-ap" type="number" min="0" max="255" value="24"><pre id="quote-result" class="compact"></pre><small>仅按原表查看报价，不执行地图读取、策略或移动。适性3的0成本槽保留原编码，正式能力未由此确认；raw地形≥6在AI查询中折算为class2。</small>
<details><summary>7个可读API的完整／前缀范围与原实现细节</summary><div class="scroll"><table><thead><tr><th>API</th><th>原入口／终点</th><th>验证范围</th></tr></thead><tbody id="semantic-scopes"></tbody></table></div><pre id="decision-quirks"></pre></details><p><a href="decisions/README.md">决策范围说明</a> · <a href="decisions/evidence.json">原字节及字段</a> · <a href="decisions/validation.json">独立语义回执</a> · <a href="../../source/recovered/tactical_decisions.py">tactical_decisions.py</a></p>
<h2 id="exchange">3 · 6F8D的含义由status决定</h2><p>同一个byte在不同提案中复用。<strong>status0的值3是向右；只有status2的计略ID3才是「要撃」。</strong>原bank12表把status0..4分派到battle主8的sub3/5/8/12/13。6F8B=FF表示请求返回；6F8F=FF在缓存效果未应用路径保留原编码，不在该5项路由表域。</p>
<label for="proposal-kind">6F8F status：</label><select id="proposal-kind"><option value="0">0 · 移动</option><option value="1">1 · 普通攻击</option><option value="2">2 · 计略</option><option value="3">3 · 无行动</option><option value="4">4 · 退却</option></select><label for="proposal-value">6F8D原值：</label><input id="proposal-value" type="number" min="0" max="255" value="3"><label for="proposal-target">6F8E原值：</label><input id="proposal-target" type="number" min="0" max="255" value="0"><pre id="proposal-result" class="compact"></pre>
<div class="two"><section><h3>请求与yield</h3><p>BEA6..BEB9只有0087符号位为1才请求phase0。A02D产生一份提案后写6F8B=FF，交原上层消费。status3计数与合格尝试数均u8回绕；扫描结束计数不等则重扫。</p></section><section><h3>报价与提交分开</h3><p>BF26..BF7B坐标suffix位于真实图形请求之后，保留Y15跳行；BF83..BF97再扣6F97费用并进入battle主4/sub2。语义接口不执行前置图形，也不补写完成标志。</p></section></div>
<p>移动控制A51F只在6F8B=FF时请求phase1、actor取0509，原global4调用B933应用缓存持续效果；第二阶段属于独立请求。<a href="secondary-origin.json">生产—消费代码链</a>确认它至少读取计略11「十面埋伏」建立的缓存；没有把该静态关联当作自然成功施放或所有缓存来源的证明。</p><p><a href="exchange/validation.json">提案交接当前回执</a> · <a href="../../source/recovered/tactical_exchange.py">tactical_exchange.py</a> · <a href="source-integration.json">GameEngine真实E22C caller桥接</a></p>
<h2 id="runtime">4 · 原核心：无注入的四次移动</h2><p id="native-summary"></p><label for="screenshot-pair">截图配对：</label><select id="screenshot-pair"><option value="movement">第1次→第4次坐标提交</option><option value="proposal">phase0请求→方向提案</option><option value="turn">等待确认→玩家回合消息</option></select><div class="screens"><figure><img id="proof-left" src="IMAGE_LEFT" alt="原Nestopia第一次移动提交"><figcaption id="proof-left-caption"></figcaption></figure><figure><img id="proof-right" src="IMAGE_RIGHT" alt="原Nestopia第四次移动提交"><figcaption id="proof-right-caption"></figcaption></figure></div>
<h3>13个原存档检查点</h3><label for="checkpoint">检查点：</label><select id="checkpoint"></select><input id="checkpoint-range" type="range" min="0" max="12" value="2" aria-label="查看原保存检查点"><div id="checkpoint-fields" class="fields"></div><p id="checkpoint-description"></p><details><summary>所选原检查点JSON</summary><pre id="checkpoint-json"></pre></details>
<h3>坐标提交之后的真实AP扣款</h3><div class="scroll"><table><thead><tr><th>坐标frame</th><th>槽位1坐标</th><th>AP扣款frame</th><th>AP</th></tr></thead><tbody id="movement-commits"></tbody></table></div>
<p id="cpu-summary"></p><details><summary>独立同步CPU调用的显式种子与8字段parity</summary><pre id="cpu-detail"></pre></details><details><summary>原核心按键／准备／重复检查与范围</summary><pre id="runtime-detail"></pre></details><p><a href="runtime/README.md">原核心完整说明</a> · <a href="runtime/natural-turn/validation.json">700帧回执</a> · <a href="runtime/natural-turn/repeat-validation.json">52项重复一致</a> · <a href="runtime/cpu-call/actual-cpu-instructions.json">8,243条实际原指令</a> · <a href="runtime/cpu-call/repeat-validation.json">独立CPU重复一致</a></p>
<details><summary>模块计数、源码边界与联合入口回执</summary><pre id="receipt-detail"></pre></details><footer>本页生成时读取当前JSON回执。CPU案例、source guard、字段parity、IR覆盖、视频帧和非空文件hash分别计数。原核心只观察到phase0/FF及status0移动，未证明phase1、成功计略或整场自然战斗。控制器复原全部可达IR不等于所有指令都已动态覆盖；硬件/NMI完整帧与图形请求仍由调用者负责。</footer></main>
<script>const D=PAYLOAD,$=s=>document.querySelector(s),hex=(n,w=4)=>Number(n).toString(16).toUpperCase().padStart(w,'0'),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),pretty=v=>JSON.stringify(v,null,2),number=v=>v==null?'待回执':Number(v).toLocaleString();
function cpuCount(key){const r=D.receipts[key];return key==='controller'?r.rom_cpu_case_count:key==='decisions'?r.rom_oracle_case_count:r.case_count;}function guards(key){const r=D.receipts[key];return r.source_guard_case_count??r.source_only_guard_count??0;}const metricLabels={controller:'完整合作控制器 · 原CPU',decisions:'可读决策段 · 原CPU',exchange:'提案交接suffix · 原CPU'};$('#metrics').innerHTML=Object.entries(metricLabels).map(([key,label])=>`<div class="metric"><small>${label}</small><strong>${number(cpuCount(key))}</strong><small>${esc(D.receipts[key].status||'尚未生成')} · 另${guards(key)}项source guard</small></div>`).join('');const iv=D.receipts.integration;$('#integration-summary').textContent=`统一入口另外${number(iv.case_count)}项检查：${number(iv.actual_ROM_CPU_comparison_count)}项原CPU、${number(iv.native_core_field_comparison_count)}项已捕获原核心字段比较。global4桥接共享原寄存器/真实caller栈，返回E22C；源模型original-code调用数${iv.source_original_code_calls??'待回执'}。`;
function requestDetail(){const value=Number($('#request-phase').value);$('#request-detail').textContent=value===255?'6F8B=FF → A02D立即RTS；不是一条新的行动提案。':value===1?'6F8B=1 → B933已部署缓存效果 → 结束写6F8B=FF。\nphase1并非新的actor扫描；自然700帧样本未观察到这条路径。':'6F8B=0（以及除1/FF以外的其他raw byte）→ A03C扫描 → A099策略 → 6F8F结果。\n非status3：写6F8B=FF yield；status3：计数并继续扫描/重扫。';}$('#request-phase').addEventListener('change',requestDetail);requestDetail();
function catalogRows(){const mode=$('#catalog-domain').value;return D.entries.filter(row=>mode==='strategy'?row.name.startsWith('strategy_')&&row.name!=='strategy_dispatch':mode==='predicate'?row.name.startsWith('tactic_predicate_'):!row.name.startsWith('tactic_predicate_')&&!(row.name.startsWith('strategy_')&&row.name!=='strategy_dispatch'));}function entryOptions(){const mode=$('#catalog-domain').value;$('#catalog-entry').innerHTML=catalogRows().map((row,i)=>`<option value="${i}">${mode==='strategy'?'策略'+row.name.split('_').at(-1):mode==='predicate'?'计略'+row.name.split('_').at(-1)+' · '+D.tactic_names[Number(row.name.split('_').at(-1))]:row.name} · $${hex(row.entry)}</option>`).join('');entryDetail();}function entryDetail(){const row=catalogRows()[Number($('#catalog-entry').value)],mode=$('#catalog-domain').value;let text=`${row.name} · physical bank${row.bank} CPU$${hex(row.entry)} / file0x${hex(row.file,6)}\n可达IR集合${row.instruction_count}条；${row.branch_count}个可达条件分支。`;if(mode==='strategy')text+='\n按6FA1[actor]&0F选择，合法表域0..7；正式策略名称未确认。';if(mode==='predicate'){const i=Number(row.name.split('_').at(-1));text+=`\n计略${i} ${D.tactic_names[i]}：${D.predicates[i]}\n这些是适用predicate；通过条件不等于优先级选择成功或已提交效果。`;}$('#entry-summary').textContent=text;$('#entry-json').textContent=pretty({entry:row,inline_tables:D.catalog.inline_tables,scope:D.catalog.scope});}$('#catalog-domain').addEventListener('change',entryOptions);$('#catalog-entry').addEventListener('change',entryDetail);entryOptions();const cv=D.receipts.controller;$('#controller-proof').textContent=`控制IR静态${number(cv.static_instruction_matches)}/${number(cv.instruction_ir_total)}条逐字节核验；动态覆盖${number(cv.instruction_ir_coverage)}/${number(cv.instruction_ir_total)}。两表共24个合法索引，重复target仍按索引保留。`;
$('#quote-class').innerHTML=Array.from({length:6},(_,i)=>`<option value="${i}">${i}</option>`).join('');$('#quote-class').value='2';$('#quote-affinity').innerHTML=Array.from({length:4},(_,i)=>`<option value="${i}">${i}${i===3?' · 原0成本槽':''}</option>`).join('');function quote(){const tc=Number($('#quote-class').value),af=Number($('#quote-affinity').value),b=Number($('#quote-byte8').value),ap=Number($('#quote-ap').value);if(!Number.isInteger(b)||!Number.isInteger(ap)||b<0||b>255||ap<0||ap>255){$('#quote-result').textContent='byte8与AP必须是0..255整数。';return;}const second=b<3,cost=D.decision.cost_tables[second?'second_rows':'first_rows'][tc][af];$('#quote-result').textContent=`byte8=${b} → ${second?'第二':'第一'}表；class${tc} / 适性${af} → 报价${cost} AP\n现有AP=${ap}，原carry条件AP≥报价：${ap>=cost?'通过':'不通过'}。\n报价过程没有改AP或坐标；同值byte9不参与选表。\n这是原表公式查看，不代表该地形坐标或策略已可达。`;}['#quote-class','#quote-affinity'].forEach(s=>$(s).addEventListener('change',quote));['#quote-byte8','#quote-ap'].forEach(s=>$(s).addEventListener('input',quote));quote();$('#semantic-scopes').innerHTML=D.decision.scopes.map(row=>`<tr><td><code>${esc(row.api)}</code></td><td><code>$${hex(row.entry)} → ${(row.stop||[]).map(x=>'$'+hex(x)).join('/')}</code></td><td>${esc(row.scope)}</td></tr>`).join('');$('#decision-quirks').textContent=pretty({quirks:D.decision.important_quirks,boundaries:D.decision.boundaries});
const kindLabels=['移动','普通攻击','计略','无行动','退却'],directions=['向上','向下','向左','向右'],routes=[3,5,8,12,13];function proposal(){const kind=Number($('#proposal-kind').value),a=Number($('#proposal-value').value),target=Number($('#proposal-target').value);if(![a,target].every(v=>Number.isInteger(v)&&v>=0&&v<=255)){$('#proposal-result').textContent='6F8D和6F8E必须是0..255整数。';return;}let interpretation=kind===0?`方向${a&3}：${directions[a&3]}（读取低2位；此处不会解释为计略ID）。`:kind===1?`普通攻击目标槽原值${a}；6F8E不是本路由的计略目标。`:kind===2?`计略ID${a}：${a<16?D.tactic_names[a]:'超出已证明16项域'}；计略目标槽原值${target}。`:kind===3?'没有可执行行动；6F8D/E可能仍有旧值，不根据它们命名动作。':`退却目的城市原值${a}；不把它解释为方向或计略。`;$('#proposal-result').textContent=`6F8F=${kind}（${kindLabels[kind]}） → battle主8/sub${routes[kind]}\n6F8D=${a} / 6F8E=${target}\n${interpretation}\n只解释字段与原路由表，不执行动作、图形或确认等待。`;}$('#proposal-kind').addEventListener('change',proposal);['#proposal-value','#proposal-target'].forEach(s=>$(s).addEventListener('input',proposal));proposal();
const points=D.runtime.checkpoints,byLabel=label=>points.find(row=>row.label===label),pairs={movement:['first-coordinate-commit','fourth-coordinate-commit'],proposal:['ai-request','ai-proposal'],turn:['wait-confirmation','player-turn-message']};function shotCaption(row){const u=row.unit1;return `frame${row.frame} · ${row.label} · 槽1(${u.x},${u.y})，AP${row.active_action_points_0505}；global${row.global_main_007A}/NMI${row.nmi_scene_0078}。原ROM/RAM/SRAM无注入。`;}function screenshotPair(){const rows=pairs[$('#screenshot-pair').value].map(byLabel);['left','right'].forEach((side,i)=>{const row=rows[i];$('#proof-'+side).src=row.image;$('#proof-'+side).alt=`原Nestopia ${row.label} 第${row.frame}帧`;$('#proof-'+side+'-caption').textContent=shotCaption(row);});}$('#screenshot-pair').addEventListener('change',screenshotPair);screenshotPair();$('#native-summary').textContent=`导入原战场菜单存档后，只用普通下/右/A输入${D.runtime.frames}帧，RAM注入${D.runtime.RAM_injections.length}、SRAM注入${D.runtime.SRAM_injections.length}、ack/readiness注入${D.runtime.readiness_or_ack_injection?'有':'无'}。敌方槽1连续4次移动，AP24→21→18→15→10，随后换回side128/第2回合。${D.runtime.native_repeat_checks}个非空PNG/RAM/SRAM/state重复hash一致；不称完整自然战斗。`;
$('#checkpoint').innerHTML=points.map((row,i)=>`<option value="${i}">${row.frame} · ${row.label}</option>`).join('');$('#checkpoint').value='2';$('#checkpoint-range').max=String(points.length-1);function checkpoint(){const row=points[Number($('#checkpoint').value)],u=row.unit1;$('#checkpoint-range').value=$('#checkpoint').value;const cells=[['frame',row.frame],['battle主/sub',row.battle_state_0500_0501.join('/')],['6F8B请求',hex(row.ai_phase_6F8B,2)],['6F8F status',row.proposal_status_6F8F],['6F8C actor',row.ai_actor_6F8C],['6F8D原值',row.proposal_action_or_direction_6F8D],['槽1坐标',`(${u.x},${u.y})`],['活动AP',row.active_action_points_0505]];$('#checkpoint-fields').innerHTML=cells.map(([label,value])=>`<div><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join('');$('#checkpoint-description').textContent=`${row.label}：side${row.side_0504} / round${row.round_0506}；6F97费用${row.movement_cost_6F97}；cursor${row.scan_cursor_6F94}、status3计数${row.status3_count_6F95}、合格尝试${row.eligible_attempts_6F96}。这是已保存的一帧结束值，滚动滑块只换证据，不推进游戏。`;$('#checkpoint-json').textContent=pretty(row);}$('#checkpoint').addEventListener('change',checkpoint);$('#checkpoint-range').addEventListener('input',()=>{$('#checkpoint').value=$('#checkpoint-range').value;checkpoint();});checkpoint();$('#movement-commits').innerHTML=D.runtime.coordinate_commits.map((row,i)=>{const charge=D.runtime.action_point_charges[i];return `<tr><td>${row.frame}</td><td>(${row.from.join(',')}) → (${row.to.join(',')})</td><td>${charge.frame}</td><td>${charge.before} → ${charge.after}</td></tr>`;}).join('');const cpu=D.runtime.cpu;$('#cpu-summary').textContent=`独立同步原CPU实验另外${cpu.case_count}个case、${number(cpu.instruction_count)}条原指令、${number(cpu.unique_instruction_starts)}个唯一(bank,PC)。显式A000/真实E22C caller种子所得8个提案/扫描字段与下一整机frame432一致；另${D.runtime.cpu_repeat_checks}项非空轨迹/RAM/SRAM重复一致。这不是Nestopia原生指令录制，8字段不算8个case。`;$('#cpu-detail').textContent=pretty(cpu);$('#runtime-detail').textContent=pretty({input_plan:D.runtime.input_plan,RAM_injections:D.runtime.RAM_injections,SRAM_injections:D.runtime.SRAM_injections,ack_injection:D.runtime.readiness_or_ack_injection,core:D.runtime.core,native_repeat_artifacts:D.runtime.native_repeat_checks,full_frame_fields_equal:D.runtime.full_frame_fields_equal,limits:D.runtime.limits});$('#receipt-detail').textContent=pretty(D.receipts);
</script></body></html>'''
    html = html.replace('IMAGE_LEFT', image_url('runtime/natural-turn/first-coordinate-commit.png'))
    html = html.replace('IMAGE_RIGHT', image_url('runtime/natural-turn/fourth-coordinate-commit.png'))
    html = html.replace('PAYLOAD', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'index.html').write_text(html)
    parsed = StaticHTML(); parsed.feed(html)
    assert len(parsed.ids) == len(set(parsed.ids)), 'Duplicate HTML ids'
    script = re.search(r'<script>([\s\S]+)</script>', html).group(1)
    literal_selectors = re.findall(r"\$\('(#[-\w]+)'\)", script)
    assert all(selector[1:] in parsed.ids for selector in literal_selectors)
    assert all('open' not in attrs for attrs in parsed.details), 'Evidence details must default closed'
    for target in parsed.links + parsed.images + [row['image'] for row in checkpoints]:
        if target.startswith('#'):
            assert target[1:] in parsed.ids, target
        else:
            assert not target.startswith(('file:', 'http:', 'https:'))
            assert (OUT / target.split('?', 1)[0]).exists(), target
    checked = subprocess.run(['node', '--check', '--input-type=commonjs'], input=script,
                             text=True, capture_output=True)
    assert checked.returncode == 0, checked.stderr
    strategies = [row for row in data['entries'] if re.fullmatch(r'strategy_\d+', row['name'])]
    predicates = [row for row in data['entries'] if row['name'].startswith('tactic_predicate_')]
    assert len(strategies) == 8 and len(predicates) == 16 and len(checkpoints) == 13
    proof = {'status': 'passed', 'html_sha256': hashlib.sha256(html.encode()).hexdigest(),
             'html_bytes': len(html.encode()), 'strategy_options': len(strategies),
             'predicate_options': len(predicates), 'checkpoint_options': len(checkpoints),
             'all_local_links_and_images_exist': True, 'unique_ids': len(parsed.ids),
             'collapsed_details': len(parsed.details), 'node_script_syntax': 'passed',
             'data_source_receipts': {key: {'case_count': value.get('case_count'),
                                      'status': value.get('status')} for key, value in data['receipts'].items()},
             'limits': ['Static structure/link/JS syntax verification only; browser interaction/rendering is separately validated.',
                        'No emulator or native core is run by this HTML page.']}
    (OUT / 'static-validation.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(proof, ensure_ascii=False))


if __name__ == '__main__':
    main()
