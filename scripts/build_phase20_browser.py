#!/usr/bin/env python3
"""Build the phase20 view from formal receipts, without running gameplay."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,tempfile,wave
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase20';RUN=OUT/'runtime'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
FIELDS=('frame','global_state','nmi_scene','active_controller','active_main','active_phase',
 'calendar_and_turn_6F00_6F06','domestic_control_6F5B_6F62','cooperation_status_6F8B',
 'all30_city_auxiliary_bytes','all30_city_owners','all30_city_gold','all30_city_food','all30_city_reserve','all30_city_rosters',
 'rulers','offer_cache_0036_0045','offer_resource_kind_0039','offer_committed_word_003A_003B','offer_quote_042F_0431',
 'consumer_choice_040C','consumer_text_0300_0304','menu_cursor_0012','cooperation_UI_040A_040F',
 'readonly_RNG_cursor_bytes_0050_0055','actual_saved_CPU_registers','actual_saved_PRG_banks',
 'RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
SOURCE_NAMES=('negotiation_services.py','negotiation_integration.py')
RECEIPTS=('services/validation.json','cpu/consumer-sequences.json','cpu/native-context-source-sequences.json','cpu/actual-caller-source-validation.json','fields-static/verification.json')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def href(p):return '../../'+str(Path(p).relative_to(ROOT))
def compact(r):
 return {k:v for k,v in r.items()if k not in('rows','cases','artifact_sha256','source_sha256','source_and_validator_sha256','executed_instruction_positions','upstream','original_constructor_checks','model_checks')}

HTML=r'''<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>阶段二十 · 原核心F8交涉与续行</title><style>__CSS__
.outcome{border-left:3px solid #9ad9c7;padding:0 18px}.phase-links{margin-top:14px}.pending{color:#e6cc9c}main{width:100%;min-width:0}section,details,pre,.scroll{min-width:0;max-width:100%}.receipt-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.receipt-grid pre{max-height:340px}#source-code{max-height:640px}.screens{grid-template-columns:repeat(2,minmax(0,1fr))}.screens figure{min-width:0}.screens label{display:flex;width:100%;min-width:0}.screens select{flex:1;width:100%;min-width:0}.screens img{width:256px;height:240px;max-width:none}.screens figcaption{font-size:14px;color:#b6c8cb;overflow-wrap:anywhere}label{max-width:100%;min-width:0}select{min-width:0;max-width:100%}.scroll{width:100%;overflow-x:auto}table{table-layout:fixed}td pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:14px 0}summary{cursor:pointer;overflow-wrap:anywhere}button[disabled]{opacity:.5;cursor:default}#point-links{margin:14px 0}.preset{display:flex;gap:12px;flex-wrap:wrap}@media(max-width:700px){.receipt-grid,.screens{grid-template-columns:minmax(0,1fr)}}
</style><main><small>三国志2超级版 · 原ROM证据 · 阶段二十</small><h1>原核心实际发出 F8<br>接受、拒绝与 AI 继续运行</h1><p>两条完整冷启动流程，通过正常扩城和普通按键触发原交涉。捕获前端没有写入请求、回复、ready、RNG、PC或策略权重；接受与拒绝都继续到原请求清除、AI续行及下一次玩家地图。</p><nav><a href="#native">原模拟器流程</a><a href="#source">完整源码</a><a href="#validation">分列验证</a><a href="#fields">城市访问合同</a><a href="README.md">本轮报告</a><a href="../phase19/index.html">阶段十九</a></nav><div class="metrics" id="metrics"></div><p id="build-status" class="note"></p><p id="error" role="alert"></p>
<section id="native"><h2>原 Nestopia：接受与拒绝</h2><p class="outcome">同一自然路线占领中立城0，袁紹势力城数3→4。第二次兵力分配确认前无键等待73帧，原AI向玩家提出粮食114的交涉。接受案原城2粮食9999→9885、城4暂升10113后回到9999；拒绝回复时双方粮食与外交保留原值。完整后续月轮变化另列，不能全部归因于交涉。</p><label for="case">实际流程 <select id="case" aria-label="实际原核心流程"></select></label><p id="case-scope"></p><div class="scroll"><table><thead><tr><th>原观察点</th><th>实际结果</th></tr></thead><tbody id="outcome-rows"></tbody></table></div><details><summary>冷启动来源、零准备声明与完整按键计划</summary><pre id="case-provenance"></pre></details><label><input id="all-points" aria-label="显示全部原检查点" type="checkbox"> 显示全部原检查点</label><p id="points-scope" class="note"></p><div class="screens"><figure><label for="point-a">原帧截图A <select id="point-a" aria-label="原帧截图A"></select></label><img id="image-a" width="256" height="240" alt="原模拟器实际检查点A"><figcaption id="caption-a"></figcaption></figure><figure><label for="point-b">原帧截图B <select id="point-b" aria-label="原帧截图B"></select></label><img id="image-b" width="256" height="240" alt="原模拟器实际检查点B"><figcaption id="caption-b"></figcaption></figure></div><p class="linkrow" id="point-links"></p><details><summary>两幅截图对应的完整原字段与REG／银行快照</summary><pre id="point-raw"></pre></details><h3>任意两个实际帧的字段对照</h3><div class="preset"><button id="show-settlement">F8产生与原回复帧</button><button id="show-grain-cap">接受后10113与原限幅帧</button></div><label for="frame-a">帧A <input id="frame-a" aria-label="对照帧A" type="number" min="1"></label><label for="frame-b">帧B <input id="frame-b" aria-label="对照帧B" type="number" min="1"></label><button id="frame-compare">对照实际帧</button><p class="note">每帧数据来自正式frame-services投影；上方原图始终对应所选checkpoint。actual_saved_CPU_registers是原保存状态的边界快照，不是原核心内部指令trace。rulers.raw_byte1维持原字节名。</p><div class="scroll"><table><thead><tr><th>原字段</th><th>帧A</th><th>帧B</th></tr></thead><tbody id="frame-rows"></tbody></table></div><h3>完整原48000Hz PCM</h3><audio id="audio" controls preload="metadata"></audio><p id="audio-meta" class="note"></p><p class="linkrow" id="case-links"></p><details><summary>完整病例结果与原F8事件</summary><pre id="case-effects"></pre></details></section>
<section id="source"><h2>两份完整可读源码</h2><p>具名交涉服务与适配入口。原CPU仅在验证器执行；生产源码无原CPU／IR回退。复用的父模块与本轮新增服务分开链接。</p><label for="source-select">源码文件 <select id="source-select" aria-label="完整源码文件"></select></label><button id="source-open">显示完整源码</button><p id="source-meta" class="note"></p><pre id="source-code"></pre><p class="linkrow" id="source-links"></p><p class="linkrow"><a href="../../source/recovered/domestic_secondary_services.py">父次级AI服务</a><a href="../../source/recovered/scene_coordinator.py">原场景协作入口</a><a href="../../source/recovered/nestopia_context.py">原State格式解析</a><a href="services/static-catalog.json">原字节与位置目录</a><a href="services/evidence.json">来源证据</a></p></section>
<section id="validation"><h2>验证范围分列</h2><p>Native帧、源码／原CPU病例、显式中断消费者序列、原快照继承序列与静态访问证明分别计数。指令位置覆盖不代表所有输入或完整硬件时序覆盖；本页不模拟游戏。</p><div class="receipt-grid" id="receipt-grid"></div><p class="linkrow"><a href="runtime/validation.json">原核心双跑回执</a><a href="runtime/static-validation.json">同帧RGB／RAM／SRAM／全State与WAV校验</a><a href="services/validation.json">服务原CPU矩阵</a><a href="cpu/consumer-sequences.json">消费者协作序列</a><a href="cpu/native-context-source-sequences.json">正式原快照源码序列</a><a href="cpu/actual-caller-source-validation.json">实际caller输入服务矩阵</a></p></section>
<section id="fields"><h2>城市+1与+28..31：仍保留未知正式名称</h2><p>城市+1参与错位word门槛300已由旧证据确认，不能由此替单字节命名。本轮在原指针、返回合同和存储屏障范围继续排除不相关访问；未解析访问也不等于实际字段消费者。旧589、新45与全1526三个域分列。</p><pre id="access-summary"></pre><label for="classification">访问归类 <select id="classification" aria-label="间接访问归类"><option value="all">全部1526条间接访问</option></select></label><label for="access-search">原地址或指针 <input id="access-search" aria-label="搜索原银行地址或指针" placeholder="例如 BD95 或 0020"></label><p id="access-count"></p><button id="access-prev">上一页</button> <button id="access-next">下一页</button><div class="scroll"><table><thead><tr><th>原bank／PC</th><th>操作／指针</th><th>分类</th><th>合同与限制</th></tr></thead><tbody id="access-rows"></tbody></table></div><p class="linkrow"><a href="fields-static/analysis-summary.json">三域完整摘要</a><a href="fields-static/all-indirect-accesses.json">全部原访问</a><a href="fields-static/remaining-accesses.json">剩余访问</a><a href="fields-static/return-pair-contracts.json">返回指针对合同</a><a href="fields-static/verification.json">构造前缀／模型验证</a></p></section><p class="note">原ROM、原core与旧阶段产物保持冻结。正式Native两案不导入State或battery、不写额外数据。原RGB／WAV来自实际原文件；不将其称为恢复源码的波形合成。空0BVRAM与路径metadata JSON不计入非空精确复跑。</p></main><script id="evidence" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.querySelector('#evidence').textContent),$=s=>document.querySelector(s),fmt=x=>JSON.stringify(x,null,2),hex=x=>Number(x).toString(16).toUpperCase().padStart(4,'0');let current,accessPage=0;
function cell(v){const t=document.createElement('td'),p=document.createElement('pre');p.textContent=typeof v==='string'?v:JSON.stringify(v);t.append(p);return t}function row(values){const tr=document.createElement('tr');values.forEach(v=>tr.append(cell(v)));return tr}function link(p,label){const a=document.createElement('a');a.href=p;a.textContent=label;return a}function links(target,items){$(target).replaceChildren(...items.map(p=>link(p.href,p.label)))}
async function source(){const s=D.sources[+$('#source-select').value];$('#source-code').textContent=s.text;$('#source-meta').textContent=`完整UTF8源码 · ${s.text.length}字符 · SHA256 ${s.sha256}`;links('#source-links',[{href:s.href,label:'原完整源码文件'}]);if(globalThis.crypto?.subtle){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s.text)),actual=[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');if(actual!==s.sha256)$('#error').textContent='嵌入源码SHA不匹配';}}
function point(){const a=current.checkpoints[+$('#point-a').value],b=current.checkpoints[+$('#point-b').value];for(const[side,p]of[['a',a],['b',b]]){$('#image-'+side).src=p.image_href;$('#caption-'+side).textContent=`实际frame${p.frame} · ${p.label} · 原256×240`;}$('#point-raw').textContent=fmt({A:{fields:a.fields,actual_saved_context:current.frames[a.frame-1].actual_saved_CPU_registers,actual_PRG_banks:current.frames[a.frame-1].actual_saved_PRG_banks},B:{fields:b.fields,actual_saved_context:current.frames[b.frame-1].actual_saved_CPU_registers,actual_PRG_banks:current.frames[b.frame-1].actual_saved_PRG_banks}});links('#point-links',[...a.links.map(p=>({...p,label:'A '+p.label})),...b.links.map(p=>({...p,label:'B '+p.label}))]);}
function compare(){let a=Number($('#frame-a').value),b=Number($('#frame-b').value);if(!Number.isInteger(a)||!Number.isInteger(b)){$('#error').textContent='帧号须为整数；当前对照保留。';return}a=Math.max(1,Math.min(current.frames.length,a));b=Math.max(1,Math.min(current.frames.length,b));$('#frame-a').value=a;$('#frame-b').value=b;const left=current.frames[a-1],right=current.frames[b-1];$('#frame-rows').replaceChildren(...D.frame_fields.map(k=>row([k,left[k],right[k]])));if($('#error').textContent.startsWith('帧号须为整数'))$('#error').textContent='';}
function framePair(a,b){$('#frame-a').value=a;$('#frame-b').value=b;compare()}
function fillPoints(keep=false){const defaults=['F8-original-choice-'+current.verified_effects.choice,'F8-original-AI-continuation-human-world'];let shown=0;for(const[side,def]of[['a',defaults[0]],['b',defaults[1]]]){const selected=keep?String($('#point-'+side).value):null,options=[];current.checkpoints.forEach((p,i)=>{if($('#all-points').checked||p.label.startsWith('F8-previous-')||p.label.startsWith('F8-original-')||p.label==='F8-request-actually-produced'||p.label==='F8-first-observed-request-return'||p.label==='AI-ruler4-status00-frame10479'||p.label==='natural-confirmation-delay'||p.label==='final'){const o=document.createElement('option');o.value=i;o.textContent=`${p.frame} · ${p.label}`;options.push(o)}});shown=options.length;$('#point-'+side).replaceChildren(...options);$('#point-'+side).value=selected!==null&&options.some(o=>String(o.value)===selected)?selected:current.checkpoints.findIndex(p=>p.label===def);}$('#points-scope').textContent=`当前列出${shown}个${$('#all-points').checked?'全部':'关键'}检查点；本案完整保留${current.checkpoints.length}个原检查点。`;}
function choose(){current=D.native[+$('#case').value];const e=current.verified_effects,r=e.first_observed_reply;$('#case-scope').textContent=`${current.case} · ${current.frames.length}实际帧 · ${current.checkpoints.length}检查点 · 原冷启动 · 0导入／0额外数据写入 · 原选择${e.choice==='accept'?'接受':'拒绝'}`;$('#case-provenance').textContent=fmt({cold_boot:true,state_imported:false,preparation:current.preparation,preparation_groups:current.preparation_groups,ordinary_confirmation_delay_frames:e.ordinary_confirmation_delay_frames,input_plan:current.plan,limits:current.limits});$('#outcome-rows').replaceChildren(...[
 ['原F8产生',{frame:e.offer.frame,producer_ruler:e.offer.producer_ruler,leaders_and_messenger:e.offer.leaders_and_messenger,resource_kind:e.offer.resource_kind,quote:e.offer.quote,commit_word:e.offer.commit_word}],
 ['原菜单／原回复',{menu_cursor:e.actual_menu_cursor,reply_frame:r.frame,actual_reply:r.observed_status,request_FF_frame:e.original_request_FF_frame}],
 ['回复当帧的粮食与外交',{city2_grain:r.city_food[2],city4_grain:r.city_food[4],ruler1_diplomacy:r.rulers[1].diplomatic_bytes,ruler4_diplomacy:r.rulers[4].diplomatic_bytes,city4_later_cap_frame:e.recipient_grain_later_cap_frame}],
 ['原AI继续后玩家地图',{frame:e.next_human_world_frame,ruler:e.next_human_ruler,controller:e.final_controller}]
 ].map(row));fillPoints();point();$('#frame-a').max=$('#frame-b').max=current.frames.length;framePair(e.offer.frame,r.frame);$('#show-grain-cap').disabled=e.recipient_grain_later_cap_frame===null;$('#audio').src=current.audio.href;$('#audio-meta').textContent=`原48000Hz／双声道16bit · ${current.audio.sample_frames}样本对 · SHA256 ${current.audio.sha256}`;links('#case-links',current.links);$('#case-effects').textContent=fmt({verified_effects:e,F8_events:current.events});}
function access(reset=false){if(reset)accessPage=0;const kind=$('#classification').value,q=$('#access-search').value.trim().toUpperCase(),all=D.accesses.filter(r=>(kind==='all'||r.classification===kind)&&(!q||`${r.physical_bank}:${hex(r.cpu)} ${hex(r.pointer_zero_page)} ${r.classification}`.toUpperCase().includes(q)));accessPage=Math.max(0,Math.min(accessPage,Math.max(0,Math.ceil(all.length/25)-1)));$('#access-count').textContent=`${all.length}条匹配；第${accessPage+1}页，每页25条。完整文件保存全部候选与边界。`;$('#access-prev').disabled=accessPage===0;$('#access-next').disabled=(accessPage+1)*25>=all.length;$('#access-rows').replaceChildren(...all.slice(accessPage*25,(accessPage+1)*25).map(r=>row([`${r.physical_bank}:${hex(r.cpu)}`,`${r.op} ${r.index_form}`,r.classification,{proof:r.proof,limits:r.limits}])));}
$('#metrics').replaceChildren(...D.metrics.map(([label,count])=>{const d=document.createElement('div');d.className='metric';const s=document.createElement('small'),b=document.createElement('strong');s.textContent=label;b.textContent=count;d.append(s,b);return d}));$('#build-status').textContent=D.final?'正式current回执构建；浏览器交互验收另列。':'预览：仍有待完成的正式回执，以下不代替最终验收。';$('#build-status').className=D.final?'note':'pending';for(const[name,r]of Object.entries(D.source_receipts)){const d=document.createElement('details'),h=document.createElement('summary'),p=document.createElement('pre');h.textContent=name;p.textContent=fmt(r);d.append(h,p);$('#receipt-grid').append(d)}$('#source-select').replaceChildren(...D.sources.map((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=s.label;return o}));$('#source-open').onclick=source;$('#source-select').onchange=source;$('#case').replaceChildren(...D.native.map((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.case;return o}));$('#case').onchange=choose;$('#point-a').onchange=$('#point-b').onchange=point;$('#all-points').onchange=()=>{fillPoints(true);point()};$('#frame-compare').onclick=compare;$('#show-settlement').onclick=()=>framePair(current.verified_effects.offer.frame,current.verified_effects.first_observed_reply.frame);$('#show-grain-cap').onclick=()=>{const f=current.verified_effects.recipient_grain_later_cap_frame;if(f!==null)framePair(f-1,f)};$('#access-summary').textContent=fmt(D.static_summary);for(const[name,count]of Object.entries(D.classifications)){const o=document.createElement('option');o.value=name;o.textContent=`${name} (${count})`;$('#classification').append(o)}$('#classification').onchange=()=>access(true);$('#access-search').oninput=()=>access(true);$('#access-prev').onclick=()=>{accessPage--;access()};$('#access-next').onclick=()=>{accessPage++;access()};access();choose();source();
</script></html>'''

class Document(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.refs=[];self.unlabelled_selects=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id'in a:self.ids.append(a['id'])
  for key in('href','src'):
   if a.get(key):self.refs.append(a[key])
  if tag=='select'and not a.get('aria-label'):self.unlabelled_selects.append(a.get('id'))

def verify_pins(receipt):
 failures=[]
 for key in('source_sha256','source_and_validator_sha256'):
  for path,pin in(receipt.get(key)or{}).items():
   if not(ROOT/path).is_file()or sha(ROOT/path)!=pin:failures.append(path)
 return failures

def build(require_final):
 dependencies={};missing=[]
 def load(path,optional=False):
  path=Path(path)
  if not path.is_file():
   if optional:missing.append(str(path.relative_to(OUT)));return dict(status='pending',path=str(path.relative_to(OUT)))
   raise FileNotFoundError(path)
  dependencies[str(path.relative_to(ROOT))]=sha(path);return read(path)
 native_evidence=load(RUN/'evidence.json');nv=load(RUN/'validation.json');assert nv['status']=='passed'and nv['case_count']==2
 receipts={n:load(OUT/n,True)for n in RECEIPTS}
 for n,r in receipts.items():
  if r['status']!='passed':missing.append(n+':not-passed')
  current_errors=verify_pins(r)
  if current_errors:missing.extend(n+':stale:'+p for p in current_errors)
 if require_final:assert not missing,missing
 static=load(OUT/'fields-static/analysis-summary.json');original=load(OUT/'fields-static/all-indirect-accesses.json');catalog=load(OUT/'services/static-catalog.json');load(OUT/'services/evidence.json')
 sources=[]
 for name in SOURCE_NAMES:
  path=ROOT/'source/recovered'/name;pin=sha(path);dependencies[str(path.relative_to(ROOT))]=pin
  sources.append(dict(label=name,path=str(path.relative_to(ROOT)),href=href(path)+'?sha='+pin,sha256=pin,text=path.read_text()))
 native=[];all_links=[];image_count=0
 for c in native_evidence['native_cases']:
  folder=RUN/c['case'];r=load(folder/'validation.json');rep=load(folder/'repeat-validation.json');assert r['status']==rep['status']=='passed'and rep['all_hashes_equal']
  assert r['cold_boot']and not r['state_imported']and r['additional_core_memory_writes']==0 and not r['preparation']
  frames=load(folder/'frame-services.json');points=load(folder/'checkpoints.json');plan=load(folder/'input-plan.json');events=load(folder/'F8-events.json')
  assert len(frames)==r['frames']and len(points)==r['checkpoint_count']and all(set(FIELDS)<=row.keys()for row in frames)
  for p in points:
   image=folder/p['image'];pin=sha(image);assert r['artifact_sha256'][image.name]['sha256']==pin
   dependencies[str(image.relative_to(ROOT))]=pin;p['image_href']=href(image)+'?sha='+pin;image_count+=1
   p['links']=[dict(label=label,href=href(folder/name))for label,name in(('PNG',p['image']),('metadata',p['label']+'.json'),('RAM',p['RAM']),('SRAM',p['SRAM']),('wholeState',p['state']))]
   all_links.extend(p['links']);assert all((OUT/l['href'].split('?')[0]).resolve().is_file()for l in p['links'])
  wav=folder/'full-audio.wav';pin=sha(wav);assert r['artifact_sha256'][wav.name]['sha256']==pin;dependencies[str(wav.relative_to(ROOT))]=pin
  with wave.open(str(wav),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000);samples=w.getnframes()
  assert samples==r['full_audio']['stereo_sample_frames']
  links=[dict(href=href(folder/n),label=n)for n in('validation.json','repeat-validation.json','frame-services.json','checkpoints.json','input-plan.json','preparation.json','F8-events.json','audio-callbacks.json')];all_links.extend(links)
  native.append(dict(case=c['case'],frames=[{k:row[k]for k in FIELDS}for row in frames],checkpoints=points,plan=plan,events=events,preparation=r['preparation'],preparation_groups=r['preparation_groups'],verified_effects=r['verified_effects'],limits=r['limits'],links=links,audio=dict(href=href(wav)+'?sha='+pin,sha256=pin,sample_frames=samples)))
 accesses=[]
 for r in original['accesses']:
  contract=r.get('address_contract')or{};whole=r.get('whole_pointer_values');indices=r.get('Y_values');summary={k:v for k,v in contract.items()if not isinstance(v,(list,dict))}
  if r['classification']=='proved_disjoint_auxiliary_address_domain':assert contract.get('auxiliary_address_intersection_count')==0,(r['physical_bank'],r['cpu'])
  proof=dict(basis=r.get('proof_basis'),whole_pointer_count=None if whole is None else len(whole),whole_pointer_preview=None if whole is None else whole[:8],Y_values=indices if indices is None or len(indices)<=16 else dict(count=len(indices),preview=indices[:16]),summary=summary)
  if 'candidate_address_contract'in r:
   candidate=r['candidate_address_contract'];values=r.get('candidate_whole_pointer_values');candidate_indices=r.get('candidate_Y_values')
   proof.update(authoritative_origin=r.get('authoritative_contract_origin'),authoritative_pointer_representation=r.get('authoritative_pointer_representation'),
    candidate_domain=dict(is_classification_basis=r['candidate_contract_is_authoritative'],available=candidate is not None,
     whole_pointer_count=None if values is None else len(values),Y_value_count=None if candidate_indices is None else len(candidate_indices),
     auxiliary_address_intersection_count=None if candidate is None else candidate.get('auxiliary_address_intersection_count')))
  accesses.append(dict(physical_bank=r['physical_bank'],cpu=r['cpu'],classification=r['classification'],op=r.get('op',r.get('opcode')),pointer_zero_page=r['pointer_zero_page'],index_form='($%02X,X)'%r['pointer_zero_page']if r.get('mode')=='ix'else'($%02X),Y'%r['pointer_zero_page'],proof=proof,limits=r.get('limits',r.get('reason'))))
 static_visible={k:static[k]for k in('status','classification_counts','all_indirect_classification_counts','new_indirect_classification_counts','newly_proved_disjoint_all_count','remaining_access_count','complete_analysis_fixed_point_proven','official_target_field_names','limitations')if k in static}
 data=dict(schema='phase20-browser-data-v1',final=require_final and not missing,pending=missing,sources=sources,native=native,frame_fields=FIELDS,accesses=accesses,classifications=original['classification_counts'],static_summary=static_visible,
  source_receipts={n:compact(r)for n,r in receipts.items()},metrics=[('原核心冷启动流程',nv['case_count']),('双跑实际帧',nv['frames_both_runs']),('实际检查点',nv['checkpoint_count']),('非空文件精确复跑',nv['nonempty_repeat_artifact_checks']),('额外数据写入',nv['additional_core_memory_writes'])])
 old=ROOT/'scripts/build_phase18_browser.py';text=old.read_text();css=re.search(r'<style>(.*?)</style>',text,re.S).group(1);dependencies[str(old.relative_to(ROOT))]=sha(old)
 html=HTML.replace('__CSS__',css).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
 document=Document();document.feed(html);assert len(document.ids)==len(set(document.ids))and not document.unlabelled_selects
 links=document.refs+[l['href']for l in all_links]+[s['href']for s in sources]+[c['audio']['href']for c in native]
 broken=[]
 for url in links:
  if url.startswith(('#','http','data:')):continue
  p=(OUT/url.split('?')[0].split('#')[0]).resolve()
  if not p.is_file():broken.append(url)
 if require_final:assert not broken,broken
 js=re.findall(r'<script>(.*?)</script>',html,re.S);assert len(js)==1
 with tempfile.TemporaryDirectory(prefix='phase20-browser-')as tmp:
  script=Path(tmp)/'browser.js';script.write_text(js[0]);subprocess.run(['node','--check',str(script)],check=True,capture_output=True)
 for s in sources:assert hashlib.sha256(s['text'].encode()).hexdigest()==s['sha256']
 (OUT/'index.html').write_text(html)
 result=dict(schema='phase20-browser-static-v1',status='passed'if require_final and not missing and not broken else'draft',HTML_sha256=sha(OUT/'index.html'),builder_sha256=sha(__file__),JS_sha256=hashlib.sha256(js[0].encode()).hexdigest(),native_case_count=len(native),source_file_count=len(sources),frame_field_count=len(FIELDS),frame_projection_count=sum(len(c['frames'])for c in native),checkpoint_count=image_count,access_count=len(accesses),DOM_ID_count=len(document.ids),select_aria_label_check=True,local_link_checks=len(links),broken_links=broken,pending_receipts=missing,dependency_pins=dependencies,source_pipeline_executed=False,browser_interaction_acceptance=False)
 (OUT/'browser-static-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','HTML_sha256','native_case_count','source_file_count','checkpoint_count','access_count','pending_receipts','broken_links')}))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--require-final',action='store_true');a=p.parse_args();build(a.require_final)
if __name__=='__main__':main()
