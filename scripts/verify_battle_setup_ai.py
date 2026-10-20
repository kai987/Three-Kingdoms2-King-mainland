#!/usr/bin/env python3
"""Actual-ROM setup/NMI auxiliary checks, with explicit service contracts."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_scene_controller import ObservableBus,VerificationOnlyExternalCPU
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.battle_background_initialization import BattleBackgroundInitialization
from source.recovered.battle_nmi_services import ServiceCall
from source.recovered.battle_setup_ai import BattleSetupAI,SetupRegisters,ROM_SHA256,strategy_profile,ordered_noncommander_triplets
RAM_SCOPE=tuple(range(0x1B4))+tuple(range(0x200,0x800))

def verify(rom,out,quick=False):
    base=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(base)+'-ram.bin').read_bytes();sram=Path(str(base)+'-sram.bin').read_bytes()
    counts=Counter();failures=[];rows=[];external_calls=Counter();guards=[];rng=random.Random(0x11A100)
    def fresh(prep):
        b=ObservableBus(rom,ram,sram);b.banks=[2,8,9,31];b.ram[0xDE:0xE4]=bytes([34,40,41,34,40,41]);b.ram[0x1FE:0x200]=bytes([255,1]);b.ram[0x7C]=0
        for a,v in prep.items():b[a]=v
        b.ports.clear();b.port_reads.clear();return b
    def compare(entry,prep,label,mode='pure_shared',regs=None,semantic=None):
        a=fresh(prep);b=fresh(prep);registers=SetupRegisters(a=17,x=31,y=63,p=32)
        for k,v in(regs or{}).items():setattr(registers,k,v)
        initial=vars(registers).copy()
        shared=SceneSharedServices(b,rom);background=BattleBackgroundInitialization(b,rom)
        def pure_services(call):return background(call)if call.target==0xF09C else shared(call)
        services=pure_services if mode=='pure_shared'else VerificationOnlyExternalCPU()
        model=BattleSetupAI(b,rom,services)
        try:
            if entry==0xF09C:
                registers.pc=entry;model.registers=registers
                call=ServiceCall(entry,0x200,'call',registers,b,tuple(b.banks),255)
                result=background(call);result['control_blocks']=0
            else:result=model.run_entry(entry,registers=registers,seed_return=True)
            cpu=MPU(memory=a,pc=entry);a.cpu=cpu
            for k,v in initial.items():setattr(cpu,k,v)
            cpu.pc=entry;cpu.sp=253
            for n in range(1500000):
                if n and cpu.pc==model.registers.pc and cpu.sp==model.registers.sp and a.banks==b.banks:break
                a.pc=cpu.pc;a.step_no=n;cpu.step()
            else:raise RuntimeError(f'Original budget ${cpu.pc:04X}')
            # Shared graphics/BCD services do not promise free CPU-stack bytes.
            scope=RAM_SCOPE
            rd=[(i,a.ram[i],b.ram[i])for i in scope if a.ram[i]!=b.ram[i]]
            sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
            rg={k:(getattr(cpu,k),getattr(model.registers,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(model.registers,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:12],registers=rg)
            assert a.ports==b.ports,(a.ports[:10],b.ports[:10]);assert a.port_reads==b.port_reads
            assert result['status']=='returned',result['status']
            if semantic:semantic(a,b)
            counts[label['kind']]+=1
            rows.append(dict(entry=entry,input=label,mode=mode,original_instructions=n,source_blocks=result['control_blocks'],comparison='complete_return'))
            if isinstance(services,VerificationOnlyExternalCPU):external_calls.update(services.calls)
        except Exception as exc:
            failures.append(dict(entry=entry,input=label,mode=mode,error=str(exc),source_PC=model.registers.pc))
            if len(failures)<=10:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
    ruler_range=range(2 if quick else 7);count_range=(0,3,9)if quick else range(10)
    for ruler in ruler_range:
        other=(ruler+1)%7
        for controllers in range(4):
            for n in count_range:
                city=(ruler*7+n)%30
                prep={0x507:ruler|(other<<4),0x50E:city,0x52A:city,
                  0x6F07+8*ruler+3:3 if controllers&1 else 1,
                  0x6F07+8*other+3:3 if controllers&2 else 1}
                for side in(0,10):
                    for slot in range(10):
                        ident=20+side+slot;prep[0x664+side+slot]=ident if slot<=n else 255
                        prep[0x628+side+slot]=(side//10*128)|(slot%3);prep[0x63C+side+slot]=slot
                        prep[0x63C0+12*ident+1]=(40 if n&1 else(99-slot*7))&255
                before=fresh(prep)
                expected={side:ordered_noncommander_triplets([(before[0x664+side+j],before[0x628+side+j],before[0x63C+side+j])for j in range(1,n+1)],before)for side in(0,10)}
                def semantic(a,b,expected=expected,n=n,controllers=controllers,ruler=ruler,other=other):
                    for side,enabled,owner in((0,controllers&1,ruler),(10,controllers&2,other)):
                        if enabled:
                            actual=tuple((b[0x664+side+j],b[0x628+side+j],b[0x63C+side+j])for j in range(1,n+1))
                            assert actual==expected[side],('sort',actual,expected[side])
                            profile=strategy_profile(owner,side,n,rom)
                            if profile:assert tuple(b[0x6FA1+side+j]for j in range(1,n+1))==profile['strategies']
                        else:assert all(b[0x6FA1+side+j]==255 for j in range(10))
                    assert bytes(b[0x4D8+i]for i in range(8))==bytes([255]*8)
                    assert all(b[0x6F94+i]==0 for i in range(3))
                compare(0xA003,prep,dict(kind='AI_setup_controllers_profiles_ties',ruler=ruler,other=other,controllers=controllers,noncommanders=n,city=city),semantic=semantic)
    # Camera whole-byte request matrix and legal limits; no hardware clock.
    requests=range(8)if quick else range(256)
    for request in requests:
        for x,y in((0,0),(254,142),(16,16),(128,64)):
            compare(0xA021,{0x500:0,0x508:request,0x8E:x,0x90:y,0x9C:165},dict(kind='camera_requests',request=request,x=x,y=y))
    # All original formation route descriptors, including the absent/self
    # fallback. City/candidate inputs are synthetic CPU fixtures, not battles.
    if not quick:
        for city in range(30):
            o=16+16*8192+(0x9D72&8191)+8*city
            origins=[city]+[v for v in rom[o:o+8]if v<30 and v!=city]
            for origin in dict.fromkeys(origins):
                prep={0x507:0x10,0x50E:city,0x52A:origin,0x6F0A:3,0x6F12:3}
                for slot in range(20):
                    prep[0x664+slot]=20+slot;prep[0x628+slot]=128 if slot>=10 else 0;prep[0x63C+slot]=slot%11
                compare(0xA003,prep,dict(kind='all_city_formation_routes',city=city,origin=origin))
    # F09C respects caller tile bias and Y clip, unlike F092 which resets them.
    for flags in range(8 if quick else 256):
        for clip in(0,144,240):
            prep={0:0x15,1:0xD3,2:flags,3:(flags*7)&255,4:clip,0xA:16,0xB:0,0xC:16,0xD:0,0x8E:8,0x8F:0,0x90:8,0x91:0,0x7C:0}
            compare(0xF09C,prep,dict(kind='world_sprite_bias_clip',flags=flags,clip=clip),regs=dict(p=32|(flags&195)))
    for entry in(0xA012,0xA015):
        for state in(0,11,12,15):
            for phase in(0,16,32,64,96,255):
                for animation in(0,1):
                    prep={0x500:state,0x5E:phase,0x4C8:animation,0x8F:0,0x7C:0,0x61:5,0x505:99,0x506:20,0x50E:4}
                    compare(entry,prep,dict(kind='HUD_or_unit_auxiliary',entry=entry,state=state,frame_byte=phase,animation=animation))
    for bad in((-1,0,1),(7,0,1),(0,1,1),(0,0,10)):
        try:strategy_profile(*bad,rom);okay=False
        except ValueError:okay=True
        guards.append(dict(kind='profile_domain',input=bad,passed=okay))
    d=dict(status='passed'if not failures and all(g['passed']for g in guards)else'failed',rom_sha256=ROM_SHA256,
      rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,
      counts=dict(counts),failed_count=len(failures),failures=failures,rows=rows,source_guard_case_count=len(guards),source_guards=guards,
      verification_only_original_CPU_callback_count=sum(external_calls.values()),source_original_CPU_calls=0,source_IR_interpretation=False,
      CPU_registers_compared=True,all_SRAM_compared_bytes=8192,compared_RAM_bytes=len(RAM_SCOPE),declared_RAM_addresses=list(RAM_SCOPE),
      ordered_ports_and_banks_compared=True,free_stack_residue_excluded=True,
      source_pins=[dict(path=f,sha256=hashlib.sha256((ROOT/f).read_bytes()).hexdigest())for f in
        ('source/recovered/battle_setup_ai.py','source/recovered/scene_shared_services.py','source/recovered/battle_background_initialization.py','scripts/verify_battle_setup_ai.py','scripts/verify_battle_scene_controller.py')])
    out.mkdir(parents=True,exist_ok=True);(out/'validation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in d.items()if k in('status','rom_cpu_case_count','counts','failed_count','source_guard_case_count','verification_only_original_CPU_callback_count')}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase11/setup-ai');a=p.parse_args();verify(a.rom.read_bytes(),a.out,a.quick)
