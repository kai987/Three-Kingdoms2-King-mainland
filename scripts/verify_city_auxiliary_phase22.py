#!/usr/bin/env python3
"""Phase22 original-CPU contract checks, not recovered-source comparisons."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'analysis/phase22/fields-static'
SPEC=importlib.util.spec_from_file_location('phase22_fields_model',ROOT/'scripts/analyze_city_auxiliary_phase22.py')
model=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=model;SPEC.loader.exec_module(model)
B=importlib.util.spec_from_file_location('frozen_phase21_field_validator',ROOT/'scripts/verify_city_auxiliary_semantics.py')
busmod=importlib.util.module_from_spec(B);sys.modules[B.name]=busmod;B.loader.exec_module(busmod)
OriginalBus=busmod.OriginalBus
base=model.base

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def seed(m,c,pc=0x7FF0,sp=0xF0):
 c.sp=sp;m.ram[0x100+((sp+1)&255)]=(pc-1)&255;m.ram[0x100+((sp+2)&255)]=(pc-1)>>8
 return pc

def scalar_checks(rom,contracts):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for d in contracts:
  p=d['scalar_prefix_contract'];begin=p['entry'];stop=d['complete_after']['cpu']+len(bytes.fromhex(d['complete_after']['raw_hex']))
  observed=set()
  for raw in range(256):
   m=OriginalBus(rom,begin['physical_bank'],begin['cpu'],d['explicit_data_window_bank']or 0)
   c=MPU(memory=m,pc=begin['cpu']);c.a=raw;c.x=raw^0x55;c.y=raw^0xAA;c.p=0x20;c.sp=0xF0
   steps=0
   while c.pc!=stop:
    c.step();steps+=1;assert steps<=20,d
   pointer=d['pointer_base'];word=m[pointer]|m[(pointer+1)&255]<<8
   assert word in d['whole_pointer_values'];observed.add(word)
  assert observed==set(d['whole_pointer_values'])
  rows.append(dict(physical_bank=begin['physical_bank'],cpu=begin['cpu'],constructor_loads_cpu=d['loads_start']['cpu'],
   raw_input_A_cases=256,original_CPU_instructions_per_case=steps,stop_pc=stop,declared_explicit_data_window=d['explicit_data_window_bank'],
   comparison='original_scalar_index_and_word_constructor_prefix',all_output_words_exact=True,
   scope='EveryrawA at the scalar-prefix start. A declared8000data-window bank is supplied explicitly; this does not claim a mapper setter was executed in this short check. Full mapper/must-builder preconditions remain part of the static contract.'))
 return rows

def count_checks(rom):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for city in range(256):
  for prefix in range(11):
   m=OriginalBus(rom,11,0xD304);m.ram[:]=b'\xA5'*2048;m.sram[:]=b'\x35'*8192
   address=0x6000+32*city
   for y in range(17,27):m.sram[address-0x6000+y]=20+y
   if prefix<10:m.sram[address-0x6000+17+prefix]=255
   m.sram[address-0x6000+2:address-0x6000+6]=b'\xFF'*4
   c=MPU(memory=m,pc=0xD304);c.a=city;c.x=0x37;c.y=0x83;c.p=0x20;stop=seed(m,c)
   reads=[];steps=0;before=bytearray(m.sram)
   while c.pc!=stop:
    if c.pc==0xD30B:reads.append((m[0x20]|m[0x21]<<8)+c.y)
    c.step();steps+=1;assert steps<300
   assert c.a==c.x==prefix and c.y==17+prefix and c.sp==0xF2
   assert (m[0x20]|m[0x21]<<8)==address
   expected=list(range(address+17,address+17+min(prefix+1,10)))
   assert reads==expected
   before[address-0x6000+2:address-0x6000+6]=b'\x0F\x27\x0F\x27';assert m.sram==before
   rows.append(dict(raw_city_ID=city,prefix_count=prefix,actual_read_addresses=reads,
    returned_A=c.a,returned_X=c.x,returned_Y=c.y,stop_PC=stop,stop_SP=c.sp,
    comparison='actual_original_D304_caller_RTS_and_FF_count_contract',SRAM_resource_cap_only=True,
    original_instruction_count=steps))
 return rows

def guarded_paths(rom):
 from py65.devices.mpu6502 import MPU
 small=next(i for i in range(256)if rom[base.original(31,0xE8BA+i)]<10)
 rows=[]
 for entry,load,store in ((0xC5D2,0xC664,0xC66C),(0xC6CC,0xC778,0xC77F)):
  for city in range(30):
   for prefix in range(11):
    m=OriginalBus(rom,11,entry,data_bank=16)
    m.sram[0xF00]=100;m.sram[0xF02]=0;m.sram[0xF03]=0;m.sram[0xF07]=1
    m.ram[0x36]=city;m.ram[0x52]=m.ram[0x54]=small
    for officer in range(237):m.sram[0x3C0+12*officer+11]=2
    start=city*32;m.sram[start+17:start+27]=bytes(range(20,30))
    if prefix<10:m.sram[start+17+prefix]=255
    # Actual original data-table ID, no prepared tactic/result/acknowledgement.
    chosen=rom[base.original(17,0x8B1C+20*city)]if entry==0xC5D2 else 100
    m.sram[0x3C0+12*chosen+11]=1 if entry==0xC5D2 else 0
    m.sram[0x3C0+12*chosen+5]=city
    m.sram[0x3C0+12*chosen+3]=50;m.sram[0x3C0+12+4]=80
    c=MPU(memory=m,pc=entry);c.a=0xA5;c.x=0x55;c.y=0xAA;c.p=0x20
    if entry==0xC6CC:
     c.sp=0xFB;m.ram[0x1FC:0x200]=bytes((0xC3,0xC5,0xEF,0x7F))
     stop=0xC5C4 if prefix==10 else 0x7FF0;expected_sp=0xFD if prefix==10 else 0xFF
    else:stop=seed(m,c,sp=0xFD);expected_sp=0xFF
    observed=[];writes=[];guard_value=None;steps=0
    while c.pc!=stop:
     if c.pc in(0xC5F4,0xC6ED):guard_value=c.a
     if c.pc in(load,store):
      pointer=m[0x20]|m[0x21]<<8;address=(pointer+c.y)&65535
      assert pointer==0x6000+32*city and 17<=c.y<=26 and address not in base.AUX
      (observed if c.pc==load else writes).append(dict(Y=c.y,address=address))
     c.step();steps+=1;assert steps<50000,(entry,city,prefix,hex(c.pc))
    assert guard_value==prefix and c.sp==expected_sp
    if prefix==10:assert observed==writes==[]
    else:
     assert [r['Y']for r in observed]==list(range(17,18+prefix))
     assert [r['Y']for r in writes]==[17+prefix]
     assert m.sram[start+17+prefix]==chosen
    rows.append(dict(entry_cpu=entry,real_city_ID=city,prefix_count=prefix,chosen_original_ID=chosen,
     guard_return_A=guard_value,first_FF_reads=observed,append_writes=writes,
     original_instruction_count=steps,stop_PC=stop,stop_SP=c.sp,
     comparison='actual_original_guarded_recruitment_normal_RTS'if entry==0xC5D2 or prefix==10 else'actual_original_guarded_recruitment_nonlocal_RTS',
     preparation='Controlled numeric originalCPUfixture: realcity ID, rosterprefix0..10, status1 table-ID or status0 ID100/current-location, rawyear100 and valid RNG cursors. No completed effect/ready/ack/result is injected.',
     scope='Originalcontinuous execution, no helper callback or IRQ/NMI. This checks guarded firstFF addresses and capacity rejection, not natural campaign reachability or every game input.'))
 return rows

def suffix_counterexamples(rom):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for entry,write,stop in ((0xC663,0xC66C,0xC66E),(0xC777,0xC77F,0xC781)):
  for offset in (1,27,28,29,30,31,33):
   m=OriginalBus(rom,11,entry);m.sram[:256]=bytes((42,))*256;m.sram[offset]=255
   m.ram[0x20],m.ram[0x21],m.ram[0x24]=0,0x60,100
   c=MPU(memory=m,pc=entry);c.y=16;c.x=100;c.p=0x20;c.sp=0xF0
   writes=[];steps=0
   while c.pc!=stop:
    if c.pc==write:writes.append((m[0x20]|m[0x21]<<8)+c.y)
    c.step();steps+=1;assert steps<2000
   assert writes==[0x6000+offset]and m.sram[offset]==100
   rows.append(dict(naked_suffix_entry_cpu=entry,first_FF_raw_offset=offset,actual_write_address=writes[0],
    touches_target_auxiliary=writes[0]in base.AUX,bypasses_original_capacity_guard=True,
    comparison='original_naked_suffix_complete_append_prefix_not_guarded_function',stop_pc=stop,
    original_instruction_count=steps,scope='Explicit raw negative-domain fixture, not legal parent eligibility or naturally reached UI.'))
 return rows

def checks(engine,rom):
 guards=[]
 def check(name,value):
  assert value,name;guards.append(dict(name=name,passed=True))
 all_rows=read('all-indirect-accesses.json')['accesses'];canonical={(r['physical_bank'],r['cpu']):r for r in all_rows}
 check('all1526accesses unique and complete',len(canonical)==len(all_rows)==1526)
 prior={(r['physical_bank'],r['cpu']):r for r in base.read('analysis/phase21/fields-static/all-indirect-accesses.json')['accesses']}
 for row in all_rows:
  proof=row['address_contract']
  if proof:
   found=model.auxiliary_intersection(proof)
   assert found==proof['possible_auxiliary_effective_addresses']and len(found)==proof['auxiliary_address_intersection_count']
   assert row['whole_pointer_values']==sorted(model.projection_words(proof))and row['Y_values']==model.projection_Y(proof)
  if row['classification']==model.DISJOINT:assert proof is not None and not model.auxiliary_intersection(proof)
  origin=row.get('authoritative_contract_origin')
  if origin:
   assert sha(ROOT/origin['path'])==origin['sha256']and proof==prior[row['physical_bank'],row['cpu']]['address_contract']
  candidate=row['candidate_address_contract'];assert row['candidate_contract_is_authoritative']is False
  assert row['candidate_whole_pointer_values']==(sorted(model.projection_words(candidate))if candidate else None)
  assert row['candidate_Y_values']==(model.projection_Y(candidate)if candidate else None)
 check('every disjoint authority recomputed with actual relation; candidates never promoted',True)
 # The authority above is the logical data address, not every micro-cycle bus
 # address. In particular, an IndY page-cross load can read the previous page
 # without consuming its value. Keep that domain separate and check it against
 # the frozen original emulator implementation as well as a forward formula.
 dummy=read('logical-vs-dummy-bus-contracts.json')
 original_source=ROOT/dummy['original_emulator_source_path']
 lines=original_source.read_text().splitlines()
 assert sha(original_source)==dummy['original_emulator_source_sha256']
 assert '\n'.join(lines[dummy['first_source_line']-1:dummy['last_source_line']])+'\n'==dummy['original_source_excerpt']
 check('original IndY_R and IndY_W source excerpt and line range exact',True)
 assert dummy['access_count']==len(dummy['accesses'])==1526
 for row in dummy['accesses']:
  authority=canonical[row['physical_bank'],row['cpu']]
  proof=authority['address_contract']
  hits=model.dummy_auxiliary_intersection(proof,row['operation'])if proof else None
  assert row['raw_hex']==authority['raw_hex'] and row['rom_offset']==authority['rom_offset']
  assert row['operation']==authority['op'] and row['logical_classification']==authority['classification']
  assert row['dummy_auxiliary_bus_addresses']==hits and row['dummy_auxiliary_intersection_count']==(len(hits)if hits is not None else None)
  assert row['classification']==('possible_dummy_auxiliary_bus_read'if hits else'proved_no_dummy_auxiliary_bus_address_in_contract'if hits is not None else'unresolved_pointer_or_index_contract')
  assert row['instruction_result_uses_dummy_value']is False and row['logical_contract_changed']is False
 assert Counter(r['classification']for r in dummy['accesses'])==dummy['classification_counts']==read('analysis-summary.json')['dummy_bus_domain_classification_counts']
 check('all1526 logical authorities and separate dummy-address contracts agree',True)
 for bank,pc in((11,0xC73F),(13,0xD243)):
  logical=canonical[bank,pc];bus=next(r for r in dummy['accesses']if(r['physical_bank'],r['cpu'])==(bank,pc))
  assert logical['classification']==model.DISJOINT and 0x6301 in bus['dummy_auxiliary_bus_addresses']
  assert 0x63FC in model.projection_words(logical['address_contract']) and 5 in model.projection_Y(logical['address_contract'])
  assert (0x63FC+5)==0x6401 and ((0x63FC&0xFF00)|((0x63FC+5)&255))==0x6301
 check('officer63FC plusY5 effective6401 differs from dummy6301 for load and store',True)
 for low in range(256):
  for index in range(256):
   pointer=0x6300+low;uncorrected=(pointer&0xFF00)|((low+index)&255)
   contract=dict(whole_pointer_values=[pointer],Y_values=[index])
   for operation in('LDA','STA'):
    expected=[uncorrected]if uncorrected in base.AUX and(operation=='STA'or low+index>=256)else[]
    assert model.dummy_auxiliary_intersection(contract,operation)==expected
 check('131072 finite abstract dummy-formula cases match independent forward addressing; not CPU cases',True)
 relational=[r for r in all_rows if r['address_contract']and'address_cases'in r['address_contract']]
 check('four guarded relational authorities',len(relational)==4)
 for row in relational:
  p=row['address_contract'];assert len(p['address_cases'])==2
  assert sorted(model.projection_words(p))==p['whole_pointer_values']and model.projection_Y(p)==p['Y_values']
  flat=dict(whole_pointer_values=p['whole_pointer_values'],Y_values=p['Y_values'])
  assert len(model.old.old.actual_auxiliary_intersection(flat))==p['independent_projection_auxiliary_intersection_count']==150
  assert not model.auxiliary_intersection(p)
  assert p['required_execution_contract']['bare_suffix_entry_covered']is False
 check('wide independent projection150 is explicit while true guarded relation0',True)
 # A falsified case extension to a real-city tail must immediately intersect.
 corrupt=dict(relational[0]['address_contract']);corrupt['address_cases']=[dict(whole_pointer_values=[0x6000],Y_values=[28])]
 check('bad realcity tail relation is rejected as non-disjoint',model.auxiliary_intersection(corrupt)==[0x601C])
 for filename,n in(('access-contracts.json',589),('new-indirect-accesses.json',45),('phase21-remaining376-handling.json',376)):
  d=read(filename);assert d['access_count']==len(d['accesses'])==n
  assert Counter(r['classification']for r in d['accesses'])==d['classification_counts']
  assert all(r==canonical[r['physical_bank'],r['cpu']]for r in d['accesses'])
 check('old589 new45 prior376 ledgers match whole canonical rows',True)
 for contract in engine.scalar_prefixes:
  marker=(contract['complete_after']['physical_bank'],contract['complete_after']['cpu']);descriptor=engine.markers[marker]
  state=model.old.old.ContextState()
  for r in contract['instructions']:state=engine.transfer((r['physical_bank'],r['cpu']),state)
  assert state.pairs[contract['pointer_base']].addresses==frozenset(contract['whole_pointer_values'])
  state=model.old.old.ContextState()
  start=(contract['loads_start']['physical_bank'],contract['loads_start']['cpu'])
  key=start
  while True:
   state=engine.transfer(key,state)
   if key==marker:break
   key=engine.next_key(key)
  assert contract['pointer_base']not in state.pairs,'Middleentry must not acquire narrowed prefix capability'
 check('all scalar constructor full-entry vs skipped-prefix capability guards',True)
 check('raw input ASL is even0..254 not assumed legal ruler IDs',model.scalar_domain([dict(op='ASL',operand=0),dict(op='TAY',operand=0)])==list(range(0,256,2)))
 for contract in engine.guards:
  for helper in contract['helper_write_contracts']:
   for row in helper['original_instructions']:
    if row['op']=='JSR':assert(row['physical_bank'],row['cpu'],row['operand'])==(11,0xD123,0xD69D)
    if row['op']not in base.WRITES or row['mode']=='a':continue
    if row['mode']in('iy','ix'):assert row['physical_bank']==11 and row['cpu']in(0xD6AF,0xD6B4,0xD6C8,0xD6CD)
    else:
     addresses=model.old.direct_addresses(row);assert addresses is not None
     assert not any(0x6000<=a<0x63C0 or base.normalized_ram(a)==0x36 for a in addresses)
 check('all complete middle-helper write instructions respect disclosed SRAM/scratch footprint',True)
 check('guard dominance and complete middle store contracts regenerated',engine.guards==read('guarded-roster-contracts.json')['contracts'])
 check('scalar prefix contracts regenerated from original instructions',engine.scalar_prefixes==read('scalar-index-constructor-contracts.json')['contracts'])
 raw_data=read('raw345-executability-ledger.json');tables=read('declared-immutable-data-inventory.json')['contracts']
 expected=model.raw_window_ledger(engine,tables);assert raw_data['windows']==expected and raw_data['window_count']==len(expected)==345
 assert Counter(r['phase22_executability_category']for r in expected)==raw_data['categories']
 for row in expected:
  assert not row['promoted_to_executable_code']and not row['trusted_instruction_entry_at_start']
 check('all345raw hypotheses retain explicit operand/data/unresolved provenance; none promoted',True)
 check('guarded relation never changes official name unknowns',all(v is None for v in read('analysis-summary.json')['official_target_field_names'].values()))
 return guards

def raw_checks(rom):
 count=0
 def walk(value):
  nonlocal count
  if isinstance(value,dict):
   if'raw_hex'in value and'physical_bank'in value and'rom_offset'in value:
    pc=value.get('cpu',value.get('cpu_start',value.get('cpu_address')))
    if pc is not None:
     off=base.original(value['physical_bank'],pc);raw=bytes.fromhex(value['raw_hex'])
     assert value['rom_offset']==off and rom[off:off+len(raw)]==raw;count+=1
    elif'bank_offset'in value:
     off=16+value['physical_bank']*8192+value['bank_offset'];raw=bytes.fromhex(value['raw_hex'])
     assert off==value['rom_offset']and rom[off:off+len(raw)]==raw;count+=1
   for child in value.values():walk(child)
  elif isinstance(value,list):
   for child in value:walk(child)
 for p in sorted(OUT.glob('*.json')):
  if p.name not in('verification.json','evidence.json'):walk(json.loads(p.read_text()))
 return count

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom');args=parser.parse_args()
 rom=Path(args.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 s=read('analysis-summary.json');assert sha(ROOT/s['analyzer_path'])==s['analyzer_sha256']
 assert sha(ROOT/'analysis/phase21/verification.json')==model.OLD_AUDIT
 assert sha(ROOT/'build/三国志2超级版-逆向分析-v21.zip')==model.OLD_ZIP
 for path,digest in s['artifact_sha256'].items():
  assert not any(p.startswith('exploratory')for p in Path(path).parts)
  assert sha(ROOT/path)==digest,path
 engine=model.Analysis(rom)
 guards=checks(engine,rom)
 scalars=scalar_checks(rom,read('scalar-index-constructor-contracts.json')['contracts'])
 counts=count_checks(rom);paths=guarded_paths(rom);suffix=suffix_counterexamples(rom)
 raw_count=raw_checks(rom)
 assert len(scalars)==s['scalar_index_constructor_count']==44
 assert len(counts)==2816 and len(paths)==660 and len(suffix)==14
 sources={p:sha(ROOT/p)for p in('scripts/analyze_city_auxiliary_phase22.py','scripts/verify_city_auxiliary_phase22.py','scripts/verify_city_auxiliary_semantics.py','scripts/verify_city_auxiliary_contexts.py')}
 artifacts={str(p.relative_to(ROOT)):sha(p)for p in sorted(OUT.glob('*'))if p.is_file()and p.name not in('verification.json','evidence.json')}
 result=dict(schema='phase22-city-auxiliary-guarded-context-validation-v1',status='passed',failed_count=0,ROM_sha256=base.ROM_SHA256,
  source_CPU_cases=0,original_scalar_constructor_prefix_CPU_cases=44*256,original_count_prefix_caller_RTS_CPU_cases=len(counts),
  original_guarded_recruitment_caller_CPU_cases=len(paths),original_raw_suffix_prefix_counterexample_CPU_cases=len(suffix),
  original_contract_CPU_cases=44*256+len(counts)+len(paths)+len(suffix),
  scalar_constructor_checks=scalars,count_prefix_checks=counts,guarded_recruitment_checks=paths,raw_suffix_counterexamples=suffix,
  model_guard_check_count=len(guards),model_checks=guards,original_nested_byte_ranges_verified=raw_count,
  classifications=dict(all1526=s['all_indirect_classification_counts'],old589=s['classification_counts'],new45=s['new_indirect_classification_counts']),
  phase21_remaining_count=376,remaining_access_count=s['remaining_access_count'],newly_proved_disjoint_all_count=s['newly_proved_disjoint_all_count'],
  source_and_validator_sha256=sources,artifact_sha256=artifacts,
  scopes=['OriginalCPU contracts only; no recovered-source comparison, CPU callback, native frame or internal original-core trace.',
   'D304 check covers rawcity0..255 and prefix0..10 with exact returnedA/X/Y/SP/PC, actual roster-read sequence and completeSRAM cap-only check; not arbitrary input-word exhaustive.',
   'The660 continuous guarded calls cover30realcities×11prefixcounts×2entries, original random gates and genuine nested/nonlocal stack shapes; do not prove natural reachability.',
   'The14suffix cases deliberately bypass capacity guards; real tail/nextcity aliases remain outside guarded entry contracts.',
   'The11264scalar-prefix checks explicitly prepare known data-window mapping and execute original prefix bytes; no functionRTS or whole-scene completion claim.'])
 model.save('verification.json',result)
 model.save('evidence.json',dict(schema='phase22-city-auxiliary-guarded-context-evidence-v1',status='passed',ROM_sha256=base.ROM_SHA256,
  analyzer_path='scripts/analyze_city_auxiliary_phase22.py',analyzer_sha256=sha(ROOT/'scripts/analyze_city_auxiliary_phase22.py'),
  validator_path='scripts/verify_city_auxiliary_phase22.py',validator_sha256=sha(__file__),
  source_and_validator_sha256=sources,artifact_sha256=s['artifact_sha256']|artifacts|{'analysis/phase22/fields-static/verification.json':sha(OUT/'verification.json')},
  source_CPU_cases=0,original_contract_CPU_cases=result['original_contract_CPU_cases'],model_guard_check_count=len(guards),
  classifications=result['classifications'],phase21_remaining_count=376,remaining_access_count=s['remaining_access_count'],newly_proved_disjoint_all_count=s['newly_proved_disjoint_all_count'],
  guarded_pointer_index_relation=dict(access_count=4,independent_projection_auxiliary_intersection_count=150,actual_relation_auxiliary_intersection_count=0),
  raw_window_categories=s['raw_window_categories'],official_target_field_names=s['official_target_field_names'],limitations=s['limitations']))
 print(json.dumps({k:result[k]for k in('status','original_contract_CPU_cases','model_guard_check_count','remaining_access_count')},ensure_ascii=False))

if __name__=='__main__':main()
