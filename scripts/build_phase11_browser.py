#!/usr/bin/env python3
"""Static QA and evidence browser for structured scene controllers and native flows.

Reads captured artifacts/current receipts only; no core, game formulas, CPU,
IR, synthesis or controller is executed by this generator or its browser page.
"""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib,json,re,subprocess,tempfile,wave
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase11';RUN=OUT/'runtime'
MODULES={
 'battle':('战场控制器','battle_scene_controller.py','0500 / 0501 · bank12/13 A028'),
 'attack':('普通攻击控制器','attack_scene_controller.py','0540 / 0541 · bank14/15 A069'),
 'duel':('单挑控制器','duel_scene_controller.py','04A8 / 04A9 · bank23/24 B100'),
 'shared':('共享实际服务','scene_shared_services.py','queue / menu / RNG / arithmetic / fade / real farcall'),
 'initialization':('原场景初始化','scene_initialization.py','global E18B / E22F / E2E8 → E066'),
 'setup-ai':('战场部署与AI初始化','battle_setup_ai.py','physical8/9 A003 · formation / camera / original AI setup'),
 'background':('战场背景初始化','battle_background_initialization.py','physical23/24 A009 → battle background / scroll request construction')}
FIELDS=('global_state','nmi_scene','active_controller','active_main','active_phase','battle_state','attack_state','duel_state','duel_HP',
        'PPU_jobs','NMI_busy','IRQ_pending','palette_fade','text_progress_0300','text_cursor_0304','PCM_stereo_sample_frames','PCM_stop_byte')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','handoffs.json','initial-fields.json')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def relative(p):return str(p.relative_to(OUT))if p.is_relative_to(OUT)else'../../'+str(p.relative_to(ROOT))

def native_qa():
 e=read(RUN/'evidence.json');groups=[];checks=Counter()
 assert e['status']=='passed'and e['summary']['native_case_count']==len(e['native_cases'])
 assert e['core']['core_sha256']==sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')
 for pin in e['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
 for case in e['native_cases']:
  path=RUN/case['case'];v=read(path/'validation.json');rep=read(path/'repeat-validation.json');second=ROOT/rep['second_run']
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal']
  assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
  assert v['native_internal_CPU_trace']is False and v['source_CPU_comparisons_in_this_receipt']==0
  assert sha(ROOT/'scripts/capture_scene_controller_flows.py')==v['script_sha256']
  if v['initial_state']:assert sha(ROOT/v['initial_state'])==v['initial_state_sha256']
  if v['preparation_reference']:assert sha(ROOT/v['preparation_reference'])==v['preparation_sha256']
  for name,pin in v['artifact_sha256'].items():
   f=path/name;g=second/name;assert f.stat().st_size==g.stat().st_size==pin['bytes']>0 and sha(f)==sha(g)==pin['sha256'];checks['nonempty_double_run_artifacts']+=1
  for f in FORMAL:assert(path/f).read_bytes()==(second/f).read_bytes();checks['formal_JSON_exact_parity']+=1
  frames=read(path/'frame-services.json');points=read(path/'checkpoints.json');plan=read(path/'input-plan.json');calls=read(path/'audio-callbacks.json')
  assert len(frames)==v['frames']and [r['frame']for r in frames]==list(range(1,len(frames)+1))
  cursor=0
  for step in plan:assert step['start_frame']==cursor;cursor+=step['frames']
  assert cursor==len(frames)
  wav=path/'full-flow.wav'
  with wave.open(str(wav),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,v['full_audio']['stereo_sample_frames']);pcm=w.readframes(w.getnframes())
  assert len(pcm)==v['full_audio']['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==v['full_audio']['PCM_sha256']and sha(wav)==v['full_audio']['WAV_sha256']and any(pcm);checks['WAV_header_PCM_hash']+=1
  cursor=0;seen=Counter();previous=None;timeline=[]
  for row in frames:
   samples=row['PCM_stereo_sample_frames'];raw=pcm[cursor:cursor+4*samples];cursor+=4*samples
   assert samples>0 and hashlib.sha256(raw).hexdigest()==row['PCM_sha256']and bool(any(raw))==row['PCM_nonzero']and cursor==row['PCM_stop_byte'];checks['frame_PCM_segments']+=1
   controller=row['active_controller']
   if controller:
    expected={'battle':(3,(3,4),'battle_state'),'attack':(4,(5,6),'attack_state'),'duel':(5,(7,8),'duel_state')}[controller]
    assert row['nmi_scene']==expected[0]and row['global_state']in expected[1]and [row['active_main'],row['active_phase']]==row[expected[2]][:2]
    seen[(controller,row['active_main'])]+=1
   signature=tuple(str(row[k])for k in('global_state','nmi_scene','active_controller','active_main','active_phase','PPU_jobs','palette_fade','text_progress_0300','text_cursor_0304'))
   if signature!=previous:timeline.append({k:row[k]for k in('frame',*FIELDS)});previous=signature
  assert cursor==len(pcm);cursor=0
  for call in calls:
   samples=call['stereo_sample_frames'];raw=pcm[cursor:cursor+4*samples];cursor+=4*samples
   assert hashlib.sha256(raw).hexdigest()==call['pcm_sha256']and 0<=call['emulated_frame_start']<len(frames);checks['audio_callback_segments']+=1
  assert cursor==len(pcm)
  captures=[]
  for point in points:
   row=frames[point['frame']-1];png=path/point['image'];ram=path/point['RAM'];sram=path/point['SRAM']
   with Image.open(png)as image:
    assert image.size==(256,240)and hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   assert ram.stat().st_size==2048 and sha(ram)==row['RAM_sha256'];assert sram.stat().st_size==8192 and sha(sram)==row['SRAM_sha256']
   assert(path/point['state']).stat().st_size>0;checks['PNG_native_RGB_RAM_SRAM_state_checkpoints']+=1
   captures.append(dict(label=point['label'],frame=point['frame'],reason=point['reason'],image=relative(png)+'?sha='+sha(png),PNG_sha256=sha(png),
                        RAM=relative(ram),SRAM=relative(sram),state=relative(path/point['state']),fields={k:row[k]for k in FIELDS},
                        raw={k:row[k]for k in('officer_records','palette_0100_013F','audio_RAM_0700_07FF','RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256')}))
  groups.append(dict(case=case['case'],title=case['title'],frames=v['frames'],checkpoint_count=v['checkpoint_count'],observed_active_main_states=v['observed_active_main_states'],
       natural_gameplay=v['natural_gameplay'],controlled_fixture=v['controlled_fixture'],initial_state=v['initial_state'],preparation_reference=v['preparation_reference'],inherited_preparation=v['inherited_preparation'],
       captures=captures,timeline=timeline,plan=plan,final_fields=v['final_fields'],termination=v['termination'],
       audio=dict(path=relative(wav)+'?sha='+sha(wav),download=relative(wav),seconds=v['full_audio']['stereo_sample_frames']/48000,**v['full_audio']),
       links=[dict(href=relative(path/f),label=label)for f,label in [('validation.json','首跑回执'),('repeat-validation.json','两跑逐项hash'),('input-plan.json','实际原输入'),('frame-services.json','完整逐帧字段/hash'),('audio-callbacks.json','原PCM callbacks')]],
       nonempty_repeat_artifact_checks=rep['nonempty_artifact_checks'],A_confirmation_pulses=v['A_confirmation_pulses'],ordinary_A_input_steps=sum('a'in step['buttons']for step in plan),
       excluded_empty_VRAM=v['excluded_empty_VRAM'],excluded_snapshot_metadata_JSON=v['excluded_snapshot_metadata_JSON']))
 assert checks['nonempty_double_run_artifacts']==e['summary']['nonempty_repeat_artifact_checks']
 result=dict(status='passed',schema='phase11-native-static-QA-v1',checks=dict(checks),failed_count=0,
             generator_sha256=sha(Path(__file__)),native_evidence_sha256=sha(RUN/'evidence.json'),source_CPU_comparisons_in_this_receipt=0,
             limits=['PNG RGB matches the same originalcore framehash; these checks do not execute restored controllers.',
                     'WAV PCM and every frame/audio-callback segment are independently rehashed; no waveform synthesis model is claimed.',
                     'Native inactive main arrays are retainedraw and excluded from observedstate coverage.'])
 write(RUN/'static-validation.json',result);return e,groups,result

def module_data(key):
 title,filename,entries=MODULES[key];folder=OUT/key;p=folder/'validation.json';source=ROOT/'source/recovered'/filename
 if not p.exists():return dict(key=key,title=title,entries=entries,status='pending',links=[])
 r=read(p);status=r.get('status','pending');notes=[]
 if r.get('quick'):status='quick';notes.append('当前为quick回执，最终矩阵待冻结')
 pins=[];reported=r.get('source_sha256')
 if isinstance(reported,str):pins.append(dict(path=str(source.relative_to(ROOT)),sha256=reported))
 elif isinstance(reported,dict):pins.extend(dict(path=path,sha256=value)for path,value in reported.items())
 pins.extend(r.get('source_pins',[]))
 checks=[dict(path=pin['path'],expected_sha256=pin['sha256'],actual_sha256=sha(ROOT/pin['path'])if(ROOT/pin['path']).is_file()else None)for pin in pins]
 stale=[c['path']for c in checks if c['actual_sha256']!=c['expected_sha256']]
 if stale:status='source_changed';notes.append('回执所绑定文件已变或缺失：'+', '.join(stale))
 links=[dict(href=relative(f),label=label)for f,label in [(source,'具名可读源码'),(folder/'README.md','作用域与API'),(folder/'evidence.json','原bytes/表/来源'),(p,'原CPU/guards回执'),(folder/'original-ranges.asm','原范围汇编')]if f.is_file()]
 # Retain exact reported contracts/limits/callback counts; never infer a completeCPU emulator.
 receipt={k:v for k,v in r.items()if k not in('samples','rows','cases','failures','declared_RAM_addresses','compared_RAM_addresses')}
 receipt['current_pin_checks']=checks
 return dict(key=key,title=title,entries=entries,status=status,notes=notes,receipt=receipt,links=links,source_href=relative(source)if source.is_file()else None)

class Parsed(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if'id'in a:self.ids.append(a['id'])
  if tag=='a'and'href'in a:self.links.append(a['href'])

def main():
 evidence,groups,qa=native_qa();modules=[module_data(k)for k in MODULES]
 css=re.search(r'<style>([\s\S]+?)</style>',(ROOT/'analysis/phase10/index.html').read_text()).group(1)
 css+='\npre{max-height:480px;overflow:auto}.module-code{font-size:12px;line-height:1.5}audio{width:100%;max-width:620px} .controls{display:flex;flex-wrap:wrap;gap:16px;margin:20px 0}.timeline{max-height:400px;overflow:auto} .small-note{font-size:13px;color:#586362}'
 data=dict(summary=evidence['summary'],groups=groups,modules=modules,core=evidence['core'],QA=qa,
    integration=read(OUT/'source-integration.json')if(OUT/'source-integration.json').exists()else dict(status='pending'))
 html=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>战场、普通攻击与单挑控制流程</title><style>STYLES</style></head><body><main>
<small>阶段十一 · 具名控制源码 / 真实原核心回放</small><h1>战场、普通攻击与单挑控制流程</h1>
<nav><a href="../index.html">总入口</a><a href="../phase10/index.html">阶段10服务</a><a href="../../source/README.md">源码合同</a><a href="../../source/recovered/scene_coordinator.py">场景coordinator API</a><a href="#native">原画面 / 声音</a><a href="#source">源码 / 原CPU对照</a><a href="runtime/README.md">原回放说明</a></nav>
<p class="note">控制器、初始化和共享服务的源码范围，与原Nestopia的实际RGB / PCM分别检验。<strong>本页只浏览已保存证据；不执行游戏、控制器、CPU、IR或波形合成。</strong>完整场景控制与初始化，不等于独立逐cycle NES模拟器。</p>
<div class="metrics" id="metrics"></div><p id="summary"></p>
<h2 id="native">1 · 原完整核心的三条控制回放</h2><p><a href="runtime/evidence.json">native manifest</a> · <a href="runtime/validation.json">双跑总回执</a> · <a href="runtime/static-validation.json">PNG / WAV逐项静态QA</a></p>
<div class="controls"><label>回放场景 <select id="case"></select></label><label>前检查点 <select id="left"></select></label><label>后检查点 <select id="right"></select></label></div>
<p id="case-scope"></p><div class="screens"><figure><img id="before" alt="原Nestopia前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="after" alt="原Nestopia后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="transition"></p>
<h3>完整原PCM音频</h3><audio id="audio" controls preload="metadata"></audio><p id="audio-info"></p><a id="audio-download">下载原48kHz stereo WAV</a>
<p class="small-note">PCM来自原核心audio callback，16bit stereo。源码输出的音序 / APU / Namco163寄存器请求，与核心合成的声音是两个证据层。</p>
<div class="scroll"><table><thead><tr><th>实际字段</th><th>前</th><th>后</th></tr></thead><tbody id="fields"></tbody></table></div>
<h3>活跃控制 / 队列字段变化</h3><p id="timeline-info"></p><div class="timeline"><table><thead><tr><th>帧</th><th>global / NMI</th><th>active controller</th><th>main / phase</th><th>007E</th><th>0300 / 0304</th><th>原PCM样本对</th></tr></thead><tbody id="timeline"></tbody></table></div>
<p class="note">活跃主态须与global / NMI场景匹配；留下的inactive原字节不计覆盖。帧末字段不是内部CPU trace，同帧开始 / 完成的转移可能无法观察；原调用 / 栈 / flags另看源码CPU回执。</p>
<details><summary>原RAM字段、palette / 音序与哈希</summary><pre id="raw"></pre></details><details><summary>起点来源、明示准备与实际普通按键</summary><pre id="preparation"></pre></details><p id="native-links"></p>
<h2 id="source">2 · 当前具名源码与差分回执</h2><div class="modules" id="modules"></div><h3 id="module-title"></h3><p id="module-entry"></p><div class="metrics" id="module-metrics"></div><p id="module-links"></p><p id="module-note"></p>
<details><summary>精确验证范围、源与validator pins、外部依赖</summary><pre id="receipt"></pre></details><details id="code-panel"><summary>读取所选完整源码文本（不执行）</summary><pre id="code" class="module-code"></pre></details>
<h2>3 · 完成边界与原环境职责</h2><ol class="steps"><li><strong>具名场景控制</strong><br>按原主 / phase分派，推进初始化、选择、动作、结果、返回；内联pointer数据不当作代码。</li><li><strong>真实服务与caller协议</strong><br>实际保留AXYP / SP / returnPC、mapper和队列 / 图形 / 音序依赖。缺失服务或硬件输入保持明确dependency，不能默认RTS或补ready。</li><li><strong>原核心完整输出</strong><br>保存真实RGB / RAM / SRAM / PCM、原输入和两跑哈希。受控起点与冷启动流程明确区分；不把本次周期冒充整场战争胜利。</li><li><strong>逐cycle硬件</strong><br>CPU cycle、PPU扫描线、IRQ / NMI实际时间与波形合成由原核心承担，完整controller / init源码仍不等于独立NES emulator。</li></ol>
<details><summary>统一接入当前回执（若尚未落盘则pending）</summary><pre id="integration"></pre></details>
<footer>本轮的原字节、独立源码、原CPU比较、源码guards、原核心帧、PCM样本分别计数；重复调用与native帧不混称唯一玩法用例。</footer>
</main><script>const D=PAYLOAD,$=s=>document.querySelector(s),fmt=v=>v==null?'待回执':Number(v).toLocaleString(),pretty=v=>JSON.stringify(v,null,2),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const s=D.summary;$('#metrics').innerHTML=[['原核心回放',s.native_case_count],['首跑帧',s.frames_first_run],['双跑非空产物',s.nonempty_repeat_artifact_checks],['原PCM样本对',s.PCM_stereo_sample_frames_first_run]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${fmt(v)}</strong></div>`).join('');$('#summary').textContent=`${fmt(s.frames_both_runs)}帧双跑；${fmt(s.checkpoint_count)}个同源PNG/RAM/SRAM/state检查点、${fmt(s.formal_JSON_repeat_checks)}份正式JSON逐字节一致。${fmt(s.excluded_empty_VRAM)}个0B VRAM与${fmt(s.excluded_snapshot_metadata_JSON)}份snapshot metadata明确排除。额外核心准备写入=${s.additional_core_memory_writes}。`;
$('#case').innerHTML=D.groups.map((g,i)=>`<option value="${i}">${esc(g.title)}</option>`).join('');let moduleKey='battle',codeSerial=0;
function group(){return D.groups[Number($('#case').value)];}
function choose(){const g=group(),opts=g.captures.map((p,i)=>`<option value="${i}">frame${p.frame} · ${esc(p.label)}</option>`).join('');$('#left').innerHTML=$('#right').innerHTML=opts;const preferred=g.case==='duel-return'?'first-duel-main-01':g.case==='ordinary-attack-return'?'retreat-row-4':'attack-intro-4';const before=g.captures.findIndex(p=>p.label===preferred);$('#left').value=String(Math.max(0,before));$('#right').value=String(g.captures.length-1);
$('#case-scope').textContent=`${g.controlled_fixture?'继承明示受控起点':'冷启动原输入'} · ${fmt(g.frames)}帧 · 实际A输入段${g.ordinary_A_input_steps}（其中结果确认循环${g.A_confirmation_pulses}次） · 活跃首次主态 ${pretty(g.observed_active_main_states)}。${g.termination}`;
const audio=$('#audio');audio.pause();audio.src=g.audio.path;audio.load();$('#audio-download').href=g.audio.download;$('#audio-info').textContent=`${fmt(g.audio.stereo_sample_frames)}个stereo样本对 · ${g.audio.seconds.toFixed(3)}秒 · ${fmt(g.audio.PCM_bytes)} PCM字节 · WAV SHA256 ${g.audio.WAV_sha256.slice(0,20)}…`;
$('#preparation').textContent=pretty({initial_state:g.initial_state,preparation_reference:g.preparation_reference,controlled_fixture:g.controlled_fixture,additional_core_memory_writes:0,inherited_preparation:g.inherited_preparation,input_plan:g.plan});$('#timeline-info').textContent=`${g.frames}帧，字段变化时间线${g.timeline.length}条；完整逐帧RGB/PCM/hash见下载。`;
$('#timeline').innerHTML=g.timeline.map(p=>`<tr><td>${p.frame}</td><td>${p.global_state}/${p.nmi_scene}</td><td>${esc(p.active_controller??'尚无匹配scene')}</td><td>${p.active_main??'—'}/${p.active_phase??'—'}</td><td>${p.PPU_jobs}</td><td>${p.text_progress_0300}/${p.text_cursor_0304}</td><td>${p.PCM_stereo_sample_frames}</td></tr>`).join('');detail();}
function detail(){const g=group(),l=g.captures[Number($('#left').value)],r=g.captures[Number($('#right').value)];for(const[id,p]of[['before',l],['after',r]]){$('#'+id).src=p.image;$('#'+id+'-caption').textContent=`${p.label} · frame${p.frame} · 原PNG ${p.PNG_sha256.slice(0,16)}…`;}
const names={global_state:'global007A',nmi_scene:'NMI0078',active_controller:'匹配scene的活跃controller',active_main:'活跃主态',active_phase:'活跃phase',battle_state:'原battle0500/0501',attack_state:'原attack0540/0541',duel_state:'原duel04A8/04A9/04AA',duel_HP:'原duel临时HP（inactive时仅raw）',PPU_jobs:'PPU请求007E',NMI_busy:'NMI忙007B',IRQ_pending:'IRQ标志0062',palette_fade:'原fade0087..89',text_progress_0300:'原文字0300',text_cursor_0304:'原文字0304',PCM_stereo_sample_frames:'该帧PCM样本对',PCM_stop_byte:'累计PCM字节'};
$('#fields').innerHTML=Object.keys(names).map(k=>`<tr><th>${esc(names[k])}</th><td>${esc(typeof l.fields[k]==='object'?pretty(l.fields[k]):l.fields[k])}</td><td>${esc(typeof r.fields[k]==='object'?pretty(r.fields[k]):r.fields[k])}</td></tr>`).join('');$('#transition').textContent=`${l.label} → ${r.label}，global / NMI ${l.fields.global_state}/${l.fields.nmi_scene} → ${r.fields.global_state}/${r.fields.nmi_scene}。这是所选实际检查点，不推断中间未观测CPU步骤。`;
$('#raw').textContent=pretty({before:l,after:r});const links=[...g.links,{href:l.RAM,label:'前RAM'},{href:r.RAM,label:'后RAM'},{href:l.state,label:'前原state'},{href:r.state,label:'后原state'}];$('#native-links').innerHTML=links.map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');}
$('#case').addEventListener('change',choose);$('#left').addEventListener('change',detail);$('#right').addEventListener('change',detail);choose();
$('#modules').innerHTML=D.modules.map(m=>`<button type="button" data-module="${m.key}" aria-pressed="false">${esc(m.title)}</button>`).join('');
function module(key){moduleKey=key;const m=D.modules.find(p=>p.key===key),r=m.receipt||{};document.querySelectorAll('[data-module]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.module===key)));$('#module-title').textContent=m.title;$('#module-entry').textContent=m.entries;$('#module-metrics').innerHTML=[['当前回执',m.status],['原CPU用例',r.rom_cpu_case_count??r.original_CPU_case_count],['单列源码guards',r.source_guard_case_count??r.source_guard_count],['未通过',r.failed_count]].map(([k,v])=>`<div class="metric"><small>${esc(k)}</small><strong>${typeof v==='number'?fmt(v):esc(v??'待回执')}</strong></div>`).join('');$('#module-links').innerHTML=m.links.map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');$('#module-note').textContent=m.notes.join('；');$('#receipt').textContent=pretty(r);$('#code').textContent='展开后读取原完整Python文本，浏览器不执行它。';if($('#code-panel').open)loadCode();}
async function loadCode(){const m=D.modules.find(p=>p.key===moduleKey),token=++codeSerial;if(!m.source_href){$('#code').textContent='源码尚未落盘';return;}try{const response=await fetch(m.source_href);if(!response.ok)throw new Error(String(response.status));const body=await response.text();if(token===codeSerial)$('#code').textContent=body;}catch(error){if(token===codeSerial)$('#code').textContent='源码读取未完成：'+error.message;}}
document.querySelectorAll('[data-module]').forEach(b=>b.addEventListener('click',()=>module(b.dataset.module)));$('#code-panel').addEventListener('toggle',()=>{if($('#code-panel').open)loadCode();});module('battle');$('#integration').textContent=pretty(D.integration);
</script></body></html>'''
 html=html.replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False).replace('</','<\\/'));OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html)
 parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids))
 links=set(parsed.links)
 for g in groups:
  links.update(p['href']for p in g['links']);links.add(g['audio']['download']);links.update(p[k]for p in g['captures']for k in('image','RAM','SRAM','state'))
 for m in modules:links.update(p['href']for p in m['links'])
 for link in links:
  clean=urlsplit(link).path
  if clean.startswith('#')or not clean:continue
  assert(OUT/clean).resolve().is_file(),link
 js=re.search(r'<script>([\s\S]+?)</script>',html).group(1)
 with tempfile.NamedTemporaryFile('w',suffix='.js')as f:
  f.write(js);f.flush();subprocess.run(['node','--check',f.name],check=True,capture_output=True)
 result=dict(status='passed',HTML_sha256=sha(OUT/'index.html'),generator_sha256=sha(Path(__file__)),unique_DOM_ids=len(parsed.ids),local_links_checked=len(links),JS_syntax='passed',native_static_QA=qa['checks'],
      current_module_receipts=[dict(key=m['key'],status=m['status'],rom_cpu_case_count=m.get('receipt',{}).get('rom_cpu_case_count'),source_guards=m.get('receipt',{}).get('source_guard_case_count',m.get('receipt',{}).get('source_guard_count')))for m in modules],
      browser_visual_acceptance='Root performs CUA visual/interaction/audio QA; this receipt is staticonly')
 write(OUT/'browser-static-validation.json',result)
 print(json.dumps(dict(status='passed',native_QA=qa['checks'],links=len(links),HTML_sha256=result['HTML_sha256'],modules=result['current_module_receipts']),ensure_ascii=False))
if __name__=='__main__':main()
