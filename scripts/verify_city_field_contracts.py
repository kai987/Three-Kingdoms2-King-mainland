#!/usr/bin/env python3
"""Validator-only actual6502 comparison for phase17 city field contracts."""
from pathlib import Path
from collections import Counter
from importlib.metadata import version
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_field_contracts import CityFieldContracts,CityAuxiliaryContract,peaceful_transfer_goal,ROM_SHA256
from source.recovered.global_ui_controller import UIRegisters
from source.recovered.city_ui_controller import CityUIController,CityRegisters
from source.recovered.service_memory import ServiceMemory
from inspect_game_data import instruction
OUT=ROOT/'analysis/phase17/fields';PARENT=ROOT/'analysis/phase12/runtime/battle-officer-info/info-open'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
class ReadEvidenceMemory(ServiceMemory):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.SRAM_reads=[];self.SRAM_writes=[]
 def __getitem__(self,a):
  value=super().__getitem__(a)
  if isinstance(a,int)and 0x6000<=a<0x8000:self.SRAM_reads.append({'address':a,'value':value})
  return value
 def __setitem__(self,a,v):
  if isinstance(a,int)and 0x6000<=a<0x8000:self.SRAM_writes.append({'address':a,'value':v&255})
  super().__setitem__(a,v)
def memory(rom,pair,prep):
 m=ReadEvidenceMemory(rom,Path(str(PARENT)+'-ram.bin').read_bytes(),Path(str(PARENT)+'-sram.bin').read_bytes(),(16,pair,pair+1,31))
 m[0x1FE:0x200]=bytes([0x87,0xE1])
 for a,v in prep.items():m[a]=v
 m.io_reads=[];m.io_writes=[];m.SRAM_reads=[];m.SRAM_writes=[]
 return m
def assert_equal(original,source,cpu,regs):
 assert original.ram==source.ram,[(i,a,b)for i,(a,b)in enumerate(zip(original.ram,source.ram))if a!=b][:8]
 assert original.sram==source.sram,[(i,a,b)for i,(a,b)in enumerate(zip(original.sram,source.sram))if a!=b][:8]
 assert all(getattr(cpu,k)==getattr(regs,k)for k in('a','x','y','p','sp','pc')),dict(original={k:getattr(cpu,k)for k in('a','x','y','p','sp','pc')},source=vars(regs))
 assert original.io_reads==source.io_reads and original.io_writes==source.io_writes and original.banks==source.banks
 assert original.SRAM_reads==source.SRAM_reads and original.SRAM_writes==source.SRAM_writes

def verify(rom,quick=False):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 rows=[];failures=[];guards=[];executed=Counter();rng=random.Random(0x170C17)
 def original_until(original,regs,executed,min_reads=0):
  cpu=MPU(memory=original)
  for k,v in vars(regs).items():setattr(cpu,k,v)
  def run(target,minimum=0):
   for steps in range(100000):
    if steps and cpu.pc==target.pc and cpu.sp==target.sp and len(original.SRAM_reads)>=minimum:break
    if cpu.pc>=0x8000:
     b=original.banks[(cpu.pc-0x8000)//8192];executed[b,cpu.pc]+=1
    cpu.step()
   else:raise RuntimeError(f'Original budget at{cpu.pc:04X}')
   return steps
  return cpu,run
 def compare(entry,pair,prep,tag,a=0,x=61,y=83,p=0x20,group=None,city_controller=False):
  original=memory(rom,pair,prep);source=memory(rom,pair,prep)
  regs=UIRegisters(a=a,x=x,y=y,p=p,sp=253,pc=entry);initial=vars(regs).copy()
  cpu,run=original_until(original,regs,executed)
  service=CityUIController(source,rom,CityFieldContracts(source,rom))if city_controller else CityFieldContracts(source,rom)
  try:
   result=service.run_entry(entry,registers=regs)
   steps=run(regs,len(source.SRAM_reads));assert_equal(original,source,cpu,regs)
   kind='complete_return'if result['status']=='returned'else'strict_prefix'
   row=dict(entry=entry,pair=[pair,pair+1],group=group or f'{entry:04X}',tag=tag,comparison=kind,
     completion_kind='actual_caller_RTS'if kind=='complete_return'else'real_scan_cycle_without_terminator'if result['status']=='waiting'else'explicit_prefix_boundary',
     source_status=result['status'],initial_registers=initial,final_registers=vars(regs).copy(),
     all_RAM_byte_count=2048,all_SRAM_byte_count=8192,ordered_SRAM_reads=len(original.SRAM_reads),ordered_SRAM_writes=len(original.SRAM_writes),
     original_CPU_instructions=steps,original_CPU_helper_callbacks=0,source_original_CPU_callbacks=0)
   if entry in(0xA442,0xC21D):
    citybase=(prep.get(0x20,0)|prep.get(0x21,0)<<8)if entry==0xA442 else(prep.get(0,0)|prep.get(1,0)<<8)
    row['city_record_reads']=[q for q in original.SRAM_reads if citybase<=q['address']<citybase+256]
    row['city_record_writes']=list(original.SRAM_writes)
   if entry==0xA442 and result['status']=='waiting':
    address=0x6080+28;original[address]=source[address]=255
    original.SRAM_writes=[];source.SRAM_writes=[]
    original.SRAM_reads=[];source.SRAM_reads=[]
    resumed=service.resume();steps2=run(regs,len(source.SRAM_reads));assert_equal(original,source,cpu,regs)
    assert resumed['status']=='bounded_prefix'and regs.pc==0xA450
    row['continuation']=dict(prepared_new_terminator_address=address,prepared_old=0,prepared_new=255,
      source_status=resumed['status'],final_registers=vars(regs).copy(),original_instructions=steps2,
      explicit_memory_input_not_readiness=True)
   rows.append(row)
   return original,source,row
  except Exception as exc:
   failures.append(dict(entry=entry,tag=tag,error=str(exc),source_registers=vars(regs)))
   if len(failures)<6:print(json.dumps(failures[-1]),flush=True)
 # Every raw byte index is mechanically tested; IDs30..255/237..255 are not
 # promoted to legitimate city/officer records by their pointer arithmetic.
 indices=range(0,256,32 if quick else 1)
 for i in indices:
  for entry in(0xF2AF,0xF2D7,0xF368):compare(entry,10,{},f'raw-index{i}',a=i,p=0xE5,group='fixed-record-pointers')
  cityptr=0x6000+32*i
  gold=[0,9999,10000,65535][i%4];grain=[10000,65535,0,9999][i%4]
  prep={cityptr:i,cityptr+2:gold&255,cityptr+3:gold>>8,cityptr+4:grain&255,cityptr+5:grain>>8}
  compare(0xD105,10,prep,f'raw-city-index{i}',a=i,p=0x65,group='city-owner-pointer-and-caps')
  for y0 in((4,255)if quick else(0,1,4,8,9,11,255)):
   ptr=0x63C0+12*i;v=(i*29+y0*13)&255
   for entry in(0xD283,0xD2AB):compare(entry,10,{ptr+y0:v},f'raw-officer{i}/Y{y0}',a=i,y=y0,p=0xE5,group='officer-pointer-and-selected-byte')
 # The complete cap service has separate boundary word inputs.
 base=0x6080
 for gold in(0,9998,9999,10000,10001,65535):
  for grain in(0,9999,10000,65535):
   compare(0xD69D,10,{0x20:base&255,0x21:base>>8,base+2:gold&255,base+3:gold>>8,base+4:grain&255,base+5:grain>>8},f'gold{gold}/grain{grain}',group='resource-cap')
 # All values of citybyte1 and representative low gold bytes. True gold high
 # varies independently: this is a wrong-offset composite, not normal gold.
 for low in(0,1,2,255):
  for byte1 in range(0,256,32 if quick else 1):
   compare(0xBD95,10,{0x20:base&255,0x21:base>>8,base+1:byte1,base+2:low,base+3:(byte1*19)&255},f'byte1{byte1}/goldlow{low}',p=0xE5,group='overlapping-threshold-prefix')
 for average in range(0,256,32 if quick else 1):
  result=compare(0xB144,10,{0x40:average},f'raw-average{average}',p=0xE5,group='peaceful-transfer-goal-prefix')
  if result:assert result[0][0x37]==peaceful_transfer_goal(average)
 # ExactFF scan boundaries include all four tails and nextcity+1. An empty
 # name slot beyond26 is a contract boundary, not an official cityfield name.
 for offset in range(0,256,32 if quick else 1):
  prep={0x20:base&255,0x21:base>>8,0x3C:196,**{base+j:0 for j in range(256)},base+offset:255}
  compare(0xA442,10,prep,f'first-FF-at-offset{offset}',group='unbounded-roster-append-prefix')
 compare(0xA442,10,{0x20:base&255,0x21:base>>8,0x3C:196,**{base+j:0 for j in range(256)}},'no-FF-in-full-Y-cycle',group='unbounded-roster-scan-wait')
 # Full ten member rosters are legitimate count inputs and require noFF. The
 # player capacity prefix rejects full destinations before its unbounded scan.
 sourcebase=0x6000+32*5
 for dest_count in range(11):
  for source_count in range(11):
   prep={0:base&255,1:base>>8,0x471:4,0x470:5}
   prep.update({base+17+j:j if j<dest_count else 255 for j in range(10)})
   prep.update({sourcebase+17+j:20+j if j<source_count else 255 for j in range(10)})
   compare(0xA71B,27,prep,f'destination{dest_count}/source{source_count}',group='player-transfer-capacity-prefix')
 # NominationC21D is bounded and ignores every byte27..31, even at full10.
 for i in range(16 if quick else 256):
  count=i%11;ids=[(i*13+j*7)%237 for j in range(count)]
  prep={0:base&255,1:base>>8,0x10:255,0x11:i&127,**{base+17+j:ids[j]if j<count else 255 for j in range(10)}}
  prep.update({base+j:rng.randrange(256)for j in range(27,32)})
  for j,officer in enumerate(ids):prep[0x63C0+12*officer+4]=(i*17+j*11)&255
  compare(0xC21D,25,prep,f'prefixcount{count}/case{i}',x=4,p=0xE5,group='bounded-nomination-full-roster')
 # A legal9+1 same-owner transfer actually constructs a full10 roster through
 # the frozen pure city controller. This is CPU/source integration evidence,
 # not a Native movie or proof that arbitrary prefix overflow is reachable.
 prep={0x470:5,0x471:4,0xEE:0x07,0xEF:0x6F,0x6F07:0,0x6F08:4}
 prep.update({base+17+j:j if j<9 else 255 for j in range(10)})
 prep.update({sourcebase+17+j:196 if j==0 else 255 for j in range(10)})
 prep.update({0x481+j:196 if j==0 else 255 for j in range(10)})
 prep.update({base+j:0 for j in range(27,32)})
 produced=compare(0xAD41,27,prep,'legitimate-destination9-plus-one-transfer',group='legal-full-roster-producer',city_controller=True)
 if produced:
  original,source,producer_row=produced
  full_roster=list(original[base+17:base+27]);assert full_roster==list(range(9))+[196]
  assert list(original[base+27:base+32])==[0]*5
  next_prep={0:base&255,1:base>>8,0x10:255,0x11:0}
  next_prep.update({base+j:original[base+j]for j in range(32)})
  for officer in full_roster:next_prep[0x63C0+12*officer+4]=officer&127
  nomination=compare(0xC21D,25,next_prep,'after-original-legitimate-full10-transfer',x=4,group='bounded-nomination-after-full-roster-producer')
  assert nomination is not None
  city_reads=nomination[2]['city_record_reads']
  assert [q['address']-base for q in city_reads]==list(range(17,27))
  save('legal-full-roster-origin.json',dict(schema='phase17-legal-full-roster-original-source-chain-v1',ROM_sha256=ROM_SHA256,
   source_controller='source/recovered/city_ui_controller.py',source_helper='source/recovered/city_field_contracts.py',
   producer_entry={'pair':[27,28],'cpu':0xAD41},producer_preparation=prep,
   destination_before_count=9,selected_to_add=1,destination_after_count=10,full_roster=full_roster,
   destination_27_to31_after=[0]*5,nomination_entry={'pair':[25,26],'cpu':0xC21D},
   nomination_city_read_offsets=list(range(17,27)),nomination_tail_reads=0,
   counted_as_two_rows_in_main_receipt=True,native_internal_CPU_trace=False,natural_campaign_reachability_claim=False,
   provenance='ActualoriginalCPU and frozenpurecitycontroller agree; the full10 record is a legalcapacity output, and boundednomination reads exactly10 rosterbytes'))
 # Exact source/raw-view guards are not originalCPU comparisons.
 def reject(name,fn):
  try:fn()
  except(ValueError,RuntimeError):guards.append({'name':name,'status':'passed'});return
  raise AssertionError(name)
 reject('actual-registers-required',lambda:CityFieldContracts(memory(rom,10,{}),rom).run_entry(0xF2AF))
 reject('production-stack-seed-rejected',lambda:CityFieldContracts(memory(rom,10,{}),rom).run_entry(0xF2AF,registers=UIRegisters(),seed_return=True))
 reject('wrong-physical-pair-rejected',lambda:CityFieldContracts(memory(rom,12,{}),rom).run_entry(0xD105,registers=UIRegisters()))
 reject('decimal-mode-not-NES-contract',lambda:CityFieldContracts(memory(rom,10,{}),rom).run_entry(0xF2AF,registers=UIRegisters(p=0x28)))
 reject('cityrecord-must-have32bytes',lambda:CityAuxiliaryContract(bytes(31)))
 reject('legal-city-view-max29',lambda:CityAuxiliaryContract.from_memory(memory(rom,10,{}),30))
 reject('mean-byte-domain-required',lambda:peaceful_transfer_goal(256))
 complete=sum(r['comparison']=='complete_return'for r in rows)
 pins=[ROOT/'source/recovered/city_field_contracts.py',Path(__file__),ROOT/'source/recovered/global_ui_controller.py',ROOT/'source/recovered/city_ui_controller.py',ROOT/'source/recovered/battle_nmi_services.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'source/recovered/service_memory.py']
 receipt=dict(schema='phase17-city-field-contracts-original-CPU-v1',status='passed'if not failures else'failed',quick=quick,
  ROM_sha256=ROM_SHA256,rom_cpu_case_count=len(rows),source_guard_case_count=len(guards),total_complete_return_CPU_cases=complete,total_strict_prefix_CPU_cases=len(rows)-complete,
  case_count=len(rows)+len(guards),failed_count=len(failures),group_case_counts=dict(Counter(r['group']for r in rows)),rows=rows,guards=guards,failures=failures,
  source_original_CPU_callbacks=0,source_control_IR_callbacks=0,original_CPU_helper_callbacks=0,
  scope=dict(RAM_bytes=2048,SRAM_bytes=8192,registers=['A','X','Y','P','SP','PC'],banks=True,ordered_IO_reads=True,ordered_IO_writes=True,ordered_SRAM_reads_and_writes=True,inactive_caller_stack_included=True),
  fixture_domains=dict(raw_indices='All256 byte indices are mechanical input; legitimate city0..29/officer0..236 domain remains separate',
    nomination='At most ten originalslots17..26; no terminator required forfull10; >= virtue ties retain original later-wins behavior',
    player_capacity='All eleven occupancy counts0..10 for both cities; prefix endsA742 or rejects atA777, not complete menu',
    append='Explicit existingpointer prefix; rawFF offsets0..255 include tail/nextcity aliases. This does not prove normally protected caller overflow',
    threshold='city+1 and goldlow(+2) form overlappingword>=300; no officialbyte1meaning established',
    wait='NoFF256iteration cycle preservesPC/SP and resumption re-reads explicit external terminator input withoutfakeack'),
  source_path='source/recovered/city_field_contracts.py',source_sha256=sha(pins[0]),validator_path='scripts/verify_city_field_contracts.py',validator_sha256=sha(__file__),
  independent_oracle='py65 MPU6502 validator only',independent_oracle_version=version('py65'),
  source_and_validator_sha256={str(p.relative_to(ROOT)):sha(p)for p in pins},
  parent_snapshot_sha256={str(p.relative_to(ROOT)):sha(p)for p in(Path(str(PARENT)+'-ram.bin'),Path(str(PARENT)+'-sram.bin'))})
 save('validation.json',receipt)
 inst=[]
 for(b,pc),count in sorted(executed.items()):
  o=16+b*8192+(pc&8191);n,t=instruction(rom,o,pc);inst.append(dict(physical_bank=b,cpu=pc,rom_offset=o,raw_hex=rom[o:o+n].hex(' ').upper(),assembly=t,count=count))
 save('executed-instructions.json',inst)
 print(json.dumps({k:receipt[k]for k in('status','rom_cpu_case_count','total_complete_return_CPU_cases','total_strict_prefix_CPU_cases','source_guard_case_count','failed_count')}))
 if failures:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();verify(a.rom.read_bytes(),a.quick)
