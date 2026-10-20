#!/usr/bin/env python3
"""Inspect a real unchanged-ROM battle snapshot through the recovered modules."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source.recovered.game_engine import GameEngine
from source.recovered.game_enums import tactic_name, TACTIC_ACTION_COSTS, map_terrain, TERRAIN_LABELS

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    p.add_argument('--snapshot',type=Path,default=ROOT/'analysis/runtime/phase3/battle-tactics-true')
    p.add_argument('--data-window-bank',type=int,default=2,help='Physical $8000 bank at controller entry;2 was observed for the bundled fixture')
    p.add_argument('--tick',action='store_true',help='Attempt one controller update; missing dependencies are reported')
    p.add_argument('--mapped',action='store_true',help='Use read-only mapper data windows and independently recovered fixed services')
    a=p.parse_args();rom=a.rom.read_bytes();game=GameEngine.from_snapshot(a.snapshot,rom=rom,data_window_bank=a.data_window_bank,mapped=a.mapped)
    units=[]
    for unit in game.battle_units():
        terrain=map_terrain(rom,game.memory[0xAA:0xAE],unit.x,unit.y)
        officer=unit.officer
        units.append({'slot':unit.slot,'officer_id':unit.officer_id,'xy':[unit.x,unit.y],
                      'faction_and_flags':unit.faction_and_flags,'hundred_troops_cache':unit.hundred_troops_cache,
                      '体':officer.health,'武':officer.martial_strength,'知':officer.intellect,
                      '兵':officer.troops_display,'raw_officer_hex':officer.raw.hex(' '),
                      'terrain':dict(terrain,label=TERRAIN_LABELS.get(terrain['raw_class'])),
                      'movement_quote':game.movement_quote(unit.slot,unit.x,unit.y)})
    tactics=[]
    for row,code in enumerate(game.memory[0x580:0x590]):
        if code==255:break
        tactics.append({'row':row,'action_id':code,'name':tactic_name(code),
                        'action_cost':TACTIC_ACTION_COSTS[code&15]})
    result={'snapshot':str(a.snapshot.resolve()),'control':game.control_state(),
            'units':units,'tactic_menu':tactics,'supplied_controller_data_window_bank':a.data_window_bank,
            'ram_sha256':hashlib.sha256(Path(str(a.snapshot)+'-ram.bin').read_bytes()).hexdigest(),
            'sram_sha256':hashlib.sha256(Path(str(a.snapshot)+'-sram.bin').read_bytes()).hexdigest(),
            'limitations':['This reads a captured original-ROM battle state; it is not a newly simulated turn.',
                           'Scene ticks are controller calls; rendering and global setup need explicit dependencies.']}
    if a.tick:
        if a.mapped:game.prepare_scene_callback()
        try:result['controller_tick']=game.tick_scene()
        except RuntimeError as e:result['required_dependency']={'type':type(e).__name__,'message':str(e)}
        if a.mapped:
            result['mapper_writes']=game.memory.mapper_writes
            result['hardware_requests']=game.memory.hardware_requests
            result['independent_service_calls']={str(k):v.calls for k,v in game.services.items()}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
