#!/usr/bin/env python3
"""Independent originalCPU city-aux access provenance, never NativePC trace.

Frozen Native RAM/SRAM initializes a declared E066 context. Main software and
explicit NMI/IRQ arrivals run only in the validator-side py65 oracle. No scene,
request, result, readiness, pointer or acknowledgement bytes are fabricated.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_succession import ROM_SHA256
from inspect_game_data import OPS,SIZES
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(c):return{k:getattr(c,k)for k in REGS}
WATCH={(10,p)for p in(0xB49C,0xBD7A,0xBD8D,0xBD95,0xBDA3,0xBDF8,0xBE02,0xBE40,0xBE7B,0xBE94,0xBEB4,0xBEC1,0xBEC7)}|{(11,p)for p in(0xD105,0xD126,0xD36F,0xD152)}
class TraceMemory(ServiceMemory):
 def __init__(self,*a,**k):
  super().__init__(*a,**k);self.context=None;self.aux=[];self.city=[]
 def __getitem__(self,a):
  v=super().__getitem__(a)
  if isinstance(a,int):self.access('read',a,v)
  return v
 def __setitem__(self,a,v):
  if isinstance(a,int):self.access('write',a,v&255)
  super().__setitem__(a,v)
 def access(self,kind,a,v):
  if self.context is None or not 0x6000<=a<0x63C0:return
  x=dict(self.context,kind=kind,address=a,value=v,city=(a-0x6000)//32,city_offset=(a-0x6000)%32)
  self.city.append(x)
  if x['city_offset']in(1,28,29,30,31):self.aux.append(x)
 def observe(self,c,step,event,chain):
  pc=c.pc;b=self.banks[(pc-0x8000)//8192]if pc>=0x8000 else None
  off=16+b*8192+(pc&8191)if b is not None else None
  op,mode=OPS[self.rom[off]]if off is not None else('RAM','i');sz=SIZES[mode]
  operand=int.from_bytes(self.rom[off+1:off+sz],'little')if off is not None else 0
  ptr=operand if mode=='iy'else(operand+c.x)&255 if mode=='ix'else None
  base=self.ram[ptr]|self.ram[(ptr+1)&255]<<8 if ptr is not None else None
  self.context=dict(step=step,event=event,physical_bank=b,CPU_PC=pc,ROM_offset=off,raw_hex=self.rom[off:off+sz].hex()if off is not None else'',opcode=op,mode=mode,operand=operand,registers=reg(c),actual_zp_pointer=ptr,actual_zp_base=base,actual_index_Y=c.y if mode=='iy'else None,pointer_city=(base-0x6000)//32 if base is not None and 0x6000<=base<0x63C0 else None,pointer_city_bias=(base-0x6000)%32 if base is not None and 0x6000<=base<0x63C0 else None,caller_chain=list(chain[-8:]))
  return b,op,mode,operand

def run(rom,prefix,out,cohort,updates,pre_nmi=0,actor=8):
 ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
 raw_banks=list(ram[0xDE:0xE1]);m=TraceMemory(rom,ram,sram,tuple([v&31 for v in raw_banks]+[31]),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 prep=[]
 if cohort!='native_baseline':
  for address,value,reason in[(0x6000+4*32+2,1,'City4 realgold257 low'),(0x6000+4*32+3,1,'City4 realgold257 high'),(0x63C0+actor*12+8,132,'Target officer troops900 low'),(0x63C0+actor*12+9,3,'Target officer troops900 high'),(0x6000+4*32+1,0 if cohort=='aux0'else 44,'City4 aux1 comparator cohort only')]:
   old=m[address]
   if old!=value:prep.append(dict(address=address,before=old,after=value,reason=reason));m[address]=value
 before_ram=bytes(m.ram);before_sram=bytes(m.sram);c=MPU(memory=m);c.a=17;c.x=31;c.y=63;c.p=32;c.sp=255;c.pc=0xE066
 initial=reg(c);events=[];watch=[];frames=[];chain=[];steps=0;NMI=IRQ=0
 def step(event):
  nonlocal steps
  bank,op,mode,target=m.observe(c,steps,event,chain)
  if(bank,c.pc)in WATCH:
   watch.append(dict(step=steps,event=event,physical_bank=bank,PC=c.pc,registers=reg(c),base20=m.ram[0x20]|m.ram[0x21]<<8,city_scan36=m.ram[0x36],selected_officer38=m.ram[0x38],selected_city39=m.ram[0x39],AI_budget=m.sram[0xF5D],troops_actor=int.from_bytes(m.sram[0x3C0+actor*12+8:0x3C0+actor*12+10],'little'),city4_gold=int.from_bytes(m.sram[130:132],'little'),city4_reserve=int.from_bytes(m.sram[140:142],'little'),caller_chain=list(chain[-8:])))
  oldpc=c.pc;oldsp=c.sp;c.step();steps+=1;m.context=None
  if op=='JSR':chain.append(dict(physical_bank=bank,call_PC=oldpc,target=target,return_PC=(oldpc+3)&65535,caller_SP=oldsp))
  elif op=='RTS':
   match=next((i for i in range(len(chain)-1,-1,-1)if chain[i]['return_PC']==c.pc and chain[i]['caller_SP']==c.sp),None)
   if match is not None:del chain[match:]
  elif op=='RTI':
   if chain and chain[-1].get('kind')=='interrupt':chain.pop()
 def until(pc,sp,event,limit=1500000):
  for n in range(limit):
   if n and(c.pc,c.sp)==(pc,sp):return
   if c.pc==0xFB28 and m.ram[0x62]and not c.p&4:
    nonlocal IRQ
    savedpc,savedsp=c.pc,c.sp;chain.append(dict(kind='interrupt',target='IRQ',return_PC=savedpc,caller_SP=savedsp));c.irq();IRQ+=1
    until(savedpc,savedsp,event+'/explicit_IRQ',100000)
   else:step(event)
  raise RuntimeError(f'Explicit originalCPU budget at{c.pc:04X}/SP{c.sp:02X}')
 boundary=None
 try:
  for delay in range(pre_nmi):
   pc,sp=c.pc,c.sp;chain.append(dict(kind='interrupt',target='NMI',return_PC=pc,caller_SP=sp));c.nmi();NMI+=1;until(pc,sp,f'pre-main_NMI{delay}')
  for tick in range(updates):
   until(0xE066,c.sp,f'main{tick}')
   events.append(dict(tick=tick,kind='main_E066_boundary',registers=reg(c),global_main=m.ram[0x7A],ruler=m.sram[0xF03],request=m.sram[0xF8B],city_controller=list(m.ram[0x400:0x403]),step=steps))
   if m.ram[0x7A]not in(1,2):boundary=dict(kind='original_other_global_boundary',global_main=m.ram[0x7A],registers=reg(c));break
   pc,sp=c.pc,c.sp;chain.append(dict(kind='interrupt',target='NMI',return_PC=pc,caller_SP=sp));c.nmi();NMI+=1;until(pc,sp,f'NMI{tick}')
   frames.append(dict(tick=tick,step=steps,global_main=m.ram[0x7A],ruler=m.sram[0xF03],request=m.sram[0xF8B],budget=m.sram[0xF5D],city4_gold=int.from_bytes(m.sram[130:132],'little'),city4_reserve=int.from_bytes(m.sram[140:142],'little'),troops_actor=int.from_bytes(m.sram[0x3C0+actor*12+8:0x3C0+actor*12+10],'little')))
  else:boundary=dict(kind='explicit_main_update_budget',updates=updates,registers=reg(c))
 except Exception as exc:boundary=dict(kind='explicit_unresolved_or_budget_boundary',reason=str(exc),registers=reg(c),banks=list(m.banks))
 groups={}
 for x in m.city:
  key=(x['physical_bank'],x['CPU_PC'],x['kind']);groups.setdefault(key,set()).add(x['city_offset'])
 for x in m.aux:
  fields=groups[x['physical_bank'],x['CPU_PC'],x['kind']]
  if(x['physical_bank'],x['CPU_PC'])==(10,0xBD97):role='dedicated_AI_recruitment_overlapping_word_gate'
  elif x['physical_bank']==10 and 0xA442<=x['CPU_PC']<0xA450:role='FF_scan_with_actual_caller_capacity_context'
  elif len(fields)==32:role='whole_record_copy_or_clear_broad_access'
  else:role='unresolved_contextual_access_not_official_field_name'
  x['access_role']=role
 out.mkdir(parents=True,exist_ok=True)
 def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 (out/'input-ram.bin').write_bytes(before_ram);(out/'input-sram.bin').write_bytes(before_sram);(out/'final-ram.bin').write_bytes(m.ram);(out/'final-sram.bin').write_bytes(m.sram)
 save('auxiliary-accesses.json',m.aux);save('city-accesses.json',m.city);save('watchpoints.json',watch);save('main-boundaries.json',events);save('update-fields.json',frames)
 result=dict(schema='phase18-original-CPU-city-auxiliary-trace-v1',status='bounded_trace_complete',rom_sha256=ROM_SHA256,cohort=cohort,target_officer=actor,explicit_pre_main_NMI_arrivals=pre_nmi,native_memory_prefix=str(prefix.relative_to(ROOT)),native_memory_sha256={str(Path(str(prefix)+e).relative_to(ROOT)):sha(str(prefix)+e)for e in('-ram.bin','-sram.bin')},original_initial_registers=initial,raw_native_PRG_shadows=raw_banks,initial_physical_banks=[v&31 for v in raw_banks]+[31],prepared_bytes=prep,postentry_memory_injections=0,original_instructions=steps,explicit_NMI_arrivals=NMI,explicit_IRQ_arrivals=IRQ,main_boundaries=len(events),boundary=boundary,auxiliary_reads=sum(x['kind']=='read'for x in m.aux),auxiliary_writes=sum(x['kind']=='write'for x in m.aux),auxiliary_role_counts=dict(Counter(x['access_role']for x in m.aux)),BD95_visits=sum(x['physical_bank']==10 and x['PC']==0xBD95 for x in watch),source_pipeline_executed=False,Native_internal_CPU_trace=False,core_frames_generated=0,hardware_inputs=dict(PPUSTATUS='explicit0',APUSTATUS='explicit0',NamcoIRQcounter='explicit127',controllers=[0,0]),limits=['DeclaredE066 AXYP/SP and mappedbank shadows from frozenNative memory do not provide originalcore internalCPU registers or PC.','Explicit NMI/IRQ arrivals are software oracle inputs, not Nativevideo frames or cycle timing.','Nativebaseline changes no RAM/SRAM; comparator cohorts change only disclosed validcity/officer numeric bytes and aux1 beforeentry.','No request/ready/result/ack/controller/pointer bytes are prepared or injected afterentry.','Trace budget/unknown hardware boundary is retained; zero observations in this finite window do not establish unused fields.'],source_sha256={'scripts/trace_city_auxiliary_fields.py':sha(__file__),'source/recovered/service_memory.py':sha(ROOT/'source/recovered/service_memory.py'),'source/recovered/mapped_memory.py':sha(ROOT/'source/recovered/mapped_memory.py')},artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in out.iterdir()if p.is_file()and p.name!='trace.json'})
 save('trace.json',result);print(json.dumps({k:result[k]for k in('cohort','original_instructions','main_boundaries','auxiliary_reads','auxiliary_writes','BD95_visits','boundary')},ensure_ascii=False))
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--snapshot',type=Path,default=ROOT/'analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame6758');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase18/cpu');p.add_argument('--updates',type=int,default=120);p.add_argument('--pre-nmi',type=int,default=0);p.add_argument('--actor',type=int,default=8);p.add_argument('--cohort',choices=('native_baseline','aux0','aux44','all'),default='all');a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 for cohort in(('native_baseline','aux0','aux44')if a.cohort=='all'else(a.cohort,)):run(rom,a.snapshot.resolve(),a.out.resolve()/cohort,cohort,a.updates,a.pre_nmi,a.actor)
