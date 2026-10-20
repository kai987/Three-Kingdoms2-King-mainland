#!/usr/bin/env python3
"""Extract exact data/byte evidence for the independent phase4 duel rules."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.duel_logic import DuelTables,ACTION_NAMES,ROM_SHA256

RANGES={
 'turn_and_duration':(23,0xB361,0xB3F0),
 'AI_low_health':(23,0xB5D8,0xB626),
 'AI_desperate':(23,0xB626,0xB659),
 'AI_attack':(23,0xB659,0xB689),
 'AI_tactics':(23,0xB689,0xB719),
 'AI_fallback':(23,0xB719,0xB760),
 'pointer_high_gate':(23,0xB7B3,0xB7C2),
 'desperate_threshold':(23,0xB7DD,0xB816),
 'attack_threshold':(23,0xB816,0xB851),
 'negotiation_threshold':(23,0xB851,0xB89B),
 'status_threshold':(23,0xB89B,0xB8C7),
 'retreat_response_gate':(23,0xBB18,0xBB40),
 'retreat_hp_penalty':(23,0xBB5B,0xBB93),
 'retreat_zero_result':(23,0xBBD0,0xBC00),
 'retreat_exit_result':(23,0xBC16,0xBC3B),
 'surrender_exit':(23,0xBE3F,0xBE78),
 'negotiation_choice':(23,0xBE86,0xBF43),
 'negotiation_exit':(23,0xBF43,0xBFB2),
 'status_effect':(24,0xC08A,0xC116),
 'win_rewards':(24,0xC35D,0xC44F),
 'ruler_predicate':(24,0xD262,0xD283),
}


def analyze(rom_path,out):
    rom=rom_path.read_bytes();tables=DuelTables.from_rom(rom)
    memory=bytearray(65536)
    for bank,start in ((17,0x8000),(23,0xA000),(24,0xC000),(31,0xE000)):
        memory[start:start+8192]=rom[16+bank*8192:16+(bank+1)*8192]
    dis=Disassembler(MPU(memory=memory));ranges=[];listing=[]
    for name,(bank,start,end) in RANGES.items():
        base=0xA000 if bank==23 else 0xC000
        offset=16+bank*8192+start-base
        ranges.append({'name':name,'bank':bank,'cpu_start':start,'cpu_end_exclusive':end,
            'rom_offset':offset,'bytes_hex':rom[offset:offset+end-start].hex(),
            'byte_sha256':hashlib.sha256(rom[offset:offset+end-start]).hexdigest()})
        listing.extend(['',f'; {name}, bank{bank}, file${offset:06X}'])
        pc=start
        while pc<end:
            size,asm=dis.instruction_at(pc);tail=''
            if memory[pc:pc+3]==bytes.fromhex('2007ee'):
                target=int.from_bytes(memory[pc+3:pc+5],'little')
                size=5;tail=f' ; inline far target${target:04X}'
            if pc+size>end:raise ValueError(f'Bad extent at{pc:04X}')
            listing.append(f'${pc:04X} {memory[pc:pc+size].hex(" "):14} {asm}{tail}');pc+=size
    original_health=[tables.template_prg[12*i] for i in range(237)]
    evidence={'rom_sha256':ROM_SHA256,'code_ranges':ranges,'main_action_names':{k:v for k,v in ACTION_NAMES.items() if k<7},
        'tactical_action_names':{k:v for k,v in ACTION_NAMES.items() if k>=7},
        'main_menu_selection':{'navigation_bank':23,'cpu':0xB461,'bytes_hex':memory[0xB461:0xB469].hex(),
            'write_cpu':0xB442,'action_address':0x04BF,
            'chr_evidence':'analysis/phase4/terrain/evidence.json:duel_main_menu'},
        'submenu_selection':{'navigation_cpu':0xB5BB,'bytes_hex':memory[0xB5BB:0xB5BF].hex(),
            'mapping':'B59E reads0012, ADC7, stores04BF atB5A4; indices0/1 become7/8',
            'chr_evidence':'analysis/phase4/terrain/evidence.json:duel_tactics_submenu',
            'native_capture':'analysis/phase4/terrain/core-labels/duel-tactics-submenu.png',
            'capture_scope':'Explicit original-core RAM fixture with separate injection log; not natural gameplay navigation'},
        'template_health':{'bank':17,'cpu_base':0x8000,'record_stride':12,'official_record_count':237,
            'min':min(original_health),'max':max(original_health),'maximum_half':max(original_health)>>1},
        'AI_anomalies':[
            {'cpu':0xB7BF,'bytes_hex':memory[0xB7BF:0xB7C2].hex(),
             'meaning':'JMP F2D7; returns record pointer high byte, not an RNG probability',
             'normal_domain_consequence':'While actorHP<templateHP/2<=49, pointer high>=0x63; category3 gate never succeeds for official template domain'},
            {'cpu':0xB666,'bytes_hex':memory[0xB666:0xB669].hex(),
             'meaning':'A still contains current actorHP; XOR1/TAY indexes04B1+u8(actorHP xor1), including beyond the two HP buffers',
             'not_rewritten_as':'opponentHP or actorIndex xor1'}],
        'fallback_action_table':{'bank':23,'cpu':0xB760,'rom_offset':0x2F770,'bytes':list(tables.fallback_actions),
            'shape':[3,3,8],'dimensions':['opponentHP bins<31/<61/other','actorHP bins<31/<61/other','RNG&7'],
            'category_counts':dict(Counter(tables.fallback_actions))},
        'negotiation_table':{'bank':23,'cpu':0xBFB2,'rom_offset':0x2FFC2,'bytes':list(tables.negotiation_results),
            'shape':[3,3,3,8],'dimensions':['u8(actorIQ+virtue) bins>=180/>=130/other','targetloyalty bins>=80/>=50/other','target permanentHP bins>=80/>=50/other','RNG&7'],
            'result_counts':dict(Counter(tables.negotiation_results))},
        'duration_mechanics':{'address_pair':[0x4B5,0x4B6],'bits0to6':'counter of the category8 ばとう effect','bit7':'AI repeat-selection inhibition marker, not a separately named official status',
            'application':'actor=80; success target gets3..5, with04C3target=2',
            'decay':'each selected actor turn AND7F then subtract1/store if nonzero; clears bit7 in that branch; pure80 persists',
            'strike':'active counter adds20 to numeric roll and adds floor(u8(3*damage)/10) to wrapped damage. Larger roll reduces the usual hit chance.',
            'menu':'active counter rejects main menu category4; AI skips tactic check while counter active'},
        'recovered_groups':['all5 AI stages and their4 formulas','turn selection and periodic reseed','counter application/decay and strike integration','all216 negotiation table cells and outcomes','retreat pursuit/HP/direct results','surrender ruler condition and result3','all weapon/armor reward branches','confirmed HP writeback and zero-HP numeric results'],
        'battle_result_consumer':{'bank':13,'dispatch_cpu':0xC782,'table_cpu':0xC787,
            'targets':[int.from_bytes(rom[16+13*8192+0x787+2*i:16+13*8192+0x789+2*i],'little') for i in range(8)],
            'code0_and1':'C797/C798 local RTS; result1 attack-scene continuation requires separate trace',
            'code2':'C799 experience award then officer byte11 OR3 and far8 A02A active-slot/cache removal',
            'code3':'C7DB opponent prisoner array6F47/6F5B and count0520/0521; far10 A00C loyalty adjustment only; clear active slot',
            'code4to7':'C81F/C886 army counts and troops;0628 XOR80;6FA1 toggle; far10 A006 loyalty adjustment only',
            'scope':'Read-only cross-agent byte/path evidence; this downstream battle bookkeeping is not implemented by DuelLogic'},
        'scope':'Independent high-level game effects; no CPU flags/stack/mapper/display recovery claim. Pending graphics/dialogue remain explicit external work.'}
    assert evidence['AI_anomalies'][0]['bytes_hex']=='4cd7f2'
    assert evidence['AI_anomalies'][1]['bytes_hex']=='4901a8'
    assert evidence['battle_result_consumer']['targets']==[0xC797,0xC798,0xC799,0xC7DB,0xC81F,0xC81F,0xC81F,0xC81F]
    out.mkdir(parents=True,exist_ok=True)
    (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (out/'logic-ranges.asm').write_text('\n'.join(listing)+'\n')
    (out/'tables.json').write_text(json.dumps({'rng':list(tables.rng),'template_health_all256':[tables.template_prg[12*i] for i in range(256)],
        'fallback_actions':list(tables.fallback_actions),'negotiation_results':list(tables.negotiation_results)},indent=2)+'\n')
    print(json.dumps({'code_ranges':len(ranges),'template_health_max':max(original_health),
        'AI_fallback_cells':len(tables.fallback_actions),'negotiation_cells':len(tables.negotiation_results)},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase4/duel');a=p.parse_args();analyze(a.rom,a.out)
