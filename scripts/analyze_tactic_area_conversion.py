#!/usr/bin/env python3
"""Record original bytes for complete7/8/10/12/14 semantic effect bodies."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction,OPS,SIZES
from source.recovered.tactic_area_conversion import ROM_SHA256,SUPPORTED_IDS,ENTRY_POINTS,DECLARED_RAM_RANGES,AreaConversionData
RANGES=[(12,0xa000,0xb2cd,0xb31c,'7_cross_and_neighbor'),(12,0xa000,0xb31c,0xb3b6,'8_conversion'),
 (12,0xa000,0xb3d0,0xb42a,'10_chain'),(12,0xa000,0xb466,0xb4b8,'12_water'),(12,0xa000,0xb50c,0xb5a6,'14_fire'),
 (12,0xa000,0xb8a1,0xb94a,'connected_candidates'),(12,0xa000,0xb643,0xb67b,'cross_coordinate_lookup'),
 (12,0xa000,0xb67b,0xb68b,'center_coordinate'),(13,0xc000,0xc886,0xc91e,'conversion_accounting'),
 (13,0xc000,0xdc4b,0xdc63,'enemy_sign_gate'),(13,0xc000,0xd6b6,0xd6cc,'highest_slot_coordinate_match'),
 (13,0xc000,0xdb46,0xdb9e,'player_terrain_lookup'),(12,0xa000,0xb72b,0xb7ba,'conversion_success_gate'),
 (12,0xa000,0xb7be,0xb85a,'generic_success_gate'),(11,0xc000,0xcf3f,0xcf7c,'loyalty_only_helper'),
 (12,0xa000,0xb070,0xb0dd,'fire_damage_and_loss'),(12,0xa000,0xb1e3,0xb243,'water_damage_and_loss'),
 (12,0xa000,0xb55c,0xb5a6,'raidfire_damage_and_loss'),(12,0xa000,0xb68b,0xb6f0,'loss_and_repeated_experience')]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/area-conversion');a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;AreaConversionData.from_rom(rom);a.out.mkdir(parents=True,exist_ok=True);ranges=[]
 for bank,base,lo,hi,name in RANGES:
  pc=lo;lines=[];off=16+bank*8192+lo-base;raw=rom[off:off+hi-lo]
  while pc<hi:
   q=16+bank*8192+pc-base;op,mode=OPS[rom[q]];size=SIZES[mode];_,asm=instruction(rom,q,pc)
   lines.append(f'{q:06X} b{bank:02d}:${pc:04X} {rom[q:q+size].hex(" ").upper():<14} {asm}')
   if op=='JSR'and int.from_bytes(rom[q+1:q+3],'little')==0xee07:
    target=int.from_bytes(rom[q+3:q+5],'little');lines.append(f'{q+3:06X} b{bank:02d}:${pc+3:04X} .word ${target:04X} ; EE07 inline target, resumes ${pc+5:04X}');size=5
   pc+=size
  assert pc==hi,(name,hex(pc),hex(hi));(a.out/(name+'.asm')).write_text('\n'.join(lines)+'\n')
  ranges.append({'name':name,'bank':bank,'cpu_start':lo,'cpu_end_exclusive':hi,'file_start':off,'raw_hex':raw.hex(' ').upper(),'sha256':hashlib.sha256(raw).hexdigest()})
 evidence={'rom_sha256':ROM_SHA256,'source_kind':'Independent readable semantic source, no IR/original-CPU fallback',
  'supported_tactic_ids':list(SUPPORTED_IDS),'entry_points':{str(k):{'bank':12,'cpu':v,'file':0x18010+v-0xa000}for k,v in ENTRY_POINTS.items()},
  'scope':'Effect handler after actual B02B reset; no AP/menu/graphics/frame simulation',
  'conversion_farcall':{'call_bank':12,'call_cpu':0xb3ad,'file':0x193bd,'raw_hex':'20 07 EE 06 A0','logical_selector':0x2a,'physical_pair':[10,11],'entry':0xa006,'actual_body':0xcf3f,'effect':'target loyalty only; no city roster/status/location writes'},
  'area_candidate_rules':{'generic':'B8A1 unconditionalcenter then breadth-first right/left/down/up first ascending enemy coordinate match, unique slot IDs, class5 blocks','ID7':'Center always hit aftergate; left/right/up/down uses descending slot match, filters enemy only after coordinate selection, no officer-record dedup','10':'class3 candidate eachdraw<2, condition sample+3+side_sign','12':'class3 candidate eachB1E3 damage+repeated NEW-total XP','14':'notclass5 candidate eachB55C damage+repeated NEW-total XP'},
  'conversion_accounting':'0628 beforeflip selects donor; counts--/++mod256, donor raw16 total minuslow10 saturates0, recipient raw16 addition wraps. Active0504 doesnotselect accounting side.',
  'ranges':ranges,'declared_RAM_ranges':[list(x)for x in DECLARED_RAM_RANGES],'all_SRAM_window':[0x6000,0x8000]}
 (a.out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'supported_ids':list(SUPPORTED_IDS),'ranges':len(ranges),'conversion_city_roster_change':False}))
if __name__=='__main__':main()
