#!/usr/bin/env python3
"""Audit native deployment data without starting an emulator or changing a ROM.

--check needs only the shipped declarative reference. --rom rebuilds it from
the pinned local ROM. The archive's lifted C3CB/C447 routines independently
closed the point order and rectangle predicates; they are not runtime inputs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'game/config/references/original-battle-deployment-v1.json'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SCHEMA = 'tk2-original-battle-deployment-v1'
# name: physical 8 KiB bank, CPU address, byte length, pinned data SHA256.
SPANS = {
 'adjacency': (16,0x9D72,240,'73fba4e4d02ba7fc0ada456b156d808e0f82a5b9ce85799d25540327fcf83b91'),
 'attacker_zone_indices': (16,0x9E62,240,'c40682070d82e3b42559d05b7eeff81f13ffdb137727bf8bc28de80c27246bb0'),
 'defender_zone_indices': (17,0x9AB4,240,'eda2369d4c2e3a343c24386ea205921c0315846912c1989ebb3dd080ca78c8c4'),
 'attacker_point_pointers': (6,0x8000,60,'38759b27efdbeb107450387f7268bc24aaa347d51c0f46b416c6eb8456083bf5'),
 'defender_point_pointers': (6,0x8C52,60,'7c7ce839aee5429f92138b13bbe956153b7c8895f9f4319ba407b34de32c13f9'),
 'attacker_bounds_pointers': (6,0x932E,60,'4924c8d8c36b4dfdc898db3f680ebf5685c50051af5ecff16dbc0c500e266fd2'),
 'defender_bounds_pointers': (6,0x94D6,60,'e6368e1789a5869b1fb6aaabc123421ece48d573c8fcd27c4b1b1ecf080239a2'),
 'attacker_points': (6,0x803C,3094,'a38bdb1d81c633c942cbc50755b5ff2b58f6ed2d5ea5420f843a92e588ca349b'),
 'defender_points': (6,0x8C8E,1696,'9d64135262170ebadc503fef9dd6fc8db2f7ce9e34c93185658ff11d928257da'),
 'attacker_bounds': (6,0x936A,364,'bc895af1e44c45b0b7bf1256c5588434c1ca1397500263bc3b9d659db1a8a724'),
 'defender_bounds': (6,0x9512,212,'526c2a63250fa71e3ea28887c9a8bf56bb1c985ff52ae02ee830ac3ea3c486a6'),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_offset(bank, cpu):
    return 16 + bank * 8192 + (cpu & 8191)


def source_tables(rom):
    require(digest(rom) == ROM_SHA, 'Pinned local ROM identity required')
    tables = {}
    for name,(bank,cpu,length,expected) in SPANS.items():
        offset = file_offset(bank,cpu)
        raw = rom[offset:offset+length]
        require(len(raw) == length and digest(raw) == expected, 'ROM deployment table mismatch: '+name)
        tables[name] = dict(physical_bank=bank,cpu=f'{cpu:04X}',
            rom_file_offset=offset,length=length,hex=raw.hex(),sha256=expected)
    return tables


def table_bytes(tables):
    require(type(tables) is dict and set(tables) == set(SPANS), 'Deployment source table set mismatch')
    result = {}
    for name,(bank,cpu,length,expected) in SPANS.items():
        row = tables[name]
        require(type(row) is dict and set(row) == {'physical_bank','cpu','rom_file_offset','length','hex','sha256'},
            'Deployment source metadata mismatch: '+name)
        require((row['physical_bank'],row['cpu'],row['rom_file_offset'],row['length'],row['sha256'])
            == (bank,f'{cpu:04X}',file_offset(bank,cpu),length,expected), 'Deployment source address/hash mismatch: '+name)
        require(type(row['hex']) is str, 'Deployment source bytes must be hexadecimal')
        raw = bytes.fromhex(row['hex'])
        require(raw.hex() == row['hex'] and len(raw) == length and digest(raw) == expected,
            'Deployment source bytes mismatch: '+name)
        result[name] = raw
    return result


def _word(raw, offset):
    return raw[offset] | raw[offset+1] << 8


def _read(table, table_name, cpu, length):
    start = cpu-SPANS[table_name][1]
    require(0 <= start <= len(table[table_name])-length, 'Deployment pointer is outside its source table')
    return table[table_name][start:start+length]


def native_cell_visible(point):
    """The existing release displays x0..30, packed y0..19 except metadata15."""
    return 0 <= point['x'] < 31 and 0 <= point['packed_y'] < 20 and point['packed_y'] != 15


def in_rectangle(point, bounds):
    return (bounds['min_x'] <= point['x'] < bounds['max_x_exclusive']
        and bounds['min_packed_y'] <= point['packed_y'] < bounds['max_packed_y_exclusive'])


def unique_points(points):
    """C3CB scans the ordered list and D6B6 skips already occupied positions."""
    seen, result = set(), []
    for point in points:
        key = point['x'], point['packed_y']
        if key not in seen:
            result.append(deepcopy(point))
            seen.add(key)
    return result


def safe_visible_points(zone):
    """Proposed shared remake filter; never label this as the C3CB predicate.

    Native C3CB tests occupancy only. It does not apply C447's rectangle or the
    remake viewport. Every extracted zone still supplies at least ten points
    after this explicit filter, so no synthetic deployment points are needed.
    """
    return [point for point in unique_points(zone['default_points'])
            if native_cell_visible(point) and in_rectangle(point,zone['bounds'])]


def derive_cities(tables):
    data = table_bytes(tables)
    cities, anomalies = {}, []
    for city in range(30):
        row = data['adjacency'][city*8:city*8+8]
        end = next((i for i,value in enumerate(row) if value == 255),8)
        require(end < 8 and all(value == 255 for value in row[end:]), 'Native adjacency terminator mismatch')
        require(all(value < 30 and value != city for value in row[:end]), 'Native source-city index mismatch')
        neighbors = [dict(source_original_city_index=value,
            attacker_zone_index=data['attacker_zone_indices'][city*8+i],
            defender_zone_index=data['defender_zone_indices'][city*8+i]) for i,value in enumerate(row[:end])]
        sides = {}
        for singular,side,stride in (('attacker','attackers',34),('defender','defenders',32)):
            zones = []
            point_base = _word(data[singular+'_point_pointers'],city*2)
            bounds_base = _word(data[singular+'_bounds_pointers'],city*2)
            indices = {entry[singular+'_zone_index'] for entry in neighbors}
            require(indices == set(range(max(indices)+1)), 'Native zone-index set is not contiguous')
            for index in range(max(indices)+1):
                point_cpu,bounds_cpu = point_base+stride*index,bounds_base+4*index
                raw = _read(data,singular+'_points',point_cpu,stride)
                y0,x0,y1,x1 = _read(data,singular+'_bounds',bounds_cpu,4)
                require(0 <= x0 < x1 <= 32 and 0 <= y0 < y1 <= 21, 'Native rectangle bounds invalid')
                points = [dict(x=raw[i+1],packed_y=raw[i]) for i in range(0,stride,2)]
                bounds = dict(min_x=x0,min_packed_y=y0,max_x_exclusive=x1,max_packed_y_exclusive=y1)
                zone = dict(index=index,point_cpu=f'{point_cpu:04X}',bounds_cpu=f'{bounds_cpu:04X}',
                    bounds=bounds,default_points=points)
                require(len(safe_visible_points(zone)) >= 10, 'Insufficient visible original deployment candidates')
                zones.append(zone)
                seen = set()
                for slot,point in enumerate(points):
                    key = point['x'],point['packed_y']
                    conditions = []
                    if key in seen: conditions.append('duplicate_default_point_skipped_by_native_occupancy_scan')
                    seen.add(key)
                    if not native_cell_visible(point): conditions.append('outside_remake_visible_grid')
                    if not in_rectangle(point,bounds): conditions.append('outside_native_manual_deployment_rectangle')
                    for kind in conditions:
                        anomalies.append(dict(original_city_index=city,side=side,zone_index=index,
                            raw_slot_index=slot,point=deepcopy(point),kind=kind))
            sides[side] = dict(point_stride_bytes=stride,zones=zones)
        cities[f'original-{city:02d}'] = dict(original_city_index=city,neighbors=neighbors,sides=sides)
    return cities, anomalies


def resolve_reference(reference, target_original_city_index, source_original_city_index):
    """Return the paired native zones, or None when native adjacency is absent.

    This is an offline data API, not an automatic115-city runtime binding.
    These small integers identify local table rows, never compass directions.
    """
    require(type(target_original_city_index) is int and 0 <= target_original_city_index < 30,
        'Invalid native target-city index')
    require(type(source_original_city_index) is int and 0 <= source_original_city_index < 30,
        'Invalid native source-city index')
    city = reference['cities'][f'original-{target_original_city_index:02d}']
    entry = next((row for row in city['neighbors']
        if row['source_original_city_index'] == source_original_city_index),None)
    if entry is None:
        return None
    return {side:deepcopy(city['sides'][side]['zones'][entry[singular+'_zone_index']])
        for side,singular in (('attackers','attacker'),('defenders','defender'))}


def build(tables):
    cities, anomalies = derive_cities(tables)
    return dict(schema=SCHEMA,rom_sha256=ROM_SHA,
      scope='Read-only native30-city deployment data. No ROM code, emulator state, UI gameplay proof or runtime115-city binding is included.',
      direction_semantics=dict(neighbor_key='target original city adjacency row searched for source original city index',
        adjacency='physical16:9D72,8 bytes per target,FF terminator',
        attackers='physical16:9E62 matched-neighbor byte selects target-local edge zone0..3',
        defenders='physical17:9AB4 matched-neighbor byte selects target-local central zone0..1',
        not_compass_indices=True,native_missing_neighbor_result=0,
        missing_neighbor_policy='The original falls back to local zone0. A remake should explicitly label a source with no native adjacency instead of pretending that zone0 proves its historical direction.'),
      side_identity=dict(defenders='slots0..9,low nibble of0507,050B==2 in C3CB/C447',
        attackers='slots10..19,high nibble of0507,050B==3 in C3CB/C447',
        warning='The recovered first_side/second_side names describe array order, not who attacks first.'),
      coordinate_policy=dict(raw_point_byte_order=['packed_y','x'],raw_rectangle_byte_order=['min_packed_y','min_x','max_packed_y_exclusive','max_x_exclusive'],
        rectangle_predicate='min_x<=x<max_x_exclusive and min_packed_y<=packed_y<max_packed_y_exclusive',
        visible_columns=31,visible_rows=19,metadata_packed_row=15,
        visible_y='packed_y if packed_y<15 else packed_y-1; reject packed_y15 and values outside0..19',
        native_default_predicate='C3CB scans ordered pairs for the first position not occupied by any of20 slots; it does not call C447 or filter terrain.',
        terrain='Water and mountain are not forbidden deployment classes; native default points actually use both.',
        proposed_remake_filter='Keep original evidence unchanged; select unique original points inside both the native rectangle and current visible grid. All91 attacker and53 defender zones retain at least10 candidates.'),
      source_helpers=[
        dict(path='source/recovered/battle_scene_controller.py',sha256='6af446393521e0cd04d4129d79e3218e27e687e0d8d77d66c2dbf346832a4781',
          entries=[dict(cpu='13:C3CB-C444',line=12847,rule='default ordered points and occupancy scan'),
            dict(cpu='13:C447-C4AE',line=12927,rule='half-open deployment rectangle'),
            dict(cpu='13:C4B1-C59F',line=13011,rule='four-direction deployment editing; occupancy, rectangle and raw-grid gates; no AP debit'),
            dict(cpu='13:D6B6-D6CB',line=18462,rule='occupancy of20 tactical unit slots'),
            dict(cpu='13:DC99-DD71',line=19598,rule='unplaced coordinatesFF; source city0402 copied to052A'),
            dict(cpu='13:DE9E-DEE8',line=20084,rule='target adjacency search and target-local zone lookup')]),
        dict(path='source/recovered/battle_setup_ai.py',sha256='b08fa8bedddf2a4f3ba49acccdc6176c78b0698bc3ac93691a7718afb9985fbb',
          entries=[dict(cpu='08:B2AE-B36C',line=327,rule='AI uses the same native central/edge coordinate tables')])],
      validation_scope=dict(kind='controlled lifted-function checks, not natural gameplay',
        source_rom_unchanged=True,emulator_started=False,directed_native_neighbor_pairs=128,
        c447_boundary_checks=2048,c3cb_ordered_coordinate_checks=2560,
        defending_commander_matches_native_camp=128,
        note='These recorded counts were verified against the archived lifted source. --check independently re-derives every shipped city/zone from pinned data bytes; it does not claim to rerun the unavailable archive in CI.'),
      proposed_regional_fallback=dict(status='design only; no runtime change',
        exact_case='If source/target native template indices form an actual native adjacent pair, use its paired local zones; regional template reuse must still be labeled as remake association.',
        expanded_case='Otherwise compute the target-to-previous-route-point vector from the final strategic route leg: this points outward toward where the attacking army came from, not along its forward travel direction. Choose the native attacker edge rectangle whose camp-to-center vector has the smallest angle to that arrival vector; among duplicate rectangles choose the smallest native neighbor index, and use that neighbor record to pair the defender central zone.',
        missing_geometry='If no nonzero arrival vector is available, choose the smallest native neighbor index deterministically and disclose no-arrival-geometry fallback.',
        legality='Player and AI use the same visible-grid, rectangle and occupancy checks; use the proposed unique-point filter rather than silently editing the source tables. Placement costs no tactical AP and draws no RNG.',
        saves='Only new battles receive arrival-aware initial placement. Loading existing positions/AP must never redeploy or refill points.'),
      source_tables=deepcopy(tables),cities=cities,native_data_anomalies=anomalies)


def check(reference):
    require(type(reference) is dict and reference.get('schema') == SCHEMA and reference.get('rom_sha256') == ROM_SHA,
        'Deployment reference identity mismatch')
    expected = build(reference.get('source_tables'))
    require(reference == expected, 'Deployment reference derived data or source annotations are stale')
    maps = json.loads((ROOT/'game/assets/battlefields/index.json').read_text())['maps']
    for key,city in reference['cities'].items():
        camp = maps[key]['camps'][0]
        for zone in city['sides']['defenders']['zones']:
            point = zone['default_points'][0]
            require(point['x'] == camp['x'] and point['packed_y'] == camp['packed_y'],
                'Native defending commander does not match the extracted castle: '+key)
    return dict(cities=len(reference['cities']),directed_native_neighbor_pairs=sum(len(row['neighbors']) for row in reference['cities'].values()),
        attacker_zones=sum(len(row['sides']['attackers']['zones']) for row in reference['cities'].values()),
        defender_zones=sum(len(row['sides']['defenders']['zones']) for row in reference['cities'].values()),
        native_data_anomalies=len(reference['native_data_anomalies']))


def verify_archive(reference, archive_source, rom):
    """Optional local recheck through the unchanged archived lifted routines.

    Only the ordinary F25F data-bank mapping boundary is supplied. No RNG,
    graphics, hardware input, emulator process or persistent save is involved.
    The script never writes bytecode back into the research archive.
    """
    require(digest(rom) == ROM_SHA, 'Pinned local ROM identity required')
    for row in reference['source_helpers']:
        path = archive_source / Path(row['path']).relative_to('source')
        require(digest(path.read_bytes()) == row['sha256'], 'Archived lifted source identity mismatch')
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.path.insert(0,str(archive_source))
    try:
        memory_class = importlib.import_module('recovered.mapped_memory').PrgDataMemory
        controller_class = importlib.import_module('recovered.battle_scene_controller').BattleSceneController
    finally:
        sys.path.pop(0)
        sys.dont_write_bytecode = previous
    memory = memory_class(rom,banks=(6,12,13,31))
    def mapper_service(call):
        require(call.target == 0xF25F, 'Unexpected original dependency during deployment check')
        call.memory[0xE1] = call.registers.y
        call.memory[0xE000] = call.registers.y
        call.registers.sp,call.registers.pc = call.expected_sp,call.return_pc
        return dict(status='returned')
    controller = controller_class(memory,rom,services=mapper_service)
    bounds_checks,point_checks = 0,0
    for city in reference['cities'].values():
        for neighbor in city['neighbors']:
            for side,singular,mode,base in (('attackers','attacker',3,10),('defenders','defender',2,0)):
                zone = city['sides'][side]['zones'][neighbor[singular+'_zone_index']]
                bounds = zone['bounds']
                x0,y0,x1,y1 = (bounds[key] for key in
                    ('min_x','min_packed_y','max_x_exclusive','max_packed_y_exclusive'))
                memory[0x50E],memory[0x52A],memory[0x50B] = (city['original_city_index'],neighbor['source_original_city_index'],mode)
                for x,y in ((x0,y0),(x1-1,y1-1),(max(0,x0-1),y0),(x1,y0),
                            (x0,max(0,y0-1)),(x0,y1),(0,0),(30,19)):
                    memory[0],memory[1] = x,y
                    result = controller.run_entry(0xC447,seed_return=True)
                    require(result['status'] == 'returned' and bool(controller.registers.p&1)
                        == in_rectangle(dict(x=x,packed_y=y),bounds), 'Archived C447 rectangle mismatch')
                    bounds_checks += 1
                memory[0x600:0x628] = bytes([255])*40
                for slot,expected in enumerate(unique_points(zone['default_points'])[:10]):
                    memory[0x509] = base+slot
                    result = controller.run_entry(0xC3CB,seed_return=True)
                    require(result['status'] == 'returned' and
                        dict(x=memory[0x600+base+slot],packed_y=memory[0x614+base+slot]) == expected,
                        'Archived C3CB ordered deployment mismatch')
                    point_checks += 1
    require((bounds_checks,point_checks) == (2048,2560), 'Archived deployment case count changed')
    return dict(c447_boundary_checks=bounds_checks,c3cb_ordered_coordinate_checks=point_checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,help='Pinned user ROM, read-only; omit for a ROM-free check')
    parser.add_argument('--check',action='store_true',help='Validate shipped data; with --rom also compare its exact extraction')
    parser.add_argument('--archive-source',type=Path,help='Optional read-only archived source directory for lifted C3CB/C447 checks; requires --rom')
    args = parser.parse_args()
    require(args.check or args.rom, 'Use --check, or supply --rom to rebuild')
    rebuilt = build(source_tables(args.rom.read_bytes())) if args.rom else None
    if args.check:
        reference = json.loads(OUTPUT.read_text())
        summary = check(reference)
        require(rebuilt is None or rebuilt == reference, 'Shipped deployment reference differs from the pinned ROM')
    else:
        summary = check(rebuilt)
        OUTPUT.write_text(json.dumps(rebuilt,ensure_ascii=False,indent=2)+'\n')
    if args.archive_source:
        require(args.rom, '--archive-source requires the pinned --rom')
        summary['lifted_checks'] = verify_archive(reference if args.check else rebuilt,args.archive_source,args.rom.read_bytes())
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    main()
