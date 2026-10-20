#!/usr/bin/env python3
"""Build a standalone navigation and raw-table viewer from retained evidence."""
from pathlib import Path
import json
from html import escape
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from recovered.officers import OfficerRecord
tables=json.loads((ROOT/'analysis/game_data/recovered_tables.json').read_text())
known={0:'阿会喃',2:'伊籍',30:'夏侯惇',38:'関羽',47:'甘寧',55:'姜維',109:'諸葛亮',222:'劉備'}
rows=[]
for v in tables['second_table']['records']:
    i=v['id'];b=v['bytes'];name=known.get(i,'未转写');o=OfficerRecord(bytes(b))
    rows.append(f'''<tr data-search="{i} {name} {v['raw_hex'].lower()}">
    <td>{i:03d}</td><td><img class="name" src="assets/names/name-{i:03d}.png" alt="ID {i} 原始姓名字形"><small>{name}</small></td>
    <td><code>{escape(v['rom_offset'])}</code><small>{escape(v['runtime_ram_address'])} RAM</small></td>
    <td>{o.health}</td><td>{o.martial_strength}</td><td>{o.intellect}</td><td>{o.loyalty_text()}</td><td>{o.virtue}</td>
    <td>{o.experience_display}<small>raw {o.experience_raw}</small></td><td>{o.troops_display}<small>raw {o.troops_raw}</small></td>
    <td>{o.weapon_id} / {o.armor_id}</td><td>{o.level_display} / {o.terrain_glyph or '未确认'}</td>
    <td><code>{escape(v['raw_hex'])}</code></td></tr>''')
city_rows=[]
for v in tables['first_table']['records']:
    city_rows.append(f"<tr><td>{v['id']:02d}</td><td><code>{v['rom_offset']}</code></td><td><code>{v['runtime_ram_address']}</code></td><td><code>{v['raw_hex']}</code></td></tr>")
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三国志2超级版 · ROM 逆向证据</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f6f5f1;color:#242721;font:16px/1.65 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:40px 24px}h1{font-size:32px;line-height:1.3}h2{margin-top:40px}a{color:#285641}code{font:13px/1.7 ui-monospace,monospace}small{display:block;color:#64695e}nav{display:flex;gap:18px;flex-wrap:wrap;border-block:1px solid #c9ccbe;padding:18px 0}.note{border-left:4px solid #a18a3b;padding-left:16px}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px 9px;text-align:left;border-bottom:1px solid #d9ddce;vertical-align:middle;white-space:nowrap}th{background:#eceee6}.name{height:32px;image-rendering:pixelated;display:block}input{font:inherit;padding:10px;width:min(100%,420px);border:1px solid #a9b49a;background:#fff}summary{cursor:pointer}footer{margin-top:40px;font-size:14px;color:#64695e}@media(max-width:600px){main{padding:24px 16px}h1{font-size:26px}}
</style><main><small>本地分析 · 2026-10-13 · REA 6.4.0 + Ghidra 12.1.4 + 6502 适配</small>
<h1>三国志2超级版<br>ROM 结构、代码、资源与数据证据</h1>
<p>524,304 字节；32 个 8 KiB PRG 银行；256 KiB CHR，16,384 个 tile。已提取全部原始字节并完成一致重建；关键逻辑已核对，完整游戏语义尚未恢复。</p>
<p><code>SHA-256 26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82</code></p>
<nav><a href="phase7/index.html">战术AI主控制器与决策</a><a href="phase7/README.md">本轮报告</a><a href="phase6/index.html">归属/灭亡与全局循环</a><a href="phase5/index.html">转属/内政AI与兵数</a><a href="phase4/index.html">战斗/单挑状态机</a><a href="../source/README.md">可读源码</a><a href="../README.md">中文总报告</a><a href="assets/index.html">全部图形</a><a href="assets/names/index.html">237 张姓名图</a><a href="officer_fields/README.md">字段证据</a><a href="names_terrain/README.md">计略和地形</a><a href="ai/README.md">AI</a><a href="verification.json">首轮验证</a></nav>
<h2>如何阅读这些结果</h2><p class="note">.byte 源可以逐字节重建 ROM；它不是原始游戏源码。REA/Ghidra 已分析固定 bank31 与八组银行对，候选伪代码仍需校正内联分派和跨银行约定。可读源码另提供经过机器码对照的计算函数与提升后的状态控制模型。灰度图片是诊断配色，不是真实游戏截图。</p>
<ul><li>已按原 ROM 界面确认：体、武、知、忠、徳、経験与兵。忠=100时显示 --。</li><li>経験显示为 raw/50，兵按低10位显示；武器/防具合存在 byte10。</li><li>战斗概率、损失、经验升级、单挑数值及战斗 AI 已整理为可执行 Python 和可编译 C11 计算库。</li><li>16个计略名称已绑定实际执行ID；战斗16主状态与单挑22主状态的合法分派及控制分支已整理。外部依赖及剩余字段含义保留证据等级。</li></ul>
<h2>第七轮：战术AI主控制器与决策</h2><p><a href="phase7/index.html">查看完整有界控制图与自然AI行动</a>：全局4通过真实8/9银行进入A02D，8策略/16计略条件，独立扫描、两轴贪心移动/AP报价及提案消费。<a href="phase7/verification.json">本轮验证</a>记录9,806项主体原CPU对照、255项guard与44项整合检查；原模拟器无注入700帧实际走过AI四次移动与换方。</p>
<h2>第六轮：城市归属、势力灭亡与全局循环</h2><p><a href="phase6/index.html">查看控制图与原模拟器证据</a>：13个已发现归属写入点、独立归属事务、君主FF跳过/灭亡、30城统一与75分结局；15项主循环、9项NMI场景、6模式结局与17个合法组合。<a href="phase6/verification.json">该轮验证</a>分开记录有界原CPU对照、源码拒绝与整机重复产物。</p>
<h2>第五轮：转属、内政AI与数值字段</h2><p><a href="phase5/index.html">查看交互证据</a>：16个名册/忠诚/继承服务、城市32字节schema、AI三策略、月轮等调度的37个子入口，以及原驻军1098溢出回放。<a href="phase5/verification.json">83,702个原ROM差分案例</a>通过，13个调度例明确止于reset/PPU/NMI边界。</p><h2>第四轮：独立单挑、战后与村落规则</h2><p><a href="phase4/index.html">打开交互式状态机浏览器</a>，按主状态查看所有子入口、CPU/bank/文件偏移、状态写入和依赖。战斗与单挑共享RAM的可读入口是 <a href="../source/recovered/game_engine.py">game_engine.py</a>。</p><img src="runtime/phase3/battle-tactics-true.png" alt="原ROM真实计略菜单" style="width:512px;max-width:100%;image-rendering:pixelated">
<h2>237 条武将记录：已确认的属性</h2><p>保留原 ROM 的「徳」名称。姓名图按游戏代码还原；只转写已检查的样本。地形栏字形为平/山/水，具体适性规则见字段报告。经验和兵同时保留显示值与原始值。</p>
<label for="filter">筛选 ID、已转写姓名或十六进制字节：</label><br><input id="filter" placeholder="例如 38、関羽、E8 03"><small id="count">237 / 237 条</small>
<div class="table"><table id="generals"><thead><tr><th>ID</th><th>姓名字形</th><th>ROM / RAM</th><th>体</th><th>武</th><th>知</th><th>忠</th><th>徳</th><th>経</th><th>兵</th><th>武器/防具ID</th><th>Lv/地形</th><th>全部 12 字节</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<h2>第一表：30 条 × 32 字节</h2><details><summary>展开城市原始表（字段见第五轮schema）的全部原始记录</summary><div class="table"><table><thead><tr><th>ID</th><th>ROM</th><th>RAM</th><th>32 字节</th></tr></thead><tbody>'''+''.join(city_rows)+'''</tbody></table></div></details>
<h2>完整模拟器中的原 ROM 画面</h2><p>Nestopia 原文件回放，使用实际 PPU/IRQ 渲染；这些画面无需改变 ROM 或 RAM。人工操作已保存为可重复输入计划。下图是武器店属性列表，体/武/知/忠/徳/経的标签和数值可直接核对。</p><img src="runtime/military-selection.png" alt="原ROM武器店属性列表" style="width:512px;max-width:100%;image-rendering:pixelated">
<h2>覆盖与剩余问题</h2><p>已增加战斗/单挑/全局/结局控制图、可执行控制模型、16计略名称、移动地形成本与原模拟器回放。源码中的外部helper必须明确提供；完整PPU/IRQ/音频及银行内部分场景主体仍有缺口。兵高位数值溢出已有实证；独立flag语义与地形1正式名称仍未确认。控制图完整与整机重制是不同验证范围。C/Python 是本次复原实现，不是原作者源码。</p>
<footer>输入文件只读；全部偏移包含 16 字节 iNES 头。可切换 CPU 地址需同时提供 bank。</footer></main>
<script>const input=document.getElementById('filter');const rows=Array.from(document.querySelectorAll('#generals tbody tr'));input.addEventListener('input',()=>{const q=input.value.trim().toLowerCase();let n=0;for(const r of rows){r.hidden=!r.dataset.search.toLowerCase().includes(q);if(!r.hidden)n++}document.getElementById('count').textContent=n+' / 237 条'});</script></html>'''
(ROOT/'analysis/index.html').write_text(html)
print('analysis/index.html: 237 linked officer records, 30 first-table records')
