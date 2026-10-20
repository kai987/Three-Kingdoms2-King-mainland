#!/usr/bin/env python3
"""Scope/acceptance and finite matrix declaration only; no CPU/Source run."""
from pathlib import Path
import ast,collections,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-shared-entry-family'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(n,x):
    p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def off(b,p):return 16+b*8192+(p&8191)
def rec(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def identity(r):return f'I:{ROM_SHA}:b{r["physical_bank"]:02X}:cpu{r["cpu"]:04X}:rom{r["rom_offset"]:06X}'
def main():
    assert read(OUT/'frozen-before.json')['status']=='passed'
    rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
    atlas=read(ROOT/'analysis/phase18/control/instruction-atlas.json');edges={(x['physical_bank'],x['cpu']):x['targets']for x in atlas['edges']}
    census=[]
    for row in atlas['instructions']:
        if row['op']!='JSR'or row.get('operand')!=0xEADE:continue
        b,p=row['physical_bank'],row['cpu'];targets=edges[b,p];start=p+3
        assert bytes(rom[off(b,p):off(b,p)+3])==bytes.fromhex('20deea')
        assert (p&8191)+3+2*len(targets)<=8192
        words=[int.from_bytes(rom[off(b,start+2*i):off(b,start+2*i)+2],'little')for i in range(len(targets))]
        assert words==[x[1]for x in targets]
        census.append(dict(bank=b,pc=p,rom_offset=off(b,p),targets=words,edge_targets=targets,legal_indices=list(range(len(words))),table_start=start,table_end=start+2*len(words)))
    assert len(census)==98 and sum(len(x['targets'])for x in census)==745
    callers=[];sources=[]
    for group,base,banks,source in (('battle','battle_fsm',(12,13),'battle_scene_controller'),('attack','attack_fsm',(14,15),'attack_scene_controller'),('duel','duel_fsm',(23,24),'duel_scene_controller')):
        path=ROOT/f'analysis/{base}/program.json';sources.append(rec(path))
        tree=ast.parse((ROOT/f'source/recovered/{source}.py').read_text());tuples={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr=='_dispatch'and len(node.args)>1:
                try:tuples[ast.literal_eval(node.args[0])]=(list(ast.literal_eval(node.args[1])),node.lineno)
                except(ValueError,TypeError):pass
        for index,row in enumerate(read(path)['instructions']):
            if row['op']!='DISPATCH':continue
            p=row['pc'];b=row.get('bank',banks[0]if p<0xC000 else banks[1]);targets=row['targets']
            found=next(x for x in census if (x['bank'],x['pc'])==(b,p));assert targets==found['targets']==tuples[p][0]
            callers.append(dict(**found,group=group,code_pair=list(banks),Source_method=f'{source}._dispatch',Source_line=tuples[p][1],catalog=rec(path),locator=f'/instructions/{index}'))
    assert len(callers)==48 and sum(len(x['targets'])for x in callers)==328
    native_dir=ROOT/'analysis/wp05-natural-nonempty/runtime/natural-day31-nonempty/observer'
    indexes=[json.loads(x)for x in(native_dir/'snapshot-index.jsonl').read_text().splitlines()]
    initial=next(x for x in indexes if x['snapshot_sequence']==22);target=next(x for x in indexes if x['snapshot_sequence']==23)
    assert initial['entry']==0xBC49 and initial['actual_registers']==dict(a=2,x=64,y=3,p=33,sp=236,pc=0xBC49)
    for row in(initial,target):
        assert sha(native_dir/row['exported_RAM'])==row['RAM_sha256']and sha(native_dir/row['exported_SRAM'])==row['SRAM_sha256']
    extra=next(x for x in census if(x['bank'],x['pc'])==(8,0xBC49));assert len(extra['targets'])==3
    callers.append(dict(**extra,group='postbattle',code_pair=[8,9],Source_method='battle_scene_controller._dispatch inherited by PostbattleEarlyServices',Source_line=91,catalog=rec(ROOT/'source/recovered/postbattle_early_services.py'),locator='allocate_AI_officers'))
    assert len({(x['bank'],x['pc'])for x in callers})==49
    previous=read(ROOT/'analysis/wp02-current-jsr-contract/remaining-accesses.json')['accesses']
    selected=[x for x in previous if x['physical_bank']==31 and x['cpu']in(0xEAE9,0xEAEE)];assert len(selected)==2
    raw=read(ROOT/'analysis/wp02-current-jsr-contract/raw345-executability-ledger.json')['windows']
    operand_relations=[]
    for row in raw:
        for c in census:
            if row['physical_bank']==c['bank']and row['rom_offset']==c['rom_offset']+1:
                assert row['raw_hex'].split()[:2]==['DE','EA']
                operand_relations.append(dict(raw_id=f'W:{ROM_SHA}:b{row["physical_bank"]:02X}:off{row["bank_offset"]:04X}:rom{row["rom_offset"]:06X}',
                    existing_category=row['phase22_executability_category'],caller_bank=c['bank'],caller_pc=c['pc'],
                    third_byte_role='index0 table low byte, consumed by EAE9 after actual current JSR',instruction_opcode_execution_proven=False,
                    shared_semantic_root=None,classification_change=False))
    assert len(operand_relations)==3
    save('family-scope.json',dict(schema='wp03-EADE-family-scope-v1',family='Current original JSR EADE to live01/02 to EAE9/EAEE to EAF4 transfer',
        shared_dependency_id='DEP-EADE-CURRENT-JSR-49CALLERS',gap_ids=['G-ACCESS-CONTRACTS','G-SERVICE-CLOSURE'],
        selected_typed_ids=[identity(x)for x in selected],selected_prior_records=selected,explicitly_excluded='31:E04D is a separate instruction/entry; palette/audio/EE07 families not executed.',
        selection_history='Audio descriptors initially considered read-only, replaced before scope lock or CPU/Source execution by broader shared scene-dispatch interface.',
        static_caller_inventory=98,static_declared_inline_words=745,dynamic_selected_callers=49,dynamic_legal_inline_slots=331,
        original_catalog_sources=sources,dynamic_callers=callers,
        original_helper=dict(bank=31,start=0xEADE,end_exclusive=0xEAF7,raw_hex=rom[off(31,0xEADE):off(31,0xEAF7)].hex()),
        natural_reference=dict(initial=initial,target=target,snapshot_index=rec(native_dir/'snapshot-index.jsonl'),evidence=rec(ROOT/'analysis/wp05-natural-nonempty/evidence.json'),
            new_Native_runs=0,credit='Existing WP05 natural local357 index2 only. Native records actual pushes/PLA boundaries/target, not selected LDA or Pull8 bus read traces.'),
        ledger_policy='No global migration: untested callers, computed/bare/middle/alternate mapping entries remain outside proved interface. Preserve all1526 and raw345 bytes.',
        field_counts=dict(total=1526,conditional_disjoint=1203,possible=80,unknown=243,remaining=323),
        raw_counts=dict(total=345,operand=104,data=13,unproved_entry=228),raw228_semantic_mapping=None,
        official_city_names={str(x):None for x in(1,28,29,30,31)},whole_game_closure_proven=False,unknown_unique_services=None,
        completion_percentage=None,remaining_rounds_estimate=None))
    save('known-direct-caller-inventory.json',dict(callers=census,count=98,inline_words=745,
        scope='Trusted atlas direct JSR inventory only; not proof against computed, arbitrary mapping or bare entry.',input_atlas=rec(ROOT/'analysis/phase18/control/instruction-atlas.json')))
    save('cross-ledger-relations.json',dict(selected_instruction_ids=[identity(x)for x in selected],
        raw228_to_selected_semantic_relation=None,raw228_classification_changes=0,operand_byte_relations=operand_relations,
        caution='Three existing operand windows have actual opcode-operand/index0 table byte provenance; not raw opcode execution or one semantic defect. Physical nonoverlap does not prove semantic disjointness.'))
    cases=[]
    def add(group,c,index,sp=253,y=61,p=0x20,**kw):
        cases.append(dict(key=f'{group}/{len(cases):05d}',group=group,caller_index=c,index=index,
            registers=dict(pc=callers[c]['pc']if c is not None else kw['entry'],a=index,x=93,y=y,p=p,sp=sp),**kw))
    for i,c in enumerate(callers):
        for index in range(256):add('raw_A_address_axis',i,index,(index*13)&255,(index*17)&255,index)
        for index in c['legal_indices']:
            for sp in(0,1,127,253,255):add('legal_slots_stack_edges',i,index,sp)
    representatives=[next(i for i,x in enumerate(callers)if x['group']==group)for group in('battle','attack','duel','postbattle')]
    for i in representatives:
        for y in range(256):add('incoming_Y_axis',i,0,201,y)
        for sp in range(256):add('SP_axis',i,0,sp)
    bc=len(callers)-1
    cases.append(dict(key='actual-WP05-BC49-snapshot22',group='actual_WP05_prefix_replay',caller_index=bc,index=2,registers=initial['actual_registers'],actual_initial_context=True))
    for a in(0,13,14,15):add('bare_EADE_aux_counterexample',None,a,253,57,entry=0xEADE,bare_stack_word=0x6000)
    for pc,y in((0xEAE9,1),(0xEAEE,28),(0xEAE9,29),(0xEAEE,30),(0xEAE9,31)):
        add('middle_aux_counterexample',None,0,253,y,entry=pc,middle_pointer=0x6000)
    for sp in(0,253):
        for fault in('high60','same_value_high','between_reads'):
            add('current_frame_fault',bc,8 if fault=='high60'else 13 if fault=='between_reads'else 2,sp,fault=fault)
        for mode in('intact','high60'):
            add('same_bus_two_generations',bc,0,sp,two_generations=mode)
        add('stale6000_full_JSR_overwrite',bc,2,sp,stale_stack_word=0x6000)
    assert len(cases)==16269
    save('case-matrix.json',dict(cases=cases,case_count=len(cases),groups=dict(collections.Counter(x['group']for x in cases)),
        basis='Independent finite axes, not a full-state Cartesian test.',initial_memory='Deterministic RAM/SRAM except exact WP05 snapshot case; all initial and fault mutations disclosed.',
        Source_policy='Only valid legal prefix cases: real existing battle/attack synchronous _dispatch; duel actual ControlHelpers EADE branch only after test caller pushes. Never enter duel handler or use Source CPU/IR fallback.',
        comparison='Full2K/8K, AXYP/SP/PC/4PRG at completed EAF4 transfer; Source helper middle instruction state is not claimed equivalent.',
        stop='Execute actual EAF4 JMP then stop before target first opcode; middle cases execute selected LDA only.',
        excluded_interrupts='No IRQ/NMI/external mutation in positive proof window. Faults explicitly separate. No Native timing/PCM/whole-scene claim.'))
    save('acceptance.json',dict(schema='wp03-preexecution-acceptance-v1',scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),
        required_cases=16269,required_callers=49,required_legal_slots=331,required_static_callers=98,
        required=['Actual JSR two pushes and actual PLA last-writer per generation.',
                  'Live01/02 still current word at both selected reads; ZP00..04 do not alias0100stack for all testedSP.',
                  'Legal-index/RAWA address domains separate, 127/255 secondY wraps0.',
                  'Full Source boundary comparison only where legal and valid; no fake target completion.',
                  'Actual unmodified WP05 REG/PRG/2K8K replay to exact target snapshot23, with provenance limits.',
                  'Bare/middle/partial/same-value/between-read faults and controlled two-generation reuse retain counterexamples.',
                  'All old objects and both ledgers preserved; raw228 mapping null; typed E04D untouched.'],
        unknown_real_dependencies='Strict prefix if encountered; do not implement a fake return or CPU-driven Source.',Source_new_services=0,Native_new_runs=0))
    print(json.dumps(dict(status='scope_and_acceptance_locked_before_execution',cases=len(cases),callers=49,legal_slots=331,scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'))))
if __name__=='__main__':main()
