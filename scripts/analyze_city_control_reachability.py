#!/usr/bin/env python3
"""Verify bounded control tables and correct phase17's inline-data graph.

This is a new evidence layer. Source AST supplies declared table extents; the
original ROM supplies every call, pointer and dispatcher instruction. Raw
selectors outside these declared extents remain an explicit boundary.
"""
from pathlib import Path
from collections import Counter, deque
import argparse, ast, hashlib, json, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from inspect_game_data import OPS, SIZES
from analyze_city_field_contracts import context_selector

SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT = ROOT / 'analysis/phase18/control'
PAIRS = (8, 10, 12, 14, 23, 25, 27, 29)
CLASS_PAIRS = dict(BattleSceneController=12, AttackSceneController=14,
                  DuelSceneController=23, CityPanelServices=25,
                  CityUIController=27, TacticalCooperationController=8,
                  TextSceneServices=29, OfficerDetailsUIServices=25,
                  CityOfficerDetailsController=25, TitleIntroGraphics=23)

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def off(bank, pc):
    return 16 + bank * 8192 + (pc & 8191)

def raw(rom, bank, start, end):
    offset = off(bank, start)
    return dict(physical_bank=bank, cpu=start, end_cpu_exclusive=end,
                rom_offset=offset, raw_hex=rom[offset:offset + end - start].hex(' ').upper())

def instruction(rom, bank, pc, origin):
    offset = off(bank, pc)
    op, mode = OPS[rom[offset]]
    size = SIZES[mode]
    return dict(physical_bank=bank, cpu=pc, rom_offset=offset, size=size,
                op=op, mode=mode, operand=int.from_bytes(rom[offset + 1:offset + size], 'little'),
                raw_hex=rom[offset:offset + size].hex(' ').upper(), sources=[origin])

def collect(rom):
    tables = {}
    pins = {}
    def add(bank, pc, targets, provenance, domain):
        targets = list(targets)
        call = instruction(rom, bank, pc, provenance['path'])
        assert call['op'] == 'JSR' and call['operand'] in (0xEADE, 0xB517, 0xD494), call
        data = raw(rom, bank, pc + 3, pc + 3 + 2 * len(targets))
        actual = list(int.from_bytes(bytes.fromhex(data['raw_hex'])[2*i:2*i+2], 'little') for i in range(len(targets)))
        assert actual == targets, (bank, pc, actual, targets)
        record = dict(call=call, table=data, targets=targets, count=len(targets),
                      normal_selector_values=list(range(len(targets))), domain=domain,
                      source=[provenance], no_all_raw_selector_claim=True)
        old = tables.get((bank, pc))
        if old:
            assert old['targets'] == targets
            old['source'].append(provenance)
        else:
            tables[bank, pc] = record
        pins[provenance['path']] = sha(ROOT / provenance['path'])
    for path in sorted((ROOT / 'source/recovered').glob('*.py')):
        for cl in [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef)]:
            pair = CLASS_PAIRS.get(cl.name)
            for node in cl.body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PAIR' for t in node.targets):
                    try:
                        pair = ast.literal_eval(node.value)[0]
                    except (ValueError, TypeError):
                        pass
            if pair is None:
                continue
            for node in ast.walk(cl):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != '_dispatch':
                    continue
                try:
                    pc, targets = [ast.literal_eval(arg) for arg in node.args[:2]]
                except (ValueError, TypeError):
                    continue
                if not isinstance(pc, int) or not isinstance(targets, (tuple, list)):
                    continue
                add(pair + int(pc >= 0xC000), pc, targets,
                    dict(path=str(path.relative_to(ROOT)), source_line=node.lineno, source_class=cl.name),
                    'Existing typed source dispatch extent; each original pointer independently verified. Arbitrary corrupted selectors remain outside this contract.')
    path = 'source/recovered/battle_graphics_services.py'
    for pc, targets in [(0xD009, (0xD41F, 0xD010)),
                        (0xD031, (0xD04A,0xD07C,0xD0B8,0xD0F5,0xD132,0xD18C,0xD1C3,0xD206,0xD232,0xD263,0xD294)),
                        (0xD422, (0xD42F,0xD476,0xD559,0xD5F2,0xD6EA))]:
        add(26, pc, targets, dict(path=path, semantic_method='existing bounded animation dispatch'),
            'Declared animation 2/11/5-way domains; raw marker and stage values outside the relevant method remain explicit.')
    path = 'analysis/phase4/terrain/service-controller.json'
    data = json.loads((ROOT / path).read_text())
    add(9, 0xC0BE, [row['entry'] for row in data['handlers']], dict(path=path),
        'Original ten village substates and exact boundary C0C1..C0D4; C0D5 is the first original handler.')
    # Original BA animation's four words end exactly at the first handler.
    # This establishes an extent, not reachability of arbitrary raw phase.
    path = 'analysis/phase7/controller/program.json'
    add(8, 0xBAB6, (0xBAC1, 0xBB3D, 0xBB93, 0xBBA0), dict(path=path),
        'Four original words end at BAC1. This data/code extent is verified; semantic raw0501 bounds remain separately unknown.')
    assert 0xBAB9 + 8 == min(tables[8,0xBAB6]['targets'])
    add(8, 0xBC49, (0xBC52, 0xBD59, 0xBD67), dict(path=path),
        'Three original words end at BC52, the first handler. This extent is data/code evidence; arbitrary raw6F91 selector reachability remains unknown.')
    assert 0xBC4C + 6 == min(tables[8,0xBC49]['targets'])
    return tables, pins

def analyze(rom):
    assert hashlib.sha256(rom).hexdigest() == SHA
    prior_path = ROOT / 'analysis/phase17/fields/instruction-atlas.json'
    prior = json.loads(prior_path.read_text())
    inventory_path = ROOT / 'analysis/phase17/fields/dispatch-bank-inventory.json'
    inventory = json.loads(inventory_path.read_text())
    tables, pins = collect(rom)
    table_bytes = {(bank, pc) for (bank, _), item in tables.items()
                   for pc in range(item['table']['cpu'], item['table']['end_cpu_exclusive'])}
    global_path = 'analysis/phase6/global/state-catalog.json'
    global_data = json.loads((ROOT / global_path).read_text())
    pins[global_path] = sha(ROOT / global_path)
    global_tables = []
    for pc, table_pc, count, key in [(0xE079,0xE07C,15,'main'),(0xF878,0xF87B,9,'nmi')]:
        table = raw(rom,31,table_pc,table_pc + 2*count)
        blob = bytes.fromhex(table['raw_hex'])
        targets = [int.from_bytes(blob[2*i:2*i+2], 'little') for i in range(count)]
        global_tables.append(dict(dispatch=raw(rom,31,pc,pc+3),table=table,targets=targets,count=count,
                                  role=key,source=global_path,domain='Declared original main0..14 / NMI0..8; masks also represent unsupported raw values.'))
        table_bytes.update((31, address) for address in range(table_pc, table_pc+2*count))
    removed = []
    known = {}
    for r in prior['instructions']:
        k = r['physical_bank'], r['cpu']
        if any((k[0],p) in table_bytes for p in range(k[1], k[1]+r['size'])):
            removed.append(dict(**r,correction='Original inline/table bytes, not a normal fallthrough instruction in the declared control domain.'))
        else:
            assert bytes.fromhex(r['raw_hex']) == rom[r['rom_offset']:r['rom_offset']+r['size']]
            known[k] = dict(r)
    global_dispatch = {(31, x['dispatch']['cpu']): x for x in global_tables}
    queue = deque(known); visited=set(); edges={}; barriers=[]; added=[]
    def mapped(k, target):
        if target>=0xE000: return 31,target
        if not 0xA000<=target<0xE000 or k[0]==31: return None
        pair=k[0]-int(k[1]>=0xC000)
        return pair+int(target>=0xC000),target
    while queue:
        k=queue.popleft()
        if k in visited: continue
        visited.add(k); r=known[k];pc=r['cpu'];v=r['operand'];following=pc+r['size'];targets=[]
        if r['mode']=='rel':
            targets=[mapped(k,following),mapped(k,(pc+2+(v if v<128 else v-256))&65535)]
        elif k in tables:
            targets=[mapped(k,t) for t in tables[k]['targets']]
        elif k in global_dispatch:
            targets=[(31,t) for t in global_dispatch[k]['targets']]
        elif r['op']=='JMP':
            if r['mode']=='ab': targets=[mapped(k,v)]
            else: barriers.append(dict(**r,kind='dispatcher_body_requires_actual_returnword_or_far_context',scope='Caller overlay resolves bounded destinations; the context-free helper itself is not a single target.'))
        elif r['op']=='JSR':
            if v in (0xEADE,0xB517) or (k[0]==10 and v==0xD494):
                barriers.append(dict(**r,kind='missing_declared_inline_extent'))
            elif v==0xEE07:
                targets=[mapped(k,following+2)]
                selector,context=context_selector(known,k)
                callee=int.from_bytes(rom[off(k[0],following):off(k[0],following)+2],'little')
                if selector is not None and selector&31 in PAIRS and 0xA000<=callee<0xE000:
                    pair=selector&31;targets.append((pair+int(callee>=0xC000),callee))
                else: barriers.append(dict(**r,kind='unresolved_far_context',selector=selector,inline_target=callee))
            else:
                targets=[mapped(k,following),mapped(k,v)]
                if k[0]==31 and 0xA000<=v<0xE000:
                    barriers.append(dict(**r,kind='fixed_body_requires_actual_mapper_context',target_cpu=v))
        elif r['op'] not in ('RTS','RTI','BRK','?'):
            targets=[mapped(k,following)]
        accepted=[]
        for target in targets:
            if target is None: continue
            if target in table_bytes:
                barriers.append(dict(**r,kind='normal_control_target_hits_original_table_data',target=list(target)))
                continue
            if target not in known:
                item=instruction(rom,*target,'phase18_bounded_control_overlay')
                if item['op'] in ('BRK','?'):
                    barriers.append(dict(**r,kind='unrecognized_direct_target',target=list(target)))
                    continue
                known[target]=item;added.append(item)
            accepted.append(target);queue.append(target)
        edges[k]=accepted
    old_dispatches=[x for x in inventory['computed_or_mapper_context_barriers'] if x['kind']=='inline_dispatch_requires_bounded_table_contract']
    assert all((x['physical_bank'],x['cpu']) in tables for x in old_dispatches)
    old_sites={(x['physical_bank'],x['cpu']) for x in old_dispatches}
    assert not any(x['kind']=='missing_declared_inline_extent' and (x['physical_bank'],x['cpu']) in old_sites for x in barriers)
    result=dict(schema='phase18-original-bounded-control-contracts-v1',ROM_sha256=SHA,
        source_and_artifact_sha256={**pins,str(prior_path.relative_to(ROOT)):sha(prior_path),str(inventory_path.relative_to(ROOT)):sha(inventory_path),
                                    'scripts/analyze_city_control_reachability.py':sha(Path(__file__))},
        prior_instruction_count=len(prior['instructions']),original_dispatch_table_count=len(tables),
        prior_inline_dispatch_barriers_resolved=len(old_dispatches),bounded_dispatch_tables=list(tables.values()),global_tables=global_tables,
        original_dispatcher_bodies=[raw(rom,31,0xEADE,0xEAF7),raw(rom,11,0xD494,0xD4AD),raw(rom,8,0xB517,0xB536),raw(rom,31,0xEE07,0xEE53)],
        removed_table_instruction_positions=removed,added_instruction_positions=added,
        corrected_instruction_count=len(known),remaining_context_barriers=barriers,
        city_auxiliary_semantic_names=dict(byte1=None,tail28_31=None),
        limitation='Overlay repairs data/code separation and explicit bounded dispatch extents. It does not prove arbitrary raw-selector or external-mapper reachability, nor city padding/unused semantics.')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'control-contracts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    graph=dict(schema='phase18-corrected-bounded-city-control-atlas-v1',ROM_sha256=SHA,
               instructions=list(known.values()),edges=[dict(physical_bank=b,cpu=pc,targets=[list(t)for t in ts])for(b,pc),ts in edges.items()],
               instruction_positions=len(known),source_contracts_path='analysis/phase18/control/control-contracts.json',
               source_contracts_sha256=sha(OUT/'control-contracts.json'),scope=result['limitation'])
    (OUT/'instruction-atlas.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='written',tables=len(tables),old_barriers_resolved=len(old_dispatches),removed=len(removed),added=len(added),positions=len(known),barriers=dict(Counter(x['kind']for x in barriers))),ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom',type=Path)
    analyze(parser.parse_args().rom.read_bytes())
