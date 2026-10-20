#!/usr/bin/env python3
"""Offline phase1 source/CPU buffer and trace audit; immutable final seal."""
from pathlib import Path
import argparse,ast,collections,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-ee07-phase1-producer';RUN=OUT/'run-01';OLD=ROOT/'analysis/wp03-ee07-return-family'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def save(n,x):
 p=OUT/n;assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def check_pins():
 a=read(OUT/'acceptance.json')
 for n,k in(('family-scope.json','scope_sha256'),('case-matrix.json','matrix_sha256'),('device-contract-boundary.json','device_boundary_sha256'),('ancestor-memory.bin','ancestor_sha256')):assert sha(OUT/n)==a[k]
 for n,h in a['implementation_pins'].items():assert sha(ROOT/n)==h,n
 return a
def audit():
 a=check_pins();v=read(RUN/'validation.json');plan=read(OUT/'case-matrix.json');scope=read(OUT/'family-scope.json')
 assert v['status']=='passed_full_phase1_producer_family'and v['cases_sha256']==sha(RUN/'cases.jsonl')and v['acceptance_sha256']==sha(OUT/'acceptance.json')
 streams={}
 for name,row in v['buffers'].items():
  p=RUN/name;assert sha(p)==row['sha256']and p.stat().st_size==row['bytes']==256000;streams[name[:-11]]=p.read_bytes()
 for stage in('forward','data-mapped','callee-return','final'):assert streams['CPU-'+stage]==streams['Source-'+stage]
 rows=[json.loads(line)for line in(RUN/'cases.jsonl').open()];assert len(rows)==25
 expected_keys=[(case,step)for case in plan['cases']for step in range(case['steps'])];assert len(expected_keys)==25
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==scope['ROM_SHA256']
 banks=collections.Counter();counts=collections.Counter();case_positions={};sources=set();phase_examples=[];chain=[];prior_final={}
 for i,(row,(case,step))in enumerate(zip(rows,expected_keys,strict=True)):
  assert row['parent']==case['key']and row['step']==step and row['spec']==case and row['status']=='passed'
  offset=i*10240;assert row['snapshot_offset']==offset
  local={name:raw[offset:offset+10240]for name,raw in streams.items()}
  for name,b in local.items():assert hashlib.sha256(b).hexdigest()==row['snapshot_sha256'][name]
  original=bytearray(local['initial']);trace=row['CPU']['trace'];io=[];positions=[]
  assert trace[0]['pc']==0xA06F and trace[-1]['pc']==0xEE52 and len(trace)==row['CPU']['instructions']
  for t in trace:
   positions.append((t['bank'],t['pc']));opcode=rom[16+t['bank']*8192+(t['pc']&8191)]
   if t['pc']in(0xBD02,0xEE52,0xED18):assert opcode==0x60
   assert t['pc']!=0xA074
   for w in t['writes']:
    q=w['address'];p=q&2047 if q<8192 else q-0x6000+2048
    assert original[p]==w['before'];original[p]=w['value']
   io.extend(t['IO_writes'])
  assert bytes(original)==local['CPU-final']==local['Source-final']
  assert io==[dict(address=0xF000,value=0x3E),dict(address=0xE800,value=0xFD),dict(address=0xE000,value=0x30),dict(address=0xF000,value=0x3C),dict(address=0xE800,value=0xFB)]
  assert row['CPU']['real_BD02_RTS']['frame']==[0x4C,0xEE]and row['CPU']['real_BD02_RTS']['after']['registers']['pc']==0xEE4D
  assert row['CPU']['real_EE52_RTS']['frame']==[0x73,0xA0]and row['CPU']['real_EE52_RTS']['after']==row['Source']['final']
  assert row['Source']['final']['registers']['pc']==0xA074 and row['Source']['final']['registers']['sp']==0
  assert row['Source']['final']['banks']==[16,27,28,31]
  assert local['initial'][0x7D]==local['CPU-final'][0x7D]==0x3A
  assert local['CPU-final'][0xE1]==0x30 and local['CPU-final'][0x8A]==local['initial'][0x8A]
  assert not any(w['address']in(0x7D,0x8A)for t in trace for w in t['writes'])
  assert local['initial'][2048:]==local['CPU-final'][2048:]
  re=row['controlled_reentry'];assert re['RAM_unchanged_by_reentry']and re['changed_registers']==['pc','y']
  before=re['before']['Source'];after=re['after'];assert before==re['before']['CPU']
  assert before['registers']['pc']==0xA074 and before['registers']['y']==0x3B and after['registers']['pc']==0xA06F and after['registers']['y']==0x3D
  assert all(before['registers'][k]==after['registers'][k]for k in('a','x','p','sp'))
  assert all(before[k]==after[k]for k in('banks','ports','RAM_sha256','SRAM_sha256'))
  if step:assert local['initial']==prior_final[case['key']]
  else:
   expected=bytearray((OUT/'ancestor-memory.bin').read_bytes())
   for addr,value in case['patches'].items():expected[int(addr)]=value
   assert bytes(expected)==local['initial']
  prior_final[case['key']]=local['CPU-final']
  CPU_events=row['CPU_packet_events'];Source_events=row['Source']['packet_events']
  norm=lambda events:[(x['kind'],x['address'],x['value'],x['Y'])for x in events]
  assert norm(CPU_events)==norm(Source_events)and len(CPU_events)==132
  data=[x for x in CPU_events if x['kind']=='payload_read'];assert len(data)==64 and[x['Y']for x in data]==list(range(64))
  src=row['initial_source'];dst=row['initial_destination'];sources.add(src)
  assert[x['address']for x in data]==[(src+y)&65535 for y in range(64)]
  for read_event in data:
   ea=read_event['address'];bank=[16,29,30,31][(ea-0x8000)//8192]
   assert read_event['bank']==bank and read_event['original_PC']==0xBCBF
   assert rom[16+bank*8192+(ea&8191)]==read_event['value'];banks[bank]+=1
  writes=[x for x in CPU_events if x['kind']=='packet_write'];assert len(writes)==68
  assert[(x['address'],x['value'])for x in writes[:3]]==[(0x380,64),(0x381,dst>>8),(0x382,dst&255)]
  assert writes[-1]['address']==0x3C3 and writes[-1]['value']==255 and writes[-1]['Y']==64 and writes[-1]['original_PC']==0xBCCB
  for y in range(64):
   assert CPU_events[3+2*y]['kind']=='payload_read'and CPU_events[4+2*y]['kind']=='packet_write'
   assert CPU_events[4+2*y]['address']==0x383+y
  if row['phase_advanced']:
   assert(29,0xBCF4)in positions and(29,0xBCF7)in positions and(31,0xED18)in positions
   assert row['CPU_palette']==row['Source']['palette']and set(row['CPU_palette'])=={'entry','return'}
   pe=row['CPU_palette'];entry_ram=bytes.fromhex(pe['entry']['RAM_hex']);ret_ram=bytes.fromhex(pe['return']['RAM_hex'])
   assert ret_ram[0x120:0x140]==entry_ram[0x100:0x120]and ret_ram[0x87:0x8A]==bytes((1,0,4))
   assert pe['return']['state']['registers']['pc']==0xBCFA
   assert any(c['target']==0xECEE and c['status']=='returned'and c['source_owner']=='shared'for c in row['Source']['callbacks'])
   counts['ECEE_returns']+=1
  else:assert(29,0xBCF4)not in positions and not row['CPU_palette']
  assert local['CPU-final'][0x401]==1+row['phase_advanced']and local['CPU-final'][0x7E]==row['initial_jobs']|4
  if step==0:phase_examples.append(dict(parent=case['key'],source=f'{src:04X}',destination=f'{dst:04X}',phase_advanced=row['phase_advanced'],jobs_before=row['initial_jobs'],jobs_after=local['CPU-final'][0x7E],return_boundary=row['Source']['final']))
  if case['steps']==16:chain.append(dict(key=row['key'],source=src,destination=dst,phase_after=local['CPU-final'][0x401],jobs_after=local['CPU-final'][0x7E],packet_sha256=hashlib.sha256(local['CPU-final'][0x380:0x3C4]).hexdigest()))
  if case['key']=='source_crosses_PRG_slot':assert not any(b==29 and 0xA000<=p<=0xA02F for b,p in positions)
  counts['instructions']+=len(trace);counts['real_callee_RTS']+=1;counts['real_EE52_RTS']+=1;case_positions[row['key']]=positions
 assert banks=={16:1552,29:48}and counts==dict(ECEE_returns=4,instructions=11562,real_callee_RTS=25,real_EE52_RTS=25)
 assert len(chain)==16 and all(x['phase_after']==1 for x in chain[:15])and chain[-1]['phase_after']==2
 assert chain[-1]['source']==0x8BC0 and chain[-1]['destination']==0x27C0 and len(sources)==18
 for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json'):
  assert not(OUT/n).exists();shutil.copyfile(OLD/n,OUT/n);assert(OUT/n).read_bytes()==(OLD/n).read_bytes()
 save('ledger-preservation.json',dict(files=[dict(previous=rec(OLD/n),current=rec(OUT/n),byte_identical=True)for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json')],
  unchanged_full_objects=1526,unchanged_remaining_objects=323,unchanged_raw_objects=345,field_classification_changes=0,raw_classification_changes=0,
  official_city_names={str(x):None for x in(1,28,29,30,31)}))
 save('bounded-access-evidence.json',dict(typed_id=scope['selected_typed_id'],full_locator='/accesses/1474',remaining_locator='/accesses/282',
  locked_source_bases=sorted(sources),actual_reads_per_side=1600,physical_bank_read_counts={str(k):v for k,v in banks.items()},
  address_rule='Each BCBF uses live whole00/01 + Y, Y0..63; F25F maps8000 tophysical16; A000 slot remainsphysical29.',
  ROM_only_for_this_locked_subset=True,all_possible_pointer_inputs_closed=False,classification_change=False,
  raw_inline_window=scope['raw_inline_window'],inline_typed_ids=scope['inline_data_typed_ids'],inline_reads_new_package=50,
  relation='Same A06F entry as the previous phase0 package now reaches BCBF phase1; two inline bytes select A039. 9FF0 cross-window values from29:A000..A02F are data reads only.',
  continuation_A074_executed=False,raw_window_start_opcode_execution_proven=False,shared_semantic_root=None,
  A077_C443_executed=False,new_callers=0,known_callers=155,covered_callers_across_the_two_packages=2,inventory_not_covered=153,global_remaining_services=None))
 save('producer-state-evidence.json',dict(first_case=row_summary(rows[0]),controlled_chain=chain,branch_examples=phase_examples,
  semantics='No busy/ready guard; header+64payload+FF terminator replaces queue; OR4 requests upload; post-add destination high28 advances phase and synchronously initializes ECEE.',
  no_cross_package_live_process_claim=True,ancestor_is_frozen_external_fixture=True,producer_chain_same_engine_and_bus_within_parent=True,
  consumer_executed=False,natural_scheduling=False,phase_advance_not_proof_of_PPU_completion=True))
 save('work-package-delta.json',dict(WP03=dict(newly_closed_bounded_edge='A06F/A039 phase1 actual64B producer including F25F side effect, real ECEE terminal branch, BD02/EE52 complete return',
  previous_gap='Phase0 return/busy branch verified; BCBF payload production and E1 retention across far return not dynamically verified for this family',
  new_algorithms=0,new_callers=0,global_shared_service_closure=False),
  G_ACCESS_CONTRACTS=dict(typed_id=scope['selected_typed_id'],new_subset_reads=1600,global_row_migration=False,remaining323_unchanged=True),
  WP07=dict(new_unknown_algorithms=0,minimum_device_contract=rec(OUT/'device-contract-boundary.json'),consumer_schedule_and_hardware_pending=True),WP08=dict(full_campaign_closure=False),
  official_city_names={str(x):None for x in(1,28,29,30,31)},completion_percentage=None,remaining_rounds_estimate=None))
 save('semantic-validation.json',dict(status='passed_offline_phase1_buffer_trace_audit',parent_cases=10,producer_calls=25,**dict(counts),actual_payload_reads_each_side=1600,
  physical_reads={str(k):v for k,v in banks.items()},both_sides_saved_stages=4,bytes_per_snapshot=10240,original_CPU_or_Source_executions_in_this_audit=0,
  Native_new_runs=0,consumer_executions=0,outer_RTS_executions=0,real_return_not_prefix=True,global_field_migrations=0,raw_migrations=0,remaining=323))
 docs()
 print(json.dumps(dict(status='passed_offline_audit',parents=10,producer_calls=25,CPU_instructions=11562,bank_reads=dict(banks),Source_CPU_Native_executions=0)))

def row_summary(row):return dict(key=row['key'],initial_source=row['initial_source'],initial_destination=row['initial_destination'],final=row['Source']['final'],snapshot_offset=row['snapshot_offset'])
def docs():
 text='''# Phase 1：64字节数据包生产与真实返回

本轮闭合 `A06F →29:A039 →BC74 phase1 →BC9B..BD02` 的实际64B生产与返回链。10个受控父案例、25次生产调用均通过独立可读Source/原ROM CPU对照，共11,562条原CPU指令。全部真实执行BD02 RTS，再经EE4D恢复代码页、EE52 RTS到A074首条指令之前。没有新增游戏算法或重复实现已有正文。

## 实际流程

| 步骤 | 原逻辑与验证结果 |
|---|---|
| BC9D/F25F | Y=30，raw E1=30、物理8000数据页16 |
| BCA2/BCA8/BCAE | 0380..0382 写入40、原目的高字节、原目的低字节 |
| BCBF/BCC1 | 按Y=0..63逐字节交错读源、写0383..03C2 |
| BCCB | Y=40时在03C3写FF终止符；64B生产不因payload字节值提前结束 |
| BCD1..BCEC | 源和目的分别独立CLC、加0040，保留页进位 |
| BCF0/BCF4/BCF7 | 更新后目的高字节等于28便推进0401并真实调用ECEE；不要求完整地址等于2800 |
| BCFF | 无条件007E |=04，表示请求；没有producer busy/ready guard |
| BD02/EE4D/EE52 | 真返回并恢复代码页27/28，保留E1=30和数据页16副作用 |

祖先来自上一包 `all_SP_values/0000` 已冻结的两侧相同phase0后态：PC=A074、A=3B、X=00、Y=3B、P=30、SP=00；PRG=[17,27,28,31]；007D=3A、007E=1、0401=1、0470..73=00 88 00 24。每次只显式把PC重入A06F、Y改3D；独立边界例另有预锁RAM补丁。跨包输入是文件fixture，未声称跨包同一活进程或自然场景连续。

首包实际结果：header=`40 24 00`、64B来自8800..883F、03C3=FF，源推进8840、目的推进2440、phase仍1、007E=05。25次各执行64读/64写，共双方各1600次payload读取与1600次payload写入；1552读来自物理16，48读来自物理29。9FF0跨窗例的A000..A02F仅作为数据被读取，没有opcode执行信用。

同一父案例内，Source和CPU各保留自己的engine/bus，受控重入16次：前15次phase1，末次目的27C0→2800后phase2，源最终8C00。这16次会覆盖同一个待上传包，不能称1024B已经上传、真实ready或自然NMI调度。其他边界覆盖007E=0/4、源单独进位、目的单独进位、27D0→2810仍推进、28BF→28FF仍推进及28C0→2900不推进。

4次ECEE均调用既有精确Source owner并由ED18真返回：87=1、88=0、89=4，将调用当时0100..011F复制至0120..013F；不写7D/8A、不等待淡出结束。SP00继承的活动帧为0100与01FF..01FA，与备份区不交。SP20..45的栈别名危险范围未纳入正例，不宣称任意SP都能返回。初始外层栈字节仍是受控fixture；本轮只证当前真实JSR/farframe，不构造或消费outer RTS。

## 源码与复核

本轮直接使用既有 `source/recovered/global_ui_controller.py` 的 `CityUIWorkers.cityuiworkers_bc74_phase_1`，通过真实 `SceneCoordinator →GlobalUIController.city_workers` 路由；`F25F`、`ECEE`由既有共享Source服务执行。冻结上一包的 `readable_entry.current_jsr` 只接入当前调用，Source先独立运行，未接收CPU输出或CPU/IR回调。生产源码无需重写，新增测试仅验证此有界数据流。

每次保存初态及forward、F25F后、callee真返回后、EE52真返回后的完整2K RAM+8K SRAM，后四阶段双方分别保存。逐案记录完整REG/PRG/raw ports、原CPU指令和栈写、两侧真实payload读写顺序与Source方法/行号。ECEE还分别保存两侧实际进入/返回的完整RAM/SRAM。离线复核从初态重放日志写入、逐字节比较双方buffer，不重跑游戏代码。

- [预锁范围与原字节](family-scope.json)、[矩阵](case-matrix.json)、[预锁验收及实现哈希](acceptance.json)
- [实际执行](run-01/validation.json)、[逐案证据](run-01/cases.jsonl)、[离线验证](semantic-validation.json)
- [生产与阶段证据](producer-state-evidence.json)、[BCBF访问关系](bounded-access-evidence.json)、[全局工作包增量](work-package-delta.json)

## 尚未覆盖的消费边界

007D=3A始终保留，来自旧fixture公式而非Native/PPU ack。phase1本身没有busy判断；后续EE53会优先走palette。实际消费需要单独预锁调度、2002读值/时序及2000/2006/2007写入合同。已有精确TextSceneServices A006/A11B算法，本包没有因此发现未知WP07算法；缺的是仍待验证的设备与调度合同。见[最小设备合同](device-contract-boundary.json)。本轮消费、NMI/IRQ、新Native和outer RTS执行均0，未宣称完整WP08或长期战役闭环。

## 固定账本与封存

BCBF保持原canonical ID `b29:cpuBCBF:rom03BCCF`，全账本索引1474、当前remaining索引282。其18个受控源基址和1600次实际读取补充有界证据，不迁移整条访问分类。raw249前两字节仍由EE1F/EE25作为A039 inline地址消费；本包延伸同一A06F的phase1，不增加第三个caller。155个冻结直接EE07 callsite中，跨两包仍纳入2个、其余153未由这些包覆盖；153不是全局未知服务数。

1526=1203 conditional/80 possible/243 unknown、remaining323和raw345=104 operand/13 data/228 unproved全部对象与字节保持。城市+1、+28..31正式名继续null。旧239445路径、上一包39文件及5脚本共239489路径前后冻结；所有旧件保持不变。不发布、不推送、不分发ROM。本包完成后停止。
'''
 p=OUT/'README.md';assert not p.exists();p.write_text(text)
 p=OUT/'index.html';assert not p.exists();p.write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>64B数据包生产与状态推进</title><style>body{font:17px/1.75 system-ui;max-width:880px;margin:48px auto;padding:0 24px;background:#faf9f6;color:#20252b}a{color:#165f8c}td{padding:10px 18px;border-bottom:1px solid #ccc}table{border-collapse:collapse}</style><h1>64字节数据包生产与真实返回</h1><p>10个受控父案例、25次生产调用全部通过可读Source / 原ROM CPU对照。数据包、状态推进、ECEE真实返回及E1数据页副作用均已验证。</p><table><tr><td>原CPU指令</td><td>11,562</td></tr><tr><td>每侧payload读 / 写</td><td>1,600 / 1,600</td></tr><tr><td>真实BD02 / EE52返回</td><td>25 / 25</td></tr><tr><td>ECEE真实返回</td><td>4</td></tr><tr><td>PPU消费 / 新Native</td><td>0 / 0</td></tr><tr><td>全局候选分类迁移</td><td>0；remaining323，正式城市字段名仍null</td></tr></table><p>phase1没有busy/ready检查。连续16次为同实例受控PC/Y重入，保留007D=3A，不代表自然调度或上传完成。</p><p><a href="README.md">完整分析和源码来源</a> · <a href="run-01/validation.json">运行结果</a> · <a href="bounded-access-evidence.json">访问证据</a> · <a href="device-contract-boundary.json">设备边界</a> · <a href="verification.json">最终封存</a></p></html>''')

def seal():
 a=check_pins();v=read(RUN/'validation.json');s=read(OUT/'semantic-validation.json');assert v['status']=='passed_full_phase1_producer_family'and s['status']=='passed_offline_phase1_buffer_trace_audit'
 before=read(OUT/'frozen-before.json');after=read(OUT/'frozen-after.json')
 assert before['status']==after['status']=='passed'and before['old_work_paths']==after['old_work_paths']==239489
 assert before['frozen_manifest_sha256']==after['frozen_manifest_sha256']
 raw=read(OUT/'raw-payload-consumer-evidence.json')
 assert raw['window_count']==4 and raw['window_byte_relations']==12 and raw['unique_ROM_bytes']==10
 assert raw['actual_case_records_sha256']==sha(RUN/'cases.jsonl')and raw['raw_ledger_sha256']==sha(OUT/'raw345-executability-ledger.json')
 for p in(ROOT/'scripts').glob('*wp03_ee07_phase1*.py'):ast.parse(p.read_text())
 save('input-manifest.json',dict(current_producers=[rec(p)for p in sorted((ROOT/'scripts').glob('*wp03_ee07_phase1*.py'))],
  actual_execution=rec(RUN/'execution-inputs.json'),executed_implementation_pins=a['implementation_pins'],prior_verification=rec(OLD/'verification.json'),
  ancestry=rec(OUT/'ancestor-memory.bin'),frozen_work=rec(OUT/'frozen-work-inputs.json'),ROM_SHA256=read(OUT/'family-scope.json')['ROM_SHA256'],
  original_core=rec(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'),ROM_distributed=False,new_Native_runs=0,offline_finalizer_no_Source_CPU_execution=True))
 files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))if p.is_file()}
 save('artifact-manifest.json',dict(files=files,excludes=['artifact-manifest.json','verification.json']))
 save('verification.json',dict(schema='wp03-EE07-phase1-producer-final-v1',status='passed_bounded_phase1_producer_real_return',
  parent_cases=10,Source_CPU_producer_calls=25,original_CPU_instructions=11562,payload_reads_each_side=1600,payload_writes_each_side=1600,
  actual_read_banks={'16':1552,'29':48},real_BD02_RTS=25,real_EE52_RTS=25,real_ECEE_return=4,full_return_not_prefix=True,
  raw_payload_role_windows=4,raw_window_byte_relations=12,raw_unique_ROM_bytes=10,raw_payload_evidence_sha256=sha(OUT/'raw-payload-consumer-evidence.json'),
  both_sides_saved_memory_stages=4,controlled_reentry=True,natural_entry_or_scheduling_proven=False,cross_package_live_process=False,
  constant_007D=0x3A,all_007D_writes=0,E1_30_data_bank16_side_effect_preserved=True,
  consumer_executions=0,NMI_IRQ_executions=0,Native_new_runs=0,outer_RTS_executions=0,new_algorithms=0,production_Source_changes=0,Source_CPU_IR_callbacks=0,
  source_map='SceneCoordinator ->GlobalUIController.city_workers ->CityUIWorkers.cityuiworkers_bc74_phase_1 plus shared F25F/ECEE',
  scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),execution_input_sha256=sha(RUN/'execution-inputs.json'),
  artifact_manifest_sha256=sha(OUT/'artifact-manifest.json'),artifact_manifest_entries=len(files),preserved_work_paths=239489,old_paths_missing_or_changed=0,
  field_counts=dict(total=1526,conditional=1203,possible=80,unknown=243,remaining=323),raw_counts=dict(total=345,operand=104,data=13,unproved=228),
  field_classification_changes=0,raw_classification_changes=0,official_city_names={str(x):None for x in(1,28,29,30,31)},
  known_EE07_callers=155,covered_callers_combined=2,new_callers=0,inventory_not_covered=153,global_remaining_services=None,
  WP03_bounded_gap_closed='phase1 actual64B producer and state transition with real return',WP07_device_consumer_pending=True,full_WP08_closed=False,
  whole_game_closure_proven=False,completion_percentage=None,remaining_rounds_estimate=None,stopped_after_package=True))
 print(json.dumps(dict(status='sealed',verification_sha256=sha(OUT/'verification.json'),manifest_entries=len(files),prior_paths_unchanged=239489)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','seal'));a=p.parse_args();audit()if a.mode=='audit'else seal()
