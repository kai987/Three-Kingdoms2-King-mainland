#!/usr/bin/env python3
"""Original CPU checks for the shared tactical/global bridge and natural fixture."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from source.recovered.game_engine import GameEngine, ROM_SHA256
from source.recovered.battle_state_machine import Registers
from verify_phase6_integration import oracle, compare, game_from_bus
from trace_startup import Bus

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    args = parser.parse_args(); rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    folder = ROOT / 'analysis/phase7/runtime/natural-turn'
    checkpoints = json.loads((folder / 'checkpoints.json').read_text())
    counts, cases, failures = Counter(), [], []

    def bus_for(label):
        bus = Bus(rom, 'zero')
        bus.ram[:] = (folder / (label + '-ram.bin')).read_bytes()
        bus.sram[:] = (folder / (label + '-sram.bin')).read_bytes()
        bus.banks = [6, 8, 9, 31]; bus.bank_initialized = [True]*4; bus.protect = 0x4C
        return bus

    def trial(label, function):
        try: function()
        except Exception as exc: failures.append({'case': label, 'error': f'{type(exc).__name__}: {exc}'})

    def no_rom_fallback(game):
        for name, service in game.services.items():
            if name == 'global-main':
                assert service.fallback.__self__ is game
                assert service.fallback.__func__ is GameEngine._global_source_call
                assert game._global_user_hooks is None
            else: assert service.fallback is None, name

    # Natural checkpoint data, replayed as explicit independent CPU calls.
    # These calls do not advance another native video frame.
    for checkpoint in checkpoints:
        label = checkpoint['label']
        def direct(label=label):
            bus = bus_for(label); bus.ram[0x1FE:0x200] = bytes((255, 1))
            game = game_from_bus(bus, rom); r = Registers(a=17, x=23, y=31, sp=0xFD, p=32)
            result = game.tick_tactical_ai(registers=r, max_instructions=1000000)
            assert result['status'] == 'returned', result
            cpu, steps = oracle(bus, 0xA02D, Registers(a=17,x=23,y=31,sp=0xFD,p=32), 0x200)
            compare(bus, game, cpu, r); no_rom_fallback(game)
            assert game._tactical_control.memory is game.memory
            assert game.tactical_rules().memory is game.memory
            assert game.tactical_bridge_rules().memory is game.memory
            counts['direct_tactical_checkpoint_CPU'] += 1
            cases.append({'kind': 'direct', 'checkpoint': label, 'status': result['status'], 'original_instructions': steps})
        trial('direct-' + label, direct)

        def global_call(label=label):
            bus = bus_for(label); bus.ram[0x7A] = 4
            game = game_from_bus(bus, rom); r = Registers(a=21, x=22, y=23, sp=0xD0, p=0x21)
            result = game.tick_global(entry_banks=tuple(bus.banks), registers=r, max_instructions=1000000)
            assert result['status'] == 'boundary' and r.pc == 0xE066, result
            cpu, steps = oracle(bus, 0xE066, Registers(a=21,x=22,y=23,sp=0xD0,p=0x21), 0xE066, max_steps=1000000)
            compare(bus, game, cpu, r); no_rom_fallback(game)
            assert game._tactical_control is not None
            counts['global4_checkpoint_CPU'] += 1
            cases.append({'kind': 'global4', 'checkpoint': label, 'status': result['status'], 'original_instructions': steps,
                          'real_nested_return': 0xE22C})
        trial('global4-' + label, global_call)

    for strategy in range(8):
        for ap in (0, 24):
            def strategy_call(strategy=strategy, ap=ap):
                bus = bus_for('ai-request'); actor = 1
                bus.sram[0xF8B] = 0; bus.sram[0xF94:0xF97] = bytes(3)
                bus.sram[0xFA1:0xFB5] = bytes([255]*20); bus.sram[0xFA1+actor] = strategy
                bus.ram[0x505] = ap; bus.ram[0x7A] = 4
                game = game_from_bus(bus, rom); r = Registers(a=21,x=22,y=23,sp=0xD0,p=32)
                result = game.tick_global(entry_banks=tuple(bus.banks), registers=r, max_instructions=1000000)
                assert result['status'] == 'boundary', result
                cpu, steps = oracle(bus,0xE066,Registers(a=21,x=22,y=23,sp=0xD0,p=32),0xE066,max_steps=1000000)
                compare(bus,game,cpu,r); no_rom_fallback(game)
                counts['global4_all8_controlled_strategies_CPU'] += 1
                cases.append({'kind':'controlled strategy', 'strategy':strategy,'ap':ap,'original_instructions':steps,
                              'proposal':game.tactical_bridge_rules().proposal()})
            trial(f'strategy-{strategy}-{ap}', strategy_call)

    # Reconstruct the independently recorded actual CPU call's explicit stack
    # preparation. It is not a resumption of the saved native PC.
    def recorded_call():
        evidence = json.loads((ROOT/'analysis/phase7/runtime/cpu-call/validation.json').read_text())
        bus = bus_for('ai-request'); entry = evidence['entry_registers']; sp = (entry['sp'] + 2) & 255
        bus.ram[0x100 + sp] = 0xE2; bus.ram[0x100 + ((sp-1)&255)] = 0x2B
        game = game_from_bus(bus, rom); r = Registers(**entry)
        class Caller: pass
        caller = Caller(); caller.registers = r
        result = game._global_source_call(caller,0xA000,0xE22C,'call')
        assert result['status'] == 'returned' and caller.registers is r
        target = ROOT/'analysis/phase7/runtime/cpu-call'
        assert bytes(game.memory.ram) == (target/'after-ram.bin').read_bytes()
        assert bytes(game.memory.sram) == (target/'after-sram.bin').read_bytes()
        assert vars(r) == evidence['return_registers']
        assert all(v['equal'] for v in evidence['native_field_comparisons'].values())
        no_rom_fallback(game)
        counts['recorded_actual_CPU_call_shared_stack'] += 1
        cases.append({'kind':'recorded actual CPU', 'original_instructions':evidence['instruction_count'],
                      'all_RAM_SRAM_and_registers_equal':True,'native_frame_comparison_field_count':8})
    trial('recorded-call', recorded_call)

    # A known consumed movement keeps the natural proposal's direction/cost,
    # while each suffix remains separate from preceding graphics requests.
    def natural_move():
        request = bus_for('ai-request'); game = game_from_bus(request,rom)
        game.tick_tactical_ai()
        proposal = game.tactical_bridge_rules().proposal()
        assert (proposal['actor_slot'],proposal['kind'],proposal['direction'],proposal['movement_cost']) == (1,'move','right',3)
        game.memory[0x509] = proposal['actor_slot']
        game.tactical_bridge_rules().commit_movement_coordinates()
        game.tactical_bridge_rules().apply_movement_cost()
        after = next(c for c in checkpoints if c['label'] == 'first-ap-charge')
        unit = next(u for u in after['units'] if u['slot'] == 1)
        assert (game.memory[0x601],game.memory[0x615],game.memory[0x505]) == (unit['x'],unit['y'],after['active_action_points_0505']) == (18,17,21)
        counts['native_core_movement_fields_semantic_suffix'] += 1
        cases.append({'kind':'core movement fields', 'fields':['slot1.x','slot1.y','AP'],
                      'scope':'Only declared semantic suffix fields, not the intervening video frames/graphics.'})
    trial('natural-move-fields',natural_move)

    result = {'status':'passed' if not failures else 'failed','rom_sha256':ROM_SHA256,
              'case_count':sum(counts.values()),'counts':dict(counts),'failures':failures,'cases':cases,
              'actual_ROM_CPU_comparison_count':sum(counts.values())-counts['native_core_movement_fields_semantic_suffix'],
              'native_core_field_comparison_count':counts['native_core_movement_fields_semantic_suffix'],
              'source_original_code_calls':0,
              'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                  'source/recovered/game_engine.py','source/recovered/tactical_ai_control.py',
                  'source/recovered/tactical_decisions.py','source/recovered/tactical_exchange.py')},
              'limits':['Natural checkpoint data is reused in synchronous CPU fixtures, not replayed as more complete-core frames.',
                        'The bridge executes source IR and fixed services only; original ROM CPU execution exists solely in verification.',
                        'Movement field comparison excludes graphics requests, real NMI/IRQ timing and animation.']}
    (ROOT/'analysis/phase7/source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','case_count','counts','actual_ROM_CPU_comparison_count','failures')},ensure_ascii=False))
    if failures:sys.exit(1)

if __name__ == '__main__':main()
