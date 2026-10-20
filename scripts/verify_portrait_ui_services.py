#!/usr/bin/env python3
"""Unchanged original CPU versus independent portrait source; no helper oracle."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.portrait_ui_services import PortraitUIServices,PortraitData,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall

class OriginalBus(Bus):
 def __init__(self,rom,ram,sram,banks):
  super().__init__(rom,'zero');self.ram[:]=ram;self.sram[:]=sram;self.banks[:]=banks;self.bank_initialized=[True]*4;self.protect=0x4C;self.ports=[]
 def __setitem__(self,a,v):
  if ServiceMemory.is_write_port(a&65535):self.ports.append(dict(address=a&65535,value=v&255))
  super().__setitem__(a,v)
 def __getitem__(self,a):
  if isinstance(a,int)and 0x2000<=a<0x6000:raise RuntimeError('Portrait closure has no hardware reads')
  return super().__getitem__(a)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase12/portraits');p.add_argument('--quick',action='store_true');a=p.parse_args()
 rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256;data=PortraitData.from_rom(rom);rng=random.Random(0x120025)
 counts=Counter();fail=[];samples=[];visited=set();prefixes=0;guards=[]
 def fresh():return bytearray(rng.randbytes(2048)),bytearray(rng.randbytes(8192))
 def compare(kind,entry,ram,sram,label,x=0,y=73,p=32,sp=253,banks=(17,25,26,31),resume_count=0,caller=None):
  nonlocal prefixes
  initial_a=ram[0x51];return_pc=0x2468
  if caller is None:
   ram[0x100+((sp+1)&255)]=0x67;ram[0x100+((sp+2)&255)]=0x24
  else:
   sp=caller['sp'];return_pc=((ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8)+1)&65535
  actual=OriginalBus(rom,ram,sram,list(banks));source=ServiceMemory(rom,ram,sram,banks)
  regs=NMIRegisters(**caller)if caller is not None else NMIRegisters(a=initial_a,x=x,y=y,p=p,sp=sp,pc=entry);ctrl=PortraitUIServices(source,data)
  cpu=MPU(memory=actual,pc=entry);actual.cpu=cpu
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(regs,k))
  try:
   result=ctrl.run_entry(entry,regs)
   total_instructions=0
   for segment in range(resume_count+1):
    if segment:result=ctrl.resume()
    stop=regs.pc if result['status']=='dependency'else return_pc
    for n in range(200000):
     boundary=n and cpu.pc==stop and cpu.sp==regs.sp
     if boundary and result['status']=='dependency':
      boundary=all(getattr(cpu,k)==getattr(regs,k)for k in('a','x','y','p'))and bytes(actual.ram)==bytes(source.ram)and actual.ports==source.io_writes
     if boundary:break
     actual.pc=cpu.pc;actual.step_no=total_instructions+n;origin=actual.origin(cpu.pc)
     if origin:visited.add((origin[0],cpu.pc))
     cpu.step()
    else:raise AssertionError(f'Original budget ${cpu.pc:04X}')
    total_instructions+=n
    rd=[(hex(i),actual.ram[i],source.ram[i])for i in range(2048)if actual.ram[i]!=source.ram[i]]
    sd=[(hex(i+0x6000),actual.sram[i],source.sram[i])for i in range(8192)if actual.sram[i]!=source.sram[i]]
    assert not rd and not sd,('memory',rd[:8],sd[:4])
    rg=[(k,getattr(cpu,k),getattr(regs,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(regs,k)]
    assert not rg,('registers',rg)
    assert actual.banks==source.banks,('banks',actual.banks,source.banks)
    assert actual.ports==source.io_writes,('ports',actual.ports,source.io_writes)
   counts[kind]+=1;prefixes+=result['status']=='dependency'
   if sum(v['kind']==kind for v in samples)<2:samples.append(dict(kind=kind,input=label,entry=entry,status=result['status'],original_instructions=total_instructions,registers=result['registers'],layers=result['portrait_layers']))
  except Exception as exc:fail.append(dict(kind=kind,entry=entry,input=label,error=str(exc)))
 ids=range(237)if not a.quick else(0,109,131,236)
 for ident in ids:
  for side in range(2):
   for frame in range(5):
    for talk in range(2):
     ram,sram=fresh();ram[0]=ident;ram[0xA]=165;ram[0xA4]=frame;ram[0x4BC]=208 if side else 0;ram[0x7C]=0;ram[0x7E]=1;ram[0x304]=0;ram[0x303]=0;ram[0x5E]=8 if talk else 0;sram[0xFEA]=0
     compare('all237_portraits_sides_five_frames_two_mouths',0xA000,ram,sram,[ident,side,frame,talk],x=side)
 # Each real mouth predicate, override ordering and preserved signed frame.
 for flags in (0,4,8,12,255):
  for a4 in (0,3,4,0x80,0x83,0x84):
   for jobs,text,phase,blink in ((0,0,0,8),(1,255,0,8),(1,0,1,8),(1,0,0,0),(1,0,0,8)):
    for side in (0,1):
     ram,sram=fresh();ram[0]=131;ram[0xA]=165;ram[0xA4]=a4;ram[0x4BC]=208;ram[0x7C]=0;ram[0x7E]=jobs;ram[0x304]=text;ram[0x303]=phase;ram[0x5E]=blink;sram[0xFEA]=flags
     compare('mouth_gate_override_and_signed_frame',0xCE1F,ram,sram,[flags,a4,jobs,text,phase,blink,side],x=side,p=(32,33,98,160,227)[blink%5],sp=(253,245)[side])
 # Exact coordinates/clip/overflow and initial OAM cursor, including odd values.
 for ycoord in (0,127,159,160,165,224,239,240,255):
  for xcoord in (0,1,16,208,248,255):
   for cursor in (0,4,176,240,248,252,253,254,255):
    ram,sram=fresh();ram[0]=0;ram[0xA]=ycoord;ram[0xA4]=0;ram[0x4BC]=xcoord;ram[0x7C]=cursor;ram[0x7E]=0;sram[0xFEA]=0
    compare('coordinates_clip_wrap_OAM_saturation',0xA000,ram,sram,[ycoord,xcoord,cursor],x=cursor&1)
 # Byte IDs237..255 deliberately read adjacent original data, not named officers.
 for ident in range(237,256):
  for side in (0,1):
   ram,sram=fresh();ram[0]=ident;ram[0xA]=165;ram[0xA4]=0;ram[0x4BC]=0;ram[0x7C]=0;ram[0x7E]=0;sram[0xFEA]=0
   compare('adjacent_byte_ID_data_not_officer_identity',0xA000,ram,sram,[ident,side],x=side)
 # Independent fixed helper with arbitrary RAM descriptors and cutoff/template offsets.
 for cutoff in (0,1,127,160,255):
  for tile in(0,64,255):
   for attr in(0,3,64,128,255):
    for cursor in (0,248,252,255):
     ram,sram=fresh();ram[0:2]=bytes((0,4));ram[0x400:0x40D]=bytes((0,128,35,0,128,255,64,255,255,0,128,1,128));ram[0xA]=165;ram[0xC]=208;ram[3]=tile;ram[2]=attr;ram[4]=cutoff;ram[0x7C]=cursor
     compare('F1B7_caller_parameters_and_terminator',0xF1B7,ram,sram,[cutoff,tile,attr,cursor])
 # Original loops with no usable descriptor/return are real resumable CPU prefixes.
 for cursor,cutoff in((0,255),(1,0)):
  ram,sram=fresh();ram[0:2]=bytes((0,4));ram[0x400:0x500]=bytes(256);ram[0xA]=0;ram[0xC]=0;ram[2]=ram[3]=0;ram[4]=cutoff;ram[0x7C]=cursor
  compare('cyclic_descriptor_same_owner_two_prefixes',0xF1B7,ram,sram,[cursor,cutoff],resume_count=1)
 # Exact untouched helper frames captured during the unchanged original attack CPU.
 actual_call_fixtures=[]
 for path in sorted((ROOT/'analysis/phase12/dependencies/callee-inputs').glob('bank25-A000-*.json')):
  meta=json.loads(path.read_text());prefix=path.with_suffix('');ram=bytearray(Path(str(prefix)+'-ram.bin').read_bytes());sram=bytearray(Path(str(prefix)+'-sram.bin').read_bytes())
  assert hashlib.sha256(ram).hexdigest()==meta['RAM_sha256']and hashlib.sha256(sram).hexdigest()==meta['SRAM_sha256']
  actual_call_fixtures.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),RAM_sha256=meta['RAM_sha256'],SRAM_sha256=meta['SRAM_sha256'],fixture_kind=meta['fixture_kind']))
  compare('actual_attack_callee_frame_no_stack_preparation',0xA000,ram,sram,str(path.relative_to(ROOT)),banks=tuple(meta['entry_banks']),caller=meta['registers_before'])
 # Guard clauses are source-only contracts; they are not ROM cases.
 ram,sram=fresh();m=ServiceMemory(rom,ram,sram,(17,25,26,31));c=PortraitUIServices(m,data)
 for name,action in [('unknown_entry',lambda:c.run_entry(0xA003,NMIRegisters())),('missing_caller',lambda:c.run_entry()),('wrong_mapper_pair',lambda:PortraitUIServices(ServiceMemory(rom,ram,sram,(17,23,24,31)),data).run_entry(0xA000,NMIRegisters()))]:
  try:action();passed=False
  except ValueError:passed=True
  guards.append(dict(name=name,passed=passed))
 ram[0:2]=bytes((0,4));ram[0x400:0x500]=bytes(256);ram[0xA]=0;ram[4]=255;ram[0x7C]=0;m=ServiceMemory(rom,ram,sram,(17,25,26,31));c=PortraitUIServices(m,data);r=NMIRegisters(sp=253,pc=0xF1B7);call=ServiceCall(0xF1B7,0x2468,'fixture',r,m,tuple(m.banks),255)
 first=c(call);second=c(call);guards.append(dict(name='same_owner_never_fakes_cyclic_RTS',passed=first['status']==second['status']=='dependency'and r.sp==253))
 try:c.run_entry(0xF1B7,r);passed=False
 except RuntimeError:passed=True
 guards.append(dict(name='pending_reentry_rejected',passed=passed))
 bad=ServiceCall(0xA003,0x2468,'unknown',r,m,tuple(m.banks),255);guards.append(dict(name='unknown_callback_preserves_dependency',passed=c(bad)['status']=='dependency'))
 fail.extend(dict(kind='sourceguard',guard=g)for g in guards if not g['passed'])
 a.out.mkdir(parents=True,exist_ok=True)
 report=dict(schema='phase12-portrait-ui-v1',status='passed'if not fail else'failed',quick=a.quick,rom_sha256=ROM_SHA256,rom_cpu_case_count=sum(counts.values()),
  original_complete_case_count=sum(counts.values())-prefixes,original_prefix_case_count=prefixes,source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(fail),
  counts=dict(counts),comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,free_CPU_stack_residue='included',registers='AXYP/SP/PC',ordered_IO_ports=True,all_mapper_banks=True,hardware_reads=0),
  source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256=sha(ROOT/'source/recovered/portrait_ui_services.py'),validator_sha256=sha(Path(__file__)),
  guards=guards,failures=fail,samples=samples,actual_call_fixtures=actual_call_fixtures)
 (a.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (a.out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],CPU=report['rom_cpu_case_count'],guards=len(guards),prefix=prefixes,failed=len(fail),failures=fail[:8]),ensure_ascii=False))
 return bool(fail)
if __name__=='__main__':raise SystemExit(main())
