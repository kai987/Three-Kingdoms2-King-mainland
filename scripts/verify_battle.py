#!/usr/bin/env python3
"""Differentially verify recovered battle behavior against actual ROM bytes.

CPU-only oracle with mapper19 banking, actual fixed-bank helpers and SRAM.
No rendering, interrupts or game-loop claims. No source ROM modifications.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered.battle import (
    ROM_SHA256, Officer, grid_distance, strategy_gate, conversion_gate,
    experience_from_accumulated_loss, troop_loss, health_loss_core,
    strategy_damage_amount, duel_parameter_seed, duel_strike_sample,
    duel_health_strike, duel_strike_effect, duel_attack_parameters,
)
from source.recovered.game_algorithms import PermutationRng


class Oracle:
    def __init__(self, rom, pair=12):
        self.bus = Bus(rom, "zero")
        self.bus.banks = [17, pair, pair + 1, 31]
        self.bus.bank_initialized = [True] * 4
        self.bus.protect = 0x4C
        self.cpu = MPU(memory=self.bus)
        self.bus.cpu = self.cpu
        self.bus.ram[0xE1:0xE4] = bytes([0x31, pair | 0x20, (pair + 1) | 0x20])
        self.executed = Counter()

    def set(self, address, value):
        if address < 0x2000:
            self.bus.ram[address & 2047] = value & 255
        elif 0x6000 <= address < 0x8000:
            self.bus.sram[address - 0x6000] = value & 255
        else:
            raise ValueError(address)

    def load(self, address, values):
        for i, value in enumerate(values): self.set(address + i, value)

    def get(self, address): return self.bus.peek(address)
    def word(self, address): return self.get(address) | self.get(address + 1) << 8

    def officer(self, officer_id, record):
        self.load(0x63C0 + officer_id * 12, record.raw)

    def read_officer(self, officer_id):
        address = 0x63C0 + officer_id * 12
        return Officer(bytes(self.get(address + i) for i in range(12)))

    def run(self, entry, *, stop=None, limit=10000):
        cpu = self.cpu
        cpu.pc, cpu.sp, cpu.p = entry, 0xFD, cpu.UNUSED
        # RTS -> artificial RAM sentinel, without patching a ROM byte.
        self.load(0x1FE, [0xFF, 0x01])
        for step in range(limit):
            if cpu.pc == 0x0200 or stop and stop(cpu.pc):
                return step
            self.bus.pc, self.bus.step_no = cpu.pc, step
            origin = self.bus.origin(cpu.pc)
            if origin is None:
                raise AssertionError(f"Unexpected RAM execution ${cpu.pc:04X}")
            bank, offset = origin
            self.executed[(bank, cpu.pc, offset)] += 1
            if cpu.disassemble[self.bus.peek(cpu.pc)][0] == "???":
                raise AssertionError(f"Unsupported opcode at bank{bank}:${cpu.pc:04X}")
            cpu.step()
        raise AssertionError(f"Oracle budget exceeded, entry ${entry:04X}, PC ${cpu.pc:04X}")


def make_record(health=100, martial=75, intelligence=80, loyalty=60, virtue=70,
                experience=0, troops=700, level=0, packed_low=0, equipment=0):
    return Officer(bytes([health & 255, martial & 255, intelligence & 255,
        loyalty & 255, virtue & 255, 0, experience & 255, experience >> 8 & 255,
        troops & 255, troops >> 8 & 255, equipment & 255, (level << 4 | packed_low) & 255]))


def participants(oracle, actor, target, cursor=0, same_record=False):
    oracle.officer(0, actor)
    if not same_record: oracle.officer(1, target)
    oracle.set(0x0664, 0)
    oracle.set(0x0665, 0 if same_record else 1)
    oracle.set(0x050A, 0)
    oracle.set(0x0509, 1)
    oracle.set(0x0050, cursor)


def verify(rom, out):
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
    table = rom[0x3E8CA:0x3E9CA]
    equipment_table = rom[0x2F2D0:0x2F2F0]
    weapon_table = rom[0x1EA2F:0x1EA4F]
    armor_table = rom[0x1EA47:0x1EA4F]
    counts = Counter()
    executed = Counter()
    samples = []
    def passed(name, oracle):
        counts[name] += 1
        executed.update(oracle.executed)
    seeded = random.Random(650219)

    # Exhaustive Cartesian product of representative byte boundaries, including
    # the unusual 15/16 grid row and signed-byte boundaries 127/128/255.
    coords = (0, 1, 14, 15, 16, 17, 127, 128, 129, 254, 255)
    for ax in coords:
        for ay in coords:
            for tx in coords:
                for ty in coords:
                    oracle = Oracle(rom)
                    oracle.set(0x050A, 0); oracle.set(0x0509, 1)
                    oracle.load(0x0600, [ax, tx]); oracle.load(0x0614, [ay, ty])
                    oracle.run(0xB860)
                    assert oracle.cpu.a == grid_distance((ax, ay), (tx, ty)), (ax, ay, tx, ty, oracle.cpu.a)
                    passed("grid_distance", oracle)

    # Inputs span normal stats and deliberately anomalous bytes; RNG cursor
    # effects and early failures without a draw are part of the assertion.
    for i in range(2048):
        actor = make_record(intelligence=seeded.randrange(256), virtue=seeded.randrange(256), level=seeded.randrange(16))
        target = make_record(intelligence=seeded.randrange(256), loyalty=seeded.choice([0, 30, 31, 50, 51, 70, 71, 100, 255]), level=seeded.randrange(16))
        actor_xy = (seeded.randrange(20), seeded.randrange(20))
        target_xy = (seeded.randrange(20), seeded.randrange(20))
        cursor, phase, environment = i & 255, i & 3, i & 7
        for name, entry, model in [("strategy_gate", 0xB7BE, strategy_gate), ("conversion_gate", 0xB72B, conversion_gate)]:
            oracle = Oracle(rom); participants(oracle, actor, target, cursor)
            oracle.load(0x0600, [actor_xy[0], target_xy[0]]); oracle.load(0x0614, [actor_xy[1], target_xy[1]])
            oracle.set(0x050F, phase); oracle.set(0x6F02, environment)
            rng = PermutationRng(table, [cursor, 0, 0, 0])
            expected = model(actor, target, actor_xy, target_xy, phase, environment, rng) if name == "strategy_gate" else model(actor, target, actor_xy, target_xy, rng)
            oracle.run(entry)
            assert bool(oracle.cpu.p & 1) == expected.passed, (name, i, expected, oracle.cpu.p)
            assert oracle.get(0x50) == rng.cursors[0], (name, i, "cursor")
            if expected.threshold is not None:
                assert oracle.get(0x00) == expected.threshold, (name, i, expected.threshold, oracle.get(0))
            passed(name, oracle)

    # Experience boundary behavior, including addition overflow and one-level
    # advancement even when an increment crosses several thresholds.
    xp_values = (0, 998, 999, 1000, 1999, 2000, 3499, 3500, 4999, 5000,
                 7499, 7500, 9999, 10000, 14999, 15000, 49998, 49999, 50000, 65535)
    for experience in xp_values:
        for level in (0, 1, 6, 7, 15):
            for martial in (0, 50, 51, 70, 71, 80, 81, 89, 90, 255):
                for counter in (0, 1, 2, 200, 65535):
                    actor = make_record(martial=martial, experience=experience, level=level, packed_low=9)
                    oracle = Oracle(rom, pair=14); oracle.officer(0, actor)
                    oracle.load(0x0A, [0, counter & 255, counter >> 8])
                    oracle.run(0xD7FB)
                    expected, marker = experience_from_accumulated_loss(actor, counter)
                    assert oracle.read_officer(0) == expected, ("experience", experience, level, martial, counter)
                    assert oracle.get(0x0F) == marker
                    passed("experience_from_accumulated_loss", oracle)

    # Full B68B executes EE07, bank14 A006, bank15 D7FB and EE4D restoration;
    # no stub or ROM patch is used. Includes actual same-address alias cases.
    for same_record in (False, True):
        for troops in (0, 1, 255, 256, 700, 1023, 0x0400, 0xABCD, 0xFFFF):
            for requested in (0, 1, 255, 256, 700, 1023, 65535):
                for counter in (0, 1, 65535):
                    target = make_record(experience=999, troops=troops, level=0, packed_low=13)
                    actor = target if same_record else make_record(experience=1999, martial=89, level=1)
                    oracle = Oracle(rom); participants(oracle, actor, target, same_record=same_record)
                    oracle.load(0x00, [0xC0 if same_record else 0xCC, 0x63, requested & 255, requested >> 8])
                    oracle.load(0x042C, [counter & 255, counter >> 8])
                    oracle.run(0xB68B)
                    ea, et, loss, total, marker = troop_loss(actor, target, requested, counter, same_record=same_record)
                    assert oracle.read_officer(0) == ea
                    assert oracle.read_officer(0 if same_record else 1) == et
                    assert oracle.word(0x042C) == total
                    assert oracle.get(0x042E) == 0
                    assert oracle.bus.banks[1:3] == [12, 13], oracle.bus.banks
                    assert oracle.cpu.sp == 255
                    passed("troop_loss_alias" if same_record else "troop_loss", oracle)

    for health in (0, 1, 5, 14, 100, 127, 128, 255):
        for requested in (0, 1, 5, 14, 100, 127, 128, 255):
            target = make_record(health=health, packed_low=8)
            oracle = Oracle(rom); oracle.officer(1, target)
            oracle.load(0, [0xCC, 0x63, requested])
            oracle.run(0xB5D8, stop=lambda pc: pc == 0xB611)
            expected, applied, zero = health_loss_core(target, requested)
            assert oracle.read_officer(1) == expected
            assert oracle.get(0x042F) == applied
            passed("health_loss_core_prefix", oracle)

    for entry, stop in [(0xB070, 0xB0CD), (0xB0EB, 0xB145), (0xB188, 0xB1C5),
                        (0xB1E3, 0xB233), (0xB4C6, 0xB4FC), (0xB55C, 0xB599)]:
        for i in range(512):
            actor = make_record(martial=seeded.randrange(256), intelligence=seeded.randrange(256), level=seeded.randrange(16))
            target = make_record(health=255, troops=1023)
            cursor = i & 255
            oracle = Oracle(rom); participants(oracle, actor, target, cursor)
            rng = PermutationRng(table, [cursor, 0, 0, 0])
            expected = strategy_damage_amount(entry, actor, rng)
            oracle.run(entry, stop=lambda pc: pc == stop)
            actual = oracle.get(2) if entry == 0xB0EB else oracle.word(2)
            assert actual == expected, (hex(entry), i, actor, expected, actual)
            assert oracle.get(0x50) == rng.cursors[0]
            passed(f"damage_{entry:04X}_prefix", oracle)
            if i < 2: samples.append({"routine":f"damage_{entry:04X}","actor_record_hex":actor.raw.hex(),"cursor":cursor,"result":expected,"next_cursor":rng.cursors[0]})

    # Duel parameter construction executes both original record reads and the
    # actual correction table, with separate rejection samples for both sides.
    for i in range(512):
        left = make_record(health=seeded.randrange(256), martial=seeded.randrange(256), equipment=i & 255)
        right = make_record(health=seeded.randrange(256), martial=seeded.randrange(256), equipment=255 - (i & 255))
        oracle = Oracle(rom, pair=23); oracle.officer(0, left); oracle.officer(1, right)
        oracle.load(0x04AD, [0, 1]); oracle.set(0x50, i & 255)
        rng = PermutationRng(table, [i & 255, 0, 0, 0])
        bases, randomized, selected = duel_parameter_seed(left, right, equipment_table, rng)
        oracle.run(0xB230)
        assert tuple(oracle.get(0x04B3 + j) for j in range(2)) == bases
        assert tuple(oracle.get(0x04BD + j) for j in range(2)) == randomized
        assert oracle.get(0x04AA) == selected
        assert oracle.get(0x50) == rng.cursors[0]
        passed("duel_parameter_seed", oracle)

    for i in range(1024):
        attack_base, attack_modifier, opposing_modifier = [seeded.randrange(256) for _ in range(3)]
        oracle = Oracle(rom, pair=23)
        oracle.set(0x04AA, 0); oracle.set(0x04AD, 0); oracle.set(0x0560, 0)
        oracle.set(0x04C1, attack_base); oracle.set(0x0570, attack_modifier); oracle.set(0x056F, opposing_modifier)
        oracle.set(0x50, i & 255)
        rng = PermutationRng(table, [i & 255, 0, 0, 0])
        roll, damage = duel_strike_sample(attack_base, attack_modifier, opposing_modifier, rng)
        oracle.run(0xBA15)
        assert oracle.get(0x10) == roll
        assert oracle.get(1) == damage, ("duel_strike_sample", i, attack_base, attack_modifier, opposing_modifier, damage, oracle.get(1))
        assert oracle.get(0x50) == rng.cursors[0]
        passed("duel_strike_sample", oracle)

    for health in range(256):
        for cursor in (0, 1, 127, 128, 254, 255):
            target = make_record(health=health)
            oracle = Oracle(rom, pair=23); oracle.officer(1, target)
            oracle.load(0x04AD, [0, 1]); oracle.set(0x04AA, 0); oracle.set(0x50, cursor)
            rng = PermutationRng(table, [cursor, 0, 0, 0])
            expected, requested = duel_health_strike(target, rng)
            oracle.run(0xBB5B)
            assert oracle.read_officer(1) == expected
            assert oracle.get(0x042F) == requested
            assert oracle.get(0x50) == rng.cursors[0]
            passed("duel_health_strike", oracle)

    for i in range(1024):
        attack_base, attack_modifier, opposing_modifier, actor_hp, target_hp, threshold = [seeded.randrange(256) for _ in range(6)]
        category = (0, 6, 1, 3, 255)[i % 5]
        boost = (0, 1, 128, 129, 255)[i // 5 % 5]
        oracle = Oracle(rom, pair=23)
        oracle.set(0x04AA, 0); oracle.set(0x04AD, 0); oracle.set(0x0560, 0)
        oracle.set(0x04C1, attack_base); oracle.set(0x0570, attack_modifier); oracle.set(0x056F, opposing_modifier)
        oracle.load(0x04B1, [actor_hp, target_hp]); oracle.set(0x04B5, boost)
        oracle.set(0x04BF, category); oracle.set(0x04C5, threshold)
        oracle.set(0x50, i & 255)
        rng = PermutationRng(table, [i & 255, 0, 0, 0])
        expected = duel_strike_effect(attack_base, attack_modifier, opposing_modifier, actor_hp, target_hp, boost, category, threshold, rng)
        oracle.run(0xB8D3)
        assert oracle.get(0x04B1) == expected['actor_health'], ("duel_strike_actor",i,expected,oracle.get(0x04B1))
        assert oracle.get(0x04B2) == expected['target_health'], ("duel_strike_target",i,expected,oracle.get(0x04B2))
        assert oracle.get(0x0311) == expected['message'], ("duel_strike_message",i,expected,oracle.get(0x0311))
        assert oracle.get(0x50) == rng.cursors[0]
        if expected['reported_damage'] is not None:
            assert oracle.get(0x042C) == expected['reported_damage']
        passed("duel_strike_effect", oracle)

    for martial in (0, 49, 50, 64, 65, 79, 80, 86, 87, 91, 92, 96, 97, 100, 127, 128, 255):
        for equipment in range(256):
            cursor = equipment & 255
            officer = make_record(martial=martial, equipment=equipment)
            oracle = Oracle(rom, pair=14); oracle.officer(0, officer)
            oracle.load(0, [0xC0, 0x63]); oracle.set(0x50, cursor)
            rng = PermutationRng(table, [cursor, 0, 0, 0])
            attack_base, weapon, armor = duel_attack_parameters(officer, weapon_table, armor_table, rng)
            oracle.run(0xC991)
            assert (oracle.cpu.a, oracle.cpu.y, oracle.cpu.x) == (attack_base, weapon, armor), ("duel_attack_parameters", martial, equipment)
            assert oracle.get(0x50) == rng.cursors[0]
            passed("duel_attack_parameters", oracle)

    out.mkdir(parents=True, exist_ok=True)
    result = {"status":"passed", "rom_sha256":ROM_SHA256,
        "oracle":"py65 1.2.0 executing original machine bytes through mapper19 Bus; no ROM patch or dependency stub",
        "case_count":sum(counts.values()), "counts":dict(counts), "examples":samples,
        "limits":["CPU function harnesses; no PPU, NMI/IRQ timing, audio, complete game flow or hardware validation.",
            "Damage prefixes intentionally stop before target application; health core stops before removal/death dependencies.",
            "Troop-loss harness separately executes its complete real far-call/experience path with distinct and aliased records.",
            "Duel strike buffers are linked to actual C926/C991 producer; full duel state machine, animation and result writeback remain to be recovered.",
            "Officers use synthetic byte/boundary inputs plus this ROM's actual RNG/correction tables."]}
    (out / "validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    locations = [{"physical_bank":b,"cpu_address":pc,"prg_offset":offset,
        "rom_offset":offset+16,"executions":n} for (b,pc,offset),n in sorted(executed.items())]
    (out / "oracle_executed_locations.json").write_text(json.dumps(locations,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"case_count":result["case_count"],"counts":result["counts"]},indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "analysis/battle")
    args = parser.parse_args()
    verify(args.rom.read_bytes(), args.out)
