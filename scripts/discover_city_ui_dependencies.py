#!/usr/bin/env python3
"""Original-CPU-only city callee discovery from the frozen native RAM inputs.

This is not a production adapter or source-completion proof. Original fixed
mapper/OAM helpers reconstruct the declared callback context before27A000.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.battle_graphics_services import ROM_SHA256
REGS=('a','x','y','p','sp','pc')
INPUTS=(0,1,2,3,4,0xA,0xB,0xC,0xD,0x12,0x13,0x7A,0x78,0x7C,0x7E,0x81,0x87,0xA4,0x300,0x304,0x400,0x401,0x40C,0x40D,0x410,0x470,0x471)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def reg(cpu):return {k:getattr(cpu,k)for k in REGS}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'));p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/dependencies');a=p.parse_args()
    rom=a.rom.read_bytes();assert sha(rom)==ROM_SHA256;out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    runtime=ROOT/'analysis/phase13/runtime';cases=[];calls=[];actual_entries=[];snapshots=Counter()
    selected={'city-menu-cancel-cycle':('icons-ready','domestic-menu','domestic-officer-choice','military-menu','military-target-choice','resource-menu','town-menu','town-weapon-officer-choice','world-map-return'),
              'world-officer-browse-cycle':('officer-info-first','officer-info-next','officer-info-first-again','officer-info-closed')}
    for name,labels in selected.items():
        receipt=json.loads((runtime/name/'validation.json').read_text());assert receipt['status']=='passed'and not receipt['additional_core_memory_writes']
        for label in labels:
            prefix=runtime/name/label;ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
            b=PortBus(rom);b.ram[:]=ram;b.sram[:]=sram;b.banks=[ram[0xDE]&31,ram[0xDF]&31,ram[0xE0]&31,31];b.bank_initialized=[True]*4;b.protect=0x4C;b.record_ports=True
            cpu=MPU(memory=b);b.cpu=cpu;cpu.a=76;cpu.x=ram[0x7C];cpu.p=32
            def invoke(entry,Y=None,trace=False):
                if Y is not None:cpu.y=Y
                cpu.sp=0xFD;b.ram[0x1FE:0x200]=bytes((255,1));cpu.pc=entry;pending=[]
                for n in range(400000):
                    if cpu.pc==0x200 and cpu.sp==255:return n,'returned'
                    if trace:
                        origin=b.origin(cpu.pc)
                        if origin and b.peek(cpu.pc)==0x20 and(b.peek(cpu.pc+1)|b.peek(cpu.pc+2)<<8)==0xEE07:
                            target=b.peek(cpu.pc+3)|b.peek(cpu.pc+4)<<8;off=origin[1]+16
                            record=dict(case=name,label=label,caller_physical_bank=origin[0],call_PC=cpu.pc,rom_offset=off,
                              inline_target=target,logical_selector=cpu.y,expected_first_code_bank=cpu.y&31,return_PC=(cpu.pc+5)&65535,
                              raw_call_hex=rom[off:off+5].hex(' ').upper(),raw_call_sha256=sha(rom[off:off+5]),registers=reg(cpu),banks=list(b.banks),
                              fields={f'{addr:04X}':b.peek(addr)for addr in INPUTS})
                            calls.append(record);pending.append(record)
                        if pending and cpu.pc==pending[-1]['inline_target']:
                            record=pending.pop();origin=b.origin(cpu.pc)
                            expected=(record['logical_selector']&31)+(1 if cpu.pc>=0xC000 else 0)
                            if origin and origin[0]==expected:
                                boundary=dict(case=name,label=label,physical_bank=origin[0],CPU=cpu.pc,caller_call_PC=record['call_PC'],logical_selector=record['logical_selector'],
                                  registers=reg(cpu),banks=list(b.banks),fields={f'{addr:04X}':b.peek(addr)for addr in INPUTS})
                                key=(origin[0],cpu.pc)
                                if snapshots[key]<2:
                                    capture=out/'callee-inputs'/f'bank{key[0]:02d}-{key[1]:04X}-{snapshots[key]}'
                                    capture.parent.mkdir(parents=True,exist_ok=True);Path(str(capture)+'-ram.bin').write_bytes(b.ram);Path(str(capture)+'-sram.bin').write_bytes(b.sram)
                                    Path(str(capture)+'.json').write_text(json.dumps(dict(boundary,RAM_sha256=sha(b.ram),SRAM_sha256=sha(b.sram),
                                        fixture='original CPU callback reconstruction from native end-of-frame RAM, not core-internal trace'),ensure_ascii=False,indent=2)+'\n')
                                    boundary['snapshot_prefix']=str(capture.relative_to(ROOT));snapshots[key]+=1
                                actual_entries.append(boundary)
                    b.pc=cpu.pc;b.step_no=n;cpu.step()
                return 400000,'prefix_budget'
            prepare=[]
            for entry,Y in((0xF206,None),(0xF25F,ram[0xE1]),(0xF237,0x3B)):
                n,status=invoke(entry,Y);assert status=='returned';prepare.append(dict(entry=entry,Y=Y,instructions=n))
            before=len(calls);n,status=invoke(0xA000,trace=True)
            cases.append(dict(case=name,label=label,native_snapshot=str(prefix.relative_to(ROOT)),RAM_sha256=sha(ram),SRAM_sha256=sha(sram),
                native_city_state=list(ram[0x400:0x40C]),original_preparatory_helpers=prepare,entry=0xA000,physical_pair=[27,28],
                status=status,original_instructions=n,far_call_count=len(calls)-before,stop_registers=reg(cpu),stop_banks=list(b.banks),port_writes=len(b.ports)))
    grouped=Counter(f'b{item["physical_bank"]}:{item["CPU"]:04X}'for item in actual_entries)
    result=dict(schema='phase13-original-city-dependency-discovery-v1',status='passed'if all(c['status']=='returned'for c in cases)else'bounded_partial',rom_sha256=ROM_SHA256,
       bounded_original_CPU_cases=len(cases),complete_original_callback_cases=sum(c['status']=='returned'for c in cases),prefix_budget_cases=sum(c['status']!='returned'for c in cases),
       production_source_CPU_callbacks=0,source_equivalence_claim=False,native_internal_CPU_trace=False,original_ROM_modified=False,
       original_cases=cases,original_farcall_sites=calls,actual_farcallee_boundaries=actual_entries,actual_farcallee_counts=dict(grouped),
       dependency_pins={p:sha((ROOT/p).read_bytes())for p in('scripts/discover_city_ui_dependencies.py','scripts/verify_battle_graphics_services.py','scripts/trace_startup.py')},
       provenance=dict(native_manifest='analysis/phase13/runtime/evidence.json',native_manifest_sha256=sha((runtime/'evidence.json').read_bytes()),
                       CPU_fixture='declared AXYP,existing0200caller frame,realF206/F25F/F237 for NMI context; zero syntheticPPUSTATUS/defaultAPU/pads; no IRQ/NMIclock'),
       limits=['These are controlled originalCPU callbacks from observed nativeRAM, not production fallback or core-internalinstruction capture.',
               'A bounded originalCPU prefix cannot be promoted to complete: unknown hardware/cooperative progress remains explicit.',
               'Dynamically observed calls do not prove every main/phase/value path; root static27/28 closure remains separate.'])
    (out/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],cases=len(cases),complete=result['complete_original_callback_cases'],prefix=result['prefix_budget_cases'],callees=dict(grouped)),ensure_ascii=False))
if __name__=='__main__':main()
