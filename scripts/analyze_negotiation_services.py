#!/usr/bin/env python3
"""Pin newly named helpers, original instruction bytes and measured coverage."""
from pathlib import Path
import ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction
OUT=ROOT/'analysis/phase20/services'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 result=read(OUT/'validation.json');seq=read(ROOT/'analysis/phase20/cpu/consumer-sequences.json')
 assert result['status']==seq['status']=='passed'
 positions={(r['physical_bank'],r['cpu_address'])for r in result['executed_instruction_positions']}
 positions.update((r['physical_bank'],r['cpu_address'])for r in seq['executed_instruction_positions'])
 instructions=[];ranges=[];asm=[]
 for bank,start,end in((10,0xB7A2,0xB98B),(11,0xD080,0xD0AA),(11,0xD307,0xD319)):
  pc=start
  while pc<end:
   off=16+bank*8192+(pc&8191);size,text=instruction(rom,off,pc)
   assert not text.startswith('.byte')and pc+size<=end
   raw=rom[off:off+size];row=dict(physical_bank=bank,cpu=pc,rom_offset=off,raw_hex=raw.hex(' '),assembly=text,dynamically_executed=(bank,pc)in positions)
   instructions.append(row);asm.append(f'{off:06X} b{bank:02d}:${pc:04X} {raw.hex(" "):<8} {text}');pc+=size
  off=16+bank*8192+(start&8191);blob=rom[off:off+end-start]
  ranges.append(dict(physical_bank=bank,start=start,end_exclusive=end,rom_offset=off,size=len(blob),raw_hex=blob.hex(),sha256=hashlib.sha256(blob).hexdigest()))
 files=[ROOT/'source/recovered/negotiation_services.py',ROOT/'source/recovered/negotiation_integration.py',Path(__file__),ROOT/'scripts/verify_negotiation_services.py',ROOT/'scripts/verify_phase20_negotiation_interleave.py']
 tree=ast.parse(files[0].read_text());forbidden=[]
 for node in ast.walk(tree):
  if isinstance(node,(ast.Import,ast.ImportFrom)):
   name=getattr(node,'module','')or' '.join(x.name for x in node.names)
   if 'py65'in name or 'control_ir'in name:forbidden.append(name)
  if isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id in('eval','exec','compile'):forbidden.append(node.func.id)
 assert not forbidden
 coverage=dict(static_original_positions=len(instructions),static_original_bytes=sum(r['size']for r in ranges),
  dynamically_executed_positions=sum(r['dynamically_executed']for r in instructions),
  not_dynamically_executed=[r for r in instructions if not r['dynamically_executed']],
  instruction_position_coverage_is_not_full_input_or_hardware_timing_coverage=True)
 write(OUT/'static-catalog.json',dict(schema='phase20-named-negotiation-original-bytes-v1',ROM_sha256=ROM_SHA,ranges=ranges,instructions=instructions,coverage=coverage))
 (OUT/'original.asm').write_text('\n'.join(asm)+'\n')
 write(OUT/'evidence.json',dict(schema='phase20-named-negotiation-evidence-v1',status='passed',ROM_sha256=ROM_SHA,coverage=coverage,
  source_original_CPU_callbacks=0,production_IR_interpretation=False,AST_forbidden_imports_or_dynamic_execution=forbidden,
  source_sha256={str(p.relative_to(ROOT)):sha(p)for p in files},
  validation=dict(path='analysis/phase20/services/validation.json',sha256=sha(OUT/'validation.json'),parent_cases=result['original_CPU_parent_cases'],counts=result['counts']),
  consumer_sequences=dict(path='analysis/phase20/cpu/consumer-sequences.json',sha256=sha(ROOT/'analysis/phase20/cpu/consumer-sequences.json'),parent_cases=seq['rom_cpu_sequence_count']),
  artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(OUT/'static-catalog.json',OUT/'original.asm')},
  limits=['The CPU oracle executes original bytes only in validators; production source has no CPU/IR fallback.','New aliases bind ordinary named methods directly.','Native screenshots and timing are separate artifacts.']))
 print(json.dumps(dict(status='passed',coverage=coverage)))
if __name__=='__main__':main()
