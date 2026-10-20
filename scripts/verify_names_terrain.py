#!/usr/bin/env python3
"""Execute original 6502 routines against recovered names/terrain models.

Synthetic CPU RAM inputs are used; the original ROM and native snapshots are
read only. This is a subroutine oracle, not a full gameplay/PPU simulation.
"""
from pathlib import Path
import argparse,sys,json,hashlib,random
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--py65-path',type=Path,default=Path('/tmp/nes-reverse-py65'))
    p.add_argument('--out',type=Path,default=ROOT/'analysis/names_terrain')
    a=p.parse_args();sys.path.insert(0,str(a.py65_path));sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'source/recovered'))
    from py65.devices.mpu6502 import MPU
    from trace_startup import Bus
    import game_enums as model
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==model.ROM_SHA256
    results=[]
    def run(bank,pc,extra=None,flags=0,reg=None,stop=0x0200):
        bus=Bus(rom,'alternating');bus.banks=[16,bank,bank+1,31];bus.bank_initialized=[True]*4;bus.protect=0x40
        bus.ram[0x1fe:0x200]=b'\xff\x01';bus.sram[0x3cb]=flags
        for address,value in (extra or {}).items():bus[address]=value
        cpu=MPU(memory=bus,pc=pc);cpu.sp=0xfd;bus.cpu=cpu
        for key,value in (reg or {}).items():setattr(cpu,key,value)
        for step in range(2000):
            bus.pc=cpu.pc;bus.step_no=step;cpu.step()
            if cpu.pc==stop:return bus,cpu,step+1
        raise AssertionError((bank,hex(pc),hex(cpu.pc),'oracle did not stop'))
    def add(routine,offset,purpose,count,**extra):
        results.append(dict(routine=routine,rom_offset=offset,purpose=purpose,cases=count,status='passed',**extra))
    count=0
    for action in range(16):
        ptr=int.from_bytes(rom[0x18ca1+2*action:0x18ca3+2*action],'little');off=0x18010+ptr-0xa000
        n1=rom[off];top=rom[off+1:off+1+n1];off2=off+1+n1;n2=rom[off2];bottom=rom[off2+1:off2+1+n2]
        for row in range(16):
            bus,cpu,steps=run(12,0xabd9,{0x50b:row,0x580+row:action})
            address=0x18c61+4*row
            packet=bytes([n1,rom[address+1],rom[address]])+top+bytes([n2,rom[address+3],rom[address+2]])+bottom+b'\xff'
            assert bytes(bus.ram[0x380:0x380+len(packet)])==packet,(action,row)
            assert bus.ram[0x7e]&4;count+=1
    add('bank12 $ABD9-$AC50','0x018BE9','All16 original tactic name records across all16 displayed positions: exact emitted two-row VRAM packets',count)
    count=0
    for action in range(16):
        for row in range(16):
            bus,cpu,steps=run(12,0xa951,{0x12:row,0x580+row:action},stop=0xa959)
            assert bus.ram[0x543]==action;count+=1
    add('bank12 $A951-$A958 prefix','0x018961','Displayed0580[row] selection is copied directly into0543',count)
    count=0
    for raw in range(256):
        action=raw&15;target=int.from_bytes(rom[0x19052+2*action:0x19054+2*action],'little')
        bus,cpu,steps=run(12,0xb02b,{0x543:raw,**{k:0xa5 for k in range(0x42c,0x435)},0x544:0xa5},stop=target)
        assert bus.ram[0x543]==raw and bus.ram[0x544]==0 and bus.ram[0x42c:0x435]==bytes(9);count+=1
    add('bank12 $B02B-$B041 + fixedbank $EADE','0x01903B','All256 raw action bytes select the corresponding16 effect addresses via action&15; actual inline dispatcher executed',count)
    assert tuple(rom[0x18bd9:0x18be9])==model.TACTIC_ACTION_COSTS
    assert tuple(rom[0x18833:0x1884f])==tuple(x for row in model.MOVEMENT_COST_FIRST for x in row)
    assert tuple(rom[0x1884f:0x1886b])==tuple(x for row in model.MOVEMENT_COST_SECOND for x in row)
    count=0;undefined=0
    for terrain in range(7):
        for affinity in range(4):
            for selector in range(256):
                cost=model.movement_cost(terrain,affinity,selector)
                bus,cpu,steps=run(12,0xa7e7,{0x509:0,0x664:0,0x63c:selector,0x505:6},flags=affinity<<2,reg={'a':terrain})
                assert cpu.x==cost and cpu.a==(6-cost)&255 and bool(cpu.p&cpu.CARRY)==(6>=cost),(terrain,affinity,selector)
                count+=1;undefined+=affinity==3
    rng=random.Random(0x6502)
    # Table boundary6 plus varied unrelated flag bits and AP borrow boundaries.
    for terrain in range(7):
        for affinity in range(4):
            for selector in [0,5,6,255]:
                cost=model.movement_cost(terrain,affinity,selector)
                for ap in sorted(set([0,1,2,3,4,5,6,255,max(0,cost-1),cost,min(255,cost+1),rng.randrange(256)])):
                    flags=(rng.randrange(256)&0xf3)|(affinity<<2)
                    bus,cpu,steps=run(12,0xa7e7,{0x509:0,0x664:0,0x63c:selector,0x505:ap},flags=flags,reg={'a':terrain})
                    assert cpu.x==cost and cpu.a==(ap-cost)&255 and bool(cpu.p&cpu.CARRY)==(ap>=cost)
                    count+=1;undefined+=affinity==3
    add('bank12 $A7E7-$A822','0x0187F7','7 terrain rows ×4 affinities ×all256 RAM063C selector bytes; additional AP borrow/flag boundaries',count,undefined_affinity3_cases=undefined,selector_name='selector_byte (RAM063C[slot]); bank13 DB03 refreshes it from troops_low10//100, orFF for empty slots')
    count=0;observed=set();samples=[];coordinates=set()
    for chunk in range(120):
        for x,y in [(0,0),(15,0),(0,14),(15,14),(0,15),(15,15),(7,7),(8,8),(15,8)]:coordinates.add((chunk,x,y))
    # Include every distinct tile byte from all120 source chunks, not only valid
    # map cells; metadata/sentinel behavior is explicitly exercised as raw lookup.
    first_tile={}
    for chunk in range(120):
        for y in range(16):
            for x in range(16):
                data=model.map_terrain(rom,[chunk]*4,x,y);first_tile.setdefault(data['tile_id'],(chunk,x,y))
    coordinates.update(first_tile.values())
    for chunk,x,y in sorted(coordinates):
        expected=model.map_terrain(rom,[chunk]*4,x,y)
        for entry,key in [(0xb6ef,'raw_class'),(0xb6e5,'ai_class')]:
            bus,cpu,steps=run(8,entry,{0xa8:0xaa,0xa9:0,0xaa:chunk,0xab:chunk,0xac:chunk,0xad:chunk,0x20:x,0x21:y})
            assert cpu.a==expected[key],(chunk,x,y,hex(entry),cpu.a,expected)
            assert bus.banks[0]==((rom[0x118cb+chunk]&63)%32);count+=1
        observed.add(expected['raw_class'])
        if len(samples)<9:samples.append(expected)
    chunks=[16,18,17,19]
    for y in range(32):
        for x in range(32):
            expected=model.map_terrain(rom,chunks,x,y)
            for entry,key in [(0xb6ef,'raw_class'),(0xb6e5,'ai_class')]:
                bus,cpu,steps=run(8,entry,{0xa8:0xaa,0xa9:0,0xaa:chunks[0],0xab:chunks[1],0xac:chunks[2],0xad:chunks[3],0x20:x,0x21:y})
                assert cpu.a==expected[key],(chunks,x,y,hex(entry),cpu.a,expected);count+=1
            observed.add(expected['raw_class'])
    add('bank8 $B6EF-$B74A / $B6E5-$B6EE','0x0116FF / 0x0116F5','All120 chunk pointers/banks; every tile byte present in source chunks; complete32×32 four-quadrant scene raw and AI-normalized lookups',count,tile_byte_values_covered=len(first_tile),raw_classes_observed=sorted(observed),examples=samples)
    # Preserve the original3-entry glyph table overrun evidence for raw affinity3.
    glyph_table=rom[0x33657:0x3365d];count=0;invalid_outputs=set()
    for flags in range(256):
        bus,cpu,steps=run(25,0xb630,{0x10:0xc0,0x11:0x63},flags=flags)
        affinity=(flags>>2)&3;expected=rom[0x33657+2*affinity:0x33659+2*affinity]
        assert bytes(bus.ram[0x38b:0x38d])==expected
        if affinity==3:invalid_outputs.add(bytes(expected).hex(' ').upper())
        count+=1
    add('bank25 $B630 affinity glyph selector','0x033640','All256 packed flags;64 affinity3 cases read past the three documented original glyph entries, rather than defining a fourth name',count,glyph_table_rom_offset='0x033657',valid_three_entry_hex=glyph_table.hex(' ').upper(),affinity3_following_bytes=sorted(invalid_outputs))
    count=0
    for high in range(256):
        for low in [0,1,255]:
            for loss in [0,1,65535]:
                remaining=max(0,low+((high&3)<<8)-loss)
                bus,cpu,steps=run(12,0xb68b,{0:0xc0,1:0x63,2:loss&255,3:loss>>8,0x63c8:low,0x63c9:high},stop=0xb6c0)
                assert bus.sram[0x3c8:0x3ca]==remaining.to_bytes(2,'little')
                assert bus.sram[0x3c9]&0xfc==0;count+=1
    add('bank12 $B68B-$B6BF writeback prefix','0x01969B','All256 raw troop high bytes ×3 low-byte boundaries ×loss0/1/65535; upper6 bits cleared even on zero loss',count)
    count=0
    for high in range(256):
        for low in [0,99,100,255]:
            bus,cpu,steps=run(8,0xadcf,{0x29:0,0x6f8c:0,0x664:0,0x504:0,0x4d8:255,0x63c8:low,0x63c9:high})
            assert bool(cpu.p&cpu.CARRY)==(high!=0 or low>=100);count+=1
    add('bank8 $ADCF-$ADFD tactic11 predicate','0x010DDF','All256 raw troop high bytes ×4 low-byte boundaries; raw high bits remain observable to AI troop predicate',count,example='raw troops0x0400: UI low10 value0 but this AI troop predicate is true')
    payload={'status':'passed','rom_sha256':model.ROM_SHA256,'oracle':'py65 1.2.0 executing original6502 instructions; synthetic RAM and mapper bus, original ROM read only','case_count':sum(r['cases']for r in results),'results':results,'limitations':['This verifies recovered packet/index/lookup/cost behavior, not full gameplay effects of each tactic.','Terrain formal names remain separate visual inferences; class1 name remains unresolved.','Affinity3 zero costs and glyph overrun are raw invalid-encoding observations, not a legitimate extra ability.','Map lookup metadata/unused rows are exercised mechanically and are not asserted to be traversable.']}
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'validation.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f'Passed {payload["case_count"]} actual-ROM name/terrain cases; wrote {a.out}/validation.json')

if __name__=='__main__':main()
