#!/usr/bin/env python3
"""Pin original text script, PPU consumer and immutable data provenance."""
import argparse,ast,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction
from source.recovered.officers import ROM_SHA256
from source.recovered.text_services import TextData

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 out=ROOT/'analysis/phase10/text';out.mkdir(parents=True,exist_ok=True)
 ranges=[];lines=[]
 for name,bank,lo,hi in [('text_PPU_consumer',29,0xA048,0xA154),('text_worker_and_commands',29,0xA154,0xA607),('buffer_fill_and_message_pointer',29,0xA60F,0xA672),('select_message_data_window',29,0xA690,0xA6A7),('message_readiness',13,0xDF27,0xDF39),('selected_actor_name_panel',29,0xA830,0xA856),('name_panel_glyph_rows',29,0xA957,0xA991),('officer_symbol_pointer_and_centering',31,0xF308,0xF35F)]:
  file=16+bank*8192+(lo&8191);raw=rom[file:file+hi-lo]
  ranges.append(dict(name=name,physical_bank=bank,cpu_start=lo,cpu_end_exclusive=hi,rom_offset=file,byte_count=len(raw),raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
  lines.append('; '+name)
  pc=lo
  while pc<hi:
   offset=16+bank*8192+(pc&8191)
   if 0xA208<=pc<0xA248:
    word=int.from_bytes(rom[offset:offset+2],'little');lines.append(f'{offset:06X} b{bank}:${pc:04X} .word ${word:04X} ; original text command ${0x80+(pc-0xA208)//2:02X}');pc+=2;continue
   n,s=instruction(rom,offset,pc);assert pc+n<=hi
   lines.append(f'{offset:06X} b{bank}:${pc:04X} {rom[offset:offset+n].hex(" "):<10} {s}');pc+=n
 tables=[]
 for name,bank,lo,size in [('32_text_command_targets',29,0xA208,64),('message_selectors15',29,0xA6A7,15),('number_widths8',29,0xA607,8),('officer_text_symbols',16,0x901A,2370),('city_text_symbols',16,0x9A1A,240),('actor_name_panel_template',29,0xA856,59),('symbol_centering',31,0xF35F,8)]:
  offset=16+bank*8192+(lo&8191);raw=rom[offset:offset+size]
  tables.append(dict(name=name,physical_bank=bank,cpu=lo,rom_offset=offset,byte_count=size,raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
 files=['source/recovered/text_services.py','source/recovered/service_memory.py','source/recovered/battle_nmi_services.py','source/recovered/game_algorithms.py','scripts/analyze_text_services.py','scripts/verify_text_services.py']
 d=dict(rom_sha256=ROM_SHA256,source_kind='independent readable text data parser and actual port writers',ranges=ranges,tables=tables,
        dependency_pins=[dict(path=f,sha256=hashlib.sha256((ROOT/f).read_bytes()).hexdigest())for f in files],
        REA_archive=[dict(path=f'analysis/rea/pairs/pair-29/{name}',sha256=hashlib.sha256((ROOT/f'analysis/rea/pairs/pair-29/{name}').read_bytes()).hexdigest())for name in ('image.bin','evidence-bundle.json')],
        text_command_count=32,command_targets=TextData.from_rom(rom).command_targets,
        semantic_RAM_scope='0300..0374 buffers/queue,007D/E actualjobs,A6/A7 stream,E1 currentwindow; packedBCD7..9 wheredeclared; selected-actor body also0000..0002,0380..03BF; all8KSRAM',
        CPU_scratch_registers_stack_excluded=True,source_original_code_calls=0,source_IR_interpretation=False,
        distinctions=['Game text-data command parsing is separate from 6502/IR execution.',
                      'Cadence tailEE72 performs the actual E70E palette upload, while retaining the text job.',
                      'Finishing a script shifts0310..0313 but readiness DF27 still requires BOTH0304 and0300 equalFF.',
                      'The32-target table admits80..9F, not arbitraryA0..BF out-of-table bytes.',
                      '9C citymultiply wraps tobyte before base addition;9F reads report slot specified by its parameter, not a literal officer ID.'])
 (out/'evidence.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(out/'original-ranges.asm').write_text('\n'.join(lines)+'\n')
 print(json.dumps(dict(status='passed',ranges=len(ranges),tables=len(tables),text_commands=32)))
if __name__=='__main__':main()
