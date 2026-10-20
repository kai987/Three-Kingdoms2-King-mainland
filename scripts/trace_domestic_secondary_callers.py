#!/usr/bin/env python3
"""Continue captured Native REG/RAM/SRAM/MAP/N163 through originalCPU only.

The saved PC is used as-is. Hardware reads are explicit; this script does not
schedule NMI/IRQ, synthesize readiness or turn an unknown wait into a return.
Captured B5FC/branch caller inputs can initialize independent source comparisons.
It does not claim an internal Native instruction trace or matching video timing.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import NestopiaContext
from source.recovered.domestic_secondary_services import ROM_SHA256
OUT=ROOT/'analysis/phase19/cpu/actual-callers';REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registers(c):return{k:getattr(c,k)for k in REGS}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--max-states',type=int,default=240);p.add_argument('--instruction-budget',type=int,default=200000);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 paths=list((ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window').glob('AI-ruler*-status00-*.state'))+list((ROOT/'analysis/phase15/runtime/cold-yearwrap').glob('AI-ruler*-status00-*.state'))
 found={};rows=[];pins={};visited=Counter()
 for path in paths[:a.max_states]:
  native=NestopiaContext.parse(path.read_bytes());m=native.service_memory(rom,read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0));c=MPU(memory=m)
  for k,v in native.registers.items():setattr(c,k,v)
  watch=[];stop=None;chain=[]
  for n in range(a.instruction_budget):
   bank=m.banks[(c.pc-0x8000)//8192]if c.pc>=0x8000 else None
   visited[bank,c.pc]+=1
   if bank==10 and c.pc in(0xB49C,0xB49F,0xB5FC,0xB5FF,0xB619,0xB98B,0xBBB2):
    watch.append(dict(step=n,physical_bank=bank,pc=c.pc,registers=registers(c),request=m[0x6F8B],ruler=m[0x6F03]))
    if c.pc in(0xB5FC,0xB619,0xB98B,0xBBB2)and c.pc not in found:
     folder=OUT/f'entry-{c.pc:04X}';folder.mkdir(exist_ok=True);(folder/'input-ram.bin').write_bytes(m.ram);(folder/'input-sram.bin').write_bytes(m.sram);(folder/'input-n163.bin').write_bytes(m.n163_ram)
     meta=dict(schema='phase19-Native-context-originalCPU-callee-input-v1',Native_internal_CPU_trace=False,native_state_path=str(path.relative_to(ROOT)),native_state_sha256=sha(path),captured_native_registers=native.registers,captured_native_prg_banks=list(native.prg_banks),captured_native_ram_sha256=hashlib.sha256(native.ram).hexdigest(),captured_native_sram_sha256=hashlib.sha256(native.sram).hexdigest(),original_CPU_prefix_instructions=n,explicit_NMI_IRQ_arrivals=0,postcapture_memory_injections=0,registers=registers(c),physical_banks=list(m.banks),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,existing_return_PC=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535,known_prefix_JSR_chain=chain[-12:],hardware=dict(PPUSTATUS=0,APUSTATUS=0,NamcoIRQread=127,controllers=[0,0]))
     (folder/'context.json').write_text(json.dumps(meta,indent=2)+'\n');found[c.pc]=str(folder.relative_to(ROOT));print(json.dumps(dict(found=hex(c.pc),native=str(path.relative_to(ROOT)),prefix=n)),flush=True)
   if all(k in found for k in(0xB5FC,0xB619,0xB98B,0xBBB2))and c.pc in(0xB619,0xB98B,0xBBB2):stop='all_requested_original_caller_inputs_captured';break
   if m[0x6F8B]in(248,249,250):stop='genuine_software_request_wait';break
   if m[0x6F8B]==255:stop='original_request_FF';break
   if c.pc==0xFB28:stop='hardware_IRQ_wait_requires_external_arrival';break
   oldpc,oldsp=c.pc,c.sp;op=m[c.pc];target=m[(c.pc+1)&65535]|m[(c.pc+2)&65535]<<8 if op==0x20 else None
   c.step()
   if op==0x20:chain.append(dict(call_pc=oldpc,target=target,return_pc=oldpc+3,caller_sp=oldsp))
   elif op==0x60:
    ix=next((i for i in range(len(chain)-1,-1,-1)if chain[i]['return_pc']==c.pc and chain[i]['caller_sp']==c.sp),None)
    if ix is not None:del chain[ix:]
  else:stop='explicit_instruction_budget'
  rows.append(dict(native_state=str(path.relative_to(ROOT)),native_sha256=sha(path),initial_registers=native.registers,actual_MAP_PRG_banks=list(native.prg_banks),RAM_bank_shadows=list(native.ram[0xDE:0xE1])+[31],original_CPU_prefix_instructions=n,watch=watch,stop=stop,final_registers=registers(c),final_request=m[0x6F8B]));pins[str(path.relative_to(ROOT))]=sha(path)
  if len(found)==4:break
 for p in OUT.rglob('*'):
  if p.is_file()and p.name!='discovery.json':pins[str(p.relative_to(ROOT))]=sha(p)
 receipt=dict(schema='phase19-saved-Native-context-original-caller-discovery-v1',status='bounded_discovery_complete',rom_sha256=ROM_SHA256,contexts=rows,contexts_examined=len(rows),captured_original_callers={f'{k:04X}':v for k,v in found.items()},postcapture_memory_injections=0,explicit_NMI_IRQ_arrivals=0,source_comparisons_counted_elsewhere=True,Native_internal_CPU_trace=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__),'source/recovered/nestopia_context.py':sha(ROOT/'source/recovered/nestopia_context.py'),'source/recovered/service_memory.py':sha(ROOT/'source/recovered/service_memory.py'),'source/recovered/mapped_memory.py':sha(ROOT/'source/recovered/mapped_memory.py')},limitations=['SavedNative PC/SP/AXYP, actualPRGbanks andN163 initialize each independentCPU continuation.','Later hardware/timing state is explicit, no NMI/IRQ arrival is synthesized.','Requests/waits/instructionbudget remain boundaries, not assumed completion.','The prefix is independent originalCPU execution, not Nativeinternal perinstruction recording.','Capturedcallee comparisons are separately counted; these prefixes are not additional complete source cases.'])
 (OUT/'discovery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(contexts=len(rows),found=receipt['captured_original_callers'])))
if __name__=='__main__':main()
