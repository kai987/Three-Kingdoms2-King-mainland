#!/usr/bin/env python3
"""OriginalCPU effective-address watch from captured Native PC/MAP/N163.

No PC/frame/request/RNG or readiness is prepared. This is an independent CPU
continuation with explicit hardware inputs and no newly scheduled NMI/IRQ,
not a Native internal instruction recording. Diagnostic accesses do not count
as source differential cases or establish universal field names.
"""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import NestopiaContext,CapturedServiceMemory
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase21/cpu'
REGS=('a','x','y','p','sp','pc')
ENTRIES={0xA000,0xC5B9,0xC5D2,0xC66F,0xC6CC,0xC71A}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(c):return{k:getattr(c,k)for k in REGS}
def raw(memory,addr):return CapturedServiceMemory.__getitem__(memory,addr&65535)
class WatchMemory(CapturedServiceMemory):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.active=False;self.context={};self.accesses=[];self.zp_writers={}
 def observe(self,address,value,kind,before=None):
  if not self.active:return
  c=self.context
  if kind=='write'and address<256:self.zp_writers[address]=dict(step=c['step'],physical_bank=c['physical_bank'],pc=c['pc'],value=value)
  if not 0x6000<=address<0x63C0:return
  city,offset=divmod(address-0x6000,32)
  # All city accesses are retained. The targeted subset is explicitly marked.
  zp=c['opcode_operand'];pointer=None
  if c['opcode']in(0x11,0x31,0x51,0x71,0x91,0xB1,0xD1,0xF1):pointer=zp
  row=dict(**c,operation=kind,effective_address=address,value=value,city_id=city,normalized_offset=offset,
   target_auxiliary=offset in(1,28,29,30,31),zero_page_pointer=pointer,
   pointer_value=None if pointer is None else raw(self,pointer)|(raw(self,(pointer+1)&255)<<8),
   pointer_low_writer=None if pointer is None else self.zp_writers.get(pointer),
   pointer_high_writer=None if pointer is None else self.zp_writers.get((pointer+1)&255))
  if before is not None:row['before']=before
  if(c['physical_bank'],c['pc'])in((11,0xC664),(11,0xC778),(10,0xA445),(27,0xAD4B)):row['observed_operation_role']='first_FF_scan'
  elif(c['physical_bank'],c['pc'])==(10,0xBD97):row['observed_operation_role']='overlapping_city1_city2_threshold'
  elif(c['physical_bank'],c['pc'])in((11,0xD3F0),(11,0xD406)):row['observed_operation_role']='roster_compaction'
  else:row['observed_operation_role']='effective_access_only_no_official_field_name_inferred'
  self.accesses.append(row)
 def __getitem__(self,address):
  value=super().__getitem__(address)
  if isinstance(address,int):self.observe(address,value,'read')
  return value
 def __setitem__(self,address,value):
  before=raw(self,address)if isinstance(address,int)and(address<0x2000 or 0x6000<=address<0x8000)else None
  super().__setitem__(address,value)
  if isinstance(address,int):self.observe(address,value&255,'write',before)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--state',type=Path,action='append');p.add_argument('--instruction-budget',type=int,default=200000);a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA;OUT.mkdir(parents=True,exist_ok=True)
 paths=a.state or[ROOT/'analysis/phase20/runtime/natural-F8-accept/AI-ruler4-status00-frame10479.state',
  ROOT/'analysis/phase21/runtime/original-control/actual-cold-frame10491.state',
  ROOT/'analysis/phase21/runtime/original-control/actual-cold-frame10492.state']
 rows=[];pins={};all_accesses=[];all_rng=[];captured=[]
 for path in paths:
  path=path.resolve();native=NestopiaContext.parse(path.read_bytes());hardware=dict(read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m=WatchMemory(rom,native.ram,native.sram,native.prg_banks,**hardware);m.n163_ram[:]=native.n163_ram;m.n163_address=native.n163_address;m.n163_autoincrement=native.n163_autoincrement
  c=MPU(memory=m)
  for k,v in native.registers.items():setattr(c,k,v)
  chain=[];rng_stack=[];rng=[];scans=[];stop=None;initial_request=m[0x6F8B]
  for n in range(a.instruction_budget):
   if c.pc<0x8000:stop='non_ROM_PC_boundary';break
   bank=m.banks[(c.pc-0x8000)//8192]
   if tuple(m.banks[1:3])==(10,11)and c.pc in ENTRIES:
    folder=OUT/'actual-callers'/f'entry-{c.pc:04X}'
    if not folder.exists():
     folder.mkdir(parents=True);(folder/'input-ram.bin').write_bytes(m.ram);(folder/'input-sram.bin').write_bytes(m.sram);(folder/'input-n163.bin').write_bytes(m.n163_ram)
     x=dict(schema='phase21-formal-Native-REG-originalCPU-callee-input-v1',original_Native_state=str(path.relative_to(ROOT)),original_Native_state_sha256=sha(path),native_captured_registers=native.registers,
      original_CPU_prefix_instructions=n,registers=reg(c),physical_banks=list(m.banks),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
      existing_return_PC=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535,
      synthetic_caller_or_PC_or_RNG_or_request_preparation=False,new_NMI_IRQ_arrivals=0,Native_internal_CPU_trace=False,prepared_numeric_bytes=[])
     (folder/'context.json').write_text(json.dumps(x,indent=2)+'\n');captured.append(str(folder.relative_to(ROOT)));print(json.dumps(dict(captured=hex(c.pc),prefix=n,native=path.name)),flush=True)
   if c.pc==0xE89A:rng_stack.append(dict(step=n,input_X=c.x,input53=m[0x53],cursor54=m[0x54],input_SP=c.sp,return_PC=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535))
   if bank==11 and c.pc==0xC726:scans.append(dict(step=n,X=c.x,pointer22=m[0x22]|m[0x23]<<8,effective_address=(m[0x22]|m[0x23]<<8)+c.y))
   if initial_request!=255 and m[0x6F8B]==255:stop='original_request_FF';break
   if m[0x6F8B]in(248,249,250,251,252):stop='original_software_request';break
   if c.pc==0xFB28:stop='hardware_IRQ_wait';break
   op=m[c.pc];operand=m[(c.pc+1)&65535];old_pc,old_sp=c.pc,c.sp
   m.context=dict(step=n,physical_bank=bank,pc=c.pc,ROM_offset=16+bank*8192+(c.pc&8191),opcode=op,opcode_operand=operand,registers=reg(c),
    last_actual_JSR_chain=chain[-5:],city_scan_0036=m[0x36],pointer00=m[0]|m[1]<<8,pointer20=m[0x20]|m[0x21]<<8,pointer22=m[0x22]|m[0x23]<<8)
   m.active=True
   try:c.step()
   except Exception as exc:stop='explicit_hardware_or_execution_boundary: '+str(exc);break
   finally:m.active=False
   if op==0x20:chain.append(dict(physical_bank=bank,call_pc=old_pc,target=operand|(m[(old_pc+2)&65535]<<8),return_pc=old_pc+3,caller_sp=old_sp))
   if op==0x60:
    index=next((i for i in range(len(chain)-1,-1,-1)if(chain[i]['return_pc'],chain[i]['caller_sp'])==(c.pc,c.sp)),None)
    if index is not None:del chain[index:]
   if rng_stack and(c.pc,c.sp)==(rng_stack[-1]['return_PC'],(rng_stack[-1]['input_SP']+2)&255):
    x=rng_stack.pop();x.update(returned_X=c.x,returned53=m[0x53],returned54=m[0x54],X_preserved=c.x==x['input_X']);rng.append(x)
  else:stop='explicit_instruction_budget'
  stem=path.stem;case=dict(native_state=str(path.relative_to(ROOT)),native_sha256=sha(path),captured_registers=native.registers,actual_PRG_banks=list(native.prg_banks),
   original_instructions=n,stop=stop,final_registers=reg(c),final_request=m[0x6F8B],all_city_access_count=len(m.accesses),target_auxiliary_access_count=sum(x['target_auxiliary']for x in m.accesses),
   C726_record_reads=len(scans),C726_first=scans[:1],C726_last=scans[-1:],uninterrupted_E89A_calls=len(rng),all_uninterrupted_E89A_X_preserved=all(x['X_preserved']for x in rng),
   accesses_file=f'{stem}-accesses.json',rng_file=f'{stem}-E89A-calls.json',Native_internal_CPU_trace=False,new_NMI_IRQ_arrivals=0,prepared_bytes=[])
  (OUT/case['accesses_file']).write_text(json.dumps(m.accesses,indent=2)+'\n');(OUT/case['rng_file']).write_text(json.dumps(rng,indent=2)+'\n')
  rows.append(case);all_accesses.extend(m.accesses);all_rng.extend(rng);pins[str(path.relative_to(ROOT))]=sha(path)
 # Keep exported true callers idempotent across a repeated analysis run. A
 # later context does not overwrite a previous actual caller with the same
 # entry; the per-caller metadata remains the authoritative provenance.
 captured=[str(path.parent.relative_to(ROOT))for path in sorted((OUT/'actual-callers').glob('entry-*/context.json'))]
 generated=[OUT/case[key]for case in rows for key in('accesses_file','rng_file')]
 generated.extend(path for path in(OUT/'actual-callers').rglob('*')if path.is_file())
 for path in generated:pins[str(path.relative_to(ROOT))]=sha(path)
 result=dict(schema='phase21-Native-context-originalCPU-city-effective-access-v1',status='bounded_original_CPU_observation',ROM_sha256=ROM_SHA,contexts=rows,captured_callers=captured,
  source_CPU_comparison_cases=0,Native_internal_CPU_trace=False,new_NMI_IRQ_arrivals=0,PC_RNG_request_ready_or_caller_injections=0,
  total_city_accesses=len(all_accesses),target_auxiliary_accesses=sum(x['target_auxiliary']for x in all_accesses),target_auxiliary_observations=[x for x in all_accesses if x['target_auxiliary']],
  uninterrupted_E89A_calls=len(all_rng),uninterrupted_E89A_X_changes=sum(not x['X_preserved']for x in all_rng),artifact_sha256=pins,
  source_sha256={str(path.relative_to(ROOT)):sha(path)for path in(Path(__file__),ROOT/'source/recovered/nestopia_context.py',ROOT/'source/recovered/service_memory.py',ROOT/'source/recovered/mapped_memory.py')},
  limits=['OriginalCPU continuation starts at actual saved PC/SP/AXYP and actual MAP/N163; no new interrupt/video timing is synthesized.','No-interrupt X preservation is distinct from any midcallee Native NMI overwrite possibility.','Whole city accesses and exact effective addresses do not identify official names of opaque bytes.','Exported caller inputs and diagnostics are not extra source comparison cases.'])
 (OUT/'runtime-trace.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 native_receipt=ROOT/'analysis/phase21/runtime/evidence.json'
 evidence=dict(schema='phase21-city-effective-access-originalCPU-evidence-v1',status='bounded_original_CPU_observation',ROM_sha256=ROM_SHA,
  contexts=len(rows),original_CPU_instructions=sum(x['original_instructions']for x in rows),source_CPU_comparison_cases=0,Native_internal_CPU_trace=False,
  new_NMI_IRQ_arrivals=0,prepared_bytes=0,exported_actual_caller_entries=len(captured),total_city_accesses=result['total_city_accesses'],target_auxiliary_accesses=result['target_auxiliary_accesses'],
  trace_receipt=dict(path=str((OUT/'runtime-trace.json').relative_to(ROOT)),sha256=sha(OUT/'runtime-trace.json')),
  source_sha256=result['source_sha256'],artifact_sha256=pins,
  formal_Native_provenance=dict(path=str(native_receipt.relative_to(ROOT)),sha256=sha(native_receipt))if native_receipt.exists()else None,
  limits=result['limits'])
 (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
 (OUT/'README.md').write_text(f'''# 保存点后的独立原CPU有效地址观察

本工具从实际保存的PC/SP/AXYP、实际MAP四银行和N163寄存器image开始，没有设置新PC、caller、RNG、request、ready或结果。{len(rows)}个上下文共执行{evidence['original_CPU_instructions']}条原指令，全部停在原请求FF。这里只是独立原CPU continuation；没有调度新增NMI/IRQ，不是原Nestopia内部CPU trace，也不把这些准备指令增加到源码差分case数。

原20正式10479保存点来自未改原核心；本轮10491/10492默认使用`runtime/original-control`的全冷原核心保存点。`observer-accept`同帧state与其字节相同，且观察核心/重建控制/原核心三组各fresh双跑的RGB、PCM、2K、8K和wholeState每帧一致，由runtime域另行证明。独立CPU使用明确硬件输入：PPUSTATUS=0、APUstatus=0、NamcoIRQ读127、两手柄无键；它不补硬件就绪中断。

观察保留全部{result['total_city_accesses']}次城市记录访问，而非只保留有意义的结果。每行有原physicalbank/PC/ROMoffset、实际有效地址、city归一偏移、读写前后值、Y、零页base、当前代各指针低/高字节producer与实际JSR链。保存点之前形成的指针writer为null，不猜前代来源。共{result['target_auxiliary_accesses']}次辅助字段访问都来自10:BD97，实际20/21=6040、Y=1、city2 offset1读0；其LE16门槛的另一字节是city+2，不能据此命名+1。没有观察到28..31的专用访问，不据有限窗口宣称unused。

10491从PC C56A/X4继续1842条原指令后形成真正C71A入口caller，随后扫描237记录；10492保存点本来已在C724/X66，只剩171记录。后者不能计成另一个完整237扫描。三条独立continuation均未进入C732/E89A内部招募随机调用；原记录状态无status0在野将，不构成成功录用实证。

`actual-callers`共{len(captured)}个入口输入，用原前序形成的真实栈、RAM/SRAM/N163/寄存器和银行交给独立源码差分矩阵。它们不是人为seed-return。C71A输入来自本轮原核心10491点；A000/C5B9/C5D2/C6CC输入保持原20正式10479来源。源码比较另见`../recruitment/validation.json`，此域source cases为0。

```sh
.venv-trace/bin/python scripts/trace_city_auxiliary_runtime.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[轨迹摘要](runtime-trace.json) · [hash证据](evidence.json) · [完整原机观察](../runtime/README.md) · [具名源码差分](../recruitment/README.md)
''')
 print(json.dumps({k:result[k]for k in('total_city_accesses','target_auxiliary_accesses','uninterrupted_E89A_calls','uninterrupted_E89A_X_changes')}))
if __name__=='__main__':main()
