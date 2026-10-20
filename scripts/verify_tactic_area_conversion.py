#!/usr/bin/env python3
"""Full original-ROM body comparisons for independent area/conversion rules."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered.tactic_area_conversion import AreaConversionTactics,AreaConversionData,ROM_SHA256,SUPPORTED_IDS,ENTRY_POINTS,DECLARED_RAM_RANGES
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/area-conversion');args=p.parse_args()
 rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=AreaConversionData.from_rom(rom)
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
 counts=Counter();failures=[];rows=[];outcomes=Counter();visited=set();rng=random.Random(0x907)
 def fresh():
  b=Bus(rom,'alternating');b.ram[:]=ram;b.sram[:]=sram;b.banks=[6,12,13,31];b.bank_initialized=[True]*4;b.protect=0x4c
  b.ram[0xe1:0xe4]=bytes([0x26,0x2c,0x2d]);b.ram[0x1fe:0x200]=bytes([255,1]);return b
 def flat(b):
  m=bytearray(65536)
  for i in range(4):m[2048*i:2048*(i+1)]=b.ram
  m[0x6000:0x8000]=b.sram
  for i,bank in enumerate(b.banks):m[0x8000+i*8192:0xa000+i*8192]=rom[16+bank*8192:16+(bank+1)*8192]
  return m
 def execute(b,entry,registers=None):
  c=MPU(memory=b,pc=entry);c.sp=0xfd;c.p=32;b.cpu=c
  for k,v in(registers or{}).items():setattr(c,k,v)
  for step in range(250000):
   if step and c.pc==0x200:return c,step
   if c.disassemble[b.peek(c.pc)][0]=='???':raise RuntimeError(f'Original opcode ${c.pc:04X}')
   b.pc=c.pc;b.step_no=step;visited.add((b.origin(c.pc)[0],c.pc));c.step()
  raise RuntimeError(f'Original CPU budget at ${c.pc:04X}')
 def compare(group,b,entry,fn,registers=None,notes=None):
  m=flat(b);model=AreaConversionTactics(m,data)
  try:
   result=fn(model);c,n=execute(b,entry,registers)
   rd=[(a,m[a],b[a])for lo,hi in DECLARED_RAM_RANGES for a in range(lo,hi)if m[a]!=b[a]][:20]
   sd=[(0x6000+i,m[0x6000+i],b.sram[i])for i in range(8192)if m[0x6000+i]!=b.sram[i]][:20]
   good=not(rd or sd);counts[group]+=1
   if not good:failures.append({'group':group,'entry':entry,'ram':rd,'sram':sd,'notes':notes,'result':result})
   if group=='full_effect_body':outcomes[(notes['tactic'],bool(result['success']))]+=1
   if notes and notes.get('sample')or not good:rows.append({'group':group,'entry':entry,'native_instructions':n,'notes':notes,'result':result,'passed':good})
   return m,result
  except Exception as e:counts[group]+=1;failures.append({'group':group,'entry':entry,'notes':notes,'error':str(e)[:1400]});return m,None
 def setup(b,side,cx,cy,variant=0):
  for slot in range(20):
   b[0x600+slot]=b[0x614+slot]=b[0x628+slot]=b[0x664+slot]=255;b[0x6fa1+slot]=255
  actor=0;target=1;b[0x50a]=actor;b[0x509]=target;b[0x504]=side;b[0x507]=0x21;b[0x50f]=0;b[0x6f02]=variant%3
  actorx=min(30,cx+3);b[0x600]=actorx;b[0x614]=cy;b[0x628]=side;b[0x664]=109
  coords=[(cx,cy),(cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1),(cx+2,cy),(cx+2,cy+1),(cx+1,cy+1)]
  for slot,(x,y)in enumerate(coords,1):
   if not 0<=x<32 or not 0<=y<20:continue
   if y==15:y=16
   b[0x600+slot]=x;b[0x614+slot]=y;b[0x628+slot]=side^128;b[0x664+slot]=[8,191,51,167,131,108,166,121][slot-1]
  if variant&1:b[0x628+2]=side
  if variant&2:
   b[0x600+9]=b[0x600+2];b[0x614+9]=b[0x614+2];b[0x628+9]=side;b[0x664+9]=108
  if variant&4:
   for slot in [2,3,4,5]:
    if b[0x664+slot]!=255:b[0x664+slot]=b[0x664+1]
  if variant&8:b[0x664+1]=109
  for slot in range(20):
   ident=b[0x664+slot]
   if ident==255:continue
   a=0x63c0+12*ident;b[a]=100;b[a+1]=90;b[a+2]=10;b[a+3]=30;b[a+4]=80;b[a+11]=(variant%8)<<4|(variant&3)
   xp=[0,999,1000,49999,65535][variant%5];b[a+6]=xp&255;b[a+7]=xp>>8
   troops=[0,1,99,100,255,700,1000,1023][variant%8];b[a+8]=troops&255;b[a+9]=(troops>>8)|[0,4,128,252][variant%4]
  a=0x63c0+12*109;b[a+2]=99;b[a+4]=90;b[a+11]=0x70|(variant&3)
  for a in range(0x42c,0x435):b[a]=0
  b[0x544]=0;b[0x501]=(variant*17)&255;b[0x50]=next(i for i,v in enumerate(data.fixed_rng)if v<5)if variant&16 else(variant*13)&255
  return actor,target
 # Original map classes, not a supplied or patched terrain enum.
 b=fresh();model=AreaConversionTactics(flat(b),data);classes={}
 for y in range(20):
  if y==15:continue
  for x in range(31):classes.setdefault(model.terrain_at(x,y),(x,y))
 for tactic in SUPPORTED_IDS:
  for i in range(128):
   b=fresh();terrain=3 if tactic in [10,12]else[i%6 if i%6 in classes else 2][0];cx,cy=classes[terrain]
   setup(b,128 if i&1 else 0,cx,cy,i)
   if tactic==8:
    a=0x63c0+12*b[0x665];b[a+3]=[0,30,31,50,51,70,71,100][i%8]
    b[0x4d8]=1 if i&2 else 255;b[0x4dc]=1 if i&4 else 255;b[0x6fa2]=255 if i&8 else 0xA3
    for where in [0x51a,0x51c]:b[where]=[0,255,254,232][i%4];b[where+1]=[0,0,255,3][i%4]
    b[0x51e]=i&255;b[0x51f]=(255-i)&255
   if i%16==0:b[0x600]=min(30,cx+7)
   compare('full_effect_body',b,ENTRY_POINTS[tactic],lambda s,t=tactic:s.apply(t),notes={'tactic':tactic,'variant':i,'center':[cx,cy],'sample':i<4 or i==18})
 # Actor-level changes and alias targets repeatedly reuse cumulative loss.
 for tactic in [7,12,14]:
  for i in range(32):
   b=fresh();cx,cy=classes[3 if tactic==12 else 0];setup(b,0,cx,cy,i|16)
   a=0x63c0+12*109;xp=[990,1980,3490,4990,7490,9990,14990,65535][i%8];b[a+6]=xp&255;b[a+7]=xp>>8;b[a+11]=((i%7)<<4)|(i&15)
   # The caller's declared accumulator need not be zero for direct effect body.
   total=[0,1,255,65535][i%4];b[0x42c]=total&255;b[0x42d]=total>>8
   compare('repeated_loss_experience_and_alias',b,ENTRY_POINTS[tactic],lambda s,t=tactic:s.apply(t),notes={'tactic':tactic,'variant':i,'sample':i<4})
 # Full helper bodies are separated from the complete effect counts.
 for i in range(512):
  b=fresh();slot=i%20;ident=i%237;b[0x664+slot]=ident;b[0x628+slot]=(128 if i&1 else 0)|(i&127);b[0x504]=b[0x628+slot]^128
  a=0x63c0+12*ident;raw=[0,1,99,100,255,256,1000,1023,1024,65535][i%10];b[a+8]=raw&255;b[a+9]=raw>>8
  for where in [0x51a,0x51c]:total=[0,raw&1023,max(0,(raw&1023)-1),65535][(i//10)%4];b[where]=total&255;b[where+1]=total>>8
  b[0x51e]=i&255;b[0x51f]=(255-i)&255
  compare('C886_full_accounting_helper',b,0xc886,lambda s,q=slot:s.convert_accounting(q),registers={'y':slot})
 for i in range(128):
  b=fresh();cx,cy=classes[i%6 if i%6 in classes else 2];setup(b,128 if i&1 else 0,cx,cy,i)
  compare('B8A1_full_candidate_helper',b,0xb8a1,lambda s:s.connected_candidates(),notes={'variant':i,'sample':i<4})
 # Explicit highest-friendly coordinate collision versus ascending BFS enemy
 # lookup, plus the raw14/16 hole skip at both map side edges.
 for cx in [0,1,8,30]:
  for cy in [14,16]:
   b=fresh();setup(b,0,cx,cy,18);b[0x501]=0
   compare('cross_slot_order_and_row_skip',b,0xb2cd,lambda s:s.apply(7),notes={'tactic':7,'center':[cx,cy],'sample':True})
 # Fill the entire candidate capacity from an actual non-class5 connected
 # map region. Center is unconditional, so this helper's input may be friendly;
 # this is a helper contract case, not a naturally selected menu target.
 b=fresh();wm=AreaConversionTactics(flat(b),data);start=classes[3];cells=[start];cursor=0
 while len(cells)<20 and cursor<len(cells):
  x,y=cells[cursor];cursor+=1
  for nx,ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
   if ny==15:ny=16 if y==14 else 14
   if 0<=nx<31 and 0<=ny<20 and (nx,ny)not in cells and wm.terrain_at(nx,ny)!=5:cells.append((nx,ny))
   if len(cells)==20:break
 assert len(cells)==20
 for side in [0,128]:
  b=fresh();b[0x504]=side;b[0x509]=0
  for slot,(x,y)in enumerate(cells):b[0x600+slot]=x;b[0x614+slot]=y;b[0x628+slot]=side^128;b[0x664+slot]=slot
  m,result=compare('B8A1_twenty_slot_capacity',b,0xb8a1,lambda s:s.connected_candidates(),notes={'side':side,'sample':True})
  if result is None or len(result)!=20:failures.append({'group':'candidate_capacity','result':result})
 # Three genuine successive conversion effect bodies, alternating the side
 # and real caster. Only the caller's reset/RNG/selection inputs are supplied;
 # counts/totals/loyalty/cache/strategy carry over from the previous effect.
 for scenario in range(2):
  b=fresh();cx,cy=classes[0];setup(b,0,cx,cy,18);b[0x664+2]=51;b[0x600+2]=cx+1;b[0x614+2]=cy;b[0x628+2]=128
  for ident in [109,51]:aa=0x63c0+12*ident;b[aa+2]=99;b[aa+4]=90;b[aa+11]=0x70
  b[0x6fa2]=255 if scenario else 0xA4;b[0x4d8]=b[0x4dc]=1
  for tick in range(3):
   b[0x504]=128 if tick&1 else 0;b[0x50a]=2 if tick&1 else 0;b[0x509]=1;b[0x50]=next(i for i,v in enumerate(data.fixed_rng)if v<5)
   for address in range(0x42c,0x435):b[address]=0
   b[0x544]=0
   compare('continuous_conversion_both_sides',b,0xb31c,lambda s:s.apply(8),notes={'tactic':8,'scenario':scenario,'tick':tick,'sample':True})
 guards=0
 for tactic in [-1,0,1,2,3,4,5,6,9,11,13,15,16,255]:
  m=flat(fresh());before=bytes(m)
  try:AreaConversionTactics(m,data).apply(tactic);ok=False
  except ValueError:ok=True
  guards+=1
  if not ok or bytes(m)!=before:failures.append({'group':'unsupported_tactic_guard','tactic':tactic})
 evidence=json.loads((args.out/'evidence.json').read_text())
 for r in evidence['ranges']:raw=bytes.fromhex(r['raw_hex']);assert rom[r['file_start']:r['file_start']+len(raw)]==raw
 report={'status':'passed'if not failures else'failed','rom_sha256':ROM_SHA256,'case_count':sum(counts.values())+guards,'rom_cpu_case_count':sum(counts.values()),'source_guard_case_count':guards,'failed_count':len(failures),
  'complete_effect_cpu_case_count':counts['full_effect_body']+counts['repeated_loss_experience_and_alias']+counts['cross_slot_order_and_row_skip']+counts['continuous_conversion_both_sides'],'complete_helper_cpu_case_count':counts['C886_full_accounting_helper']+counts['B8A1_full_candidate_helper']+counts['B8A1_twenty_slot_capacity'],'prefix_cpu_case_count':0,'counts':dict(counts),
  'supported_ids':list(SUPPORTED_IDS),'effect_outcomes':{str(t):{'success':outcomes[(t,True)],'failure':outcomes[(t,False)]}for t in SUPPORTED_IDS},
  'all_SRAM_compared_bytes':8192,'declared_RAM_ranges':[list(x)for x in DECLARED_RAM_RANGES],'native_instruction_locations':len(visited),
  'source_sha256':sha(ROOT/'source/recovered/tactic_area_conversion.py'),'validator_sha256':sha(Path(__file__).resolve()),'evidence_sha256':sha(args.out/'evidence.json'),
  'dependency_source_sha256':{n:sha(ROOT/'source/recovered'/n)for n in ['battle.py','game_algorithms.py','tactical_decisions.py','officer_transfer.py']},
  'fixture_source':str(prefix.relative_to(ROOT)),'fixture_sha256':{s:sha(Path(str(prefix)+s))for s in ['-ram.bin','-sram.bin']},
  'fixture_inputs':'Synthetic CPU inputs from original coreRAM/SRAM: slots/coords/records/side/RNG/resultreset/counts/rosters unchanged unless declared. True original map resource suppliesclasses, no terrain or readiness injection.',
  'source_IR_or_original_CPU':False,'graphics_or_readiness_ack':False,'rows':rows,'failures':failures,
  'limitations':['Full effect bodies assume actual B02B reset and preceding UI/animation complete; no AP/graphics/frame claim.','AllSRAM+declaredRAM compared; CPU pointers/registers/stack/mapper outside semantic contract.','Conversion mutates battle counts/sign/cache/strategy and loyalty only, no immediate city membership/status/location update.','Helper and full-effect cases are separately counted; no prefix stand-in is reported as a complete effect.']}
 (args.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','case_count','rom_cpu_case_count','source_guard_case_count','failed_count','counts','effect_outcomes']},ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
