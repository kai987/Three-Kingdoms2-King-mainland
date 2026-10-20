#!/usr/bin/env python3
"""Compare recovered AI algorithms to actual ROM 6502 execution under py65.

Controlled chooser fixtures replace $AC7B's suitability result. Separate terrain
fixtures execute actual $AC7B and neighbors but supply $B6E5's external terrain
classes. All substitutions are recorded per result. Surrounding branches,
record-pointer lookup, whitelist lookup and AI RNG execute original ROM bytes.
This is a CPU behavior oracle, not a complete gameplay timing claim.
"""
from pathlib import Path
import argparse, json, hashlib, random, sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--output',type=Path,default=Path('analysis/ai/validation.json'))
    a=p.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source/recovered'))
    import ai
    from py65.devices.mpu6502 import MPU
    blob=a.rom.read_bytes()
    assert hashlib.sha256(blob).hexdigest()==ai.ROM_SHA256
    memory=[0]*65536
    memory[0xA000:0xC000]=blob[0x10010:0x12010]
    memory[0xC000:0xE000]=blob[0x12010:0x14010]
    memory[0xE000:0x10000]=blob[0x3E010:0x40010]
    def run(cpu, regs=None, values=None, predicate=None, stop_at=None, predicate_by_slot=False, terrain_by_position=None):
        m=MPU(memory=memory.copy()); m.memory[0x200:0x203]=[0x20,cpu&255,cpu>>8]
        m.pc=0x200; m.p &= ~8
        for key,value in (regs or {}).items(): setattr(m,key,value)
        for key,value in (values or {}).items(): m.memory[key]=value&255
        requests=[]
        for steps in range(500000):
            if stop_at is not None and m.pc==stop_at:
                return m,steps,requests
            if terrain_by_position is not None and m.pc==0xB6E5:
                value=terrain_by_position[(m.memory[0x20],m.memory[0x21])]
                m.a=2 if value>=6 else value
                low=m.memory[0x100+((m.sp+1)&255)];high=m.memory[0x100+((m.sp+2)&255)]
                m.sp=(m.sp+2)&255;m.pc=(low+256*high+1)&65535
            elif predicate is not None and m.pc==0xAC7B:
                requests.append((m.memory[0x2B],m.x) if predicate_by_slot else m.x)
                m.memory[0x2C]=m.x
                accepted=predicate(m.memory[0x2B],m.x) if predicate_by_slot else predicate(m.x)
                m.p=(m.p&~1)|int(bool(accepted))
                low=m.memory[0x100+((m.sp+1)&255)]; high=m.memory[0x100+((m.sp+2)&255)]
                m.sp=(m.sp+2)&255; m.pc=((low+256*high+1)&65535)
            else:
                if terrain_by_position is not None and m.pc==0xAC7B:
                    requests.append((m.memory[0x2B],m.x))
                m.step()
            if m.pc==0x203: return m,steps+1,requests
        raise AssertionError(f'CPU ${cpu:04X} failed return; PC=${m.pc:04X}')
    rnd=random.Random(0xA9CF)
    results=[]
    def save(name,count,examples,substituted=False,variant=None):
        results.append(dict(name=name,status='passed',case_count=count,
                            routine=ai.ROUTINES[name],examples=examples,
                            variant=variant,
                            substituted_subroutines=substituted if isinstance(substituted,list) else
                                ['bank8/9 $AC7B action suitability'] if substituted else []))
    count=0; examples=[]
    for side in [0,1,127,128,129,255]:
        for target in range(256):
            m,steps,_=run(0xA944,{'y':3},{0x504:side,0x62B:target})
            assert m.a==ai.opposing_side_marker(side,target)
            count+=1
            if target in [0,128] and side in [0,128]:
                examples.append(dict(current_side=side,target_side=target,marker=m.a))
    save('opposing_side_marker',count,examples)
    examples=[];terrain_examples=[]
    for knowledge in range(256):
        m,steps,_=run(0xA965,values={0x20:0,0x21:0x64,0x6402:knowledge},stop_at=0xA986)
        assert m.memory[0x2A]==ai.knowledge_tier(knowledge)
        if knowledge in [0,39,40,59,60,74,75,84,85,99]:
            examples.append(dict(knowledge=knowledge,tier=m.memory[0x2A]))
    save('knowledge_tier',256,examples)
    examples=[]; cases=[]
    # Exact carry boundary: dx=1,dy=radius=5 adds 1 beyond dx+dy.
    ids=list(range(20)); xs=[10]*20; ys=[10]*20; sides=[0]*20
    xs[1]=11;ys[1]=15;sides[1]=128
    cases.append((0,ids,xs,ys,sides,0,5))
    for _ in range(600):
        ids=[i if rnd.randrange(4) else 255 for i in range(20)]
        xs=[rnd.randrange(32) for i in range(20)]; ys=[rnd.randrange(33) for i in range(20)]
        sides=[rnd.randrange(256) for i in range(20)]
        cases.append((rnd.randrange(20),ids,xs,ys,sides,rnd.randrange(256),rnd.choice([0,1,2,5,10,31,127,128,255])))
    for i,(actor,ids,xs,ys,sides,side,radius) in enumerate(cases):
        values={0x504:side}
        for base,array in [(0x664,ids),(0x600,xs),(0x614,ys),(0x628,sides)]:
            values.update({base+k:v for k,v in enumerate(array)})
        m,steps,_=run(0xA8D3,{'a':radius,'y':actor},values)
        expected=ai.nearby_candidates(actor,ids,xs,ys,sides,side,radius)
        assert m.memory[0x6FC9:0x6FDD]==expected,(i,m.memory[0x6FC9:0x6FDD],expected)
        if i==0:
            assert expected[1]==0x87
            examples.append(dict(actor=[10,10],target=[11,15],radius=5,side_marker=128,
                                 observed_mask=expected[1],note='dx+dy+carry = 1+5+1 = 7; enemy marker -> 0x87'))
    save('nearby_candidates',len(cases),examples)
    examples=[]
    for case in range(400):
        ids=[i if rnd.randrange(5) else 255 for i in range(20)]
        xs=[rnd.randrange(0,7) for _ in range(20)];ys=[rnd.randrange(12,19) for _ in range(20)]
        sides=[rnd.randrange(256) for _ in range(20)];slot=rnd.randrange(20);side=rnd.randrange(256)
        values={0x504:side}
        for base,array in [(0x664,ids),(0x600,xs),(0x614,ys),(0x628,sides)]:
            values.update({base+i:v for i,v in enumerate(array)})
        m,steps,_=run(0xA837,{'y':slot},values)
        expected=ai.orthogonal_neighbors(slot,ids,xs,ys,sides,side)
        assert tuple(m.memory[0x6FDD:0x6FE1])==expected
        if len(examples)<2:examples.append(dict(slot=slot,neighbors=list(expected)))
    save('orthogonal_neighbors',400,examples)
    examples=[];case_count=0
    for fixture in range(220):
        ids=list(range(20));actor=rnd.randrange(20);target=rnd.randrange(20)
        xs=[rnd.randrange(10,15) for _ in range(20)];ys=[rnd.randrange(10,15) for _ in range(20)]
        sides=[rnd.choice([0,128]) for _ in range(20)];side=sides[actor]
        terrain_map={position:rnd.randrange(8) for position in zip(xs,ys)}
        terrain=[terrain_map[x,y] for x,y in zip(xs,ys)]
        reserve=[rnd.choice([0,255]) for _ in range(8)]
        records=[[rnd.randrange(256) for _ in range(12)] for _ in range(237)]
        values={0x6F8C:actor,0x2B:target,0x504:side}
        for base,array in [(0x664,ids),(0x600,xs),(0x614,ys),(0x628,sides),(0x4D8,reserve)]:
            values.update({base+i:v for i,v in enumerate(array)})
        for ident,record in enumerate(records):
            values.update({0x63C0+ident*12+i:v for i,v in enumerate(record)})
        for action in range(16):
            m,steps,_=run(0xAC7B,{'x':action},values,terrain_by_position=terrain_map)
            expected=ai.action_suitability(action,actor,target,ids,records,xs,ys,sides,side,terrain,reserve)
            assert bool(m.p&1)==expected,(fixture,action,expected,m.p)
            assert m.memory[0x2C]==action
            case_count+=1
            if fixture<2:examples.append(dict(action=action,actor=actor,target=target,suitable=expected))
    save('action_suitability',case_count,examples,['bank8 $B6E5 terrain resolver; external classes supplied by RAM fixture'])
    cases=[]
    for counter in [0,1,2,8,20,128,129,255]:
        cases.append(([128]*4+[0]*16,list(range(20)),[100,400,200,300]+[0]*252,counter))
    cases.append(([128]*5+[0]*15,list(range(20)),[10]*256,4))
    for _ in range(220):
        mask=[rnd.choice([0,3,128,132]) for i in range(20)]
        ids=list(range(20)); rnd.shuffle(ids)
        values=[rnd.randrange(65536) for i in range(256)]
        cases.append((mask,ids,values,rnd.choice([0,1,2,8,20,255])))
    examples=[]
    for case,(mask,ids,troops,counter) in enumerate(cases):
        values={0x2F:counter}
        values.update({0x6FC9+i:v for i,v in enumerate(mask)})
        values.update({0x664+i:v for i,v in enumerate(ids)})
        for ident in range(237):
            base=0x63C0+ident*12
            values[base+8]=troops[ident]&255;values[base+9]=troops[ident]>>8
        m,steps,_=run(0xAE93,values=values)
        expected=ai.rank_enemy_candidates(mask,ids,troops,counter)
        assert tuple(m.memory[0x6FC9:0x6FDD])==expected.slots,(case,expected,m.memory[0x6FC9:0x6FDD])
        assert m.memory[0x2F]==expected.remaining_pass_counter
        if case<3 or case==8:
            examples.append(dict(counter=counter,input_officer_values=troops[:5],
                                 observed_slots=list(expected.slots),passes=expected.passes_executed,
                                 remaining_counter=expected.remaining_pass_counter))
    save('rank_enemy_candidates',len(cases),examples)
    rng_table=blob[0x115F5:0x116F5];assert len(set(rng_table))==256
    examples=[]
    for cursor in range(256):
        m,steps,_=run(0xB5D5,{'x':71},{0x6F92:cursor})
        oracle=ai.AiPermutationRng(rng_table,cursor)
        assert (m.a,m.x,m.memory[0x6F92])==(oracle.next_u8(),71,oracle.cursor)
        if cursor in [0,255]: examples.append(dict(cursor=cursor,value=m.a,next_cursor=oracle.cursor,X_preserved=True))
    save('ai_rng_next',256,examples)
    cases=[]
    for tier in [1,3,5,7,9]:
        for budget in [0,3,4,5,6,7,8,9,10,12]:
            for troops in [0,100]:
                for selected in [None,0,1,4,5,6,7,8,9]:
                    mask={i:i==selected for i in range(16)}
                    cases.append((tier,budget,troops,0,mask,0))
    for _ in range(1800):
        cases.append((rnd.choice([1,3,5,7,9]),rnd.randrange(16),rnd.choice([0,1,1023]),
                      rnd.randrange(256),{i:bool(rnd.randrange(2)) for i in range(16)},rnd.randrange(256)))
    examples=[]
    for case,(tier,budget,troops,condition,mask,cursor) in enumerate(cases):
        record=0x63C0+17*12
        values={0x2A:tier,0x2B:1,0x505:budget,0x665:17,record+8:troops&255,
                record+9:troops>>8,0x651:condition,0x6F92:cursor,0x6F8F:85,0x2C:170}
        m,steps,requests=run(0xA9CF,values=values,predicate=lambda i:mask[i])
        rng=ai.AiPermutationRng(rng_table,cursor)
        expected=ai.choose_basic_action(tier,budget,troops,condition,lambda i:mask[i],rng.next_u8,85,170)
        assert bool(m.p&1)==expected.success,(case,expected,m.p)
        assert m.memory[0x2C]==expected.scratch_action,(case,expected,m.memory[0x2C])
        assert m.memory[0x6F8F]==expected.final_status
        assert m.memory[0x6F92]==rng.cursor
        assert tuple(requests)==expected.predicate_requests,(case,requests,expected)
        if len(examples)<10 and expected.success and (expected.scratch_action not in [e['action'] for e in examples]):
            examples.append(dict(tier=tier,resource=budget,target_raw_u16=troops,
                                 action=expected.scratch_action,predicate_requests=requests,
                                 random_samples=list(expected.random_samples),cursor_after=rng.cursor))
    save('choose_basic_action',len(cases),examples,True)
    count=0;examples=[]
    for knowledge in [0,91,92,93,99,255]:
        for packed in range(256):
            record=0x63C0+17*12
            values={0x6F8C:1,0x665:17,record+2:knowledge,record+11:packed}
            m,steps,_=run(0xAAF8,values=values,stop_at=0xAB1F)
            passed=m.pc==0xAB1F
            assert passed==ai.special_ai_gate(knowledge,packed)
            count+=1
            if packed in [0x20,0x30] and knowledge in [91,92]:
                examples.append(dict(knowledge=knowledge,level=packed>>4,passed=passed))
    save('special_ai_gate',count,examples)
    count=0;examples=[]
    for start,required in [(0,3),(11,4),(17,5)]:
        for level in [required-1,required]:
            for officer in range(256):
                m,steps,_=run(0xAC31,{'y':start},{0x36:level,0x22:required,0x2A:officer})
                expected=ai.special_officer_whitelist(officer,level,required,start)
                assert bool(m.p&1)==expected
                count+=1
                if officer==109:examples.append(dict(officer_id=officer,level=level,
                                                     required=required,start_index=start,passed=expected))
    save('special_officer_whitelist',count,examples)
    cases=[]
    for actor in [0,*ai.SPECIAL_OFFICERS,109,236]:
        for level in [2,3,4,5,6]:
            for troops in [0,100]:
                for action in [None,10,11,12,13,14,15]:
                    mask={i:i==action for i in range(16)}
                    cases.append((actor,level,12,troops,0,mask))
    for _ in range(900):
        cases.append((rnd.choice([*ai.SPECIAL_OFFICERS,rnd.randrange(237)]),rnd.randrange(8),
                      rnd.randrange(16),rnd.choice([0,100]),rnd.randrange(256),
                      {i:bool(rnd.randrange(2)) for i in range(16)}))
    examples=[]
    for case,(actor,level,budget,troops,condition,mask) in enumerate(cases):
        record=0x63C0+17*12
        values={0x2A:actor,0x2B:1,0x36:level,0x505:budget,0x665:17,
                record+8:troops&255,record+9:troops>>8,0x651:condition,0x6F8F:85,0x2C:170}
        m,steps,requests=run(0xAB68,values=values,predicate=lambda i:mask[i])
        expected=ai.choose_special_action(actor,level,budget,troops,condition,lambda i:mask[i],85,170)
        assert bool(m.p&1)==expected.success,(case,expected,m.p)
        assert m.memory[0x2C]==expected.scratch_action,(case,expected,m.memory[0x2C])
        assert m.memory[0x6F8F]==85 and tuple(requests)==expected.predicate_requests
        if expected.success and len(examples)<6 and expected.scratch_action not in [e['action'] for e in examples]:
            examples.append(dict(officer_id=actor,level=level,resource=budget,
                                 action=expected.scratch_action,predicate_requests=requests))
    save('choose_special_action',len(cases),examples,True)
    examples=[]
    for case in range(320):
        ids=[i if rnd.randrange(5) else 255 for i in range(20)]
        actor=rnd.randrange(20); ids[actor]=actor
        records=[[rnd.randrange(100) for _ in range(12)] for _ in range(237)]
        for record in records:
            troops=rnd.choice([0,1,100,1023]);record[8]=troops&255;record[9]=troops>>8
        xs=[rnd.randrange(8,19) for _ in range(20)]
        ys=[rnd.randrange(8,20) for _ in range(20)]
        sides=[rnd.choice([0,128]) for _ in range(20)]
        current_side=sides[actor];conditions=[rnd.randrange(16) for _ in range(20)]
        budget=rnd.randrange(13);counter=rnd.choice([0,1,2,5,20,255]);cursor=rnd.randrange(256)
        eligible=[[bool(rnd.randrange(2)) for _ in range(16)] for _ in range(20)]
        values={0x6F8C:actor,0x504:current_side,0x505:budget,0x2F:counter,0x6F92:cursor,
                0x6F8D:170,0x6F8E:187,0x6F8F:85,0x2C:204}
        for base,array in [(0x664,ids),(0x600,xs),(0x614,ys),(0x628,sides),(0x650,conditions)]:
            values.update({base+i:v for i,v in enumerate(array)})
        for ident,record in enumerate(records):
            values.update({0x63C0+ident*12+i:v for i,v in enumerate(record)})
        m,steps,requests=run(0xA95C,values=values,predicate=lambda slot,code:eligible[slot][code],predicate_by_slot=True)
        rng=ai.AiPermutationRng(rng_table,cursor)
        expected=ai.plan_basic_tactic(actor,ids,records,xs,ys,sides,current_side,conditions,
                                     budget,counter,lambda slot,code:eligible[slot][code],rng.next_u8,
                                     170,187,85,204)
        assert bool(m.p&1)==expected.success,(case,expected,m.p)
        assert (m.memory[0x6F8D],m.memory[0x6F8E],m.memory[0x6F8F],m.memory[0x2C],m.memory[0x2F])==(
            expected.action,expected.target_slot,expected.final_status,expected.scratch_action,expected.final_pass_scratch)
        assert tuple(m.memory[0x6FC9:0x6FDD])==expected.candidate_slots
        assert tuple(requests)==expected.predicate_requests and m.memory[0x6F92]==rng.cursor
        if len(examples)<4:
            examples.append(dict(actor_slot=actor,knowledge=records[actor][2],resource=budget,
                                 initial_sort_counter=counter,candidate_slots=list(expected.candidate_slots),
                                 action=expected.action,target=expected.target_slot,status=expected.final_status,
                                 success=expected.success,instructions=steps))
        if case<160:
            terrain_map={position:rnd.randrange(6) for position in zip(xs,ys)}
            terrain=[terrain_map[x,y] for x,y in zip(xs,ys)]
            reserve=[rnd.choice([0,255]) for _ in range(8)]
            values.update({0x4D8+i:v for i,v in enumerate(reserve)})
            m,steps,requests=run(0xA95C,values=values,terrain_by_position=terrain_map)
            rng=ai.AiPermutationRng(rng_table,cursor)
            def eligibility(slot,code):
                return ai.action_suitability(code,actor,slot,ids,records,xs,ys,sides,current_side,terrain,reserve)
            expected=ai.plan_basic_tactic(actor,ids,records,xs,ys,sides,current_side,conditions,
                                         budget,counter,eligibility,rng.next_u8,170,187,85,204)
            assert bool(m.p&1)==expected.success
            assert (m.memory[0x6F8D],m.memory[0x6F8E],m.memory[0x6F8F],m.memory[0x2C],m.memory[0x2F])==(
                expected.action,expected.target_slot,expected.final_status,expected.scratch_action,expected.final_pass_scratch)
            assert tuple(m.memory[0x6FC9:0x6FDD])==expected.candidate_slots
            assert tuple(requests)==expected.predicate_requests and m.memory[0x6F92]==rng.cursor
            if len(terrain_examples)<4:
                terrain_examples.append(dict(actor=actor,resource=budget,action=expected.action,
                                             target=expected.target_slot,status=expected.final_status,
                                             success=expected.success,instructions=steps))
    save('plan_basic_tactic',320,examples,True)
    save('plan_basic_tactic',160,terrain_examples,['bank8 $B6E5 terrain resolver; external classes supplied by RAM fixture'],
         'whole caller pipeline including actual $AC7B predicates and $A837 neighbor discovery')
    payload=dict(status='passed',rom_sha256=ai.ROM_SHA256,oracle='py65 1.2.0 executes exact original ROM 6502 bytes',
                 random_seed=0xA9CF,case_count=sum(r['case_count'] for r in results),results=results,
                 limitations=['CPU-only initialized RAM fixtures; not a complete NES gameplay simulation.',
                              '$AC7B is substituted only in controlled-predicate chooser fixtures. Terrain-fixture tests execute actual $AC7B but substitute its bank-backed $B6E5 resolver. Every result lists its substitutions.',
                              'No interrupt/PPU/APU/mapper timing claim; RNG cursor is controlled in each fixture.',
                              'Action number meanings and total UI command costs remain pending a UI/action-table connection.',
                              'Rank routine pass count depends on caller RAM $002F; partial ordering and unstable equal-key swaps are preserved.'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f"Passed {payload['case_count']} AI cases; wrote {a.output}")
    for item in results: print(f"  {item['name']}: {item['case_count']} cases")

if __name__=='__main__':main()
