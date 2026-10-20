#!/usr/bin/env python3
"""Original-ROM CPU comparisons for independently readable audio services."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.audio_services import AudioData,AudioServices,AudioDataUnavailable,ROM_SHA256,REQUEST_COUNTS,SLOTS,DECLARED_RAM_RANGES
from source.recovered.service_memory import ServiceMemory


class AudioOracleBus(Bus):
    def __init__(self,rom,ram,sram):
        super().__init__(rom,'zero');self.ram[:]=ram;self.sram[:]=sram
        self.banks[:]=[2,14,15,31];self.bank_initialized=[True]*4;self.protect=0x4C
        self.port_writes=[]
    def __setitem__(self,address,value):
        if ServiceMemory.is_write_port(address&65535):self.port_writes.append({'address':address&65535,'value':value&255})
        super().__setitem__(address,value)
    def __getitem__(self,address):
        if isinstance(address,int)and 0x2000<=address<0x6000:
            raise RuntimeError(f'Unexpected audio hardware read ${address:04X}; no invented input')
        return super().__getitem__(address)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/audio');p.add_argument('--quick',action='store_true')
    a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=AudioData.from_rom(rom)
    rng=random.Random(0xA0D10);counts=Counter();failures=[];samples=[];visited=set();commands=Counter();guards=[]
    compared_RAM=[i for i in range(2048)if not 0x100<=i<0x200]
    def fresh():
        ram=bytearray(rng.randbytes(2048));sram=bytearray(rng.randbytes(8192))
        for x in SLOTS:ram[0x700+x]=255;ram[0x701+x]=x//22&7
        ram[0x7F2:0x7FA]=bytes(8);ram[0x1FE:0x200]=bytes((255,1))
        return ram,sram
    def run_original(bus,entry,regs):
        cpu=MPU(memory=bus);bus.cpu=cpu;cpu.pc=entry
        for k,v in vars(regs).items():setattr(cpu,k,v)
        for n in range(1000000):
            if n and cpu.pc==0x200:return cpu,n
            bus.pc=cpu.pc;bus.step_no=n
            origin=bus.origin(cpu.pc)
            if origin:visited.add((origin[0],cpu.pc))
            cpu.step()
        raise AssertionError(f'Original instruction budget at ${cpu.pc:04X}')
    def compare(group,entry,ram,sram,call,label=None,registers=None):
        regs=registers or SimpleNamespace(a=0,x=0,y=0,p=32,sp=0xFD)
        source_regs=SimpleNamespace(**vars(regs));bus=AudioOracleBus(rom,ram,sram)
        memory=ServiceMemory(rom,ram,sram,banks=(2,14,15,31));rules=AudioServices(memory,data)
        try:
            result=call(rules,source_regs)
            assert result['status']=='returned',result
            cpu,n=run_original(bus,entry,regs)
            rd=[(hex(i),bus.ram[i],memory.ram[i])for i in compared_RAM if bus.ram[i]!=memory.ram[i]]
            sd=[(i,x,y)for i,(x,y)in enumerate(zip(bus.sram,memory.sram))if x!=y]
            actual={k:getattr(cpu,k)for k in ('a','x','y','p')};expected={k:getattr(source_regs,k)for k in ('a','x','y','p')}
            assert not rd and not sd,(rd[:16],sd[:4])
            assert memory.io_writes==bus.port_writes,('ports',memory.io_writes[:12],bus.port_writes[:12],len(memory.io_writes),len(bus.port_writes))
            assert memory.n163_ram==bus.sound,('N163 register image',list(memory.n163_ram),list(bus.sound))
            assert memory.banks==bus.banks,('banks',memory.banks,bus.banks)
            assert actual==expected and cpu.sp==(source_regs.sp+2)&255,('registers',actual,expected,cpu.sp,source_regs.sp)
            counts[group]+=1
            if sum(r['group']==group for r in samples)<4:
                samples.append(dict(group=group,label=label,original_entry=entry,original_instructions=n,
                    returned_registers=actual,body_SP=source_regs.sp,original_after_RTS_SP=cpu.sp,
                    port_write_count=len(bus.port_writes),ports=bus.port_writes,result=result))
            return memory.ram[:],memory.sram[:]
        except Exception as exc:
            failures.append(dict(group=group,label=label,error=f'{type(exc).__name__}: {exc}'))
            return None

    # Complete reset including active prior channel replacement/disable paths.
    for scenario in range(8 if a.quick else 32):
        ram,sram=fresh()
        for x in SLOTS:
            ram[0x700+x]=[255,0,2,127][scenario%4];ram[0x701+x]=(scenario+x//22)&7
        regs=SimpleNamespace(a=scenario,x=(scenario*11)&255,y=255-scenario,p=32|((scenario*37)&~8&255),sp=0xFD)
        compare('complete_reset',0xE57F,ram,sram,lambda e,r:e.reset(registers=r),label=scenario,registers=regs)

    for entry,count in REQUEST_COUNTS.items():
        ids=[0,0x1D,0x7B]if a.quick else range(data.descriptor_count-count+1)
        for ident in ids:
            for previous in (255,2):
                ram,sram=fresh()
                for x in SLOTS:ram[0x700+x]=previous
                ram[0x7F6]=255;regs=SimpleNamespace(a=ident,x=(ident*3)&255,y=ident^255,p=32,sp=0xFD)
                compare('complete_request_wrappers',entry,ram,sram,lambda e,r:e.request(ident,entry=entry,registers=r),label=[entry,ident,previous],registers=regs)

    # Every descriptor's genuine stream across multiple ticks and priority mixes.
    ids=[0,8,18,29,65,0x7B]if a.quick else range(data.descriptor_count)
    frames=8 if a.quick else 40
    for ident in ids:
        ram,sram=fresh();mem=ServiceMemory(rom,ram,sram,banks=(2,14,15,31));AudioServices(mem,data).request(ident,entry=0xE609)
        ram,sram=mem.ram[:],mem.sram[:]
        for frame in range(frames):
            result=compare('original_descriptor_stream_ticks',0xD8D4,ram,sram,lambda e,r:e.tick(registers=r),label=[ident,frame])
            if result is None:break
            ram,sram=result
    for first,entry in [(0,0xE66B),(8,0xE683),(18,0xE67B),(29,0xE673),(0x7B,0xE68B)]:
        ram,sram=fresh();mem=ServiceMemory(rom,ram,sram,banks=(2,14,15,31));AudioServices(mem,data).request(first,entry=entry)
        ram,sram=mem.ram[:],mem.sram[:]
        for frame in range(8 if a.quick else 128):
            result=compare('continuous_multichannel_priority_ticks',0xA003,ram,sram,lambda e,r:e.tick(registers=r),label=[first,entry,frame])
            if result is None:break
            ram,sram=result

    if not a.quick:
        # Caller-owned stack position can wrap. Only the originalCPU executes
        # RTS; the source returns exact bodySP/AXYP without planting a return.
        for sp in range(256):
            for entry in (0xE57F,0xE609,0xE673,0xE68B,0xD8D4):
                ram,sram=fresh();ram[0x100+((sp+1)&255)]=255;ram[0x100+((sp+2)&255)]=1
                regs=SimpleNamespace(a=0x1D,x=(sp*7)&255,y=sp,p=32|(sp&~8),sp=sp)
                call=(lambda e,r:e.reset(registers=r))if entry==0xE57F else (lambda e,r:e.tick(registers=r))if entry==0xD8D4 else (lambda e,r:e.request(0x1D,entry=entry,registers=r))
                compare('caller_owned_all256_SP_body_registers',entry,ram,sram,call,label=[sp,entry],registers=regs)
        # Explicit RAM music-data fixtures exercise every note/rest byte, all
        # logicalchannel classes and both pitch-table variants. ROM is unchanged.
        for channel in range(8):
            for tempo_variant in (0,128):
                for note in range(160):
                    ram,sram=fresh();ram[0x700]=0;ram[0x701]=channel
                    ram[0x702:0x704]=bytes((0,4));ram[0x400:0x408]=bytes((0,2,31,8,note,1,255,0))
                    # AE sets the header variant beforetheactualnote.
                    ram[0x404:0x40A]=bytes((0xAE,tempo_variant,note,1,255,0))
                    compare('RAM_music_all160_notes_all8_channels_both_variants',0xD8D4,ram,sram,
                            lambda e,r:e.tick(registers=r),label=[channel,tempo_variant,note])
        patterns={
            'positive_volume_slide':[0xD2,2,0x30,16,255,0],
            'negative_volume_slide':[0xE2,2,0x30,16,255,0],
            'envelope':[0xC3,7,0x30,16,255,0],
            'volume_and_sweep_and_wave':[0xA0,0x1F,0xA1,0x89,0xA2,3,0x30,16,255,0],
            'vibrato':[0xA3,0x21,0x30,16,255,0],
            'vibrato_disable':[0xA3,0x21,0xA3,128,0x30,16,255,0],
            'clear_channel_flags':[0xA3,0x21,0xA4,0,0x30,16,255,0],
            'loop_marker_and_counter':[0xFD,0,0x30,1,0xB2,0,255,0],
            'loop_absolute_and_counter':[0x30,1,0xB2,2,255,0],
            'relative_base_new_header':[0xAD,0,0,0,31,8,0x30,16,255,0],
            'relative_base_nonzero_original_RAM_pointer':[0xAD,1,255,0],
            'tempo_low_and_high':[0xAF,2,0xAE,128,0x30,16,255,0],
            'unused_F_commands':[0xF0,0,0xF1,0,0xFC,0,0xFE,0,0x30,16,255,0],
            'unused_A_commands':[v for cmd in range(0xA5,0xAD)for v in (cmd,0)]+[0x30,16,255,0],
        }
        for channel in range(8):
            for name,stream in patterns.items():
                ram,sram=fresh();ram[0x700]=0;ram[0x701]=channel;ram[0x702:0x704]=bytes((0,4))
                ram[0x400:0x404]=bytes((0,2,31,8));ram[0x404:0x404+len(stream)]=bytes(stream)
                # AD nonzero's originalF1 quirk continues through RAM0006.
                ram[6:8]=bytes((0x30,16))
                for frame in range(8):
                    result=compare('RAM_music_control_commands_continuous_ticks',0xD8D4,ram,sram,
                                   lambda e,r:e.tick(registers=r),label=[channel,name,frame])
                    if result is None:break
                    ram,sram=result
        # Duplicate logical channels reach DC31's real stack-unwind path.
        # Earlier slots own output; later slots retain note/tempo/envelope state.
        for channel in range(8):
            for scenario in range(4):
                ram,sram=fresh()
                for x,pointer in ((0,0x400),(22,0x440)):
                    ram[0x700+x]=0;ram[0x701+x]=channel
                    ram[0x702+x]=pointer&255;ram[0x703+x]=pointer>>8
                    stream=[0,2,31 if x==0 else 24,8,0xA3,0x21,0xC3,7,0x30,16,255,0]
                    if scenario==1 and x==0:stream=[0,2,31,8,255,0]
                    if scenario==2 and x==22:stream=[0,2,31,8,0x3C,16,255,0]
                    if scenario==3 and x==22:stream=[0,2,31,8,0xD2,2,0x30,16,255,0]
                    ram[pointer:pointer+len(stream)]=bytes(stream)
                for frame in range(8):
                    result=compare('duplicate_channel_priority_stack_unwind',0xD8D4,ram,sram,
                                   lambda e,r:e.tick(registers=r),label=[channel,scenario,frame])
                    if result is None:break
                    ram,sram=result
        # Actual infiniteB0 loop: bothsourceandCPU stop at a real data prefix,
        # with no sound/note/end or callerRTS fabricated.
        ram,sram=fresh();ram[0x700]=0;ram[0x701]=0;ram[0x702:0x704]=bytes((0,4))
        ram[0x400:0x406]=bytes((0,0,31,8,0xB0,2))
        mem=ServiceMemory(rom,ram,sram,banks=(2,14,15,31));result=AudioServices(mem,data).tick(command_budget=1)
        bus=AudioOracleBus(rom,ram,sram);cpu=MPU(memory=bus);bus.cpu=cpu;cpu.sp=253;cpu.p=32;cpu.pc=0xD8D4;hits=0
        for n in range(100000):
            if cpu.pc==0xD9BD:
                hits+=1
                if hits==2:break
            bus.pc=cpu.pc;cpu.step()
        good=result['status']=='budget'and result['contract_registers']is None and hits==2 and all(mem.ram[i]==bus.ram[i]for i in compared_RAM)and mem.sram==bus.sram and mem.io_writes==bus.port_writes
        if good:counts['original_B0_loop_budget_prefix']+=1
        else:failures.append(dict(group='original_B0_loop_budget_prefix',result=result,pc=cpu.pc))

    for ident,entry in [(-1,0xE609),(183,0xE609),(182,0xE68B),(0,0xE6C6)]:
        ram,sram=fresh();mem=ServiceMemory(rom,ram,sram);before=mem.ram[:]
        try:AudioServices(mem,data).request(ident,entry=entry);okay=False
        except(ValueError,AudioDataUnavailable):okay=mem.ram==before and not mem.io_writes
        guards.append(dict(sequence_id=ident,entry=entry,passed=okay))
        if not okay:failures.append(dict(group='source_guard',input=[ident,entry]))
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    report=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=a.quick,
        rom_cpu_case_count=sum(counts.values()),source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(failures),
        original_complete_case_count=sum(counts.values())-counts['original_B0_loop_budget_prefix'],
        original_prefix_case_count=counts['original_B0_loop_budget_prefix'],
        counts=dict(counts),failures=failures,samples=samples,source_guards=guards,
        compared_SRAM_bytes=8192,compared_RAM_addresses=compared_RAM,declared_audio_RAM_ranges=DECLARED_RAM_RANGES,
        original_instruction_locations=len(visited),port_sequence_compared=True,N163_register_image_compared=True,
        hardware_read_inputs='No audio path reads a hardware port in these cases; unexpected reads fail explicitly.',
        register_contract='AXYP final body values match original; SP before callerRTS is restored. Free stack residue excluded; actual originalRTS executes only in validator.',
        source_uses_IR_or_original_CPU=False,PCM_synthesis=False,
        source_sha256=hashlib.sha256((ROOT/'source/recovered/audio_services.py').read_bytes()).hexdigest(),
        validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=['Validation models observable register writes; it does not synthesize sound or claim fullNES timing.',
                     'Explicit RAM music command fixtures test code branches; they are not natural campaign or ROM music modifications.',
                     'AXYP/SP comparisons use decimal-cleared originalCPU contexts; NES2A03 binary arithmetic is the source contract.',
                     'Source audio request IDs are bounded to the original183 descriptors, not arbitrary following music bytes.',
                     'E6C6 controller sampling and E70E palette upload are separate services.'])
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(visited)],indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ('status','quick','rom_cpu_case_count','source_guard_case_count','failed_count','counts','original_instruction_locations')},ensure_ascii=False))
    if failures:
        print(json.dumps(failures[:12],ensure_ascii=False,indent=2));sys.exit(1)


if __name__=='__main__':main()
