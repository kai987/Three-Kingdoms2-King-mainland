#!/usr/bin/env python3
"""Static scope, ancestry, finite branch matrix and pre-execution acceptance."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-ee07-phase1-producer';OLD=ROOT/'analysis/wp03-ee07-return-family'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size)
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def iid(b,p):return f'I:{ROM_SHA}:b{b:02d}:cpu{p:04X}:rom{16+b*8192+(p&8191):06X}'
def main():
 assert read(OUT/'frozen-before.json')['status']=='passed'
 row=json.loads((OLD/'run-01/cases.jsonl').open().readline());assert row['case']=='all_SP_values/0000'
 raw=(OLD/'run-01/CPU-final-memory.bin').read_bytes()[:10240];assert raw==(OLD/'run-01/Source-final-memory.bin').read_bytes()[:10240]
 assert hashlib.sha256(raw).hexdigest()=='31c52f5a451fdd006780a9bbcdd95f83f0b601ab0d67f2189dd254d516f38368'
 assert row['Source']['final']['registers']==dict(pc=0xA074,a=0x3B,x=0,y=0x3B,p=0x30,sp=0)
 assert raw[0x7D]==0x3A and raw[0x7E]==1 and raw[0x401]==1 and raw[0x470:0x474]==bytes.fromhex('00880024')
 (OUT/'ancestor-memory.bin').write_bytes(raw)
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 atlas=read(ROOT/'analysis/phase18/control/instruction-atlas.json')
 body=[x for x in atlas['instructions']if(x['physical_bank']==29 and 0xBC9B<=x['cpu']<=0xBD02)or(x['physical_bank']==31 and 0xECEE<=x['cpu']<=0xED18)]
 for x in body:
  start=16+x['physical_bank']*8192+(x['cpu']&8191);assert rom[start:start+len(bytes.fromhex(x['raw_hex']))]==bytes.fromhex(x['raw_hex'])
 selected=read(OLD/'all-indirect-accesses.json')['accesses'][1474];remaining=read(OLD/'remaining-accesses.json')['accesses'][282]
 assert selected==remaining and(selected['physical_bank'],selected['cpu'])==(29,0xBCBF)
 save('family-scope.json',dict(schema='wp03-EE07-phase1-producer-v1',ROM_SHA256=ROM_SHA,
  ancestor=dict(case=row['case'],state=row['Source']['final'],memory_sha256=hashlib.sha256(raw).hexdigest(),CPU_file=rec(OLD/'run-01/CPU-final-memory.bin'),Source_file=rec(OLD/'run-01/Source-final-memory.bin'),offset=0,bytes=10240),
  family='27:A06F JSR EE07 ->29:A039 ->BC71/BC74 phase1 ->BC9B..BD02 ->EE4D/F237/EE52 ->A074 preopcode',
  site=dict(call_pc=0xA06F,selector=0x3D,target=0xA039,target_pair=[29,30],body=0xBC9B,body_rts=0xBD02,continuation=0xA074,phase=1),
  Source_owner='SceneCoordinator -> GlobalUIController.city_workers -> CityUIWorkers.cityuiworkers_bc74_phase_1',
  semantic_edges=['F25F Y30 sets raw E1=30 / physical data bank16','header0380..382 =40,destination high,low',
    '64 actual BCBF reads interleaved with BCC1 writes to0383..03C2','BCCB writes FF at03C3 after exactly64 payload bytes',
    'independent full16bit source/destination +0040','updated destination high==28 advances0401 and real ECEE returns',
    'BCFF unconditionally ORs007E bit2','BD02 RTS consumes actual EE4C; EE52 restores codepair only, preserving E1/data side effect'],
  busy_ready='No producer busy/ready guard. 007E=0,1,4 are controlled flag inputs; no readiness/PPU acknowledgement is inferred.',
  constant_007D=dict(value=0x3A,origin='Inherited old deterministic fixture, zero writes in ancestor phase0; no Native or PPU ack credit',must_not_mutate=True),
  ECEE=dict(advance_condition='((old_destination+0x40)&0xFFFF)>>8 ==0x28, not whole word==2800',effects='87=1,88=0,89=4; copy live0100..011F to0120..013F; no write7D/8A; synchronous ED18 RTS'),
  stack_premise='All cases inherit SP00: live stack cells0100,01FF..01FA do not intersect ECEE backup0120..013F. No arbitrary-SP claim; SP20..45 overlap excluded.',
  reentry='Only PC A074->A06F and Y3B->3D per invocation, disclosed before execution; branch cases additionally patch locked RAM fields before their first entry. No natural temporal continuity or real outer frame claimed.',
  termination='Producer and real return only; no PPU consumer, interrupts, hardware reads or Native runs.',
  selected_typed_id=iid(29,0xBCBF),selected_full_locator='/accesses/1474',selected_remaining_locator='/accesses/282',selected_prior_record=selected,
  inline_data_typed_ids=[iid(31,0xEE1F),iid(31,0xEE25)],raw_inline_window='W:'+ROM_SHA+':b27:off0072:rom036082',
  body_original_instructions=body,known_EE07_callers=155,previous_package_callers=2,new_callers=0,inventory_callers_outside_combined_packages=153,
  field_counts=dict(total=1526,conditional=1203,possible=80,unknown=243,remaining=323),raw_counts=dict(total=345,operand=104,data=13,unproved=228),
  official_city_names={str(x):None for x in(1,28,29,30,31)},global_remaining_services=None,completion_percentage=None,whole_game_closure_proven=False))
 cases=[dict(key='ancestor-controlled-16-producer-sequence',steps=16,patches={},basis='Same independent Source and CPU bus per parent;16 controlled PC/Y reentries, no consumer. Last packet advances phase1->2.')]
 for key,patches in(
  ('zero_request_is_not_a_ready_guard',{0x7E:0}),('existing_bit2_is_not_a_busy_guard',{0x7E:4}),
  ('source_page_carry',{0x470:0xF0}),('destination_page_carry',{0x472:0xF0}),
  ('terminal_exact_2800',{0x472:0xC0,0x473:0x27}),('terminal_nonzero_low_2810',{0x472:0xD0,0x473:0x27}),
  ('already_high28_still_advances',{0x472:0xBF,0x473:0x28}),('leave_high28_no_advance',{0x472:0xC0,0x473:0x28}),
  ('source_crosses_PRG_slot',{0x470:0xF0,0x471:0x9F})):
  cases.append(dict(key=key,steps=1,patches={str(k):v for k,v in patches.items()},basis='Independent controlled branch case from the same frozen ancestor; all other bytes inherited.'))
 assert len(cases)==10 and sum(x['steps']for x in cases)==25
 save('case-matrix.json',dict(parent_count=10,producer_invocations=25,cases=cases,Source_CPU_pairing='Independent execution with identical immutable ancestor and declared patches/reentry; full2K8K/REG/PRG/rawports at actual boundaries, plus64-byte actual per-side access sequence.',
  deliberate_exclusions=['No mechanical re-test of all old SP/P/data-page axes','No consumer or Native','No unsafe palette stack aliases','No host PC/SP repair after a call starts']))
 save('device-contract-boundary.json',dict(status='producer_only_no_consumer_execution',palette_priority_flag=0x3A,
  actual_consumer_owner='TextSceneServices A006/A11B; fixed EE53 services palette first while007D nonzero',
  minimal_WP07_contract=['Explicit entry/caller stack and scheduling: EE53 sees007D3A and must choose palette first',
    'Explicit PPUSTATUS2002 read samples at actual requested positions and timing','Observe actual2000/2006/2007 writes; keep007D/7E software changes genuine',
    'Only after real palette scheduling permits bit2 consumer may packet upload be claimed'],
  known_algorithm_missing=False,new_unknown_service_count=0,Source_CPU_Native_executions=0,consumer_or_full_WP08_closed=False))
 pins={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source/recovered').glob('*.py'))}
 pins.update({str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'scripts').glob('*wp03_ee07_phase1*.py'))})
 for p in(ROOT/'scripts/verify_wp03_ee07_family.py',OLD/'readable_entry.py'):pins[str(p.relative_to(ROOT))]=sha(p)
 save('acceptance.json',dict(schema='wp03-phase1-locked-acceptance-v1',scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),device_boundary_sha256=sha(OUT/'device-contract-boundary.json'),
  ancestor_sha256=sha(OUT/'ancestor-memory.bin'),implementation_pins=pins,expected_parents=10,expected_invocations=25,expected_ECEE=4,
  expected_each_payload_reads=64,expected_each_payload_writes=64,expected_each_terminators=1,expected_real_return_count=25,
  expected_consumer_Native_outer_RTS=0,Source_CPU_Native_executions_before_lock=0,
  failure_policy='Preserve first failed run, strict actual missing boundary. Never fake return or modify scope after execution.'))
 print(json.dumps(dict(status='locked_before_execution',parents=10,producer_invocations=25,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'))))
if __name__=='__main__':main()
