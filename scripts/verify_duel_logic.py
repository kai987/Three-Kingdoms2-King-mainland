#!/usr/bin/env python3
"""Actual 6502 differential tests for independent high-level duel game rules.

Original code and all called shared helpers execute unchanged in the oracle.
Compared scope is game fields/RNG/SRAM. CPU registers/flags/stack, mapper and
graphics are explicitly outside the source model's contract, not silently
stubbed into agreement. All fixture writes are to the harness, never the ROM.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from verify_battle import Oracle,make_record
from trace_startup import Bus
from source.recovered.duel_logic import DuelLogic,DuelTables,ROM_SHA256


class DuelOracle(Oracle):
    def __init__(self,rom):
        super().__init__(rom,pair=23)
        snap=ROOT/'analysis/duel_fsm/runtime/injected-core/fixture-state-16'
        self.bus.ram[:]=Path(str(snap)+'-ram.bin').read_bytes()
        self.bus.sram[:]=Path(str(snap)+'-sram.bin').read_bytes()
        self.bus.status_mode='alternating'
        self.load(0xE1,[0x31,0x37,0x38])
        self.set(0x7C,0);self.set(0x300,255);self.set(0x304,255);self.set(0x81,1)


def verify(rom_path,out):
    rom=rom_path.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    tables=DuelTables.from_rom(rom);seed=random.Random(230024)
    counts=Counter();coverage=Counter();examples=[];branches=Counter()
    def model(oracle):
        b=Bus(rom,'alternating');b.ram[:]=oracle.bus.ram;b.sram[:]=oracle.bus.sram
        b.banks=list(oracle.bus.banks);b.bank_initialized=[True]*4;b.protect=0x4c
        return DuelLogic(b,tables)
    def check(name,oracle,logic,entry,method,*,stops=None,extra_addresses=(),incoming_y=None):
        if incoming_y is not None:oracle.cpu.y=incoming_y
        instruction_count=oracle.run(entry,stop=stops,limit=100000)
        outcome=method()
        addresses=list(range(0x4A8,0x4C7))+[0x50,0x515,0x517]+list(extra_addresses)
        mismatches=[{'address':hex(a),'rom':oracle.get(a),'source':logic.memory[a]} for a in addresses if oracle.get(a)!=logic.memory[a]]
        assert not mismatches,(name,mismatches[:8],outcome)
        assert oracle.bus.sram==logic.memory.sram,(name,'SRAM',[(hex(i+0x6000),oracle.bus.sram[i],logic.memory.sram[i]) for i in range(8192) if oracle.bus.sram[i]!=logic.memory.sram[i]][:8])
        counts[name]+=1;coverage.update(oracle.executed)
        if len(examples)<30 or name not in {v['function'] for v in examples}:
            examples.append({'function':name,'entry':hex(entry),'outcome':outcome,'rng_cursor':logic.memory[0x50],'rom_instructions':instruction_count})
        return outcome
    def participants(oracle,left,right,actor=0,ids=(0,1),cursor=0):
        oracle.officer(ids[0],left)
        if ids[1]!=ids[0]:oracle.officer(ids[1],right)
        oracle.load(0x4AD,ids);oracle.set(0x4AA,actor);oracle.set(0x50,cursor)
        oracle.set(0x4A8,2);oracle.set(0x4A9,0)
        oracle.load(0x4B1,[left.health,right.health])
        oracle.load(0x4B5,[0,0])
        for i,leader in enumerate((131,28,208,191,136,78,110)):oracle.set(0x6F07+8*i,leader)

    # Every AI stage plus selected byte boundaries, ambient HP-index bytes and
    # true/false ruler predicates. These execute F387/F2D7/RNG unchanged.
    hp_edges=(0,1,2,14,15,29,30,31,49,50,60,61,99,100,127,128,254,255)
    for i in range(2500):
        actor=i&1;ids=(131,47) if i%7==0 else (0,1)
        left=make_record(health=seed.choice(hp_edges),martial=seed.randrange(256),intelligence=seed.randrange(256),loyalty=seed.randrange(256),virtue=seed.randrange(256))
        right=make_record(health=seed.choice(hp_edges),martial=seed.randrange(256),intelligence=seed.randrange(256),loyalty=seed.randrange(256),virtue=seed.randrange(256))
        oracle=DuelOracle(rom);participants(oracle,left,right,actor,ids,i&255)
        sub=i%5;oracle.set(0x4A9,sub)
        oracle.load(0x4B5,[seed.choice((0,1,2,3,127,128,129,255)),seed.choice((0,1,2,3,127,128,129,255))])
        hp=oracle.get(0x4B1+actor)
        if hp<30 and (hp^1)>1:oracle.set(0x4B1+(hp^1),seed.choice((0,49,50,80,255)))
        logic=model(oracle)
        result=check('ai_stage_'+str(sub),oracle,logic,(0xB5D8,0xB626,0xB659,0xB689,0xB719)[sub],logic.ai_step)
        branches['AI:'+result['reason']]+=1
    # Coupled full AI calls, including real stage skipping and RNG cursor reads.
    for i in range(1200):
        left=make_record(health=seed.randrange(256),martial=seed.randrange(256),intelligence=seed.randrange(256),loyalty=seed.randrange(256),virtue=seed.randrange(256))
        right=make_record(health=seed.randrange(256),martial=seed.randrange(256),intelligence=seed.randrange(256),loyalty=seed.randrange(256),virtue=seed.randrange(256))
        oracle=DuelOracle(rom);participants(oracle,left,right,i&1,cursor=i&255)
        oracle.load(0x4B5,[seed.choice((0,0,0,128)),seed.choice((0,0,0,128))])
        hp=oracle.get(0x4B1+(i&1))
        if hp<30 and (hp^1)>1:oracle.set(0x4B1+(hp^1),seed.choice((0,49,50,80,255)))
        logic=model(oracle);result=logic.choose_ai_action()
        steps=0
        while oracle.get(0x4A8)==2:
            oracle.run(0xB5C8);steps+=1
            assert steps<=5
        addresses=list(range(0x4A8,0x4C7))+[0x50]
        assert all(oracle.get(a)==logic.memory[a] for a in addresses),('fullAI',i,result)
        assert oracle.bus.sram==logic.memory.sram
        counts['choose_ai_action']+=1;coverage.update(oracle.executed);branches['AI_final:'+str(result['category'])]+=1

    # Four conditional formulas tested directly so AI early filters cannot hide
    # missing signed-byte or addition-wrap coverage. Actual helpers also drawR100.
    for entry in (0xB7DD,0xB816,0xB851,0xB89B):
        for i in range(512):
            left=make_record(martial=i&255,intelligence=seed.randrange(256),virtue=seed.randrange(256))
            right=make_record(martial=seed.randrange(256),intelligence=i&255,loyalty=seed.randrange(256))
            oracle=DuelOracle(rom);participants(oracle,left,right,i&1,cursor=i&255)
            oracle.load(0x4B1,[seed.randrange(256),seed.randrange(256)])
            logic=model(oracle)
            def formula():return {'threshold':logic.threshold(entry),'roll':logic.sample(bound=100)}
            result=check('AI_formula_'+hex(entry),oracle,logic,entry,formula)
            assert oracle.get(0x10)==result['threshold']
            assert oracle.cpu.a==result['roll']

    # Duration decay, actor selection, periodic reseed and controller routing.
    for i in range(1024):
        oracle=DuelOracle(rom)
        oracle.set(0x4A8,1);oracle.set(0x4A9,i%3);oracle.set(0x4AA,i&1)
        oracle.load(0x4C0,[seed.choice((0,1,2,3,127,254,255))])
        oracle.load(0x4B3,[seed.randrange(256),seed.randrange(256)])
        oracle.load(0x4B5,[i&255,(i*37)&255]);oracle.load(0x4AB,[0 if i&2 else 128,0 if i&4 else 128])
        oracle.set(0x50,i&255)
        logic=model(oracle)
        check('advance_turn',oracle,logic,0xB361,logic.advance_turn,extra_addresses=(0xA4,))

    # Exact status application: all RNG cursor phases and anomalous stat bytes.
    for i in range(2048):
        left=make_record(intelligence=seed.randrange(256),virtue=seed.randrange(256))
        right=make_record(intelligence=seed.randrange(256),virtue=seed.randrange(256))
        oracle=DuelOracle(rom);participants(oracle,left,right,i&1,cursor=i&255)
        oracle.set(0x4A8,8);oracle.load(0x4B5,[seed.randrange(256),seed.randrange(256)])
        logic=model(oracle)
        result=check('attempt_status_effect',oracle,logic,0xC08A,logic.attempt_status_effect)
        branches['status:'+str(result['succeeded'])]+=1

    # Every one of216 table cells, then extra threshold/wrap/temporary-vs-permanent
    # HP cases. Choose cursor with the required low3 sample for literal coverage.
    cursors=[next(i for i,v in enumerate(tables.rng) if v&7==k) for k in range(8)]
    indices=set()
    for capability in (200,150,100):
        for loyal in (90,60,40):
            for hp in (90,60,40):
                for cursor in cursors:
                    left=make_record(intelligence=capability//2,virtue=capability-capability//2)
                    right=make_record(health=hp,loyalty=loyal)
                    oracle=DuelOracle(rom);participants(oracle,left,right,cursor=cursor)
                    oracle.set(0x4A8,7);oracle.set(0x4B2,255-hp)
                    logic=model(oracle)
                    result=check('negotiation_choice',oracle,logic,0xBE86,logic.negotiation_choice)
                    indices.add(result['table_index'])
    assert indices==set(range(216))
    for i in range(600):
        left=make_record(intelligence=seed.choice((0,49,50,79,80,89,90,100,127,128,180,255)),virtue=seed.randrange(256))
        right=make_record(health=seed.choice((0,49,50,79,80,100,128,255)),loyalty=seed.choice((0,49,50,79,80,100,128,255)))
        oracle=DuelOracle(rom);participants(oracle,left,right,i&1,cursor=i&255)
        oracle.set(0x4A8,7);logic=model(oracle)
        check('negotiation_choice',oracle,logic,0xBE86,logic.negotiation_choice)

    # Direct action1 HP branch: entire byte domain and real same-record aliases.
    for same in (False,True):
        for hp in range(256):
            left=make_record(health=hp);right=make_record(health=hp)
            oracle=DuelOracle(rom);participants(oracle,left,right,hp&1,(0,0) if same else (0,1),hp)
            oracle.set(0x4A8,4);oracle.set(0x4A9,6)
            logic=model(oracle)
            check('action1_hp_penalty',oracle,logic,0xBB5B,logic.action1_hp_penalty,extra_addresses=range(0x42C,0x432))
    for i in range(512):
        oracle=DuelOracle(rom);oracle.set(0x4A8,4);oracle.set(0x4A9,4);oracle.set(0x4AA,i&1)
        oracle.load(0x4B3,[i&255,(i*13)&255]);oracle.set(0x50,i&255)
        logic=model(oracle)
        check('action1_response_gate',oracle,logic,0xBB18,logic.action1_response_gate)
    for actor in (0,1):
        for y in (0,1,2,3,127,128,255):
            oracle=DuelOracle(rom);oracle.set(0x4AA,actor);oracle.set(0x4A8,4)
            logic=model(oracle)
            extra=(0x515+(2 if actor==0 else y),0x515+((2 if actor==0 else y)^2))
            check('action1_exit_result',oracle,logic,0xBC16,lambda:logic.action1_exit_result(incoming_y=y),extra_addresses=extra,incoming_y=y)
        oracle=DuelOracle(rom);oracle.set(0x4AA,actor);oracle.set(0x4A8,4)
        logic=model(oracle)
        check('action1_exit_zero_hp',oracle,logic,0xBBD0,lambda:logic.action1_exit_result(zero_hp=True),extra_addresses=(0x42C,))

    # New high-level action-to-buffer integration around the previously verified
    # arithmetic, including swapped/aliased IDs and full-byte effect/counter data.
    for i in range(1536):
        oracle=DuelOracle(rom);actor=i&1
        oracle.set(0x4AA,actor);oracle.set(0x4A8,3);oracle.set(0x4A9,0)
        ids=(131,131) if i%5==0 else (47,131) if i&2 else (131,47)
        oracle.load(0x4AD,ids);oracle.load(0x560,[131,47])
        oracle.load(0x4B1,[seed.randrange(256),seed.randrange(256)])
        oracle.load(0x4B5,[seed.choice((0,1,127,128,129,255)),seed.choice((0,1,127,128,129,255))])
        oracle.set(0x4BF,(0,2,6)[i%3]);oracle.load(0x4C1,[seed.randrange(256),seed.randrange(256)])
        oracle.load(0x570,[seed.randrange(256),seed.randrange(256)]);oracle.load(0x56E,[seed.randrange(256),seed.randrange(256)])
        oracle.load(0x4C5,[seed.randrange(256),seed.randrange(256)]);oracle.set(0x50,i&255)
        logic=model(oracle)
        check('strike',oracle,logic,0xB8D3,logic.strike,extra_addresses=range(0x42C,0x42F))
    for same in (False,True):
        for i in range(128):
            oracle=DuelOracle(rom);oracle.set(0x4A8,3);oracle.set(0x4A9,1)
            oracle.load(0x4AD,[0,0 if same else 1]);oracle.load(0x4B1,[i*2,(255-i*2)&255])
            finished=bool(i&1);buttons=(0,1,2,3,128,255)[i%6]
            oracle.set(0x300,255 if finished else 0);oracle.set(0x304,255);oracle.set(0x81,buttons)
            logic=model(oracle)
            check('commit_confirmed_hp',oracle,logic,0xB9A5,
                lambda:logic.commit_confirmed_hp(queues_finished=finished,buttons=buttons),extra_addresses=(0x7E,))
    for actor in (0,1):
        for left in (0,1,127,128,255):
            for right in (0,1,127,128,255):
                for display in (0,1,4,255):
                    oracle=DuelOracle(rom);oracle.set(0x4AA,actor);oracle.set(0x4A8,3);oracle.set(0x4A9,2)
                    oracle.load(0x4B1,[left,right]);oracle.set(0x7E,display)
                    logic=model(oracle)
                    check('check_strike_result',oracle,logic,0xB9C8,logic.check_strike_result,extra_addresses=(0x7E,0x42C))

    # Outcome/wait branches execute original UI helpers in the oracle; the
    # source's supplied completion signals are explicit caller inputs.
    for actor in (0,1):
        for sub,entry in ((1,0xBF43),(2,0xBF66),(3,0xBF7E)):
            for finished in (False,True):
                for buttons in (0,1,2,3,128,255):
                    oracle=DuelOracle(rom);oracle.set(0x4AA,actor);oracle.set(0x4A8,7);oracle.set(0x4A9,sub)
                    oracle.set(0x300,255 if finished else 0);oracle.set(0x304,255);oracle.set(0x81,buttons)
                    logic=model(oracle)
                    check('negotiation_outcome',oracle,logic,entry,lambda:logic.negotiation_outcome(sub,queues_finished=finished,buttons=buttons))
        for finished in (False,True):
            for buttons in (0,1,2,3,128,255):
                oracle=DuelOracle(rom);oracle.set(0x4AA,actor);oracle.set(0x4A8,6);oracle.set(0x4A9,5)
                oracle.set(0x300,255 if finished else 0);oracle.set(0x304,255);oracle.set(0x81,buttons)
                logic=model(oracle)
                check('finish_action3',oracle,logic,0xBE3F,lambda:logic.finish_action3(queues_finished=finished,buttons=buttons))

    # Reward identities, level cutoff, one-time flag and same-ID behavior.
    for defeated in (47,131,173,182,222,28):
        for alias in (False,True):
            for packed in (0,0x1F,0x20,0xFF):
                for level in (0x1F,0x20,0xFF):
                    for flag in (0,1,254,255):
                        oracle=DuelOracle(rom);winner=defeated if alias else 0
                        oracle.officer(winner,make_record(equipment=packed,packed_low=level))
                        oracle.set(0x4BD,0);oracle.set(0x514,defeated);oracle.set(0x516,winner)
                        oracle.set(0x4A8,14);oracle.set(0x4A9,2);oracle.set(0x6FE1,flag)
                        oracle.set(0x50,(packed+level+flag)&255)
                        logic=model(oracle)
                        result=check('reward_after_zero_hp',oracle,logic,0xC35D,logic.reward_after_zero_hp,extra_addresses=(0x42C,))
                        branches['reward:'+str(result['awarded'])]+=1
    out.mkdir(parents=True,exist_ok=True)
    # Missing host signals are an API error; these are source contract checks,
    # not added to the original-ROM differential case count.
    contract_checks=[]
    for name,invoke in (
        ('commit_confirmed_hp',lambda m:m.commit_confirmed_hp()),
        ('finish_surrender',lambda m:m.finish_surrender()),
        ('finish_action3',lambda m:m.finish_action3()),
        ('negotiation_outcome_sub3',lambda m:m.negotiation_outcome(3)),
    ):
        oracle=DuelOracle(rom);logic=model(oracle)
        before=(bytes(logic.memory.ram),bytes(logic.memory.sram))
        try:invoke(logic)
        except TypeError:
            assert before==(bytes(logic.memory.ram),bytes(logic.memory.sram))
            contract_checks.append({'method':name,'missing_host_inputs':'raises TypeError','memory_unchanged':True})
        else:raise AssertionError(f'{name} silently assumed completed host work')
    result={'status':'passed','rom_sha256':ROM_SHA256,'case_count':sum(counts.values()),'function_cases':dict(counts),
        'branch_observations':dict(branches),'negotiation_cells_verified':len(indices),'samples':examples,
        'executed_unique_original_instruction_locations':len(coverage),
        'compared_scope':'Declared game fields, whole SRAM and RNG cursor0; flags/registers/stack/mapper/display effects explicitly excluded',
        'source_original_code_calls':0,'source_ir_execution':False,'source_rendering_noops':False,
        'host_input_contract_checks':contract_checks,
        'oracle_scope':'Actual unmodified ROM instructions and all called helpers; CPU-only bus with explicit IO assumptions, not a full video-frame test',
        'original_rom_unchanged':hashlib.sha256(rom_path.read_bytes()).hexdigest()==ROM_SHA256}
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','case_count','function_cases','negotiation_cells_verified')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase4/duel');a=p.parse_args();verify(a.rom,a.out)
