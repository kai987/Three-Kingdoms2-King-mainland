#!/usr/bin/env python3
"""Offline original-byte evidence for unresolved city auxiliary fields.

This analyzer decodes original bytes solely to write audit artifacts. New
production functions are manually readable rule implementations, not generated
runtime opcode/IR dispatch. Old field schemas/native records remain immutable.
"""
from pathlib import Path
from collections import Counter
import argparse, ast, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS, SIZES, instruction
from source.recovered.record_fields import ROM_SHA256, adverse_event_threshold
OUT=ROOT/'analysis/phase15/fields'
SOURCE=ROOT/'source/recovered/record_fields.py'
REFERENCES={
    'city':ROOT/'analysis/phase13/city/static-control.json',
    'panels':ROOT/'analysis/phase13/panels/static-control.json',
    'domestic':ROOT/'analysis/phase14/domestic/offline-control-graph.json',
}
RANGES=(
    (25,0xA041,0xA068,'calendar_month_boundary_prefix'),
    (25,0xA2BC,0xA30C,'monthly_event_gate'),
    (25,0xAB25,0xABA9,'adverse_event_candidate_scanner'),
    (25,0xABA9,0xAC4D,'candidate_consumer_and_type_dispatch_reference'),
    (25,0xACCD,0xAD81,'three_resource_loss_effects_reference'),
    (10,0xBD95,0xBDA3,'misaligned_city_word_assignment_gate_prefix'),
    (27,0xACF0,0xAD03,'recruitment_roster_append_prefix'),
    (27,0xDC6B,0xDC7C,'ten_slot_occupied_roster_count'),
)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def off(pair,pc):return 16+(pair+int(pc>=0xC000))*8192+(pc&8191)
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def analyze(rom):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    OUT.mkdir(parents=True,exist_ok=True);ranges=[];assembly=[];positions=set()
    for pair,start,end,name in RANGES:
        address=off(pair,start);ranges.append(dict(name=name,physical_pair=[pair,pair+1],physical_bank=pair+int(start>=0xC000),
            cpu=start,end_cpu_exclusive=end,rom_offset=address,byte_count=end-start,raw_hex=rom[address:address+end-start].hex(' ').upper(),
            scope='reference_only'if'reference'in name else'new_direct_source'))
        assembly.append(f'; {name}; pair{pair}/{pair+1}; file0x{address:06X} includes16B iNES header')
        pc=start
        while pc<end:
            address=off(pair,pc);size,text=instruction(rom,address,pc)
            assert pc+size<=end,(name,pc,size)
            assembly.append(f'{pair+int(pc>=0xC000):02d}:{pc:04X} file0x{address:06X} {rom[address:address+size].hex(" ").upper():<9} {text}')
            positions.add((pair+int(pc>=0xC000),pc))
            if rom[address] == 0x20 and rom[address+1:address+3] == b'\x07\xee':
                target = int.from_bytes(rom[address+3:address+5], 'little')
                assembly.append(f'{pair+int(pc>=0xC000):02d}:{pc+3:04X} file0x{address+3:06X} {rom[address+3:address+5].hex(" ").upper():<9} .word ${target:04X} ; inline farcallee, not opcode')
                size += 2
            pc+=size
        assembly.append('')
    (OUT/'raw.asm').write_text('\n'.join(assembly)+'\n')
    # Compile-time field access candidates in three verified bounded closures.
    # The negative result is intentionally not a whole-ROM usage proof:
    # dynamicY, pointer shifts and generic copies are outside this local pass.
    catalog={};reference_counts={};known_offsets={}
    for name,path in REFERENCES.items():
        d=json.loads(path.read_text());rows=d.get('instructions',d.get('original_instructions',[]))
        reference_counts[name]=len(rows)
        for row in rows:
            address=row.get('file',row.get('rom_offset'));known_offsets[address]=name
            assert bytes.fromhex(row['raw_hex'])==rom[address:address+len(bytes.fromhex(row['raw_hex']))]
        catalog[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),instruction_positions=len(rows))
    globals_access=[];immediate_candidates=[];absolute_candidates=[]
    for address,domain in sorted(known_offsets.items()):
        opcode,mode=OPS[rom[address]];size=SIZES[mode];bank=(address-16)//8192
        pc=(0xA000 if domain in ('city','panels','domestic')and bank in(10,25,27)else 0xC000)+(address-16)%8192
        if mode in('ab','abx','aby')and rom[address+1:address+3]==b'\x06\x6f':
            globals_access.append(dict(domain=domain,physical_bank=bank,cpu=pc,rom_offset=address,op=opcode,raw_hex=rom[address:address+size].hex(' ').upper()))
        if opcode=='LDY'and mode=='im'and rom[address+1]in(1,27,28,29,30,31):
            candidate=[];p=address+2
            for _ in range(8):
                if p not in known_offsets:break
                op,md=OPS[rom[p]];n=SIZES[md]
                if op in('JSR','JMP','RTS','RTI','BRK','LDY','INY','DEY','TAY'):break
                if md=='iy'and op in('LDA','STA','ADC','SBC','CMP','AND','ORA','EOR'):
                    candidate.append(dict(rom_offset=p,op=op,pointer_zero_page=rom[p+1],raw_hex=rom[p:p+n].hex(' ').upper()))
                if md=='rel':break
                p+=n
            if candidate:immediate_candidates.append(dict(domain=domain,physical_bank=bank,cpu=pc,rom_offset=address,Y=rom[address+1],candidates=candidate,
                limitation='Immediate-Y syntactic candidate; pointer record identity requires manual/dataflow evidence'))
        if mode in('ab','abx','aby')and opcode not in('JSR','JMP'):
            operand=int.from_bytes(rom[address+1:address+3],'little')
            if 0x6000<=operand<0x63C0 and operand%32 in(1,27,28,29,30,31):
                absolute_candidates.append(dict(domain=domain,physical_bank=bank,cpu=pc,rom_offset=address,operand=operand,op=opcode,mode=mode))
    dump(OUT/'static-catalog.json',dict(schema='phase15-record-field-static-catalog-v1',ROM_sha256=ROM_SHA256,
        ranges=ranges,reference_closures=catalog,global_6F06_accesses=globals_access,immediate_Y_field_candidates=immediate_candidates,
        absolute_city_auxiliary_candidates=absolute_candidates,negative_search_scope='Only exact instruction starts in these three bounded closures; no claim that all dynamic offsets/all ROM code are resolved',
        source_path=str(SOURCE.relative_to(ROOT)),source_sha256=sha(SOURCE),analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__)))
    raw_cities=rom[0x20C10:0x20FD0];assert len(raw_cities)==960
    initial=[dict(city=i,rom_offset=0x20C10+32*i,cpu_in_bank16=0x8C00+32*i,runtime_address=0x6000+32*i,
                  raw_hex=raw_cities[32*i:32*(i+1)].hex(' ').upper(),byte1=raw_cities[32*i+1],cooldown27=raw_cities[32*i+27],tail28_31=list(raw_cities[32*i+28:32*(i+1)]))for i in range(30)]
    dump(OUT/'initial-records.json',dict(ROM_sha256=ROM_SHA256,initial_city_records=initial))
    # Natural previously frozen Native records: only already recorded frame
    # fields are used. They do not expose internal CPU PCs or prove a hazard.
    native=ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle';frames=json.loads((native/'frame-services.json').read_text());native_changes=[];old=None
    for row in frames:
        new=(row['event_flag_6F06'],row['calendar_month_zero_based_6F01'])
        if new!=old:
            native_changes.append(dict(frame=row['frame'],month_zero_based=new[1],monthly_event_latch=new[0],
                turn_slot=row['turn_slot_6F04'],ruler=row['ruler_6F03'],city_main=row['city_state_0400_040F'][0],city_phase=row['city_state_0400_040F'][1],
                RAM_sha256=row['RAM_sha256'],SRAM_sha256=row['SRAM_sha256'],PNG_checkpoint_at_this_exact_frame=any(x['frame']==row['frame']for x in json.loads((native/'checkpoints.json').read_text()))))
        old=new
    confirmed_city=[dict(offsets=[27],name='adverse_city_event_cooldown',confidence='confirmed_mechanical',official_name=None,
        read_write_sites=[dict(physical_bank=25,cpu=0xAB57,rom_offset=off(25,0xAB57),access='read'),dict(physical_bank=25,cpu=0xAB5E,rom_offset=off(25,0xAB5E),access='decrement write'),dict(physical_bank=25,cpu=0xABA4,rom_offset=off(25,0xABA4),access='candidate write6')],
        role='Nonzero decremented on eligible scanner invocation; zero allows governance/RNG candidate gate. A formed candidate writes6.',
        aliases=[dict(physical_bank=27,cpu=0xAD01,rom_offset=off(27,0xAD01),role='Full10-slot recruitment helper appends at17+10=27, overwriting cooldown; explicit boundary, not normal-menu acceptance')],
        clock='Eligible invocations, not universally proven six months; initialyear89/month0..3 skips whole scanner; owner&15==7 skips decrement'),
        dict(offsets=[1],name='byte1_unresolved',confidence='unresolved_semantic_name',official_name=None,
             observed_role='One confirmed indirectAI read: BD97/BD9D form LE16(record1,record2) and require>=300; overlaps low gold byte. No proven named resource/flag.',
             read_sites=[dict(physical_bank=10,cpu=0xBD97,rom_offset=off(10,0xBD97)),dict(physical_bank=10,cpu=0xBD9D,rom_offset=off(10,0xBD9D))],
             initial_values=sorted(set(x['byte1']for x in initial))),
        dict(offsets=[28,29,30,31],name='unresolved_tail_28_31',confidence='unresolved',official_name=None,
             observed_role='Copied as part of whole32-byte record initialization; scanner/assignment/recruitment prefixes preserve allfour in the tested domain.',
             no_unused_or_reserved_claim=True,initial_values=[sorted(set(x['tail28_31'][i]for x in initial))for i in range(4)],
             search_limitation='No confirmed dedicated field consumer in the three audited bounded city/panel/domestic closures; dynamic-offset/all-code absence has not been proven')]
    global_fields=[dict(address=0x6F06,name='monthly_event_check_latch',confidence='confirmed_mechanical',official_name=None,
        read_sites=[dict(physical_bank=25,cpu=0xA2CF,rom_offset=off(25,0xA2CF))],write_sites=[dict(physical_bank=25,cpu=0xA055,rom_offset=off(25,0xA055),value=0,condition='turn index wraps>=7'),dict(physical_bank=25,cpu=0xA2DA,rom_offset=off(25,0xA2DA),value='INC from0',condition='text0300/0304FF and007E0')],
        role='If nonzero idle gate selectsphase2; ifzero incrementslatch then dispatches month3→6/month9→7/other→15 with0402=0.',
        native_observations=native_changes)]
    # Keep original field schemas intact, recording the limited new overlay.
    old_city=json.loads((ROOT/'analysis/phase5/domestic-ai/city-schema.json').read_text())
    old_officer=json.loads((ROOT/'analysis/officer_fields/fields.json').read_text())
    schema=dict(schema='phase15-record-fields-overlay-v1',ROM_sha256=ROM_SHA256,
        city_record_size=32,city_record_count=30,city_auxiliary_fields=confirmed_city,global_fields=global_fields,
        inherited_city_schema='analysis/phase5/domestic-ai/city-schema.json',inherited_officer_schema='analysis/officer_fields/fields.json',
        officer_remaining_fields_review=[dict(offsets=[5],status='context-dependent city/location payload; retain original strong inference',
            detail='Release paths write a city when lowstatus0. Initial value0 for everyofficer and assigned-roster residence is not guaranteed bybyte5; roster/owner remains authoritative.',
            existing_natural_native_example=dict(frame=1943,city=11,city_owner_low3=2,roster=[131,5,30],officer=131,status_low2=2,byte5=0,
                city_raw_hex=next(x['city11_record']for x in frames if x['frame']==1943),officer_raw_hex=next(x['observer_officer_records']['131']['raw']for x in frames if x['frame']==1943),
                meaning='Officer131 is rostered in city11 but byte5 is0, not11; no extra memory preparations or newcore run.')),
            dict(offsets=[9],mask=252,status='No independent official flag meanings identified; rawword numeric overflow/residual remains proven in phase5.',reference='analysis/phase5/troops/README.md'),
            dict(offsets=[11],mask=3,status='Original status encoding remains context-dependent. Code3 includes defeated/removed/unavailable routes, not universally permanentdeath.',reference='analysis/phase4/postbattle/README.md'),
            dict(offsets=[11],mask=12,status='Affinity0/1/2 glyphs known; rawcode3 officialmeaning/naturalproducer unresolved.',reference='analysis/names_terrain/README.md')],
        original_schemas_preserved=True,old_city_field_count=len(old_city['fields']),old_officer_field_count=len(old_officer['fields']))
    dump(OUT/'schema.json',schema)
    production_ast=ast.parse(SOURCE.read_text());forbidden=[]
    for node in ast.walk(production_ast):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[node.module or'']if isinstance(node,ast.ImportFrom)else[a.name for a in node.names]
            forbidden.extend(name for name in names if any(x in name.lower()for x in('py65','state_machine','cpu_trace','structuring')))
    assert not forbidden
    pins=[SOURCE,ROOT/'scripts/verify_record_fields.py',Path(__file__),ROOT/'source/recovered/global_ui_controller.py',ROOT/'source/recovered/scene_shared_services.py',ROOT/'source/recovered/controller_helpers.py',ROOT/'source/recovered/battle_nmi_services.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'source/recovered/service_memory.py']
    artifacts=[*REFERENCES.values(),ROOT/'analysis/officer_fields/fields.json',ROOT/'analysis/phase5/domestic-ai/city-schema.json',
               native/'frame-services.json',native/'checkpoints.json',native/'validation.json',native/'repeat-validation.json',ROOT/'analysis/phase14/runtime/evidence.json']
    for pair in (10,25,27):
        for filename in('mapping.json','evidence-bundle.json','procedure-index.json'):
            path=ROOT/f'analysis/rea/pairs/pair-{pair:02d}'/filename
            if path.exists():artifacts.append(path)
    dependency_pins={str(p.relative_to(ROOT)):sha(p)for p in artifacts}
    evidence=dict(schema='phase15-record-fields-evidence-v1',ROM_sha256=ROM_SHA256,source_status='Independent readable recovered functions; not original development source or a complete campaign simulator',
        source_path=str(SOURCE.relative_to(ROOT)),source_sha256=sha(SOURCE),analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),
        source_and_validator_sha256={str(p.relative_to(ROOT)):sha(p)for p in pins},artifact_and_dependency_sha256=dependency_pins,
        ranges=ranges,immutable_tables=[dict(name='initial_30_city_records',physical_bank=16,cpu=0x8C00,rom_offset=0x20C10,byte_count=960,raw_hex=raw_cities.hex(' ').upper())],
        field_overlay_path='analysis/phase15/fields/schema.json',city_auxiliary_fields=confirmed_city,global_fields=global_fields,
        adverse_candidate_thresholds=[dict(governance_min=a,governance_max=b,threshold=adverse_event_threshold(a))for a,b in((0,19),(20,29),(30,39),(40,49),(50,255))],
        candidate_success_condition='E862(A100) accepted byte <threshold; original rejection permutation/cursor stream. No unbiased-percent/independent-randomness claim.',
        downstream_reference=dict(type1=dict(entry=0xACCD,word_offsets=[6]),type2=dict(entry=0xACE9,word_offsets=[2,4]),type3=dict(entry=0xAD14,word_offsets=[8,14]),
            message_id_expression='E8 + effecttype1..3 atAC92..AC97',official_event_names='unresolved in this investigation',not_newly_restored_or_CPU_validated_here=True),
        implementation=dict(complete_entries=[dict(pair=[25,26],cpu=0xA2BC,name='monthly_event_gate'),dict(pair=[25,26],cpu=0xAB25,name='scan_adverse_event_candidates')],
            bounded_prefixes=[dict(pair=[10,11],start=0xBD95,stop=[0xBDA3,0xBDEE],name='assignment_word_gate_prefix'),dict(pair=[25,26],start=0xA041,stop=[0xA068,0xA06B],name='calendar_turn_scan_prefix'),dict(pair=[27,28],start=0xACF0,stop=[0xAD03],name='recruitment_append_prefix')],
            fixed_source_services=[0xF2AF,0xE862],source_original_CPU_callbacks=0,source_control_IR_callbacks=0,unknown_services_fabricated=False),
        native_reuse=dict(parent_phase=14,natural_gameplay=True,RAM_injections=0,SRAM_injections=0,new_native_runs_in_this_area=0,native_internal_CPU_trace=False,
            frames=native_changes,limitation='Only existing original-core frame fields prove latch/month observations. They do not identify instruction PCs or show a successful adverse city event.'),
        AST_check=dict(forbidden_runtime_dependencies=forbidden),
        reproducible_commands=["python3 scripts/analyze_record_fields.py '/Users/paulasmith/Downloads/三国志2超级版.nes'", ".venv-trace/bin/python scripts/verify_record_fields.py '/Users/paulasmith/Downloads/三国志2超级版.nes'"],
        limitations=['Byte1 andtail28..31 officialsemanticnames remainunresolved.', 'City27 counter is scanner-call based; six universallyelapsedmonths are not established.',
            'Full-roster recruitment is an explicit boundary invocation; normalUI capacity acceptance is not claimed.', 'Reference lossprocedures are read-only evidence, not new verified service implementations.',
            'Three prefix APIs stop before their excluded parent work and retainactualPC/SP. They are notRTS completions.', 'Oldschema,oldNativeandv14archive are notmodified.'])
    dump(OUT/'evidence.json',evidence)
    print(json.dumps(dict(ranges=len(ranges),city_records=len(initial),native_latch_changes=len(native_changes),global_latch_sites=len(globals_access),source_sha256=sha(SOURCE)),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);args=p.parse_args();analyze(args.rom.read_bytes())
