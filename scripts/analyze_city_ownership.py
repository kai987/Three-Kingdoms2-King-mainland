#!/usr/bin/env python3
"""Read-only byte provenance/catalog for city-owner writer paths, phase6."""
from pathlib import Path
import argparse,hashlib,inspect,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.city_ownership import CityOwnership,OwnershipData,ROM_SHA256
RANGES={
 'AI_zero_branch_capture_commit':(10,0xA8FC,0xA90D),
 'AI_officer_neighbor_relocation_or_release':(10,0xABA3,0xAC67),
 'AI_colonization_transaction':(10,0xB287,0xB357),
 'AI_withdrawal_transaction':(10,0xB3B1,0xB42B),
 'AI_persuasion_membership_transaction':(10,0xBA8D,0xBAE2),
 'city_action_mode2_empty_firstslot_check':(28,0xD16B,0xD183),
 'unit_retreat_roster_cache_owner_body':(12,0xBC2D,0xBC93),
 'existing_finalizer_owner_and_chiefs':(8,0xBBB8,0xBC46),
}
WRITERS=[
 (8,0xBBDD,240,'outcome0514==0; high ruler0507','battle_state_machine.finalize_city_ownership','composed old source'),
 (8,0xBCD9,0,'AI allocation fills an initiallyempty eligible neighbor','postbattle.process_ai_officers','existing source'),
 (10,0xA90B,248,'6F8C==0 branch; targetcity0038, owner6F03','city_ownership.commit_ai_capture','new source'),
 (10,0xAC11,248,'AI combat officer relocation chosecity; ruler0040','city_ownership.relocate_after_ai_battle','new source'),
 (10,0xB354,248,'colonization target0038; ruler6F03','city_ownership.colonize_city','new source'),
 (10,0xB429,248,'withdrawsource0037 becomesneutral7','city_ownership.withdraw_city','new source'),
 (10,0xBAE0,0,'persuaded officer removed from003F; empty ->whole7','city_ownership.transfer_persuaded_officer','new source'),
 (11,0xCC0F,0,'AI follower fullroster compaction path; count0 ->whole7','officer_transfer.recalculate_ai_followers','existing source; conditional empty branch not demonstrated by valid fullroster fixture'),
 (12,0xBC90,240,'unit retreat destinationowner&7==7; side ruler0507/0504','city_ownership.retreat_unit_to_city','new source'),
 (13,0xD296,240,'human postbattle destinationowner&7==7; side050B/0507','postbattle.apply_selected_officers','existing source'),
 (25,0xBDFE,248,'selectedcity officer deletion leaves no records ->neutral7','officer_transfer.delete_city_officer','existing source'),
 (26,0xC0D5,0,'selectedcity release leaves no records ->whole7','officer_transfer.release_city_officer','existing source'),
 (28,0xD181,0,'mode0473==2; city0471 firstslotFF ->whole7','city_ownership.finish_empty_city_action','new source'),
]
BASES={8:0xA000,10:0xA000,11:0xC000,12:0xA000,13:0xC000,25:0xA000,26:0xC000,28:0xC000}
def analyze(path,out):
 rom=path.read_bytes();data=OwnershipData.from_rom(rom);listing=[];ranges=[]
 for name,(bank,start,end)in RANGES.items():
  base=BASES[bank];memory=bytearray(65536);memory[base:base+8192]=rom[16+bank*8192:16+(bank+1)*8192];memory[0xE000:]=rom[16+31*8192:16+32*8192]
  d=Disassembler(MPU(memory=memory));offset=16+bank*8192+start-base;raw=rom[offset:offset+end-start]
  ranges.append({'name':name,'physical_bank':bank,'cpu_start':start,'cpu_end_exclusive':end,'rom_offset':offset,'byte_sha256':hashlib.sha256(raw).hexdigest(),'bytes_hex':raw.hex()})
  listing+=['',f'; {name}, physicalbank{bank}, file${offset:06X}'];pc=start
  while pc<end:
   size,asm=d.instruction_at(pc)
   if pc+size>end:raise ValueError(f'Split instruction at{pc:04X}')
   listing.append(f'${pc:04X} {memory[pc:pc+size].hex(" "):14} {asm}');pc+=size
 writers=[]
 for bank,pc,mask,condition,service,status in WRITERS:
  off=16+bank*8192+pc-BASES[bank];assert rom[off]==0x91,(bank,pc,rom[off])
  writers.append({'physical_bank':bank,'CPU_store':pc,'rom_store_offset':off,'store_bytes_hex':rom[off:off+2].hex(),'nearby_original_bytes_hex':rom[off-12:off+5].hex(),'preserve_mask':mask,'condition':condition,'source_service':service,'recovery_status':status})
 source={name:inspect.getsourcelines(getattr(CityOwnership,name))[1]for name in ['commit_ai_capture','relocate_after_ai_battle','colonize_city','withdraw_city','transfer_persuaded_officer','finish_empty_city_action','retreat_unit_to_city','finalize_battle_ownership']}
 evidence={'original_rom_sha256':ROM_SHA256,'source_status':'Independent manually recovered game-memory transaction semantics; not original development source, CPU protocol or whole city menu engine.','new_direct_transaction_count':7,'existing_composed_service_count':1,'source_lines':source,'code_ranges':ranges,'discovered_gameplay_owner_writer_count':len(writers),'owner_writers':writers,
  'data':{'adjacency_bank':16,'CPU_address':0x9D72,'ROM_offset':0x21D82,'byte_count':256,'proven_city_rows':30,'bytes_hex':data.adjacency.hex(),'rng_cursor54_original_helper':'E89A'},
  'entry_inputs':{'A8FC':'0038 targetcity,6F03 newruler; caller previouslytested6F8C==0','ABA3':'0038 combatcity,0040 ruler,0041 officer,0042=0 forloyalty adjustment; data16 selected byoriginalF266; RNGcursor54','B287':'003A sourcecity,0038 targetcity,0037 allocationbase3..10 (not source rostercount; upstream B159 computes it and B168 separatelyreads D304),003D/3E goldword,003B/3C grainword,6F03 ruler; priorselection/affordability outside','B3B1':'A must already contain destinationcity (loaded atB3A9);0037 sourcecity,0038 destinationcity; stopB42B beforeAP/unwind','BA8D':'0038 destinationcity,003F formercity,003D officer,6F03 newruler; successful priorpersuasion outside','D16B':'A=0473 actionmode,0471 city; earlierUI/input/D568 work outside; stopD183','BC2D':'0509 active slot,050B destinationcity,0504 side,0507 packedrulers; precedingC91E helper atBC2A outside'},
  'confirmed_effects':['Ownerpreservation masksF8,F0,andwholebyte writes remain distinct','Real BA8D membership transfer appends then adjusts loyalty then deletes oldcity firstmatch and compacts; no status/byte5 or rulerhome write','Colonize moves count-2 highestloyal followers fromslots18..26, late ties; excludes firstslot and overwrites destinationprefix','Withdrawal merges fullword supplies withwrap but no finalcap, clears source supplies, moves untilfirstFF, F8|7 source, returns APcost4+2*count','Retreat unit body clears six battlearrays and matching04D8/04DC cache references; commander0/10 save052B/052C, neutralownerF0|ruler','AI relocation uses owncity smallestprefixcount before lastneutral neighbor; no roster/status2/home write unless described; overflowstatus0 location samples roll0=currentcity orroll1..7 neighbor0..6','Mode2 emptycheck tests firstslot only, not count of all10 slots'],
  'boundaries':['A90D D249 residence search + CA19 succession outside captureprefix','BAE2 former-ruler political reaction/diplomacy outside membershipprefix','B42B D152 AI budgetunwind/B17D continuation external; cost returned as pending','C91E work before retreatunit body not counted as completed','No gamecontroller/NMI/display/input/hardware preparation is synthesized'],
  'coverage_limits':['13 gameplay writer sites are all currentlydiscovered/reviewed examples, not proof of a complete ROMwide pointer-dataflow audit. Signature/callgraph scans can miss indirect aliases or writes in unseeded code.','Startup SRAM templatecopy is initialization and excluded from gameplay writer list.','Prior battle/postbattle/officer services remain their own source; this new file doesnot rewrite whole allocation/UI algorithms.','No new full-core naturalcity takeover/diplomacy capture is claimed.','Factions lifecycle, leaderFF/controller/victory bookkeeping are distinct: cityneutralization alone doesnot mean factionelimination.','AI validfullroster release retainsIDs, so CC0F emptybranch is cataloged but not claimed as dynamicallycovered by normalvalidfullroster fixtures.'],
  'commands':['.venv-trace/bin/python scripts/analyze_city_ownership.py "/Users/paulasmith/Downloads/三国志2超级版.nes"','.venv-trace/bin/python scripts/verify_city_ownership.py']}
 out.mkdir(parents=True,exist_ok=True);(out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');(out/'original-ranges.asm').write_text('\n'.join(listing)+'\n');print(json.dumps({'new_direct_transactions':7,'composed_existing':1,'owner_writer_sites':len(writers),'code_ranges':len(ranges)},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase6/ownership');a=p.parse_args();analyze(a.rom,a.out)
