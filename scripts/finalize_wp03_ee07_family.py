#!/usr/bin/env python3
"""Offline buffer/trace/identity audit and immutable EE07 package seal."""
from pathlib import Path
import argparse,ast,collections,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-ee07-return-family';RUN=OUT/'run-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rec(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def save(n,x):
 p=OUT/n;assert not p.exists(),p;p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def audit():
 v=read(RUN/'validation.json');a=read(OUT/'acceptance.json');scope=read(OUT/'family-scope.json');plan=read(OUT/'case-matrix.json')
 assert v['status']=='passed_full_declared_return_family'and sha(RUN/'cases.jsonl')==v['cases_sha256']
 for name,key in(('family-scope.json','scope_sha256'),('case-matrix.json','matrix_sha256'),('cross-ledger-relations.json','cross_ledger_sha256')):assert sha(OUT/name)==a[key]
 assert sha(OUT/'acceptance.json')==v['acceptance_sha256']
 for p,h in a['implementation_pins'].items():assert sha(ROOT/p)==h,p
 for p,row in v['buffers'].items():assert rec(RUN/p)['sha256']==row['sha256']and(RUN/p).stat().st_size==row['bytes']==656*10240
 buffers={n[:-11]:(RUN/n).read_bytes()for n in v['buffers']}
 assert buffers['CPU-forward']==buffers['Source-forward']and buffers['CPU-callee-return']==buffers['Source-callee-return']and buffers['CPU-final']==buffers['Source-final']
 groups=collections.Counter();counts=collections.Counter();examples={};waits=[];keys=[]
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==scope['ROM_SHA256']
 for spec,line in zip(plan['cases'],(RUN/'cases.jsonl').open(),strict=True):
  r=json.loads(line);assert r['spec']==spec and r['case']==spec['key']and r['status']=='passed'
  site=scope['sites'][spec['site_index']];S=spec['registers']['sp'];offset=r['snapshot_offset'];assert offset==len(keys)*10240
  for name,data in buffers.items():assert hashlib.sha256(data[offset:offset+10240]).hexdigest()==r['snapshot_sha256'][name]
  initial=buffers['initial'][offset:offset+10240];rebuilt=bytearray(initial);trace=r['CPU']['trace']
  assert trace[0]['pc']==site['call_pc']and trace[-1]['pc']==0xEE52
  assert len(trace)==r['CPU']['instructions']and not any(t['pc']==site['continuation']for t in trace)
  for step in trace:
   code=rom[16+step['bank']*8192+(step['pc']&8191)]
   if step['pc']in(site['body_rts'],0xEE52):assert code==0x60
   for w in step['writes']:
    q=w['address'];p=q&2047 if q<8192 else q-0x6000+2048
    assert rebuilt[p]==w['before'];rebuilt[p]=w['value']
  assert bytes(rebuilt)==buffers['CPU-final'][offset:offset+10240]
  c=r['CPU'];j=c['actual_JSR'];assert j['before']['registers']==spec['registers']and j['after']['registers']['pc']==0xEE07
  assert[(w['address'],w['value'])for w in c['five_pushes']]==[(0x100+((S-i)&255),x)for i,x in enumerate((0xA0,(site['call_pc']+4)&255,spec['raw_E2'],0xEE,0x4C))]
  assert c['real_callee_RTS']['after']['registers']['pc']==0xEE4D and c['real_callee_RTS']['frame']==[0x4C,0xEE]
  assert c['real_EE52_RTS']['after']['registers']['pc']==site['continuation']and c['real_EE52_RTS']['after']['registers']['sp']==S
  assert c['real_EE52_RTS']['after']==r['Source']['final']and r['Source']['callback_return']==c['real_callee_RTS']['after']
  assert r['full_2K_8K_checked']and r['all_nonwrite_RAM_checked']and r['whole_SRAM_unchanged']and not r['actual_outer_RTS']
  assert r['Source']['real_callee_runs']==1 and r['Source']['CPU_IR_callbacks']==0 and not r['Source']['callee_seed_return']
  actual=[e for e in r['Source']['audit']if e['mode']=='actual'and e['target']==site['target']]
  assert len(actual)==1 and actual[0]['status']=='returned'and actual[0]['entry_banks'][1:3]==site['target_pair']
  assert buffers['CPU-forward'][offset:offset+10240]==buffers['Source-forward'][offset:offset+10240]
  if spec['site_index']==0:
   final=buffers['CPU-final'][offset:offset+10240];assert final[0x401]==1 and final[0x470:0x474]==bytes.fromhex('00880024')
  if spec['withhold']:
   assert r['Source']['wait_evidence']==[dict(missing_status='dependency',fake_status='dependency',fake_zero_bus_REG_progress=True,same_pending_callee=True)]
   assert[e['mode']for e in r['Source']['audit']if e['target']==site['target']]==['missing','fake','actual'];waits.append(r)
  if spec['site_index']not in examples:examples[spec['site_index']]=r
  keys.append(r['case']);groups[spec['group']]+=1;counts['CPU_instructions']+=len(trace);counts['real_callee_RTS']+=1;counts['real_EE52_RTS']+=1
 assert len(keys)==656 and dict(groups)==plan['groups']and counts['CPU_instructions']==54120 and len(waits)==2
 ledger=ROOT/'analysis/wp03-shared-entry-family'
 for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json'):
  assert not(OUT/n).exists();shutil.copyfile(ledger/n,OUT/n);assert(ledger/n).read_bytes()==(OUT/n).read_bytes()
 save('ledger-preservation.json',dict(files=[dict(previous=rec(ledger/n),current=rec(OUT/n),byte_identical=True)for n in('all-indirect-accesses.json','remaining-accesses.json','raw345-executability-ledger.json')],
  instruction_objects_unchanged=1526,remaining_objects_unchanged=323,raw_objects_unchanged=345,classification_changes=0,
  reason='Two controlled caller/phase contracts do not close all EE07 inputs, bank mappings, arbitrary entry or remaining field semantics.'))
 cross=read(OUT/'cross-ledger-relations.json');evidence=[]
 for i,rel in enumerate(cross['relations']):
  r=examples[i];inline=[x for x in r['CPU']['inline_and_PLA_reads']if x['probe']=='inline_data']
  assert[x['address']for x in inline]==rel['data_addresses']
  evidence.append(dict(**rel,example_case=r['case'],actual_original_inline_reads=inline,callee_body_executed=True,
   actual_callee_RTS=r['CPU']['real_callee_RTS'],actual_EE52_RTS=r['CPU']['real_EE52_RTS'],
   excluded_interpretations=['Not a pure data window: third byte remains original RTS','Raw window starting opcode execution is not proved','BCBF/C443 consumers not executed in these phases','No common semantic root inferred']))
 save('raw-window-consumer-evidence.json',dict(relations=evidence,raw_classification_changes=0,global_semantic_root=None))
 save('strict-callee-resume-evidence.json',dict(parent_cases=waits,strict_missing_callee_count=2,fake_zero_progress_count=2,
  pending_identity_scope='Same callee ServiceCall object explicitly asserted. Same owner/generator identity not separately dynamically asserted.',
  original_CPU_or_Source_executions_in_this_audit=0))
 save('shared-interface-contract.json',dict(resolved_dependency=scope['bounded_dependency'],sites=scope['sites'],
  resolved_window='Actual current JSR -> inline word -> mapper switch -> real named callee body -> real callee RTS to EE4D -> code-pair restoration -> real EE52 RTS -> ordinary continuation before opcode',
  Source_parent_cases=656,CPU_parent_cases=656,stateful_returns=328,busy_only_returns=328,CPU_instructions=54120,
  known_direct_EE07_callers=155,this_package_callers=2,outside_this_package_callers=153,global_remaining_shared_services=None,
  entry_conditions=scope['premises'],code_pair_restored=True,E1_or_data_window_not_generically_restored=True,
  data_page_side_effect_tested=False,data_page_effect_note='These selected bodies do not write E1. A phase1 callee that changes E1 is a proposed next scope, not executed here.',
  new_gameplay_algorithms=0,production_Source_changes=0,Native_new_runs=0,natural_A06F_A077_capture=False,outer_RTS_executions=0,
  full_campaign_or_WP08_closure=False,global_field_names_confirmed=False))
 save('next-minimal-package-readiness.json',dict(status='static_ready_for_separate_scope_lock_only',suggested_family='A06F ->29:A039/0401=1 ->BC9B..BD02',
  body_owner='CityUIWorkers.cityuiworkers_bc74_phase_1',new_field_consumer='29:BCBF',
  proposed_actual_premise='Use phase0 output values0470..0473=00,88,00,24 as disclosed controlled phase1 inputs; do not call it natural scheduling continuity.',
  expected_data_effect='BC9D calls real F25F(Y30): raw E1=30 and physical8000 bank16; EE07 must restore only code pair, retaining E1/data side effect.',
  minimum_services=['fixed F25F mapper service','optional ECEE palette transition only when destination high reaches28'],
  expected_copy='64 ROM bytes from current 0470/0471 pointer to0383..03C2, terminator at03C3, advance source/destination by0x40, set007E bit2',
  must_declare=['fresh scope/matrix/acceptance before execution','actual caller frame provenance','real BD02 RTS through EE4D/EE52','source/destination page carry and ECEE branch','strict unknown/PPU boundary if encountered'],
  Source_CPU_Native_executions=0,global_city_field_names={str(x):None for x in(1,28,29,30,31)},other_panel_phase0='A077/C441/C443 remains a separate unexecuted phase, not closed by busy-only case.'))
 save('semantic-validation.json',dict(status='passed_offline_full_buffer_trace_audit',cases=656,Source_cases=656,**dict(counts),
  groups=dict(groups),both_sides_saved=True,bytes_per_snapshot=10240,stages=['forward-before-callee','after-real-callee-RTS','after-real-EE52-RTS'],
  original_CPU_or_Source_executions_in_this_audit=0,Native_new_runs=0,outer_RTS_executions=0,field_changes=0,raw_changes=0,remaining=323,
  official_city_names={str(x):None for x in(1,28,29,30,31)},unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,whole_game_closure_proven=False))
 docs()
 print(json.dumps(dict(status='passed_offline_audit',cases=656,CPU_instructions=54120,Source_CPU_executions=0,both_sides_saved=True)))

def docs():
 text='''# EE07 城市菜单远端调用：真实正文与返回链

本轮完成一个有界入口族的验证：`27:A06F` 的城市菜单初始化，以及 `27:A077` 的面板忙碌分支。两条路径都执行已有可读源码中的真实 callee，并通过 EE4D、F237、EE52 返回调用方。主路径不是仅抵达 callee：实际写入 `0470..0473 = 00 88 00 24`，`0401:0→1`。

| 项目 | 本轮证据 |
|---|---|
| Source / 原 ROM CPU | 各 656 个受控父案例，54,120 条原 CPU 指令 |
| 主路径 / 忙碌分支 | 各 328；主路径 owner 为 CityUIWorkers，次路径为 CityPanelServices |
| 真实 callee RTS / EE52 RTS | 各 656 次；停在 A074/A07C 首条指令之前 |
| 栈与输入 | 每入口覆盖 256 个 SP；32 个状态组合；8 个 raw E2 别名；32 个数据页 |
| 严格依赖 | 2 次缺 callee 停住，2 次 fake returned 零内存/REG进展，同 pending callee 真正恢复各一次 |
| 双方完整输出 | 每案保存初态、forward、callee 返回、最终 2K RAM+8K SRAM；Source/CPU 双方分开保存后三段 |
| 原模拟器新运行 | 0；没有这两个入口的自然瞬时现场，不将受控 CPU 对照记作自然 Native |

主路径：`A06F JSR EE07` → inline `A039` → selector `3D`、物理29/30 → `A039 JMP BC71` → `BC74` phase0 → `BC83..BC9A` → 真 RTS 到 `EE4D` → `F237` 恢复原代码页 → `EE52 RTS` → `A074`。

次路径：`A077 JSR EE07` → inline `A01E` → selector `39`、物理25/26 → `A01E JMP C435` → phase1 且 `007E!=0` → `C5BE RTS` → `EE4D/EE52` → `A07C`。这只覆盖忙碌返回，不代表面板其余阶段完成。

## 可读源码的整合

现有生产源码已经具备这两段正文及 coordinator 路由，因此本轮没有重写游戏算法。新增的 [窄入口适配器](readable_entry.py) 复用 `CityUIController._external` 与真实 `SceneCoordinator`，让当前 JSR 进入原有 Source owner。所有 callee 保留真实现有栈，`run_entry` 默认 `seed_return=False`；Source 不接收 CPU/IR 回调或原 CPU 输出。对照先运行独立 Source，再执行原 ROM CPU。

本轮起点直接是已声明的 A06F/A077 当前调用位置与 Y 寄存器；前置 LDY 未执行。不构造外层返回帧，不执行 A074/A07C 自身 RTS，不称整场城市 UI 或长期战役已经通过。测试使用基础 GameEngine/SceneCoordinator，不是 CampaignSession/frontdoor 连续战役测试。

## 字段与跨账本关系

城市 `+1`、`+28..31` 正式字段名继续为 `null`。1526 条总访问、1203 条条件排除、80 条 possible、243 条 unknown、剩余 323 条均保持原对象与分类；原始345窗口的104 operand /13 data /228未证入口也不迁移。

本轮给 raw249 `b27:off0072:rom036082`（39 A0 60）及 raw250 `b27:off007A:rom03608A`（1E A0 60）补充实际字节角色：前两字节由 `31:EE1F/EE25` 作为远端地址读取；第三字节仍是调用方原 RTS，本轮只到达它之前。两者都是混合窗口，不能整块叫纯数据，也未证明 raw 起点被当 opcode 执行或其他入口不可达。下游 `29:BCBF` / `26:C443` 均未执行，共同语义根仍为 `null`。

冻结 atlas 里共有 155 个独立直接 `JSR EE07` callsite，本轮纳入2个，其余153个是“该清单中未由本包覆盖的调用点”，不能当作全项目未恢复服务数。全局真正剩余服务数、完成比例和预计轮数仍为 `null`。

执行后元数据审查纠正了静态调用清单中8个 bank9 的 ID 填充：canonical 是十进制两位 `b09`。原清单、prepare 脚本及执行时哈希保持原样，另存 [canonical-v2 清单](known-direct-caller-inventory-v2.json) 和 [8条别名映射](typed-ID-normalization.json)。物理银行、CPU/ROM地址、病例及执行范围均未变化，也未重跑 Source/CPU。所选两个入口及跨账本映射的 ID 不受影响。

## 证据与边界

- [预锁范围](family-scope.json)、[656案矩阵](case-matrix.json)、[预锁验收](acceptance.json)
- [Root实际执行回执](run-01/validation.json)、[逐指令与Source边界记录](run-01/cases.jsonl)、[离线复核](semantic-validation.json)
- [raw窗口消费者](raw-window-consumer-evidence.json)、[严格依赖恢复](strict-callee-resume-evidence.json)、[账本零迁移](ledger-preservation.json)
- [独立下一包准备](next-minimal-package-readiness.json)：仅静态建议 A06F/phase1 的真实64字节复制与 E1 副作用；本轮未执行。

旧工作239445个路径应由最终 before/after 回执逐项保持；另外补充祖先核验，将 EADE 冻结的239404个哈希逐项承接，避免把新采样误当历史一致性。旧 EADE、WP02、WP05、WP08、phase31及phase32残留均不修改。执行前 scope/matrix/acceptance 及生产 Source/脚本哈希已锁定；最终 seal 还核跨账本 SHA。冻结历史和新包各自独立。

完成本包后停止，等待评估。没有宣称全游戏、在野招募自然成功、正式城市字段或完整战役闭环完成。
'''
 p=OUT/'README.md';assert not p.exists();p.write_text(text)
 html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>EE07 真实正文与返回链</title><style>body{max-width:920px;margin:48px auto;padding:0 24px;font:17px/1.75 system-ui;color:#20252b;background:#faf9f6}a{color:#165f8c}h1{font-size:30px}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #ccc;text-align:left}code{background:#eee;padding:2px 5px}</style><h1>城市菜单远端调用：正文与返回链已验证</h1><p>656组受控 Source / 原 ROM CPU 对照通过。主路径真实初始化菜单状态，次路径验证面板忙碌返回；两者均经 EE4D 恢复代码页，再由 EE52 返回普通调用方。</p><table><tr><th>验证项</th><th>结果</th></tr><tr><td>主路径 / 忙碌分支</td><td>328 / 328</td></tr><tr><td>原 CPU 指令</td><td>54,120</td></tr><tr><td>真实 callee 返回 / EE52 返回</td><td>656 / 656</td></tr><tr><td>新增原模拟器自然证据</td><td>0</td></tr><tr><td>候选访问 / raw窗口分类变化</td><td>0 / 0；剩余323条，正式城市字段名仍待确认</td></tr></table><p>停点为 A074 / A07C 首条指令前。未执行外层 RTS，未宣称整个城市 UI、在野招募或长期战役完成。</p><p><a href="README.md">完整分析与源码入口</a> · <a href="run-01/validation.json">执行结果</a> · <a href="shared-interface-contract.json">有界合同</a> · <a href="raw-window-consumer-evidence.json">字节消费者</a> · <a href="next-minimal-package-readiness.json">下一包静态准备</a> · <a href="verification.json">最终封存</a></p></html>'''
 p=OUT/'index.html';assert not p.exists();p.write_text(html)

def seal():
 v=read(RUN/'validation.json');a=read(OUT/'acceptance.json');s=read(OUT/'semantic-validation.json')
 assert v['status']=='passed_full_declared_return_family'and s['status']=='passed_offline_full_buffer_trace_audit'
 for name,key in(('family-scope.json','scope_sha256'),('case-matrix.json','matrix_sha256'),('cross-ledger-relations.json','cross_ledger_sha256')):assert sha(OUT/name)==a[key]
 for name,h in a['implementation_pins'].items():assert sha(ROOT/name)==h,name
 before,after,ancestral=[read(OUT/n)for n in('frozen-before.json','frozen-after.json','frozen-ancestral-before.json')]
 assert before['status']==after['status']==ancestral['status']=='passed'
 assert before['old_work_paths']==after['old_work_paths']==239445 and before['full_work_manifest_sha256']==after['full_work_manifest_sha256']
 assert ancestral['previous_frozen_paths']==239404 and ancestral['current_frozen_paths']==239445
 norm=read(OUT/'typed-ID-normalization.json');canonical=read(OUT/'known-direct-caller-inventory-v2.json');original=read(OUT/'known-direct-caller-inventory.json')
 assert norm['alias_count']==8 and norm['canonical_inventory_sha256']==sha(OUT/'known-direct-caller-inventory-v2.json')
 assert norm['original_inventory_sha256']==sha(OUT/'known-direct-caller-inventory.json')
 for before,row in zip(original['callers'],canonical['callers'],strict=True):
  assert all(before[k]==row[k]for k in('bank','pc','rom_offset'))
  assert f':b{row["bank"]:02d}:'in row['id']
 for p in(ROOT/'scripts').glob('*wp03_ee07*.py'):ast.parse(p.read_text())
 save('input-manifest.json',dict(current_producers=[rec(p)for p in sorted((ROOT/'scripts').glob('*wp03_ee07*.py'))],
  executed_implementation_pins=a['implementation_pins'],execution_inputs=rec(RUN/'execution-inputs.json'),
  adapter=rec(OUT/'readable_entry.py'),previous_EADE=rec(ROOT/'analysis/wp03-shared-entry-family/verification.json'),
  original_static_inventory=rec(OUT/'known-direct-caller-inventory.json'),canonical_inventory=rec(OUT/'known-direct-caller-inventory-v2.json'),ID_normalization=rec(OUT/'typed-ID-normalization.json'),
  prior_work=rec(OUT/'frozen-work-inputs.json'),ancestral_check=rec(OUT/'frozen-ancestral-before.json'),
  original_emulator=rec(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'),ROM_SHA256=read(OUT/'family-scope.json')['ROM_SHA256'],
  ROM_distributed=False,Native_new_runs=0,offline_finalizer_not_part_of_Source_execution=True))
 files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.rglob('*'))if p.is_file()}
 save('artifact-manifest.json',dict(files=files,excludes=['artifact-manifest.json','verification.json']))
 save('verification.json',dict(schema='wp03-EE07-real-callee-return-final-v1',status='passed_bounded_EE07_real_callee_return_family',
  Source_parent_cases=656,original_CPU_parent_cases=656,original_CPU_instructions=54120,stateful_returns=328,busy_only_returns=328,
  real_callee_RTS=656,real_EE52_RTS=656,outer_RTS_executions=0,strict_missing_callee_parents=2,fake_return_zero_progress=2,
  saved_two_sided_memory_stages=3,Native_new_runs=0,exact_natural_A06F_A077_origin=False,
  actual_entry='Controlled actual callsite PC/Y/REG/PRG/RAM/SRAM',execution_manifest=rec(RUN/'execution-inputs.json'),
  acceptance_sha256=sha(OUT/'acceptance.json'),scope_sha256=sha(OUT/'family-scope.json'),matrix_sha256=sha(OUT/'case-matrix.json'),
  cross_ledger_sha256=sha(OUT/'cross-ledger-relations.json'),semantic_validation_sha256=sha(OUT/'semantic-validation.json'),
  artifact_manifest_sha256=sha(OUT/'artifact-manifest.json'),artifact_manifest_entries=len(files),
  preserved_work_paths=239445,verified_ancestral_paths=239404,old_paths_missing_or_changed=0,
  fixed_ledger_counts=dict(total=1526,conditional_disjoint=1203,possible=80,unknown=243,remaining=323,raw345=345,raw104=104,raw13=13,raw228=228),
  field_classification_changes=0,raw_classification_changes=0,official_city_names={str(x):None for x in(1,28,29,30,31)},
  known_direct_EE07_callers=155,tested_callers=2,inventory_callers_outside_this_package=153,
  global_remaining_shared_services=None,production_Source_changes=0,new_gameplay_algorithms=0,production_CPU_IR_fallback_added=False,
  static_inventory_ID_aliases=8,original_execution_pins_preserved=True,canonical_inventory_sha256=sha(OUT/'known-direct-caller-inventory-v2.json'),
  whole_game_closure_proven=False,completion_percentage=None,remaining_rounds_estimate=None,stopped_after_locked_package=True))
 print(json.dumps(dict(status='sealed',verification_sha256=sha(OUT/'verification.json'),manifest_entries=len(files),preserved_paths=239445)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('audit','seal'));a=p.parse_args();audit()if a.mode=='audit'else seal()
