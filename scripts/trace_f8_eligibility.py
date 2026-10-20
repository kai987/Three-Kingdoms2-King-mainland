#!/usr/bin/env python3
"""Explain F8 selection from actual saved Nestopia REG/MAP/N163 contexts.

Only the oracle executes original6502 bytes. Captured PC, RNG/request/caller
stack and actual PRG mapping are never replaced. Explicit hardware reads and
absence of newly scheduled interrupts bound this software continuation; it is
not a Native internal instruction trace. Optional numeric preparations are
reported individually and must precede execution.
"""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.nestopia_context import NestopiaContext
ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase20/cpu'
REGS=('a','x','y','p','sp','pc')
WATCH={
 0xA043:'weight_initialization',0xA073:'roster_pressure_scan_return',
 0xA099:'roster_pressure_percent',0xA0CF:'final_strategy_weights',
 0xA19C:'three_way_strategy_selection',0xA1AC:'strategy_random_return',
 0xA1BC:'strategy_index',0xB49C:'assignment_sample_call',
 0xB49F:'assignment_sample_return',0xB4A9:'secondary_selected',
 0xB5FC:'secondary_sample_call',0xB5FF:'secondary_sample_return',
 0xB619:'alliance_body_enter',0xB629:'messenger_selection_return',
 0xB652:'active_ruler_count_gate',0xB65F:'own_diplomacy_pointer',
 0xB678:'diplomacy_zero_gate_passed',0xB67B:'foreign_neighbor_count',
 0xB6B8:'own_city_count_return',0xB6C0:'strict_city_gap_branch',
 0xB6C5:'quote_start',0xB70E:'currency_random_return',
 0xB749:'affordability_return',0xB75A:'target_controller_branch',
 0xB75C:'target_controller3_local_resolution',0xB788:'F8_store',
 0xB78B:'F8_reply_wait',0xB98B:'secondary_recruitment_selected',
 0xBBB2:'secondary_loyalty_selected',0xBEC7:'development_tail',
}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def regs(cpu):return {k:getattr(cpu,k)for k in REGS}
def field(m):
 return dict(ruler=m[0x6F03],phase=m[0x6F5B],budget=m[0x6F5D],request=m[0x6F8B],
  weights=list(m[0x6F5F:0x6F62]),rng_cursors={f'{a:02X}':m[a]for a in(0x50,0x52,0x54,0x55)},
  scratch={f'{a:02X}':m[a]for a in range(0x20,0x46)},quote=m[0x42F]|m[0x430]<<8)
def campaign(m):
 rulers=[]
 for r in range(7):
  base=0x6F07+8*r;cities=[]
  for city in range(30):
   b=0x6000+32*city
   if m[b]&7==r:cities.append(dict(city=city,gold=m[b+2]|m[b+3]<<8,grain=m[b+4]|m[b+5]<<8,roster=list(m[b+17:b+27])))
  rulers.append(dict(ruler=r,leader=m[base],controller=m[base+3],diplomacy=list(m[base+4:base+8]),cities=cities))
 return rulers
def selection_summary(events):
 """Classify only actually visited gates; do not infer an unvisited body."""
 strategy=[e for e in events if e['pc']==0xA1BC]
 assignment=[e for e in events if e['pc']==0xB49F and e['registers']['a']&127<50]
 secondary=[e for e in events if e['pc']==0xB5FF and e['registers']['a']&127<90]
 if strategy and strategy[-1]['registers']['a']!=1:
  return dict(first_non_F8_branch='A1BC_nonassignment_strategy',index=strategy[-1]['registers']['a'])
 if assignment and assignment[-1]['registers']['a']&127>=10:
  return dict(first_non_F8_branch='B4A7_primary_assignment',accepted_raw=assignment[-1]['registers']['a'],masked=assignment[-1]['registers']['a']&127)
 if secondary and secondary[-1]['registers']['a']&127<60:
  return dict(first_non_F8_branch='B5FC_nonalliance_secondary',accepted_raw=secondary[-1]['registers']['a'],masked=secondary[-1]['registers']['a']&127)
 if any(e['pc']==0xB619 for e in events):return dict(alliance_body_actually_entered=True)
 return dict(first_non_F8_branch=None,reason='No deciding selection boundary was visited within this prefix')
def raw_catalog(rom,directory):
 ranges=((10,0xA19C,0xA1C5,'three_way_choice'),(10,0xB49C,0xB4AC,'primary_or_secondary'),
  (10,0xB5FC,0xB619,'secondary_choice'),(10,0xB619,0xB7A2,'alliance_gates_quote_request_wait'),
  (31,0xE88A,0xE8BA,'three_domestic_random_cursors'),(31,0xE8BA,0xE9BA,'random_literal_table'),
  (31,0xF8A1,0xF8B5,'full_NMI_cursor_advance'))
 catalog=[];lines=['; Phase20 original ROM bytes; offsets include 16-byte iNES header.']
 for bank,start,end,label in ranges:
  offset=16+bank*8192+(start&8191);raw=rom[offset:offset+end-start]
  catalog.append(dict(label=label,physical_bank=bank,CPU_start=start,CPU_end_exclusive=end,ROM_offset=offset,length=len(raw),bytes=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
  lines.append(f'\n; {label} physical{bank} ${start:04X}..${end-1:04X}')
  mem=[0]*65536;mem[start:end]=raw;dis=Disassembler(MPU(memory=mem));pc=start
  while pc<end:
   if label=='random_literal_table':
    count=min(16,end-pc);text='.byte '+','.join(f'${v:02X}'for v in mem[pc:pc+count])
   elif bank==10 and 0xA1BF<=pc<0xA1C5:
    count=2;text=f'.word ${mem[pc]|mem[pc+1]<<8:04X} ; inline D494 selector word'
   else:count,text=dis.instruction_at(pc)
   assert pc+count<=end
   lines.append(f'{16+bank*8192+(pc&8191):06X} b{bank:02}:${pc:04X} {bytes(mem[pc:pc+count]).hex(" "):<48} {text}')
   pc+=count
 directory.mkdir(parents=True,exist_ok=True)
 (directory/'original-f8-selection.asm').write_text('\n'.join(lines)+'\n')
 (directory/'original-ranges.json').write_text(json.dumps(dict(rom_sha256=ROM_SHA256,ranges=catalog),indent=2)+'\n')
def finalize(directory):
 """Pin diagnostics without recounting overlapping prefixes/callee exports."""
 names=('eligibility.json','pre-F8-native-parity.json','actual-callers.json')
 records=[json.loads((directory/name).read_text())for name in names]
 pins={str((directory/name).relative_to(ROOT)):sha(directory/name)for name in names}
 dependencies={}
 for record in records:
  assert record['status']=='passed'and record['source_comparison_cases']==0
  for name,digest in record['source_sha256'].items():assert sha(ROOT/name)==digest,(name,'Stale diagnostic source pin')
  for name,digest in record['artifact_sha256'].items():assert sha(ROOT/name)==digest,(name,'Stale diagnostic artifact pin')
  dependencies.update(record['source_sha256']);pins.update(record['artifact_sha256'])
 rows=records[0]['rows'];parity=records[1]['rows'];callers=records[2]['rows'][0]['captured_callee_inputs']
 assert len(rows)==6 and len(parity)==4 and len(callers)==8
 assert sum(x['stop']=='genuine_software_request_boundary'for x in rows)==4
 assert sum(x['original_wait_cycle_entire_machine_unchanged']is True for x in rows)==1
 assert all(x['later_Native_frame_parity']['SRAM_difference_count']==0 for x in parity)
 pins[str((directory/'README.md').relative_to(ROOT))]=sha(directory/'README.md')
 receipt=dict(schema='phase20-F8-real-context-gate-evidence-v1',status='passed',ROM_sha256=ROM_SHA256,
  source_comparison_cases=0,distinct_original_CPU_diagnostic_contexts=6,
  original_CPU_diagnostic_instructions=sum(x['original_instructions']for x in rows),F8_generated_prefixes=4,
  original_unchanged_F8_wait_cycles=1,independent_no_new_NMI_request_FF_prefixes=1,
  reused_prefix_Native_SRAM_parity_observations=4,SRAM_comparison_bytes=8192,
  parity_RAM_difference_counts=[x['later_Native_frame_parity']['RAM_difference_count']for x in parity],
  existing_real_callee_input_count=len(callers),callee_directories=callers,
  artifact_sha256=pins,source_sha256=dependencies,
  Native_internal_CPU_trace=False,new_NMI_IRQ_arrivals=0,PC_RNG_request_ready_or_caller_frame_injections=0,
  limits=['Six independent originalCPU diagnostics are not six readable-source comparisons.','The four Native SRAM observations and eight exported callees overlap those same prefixes and must not be added again.','Full8192SRAM parity does not imply identical Native RAM/registers/timing; all differences remain in the parity receipt.','Formal full-core acceptance/rejection and repeats are owned by the separate runtime evidence.'])
 (directory/'evidence.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
def trace(rom,path,budget=300000,preparations=(),capture_callers=None):
 path=Path(path).resolve()
 native=NestopiaContext.parse(path.read_bytes())
 hardware=dict(read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=(0,0))
 m=native.service_memory(rom,**hardware);prepared=[]
 # Only an explicit caller supplied numeric whitelist can prepare a context.
 for address,value,label in preparations:
  old=m[address];m[address]=value;prepared.append(dict(address=address,before=old,after=value,label=label))
 c=MPU(memory=m)
 for k,v in native.registers.items():setattr(c,k,v)
 initial=field(m);events=[];rng=[];visited=Counter();stop=None;captured=[]
 initial_machine=(bytes(m.ram),bytes(m.sram),bytes(m.n163_ram),tuple(m.banks),m.n163_address,m.n163_autoincrement,regs(c))
 request_initial=m[0x6F8B]
 for n in range(budget):
  bank=m.banks[(c.pc-0x8000)//8192]if c.pc>=0x8000 else None
  visited[bank,c.pc]+=1
  capture_entry=(bank==10 and c.pc in(0xB619,0xB7A2,0xB837,0xB85F,0xB898,0xB955))or(bank==11 and c.pc in(0xD080,0xD307))
  if capture_callers is not None and capture_entry:
   folder=Path(capture_callers)/f'entry-{c.pc:04X}'
   folder_name=str(folder.relative_to(ROOT))
   if folder_name not in captured and folder.exists():
    old=json.loads((folder/'context.json').read_text())
    assert old['original_Native_state_sha256']==sha(path)and old['registers']==regs(c),'Use a fresh caller output for another input'
    assert (folder/'input-ram.bin').read_bytes()==bytes(m.ram)and(folder/'input-sram.bin').read_bytes()==bytes(m.sram)and(folder/'input-n163.bin').read_bytes()==bytes(m.n163_ram),'Existing caller bytes differ'
    captured.append(folder_name)
   if folder_name not in captured:
    folder.mkdir(parents=True);(folder/'input-ram.bin').write_bytes(m.ram);(folder/'input-sram.bin').write_bytes(m.sram);(folder/'input-n163.bin').write_bytes(m.n163_ram)
    metadata=dict(schema='phase20-original-CPU-from-formal-Native-real-callee-v1',Native_internal_CPU_trace=False,
     original_Native_state=str(path.relative_to(ROOT)),original_Native_state_sha256=sha(path),native_captured_registers=native.registers,
     original_CPU_prefix_instructions=n,registers=regs(c),physical_banks=list(m.banks),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
     existing_return_PC=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535,
     synthetic_caller_or_PC_or_RNG_or_request_preparation=False,new_NMI_IRQ_arrivals=0,prepared_numeric_bytes=prepared)
    (folder/'context.json').write_text(json.dumps(metadata,indent=2)+'\n');captured.append(folder_name)
  if bank==10 and c.pc in WATCH:
   events.append(dict(step=n,physical_bank=bank,pc=c.pc,label=WATCH[c.pc],registers=regs(c),fields=field(m),ROM_offset=16+bank*8192+(c.pc&8191)))
  if m[0x6F8B]in(248,249,250,251,252)and request_initial not in(248,249,250,251,252):stop='genuine_software_request_boundary';break
  if n and request_initial in(248,249,250)and m[0x6F8B]==request_initial and c.pc==native.registers['pc']and c.sp==native.registers['sp']:
   stop='original_request_wait_cycle_observed';break
  if m[0x6F8B]==255 and request_initial!=255:stop='original_request_FF';break
  if c.pc==0xFB28:stop='hardware_interrupt_wait';break
  if c.pc<0x8000:stop='non_ROM_PC_boundary';break
  pc=c.pc;cursor={a:m[a]for a in(0x50,0x52,0x54,0x55)}
  try:c.step()
  except Exception as e:stop='explicit_hardware_or_execution_boundary: '+str(e);break
  for a,old in cursor.items():
   if m[a]!=old:rng.append(dict(step=n,writer_pc=pc,cursor_address=a,before=old,after=m[a]))
 else:stop='instruction_budget'
 wait_unchanged=None
 if stop=='original_request_wait_cycle_observed':
  wait_unchanged=initial_machine==(bytes(m.ram),bytes(m.sram),bytes(m.n163_ram),tuple(m.banks),m.n163_address,m.n163_autoincrement,regs(c))
  assert wait_unchanged and not m.io_reads and not m.io_writes
 return dict(native_state=str(path.relative_to(ROOT)),native_sha256=sha(path),native_registers=native.registers,
  actual_PRG_banks=list(native.prg_banks),bank_shadows=list(native.ram[0xDE:0xE1])+[31],
  prepared_numeric_bytes=prepared,initial=initial,campaign=campaign(native.service_memory(rom,**hardware)),
  events=events,selection_summary=selection_summary(events),captured_callee_inputs=captured,rng_writes=rng,stop=stop,original_instructions=n,final_registers=regs(c),final=field(m),
  original_wait_cycle_entire_machine_unchanged=wait_unchanged,visited_instruction_count=len(visited),Native_internal_CPU_trace=False,new_NMI_IRQ_arrivals=0),m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--state',type=Path,action='append');p.add_argument('--instruction-budget',type=int,default=300000);p.add_argument('--out',type=Path,default=OUT/'eligibility.json');p.add_argument('--scan-resources',action='store_true');p.add_argument('--require-F8',action='store_true');p.add_argument('--compare-post-state',type=Path);p.add_argument('--capture-callers',type=Path);p.add_argument('--finalize',action='store_true');a=p.parse_args()
 a.out=a.out.resolve()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 paths=a.state or sorted((ROOT/'analysis/phase19/runtime/natural-expansion-monthly-secondary-window').glob('AI-ruler4-status00-*.state'))
 rows=[];input_pins={}
 if a.compare_post_state:assert not a.scan_resources,'Postframe parity applies only to unprepared prefixes'
 for path in paths:
  row,m=trace(rom,path,a.instruction_budget,capture_callers=a.capture_callers.resolve()if a.capture_callers else None);rows.append(row)
  input_pins[str(Path(path).resolve().relative_to(ROOT))]=sha(path)
  if a.compare_post_state:
   after=a.compare_post_state.resolve();post=NestopiaContext.parse(after.read_bytes());input_pins[str(after.relative_to(ROOT))]=sha(after)
   sd=[dict(address=0x6000+i,CPU_prefix=a,Native_frame_end=b)for i,(a,b)in enumerate(zip(m.sram,post.sram))if a!=b]
   rd=[dict(address=i,CPU_prefix=a,Native_frame_end=b)for i,(a,b)in enumerate(zip(m.ram,post.ram))if a!=b]
   row['later_Native_frame_parity']=dict(native_state=str(after.relative_to(ROOT)),native_state_sha256=sha(after),
    SRAM_bytes_compared=8192,SRAM_difference_count=len(sd),SRAM_differences=sd,RAM_difference_count=len(rd),RAM_differences=rd,
    registers_equal=row['final_registers']==post.registers,
    contract='Only field/SRAM parity is tested across these different timelines; no native perinstruction timing, complete RAM/register or source comparison is claimed.')
  print(json.dumps(dict(state=row['native_state'],stop=row['stop'],steps=row['original_instructions'],events=[f"{e['pc']:04X}:{e['registers']['a']}"for e in row['events']])),flush=True)
  if a.scan_resources:
   native=NestopiaContext.parse(path.read_bytes());ruler=native.sram[0xF03]
   owned=[city for city in range(30)if native.sram[city*32]&7==ruler]
   for amount in(0,100,300,1000,9999):
    preparation=[]
    for city in owned:
     for off,label in((2,'gold'),(4,'grain')):
      preparation.extend(((0x6000+32*city+off,amount&255,f'city{city}_{label}_low'),(0x6000+32*city+off+1,amount>>8,f'city{city}_{label}_high')))
    trial,_=trace(rom,path,a.instruction_budget,preparation);trial['trial']=f'owned_gold_and_grain{amount}';rows.append(trial)
    print(json.dumps(dict(trial=trial['trial'],stop=trial['stop'],steps=trial['original_instructions'],events=[f"{e['pc']:04X}:{e['registers']['a']}"for e in trial['events']])),flush=True)
 raw_catalog(rom,a.out.parent)
 if a.require_F8:assert any((row['initial']['request']==248 and row['original_wait_cycle_entire_machine_unchanged'])or(row['final']['request']==248 and row['stop']=='genuine_software_request_boundary')for row in rows),'No genuine F8 original waiting cycle or producer boundary'
 dependency_paths=[Path(__file__),ROOT/'source/recovered/nestopia_context.py',ROOT/'source/recovered/service_memory.py',ROOT/'source/recovered/mapped_memory.py']
 if a.capture_callers:
  input_pins.update({str(path.resolve().relative_to(ROOT)):sha(path)for path in a.capture_callers.rglob('*')if path.is_file()})
 receipt=dict(schema='phase20-F8-actual-context-gate-trace-v1',rom_sha256=ROM_SHA256,rows=rows,
  status='passed'if a.require_F8 else'bounded_original_CPU_diagnostics',analysis_kind='original_CPU_prefix_and_wait_diagnostics',Native_internal_CPU_trace=False,source_comparison_cases=0,
  original_CPU_prefix_count=len(rows),F8_initial_contexts=sum(row['initial']['request']==248 for row in rows),
  source_sha256={str(path.relative_to(ROOT)):sha(path)for path in dependency_paths},
  artifact_sha256={**input_pins,**{str(path.relative_to(ROOT)):sha(path)for path in (a.out.parent/'original-f8-selection.asm',a.out.parent/'original-ranges.json')}},
  limitations=['SavedPC/AXYP/SP/MAP/N163 are imported as captured; no cursor/request/ready/callerframe is injected.','Hardware reads are explicit constants and no new NMI/IRQ is scheduled. Native video timing is not reproduced.','Optional campaign numeric preparations are counterfactual software diagnostics, not observed Native effects.'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 if a.finalize:finalize(a.out.parent)
if __name__=='__main__':main()
