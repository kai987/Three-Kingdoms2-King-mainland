#!/usr/bin/env python3
"""Native-input city callback CPU vs GameEngine's pure source composition.

Native files are immutable end-of-frame observations, not CPU register traces.
Both sides receive declared AXYP/0200 caller frames and the real F206/F25F/
F237 preparation. The recovered-source side has no original CPU callback.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.game_engine import GameEngine
from source.recovered.city_ui_controller import CityRegisters,ROM_SHA256
from source.recovered.battle_nmi_services import ServiceCall
from source.recovered.service_memory import ServiceMemory

REGS=('a','x','y','p','sp','pc')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):return digest(Path(p).read_bytes())
def regs(r):return {k:getattr(r,k)for k in REGS}

def verify(rom,out):
    assert digest(rom)==ROM_SHA256
    inventory_path=ROOT/'analysis/phase13/dependencies/inventory.json';inventory=json.loads(inventory_path.read_text())
    assert inventory['status']=='passed'and inventory['bounded_original_CPU_cases']==13
    sources=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))
    sources+=['scripts/verify_phase13_city_integration.py','scripts/verify_battle_graphics_services.py','scripts/trace_startup.py']
    before_pins={p:file_sha(ROOT/p)for p in sources}
    rows=[];failures=[];counts=Counter();snapshot_pins={};guard_rows=[]
    def original(bus,r,entry):
        cpu=MPU(memory=bus);bus.cpu=cpu
        for k,v in regs(r).items():setattr(cpu,k,v)
        cpu.pc=entry
        for n in range(400000):
            if n and cpu.pc==0x200 and cpu.sp==255:return cpu,n
            if bus.origin(cpu.pc)is None:raise RuntimeError(f'Original entered RAM at ${cpu.pc:04X}')
            bus.pc=cpu.pc;bus.step_no=n;cpu.step()
        raise RuntimeError(f'Original callback budget at ${cpu.pc:04X}')
    def differences(a,m,r,cpu):
        rd=[(i,a.ram[i],m.ram[i])for i in range(2048)if a.ram[i]!=m.ram[i]]
        sd=[(i,a.sram[i],m.sram[i])for i in range(8192)if a.sram[i]!=m.sram[i]]
        rg={k:(getattr(cpu,k),getattr(r,k))for k in REGS if getattr(cpu,k)!=getattr(r,k)}
        return dict(RAM=rd[:20],SRAM=sd[:10],registers=rg,ports_equal=a.ports==m.io_writes,banks_equal=a.banks==m.banks,
                    RAM_difference_count=len(rd),SRAM_difference_count=len(sd))
    def assert_equal(d):
        assert not d['RAM']and not d['SRAM']and not d['registers']and d['ports_equal']and d['banks_equal'],d
    for item in inventory['original_cases']:
        prefix=ROOT/item['native_snapshot'];ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
        assert digest(ram)==item['RAM_sha256']and digest(sram)==item['SRAM_sha256']
        snapshot_pins[str(Path(str(prefix)+'-ram.bin').relative_to(ROOT))]=digest(ram)
        snapshot_pins[str(Path(str(prefix)+'-sram.bin').relative_to(ROOT))]=digest(sram)
        actual=PortBus(rom);actual.ram[:]=ram;actual.sram[:]=sram
        actual.banks=[ram[0xDE]&31,ram[0xDF]&31,ram[0xE0]&31,31];actual.bank_initialized=[True]*4;actual.protect=0x4C;actual.record_ports=True
        m=ServiceMemory(rom,ram,sram,tuple(actual.banks),read_ports={0x2002:0,0x4015:0,0x4016:0,0x4017:0},repeat_read_ports=(0x2002,0x4015,0x4016,0x4017))
        game=GameEngine(m,rom=rom,mapped=True);coordinator=game.readable_scene_rules();assert coordinator.external_callback is None
        r=CityRegisters(a=76,x=ram[0x7C],y=0,p=32,sp=253,pc=0xF206)
        prelude=[];source_call_counts=Counter()
        try:
            for entry,Y in((0xF206,None),(0xF25F,ram[0xE1]),(0xF237,0x3B)):
                if Y is not None:r.y=Y
                r.sp=253;r.pc=entry
                for bus in(actual,m):bus[0x1FE]=255;bus[0x1FF]=1
                initial=regs(r);cpu,n=original(actual,r,entry)
                result=coordinator(ServiceCall(entry,0x200,'declared_preparation',r,m,tuple(m.banks),255))
                assert result['status']=='returned',result
                d=differences(actual,m,r,cpu);assert_equal(d)
                prelude.append(dict(entry=entry,Y=Y,initial_registers=initial,original_instructions=n,comparison='exact_complete_return'))
            r.sp=253;r.pc=0xA000
            for bus in(actual,m):bus[0x1FE]=255;bus[0x1FF]=1
            initial=regs(r);source=game.tick_readable_scene(r,scene=2)
            assert source['status']=='returned',source
            cpu,n=original(actual,CityRegisters(**initial),0xA000)
            d=differences(actual,m,r,cpu);assert_equal(d)
            for call in coordinator.calls:source_call_counts[call['kind']]+=1
            row=dict(case=item['case'],label=item['label'],snapshot=item['native_snapshot'],native_city_state=list(ram[0x400:0x40C]),
                initial_registers=initial,original_preparation=prelude,pure_API='GameEngine.tick_readable_scene(registers,scene=2)',
                source_status=source['status'],original_instructions=n,comparison='complete_return',final_registers=regs(r),final_banks=list(m.banks),
                port_writes=len(m.io_writes),ordered_ports_sha256=digest(json.dumps(m.io_writes,separators=(',',':')).encode()),
                pure_source_owner_counts=dict(source_call_counts),source_calls=coordinator.calls,source_original_CPU_callbacks=0,comparison_details=d)
            rows.append(row);counts['native_RAM_callback_complete']+=1
        except Exception as exc:
            failure=dict(case=item['case'],label=item['label'],error=str(exc),source_PC=r.pc,source_SP=r.sp,source_calls=coordinator.calls)
            failures.append(failure);print(json.dumps(failure,ensure_ascii=False),flush=True)
    # Reject an unknown owner without touching the actual caller frame.
    m=ServiceMemory(rom,ram,sram,(17,27,28,31));game=GameEngine(m,rom=rom,mapped=True);r=CityRegisters(pc=0x8123)
    before=(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),regs(r))
    result=game.readable_scene_rules()(ServiceCall(0x8123,0x200,'unknown',r,m,tuple(m.banks),255))
    assert result['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),regs(r))
    guard_rows.append('unowned_callee_remains_dependency_without_fake_RTS')
    after_pins={p:file_sha(ROOT/p)for p in sources};assert before_pins==after_pins,'Source changed during matrix; rerun after freeze'
    result=dict(schema='phase13-pure-city-source-integration-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,
        source_guard_case_count=len(guard_rows),failed_count=len(failures),counts=dict(counts),failures=failures,rows=rows,guards=guard_rows,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,production_fallback=False,native_internal_CPU_trace=False,
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers=['A','X','Y','P','SP','PC'],free_stack_residue='included',ordered_ports_and_banks=True),
        source_sha256=before_pins,artifact_sha256={str(inventory_path.relative_to(ROOT)):file_sha(inventory_path),**snapshot_pins},
        formal_native_manifest=dict(path='analysis/phase13/runtime/evidence.json',sha256=file_sha(ROOT/'analysis/phase13/runtime/evidence.json')),
        preparation_CPU_comparisons_within_cases=sum(len(r['original_preparation'])for r in rows),
        limits=['13 source callback pipelines include3exact original/source preparations each; these39helper checks are nested and not additional13case totals.',
                'Native RAM/SRAM are unchanged input artifacts. AXYP and0200caller are explicit CPU fixtures, not observed core registers.',
                'The native Nestopia screenshots/PCM were not produced by this source pipeline. No IRQ/NMI clock or PPU pixel timing equivalence is claimed.',
                'Observed idle settled menus/selection/return cover only these13A000 inputs, not every city action or monthly/game campaign.'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','preparation_CPU_comparisons_within_cases')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/source-integration.json');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out);raise SystemExit(bool(result['failures']))
