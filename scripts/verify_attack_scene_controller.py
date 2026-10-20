#!/usr/bin/env python3
"""Original ROM differential checks of the independent attack controller.

External CPU callbacks are a verification adapter, counted separately. Missing
services are compared at the real first call boundary, never replaced by RTS.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.attack_scene_controller import AttackSceneController,AttackRegisters,ROM_SHA256

OUT=ROOT/'analysis/phase11/attack'
REGS=('a','x','y','sp','p','pc')

class OriginalServices:
    """Execute only an explicitly yielded service and its real caller return."""
    def __init__(self,bus):self.bus=bus;self.calls=[]
    def __call__(self,call):
        r=call.registers;cpu=MPU(memory=self.bus)
        for key in REGS:setattr(cpu,key,getattr(r,key))
        self.bus.cpu=cpu
        for n in range(200000):
            if cpu.pc==call.return_pc and cpu.sp==call.expected_sp:break
            self.bus.pc=cpu.pc
            if cpu.disassemble[self.bus.peek(cpu.pc)][0]=='???':raise RuntimeError(f'Invalid service opcode ${cpu.pc:04X}')
            cpu.step()
        else:return dict(status='dependency',reason='Original service did not reach its actual return',pc=cpu.pc)
        for key in REGS:setattr(r,key,getattr(cpu,key))
        self.calls.append(dict(target=call.target,kind=call.kind,return_pc=call.return_pc,
                               entry_banks=list(call.entry_banks),expected_sp=call.expected_sp,
                               original_CPU_instructions=n))
        return {'status':'returned'}

def verify(rom,out):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    old=json.loads((ROOT/'analysis/attack_fsm/state-catalog.json').read_text())
    source_catalog=json.loads((out/'catalog.json').read_text())
    snapshot=ROOT/'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu'
    raw_ram=Path(str(snapshot)+'-ram.bin').read_bytes();raw_sram=Path(str(snapshot)+'-sram.bin').read_bytes()
    counts=Counter();failures=[];samples=[];guards=[];coverage=Counter();callback_counts=Counter()
    def fresh():
        b=PortBus(rom);b.status_mode='alternating';b.ram[:]=raw_ram;b.sram[:]=raw_sram
        b.banks=[17,14,15,31];b.bank_initialized=[True]*4;b.protect=0x4C
        b.ram[0xDE:0xE4]=bytes([49,46,47,49,46,47]);b.ram[0x1FE:0x200]=bytes([255,1])
        for a,v in {0x540:0,0x541:0,0x545:0,0x546:0,0x547:0,0x548:0,0x549:1,0x54A:1,0x54B:1,
                    0x560:131,0x561:47,0x564:0,0x565:1,0x568:0,0x569:0,
                    0x7C:0,0x7E:0,0x81:0,0x87:255,0x300:255,0x304:255,0x7A:6}.items():b[a]=v
        b.ram[0x550:0x558]=bytes(8);b.ram[0x580:0x596]=bytes([0]*21+[255])
        b.ram[0x5AC:0x5D8]=bytes(44);b.ram[0x522:0x526]=bytes([188,2,44,1]);return b
    def copy(b):
        c=PortBus(rom);c.status_mode=b.status_mode;c.ram[:]=b.ram;c.sram[:]=b.sram
        c.banks=b.banks[:];c.bank_initialized=[True]*4;c.protect=b.protect;return c
    def original(b,entry,r,stop=0x200,prefix=None):
        cpu=MPU(memory=b,pc=entry)
        for key in REGS:setattr(cpu,key,getattr(r,key))
        cpu.pc=entry;b.cpu=cpu;b.record_ports=True
        for n in range(300000):
            if prefix is not None:
                if cpu.pc==prefix.target and cpu.sp==prefix.registers.sp:break
            elif cpu.pc==stop:break
            b.pc=cpu.pc;origin=b.origin(cpu.pc)
            if origin is None:raise RuntimeError(f'Unexpected source fixture execution ${cpu.pc:04X}')
            bank,offset=origin
            if bank in(14,15)and cpu.pc<0xD8D4:coverage[(bank,cpu.pc,offset+16)]+=1
            cpu.step()
        else:raise RuntimeError(f'Original attack budget ${cpu.pc:04X}')
        return cpu,n
    def equality(b,c,actual,r):
        assert all(getattr(actual,k)==getattr(r,k)for k in REGS),('registers', {k:getattr(actual,k)for k in REGS},asdict(r))
        assert b.ram==c.ram,('RAM',[(hex(i),b.ram[i],c.ram[i])for i in range(2048)if b.ram[i]!=c.ram[i]][:12])
        assert b.sram==c.sram,('SRAM',[(hex(0x6000+i),b.sram[i],c.sram[i])for i in range(8192)if b.sram[i]!=c.sram[i]][:12])
        assert b.ports==c.ports,('ports',b.ports[:15],c.ports[:15],len(b.ports),len(c.ports))
        assert b.banks==c.banks,('banks',b.banks,c.banks)
        assert b.vram==c.vram and b.ppu==c.ppu,('synthetic PPU register-image mismatch')
    def compare(kind,b,entry,meta,*,prefix=False,r=None):
        r=r or AttackRegisters();c=copy(b);c.record_ports=True;adapter=OriginalServices(c)
        controller=AttackSceneController(c,rom,services=None if prefix else adapter)
        try:
            result=controller.run_entry(entry,registers=AttackRegisters(**asdict(r)))
            pending=controller.pending if result['status']=='dependency' else None
            if prefix:
                assert result['status']in('dependency','returned'),result['status']
            else:assert result['status']=='returned',result['status']
            actual,n=original(b,entry,r,prefix=pending)
            equality(b,c,actual,controller.registers)
            label=kind+('_strict_prefix'if pending else'_complete')
            counts[label]+=1;callback_counts.update(f'{x["target"]:04X}'for x in adapter.calls)
            if sum(s['kind']==label for s in samples)<12:
                samples.append(dict(kind=label,entry=entry,input=meta,original_CPU_instructions=n,
                                    after=result['after'],original_CPU_service_callbacks=adapter.calls,
                                    pending_target=None if pending is None else pending.target,
                                    source_control_blocks=result['control_blocks']))
        except Exception as exc:
            failures.append(dict(kind=kind,entry=entry,input=meta,error=str(exc)))
            if len(failures)<=6:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
    # Every bounded main/sub entry, through both direct controller and actual
    # NMI4 wrapper. The same inputs also prove the first missing-service edge.
    for s in old['states']:
        for h in s['handlers']:
            for button in(0,1,2):
                for entry in(0xA069,0xA000):
                    b=fresh();b[0x540]=s['state'];b[0x541]=h['substate'];b[0x81]=button
                    meta=[s['state'],h['substate'],button]
                    compare('legal_controller'if entry==0xA069 else'actual_NMI4_wrapper',b,entry,meta)
                    if entry==0xA069:
                        b=fresh();b[0x540]=s['state'];b[0x541]=h['substate'];b[0x81]=button
                        compare('missing_services',b,entry,meta,prefix=True)
    # Real A095->C926 initialization, fade and martial coefficient boundaries.
    for fade in(0,1,127,128,255):
        for martial in(0,49,50,64,65,79,80,86,87,91,92,96,97,99,255):
            b=fresh();b[0x87]=fade
            b[0x63C0+12*131+1]=martial;b[0x63C0+12*47+1]=99
            b[0x63C0+12*131+10]=23|7<<5
            compare('full_initialization_A095_C926',b,0xA095,[fade,martial,23,7])
    # All75 proven table arms, including the extra six-way AF17 object table.
    for table in old['dispatch_tables']:
        for index,target in enumerate(table['targets']):
            b=fresh()
            parent=next((s for s in old['states']if s['dispatch_pc']==table['call_pc']),None)
            if parent is not None:b[0x540]=parent['state'];b[0x541]=index
            if table['call_pc']==0xA06C:b[0x540]=index
            compare('every_legal_dispatch_arm',b,table['call_pc'],[index,target],r=AttackRegisters(a=index,y=127))
    # Meaningful direct coverage of the three semantic axis-search rewrites.
    for entry in(0xC064,0xC20F,0xC30F):
        for actor in(1,12):
            for object_class in(0,2,3):
                for distance in(0,1,3):
                    for cursor in(0,17):
                        b=fresh();b[0x545]=actor;b[0x50]=cursor;b[0x54F]=int(cursor!=0);b[0x575]=0x11
                        b.ram[0x580:0x596]=bytes([255]*22);b.ram[0x596:0x5AC]=bytes([255]*22)
                        b[0x580]=3;b[0x596]=3;b[0x58B]=12;b[0x5A1]=7
                        b[0x580+actor]=8;b[0x596+actor]=5;b[0x5C2+actor]=object_class
                        if distance:
                            target=12 if actor==1 else 1;b[0x580+target]=8+distance;b[0x596+target]=5;b[0x5C2+target]=2
                        compare('semantic_axis_search',b,entry,[actor,object_class,distance,cursor],r=AttackRegisters(y=actor))
    # Source-only guards: failed/budget/unknown callbacks cannot pop a return.
    for status in('dependency','budget','waiting','blocked','failed','error'):
        b=fresh();controller=AttackSceneController(b,rom,services=lambda call:{'status':status})
        result=controller.run_entry(0xA095)
        assert result['status']=='dependency' and controller.pending is not None
        before=(bytes(b.ram),bytes(b.sram),b.banks[:],list(b.ports),asdict(controller.registers))
        assert controller.resume()['status']=='dependency'
        assert before==(bytes(b.ram),bytes(b.sram),b.banks[:],list(b.ports),asdict(controller.registers))
        guards.append('service_'+status+'_retains_real_call')
    for field,value in((0x540,11),(0x541,5)):
        b=fresh();b[field]=value
        try:AttackSceneController(b,rom).run_entry(0xA069)
        except ValueError:guards.append('invalid_main'if field==0x540 else'invalid_sub')
        else:raise AssertionError('Out-of-table state was not rejected')
    b=fresh();controller=AttackSceneController(b,rom,services=lambda call:{'status':'returned'})
    assert controller.run_entry(0xA095)['status']=='dependency';guards.append('returned_without_PC_SP_is_not_return')
    b=fresh();controller=AttackSceneController(b,rom)
    assert controller.run_entry(0xA069,max_blocks=0)['status']=='budget';guards.append('source_budget_never_returns')
    try:controller.resume()
    except RuntimeError:guards.append('budget_cannot_resume_closed_body_as_RTS')
    else:raise AssertionError('Closed budget body resumed')
    result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
                rom_cpu_case_count=sum(counts.values()),actual_ROM_CPU_comparison_count=sum(counts.values()),
                counts=dict(counts),failed_count=len(failures),failures=failures,
                complete_CPU_count=sum(n for k,n in counts.items()if k.endswith('_complete')),
                strict_prefix_CPU_count=sum(n for k,n in counts.items()if k.endswith('_strict_prefix')),
                source_guard_case_count=len(guards),source_guards=guards,samples=samples,
                original_CPU_service_callback_count=sum(callback_counts.values()),external_helper_counts=dict(callback_counts),
                compared_RAM_bytes=2048,compared_SRAM_bytes=8192,stack_page_compared=True,
                returned_register_contract=list(REGS),ordered_port_writes_compared=True,banks_compared=True,
                synthetic_PPU_register_image_compared=True,actual_NES_frame_or_IRQ_or_PCM_synthesized=False,
                fixture_provenance=dict(snapshot=str(snapshot.relative_to(ROOT)),RAM_sha256=hashlib.sha256(raw_ram).hexdigest(),SRAM_sha256=hashlib.sha256(raw_sram).hexdigest(),
                                        controlled_fields='state/substate/buttons,object indices and arrays,fade,RNG,participant IDs/controller/stat fields,real caller return',
                                        original_snapshot_has_one_explicit_adjacent_enemy_coordinate=True,hardware_inputs='alternating synthetic PPUSTATUS;APU/handheld controller default0 in bounded Bus'),
                source_kind='independent direct named functions/if/natural while plus three semantic axis algorithms',
                source_runtime_IR_interpretation=False,source_original_ROM_fallback=False,
                external_helpers_are_actual_ROM_oracle_in_this_validator=True,
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in('source/recovered/attack_scene_controller.py','scripts/analyze_attack_scene_controller.py','scripts/verify_attack_scene_controller.py','source/recovered/battle_nmi_services.py')},
                dynamic_original_instruction_locations=len(coverage),static_original_instruction_nodes=source_catalog['original_instruction_nodes'])
    out.mkdir(parents=True,exist_ok=True);(out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(coverage.items())],indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_CPU_count','strict_prefix_CPU_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False))
    if failures:raise SystemExit(1)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=OUT);a=p.parse_args()
    verify(a.rom.read_bytes(),a.out)
