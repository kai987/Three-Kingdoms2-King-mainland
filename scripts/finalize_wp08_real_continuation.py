#!/usr/bin/env python3
"""Offline prefix/device reconstruction and sealing; no game execution."""
from pathlib import Path
import argparse,ast,collections,copy,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp08-real-continuation';RUN=OUT/'run-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def checkpins():
 a=read(OUT/'acceptance.json')
 for n,h in a['inputs'].items():assert sha(OUT/n)==h,n
 for n,h in a['implementation_pins'].items():assert sha(ROOT/n)==h,n
 return a
def norm(xs):return[{k:v for k,v in e.items()if k not in('original_PC','Source_method','Source_line','Source_semantic_PC')}for e in xs]
def apply_software(b,ws):
 for w in ws:
  q=w['address'];pos=q&2047 if q<8192 else q-0x6000+2048
  assert b[pos]==w['before'];b[pos]=w['value']
def rebuild_device(initial,events,initial_bytes):
 d=copy.deepcopy(initial);b=bytearray(initial_bytes[10240:]);data=[]
 for e in events:
  # Input refill is a separate declared event, not a hardware observation.
  if e['before']!=d:
   before=copy.deepcopy(e['before']);q=d['read_ports']['8194'];new=before['read_ports']['8194'];before['read_ports']['8194']=q
   assert before==d and q==[]and new==[128]
   d['read_ports']['8194']=new
  assert e['before']==d
  address=e['address'];v=e['value']
  if e['kind']=='read':
   assert address==0x2002 and d['read_ports']['8194'].pop(0)==v;d['status_success_count']+=1;d['ppu_latch']=d['ppu_scroll_latch']=0
  else:
   d['port_image'][str(address)]=v;reg=address&0xF800
   if reg in(0xE000,0xE800,0xF000):d['banks'][{0xE000:0,0xE800:1,0xF000:2}[reg]]=(v&63)%32
   elif 0x8000<=reg<0xE000:d['CHR_selectors'][str(reg)]=v
   if address==0x2000:d['ppu_increment']=32 if v&4 else 1
   elif address==0x2005:
    d['ppu_scroll'][d['ppu_latch']]=v;d['ppu_latch']^=1;d['ppu_scroll_latch']=d['ppu_latch']
   elif address==0x2006:
    if not d['ppu_latch']:d['ppu_address']=(v&63)<<8|(d['ppu_address']&255)
    else:d['ppu_address']=(d['ppu_address']&0x3F00)|v
    d['ppu_latch']^=1
   elif address==0x2007:
    p=d['ppu_address']&0x3FFF;b[p]=v;data.append(dict(address=p,value=v));d['ppu_address']=(p+d['ppu_increment'])&0x3FFF
   elif address==0x4014:
    assert v==2;d['DMA_requests'].append(dict(page=v,OAMADDR=d['port_image'].get('8195',0),bytes_hex=initial_bytes[512:768].hex()))
  assert e['after']==d,(address,e['after'],d)
 return d,bytes(b),data
def audit():
 a=checkpins();v=read(RUN/'validation.json');assert v['status']=='passed_bounded_real_continuation_contract'
 assert sha(RUN/'parents.jsonl')==v['parents_sha256']and sha(RUN/'points.jsonl')==v['points_sha256']
 for n,r in v['buffers'].items():assert(RUN/n).stat().st_size==r['bytes']and sha(RUN/n)==r['sha256']
 rows=[json.loads(s)for s in(RUN/'parents.jsonl').read_text().splitlines()];points=[json.loads(s)for s in(RUN/'points.jsonl').read_text().splitlines()]
 assert[r['spec']for r in rows]==read(OUT/'case-matrix.json')['cases']and[r['parent']for r in rows]==[r['spec']['key']for r in rows]
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==read(OUT/'family-scope.json')['ROM_SHA256']
 cp=(RUN/'CPU-snapshots.bin').read_bytes();sp=(RUN/'Source-snapshots.bin').read_bytes();assert cp==sp and len(cp)==len(points)*26624
 by={r['parent']:r for r in rows};initials={r['parent']:next(p for p in points if p['label']==r['parent']+'/imported-complete-state')for r in rows}
 stats=collections.Counter();routes=[]
 for row in rows:
  spec=row['spec'];calls=row['CPU_calls'];trace=row['CPU_trace'];assert len(calls)==spec['expected_call_count']
  route=[(0xF8B5,0xEE53),(0xF8B8,0xF206),(0xF8BB,0xFB0B),(0xFB0B,0xEAF7),(0xF8BE,0xEC67)]
  assert[(c['caller_pc'],c['target'])for c in calls]==(route if spec['software_NMI_entry']else route[1:])
  assert norm(row['CPU_port_events'])==norm(row['Source_port_events']);assert norm(row['CPU_software_writes'])==norm(row['Source_software_writes'])
  assert all(e['original_PC']is None for e in row['Source_port_events']+row['Source_software_writes'])
  ti=0;events=[];writes=[];stack=[];returned=[]
  for t in trace:
   assert t['pc']==t['before']['pc']and t['banks_before'][3]==31
   off=16+t['bank']*8192+(t['pc']&8191);assert rom[off]==t['opcode']
   if t['opcode']==0x20:
    call=calls[ti];ti+=1;assert t['pc']==call['caller_pc']and t['after']==call['entry']['point']['registers']
    assert t['after']['sp']==(t['before']['sp']-2)&255 and t['after']['pc']==call['target']
    w=t['software_writes'];assert[(x['address'],x['value'])for x in w]==[(0x100+t['before']['sp'],(t['pc']+2)>>8),(0x100+((t['before']['sp']-1)&255),(t['pc']+2)&255)]
    stack.append(call)
   if t['opcode']==0x60:
    c=stack.pop();assert t['pc']==c['RTS_PC']and t['after']==c['after']['point']['registers']
    dest=(c['actual_frame'][0]|c['actual_frame'][1]<<8)+1;assert t['after']['pc']==dest and t['after']['sp']==c['expected_sp'];returned.append(c)
   if t['pc']==0xFB22:
    e=t['port_events'];assert len(e)==1 and e[0]['kind']=='read';value=e[0]['value'];before=t['before'];after=t['after']
    assert before['a']==after['a']and after['p']&0xC2==((value&0xC0)|(2 if not(before['a']&value)else 0))
   if t['pc']==0xFB25:
    assert t['opcode']==0x70 and t['after']['pc']==(0xFB22 if t['before']['p']&64 else 0xFB27)and not t['port_events']and t['before']['p']==t['after']['p']
   writes.extend(t['software_writes']);events.extend(t['port_events'])
  assert not stack and ti==len(calls)
  # MPU.nmi is a separately declared event, not an opcode or JSR.
  n=6 if spec['software_NMI_entry']else 0
  assert norm(writes)==norm(row['CPU_software_writes'][3 if n else 0:])
  assert norm(events)==norm(row['CPU_port_events'])
  first=initials[row['parent']];b=cp[first['offset']:first['offset']+26624]
  if spec['software_NMI_entry']:
   assert b[:10240]==(OUT/'native122-software-memory.bin').read_bytes()
   frame=next(p for p in points if p['label']==row['parent']+'/derived-actual-interrupt-frame');fr=frame['CPU']['registers'];assert fr['pc']==0xF800 and fr['sp']==0xFC
   fb=cp[frame['offset']:frame['offset']+26624];assert fb[0x1FD:0x200]==bytes((0xE4,0x66,0xE0))
   dispatch=next(p for p in points if p['label']==row['parent']+'/actual-F878-dispatch');db=cp[dispatch['offset']:dispatch['offset']+26624];assert dispatch['CPU']['registers']['sp']==0xF9 and db[0x1FA:0x200]==bytes((0,0,0x90,0xE4,0x66,0xE0))
   assert row['final']['registers']['pc']==0xF8C1 and row['final']['registers']['sp']==0xF9 and len(row['final']['device']['DMA_requests'])==1
  else:
   assert b==(OUT/'controlled-SP00-memory-and-raw-sink.bin').read_bytes()
   last=calls[-1];assert last['caller_pc']==0xF8BE and last['target']==0xEC67 and last['actual_frame']==[0xC0,0x0F]
   assert last['entry']['point']['registers']['sp']==0xFE and last['after']['point']['registers']['pc']==0x0FC1 and not last['returned_to_original_caller']
   overwrites=[w for w in row['CPU_software_writes']if w['address']==0x100];assert overwrites[-1]['original_PC']==0xECB9 and overwrites[-1]['before']==0xF8 and overwrites[-1]['value']==0x0F
  assert row['final']['registers']['pc']==spec['expected_stop_PC']and trace[-1]['opcode']==0x60
  assert not any(t['pc']in(0xF8C1,0x0FC1)for t in trace)
  assert sum(not c['returned_to_original_caller']for c in calls)==int(spec['expected_nonlocal'])
  stats['original_CPU_instructions']+=len(trace);stats['actual_JSR_RTS_pairs']+=len(calls);stats['normal_returns']+=sum(c['returned_to_original_caller']for c in calls);stats['nonlocal_returns']+=sum(not c['returned_to_original_caller']for c in calls);stats['port_events']+=len(events);stats['status_reads']+=sum(e['kind']=='read'for e in events);stats['raw_palette_writes']+=len(row['raw_PPU_writes'])
  routes.append(dict(parent=row['parent'],stop=row['Source_stop'],calls=[dict(caller=c['caller_pc'],target=c['target'],actual_return=c['after']['point']['registers']['pc'],SP=c['after']['point']['registers']['sp'],normal=c['returned_to_original_caller'])for c in calls],instructions=len(trace),status_reads=[dict(PC=e['original_PC'],value=e['value'])for e in events if e['kind']=='read']))
 for i,p in enumerate(points):
  assert p['offset']==i*26624 and p['bytes']==26624 and p['Source']==p['CPU'];seg=cp[p['offset']:p['offset']+26624];assert hashlib.sha256(seg).hexdigest()==p['Source_sha256']==p['CPU_sha256']
  row=next(r for key,r in by.items()if p['label'].startswith(key+'/'));start=initials[row['parent']];initial=cp[start['offset']:start['offset']+26624];h=p['CPU']['history_counts'];b=bytearray(initial[:10240]);apply_software(b,row['CPU_software_writes'][:h['software_writes']])
  es=row['CPU_port_events'][:h['IO_reads']+h['IO_writes']];d,ppu,data=rebuild_device(start['CPU']['device'],es,initial)
  if p['label'].endswith('/planned-input-appended'):
   assert d['read_ports']['8194']==[];d['read_ports']['8194']=[128]
  assert d==p['CPU']['device'],p['label'];assert bytes(b)+ppu==seg,p['label'];assert len(data)==h['PPU_data_writes']
  if p['label'].endswith('/strict-missing-retry'):
   prior=points[i-1];assert p['Source']==prior['Source']and seg==cp[prior['offset']:prior['offset']+26624]
 assert stats['actual_JSR_RTS_pairs']==14 and stats['normal_returns']==13 and stats['nonlocal_returns']==1 and stats['status_reads']==8
 save('semantic-validation.json',dict(status='passed_offline_original_call_and_full_prefix_audit',parents=3,paired_points=len(points),**dict(stats),
  all_memory_rawsink_and_declared_device_prefixes_independently_rebuilt=True,actual_BIT_flags_and_BVS_wait_verified=True,actual_RTS_frame_destinations_verified=True,
  Source_original_PC_attribution_null=True,original_CPU_Source_Native_executions_in_this_audit=0,new_Native_runs=0,physical_device_timing_credit=False))
 save('actual-continuation-evidence.json',dict(routes=routes,actual_nonlocal_counterexample=True,controlled_SP00_is_not_Native=True,
  positive_grade='Native122 full software snapshot -> declared software NMI -> original prologue -> scene2 -> real callee returns; raw device fixture',
  old_same64B_queue_bridge_closed=False,old_controlled_PC_reentry_replaced=False,NMI_RTI_completed=False,natural_hardware_NMI_credit=0))
 save('work-package-delta.json',dict(WP08=dict(new_positive_edge='Complete Native122 E066 software context, declared software NMI, original F878 dispatch and F8B5/EE53,F8B8/F206,F8BB/FB0B,EAF7,F8BE/EC67 returns -> F8C1 before opcode',
  new_wait_contract='FB22 BIT/BVS bit6set wait -> actual missing read -> strict zero-progress retry -> planned80 -> real return; bit7 does not block',
  new_negative_edge='Old actual palette-return SP00 -> same original continuation -> ECB9 overwrites0100 returnhigh -> ECBE RTS0FC1; exact nonlocal stop',
  old64B_PC_reentry_replaced=False,full_WP08_closed=False,remaining_route_premises=read(OUT/'family-scope.json')['remaining_route_premises'],remaining_route_premises_count=3),
  new_Native_runs=0,new_game_hardware_algorithms=0,production_Source_changes=0,city_field_migrations=0,raw_migrations=0,remaining323_unchanged=True,global_unknown_services=None,completion_percentage=None,remaining_rounds=None))
 save('ledger-preservation.json',dict(ledger_sources=[rec(ROOT/'analysis/wp07-palette-packet-consumer'/n)for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json')],
  full_objects_preserved_by_freeze=True,total1526=dict(conditional=1203,possible=80,unknown=243,remaining=323),raw345=dict(operand=104,data=13,unproved=228),migrations=0,
  official_city_names={str(i):None for i in(1,28,29,30,31)},EE07_known_callers=155,EE07_combined_covered=2,EE07_outside_packages=153,outside_callers_are_not_global_unknown_services=True))
 docs(v,stats,len(points))
 print(json.dumps(dict(status='passed_offline_audit',paired_points=len(points),**dict(stats))))
def docs(v,s,points):
 text=f'''# WP08：真实调用者续程与SP00反例

本包完成一个有界验证：从完整的原模拟器E066软件快照出发，声明一次软件NMI，经过原入口和城市场景调度，真实执行 `F8B5→EE53、F8B8→F206、F8BB→FB0B→EAF7、F8BE→EC67`，停在F8C1首条指令之前。另从旧SP00夹具的真实palette返回处续行，得到实际非本地返回0FC1并停机，没有修PC或SP。

3个有限案例、14对原JSR/RTS（13正常、1非本地）、{s['original_CPU_instructions']}条原ROM CPU指令、6次Source推进通过对照。8次成功2002读取；1次bit6等待、2次无输入且无状态进展的续程，其中1次严格保留整个generator链位置。{points}对完整保存点覆盖2K RAM、8K SRAM、16K原始PPU sink及设备/REG/银行JSON。新Native运行0；本包不声称全NMI/RTI或整局游戏完成。

## SP00从哪里来

SP00来自早期EE07矩阵 `all_SP_values/0000` 的显式测试轴，RAM/SRAM由公式生成。它沿phase0→phase1 step01→WP07第一次palette返回保留下来，是受控fixture，不是自然原机栈。当前导入WP07 offset79872的完整26KiB状态，SHA256 `fa808f7eec2b44045cfe3ed8e27a3fead6edd44601ce9a771549fb20fb0901cb`；PC原本就是F8B8，未取此前第二次跳回F8B5的后态。

该状态实际执行F8BE JSR EC67时，返回高F8写入0100、低C0写入01FF。EC67重算palette的ECB9又把0100写成0F；ECBE真正RTS消费C0/0F，实际目的为0FC1、SP00。Source和独立原ROM CPU一致，停在0FC1执行前。这只说明该人工栈上下文不适合继续这一调色路径，不能称为Native游戏故障。

## 完整来源及证据等级

所查WP05的122份完整软件快照和265872条选定总线事件，没有保存F8B5/F8B8/FB22/EC67的同一瞬间完整scene2现场。此结果只限观察hook的选择范围，不能当成这些指令从未运行。旧WP08 run05属于scene3；其EC67选定寄存器检查点没有同一时刻完整RAM/SRAM，不能拼接来替换SP。

采用WP05 frame383的 `callee-0122-E066`：全10KiB SHA256 `a92e590d49aa56de45a66f5751200fe306515a11ebc9fee9523d146042c74a9b`；REG E066/A90/X00/Y00/PE4/SPFF、PRG[2,29,30,31]，global2/NMI2、7D/7E=01/00。所有软件内存、寄存器和银行完整保留。它与旧64B待传queue不同，未移植任何旧queue或SP。

每个正例显式触发一次软件NMI：原PC/P三字节中断帧、F800保存AXY三字节均真实形成，scene基准SPF9；原指针00/01=F8B5后，以可读源码补足F878 JMP($0000)语义。后续每一调用都要求实际PC恰在原callsite，并核真实返回PC/SP。EC67的计时器8A由4减至3，走提前返回，真正RTS到F8C1/SPF9。NMI外层仍在栈上，未执行F8C1或后续恢复/RTI。

证据等级是“Native完整软件快照→明示软件NMI派生→原调用链”，不是捕获到的自然F8B5现场或真实硬件NMI时序。

## FB22等待与设备合同

FB22是BIT $2002，FB25是BVS回FB22，检查bit6，保留A并设置N/V/Z。80虽有bit7置位但bit6清，正常退出；40会等待。等待案例在真实BIT+BVS返回FB22后对齐Source暂停；下一读缺样本时停在BIT之前。第一次由sprite-hit等待转为缺输入等待只声明无模拟状态进展；第二次重试还核同owner、整条generator及位置不变。只追加预锁80样本后，在同对象续行并真实返回。

复用既有ServiceMemory，有序保存PPU/CHR/nametable/mapper/N163计数器命令。4014记录完整256字节DMA请求和OAMADDR；不因此获得实际OAM传输、DMA停顿或周期信用。fresh设备状态另行声明，未捕获的PPU/APU/N163瞬态未由软件快照补造。缺少vblank产生/读后清bit7、开放总线、物理镜像、6位palette掩码、周期、IRQ调度和渲染/音频模型。

新适配器只补F878控制流语义、严格调用者校验和观察；所有业务算法仍来自既有battle_nmi_services.py的nmi_body、pending_ppu/palette_upload、chr_banks、nametable_banks/scroll_control、palette_fade。旧生产源码未改，无CPU/IR作为Source回调。

## 验证材料

- [可读续程源码](continuation_adapter.py)、[来源链](source-provenance.json)、[有限来源搜索](finite-source-search.json)
- [预锁范围](family-scope.json)、[3案矩阵](case-matrix.json)、[设备合同](device-contract.json)、[验收pins](acceptance.json)
- [执行输入及hash](run-01/execution-inputs.json)、[运行结果](run-01/validation.json)、[逐指令与调用证据](run-01/parents.jsonl)、[完整保存点索引](run-01/points.jsonl)
- [独立离线前缀重建](semantic-validation.json)、[实际返回证据](actual-continuation-evidence.json)、[工作包增量](work-package-delta.json)、[最终封存](verification.json)

离线审计从初态和实际软件/端口写前缀重建全部保存点，复核真实压栈、BIT flags、RTS目标和完整DMA bytes；该审计没有再次执行Source、CPU或Native。

## 仍未闭合

本包增加scene2相邻调用、bit6等待恢复及SP00非本地返回的明确证据。它没有替换此前同一个64B包的受控PC重入，也没有连接旧queue到新Native122上下文。该路线仍有3项明确前提：旧64B queue与兼容的实际/派生NMI入口；F8C1之后直到下一消费者的真实scene/NMI续程；兼容设备现场和时序。3是本路线前提数，不是全局未知服务数或剩余轮数。

分类账1526=1203/80/243、remaining323，raw345=104/13/228均不变；城市+1及+28..31正式字段名仍null。155个已知EE07 caller、跨包覆盖2个、外部153的口径不变。239563旧路径前后冻结。未发布、推送或分发ROM；完成此包后停止，完整WP08和整游戏仍未完成。
'''
 p=OUT/'README.md';assert not p.exists();p.write_text(text)
 p=OUT/'index.html';assert not p.exists();p.write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>WP08真实续程</title><style>body{{font:17px/1.75 system-ui;max-width:900px;margin:48px auto;padding:0 24px;background:#faf9f6;color:#20252b}}a{{color:#165f8c}}td{{padding:10px 18px;border-bottom:1px solid #ccc}}table{{border-collapse:collapse}}</style><h1>原调用者续程与SP00反例</h1><p>完整Native软件快照 → 明示软件NMI → 城市场景 → 真RTS到F8C1。旧SP00夹具则真实返回0FC1，并原样停止。</p><table><tr><td>有限案例 / 实际调用</td><td>3 / 14对JSR与RTS，13正常+1非本地</td></tr><tr><td>原CPU指令 / 完整保存点</td><td>{s['original_CPU_instructions']} / {points}对</td></tr><tr><td>FB22</td><td>BIT检查bit6；80退出，40等待；缺输入严格暂停/恢复</td></tr><tr><td>新增Native / 全NMI/RTI</td><td>0 / 未完成</td></tr><tr><td>旧64B包重入替换</td><td>未替换；不同完整来源不能拼接</td></tr><tr><td>城市正式字段名 / 剩余候选</td><td>仍null / 323，不变</td></tr></table><p>设备是显式原始命令sink，无硬件时序或渲染信用。SP00来自测试轴，不是自然原机现场。</p><p><a href="README.md">完整报告</a> · <a href="continuation_adapter.py">可读源码</a> · <a href="run-01/validation.json">运行结果</a> · <a href="semantic-validation.json">离线复核</a> · <a href="verification.json">最终封存</a></p></html>''')
def seal():
 a=checkpins();v=read(RUN/'validation.json');s=read(OUT/'semantic-validation.json');b=read(OUT/'frozen-before.json');e=read(OUT/'frozen-after.json')
 assert v['status']=='passed_bounded_real_continuation_contract'and s['status']=='passed_offline_original_call_and_full_prefix_audit'
 assert b['status']==e['status']=='passed'and b['old_work_paths']==e['old_work_paths']==239563 and b['frozen_manifest_sha256']==e['frozen_manifest_sha256']
 for p in(ROOT/'scripts').glob('*wp08_real_continuation*.py'):ast.parse(p.read_text())
 save('input-manifest.json',dict(current_producers=[rec(p)for p in sorted((ROOT/'scripts').glob('*wp08_real_continuation*.py'))],adapter=rec(OUT/'continuation_adapter.py'),actual_execution=rec(RUN/'execution-inputs.json'),
  implementation_pins=a['implementation_pins'],frozen_work=rec(OUT/'frozen-work-inputs.json'),previous_verification=rec(ROOT/'analysis/wp07-palette-packet-consumer/verification.json'),original_core=rec(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'),ROM_SHA256=read(OUT/'family-scope.json')['ROM_SHA256'],ROM_distributed=False))
 files={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(OUT.rglob('*'))if p.is_file()}
 save('artifact-manifest.json',dict(files=files,excludes=['artifact-manifest.json','verification.json']))
 save('verification.json',dict(schema='WP08-real-continuation-final-v1',status='sealed_bounded_real_continuation_and_nonlocal_counterexample',
  parents=3,actual_JSR_RTS_pairs=14,normal_RTS_returns=13,nonlocal_RTS_returns=1,original_CPU_instructions=v['CPU_instructions'],Source_advances=6,software_NMI_entries=2,
  status_successes=8,bit6_waits=1,missing_zero_state_resumes=2,strict_same_generator_position_retries=1,paired_points=v['paired_points'],buffers=v['buffers'],
  full_memory_rawsink_and_device_prefix_audit=True,actual_return_positive_PC=0xF8C1,actual_return_negative_PC=0x0FC1,actual_positive_SP=0xF9,actual_negative_SP=0,
  source_grade='Native software snapshot -> controlled software NMI -> original scene2 caller; instantaneous device fixture',SP00_origin='explicit prior test-matrix axis, not Native',
  new_Native_runs=0,natural_hardware_NMI_credit=0,NMI_RTI_completed=False,host_PC_SP_flags_repairs=0,Source_CPU_IR_callbacks=0,production_Source_changes=0,new_game_hardware_algorithms=0,
  old_same64B_reentry_replaced=False,remaining_route_premises_count=3,premise_count_is_not_global_services_or_rounds=True,
  preserved_work_paths=239563,old_missing_or_changed=0,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),artifact_manifest_sha256=sha(OUT/'artifact-manifest.json'),artifact_manifest_entries=len(files),
  field_counts=dict(total=1526,conditional=1203,possible=80,unknown=243,remaining=323),raw_counts=dict(total=345,operand=104,data=13,unproved=228),migrations=0,official_city_names={str(i):None for i in(1,28,29,30,31)},
  known_EE07_callers=155,covered_combined=2,outside_packages=153,unknown_global_services=None,completion_percentage=None,remaining_rounds=None,full_WP08_closed=False,whole_game_closed=False,stopped_after_package=True))
 print(json.dumps(dict(status='sealed',verification_sha256=sha(OUT/'verification.json'),artifact_manifest_sha256=sha(OUT/'artifact-manifest.json'),artifact_manifest_entries=len(files),preserved_work_paths=239563)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','seal'));a=p.parse_args();audit()if a.mode=='audit'else seal()
