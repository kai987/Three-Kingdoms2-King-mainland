#!/usr/bin/env python3
"""Root-only locked Source vs original-ROM CPU continuation; never repair PC/SP."""
from pathlib import Path
import argparse,collections,copy,hashlib,importlib.util,inspect,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'analysis/wp08-real-continuation'
from py65.devices.mpu6502 import MPU
from source.recovered.battle_nmi_services import NMIRegisters
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def read(p):return json.loads(p.read_text())
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def load_adapter():
 spec=importlib.util.spec_from_file_location('wp08_locked_adapter',OUT/'continuation_adapter.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def norm_writes(w):return[(e['address'],e['before'],e['value'])for e in w]
def norm_ports(w):return[{k:v for k,v in e.items()if k not in('original_PC','Source_method','Source_line','Source_semantic_PC')}for e in w]
def identity(owner):
 out=[];g=owner._program
 while inspect.isgenerator(g):
  f=g.gi_frame;out.append((id(g),None if f is None else f.f_lasti));g=g.gi_yieldfrom
 return id(owner),out
def summary_snapshot(v):return dict(point=v[0],memory_sha256=digest(v[1]))
def summary_call(row):
 return{k:summary_snapshot(v)if k in('before','entry','after')else v for k,v in row.items()}

class OriginalContinuation:
 def __init__(self,cpu,memory,adapter,spec,budget):
  self.cpu=cpu;self.memory=memory;self.a=adapter;self.spec=spec;self.budget=budget
  self.trace=[];self.calls=[];self.active=[];self.gates=[];self.dispatch=None;self.waits=[]
 def advance(self):
  c=self.cpu;m=self.memory;a=self.a
  while True:
   pc=c.pc
   if pc==self.spec['expected_stop_PC']:
    assert not self.active;return dict(category='nonlocal_return'if self.spec['expected_nonlocal']else'declared_continuation_boundary',PC=pc,SP=c.sp,instructions=len(self.trace))
   assert len(self.trace)<self.budget,'Original CPU instruction budget exhausted'
   assert pc>=0x8000,('Unexpected nonlocal stop',pc)
   if pc in(0xF805,0xE716,0xFB22)and not m.read_ports.get(0x2002):
    gate=dict(category='hardware_read',PC=pc,SP=c.sp,instructions=len(self.trace));self.gates.append(gate);return gate
   m.opcode_pc=pc;before=a.snapshot(m,c);bank=m.banks[(pc-0x8000)//8192];op=m[pc]
   ws=len(m.soft_writes);ps=len(m.port_events)
   if pc==0xF8B5 and self.spec['software_NMI_entry']:
    assert self.dispatch is None;self.dispatch=before
   if op==0x20:
    target=m[pc+1]|m[pc+2]<<8;row=dict(caller_pc=pc,target=target,expected_return_pc=pc+3,expected_sp=c.sp,before=before)
    self.calls.append(row);self.active.append(row)
   if op==0x60:
    assert self.active;row=self.active[-1];row['RTS_PC']=pc;row['actual_frame']=[m[0x100+((c.sp+i)&255)]for i in(1,2)]
   c.step();after=a.snapshot(m,c)
   if op==0x20:
    assert c.pc==target and c.sp==(row['expected_sp']-2)&255;row['entry']=after
   if op==0x60:
    self.active.pop();row['after']=after;row['returned_to_original_caller']=c.pc==row['expected_return_pc']and c.sp==row['expected_sp']
   self.trace.append(dict(bank=bank,pc=pc,opcode=op,before=before[0]['registers'],after=after[0]['registers'],banks_before=before[0]['device']['banks'],banks_after=after[0]['device']['banks'],software_writes=m.soft_writes[ws:],port_events=m.port_events[ps:]))
   m.opcode_pc=None
   if pc==0xFB25 and c.pc==0xFB22:
    assert c.p&64;wait=dict(category='PPUSTATUS_sprite_hit',PC=c.pc,SP=c.sp,instructions=len(self.trace),last_completed_PC=pc)
    self.waits.append(wait);return wait

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--root-execution-authorized',action='store_true');args=p.parse_args();assert args.root_execution_authorized
 folder=args.out.resolve();assert folder.parent==OUT and not folder.exists();folder.mkdir()
 accept=read(OUT/'acceptance.json');scope=read(OUT/'family-scope.json');plan=read(OUT/'case-matrix.json');prov=read(OUT/'source-provenance.json');fixture=read(OUT/'device-contract.json')
 for n,h in accept['inputs'].items():assert sha(OUT/n)==h,n
 for n,h in accept['implementation_pins'].items():assert sha(ROOT/n)==h,n
 rompath=Path('/Users/paulasmith/Downloads/三国志2超级版.nes');rom=rompath.read_bytes();assert digest(rom)==scope['ROM_SHA256']
 pyroot=Path(inspect.getfile(MPU)).resolve().parents[1]
 save(folder/'execution-inputs.json',dict(acceptance_sha256=sha(OUT/'acceptance.json'),inputs=accept['inputs'],implementation_pins=accept['implementation_pins'],
  runtime=dict(Python=sys.version,executable=str(Path(sys.executable).resolve()),executable_sha256=sha(Path(sys.executable).resolve()),py65={str(p):sha(p)for p in sorted(pyroot.rglob('*.py'))}),
  new_Native_runs=0,Source_CPU_IR_callbacks=0,software_NMI_entry_primitive='MPU.nmi and existing BattleNMIServices.interrupt_entry;2 declared events, not Natural hardware edge',host_PC_SP_flag_repairs=0))
 a=load_adapter();streams={s:(folder/(s+'-snapshots.bin')).open('wb')for s in('Source','CPU')};points=(folder/'points.jsonl').open('w');count=0;stats=collections.Counter();parents=[];failure=None
 def pair(label,source,cpu):
  nonlocal count
  assert source==cpu,(label,source[0],cpu[0],digest(source[1]),digest(cpu[1]))
  assert len(source[1])==26624;offset=count*26624
  for side,s in(('Source',source),('CPU',cpu)):streams[side].write(s[1])
  points.write(json.dumps(dict(label=label,offset=offset,bytes=26624,Source=source[0],CPU=cpu[0],Source_sha256=digest(source[1]),CPU_sha256=digest(cpu[1])),separators=(',',':'))+'\n');count+=1
 def equal(left,cpu,right,r):
  assert a.snapshot(left,cpu)==a.snapshot(right,r),(a.point(left,cpu),a.point(right,r))
  assert norm_writes(left.soft_writes)==norm_writes(right.soft_writes)
  assert norm_ports(left.port_events)==norm_ports(right.port_events)
  for k in('io_reads','io_writes','ppu_writes','hardware_requests','mapper_writes'):assert getattr(left,k)==getattr(right,k),k
 def fresh(spec,side):
  native=spec['software_NMI_entry'];b=(OUT/('native122-software-memory.bin'if native else'controlled-SP00-memory-and-raw-sink.bin')).read_bytes()
  seed=prov['Native122']['state']if native else prov['controlled_SP00']['point']['CPU']
  reg=seed['actual_registers']if native else seed['registers'];banks=seed['actual_PRG_banks']if native else seed['device']['banks']
  m=a.ContinuationMemory(rom,b[:2048],b[2048:10240],banks,side=side,status_plan=spec['status_plan'],read_ports={0x2002:[v['value']for v in spec['status_plan'][:spec['initial_available']]]})
  if native:
   f=fixture['fresh_Native122'];m.port_image.update({0xE000:b[0xE1],0xE800:b[0xE2]|0xC0,0xF000:b[0xE3],0x2000:f['initial_control']})
   m.ppu_register_bytes[:]=bytes((i*17+11)&255 for i in range(16384));m.ppu_address=f['ppu_address'];m.ppu_increment=f['initial_increment'];m.ppu_latch=f['ppu_latch'];m.ppu_scroll_latch=f['ppu_scroll_latch'];m.ppu_scroll[:]=f['ppu_scroll']
  else:
   d=seed['device'];assert not d['DMA_requests'];m.ppu_register_bytes[:]=b[10240:]
   m.port_image.update({int(k):v for k,v in d['port_image'].items()})
   for k in('ppu_address','ppu_increment','ppu_latch','ppu_scroll_latch','controller_strobe'):setattr(m,k,d[k])
   m.ppu_scroll[:]=d['ppu_scroll'];m.controller_index[:]=d['controller_index'];m.n163_ram[:]=bytes(d['N163_bytes']);m.n163_address=d['N163_address'];m.n163_autoincrement=d['N163_autoincrement'];m.chr_selectors.update({int(k):v for k,v in d['CHR_selectors'].items()})
  return m,dict(reg),b
 with(folder/'parents.jsonl').open('w')as results:
  for spec in plan['cases']:
   try:
    left,cregs,initial=fresh(spec,'CPU');right,sregs,initial2=fresh(spec,'Source');assert initial==initial2
    cpu=MPU(memory=left);r=NMIRegisters(**sregs)
    for k,v in cregs.items():setattr(cpu,k,v)
    left.registers=cpu;right.registers=r;owner=a.ReadableContinuation(right);orig=OriginalContinuation(cpu,left,a,spec,plan['CPU_budget_per_case']);key=spec['key'];advances=[];missing=[];append_events=[]
    pair(key+'/imported-complete-state',a.snapshot(right,r),a.snapshot(left,cpu))
    if spec['software_NMI_entry']:
     # Explicit software event, no host change of incoming PC/SP/memory/banks.
     cpu.nmi();cpu_interrupt=a.snapshot(left,cpu)
     result=owner.run_nmi(r,hardware_entry=True);stats['software_NMI_entries']+=1
     assert owner.interrupt_snapshot;pair(key+'/derived-actual-interrupt-frame',owner.interrupt_snapshot,cpu_interrupt)
    else:result=owner.run_existing_scene(r)
    oracle=orig.advance();stats['Source_advances']+=1;equal(left,cpu,right,r)
    assert result['status']=='dependency'and result['dependency']['category']==oracle['category']
    pair(key+'/advance1-'+oracle['category'],a.snapshot(right,r),a.snapshot(left,cpu));advances.append(dict(Source=result,CPU=oracle))
    if spec['key']=='native122-bit6-wait-missing-resume':
     assert oracle['category']=='PPUSTATUS_sprite_hit'and len(orig.waits)==1 and right.status_success_count==3
     baseline=copy.deepcopy(a.fingerprint(right,r));cpu_base=copy.deepcopy(a.fingerprint(left,cpu));ident=identity(owner);n=len(orig.trace)
     result=owner.resume();oracle=orig.advance();stats['Source_advances']+=1
     assert result['dependency']['category']==oracle['category']=='hardware_read'
     assert a.fingerprint(right,r)==baseline and a.fingerprint(left,cpu)==cpu_base and len(orig.trace)==n
     assert identity(owner)[0]==ident[0]
     missing.append(dict(transition='sprite_hit_wait_to_missing_read',zero_emulated_state_and_IO_progress=True,same_owner=True,generator_position_identity_claimed=False))
     equal(left,cpu,right,r);pair(key+'/missing-read-no-state-progress',a.snapshot(right,r),a.snapshot(left,cpu));advances.append(dict(Source=result,CPU=oracle))
     ident=identity(owner);result=owner.resume();oracle=orig.advance();stats['Source_advances']+=1
     assert result['dependency']['category']==oracle['category']=='hardware_read'and identity(owner)==ident
     assert a.fingerprint(right,r)==baseline and a.fingerprint(left,cpu)==cpu_base and len(orig.trace)==n
     missing.append(dict(transition='missing_read_retry',zero_emulated_state_and_IO_progress=True,same_owner_and_entire_generator_chain_positions=True))
     equal(left,cpu,right,r);pair(key+'/strict-missing-retry',a.snapshot(right,r),a.snapshot(left,cpu));advances.append(dict(Source=result,CPU=oracle))
     for m in(left,right):assert not m.read_ports[0x2002];m.read_ports[0x2002].append(spec['status_plan'][3]['value'])
     append_events.append(dict(after_successful_reads=3,ordinal=4,PC=0xFB22,value=0x80,only_device_queue_changed=True));pair(key+'/planned-input-appended',a.snapshot(right,r),a.snapshot(left,cpu))
     result=owner.resume();oracle=orig.advance();stats['Source_advances']+=1;equal(left,cpu,right,r)
     assert result['dependency']['category']==oracle['category']=='declared_continuation_boundary'
     pair(key+'/same-owner-resumed-real-return',a.snapshot(right,r),a.snapshot(left,cpu));advances.append(dict(Source=result,CPU=oracle))
    assert owner.stop and r.pc==cpu.pc==spec['expected_stop_PC'];assert len(owner.calls)==len(orig.calls)==spec['expected_call_count']
    if spec['software_NMI_entry']:
     assert owner.dispatch==orig.dispatch;pair(key+'/actual-F878-dispatch',owner.dispatch,orig.dispatch)
     assert r.sp==cpu.sp==0xF9 and right.ram[0x7B]==1 and right.ram[0x7D:0x7F]==bytes((0,0))and right.ram[0x8A]==3
     assert len(right.dma_requests)==1 and len(right.dma_requests[0]['bytes'])==256
    else:
     assert r.sp==0 and right.ram[0x100]==0x0F and right.ram[0x7D]==1 and right.ram[0x7E]==5
     assert owner.calls[-1]['returned_to_original_caller']is False and orig.calls[-1]['actual_frame']==[0xC0,0x0F]
    for i,(s,c)in enumerate(zip(owner.calls,orig.calls,strict=True)):
     for k in('caller_pc','target','expected_return_pc','expected_sp','returned_to_original_caller'):assert s[k]==c[k],(key,i,k,s[k],c[k])
     for k in('before','entry','after'):pair(key+f'/call{i+1}-{s["caller_pc"]:04X}-{k}',s[k],c[k])
    assert not left.read_ports[0x2002]and not right.read_ports[0x2002]and not right.repeat_read_ports
    assert bytes(right.sram)==initial[2048:10240]and right.ram[0x380:0x3C4]==initial[0x380:0x3C4]
    stats['parents']+=1;stats['actual_JSR_RTS_pairs']+=len(orig.calls);stats['normal_RTS_returns']+=sum(c['returned_to_original_caller']for c in orig.calls);stats['nonlocal_RTS']+=sum(not c['returned_to_original_caller']for c in orig.calls)
    stats['CPU_instructions']+=len(orig.trace);stats['status_successes']+=right.status_success_count;stats['bit6_waits']+=len(orig.waits);stats['CPU_missing_gates']+=len(orig.gates);stats['zero_state_missing_resumes']+=len(missing);stats['strict_same_position_missing_retries']+=sum(x['transition']=='missing_read_retry'for x in missing)
    results.write(json.dumps(dict(parent=key,status='passed',spec=spec,Source_calls=[summary_call(s)for s in owner.calls],CPU_calls=[summary_call(c)for c in orig.calls],Source_events=owner.events,
     CPU_trace=orig.trace,advances=advances,missing=missing,replenishments=append_events,Source_stop=owner.stop,final=a.point(right,r),
     CPU_software_writes=left.soft_writes,Source_software_writes=right.soft_writes,CPU_port_events=left.port_events,Source_port_events=right.port_events,raw_PPU_writes=right.ppu_writes,
     software_NMI_entry=spec['software_NMI_entry'],new_Native_runs=0,host_PC_SP_flags_repairs=0,NMI_RTI_completed=False,old_same64B_reentry_replaced=False),separators=(',',':'))+'\n');parents.append(key)
   except Exception as exc:
    failure=dict(parent=spec['key'],type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());save(folder/'failure.json',failure)
    if 'cpu'in locals():
     (folder/'failure-CPU-state.bin').write_bytes(a.memory_bytes(left));(folder/'failure-Source-state.bin').write_bytes(a.memory_bytes(right))
     save(folder/'failure-actual-states.json',dict(CPU=a.point(left,cpu),Source=a.point(right,r),CPU_memory_sha256=digest(a.memory_bytes(left)),Source_memory_sha256=digest(a.memory_bytes(right)),CPU_trace=orig.trace,Source_result=result,Source_calls=[summary_call(s)for s in owner.calls]))
    break
 for f in streams.values():f.close()
 points.close()
 for n,h in accept['implementation_pins'].items():assert sha(ROOT/n)==h,n
 complete=failure is None and parents==[s['key']for s in plan['cases']]
 if complete:
  for k,v in dict(parents=3,actual_JSR_RTS_pairs=14,normal_RTS_returns=13,nonlocal_RTS=1,software_NMI_entries=2,status_successes=8,bit6_waits=1,CPU_missing_gates=2,zero_state_missing_resumes=2,strict_same_position_missing_retries=1,Source_advances=6).items():assert stats[k]==v,(k,stats[k],v)
 validation=dict(status='passed_bounded_real_continuation_contract'if complete else'failed_or_incomplete',**dict(stats),paired_points=count,bytes_per_point=26624,
  buffers={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(folder.glob('*-snapshots.bin'))},points_sha256=sha(folder/'points.jsonl'),parents_sha256=sha(folder/'parents.jsonl'),
  failure=failure,acceptance_sha256=sha(OUT/'acceptance.json'),Source_CPU_IR_callbacks=0,production_Source_changes=0,new_Native_runs=0,new_game_or_hardware_algorithms=0,host_PC_SP_flags_repairs=0,
  software_NMI_only=True,natural_hardware_NMI_credit=0,NMI_RTI_completed=False,old_same64B_reentry_replaced=False,whole_WP08_closed=False,whole_game_closed=False,
  field_changes=0,raw_changes=0,remaining=323,official_city_names={str(i):None for i in(1,28,29,30,31)})
 save(folder/'validation.json',validation);print(json.dumps(validation,ensure_ascii=False))
if __name__=='__main__':main()
