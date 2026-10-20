#!/usr/bin/env python3
"""Compare unified source APIs and genuine nested caller protocols with this ROM."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.game_engine import GameEngine, snapshot_memory, ROM_SHA256
from source.recovered.battle_state_machine import Registers, UnresolvedDependency
from source.recovered.controller_helpers import MissingSharedHelper
from source.recovered.mapped_memory import UnsupportedHardware

def context(rom):
    prefix = ROOT / 'analysis/phase5/runtime/city-info/menu-0'
    bus = Bus(rom, 'zero')
    bus.ram[:] = Path(str(prefix) + '-ram.bin').read_bytes()
    bus.sram[:] = Path(str(prefix) + '-sram.bin').read_bytes()
    bus.banks = [2, 25, 26, 31]
    bus.bank_initialized = [True]*4
    bus.protect = 0x4C
    return bus

def game_from_bus(bus, rom):
    game = GameEngine(snapshot_memory(bytes(bus.ram), bytes(bus.sram)), rom=rom,
                      mapped=True, data_window_bank=bus.banks[0])
    game.memory.banks[:] = bus.banks
    return game

def oracle(bus, entry, registers, stop, max_steps=400000):
    cpu = MPU(memory=bus); bus.cpu = cpu
    for name in ('a', 'x', 'y', 'sp', 'p'): setattr(cpu, name, getattr(registers, name))
    cpu.pc = entry
    for n in range(max_steps):
        if n and cpu.pc == stop: return cpu, n
        bus.pc = cpu.pc; bus.step_no = n; cpu.step()
    raise AssertionError(f'Original ROM did not reach {stop:04X}; PC={cpu.pc:04X}')

def compare(bus, game, cpu, source_registers):
    assert bytes(bus.ram) == bytes(game.memory.ram), ('RAM', [(hex(i), bus.ram[i], game.memory.ram[i]) for i in range(2048) if bus.ram[i] != game.memory.ram[i]][:8])
    assert bytes(bus.sram) == bytes(game.memory.sram), ('SRAM', [(hex(0x6000+i), bus.sram[i], game.memory.sram[i]) for i in range(8192) if bus.sram[i] != game.memory.sram[i]][:8])
    assert bus.banks == game.memory.banks, (bus.banks, game.memory.banks)
    assert all(getattr(cpu, name) == getattr(source_registers, name) for name in ('a', 'x', 'y', 'sp', 'p', 'pc')), ({k:getattr(cpu,k) for k in ('a','x','y','sp','p','pc')}, vars(source_registers))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    args = p.parse_args(); rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    counts, cases, failures, guards = Counter(), [], [], []
    def trial(label, run):
        try: run()
        except Exception as exc: failures.append({'case': label, 'type': type(exc).__name__, 'message': str(exc)})
    for main_state in range(15):
        for marker in (0, 255):
            def run(main_state=main_state, marker=marker):
                bus = context(rom); bus.ram[0x7A] = main_state
                bus.sram[0xF8B] = marker
                # This is a valid cooperative AI-entry context, not flag1 battle return.
                bus.sram[0xF5B] = 0; bus.sram[0xF5D] = 50
                game = game_from_bus(bus, rom)
                regs = Registers(a=17, x=23, y=31, sp=0xFD, p=32)
                result = game.tick_global(entry_banks=tuple(bus.banks), registers=regs, max_instructions=200000)
                assert result['status'] in ('boundary', 'dependency'), result
                stop = game._global.registers.pc
                cpu, steps = oracle(bus, 0xE066, Registers(a=17,x=23,y=31,sp=0xFD,p=32), stop)
                compare(bus, game, cpu, game._global.registers)
                counts['global_' + result['status']] += 1
                cases.append({'kind': 'global', 'main': main_state, 'marker': marker,
                              'status': result['status'], 'stop_pc': stop, 'oracle_steps': steps,
                              'nested_domestic_source_used': game._domestic_control is not None})
            trial(f'global-{main_state}-{marker}', run)
    # Caller-owned nested return: the real FA85 JSR return bytes are supplied,
    # and the source bridge must leave unrelated1FE/1FF unchanged.
    for mode in range(6):
        def run(mode=mode):
            bus = context(rom); bus.banks = [2,23,24,31]
            bus.ram[0x541] = mode; bus.ram[0x542] = 0
            bus.ram[0x4CA] = 1; bus.ram[0x300] = bus.ram[0x304] = 255
            bus.ram[0x1FC:0x1FE] = bytes([0x87,0xFA])
            bus.ram[0x1FE:0x200] = bytes([0xA6,0x59])
            game = game_from_bus(bus, rom)
            borrowed = Registers(a=19,x=29,y=39,sp=0xFB,p=32,pc=0xA01E)
            class Caller:
                registers = borrowed
            caller = Caller()
            result = None
            try: result = game._global_source_call(caller, 0xA01E, 0xFA88, 'call')
            except (MissingSharedHelper, UnresolvedDependency, UnsupportedHardware): pass
            stop = caller.registers.pc
            cpu, steps = oracle(bus, 0xA01E, Registers(a=19,x=29,y=39,sp=0xFB,p=32), stop)
            compare(bus, game, cpu, caller.registers)
            assert game.memory[0x1FE:0x200] == bytes([0xA6,0x59])
            counts['ending_nested_return' if result is not None else 'ending_nested_dependency_prefix'] += 1
            cases.append({'kind':'ending source bridge','mode':mode,'stop_pc':stop,'oracle_steps':steps,
                          'caller_return':0xFA88,'unrelated_stack_bytes_preserved':True})
        trial(f'ending-nested-{mode}', run)
    # The NMI cooperation prefix has a real caller-owned stack and mapping.
    for scene in range(9):
        def run(scene=scene):
            bus = context(rom); bus.ram[0x78] = scene
            bus.ram[0x300] = bus.ram[0x304] = 255
            game = game_from_bus(bus, rom)
            result = game.tick_nmi_cooperation(entry_banks=tuple(bus.banks), registers=Registers(p=32))
            assert result['status'] in ('boundary','dependency')
            stop = game._global.registers.pc
            cpu, steps = oracle(bus, 0xF862, Registers(p=32), stop)
            compare(bus, game, cpu, game._global.registers)
            counts['nmi_' + result['status']] += 1
            cases.append({'kind':'NMI cooperation','scene':scene,'status':result['status'],'stop_pc':stop,'oracle_steps':steps})
        trial(f'nmi-{scene}', run)
    for frame in (0, 255, 256, 65535):
        def run(frame=frame):
            bus=context(rom);bus.ram[0x5E:0x60]=frame.to_bytes(2,'little')
            game=game_from_bus(bus,rom);game.nmi_bookkeeping_effects()
            cpu,steps=oracle(bus,0xF88D,Registers(p=32),0xF8AF)
            assert bytes(bus.ram)==bytes(game.memory.ram) and bytes(bus.sram)==bytes(game.memory.sram) and bus.banks==game.memory.banks
            counts['nmi_bookkeeping_fields']+=1
        trial(f'bookkeeping-{frame}',run)
    # Shared-memory ownership and faction APIs perform actual original field writes.
    for city in (0,4,11,29):
        def run(city=city):
            bus=context(rom);bus.banks=[2,10,11,31];address=0x6000+city*32;bus.sram[address-0x6000]=0xFF
            bus.ram[0x38]=city;bus.sram[0xF03]=2;bus.sram[0xF8C]=0;bus.ram[0x39]=1
            game=game_from_bus(bus,rom);rules=game.city_ownership_rules()
            assert rules.memory is game.memory and game.faction_rules().memory is game.memory
            rules.commit_ai_capture(city,2,branch_zero=True)
            cpu,_=oracle(bus,0xA8FC,Registers(p=32),0xA90D)
            assert bytes(bus.sram)==bytes(game.memory.sram)
            counts['shared_ownership_fields']+=1
        trial(f'ownership-{city}',run)
    def core_score():
        prefix=ROOT/'analysis/phase6/runtime/unification-ending/victory-summary'
        game=GameEngine.from_snapshot(prefix,rom=rom,mapped=True,data_window_bank=2)
        score=game.faction_rules().victory_score()
        original=int.from_bytes(Path(str(prefix)+'-ram.bin').read_bytes()[0x435:0x438],'little')
        assert game.memory[0x435:0x438]==original.to_bytes(3,'little') and original==75
        counts['captured_core_score_parity']+=1
        guards.append({'kind':'captured original summary score','score':original,'result':score})
    trial('captured-core-score',core_score)
    game=game_from_bus(context(rom),rom)
    try: game.tick_global(entry_banks=(2,25,26,30))
    except ValueError: guards.append({'kind':'invalid fixed bank rejected'});counts['source_contract_guards']+=1
    else: failures.append({'case':'invalid fixed bank','message':'accepted'})
    result={'status':'passed' if not failures else 'failed','rom_sha256':ROM_SHA256,
            'case_count':sum(counts.values()),'counts':dict(counts),'failures':failures,
            'actual_ROM_CPU_comparison_count':sum(counts[k] for k in (
                'global_dependency','global_boundary','ending_nested_dependency_prefix',
                'ending_nested_return','nmi_dependency','nmi_bookkeeping_fields','shared_ownership_fields')),
            'actual_core_score_comparison_count':counts['captured_core_score_parity'],
            'source_contract_guard_count':counts['source_contract_guards'],
            'cases':cases,'guards':guards,'source_original_code_calls':0,
            'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in [
                'source/recovered/game_engine.py','source/recovered/battle_state_machine.py',
                'source/recovered/global_main_loop.py','source/recovered/city_ownership.py',
                'source/recovered/faction_lifecycle.py']},
            'limits':['Nested source calls share actual registers/SP and real caller return; no0200 sentinel is planted.',
                      'Global/NMI dependency prefixes are compared to their exact original PC; they do not complete the callback.',
                      'NMI bookkeeping compares only its declared RAM/mapper effects, excluding saved pops/RTI and time.',
                      'Captured score75 comes from the explicitly prepared30-city core scenario, not a natural campaign.']}
    out=ROOT/'analysis/phase6/source-integration.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'case_count':result['case_count'],'counts':result['counts'],'failures':failures},ensure_ascii=False,indent=2))
    if failures:sys.exit(1)

if __name__=='__main__':main()
