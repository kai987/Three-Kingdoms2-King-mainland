#!/usr/bin/env python3
"""Differential original6502 oracles for independently readable domestic rules."""
from pathlib import Path
from collections import Counter
import sys,argparse,json,hashlib,random
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered import domestic_ai as model
from source.recovered.battle_state_machine import Registers
from verify_terrain_rules import ActualHooks

TURN_BARRIERS={0xe000:'system reset',0xe57f:'PPU scene transition',0xe673:'frame-dependent scene effect',0xe683:'frame-dependent scene effect',0xe693:'frame-dependent scene effect',0xecee:'NMI/frame barrier'}
class ValidationBarrier(Exception):pass
class TurnHooks(ActualHooks):
    """Execute original outsidehelper only until an explicit frame/reset boundary."""
    def __call__(self,context,target,return_pc,kind):
        r=context.registers;c=MPU(memory=self.bus,pc=target)
        for name in('a','x','y','sp','p'):setattr(c,name,getattr(r,name))
        self.bus.cpu=c;stop=return_pc if return_pc is not None else 0x0200
        for count in range(100000):
            if c.pc==stop or c.pc in TURN_BARRIERS:break
            self.bus.pc=c.pc
            if c.disassemble[self.bus.peek(c.pc)][0]=='???':raise RuntimeError(f'Unknown turnhelper opcode{c.pc:04X}')
            c.step()
        else:raise RuntimeError(f'Turnhelper{target:04X} exceededbound at{c.pc:04X}')
        for name in('a','x','y','sp','p','pc'):setattr(r,name,getattr(c,name))
        self.calls.append({'target':target,'kind':kind,'instructions':count,'barrier':TURN_BARRIERS.get(c.pc)})
        if c.pc in TURN_BARRIERS:raise ValidationBarrier(TURN_BARRIERS[c.pc])

def fresh(rom,pair=10):
    b=Bus(rom,'alternating');b.ram[:]=(ROOT/'analysis/phase5/runtime/city-info/menu-0-ram.bin').read_bytes()
    b.sram[:]=(ROOT/'analysis/phase5/runtime/city-info/menu-0-sram.bin').read_bytes()
    b.banks=[2,pair,pair+1,31];b.bank_initialized=[True]*4;b.protect=0x4c
    b.ram[0xe1:0xe4]=bytes([0x22,0x20+pair,0x21+pair]);b.ram[0x1fe:0x200]=bytes([255,1]);b[0x7c]=0
    return b

def execute(b,entry,stop=0x0200,registers=None,limit=1000000,min_steps=0):
    c=MPU(memory=b,pc=entry);c.sp=0xfd;c.p=c.UNUSED;b.cpu=c
    for name,value in(registers or{}).items():setattr(c,name,value)
    stops={stop}if isinstance(stop,int)else set(stop)
    for i in range(limit):
        if i>=min_steps and c.pc in stops:return c,i
        b.pc=c.pc;b.step_no=i
        if c.disassemble[b.peek(c.pc)][0]=='???':raise RuntimeError(f'Original unknown opcode at{c.pc:04X}')
        c.step()
    raise RuntimeError(f'Original budget expired entry{entry:04X} PC{c.pc:04X}')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/domestic-ai');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==model.ROM_SHA256
    rng=random.Random(0x507);counts=Counter();failures=[];coverage=set();ir_cases=[]
    for ruler in range(7):
        for officer in range(237):
            b=fresh(rom);b[0x6f03]=ruler;c,n=execute(b,0xc66f,registers={'a':officer})
            assert c.a==model.recruitment_probability(ruler,officer);counts['recruitment_probability']+=1
    for i in range(512):
        b=fresh(rom);city=i%30;b[0x36]=city;b[0x37]=i%7;addr=model.city_address(city)
        b[addr]=(b[addr]&248)|(i%7)
        roster=[rng.choice([255,rng.randrange(237)])for _ in range(10)]
        b.sram[addr-0x6000+17:addr-0x6000+27]=bytes(roster)
        loyalties=[rng.choice([0,99,100,101,255,rng.randrange(256)])for _ in range(237)]
        virtues=[rng.randrange(256)for _ in range(237)]
        for officer in range(237):b[model.officer_address(officer)+3]=loyalties[officer];b[model.officer_address(officer)+4]=virtues[officer]
        expected=model.choose_governor(roster,loyalties,virtues);c,n=execute(b,0xc9a5)
        assert list(b.sram[addr-0x6000+17:addr-0x6000+27])==expected['roster'],('governor',i,expected);counts['governor_selection']+=1
    for budget in [0,1,2,4,5,7,10,127,128,254,255]:
        for cost in range(0,11):
            for entry,variant in[(0xd12d,'continue_cycle'),(0xd152,'task'),(0xd165,'nested1'),(0xd178,'nested2'),(0xd18d,'nested3')]:
                b=fresh(rom);b[0x6f5d]=budget
                if variant=='continue_cycle':stops=[0xd138]
                elif variant=='task':stops=[0xd15d]
                elif variant=='nested1':stops=[0xd170]
                elif variant=='nested2':stops=[0xd183]
                else:stops=[0xd198]
                c,n=execute(b,entry,stop=stops,registers={'a':cost})
                expected=model.consume_ai_budget(budget,cost,variant)
                assert b[0x6f5d]==expected['remaining']and bool(c.p&1)==(budget>=cost)
                counts['budget_subtraction_boundaries']+=1
    for year in [0,89,90,99,255]:
        for month in range(12):
            for turn in range(7):
                b=fresh(rom,25);b[0x6f00]=year;b[0x6f01]=month;b[0x6f04]=turn
                execute(b,0xa046,stop=0xa06b);expected=model.calendar_step(year,month,turn)
                assert(b[0x6f00],b[0x6f01],b[0x6f04])==(expected['year'],expected['month'],expected['turn'])
                counts['calendar_valid_domain']+=1
    for i in range(256):
        b=fresh(rom,25);values=bytes((i+j)&255 for j in range(28))
        for ruler in range(7):b.sram[0xf07+8*ruler+4:0xf07+8*ruler+8]=values[4*ruler:4*ruler+4]
        execute(b,0xa209)
        actual=bytes(b[0x6f0b+8*ruler+j]for ruler in range(7)for j in range(4))
        assert actual==model.decay_diplomacy_nibbles(values);counts['diplomacy_nibble_decay']+=1
    for i in range(256):
        b=fresh(rom);difficulty=i%3;ruler=i%7;denominator=rng.randrange(1,121);numerator=rng.randrange(31)
        b[0x6f02]=difficulty;b[0x6f03]=ruler
        # Start after the graph aggregate call; supply its true scratch results.
        b[0x37]=denominator;b[0x38]=numerator
        row=8*difficulty+ruler
        for address,cpu in[(0x6f5f,0xa133),(0x6f60,0xa14b),(0x6f61,0xa163)]:b[address]=rom[0x14010+cpu-0xa000+row]
        execute(b,0xa073,stop=0xa0d2)
        expected=model.initial_strategy_weights(rom,difficulty,ruler,denominator,numerator)
        assert [b[0x6f5f],b[0x6f60],b[0x6f61]]==expected['weights'],('weights',i,expected)
        counts['strategic_weight_corrections']+=1
    strategy_branches=Counter()
    for i in range(512):
        b=fresh(rom);weights=rng.choice([(13,3,4),(0,1,1),(1,0,1),(5,5,5),(30,30,30),(0,0,1)])
        b[0x6f5f],b[0x6f60],b[0x6f61]=weights;b[0x52]=i&255
        clone=fresh(rom);clone.ram[:]=b.ram;sample_rng=model.DomesticRandom(clone,rom)
        sampled=sample_rng.below(sum(weights)&255,low_nibble=True);branch=model.weighted_branch(weights,sampled)
        c,n=execute(b,0xa19c,stop=[0xa1c5,0xb49c,0xbec7])
        assert c.pc==[0xa1c5,0xb49c,0xbec7][branch]and b[0x52]==clone[0x52]
        counts['three_strategy_low_nibble_choices']+=1;strategy_branches[branch]+=1
    for i in range(256):
        b=fresh(rom);ruler=i%7;b[0x6f03]=ruler;model.put_word(b,0xee,0x6f07+8*ruler)
        for j in range(4):b[0x6f0b+8*ruler+j]=rng.choice([0,1,15,16,240,255])
        for city in range(30):
            addr=model.city_address(city);b[addr]=(b[addr]&248)|rng.randrange(8)
            roster=[rng.randrange(237)for _ in range(rng.randrange(11))];roster+=([255]*(10-len(roster)))
            b.sram[addr-0x6000+17:addr-0x6000+27]=bytes(roster)
            model.put_word(b,addr+2,rng.choice([9999,10000,65535]));model.put_word(b,addr+4,rng.choice([9999,10000,65535]))
        clone=fresh(rom);clone.ram[:]=b.ram;clone.sram[:]=b.sram
        expected=model.choose_attack_target(clone,rom,ruler);c,n=execute(b,0xa240)
        assert(b[0x37],b[0x38],b[0x39],b[0x3a])==(expected['enemy_prefix_officers'],expected['target_city'],expected['own_prefix_officers'],expected['source_city']),('attack target',i,expected)
        assert b.sram==clone.sram
        counts['military_target_scanning']+=1
    for i in range(256):
        b=fresh(rom);ruler=i%7;city=i%30;address=model.city_address(city);b[0x6f03]=ruler;b[0x3b]=city;b[0x44]=i&1
        leader=b[0x6f07+8*ruler]
        roster=[rng.choice([255,leader,rng.randrange(237)])for _ in range(10)]
        b.sram[address-0x6000+17:address-0x6000+27]=bytes(roster)
        martial=[rng.randrange(256)for _ in range(237)];loyalties=[rng.randrange(256)for _ in range(237)]
        for officer in range(237):b[model.officer_address(officer)+1]=martial[officer];b[model.officer_address(officer)+3]=loyalties[officer]
        expected=model.choose_reinforcement_officer(roster,martial,loyalties,leader,i&1);c,n=execute(b,0xa3dc,stop=0xa430)
        assert b[0x26]==(17+expected['slot']if expected['slot']is not None else 0)and b[0x25]==expected['score']
        if expected['slot']is not None:assert b[0x3c]==expected['officer']
        counts['reinforcement_officer_selection']+=1
    for i in range(512):
        b=fresh(rom);city=i%30;address=model.city_address(city);b[0x6f5e]=city
        roster=[rng.choice([255,rng.randrange(237)])for _ in range(10)];available=[rng.randrange(2)for _ in range(10)]
        b.sram[address-0x6000+17:address-0x6000+27]=bytes(roster);b.sram[0xf73:0xf7d]=bytes(available)
        values=[rng.choice([0,50,69,70,79,80,100,255,rng.randrange(256)])for _ in range(237)];loyalty=bool(i&1)
        for officer in range(237):b[model.officer_address(officer)+(3 if loyalty else 2)]=values[officer]
        expected=model.choose_lowest_officer(roster,values,available,loyalty);c,n=execute(b,0xc248 if loyalty else 0xc2eb)
        assert b[0x23]==(255 if expected['officer']is None else expected['officer'])and list(b.sram[0xf73:0xf7d])==expected['available']
        counts['lowest_officer_selection']+=1
    for i in range(384):
        b=fresh(rom,25);difficulty=i%3;b[0x6f02]=difficulty
        cities=[]
        for city in range(30):
            addr=model.city_address(city);raw=bytearray(b.sram[addr-0x6000:addr-0x6000+32])
            for offset in[2,4,6,8,14]:model.put_word(raw,offset,rng.choice([0,999,9999,10000,32767,65535,rng.randrange(65536)]))
            raw[11]=rng.choice([0,50,51,70,71,80,81,90,91,99,100,127,255]);cities.append(bytes(raw));b.sram[addr-0x6000:addr-0x6000+32]=raw
        kind='gold'if i&1 else'grain';execute(b,0xa429 if kind=='gold'else 0xa5ee)
        for city,raw in enumerate(cities):
            expected=model.seasonal_income(raw,difficulty,kind);address=model.city_address(city)+(2 if kind=='gold'else 4)
            assert model.word(b,address)==expected['value'],('seasonal income',i,city,expected)
        counts['seasonal_collection_30_city_cases']+=1
    development_branches=Counter()
    for i in range(768):
        b=fresh(rom);ruler=i%7;b[0x6f03]=ruler;b[0x6f02]=i%3;b[0x6f01]=i%12;b[0x52]=i&255
        b[0x6f62]=i%3;b[0x6f83+ruler]=(i//3)%30;b[0x6f5d]=[0,1,4,5,6,10,30][i%7]
        for city in range(30):
            addr=model.city_address(city);b[addr]=(b[addr]&248)|(ruler if city%4==i%4 else 7)
            for offset in[2,4,6,8,14]:model.put_word(b,addr+offset,rng.choice([0,9,10,29,30,100,999,9999,65535]))
            b[addr+10]=rng.choice([0,98,99,255]);b[addr+11]=rng.choice([0,99,100,255])
        clone=fresh(rom);clone.ram[:]=b.ram;clone.sram[:]=b.sram
        expected=model.domestic_development_once(clone,rom)
        c,n=execute(b,0xbec7,stop=[0xbec7,0xc1e0,0x0200],min_steps=1)
        assert clone.sram==b.sram,('development SRAM',i,expected,[(j,b.sram[j],clone.sram[j])for j in range(8192)if b.sram[j]!=clone.sram[j]][:10])
        for address in[0x52,0x6f62,0x6f5b,0x6f5d,0x6f5e,0x6f8b,0x6f8d,0x6f83+ruler]:assert clone[address]==b[address],('development RAM',i,hex(address),expected,clone[address],b[address])
        expected_pc=0xc1e0 if expected['next_stage']=='officer_or_equipment'else 0x0200 if expected['next_stage']=='turn_end'else 0xbec7
        assert c.pc==expected_pc,('development destination',i,expected,c.pc)
        counts['complete_development_iteration']+=1;development_branches[expected.get('kind',expected['next_stage'])]+=1
    program=json.loads((a.out/'program.json').read_text())
    for entry in[0xa00f,0xa042,0xc66f,0xc9a5,0xd304,0xd0e1,0xd4cb,0xd583]:
        for i in range(24):
            b=fresh(rom);ruler=i%7;b[0x6f03]=ruler;b[0x6f02]=i%3;b[0x6f8b]=255;b[0x6f5b]=0;b[0x6f5d]=30
            pointer=0x6f07+8*ruler;model.put_word(b,0xee,pointer)
            for city in range(30):
                addr=model.city_address(city);b[addr]=(b[addr]&248)|rng.randrange(8)
            # Seed equal scratch inputs on both sides; no original opcode patch.
            b[0x36]=i%30
            registers={'a':i%237,'x':i%30,'y':(i*7)%30}
            if entry==0xc9a5:
                b[0x37]=ruler;b[model.city_address(i%30)]=ruler
            if entry==0xd583:
                for j in range(128):b[0x580+j]=rng.randrange(256)
            clone=fresh(rom);clone.ram[:]=b.ram;clone.sram[:]=b.sram;clone.banks[:]=b.banks
            adapter=ActualHooks(clone);machine=model.DomesticAIControl(clone,adapter,program)
            try:
                c,n=execute(b,entry,registers=registers)
                effect=machine.run_entry(entry,registers=Registers(**registers),max_instructions=1000000);got=machine.registers
                assert all(getattr(got,k)==getattr(c,k)for k in['a','x','y','sp','p','pc']),('register mismatch',vars(got),vars(c))
                assert clone.ram==b.ram and clone.sram==b.sram and clone.banks==b.banks,('RAM/mapper mismatch',[(j,b.ram[j],clone.ram[j])for j in range(2048)if b.ram[j]!=clone.ram[j]][:8])
                ir_cases.append({'entry':entry,'index':i,'instructions':n,'external_calls':adapter.calls});coverage.update(machine.executed)
            except Exception as e:failures.append({'entry':entry,'index':i,'error':str(e)[:1200]})
    for i in range(63):
        b=fresh(rom);ruler=i%7;b[0x6f03]=ruler;b[0x6f02]=(i//7)%3
        b[0x6f8b]=0;b[0x6f5b]=0;b[0x6f5d]=[5,10,30][i//21]
        b[0x6f62]=0;model.put_word(b,0xee,0x6f07+8*ruler)
        b[0x52]=(i*13)&255;b[0x54]=(i*23)&255;b[0x55]=(i*43)&255
        for tick in range(2):
            clone=fresh(rom);clone.ram[:]=b.ram;clone.sram[:]=b.sram;clone.banks[:]=b.banks
            adapter=ActualHooks(clone);machine=model.DomesticAIControl(clone,adapter,program)
            try:
                c,n=execute(b,0xa00f);machine.step(max_instructions=1000000);got=machine.registers
                assert all(getattr(got,k)==getattr(c,k)for k in['a','x','y','sp','p','pc']),('full AI registers',vars(got))
                assert clone.ram==b.ram and clone.sram==b.sram and clone.banks==b.banks,('full AI memory',[(j,b.ram[j],clone.ram[j])for j in range(2048)if b.ram[j]!=clone.ram[j]][:8])
                ir_cases.append({'entry':0xa00f,'index':i,'tick':tick,'full_original_city_fixture':True,'instructions':n,'external_calls':adapter.calls});coverage.update(machine.executed)
            except Exception as e:failures.append({'entry':0xa00f,'index':i,'tick':tick,'error':str(e)[:1200]});break
    turn_program=json.loads((a.out/'turn-program.json').read_text());turn_catalog=json.loads((a.out/'turn-controllers.json').read_text())
    turn_cases=[];turn_failures=[];turn_coverage=set();turn_terminations=Counter()
    for controller in turn_catalog['controllers']:
        for sub in range(controller['count']):
            for button in[0,1,2]:
                for idle in[0,255]:
                    b=fresh(rom,25);b[0x401]=sub;b[0x402]=0;b[0x400]=0 if controller['name']=='calendar'else 10 if controller['name']=='turn_events'else 9
                    b[0x300]=b[0x304]=idle;b[0x81]=button;b[0x7c]=0;b[0x7e]=0;b[0x140]=0;b[0x4a0]=0
                    b[0x6f03]=2;b[0x6f04]=2;b[0x6f05]=3;b[0x6f06]=0;b[0x6f8b]=255;b[0x40c]=0
                    b[0x470]=b[0x471]=b[0x472]=0;b[0x473]=0;b[0x478]=0;b[0x40b]=131;b[0x40a]=2;b[0x40e]=11
                    model.put_word(b,0xee,0x6f17)
                    clone=fresh(rom,25);clone.ram[:]=b.ram;clone.sram[:]=b.sram;clone.banks[:]=b.banks
                    adapter=TurnHooks(clone);machine=model.RulerTurnControl(clone,adapter,turn_program)
                    try:
                        expected,n=execute(b,controller['entry'],stop=[0x0200,*TURN_BARRIERS])
                        try:effect=machine.run_entry(controller['entry'],max_instructions=1000000);boundary=None
                        except ValidationBarrier as barrier:boundary=str(barrier)
                        got=machine.registers
                        assert all(getattr(got,k)==getattr(expected,k)for k in['a','x','y','sp','p','pc']),('turnregisters',vars(got),vars(expected))
                        assert clone.ram==b.ram and clone.sram==b.sram and clone.banks==b.banks,('turnmemory',[(j,b.ram[j],clone.ram[j])for j in range(2048)if b.ram[j]!=clone.ram[j]][:8])
                        status='returned'if expected.pc==0x0200 else'validated_to_explicit_boundary'
                        if expected.pc!=0x0200:assert boundary==TURN_BARRIERS[expected.pc]
                        turn_cases.append({'controller':controller['name'],'substate':sub,'button':button,'job_value':idle,'status':status,'boundary':boundary,'final_pc':expected.pc,'instructions':n,'after':[b[0x400],b[0x401],b[0x402]],'external_calls':adapter.calls})
                        turn_coverage.update(machine.executed);turn_terminations[status]+=1
                    except Exception as e:turn_failures.append({'controller':controller['name'],'substate':sub,'button':button,'idle':idle,'error':str(e)[:1500]})
    failures.extend(turn_failures)
    result={'rom_sha256':model.ROM_SHA256,'status':'passed'if not failures else'partial_with_explicit_failures','semantic_case_count':sum(counts.values()),'counts':dict(counts),'strategy_branches':dict(strategy_branches),'development_branches':dict(development_branches),'control_ir_case_count':len(ir_cases),'control_ir_failed_count':len(failures),'control_instruction_total':len(program['instructions']),'control_dynamic_instruction_coverage':len(coverage),'control_fixtures':ir_cases,'failures':failures,'scope':'Independent pure rules compared to original6502; bounded controller uses actual original outside-helper oracle only in verification. No patched ROM or silently completed dependency.'}
    result.update(turn_controller_case_count=len(turn_cases),turn_controller_failed_count=len(turn_failures),turn_controller_terminations=dict(turn_terminations),turn_instruction_total=len(turn_program['instructions']),turn_dynamic_instruction_coverage=len(turn_coverage),turn_fixtures=turn_cases,turn_failures=turn_failures)
    result['case_count']=result['semantic_case_count']+result['control_ir_case_count']+result['turn_controller_case_count']
    (a.out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in['control_fixtures','turn_fixtures']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
