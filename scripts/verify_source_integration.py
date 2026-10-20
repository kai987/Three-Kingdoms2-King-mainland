#!/usr/bin/env python3
"""Verify shared-memory source integration and explicit scene/UI contracts."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.game_engine import GameEngine,ROM_SHA256,UnresolvedScene
from source.recovered.mapped_memory import UnsupportedHardware
from source.recovered.runtime_services import queued_message
from source.recovered.controller_helpers import MissingSharedHelper

def main():
    parser=argparse.ArgumentParser();parser.add_argument('rom',type=Path);a=parser.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    cases=[]
    specs=[('battle','analysis/runtime/phase3/battle-tactics-true',0xA028,12,True),
           ('attack','analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu',0xA069,14,False),
           ('duel','analysis/duel_fsm/runtime/injected-core/fixture-state-16',0xB100,23,False)]
    for name,prefix,entry,pair,natural in specs:
        path=ROOT/prefix;game=GameEngine.from_snapshot(path,rom=rom,data_window_bank=2,mapped=True)
        bus=Bus(rom,'alternating');bus.ram[:]=game.memory.ram;bus.sram[:]=game.memory.sram
        bus.banks=[bus.ram[0xDE]&31,bus.ram[0xDF]&31,bus.ram[0xE0]&31,31]
        bus.bank_initialized=[True]*4;bus.protect=0x4C;cpu=MPU(memory=bus);bus.cpu=cpu;cpu.pc=0xF800
        for n in range(200000):
            if cpu.pc==entry:break
            bus.pc=cpu.pc;bus.step_no=n;cpu.step()
        else:raise AssertionError('NMI failed to reach entry')
        game.prepare_scene_callback()
        assert game.memory.banks==bus.banks
        assert game.memory[0xE1:0xE4]==bus.ram[0xE1:0xE4]
        assert game.memory[0x7C]==bus.ram[0x7C]==0
        dependency=None
        try:game.tick_scene()
        except RuntimeError as exc:dependency={'type':type(exc).__name__,'message':str(exc)}
        assert dependency is not None,'Fixture unexpectedly completed all outstanding display dependencies'
        cases.append({'kind':'mapped callback context','scene':name,'snapshot':prefix,'natural_gameplay':natural,
                      'banks':bus.banks,'source_fixed_services':list(game.services),
                      'remaining_dependency':dependency,'original_nmi_steps':n})
    base=ROOT/specs[0][1]
    def fixture():return GameEngine.from_snapshot(base,rom=rom,data_window_bank=2,mapped=True)
    game=fixture();unit=game.battle_units()[0]
    quote=game.movement_quote(unit.slot,unit.x,unit.y)
    assert quote['cell']['legal_cell'] and quote['affinity_supported']
    cases.append({'kind':'original snapshot movement quote','natural_gameplay':True,'slot':unit.slot,'quote':quote})
    # Explicit synthetic gameplay inputs exercise module wiring, not natural play.
    game=GameEngine.from_snapshot(ROOT/specs[2][1],rom=rom,data_window_bank=2,mapped=True)
    game.memory[0x4A8]=2;game.memory[0x4A9]=4;game.memory[0x4AA]=0
    rules=game.duel_rules();assert rules.memory is game.memory
    result=rules.choose_ai_action();assert game.memory[0x4A8:0x4AA]==bytes([1,3])
    cases.append({'kind':'synthetic duel AI integration','natural_gameplay':False,'result':result})
    game=fixture();m=game.memory
    m[0x500:0x502]=bytes([14,0]);m[0x50B]=2
    city=m[0x50E];start=0x6000+32*city;m[start+17:start+27]=bytes([255]*10)
    ids=[u.officer_id for u in game.battle_units() if not u.faction_and_flags&128]
    before={i:bytes(m[0x63C0+12*i:0x63CC+12*i]) for i in ids}
    result=game.postbattle_rules().step()
    assert m[0x500:0x502]==bytes([15,2])
    assert set(ids)<=set(m[start+17:start+27])
    assert all(bytes(m[0x63C0+12*i:0x63CC+12*i])==before[i] for i in ids)
    cases.append({'kind':'synthetic winner roster integration','natural_gameplay':False,'officers':ids,'result':result})
    game=fixture();m=game.memory;m[0x500:0x502]=bytes([15,0]);m[0x507]=0;m[0x514]=0
    m[0x6F0A]=3;m[0x664:0x678]=bytes([255]*20);m[0x628:0x63C]=bytes([255]*20)
    m[0x6F47:0x6F6F]=bytes([255]*40)
    for i,officer in enumerate(ids[:3]):m[0x66E+i]=officer;m[0x632+i]=128
    m[start+17:start+27]=bytes([255]*10)
    result=game.settlement_rules();assert m[0x501]==1 and m[0x6F91]==0
    assert list(m[start+17:start+17+min(3,len(ids))])==ids[:3]
    m[0x501]=2
    try:game.settlement_rules()
    except RuntimeError as exc:assert 'ECEE' in str(exc)
    else:raise AssertionError('Missing display barrier silently accepted')
    cases.append({'kind':'synthetic allocation plus explicit settlement barrier','natural_gameplay':False,
                  'allocation_result':result,'missing_display_barrier_rejected':True})
    game=fixture();m=game.memory;m[0x500:0x502]=bytes([9,8]);m[0x300]=m[0x304]=0;m[0x81]=0
    bus=Bus(rom,'zero');bus.ram[:]=m.ram;bus.sram[:]=m.sram
    bus.banks=[2,8,9,31];bus.bank_initialized=[True]*4;bus.protect=0x4C
    bus.ram[0x1FE:0x200]=bytes([255,1]);cpu=MPU(memory=bus);bus.cpu=cpu;cpu.pc=0xC0BB;cpu.sp=0xFD;cpu.p=32
    for n in range(20000):
        if cpu.pc==0x200:break
        bus.pc=cpu.pc;bus.step_no=n;cpu.step()
    else:raise AssertionError('Village oracle exceeded budget')
    result=game.tick_map_service()
    assert m.ram==bus.ram and m.sram==bus.sram and m.banks==bus.banks
    registers=game._map_service.registers
    assert all(getattr(registers,k)==getattr(cpu,k)for k in ('a','x','y','p','sp','pc'))
    m[0x300]=m[0x304]=255;m[0x81]=1
    try:game.tick_map_service()
    except MissingSharedHelper as exc:assert 'F1AD' in str(exc)
    else:raise AssertionError('Missing village renderer silently accepted')
    cases.append({'kind':'synthetic village wait entry with original full CPU comparison','natural_gameplay':False,
                  'result':result,'missing_village_renderer_rejected':True})
    try:m[0x2000]=128
    except UnsupportedHardware:pass
    else:raise AssertionError('PPU write silently accepted')
    assert game.memory.rom==rom
    out=ROOT/'analysis/phase4/source-integration.json'
    report={'status':'passed','case_count':len(cases),'cases':cases,'rom_sha256':ROM_SHA256,
            'game_source_uses_original_cpu_oracle':False,
            'limits':['NMI comparisons cover only callback banks/E1..E3/OAM preconditions; village waiting entry also compares full RAM/SRAM/registers. Video is excluded.',
                      'Domain integration fixtures are labeled synthetic and do not add original-ROM differential case counts.',
                      'Rendering, queue completion and whole-video-frame execution remain explicit dependencies.']}
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'passed','integration_cases':len(cases)},ensure_ascii=False))
if __name__=='__main__':main()
