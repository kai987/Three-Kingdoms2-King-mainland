#!/usr/bin/env python3
"""Check state-table/IR provenance and aggregate the separate validation scopes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import OPS,SIZES
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BRANCHES={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args()
    blob=a.rom.read_bytes();assert hashlib.sha256(blob).hexdigest()==SHA
    controller_specs=[('battle_fsm',12,0xA02E,16,'state-catalog.json'),
                      ('duel_fsm',23,0xB118,22,'state_machine.json'),
                      ('attack_fsm',14,0xA06F,11,'state-catalog.json')]
    controllers=[]
    for area,pair,table,count,catalog_name in controller_specs:
        folder=ROOT/'analysis'/area
        catalog=json.loads((folder/catalog_name).read_text())
        program=json.loads((folder/'program.json').read_text())
        validation=json.loads((folder/'validation.json').read_text())
        assert validation['status']=='passed', (area,validation['status'])
        assert not validation.get('failed_count',validation.get('failure_count',0))
        states=catalog['states'];assert len(states)==count
        def offset(pc):
            if pc>=0xE000:return 0x3E010+pc-0xE000
            bank=pair+int(pc>=0xC000)
            return 16+8192*bank+pc-(0xC000 if pc>=0xC000 else 0xA000)
        for state in states:
            entry=state.get('entry_cpu',state.get('entry'))
            o=offset(table+2*state['state'])
            assert int.from_bytes(blob[o:o+2],'little')==entry,(area,state['state'])
        assert table+2*count==min(s.get('entry_cpu',s.get('entry')) for s in states)
        for item in program['instructions']:
            pc=item['pc'];o=offset(pc)
            op,mode=OPS[blob[o]];size=SIZES[mode]
            expected_op='JSR' if item['op'] in ('DISPATCH','FARCALL') else item['op']
            assert op==expected_op,(area,hex(pc),op,item['op'])
            value=int.from_bytes(blob[o+1:o+size],'little')
            if op in BRANCHES:value=(pc+size+(value if value<128 else value-256))&65535
            if item['op']=='DISPATCH':
                assert value==0xEADE
                for i,target in enumerate(item['targets']):
                    target_o=offset(pc+3+2*i)
                    assert int.from_bytes(blob[target_o:target_o+2],'little')==target
            else:assert value==item['operand'],(area,hex(pc),value,item['operand'])
            if item['op']=='FARCALL':
                assert value==0xEE07
                target_o=offset(pc+3)
                assert int.from_bytes(blob[target_o:target_o+2],'little')==item.get('inline_target',item.get('target'))
        controllers.append({'area':area,'main_states':count,'lifted_ir_instructions':len(program['instructions']),
                            'entry_case_count':validation['case_count'],
                            'semantic_case_count':validation.get('semantic_case_count',0),
                            'tick_case_count':validation.get('tick_case_count',0),
                            'hp_writeback_case_count':len(validation.get('writeback_cases',[])),
                            'dispatch_case_count':validation.get('dispatch_case_count',0),
                            'fixed_helper_case_count':validation.get('fixed_helper_case_count',0),
                            'executed_ir_instructions':validation.get('instruction_ir_coverage'),
                            'validation_status':validation['status'],
                            'program_sha256':hashlib.sha256((folder/'program.json').read_bytes()).hexdigest(),
                            'scope':validation.get('scope')})
    names=json.loads((ROOT/'analysis/names_terrain/validation.json').read_text())
    shared=json.loads((ROOT/'analysis/phase3/shared-helper-validation.json').read_text())
    context=json.loads((ROOT/'analysis/phase3/game-engine-context-validation.json').read_text())
    assert names['status']==shared['status']=='passed'
    assert context['status']=='passed'
    replay=json.loads((ROOT/'analysis/runtime/phase3/cold-replay/validation.json').read_text())
    assert all(c['changed_pixels']==0 and c['sram_differences']==0 and c['control_state_equal'] for c in replay['checkpoints'])
    rea=json.loads((ROOT/'analysis/rea/pairs/pair-23/inspect_native_load_image.json').read_text())
    assert rea['structuredContent']['normalized_result']['status']=='verified'
    rebuilt=(ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes();assert rebuilt==blob
    duel_core=json.loads((ROOT/'analysis/duel_fsm/runtime/injected-core/validation.json').read_text())
    assert duel_core['checks_passed'] and duel_core['completed_duel_return']
    assert duel_core['rom_modified'] is False and duel_core['natural_gameplay'] is False
    result={'status':'passed','rom_sha256':SHA,'original_and_rebuilt_identical':True,
            'controllers':controllers,'names_terrain_cases':names['case_count'],'shared_helper_cases':shared['case_count'],
            'rea_pair23_load_image':'verified','original_rom_replay':replay,
            'game_engine_context':context,
            'duel_core_fixture':{'frames':duel_core['frames'],'natural_gameplay':False,'rom_modified':False,
                                 'checks':duel_core['checks'],'checks_passed':True,
                                 'vram_readback':'unavailable: this core returns an empty libretro memory3 region'},
            'limits':['All valid entries are covered by fixtures; executed IR coverage is reported separately from static coverage.',
                      'External ROM helper adapters and declared NMI barrier bypasses are not independent source recovery.',
                      'Controller ticks and complete-emulator video frames are different scopes.',
                      'Formal names of terrain1/6/7/8 and independent meaning of troop upper6 bits remain unresolved.']}
    out=ROOT/'analysis/phase3/verification.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'controllers':controllers,'names_terrain_cases':names['case_count'],'shared_helper_cases':shared['case_count']},ensure_ascii=False))

if __name__=='__main__':main()
