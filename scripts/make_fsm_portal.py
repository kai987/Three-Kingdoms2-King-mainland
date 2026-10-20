#!/usr/bin/env python3
"""Build a searchable, source-backed state-machine browser from ROM catalogs."""
import json,hashlib,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
battle=json.loads((ROOT/'analysis/battle_fsm/state-catalog.json').read_text())
attack=json.loads((ROOT/'analysis/attack_fsm/state-catalog.json').read_text())
duel=json.loads((ROOT/'analysis/duel_fsm/state_machine.json').read_text())
machines=[]
for title,data,pair in [('战斗',battle,12),('普通攻击',attack,14),('单挑',duel,23)]:
    states=[]
    for state in data['states']:
        handlers=[]
        for h in state.get('substates',state.get('handlers',[])):
            entry=h.get('entry_cpu',h.get('entry'))
            bank=h.get('entry_bank',pair if entry<0xC000 else pair+1)
            base=0xA000 if bank==pair else 0xC000
            handlers.append({'substate':h['substate'],'entry':f'${entry:04X}',
                             'bank':bank,'file':f'0x{16+bank*8192+entry-base:06X}',
                             'instructions':h.get('node_count',h.get('instruction_count')),
                             'conditions':h.get('conditions',[]),
                             'writes':h.get('state_writes',h.get('writes',[])),
                             'dependencies':h.get('dependencies',h.get('hooks',[]))})
        entry=state.get('entry_cpu',state.get('entry'))
        states.append({'id':state['state'],'name':state.get('label_cn',state['name']),'entry':f'${entry:04X}',
                       'handlers':handlers,'substate_count':state.get('substate_count')})
    machines.append({'title':title,'states':states})
service_path=ROOT/'analysis/phase4/terrain/service-controller.json'
if service_path.exists():
    service=json.loads(service_path.read_text())
    states=[]
    for h in service['handlers']:
        states.append({'id':h['substate'],'name':h['name'],'entry':f"${h['entry']:04X}",
            'handlers':[{'substate':h['substate'],'entry':f"${h['entry']:04X}",'bank':h['bank'],
            'file':f"0x{h['file']:06X}",'instructions':h['instruction_count'],
            'conditions':h.get('conditions',[]),'writes':h['state_writes'],
            'dependencies':h.get('hooks',[])}], 'substate_count':1})
    machines.append({'title':'村落服务','level':'子状态','states':states})
payload=json.dumps(machines,ensure_ascii=False).replace('</','<\\/')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>战斗与单挑状态机 · ROM证据</title>
<style>*{box-sizing:border-box}body{background:#f6f5f1;color:#242721;font:16px/1.6 system-ui,sans-serif;margin:0}main{max-width:1200px;margin:auto;padding:32px 24px}a{color:#285641}h1{font-size:30px}code{font:13px/1.5 ui-monospace,monospace}nav{display:flex;gap:18px;flex-wrap:wrap;border-block:1px solid #c9ccbe;padding:14px 0}button,select,input{font:inherit;padding:8px;margin:4px 10px 4px 0;border:1px solid #a9b49a;background:white;color:inherit}button[aria-pressed=true]{background:#285641;color:white}.note{border-left:4px solid #a18a3b;padding-left:16px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #d9ddce;white-space:nowrap}th{background:#eceee6}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eceee6;padding:16px;font-size:12px}img{image-rendering:pixelated;max-width:100%}small{color:#64695e}.screens{display:flex;gap:20px;flex-wrap:wrap}.screens figure{margin:0;max-width:512px}footer{margin-top:32px;color:#64695e}@media(max-width:600px){main{padding:20px 16px}h1{font-size:25px}}</style>
<main><small>第四轮 · 独立游戏规则、控制图与原 ROM 对照</small><h1>战斗与单挑：状态机与可读规则</h1>
<nav><a href="../index.html">分析总入口</a><a href="README.md">本轮报告</a><a href="../../source/README.md">可读源码</a><a href="../battle_fsm/README.md">战斗状态机</a><a href="../attack_fsm/README.md">攻击场景</a><a href="../duel_fsm/README.md">单挑状态机</a><a href="../names_terrain/README.md">名称和地形证据</a></nav>
<p class="note">战斗以 $0500/$0501 分派，普通攻击场景以 $0540/$0541 分派，单挑以 $04A8/$04A9 分派。它们由 NMI 的 $0078 场景选择推进；$007A 是另一层全局状态。本地控制分派之外，战斗主9新增bank9的10项村落服务子状态。单挑AI、戦術、退却/投降、战后名册处理与29个固定服务已有独立源码；显示和转属等剩余依赖见报告。</p>
<h2>本轮新增的可读规则</h2><p>单挑的牽制・退却・攻撃・投降・戦術・データ・捨身攻撃与子菜单「せっとく」「ばとう」已用原字形确认。战后选项30是「ざいや」（在野）。村落根据独立坐标表提供米屋、武器屋与病院服务；地形6/7/8按平地计移动成本。</p><nav><a href="duel/README.md">单挑AI与結果</a><a href="postbattle/README.md">战后名册与在野</a><a href="terrain/README.md">地形与村落服务</a><a href="services/README.md">独立固定服务</a><a href="verification.json">本轮验证</a></nav><div class="screens"><figure><img src="terrain/duel-menu-atlas.png" alt="原单挑九项动作字形"><figcaption>动作类别0..8：原CHR字形</figcaption></figure><figure><img src="postbattle/synthetic-ui/option30-cursor-fullframe-x3-738bbeec98aa.png" alt="原战后在野选项"><figcaption>明确注入的原核心fixture：目的地30「ざいや」</figcaption></figure></div><h2>逐状态查看原入口与写入</h2><div id="tabs"></div><label><span id="state-label">主状态</span> <select id="state"></select></label><input id="filter" placeholder="筛选子状态、CPU地址或bank"><p id="info"></p><div class="scroll"><table><thead><tr><th>子状态</th><th>CPU入口</th><th>物理bank</th><th>ROM文件偏移</th><th>控制指令</th><th>写入证据</th><th>依赖</th></tr></thead><tbody id="body"></tbody></table></div><details><summary>展开本状态的原始控制证据</summary><pre id="details"></pre></details>
<h2>16 个计略名称</h2><p>名称来自 ROM 字形，菜单索引 $0580 → 选择值 $0543 → 执行表 $B02B。ID 顺序保持原程序编码。</p><img src="../names_terrain/tactics16.png" alt="ROM中16个计略名称字形"><p><a href="../names_terrain/README.md">查看每项菜单/指针/执行入口对应关系</a></p>
<h2>原 ROM 战斗回放</h2><p>从冷启动到计略菜单的 7,738 帧输入已保存，无 ROM 改动或 RAM 注入。9 个检查点画面和 SRAM 一致；CPU RAM 有 8–26 字节差异，原始差异计数保留。</p><div class="screens"><figure><img src="../runtime/phase3/battle-tactics-true.png" width="512" alt="真实ROM计略菜单"><figcaption>曹操的前10项计略菜单</figcaption></figure><figure><img src="../runtime/phase3/battle-camera-right2.png" width="512" alt="真实ROM战场地形"><figcaption>山、水、森林、平地与城的真实战场画面</figcaption></figure></div>
<footer>原文件只读。此页的代码/文件偏移可追溯到保留的 ROM 与汇编；合成地形 fixture 在报告中单独标注。</footer></main>
<script>const data=PAYLOAD;let machine=0;
const state=document.querySelector('#state'),body=document.querySelector('#body'),filter=document.querySelector('#filter');
const esc=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function render(){const s=data[machine].states[Number(state.value)];document.querySelector('#info').textContent=data[machine].title+' '+(data[machine].level||'主状态')+' '+s.id+' · '+s.name+' · '+s.entry+' · '+s.handlers.length+' 个展开子入口';document.querySelector('#details').textContent=JSON.stringify(s,null,2);const q=filter.value.toLowerCase();body.innerHTML=s.handlers.filter(h=>JSON.stringify(h).toLowerCase().includes(q)).map(h=>'<tr><td>'+h.substate+'</td><td><code>'+h.entry+'</code></td><td>'+h.bank+'</td><td><code>'+h.file+'</code></td><td>'+h.instructions+'</td><td>'+h.writes.length+'</td><td>'+h.dependencies.length+'</td></tr>').join('');}
function choose(i){machine=i;document.querySelector('#state-label').textContent=data[i].level||'主状态';state.innerHTML=data[i].states.map((s,n)=>'<option value="'+n+'">'+s.id+' · '+esc(s.name)+'</option>').join('');document.querySelectorAll('#tabs button').forEach((b,n)=>b.setAttribute('aria-pressed',n===i));filter.value='';render();}
document.querySelector('#tabs').innerHTML=data.map((m,i)=>'<button type="button" onclick="choose('+i+')" aria-pressed="false">'+m.title+' · '+m.states.length+' '+(m.level||'主状态')+'</button>').join('');state.addEventListener('change',render);filter.addEventListener('input',render);choose(0);</script></html>'''.replace('PAYLOAD',payload)
out=ROOT/'analysis/phase4';out.mkdir(parents=True,exist_ok=True)
html=re.sub(r'(<img src=")([^"]+)',lambda m:m[1]+m[2]+'?v='+hashlib.sha256((out/m[2]).read_bytes()).hexdigest()[:12],html)
(out/'index.html').write_text(html)
print('Created phase4/index.html with three scene catalogs and the village service catalog')
