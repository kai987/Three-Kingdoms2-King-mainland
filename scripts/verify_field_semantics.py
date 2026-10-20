#!/usr/bin/env python3
"""Validator-only original6502 comparison for direct affinity field consumers."""
from pathlib import Path
from collections import Counter
from importlib.metadata import version
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.field_semantics import AffinityFieldServices,CityUnresolvedFields,affinity_code,ROM_SHA256
from source.recovered.global_ui_controller import UIRegisters
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
from inspect_game_data import instruction
OUT=ROOT/'analysis/phase16/fields'
PARENT=ROOT/'analysis/phase12/runtime/battle-officer-info/info-open'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def memory(rom,pair,prep):
 m=ServiceMemory(rom,Path(str(PARENT)+'-ram.bin').read_bytes(),Path(str(PARENT)+'-sram.bin').read_bytes(),(16,pair,pair+1,31))
 # Existing fixture caller frame returns to E188. No production stack seed.
 m[0x1FE:0x200]=bytes([0x87,0xE1])
 for a,v in prep.items():m[a]=v
 m.io_reads=[];m.io_writes=[]
 return m
def verify(rom,quick=False):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 rows=[];failures=[];guards=[];executed=Counter();counts=Counter();rng=random.Random(0x16AFF1)
 def compare(entry,pair,prep,tag,flags=0x20,services=True,terrain=0):
  original=memory(rom,pair,prep);source_mem=memory(rom,pair,prep)
  regs=UIRegisters(a=terrain,x=1,y=61,p=flags,sp=253,pc=entry)
  if entry==0xA796:
   # A78C PHA terrain is a real input contract above the RTS frame.
   original[0x1FD]=terrain;source_mem[0x1FD]=terrain;regs.sp=252
  initial=vars(regs).copy();cpu=MPU(memory=original)
  for k,v in initial.items():setattr(cpu,k,v)
  source=AffinityFieldServices(source_mem,rom,SceneSharedServices(source_mem,rom)if services else None)
  try:
   result=source.run_entry(entry,registers=regs)
   for steps in range(100000):
    if steps and cpu.pc==regs.pc and cpu.sp==regs.sp:break
    b=original.banks[(cpu.pc-0x8000)//8192]if cpu.pc>=0x8000 else None
    if b is not None:executed[b,cpu.pc,16+b*8192+(cpu.pc&8191)]+=1
    cpu.step()
   else:raise RuntimeError(f'Original budget at{cpu.pc:04X}')
   ram=[(i,original.ram[i],source_mem.ram[i])for i in range(2048)if original.ram[i]!=source_mem.ram[i]]
   sram=[(i,original.sram[i],source_mem.sram[i])for i in range(8192)if original.sram[i]!=source_mem.sram[i]]
   different=[(k,getattr(cpu,k),getattr(regs,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(regs,k)]
   assert not ram and not sram and not different,dict(RAM=ram[:8],SRAM=sram[:8],registers=different)
   assert original.io_reads==source_mem.io_reads and original.io_writes==source_mem.io_writes and original.banks==source_mem.banks
   comparison='complete_return'if result['status']=='returned'else'strict_prefix'
   group={0xB630:'upper-glyph',0xB64D:'lower-glyph-prefix',0xA7E7:'player-movement',0xA796:'AI-movement-suffix',0xCB2F:'attack-terrain-suffix',0xD102:'formation-parameters',0xDD2F:'unit-affinity-and-hundred-troop-cache'}[entry]
   counts[group+'/'+comparison]+=1
   rows.append(dict(entry=entry,physical_pair=[pair,pair+1],tag=tag,comparison=comparison,
    completion_kind='actual_caller_RTS'if comparison=='complete_return'else'explicit_lower_glyph_boundary'if entry==0xB64D else'missing_fixed_service',
    source_status=result['status'],prepared_bytes=prep,input_registers=initial,final_registers=vars(regs).copy(),
    original_instructions=steps,all_RAM_byte_count=2048,all_SRAM_byte_count=8192,original_CPU_helper_callbacks=0,
    upper_or_lower_glyph_pair=list(source_mem[0x38B:0x38D])if entry in(0xB630,0xB64D)else None,
    formation_parameters=list(source_mem[0x550:0x558])if entry==0xD102 else None,
    ports_reads=len(original.io_reads),ports_writes=len(original.io_writes),final_banks=list(original.banks)))
  except Exception as exc:
   failures.append(dict(entry=entry,tag=tag,error=str(exc),source_pc=regs.pc))
   if len(failures)<8:print(json.dumps(failures[-1]),flush=True)
 base=0x63C0+12*131
 for flags in range(0,256,16 if quick else 1):
  for entry in(0xB630,0xB64D):compare(entry,25,{0x10:base&255,0x11:base>>8,base+11:flags},f'flag-byte{flags}',flags=0xE5 if flags&1 else 0x20)
 for affinity in range(4):
  for terrain in range(7):
   for cache in(0,5,6,255):
    for AP in(0,1,4,24,255):
     compare(0xA7E7,12,{0x509:10,0x664+10:131,base+11:0x73|(affinity<<2),0x63C+10:cache,0x505:AP},f'affinity{affinity}/terrain{terrain}/cache{cache}/AP{AP}',terrain=terrain,flags=0xE5)
   for low in((0,2,3)if quick else(0,1,2,3,88,89,90,100,255)):
    for AP in(0,24):
     compare(0xA796,8,{0x20:base&255,0x21:base>>8,base+11:0x72|(affinity<<2),base+8:low,base+9:rng.randrange(256),0x505:AP},f'affinity{affinity}/terrain{terrain}/raw-low{low}/AP{AP}',terrain=terrain,flags=0xE5)
  for terrain in(0,2,3,4):
   for obj in(0,10,11,21):
    compare(0xCB2F,14,{0x545:obj,0x560:131,0x561:47,base+11:0x72|(affinity<<2),0x63C0+12*47+11:0x31|(affinity<<2)},f'affinity{affinity}/terrain{terrain}/object{obj}',terrain=terrain,flags=0xE5)
  for bg in range(8):
   for out in(0,4):
    for strength in(0,3,4,5,6,255):
     for available in(0,1):
      prep={0xC:131,base+11:0x73|(affinity<<2),0x544:bg,0x57A:strength}
      prep.update({0x580+i:0 if available else 255 for i in range(1,11)})
      compare(0xD102,14,prep,f'affinity{affinity}/background{bg}/output{out}/strength{strength}/available{available}',terrain=out,flags=0xE5)
 for case in range(8 if quick else 128):
  prep={}
  for slot in range(20):
   officer=(case*19+slot*11)%237;prep[0x664+slot]=255 if(case+slot)%7==0 else officer
   ptr=0x63C0+12*officer;prep[ptr+11]=rng.randrange(256);prep[ptr+8]=rng.randrange(256);prep[ptr+9]=rng.randrange(256)
   for area in(0x600,0x614,0x628,0x63C,0x650):prep[area+slot]=rng.randrange(256)
  compare(0xDD2F,12,prep,f'20-slot-cache-fixture{case}',flags=0xE5)
 compare(0xA7E7,12,{0x509:10,0x664+10:131},'missing-F2D7',services=False)
 def reject(name,fn):
  try:fn()
  except(ValueError,RuntimeError):guards.append(dict(name=name,status='passed'));return
  raise AssertionError(name)
 reject('flag-byte-required',lambda:affinity_code(256))
 reject('city32byte-record-required',lambda:CityUnresolvedFields(bytes(31)))
 reject('city30-outside-original-records',lambda:CityUnresolvedFields.from_memory(memory(rom,25,{}),30))
 reject('actual-registers-required',lambda:AffinityFieldServices(memory(rom,25,{}),rom).run_entry(0xB630))
 reject('wrong-physical-bank',lambda:AffinityFieldServices(memory(rom,12,{}),rom).run_entry(0xB630,registers=UIRegisters()))
 reject('no-production-stack-seed',lambda:AffinityFieldServices(memory(rom,25,{}),rom).run_entry(0xB630,registers=UIRegisters(),seed_return=True))
 for status in(None,'waiting','error','blocked'):
  m=memory(rom,12,{0x509:10,0x664+10:131})
  def counterfeit(call,status=status):
   call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
   return None if status is None else{'status':status}
  result=AffinityFieldServices(m,rom,counterfeit).run_entry(0xA7E7,registers=UIRegisters())
  assert result['status']=='dependency'and result['pending']is not None
  guards.append(dict(name=f'no-counterfeit-return-{status}',status='passed'))
 OUT.mkdir(parents=True,exist_ok=True)
 inst=[]
 for(bank,pc,off),count in sorted(executed.items()):
  size,asm=instruction(rom,off,pc);inst.append(dict(physical_bank=bank,cpu=pc,rom_offset=off,raw_hex=rom[off:off+size].hex(' ').upper(),assembly=asm,count=count))
 (OUT/'executed-instructions.json').write_text(json.dumps(inst,indent=2)+'\n')
 complete=sum(x['comparison']=='complete_return'for x in rows)
 pins=[ROOT/'source/recovered/field_semantics.py',ROOT/'source/recovered/global_ui_controller.py',ROOT/'source/recovered/scene_shared_services.py',ROOT/'source/recovered/controller_helpers.py',ROOT/'source/recovered/battle_nmi_services.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'source/recovered/service_memory.py',Path(__file__)]
 receipt=dict(schema='phase16-field-semantics-original-CPU-v1',status='passed'if not failures else'failed',ROM_sha256=ROM_SHA256,
  rom_cpu_case_count=len(rows),source_guard_case_count=len(guards),total_complete_return_CPU_cases=complete,total_strict_prefix_CPU_cases=len(rows)-complete,
  case_count=len(rows)+len(guards),failed_count=len(failures),group_case_counts=dict(counts),rows=rows,guards=guards,failures=failures,
  scope=dict(RAM_byte_count=2048,RAM_addresses='0000..07FF including inactive caller stack',SRAM_byte_count=8192,registers=['A','X','Y','P','SP','PC'],banks=True,ordered_IO_reads=True,ordered_IO_writes=True,
   original_CPU_helper_callbacks=0,source_original_CPU_callbacks=0,source_control_IR_callbacks=0,native_internal_CPU_trace=False),
  fixture_domains=dict(code3='Explicit non-initial-record boundary input; no natural producer claimed',lower_glyph='StopsB663 before troop/UI fallthrough, not a complete original function',AI_movement='Actual suffix stack contract includes caller-PHA terrain; raw byte9 varied independently',terrain_suffix='Original caller excludes0/1/5; direct0 invokes boundary suffix mechanically',formation='Background0..7/output0or4; code3 and strength255 are explicit boundary data',cache='20mixed valid/empty slots; all four affinity codes are direct field inputs'),
  original_dynamically_executed_positions=len(executed),source_path='source/recovered/field_semantics.py',source_sha256=sha(pins[0]),validator_path='scripts/verify_field_semantics.py',validator_sha256=sha(__file__),
  independent_oracle='py65 MPU6502 validator-only',independent_oracle_version=version('py65'),source_and_validator_sha256={str(p.relative_to(ROOT)):sha(p)for p in pins},
  parent_snapshot_sha256={str(p.relative_to(ROOT)):sha(p)for p in(Path(str(PARENT)+'-ram.bin'),Path(str(PARENT)+'-sram.bin'))})
 (OUT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:receipt[k]for k in('status','rom_cpu_case_count','total_complete_return_CPU_cases','total_strict_prefix_CPU_cases','source_guard_case_count','failed_count')}),flush=True)
 if failures:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();verify(a.rom.read_bytes(),a.quick)
