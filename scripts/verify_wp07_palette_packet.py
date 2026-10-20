#!/usr/bin/env python3
"""Root-only two actual EE53 calls on independent Source/CPU device fixtures."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,inspect,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'analysis/wp07-palette-packet-consumer'
from py65.devices.mpu6502 import MPU
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.game_engine import GameEngine
from source.recovered.scene_coordinator import SceneCoordinator
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def read(p):return json.loads(p.read_text())
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def normalize(result):
 if result is None or isinstance(result,(str,int,float,bool)):return result
 if isinstance(result,(list,tuple)):return[normalize(x)for x in result]
 if isinstance(result,dict):return{str(k):normalize(v)for k,v in result.items()}
 return{k:normalize(getattr(result,k))for k in('category','pc','address','reason','target','return_pc','expected_sp','entry_banks')if hasattr(result,k)}

def load_adapter():
 spec=importlib.util.spec_from_file_location('wp07_locked_adapter',OUT/'consumer_adapter.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

class AuditedCoordinator(SceneCoordinator):
 def __init__(self,game,adapter):super().__init__(game);self.adapter=adapter;self.audit=[];self.references=[];self.tail=None
 def _resolve_call(self,call):
  self.references.append(call);before=self.adapter.point(self.memory,call.registers)
  if call.target==0xA006 and call.registers.pc==0xA006:
   assert self.tail is None;self.tail=(before,self.adapter.memory_bytes(self.memory))
  result=super()._resolve_call(call)
  self.audit.append(dict(target=call.target,return_pc=call.return_pc,expected_sp=call.expected_sp,entry_banks=list(call.entry_banks),
    source_owner=result.get('source_owner'),status=result.get('status'),before=before,after=self.adapter.point(self.memory,call.registers)))
  return result

class OriginalCall:
 def __init__(self,cpu,memory,adapter,call_number,budget):
  self.cpu=cpu;self.memory=memory;self.adapter=adapter;self.call_number=call_number;self.budget=budget;self.trace=[];self.entry=None;self.tail=None;self.JSR=None;self.RTS=None;self.gates=[]
 def advance(self):
  cpu=self.cpu;m=self.memory;a=self.adapter
  while True:
   pc=cpu.pc
   if self.trace and pc==0xF8B8:
    assert m.banks[3]==31 and cpu.sp==0;return dict(status='returned',instructions=len(self.trace))
   assert len(self.trace)<self.budget,'Original instruction budget exhausted'
   if pc in(0xE716,0xA12D)and not m.read_ports.get(0x2002):
    # Host gate before executing a missing-input instruction. No partial MPU
    # step, exception-driven PC repair, fake input or state restoration.
    self.gates.append(dict(PC=pc,point=a.point(m,cpu),instruction_count=len(self.trace)))
    return dict(status='dependency',PC=pc,instructions=len(self.trace))
   assert pc>=0x8000;bank=m.banks[(pc-0x8000)//8192];m.opcode_pc=pc;before=a.point(m,cpu);ws=len(m.soft_writes);ios=len(m.io_writes);rs=len(m.io_reads)
   if pc==0xEE53:
    assert self.entry is None;self.entry=(before,a.memory_bytes(m))
   if pc==0xA006:
    assert self.tail is None;self.tail=(before,a.memory_bytes(m))
   is_RTS=pc==(0xE748 if self.call_number==1 else 0xA152)
   if is_RTS:
    assert m[pc]==0x60;self.RTS=dict(before=before,frame=[m[0x100+((cpu.sp+i)&255)]for i in(1,2)])
   cpu.step();after=a.point(m,cpu)
   if pc==0xF8B5:
    assert cpu.pc==0xEE53 and cpu.sp==0xFE
    assert[(w['address'],w['value'])for w in m.soft_writes[ws:]]==[(0x100,0xF8),(0x1FF,0xB7)]
    self.JSR=dict(before=before,after=after,pushes=m.soft_writes[ws:])
   if is_RTS:
    assert cpu.pc==0xF8B8 and cpu.sp==0;self.RTS['after']=after
   self.trace.append(dict(bank=bank,pc=pc,before=before['registers'],after=after['registers'],banks_before=before['device']['banks'],banks_after=after['device']['banks'],
     software_writes=m.soft_writes[ws:],IO_writes=m.io_writes[ios:],IO_reads=m.io_reads[rs:]))
   m.opcode_pc=None

def identities(owner,co):
 programs=[]
 def chain(program):
  while program is not None and inspect.isgenerator(program):
   f=program.gi_frame;programs.append((id(program),None if f is None else f.f_lasti));program=program.gi_yieldfrom
 chain(owner._program)
 refs=[]
 for key,(inner,kind)in co._owners.items():refs.append((key,id(inner),kind));chain(inner._program)
 pending=id(owner.pending)if isinstance(owner.pending,ServiceCall)else None
 return(programs,refs,pending)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--root-execution-authorized',action='store_true');args=p.parse_args();assert args.root_execution_authorized
 folder=args.out.resolve();assert folder.parent==OUT and not folder.exists();folder.mkdir()
 accept=read(OUT/'acceptance.json');scope=read(OUT/'family-scope.json');plan=read(OUT/'case-matrix.json');fixture=read(OUT/'device-contract.json')
 for n,k in(('family-scope.json','scope_sha256'),('case-matrix.json','matrix_sha256'),('device-contract.json','device_sha256'),('ancestor-memory.bin','ancestor_sha256')):assert sha(OUT/n)==accept[k]
 for n,h in accept['implementation_pins'].items():assert sha(ROOT/n)==h,n
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert digest(rom)==scope['ROM_SHA256'];raw=(OUT/'ancestor-memory.bin').read_bytes();seed=scope['ancestry']['state']
 pyroot=Path(inspect.getfile(MPU)).resolve().parents[1]
 save(folder/'execution-inputs.json',dict(scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),device_sha256=sha(OUT/'device-contract.json'),
  implementation_pins=accept['implementation_pins'],ancestor_sha256=digest(raw),runtime=dict(Python=sys.version,executable=str(Path(sys.executable).resolve()),executable_sha256=sha(Path(sys.executable).resolve()),py65={str(p):sha(p)for p in sorted(pyroot.rglob('*.py'))}),
  status_input_source='Explicit prelocked per-PC/ordinal finite software-device plans;notNative capture',Source_CPU_IR_callbacks=0,Native_runs=0))
 a=load_adapter();streams={s:(folder/(s+'-snapshots.bin')).open('wb')for s in('Source','CPU')};points=(folder/'points.jsonl').open('w');point_count=0;counts=collections.Counter();parents=[];failure=None
 def pair(label,left,cpu,right,r,source_point=None,cpu_point=None):
  nonlocal point_count
  sp=(a.point(right,r),a.memory_bytes(right))if source_point is None else source_point
  cp=(a.point(left,cpu),a.memory_bytes(left))if cpu_point is None else cpu_point
  assert sp==cp,(label,sp[0],cp[0])
  assert len(sp[1])==26624
  offset=point_count*26624
  streams['Source'].write(sp[1]);streams['CPU'].write(cp[1]);points.write(json.dumps(dict(label=label,offset=offset,bytes=26624,Source=sp[0],CPU=cp[0],Source_sha256=digest(sp[1]),CPU_sha256=digest(cp[1])),separators=(',',':'))+'\n');point_count+=1
 def equal_live(left,cpu,right,r):
  assert a.point(left,cpu)==a.point(right,r)and a.memory_bytes(left)==a.memory_bytes(right)
  for attr in('io_reads','io_writes','ppu_writes','hardware_requests'):assert getattr(left,attr)==getattr(right,attr),attr
  norm=lambda m:[(x['address'],x['before'],x['value'])for x in m.soft_writes]
  assert norm(left)==norm(right)
 def fresh(case,side):
  m=a.ConsumerMemory(rom,raw[:2048],raw[2048:],tuple(seed['banks']),side=side,status_plan=case['status_plan'],read_ports={0x2002:[s['value']for s in case['status_plan'][:case['initial_available']]]})
  m.port_image.update({int(k):v for k,v in seed['ports'].items()});m.port_image[0x2000]=fixture['initial_control']
  m.ppu_register_bytes[:]=bytes((i*17+11)&255 for i in range(16384));m.ppu_address=case['ppu_address'];m.ppu_increment=fixture['initial_increment'];m.ppu_latch=case['ppu_latch'];m.ppu_scroll_latch=case['ppu_scroll_latch'];m.ppu_scroll[:]=fixture['ppu_scroll'];return m
 with(folder/'parents.jsonl').open('w')as results:
  for case in plan['cases']:
   try:
    left,right=fresh(case,'CPU'),fresh(case,'Source');r=NMIRegisters(**seed['registers']);cpu=MPU(memory=left)
    for k,v in seed['registers'].items():setattr(cpu,k,v)
    left.registers=cpu;right.registers=r;game=GameEngine(right,rom=rom,mapped=True);co=AuditedCoordinator(game,a);assert co.external_callback is None
    pair(case['key']+'/fixture-initial',left,cpu,right,r);calls=[];reentries=[];replenishments=[];missing=[]
    for call_number in(1,2):
     equal_live(left,cpu,right,r);before=a.point(right,r);unchanged=a.memory_bytes(right);cpu.pc=r.pc=0xF8B5
     after=a.point(right,r);assert before['registers']['pc']==(0xA074 if call_number==1 else 0xF8B8)
     assert all(before['registers'][k]==after['registers'][k]for k in('a','x','y','p','sp'))and unchanged==a.memory_bytes(right)==a.memory_bytes(left)
     reentries.append(dict(call=call_number,before=before,after=after,changed_registers=['pc']))
     pair(case['key']+f'/call{call_number}-start',left,cpu,right,r)
     orig=OriginalCall(cpu,left,a,call_number,plan['CPU_instruction_budget_per_call']);entry_index=len(right.entry_points);io_start=len(right.io_writes);data_start=len(right.data_reads)
     owner,result=a.current_call(right,r,co);oracle=orig.advance();counts['Source_advances']+=1
     assert result['status']==oracle['status'];equal_live(left,cpu,right,r)
     assert len(right.entry_points)==entry_index+1 and orig.entry==right.entry_points[entry_index]
     pair(case['key']+f'/call{call_number}-actual-JSR-entry',left,cpu,right,r,source_point=right.entry_points[entry_index],cpu_point=orig.entry)
     if call_number==2:
      assert co.tail and orig.tail==co.tail
      pair(case['key']+'/packet-tail-A006-entry',left,cpu,right,r,source_point=co.tail,cpu_point=orig.tail)
     pair(case['key']+f'/call{call_number}-advance1-{result["status"]}',left,cpu,right,r)
     advance_results=[dict(Source=normalize(result),CPU=oracle)]
     if result['status']=='dependency':
      expected_pc=0xE716 if call_number==1 else 0xA12D;assert r.pc==cpu.pc==expected_pc and r.sp==0xFE
      if call_number==1:assert right.ram[0x7D]==0x3A and right.ram[0x7E]==5 and len(right.ppu_writes)==0
      else:assert right.ram[0x7D]==0 and right.ram[0x7E]==1 and len(right.ppu_writes)==32
      baseline=a.fingerprint(right,r);cpu_baseline=a.fingerprint(left,cpu);identity=identities(owner,co);instructions_before=len(orig.trace)
      repeat=owner.resume();retry_CPU=orig.advance();counts['Source_advances']+=1
      assert repeat['status']==retry_CPU['status']=='dependency'and a.fingerprint(right,r)==baseline and a.fingerprint(left,cpu)==cpu_baseline
      assert identities(owner,co)==identity and len(orig.trace)==instructions_before
      pair(case['key']+f'/call{call_number}-zero-progress-retry',left,cpu,right,r)
      advance_results.append(dict(Source=normalize(repeat),CPU=retry_CPU));counts['zero_progress_retries']+=1;counts['missing_boundaries']+=1
      missing.append(dict(PC=expected_pc,flags=[right.ram[0x7D],right.ram[0x7E]],same_owner_call_generator_and_position=True,no_duplicate_IO_or_software_writes=True,CPU_preinstruction_gate_no_PC_repair=True))
      start=right.status_success_count;values=[s['value']for s in case['status_plan'][start:]];assert not right.read_ports[0x2002]and not left.read_ports[0x2002]
      before_fill=bytes(right.ram)+bytes(right.sram);regs_before=a.registers(r);banks_before=list(right.banks)
      for m in(left,right):m.read_ports[0x2002].extend(values)
      assert bytes(right.ram)+bytes(right.sram)==before_fill and a.registers(r)==regs_before and right.banks==banks_before
      replenishments.append(dict(after_one_strict_retry=True,next_ordinal=start+1,values=values,only_device_input_queue_modified=True))
      result=owner.resume();oracle=orig.advance();counts['Source_advances']+=1;assert result['status']==oracle['status']=='returned';equal_live(left,cpu,right,r)
      assert owner._program is None
      pair(case['key']+f'/call{call_number}-real-resume-return',left,cpu,right,r);advance_results.append(dict(Source=normalize(result),CPU=oracle))
     assert result['status']=='returned'and orig.JSR and orig.RTS and not co._owners
     assert orig.RTS['after']==a.point(right,r)and r.pc==0xF8B8 and r.sp==0
     if call_number==1:
      live_palette=orig.entry[1][0x100:0x120];assert live_palette[0]==0xF8 and raw[0x100]==0xA0
      assert right.ppu_writes==[dict(address=0x3F00+i,value=v)for i,v in enumerate(live_palette)]
      assert right.ram[0x7D]==0 and right.ram[0x7E]==5 and right.banks==[16,27,28,31]
      assert right.ppu_address==0 and right.ppu_latch==0 and right.ppu_scroll_latch==0
     else:
      packet=raw[0x383:0x3C3];assert right.ppu_writes[32:]==[dict(address=0x2400+i,value=v)for i,v in enumerate(packet)]
      assert right.ram[0x7D]==0 and right.ram[0x7E]==1 and right.banks==[16,29,30,31]and right.ram[0xE1:0xE4]==bytes.fromhex('303d3e')
      assert right.ppu_address==0x2440
     calls.append(dict(call=call_number,CPU_instructions=len(orig.trace),CPU_trace=orig.trace,actual_JSR=orig.JSR,actual_RTS=orig.RTS,
       Source_events=owner.events,advances=advance_results,source_data_reads=right.data_reads[data_start:],CPU_data_reads=left.data_reads[data_start:],
       IO_prefix_start=io_start,final=a.point(right,r)))
     counts['calls']+=1;counts['CPU_instructions']+=len(orig.trace)
    assert right.status_success_count==2 and len(right.io_reads)==2 and not right.read_ports[0x2002]and not right.repeat_read_ports
    assert len(right.ppu_writes)==96 and len([w for w in right.io_writes if w['address']==0x2000])==2
    assert len([w for w in right.io_writes if w['address']==0x2006])==8
    norm=lambda xs:[(x['address'],x['value'])for x in xs]
    assert norm(right.data_reads)==norm(left.data_reads)and len(right.data_reads)==100
    assert bytes(right.sram)==raw[2048:]and right.ram[0x380:0x3C4]==raw[0x380:0x3C4]
    for event in right.port_events:
     if event['kind']=='read':assert event['after']['ppu_latch']==event['after']['ppu_scroll_latch']==0
    results.write(json.dumps(dict(parent=case['key'],spec=case,status='passed',calls=calls,controlled_reentries=reentries,missing=missing,replenishments=replenishments,
     Source_callbacks=co.audit,CPU_IO_reads=left.io_reads,Source_IO_reads=right.io_reads,CPU_IO_writes=left.io_writes,Source_IO_writes=right.io_writes,
     CPU_port_events=left.port_events,Source_port_events=right.port_events,CPU_software_writes=left.soft_writes,Source_software_writes=right.soft_writes,
     raw_PPU_data_writes=right.ppu_writes,final=a.point(right,r),new_Native_runs=0,status_plan_not_hardware_timing=True),separators=(',',':'))+'\n')
    parents.append(case['key'])
   except Exception as exc:
    failure=dict(parent=case['key'],type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());save(folder/'failure.json',failure);break
 for f in streams.values():f.close()
 points.close()
 for n,h in accept['implementation_pins'].items():assert sha(ROOT/n)==h,n
 complete=failure is None and parents==[c['key']for c in plan['cases']]
 if complete:assert counts['calls']==10 and counts['Source_advances']==14 and counts['missing_boundaries']==counts['zero_progress_retries']==2 and point_count==44
 validation=dict(status='passed_bounded_palette_packet_software_device_contract'if complete else'failed_or_incomplete',parents=len(parents),**dict(counts),saved_paired_points=point_count,
  bytes_per_point=26624,case_sha256=sha(folder/'parents.jsonl'),points_sha256=sha(folder/'points.jsonl'),buffers={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(folder.glob('*-snapshots.bin'))},
  scope_sha256=sha(OUT/'family-scope.json'),acceptance_sha256=sha(OUT/'acceptance.json'),failure=failure,
  Source_CPU_IR_callbacks=0,production_Source_changes=0,new_algorithms=0,new_Native_runs=0,NMI_IRQ_entries=0,outer_frame_credit=0,
  internal_vblank_mirroring_timing_or_rendering_proven=False,field_changes=0,raw_changes=0,remaining=323,whole_WP08_or_game_closure=False)
 save(folder/'validation.json',validation);print(json.dumps(validation,ensure_ascii=False))
if __name__=='__main__':main()
