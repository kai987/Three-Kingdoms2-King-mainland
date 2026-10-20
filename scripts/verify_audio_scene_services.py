#!/usr/bin/env python3
"""Original CPU differential for exact audio body, actual frames and idle RAM."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.audio_scene_services import AudioSceneServices,AudioRegisters,AudioBlockBudget,ROM_SHA256
from source.recovered.audio_services import AudioServices,AudioData,SLOTS
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import ServiceCall
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def verify(rom,out,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;out.mkdir(parents=True,exist_ok=True)
    parent=ROOT/'analysis/phase11/runtime/cold-battle/city-commands'
    mother_ram=Path(str(parent)+'-ram.bin').read_bytes();mother_sram=Path(str(parent)+'-sram.bin').read_bytes()
    data=AudioData.from_rom(rom);counts=Counter();rows=[];failures=[];visited=Counter();guards=[];writers=[]
    def fresh():
        r=bytearray(mother_ram);s=bytearray(mother_sram);r[0x700:0x7F2]=bytes(242);r[0x7F2:0x7FA]=bytes(8)
        for x in SLOTS:r[0x700+x]=255;r[0x701+x]=x//22&7
        r[0xE1:0xE4]=bytes([34,46,47]);return r,s
    def compare(group,r,s,meta,*,entry=0xA003,sp=241,p=32,mode='complete',budget=200000):
        a=ServiceMemory(rom,r,s,(2,14,15,31));b=ServiceMemory(rom,r,s,(2,14,15,31))
        for m in(a,b):m[0x100+((sp+1)&255)]=0xCD;m[0x100+((sp+2)&255)]=0xF8
        rr=AudioRegisters(a=17,x=31,y=63,p=p,sp=sp,pc=entry);initial=reg(rr);c=MPU(memory=a)
        for k,v in initial.items():setattr(c,k,v)
        shared=SceneSharedServices(b,rom)
        def service(call):
            if call.target!=0xF25F:return {'status':'dependency','reason':'Only real F25F is owned by this bounded source service'}
            return shared(call)
        ctrl=AudioSceneServices(b,rom,service if mode!='missing'else None)
        try:
            result=ctrl.run_entry(entry,registers=rr,max_blocks=budget)
            assert result['status']==('returned'if mode=='complete'else'budget'if mode=='budget'else'dependency'),result
            write_rows=[]
            for n in range(300000):
                if n and c.pc==rr.pc and c.sp==rr.sp:
                    if mode=='complete'or(reg(c)==reg(rr)and a.ram==b.ram and a.sram==b.sram):break
                if c.pc<0x8000:raise RuntimeError(f'Original unexpectedly entered RAM ${c.pc:04X}')
                bank=a.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1
                if bank==15 and c.pc in(0xDF92,0xDF93):
                    write_rows.append(dict(physical_bank=bank,CPU_PC=c.pc,ROM_offset=16+15*8192+(c.pc&8191),opcode='PHA',raw_hex='48',
                        address=0x100+c.sp,value=c.a,SP_before=c.sp,N163_port_group=a[0x7F5],slot_X=c.x,slot_volume=a[0x706+c.x]))
                c.step()
            else:raise RuntimeError(f'Original budget ${c.pc:04X},source ${rr.pc:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y];sd=[(i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
            rg={k:(getattr(c,k),getattr(rr,k))for k in REGS if getattr(c,k)!=getattr(rr,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:6],registers=rg)
            assert a.io_writes==b.io_writes and a.io_reads==b.io_reads and a.banks==b.banks
            assert a.n163_ram==b.n163_ram
            comparison='complete_return'if mode=='complete'else'strict_prefix';counts[group+':'+comparison]+=1
            rows.append(dict(group=group,input=meta,entry=entry,comparison=comparison,source_status=result['status'],initial_registers=initial,final_registers=reg(rr),
                original_instructions=n,control_blocks=result['control_blocks'],final_banks=list(b.banks),port_write_count=len(b.io_writes),
                ordered_ports_sha256=hashlib.sha256(json.dumps(b.io_writes,separators=(',',':')).encode()).hexdigest(),DF92_DF93_writers=write_rows,source_original_CPU_callbacks=0))
            if write_rows and not writers:writers.extend(write_rows)
            if mode=='missing':
                before=(bytes(b.ram),bytes(b.sram),reg(rr),list(b.io_writes),list(b.banks));again=ctrl.resume()
                assert again['status']=='dependency'and before==(bytes(b.ram),bytes(b.sram),reg(rr),list(b.io_writes),list(b.banks))
                guards.append('same_missing_F25F_does_not_fake_RTS')
                ctrl.services=service;continued=ctrl.resume();assert continued['status']=='returned'
                for extra in range(10000):
                    if extra and c.pc==rr.pc and c.sp==rr.sp:break
                    c.step()
                else:raise RuntimeError('Resumed original fixedhelper budget')
                assert a.ram==b.ram and a.sram==b.sram and reg(c)==reg(rr)and a.io_writes==b.io_writes and a.banks==b.banks
                counts['same_missing_F25F_source_resumed:complete_return']+=1
                rows.append(dict(group='same_missing_F25F_source_resumed',entry=entry,comparison='complete_return',initial_prefix_group=group,
                    original_instructions=extra,final_registers=reg(rr),source_original_CPU_callbacks=0))
            return b.ram[:],b.sram[:]
        except Exception as exc:
            failures.append(dict(group=group,input=meta,entry=entry,SP=sp,error=str(exc)))
            if len(failures)<=8:print(json.dumps(failures[-1]),flush=True)
            return r,s
    ids=(0,8,18,29,65,123)if quick else range(183)
    for ident in ids:
        r,s=fresh();m=ServiceMemory(rom,r,s,(2,14,15,31));AudioServices(m,data).request(ident,entry=0xE609);r,s=m.ram[:],m.sram[:]
        for tick in range(2 if quick else 4):r,s=compare('actual_ROM_descriptor_ticks',r,s,dict(descriptor=ident,tick=tick))
    # Real data command branches, not runtime CPU opcode fixtures. Every
    # logicalchannel class has note/loop/volume/envelope/relativeheader data.
    patterns={
        'volume_wave_sweep':[0xA0,31,0xA1,137,0xA2,3,0x30,16,255,0],
        'volume_envelope':[0xC3,7,0x30,16,255,0],
        'positive_slide':[0xD2,2,0x30,16,255,0],
        'negative_slide':[0xE2,2,0x30,16,255,0],
        'vibrato_flags':[0xA3,33,0xA3,128,0xA4,0,0x30,16,255,0],
        'loop_marker_and_counter':[0xFD,0,0x30,1,0xB2,0,255,0],
        'relative_new_header':[0xAD,0,0,0,31,8,0x30,16,255,0],
        'pitch_and_tempo':[0xAF,2,0xAE,128,0x30,16,255,0],
        'unused_A_F_tokens':[0xA5,0,0xAC,0,0xF1,0,0xFE,0,0x30,16,255,0],
    }
    for channel in(range(0,8,3)if quick else range(8)):
        for name,stream in patterns.items():
            r,s=fresh();r[0x700]=0;r[0x701]=channel;r[0x702:0x704]=bytes([0,4]);r[0x400:0x404]=bytes([0,2,31,8]);r[0x404:0x404+len(stream)]=bytes(stream)
            for tick in range(3 if quick else 8):r,s=compare('music_data_controls_continuous',r,s,dict(channel=channel,pattern=name,tick=tick),entry=0xD8D4)
    for sp in((0,1,127,241,253,255)if quick else range(256)):
        r,s=fresh();r[0x700]=0;r[0x701]=4;r[0x702:0x704]=bytes([0,4]);r[0x400:0x408]=bytes([0,2,24,8,0x30,16,255,0])
        compare('all256_actual_caller_stack_and_N163_PHA',r,s,dict(SP=sp),sp=sp,p=(sp|32)&~8)
    for channel in(range(0,8,3)if quick else range(8)):
        r,s=fresh()
        for x,pointer in((0,0x400),(22,0x440)):
            r[0x700+x]=0;r[0x701+x]=channel;r[0x702+x]=pointer&255;r[0x703+x]=pointer>>8
            r[pointer:pointer+8]=bytes([0,2,31 if x==0 else 24,8,0x30,16,255,0])
        for tick in range(3 if quick else 8):r,s=compare('duplicate_channel_real_stack_unwind',r,s,dict(channel=channel,tick=tick),entry=0xD8D4)
    # Absent F25F and a genuinely infiniteB0 token loop are explicit prefixes.
    r,s=fresh();compare('missing_F25F_actual_call_boundary',r,s,None,mode='missing')
    r,s=fresh();r[0x700]=0;r[0x701]=0;r[0x702:0x704]=bytes([0,4]);r[0x400:0x406]=bytes([0,0,31,8,0xB0,2])
    compare('actual_B0_data_loop_budget',r,s,None,mode='budget',budget=32)
    for name,kwargs,banks in[
        ('missing_actual_registers',{},(2,14,15,31)),('decimal_protocol',dict(registers=AudioRegisters(p=40)),(2,14,15,31)),
        ('negative_budget',dict(registers=AudioRegisters(),max_blocks=-1),(2,14,15,31)),('wrong_entry',dict(entry=0xA000,registers=AudioRegisters()),(2,14,15,31)),
        ('wrong_mapping',dict(registers=AudioRegisters()),(2,12,13,31)),
        ('return_PC_mismatches_actual_stack',dict(registers=AudioRegisters(),return_pc=0x2222),(2,14,15,31))]:
        r,s=fresh();m=ServiceMemory(rom,r,s,banks);before=(bytes(m.ram),bytes(m.sram),list(m.io_writes));g=AudioSceneServices(m,rom)
        try:g.run_entry(**kwargs)
        except ValueError:pass
        else:raise AssertionError('Missing guard '+name)
        assert before==(bytes(m.ram),bytes(m.sram),list(m.io_writes));guards.append(name)
    r,s=fresh();m=ServiceMemory(rom,r,s,(2,12,13,31));rr=AudioRegisters(pc=0xA003);before=(bytes(m.ram),bytes(m.sram),reg(rr))
    result=AudioSceneServices(m,rom)(ServiceCall(0xA003,0xF8CE,'wrong_owner',rr,m,tuple(m.banks),255));assert result['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),reg(rr));guards.append('wrong_pair_preserves_actual_caller')
    for status in(None,'waiting','blocked','returned'):
        r,s=fresh();m=ServiceMemory(rom,r,s,(2,14,15,31));m[0x1FE:0x200]=bytes([0xCD,0xF8]);rr=AudioRegisters(pc=0xA003)
        def invalid(call,status=status):return None if status is None else{'status':status}
        ctrl=AudioSceneServices(m,rom,invalid);result=ctrl.run_entry(registers=rr)
        assert result['status']=='dependency'and rr.pc==0xF25F and rr.sp==251
        before=(bytes(m.ram),bytes(m.sram),reg(rr),list(m.io_writes),list(m.banks));call=ctrl.pending
        assert ctrl.resume()['status']=='dependency'and ctrl.pending is call and before==(bytes(m.ram),bytes(m.sram),reg(rr),list(m.io_writes),list(m.banks))
        guards.append('helper_'+str(status)+'_without_real_PC_SP_cannot_complete')
    r,s=fresh();m=ServiceMemory(rom,r,s,(2,14,15,31));m[0x1FE:0x200]=bytes([0xCD,0xF8]);rr=AudioRegisters(pc=0xA003)
    ctrl=AudioSceneServices(m,rom,SceneSharedServices(m,rom));result=ctrl.run_entry(registers=rr,max_blocks=0)
    before=(bytes(m.ram),bytes(m.sram),reg(rr),list(m.io_writes),list(m.banks));assert ctrl.resume()['status']=='budget'and before==(bytes(m.ram),bytes(m.sram),reg(rr),list(m.io_writes),list(m.banks))
    result=ctrl.resume(max_blocks=200000);assert result['status']=='returned'and rr.pc==0xF8CE and rr.sp==255
    guards.append('explicit_budget_preserves_caller_until_positive_resume_budget')
    sources=['source/recovered/'+x+'.py'for x in('audio_scene_services','global_ui_controller','scene_shared_services','battle_nmi_services','controller_helpers','audio_services','service_memory','mapped_memory')]+['scripts/verify_audio_scene_services.py']
    result=dict(schema='phase15-exact-audio-caller-protocol-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=quick,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(v for k,v in counts.items()if k.endswith(':complete_return')),
        strict_prefix_count=sum(v for k,v in counts.items()if k.endswith(':strict_prefix')),source_guard_case_count=len(guards),failed_count=len(failures),
        counts=dict(counts),rows=rows,failures=failures,guards=guards,source_original_CPU_callbacks=0,source_IR_interpretation=False,
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers='AXYP/SP/PC',free_stack_residue='included',ordered_ports_banks_reads=True,N163_image=True),
        source_sha256={p:sha(ROOT/p)for p in sources},DF92_DF93_first_original_writers=writers,
        executed_original_locations=[dict(physical_bank=b,cpu_address=p,rom_offset=o,visits=n)for(b,p,o),n in sorted(visited.items())],
        limits=['The original6502 comparator is confined to this validator;F25F is the independent fixed source helper.',
            'Music commands are game data; RAMtoken fixtures are declared serviceinputs, not naturalcampaign captures or alteredROM.',
            'Original descriptor and stack matrices do not claim everypossible audio branch/value is tested.',
            'Registers/stack/orderedports are verified; this service synthesizes no PCM/time/IRQ or completionflags.',
            'MissingF25F prefix is deliberately unprovided in the test; productioncoordinator already ownsF25F.'])
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','failed_count')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase15/audio-domain');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out,a.quick);raise SystemExit(bool(result['failures']))
