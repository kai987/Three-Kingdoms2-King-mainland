#!/usr/bin/env python3
"""Phase23 model guards and actual original-CPU address-contract checks.

No recovered-source comparison or original-helper callback is performed. Full
original caller returns and two-instruction flag prefixes are separate scopes.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase23/fields-static'
SPEC=importlib.util.spec_from_file_location('phase23_scalar_cell_model',ROOT/'scripts/analyze_city_auxiliary_phase23.py')
model=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=model;SPEC.loader.exec_module(model)
BUS=importlib.util.spec_from_file_location('frozen_phase21_field_CPU_validator',ROOT/'scripts/verify_city_auxiliary_semantics.py')
busmod=importlib.util.module_from_spec(BUS);sys.modules[BUS.name]=busmod;BUS.loader.exec_module(busmod)
OriginalBus=busmod.OriginalBus;base=model.base


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text())
def seed(m,c):
 c.sp=0xF0;m.ram[0x1F1:0x1F3]=bytes((0xEF,0x7F));return 0x7FF0


def run_original(rom,entry,prepare,watch,limit=70000):
 from py65.devices.mpu6502 import MPU
 m=OriginalBus(rom,11,entry);m.ram[:]=b'\x00'*2048;m.sram[:]=b'\x00'*8192
 c=MPU(memory=m,pc=entry);c.a=37;c.x=83;c.y=191;c.p=0x20;stop=seed(m,c);prepare(m,c)
 steps=0;observed=[]
 while c.pc!=stop:
  if c.pc in watch:
   p=m[0x20]|m[0x21]<<8;observed.append(dict(cpu=c.pc,pointer=p,Y=c.y,effective_address=(p+c.y)&65535))
  c.step();steps+=1;assert steps<limit,(hex(entry),hex(c.pc),steps)
 assert c.sp==0xF2
 return dict(entry_cpu=entry,original_instructions=steps,actual_accesses=observed,final_PC=c.pc,final_SP=c.sp,comparison='actual_original_caller_RTS_address_contract',original_helper_CPU_callbacks=0)


def initialize_officers(m):
 for officer in range(256):
  p=0x3C0+12*officer
  m.sram[p+2]=50;m.sram[p+3]=80;m.sram[p+4]=80;m.sram[p+11]=2


def selection_checks(rom,canonical):
 rows=[]
 for entry,sites in((0xC248,(0xC25A,0xC293)),(0xC2EB,(0xC2FD,0xC332))):
  for city in range(256):
   for count in(0,1,9,10):
    def prepare(m,c):
     initialize_officers(m);m.sram[city*32+17:city*32+27]=bytes([20+i if i<count else 255 for i in range(10)])
     m.sram[0xF5E]=city;m.sram[0xF73:0xF7D]=b'\x01'*10
    row=run_original(rom,entry,prepare,sites)
    assert [r['Y']for r in row['actual_accesses']if r['cpu']==sites[0]]==list(range(17,27))
    for actual in row['actual_accesses']:
     proof=canonical[11,actual['cpu']]['address_contract']
     assert actual['pointer']==0x6000+32*city and actual['Y']in proof['Y_values'] and actual['effective_address']not in base.AUX
    row.update(raw_city_ID=city,roster_prefix_count=count,scope='All raw city IDs with four explicitly prepared roster prefixes. Ten-slot scan and optional nonnegative selected-slot read are executed continuously through real D105/D283 calls; no IRQ/NMI/external mutation.')
    rows.append(row)
 return rows


def follower_checks(rom,canonical):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for city in range(256):
  for count in(0,1,9,10):
   def prepare(m,c):
    initialize_officers(m);m.sram[city*32+17:city*32+27]=bytes([20+i if i<count else 255 for i in range(10)])
    m.ram[0x45]=city;m.ram[0x40]=0;m.ram[0x30]=200
   m=OriginalBus(rom,11,0xCBA3);m.ram[:]=b'\x00'*2048;m.sram[:]=b'\x00'*8192
   c=MPU(memory=m,pc=0xCBA3);c.a=37;c.x=83;c.y=191;c.p=0x20;seed(m,c);prepare(m,c)
   observed=[];steps=0
   while c.pc not in(0xCB98,0xCBF5):
    if c.pc==0xCBB1:
     pointer=m[0x20]|m[0x21]<<8;observed.append(dict(cpu=c.pc,pointer=pointer,Y=c.y,effective_address=(pointer+c.y)&65535))
    c.step();steps+=1;assert steps<70000,(city,count,hex(c.pc))
   row=dict(entry_cpu=0xCBA3,original_instructions=steps,actual_accesses=observed,final_PC=c.pc,final_SP=c.sp,comparison='actual_original_bounded_follower_scan_prefix_not_RTS',original_helper_CPU_callbacks=0)
   assert all(17<=r['Y']<=26 and r['pointer']==0x6000+32*city and r['effective_address']not in base.AUX for r in row['actual_accesses'])
   assert 1<=len(row['actual_accesses'])<=10
   row.update(raw_city_ID=city,roster_prefix_count=count,scope='Actual bounded follower/loyalty scan through real helpers, stopping at its CB98/CBF5 outward continuation. CBA3 is not treated as an independent ordinary RTS function. Numeric inputs are controlled; no natural campaign reachability claim.')
   rows.append(row)
 return rows


def resource_checks(rom,canonical):
 rows=[];sites=(0xCDC3,0xCDC7,0xCE00,0xCE05,0xCE08,0xCE0C,0xCE15,0xCE18,0xCE25,0xCE59,0xCE5E,0xCE64)
 for city in range(256):
  for amount in(0,1,60,255):
   for value in(0,9999):
    def prepare(m,c):
     start=city*32
     for offset in(2,4,6,8,14):m.sram[start+offset:start+offset+2]=value.to_bytes(2,'little')
     m.sram[start+11]=99;m.ram[0x38]=city;m.sram[0xF8D]=amount;c.a=amount
    row=run_original(rom,0xCD70,prepare,sites)
    assert row['actual_accesses']
    for actual in row['actual_accesses']:
     proof=canonical[11,actual['cpu']]['address_contract']
     assert actual['pointer']==0x6000+32*city and actual['Y']in proof['Y_values'] and actual['effective_address']not in base.AUX
    row.update(raw_city_ID=city,initial_A=amount,initial_word_fields=value,scope='Actual CD70 selector caller chain:36 takes6/8/14 for word helpers and11 for byte helper, pointer comes from0038/D105. All original arithmetic helpers execute; no interrupts or Source comparison.')
    rows.append(row)
 # A controlled bare byte-helper input reaches its saturation store. This
 # covers its valid selector, not the caller's narrower percentage range.
 def prepare(m,c):m.ram[0x38]=0;m.ram[0x36]=11;m.sram[11]=100;c.a=255
 row=run_original(rom,0xCE1B,prepare,sites)
 assert any(a['cpu']==0xCE64 for a in row['actual_accesses'])
 assert all(a['Y']==11 and a['effective_address']not in base.AUX for a in row['actual_accesses'])
 row.update(raw_city_ID=0,initial_A=255,bare_helper_selector=11,scope='Explicit standalone CE1B amount255 fixture with admitted selector11. Does not claim the full CD70 caller emits amount255 at CE1B.')
 rows.append(row)
 return rows


def suffix_counterexamples(rom):
 rows=[]
 for entry,watch in((0xCDB9,(0xCDC3,0xCDC7,0xCE00,0xCE05,0xCE08,0xCE0C)),(0xCE1B,(0xCE25,0xCE59,0xCE5E,0xCE64))):
  for selector in(1,28,29,30,31):
   def prepare(m,c):m.ram[0x38]=0;m.ram[0x36]=selector;m.sram[selector]=100;c.a=10
   row=run_original(rom,entry,prepare,watch)
   assert any(a['effective_address']==0x6000+selector and a['effective_address']in base.AUX for a in row['actual_accesses'])
   row.update(bare_helper_selector=selector,bypasses_caller_selector_contract=True,scope='Explicit raw helper-entry counterexample:0036 is prepared outside admitted original caller selector values. The helper itself has no universal auxiliary-address exclusion.')
   rows.append(row)
 return rows


def NZ_checks(rom):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for entry,fallthrough,taken in((0xC28A,0xC28E,0xC297),(0xC329,0xC32D,0xC336)):
  for value in range(256):
   m=OriginalBus(rom,11,entry);m.ram[0x23]=value;c=MPU(memory=m,pc=entry);c.p=0xFF;c.y=value^255
   c.step();c.step()
   assert c.y==value and c.pc==(taken if value&128 else fallthrough)
   rows.append(dict(entry_cpu=entry,raw_cell23=value,stop_PC=c.pc,stop_Y=c.y,original_instruction_count=2,comparison='actual_original_LDY_and_BMI_prefix_not_function_RTS'))
 return rows


def model_checks(engine,canonical):
 checks=[];origin_cache={};origin_hashes={}
 def check(name,value):assert value,name;checks.append(dict(name=name,passed=True))
 S=model.ScalarState
 left=S();left.scalar_cells={0x24:frozenset((17,))};left.numbers=(None,None,frozenset((17,)));left.cell_refs=(None,None,0x24)
 right=left.copy();right.scalar_cells[0x24]=frozenset((26,));right.numbers=(None,None,frozenset((26,)))
 joined=model.scalar_join(left,right)
 check('merge keeps complete current-cell equality across all predecessors and unions raw values',joined.scalar_cells[0x24]==frozenset((17,26))and joined.cell_refs[2]==0x24)
 right.cell_refs=(None,None,None);check('one unpaired predecessor loses equality',model.scalar_join(left,right).cell_refs[2]is None)
 right=left.copy();right.scalar_cells={};check('unknown cell predecessor drops cell and all register references',not model.scalar_join(left,right).scalar_cells and model.scalar_join(left,right).cell_refs[2]is None)
 state=S();state.scalar_cells={0x20:frozenset((1,)),0x24:frozenset((17,))};state.numbers=(frozenset((9,)),frozenset((1,)),frozenset((17,)));state.cell_refs=(None,0x20,0x24)
 result=engine.transfer((11,0xD287),state)
 check('real STA20 creates new current cell generation; old X reference killed',result.scalar_cells[0x20]==frozenset((9,))and result.cell_refs[1]is None and result.cell_refs[0]==0x20)
 check('atomic city factory kills references to overwritten20/21 even when X is restored',engine.apply_call(state,(11,0xD105),(11,0xC255)).cell_refs[1]is None)
 unknown=engine.apply_call(state,None,(11,0xC255));check('unknown callee kills all scalar memory and current-cell references',not unknown.scalar_cells and unknown.cell_refs==(None,None,None))
 # Synthetic instruction metadata only; these are NOT claimed original ROM
 # code positions or CPU cases. Their purpose is to guard the transfer domain.
 key=(31,0x7F00);saved=engine.known.get(key);saved_access=engine.access_index.get(key)
 try:
  for operand in(0x0024,0x0824,0x1024,0x1824):
   engine.known[key]=dict(op='STA',mode='ab',operand=operand,size=3,cpu=key[1],physical_bank=31)
   result=engine.transfer(key,state)
   assert 0x24 not in result.scalar_cells or result.scalar_cells[0x24]==frozenset((9,))
   assert result.cell_refs[2]is None
  check('all four physical RAM mirrors invalidate the current cell relation',True)
  engine.known[key]=dict(op='STA',mode='abx',operand=0xFF80,size=3,cpu=key[1],physical_bank=31)
  result=engine.transfer(key,state)
  check('raw indexed16-bit wrap is conservatively clobbered',not result.scalar_cells and result.cell_refs==(None,None,None))
  engine.known[key]=dict(op='STA',mode='abx',operand=0x00FF,size=3,cpu=key[1],physical_bank=31)
  partial=state.copy();partial.scalar_cells[255]=frozenset((77,));partial.numbers=(frozenset((9,)),frozenset((0,2)),frozenset((17,)))
  result=engine.transfer(key,partial)
  check('singleton MAY-ZP plus non-ZP EA never creates a MUST cell',255 not in result.scalar_cells and engine.must_scalar_store_target(key,partial)is None)
  engine.known[key]=dict(op='STA',mode='iy',operand=0x20,size=2,cpu=key[1],physical_bank=31)
  engine.access_index[key]=dict(Y_values=[0])
  mixed=state.copy();mixed.pairs[0x20]=base.Pair(frozenset((0x24,0x2000)));mixed.numbers=(frozenset((9,)),None,frozenset((0,)));mixed.cell_refs=(None,None,None)
  assert engine.store_effect(key,mixed)==({0x24},False)
  result=engine.transfer(key,mixed)
  check('mixed indirect ZP and IO with no stack flag still cannot create a MUST cell',0x24 not in result.scalar_cells and engine.must_scalar_store_target(key,mixed)is None)
  mirrored=mixed.copy();mirrored.pairs[0x20]=base.Pair(frozenset((0x24,0x824)))
  result=engine.transfer(key,mirrored)
  check('multiple complete EAs aliasing one physical ZP cell do create the correct MUST value',engine.must_scalar_store_target(key,mirrored)==0x24 and result.scalar_cells[0x24]==frozenset((9,)))
 finally:
  if saved is None:engine.known.pop(key)
  else:engine.known[key]=saved
  if saved_access is None:engine.access_index.pop(key,None)
  else:engine.access_index[key]=saved_access
 wide=left.copy();wide.scalar_cells[0x24]=frozenset(range(32));right=left.copy();right.scalar_cells[0x24]=frozenset((32,))
 merged=model.scalar_join(wide,right);check('33-value widening drops the cell instead of assuming a smaller range',0x24 not in merged.scalar_cells and merged.cell_refs[2]is None)
 # The actual zero-displacement BNE has one shared successor. Neither path
 # condition may be inferred from that single address.
 for a in(1,2):
  s=S();s.numbers=(frozenset((a,)),None,None)
  values=engine.branch_successors((8,0xA67C),s)
  assert values and all(t==(8,0xA67E)and v.numbers[0]==frozenset((a,))for t,v in values)
 check('original zero-displacement branch is never mistaken for a false-only edge',True)
 for key,row in canonical.items():
  proof=row['address_contract']
  if proof:
   assert model.old.auxiliary_intersection(proof)==proof['possible_auxiliary_effective_addresses']
   assert len(proof['possible_auxiliary_effective_addresses'])==proof['auxiliary_address_intersection_count']
   assert row['whole_pointer_values']==sorted(model.old.projection_words(proof))and row['Y_values']==model.old.projection_Y(proof)
  if row['classification']==model.DISJOINT:assert proof is not None and not model.old.auxiliary_intersection(proof)
  assert not row['candidate_contract_is_authoritative']
  assert row['authoritative_contract_origin']==row['phase23_authoritative_contract_origin']
  origin=row['authoritative_contract_origin']
  if origin:
   if origin['path']not in origin_cache:
    origin_cache[origin['path']]={(r['physical_bank'],r['cpu']):r for r in base.read(origin['path'])['accesses']}
    origin_hashes[origin['path']]=sha(ROOT/origin['path'])
   assert origin_hashes[origin['path']]==origin['sha256']
   assert proof==origin_cache[origin['path']][key]['address_contract']
 check('every authoritative domain/top projection/origin and nonauthoritative candidate independently consistent',True)
 for name,count in(('all-indirect-accesses.json',1526),('access-contracts.json',589),('new-indirect-accesses.json',45),('phase22-remaining368-handling.json',368)):
  d=read(name);assert len(d['accesses'])==d['access_count']==count
  assert Counter(r['classification']for r in d['accesses'])==d['classification_counts']
  assert all(row==canonical[row['physical_bank'],row['cpu']]for row in d['accesses'])
 check('all1526 old589 new45 and previous368 ledgers preserve complete canonical rows',True)
 groups=read('shared-producer-caller-groups.json')
 check('all368 candidates belong to exactly one shared producer/caller group',len(groups['groups'])==groups['group_count']==110 and Counter((r['physical_bank'],r['cpu'])for g in groups['groups']for r in g['accesses'])==Counter(key for key,row in canonical.items()if row['phase22_classification']!=model.DISJOINT))
 raw=read('raw345-executability-ledger.json');check('all345 raw hypotheses retained byte-for-byte with104operand13data228unknown scope',raw==base.read('analysis/phase22/fields-static/raw345-executability-ledger.json')and raw['window_count']==345)
 dummy=read('logical-vs-dummy-bus-contracts.json');assert len(dummy['accesses'])==1526
 for row in dummy['accesses']:
  proof=canonical[row['physical_bank'],row['cpu']]['address_contract'];expected=model.old.dummy_auxiliary_intersection(proof,row['operation'])if proof else None
  assert expected==row['dummy_auxiliary_bus_addresses']and row['dummy_auxiliary_intersection_count']==(len(expected)if expected is not None else None)
 check('logical effective and dummy bus domains remain separate and recomputed',True)
 check('official auxiliary names remain explicitly unknown',all(v is None for v in read('analysis-summary.json')['official_target_field_names'].values()))
 return checks


def raw_checks(rom):
 count=0
 def walk(value):
  nonlocal count
  if isinstance(value,dict):
   pc=value.get('cpu',value.get('cpu_start',value.get('cpu_address')))
   if all(k in value for k in('physical_bank','raw_hex','rom_offset'))and pc is not None:
    off=base.original(value['physical_bank'],pc);raw=bytes.fromhex(value['raw_hex']);assert value['rom_offset']==off and rom[off:off+len(raw)]==raw;count+=1
   for child in value.values():walk(child)
  elif isinstance(value,list):
   for child in value:walk(child)
 for path in OUT.glob('*.json'):
  if path.name not in('verification.json','evidence.json'):walk(json.loads(path.read_text()))
 return count


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom');args=parser.parse_args();rom=Path(args.rom).read_bytes()
 assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 assert sha(ROOT/'analysis/phase22/verification.json')==model.OLD_AUDIT and sha(ROOT/'build/三国志2超级版-逆向分析-v22.zip')==model.OLD_ZIP
 summary=read('analysis-summary.json');assert sha(ROOT/summary['analyzer_path'])==summary['analyzer_sha256']
 for path,digest in summary['artifact_sha256'].items():
  assert not any(part.startswith('exploratory')for part in Path(path).parts);assert sha(ROOT/path)==digest,path
 rows=read('all-indirect-accesses.json')['accesses'];canonical={(r['physical_bank'],r['cpu']):r for r in rows};assert len(canonical)==1526
 engine=model.Analysis(rom);guards=model_checks(engine,canonical)
 selected=selection_checks(rom,canonical);followers=follower_checks(rom,canonical);resources=resource_checks(rom,canonical);bare=suffix_counterexamples(rom);NZ=NZ_checks(rom)
 assert len(selected)==2048 and len(followers)==1024 and len(resources)==2049 and len(bare)==10 and len(NZ)==512
 observed={r['cpu']for row in selected+followers+resources for r in row['actual_accesses']}
 newly={r['cpu']for r in rows if r['newly_proved_disjoint']};assert newly<=observed,(newly-observed)
 raw_count=raw_checks(rom)
 pins={path:sha(ROOT/path)for path in('scripts/analyze_city_auxiliary_phase23.py','scripts/verify_city_auxiliary_phase23.py','scripts/verify_city_auxiliary_semantics.py','scripts/verify_city_auxiliary_contexts.py')}
 artifacts={str(path.relative_to(ROOT)):sha(path)for path in sorted(OUT.glob('*'))if path.is_file()and path.name not in('verification.json','evidence.json')}
 complete=len(selected)+len(resources)+len(bare)
 result=dict(schema='phase23-must-scalar-cell-original-contract-verification-v1',status='passed',failed_count=0,ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,
  original_contract_CPU_cases=complete+len(followers)+len(NZ),actual_caller_RTS_contract_cases=complete,original_follower_scan_prefix_contract_CPU_cases=len(followers),original_flag_prefix_contract_CPU_cases=len(NZ),
  roster_selection_caller_checks=selected,follower_caller_checks=followers,resource_selector_caller_checks=resources,raw_helper_counterexamples=bare,last_load_NZ_prefix_checks=NZ,
  model_guard_check_count=len(guards),model_checks=guards,original_nested_byte_ranges_verified=raw_count,
  classification_counts=summary['all_indirect_classification_counts'],previous_candidate_count=368,remaining_access_count=summary['remaining_access_count'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],
  source_and_validator_sha256=pins,artifact_sha256=artifacts,scope=['OriginalCPU address/loop/flag contracts only; no recovered Source comparison, native trace, helper callbacks or interrupt injection.',
   'Rawcity0..255 inputs and controlled numeric roster/resource/leader values are disclosed. Normal callerRTS/SP and actual selected effective addresses are checked; not a Source comparison of all2K/8K/AXYP/ports/banks.',
   'Bare resource helpers with selectors1/28..31 intentionally demonstrate aliases outside the admitted complete caller context.',
  'The1024 CBA3 scans stop at outward CB98/CBF5 continuations, and512 LDY/BMI checks stop after two instructions; these are prefixes, not complete function returns. Model guards are separately counted.'])
 model.save('verification.json',result)
 model.save('evidence.json',dict(schema='phase23-must-scalar-cell-original-contract-evidence-v1',status='passed',ROM_sha256=base.ROM_SHA256,
  analyzer_path='scripts/analyze_city_auxiliary_phase23.py',analyzer_sha256=sha(ROOT/'scripts/analyze_city_auxiliary_phase23.py'),validator_path='scripts/verify_city_auxiliary_phase23.py',validator_sha256=sha(__file__),
  source_and_validator_sha256=pins,artifact_sha256=summary['artifact_sha256']|artifacts|{'analysis/phase23/fields-static/verification.json':sha(OUT/'verification.json')},source_CPU_cases=0,
  original_contract_CPU_cases=result['original_contract_CPU_cases'],actual_caller_RTS_contract_cases=complete,original_follower_scan_prefix_contract_CPU_cases=len(followers),original_flag_prefix_contract_CPU_cases=len(NZ),model_guard_check_count=len(guards),
  previous_candidate_count=368,remaining_access_count=summary['remaining_access_count'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],classification_counts=summary['all_indirect_classification_counts'],
  newly_excluded_sites=[dict(physical_bank=r['physical_bank'],cpu=r['cpu'],raw_hex=r['raw_hex'],Y_values=r['Y_values'],scalar_cells=r['address_contract'].get('scalar_cells_at_access',{}))for r in rows if r['newly_proved_disjoint']],
  known_producer_caller_group_count=summary['grouping_count'],raw_window_categories=summary['raw_window_categories'],official_target_field_names=summary['official_target_field_names'],limits=summary['limits']+result['scope']))
 print(json.dumps({key:result[key]for key in('status','original_contract_CPU_cases','actual_caller_RTS_contract_cases','model_guard_check_count','remaining_access_count')},ensure_ascii=False))


if __name__=='__main__':main()
