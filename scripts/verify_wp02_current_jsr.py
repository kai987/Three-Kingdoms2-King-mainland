#!/usr/bin/env python3
"""Root-only original-ROM CPU contracts; no production Source or Native runs."""
from pathlib import Path
import argparse,collections,hashlib,inspect,json,sys,traceback
sys.dont_write_bytecode=True
from py65.devices.mpu6502 import MPU
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp02-current-jsr-contract'
CALLS={0xA09E:8,0xACAB:16};SELECTED=(0xB525,0xB52B)
AUX={0x6000+city*32+off for city in range(30)for off in (1,28,29,30,31)}
BASE_RAM=bytes((i*29+17)&255 for i in range(2048));BASE_SRAM=bytes((i*11+23)&255 for i in range(8192))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def regs(r):return{k:getattr(r,k)for k in ('pc','a','x','y','p','sp')}
def off(bank,pc):return 16+bank*8192+(pc&8191)
def normal(a):return a&2047 if a<8192 else a
def save(p,x):assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

class ContractBus:
    def __init__(self,rom,bank):
        self.rom=rom;self.ram=bytearray(BASE_RAM);self.sram=bytearray(BASE_SRAM);self.banks=[bank,8,9,31]
        self.writes=[];self.mapper=[];self.mutations=[];self.tags={};self.pc=None;self.generation=None
        self.primary_call=None;self.selected_context=None;self.selected_reads=[];self.pla_context=None;self.pla_reads=[]
    def __len__(self):return 65536
    def peek(self,a):
        a&=65535
        if a<8192:return self.ram[a&2047]
        if 0x6000<=a<0x8000:return self.sram[a-0x6000]
        if a>=0x8000:return self.rom[off(self.banks[(a-0x8000)//8192],a)]
        raise RuntimeError(f'No declared hardware read at {a:04X}')
    def __getitem__(self,a):
        a&=65535;value=self.peek(a)
        if self.selected_context is not None and a==self.selected_context['logical_effective_address']:
            self.selected_reads.append(dict(**self.selected_context,value=value))
        if self.pla_context is not None and a==self.pla_context['stack_address']:
            self.pla_reads.append(dict(**self.pla_context,value=value,last_writer=self.tags.get(a)))
        return value
    def __setitem__(self,a,v):
        a&=65535;v&=255
        if a<8192 or 0x6000<=a<0x8000:
            p=normal(a);before=self.peek(a)
            if a<8192:self.ram[p]=v
            else:self.sram[a-0x6000]=v
            tag=dict(kind='primary_JSR'if self.pc==self.primary_call else'original_instruction',generation=self.generation,PC=self.pc)
            self.tags[p]=tag;self.writes.append(dict(address=a,physical_address=p,before=before,value=v,PC=self.pc,generation=self.generation))
        elif a in (0xE000,0xE800,0xF000):
            slot={0xE000:0,0xE800:1,0xF000:2}[a];self.banks[slot]=v&31
            self.mapper.append(dict(address=a,value=v,physical_bank=v&31,PC=self.pc,generation=self.generation))
        else:raise RuntimeError(f'Unexpected hardware write at {a:04X}')
    def fixture(self,a,v,reason):
        before=self.peek(a);v&=255
        if a<8192:self.ram[a&2047]=v
        elif 0x6000<=a<0x8000:self.sram[a-0x6000]=v
        else:raise ValueError('Fixture may only mutate declared RAM/SRAM inputs')
        self.tags[normal(a)]=dict(kind='disclosed_fixture_mutation',reason=reason,generation=self.generation)
        self.mutations.append(dict(address=a,before=before,value=v,reason=reason,generation=self.generation))

def prepare(bus,s):
    if 'strategy_raw'in s:bus.fixture(0x6FA1+s['registers']['y'],s['strategy_raw'],'controlled strategy input before A099')
    if 'initial_live_pointer'in s:
        for a,v in ((0x21,s['initial_live_pointer']&255),(0x22,s['initial_live_pointer']>>8)):bus.fixture(a,v,'initial stale live21/22')
    if 'bare_stack_word'in s:
        sp=s['registers']['sp'];word=s['bare_stack_word']
        bus.fixture(0x100+((sp+1)&255),word&255,'bare B517 stack low, no original JSR')
        bus.fixture(0x100+((sp+2)&255),word>>8,'bare B517 stack high, no original JSR')
    if s['entry']==0xAC7B or 'outer_call_pc'in s:
        bus.fixture(0x2B,5,'target unit input');bus.fixture(0x6F8C,10,'actor unit input')
        bus.fixture(0xA8,0xAA,'chunk descriptor pointer low');bus.fixture(0xA9,0,'chunk descriptor pointer high')
        for i,value in enumerate((0,1,32,64)):bus.fixture(0xAA+i,value,'four distinct original chunk descriptor IDs')
        for slot,q in ((5,s['target_quadrant']),(10,s['actor_quadrant'])):
            bus.fixture(0x600+slot,3+16*(q&1),'controlled unit X')
            bus.fixture(0x614+slot,7+16*(q>>1),'controlled unit Y')

def segment(bus,cpu,s,generation,index,frame_fault=None,second=False):
    bus.generation=generation;bus.primary_call=s['call_pc'];bus.selected_context=None;bus.pla_context=None
    if second:
        cpu.pc=s['call_pc'];cpu.a=index;cpu.y=93
        for a,v in ((0x21,0),(0x22,0x60)):bus.fixture(a,v,'between-generation stale live pointer, before new JSR')
    initial=regs(cpu);before_ram=bytes(bus.ram);before_sram=bytes(bus.sram);before_banks=list(bus.banks)
    wstart=len(bus.writes);mstart=len(bus.mapper);rstart=len(bus.selected_reads);pstart=len(bus.pla_reads);ustart=len(bus.mutations)
    call=None;terrain_calls=[];terrain_returns=[];fixed_entries=[];fixed_returns=[];positions=[];observations=[];load2C=None
    bare=s['entry']in (0xB517,*SELECTED);middle=s['entry']in SELECTED
    terrain=s['entry']==0xAC7B or 'outer_call_pc'in s
    for n in range(1000):
        pc=cpu.pc;sp=cpu.sp;bus.pc=pc;bus.selected_context=None;bus.pla_context=None
        assert 0x8000<=pc<=0xFFFF,(s['key'],'unexpected opcode domain',pc)
        bank=bus.banks[(pc-0x8000)//8192];positions.append([bank,pc])
        if bank==8 and pc==s['call_pc']:
            assert bus.peek(pc)==0x20 and bytes(bus.peek(pc+i)for i in range(3))==bytes.fromhex('2017b5')
            assert cpu.a==index,(s['key'],'call A',cpu.a,index)
            if 'stale_stack_word'in s or second:
                word=s.get('stale_stack_word',0x6000)
                bus.fixture(0x100+sp,word>>8,'stale stack high immediately before current real JSR')
                bus.fixture(0x100+((sp-1)&255),word&255,'stale stack low immediately before current real JSR')
            call=dict(registers=regs(cpu),raw_return=pc+2,stack_before=[bus.peek(0x100+sp),bus.peek(0x100+((sp-1)&255))])
            if terrain:assert bus.peek(0x2C)==index and cpu.x==0 and load2C==index
        if bank==8 and pc in (0xAC8D,0xACA2):terrain_calls.append(dict(PC=pc,registers=regs(cpu),live2C=bus.peek(0x2C)))
        if bank==8 and pc in (0xAC90,0xACA5):terrain_returns.append(dict(PC=pc,registers=regs(cpu),live2C=bus.peek(0x2C),banks=list(bus.banks),DE=bus.peek(0xDE)))
        if bank==31 and pc==0xF266:fixed_entries.append(dict(registers=regs(cpu),live2C=bus.peek(0x2C)))
        if bank==8 and pc==0xB71F:fixed_returns.append(dict(registers=regs(cpu),live2C=bus.peek(0x2C),banks=list(bus.banks),DE=bus.peek(0xDE)))
        if bank==8 and pc in SELECTED:
            pointer=bus.peek(0x21)|(bus.peek(0x22)<<8);ea=(pointer+cpu.y)&65535
            bus.selected_context=dict(PC=pc,SP=sp,live21_22=pointer,Y=cpu.y,logical_effective_address=ea,
                                      normalized_address=normal(ea),auxiliary_alias=normal(ea)in AUX,generation=generation)
        if bank==8 and pc in (0xB51D,0xB521):
            bus.pla_context=dict(PC=pc,SP_before=sp,stack_address=0x100+((sp+1)&255),generation=generation)
        before_step=regs(cpu);start=len(bus.writes);cpu.step()
        if bank==8 and pc==0xACA8:
            load2C=cpu.a;assert cpu.a==bus.peek(0x2C)==index
        if bank==8 and pc==s['call_pc']:
            actual=bus.writes[start:];expected=[(0x100+sp,(pc+2)>>8),(0x100+((sp-1)&255),(pc+2)&255)]
            assert[(x['address'],x['value'])for x in actual]==expected
            assert cpu.pc==0xB517 and cpu.sp==(sp-2)&255
            call['actual_pushes']=actual;call['registers_after_JSR']=regs(cpu)
            if frame_fault:
                address=0x100+(sp if frame_fault=='high'else((sp-1)&255))
                bus.fixture(address,0x60 if frame_fault=='high'else 0,'post-JSR one-byte restoration of stale6000; current frame premise violated')
        if bank==8 and pc in (0xB51D,0xB521):
            observation=bus.pla_reads[-1];assert cpu.a==observation['value']and cpu.sp==(sp+1)&255
            observations.append(dict(kind='actual_PLA',**observation,registers_after=regs(cpu)))
        if bank==8 and pc==0xB52A and 'between_reads_pointer'in s:
            value=s['between_reads_pointer']
            bus.fixture(0x21,value&255,'external pointer overwrite between actual selected LDA instructions')
            bus.fixture(0x22,value>>8,'external pointer overwrite between actual selected LDA instructions')
        if middle or(bank==8 and pc==0xB533):break
    else:raise AssertionError((s['key'],'instruction budget',regs(cpu)))
    bus.selected_context=None;bus.pla_context=None
    reads=bus.selected_reads[rstart:];plas=bus.pla_reads[pstart:];writes=bus.writes[wstart:]
    assert len(reads)==(1 if middle else 2)
    assert all(read['value']==bus.peek(read['logical_effective_address'])for read in reads)
    assert bytes(bus.sram)==before_sram
    allowed=set()if middle else set(range(0x20,0x25))
    if terrain:allowed|=set(range(0x100,0x200))|set(range(0x20,0x2A))|{0x2C,0xDE}
    elif call:allowed|={x['physical_address']for x in call['actual_pushes']}
    assert all(value==before_ram[a]for a,value in enumerate(bus.ram)if a not in allowed)
    assert all(x['physical_address']in allowed for x in writes)
    valid=(call is not None and len(plas)==2
           and all(p['last_writer']==dict(kind='primary_JSR',generation=generation,PC=s['call_pc'])for p in plas)
           and all(x['live21_22']==s['call_pc']+2 for x in reads)
           and not any('post-JSR'in m['reason']or'external pointer'in m['reason']for m in bus.mutations[ustart:]))
    expected_valid=not bare and not frame_fault and 'between_reads_pointer'not in s
    assert valid==expected_valid,(s['key'],generation,'derived current-frame authority',valid,expected_valid)
    if valid:
        raw=s['call_pc']+2;first=(2*index+1)&255;last=(first+1)&255;low=bus.rom[off(8,raw+first)];high=bus.rom[off(8,raw+last)]
        assert[(x['PC'],x['live21_22'],x['Y'],x['logical_effective_address'],x['value'])for x in reads]==[
            (0xB525,raw,first,raw+first,low),(0xB52B,raw,last,raw+last,high)]
        assert cpu.pc==low|(high<<8) and cpu.sp==call['registers']['sp']
        assert(cpu.x,cpu.y,cpu.a)==(call['registers']['x'],call['registers']['y'],high)
        expected_p=(call['registers']['p']&~0x83)|(1 if index&128 else 0)
        y=call['registers']['y'];expected_p|=(2 if y==0 else 0)|(128 if y&128 else 0)
        assert cpu.p==expected_p
        assert list(bus.ram[0x20:0x25])==[y,raw&255,raw>>8,low,high]
        assert all(not x['auxiliary_alias']for x in reads)
        assert [p['stack_address']for p in plas]==[call['actual_pushes'][1]['address'],call['actual_pushes'][0]['address']]
        assert [p['value']for p in plas]==[raw&255,raw>>8]
    if terrain:
        assert len(terrain_calls)==len(terrain_returns)==len(fixed_entries)==len(fixed_returns)==2
        assert all(x['live2C']==index for x in terrain_calls+terrain_returns+fixed_entries+fixed_returns)
        assert all(x['registers']['x']==0 for x in terrain_returns)
        for entry,returned in zip(fixed_entries,fixed_returns):
            assert returned['DE']==entry['registers']['y'] and returned['banks'][0]==(entry['registers']['y']&31)
            assert returned['registers']['sp']==(entry['registers']['sp']+2)&255
        assert bus.banks[1:]==[8,9,31]and bus.banks[0]==fixed_entries[-1]['registers']['y']&31
        assert len([x for x in writes if x['physical_address']==0x2C])==1
    if bare:assert any(x['auxiliary_alias']for x in reads)
    if frame_fault:assert plas[0]['last_writer']['kind']=='disclosed_fixture_mutation'or plas[1]['last_writer']['kind']=='disclosed_fixture_mutation'
    if 'between_reads_pointer'in s:assert reads[0]['live21_22']==s['call_pc']+2 and reads[1]['normalized_address']==0x601C
    return dict(generation=generation,input_registers=initial,initial_banks=before_banks,
        initial_RAM_sha256=digest(before_ram),initial_SRAM_sha256=digest(before_sram),final_registers=regs(cpu),final_banks=list(bus.banks),
        final_RAM_sha256=digest(bytes(bus.ram)),final_SRAM_sha256=digest(bytes(bus.sram)),original_instructions=n+1,
        executed_positions=positions,actual_primary_JSR=call,actual_PLA_reads=observations,selected_reads=reads,
        derived_current_frame_authority=valid,legal_inline_target=index<CALLS[s['call_pc']]if s['call_pc']in CALLS else None,
        allowed_RAM_write_addresses=sorted(allowed),logical_RAM_SRAM_writes=writes,mapper_writes=bus.mapper[mstart:],
        terrain_calls=terrain_calls,terrain_returns=terrain_returns,F266_entries=fixed_entries,F266_returns=fixed_returns,
        A_reloaded_from_live2C=load2C,whole_SRAM_unchanged=True,all_RAM_nonwrite_invariants_checked=True,
        boundary='selected_LDA_only'if middle else'after_B533_JMP_before_target_first_opcode',actual_caller_RTS=False,target_first_opcode_executed=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--root-execution-authorized',action='store_true');a=p.parse_args();assert a.root_execution_authorized
    folder=a.out.resolve();assert folder.is_relative_to(OUT)and not folder.exists();folder.mkdir()
    plan=json.loads((OUT/'case-matrix.json').read_text());accept=json.loads((OUT/'acceptance.json').read_text())
    assert sha(OUT/'case-matrix.json')==accept['matrix_sha256'];assert sha(OUT/'static-contract.json')==accept['static_contract_sha256']
    rom=a.rom.read_bytes();assert digest(rom)=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
    py65root=Path(inspect.getfile(MPU)).resolve().parents[1]
    pins={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'scripts').glob('*wp02*.py'))}
    runtime=dict(Python=sys.version,executable=str(Path(sys.executable).resolve()),executable_sha256=sha(Path(sys.executable).resolve()),
                 py65_python_files={str(p):sha(p)for p in sorted(py65root.rglob('*.py'))})
    save(folder/'execution-inputs.json',dict(matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),
         static_contract_sha256=sha(OUT/'static-contract.json'),script_sha256=pins,runtime=runtime,actual_capture_origin=None,
         base_RAM_sha256=digest(BASE_RAM),base_SRAM_sha256=digest(BASE_SRAM),Native_runs=0,Source_cases=0))
    (folder/'base-ram.bin').write_bytes(BASE_RAM);(folder/'base-sram.bin').write_bytes(BASE_SRAM)
    snapshots=folder/'executed-scripts';snapshots.mkdir()
    for name,d in pins.items():raw=(ROOT/name).read_bytes();assert digest(raw)==d;(snapshots/Path(name).name).write_bytes(raw)
    counts=collections.Counter();segments=0;instructions=0;primary_jsrs=0;valid=0;aliases=set();keys=[];failure=None
    with(folder/'cases.jsonl').open('w')as stream:
        for s in plan['cases']:
            try:
                bus=ContractBus(rom,s['data_bank']);prepare(bus,s);cpu=MPU(memory=bus)
                for name,value in s['registers'].items():setattr(cpu,name,value)
                if s['entry']==0xAC7B:cpu.x=s['index']
                pieces=[segment(bus,cpu,s,0,s['index'],s.get('post_JSR_restore_stale_byte'))]
                if 'two_generations'in s:
                    index=(0 if s['call_pc']==0xA09E else 7)if s['two_generations']=='fault'else 7
                    pieces.append(segment(bus,cpu,s,1,index,'high'if s['two_generations']=='fault'else None,second=True))
                    assert len(pieces)==2 and pieces[0]['actual_primary_JSR']['registers']['pc']==pieces[1]['actual_primary_JSR']['registers']['pc']
                row=dict(case=s['key'],group=s['group'],status='passed',segments=pieces,disclosed_mutations=bus.mutations,
                         one_bus_and_CPU_across_generations=True,spec=s)
                stream.write(json.dumps(row,separators=(',',':'))+'\n')
                counts[s['group']]+=1;keys.append(s['key']);segments+=len(pieces)
                for piece in pieces:
                    instructions+=piece['original_instructions'];primary_jsrs+=piece['actual_primary_JSR']is not None
                    valid+=piece['derived_current_frame_authority'];aliases.update(x['normalized_address']for x in piece['selected_reads']if x['auxiliary_alias'])
            except Exception as exc:
                failure=dict(case=s['key'],type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),registers=regs(cpu))
                save(folder/'failure.json',failure);break
    assert all(sha(ROOT/name)==d for name,d in pins.items())
    complete=(failure is None and keys==[x['key']for x in plan['cases']]and dict(counts)==accept['required_groups'])
    if complete:assert segments==17215 and primary_jsrs==17206 and valid==17190 and aliases>={0x6001,0x601C,0x601D,0x601E,0x601F}
    result=dict(schema='wp02-current-JSR-CPU-contract-run-v1',status='passed_full_declared_matrix'if complete else'failed_or_incomplete',
        controlled_CPU_parent_cases=len(keys),completed_prefix_segments=segments,actual_primary_JSR_executions=primary_jsrs,
        conditionally_valid_current_frame_segments=valid,original_CPU_instructions=instructions,groups=dict(counts),
        case_keys_sha256=digest(json.dumps(keys,separators=(',',':')).encode()),cases=record_case_file(folder/'cases.jsonl'),
        matrix_sha256=sha(OUT/'case-matrix.json'),acceptance_sha256=sha(OUT/'acceptance.json'),scripts_sha256=pins,
        failed_count=0 if failure is None else 1,failure=failure,actual_capture_origin=None,Source_cases=0,Native_runs=0,
        actual_caller_RTS_cases=0,unimplemented_target_opcode_executions=0,whole_game_closure_proven=False,
        auxiliary_counterexample_addresses=sorted(aliases),production_CPU_or_IR_fallback_added=False)
    save(folder/'validation.json',result)
    print(json.dumps({k:v for k,v in result.items()if k not in ('scripts_sha256','cases','auxiliary_counterexample_addresses')},ensure_ascii=False))
def record_case_file(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
if __name__=='__main__':main()
