#!/usr/bin/env python3
"""Compare named F8 helpers with original bytes, retaining real pending states.

This script's call frames and game-data preparation are explicit CPU fixtures.
They are not original Nestopia frames or naturally triggered F8 evidence.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.negotiation_services import NegotiationServices,UIRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from verify_domestic_secondary_services import fixture,clone,reg,REGS
OUT=ROOT/'analysis/phase20/services'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];visited=Counter()
 def compare(m,initial,tag,services=True):
  left,right=clone(m),clone(m);c=MPU(memory=left);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  owner=NegotiationServices(right,rom,SceneSharedServices(right,rom)if services else None)
  result=owner.run_entry(initial['pc'],registers=r)
  for n in range(1500000):
   if n and(c.pc,c.sp)==(r.pc,r.sp)and(result['status']=='returned'or reg(c)==reg(r)):break
   assert c.pc>=0x8000,(tag,c.pc)
   bank=left.banks[(c.pc-0x8000)//8192];visited[bank,c.pc]+=1;c.step()
  else:raise RuntimeError((tag,hex(c.pc),hex(r.pc)))
  assert bytes(left.ram)==bytes(right.ram),(tag,'RAM',[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y][:8])
  assert bytes(left.sram)==bytes(right.sram),(tag,'SRAM')
  assert reg(c)==reg(r),(tag,'regs',reg(c),reg(r))
  assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks,(tag,'IO/banks')
  assert left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,(tag,'N163')
  if result['status']=='waiting':
   before=(bytes(right.ram),bytes(right.sram),reg(r));again=owner.resume()
   assert again['status']=='waiting'and before==(bytes(right.ram),bytes(right.sram),reg(r))
  comparison='actual_fixture_caller_RTS'if result['status']=='returned'else'original_loop_wait'if result['status']=='waiting'else'strict_dependency_prefix'
  rows.append(dict(case=tag,entry=initial['pc'],input_registers=initial,final_registers=reg(r),comparison=comparison,
   source_status=result['status'],original_CPU_instructions=n,RAM_bytes=2048,SRAM_bytes=8192,
   request=right[0x6F8B],all_registers_IO_banks_N163_equal=True,source_original_CPU_callbacks=0,
   controller_mode='explicit_fixture',hardware_timing='explicit_software_bus',pending=repr(owner.pending),
   RAM_sha256=hashlib.sha256(right.ram).hexdigest(),SRAM_sha256=hashlib.sha256(right.sram).hexdigest()))
 def make(entry):return fixture(rom,entry,'alliance',0,0)
 for controller in(0,1,2,3,255):
  for cursor in(0,17,31,83,144,255):
   m,r=fixture(rom,0xB619,'alliance',cursor,controller);compare(m,r,f'complete-offer/ctl{controller}/cursor{cursor}')
 for mode in(0,1,2,255):
  for funds in(0,255,256,9999,65535):
   for entry in(0xB7A2,0xB7CE):
    m,r=make(entry);m[0x38]=1;m[0x39]=mode;m[0x3A]=218;m[0x3B]=0;m[0x42F]=218;m[0x430]=1
    # The fixture's current ruler4 leader remains in its actual initial city.
    leader=m[0x6F07+4*8]
    city=next(c for c in range(30)if m[0x6000+32*c]&7==4 and leader in m[0x6000+32*c+17:0x6000+32*c+27])
    b=0x6000+city*32+(4 if mode else 2);m[b]=funds&255;m[b+1]=funds>>8
    compare(m,r,f'resource/{entry:04X}/mode{mode}/funds{funds}')
 for raw in range(256):
  for pattern in(0x00,0x5C):
   m,r=make(0xB923);r['a']=raw;m[0x24]=7;m[0x25]=0x6F
   for k in range(4,8):m[0x6F07+k]=pattern
   compare(m,r,f'packed-relation/raw{raw}/pattern{pattern}')
 for ruler in range(7):
  for entry in(0xB837,0xB898,0xB90A,0xB955,0xD080):
   m,r=make(entry);m[0x6F03]=ruler;m[0x38]=(ruler+1)%7;r['a']=ruler
   m[0x40]=m[0x6F07+ruler*8]
   compare(m,r,f'natural-record-data/{entry:04X}/ruler{ruler}')
 for ids in((255,)*10,(77,255,27,7,117,194,255,255,255,255),tuple(range(10))):
  for entry in(0xB85F,0xD307):
   m,r=make(entry);m[0x36]=1;m[0x20]=32;m[0x21]=0x60;m[0x3D]=255;m[0x3E]=0;m[0x40]=157
   m[0x6031:0x603B]=bytes(ids)
   compare(m,r,f'prefix-and-envoys/{entry:04X}/{list(ids)}')
 m,r=make(0xB955);r['a']=4
 for city in range(30):
  if m[0x6000+city*32]&7==4:m[0x6000+city*32+17:0x6000+city*32+27]=bytes([255]*10)
 compare(m,r,'leader-city/no-matching-roster')
 m,r=make(0xB898);compare(m,r,'missing-bank-service-prefix',False)
 counts=Counter(x['comparison']for x in rows)
 files=list((ROOT/'source/recovered').glob('*.py'))+[Path(__file__),ROOT/'scripts/verify_domestic_secondary_services.py']
 receipt=dict(schema='phase20-named-negotiation-source-differential-v1',status='passed',ROM_sha256=ROM_SHA256,
  original_CPU_parent_cases=len(rows),counts=dict(counts),cases=rows,failed_count=0,
  source_original_CPU_callbacks=0,production_IR_interpretation=False,Native_internal_CPU_trace=False,
  source_sha256={str(p.relative_to(ROOT)):sha(p)for p in files},
  executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],
  limits=['Controlled CPU fixtures are not Native reachability evidence.','RTS, original waiting loops and strict missing-service prefixes are counted separately.','No reply, request, text-ready or artificial completion is supplied afterentry.'])
 (OUT/'validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:receipt[k]for k in('status','original_CPU_parent_cases','counts')}))
if __name__=='__main__':main()
