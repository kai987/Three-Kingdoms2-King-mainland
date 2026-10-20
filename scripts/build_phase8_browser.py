#!/usr/bin/env python3
"""Build the phase8 evidence browser using existing phase7 visual styles.

JSON receipts and formal native captures are read at generation time. No game,
emulator or source CPU/controller runs in the generated browser page.
"""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase8';sys.path.insert(0,str(ROOT))
from source.recovered.game_enums import TACTIC_NAMES

def read(name):
 p=OUT/name
 return json.loads(p.read_text())if p.exists()else{}

def slim_receipt(name):
 d=read(name)
 keys=['status','case_count','rom_cpu_case_count','source_guard_case_count','source_guard_count','failed_count','counts','original_complete_case_count','original_prefix_case_count','actual_ROM_CPU_comparison_count','source_original_code_calls','source_uses_IR_or_original_CPU','semantic_source_IR_interpretation','contract','scope','limits','limitations']
 return {k:d[k]for k in keys if k in d}

def native_captures():
 """Only formal directories with validation.json; exploratory is never proof."""
 groups=[]
 for receipt in sorted((OUT/'runtime').glob('*/validation.json')):
  directory=receipt.parent
  if any(token in directory.name for token in('exploratory','repeat')):continue
  validation=json.loads(receipt.read_text());captures=[]
  for png in sorted(directory.glob('*.png')):
   ram=png.with_name(png.stem+'-ram.bin');sram=png.with_name(png.stem+'-sram.bin')
   if not ram.exists()or not sram.exists():continue
   r,s=ram.read_bytes(),sram.read_bytes()
   if len(r)!=2048 or len(s)!=8192:continue
   metadata=json.loads(png.with_suffix('.json').read_text())if png.with_suffix('.json').exists()else{}
   units=[]
   for slot in range(20):
    ident=r[0x664+slot]
    if ident>=237:continue
    at=0x3C0+12*ident
    units.append(dict(slot=slot,officer=ident,xy=[r[0x600+slot],r[0x614+slot]],side_raw=r[0x628+slot],condition_raw=r[0x650+slot],troops_raw=int.from_bytes(s[at+8:at+10],'little'),troops_low10=int.from_bytes(s[at+8:at+10],'little')&1023,HP=s[at]))
   image=str(png.relative_to(OUT))+'?sha='+hashlib.sha256(png.read_bytes()).hexdigest()[:12]
   captures.append(dict(label=png.stem,image=image,frame=metadata.get('frames',metadata.get('frame')),global_main=r[0x7A],NMI_scene=r[0x78],battle=[r[0x500],r[0x501]],side=r[0x504],AP=r[0x505],tactic=r[0x543],proposal=[s[0xF8B],s[0xF8C],s[0xF8D],s[0xF8E],s[0xF8F]],cache=list(r[0x4D8:0x4E0]),loss_report_u24=int.from_bytes(r[0x42C:0x42F],'little'),units=units))
  if captures:groups.append(dict(name=directory.name,receipt=str(receipt.relative_to(OUT)),validation=validation,captures=captures))
 return groups

class Parsed(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.targets=[];self.details=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if 'id'in d:self.ids.append(d['id'])
  if tag=='a'and'href'in d:self.targets.append(d['href'])
  if tag=='img'and'src'in d:self.targets.append(d['src'])
  if tag=='details':self.details.append(d)

def main():
 strategies=read('strategies/evidence.json');effects=read('effects/evidence.json')
 assert len(strategies['strategy_flows'])==8
 # Preserve the already reviewed visual system; no new stylesheet is invented.
 old=(ROOT/'analysis/phase7/index.html').read_text();css=re.search(r'<style>([\s\S]+?)</style>',old).group(1)
 data={'strategies':{k:strategies[k]for k in('strategy_flows','APIs','basic_chooser','special_chooser','retreat','resupply','heal','context','scope')},
       'effects':effects,'tactics':list(TACTIC_NAMES),
       'receipts':{'strategies':slim_receipt('strategies/validation.json'),'effects':slim_receipt('effects/validation.json'),'integration':slim_receipt('source-integration.json')},
       'runtime_evidence':read('runtime/evidence.json'),'runtime':native_captures()}
 html=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>战术8策略、计略与十面埋伏 · 第八轮逆向证据</title><style>STYLES</style></head><body><main>
<small>第八轮 · 原ROM只读 · 独立玩法源码与受控原核心证据</small><h1>战术策略：退却、补给、治疗与计略作用</h1><nav><a href="../index.html">总入口</a><a href="../phase7/index.html">阶段7</a><a href="README.md">本轮总报告</a><a href="../../source/README.md">源码合同</a><a href="#strategy">8策略</a><a href="#resources">退却与资源</a><a href="#effects">施放与缓存</a><a href="#runtime">原核心证据</a></nav>
<p class="note">8项策略和A02D合作扫描已独立高层化，游戏源码不解释IR、不执行原ROMCPU。计略仍有明确的未恢复效果与实际图形依赖。<strong>本页是证据浏览器和字段公式查看器，不运行游戏或模拟器。</strong></p><div class="metrics" id="metrics"></div><p id="integration"></p>
<h2 id="strategy">1 · 8项策略的完整优先序</h2><label for="strategy-id">策略：</label><select id="strategy-id"></select><pre id="strategy-detail"></pre><p>strategy由6FA1[actor]低4位在8项表内选择；0..7是原编码，未编造正式策略名称。提案status决定6F8D的意义：移动方向、攻击目标、计略ID与退却城市是不同域。</p>
<ol class="steps"><li><strong>筛选actor</strong><br>跳过FF策略、异侧和空武将；6F96记尝试，6F95记status3。</li><li><strong>执行完整策略</strong><br>退却、特殊计略及各策略的后续优先序；必要时原计数重扫。</li><li><strong>返回提案</strong><br>非status3写请求FF，交原战场消费；不替施放或移动扣AP。</li><li><strong>保留等待边界</strong><br>高层budget停在pendingstrategy；不补图形、消息或手柄ack。</li></ol>
<details><summary>基础/特殊计略选择的精确门槛与目标排序</summary><pre id="chooser-detail"></pre></details><details><summary>共享内存、数据窗上下文及高层等价范围</summary><pre id="strategy-scope"></pre></details><p><a href="strategies/README.md">8策略完整说明</a> · <a href="strategies/evidence.json">原bytes、ROM偏移与table pins</a> · <a href="strategies/original-ranges.asm">原汇编与inline表</a> · <a href="strategies/validation.json">差分回执</a> · <a href="../../source/recovered/tactical_strategy_ai.py">独立策略源码</a></p>
<h2 id="resources">2 · 退却、补给和治疗的原字段公式</h2><p>以下控件只计算已声明字段。退却例只展示角色门槛；目的地仍须按原邻城和名册条件选择。补给、治疗例假设已通过原service到达检查，显示作用次序，不执行移动。</p>
<h3>退却门槛</h3><label for="role">角色：</label><select id="role"><option value="leader">君主record</option><option value="commander">非君主首槽0/10</option><option value="officer">其他武将</option></select><label for="retreat-troops">raw兵word：</label><input id="retreat-troops" type="number" min="0" max="65535" value="200"><label for="retreat-HP">体力byte：</label><input id="retreat-HP" type="number" min="0" max="255" value="40"><label for="army-own">本军raw总兵：</label><input id="army-own" type="number" min="0" max="65535" value="1000"><label for="army-enemy">敌军raw总兵：</label><input id="army-enemy" type="number" min="0" max="65535" value="5000"><label for="retreat-draw">已接受的0..99抽样：</label><input id="retreat-draw" type="number" min="0" max="99" value="69"><pre id="retreat-result"></pre>
<h3>到达资源点后的预算补给</h3><label for="supply-army">本军raw总兵：</label><input id="supply-army" type="number" min="0" max="65535" value="1000"><label for="supply-round">回合byte：</label><input id="supply-round" type="number" min="0" max="255" value="1"><label for="supply-gold">原gold word：</label><input id="supply-gold" type="number" min="0" max="65535" value="100"><label for="supply-grain">原grain word：</label><input id="supply-grain" type="number" min="0" max="65535" value="100"><label for="supply-price">原城市quote byte：</label><input id="supply-price" type="number" min="0" max="255" value="30"><pre id="supply-result"></pre><small>缺粮u16减法回绕不clamp零；兵数先乘4再除1000取整，然后乘剩余回合。到达后先markstrategy7，再做资源算术。</small>
<h3>到达治疗点后的体力恢复</h3><label for="heal-gold">原gold word：</label><input id="heal-gold" type="number" min="0" max="65535" value="50"><label for="heal-HP">原HP byte：</label><input id="heal-HP" type="number" min="0" max="255" value="40"><label for="heal-initial">初始HP byte：</label><input id="heal-initial" type="number" min="0" max="255" value="80"><label for="heal-draw">已接受的low4 0..10：</label><input id="heal-draw" type="number" min="0" max="10" value="5"><pre id="heal-result"></pre><small>先markstrategy7，余额不足仍保留该标记；足额先扣50再抽样。HP字节加法先回绕，之后才封顶。service到达预测未执行真正坐标commit的Y15跳行。</small>
<h2 id="effects">3 · 从计略提案到真实效果</h2><label for="tactic-id">计略ID：</label><select id="tactic-id"></select><pre id="effect-detail"></pre><p>普通player与AI施放费用分别来自原表；AI的ID11专门旁路普通收费表，部署AP扣款为0，player菜单为10。部署另扣officer原rawLE16兵100，保持word回绕。策略选择的AP门槛不等于实际消费费用。</p><div class="two"><section><h3>已恢复效果与真实依赖</h3><p id="effect-coverage"></p><p>未恢复的其余ID返回原effect入口依赖；音频、portrait、单位图形和消息确认仍须由实际前序服务完成。after_*方法是精确后缀合同，没有空渲染或默认成功。</p></section><section><h3>十面埋伏的生产—消费链</h3><p>B42A建立本侧04D8/04DC四字节缓存：actor、X、Y、TTL5。移动A51F请求phase1；global4 A02D→B933读取相反侧缓存，在原地形/半径条件下扣兵。A535后缀更新经验/百兵cache，并停在原portrait依赖。</p></section></div>
<h3>回合TTL字节查看</h3><label for="cache-active">slot：</label><select id="cache-active"><option value="3">有效slot3</option><option value="255">FF空缓存</option></select><label for="cache-TTL">TTL byte：</label><input id="cache-TTL" type="number" min="0" max="255" value="5"><pre id="TTL-result"></pre><small>原CE20只检查TTL：TTL==FF跳过，与slot是否FF无关；空slotFF的TTL5仍减4。TTL1→0执行写slotFF（即使slot原已FF）；TTL0→FF下溢保持原slot。expiry不改XY。</small>
<details><summary>缓存部署、触发、过期和清除的完整边界</summary><pre id="effect-lifecycle"></pre></details><p><a href="effects/evidence.json">计略及缓存bytes证据</a> · <a href="effects/validation.json">当前效果回执</a> · <a href="effects/ambush_deployment.asm">部署原汇编</a> · <a href="effects/movement_secondary_request_and_consume.asm">触发与消费原汇编</a> · <a href="effects/round_expiry.asm">回合过期原汇编</a> · <a href="../../source/recovered/tactical_effects.py">计略作用源码</a></p>
<h2 id="runtime">4 · 原完整核心的施放与触发证据</h2><p id="runtime-summary"></p><label for="runtime-group">正式实验：</label><select id="runtime-group"></select><label for="runtime-left">前检查点：</label><select id="runtime-left"></select><label for="runtime-right">后检查点：</label><select id="runtime-right"></select><div class="screens" id="runtime-screens"><figure><img id="runtime-before" alt="原完整Nestopia核心前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="runtime-after" alt="原完整Nestopia核心后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="runtime-transition"></p><details><summary>前后战斗字段、缓存和武将raw记录</summary><pre id="runtime-fields"></pre></details><details><summary>原核心准备写入、按键、作用字段与重复回执</summary><pre id="runtime-detail"></pre></details><p id="runtime-links"></p><p class="note">原核心截图与RAM/SRAM/state共同证明真实施放和作用。原fixture的具体准备必须单列；不把受控预置称作自然战役可达，也不把同步CPU指令轨迹当Nestopia逐指令录制。空VRAM导出不计有效非空产物检查。</p>
<details><summary>当前模块与统一API验证回执</summary><pre id="receipt-detail"></pre></details><footer>来源：原ROMbytes与pinned表、独立高层源码、实际原CPU差分、完整核心实验分别说明。页面控件只查看已有证据或原字段公式，不推进游戏，不默认完成硬件/消息/图形任务。</footer>
</main><script>const D=PAYLOAD,$=s=>document.querySelector(s),pretty=v=>JSON.stringify(v,null,2),hex=(v,w=4)=>Number(v).toString(16).toUpperCase().padStart(w,'0'),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),num=v=>v==null?'待回执':Number(v).toLocaleString();
// FORMULA_START
function retreatFormula(role,troops,hp,own,enemy,draw){if(role==='leader')return{eligible:troops<301&&hp<51,rule:'兵<301 且体<51'};if(role==='commander'){const forced=own<1757&&own+3499<enemy;return{eligible:forced||(troops<101&&hp<41),forced,rule:'弱势强制，否则兵<101且体<41'};}return{eligible:troops<201&&hp<100&&draw<70,rule:'兵<201且体<100，再接受抽样<70'};}
function resupplyFormula(army,round,gold,grain,price){const rounds=(30-round)&255,demand=(Math.floor(army*4/1000)*rounds)&65535,budget=Math.floor(gold*7/10)&65535,shortage=(demand-grain)&65535,cost=price?Math.floor(shortage*100/price)&65535:65535,spent=budget>=cost?cost:budget,gained=budget>=cost?shortage:Math.floor(budget*price/100)&65535;return{strategy_low_nibble:7,rounds,demand,budget,shortage,cost,spent,gained,gold_after:(gold-spent)&65535,grain_after:(grain+gained)&65535};}
function healFormula(gold,hp,initial,draw){if(gold<50)return{strategy_low_nibble:7,applied:false,gold_after:gold,HP_after:hp};const amount=draw+35;return{strategy_low_nibble:7,applied:true,gold_after:(gold-50)&65535,amount,HP_wrapped:(hp+amount)&255,HP_after:Math.min((hp+amount)&255,initial)};}
function expiryFormula(slot,ttl){if(ttl===255)return{slot_before:slot,slot_after:slot,TTL_before:ttl,TTL_after:ttl,slot_cleared:false,XY_changed:false,reason:'TTL==FF跳过，slot不参与该检查'};const after=(ttl-1)&255;return{slot_before:slot,slot_after:after===0?255:slot,TTL_before:ttl,TTL_after:after,slot_cleared:after===0,XY_changed:false,reason:ttl===0?'0→FF下溢，原slot保持':after===0?'TTL1→0执行写slotFF':'TTL递减，原slot保持'};}
// FORMULA_END
const labels={strategies:'8策略独立高层 · 原CPU',effects:'计略/缓存独立高层 · 原CPU',integration:'GameEngine集成 · 原CPU'};$('#metrics').innerHTML=Object.entries(labels).map(([k,label])=>{const r=D.receipts[k],count=k==='integration'?r.actual_ROM_CPU_comparison_count:r.rom_cpu_case_count;return`<div class="metric"><small>${label}</small><strong>${num(count)}</strong><small>${esc(r.status||'待正式回执')} · source guards另${num(r.source_guard_case_count??r.source_guard_count)}</small></div>`;}).join('');$('#integration').textContent='统一API保留原CPU/IR桥接作独立参照，同时提供tactical_strategy_rules()/tick_tactical_strategy()和tactical_effect_rules()共享内存语义接口；高层入口不声称寄存器/mapper等价。';$('#receipt-detail').textContent=pretty(D.receipts);
$('#strategy-id').innerHTML=D.strategies.strategy_flows.map(v=>`<option value="${v.id}">${v.id} · $${hex(v.cpu)}</option>`).join('');function strategy(){const v=D.strategies.strategy_flows[Number($('#strategy-id').value)];$('#strategy-detail').textContent=`策略${v.id} · 原bank8 CPU$${hex(v.cpu)} / file0x${hex(v.rom_offset,6)}\n${v.priority}\n范围：${v.scope}\n这里只浏览优先序，不执行策略或消费提案。`;}$('#strategy-id').addEventListener('change',strategy);strategy();$('#chooser-detail').textContent=pretty({basic:D.strategies.basic_chooser,special:D.strategies.special_chooser});$('#strategy-scope').textContent=pretty({context:D.strategies.context,scope:D.strategies.scope});
function inputs(ids,bounds){return ids.map((id,i)=>{const v=Number($('#'+id).value);if(!Number.isInteger(v)||v<0||v>bounds[i])throw Error('请输入字段域内整数');return v;});}function show(id,calculate){try{$('#'+id).textContent=pretty(calculate());}catch(e){$('#'+id).textContent=e.message;}}const retreatIds=['retreat-troops','retreat-HP','army-own','army-enemy','retreat-draw'];function retreat(){show('retreat-result',()=>{const a=inputs(retreatIds,[65535,255,65535,65535,99]);return{...retreatFormula($('#role').value,...a),destination:'仍需真实原邻城/名册条件；此控件不选择目的地'};});}$('#role').addEventListener('change',retreat);retreatIds.forEach(id=>$('#'+id).addEventListener('input',retreat));retreat();const supplyIds=['supply-army','supply-round','supply-gold','supply-grain','supply-price'];function supply(){show('supply-result',()=>resupplyFormula(...inputs(supplyIds,[65535,255,65535,65535,255])));}supplyIds.forEach(id=>$('#'+id).addEventListener('input',supply));supply();const healIds=['heal-gold','heal-HP','heal-initial','heal-draw'];function heal(){show('heal-result',()=>healFormula(...inputs(healIds,[65535,255,255,10])));}healIds.forEach(id=>$('#'+id).addEventListener('input',heal));heal();
$('#tactic-id').innerHTML=D.tactics.map((name,i)=>`<option value="${i}">${i} · ${name}${(D.effects.fully_recovered_effect_ids||[]).includes(i)?' · 已恢复':' · effect依赖'}</option>`).join('');$('#tactic-id').value='11';function effect(){const i=Number($('#tactic-id').value),supported=(D.effects.fully_recovered_effect_ids||[]).includes(i),player=D.effects.player_AP_cost_table?.bytes[i],ai=i===11?0:D.effects.AI_AP_cost_table?.bytes[i];$('#effect-detail').textContent=`ID${i} ${D.tactics[i]}\n${supported?'已恢复原effect玩法体':'未恢复effect body：返回真实依赖入口，不称施放成功'}\nplayer菜单AP成本=${player??'待表'}；AI消费AP成本=${ai??'待表'}${i===11?'（C1AF专用旁路，不用普通AI表第11项）':''}\n${i===11?'另扣rawLE16兵100；缓存actor/X/Y/TTL5；无渲染或消息完成ack。':'施放资格、RNG、原效果和真实前序等待仍需符合各API合同。'}\n这是已恢复范围查看，不会施放计略。`;}$('#tactic-id').addEventListener('change',effect);effect();$('#effect-coverage').textContent=`当前完整effect IDs：${(D.effects.fully_recovered_effect_ids||[]).map(i=>i+' '+D.tactics[i]).join('、')}。其余8项保留原effect入口依赖；不把正式16项名字等同于全部16效果源码完成。`;$('#effect-lifecycle').textContent=pretty({deployment:D.effects.deployment,lifecycle:D.effects.lifecycle,scope:D.effects.graphics_audio_readiness});function ttl(){show('TTL-result',()=>expiryFormula(Number($('#cache-active').value),inputs(['cache-TTL'],[255])[0]));}$('#cache-active').addEventListener('change',ttl);$('#cache-TTL').addEventListener('input',ttl);ttl();
const groups=D.runtime;$('#runtime-summary').textContent=groups.length?`当前${groups.length}组正式原核心回执。配对PNG与rawRAM/SRAM/state同源；准备字节、输入、真实等待和重复检查见下方JSON。阶段8的受控fixture须与阶段7无注入自然片段分开。`:'正式原核心manifest尚在整理；此生成器等待已验证的validation/PNG。未把exploratory图片当作正式运行实证。';$('#runtime-group').innerHTML=groups.length?groups.map((g,i)=>`<option value="${i}">${g.name}</option>`).join(''):'<option>待正式回执</option>';function runtimeOptions(){const group=groups[Number($('#runtime-group').value)];if(!group){$('#runtime-screens').hidden=true;$('#runtime-fields').textContent='待正式原核心检查点';return;}$('#runtime-screens').hidden=false;const options=group.captures.map((c,i)=>`<option value="${i}">${c.frame??'?'} · ${c.label}</option>`).join('');$('#runtime-left').innerHTML=options;$('#runtime-right').innerHTML=options;const labelIndex=label=>group.captures.findIndex(c=>c.label===label),before=labelIndex(group.name.includes('ambush')?'trigger-before':'effect-before'),after=labelIndex(group.name.includes('ambush')?'trigger-after':'effect-after');$('#runtime-left').value=String(before>=0?before:0);$('#runtime-right').value=String(after>=0?after:Math.max(0,group.captures.length-1));runtimeDetail();}function runtimeDetail(){const group=groups[Number($('#runtime-group').value)];if(!group)return;const left=group.captures[Number($('#runtime-left').value)],right=group.captures[Number($('#runtime-right').value)];if(!left||!right){$('#runtime-screens').hidden=true;return;}[['before',left],['after',right]].forEach(([id,c])=>{$('#runtime-'+id).src=c.image;$('#'+id+'-caption').textContent=`${group.name} · ${c.label} · frame${c.frame??'?'}；原core global${c.global_main}/NMI${c.NMI_scene}，battle${c.battle.join('/')}，AP${c.AP}。`});$('#runtime-transition').textContent=`${left.label}→${right.label}：AP ${left.AP}→${right.AP}，042C..042E ${left.loss_report_u24}→${right.loss_report_u24}；控制请求 ${hex(left.proposal[0],2)}→${hex(right.proposal[0],2)}。这是帧末值；phase1可在帧内消费，未据此声称截图捕获请求1。`;$('#runtime-fields').textContent=pretty({before:{cache:left.cache,AP:left.AP,tactic:left.tactic,proposal:left.proposal,loss_u24:left.loss_report_u24,units:left.units},after:{cache:right.cache,AP:right.AP,tactic:right.tactic,proposal:right.proposal,loss_u24:right.loss_report_u24,units:right.units}});$('#runtime-detail').textContent=pretty({formal_manifest:D.runtime_evidence,experiment:group.validation});$('#runtime-links').innerHTML=`<a href="${esc(group.receipt)}">所选正式实验JSON</a> · <a href="${esc(left.image.split('?')[0])}">前原PNG</a> · <a href="${esc(right.image.split('?')[0])}">后原PNG</a>`;}$('#runtime-group').addEventListener('change',runtimeOptions);$('#runtime-left').addEventListener('change',runtimeDetail);$('#runtime-right').addEventListener('change',runtimeDetail);runtimeOptions();
</script></body></html>'''
 html=html.replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html)
 parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids));assert all('open'not in d for d in parsed.details)
 script=re.search(r'<script>([\s\S]+)</script>',html).group(1)
 check=subprocess.run(['node','--check','--input-type=commonjs'],input=script,text=True,capture_output=True);assert check.returncode==0,check.stderr
 missing=[]
 for target in parsed.targets:
  if target.startswith('#'):assert target[1:]in parsed.ids
  elif not(OUT/target.split('?',1)[0]).exists():missing.append(target)
 # The parent writes the total README last; all other existing links are hardrequirements.
 assert missing in([],['README.md']),missing
 for group in data['runtime']:
  for capture in group['captures']:assert(OUT/capture['image'].split('?',1)[0]).is_file()
 formula=re.search(r'// FORMULA_START([\s\S]*?)// FORMULA_END',script).group(1)
 tests=r'''const assert=require('node:assert/strict');let n=0;const ck=(a,b)=>{assert.deepEqual(a,b);n++};ck(retreatFormula('leader',300,50,0,0,0).eligible,true);ck(retreatFormula('leader',301,50,0,0,0).eligible,false);ck(retreatFormula('commander',500,90,1000,5000,0).forced,true);ck(retreatFormula('commander',100,40,2000,5000,0).eligible,true);ck(retreatFormula('officer',200,99,0,0,69).eligible,true);ck(retreatFormula('officer',200,99,0,0,70).eligible,false);ck(healFormula(49,40,80,5).applied,false);ck(healFormula(50,40,80,5).HP_after,80);ck(healFormula(50,255,80,10).HP_after,44);ck(resupplyFormula(1000,1,100,100,30).shortage,16);ck(resupplyFormula(1000,1,100,100,30).spent,53);ck(resupplyFormula(1000,1,100,100,30).grain_after,116);ck(resupplyFormula(1000,31,0,200,0).cost,65535);process.stdout.write(String(n));'''
 # Compare browserTTL against the independent effectsource, including the
 # clear-path event when the slot already isFF. These are sourceUI parity
 # fixtures, not additional originalROM or nativecore cases.
 from source.recovered.tactical_effects import TacticalEffects
 ttl_fixtures=[]
 for slot,ttl in[(255,5),(3,255),(3,1),(3,0),(255,1)]:
  memory=bytearray(65536);memory[0x4D8:0x4E0]=bytes([255,20,17,255,255,20,17,255])
  memory[0x4D8]=slot;memory[0x4DB]=ttl
  result=TacticalEffects(memory,None).tick_expiry()
  event=next((event for event in result['events']if event['group']==0),None)
  expected=dict(slot_before=slot,slot_after=memory[0x4D8],TTL_before=ttl,TTL_after=memory[0x4DB],
                slot_cleared=bool(event and event['slot_cleared']),XY_changed=False)
  assert memory[0x4D9:0x4DB]==bytes([20,17])
  ttl_fixtures.append(dict(slot=slot,ttl=ttl,expected=expected))
 # Existing tests write their count; keep that count while adding5 source
 # comparisons against the same JSformula shipped in the generatedpage.
 tests=tests.replace('process.stdout.write(String(n));','')
 tests+='const TTL_SOURCE_FIXTURES='+json.dumps(ttl_fixtures)+';for(const f of TTL_SOURCE_FIXTURES){const v=expiryFormula(f.slot,f.ttl);delete v.reason;ck(v,f.expected);}process.stdout.write(String(n));'
 tested=subprocess.run(['node','--input-type=commonjs'],input=formula+tests,text=True,capture_output=True);assert tested.returncode==0,tested.stderr
 print(json.dumps(dict(output='analysis/phase8/index.html',html_bytes=len(html.encode()),html_sha256=hashlib.sha256(html.encode()).hexdigest(),strategy_options=8,tactic_options=16,supported_effect_ids=len(effects.get('fully_recovered_effect_ids',[])),formal_runtime_groups=len(data['runtime']),formal_screenshots=sum(len(g['captures'])for g in data['runtime']),formula_checks=int(tested.stdout),TTL_source_fixture_checks=len(ttl_fixtures),TTL_source_fixtures=ttl_fixtures,unique_ids=len(parsed.ids),closed_details=len(parsed.details),JS_syntax='passed',links='passed_except_pending_totalREADME'if missing else'passed',receipt_counts={k:v.get('rom_cpu_case_count',v.get('actual_ROM_CPU_comparison_count'))for k,v in data['receipts'].items()}),ensure_ascii=False))

if __name__=='__main__':main()
