#!/usr/bin/env python3
"""Root-only existing readable Source versus independently executed ROM CPU."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,inspect,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'analysis/wp03-ee07-return-family'
from py65.devices.mpu6502 import MPU
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.game_engine import GameEngine
from source.recovered.scene_coordinator import SceneCoordinator

def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def read(p):return json.loads(p.read_text())
def save(p,x):
 assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def regs(r):return{k:getattr(r,k)for k in('pc','a','x','y','p','sp')}
def software(m):return bytes(m.ram)+bytes(m.sram)
def state(m,r):return dict(registers=regs(r),banks=list(m.banks),ports=dict(m.port_image),RAM_sha256=digest(bytes(m.ram)),SRAM_sha256=digest(bytes(m.sram)))
def fingerprint(m,r):return(software(m),regs(r),tuple(m.banks),list(m.io_reads),list(m.io_writes),dict(m.port_image),list(m.writes))

class ObservedBus(ServiceMemory):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.registers=None;self.opcode_pc=None;self.writes=[];self.tags={};self.reads=[];self.probe=None
 def __getitem__(self,a):
  value=super().__getitem__(a)
  if isinstance(a,int)and self.probe is not None and a in self.probe['addresses']:
   self.reads.append(dict(PC=self.opcode_pc,address=a,value=value,tag=self.tags.get(a),probe=self.probe['kind']))
  return value
 def __setitem__(self,a,v):
  if isinstance(a,int):
   q=a&65535;p=q&2047 if q<8192 else q
   if q<8192 or 0x6000<=q<0x8000:
    before=self.ram[p]if q<8192 else self.sram[q-0x6000]
    tag=dict(PC=self.opcode_pc,kind='original_instruction'if self.opcode_pc is not None else'production_Source')
    self.tags[p]=tag;self.writes.append(dict(address=q,value=v&255,before=before,tag=tag))
  return super().__setitem__(a,v)

class AuditedCoordinator(SceneCoordinator):
 def __init__(self,game,site,withhold):
  super().__init__(game);self.site=site;self.mode='missing'if withhold else'actual';self.audit=[];self.references=[];self.forward=None;self.callee_return=None;self.real_callee_runs=0
 def _resolve_call(self,call):
  self.references.append(call);is_callee=call.target==self.site['target']and list(call.entry_banks[1:3])==self.site['target_pair']
  before=state(self.memory,call.registers);before_bytes=software(self.memory)
  if is_callee and self.mode!='actual':
   result=dict(status='dependency'if self.mode=='missing'else'returned',test_only_withheld_callee=True)
  else:
   if is_callee:
    assert self.forward is None;self.forward=(before,before_bytes);self.real_callee_runs+=1
   result=super()._resolve_call(call)
   if is_callee:
    self.callee_return=(state(self.memory,call.registers),software(self.memory))
  self.audit.append(dict(target=call.target,entry_banks=list(call.entry_banks),return_pc=call.return_pc,expected_sp=call.expected_sp,
                         status=result.get('status'),mode=self.mode,before=before,after=state(self.memory,call.registers)))
  return result

def initial(rom,s,site):
 ram=bytearray((i*29+17)&255 for i in range(2048));sram=bytes((i*11+23)&255 for i in range(8192))
 patches={0x401:site['phase'],0x7E:s['PPU_jobs'],0xE1:s['raw_E1'],0xE2:s['raw_E2'],0xE3:(s['raw_E2']+1)&255,
          0x470:0xA1,0x471:0xB2,0x472:0xC3,0x473:0xD4}
 for a,v in patches.items():ram[a]=v
 m=ObservedBus(rom,ram,sram,(s['data_bank'],27,28,31))
 m.port_image.update({0xE000:s['raw_E1'],0xE800:s['raw_E2']|0xC0,0xF000:(s['raw_E2']+1)&255})
 return m

def original_cpu(m,s,site):
 cpu=MPU(memory=m)
 for k,v in s['registers'].items():setattr(cpu,k,v)
 m.registers=cpu;S=cpu.sp;trace=[];forward=callee_return=None;callee_rts=None;five=[];actual_jsr=None;EE52=None
 for n in range(400):
  pc=cpu.pc;bank=m.banks[(pc-0x8000)//8192];assert pc>=0x8000
  if pc==site['continuation']and bank==27:break
  assert pc!=site['continuation'],'Continuation PC reached in wrong code bank'
  m.opcode_pc=pc;m.probe=None;start=len(m.writes);before=state(m,cpu)
  if pc in(0xEE1F,0xEE25):
   pointer=m.ram[0x59]|m.ram[0x5A]<<8
   m.probe=dict(kind='inline_data',addresses=[(pointer+cpu.y)&65535])
  if pc in(0xEE10,0xEE17):m.probe=dict(kind='current_JSR_PLA',addresses=[0x100+((cpu.sp+1)&255)])
  if pc==site['target']and m.banks[1:3]==site['target_pair']:
   assert forward is None;forward=(state(m,cpu),software(m))
  if pc==site['body_rts']:
   assert bank==site['target_pair'][1 if pc>=0xC000 else 0]
   assert m[pc]==0x60;callee_rts=dict(before=before,frame=[m[0x100+((cpu.sp+i)&255)]for i in(1,2)])
  if pc==0xEE52:EE52=dict(before=before,frame=[m[0x100+((cpu.sp+i)&255)]for i in(1,2)])
  cpu.step();after=state(m,cpu);writes=m.writes[start:]
  if pc==site['call_pc']:
   assert bytes(m.rom[16+27*8192+(pc&8191):16+27*8192+(pc&8191)+3])==bytes.fromhex('2007ee')
   assert cpu.pc==0xEE07 and cpu.sp==(S-2)&255
   assert[(w['address'],w['value'])for w in writes]==[(0x100+S,(pc+2)>>8),(0x100+((S-1)&255),(pc+2)&255)]
   actual_jsr=dict(before=before,after=after,pushes=writes)
  if pc in(0xEE3B,0xEE3F,0xEE43,0xEE46,0xEE49):five.extend(writes)
  if pc==site['body_rts']:
   assert cpu.pc==0xEE4D and cpu.sp==(S-3)&255;callee_rts['after']=after;callee_return=(after,software(m))
  if pc==0xEE52:
   assert cpu.pc==site['continuation']and cpu.sp==S;EE52['after']=after
  trace.append(dict(bank=bank,pc=pc,before=before['registers'],after=after['registers'],writes=writes))
 else:raise AssertionError('Original CPU instruction budget exhausted')
 m.opcode_pc=None;m.probe=None
 assert actual_jsr and forward and callee_return and EE52 and callee_rts
 assert[(w['address'],w['value'])for w in five]==[(0x100+((S-i)&255),v)for i,v in enumerate(((site['call_pc']+4)>>8,(site['call_pc']+4)&255,s['raw_E2'],0xEE,0x4C))]
 assert callee_rts['frame']==[0x4C,0xEE]and EE52['frame']==[(site['call_pc']+4)&255,(site['call_pc']+4)>>8]
 assert not any(t['pc']==site['continuation']for t in trace)
 return cpu,dict(instructions=len(trace),trace=trace,actual_JSR=actual_jsr,five_pushes=five,real_callee_RTS=callee_rts,real_EE52_RTS=EE52,
                 inline_and_PLA_reads=m.reads,forward=forward,callee_return=callee_return)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--root-execution-authorized',action='store_true');a=parser.parse_args();assert a.root_execution_authorized
 folder=a.out.resolve();assert folder.parent==OUT and not folder.exists();folder.mkdir()
 accept=read(OUT/'acceptance.json');scope=read(OUT/'family-scope.json');matrix=read(OUT/'case-matrix.json')
 assert sha(OUT/'family-scope.json')==accept['scope_sha256']and sha(OUT/'case-matrix.json')==accept['matrix_sha256']
 for name,h in accept['implementation_pins'].items():assert sha(ROOT/name)==h,name
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert digest(rom)==scope['ROM_SHA256']
 runtime_root=Path(inspect.getfile(MPU)).resolve().parents[1]
 save(folder/'execution-inputs.json',dict(acceptance_sha256=sha(OUT/'acceptance.json'),scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),
  implementation_pins=accept['implementation_pins'],runtime=dict(Python=sys.version,executable=str(Path(sys.executable).resolve()),executable_sha256=sha(Path(sys.executable).resolve()),
  py65={str(p):sha(p)for p in sorted(runtime_root.rglob('*.py'))}),actual_natural_context=None,Native_new_runs=0))
 spec=importlib.util.spec_from_file_location('ee07_readable_entry',OUT/'readable_entry.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 streams={name:(folder/(name+'-memory.bin')).open('wb')for name in('initial','CPU-forward','Source-forward','CPU-callee-return','Source-callee-return','CPU-final','Source-final')}
 counts=collections.Counter();groups=collections.Counter();failure=None;keys=[];offset=0
 with(folder/'cases.jsonl').open('w')as results:
  for s in matrix['cases']:
   try:
    site=scope['sites'][s['site_index']];left,right=initial(rom,s,site),initial(rom,s,site);r=NMIRegisters(**s['registers']);right.registers=r
    assert software(left)==software(right);initial_bytes=software(left)
    game=GameEngine(right,rom=rom,mapped=True);co=AuditedCoordinator(game,site,s['withhold']);assert co.external_callback is None
    owner,res=mod.current_jsr(right,rom,r,co,site);wait_evidence=[]
    if s['withhold']:
     assert res['status']=='dependency'and r.pc==site['target']and r.sp==(s['registers']['sp']-5)&255
     callee_calls=[x for x in co.references if x.target==site['target']];assert len(callee_calls)==1;pending=callee_calls[0]
     old=fingerprint(right,r);co.mode='fake';fake=owner.resume()
     assert fake['status']=='dependency'and fingerprint(right,r)==old
     assert [x for x in co.references if x.target==site['target']][-1]is pending
     wait_evidence.append(dict(missing_status=res['status'],fake_status=fake['status'],fake_zero_bus_REG_progress=True,same_pending_callee=True))
     co.mode='actual';res=owner.resume();assert [x for x in co.references if x.target==site['target']][-1]is pending
     counts['strict_withhold_parents']+=1;counts['fake_zero_progress_checks']+=1
    assert res['status']=='returned'and co.real_callee_runs==1 and not co._owners
    assert r.pc==site['continuation']and r.sp==s['registers']['sp']
    cpu,record=original_cpu(left,s,site)
    for key,value in(('forward',co.forward),('callee_return',co.callee_return)):
     assert record[key]==value,(s['key'],key,record[key][0],value[0])
    assert software(left)==software(right)and regs(cpu)==regs(r)and left.banks==right.banks
    assert left.io_reads==right.io_reads==[]and left.io_writes==right.io_writes and left.port_image==right.port_image
    assert left.hardware_requests==right.hardware_requests
    assert[(x['address'],x['value'])for x in left.writes]==[(x['address'],x['value'])for x in right.writes]
    assert left.banks==[s['data_bank'],27,28,31]and right.ram[0xE1]==s['raw_E1']
    expected=[dict(address=0xF000,value=(site['selector']+1)&255),dict(address=0xE800,value=site['selector']|0xC0),
              dict(address=0xF000,value=(s['raw_E2']+1)&255),dict(address=0xE800,value=s['raw_E2']|0xC0)]
    assert left.io_writes==expected
    if s['site_index']==0:
     assert right.ram[0x401]==1 and right.ram[0x470:0x474]==bytes((0,0x88,0,0x24));counts['stateful_full_returns']+=1
    else:
     assert right.ram[0x401]==1 and right.ram[0x470:0x474]==bytes.fromhex('a1b2c3d4');counts['busy_full_returns']+=1
    S=s['registers']['sp'];residue=[right.ram[0x100+((S-i)&255)]for i in range(7)]
    expected_residue=[0xA0,(site['call_pc']+4)&255,0xEE,0x51,s['raw_E2'],0xBC if s['site_index']==0 else 0xC4,0x76 if s['site_index']==0 else 0x3A]
    assert residue==expected_residue
    plas=[x for x in record['inline_and_PLA_reads']if x['probe']=='current_JSR_PLA'];inline=[x for x in record['inline_and_PLA_reads']if x['probe']=='inline_data']
    assert len(plas)==2 and all(x['tag']==dict(PC=site['call_pc'],kind='original_instruction')for x in plas)
    assert[(x['PC'],x['address'],x['value'])for x in inline]==[(0xEE1F,site['call_pc']+3,site['target']&255),(0xEE25,site['call_pc']+4,site['target']>>8)]
    allowed=set(range(0x100,0x200))|set(range(5))|set(range(0x58,0x5E))|{0xE2,0xE3}
    if s['site_index']==0:allowed|={0x401,0x470,0x471,0x472,0x473}
    assert all(v==initial_bytes[i]for i,v in enumerate(right.ram)if i not in allowed)
    assert bytes(right.sram)==initial_bytes[2048:]
    buffers={'initial':initial_bytes,'CPU-forward':record['forward'][1],'Source-forward':co.forward[1],
             'CPU-callee-return':record['callee_return'][1],'Source-callee-return':co.callee_return[1],
             'CPU-final':software(left),'Source-final':software(right)}
    for name,b in buffers.items():assert len(b)==10240;streams[name].write(b)
    del record['forward'];del record['callee_return']
    row=dict(case=s['key'],spec=s,status='passed',CPU=record,Source=dict(final=state(right,r),audit=co.audit,events=owner.events,real_callee_runs=co.real_callee_runs,
       callback_return=co.callee_return[0],wait_evidence=wait_evidence,CPU_IR_callbacks=0,callee_seed_return=False),
       snapshot_offset=offset,snapshot_bytes=10240,snapshot_sha256={name:digest(b)for name,b in buffers.items()},
       final_stack_residue=residue,full_2K_8K_checked=True,all_nonwrite_RAM_checked=True,whole_SRAM_unchanged=True,
       actual_outer_RTS=False,actual_natural_origin=False,classification_changes=0)
    results.write(json.dumps(row,separators=(',',':'))+'\n');offset+=10240;groups[s['group']]+=1;keys.append(s['key']);counts['instructions']+=record['instructions']
   except Exception as exc:
    failure=dict(case=s['key'],type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());save(folder/'failure.json',failure);break
 for f in streams.values():f.close()
 for name,h in accept['implementation_pins'].items():assert sha(ROOT/name)==h,name
 complete=failure is None and keys==[s['key']for s in matrix['cases']]and dict(groups)==matrix['groups']
 if complete:assert counts['stateful_full_returns']==counts['busy_full_returns']==328 and counts['strict_withhold_parents']==counts['fake_zero_progress_checks']==2
 result=dict(status='passed_full_declared_return_family'if complete else'failed_or_incomplete',CPU_parent_cases=len(keys),Source_parent_cases=len(keys),
  **dict(counts),groups=dict(groups),cases_sha256=sha(folder/'cases.jsonl'),buffers={p.name:dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(folder.glob('*-memory.bin'))},
  scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),
  failure=failure,Native_new_runs=0,outer_RTS_executions=0,production_Source_changes=0,production_CPU_IR_fallback_added=False,
  field_classification_changes=0,raw_classification_changes=0,remaining=323,unknown_unique_services=None,completion_percentage=None,whole_game_closure_proven=False)
 save(folder/'validation.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
