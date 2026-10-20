#!/usr/bin/env python3
"""Compare named services at real JSR inputs reached from a Native snapshot.

The independent original CPU continues the captured context without injecting
an entry PC or return frame. Its exported caller inputs are not a Native trace.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import CapturedServiceMemory
from source.recovered.negotiation_services import NegotiationServices,UIRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from verify_domestic_secondary_services import clone,reg
OUT=ROOT/'analysis/phase20/cpu'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 rows=[];inputs={}
 for folder in sorted((OUT/'actual-callers').iterdir()):
  context=json.loads((folder/'context.json').read_text());initial=context['registers']
  for p in folder.iterdir():inputs[str(p.relative_to(ROOT))]=sha(p)
  assert not context['synthetic_caller_or_PC_or_RNG_or_request_preparation']
  assert context['prepared_numeric_bytes']==[] and context['original_CPU_prefix_instructions']>0
  m=CapturedServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),context['physical_banks'],read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=context['N163_address'];m.n163_autoincrement=context['N163_autoincrement']
  left,right=clone(m),clone(m);c=MPU(memory=left);r=UIRegisters(**initial)
  for key,value in initial.items():setattr(c,key,value)
  service=NegotiationServices(right,rom,SceneSharedServices(right,rom));out=service.run_entry(initial['pc'],registers=r)
  for steps in range(1500000):
   if steps and(c.pc,c.sp)==(r.pc,r.sp)and(out['status']=='returned'or reg(c)==reg(r)):break
   assert c.pc>=0x8000,(folder.name,c.pc);c.step()
  else:raise RuntimeError((folder.name,'original CPU budget'))
  assert bytes(left.ram)==bytes(right.ram)and bytes(left.sram)==bytes(right.sram),folder.name
  assert reg(c)==reg(r)and left.io_reads==right.io_reads and left.io_writes==right.io_writes,folder.name
  assert left.banks==right.banks and left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,folder.name
  assert out['status']in('returned','waiting'),(folder.name,out)
  if out['status']=='returned':assert r.pc==context['existing_return_PC']
  if out['status']=='waiting':
   before=(bytes(right.ram),bytes(right.sram),reg(r));again=service.resume()
   assert again['status']=='waiting'and before==(bytes(right.ram),bytes(right.sram),reg(r))
  rows.append(dict(case=folder.name,input_context=str((folder/'context.json').relative_to(ROOT)),initial_registers=initial,final_registers=reg(r),original_CPU_instructions=steps,completion=out['status'],existing_return_PC=context['existing_return_PC'],prepared_bytes=[],all_RAM_2048_SRAM_8192_registers_IO_banks_N163_equal=True,source_original_CPU_callbacks=0,Native_internal_CPU_trace=False))
 assert len(rows)==8
 sources={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')};sources[str(Path(__file__).relative_to(ROOT))]=sha(__file__);sources['scripts/verify_domestic_secondary_services.py']=sha(ROOT/'scripts/verify_domestic_secondary_services.py')
 result=dict(schema='phase20-real-caller-named-source-differential-v1',status='passed',ROM_sha256=ROM_SHA256,original_CPU_parent_cases=len(rows),returned_count=sum(r['completion']=='returned'for r in rows),waiting_count=sum(r['completion']=='waiting'for r in rows),rows=rows,source_sha256=sources,input_sha256=inputs,source_original_CPU_callbacks=0,production_IR_interpretation=False,limits=['Caller inputs are reached by an independent original CPU from a formal Native snapshot; they are not original-core instruction traces.','No entry or caller-stack preparation is introduced; memory, registers, physical banks and N163 state are copied from the exported inputs.','A pending offer remains pending; no fake reply is supplied.'])
 (OUT/'actual-caller-source-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','original_CPU_parent_cases','returned_count','waiting_count')}))
if __name__=='__main__':main()
