#!/usr/bin/env python3
"""Compare composed extinction/reset/continuation with original CPU software.

Native snapshots provide memory only. Registers, interrupts, controller pulses
and PPU edges here are explicit CPU fixtures, never native internal traces.
Each whole sequence counts once; nested main/NMI/IRQ events are not extra cases.
"""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.player_extinction import PlayerExtinction,PlayerLossEnding
from source.recovered.extinction_scene_services import ExtinctionGlobalUI

REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(r):return{k:getattr(r,k)for k in REGS}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert sha(a.rom)==ROM_SHA256
    out=ROOT/'analysis/phase17';out.mkdir(parents=True,exist_ok=True)
    files=sorted(str(x.relative_to(ROOT))for x in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_phase17_integration.py']
    pins={f:sha(ROOT/f)for f in files};artifacts={};rows=[];failures=[];visited=Counter();guards=[]
    def equal(left,right,r,c):
        rd=[(i,x,y)for i,(x,y)in enumerate(zip(left.ram,right.ram))if x!=y]
        sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(left.sram,right.sram))if x!=y]
        rg={k:[getattr(c,k),getattr(r,k)]for k in REGS if getattr(c,k)!=getattr(r,k)}
        assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:12],registers=rg)
        assert left.io_reads==right.io_reads and left.io_writes==right.io_writes and left.banks==right.banks and left.n163_ram==right.n163_ram
    def original(left,right,r,c,result):
        for n in range(1000000):
            if n and c.pc==r.pc and c.sp==r.sp:
                if result['status']in('returned','reset_boundary')or(reg(c)==reg(r)and left.ram==right.ram and left.sram==right.sram and left.io_writes==right.io_writes):return n
            if c.pc<0x8000:raise RuntimeError(f'Original RAMPC{c.pc:04X}')
            bank=left.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1;c.step()
        raise RuntimeError(f'Original budget{c.pc:04X}; source{r.pc:04X}/{result["status"]}')
    for case,mode in [('single-player-empty-rosters-reset',0),('two-player-empty-rosters-continue',1)]:
        folder=out/'runtime'/case;checkpoint_path=folder/'checkpoints.json';points=json.loads(checkpoint_path.read_text());artifacts[str(checkpoint_path.relative_to(ROOT))]=sha(checkpoint_path)
        point=next(x for x in points if x['global_state']==1 and x['active_main']==13 and x['active_phase']==0)
        data=[]
        for k in('RAM','SRAM'):
            f=folder/point[k];data.append(f.read_bytes());artifacts[str(f.relative_to(ROOT))]=sha(f)
        ram,sram=data;banks=(ram[0xDE]&31,ram[0xDF]&31,ram[0xE0]&31,31)
        def memory():return ServiceMemory(rom,ram,sram,banks,read_ports={0x2002:0,0x5800:127,0x4015:0},repeat_read_ports=(0x2002,0x5800,0x4015),controller_buttons=(0,0))
        left,right=memory(),memory();initial=dict(a=17,x=31,y=63,p=32,sp=255,pc=0xE066);r=NMIRegisters(**initial);c=MPU(memory=left)
        for k,v in initial.items():setattr(c,k,v)
        game=GameEngine(right,rom=rom,mapped=True);co=game.readable_scene_rules();session=game.readable_campaign(r)
        assert isinstance(co.global_ui,ExtinctionGlobalUI)and isinstance(co.controller(8),PlayerLossEnding)
        assert isinstance(game.battle_succession_rules(),PlayerExtinction)and co.external_callback is None
        states=[];inputs=[];irq_count=main_count=nmi_count=steps=0;saw_ending=False;reset_seen=False
        try:
            assert right[0x6F43]==mode
            for tick in range(3000):
                ruler=right[0x6F03];control=right[0x6F0A+8*ruler]&3 if ruler<7 else 0
                buttons=(1 if tick%32<8 else 0);ports=(buttons,0)if control!=1 else(0,buttons)
                for m in(left,right):m.controller_buttons=ports
                inputs.append(dict(tick=tick,controller_buttons=list(ports),declared_hardware_inputs=True))
                result=session.main();steps+=original(left,right,r,c,result);equal(left,right,r,c);main_count+=1
                assert result['status']=='returned',result
                result=session.nmi();c.nmi();steps+=original(left,right,r,c,result);equal(left,right,r,c);nmi_count+=1
                arrivals=0
                while result['status']not in('returned','reset_boundary'):
                    assert result['status']=='dependency',result
                    if r.pc in(0xE00C,0xE011,0xE032,0xE037):
                        assert mode==0 and saw_ending
                        # The boot software is genuinely paused at its own
                        # vblank read. Supply edges at this boundary, after
                        # earlier NMI PPU reads, then resume the same owner.
                        for m in(left,right):m.read_ports[0x2002]=deque([128,0]*8)
                        inputs[-1]['PPUSTATUS_reset_edges']=[128,0]*8
                        result=session.resume();steps+=original(left,right,r,c,result);equal(left,right,r,c)
                        continue
                    assert r.pc==0xFB28,result
                    if right[0x62]:
                        child=session.irq();c.irq();steps+=original(left,right,r,c,child);equal(left,right,r,c);irq_count+=1;arrivals+=1
                    else:
                        result=session.resume();steps+=original(left,right,r,c,result);equal(left,right,r,c)
                    assert arrivals<10
                fields=[right[0x7A],right[0x78],right[0x400],right[0x401],right[0x4CB],right[0x6F43],right[0x6F03],right[0x6F17],right[0x300],right[0x304]]
                if not states or states[-1]['fields']!=fields:states.append(dict(tick=tick,fields=fields))
                saw_ending |= fields[:2]==[14,8]
                if result['status']=='reset_boundary':
                    assert mode==0 and saw_ending and r.pc==0xE066 and r.sp==255 and co.reset_epoch==1
                    reset_seen=True;break
                if mode==1 and saw_ending and fields[0]==2 and fields[2:4]==[0,1]and fields[6]==4 and fields[8:]==[255,255]:break
            else:raise RuntimeError('3000 explicit NMI arrivals did not finish the declared boundary')
            assert right[0x6F17]==255 and saw_ending and right[0x6F43]==0
            assert reset_seen==(mode==0)
            assert any(x['kind']=='player_loss_ending'for x in co.calls)
            rows.append(dict(case=case,comparison='reset_boundary'if mode==0 else'complete_return',completion_kind='actual_E000_nonlocal_E066'if mode==0 else'main_E066_and_actual_NMI_IRQ_RTI_sequence',input_checkpoint=point['label'],input_provenance='Native memory after original ordinary-attack death; explicit E066 registers, no result/state/ready/ack writes',initial_registers=initial,final_registers=reg(r),main_updates=main_count,explicit_NMI_arrivals=nmi_count,explicit_IRQ_arrivals=irq_count,original_instructions=steps,states=states,hardware_input_plan=inputs,source_original_CPU_callbacks=0,source_IR_interpretation=False,all_event_comparisons_equal=True,RAM_bytes=2048,SRAM_bytes=8192,reset_epoch=co.reset_epoch,owner_counts=dict(Counter(x['kind']for x in co.calls))))
            print(json.dumps(dict(case=case,status='passed',NMI=nmi_count,IRQ=irq_count,reset=reset_seen)),flush=True)
        except Exception as exc:failures.append(dict(case=case,error=str(exc),registers=reg(r),states=states[-20:]))
    guards=['actual_postbattle_subclass_selected','actual_NMI8_loss_subclass_selected','global_audio_and_loss_composition_without_CPU_IR_fallback']
    assert pins=={f:sha(ROOT/f)for f in files},'Source changed during sequences; rerun after freeze'
    result=dict(schema='phase17-composed-player-extinction-original-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=len(rows),source_guard_case_count=len(guards),complete_return_count=sum(x['comparison']=='complete_return'for x in rows),reset_boundary_count=sum(x['comparison']=='reset_boundary'for x in rows),strict_prefix_count=0,failed_count=len(failures),failures=failures,rows=rows,guards=guards,source_sha256=pins,artifact_sha256=artifacts,source_original_CPU_callbacks=0,source_IR_interpretation=False,native_internal_CPU_trace=False,comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,AXYP_SP_PC=True,idle_stack='included',ordered_IO_banks_N163=True),limits=['Two parent sequences only; nested main/interrupt events are not additional CPU cases or native frames.','Declared input pulses/PPUSTATUS edges are identical CPU-oracle fixtures, not automatic native hardware timing.','Whole new-game scenario after title is validated by separate native run; this source sequence stops at real E000/E066 or remaining-player world return.'])
    (out/'source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'integration-executed-instructions.json').write_text(json.dumps(dict(schema='phase17-integration-executed-original-instructions-v1',instruction_count=len(visited),original_instructions=[dict(physical_bank=b,pc=pc,rom_offset=off,raw_hex=rom[off:off+1].hex(),execution_count=count)for(b,pc,off),count in sorted(visited.items())]),indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],CPU=len(rows),guards=len(guards),failures=failures),ensure_ascii=False))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
