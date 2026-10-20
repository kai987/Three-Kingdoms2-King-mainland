#!/usr/bin/env python3
"""Original CPU against new city control bodies; helper CPU is validator-only.

The separate phase13 integration suite will replace these external oracles
with the recovered owners. This receipt proves local control, not whole core
frames or independent completion of an oracle's callees.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_scene_controller import ObservableBus,VerificationOnlyExternalCPU
from source.recovered.city_ui_controller import CityUIController,CityRegisters
from source.recovered.city_panel_services import CityPanelServices,CityPanelRegisters
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--area',choices=['city','panels'],default='city');p.add_argument('--quick',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==SHA
 out=a.out or ROOT/'analysis/phase13'/a.area;out.mkdir(parents=True,exist_ok=True)
 pair=27 if a.area=='city'else 25;owner=CityUIController if pair==27 else CityPanelServices;regtype=CityRegisters if pair==27 else CityPanelRegisters
 base=ROOT/'analysis/phase11/runtime/cold-battle/city-commands';raw_ram=Path(str(base)+'-ram.bin').read_bytes();raw_sram=Path(str(base)+'-sram.bin').read_bytes()
 catalog=json.loads((ROOT/'analysis/phase13'/a.area/'static-control.json').read_text());counts=Counter();failed=[];unusable=[];rows=[];visited=set();helpers=Counter();guards=[]
 def fresh(prep):
  b=ObservableBus(rom,raw_ram,raw_sram);b.banks=[17,pair,pair+1,31];b.ram[0xDE:0xE4]=bytes((49,42,43,49,pair+32,pair+33));b.ram[0x1FE:0x200]=bytes((0x67,0x24))
  b.ram[0x300]=b.ram[0x304]=255;b.ram[0x7E]=b.ram[0x7C]=b.ram[0x81]=b.ram[0x87]=0;b.ram[0x69]=0
  b.ram[0x140:0x180]=bytes(64);b.ram[0x12]=0;b.ram[0x13]=0;b.ram[0x40C]=0;b.ram[0x40D]=255;b.ram[0x471]=1;b.ram[0x470]=1
  for address,value in prep.items():b[address]=value
  b.ports=[];b.port_reads=[];return b
 def compare(group,entry,prep):
  actual=fresh(prep);source=fresh(prep);initial_a=prep.get(0x401,0)if group=='all_bounded_dispatch_arms'else 17;r=regtype(a=initial_a,x=0,y=0,p=32,sp=253,pc=entry);oracle=VerificationOnlyExternalCPU();controller=owner(source,rom,services=oracle)
  try:
   result=controller.run_entry(entry,registers=r,return_pc=0x2468,max_blocks=20000)
   assert result['status']in('returned','dependency','nonlocal_return'),result
   cpu=MPU(memory=actual,pc=entry);actual.cpu=cpu
   for k,v in dict(a=initial_a,x=0,y=0,p=32,sp=253).items():setattr(cpu,k,v)
   for n in range(400000):
    if n and cpu.pc==r.pc and cpu.sp==r.sp and actual.banks==source.banks:break
    origin=actual.origin(cpu.pc)
    if origin is None:raise RuntimeError(f'Original entered RAM ${cpu.pc:04X}')
    visited.add((origin[0],cpu.pc));actual.pc=cpu.pc;actual.step_no=n;cpu.step()
   else:raise RuntimeError(f'Original budget ${cpu.pc:04X}, expected ${r.pc:04X}')
   rd=[(i,actual.ram[i],source.ram[i])for i in range(2048)if actual.ram[i]!=source.ram[i]];sd=[(i,actual.sram[i],source.sram[i])for i in range(8192)if actual.sram[i]!=source.sram[i]]
   rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
   assert not rd and not sd and not rg,dict(RAM=rd[:10],SRAM=sd[:5],regs=rg)
   assert actual.ports==source.ports and actual.port_reads==source.port_reads and actual.banks==source.banks
   kind='complete_return'if result['status']=='returned'else'strict_prefix';counts[kind]+=1;helpers.update(oracle.calls)
   rows.append(dict(group=group,entry=entry,preparation={hex(k):v for k,v in prep.items()},comparison=kind,original_instructions=n,source_blocks=result['control_blocks'],verification_only_original_CPU_callbacks=sum(oracle.calls.values()),boundary_PC=r.pc,boundary_SP=r.sp))
  except Exception as exc:
   d=dict(group=group,entry=entry,preparation={hex(k):v for k,v in prep.items()},error=str(exc),source_PC=r.pc)
   if any(w in str(exc)for w in('budget','bounded dispatch index','outside original','Original entered RAM')):unusable.append(d)
   else:failed.append(d)
   if len(failed)<=5 and not any(w in str(exc)for w in('budget','bounded dispatch index','Original entered RAM')):print(json.dumps(d),flush=True)
 if pair==27:
  main=[t for t in catalog['dispatch_tables']if t['call_pc']==0xA022][0]
  phase_tables={0xA07D:3,0xA18B:2,0xA295:23,0xADF2:25,0xB759:16,0xB7BF:24,0xDFCA:18}
  states=list(range(16))if not a.quick else[0,1,2,3,4,5,12,14]
  for state in states:
   arm=main['targets'][state];phases=range(phase_tables.get(arm,1))
   if a.quick:phases=list(phases)[:2]
   for phase in phases:
    for button in((0,1,2,128)if not a.quick else(0,2)):
     for entry in((0xA000,0xA01F)if not a.quick else(0xA000,)):
      compare('main_phase_button_domain',entry,{0x400:state,0x401:phase,0x81:button,0x87:button})
 else:
  for entry in(0xA02A,0xBBDE,0xA024,0xA027,0xA02D,0xA030):
   for phase in range(3 if a.quick else 8):compare('fixed_header_requests',entry,{0x401:phase})
  for t in catalog['dispatch_tables']:
   for phase in(range(min(t['count'],2))if a.quick else range(t['count'])):
    for button in((0,)if a.quick else(0,1,2)):
     compare('all_bounded_dispatch_arms',t['call_pc'],{0x401:phase,0x81:button})
 # Newly rewritten loops have independent inputs, not tests mirroring source.
 if pair==27:
  for selected in range(1 if a.quick else 32):
   compare('four_equipment_packets',0xC81F,{0x44C+i:(selected+i)%32 for i in range(4)})
  for count in(0,1,3,10):
   for ruler_present in(False,True):
    ids=list(range(20,30));ids[0]=131 if ruler_present else 20
    prep={0x471:2,0x470:1,0xEE:0,0xEF:0x63,0x6300:131}
    prep.update({0x6011+i:ids[i]for i in range(10)})
    prep.update({0x6051+i:255 for i in range(10)})
    prep.update({0x481+i:ids[i]if i<count else 255 for i in range(10)})
    compare('valid_roster_transfer_and_ruler_priority',0xAD41,prep)
 else:
  for ident in((0,131,236)if a.quick else range(237)):compare('find_officer_city',0xA1EB,{0xA:ident})
  compare('ruler_nibble_decay',0xA209,{})
  compare('nonruler_available_count',0xA240,{})
  for count in(0,1,3,10):
   prep={0:0x20,1:0x60,0x42F:1,0x430:0,0x432:2,0x433:0}
   prep.update({0x6031+i:20+i for i in range(10)})
   prep.update({0x151+i:20+i if i<count else 255 for i in range(10)})
   compare('valid_departure_removal_and_compaction',0xB859,prep)
 for status in(None,'waiting','error','blocked'):
  b=fresh({});r=regtype(sp=253,pc=0xA1EB if pair==25 else 0xA000)
  def bad(call,status=status):
   call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
   return None if status is None else dict(status=status)
  c=owner(b,rom,services=bad);res=c.run_entry(r.pc,registers=r,return_pc=0x2468);assert res['status']=='dependency';guards.append('nonreturned_'+str(status)+'_does_not_advance_even_if_PC_SP_mutated')
 module='city_ui_controller'if pair==27 else'city_panel_services'
 result=dict(status='passed'if not failed else'failed',quick=a.quick,rom_sha256=SHA,rom_cpu_case_count=sum(counts.values()),complete_return_count=counts['complete_return'],strict_prefix_count=counts['strict_prefix'],source_guard_case_count=len(guards),counts=dict(counts),failures=failed,failed_count=len(failed),rows=rows,
  unusable_input_fixtures_excluded=len(unusable),unusable_fixture_artifact='unusable-fixtures.json',comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,registers='AXYP/SP/PC',free_stack_residue='included',ordered_ports_and_banks=True),verification_only_original_CPU_callback_count=sum(helpers.values()),production_source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256=sha(ROOT/f'source/recovered/{module}.py'),source_path=f'source/recovered/{module}.py',validator_sha256=sha(Path(__file__)),validator_path=str(Path(__file__).relative_to(ROOT)),guards=guards,
  limitations=['External original helpers execute only in this validator; no claim of independently recovered helper completion.','Invalid or nonterminating prepared fixtures are explicitly excluded, not passed CPU cases.','The separate pure-coordinator suite uses no original helper callback.'])
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'unusable-fixtures.json').write_text(json.dumps(unusable,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n')
 print(json.dumps(dict(status=result['status'],CPU=sum(counts.values()),counts=dict(counts),failed=len(failed),excluded=len(unusable))),flush=True)
 return bool(failed)
if __name__=='__main__':raise SystemExit(main())
