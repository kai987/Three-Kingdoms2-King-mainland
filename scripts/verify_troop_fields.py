#!/usr/bin/env python3
"""Compare explicit troop writers to original6502 code, including legal overflow."""
import argparse,hashlib,json,random,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from verify_battle import Oracle,make_record
from source.recovered.officers import ROM_SHA256
from source.recovered.troop_fields import (TroopFieldRules,ai_recruitment_write,raw_attrition_write,
                                          normalize_reserve,garrison_allocation,low10_loss)

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    seed=random.Random(650205);counts=Counter();upper_results=set();samples=[];visited=set()
    def record_case(name,oracle):
        counts[name]+=1;visited.update(oracle.executed)
    def word_bytes(raw):return bytes([raw&255,(raw>>8)&255])
    def clone(oracle):
        m=bytearray(65536);m[:2048]=oracle.bus.ram;m[0x6000:0x8000]=oracle.bus.sram
        return m
    def same_sram(oracle,memory,name):
        assert oracle.bus.sram==memory[0x6000:0x8000],(name,[(hex(i+0x6000),a,b)for i,(a,b)in enumerate(zip(oracle.bus.sram,memory[0x6000:0x8000]))if a!=b][:8])
    def prepare(raw,pair):
        o=Oracle(rom,pair);o.officer(0,make_record(troops=raw,health=97,equipment=0xAC,packed_low=10))
        return o
    lows=(0,1,99,100,255,256,599,600,999,1000,1023)
    for upper in range(64):
        for low in lows:
            raw=(upper<<10)|low
            for loss in (0,1,99,100,1000,65535):
                o=prepare(raw,8);o.set(0x6F8C,0);o.set(0x664,0);o.load(0x20,word_bytes(0x63C0));o.load(0x22,word_bytes(loss))
                m=clone(o);result=TroopFieldRules(m).ai_loss(0,loss);o.run(0xBA4E)
                same_sram(o,m,'AI loss preserving upper6')
                assert bytes(o.get(i)for i in range(0x42C,0x42F))==m[0x42C:0x42F]
                assert o.get(0x6F8B)==m[0x6F8B] and o.get(0x6F8F)==m[0x6F8F]
                assert result['raw_word']>>10==upper
                record_case('ai_loss_preserves_upper6',o)
                o=prepare(raw,12);o.load(0,word_bytes(0x63C0));o.load(2,word_bytes(loss))
                before=bytearray(o.bus.sram);cleared=low10_loss(raw,loss,preserve_upper6=False)
                o.run(0xB68B,stop=lambda pc:pc==0xB6C0)
                before[0x3C8:0x3CA]=word_bytes(cleared['raw_word'])
                assert o.bus.sram==before and o.word(2)==cleared['applied_loss']
                assert cleared['raw_word']>>10==0;record_case('standard_troop_loss_clears_upper6',o)
            for increment in (0,1,99,100,999,1000,1023,65535):
                o=prepare(raw,10);o.load(0x20,word_bytes(0x63C0));o.load(0x22,word_bytes(increment))
                before=bytearray(o.bus.sram);expected=ai_recruitment_write(raw,increment)
                o.run(0xBF95,stop=lambda pc:pc==0xBFBB)
                before[0x3C8:0x3CA]=word_bytes(expected)
                assert o.bus.sram==before,('AI recruit',raw,increment,expected,o.word(0x63C8))
                assert expected>>10==0;record_case('ai_recruit_masks_and_caps999',o)
            o=prepare(raw,10);o.load(0x22,word_bytes(0x63C0));m=clone(o)
            TroopFieldRules(m).refill_invasion(0);o.run(0xA54B,stop=lambda pc:pc==0xA556)
            same_sram(o,m,'Invasion full1000');record_case('invasion_refill_clears_upper6',o)
    # Full two-sided animation writeback including same-ID aliases and oversized
    # bins, with the source preserving the actual high-byte OR rather than AND03.
    for i in range(2048):
        o=Oracle(rom,14);same=i%5==0;ids=(0,0)if same else(0,1)
        o.officer(0,make_record(troops=seed.randrange(65536)))
        if not same:o.officer(1,make_record(troops=seed.randrange(65536)))
        o.load(0x560,ids);o.set(0x5AC,seed.randrange(256));o.set(0x5B7,seed.randrange(256))
        o.load(0x5AD,[seed.choice((0,1,99,100,254,255))for _ in range(10)])
        o.load(0x5B8,[seed.choice((0,1,99,100,254,255))for _ in range(10)])
        m=clone(o);TroopFieldRules(m).commit_attack_groups();o.run(0xCA3F)
        same_sram(o,m,'Attack group writeback');record_case('attack_group_sum_preservation_and_alias',o)
    for raw in [(upper<<10)|low for upper in range(64)for low in lows]:
        for loss in (0,1,80,100,150,255):
            o=prepare(raw,8);o.load(0,word_bytes(0x63C0));o.set(2,loss)
            expected=raw_attrition_write(raw,loss);o.run(0xCE75,stop=lambda pc:pc==0xCE94)
            assert o.word(0x63C8)==expected,('Raw attrition',raw,loss,expected,o.word(0x63C8))
            record_case('raw16_attrition_signed_clamp',o)
    reserves=(0,1,99,100,2500,9899,9900,9901,9999,10000,12001,65535)
    for raw in [(upper<<10)|low for upper in range(64)for low in lows]:
        for reserve in reserves:
            o=prepare(raw,27);o.load(0,word_bytes(0x63C0));o.load(2,word_bytes(raw));o.load(0x42C,word_bytes(reserve))
            expected=normalize_reserve(raw,reserve);o.run(0xD987)
            assert o.word(0x63C8)==expected['raw_word'] and o.word(0x42C)==expected['reserve'],('Normalize',raw,reserve,expected)
            assert o.get(5)==expected['removed_remainder'];record_case('reserve_normalization_raw16',o)
    # Capacity and parent-selected up/down core. Includes valid999/9999 which
    # generates1098 and the separate injected upper-bit matrix.
    for i in range(4096):
        raw=seed.choice((0,1,99,100,599,600,999,1000,1023,1024,1098,32767,32768,65535)) if i<2048 else seed.randrange(65536)
        reserve=seed.choice(reserves);allocate=bool(i&1)
        o=prepare(raw,27);o.set(0x402,0);o.set(0x12,0);o.set(0x6011,0)
        o.set(0x81,128 if allocate else 64);o.load(0x42C,word_bytes(reserve));before=bytearray(o.bus.sram)
        expected=garrison_allocation(raw,reserve,allocate=allocate)
        o.run(0xD805,stop=lambda pc:pc==0xD8B4);before[0x3C8:0x3CA]=word_bytes(expected['raw_word'])
        assert o.bus.sram==before and o.word(0x42C)==expected['reserve'],('Garrison allocation',i,raw,reserve,expected,o.word(0x63C8),o.word(0x42C))
        record_case('garrison_allocation_core_raw16',o)
    for raw,reserve in ((999,9999),(999,10000),(1000,9999)):
        o=prepare(raw,27);o.set(0x402,0);o.set(0x12,0);o.set(0x6011,0);o.set(0x81,128);o.load(0x42C,word_bytes(reserve))
        o.run(0xD805,stop=lambda pc:pc==0xD8B4);actual=o.word(0x63C8)
        samples.append({'input_troops':raw,'input_reserve':reserve,'output_raw_troops':actual,
                        'output_low10':actual&1023,'output_upper6':actual>>10,'output_reserve':o.word(0x42C),
                        'natural_gameplay':False,'legal_numeric_preconditions':raw<=1000 and reserve<=10000,
                        'scope':'Actual complete allocation core before display; synthetic caller RAM, not a natural campaign'})
        record_case('legal_numeric_overflow_demonstration',o)
    assert samples[0]['output_raw_troops']==1098 and samples[0]['output_upper6']==1
    report={'status':'passed','rom_sha256':ROM_SHA256,'case_count':sum(counts.values()),'counts':dict(counts),
            'failures':[],'failed_count':0,'overflow_examples':samples,'original_instruction_locations':len(visited),
            'source_original_code_calls':0,
            'scope':'Independent gameplay word/record/buffer effects versus actual original ROM helper/core instructions; whole SRAM checked for shared-memory APIs.',
            'limits':['CPU flags/stack/mapper and numeric packet/graphics are outside this high-level source contract.',
                      'Prefix stop PCs explicitly exclude subsequent cost/screen/controller work; no render no-op is used.',
                      'Legal numeric inputs prove a producer for bit10, not natural campaign reachability or the meaning of every upper bit.',
                      'No independent training/status flag meaning has been confirmed for upper6 bits.']}
    out=ROOT/'analysis/phase5/troops';out.mkdir(parents=True,exist_ok=True)
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ('status','case_count','counts','overflow_examples')},ensure_ascii=False))
if __name__=='__main__':main()
