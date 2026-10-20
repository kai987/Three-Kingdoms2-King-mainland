#!/usr/bin/env python3
"""Browse phase16 frozen evidence only. Root owns CUA acceptance."""
from pathlib import Path
from urllib.parse import urlsplit
from collections import Counter
import argparse,hashlib,json,re,subprocess,tempfile,wave,sys
from PIL import Image
sys.dont_write_bytecode=True
from build_phase14_browser import HTML as BASE_HTML,pins,current_pin_status,trim,Parsed
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase16';RUN=OUT/'runtime'
MODULES={
 'fields':('字段与适性机械语义','field_semantics.py','原武将／城市字段、适性0／1／2／3字形、移动成本与阵形参数；有效范围和越界分开'),
 'succession':('真实战后继承消费者','battle_succession.py','physical25 A00C→AD81 city13；C132候选／C386无候选与BE01玩家选城／新君主写回'),
 'audio-requests':('真实音频请求caller','exact_audio_requests.py','固定音频请求／音序驱动闭包；原caller栈、寄存器与APU／Namco163端口协议'),
 'graphics':('实际年月图形请求','postbattle_graphics.py','physical29 A01E→A6B6实际年月packet；真实请求、队列／bank／返回，不伪造消费完成'),
 'loyalty':('战后忠诚跳转桥','postbattle_loyalty_bridge.py','physical10 A009原跳转至既有CF7C；复用已恢复内政helper，不称整个body是本轮新恢复')}
FIELD_NAMES={
 'global_state':'global007A','nmi_scene':'NMI0078','active_controller':'真正活跃controller','active_main':'活跃main','active_phase':'活跃phase',
 'calendar_year_6F00':'原年值6F00（89→显示189年）','calendar_month_zero_based_6F01':'原0-based月6F01','ruler_6F03':'君主6F03','turn_slot_6F04':'轮转slot6F04',
 'remaining_budget_raw_6F05':'行动预算6F05','event_flag_6F06':'原标志6F06','cooperation_status_6F8B':'合作字节6F8B（帧末观察）','domestic_phase_6F5B':'内政phase6F5B','domestic_budget_6F5D':'内政raw预算6F5D',
 'domestic_city_6F5E':'内政city6F5E','menu_cursor_0012':'菜单cursor0012','buttons_0081_0086':'原输入0081..86','PPU_jobs_007E':'原PPU请求007E','NMI_busy_007B':'原busy007B',
 'text_progress_0300':'文字进度0300','text_cursor_0304':'文字cursor0304','battle_AP_0505':'原0505 AP（非战场时为inactive原字节）','battle_round_0506':'原战场round0506',
 'campaign_record_summary':'原记录ID→[HP,status低2,raw16兵,raw16经验]','battle_active_units':'仅实际battle场景：slot/ID/XY/原side/condition','ordinary_attack_object_values':'仅实际attack场景：原5AC..5C1对象值',
 'city_owners':'原30城owner低3','city_rosters_sha256':'逐帧30×10原名册完整hash','city_nested_0402_raw':'0402原字节（city13/phase4时为nestedphase）','all237_officer_status_low2':'原237武将status低2','all237_officer_byte5_raw':'原237武将byte5（保留raw）','all30_city_byte27':'原30城byte27','UI_row_040D':'真实资料row040D','UI_officer_0410':'资料名单首ID0410（本资料页code0..3为131）','PCM_stereo_sample_frames':'该实际帧PCM样本对'}
FIELDS=tuple(FIELD_NAMES)
RAW_FIELDS=('city_state_0400_040F','title_state_0540_0544','battle_state_0500_050F','calendar_and_turn_6F00_6F06','ruler_records_6F07_6F3E',
 'domestic_control_6F5B_6F62','cooperation_6F8B_6FAB','palette_0100_013F','text_queue_0310_037F','mapper_main_DE_DF_E0','mapper_NMI_E1_E2_E3','IRQ_fields_0068_0075','audio_RAM_0700_07FF',
 'all30_city_records_raw32','all237_officer_status_low2','all237_officer_byte5_raw','all30_city_byte1','all30_city_byte27','all30_city_bytes28_31','UI_row_040D','UI_packet_0380_03BF','ordinary_attack_fields_0550_05D7','campaign_officers','unit_arrays','city_rosters','rulers','RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256')
DEFAULTS={'heir-city13-month':('actual-city13-consumer-open','post-succession-month-final'),
 'no-heir-city13-month':('actual-city13-consumer-open','post-succession-month-final'),
 'player-defeat-successor':('player-failure-attack-enter','player-failure-final'),
 'affinity-pages':('trait-code0-info-open','trait-code3-info-open')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def relative(p):return str(p.relative_to(OUT))if p.is_relative_to(OUT)else'../../'+str(p.relative_to(ROOT))
def link(p,label):return dict(href=relative(p),label=label)
def view(row):
 v={k:row.get(k)for k in FIELDS};v['city_nested_0402_raw']=row['city_state_0400_040F'][2];v['campaign_record_summary']={}
 for ID,record in row['campaign_officers'].items():
  raw=bytes.fromhex(record['raw']);v['campaign_record_summary'][ID]=[raw[0],raw[11]&3,int.from_bytes(raw[8:10],'little'),int.from_bytes(raw[6:8],'little')]
 v['battle_active_units']=[{k:u[k]for k in('slot','officer_id','x','y','side_condition','condition')}for u in row['active_units']]
 v['ordinary_attack_object_values']=list(bytes.fromhex(row['ordinary_attack_fields_0550_05D7'])[0x5AC-0x550:0x5C2-0x550])if row['active_controller']=='attack'else None
 return v

def module_data(key):
 title,filename,entries=MODULES[key];folder=OUT/key;source=ROOT/'source/recovered'/filename;receipt=folder/'validation.json';r=read(receipt)if receipt.is_file()else{}
 checked=pins(r,source);status=r.get('status','pending');notes=[]
 if r.get('quick'):status='quick'
 if checked and not current_pin_status(checked):status='source_changed'
 if source.is_file()and not any(p['path']==str(source.relative_to(ROOT))for p in checked):status='unconfirmed_source_pin'
 cpu=r.get('rom_cpu_case_count');complete=r.get('complete_return_count',r.get('total_complete_return_CPU_cases'));prefix=r.get('strict_prefix_count',r.get('total_strict_prefix_CPU_cases'))
 if cpu is not None:assert cpu==complete+prefix
 if key=='fields':notes.append('完整upper glyph、lower glyph前缀、player/AI移动、formation矩阵分开。code3属于原raw位域但表外读后续机器码，不是官方第四种能力。未命名字段不猜正式名称。')
 if key=='succession':notes.append('真正Native入口为city13/AD81，不能套用DomesticCA19。候选C132只按原owned-city连续名册／家族或德，不借HP/status/byte5做未有的资格。无候选C386仅leaderFF，不自动中立全部城市。')
 if key=='audio-requests':notes.append('请求driver与实际caller寄存器／SP／PC分开核对，原Native WAV来自Nestopia。硬件输入、端口序、严格等待仍以回执scope为准，不称源码独立PCM合成。')
 if key=='graphics':notes.append('年月packet／nametable请求来自原A6B6流程；生产原请求和已被原PPU消费的PNG是两种证据，不能用空渲染或fake ack越过依赖。')
 if key=='loyalty':notes.append('新A009跳转桥复用Domestic CF7C既有纯helper；忠诚byte3作用不等城市名册／即时政治转属，复用body不计作新恢复整份内政程序。')
 
 result=trim(r)
 files=[(source,'完整可读源码'),(folder/'README.md','范围与API'),(folder/'evidence.json','原bytes／数据／来源'),(receipt,'原CPU回执')]
 if key=='audio-requests':
  extra_path=folder/'actual-callers.json';extra=read(extra_path);extra_pins=pins(extra,source)
  assert extra['status']=='passed'and current_pin_status(extra_pins),'Final actual audio caller receipt required'
  result['additional_actual_caller_receipt']=trim(extra)
  notes.append(f'额外{extra["rom_cpu_case_count"]}个actualcallee原CPU案例独立列示，不在上方{cpu}个body矩阵中；Native只供内存，实际caller寄存器／PC来自受控原CPU。')
  files.append((extra_path,'额外actualcaller独立回执'))
 if key=='loyalty':files.append((ROOT/'source/recovered/domestic_cooperation_controller.py','已恢复CF7C parent完整源码'))
 for name in('raw.asm','original.asm','original-ranges.asm','static-catalog.json','source-catalog.json','writer-provenance.json','executed-instructions.json'):files.append((folder/name,name))
 result['current_pin_checks']=checked
 return dict(key=key,title=title,entries=entries,status=status,CPU=cpu,complete=complete,prefix=prefix,guards=r.get('source_guard_case_count'),
  verification_CPU_callbacks=r.get('original_fixed_helper_calls',0 if r else None),production_CPU_callbacks=r.get('source_original_CPU_callbacks',0 if key=='fields'and r else None),
  comparison=r.get('comparison',r.get('scope',{})),counts=r.get('counts',r.get('group_case_counts',{})),completion_kinds=r.get('completion_kinds',{}),notes=notes,receipt=result,
  source_href=relative(source)if source.is_file()else None,links=[link(p,label)for p,label in files if p.is_file()])
def integration_data(path):
 if not path.is_file():return dict(status='pending',path=relative(path),note='Root最终纯源码整合尚待冻结')
 r=read(path);checked=pins(r,ROOT/'source/recovered/battle_succession.py');result=trim(r);result['current_pin_checks']=checked;result['current_pins_match']=current_pin_status(checked);result['path']=relative(path)
 if not result['current_pins_match']:result['status']='source_changed'
 result['linked_receipts']=[];return result

def native_data():
 e=read(RUN/'evidence.json');assert e['schema']=='phase16-native-succession-flows-v1'and e['status']=='passed';qa=Counter();groups=[]
 for pin in e['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
 for case in e['native_cases']:
  folder=RUN/case['case'];v=read(RUN/case['validation']);rep=read(RUN/case['repeat_validation']);second=ROOT/rep['second_run']
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal']and rep['whole_serialized_buffers_exact']and v['fresh_process_per_run']
  assert not v['battery_file_imported']and not v['additional_ready_or_result_injections']and not v['source_pipeline_installed']and not v['native_internal_CPU_trace']and not v['source_CPU_comparisons_in_this_receipt']
  assert sha(ROOT/'scripts/capture_succession_flows.py')==v['script_sha256']
  if v['cold_boot']:assert not v['state_imported']and not v['preparation']
  else:assert v['state_imported']and sha(ROOT/v['mother_state'])==v['mother_sha256']
  for name,pin in v['artifact_sha256'].items():
   a,b=folder/name,second/name;assert a.stat().st_size==b.stat().st_size==pin['bytes']>0 and sha(a)==sha(b)==pin['sha256'];qa['nonempty_double_run_artifacts']+=1
  for name in rep['formal_JSON_exact_parity']:assert(folder/name).read_bytes()==(second/name).read_bytes();qa['formal_JSON_exact_parity']+=1
  for name in v['excluded_empty_VRAM']:assert(folder/name).stat().st_size==0;qa['excluded_empty_VRAM']+=1
  qa['excluded_snapshot_metadata_JSON']+=len(v['excluded_snapshot_metadata_JSON'])
  for group in v['preparation_groups']:
   for kind,base in(('RAM',0),('SRAM',0x6000)):
    before=bytearray((folder/group['before'][kind]['path']).read_bytes());after=(folder/group['after'][kind]['path']).read_bytes()
    for p in group['writes']:
     if p['kind']==kind:assert before[p['address']-base]==p['before'];before[p['address']-base]=p['after']
    assert bytes(before)==after
   qa['preparation_group_checks']+=1
  context=v['inherited_context'];assert sha(ROOT/context['validation'])==context['validation_sha256']
  for crop in v['verified_effects'].get('affinity_glyph_regions',[]):
   with Image.open(folder/crop['PNG'])as im:assert hashlib.sha256(im.crop(crop['box']).tobytes()).hexdigest()==crop['RGB_sha256']
   qa['affinity_glyph_region_checks']+=1
  rows=read(RUN/case['frame_services']);points=read(RUN/case['checkpoints']);plan=read(RUN/case['input_plan']);events=read(RUN/case['campaign_events'])
  assert len(rows)==v['frames']and len(points)==v['checkpoint_count']and [r['frame']for r in rows]==list(range(1,len(rows)+1))
  pos=0
  for p in plan:assert p['start_frame']==pos;pos+=p['frames']
  assert pos==len(rows)
  wav=RUN/case['full_WAV'];audio=v['full_audio']
  with wave.open(str(wav),'rb')as w:
   assert(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,audio['stereo_sample_frames']);pcm=w.readframes(w.getnframes())
  assert len(pcm)==audio['PCM_bytes']and hashlib.sha256(pcm).hexdigest()==audio['PCM_sha256']and sha(wav)==audio['WAV_sha256']and any(pcm);qa['WAV_header_PCM_hash']+=1
  cursor=0;timeline=[];previous=None;views=[]
  for r in rows:
   count=r['PCM_stereo_sample_frames'];part=pcm[cursor:cursor+count*4];cursor+=count*4
   assert hashlib.sha256(part).hexdigest()==r['PCM_sha256']and bool(any(part))==r['PCM_nonzero']and cursor==r['PCM_stop_byte'];qa['frame_PCM_segments']+=1
   f=dict(frame=r['frame'],**view(r));views.append([f[k]for k in('frame',*FIELDS)])
   signature=tuple(str(r[k])for k in('global_state','nmi_scene','active_controller','active_main','active_phase','calendar_year_6F00','calendar_month_zero_based_6F01','ruler_6F03','remaining_budget_raw_6F05','cooperation_status_6F8B'))
   if signature!=previous:timeline.append(f);previous=signature
  assert cursor==len(pcm);cursor=0
  for call in read(folder/'audio-callbacks.json'):
   count=call['stereo_sample_frames'];part=pcm[cursor:cursor+count*4];cursor+=count*4
   assert hashlib.sha256(part).hexdigest()==call['pcm_sha256']and 0<=call['emulated_frame_start']<len(rows);qa['audio_callback_segments']+=1
  assert cursor==len(pcm);captures=[]
  for p in points:
   row=rows[p['frame']-1];png=folder/p['image'];ram=folder/p['RAM'];sram=folder/p['SRAM'];state=folder/p['state']
   with Image.open(png)as im:im.load();assert im.size==(256,240)and im.mode=='RGB'and hashlib.sha256(im.tobytes()).hexdigest()==row['RGB_sha256']
   assert ram.stat().st_size==2048 and sha(ram)==row['RAM_sha256'];assert sram.stat().st_size==8192 and sha(sram)==row['SRAM_sha256']and state.stat().st_size>0
   captures.append(dict(label=p['label'],display_label=p['label'],frame=p['frame'],reason=p['reason'],image=relative(png)+'?sha='+sha(png),PNG_sha256=sha(png),RAM=relative(ram),SRAM=relative(sram),state=relative(state),
    fields=view(row),raw={k:p['fields'].get(k,row.get(k))for k in RAW_FIELDS}));qa['same_frame_PNG_RAM_SRAM_state']+=1
  groups.append(dict(case=case['case'],title=case['title'],frames=v['frames'],checkpoint_count=v['checkpoint_count'],captures=captures,timeline=timeline,frame_views=views,defaults=DEFAULTS[case['case']],events=events,plan=plan,
   termination=v['termination'],final_fields=v['final_fields'],cold_boot=v['cold_boot'],state_imported=v['state_imported'],mother_state=v['mother_state'],mother_sha256=v['mother_sha256'],preparation=v['preparation'],preparation_groups=v['preparation_groups'],additional_core_memory_writes=v['additional_core_memory_writes'],inherited_context=v['inherited_context'],verified_effects=v['verified_effects'],
   audio=dict(path=relative(wav)+'?sha='+sha(wav),download=relative(wav),seconds=audio['stereo_sample_frames']/48000,**audio),
   links=[link(folder/name,txt)for name,txt in [('validation.json','病例回执'),('repeat-validation.json','整份state双跑'),('input-plan.json','实际输入'),('frame-services.json','逐帧原字段/hash'),('campaign-events.json','原观察事件'),('preparation.json','准备前后完整dump'),('audio-callbacks.json','实际PCM callbacks')]]))
 summary=e['summary'];assert qa['nonempty_double_run_artifacts']==summary['nonempty_repeat_artifact_checks']and qa['formal_JSON_exact_parity']==summary['formal_JSON_repeat_checks']
 assert qa['same_frame_PNG_RAM_SRAM_state']==summary['checkpoint_count']and qa['excluded_empty_VRAM']==summary['excluded_empty_VRAM']
 return e,groups,dict(qa)

def template():
 html=BASE_HTML
 replacements={
  '冷启动、复位与合作AI证据':'真实战后继承、势力退出与字段证据','阶段十四 · 原冷启动／重启 · 独立合作AI源码':'阶段十六 · 原city13继承／玩家败北 · 字段／图形／音频服务','冷启动与合作调度':'实际继承与字段语义',
  '../phase13/index.html':'../phase15/index.html','城市与全局UI':'长期回合与连续出征','四个源码域':'五个源码域','三组真实冷启动与合作流程':'四组实际继承、玩家败北与资料适性流程','四个独立源码域与验证范围':'五个独立源码域与验证范围',
  '三案都直接加载只读原ROM，不导入状态或battery文件，不新增core内存／ready／结果写入。复位只证明同一已加载实例的8KiB SRAM保留；不是断电battery文件重载。标题软件重启是原介绍超时0B58路径，非猜测的重启菜单。':'四案均公开母档；两个city13案继承旧19／26byte事前准备与已由原核心发生的死亡，本轮新增writes0。玩家败北与适性案的新数值准备逐byte公开，原ready／结果／request／ack未注入。leaderFF后空城owner仍可保留；适性3是表外机器码字形，不是官方第四能力。',
  '冷起点、原输入／复位操作与结束条件':'原起点／母档、完整数据准备、原输入与终点','三案native输入':'四案native输入',
  '<a href="../../source/recovered/scene_coordinator.py">coordinator API</a>':'<a href="../../source/recovered/battle_succession.py">真实继承 API</a><a href="../../source/recovered/scene_coordinator.py">coordinator API</a>',
  "['真实冷boot回放',s.native_case_count]":"['正式原核心回放',s.native_case_count]",
  "let moduleKey='boot'":"let moduleKey='fields'","module('boot');":"module('fields');"}
 for a,b in replacements.items():html=html.replace(a,b)
 html=html.replace("$('#case-scope').textContent=`真实只读ROM冷起点 · 无state／battery文件导入 · ${fmt(g.frames)}原帧。${g.termination}`;", "$('#case-scope').textContent=`公开母档一次state import · 本轮新增${g.additional_core_memory_writes}byte准备写／继承旧准备${g.inherited_context.inherited_preparation_byte_writes}byte · ${fmt(g.frames)}原帧。${g.termination}`;")
 html=html.replace("{cold_boot:true,state_imported:false,battery_file_imported:false,additional_core_memory_writes:0,input_plan:g.plan,termination:g.termination,reset_events:g.reset_events,software_restart_frames:g.software_restart_frames,final_fields:g.final_fields}","{cold_boot:false,state_imported:g.state_imported,mother:g.mother_state,mother_sha256:g.mother_sha256,inherited_context:g.inherited_context,battery_file_imported:false,additional_core_memory_writes:g.additional_core_memory_writes,preparation:g.preparation,preparation_groups:g.preparation_groups,input_plan:g.plan,verified_effects:g.verified_effects,termination:g.termination,final_fields:g.final_fields}")
 html=html.replace("const l=g.frame_views[a-1],r=g.frame_views[b-1],lc=", "const unpack=v=>Object.fromEntries(D.frame_keys.map((k,i)=>[k,v[i]]));const l=unpack(g.frame_views[a-1]),r=unpack(g.frame_views[b-1]),lc=")
 html=re.sub(r'const names=\{[\s\S]*?\};\$\(\x27#fields\x27\)',lambda m:'const names='+json.dumps(FIELD_NAMES,ensure_ascii=False,separators=(',',':'))+';$(\x27#fields\x27)',html)
 html=re.sub(r'<p class="note">主循环E066边界[\s\S]*?</ol>',r'''<p class="note">Native原帧没有内部指令trace。真实战后city13、DomesticCA19、自动候选和玩家选城／选将分别归属原入口；字段／音频／图形／忠诚桥按各自完整返回或严格prefix核对，不自动填ready／ack或缺失硬件读取。</p>
<ol class="steps"><li><strong>实际继承入口</strong><br>原city13 AD81→C132／C386，家族／德筛选和玩家BE01选择分开；leaderFF不等全部城自动中立。月轮实际跳过君主由原帧另证。</li><li><strong>字段与越界语义</strong><br>正式平／山／水和rawcode3机器码字形分开。移动／阵形矩阵、byte5及未定城尾字段保留准确作用域，不猜正式名称。</li><li><strong>真实服务与复用</strong><br>年月图形packet、音频caller和旧CF7C忠诚纯helper严格保留返回协议；新跳转桥不冒称又恢复整份内政。原PNG／WAV不是源码独立NES帧或PCM合成。</li></ol>''',html)
 html=html.replace("['main E066边界',c.main_boundary_count??c.complete_main_boundary_count]","['完整返回／出口',c.complete_return_count]")
 html=html.replace("['实际caller RTS',c.actual_caller_return_count]","['实际caller RTS',c.actual_caller_return_count??c.completion_kinds?.actual_caller_RTS]")
 html=html.replace("['reset E066边界',c.reset_boundary_count]","['生产CPUfallback',c.source_original_CPU_callbacks]")
 html=html.replace("实际caller register／SP／PC、pending硬件输入与已退役reset caller分别核对","实际caller register／SP／PC、真实服务返回与pending边界分别核对")
 html=html.replace('</div><p id="transition"></p>',r'''</div><p id="transition"></p><section id="trait-zoom" hidden><h3>所选原PNG的16×16适性字形</h3><p>固定原图区域[64,192,80,208]，CSS放大原像素；没有生成新字形或替换完整截图。</p><div class="screens"><figure id="trait-left"><div class="trait-window"><img id="trait-before" alt="前原PNG适性区域"></div><figcaption id="trait-before-caption"></figcaption></figure><figure id="trait-right"><div class="trait-window"><img id="trait-after" alt="后原PNG适性区域"></div><figcaption id="trait-after-caption"></figcaption></figure></div></section>''')
 html=html.replace("$('#transition').textContent=",r'''const trait=g.case==='affinity-pages';$('#trait-zoom').hidden=!trait;for(const[id,p,figure]of[['trait-before',l,'trait-left'],['trait-after',r,'trait-right']]){const m=/^trait-code([0-3])-info-open$/.exec(p.label);$('#'+figure).hidden=!trait||!m;if(trait&&m){$('#'+id).src=p.image;const c=g.verified_effects.affinity_glyph_regions.find(x=>x.code===Number(m[1]));$('#'+id+'-caption').textContent=`rawcode${m[1]} · 原frame${p.frame} · regionRGB ${c.RGB_sha256.slice(0,16)}…`;}}$('#transition').textContent=''')
 html=html.replace('</style>',' .trait-window{width:128px;height:128px;overflow:hidden}.trait-window img{display:block;width:2048px;height:1920px;max-width:none;image-rendering:pixelated;transform:translate(-512px,-1536px)} </style>')
 return html

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--integration-receipt',type=Path,default=OUT/'source-integration.json');p.add_argument('--require-final',action='store_true');a=p.parse_args();a.integration_receipt=a.integration_receipt.resolve()
 e,groups,qa=native_data();modules=[module_data(k)for k in MODULES];integration=integration_data(a.integration_receipt)
 if a.require_final:assert all(m['status']=='passed'for m in modules)and integration['status']=='passed','Final current pins required'
 css=re.search(r'<style>([\s\S]+?)</style>',(ROOT/'analysis/phase14/index.html').read_text()).group(1)
 data=dict(summary=e['summary'],core=e['core'],groups=groups,modules=modules,integration=integration,QA=qa,frame_keys=['frame',*FIELDS])
 html=template().replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/'))
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html);parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids));links=list(parsed.links)
 for g in groups:
  links.extend(x['href']for x in g['links']);links.append(g['audio']['download'])
  for c in g['captures']:links.extend(c[k]for k in('image','RAM','SRAM','state'))
 for m in modules:links.extend(x['href']for x in m['links'])
 if integration['status']!='pending':links.append(integration['path'])
 for href in links:
  clean=urlsplit(href).path
  if clean and not clean.startswith('#')and clean!='browser-static-validation.json':assert(OUT/clean).resolve().is_file(),href
 js=re.search(r'<script>([\s\S]+?)</script>',html).group(1)
 with tempfile.NamedTemporaryFile('w',suffix='.js')as f:f.write(js);f.flush();subprocess.run(['node','--check',f.name],check=True,capture_output=True)
 result=dict(schema='phase16-browser-static-v1',status='passed',HTML_sha256=sha(OUT/'index.html'),generator_sha256=sha(Path(__file__)),template_generator_sha256=sha(ROOT/'scripts/build_phase14_browser.py'),
  unique_DOM_ids=len(parsed.ids),local_links_checked=len(links),JS_syntax='passed',native_static_QA=qa,native_evidence_sha256=sha(RUN/'evidence.json'),native_files_modified=False,
  modules=[{k:m[k]for k in('key','status','CPU','complete','prefix','guards','verification_CPU_callbacks','production_CPU_callbacks')}for m in modules],integration=dict(status=integration['status'],path=integration['path'],current_pins_match=integration.get('current_pins_match')),
  field_frames=sum(len(g['frame_views'])for g in groups),final_required=a.require_final,browser_visual_acceptance='Root owns CUA; this receipt static only')
 (OUT/'browser-static-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
