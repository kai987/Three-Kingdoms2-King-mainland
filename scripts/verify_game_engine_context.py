#!/usr/bin/env python3
"""Verify explicit controller data windows against original NMI entry behavior.

The py65 bus has synthetic PPU status; this tests mapper writes and entry context,
not a complete video frame. Imported snapshots retain their natural/fixture scope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import GameEngine,UnresolvedScene
from source.recovered.controller_helpers import MissingSharedHelper
from source.recovered.battle_state_machine import UnresolvedDependency as BattleDependency
from source.recovered.attack_state_machine import UnresolvedDependency as AttackDependency
from source.recovered.duel_state_machine import UnresolvedDependency as DuelDependency

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
    specs=[('battle','analysis/runtime/phase3/battle-tactics-true',0xA028,3,True),
           ('attack','analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu',0xA069,4,False),
           ('duel','analysis/duel_fsm/runtime/injected-core/fixture-state-16',0xB100,5,False)]
    results=[]
    for label,name,entry,scene,natural in specs:
        prefix=ROOT/name;ram=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
        bus=Bus(rom,'alternating');bus.ram[:]=ram;bus.sram[:]=sram
        bus.banks=[ram[0xDE]&31,ram[0xDF]&31,ram[0xE0]&31,31];bus.bank_initialized=[True]*4;bus.protect=0x4C
        cpu=MPU(memory=bus);cpu.pc=0xF800;bus.cpu=cpu
        for steps in range(200000):
            if cpu.pc==entry:break
            bus.pc=cpu.pc;bus.step_no=steps
            if cpu.disassemble[bus.peek(cpu.pc)][0]=='???':raise AssertionError(f'Unsupported opcode {cpu.pc:04X}')
            cpu.step()
        else:raise AssertionError(f'NMI did not reach {label} controller, PC {cpu.pc:04X}')
        assert bus.banks[0]==2,(label,bus.banks)
        assert bus.ram[0x7C]==0
        game=GameEngine.from_snapshot(prefix,rom=rom,data_window_bank=bus.banks[0])
        assert game.scene==scene
        dependency=None
        try:game.tick_scene()
        except (MissingSharedHelper,BattleDependency,AttackDependency,DuelDependency) as e:dependency=str(e)
        assert game.memory[0x8000:0xA000]==rom[16+8192*2:16+8192*3]
        no_context=GameEngine.from_snapshot(prefix,rom=rom)
        try:no_context.tick_scene()
        except UnresolvedScene as e:assert 'data_window_bank' in str(e)
        else:raise AssertionError('Missing entry-bank context was silently guessed')
        results.append({'scene':label,'snapshot':name,'natural_gameplay':natural,'controller_entry':hex(entry),
                        'original_nmi_steps':steps,'entry_banks':bus.banks,
                        'saved_restore_bank_DE':ram[0xDE]&31,'observed_entry_E1':bus.ram[0xE1],
                        'nmi_oam_counter_007c':bus.ram[0x7C],
                        'explicit_data_window_matches':True,'missing_context_rejected':True,
                        'controller_tick_required_dependency':dependency})
    out=ROOT/'analysis/phase3/game-engine-context-validation.json'
    result={'status':'passed','rom_sha256':hashlib.sha256(rom).hexdigest(),'cases':results,
            'scope':'Original NMI mapper selection up to the three controller entries, plus explicit source context validation',
            'limits':['PPUSTATUS is an alternating fixture, not real PPU timing.','Bank2 is observed for these inputs, not asserted as a universal rule.']}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
