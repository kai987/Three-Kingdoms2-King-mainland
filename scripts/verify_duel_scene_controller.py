#!/usr/bin/env python3
"""Original6502 oracle for the structured duel controller; helpers explicitly external.

The verification-only callback executes an unchanged external helper on the
source fixture bus, reaching its exact caller PC/SP. It is never installed in
production source. Local135 readable routines execute Python only. No PPU
readiness/NMI/IRQ/CPUreturn is acknowledged by the source.
"""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.duel_scene_controller import DuelSceneController,DuelSceneData,ROM_SHA256,InvalidDuelState
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.scene_shared_services import SceneSharedServices

DECLARED=tuple(range(0x140))+tuple(range(0x200,0x800))
class DuelBus(Bus):
 def __init__(self,rom,ram,sram):
  super().__init__(rom,'zero');self.ram[:]=ram;self.sram[:]=sram;self.banks[:]=[17,23,24,31];self.bank_initialized=[True]*4;self.protect=0x4C;self.port_writes=[]
 def __setitem__(self,a,v):
  if ServiceMemory.is_write_port(a&65535):self.port_writes.append(dict(address=a&65535,value=v&255))
  super().__setitem__(a,v)
 def __getitem__(self,a):
  if isinstance(a,int)and 0x2000<=a<0x6000:raise RuntimeError(f'External hardware read needs explicitinput ${a:04X}')
  return super().__getitem__(a)
class VerificationOnlyHelpers:
 def __init__(self,bus,rom=None):
  self.bus=bus;self.calls=[];self.visited=set();self.shared=SceneSharedServices(bus,rom,callbacks=self._original_helper)if rom else None;self.shared_calls=Counter()
 def __call__(self,call):
  if self.shared is not None and call.target in self.shared.FIXED:
   result=self.shared(call)
   self.shared_calls[call.target]+=1
   return result
  return self._original_helper(call)
 def _original_helper(self,call):
  cpu=MPU(memory=self.bus);self.bus.cpu=cpu
  for k in ('a','x','y','p','sp','pc'):setattr(cpu,k,getattr(call.registers,k))
  initial_sp=cpu.sp
  for n in range(100000):
   if n and cpu.pc==call.return_pc and cpu.sp==call.expected_sp:break
   self.bus.pc=cpu.pc;self.bus.step_no=n
   origin=self.bus.origin(cpu.pc)
   if origin:self.visited.add((origin[0],cpu.pc))
   cpu.step()
  else:raise AssertionError(f'Verification helper${call.target:04X} didnot reach actualcaller ${call.return_pc:04X}/SP{call.expected_sp:02X}; pc={cpu.pc:04X} sp={cpu.sp:02X}')
  for k in ('a','x','y','p','sp','pc'):setattr(call.registers,k,getattr(cpu,k))
  self.calls.append(dict(target=call.target,return_pc=call.return_pc,initial_sp=initial_sp,returned_sp=cpu.sp,instructions=n,banks=list(call.entry_banks)))
  return dict(status='returned',verification_only_original_helper=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase11/duel');p.add_argument('--quick',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=DuelSceneData.from_rom(rom);rng=random.Random(0xD01111)
 fixture=ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-state-16'
 base_ram=Path(str(fixture)+'-ram.bin').read_bytes();base_sram=Path(str(fixture)+'-sram.bin').read_bytes()
 static=json.loads((a.out/'static-control.json').read_text());counts=Counter();fail=[];samples=[];visited=set();local=set();helper_counts=Counter();shared_counts=Counter();guards=[]
 def fresh(i=0):
  ram=bytearray(base_ram);sram=bytearray(base_sram)
  ram[0xE1:0xE4]=bytes((0x31,0x37,0x38));ram[0x4AD:0x4AF]=bytes((131,47));ram[0x4AB:0x4AD]=bytes((0,128));ram[0x4AA]=i&1
  ram[0x4B1:0x4B3]=bytes((73,64));ram[0x4AF:0x4B1]=bytes((0,1));ram[0x4C5:0x4C7]=bytes((60,50));ram[0x4C0]=i%3
  ram[0x4B5:0x4B7]=bytes((i&3,(i>>1)&3));ram[0x4B8]=i%160;ram[0x4BD]=3;ram[0x4BE]=0;ram[0x4BF]=(0,2,6,7)[i%4]
  ram[0x50]=i&255;ram[0x87]=(0,128)[i&1];ram[0x7E]=(0,4)[(i>>1)&1];ram[0x81]=(0,1,2,3,16,32)[i%6];ram[0x7C]=0
  ram[0x300]=ram[0x304]=255 if i&1 else 0;ram[0x310]=ram[0x312]=255
  ram[0x4BB]=(0x18,0xA8,0x08,0xB8,0x40,0x80)[i%6];ram[0x4BA]=0x5D
  ram[0x514:0x518]=bytes((131,0,47,0));ram[0x4A8]=0;ram[0x4A9]=0
  for j in range(7):sram[0xF07+j*8]=(131,28,208,191,136,78,110)[j]
  ram[0x1FE:0x200]=bytes((255,1));return ram,sram
 def compare(group,entry,ram,sram,label,source_shared=False):
  regs=NMIRegisters(a=0,x=0,y=0,p=32,sp=253,pc=entry)
  actual=DuelBus(rom,ram,sram);source=DuelBus(rom,ram,sram);callback=VerificationOnlyHelpers(source,rom if source_shared else None);controller=DuelSceneController(source,data,callback)
  cpu=MPU(memory=actual);actual.cpu=cpu;cpu.pc=entry;cpu.sp=253;cpu.p=32
  try:
   result=controller.run_entry(entry,registers=regs)
   assert result['status']=='returned',result
   for n in range(100000):
    if n and cpu.pc==0x200:break
    actual.pc=cpu.pc;actual.step_no=n;origin=actual.origin(cpu.pc)
    if origin:visited.add((origin[0],cpu.pc))
    cpu.step()
   else:raise AssertionError(f'Original main budget ${cpu.pc:04X}')
   rd=[(f'{j:04X}',actual.ram[j],source.ram[j])for j in DECLARED if actual.ram[j]!=source.ram[j]]
   sd=[(f'{j+0x6000:04X}',x,y)for j,(x,y)in enumerate(zip(actual.sram,source.sram))if x!=y]
   assert not rd and not sd,('memory',rd[:12],sd[:6])
   expected={k:getattr(regs,k)for k in ('a','x','y','p','sp','pc')};observed={k:getattr(cpu,k)for k in expected}
   assert expected==observed,('registers',observed,expected)
   assert source.banks==actual.banks,('banks',source.banks,actual.banks)
   assert source.port_writes==actual.port_writes,('ports',len(source.port_writes),len(actual.port_writes),source.port_writes[:5],actual.port_writes[:5])
   counts[group]+=1;local.update(controller.source_locations);helper_counts.update(call['target']for call in callback.calls);shared_counts.update(callback.shared_calls)
   if sum(v['group']==group for v in samples)<3:samples.append(dict(group=group,entry=entry,label=label,original_instructions=n,result=result,verification_only_helper_calls=callback.calls))
  except Exception as exc:fail.append(dict(group=group,entry=entry,label=label,error=f'{type(exc).__name__}: {exc}'))
 for routine in static['routines']:
  entry=routine['entry']
  for i in range(2 if a.quick else 16):
   ram,sram=fresh(i)
   if entry in(0xB100,):ram[0x4A8]=i%22;ram[0x4A9]=0
   compare('each_proven_local_routine',entry,ram,sram,[routine['name'],i])
 for state in range(22):
  targets=next(t['targets']for t in static['dispatch_tables']if t['pc']==0xB115)
  driver=targets[state];table=next((t for t in static['dispatch_tables']if driver<=t['pc']<driver+24),None)
  for sub in range(len(table['targets'])if table else 1):
   for i in range(2 if a.quick else 12):
    ram,sram=fresh(i);ram[0x4A8]=state;ram[0x4A9]=sub
    compare('all_main_and_nested_phase_dispatches',0xB100,ram,sram,[state,sub,i])
 # Meaningful timer/endpoint boundaries exercise all motion controllers,
 # including the sound-request register clobber at frame32 and completion paths.
 motion_states=(6,13,16,17,18,19,20,21)
 for state in motion_states:
  driver=next(t['targets']for t in static['dispatch_tables']if t['pc']==0xB115)[state]
  table=next(t for t in static['dispatch_tables']if driver<=t['pc']<driver+24)
  for sub in range(len(table['targets'])):
   for timer in ((31,32,159,160)if a.quick else(0,1,7,8,15,16,31,32,63,64,95,96,127,128,159,160,191,192,223,224,255)):
    for actor in (0,1):
     ram,sram=fresh(timer);ram[0x4A8]=state;ram[0x4A9]=sub;ram[0x4AA]=actor;ram[0x4B8]=timer
     ram[0x87]=128;ram[0x7E]=0;ram[0x300]=ram[0x304]=255;ram[0x81]=1
     compare('motion_timer_and_return_endpoints',0xB100,ram,sram,[state,sub,timer,actor])
 # Repeat every state/phase through recovered shared Python helpers. Only far
 # bank calls remain verificationCPU callbacks; realPC/SP is required for both.
 for state in range(22):
  driver=next(t['targets']for t in static['dispatch_tables']if t['pc']==0xB115)[state]
  table=next((t for t in static['dispatch_tables']if driver<=t['pc']<driver+24),None)
  for sub in range(len(table['targets'])if table else 1):
   for i in range(2):
    ram,sram=fresh(i);ram[0x4A8]=state;ram[0x4A9]=sub
    compare('recovered_shared_service_composition',0xB100,ram,sram,[state,sub,i],True)
 # Readable controller result/writeback branches, including same-record aliases.
 for alias in (False,True):
  for left in (0,1,9,10,99,100):
   for right in (0,1,9,10,99,100):
    ram,sram=fresh();ram[0x4AD:0x4AF]=bytes((131,131 if alias else 47));ram[0x4B1:0x4B3]=bytes((left,right))
    compare('HP_writeback_alias_order_and_bar_boundaries',0xD060,ram,sram,[alias,left,right],True)
 for defeated in (131,173,182,222,28,47):
  for actor in (0,1):
   for alias in (False,True):
    for flag in (0,1):
     for cursor in (0,31,128,255):
      ram,sram=fresh(cursor);ids=(defeated,defeated if alias else 0)
      ram[0x514:0x518]=bytes((ids[0],2,ids[1],0));ram[0x4BD]=0;ram[0x4AA]=actor;ram[0x4A8]=14;ram[0x4A9]=2;sram[0xFE1]=flag
      addr=0x3C0+12*ids[1];sram[addr+10]=31 if cursor&1 else 0;sram[addr+11]=(0x10,0x20,0x70,0xFF)[cursor%4]
      compare('result_reward_identity_flags_aliases',0xB100,ram,sram,[defeated,actor,alias,flag,cursor],True)
 cursors=[next(i for i,v in enumerate(data.rules.rng)if v&7==k)for k in range(8)]
 for ability in (200,150,100):
  for loyalty in (90,60,40):
   for hp in (90,60,40):
    for cursor in cursors:
     ram,sram=fresh(cursor);ram[0x4AA]=0;ram[0x4A8]=7;ram[0x4A9]=0
     caster=0x3C0+12*131;target=0x3C0+12*47
     sram[caster+2]=ability//2;sram[caster+4]=ability-ability//2;sram[target]=hp;sram[target+3]=loyalty
     compare('all216_persuasion_table_cells',0xB100,ram,sram,[ability,loyalty,hp,cursor],True)
 # Strict missing-services and pending re-entry are sourceguards, not ROM cases.
 ram,sram=fresh(0);ram[0x4A8]=0;ram[0x4A9]=0;ram[0x87]=128
 bus=DuelBus(rom,ram,sram);controller=DuelSceneController(bus,data)
 result=controller.tick(NMIRegisters());okay=result['status']=='returned' # CDFD is genuinelylocal, no fake external graphics consumer.
 guards.append(dict(name='local_initializer_does_not_need_fake_renderer',passed=okay))
 ram,sram=fresh(1);ram[0x4A8]=1;ram[0x4A9]=1
 bus=DuelBus(rom,ram,sram);controller=DuelSceneController(bus,data)
 result=controller.tick(NMIRegisters());okay=result['status']=='dependency'and result['dependency']['category']=='external_call'
 guards.append(dict(name='missing_real_service_stays_pending',passed=okay))
 try:controller.tick();okay=False
 except RuntimeError:okay=True
 guards.append(dict(name='pending_reentry_rejected',passed=okay))
 ram,sram=fresh(1);ram[0x4A8]=1;ram[0x4A9]=1
 bus=DuelBus(rom,ram,sram);controller=DuelSceneController(bus,data,lambda call:dict(status='returned'))
 result=controller.tick(NMIRegisters());okay=result['status']=='dependency'and 'real caller PC/SP'in result.get('reason','')
 guards.append(dict(name='claimed_return_without_PC_SP_rejected',passed=okay))
 for g in guards:
  if not g['passed']:fail.append(dict(group='sourceguard',guard=g))
 out=a.out;out.mkdir(parents=True,exist_ok=True)
 report=dict(schema='phase11-duel-scene-controller-v1',status='passed'if not fail else'failed',quick=a.quick,rom_sha256=ROM_SHA256,
  rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(fail),counts=dict(counts),
  declared_RAM_count=len(DECLARED),declared_RAM_addresses=list(DECLARED),SRAM_bytes=8192,
  compare_scope='Declared nonstack RAM, entireSRAM, AXYP/SP/PC, exactports/banks. ExternalCPUhelpers separately named; no fullframe claim.',
  recovered_shared_service_call_count=sum(shared_counts.values()),recovered_shared_service_counts={hex(k):v for k,v in shared_counts.items()},
  verification_only_helper_call_count=sum(helper_counts.values()),verification_only_helper_counts={hex(k):v for k,v in helper_counts.items()},
  source_local_instruction_locations=len(local),observed_original_instruction_locations=len(visited),
  source_sha256=hashlib.sha256((ROOT/'source/recovered/duel_scene_controller.py').read_bytes()).hexdigest(),validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  guards=guards,failures=fail,samples=samples)
 (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n')
 (out/'source-executed-locations.json').write_text(json.dumps(sorted(local),indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],CPU=sum(counts.values()),guards=len(guards),failed=len(fail),failures=fail[:10]),ensure_ascii=False));return bool(fail)
if __name__=='__main__':raise SystemExit(main())
