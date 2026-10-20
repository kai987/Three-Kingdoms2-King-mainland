#!/usr/bin/env python3
"""Differential control-IR checks, using original ROM only for external hooks.

This verifies recovered local execution, not independent helper implementations.
The NMI-dependent ECEE render barrier is a declared no-op in both sides. No ROM
bytes are patched. Every legal main/sub entry has a separately reported result.
"""
from pathlib import Path
import argparse
import json, hashlib, sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered.battle_state_machine import BattleStateMachine, Registers, ROM_SHA256

BARRIER=0xECEE

def make_bus(rom,ram,sram,pair=12):
    bus=Bus(rom,'alternating');bus.ram[:]=ram;bus.sram[:]=sram
    bus.banks=[17,pair,pair+1,31];bus.bank_initialized=[True]*4;bus.protect=0x4C
    bus.ram[0xE1:0xE4]=bytes([0x31,pair|0x20,(pair+1)|0x20])
    return bus

def rts(cpu,bus):
    cpu.sp=(cpu.sp+1)&255;lo=bus[0x100+cpu.sp]
    cpu.sp=(cpu.sp+1)&255;hi=bus[0x100+cpu.sp]
    cpu.pc=((lo|hi<<8)+1)&65535

def native(bus,entry,limit=200000,extra_return=False,cpu_regs=None):
    cpu=MPU(memory=bus);bus.cpu=cpu;cpu.pc=entry;cpu.sp=0xFD;cpu.p=32
    for key,value in (cpu_regs or {}).items():setattr(cpu,key,value)
    bus.ram[0x1FE:0x200]=bytes([0xFF,1]);visited=Counter();barriers=0
    if extra_return:cpu.sp=0xFB;bus.ram[0x1FC:0x1FE]=bytes([0xFF,1])
    for n in range(limit):
        if cpu.pc==0x200:return cpu,visited,barriers
        if cpu.pc==BARRIER:rts(cpu,bus);barriers+=1;continue
        bank,offset=bus.origin(cpu.pc) or (-1,cpu.pc)
        visited[(bank,cpu.pc)]+=1
        if bank<0:raise RuntimeError(f'RAM PC {cpu.pc:04X}')
        bus.pc=cpu.pc;bus.step_no=n;cpu.step()
    raise RuntimeError(f'native budget PC {cpu.pc:04X}')

class ExternalOracle:
    def __init__(self):self.calls=Counter();self.steps=Counter();self.barriers=0
    def __call__(self,context,target,return_pc,kind):
        bus=context.memory;r=context.registers
        cpu=MPU(memory=bus);bus.cpu=cpu
        for key in ('a','x','y','sp','p','pc'):setattr(cpu,key,getattr(r,key))
        cpu.pc=target
        self.calls[(target,kind)]+=1
        for n in range(200000):
            if n and ((return_pc is not None and cpu.pc==return_pc) or (return_pc is None and (cpu.pc==0x200 or cpu.pc in context.instructions))):break
            if cpu.pc==BARRIER:rts(cpu,bus);self.barriers+=1;continue
            if bus.origin(cpu.pc) is None:raise RuntimeError(f'hook RAM PC {cpu.pc:04X} target {target:04X}')
            bus.pc=cpu.pc;bus.step_no=n;cpu.step()
        else:raise RuntimeError(f'hook budget PC {cpu.pc:04X} target {target:04X}')
        self.steps[target]+=n
        for key in ('a','x','y','sp','p','pc'):setattr(r,key,getattr(cpu,key))


def verify(rom):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
    ram=(prefix.with_name(prefix.name+'-ram.bin')).read_bytes()
    sram=(prefix.with_name(prefix.name+'-sram.bin')).read_bytes()
    catalog=json.loads((ROOT/'analysis/battle_fsm/state-catalog.json').read_text())
    rows=[];coverage=set();helpercalls=Counter();passed=0;failures=[];blocked=[]
    for state in catalog['states']:
        for sub in state['substates']:
            for variant in range(8):
                case=(state['state'],sub['substate'],variant)
                a=make_bus(rom,ram,sram);b=make_bus(rom,ram,sram)
                for bus in (a,b):
                    bus[0x500]=case[0];bus[0x501]=case[1];bus[0x502]=0
                    bus[0x81]=(0,1,2,3)[variant%4]
                    bus[0x87]=(0,0x80,0x80,0)[variant%4]
                    if variant>=4:
                        bus[0x509]=0;bus[0x600]=3;bus[0x614]=16;bus[0x504]=0x80
                        bus[0x6F3F]=48;bus[0x6F40]=0;bus[0x6F41]=0;bus[0x6F42]=1
                    bus[0x7E]=0;bus[0xDF]=0
                    bus[0x6F92]=0;bus[0x6F93]=0
                entry=sub['entry_cpu'];external=ExternalOracle();model=BattleStateMachine(b,external)
                try:
                    cpu,visited,barriers=native(a,entry)
                    result=model.run_entry(entry,max_instructions=200000)
                    diffs=[(i,x,y) for i,(x,y) in enumerate(zip(a.ram,b.ram)) if x!=y]
                    sdiffs=[(i+0x6000,x,y) for i,(x,y) in enumerate(zip(a.sram,b.sram)) if x!=y]
                    regs={k:(getattr(cpu,k),getattr(model.registers,k)) for k in ('a','x','y','sp','p','pc') if getattr(cpu,k)!=getattr(model.registers,k)}
                    if diffs or sdiffs or regs:
                        failures.append({'case':case,'entry':entry,'ram':diffs[:20],'sram':sdiffs[:20],'regs':regs})
                        status='mismatch'
                    else:passed+=1;status='passed'
                    coverage.update(model.executed);helpercalls.update(external.calls)
                    rows.append({'state':case[0],'substate':case[1],'variant':variant,'entry':entry,'status':status,'instructions':len(model.executed),'external_calls':sum(external.calls.values()),'barriers':barriers,'after':[b[0x500],b[0x501],b[0x50A]],'global_after':b[0x7A]})
                except Exception as e:
                    blocked.append({'case':case,'entry':entry,'error':str(e),'source_pc':model.registers.pc})
                    rows.append({'state':case[0],'substate':case[1],'variant':variant,'entry':entry,'status':'blocked','error':str(e)})
                    coverage.update(model.executed);helpercalls.update(external.calls)
    program=json.loads((ROOT/'analysis/battle_fsm/program.json').read_text())
    declared={(i['operand'],i['op']) for i in program['instructions'] if 'hook' in i or i['op']=='FARCALL'}
    shared={0xEADE,0xF2D7,0xE87A,0xE88A,0xE89A,0xE8AA}
    return {'rom_sha256':ROM_SHA256,'scope':'all 101 legal main/sub combinations (98 local plus bank8 aliases); original-ROM external helper oracle; ECEE NMI render barrier explicitly bypassed on both sides','total_cases':len(rows),'passed':passed,'mismatches':failures,'blocked':blocked,'rows':rows,'legal_entries':len({(r['state'],r['substate']) for r in rows}),'legal_entries_passed':len({(r['state'],r['substate']) for r in rows if r['status']=='passed'}),'ir_instruction_count':len(program['instructions']),'executed_ir_instruction_count':len(coverage),'executed_pcs':sorted(coverage),'declared_external_helper_targets':len({t for t,op in declared}),'unrecovered_external_helper_targets':len({t for t,op in declared if t not in shared}),'helper_calls':[{'target':t,'kind':kind,'count':n} for (t,kind),n in sorted(helpercalls.items())]}

def verify_ticks(rom):
    rows=[];failures=[];coverage=set()
    for snapshot in (0,2,3,4,5,6,7):
        prefix=ROOT/f'analysis/runtime/phase3/attack-intro-{snapshot}'
        ram=prefix.with_name(prefix.name+'-ram.bin').read_bytes()
        sram=prefix.with_name(prefix.name+'-sram.bin').read_bytes()
        for variant in range(8):
            a=make_bus(rom,ram,sram);b=make_bus(rom,ram,sram)
            for bus in (a,b):
                bus[0x81]=variant&3;bus[0x87]=128 if variant&1 else 0
                if variant>=4:bus[0x664]=255;bus[0x52B]=10
            before=[b[0x500],b[0x501],b[0x50A]]
            external=ExternalOracle();model=BattleStateMachine(b,external)
            cpu,visited,barriers=native(a,0xA028)
            model.step(max_instructions=200000);coverage.update(model.executed)
            diffs=[(i,x,y) for i,(x,y) in enumerate(zip(a.ram,b.ram)) if x!=y]
            sdiffs=[(i+0x6000,x,y) for i,(x,y) in enumerate(zip(a.sram,b.sram)) if x!=y]
            regs={k:(getattr(cpu,k),getattr(model.registers,k)) for k in ('a','x','y','sp','p','pc') if getattr(cpu,k)!=getattr(model.registers,k)}
            status='passed' if not(diffs or sdiffs or regs) else 'mismatch'
            if status!='passed':failures.append({'snapshot':snapshot,'variant':variant,'ram':diffs[:20],'sram':sdiffs[:20],'regs':regs})
            rows.append({'snapshot':snapshot,'variant':variant,'before':before,'after':[b[0x500],b[0x501],b[0x50A]],'global_after':b[0x7A],'status':status})
    return {'passed':sum(r['status']=='passed' for r in rows),'rows':rows,'mismatches':failures,'executed_pcs':sorted(coverage),'scope':'original unmodified gameplay snapshots plus labeled synthetic button/commander-removal boundary variants'}

def verify_fixed_helpers(rom):
    import random
    seeded=random.Random(650231);counts=Counter();failures=[];coverage=set()
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
    ram=prefix.with_name(prefix.name+'-ram.bin').read_bytes()
    sram=prefix.with_name(prefix.name+'-sram.bin').read_bytes()
    entries=(0xE850,0xE856,0xE862,0xEA7C,0xEAA5,0xEBE9,0xF2AF,0xF368)
    for entry in entries:
        for i in range(512):
            a=make_bus(rom,ram,sram)
            for address in range(10):a[address]=seeded.randrange(256)
            a[0x50]=i&255
            if entry in (0xEA7C,0xEAA5):
                divisor=(0,1,2,10,100,1000,32768,65535)[i%8]
                a[3]=divisor&255;a[4]=divisor>>8
            regs={'a':(1+i%255) if entry==0xE862 else i&255,
                  'x':seeded.randrange(256),'y':seeded.randrange(256),
                  'p':32|(seeded.randrange(256)&(1|2|4|64|128))}
            b=make_bus(rom,a.ram,a.sram);model=BattleStateMachine(b)
            cpu,visited,barriers=native(a,entry,cpu_regs=regs)
            model.run_entry(entry,registers=Registers(**regs),max_instructions=200000)
            diffs=[(j,x,y) for j,(x,y) in enumerate(zip(a.ram,b.ram)) if x!=y]
            sdiffs=[(j+0x6000,x,y) for j,(x,y) in enumerate(zip(a.sram,b.sram)) if x!=y]
            rdiffs={k:(getattr(cpu,k),getattr(model.registers,k)) for k in ('a','x','y','sp','p','pc') if getattr(cpu,k)!=getattr(model.registers,k)}
            if diffs or sdiffs or rdiffs:failures.append({'entry':entry,'case':i,'ram':diffs[:12],'sram':sdiffs[:12],'registers':rdiffs})
            else:counts[f'{entry:04X}']+=1
            coverage.update(model.executed)
    return {'passed':sum(counts.values()),'counts':dict(counts),'mismatches':failures,'executed_pcs':sorted(coverage),
       'scope':'Eight newly lifted fixed helpers; no original-ROM oracle hook in source model. Full registers/flags/SP/RAM/SRAM. D=0 (py65 is generic6502); E862 bound1..255 because bound0 cannot terminate.'}

def verify_semantic(rom):
    import random
    from source.recovered.battle_state_machine import (commander_outcome,
        finalize_city_ownership,postbattle_city_losses,return_campaign_supplies,
        finalization_phase,refresh_movement_selectors,restore_side_action_budgets,finish_side_turn)
    rng=random.Random(650213);counts=Counter();failures=[]
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
    ram=(prefix.with_name(prefix.name+'-ram.bin')).read_bytes()
    sram=(prefix.with_name(prefix.name+'-sram.bin')).read_bytes()
    adjacency=rom[16+16*8192+0x1D72:16+16*8192+0x1D72+256]
    table=rom[0x3E8CA:0x3E9CA]
    def copied(bus):return make_bus(rom,bus.ram,bus.sram,pair=8)
    def sram_same(name,a,b,i):
        diffs=[(j+0x6000,x,y) for j,(x,y) in enumerate(zip(a.sram,b.sram)) if x!=y]
        if diffs:failures.append({'function':name,'case':i,'diffs':diffs[:12]})
        else:counts[name]+=1
    values=[0,1,500,501,502,9999,10000,32767,65535]
    for i in range(512):
        a=make_bus(rom,ram,sram,pair=8);city=i%30;a[0x50E]=city;a[0x514]=i%2
        a[0x506]=[0,5,6,10,11,15,16,20,21,255][i%10];a[0x50]=i&255
        addr=0x6000+city*32
        for offset in (2,4,6,8,14):
            v=values[(i+offset)%len(values)] if i<90 else rng.randrange(65536)
            a[addr+offset]=v&255;a[addr+offset+1]=v>>8
        a[addr+11]=i&255;b=copied(a)
        postbattle_city_losses(b,table[a[0x50]])
        native(a,0xBF0A);sram_same('postbattle_city_losses',a,b,i)
        a=make_bus(rom,ram,sram,pair=8);a[0x50E]=city;a[0x514]=i%2
        a[0x52B]=255 if i%5==0 else i%237;a[0x52C]=(city+1)%30
        if a[0x52B]!=255:a[0x63C0+12*a[0x52B]+11]=i%4
        for at in (0x522,0x524,0x526,0x528):
            v=values[(i+at)%len(values)] if i<90 else rng.randrange(65536)
            a[at]=v&255;a[at+1]=v>>8
        for c in (city,(city+1)%30):
            for o in (2,4):
                v=values[(i+c+o)%len(values)];a[0x6000+32*c+o]=v&255;a[0x6000+32*c+o+1]=v>>8
        b=copied(a);return_campaign_supplies(b);native(a,0xC027);sram_same('return_campaign_supplies',a,b,i)
        a=make_bus(rom,ram,sram,pair=8);a[0x50E]=city;a[0x514]=i%2;a[0x507]=0x21
        for c in range(30):
            owner=c%8;a[0x6000+32*c]=owner
            if owner!=7:a[0x6000+32*c+17+(i+c)%10]=a[0x6F07+owner*8]
        b=copied(a);finalize_city_ownership(b,adjacency);native(a,0xBBB8);sram_same('finalize_city_ownership',a,b,i)
    keys=[0x500,0x501,0x509,0x50A,0x514,0xA4,0x6F44,0x42C]
    for i in range(512):
        a=make_bus(rom,ram,sram);a[0x507]=0x21
        a[0x66E]=255 if i%2 else 20;a[0x664]=255 if i%3==0 else 30
        for slot in range(20):a[0x628+slot]=255
        a[0x628]=[0,128,255][i%3];a[0x632]=[128,0,255][i%3]
        if i%4:a[0x628+(i%20)]=0 if i%2 else 128
        a[0x52B]=255 if i%2 else 10
        a[0x6F0A]=i%4;a[0x6F12]=(i+1)%4;a[0x6F1A]=(i+2)%4
        b=make_bus(rom,a.ram,a.sram);commander_outcome(b)
        native(a,0xDD72,extra_return=True)
        diffs=[(key,a[key],b[key]) for key in keys if a[key]!=b[key]]
        if diffs:failures.append({'function':'commander_outcome','case':i,'diffs':diffs})
        else:counts['commander_outcome']+=1
    # Source has strict semantic dependencies for AI captive processing and
    # rendering; test all recovered human routes and final city return itself.
    for stage in (0,1,2,3):
        for i in range(64):
            a=make_bus(rom,ram,sram,pair=8);a[0x501]=stage;a[0x514]=i%2
            a[0x507]=0x21;a[0x6F12]=i%3;a[0x6F1A]=(i+1)%3
            a[0x87]=0x80 if i%2 else 0
            b=copied(a)
            def draw():
                value=table[b[0x50]];b[0x50]=(b[0x50]+1)&255;return value
            finalization_phase(b,adjacency,rng_draw=draw,render_barrier=lambda memory:None)
            native(a,[0xBAC1,0xBB3D,0xBB93,0xBBA0][stage])
            keys=[0x500,0x501,0x504,0x50B,0x6F44,0x7A,0x400,0x401]+list(range(0xB2,0xDC))
            diffs=[(key,a[key],b[key]) for key in keys if a[key]!=b[key]]
            sdiffs=[(j+0x6000,x,y) for j,(x,y) in enumerate(zip(a.sram,b.sram)) if x!=y]
            if diffs or sdiffs:failures.append({'function':'finalization_phase','stage':stage,'case':i,'diffs':diffs[:12],'sram':sdiffs[:12]})
            else:counts['finalization_phase']+=1
    for i in range(512):
        a=make_bus(rom,ram,sram);a[0x50C]=i&255;a[0x50D]=(255-i)&255
        for slot in range(20):
            officer=slot if (slot+i)%7 else 255;a[0x664+slot]=officer
            a[0x628+slot]=0 if slot<10 else 128
            if officer!=255:
                troops=rng.randrange(1024);address=0x63C0+12*officer
                a[address+8]=troops&255;a[address+9]=(troops>>8)|(i&252)
        b=make_bus(rom,a.ram,a.sram);restore_side_action_budgets(b);native(a,0xC5A0)
        keys=list(range(0x63C,0x650))+[0x50C,0x50D]
        diffs=[(key,a[key],b[key]) for key in keys if a[key]!=b[key]]
        if diffs:failures.append({'function':'restore_side_action_budgets','case':i,'diffs':diffs})
        else:counts['restore_side_action_budgets']+=1
        # Entire low-side turn is independent gameplay source for human rulers.
        a=make_bus(rom,ram,sram);a[0x504]=128;a[0x50F]=0;a[0x6F12]=i%3
        a[0x505]=i&255;a[0x50C]=(255-i)&255;b=make_bus(rom,a.ram,a.sram)
        finish_side_turn(b);native(a,0xBDC0)
        keys=[0x504,0x505,0x506,0x50C,0x50D,0x50F,0x6F44,0x470,0x471,0x500,0x501,0x509,0x52C,0x52E,0x6F94,0x6F95,0x6F96]
        diffs=[(key,a[key],b[key]) for key in keys if a[key]!=b[key]]
        if diffs:failures.append({'function':'finish_side_turn','case':i,'diffs':diffs})
        else:counts['finish_side_turn']+=1
    return {'counts':dict(counts),'passed':sum(counts.values()),'mismatches':failures,
            'comparison':'gameplay state fields and SRAM; semantic functions do not promise CPU scratch/flags/stack or queue encodings'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom',type=Path,nargs='?',default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    parser.add_argument('--out',type=Path,default=ROOT/'analysis/battle_fsm')
    args=parser.parse_args();rom=args.rom.read_bytes();args.out.mkdir(parents=True,exist_ok=True)
    result=verify(rom);result['ticks']=verify_ticks(rom);result['semantic']=verify_semantic(rom);result['fixed_helpers']=verify_fixed_helpers(rom)
    out=args.out/'oracle-verification.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    coverage=set(result['executed_pcs'])|set(result['ticks']['executed_pcs'])|set(result['fixed_helpers']['executed_pcs'])
    failed=len(result['mismatches'])+len(result['blocked'])+len(result['ticks']['mismatches'])+len(result['semantic']['mismatches'])+len(result['fixed_helpers']['mismatches'])
    program=json.loads((ROOT/'analysis/battle_fsm/program.json').read_text())
    previous={i['next_pc']:i for i in program['instructions']}
    far=set()
    for i in program['instructions']:
        if i['op']=='FARCALL':
            prev=previous.get(i['pc'])
            far.add((prev['operand'] if prev and prev['op']=='LDY' and prev['mode']=='imm' else None,i['inline_target']))
    summary={'status':'passed' if failed==0 else 'failed','rom_sha256':ROM_SHA256,
       'case_count':result['total_cases'],'failed_count':failed,
       'legal_entry_count':result['legal_entries'],'legal_entry_passed':result['legal_entries_passed'],
       'instruction_ir_coverage':len(coverage),'instruction_ir_total':result['ir_instruction_count'],
       'semantic_case_count':result['semantic']['passed']+len(result['semantic']['mismatches']),
       'tick_case_count':len(result['ticks']['rows']),'fixed_helper_case_count':result['fixed_helpers']['passed']+len(result['fixed_helpers']['mismatches']),
       'fixed_helper_counts':result['fixed_helpers']['counts'],
       'semantic_counts':result['semantic']['counts'],
       'external_helper_address_count':result['declared_external_helper_targets'],
       'unrecovered_external_helper_address_count':result['unrecovered_external_helper_targets'],
       'far_dependency_variant_count':len(far),
       'unrecovered_semantic_dependency_count':result['unrecovered_external_helper_targets']-1+len(far),
       'scope':'Local IR CPU/RAM/SRAM equivalence with original-ROM external helper oracle; semantic gameplay APIs compare gameplay fields/SRAM. ECEE NMI barrier is bypassed explicitly on both CPU sides.'}
    (args.out/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for row in result['mismatches'][:3]+result['blocked'][:3]+result['semantic']['mismatches'][:3]+result['fixed_helpers']['mismatches'][:3]:print(row)
    if failed:raise SystemExit(1)
