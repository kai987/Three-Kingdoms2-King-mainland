#!/usr/bin/env python3
"""Verify lifted duel handlers against actual ROM with explicit helper oracle.

Synthetic function fixtures are separate from unchanged-ROM Nestopia runs.
Only control instructions inside the recovered region are independently lifted;
external helpers execute their original bytes and are listed in every result.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered.duel_state_machine import (
    DuelMachine,Registers,commit_duel_hp,ROM_SHA256,initialize_duel_records,
    route_duel_action,check_duel_strike_end,prepare_duel_return,finish_duel_return,
    prepare_duel_handoff_header,
)


def bus_fixture(rom,ram,sram):
    b=Bus(rom,'alternating');b.ram[:]=ram;b.sram[:]=sram
    b.banks=[17,23,24,31];b.bank_initialized=[True]*4;b.protect=0x4c
    b.ram[0xe1:0xe4]=bytes([0x31,0x37,0x38])
    return b


class ActualHelperHooks:
    """Verification adapter: actual ROM helper bytes, never silent no-op hooks."""
    def __init__(self,bus):self.bus=bus;self.calls=[]
    def __call__(self,context,target,return_pc,kind):
        r=context.registers;m=MPU(memory=self.bus)
        m.pc,m.a,m.x,m.y,m.sp,m.p=target,r.a,r.x,r.y,r.sp,r.p
        self.bus.cpu=m
        stop=return_pc if return_pc is not None else 0x0200
        for count in range(100000):
            if m.pc==stop:break
            self.bus.pc=m.pc
            if m.disassemble[self.bus.peek(m.pc)][0]=='???':raise RuntimeError(f'Unrecognized helper opcode {m.pc:04X}')
            m.step()
        else:raise RuntimeError(f'Helper {target:04X} did not return, stopped {m.pc:04X}')
        r.pc,r.a,r.x,r.y,r.sp,r.p=m.pc,m.a,m.x,m.y,m.sp,m.p
        self.calls.append({'target':target,'kind':kind,'instructions':count})


def actual(bus,entry=0xb100,stop=0x0200):
    m=MPU(memory=bus);m.pc,m.sp,m.p=entry,0xfd,m.UNUSED
    bus.cpu=m;bus.ram[0x1fe:0x200]=bytes([255,1])
    for count in range(100000):
        if m.pc==stop or isinstance(stop,(tuple,list,set)) and m.pc in stop:return m,count
        bus.pc=m.pc
        if m.disassemble[bus.peek(m.pc)][0]=='???':raise RuntimeError(f'Unrecognized opcode {m.pc:04X}')
        m.step()
    raise RuntimeError(f'ROM fixture did not return, stopped {m.pc:04X}')


def verify(rom_path,out):
    rom=rom_path.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    data=json.loads((ROOT/'analysis/duel_fsm/state_machine.json').read_text())
    snap=ROOT/'analysis/runtime/phase3/attack-intro-7'
    ram=(Path(str(snap)+'-ram.bin')).read_bytes();sram=(Path(str(snap)+'-sram.bin')).read_bytes()
    fixtures=[];failures=[];coverage=set();hooks=Counter();writeback=[];semantic=[];sequences=[]
    for state in data['states']:
        for handler in state['handlers']:
            for buttons in (0,1,2):
                b=bus_fixture(rom,ram,sram)
                b.ram[0x4a8]=state['state'];b.ram[0x4a9]=handler['substate'];b.ram[0x4aa]=0
                b.ram[0x4ab:0x4af]=bytes([0,3,131,47]);b.ram[0x4b1:0x4b3]=bytes([50,30])
                b.ram[0x7c]=0  # NMI F9A9/F9AB resets OAM byte count before this callback.
                b.ram[0x81]=buttons;b.ram[0x87]=255;b.ram[0x7e]=0;b.ram[0x300]=255;b.ram[0x304]=255
                c=bus_fixture(rom,bytes(b.ram),bytes(b.sram))
                adapter=ActualHelperHooks(c);machine=DuelMachine(c,adapter)
                try:
                    expected,instructions=actual(b)
                    transition=machine.tick()
                    got=machine.registers
                    assert (got.a,got.x,got.y,got.sp,got.p,got.pc)==(expected.a,expected.x,expected.y,expected.sp,expected.p,expected.pc),('registers',asdict(got),vars(expected))
                    assert c.ram==b.ram,('RAM',[(i,b.ram[i],c.ram[i]) for i in range(2048) if c.ram[i]!=b.ram[i]][:8])
                    assert c.sram==b.sram,('SRAM',[(i,b.sram[i],c.sram[i]) for i in range(8192) if c.sram[i]!=b.sram[i]][:8])
                    assert c.banks==b.banks
                    fixtures.append({'state':state['state'],'substate':handler['substate'],'buttons_0081':buttons,'next_state':list(transition['after']),'rom_instructions':instructions,'lifted_instructions':transition['instructions'],'helper_calls':adapter.calls})
                    coverage.update(machine.executed);hooks.update(f'{v["target"]:04X}' for v in adapter.calls)
                except Exception as e:
                    failures.append({'state':state['state'],'substate':handler['substate'],'buttons':buttons,'error':str(e)[:1000]})
    baseline_coverage=len(coverage)
    # Real writeback core oracle, with distinct and aliased IDs and byte edges.
    for ids in [(131,47),(131,131)]:
        for left in (0,1,100,127,128,255):
            for right in (0,1,100,127,128,255):
                b=bus_fixture(rom,ram,sram);b.ram[0x4ad:0x4af]=bytes(ids);b.ram[0x4b1:0x4b3]=bytes([left,right])
                c=bus_fixture(rom,bytes(b.ram),bytes(b.sram))
                actual(b,0xd060,0xd074);writes=commit_duel_hp(c)
                assert c.sram==b.sram
                writeback.append({'ids':list(ids),'temporary_hp':[left,right],'writes':writes,'alias_last_write_wins':ids[0]==ids[1]})
    # Readable semantic functions independently reproduce declared game effects;
    # CPU registers/pointer scratch belong to the exact IR API, not this API.
    def semantic_case(name,entry,function,changes,stops=(0x0200,),kwargs=None,banks=None):
        b=bus_fixture(rom,ram,sram)
        if banks is not None:b.banks=list(banks)
        for address,value in changes.items():b[address]=value
        c=bus_fixture(rom,bytes(b.ram),bytes(b.sram))
        if banks is not None:c.banks=list(banks)
        expected,instructions=actual(b,entry,stops)
        effect=function(c,**(kwargs or {}))
        assert c.ram[0x400:]==b.ram[0x400:],(name,[(i,b.ram[i],c.ram[i]) for i in range(0x400,2048) if c.ram[i]!=b.ram[i]][:8])
        assert c.sram==b.sram,(name,'SRAM')
        assert c.ram[0x7a:0x80]==b.ram[0x7a:0x80],(name,'global controls')
        semantic.append({'function':name,'entry':entry,'inputs':changes,'returned_effect':effect,'rom_stop':expected.pc,'rom_instructions':instructions})
    for controls in ((left,right) for left in (0,1,2,3,128,255) for right in (0,1,2,3,128,255)):
        for ids in ((131,47),(131,131)):
            for substate in (0,255):
                semantic_case('prepare_duel_handoff_header',0xcd61,prepare_duel_handoff_header,
                    {0x541:substate,0x560:ids[0],0x561:ids[1],0x562:controls[0],0x563:controls[1]},banks=(17,14,15,31))
    for fade in (0,1,127,128,255):
        for weapons in ((0,7),(8,15),(16,23),(24,31)):
            semantic_case('initialize_duel_records',0xb15a,initialize_duel_records,
                {0x87:fade,0x4a9:0,0x4ad:131,0x4ae:47,0x63c0+12*131+10:weapons[0],0x63c0+12*47+10:weapons[1]},(0x0200,0xcdfd))
    for actor in (0,1):
        for category in range(10):
            b=bus_fixture(rom,ram,sram);b[0x4aa]=actor;b[0x4ad]=131;b[0x4ae]=47
            predicate,_=actual(b,0xd262)
            semantic_case('route_duel_action',0xb47e,route_duel_action,
                {0x4aa:actor,0x4a8:1,0x4a9:3,0x4ad:131,0x4ae:47,0x4bf:category},(0x0200,0xf28b),{'is_ruler':bool(predicate.p&1)})
    for actor in (0,1):
        for hp0 in (0,1,127,128,255):
            for hp1 in (0,1,127,128,255):
                for display_flag in (0,4,255):
                    semantic_case('check_duel_strike_end',0xb9c8,check_duel_strike_end,
                        {0x4aa:actor,0x4a8:3,0x4a9:2,0x4ad:131,0x4ae:47,0x4b1:hp0,0x4b2:hp1,0x7e:display_flag})
    for left in range(5):
        for right in range(5):
            semantic_case('prepare_duel_return',0xc30e,prepare_duel_return,
                {0x4a8:14,0x4a9:0,0x4ad:131,0x4ae:47,0x515:left,0x517:right},(0x0200,0xecee))
    for attack in (False,True):
        for fade in (0,1,127,128,255):
            for owner in (0,1,2,3,255):
                semantic_case('finish_duel_return',0xc480 if attack else 0xc33b,finish_duel_return,
                    {0x87:fade,0x50f:owner},(0x0200,0xecbf),{'restart_attack':attack})
    # Multi-tick handler sequences keep real RAM between ticks. Host preconditions
    # are explicit fixture inputs, not claims of autonomous graphics completion.
    for defeated in (None,0,1):
        b=bus_fixture(rom,ram,sram)
        b[0x4ad]=131;b[0x4ae]=47;b[0x4aa]=0
        b[0x4a8]=3;b[0x4a9]=1;b[0x4b1]=50;b[0x4b2]=30
        if defeated is not None:b[0x4b1+defeated]=0
        c=bus_fixture(rom,bytes(b.ram),bytes(b.sram))
        machine=DuelMachine(c,ActualHelperHooks(c));steps=[]
        for phase in ('confirm_hp','wait_display','check_hp','return_header','finish_return'):
            if phase in ('return_header','finish_return') and defeated is None:break
            injection={0x7c:0,0x81:1,0x87:255,0x300:255,0x304:255}
            if phase=='wait_display':injection[0x7e]=4
            if phase=='check_hp':injection[0x7e]=0
            if phase=='return_header':injection.update({0x4a8:14,0x4a9:0,0x4c0:255})
            if phase=='finish_return':injection.update({0x4a8:14,0x4a9:1})
            for address,value in injection.items():b[address]=value;c[address]=value
            expected,count=actual(b);transition=machine.tick();got=machine.registers
            assert c.ram==b.ram and c.sram==b.sram and c.banks==b.banks,(phase,'memory')
            assert (got.a,got.x,got.y,got.sp,got.p,got.pc)==(expected.a,expected.x,expected.y,expected.sp,expected.p,expected.pc),(phase,'registers')
            coverage.update(machine.executed)
            steps.append({'phase':phase,'explicit_fixture_inputs':injection,'before':transition['before'],'after':transition['after'],'global_state':c[0x7a],'hp_records':[c[0x63c0+12*131],c[0x63c0+12*47]],'rom_instructions':count})
        sequences.append({'defeated_side':defeated,'steps':steps,'animation_skip_explicit':defeated is not None})
    out.mkdir(parents=True,exist_ok=True)
    result={'rom_sha256':ROM_SHA256,'status':'passed' if not failures else 'partial_with_explicit_failures','synthetic_ram_initialization':True,
        'complete_emulator_validation':False,'fixture_source':str(snap.relative_to(ROOT)),'case_count':len(fixtures),'failed_count':len(failures),
        'instruction_ir_coverage':len(coverage),'handler_fixture_ir_coverage':baseline_coverage,'instruction_ir_total':data['instruction_count'],'external_helper_counts':dict(hooks),'fixtures':fixtures,'failures':failures,'writeback_cases':writeback,
        'semantic_case_count':len(semantic),'semantic_cases':semantic,'multi_tick_sequences':sequences,
        'scope':'Independent lifted control/ALU/memory effects against original 6502; external dependencies use actual ROM helper adapter, not independently recovered source.'}
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','case_count','failed_count','instruction_ir_coverage','instruction_ir_total']},indent=2))
    if failures:print(json.dumps(failures[:8],indent=2))


def verify_core_fixture(rom_path,out):
    """Full Nestopia integration with fully declared synthetic state injection.

    This is not a cold-start gameplay-reachability proof. Original ROM bytes,
    real NMI/PPU/APU/controller logic and all external display helpers run in the
    complete core; injected scene/header/HP/parameter fields are listed exactly.
    """
    import ctypes as C
    from nes_runtime import Runtime
    from source.recovered.battle import Officer,duel_attack_parameters
    from source.recovered.game_algorithms import PermutationRng
    rom=rom_path.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    snap=ROOT/'analysis/runtime/phase3/attack-intro-7.state'
    out=out/'runtime/injected-core';out.mkdir(parents=True,exist_ok=True)
    runtime=Runtime(rom_path,out);transitions=[];captures=[];seen=set();prior=None
    try:
        runtime.load_state(snap)
        ram=bytearray(runtime.memory(2));sram=bytearray(runtime.memory(0))
        injected_ram={0x7a:7,0x4a8:0,0x4a9:0,0x4aa:0,0x4ab:0,0x4ac:0,
            0x4ad:131,0x4ae:47,0x560:131,0x561:47,0x562:0,0x563:0}
        injected_sram={0x63c0+12*131:80,0x63c0+12*47:5}
        for address,value in injected_sram.items():sram[address-0x6000]=value
        rng=PermutationRng(rom[16+31*8192+0x8ba:16+31*8192+0x9ba],[ram[0x50],ram[0x52],ram[0x54],ram[0x55]])
        weapon=rom[16+15*8192+0xa1f:16+15*8192+0xa3f]
        armor=rom[16+15*8192+0xa37:16+15*8192+0xa3f]
        for side,officer_id in enumerate((131,47)):
            record=Officer(bytes(sram[0x3c0+12*officer_id:0x3c0+12*officer_id+12]))
            base,attack,defense=duel_attack_parameters(record,weapon,armor,rng)
            injected_ram.update({0x4c1+side:base,0x570+side:attack,0x56e+side:defense})
        injected_ram[0x50]=rng.cursors[0]
        for address,value in injected_ram.items():ram[address]=value
        C.memmove(runtime.core.retro_get_memory_data(2),bytes(ram),len(ram))
        C.memmove(runtime.core.retro_get_memory_data(0),bytes(sram),len(sram))
        fixture={'rom_sha256':ROM_SHA256,'source_state':str(snap.relative_to(ROOT)),
            'source_state_sha256':hashlib.sha256(snap.read_bytes()).hexdigest(),
            'ram_injections':injected_ram,'sram_injections':injected_sram,
            'parameter_origin':'independently verified C991 readable algorithm, explicit fixture preparation',
            'natural_gameplay':False,'rom_modified':False,'purpose':'NMI/animation/writeback/return integration of an injected duel scene'}
        runtime.events.append({'explicit_synthetic_fixture':fixture})
        def observe(r):
            nonlocal prior
            m=r.memory(2);save=r.memory(0)
            key=tuple(m[a] for a in (0x7a,0x78,0x4a8,0x4a9,0x4aa,0x4b1,0x4b2,0x500,0x501,0x540,0x541))
            if key!=prior:
                transitions.append({'frame':r.frames,'global_state':m[0x7a],'nmi_mode':m[0x78],
                    'duel_state':m[0x4a8],'duel_substate':m[0x4a9],'actor':m[0x4aa],
                    'temporary_hp':list(m[0x4b1:0x4b3]),'battle_state':[m[0x500],m[0x501]],
                    'attack_state':[m[0x540],m[0x541]],
                    'permanent_hp':[save[0x3c0+12*i] for i in (131,47)],
                    'record_status_low2':[save[0x3c0+12*i+11]&3 for i in (131,47)]})
                prior=key
            if m[0x78]==5 and m[0x4a8] not in seen:
                seen.add(m[0x4a8]);label=f'fixture-state-{m[0x4a8]:02d}'
                r.snapshot(label);captures.append(label)
        runtime.run(1,observer=observe);runtime.snapshot('fixture-entry')
        for pulse in range(300):
            runtime.run(2,['a'],observe);runtime.run(30,observer=observe)
            m=runtime.memory(2)
            if pulse>5 and m[0x7a] in (3,4,5,6):break
        runtime.snapshot('fixture-final')
        final_sram=runtime.memory(0)
        record_deltas=[]
        for officer_id in (131,47):
            start=0x3c0+12*officer_id
            record_deltas.append({'officer_id':officer_id,'changes':[
                {'byte':i,'before':sram[start+i],'after':final_sram[start+i]}
                for i in range(12) if sram[start+i]!=final_sram[start+i]]})
        checks={'entered_real_duel_nmi':5 in [v['nmi_mode'] for v in transitions],
            'initial_hp_read_from_records':any(v['temporary_hp']==[80,5] for v in transitions),
            'temporary_damage_before_commit':any(v['temporary_hp']==[74,0] and v['permanent_hp']==[74,5] for v in transitions),
            'permanent_hp_commit':any(v['permanent_hp']==[74,0] for v in transitions),
            'returned_battle_state11':any(v['global_state']==3 and v['battle_state']==[11,0] for v in transitions),
            'duel_did_not_change_record_status':all(v['record_status_low2']==[2,1] for v in transitions)}
        result={**fixture,'engine':runtime.info,'frames':runtime.frames,'inputs_and_imports':runtime.events,
            'transitions':transitions,'main_states_observed':sorted(seen),'captures':captures,
            'returned_global_state':runtime.memory(2)[0x7a],
            'completed_duel_return':runtime.memory(2)[0x7a] in (3,4,5,6),
            'checks':checks,'checks_passed':all(checks.values()),'officer_record_deltas':record_deltas,
            'memory_region_sizes':{'ram':len(runtime.memory(2)),'sram':len(runtime.memory(0)),'vram':len(runtime.memory(3))},
            'unavailable_regions':['VRAM: libretro memory3 returns0B in this pinned core; empty files are not validation evidence'],
            'checkpoint_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.suffix in ('.png','.bin','.state') and p.stat().st_size>0},
            'empty_checkpoint_files_excluded':[p.name for p in sorted(out.iterdir()) if p.suffix in ('.png','.bin','.state') and p.stat().st_size==0],
            'scope':'Complete emulator integration of an explicitly injected scene; no natural reachability claim and no silent graphics hooks.'}
        (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('frames','main_states_observed','returned_global_state','completed_duel_return')}))
    finally:runtime.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/duel_fsm');p.add_argument('--core-fixture',action='store_true');a=p.parse_args()
    verify_core_fixture(a.rom,a.out) if a.core_fixture else verify(a.rom,a.out)
