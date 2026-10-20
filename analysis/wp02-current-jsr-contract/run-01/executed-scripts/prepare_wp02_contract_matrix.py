#!/usr/bin/env python3
"""Declare finite independent axes BEFORE any new CPU execution."""
from pathlib import Path
import collections,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import analyze_inline_dispatch_contracts_phase32 as old_static
OUT=ROOT/'analysis/wp02-current-jsr-contract'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):
    p=OUT/name;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    assert json.loads((OUT/'frozen-before.json').read_text())['status']=='passed'
    rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes()
    assert hashlib.sha256(rom).hexdigest()==old_static.ROM_SHA
    proof=old_static.prepared_contract(rom)
    cases=[]
    def add(group,key,entry,call,index,sp=253,y=41,p=0x20,**kw):
        cases.append(dict(group=group,key=key,entry=entry,call_pc=call,index=index,
            data_bank=(index+sp+y)&31,registers=dict(pc=entry,a=index,x=0xC3,y=y,p=p,sp=sp),**kw))
    for call,limit in ((0xA09E,8),(0xACAB,16)):
        for a in range(256):add('raw_A',f'raw/{call:04X}/{a}',call,call,a,(a*13)&255,(a*17)&255,a)
        for a in range(limit):
            for sp in range(256):add('legal_index_all_SP',f'sp/{call:04X}/{a}/{sp}',call,call,a,sp,182,0xEF)
            for y in range(256):add('legal_index_all_Y',f'y/{call:04X}/{a}/{y}',call,call,a,201,y)
        for sp in (0,1,253,255):add('stale_stack_6000_fully_overwritten',f'stale/{call:04X}/{sp}',call,call,3,sp,137,stale_stack_word=0x6000)
        for sp in (0,253):
            for byte in ('high','low'):
                add('one_byte_frame_fault',f'fault/{call:04X}/{sp}/{byte}',call,call,0 if call==0xA09E else 7,sp,49,
                    stale_stack_word=0x6000,post_JSR_restore_stale_byte=byte)
            for mode in ('intact','fault'):
                add('same_bus_two_generations',f'generations/{call:04X}/{sp}/{mode}',call,call,3,sp,49,two_generations=mode)
            add('old_live_pointer_overwritten',f'oldlive/{call:04X}/{sp}',call,call,13,sp,19,initial_live_pointer=0x6000)
            add('between_reads_pointer_fault',f'between/{call:04X}/{sp}',call,call,13,sp,19,between_reads_pointer=0x6000)
    for a in range(256):add('A099_AND0F',f'A099/{a}',0xA099,0xA09E,a&15,253,5,strategy_raw=a)
    for x in range(256):
        for target_quad in range(4):
            for actor_quad in range(4):
                add('AC7B_two_terrain_calls',f'AC7B/{x}/{target_quad}/{actor_quad}',0xAC7B,0xACAB,x,(x*7)&255,165,
                    target_quadrant=target_quad,actor_quadrant=actor_quad)
    for row in proof['AC7B_live_2C_lifecycle']['actual_adjacent_LDX_JSR_prefixes']:
        add('adjacent_real_LDX_JSR_AC7B',f'prefix/{row["prefix_entry"]:04X}',row['prefix_entry'],0xACAB,row['input_X'],37,165,
            outer_call_pc=row['call_PC'],target_quadrant=1,actor_quadrant=2)
    for a in (0,13,14,15):add('bare_B517_aux_counterexample',f'bare/{a}',0xB517,None,a,253,57,bare_stack_word=0x6000)
    for pc,y in ((0xB525,1),(0xB52B,28),(0xB525,29),(0xB52B,30),(0xB525,31)):
        add('middle_access_aux_counterexample',f'middle/{pc:04X}/{y}',pc,None,59,251,y,initial_live_pointer=0x6000)
    counts=dict(collections.Counter(x['group']for x in cases));assert len(cases)==17207
    assert len({x['key']for x in cases})==len(cases)
    save('case-matrix.json',dict(schema='wp02-preexecution-case-matrix-v1',cases=cases,case_count=len(cases),groups=counts,
        independent_axes_not_full_state_Cartesian=True,software_terrain_descriptor_ids=[0,1,32,64],
        actual_capture_origin=None,Native_runs=0,Source_cases=0,
        controlled_initialization='Deterministic base RAM/SRAM, literal REG/4PRG; per-case mutations fully recorded before execution.',
        logical_device_policy='No hardware reads; only original F266 writes DE and E000 (raw selector retained; PRG window selector&31).',
        missing_input_policy='Strict failure, never supply result/ready/RNG/device samples.',
        stop_policy='Execute B533 JMP then stop BEFORE target first opcode; middle cases execute only their selected LDA.',
        interrupt_policy='No interrupts in proof window; interrupt/external mutation excluded premise, not new interrupt coverage.',
        source_credit='Existing readable dispatch is unchanged; new tests are original-CPU contracts, not new Source services.'))
    save('static-contract.json',proof)
    save('acceptance.json',dict(schema='wp02-acceptance-v1',required_case_count=17207,required_groups=counts,
        required=['Original JSR opcode and high/low writes per dynamic generation; each PLA actual read provenance.',
                  'Live21/22 and actual selected logical reads; complete RAM/SRAM postconditions and allowed writes.',
                  'Raw A256, independent legal index/SP256 and index/incomingY256, AND0F separate legal table domains.',
                  'Complete AC7B two B6E5/F266 calls, all quadrant pairs, live2C, X clobber, A reload, mapping effect.',
                  'Same bus/CPU two generations; complete stale overwrite and partial frame/between-read fault counterexamples.',
                  'Bare6000 and middle selected reads preserve all five auxiliary-offset counterexamples.',
                  'Actual B533 transfer prefix; no RTS/target-completion credit.',
                  'Exact case key/group completeness, current hashes; no acceptance from a nonempty partial receipt.'],
        migration=dict(base='analysis/phase31/fields-static/all-indirect-accesses.json',selected=[[8,0xB525],[8,0xB52B]],
            require_other_1524_full_objects_unchanged=True,conditional_only=True,maximum_promotions=2,
            if_incomplete='No migration and original325 count retained',official_names_remain_null=True),
        matrix_sha256=sha(OUT/'case-matrix.json'),static_contract_sha256=sha(OUT/'static-contract.json'),
        old_static_definition_sha256=sha(ROOT/'scripts/analyze_inline_dispatch_contracts_phase32.py')))
    print(json.dumps(dict(status='declared_before_CPU',cases=len(cases),groups=counts,matrix_sha256=sha(OUT/'case-matrix.json'))))
if __name__=='__main__':main()
