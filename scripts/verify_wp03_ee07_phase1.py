#!/usr/bin/env python3
"""Root-only phase1 producer; independent existing Source and original ROM CPU."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,inspect,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
OUT=ROOT/'analysis/wp03-ee07-phase1-producer';OLD=ROOT/'analysis/wp03-ee07-return-family'
from py65.devices.mpu6502 import MPU
from verify_wp03_ee07_family import ObservedBus,state,software,regs
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.game_engine import GameEngine
from source.recovered.scene_coordinator import SceneCoordinator
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def read(p):return json.loads(p.read_text())
def save(p,x):
 assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

class ProducerBus(ObservedBus):
 def __init__(self,*a,side,**kw):
  super().__init__(*a,**kw);self.side=side;self.events=[]
 def __getitem__(self,address):
  value=super().__getitem__(address)
  if isinstance(address,int)and self.registers is not None:
   frame=sys._getframe(1);method=frame.f_code.co_name;r=self.registers
   source=self.side=='Source'and method=='cityuiworkers_bc74_phase_1'and address>=0x8000
   cpu=self.side=='CPU'and self.opcode_pc==0xBCBF and address==((self.ram[0]|self.ram[1]<<8)+r.y)&65535
   if source or cpu:
    assert 0<=r.y<64
    self.events.append(dict(kind='payload_read',address=address,value=value,Y=r.y,
      bank=self.banks[(address-0x8000)//8192],live00_01=self.ram[0]|self.ram[1]<<8,
      original_PC=self.opcode_pc,Source_method=method if source else None,Source_line=frame.f_lineno if source else None))
  return value
 def __setitem__(self,address,value):
  frame=sys._getframe(1);method=frame.f_code.co_name
  result=super().__setitem__(address,value)
  if isinstance(address,int)and 0x380<=address<=0x3C3 and self.registers is not None:
   source=self.side=='Source'and method=='cityuiworkers_bc74_phase_1'
   cpu=self.side=='CPU'and self.opcode_pc in(0xBCA2,0xBCA8,0xBCAE,0xBCC1,0xBCCB)
   if source or cpu:
    self.events.append(dict(kind='packet_write',address=address,value=value&255,Y=self.registers.y,
      original_PC=self.opcode_pc,Source_method=method if source else None,Source_line=frame.f_lineno if source else None))
  return result

class ProducerCoordinator(SceneCoordinator):
 def __init__(self,game):super().__init__(game);self.reset_audit()
 def reset_audit(self):self.audit=[];self.points={};self.palette={}
 def _resolve_call(self,call):
  before=state(self.memory,call.registers);data=software(self.memory)
  if call.target==0xA039:self.points['forward']=(before,data)
  if call.target==0xECEE:self.palette['entry']=(before,data)
  result=super()._resolve_call(call)
  after=state(self.memory,call.registers);after_data=software(self.memory)
  if call.target==0xA039:self.points['callee-return']=(after,after_data)
  if call.target==0xF25F:self.points['data-mapped']=(after,after_data)
  if call.target==0xECEE:self.palette['return']=(after,after_data)
  self.audit.append(dict(target=call.target,entry_banks=list(call.entry_banks),return_pc=call.return_pc,expected_sp=call.expected_sp,
    status=result.get('status'),source_owner=result.get('source_owner'),before=before,after=after))
  return result

def original(m,cpu,site):
 S=cpu.sp;trace=[];points={};palette={};five=[];JSR=None;body_RTS=None;final_RTS=None
 for n in range(2000):
  pc=cpu.pc;assert pc>=0x8000;bank=m.banks[(pc-0x8000)//8192]
  if pc==0xA074:
   assert bank==27;break
  m.opcode_pc=pc;m.probe=None;ws=len(m.writes);ios=len(m.io_writes);before=state(m,cpu)
  if pc==0xA039:points['forward']=(before,software(m))
  if pc==0xECEE:palette['entry']=(before,software(m))
  if pc in(0xEE1F,0xEE25):m.probe=dict(kind='inline_data',addresses=[((m.ram[0x59]|m.ram[0x5A]<<8)+cpu.y)&65535])
  if pc==0xBD02:body_RTS=dict(before=before,frame=[m[0x100+((cpu.sp+i)&255)]for i in(1,2)])
  if pc==0xEE52:final_RTS=dict(before=before,frame=[m[0x100+((cpu.sp+i)&255)]for i in(1,2)])
  cpu.step();after=state(m,cpu);writes=m.writes[ws:]
  if pc==0xA06F:
   assert cpu.pc==0xEE07 and cpu.sp==(S-2)&255
   assert[(w['address'],w['value'])for w in writes]==[(0x100+S,0xA0),(0x100+((S-1)&255),0x71)]
   JSR=dict(before=before,after=after,pushes=writes)
  if pc in(0xEE3B,0xEE3F,0xEE43,0xEE46,0xEE49):five.extend(writes)
  if cpu.pc==0xBCA0:assert 'data-mapped'not in points;points['data-mapped']=(after,software(m))
  if pc==0xED18:assert cpu.pc==0xBCFA;palette['return']=(after,software(m))
  if pc==0xBD02:
   assert cpu.pc==0xEE4D and cpu.sp==(S-3)&255;body_RTS['after']=after;points['callee-return']=(after,software(m))
  if pc==0xEE52:
   assert cpu.pc==0xA074 and cpu.sp==S;final_RTS['after']=after
  trace.append(dict(bank=bank,pc=pc,before=before['registers'],after=after['registers'],banks_before=before['banks'],banks_after=after['banks'],writes=writes,IO_writes=m.io_writes[ios:]))
 else:raise AssertionError('Original CPU instruction budget exhausted')
 m.opcode_pc=None;m.probe=None
 assert JSR and body_RTS and final_RTS and set(points)=={'forward','data-mapped','callee-return'}
 assert[(w['address'],w['value'])for w in five]==[(0x100+((S-i)&255),v)for i,v in enumerate((0xA0,0x73,0x3B,0xEE,0x4C))]
 assert body_RTS['frame']==[0x4C,0xEE]and final_RTS['frame']==[0x73,0xA0]
 return dict(instructions=len(trace),trace=trace,actual_JSR=JSR,five_pushes=five,real_BD02_RTS=body_RTS,real_EE52_RTS=final_RTS,
             points=points,palette=palette,inline_reads=m.reads)

def fresh(rom,raw,seed,side):
 m=ProducerBus(rom,raw[:2048],raw[2048:],tuple(seed['banks']),side=side);m.port_image.update({int(k):v for k,v in seed['ports'].items()});return m
def palette_record(p):
 return{key:dict(state=value[0],RAM_hex=value[1][:2048].hex(),SRAM_hex=value[1][2048:].hex())for key,value in p.items()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--root-execution-authorized',action='store_true');args=p.parse_args();assert args.root_execution_authorized
 folder=args.out.resolve();assert folder.parent==OUT and not folder.exists();folder.mkdir()
 accept=read(OUT/'acceptance.json');scope=read(OUT/'family-scope.json');plan=read(OUT/'case-matrix.json')
 for name,key in(('family-scope.json','scope_sha256'),('case-matrix.json','matrix_sha256'),('device-contract-boundary.json','device_boundary_sha256'),('ancestor-memory.bin','ancestor_sha256')):assert sha(OUT/name)==accept[key]
 for name,h in accept['implementation_pins'].items():assert sha(ROOT/name)==h,name
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert digest(rom)==scope['ROM_SHA256']
 raw=(OUT/'ancestor-memory.bin').read_bytes();seed=scope['ancestor']['state'];pyroot=Path(inspect.getfile(MPU)).resolve().parents[1]
 save(folder/'execution-inputs.json',dict(scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),
  implementation_pins=accept['implementation_pins'],ancestor_sha256=digest(raw),runtime=dict(Python=sys.version,executable=str(Path(sys.executable).resolve()),executable_sha256=sha(Path(sys.executable).resolve()),
  py65={str(x):sha(x)for x in sorted(pyroot.rglob('*.py'))}),new_Native_runs=0,controlled_reentry=True,Source_CPU_IR_callbacks=0))
 imp=importlib.util.spec_from_file_location('frozen_ee07_entry',OLD/'readable_entry.py');entry=importlib.util.module_from_spec(imp);imp.loader.exec_module(entry)
 names=['initial']+[f'{side}-{stage}'for stage in('forward','data-mapped','callee-return','final')for side in('CPU','Source')]
 streams={name:(folder/(name+'-memory.bin')).open('wb')for name in names};count=collections.Counter();parents=[];keys=[];failure=None;offset=0
 with(folder/'cases.jsonl').open('w')as results:
  for case in plan['cases']:
   left,right=fresh(rom,raw,seed,'CPU'),fresh(rom,raw,seed,'Source');r=NMIRegisters(**seed['registers']);cpu=MPU(memory=left)
   for k,v in seed['registers'].items():setattr(cpu,k,v)
   for address,value in case['patches'].items():
    address=int(address);assert address in(0x7E,0x470,0x471,0x472,0x473);left.ram[address]=right.ram[address]=value
   left.registers=cpu;right.registers=r;game=GameEngine(right,rom=rom,mapped=True);co=ProducerCoordinator(game);assert co.external_callback is None
   try:
    for step in range(case['steps']):
     before_reentry=dict(CPU=state(left,cpu),Source=state(right,r));before_bytes=software(left);assert before_bytes==software(right)and regs(cpu)==regs(r)
     assert r.pc==0xA074 and r.y==0x3B and r.sp==0 and r.p&8==0 and right.ram[0x7D]==0x3A and right.ram[0x401]==1
     cpu.pc=r.pc=0xA06F;cpu.y=r.y=0x3D
     assert software(left)==before_bytes==software(right)
     initial_state=state(right,r);initial_bytes=software(right);src=right.ram[0x470]|right.ram[0x471]<<8;dst=right.ram[0x472]|right.ram[0x473]<<8;jobs=right.ram[0x7E]
     addresses=[(src+i)&65535 for i in range(64)];assert all(a>=0x8000 for a in addresses)
     banks=[16,29,30,31];expected_payload=bytes(rom[16+banks[(a-0x8000)//8192]*8192+(a&8191)]for a in addresses)
     co.reset_audit();left.events=[];right.events=[];left.writes=[];right.writes=[];left.io_writes=[];right.io_writes=[];left.io_reads=[];right.io_reads=[];left.hardware_requests=[];right.hardware_requests=[];left.reads=[];right.reads=[]
     owner,result=entry.current_jsr(right,rom,r,co,scope['site']);assert result['status']=='returned'and not co._owners
     record=original(left,cpu,scope['site'])
     for key,value in co.points.items():assert record['points'][key]==value,(case['key'],step,key)
     assert record['palette']==co.palette
     assert software(left)==software(right)and regs(cpu)==regs(r)and left.banks==right.banks and left.port_image==right.port_image
     assert left.io_reads==right.io_reads==[]and left.io_writes==right.io_writes and left.hardware_requests==right.hardware_requests
     assert[(w['address'],w['value'])for w in left.writes]==[(w['address'],w['value'])for w in right.writes]
     assert left.io_writes==[dict(address=0xF000,value=0x3E),dict(address=0xE800,value=0xFD),dict(address=0xE000,value=0x30),dict(address=0xF000,value=0x3C),dict(address=0xE800,value=0xFB)]
     assert left.banks==[16,27,28,31]and right.ram[0xE1]==0x30 and right.ram[0x7D]==0x3A
     assert not any(w['address']==0x7D for w in right.writes)
     assert right.ram[0x380:0x3C4]==bytes((64,dst>>8,dst&255))+expected_payload+b'\xff'
     assert(right.ram[0x470]|right.ram[0x471]<<8)==(src+64)&65535 and(right.ram[0x472]|right.ram[0x473]<<8)==(dst+64)&65535
     advanced=(((dst+64)&65535)>>8)==0x28
     assert right.ram[0x401]==1+advanced and right.ram[0x7E]==jobs|4
     assert bool(co.palette)==advanced
     if advanced:
      assert right.ram[0x87:0x8A]==bytes((1,0,4))
      assert right.ram[0x120:0x140]==co.palette['entry'][1][0x100:0x120]
      count['ECEE_calls']+=1
     CPU_events=left.events;Source_events=right.events
     norm=lambda e:[(x['kind'],x['address'],x['value'],x['Y'])for x in e]
     assert norm(CPU_events)==norm(Source_events)
     expected_order=[('packet_write',0x380,64),('packet_write',0x381,dst>>8),('packet_write',0x382,dst&255)]
     for i,v in enumerate(expected_payload):expected_order.extend([('payload_read',addresses[i],v),('packet_write',0x383+i,v)])
     expected_order.append(('packet_write',0x3C3,255))
     assert[(x['kind'],x['address'],x['value'])for x in CPU_events]==expected_order
     for side,events in(('CPU',CPU_events),('Source',Source_events)):
      reads=[x for x in events if x['kind']=='payload_read'];assert[x['Y']for x in reads]==list(range(64))
      assert all(x['live00_01']==src for x in reads)
      if side=='CPU':assert all(x['original_PC']==0xBCBF for x in reads)
      else:assert all(x['original_PC']is None and x['Source_method']=='cityuiworkers_bc74_phase_1'for x in reads)
     assert bytes(right.sram)==initial_bytes[2048:]
     snapshots={'initial':initial_bytes}
     for key in('forward','data-mapped','callee-return'):
      snapshots['CPU-'+key]=record['points'][key][1];snapshots['Source-'+key]=co.points[key][1]
     snapshots['CPU-final']=software(left);snapshots['Source-final']=software(right)
     for name,b in snapshots.items():assert len(b)==10240;streams[name].write(b)
     point_states={k:v[0]for k,v in record.pop('points').items()};palette=palette_record(record.pop('palette'))
     key=f'{case["key"]}/step-{step+1:02d}';row=dict(key=key,parent=case['key'],step=step,spec=case,status='passed',
      ancestry=scope['ancestor']['memory_sha256'],controlled_reentry=dict(before=before_reentry,after=initial_state,changed_registers=['pc','y'],RAM_unchanged_by_reentry=True),
      initial_source=src,initial_destination=dst,initial_jobs=jobs,expected_payload_sha256=digest(expected_payload),CPU=record,
      Source=dict(events=owner.events,callbacks=co.audit,packet_events=Source_events,boundary_states={k:v[0]for k,v in co.points.items()},palette=palette_record(co.palette),final=state(right,r),CPU_IR_callbacks=0),
      CPU_packet_events=CPU_events,CPU_boundary_states=point_states,CPU_palette=palette,
      snapshot_offset=offset,snapshot_bytes=10240,snapshot_sha256={n:digest(b)for n,b in snapshots.items()},
      phase_advanced=advanced,request_bit2_set=True,constant_007D=0x3A,real_return=True,outer_RTS_executed=False,consumer_executed=False,new_Native_runs=0)
     results.write(json.dumps(row,separators=(',',':'))+'\n');offset+=10240;keys.append(key);count['CPU_instructions']+=record['instructions'];count['producer_invocations']+=1;count['payload_reads_each_side']+=64;count['payload_writes_each_side']+=64
    if case['steps']==16:assert right.ram[0x401]==2 and right.ram[0x472:0x474]==bytes.fromhex('0028')
    parents.append(case['key'])
   except Exception as exc:
    failure=dict(parent=case['key'],step=step,type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());save(folder/'failure.json',failure);break
 for f in streams.values():f.close()
 for n,h in accept['implementation_pins'].items():assert sha(ROOT/n)==h,n
 complete=failure is None and parents==[c['key']for c in plan['cases']]
 if complete:assert count['producer_invocations']==25 and count['ECEE_calls']==4
 validation=dict(status='passed_full_phase1_producer_family'if complete else'failed_or_incomplete',parent_cases=len(parents),Source_CPU_invocations=count['producer_invocations'],**dict(count),
  acceptance_sha256=sha(OUT/'acceptance.json'),scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),cases_sha256=sha(folder/'cases.jsonl'),
  buffers={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(folder.glob('*-memory.bin'))},failure=failure,
  real_return_count=count['producer_invocations'],new_callers=0,production_Source_changes=0,new_algorithms=0,Source_CPU_IR_callbacks=0,
  Native_new_runs=0,consumer_executions=0,outer_RTS_executions=0,field_classification_changes=0,raw_classification_changes=0,remaining=323,whole_game_closure_proven=False)
 save(folder/'validation.json',validation);print(json.dumps(validation,ensure_ascii=False))
if __name__=='__main__':main()
