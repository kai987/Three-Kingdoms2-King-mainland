#!/usr/bin/env python3
"""Original CPU differential for GameEngine's independent semantic AI APIs.

These fixtures compare declared game memory, not CPU registers or video frames.
The independent CPU-contract global bridge is checked by the earlier verifier.
"""
import argparse
import ast
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from source.recovered.game_engine import GameEngine, ROM_SHA256
from source.recovered.battle_state_machine import Registers
from source.recovered.tactical_effects import DECLARED_RAM_RANGES
from verify_phase6_integration import oracle, game_from_bus
from verify_tactical_ai_control import native_bus

STRATEGY_RAM = list(range(0x4D8, 0x4E0)) + list(range(0x500, 0x678)) + list(range(0x42C, 0x42F))
EFFECT_RAM = [a for lo, hi in DECLARED_RAM_RANGES for a in range(lo, hi) if not 0x20 <= a < 0x30]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    args = parser.parse_args(); rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    folder = ROOT / 'analysis/phase7/runtime/natural-turn'
    checkpoints = json.loads((folder / 'checkpoints.json').read_text())
    counts, cases, failures = Counter(), [], []
    native_cases = []

    def load(label='ai-request', banks=(6, 8, 9, 31)):
        ram = bytearray((folder / (label + '-ram.bin')).read_bytes())
        sram = bytearray((folder / (label + '-sram.bin')).read_bytes())
        ram[0x1FE:0x200] = bytes((255, 1))
        return native_bus(rom, ram, sram, banks=banks)

    def compare_data(bus, game, addresses):
        delta = [(hex(a), bus.peek(a), game.memory[a]) for a in addresses if bus.peek(a) != game.memory[a]]
        sdelta = [(hex(0x6000+i), a, b) for i, (a, b) in enumerate(zip(bus.sram, game.memory.sram)) if a != b]
        assert not delta and not sdelta, (delta[:12], sdelta[:12])

    def run(label, kind, bus, entry, call, stop=0x200, addresses=STRATEGY_RAM):
        try:
            game = game_from_bus(bus, rom)
            result = call(game)
            assert result['status'] in ('returned', 'dependency'), result
            cpu, instructions = oracle(bus, entry, Registers(a=0, x=0, y=0, sp=0xFD, p=32), stop, max_steps=1000000)
            compare_data(bus, game, addresses)
            assert game._tactical_control is None, 'semantic API must not construct an IR interpreter'
            for name, service in game.services.items():
                if name != 'global-main': assert service.fallback is None, name
            counts[kind] += 1
            cases.append(dict(case=label, kind=kind, original_instructions=instructions,
                              source_status=result['status'], full_sram_equal=True, compared_ram_count=len(addresses)))
        except Exception as exc:
            failures.append(dict(case=label, error=f'{type(exc).__name__}: {exc}'))

    for checkpoint in checkpoints:
        label = checkpoint['label']
        run(label, 'native_snapshot_semantic_CPU', load(label), 0xA02D,
            lambda game: game.tick_tactical_strategy())

    for strategy in range(8):
        for ap in (0, 24):
            bus = load(); actor = 1
            bus.sram[0xF8B] = 0; bus.sram[0xF94:0xF97] = bytes(3)
            bus.sram[0xFA1:0xFB5] = bytes([255]*20); bus.sram[0xFA1+actor] = strategy
            bus.ram[0x505] = ap
            run(f'strategy-{strategy}-AP{ap}', 'all8_shared_semantic_CPU', bus, 0xA02D,
                lambda game: game.tick_tactical_strategy())

    # Original C004 ID11 bypasses C01E's AP charge. Stop at actual D6CC call.
    bus = load(banks=(6, 12, 13, 31)); bus.sram[0xF8D] = 11; bus.sram[0xF8C] = 1
    bus.ram[0x505] = 24
    run('AI-ID11-prepare', 'shared_cast_CPU', bus, 0xC004,
        lambda game: game.tactical_effect_rules().prepare(), stop=0xC1C8, addresses=EFFECT_RAM)

    # Both actual cache timers, including the byte0->FF underflow behavior.
    for ttl in (0, 1, 5, 255):
        bus = load(); bus.ram[0x4D8:0x4E0] = bytes((1, 20, 17, ttl, 10, 24, 17, ttl))
        run(f'expiry-{ttl}', 'shared_expiry_CPU', bus, 0xCE20,
            lambda game: game.tactical_effect_rules().tick_expiry(), addresses=EFFECT_RAM)

    # Full BC2A begins with the original C91E accounting helper, then moves
    # the city roster. Vary current side independently of the unit's side.
    for side in (0, 128):
        for active_side in (0, 128):
            for total in (0, 1000, 65535):
                bus = load(banks=(6, 12, 13, 31)); slot = 10 if side else 0
                bus.ram[0x509] = slot; bus.ram[0x504] = active_side; bus.ram[0x50B] = 3
                bus.ram[0x628+slot] = side
                address = 0x51C if side else 0x51A
                bus.ram[address:address+2] = total.to_bytes(2, 'little')
                bus.ram[0x51F if side else 0x51E] = 0
                city = 32*3; bus.sram[city] = 7
                bus.sram[city+17:city+27] = bytes([255]*10)
                run(f'retreat-{side}-{active_side}-{total}', 'shared_full_retreat_commit_CPU',
                    bus, 0xBC2A, lambda game: game.commit_tactical_retreat(), addresses=STRATEGY_RAM)

    def native(label, case, before, after, call, addresses, extra=None):
        try:
            path=ROOT/'analysis/phase8/runtime'/case
            game=GameEngine.from_snapshot(path/before,rom=rom,mapped=True,data_window_bank=6)
            expected_ram=(path/(after+'-ram.bin')).read_bytes()
            expected_sram=(path/(after+'-sram.bin')).read_bytes()
            result=call(game)
            comparisons=[]
            for address in addresses:
                expected=expected_ram[address] if address<0x800 else expected_sram[address-0x6000]
                actual=game.memory[address]
                assert actual==expected,(hex(address),actual,expected)
                comparisons.append(dict(address=address,source=actual,native=expected,equal=True))
            if extra:extra(game,expected_ram)
            assert game._tactical_control is None
            native_cases.append(dict(case=label,before=f'{case}/{before}',after=f'{case}/{after}',
                                     comparisons=comparisons,source_status=result.get('status'),
                                     scope='Only listed effect fields; real intervening rendering/input/NMI is not executed by this source check.'))
        except Exception as exc:
            failures.append(dict(case=label,error=f'{type(exc).__name__}: {exc}'))

    caster=0x63C0+12*167; mover=0x63C0+12*131
    native('core-AI-deployment','ambush-chain','deploy-before','deploy-after',
           lambda g:g.tactical_effect_rules().prepare(),
           [0x505,0x543,0x544,*range(0x4D8,0x4E0),caster+8,caster+9])
    def request_and_decide(game):
        request=game.tactical_effect_rules().request_secondary_after_move()
        assert request['request']==1
        return game.tick_tactical_strategy()
    native('core-request-and-trigger','ambush-chain','trigger-before','trigger-after',request_and_decide,
           [0x501,0x505,0x6F8B,0x6F8C,0x6F8F,0x6F92,0x6F93,
            *range(0x4D8,0x4E0),*range(0x42C,0x42F),mover+8,mover+9,caster+6,caster+7])
    native('core-consume-XP','ambush-chain','trigger-after','trigger-consumed',
           lambda g:g.tactical_effect_rules().consume_secondary(),
           [0x501,0x505,*range(0x4D8,0x4E0),caster+6,caster+7,mover+6,mover+7])
    native('core-confirmation-slot-clear','ambush-chain','trap-message','cache-cleared',
           lambda g:g.tactical_effect_rules().clear_triggered_cache_after_confirmation(),
           [0x505,*range(0x4D8,0x4E0),caster+6,caster+7])
    def ordinary_fee(game,expected):
        # The frame-before animation flag is still busy. Dispatch verifies only
        # the effect body; the real original frame owns the animation completion.
        fee=game.tactical_effect_rules().data.player_costs[2]
        assert fee==4 and ((16-fee)&255)==expected[0x505]==12
    native('core-ordinary-effect-body','ordinary-cast','effect-before','effect-after',
           lambda g:g.tactical_effect_rules().dispatch(),
           [0x50,0x501,0x543,0x544,0x651,mover+6,mover+7],extra=ordinary_fee)

    # Check the source boundary directly; these are not invalid-ROM CPU cases.
    guard_count = 0
    for method in ('tactical_strategy_rules', 'tactical_effect_rules'):
        try: getattr(GameEngine(), method)()
        except (ValueError, RuntimeError): guard_count += 1
        else: failures.append(dict(case=method+'-missing-ROM', error='missing explicit ROM guard'))

    pure_modules = ('tactical_strategy_ai.py', 'tactical_effects.py')
    prohibited = ('tactical_ai_control', 'runtime_services', 'py65', 'trace_startup')
    for name in pure_modules:
        tree = ast.parse((ROOT / 'source/recovered' / name).read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom): imports.append(node.module or '')
        assert not any(p in value for p in prohibited for value in imports), (name, imports)

    result = dict(status='passed' if not failures else 'failed', rom_sha256=ROM_SHA256,
                  actual_ROM_CPU_comparison_count=sum(counts.values()), source_guard_count=guard_count,
                  counts=dict(counts), failures=failures, cases=cases,
                  native_core_field_comparison_count=len(native_cases),native_core_field_cases=native_cases,
                  source_original_code_calls=0, semantic_source_IR_interpretation=False,
                  contract='Full SRAM and method-declared game RAM; CPU registers, stack, mapper writes and video timing excluded.',
                  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                      'source/recovered/game_engine.py', 'source/recovered/tactical_strategy_ai.py',
                      'source/recovered/tactical_effects.py')})
    out = ROOT / 'analysis/phase8/source-integration.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','actual_ROM_CPU_comparison_count','source_guard_count','native_core_field_comparison_count','counts','failures')}, ensure_ascii=False))
    if failures: raise SystemExit(1)

if __name__ == '__main__': main()
