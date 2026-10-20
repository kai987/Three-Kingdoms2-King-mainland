#!/usr/bin/env python3
"""Mutation/boundary oracle for actual officer field read/write routines.

py65 CPU + existing read-only mapper bus; synthetic input RAM, unchanged ROM.
This is not a claim that edited gameplay/save states were used for screenshots.
"""
from pathlib import Path
import argparse,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--py65-path',type=Path,default=Path('/tmp/nes-reverse-py65'))
    p.add_argument('--out',type=Path,default=ROOT/'analysis/officer_fields');a=p.parse_args()
    sys.path.insert(0,str(a.py65_path));sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'source/recovered'))
    from py65.devices.mpu6502 import MPU
    from trace_startup import Bus
    from officers import OfficerRecord,ROM_SHA256,initial_officers
    blob=a.rom.read_bytes();assert hashlib.sha256(blob).hexdigest()==ROM_SHA256
    initial=initial_officers(blob);baseptr=0x63c0;results=[]
    def run(bank,pc,record,mode=0,extra=None,stop=0x200,reg=None):
        bus=Bus(blob,'alternating');bus.banks=[16,bank,bank+1,31] if bank in (23,25,29) else [16,bank-1,bank,31]
        bus.bank_initialized=[True]*4;bus.protect=0x40;bus.sram[0x3c0:0x3cc]=record.raw
        for zp in [0,0x10,0x1c]:bus.ram[zp]=baseptr&255;bus.ram[zp+1]=baseptr>>8
        bus.ram[0x479]=mode;bus.ram[0x1fe:0x200]=b'\xff\x01'
        for addr,value in (extra or {}).items():bus.ram[addr]=value
        cpu=MPU(memory=bus,pc=pc);cpu.sp=0xfd;cpu.x=0;cpu.a=0;bus.cpu=cpu
        for key,value in (reg or {}).items():setattr(cpu,key,value)
        for step in range(20000):
            bus.pc=cpu.pc;bus.step_no=step;cpu.step()
            if cpu.pc==stop:return bus,cpu,step+1
        raise AssertionError((bank,hex(pc),'did not return',hex(cpu.pc)))
    def text_digits(row,column,width):
        text=''
        for tile in row[column:column+width]:
            if tile==1:text+=' '
            elif tile==0x32:text+='-'
            else:
                assert 0x76<=tile<=0x7f,tile;text+=str(tile-0x76)
        return text
    cases=[(i,o) for i,o in enumerate(initial)]
    template=initial[0]
    for field in range(5):
        for value in [0,1,9,10,99,100,255]:cases.append((0,template.with_raw_byte(field,value)))
    for value in [0,1,49,50,999,1000,3500,49999,65535]:
        raw=bytearray(template.raw);raw[6:8]=value.to_bytes(2,'little');cases.append((0,OfficerRecord(raw)))
    for value in [0,1,255,256,999,1000,1023,1024,3500,65535]:
        raw=bytearray(template.raw);raw[8:10]=value.to_bytes(2,'little');cases.append((0,OfficerRecord(raw)))
    count=0;examples=[]
    for ident,officer in cases:
        for mode in (0,1):
            bus,cpu,steps=run(29,0xbb28,officer,mode=mode)
            row=bus.ram[0x160:0x1a0]
            for i in range(4):
                output=text_digits(row,43+3*i,2)
                expect='--' if i==3 and officer.raw[i]==100 else f'{officer.raw[i]%100:2d}'
                assert output==expect,(i,officer.raw[i],output,expect)
            if mode==0:
                assert text_digits(row,55,2)==f'{officer.virtue%100:2d}'
                assert int(text_digits(row,58,3))==officer.experience_display
            else:
                assert int(text_digits(row,55,3))==officer.experience_display
                assert int(text_digits(row,59,4))==officer.troops_display
            count+=1
            if len(examples)<4:examples.append({'officer_id':ident,'mode':mode,'raw_hex':officer.raw.hex(' ').upper(),'rendered_tiles':list(row),'instructions':steps})
    results.append({'routine':'bank29 $BB28-$BC31','rom_offset':'0x03BB38','purpose':'All237 initial officers plus single-field boundary mutations; exact output tile digits and loyalty sentinel','cases':count,'status':'passed','examples':examples})
    count=0
    for flags in range(256):
        o=template.with_raw_byte(11,flags);bus,cpu,steps=run(25,0xb630,o)
        code=o.terrain_affinity_code;top=blob[0x33657+2*code:0x33659+2*code]
        assert bus.ram[0x38b:0x38d]==top
        if code<3:count+=1
    results.append({'routine':'bank25 $B630','rom_offset':'0x033640','purpose':'Terrain bits2..3 extraction across all flags;192 valid categories and64 undefined-category decoder cases','cases':256,'valid_category_cases':count,'status':'passed'})
    count=0
    for flags in range(256):
        bus,cpu,steps=run(25,0xb5a6,template.with_raw_byte(11,flags))
        assert bus.ram[0x391]==0x76+((flags>>4)+1)%10;count+=1
    results.append({'routine':'bank25 $B5A6','rom_offset':'0x0335B6','purpose':'Level display derives high nibble+1; invalid tiers>=9 truncate to one decimal digit as actual code does','cases':count,'status':'passed'})
    count=0
    for equipment in range(256):
        o=template.with_raw_byte(10,equipment);bus,cpu,steps=run(25,0xb770,o)
        for item,column,add in [(equipment&31,14,0),(24+(equipment>>5),26,64)]:
            ptr=0x8000+int.from_bytes(blob[0x21b22+2*item:0x21b24+2*item],'little');off=0x20010+ptr-0x8000
            expected=bytes(t if t==1 else (t+add)&255 for t in blob[off+9:off+17])
            assert bus.ram[0x380+column:0x380+column+8]==expected,(equipment,item)
        count+=1
    results.append({'routine':'bank25 $B770','rom_offset':'0x033780','purpose':'Byte10 lower5/high3 independently select weapon vs armor pointer record','cases':count,'status':'passed'})
    count=0
    for flags in range(256):
        for city in [0,1,29]:
            o=template.with_raw_byte(11,flags);bus,cpu,steps=run(26,0xc099,o,extra={0x40e:city},stop=0xc0a8)
            assert bytes(bus.sram[0x3c0:0x3cc])==o.with_status(0).with_raw_byte(5,city).raw;count+=1
    results.append({'routine':'bank26 $C099-$C0A7 prefix','rom_offset':'0x0340A9','purpose':'Roaming status0 preserves terrain/tier bits and writes city byte5','cases':count,'status':'passed'})
    count=0
    for equipment in range(256):
        o=template.with_raw_byte(10,equipment)
        for weapon in [0,7,8,15,16,23]:
            bus,cpu,steps=run(24,0xc417,o,extra={0x10:weapon},stop=0xc425)
            assert bytes(bus.sram[0x3c0:0x3cc])==o.with_weapon(weapon).raw;count+=1
        for armor in range(8):
            bus,cpu,steps=run(28,0xca27,o,extra={0x10:31,0x44c:armor<<5},stop=0xca36)
            assert bytes(bus.sram[0x3c0:0x3cc])==o.with_armor(armor).raw;count+=1
    results.append({'routine':'bank24 $C417 / bank28 $CA27 prefixes','rom_offsets':['0x030427','0x038A37'],'purpose':'Actual weapon/armor setters preserve the other packed equipment field','cases':count,'status':'passed'})
    baseline=blob[0x22010:0x22b2c];runtime=[]
    for label in ['game-start','picked-ruler','military-selection']:
        path=ROOT/'analysis/runtime'/f'{label}-sram.bin'
        if not path.exists():continue
        state=path.read_bytes();runtime.append({'snapshot':label,'file':str(path.relative_to(ROOT)),'changed_officer_ids':[i for i in range(237) if state[0x3c0+i*12:0x3c0+(i+1)*12]!=baseline[i*12:(i+1)*12]],'liu_bei_id222_record':list(state[0x3c0+222*12:0x3c0+223*12])})
    payload={'status':'passed','rom_sha256':ROM_SHA256,'oracle':'py651.2.0 executes actual ROM; mapper bus uses synthetic RAM and no full PPU/IRQ','case_count':sum(r['cases'] for r in results),'results':results,'unchanged_rom_runtime_snapshots':runtime,'initial_word_distributions':{'experience3500_count':sum(o.experience_raw==3500 for o in initial),'troops3500_count':sum(o.troops_raw==3500 for o in initial),'maximum_initial_troops_raw':max(o.troops_raw for o in initial)},'limitations':['CPU field mutation harness does not modify the original ROM or the real Nestopia screenshot/save states.','Byte5/terrain/status semantic wording is calibrated separately in fields.json.','Byte9 upper6 bits and low5 equipment IDs24..31 retain raw data without invented semantics.']}
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'validation.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f'Passed {payload["case_count"]} actual-ROM field read/write cases; wrote {a.out}/validation.json')

if __name__=='__main__':main()
