#!/usr/bin/env python3
"""Browse frozen phase14 receipts/native media; never execute game models.

Root owns CUA browser/PNG/audio acceptance. This builder checks JSON, current
pins, both original artifact copies, actual WAV/PNG bytes and script syntax.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from collections import Counter
import argparse,hashlib,json,re,subprocess,tempfile,wave,sys
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase14';RUN=OUT/'runtime'
MODULES={
 'boot':('固定冷启动／复位服务','boot_initialization.py','fixed31 E000→E066；真实PPU输入等待、RAM/栈替换、SRAM保留与诊断边界'),
 'domestic':('内政合作控制器','domestic_cooperation_controller.py','physical10/11 A000→A00F；6053位置静态闭包／具名子过程；请求、预算、城市选择与实际ack等待'),
 'tactical':('战术合作控制器','tactical_cooperation_controller.py','physical8/9 A000→A02D；八策略合作请求、扫描、行动提交、B517协议与资源边界'),
 'city-cooperation-ui':('城市合作UI辅助服务','city_cooperation_ui_services.py','physical29/30 A042→AA37／AB38；标题、原13-byte徽记/OAM与真实队列请求')}
FIELDS=('global_state','nmi_scene','active_controller','active_main','active_phase','calendar_year_6F00','calendar_month_zero_based_6F01',
 'ruler_6F03','turn_slot_6F04','remaining_budget_raw_6F05','event_flag_6F06','cooperation_status_6F8B','domestic_phase_6F5B','domestic_budget_6F5D','domestic_city_6F5E',
 'menu_cursor_0012','buttons_0081_0086','PPU_jobs_007E','NMI_busy_007B','text_progress_0300','text_cursor_0304','title_intro_counter_0471_0470',
 'city11_gold','city11_reserve_raw16','recruitment_quantity_raw_048E_048F','observer_officer_records','PCM_stereo_sample_frames')
RAW_FIELDS=('city_state_0400_040F','title_state_0540_0544','battle_state_0500_050F','calendar_and_turn_6F00_6F06','ruler_records_6F07_6F3E',
 'domestic_control_6F5B_6F62','cooperation_6F8B_6FAB','battery_flags_6FE2_6FEB','control_0470_047F','palette_0100_013F','text_queue_0310_037F',
 'mapper_main_DE_DF_E0','mapper_NMI_E1_E2_E3','IRQ_fields_0068_0075','audio_RAM_0700_07FF','scratch_0000_001F','city11_record',
 'RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256')
DEFAULTS={
 'cold-city-domestic-cycle':('city-commands','next-player-world-return'),
 'core-reset-battery-retention':('before-core-reset','post-core-reset-title'),
 'title-intro-software-restart':('software-restart-boot-frame-3073','software-restarted-title')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def relative(p):return str(p.relative_to(OUT))if p.is_relative_to(OUT)else'../../'+str(p.relative_to(ROOT))
def link(p,label):return dict(href=relative(p),label=label)
def trim(r):return{k:v for k,v in r.items()if k not in('rows','cases','failures','original_cases','declared_RAM_addresses','actual_call_fixtures','fixtures','executed_original_locations')}
def pins(r,source=None):
 result={}
 for key in('source_and_validator_sha256','source_sha256','pins','dependencies','native_input_sha256'):
  value=r.get(key)
  if isinstance(value,str)and key=='source_sha256'and source is not None:result[str(source.relative_to(ROOT))]=value
  elif isinstance(value,dict):
   for path,digest in value.items():
    if isinstance(digest,str)and len(digest)==64 and '/'in path:result[path]=digest
 for key in('dependency_pins','source_pins','source_and_validator_pins'):
  value=r.get(key,[])
  if isinstance(value,list):
   for p in value:
    if isinstance(p,dict)and'path'in p and'sha256'in p:result[p['path']]=p['sha256']
 for name in('validator','analyzer'):
  if r.get(name+'_path')and r.get(name+'_sha256'):result[r[name+'_path']]=r[name+'_sha256']
 return[dict(path=p,expected_sha256=h,actual_sha256=sha(ROOT/p)if(ROOT/p).is_file()else None)for p,h in result.items()]
def current_pin_status(values):return all(p['expected_sha256']==p['actual_sha256']for p in values)
def module_data(key):
 title,filename,entries=MODULES[key];folder=OUT/key;source=ROOT/'source/recovered'/filename;path=folder/'validation.json';r=read(path)if path.is_file()else{}
 checked=pins(r,source);status=r.get('status','pending');notes=[]
 if r.get('quick'):status='quick';notes.append('quick矩阵不能当最终验证')
 if checked and not current_pin_status(checked):status='source_changed';notes.append('当前依赖pin与回执不一致')
 if source.is_file()and not any(p['path']==str(source.relative_to(ROOT))for p in checked):status='unconfirmed_source_pin';notes.append('回执缺该生产模块源码pin')
 cpu,complete,prefix=r.get('rom_cpu_case_count'),r.get('complete_return_count'),r.get('strict_prefix_count')
 if cpu is not None:assert cpu==complete+prefix
 if key=='boot':notes.append('complete包含真实caller RTS和E066 reset boundary，不能一律叫RTS；全70bit echo匹配的F41E永久诊断仅受控CPU fixture，不称普通native启动')
 if key=='domestic':notes.append('complete按mode分列：纯Source与验证借原fixedhelper不同；缺服务prefix和真实ack等待prefix也分别列。所有数量由当前回执模式表读取，helper调用不是CPU病例')
 if key=='city-cooperation-ui':notes.append('真实0380请求、7E标志和徽记/OAM生产者；不声称已消费PPU、选继承人或写6F8B ack。rawID237..255只验证原字节寻址边界，非有效武将身份')
 if key=='tactical':notes.append('B517严格前缀保持真实协议界限；独立源码block数不是原指令/CPU病例，旧phase7原战场起点只在独立CPU fixture中明确继承')
 comp=r.get('comparison',r.get('comparison_scope',{}));ret=trim(r);ret['current_pin_checks']=checked
 callbacks=r.get('source_original_CPU_callbacks',r.get('production_original_CPU_callbacks'));borrowed=r.get('original_fixed_helper_calls',0 if r else None)
 files=[(source,'完整可读源码'),(folder/'README.md','范围与API'),(folder/'evidence.json','原bytes／表／REA'),(path,'当前CPU／guards回执')]
 for name in('raw.asm','original.asm','original-ranges.asm','static-catalog.json','offline-control-graph.json','executed-instructions.json'):
  files.append((folder/name,name))
 return dict(key=key,title=title,entries=entries,status=status,CPU=cpu,complete=complete,prefix=prefix,guards=r.get('source_guard_case_count'),
  verification_CPU_callbacks=borrowed,production_CPU_callbacks=callbacks,comparison=comp,counts=r.get('counts',{}),completion_kinds=r.get('completion_kinds',{}),
  notes=notes,receipt=ret,source_href=relative(source)if source.is_file()else None,links=[link(p,label)for p,label in files if p.is_file()])
def integration_data(path):
 if not path.is_file():return dict(status='pending',path=relative(path),note='最终纯源码整合回执尚待root冻结')
 r=read(path);checked=pins(r,ROOT/'source/recovered/scene_coordinator.py');result=trim(r);result['current_pin_checks']=checked;result['current_pins_match']=current_pin_status(checked);result['path']=relative(path)
 if not result['current_pins_match']:result['status']='source_changed'
 result['linked_receipts']=[link(p,label)for p,label in((OUT/'boot-integration.json','reset独立整合回执'),(OUT/'cooperation-integration.json','内政／战术合作独立整合回执'))if p.is_file()]
 return result
def label(name):
 names={'city-commands':'首次玩家城市命令：189年1月／行动3','next-player-world-return':'189年2月玩家世界光标：行动恢复3',
  'next-player-turn-message':'六君主合作后：二月玩家回合原消息','before-core-reset':'原核心复位前：真实城市画面',
  'post-core-reset-title':'原核心复位后：原标题重建','software-restarted-title':'介绍超时软件重启后的原标题',
  'observed-g10-n06-title-004-000':'标题main4/sub0：完整计数0B58已到',
  'observed-g10-n06-title-004-001':'标题main4/sub1：原软件reset入口',
  'software-restart-boot-frame-3073':'原global0：软件重启实际帧3073'}
 return names.get(name,name)
def native_data():
 e=read(RUN/'evidence.json');assert e['schema']=='phase14-native-boot-cooperation-flows-v1'and e['status']=='passed';qa=Counter();groups=[]
 for pin in e['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
 for case in e['native_cases']:
  folder=RUN/case['case'];v=read(RUN/case['validation']);rep=read(RUN/case['repeat_validation']);second=ROOT/rep['second_run']
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal'];assert v['cold_boot']and not v['state_imported']and not v['battery_file_imported']and v['fresh_process_per_run']
  assert not v['additional_core_memory_writes']and not v['additional_ready_or_result_injections']and not v['source_pipeline_installed']and not v['native_internal_CPU_trace']and v['source_CPU_comparisons_in_this_receipt']==0
  assert sha(ROOT/'scripts/capture_boot_cooperation_flows.py')==v['script_sha256']
  for name,pin in v['artifact_sha256'].items():
   a,b=folder/name,second/name;assert a.stat().st_size==b.stat().st_size==pin['bytes']>0 and sha(a)==sha(b)==pin['sha256'];qa['nonempty_double_run_artifacts']+=1
  for name in rep['formal_JSON_exact_parity']:assert(folder/name).read_bytes()==(second/name).read_bytes();qa['formal_JSON_exact_parity']+=1
  for name in v['excluded_empty_VRAM']:assert(folder/name).stat().st_size==0;qa['excluded_empty_VRAM']+=1
  qa['excluded_snapshot_metadata_JSON']+=len(v['excluded_snapshot_metadata_JSON'])
  rows=read(RUN/case['frame_services']);points=read(RUN/case['checkpoints']);plan=read(RUN/case['input_plan']);events=read(RUN/case['flow_events'])
  assert len(rows)==v['frames']and len(points)==v['checkpoint_count']and [r['frame']for r in rows]==list(range(1,len(rows)+1))
  pos=0
  for p in plan:assert p['start_frame']==pos;pos+=p['frames']
  assert pos==len(rows)
  wav=RUN/case['full_WAV'];audio=v['full_audio']
  with wave.open(str(wav),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,audio['stereo_sample_frames']);pcm=w.readframes(w.getnframes())
  assert len(pcm)==audio['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==audio['PCM_sha256']and sha(wav)==audio['WAV_sha256']and any(pcm);qa['WAV_header_PCM_hash']+=1
  cursor=0;timeline=[];previous=None
  for r in rows:
   count=r['PCM_stereo_sample_frames'];part=pcm[cursor:cursor+count*4];cursor+=count*4
   assert hashlib.sha256(part).hexdigest()==r['PCM_sha256']and bool(any(part))==r['PCM_nonzero']and cursor==r['PCM_stop_byte'];qa['frame_PCM_segments']+=1
   signature=tuple(str(r[k])for k in('global_state','nmi_scene','active_controller','active_main','active_phase','calendar_month_zero_based_6F01','ruler_6F03','remaining_budget_raw_6F05','cooperation_status_6F8B','domestic_phase_6F5B','domestic_budget_6F5D'))
   if signature!=previous:timeline.append({k:r[k]for k in('frame',*FIELDS)});previous=signature
  assert cursor==len(pcm);cursor=0
  for call in read(folder/'audio-callbacks.json'):
   count=call['stereo_sample_frames'];part=pcm[cursor:cursor+count*4];cursor+=count*4
   assert hashlib.sha256(part).hexdigest()==call['pcm_sha256']and 0<=call['emulated_frame_start']<len(rows);qa['audio_callback_segments']+=1
  assert cursor==len(pcm);captures=[]
  for p in points:
   row=rows[p['frame']-1];png=folder/p['image'];ram=folder/p['RAM'];sram=folder/p['SRAM'];state=folder/p['state']
   with Image.open(png)as im:im.load();assert im.size==(256,240)and im.mode=='RGB'and hashlib.sha256(im.tobytes()).hexdigest()==row['RGB_sha256']
   assert ram.stat().st_size==2048 and sha(ram)==row['RAM_sha256'];assert sram.stat().st_size==8192 and sha(sram)==row['SRAM_sha256']and state.stat().st_size>0
   for k in FIELDS:
    if k!='PCM_stereo_sample_frames':assert p['fields'][k]==row[k]
   captures.append(dict(label=p['label'],display_label=label(p['label']),frame=p['frame'],reason=p['reason'],image=relative(png)+'?sha='+sha(png),PNG_sha256=sha(png),
    RAM=relative(ram),SRAM=relative(sram),state=relative(state),fields={k:row[k]for k in FIELDS},raw={k:row.get(k)for k in RAW_FIELDS}));qa['same_frame_PNG_RAM_SRAM_state']+=1
  if case['case']=='core-reset-battery-retention':
   reset=v['core_reset_events'][0];before=folder/'before-core-reset-sram.bin';immediate=folder/'immediate-reset-sram.bin';assert reset['SRAM_byteidentical']and not reset['SRAM_diff']
   assert sha(before)==sha(immediate)==rows[-1]['SRAM_sha256']==reset['before_SRAM_sha256']==reset['after_SRAM_sha256']
  elif case['case']=='title-intro-software-restart':
   assert v['software_restart_observed_frames']==[3073]and rows[3062]['title_intro_counter_0471_0470']==0x0B58 and rows[3072]['global_state']==0
  else:
   assert rows[-1]['calendar_and_turn_6F00_6F06']==[89,1,0,2,1,3,1]and rows[-1]['active_main']==0 and rows[-1]['active_phase']==1
  groups.append(dict(case=case['case'],title=case['title'],frames=v['frames'],checkpoint_count=v['checkpoint_count'],captures=captures,timeline=timeline,frame_views=[{k:r[k]for k in('frame',*FIELDS)}for r in rows],
   defaults=DEFAULTS[case['case']],events=events,plan=plan,termination=v['termination'],final_fields=v['final_fields'],reset_events=v['core_reset_events'],software_restart_frames=v['software_restart_observed_frames'],
   audio=dict(path=relative(wav)+'?sha='+sha(wav),download=relative(wav),seconds=audio['stereo_sample_frames']/48000,**audio),
   links=[link(folder/name,txt)for name,txt in [('validation.json','病例回执'),('repeat-validation.json','原buffer双跑hash'),('input-plan.json','原输入／复位计划'),('frame-services.json','每帧字段/hash'),('flow-events.json','实际请求／重启事件'),('audio-callbacks.json','原PCM callbacks')]]))
 summary=e['summary'];assert qa['nonempty_double_run_artifacts']==summary['nonempty_repeat_artifact_checks']and qa['formal_JSON_exact_parity']==summary['formal_JSON_repeat_checks']
 assert qa['same_frame_PNG_RAM_SRAM_state']==summary['checkpoint_count']and qa['excluded_empty_VRAM']==summary['excluded_empty_VRAM']and qa['excluded_snapshot_metadata_JSON']==summary['excluded_snapshot_metadata_JSON']
 return e,groups,dict(qa)
class Parsed(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if'id'in a:self.ids.append(a['id'])
  if tag=='a'and'href'in a:self.links.append(a['href'])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--integration-receipt',type=Path,default=OUT/'source-integration.json');p.add_argument('--require-final',action='store_true');a=p.parse_args();a.integration_receipt=a.integration_receipt.resolve()
 e,groups,qa=native_data();modules=[module_data(k)for k in MODULES];integration=integration_data(a.integration_receipt)
 if a.require_final:assert all(m['status']=='passed'for m in modules)and integration['status']=='passed','Final source and integration receipts required'
 css=re.search(r'<style>([\s\S]+?)</style>',(ROOT/'analysis/phase13/index.html').read_text()).group(1)
 data=dict(summary=e['summary'],core=e['core'],groups=groups,modules=modules,integration=integration,QA=qa)
 html=HTML.replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/'))
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html);parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids));links=list(parsed.links)
 for g in groups:
  links.extend(x['href']for x in g['links']);links.append(g['audio']['download'])
  for c in g['captures']:links.extend(c[k]for k in('image','RAM','SRAM','state'))
 for m in modules:links.extend(x['href']for x in m['links'])
 if integration['status']!='pending':links.append(integration['path'])
 links.extend(x['href']for x in integration.get('linked_receipts',[]))
 for href in links:
  clean=urlsplit(href).path
  if clean and not clean.startswith('#')and clean!='browser-static-validation.json':assert(OUT/clean).resolve().is_file(),href
 js=re.search(r'<script>([\s\S]+?)</script>',html).group(1)
 with tempfile.NamedTemporaryFile('w',suffix='.js')as f:f.write(js);f.flush();subprocess.run(['node','--check',f.name],check=True,capture_output=True)
 result=dict(schema='phase14-browser-static-v1',status='passed',HTML_sha256=sha(OUT/'index.html'),generator_sha256=sha(Path(__file__)),unique_DOM_ids=len(parsed.ids),local_links_checked=len(links),
  JS_syntax='passed',native_static_QA=qa,native_evidence_sha256=sha(RUN/'evidence.json'),native_files_modified=False,modules=[{k:m[k]for k in('key','status','CPU','complete','prefix','guards','verification_CPU_callbacks','production_CPU_callbacks')}for m in modules],
  integration=dict(status=integration['status'],path=integration['path'],current_pins_match=integration.get('current_pins_match')),field_frames=sum(len(g['frame_views'])for g in groups),final_required=a.require_final,
  browser_visual_acceptance='Root owns CUA interaction/PNG/audio acceptance; this receipt is static only')
 (OUT/'browser-static-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))

HTML=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>冷启动、复位与合作AI证据</title><style>STYLES</style></head><body><main>
<small>阶段十四 · 原冷启动／重启 · 独立合作AI源码</small><h1>冷启动与合作调度</h1>
<nav><a href="../index.html">总入口</a><a href="../phase13/index.html">城市与全局UI</a><a href="../../source/README.md">源码合同</a><a href="../../source/recovered/scene_coordinator.py">coordinator API</a><a href="#native">真实原画面／声音</a><a href="#source">四个源码域</a><a href="#integration">纯源码整合</a><a href="runtime/README.md">原回放说明</a></nav>
<p class="note">本页浏览保存证据，不运行游戏、CPU、IR或声音合成。真实原核心帧、源码CPU差分、严格前缀、守卫、验证端原helper调用分别列示。控制器／初始化源码不等于独立cycle NES模拟器。</p>
<div class="metrics" id="metrics"></div><p id="summary"></p>
<h2 id="native">1 · 三组真实冷启动与合作流程</h2><p><a href="runtime/evidence.json">原核心manifest</a> · <a href="runtime/validation.json">双跑总回执</a> · <a href="runtime/static-validation.json">原产物静态QA</a> · <a href="browser-static-validation.json">本页链接／JS／媒体QA</a></p>
<div class="controls"><label>原回放 <select id="case"></select></label><label>前检查点 <select id="left"></select></label><label>后检查点 <select id="right"></select></label></div>
<p id="case-scope"></p><div class="screens"><figure><img id="before" alt="原Nestopia前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="after" alt="原Nestopia后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="transition"></p>
<p class="note">三案都直接加载只读原ROM，不导入状态或battery文件，不新增core内存／ready／结果写入。复位只证明同一已加载实例的8KiB SRAM保留；不是断电battery文件重载。标题软件重启是原介绍超时0B58路径，非猜测的重启菜单。</p>
<h3>完整原核心声音</h3><audio id="audio" controls preload="metadata"></audio><p id="audio-info"></p><a id="audio-download">下载原48kHz stereo WAV</a><p class="small-note">原callback产生的16bit stereo PCM；不称恢复源码已经合成PCM。每个实际原frame的PCM完整hash可核。</p>
<h3>每帧真实字段比较</h3><div class="frame-controls"><label>前字段帧 <input id="frame-left" type="number" min="1" step="1"></label><label>后字段帧 <input id="frame-right" type="number" min="1" step="1"></label><button id="apply-frames" type="button">比较字段</button></div><p id="field-frame-note"></p>
<div class="scroll"><table><thead><tr><th>原字段</th><th>前字段帧</th><th>后字段帧</th></tr></thead><tbody id="fields"></tbody></table></div>
<details><summary>所选真实检查点完整声明字段／palette／队列／音频RAM／hash</summary><pre id="raw"></pre></details><details><summary>冷起点、原输入／复位操作与结束条件</summary><pre id="preparation"></pre></details><p id="native-links"></p>
<h3>活跃状态与真实预算／请求变化</h3><p id="timeline-info"></p><div class="timeline"><table><thead><tr><th>帧</th><th>global／NMI</th><th>活跃controller main／phase</th><th>年月（原值）</th><th>君主／行动预算</th><th>请求6F8B</th><th>内政phase／预算</th></tr></thead><tbody id="timeline"></tbody></table></div>
<p class="small-note">任意字段帧不会生成新PNG；inactive状态数组只是原残余字节，不计作场景执行。0471:0470仅在原title intro域为计时，其它场景复用这两个地址。请求FF不能单独证明整个campaign／PPU已完成。</p>
<details><summary>观察到的原预算、年月、合作请求与复位事件</summary><pre id="flow-events"></pre></details>
<h2 id="source">2 · 四个独立源码域与验证范围</h2><div class="modules" id="modules"></div><h3 id="module-title"></h3><p id="module-entry"></p><div class="metrics" id="module-metrics"></div><p id="module-scope"></p><p id="module-note"></p><p id="module-links"></p>
<div class="scroll"><table><thead><tr><th>模块</th><th>状态</th><th>原CPU例</th><th>完整返回／有界出口</th><th>严格prefix</th><th>guards</th><th>验证端CPUhelper</th><th>生产CPUfallback</th></tr></thead><tbody id="scope-table"></tbody></table></div>
<h3>所选模块的实际模式计数</h3><div class="scroll"><table><thead><tr><th>原回执模式</th><th>数量</th></tr></thead><tbody id="mode-table"></tbody></table></div>
<details><summary>所选精确比较范围／模式计数／当前pins</summary><pre id="receipt"></pre></details><details id="code-panel"><summary>完整可读源码（获取文本，不执行）</summary><pre id="code" class="module-code"></pre></details>
<h2 id="integration">3 · 实际caller与严格纯源码接入</h2><div class="metrics" id="integration-metrics"></div><p id="integration-note"></p><p id="integration-links"></p><details><summary>当前整合回执</summary><pre id="integration-receipt"></pre></details>
<p class="note">主循环E066边界、实际caller RTS和reset E066边界分开计数。两条同一主generator的继承等待序列通过真实NMI2写原ack后resume，固定比较1976B RAM（1972B＋实际4B suspended-main栈），公开旧audio inactive栈01EC差异：原56／source166；其它同步整合行含全部2048B。这些受控CPU硬件输入序列不是三案native输入或完整NES帧证明。</p>
<ol class="steps"><li><strong>冷启动与软件reset真正替换栈</strong><br>E000的完整合同到E066入口，不假RTS回到已退役的旧scene caller；缺真实PPU vblank输入保留等待。普通启动4017 bit1不匹配回返，与受控全echo诊断永久F41E分开。</li><li><strong>内政与战术各自合作一次</strong><br>global2调用pair10/11 A000；global4调用pair8/9 A000。请求、预算、等待与实际返回register／SP／PC保留；生产不安装原CPU或IRfallback。</li><li><strong>原核心证据与软件验证分开</strong><br>自然一月行动耗尽→电脑君主→二月玩家返回来自原核心普通按键；战术矩阵继承的旧phase7战场起点另见来源，不称此三案冷启动进战争。原帧没有提供内部指令trace。</li></ol>
<footer>源码原CPU例、完整出口、严格前缀、source guards、helper调用、原核心帧、RGB检查点与PCM样本对分别计数。</footer></main>
<script>const D=PAYLOAD,$=s=>document.querySelector(s),fmt=v=>v==null?'待回执':Number(v).toLocaleString(),pretty=v=>JSON.stringify(v,null,2),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const s=D.summary;$('#metrics').innerHTML=[['真实冷boot回放',s.native_case_count],['首跑原帧',s.frames_first_run],['双跑非空产物',s.nonempty_repeat_artifact_checks],['原PCM样本对',s.PCM_stereo_sample_frames_first_run]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${fmt(v)}</strong></div>`).join('');$('#summary').textContent=`双跑${fmt(s.frames_both_runs)}帧、${fmt(s.checkpoint_count)}个真实检查点；${fmt(s.nonempty_repeat_artifact_checks)}份原buffer／PNG／RAM／SRAM／WAV产物已包含${fmt(s.formal_JSON_repeat_checks)}份正式JSON exact parity。${s.excluded_empty_VRAM}个0B VRAM和${s.excluded_snapshot_metadata_JSON}份路径metadata排除。每跑独立新进程，state未截断或规范化；新增core写入=${s.additional_core_memory_writes}。`;
$('#case').innerHTML=D.groups.map((g,i)=>`<option value="${i}">${esc(g.title)}</option>`).join('');let moduleKey='boot',codeSerial=0;
function group(){return D.groups[Number($('#case').value)];}function state(p){return p.active_controller?`${p.active_controller} ${p.active_main}/${p.active_phase}`:'本帧无已标识活跃controller';}
function choose(){const g=group(),opts=g.captures.map((p,i)=>`<option value="${i}">frame${p.frame} · ${esc(p.display_label)}</option>`).join('');$('#left').innerHTML=$('#right').innerHTML=opts;$('#left').value=String(Math.max(0,g.captures.findIndex(p=>p.label===g.defaults[0])));$('#right').value=String(Math.max(0,g.captures.findIndex(p=>p.label===g.defaults[1])));$('#frame-left').max=$('#frame-right').max=g.frames;
$('#case-scope').textContent=`真实只读ROM冷起点 · 无state／battery文件导入 · ${fmt(g.frames)}原帧。${g.termination}`;const audio=$('#audio');audio.pause();audio.src=g.audio.path;audio.load();$('#audio-download').href=g.audio.download;$('#audio-info').textContent=`${fmt(g.audio.stereo_sample_frames)} stereo样本对 · ${g.audio.seconds.toFixed(3)}秒 · WAV SHA ${g.audio.WAV_sha256.slice(0,20)}…`;
$('#preparation').textContent=pretty({cold_boot:true,state_imported:false,battery_file_imported:false,additional_core_memory_writes:0,input_plan:g.plan,termination:g.termination,reset_events:g.reset_events,software_restart_frames:g.software_restart_frames,final_fields:g.final_fields});$('#flow-events').textContent=pretty(g.events);$('#timeline-info').textContent=`${fmt(g.frames)}个原帧，活跃状态／预算／内政请求变化${g.timeline.length}条；全部每帧字段另有JSON。`;
$('#timeline').innerHTML=g.timeline.map(p=>`<tr><td>${p.frame}</td><td>${p.global_state}/${p.nmi_scene}</td><td>${esc(state(p))}</td><td>${p.calendar_year_6F00}/${p.calendar_month_zero_based_6F01}</td><td>${p.ruler_6F03}/${p.remaining_budget_raw_6F05}</td><td>${p.cooperation_status_6F8B}</td><td>${p.domestic_phase_6F5B}/${p.domestic_budget_6F5D}</td></tr>`).join('');detail();}
function detail(){const g=group(),l=g.captures[Number($('#left').value)],r=g.captures[Number($('#right').value)];for(const[id,p]of[['before',l],['after',r]]){$('#'+id).src=p.image;$('#'+id+'-caption').textContent=`${p.display_label} · 原frame${p.frame} · ${state(p.fields)} · PNG ${p.PNG_sha256.slice(0,16)}…`;}
$('#transition').textContent=`检查点 ${l.display_label} → ${r.display_label}：global／NMI ${l.fields.global_state}/${l.fields.nmi_scene} → ${r.fields.global_state}/${r.fields.nmi_scene}；${state(l.fields)} → ${state(r.fields)}。`;$('#frame-left').value=l.frame;$('#frame-right').value=r.frame;fields();$('#raw').textContent=pretty({before:l,after:r});$('#native-links').innerHTML=[...g.links,{href:l.RAM,label:'前RAM'},{href:r.RAM,label:'后RAM'},{href:l.SRAM,label:'前SRAM'},{href:r.SRAM,label:'后SRAM'},{href:l.state,label:'原完整前state'},{href:r.state,label:'原完整后state'}].map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');}
function fields(){const g=group(),a=Number($('#frame-left').value),b=Number($('#frame-right').value);if(!Number.isInteger(a)||!Number.isInteger(b)||a<1||b<1||a>g.frames||b>g.frames){$('#field-frame-note').textContent=`字段帧必须在1..${g.frames}范围内`;return;}const l=g.frame_views[a-1],r=g.frame_views[b-1],lc=g.captures[Number($('#left').value)],rc=g.captures[Number($('#right').value)];$('#field-frame-note').textContent=`字段frame${a}／${b}；上方PNG仍为实际检查点frame${lc.frame}／${rc.frame}，没有给任意字段帧生成截图。`;
const names={global_state:'global007A',nmi_scene:'NMI0078',active_controller:'本帧真正活跃controller',active_main:'活跃主态',active_phase:'活跃phase',calendar_year_6F00:'原年值6F00（89在原图显示189年）',calendar_month_zero_based_6F01:'原0-based月6F01',ruler_6F03:'当前君主6F03',turn_slot_6F04:'轮转slot6F04',remaining_budget_raw_6F05:'玩家／君主行动预算6F05',event_flag_6F06:'原标志6F06（不猜角色）',cooperation_status_6F8B:'原合作请求6F8B（0/FF等）',domestic_phase_6F5B:'内政phase6F5B',domestic_budget_6F5D:'内政raw预算6F5D（原借位值保留）',domestic_city_6F5E:'内政城市6F5E',menu_cursor_0012:'原菜单cursor0012',buttons_0081_0086:'原输入0081..86',PPU_jobs_007E:'原PPU请求007E',NMI_busy_007B:'原NMI busy007B',text_progress_0300:'文字进度0300',text_cursor_0304:'文字游标0304',title_intro_counter_0471_0470:'原0471:0470合字（仅标题intro时为计时）',city11_gold:'城市11原金word',city11_reserve_raw16:'城市11预备兵raw16',recruitment_quantity_raw_048E_048F:'原征兵quantity raw单位（此次1=100兵）',observer_officer_records:'ID5/30/131原12B记录及字段',PCM_stereo_sample_frames:'该实际帧PCM样本对'};$('#fields').innerHTML=Object.entries(names).map(([k,n])=>`<tr><th>${esc(n)}</th><td>${esc(typeof l[k]==='object'?pretty(l[k]):l[k])}</td><td>${esc(typeof r[k]==='object'?pretty(r[k]):r[k])}</td></tr>`).join('');}
$('#case').addEventListener('change',choose);$('#left').addEventListener('change',detail);$('#right').addEventListener('change',detail);$('#apply-frames').addEventListener('click',fields);$('#frame-left').addEventListener('change',fields);$('#frame-right').addEventListener('change',fields);choose();
$('#modules').innerHTML=D.modules.map(m=>`<button type="button" data-module="${m.key}" aria-pressed="false">${esc(m.title)}</button>`).join('');$('#scope-table').innerHTML=D.modules.map(m=>`<tr><th>${esc(m.title)}</th><td>${esc(m.status)}</td><td>${fmt(m.CPU)}</td><td>${fmt(m.complete)}</td><td>${fmt(m.prefix)}</td><td>${fmt(m.guards)}</td><td>${fmt(m.verification_CPU_callbacks)}</td><td>${fmt(m.production_CPU_callbacks)}</td></tr>`).join('');
function module(key){moduleKey=key;codeSerial++;const m=D.modules.find(p=>p.key===key);document.querySelectorAll('[data-module]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.module===key)));$('#module-title').textContent=m.title;$('#module-entry').textContent=m.entries;$('#module-metrics').innerHTML=[['当前状态',m.status],['原CPU例',m.CPU],['完整返回／出口',m.complete],['严格prefix',m.prefix],['source guards',m.guards],['验证端CPUhelper',m.verification_CPU_callbacks]].map(([k,v])=>`<div class="metric"><small>${esc(k)}</small><strong>${typeof v==='number'?fmt(v):esc(v??'待回执')}</strong></div>`).join('');$('#module-scope').textContent=`精确比较合同：${pretty(m.comparison)}；生产原CPUfallback=${fmt(m.production_CPU_callbacks)}。`;$('#module-note').textContent=m.notes.join('；');$('#module-links').innerHTML=m.links.map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');$('#receipt').textContent=pretty(m.receipt);$('#mode-table').innerHTML=Object.entries({...m.counts,...m.completion_kinds}).map(([k,v])=>`<tr><th>${esc(k)}</th><td>${fmt(v)}</td></tr>`).join('');$('#code').textContent=m.source_href?'展开读取完整原Python文本，浏览器不执行。':'源码路径待回执';if($('#code-panel').open)loadCode();}
async function loadCode(){const m=D.modules.find(p=>p.key===moduleKey),token=++codeSerial;if(!m.source_href){$('#code').textContent='源码未确认，保持pending。';return;}try{const res=await fetch(m.source_href);if(!res.ok)throw new Error(String(res.status));const text=await res.text();if(token===codeSerial)$('#code').textContent=text;}catch(err){if(token===codeSerial)$('#code').textContent='读取未完成：'+err.message;}}
document.querySelectorAll('[data-module]').forEach(b=>b.addEventListener('click',()=>module(b.dataset.module)));$('#code-panel').addEventListener('toggle',()=>{if($('#code-panel').open)loadCode();});module('boot');const c=D.integration;$('#integration-metrics').innerHTML=[['整合状态',c.status],['原CPU例',c.rom_cpu_case_count??c.actual_ROM_CPU_comparison_count],['实际caller RTS',c.actual_caller_return_count],['main E066边界',c.main_boundary_count??c.complete_main_boundary_count],['reset E066边界',c.reset_boundary_count],['严格prefix',c.strict_prefix_count??c.original_prefix_case_count],['source guards',c.source_guard_case_count??c.source_guard_count]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${typeof v==='number'?fmt(v):esc(v??'待回执')}</strong></div>`).join('');$('#integration-note').textContent=`当前纯整合=${c.status}，currentpins=${c.current_pins_match??'待回执'}。${c.note??'实际caller register／SP／PC、pending硬件输入与已退役reset caller分别核对；原帧与sourceCPU例不混计。'}`;$('#integration-links').innerHTML=c.status==='pending'?'最终回执尚未落盘':[{href:c.path,label:'最终纯源码整合回执'},...(c.linked_receipts??[])].map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');$('#integration-receipt').textContent=pretty(c);
</script></body></html>'''
if __name__=='__main__':main()
