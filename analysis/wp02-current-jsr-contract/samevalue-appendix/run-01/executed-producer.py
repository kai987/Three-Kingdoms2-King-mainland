#!/usr/bin/env python3
"""Four predeclared controlled original-CPU provenance counterexamples."""
from pathlib import Path
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
OUT=ROOT/'analysis/wp02-current-jsr-contract';DEST=OUT/'samevalue-appendix'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def prepare():
    assert not DEST.exists();DEST.mkdir()
    cases=[dict(key=f'samevalue/{call:04X}/{sp}',call_pc=call,sp=sp,index=3 if call==0xA09E else 7,
                registers=dict(pc=call,a=3 if call==0xA09E else 7,x=90,y=137,p=0xA5,sp=sp))
           for call in(0xA09E,0xACAB)for sp in(0,253)]
    save(DEST/'plan.json',dict(schema='wp02-samevalue-external-write-plan-v1',cases=cases,case_count=4,
        initial='Original controlled base RAM/SRAM and PRG[5,8,9,31], no Native capture.',
        intervention='After actual original JSR, host rewrites high stack byte to EXACTLY the byte just pushed; last writer becomes external.',
        expected='Numeric raw return/selected ROM values remain correct, PLA high last-writer external, current-frame premise false.',
        boundary='After real B533 JMP, before target first opcode. No RTS result.',Source_cases=0,Native_runs=0,
        dependency_runner_sha256=sha(ROOT/'scripts/verify_wp02_current_jsr.py'),producer_sha256=sha(Path(__file__).resolve())))
    print(json.dumps(dict(status='declared_before_appendix_CPU',cases=4,plan_sha256=sha(DEST/'plan.json'))))
def execute(rom_path):
    from py65.devices.mpu6502 import MPU
    from verify_wp02_current_jsr import ContractBus,regs,BASE_RAM,BASE_SRAM,off
    plan=json.loads((DEST/'plan.json').read_text())
    assert sha(Path(__file__).resolve())==plan['producer_sha256']
    assert sha(ROOT/'scripts/verify_wp02_current_jsr.py')==plan['dependency_runner_sha256']
    run=DEST/'run-01';assert not run.exists();run.mkdir()
    rom=rom_path.read_bytes();assert hashlib.sha256(rom).hexdigest()=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
    save(run/'execution-inputs.json',dict(plan_sha256=sha(DEST/'plan.json'),producer_sha256=sha(Path(__file__).resolve()),
        dependency_runner_sha256=plan['dependency_runner_sha256'],original_main_execution_inputs_sha256=sha(OUT/'run-01/execution-inputs.json'),
        Source_cases=0,Native_runs=0,actual_capture_origin=None))
    (run/'executed-producer.py').write_bytes(Path(__file__).read_bytes());(run/'executed-plan.json').write_bytes((DEST/'plan.json').read_bytes())
    result=[]
    for spec in plan['cases']:
        call=spec['call_pc'];bus=ContractBus(rom,5);bus.generation=0;bus.primary_call=call;cpu=MPU(memory=bus)
        for k,v in spec['registers'].items():setattr(cpu,k,v)
        before_ram=bytes(bus.ram);before_sram=bytes(bus.sram);trace=[];pushes=None;mutation=None
        case=run/spec['key'].replace('/','-');case.mkdir()
        (case/'initial-ram.bin').write_bytes(before_ram);(case/'initial-sram.bin').write_bytes(before_sram)
        for n in range(32):
            pc=cpu.pc;sp=cpu.sp;bus.pc=pc;bus.selected_context=None;bus.pla_context=None
            assert 0x8000<=pc<=0xFFFF
            pre=regs(cpu);write_start=len(bus.writes);read_start=len(bus.selected_reads);pla_start=len(bus.pla_reads)
            if pc in (0xB525,0xB52B):
                pointer=bus.peek(0x21)|(bus.peek(0x22)<<8);ea=(pointer+cpu.y)&65535
                bus.selected_context=dict(PC=pc,SP=sp,live21_22=pointer,Y=cpu.y,logical_effective_address=ea,generation=0)
            if pc in (0xB51D,0xB521):bus.pla_context=dict(PC=pc,SP_before=sp,stack_address=0x100+((sp+1)&255),generation=0)
            opcode=bus.peek(pc);cpu.step()
            trace.append(dict(before=pre,opcode=opcode,after=regs(cpu),actual_CPU_writes=bus.writes[write_start:],
                              actual_selected_reads=bus.selected_reads[read_start:],actual_PLA_reads=bus.pla_reads[pla_start:]))
            if pc==call:
                assert bytes(rom[off(8,call):off(8,call)+3])==bytes.fromhex('2017b5')
                pushes=bus.writes[write_start:];assert[(x['address'],x['value'])for x in pushes]==[(0x100+sp,(call+2)>>8),(0x100+((sp-1)&255),(call+2)&255)]
                address=pushes[0]['address'];value=bus.peek(address)
                bus.fixture(address,value,'post-JSR external SAME-VALUE high-byte rewrite; provenance premise violated')
                mutation=bus.mutations[-1];assert mutation['before']==mutation['value']==(call+2)>>8
            if pc==0xB533:break
        else:raise AssertionError('Appendix budget exhausted')
        assert len(trace)==16 and len(bus.selected_reads)==len(bus.pla_reads)==2 and pushes is not None
        assert bus.pla_reads[0]['last_writer']==dict(kind='primary_JSR',generation=0,PC=call)
        assert bus.pla_reads[1]['last_writer']['kind']=='disclosed_fixture_mutation'
        assert[read['value']for read in bus.pla_reads]==[(call+2)&255,(call+2)>>8]
        assert all(x['live21_22']==call+2 for x in bus.selected_reads)
        ys=[(2*spec['index']+1)&255,(2*spec['index']+2)&255]
        values=[rom[off(8,call+2+y)]for y in ys]
        assert[(x['logical_effective_address'],x['value'])for x in bus.selected_reads]==[(call+2+y,v)for y,v in zip(ys,values)]
        assert cpu.pc==values[0]|(values[1]<<8) and cpu.sp==spec['sp']and cpu.y==137 and cpu.x==90 and cpu.a==values[1]
        assert cpu.p==((spec['registers']['p']&~0x83)|128)
        assert list(bus.ram[0x20:0x25])==[137,(call+2)&255,(call+2)>>8,*values]
        allowed=set(range(0x20,0x25))|{x['address']for x in pushes}
        assert all(value==before_ram[i]for i,value in enumerate(bus.ram)if i not in allowed)
        assert bytes(bus.sram)==before_sram and bus.banks==[5,8,9,31]
        (case/'final-ram.bin').write_bytes(bytes(bus.ram));(case/'final-sram.bin').write_bytes(bytes(bus.sram))
        save(case/'actual-trace.json',trace)
        result.append(dict(case=spec['key'],status='passed',original_CPU_instructions=16,
            actual_JSR_pushes=pushes,external_same_value_mutation=mutation,actual_PLA_reads=bus.pla_reads,
            selected_reads=bus.selected_reads,numeric_raw_word_correct=True,selected_ROM_reads_correct=True,
            current_frame_provenance_premise_valid=False,auxiliary_hit=False,final_registers=regs(cpu),
            boundary='after_B533_JMP_before_target_first_opcode',actual_caller_RTS=False,Source_cases=0,Native_runs=0))
    save(run/'validation.json',dict(schema='wp02-samevalue-appendix-validation-v1',status='passed_all4',
        cases=result,controlled_CPU_parent_cases=4,actual_JSR_executions=4,original_CPU_instructions=64,
        invalid_current_frame_provenance_cases=4,numeric_and_ROM_read_success_cases=4,
        Source_cases=0,Native_runs=0,plan_sha256=sha(DEST/'plan.json')))
    print(json.dumps(dict(status='passed_all4',original_CPU_instructions=64,provenance_invalid_despite_correct_numeric_word=4)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','execute'));p.add_argument('--rom',type=Path);a=p.parse_args()
    prepare()if a.mode=='prepare'else execute(a.rom)
