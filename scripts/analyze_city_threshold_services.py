#!/usr/bin/env python3
"""Pin city threshold helpers; optionally export real saved-PC caller inputs.

Production code is hand-written. Original-CPU continuation, if requested, is
only an analysis oracle and does not synthesize NMI/IRQ, RNG, PC or readiness.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction
from source.recovered.city_threshold_services import ROM_SHA256
OUT=ROOT/'analysis/phase23/threshold';CPU=ROOT/'analysis/phase23/cpu-threshold'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def off(bank,pc):return 16+bank*8192+(pc&8191)
def registers(c):return{k:getattr(c,k)for k in('a','x','y','p','sp','pc')}
def return_word(m,sp,shift=1):return((m[0x100+((sp+shift)&255)]|m[0x100+((sp+shift+1)&255)]<<8)+1)&65535
def write_readmes(receipt,dynamic,trace):
 counts=receipt['counts']
 (OUT/'README.md').write_text(f'''# 城市门槛、资源上限与支付辅助服务

本轮新增独立手写 [CityThresholdServices](../../../source/recovered/city_threshold_services.py)，恢复 physical11 的 D105..D12C、D36F..D3A8、D69D..D6CF，共 149 字节、85 个指令位置。已有 physical10 BD7A 完整补兵/发展消费者继续复用阶段18具名源码，不计为本轮新增恢复。

| 入口 | 具名方法 | 精确作用 |
| --- | --- | --- |
| D105 | `city_pointer_and_resource_caps` | 用 raw8 A 构建 `6000+32*A`，先限制金/粮到9999，再返回 owner低3位；后续归属检查失败也不撤销上限写入。 |
| D69D | `cap_city_word` | 顺序检查 +2/+3 金、+4/+5 粮；>=10000 时写9999，低字节先写，金先于粮；不写 +1。 |
| D36F | `pay_city_gold` | 原真实调用帧、可选随机加费、16位费用回绕、扣金或 CLC 拒绝；拒绝保留先前上限/RNG/费用/临时区效果。BD7A 父流程忽略该 carry。 |

`run_entry(entry, registers=actual_registers)` 保留已有真实 caller，未提供服务时停在真实依赖处，不种植返回地址或确认信号。PUBLIC 沿用 CityRecruitmentServices 并增加上述三个入口。`threshold_snapshot(city)` 是仅供实际城市0..29的只读检查接口，不声称 CPU 寄存器/栈/mapper 合同。

原 BD8D 调 D105 后，20/21 是城市原基址，并未偏移1。BD97 比较 `LE16(city+1,city+2)>=300`，其中 +2 是实际金的低字节。精确条件是上限处理后的金低字节>=2，或低字节==1且不明 +1>=44；低字节0总拒绝。金高字节不直接参与该比较，但在更早 D105 的资源上限中有作用。+1 的正式名称仍未知，不能将该判定改称金>=300，也不能称支付300。

完整父消费者保留全部10槽、FF洞跳过、low10兵数、首将固定评分100与后遇相同评分优先、库存相等仍进入购买、8位购买费/16位库存回绕、付款失败 carry 被忽略、raw1000写回与随后预算扣2的实际顺序。原库存足够的 Native 过门槛组不在此补兵时扣金；后续发展付款单列。

验证 [validation.json](validation.json) 实际通过 {receipt['original_CPU_parent_cases']} 原CPU父案：{counts.get('actual_caller_RTS',0)} RTS、{counts.get('strict_missing_dependency_prefix',0)} 严格缺 E88A 的 RNG 依赖前缀，另 {receipt['source_guard_count']} 个源码 guard。逐案比较全部2048 RAM（含闲置栈）、8192 SRAM、AXYP/SP/PC、顺序端口读写、四个实际PRG页与N163 RAM/地址/自增；Source 原CPU callback=0。受控 raw城市30..255、栈回绕、全部NZCV、费用不足/回绕、上限影响后续门槛等仅是明确的软件CPU数值边界，不是 Native UI 可达性证明。只读公式另做65536输入模型检查，计入 Source CPU案数0。

新增85个静态位置中动态命中 {dynamic} 个；位置命中不等于全部路径或输入已证明。全部原字节/含16字节头的ROM偏移在 [static-catalog.json](static-catalog.json) 与 [original.asm](original.asm)。

正式 Native 六组由独立原核心/观察核心双跑提供，1组天然金额8888/+1=0，5组明确准备金币257/258/512或 +1=43/44。新导出24个独立原CPU调用输入（4自然、20诊断），使用真实保存PC/MAP/N163，无新NMI/IRQ、PC/RNG/request/ready写入。详见 [调用来源](../cpu-threshold/README.md)。它们支持相同门槛和补兵效果，不声称后续随机付款/最终金的整帧 Native 等价。未确认专用 +1 producer；有限未观察写入不能证明字段无用。

可复现本轮命令（不运行旧生成器）：

```sh
.venv-trace/bin/python scripts/analyze_city_threshold_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --capture-native
.venv-trace/bin/python scripts/verify_city_threshold_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_threshold_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 if trace is not None:
  (CPU/'README.md').write_text(f'''# 实际保存点到门槛调用的独立原CPU前序

[trace.json](trace.json) 从阶段23六组正式 `original-control/actual-frame-003.state` 的实际 REG/MAP/N163 开始，每组无新增中断地执行原ROM，导出 {trace['exported_caller_inputs']} 个真实已到达调用输入：每组 BD7A、BD90返回点的D105、其D126返回点的D69D，以及真实D36F支付入口。原始输入在 `actual-callers/entry-*`，每个目录保存 context、完整RAM/SRAM/N163。

自然组4输入的 origin 为 `actual_Native_snapshot_originalCPU_reached_caller`；其余20输入为 `diagnostic_Native_snapshot_originalCPU_reached_caller`，明确继承 Native 金额/不明+1准备。`additional_CPU_prepared_numeric_bytes=[]`，新NMI/IRQ数0；没有构造caller、PC、RNG、request或ready。硬件端口输入明确固定 PPUSTATUS0/APUstatus0/NamcoIRQ127/双手柄0，为独立原CPU软件观察条件。

六组首个城市2 BD97 均在前序第2528指令；BD7A在第2381指令。过门槛组再次评估并实际补到兵1000、库存7799。原CPU后续预算18（拒绝组20），而原核心帧5刚补兵时预算28；两者终点不同。独立原CPU没有后续NMI/RNG时序，因此例如天然组最终金8853与原核心8850不同。只声明门槛及补兵效果对应，不声明整个request/帧/最终金一致。原核心 +1 读取有被动观察证据，瞬时 +2 解释同时依赖原字节与独立CPU，不能将它冒充同一原核心bus观测。

这里 Source CPU比较案数0，非 Native 内部逐指令trace。24个输入在独立 [Source验证](../threshold/validation.json) 中逐案做完整服务差分；前序指令数、导出数及Native双跑均不重复计入 Source父案。

来源固定为阶段23正式runtime六组；自然母档继承阶段22实际野外录用后兵700的保存点。未修改旧阶段、原ROM或原核心。
''')
def capture_native(rom):
 from py65.devices.mpu6502 import MPU
 from source.recovered.nestopia_context import NestopiaContext
 manifest=ROOT/'analysis/phase23/runtime/evidence.json';native=json.loads(manifest.read_text());assert native['status']=='passed'
 cases=[];pins={str(manifest.relative_to(ROOT)):sha(manifest)}
 for item in native['native_cases']:
  case=item['case'];path=ROOT/'analysis/phase23/runtime'/item['folder']/'actual-frame-003.state';saved=NestopiaContext.parse(path.read_bytes())
  m=saved.service_memory(rom,read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0));c=MPU(memory=m)
  for k,v in saved.registers.items():setattr(c,k,v)
  origin='diagnostic_Native_snapshot_originalCPU_reached_caller'if item['controlled_diagnostic']else'actual_Native_snapshot_originalCPU_reached_caller'
  prep=item['preparation'];captured=[];gates=[];branches=[];before5=None
  for step in range(200000):
   if m[0x6F8B]==255:stop='original_request_FF';break
   if c.pc==0xFB28:stop='actual_hardware_IRQ_wait';break
   if c.pc<0x8000:stop='non_ROM_PC_boundary';break
   if tuple(m.banks[1:3])==(10,11):
    target=None;ret=return_word(m,c.sp)
    if c.pc==0xBD7A:target='BD7A'
    elif c.pc==0xD105 and c.a==2 and ret==0xBD90:target='D105-BD90'
    elif c.pc==0xD69D and(m[0x20]|m[0x21]<<8)==0x6040 and ret==0xD126 and return_word(m,c.sp,3)==0xBD90:target='D69D-D126-BD90'
    elif c.pc==0xD36F:target='D36F'
    if target is not None:
     key='entry-'+target+'-'+case;folder=CPU/'actual-callers'/key
     if key not in captured:
      context=dict(schema='phase23-city-threshold-caller-input-v1',origin=origin,original_Native_state=str(path.relative_to(ROOT)),original_Native_state_sha256=sha(path),native_captured_registers=saved.registers,
       original_CPU_prefix_instructions=step,registers=registers(c),physical_banks=list(m.banks),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
       existing_return_PC=ret,actual_grandparent_return_PC=return_word(m,c.sp,3),synthetic_caller_or_PC_or_RNG_or_request_preparation=False,
       injected_new_NMI=0,injected_new_IRQ=0,hardware_events=[dict(kind='explicit_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0],range='entire independent originalCPU continuation')],
       prepared_numeric_bytes=prep,inherited_Native_preparation=prep,additional_CPU_prepared_numeric_bytes=[],Native_internal_CPU_trace=False)
      folder.mkdir(parents=True,exist_ok=True);(folder/'input-ram.bin').write_bytes(m.ram);(folder/'input-sram.bin').write_bytes(m.sram);(folder/'input-n163.bin').write_bytes(m.n163_ram);dump(folder/'context.json',context);captured.append(key)
    if c.pc==0xBD97:
     city=m[0x36];base=m[0x20]|m[0x21]<<8;row=dict(step=step,city=city,pointer20=base,Y=c.y,opaque_byte1=m[base+1],true_gold=m[base+2]|m[base+3]<<8,overlap_word=m[base+1]|m[base+2]<<8,registers=registers(c));row['unsigned_predicate']=row['overlap_word']>=300;gates.append(row)
    if c.pc==0xBDA1:branches.append(dict(step=step,city=m[0x36],carry=bool(c.p&1),registers=registers(c)))
    if c.pc==0xBEB8 and m[0x38]==5 and before5 is None:before5=dict(step=step,true_gold=m[0x6042]|m[0x6043]<<8,reserve=m[0x604C]|m[0x604D]<<8,budget=m[0x6F5D])
   c.step()
  else:stop='explicit_instruction_budget'
  assert len(captured)==4,(case,captured)
  cases.append(dict(case=case,origin=origin,native_state=str(path.relative_to(ROOT)),saved_registers=saved.registers,actual_banks=list(saved.prg_banks),prepared_numeric_bytes=prep,additional_CPU_prepared_numeric_bytes=[],new_NMI_IRQ_arrivals=0,
   original_instructions=step,stop=stop,captured=captured,gates=gates,branches=branches,before_officer5_commit=before5,
   final_fields=dict(officer5_troops=m[0x63C0+5*12+8]|m[0x63C0+5*12+9]<<8,city2_gold=m[0x6042]|m[0x6043]<<8,city2_reserve=m[0x604C]|m[0x604D]<<8,budget=m[0x6F5D]),
   source_CPU_cases=0,Native_internal_CPU_trace=False))
  pins[str(path.relative_to(ROOT))]=sha(path)
 for p in(CPU/'actual-callers').rglob('*'):
  if p.is_file():pins[str(p.relative_to(ROOT))]=sha(p)
 trace=dict(schema='phase23-city-threshold-originalCPU-context-trace-v1',status='bounded_original_CPU_observation',ROM_sha256=ROM_SHA256,contexts=len(cases),exported_caller_inputs=sum(len(x['captured'])for x in cases),source_CPU_cases=0,
  source_sha256={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),ROOT/'source/recovered/nestopia_context.py',ROOT/'source/recovered/service_memory.py')},artifact_sha256=pins,cases=cases,
  limits=['Pure continuation from actual saved REG/MAP/N163; no new interrupt, RNG, PC, caller or readiness is prepared.','Five diagnostic Native initial states inherit their explicitly declared gold/opaque-byte preparation. They are not natural counterexamples.','The independent CPU reaches the same gate and reinforcement effect; later RNG fees/final gold can differ from the interrupted Native frames.','OriginalCPU preparation and exported callees are not extra Source comparison cases.'])
 dump(CPU/'trace.json',trace)
 return trace
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--capture-native',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 trace=capture_native(rom)if a.capture_native else json.loads((CPU/'trace.json').read_text())if(CPU/'trace.json').exists()else None
 OUT.mkdir(parents=True,exist_ok=True);ranges=[];positions=[];listing=[]
 for start,end,name in((0xD105,0xD12D,'rawcity pointer and resource cap'),(0xD36F,0xD3A9,'gold payment with optional random surcharge'),(0xD69D,0xD6D0,'gold/grain cap to9999')):
  data=rom[off(11,start):off(11,end)];ranges.append(dict(physical_bank=11,cpu_start=start,cpu_end_exclusive=end,rom_offset=off(11,start),byte_count=len(data),raw_hex=data.hex(' ').upper(),sha256=hashlib.sha256(data).hexdigest(),name=name))
  pc=start
  while pc<end:
   at=off(11,pc);size,asm=instruction(rom,at,pc);raw=rom[at:at+size];x=dict(physical_bank=11,cpu_address=pc,rom_offset=at,size=size,raw_hex=raw.hex(' ').upper(),assembly=asm);positions.append(x);listing.append(f'{at:06X} b11:${pc:04X} {x["raw_hex"]:<11} {asm}');pc+=size
  assert pc==end
 catalog=dict(schema='phase23-city-threshold-new-helper-byte-catalog-v1',ROM_sha256=ROM_SHA256,new_manual_instruction_positions=len(positions),new_manual_code_bytes=sum(x['byte_count']for x in ranges),instructions=positions,original_ranges=ranges,
  full_consumer_reused_frozen_source='source/recovered/city_auxiliary_services.py:recruitment_then_development',real_dependencies=[dict(physical_bank=11,cpu=0xD4BB,name='random_below, inherited frozen source, genuine E88A dependency')])
 dump(OUT/'static-catalog.json',catalog);(OUT/'original.asm').write_text('; New hand-written helper scopes; offsets include16-byte header.\n'+'\n'.join(listing)+'\n')
 if not(OUT/'validation.json').exists()or json.loads((OUT/'validation.json').read_text())['quick']:
  print(json.dumps(dict(status='capture_and_catalog_written',contexts=0 if trace is None else trace['contexts'],exports=0 if trace is None else trace['exported_caller_inputs'],new_positions=len(positions))));return
 receipt=json.loads((OUT/'validation.json').read_text());assert receipt['status']=='passed'
 vis={(x['physical_bank'],x['cpu_address'])for x in receipt['executed_instruction_positions']};dynamic=sum((11,x['cpu_address'])in vis for x in positions)
 write_readmes(receipt,dynamic,trace)
 source=ROOT/'source/recovered/city_threshold_services.py';tree=ast.parse(source.read_text());assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('exec','eval','compile')for n in ast.walk(tree))
 files=('source/recovered/city_threshold_services.py','source/recovered/city_threshold_integration.py','source/recovered/city_recruitment_services.py','source/recovered/city_auxiliary_services.py','source/recovered/domestic_cooperation_controller.py','source/recovered/nestopia_context.py','scripts/analyze_city_threshold_services.py','scripts/verify_city_threshold_services.py')
 evidence=dict(schema='phase23-city-threshold-resource-helper-evidence-v1',ROM_sha256=ROM_SHA256,source_sha256={p:sha(ROOT/p)for p in files},production_original_CPU_callbacks=0,production_IR_interpretation=False,production_runtime_codegen=False,
  coverage=dict(new_manual_instruction_positions=len(positions),new_manual_code_bytes=149,dynamic_new_positions=dynamic,not_dynamic=len(positions)-dynamic,all_paths_or_inputs_proven=False),
  validation=dict(path=str((OUT/'validation.json').relative_to(ROOT)),sha256=sha(OUT/'validation.json'),original_CPU_parent_cases=receipt['original_CPU_parent_cases'],counts=receipt['counts'],source_guard_count=receipt['source_guard_count'],domains=dict(Counter(x['domain']for x in receipt['cases']))),
  exact_scope=dict(RAM_bytes=2048,SRAM_bytes=8192,registers=['A','X','Y','P','SP','PC'],ordered_IO_reads_writes=True,four_PRG_banks=True,N163_RAM_address_autoincrement=True,free_stack_excluded_bytes=0),
  threshold=dict(original_body='10 BD95..BDA1',original_city_pointer_call='10 BD8D→11 D105',actual_base='6000+32*rawcity; no pointer+1 bias',original_low_byte=1,original_high_byte=2,threshold=300,predicate='postcap_gold_low>=2 or(postcap_gold_low==1 and opaque_city_byte1>=44)',gold_high='Ignored by the predicate after caps; it still participates in D105 actual gold cap before the read.',opaque_name_confirmed=False),
  new_helper_effects=dict(D105='Raw8 city pointer20/21; cap actual gold/grain before owner&7 result. Caps happen even when owner check subsequently fails.',D69D='LE16 city+2/+3 and+4/+5>=10000 are written9999, low before high, gold before grain. It never writes+1.',D36F='Caps before optional random fee, cost16 wrap; repeats D105 and cap before subtraction. Insufficient funds CLC leaves prior caps and fee/RNG/scratch effects; success high-then-low write, another cap, SEC. BD7A ignores returned carry.'),
  caller_order='B49C real sampling/redistribution tails BD7A; every city D105/caps→owner test→overlap gate→all10roster entries→low10==1000 skip→head100/武力 late ties→chosen fill/reserve purchase→raw1000 commit→budget2. Existing named caller remains frozen and is not recounted as new recovery.',
  hypothesis_limits=['Six controlled/natural Native cohorts establish this observed branch and complete effect. They do not give+1 a formal name.','A literal gold>=300 test is not equivalent: actual diagnostic gold258 passes while512 rejects with+1=0.','The qualifying branch is not a payment300: reserve-sufficient cases keep gold unchanged at reinforcement and deduct reserve300/budget2; later development/payment is separate.','No dedicated+1 producer is confirmed. Existing initialization/copy and unresolved arbitrary-writer paths are separate; finite zero-write observation is not an unused-field proof.','Raw corrupt city/pointer cases in the CPU matrix are explicitly mechanical domains, not legal Native UI inputs.'],
  artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm',OUT/'README.md')})
 dump(OUT/'evidence.json',evidence)
 if trace is not None:
  dump(CPU/'evidence.json',dict(schema='phase23-threshold-caller-provenance-v1',status='bounded_original_CPU_observation',ROM_sha256=ROM_SHA256,contexts=trace['contexts'],exported_caller_inputs=trace['exported_caller_inputs'],source_CPU_cases=0,Native_internal_CPU_trace=False,
   pure_no_additional_NMI_IRQ=True,natural_contexts=1,prepared_diagnostic_contexts=5,trace=dict(path=str((CPU/'trace.json').relative_to(ROOT)),sha256=sha(CPU/'trace.json')),source_sha256=trace['source_sha256'],artifact_sha256=trace['artifact_sha256'],limits=trace['limits']))
 print(json.dumps(dict(status='written',new_positions=len(positions),dynamic=dynamic,CPU=receipt['original_CPU_parent_cases'],counts=receipt['counts'],exports=0 if trace is None else trace['exported_caller_inputs'])))
if __name__=='__main__':main()
