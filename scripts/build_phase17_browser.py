#!/usr/bin/env python3
"""Browse frozen Phase17 evidence; do not execute ROM, IR or game models.

Root owns CUA acceptance. --check-only checks the template/formal artifacts
without creating HTML; a final build is performed only after Root release.
"""
from pathlib import Path
from urllib.parse import urlsplit
from collections import Counter
import argparse,hashlib,json,re,subprocess,tempfile,wave,sys
from PIL import Image
sys.dont_write_bytecode=True
from build_phase14_browser import HTML as BASE_HTML,pins,current_pin_status,trim,Parsed
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase17';RUN=OUT/'runtime'
MODULES={
 'fields':('城市字段与名册边界','city_field_contracts.py','fixed record pointers；physical10/11 overlappingword300、显式A442前缀；25/26 C21D满10槽有界扫描与27/28真实容量门槛'),
 'extinction':('玩家失势与败亡结局','player_extinction.py','真实city13 AD81父流程／BE2E首名单候选／C386仅清leader；NMI8 loss mode0、markerFE A-only、真实E000或父流程恢复'),
 'adapter':('败亡场景整合适配器','extinction_scene_services.py','复用实际主循环／音频／图形服务，把NMI8 loss模式接到独立PlayerLossEnding；计数归整合回执，不新增一份CPU矩阵')}
FIELD_NAMES={
 'global_state':'global007A','nmi_scene':'NMI0078','active_controller':'真正活跃controller','active_main':'活跃main','active_phase':'活跃phase',
 'calendar_year_6F00':'原年6F00（89显示189年）','calendar_month_zero_based_6F01':'原0-based月6F01','ruler_6F03':'当前君主6F03','turn_slot_6F04':'轮转slot6F04','remaining_budget_raw_6F05':'行动预算6F05',
 'cooperation_status_6F8B':'原合作字节6F8B（帧末观察）','menu_cursor_0012':'原菜单cursor0012','buttons_0081_0086':'原两手柄输入0081..86','PPU_jobs_007E':'原PPU请求007E','NMI_busy_007B':'原busy007B',
 'text_progress_0300':'文字进度0300','text_cursor_0304':'文字cursor0304','city_nested_0402_raw':'city13 nested0402原字节','succession_fields_040A_040F':'原继承040A..040F',
 'ending_mode_0541':'原败亡模式0541','ending_phase_0542':'原结局phase0542','ending_animation_marker_04CB':'原结局04CB（FE才接受A退出）','ending_parent_0472_0473':'原saved parent0472/73',
 'ending_continue_flag_6F43':'原开局模式残留6F43（非实时活玩家数量）','campaign_record_summary':'原武将ID→[HP,status低2,raw16兵,raw16经验]','ruler_ids_and_status':'逐帧原7君主ID与status',
 'city_owners':'原30城owner低3','city_rosters_sha256':'逐帧30×10名册完整hash','all30_city_byte1':'原城市+1单字节（未定正式名）','all30_city_bytes28_31':'原30城尾28..31（未定正式名）',
 'battle_AP_0505':'原0505 AP（非battle时为inactive字节）','PCM_stereo_sample_frames':'该实际帧PCM样本对'}
FIELDS=tuple(FIELD_NAMES)
RAW_FIELDS=('city_state_0400_040F','title_state_0540_0544','battle_state_0500_050F','calendar_and_turn_6F00_6F06','ruler_records_6F07_6F3E',
 'ending_mode_0541','ending_phase_0542','ending_fields_04C9_04CE','ending_parent_0472_0473','ending_substitutions_042C_0434','ending_continue_flag_6F43','succession_fields_040A_040F',
 'cooperation_6F8B_6FAB','palette_0100_013F','text_queue_0310_037F','mapper_main_DE_DF_E0','mapper_NMI_E1_E2_E3','IRQ_fields_0068_0075','audio_RAM_0700_07FF',
 'all30_city_records_raw32','all237_officer_status_low2','all237_officer_byte5_raw','all30_city_byte1','all30_city_byte27','all30_city_bytes28_31','campaign_officers','unit_arrays',
 'city_rosters','rulers','RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256')
DEFAULTS={
 'single-player-empty-rosters-reset':('loss-ending-ready-for-original-A','reactivated-player-city'),
 'two-player-empty-rosters-continue':('loss-ending-ready-for-original-A','remaining-player-world-ready'),
 'former-leader-only-candidate':('former-leader-confirm-A0','former-leader-selection-final')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def relative(p):return str(p.relative_to(OUT))if p.is_relative_to(OUT)else'../../'+str(p.relative_to(ROOT))
def link(p,label):return dict(href=relative(p),label=label)
def view(row):
 v={k:row.get(k)for k in FIELDS};v['city_nested_0402_raw']=row['city_state_0400_040F'][2];v['campaign_record_summary']={}
 for ID,record in row['campaign_officers'].items():
  raw=bytes.fromhex(record['raw']);v['campaign_record_summary'][ID]=[raw[0],raw[11]&3,int.from_bytes(raw[8:10],'little'),int.from_bytes(raw[6:8],'little')]
 return v

def integration_data(path):
 if not path.is_file():return dict(status='pending',path=relative(path),note='Root最终组合回执尚待冻结',completion_kinds={})
 r=read(path);checked=pins(r,ROOT/'source/recovered/extinction_scene_services.py');v=trim(r);v['current_pin_checks']=checked;v['current_pins_match']=current_pin_status(checked);v['path']=relative(path)
 if not checked or not v['current_pins_match']:v['status']='source_changed'
 v['completion_kinds']=dict(Counter(row['completion_kind']for row in r.get('rows',[])if row.get('comparison')!='strict_prefix'))
 v['linked_receipts']=[link(p,label)for p,label in((OUT/'README.md','本阶段报告'),(OUT/'fields/README.md','字段边界说明'),(OUT/'extinction/README.md','败亡与结局说明'))if p.is_file()]
 v['note']='两条原内存组合序列；一个main E066／真实NMI与IRQ RTI完成边界，一个E000非局部E066重启。nested调度不重复加计；声明硬件输入与原Native帧分开。'
 return v

def module_data(key,integration):
 title,filename,entries=MODULES[key];source=ROOT/'source/recovered'/filename;folder=OUT/key
 path=OUT/'source-integration.json'if key=='adapter'else folder/'validation.json';r=read(path)if path.is_file()else{}
 checked=pins(r,source);status=r.get('status','pending')
 if r.get('quick'):status='quick'
 if checked and not current_pin_status(checked):status='source_changed'
 if source.is_file()and not any(p['path']==str(source.relative_to(ROOT))for p in checked):status='unconfirmed_source_pin'
 cpu=r.get('rom_cpu_case_count');complete=r.get('complete_return_count',r.get('total_complete_return_CPU_cases'));prefix=r.get('strict_prefix_count',r.get('total_strict_prefix_CPU_cases'));reset=r.get('reset_boundary_count',0)
 if cpu is not None:assert cpu==complete+prefix+reset
 notes=[]
 if key=='fields':notes=['城市+1与金低字节+2组成重叠word，原比较门槛300；不能给单字节或尾28..31猜官方名称。',
  '合法名册17..26满10槽可以没有FF；C21D有界扫描不读27及尾28..31。原合法满10生产者与原bounded消费者是独立证据。',
  'A442无界append的尾部／邻城别名只在显式容量边界输入展示；它绕过正常player容量门槛，不证明自然可达溢出。原缺FF循环保留等待，不伪造结束。']
 elif key=='extinction':notes=['玩家BE2E允许A/B，只看owned城首名单槽非FF，不查HP/status/byte5；空城、首槽hole和死者名单分别测试。',
  'C386只清leaderFF，失势城市owner仍可为2；6F43为开局模式残留，不是实时活玩家数量。',
  '败亡mode0 markerFE只接受新A。reset病例到真实E000/E066非局部边界，不能叫callerRTS；缺reset或PPUSTATUS等待仍严格prefix。原NativeWAV不等源码PCM合成。']
 else:notes=['适配器第三全文按钮复用根组合回执，不新增一份独立CPU／guard计数。',
  '保留原main／audio caller和NMI8 PlayerLossEnding；真实SP/PC、pending输入与原mapper/端口协议来自组合差分，源码没有原CPU或IR fallback。']
 files=[(source,'完整UTF8可读源码'),(path,'当前CPU／guards回执')]
 if key!='adapter':
  files.extend((folder/name,label)for name,label in [('README.md','范围与API'),('evidence.json','原bytes／数据／来源'),('raw.asm','原汇编'),('original.asm','原汇编'),('static-catalog.json','有界目录'),('schema.json','城市记录schema'),('alias-refinement.json','别名精化'),('legal-full-roster-origin.json','原合法满10生产者'),('executed-instructions.json','执行覆盖')])
 else:files.extend([(ROOT/'source/recovered/integrated_scene_services.py','复用的主循环服务'),(ROOT/'source/recovered/battle_succession.py','复用的完整父继承controller'),(ROOT/'source/recovered/global_ui_controller.py','复用的完整结局／UI父controller')])
 if key=='extinction':files.append((ROOT/'source/recovered/battle_succession.py','原父继承完整源码'))
 ret=trim(r);ret['current_pin_checks']=checked
 return dict(key=key,title=title,entries=entries,status=status,standalone_counted=key!='adapter',CPU=cpu if key!='adapter'else None,complete=complete if key!='adapter'else None,
  reset=reset if key!='adapter'else None,prefix=prefix if key!='adapter'else None,guards=r.get('source_guard_case_count')if key!='adapter'else None,
  verification_CPU_callbacks=r.get('original_CPU_helper_callbacks',r.get('original_fixed_helper_calls',0 if r else None)),production_CPU_callbacks=r.get('source_original_CPU_callbacks'),
  comparison=r.get('comparison',r.get('scope',{})),counts=r.get('counts',r.get('group_case_counts',{}))if key!='adapter'else{},
  completion_kinds=r.get('completion_kinds',{})if key!='adapter'else integration.get('completion_kinds',{}),notes=notes,receipt=ret,
  source_href=relative(source)+'?sha='+sha(source)if source.is_file()else None,source_sha256=sha(source)if source.is_file()else None,links=[link(p,label)for p,label in files if p.is_file()])

def native_data():
 e=read(RUN/'evidence.json');assert e['schema']=='phase17-native-player-extinction-flows-v1'and e['status']=='passed';qa=Counter();groups=[]
 for pin in e['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
 for case in e['native_cases']:
  folder=RUN/case['case'];v=read(RUN/case['validation']);rep=read(RUN/case['repeat_validation']);second=ROOT/rep['second_run']
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal']and rep['whole_serialized_buffers_exact']and v['fresh_process_per_run']
  assert not any(v[k]for k in('battery_file_imported','additional_ready_or_result_injections','source_pipeline_installed','native_internal_CPU_trace','source_CPU_comparisons_in_this_receipt','death_or_status_bit_preparation','frontend_reset_calls'))
  assert sha(ROOT/'scripts/capture_player_extinction.py')==v['script_sha256']and v['additional_core_memory_writes']==len(v['preparation'])
  if v['cold_boot']:assert not v['state_imported']and v['mother_state']is None
  else:
   assert v['state_imported']and sha(ROOT/v['mother_state'])==v['mother_sha256'];ctx=v['inherited_context']
   assert sha(ROOT/ctx['ancestor_state'])==ctx['ancestor_state_sha256']==v['mother_sha256']and ctx['inherited_preparation_byte_writes']==0
  for name,pin in v['artifact_sha256'].items():
   a,b=folder/name,second/name;assert a.stat().st_size==b.stat().st_size==pin['bytes']>0 and sha(a)==sha(b)==pin['sha256'];qa['nonempty_double_run_artifacts']+=1
  for name in rep['formal_JSON_exact_parity']:assert(folder/name).read_bytes()==(second/name).read_bytes();qa['formal_JSON_exact_parity']+=1
  for name in v['excluded_empty_VRAM']:assert(folder/name).stat().st_size==0;qa['excluded_empty_VRAM']+=1
  qa['excluded_snapshot_metadata_JSON']+=len(v['excluded_snapshot_metadata_JSON'])
  for g in v['preparation_groups']:
   for kind,base,size in(('RAM',0,2048),('SRAM',0x6000,8192)):
    before=bytearray((folder/g['before'][kind]['path']).read_bytes());after=(folder/g['after'][kind]['path']).read_bytes();assert len(before)==len(after)==size
    for p in g['writes']:
     if p['kind']==kind:assert before[p['address']-base]==p['before'];before[p['address']-base]=p['after']
    assert bytes(before)==after
   qa['preparation_group_checks']+=1
  rows=read(RUN/case['frame_services']);points=read(RUN/case['checkpoints']);plan=read(RUN/case['input_plan']);events=read(RUN/case['campaign_events'])
  assert len(rows)==v['frames']and len(points)==v['checkpoint_count']and [r['frame']for r in rows]==list(range(1,len(rows)+1))
  pos=0
  for p in plan:assert p['start_frame']==pos and p.get('controller_port',0)in(0,1);pos+=p['frames']
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
   signature=tuple(str(r[k])for k in('global_state','nmi_scene','active_controller','active_main','active_phase','ruler_6F03','remaining_budget_raw_6F05','ending_continue_flag_6F43','city_state_0400_040F','ending_animation_marker_04CB'))
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
   raw={k:p['fields'].get(k,row.get(k))for k in RAW_FIELDS}
   # These full lists are checkpoint declarations, not missing per-frame data.
   sr=sram.read_bytes();raw['city_rosters']=raw['city_rosters']if raw['city_rosters']is not None else[list(sr[32*i+17:32*i+27])for i in range(30)]
   assert len(raw['city_rosters'])==30 and raw['rulers']is not None and len(raw['rulers'])==7
   raw['checkpoint_only_original_6F43_6F44']=list(sr[0xF43:0xF45])
   captures.append(dict(label=p['label'],display_label=p['label'],frame=p['frame'],reason=p['reason'],image=relative(png)+'?sha='+sha(png),PNG_sha256=sha(png),RAM=relative(ram),SRAM=relative(sram),state=relative(state),fields=view(row),raw=raw));qa['same_frame_PNG_RAM_SRAM_state']+=1
  assert all(label in{p['label']for p in captures}for label in DEFAULTS[case['case']])
  groups.append(dict(case=case['case'],title=case['title'],frames=v['frames'],checkpoint_count=v['checkpoint_count'],captures=captures,timeline=timeline,frame_views=views,defaults=DEFAULTS[case['case']],events=events,plan=plan,
   termination=v['termination'],final_fields=v['final_fields'],cold_boot=v['cold_boot'],state_imported=v['state_imported'],mother_state=v['mother_state'],mother_sha256=v['mother_sha256'],preparation=v['preparation'],preparation_groups=v['preparation_groups'],additional_core_memory_writes=v['additional_core_memory_writes'],inherited_context=v['inherited_context'],verified_effects=v['verified_effects'],
   audio=dict(path=relative(wav)+'?sha='+sha(wav),download=relative(wav),seconds=audio['stereo_sample_frames']/48000,**audio),
   links=[link(folder/name,txt)for name,txt in [('validation.json','病例回执'),('repeat-validation.json','整份state双跑'),('input-plan.json','实际双手柄输入'),('frame-services.json','逐帧原字段/hash'),('campaign-events.json','原观察事件'),('preparation.json','准备前后完整dump'),('audio-callbacks.json','实际PCM callbacks')]]))
 summary=e['summary'];assert qa['nonempty_double_run_artifacts']==summary['nonempty_artifacts_double_run_hash_checks']and qa['formal_JSON_exact_parity']==summary['formal_JSON_exact_parity']
 assert qa['same_frame_PNG_RAM_SRAM_state']==summary['checkpoint_count']and qa['excluded_empty_VRAM']==summary['excluded_empty_VRAM']
 return e,groups,dict(qa)

def totals(modules,integration):
 selected=[m for m in modules if m['standalone_counted']]
 if not all(m['status']=='passed'for m in selected)or integration['status']!='passed':return dict(status='pending')
 return dict(status='passed',CPU=sum(m['CPU']for m in selected)+integration['rom_cpu_case_count'],
  completed_boundary=sum(m['complete']for m in selected)+integration['complete_return_count'],actual_caller_RTS=sum(m['complete']for m in selected),
  reset_boundary=sum(m['reset']for m in selected)+integration['reset_boundary_count'],strict_prefix=sum(m['prefix']for m in selected)+integration['strict_prefix_count'],
  guards=sum(m['guards']for m in selected)+integration['source_guard_case_count'])

def template():
 html=BASE_HTML
 replacements={
  '冷启动、复位与合作AI证据':'城市字段边界与真实玩家败亡','阶段十四 · 原冷启动／重启 · 独立合作AI源码':'阶段十七 · 城市字段／满名单 · 原玩家败亡／重开与继续',
  '冷启动与合作调度':'字段边界与玩家败亡','../phase13/index.html':'../phase16/index.html','城市与全局UI':'真实战后继承与字段','四个源码域':'两个主源码域与适配器',
  '三组真实冷启动与合作流程':'三组真实败北、结局退出与候选对照','四个独立源码域与验证范围':'两个主源码域与一个整合适配器',
  '冷起点、原输入／复位操作与结束条件':'原起点／完整数值准备／两只手柄输入与结束条件',
  '三案都直接加载只读原ROM，不导入状态或battery文件，不新增core内存／ready／结果写入。复位只证明同一已加载实例的8KiB SRAM保留；不是断电battery文件重载。标题软件重启是原介绍超时0B58路径，非猜测的重启菜单。':'三案各有11byte战前数值／名册准备，全部前后2048B RAM与8192B SRAM dump公开。单人和曹操名单案继承自然战场准备之前的母档；双人从真正冷启动、标题两人游戏、原第二手柄和出征开始。原普通攻击才写HPFF/status3；没有注入death／result／controller／ready／ack／6F43。',
  '0471:0470仅在原title intro域为计时，其它场景复用这两个地址。':'6F43是开局模式残留，非实时活玩家数；0402仅在实际city13为继承子phase。',
  '观察到的原预算、年月、合作请求与复位事件':'观察到的原败北／君主ID／城市归属／结局退出事件',
  '活跃状态与真实预算／请求变化':'活跃状态、败亡marker与原请求变化','内政phase／预算':'开局模式残留／结局marker',
  "let moduleKey='boot'":"let moduleKey='fields'","module('boot');":"module('fields');"}
 for a,b in replacements.items():html=html.replace(a,b)
 html=html.replace('${p.domestic_phase_6F5B}/${p.domestic_budget_6F5D}','${p.ending_continue_flag_6F43}/${p.ending_animation_marker_04CB}')
 html=html.replace('<div class="metrics" id="metrics"></div><p id="summary"></p>','<div class="metrics" id="metrics"></div><p id="summary"></p><h3>源码验证分类</h3><div class="metrics" id="source-totals"></div><p class="small-note">完成边界、实际caller RTS、E000非局部reset与严格prefix分别列。适配器归组合矩阵，不重复计数。静态位置／事件数不当CPU病例。</p>')
 html=html.replace("const s=D.summary;", "const s=D.summary;")
 html=html.replace("['真实冷boot回放',s.native_case_count]","['正式原核心回放',s.case_count]").replace('s.frames_first_run','s.original_core_frames_first_run').replace('s.frames_both_runs','s.original_core_frames_both_runs').replace('s.nonempty_repeat_artifact_checks','s.nonempty_artifacts_double_run_hash_checks').replace('s.formal_JSON_repeat_checks','s.formal_JSON_exact_parity')
 html=html.replace("$('#case').innerHTML=", "const t=D.source_totals;$('#source-totals').innerHTML=[['原CPU例',t.CPU],['完成边界',t.completed_boundary],['其中实际RTS',t.actual_caller_RTS],['非局部reset边界',t.reset_boundary],['严格prefix',t.strict_prefix],['source guards',t.guards]].map(([k,v])=>`<div class=\"metric\"><small>${k}</small><strong>${fmt(v)}</strong></div>`).join('');$('#case').innerHTML=")
 html=html.replace("$('#case-scope').textContent=`真实只读ROM冷起点 · 无state／battery文件导入 · ${fmt(g.frames)}原帧。${g.termination}`;","$('#case-scope').textContent=`${g.cold_boot?'真正冷启动／无state导入':'公开自然母档一次state import'} · 本案${g.additional_core_memory_writes}byte战前准备／继承准备${g.inherited_context.inherited_preparation_byte_writes}byte · ${fmt(g.frames)}原帧。${g.termination}`;")
 html=html.replace('{cold_boot:true,state_imported:false,battery_file_imported:false,additional_core_memory_writes:0,input_plan:g.plan,termination:g.termination,reset_events:g.reset_events,software_restart_frames:g.software_restart_frames,final_fields:g.final_fields}', '{cold_boot:g.cold_boot,state_imported:g.state_imported,mother:g.mother_state,mother_sha256:g.mother_sha256,inherited_context:g.inherited_context,battery_file_imported:false,additional_core_memory_writes:g.additional_core_memory_writes,preparation:g.preparation,preparation_groups:g.preparation_groups,input_plan:g.plan,verified_effects:g.verified_effects,termination:g.termination,final_fields:g.final_fields}')
 html=html.replace('const l=g.frame_views[a-1],r=g.frame_views[b-1],lc=', 'const unpack=v=>Object.fromEntries(D.frame_keys.map((k,i)=>[k,v[i]]));const l=unpack(g.frame_views[a-1]),r=unpack(g.frame_views[b-1]),lc=')
 html=re.sub(r'const names=\{[\s\S]*?\};\$\(\x27#fields\x27\)',lambda m:'const names='+json.dumps(FIELD_NAMES,ensure_ascii=False,separators=(',',':'))+';$(\x27#fields\x27)',html)
 html=html.replace('<th>完整返回／有界出口</th><th>严格prefix</th>','<th>实际caller RTS</th><th>reset边界</th><th>严格prefix</th>')
 html=html.replace('<td>${fmt(m.complete)}</td><td>${fmt(m.prefix)}</td>','<td>${m.standalone_counted?fmt(m.complete):\'归整合\'}</td><td>${m.standalone_counted?fmt(m.reset):\'归整合\'}</td><td>${m.standalone_counted?fmt(m.prefix):\'归整合\'}</td>')
 html=html.replace('<td>${fmt(m.CPU)}</td>','<td>${m.standalone_counted?fmt(m.CPU):\'归整合\'}</td>').replace('<td>${fmt(m.guards)}</td>','<td>${m.standalone_counted?fmt(m.guards):\'归整合\'}</td>')
 html=html.replace("['完整返回／出口',m.complete]", "['实际caller RTS',m.complete],['非局部reset',m.reset]")
 html=html.replace("['原CPU例',m.CPU]","['原CPU例',m.standalone_counted?m.CPU:'计入整合']").replace("['source guards',m.guards]","['source guards',m.standalone_counted?m.guards:'计入整合']")
 html=html.replace("['实际caller RTS',m.complete],['非局部reset',m.reset]","['实际caller RTS',m.standalone_counted?m.complete:'计入整合'],['非局部reset',m.standalone_counted?m.reset:'计入整合']").replace("['严格prefix',m.prefix]","['严格prefix',m.standalone_counted?m.prefix:'计入整合']")
 html=html.replace("['实际caller RTS',c.actual_caller_return_count],['main E066边界',c.main_boundary_count??c.complete_main_boundary_count]", "['main E066／NMI+IRQ RTI完成',c.complete_return_count]")
 html=re.sub(r'<p class="note">主循环E066边界[\s\S]*?</ol>', '''<p class="note">组合回执声明完整2048B RAM（含idle栈）、8192B SRAM、AXYP／SP／PC、原mapper和端口序；两个原内存序列分别到main E066／NMI+IRQ RTI完成边界和E000非局部E066重启。显式硬件输入用于sourceCPU差分，不称原Native内部指令trace或完整硬件NES帧。</p>
<ol class="steps"><li><strong>城市字段与容量界限</strong><br>城市+1与+2的重叠word比较300；尾28..31官方名称未确认。合法17..26满10槽可以无FF，有界候选不越过名单。A442无界前缀的别名只证明显式边界行为，不证明自然容量绕过。</li><li><strong>真正玩家无候选</strong><br>原BE2E仅owner匹配且首槽非FF，A/B都能确认；HPFF/status3曹操仍能被名单接受。无候选只清leaderFF，失势空城owner仍2。</li><li><strong>结局A-only与原开局模式</strong><br>markerFE新A才退出；单人本案B按2帧、松开观察120帧仍不退出，A真实软件reset、标题及原新剧本重建。双人本案6F43=1由真实开局生成，A清为0并恢复0472/73父流程，随后ruler4经原第二手柄继续；退出代码不另检查其存活或城市。6F43不是实时活玩家数。</li></ol>''',html)
 return html

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--integration-receipt',type=Path,default=OUT/'source-integration.json');p.add_argument('--require-final',action='store_true');p.add_argument('--check-only',action='store_true');a=p.parse_args();a.integration_receipt=a.integration_receipt.resolve()
 e,groups,qa=native_data();integration=integration_data(a.integration_receipt);modules=[module_data(k,integration)for k in MODULES]
 if a.require_final:assert all(m['status']=='passed'for m in modules)and integration['status']=='passed'and(OUT/'README.md').is_file(),'Final current source/integration/report required'
 css=re.search(r'<style>([\s\S]+?)</style>',(ROOT/'analysis/phase14/index.html').read_text()).group(1)
 data=dict(summary=e['summary'],source_totals=totals(modules,integration),core=e['core'],groups=groups,modules=modules,integration=integration,QA=qa,frame_keys=['frame',*FIELDS])
 html=template().replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/'))
 parsed=Parsed();parsed.feed(html);assert len(parsed.ids)==len(set(parsed.ids));links=list(parsed.links)
 for g in groups:
  links.extend(x['href']for x in g['links']);links.append(g['audio']['download'])
  for c in g['captures']:links.extend(c[k]for k in('image','RAM','SRAM','state'))
 for m in modules:links.extend(x['href']for x in m['links']);links.append(m['source_href'])
 if integration['status']!='pending':links.append(integration['path'])
 links.extend(x['href']for x in integration.get('linked_receipts',[]))
 for href in links:
  clean=urlsplit(href).path
  if clean and not clean.startswith('#')and clean!='browser-static-validation.json':assert(OUT/clean).resolve().is_file(),href
 js=re.search(r'<script>([\s\S]+?)</script>',html).group(1)
 with tempfile.NamedTemporaryFile('w',suffix='.js')as f:f.write(js);f.flush();subprocess.run(['node','--check',f.name],check=True,capture_output=True)
 result=dict(schema='phase17-browser-static-v1',status='passed',generator_sha256=sha(Path(__file__)),template_generator_sha256=sha(ROOT/'scripts/build_phase14_browser.py'),
  unique_DOM_ids=len(parsed.ids),local_links_checked=len(links),JS_syntax='passed',native_static_QA=qa,native_evidence_sha256=sha(RUN/'evidence.json'),native_files_modified=False,
  module_count=len(modules),standalone_CPU_domains=2,source_totals=data['source_totals'],modules=[{k:m[k]for k in('key','status','standalone_counted','CPU','complete','reset','prefix','guards','source_sha256','verification_CPU_callbacks','production_CPU_callbacks')}for m in modules],
  integration=dict(status=integration['status'],path=integration['path'],current_pins_match=integration.get('current_pins_match'),completion_kinds=integration['completion_kinds']),field_frames=sum(len(g['frame_views'])for g in groups),final_required=a.require_final,
  browser_visual_acceptance='Root owns CUA; this receipt static only',HTML_created=not a.check_only)
 if a.check_only:
  result['prospective_HTML_sha256']=hashlib.sha256(html.encode()).hexdigest();destination=OUT/'browser-preflight-validation.json'
 else:
  (OUT/'index.html').write_text(html);result['HTML_sha256']=sha(OUT/'index.html');destination=OUT/'browser-static-validation.json'
 destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
