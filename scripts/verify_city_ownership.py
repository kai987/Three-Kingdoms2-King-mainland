#!/usr/bin/env python3
"""Actual unmodified ROM differential for bounded city ownership algorithms."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from verify_officer_transfer import context,record,city,TransferOracle
from source.recovered.city_ownership import *

def make_model(o,data):
 m=bytearray(65536);m[:2048]=o.bus.ram;m[0x6000:0x8000]=o.bus.sram
 return CityOwnership(m,data)
def compare(o,model,label,ram=()):
 got=bytes(o.bus.sram);want=bytes(model.memory[0x6000:0x8000])
 assert got==want,(label,'SRAM',[(hex(0x6000+i),got[i],want[i])for i in range(8192)if got[i]!=want[i]][:16])
 for a in ram:assert o.get(a)==model.memory[a],(label,hex(a),o.get(a),model.memory[a])
def verify(rom):
 data=OwnershipData.from_rom(rom);rng=random.Random(6019);counts=Counter();coverage=Counter();examples=[]
 def passed(name,o):counts[name]+=1;coverage.update(o.executed)
 for i in range(256):
  o=context(rom);owner=i;ruler=i%7;city(o,3,owner,[],resources=(65535,10000));o.set(0x38,3);o.set(0x6F03,ruler)
  logic=make_model(o,data);result=logic.commit_ai_capture(3,ruler,branch_zero=True)
  o.run(0xA8FC,stop=lambda pc:pc==0xA90D);compare(o,logic,('capture',i));passed('AI_capture_preserve_high5',o)
  if i<3:examples.append({'kind':'capture','fixture':i,'result':result})
 for i in range(256):
  o=context(rom);combat=i%30;ruler=i%7;neighbors=list(data.neighbors(combat));officer=80;record(o,officer,loyalty=i,status=0xEE,location=29)
  for j,target in enumerate(neighbors):
   owner=(ruler+1)%7 if i%4==0 else [ruler,7,(ruler+1)%7][(i+j)%3]
   n=[0,3,10,1,5][(i+j)%5];city(o,target,((i%32)<<3)|owner,list(range(30,30+n)),resources=(65535,10000))
  o.set(0x38,combat);o.set(0x40,ruler);o.set(0x41,officer);o.set(0x42,i&1);o.set(0x54,i)
  logic=make_model(o,data);result=logic.relocate_after_ai_battle(combat,officer,ruler,adjust_capture_loyalty=not bool(i&1))
  o.run(0xABA3);compare(o,logic,('relocate',i),[0x54]);passed('AI_battle_relocation_or_release',o)
  if i<8:examples.append({'kind':'relocation','fixture':i,'result':result})
 for i in range(384):
  o=context(rom);ruler=i%7;n=3+i%8;source=3;destination=source if i%17==0 else 4
  city(o,source,((i%32)<<3)|ruler,list(range(30,30+n)),resources=(rng.choice([0,9999,65535]),rng.choice([0,9999,65535])))
  if destination!=source:city(o,destination,((i%32)<<3)|7,[],resources=(rng.choice([0,9999,65535]),rng.choice([0,9999,65535])))
  for j in range(n):record(o,30+j,loyalty=[0,100,255,50][(i+j)%4],status=0xAE,location=29)
  gold,grain=rng.choice([0,100,9999,65535]),rng.choice([0,100,9999,65535]);o.set(0x3A,source);o.set(0x38,destination);o.set(0x37,n);o.set(0x6F03,ruler);o.load(0x3D,[gold&255,gold>>8]);o.load(0x3B,[grain&255,grain>>8])
  logic=make_model(o,data);result=logic.colonize_city(source,destination,ruler,gold=gold,grain=grain,allocation_base_count=n)
  o.run(0xB287);compare(o,logic,('colonize',i),[0x37]+list(range(0x6F73,0x6F83)));passed('colonize_finances_roster_owner',o)
  if i<3:examples.append({'kind':'colonize','fixture':i,'gold':gold,'grain':grain,'result':result})
 for i in range(256):
  o=context(rom);source=3;destination=source if i%17==0 else 4;n=i%11;destination_count=(i//11)%11
  city(o,source,((i%32)<<3)|i%7,list(range(30,30+n)),resources=(rng.choice([0,9999,65535]),rng.choice([0,9999,65535])))
  if source!=destination:city(o,destination,i%7,list(range(50,50+destination_count)),resources=(rng.choice([0,9999,65535]),rng.choice([0,9999,65535])))
  o.set(0x37,source);o.set(0x38,destination);logic=make_model(o,data);result=logic.withdraw_city(source,destination)
  o.run(0xB3B1,stop=lambda pc:pc==0xB42B,a=destination);compare(o,logic,('withdraw',i),[0x26]);passed('withdraw_finances_roster_neutralize',o)
  if i<3:examples.append({'kind':'withdraw','fixture':i,'result':result})
 for i in range(256):
  o=context(rom);source=3;destination=source if i%31==0 else 4;newruler=i%7;oldruler=(i+1)%7;n=1+i%8;officer=30+i%n;leader=20+newruler
  city(o,source,((i%32)<<3)|(newruler if source==destination else oldruler),list(range(30,30+n)),resources=(65535,10000))
  if source!=destination:city(o,destination,newruler,list(range(50,50+i%10)),resources=(65535,10000))
  record(o,officer,loyalty=i,virtue=70,status=0xAE,location=29);record(o,leader,virtue=i)
  o.set(0x38,destination);o.set(0x3F,source);o.set(0x3D,officer);o.set(0x6F03,newruler)
  logic=make_model(o,data);result=logic.transfer_persuaded_officer(source,destination,officer,newruler)
  o.run(0xBA8D,stop=lambda pc:pc==0xBAE2);compare(o,logic,('persuaded',i),[0x42]+list(range(0x6F73,0x6F83)));passed('persuaded_membership_and_empty_whole7',o)
  if i<3:examples.append({'kind':'persuaded','fixture':i,'result':result})
 for i in range(384):
  o=context(rom,27);city(o,3,i&255,[255,30]if i%2==0 else[30,255]);o.set(0x471,3);mode=[2,0,0x81][i%3]
  logic=make_model(o,data);result=logic.finish_empty_city_action(3,action_mode=mode)
  o.run(0xD16B,stop=lambda pc:pc==0xD183,a=mode);compare(o,logic,('mode2empty',i));passed('mode2_firstFF_whole7',o)
 for i in range(128):
  o=context(rom,8);combat=i%30;low=i%7;high=(i+1)%7
  city(o,combat,((i%16)<<4)|low,[20+high,20+low],resources=(0,0))
  for j,target in enumerate(data.neighbors(combat)):city(o,target,((i%16)<<4)|(j%7),[50,20+j%7])
  o.set(0x50E,combat);o.set(0x514,i&1);o.set(0x507,(high<<4)|low)
  logic=make_model(o,data);logic.finalize_battle_ownership();o.run(0xBBB8);compare(o,logic,('oldbattlefinalizer',i));passed('existing_battle_finalize_composition',o)
 for i in range(256):
  o=context(rom,12);slot=i%20;destination=3;owner=((i%32)<<3)|(7 if i%3 else i%7);n=i%11
  city(o,destination,owner,list(range(50,50+n)),resources=(65535,10000));o.set(0x509,slot);o.set(0x50B,destination);o.set(0x507,(((i+1)%7)<<4)|(i%7));o.set(0x504,128 if i&1 else 0)
  for base in (0x600,0x614,0x628,0x63C,0x650):o.set(base+slot,slot)
  o.set(0x664+slot,80);o.set(0x4D8,slot if i%2 else 19);o.set(0x4DC,slot if i%3 else 18)
  logic=make_model(o,data);result=logic.retreat_unit_to_city(slot,destination)
  o.run(0xBC2D);compare(o,logic,('retreat_unit',i),[b+slot for b in (0x600,0x614,0x628,0x63C,0x650,0x664)]+[0x4D8,0x4DC,0x52B,0x52C]);passed('retreat_unit_clear_caches_neutralF0',o)
  if i<3:examples.append({'kind':'retreat_unit','fixture':i,'result':result})
 guards=[];o=context(rom);logic=make_model(o,data)
 for label,fn in [('nonzero capture branch',lambda:logic.commit_ai_capture(3,0,branch_zero=False)),('invalid colonize count',lambda:logic.colonize_city(3,4,0,gold=0,grain=0,allocation_base_count=2)),('invalid city',lambda:logic.finish_empty_city_action(222,action_mode=2))]:
  try:fn()
  except ValueError:guards.append(label)
  else:raise AssertionError(label)
 return {'status':'passed','original_rom_sha256':hashlib.sha256(rom).hexdigest(),'case_count':sum(counts.values()),'counts':dict(counts),'source_only_guard_count':len(guards),'source_only_guards':guards,'failures':0,'unique_executed_instruction_locations':len(coverage),'coverage_banks':sorted({b for b,p,c in coverage}),
  'source_sha256':hashlib.sha256((ROOT/'source/recovered/city_ownership.py').read_bytes()).hexdigest(),'examples':examples,'contract':'All8192B SRAM peractualROM case; declared cursor54/buffers6F73/scan fields/APcost additionally. CPU stack/mapper/scratch are external. No originalROM code installed as sourcefallback.',
  'stops':{'A8FC':'A90D beforeD249/city-residence search + CA19 succession','ABA3':'RTS','B287':'RTS','B3B1':'B42B before D152 budget/unwind/nextcycle','BA8D':'BAE2 before former-ruler response','D16B':'D183 beforeUI/cursor tail','BBB8':'RTS existing pure source composition','BC2D':'RTS before caller; precedingBC2A C91E remains outside'},
  'limitations':['Strategic selection, diplomacy menus and result/UI setup are not completed by these transaction APIs.','Controlled valid city/ruler/record inputs; full colonization affordability selection external, explicit amount underflow tested at the bounded core.','Colonization/withdrawal/persuaded transaction aliases and roster-overcapacity traversal preserve original sequentialwrites; no complete gameplayUI permission claim.','Family/faction death cleanup remains a distinct source module; cityneutralization alone is not faction elimination.'],'command':'.venv-trace/bin/python scripts/verify_city_ownership.py'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'));p.add_argument('--out',type=Path,default=ROOT/'analysis/phase6/ownership/validation.json');a=p.parse_args();j=verify(a.rom.read_bytes());a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:j[k]for k in ['status','case_count','counts','source_only_guard_count']},ensure_ascii=False))
