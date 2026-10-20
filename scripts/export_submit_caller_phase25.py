#!/usr/bin/env python3
"""Export the passive B431 software snapshot; hardware stays an explicit fixture.

No CPU/core is run and no saved caller or numeric byte is altered. Only new
phase25 files are written. The fixed original core has no internal hook.
"""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
CAPTURE=ROOT/'analysis/phase25/runtime/natural-nonzero-reserve-submit/observer'
OUT=ROOT/'analysis/phase25/cpu-submit/actual-callers/entry-B431-observer-0023'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def main():
 p=CAPTURE/'callee-0023-B431.json';x=json.loads(p.read_text())
 assert (x['frame'],x['entry'],x['physical_bank'])==(23,0xB431,27)
 assert x['actual_registers']['pc']==x['entry'] and x['actual_PRG_banks']==[2,27,28,31]
 assert x['inherited_preparation_byte_writes']==x['additional_core_memory_writes']==0
 assert not x['instantaneous_N163_PPU_APU_captured']
 ram=CAPTURE/x['exported_RAM'];sram=CAPTURE/x['exported_SRAM'];r=ram.read_bytes();s=sram.read_bytes()
 assert len(r)==2048 and len(s)==8192 and sha(ram)==x['RAM_sha256'] and sha(sram)==x['SRAM_sha256']
 sp=x['actual_registers']['sp'];word=r[0x100+((sp+1)&255)]|r[0x100+((sp+2)&255)]<<8
 assert word==x['stack_top_word_raw'] and int.from_bytes(r[0x42C:0x42E],'little')==9899
 OUT.mkdir(parents=True,exist_ok=True);assert not any(OUT.iterdir()),'A captured-input export is immutable'
 (OUT/'input-ram.bin').write_bytes(r);(OUT/'input-sram.bin').write_bytes(s)
 (OUT/'input-n163.bin').write_bytes(bytes((11+37*i)&255 for i in range(128)))
 x=dict(schema='phase25-passive-submit-caller-with-hardware-fixture-v1',
  origin='passive_Native_callee_capture_with_explicit_N163_fixture',
  registers=x['actual_registers'],physical_banks=x['actual_PRG_banks'],actual_caller_return_pc=(word+1)&65535,
  original_software_caller_frame_preserved=True,prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],
  N163_origin='explicit_shared_fixture_not_Native_snapshot',N163_address=127,N163_autoincrement=True,
  controller_buttons=[0,0],hardware_events=[],instantaneous_N163_PPU_APU_captured=False,
  capture_core_sha256=x['capture_core_sha256'],capture=rel(p),capture_sha256=sha(p),
  exact_capture_input_pins={rel(ram):sha(ram),rel(sram):sha(sram)},
  paired_Native_validation='analysis/phase25/runtime/validation.json',
  limits=['RAM,SRAM,registers,four banks and existing stack are instantaneous passive-core software observations.',
   'The N163 pattern, device read ports and zero controller ports are explicit common CPU/Source inputs; no instant Native hardware state is asserted.',
   'The import inherits a zero-preparation ordinary-input allocation route; this is not a new cold boot.'])
 (OUT/'context.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='exported_without_CPU_or_core',path=rel(OUT),prepared_numeric_bytes=0)))
if __name__=='__main__':main()
