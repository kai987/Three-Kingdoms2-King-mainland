#!/usr/bin/env python3
"""Exact original fixed-menu CPU comparisons, including all inactive stack RAM."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_scene_controller import ObservableBus
from source.recovered.city_menu_navigation import CityMenuNavigation
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.service_memory import ServiceMemory
from source.recovered.officers import ROM_SHA256

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify(rom,out):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    p=ROOT/'analysis/phase11/runtime/cold-battle/city-commands';ram=Path(str(p)+'-ram.bin').read_bytes();sram=Path(str(p)+'-sram.bin').read_bytes()
    counts=Counter();rows=[];failures=[];guards=[];executed=Counter()
    def fresh(prep,table,sp):
        actual=ObservableBus(rom,ram,sram);actual.banks=[17,27,28,31]
        actual.ram[0x580:0x680]=bytes(table);actual.ram[0x10:0x12]=bytes((128,5))
        for a,v in prep.items():actual[a]=v
        actual.ram[0x100+((sp+1)&255)]=255;actual.ram[0x100+((sp+2)&255)]=1
        actual.ports=[];actual.port_reads=[]
        memory=ServiceMemory(rom,actual.ram,actual.sram,tuple(actual.banks))
        return actual,memory
    def compare(group,entry,prep,table,reg_input=None):
        initial=dict(a=17,x=31,y=63,p=32,sp=253,pc=entry);initial.update(reg_input or{})
        actual,memory=fresh(prep,table,initial['sp']);cpu=MPU(memory=actual);actual.cpu=cpu
        for k,v in initial.items():setattr(cpu,k,v)
        r=NMIRegisters(**initial);model=CityMenuNavigation(memory,rom)
        try:
            result=model.run_service(entry,r);assert result['status']=='returned',result
            for n in range(50000):
                if n and cpu.pc==0x200 and cpu.sp==r.sp:break
                origin=actual.origin(cpu.pc)
                if origin is None:raise RuntimeError(f'Original entered RAM at ${cpu.pc:04X}')
                executed[(origin[0],cpu.pc,origin[1]+16)]+=1;actual.pc=cpu.pc;actual.step_no=n;cpu.step()
            else:raise RuntimeError(f'Original menu budget ${cpu.pc:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(actual.ram,memory.ram))if x!=y]
            rg={k:(getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)}
            assert not rd and not rg and actual.sram==memory.sram,dict(RAM=rd[:12],registers=rg)
            assert actual.ports==memory.io_writes and actual.banks==memory.banks and not actual.port_reads
            counts[group]+=1
            rows.append(dict(group=group,entry=entry,preparation={f'{a:04X}':v for a,v in prep.items()},initial_registers=initial,
                original_instructions=n,final_registers=vars(r).copy(),table_hex=bytes(table).hex(),complete_return=True))
        except Exception as exc:
            failures.append(dict(group=group,entry=entry,preparation=prep,registers=initial,error=str(exc)))
            if len(failures)<5:print(json.dumps(failures[-1]),flush=True)
    buttons=(0,16,32,64,128,240,255,144,96)
    for width in range(1,9):
        table=[255]*256
        for i in range(3*width):table[i]=i
        if width>1:table[2*width-1]=255
        for row in range(3):
            for column in range(width):
                value=table[row*width+column]
                if value==255:continue
                for button in buttons:
                    for entry in(0xED19+5*(width-1),0xED41):
                        compare('legal_direction_width_table',entry,{0x81:button,0x424:column,0x425:row,0x12:value},table,
                            dict(a=width,p=(32,33,96,97,160,161)[(width+row+column+button)%6]))
    # Raw offset arithmetic lives wholly inside a256B table and executes no
    # table bytes as code. These inputs are service byte-boundaries only.
    table=[i%127 for i in range(256)]
    for width in(0,1,127,128,255):
        for row in(0,1,255):
            for column in(0,127,255):compare('raw_byte_offset_wrap_EDDD',0xEDDD,{0:width,0x424:column,0x425:row},table,dict(p=97))
    table=[0,1,2,3,255,255]+[255]*250
    for sp in range(256):compare('all_caller_stack_positions',0xED1E,{0x81:255,0x424:0,0x425:0,0x12:0},table,dict(sp=sp,p=97))
    # Left scans reject onlyFF. A sign-bit value80 is accepted by that path,
    # while right/down/up treat its sign bit as a boundary.
    table=[0,128]+[255]*254
    compare('left_accepts_nonFF_negative_cell',0xED1E,{0x81:64,0x424:0,0x425:0,0x12:0},table)
    # Missing sentinels are real cyclic source prefixes, never fake returns.
    for name,button,table in [('no_left_valid_byte',64,[255]*256),('no_up_sign_bit',16,[0]*256)]:
        _,memory=fresh({0x81:button,0x424:0,0x425:0,0x12:0},table,253)
        r=NMIRegisters(a=2,p=33);model=CityMenuNavigation(memory,rom)
        result=model.run_service(0xED1E,r);assert result['status']=='dependency',result
        before=(bytes(memory.ram),bytes(memory.sram),vars(r).copy(),list(memory.io_writes))
        after=model.resume();assert after['status']=='dependency'and before==(bytes(memory.ram),bytes(memory.sram),vars(r).copy(),list(memory.io_writes))
        guards.append(dict(name=name,kind='cyclic_source_dependency',pc=r.pc,sp=r.sp,caller_return_not_consumed=True))
    _,memory=fresh({},[0]*256,253);r=NMIRegisters(p=40)
    before=(bytes(memory.ram),bytes(memory.sram),vars(r).copy())
    try:CityMenuNavigation(memory,rom).run_service(0xED1E,r)
    except ValueError:pass
    else:raise AssertionError('Missing decimal guard')
    assert before==(bytes(memory.ram),bytes(memory.sram),vars(r).copy());guards.append(dict(name='decimal_protocol',kind='source_rejection'))
    r=NMIRegisters(pc=0x8123);model=CityMenuNavigation(memory,rom)
    before=(bytes(memory.ram),bytes(memory.sram),vars(r).copy())
    result=model(ServiceCall(0x8123,0x200,'unknown',r,memory,tuple(memory.banks),255))
    assert result['status']=='dependency'and before==(bytes(memory.ram),bytes(memory.sram),vars(r).copy());guards.append(dict(name='unknown_target',kind='source_dependency'))
    before=(bytes(memory.ram),bytes(memory.sram))
    try:CityMenuNavigation(memory,rom).run_service(0xED1E)
    except ValueError:pass
    else:raise AssertionError('Missing actual-caller registers guard')
    assert before==(bytes(memory.ram),bytes(memory.sram));guards.append(dict(name='missing_actual_caller_registers',kind='source_rejection'))
    pins=('source/recovered/city_menu_navigation.py','source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py',
          'scripts/verify_city_menu_navigation.py','scripts/verify_battle_scene_controller.py','scripts/trace_startup.py')
    result=dict(schema='phase13-exact-menu-navigation-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,counts=dict(counts),
        source_guard_case_count=len(guards),guards=guards,failed_count=len(failures),failures=failures,rows=rows,source_original_CPU_callbacks=0,source_IR_interpretation=False,
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers=['A','X','Y','P','SP','PC'],free_stack_residue='included',ordered_ports_and_banks=True),
        source_sha256={p:sha(ROOT/p)for p in pins},
        limits=['Prepared caller tables, directions and cursor bytes are independent service CPU cases, not native internal registers or complete core frames.',
                'No original helper callback runs on the source side. Fullmenu/nestedEDDD callers preserve original inactive stack writes.',
                'The two cyclic source guards are not complete originalCPU return cases and are counted separately.','Decimal flag clear is the explicit binary6502 oracle contract.'])
    out.mkdir(parents=True,exist_ok=True);(out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=f,count=n)for(b,pc,f),n in sorted(executed.items())],indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/menu-navigation');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out);raise SystemExit(bool(result['failures']))
