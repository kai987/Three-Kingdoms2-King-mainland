#!/usr/bin/env python3
"""Original6502 differential checks for exact name packets and F308.

The production side uses only independent source services. Six saved callee
inputs preserve the real EE07 frame, rather than seeding an entry sentinel.
All other comparisons are explicitly prepared CPU fixtures, not native video.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_scene_controller import ObservableBus
from source.recovered.officer_ui_services import OfficerUIServices,ROM_SHA256
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.scene_initialization import SceneInitialization
from source.recovered.service_memory import ServiceMemory

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(rom,out,quick=False):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 parent=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(parent)+'-ram.bin').read_bytes();sram=Path(str(parent)+'-sram.bin').read_bytes()
 counts=Counter();failures=[];rows=[];guards=[];visited=Counter();callback_counts=Counter();rng=random.Random(0x12F308);snapshot_pins=[]
 def bus(initial_ram,initial_sram,banks):
  b=ObservableBus(rom,initial_ram,initial_sram);b.banks=list(banks);b.bank_initialized=[True]*4;b.protect=0x4C;b.ports=[];b.port_reads=[];return b
 def fresh(prep,sp,stop):
  b=bus(ram,sram,(17,29,30,31));b.ram[0xDE:0xE4]=bytes([49,61,62,49,61,62])
  for address,value in prep.items():b[address]=value
  ret=(stop-1)&65535;b.ram[0x100+((sp+1)&255)]=ret&255;b.ram[0x100+((sp+2)&255)]=ret>>8;b.ports=[];return b
 def pure_router(memory):
  owners={}
  def callback(call):
   callback_counts[call.target]+=1
   if call.target==0xA015 and tuple(call.entry_banks[1:3])==(29,30):
    if id(call)not in owners:owners[id(call)]=SceneInitialization(memory,rom,callbacks=callback)
    return owners[id(call)].banked_graphics(call)
   if id(call)not in owners:owners[id(call)]=SceneSharedServices(memory,rom,callbacks=callback)
   return owners[id(call)](call)
  return callback
 def compare(kind,entry,prep=None,regs=None,snapshot=None):
  initial=dict(a=17,x=31,y=63,p=32,sp=253,pc=entry);initial.update(regs or{})
  if snapshot:
   meta=json.loads(snapshot.read_text());prefix=str(snapshot)[:-5]
   a=bus(Path(prefix+'-ram.bin').read_bytes(),Path(prefix+'-sram.bin').read_bytes(),meta['entry_banks']);initial.update(meta['registers_before'])
   assert digest(prefix+'-ram.bin')==meta['RAM_sha256']and digest(prefix+'-sram.bin')==meta['SRAM_sha256']
  else:a=fresh(prep or{},initial['sp'],0x2200+(initial['x']&15))
  b=bus(a.ram,a.sram,a.banks);b.ram[:]=a.ram;registers=NMIRegisters(**initial)
  model=OfficerUIServices(b,rom,pure_router(b));cpu=MPU(memory=a);a.cpu=cpu
  for k,v in initial.items():setattr(cpu,k,v)
  try:
   if snapshot:
    sp=initial['sp'];ret=((a.ram[0x100+((sp+1)&255)]|a.ram[0x100+((sp+2)&255)]<<8)+1)&65535
    result=model(ServiceCall(entry,ret,'far_callee',registers,b,tuple(b.banks),(sp+2)&255))
   else:result=model.run_entry(entry,registers)
   assert result['status']=='returned',result
   for n in range(150000):
    if n and cpu.pc==registers.pc and cpu.sp==registers.sp and a.banks==b.banks:break
    origin=a.origin(cpu.pc)
    if origin:visited[(origin[0],cpu.pc,origin[1]+16)]+=1
    a.pc=cpu.pc;a.step_no=n;cpu.step()
   else:raise RuntimeError(f'Original budget ${cpu.pc:04X}')
   rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y]
   rg={k:(getattr(cpu,k),getattr(registers,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(registers,k)}
   assert not rd and not rg and bytes(a.sram)==bytes(b.sram),dict(RAM=rd[:12],registers=rg)
   assert a.ports==b.ports and a.port_reads==b.port_reads,dict(original_ports=a.ports,source_ports=b.ports)
   if entry!=0xA036:assert b.banks[0]==16,('name bank',b.banks)
   counts[kind]+=1;rows.append(dict(kind=kind,entry=entry,input_registers=initial,preparation=prep,
    actual_caller_snapshot=str(snapshot.relative_to(ROOT))if snapshot else None,comparison='complete_return',
    original_instructions=n,final_registers=vars(registers),final_banks=b.banks,
    packet_sha256=hashlib.sha256(b.ram[0x380:0x3BB]).hexdigest(),port_writes=len(b.ports)))
  except Exception as exc:
   failures.append(dict(kind=kind,entry=entry,regs=initial,prep=prep,snapshot=str(snapshot)if snapshot else None,error=str(exc)))
   if len(failures)<=12:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
 ids=range(8)if quick else range(256);jobs=(0,1)if quick else(0,1,4,255)
 for ident in ids:
  for flags in jobs:
   p=32|(ident&199);regs=dict(a=ident,x=ident^165,y=flags,p=p,sp=(253 if flags<4 else 246))
   compare('fixed_F308_all_identifier_bytes',0xF308,{0x7E:flags},regs)
   if ident<237:
    compare('left_name_all237',0xA030,{0:ident,0x7E:flags},regs)
    for side in(0,1):compare('participant_name_all237_both_sides',0xA03C,{0:ident,1:side,0x7E:flags},regs)
  if ident<237:
   compare('duel_name_all237',0xA033,{0x4AE:ident,0x7E:(ident*73)&255},dict(p=32|(ident&199)))
   for slot in(0,10,19):compare('selected_unit_name_all237_three_slots',0xA027,{0x509:slot,0x664+slot:ident,0x7E:ident},dict(x=slot))
   for helper in(0xA957,0xA976):compare('direct_mark_and_glyph_helpers',helper,{},dict(a=ident,p=32|(ident&199)))
 for byte in(range(8)if quick else range(256)):
  compare('attribute_buffer_clear_all_flags',0xA036,{0x7E:byte},dict(a=byte,x=byte,y=255-byte,p=32|(byte&215)))
 for ident in(0,1,47,131,236):
  compare('palette_wrapper_with_independent_source_callee',0xA02A,{0:ident,0x7E:1},dict(a=127,x=37,y=19,p=99))
 for snapshot in sorted((ROOT/'analysis/phase12/dependencies/callee-inputs').glob('bank29-A0[3][0C]-*.json')):
  meta=json.loads(snapshot.read_text());compare('original_EE07_callee_frames',meta['cpu_address'],snapshot=snapshot)
  for f in(snapshot,Path(str(snapshot)[:-5]+'-ram.bin'),Path(str(snapshot)[:-5]+'-sram.bin')):snapshot_pins.append(dict(path=str(f.relative_to(ROOT)),sha256=digest(f)))
 # Source guards are separate from originalCPU comparisons. Never fake an ack.
 for bad in(0,0xA039,0xF307):
  b=fresh({},253,0x2200);model=OfficerUIServices(b,rom)
  try:model.run_entry(bad);ok=False
  except ValueError:ok=True
  assert ok;guards.append('unknown_entry_'+hex(bad))
 for outcome in(None,{'status':'waiting'},{'status':'error'},{'status':'blocked'},{'status':'returned'}):
  b=fresh({0:131},253,0x2200);model=OfficerUIServices(b,rom)
  def callback(call,value=outcome):
   if value!= {'status':'returned'}:call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
   return value
  model.callbacks=callback;result=model.run_entry(0xA02A,NMIRegisters(sp=253))
  assert result['status']=='dependency' and isinstance(model.pending,ServiceCall)
  guards.append('strict_callback_'+('None'if outcome is None else outcome['status']))
 b=fresh({0:131},253,0x2200);model=OfficerUIServices(b,rom);regs=NMIRegisters(sp=253)
 result=model.run_entry(0xA02A,regs);assert result['status']=='dependency';saved=bytes(b.ram);ports=list(b.ports)
 for _ in range(3):assert model.resume()['status']=='dependency' and bytes(b.ram)==saved and b.ports==ports
 model.callbacks=pure_router(b);assert model.resume()['status']=='returned';guards.append('pending_real_far_call_resumes_without_repeated_prefix')
 b=fresh({},253,0x2200);model=OfficerUIServices(b,rom);r=NMIRegisters(pc=0xA030,sp=253)
 assert model(ServiceCall(0xA030,0x2200,'call',r,b,(17,14,15,31),255))['status']=='dependency';guards.append('banked_entry_wrong_pair_is_not_owned')
 out.mkdir(parents=True,exist_ok=True)
 pins=[dict(path=f,sha256=digest(ROOT/f))for f in('source/recovered/officer_ui_services.py','source/recovered/battle_nmi_services.py','source/recovered/scene_shared_services.py','source/recovered/scene_initialization.py','source/recovered/service_memory.py','scripts/verify_officer_ui_services.py','scripts/verify_battle_scene_controller.py')]+snapshot_pins
 d=dict(schema='phase12-officer-UI-actual-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=quick,
  rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,
  source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,guards=guards,rows=rows,
  production_original_CPU_callbacks=0,production_IR_interpretation=False,verification_only_original_CPU_callback_count=0,
  independent_source_service_calls={hex(k):v for k,v in callback_counts.items()},
  all_RAM_compared_bytes=2048,all_SRAM_compared_bytes=8192,AXYPSPPC_compared=True,
  ordered_ports_reads_banks_compared=True,source_and_validator_pins=pins,
  native_internal_CPU_trace=False,native_video_cases_in_this_receipt=0,
  scope='Source calls are independent. Snapshot cases are actual original-helper boundaries of controlled CPU fixtures, not native callee traces. Oracle flags use D=0; native2A03 has no decimal arithmetic.')
 (out/'validation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=bank,cpu_address=pc,rom_offset=offset,count=n)for(bank,pc,offset),n in sorted(visited.items())],indent=2)+'\n')
 print(json.dumps({k:d[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')}))
 if failures:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase12/officer-ui');a=p.parse_args();verify(a.rom.read_bytes(),a.out,a.quick)
