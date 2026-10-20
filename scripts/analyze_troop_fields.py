#!/usr/bin/env python3
"""Retain precise troop-word producer/consumer provenance without naming flags."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction,OPS,SIZES
from source.recovered.officers import ROM_SHA256

RANGES=[
 ('ai_loss',8,0xA000,0xBA4E,0xBAB3,'Low10 saturation loss; retains old high6; writes loss buffer and AI result bytes.'),
 ('standard_loss_prefix',12,0xA000,0xB68B,0xB6C0,'Low10 saturation loss; replaces byte9 and discards high6 before later XP.'),
 ('ai_recruitment_prefix',10,0xA000,0xBF95,0xBFBB,'Adds to rawword, masks result to10 bits and caps999; prior amount and later AP excluded.'),
 ('invasion_refill_prefix',10,0xA000,0xA54B,0xA556,'WritesE8/03: exactly1000; prior funding and later AP excluded.'),
 ('attack_animation_writeback',15,0xC000,0xCA3F,0xCAC8,'Health plus10 animation groups per side; preserve existing high6 with OR of sum-high.'),
 ('raw_attrition_prefix',9,0xC000,0xCE75,0xCE94,'Full-word subtraction with highbyte BPL clipping; later slot loop excluded.'),
 ('garrison_allocation_core',28,0xC000,0xD805,0xD8B4,'Actual troop/reserve controller writes before numeric packet and display.'),
 ('reserve_normalization',28,0xC000,0xD987,0xDA02,'Divide raw16 by100 and transfer remainder subject toreserve cap10000.')]

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    out=ROOT/'analysis/phase5/troops';out.mkdir(parents=True,exist_ok=True);entries=[]
    for name,bank,base,start,end,meaning in RANGES:
        offset=16+bank*8192+start-base;pc=start;nodes=[];lines=[f';{meaning}',';Exact bounded entry/prefix; no linear-data-as-code claim.']
        while pc<end:
            pos=16+bank*8192+pc-base;op,mode=OPS[rom[pos]];size=SIZES[mode]
            assert op!='?'and pc+size<=end,(name,hex(pc))
            _,assembly=instruction(rom,pos,pc)
            nodes.append({'bank':bank,'pc':pc,'file':pos,'op':op,'mode':mode,'raw_hex':rom[pos:pos+size].hex(' ')})
            lines.append(f'{pos:06X} b{bank:02d}:${pc:04X} {rom[pos:pos+size].hex(" ").upper():<10} {assembly}')
            pc+=size
        file=name+'.asm';(out/file).write_text('\n'.join(lines)+'\n')
        entries.append({'name':name,'bank':bank,'cpu_start':start,'cpu_end_exclusive':end,'file':offset,
                        'raw_sha256':hashlib.sha256(rom[offset:offset+end-start]).hexdigest(),
                        'meaning':meaning,'instructions':nodes,'listing':file})
    # Raw search is inventory only. It deliberately retains possible data hits,
    # rather than labelling all immediate8/9 patterns as proven record access.
    candidates=[]
    for bank in range(32):
        data=rom[16+bank*8192:16+(bank+1)*8192]
        for i in range(8191):
            if data[i:i+2]in (bytes([160,8]),bytes([160,9])):
                candidates.append({'bank':bank,'file':16+bank*8192+i,'immediate':data[i+1],
                                   'next_bytes':data[i+2:i+18].hex(' '),'status':'raw byte-pattern candidate; code/data and pointer ownership must be validated'})
    initial=rom[0x22010:0x22010+237*12]
    snapshots=[]
    for prefix in ('analysis/runtime/phase3/cold-replay/army-third','analysis/runtime/phase3/battle-tactics-true',
                   'analysis/phase5/runtime/city-info/menu-0'):
        data=(ROOT/(prefix+'-sram.bin')).read_bytes();words=[int.from_bytes(data[0x3C8+12*i:0x3CA+12*i],'little')for i in range(237)]
        snapshots.append({'snapshot':prefix,'nonzero_upper6_ids':[i for i,v in enumerate(words)if v>>10],
                          'scope':'Observed imported original-game snapshots; absence is not proof for every future state.'})
    result={'rom_sha256':ROM_SHA256,'entries':entries,'raw_pattern_candidates':candidates,
            'initial_officer_records':237,'initial_nonzero_upper6':sum(bool(initial[12*i+9]&252)for i in range(237)),
            'observed_snapshots':snapshots,
            'conclusion':{'low10':'Confirmed ordinary officer-list/battle troop view',
                          'upper6':'A real numerical-overflow producer is confirmed; separate training/status flag interpretation is not established.',
                          'producer':'D805/D987: troop999,reserve9999,allocate100→1098; retained byB431 allocation commit.',
                          'mechanics':'Preserve, clear, raw16 addition/subtraction/comparison and masked10 reads are path dependent.'},
            'limits':['Raw pattern inventory is not complete verified instruction CFG coverage.',
                      'An overflow example is an explicitly controlled core fixture, not a natural campaign trajectory.',
                      'Only the proven routines/prefixes are reimplemented; unknown upper-bit purposes are not guessed.']}
    (out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'entries':len(entries),'bounded_instructions':sum(len(e['instructions'])for e in entries),'raw_candidates':len(candidates),'initial_upper6_nonzero':result['initial_nonzero_upper6']},ensure_ascii=False))
if __name__=='__main__':main()
