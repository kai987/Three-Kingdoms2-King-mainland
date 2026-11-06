#!/usr/bin/env python3
"""Rebuild the small, pinned native AI formation tables without an emulator."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'game/config/references/original-battle-ai-deployment-v1.json'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SCHEMA = 'tk2-original-battle-ai-deployment-v1'
SPANS = {
    'defender_group_offsets': (8,0xB30E,4,'9b2cf966adf226a8e2028886d77bf2b63fcaa7aa571d5916af87e2c6b7fe2f8e'),
    'attacker_group_offsets': (8,0xB36D,4,'b2f3c5d4cef4b82ac0599dfa620c941a371480c01d12f492bf256ff88c274316'),
    'profiles': (8,0xB3FD,108,'a70cd1fc0a10600d3e662ac844e1c871b7911d255e966307b4914516f88f8cb5'),
}


def require(condition,message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_offset(bank,cpu):
    return 16+bank*8192+(cpu&8191)


def source_tables(rom):
    require(digest(rom)==ROM_SHA,'Pinned local ROM identity required')
    result={}
    for name,(bank,cpu,length,sha) in SPANS.items():
        start=file_offset(bank,cpu);raw=rom[start:start+length]
        require(len(raw)==length and digest(raw)==sha,'AI deployment ROM table mismatch: '+name)
        result[name]=dict(physical_bank=bank,cpu=f'{cpu:04X}',rom_file_offset=start,
                          length=length,hex=raw.hex(),sha256=sha)
    return result


def table_bytes(tables):
    require(type(tables) is dict and set(tables)==set(SPANS),'AI deployment source table set mismatch')
    result={}
    for name,(bank,cpu,length,sha) in SPANS.items():
        row=tables[name]
        require(type(row) is dict and set(row)=={'physical_bank','cpu','rom_file_offset','length','hex','sha256'},
                'AI deployment source fields mismatch: '+name)
        require((row['physical_bank'],row['cpu'],row['rom_file_offset'],row['length'],row['sha256'])
                ==(bank,f'{cpu:04X}',file_offset(bank,cpu),length,sha),'AI deployment source metadata mismatch: '+name)
        require(type(row['hex']) is str,'AI deployment bytes must be hexadecimal')
        raw=bytes.fromhex(row['hex'])
        require(raw.hex()==row['hex'] and len(raw)==length and digest(raw)==sha,
                'AI deployment source bytes mismatch: '+name)
        result[name]=raw
    return result


def build(tables):
    data=table_bytes(tables);profiles=[]
    for profile in range(6):
        counts=[]
        for count in range(1,10):
            offset=profile*18+2*(count-1);a,b=data['profiles'][offset:offset+2]
            groups=[a>>4,a&15,b>>4,b&15]
            require(sum(groups)==count,'AI deployment profile count mismatch')
            counts.append(groups)
        profiles.append(dict(index=profile,side='defenders' if profile<3 else 'attackers',
                             family=profile%3,counts=counts))
    return dict(schema=SCHEMA,rom_sha256=ROM_SHA,
        scope='Native data and instruction-derived rules only; no115-city lineage binding or runtime code.',
        source_tables=deepcopy(tables),
        original_slot_families=[0,1,2,0,2,1,0],
        group_byte_offsets={side:list(data[singular+'_group_offsets'])
                            for side,singular in [('defenders','defender'),('attackers','attacker')]},
        profiles=profiles,
        rules=dict(commander_group=0,commander_point_byte_offset=0,
            noncommander_order='B371: n-1 full adjacent passes; swap when next martial >= current martial; commander excluded',
            profile='B1B0: family + (3 for attackers else0), two bytes per noncommander count1..9',
            zero_noncommanders='No profile read; only commander placed. Native scratch count cache is not cleared.',
            position='B272/B278 commander at offset0; B290/B296 group cursor reads packed_y,x and advances2',
            native_legality='No C447 rectangle, D6B6 occupancy or terrain check; shared remake safety is a separate adaptation',
            rng='No random call or cursor advance in B130/B1B0/B371/B2AE/B312',
            side_order='B130: defending AI first, attacking AI second; skip human controller sides',
            faction='B4D3 fixed slot pointers; profile depends on slot, not the current successor stored in leader byte0'))


def check(reference):
    require(type(reference) is dict and reference.get('schema')==SCHEMA and reference.get('rom_sha256')==ROM_SHA,
            'AI deployment reference identity mismatch')
    require(reference==build(reference.get('source_tables')),'AI deployment derived data or annotations are stale')
    return dict(profiles=6,count_records=54,groups=4,original_slots=7)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path);parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check:
        reference=json.loads(OUTPUT.read_text())
        if args.rom:
            require(reference==build(source_tables(args.rom.read_bytes())),'Pinned ROM rebuild differs')
        print(json.dumps(check(reference),sort_keys=True));return
    require(args.rom is not None,'Use --rom to rebuild; --check needs only the shipped reference')
    reference=build(source_tables(args.rom.read_bytes()));check(reference)
    OUTPUT.write_text(json.dumps(reference,ensure_ascii=False,indent=2)+'\n')
    print(str(OUTPUT))


if __name__=='__main__':
    main()
