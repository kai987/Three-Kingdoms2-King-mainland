#!/usr/bin/env python3
"""Read-only exact-byte evidence for phase5 independent transfer/succession rules."""
import argparse, hashlib, inspect, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.officer_transfer import ROM_SHA256,TransferData,OfficerTransfer
RANGES={
 'pair10_entry_trampolines':(10,0xA000,0xA00F),
 'all_city_chiefs':(11,0xC98F,0xCA19),
 'AI_leader_death_and_family_selection':(11,0xCA19,0xCAD8),
 'AI_virtue_selection_and_commit_and_followers':(11,0xCB05,0xCC12),
 'recruitment_loyalty_only':(11,0xCF3F,0xCF7C),
 'leader_change_loyalty_only':(11,0xCF7C,0xD00C),
 'capture_loyalty_only':(11,0xD00C,0xD03A),
 'city_pointer_caps_resources':(11,0xD105,0xD12D),
 'ruler_pointer_protocol':(11,0xD319,0xD328),
 'AI_roster_compaction':(11,0xD3DD,0xD40F),
 'city_resources_cap':(11,0xD69D,0xD6D0),
 'loyalty_post_write_helper_is_RTS':(11,0xD61E,0xD61F),
 'player_roster_compaction_and_removal':(25,0xBD86,0xBE01),
 'manual_successor_commit':(25,0xBF85,0xBFAC),
 'release_selected_officer':(26,0xC099,0xC0E5),
 'swap_city_chief':(26,0xC101,0xC132),
 'automatic_successor_commit':(26,0xC25D,0xC280),
 'player_follower_recalculation_and_removal':(26,0xC289,0xC342),
 'recruit_and_move_roster':(27,0xACF0,0xADF2),
}
SERVICES={
 'loyalty_for_recruitment':{'entry':'physical10 A006 -> physical11 CF3F','stop':'RTS','writes':['officer.byte3']},
 'loyalty_after_leader_change':{'entry':'physical10 A009 -> physical11 CF7C','stop':'RTS','writes':['officer.byte3 unless family exemption']},
 'loyalty_after_capture':{'entry':'physical10 A00C -> physical11 D00C','stop':'RTS','writes':['officer.byte3']},
 'delete_city_officer':{'entry':'25 BDBB','stop':'RTS','writes':['officer.byte11 low2 OR3','selected city roster slot erase+compact','empty owner=(owner&F8)|7','RAM0580..058F']},
 'release_city_officer':{'entry':'26 C099','stop':'C0E2 before F28B dialogue','writes':['status low2=0','byte5=currentcity','roster left shift','empty owner whole byte7','0402++','042C ID']},
 'move_roster_group':{'entry':'27 AD41','stop':'RTS','writes':['append into destination','leader swap into first roster','ruler.byte1 destination if leader found','erase source first matches+compact','0481..048A']},
 'recruit_officer':{'entry':'27 ACF0','stop':'AD37 before UI state/text tail','writes':['roster17+count(nonFF)','status2','loyalty unless oldstatus1','RAM30/31']},
 'promote_city_chief':{'entry':'11 C9A5','stop':'RTS','writes':['two city roster entries swap','city resource caps even on owner rejection']},
 'repair_ruler_city_chiefs':{'entry':'11 C98F','stop':'RTS','writes':['repeat promote over30cities']},
 'choose_successor':{'entry':'11 CA68 / CA87 / CB05','stop':'CB52 before commit or CA6E if none','writes':['city resources cap','RAM27 candidate']},
 'recalculate_ai_followers':{'entry':'11 CB81','stop':'RTS','writes':['loyalty','if sampled<20: status0+byte5city but roster retained','6F73 buffer only full roster path','RNGcursor52','0045=30+early tail frames']},
 'install_ai_successor':{'entry':'11 CB52','stop':'CB79 before required6F8B=1 acknowledgement','writes':['ruler.byte0 newID','new leader loyalty100','AI follower effects','6F8B=FC','ruler.byte1 unchanged']},
 'resolve_ai_leader_death':{'entry':'11 CA19 selected-ruler prefix CA37','stop':'CA52 alive / CB79 installed / CA7F no candidate; UI ack and chief repair external','writes':['oldleaderstatus3','selection+commit or only rulerleaderFF','6F8B=FC or FB']},
 'set_city_chief':{'entry':'26 C101','stop':'RTS','writes':['first matching rosterID swap withslot17']},
 'commit_player_successor':{'entry':'25 BF85 manual / 26 C25D automatic','stop':'BFA9 / C27D before F28B dialogue','writes':['ruler.byte0 candidate','manual only ruler.byte1 city','chief swap','0402++','042C candidate','automatic only04D0=0']},
 'recalculate_player_followers':{'entry':'26 C289','stop':'RTS','writes':['optional loyalty','sampled departure: actual roster remove+status0','family stale22/23 pointer preserved','newleaderloyalty100','0401=0470','0402=0','RNGcursor50']},
}

def analyze(rom_path,out):
 rom=rom_path.read_bytes();data=TransferData.from_rom(rom);ranges=[];listing=[]
 for name,(bank,start,end) in RANGES.items():
  memory=bytearray(65536);base=0xA000 if bank in (10,25,27) else 0xC000
  memory[base:base+8192]=rom[16+bank*8192:16+(bank+1)*8192]
  memory[0xE000:]=rom[16+31*8192:16+32*8192]
  d=Disassembler(MPU(memory=memory));offset=16+bank*8192+start-base;code=rom[offset:offset+end-start]
  ranges.append({'name':name,'bank':bank,'cpu_start':start,'cpu_end_exclusive':end,'rom_offset':offset,'bytes_hex':code.hex(),'byte_sha256':hashlib.sha256(code).hexdigest()})
  listing+=['',f'; {name}; bank{bank}, ROM${offset:06X}, byteSHA256{hashlib.sha256(code).hexdigest()}']
  pc=start
  while pc<end:
   size,asm=d.instruction_at(pc);tail=''
   if memory[pc:pc+3]==bytes.fromhex('2007ee'):
    target=int.from_bytes(memory[pc+3:pc+5],'little');size=5;tail=f' ; inline far target${target:04X}; selector supplied inY'
   if pc+size>end:raise ValueError(f'Range split an instruction:{bank}:{pc:04X}')
   listing.append(f'${pc:04X} {memory[pc:pc+size].hex(" "):17} {asm}{tail}');pc+=size
 family=[]
 for index,ids in enumerate(data.families):
  poff=16+11*8192+0xAD8+index*2;address=int.from_bytes(rom[poff:poff+2],'little');offset=16+11*8192+address-0xC000
  family.append({'ruler_index':index,'pointer_cpu':0xCAD8+index*2,'pointer_rom_offset':poff,'list_cpu':address,'list_rom_offset':offset,'officer_ids_in_priority_order':list(ids),'bytes_including_FF':rom[offset:offset+len(ids)+1].hex()})
 services={name:{**spec,'source_line':inspect.getsourcelines(getattr(OfficerTransfer,name))[1]} for name,spec in SERVICES.items()}
 evidence={'original_rom_sha256':ROM_SHA256,'original_rom_size':len(rom),'source_status':'Manually recovered independent high-level behavior, not original development source and not full game engine.',
  'code_ranges':ranges,'services':services,'service_count':len(services),'family_lists':family,
  'field_claims':{'city_record_base':0x6000,'city_stride':32,'roster_offsets_inclusive':[17,26],'officer_base':0x63C0,'officer_stride':12,'ruler_base':0x6F07,'ruler_stride':8,'ruler_proven_count':7,
   'city_owner_access':'Most political scans usebyte0&7; recruitment passesbyte0 throughF368 which masks0F. Out-of-range ruler8..15 not claimed.',
   'ruler_byte0':'leaderID written CB60/BF98/C268','ruler_byte1':'residence city written AD96/BF9F, not CB52/C25D','ruler_byte3':'CA33 compares exactly3, AI succession-controller classification',
   'byte3':'loyalty (prior UI evidence + writer endpoints)','byte4':'virtue (prior UI evidence + D2AB offsets)','byte5':'location when released C0A6/CBE9; no update on move/recruit/player-inheritance release','byte11_low2':'persistent status0/2/3 mechanical writes; no unsupported global permanent-deletion claim',
   'troops':'raw16 bytes8/9 preserved byte-for-byte in these algorithms; no low10 assumption'},
  'important_label_correction':{'physical10_A003':'JMP D717 scene controller, not political transfer','physical10_A006':'JMP CF3F loyalty only','physical10_A009':'JMP CF7C loyalty only','physical10_A00C':'JMP D00C loyalty only','D61E_byte_hex':rom[16+11*8192+0x161E:16+11*8192+0x161F].hex(),'D61E':'RTS; no hidden ownership helper'},
  'boundaries':{'scene_acknowledgement':'6F8B=FC/FB means pending; host must later supply original acknowledgement1; source never auto-acknowledges','AI_post_ack':'C98F chief repair can be separately invoked; outer CA19 loop then D249/BEC7 domestic orchestration is outside this source','player_dialogue':'F28B message queues C2/D3/D4 remain external; pending IDs returned, no dummy renderer','scan_safety':'AD41 searches without city-roster bound and8bitY wraps. Missing value after256 positions raises UnboundedOriginalScan; this is an explicit host guard for the original infinite scan.'},
  'quirks':['CF3F unsigned subtraction wraps before min90/max10; anomaly oldloyalty>base can become90','CF7C family exemption depends on newleader ID, not target officer; it exempts every follower and leaves22/23 unchanged','CF7C positive virtue-delta add wraps before penalty10 and clamping','C9A5 scoreu8(loyalty+virtue), late ties; first loyalty100 wins immediately','CA87 family-priority/fallback virtue selection does not check health or officerstatus','ACF0 inserts at17+count(nonFF), potentially overwrites an existing entry if a hole occurs, or offset27 when full','AD41 does not check same owner or capacity; source preserves alias/overflow writes','CB81 early rosterFF/newleader tail-jumps into its caller leaving return frames; final0045=30+frames','AI sampled departure clears status and writes location but never erases ID; player sampled departure really shifts roster and leaves location untouched','Player family exemption leaves a stale22 pointer read/clear while deleting current roster entry; preserved for valid stale officer-record pointers; arbitrary I/O/ROM/control aliases are outside scope','Empty city removal BDBB preservesowner upper5bits; releaseC099 writes wholebyte7; player succession does not clear owner','No-successor CA68 clears only rulerleaderID and emitsFB; no whole faction/city neutralization is inferred'],
  'reproducible_commands':['.venv-trace/bin/python scripts/analyze_officer_transfer.py "/Users/paulasmith/Downloads/三国志2超级版.nes"','.venv-trace/bin/python scripts/verify_officer_transfer.py'],
  'runtime_scope':'Original CPU oracle only. No new full-core transfer/succession navigation or screenshot validation is claimed; menu-0 is context, fixtures explicitly replace records.'}
 out.mkdir(parents=True,exist_ok=True)
 (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');(out/'original-ranges.asm').write_text('\n'.join(listing)+'\n')
 (out/'tables.json').write_text(json.dumps({'families':family,'rng':list(data.rng),'rng_rom_offset':0x3E8CA},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'code_ranges':len(ranges),'services':len(services),'family_lists':len(family),'sha256':ROM_SHA256},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/transfer');a=p.parse_args();analyze(a.rom,a.out)
