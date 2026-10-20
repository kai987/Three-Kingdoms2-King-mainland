#!/usr/bin/env python3
"""Actual-ROM differential checks for the newly structured battle controller.

External CPU callbacks belong only to this validator. No render/NMI barrier is
bypassed: an unresolved ECEE leaves the source and oracle at that exact prefix.
"""
import argparse,hashlib,json,sys,random
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_scene_controller import BattleSceneController,BattleRegisters,ROM_SHA256

class ObservableBus(Bus):
    def __init__(self,rom,ram,sram):
        super().__init__(rom,'alternating');self.ram[:]=ram;self.sram[:]=sram
        self.banks=[2,12,13,31];self.bank_initialized=[True]*4;self.protect=0x4C
        self.ports=[];self.port_reads=[]
    def __setitem__(self,address,value):
        if isinstance(address,slice):
            for a,v in zip(range(address.start,address.stop),value):self[a]=v
            return
        if ServiceMemory.is_write_port(address&65535):self.ports.append(dict(address=address&65535,value=value&255))
        super().__setitem__(address,value)
    def __getitem__(self,address):
        value=super().__getitem__(address)
        if 0x2000<=address<0x6000:self.port_reads.append(dict(address=address,value=value))
        return value

class VerificationOnlyExternalCPU:
    def __init__(self):self.calls=Counter();self.steps=0
    def __call__(self,call):
        if call.target==0xECEE:return {'status':'dependency','reason':'Unexecuted real NMI/renderer barrier'}
        cpu=MPU(memory=call.memory);call.memory.cpu=cpu
        for k in ('a','x','y','p','sp','pc'):setattr(cpu,k,getattr(call.registers,k))
        self.calls[(call.target,call.kind)]+=1
        for n in range(150000):
            if n and cpu.pc==call.return_pc and cpu.sp==call.expected_sp:break
            if cpu.pc==0xECEE:break
            if call.memory.origin(cpu.pc)is None:raise RuntimeError(f'External original entered RAM ${cpu.pc:04X}')
            call.memory.pc=cpu.pc;call.memory.step_no=n;cpu.step()
        else:raise RuntimeError(f'External callback budget ${cpu.pc:04X} from ${call.target:04X}')
        self.steps+=n
        for k in ('a','x','y','p','sp','pc'):setattr(call.registers,k,getattr(cpu,k))
        return {'status':'returned'if cpu.pc==call.return_pc and cpu.sp==call.expected_sp else'dependency'}

def verify(rom,out,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    catalog=json.loads((ROOT/'analysis/phase11/battle/catalog.json').read_text())
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
    ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
    counts=Counter();failed=[];rows=[];callbacks=Counter();blocked=[];guards=[]
    def fresh(state=0,phase=0,variant=0):
        b=ObservableBus(rom,ram,sram)
        b.ram[0xDE:0xE4]=bytes([34,44,45,34,44,45]);b.ram[0x1FE:0x200]=bytes([255,1])
        b.ram[0x500]=state;b.ram[0x501]=phase;b.ram[0x502]=0;b.ram[0x81]=(0,1,2,3)[variant%4]
        b.ram[0x87]=(0,128,128,0)[variant%4];b.ram[0x7E]=0;b.ram[0x7C]=0;b.ram[0x300]=b.ram[0x304]=255
        b[0x6F92]=b[0x6F93]=0
        if variant>=2:b.ram[0x509]=0;b.ram[0x600]=3;b.ram[0x614]=16;b.ram[0x504]=128
        return b
    def compare(entry,state,phase,variant,mode,preparation=None,regs_input=None):
        a=fresh(state,phase,variant);b=fresh(state,phase,variant)
        for address,value in (preparation or{}).items():a[address]=b[address]=value
        regs=BattleRegisters(a=3 if entry==0xE862 else 17,x=31,y=63,p=32)
        for key,value in(regs_input or{}).items():setattr(regs,key,value)
        initial=vars(regs).copy()
        ext=VerificationOnlyExternalCPU()if mode in('external_CPU','fixed_helpers','scene_wrapper','battle_initialization','duel_outcome')else None
        if mode=='pure_shared':
            from source.recovered.scene_shared_services import SceneSharedServices
            ext=SceneSharedServices(b,rom)
        model=BattleSceneController(b,rom,ext)
        label=dict(entry=entry,state=state,phase=phase,variant=variant,mode=mode)
        try:
            result=model.run_entry(entry,registers=regs,seed_return=True)
            cpu=MPU(memory=a,pc=entry);a.cpu=cpu
            for key,value in initial.items():setattr(cpu,key,value)
            cpu.pc=entry;cpu.sp=253
            stop=model.registers.pc;sp=model.registers.sp;bank=list(b.banks)
            for n in range(1000000):
                if n and cpu.pc==stop and cpu.sp==sp and a.banks==bank:break
                if a.origin(cpu.pc)is None:raise RuntimeError(f'Original entered RAM ${cpu.pc:04X}')
                a.pc=cpu.pc;a.step_no=n;cpu.step()
            else:raise RuntimeError(f'Original budget ${cpu.pc:04X} expected ${stop:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y]
            sd=[(i+0x6000,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
            rg={k:(getattr(cpu,k),getattr(model.registers,k))for k in ('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(model.registers,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:15],SRAM=sd[:10],registers=rg)
            assert a.ports==b.ports,(a.ports[:12],b.ports[:12]);assert a.port_reads==b.port_reads
            kind='complete_return'if result['status']=='returned'else'strict_prefix'
            counts[mode+'_'+kind]+=1
            row={**label,'status':'passed','comparison':kind,'stop_PC':stop,'stop_SP':sp,'original_instructions':n,'source_blocks':result['control_blocks'],'external_CPU_calls':sum(ext.calls.values())if isinstance(ext,VerificationOnlyExternalCPU)else 0,'after':result['after']}
            rows.append(row)
            if isinstance(ext,VerificationOnlyExternalCPU):callbacks.update(ext.calls)
        except Exception as exc:
            failure={**label,'error':str(exc),'source_PC':model.registers.pc}
            if 'budget'in str(exc) or 'External original entered RAM'in str(exc):blocked.append(failure)
            else:failed.append(failure)
            if len(failed)<=8:print(json.dumps(failure,ensure_ascii=False),flush=True)
    variants=range(2 if quick else 4)
    for state in catalog['states']:
        for phase in state['substates']:
            for variant in variants:
                compare(phase['entry_cpu'],state['state'],phase['substate'],variant,'strict_services')
                compare(0xA028,state['state'],phase['substate'],variant,'external_CPU')
    # Every discovered local procedure is independently callable only as a
    # declared CPU fixture. It is not necessarily a natural gameplay entry.
    for procedure in catalog['procedures']:
        compare(procedure['entry'],0,0,0,'strict_services')
    # Original NMI3 wrapper, including its three genuine bank8 calls. No
    # opcode/service is skipped; unresolved asynchronous work stays a prefix.
    for state in catalog['states']:
        for variant in variants:compare(0xA000,state['state'],0,variant,'scene_wrapper')
    # Real public12A003 initialization, with controlled valid city/unit inputs.
    for city in (0,4,15,29):
        for units in range(3):
            prep={0x402:city}
            if units==1:prep.update({0x664+slot:255 for slot in range(20)})
            if units==2:
                for slot in range(20):
                    ident=slot+1;prep[0x664+slot]=ident;prep[0x63C0+12*ident+11]=((slot%8)<<4)|((slot%4)<<2)|(slot%4)
            compare(0xA003,0,0,units,'battle_initialization',prep)
    # Every bounded low3 duel-result branch, preserving aliases/slot removal.
    outcome_pairs=[(a,b)for a in range(8)for b in range(8)]if not quick else[(0,0),(2,0),(3,0),(4,0)]
    for first,second in outcome_pairs:
        compare(0xA006,11,0,0,'duel_outcome',{0x514:8,0x516:131,0x515:first,0x517:second})
    # IRQ layout accepts byte selectors; this validates software request fields
    # only, not real interrupt edges/scanline timing.
    for entry in (0xDF39,0xDF88):
        for value in range(8 if quick else 256):
            compare(entry,0,0,0,'IRQ_layout',{0x518:value,0x61:5 if value&1 else 7,0x8E:value},dict(a=73,x=91,y=117,p=32|(value&195)))
    # Actual newly readable fixed services: no original CPU on the source side.
    for entry,state,phase in ((0xA003,0,0),(0xA05E,0,0),(0xA2A7,2,0),(0xA470,4,0),(0xA8D8,5,2),(0xB964,6,0),(0xDB03,0,0),(0xE850,0,0)):
        compare(entry,state,phase,0,'pure_shared')
    # Exact arithmetic/RNG caller contracts against boundary and random data.
    rng=random.Random(0xB41111)
    for entry in (0xE850,0xE856,0xE862,0xEA7C,0xEAA5,0xEBE9,0xF2AF,0xF368):
        for sample in range(8 if quick else 128):
            prep={address:rng.randrange(256)for address in range(10)}
            divisor=(0,1,2,10,100,1000,32768,65535)[sample%8]
            prep[3]=divisor&255;prep[4]=divisor>>8;prep[0x50]=sample&255
            value=1+sample%255 if entry==0xE862 else sample%7 if entry==0xF368 else sample&255
            compare(entry,0,0,0,'fixed_helpers',prep,dict(a=value,x=rng.randrange(256),y=rng.randrange(256),p=32|(rng.randrange(256)&195)))
    # Source-domain/pending checks do not count as original CPU cases.
    for description,entry,state,phase,extra in (
      ('main16_rejected',0xA028,16,0,{}),('substate5_rejected_at_A054',0xA028,0,5,{}),
      ('unknown_entry_rejected',0x9FFF,0,0,{}),('decimal_mode_rejected',0xA028,0,0,{'p':40})):
        b=fresh(state,phase);model=BattleSceneController(b,rom)
        try:model.run_entry(entry,registers=BattleRegisters(**extra),seed_return=True);okay=False
        except ValueError:okay=True
        guards.append(dict(kind=description,passed=okay))
    b=fresh();model=BattleSceneController(b,rom);one=model.run_entry(0xA000,seed_return=True)
    before=(bytes(b.ram),bytes(b.sram),vars(model.registers).copy(),tuple(b.banks))
    two=model.resume();after=(bytes(b.ram),bytes(b.sram),vars(model.registers).copy(),tuple(b.banks))
    guards.append(dict(kind='missing_service_resume_keeps_real_stack',passed=one['status']==two['status']=='dependency'and before==after))
    model.services=lambda call:{'status':'returned'}
    model.resume();guards.append(dict(kind='false_return_cannot_pop_or_advance',passed=before==(bytes(b.ram),bytes(b.sram),vars(model.registers).copy(),tuple(b.banks))))
    for bad_status in('waiting','error','blocked',None):
        bus=fresh();source=BattleSceneController(bus,rom)
        source.run_entry(0xA003,seed_return=True);call=source.pending
        memory_before=(bytes(bus.ram),bytes(bus.sram),source._blocks)
        def invalid_return(current,bad_status=bad_status):
            current.registers.pc=current.return_pc;current.registers.sp=current.expected_sp
            return None if bad_status is None else{'status':bad_status}
        source.services=invalid_return;outcome=source.resume()
        guards.append(dict(kind='nonreturned_callback_rejected',input=bad_status,
            passed=outcome['status']=='dependency'and source.pending is call and memory_before==(bytes(bus.ram),bytes(bus.sram),source._blocks)))
    if not all(x['passed']for x in guards):failed.append(dict(source_guards=guards))
    out.mkdir(parents=True,exist_ok=True)
    receipt=dict(status='passed'if not failed else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),counts=dict(counts),failed_count=len(failed),failures=failed,
        unresolved_fixture_count=len(blocked),unresolved_fixtures=blocked,rows=rows,
        verification_only_original_CPU_callback_count=sum(callbacks.values()),
        source_guard_case_count=len(guards),source_guards=guards,
        external_callbacks=[dict(target=t,kind=k,count=n)for (t,k),n in sorted(callbacks.items())],
        source_original_CPU_calls=0,source_IR_interpretation=False,
        contract='All2KiBRAM/all8KiBSRAM,AXYPSPPC,banks,ordered ports and read observations; no video/cycles.',
        source_sha256=hashlib.sha256((ROOT/'source/recovered/battle_scene_controller.py').read_bytes()).hexdigest(),
        validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        shared_service_sha256=hashlib.sha256((ROOT/'source/recovered/scene_shared_services.py').read_bytes()).hexdigest())
    (out/'validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k in('status','rom_cpu_case_count','counts','failed_count','unresolved_fixture_count','verification_only_original_CPU_callback_count')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase11/battle');p.add_argument('--quick',action='store_true');a=p.parse_args()
    verify(a.rom.read_bytes(),a.out,a.quick)
