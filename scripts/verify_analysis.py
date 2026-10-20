#!/usr/bin/env python3
"""Independent cross-artifact checks, preserving the original ROM."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
KNOWN='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'

def sha(x): return hashlib.sha256(x).hexdigest()
def read_json(p): return json.loads((ROOT/p).read_text())

def verify(rom):
    raw=rom.read_bytes();assert sha(raw)==KNOWN
    manifest=read_json('analysis/rom/manifest.json');assert manifest['rom_sha256']==KNOWN
    assert (ROOT/'analysis/rom/prg.bin').read_bytes()==raw[16:0x40010]
    assert (ROOT/'analysis/rom/chr.bin').read_bytes()==raw[0x40010:]
    for v in manifest['prg']['banks']:
        b=(ROOT/'analysis/rom/prg-banks'/f"bank-{v['bank']:02d}.bin").read_bytes()
        assert b==raw[v['file_offset']:v['file_offset']+v['length']]
    order=read_json('source/byte-source/order.json');result=bytearray()
    for v in order['chunks']:
        values=[]
        for line in (ROOT/'source/byte-source'/v['file']).read_text().splitlines():
            code=line.split(';',1)[0]
            values.extend(int(x,16) for x in re.findall(r'\$([0-9A-F]{2})',code))
        assert len(result)==v['offset'] and len(values)==v['length'] and sha(bytes(values))==v['sha256']
        result.extend(values)
    assert result==raw and (ROOT/'build/三国志2超级版.rebuilt.nes').read_bytes()==raw
    tables=read_json('analysis/game_data/recovered_tables.json')
    for name in ['first_table','second_table']:
        table=tables[name];assert len(table['records'])==table['record_count']
        for v in table['records']:
            offset=int(v['rom_offset'],16)
            assert bytes(v['bytes'])==raw[offset:offset+table['record_size']]
    glyphs=read_json('analysis/assets/names/name-glyph-index.json')
    assert len(glyphs['names'])==237
    for v in glyphs['names']:
        assert v['record_file_offset']==0x22dc4+v['name_id']*13
        assert bytes.fromhex(v['record_hex'])==raw[v['record_file_offset']:v['record_file_offset']+13]
        assert (ROOT/'analysis/assets/names'/v['image']).exists()
    static=read_json('analysis/disassembly/fixed-bank.json')
    assert len(static['state_pointer_candidates'])==15 and not static['conflicts']
    for v in static['instructions']:
        assert bytes.fromhex(v['bytes_hex'])==raw[v['rom_offset']:v['rom_offset']+v['size']]
    asset=read_json('analysis/assets/validation.json');assert asset['verified'] and asset['source_sha256']==KNOWN
    algorithms=read_json('analysis/game_data/algorithm-validation.json')
    assert algorithms['status']=='passed' and algorithms['rom_sha256']==KNOWN and algorithms['case_count']==3699
    trace=read_json('analysis/trace/verification.json')
    assert trace['rom_sha256']==KNOWN and trace['original_rom_still_matches_recorded_hash']
    assert trace['sram_copy_checks_passed'] and trace['preserved_sram_6f43_check_passed']
    assert all(v['instruction_bytes_match_input_rom'] and v['count_consistent'] for v in trace['runs'])
    protocols=read_json('analysis/game_data/call-protocol-validation.json')
    assert protocols['status']=='passed' and protocols['case_count']==15
    image=read_json('analysis/rea/mcp/inspect_native_load_image.json')['structuredContent']['normalized_result']
    assert image['status']=='verified' and all(v['matched'] for v in image['checks'])
    assert image['target_sha256']==manifest['prg']['banks'][31]['sha256']
    assert sha(rom.read_bytes())==KNOWN
    report={'verified':True,'rom_sha256':KNOWN,'rom_bytes':len(raw),'source_chunks':len(order['chunks']),
            'prg_banks':32,'chr_tiles':16384,'name_records':237,'first_table_records':30,
            'algorithm_cases':3699,'call_protocol_cases':15,'static_candidate_instructions':static['instruction_count'],
            'static_candidate_bytes':static['candidate_code_bytes'],'rea_load_image':'verified',
            'original_rom_unchanged':True,
            'limitations':['Byte identity is not source recovery or full-game validation.',
                           'PPU/NMI/audio/full gameplay are outside the bounded CPU model.',
                           'Officer field labels and first-table city semantics remain partially unresolved.']}
    (ROOT/'analysis/verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);verify(p.parse_args().rom)
