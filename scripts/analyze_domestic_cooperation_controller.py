#!/usr/bin/env python3
"""Offline structure the complete physical10/11 domestic cooperation closure.

Original opcodes are decoded only in this analyzer. Production comprises named
Python procedures, structured conditions and natural loops, with strict real
caller services; no runtime control IR or original CPU fallback is generated.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from inspect_game_data import OPS,SIZES,instruction
from analyze_global_ui_controller import UIStructurer,compiler,offset,BRANCHES,MODES
from ui_structuring import labelled_procedure,loop_exception_source
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase14/domestic';SOURCE=ROOT/'source/recovered/domestic_cooperation_controller.py'
NAMES={
 0xA000:'domestic_entry',0xA00F:'cooperate_domestic_ai',0xA042:'return_ai_call',
 0xA043:'initialize_strategy_weights',0xA0D3:'scan_neighbor_roster_pressure',
 0xA19C:'choose_three_way_strategy',0xA1C5:'military_strategy',0xA240:'choose_attack_city',
 0xA2D3:'diplomacy_attack_filter',0xA303:'seek_connected_reinforcements',
 0xA3D6:'select_reinforcement_officer',0xA45C:'prepare_attack_troops',0xA481:'fill_officer_troops',
 0xA55C:'transfer_attack_gold',0xA60C:'transfer_attack_grain',0xA6C9:'choose_attack_officer_count',
 0xA74A:'quote_attack_supplies',0xA79C:'commit_attack_preparation',
 0xA8D7:'consume_battle_return',0xA910:'handle_returned_leader',0xA91C:'handle_returned_leader_alternate',
 0xAB0C:'adjust_commander_loyalty',0xAB9F:'adjust_roster_loyalty',
 0xB49C:'city_assignment_strategy',0xBEC7:'city_development_strategy',
 0xBEE6:'scan_next_owned_city',0xC1A7:'increase_governance',0xC1C0:'increase_governance_for_population',
 0xC1E0:'officer_and_equipment_stage',0xC248:'choose_lowest_loyalty_officer',0xC2EB:'choose_lowest_intelligence_officer',
 0xC3FF:'choose_weapon_purchase_officer',0xC451:'lookup_next_equipment',0xC50E:'move_ruler_city_position',
 0xC5B9:'search_and_recruit_preparation',0xC5D2:'recruit_appearing_officers',0xC66F:'recruitment_probability',
 0xC6CC:'recruit_unaffiliated_officers',0xC79A:'recover_owned_city_health',0xC98F:'repair_owned_city_governors',
 0xC9A5:'choose_city_governor',0xCA19:'resolve_AI_leader_deaths',0xCA68:'resolve_missing_heir',
 0xCA87:'inspect_successor_candidates',0xCAAD:'test_successor_candidate',0xCB05:'release_extinct_ruler_cities',
 0xCB52:'install_successor',0xCB81:'adjust_successor_followers',0xCA7F:'await_extinction_acknowledgment',
 0xCB79:'await_successor_acknowledgment',0xCC12:'sell_grain_for_low_gold',
 0xCF3F:'recalculate_recruited_loyalty',0xCF7C:'recalculate_other_loyalty',0xD00C:'recalculate_shifted_loyalty',
 0xD0E1:'count_enemy_neighbors',0xD105:'city_pointer_and_resource_caps',0xD12D:'charge_cycle_budget',
 0xD152:'charge_task_budget',0xD165:'charge_nested_budget_one',0xD178:'charge_nested_budget_two',
 0xD18D:'charge_nested_budget_three',0xD1A4:'build_enemy_neighbor_list',0xD249:'find_ruler_city',
 0xD2AB:'officer_field_pointer',0xD304:'count_prefix_officers',0xD319:'ruler_pointer',
 0xD36F:'pay_city_gold',0xD3A9:'pay_city_grain',0xD3DD:'compact_city_roster',
 0xD40F:'divide_domestic_word',0xD438:'multiply_domestic_word',0xD4AD:'random_low_nibble_below',
 0xD4BB:'random_below',0xD4CB:'build_owned_connectivity',0xD583:'common_connectivity_bits',
 0xD69D:'cap_city_word',
}
def collect(rom):
    I={};todo=[0xA000];tables=[];occupied={}
    def local(pc):return pc==0xA000 or 0xA00F<=pc<0xD717 and pc!=0xD494
    while todo:
        pc=todo.pop()
        if pc in I:continue
        off=offset(10,pc);op,mode=OPS[rom[off]];size=SIZES[mode]
        if op=='?':raise ValueError(f'Invalid/data opcode at{pc:04X}')
        operand=int.from_bytes(rom[off+1:off+size],'little');nxt=pc+size
        if op in BRANCHES:operand=(nxt+(operand if operand<128 else operand-256))&65535
        x=dict(pc=pc,bank=10+int(pc>=0xC000),file=off,op=op,mode=MODES.get(mode,mode),operand=operand,next_pc=nxt)
        if pc in (0xA039,0xA1BC):
            assert op=='JSR' and operand==0xD494
            targets=[int.from_bytes(rom[off+3+2*k:off+5+2*k],'little')for k in range(3)]
            x.update(op='DISPATCH',targets=targets,dispatch_helper=0xD494)
            tables.append(dict(dispatch_pc=pc,cpu=pc+3,file=off+3,count=3,targets=targets,
                raw_hex=rom[off+3:off+9].hex(' ').upper(),bound='three words; A1C5/A042 next code; destinations checked from original bytes'))
        elif op=='JSR'and operand==0xEE07:
            x.update(op='FARCALL',inline_target=int.from_bytes(rom[off+3:off+5],'little'),next_pc=pc+5,hook='genuine far dependency')
        elif op in('JSR','JMP')and not local(operand):x['hook']='genuine fixed dependency'
        if mode=='ind':raise ValueError(('unbounded indirect',hex(pc)))
        rawsize=5 if x['op']=='FARCALL'else size
        x.update(raw_hex=rom[off:off+rawsize].hex(' ').upper(),assembly=instruction(rom,off,pc)[1])
        for byte in range(pc,pc+size):
            assert byte not in occupied,('instruction overlap',hex(byte));occupied[byte]=pc
        if x['op']=='DISPATCH':todo.extend(x['targets'])
        elif op in('RTS','RTI','BRK'):pass
        elif op=='JMP':
            if not x.get('hook'):todo.append(operand)
        elif op in BRANCHES:todo.extend((operand,nxt))
        else:
            todo.append(x['next_pc'])
            if op=='JSR'and not x.get('hook'):todo.append(operand)
        I[pc]=x
    for table in tables:assert not any(p in occupied for p in range(table['cpu'],table['cpu']+table['count']*2))
    return I,tables
HEADER='''"""Readable physical10/11 domestic cooperation controller.

Named original decision stages are directly implemented with Python conditions
and loops. ROM provides immutable tables and mapped data only. No opcodes, IR,
original CPU or simulated UI/IRQ acknowledgement execute in production.
"""
from .global_ui_controller import UIControlBase,UIRegisters,C,Z,I,D,B,U,V,N
from .battle_nmi_services import ServiceWait

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
RULER,AI_REQUEST,AI_PHASE,AI_BUDGET,SELECTED_CITY=0x6F03,0x6F8B,0x6F5B,0x6F5D,0x6F5E
YEAR,MONTH,DIFFICULTY,CITY_WRAP_COUNT=0x6F00,0x6F01,0x6F02,0x6F62
WEIGHT_MILITARY,WEIGHT_ASSIGNMENT,WEIGHT_DEVELOPMENT=0x6F5F,0x6F60,0x6F61
RANDOM_PRIMARY,RANDOM_SECONDARY,RANDOM_TERTIARY=0x52,0x54,0x55

'''
CLASS='''class DomesticCooperationController(UIControlBase):
    """One original cooperative call, retaining real caller/stack and waits.

    A000 is the genuine main2 banked trampoline; A00F is its decision body.
    An invocation can finish, request battle/UI handling, or await6F8B==1.
    resume only observes externally generated acknowledgement; it never writes
    that flag or advances a hardware/NMI event on behalf of another owner.
    """
    PAIR=(10,11)
    PUBLIC_ENTRIES=(0xA000,0xA00F)
    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],ruler=m[RULER],
                    request=m[AI_REQUEST],phase=m[AI_PHASE],budget=m[AI_BUDGET],
                    selected_city=m[SELECTED_CITY],strategy_weights=tuple(m[0x6F5F+i]for i in range(3)),
                    city_wrap_count=m[0x6F62],ruler_city_cursor=m[0x6F83+m[RULER]]if m[RULER]<7 else None,
                    random_cursors=tuple(m[i]for i in (0x52,0x54,0x55)))
    def _dispatch(self,pc,targets):
        # D494 retains Y using20..24, unlike fixed EADE's00..04 protocol.
        r=self.registers;m=self.memory;index=r.a
        if pc not in(0xA039,0xA1BC)or index>=3:raise ValueError('Outside original three-way domestic dispatch')
        self._push((pc+2)>>8);self._push(pc+2)
        m[0x20]=r.y;r.a=self._shift(r.a,True);self._y(r.a);self._y(r.y+1)
        self._a(self._pop());m[0x21]=r.a;self._a(self._pop());m[0x22]=r.a
        self._a(m[((m[0x21]|m[0x22]<<8)+r.y)&65535]);m[0x23]=r.a
        self._y(r.y+1);self._a(m[((m[0x21]|m[0x22]<<8)+r.y)&65535]);m[0x24]=r.a
        self._y(m[0x20]);r.pc=m[0x23]|m[0x24]<<8
        if r.pc!=targets[index]:raise ValueError('Pinned inline dispatch words unavailable in current caller mapping')
        return index
    def _drive(self):
        while True:
            if self.pending is not None:
                call=self.pending
                if isinstance(call,ServiceWait):
                    if self.memory[call.address]!=call.value:return self._result('waiting')
                    self.pending=None
                else:
                    if self.services is None:return self._result('dependency')
                    result=self.services(call)
                    if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                    if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                    self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def run_entry(self,entry=None,*,registers=None,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('An actual caller register/stack context is required')
        if tuple(getattr(self.memory,'banks',())[1:3])!=self.PAIR:raise ValueError('Domestic decision requires physical10/11 caller mapping')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)

'''
MANUAL={0xA00F:'''    def cooperate_domestic_ai(self):
        """A00F: early return, battle return, or ordered housekeeping then phase.

        The ordered preprocessing is real: connectivity, ruler placement,
        search/recruit, health, governors, ruler-city lookup, grain conversion.
        Three-way strategy selection occurs only after those persistent effects.
        """
        r=self.registers;m=self.memory;self._mark(0xA00F);self._a(m[AI_REQUEST])
        if r.p&N:return (yield from self.return_ai_call())
        self._compare(r.a,1)
        if r.p&Z:
            if not(yield from self._local_call(self.build_owned_connectivity,0xA018,0xA01B)):return
            return (yield from self.consume_battle_return())
        for method,call_pc in ((self.build_owned_connectivity,0xA01E),(self.move_ruler_city_position,0xA021),
                (self.search_and_recruit_preparation,0xA024),(self.recover_owned_city_health,0xA027)):
            if not(yield from self._local_call(method,call_pc,call_pc+3)):return
        self._a(m[RULER])
        if not(yield from self._local_call(self.repair_owned_city_governors,0xA02D,0xA030)):return
        if not(yield from self._local_call(self.find_ruler_city,0xA030,0xA033)):return
        if not(yield from self._local_call(self.sell_grain_for_low_gold,0xA033,0xA036)):return
        self._a(m[AI_PHASE]);index=self._dispatch(0xA039,(0xA043,0xA19C,0xA042))
        return (yield from (self.initialize_strategy_weights,self.choose_three_way_strategy,self.return_ai_call)[index]())

'''}
for pc,name in ((0xCA7F,'await_extinction_acknowledgment'),(0xCB79,'await_successor_acknowledgment')):
    MANUAL[pc]=f'''    def {name}(self):
        """${pc:04X}: genuine cooperative wait for external6F8B==1.

        The emittedFB/FC event is retained. No implicit UI/NMI progress or fake
        acknowledgement is supplied. Resume repeats the original LDA/CMP/BNE.
        """
        r=self.registers;m=self.memory
        while True:
            self._mark(0x{pc:04X});self._a(m[AI_REQUEST]);self._compare(r.a,1)
            if r.p&Z:break
            r.pc=0x{pc:04X}
            yield ServiceWait('domestic_ack',0x{pc:04X},AI_REQUEST,1,'Original succession/extinction acknowledgement',r.sp)
        self._rts()

'''
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest()==SHA;OUT.mkdir(parents=True,exist_ok=True)
    I,tables=collect(rom);domain=dict(pair=10,entries=(0xA000,0xA00F),names=NAMES,class_name='DomesticCooperationController')
    b=compiler(I,tables,domain);b.procedure=labelled_procedure.__get__(b,type(b))
    procedures=[]
    for pc in sorted(b.roots):
        if pc in MANUAL:
            # Still compile offline to document natural loops/positions; replace
            # with the separately handwritten semantic stage only in source.
            b.procedure(pc);procedures.append(MANUAL[pc])
        else:procedures.append(b.procedure(pc))
    source=HEADER+loop_exception_source(b.stats)+CLASS+'    def _entry(self,entry):\n'
    for k,pc in enumerate(sorted(b.roots)):source+=f'        {"if"if k==0 else"elif"} entry==0x{pc:04X}:return self.{b.names[pc]}()\n'
    source+='        raise ValueError("Outside the original domestic procedure catalogue")\n\n'+''.join(procedures)
    source=source.replace('m[CITY]','m[0x50E]').replace('m[RULERS]','m[0x507]')
    for address,name in {0x6F03:'RULER',0x6F8B:'AI_REQUEST',0x6F5B:'AI_PHASE',0x6F5D:'AI_BUDGET',0x6F5E:'SELECTED_CITY',0x6F00:'YEAR',0x6F01:'MONTH',0x6F02:'DIFFICULTY',0x6F62:'CITY_WRAP_COUNT',0x6F5F:'WEIGHT_MILITARY',0x6F60:'WEIGHT_ASSIGNMENT',0x6F61:'WEIGHT_DEVELOPMENT',0x52:'RANDOM_PRIMARY',0x54:'RANDOM_SECONDARY',0x55:'RANDOM_TERTIARY'}.items():
        source=source.replace(f'm[0x{address:04X}]',f'm[{name}]')
    source=source.replace('choose three way strategy; retains flags/aliases/caller stack.', 'three strategies: original low4 rejection sampling then two byte thresholds; keeps real caller.')
    source=source.replace('charge task budget; retains flags/aliases/caller stack.', 'task budget: byte subtract; zero or borrow discards one extra caller frame and reportsFF.')
    source=source.replace('charge nested budget one; retains flags/aliases/caller stack.', 'nested budget: byte subtract; borrow discards two extra caller frames and reportsFF.')
    source=source.replace('charge nested budget three; retains flags/aliases/caller stack.', 'deep budget: byte subtract; borrow discards four extra caller frames and reportsFF.')
    SOURCE.write_text(source);tree=ast.parse(source)
    external=[dict(call_pc=x['pc'],target=x['operand'],file=x['file'],kind='call')for x in I.values()if x.get('hook')]
    catalog=dict(schema='phase14-domestic-direct-source-v1',rom_sha256=SHA,pair=[10,11],entries=[0xA000,0xA00F],
        instruction_positions=len(I),procedure_roots=len(b.roots),procedures=b.stats,inline_dispatch_tables=tables,
        external_services=external,waits=[dict(pc=pc,field=0x6F8B,required_value=1,event=0xFB if pc==0xCA7F else 0xFC)for pc in(0xCA7F,0xCB79)],
        named_stages={f'{pc:04X}':name for pc,name in NAMES.items()if pc in b.roots},
        structured_if_count=sum(isinstance(n,ast.If)for n in ast.walk(tree)),natural_while_count=sum(isinstance(n,ast.While)for n in ast.walk(tree)),
        production_IR_interpretation=False,production_original_CPU_callbacks=0)
    dump(OUT/'static-catalog.json',catalog)
    dump(OUT/'offline-control-graph.json',dict(rom_sha256=SHA,instructions=sorted(I.values(),key=lambda x:x['pc']),tables=tables))
    ranges=[];listing=[]
    for x in sorted(I.values(),key=lambda x:x['pc']):
        ranges.append(dict(bank=x['bank'],cpu=x['pc'],file=x['file'],raw_hex=x['raw_hex']))
        listing.append(f'{x["file"]:06X} b{x["bank"]:02d}:${x["pc"]:04X} {x["raw_hex"]:<14} {x["assembly"]}')
    # D494 is handwritten inline control, not traversed as indirect JMP code.
    file=offset(10,0xD494);raw=rom[file:offset(10,0xD4AD)]
    ranges.append(dict(bank=11,cpu=0xD494,file=file,raw_hex=raw.hex(' ').upper(),name='D494 original custom dispatch'))
    pc=0xD494
    while pc<0xD4AD:
        at=offset(10,pc);size,asm=instruction(rom,at,pc);listing.append(f'{at:06X} b11:${pc:04X} {rom[at:at+size].hex(" " ).upper():<14} {asm} ; handwritten custom inline dispatcher');pc+=size
    assert pc==0xD4AD
    for table in tables:listing.append(f'{table["file"]:06X} b10:${table["cpu"]:04X} {table["raw_hex"]} ; three immutable pointer words')
    (OUT/'raw.asm').write_text('; Original physical10/11 domestic closure. File offsets include16-byte iNES header.\n'+'\n'.join(listing)+'\n')
    immutable=list(tables)
    for bank,cpu,length,name in ((10,0xA133,72,'three difficulty/ruler weight tables'),(10,0xA17B,33,'pressure corrections'),
        (10,0xA6C0,9,'attack count reductions'),(11,0xCAD8,14,'successor candidate pointers'),
        (11,0xCAE6,31,'FF-terminated successor candidate lists'),(16,0x8FFC,30,'city static service bits'),
        (11,0xC042,9,'development difficulty multipliers'),(10,0xBEDF,7,'city-development phase thresholds'),
        (16,0x9D72,240,'city adjacency8 entries per city'),(31,0xE8BA,256,'original random permutation')):
        file=16+bank*8192+(cpu&8191);raw=rom[file:file+length]
        immutable.append(dict(bank=bank,cpu=cpu,file=file,length=length,name=name,raw_hex=raw.hex(' ').upper()))
    pins=[SOURCE,Path(__file__),ROOT/'scripts/verify_domestic_cooperation_controller.py',ROOT/'scripts/ui_structuring.py',
        ROOT/'scripts/analyze_global_ui_controller.py',ROOT/'scripts/analyze_battle_scene_controller.py',ROOT/'source/recovered/global_ui_controller.py',
        ROOT/'source/recovered/scene_shared_services.py',ROOT/'source/recovered/service_memory.py']
    archive={}
    for name in('image.bin','mapping.json','catalog.json','evidence-bundle.json','pair-pseudocode.c'):
        f=ROOT/'analysis/rea/pairs/pair-10'/name
        if f.exists():archive[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
    dump(OUT/'evidence.json',dict(schema='phase14-domestic-direct-source-v1',rom_sha256=SHA,source_path=str(SOURCE.relative_to(ROOT)),
        analyzer_path=str(Path(__file__).relative_to(ROOT)),validator_path='scripts/verify_domestic_cooperation_controller.py',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        dependency_pins={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in pins if f.is_file()},
        ranges=ranges,immutable_tables=immutable,REA_archive_pins=archive,catalog=catalog,
        source_uses_original_CPU=False,source_uses_control_IR=False,
        production_remaining_dependencies=['Caller-supplied fixed services E88A/E89A/E8AA/F266','External true6F8B acknowledgment at CA7F/CB79'],
        input_contract='Actual registers/occupied caller stack and mapped physical10/11; no synthetic return by default; no ready/ack writes.',
        original_domain=dict(rulers=7,cities=30,officers=237,difficulties=3,primary_phases=3,strategies=3),
        source_AST=dict(no_original_CPU=True,no_runtime_IR=True,one_time_entry_selection=True)))
    print(json.dumps({k:catalog[k]for k in('instruction_positions','procedure_roots','structured_if_count','natural_while_count')}))
if __name__=='__main__':main()
