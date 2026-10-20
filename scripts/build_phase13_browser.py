#!/usr/bin/env python3
"""Read current phase13 receipts and frozen native RGB/PCM evidence only.

No model, CPU, IR, core or synthesis runs here. Missing receipts remain pending;
native files, production source and earlier portals are never modified.
"""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit
import argparse,hashlib,json,re,subprocess,tempfile,wave,sys
sys.dont_write_bytecode=True
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase13';RUN=OUT/'runtime'
MODULES={
 'city':('城市主控制器','city_ui_controller.py','physical27/28 A000 · 菜单、选择、取消与城市主/子分派'),
 'panels':('城市资料与年月服务','city_panel_services.py','physical25/26 · 城市资料、名册与表头服务'),
 'global-ui':('全局／城市显示workers','global_ui_controller.py','physical29/30 workers · 标题、新君主与全局UI控制'),
 'graphics':('地图资源与单位字形','ui_graphics_initialization.py','physical23 A012/A015/A018 · 指针、数据窗及四tile'),
 'scenario':('新剧本持久记录初始化','scenario_initialization.py','physical29 A018 → physical30 DD8B · 明确SRAM替换'),
 'city-details':('城市武将资料控制器','city_officer_details_controller.py','physical25 A021 → AFE5 · 五phase、真实资料/肖像服务'),
 'title-intro':('标题开场图形服务','title_intro_graphics.py','physical23 A021 → physical24 DE25 · 五phase/timer/OAM/audio'),
 'action-bridges':('城市动作源码桥接','city_action_bridges.py','8A01E装备/价格准备 · 10A006忠诚调整 · 非购买／即时转属'),
 'arithmetic':('UI共享算术服务','ui_arithmetic_services.py','独立整数乘法／原caller协议；算术CPU对照单列'),
 'menu-navigation':('城市菜单导航协议','city_menu_navigation.py','独立固定menu入口 · 保留真实尾调用／caller栈')}
FIELDS=('global_state','nmi_scene','city_main','city_phase','menu_cursor_0012','menu_cursor_0013','controller_buttons_0081',
 'UI_index_040C','UI_row_040D','UI_ids_0410_0417','UI_candidate_at_index','UI_candidate_record','city_control_0470_047F',
 'portrait_CHR_B8_B9','OAM_byte_count_007C','PPU_jobs_007E','NMI_busy_007B','text_progress_0300','text_cursor_0304',
 'RNG_cursor_0050','calendar_and_request_6F00_6F06','PCM_stereo_sample_frames')
RAW_FIELDS=('scratch_0000_001F','packet_0380_03BF','queue_0310_037F','palette_0100_013F','audio_RAM_0700_07FF','OAM_0200_02FF',
 'CHR_cache_00B0_00DD','IRQ_fields_0068_0075','camera_008E_00A9','main_mapper_cache_DE_DF_E0','NMI_mapper_cache_E1_E2_E3',
 'RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256')
MAIN_NAMES={0:'世界／城市光标',1:'城市图标',2:'内政',3:'军事',4:'资源转交／给予',5:'城镇／武器店',12:'武将资料'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def relative(p):return str(p.relative_to(OUT))if p.is_relative_to(OUT)else'../../'+str(p.relative_to(ROOT))
def link(p,label):return dict(href=relative(p),label=label)
def address_ranges(addresses):
 values=sorted(set(addresses));parts=[]
 if not values:return'回执未列地址'
 start=last=values[0]
 for value in values[1:]:
  if value!=last+1:parts.append(f'{start:04X}..{last:04X}');start=value
  last=value
 parts.append(f'{start:04X}..{last:04X}');return' + '.join(parts)
def native_data():
 e=read(RUN/'evidence.json');assert e['schema']=='phase13-native-city-flows-v1'and e['status']=='passed';checks=Counter();groups=[]
 assert len(e['native_cases'])==e['summary']['native_case_count'];assert sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')==e['core']['core_sha256']
 for pin in e['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
 for case in e['native_cases']:
  v=read(RUN/case['validation']);rep=read(RUN/case['repeat_validation']);path=RUN/case['case'];second=ROOT/rep['second_run']
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal'];assert v['additional_core_memory_writes']==v['additional_ready_or_result_injections']==0
  assert v['native_internal_CPU_trace']is False and v['source_CPU_comparisons_in_this_receipt']==0 and v['source_pipeline_installed']is False
  assert v['natural_inherited_start']and v['final_SRAM_equals_initial']and not v['SRAM_changed_addresses']
  for field in('initial_state','provenance'):assert sha(ROOT/v[field])==v[field+'_sha256']
  assert sha(ROOT/'scripts/capture_city_ui_flows.py')==v['script_sha256']
  for name,pin in v['artifact_sha256'].items():
   first=path/name;other=second/name;assert first.stat().st_size==other.stat().st_size==pin['bytes']>0 and sha(first)==sha(other)==pin['sha256'];checks['nonempty_double_run_artifacts']+=1
  for name in rep['formal_JSON_exact_parity']:assert(path/name).read_bytes()==(second/name).read_bytes();checks['formal_JSON_exact_parity']+=1
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
   assert(row['global_state'],row['nmi_scene'])==(2,2)
   ids=row['UI_ids_0410_0417'];index=row['UI_index_040C'];expected=ids[index]if index<len(ids)else None
   assert row['UI_candidate_at_index']==expected,(case['case'],row['frame'],index,expected)
   signature=tuple(str(row[k])for k in('city_main','city_phase','menu_cursor_0012','UI_index_040C','UI_row_040D','PPU_jobs_007E','text_progress_0300','text_cursor_0304'))
   if signature!=previous:timeline.append({k:row.get(k)for k in('frame',*FIELDS)});previous=signature
  assert cursor==len(pcm);cursor=0
  for call in calls:
   count=call['stereo_sample_frames'];part=pcm[cursor:cursor+4*count];cursor+=4*count
   assert hashlib.sha256(part).hexdigest()==call['pcm_sha256']and 0<=call['emulated_frame_start']<len(rows);checks['audio_callback_segments']+=1
  assert cursor==len(pcm);captures=[]
  for point in points:
   row=rows[point['frame']-1];png=path/point['image'];ram=path/point['RAM'];sram=path/point['SRAM'];state=path/point['state']
   with Image.open(png)as image:assert image.size==(256,240)and hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   assert ram.stat().st_size==2048 and sha(ram)==row['RAM_sha256'];assert sram.stat().st_size==8192 and sha(sram)==row['SRAM_sha256'];assert state.stat().st_size>0
   raw=ram.read_bytes();assert raw[0x40C]==row['UI_index_040C']and raw[0x40D]==row['UI_row_040D']and list(raw[0x410:0x418])==row['UI_ids_0410_0417']
   record=row.get('UI_candidate_record')
   if record:offset=0x3C0+12*record['ID'];assert sram.read_bytes()[offset:offset+12].hex()==record['raw']
   fields={k:row.get(k)for k in FIELDS};fields['portrait_list_index_0408']=raw[0x408];fields['UI_ids_0410_0419']=list(raw[0x410:0x41A])
   checks['PNG_native_RGB_RAM_SRAM_state_checkpoints']+=1
   captures.append(dict(label=point['label'],display_label=point['label'],frame=point['frame'],reason=point['reason'],image=relative(png)+'?sha='+sha(png),PNG_sha256=sha(png),RAM=relative(ram),SRAM=relative(sram),state=relative(state),fields=fields,raw={k:row.get(k)for k in RAW_FIELDS}))
  final=rows[-1];assert(final['global_state'],final['nmi_scene'],final['city_main'],final['city_phase'])==(2,2,0,1)
  groups.append(dict(case=case['case'],title=case['title'],frames=v['frames'],checkpoint_count=v['checkpoint_count'],captures=captures,timeline=timeline,
   frame_views=[{k:row.get(k)for k in('frame',*FIELDS)}for row in rows],observed_states=v['observed_states'],
   plan=plan,initial_state=v['initial_state'],provenance=v['provenance'],natural_inherited_start=v['natural_inherited_start'],termination=v['termination'],final_fields=v['final_fields'],
   audio=dict(path=relative(wav)+'?sha='+sha(wav),download=relative(wav),seconds=audio['stereo_sample_frames']/48000,**audio),
   links=[link(path/name,label)for name,label in [('validation.json','首跑回执'),('repeat-validation.json','双跑逐项hash'),('input-plan.json','实际原按键'),('frame-services.json','全部每帧字段/hash'),('audio-callbacks.json','原PCM callbacks')]]))
 summary=e['summary'];assert checks['nonempty_double_run_artifacts']==summary['nonempty_repeat_artifact_checks'];assert checks['formal_JSON_exact_parity']==summary['formal_JSON_repeat_checks'];assert checks['PNG_native_RGB_RAM_SRAM_state_checkpoints']==summary['checkpoint_count']
 assert checks['excluded_empty_VRAM']==summary['excluded_empty_VRAM']and checks['excluded_snapshot_metadata_JSON']==summary['excluded_snapshot_metadata_JSON'];return e,groups,dict(checks)
def collect_pins(receipt,source):
 pins=[];value=receipt.get('source_sha256')
 if isinstance(value,str):pins.append(dict(path=str(source.relative_to(ROOT)),sha256=value))
 elif isinstance(value,dict):pins.extend(dict(path=p,sha256=h)for p,h in value.items())
 for key in('source_pins','dependency_pins','source_and_validator_pins'):
  values=receipt.get(key,[])
  if isinstance(values,list):pins.extend(values)
 for key in('pins','dependencies'):
  values=receipt.get(key,{})
  if isinstance(values,dict):pins.extend(dict(path=p,sha256=h)for p,h in values.items())
 if receipt.get('validator_sha256')and receipt.get('validator_path'):pins.append(dict(path=receipt['validator_path'],sha256=receipt['validator_sha256']))
 dedup={p['path']:p['sha256']for p in pins if 'path'in p and 'sha256'in p}
 return[dict(path=p,expected_sha256=h,actual_sha256=sha(ROOT/p)if(ROOT/p).is_file()else None)for p,h in dedup.items()]
def without_heavy(value):return{k:v for k,v in value.items()if k not in('samples','rows','failures','declared_RAM_addresses','declared_minimum_RAM_addresses','actual_call_fixtures','original_cases','actual_farcallee_boundaries')}
def module_data(key,bridges_path):
 title,filename,entries=MODULES[key];folder=OUT/key;source=ROOT/'source/recovered'/filename
 receipt_path=bridges_path if key=='action-bridges'else folder/'validation.json';r=read(receipt_path)if receipt_path.is_file()else{};pins=collect_pins(r,source);notes=[];status=r.get('status','pending')
 if r.get('quick'):status='quick';notes.append('当前quick矩阵尚未冻结')
 stale=[p['path']for p in pins if p['actual_sha256']!=p['expected_sha256']]
 if stale:status='source_changed';notes.append('当前文件与回执pin不同：'+','.join(stale))
 if not r:notes.append('最终桥接／验证回执尚未落盘；不以动态调查代替纯源码整合')
 complete=r.get('original_complete_case_count',r.get('complete_return_count'));prefix=r.get('original_prefix_case_count',r.get('strict_prefix_count'));cpu=r.get('rom_cpu_case_count',r.get('actual_ROM_CPU_comparison_count'))
 if cpu is not None and complete is not None and prefix is not None:assert cpu==complete+prefix
 comp=r.get('comparison',{});addresses=comp.get('RAM_addresses',r.get('declared_RAM_addresses',r.get('declared_minimum_RAM_addresses',[])));ram=comp.get('RAM_bytes',r.get('compared_RAM_bytes',r.get('all_RAM_compared_bytes',len(addresses)or None)))
 scope=address_ranges(addresses or(range(2048)if ram==2048 else[]));stack=comp.get('free_CPU_stack_residue',comp.get('free_stack_residue','按模式见回执'))
 if key=='global-ui'and r:
  scope='banked/fixed CPU模式2048；纯组合至少'+scope+'+实际active stack'
  notes.append('global main的complete仅到下一E066且caller SP不变；banked worker的真实RTS另按入口核对，均不是完整NES帧')
 if comp.get('additional_active_caller_stack'):scope+='；另'+comp['additional_active_caller_stack']
 callback_count=r.get('verification_only_original_CPU_callback_count',0 if r else None)
 production_callbacks=r.get('production_source_original_CPU_callbacks',r.get('production_original_CPU_callbacks',r.get('source_original_CPU_callbacks')))
 if callback_count:notes.append('验证端借用原CPU callee的调用数单列；该数不是完整源码病例数，生产不安装这些callbacks')
 catalog=folder/'source-catalog.json';static=read(catalog)if catalog.is_file()else{}
 static_note=None
 if static:static_note='静态具名procedures / if / loop见source-catalog；这些数量不是原CPU病例'
 receipt=without_heavy(r);receipt['current_pin_checks']=pins
 files=[(source,'完整具名源码'),(folder/'README.md','作用域与API'),(folder/'evidence.json','原bytes/表/来源'),(receipt_path,'当前原CPU/guards回执'),(folder/'original-ranges.asm','原范围汇编'),(folder/'source-catalog.json','静态源码目录')]
 if key=='action-bridges':files.extend([(OUT/'dependencies/inventory.json','单列：原CPU依赖调查'),(ROOT/'source/recovered/scene_coordinator.py','coordinator API')])
 return dict(key=key,title=title,entries=entries,status=status,notes=notes,CPU=cpu,complete=complete,prefix=prefix,RAM_bytes=ram,RAM_scope=scope,free_stack_residue=stack,
  SRAM_bytes=comp.get('SRAM_bytes',r.get('compared_SRAM_bytes',r.get('all_SRAM_compared_bytes'))),guard_count=r.get('source_guard_case_count',r.get('source_guard_count')),
  verification_CPU_callbacks=callback_count,production_CPU_callbacks=production_callbacks,static_note=static_note,receipt=receipt,source_href=relative(source)if source.is_file()else None,
  receipt_href=relative(receipt_path)if receipt_path.is_file()else None,links=[link(p,label)for p,label in files if p.is_file()])
def integration_data(path):
 if not path.is_file():return dict(status='pending',note='纯源码整合回执尚未落盘；不采用inventory调查数',path=relative(path))
 r=read(path);pins=collect_pins(r,ROOT/'source/recovered/scene_coordinator.py');result=without_heavy(r);result['current_pin_checks']=pins;result['current_pins_match']=all(p['expected_sha256']==p['actual_sha256']for p in pins);result['path']=relative(path)
 if not result['current_pins_match']:result['status']='source_changed'
 return result
class Parsed(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if'id'in values:self.ids.append(values['id'])
  if tag=='a'and'href'in values:self.links.append(values['href'])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bridges-receipt',type=Path,default=OUT/'action-bridges/validation.json');p.add_argument('--integration-receipt',type=Path,default=OUT/'source-integration.json');p.add_argument('--require-final',action='store_true');a=p.parse_args()
 a.bridges_receipt=a.bridges_receipt.resolve();a.integration_receipt=a.integration_receipt.resolve()
 e,groups,qa=native_data();modules=[module_data(k,a.bridges_receipt)for k in MODULES];integration=integration_data(a.integration_receipt);inventory=read(OUT/'dependencies/inventory.json')
 if a.require_final:assert all(m['status']=='passed'for m in modules)and integration['status']=='passed','Current source/integration receipts are not all frozen passed'
 details=read(ROOT/'analysis/phase12/details/evidence.json')['row_field_mapping'];css=re.search(r'<style>([\s\S]+?)</style>',(ROOT/'analysis/phase12/index.html').read_text()).group(1)
 data=dict(summary=e['summary'],core=e['core'],groups=groups,modules=modules,detail_rows=details,integration=integration,discovery=without_heavy(inventory),main_names=MAIN_NAMES,QA=qa)
 html=HTML.replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/'))
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html)
 parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids));links=list(parsed.links)
 for group in groups:
  links.extend(x['href']for x in group['links']);links.append(group['audio']['download'])
  for point in group['captures']:links.extend(point[k]for k in('image','RAM','SRAM','state'))
 for module in modules:links.extend(x['href']for x in module['links'])
 for path in links:
  clean=urlsplit(path).path
  if clean and not clean.startswith('#')and clean!='browser-static-validation.json':assert(OUT/clean).resolve().is_file(),path
 js=re.search(r'<script>([\s\S]+?)</script>',html).group(1)
 with tempfile.NamedTemporaryFile('w',suffix='.js')as f:f.write(js);f.flush();subprocess.run(['node','--check',f.name],check=True,capture_output=True)
 receipt=dict(schema='phase13-browser-static-v1',status='passed',HTML_sha256=sha(OUT/'index.html'),generator_sha256=sha(Path(__file__)),unique_DOM_ids=len(parsed.ids),local_links_checked=len(links),JS_syntax='passed',native_static_QA=qa,native_evidence_sha256=sha(RUN/'evidence.json'),native_files_modified=False,
  modules=[{k:m[k]for k in('key','status','CPU','complete','prefix','RAM_bytes','guard_count','verification_CPU_callbacks','production_CPU_callbacks')}for m in modules],integration=dict(status=integration['status'],path=integration['path'],current_pins_match=integration.get('current_pins_match')),
  field_frames=sum(len(g['frame_views'])for g in groups),detail_rows=len(details),final_required=a.require_final,browser_visual_acceptance='Root owns CUA interaction/PNG/audio QA; this receipt is static only')
 (OUT/'browser-static-validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False))

HTML=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>城市与全局界面源码证据</title><style>STYLES</style></head><body><main>
<small>阶段十三 · 城市／全局UI · 独立源码与原核心回放</small><h1>城市与全局界面</h1>
<nav><a href="../index.html">总入口</a><a href="../phase12/index.html">阶段12资料服务</a><a href="../../source/README.md">源码合同</a><a href="../../source/recovered/scene_coordinator.py">coordinator API</a><a href="#native">原画面／声音</a><a href="#source">十个模块域</a><a href="#integration">源码整合</a><a href="runtime/README.md">原回放说明</a></nav>
<p class="note">本页只浏览保存的证据，不运行游戏、CPU、IR或声音合成。原CPU条件矩阵、验证端借用callee、纯源码整合与原Nestopia的RGB／PCM分别列示。静态源码位置／函数数不当作CPU病例。</p>
<div class="metrics" id="metrics"></div><p id="summary"></p>
<h2 id="native">1 · 原菜单与资料浏览周期</h2><p><a href="runtime/evidence.json">native evidence</a> · <a href="runtime/validation.json">原双跑总回执</a> · <a href="browser-static-validation.json">本页静态PNG／WAV／链接QA</a></p>
<div class="controls"><label>原回放 <select id="case"></select></label><label>前检查点 <select id="left"></select></label><label>后检查点 <select id="right"></select></label></div>
<p id="case-scope"></p><div class="screens"><figure><img id="before" alt="原Nestopia前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="after" alt="原Nestopia后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="transition"></p>
<p class="note">main4为资源转交／给予（resource_transfer/give），main5为城镇／武器店（town_shop/weapon）。两案终点global2／NMI2／city0/1，仅返回世界／城市光标，没有执行回合结束。资料040D的FF不能单独证明画面完成。</p>
<h3>完整原核心声音</h3><audio id="audio" controls preload="metadata"></audio><p id="audio-info"></p><a id="audio-download">下载原48kHz stereo WAV</a><p class="small-note">原audio callback的16bit stereo PCM。软件音序／端口请求与核心波形输出分别验证。</p>
<h3>每帧UI字段比较</h3><div class="frame-controls"><label>前字段帧 <select id="frame-left"></select></label><label>后字段帧 <select id="frame-right"></select></label></div><p id="field-frame-note"></p>
<div class="scroll"><table><thead><tr><th>原字段</th><th>前字段帧</th><th>后字段帧</th></tr></thead><tbody id="fields"></tbody></table></div>
<h3>实际检查点的完整十槽名单</h3><p>每帧回执保存0410..0417八项；下表另外直接读检查点RAM的0410..0419全部十槽与0408。indexedOfficerID取0410[040C]，不把0410首项当成当前武将。切页期间040C已指新卡时，肖像0408可仍指旧项。</p>
<div class="scroll"><table><thead><tr><th>检查点RAM字段</th><th>前PNG帧</th><th>后PNG帧</th></tr></thead><tbody id="rosters"></tbody></table></div>
<details><summary>所选检查点packet／scratch／palette／OAM和哈希</summary><pre id="raw"></pre></details><details><summary>原起点、按键计划与结束条件</summary><pre id="preparation"></pre></details><p id="native-links"></p>
<h3>原活跃城市状态与队列变化</h3><p id="timeline-info"></p><div class="timeline"><table><thead><tr><th>帧</th><th>global/NMI</th><th>city main/phase</th><th>040C → indexed ID</th><th>040D</th><th>007E</th><th>0300/0304</th></tr></thead><tbody id="timeline"></tbody></table></div>
<p class="small-note">逐帧数据不是Nestopia内部CPU trace；上方PNG是47个保存检查点，任意字段帧不会生成新的截图。</p>
<h2 id="details">2 · 原资料十行的字段来源</h2><p><a href="../phase12/details/evidence.json">十行原bytes／字段</a> · <a href="city-details/README.md">五阶段资料控制器</a></p><div class="scroll"><table><thead><tr><th>row</th><th>原入口</th><th>作用／字段</th><th>recordbyte</th></tr></thead><tbody id="row-fields"></tbody></table></div>
<h2 id="source">3 · 十个模块域与各自比较范围</h2><div class="modules" id="modules"></div><h3 id="module-title"></h3><p id="module-entry"></p><div class="metrics" id="module-metrics"></div><p id="module-scope"></p><p id="module-note"></p><p id="module-links"></p>
<div class="scroll"><table><thead><tr><th>模块</th><th>状态</th><th>原CPU例</th><th>完整返回</th><th>严格prefix</th><th>RAM</th><th>guards</th><th>验证端CPUcallee调用</th><th>生产CPUfallback</th></tr></thead><tbody id="scope-table"></tbody></table></div>
<details><summary>所选回执／范围／guards／当前pins</summary><pre id="receipt"></pre></details><details id="code-panel"><summary>所选完整源码文本（读取但不执行）</summary><pre id="code" class="module-code"></pre></details>
<h2 id="integration">4 · 纯源码接入与原CPU依赖调查</h2><div class="metrics" id="integration-metrics"></div><p id="integration-note"></p><p id="integration-links"></p><details><summary>当前纯源码整合回执</summary><pre id="integration-receipt"></pre></details>
<p>依赖调查只定位原远端调用与真实callee输入，不是生产fallback或恢复源码等价证明。</p><p><a href="dependencies/inventory.json">原CPU依赖调查／caller输入</a> · <a href="dependencies/README.md">发现层合同</a></p><pre id="discovery"></pre>
<ol class="steps"><li><strong>真实跨银行入口</strong><br>23A012→A61C是地图资源，29A018→DD8B有意初始化SRAM，25A021→AFE5是城市资料，23A021→DE25是标题开场。相同数字地址不能跨physical bank混同。</li><li><strong>原状态和外部服务</strong><br>缺硬件输入／未知callee保留真实dependency；请求、队列消费与实际caller PC/SP分开。不伪ready／IRQ／RTS。</li><li><strong>明确比较范围</strong><br>地图资源、新剧本初始化和城市资料控制器含全部2048RAM；标题服务固定1972RAM加实际caller栈，保留音频既有inactive栈排除。城市、panels和globalUI的验证端CPUcallee与纯整合回执另列。</li><li><strong>原核心与独立软件层</strong><br>controller／UI初始化完整返回不等于独立cycle CPU、PPU扫描线、IRQ/NMI时间和APU/Namco163波形合成已完成。</li></ol>
<footer>CPU病例、完整返回、严格前缀、source guards、静态位置、原核心帧、检查点与PCM样本分别计数。</footer></main>
<script>const D=PAYLOAD,$=s=>document.querySelector(s),fmt=v=>v==null?'待回执':Number(v).toLocaleString(),pretty=v=>JSON.stringify(v,null,2),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const s=D.summary;$('#metrics').innerHTML=[['原核心回放',s.native_case_count],['首跑帧',s.frames_first_run],['双跑非空产物',s.nonempty_repeat_artifact_checks],['原PCM样本对',s.PCM_stereo_sample_frames_first_run]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${fmt(v)}</strong></div>`).join('');$('#summary').textContent=`双跑${fmt(s.frames_both_runs)}帧；${fmt(s.checkpoint_count)}个PNG/RAM/SRAM/state检查点；${fmt(s.nonempty_repeat_artifact_checks)}个非空产物已包含${fmt(s.formal_JSON_repeat_checks)}份逐字节相同的正式JSON。${s.excluded_empty_VRAM}个0B VRAM和${s.excluded_snapshot_metadata_JSON}份metadata排除；新增核心写入=${s.additional_core_memory_writes}，两案最终SRAM与起点相同。`;
$('#case').innerHTML=D.groups.map((g,i)=>`<option value="${i}">${esc(g.title)}</option>`).join('');let moduleKey='city-details',codeSerial=0;
function group(){return D.groups[Number($('#case').value)];}function state(p){return`${p.city_main}/${p.city_phase} ${D.main_names[p.city_main]??'原状态'}`;}
function choose(){const g=group(),opts=g.captures.map((p,i)=>`<option value="${i}">frame${p.frame} · ${esc(p.display_label)}</option>`).join('');$('#left').innerHTML=$('#right').innerHTML=opts;const labels=g.case==='world-officer-browse-cycle'?['officer-info-first','officer-info-next']:['domestic-menu','world-map-return'];$('#left').value=String(Math.max(0,g.captures.findIndex(p=>p.label===labels[0])));$('#right').value=String(Math.max(0,g.captures.findIndex(p=>p.label===labels[1])));
const frames=g.frame_views.map(p=>`<option value="${p.frame}">frame${p.frame} · city${p.city_main}/${p.city_phase} · 040C=${p.UI_index_040C} → ID${p.UI_candidate_at_index??'—'}</option>`).join('');$('#frame-left').innerHTML=$('#frame-right').innerHTML=frames;$('#case-scope').textContent=`继承冷启动原输入的自然城市起点 · ${fmt(g.frames)}帧 · 零新增核心写入。${g.termination}`;const audio=$('#audio');audio.pause();audio.src=g.audio.path;audio.load();$('#audio-download').href=g.audio.download;$('#audio-info').textContent=`${fmt(g.audio.stereo_sample_frames)} stereo样本对 · ${g.audio.seconds.toFixed(3)}秒 · WAV SHA ${g.audio.WAV_sha256.slice(0,20)}…`;
$('#preparation').textContent=pretty({initial_state:g.initial_state,provenance:g.provenance,natural_inherited_start:g.natural_inherited_start,additional_core_memory_writes:0,input_plan:g.plan,termination:g.termination,final_fields:g.final_fields});$('#timeline-info').textContent=`${g.frames}原帧，保存城市／UI／请求变化${g.timeline.length}条；每帧完整数据另有JSON。`;$('#timeline').innerHTML=g.timeline.map(p=>`<tr><td>${p.frame}</td><td>${p.global_state}/${p.nmi_scene}</td><td>${esc(state(p))}</td><td>${p.UI_index_040C} → ${p.UI_candidate_at_index??'—'}</td><td>${p.UI_row_040D}</td><td>${p.PPU_jobs_007E}</td><td>${p.text_progress_0300}/${p.text_cursor_0304}</td></tr>`).join('');detail();}
function detail(){const g=group(),l=g.captures[Number($('#left').value)],r=g.captures[Number($('#right').value)];for(const[id,p]of[['before',l],['after',r]]){$('#'+id).src=p.image;$('#'+id+'-caption').textContent=`${p.display_label} · 原frame${p.frame} · ${state(p.fields)} · PNG ${p.PNG_sha256.slice(0,16)}…`;}
$('#transition').textContent=`实际检查点 ${l.display_label} → ${r.display_label}：global/NMI ${l.fields.global_state}/${l.fields.nmi_scene} → ${r.fields.global_state}/${r.fields.nmi_scene}；city ${state(l.fields)} → ${state(r.fields)}。`;$('#frame-left').value=String(l.frame);$('#frame-right').value=String(r.frame);fields();$('#rosters').innerHTML=[['UI_ids_0410_0419','原RAM十槽0410..0419'],['portrait_list_index_0408','原肖像名单索引0408'],['UI_index_040C','资料producer索引040C'],['UI_candidate_at_index','indexedOfficerID = 0410[040C]']].map(([k,n])=>`<tr><th>${esc(n)}</th><td>${esc(pretty(l.fields[k]))}</td><td>${esc(pretty(r.fields[k]))}</td></tr>`).join('');$('#raw').textContent=pretty({before:l,after:r});$('#native-links').innerHTML=[...g.links,{href:l.RAM,label:'前RAM'},{href:r.RAM,label:'后RAM'},{href:l.SRAM,label:'前SRAM'},{href:r.SRAM,label:'后SRAM'},{href:l.state,label:'前state'},{href:r.state,label:'后state'}].map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');}
function fields(){const g=group(),l=g.frame_views[Number($('#frame-left').value)-1],r=g.frame_views[Number($('#frame-right').value)-1],lc=g.captures[Number($('#left').value)],rc=g.captures[Number($('#right').value)];$('#field-frame-note').textContent=`字段frame${l.frame}／${r.frame}；上方PNG仍是检查点frame${lc.frame}／${rc.frame}，任意字段帧不冒充保存截图。`;
const names={global_state:'global007A',nmi_scene:'NMI0078',city_main:'活跃城市main0400',city_phase:'活跃城市phase0401',menu_cursor_0012:'原菜单游标0012',menu_cursor_0013:'原游标0013',controller_buttons_0081:'原button0081',UI_index_040C:'资料列表索引040C',UI_row_040D:'资料producer行040D（FF本身不证明画面完成）',UI_ids_0410_0417:'逐帧保存的八槽名单0410..0417',UI_candidate_at_index:'indexedOfficerID = 0410[040C]',UI_candidate_record:'该indexed ID原12B记录／字段',city_control_0470_047F:'原城市控制0470..047F',portrait_CHR_B8_B9:'肖像CHR缓存B8/B9',OAM_byte_count_007C:'原OAMcursor007C',PPU_jobs_007E:'请求007E',NMI_busy_007B:'原NMI busy007B',text_progress_0300:'文字进度0300',text_cursor_0304:'文字游标0304',RNG_cursor_0050:'原RNGcursor0050',calendar_and_request_6F00_6F06:'原年月／请求6F00..6F06',PCM_stereo_sample_frames:'该帧原PCM样本对'};$('#fields').innerHTML=Object.entries(names).map(([k,n])=>`<tr><th>${esc(n)}</th><td>${esc(typeof l[k]==='object'?pretty(l[k]):l[k])}</td><td>${esc(typeof r[k]==='object'?pretty(r[k]):r[k])}</td></tr>`).join('');}
$('#case').addEventListener('change',choose);$('#left').addEventListener('change',detail);$('#right').addEventListener('change',detail);$('#frame-left').addEventListener('change',fields);$('#frame-right').addEventListener('change',fields);choose();$('#row-fields').innerHTML=D.detail_rows.map(p=>`<tr><td>${p.row}</td><td>$${p.handler.toString(16).toUpperCase()}</td><td>${esc(p.label)}</td><td>${esc(pretty(p.record_offsets))}</td></tr>`).join('');
$('#modules').innerHTML=D.modules.map(m=>`<button type="button" data-module="${m.key}" aria-pressed="false">${esc(m.title)}</button>`).join('');$('#scope-table').innerHTML=D.modules.map(m=>`<tr><th>${esc(m.title)}</th><td>${esc(m.status)}</td><td>${fmt(m.CPU)}</td><td>${fmt(m.complete)}</td><td>${fmt(m.prefix)}</td><td>${fmt(m.RAM_bytes)}</td><td>${fmt(m.guard_count)}</td><td>${fmt(m.verification_CPU_callbacks)}</td><td>${fmt(m.production_CPU_callbacks)}</td></tr>`).join('');
function module(key){moduleKey=key;codeSerial++;const m=D.modules.find(p=>p.key===key);document.querySelectorAll('[data-module]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.module===key)));$('#module-title').textContent=m.title;$('#module-entry').textContent=m.entries;$('#module-metrics').innerHTML=[['当前回执',m.status],['原CPU例',m.CPU],['完整返回／有界出口',m.complete],['严格prefix',m.prefix],['source guards',m.guard_count],['验证端CPUcallee',m.verification_CPU_callbacks]].map(([k,v])=>`<div class="metric"><small>${esc(k)}</small><strong>${typeof v==='number'?fmt(v):esc(v??'待回执')}</strong></div>`).join('');$('#module-scope').textContent=`RAM范围：${m.RAM_scope}（固定至少${fmt(m.RAM_bytes)}字节），自由栈残留=${m.free_stack_residue}；SRAM${fmt(m.SRAM_bytes)}字节；真实AXYP/SP/PC、有序ports与银行另见精确回执。生产原CPUfallback=${fmt(m.production_CPU_callbacks)}。`;$('#module-note').textContent=[...m.notes,m.static_note].filter(Boolean).join('；');$('#module-links').innerHTML=m.links.map(p=>`<a href="${esc(p.href)}">${esc(p.label)}</a>`).join(' · ');$('#receipt').textContent=pretty(m.receipt);$('#code').textContent=m.source_href?'展开读取所选完整Python文本；浏览器不执行。':'该域独立源码／桥接来源尚待回执。';if($('#code-panel').open)loadCode();}
async function loadCode(){const m=D.modules.find(p=>p.key===moduleKey),token=++codeSerial;if(!m.source_href){$('#code').textContent='源码路径尚未确认，保持pending。';return;}try{const response=await fetch(m.source_href);if(!response.ok)throw new Error(String(response.status));const text=await response.text();if(token===codeSerial)$('#code').textContent=text;}catch(error){if(token===codeSerial)$('#code').textContent='源码文本读取未完成：'+error.message;}}
document.querySelectorAll('[data-module]').forEach(b=>b.addEventListener('click',()=>module(b.dataset.module)));$('#code-panel').addEventListener('toggle',()=>{if($('#code-panel').open)loadCode();});module('city-details');const c=D.integration;$('#integration-metrics').innerHTML=[['整合状态',c.status],['原CPU例',c.rom_cpu_case_count??c.actual_ROM_CPU_comparison_count],['完整返回',c.complete_return_count??c.original_complete_case_count],['严格prefix',c.strict_prefix_count??c.original_prefix_case_count],['source guards',c.source_guard_case_count??c.source_guard_count]].map(([k,v])=>`<div class="metric"><small>${k}</small><strong>${typeof v==='number'?fmt(v):esc(v??'待回执')}</strong></div>`).join('');$('#integration-note').textContent=`当前纯整合status=${c.status}，currentpins=${c.current_pins_match??'待回执'}。${c.note??'验证端CPUcallee调查与生产纯源码接入分别列示，不把静态节点或原callee调用次数当纯源码病例。'}`;$('#integration-links').innerHTML=c.status==='pending'?'回执路径尚未落盘，保持pending。':`<a href="${esc(c.path)}">当前纯源码整合回执</a>`;$('#integration-receipt').textContent=pretty(c);$('#discovery').textContent=pretty(D.discovery);
</script></body></html>'''
if __name__=='__main__':main()
