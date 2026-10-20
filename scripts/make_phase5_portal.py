#!/usr/bin/env python3
"""Build the phase5 evidence browser from retained catalogs and real snapshots."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from source.recovered.domestic_ai import CityRecord

def read(name):
    return json.loads((ROOT / 'analysis/phase5' / name).read_text())

def main():
    proof = read('verification.json')
    schema = read('domestic-ai/city-schema.json')
    turns = read('domestic-ai/turn-controllers.json')['controllers']
    domestic = read('domestic-ai/evidence.json')['dispatches']
    controllers = []
    labels = {'calendar': '月轮 · 0401', 'turn_events': '回合事件 · 0401', 'ruler_ai_scene': '君主AI桥接 · 0401'}
    for c in turns:
        pair = 25
        controllers.append({'name': labels[c['name']], 'entry': c['entry'], 'entry_kind': 'controller', 'rows': [
            {'id': i, 'entry': target, 'bank': pair if target < 0xC000 else pair + 1,
             'file': 16 + (pair if target < 0xC000 else pair + 1)*8192 + target - (0xA000 if target < 0xC000 else 0xC000)}
            for i, target in enumerate(c['targets'])]})
    for c in sorted(domestic, key=lambda c: c['call_pc']):
        name = '内政AI进度 · 6F5B' if c['call_pc'] == 0xA039 else '内政AI三策略'
        controllers.append({'name': name, 'entry': c['call_pc'], 'entry_kind': 'dispatch', 'rows': [
            {'id': i, 'entry': target, 'bank': 10 if target < 0xC000 else 11,
             'file': 16 + (10 if target < 0xC000 else 11)*8192 + target - (0xA000 if target < 0xC000 else 0xC000)}
            for i, target in enumerate(c['targets'])]})
    sram = (ROOT / 'analysis/phase5/runtime/city-info/menu-0-sram.bin').read_bytes()
    cities = []
    for city_id in range(30):
        c = CityRecord(sram[city_id*32:city_id*32 + 32])
        cities.append({'id': city_id, 'gold': c.gold, 'grain': c.grain, 'population': c.population_hundreds,
                       'populationDisplay': c.displayed_population, 'populationIncome': c.income_population_hundreds,
                       'land': c.land, 'landDisplay': c.displayed_land, 'landIncome': c.income_land,
                       'industry': c.industry, 'industryDisplay': c.displayed_industry, 'industryIncome': c.income_industry,
                       'prevention': c.disaster_prevention, 'governance': c.governance,
                       'reserve': c.reserve_troops, 'treasures': c.treasures, 'roster': c.roster})
    data = {'controllers': controllers, 'cities': cities, 'fields': schema['fields'],
            'troops': read('troops/validation.json')['overflow_examples'],
            'quotes': read('terrain/validation.json')['selector_disagreement_examples'],
            'proof': {'romCases': proof['rom_differential_case_count'], 'artifactChecks': proof['terrain_artifact_checks']}}
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>转属、内政AI与兵数 · 第五轮逆向证据</title>
<style>*{box-sizing:border-box}body{background:#f6f5f1;color:#242721;font:16px/1.65 system-ui,sans-serif;margin:0}main{max-width:1180px;margin:auto;padding:32px 24px}h1{font-size:32px;line-height:1.3}h2{margin-top:36px}a{color:#285641}nav{display:flex;gap:18px;flex-wrap:wrap;border-block:1px solid #c9ccbe;padding:14px 0}code{font:13px/1.5 ui-monospace,monospace}button,select,input{font:inherit;padding:8px;border:1px solid #a9b49a;background:white;color:inherit;margin:4px 12px 4px 0}input{max-width:100%}.note{border-left:4px solid #a18a3b;padding-left:16px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #d9ddce;vertical-align:top}th{background:#eceee6}.nowrap td{white-space:nowrap}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eceee6;padding:16px;font-size:13px}img{image-rendering:pixelated;max-width:100%;height:auto}small{color:#64695e}.screens{display:flex;gap:24px;flex-wrap:wrap}.screens figure{margin:0;max-width:512px}.screens figure img{width:512px}figcaption{font-size:14px;color:#64695e}footer{border-top:1px solid #c9ccbe;margin-top:36px;padding-top:16px;color:#64695e}@media(max-width:600px){main{padding:20px 16px}h1{font-size:26px}select{max-width:100%}}</style>
<main><small>第五轮 · 原ROM只读 · 逆向复原源码</small><h1>武将转属、内政AI与兵数高位</h1>
<nav><a href="../index.html">总入口</a><a href="README.md">本轮报告</a><a href="../../source/README.md">可读源码与使用说明</a><a href="verification.json">联合验证</a><a href="../phase4/index.html">战斗/单挑状态机</a><a href="../../build/三国志2超级版-逆向分析.zip">完整归档</a></nav>
<p class="note">已恢复16个名册/忠诚/继承服务，内政AI三策略和月轮、回合事件、君主AI的37个子入口（32个不同目标地址）。原驻军程序可产生1098，而武将列表低10位显示74；地形1的图块与规则已确认，正式名称仍未知。<br><strong>83,702个原ROM CPU差分案例，0失败</strong>，其中13个调度案例止于明确边界；另有892项地形图像/证据检查。</p>
<h2>1 · 两套调度，保留原异步等待</h2>
<pre>主循环 007A=2 → E17D → pair10/11 A00F → 6F5B进度 → A1BC三策略
NMI    0078=2 → F8EF → pair27/28 A000 → 城市界面
pair25/26 C773 → 准备君主/预算 → 请求全局AI → 等待6F8B事件
安装继承人请求FC；没有继承人请求FB → host计时/显示依赖 → 原代码写1才继续</pre>
<p>源码提供直接控制入口；银行映射不自动准备E1/E2/E3缓存、OAM或renderer上下文。缺少hook会报出入口。13例边界为reset1、PPU6、NMI6，没有把等待伪装成完成。受控host计时段逐次对照：FC第480次、FB第240次调用由原CBBF写1；前置renderer仍外置，调用次数不是帧数。</p>
<label for="controller">查看控制表：</label><select id="controller"></select><label for="entry-filter">筛选入口/bank：</label><input id="entry-filter" placeholder="例如 C7、25">
<small id="entry-count"></small><div class="scroll"><table class="nowrap"><thead><tr><th>子ID</th><th>CPU入口</th><th>物理bank</th><th>ROM文件偏移</th></tr></thead><tbody id="entries"></tbody></table></div>
<p><a href="domestic-ai/README.md">策略、发展、付款、年度收入与调度完整说明</a> · <a href="domestic-ai/turn-controllers.json">全部嵌套表</a> · <a href="../../source/recovered/domestic_ai.py">domestic_ai.py</a></p>
<h2>2 · 城市32字节：原值、显示值和税收值</h2>
<p>数据来自未注入内存的城市菜单快照。人口以百人为单位；土地/产业初始9999，但三位UI显示999、税收使用783。+16通过原「タカラ」文字、获得和卖出路径确认是宝物数。</p>
<label for="city">城市ID：</label><select id="city"></select><div class="scroll"><table><thead><tr><th>字段/偏移</th><th>原始值</th><th>显示值</th><th>税收/用途</th></tr></thead><tbody id="city-values"></tbody></table></div>
<details><summary>全部字段及确认范围</summary><pre id="schema"></pre></details>
<p><a href="domestic-ai/city-schema.json">机器码与UI模板证据</a> · <a href="domestic-ai/resource16-fixtures/message-34-zoom.png">原宝物文字fixture</a></p>
<h2>3 · 真正的转属与继承写入</h2>
<div class="scroll"><table><thead><tr><th>入口</th><th>作用</th><th>保留的区别</th></tr></thead><tbody>
<tr><td>bank10 A006/A009/A00C</td><td>仅忠诚调整</td><td>不会自动改owner或名册；D61E原字节是RTS</td></tr>
<tr><td>bank27 ACF0 / AD41</td><td>招入 / 名册组迁移</td><td>招入不自动删其它城同ID；迁移保留原兵数word</td></tr>
<tr><td>bank25 BDBB</td><td>状态OR3、删名册、压紧</td><td>空城保留owner byte高5位</td></tr>
<tr><td>bank26 C099</td><td>清状态、写所在地、名单左移</td><td>空城owner整byte写7；D4对话外置</td></tr>
<tr><td>bank11 CA87/CB05/CB52</td><td>家属优先或最大徳继承</td><td>电脑离队仍留名单ID；FC/FB等待实际确认</td></tr>
<tr><td>bank25 BF85 / bank26 C25D/C289</td><td>玩家继承、城首及随员</td><td>手动/自动驻城写入不同；离队真实删除ID</td></tr>
</tbody></table></div><p><a href="transfer/README.md">16个服务与原程序quirks</a> · <a href="transfer/evidence.json">19段真实字节证据</a> · <a href="../../source/recovered/officer_transfer.py">officer_transfer.py</a></p>
<h2>4 · 兵数高位有数值来源</h2>
<p>选择实际原CPU验证过的拨兵输入。表中是右键拨入路径；不把高位命名为训练度/状态flag。</p>
<label for="troop-case">受控输入：</label><select id="troop-case"></select><pre id="troop-result"></pre>
<div class="screens"><figure><img src="troops/core-fixture/allocation-overflow.png" alt="原ROM驻军分配曹操行显示1098"><figcaption>原核心2050帧回放中的第1766帧：界面显示1098。仅预置两个SRAM word；RAM与ROM均不改。</figcaption></figure><figure><img src="troops/core-fixture/committed-overflow.png" alt="原ROM拨兵确认退出后的地图"><figcaption>第2050帧退出后的地图；配对SRAM仍为1098，画面本身不显示该兵数。两个回放的三个检查点、12个文件hash逐项一致。</figcaption></figure></div>
<p><a href="troops/README.md">分路径读写与溢出机制</a> · <a href="troops/core-fixture/validation.json">输入/补丁/检查点</a> · <a href="troops/core-fixture/replay-validation.json">重复回放hash</a> · <a href="../../source/recovered/troop_fields.py">troop_fields.py</a></p>
<h2>5 · 地形1：335格、7种图块，名称仍未知</h2>
<div class="screens"><figure><img src="terrain/core-views/class1-seven-raw-tiles-56490c4d22fc.png" alt="地形1七种原metatile裁切"><figcaption>7种原metatile；颜色和像素不能单独证明道路/沙漠等正式名称。</figcaption></figure><figure><img src="terrain/core-views/city5-map-e4613f07e4f9-fullframe-x3.png" alt="城市5原核心地形地图fixture"><figcaption>原核心RAM fixture，城市与视口明确设置。三个地图共122个16×16可见格逐像素核对；正式地形名称未证实。</figcaption></figure></div>
<p>AI代码两次读取武将byte8，按byte8≥3选表；玩家按百人cache≥6选表。选择对照案例查看同一地形1的不同成本：</p>
<label for="quote-case">原CPU报价案例：</label><select id="quote-case"></select><pre id="quote-result"></pre>
<details><summary>普通攻击背景的独立像素证据</summary><img src="terrain/attack-view/class1-attack-background-deff5d0aa386-fullframe-x3.png" alt="原核心地形1普通攻击背景"><p>仅验证背景640个8×8tile；本fixture不证明自然单位/菜单或完整普通攻击流程。</p></details>
<p><a href="terrain/README.md">地形完整报告</a> · <a href="terrain/validation.json">成本/图像验证</a> · <a href="../../source/recovered/terrain_semantics.py">terrain_semantics.py</a></p>
<footer>CPU字段等价、控制图覆盖、原核心受控回放和自然战役可达性是不同证据。当前源码仍缺完整PPU/IRQ/音频、部分外部helper与游戏主循环；不是原开发源码或完整可玩的重制游戏。</footer></main>
<script>const data=PAYLOAD;const $=s=>document.querySelector(s);const hex=(n,w=4)=>n.toString(16).toUpperCase().padStart(w,'0');
const controller=$('#controller'),filter=$('#entry-filter');controller.innerHTML=data.controllers.map((c,i)=>`<option value="${i}">${c.name} · ${c.rows.length}项</option>`).join('');
function entries(){const c=data.controllers[controller.value],q=filter.value.trim().toLowerCase();const rows=c.rows.filter(r=>`${r.id} ${hex(r.entry)} ${r.bank} ${hex(r.file,6)}`.toLowerCase().includes(q));$('#entries').innerHTML=rows.map(r=>`<tr><td>${r.id}</td><td><code>$${hex(r.entry)}</code></td><td>${r.bank}</td><td><code>0x${hex(r.file,6)}</code></td></tr>`).join('');$('#entry-count').textContent=`${rows.length} / ${c.rows.length}项；${c.entry_kind==='dispatch'?'分派调用点（AI入口 $A00F）':'控制入口'} $${hex(c.entry)}`;}controller.addEventListener('change',entries);filter.addEventListener('input',entries);entries();
const city=$('#city');city.innerHTML=data.cities.map(c=>`<option value="${c.id}">${c.id}</option>`).join('');city.value='11';function cityValues(){const c=data.cities[city.value],rows=[['金 +2',c.gold,c.gold,'四月收入'],['米 +4',c.grain,c.grain,'十月收入'],['人口 +6',c.population,c.populationDisplay,c.populationIncome+' 百人'],['土地 +8',c.land,c.landDisplay,c.landIncome+' 收米等级'],['防災 +10',c.prevention,c.prevention,'byte'],['統治度 +11',c.governance,c.governance,'治理率分档'],['ヒカエ +12',c.reserve,c.reserve,'后备兵'],['産業 +14',c.industry,c.industryDisplay,c.industryIncome+' 收金等级'],['タカラ +16',c.treasures,c.treasures,'宝物数'],['名册 +17..26',c.roster.join(', '),'FF空槽','10槽']];$('#city-values').innerHTML=rows.map(r=>'<tr>'+r.map(v=>`<td>${v}</td>`).join('')+'</tr>').join('');}city.addEventListener('change',cityValues);cityValues();$('#schema').textContent=JSON.stringify(data.fields,null,2);
const tc=$('#troop-case');tc.innerHTML=data.troops.map((c,i)=>`<option value="${i}">兵${c.input_troops} / 后备${c.input_reserve}</option>`).join('');function troop(){const c=data.troops[tc.value];$('#troop-result').textContent=`原兵数 ${c.input_troops}，后备 ${c.input_reserve} → 右键拨入\n输出 raw ${c.output_raw_troops} (0x${hex(c.output_raw_troops)})，后备 ${c.output_reserve}\n列表低10位 ${c.output_low10}；原高6位 ${c.output_upper6}\n证据：实际原6502分配核心，显式受控输入。`;}tc.addEventListener('change',troop);troop();
const qc=$('#quote-case');qc.innerHTML=data.quotes.map((c,i)=>`<option value="${i}">byte8=${c.byte8}，byte9=${c.byte9}，cache=${c.player_cache}</option>`).join('');function quote(){const c=data.quotes[qc.value];$('#quote-result').textContent=`兵低10位 ${c.troops_low10} / 百人cache ${c.player_cache}\nAI成本 ${c.ai_cost}（byte8≥3选第一表）\n玩家成本 ${c.player_cost}（cache≥6选第一表）\n地形1正式名称：未确认。`;}qc.addEventListener('change',quote);quote();</script></html>'''
    html = html.replace('PAYLOAD', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    import re
    out = ROOT / 'analysis/phase5'
    # Content hashes keep repeat captures from displaying an older browser image.
    html = re.sub(r'(<img src=")([^"]+)', lambda m: m[1] + m[2] + '?sha=' + hashlib.sha256((out / m[2]).read_bytes()).hexdigest()[:12], html)
    (out / 'index.html').write_text(html)
    print('Created phase5 evidence browser: five control tables, thirty cities and bounded troop/terrain cases')

if __name__ == '__main__':
    main()
