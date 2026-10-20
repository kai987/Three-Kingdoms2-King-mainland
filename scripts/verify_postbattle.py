#!/usr/bin/env python3
"""Actual-ROM oracle versus independent readable postbattle gameplay APIs."""
from pathlib import Path
import sys,json,argparse,random
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from verify_battle_fsm import make_bus,native,rts
from py65.devices.mpu6502 import MPU
from source.recovered.postbattle import *

def native_ui(bus,entry,*,ready,cursor):
    """Declared UI service boundary: controlled ready/cursor, draw-only no-ops.
    No campaign mutation helper is intercepted; all writes execute real ROM.
    """
    cpu=MPU(memory=bus);bus.cpu=cpu;cpu.pc=entry;cpu.sp=0xFD;cpu.p=32
    bus.ram[0x1FE:0x200]=bytes([255,1]);messages=[]
    for n in range(200000):
        if cpu.pc==0x200:return messages
        if cpu.pc in(0xF283,0xF28B,0xF293):messages.append((cpu.a,f'{cpu.pc:04X}'))
        if cpu.pc==0xDF27:
            cpu.p=(cpu.p|1) if ready else (cpu.p&~1);rts(cpu,bus);continue
        if cpu.pc in (0xED1E,0xED23):
            bus[0x12]=cursor;rts(cpu,bus);continue
        if cpu.pc in (0xCC29,0xDC63,0xEDF5,0xD1BC):rts(cpu,bus);continue
        if bus.origin(cpu.pc) is None:raise RuntimeError(f'RAM PC {cpu.pc:04X}')
        cpu.step()
    raise RuntimeError(f'UI oracle instruction budget PC {cpu.pc:04X}')

def verify(rom):
    data=PostbattleData.from_rom(rom);rng=random.Random(650204)
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
    ram=prefix.with_name(prefix.name+'-ram.bin').read_bytes();sram=prefix.with_name(prefix.name+'-sram.bin').read_bytes()
    counts=Counter();errors=[];samples=[]
    gameplay=list(range(0x42C,0x44C))+list(range(0x550,0x55B))+list(range(0x6FA1,0x6FCB))+[4,0x50,0x52C]
    def compare(name,a,b,i,keys=gameplay):
        diff=[(x,a[x],b[x]) for x in keys if a[x]!=b[x]]
        sd=[(j+0x6000,x,y) for j,(x,y) in enumerate(zip(a.sram,b.sram)) if x!=y]
        if diff or sd:errors.append({'function':name,'case':i,'ram':diff[:16],'sram':sd[:16]})
        else:counts[name]+=1
    def fixture(i,pair=8):
        a=make_bus(rom,ram,sram,pair);a[0x50E]=11;a[0x507]=0x21;a[0x504]=128 if i&1 else 0
        a[0x50]=i&255;a[0x52A]=3;a[0x52B]=255 if i%4 else 100;a[4]=(0,1,5,19)[i%4]
        ruler=side_ruler(a);a[0x6F07+8*ruler]=100
        for city in range(30):
            addr=city_address(city);a[addr]=0xA0|([ruler,7,3,ruler][(city+i)%4])
            occupied=[0,1,5,9,10][(city+i)%5]
            for o in range(10):a[addr+17+o]=200+o if o<occupied else 255
        for slot in range(20):
            for base in (0x600,0x614,0x628,0x63C,0x650,0x664):a[base+slot]=255
        for j in range(40):a[0x6F47+j]=255
        sign=a[0x504];first=10 if sign else 0;other=0 if sign else 10
        n=i%11
        for j in range(n):a[0x628+first+j]=sign;a[0x664+first+j]=100+j
        transfer=min(10,(i//11)%4)
        for j in range(transfer):a[0x628+other+j]=sign;a[0x664+other+j]=120+j
        captured=0x6F5B if sign else 0x6F47
        for j in range((i//7)%7):a[captured+j]=140+j
        for officer in list(range(100,110))+list(range(120,124))+list(range(140,147)):
            address=officer_address(officer)
            a[address+5]=rng.randrange(30);a[address+11]=rng.randrange(256)
        return a
    for mode in range(3):
        for i in range(512):
            a=fixture(i);a[0x6F91]=mode;b=make_bus(rom,a.ram,a.sram,8)
            expected=process_ai_officers(b,mode,data=data);native(a,0xBC46)
            compare(f'ai_mode{mode}',a,b,i)
            if i in (0,10,15,63,511):samples.append({'mode':mode,'case':i,'events':expected})
    for i in range(512):
        a=fixture(i);b=make_bus(rom,a.ram,a.sram,8)
        collect_ai_officers(b);native(a,0xBDCD);compare('collect_ai_officers',a,b,i,list(range(0x6FA1,0x6FCB)))
        a=fixture(i);collect_ai_officers(a);b=make_bus(rom,a.ram,a.sram,8)
        prioritize_commander(b);native(a,0xBE55);compare('prioritize_commander',a,b,i,list(range(0x6FA1,0x6FCB)))
        a=fixture(i);b=make_bus(rom,a.ram,a.sram,8)
        ai_neighbor_cities(b,data);native(a,0xBE90);compare('ai_neighbor_cities',a,b,i,list(range(0x42C,0x437))+list(range(0x550,0x55B)))
        a=fixture(i,12);a[0x50B]=17 if i&1 else 2;b=make_bus(rom,a.ram,a.sram,12)
        build_postbattle_roster(b);native(a,0xD0E1)
        compare('build_postbattle_roster',a,b,i,list(range(0x42C,0x44C))+list(range(0x580,0x5A1))+[0x50A])
        a=fixture(i,12);b=make_bus(rom,a.ram,a.sram,12)
        human_neighbor_cities(b,data);native(a,0xBB84)
        compare('human_neighbor_cities',a,b,i,list(range(0x42C,0x46C))+list(range(0x550,0x560))+[0x50A])
        a=fixture(i,12);a[0x50B]=17 if i&1 else 2;a[0x500]=13;a[0x501]=1
        b=make_bus(rom,a.ram,a.sram,12);release_all_without_destination(b);native(a,0xCD9C)
        compare('release_all_without_destination',a,b,i,list(range(0x42C,0x44C))+list(range(0x580,0x5A1))+[0x50A,0x500,0x501])
    # Independent selective allocation/release and alias-removal inputs.
    for i in range(768):
        a=fixture(i,12);a[0x50B]=17 if i&1 else 2
        ids=build_postbattle_roster(a);n=min(20,len(ids))
        for j in range(n):a[0x580+j]=0 if (i+j)%3==0 else 255
        a[0x540]=30 if i%3==0 else [3,11,12][i%3]
        if i%7==0 and n>1:a[0x42D]=a[0x42C] # real alias semantics, no dedupe
        b=make_bus(rom,a.ram,a.sram,12);apply_selected_officers(b,data=data);native(a,0xD1F9)
        compare('apply_selected_officers',a,b,i,list(range(0x600,0x678))+list(range(0x6F47,0x6F6F))+[0x50,0x52C])
        a=fixture(i,12);a[0x50B]=17 if i&1 else 2;build_postbattle_roster(a)
        for j in range(20):
            if a[0x42C+j]==254:a[0x42C+j]=255
        b=make_bus(rom,a.ram,a.sram,12);accept_remaining_current_city(b);native(a,0xD48D)
        compare('accept_remaining_current_city',a,b,i,list(range(0x600,0x678))+list(range(0x6F47,0x6F6F)))
        a=fixture(i,12);a[0x50B]=17 if i&1 else 2;ids=build_postbattle_roster(a)
        a[0x50A]=len(ids);a[0x508]=i%(len(ids)+1);a[0x81]=1 if i%2 else 0
        a[0x540]=30 if i%3==0 else 12;a[0x541]=0;a[0x550]=i%11
        for j in range(len(ids)):a[0x580+j]=[0,255,128][(i+j)%3]
        b=make_bus(rom,a.ram,a.sram,12);toggle_officer_selection(b);native(a,0xD167)
        compare('toggle_officer_selection',a,b,i,list(range(0x580,0x5A1))+[0x44C])
    engine_keys=list(range(0x42C,0x46C))+list(range(0x550,0x560))+list(range(0x580,0x5A1))+list(range(0x500,0x50F))+list(range(0x540,0x542))+list(range(0x600,0x678))+list(range(0x6F47,0x6F6F))+[0x50,0x52C,0xE6,0xE7,0x8E,0x90,0x424,0x425]
    for main in (13,14):
        for sub in range(7):
            for i in range(64):
                a=fixture(i,12);a[0x50B]=17 if i&1 else 2
                a[0x500]=main;a[0x501]=sub;ids=build_postbattle_roster(a)
                if sub==2:
                    cities=human_neighbor_cities(a,data);a[0x50A]=len(cities);a[0x42C+len(cities)]=30
                    cursor=i%(len(cities)+1)
                else:
                    a[0x50A]=len(ids);cursor=i%(len(ids)+1)
                a[0x540]=30 if i%3==0 else 12;a[0x541]=0;a[0x550]=i%11
                for j in range(len(ids)):a[0x580+j]=0 if (i+j)%3==0 else 255
                a[0x81]=i&1;ready=bool(i&2)
                b=make_bus(rom,a.ram,a.sram,12)
                result=PostbattleEngine(b,data=data).step(text_ready=ready,cursor_index=cursor)
                native_messages=native_ui(a,0xCD16 if main==13 else 0xD2CD,ready=ready,cursor=cursor)
                source_messages=[(e['id'],e['queue']) for e in result['events'] if e['kind']=='message']
                if native_messages!=source_messages:errors.append({'function':'message_queue_event','case':(main,sub,i),'rom':native_messages,'source':source_messages})
                compare(f'engine_{main}_{sub}',a,b,i,engine_keys)
    # Sequential human allocation frames: no list reset between model/native
    # steps, completing multiple officers until the real parent-state return.
    sequences=[]
    for main in (13,14):
        for variant in range(16):
            a=fixture(40+variant,12);a[0x50B]=17 if variant&1 else 2
            a[0x500]=main;a[0x501]=0
            city=city_address(a[0x50E])
            for o in range(17,27):a[city+o]=255
            b=make_bus(rom,a.ram,a.sram,12);engine=PostbattleEngine(b,data=data)
            trace=[]
            for frame in range(160):
                if a[0x500]==15:break
                assert a[0x500]==b[0x500] and a[0x501]==b[0x501]
                sub=a[0x501];cursor=0
                if sub==2:
                    limit=a[0x50A]
                    cursor=next((j for j in range(limit) if a[0x550+j]<10),limit)
                if sub==5:
                    # Select one legal officer then the done item. Release
                    # cannot select the ruler, so skip it using real record ID.
                    selected=any(a[0x580+j]==0 for j in range(20))
                    if selected:cursor=a[0x50A]
                    else:
                        candidates=[j for j in range(a[0x50A]) if a[0x540]!=30 or a[0x42C+j]!=context_leader(a)]
                        cursor=candidates[0] if candidates else a[0x50A]
                a[0x81]=b[0x81]=1
                before=[a[0x500],a[0x501]]
                result=engine.step(text_ready=True,cursor_index=cursor)
                native_messages=native_ui(a,0xCD16 if main==13 else 0xD2CD,ready=True,cursor=cursor)
                source_messages=[(e['id'],e['queue']) for e in result['events'] if e['kind']=='message']
                if native_messages!=source_messages:errors.append({'function':'continuous_message_queue_event','case':(main,variant,frame),'rom':native_messages,'source':source_messages})
                compare('continuous_human_frames',a,b,(main,variant,frame),engine_keys)
                trace.append({'before':before,'cursor':cursor,'after':[b[0x500],b[0x501]]})
            sequences.append({'main':main,'variant':variant,'frames':len(trace),'returned_to_parent':b[0x500]==15,'trace':trace})
    # Faithful BC46 scratch02 clobber: after releasing ID120, comparison uses
    # city11*8=88, so a living nonleader88 gets status3 without losing health.
    a=fixture(10);a[0x504]=128;a[0x6F91]=0
    for city in range(30):
        for o in range(17,27):a[city_address(city)+o]=200+o
    for slot in range(20):a[0x628+slot]=255;a[0x664+slot]=255
    for j in range(40):a[0x6F47+j]=255
    for j in range(10):a[0x628+10+j]=128;a[0x664+10+j]=100+j
    a[0x628]=a[0x629]=128;a[0x664]=120;a[0x665]=88
    a[officer_address(88)]=100;a[officer_address(88)+11]=0
    b=make_bus(rom,a.ram,a.sram,8);process_ai_officers(b,data=data);native(a,0xBC46)
    compare('scratch02_nonleader_status3',a,b,0)
    special={'officer_id':88,'health_after':b[officer_address(88)],'status_after':b[officer_address(88)+11]&3,'synthetic_fixture':True,'naturally_reachable_officer_order_not_verified':True}
    ai_sequences=[]
    for i in range(128):
        a=fixture(i);b=make_bus(rom,a.ram,a.sram,8);outcome=i&1;steps=[]
        for side,mode in ((128,0 if outcome==0 else 2),(0,1 if outcome==0 else 0)):
            a[0x504]=b[0x504]=side;a[0x6F91]=b[0x6F91]=mode
            process_ai_officers(b,mode,data=data);native(a,0xBC46)
            compare('continuous_ai_sides',a,b,(i,side),gameplay)
            steps.append({'side':side,'mode':mode,'rng_cursor':b[0x50]})
        ai_sequences.append({'variant':i,'outcome':outcome,'steps':steps})
    for i in range(512):
        a=fixture(i,8);slot=i%20;a[0]=slot
        a[0x4D8]=slot if i%3==0 else (slot+1)%20
        a[0x4DC]=slot if i%4==0 else (slot+2)%20
        b=make_bus(rom,a.ram,a.sram,8);remove_inactive_unit_slot(b);native(a,0xD6CD)
        compare('remove_inactive_unit_slot',a,b,i,list(range(0x600,0x678))+list(range(0x6FA1,0x6FB5))+list(range(0x4D8,0x4E0)))
    return {'status':'passed' if not errors else 'failed','rom_sha256':ROM_SHA256,'case_count':sum(counts.values())+len(errors),
        'passed_case_count':sum(counts.values()),'failed_count':len(errors),'counts':dict(counts),'mismatches':errors,'samples':samples,
        'sequences':sequences,'ai_sequences':ai_sequences,'status3_special_case':special,
        'message_queue_event_comparison':True,'scope':'Independent high-level gameplay source versus original-ROM CPU oracle; full SRAM plus declared gameplay buffers/state. CPU scratch/flags/bank-register and UI queue encodings are not promised.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase4/postbattle');a=p.parse_args()
    result=verify(a.rom.read_bytes());a.out.mkdir(parents=True,exist_ok=True);(a.out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in('mismatches','samples','sequences','ai_sequences')},indent=2))
    for e in result['mismatches'][:10]:print(e)
    if result['failed_count']:raise SystemExit(1)
