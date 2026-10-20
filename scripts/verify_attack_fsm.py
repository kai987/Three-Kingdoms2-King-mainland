#!/usr/bin/env python3
"""Compare lifted normal-attack IR with original bank14/15 instructions.

All legal main/substate entries get synthetic RAM fixtures. External helper
hooks execute original helper bytes and remain declared dependencies.
"""
from pathlib import Path
import argparse,sys,json,hashlib
from dataclasses import asdict
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.attack_state_machine import AttackStateMachine,Registers,ROM_SHA256,initialize_attack_control,handoff_to_duel,return_to_battle

def bus_fixture(rom,ram,sram):
    b=Bus(rom,'alternating');b.ram[:]=ram;b.sram[:]=sram
    b.banks=[17,14,15,31];b.bank_initialized=[True]*4;b.protect=0x4c
    b.ram[0xe1:0xe4]=bytes([0x31,0x2e,0x2f]);return b

class ActualHelperHooks:
    """Verification adapter: actual helpers, never a success/no-op stub."""
    def __init__(self,bus):self.bus=bus;self.calls=[]
    def __call__(self,context,target,return_pc,kind):
        r=context.registers;m=MPU(memory=self.bus);m.pc,m.a,m.x,m.y,m.sp,m.p=target,r.a,r.x,r.y,r.sp,r.p
        self.bus.cpu=m;stop=return_pc if return_pc is not None else 0x0200
        for count in range(100000):
            if m.pc==stop:break
            self.bus.pc=m.pc
            if m.disassemble[self.bus.peek(m.pc)][0]=='???':raise RuntimeError(f'Unsupported helper opcode at {m.pc:04X}')
            m.step()
        else:raise RuntimeError(f'Helper {target:04X} did not return: {m.pc:04X}')
        r.pc,r.a,r.x,r.y,r.sp,r.p=m.pc,m.a,m.x,m.y,m.sp,m.p
        self.calls.append({'target':target,'kind':kind,'instructions':count})

def actual(bus,entry=0xa069,stop=0x0200,registers=None):
    m=MPU(memory=bus);m.pc,m.sp,m.p=entry,0xfd,m.UNUSED;bus.cpu=m
    for key,value in (registers or{}).items():setattr(m,key,value)
    bus.ram[0x1fe:0x200]=bytes([255,1])
    for count in range(100000):
        if m.pc==stop:return m,count
        bus.pc=m.pc
        if m.disassemble[bus.peek(m.pc)][0]=='???':raise RuntimeError(f'Unsupported original opcode at {m.pc:04X}')
        m.step()
    raise RuntimeError(f'Original fixture did not return: {m.pc:04X}')

def verify(rom_path,out):
    rom=rom_path.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    catalog=json.loads((ROOT/'analysis/attack_fsm/state-catalog.json').read_text())
    snap=ROOT/'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu'
    ram=Path(str(snap)+'-ram.bin').read_bytes();sram=Path(str(snap)+'-sram.bin').read_bytes()
    fixtures=[];failures=[];coverage=set();hook_counts=Counter()
    for state in catalog['states']:
        for handler in state['handlers']:
            for buttons in (0,1,2):
                b=bus_fixture(rom,ram,sram)
                inputs={0x540:state['state'],0x541:handler['substate'],0x545:0,0x546:0,0x547:0,0x548:0,0x549:1,0x54a:1,0x54b:1,
                    0x560:131,0x561:47,0x564:0,0x565:1,0x568:0,0x569:0,
                    0x7c:0,0x7e:0,0x81:buttons,0x87:255,0x300:255,0x304:255,0x7a:6}
                for address,value in inputs.items():b[address]=value
                b.ram[0x550:0x558]=bytes(8);b.ram[0x580:0x596]=bytes([0]*21+[255])
                b.ram[0x5ac:0x5d8]=bytes(44)
                b.ram[0x522:0x526]=bytes([188,2,44,1])
                c=bus_fixture(rom,bytes(b.ram),bytes(b.sram));adapter=ActualHelperHooks(c);machine=AttackStateMachine(c,adapter)
                try:
                    expected,steps=actual(b);transition=machine.step();got=machine.registers
                    assert (got.a,got.x,got.y,got.sp,got.p,got.pc)==(expected.a,expected.x,expected.y,expected.sp,expected.p,expected.pc),('registers',asdict(got),{k:getattr(expected,k)for k in ['a','x','y','sp','p','pc']})
                    assert c.ram==b.ram,('RAM',[(i,b.ram[i],c.ram[i])for i in range(2048)if c.ram[i]!=b.ram[i]][:8])
                    assert c.sram==b.sram,('SRAM',[(i,b.sram[i],c.sram[i])for i in range(8192)if c.sram[i]!=b.sram[i]][:8])
                    assert c.banks==b.banks and c.vram==b.vram
                    fixtures.append({'state':state['state'],'substate':handler['substate'],'buttons_0081':buttons,'after':transition['after'],'global_after':c[0x7a],'rom_instructions':steps,'lifted_instructions':transition['instructions'],'helper_calls':adapter.calls})
                    coverage.update(machine.executed);hook_counts.update(f'{call["target"]:04X}'for call in adapter.calls)
                except Exception as e:failures.append({'state':state['state'],'substate':handler['substate'],'buttons':buttons,'error':str(e)[:1500]})
    semantic=[]
    def semantic_case(name,entry,fun,inputs,stop=0x0200):
        b=bus_fixture(rom,ram,sram)
        for address,value in inputs.items():b[address]=value
        c=bus_fixture(rom,bytes(b.ram),bytes(b.sram));expected,count=actual(b,entry,stop);effect=fun(c)
        assert c.ram[0x400:]==b.ram[0x400:]and c.sram==b.sram,(name,'game data differs')
        assert c.ram[0x7a:0x80]==b.ram[0x7a:0x80],(name,'global controls differ')
        semantic.append({'function':name,'entry':entry,'inputs':inputs,'effect':effect,'rom_instructions':count})
    for fade in range(256):
        semantic_case('initialize_attack_control',0xa095,initialize_attack_control,{0x87:fade,0x540:0,0x541:0},0xa0cf if fade&128 else 0x0200)
        semantic_case('return_to_battle',0xa3f2,return_to_battle,{0x87:fade,0x500:3,0x501:2,0x7a:6})
    for first_party in [0,1,2,3,127,128,255]:
        for second_party in [0,1,2,3,127,128,255]:
            for substate in [0,1,127,255]:
                semantic_case('handoff_to_duel',0xcd61,handoff_to_duel,{0x541:substate,0x560:131,0x561:8,0x562:first_party,0x563:second_party})
    dispatch=[]
    for table in catalog['dispatch_tables']:
        for index,target in enumerate(table['targets']):
            b=bus_fixture(rom,ram,sram);c=bus_fixture(rom,ram,sram);expected,count=actual(b,table['call_pc'],target,{'a':index,'y':127})
            machine=AttackStateMachine(c,ActualHelperHooks(c));machine.run_entry(table['call_pc'],registers=Registers(a=index,y=127),stop_pc=target)
            got=machine.registers
            assert (got.a,got.x,got.y,got.sp,got.p,got.pc)==(expected.a,expected.x,expected.y,expected.sp,expected.p,expected.pc)
            assert c.ram==b.ram and c.sram==b.sram
            dispatch.append({'call_pc':table['call_pc'],'index':index,'target':target,'rom_instructions':count})
    out.mkdir(parents=True,exist_ok=True)
    result={'rom_sha256':ROM_SHA256,'status':'passed'if not failures else'partial_with_explicit_failures','synthetic_ram_initialization':True,'complete_emulator_validation':False,'fixture_source':str(snap.relative_to(ROOT)),'fixture_note':'Source snapshot has one explicitly injected enemy coordinate; original battle controller prepared attack parameters. Per-handler oracle additionally initializes scene object indices/arrays and buttons, separately from the native core screenshot.','case_count':len(fixtures),'failed_count':len(failures),'instruction_ir_coverage':len(coverage),'instruction_ir_total':catalog['instruction_count'],'external_helper_counts':dict(hook_counts),'fixtures':fixtures,'failures':failures,'semantic_case_count':len(semantic),'semantic_cases':semantic,'dispatch_case_count':len(dispatch),'dispatch_cases':dispatch,'scope':'Independent instruction IR control/ALU/memory behavior compared with original6502; external helpers use actual ROM oracle hooks, not independently recovered source.'}
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','case_count','failed_count','instruction_ir_coverage','instruction_ir_total']},indent=2))
    if failures:print(json.dumps(failures[:8],ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/attack_fsm');a=p.parse_args();verify(a.rom,a.out)
