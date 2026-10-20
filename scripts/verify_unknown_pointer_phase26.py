#!/usr/bin/env python3
"""OriginalCPU deployment contracts, distinct from Source and Native cases."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import analyze_unknown_pointer_phase26 as model
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import CapturedServiceMemory
from verify_deployment_pointer_phase26 import fixture,clone,registers
OUT=model.OUT;base=model.base
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 e=model.Analysis(rom);proof=json.loads((OUT/'deployment-pointer-postconditions.json').read_text());assert proof==model.prove_constructors(e)
 rows=json.loads((OUT/'all-indirect-accesses.json').read_text())['accesses'];canonical={(r['physical_bank'],r['cpu']):r for r in rows};helpers=[];constructors=[];consumers=[];bare=[];checks=[]
 def check(name,value):assert value,name;checks.append(dict(name=name,passed=True))
 for entry in(0xB2AE,0xB312):
  allowed=set(e.formation_contracts[entry]['whole_pointer_values'])
  for city in range(256):
   for origin in(0,255):
    m,r=fixture(rom,entry,city=city,origin=origin);before=bytes(m.ram),bytes(m.sram);c=MPU(memory=m)
    for k,v in r.items():setattr(c,k,v)
    stop=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535;steps=0
    while c.pc!=stop:c.step();steps+=1;assert steps<3000
    pointer=m[0x20]|m[0x21]<<8;assert pointer in allowed and c.sp==(r['sp']+2)&255 and c.x==r['x']and c.y==4 and m.banks==[6,8,9,31]
    assert bytes(m.sram)==before[1];changed={i for i,(x,y)in enumerate(zip(before[0],m.ram))if x!=y};assert changed<={0x20,0x21,0x22,0x23,0x24,0x25,0xDE,0x1FA,0x1FB,0x1FC,0x1FD}
    assert all(event[0]=='write'and event[1]==0xE000 for event in m.combined_IO)
    helpers.append(dict(entry=entry,raw_city=city,origin=origin,final_pointer20=pointer,final_PC=c.pc,final_SP=c.sp,original_instructions=steps,comparison='complete_original_formation_caller_RTS',all2048_RAM_write_scope=True,all8192_SRAM_unchanged=True,final_four_banks=list(m.banks),ordered_logical_IO=m.combined_IO))
  # The actual low/high pointer prefix after bank6 selection. All rawcity
  # bytes and every possible modulo offset are retained; this is a prefix,
  # not an entire formation/consumer return or a reachable-menu claim.
  d=e.formation_contracts[entry];start,end=(0xB2E9,0xB300)if entry==0xB2AE else(0xB348,0xB35F)
  for city in range(256):
   outputs=[];instructions=[]
   for offset in d['offset_bytes']:
    m=CapturedServiceMemory(rom,banks=(6,8,9,31));m[0x50E]=city;m[0x20]=offset;c=MPU(memory=m,pc=start);c.sp=0xF7;c.p=32;steps=0
    while c.pc!=end:c.step();steps+=1;assert steps<30
    index=(2*city)&255;table=d['table'];baseword=model.byte(rom,6,table+index)|model.byte(rom,6,table+index+1)<<8;expected=(baseword+offset)&65535
    actual=m[0x20]|m[0x21]<<8;assert actual==expected and actual in allowed and c.sp==0xF7 and not m.io_reads and not m.io_writes
    outputs.append(actual);instructions.append(steps)
   constructors.append(dict(entry=start,end_exclusive=end,raw_city=city,offset_bytes=d['offset_bytes'],output_whole_pointer_words=outputs,case_count=len(outputs),instructions_per_case=sorted(set(instructions)),comparison='complete_original_low_high_constructor_prefix'))
 # All30cities ×bothsides ×all10 noncommander counts use complete original
 # B1B0 callers; profile families vary by city, with existing named behavior.
 for city in range(30):
  for side in(0,10):
   for count in range(10):
    m,r=fixture(rom,0xB1B0,city=city,origin=city,side=side,count=count,ruler=city%7);c=MPU(memory=m)
    for k,v in r.items():setattr(c,k,v)
    stop=0xB16E if side==0 else 0xB198;observed=[];steps=0
    while c.pc!=stop:
     if(8,c.pc)in model.TARGETS:
      pointer=m[0x20]|m[0x21]<<8;address=(pointer+c.y)&65535;contract=canonical[8,c.pc]['address_contract']
      assert pointer in contract['whole_pointer_values']and c.y in contract['Y_values']and address not in base.AUX and 0x8000<=address<0xA000 and m.banks[0]==6
      page_cross=(pointer&255)+c.y>255;candidate=(pointer&0xFF00)|((pointer+c.y)&255)
      observed.append(dict(cpu=c.pc,pointer20=pointer,Y=c.y,logical_address=address,physical_bank=6,value=m[address],candidate_not_actual_dummy_address=candidate,page_cross_dummy_read_required=page_cross,required_dummy_address=candidate if page_cross else None,dummy_basis='Deduced conditional official IndY_R rule; py65 does not issue dummy reads'))
     c.step();steps+=1;assert steps<10000
    assert c.sp==(r['sp']+2)&255 and len(observed)==2+2*count
    consumers.append(dict(city=city,side=side,count=count,ruler=city%7,observed_accesses=observed,original_instructions=steps,final_PC=c.pc,final_SP=c.sp,comparison='complete_original_existing_B1B0_caller_RTS'))
 # Bare accesses can read the very city auxiliary fields the full producer
 # contract excludes. These are deliberate counterexamples, not Native paths.
 for pointer in(0x6001,0x601C,0x601F):
  m=CapturedServiceMemory(rom,banks=(6,8,9,31));m[0x20]=pointer&255;m[0x21]=pointer>>8;m[pointer]=73;c=MPU(memory=m,pc=0xB272);c.y=0;c.p=32;c.step();assert c.a==73 and c.pc==0xB274
  bare.append(dict(pointer=pointer,Y=0,logical_address=pointer,original_instructions=1,final_PC=c.pc,comparison='explicit_bare_access_counterexample_prefix',covered_by_complete_formation_contract=False))
 # Address-only outside-hardware-domain evidence. Never execute an unknown
 # PPU-port read merely to add a supposed completed CPU case.
 second=e.formation_contracts[0xB312];io_examples=[]
 for pointer in second['whole_pointer_values']:
  for y in range(256):
   address=(pointer+y)&65535
   if 0x2000<=address<0x6000:
    io_examples.append(dict(pointer=pointer,Y=y,logical_address=address,original_instructions_executed=0,scope='Address-only model boundary; absent explicit hardware input this read is not executed or counted as a CPU case.'))
 check('second-side conservative raw domain keeps potential2000..200E hardware reads',{r['logical_address']for r in io_examples}==set(range(0x2000,0x200F)))
 check('all256 rawcities and all modulo offset bytes verified by full lowhigh prefix',len(constructors)==512 and sum(r['case_count']for r in constructors)==34816)
 check('1024 complete raw formation callers verify helper pointer/postreturn/write scope',len(helpers)==1024)
 check('all600 complete typed B1B0 callers cover allfour real coordinate reads',{r['cpu']for x in consumers for r in x['observed_accesses']}=={pc for b,pc in model.TARGETS}and len(consumers)==600)
 check('bare cityaux reads do not receive the complete constructor postcondition',len(bare)==3 and all(r['logical_address']in base.AUX for r in bare))
 prior=json.loads((ROOT/'analysis/phase25/fields-static/all-indirect-accesses.json').read_text())['accesses'];oldcanonical={(r['physical_bank'],r['cpu']):r for r in prior}
 for key,row in canonical.items():
  p=row['address_contract']
  if p:assert model.old.old.old.old.auxiliary_intersection(p)==p['possible_auxiliary_effective_addresses']
  if key not in model.TARGETS:assert row['classification']==oldcanonical[key]['classification']and p==oldcanonical[key]['address_contract']
 check('all1526 intersections recomputed and only G107four selected classifications change',{k for k,r in canonical.items()if r['newly_proved_disjoint']}==set(model.TARGETS))
 for key in model.TARGETS:e.emit(key,base.State())
 e.run_queue()
 check('no fullpair means a bare selected entry retains no manufactured pointer',all(e.contract(key)is None for key in model.TARGETS))
 state=base.State();state.pairs[0x20]=base.Pair(frozenset((0x6001,)))
 for target in(0xB2AE,0xB312):
  output=e.apply_call(state,(8,target),(8,0xB25D if target==0xB2AE else 0xB263));assert output.pairs[0x20].addresses==frozenset(e.formation_contracts[target]['whole_pointer_values'])and output.numbers[2]==frozenset((4,))
 check('normal formation replaces an old citypointer rather than preserving its prior type',True)
 check('allraw data windows and code slots separated from legal city meaning',all(f['physical_data_bank_at_return']==6 for f in proof['formations'])and proof['formations'][1]['all_raw_domain_excludes_ports']is False)
 check('34byte offset exact raw arithmetic retained',e.formation_contracts[0xB312]['byte_stride']==34 and e.formation_contracts[0xB312]['offset_bytes']==list(range(0,256,2)))
 check('prior named B1B0 and generated formation bodies not labeled semantic first recovery',proof['credit']['new_semantic_first_recovery']is False)
 check('official auxiliary field names remain unknown',all(v is None for v in json.loads((OUT/'analysis-summary.json').read_text())['official_target_field_names'].values()))
 raw_count=0
 def walk(x):
  nonlocal raw_count
  if isinstance(x,dict):
   pc=x.get('cpu',x.get('cpu_start',x.get('cpu_address')))
   if pc is not None and all(k in x for k in('physical_bank','rom_offset','raw_hex')):
    raw=bytes.fromhex(x['raw_hex']);off=base.original(x['physical_bank'],pc);assert off==x['rom_offset']and rom[off:off+len(raw)]==raw;raw_count+=1
   for y in x.values():walk(y)
  elif isinstance(x,list):
   for y in x:walk(y)
 for p in OUT.glob('*.json'):
  if p.name not in('evidence.json','verification.json'):walk(json.loads(p.read_text()))
 check('all nested original instruction bytes and locations verified',raw_count>0)
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for module in tuple(sys.modules.values()):
  p=Path(getattr(module,'__file__','')or'/nonexistent')
  if p.is_file()and p.is_relative_to(ROOT/'scripts'):pins[str(p.relative_to(ROOT))]=sha(p)
 pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__);artifacts={str(p.relative_to(ROOT)):sha(p)for p in OUT.glob('*.json')if p.name not in('verification.json','evidence.json')};summary=json.loads((OUT/'analysis-summary.json').read_text());prefixes=sum(r['case_count']for r in constructors)
 result=dict(schema='phase26-original-deployment-pointer-contract-validation-v1',status='passed',failed_count=0,ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,original_contract_CPU_cases=len(helpers)+prefixes+len(consumers)+len(bare),actual_caller_RTS_CPU_cases=len(helpers)+len(consumers),constructor_prefix_CPU_cases=prefixes,bare_access_counterexample_prefix_CPU_cases=len(bare),formation_helper_checks=helpers,constructor_prefix_check_groups=constructors,B1B0_caller_checks=consumers,bare_counterexamples=bare,raw_IO_address_only_examples=io_examples,raw_IO_address_only_examples_added_CPU_cases=0,model_guard_check_count=len(checks),model_checks=checks,original_nested_byte_ranges_verified=raw_count,source_and_validator_sha256=pins,artifact_sha256=artifacts,remaining_access_count=summary['remaining_access_count'],all_indirect_classification_counts=summary['all_indirect_classification_counts'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],limits=proof['limits']+['Source cases0; originalCPU ordinary callee and controlled prefix contracts are not Native frames.','No additional IRQ/NMI or ack/ready/RNG is supplied. IO-address-only cases execute zero instructions and are not counted as CPU cases.','py65 is not a bus-cycle emulator; extra IndY read metadata is conditional official-core deduction, never an observed dummy event.'])
 model.save('verification.json',result);model.save('evidence.json',dict(schema='phase26-G107-static-and-CPU-contract-evidence-v1',status='passed',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,original_contract_CPU_cases=result['original_contract_CPU_cases'],actual_caller_RTS_CPU_cases=result['actual_caller_RTS_CPU_cases'],constructor_prefix_CPU_cases=prefixes,bare_access_counterexample_prefix_CPU_cases=len(bare),model_guard_check_count=len(checks),source_and_validator_sha256=pins,artifact_sha256=artifacts|{'analysis/phase26/fields-static/verification.json':sha(OUT/'verification.json')},remaining_access_count=summary['remaining_access_count'],all_indirect_classification_counts=summary['all_indirect_classification_counts'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],official_target_field_names=summary['official_target_field_names'],limits=result['limits']))
 print(json.dumps({k:result[k]for k in('status','original_contract_CPU_cases','actual_caller_RTS_CPU_cases','constructor_prefix_CPU_cases','model_guard_check_count','remaining_access_count')}))
if __name__=='__main__':main()
