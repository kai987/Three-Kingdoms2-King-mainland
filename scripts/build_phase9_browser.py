#!/usr/bin/env python3
"""Build a static phase9 browser of existing source and original-core evidence.

Only evidence JSON, raw snapshots and pinned source text are read. The generated
page neither executes gameplay formulas nor a CPU, IR, emulator or game frame.
Formal images require both original-core runs to have passed artifact parity.
"""
from pathlib import Path
from html.parser import HTMLParser
import ast
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase9'
IDS = (1, 5, 7, 8, 9, 10, 12, 14)
NAMES = ('火計', '陥穽', '虚兵', '要撃', '乱水', '火箭', '偽撃転殺', '共殺',
         '籠絡', '落石', '連環', '十面埋伏', '水攻', '連弩', '劫火', '奇門遁甲')
CASES = tuple(f'tactic-{i:02}' for i in IDS) + ('tactic-01-death', 'tactic-09-levelup')


def read(relative):
    p = OUT / relative
    return json.loads(p.read_text()) if p.exists() else {}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def receipt(relative):
    d = read(relative)
    keys = ('status', 'rom_cpu_case_count', 'source_guard_case_count', 'source_guard_count', 'case_count',
            'actual_ROM_CPU_comparison_count', 'failed_count', 'counts',
            'original_complete_case_count', 'original_prefix_case_count',
            'original_death_prefix_case_count', 'original_post_graphics_suffix_case_count',
            'complete_effect_cpu_case_count', 'complete_helper_cpu_case_count',
            'prefix_cpu_case_count', 'source_sha256', 'validator_sha256', 'evidence_sha256',
            'contract', 'limits', 'limitations')
    return {k: d[k] for k in keys if k in d}


def excerpt(relative, names):
    """Show exact tested source text, not a second browser implementation."""
    text = (ROOT / relative).read_text()
    lines = text.splitlines()
    wanted = set(names)
    return '\n\n'.join('\n'.join(lines[n.lineno - 1:n.end_lineno])
                       for n in ast.walk(ast.parse(text))
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in wanted)


def snapshot(directory, checkpoint, tracked):
    label = checkpoint['label']
    png = directory / f'{label}.png'
    rp = directory / f'{label}-ram.bin'
    sp = directory / f'{label}-sram.bin'
    r, s = rp.read_bytes(), sp.read_bytes()
    assert len(r) == 2048 and len(s) == 8192, (directory.name, label)
    pixels = png.read_bytes()
    assert pixels[:8] == b'\x89PNG\r\n\x1a\n'
    assert (int.from_bytes(pixels[16:20], 'big'), int.from_bytes(pixels[20:24], 'big')) == (256, 240)
    units = []
    records = []
    for ident in sorted(tracked):
        at = 0x3C0 + ident * 12
        raw = s[at:at + 12]
        records.append(dict(officer=ident, record_hex=raw.hex(' ').upper(), HP=raw[0],
                            martial=raw[1], intelligence=raw[2], loyalty=raw[3],
                            virtue=raw[4], location_raw=raw[5],
                            XP=int.from_bytes(raw[6:8], 'little'),
                            troops_raw=int.from_bytes(raw[8:10], 'little'),
                            troops_low10=int.from_bytes(raw[8:10], 'little') & 1023,
                            packed_byte11=raw[11], experience_level=raw[11] >> 4,
                            record_status_raw=raw[11] & 3))
    for slot in range(20):
        ident = r[0x664 + slot]
        if ident >= 237:
            continue
        units.append(dict(slot=slot, officer=ident, X=r[0x600 + slot], Y=r[0x614 + slot],
                          side_raw=r[0x628 + slot], condition_raw=r[0x650 + slot],
                          selector_raw=r[0x63C + slot], AI_strategy_raw=s[0xFA1 + slot]))
    # Compare decoded data with the original capture metadata when supplied.
    for key, expected in [('AP_0505', r[0x505]), ('tactic_0543', r[0x543]),
                          ('result_0544', r[0x544]), ('battle_state', list(r[0x500:0x502]))]:
        if key in checkpoint:
            assert checkpoint[key] == expected, (directory.name, label, key)
    for item in records:
        stored = checkpoint.get('officer_records', {}).get(str(item['officer']))
        if stored is not None:
            assert stored['record_hex'] == item['record_hex'], (directory.name, label, item['officer'])
    relative = str(png.relative_to(OUT))
    return dict(label=label, frame=checkpoint.get('frame'), image=relative + '?sha=' + sha(png),
                sha256=sha(png), RAM=str(rp.relative_to(OUT)), SRAM=str(sp.relative_to(OUT)),
                global_main=r[0x7A], NMI_scene=r[0x78], battle=list(r[0x500:0x502]),
                side=r[0x504], AP=r[0x505], tactic=r[0x543], result=r[0x544],
                actor=r[0x50A], target=r[0x509], loss_report=list(r[0x42C:0x434]),
                grain_effect_words={'0522': int.from_bytes(r[0x522:0x524], 'little'),
                                    '0524': int.from_bytes(r[0x524:0x526], 'little')},
                resources_0520_0527=list(r[0x520:0x528]),
                side_aggregates_0518_051F=list(r[0x518:0x520]),
                cache=list(r[0x4D8:0x4E0]), units=units, records=records,
                unit_arrays={f'{a:04X}': list(r[a:a + 20]) for a in (0x600, 0x614, 0x628, 0x63C, 0x650, 0x664)})


def native():
    groups, pending, checks = [], [], 0
    manifest = read('runtime/evidence.json')
    formal_cases = {c['case']: c for c in manifest.get('native_cases', [])}
    for case in CASES:
        directory = OUT / 'runtime' / case
        validation = read(f'runtime/{case}/validation.json')
        repeat = read(f'runtime/{case}/repeat-validation.json')
        if validation.get('status') != 'passed' or repeat.get('status') != 'passed' or repeat.get('all_hashes_equal') is not True:
            pending.append(case)
            continue
        # This whitelist excludes every exploration and repeat-output directory.
        assert validation.get('case', case) == case
        for name, expected in validation['artifact_sha256'].items():
            p = directory / name
            assert p.is_file() and p.stat().st_size == expected['bytes'] and sha(p) == expected['sha256'], (case, name)
            if p.stat().st_size:
                checks += 1
        for artifact in repeat.get('artifacts', []):
            assert artifact['equal'] is True, (case, artifact)
            p = directory / artifact['artifact']
            assert p.stat().st_size == artifact['bytes'] and sha(p) == artifact['sha256'], (case, artifact['artifact'])
        checkpoints = read(f'runtime/{case}/checkpoints.json') or validation['checkpoints']
        tracked = {int(k) for checkpoint in checkpoints for k in checkpoint.get('officer_records', {}) if int(k) < 237}
        tracked.update(unit['officer_id'] for c in checkpoints for unit in c.get('units', []) if unit['officer_id'] < 237)
        captures = [snapshot(directory, c, tracked) for c in checkpoints]
        assert len(captures) == validation['checkpoint_count']
        formal = formal_cases.get(case)
        if formal is not None:
            assert formal['status'] == 'passed' and formal['all_native_artifact_hashes_equal'] is True
            assert formal['full_frame_fields_equal'] is True
            assert {c['label']: c['image'].split('?', 1)[0].removeprefix('runtime/') for c in captures} == formal['images']
            for key in ('validation', 'repeat_validation', 'checkpoints', 'frame_fields', 'input_plan'):
                assert (OUT / 'runtime' / formal[key]).is_file()
        keys = ('case', 'tactic_id', 'name', 'controlled_fixture', 'natural_gameplay', 'parent_state',
                'parent_sha256', 'core', 'frames', 'RAM_preparation', 'SRAM_preparation', 'rng_preparation',
                'selected_tactic_result_request_cache_animation_ack_injection', 'readiness_or_ack_injection',
                'terrain_fixture', 'menu_generated_by_original_code', 'input_plan', 'verified_effects', 'limits')
        groups.append(dict(name=case, tactic_id=validation['tactic_id'],
                           validation={k: validation[k] for k in keys if k in validation},
                           repeat=repeat, receipt=f'runtime/{case}/validation.json',
                           repeat_receipt=f'runtime/{case}/repeat-validation.json', captures=captures,
                           manifest_case=formal))
    if manifest.get('status') == 'passed':
        summary = manifest['summary']
        assert set(formal_cases) == {g['name'] for g in groups}
        assert summary['native_case_count'] == len(groups)
        assert summary['checkpoint_count'] == sum(len(g['captures']) for g in groups)
        assert summary['nonempty_artifact_hash_checks'] == checks
    return groups, pending, checks


def flows():
    """Grounded prose only; target qualification and effect RNG remain separate."""
    common = '施放成功 gate 为 bank12 $B7BE：依实时知力、等级差、距离与环境形成5..95门槛，使用原接受的0..99抽样；资格合格仍可能失败。'
    entries = {1: 0xB0DD, 5: 0xB243, 7: 0xB2CD, 8: 0xB31C,
               9: 0xB3B6, 10: 0xB3D0, 12: 0xB466, 14: 0xB50C}
    qualifiers = {
        1: '玩家目标 class0或4；还须实际异侧、距离<6、菜单可用/AP前序。',
        5: '玩家目标必须为军首槽0或10；还须实际异侧与距离<6。',
        7: '玩家目标 class0或4，而且四邻至少一个异侧单位；还须实际异侧与距离<6。',
        8: '玩家目标 class≠5；还须实际异侧与距离<6。忠诚门槛属于施放概率，不属于这段地形资格。',
        9: '玩家施法者 class4或5、与目标正交相邻，目标 class≠5。AI的ID9资格要求目标class5；两条规则分别保留。',
        10: '玩家目标 class3，而且四邻至少一个异侧class3单位；还须实际异侧与距离<6。',
        12: '玩家目标 class3，而且四邻至少一个异侧class3单位；还须实际异侧与距离<6。',
        14: '玩家目标 class≠5，而且四邻至少一个异侧非class5单位；还须实际异侧与距离<6。'}
    effects = {
        1: ['通过概率后计算并饱和扣HP，写042F..0432报告，子状态推进。',
            'HP到0进入实际D6CC地图刷新CALL边界；返回后才进行杀将XP、死者报告与清槽。'],
        5: ['通过概率后读取对侧原raw16效果字0522或0524，按原10..14%和知力项计算损失并饱和扣除。',
            '写042C..042E损失报告，推进子状态；不把火箭名称推断为目标扣兵。'],
        7: ['一次成功gate后，先中心，再左、右、上、下；邻居按slot19→0匹配坐标，再判断阵营。',
            '最高友方重叠槽可挡住更低敌槽；同武将record重复命中保留逐次实时读取。',
            '每次扣兵后以新的累计损失再次奖励XP；不去重、不把多次奖励改成最后一次。'],
        8: ['按目标0628翻侧前记账：人数byte减/加回绕；旧侧总兵减目标low10并饱和0，新侧raw16加法回绕。',
            '翻转目标0628的bit7，清匹配十面缓存slot，切换6FA1策略，调用真实pair10/11 A006→CF3F忠诚helper。',
            '本效果不改城市owner、城市名册、武将byte5位置或record状态。战后政治归属另有流程。'],
        9: ['先执行完整HP损失阶段，再按此刻record计算兵损，最终子状态=7。',
            '死亡需实际D6CC返回后继续；清0664后再次F2D7(FF)按原映射访问6FB4，保留原内部FF路径。'],
        10: ['B8A1生成中心及正交连通敌槽候选；只对其中class3逐个抽样并写0650状态。',
             '条件码保留原side位影响；原核心当前帧的状态可能已随回合推进再次递减，见真实raw值。'],
        12: ['B8A1生成正交连通敌槽候选；只对class3候选逐个执行水攻损失。',
             '每目标使用真实RNG、累积损失，并将新的累计损失再次交经验helper。'],
        14: ['B8A1生成正交连通敌槽候选；对非class5候选逐个执行劫火损失。',
             '每目标使用真实RNG、累积损失和反复XP更新；class5阻断候选扩展。']}
    return [dict(id=i, name=NAMES[i], bank=12, cpu=entries[i], file=16 + 12 * 8192 + entries[i] - 0xA000,
                 qualifier=qualifiers[i], gate=('籠絡专用$B72B：距离<6、目标忠诚<71；按忠诚分档、施法者知力/徳与正等级差构成概率，使用原0..99抽样。' if i == 8 else common),
                 steps=effects[i], scope='实际B02B清结果区之后的玩法体；费用、图形/音频/消息等待由明确调用前序与后缀合同处理。') for i in IDS]


class Parsed(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = []; self.targets = []; self.details = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if 'id' in d: self.ids.append(d['id'])
        if tag == 'a' and 'href' in d: self.targets.append(d['href'])
        if tag == 'img' and 'src' in d: self.targets.append(d['src'])
        if tag == 'details': self.details.append(d)


def main():
    old = (ROOT / 'analysis/phase8/index.html').read_text()
    css = re.search(r'<style>([\s\S]+?)</style>', old).group(1)
    groups, pending, artifact_checks = native()
    individual = read('individual/evidence.json'); area = read('area-conversion/evidence.json')
    runtime_manifest = read('runtime/evidence.json')
    data = dict(flows=flows(), names=NAMES, runtime=groups, pending=pending,
                runtime_manifest={k: runtime_manifest[k] for k in ('schema', 'status', 'summary', 'rom_sha256', 'limits') if k in runtime_manifest},
                receipts={k: receipt(p) for k, p in {'individual':'individual/validation.json',
                    'area':'area-conversion/validation.json', 'targeting':'targeting/validation.json',
                    'integration':'source-integration.json'}.items()},
                death=individual.get('death', {}), candidates=area.get('area_candidate_rules', {}),
                conversion=area.get('conversion_accounting'),
                costs=json.loads((ROOT/'analysis/phase8/effects/evidence.json').read_text()).get('player_AP_cost_table', {}).get('bytes', []),
                excerpts={'individual':excerpt('source/recovered/tactic_individual_effects.py', ('apply','after_death_graphics','death_settlement')),
                          'area':excerpt('source/recovered/tactic_area_conversion.py', ('apply','connected_candidates','_conversion')),
                          'targeting':excerpt('source/recovered/player_tactic_targeting.py', ('eligibility_suffix','can_target'))})
    html = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>16计略、死亡与经验结算 · 第九轮逆向证据</title><style>STYLES</style></head><body><main>
<small>第九轮 · 原ROM只读 · 可读玩法源码、原CPU差分与双跑原核心证据</small><h1>计略效果：范围、转侧、死亡与经验结算</h1>
<nav><a href="../index.html">总入口</a><a href="../phase8/index.html">阶段8</a><a href="README.md">本轮总报告</a><a href="../../source/README.md">源码合同</a><a href="#effects">新增8效果</a><a href="#settlement">结算边界</a><a href="#runtime">原核心前后证据</a></nav>
<p class="note">全部16项计略的玩法效果已接入独立可读源码。本轮补齐1、5、7、8、9、10、12、14，并恢复玩家目标资格与结果/升级消息后缀。<strong>页面只浏览已保存证据，不执行玩法公式、游戏帧、IR或模拟器。</strong>音频、消息 readiness 与地图绘制仍有真实外部服务边界。</p><div class="metrics" id="metrics"></div><p id="receipt-summary"></p>
<h2 id="effects">1 · 新增8效果及施放条件</h2><label for="effect-id">计略：</label><select id="effect-id"></select><pre id="effect-detail"></pre><ol class="steps" id="effect-steps"></ol>
<p>目标资格、成功概率和AP扣款是不同阶段。费用来自原player表；施法动画完成后的精确前序才扣款、清结果区与执行效果。玩家光标资格与AI提案资格各保留原判断。</p>
<details><summary>所选效果的真实可读源码片段</summary><pre id="effect-source"></pre></details><details><summary>全部16项玩家目标资格源码</summary><pre id="targeting-source"></pre></details>
<p><a href="../../source/recovered/tactical_effects_complete.py">全部16效果统一源码</a> · <a href="../../source/recovered/tactical_effects.py">阶段8施放/缓存及8效果</a> · <a href="../../source/recovered/tactic_individual_effects.py">陥穽/火箭/落石源码</a> · <a href="../../source/recovered/tactic_area_conversion.py">共殺/籠絡/連環/水攻/劫火源码</a> · <a href="../../source/recovered/player_tactic_targeting.py">玩家目标资格源码</a></p>
<div class="two"><section><h3>范围候选的原规则</h3><p>共殺是中心与四邻，按邻居坐标选最高slot后再检查敌我。連環、水攻、劫火用B8A1：中心先入列，以右/左/下/上扩展正交连通敌槽；按最低slot找坐标，class5阻断。槽位去重不等于武将record去重。</p><p>损失逐目标累加；每次将<strong>新的累计损失</strong>交经验helper。别名record和升级后数值保留原执行顺序。</p></section><section><h3>籠絡的即时作用</h3><p>先按目标0628所属侧迁移人数/总兵，再翻bit7、清匹配缓存slot、改策略与忠诚。计数借位/总兵饱和、raw16接收加法回绕都保留。</p><p><strong>这个效果没有即时城市名册转属。</strong>不改城市owner、武将位置byte5或record状态；后续战后归属处理单独分析。</p></section></div>
<p><a href="individual/README.md">单体效果说明</a> · <a href="individual/original-ranges.asm">原单体bytes</a> · <a href="individual/evidence.json">单体证据与pins</a> · <a href="area-conversion/README.md">范围/转侧说明</a> · <a href="area-conversion/connected_candidates.asm">B8A1原bytes</a> · <a href="area-conversion/8_conversion.asm">籠絡原bytes</a> · <a href="area-conversion/evidence.json">范围证据与pins</a> · <a href="targeting/validation.json">资格差分回执</a></p>
<h2 id="settlement">2 · 死亡、清槽与升级消息的真实边界</h2>
<ol class="steps"><li><strong>HP到0</strong><br>record11 OR3，保留原兵字节；源码返回D6CC地图刷新CALL依赖。</li><li><strong>真实CALL返回后</strong><br>计算杀将XP、报告死者ID，清六组单位数组/6FA1和首个匹配缓存。</li><li><strong>原结果扫描</strong><br>逐slot请求实际单位图形；队列写入不等于消息已经显示完成。</li><li><strong>真实输入继续</strong><br>查询已发生的等级变化，按原条件排升级/第二通知，再交音频和光标服务。</li></ol>
<p class="note">公开方法 after_death_map_refresh(map_refresh_returned=True) 表示<strong>实际同步CALL已返回</strong>，不表示PPU渲染或异步图形任务完成。False、缺失真实服务或缺失按键会保留等待/依赖。死亡本段不执行城市、君主或军总人数/总兵结算；record状态3的长期政治语义不可由一次截图扩大推断。</p>
<details><summary>死亡CPU前缀、真实服务、后缀的分别计数</summary><pre id="death-detail"></pre></details>
<p><a href="individual/validation.json">单体CPU完整/前缀/后缀回执</a> · <a href="area-conversion/validation.json">范围与转侧CPU回执</a> · <a href="source-integration.json">统一API及结果/升级后缀回执</a> · <a href="settlement/README.md">结算原字节来源</a> · <a href="settlement/evidence.json">结算机器证据与pins</a> · <a href="settlement/original-ranges.asm">扫描/通知原汇编与数据表</a></p>
<h2 id="runtime">3 · 原完整核心：菜单输入、作用与连续结算</h2><p id="runtime-summary"></p><p><a href="runtime/README.md">原核心实验合同与回放方法</a> · <a href="runtime/evidence.json">正式manifest</a> · <a href="runtime/validation.json">原核心汇总回执</a></p><label for="runtime-group">正式实验：</label><select id="runtime-group"></select><label for="runtime-left">前检查点：</label><select id="runtime-left"></select><label for="runtime-right">后检查点：</label><select id="runtime-right"></select>
<div class="screens" id="runtime-screens"><figure><img id="runtime-before" alt="原完整核心前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="runtime-after" alt="原完整核心后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="runtime-transition"></p>
<h3>所选前后检查点的实际字段</h3><div class="scroll"><table><thead><tr><th>字段 / raw编码</th><th>前</th><th>后</th></tr></thead><tbody id="core-fields"></tbody></table></div>
<h3>武将记录：包括清槽后仍可读的原死者record</h3><p>兵word与low10分别列出；record状态是byte11低2位，单位条件是0650，阵营是0628bit7。下面的值全部来自同帧raw文件，未代入公式预测。</p><div class="scroll"><table><thead><tr><th>武将ID</th><th>HP</th><th>兵 raw / low10</th><th>忠诚</th><th>经验 / 等级</th><th>record状态 / byte11</th><th>单位slot / 阵营 / 条件</th><th>位置byte5</th></tr></thead><tbody id="officer-fields"></tbody></table></div>
<details><summary>完整12字节record与单位数组前后值</summary><pre id="runtime-fields"></pre></details><details><summary>准备字段与实际普通按键输入</summary><pre id="runtime-preparation"></pre></details><details><summary>效果确认、二次回放及产物哈希</summary><pre id="runtime-detail"></pre></details><p id="runtime-links"></p>
<p class="note">这些实验是显式准备的原核心fixture：准备值、普通菜单/光标/A输入分别保留。正式实验须二次回放的非空产物byte一致；探索目录不作为实证。PNG、RAM、SRAM与state同源，hash随图片URL固定。它们证明此fixture的实际施放/结算与绘制，不证明完整自然战役或全硬件源码完成。</p>
<details><summary>当前源码与统一API验证范围</summary><pre id="receipt-detail"></pre></details><footer>原bytes、独立玩法源码、原CPU差分、完整核心回放分别计数。IR目录和源码guards不作为原CPU运行例；外部图形/消息/音频前序没有默认完成。</footer>
</main><script>const D=PAYLOAD,$=s=>document.querySelector(s),pretty=v=>JSON.stringify(v,null,2),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),hex=(v,w=2)=>Number(v).toString(16).toUpperCase().padStart(w,'0'),num=v=>v==null?'待回执':Number(v).toLocaleString(),pair=(a,b)=>`${esc(a)} → ${esc(b)}`;
const metricLabels={individual:'单体效果原CPU',area:'范围/转侧原CPU',targeting:'玩家资格原CPU',integration:'统一API原CPU'};$('#metrics').innerHTML=Object.entries(metricLabels).map(([k,label])=>{const r=D.receipts[k],guardCount=r.source_guard_case_count??r.source_guard_count,guards=guardCount==null?'未单列guard计数':'源码guards '+num(guardCount);return`<div class="metric"><small>${label}</small><strong>${num(r.rom_cpu_case_count??r.actual_ROM_CPU_comparison_count)}</strong><small>${esc(r.status||'待回执')} · ${guards}</small></div>`}).join('');$('#receipt-summary').textContent='原CPU例包括各回执声明的完整体、真实依赖前缀和实际服务返回后缀；分别范围见JSON。模块矩阵与集成例互不替代原核心回放。';$('#receipt-detail').textContent=pretty(D.receipts);$('#death-detail').textContent=pretty({death:D.death,individual_receipt:D.receipts.individual});$('#targeting-source').textContent=D.excerpts.targeting;
$('#effect-id').innerHTML=D.flows.map(v=>`<option value="${v.id}">${v.id} · ${esc(v.name)}</option>`).join('');function effect(){const id=Number($('#effect-id').value),v=D.flows.find(v=>v.id===id);$('#effect-detail').textContent=`ID${v.id} ${v.name} · bank${v.bank} CPU$${hex(v.cpu,4)} / file0x${hex(v.file,6)}\n\n玩家目标资格：${v.qualifier}\n\n成功概率：${v.gate}\n\nplayer原AP费用：${D.costs[id]??'待table'}\n范围：${v.scope}`;$('#effect-steps').innerHTML=v.steps.map((s,i)=>`<li><strong>${i+1}</strong><br>${esc(s)}</li>`).join('');$('#effect-source').textContent=D.excerpts[[1,5,9].includes(id)?'individual':'area'];}$('#effect-id').addEventListener('change',effect);effect();
const groups=D.runtime,summary=D.runtime_manifest.summary;$('#runtime-summary').textContent=groups.length?`当前${groups.length}组正式双跑实验、${groups.reduce((a,g)=>a+g.captures.length,0)}个同源截图检查点。${summary?`首跑${num(summary.frames_first_run)}帧，两跑合计${num(summary.frames_both_runs)}帧；${num(summary.nonempty_artifact_hash_checks)}项非空产物哈希一致，${num(summary.excluded_empty_vram_exports)}个空VRAM导出不计入。`:''}${D.pending.length?'待二次回放冻结：'+D.pending.join('、')+'。':''}`:`正式双跑manifest尚在整理；${D.pending.length}组计划实验等待冻结。探索截图未作为正式结论。`;$('#runtime-group').innerHTML=groups.length?groups.map((g,i)=>`<option value="${i}">${esc(g.name)} · ${esc(D.names[g.tactic_id])}</option>`).join(''):'<option value="">待正式双跑回执</option>';
function runtimeOptions(){const g=groups[Number($('#runtime-group').value)];if(!g){$('#runtime-screens').hidden=true;$('#runtime-left').disabled=$('#runtime-right').disabled=true;return;}$('#runtime-screens').hidden=false;$('#runtime-left').disabled=$('#runtime-right').disabled=false;const options=g.captures.map((c,i)=>`<option value="${i}">frame${c.frame??'?'} · ${esc(c.label)}</option>`).join('');$('#runtime-left').innerHTML=$('#runtime-right').innerHTML=options;const at=s=>g.captures.findIndex(c=>c.label===s);$('#runtime-left').value=String(Math.max(0,at('effect-before')));$('#runtime-right').value=String(at(g.name.includes('levelup')?'continuation-1':'effect-generated')>=0?at(g.name.includes('levelup')?'continuation-1':'effect-generated'):g.captures.length-1);runtimeDetail();}
function runtimeDetail(){const g=groups[Number($('#runtime-group').value)];if(!g)return;const l=g.captures[Number($('#runtime-left').value)],r=g.captures[Number($('#runtime-right').value)];if(!l||!r)return;[['before',l],['after',r]].forEach(([name,c])=>{$('#runtime-'+name).src=c.image;const notice=g.manifest_case?.notification_evidence?.find(n=>n.label===c.label);$('#'+name+'-caption').textContent=`${g.name} · ${c.label} · frame${c.frame??'?'}；global${c.global_main}/NMI${c.NMI_scene}，battle${c.battle.join('/')}。PNG sha256=${c.sha256.slice(0,16)}…${notice?'；原画面文字：'+notice.visible_text.join('；'):''}`;});$('#runtime-transition').textContent=`${l.label} → ${r.label}；AP ${l.AP}→${r.AP}，原结果0544 ${hex(l.result)}→${hex(r.result)}。逐帧值见raw记录，不把frame末值当帧内逐指令轨迹。`;const rows=[['行动力0505',l.AP,r.AP],['计略0543',l.tactic,r.tactic],['结果0544',hex(l.result),hex(r.result)],['军粮效果word0522',l.grain_effect_words['0522'],r.grain_effect_words['0522']],['军粮效果word0524',l.grain_effect_words['0524'],r.grain_effect_words['0524']],['结果报告042C..0433',pretty(l.loss_report),pretty(r.loss_report)],['人数/总兵raw0518..051F',pretty(l.side_aggregates_0518_051F),pretty(r.side_aggregates_0518_051F)],['缓存04D8..04DF',pretty(l.cache),pretty(r.cache)]];$('#core-fields').innerHTML=rows.map(([key,a,b])=>`<tr><th>${esc(key)}</th><td>${esc(a)}</td><td>${esc(b)}</td></tr>`).join('');const old=new Map(l.records.map(x=>[x.officer,x])),now=new Map(r.records.map(x=>[x.officer,x])),unit=(c,id)=>{const found=c.units.filter(x=>x.officer===id);return found.length?found.map(x=>`${x.slot} / ${hex(x.side_raw)} / ${hex(x.condition_raw)}`).join('; '):'无活动slot'};$('#officer-fields').innerHTML=[...new Set([...old.keys(),...now.keys()])].sort((a,b)=>a-b).map(id=>{const a=old.get(id),b=now.get(id);if(!a||!b)return'';return`<tr><th>${id}</th><td>${pair(a.HP,b.HP)}</td><td>${pair(a.troops_raw+' / '+a.troops_low10,b.troops_raw+' / '+b.troops_low10)}</td><td>${pair(a.loyalty,b.loyalty)}</td><td>${pair(a.XP+' / '+a.experience_level,b.XP+' / '+b.experience_level)}</td><td>${pair(a.record_status_raw+' / '+hex(a.packed_byte11),b.record_status_raw+' / '+hex(b.packed_byte11))}</td><td>${pair(unit(l,id),unit(r,id))}</td><td>${pair(a.location_raw,b.location_raw)}</td></tr>`}).join('');$('#runtime-fields').textContent=pretty({before:{records:l.records,units:l.units,unit_arrays:l.unit_arrays,resources_0520_0527:l.resources_0520_0527},after:{records:r.records,units:r.units,unit_arrays:r.unit_arrays,resources_0520_0527:r.resources_0520_0527}});const v=g.validation;$('#runtime-preparation').textContent=pretty({controlled_fixture:v.controlled_fixture,natural_gameplay:v.natural_gameplay,parent_state:v.parent_state,parent_sha256:v.parent_sha256,RAM_preparation:v.RAM_preparation,SRAM_preparation:v.SRAM_preparation,rng_preparation:v.rng_preparation,terrain_fixture:v.terrain_fixture,selected_result_cache_or_ack_injection:v.selected_tactic_result_request_cache_animation_ack_injection,readiness_or_ack_injection:v.readiness_or_ack_injection,actual_input_plan:v.input_plan});$('#runtime-detail').textContent=pretty({verified_effects:v.verified_effects,repeat:g.repeat,core:v.core,frames:v.frames,limits:v.limits,death_settlement_evidence:g.manifest_case?.death_settlement_evidence,notification_evidence:g.manifest_case?.notification_evidence,formal_manifest:D.runtime_manifest});$('#runtime-links').innerHTML=[[g.receipt,'实验回执'],[g.repeat_receipt,'二次回放哈希'],[l.image.split('?')[0],'前原PNG'],[r.image.split('?')[0],'后原PNG'],[l.RAM,'前rawRAM'],[r.RAM,'后rawRAM'],[l.SRAM,'前rawSRAM'],[r.SRAM,'后rawSRAM']].map(([path,name])=>`<a href="${esc(path)}">${name}</a>`).join(' · ');}
$('#runtime-group').addEventListener('change',runtimeOptions);$('#runtime-left').addEventListener('change',runtimeDetail);$('#runtime-right').addEventListener('change',runtimeDetail);runtimeOptions();
</script></body></html>'''
    html = html.replace('STYLES', css).replace('PAYLOAD', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'index.html').write_text(html)
    parsed = Parsed(); parsed.feed(html)
    assert len(parsed.ids) == len(set(parsed.ids))
    assert all('open' not in d for d in parsed.details)
    script = re.search(r'<script>([\s\S]+)</script>', html).group(1)
    checked = subprocess.run(['node', '--check', '--input-type=commonjs'], input=script, text=True, capture_output=True)
    assert checked.returncode == 0, checked.stderr
    missing = []
    for target in parsed.targets:
        if target.startswith('#'): assert target[1:] in parsed.ids
        elif not (OUT / target.split('?', 1)[0]).is_file(): missing.append(target)
    assert missing in ([], ['README.md']), missing
    for g in groups:
        for c in g['captures']:
            for field in ('image', 'RAM', 'SRAM'):
                assert (OUT / c[field].split('?', 1)[0]).is_file()
    print(json.dumps(dict(output='analysis/phase9/index.html', html_bytes=len(html.encode()),
                          html_sha256=sha(OUT/'index.html'), remaining_effect_options=len(IDS),
                          total_effect_source_ids=16, formal_runtime_groups=len(groups),
                          formal_screenshots=sum(len(g['captures']) for g in groups), pending=pending,
                          formal_artifact_hash_checks=artifact_checks, unique_ids=len(parsed.ids),
                          closed_details=len(parsed.details), JS_syntax='passed',
                          links='passed_except_pending_totalREADME' if missing else 'passed'), ensure_ascii=False))


if __name__ == '__main__':
    main()
