#!/usr/bin/env python3
"""Prelock ancestry, current original caller, finite inputs and device bounds."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp07-palette-packet-consumer';PREV=ROOT/'analysis/wp03-ee07-phase1-producer'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 assert read(OUT/'frozen-before.json')['status']=='passed'
 seed=json.loads((PREV/'run-01/cases.jsonl').open().readline());assert seed['key']=='ancestor-controlled-16-producer-sequence/step-01'
 raw=(PREV/'run-01/CPU-final-memory.bin').read_bytes()[:10240];assert raw==(PREV/'run-01/Source-final-memory.bin').read_bytes()[:10240]
 assert hashlib.sha256(raw).hexdigest()=='28c408c54d3228dc2c3ab0e5a8a417f06deae0b6b34da01db6aa2a602bf27e0a'
 assert raw[0x7D:0x7F]==bytes((0x3A,5))and raw[0x470:0x474]==bytes.fromhex('40884024')
 (OUT/'ancestor-memory.bin').write_bytes(raw)
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();romsha=hashlib.sha256(rom).hexdigest();assert romsha=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 atlas=read(ROOT/'analysis/phase18/control/instruction-atlas.json');calls=[r for r in atlas['instructions']if r['op']=='JSR'and r.get('operand')==0xEE53];assert len(calls)==7
 assert rom[16+31*8192+(0xF8B5&8191):16+31*8192+(0xF8B5&8191)+3]==bytes.fromhex('2053ee')
 full=read(PREV/'all-indirect-accesses.json')['accesses'];typed=[]
 for i,pc in zip(range(1405,1409),(0xA132,0xA13A,0xA140,0xA146)):
  row=full[i];assert(row['physical_bank'],row['cpu'])==(29,pc);typed.append(dict(id=f'I:{romsha}:b29:cpu{pc:04X}:rom{row["rom_offset"]:06X}',locator=f'/accesses/{i}',prior_classification=row['classification']))
 save('family-scope.json',dict(schema='WP07-palette-packet-software-device-contract-v1',ROM_SHA256=romsha,
  ancestry=dict(case=seed['key'],state=seed['Source']['final'],offset=0,bytes=10240,memory_sha256=hashlib.sha256(raw).hexdigest(),
   CPU_file=rec(PREV/'run-01/CPU-final-memory.bin'),Source_file=rec(PREV/'run-01/Source-final-memory.bin'),PPU_state_in_old_capture=False),
  original_call=dict(bank=31,PC=0xF8B5,target=0xEE53,raw_return_word=0xF8B7,return_bank=31,return_PC=0xF8B8,raw_hex='20 53 EE'),known_direct_callers=calls,
  controlled_entry='Per call only PC is changed: seed A074->F8B5 then prior returnF8B8->F8B5. Other REG/SP/RAM/PRG/ports inherited. No host pushes or synthetic outer frame. No NMI hardware entry.',
  Source_entry='consumer_adapter.current_call reuses BattleNMIServices.call(F8B5,EE53); SceneCoordinator owns tail29:A006 via exact TextSceneServices; program adds no RTS.',
  palette_path='7D3A ->EE56/EE72 ->E70E;E713 control;E716 status;E71B clears7D;32 palette data writes;E748 RTS ->F8B8. 7E05 unchanged.',
  packet_path='Second actual JSR;7D0/7E05 ->EEBE/EEC3 true clearbit2 ->F2373D ->EECB tailA006/A11B ->A12D status ->2400/64data/FF ->A152 RTS consuming same F8B7 ->F8B8.',
  final_mapping='[16,29,30,31],rawE1/E2/E3=30/3D/3E; retain7E01. No EE07 restore in this consumer.',
  palette_stack_alias='SP00 actual JSR writes0100=F8,01FF=B7; palette expectation comes from live post-JSR0100..011F, not frozen ancestorA0.',
  status_polling=False,status_bit_values_control_readiness=False,device_contract=rec(OUT/'consumer_adapter.py'),
  packet_typed_accesses=typed,typed_classification_changes=0,raw_classification_changes=0,
  official_city_names={str(x):None for x in(1,28,29,30,31)},counts=dict(total=1526,conditional=1203,possible=80,unknown=243,remaining=323,raw345=345,raw104=104,raw13=13,raw228=228),
  known_EE07=155,covered_EE07_combined=2,EE07_outside_packages=153,global_remaining_services=None,
  scope_limit='Two calls and their declared missing-input resumes only. No next F206/FB0B/NMI/IRQ/main iteration, Native, rendering or oldouter return.'))
 fixture=dict(PPU_bytes_formula='(i*17+11)&255, i=0..16383',ppu_scroll=[17,93],initial_control=4,initial_increment=32,
  declared_raw_sink=True,internal_vblank_generation=False,status_read_clear_vblank_modeled=False,open_bus=False,palette_or_nametable_mirroring=False,
  nametable_chr_banking=False,palette_6bit_mask=False,NMI_edges=False,cycle_timing=False,rendering=False,
  supported='Use existing ServiceMemory only: finitecaller2002 deque;successful read resetsppu_latch/scroll_latch;2000 controlsincrement1/32;2006 high/low14bit;2007 storesraw byte and advancesmod4000.',
  status_contract='Samples are caller-authorized software-device inputs at exact PC+ordinal, not Native capture, vblank completion or hardware-ready grants. No repeat_read_ports/autofill.',
  missing_policy='Source stops in existing ServiceWait;CPU gates before2002 instruction with empty deque, no PC repair;repeat without input must make zero emulated-state/IO progress. Append planned samples only, then same owner/generator resumes.')
 save('device-contract.json',fixture)
 cases=[]
 for key,values,available,latch,address in(
  ('zero_samples',[0,0],2,0,0),('mixed_status_nonzero_latch',[0x80,0x40],2,1,0x2ABD),
  ('other_status_bits',[0xFF,0x80],2,1,0x3FFF),('missing_first_then_resume',[0x80,0],0,1,0x2ABD),
  ('exhausted_second_then_resume',[0x40,0xFF],1,1,0x3FFF)):
  cases.append(dict(key=key,status_plan=[dict(ordinal=i+1,PC=pc,value=value,availability_time='Explicit finite input before read; missing-case replenishment after one zero-progress retry')for i,(pc,value)in enumerate(zip((0xE716,0xA12D),values,strict=True))],
   initial_available=available,refill_remaining_after_one_retry=True,ppu_latch=latch,ppu_scroll_latch=latch,ppu_address=address))
 save('case-matrix.json',dict(parent_cases=5,actual_JSR_calls=10,cases=cases,CPU_instruction_budget_per_call=2000,
  expected_status_successes=10,distinct_missing_boundaries=2,expected_zero_progress_retries=2,Source_advance_segments=14,
  snapshot_domain='Full2K RAM+8K SRAM+16K rawPPU sink plus complete declared device JSON/REG/banks/IO at initial,actualcalleeentry,each pause/resume/return andpacket tail entry.',
  exclusions='No arbitrary hardware Cartesian axes, no PPU consumer status polling, no hostclear7D/7E, no CPU oracle as Source fallback.'))
 pins={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source/recovered').glob('*.py'))}
 pins.update({str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'scripts').glob('*wp07_palette_packet*.py'))});pins[str((OUT/'consumer_adapter.py').relative_to(ROOT))]=sha(OUT/'consumer_adapter.py')
 save('acceptance.json',dict(schema='WP07-palette-packet-prelocked-acceptance-v1',scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),device_sha256=sha(OUT/'device-contract.json'),ancestor_sha256=sha(OUT/'ancestor-memory.bin'),
  implementation_pins=pins,expected_parents=5,expected_calls=10,expected_status_reads=10,expected_palette_bytes_each_side=160,expected_packet_bytes_each_side=320,
  expected_missing_boundaries=2,expected_no_progress_retries=2,expected_Source_advances=14,Native_NMI_IRQ_outerframe_credit=0,Source_CPU_Native_executions_before_lock=0,
  failure_policy='Preserve failed run and exact dependency;never edit old sources,modify planned scope afterexecution,repairPC/SP/flags or silently invent hardware inputs.'))
 print(json.dumps(dict(status='locked_before_execution',parents=5,calls=10,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'))))
if __name__=='__main__':main()
