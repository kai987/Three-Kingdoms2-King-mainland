#!/usr/bin/env python3
"""Original CPU writer provenance from the frozen phase14 succession fixtures.

Actual audio callee frames are captured inside the explicitNMI2 software
sequence, then compared with the new pure source. This is not a Nestopia
internal trace and no script writes ack/readiness/results after entry.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.audio_scene_services import AudioSceneServices,AudioRegisters,ROM_SHA256
from source.recovered.audio_services import AudioServices,AudioData
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def trace(rom,out):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;out.mkdir(parents=True,exist_ok=True);inputs=out/'actual-callee-inputs';inputs.mkdir(exist_ok=True)
    receipt=ROOT/'analysis/phase14/cooperation-integration.json';old=json.loads(receipt.read_text());assert old['status']=='passed'
    mother=ROOT/'analysis/phase11/runtime/cold-battle/city-commands'
    ram=Path(str(mother)+'-ram.bin').read_bytes();sram=Path(str(mother)+'-sram.bin').read_bytes()
    rows=[];failures=[];sequences=[];artifact_pins={str(receipt.relative_to(ROOT)):sha(receipt)};data=AudioData.from_rom(rom)
    for row in old['rows']:
        if row['group']!='main2_succession_actual_NMI2_resume':continue
        heir=row['input']['heir'];a=ServiceMemory(rom,ram,sram,(16,10,11,31),read_ports={0x2002:0,0x4015:0,0x4016:0,0x4017:0},repeat_read_ports=(0x2002,0x4015,0x4016,0x4017))
        for k,v in row['input']['prepared_bytes'].items():a[int(k)]=v
        owned=[i for i in range(30)if a[0x6000+32*i]&7==0]
        for slot in range(20):a[0x664+slot]=255
        for ruler in range(7):
            leader=a[0x6F07+8*ruler];a[0x63C0+12*leader+11]=(a[0x63C0+12*leader+11]&252)|(3 if ruler==0 else 2)
        for city in owned:
            for j in range(10):a[0x6000+32*city+17+j]=255
        if heir:
            o=16+11*8192+0xAD8;pointer=int.from_bytes(rom[o:o+2],'little');candidate=rom[16+11*8192+(pointer&8191)]
            a[0x6000+32*owned[0]+17]=candidate;a[0x63C0+12*candidate+5]=owned[0];a[0x63C0+12*candidate+11]=(a[0x63C0+12*candidate+11]&252)|2
        a[0xDE:0xE4]=bytes([48,42,43,48,59,60]);a.io_writes=[]
        c=MPU(memory=a)
        for k,v in row['initial_registers'].items():setattr(c,k,v)
        pause=0xCB79 if heir else 0xCA7F
        for main_steps in range(1000000):
            if main_steps and c.pc==pause and c.sp==251 and c.a==(252 if heir else 251)and c.p==161:break
            c.step()
        else:raise RuntimeError('Original controlledmain did not reach genuineack wait')
        paused=reg(c);checkpoints=[]
        for tick in range(1,11):
            c.nmi();total=0
            while not(total and c.pc==pause and c.sp==251):
                if total>100000:raise RuntimeError('Original NMI budget')
                if c.pc==0xA003 and tuple(a.banks[1:3])==(14,15):
                    prefix=inputs/f'{"heir"if heir else"no-heir"}-NMI-{tick:02d}'
                    rp=Path(str(prefix)+'-ram.bin');sp=Path(str(prefix)+'-sram.bin');jp=Path(str(prefix)+'.json')
                    rp.write_bytes(a.ram);sp.write_bytes(a.sram);initial=reg(c);banks=list(a.banks)
                    ret=((a[0x100+((c.sp+1)&255)]|a[0x100+((c.sp+2)&255)]<<8)+1)&65535;expected_sp=(c.sp+2)&255
                    jp.write_text(json.dumps(dict(provenance='Controlled originalCPU E066 mainpaused, explicitNMI2, genuineF8CBJSR audio entry; notNativeinternaltrace',
                        ROM_sha256=ROM_SHA256,registers=initial,banks=banks,actual_return_PC=ret,actual_return_SP=expected_sp,heir=heir,NMI=tick),indent=2)+'\n')
                    for p in(rp,sp,jp):artifact_pins[str(p.relative_to(ROOT))]=sha(p)
                    b=ServiceMemory(rom,a.ram,a.sram,tuple(banks));b.n163_ram[:]=a.n163_ram;b.n163_address=a.n163_address;b.n163_autoincrement=a.n163_autoincrement
                    r=AudioRegisters(**initial);shared=SceneSharedServices(b,rom);source=AudioSceneServices(b,rom,shared)
                    result=source.run_entry(registers=r);assert result['status']=='returned'
                    legacy=ServiceMemory(rom,a.ram,a.sram,tuple(banks));legacy.n163_ram[:]=a.n163_ram
                    legacy_r=AudioRegisters(**initial);legacy_result=AudioServices(legacy,data).tick(registers=legacy_r);assert legacy_result['status']=='returned'
                    # Existing facade's real callerRTS after the semanticbody:
                    for m,rr in((legacy,legacy_r),):
                        rr.sp=(rr.sp+1)&255;lo=m[0x100+rr.sp];rr.sp=(rr.sp+1)&255;hi=m[0x100+rr.sp];rr.pc=((lo|hi<<8)+1)&65535
                    start_ports=len(a.io_writes);writes=[]
                    for n in range(100000):
                        if n and c.pc==ret and c.sp==expected_sp:break
                        if a.banks[2]==15 and c.pc in(0xDF92,0xDF93):
                            writes.append(dict(bank=15,CPU_PC=c.pc,ROM_offset=16+15*8192+(c.pc&8191),raw_hex='48',opcode='PHA',
                                stack_address=0x100+c.sp,value=c.a,slot_X=c.x,slot_volume=a[0x706+c.x],port_group=a[0x7F5],registers_before=reg(c)))
                        c.step()
                    else:raise RuntimeError('Original audio callee budget')
                    rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y];sd=[(i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
                    rg={k:(getattr(c,k),getattr(r,k))for k in REGS if getattr(c,k)!=getattr(r,k)}
                    if rd or sd or rg or a.io_writes[start_ports:]!=b.io_writes or a.banks!=b.banks:
                        failures.append(dict(heir=heir,NMI=tick,RAM=rd[:12],SRAM=sd[:6],registers=rg))
                    rows.append(dict(heir=heir,NMI=tick,actual_callee_input=str(prefix.relative_to(ROOT)),initial_registers=initial,final_registers=reg(c),
                        comparison='complete_return',completion_kind='actual_caller_RTS',original_audio_instructions=n,return_PC=ret,return_SP=expected_sp,
                        actual_stack_writers=writes,legacy_semantic_idle_stack_differences=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,legacy.ram))if x!=y],
                        new_source_RAM_differences=rd,new_source_SRAM_differences=sd,new_source_register_differences=rg,
                        new_source_ordered_ports_equal=a.io_writes[start_ports:]==b.io_writes,new_source_banks_equal=a.banks==b.banks,
                        source_original_CPU_callbacks=0))
                    total+=n
                else:c.step();total+=1
            checkpoints.append(dict(NMI=tick,paused_registers=reg(c),request=a[0x6F8B],city_phase=a[0x401],counter=a[0x40C],stack_01EC=a[0x1EC]))
        sequences.append(dict(heir=heir,original_main_instructions=main_steps,original_wait_registers=paused,explicit_NMI_arrivals=10,
            ack_injected=False,request_after=a[0x6F8B],checkpoints=checkpoints))
    sources=['source/recovered/'+x+'.py'for x in('audio_scene_services','global_ui_controller','scene_shared_services','audio_services','service_memory','mapped_memory','battle_nmi_services')]
    sources+=['scripts/trace_cooperation_audio_writer.py']
    result=dict(schema='phase15-controlled-original-NMI-audio-writer-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=len(rows),complete_return_count=len(rows),strict_prefix_count=0,source_guard_case_count=0,failed_count=len(failures),failures=failures,
        rows=rows,sequences=sequences,source_original_CPU_callbacks=0,native_internal_CPU_trace=False,core_frames_generated=0,
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers='AXYP/SP/PC',free_stack_residue='included',ordered_ports_banks=True),
        source_sha256={p:sha(ROOT/p)for p in sources},artifact_sha256=artifact_pins,
        limits=['Uses frozenphase14 declaredCPU fixtures. E066main and explicitNMI are originalCPU context preparation, notextraCPUcase totals.',
            'The20audio entrycomparisons reuse genuineF8CBcallerframes; no furtherAXYP/stackpreparation or NMIaudio replacement is planted.',
            'Source side executes newdirectPython and recoveredF25F only; originalCPU is the independentoracle and caller-context producer.',
            'Legacysemantic audio differences are diagnostic of its declaredexcluded idle-stack contract, not unknowncallees.',
            'NoNativeinternaltrace, newNestopiacoreframes, PCM synthesis or hardwarecycle timing are asserted.'])
    (out/'writer-provenance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],CPU=len(rows),failures=len(failures),actual_01EC_writers=[dict(heir=r['heir'],NMI=r['NMI'],writer=w)for r in rows for w in r['actual_stack_writers']if w['stack_address']==0x1EC][:4]),ensure_ascii=False))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase15/audio-domain');a=p.parse_args()
    result=trace(a.rom.read_bytes(),a.out);raise SystemExit(bool(result['failures']))
