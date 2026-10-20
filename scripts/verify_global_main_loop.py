#!/usr/bin/env python3
"""Original6502 comparison of bounded global updates, dependencies and helpers."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.global_main_loop import GlobalMainLoop,GlobalDependency,Registers,main_target,nmi_target,InvalidGlobalIndex,reset_scene_working_state,finish_nmi_bookkeeping,ROM_SHA256
from source.recovered.mapped_memory import PrgDataMemory

def native_bus(rom,ram,sram,banks):
    b=Bus(rom,'alternating');b.ram[:]=ram;b.sram[:]=sram;b.banks[:]=banks;b.bank_initialized=[True]*4;b.protect=0x4c
    return b
def cpu_for(bus,registers):
    c=MPU(memory=bus);bus.cpu=c
    for k in ['a','x','y','sp','p','pc']:setattr(c,k,getattr(registers,k))
    return c
def regs(c):return {k:getattr(c,k)for k in ['a','x','y','sp','p','pc']}
def clone_regs(r):return Registers(**vars(r))
def actual_prefix(bus,r,entry,stop_pc,limit=200000):
    c=cpu_for(bus,clone_regs(r));c.pc=entry;visits=Counter()
    for count in range(limit):
        if count and c.pc==stop_pc:return c,visits
        if c.disassemble[bus.peek(c.pc)][0]=='???':raise RuntimeError(f'Unsupported original opcode{c.pc:04X}')
        bank,off=bus.origin(c.pc);visits[(bank,c.pc)]+=1;bus.pc=c.pc;bus.step_no=count;c.step()
    raise RuntimeError(f'Original prefix did not reach{stop_pc:04X};pc{c.pc:04X}')

class ActualOutside:
    """Verification only. Every helper executes real bytes; none is acked."""
    def __init__(self,bus,limit=20000):self.bus=bus;self.limit=limit;self.calls=[]
    def execute(self,c,target,return_pc,kind):
        self.bus.cpu=c;before_banks=list(self.bus.banks);c.pc=target
        for count in range(self.limit):
            if count and (c.pc==return_pc if return_pc is not None else c.pc in self.global_pcs):
                self.calls.append({'target':target,'kind':kind,'entry_banks':before_banks,'instructions':count,'outcome':'returned'});return None
            if c.pc==0xfb28 and self.bus[0x62]!=0:
                detail={'category':'outside_helper_irq_wait','target':target,'pc':c.pc,'flag':self.bus[0x62]};break
            if c.disassemble[self.bus.peek(c.pc)][0]=='???':
                detail={'category':'outside_helper_unrecognized_opcode','target':target,'pc':c.pc,'opcode':self.bus.peek(c.pc)};break
            self.bus.pc=c.pc;self.bus.step_no=count;c.step()
        else:detail={'category':'outside_helper_budget','target':target,'pc':c.pc,'budget':self.limit}
        self.calls.append({'target':target,'kind':kind,'entry_banks':before_banks,'instructions':count,'outcome':'dependency','detail':detail});return detail
    def __call__(self,context,target,return_pc,kind):
        c=cpu_for(self.bus,context.registers);self.global_pcs=context.instructions
        detail=self.execute(c,target,return_pc,kind)
        for key,value in regs(c).items():setattr(context.registers,key,value)
        if detail is not None:raise GlobalDependency(detail)

def actual_assisted(bus,r,entry,stop_pcs,program,limit=50000):
    """Original outer code, authentic bounded outside helpers, same cutset."""
    c=cpu_for(bus,clone_regs(r));c.pc=entry;outside=ActualOutside(bus);outside.global_pcs=program;visits=Counter()
    for count in range(limit):
        if count and c.pc in stop_pcs:return c,visits,'boundary',outside.calls
        if c.pc==0xfb28 and bus[0x62]!=0:return c,visits,'dependency',outside.calls
        item=program.get(c.pc)
        if item and item['op']in ['JSR','JMP']and'hook'in item:
            bank,off=bus.origin(c.pc);visits[(bank,c.pc)]+=1;bus.pc=c.pc;c.step()
            detail=outside.execute(c,item['operand'],item['next_pc']if item['op']=='JSR'else None,'call'if item['op']=='JSR'else'tail')
            if detail is not None:return c,visits,'dependency',outside.calls
            continue
        if c.disassemble[bus.peek(c.pc)][0]=='???':raise RuntimeError(f'Unsupported outer opcode{c.pc:04X}')
        bank,off=bus.origin(c.pc);visits[(bank,c.pc)]+=1;bus.pc=c.pc;bus.step_no=count;c.step()
    return c,visits,'budget',outside.calls

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase6/global');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
    snapshot_prefixes={'battle':prefix,'attack':ROOT/'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu',
                       'duel':ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-state-16',
                       'city':ROOT/'analysis/phase5/runtime/city-info/menu-1',
                       'title':ROOT/'analysis/runtime/title','ruler-select':ROOT/'analysis/runtime/ruler-confirm'}
    snapshots={key:(Path(str(value)+'-ram.bin').read_bytes(),Path(str(value)+'-sram.bin').read_bytes())for key,value in snapshot_prefixes.items()}
    program=json.loads((a.out/'program.json').read_text());instructions={v['pc']:v for v in program['instructions']}
    counts=Counter();failures=[];coverage=set();native_locations=set();statuses=Counter();fixtures=[];rng=random.Random(0x6007)
    def check(group,condition,details):
        counts[group]+=1
        if not condition:failures.append({'group':group,'details':details})
    def initial(changes=(),snapshot='battle'):
        ram=bytearray(snapshots[snapshot][0])
        for addr,value in {0xe1:0x31,0xe2:0x2c,0xe3:0x2d,0xde:0x31,0xdf:0x28,0xe0:0x29,0x62:0,**dict(changes)}.items():ram[addr]=value
        return ram
    def equal(source,native,r,c,extra=False):
        good=source.ram==native.ram and source.sram==native.sram and source.banks==native.banks and vars(r)==regs(c)
        if extra:good &= source.sound==native.sound and source.ppu==native.ppu and source.vram==native.vram and source.protect==native.protect
        return good
    def paired_prefix(group,entry,ram,call,registers,banks=(17,12,13,31),mapped=False):
        ref=native_bus(rom,ram,base_sram,banks)
        source=PrgDataMemory(rom,ram,base_sram,banks=banks)if mapped else native_bus(rom,ram,base_sram,banks)
        machine=GlobalMainLoop(source);effect=call(machine,clone_regs(registers));r=machine.registers
        c,visited=actual_prefix(ref,registers,entry,r.pc);coverage.update(machine.executed);native_locations.update(visited)
        good=equal(source,ref,r,c,not mapped);statuses[f'{group}:{effect["status"]}']+=1
        details={'entry':entry,'main':ram[0x7a],'scene':ram[0x78],'status':effect['status'],'pc':r.pc,'registers_model':vars(r),'registers_rom':regs(c)}
        check(group,good,details)
        if group.startswith('strict_'):fixtures.append({**details,'dependency':effect.get('dependency'),'events':effect['events']})
    # All masked aliases that land within the proven pointer table domains.
    for value in range(256):
        ram=initial([(0x7a,value)]);r=Registers(a=0x82,x=0x91,y=0x20,sp=0xd2,p=0xe7,pc=0xe066)
        if value&31<15:
            target=main_target(ram);paired_prefix('all120_main_masked_dispatch_aliases',0xe066,ram,lambda m,rr:m.run_window(0xe066,stop_pcs=(target,),registers=rr),r)
        else:
            try:main_target(ram);rejected=False
            except InvalidGlobalIndex:rejected=True
            check('unproven_main_indices_rejected',rejected,{'value':value})
        ram=initial([(0x78,value)]);r=Registers(a=0x75,x=0xe1,y=0,sp=0xd2,p=0xa1,pc=0xf862)
        if value&15<9:
            target=nmi_target(ram);paired_prefix('all144_nmi_masked_dispatch_aliases',0xf862,ram,lambda m,rr:m.run_window(0xf862,stop_pcs=(target,),registers=rr),r)
        else:
            try:nmi_target(ram);rejected=False
            except InvalidGlobalIndex:rejected=True
            check('unproven_nmi_indices_rejected',rejected,{'value':value})
    # Strict production data bus: absence of hardware/helpers must be reported.
    for state in range(15):
        for i in range(4):
            ram=initial([(0x7a,state),(0x8b,[0,0x10,0x80,0xff][i]),(0x50,[0,1,254,255][i])]);r=Registers(a=33*i,x=85*i,y=17*i,sp=0xfd,p=[0x20,0x21,0x66,0xe7][i])
            paired_prefix('strict_all15_main_entries',0xe066,ram,lambda m,rr:m.step(registers=rr),r,mapped=True)
    for scene in range(9):
        for busy in [0,1]:
            ram=initial([(0x78,scene),(0x7b,busy)]);r=Registers(a=0x71,x=0xfe,y=0x55,sp=0xfa,p=0xa5)
            paired_prefix('strict_all9_nmi_windows',0xf862,ram,lambda m,rr:m.nmi_step(registers=rr),r,mapped=True)
            paired_prefix('strict_all9_nmi_prefixes',0xf800,ram,lambda m,rr:m.nmi_prefix(registers=rr),r,mapped=True)
    ram=initial();r=Registers(a=128,x=49,y=16,sp=0xff,p=0x24)
    paired_prefix('strict_post_reset_entry',0xe05e,ram,lambda m,rr:m.cold_post_reset(registers=rr),r,mapped=True)
    # This verifier's synchronous bus supplies explicit PPU status samples and
    # records IO. It tests the normal/busy NMI prefix's real cache/DMA requests,
    # while absence of display/IRQ/audio source still produces a dependency.
    for scene in range(9):
        for busy in [0,1]:
            ram=initial([(0x78,scene),(0x7b,busy)]);r=Registers(a=0x71,x=0xfe,y=0x55,sp=0xfa,p=0xa5)
            paired_prefix('nmi_prefix_synchronous_io_contract',0xf800,ram,lambda m,rr:m.nmi_prefix(registers=rr),r)
    # Authentic outside helpers are used only by this verifier to exercise the
    # rest of the local control graph. They never fake a renderer return/IRQ.
    for domain,indices in [('main',range(15)),('nmi',range(9))]:
        for index in indices:
            variants=[0,1,2,3]if index==13 and domain=='main'or index==8 and domain=='nmi'else[0,1]
            for variant in variants:
                snapshot='attack'if domain=='nmi'and index==4 or domain=='main'and index in[5,6]else'duel'if domain=='nmi'and index==5 or domain=='main'and index in[7,8]else'city'if domain=='nmi'and index in[2,6,7,8]or domain=='main'and index in[1,2,9,11,13]else'battle'
                if domain=='nmi'and index==6 or domain=='main'and index==9:snapshot='title'
                if domain=='nmi'and index==7 or domain=='main'and index==11:snapshot='ruler-select'
                changes=[(0x7a,index)]if domain=='main'else[(0x78,index)]
                changes += [(0x541,variant if index in[13,8]else snapshots[snapshot][0][0x541]),(0x50,(variant*127)&255),(0x7d,0),(0x7e,0),(0x62,0),(0x300,255),(0x304,255)]
                if domain=='main'and index==3:changes += [(0x500,11 if variant else 0),(0x501,0)]
                if domain=='nmi'and index==8:changes += [(0x540,0)]
                ram=initial(changes,snapshot);sram=snapshots[snapshot][1];registers=Registers(a=0x43,x=(0x80*variant)&255,y=0x11,sp=0xfd,p=0x20|(variant&1))
                source=native_bus(rom,ram,sram,[17,12,13,31]);ref=native_bus(rom,ram,sram,[17,12,13,31])
                helper=ActualOutside(source);machine=GlobalMainLoop(source,hooks=helper)
                if domain=='main':entry=0xe066;effect=machine.step(registers=clone_regs(registers));stops=(0xe066,)
                else:entry=0xf862;effect=machine.nmi_step(registers=clone_regs(registers));stops=(0xf88d,)
                c,visited,outcome,refcalls=actual_assisted(ref,registers,entry,stops,instructions)
                coverage.update(machine.executed);native_locations.update(visited);statuses[f'oracle_assisted_{domain}:{effect["status"]}']+=1
                good=equal(source,ref,machine.registers,c,True)and effect['status']==outcome
                details={'domain':domain,'index':index,'variant':variant,'snapshot':snapshot,'status':effect['status'],'rom_status':outcome,'registers_model':vars(machine.registers),'registers_rom':regs(c),
                         'source_outside_helpers':helper.calls,'reference_outside_helpers':refcalls,'dependency':effect.get('dependency')}
                check('oracle_assisted_global_updates',good,details);fixtures.append(details)
    # Exact raw-byte mapper protocols, including flags, stack and all shadows.
    for entry in [0xf237,0xf24b,0xf25f,0xf266]:
        for selector in range(256):
            for variant in range(4):
                ram=initial();sp=[0xfd,0xa3,0x23,0][variant];ram[0x100+((sp+1)&255)]=255;ram[0x100+((sp+2)&255)]=1
                r=Registers(a=(selector*17+variant)&255,x=[0,127,128,255][variant],y=selector,sp=sp,p=[0x20,0x21,0x66,0xe7][variant])
                paired_prefix('four_mapper_helpers_all_raw_selectors',entry,ram,lambda m,rr:m.run_window(entry,return_pc=0x200,registers=rr),r,mapped=True)
    # Readable high-level helpers compare their declared complete RAM/SRAM and
    # mapper effects; no CPU register or interrupt-return contract is inferred.
    for case in range(512):
        ram=bytearray(rng.randrange(256)for _ in range(2048));ram[0x1fe:0x200]=bytes([255,1]);r=Registers(sp=0xfd,p=0x20)
        ref=native_bus(rom,ram,base_sram,[17,12,13,31]);source=PrgDataMemory(rom,ram,base_sram,banks=[17,12,13,31])
        c,visited=actual_prefix(ref,r,0xe4e9,0x200);native_locations.update(visited);reset_scene_working_state(source)
        check('readable_scene_working_state_reset',source.ram==ref.ram and source.sram==ref.sram and source.banks==ref.banks,{'case':case})
    for case in range(1024):
        ram=initial([(0x7b,case&255),(0x50,case&255),(0x52,(case*3)&255),(0x54,(case*7)&255),(0x55,(case*17)&255),
                     (0x5e,[0,1,254,255][case&3]),(0x5f,(case*5)&255),(0xde,case&255),(0xdf,(case*19)&255),(0xe0,(case*23)&255)])
        r=Registers(a=0x71,x=0x91,y=0x53,sp=0xfa,p=0xa5)
        ref=native_bus(rom,ram,base_sram,[17,12,13,31]);source=PrgDataMemory(rom,ram,base_sram,banks=[17,12,13,31])
        c,visited=actual_prefix(ref,r,0xf88d,0xf8af);native_locations.update(visited);finish_nmi_bookkeeping(source)
        check('readable_normal_nmi_bookkeeping',source.ram==ref.ram and source.sram==ref.sram and source.banks==ref.banks,{'case':case})
    # Direct epilogue is a six-byte caller-owned interrupt/save-register frame.
    # No complete NMI or hardware frame is inferred from this pop/RTI test.
    for sp in range(256):
        ram=initial();saved=[sp,(sp*7)&255,(sp*17)&255,(sp*29)&247,0,2]
        for j,value in enumerate(saved):ram[0x100+((sp+j+1)&255)]=value
        r=Registers(a=0x43,x=0x82,y=0x11,sp=sp,p=0x20)
        paired_prefix('nmi_saved_registers_and_rti_stack',0xf8af,ram,lambda m,rr:m.run_window(0xf8af,return_pc=0x200,registers=rr),r,mapped=True)
    # Static source provenance is separate from dynamic execution coverage.
    static_matches=0
    for item in program['instructions']:
        raw=bytes.fromhex(item['raw_hex']);assert item['bank']==31 and item['file']==0x3e010+item['pc']-0xe000
        assert rom[item['file']:item['file']+len(raw)]==raw;static_matches+=1
    guard_count=counts['unproven_main_indices_rejected']+counts['unproven_nmi_indices_rejected']
    report={'rom_sha256':ROM_SHA256,'status':'passed'if not failures else'failed','case_count':sum(counts.values()),'failed_count':len(failures),
            'source_sha256':hashlib.sha256((ROOT/'source/recovered/global_main_loop.py').read_bytes()).hexdigest(),
            'validator_sha256':hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
            'program_sha256':hashlib.sha256((a.out/'program.json').read_bytes()).hexdigest(),
            'catalog_sha256':hashlib.sha256((a.out/'state-catalog.json').read_bytes()).hexdigest(),
            'dependency_source_sha256':{name:hashlib.sha256((ROOT/'source/recovered'/name).read_bytes()).hexdigest()for name in ['battle_state_machine.py','controller_helpers.py','runtime_services.py','mapped_memory.py']},
            'fixture_source_sha256':{key:{suffix:hashlib.sha256(Path(str(value)+suffix).read_bytes()).hexdigest()for suffix in ['-ram.bin','-sram.bin']}for key,value in snapshot_prefixes.items()},
            'rom_cpu_case_count':sum(counts.values())-guard_count,'source_guard_case_count':guard_count,
            'readable_semantic_case_count':counts['readable_scene_working_state_reset']+counts['readable_normal_nmi_bookkeeping'],
            'counts':dict(counts),'status_counts':dict(statuses),'instruction_ir_total':len(instructions),'instruction_ir_coverage':len(coverage),
            'static_instruction_matches':static_matches,'native_instruction_locations_including_semantic_oracles':len(native_locations),
            'source_instruction_locations_executed':sorted(coverage),'main_entry_indices_verified':list(range(15)),'nmi_scene_indices_verified':list(range(9)),
            'failures':failures,'fixtures':fixtures,'fixture_source':str(prefix.relative_to(ROOT)),
            'typed_fixture_sources':{key:str(value.relative_to(ROOT))for key,value in snapshot_prefixes.items()},
            'contract':'CPU registers A/X/Y/P/SP/PC, full2KiB RAM+8KiB SRAM and PRG banks; verificationBus additionally compares sound/APU-request/PPU/VRAM/protection state. Strict source stops before unsupported accesses. No full NES frame is simulated.',
            'outside_helper_policy':'Verification-only actual6502 code, bounded20000 instructions per outside helper; waits/unknown opcodes/budgets are explicit dependencies, never fake RTS or job completion.',
            'limitations':['Masked invalid indices are fail-closed source guards, not unsafe original control execution.','Static1005/1005 byte provenance and dynamic IR coverage are different measurements.','Oracle-assisted completion is conditional on authentic outside-code execution, not standalone recovered audio/renderer semantics.','Source PrgDataMemory retains its strict hardware/protection limits; no PPU/NMI/IRQ timing is invented.','Readable helpers verify memory/mapper contracts, not complete CPU flags or RTI.']}
    (a.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','case_count','failed_count','instruction_ir_total','instruction_ir_coverage','status_counts']},ensure_ascii=False))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
