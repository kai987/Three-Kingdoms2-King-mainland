#!/usr/bin/env python3
"""Inspect real initial officers and demonstrate recovered combat calculations.

The battle inputs are an explicit example, not a captured game turn. A failed
gate does not apply damage or award experience. Unknown game stages are omitted.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from recovered.officers import initial_officers,STATUS_INTERPRETATION
from recovered.battle import Officer,strategy_gate,strategy_damage_amount,troop_loss,DAMAGE_PREFIX_TACTICS
from recovered.game_enums import tactic_name
from recovered.ai import knowledge_tier,special_ai_gate
from recovered.game_algorithms import PermutationRng

def describe(ident,o):
    return {'id':ident,'raw_hex':o.raw.hex(' '),'体':o.health,'武':o.martial_strength,
            '知':o.intellect,'忠':o.loyalty,'忠_表示':o.loyalty_text(),'徳':o.virtue,
            '経験_raw':o.experience_raw,'経_表示':o.experience_display,
            '兵_raw_le16':o.troops_raw,'兵_表示_low10':o.troops_display,
            'weapon_id':o.weapon_id,'armor_id':o.armor_id,
            'experience_tier':o.experience_tier,'level_display':o.level_display,
            'terrain_code':o.terrain_affinity_code,'terrain_glyph':o.terrain_glyph,
            'status_code':o.status_code,'status_interpretation':STATUS_INTERPRETATION[o.status_code],
            'byte5_roaming_location_inference':o.roaming_city_id}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    p.add_argument('--officer',type=int,default=38);p.add_argument('--target',type=int,default=109)
    p.add_argument('--rng-cursor',type=int,default=128);p.add_argument('--effect',type=lambda x:int(x,0),default=0xB188)
    a=p.parse_args();rom=a.rom.read_bytes();records=initial_officers(rom)
    if not 0<=a.officer<237 or not 0<=a.target<237:raise ValueError('Officer IDs must be 0..236')
    if a.officer==a.target:raise ValueError('This demonstration uses distinct actor and target IDs')
    actor,target=Officer(records[a.officer].raw),Officer(records[a.target].raw)
    rng=PermutationRng(rom[0x3e8ca:0x3e9ca],[a.rng_cursor&255,0,0,0])
    gate=strategy_gate(actor,target,(3,6),(4,8),0,0,rng)
    damage=0;applied=0;accumulator=0;marker=0
    if gate.passed:
        damage=strategy_damage_amount(a.effect,actor,rng)
        actor,target,applied,accumulator,marker=troop_loss(actor,target,damage)
    result={'actor':describe(a.officer,records[a.officer]),'target':describe(a.target,records[a.target]),
            'example_input':{'actor_xy':[3,6],'target_xy':[4,8],'phase_type':0,'environment':0,
                             'effect_entry':hex(a.effect),'rng_cursor':a.rng_cursor&255,
                             'tactic_id':int(DAMAGE_PREFIX_TACTICS[a.effect]),
                             'tactic_name':tactic_name(DAMAGE_PREFIX_TACTICS[a.effect])},
            'battle_example':{'gate':asdict(gate),'requested_effect_amount':damage,'applied_troop_loss':applied,
                              'actor_after_raw':actor.raw.hex(' '),'target_after_raw':target.raw.hex(' '),
                              'accumulated_loss':accumulator,'level_marker':marker,'rng_cursor_after':rng.cursors[0]},
            'ai_gate':{'knowledge_tier':knowledge_tier(records[a.officer].intellect),
                       'special_ai_gate':special_ai_gate(records[a.officer].intellect,records[a.officer].raw[11])},
            'limitations':['Example calculations use explicit invented positions/context, not an observed turn.',
                           'The effect prefix has a verified tactic name; its full state/animation execution is separate.',
                           'Animation, removal, global campaign rules and full battle state machines are omitted.']}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
