#!/usr/bin/env python3
"""Offline reconstruction of captured software/PPU-command prefixes and seal."""
from pathlib import Path
import argparse,ast,collections,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp07-palette-packet-consumer';RUN=OUT/'run-01';PREV=ROOT/'analysis/wp03-ee07-phase1-producer'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def pins():
 a=read(OUT/'acceptance.json')
 for n,k in(('family-scope.json','scope_sha256'),('case-matrix.json','matrix_sha256'),('device-contract.json','device_sha256'),('ancestor-memory.bin','ancestor_sha256')):assert sha(OUT/n)==a[k]
 for n,h in a['implementation_pins'].items():assert sha(ROOT/n)==h,n
 return a
def rebuild_PPU(events,case,fixture,seed):
 raw=bytearray((i*17+11)&255 for i in range(16384));address=case['ppu_address'];latch=case['ppu_latch'];scroll_latch=case['ppu_scroll_latch'];increment=fixture['initial_increment']
 banks=list(seed['banks']);ports={int(k):v for k,v in seed['ports'].items()};ports[0x2000]=fixture['initial_control'];data=[]
 for e in events:
  q=e['address'];v=e['value']
  if e['kind']=='read':assert q==0x2002;latch=scroll_latch=0;continue
  ports[q]=v
  if q in(0xE800,0xF000):banks[{0xE800:1,0xF000:2}[q]]=v&31
  elif q==0x2000:increment=32 if v&4 else 1
  elif q==0x2006:
   address=((v&63)<<8)|(address&255)if latch==0 else(address&0x3F00)|v;latch^=1
  elif q==0x2007:raw[address&0x3FFF]=v;data.append(dict(address=address&0x3FFF,value=v));address=(address+increment)&0x3FFF
  else:raise AssertionError(f'Unexpected locked device port{q:04X}')
 return raw,dict(ppu_address=address,ppu_latch=latch,ppu_scroll_latch=scroll_latch,ppu_increment=increment,banks=banks,port_image={str(k):v for k,v in ports.items()}),data
def audit():
 a=pins();v=read(RUN/'validation.json');scope=read(OUT/'family-scope.json');plan=read(OUT/'case-matrix.json');fixture=read(OUT/'device-contract.json');seed=scope['ancestry']['state'];ancestor=(OUT/'ancestor-memory.bin').read_bytes()
 assert v['status']=='passed_bounded_palette_packet_software_device_contract'and v['case_sha256']==sha(RUN/'parents.jsonl')and v['points_sha256']==sha(RUN/'points.jsonl')
 CPU=(RUN/'CPU-snapshots.bin').read_bytes();Source=(RUN/'Source-snapshots.bin').read_bytes();assert CPU==Source and len(CPU)==1171456
 for n,row in v['buffers'].items():assert sha(RUN/n)==row['sha256']and(RUN/n).stat().st_size==row['bytes']
 parents=[json.loads(l)for l in(RUN/'parents.jsonl').open()];points=[json.loads(l)for l in(RUN/'points.jsonl').open()];assert len(parents)==5 and len(points)==44
 by_parent={row['parent']:row for row in parents};counts=collections.Counter();typed=collections.Counter();sample_evidence=[];pause_evidence=[];pipeline=[]
 for spec,parent in zip(plan['cases'],parents,strict=True):
  assert parent['spec']==spec and parent['parent']==spec['key']and parent['status']=='passed'
  events=parent['CPU_port_events'];sevents=parent['Source_port_events']
  normalize=lambda es:[{k:e.get(k)for k in('kind','address','value','ordinal','before','after')}for e in es]
  assert normalize(events)==normalize(sevents)and len(events)==110
  assert parent['CPU_IO_reads']==parent['Source_IO_reads']and parent['CPU_IO_writes']==parent['Source_IO_writes']
  assert len(parent['CPU_IO_reads'])==2 and len(parent['CPU_IO_writes'])==108 and len(parent['raw_PPU_data_writes'])==96
  assert[(e['original_PC'],e['value'],e['ordinal'])for e in events if e['kind']=='read']==[(s['PC'],s['value'],s['ordinal'])for s in spec['status_plan']]
  assert all(e['original_PC']is None for e in sevents)
  for e in events:
   if e['kind']=='read':
    assert e['after']['ppu_latch']==e['after']['ppu_scroll_latch']==0
    assert e['after']['read_ports']['8194']==e['before']['read_ports']['8194'][1:]
    assert e['after']['status_success_count']==e['before']['status_success_count']+1
  all_trace=[];all_IO=[];normal_writes=[]
  for index,call in enumerate(parent['calls']):
   trace=call['CPU_trace'];assert len(trace)==call['CPU_instructions']and trace[0]['pc']==0xF8B5 and trace[-1]['pc']==(0xE748 if index==0 else 0xA152)
   assert not any(t['pc']==0xF8B8 for t in trace)
   assert[(w['address'],w['value'])for w in call['actual_JSR']['pushes']]==[(0x100,0xF8),(0x1FF,0xB7)]
   assert call['actual_JSR']['after']['registers']['pc']==0xEE53 and call['actual_JSR']['after']['registers']['sp']==0xFE
   assert call['actual_RTS']['frame']==[0xB7,0xF8]and call['actual_RTS']['after']['registers']['pc']==0xF8B8 and call['actual_RTS']['after']['registers']['sp']==0
   cpu_data=call['CPU_data_reads'];source_data=call['source_data_reads'];assert[(e['address'],e['value'])for e in cpu_data]==[(e['address'],e['value'])for e in source_data]
   assert all(e['original_PC']is None and e['Source_method']for e in source_data)
   if index==0:
    assert len(cpu_data)==32 and cpu_data[0]['address']==0x100 and cpu_data[0]['value']==0xF8
    assert[e['address']for e in cpu_data]==list(range(0x100,0x120));counts['palette_reads']+=32
   else:
    assert len(cpu_data)==68 and[e['address']for e in cpu_data]==list(range(0x380,0x3C4))
    for e in cpu_data:typed[e['original_PC']]+=1
    counts['packet_reads']+=68
   for t in trace:
    all_trace.append(t);normal_writes.extend(t['software_writes'])
    assert not(t['IO_reads']and t['IO_writes'])
    all_IO.extend([('read',e['address'],e['value'])for e in t['IO_reads']]+[('write',e['address'],e['value'])for e in t['IO_writes']])
   counts['CPU_instructions']+=len(trace);counts['real_JSR']+=1;counts['real_RTS']+=1
  assert all_IO==[(e['kind'],e['address'],e['value'])for e in events]
  norm=lambda ws:[(w['address'],w['before'],w['value'])for w in ws]
  assert norm(normal_writes)==norm(parent['CPU_software_writes'])==norm(parent['Source_software_writes'])
  assert not any(0x6000<=w['address']<0x8000 for w in normal_writes)
  for change in parent['controlled_reentries']:
   before=change['before'];after=change['after'];assert change['changed_registers']==['pc']and after['registers']['pc']==0xF8B5
   assert all(before['registers'][k]==after['registers'][k]for k in('a','x','y','p','sp'))and before['device']==after['device']
  rebuilt,dev,data=rebuild_PPU(events,spec,fixture,seed)
  assert data==parent['raw_PPU_data_writes']
  live=bytearray(ancestor[0x100:0x120]);live[0]=0xF8
  assert data[:32]==[dict(address=0x3F00+i,value=value)for i,value in enumerate(live)]
  assert data[32:]==[dict(address=0x2400+i,value=value)for i,value in enumerate(ancestor[0x383:0x3C3])]
  for k,value in dev.items():assert parent['final']['device'][k]==value,(parent['parent'],k)
  assert parent['final']['device']['banks']==[16,29,30,31]and dev['ppu_address']==0x2440
  assert len(parent['missing'])==(spec['initial_available']<2)
  if parent['missing']:
   m=parent['missing'][0];expected=0xE716 if spec['initial_available']==0 else 0xA12D
   assert m['PC']==expected and m['flags']==([0x3A,5]if expected==0xE716 else[0,1])
   assert m['same_owner_call_generator_and_position']and m['no_duplicate_IO_or_software_writes']and m['CPU_preinstruction_gate_no_PC_repair']
   affected=parent['calls'][0 if expected==0xE716 else 1]['advances'];assert [x['Source']['status']for x in affected]==['dependency','dependency','returned']
   assert affected[0]['CPU']['instructions']==affected[1]['CPU']['instructions']<affected[2]['CPU']['instructions']
   pause_evidence.append(dict(parent=parent['parent'],missing=m,advances=affected,replenishments=parent['replenishments']))
   counts['missing_boundaries']+=1;counts['zero_progress_retries']+=1
  callback=parent['Source_callbacks'];assert all(c['target']==0xA006 and c['source_owner']=='text_cpu_protocol'for c in callback)
  assert callback[-1]['status']=='returned'
  sample_evidence.append(dict(parent=parent['parent'],status_samples=spec['status_plan'],actual_reads=[e for e in events if e['kind']=='read'],last_state=parent['final']))
  pipeline.append(dict(parent=parent['parent'],first_return=parent['calls'][0]['final'],second_return=parent['calls'][1]['final'],raw_data_writes=96,actual_JSRs=2,actual_RTS=2))
  counts['port_events']+=len(events);counts['status_reads']+=2;counts['palette_writes']+=32;counts['packet_writes']+=64
 for i,p in enumerate(points):
  assert p['offset']==i*26624 and p['bytes']==26624 and p['Source']==p['CPU']
  segment=CPU[p['offset']:p['offset']+26624];assert hashlib.sha256(segment).hexdigest()==p['CPU_sha256']==p['Source_sha256']
  parent_name=next(spec['key']for spec in plan['cases']if p['label'].startswith(spec['key']+'/'));parent=by_parent[parent_name];spec=parent['spec'];h=p['CPU']['history_counts']
  software=bytearray(ancestor)
  for w in parent['CPU_software_writes'][:h['software_writes']]:
   q=w['address'];pos=q&2047 if q<8192 else q-0x6000+2048;assert software[pos]==w['before'];software[pos]=w['value']
  events=parent['CPU_port_events'][:h['IO_reads']+h['IO_writes']];ppu,dev,data=rebuild_PPU(events,spec,fixture,seed)
  assert segment==bytes(software)+bytes(ppu)
  for k,value in dev.items():assert p['CPU']['device'][k]==value,(p['label'],k)
  assert h['PPU_data_writes']==len(data)and p['CPU']['device']['status_success_count']==h['IO_reads']
  if p['label'].endswith('fixture-initial'):assert segment[:10240]==ancestor
  if 'zero-progress-retry'in p['label']:
   prior=points[i-1];assert prior['Source']==p['Source']and CPU[prior['offset']:prior['offset']+26624]==segment
  if 'packet-tail-A006-entry'in p['label']:assert p['CPU']['registers']['pc']==0xA006 and p['CPU']['device']['banks']==[16,29,30,31]
 assert counts==dict(palette_reads=160,packet_reads=340,CPU_instructions=2630,real_JSR=10,real_RTS=10,port_events=550,status_reads=10,palette_writes=160,packet_writes=320,missing_boundaries=2,zero_progress_retries=2)
 assert typed=={0xA132:10,0xA13A:5,0xA140:5,0xA146:320}
 for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json'):
  assert not(OUT/n).exists();shutil.copyfile(PREV/n,OUT/n);assert(OUT/n).read_bytes()==(PREV/n).read_bytes()
 save('ledger-preservation.json',dict(files=[dict(previous=rec(PREV/n),current=rec(OUT/n),byte_identical=True)for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json')],
  unchanged_field_objects=1526,unchanged_remaining=323,unchanged_raw_objects=345,field_changes=0,raw_changes=0,official_city_names={str(x):None for x in(1,28,29,30,31)}))
 save('actual-data-consumer-relations.json',dict(packet_typed_points=[dict(**row,actual_reads=typed[int(row['id'].split(':cpu')[1][:4],16)],new_classification_credit=False)for row in scope['packet_typed_accesses']],
  actual_packet_reads=340,palette_absolute_Y_reads=160,palette_is_not_new_indirect_candidate=True,
  raw136_139_inherited_read_credit=False,raw_source='This packet is frozen first8800..883F payload now read fromRAM0383..03C2. No new BCBF read or old16packet coverage credit.',
  class_migrations=0,remaining323_unchanged=True,shared_semantic_root=None))
 save('strict-input-recovery-evidence.json',dict(parent_cases=pause_evidence,missing_boundaries=2,zero_progress_retries=2,
  Source_same_owner_call_generator_positions_asserted=True,CPU_gates_before_instruction=True,host_PC_SP_repairs=0,
  inputs_only_appended_from_prelocked_plans=True,actual_game_executions_in_this_audit=0))
 save('status-and-command-evidence.json',dict(parents=sample_evidence,all_port_events_interleaved_equal=True,port_event_count=550,
  status_reads=10,sample_values_do_not_gate_this_path=True,polling=False,vblank_ack_proven=False,raw14bit_sink_only=True,
  physical_PPU_mirroring_status_clear_timing_or_rendering_proven=False))
 save('work-package-delta.json',dict(WP07=dict(new_bounded_contract='Frozen firstphase1 queue -> actualF8B5 palette-priority call -> explicitE716 sample/latchreset ->32 rawpalette commands -> realreturn -> secondactualcall ->clearbit2/F237 -> explicitA12D sample ->64 rawpacket commands ->tailRTS',
  device_input_missing_resume_closed_for_selected_plan=True,software_command_sink_consumer_closed=True,known_new_algorithms=0,
  unclosed=['Internal vblank/statusclear/openbus/clock/NMI edges','CIRAM/CHR/palette physical mirroring or6bit masks','Native PPU internal state and natural scheduler entry']),
  WP08=dict(new_reusable_fragment='phase1 step01 filefixture to two controlled realcall returns with full RAM/SRAM/PPUsink state',full_campaign_or_NMI_continuity_closed=False,
   remaining=['True NMI/IRQ/main continuation and its real incoming frame','Actual PPU/hardware capture replacing the declared fixture','Residual7E bit0 service and subsequent F206/FB0B outside this scope']),
  unknown_unique_services=None,field_changes=0,raw_changes=0,completion_percentage=None,remaining_rounds_estimate=None))
 save('semantic-validation.json',dict(status='passed_offline_full_prefix_and_device_command_audit',parents=5,paired_points=44,bytes_per_point=26624,
  **dict(counts),Source_port_IO_before_after_and_order_verified=True,all_snapshot_memory_PPUsink_prefixes_independently_rebuilt=True,
  original_CPU_Source_Native_executions_in_this_audit=0,new_Native_runs=0,field_changes=0,raw_changes=0,remaining=323,
  physical_PPU_correctness_proven=False,full_WP07_or_WP08_closed=False))
 docs()
 print(json.dumps(dict(status='passed_offline_audit',parents=5,points=44,CPU_instructions=2630,interleaved_port_events=550,Source_CPU_Native_executions=0)))

def docs():
 text='''# WP07：调色板优先处理 → 首个64B包消费

本包从phase1主序列step-01的实际后态出发，完成两次真实 `31:F8B5 JSR EE53`：先输出32字节调色板，再输出64字节packet，分别由E748/A152真RTS回固定31:F8B8首指令之前。5个受控父案例、10次实际调用通过独立可读Source/原ROM CPU对照，共2630条原CPU指令；两处缺输入各一次零进展重试及真实恢复也通过。

## 来源与真实调用

祖先只取前包CPU/Source双方相同的offset0、10240字节，SHA256 `28c408c54d3228dc2c3ab0e5a8a417f06deae0b6b34da01db6aa2a602bf27e0a`。它是首包后态：007D=3A、007E=05、源8840、目的2440、phase1；REG A074/A3B/X00/Y3B/P30/SP00，PRG[16,27,28,31]。没有取step16，也没有倒填后15个已覆盖包上传的信用。

每次仅将PC受控转至实际callsite F8B5；第二次从真实返回F8B8再次转至F8B5，其余寄存器、SP、RAM和银行由程序保留。callsite原字节2053EE，真实JSR压F8B7；Source复用已有BattleNMIServices.call，既有SceneCoordinator把A006尾调用交给TextSceneServices。没有hostpush、seed返回帧或Source CPU/IR回调，也未执行NMI入口、硬件中断frame或F8B8的下一条F206调用。

SP00使本次真实JSR先写0100=F8、01FF=B7，所以palette首字节实际是F8，祖先的A0已被真实建帧替换。上传期望取建帧后的live0100..011F。这是受控栈别名事实，不是自然palette画面验收。

| 调用 | 实际路径与结果 |
|---|---|
| 第一次 | 7D3A→EE56/EE72→E70E；E713写2000，E716读一次2002；E71B真实清7D；写32个2007 palette值；E748 RTS→F8B8。7E仍05，代码页仍27/28。 |
| 第二次 | 7D0/7E05→EEC3真实清bit2为01；EEC8/F237选29/30→EECB尾跳A006/A11B；A12D第二次读2002；地址2400写64B；FF结束；A152直接消费同一个F8B7 frame→F8B8。 |

第二次最终E1/E2/E3=30/3D/3E、PRG[16,29,30,31]；不是EE07，不恢复旧代码页27/28。007E仍bit0=1，不称全部job清空。phase1已生产的queue字节与城市SRAM均保持。

## 明示的软件设备合同

旧包只保存2K RAM+8K SRAM，没有PPU内部状态。本轮PPU初态另行声明：16K raw sink字节公式、地址、地址/滚动latch、增量和端口影像均为受控fixture，未获得Native或自然时序祖先信用。

完全复用现有ServiceMemory：有限2002样本队列，无repeat或自动填值；成功读会消费样本并重置其ppu_latch/ppu_scroll_latch；2000的bit2控制1/32增量；2006按高低两次写14位地址；2007按原14位地址保存完整原byte并递增。不同样本00、80、40、FF及非零latch初态均已覆盖。这两处LDA2002不轮询、不测试状态位决定ready，样本是外部软件输入而不是vblank完成许可。

该bus没有内部PPUSTATUS/vblank产生或读后清bit7模型、开放总线、CIRAM/CHR或palette物理镜像、palette6bit掩码、周期、NMI边缘或渲染。因此只证明有序软件端口命令和原始地址sink；不能从Source/CPU共用此模型后相等，推导真实PPU正确。F8是原始2007命令值，未当作已渲染颜色。见[预锁设备合同](device-contract.json)。

## 缺样本与恢复

| 边界 | 已发生并保留的前缀 |
|---|---|
| E716缺样本 | 2000已写；7D仍3A、7E05；尚未palette数据输出。 |
| A12D耗尽 | bit2已由真实EEC3清为01，代码页已切29/30，00/01=0380，2000已写；64B数据尚未输出。7E01不代表消费完成。 |

Source停在既有ServiceWait；CPU在缺样本读指令之前gate，不半执行后修复PC。重复无输入续程无内存、REG、设备或IO进展，不重做2000或建帧；同Source owner、pending call、generator链和位置动态断言保持。仅向两侧设备输入deque追加预锁剩余样本后，原对象继续执行并真实返回。成功2002总计10读；两个缺样本位置和两次重试不额外计为成功读。

## 复核与可读源码

5父案均526条原CPU指令。逐侧palette160读、packet340读（含每包3B header/64B payload/FF），500次数据读值与顺序一致；原始2007输出palette160B、packet320B。每父110个交织端口事件（2读+108写），Source/CPU逐事件kind/address/value及设备before/after全部一致，来源标签单独保留：Source使用实际方法/行号和语义PC，original_PC为null；CPU使用实际opcode PC。

44对完整保存点包含2K RAM+8K SRAM+16K raw sink及REG/银行/完整声明设备JSON；双方各1171456字节。保存了初态、受控call起点、真实JSR后callee入口、packet尾入口、每次暂停/零进展重试/恢复/返回。离线从初态和实际软件/端口写前缀逐点重建所有44份内存与raw sink，核对交织事件；离线审计没有重跑游戏。

实际正文仍来自已有 `battle_nmi_services.py` 的pending_ppu/palette_upload/mapper_window以及 `text_scene_services.py` 的packet_consumer_entry/consume_nametable_packets/write_nametable_packet_tiles；新[入口与观察适配器](consumer_adapter.py)只复用这些算法，新增游戏/硬件算法均0，旧生产Source未改。

- [预锁范围](family-scope.json)、[有限矩阵](case-matrix.json)、[验收和112项执行pins](acceptance.json)
- [实际执行回执](run-01/validation.json)、[逐案原指令与Source证据](run-01/parents.jsonl)、[44对保存点](run-01/points.jsonl)
- [离线复核](semantic-validation.json)、[严格恢复证据](strict-input-recovery-evidence.json)、[状态与命令证据](status-and-command-evidence.json)

## 全局范围与剩余前提

 WP07新增闭合的是本首包在有限输入计划和原始地址sink上的生产后态→palette优先→packet消费→真实返回及缺样本恢复合同。WP08获得可复用的有界文件fixture片段；真实NMI/IRQ/main连续调度、原PPU现场/时序、残余bit0和后续F206/FB0B均未纳入，完整WP07/WP08仍未完成。见[工作包增量](work-package-delta.json)。新Native、自然入口、旧outerframe和显示信用均0。

packet A132/A13A/A140/A146是全账本1405..1408原已disjoint的四个typed点，不重复减少323。palette是absolute,Y读，不增加typed间接访问。旧raw136..139的16包覆盖不继承为本次consumer证据，本次消费只读取首包RAM数据。

1526=1203/80/243、remaining323及raw345=104/13/228全对象/字节分类保持；城市+1/+28..31正式名仍null。155个EE07已知caller/跨包2个/外部153的口径不变，153不是全局未知服务数。239489旧路径加phase1的34文件和5脚本，共239528路径前后冻结。无发布、推送或ROM分发。本包完成后停止。
'''
 p=OUT/'README.md';assert not p.exists();p.write_text(text)
 p=OUT/'index.html';assert not p.exists();p.write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Palette → 首包消费</title><style>body{font:17px/1.75 system-ui;max-width:900px;margin:48px auto;padding:0 24px;background:#faf9f6;color:#20252b}a{color:#165f8c}td{padding:10px 18px;border-bottom:1px solid #ccc}table{border-collapse:collapse}</style><h1>调色板优先 → 首个64字节包消费</h1><p>5父案例、10次真实JSR调用、2630条原CPU指令通过可读Source对照；两处缺样本严格暂停及原对象续程通过。</p><table><tr><td>Palette / packet原始输出</td><td>逐侧160 / 320字节</td></tr><tr><td>交织端口事件</td><td>550个，双方内容及前后态相同</td></tr><tr><td>完整保存点</td><td>44对2K+8K+16K及设备JSON</td></tr><tr><td>最终代码页 / 剩余job</td><td>29/30；7E bit0仍1</td></tr><tr><td>Native / NMI / 物理PPU证明</td><td>0 / 0 / 无</td></tr></table><p>设备是显式样本与原始14位写入sink；没有vblank、镜像、周期或渲染模型。正式城市字段名仍null，remaining323不变。</p><p><a href="README.md">完整报告与源码来源</a> · <a href="run-01/validation.json">运行结果</a> · <a href="semantic-validation.json">离线复核</a> · <a href="device-contract.json">设备边界</a> · <a href="verification.json">最终封存</a></p></html>''')

def seal():
 a=pins();v=read(RUN/'validation.json');s=read(OUT/'semantic-validation.json');before=read(OUT/'frozen-before.json');after=read(OUT/'frozen-after.json')
 assert v['status']=='passed_bounded_palette_packet_software_device_contract'and s['status']=='passed_offline_full_prefix_and_device_command_audit'
 assert before['status']==after['status']=='passed'and before['old_work_paths']==after['old_work_paths']==239528 and before['frozen_manifest_sha256']==after['frozen_manifest_sha256']
 continuation=read(OUT/'continuation-preconditions.json');assert len(continuation['actual_first_returns'])==5 and not continuation['actual_continuation_executed']
 for p in(ROOT/'scripts').glob('*wp07_palette_packet*.py'):ast.parse(p.read_text())
 save('input-manifest.json',dict(current_producers=[rec(p)for p in sorted((ROOT/'scripts').glob('*wp07_palette_packet*.py'))],actual_execution=rec(RUN/'execution-inputs.json'),
  adapter=rec(OUT/'consumer_adapter.py'),executed_implementation_pins=a['implementation_pins'],frozen_work=rec(OUT/'frozen-work-inputs.json'),ancestor=rec(OUT/'ancestor-memory.bin'),
  previous_verification=rec(PREV/'verification.json'),original_core=rec(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'),ROM_SHA256=read(OUT/'family-scope.json')['ROM_SHA256'],ROM_distributed=False))
 files={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(OUT.rglob('*'))if p.is_file()}
 save('artifact-manifest.json',dict(files=files,excludes=['artifact-manifest.json','verification.json']))
 save('verification.json',dict(schema='WP07-palette-packet-final-verification-v1',status='passed_bounded_software_device_production_to_consumption',parents=5,real_JSR_calls=10,original_CPU_instructions=2630,
  Source_advances=14,missing_boundaries=2,zero_progress_retries=2,real_RTS_returns=10,full_return_not_prefix=True,
  paired_points=44,bytes_per_snapshot=26624,Source_CPU_file_bytes_each=1171456,palette_bytes_each_side=160,packet_bytes_each_side=320,
  data_reads_each_side=500,successful_status_reads_each_side=10,interleaved_port_events_each_side=550,
  all_memory_and_raw_PPUsink_prefixes_independently_rebuilt=True,Source_CPU_port_event_device_before_after_equal=True,
  explicit_status_sample_plan=True,status_polling=False,internal_vblank_or_readclear_modeled=False,physical_mirroring_rendering_timing_proven=False,
  final_7D_7E=[0,1],final_E1_E2_E3=[0x30,0x3D,0x3E],final_PRG=[16,29,30,31],final_return_PC=0xF8B8,
  new_Native_runs=0,NMI_IRQ_entries=0,old_outer_frame_credit=0,natural_entry_credit=0,new_algorithms=0,production_Source_changes=0,Source_CPU_IR_callbacks=0,
  preserved_work_paths=239528,old_missing_or_changed=0,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),
  artifact_manifest_sha256=sha(OUT/'artifact-manifest.json'),artifact_manifest_entries=len(files),
  field_counts=dict(total=1526,conditional=1203,possible=80,unknown=243,remaining=323),raw_counts=dict(total=345,operand=104,data=13,unproved=228),field_migrations=0,raw_migrations=0,
  official_city_names={str(x):None for x in(1,28,29,30,31)},global_unknown_services=None,completion_percentage=None,remaining_rounds_estimate=None,
  full_WP07_or_WP08_closed=False,whole_game_closed=False,stopped_after_package=True))
 print(json.dumps(dict(status='sealed',verification_sha256=sha(OUT/'verification.json'),manifest_entries=len(files),preserved_paths=239528)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','seal'));a=p.parse_args();audit()if a.mode=='audit'else seal()
