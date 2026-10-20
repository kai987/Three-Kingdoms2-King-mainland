#!/usr/bin/env python3
"""Browse frozen native UI outputs and current independent-source receipts.

This builder and page run no game model, CPU, IR, core or synthesis. Static
PNG/WAV/hash checks leave the native files and earlier phases unchanged.
"""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib,json,re,subprocess,tempfile,wave
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase12';RUN=OUT/'runtime'
MODULES={
 'portraits':('肖像OAM服务','portrait_ui_services.py','physical25 A000 → physical26 CE1F · 两层肖像与CHR缓存'),
 'officer-ui':('姓名数据包服务','officer_ui_services.py','physical29/30 A027/A02A/A030/A033/A036/A03C · 固定F308'),
 'text':('精确文本／nametable协议','text_scene_services.py','physical29/30 A000/A003/A006 · 32原文本命令、真实caller协议'),
 'details':('十行武将资料服务','officer_details_ui_services.py','physical25 A012 → B2D7 · 十行资料、字段与装备资源')}
FIELDS=('global_state','nmi_scene','active_controller','active_main','active_phase','battle_state','attack_state',
        'UI_main_040C','UI_row_040D','UI_officer_0410','portrait_CHR_B8_B9','portrait_frame_A4','portrait_x_override_04BC',
        'OAM_byte_count','PPU_jobs','text_progress_0300','text_cursor_0304','selected_UI_officer_record','PCM_stereo_sample_frames')
RAW_FIELDS=('scratch_0000_0012','packet_0380_03BF','queue_0310_0373','palette_0100_013F','audio_RAM_0700_07FF','OAM_0200_02FF',
            'RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256')
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json','handoffs.json')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def relative(p):return str(p.relative_to(OUT))if p.is_relative_to(OUT)else'../../'+str(p.relative_to(ROOT))
def link(p,label):return dict(href=relative(p),label=label)
def address_ranges(addresses):
 values=sorted(set(addresses));parts=[]
 if not values:return '回执未列地址'
 start=last=values[0]
 for value in values[1:]:
  if value!=last+1:parts.append(f'{start:04X}..{last:04X}');start=value
  last=value
 parts.append(f'{start:04X}..{last:04X}');return ' + '.join(parts)
def native_data():
 e=read(RUN/'evidence.json');assert e['schema']=='phase12-native-ui-flows-v1'and e['status']=='passed';checks=Counter();groups=[]
 assert len(e['native_cases'])==e['summary']['native_case_count'];assert sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')==e['core']['core_sha256']
 for pin in e['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
 for case in e['native_cases']:
  v=read(RUN/case['validation']);rep=read(RUN/case['repeat_validation']);path=RUN/case['case'];second=ROOT/rep['second_run']
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal'];assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
  assert v['native_internal_CPU_trace']is False and v['source_CPU_comparisons_in_this_receipt']==0 and v['source_pipeline_installed']is False
  for field,hash_field in(('initial_state','initial_state_sha256'),('provenance','provenance_sha256'),('inherited_input_plan','inherited_input_plan_sha256')):
   if v[field]:assert sha(ROOT/v[field])==v[hash_field]
  assert sha(ROOT/'scripts/capture_ui_service_flows.py')==v['script_sha256']
  for name,pin in v['artifact_sha256'].items():
   first=path/name;other=second/name;assert first.stat().st_size==other.stat().st_size==pin['bytes']>0 and sha(first)==sha(other)==pin['sha256'];checks['nonempty_double_run_artifacts']+=1
  for name in FORMAL:assert(path/name).read_bytes()==(second/name).read_bytes();checks['formal_JSON_exact_parity']+=1
  for name in v['excluded_empty_VRAM']:assert(path/name).stat().st_size==0;checks['excluded_empty_VRAM']+=1
  checks['excluded_snapshot_metadata_JSON']+=len(v['excluded_snapshot_metadata_JSON'])
  rows=read(RUN/case['frame_services']);points=read(RUN/case['checkpoints']);plan=read(RUN/case['input_plan']);calls=read(path/'audio-callbacks.json')
  assert len(rows)==case['frames']==v['frames']and len(points)==v['checkpoint_count'];assert[row['frame']for row in rows]==list(range(1,len(rows)+1))
  cursor=0
  for step in plan:assert step['start_frame']==cursor;cursor+=step['frames']
  assert cursor==len(rows)
  wav=RUN/case['full_WAV'];audio=v['full_audio']
  with wave.open(str(wav),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,audio['stereo_sample_frames']);pcm=w.readframes(w.getnframes())
  assert len(pcm)==audio['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==audio['PCM_sha256']and sha(wav)==audio['WAV_sha256']and any(pcm);checks['WAV_header_PCM_hash']+=1
  cursor=0;timeline=[];previous=None
  for row in rows:
   count=row['PCM_stereo_sample_frames'];part=pcm[cursor:cursor+4*count];cursor+=4*count
   assert count>0 and hashlib.sha256(part).hexdigest()==row['PCM_sha256']and bool(any(part))==row['PCM_nonzero']and cursor==row['PCM_stop_byte'];checks['frame_PCM_segments']+=1
   if row['active_controller']:
    expected={'battle':(3,(3,4),'battle_state'),'attack':(4,(5,6),'attack_state'),'duel':(5,(7,8),'duel_state')}[row['active_controller']]
    assert row['nmi_scene']==expected[0]and row['global_state']in expected[1]and[row['active_main'],row['active_phase']]==row[expected[2]][:2]
   signature=tuple(str(row[k])for k in('global_state','nmi_scene','active_controller','active_main','active_phase','UI_row_040D','PPU_jobs','text_progress_0300','text_cursor_0304'))
   if signature!=previous:timeline.append({k:row[k]for k in('frame',*FIELDS)});previous=signature
  assert cursor==len(pcm);cursor=0
  for call in calls:
   count=call['stereo_sample_frames'];part=pcm[cursor:cursor+4*count];cursor+=4*count
   assert hashlib.sha256(part).hexdigest()==call['pcm_sha256']and 0<=call['emulated_frame_start']<len(rows);checks['audio_callback_segments']+=1
  assert cursor==len(pcm);captures=[]
  for point in points:
   row=rows[point['frame']-1];png=path/point['image'];ram=path/point['RAM'];sram=path/point['SRAM'];state=path/point['state']
   with Image.open(png)as image:assert image.size==(256,240)and hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   assert ram.stat().st_size==2048 and sha(ram)==row['RAM_sha256'];assert sram.stat().st_size==8192 and sha(sram)==row['SRAM_sha256'];assert state.stat().st_size>0
   ram_raw=ram.read_bytes();record=row['selected_UI_officer_record']
   assert ram_raw[0x40D]==row['UI_row_040D']and ram_raw[0x410]==row['UI_officer_0410']
   if record and record['officer_id']<237:
    offset=0x3C0+12*record['officer_id'];assert sram.read_bytes()[offset:offset+12].hex()==record['raw']
   checks['PNG_native_RGB_RAM_SRAM_state_checkpoints']+=1
   display_label='进入资料：继承旧FF（非完成）'if point['label']=='info-rows-complete'else point['label']
   captures.append(dict(label=point['label'],display_label=display_label,frame=point['frame'],reason=point['reason'],image=relative(png)+'?sha='+sha(png),PNG_sha256=sha(png),RAM=relative(ram),SRAM=relative(sram),state=relative(state),fields={k:row[k]for k in FIELDS},raw={k:row[k]for k in RAW_FIELDS}))
  groups.append(dict(case=case['case'],title=case['title'],frames=v['frames'],checkpoint_count=v['checkpoint_count'],captures=captures,timeline=timeline,
   frame_views=[{k:row[k]for k in('frame',*FIELDS)}for row in rows],observed_active_main_states=v['observed_active_main_states'],verified_effects=v['verified_effects'],
   plan=plan,initial_state=v['initial_state'],provenance=v['provenance'],inherited_start_natural=v['inherited_start_natural'],inherited_controlled_fixture=v['inherited_controlled_fixture'],inherited_preparation=v['inherited_preparation'],termination=v['termination'],
   audio=dict(path=relative(wav)+'?sha='+sha(wav),download=relative(wav),seconds=audio['stereo_sample_frames']/48000,**audio),
   links=[link(path/name,label)for name,label in [('validation.json','首跑回执'),('repeat-validation.json','双跑逐项hash'),('input-plan.json','实际原按键'),('frame-services.json','完整每帧字段/hash'),('audio-callbacks.json','原PCM callbacks')]]))
 summary=e['summary'];assert checks['nonempty_double_run_artifacts']==summary['nonempty_repeat_artifact_checks'];assert checks['formal_JSON_exact_parity']==summary['formal_JSON_repeat_checks'];assert checks['PNG_native_RGB_RAM_SRAM_state_checkpoints']==summary['checkpoint_count']
 assert checks['excluded_empty_VRAM']==summary['excluded_empty_VRAM']and checks['excluded_snapshot_metadata_JSON']==summary['excluded_snapshot_metadata_JSON'];return e,groups,dict(checks)

def collect_pins(receipt,source):
 pins=[];value=receipt.get('source_sha256')
 if isinstance(value,str):pins.append(dict(path=str(source.relative_to(ROOT)),sha256=value))
 elif isinstance(value,dict):pins.extend(dict(path=p,sha256=h)for p,h in value.items())
 for key in('source_pins','dependency_pins','source_and_validator_pins'):pins.extend(receipt.get(key,[]))
 pins.extend(dict(path=p,sha256=h)for p,h in receipt.get('dependencies',{}).items())
 dedup={p['path']:p['sha256']for p in pins}
 return[dict(path=p,expected_sha256=h,actual_sha256=sha(ROOT/p)if(ROOT/p).is_file()else None)for p,h in dedup.items()]
def module_data(key):
 title,filename,entries=MODULES[key];folder=OUT/key;source=ROOT/'source/recovered'/filename;r=read(folder/'validation.json');pins=collect_pins(r,source);notes=[];status=r['status']
 if r.get('quick'):status='quick';notes.append('当前quick矩阵尚未冻结')
 stale=[p['path']for p in pins if p['actual_sha256']!=p['expected_sha256']]
 if stale:status='source_changed';notes.append('回执pins尚待刷新：'+','.join(stale))
 complete=r.get('original_complete_case_count',r.get('complete_return_count'));prefix=r.get('original_prefix_case_count',r.get('strict_prefix_count'))
 assert r['rom_cpu_case_count']==complete+prefix
 ram=r.get('comparison',{}).get('RAM_bytes',r.get('all_RAM_compared_bytes',len(r.get('declared_RAM_addresses',[]))))
 stack=r.get('comparison',{}).get('free_CPU_stack_residue','excluded'if r.get('free_stack_residue_excluded')else'included'if ram==2048 else'not_declared')
 receipt={k:v for k,v in r.items()if k not in('samples','rows','failures','declared_RAM_addresses','actual_call_fixtures')};receipt['current_pin_checks']=pins
 ram_scope=address_ranges(r.get('declared_RAM_addresses',range(2048)if ram==2048 else[]))
 return dict(key=key,title=title,entries=entries,status=status,notes=notes,complete=complete,prefix=prefix,RAM_bytes=ram,RAM_scope=ram_scope,free_stack_residue=stack,
  SRAM_bytes=r.get('comparison',{}).get('SRAM_bytes',r.get('all_SRAM_compared_bytes')),receipt=receipt,source_href=relative(source),
  links=[link(p,label)for p,label in [(source,'完整具名源码'),(folder/'README.md','作用域与API'),(folder/'evidence.json','原bytes/表/来源'),(folder/'validation.json','原CPU/guards回执'),(folder/'original-ranges.asm','原范围汇编')]if p.is_file()])
class Parsed(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if'id'in values:self.ids.append(values['id'])
  if tag=='a'and'href'in values:self.links.append(values['href'])
def main():
 e,groups,qa=native_data();modules=[module_data(k)for k in MODULES];details=read(OUT/'details/evidence.json')['row_field_mapping'];canonical=read(OUT/'dependencies/source-integration.json')
 canonical_view={k:v for k,v in canonical.items()if k not in('rows','failures','declared_RAM_addresses')};canonical_view['current_pin_checks']=collect_pins(canonical,ROOT/'source/recovered/scene_coordinator.py');canonical_view['RAM_scope']=address_ranges(canonical['declared_RAM_addresses'])
 canonical_stale=[p['path']for p in canonical_view['current_pin_checks']if p['actual_sha256']!=p['expected_sha256']];canonical_view['current_pins_match']=not canonical_stale
 css=re.search(r'<style>([\s\S]+?)</style>',(ROOT/'analysis/phase11/index.html').read_text()).group(1)
 css+='\n.frame-controls{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}.row-buttons{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.row-buttons button{padding:8px 12px}pre{max-height:480px;overflow:auto}audio{width:100%;max-width:620px}'
 data=dict(summary=e['summary'],core=e['core'],groups=groups,modules=modules,detail_rows=details,canonical=canonical_view,QA=qa)
 html=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>肖像、姓名、文本与武将资料</title><style>STYLES</style></head><body><main>
<small>阶段十二 · 独立UI源码 / 原核心RGB与PCM</small><h1>肖像、姓名、文本与武将资料</h1>
<nav><a href="../index.html">总入口</a><a href="../phase11/index.html">阶段11控制器</a><a href="../../source/README.md">源码合同</a><a href="../../source/recovered/scene_coordinator.py">coordinator API</a><a href="#native">原画面／声音</a><a href="#details">十行资料</a><a href="#source">四模块源码</a><a href="runtime/README.md">原回放说明</a></nav>
<p class="note">四个独立UI模块按原调用栈、银行与队列协议对照；原Nestopia的实际画面／声音另由完整核心生成。本页只浏览保存证据，不运行游戏、CPU、IR或波形合成。资料／姓名请求与一帧NES硬件执行分别计数。</p>
<div class="metrics" id="metrics"></div><p id="summary"></p>
<h2 id="native">1 · 原核心资料页与普通攻击回放</h2><p><a href="runtime/evidence.json">native manifest</a> · <a href="runtime/validation.json">双跑总回执</a> · <a href="browser-static-validation.json">本页PNG／WAV静态QA</a></p>
<div class="controls"><label>原回放 <select id="case"></select></label><label>前检查点 <select id="left"></select></label><label>后检查点 <select id="right"></select></label></div>
<p id="case-scope"></p><div class="screens"><figure><img id="before" alt="原Nestopia前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="after" alt="原Nestopia后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="transition"></p>
<h3>完整原PCM音频</h3><audio id="audio" controls preload="metadata"></audio><p id="audio-info"></p><a id="audio-download">下载原48kHz stereo WAV</a><p class="small-note">原核心audio callback输出的16bit stereo PCM，与源码音序／寄存器请求是两个证据层。</p>
<h3>逐帧UI字段比较</h3><div class="frame-controls"><label>前字段帧 <select id="frame-left"></select></label><label>后字段帧 <select id="frame-right"></select></label></div><p id="field-frame-note"></p>
<div class="scroll"><table><thead><tr><th>原字段</th><th>前字段帧</th><th>后字段帧</th></tr></thead><tbody id="fields"></tbody></table></div>
<details><summary>所选截图的packet／scratch／OAM／palette及哈希</summary><pre id="raw"></pre></details><details><summary>起点、继承准备、真实普通按键和验证结果</summary><pre id="preparation"></pre></details><p id="native-links"></p>
<h3>活跃控制／资料游标／请求变化</h3><p id="timeline-info"></p><div class="timeline"><table><thead><tr><th>帧</th><th>global/NMI</th><th>活跃控制 main/phase</th><th>040D游标</th><th>007E</th><th>0300/0304</th></tr></thead><tbody id="timeline"></tbody></table></div>
<p class="note">逐帧字段不是内部CPU trace。inactive数组保留原字节，不计活跃主态覆盖；同一帧结束前的短暂转移未必可见。自选字段帧与PNG检查点分别标明，不把未保存PNG的帧冒充截图。</p>
<h2 id="details">2 · 原十行资料与永久记录来源</h2><p><a href="details/evidence.json">十行字段／原入口证据</a> · <a href="details/README.md">真实队列／sentinel合同</a> · <a href="portraits/portrait-identity-atlas.png">237姓名／肖像诊断图</a></p>
<p>下列按钮跳到实测040D游标检查点。040D=n表示待生产第n行；producer提交后才递增，PPU还可等待消费，因此不把该瞬间称为第n行已经绘制。稳定完整画面见info-open。</p><div class="row-buttons" id="detail-rows"></div>
<div class="scroll"><table><thead><tr><th>原row</th><th>入口</th><th>作用／字段</th><th>recordbyte</th><th>原写入／边界</th></tr></thead><tbody id="row-fields"></tbody></table></div>
<p class="small-note">诊断图是原2bpp／sprite模板灰度解码，非原核心截图、原palette或OCR。原资料页／前后记录来自上面的原截图与逐帧SRAM字段。</p>
<h2 id="source">3 · 四个独立源码模块与准确比较范围</h2><div class="modules" id="modules"></div><h3 id="module-title"></h3><p id="module-entry"></p><div class="metrics" id="module-metrics"></div><p id="module-scope"></p><p id="module-note"></p><p id="module-links"></p>
<div class="scroll"><table><thead><tr><th>模块</th><th>原CPU总数</th><th>完整返回</th><th>严格prefix</th><th>声明RAM</th><th>CPU自由栈残留</th><th>SRAM</th><th>guards</th></tr></thead><tbody id="scope-table"></tbody></table></div>
<details><summary>所选模块全部验证合同、guards及current pins</summary><pre id="receipt"></pre></details><details id="code-panel"><summary>所选完整源码文本（读取但不执行）</summary><pre id="code" class="module-code"></pre></details>
<h2>4 · 普通攻击远端接入与完成边界</h2><div class="metrics" id="canonical-metrics"></div><p id="canonical-note"></p><p><a href="dependencies/source-integration.json">当前canonical原CPU接入回执</a> · <a href="dependencies/README.md">合法域、unknownhelper与scope</a></p><details><summary>canonical精确比较域／pins／剩余边界</summary><pre id="canonical"></pre></details>
<ol class="steps"><li><strong>肖像与完整参数卡分别恢复</strong><br>25A000生成两层OAM及CHR缓存；25A012才是真十行属性卡；29A030/A03C只是姓名包。</li><li><strong>请求、消费与真实caller</strong><br>姓名／资料producer不替代PPU consumer；busy早RTS保留队列，缺硬件输入保持dependency，不能fake ready／RTS。</li><li><strong>源码与原核心分开验证</strong><br>原CPU矩阵逐项比RAM／SRAM／AXYP／PC/SP／ports／banks；各自RAM范围不同。native双跑证明原输入后的原RGB／PCM一致，不证明恢复源码自己产生这些像素或声音。</li><li><strong>原NES环境仍负责时间与合成</strong><br>软件UI／控制服务完整，不等于独立cycle CPU、PPU扫描线、IRQ/NMI时间与APU/Namco163波形合成已完成。</li></ol>
<footer>完整返回、循环前缀、source guards、原核心帧、保存检查点和PCM样本分别计数，不混称唯一玩法用例。</footer></main>
<script>const D=PAYLOAD,$=s=>document.querySelector(s),fmt=v=>v==null?'待回执':Number(v).toLocaleString(),pretty=v=>JSON.stringify(v,null,2),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const s=D.summary;$('#metrics').innerHTML=[['原核心回放',s.native_case_count],['首跑帧',s.frames_first_run],['双跑非空产物',s.nonempty_repeat_artifact_checks],['原PCM样本对',s.PCM_stereo_sample_frames_first_run]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${fmt(v)}</strong></div>`).join('');$('#summary').textContent=`${fmt(s.frames_both_runs)}帧双跑；${fmt(s.checkpoint_count)}个PNG/RAM/SRAM/state检查点（部分同帧别名），${fmt(s.formal_JSON_repeat_checks)}份正式JSON逐字节相同。${fmt(s.excluded_empty_VRAM)}个0B VRAM和${fmt(s.excluded_snapshot_metadata_JSON)}份目录metadata明确排除。本轮手动核心准备写入=${s.additional_core_memory_writes}。`;
$('#case').innerHTML=D.groups.map((g,i)=>`<option value="${i}">${esc(g.title)}</option>`).join('');let moduleKey='details',codeSerial=0;
function group(){return D.groups[Number($('#case').value)];}
function choose(){const g=group(),opts=g.captures.map((p,i)=>`<option value="${i}">frame${p.frame} · ${esc(p.display_label)}</option>`).join('');$('#left').innerHTML=$('#right').innerHTML=opts;
const labels=g.case==='battle-officer-info'?['info-open','info-closed']:['retreat-row-4','final'];$('#left').value=String(Math.max(0,g.captures.findIndex(p=>p.label===labels[0])));$('#right').value=String(Math.max(0,g.captures.findIndex(p=>p.label===labels[1])));
const frames=g.frame_views.map(p=>`<option value="${p.frame}">frame${p.frame} · 040D=${p.UI_row_040D} · ${p.active_controller??'无匹配scene'} ${p.active_main??'—'}/${p.active_phase??'—'}</option>`).join('');$('#frame-left').innerHTML=$('#frame-right').innerHTML=frames;
$('#case-scope').textContent=`${g.inherited_start_natural?'继承冷启动原输入的自然战场起点':'继承已明示受控起点'} · ${fmt(g.frames)}帧。${g.termination}`;const audio=$('#audio');audio.pause();audio.src=g.audio.path;audio.load();$('#audio-download').href=g.audio.download;$('#audio-info').textContent=`${fmt(g.audio.stereo_sample_frames)} stereo样本对 · ${g.audio.seconds.toFixed(3)}秒 · WAV SHA ${g.audio.WAV_sha256.slice(0,20)}…`;
$('#preparation').textContent=pretty({initial_state:g.initial_state,provenance:g.provenance,inherited_start_natural:g.inherited_start_natural,inherited_controlled_fixture:g.inherited_controlled_fixture,inherited_preparation:g.inherited_preparation,additional_core_memory_writes:0,input_plan:g.plan,verified_effects:g.verified_effects});$('#timeline-info').textContent=`${g.frames}原帧，控制／UI／请求变化${g.timeline.length}条；每帧完整数据另有JSON。`;
$('#timeline').innerHTML=g.timeline.map(p=>`<tr><td>${p.frame}</td><td>${p.global_state}/${p.nmi_scene}</td><td>${esc(p.active_controller??'无匹配scene')} ${p.active_main??'—'}/${p.active_phase??'—'}</td><td>${p.UI_row_040D}</td><td>${p.PPU_jobs}</td><td>${p.text_progress_0300}/${p.text_cursor_0304}</td></tr>`).join('');detail();}
function detail(){const g=group(),l=g.captures[Number($('#left').value)],r=g.captures[Number($('#right').value)];for(const[id,p]of[['before',l],['after',r]]){$('#'+id).src=p.image;$('#'+id+'-caption').textContent=`${p.display_label} · 原frame${p.frame} · PNG ${p.PNG_sha256.slice(0,16)}…`;}
$('#transition').textContent=`实际检查点 ${l.display_label} → ${r.display_label}：global/NMI ${l.fields.global_state}/${l.fields.nmi_scene} → ${r.fields.global_state}/${r.fields.nmi_scene}。`;
$('#frame-left').value=String(l.frame);$('#frame-right').value=String(r.frame);fields();$('#raw').textContent=pretty({before:l,after:r});$('#native-links').innerHTML=[...g.links,{href:l.RAM,label:'前RAM'},{href:r.RAM,label:'后RAM'},{href:l.SRAM,label:'前SRAM'},{href:r.SRAM,label:'后SRAM'},{href:l.state,label:'前state'},{href:r.state,label:'后state'}].map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');}
function fields(){const g=group(),l=g.frame_views[Number($('#frame-left').value)-1],r=g.frame_views[Number($('#frame-right').value)-1],lc=g.captures[Number($('#left').value)],rc=g.captures[Number($('#right').value)];$('#field-frame-note').textContent=`字段frame${l.frame}／${r.frame}；上方PNG检查点仍是frame${lc.frame}／${rc.frame}。字段帧可独立选择，未保存PNG的帧不会产生截图。`;
const names={global_state:'global007A',nmi_scene:'NMI0078',active_controller:'匹配场景的活跃控制',active_main:'活跃main',active_phase:'活跃phase',battle_state:'原battle0500/0501',attack_state:'原attack0540/0541(inactive仅raw)',UI_main_040C:'资料名单索引040C',UI_row_040D:'资料生产游标040D(FF停止)',UI_officer_0410:'原资料ID0410',portrait_CHR_B8_B9:'肖像CHR缓存B8/B9',portrait_frame_A4:'原肖像frameA4',portrait_x_override_04BC:'原X override04BC',OAM_byte_count:'原OAMcursor007C',PPU_jobs:'请求007E',text_progress_0300:'文字进度0300',text_cursor_0304:'文字游标0304',selected_UI_officer_record:'0410引用原12byte记录(inactive仅raw)',PCM_stereo_sample_frames:'该帧原PCM样本对'};
$('#fields').innerHTML=Object.entries(names).map(([k,name])=>`<tr><th>${esc(name)}</th><td>${esc(typeof l[k]==='object'?pretty(l[k]):l[k])}</td><td>${esc(typeof r[k]==='object'?pretty(r[k]):r[k])}</td></tr>`).join('');}
$('#case').addEventListener('change',choose);$('#left').addEventListener('change',detail);$('#right').addEventListener('change',detail);$('#frame-left').addEventListener('change',fields);$('#frame-right').addEventListener('change',fields);choose();
$('#detail-rows').innerHTML=D.detail_rows.map(p=>`<button type="button" data-row="${p.row}">观察040D=${p.row}</button>`).join('');$('#row-fields').innerHTML=D.detail_rows.map(p=>`<tr><td>${p.row}</td><td>$${p.handler.toString(16).toUpperCase()}</td><td>${esc(p.label)}</td><td>${esc(pretty(p.record_offsets))}</td><td>${esc(p.behavior)}<br>${esc(p.outputs.join(' / '))}</td></tr>`).join('');document.querySelectorAll('[data-row]').forEach(b=>b.addEventListener('click',()=>{$('#case').value=String(D.groups.findIndex(g=>g.case==='battle-officer-info'));choose();const g=group(),index=g.captures.findIndex(p=>p.label==='info-row-'+b.dataset.row.padStart(2,'0'));if(index>=0){$('#left').value=String(index);$('#right').value=String(g.captures.findIndex(p=>p.label==='info-open'));detail();}document.querySelectorAll('[data-row]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));}));
$('#modules').innerHTML=D.modules.map(m=>`<button type="button" data-module="${m.key}" aria-pressed="false">${esc(m.title)}</button>`).join('');$('#scope-table').innerHTML=D.modules.map(m=>`<tr><th>${esc(m.title)}</th><td>${fmt(m.receipt.rom_cpu_case_count)}</td><td>${fmt(m.complete)}</td><td>${fmt(m.prefix)}</td><td>${fmt(m.RAM_bytes)}</td><td>${esc(m.free_stack_residue)}</td><td>${fmt(m.SRAM_bytes)}</td><td>${fmt(m.receipt.source_guard_case_count)}</td></tr>`).join('');
function module(key){moduleKey=key;const m=D.modules.find(p=>p.key===key),r=m.receipt;document.querySelectorAll('[data-module]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.module===key)));$('#module-title').textContent=m.title;$('#module-entry').textContent=m.entries;$('#module-metrics').innerHTML=[['当前回执',m.status],['完整返回',m.complete],['原循环prefix',m.prefix],['source guards',r.source_guard_case_count]].map(([k,v])=>`<div class="metric"><small>${esc(k)}</small><strong>${typeof v==='number'?fmt(v):esc(v)}</strong></div>`).join('');$('#module-scope').textContent=`原CPU总数${fmt(r.rom_cpu_case_count)} = 完整返回${fmt(m.complete)} + 严格prefix${fmt(m.prefix)}；RAM ${m.RAM_scope} 共${fmt(m.RAM_bytes)}字节，CPU自由栈残留=${m.free_stack_residue}，SRAM${fmt(m.SRAM_bytes)}字节；真实AXYP/SP/PC、银行及有序ports另见精确回执。`;$('#module-note').textContent=m.notes.join('；');$('#module-links').innerHTML=m.links.map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');$('#receipt').textContent=pretty(r);$('#code').textContent='展开读取所选完整Python文本；浏览器不执行。';if($('#code-panel').open)loadCode();}
async function loadCode(){const m=D.modules.find(p=>p.key===moduleKey),token=++codeSerial;try{const response=await fetch(m.source_href);if(!response.ok)throw new Error(String(response.status));const text=await response.text();if(token===codeSerial)$('#code').textContent=text;}catch(error){if(token===codeSerial)$('#code').textContent='源码文本读取未完成：'+error.message;}}
document.querySelectorAll('[data-module]').forEach(b=>b.addEventListener('click',()=>module(b.dataset.module)));$('#code-panel').addEventListener('toggle',()=>{if($('#code-panel').open)loadCode();});module('details');const c=D.canonical;$('#canonical-metrics').innerHTML=[['原CPU比较',c.actual_ROM_CPU_comparison_count],['完整返回',c.complete_return_count],['严格prefix',c.strict_prefix_count],['source guards',c.source_guard_count]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${fmt(v)}</strong></div>`).join('');$('#canonical-note').textContent=`当前canonical状态${c.status}，currentpins=${c.current_pins_match}，RAM ${c.RAM_scope} 共${fmt(c.compared_RAM_bytes)}／SRAM${fmt(c.compared_SRAM_bytes)}字节，register contract=${c.register_contract}。按当前冻结回执读取，不把发现层原helper调用数算进生产源码比较。`;$('#canonical').textContent=pretty(c);
</script></body></html>'''
 html=html.replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False).replace('</','<\\/'));OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html)
 parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids));links=set(parsed.links)
 for g in groups:
  links.update(p['href']for p in g['links']);links.add(g['audio']['download']);links.update(p[k]for p in g['captures']for k in('image','RAM','SRAM','state'))
 for m in modules:links.update(p['href']for p in m['links']);links.add(m['source_href'])
 for path in links:
  clean=urlsplit(path).path
  if clean and not clean.startswith('#')and clean!='browser-static-validation.json':assert(OUT/clean).resolve().is_file(),path
 js=re.search(r'<script>([\s\S]+?)</script>',html).group(1)
 with tempfile.NamedTemporaryFile('w',suffix='.js')as f:f.write(js);f.flush();subprocess.run(['node','--check',f.name],check=True,capture_output=True)
 receipt=dict(schema='phase12-browser-static-v1',status='passed',HTML_sha256=sha(OUT/'index.html'),generator_sha256=sha(Path(__file__)),unique_DOM_ids=len(parsed.ids),local_links_checked=len(links),JS_syntax='passed',native_static_QA=qa,native_evidence_sha256=sha(RUN/'evidence.json'),native_files_modified=False,
  modules=[dict(key=m['key'],status=m['status'],CPU=m['receipt']['rom_cpu_case_count'],complete=m['complete'],prefix=m['prefix'],RAM_bytes=m['RAM_bytes'],source_guards=m['receipt']['source_guard_case_count'])for m in modules],canonical=dict(status=canonical['status'],CPU=canonical['actual_ROM_CPU_comparison_count'],complete=canonical['complete_return_count'],prefix=canonical['strict_prefix_count'],RAM_bytes=canonical['compared_RAM_bytes'],current_pins_match=not canonical_stale),
  field_frames=sum(len(g['frame_views'])for g in groups),detail_rows=len(details),browser_visual_acceptance='Root performs CUA interaction/PNG/audio QA; this receipt is static only')
 (OUT/'browser-static-validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');assert(OUT/'browser-static-validation.json').is_file();print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
