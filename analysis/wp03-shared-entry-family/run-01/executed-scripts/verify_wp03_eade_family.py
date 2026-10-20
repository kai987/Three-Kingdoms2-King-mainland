#!/usr/bin/env python3
"""Root-only EADE original-CPU prefixes and independent existing-Source prefixes."""
from pathlib import Path
from types import SimpleNamespace
import argparse,collections,hashlib,inspect,json,sys,traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_wp02_current_jsr import ContractBus,BASE_RAM,BASE_SRAM,regs,normal
from source.recovered.battle_scene_controller import BattleSceneController
from source.recovered.attack_scene_controller import AttackSceneController
from source.recovered.controller_helpers import ControlHelpers
OUT=ROOT/'analysis/wp03-shared-entry-family';ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
AUX={0x6000+city*32+offset for city in range(30)for offset in(1,28,29,30,31)}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def clone(bus):
    copy=ContractBus(bus.rom,bus.banks[0]);copy.ram[:]=bus.ram;copy.sram[:]=bus.sram;copy.banks[:]=bus.banks
    return copy
def Source_prefix(bus,initial,caller):
    """Test boundary uses existing named Source only; no original CPU callback."""
    r=SimpleNamespace(**initial);bus.pc=caller['pc'];bus.primary_call=caller['pc'];bus.generation='Source-prefix'
    if caller['group']=='duel':
        word=caller['pc']+2
        for value in(word>>8,word&255):bus[0x100+r.sp]=value;r.sp=(r.sp-1)&255
        r.pc=0xEADE
        def pop():
            r.sp=(r.sp+1)&255;return bus[0x100+r.sp]
        context=SimpleNamespace(memory=bus,registers=r,pop=pop);helper=ControlHelpers();assert helper.fallback is None
        helper(context,0xEADE,caller['targets'][initial['a']],'dispatch')
        return regs(r),'production_ControlHelpers_EADE_only_no_duel_handler'
    cls=AttackSceneController if caller['group']=='attack'else BattleSceneController
    owner=cls(bus,bus.rom);owner.registers=r
    assert owner.services is None
    owner._dispatch(caller['pc'],tuple(caller['targets']))
    return regs(r),'production_synchronous_scene_dispatch_prefix'

def segment(bus,cpu,s,caller,generation,index,fault=None):
    bus.generation=generation;bus.primary_call=None if caller is None else caller['pc'];bus.pc=None
    bus.selected_context=None;bus.pla_context=None
    if s.get('stale_stack_word')is not None or generation:
        word=s.get('stale_stack_word',0x6000);sp=cpu.sp
        bus.fixture(0x100+sp,word>>8,'stale old high before real current JSR')
        bus.fixture(0x100+((sp-1)&255),word&255,'stale old low before real current JSR')
    initial=regs(cpu);before_ram=bytes(bus.ram);before_sram=bytes(bus.sram);before_banks=list(bus.banks);source_bus=clone(bus)
    wstart=len(bus.writes);rstart=len(bus.selected_reads);pstart=len(bus.pla_reads);mutstart=len(bus.mutations)
    call=None;positions=[];step_rows=[];middle=s.get('entry')in(0xEAE9,0xEAEE)
    for n in range(1000):
        pc=cpu.pc;sp=cpu.sp;bus.pc=pc;bus.selected_context=None;bus.pla_context=None
        assert pc>=0x8000,(s['key'],'unknown opcode domain',pc)
        bank=bus.banks[(pc-0x8000)//8192];positions.append([bank,pc]);before=regs(cpu);start=len(bus.writes)
        if caller is not None and pc==caller['pc']:
            assert bytes(bus.peek(pc+i)for i in range(3))==bytes.fromhex('20deea')and cpu.a==index
            call=dict(registers=regs(cpu),raw_return=pc+2,generation=generation)
        if bank==31 and pc in(0xEAE3,0xEAE6):
            bus.pla_context=dict(PC=pc,SP_before=sp,stack_address=0x100+((sp+1)&255),generation=generation)
        if bank==31 and pc in(0xEAE9,0xEAEE):
            pointer=bus.peek(1)|(bus.peek(2)<<8);ea=(pointer+cpu.y)&65535
            bus.selected_context=dict(PC=pc,SP=sp,live01_02=pointer,Y=cpu.y,logical_effective_address=ea,
                                      normalized_address=normal(ea),auxiliary_alias=normal(ea)in AUX,generation=generation)
        cpu.step()
        if caller is not None and pc==caller['pc']:
            call['pushes']=bus.writes[start:]
            assert[(x['address'],x['value'])for x in call['pushes']]==[(0x100+sp,(pc+2)>>8),(0x100+((sp-1)&255),(pc+2)&255)]
            assert cpu.pc==0xEADE and cpu.sp==(sp-2)&255
            if fault in('high60','same_value_high'):
                bus.fixture(0x100+sp,0x60 if fault=='high60'else(pc+2)>>8,'post-JSR external '+fault+' write invalidates frame provenance')
        if bank==31 and pc==0xEAED and fault=='between_reads':
            bus.fixture(1,0,'external pointer change between selected reads');bus.fixture(2,0x60,'external pointer change between selected reads')
        step_rows.append(dict(before=before,after=regs(cpu),CPU_writes=bus.writes[start:]))
        if middle or(bank==31 and pc==0xEAF4):break
    else:raise AssertionError('Declared prefix instruction budget exhausted')
    bus.selected_context=None;bus.pla_context=None
    reads=bus.selected_reads[rstart:];plas=bus.pla_reads[pstart:];writes=bus.writes[wstart:]
    assert len(reads)==(1 if middle else 2)
    allowed=set()if middle else set(range(5))
    if call:allowed|={x['address']for x in call['pushes']}
    assert all(value==before_ram[a]for a,value in enumerate(bus.ram)if a not in allowed)
    assert all(x['physical_address']in allowed for x in writes)
    assert bytes(bus.sram)==before_sram and bus.banks==before_banks and not bus.mapper
    valid=(call is not None and len(plas)==2
           and all(x['last_writer']==dict(kind='primary_JSR',generation=generation,PC=caller['pc'])for x in plas)
           and all(x['live01_02']==caller['pc']+2 for x in reads)
           and not any('external'in x['reason']for x in bus.mutations[mutstart:]))
    assert valid==(caller is not None and fault is None)
    legal=caller is not None and 0<=index<len(caller['targets'])
    if valid:
        word=caller['pc']+2;ys=[(2*index+1)&255,(2*index+2)&255];values=[bus.peek(word+y)for y in ys]
        assert[(x['PC'],x['live01_02'],x['Y'],x['logical_effective_address'],x['value'])for x in reads]==[
            (pc,word,y,word+y,v)for pc,y,v in zip((0xEAE9,0xEAEE),ys,values)]
        assert all(not x['auxiliary_alias']for x in reads)
        assert [x['stack_address']for x in plas]==[call['pushes'][1]['address'],call['pushes'][0]['address']]
        assert [x['value']for x in plas]==[word&255,word>>8]
        assert cpu.sp==call['registers']['sp']and(cpu.x,cpu.y,cpu.a)==(initial['x'],initial['y'],values[1])
        assert cpu.pc==values[0]|(values[1]<<8)
        assert list(bus.ram[:5])==[initial['y'],word&255,word>>8,*values]
        expected_p=(initial['p']&~0x83)|(1 if index&128 else 0)|(2 if initial['y']==0 else 0)|(128 if initial['y']&128 else 0)
        assert cpu.p==expected_p
        if legal:assert cpu.pc==caller['targets'][index]
    if caller is None:assert any(x['auxiliary_alias']for x in reads)
    if fault=='same_value_high':
        changed=bus.mutations[mutstart:];assert len(changed)==1 and changed[0]['before']==changed[0]['value']
        assert all(x['live01_02']==caller['pc']+2 for x in reads)and plas[1]['last_writer']['kind']=='disclosed_fixture_mutation'
    if fault=='between_reads':assert reads[0]['live01_02']==caller['pc']+2 and reads[1]['normalized_address']==0x601C
    paired=False;source_kind=None
    if valid and legal and generation==0 and s['group']not in('same_bus_two_generations','stale6000_full_JSR_overwrite'):
        source_regs,source_kind=Source_prefix(source_bus,initial,caller)
        assert source_bus.ram==bus.ram and source_bus.sram==bus.sram and source_bus.banks==bus.banks and source_regs==regs(cpu)
        assert not source_bus.mapper
        paired=True
    return dict(generation=generation,input_registers=initial,initial_banks=before_banks,
        initial_RAM_sha256=digest(before_ram),initial_SRAM_sha256=digest(before_sram),final_registers=regs(cpu),final_banks=list(bus.banks),
        final_RAM_sha256=digest(bytes(bus.ram)),final_SRAM_sha256=digest(bytes(bus.sram)),instructions=n+1,
        executed_positions=positions,actual_JSR=call,actual_PLA_reads=plas,selected_reads=reads,CPU_logical_writes=writes,
        current_frame_premise_valid=valid,legal_inline_target=legal,Source_prefix_paired=paired,Source_comparison_kind=source_kind,
        Source_not_CPU_driven=True,full_RAM_nonwrite_domain_checked=True,whole_SRAM_unchanged=True,
        boundary='selected_LDA_only'if middle else'after_EAF4_JMP_before_target_first_opcode',actual_caller_RTS=False,
        instruction_trace=step_rows if(s.get('actual_initial_context')or s.get('fault')or s.get('two_generations')or caller is None)else None)

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--root-execution-authorized',action='store_true');a=p.parse_args();assert a.root_execution_authorized
    folder=a.out.resolve();assert folder.is_relative_to(OUT)and not folder.exists();folder.mkdir()
    plan=read(OUT/'case-matrix.json');scope=read(OUT/'family-scope.json');accept=read(OUT/'acceptance.json')
    assert sha(OUT/'family-scope.json')==accept['scope_sha256']and sha(OUT/'case-matrix.json')==accept['matrix_sha256']
    rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA
    pins={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'scripts').glob('*wp03*.py'))}
    pins.update({str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source/recovered').glob('*.py'))})
    pins['scripts/verify_wp02_current_jsr.py']=sha(ROOT/'scripts/verify_wp02_current_jsr.py')
    py65root=Path(inspect.getfile(MPU)).resolve().parents[1]
    save(folder/'execution-inputs.json',dict(scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),
        Source_and_scripts_sha256=pins,base_RAM_sha256=digest(BASE_RAM),base_SRAM_sha256=digest(BASE_SRAM),
        runtime=dict(Python=sys.version,executable=str(Path(sys.executable).resolve()),executable_sha256=sha(Path(sys.executable).resolve()),
                     py65_files={str(x):sha(x)for x in sorted(py65root.rglob('*.py'))}),Native_new_runs=0))
    executed=folder/'executed-scripts';executed.mkdir()
    for name in pins:
        if name.startswith('scripts/')and'wp03'in name:(executed/Path(name).name).write_bytes((ROOT/name).read_bytes())
    (folder/'executed-scope.json').write_bytes((OUT/'family-scope.json').read_bytes());(folder/'executed-matrix.json').write_bytes((OUT/'case-matrix.json').read_bytes())
    (folder/'base-ram.bin').write_bytes(BASE_RAM);(folder/'base-sram.bin').write_bytes(BASE_SRAM)
    groups=collections.Counter();source_kinds=collections.Counter();count=segments=primary=valid=source=instruction_count=0;failure=None;keys=[];native_result=None
    with(folder/'cases.jsonl').open('w')as stream:
        for s in plan['cases']:
            try:
                caller=None if s['caller_index']is None else scope['dynamic_callers'][s['caller_index']]
                pair=[8,9]if caller is None else caller['code_pair'];bus=ContractBus(rom,(s['index']+s['registers']['sp'])&31);bus.banks[:]=[bus.banks[0],*pair,31]
                if s.get('actual_initial_context'):
                    meta=scope['natural_reference']['initial'];directory=ROOT/'analysis/wp05-natural-nonempty/runtime/natural-day31-nonempty/observer'
                    bus.ram[:]=(directory/meta['exported_RAM']).read_bytes();bus.sram[:]=(directory/meta['exported_SRAM']).read_bytes();bus.banks[:]=meta['actual_PRG_banks']
                    assert digest(bytes(bus.ram))==meta['RAM_sha256']and digest(bytes(bus.sram))==meta['SRAM_sha256']
                if s.get('bare_stack_word')is not None:
                    sp=s['registers']['sp'];word=s['bare_stack_word']
                    bus.fixture(0x100+((sp+1)&255),word&255,'bare stack low without current JSR');bus.fixture(0x100+((sp+2)&255),word>>8,'bare stack high without current JSR')
                if s.get('middle_pointer')is not None:
                    bus.fixture(1,0,'middle-entry pointer low');bus.fixture(2,0x60,'middle-entry pointer high')
                cpu=MPU(memory=bus)
                for k,v in s['registers'].items():setattr(cpu,k,v)
                pieces=[segment(bus,cpu,s,caller,0,s['index'],s.get('fault'))];reentry=None
                if s.get('two_generations'):
                    before=regs(cpu);cpu.pc=caller['pc'];cpu.a=2 if s['two_generations']=='intact'else 8;cpu.y=93
                    after=regs(cpu);reentry=dict(before=before,after=after,reason='Host controlled PC/A/Y reentry after target-prefix boundary; SP not written.')
                    pieces.append(segment(bus,cpu,s,caller,1,cpu.a,None if s['two_generations']=='intact'else'high60'))
                if s.get('actual_initial_context'):
                    target=scope['natural_reference']['target']
                    assert bytes(bus.ram)==(directory/target['exported_RAM']).read_bytes()and bytes(bus.sram)==(directory/target['exported_SRAM']).read_bytes()
                    assert regs(cpu)==target['actual_registers']and bus.banks==target['actual_PRG_banks']
                    (folder/'WP05-replayed-target-ram.bin').write_bytes(bytes(bus.ram));(folder/'WP05-replayed-target-sram.bin').write_bytes(bytes(bus.sram))
                    native_result=dict(status='exact_WP05_target_snapshot23_matched',Source_prefix_matched=pieces[0]['Source_prefix_paired'],initial_registers_unmodified=True,initial_banks_unmodified=True,new_Native_runs=0)
                row=dict(case=s['key'],group=s['group'],spec=s,status='passed',segments=pieces,disclosed_RAM_mutations=bus.mutations,controlled_generation_reentry=reentry)
                stream.write(json.dumps(row,separators=(',',':'))+'\n');groups[s['group']]+=1;count+=1;keys.append(s['key'])
                for part in pieces:
                    segments+=1;primary+=part['actual_JSR']is not None;valid+=part['current_frame_premise_valid'];source+=part['Source_prefix_paired'];instruction_count+=part['instructions']
                    if part['Source_comparison_kind']:source_kinds[part['Source_comparison_kind']]+=1
            except Exception as exc:
                failure=dict(case=s['key'],type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),registers=regs(cpu));save(folder/'failure.json',failure);break
    assert all(sha(ROOT/name)==value for name,value in pins.items())
    complete=(failure is None and keys==[s['key']for s in plan['cases']]and dict(groups)==plan['groups'])
    if complete:assert(count,segments,primary,valid,source)==(16269,16273,16264,16256,4035)
    result=dict(schema='wp03-EADE-bounded-family-run-v1',status='passed_full_declared_family_matrix'if complete else'failed_or_incomplete',
        CPU_parent_cases=count,prefix_segments=segments,actual_primary_JSRs=primary,current_frame_valid_segments=valid,
        Source_prefix_comparisons=source,Source_comparison_kinds=dict(source_kinds),original_CPU_instructions=instruction_count,
        groups=dict(groups),cases_sha256=sha(folder/'cases.jsonl'),case_keys_sha256=digest(json.dumps(keys,separators=(',',':')).encode()),
        scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),actual_WP05_snapshot_replay=native_result,
        failed_count=0 if failure is None else 1,failure=failure,Native_new_runs=0,actual_caller_RTS_cases=0,
        whole_scene_Source_cases=0,production_CPU_IR_fallback_added=False,new_services_or_algorithms=0,
        field_classification_changes=0,raw_classification_changes=0,remaining=323,raw_unproved_entry=228,
        unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,whole_game_closure_proven=False)
    save(folder/'validation.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
