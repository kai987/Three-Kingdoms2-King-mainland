#!/usr/bin/env python3
"""Independent originalCPU comparison for fixed reset/descriptor requests."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.exact_audio_requests import ExactAudioRequests,AudioRequestRegisters,AudioRequestBudget,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import ServiceCall
OUT=ROOT/'analysis/phase16/audio-requests';REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(r):return{k:getattr(r,k)for k in REGS}
def verify(rom,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
    prefix=ROOT/'analysis/phase15/runtime/succession-heir/postbattle-A1';base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
    rows=[];failures=[];guards=[];visited=Counter();counts=Counter()
    def fresh(entry,ident=0,sp=253,channel=4,state=255):
        r=bytearray(base_ram);r[0xE1]=34;r[0x7F6]=15
        for x in range(0,242,22):r[0x700+x]=state;r[0x701+x]=channel
        r[0x100+((sp+1)&255)]=0x67;r[0x100+((sp+2)&255)]=0x24
        return r,base_sram,dict(a=ident,x=23,y=31,p=32,sp=sp,pc=entry)
    def compare(group,entry,ident=0,sp=253,channel=4,state=255,missing=False,budget=200000):
        r,s,initial=fresh(entry,ident,sp,channel,state)
        a=ServiceMemory(rom,r,s,(6,25,26,31));b=ServiceMemory(rom,r,s,(6,25,26,31));rr=AudioRequestRegisters(**initial);c=MPU(memory=a)
        for k,v in initial.items():setattr(c,k,v)
        owner=ExactAudioRequests(b,rom,None if missing else SceneSharedServices(b,rom))
        try:
            result=owner.run_entry(entry,registers=rr,max_blocks=budget)
            assert result['status']in('returned','dependency','budget'),result
            for n in range(100000):
                if(n or result['status']=='budget')and c.pc==rr.pc and c.sp==rr.sp and a.banks==b.banks:
                    if result['status']=='returned'or(reg(c)==reg(rr)and a.ram==b.ram and a.sram==b.sram):break
                if c.pc<0x8000:raise RuntimeError('Original escaped callerboundary')
                bank=a.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1;c.step()
            else:raise RuntimeError(f'Original budget${c.pc:04X};source${rr.pc:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y];sd=[(i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y];rg={k:(getattr(c,k),getattr(rr,k))for k in REGS if getattr(c,k)!=getattr(rr,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:10],SRAM=sd[:5],registers=rg)
            assert a.io_writes==b.io_writes and a.io_reads==b.io_reads and a.banks==b.banks and a.n163_ram==b.n163_ram
            comparison='complete_return'if result['status']=='returned'else'strict_prefix';counts[group+':'+comparison]+=1
            rows.append(dict(group=group,entry=entry,input=dict(id=ident,SP=sp,oldchannel=channel,oldstate=state),comparison=comparison,source_status=result['status'],initial_registers=initial,final_registers=reg(rr),original_instructions=n,port_writes=len(b.io_writes),final_banks=list(b.banks),source_original_CPU_callbacks=0))
            return owner,b,rr
        except Exception as exc:
            failures.append(dict(group=group,entry=entry,input=dict(id=ident,SP=sp,channel=channel,state=state),error=str(exc)))
            if len(failures)<=10:print(json.dumps(failures[-1]),flush=True)
    for entry,count in[(0xE609,1),(0xE66B,8),(0xE673,7),(0xE67B,6),(0xE683,5),(0xE68B,4),(0xE693,3),(0xE69B,2)]:
        ids=(0,8,80,175)if quick else range(184-count)
        for ident in ids:compare('legitimate_descriptors_and_sequences',entry,ident)
    for entry in(0xE57F,0xE590,0xE683,0xE673,0xE67B):
        for sp in((0,1,127,241,253,255)if quick else range(256)):compare('all256_caller_stack_reset_or_request',entry,8 if entry>=0xE673 else 0,sp=sp)
    for channel in(range(0,12,3)if quick else range(12)):
        for state in(0,1,128,255):compare('active_APU_disable_or_N163_branch',0xE609,8,channel=channel,state=state)
    # Rawbyte255→0 sequence reads descriptor255 as originaldata. It is an
    # explicit byteedge fixture, not a named legitimate music request.
    compare('raw_descriptor255_and_IDwrap_to0',0xE69B,255)
    compare('missing_F25F_real_call',0xE609,missing=True)
    compare('budget_before_first_operation',0xE57F,budget=0)
    for name,kwargs in[
        ('actual_registers_required',{}),('decimal',dict(registers=AudioRequestRegisters(p=40))),
        ('wrong_entry',dict(entry=0xE6C6,registers=AudioRequestRegisters())),('returnword',dict(registers=AudioRequestRegisters(),return_pc=0x1234)),
        ('negative_budget',dict(registers=AudioRequestRegisters(),max_blocks=-1))]:
        r,s,_=fresh(0xE57F);m=ServiceMemory(rom,r,s);before=(bytes(m.ram),bytes(m.sram),list(m.io_writes))
        try:ExactAudioRequests(m,rom).run_entry(**kwargs)
        except ValueError:pass
        else:raise AssertionError('Guard'+name)
        assert before==(bytes(m.ram),bytes(m.sram),list(m.io_writes));guards.append(name)
    for status in(None,'waiting','blocked','returned'):
        r,s,_=fresh(0xE609);m=ServiceMemory(rom,r,s);rr=AudioRequestRegisters(pc=0xE609)
        owner=ExactAudioRequests(m,rom,lambda call,status=status:None if status is None else{'status':status})
        assert owner.run_entry(0xE609,registers=rr)['status']=='dependency';pending=owner.pending;before=(bytes(m.ram),bytes(m.sram),reg(rr),list(m.io_writes))
        assert owner.resume()['status']=='dependency'and owner.pending is pending and before==(bytes(m.ram),bytes(m.sram),reg(rr),list(m.io_writes));guards.append('nonreturned_helper_'+str(status))
    r,s,_=fresh(0xE57F);m=ServiceMemory(rom,r,s);rr=AudioRequestRegisters(pc=0xE57F);owner=ExactAudioRequests(m,rom,SceneSharedServices(m,rom));assert owner.run_entry(registers=rr,max_blocks=0)['status']=='budget'
    assert owner.resume()['status']=='budget'and owner.resume(max_blocks=200000)['status']=='returned';guards.append('budget_requires_explicit_positive_resume')
    sources=['source/recovered/'+x+'.py'for x in('exact_audio_requests','global_ui_controller','scene_shared_services','service_memory','mapped_memory','battle_nmi_services')]+['scripts/verify_exact_audio_requests.py','scripts/analyze_exact_audio_requests.py']
    result=dict(schema='phase16-exact-fixed-audio-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=quick,rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(v for k,v in counts.items()if k.endswith(':complete_return')),strict_prefix_count=sum(v for k,v in counts.items()if k.endswith(':strict_prefix')),source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),rows=rows,failures=failures,guards=guards,source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256={p:sha(ROOT/p)for p in sources},
        comparison=dict(RAM_bytes=2048,free_stack='included',SRAM_bytes=8192,AXYP_SP_PC=True,ordered_ports_reads_banks=True,N163_image=True),executed_original_locations=[dict(physical_bank=b,cpu_address=pc,rom_offset=f,visits=v)for(b,pc,f),v in sorted(visited.items())],
        limits=['OriginalCPU is the independentvalidator only. FixedF25F is recoveredsource, zeroCPUcallback in productionor sourcecomposition.',
            '183 legitimate descriptorrecords supplytypedinputs; controlledchannel/state/SP cases are not naturalcore recordings.',
            'Orderedsoftware port and N163image equality does not synthesizePCM,time,IRQ or readiness.'])
    (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','failed_count')}));return result
def genuine_callers(rom):
    """One originalA00C consumer yields actualJSRframes; notNative CPUtrace."""
    meta_path=ROOT/'analysis/phase16/succession/actual-callee-inputs/player-defeat-successor-observed-g02-n02-city-013-004.json'
    meta=json.loads(meta_path.read_text());prefix=Path(str(meta_path)[:-5]);r=Path(str(prefix)+'-ram.bin').read_bytes();s=Path(str(prefix)+'-sram.bin').read_bytes()
    a=ServiceMemory(rom,r,s,tuple(meta['actual_banks']));c=MPU(memory=a)
    for k,v in meta['initial_registers'].items():setattr(c,k,v)
    parent_return=meta['actual_return_PC'];parent_sp=meta['actual_return_SP'];contexts=[];previous=None
    for n in range(100000):
        if n and c.pc==parent_return and c.sp==parent_sp:break
        if previous is not None and c.pc in ExactAudioRequests.PUBLIC_ENTRIES:
            pc=previous;bank=a.banks[(pc-0x8000)//8192]
            if a[pc]==0x20 and (a[pc+1]|a[pc+2]<<8)==c.pc:
                contexts.append(dict(registers=reg(c),RAM=bytes(a.ram),SRAM=bytes(a.sram),banks=tuple(a.banks),call_pc=pc,call_bank=bank,
                    n163=bytes(a.n163_ram),n163_address=a.n163_address,n163_autoincrement=a.n163_autoincrement))
        previous=c.pc;c.step()
    else:raise RuntimeError('Originalparent A00C budget')
    rows=[];failures=[];artifacts={str(meta_path.relative_to(ROOT)):sha(meta_path)};dest=OUT/'actual-callee-inputs';dest.mkdir(exist_ok=True)
    for index,x in enumerate(contexts):
        entry=x['registers']['pc'];suffix=dest/f'player-frame6276-call{index:02d}-{entry:04X}'
        ret=((x['RAM'][0x100+((x['registers']['sp']+1)&255)]|x['RAM'][0x100+((x['registers']['sp']+2)&255)]<<8)+1)&65535;ret_sp=(x['registers']['sp']+2)&255
        info={k:v for k,v in x.items()if k not in('RAM','SRAM','n163')};info.update(return_PC=ret,return_SP=ret_sp,n163_hex=x['n163'].hex(),source_parent=str(meta_path.relative_to(ROOT)),provenance='GenuineoriginalJSR inside controlledoriginalCPU A00C consumer from frozenNativeRAM; notNativeinternaltrace')
        Path(str(suffix)+'-ram.bin').write_bytes(x['RAM']);Path(str(suffix)+'-sram.bin').write_bytes(x['SRAM']);Path(str(suffix)+'.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
        for ext in('-ram.bin','-sram.bin','.json'):artifacts[str(Path(str(suffix)+ext).relative_to(ROOT))]=sha(str(suffix)+ext)
        aa=ServiceMemory(rom,x['RAM'],x['SRAM'],x['banks']);b=ServiceMemory(rom,x['RAM'],x['SRAM'],x['banks'])
        for m in(aa,b):m.n163_ram[:]=x['n163'];m.n163_address=x['n163_address'];m.n163_autoincrement=x['n163_autoincrement']
        cc=MPU(memory=aa);rr=AudioRequestRegisters(**x['registers'])
        for k,v in x['registers'].items():setattr(cc,k,v)
        try:
            result=ExactAudioRequests(b,rom,SceneSharedServices(b,rom)).run_entry(entry,registers=rr);assert result['status']=='returned'
            for steps in range(100000):
                if steps and cc.pc==ret and cc.sp==ret_sp:break
                cc.step()
            else:raise RuntimeError('Originalgenuine callee budget')
            assert aa.ram==b.ram and aa.sram==b.sram and reg(cc)==reg(rr)and aa.io_writes==b.io_writes and aa.io_reads==b.io_reads and aa.banks==b.banks and aa.n163_ram==b.n163_ram
            rows.append(dict(input=str(suffix.relative_to(ROOT)),entry=entry,caller_PC=x['call_pc'],initial_registers=x['registers'],final_registers=reg(rr),comparison='complete_return',completion_kind='actual_caller_RTS',original_instructions=steps,source_original_CPU_callbacks=0))
        except Exception as exc:failures.append(dict(index=index,entry=entry,error=str(exc)))
    source_paths=['source/recovered/exact_audio_requests.py','source/recovered/global_ui_controller.py','source/recovered/scene_shared_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py','scripts/verify_exact_audio_requests.py']
    receipt=dict(schema='phase16-native-input-originalCPU-audio-caller-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,rom_cpu_case_count=len(rows),complete_return_count=len(rows),strict_prefix_count=0,source_guard_case_count=0,failed_count=len(failures),failures=failures,rows=rows,
        source_original_CPU_callbacks=0,native_internal_CPU_trace=False,source_sha256={p:sha(ROOT/p)for p in source_paths},artifact_sha256=artifacts,parent_originalCPU_preparation_steps=n,parent_case_count_not_added=1,
        limits=['Source cases are genuine originalJSR audio frames created by originalA00C software from NativeRAM/SRAM + explicitcallback context, not observedNestopia registers.',
            'The parentA00C preparation and19nestedserviceorigins are not newcoreframes or extraNativeparentcases.',
            'This19callee-input group is separate from the fullaudio-bodymatrix; fullRAM/SRAM/registers/ports/banks/N163allmatch.'])
    (OUT/'actual-callers.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=receipt['status'],CPU=len(rows),failed=len(failures),parent_steps=n)));return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--genuine-only',action='store_true');a=p.parse_args();r=genuine_callers(a.rom.read_bytes())if a.genuine_only else verify(a.rom.read_bytes(),a.quick);raise SystemExit(bool(r['failures']))
