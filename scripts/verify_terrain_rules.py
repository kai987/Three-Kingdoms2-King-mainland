#!/usr/bin/env python3
"""Original6502 oracles for all legal maps, village events and10 service states."""
from pathlib import Path
from collections import Counter
import sys,argparse,hashlib,json,random
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered import terrain_rules as model
from source.recovered.map_service_machine import MapServiceMachine

def fresh(rom,pair=12):
    b=Bus(rom,'alternating');b.banks=[17,pair,pair+1,31];b.bank_initialized=[True]*4;b.protect=0x4c
    b.ram[0xe1:0xe4]=bytes([0x31,0x20+pair,0x21+pair]);b.ram[0x1fe:0x200]=bytes([255,1])
    b.sram[0x3c0:0xf2c]=rom[0x22010:0x22b7c];return b

def run(b,entry,stop=0x0200,reg=None,limit=100000):
    c=MPU(memory=b,pc=entry);c.sp=0xfd;c.p=c.UNUSED;b.cpu=c
    for key,value in(reg or{}).items():setattr(c,key,value)
    for count in range(limit):
        if c.pc==stop:return c,count
        b.pc=c.pc;b.step_no=count
        if c.disassemble[b.peek(c.pc)][0]=='???':raise RuntimeError(f'Unsupported original opcode{c.pc:04X}')
        c.step()
    raise RuntimeError(f'Original entry{entry:04X} did not return at{c.pc:04X}')

class ActualHooks:
    def __init__(self,bus):self.bus=bus;self.calls=[]
    def __call__(self,context,target,return_pc,kind):
        r=context.registers;c=MPU(memory=self.bus,pc=target)
        for name in('a','x','y','sp','p'):setattr(c,name,getattr(r,name))
        self.bus.cpu=c;stop=return_pc if return_pc is not None else 0x0200
        for count in range(100000):
            if c.pc==stop:break
            self.bus.pc=c.pc
            if c.disassemble[self.bus.peek(c.pc)][0]=='???':raise RuntimeError(f'Unrecognized helper opcode{c.pc:04X}')
            c.step()
        else:raise RuntimeError(f'External helper{target:04X} did not return at{c.pc:04X}')
        for name in('a','x','y','sp','p','pc'):setattr(r,name,getattr(c,name))
        self.calls.append({'target':target,'kind':kind,'instructions':count})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase4/terrain');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==model.ROM_SHA256;counts=Counter();examples=[];rng=random.Random(0x416)
    def inc(name):counts[name]+=1
    assert rom[0x1175b:0x117db]==rom[0x1bbae:0x1bc2e]
    for city in range(30):
        chunks=model.city_chunks(rom,city)
        b=fresh(rom,23);b[0x50e]=city;run(b,0xdf15)
        assert list(b.ram[0xaa:0xae])==list(chunks)and b[0xa8]==0xaa and b[0xa9]==0;inc('city_chunk_setup')
        for y in range(20):
            if y==15:continue
            for x in range(31):
                cell=model.map_cell(rom,chunks,x,y)
                b=fresh(rom,8)
                for address,value in{0xa8:0xaa,0xa9:0,0x20:x,0x21:y,**{0xaa+i:c for i,c in enumerate(chunks)}}.items():b[address]=value
                c,n=run(b,0xb6ef);assert c.a==cell['raw_class'];inc('all_legal_raw_map_lookup')
                if cell['raw_class']>=6 or(x+y)%37==0:
                    for pair,entry,zpx,zpy in[(8,0xb6e5,0x20,0x21),(12,0xdb46,0x10,0x11)]:
                        b=fresh(rom,pair)
                        for address,value in{0xa8:0xaa,0xa9:0,zpx:x,zpy:y,**{0xaa+i:c for i,c in enumerate(chunks)}}.items():b[address]=value
                        c,n=run(b,entry);assert c.a==cell['movement_class'];inc('player_ai_normalization')
                index=model.service_at(rom,city,x,y)
                if index is not None or(x+y)%31==0:
                    for mode in[0,3]:
                        b=fresh(rom);b[0x500]=4;b[0x501]=5;b[0x509]=0;b[0x600]=x;b[0x614]=y;b[0x50e]=city;b[0x50f]=mode;b[0x10]=x;b[0x11]=y;b[0x664]=131;b[0x7c]=0
                        clone=fresh(rom);clone.ram[:]=b.ram;clone.sram[:]=b.sram
                        c,n=run(b,0xa4d6)
                        def render(memory):run(memory,0xd6cc,reg={'a':1})
                        effect=model.enter_map_service(clone,rom,render)
                        assert clone.ram[0x400:]==b.ram[0x400:]and clone.sram==b.sram,('service entry',city,x,y,mode,effect)
                        assert clone.ram[0x300:0x314]==b.ram[0x300:0x314]
                        inc('service_event_coordinate_scan')
                        if effect['entered']and len(examples)<5:examples.append({'city':city,'xy':[x,y],'raw_class':cell['raw_class'],'effect':effect})
    for index in range(256):
        for selection in[0,1]:
            b=fresh(rom,8);b[0x470]=index;b[0x12]=selection;b[0x500]=9;b[0x501]=9
            c=fresh(rom,8);c.ram[:]=b.ram;c.sram[:]=b.sram
            run(b,0xc80b);model.select_map_service(c)
            assert c.ram[0x400:]==b.ram[0x400:]and c.ram[0x300:0x314]==b.ram[0x300:0x314];inc('service_selection_routing')
    for i in range(1200):
        grain,gold,amount=[rng.choice([0,1,9998,9999,10000,65535])if i<120 else rng.randrange(65536)for _ in range(3)]
        price=rng.choice([0,1,2,50,99,100,255]);buy=bool(i&1)
        b=fresh(rom,8);b[0x504]=0;b[0x492]=price;b[0x501]=1
        for address,value in[(0x522,grain),(0x526,gold),(0x48e,amount)]:b[address]=value&255;b[address+1]=value>>8
        run(b,0xc21b if buy else 0xc2f2)
        expected=model.resource_trade(grain,gold,amount,price,buy)
        assert(b[0x522]|b[0x523]<<8)==expected['grain']and(b[0x526]|b[0x527]<<8)==expected['gold'],('trade',i,expected)
        if amount:assert b[0x501]==8 and b[0x311]==expected['message']and(b[0x42c]|b[0x42d]<<8)==expected['reported_amount']
        inc('resource_trade_transactions')
    for i in range(1024):
        officer=rng.randrange(237);current=rng.randrange(256);sample=i%11;initial=rom[0x22010+12*officer]
        b=fresh(rom,8);b[0x509]=0;b[0x664]=officer;b[0x63c0+12*officer]=current
        run(b,0xc462,reg={'a':sample})
        expected=model.map_service_heal(current,initial,sample)
        assert b[0x63c0+12*officer]==expected['health']and b[0x42c]==expected['reported_healing'],(officer,current,sample,expected)
        inc('healing_wrap_and_initial_ceiling')
    for i in range(2048):
        item=rng.choice([15,22,23,30,rng.randrange(32)]);officer=rng.choice([38,153,rng.randrange(237)])
        martial=rng.choice([0,89,90,91,255]);virtue=rng.choice([0,89,90,91,255]);flags=i&255
        b=fresh(rom,8);b[0x509]=0;b[0x664]=officer;b[0x44c]=item;b[0x6fe1]=flags;b[0x63c1+12*officer]=martial;b[0x63c4+12*officer]=virtue
        c,n=run(b,0xc73b);expected=model.equipment_permission(item,officer,martial,virtue,flags)
        assert bool(c.p&1)==expected['allowed']and b[0x6fe1]==expected['allocation_flags']
        if expected['message']is not None:assert b[0x311]==expected['message']
        inc('rare_equipment_restrictions')
    for packed in range(256):
        for item in[0,15,22,23,24,30,31]:
            b=fresh(rom,8);b[0x509]=0;b[0x664]=0;b[0x44c]=item;b[0x63ca]=packed
            run(b,0xc6d5,stop=0xc708)
            assert b[0x63ca]==model.pack_purchased_equipment(packed,item);inc('equipment_bitfield_purchase_write')
    representatives={}
    for city in range(30):
        chunks=model.city_chunks(rom,city)
        for y in range(20):
            if y==15:continue
            for x in range(31):
                cell=model.map_cell(rom,chunks,x,y);representatives.setdefault(cell['raw_class'],(chunks,x,y))
    for raw_class,(chunks,x,y)in representatives.items():
        for affinity in range(4):
            for troops in[0,599,600,1023,1024,65535]:
                for ap in[0,1,3,6,255]:
                    flags=(rng.randrange(256)&0xf3)|(affinity<<2);b=fresh(rom)
                    b.ram[0x664:0x678]=bytes([131]+[255]*19);b[0x509]=0;b[0x505]=ap
                    off=0x63c0+131*12;b[off+8]=troops&255;b[off+9]=troops>>8;b[off+11]=flags
                    run(b,0xdb03);cache=b[0x63c];assert cache==(troops&1023)//100
                    for address,value in{0xa8:0xaa,0xa9:0,0x10:x,0x11:y,**{0xaa+i:c for i,c in enumerate(chunks)}}.items():b[address]=value
                    lookup,n=run(b,0xdb46);result,n=run(b,0xa7e7,reg={'a':lookup.a})
                    expected=model.movement_quote(rom,chunks,x,y,flags,cache,ap)
                    assert result.x==expected['cost']and result.a==expected['remaining_ap']and bool(result.p&1)==expected['sufficient_ap']
                    inc('cached_movement_quote_all_classes')
    program=json.loads((a.out/'service-program.json').read_text());fixtures=[];failures=[];coverage=set();hooks=Counter()
    for sub in range(10):
        for buttons in[0,1,2]:
            for side in[0,128]:
                for idle in[0,255]:
                    b=fresh(rom,8)
                    inputs={0x500:9,0x501:sub,0x509:0,0x664:131,0x470:0,0x504:side,0x50e:4,0x81:buttons,0x300:idle,0x304:idle,0x7c:0,0x7e:0,0x492:100,0x48e:1,0x48f:0,0x12:0}
                    for address,value in inputs.items():b[address]=value
                    b.ram[0x44c:0x450]=bytes([0,1,2,3]);b.ram[0x42c:0x438]=bytes([50,0,0,70,0,0,120,0,0,180,0,0]);b.ram[0x522:0x52a]=bytes([232,3,232,3,208,7,208,7])
                    clone=fresh(rom,8);clone.ram[:]=b.ram;clone.sram[:]=b.sram;adapter=ActualHooks(clone);machine=MapServiceMachine(clone,adapter,program)
                    try:
                        expected,steps=run(b,0xc0bb);effect=machine.step();got=machine.registers
                        assert all(getattr(got,k)==getattr(expected,k)for k in['a','x','y','sp','p','pc']),('registers',vars(got))
                        assert clone.ram==b.ram and clone.sram==b.sram and clone.banks==b.banks,('memory',[(i,b.ram[i],clone.ram[i])for i in range(2048)if b.ram[i]!=clone.ram[i]][:7])
                        fixtures.append({'substate':sub,'buttons':buttons,'side':side,'job_idle_value':idle,'after':effect['after'],'instructions':steps,'hooks':adapter.calls});coverage.update(machine.executed);hooks.update(f'{v["target"]:04X}'for v in adapter.calls)
                    except Exception as e:failures.append({'substate':sub,'buttons':buttons,'side':side,'idle':idle,'error':str(e)[:1200]})
    result={'rom_sha256':model.ROM_SHA256,'status':'passed'if not failures else'partial_with_explicit_failures','case_count':sum(counts.values())+len(fixtures),'counts':dict(counts),'service_controller_case_count':len(fixtures),'service_controller_failed_count':len(failures),'service_instruction_coverage':len(coverage),'service_instruction_total':len(program['instructions']),'service_controller_fixtures':fixtures,'service_controller_failures':failures,'service_external_helpers':dict(hooks),'examples':examples,'scope':'Original6502 code oracle with synthetic RAM; external drawing/input/far helpers execute original ROM explicitly. Complete-core menu screenshots are separately labeled synthetic fixtures.','limitations':['Formal terrainclass1 name remains unidentified.','Raw marker encodings and coordinate-index service kinds are not conflated.','All legal map cells and10 service entries are checked; dynamic instruction coverage is separately reported.']}
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in['status','case_count','counts','service_controller_case_count','service_controller_failed_count','service_instruction_coverage','service_instruction_total']},indent=2))
    if failures:print(json.dumps(failures[:8],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
