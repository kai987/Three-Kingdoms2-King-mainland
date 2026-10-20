#!/usr/bin/env python3
"""Static-only preparation and prelock for three finite continuation plans."""
from pathlib import Path
import hashlib,json,struct,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp08-real-continuation'
NATIVE=ROOT/'analysis/wp05-natural-nonempty/runtime/natural-day31-nonempty/observer'
OLD=ROOT/'analysis/wp07-palette-packet-consumer'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 assert read(OUT/'frozen-before.json')['status']=='passed'
 meta=read(NATIVE/'callee-0122-E066.json');b=(NATIVE/'snapshots.bin').read_bytes()[meta['byte_offset']:meta['byte_offset']+meta['bytes']]
 assert hashlib.sha256(b).hexdigest()==meta['sha256']=='a92e590d49aa56de45a66f5751200fe306515a11ebc9fee9523d146042c74a9b'
 assert meta['actual_registers']==dict(a=144,x=0,y=0,p=228,sp=255,pc=0xE066)and b[0x78]==2 and b[0x7B]==0 and b[0x7D:0x7F]==bytes((1,0))and b[0x87:0x8B]==bytes((0,4,4,4))
 (OUT/'native122-software-memory.bin').write_bytes(b)
 points=[json.loads(s)for s in(OLD/'run-01/points.jsonl').read_text().splitlines()];old=points[3]
 assert old['label']=='zero_samples/call1-advance1-returned'and old['offset']==79872
 ob=(OLD/'run-01/CPU-snapshots.bin').read_bytes()[79872:79872+26624]
 assert ob==(OLD/'run-01/Source-snapshots.bin').read_bytes()[79872:79872+26624]
 assert hashlib.sha256(ob).hexdigest()=='fa808f7eec2b44045cfe3ed8e27a3fead6edd44601ce9a771549fb20fb0901cb'
 (OUT/'controlled-SP00-memory-and-raw-sink.bin').write_bytes(ob)
 save('source-provenance.json',dict(Native122=dict(metadata=rec(NATIVE/'callee-0122-E066.json'),snapshot_archive=rec(NATIVE/'snapshots.bin'),state=meta,
   exported_memory=rec(OUT/'native122-software-memory.bin'),source_grade='Actual passive Native E066 software snapshot; new controlled software NMI derives stack/scene2; instantaneous device state not captured',
   original_REG_RAM_SRAM_banks_preserved=True,pending_queue_equal_to_old64B=False),
  controlled_SP00=dict(point=old,metadata_file=rec(OLD/'run-01/points.jsonl'),archive=rec(OLD/'run-01/CPU-snapshots.bin'),exported_memory=rec(OUT/'controlled-SP00-memory-and-raw-sink.bin'),
   SP_origin='analysis/wp03-ee07-return-family/case-matrix.json case0 all_SP_values/0000 explicit SP00 axis; formula RAM/SRAM, not Native',
   initial_10K_sha256='6502352583e32fa74d2a05f992ed2a4dd7f78955bbd13f00ababb129ba547088',phase0_final_10K_sha256='31c52f5a451fdd006780a9bbcdd95f83f0b601ab0d67f2189dd254d516f38368',
   phase1_step01_10K_sha256='28c408c54d3228dc2c3ab0e5a8a417f06deae0b6b34da01db6aa2a602bf27e0a',
   prior_controlled_PC_change='A074->F8B5 only; palette call returned F8B8. This package imports that first return, not the old second PC reentry.',
   device_input_rebinding='Old unused A12D sample00 replaced by explicit FB22 sample00; all stored software/REG/banks and raw device state otherwise retained; new per-package history counters start0.'),
  source_cross_splicing=False,new_Source_CPU_Native_executions=0))
 targets=(0xF8B5,0xF8B8,0xFB22,0xEC67)
 index=[json.loads(s)for s in(NATIVE/'snapshot-index.jsonl').read_text().splitlines()];raw=(NATIVE/'bus-events.bin').read_bytes();assert len(raw)%288==0
 hits={str(t):0 for t in targets}
 for w in struct.iter_unpack('<72I',raw):
  if w[4]in targets:hits[str(w[4])]+=1
 assert len(index)==122 and len(raw)//288==265872 and not any(hits.values())
 save('finite-source-search.json',dict(search_domain='Existing WP05 sparse full snapshots and selected passive ABI events; not a whole-instruction absence proof',
  snapshot_index=rec(NATIVE/'snapshot-index.jsonl'),full_snapshots=len(index),target_full_snapshot_hits=[x for x in index if x.get('entry')in targets],
  bus=rec(NATIVE/'bus-events.bin'),ABI=rec(NATIVE/'event-schema.json'),records=len(raw)//288,opcode_field=4,target_selected_bus_hits=hits,
  WP08_run05=dict(verification=rec(ROOT/'analysis/wp08-shortest-continuity/verification.json'),validation=rec(ROOT/'analysis/wp08-shortest-continuity/run-05/validation.json'),
   source_grade='Existing software-NMI/IRQ-derived scene3; selected EC67 register checkpoints lack same-instant full software memory, not a scene2 substitute'),
  compatible_instant_F8B5_full_capture_found=False,selected_complete_source='Native122 scene2 E066; declare fresh software NMI and retain its own queue',new_execution_count=0))
 fixture=dict(kind='Existing ServiceMemory raw14bit/register sink only',fresh_Native122=dict(raw_PPU_formula='(i*17+11)&255 for 0<=i<16384',ppu_address=0x2ABD,ppu_latch=1,ppu_scroll_latch=1,ppu_scroll=[17,93],initial_control=4,initial_increment=32,
   port_E000_E800_F000='derived from complete RAM E1/E2/E3; E800 OR C0; not captured device state',N163_zero_fixture=True),
  controlled_SP00='Exact saved raw-sink/register fixture after first WP07 palette return; only finite future2002 plan rebound and new history counters reset',
  finite_reads='Exact PC/ordinal values; no repeat or autofill. Successful read consumes sample and resets latch. bit6 controls FB22 BIT/BVS.',
  supported_writes='5000/5800 raw commands, mapper/CHR/nametable selectors,2000/2001/2003/2005/2006/2007,4014 request with all256 bytes; existing ServiceMemory only',
  missing_policy='CPU stops before missing BIT; Source hardware_read wait. bit6set Source wait pairs with actual CPU BIT+BVS returningFB22. Repeated no-input resume preserves state and owner; only planned sample may be appended.',
  NMI_entry='Explicit one software interrupt primitive per Native122 case; real six-byte stack path including original prologue. No captured hardware NMI edge/timing credit.',
  not_modeled=['PPU/APU/N163 internal timing','automatic vblank or read-clearbit7','openbus','CIRAM/CHR/palette physical mirroring','6bit palette masking','DMA transfer/stall/cycles','IRQ scheduler','rendering/audio synthesis'])
 save('device-contract.json',fixture)
 rompath=Path('/Users/paulasmith/Downloads/三国志2超级版.nes');rom=rompath.read_bytes();romsha=hashlib.sha256(rom).hexdigest()
 assert romsha=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 assert rom[16+31*8192+(0xF878&8191):16+31*8192+(0xF878&8191)+3]==bytes.fromhex('6c0000')and rom[16+31*8192+8192-6:16+31*8192+8192-4]==bytes.fromhex('00f8')
 edges=[]
 for pc,target in((0xF8B5,0xEE53),(0xF8B8,0xF206),(0xF8BB,0xFB0B),(0xF8BE,0xEC67),(0xFB0B,0xEAF7)):
  b=rom[16+31*8192+(pc&8191):16+31*8192+(pc&8191)+3];assert b==bytes((32,target&255,target>>8))
  edges.append(dict(bank=31,PC=pc,target=target,raw=b.hex(),expected_return_PC=pc+3))
 save('family-scope.json',dict(schema='WP08-real-scene2-continuation-v1',ROM_SHA256=romsha,original_calls=edges,
  branch='FB22 BIT2002;FB25 BVS FB22; bit6 clear including value80 exits; EC67 existing palette_fade; stop beforeF8C1 or exactnonlocal',
  strict_caller_policy='Source actual PC must equal each declared callsite. Preserve actual RTS destination and SP. Never repair PC/SP/flags or seed next call after nonlocal return.',
  Source_control_glue='Scene2 only: original F878 JMP($0000) semantic assignment after nmi_body computes pointer. Existing chr_banks/nametable_banks/scroll_control/palette_fade reused unchanged.',
  permitted_software_NMI_entries=2,planned_Native_runs=0,CPU_instruction_budget_per_case=4096,
  official_city_names={str(i):None for i in(1,28,29,30,31)},counts=dict(total=1526,conditional=1203,possible=80,unknown=243,remaining=323),raw_counts=dict(total=345,operand=104,data=13,unproved=228),
  known_EE07_callers=155,covered_EE07_combined=2,EE07_outside_packages=153,unknown_global_services=None,
  remaining_route_premises=['Same old64B pendingqueue with compatible actual/derived incoming NMI scene2 context','Caller/scene/NMI continuation beyondF8C1 through actual next consumer','Captured compatible device state and timing replacing raw fixture'],
  limits='Not same64B queue bridge, old reentry replacement, fullNMI/RTI/main/campaign, city meaning migration, physical hardware timing or natural execution proof. Stop after sealed package.'))
 cases=[]
 for key,origin,plan,available,stop in(
  ('native122-clear80','Native122',[(0xF805,0),(0xE716,0),(0xFB22,0x80)],3,0xF8C1),
  ('native122-bit6-wait-missing-resume','Native122',[(0xF805,0x80),(0xE716,0x40),(0xFB22,0x40),(0xFB22,0x80)],3,0xF8C1),
  ('controlled-SP00-nonlocal','controlled_SP00',[(0xFB22,0)],1,0x0FC1)):
  cases.append(dict(key=key,origin=origin,status_plan=[dict(ordinal=i+1,PC=p,value=v)for i,(p,v)in enumerate(plan)],initial_available=available,expected_stop_PC=stop,
   software_NMI_entry=origin=='Native122',expected_call_count=5 if origin=='Native122'else 4,expected_nonlocal=origin!='Native122'))
 save('case-matrix.json',dict(cases=cases,parents=3,actual_JSR_RTS_pairs=14,normal_RTS_returns=13,expected_nonlocal_RTS=1,software_NMI_entries=2,
  status_successes=8,bit6_waits=1,missing_gates=2,strict_same_position_missing_retry=1,zero_emulated_state_missing_resumes=2,Source_advances=6,
  snapshot_bytes=26624,CPU_budget_per_case=4096,finite_only=True))
 pins={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source/recovered').glob('*.py'))}
 pins.update({str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'scripts').glob('*wp08_real_continuation*.py'))});pins[str((OUT/'continuation_adapter.py').relative_to(ROOT))]=sha(OUT/'continuation_adapter.py')
 save('acceptance.json',dict(schema='WP08-real-continuation-prelocked-v1',inputs={n:sha(OUT/n)for n in('family-scope.json','case-matrix.json','device-contract.json','source-provenance.json','finite-source-search.json','native122-software-memory.bin','controlled-SP00-memory-and-raw-sink.bin')},
  implementation_pins=pins,Source_CPU_Native_executions_before_lock=0,source_algorithms_unchanged=True,host_PC_SP_flags_repairs=0,
  failure_policy='Preserve failed output and exact stop; never silently repair state or mutate locked plans/pins. No broad extra search.'))
 print(json.dumps(dict(status='locked_before_execution',parents=3,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'))))
if __name__=='__main__':main()
