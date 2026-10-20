#!/usr/bin/env python3
"""Phase31 original-byte/state evidence for reused human postbattle Source.

This analyzer never executes a core or a legacy artifact producer. The old
catalog is a read-only static index; production still runs direct Python.
"""
from pathlib import Path
from collections import Counter
import argparse, ast, hashlib, json, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from verify_player_postbattle_phase31 import PHASES, ROM_SHA256

OUT = ROOT / 'analysis/phase31/player-disposition'
CPU = ROOT / 'analysis/phase31/cpu-disposition'
FUNCTIONS = {
 13: ('prepare_defeated_roster', 'select_defeated_roster_destination',
      'open_defeated_roster_selection', 'choose_defeated_roster_officer',
      'exclude_defeated_roster_officer', 'prepare_defeated_roster_confirmation',
      'confirm_defeated_roster_transfer'),
 14: ('prepare_victor_roster', 'select_victor_roster_destination',
      'open_victor_roster_selection', 'choose_victor_roster_officer',
      'exclude_victor_roster_officer', 'prepare_victor_roster_confirmation',
      'confirm_victor_roster_transfer'),
}
MEANINGS = (
 'Build current side officer list; empty defeated list or at most10 victorious officers can return to15 immediately.',
 'Wait for both text jobs FF; only new A advances. Defeated side also checks any available neighboring destination.',
 'Width2 destination menu; new A accepts release30 or a city with occupancy below10.',
 'Wait for both text jobs FF and new A, rebuild officer list and append the End index.',
 'Wait for both text jobs FF, then initialize the width3 officer-selection display.',
 'Width3 officer menu; release30 protects the cached ruler leader, city destinations enforce reception capacity; End commits directly or queues confirmation.',
 'Render chosen entries; both text jobs FF and new A commit through the real D1F9 caller then rebuild phase0.',
)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def off(bank, pc): return 16 + bank * 8192 + (pc & 8191)
def dump(path, data):
 path.parent.mkdir(parents=True, exist_ok=True)
 path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def sparse_boundary_proofs(path, wanted):
 """Retain only requested hits plus their prior watched opcode, streaming."""
 result={};previous=None
 with Path(path).open() as f:
  for line in f:
   if '"opcode_boundary"' not in line:continue
   event=json.loads(line)
   if event['kind']!='opcode_boundary':continue
   if event['sequence'] in wanted:result[event['sequence']]=(event,previous)
   previous=event
   if len(result)==len(wanted):break
 assert set(result)==wanted,('Missing passive opcode events',sorted(wanted-set(result)))
 return result

def import_native(rom):
 """Copy selected immutable passive software entries; never execute a core."""
 manifest=ROOT/'analysis/phase31/runtime/evidence.json'
 assert read(manifest)['status']=='passed'
 player_entries={0xA000,0xA028,0xCD16,0xD2CD,0xD4F0,0xD1F9,0xD20D,0xD299}
 player_entries.update(pc for row in PHASES.values() for pc in row)
 early_entries={0xA006,0xBAB3,0xBAC1,0xBB3D,0xBC46}
 entries=player_entries|early_entries
 manifest_digest=sha(manifest);pins={str(manifest.relative_to(ROOT)):manifest_digest};exports=[];counts=Counter();selected=set()
 for parent in sorted((ROOT/'analysis/phase31/runtime').glob('*/observer')):
  prep=read(parent/'preparation.json');paths=sorted(parent.glob('callee-*.json'))
  wanted={x['event_sequence'] for path in paths if (x:=read(path))['entry'] in entries}
  if not wanted:continue
  event_proofs=sparse_boundary_proofs(parent/'events.jsonl',wanted)
  events_digest=sha(parent/'events.jsonl');prep_digest=sha(parent/'preparation.json')
  pins[str((parent/'events.jsonl').relative_to(ROOT))]=events_digest
  pins[str((parent/'preparation.json').relative_to(ROOT))]=prep_digest
  controlled=prep['controlled_ancestry']
  for path in paths:
   x=read(path);entry=x['entry']
   if entry not in entries:continue
   pair=tuple(x['actual_PRG_banks'][1:3])
   if not (pair==(12,13) and entry in player_entries or pair==(8,9) and entry in early_entries):continue
   rp=parent/x['exported_RAM'];sp=parent/x['exported_SRAM'];ram=rp.read_bytes();sram=sp.read_bytes();r=x['actual_registers']
   state,phase=ram[0x500],ram[0x501];mode=sram[0xF91] if pair==(8,9) else None;side=ram[0x504]
   if state not in(13,14,15):continue
   ready=ram[0x300]==255 and ram[0x304]==255;new_A=bool(ram[0x81]&1)
   fade_negative=bool(ram[0x87]&128) if state==15 and phase==3 else None
   key=parent.parent.name,entry,state,phase,mode,side,ready,new_A,fade_negative
   if key in selected:continue
   selected.add(key);s=r['sp'];word=ram[0x100+((s+1)&255)]|ram[0x100+((s+2)&255)]<<8
   assert len(ram)==2048 and len(sram)==8192 and sha(rp)==x['RAM_sha256'] and sha(sp)==x['SRAM_sha256']
   assert r['pc']==entry and word==x['stack_top_word_raw'] and x['additional_core_memory_writes']==0
   hit,before=event_proofs[x['event_sequence']]
   kind='unknown';transfer=None
   proof=dict(callee_opcode_boundary=hit,previous_watched_opcode_boundary=before,
      not_inferred_from_return_stack=True,scope='Watched sparse boundaries; not a globally unbroken CPU trace')
   if before:
    pc=before['opcode_PC'];bank=before['actual_PRG_banks'][(pc-0x8000)//8192]
    raw=rom[off(bank,pc):off(bank,pc)+3];ticks=hit['cycle']-before['cycle'];proof.update(previous_ROM_bytes=raw.hex(' ').upper(),cycle_ticks=ticks)
    if raw[0] in(0x20,0x4C) and int.from_bytes(raw[1:],'little')==entry and ticks==(72 if raw[0]==0x20 else 36):
     kind='call' if raw[0]==0x20 else 'trampoline' if entry in(0xCD16,0xD2CD) else 'tail';transfer=pc
     assert (before['SP']-s)&255==(2 if kind=='call' else 0)
    elif raw[0]==0x6C and ticks==60:
     ptr=int.from_bytes(raw[1:],'little');high=(ptr&0xFF00)|((ptr+1)&255)
     if ptr<0x2000 and ram[ptr&2047]|ram[high&2047]<<8==entry and before['SP']==s:
      kind='far_indirect_jump' if pc==0xEE4A else 'indirect_dispatch_or_tail';transfer=pc;proof['actual_indirect_pointer']=ptr
   frame_owner=dict(kind='captured_existing_frame_creator_not_fully_observed',existing_stack_word=word,
      return_PC=(word+1)&65535,SP=s,creation_PC=None,not_inferred_from_return_word_minus3=True)
   if word==0xEE4C:
    frame_owner.update(kind='existing_frame_matches_EE07_protocol_return_word',
      static_protocol_push_PC_reference=[0xEE46,0xEE49],original_protocol_return_word=0xEE4C,
      frame_creation_capture_observed=False)
    if kind=='far_indirect_jump' and transfer==0xEE4A:
     frame_owner.update(kind='observed_EE07_far_transfer_with_existing_protocol_frame',
       frame_transfer_capture_observed=True)
   elif kind=='call':assert word==(transfer+2)&65535;frame_owner.update(kind='observed_original_JSR_frame',creation_PC=transfer)
   folder=CPU/'actual-callers'/f'entry-{entry:04X}-{parent.parent.name}-state{state}-phase{phase}-ready{int(ready)}-A{int(new_A)}-{x["snapshot_sequence"]:04d}'
   folder.mkdir(parents=True,exist_ok=True);(folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram)
   n163=bytes((11+37*j)&255 for j in range(128));(folder/'input-n163.bin').write_bytes(n163)
   context=dict(schema='phase31-passive-player-disposition-caller-with-device-fixture-v1',
     origin='passive_Native_callee_capture_with_explicit_N163_fixture',ancestry_origin='controlled_ancestry' if controlled else 'natural_ancestry',
     controlled_ancestry=controlled,natural_ordinary_input_route=prep['natural_ordinary_input_route'],
     registers=r,physical_banks=x['actual_PRG_banks'],existing_return_PC=(word+1)&65535,
     N163_address=127,N163_autoincrement=True,N163_origin='explicit_shared_fixture_not_Native_snapshot',
     explicit_N163_fixture=dict(bytes=128,sha256=hashlib.sha256(n163).hexdigest(),pattern='(11+37*i)&255',address=127,autoincrement=True,
        scope='Common Source/originalCPU fixture; not instantaneous Native device capture'),
     prepared_numeric_bytes=[],additional_CPU_prepared_numeric_bytes=[],
     inherited_Native_preparation=prep['known_inherited_preparation'],known_inherited_preparation_byte_writes=prep['known_inherited_preparation_byte_writes'],
     ancestry_provenance=prep,controller_buttons=[0,0],injected_new_NMI=0,injected_new_IRQ=0,
     hardware_events=[dict(kind='explicit_model_port_inputs',PPUSTATUS=0,APU_status=0,Namco_IRQ=127,controller_buttons=[0,0])],
     actual_call_kind=kind,immediate_transfer_PC=transfer,immediate_transfer_proof=proof,real_return_frame_owner=frame_owner,
     state=state,phase=phase,mode=mode,side=side,original_queue_ready=ready,original_new_A=new_A,
     fade_87=ram[0x87],fade_negative_if_stage3=fade_negative,
     passive_capture=dict(metadata=str(path.relative_to(ROOT)),metadata_sha256=sha(path),frame=x['frame'],
       snapshot_sequence=x['snapshot_sequence'],event_sequence=x['event_sequence'],RAM_path=str(rp.relative_to(ROOT)),RAM_sha256=sha(rp),
       SRAM_path=str(sp.relative_to(ROOT)),SRAM_sha256=sha(sp),manifest=str(manifest.relative_to(ROOT)),manifest_sha256=manifest_digest,
       events_path=str((parent/'events.jsonl').relative_to(ROOT)),events_sha256=events_digest,
       preparation_path=str((parent/'preparation.json').relative_to(ROOT)),preparation_sha256=prep_digest),
     actual_software_state_captured=True,synthetic_caller_PC_or_stack=False,unmodified_core_internal_trace=False)
   dump(folder/'context.json',context);exports.append(folder);counts[f'{entry:04X}']+=1
   for p in(path,rp,sp,*folder.iterdir()):pins[str(p.relative_to(ROOT))]=sha(p)
 assert exports,'No eligible formal31 passive inputs'
 dump(CPU/'evidence.json',dict(schema='phase31-passive-player-disposition-provenance-v1',status='passed',ROM_sha256=ROM_SHA256,
   exported_caller_inputs=len(exports),targets=dict(counts),source_CPU_cases=0,original_CPU_prefix_instructions=0,
   instant_N163_captured=False,artifact_sha256=pins,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__)},
   selection='First actual entry/state/phase/mode/side/queue-ready/new-A/stage3-fade-sign combination per formal route; sparse captures only.',
   limits=['No transfer PC or caller instruction is inferred from raw return-minus3.',
     'Instantaneous N163/PPU/APU is not captured; common explicit device fixture remains separate.',
     'New passive observer is not the fixed unmodified core; five-buffer route parity has its own declared scope.']))
 (CPU/'README.md').write_text('''# 阶段31被动软件调用输入

只读复制正式runtime/*/observer中的实际寄存器/PC/SP、原栈、2K RAM、8K SRAM与实际四PRG。每条路线按entry/state/phase/queue-ready/new-A组合只取首现场，不从return−3反推call。被动边界若不能连续证明immediate transfer，则明确unknown/null；同一原有frame直接用于Source，不新push或seed return。

N163未在现场捕获。input-n163.bin、address127/autoincrement及2002/4015/5800/controller输入是共同明确的软件比较夹具；不是原机瞬时设备值。独立CPU/Source回调比较不注入新NMI/IRQ，不等于逐帧或整段不被中断的原机执行。原机连续路线及新核与固定核逐帧五buffer旁证由Root的runtime回执单列，不能推广成所有路径等价。

自然/受控祖先、已知准备及更早unknown原样保留在context。prepared_numeric_bytes和additional_CPU_prepared_numeric_bytes为空只说明本次导出/软件比较没有新增数值准备，不能抹去祖先记录。旧30现场用于回归另列，不复制到此新31目录。本轮不执行旧producer/core，不改旧目录。
''')
 print(json.dumps(dict(passive_exports=len(exports),targets=dict(counts))))

def main():
 p = argparse.ArgumentParser(description=__doc__)
 p.add_argument('rom', type=Path)
 p.add_argument('--import-native-callees', action='store_true')
 p.add_argument('--import-only', action='store_true')
 a = p.parse_args()
 rom = a.rom.read_bytes()
 assert hashlib.sha256(rom).hexdigest() == ROM_SHA256
 OUT.mkdir(parents=True, exist_ok=True)
 if a.import_native_callees:import_native(rom)
 if a.import_only:return
 catalog_path = ROOT / 'analysis/phase11/battle/catalog.json'
 catalog = read(catalog_path)
 assert catalog['rom_sha256'] == ROM_SHA256
 source = ROOT / 'source/recovered/battle_scene_controller.py'
 functions = {n.name: n.lineno for n in ast.walk(ast.parse(source.read_text())) if isinstance(n, ast.FunctionDef)}
 states, nodes, tables = [], {}, []
 for state in (13, 14):
  old = next(x for x in catalog['states'] if x['state'] == state)
  assert old['substate_count'] == 7
  table = old['substate_table_cpu']
  raw = rom[off(13, table):off(13, table) + 14]
  assert tuple(int.from_bytes(raw[i:i + 2], 'little') for i in range(0, 14, 2)) == PHASES[state]
  tables.append(dict(physical_bank=13, cpu=table, rom_offset=off(13, table),
                     bytes=14, raw_hex=raw.hex(' ').upper(), targets=PHASES[state]))
  for phase, pc in enumerate(PHASES[state]):
   fn = FUNCTIONS[state][phase]
   assert fn in functions and old['substates'][phase]['entry_cpu'] == pc
   states.append(dict(state=state, phase=phase, physical_bank=13, cpu=pc,
     rom_offset=off(13, pc), source_function=fn, source_line=functions[fn],
     behavior=MEANINGS[phase], existing_Source=True, first_recovery_claim=False))
   for node in old['substates'][phase]['nodes']:
    assert node['bank'] == 13
    raw = bytes.fromhex(node['raw_hex'])
    assert node['file'] == off(13, node['pc']) and rom[node['file']:node['file'] + len(raw)] == raw
    nodes[node['pc']] = dict(physical_bank=13, cpu=node['pc'], rom_offset=node['file'],
       bytes=node['size'], raw_hex=node['raw_hex'].upper(), opcode=node['op'],
       operand=node['operand'])
 ranges = []
 for bank, pc, count, name in ((13,0xCD16,0xCF34-0xCD16,'main13 body and inline table'),
    (13,0xD0C3,0xD1F9-0xD0C3,'leader/list/selection helpers before frozen22 settlement'),
    (13,0xD2CD,0xD4FB-0xD2CD,'main14 and main15 return body'),
    (13,0xDF27,18,'complete text readiness body through both RTS endpoints')):
  raw=rom[off(bank,pc):off(bank,pc)+count]
  ranges.append(dict(physical_bank=bank,cpu_start=pc,rom_offset=off(bank,pc),bytes=count,
                     raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest(),name=name))
 commit = [dict(physical_bank=13,call_pc=0xCF2D,callee=0xD1F9,raw_return_word=0xCF2F,return_pc=0xCF30),
           dict(physical_bank=13,call_pc=0xD486,callee=0xD1F9,raw_return_word=0xD488,return_pc=0xD489)]
 for x in commit: assert rom[off(13,x['call_pc']):off(13,x['call_pc'])+3] == bytes((0x20,0xF9,0xD1))
 static=dict(schema='phase31-reused-player-disposition-static-v1',ROM_sha256=ROM_SHA256,
   new_production_source_modules=0,new_gameplay_first_recovery=False,
   existing_source_credit=['phase11 direct BattleSceneController state13/14 and menu helpers',
      'phase22 named D1F9/D20D/D299 release and relocation',
      'phase30 exact 8A006 early AI/human disposition owner'],
   states=states,tables=tables,state_handler_node_union=sorted(nodes.values(),key=lambda x:x['cpu']),
   node_union_scope='Read-only frozen11 state-handler index; not a newly recovered full service closure or new code-position denominator.',
   original_byte_ranges=ranges,real_commit_calls=commit,
   main15=dict(physical_bank=13,entry=0xD4F0,draw_call=0xD4F0,LDY28_pc=0xD4F3,
     EE07_call=0xD4F5,inline_target=0xA006,return_pc=0xD4FA,
     code_pair_restored=[12,13],data8000_page_is_preserved_after_far_service=True),
   readiness=dict(physical_bank=13,entry=0xDF27,requires={'0304':255,'0300':255},
     new_A_mask=1,busy_or_no_input_is_normal_body_RTS=True),
   dependency_scope='No unowned dependency discovered in declared complete fixtures. Eight deliberately missing-service cases remain exact prefixes.')
 dump(OUT/'static-catalog.json',static)
 (OUT/'original.asm').write_text('\n'.join(f'13:{x["cpu"]:04X} file={x["rom_offset"]:06X} {x["raw_hex"]:<9} {x["opcode"]}' for x in static['state_handler_node_union'])+'\n')
 v=read(OUT/'validation.json')
 assert v['status']=='passed' and not v['quick'] and v['failed_count']==0
 for name,digest in v['source_sha256'].items(): assert sha(ROOT/name)==digest, name
 for name,digest in v['input_sha256'].items(): assert sha(ROOT/name)==digest, name
 groups=Counter('new31_passive' if x['case'].startswith('passive31/') else
    'inherited30_passive' if x['case'].startswith('inherited30-passive/') else
    'inherited30_BB36_controlled' if x['case'].startswith('inherited30-controlled-') else
    'new31_controlled' for x in v['cases'])
 observed=Counter()
 for x in v['cases']:
  for b in x['original_local_caller_protocol']:
   if b['registers']['pc'] in (0xBB36,0xBB8C): observed[f'{b["registers"]["pc"]:04X}']+=1
 dep=Counter(f'{call["target"]:04X}/{call["kind"]}/{call["status"]}' for x in v['cases'] for call in x['source_calls'])
 pins={str(x.relative_to(ROOT)):sha(x) for x in (OUT/'static-catalog.json',OUT/'original.asm',OUT/'validation.json',catalog_path)}
 cp=CPU/'evidence.json'
 ancestry=Counter(x['metadata']['ancestry_origin'] for x in v['cases'] if x['case'].startswith('passive31/'))
 if cp.exists():
  cx=read(cp);cx['ancestries']=dict(ancestry)
  cx['source_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(__file__)
  if (CPU/'README.md').exists():cx['artifact_sha256'][str((CPU/'README.md').relative_to(ROOT))]=sha(CPU/'README.md')
  dump(cp,cx);pins[str(cp.relative_to(ROOT))]=sha(cp)
 result=dict(schema='phase31-reused-readable-player-disposition-evidence-v1',status='passed',
   ROM_sha256=ROM_SHA256,new_production_source_modules=0,new_gameplay_first_recovery=False,
   original_CPU_parent_cases=v['original_CPU_parent_cases'],counts=v['counts'],groups=dict(groups),
   controlled_cases=groups['new31_controlled']+groups['inherited30_BB36_controlled'],
   passive_software_caller_cases=groups['new31_passive']+groups['inherited30_passive'],new31_passive_ancestries=dict(ancestry),
   source_guard_count=v['source_guard_count'],failed_count=0,source_original_CPU_callbacks=0,
   production_IR_interpretation=False,Native_runs_by_this_validator=0,
   per_caller_fresh_Source_instances=True,continuous_single_Source_UI_session_proven=False,
   same_Native_callback_may_contribute_multiple_API_layers=True,
   original_CPU_BB36_BB8C_boundary_observations=dict(observed),
   protocol_counts_are_software_oracle_observations_not_unique_Native_events=True,source_service_outcomes=dict(dep),
   declared_comparison=['all2048RAM including stack','all8192SRAM','AXYP/SP/PC',
     'all four PRG pages','combined ordered logical reads and writes','common explicit N163 bytes/address/autoincrement'],
   source_sha256=v['source_sha256'],input_sha256=v['input_sha256'],artifact_sha256=pins,
   analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),
   limits=v['limits']+['The Native continuous route and passive capture are independent evidence; fresh per-caller comparisons do not replay one Source UI session across frames.',
     'Inherited phase30 BB36 controlled cases are not Native reachability proof.',
     'No new city auxiliary field meaning or full-ROM completion claim.'])
 dump(OUT/'evidence.json',result)
 (OUT/'README.md').write_text(f'''# 阶段31玩家战后处置的既有源码对照

本轮未新增生产Source owner。现有 BattleSceneController 的 main13（CD16）/main14（D2CD）各7子态、phase22 PostbattleReleaseController 的 D1F9/D20D，以及 phase30 PostbattleEarlyGameEngine/SceneCoordinator 已覆盖此声明调用范围。既有玩法、指令具名和精确早态协议各保留原信用，不称首次恢复。

main13/14 的真实阶段表、原字节、Source函数与行号见 static-catalog.json。文本只在0304和0300都等于FF时允许确认；只新A位1推进，B/无输入或busy可正常RTS。菜单阶段由ED1E宽2选目标，ED23宽3选武将；坐标来自真实游标，不能直接伪写已选结果。确认经CF2D→D1F9→CF30或D486→D1F9→D489，之后重建phase0。空败方名单或胜方≤10名可返回15；15D4F0先画CC29、D4F3 LDY28、D4F5真实EE07(A006)到D4FA，再返回原caller。EE07只恢复代码pair12/13，E1数据窗副作用保留。

Source CPU对照 {v['original_CPU_parent_cases']} 案：{json.dumps(v['counts'],ensure_ascii=False)}；来源分组 {json.dumps(dict(groups),ensure_ascii=False)}；guard {v['source_guard_count']}，失败0。所有完成案比较2048RAM含栈、8192SRAM、AXYP/SP/PC、四PRG页、混合有序logicalIO及共同显式N163。原6502只在oracle侧运行，Source CPU callback=0、IR解释=0。8个缺服务prefix是主动撤去services的边界对照，不是已发现的新未知服务。

每个parent case独立克隆输入并新建GameEngine/SceneCoordinator。本回执证明逐caller软件合同，没有将这些调用串称单Source实例跨帧UI完整重放。同一原机callback可贡献wrapper/phase/leaf多个接口层病例，case数不是独立游戏路线或帧数。初始text queue/cursor/名单/按钮为明确受控夹具，不是Native ready写入。原机连续13/14→15与新被动capture由Root另供；被动现场2K/8K/实际寄存器/四银行/原栈真实，N163未瞬时捕获则仍用共同显式fixture。继承30的14现场与2个BB36受控parent另列，不称本轮新原机到达。py65无硬件dummy-cycle仿真，不宣称逐总线周期相同。

复现：`.venv-trace/bin/python scripts/verify_player_postbattle_phase31.py ROM`；随后 `.venv-trace/bin/python scripts/analyze_player_postbattle_phase31.py ROM`。只生成新31目录，不运行旧producer、不执行Native/core。本轮完成后停止，不自动启动32。
''')
 print(json.dumps({k:result[k] for k in ('status','original_CPU_parent_cases','counts','groups','source_guard_count')}))
if __name__=='__main__': main()
