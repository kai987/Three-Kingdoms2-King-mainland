#!/usr/bin/env python3
"""Document one conditional roster-write domain; never run old producers."""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase31/fields-static'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BASE_AUDIT = '6cabf530d87046ca0df8d13775b8180b793c92a4a51ed1ab2772533bfb00d4d5'
TARGET = (8, 0xBDB8)
AUX = {0x6000 + 32 * city + offset for city in range(30) for offset in (1, 28, 29, 30, 31)}
CALLS = [(0xBC65, 0xBC68), (0xBD8E, 0xBD91), (0xBC8E, 0xBC91), (0xBCC9, 0xBCCC)]


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def off(bank, pc):
    return 16 + bank * 8192 + (pc & 8191)


def normal(address):
    return address & 2047 if address < 8192 else address


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def address_contract():
    pointers = [0x6000 + 32 * raw for raw in range(256)]
    ys = list(range(17, 27))
    intersection = sorted({normal((pointer + y) & 65535) for pointer in pointers for y in ys} & AUX)
    return dict(whole_pointer_values=pointers, whole_pointer_count=len(pointers), Y_values=ys,
                low_high_relationship='Complete F2AF word for raw city byte; no Cartesian byte product.',
                possible_auxiliary_effective_addresses=intersection,
                auxiliary_address_intersection_count=len(intersection),
                authority='Conditional complete BC46 normal-mode lifecycle, not bare BD96 or middle entry.',
                supersets='All256 F2AF city words conservatively include the normal30-city parent domain.',
                logical_effective_address_only=True)


def admissible_context(context):
    return (context.get('root') == 0xBC46 and context.get('code_pair') == [8, 9]
            and context.get('mode') in (0, 1, 2) and context.get('current_city') in range(30)
            and context.get('source_city') in range(30)
            and len(context.get('rulers', [])) == 2
            and all(value in range(7) for value in context['rulers'])
            and context.get('complete_entry') is True and context.get('binary') is True
            and context.get('interrupted') is False and context.get('middle_entry') is False
            and context.get('immutable_adjacency_table') is True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest() == ROM_SHA
    assert sha(ROOT / 'analysis/phase30/verification.json') == BASE_AUDIT
    OUT.mkdir(parents=True, exist_ok=True)
    prior_path = 'analysis/phase30/fields-static/all-indirect-accesses.json'
    prior = read(prior_path)
    rows = copy.deepcopy(prior['accesses'])
    catalog = read('analysis/phase30/early-services/static-catalog.json')
    instructions = [row for row in catalog['original_instructions'] if 0xBC46 <= row['cpu'] < 0xBF0A]
    for row in instructions:
        assert rom[row['rom_offset']:row['rom_offset'] + row['bytes']] == bytes.fromhex(row['raw_hex'])
        assert row['rom_offset'] == off(row['physical_bank'], row['cpu'])
    by = {row['cpu']: row for row in instructions}
    for call, return_pc in CALLS:
        assert bytes.fromhex(by[call]['raw_hex']) == bytes([0x20, 0x96, 0xBD])
        assert return_pc == call + 3
    helper = []
    # Complete F2AF contains no indirect or indexed store and no further call.
    pc = 0xF2AF
    sizes = {0xA0: 2, 0x8C: 3, 0x0A: 1, 0x2E: 3, 0x18: 1, 0x69: 2,
             0x8D: 3, 0xAD: 3, 0x60: 1}
    while pc <= 0xF2D6:
        index = off(31, pc)
        length = sizes[rom[index]]
        helper.append(dict(physical_bank=31, cpu=pc, rom_offset=index,
                           raw_hex=rom[index:index + length].hex(' ').upper()))
        pc += length
    assert pc == 0xF2D7
    table_offset = off(16, 0x9D72)
    table = rom[table_offset:table_offset + 240]
    neighbors = []
    for city in range(30):
        raw = list(table[city * 8:city * 8 + 8])
        end = next(index for index, value in enumerate(raw) if value & 128)
        values = raw[:end]
        assert end < 8 and all(value < 30 for value in values)
        neighbors.append(dict(city=city, row_cpu=0x9D72 + city * 8,
                              rom_offset=table_offset + city * 8, raw_bytes=raw,
                              negative_terminator_index=end, candidate_cities=values))
    contract = address_contract()
    assert contract['auxiliary_address_intersection_count'] == 0
    selected = next(row for row in rows if (row['physical_bank'], row['cpu']) == TARGET)
    assert selected['classification'] == 'possible_city_auxiliary_alias'
    bare_contract = copy.deepcopy(selected.get('address_contract'))
    selected['classification'] = 'proved_disjoint_auxiliary_address_domain'
    selected['address_contract'] = contract
    selected['whole_pointer_values'] = contract['whole_pointer_values']
    selected['Y_values'] = contract['Y_values']
    selected['proof_basis'] = 'phase31_complete_BC46_roster_lifecycle_conditional_contract'
    selected['newly_proved_disjoint'] = True
    selected['phase31_prior_classification'] = 'possible_city_auxiliary_alias'
    selected['phase31_prior_authority'] = dict(path=prior_path, sha256=sha(ROOT / prior_path),
                                              physical_bank=8, cpu=0xBDB8)
    selected['phase31_bare_entry_candidate_not_authority'] = bare_contract
    selected['limits'] = [
        'Authority requires current complete BC46 entry, normal modes and immutable original adjacency, binary/no interrupts.',
        'Bare BD96 raw03>=27 writes before its CPY27; raw03=255 can wrap and then write0..26.',
        'This is a logical effective-address domain, not a microcycle dummy-bus or full game closure proof.',
        'No official meaning is assigned to city+1 or+28..31; a conditional exclusion does not prove unused.',
    ]
    counts = dict(Counter(row['classification'] for row in rows))
    assert counts == dict(proved_disjoint_auxiliary_address_domain=1201,
                          possible_city_auxiliary_alias=80,
                          unresolved_pointer_or_index_contract=245)
    for row in rows:
        if (row['physical_bank'], row['cpu']) != TARGET:
            row['newly_proved_disjoint'] = False
    proof = dict(schema='phase31-complete-BC46-roster-logical-write-contract-v1',
        status='analyzed_original_CPU_contract_receipt_required', ROM_sha256=ROM_SHA,
        root_entry=dict(physical_bank=8, cpu=0xBC46), selected_targets=[dict(physical_bank=8, cpu=0xBDB8)],
        original_instructions=instructions, F2AF_complete_instructions=helper,
        inline_table=dict(physical_bank=8, cpu=0xBC4C, rom_offset=off(8, 0xBC4C),
                          raw_hex=rom[off(8, 0xBC4C):off(8, 0xBC4C) + 6].hex(' ').upper(),
                          targets=[0xBC52, 0xBD59, 0xBD67]),
        adjacency_ROM=dict(physical_bank=16, cpu=0x9D72, rom_offset=table_offset,
                           bytes=240, raw_hex=table.hex(' ').upper(), rows=neighbors),
        real_BD96_callers=[dict(call_cpu=call, callee_cpu=0xBD96,
                               raw_stacked_return=call + 2, actual_return_PC=ret)
                           for call, ret in CALLS],
        caller_argument_contracts=[
            dict(call_cpu=0xBC65, mode=0, construction='BC55 current city050E→02; BC5B LDA17→03;04=0.',
                 input03=[17]),
            dict(call_cpu=0xBD8E, mode=2, construction='BD73 F2AF source052A; BD78 firstFF scan17..26; onlyfound branchBD86 STY03;04=0.',
                 input03=list(range(17, 27))),
            dict(call_cpu=0xBC8E, mode=[0, 1, 2], construction='BE90 counts at most10 roster bytes17..26; BC7C skips counts0/10, then CLC+17→03.',
                 input03=list(range(18, 27))),
            dict(call_cpu=0xBCC9, mode=[0, 1, 2], construction='Secondneighbor pass BCBB count must equal0, then CLC+17→03.',
                 input03=[17]),
        ],
        producer_lifecycle=[
            'All30 actual adjacency rows terminate negative within8bytes and contain only0..29 before terminator; at most7eligible outputs, within clear11 arrays.',
            'BE90 selects physical16 itself; each occupancy scan tests bytes17..26 and returnscount0..10; arrays042C/0550 do not overlap scratch00..05.',
            'F2AF reconstructs complete00/01=6000+32*rawcity and writes only00/01, not02/03/04; all256 values remain SRAM6000..7FE0.',
            'BD96 loads live03 intoY and04 intoX after F2AF. BDB8 writes before increment/check; onlytypedentryY17..26 yields this domain.',
            'BDB8 cannot write ZP/scratch or stack for any F2AF rawcity. Optional PHA/PLA uses0100..01FF; 052Cstore is RAM outside00..04.',
            'X/list aliasing, including rawcity125 overlapping6FA1workspace, may changevalues/termination but cannot change00/01 or the boundedYwrite domain.',
            'Mode2 full-source fallback retains EADE highbyteBD in04 until normal laterwrites; no invented reset or Xclamp is assumed.',
        ],
        full_parent_domain=dict(modes=[0, 1, 2], normal_current_cities=list(range(30)),
            normal_source_cities=list(range(30)), normal_rulers=list(range(7)),
            side_signs=[0, 128], binary=True, interrupted=False, bare_or_middle_entry=False,
            termination_not_universally_proven=True),
        whole_pointer_domain_superset=contract,
        bare_counterexample_request=dict(entry=0xBD96, raw03=[1, 27, 28, 29, 30, 31, 255],
            why='Firststore beforeCPY; 255 wraps to0 and can subsequently reachcity+1.'),
        semantic_credit='BC46 gameplay and exactSource alreadyfrozen30; this adds one conditional staticaddress theorem only.',
        source_CPU_cases=0, Native_runs=0,
        limits=selected['limits'])
    save('roster-write-lifecycle-contract.json', proof)
    save('all-indirect-accesses.json', dict(schema='phase31-all-indirect-contract-ledger-v1', ROM_sha256=ROM_SHA,
         access_count=len(rows), classification_counts=counts, newly_proved_disjoint_count=1, accesses=rows))
    save('selected-accesses.json', dict(schema='phase31-selected-roster-store-v1', accesses=[selected]))
    remaining = [row for row in rows if row['classification'] != 'proved_disjoint_auxiliary_address_domain']
    save('remaining-accesses.json', dict(schema='phase31-remaining-city-auxiliary-candidates-v1', count=len(remaining), accesses=remaining))
    save('raw345-executability-ledger.json', read('analysis/phase30/fields-static/raw345-executability-ledger.json'))
    output = []
    for row in instructions + helper:
        output.append(f"{row['physical_bank']:02d}:{row['cpu']:04X} file={row['rom_offset']:06X} {row['raw_hex']:<9} {row.get('assembly', '')}")
    (OUT / 'original-ranges.asm').write_text('\n'.join(output) + '\n')
    dependencies = ['analysis/phase30/verification.json', prior_path,
                    'analysis/phase30/fields-static/raw345-executability-ledger.json',
                    'analysis/phase30/early-services/static-catalog.json',
                    'analysis/phase30/early-services/validation.json',
                    'source/recovered/postbattle_early_services.py']
    artifacts = {name: sha(ROOT / name) for name in dependencies}
    artifacts.update({str(path.relative_to(ROOT)): sha(path) for path in OUT.iterdir()
                      if path.is_file() and path.name not in ('analysis-summary.json', 'verification.json', 'evidence.json', 'README.md')})
    save('analysis-summary.json', dict(schema='phase31-roster-store-field-summary-v1', status='analyzed',
         ROM_sha256=ROM_SHA, original_CPU_contract_receipt_required=True, source_CPU_cases=0, Native_runs=0,
         all_indirect_access_count=1526, previous_candidate_count=326,
         all_indirect_classification_counts=counts, remaining_access_count=len(remaining),
         newly_proved_disjoint_all_count=1, raw345=dict(total=345, operand=104, known_data=13, no_proved_control_entry=228),
         official_city_auxiliary_names={str(offset): None for offset in (1, 28, 29, 30, 31)},
         whole_game_closure_proven=False, complete_analysis_fixed_point_proven=False,
         source_and_validator_sha256={str(Path(__file__).relative_to(ROOT)): sha(__file__)},
         artifact_sha256=artifacts, limits=proof['limits']))
    print(json.dumps(dict(status='analyzed', selected='8:BDB8', new_conditional=1,
                          counts=counts, remaining=len(remaining), Source_CPU_cases=0, Native_runs=0)))


if __name__ == '__main__':
    main()
