#!/usr/bin/env python3
"""Export bounded, manually identified battle routine bytes and annotations.

The source ROM is read only. Listings explicitly mark known inline pointers
and data tables; this script does not classify an entire bank as executable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_game_data import instruction
from source.recovered.battle import ROM_SHA256

FUNCTIONS = [
    ("strategy_dispatch", 12, 0xB02B, 0xB062),
    ("damage_B070", 12, 0xB070, 0xB0DD),
    ("damage_B0EB", 12, 0xB0EB, 0xB155),
    ("damage_B188", 12, 0xB188, 0xB1D5),
    ("damage_B1E3", 12, 0xB1E3, 0xB243),
    ("damage_B4C6", 12, 0xB4C6, 0xB50C),
    ("damage_B55C", 12, 0xB55C, 0xB5A6),
    ("health_loss", 12, 0xB5D8, 0xB643),
    ("troop_loss", 12, 0xB68B, 0xB6F0),
    ("conversion_gate", 12, 0xB72B, 0xB7BE),
    ("strategy_gate", 12, 0xB7BE, 0xB860),
    ("grid_distance", 12, 0xB860, 0xB8A1),
    ("experience_from_accumulated_loss", 15, 0xD7FB, 0xD8B0),
    ("duel_parameter_seed", 23, 0xB230, 0xB2E0),
    ("duel_strike_sample", 23, 0xBA15, 0xBA6D),
    ("duel_health_strike", 23, 0xBB5B, 0xBB93),
    ("duel_strike_effect", 23, 0xB8D3, 0xB9A5),
    ("duel_attack_parameters", 15, 0xC991, 0xCA3F),
]
DATA_SPANS = {
    (12, 0xB042): (32, "word", "Sixteen strategy effect pointers, not instructions"),
    (12, 0xB7BA): (4, "byte", "Conversion base probabilities 60,30,10,5; normal threshold branches use first three"),
    (12, 0xB85A): (6, "byte", "Distance correction bytes: 15,10,5,0,-5,-10"),
    (15, 0xD85B): (14, "word", "Seven experience thresholds, not instructions"),
    (23, 0xB2C0): (32, "byte", "Equipment correction lookup: 24+8 entries"),
    (15, 0xCA1F): (32, "byte", "Duel weapon attack bonuses followed by eight armor defense modifiers"),
}


def offset(bank, address):
    base = 0xA000 if bank in (12, 23) else 0xC000
    return 16 + bank * 8192 + address - base


def analyze(rom, out):
    raw = rom.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ROM_SHA256
    out.mkdir(parents=True, exist_ok=True)
    (out / "routines").mkdir(exist_ok=True)
    reports = []
    for name, bank, start, end in FUNCTIONS:
        begin, finish = offset(bank, start), offset(bank, end)
        data = raw[begin:finish]
        lines = [f"; {name}: physical bank {bank}, CPU ${start:04X}..${end-1:04X}",
            f"; File offset ${begin:06X}, exact byte SHA256 {hashlib.sha256(data).hexdigest()}",
            "; Reconstructed evidence listing, not original source. Known pointer/table data is marked."]
        pc = start
        calls = []
        while pc < end:
            file_offset = offset(bank, pc)
            span = DATA_SPANS.get((bank, pc))
            if span:
                length, kind, description = span
                lines.append(f"; {description}")
                payload = raw[file_offset:file_offset + length]
                if kind == "word":
                    values = [int.from_bytes(payload[i:i+2], "little") for i in range(0, length, 2)]
                    for i, value in enumerate(values):
                        lines.append(f"${pc+2*i:04X} | ${file_offset+2*i:06X} | .word ${value:04X}")
                else:
                    lines.append(f"${pc:04X} | ${file_offset:06X} | .byte " + ", ".join(f"${v:02X}" for v in payload))
                pc += length
                continue
            size, text = instruction(raw, file_offset, pc)
            code = raw[file_offset:file_offset + size]
            lines.append(f"${pc:04X} | ${file_offset:06X} | {code.hex(' ').upper():<8} | {text}")
            if code == b"\x20\x07\xEE":
                target = int.from_bytes(raw[file_offset + 3:file_offset + 5], "little")
                calls.append({"cpu_address":pc,"kind":"EE07_far_call", "inline_target":target})
                lines.append(f"${pc+3:04X} | ${file_offset+3:06X} | .word ${target:04X} ; EE07 inline far-call target")
                pc += 5
            else:
                if code[0] == 0x20:
                    calls.append({"cpu_address":pc,"kind":"JSR", "target":int.from_bytes(code[1:], "little")})
                pc += size
        (out / "routines" / f"bank-{bank:02d}-{start:04x}-{name}.asm").write_text("\n".join(lines)+"\n")
        reports.append({"name":name,"physical_bank":bank,"cpu_start":start,"cpu_end_exclusive":end,
            "rom_start":begin,"size":len(data),"raw_hex":data.hex(),"sha256":hashlib.sha256(data).hexdigest(),"calls":calls})
    pointer_offset = offset(12, 0xB042)
    targets = [int.from_bytes(raw[pointer_offset+2*i:pointer_offset+2*i+2], "little") for i in range(16)]
    report = {"rom_sha256":ROM_SHA256,"source_is_reconstructed":True,"complete_battle_engine":False,
        "routines":reports,
        "strategy_dispatch":{"physical_bank":12,"cpu_address":0xB02B,"selector_ram":0x0543,"mask":15,
            "pointer_table_cpu":0xB042,"pointer_table_rom_offset":pointer_offset,"count":16,
            "entries":[{"index":i,"target_cpu":target,"action_name":None} for i,target in enumerate(targets)],
            "extent_evidence":"32 pointer bytes at B042..B061; first handler code begins B062. Names await menu/producer linkage."},
        "battle_state_ram":{"actor_slot":"$050A","target_slot":"$0509","slot_to_officer_id":"$0664[20]",
            "x_coordinates":"$0600[20]","y_coordinates":"$0614[20]","side_bits":"$0628[20].7",
            "damage_accumulator":"$042C/$042D","strategy_selector":"$0543&$0F","phase_substate":"$0501"},
        "entry_evidence":[{"physical_bank":31,"cpu_address":0xE1A7,"description":"Fixed-bank initialization sets Y=$2C, calls F237, then A006 -> bank12 A006 JMP bank13 C766"},
            {"physical_bank":12,"cpu_address":0xA000,"description":"Bank12 public entry JMP A009; A028 dispatches $0500 with EADE"},
            {"physical_bank":12,"cpu_address":0xAA9B,"description":"Tactical effect state calls B02B strategy dispatcher"}],
        "limits":["Gameplay action labels are not inferred merely from the opcode index.",
            "Six damage formulas are verified successful-effect prefixes; preceding success gate is separate.",
            "Body-zero removal/far-call dependencies and full duel/battle state machines remain outside reconstructed model.",
            "CPU addresses require mapper state. Pure linear listings in listings/ may decode unmarked data as opcodes; use routines/ annotations for known regions."]}
    (out / "routines.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"routines":len(reports),"strategy_targets":[f"${t:04X}" for t in targets]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "analysis/battle")
    args = parser.parse_args()
    analyze(args.rom, args.out)
