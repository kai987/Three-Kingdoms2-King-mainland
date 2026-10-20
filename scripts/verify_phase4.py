#!/usr/bin/env python3
"""Pin new source, prove IR/table byte provenance, and aggregate validation scopes."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES
from source.recovered.game_enums import ROM_SHA256,TACTIC_NAMES
BRANCHES={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}
def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    programs={}
    for label,name in [('fixed services','services/program.json'),('village services','terrain/service-program.json')]:
        program=json.loads((ROOT/'analysis/phase4'/name).read_text());assert program['rom_sha256']==ROM_SHA256
        for item in program['instructions']:
            pc=item['pc'];offset=item['file'];op,mode=OPS[rom[offset]];size=SIZES[mode]
            assert op==('JSR' if item['op'] in ('DISPATCH','FARCALL') else item['op']),(label,hex(pc))
            value=int.from_bytes(rom[offset+1:offset+size],'little')
            if op in BRANCHES:value=(pc+size+(value if value<128 else value-256))&65535
            if item['op']=='DISPATCH':
                assert value==0xEADE
                for i,target in enumerate(item['targets']):assert int.from_bytes(rom[offset+3+2*i:offset+5+2*i],'little')==target
            else:assert value==item['operand'],(label,hex(pc),value,item['operand'])
            if item['op']=='FARCALL':assert int.from_bytes(rom[offset+3:offset+5],'little')==item.get('inline_target',item.get('target'))
        programs[label]={'instruction_count':len(program['instructions']),'sha256':hashlib.sha256((ROOT/'analysis/phase4'/name).read_bytes()).hexdigest(),'all_bytes_verified':True}
    services=json.loads((ROOT/'analysis/phase4/terrain/service-controller.json').read_text())
    assert services['substate_count']==10 and services['table_end_exclusive']==min(h['entry']for h in services['handlers'])
    for h in services['handlers']:
        offset=services['table_file']+2*h['substate']
        assert int.from_bytes(rom[offset:offset+2],'little')==h['entry']
    areas=['duel','postbattle','services','terrain'];receipts={}
    for area in areas:
        receipt=json.loads((ROOT/'analysis/phase4'/area/'validation.json').read_text())
        assert receipt['status']=='passed',(area,receipt.get('failures'))
        assert not receipt.get('failed_count',receipt.get('failure_count',0))
        receipts[area]=receipt
    integration=json.loads((ROOT/'analysis/phase4/source-integration.json').read_text());assert integration['status']=='passed'
    rea={}
    for pair in (8,23):
        name=ROOT/f'analysis/rea/pairs/pair-{pair:02d}/inspect_native_load_image.json'
        r=json.loads(name.read_text());assert r['structuredContent']['normalized_result']['status']=='verified'
        rea[str(pair)]={'load_image':'verified','source':str(name.relative_to(ROOT))}
    assert (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==rom
    code_files=['source/recovered/game_engine.py','source/recovered/duel_logic.py','source/recovered/postbattle.py',
                'source/recovered/terrain_rules.py','source/recovered/map_service_machine.py',
                'source/recovered/runtime_services.py','source/recovered/mapped_memory.py','source/recovered/game_enums.py']
    files=code_files+['scripts/verify_duel_logic.py','scripts/verify_postbattle.py','scripts/verify_runtime_services.py',
                     'scripts/verify_terrain_rules.py','scripts/verify_source_integration.py']
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in files}
    result={'status':'passed','rom_sha256':ROM_SHA256,'original_and_rebuilt_identical':True,
            'programs':programs,'differential_receipts':{k:{f:v[f]for f in ('status','case_count','scope','limits','comparison_scope','compared_scope','oracle_scope','source_original_code_calls','service_controller_case_count','service_instruction_coverage','service_instruction_total')if f in v}for k,v in receipts.items()},
            'integration_case_count':integration['case_count'],'village_substate_count':10,
            'tactic_names':TACTIC_NAMES,'rea_existing_verified_pairs':rea,'source_and_validator_sha256':hashes,
            'limits':['Legal control-table coverage, executed instruction coverage, semantic-field equivalence and full NES frames are separate scopes.',
                      'Village and older controller IR tests may use explicitly declared original-ROM adapters for unresolved helpers.',
                      'GameEngine semantic APIs and fixed services contain no original-code adapters; graphics and asynchronous completion stay explicit.',
                      'Terrain1 formal name and independent troop upper6-bit meanings remain unresolved.',
                      'This reconstructed source is not the original source nor an independently playable complete game.']}
    out=ROOT/'analysis/phase4/verification.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'passed','programs':programs,'case_counts':{k:v['case_count']for k,v in receipts.items()}},ensure_ascii=False))
if __name__=='__main__':main()
