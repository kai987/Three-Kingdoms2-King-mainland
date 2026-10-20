#!/usr/bin/env python3
"""Actual E066 plus explicit software-device fixture; Root-only execution.

py65 is an independent test oracle, never a production Source callback.
Every parent imports once and retains its game, coordinator, bus, registers
and session. This runner does not call any frozen producer/main function.
"""
from pathlib import Path
import argparse,collections,copy,hashlib,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_postbattle_continuity_phase32 import ComparisonMemory,fixture_from_context,registers
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.postbattle_early_integration import PostbattleEarlyGameEngine,PostbattleEarlySceneCoordinator
from source.recovered.postbattle_continuity_wp08 import ActualE066PostbattleContinuity

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def normalize(value):
 if value is None or isinstance(value,(str,int,bool,float)):return value
 if isinstance(value,(tuple,list)):return[normalize(v)for v in value]
 if isinstance(value,dict):return{str(k):normalize(v)for k,v in value.items()}
 return {k:normalize(getattr(value,k))for k in('category','target','return_pc','expected_sp','entry_banks','address','reason')if hasattr(value,k)}

class TracedMemory(ComparisonMemory):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.logical_writes=[];self.logical_reads=[];self.observed_registers=None;self.instruction_pc=None
 def __getitem__(self,address):
  value=super().__getitem__(address)
  if isinstance(address,int)and address&65535==0x87 and hasattr(self,'logical_reads'):
   r=self.observed_registers
   self.logical_reads.append(dict(address=0x87,value=value,PC=None if r is None else r.pc,
    SP=None if r is None else r.sp,oracle_opcode_PC=self.instruction_pc))
  return value
 def __setitem__(self,address,value):
  before=None;physical=None
  if isinstance(address,int):
   address&=65535
   if address<0x2000:physical=address&2047;before=self.ram[physical]
   elif 0x6000<=address<0x8000:physical=address;before=self.sram[address-0x6000]
  super().__setitem__(address,value)
  if physical is not None and hasattr(self,'logical_writes'):
   r=self.observed_registers
   self.logical_writes.append(dict(address=physical,before=before,value=value&255,
    PC=None if r is None else r.pc,SP=None if r is None else r.sp,oracle_opcode_PC=self.instruction_pc))

def clone(m):
 x=TracedMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),
  read_ports={k:list(v)for k,v in m.read_ports.items()},repeat_read_ports=set(m.repeat_read_ports),controller_buttons=m.controller_buttons)
 for attr in('n163_ram','ppu_register_bytes'):getattr(x,attr)[:]=getattr(m,attr)
 for attr in('n163_address','n163_autoincrement','controller_strobe','ppu_address','ppu_increment','ppu_latch','ppu_scroll_latch'):setattr(x,attr,getattr(m,attr))
 for attr in('controller_index','ppu_scroll','port_image','chr_selectors','dma_requests'):setattr(x,attr,copy.deepcopy(getattr(m,attr)))
 return x

def bus_state(m):
 return dict(controller_buttons=m.controller_buttons,controller_strobe=m.controller_strobe,controller_index=m.controller_index,
  read_ports={str(k):list(v)for k,v in m.read_ports.items()},repeat_read_ports=sorted(m.repeat_read_ports),
  N163_bytes=list(m.n163_ram),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
  PPU_bytes_sha256=digest(bytes(m.ppu_register_bytes)),PPU_address=m.ppu_address,PPU_increment=m.ppu_increment,
  PPU_latch=m.ppu_latch,PPU_scroll_latch=m.ppu_scroll_latch,PPU_scroll=m.ppu_scroll,
  port_image=m.port_image,CHR_selectors=m.chr_selectors,
  DMA_requests=[dict(page=x['page'],OAMADDR=x['OAMADDR'],bytes_sha256=digest(x['bytes']))for x in m.dma_requests])

def compare(left,right,cpu,r):
 for name in('ram','sram'):
  a,b=getattr(left,name),getattr(right,name)
  if a!=b:raise AssertionError(dict(domain=name,differences=[(i,x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y][:24]))
 assert registers(cpu)==registers(r),dict(CPU=registers(cpu),Source=registers(r))
 assert left.banks==right.banks
 assert left.combined_IO==right.combined_IO,dict(CPU_IO=left.combined_IO[-20:],Source_IO=right.combined_IO[-20:])
 assert left.ppu_register_bytes==right.ppu_register_bytes
 assert left.ppu_writes==right.ppu_writes and left.dma_requests==right.dma_requests
 assert left.io_reads==right.io_reads and left.io_writes==right.io_writes
 assert left.hardware_requests==right.hardware_requests
 assert bus_state(left)==bus_state(right),'Declared software device states differ'

def fingerprint(m,r):
 return(bytes(m.ram),bytes(m.sram),registers(r),tuple(m.banks),tuple(m.combined_IO),json.dumps(bus_state(m),sort_keys=True),
  bytes(m.ppu_register_bytes),copy.deepcopy(m.ppu_writes),copy.deepcopy(m.dma_requests),copy.deepcopy(m.hardware_requests),copy.deepcopy(m.io_reads),copy.deepcopy(m.io_writes))

class AuditedCoordinator(PostbattleEarlySceneCoordinator):
 def __init__(self,game,withholding=False):
  super().__init__(game);self.ecee_mode='missing'if withholding else'actual';self.real_ECEE_resolutions=0;self.audit=[];self.call_references=[]
 def _resolve_call(self,call):
  self.call_references.append(call)
  before=dict(registers=registers(call.registers),banks=list(self.memory.banks),E1=self.memory[0xE1],stack=bytes(self.memory.ram[0x100:0x200]).hex())
  if call.target==0xECEE and self.ecee_mode!='actual':result=dict(status='dependency'if self.ecee_mode=='missing'else'returned',test_only_withheld_real_service=True)
  else:
   if call.target==0xECEE:self.real_ECEE_resolutions+=1
   result=super()._resolve_call(call)
  after=dict(registers=registers(call.registers),banks=list(self.memory.banks),E1=self.memory[0xE1],stack=bytes(self.memory.ram[0x100:0x200]).hex())
  self.audit.append(dict(target=call.target,return_pc=call.return_pc,expected_sp=call.expected_sp,entry_banks=list(call.entry_banks),status=result.get('status'),before=before,after=after,controlled_ECEE_mode=self.ecee_mode))
  return result

def run_parent(rom,spec,input_cycles,out,withholding):
 tag='withheld-ECEE-same-actual-origin'if withholding else'normal-same-actual-origin'
 folder=out/tag;folder.mkdir();inputs={}
 m,initial,provenance=fixture_from_context(rom,ROOT/spec['initial_context'],spec['hardware'],inputs)
 meta=json.loads((ROOT/spec['initial_context']).read_text());h=spec['hardware']
 assert initial==spec['expected_registers']and m.banks==spec['expected_actual_PRG_banks']
 assert digest(bytes(m.ram))==spec['expected_RAM_sha256']and digest(bytes(m.sram))==spec['expected_SRAM_sha256']
 m.controller_strobe=h['controller_strobe'];m.controller_index[:]=h['controller_index']
 assert bytes(m.ppu_register_bytes)==bytes(h['PPU_fixture']['register_bytes_zero_length'])
 left,right=clone(m),clone(m);r=NMIRegisters(**initial);cpu=MPU(memory=left)
 for k,v in initial.items():setattr(cpu,k,v)
 left.observed_registers=cpu;right.observed_registers=r
 game=PostbattleEarlyGameEngine(right,rom=rom,mapped=True);game._scene_coordinator=AuditedCoordinator(game,withholding)
 driver=ActualE066PostbattleContinuity(game,r,actual_context=meta);co=driver.coordinator
 assert co.external_callback is None and left is not right
 identities=(game,co,right,r,driver.session);stages=[];counts=collections.Counter();instructions=0;fake_count=0;regression=None;exception=None;result=None;stop=None;oracle_checkpoints=[];fake_checks=[]
 def event(kind,label):
  nonlocal instructions
  before_regs=registers(r);left.instruction_pc=None;res=driver.advance(kind,label=label)
  if kind=='nmi':cpu.nmi()
  elif kind=='irq':cpu.irq()
  for n in range(spec['policy']['max_original_instructions_per_event']+1):
   if n and(cpu.pc,cpu.sp)==(r.pc,r.sp)and(res['status']in('returned','reset_boundary')or registers(cpu)==registers(r)):
    compare(left,right,cpu,r);break
   if n==spec['policy']['max_original_instructions_per_event']:raise RuntimeError(f'Original oracle budget at {cpu.pc:04X}; Source {r.pc:04X}')
   assert cpu.pc>=0x8000,'Oracle entered RAM'
   left.instruction_pc=cpu.pc
   bank=left.banks[(cpu.pc-0x8000)//8192]
   if(bank==8 and cpu.pc in(0xBB36,0xBC46,0xBD67,0xBDCD,0xBE54,0xBD8E,0xBD96,0xBDB8,0xBDAA,0xBD91,0xBD95,0xBB39,0xBBA0))or(bank==31 and cpu.pc in(0xECEE,0xEE07,0xEE4A,0xEE4D,0xEE52,0xEC67)):
    oracle_checkpoints.append(dict(event=len(stages),operation=kind,registers=registers(cpu),banks=list(left.banks),
     stack_top_word=left.ram[0x100+((cpu.sp+1)&255)]|(left.ram[0x100+((cpu.sp+2)&255)]<<8),
     stack=bytes(left.ram[0x100:0x200]).hex(),E1=left.ram[0xE1],fade=list(left.ram[0x87:0x8B]),
     working=list(left.sram[0xFA1:0xFB6]),source_city_roster=list(left.sram[0x211:0x21B])))
   cpu.step()
  instructions+=n;counts[kind]+=1
  assert all(a is b for a,b in zip(identities,(driver.game,driver.coordinator,driver.memory,driver.registers,driver.session)))
  index=len(stages);base=f'event-{index:04d}'
  for role,bus in(('CPU',left),('Source',right)):
   (folder/(base+'-'+role+'-ram.bin')).write_bytes(bytes(bus.ram));(folder/(base+'-'+role+'-sram.bin')).write_bytes(bytes(bus.sram))
   (folder/(base+'-'+role+'-ppu-sink.bin')).write_bytes(bytes(bus.ppu_register_bytes))
  io=list(right.combined_IO)
  stages.append(dict(sequence=index,operation=kind,label=label,status=res['status'],original_CPU_instructions=n,
   before_registers=before_regs,registers=registers(r),banks=list(right.banks),battle=list(right.ram[0x500:0x502]),global_state=right[0x7A],NMI_state=right[0x78],city=list(right.ram[0x400:0x404]),
   RAM_sha256=digest(bytes(right.ram)),SRAM_sha256=digest(bytes(right.sram)),combined_IO_count=len(io),combined_IO_prefix_sha256=digest(json.dumps(io,separators=(',',':')).encode()),
   software_devices=copy.deepcopy(bus_state(right)),pending_depth=len(driver.session.pending),ownership=driver.ownership(),result=normalize(res)))
  return res
 def is_irq_wait():
  if not driver.session.pending:return False
  phase=driver.session.pending[-1]
  return phase.kind=='nmi'and getattr(driver.session._interrupt_owners[phase.token].pending,'category',None)=='IRQ_software_flag'
 def irq_policy(res,label):
  for attempt in range(12):
   if res['status']=='returned'or not is_irq_wait():return res
   if right[0x62]:
    child=event('irq',label+f'/IRQ-{attempt}');assert child['status']=='returned'
   else:res=event('resume',label+f'/same-NMI-resume-{attempt}')
  raise RuntimeError('Declared IRQ bound exhausted')
 def restore_ecee(res,label):
  nonlocal fake_count,regression
  if not withholding or co.ecee_mode!='missing'or r.pc!=0xECEE:return res
  assert res['status']=='dependency'and driver.session.pending
  phase=driver.session.pending[-1];owner=driver.session._interrupt_owners[phase.token];program=owner._program
  relevant=[(who.pending,who,who._program)for who,_ in co._owners.values()if getattr(getattr(who,'pending',None),'target',None)==0xECEE]
  assert len(relevant)==1;call,inner,inner_program=relevant[0]
  before=fingerprint(right,r);before_cpu=fingerprint(left,cpu);co.ecee_mode='fake'
  for i in range(2):
   fake=driver.resume(label=f'{label}/fake-return-{i}');assert fake['status']=='dependency'
   assert fingerprint(right,r)==before and fingerprint(left,cpu)==before_cpu
   assert driver.session.pending[-1]is phase and owner._program is program and inner.pending is call and inner._program is inner_program
   compare(left,right,cpu,r);fake_count+=1
   fake_checks.append(dict(check=i,original_CPU_instructions=0,Source_program_advance=False,
    RAM_sha256=digest(bytes(right.ram)),SRAM_sha256=digest(bytes(right.sram)),
    registers=registers(r),devices=copy.deepcopy(bus_state(right)),
    pending_identity=driver.ownership(),PPU_full_bytes_unchanged=True,combined_logical_IO_unchanged=True))
  co.ecee_mode='actual';res=event('resume',label+'/actual-Shared-once')
  assert co.real_ECEE_resolutions==1
  ecee=[x for x in co.audit if x['target']==0xECEE and x['controlled_ECEE_mode']=='actual']
  assert len(ecee)==1 and ecee[0]['status']=='returned'and ecee[0]['after']['registers']['pc']==0xBB96
  regression=dict(same_outer_phase=True,same_inner_call_owner_generator=True,fake_returns_without_CPU_or_Source_progress=2,actual_ECEE_resolutions=1)
  return res
 try:
  for cycle,buttons in enumerate(input_cycles):
   driver.set_buttons(*buttons);left.controller_buttons=tuple(buttons)
   result=event('main',f'cycle-{cycle}/main')
   if result['status']!='returned':stop='strict_dependency_prefix';break
   if right[0x7A]in spec['success']['stop_on_first_returned_global_state']:stop='declared_success_boundary';break
   result=event('nmi',f'cycle-{cycle}/fresh-NMI');result=restore_ecee(result,f'cycle-{cycle}')
   result=irq_policy(result,f'cycle-{cycle}')
   if result['status']!='returned':stop='strict_dependency_prefix'if result['status']=='dependency'else'budget_or_nonlocal_incomplete';break
   if right[0x7A]in spec['success']['stop_on_first_returned_global_state']:stop='declared_success_boundary';break
  else:stop='declared_cycle_budget_without_success'
 except Exception as exc:
  exception=dict(type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),Source_registers=registers(r),CPU_registers=registers(cpu),Source_banks=list(right.banks),CPU_banks=list(left.banks),pending=normalize(getattr(driver.session,'pending',[])),last_coordinator_calls=co.audit[-8:]);stop='comparison_failure'
 final=driver.state();writes=right.logical_writes
 state_writes=[x for x in writes if x['address']in(0x500,0x501,0x7A)]
 seen={(15,0)};main,sub=15,0
 for x in state_writes:
  if x['address']==0x500:main=x['value']
  elif x['address']==0x501:sub=x['value']
  seen.add((main,sub))
 commit=[x for x in writes if x['address']==0x6214 and x['before']==255 and x['value']==67]
 equal_protocol=False
 if stop=='declared_success_boundary':
  assert set(map(tuple,spec['success']['required_battle_states']))<=seen,(seen,'Missing declared stage')
  assert len(commit)==1 and right.sram[0x214]==67 and list(right.sram[0xFA1:0xFB6])==[67]+[255]*20
  assert r.pc==0xE066 and r.sp==255 and not driver.session.pending and not driver.session._interrupt_owners
  assert co.real_ECEE_resolutions==1
  source_fade=[x for x in right.logical_reads if x['PC']==0xBBA0]
  cpu_fade=[x for x in left.logical_reads if x['oracle_opcode_PC']==0xBBA0]
  assert[x['value']for x in source_fade]==[x['value']for x in cpu_fade]==[1]*19+[255]
  side_effects=[x for x in co.audit if x['target']==0xEE07 and x['before']['E1']!=x['after']['E1']]
  assert side_effects and all(x['entry_banks'][1:3]==x['after']['banks'][1:3]for x in side_effects)
  assert any((x['before']['E1'],x['after']['E1'])==(49,48)for x in side_effects)
  ecee=[x for x in co.audit if x['target']==0xECEE and x['controlled_ECEE_mode']=='actual']
  assert len(ecee)==1 and ecee[0]['status']=='returned'and ecee[0]['after']['registers']['pc']==0xBB96
  if withholding:assert regression is not None and fake_count==2
  for rawword in(0xBB38,0xBD90):
   hi,lo=rawword>>8,rawword&255
   def pairs(rows):
    return[(a['address'],b['address'],a['value'],b['value'])for a,b in zip(rows,rows[1:])if 0x100<=a['address']<0x200 and b['address']==a['address']-1 and(a['value'],b['value'])==(hi,lo)]
   assert pairs(right.logical_writes)==pairs(left.logical_writes)and pairs(right.logical_writes)
  equal_protocol=True
  status='passed_complete_continuous_software_suffix'
 elif stop=='strict_dependency_prefix':status='strict_dependency_prefix'
 else:status='failed_or_incomplete'
 save(folder/'Source-logical-writes.json',writes);save(folder/'CPU-logical-writes.json',left.logical_writes)
 save(folder/'Source-selected-reads.json',right.logical_reads);save(folder/'CPU-selected-reads.json',left.logical_reads)
 save(folder/'oracle-selected-checkpoints.json',oracle_checkpoints);save(folder/'fake-return-checks.json',fake_checks)
 save(folder/'Source-combined-IO.json',right.combined_IO);save(folder/'CPU-combined-IO.json',left.combined_IO)
 save(folder/'source-call-audit.json',co.audit);save(folder/'identity-journal.json',driver.journal)
 row=dict(case=tag,status=status,stop_reason=stop,exception=exception,declared_cycle_upper_bound=27,executed_software_cycles=cycle+1,
  compared_event_count=len(stages),operation_counts=dict(counts),original_CPU_instructions=instructions,events=stages,
  initial_provenance=provenance,initial_import_count_per_bus=1,subsequent_Native_snapshot_imports=0,
  same_game_coordinator_bus_register_session=True,actual_final_registers=registers(r),final_state=final,
  seen_battle_states_including_transient_write_pairs=sorted(map(list,seen)),
  compared_boundary_battle_states=sorted({tuple(x['battle'])for x in stages}),
  Source_actual_commits=commit,current_return_stack_protocol_matches_CPU=equal_protocol,
  ECEE_synchronous_actual_return_count=co.real_ECEE_resolutions,
  BBA0_fresh_NMI_read_count=len([x for x in right.logical_reads if x['PC']==0xBBA0]),
  ECEE_regression=regression,fake_return_zero_progress_checks=fake_count,Source_original_CPU_callbacks=0,production_IR_interpretation=False,
  Native_frames_claimed=0,unknown_dependency=stages[-1]if status=='strict_dependency_prefix'and stages else None)
 save(folder/'validation.json',row)
 printed={k:row[k]for k in('case','status','stop_reason','executed_software_cycles','compared_event_count','operation_counts','original_CPU_instructions','actual_final_registers')}
 if exception:printed['exception']={k:exception[k]for k in('type','error','traceback')}
 print(json.dumps(printed,ensure_ascii=False),flush=True)
 return row

def main():
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--root-execution-authorized',action='store_true');a=p.parse_args()
 assert a.root_execution_authorized
 out=a.out.resolve();assert out.is_relative_to(ROOT/'analysis/wp08-shortest-continuity')and not out.exists();out.mkdir(parents=True)
 spec=json.loads(a.spec.read_text());assert spec['case']=='actual_E066_plus_explicit_software_device_fixture'
 plan_path=ROOT/spec['input_plan'];assert sha(plan_path)==spec['input_plan_sha256']
 input_cycles=[]
 for block in json.loads(plan_path.read_text()):
  assert block['start_software_cycle']==len(input_cycles)and block['software_cycles']>0
  buttons=block['pad_buttons'];assert len(buttons)==2 and all(isinstance(x,int)and 0<=x<=255 for x in buttons)
  input_cycles.extend([tuple(buttons)]*block['software_cycles'])
 assert len(input_cycles)==spec['policy']['max_software_cycles']
 assert sha(ROOT/spec['initial_context'])==spec['initial_context_sha256']
 rom=a.rom.read_bytes();assert digest(rom)=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 pins={str(x.relative_to(ROOT)):sha(x)for x in sorted((ROOT/'source/recovered').glob('*.py'))};pins[str(Path(__file__).resolve().relative_to(ROOT))]=sha(__file__)
 pins['scripts/verify_postbattle_continuity_phase32.py']=sha(ROOT/'scripts/verify_postbattle_continuity_phase32.py')
 save(out/'execution-inputs.json',dict(spec_path=str(a.spec.resolve().relative_to(ROOT)),spec_sha256=sha(a.spec),input_plan_path=spec['input_plan'],input_plan_sha256=sha(plan_path),actual_two_pad_input_cycles=input_cycles,Source_and_runner_sha256=pins,initial_context_sha256=spec['initial_context_sha256']))
 (out/'executed-spec.json').write_bytes(a.spec.read_bytes());(out/'executed-input-plan.json').write_bytes(plan_path.read_bytes())
 executed=out/'executed-source';executed.mkdir()
 for name in('scripts/verify_wp08_shortest_continuity.py','source/recovered/postbattle_continuity_wp08.py'):
  raw=(ROOT/name).read_bytes();assert digest(raw)==pins[name];(executed/Path(name).name).write_bytes(raw)
 rows=[]
 for withholding in(False,True):
  row=run_parent(rom,spec,input_cycles,out,withholding);rows.append(row)
  if row['status']!='passed_complete_continuous_software_suffix':break
 assert all(sha(ROOT/k)==v for k,v in pins.items())and sha(plan_path)==spec['input_plan_sha256']
 status='passed'if len(rows)==2 and all(x['status']=='passed_complete_continuous_software_suffix'for x in rows)else'blocked_or_incomplete'
 receipt=dict(schema='wp08-shortest-continuous-source-validation-v1',status=status,parents=rows,source_parent_case_count=len(rows),
  complete_continuous_suffixes=sum(x['status']=='passed_complete_continuous_software_suffix'for x in rows),
  strict_prefixes=sum(x['status']=='strict_dependency_prefix'for x in rows),Native_new_frames=0,production_original_CPU_callbacks=0,
  production_IR_interpretation=False,spec_sha256=sha(a.spec),Source_and_runner_sha256=pins,
  whole_game_closure_proven=False,unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None)
 save(out/'validation.json',receipt);print(json.dumps(dict(status=status,parent_cases=len(rows),complete=receipt['complete_continuous_suffixes'])),flush=True)
if __name__=='__main__':main()
