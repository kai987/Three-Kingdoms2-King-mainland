#!/usr/bin/env python3
"""Declare the bounded EE07 family before any Source/CPU execution."""
from pathlib import Path
import collections,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-ee07-return-family'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(n,x):
 p=OUT/n;assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def off(b,p):return 16+b*8192+(p&8191)
def iid(b,p):return f'I:{ROM_SHA}:b{b}:cpu{p:04X}:rom{off(b,p):06X}'
def main():
 assert read(OUT/'frozen-before.json')['status']==read(OUT/'frozen-ancestral-before.json')['status']=='passed'
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 atlas=read(ROOT/'analysis/phase18/control/instruction-atlas.json')
 calls=[dict(bank=r['physical_bank'],pc=r['cpu'],rom_offset=r['rom_offset'],id=iid(r['physical_bank'],r['cpu']))for r in atlas['instructions']if r['op']=='JSR'and r.get('operand')==0xEE07]
 assert len(calls)==155 and len({(r['bank'],r['pc'])for r in calls})==155
 for r in calls:assert rom[off(r['bank'],r['pc']):off(r['bank'],r['pc'])+3]==bytes.fromhex('2007ee')
 sites=[dict(name='A06F-stateful-phase0',call_pc=0xA06F,selector=0x3D,target=0xA039,target_pair=[29,30],body=0xBC83,body_rts=0xBC9A,continuation=0xA074,phase=0,
             owner='SceneCoordinator -> GlobalUIController.city_workers -> CityUIWorkers.block_menu_entry -> cityuiworkers_bc74_phase_0'),
        dict(name='A077-phase1-busy-only',call_pc=0xA077,selector=0x39,target=0xA01E,target_pair=[25,26],body=0xC5B9,body_rts=0xC5BE,continuation=0xA07C,phase=1,
             owner='SceneCoordinator -> CityPanelServices.panel_helper_c435 -> panel_helper_c5b9 (007E != 0)')]
 for s in sites:
  assert any((r['bank'],r['pc'])==(27,s['call_pc'])for r in calls)
  assert int.from_bytes(rom[off(27,s['call_pc']+3):off(27,s['call_pc']+3)+2],'little')==s['target']
  assert rom[off(27,s['continuation'])]==0x60
 save('family-scope.json',dict(schema='wp03-EE07-return-family-v1',ROM_SHA256=ROM_SHA,sites=sites,
  actual_boundary='Start before the actual 27:A06F/A077 JSR; stop after real EE52 RTS, before A074/A07C first opcode. No outer RTS.',
  bounded_dependency='DEP-EE07-A06F-A077-REAL-CALLEE-RETURN',selected_typed_ids=[iid(31,p)for p in(0xEE1F,0xEE25)],
  entry_origin='Explicit controlled literals; no exact natural A06F/A077 context found. Prior phase13 positions and phase28 different EE07 caller are supporting history only.',
  requirements=['actual current JSR frame and five-byte far frame','real named callee body and RTS to EE4D','F237 raw writes and physical masks','real EE52 RTS to ordinary continuation',
                'full independent Source/CPU RAM/SRAM/REG/PRG/port parity with both output buffers saved','missing callee and fake-return must retain same pending call, then genuine resume once'],
  premises=['No interrupts or external writes in each positive window','D=0','E2 raw selector maps to physical27/28 and E3=E2+1','007E is nonzero for the secondary busy case'],
  original_fixed_bytes=rom[off(31,0xEE07):off(31,0xEE53)].hex(),known_direct_callers=155,selected_callers=2,inventory_callers_outside_this_package=153,
  global_remaining_shared_entries=None,unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
  official_city_names={str(x):None for x in(1,28,29,30,31)},whole_game_closure_proven=False,Native_new_runs=0,
  forbidden=['No Source CPU/IR fallback','No host PC/SP return','No synthetic outer frame','No global ledger migration','No claiming busy-only branch completes the other panel phases']))
 save('known-direct-caller-inventory.json',dict(count=155,callers=calls,not_selected=153,
  meaning='Only direct JSR EE07 in frozen atlas; 153 outside this package is not a count of all unresolved game services.'))
 cases=[]
 def add(group,i,sp=253,p=48,raw=59,data=17,withhold=False):
  k=len(cases);s=sites[i]
  cases.append(dict(key=f'{group}/{k:04d}',group=group,site_index=i,registers=dict(pc=s['call_pc'],a=k*13&255,x=k*17&255,y=s['selector'],p=p,sp=sp),
                    raw_E2=raw,data_bank=data,raw_E1=32|data,PPU_jobs=(1,128,255)[k%3],withhold=withhold))
 for i in range(2):
  for sp in range(256):add('all_SP_values',i,sp=sp)
  for bits in range(32):
   p=48|sum(flag for b,flag in enumerate((1,2,4,64,128))if bits>>b&1)
   add('binary_flag_axis',i,p=p)
  for raw in(27,91,123,155,187,219,251):add('raw_E2_alias_axis',i,raw=raw)
  for bank in range(32):add('data_window_axis',i,data=bank)
  add('missing_fake_then_real_resume',i,withhold=True)
 assert len(cases)==656
 save('case-matrix.json',dict(case_count=len(cases),groups=dict(collections.Counter(s['group']for s in cases)),cases=cases,
  initial_RAM_formula='(i*29+17)&255, i=0..2047',initial_SRAM_formula='(i*11+23)&255, i=0..8191',
  initial_patches='0401=site.phase; 007E=PPU_jobs; 0470..0473=A1 B2 C3 D4; E1=raw_E1; E2=raw_E2; E3=(raw_E2+1)&255',
  initial_PRG='[data_bank,27,28,31]',initial_ports='E000=raw_E1; E800=raw_E2|C0; F000=(raw_E2+1)&255. All other ports unobserved. No hardware input samples.',
  Source_entry_adapter='readable_entry.current_jsr sets predeclared entry boundary once and uses existing CityUIController._external plus SceneCoordinator; callee run_entry(seed_return=False).',
  independence='Finite axes, not full Cartesian or natural campaign coverage. No host state modification after execution starts, including missing/fake/resume steps.'))
 raw=read(ROOT/'analysis/wp03-shared-entry-family/raw345-executability-ledger.json')['windows'];relations=[]
 for s,idx,consumer in zip(sites,(249,250),((29,0xBCBF),(26,0xC443))):
  w=raw[idx];assert(w['physical_bank'],w['rom_offset'])==(27,off(27,s['call_pc']+3))
  relations.append(dict(raw_id=f'W:{ROM_SHA}:b27:off{w["bank_offset"]:04X}:rom{w["rom_offset"]:06X}',raw_locator=f'/windows/{idx}',raw_hex=w['raw_hex'],
   typed_data_consumers=[iid(31,0xEE1F),iid(31,0xEE25)],data_addresses=[s['call_pc']+3,s['call_pc']+4],
   continuation_id=iid(27,s['continuation']),continuation_opcode_executed=False,
   downstream_typed_id=iid(*consumer),downstream_typed_access_executed=False,
   classification_migration=False,shared_semantic_root=None,role='Mixed window: two inline destination bytes consumed as data; third byte is original RTS, reached before opcode execution.'))
 save('cross-ledger-relations.json',dict(relations=relations,field_classification_changes=0,raw_classification_changes=0,
  counts=dict(total=1526,conditional_disjoint=1203,possible=80,unknown=243,remaining=323,raw_total=345,raw_operand=104,raw_data=13,raw_unproved_entry=228)))
 pins={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source/recovered').glob('*.py'))}
 pins.update({str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'scripts').glob('*wp03_ee07*.py'))})
 pins['analysis/wp03-ee07-return-family/readable_entry.py']=sha(OUT/'readable_entry.py')
 save('acceptance.json',dict(schema='wp03-EE07-locked-acceptance-v1',scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),
  cross_ledger_sha256=sha(OUT/'cross-ledger-relations.json'),implementation_pins=pins,expected_cases=656,
  expected_stateful_full_returns=328,expected_busy_full_returns=328,expected_strict_withhold_parents=2,expected_fake_zero_progress_checks=2,
  expected_native_runs=0,expected_outer_RTS_executions=0,Source_CPU_executions_before_this_lock=0,
  failure_policy='Stop at a real missing boundary; preserve failed receipt. No expanding service family or rewriting scope after execution.'))
 print(json.dumps(dict(status='locked_before_execution',cases=656,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'))))
if __name__=='__main__':main()
