#!/usr/bin/env python3
"""Split iNES bytes and conservatively follow fixed-bank 6502 control flow."""
import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def byte_source(path, data, offset):
    lines = ["; Exact bytes, not recovered original assembly source.",
             f"; Original file offset ${offset:06X}, length ${len(data):X}"]
    for i in range(0, len(data), 16):
        lines.append(".byte " + ", ".join(f"${v:02X}" for v in data[i:i+16])
                     + f" ; file ${offset+i:06X}")
    path.write_text("\n".join(lines)+"\n")


def analyze(rom):
    data = rom.read_bytes()
    if data[:4] != b"NES\x1a" or (data[7] & 12) == 8:
        raise ValueError("Expected legacy iNES input")
    prg_size, chr_size = data[4]*16384, data[5]*8192
    start = 16 + (512 if data[6] & 4 else 0)
    expected = start + prg_size + chr_size
    if len(data) != expected or prg_size != 262144 or chr_size != 262144:
        raise ValueError("Unexpected extent or cartridge size for this investigation")
    dest, src = ROOT/'analysis/rom', ROOT/'source/byte-source'
    (dest/'prg-banks').mkdir(parents=True, exist_ok=True)
    src.mkdir(parents=True, exist_ok=True)
    chunks = [('header.asm', data[:16], 0)]
    if start > 16:
        chunks.append(('trainer.asm', data[16:start], 16))
    (dest/'header.bin').write_bytes(data[:16])
    prg, chr_data = data[start:start+prg_size], data[start+prg_size:]
    (dest/'prg.bin').write_bytes(prg)
    (dest/'chr.bin').write_bytes(chr_data)
    banks = []
    for i in range(prg_size//8192):
        raw, offset = prg[i*8192:(i+1)*8192], start+i*8192
        (dest/'prg-banks'/f'bank-{i:02d}.bin').write_bytes(raw)
        counts = Counter(raw)
        entropy = -sum((n/len(raw))*math.log2(n/len(raw)) for n in counts.values())
        banks.append({'bank': i, 'file_offset': offset, 'length': len(raw),
                      'sha256': digest(raw), 'entropy_bits_per_byte': round(entropy, 5),
                      'ff_bytes': counts[255], 'zero_bytes': counts[0],
                      'mapping': '$E000-$FFFF fixed' if i == 31 else
                      'switchable: $8000/$A000/$C000; requires mapper state'})
        chunks.append((f'prg-{i:02d}.asm', raw, offset))
    for i in range(chr_size//4096):
        chunks.append((f'chr-{i:02d}.asm', chr_data[i*4096:(i+1)*4096], start+prg_size+i*4096))
    source_order = []
    for name, raw, offset in chunks:
        byte_source(src/name, raw, offset)
        source_order.append({'file': name, 'offset': offset, 'length': len(raw), 'sha256': digest(raw)})
    (src/'order.json').write_text(json.dumps({'rom_sha256': digest(data), 'rom_length': len(data),
                                             'chunks': source_order}, indent=2)+'\n')
    vectors = {name: {'cpu_address': int.from_bytes(prg[-6+i*2:-4+i*2] if i<2 else prg[-2:], 'little'),
                       'vector_file_offset': start+prg_size-6+i*2}
               for i, name in enumerate(['NMI', 'RESET', 'IRQ'])}
    for v in vectors.values():
        v['handler_file_offset'] = start+31*8192+v['cpu_address']-0xe000
    manifest = {'source_path': str(rom.resolve()), 'date': '2026-10-13',
                'rom_sha256': digest(data), 'rom_length': len(data), 'header_hex': data[:16].hex(),
                'format': 'iNES 1.0', 'mapper': (data[6]>>4)|(data[7]&0xf0),
                'battery_flag': bool(data[6]&2), 'trainer_flag': bool(data[6]&4),
                'header_mirroring_bit': data[6]&1,
                'prg': {'offset': start, 'length': prg_size, 'sha256': digest(prg), 'banks': banks},
                'chr': {'offset': start+prg_size, 'length': chr_size, 'sha256': digest(chr_data)},
                'vectors': vectors,
                'limitations': ['Header flags do not establish exact physical board or RAM size.',
                                'Bank aliases in this investigation use selector & 31 for 256 KiB PRG.',
                                'The byte-source is an exact byte representation, not original game source.']}
    (dest/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    follow_fixed_bank(prg[-8192:], start+31*8192, vectors)
    print(json.dumps({'sha256': digest(data), 'prg_banks': len(banks), 'chr_4k_groups':64, 'vectors': vectors}))


def follow_fixed_bank(bank, file_base, vectors):
    from py65.devices.mpu6502 import MPU
    from py65.disassembler import Disassembler
    memory = [0]*65536
    memory[0xe000:] = bank
    cpu, base = MPU(memory=memory), 0xe000
    decoder = Disassembler(cpu)
    # Table ends at $E099; $E09A is the first handler's JSR instruction.
    # AND #$1F constrains the index but does not prove 32 valid records.
    state_table = [int.from_bytes(bank[0x7c+2*i:0x7e+2*i], 'little') for i in range(15)]
    seeds = {v['cpu_address'] for v in vectors.values()}
    # Only the 15 confirmed table entries seed computed dispatch targets.
    seeds.update(x for x in state_table if base <= x < 0xfffa)
    pending = deque(sorted(seeds))
    found, occupied, edges, unresolved, conflicts, inline_data = {}, {}, [], [], [], []
    branches = {'BCC','BCS','BEQ','BMI','BNE','BPL','BVC','BVS'}
    while pending:
        pc = pending.popleft()
        while base <= pc < 0xfffa and pc not in found:
            if pc in occupied:
                conflicts.append({'cpu_address': pc, 'overlaps_start': occupied[pc]})
                break
            n, text = decoder.instruction_at(pc)
            op, mode = cpu.disassemble[memory[pc]]
            if op == '???' or pc+n > 0xfffa:
                unresolved.append({'cpu_address': pc, 'reason': 'unsupported opcode or vector boundary'})
                break
            raw = bytes(memory[pc:pc+n])
            if any(a in occupied for a in range(pc,pc+n)):
                conflicts.append({'cpu_address': pc, 'reason': 'instruction extent overlaps prior decode'})
                break
            found[pc] = {'cpu_address': pc, 'rom_offset': file_base+pc-base,
                         'bytes_hex': raw.hex(), 'instruction': text, 'size': n,
                         'evidence': 'static reachable candidate'}
            for a in range(pc,pc+n):
                occupied[a] = pc
            target = None
            if op in branches:
                target = (pc+2+int.from_bytes(raw[1:2], 'little', signed=True)) & 65535
            elif op in {'JSR','JMP'} and mode == 'abs':
                target = int.from_bytes(raw[1:3], 'little')
            if target is not None:
                edges.append({'from': pc, 'to': target, 'kind': op,
                              'resolved_fixed_bank': base <= target < 0xfffa})
                if base <= target < 0xfffa:
                    pending.append(target)
                else:
                    unresolved.append({'cpu_address': pc, 'target': target,
                                       'reason': 'switchable bank or RAM requires mapper/runtime state'})
            if op == 'JSR' and target == 0xee07:
                # This helper edits the return stack and consumes an inline word.
                # The observed .word is data even though normal JSR fallthrough decodes it.
                if pc+5 <= 0xfffa:
                    inline_raw = bytes(memory[pc+3:pc+5])
                    far_target = int.from_bytes(inline_raw, 'little')
                    previous = found.get(pc-2)
                    selector = None
                    if previous and previous['bytes_hex'].startswith('a0') and previous['size'] == 2:
                        selector = memory[pc-1]
                    inline_data.append({'cpu_address':pc+3, 'rom_offset':file_base+pc+3-base,
                                        'bytes_hex':inline_raw.hex(), 'kind':'far-call inline address',
                                        'target':far_target, 'raw_bank_selector':selector})
                    unresolved.append({'cpu_address':pc, 'target':far_target,
                                       'reason':'far-call target requires helper bank mapping',
                                       'raw_bank_selector':selector})
                    pc += 5
                    continue
                break
            if op == 'JSR' and target == 0xeade:
                unresolved.append({'cpu_address':pc, 'table_cpu_address':pc+3,
                                   'reason':'inline indexed jump table; size and cases require caller context'})
                break
            if op == 'JMP':
                if mode == 'ind':
                    unresolved.append({'cpu_address': pc, 'pointer': int.from_bytes(raw[1:3], 'little'),
                                       'reason': 'computed jump; explicit state table supplied separately'})
                break
            if op in {'RTS','RTI','BRK'}:
                break
            pc += n
    out = ROOT/'analysis/disassembly'
    out.mkdir(parents=True, exist_ok=True)
    report = {'bank':31, 'cpu_base':base, 'file_base':file_base,
              'seed_addresses':sorted(seeds), 'state_pointer_candidates':state_table,
              'instruction_count':len(found), 'candidate_code_bytes':len(occupied),
              'bank_bytes':len(bank), 'instructions':[found[x] for x in sorted(found)],
              'edges':edges, 'unresolved':unresolved, 'conflicts':conflicts,
              'inline_data':inline_data,
              'limitation':'Reachability is static and may include data reached by a false seed. No target execution is claimed.'}
    (out/'fixed-bank.json').write_text(json.dumps(report, indent=2)+'\n')
    lines = ['; Conservative fixed-bank 31 control-flow listing; candidates, not original source.',
             '; Columns: CPU address | original ROM offset | bytes | decoded instruction']
    for pc in sorted(found):
        v=found[pc]
        lines.append(f"${pc:04X} | ${v['rom_offset']:06X} | {v['bytes_hex'].upper():<6} | {v['instruction']}")
    lines.extend(['', '; Inline far-call words omitted from instruction flow:'])
    for v in inline_data:
        lines.append(f"${v['cpu_address']:04X} | ${v['rom_offset']:06X} | {v['bytes_hex'].upper():<6} | .word ${v['target']:04X} ; bank selector {v['raw_bank_selector']}")
    (out/'fixed-bank.asm').write_text('\n'.join(lines)+'\n')
    names={0xe000:'reset_dispatch',0xf800:'nmi',0xfb2d:'irq',0xf25f:'select_data_bank',
           0xf2af:'record32_address',0xf2d7:'record12_address'}
    labels = seeds | set(names)
    (ROOT/'analysis/rea/fixed-bank-seeds.tsv').write_text(
        '\n'.join(f"0x{a:x}\tfunction\t{names.get(a, 'state_or_entry_'+format(a,'04x'))}"
                  for a in sorted(labels) if base <= a < 0xfffa)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('rom', type=Path)
    analyze(parser.parse_args().rom)
