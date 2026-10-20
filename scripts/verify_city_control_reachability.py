#!/usr/bin/env python3
"""Independent ROMCPU check of the bounded phase18 inline control extents.

All-zero RAM/SRAM and explicit registers are validator fixtures. These cases
stop at the original dispatch destination, not at a callee RTS, and are neither
Native CPU traces nor recovered-source equivalence cases.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.service_memory import ServiceMemory
from inspect_game_data import OPS,SIZES
OUT=ROOT/'analysis/phase18/control'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regs(c):return{k:getattr(c,k)for k in('a','x','y','p','sp','pc')}
def run(rom):
 contract_path=OUT/'control-contracts.json';atlas_path=OUT/'instruction-atlas.json'
 contract=json.loads(contract_path.read_text());atlas=json.loads(atlas_path.read_text())
 assert hashlib.sha256(rom).hexdigest()==contract['ROM_sha256']
 assert atlas['source_contracts_sha256']==sha(contract_path)
 rows=[];table_bytes=set()
 for item in contract['bounded_dispatch_tables']+contract['global_tables']:
  t=item['table'];blob=bytes.fromhex(t['raw_hex']);assert rom[t['rom_offset']:t['rom_offset']+len(blob)]==blob
  assert len(blob)==2*len(item['targets'])
  assert [int.from_bytes(blob[i:i+2],'little')for i in range(0,len(blob),2)]==item['targets']
  table_bytes.update((t['physical_bank'],p)for p in range(t['cpu'],t['end_cpu_exclusive']))
 for node in atlas['instructions']:
  blob=bytes.fromhex(node['raw_hex']);assert rom[node['rom_offset']:node['rom_offset']+node['size']]==blob
  assert not any((node['physical_bank'],p)in table_bytes for p in range(node['cpu'],node['cpu']+node['size']))
 for item in contract['bounded_dispatch_tables']:
  call=item['call'];pair=call['physical_bank']-int(call['cpu']>=0xC000)
  for index,target in enumerate(item['targets']):
   memory=ServiceMemory(rom,bytes(0x800),bytes(0x2000),(2,pair,pair+1,31))
   c=MPU(memory=memory);c.a=index;c.x=117;c.y=83;c.p=33;c.sp=253;c.pc=call['cpu']
   initial=regs(c);trace=[]
   for steps in range(80):
    if steps and c.pc==target:break
    bank=memory.banks[(c.pc-0x8000)//8192]
    offset=16+bank*8192+(c.pc&8191);op,mode=OPS[rom[offset]];size=SIZES[mode]
    trace.append(dict(physical_bank=bank,cpu=c.pc,ROM_offset=offset,raw_hex=rom[offset:offset+size].hex(),opcode=op,mode=mode,registers=regs(c)))
    c.step()
   else:raise AssertionError((call,index,target,regs(c)))
   assert c.sp==initial['sp'] and c.x==initial['x'] and c.y==initial['y']
   assert not memory.io_reads and not memory.io_writes
   rows.append(dict(physical_bank=call['physical_bank'],call_PC=call['cpu'],selector=index,
      destination=target,initial_registers=initial,final_registers=regs(c),instructions=trace,
      boundary='original_computed_dispatch_destination',actual_caller_RTS=False,
      RAM_sha256=hashlib.sha256(bytes(memory.ram)).hexdigest(),SRAM_sha256=hashlib.sha256(bytes(memory.sram)).hexdigest()))
 result=dict(schema='phase18-original-CPU-bounded-control-verification-v1',status='passed',ROM_sha256=contract['ROM_sha256'],
   dependencies_sha256={'analysis/phase18/control/control-contracts.json':sha(contract_path),'analysis/phase18/control/instruction-atlas.json':sha(atlas_path),
     'scripts/verify_city_control_reachability.py':sha(Path(__file__)),'source/recovered/service_memory.py':sha(ROOT/'source/recovered/service_memory.py'),
     'source/recovered/mapped_memory.py':sha(ROOT/'source/recovered/mapped_memory.py')},
   inline_table_count=len(contract['bounded_dispatch_tables']),original_CPU_dispatch_destination_case_count=len(rows),
   global_static_table_count=len(contract['global_tables']),raw_instruction_positions_verified=len(atlas['instructions']),rows=rows,
   fixture=dict(RAM='all-zero 2048 bytes',SRAM='all-zero 8192 bytes',A='each bounded original table index',X=117,Y=83,P=33,SP=253),
   limitations=dict(original_Native_internal_CPU_trace=False,recovered_source_comparison=False,actual_caller_RTS_count=0,
    no_raw_selector_outside_declared_extent_claim=True,global_tables_static_only=True,city_field_names_proved=False))
 (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','inline_table_count','original_CPU_dispatch_destination_case_count','raw_instruction_positions_verified')}))
if __name__=='__main__':run(Path(sys.argv[1]).read_bytes())
