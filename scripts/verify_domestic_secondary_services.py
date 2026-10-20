#!/usr/bin/env python3
"""Original6502 differential of named secondary decisions and real wait points.

Only this validator runs original bytes. CPUnumeric fixtures, original caller
provenance and true asynchronous consumer sequences are separately labelled.
Source has no original CPU callbacks and never writes a reply on behalf of UI.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.domestic_secondary_services import DomesticSecondaryServices,SecondaryRequestWait,UIRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.battle_nmi_services import ServiceWait
from source.recovered.service_memory import ServiceMemory
from verify_city_auxiliary_services import base_memory,controlled,REGS,sha
from source.recovered.nestopia_context import CapturedServiceMemory
OUT=ROOT/'analysis/phase19/services'

def clone(m):
 # Newphase19 exact N163127->0 bus; never change the frozen phase18 helper.
 b=CapturedServiceMemory(m.rom,bytes(m.ram),bytes(m.sram),tuple(m.banks),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 b.n163_ram[:]=m.n163_ram;b.n163_address=m.n163_address;b.n163_autoincrement=m.n163_autoincrement
 return b
def reg(c):return{k:getattr(c,k)for k in REGS}
def fixture(rom,entry,kind='base',cursor=0,controller=3,loyalty=60,level=0,difficulty=1):
 m=base_memory(rom);m[0xE1:0xE4]=bytes((48,42,43));m[0x1FE:0x200]=bytes((0x87,0xE1));m[0x6F02]=difficulty;m[0x6F5D]=2;m[0x6F5B]=1;m[0x6F8B]=0
 m[0x52]=cursor;m[0x54]=cursor;m[0x55]=cursor
 if kind=='alliance':
  m[0x6F03]=4;m[0xEE]=39;m[0xEF]=0x6F;m[0x6000]=1;m[0x6F0A+8]=controller
  for off in range(4,8):m[0x6F07+4*8+off]=0
  for off in(2,4):m[0x6000+2*32+off]=15;m[0x6000+2*32+off+1]=39
 elif kind in('recruit','loyalty'):
  m[0x6F03]=1;m[0xEE]=15;m[0xEF]=0x6F
  # Exact foreign controller and target officers are controlledcampaign data;
  # the body still selects, samples and mutates through its real instructions.
  m[0x6F0A+2*8]=controller
  own=3;foreign=11
  for city in range(30):
   for j in range(10):m[0x6000+city*32+17+j]=255
  for j,id in enumerate((8,117,9)):
   m[0x6000+own*32+17+j]=id;m[0x63C0+id*12+2]=99;m[0x63C0+id*12+11]=(level<<4)|2
  foreign_ids=(131,5,12,30,44,69)if kind=='loyalty'else(5,)
  for j,id in enumerate(foreign_ids):
   b=0x63C0+id*12;m[0x6000+foreign*32+17+j]=id;m[b+3]=loyalty;m[b+2]=0;m[b+4]=20;m[b+11]=2
 else:m[0x6F03]=1;m[0xEE]=15;m[0xEF]=0x6F
 return m,dict(a=17,x=23,y=31,p=32,sp=253,pc=entry)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 rows=[];failures=[];guards=[];visited=Counter();requests=Counter()
 def compare(m,initial,tag,domain='controlled_CPU_fixture',services=True):
  left=clone(m);right=clone(m);c=MPU(memory=left);r=UIRegisters(**initial)
  for k,v in initial.items():setattr(c,k,v)
  owner=DomesticSecondaryServices(right,rom,SceneSharedServices(right,rom)if services else None);before=bytes(m.sram)
  try:
   result=owner.run_entry(initial['pc'],registers=r)
   for n in range(1500000):
    match=(c.pc,c.sp)==(r.pc,r.sp)
    if result['status']=='waiting':match=match and all(getattr(c,k)==getattr(r,k)for k in('a','x','y','p'))
    if n and match:break
    bank=left.banks[(c.pc-0x8000)//8192]if c.pc>=0x8000 else None
    if bank is not None:visited[bank,c.pc]+=1
    c.step()
   else:raise RuntimeError(f'Originalbudget{c.pc:04X}; source{r.pc:04X}/SP{r.sp:02X}')
   rd=[(i,left.ram[i],right.ram[i])for i in range(2048)if left.ram[i]!=right.ram[i]];sd=[(0x6000+i,left.sram[i],right.sram[i])for i in range(8192)if left.sram[i]!=right.sram[i]];rg=[(k,getattr(c,k),getattr(r,k))for k in REGS if getattr(c,k)!=getattr(r,k)]
   assert not(rd or sd or rg),dict(RAM=rd[:8],SRAM=sd[:8],registers=rg)
   assert left.banks==right.banks and left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.n163_ram==right.n163_ram and left.n163_address==right.n163_address and left.n163_autoincrement==right.n163_autoincrement,dict(banks=(left.banks,right.banks),ports=(left.io_writes,right.io_writes))
   if result['status']=='waiting':
    old=(bytes(right.ram),bytes(right.sram),vars(r).copy());again=owner.resume();assert again['status']=='waiting'and old==(bytes(right.ram),bytes(right.sram),vars(r).copy())
   comparison='actual_caller_RTS'if result['status']=='returned'else'original_loop_wait'if result['status']=='waiting'else'strict_missing_dependency_prefix'
   requests[right[0x6F8B]]+=1
   offer=None
   if right[0x6F8B]==248:
    offer=dict(quote_full_word=right[0x42F]|right[0x430]<<8,commit_word=right[0x3A]|right[0x3B]<<8,mode=right[0x39],zero_byte0431=right[0x431])
   if tag.startswith('alliance/24targetcities/'):
    if tag.endswith('funds9999'):
     assert offer is not None and offer['quote_full_word']in(316,474)and offer['commit_word']==offer['quote_full_word']%256 and offer['zero_byte0431']==0,offer
    else:assert result['status']=='returned'and right[0x6F8B]==255
   row=dict(tag=tag,domain=domain,entry=initial['pc'],input_registers=initial,final_registers=vars(r).copy(),source_status=result['status'],alliance_offer_if_waiting=offer,comparison=comparison,original_instructions=n,all_RAM_byte_count=2048,all_SRAM_byte_count=8192,pure_source_CPU_callbacks=0,request=right[0x6F8B],pending=None if owner.pending is None else dict(category=getattr(owner.pending,'category',None),pc=getattr(owner.pending,'pc',None),address=getattr(owner.pending,'address',None),value=getattr(owner.pending,'value',None),condition=getattr(owner.pending,'condition',None)),ordered_IO_writes=right.io_writes,ordered_IO_reads=right.io_reads,banks=list(right.banks),changed_SRAM=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(before,right.sram))if x!=y],events=result['events'])
   rows.append(row);return owner,c,row
  except Exception as e:
   failures.append(dict(tag=tag,error=str(e),source_PC=r.pc));print(json.dumps(failures[-1]),flush=True)
 for entry in(0xB5FC,0xB619,0xB98B,0xBBB2):
  for cursor in((0,17,83)if a.quick else range(0,256,7)):
   m,r=fixture(rom,entry,cursor=cursor);compare(m,r,f'baseline{entry:04X}/cursor{cursor}','unchanged_campaign_data_with_CPU_caller')
 for ctl in(0,1,2,3,255):
  for cur in((0,83)if a.quick else(0,7,31,83,144,255)):
   m,r=fixture(rom,0xB619,'alliance',cur,ctl);compare(m,r,f'alliance/ctl{ctl}/cur{cur}')
 for entry,kind in((0xB98B,'recruit'),(0xBBB2,'loyalty')):
  for ctl in(0,3):
   for loyalty in((60,)if a.quick else(0,30,31,49,50,51,69,70,89,90,100)):
    for cur in((0,83)if a.quick else(0,17,83)):
     m,r=fixture(rom,entry,kind,cur,ctl,loyalty);compare(m,r,f'{kind}/ctl{ctl}/loyal{loyalty}/cur{cur}')
 # Pin both remaining valid difficulty rows of the two probability tables.
 for entry,kind in((0xB98B,'recruit'),(0xBBB2,'loyalty')):
  for difficulty in(0,2):
   m,r=fixture(rom,entry,kind,17,0,60,difficulty=difficulty)
   compare(m,r,f'{kind}/difficulty{difficulty}','controlled_valid_difficulty_rows')
 # Exact path fixtures for the still-unexecuted B49C redistribution branches.
 for frontier in(False,True):
  m,r=fixture(rom,0xB49C);m[0x55]=31;m[0x6F5D]=2
  if not frontier:
   for city in(2,11,12):m[0x6000+32*city]=7
  for city,ids in((1,(157,77,27,7,117,194)),(3,(8,)),(4,(167,))):
   for j in range(10):m[0x6000+32*city+17+j]=ids[j]if j<len(ids)else 255
  compare(m,r,f'assignment-redistribution/frontier{frontier}','controlled_valid_roster_path')
 # Full owned destinations reject a foreign recruit before changing its roster.
 m,r=fixture(rom,0xB98B,'recruit',17,0,0)
 for city in range(30):
  if m[0x6000+32*city]&7==1:
   for j in range(10):m[0x6000+32*city+17+j]=20+10*(city%3)+j
 compare(m,r,'recruit/full-owned-destinations','controlled_valid_capacity_boundary')
 # Affordability fails before any request; quote checks the fullword.
 for cur in(0,31):
  m,r=fixture(rom,0xB619,'alliance',cur,0)
  for off in(2,3,4,5):m[0x6040+off]=0
  compare(m,r,f'alliance/no-resource/cur{cur}','controlled_resource_boundary')
 # Target IQ above the best domestic IQ exercises the valid probability clamp.
 m,r=fixture(rom,0xBBB2,'loyalty',0,0,60)
 for id in(8,117,9):m[0x63C0+12*id+2]=0
 for id in(131,5,12,30,44,69):m[0x63C0+12*id+2]=99
 compare(m,r,'loyalty/ownIQ0-targetIQ99','controlled_valid_IQ_boundary')
 # Legal-sized largefaction quotation crosses255. Eligibility uses the
 # fullquote, whereas committed3A/3B takes its lowbyte and zero0431.
 for cur in(0,31):
  for funds in(255,9999):
   m,r=fixture(rom,0xB619,'alliance',cur,0)
   for city in range(30):m[0x6000+32*city]=1
   for city,ruler in((2,4),(8,0),(11,2),(15,3),(25,5),(6,6)):m[0x6000+32*city]=ruler
   for off in(2,4):m[0x6040+off]=funds&255;m[0x6040+off+1]=funds>>8
   compare(m,r,f'alliance/24targetcities/cur{cur}/funds{funds}','controlled_valid_word_quote_boundary')
 # Real savedNative REG/MAP/N163 contexts are continued only by the oracle
 # to actual B5FC/branch entries. These three different callable boundaries
 # are comparisons; their prefix steps are not extra source cases.
 caller_inputs=[]
 for context in sorted((ROOT/'analysis/phase19/cpu/actual-callers').glob('entry-*/context.json')):
  meta=json.loads(context.read_text());folder=context.parent
  m=ServiceMemory(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),tuple(meta['physical_banks']),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
  m.n163_ram[:]=(folder/'input-n163.bin').read_bytes();m.n163_address=meta['N163_address'];m.n163_autoincrement=meta['N163_autoincrement']
  compare(m,meta['registers'],f'actual-saved-Native-caller/{folder.name}','actual_saved_Native_context_original_CPU_callee')
  caller_inputs.extend(folder.glob('*'))
 # The formermissingE8AA fixture now runs with the genuine readable owner.
 m,r=controlled(rom);r['pc']=0xB49C;compare(m,r,'phase18-missingE8AA-now-provided')
 for entry,req in((0xB78B,248),(0xBB40,250),(0xBD36,249)):
  m,r=fixture(rom,entry);m[0x6F8B]=req;compare(m,r,f'unchanged-wait/{entry:04X}','explicit_wait_entry_fixture')
 for entry in(0xB5FC,0xB619):
  m,r=fixture(rom,entry,'alliance');compare(m,r,f'missing-fixed/{entry:04X}','strict_missing_service_fixture',False)
 for name,fn in[
  ('actualregs',lambda:DomesticSecondaryServices(base_memory(rom),rom).run_entry()),
  ('wrongpair',lambda:DomesticSecondaryServices(ServiceMemory(rom,banks=(16,12,13,31)),rom).run_entry(registers=UIRegisters())),
  ('wrongentry',lambda:DomesticSecondaryServices(base_memory(rom),rom).run_entry(0xB600,registers=UIRegisters())),
  ('Dflag',lambda:DomesticSecondaryServices(base_memory(rom),rom).run_entry(registers=UIRegisters(p=40))),
 ]:
  try:fn();raise AssertionError('guarddidnotreject')
  except ValueError:guards.append(dict(name=name,status='passed'))
 for status in(None,'waiting','error','blocked','dependency'):
  m,r=fixture(rom,0xB5FC)
  def unresolved(call):
   call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
   return None if status is None else dict(status=status)
  owner=DomesticSecondaryServices(m,rom,unresolved);out=owner.run_entry(0xB5FC,registers=UIRegisters(**r))
  assert out['status']=='dependency'and owner.pending is not None
  guards.append(dict(name=f'explicit-service-return-required/{status}',status='passed'))
 counts=Counter(x['comparison']for x in rows)
 pins={str(p.relative_to(ROOT)):sha(p)for p in ROOT.glob('source/recovered/*.py')};pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__);pins.update({str(p.relative_to(ROOT)):sha(p)for p in caller_inputs})
 receipt=dict(schema='phase19-domestic-secondary-actual-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=a.quick,rom_cpu_case_count=len(rows),source_guard_case_count=len(guards),case_count=len(rows)+len(guards),failed_count=len(failures),actual_caller_RTS_count=counts['actual_caller_RTS'],original_loop_wait_count=counts['original_loop_wait'],strict_prefix_count=counts['strict_missing_dependency_prefix'],production_original_CPU_callbacks=0,production_IR_interpretation=False,source_original_CPU_callbacks=0,counts=dict(counts),request_values={str(k):v for k,v in requests.items()},cases=rows,failures=failures,guards=guards,source_sha256=pins,executed_instruction_positions=[dict(physical_bank=b,cpu_address=p,rom_offset=16+b*8192+(p&8191),execution_count=n)for(b,p),n in sorted(visited.items())],scope=dict(RAM='all2048 includingstack',SRAM='all8192',registers='A X Y P SP PC',ports='ordered writes/reads',mapper='all4banks',N163='all128bytes/address/autoincrement, official127to0wrap'),Native_internal_CPU_trace=False,limits=['Controlledcaller RTS frames and campaignnumeric preparations are disclosed CPUfixtures, not Native reachability proof.','Waiting cases retain the actual generator; neither source nor validator supplies a fabricatedreply.','Actual asynchronous UI/NMI consumer sequences will be separately labelled and counted as parentcases.'])
 (OUT/'validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:receipt[k]for k in('status','rom_cpu_case_count','actual_caller_RTS_count','original_loop_wait_count','strict_prefix_count','source_guard_case_count','failed_count')}));return 0 if not failures else 1
if __name__=='__main__':sys.exit(main())
