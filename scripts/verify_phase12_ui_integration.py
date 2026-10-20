#!/usr/bin/env python3
"""Bounded native-RAM UI callbacks through the pure GameEngine coordinator.

Real fixed mapper/PPU services prepare/consume context. No ready byte is
patched. Native frames do not supply CPU registers/caller frames, so those
are explicitly declared CPU-fixture inputs, not an unmodified native call.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
SCOPE=tuple([*range(0x1B4),*range(0x200,0x800)])
REGS=('a','x','y','p','sp','pc')
RETURN_PC=0xEE4D
def sha(raw):return hashlib.sha256(raw).hexdigest()
def registers(r):return {key:getattr(r,key)for key in REGS}
def differences(a,b,scope):return [(address,a[address],b[address])for address in scope if a[address]!=b[address]]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'));args=p.parse_args()
    rom=args.rom.read_bytes();assert sha(rom)==ROM_SHA256
    native=ROOT/'analysis/phase12/runtime/battle-officer-info'
    receipt=json.loads((native/'validation.json').read_text());assert receipt['status']=='passed'and receipt['additional_core_memory_writes']==0
    points={row['label']:row for row in json.loads((native/'checkpoints.json').read_text())}
    labels=[f'info-row-{index:02d}'for index in range(10)]+['info-open','info-rows-complete']
    counts=Counter();rows=[];failures=[];guards=[]
    files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_phase12_ui_integration.py']
    before_pins={path:sha((ROOT/path).read_bytes())for path in files}
    def bus(label):
        ram=(native/(label+'-ram.bin')).read_bytes();sram=(native/(label+'-sram.bin')).read_bytes()
        b=PortBus(rom);b.ram[:]=ram;b.sram[:]=sram;b.status_mode='zero';b.protect=0x4C
        # Native end-of-frame main caches provide the declared starting map.
        # F25F/F237 below actually reconstruct the NMI data/code windows.
        b.banks=[ram[0xDE]&31,ram[0xDF]&31,ram[0xE0]&31,31];b.bank_initialized=[True]*4;b.record_ports=True
        return b,ram,sram
    def frame(memory,r,entry):
        r.sp=0xFD;r.pc=entry;memory[0x1FE]=(RETURN_PC-1)&255;memory[0x1FF]=(RETURN_PC-1)>>8
    def original_call(b,r,entry,prefix=None):
        frame(b,r,entry);cpu=MPU(memory=b,pc=entry)
        for key in('a','x','y','p','sp'):setattr(cpu,key,getattr(r,key))
        b.cpu=cpu
        for n in range(400000):
            if prefix is None:
                if cpu.pc==RETURN_PC and cpu.sp==255:break
            else:
                memory,source=prefix
                if cpu.pc==source.pc and cpu.sp==source.sp and b.banks==memory.banks and len(b.ports)>=len(memory.io_writes):
                    if all(b.peek(0x100+((cpu.sp+i)&255))==memory[0x100+((cpu.sp+i)&255)]for i in(1,2)):break
            b.pc=cpu.pc;b.step_no=n;cpu.step()
        else:raise RuntimeError(f'Original UI body budget ${cpu.pc:04X}')
        for key in REGS:setattr(r,key,getattr(cpu,key))
        return n
    def compare(label,kind,entry,code_selector,consume_packet=False):
        b,raw_ram,raw_sram=bus(label);m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:0},repeat_read_ports=(0x2002,))
        game=GameEngine(m,rom=rom,mapped=True);coordinator=game.readable_scene_rules()
        r=NMIRegisters(a=76,x=raw_ram[0x7C],y=0,p=32,sp=253);actual=NMIRegisters(a=76,x=raw_ram[0x7C],y=0,p=32,sp=253)
        stages=[];prepared=[]
        try:
            for target,selector,description in ((0xF25F,raw_ram[0xE1],'actual NMI data-window selector helper'),
                                                 (0xF237,code_selector,'actual NMI code-window selector helper')):
                r.y=actual.y=selector;frame(m,r,target)
                result=coordinator(ServiceCall(target,RETURN_PC,'declared_existing_fixture_caller',r,m,tuple(m.banks),255))
                assert result['status']=='returned',result
                n=original_call(b,actual,target);prepared.append(dict(entry=target,Y=selector,original_instructions=n,description=description))
            if consume_packet:
                frame(m,r,0xEE53);result=coordinator(ServiceCall(0xEE53,RETURN_PC,'real_original_PPU_dispatch',r,m,tuple(m.banks),255))
                assert result['status']=='returned',result
                n=original_call(b,actual,0xEE53);stages.append(dict(entry=0xEE53,original_instructions=n,PPU_jobs_after=m[0x7E]))
                assert not m[0x7E]&4 and not b.peek(0x7E)&4
                # EE53 tail-routes to the actual29/30 packet consumer; it
                # legitimately leaves that code window selected. Re-enter
                # the producer only after the real fixedF237 selector.
                r.y=actual.y=code_selector;frame(m,r,0xF237)
                result=coordinator(ServiceCall(0xF237,RETURN_PC,'actual_code_window_return_to_producer',r,m,tuple(m.banks),255))
                assert result['status']=='returned',result
                n=original_call(b,actual,0xF237);stages.append(dict(entry=0xF237,Y=code_selector,original_instructions=n))
            frame(m,r,entry);result=coordinator(ServiceCall(entry,RETURN_PC,'real_UI_body_existing_caller_fixture',r,m,tuple(m.banks),255))
            prefix=result['status']=='dependency'
            if prefix:
                assert kind=='battle_A244_info_phase'and label=='info-rows-complete',result
                assert r.pc==0xA012 and m.banks[1:3]==[23,24],(registers(r),m.banks)
            else:assert result['status']=='returned',result
            n=original_call(b,actual,entry,(m,r)if prefix else None);stages.append(dict(entry=entry,original_instructions=n))
            rd=differences(b.ram,m.ram,SCOPE);sd=differences(b.sram,m.sram,range(8192));rg=[(key,getattr(actual,key),getattr(r,key))for key in REGS if getattr(actual,key)!=getattr(r,key)]
            assert not rd and not sd and not rg,(rd[:10],sd[:6],rg)
            assert b.ports==m.io_writes,(len(b.ports),len(m.io_writes));assert b.banks==m.banks,(b.banks,m.banks)
            counts[kind+('_strict_prefix'if prefix else'')]+=1
            rows.append(dict(kind=kind,comparison='strict_prefix'if prefix else'complete_return',native_snapshot_label=label,native_frame=points[label]['frame'],
                 snapshot_RAM_sha256=sha(raw_ram),snapshot_SRAM_sha256=sha(raw_sram),entry=entry,caller_return_PC=RETURN_PC,
                 actual_mapper_prepare=prepared,actual_body_stages=stages,
                 native_battle_state=list(raw_ram[0x500:0x502]),native_UI_control=list(raw_ram[0x40C:0x418]),
                 UI_control_after=list(m.ram[0x40C:0x418]),PPU_jobs_before=raw_ram[0x7E],PPU_jobs_after=m[0x7E],
                 original_registers=registers(actual),source_registers=registers(r),source_callbacks=coordinator.calls,
                 original_instructions=sum(stage['original_instructions']for stage in prepared+stages),
                 port_writes=len(m.io_writes),ordered_ports_sha256=sha(json.dumps(m.io_writes,separators=(',',':')).encode()),
                 banks_after=list(m.banks),all_declared_RAM_equal=True,all_SRAM_equal=True,AXYP_SP_PC_equal=True,
                 original_CPU_callback_on_source_side=0,native_CPU_registers_observed=False,
                 legacy_FF_marker_not_completion=(label=='info-rows-complete'),
                 pending_dependency=dict(physical_bank=23,CPU=0xA012,logical_selector=0x37,
                      reason='DirectA244 on preinitialized frame31 requests additional graphics after B; actualA000 uses its realphase0 and returns')if prefix else None))
        except Exception as exc:
            failure=dict(kind=kind,native_snapshot_label=label,entry=entry,error=str(exc));failures.append(failure)
            if len(failures)<=6:print(json.dumps(failure,ensure_ascii=False),flush=True)
    for label in labels:
        compare(label,'actual_25A012_callback',0xA012,0x39)
        compare(label,'battle_A244_info_phase',0xA244,0x2C)
        compare(label,'battle_A000_info_wrapper',0xA000,0x2C)
    # Native rows1..9 have a queued packet. Consume its actual bit4 owner
    # through EE53, then call the next producer, without writing an ack.
    for index in range(1,10):compare(f'info-row-{index:02d}','real_PPU_packet_consume_then_25A012',0xA012,0x39,True)
    # Direct native old FF marker must remain explicitly uncompleted.
    initial_marker=next(r for r in rows if r['kind']=='actual_25A012_callback'and r['native_snapshot_label']=='info-rows-complete')
    assert initial_marker['native_frame']==31 and initial_marker['native_UI_control'][1]==255 and initial_marker['UI_control_after'][1]==255
    guards.append('frame31_inherited_FF_is_only_original_early_return_not_completed_details')
    after_pins={path:sha((ROOT/path).read_bytes())for path in files}
    if before_pins!=after_pins:failures.append(dict(stage='source_dependency_changed_during_run',paths=[path for path in files if before_pins[path]!=after_pins[path]]))
    output=dict(schema='phase12-pure-UI-integration-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),actual_ROM_CPU_comparison_count=sum(counts.values()),complete_return_count=sum(row['comparison']=='complete_return'for row in rows),strict_prefix_count=sum(row['comparison']=='strict_prefix'for row in rows),
        source_guard_case_count=len(guards),source_guards=guards,case_count=sum(counts.values())+len(guards),counts=dict(counts),failed_count=len(failures),failures=failures,rows=rows,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,source_regs_or_mapper_completion_stub=False,
        compared_RAM_addresses=SCOPE,compared_RAM_bytes=len(SCOPE),all_SRAM_bytes=8192,returned_registers=list(REGS),ordered_ports_and_final_banks_compared=True,
        caller_and_registers_are_explicit_CPU_fixture=True,gameplay_RAM_ready_or_result_pokes=0,
        native_inputs=dict(directory=str(native.relative_to(ROOT)),validation_sha256=sha((native/'validation.json').read_bytes()),checkpoints_sha256=sha((native/'checkpoints.json').read_bytes()),
                          labels=labels,raw_native_fields_preserved=True,frame31_legacy_artifact_label_is_inherited_FF=True,true_completed_checkpoint='info-open',true_completed_native_frame=272),
        source_sha256=after_pins,source_dependency_hashes_stable_during_run=before_pins==after_pins,
        limitations=['Native snapshots supply RAM/SRAM only; AXYP,SP/realEE4Dreturn frame are declared CPUfixture inputs, not an internalcore call capture.',
                    'F25F/F237 are actually executed by pure/CPU sides to reconstruct NMI bank context; no manual cache/mapper protocol shortcut.',
                    'Busy packet cases may have a legal earlyRTS. Separate9cases use the actualEE53 consumer before producing the next row.',
                    'Frame31 artifact named info-rows-complete contains inheritedoldFF before0..9; it is not completed UI. Genuine completed screenshot is info-open at272.',
                    'DirectA244 on that not-yetinitialized frame31 is an extra entryfixture and stops at real23A012 graphics dependency; it is not a failed legitimateA000 callback.',
                    'Inactive01B4..01FF stackresidue excluded; actual AXYP,SP/PC,all otherRAM/allSRAM,orderedports/banks included.',
                    'No completeNMI/IRQ/frame/PCM/sourcepixel claim; callbacks and45boundedfunctionsequences are separate from1164attack matrix.'])
    out=ROOT/'analysis/phase12/ui-integration.json';out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:output[key]for key in('status','rom_cpu_case_count','source_guard_case_count','counts','failed_count')},ensure_ascii=False))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
