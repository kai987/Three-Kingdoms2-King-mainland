#!/usr/bin/env python3
"""Root-executed phase32 single-instance readable main/NMI/IRQ comparison.

The authoring agent must not run this script: Root owns all phase32 CPU/core
execution.  OriginalCPU is solely an oracle.  Each plan imports its initial
memory once and retains one source game/coordinator/register/session.  A
software cycle is an explicitly declared main/NMI/IRQ policy, not a Native
video frame, inferred interrupt timing, or replay of later Native RAM.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import ROM_SHA256
from source.recovered.nestopia_context import CapturedServiceMemory, NestopiaContext
from source.recovered.battle_nmi_services import NMIRegisters
from source.recovered.postbattle_early_integration import (
    PostbattleEarlyGameEngine, PostbattleEarlySceneCoordinator,
)
from source.recovered.postbattle_continuity_phase32 import PostbattleContinuity
from verify_postbattle_early_services import fixture as early_fixture

OUT = ROOT / 'analysis/phase32/source-continuity'
REGS = ('a', 'x', 'y', 'p', 'sp', 'pc')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def registers(r):
    return {k: getattr(r, k) for k in REGS}


class ComparisonMemory(CapturedServiceMemory):
    """Logical API order only; py65 does not expose hardware dummy cycles."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combined_IO = []

    def io_read(self, address):
        value = super().io_read(address)
        self.combined_IO.append(('read', address & 65535, value))
        return value

    def io_write(self, address, value):
        super().io_write(address, value)
        self.combined_IO.append(('write', address & 65535, value & 255))


def clone(m):
    other = ComparisonMemory(m.rom, bytes(m.ram), bytes(m.sram), tuple(m.banks),
        read_ports={k: list(v) for k, v in m.read_ports.items()},
        repeat_read_ports=set(m.repeat_read_ports),
        controller_buttons=m.controller_buttons)
    for attr in ('n163_ram', 'ppu_register_bytes'):
        getattr(other, attr)[:] = getattr(m, attr)
    for attr in ('n163_address', 'n163_autoincrement', 'controller_strobe',
                 'ppu_address', 'ppu_increment', 'ppu_latch', 'ppu_scroll_latch'):
        setattr(other, attr, getattr(m, attr))
    other.controller_index[:] = m.controller_index
    other.ppu_scroll[:] = m.ppu_scroll
    other.port_image.update(m.port_image)
    other.chr_selectors.update(m.chr_selectors)
    return other


class ECEEWithholdingCoordinator(PostbattleEarlySceneCoordinator):
    """Test-only dependency boundary, never an application service fallback."""
    ecee_mode = 'missing'
    real_ECEE_resolutions = 0

    def _resolve_call(self, call):
        if call.target == 0xECEE:
            if self.ecee_mode != 'actual':
                return dict(status='dependency' if self.ecee_mode == 'missing' else 'returned')
            self.real_ECEE_resolutions += 1
        return super()._resolve_call(call)


def fingerprint(m, r):
    return (bytes(m.ram), bytes(m.sram), registers(r), tuple(m.banks),
            tuple(m.combined_IO), bytes(m.n163_ram), m.n163_address,
            m.n163_autoincrement)


def equality(left, right, cpu, r):
    rd = [(i, a, b) for i, (a, b) in enumerate(zip(left.ram, right.ram)) if a != b]
    sd = [(0x6000+i, a, b) for i, (a, b) in enumerate(zip(left.sram, right.sram)) if a != b]
    assert not rd and not sd, dict(RAM=rd[:16], SRAM=sd[:16])
    assert registers(cpu) == registers(r), dict(original=registers(cpu), source=registers(r))
    assert left.banks == right.banks, 'Actual four PRG pages differ'
    assert left.combined_IO == right.combined_IO, dict(
        original_IO=left.combined_IO[-12:], source_IO=right.combined_IO[-12:])
    assert (left.n163_ram, left.n163_address, left.n163_autoincrement) == (
        right.n163_ram, right.n163_address, right.n163_autoincrement), 'N163 differs'


def oracle_to_boundary(left, right, cpu, r, result, limit):
    """Advance original instructions only, without inventing an interrupt."""
    boundary = result['status'] in ('returned', 'reset_boundary')
    for steps in range(limit+1):
        if steps and (cpu.pc, cpu.sp) == (r.pc, r.sp):
            if boundary or registers(cpu) == registers(r):
                equality(left, right, cpu, r)
                return steps
        if steps == limit:
            raise RuntimeError(f'OriginalCPU budget at {cpu.pc:04X}; source {r.pc:04X}')
        if cpu.pc < 0x8000:
            raise RuntimeError(f'OriginalCPU entered RAM at {cpu.pc:04X}')
        cpu.step()


def fixture_from_state(rom, state_path, initial, hardware):
    context = NestopiaContext.parse(state_path.read_bytes())
    m = ComparisonMemory(rom, context.ram, context.sram, context.prg_banks,
        read_ports={int(k, 0): v for k, v in hardware['read_ports'].items()},
        repeat_read_ports=[int(x, 0) for x in hardware['repeat_read_ports']],
        controller_buttons=tuple(hardware.get('controller_buttons', (0, 0))))
    m.n163_ram[:] = context.n163_ram
    m.n163_address = context.n163_address
    m.n163_autoincrement = context.n163_autoincrement
    if initial is None:
        initial = dict(context.registers)
    return m, initial, dict(saved_Native_registers=context.registers,
        used_registers=initial, changed_register_context=initial != context.registers,
        actual_PRG_banks=list(context.prg_banks), initial_import_count=1,
        subsequent_Native_snapshot_imports=0)


def fixture_from_context(rom, path, hardware, inputs):
    """A genuine E066 software capture; instantaneous devices are not implied."""
    meta_path = path/'context.json' if path.is_dir() else path
    x = json.loads(meta_path.read_text())
    initial = x.get('registers', x.get('actual_registers'))
    banks = x.get('physical_banks', x.get('actual_PRG_banks'))
    assert initial is not None and banks is not None
    assert initial['pc'] == 0xE066, 'Actual context must already be at E066'
    if path.is_dir():
        ram_path, sram_path = path/'input-ram.bin', path/'input-sram.bin'
    else:
        ram_path = path.with_name(path.stem+'-ram.bin')
        sram_path = path.with_name(path.stem+'-sram.bin')
    for p in (meta_path, ram_path, sram_path):
        inputs[str(p.resolve().relative_to(ROOT))] = sha(p)
    m = ComparisonMemory(rom, ram_path.read_bytes(), sram_path.read_bytes(), banks,
        read_ports={int(k, 0): v for k, v in hardware['read_ports'].items()},
        repeat_read_ports=[int(a, 0) for a in hardware['repeat_read_ports']],
        controller_buttons=tuple(hardware.get('controller_buttons', (0, 0))))
    n163 = hardware.get('N163_fixture', dict(bytes=[(11+37*i)&255 for i in range(128)],
                                          address=127, autoincrement=True))
    assert len(n163['bytes']) == 128
    m.n163_ram[:] = bytes(n163['bytes'])
    m.n163_address = n163['address']; m.n163_autoincrement = n163['autoincrement']
    return m, initial, dict(origin=x.get('origin', 'passive_software_E066_capture'),
        actual_capture_metadata=x, saved_Native_registers=initial,
        used_registers=initial, changed_register_context=False,
        actual_PRG_banks=list(banks), initial_import_count=1,
        subsequent_Native_snapshot_imports=0,
        N163_origin='explicit_shared_fixture_not_instantaneous_Native_capture',
        explicit_N163_fixture=n163)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--spec', type=Path, action='append', default=[])
    parser.add_argument('--cycles', type=int, default=None,
                        help='Shorten each declared plan; marks the row as a partial plan')
    parser.add_argument('--instruction-limit', type=int, default=2000000)
    parser.add_argument('--skip-regressions', action='store_true')
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    OUT.mkdir(parents=True, exist_ok=True)
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'source/recovered').glob('*.py'))}
    pins['scripts/verify_postbattle_continuity_phase32.py'] = sha(__file__)
    inputs, rows, failures, guards = {}, [], [], []
    hardware = dict(read_ports={'0x2002': 0, '0x4015': 0, '0x5800': 127},
                    repeat_read_ports=['0x2002', '0x4015', '0x5800'],
                    controller_buttons=[0, 0])
    specs = []
    for p in args.spec:
        x = json.loads(p.read_text()); inputs[str(p.resolve().relative_to(ROOT))] = sha(p)
        specs.extend(x if isinstance(x, list) else [x])
    if not specs:
        for route in ('natural13-continuous', 'controlled14-direct', 'natural-AI-mode2'):
            base = f'analysis/phase31/runtime/{route}/original-control/'
            specs.append(dict(case=route,
                initial_state=base+'initial.state', input_plan=base+'input-plan.json',
                initial_registers=dict(a=17, x=31, y=63, p=32, sp=255, pc=0xE066),
                origin='inherited_Native_memory_plus_declared_E066_register_and_interrupt_fixture',
                hardware=hardware))

    def run_parent(m, initial, tag, *, cycles=None, special=False, provenance=None):
        left, right = clone(m), clone(m)
        r = NMIRegisters(**initial); cpu = MPU(memory=left)
        for k, v in initial.items(): setattr(cpu, k, v)
        game = PostbattleEarlyGameEngine(right, rom=rom, mapped=True)
        if special: game._scene_coordinator = ECEEWithholdingCoordinator(game)
        driver = PostbattleContinuity(game, r); co = driver.coordinator
        identities = (game, co, right, r, driver.session)
        stages, instructions, interrupt_counts = [], 0, Counter()

        def event(kind, label):
            nonlocal instructions
            origin = (r.pc, r.sp)
            result = driver.advance(kind, label=label)
            if kind == 'nmi': cpu.nmi()
            elif kind == 'irq': cpu.irq()
            n = oracle_to_boundary(left, right, cpu, r, result, args.instruction_limit)
            instructions += n
            interrupt_counts[kind] += 1
            assert all(a is b for a, b in zip(identities,
                (driver.game, driver.coordinator, driver.memory, driver.registers, driver.session)))
            stages.append(dict(operation=kind, label=label, source_status=result['status'],
                original_CPU_instructions=n, origin_PC_SP=list(origin), registers=registers(r),
                pending_depth=len(driver.session.pending),
                battle=list(right.ram[0x500:0x502]), global_state=right[0x7A],
                queue=[right[0x300], right[0x304], right[0x310]],
                fade=list(right.ram[0x87:0x8B]), actual_PRG_banks=list(right.banks),
                combined_logical_IO_count=len(right.combined_IO), ownership=driver.ownership()))
            return result

        def explicit_IRQ_policy(result, label):
            """Validator-only declared arrivals; no software flag is assigned."""
            for attempt in range(12):
                if result['status'] in ('returned', 'reset_boundary'): return result
                if not driver.session.pending: return result
                phase = driver.session.pending[-1]
                if phase.kind != 'nmi': return result
                owner = driver.session._interrupt_owners[phase.token]
                pending = owner.pending
                if getattr(pending, 'category', None) != 'IRQ_software_flag': return result
                if right[0x62]:
                    child = event('irq', label+f'/declared-IRQ-{attempt}')
                    assert child['status'] == 'returned', child
                else:
                    result = event('resume', label+f'/same-NMI-resume-{attempt}')
            raise RuntimeError('Declared IRQ budget did not finish the original NMI')

        try:
            if special:
                result = event('nmi', 'stage2-missing-ECEE')
                assert result['status'] == 'dependency' and r.pc == 0xECEE
                phase = driver.session.pending[-1]
                owner = driver.session._interrupt_owners[phase.token]
                phase_identity, program = phase, owner._program
                relevant = [(call, who, who._program) for who, _ in co._owners.values()
                            for call in [getattr(who, 'pending', None)]
                            if getattr(call, 'target', None) == 0xECEE]
                assert len(relevant) == 1
                pending_call, inner_owner, inner_program = relevant[0]
                before = fingerprint(right, r)
                co.ecee_mode = 'fake'
                for repeat in range(2):
                    fake = driver.resume(label=f'fake-return-{repeat}')
                    assert fake['status'] == 'dependency'
                    assert fingerprint(right, r) == before
                    assert driver.session.pending[-1] is phase_identity and owner._program is program
                    assert inner_owner.pending is pending_call and inner_owner._program is inner_program
                    equality(left, right, cpu, r)
                co.ecee_mode = 'actual'
                result = explicit_IRQ_policy(event('resume', 'same-owner-real-Shared-ECEE'), 'stage2')
                assert result['status'] == 'returned' and co.real_ECEE_resolutions == 1
                assert sum(e.get('target') == 0xECEE for e in inner_owner.events) == 1
                assert right[0x501] == 3 and right[0x87] == 1
                first_E1 = right[0xE1]
                # Every NMI below is a new actual interrupt/callback; it is not
                # a continuation of a fictitiously suspended fade barrier.
                for fresh in range(28):
                    result = explicit_IRQ_policy(event('nmi', f'fresh-stage3-{fresh}'), 'stage3')
                    if result['status'] != 'returned': break
                    if right[0x7A] == 1: break
                assert result['status'] == 'returned' and right[0x7A] == 1
                assert right[0x87] & 128
                detail = dict(same_original_ServiceCall=True, same_outer_pending_phase=True,
                    same_inner_owner_and_generator=True, fake_returns_checked=2,
                    real_ECEE_resolutions=co.real_ECEE_resolutions,
                    fresh_stage3_interrupt_invocations=fresh+1,
                    E1_after_stage2=first_E1, E1_at_completion=right[0xE1],
                    EE07_actual_data_page_side_effect_not_globally_restored=True)
                guards.append('new_driver_same_NMI_ECEE_missing_fake_return_real_Shared_once')
            else:
                detail = None
                result = None
                for cycle, buttons in enumerate(cycles):
                    driver.set_buttons(*buttons); left.controller_buttons = tuple(buttons)
                    result = event('main', f'cycle-{cycle}/main')
                    if result['status'] != 'returned': break
                    result = explicit_IRQ_policy(event('nmi', f'cycle-{cycle}/NMI'), f'cycle-{cycle}')
                    if result['status'] != 'returned': break
                assert result is not None
            status = result['status']
            comparison = ('complete_explicit_software_event_plan' if status == 'returned' else
                          'reset_boundary' if status == 'reset_boundary' else 'strict_dependency_prefix')
            rows.append(dict(case=tag, comparison=comparison, source_status=status,
                source_single_instance=True, same_game_coordinator_bus_register_session=True,
                source_original_CPU_callbacks=0, source_IR_interpretation=False,
                new_gameplay_algorithm_claim=False, original_CPU_instructions=instructions,
                explicit_operation_counts=dict(interrupt_counts), stages=stages,
                identity_journal=driver.journal, initial_provenance=provenance,
                ECEE_regression=detail, all2K_8K_registers_PRG_combined_IO_N163_equal_each_event=True,
                final_registers=registers(r), final_state=driver.state(),
                dependency=stages[-1] if comparison == 'strict_dependency_prefix' else None))
        except Exception as exc:
            failures.append(dict(case=tag, error=str(exc), registers=registers(r),
                                 stages=stages, journal=driver.journal))
        print(json.dumps(dict(case=tag, failed=bool(failures and failures[-1]['case']==tag),
                              last_registers=registers(r))), flush=True)

    names = {'a':1, 'b':2, 'select':4, 'start':8, 'up':16, 'down':32, 'left':64, 'right':128}
    for spec in specs:
        plan = ROOT/spec['input_plan']
        inputs[str(plan.relative_to(ROOT))] = sha(plan)
        h = spec.get('hardware', hardware)
        if 'initial_context' in spec:
            assert 'initial_registers' not in spec, 'Do not override captured E066 registers'
            m, initial, provenance = fixture_from_context(rom, ROOT/spec['initial_context'], h, inputs)
        else:
            state = ROOT/spec['initial_state']; inputs[str(state.relative_to(ROOT))] = sha(state)
            m, initial, provenance = fixture_from_state(rom, state, spec.get('initial_registers'), h)
        assert initial['pc'] == 0xE066, 'Supply actual E066 entry or an explicitly declared E066 fixture'
        plan_rows = json.loads(plan.read_text()); cycles = []
        for item in plan_rows:
            byte = sum(names[x.lower()] for x in item['buttons'])
            cycles.extend([(byte, 0)] * item['frames'])
        if args.cycles is not None: cycles = cycles[:args.cycles]
        provenance.update(origin=spec['origin'], hardware_fixture=h,
            full_input_plan_cycles=sum(x['frames'] for x in plan_rows),
            executed_requested_cycles=len(cycles), partial_plan=args.cycles is not None,
            no_later_Native_memory_loaded=True, supplied_interrupt_timing='declared software event policy, not Native video timing')
        run_parent(m, initial, spec['case'], cycles=cycles, provenance=provenance)

    if not args.skip_regressions:
        m, initial = early_fixture(rom, stage=2, outcome=0)
        m[0x78]=3; m[0x7A]=4; m[0x7B]=0; m[0x500]=15
        initial.update(pc=0xE066, sp=255)
        run_parent(m, initial, 'controlled-same-session-ECEE-and-fresh-stage3', special=True,
            provenance=dict(origin='controlled_initial_numeric_and_register_software_fixture',
                            Native_case=False, E066_register_fixture=True))

    current = {p: sha(ROOT/p) for p in pins}
    assert current == pins, 'Source changed while Root executed the matrix'
    counts = Counter(x['comparison'] for x in rows)
    receipt = dict(schema='phase32-single-instance-source-continuity-v1',
        status='failed' if failures else 'passed', rom_sha256=ROM_SHA256,
        original_CPU_parent_case_count=len(rows), complete_event_plan_count=counts['complete_explicit_software_event_plan'],
        strict_prefix_count=counts['strict_dependency_prefix'], nonlocal_return_count=0,
        reset_boundary_count=counts['reset_boundary'], source_guard_case_count=len(guards),
        failed_count=len(failures), failures=failures, guards=guards, rows=rows,
        source_sha256=pins, artifact_sha256=inputs,
        comparison=dict(RAM_bytes=2048, SRAM_bytes=8192, AXYP_SP_PC=True,
                        four_PRG_banks=True, combined_logical_IO=True, common_N163=True),
        source_original_CPU_callbacks=0, source_IR_interpretation=False,
        Native_video_frames_claimed=0, new_production_gameplay_algorithm_count=0,
        limits=['This validator is authored without execution; only Root may execute it in phase32.',
                'Each long plan is one parentcase; nested main/NMI/IRQ/RTI operations are not extra cases.',
                'Default initial E066 registers and software interrupt policy are controlled fixtures, not saved Native registers/timing.',
                'A matching software plan does not reproduce original pixels/PCM or arbitrary hardware interleavings.',
                'Unknown real dependencies remain strict prefixes; no ready/result/RNG/PC patch is applied after initialization.',
                'All declared source and original events retain the same respective memory/context; no later Native RAM is imported.'])
    (OUT/'validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: receipt[k] for k in ('status','original_CPU_parent_case_count','complete_event_plan_count','strict_prefix_count','source_guard_case_count','failed_count')}))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
