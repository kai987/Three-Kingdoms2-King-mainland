#!/usr/bin/env python3
"""Original CPU vs pure city action bodies; all RAM/SRAM and actual caller RTS.

No original helper callback is used on the recovered-source side. Prepared
byte-edge/alias fixtures are CPU service inputs, not unmodified gameplay.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_scene_controller import ObservableBus
from source.recovered.city_action_bridges import CityActionBridges,CityActionData,ROM_SHA256
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.service_memory import ServiceMemory

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify(rom,out,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    base=ROOT/'analysis/phase11/runtime/cold-battle/city-commands'
    ram=Path(str(base)+'-ram.bin').read_bytes();sram=Path(str(base)+'-sram.bin').read_bytes()
    data=CityActionData.from_rom(rom);counts=Counter();failures=[];rows=[];coverage=Counter();guards=[]
    def compare(group,entry,prep,regs=None):
        pair=8 if entry in CityActionBridges.SHOP_ENTRIES else 10
        actual=ObservableBus(rom,ram,sram);actual.banks=[17,pair,pair+1,31]
        initial=dict(a=17,x=31,y=63,p=32,sp=253,pc=entry);initial.update(regs or{})
        for address,value in prep.items():actual[address]=value
        sp=initial['sp'];return_word=0x2467
        actual.ram[0x100+((sp+1)&255)]=return_word&255;actual.ram[0x100+((sp+2)&255)]=return_word>>8
        actual.ports=[];actual.port_reads=[]
        memory=ServiceMemory(rom,actual.ram,actual.sram,tuple(actual.banks))
        r=NMIRegisters(**initial);model=CityActionBridges(memory,data);cpu=MPU(memory=actual);actual.cpu=cpu
        for k,v in initial.items():setattr(cpu,k,v)
        try:
            result=model.run_entry(entry,r);assert result['status']=='returned',result
            for n in range(10000):
                if n and cpu.pc==r.pc and cpu.sp==r.sp:break
                origin=actual.origin(cpu.pc)
                if origin is None:raise RuntimeError(f'Original unexpectedly entered RAM ${cpu.pc:04X}')
                coverage[(origin[0],cpu.pc,origin[1]+16)]+=1;actual.pc=cpu.pc;actual.step_no=n;cpu.step()
            else:raise RuntimeError(f'Original service budget at ${cpu.pc:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(actual.ram,memory.ram))if x!=y]
            sd=[(i,x,y)for i,(x,y)in enumerate(zip(actual.sram,memory.sram))if x!=y]
            rg={k:(getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:6],registers=rg)
            assert actual.banks==memory.banks and actual.ports==memory.io_writes and not actual.port_reads
            counts[group]+=1
            rows.append(dict(group=group,entry=entry,prepared_memory={f'{a:04X}':v for a,v in prep.items()},initial_registers=initial,
                original_instructions=n,final_registers=vars(r).copy(),complete_return=True,ordered_ports=memory.io_writes))
        except Exception as exc:
            failures.append(dict(group=group,entry=entry,prep={hex(k):v for k,v in prep.items()},registers=initial,error=str(exc)))
            if len(failures)<=4:print(json.dumps(failures[-1]),flush=True)
    flags=(32,33)if quick else(32,33,34,35,96,97,160,161)
    for group in range(3 if quick else 6):
        for category in range(4):
            for entry in(0xA01E,0xC851):
                for p in flags:compare('shop_all_table_groups',entry,{0:group,0x12:category},{'p':p})
    virtues=(0,99,255)if quick else(0,1,9,10,11,99,100,127,128,249,255)
    loyalties=(0,70,100,255)if quick else(0,1,9,10,11,70,79,89,90,99,100,127,128,255)
    for virtue in virtues:
        for loyalty in loyalties:
            for entry in(0xA006,0xCF3F):
                for p in((32,)if quick else(32,33,96,160)):
                    compare('recruitment_wrap_clamp',entry,{0x30:131,0x31:5,0x63C0+12*131+4:virtue,0x63C0+12*5+3:loyalty},{'p':p})
    for ident in((0,131,255)if quick else(0,131,236,237,254,255)):
        for old in(0,70,100,255):
            compare('same_record_alias_and_raw_ID',0xA006,{0x30:ident,0x31:ident,0x63C0+12*ident+4:99,0x63C0+12*ident+3:old})
    for ident in((0,255)if quick else(0,1,127,128,131,236,237,254,255)):
        for field in(0,3,4,11):compare('record_pointer_byte_ID',0xD2AB,{}, {'a':ident,'y':field,'p':33})
    values=(0,1,65535)if quick else(0,1,9,10,255,256,32767,32768,65535)
    divisors=(0,10)if quick else(0,1,2,10,255,256,32768,65535)
    for value in values:
        for divisor in divisors:compare('divide_word_boundaries',0xD40F,{0x21:value&255,0x22:value>>8,0x23:divisor&255,0x24:divisor>>8},{'p':97})
    for sp in((0,1,128,253,255)if quick else range(256)):
        compare('all_caller_stack_positions',0xA006,{0x30:131,0x31:5},{'sp':sp})
    compare('actual_empty_D61E',0xD61E,{}, {'a':255,'x':255,'y':255,'p':225,'sp':3})
    for name,entry,prep,regs in[
        ('group6',0xA01E,{0:6,0x12:0},{}),('category4',0xA01E,{0:0,0x12:4},{}),
        ('decimal_protocol',0xA006,{},dict(p=40)),('unknown_entry',0xA009,{},{}),
    ]:
        m=ServiceMemory(rom,ram,sram,(17,8,9,31));r=NMIRegisters(**regs)
        for a,v in prep.items():m[a]=v
        before=(bytes(m.ram),bytes(m.sram),vars(r).copy());g=CityActionBridges(m,data)
        try:g.run_entry(entry,r)
        except ValueError:pass
        else:raise AssertionError('Missing source guard '+name)
        assert before==(bytes(m.ram),bytes(m.sram),vars(r).copy());guards.append(name)
    m=ServiceMemory(rom,ram,sram,(17,10,11,31));r=NMIRegisters(pc=0xA01E)
    g=CityActionBridges(m,data);res=g(ServiceCall(0xA01E,0x0200,'callee',r,m,(17,10,11,31),255))
    assert res['status']=='dependency';guards.append('wrong_physical_pair')
    out.mkdir(parents=True,exist_ok=True)
    pins=('source/recovered/city_action_bridges.py','source/recovered/battle_nmi_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py',
          'scripts/verify_city_action_bridges.py','scripts/verify_battle_scene_controller.py','scripts/trace_startup.py')
    result=dict(schema='phase13-city-action-bridges-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=quick,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,counts=dict(counts),
        source_guard_case_count=len(guards),guards=guards,failed_count=len(failures),failures=failures,source_original_CPU_callbacks=0,
        source_IR_interpretation=False,comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers=['A','X','Y','P','SP','PC'],free_stack_residue='included',ordered_ports_and_banks=True),
        native_internal_CPU_trace=False,native_cases=0,source_sha256={p:sha(ROOT/p)for p in pins},rows=rows,
        limits=['Prepared service-domain CPU cases are distinct from native core flows.','Shop guards reject table-external values before source mutation; no original table-external code is executed.',
                'Raw IDs237..255 and zero-divisor directhelper cases verify byte addressing/arithmetic only; they are not valid officer gameplay claims.','Neither body buys equipment, transfers allegiance/rosters, requests PPU work or completes readiness.'])
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=f,count=n)for(b,pc,f),n in sorted(coverage.items())],indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/action-bridges');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out,a.quick);raise SystemExit(bool(result['failures']))
