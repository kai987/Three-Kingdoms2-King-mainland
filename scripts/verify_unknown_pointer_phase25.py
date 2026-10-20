#!/usr/bin/env python3
"""OriginalCPU contracts for one complete appearance pointer; Source cases0."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import analyze_unknown_pointer_phase25 as model
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import CapturedServiceMemory
OUT=model.OUT;base=model.base
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class ReadWatchMemory(CapturedServiceMemory):
 """Validator-only py65 read observation; no invented dummy read is issued."""
 trace_enabled=False
 def __getitem__(self,address):
  if self.trace_enabled:self.read_trace.append(address)
  return super().__getitem__(address)
def rawbus(rom):return ReadWatchMemory(rom,banks=(17,10,11,31),read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 allrows=json.loads((OUT/'all-indirect-accesses.json').read_text())['accesses'];canonical={(r['physical_bank'],r['cpu']):r for r in allrows};e=model.Analysis(rom);checks=[]
 def check(name,condition):assert condition,name;checks.append(dict(name=name,passed=True))
 typed=[];constructor=[];reads=[];cross=[];bus_observations=[]
 for raw in range(256):
  # Actual original helper frame shape at C601. Registers and nonselected
  # bytes are controlled inputs, not forged Native captures.
  m=rawbus(rom);m.ram[:]=bytes((raw^0xA5,))*2048;m.sram[:]=bytes((raw,))*8192;m[0x20]=raw;m[0x21]=20;m.ram[0x1F8:0x1FA]=bytes((3,0xC6))
  c=MPU(memory=m,pc=0xD471);c.sp=0xF7;c.a=20;c.x=raw^255;c.y=22;c.p=32;before=bytes(m.ram);sram=bytes(m.sram);steps=0
  while c.pc!=0xC604:c.step();steps+=1;assert steps<200
  allowed={0x20,0x21,0x2A,0x2B,0x2C};changed={i for i,(x,y)in enumerate(zip(before,m.ram))if x!=y}
  assert changed<=allowed and bytes(m.sram)==sram and c.sp==0xF9 and c.x==raw^255 and not m.io_writes and not m.io_reads and m.banks==[17,10,11,31]
  assert m[0x2A]|m[0x2B]<<8==raw*20
  typed.append(dict(raw_city=raw,multiplier=20,product=m[0x2A]|m[0x2B]<<8,final_PC=c.pc,final_SP=c.sp,original_instructions=steps,comparison='original_D471_actual_software_frame_RTS',RAM2048_write_scope=True,SRAM8192_unchanged=True))
  # Full real constructor, including JSR and destructive helper work.
  m=rawbus(rom);m[0x36]=raw;c=MPU(memory=m,pc=0xC5F8);c.sp=0xF9;c.p=32;steps=0
  while c.pc!=0xC616:c.step();steps+=1;assert steps<250
  pointer=m[0x22]|m[0x23]<<8;assert pointer==0x8B1C+20*raw and c.sp==0xF9 and m[0x37]==0
  constructor.append(dict(raw_city=raw,output_pointer=pointer,original_instructions=steps,final_PC=c.pc,final_SP=c.sp,comparison='original_complete_constructor_prefix_C5F8_to_C616'))
  for pair in range(128):
   m[0x37]=pair*2;c.pc=0xC616;c.sp=0xF9;steps=0;observed=[]
   while c.pc!=0xC626:
    watch=c.pc in(0xC61F,0xC624)and(raw==0 and pair==0 or raw==255 and pair>=124)
    if c.pc in(0xC61F,0xC624):
     address=(pointer+c.y)&65535;physical=m.banks[(address-0x8000)//8192];value=m[address];expected=rom[16+physical*8192+(address&8191)]
     assert value==expected and address>=0x8000 and address not in base.AUX
     proof=canonical[11,c.pc]['address_contract'];assert pointer in proof['whole_pointer_values']and c.y in proof['Y_values']
     candidate=(pointer&0xFF00)|((pointer+c.y)&255);page_cross=bool((pointer&255)+c.y>255)
     observed.append(dict(cpu=c.pc,pointer=pointer,Y=c.y,logical_address=address,physical_bank=physical,ROM_offset=16+physical*8192+(address&8191),value=value,candidate_not_actual_dummy_address=candidate,page_cross_dummy_read_required=page_cross,actual_dummy_bus_address=candidate if page_cross else None,actual_dummy_address_basis='Pinned official NstCpu::IndY_R rule; required hardware read, not observed by py65'))
    if watch:m.read_trace=[];m.trace_enabled=True;before_cycles=c.processorCycles
    c.step();steps+=1;assert steps<=8
    if watch:
     m.trace_enabled=False;access=observed[-1];trace=list(m.read_trace)
     assert trace==[access['cpu'],access['cpu']+1,0x22,0x23,access['logical_address']]
     assert c.processorCycles-before_cycles==5+int(access['page_cross_dummy_read_required'])
     bus_observations.append(dict(raw_city=raw,access=access,py65_step_read_addresses=trace,py65_step_cycles=c.processorCycles-before_cycles,py65_dummy_bus_cycle_observed=False,scope='Read logger around an existing matrix instruction; no additional CPU case. py65 charges the crossing cycle but does not execute the dummy memory read.'))
   assert len(observed)==2 and observed[0]['Y']==pair*2 and observed[1]['Y']==pair*2+1 and m[0x37]==((pair*2+2)&255)
   row=dict(raw_city=raw,pair_index=pair,accesses=observed,original_instructions=steps,comparison='original_pair_read_prefix_C616_to_C626')
   reads.append(row)
   if any(x['logical_address']>=0xA000 for x in observed):cross.append(row)
 # Conservative must-entry checks, including mixed-path builder joins.
 state=base.State();d=e.appearance_descriptor
 for pc in model.PREFIX:
  key=11,pc
  if pc==0xC601:state=e.apply_call(state,(11,0xD471),key)
  else:state=e.transfer(key,state)
 check('complete original prefix creates all256 full pointer words',state.pairs[0x22].addresses==model.WORDS)
 bare=e.transfer((11,0xC614),base.State());check('bare final high-store never manufactures a full pair',0x22 not in bare.pairs)
 check('wrong callsite cannot preserve active constructor capability',d['id']not in e.apply_call(state,(11,0xD471),(11,0xC602)).builders)
 prefix=base.State()
 for pc in model.PREFIX[:4]:prefix=e.transfer((11,pc),prefix)
 joined=base.join(prefix,base.State());check('must-join with a bypass path kills builder',d['id']not in joined.builders)
 check('only exact multiply target passes active prefix capability',d['id']not in e.apply_call(prefix,(11,0xD472),(11,0xC601)).builders)
 oldrows=json.loads((ROOT/'analysis/phase24/fields-static/all-indirect-accesses.json').read_text())['accesses'];oldcanonical={(r['physical_bank'],r['cpu']):r for r in oldrows}
 for key,r in canonical.items():
  if key not in model.TARGETS:assert r['address_contract']==oldcanonical[key]['address_contract']and r['classification']==oldcanonical[key]['classification']
  if r['address_contract']:
   hits=model.old.old.old.auxiliary_intersection(r['address_contract']);assert hits==r['address_contract']['possible_auxiliary_effective_addresses']
 check('all1526 canonical logical domains checked; only selected two change authority',len(canonical)==1526 and{key for key,r in canonical.items()if r['newly_proved_disjoint']}==set(model.TARGETS))
 check('raw255 crossingA000A007 maps to physical10, not17',len(cross)==4 and all(x['physical_bank']==10 for r in cross for x in r['accesses']))
 check('full even/odd cursor cycle has no guessed10pair bound',len(reads)==32768 and {a['Y']for r in reads for a in r['accesses']}==set(range(256)))
 check('all rawcity bytes remain in constructor',len(constructor)==256 and len(typed)==256)
 dummy=json.loads((OUT/'logical-vs-dummy-bus-contracts.json').read_text())['accesses']
 for row in dummy:
  proof=canonical[row['physical_bank'],row['cpu']]['address_contract'];hits=model.old.old.old.dummy_auxiliary_intersection(proof,row['operation'])if proof else None
  assert hits==row['dummy_auxiliary_bus_addresses']
 check('logical and page dummy bus domains recomputed independently',len(dummy)==1526 and len(bus_observations)==10 and sum(x['access']['page_cross_dummy_read_required']for x in bus_observations)==8)
 check('official cityaux names remain unknown',all(v is None for v in json.loads((OUT/'analysis-summary.json').read_text())['official_target_field_names'].values()))
 check('all252 original closure positions, mapper dominance and typed-store lifetime proof regenerated',model.prove_mapping_lifetime(e)==json.loads((OUT/'mapping-lifetime-contract.json').read_text()))
 raw_count=0
 def walk(value):
  nonlocal raw_count
  if isinstance(value,dict):
   pc=value.get('cpu',value.get('cpu_start',value.get('cpu_address')))
   if pc is not None and all(k in value for k in('physical_bank','rom_offset','raw_hex')):
    offset=base.original(value['physical_bank'],pc);raw=bytes.fromhex(value['raw_hex']);assert offset==value['rom_offset']and rom[offset:offset+len(raw)]==raw;raw_count+=1
   for child in value.values():walk(child)
  elif isinstance(value,list):
   for child in value:walk(child)
 for path in OUT.glob('*.json'):
  if path.name not in('evidence.json','verification.json'):walk(json.loads(path.read_text()))
 check('nested original-byte location and payload objects all match pinned ROM',raw_count>0)
 pins={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),ROOT/'scripts/analyze_unknown_pointer_phase25.py',ROOT/'scripts/analyze_unknown_pointer_phase24.py')}
 for module in tuple(sys.modules.values()):
  path=Path(getattr(module,'__file__','')or'/nonexistent')
  if path.is_file()and path.is_relative_to(ROOT/'scripts'):pins[str(path.relative_to(ROOT))]=sha(path)
 for path in(ROOT/'source/recovered').glob('*.py'):pins[str(path.relative_to(ROOT))]=sha(path)
 core_path=ROOT/'analysis/phase25/runtime/core-provenance/upstream/source/core/NstCpu.cpp';core=core_path.read_text();begin=core.index('\t\tuint Cpu::IndY_R()');end=core.index('\n\t\tinline uint Cpu::IndY_RW',begin);official_rule=core[begin:end]
 assert 'if (indexed & 0x100)'in official_rule and 'PeekBus( data - 0x100 );'in official_rule and 'data = PeekBus( data );'in official_rule
 artifacts={str(p.relative_to(ROOT)):sha(p)for p in OUT.glob('*.json')if p.name not in('verification.json','evidence.json')}
 summary=json.loads((OUT/'analysis-summary.json').read_text());result=dict(schema='phase25-original-appearance-pointer-contract-validation-v1',status='passed',failed_count=0,ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,original_contract_CPU_cases=len(typed)+len(constructor)+len(reads),actual_caller_RTS_CPU_cases=len(typed),constructor_prefix_CPU_cases=len(constructor),pair_read_prefix_CPU_cases=len(reads),typed_helper_checks=typed,constructor_checks=constructor,pair_read_checks=reads,raw_code_window_crossing_cases=cross,model_guard_check_count=len(checks),model_checks=checks,original_nested_byte_ranges_verified=raw_count,source_and_validator_sha256=pins,artifact_sha256=artifacts,all_indirect_classification_counts=summary['all_indirect_classification_counts'],remaining_access_count=summary['remaining_access_count'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],limits=['OriginalCPU contracts are not Source differential cases or Native video frames.','256 constructor and32768 read-prefix comparisons deliberately enter controlled original labels; they are not complete C5D2 caller returns.','All rawcity and full byte cursor values remain. Mapping17/10 is an explicit originalCPU input here; natural caller mapping is separately captured.','No inserted IRQ/NMI or arbitrary bare suffix claim; source helper, parent integration and passive Native evidence are separate.'])
 result['IndY_read_bus_semantics']=dict(metadata_correction='The uncorrected-page formula is a candidate address, not an actual extra read when no page crossing occurs.',official_core_path=str(core_path.relative_to(ROOT)),official_core_sha256=sha(core_path),official_IndY_R_source=official_rule,py65_IndirectYAddr_source=inspect.getsource(MPU.IndirectYAddr),py65_LDA_source=inspect.getsource(MPU.opLDA),py65_bus_observations_within_existing_cases=bus_observations,extra_CPU_cases=0,unmodified_core_internal_trace=False)
 result['artifact_sha256'][str(core_path.relative_to(ROOT))]=sha(core_path)
 result['limits'].append('py65 does not issue IndY_R dummy memory reads even when it adds the page-cross cycle. Required dummy metadata is deduced from the pinned official core rule; no Native/py65 bus observation is fabricated.')
 readme=OUT/'README.md';note='\n## IndY_R候选地址与实际额外读取\n\n每条pair_read_checks访问的candidate_not_actual_dummy_address只是未进位地址公式。只有page_cross_dummy_read_required=true时，官方核心IndY_R才执行额外读，actual_dummy_bus_address才非null；未跨页没有额外dummy（如rawcity0/Y0）。raw255/Y248..255确实跨页，因此9F00..9F07额外读取成立。py65只增加跨页周期，不调用该dummy内存读；验证器对既有矩阵10条指令记录实际py65读序，不能将公式冒称观察到的总线事件。原Native配兵提交STA的无条件dummy读取是另一种IndY_W规则，与此处LDA的条件读取分开。\n'
 text=readme.read_text().split('\n## IndY_R候选地址与实际额外读取')[0];readme.write_text(text+note)
 model.save('verification.json',result);model.save('evidence.json',dict(schema='phase25-original-appearance-pointer-evidence-v1',status='passed',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,original_contract_CPU_cases=result['original_contract_CPU_cases'],actual_caller_RTS_CPU_cases=len(typed),constructor_prefix_CPU_cases=len(constructor),pair_read_prefix_CPU_cases=len(reads),model_guard_check_count=len(checks),source_and_validator_sha256=pins,artifact_sha256=artifacts|{'analysis/phase25/fields-static/verification.json':sha(OUT/'verification.json')},all_indirect_classification_counts=summary['all_indirect_classification_counts'],remaining_access_count=summary['remaining_access_count'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],official_target_field_names=summary['official_target_field_names'],limits=result['limits']))
 print(json.dumps({k:result[k]for k in('status','original_contract_CPU_cases','model_guard_check_count','remaining_access_count')}))
if __name__=='__main__':main()
