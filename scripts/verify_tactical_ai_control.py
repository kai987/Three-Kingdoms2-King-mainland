#!/usr/bin/env python3
"""Original-ROM CPU comparison for the independent tactical cooperation graph."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.tactical_ai_control import TacticalAIControl,TacticalDispatch,Registers,InvalidState,ROM_SHA256
from source.recovered.mapped_memory import PrgDataMemory

def native_bus(rom,ram,sram,banks=(6,8,9,31)):
    b=Bus(rom,'alternating');b.ram[:]=ram;b.sram[:]=sram;b.banks[:]=banks;b.bank_initialized=[True]*4;b.protect=0x4c;return b
def native_cpu(bus,r,entry,stop,limit=2000000):
    c=MPU(memory=bus);bus.cpu=c
    for k,v in vars(r).items():setattr(c,k,v)
    c.pc=entry;visited=set()
    for count in range(limit):
        if count and c.pc==stop:return c,count,visited
        if c.disassemble[bus.peek(c.pc)][0]=='???':raise RuntimeError(f'Original unknown opcode at ${c.pc:04X}')
        visited.add(c.pc);bus.pc=c.pc;bus.step_no=count;c.step()
    raise RuntimeError(f'Original instruction budget at ${c.pc:04X}, entry ${entry:04X}')
def regs(c):return {k:getattr(c,k)for k in ['a','x','y','sp','p','pc']}
def diff(a,b):return [(i,a[i],b[i])for i in range(len(a))if a[i]!=b[i]][:12]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase7/controller');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
    program=json.loads((a.out/'program.json').read_text());catalog=json.loads((a.out/'state-catalog.json').read_text())
    counts=Counter();statuses=Counter();failures=[];coverage=set();native_locations=set();fixtures=[];rng=random.Random(0x708)
    def fresh():
        ram=bytearray(base_ram);sram=bytearray(base_sram)
        ram[0xde:0xe4]=bytes([0x26,0x28,0x29,0x26,0x28,0x29]);ram[0x1fe:0x200]=bytes([255,1])
        sram[0xf8b]=255;sram[0xf94:0xf97]=bytes(3)
        return ram,sram
    def check(group,good,details):
        counts[group]+=1
        if not good:failures.append({'group':group,**details})
    def compare(group,entry,ram,sram,r=None,seed=True,return_pc=0x200,label=None):
        r=r or Registers();src=PrgDataMemory(rom,ram,sram,banks=[6,8,9,31]);ref=native_bus(rom,ram,sram)
        m=TacticalAIControl(src,program=program)
        try:
            result=m.run_entry(entry,registers=Registers(**vars(r)),seed_return=seed,return_pc=return_pc,max_instructions=1000000)
            if result['status']!='returned':raise RuntimeError(f'Model {result["status"]}: {result.get("dependency",result.get("budget_pc"))}')
            c,n,visited=native_cpu(ref,r,entry,return_pc);coverage.update(m.executed);native_locations.update(visited)
            good=vars(m.registers)==regs(c)and src.ram==ref.ram and src.sram==ref.sram and src.banks==ref.banks
            details={'entry':entry,'label':label,'status':result['status'],'native_instructions':n,'ir_instructions':len(m.executed),'before':result['before'],'after':result['after'],
                     'model_registers':vars(m.registers),'rom_registers':regs(c),'ram_diff':diff(src.ram,ref.ram),'sram_diff':diff(src.sram,ref.sram),'model_banks':src.banks,'rom_banks':ref.banks}
            check(group,good,details);statuses[group+':'+result['status']]+=1
            if group in ['all8_strategies_cooperative_updates','continuous_scan_updates','caller_owned_A000_bridge','secondary_phase']and (label is None or label.get('sample',False)):
                fixtures.append(details)
            return src.ram[:],src.sram[:],result
        except Exception as exc:
            check(group,False,{'entry':entry,'label':label,'error':str(exc)[:1500]});return ram,sram,None
    # Every request rawbyte, with no eligible actors: avoids unsafe strategy
    # indices while proving FF/1/all-other mode comparisons directly.
    for request in range(256):
        ram,sram=fresh();sram[0xf8b]=request;sram[0xfa1:0xfb5]=bytes([255]*20)
        ram[0x4d8:0x4e0]=bytes([255]*8)
        compare('all256_request_rawbytes',0xa02d,ram,sram,r=Registers(a=request,x=(request*3)&255,y=(request*5)&255,p=request|32))
    # Exact B517 protocol across every SP value and every legal table index.
    # The original JSR's actual return words are supplied by the caller.
    for table in program['inline_tables']:
        pc=table['call_pc']
        for index,target in enumerate(table['targets']):
            for sp in range(256):
                ram,sram=fresh();pointer=pc+2
                ram[0x100+((sp+1)&255)]=pointer&255;ram[0x100+((sp+2)&255)]=pointer>>8
                r=Registers(a=index,x=(sp*3)&255,y=sp,sp=sp,p=sp|32,pc=0xb517)
                src=PrgDataMemory(rom,ram,sram,banks=[6,8,9,31]);ref=native_bus(rom,ram,sram);m=TacticalAIControl(src,program=program)
                m.machine.registers=Registers(**vars(r));m.machine.events=[{'call_pc':pc}]
                TacticalDispatch()(m.machine,0xb517,None,'call')
                c,n,visited=native_cpu(ref,r,0xb517,target);native_locations.update(visited)
                check('B517_all24_legal_indices_all256_SP',vars(m.registers)==regs(c)and src.ram==ref.ram and src.sram==ref.sram and src.banks==ref.banks,
                      {'call_pc':pc,'index':index,'sp':sp,'model_registers':vars(m.registers),'rom_registers':regs(c),'ram_diff':diff(src.ram,ref.ram)})
    # These are source fail-closed guards, not original out-of-table executions.
    for pc,values in [(0xa09e,range(8,16)),(0xacab,range(16,256))]:
        for index in values:
            ram,sram=fresh();src=PrgDataMemory(rom,ram,sram,banks=[6,8,9,31]);m=TacticalAIControl(src,program=program)
            m.machine.registers=Registers(a=index);m.machine.events=[{'call_pc':pc}];before=src.ram[:]
            try:TacticalDispatch()(m.machine,0xb517,None,'call');rejected=False
            except InvalidState:rejected=True
            check('unproven_dispatch_indices_rejected',rejected and src.ram==before,{'call_pc':pc,'index':index})
    # Eight original strategy entries, both sides, meaningful resource and
    # condition/position boundaries, using original core records and map pages.
    for strategy in range(8):
        for side in [0,128]:
            actor=10 if side else 0;enemy=0 if side else 10
            for ap in [0,1,2,3,5,10,15,255]:
                for scenario in range(4):
                    ram,sram=fresh();sram[0xf8b]=0;sram[0xf94]=actor;sram[0xf8c]=actor;sram[0xfa1:0xfb5]=bytes([255]*20);sram[0xfa1+actor]=strategy
                    ram[0x504]=side;ram[0x505]=ap;ram[0x650+actor]=[0,4,128,64][scenario]
                    ram[0x600+actor]=[2,2,15,20][scenario];ram[0x614+actor]=[14,16,17,13][scenario]
                    ram[0x600+enemy]=[3,17,16,2][scenario];ram[0x614+enemy]=[14,16,17,16][scenario]
                    compare('all8_strategies_cooperative_updates',0xa02d,ram,sram,r=Registers(a=65,x=actor,y=enemy,p=32|(scenario&1)),
                      label={'strategy':strategy,'side':side,'ap':ap,'scenario':scenario,'sample':ap in [0,15]and scenario==0})
    # Each published entry body, including all sixteen predicate indices.
    for e in catalog['entries']:
        for variant in range(4):
            ram,sram=fresh();actor=0 if variant&1 else 10;sram[0xf8c]=actor;sram[0xf8e]=10 if actor==0 else 0
            ram[0x504]=0 if actor==0 else 128;ram[0x505]=[0,5,15,255][variant]
            ram[0x20]=[0,2,15,20][variant];ram[0x21]=[0,14,16,31][variant]
            ram[0x4d8:0x4e0]=bytes([255]*8)
            if e['name']=='strategy_dispatch':sram[0xfa1+actor]=variant
            compare('all28_published_entry_bodies',e['entry'],ram,sram,r=Registers(a=variant,x=actor,y=actor,p=[32,33,96,225][variant]),label={'name':e['name'],'variant':variant})
    # Completion, reset/rescan, side/ID/strategy holes and multiple proposals
    # across consecutive independent cooperation updates, no action ack.
    for variant in range(16):
        ram,sram=fresh();sram[0xf8b]=0;sram[0xfa1:0xfb5]=bytes([255]*20);ram[0x504]=variant&128;ram[0x505]=variant%6
        for slot in [0,1,2,3,10]:sram[0xfa1+slot]=(variant+slot)%8
        if variant&1:ram[0x664+1]=255
        if variant&2:ram[0x628+2]=128
        sram[0xf94]=(variant*3)%20
        for tick in range(3):
            ram,sram,result=compare('continuous_scan_updates',0xa02d,ram,sram,label={'variant':variant,'tick':tick,'sample':variant<4})
            if result is None:break
            # Requesting another computation is an explicit fixture input;
            # proposals are deliberately not applied/acknowledged by a renderer.
            sram[0xf8b]=0
    # Secondary phase with/without reserve, same/far coordinate and health/troop
    # edge values. Its source faithfully preserves the original index/arithmetic.
    for side in [0,128]:
        for variant in range(16):
            ram,sram=fresh();actor=10 if side else 0;reserve=0 if side else 10;sram[0xf8b]=1;sram[0xf8c]=actor;ram[0x504]=side
            ram[0x4d8:0x4e0]=bytes([255]*8);i=0 if side else 4
            if variant&1:ram[0x4d8+i]=reserve
            ram[0x4d9+i]=ram[0x600+actor]if variant&2 else 0;ram[0x4da+i]=ram[0x614+actor]if variant&2 else 1
            compare('secondary_phase',0xa02d,ram,sram,label={'side':side,'variant':variant,'sample':variant<4})
    # Global E229's real JSR owns its return frame: A000 tailJMP A02D.
    for sp in [0,1,2,127,128,253,254,255]:
        ram,sram=fresh();sram[0xf8b]=255;caller=0xe22b
        ram[0x100+((sp+1)&255)]=caller&255;ram[0x100+((sp+2)&255)]=caller>>8
        compare('caller_owned_A000_bridge',0xa000,ram,sram,r=Registers(a=0x71,x=0xe1,y=0x28,sp=sp,p=0xe5),seed=False,return_pc=0xe22c,label={'sp':sp})
    # Natural complete-core request RAM/SRAM is an unmodified game input. This
    # is a separate synchronous original/source call, using its captured CPU
    # registers and the explicitly supplied real E22C caller frame. It is not
    # a claim to resume Nestopia's native saved PC or reproduce its NMI frame.
    natural_prefix=ROOT/'analysis/phase7/runtime/natural-turn/ai-request'
    native_call=json.loads((ROOT/'analysis/phase7/runtime/cpu-call/validation.json').read_text())
    ram=bytearray(Path(str(natural_prefix)+'-ram.bin').read_bytes());sram=bytearray(Path(str(natural_prefix)+'-sram.bin').read_bytes())
    nr=Registers(**native_call['entry_registers']);original_sp=(nr.sp+2)&255
    ram[0x100+original_sp]=0xe2;ram[0x100+((original_sp-1)&255)]=0x2b
    natural_ram,natural_sram,natural_result=compare('natural_core_request_synchronous_call',0xa000,ram,sram,r=nr,seed=False,return_pc=0xe22c,label={'frame':431,'native_call_instructions':native_call['instruction_count']})
    assert natural_result is not None
    checkpoints=json.loads((ROOT/'analysis/phase7/runtime/natural-turn/checkpoints.json').read_text())
    core_proposal=next(item for item in checkpoints if item['label']=='ai-proposal')
    keys={'request':'ai_phase_6F8B','actor_slot':'ai_actor_6F8C','proposal_action_or_destination':'proposal_action_or_direction_6F8D',
          'proposal_target_slot':'proposal_target_6F8E','proposal_status':'proposal_status_6F8F','scan_slot':'scan_cursor_6F94',
          'status3_count':'status3_count_6F95','eligible_attempts':'eligible_attempts_6F96'}
    natural_core_comparisons={name:{'source':natural_result['after'][name],'native_next_frame':core_proposal[key],'equal':natural_result['after'][name]==core_proposal[key]}for name,key in keys.items()}
    assert all(item['equal']for item in natural_core_comparisons.values()),natural_core_comparisons
    fixtures.append({'group':'natural_core_request_synchronous_call','snapshot':str(natural_prefix.relative_to(ROOT)),'native_field_comparisons':natural_core_comparisons,'result':natural_result})
    # Original byte provenance includes both inline tables and B517 source.
    for n in program['instructions']:
        assert n['bank']==8 and n['file']==0x10010+n['pc']-0xa000
        assert rom[n['file']:n['file']+len(bytes.fromhex(n['raw_hex']))]==bytes.fromhex(n['raw_hex'])
    for table in program['inline_tables']:assert rom[table['table_file']:table['table_file']+2*table['count']]==bytes.fromhex(table['raw_hex'])
    for n in catalog['inline_helper_evidence']:assert rom[n['file']:n['file']+len(bytes.fromhex(n['raw_hex']))]==bytes.fromhex(n['raw_hex'])
    guards=counts['unproven_dispatch_indices_rejected']
    report={'status':'passed'if not failures else'failed','rom_sha256':ROM_SHA256,'case_count':sum(counts.values()),'failed_count':len(failures),'rom_cpu_case_count':sum(counts.values())-guards,'source_guard_case_count':guards,
      'counts':dict(counts),'status_counts':dict(statuses),'instruction_ir_total':len(program['instructions']),'instruction_ir_coverage':len(coverage),'static_instruction_matches':len(program['instructions']),
      'source_instruction_locations_executed':sorted(coverage),'native_instruction_locations':len(native_locations),'legal_strategy_indices_verified':list(range(8)),'legal_predicate_indices_verified':list(range(16)),
      'source_sha256':sha(ROOT/'source/recovered/tactical_ai_control.py'),'validator_sha256':sha(Path(__file__).resolve()),'program_sha256':sha(a.out/'program.json'),'catalog_sha256':sha(a.out/'state-catalog.json'),
      'dependency_source_sha256':{name:sha(ROOT/'source/recovered'/name)for name in ['battle_state_machine.py','controller_helpers.py','runtime_services.py','mapped_memory.py']},
      'fixture_source':str(prefix.relative_to(ROOT)),'fixture_source_sha256':{suffix:sha(Path(str(prefix)+suffix))for suffix in ['-ram.bin','-sram.bin']},
      'typed_fixture_sources':{'controlled_base':str(prefix.relative_to(ROOT)),'natural_request':str(natural_prefix.relative_to(ROOT))},
      'typed_fixture_sha256':{'natural_request':{suffix:sha(Path(str(natural_prefix)+suffix))for suffix in ['-ram.bin','-sram.bin','.state']},'natural_proposal':{'checkpoints':sha(ROOT/'analysis/phase7/runtime/natural-turn/checkpoints.json')},'cpu_call_receipt':sha(ROOT/'analysis/phase7/runtime/cpu-call/validation.json')},
      'natural_core_field_comparisons':natural_core_comparisons,
      'fixture_inputs':'Read-only original-core attack-intro-7 RAM/SRAM; inject request/scan/proposal/strategy, side/budget/condition, legal slot coordinates/IDs and real stack frames as specified in validator; original ROM/opcodes unchanged.',
      'contract':'Entire2KiB RAM+8KiB SRAM, CPU A/X/Y/P/SP/PC and physical PRG banks. Independent source uses no original-code helper or timing ack; only recovered B517 and shared F266 protocols.',
      'failures':failures,'fixtures':fixtures,'limitations':['An AI proposal is not its subsequent battlefield/NMI effect.','Guard cases reject unproven pointer domains; original out-of-table executions are not performed.','Controlled CPU inputs are not natural gameplay screenshots.','Static byte provenance and dynamic instruction coverage are separate.']}
    (a.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','case_count','rom_cpu_case_count','source_guard_case_count','failed_count','instruction_ir_total','instruction_ir_coverage','counts']},ensure_ascii=False))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
