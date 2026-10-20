#!/usr/bin/env python3
"""Original6502 oracle for directly recovered auxiliary field services.

CPU execution is validator-only. Source uses independently recovered fixed
services, never original helper callbacks. Exact comparisons include all2048
RAM, all8192SRAM, AXYP/SP/PC, banks and ordered hardware reads/writes.
"""
from pathlib import Path
from collections import Counter
from importlib.metadata import version
import argparse, hashlib, json, random, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.record_fields import RecordFieldServices, CityAuxiliaryFields, adverse_event_threshold, city_address, ROM_SHA256
from source.recovered.global_ui_controller import UIRegisters
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory

OUT = ROOT / 'analysis/phase15/fields'
PARENT = ROOT / 'analysis/phase11/runtime/cold-battle/picked-ruler'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class TrackedMemory(ServiceMemory):
    def __init__(self, *args, **kwargs):
        self.observed_pc = None; self.field_reads = Counter(); self.field_writes = Counter()
        super().__init__(*args, **kwargs)
    def field(self, address):
        if address == 0x6F06: return 'monthly_event_latch'
        if 0x6000 <= address < 0x63C0 and address % 32 in (1, 27, 28, 29, 30, 31):
            return f'city+{address % 32}'
    def __getitem__(self, address):
        value = super().__getitem__(address)
        if isinstance(address, int) and self.observed_pc is not None and self.field(address):
            self.field_reads[(self.observed_pc, address, self.field(address))] += 1
        return value
    def __setitem__(self, address, value):
        if isinstance(address, int) and self.observed_pc is not None and self.field(address):
            self.field_writes[(self.observed_pc, address, self.field(address))] += 1
        super().__setitem__(address, value)

def memory(rom, pair, prep):
    m = TrackedMemory(rom, Path(str(PARENT) + '-ram.bin').read_bytes(), Path(str(PARENT) + '-sram.bin').read_bytes(), (16, pair, pair + 1, 31))
    m[0x1FC:0x200] = bytes([0x77, 0x45, 0x87, 0xE1])
    for address, value in prep.items(): m[address] = value
    m.io_writes = []; m.io_reads = []
    return m

def verify(rom, quick=False):
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    rows, failures, guards = [], [], []
    executed, reads, writes, counts = Counter(), Counter(), Counter(), Counter()
    rng = random.Random(0x15F1E1D)

    def compare(entry, pair=25, prep=None, kind='complete', tag='', services=True, flags=0x20):
        prep = prep or {}; original = memory(rom, pair, prep); recovered = memory(rom, pair, prep)
        registers = UIRegisters(a=137, x=53, y=71, p=flags, sp=253, pc=entry)
        initial = vars(registers).copy(); cpu = MPU(memory=original)
        for key, value in initial.items(): setattr(cpu, key, value)
        helper = SceneSharedServices(recovered, rom) if services else None
        source = RecordFieldServices(recovered, rom, helper)
        try:
            if kind == 'assignment_gate': result = source.assignment_word_gate_prefix(registers)
            elif kind == 'calendar': result = source.calendar_turn_scan_prefix(registers)
            elif kind == 'recruitment_append': result = source.recruitment_append_prefix(registers)
            else: result = source.run_entry(entry, registers=registers)
            for steps in range(100000):
                if steps and cpu.pc == registers.pc and cpu.sp == registers.sp: break
                bank = original.banks[(cpu.pc - 0x8000) // 8192] if cpu.pc >= 0x8000 else None
                if bank is not None: executed[(bank, cpu.pc, 16 + bank * 8192 + (cpu.pc & 8191))] += 1
                original.observed_pc = cpu.pc; cpu.step()
            else: raise RuntimeError(f'Original budget at{cpu.pc:04X}')
            original.observed_pc = None
            ram = [(i, original.ram[i], recovered.ram[i]) for i in range(2048) if original.ram[i] != recovered.ram[i]]
            sram = [(i, original.sram[i], recovered.sram[i]) for i in range(8192) if original.sram[i] != recovered.sram[i]]
            reg = [(k, getattr(cpu, k), getattr(registers, k)) for k in ('a', 'x', 'y', 'p', 'sp', 'pc') if getattr(cpu, k) != getattr(registers, k)]
            assert not ram and not sram and not reg, dict(RAM=ram[:8], SRAM=sram[:8], registers=reg)
            assert original.io_reads == recovered.io_reads and original.io_writes == recovered.io_writes and original.banks == recovered.banks
            comparison = 'complete_return' if result['status'] == 'returned' else 'strict_prefix'
            counts[f'{kind}/{comparison}'] += 1
            initial_memory = memory(rom, pair, prep)
            changed = [dict(address=0x6000 + i, old=a, new=b) for i, (a, b) in enumerate(zip(initial_memory.sram, recovered.sram)) if a != b]
            rows.append(dict(entry=entry, physical_pair=[pair, pair + 1], tag=tag, comparison=comparison,
                             completion_kind='actual_caller_RTS' if comparison == 'complete_return' else 'bounded_field_prefix' if kind != 'complete' else 'missing_fixed_service',
                             source_status=result['status'], prepared_bytes=prep, input_registers=initial,
                             final_registers=vars(registers).copy(), original_instructions=steps,
                             all_RAM_byte_count=2048, all_SRAM_byte_count=8192,
                             ordered_IO_reads=len(original.io_reads), ordered_IO_writes=len(original.io_writes), final_banks=list(original.banks),
                             changed_SRAM_bytes=changed, accepted=result.get('accepted'), month_advanced=result.get('month_advanced'),
                             candidate_thresholds=list(recovered[0x42C:0x44A]) if entry == 0xAB25 else None,
                             original_CPU_helper_callbacks=0))
            reads.update(original.field_reads); writes.update(original.field_writes)
        except Exception as exc:
            failures.append(dict(entry=entry, tag=tag, preparation=prep, error=str(exc), source_pc=registers.pc))
            if len(failures) < 6: print(json.dumps(failures[-1], ensure_ascii=False), flush=True)

    # Actual readiness inputs are varied, never forced by a fabricated callback.
    for month in range(12):
        for latch in (0, 1, 255):
            for text0, text4 in ((255, 255), (0, 255), (255, 0)):
                for jobs in (0, 4):
                    for p in ((0x20,) if quick else (0x20, 0xE5)):
                        compare(0xA2BC, prep={0x6F01:month, 0x6F06:latch, 0x300:text0, 0x304:text4, 0x7E:jobs, 0x401:11, 0x402:37}, flags=p,
                                tag=f'month{month}/latch{latch}/text{text0},{text4}/jobs{jobs}')
    # Independent direct original record overlap: exhaustive byte1, five gold
    # low-byte values. High gold byte and all tail sentinels are preserved.
    for byte1 in range(0, 256, 16 if quick else 1):
        for gold_low in (0, 1, 2, 3, 255):
            city = byte1 % 30; address = city_address(city)
            prep = {0x20:address & 255, 0x21:address >> 8, address+1:byte1, address+2:gold_low, address+3:173}
            compare(0xBD95, pair=10, prep=prep, kind='assignment_gate', tag=f'city{city}/byte1{byte1}/goldLow{gold_low}', flags=0xE5 if byte1 % 2 else 0x20)
            view = CityAuxiliaryFields.from_memory(memory(rom, 10, prep), city)
            assert view.assignment_gate_at_least_300 == (view.assignment_gate_word_01_02 >= 300)
    # Calendar prefix confirms clear only on turn-index wrap; initialFF is not
    # a month advance, and year increment is byte-sized.
    for year in (0, 89, 255):
        for month in range(12):
            for slot in (0, 5, 6, 255):
                compare(0xA041, prep={0x6F00:year, 0x6F01:month, 0x6F04:slot, 0x6F06:173}, kind='calendar', tag=f'year{year}/month{month}/slot{slot}', flags=0xE5)
    # Thirty original records, varied complete scanner calls. Each auxiliary
    # tail byte is a sentinel: preservation is asserted by all8KiB comparison.
    thresholds = (0, 19, 20, 29, 30, 39, 40, 49, 50, 100, 255)
    for i in range(16 if quick else 256):
        prep = {0x6F00:89 if i % 7 == 0 else 90, 0x6F01:i % 12, 0x402:i % 256, 0x403:71, 0x401:15, 0x50:(i * 17) & 255}
        for city in range(30):
            address = city_address(city)
            prep[address] = (7, 15, 0, 2, 128, 135)[(i + city) % 6]
            prep[address + 11] = thresholds[(i + city) % len(thresholds)]
            prep[address + 27] = (0, 0, 1, 2, 6, 255)[(i * 3 + city) % 6]
            for off in (1, 28, 29, 30, 31): prep[address + off] = rng.randrange(256)
        compare(0xAB25, prep=prep, tag=f'candidate-scanner-fixture{i}', flags=0xE5 if i % 2 else 0x20)
    # Missing F2AF is a strict original JSR prefix, not a completed scan.
    compare(0xAB25, prep={0x6F00:90}, services=False, tag='strict-missing-F2AF')
    # Every10-slot occupancy mask. Packed capacity0..9 are normal-domain
    # helper inputs; full10 and hole patterns are explicit boundary fixtures.
    # Stop before the routine mutates officer status/loyalty, not a fake RTS.
    for mask in range(0, 1024, 32 if quick else 1):
        city = mask % 30; address = city_address(city)
        prep = {0x402:city, 0x472:205, address+27:6}
        for slot in range(10): prep[address+17+slot] = 40+slot if mask & (1<<slot) else 255
        for off in (1, 28, 29, 30, 31): prep[address+off] = (off * 13 + mask) & 255
        compare(0xACF0, pair=27, prep=prep, kind='recruitment_append', tag=f'roster-occupancy-mask{mask:03X}')
        view = CityAuxiliaryFields.from_memory(memory(rom, 27, prep), city)
        assert view.recruitment_append_offset == 17 + mask.bit_count()
    # Source-only contracts and rejection guards never count as CPU cases.
    def reject(name, fn):
        try: fn()
        except (ValueError, RuntimeError): guards.append(dict(name=name, status='passed')); return
        raise AssertionError(f'Guard failed:{name}')
    reject('city-ID-outside-proven-records', lambda: city_address(30))
    reject('wrong-record-length', lambda: CityAuxiliaryFields(bytes(31)))
    reject('governance-outside-original-byte', lambda: adverse_event_threshold(256))
    reject('actual-registers-required', lambda: RecordFieldServices(memory(rom, 25, {}), rom).run_entry())
    reject('wrong-physical-caller-pair', lambda: RecordFieldServices(memory(rom, 10, {}), rom).run_entry(registers=UIRegisters()))
    reject('invalid-city-pointer-gate', lambda: RecordFieldServices(memory(rom, 10, {0x20:1, 0x21:96}), rom).assignment_word_gate_prefix(UIRegisters()))
    for status in (None, 'waiting', 'error', 'blocked'):
        m = memory(rom, 25, {0x6F00:90})
        def counterfeit(call, status=status):
            call.registers.pc=call.return_pc; call.registers.sp=call.expected_sp
            return None if status is None else {'status':status}
        result = RecordFieldServices(m, rom, counterfeit).run_entry(0xAB25, registers=UIRegisters())
        assert result['status'] == 'dependency' and result['pending'] is not None
        guards.append(dict(name=f'no-fake-return-{status}', status='passed'))
    OUT.mkdir(parents=True, exist_ok=True)
    def accesses(counter):
        return [dict(cpu=pc, address=address, field=field, count=count) for (pc, address, field), count in sorted(counter.items())]
    instructions=[]
    for (bank, pc, off), count in sorted(executed.items()):
        from inspect_game_data import instruction
        size, text = instruction(rom, off, pc)
        instructions.append(dict(physical_bank=bank, cpu=pc, rom_offset=off, raw_hex=rom[off:off+size].hex(' ').upper(), assembly=text, count=count))
    (OUT/'executed-instructions.json').write_text(json.dumps(instructions, ensure_ascii=False, indent=2)+'\n')
    (OUT/'field-accesses.json').write_text(json.dumps(dict(reads=accesses(reads), writes=accesses(writes)), indent=2)+'\n')
    complete=sum(row['comparison']=='complete_return' for row in rows); prefix=len(rows)-complete
    result=dict(schema='phase15-record-fields-original-CPU-v1', status='passed' if not failures else 'failed', ROM_sha256=ROM_SHA256,
                rom_cpu_case_count=len(rows), source_guard_case_count=len(guards), total_complete_return_CPU_cases=complete,
                total_strict_prefix_CPU_cases=prefix, case_count=len(rows)+len(guards), failed_count=len(failures),
                group_case_counts=dict(counts), rows=rows, guards=guards, failures=failures,
                scope=dict(RAM_addresses='0000..07FF including inactive stack', RAM_byte_count=2048, SRAM_byte_count=8192,
                           registers=['A','X','Y','P','SP','PC'], banks=True, ordered_IO_reads=True, ordered_IO_writes=True,
                           native_internal_CPU_trace=False, original_CPU_helper_callbacks=0, source_original_CPU_callbacks=0, source_control_IR_callbacks=0),
                fixture_domains=dict(complete_procedures='Monthly gate: month0..11 and latch0/1 normal inputs, latch255 raw-byte boundary plus explicit text/PPU busy inputs. Scanner: ordinary fields mixed with raw-byte boundary counters255/governance255/high owner bits.',
                                     recruitment_append='All1024 occupancy masks: packed count0..9 normal helper inputs, full10/hole patterns are boundary invocations rather than normal UI acceptance.',
                                     assignment_gate='Byte1 exhaustive0..255, gold_low0/1/2/3/255; no assertion that unresolved byte1 values have natural producers.',
                                     calendar='Month0..11, year0/89/255, slot0/5/6/initialFF; no downstream diplomacy/selection effects.'),
                original_dynamically_executed_positions=len(executed), source_path='source/recovered/record_fields.py',
                independent_oracle='py65 MPU6502 validator-only', independent_oracle_version=version('py65'),
                source_sha256=sha(ROOT/'source/recovered/record_fields.py'), validator_path='scripts/verify_record_fields.py', validator_sha256=sha(__file__),
                source_and_validator_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'source/recovered/record_fields.py',ROOT/'source/recovered/global_ui_controller.py',ROOT/'source/recovered/scene_shared_services.py',ROOT/'source/recovered/controller_helpers.py',ROOT/'source/recovered/battle_nmi_services.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'source/recovered/service_memory.py',Path(__file__))},
                parent_snapshot_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(str(PARENT)+'-ram.bin'),Path(str(PARENT)+'-sram.bin'))})
    (OUT/'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','rom_cpu_case_count','source_guard_case_count','total_complete_return_CPU_cases','total_strict_prefix_CPU_cases','failed_count')}, ensure_ascii=False), flush=True)
    if failures: raise SystemExit(1)

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('rom',type=Path);parser.add_argument('--quick',action='store_true');args=parser.parse_args()
    verify(args.rom.read_bytes(), args.quick)
