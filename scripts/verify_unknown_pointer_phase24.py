#!/usr/bin/env python3
"""Phase24 original-CPU typed-pointer contracts and conservative model guards.

Source comparisons and Native runs are zero here. Normal helper/consumer
caller checks, raw alias counterexamples and model guards retain their scopes.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase24/fields-static'
SPEC=importlib.util.spec_from_file_location('phase24_pointer_contract_model',ROOT/'scripts/analyze_unknown_pointer_phase24.py')
model=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=model;SPEC.loader.exec_module(model);base=model.base
BUS=importlib.util.spec_from_file_location('frozen_phase21_original_CPU_bus',ROOT/'scripts/verify_city_auxiliary_semantics.py')
busmod=importlib.util.module_from_spec(BUS);sys.modules[BUS.name]=busmod;BUS.loader.exec_module(busmod);OriginalBus=busmod.OriginalBus


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text())
def seed(m,c):c.sp=0xF0;m.ram[0x1F1:0x1F3]=bytes((0xEF,0x7F));return 0x7FF0


def typed_helper_checks(rom):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for raw in range(256):
  for troops in(0,1,99,100,999,1000,1098,65535):
   for reserve in(0,99,9999,10000,65535):
    m=OriginalBus(rom,28,0xD987);fill=(raw^troops^reserve)&255;m.ram[:]=bytes((fill,))*2048;m.sram[:]=bytes((fill^0xA5,))*8192
    pointer=0x63C0+12*raw;m.ram[0:2]=pointer.to_bytes(2,'little');m.ram[2:4]=troops.to_bytes(2,'little');m.ram[0x42C:0x42E]=reserve.to_bytes(2,'little');m.sram[pointer-0x6000+8:pointer-0x6000+10]=troops.to_bytes(2,'little')
    c=MPU(memory=m,pc=0xD987);c.a=raw;c.x=fill;c.y=fill^255;c.p=0x20|(raw&1);stop=seed(m,c)
    before_ram=bytes(m.ram);before_sram=bytes(m.sram);before_banks=list(m.banks);steps=0
    while c.pc!=stop:c.step();steps+=1;assert steps<1000,(raw,troops,reserve,hex(c.pc))
    assert c.sp==0xF2 and(m[0]|m[1]<<8)==pointer and(m[0x10]|m[0x11]<<8)==pointer and m.banks==before_banks
    ram_allowed={0,1,2,3,4,5,6,7,0x10,0x11,0x42C,0x42D,0x1EF,0x1F0}
    ram_changed={a for a,(old,new)in enumerate(zip(before_ram,m.ram))if old!=new};sram_changed={a+0x6000 for a,(old,new)in enumerate(zip(before_sram,m.sram))if old!=new}
    assert ram_changed<=ram_allowed and sram_changed<={pointer+8,pointer+9}
    assert c.x==fill and all(address<0x2000 or 0x6000<=address<0x8000 for address,value in m.writes)
    rows.append(dict(raw_officer_ID=raw,initial_pointer=pointer,initial_raw_troops=troops,initial_reserve=reserve,output_pointer=m[0]|m[1]<<8,
      final_PC=c.pc,final_SP=c.sp,original_instructions=steps,whole_RAM_2048_write_scope_verified=True,whole_SRAM_8192_write_scope_verified=True,
      actual_caller_RTS=True,comparison='actual_original_typed_helper_pointer_and_write_scope_contract',original_helper_CPU_callbacks=0))
 return rows


def caller_checks(rom,canonical):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for raw in range(256):
  for button in(0x40,0x80):
   m=OriginalBus(rom,28,0xD805);m.ram[:]=b'\x00'*2048;m.sram[:]=b'\x00'*8192
   pointer=0x63C0+12*raw;troops=(0,100,199,999,1098,65535)[raw%6];reserve=0 if button==0x40 else 9999
   m.ram[0x402]=2;m.ram[0x12]=0;m.ram[0x81]=button;m.ram[0x42C:0x42E]=reserve.to_bytes(2,'little')
   m.sram[2*32+17:2*32+27]=bytes((raw,255,255,255,255,255,255,255,255,255));m.sram[2*32+12:2*32+14]=reserve.to_bytes(2,'little');m.sram[pointer-0x6000+8:pointer-0x6000+10]=troops.to_bytes(2,'little')
   c=MPU(memory=m,pc=0xD805);c.a=raw;c.x=31;c.y=255;c.p=0x20;stop=seed(m,c);steps=0;observed=[];helper_inputs=[]
   while c.pc!=stop:
    if c.pc==0xD987:helper_inputs.append(m[0]|m[1]<<8)
    if(28,c.pc)in model.TARGETS:
     actual_pointer=m[0]|m[1]<<8;proof=canonical[28,c.pc]['address_contract'];address=(actual_pointer+c.y)&65535
     assert actual_pointer==pointer and c.y in proof['Y_values'] and address not in base.AUX
     observed.append(dict(cpu=c.pc,actual_pointer=actual_pointer,Y=c.y,effective_address=address))
    c.step();steps+=1;assert steps<10000,(raw,button,hex(c.pc))
   assert c.sp==0xF2 and all(p==pointer for p in helper_inputs)and observed
   rows.append(dict(raw_officer_ID=raw,prepared_cursor=0,prepared_city=2,buttons_byte_0081=button,initial_raw_troops=troops,initial_reserve=reserve,
      observed_helper_input_words=helper_inputs,selected_consumer_accesses=observed,final_PC=c.pc,final_SP=c.sp,original_instructions=steps,
      output_pair00=m[0]|m[1]<<8,output_pair00_preservation_claim=False,
      comparison='actual_original_D805_complete_caller_selected_address_contract',original_helper_CPU_callbacks=0,
      scope='Controlled originalCPU fixture enters D805 with selected raw rosterID and Left/Right byte. It executes original formatting/queue producers through RTS, not the full D64A/UI/PPU/NMI cycle or Native ordinary inputs. D805 reuses00/01 for formatting after the selected consumers; only D987 has the conditional pointer-preservation contract.'))
 assert{a['cpu']for row in rows for a in row['selected_consumer_accesses']}=={pc for bank,pc in model.TARGETS}
 return rows


def alias_counterexamples(rom):
 from py65.devices.mpu6502 import MPU
 rows=[]
 for pointer in(0x0008,0x07F8,0xFFF8,0x01E9,0x6FC0):
  m=OriginalBus(rom,28,0xD987);m.ram[:]=b'\x00'*2048;m.sram[:]=b'\x00'*8192
  c=MPU(memory=m,pc=0xD987);c.a=37;c.x=19;c.y=83;c.p=0x20;seed(m,c)
  m.ram[0:2]=pointer.to_bytes(2,'little');m.ram[2:4]=(199).to_bytes(2,'little');steps=0
  # FFF8 first store wraps to0000. Stop before a later now-ROM/IO-addressed
  # store rather than inventing a permissive hardware environment.
  if pointer==0xFFF8:
   while c.pc!=0xD9FA:c.step();steps+=1;assert steps<1000
   assert(m[0]|m[1]<<8)!=pointer
   comparison='actual_original_wrapping_pointer_corruption_prefix_before_unmodelled_IO'
  else:
   while c.pc!=0xDA01:c.step();steps+=1;assert steps<1000
   c.step();steps+=1
   comparison='actual_original_bare_helper_alias_RTS_counterexample'
   if pointer==0x07F8:assert(m[0]|m[1]<<8)!=pointer and c.pc==0x7FF0
   if pointer==0x01E9:assert c.pc!=0x7FF0
   if pointer==0x0008:assert(m[0x10]|m[0x11]<<8)!=pointer
  rows.append(dict(input_pointer=pointer,input_is_admitted=False,final_pointer=m[0]|m[1]<<8,final_saved_word=m[0x10]|m[0x11]<<8,
   final_PC=c.pc,final_SP=c.sp,original_instructions=steps,comparison=comparison,original_helper_CPU_callbacks=0,
   scope='Explicit raw negative-domain CPU fixture, not a natural caller or Native preparation. Outside the admitted domain some inputs corrupt00/01 or callerstack, while others coincidentally retain00/01; rejection is not a claim that all outside values must fail.'))
 return rows


def model_checks(engine,canonical):
 checks=[]
 def check(name,value):assert value,name;checks.append(dict(name=name,passed=True))
 S=model.old.ScalarState
 for values in(frozenset((0x63C0,)),model.OFFICER_WORDS,frozenset((0x6FB4,))):
  state=S();state.pairs[0]=base.Pair(values)
  result=engine.apply_call(state,(28,0xD987),(28,0xD837))
  assert result.pairs[0].addresses==values
 check('only a complete admitted input word is preserved with all rawID0..255 retained',True)
 for values in(frozenset((0xFFF8,)),frozenset((0x63C0,0xFFF8)),frozenset((0x6FC0,)),frozenset((0x07F8,))):
  state=S();state.pairs[0]=base.Pair(values)
  assert 0 not in engine.apply_call(state,(28,0xD987),(28,0xD837)).pairs
 check('unknown mixed or nonadmitted raw pointer domains never acquire the postcondition',True)
 check('missing full input pair cannot be manufactured by the helper contract',0 not in engine.apply_call(S(),(28,0xD987),(28,0xD837)).pairs)
 state=S();state.pairs[0]=base.Pair(frozenset((0x63C0,)))
 check('bare middle target does not receive the entry contract',0 not in engine.apply_call(state,(28,0xD9E4),(28,0xD837)).pairs)
 # Independent hypothetical-clobber model regression, not claimed ROM code.
 key=(31,0xEA7E);saved=engine.known[key];bad=dict(saved,operand=0x10);engine.known[key]=bad
 try:
  try:engine.prove_typed_pointer_return()
  except AssertionError:pass
  else:raise AssertionError('A helper writing the saved pair must be rejected')
 finally:engine.known[key]=saved
 check('any callee write to the saved10/11 word invalidates the proof',True)
 contract=read('typed-pointer-return-contract.json');check('complete entry/helper/write/dominator proof regenerated from frozen original bytes',engine.prove_typed_pointer_return()==contract)
 prior={(r['physical_bank'],r['cpu']):r for r in base.read('analysis/phase23/fields-static/all-indirect-accesses.json')['accesses']}
 for key,row in canonical.items():
  proof=row['address_contract']
  if proof:
   hit=model.old.old.auxiliary_intersection(proof);assert hit==proof['possible_auxiliary_effective_addresses']and len(hit)==proof['auxiliary_address_intersection_count']
   assert row['whole_pointer_values']==sorted(model.old.old.projection_words(proof))and row['Y_values']==model.old.old.projection_Y(proof)
  if row['classification']==model.DISJOINT:assert proof is not None and not model.old.old.auxiliary_intersection(proof)
  assert row['candidate_contract_is_authoritative']is False
  if key not in model.TARGETS:assert row['classification']==prior[key]['classification']and proof==prior[key]['address_contract']
 check('all1526 authoritative intersections/projections exact; only selected10 sites gain new authority',True)
 check('all ten selected officer8/9 accesses newly disjoint; four other G086 lifetimes stay unknown',{k for k,r in canonical.items()if r['newly_proved_disjoint']}==set(model.TARGETS)and all(canonical[28,pc]['classification']=='unresolved_pointer_or_index_contract'for pc in(0xC853,0xC87B,0xC8BB,0xDC6F)))
 groups=read('unknown-producer-ranking.json');members=[r for g in groups['groups']for r in g['accesses']]
 expected={key for key,row in prior.items()if row['classification']=='unresolved_pointer_or_index_contract'}
 check('full55 unknown-producer groups and270 accesses retained once with current/historical classes',len(groups['groups'])==55 and len(members)==270 and Counter((r['physical_bank'],r['cpu'])for r in members)==Counter(expected)and all(r['classification']==canonical[r['physical_bank'],r['cpu']]['classification']for r in members))
 check('only one selected group and no forced whole-group clearing',[g['group_id']for g in groups['groups']if g['selected_for_new_context_contract']]==['G086']and sum(g['remaining_unknown_access_count']for g in groups['groups'])==260)
 for name,n in(('all-indirect-accesses.json',1526),('access-contracts.json',589),('new-indirect-accesses.json',45),('phase23-remaining351-handling.json',351),('unknown270-handling.json',270)):
  d=read(name);assert d['access_count']==len(d['accesses'])==n and d['classification_counts']==Counter(r['classification']for r in d['accesses'])
  assert all(r==canonical[r['physical_bank'],r['cpu']]for r in d['accesses'])
 check('1526/589/45/351/270 canonical ledgers exact',True)
 check('raw345104operand13data228noentry ledger preserved byte-for-byte',read('raw345-executability-ledger.json')==base.read('analysis/phase23/fields-static/raw345-executability-ledger.json'))
 dummy=read('logical-vs-dummy-bus-contracts.json');assert len(dummy['accesses'])==1526
 for row in dummy['accesses']:
  proof=canonical[row['physical_bank'],row['cpu']]['address_contract'];hits=model.old.old.dummy_auxiliary_intersection(proof,row['operation'])if proof else None
  assert row['dummy_auxiliary_bus_addresses']==hits and row['dummy_auxiliary_intersection_count']==(len(hits)if hits is not None else None)
 check('logical effective addresses and dummy bus domains independently recomputed',True)
 check('official city auxiliary names remain null',all(value is None for value in read('analysis-summary.json')['official_target_field_names'].values()))
 return checks


def raw_checks(rom):
 count=0
 def walk(v):
  nonlocal count
  if isinstance(v,dict):
   pc=v.get('cpu',v.get('cpu_start',v.get('cpu_address')))
   if pc is not None and all(key in v for key in('physical_bank','rom_offset','raw_hex')):
    off=base.original(v['physical_bank'],pc);raw=bytes.fromhex(v['raw_hex']);assert off==v['rom_offset']and rom[off:off+len(raw)]==raw;count+=1
   for child in v.values():walk(child)
  elif isinstance(v,list):
   for child in v:walk(child)
 for path in OUT.glob('*.json'):
  if path.name not in('verification.json','evidence.json'):walk(json.loads(path.read_text()))
 return count


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom');args=parser.parse_args();rom=Path(args.rom).read_bytes()
 assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256 and sha(ROOT/'analysis/phase23/verification.json')==model.OLD_AUDIT and sha(ROOT/model.ZIP_PATH)==model.OLD_ZIP
 summary=read('analysis-summary.json');assert sha(ROOT/summary['analyzer_path'])==summary['analyzer_sha256']
 for path,digest in summary['artifact_sha256'].items():
  assert not any(part.startswith('exploratory')for part in Path(path).parts);assert sha(ROOT/path)==digest,path
 allrows=read('all-indirect-accesses.json')['accesses'];canonical={(r['physical_bank'],r['cpu']):r for r in allrows};assert len(canonical)==1526
 engine=model.Analysis(rom);guards=model_checks(engine,canonical)
 helper=typed_helper_checks(rom);callers=caller_checks(rom,canonical);negative=alias_counterexamples(rom)
 assert len(helper)==10240 and len(callers)==512 and len(negative)==5
 raw=raw_checks(rom)
 pins={p:sha(ROOT/p)for p in('scripts/analyze_unknown_pointer_phase24.py','scripts/verify_unknown_pointer_phase24.py','scripts/verify_city_auxiliary_semantics.py','scripts/verify_city_auxiliary_contexts.py')}
 artifacts={str(p.relative_to(ROOT)):sha(p)for p in sorted(OUT.glob('*'))if p.is_file()and p.name not in('verification.json','evidence.json')}
 result=dict(schema='phase24-typed-pointer-return-original-contract-validation-v1',status='passed',failed_count=0,ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,
  original_contract_CPU_cases=len(helper)+len(callers)+len(negative),typed_helper_actual_caller_RTS_CPU_cases=len(helper),D805_actual_caller_RTS_CPU_cases=len(callers),raw_alias_counterexample_CPU_cases=len(negative),
  helper_contract_checks=helper,D805_caller_contract_checks=callers,raw_alias_counterexamples=negative,model_guard_check_count=len(guards),model_checks=guards,original_nested_byte_ranges_verified=raw,
  all_indirect_classification_counts=summary['all_indirect_classification_counts'],previous_candidate_count=351,remaining_access_count=summary['remaining_access_count'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],
  source_and_validator_sha256=pins,artifact_sha256=artifacts,
  scope=['OriginalCPU pointer/address contracts and model guards only; no recovered Source differential cases, helper callbacks, native frame or inserted interrupts.',
   '10240 typed helper cases cover every rawofficerID0..255 ×8 rawtroop words ×5 reserves, normal callerPC/SP, pointer equality, all2048RAM and8192SRAM write-scope and no port/bank changes; not an independent Source comparison of all AXYP/memory values.',
   '512 D805 cases execute actual complete caller/formatting/queue code but not D64A controls/commit or PPU/NMI frame. Input button bytes are controlled originalCPU fixtures, not Native handpad captures.',
   'Five raw outside-domain helper cases show pointer/callerstack/mirror/wrap aliases. FFF8 stops after its first corrupting store before later unmodelled IO; these cases are not five ordinary complete caller returns.'])
 model.save('verification.json',result)
 model.save('evidence.json',dict(schema='phase24-typed-pointer-lifecycle-evidence-v1',status='passed',ROM_sha256=base.ROM_SHA256,
  analyzer_path='scripts/analyze_unknown_pointer_phase24.py',analyzer_sha256=sha(ROOT/'scripts/analyze_unknown_pointer_phase24.py'),validator_path='scripts/verify_unknown_pointer_phase24.py',validator_sha256=sha(__file__),
  source_and_validator_sha256=pins,artifact_sha256=summary['artifact_sha256']|artifacts|{'analysis/phase24/fields-static/verification.json':sha(OUT/'verification.json')},
  source_CPU_cases=0,original_contract_CPU_cases=result['original_contract_CPU_cases'],typed_helper_actual_caller_RTS_CPU_cases=len(helper),D805_actual_caller_RTS_CPU_cases=len(callers),raw_alias_counterexample_CPU_cases=len(negative),model_guard_check_count=len(guards),
  all_indirect_classification_counts=summary['all_indirect_classification_counts'],previous_candidate_count=351,remaining_access_count=summary['remaining_access_count'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],
  original_static_instruction_positions=dict(D987_body=50,EA7C_callee=22),unknown_input_group_count=55,unknown_input_access_count=270,official_target_field_names=summary['official_target_field_names'],limits=summary['limits']+result['scope']))
 print(json.dumps({k:result[k]for k in('status','original_contract_CPU_cases','model_guard_check_count','remaining_access_count')},ensure_ascii=False))


if __name__=='__main__':main()
