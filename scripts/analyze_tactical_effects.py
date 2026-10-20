#!/usr/bin/env python3
"""Export byte-grounded semantic cast/ambush evidence; no opcode IR output."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction,OPS,SIZES
from source.recovered.tactical_effects import ROM_SHA256,SUPPORTED_EFFECT_IDS,DECLARED_RAM_RANGES,EffectData
RANGES=[(12,0xa000,0xa51f,0xa617,'movement_secondary_request_and_consume'),(12,0xa000,0xaa3f,0xaaa7,'player_animation_and_cast'),
 (12,0xa000,0xaf73,0xafa1,'player_ambush_eligibility'),(12,0xa000,0xb02b,0xb042,'effect_dispatch_prefix'),
 (12,0xa000,0xb42a,0xb466,'ambush_deployment'),(13,0xc000,0xc004,0xc044,'AI_prepare'),
 (13,0xc000,0xc054,0xc100,'AI_confirmation_and_cast'),(13,0xc000,0xc1af,0xc1d1,'AI_ambush_bypass'),
 (9,0xc000,0xce20,0xce40,'round_expiry'),(9,0xc000,0xd6cd,0xd70f,'unit_removal_cache_clear'),
 (12,0xa000,0xb341,0xb353,'conversion_cache_clear'),(12,0xa000,0xbc5e,0xbc6e,'retreat_cache_clear'),
 (13,0xc000,0xc82a,0xc83c,'duel_or_transfer_cache_clear'),(13,0xc000,0xdee9,0xdf27,'level_popup_boundary'),
 (12,0xa000,0xa1f7,0xa20c,'cursor_reset'),(13,0xc000,0xc1f0,0xc1fc,'AI_return_to_unit_selection'),
 (13,0xc000,0xc91e,0xc98c,'retreat_detach_unit_accounting')]
def listing(rom,bank,base,lo,hi):
 lines=[];pc=lo
 while pc<hi:
  off=16+8192*bank+pc-base;op,mode=OPS[rom[off]];size=SIZES[mode];_,asm=instruction(rom,off,pc)
  raw=rom[off:off+size];lines.append(f'{off:06X} b{bank:02d}:${pc:04X} {raw.hex(" ").upper():<14} {asm}')
  if op=='JSR'and int.from_bytes(raw[1:],'little')==0xee07:
   pointer=int.from_bytes(rom[off+3:off+5],'little')
   lines.append(f'{off+3:06X} b{bank:02d}:${pc+3:04X} .word ${pointer:04X} ; EE07 inline data, resumes ${pc+5:04X}')
   size=5
  pc+=size
 assert pc==hi,('Evidence range must end at a code boundary',hex(lo),hex(hi),hex(pc))
 return '\n'.join(lines)+'\n'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase8/effects');a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=EffectData.from_rom(rom);a.out.mkdir(parents=True,exist_ok=True)
 evidence=[]
 for bank,base,lo,hi,name in RANGES:
  off=16+8192*bank+lo-base;raw=rom[off:off+hi-lo]
  (a.out/(name+'.asm')).write_text(listing(rom,bank,base,lo,hi))
  evidence.append({'name':name,'bank':bank,'cpu_start':lo,'cpu_end_exclusive':hi,'file_start':off,'raw_hex':raw.hex(' ').upper(),'sha256':hashlib.sha256(raw).hexdigest()})
 payload={'rom_sha256':ROM_SHA256,'source_kind':'Independent readable semantic source; no IR/original CPU fallback',
  'fully_recovered_effect_ids':list(SUPPORTED_EFFECT_IDS),'external_effect_ids':[i for i in range(16)if i not in SUPPORTED_EFFECT_IDS],
  'player_AP_cost_table':{'bank':12,'cpu':0xabc9,'file':0x18bd9,'bytes':list(data.player_costs)},
  'AI_AP_cost_table':{'bank':13,'cpu':0xc044,'file':0x1a054,'bytes':list(data.ai_costs),'ID11_bypasses_this_table':True},
  'deployment':{'tactic_id':11,'bank':12,'cpu':0xb42a,'file':0x1943a,'cache_groups':[0x4d8,0x4dc],'cache_layout':['actor_slot','x','y','ttl'],'ttl':5,'troop_word':'rawLE16 bytes8/9 subtract100 modulo65536','AI_AP_cost':0,'player_AP_cost':10},
  'retreat_accounting':{'bank':13,'cpu':0xc91e,'file':0x1a92e,'end_cpu_inclusive':0xc98b,'side_from':'0628[0509]&80','counts':[0x51e,0x51f],'totals':[0x51a,0x51c],'troop_word':'masked10bit +8/+9&3','count_subtraction':'modulo256,0->255','total_subtraction':'raw16 minus masked10, saturates0','following_commit':'bank12 BC2D..BC92 existing city_ownership.retreat_unit_to_city, UI prelude outside this semantic method'},
  'lifecycle':{'expiry_entry':{'bank':9,'cpu':0xce20,'file':0x12e30},'round_caller':'bank12 BDC0 side0->128 increments0506 and farcalls bank8A00F->bank9CD78; CE20 tail updates both rows',
   'expiry':'FF skips; only decrement1->0 clears slot. 0->FF underflow preserved. XY untouched.',
   'trigger_request':'bank12 A51F sees6F8BFF then request1 and actor0509 atA528/A52E; global4 bank8A02D branchesB933',
   'trigger':'Opposite cache group: side0 -> group4; side80 -> group0. Radius2 or original exact shortcut, normalized class0 only. Preserve B965 reads0614[group] bug and discarded draw.',
   'consume':'A535 waitsFF; status0 awards cached officer XP from042C/D and refreshes selectors; UI boundary atA5BB',
   'clear_after_confirmation':'A5F5 clears opposite slot only; actual text-ready+confirmation prefix remains external',
   'removal':'D6CD clears six unit arrays, strategy and first matching whole4B cache row; conversion/retreat/duel-transfer clear both matching slots only'},
  'declared_RAM_ranges':[list(r)for r in DECLARED_RAM_RANGES],'all_SRAM_window':[0x6000,0x8000],'CPU_register_stack_mapper_scope':False,
  'graphics_audio_readiness':'Returned exact dependencies; after_* APIs require the actual preceding service. Queue requests modify RAM but never complete rendering.',
  'ranges':evidence}
 (a.out/'evidence.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'supported_effects':list(SUPPORTED_EFFECT_IDS),'evidence_ranges':len(evidence),'AI_ambush_AP_cost':0,'player_ambush_AP_cost':10}))
if __name__=='__main__':main()
