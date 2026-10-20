#!/usr/bin/env python3
"""Reproduce a real allocation overflow in the unchanged ROM/Nestopia core.

Two valid numeric SRAM words are changed explicitly; all later progression is
ordinary game-controller input, including the final commit. No ROM or RAM patch.
"""
import argparse,ctypes as C,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_runtime import Runtime
from source.recovered.officers import ROM_SHA256

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/troops/core-fixture');a=p.parse_args()
    assert hashlib.sha256(a.rom.read_bytes()).hexdigest()==ROM_SHA256
    parent=ROOT/'analysis/phase5/runtime/city-info/menu-1.state';r=Runtime(a.rom,a.out)
    officer=131;off=0x3C0+12*officer;city=11;checkpoints=[]
    def capture(label):
        r.snapshot(label);m=r.memory(2);s=r.memory(0)
        item={'label':label,'frame':r.frames,'city_state':list(m[0x400:0x403]),
              'cursor':m[0x12],'raw_troops':int.from_bytes(s[off+8:off+10],'little'),
              'working_reserve':int.from_bytes(m[0x42C:0x42E],'little'),
              'city_reserve':int.from_bytes(s[32*city+12:32*city+14],'little')}
        item['low10']=item['raw_troops']&1023;item['upper6']=item['raw_troops']>>10
        checkpoints.append(item);return item
    try:
        r.load_state(parent)
        sram=(C.c_ubyte*8192).from_address(r.core.retro_get_memory_data(0))
        patches={0x6000+off+8:231,0x6000+off+9:3,0x6000+32*city+12:171,0x6000+32*city+13:38}
        for address,value in patches.items():sram[address-0x6000]=value
        # Cao Cao1000->999 and city reserve9999->9899, both normal numeric domains.
        r.run(30);r.run(2,['right']);r.run(20);r.run(2,['a']);r.run(180)
        capture('fee-message')
        for label,buttons in [('quantity',['a']),('quantity-up',['up']),
            ('confirm-quantity',['a']),('recruitment-animation',['a'])]:
            r.run(2,buttons);r.run(180);capture(label)
        r.run(500);r.run(2,['a']);r.run(240);before=capture('allocation-ready')
        assert before['city_state']==[3,13,11]and before['raw_troops']==999
        assert before['working_reserve']==9999
        r.run(2,['right']);r.run(60);overflow=capture('allocation-overflow')
        assert overflow['raw_troops']==1098 and overflow['low10']==74 and overflow['upper6']==1
        assert overflow['working_reserve']==9900 and overflow['city_reserve']==9999
        for _ in range(3):r.run(2,['down']);r.run(12)
        assert r.memory(2)[0x12]==3
        r.run(2,['a']);r.run(240);committed=capture('committed-overflow')
        assert committed['city_state'][:2]==[0,1]
        assert committed['raw_troops']==1098 and committed['city_reserve']==9900
        # Sprite-independent field evidence: native allocation row uses raw16.
        # Other officer-list display helpers mask tolow10, checked separately.
        files={}
        for label in ('allocation-ready','allocation-overflow','committed-overflow'):
            for suffix in ('.png','-ram.bin','-sram.bin','.state'):
                path=a.out/(label+suffix);files[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        result={'status':'passed','rom_sha256':ROM_SHA256,'rom_modified':False,'natural_gameplay':False,
                'parent_state':str(parent.relative_to(ROOT)),
                'parent_state_sha256':hashlib.sha256(parent.read_bytes()).hexdigest(),
                'sram_patches':{f'{k:04X}':v for k,v in patches.items()},'ram_patches':{},
                'patch_meaning':['officer131 initial troop1000->999','city11 reserve9999->9899'],
                'core':r.info,'frames':r.frames,'events':r.events,'checkpoints':checkpoints,'artifact_sha256':files,
                'conclusion':'Original controller writes bit10 from ordinary arithmetic and retains raw1098 after actual allocation commit.',
                'limits':['The numeric conditions are valid but injected; no natural campaign path to these preconditions is claimed.',
                          'This proves a producer of upper bits, not an independent training/status flag field.',
                          'libretro memory3 VRAM is unavailable; pixels, RAM, SRAM and serialized core are retained.']}
        (a.out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':'passed','frames':r.frames,'overflow':overflow,'committed':committed},ensure_ascii=False))
    finally:r.close()
if __name__=='__main__':main()
