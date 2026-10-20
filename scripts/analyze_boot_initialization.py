#!/usr/bin/env python3
"""Read-only original reset/probe bytes, hardware sites and boundary catalog."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from inspect_game_data import OPS,SIZES,instruction
from source.recovered.boot_initialization import ROM_SHA256

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();r=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
 out=ROOT/'analysis/phase14/boot';out.mkdir(parents=True,exist_ok=True);nodes=[];lines=[];ranges=[]
 for lo,hi in[(0xE000,0xE066),(0xF3BD,0xF477)]:
  off=16+31*8192+(lo&8191);raw=r[off:off+hi-lo];ranges.append(dict(physical_bank=31,cpu_start=lo,cpu_end_exclusive=hi,rom_offset=off,byte_count=len(raw),raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
  pc=lo
  while pc<hi:
   pos=16+31*8192+(pc&8191);op,mode=OPS[r[pos]];size=SIZES[mode];assert op!='?'and pc+size<=hi;value=int.from_bytes(r[pos+1:pos+size],'little');_,asm=instruction(r,pos,pc)
   row=dict(pc=pc,physical_bank=31,rom_offset=pos,op=op,mode=mode,operand=value,raw_hex=r[pos:pos+size].hex(),assembly=asm)
   nodes.append(row);lines.append(f'{pos:06X} bank31:${pc:04X} {row["raw_hex"]:<8} {asm}');pc+=size
 catalog=dict(status='passed',rom_sha256=ROM_SHA256,original_instruction_count=len(nodes),instructions=nodes,ranges=ranges,reset_entry=0xE000,reset_terminal=0xE066,reset_terminal_kind='nonreturning pre-dispatch boundary',reset_RAM_range=[4,2048],RAM_range_is_half_open=True,SRAM_ordinary_probe_mismatch='retained byte-for-byte',vblank_Y_initial_values=[2,4],successful_set_clear_pairs=[3,5],probe=dict(entry=0xF3BD,source_bits_cpu_range=[0xF3BD,0xF403],bit_count=70,comparison='(($4017 >> 1) ^ FF) & 1 versus ROMbyte&1',first_mismatch_returns=0xF421,all_match_diagnostic=True,permanent_halt_PC=0xF41E,palette_colors=[1,55,22],declared_readwrite_diagnostic_SRAM_range=[0x6000,0x8000]),helpers=[0xF422,0xF43F,0xF458,0xF468],source_path='source/recovered/boot_initialization.py',source_sha256=sha(ROOT/'source/recovered/boot_initialization.py'),analyzer_path='scripts/analyze_boot_initialization.py',analyzer_sha256=sha(Path(__file__)))
 (out/'static-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n');(out/'original-ranges.asm').write_text('; Original fixed31 bytes with16B iNES header; no table bytes decoded as instructions.\n'+'\n'.join(lines)+'\n')
 print(json.dumps(dict(instructions=len(nodes),original_bytes=sum(x['byte_count']for x in ranges))))
if __name__=='__main__':main()
