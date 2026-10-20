#!/usr/bin/env python3
"""Export address-grounded tactical AI evidence for the analyzed ROM only."""
from pathlib import Path
import argparse,hashlib,json,sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--output',type=Path,default=Path('analysis/ai'))
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'source/recovered'));sys.path.insert(0,str(root/'scripts'))
    import ai
    from inspect_game_data import disassemble
    blob=a.rom.read_bytes();assert hashlib.sha256(blob).hexdigest()==ai.ROM_SHA256
    a.output.mkdir(parents=True,exist_ok=True)
    routines_dir=a.output/'routines';routines_dir.mkdir(exist_ok=True)
    def offset(cpu):
        assert 0xA000<=cpu<0xE000
        return 0x10010+cpu-0xA000
    def listing(start,end):
        if start<0xC000:
            assert end<=0xC000
            return disassemble(blob,8,0xA000,start,end)
        return disassemble(blob,9,0xC000,start,end)
    routines=[]
    for name,entry in ai.ROUTINES.items():
        start=entry['cpu'];end=entry['end_cpu'];raw=blob[offset(start):offset(end)]
        assert entry['file']==offset(start)
        text=f'; Recovered evidence for {name}; file range ${offset(start):06X}-${offset(end)-1:06X}\n'
        if name=='action_suitability':
            text+=listing(start,0xACAE)
            for action in range(16):
                cpu=0xACAE+action*2;o=offset(cpu);target=int.from_bytes(blob[o:o+2],'little')
                text+=f'{o:06X}  b08:${cpu:04X}  {blob[o:o+2].hex(" ").upper():<8}  .word ${target:04X} ; action {action}\n'
            text+=listing(0xACCE,end)
        else:
            text+=listing(start,end)
        path=routines_dir/f'{name}.asm';path.write_text(text)
        routines.append(dict(name=name,**entry,file_end_inclusive=offset(end)-1,
                             raw_hex=raw.hex(' '),raw_sha256=hashlib.sha256(raw).hexdigest(),
                             listing=str(path.relative_to(a.output)),source_function=name))
    (routines_dir/'phase_scan.asm').write_text(listing(0xA02D,0xA099))
    (routines_dir/'inline_dispatch_helper.asm').write_text(listing(0xB517,0xB536))
    strategies=[]
    text=listing(0xA099,0xA0A1)
    for strategy in range(8):
        cpu=0xA0A1+2*strategy;o=offset(cpu);target=int.from_bytes(blob[o:o+2],'little')
        strategies.append(dict(strategy=strategy,pointer_cpu=cpu,pointer_file=o,target_cpu=target,target_file=offset(target)))
        text+=f'{o:06X}  b08:${cpu:04X}  {blob[o:o+2].hex(" ").upper():<8}  .word ${target:04X} ; strategy {strategy}\n'
    (routines_dir/'strategy_dispatch.asm').write_text(text)
    predicates=[]
    for action in range(16):
        cpu=0xACAE+2*action;target=int.from_bytes(blob[offset(cpu):offset(cpu)+2],'little')
        predicates.append(dict(action=action,pointer_cpu=cpu,pointer_file=offset(cpu),
                               predicate_cpu=target,predicate_file=offset(target),ui_name=None))
    assert list(blob[offset(0xAC65):offset(0xAC65)+21])==list(ai.SPECIAL_OFFICERS)
    assert blob[offset(0xAC65)+21]==255
    call_chain=[]
    for cpu,target in [(0xA962,0xB491),(0xA98B,0xA8D3),(0xA98E,0xAE93),(0xA9A8,0xA9CF),
                       (0xA9D5,0xB491),(0xACAB,0xB517),(0xAB87,0xAC7B),(0xACA2,0xB6E5)]:
        raw=blob[offset(cpu):offset(cpu)+3]
        assert raw==bytes([0x20,target&255,target>>8])
        call_chain.append(dict(caller_cpu=cpu,caller_file=offset(cpu),target_cpu=target,
                               target_file=offset(target),raw_hex=raw.hex(' ')))
    rng=blob[offset(0xB5E5):offset(0xB5E5)+256]
    assert len(set(rng))==256
    payload=dict(rom_sha256=ai.ROM_SHA256,source_rom=str(a.rom.resolve()),
                 map={'A000-BFFF':8,'C000-DFFF':9,'E000-FFFF':31},
                 evidence_level='static code, confirmed field UI, actual-ROM CPU oracle; no complete gameplay AI claim',
                 source='../../source/recovered/ai.py',routines=routines,
                 phase_scan={'cpu':0xA02D,'file':offset(0xA02D),'slot_count':20,
                             'control_flag_ram':0x6F8B,'actor_slot_ram':0x6F8C,'status_ram':0x6F8F,
                             'notes':['FF control flag returns; 1 branches to B933 secondary phase.',
                                      'Skips inactive slots and opposite-side sign bits; dispatches remaining actor slots.',
                                      'Low nibble $6FA1[slot] chooses strategy table; runtime strategy domain still needs observation.']},
                 strategy_dispatch={'call_cpu':0xA09E,'helper_cpu':0xB517,'table_cpu':0xA0A1,
                                    'table_file':offset(0xA0A1),'entries':strategies},
                 action_predicate_dispatch={'call_cpu':0xACAB,'helper_cpu':0xB517,'table_cpu':0xACAE,
                                            'table_file':offset(0xACAE),'entries':predicates},
                 basic_pipeline_calls=call_chain,
                 basic_priority=[{'action':code,'minimum_tier':tier,'minimum_resource':budget,'requires_target_raw_troops_nonzero':troops}
                                 for code,tier,budget,troops in [(6,6,8,True),(5,5,8,False),(8,8,10,False),(9,9,9,True),(7,7,8,True)]],
                 special_officers={'table_cpu':0xAC65,'table_file':offset(0xAC65),'ids':list(ai.SPECIAL_OFFICERS),
                                   'level3_suffix_start':0,'level4_suffix_start':11,'level5_suffix_start':17,
                                   'action15_officer_id':109,'action15_name_glyph':'../assets/names/name-109.png'},
                 ai_rng={'cpu':0xB5D5,'table_cpu':0xB5E5,'table_file':offset(0xB5E5),'cursor_ram':0x6F92,
                         'size':256,'sha256':hashlib.sha256(rng).hexdigest(),'is_permutation':True,
                         'same_bytes_as_fixed_bank_rng':rng==blob[0x3E8CA:0x3E9CA]},
                 ram={'x_slots':0x600,'y_slots':0x614,'side_flags':0x628,'conditions':0x650,
                      'active_officer_ids':0x664,'chosen_action':0x6F8D,'chosen_target_slot':0x6F8E,
                      'candidate_slots':0x6FC9,'four_neighbors':0x6FDD,'resource':0x505,'sort_scratch_counter':0x2F},
                 verified_field_usage={'record_byte_1':'武','record_byte_2':'知','record_byte_3':'忠',
                                       'record_byte_11_high4':'experience level','record_u10_at_8':'兵',
                                       'ranking_reads':'raw u16 at bytes8/9 without masking high byte'},
                 limitations=['Tactical bank8/9 subset, not complete strategic/domestic AI.',
                              'Action and terrain class names remain numeric until UI binding is evidenced.',
                              'CPU fixture tests substitute only the dependencies explicitly listed per validation result.',
                              '$B6E5 bank-backed terrain resolver and NMI/game timing are not reconstructed here.'])
    (a.output/'evidence.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f'Wrote {len(routines)} grounded AI routines, 8 strategy entries, 16 predicates to {a.output}')

if __name__=='__main__':main()
