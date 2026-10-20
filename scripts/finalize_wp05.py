#!/usr/bin/env python3
"""Finalize WP05 from existing Native receipts. Does not run a core or CPU."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp05-natural-nonempty';CACHE={}
def sha(p):
 p=Path(p);s=p.stat();key=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 if key not in CACHE:
  h=hashlib.sha256()
  with p.open('rb')as f:
   for b in iter(lambda:f.read(4194304),b''):h.update(b)
  t=p.stat();assert key==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns);CACHE[key]=h.hexdigest()
 return CACHE[key]
def pin(p):p=Path(p);return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def write(name,d):p=OUT/name;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def markdown(name,t):p=OUT/name;assert not p.exists();p.write_text(t.rstrip()+'\n')
def main():
 assert not(OUT/'verification.json').exists()
 f=read(OUT/'flow-validation.json');e=read(OUT/'evidence.json');n=read(OUT/'runtime/validation.json')
 assert f['status']=='passed'and f['evidence']['sha256']==sha(OUT/'evidence.json')
 assert n['fresh_process_runs']==4 and n['all_control_frames']==1532 and n['observer_events']==265872
 assert e['source_CPU_cases']==0 and e['new_gameplay_algorithms']==0
 # Byte identities of all four actual executions, including existing dependency pins.
 checked=0;deps={}
 for prefix in('runtime','runtime-repeat'):
  for variant in('original-control','observer'):
   folder=OUT/prefix/'natural-day31-nonempty'/variant;v=read(folder/'validation.json')
   assert v['status']=='passed'and v['frames']==383 and v['additional_core_memory_writes']==0
   for name,record in v['artifact_sha256'].items():
    p=folder/name;assert p.stat().st_size==record['bytes']and sha(p)==record['sha256'];checked+=1
   for d in v['dependency_pins']:
    assert sha(ROOT/d['path'])==d['sha256'];deps[d['path']]=d['sha256']
   assert v['core']['core_sha256']in('924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a','f886fefae5f2493d3931341cdb2458ff4a6637fcea8a15ffe818ebb399c9b0a6')
 b=read(OUT/'core-provenance/build.json')
 assert b['explicit_final_link_proven']and b['include_touch_rebuild_byte_identical']
 for row in b['source_files']:
  assert sha(ROOT/'.toolchain/wp05-observer-v2/upstream'/row['path'])==row['patched_sha256']
 assert sha(ROOT/b['observer']['path'])==sha(ROOT/b['last_build']['path'])==b['observer']['sha256']
 assert '-dynamiclib' in(ROOT/b['include_dependency_rebuild']['log']['path']).read_text()
 # Exact documented cold ancestor, separate from the new imported window.
 base14=ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle';v14=read(base14/'validation.json')
 base22=ROOT/'analysis/phase22/runtime/original-control';v22=read(base22/'validation.json')
 assert v14['cold_boot']and not v14['state_imported']and not v14['battery_file_imported']and v14['initial_SRAM_all_zero']and v14['additional_core_memory_writes']==0
 assert not v22['cold_boot']and v22['state_imported']and v22['additional_core_memory_writes']==0 and v22['preparation']==[]
 assert v22['mother_state']==str((base14/'city-commands.state').relative_to(ROOT))and v22['mother_sha256']==sha(base14/'city-commands.state')
 point=next(x for x in read(base14/'checkpoints.json')if x['state']=='city-commands.state');assert point['frame']==2922
 a=read(OUT/'ancestry.json');assert len(a['segments'])==6 and a['segmented_upstream_frames']==88463
 assert sha(base22/'final.state')==a['segments'][0]['initial_state']['sha256']
 supplement=dict(schema='wp05-cold-origin-supplement-v1',status='verified_frozen_provenance_not_new_coldboot',
  cold_validation=pin(base14/'validation.json'),cold_checkpoint_manifest=pin(base14/'checkpoints.json'),cold_checkpoint=pin(base14/'city-commands.state'),
  cold_checkpoint_frame=2922,imported22_validation=pin(base22/'validation.json'),
  documented_cold_start=dict(state_imports=0,battery_file_imports=0,initial_SRAM_all_zero=True,additional_memory_writes=0),
  inherited_documented_preparation_count=0,controlled19byte_or_older_unknown_route_used=False,
  later_six_segment_single_run_frames=88463,new_window_state_imports=4,new_window_cold_boots=0,
  limits='These frozen provenance receipts support a natural zero-write content chain. They do not turn segmented single runs/imports into an uninterrupted or four-fresh cold campaign. The captured ancestry null for unrecorded preparation is a scope limit, not an imported controlled19-byte route.')
 write('ancestry-supplement.json',supplement)
 timeline=dict(schema='wp05-build-provenance-timeline-v1',
  initial_v2_builder_at_run_sha256=None,
  historical_hash_limit='The initial v2 builder-at-run source snapshot/hash was not recorded. Current reproduction-script identity is not backfilled as that historical hash.',
  initial_clean_build_argv=read(OUT/'core-provenance/initial-build-receipt.json')['build']['argv'],
  initial_default_target_dependency_rebuild_proved_final_link=False,
  later_explicit_target_relink=b['include_dependency_rebuild'],
  later_explicit_target_final_link_proven=b['explicit_final_link_proven'],
  current_reproduction_builder=pin(ROOT/'scripts/build_wp05_observer.py'),
  current_builder_scope='Revised explicit-final-target recipe for reproduction; not a saved initial at-run script.',
  independently_bound_evidence=['Recorded source/official patch identities','Actual clean/build and explicit final-link logs','Exact observer/last-build dylib bytes','Four fresh original/observer runtime equivalence'],
  at_run_hash_fabricated_or_backfilled=False)
 write('build-provenance-timeline.json',timeline)
 write('checker-refinement.json',dict(schema='wp05-offline-checker-refinement-v1',
  scope='Offline checker only; no Native recapture or game-state change.',
  initial_assertion='All post357 writes6171=value131 must be exactly one',
  finding='Actual D4BA FF→131 player return is followed by BC3C/BC43 same-value131→131 writes; address/value alone is insufficient attribution.',
  correction='Classify the actual physical13 D4BA event separately from the two physical8 later same-value stores.',
  final_receipt=pin(OUT/'flow-validation.json'),new_Native_frames_for_this_correction=0))
 delta=dict(schema='wp05-closure-acceptance-delta-v1',work_package='WP05',status='complete_with_declared_bounded_scope',
  frozen_requirement='analysis/closure-audit-20261018/unique-gap-register.json#G-NONEMPTY-MODE2',
  closure_gap_id='G-NONEMPTY-MODE2',result='Natural nonempty mode2 actual allocation and BB39 return demonstrated in the new383-frame window, repeated in four fresh processes.',
  acceptance_receipt=pin(OUT/'flow-validation.json'),native_comparison_receipt=pin(OUT/'runtime/validation.json'),
  satisfied=['Natural documented ancestry and ordinary A/release inputs only','Actual CF02 outcome1→1 writer','Real current JSR Push8/entry/RTS/continuation chain and mode2 dispatch','BDCD nonempty[67,FF×20] and BDB8 city16 roster FF→67','Fresh original/observer five-buffer byte equivalence from first actual callback, full imported state/RAM/SRAM before it','0overflow/0new memory injection and old inputs preserved'],
  initial_boundary_limit='Before first retro_run there is no RGB/audio callback. No initial image is fabricated; actual first frame7611 is the initial five-buffer video boundary.',
  uncovered=e['uncovered'],field_classification_changes=0,official_city_names=e['city_official_names'],
  overall_reverse_engineering_complete=False,unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
  next_recommendation=dict(work_package='WP02',reason='WP01 frozen audit is complete and the B517 current-JSR static premises/counterexamples are already located. A new corrected contract validator can be reviewed in a separate package; the frozen32 draft is not a passing CPU receipt.'),
  not_automatically_started=['WP02','WP06','WP08','phase32 completion','phase33'],
  stop='WP05 delivered, stop for parent assessment.')
 write('acceptance-delta.json',delta)
 source_rows=e['readable_source_mapping'];table=['# 可读源码与本次原机证据', '',
  '复用冻结的 PostbattleEarlyServices；本包没有新增玩法算法，也没有新跑 Source。以下是实际 Native 链到既有可读函数的对应，不是单实例 Source 连续性验收。', '',
  '| 可读函数 | 原代码 | 新证据 |', '|---|---|---|']
 labels={'allocate_defeated_attacker':('BD67','mode2实际分派、源城找空槽及真实返回'),
  'collect_side_officers_and_captives':('BDCD→BE54','真实生成[67,FF×20]'),
  'prioritize_original_commander':('BE55→BE89','Y0自交换两次67→67；非平凡重排未验'),
  'fill_pointed_city_roster':('BD96/BDB8→BDAA','6214:FF→67；同址dummy读单列')}
 for row in source_rows:
  address,claim=labels[row['method']];table.append(f"| [{row['method']}](../../{row['path']}#L{row['line']}) | {address} | {claim} |")
 table+=['', '实际链：BB36 JSR BC46 → BC49 JSR EADE（两PLA消费此层栈，EAF4间接JMP）→ BD67 → BDCD → BE54 RTS → BE55/BE89 → BD73/F2AF → BD8E JSR BD96 → BD99/F2AF → BDB8 → BDAA RTS → BD91 → BD95 RTS → BB39。',
  '', 'BDB8是BD96内部store标签，不是独立callee。BB39返回SP恢复EE；callee入口SP为EC，BD96入口EA。raw栈字与当前真实JSR两次Push8分别留证，未用ret−3猜实际调用者。',
  '', '武将67的完整12字节和战场unit10未改变；这里只验证战后归城分配。玩家131随后由13:D4BA回city11，另有两次BC3C/BC43同值写；不能并入67的分配或在野招募。']
 markdown('readable-source-map.md','\n'.join(table))
 markdown('README.md',f'''# WP05 · 自然非空mode2战后分配

**本工作包已完成有界验收。** 新窗口实际生成非空名单，将武将67写入城市16第4个武将槽，并沿原调用栈返回BB39。完成后停止，等待父级评估；未启动WP06/08或下一阶段。

## 本次新增

| 项目 | 实际结果 |
|---|---|
| 输入/范围 | 从冻结32 day30第7610帧末态导入；172帧松键、A2、松键180、A2、松键27，共383帧，至旧路线7993 |
| 原模拟器复跑 | 原固定核与新被动核各两次独立进程：4fresh、383首跑帧、1532总控制帧 |
| 完整缓冲 | 每实际帧RAM/SRAM/RGB/PCM/full serialized state逐字节一致，不归一化；3461项非空产物复跑检查 |
| 原始观察 | 首观察运行265872事件、122完整2K/8K软件快照；独立复跑内容相同；溢出0 |
| 结果原写入 | local1 seq412，physical9:CF02实际STA0514，1→1，同值写仍明确捕获 |
| 非空收集 | local357，BDCD/BDF7生成[67,FF×20] |
| 名册写入 | local357 seq246991，physical8:BDB8，ptr6200/Y14(hex)，6214:FF→67 |
| dummy读取 | 前一seq246990同址6214读FF，是STA原dummy读，不当作字段逻辑消费 |
| 真实返回 | BD96/BDAA→BD91→BD95→BB39；SP EA→EC→EE，两层原始返回字及实际Push8留证 |
| 可选交换 | BE55实际执行Y0自交换，BE80/BE86两次67→67；不同槽位的非平凡交换未覆盖 |

完整断言见 [flow-validation.json](flow-validation.json)，原始事件、实际栈写和快照绑定见 [evidence.json](evidence.json)。源城16名单由[163,158,89,FF…]变为[163,158,89,67,FF…]。武将67原12字节保持484f4a545000e803e803281a；这是已有武将的战后归城分配。玩家131在local359由13:D4BA另写6171，随后同值写另列，未计入67分配。

## 来源与比较边界

母态内容链是31前五段80853帧＋冻结32前缀7610帧＝88463祖先单跑帧，排除后来segment07..10及141636帧duel母链。阶段14的零写入冷启、阶段22导入和相邻存档衔接另见 [祖先补充核验](ancestry-supplement.json)。本次四次均为导入态、0新增准备/内存写、无PC/ready/RNG/结果/名册注入；没有新冷启动或全战役fresh声明。

导入后、首次retro_run前，接口尚无RGB或音频回调；该边界只比较完整state及2K/8K，并记录RGB不可用、PCM为空。首个真实回调帧7611作为初始五缓冲视频边界，其后每帧五缓冲全量比较。软件快照不含即时N163/PPU/APU，不伪造初始图像。

终点global2/NMI2、city13/0，是全黑画面的城市调度/过渡边界；不宣称已回到可操作world0/1或完成随后city13事件。052C变化只由软件快照确认，本观察写域未捕获其BDB4总线写。完整原输入和捕获回执在 [runtime](runtime/evidence.json)；代表性原画面：[结算](runtime/natural-day31-nonempty/original-control/frame-00357.png)。

## 构建与交付

固定原核心SHA924191eb…a539a保持。新观察核SHAf886fefa…9b0a6，独立72u32 ABI；const backing快照、实际JSR/RTS/continuation与原Push8写记录。源码、官方commit、编译器、clean build、实际最终dylib链接及依赖重编逐字相同证明见 [构建回执](core-provenance/build.json)。初始v1构建未用于任何Native运行，保留为构建草稿；正式采用v2。旧32版本和哈希错配均未就地修复。

构建时点分开记录：初次旧builder完成clean/build，默认目标的依赖重编未证明最终链接；随后显式dylib目标实际重编并链接，完整二进制相同；当前builder是修订后的复现版本。初次v2 builder-at-run快照/hash未记录，保持null，没有倒填当前脚本SHA。源/补丁、真实链接、二进制和fresh运行等价证据独立成立。详见 [build-provenance-timeline.json](build-provenance-timeline.json)。

已有可读源码的函数与新证据对应见 [readable-source-map.md](readable-source-map.md)。本包Source案例0、独立字段CPU合同0、新玩法算法0；顺带保存的14份实际E066现场留待后续独立验收，不启动WP08。

最终只读校验见 [verification.json](verification.json)，输入/输出hash见 [input-manifest.json](input-manifest.json) 与 [artifact-manifest.json](artifact-manifest.json)。31全部91929依赖pins/596源码脚本pins、32全部2101残留及closure全部16文件保持不变。只有完整逐字比较之后才在新目录内硬链接去重；未重打历史大包，未包含或分发ROM。

字段账本仍1526=1201条件排除/80possible/245unknown，剩325；raw345独立，城市+1/+28..31正式名称仍null，整款闭包仍false。下一个建议包是WP02（B517当前JSR合同），此处只建议并停止，不自动执行。完成百分比、未知服务数、剩余轮数均null。
''')
 # A final preservation pass is independent of the earlier content-manifest checks.
 subprocess.run([sys.executable,str(ROOT/'scripts/verify_wp05_frozen_inputs.py'),'after'],check=True)
 frozen=read(OUT/'frozen-after.json');assert frozen['status']=='passed'and not frozen['changed']
 scripts=['scripts/capture_native_wp05_nonempty.py','scripts/build_wp05_observer.py','scripts/prepare_wp05_case.py',
  'scripts/verify_wp05_nonempty_flow.py','scripts/verify_wp05_frozen_inputs.py','scripts/finalize_wp05.py']
 inputs=dict(schema='wp05-input-manifest-v1',frozen_before=pin(OUT/'frozen-before.json'),frozen_after=pin(OUT/'frozen-after.json'),
  original_ROM=dict(path=str(ROM)if 'ROM'in globals()else'/Users/paulasmith/Downloads/三国志2超级版.nes',sha256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'),
  scripts=[pin(ROOT/p)for p in scripts],scripts_kind='Current source revisions; historical at-run identity is claimed only where separately recorded by execution receipts.',
  build=pin(OUT/'core-provenance/build.json'),build_timeline=pin(OUT/'build-provenance-timeline.json'),
  active_core=pin(ROOT/b['observer']['path']),active_last_build=pin(ROOT/b['last_build']['path']),
  source_files=[pin(ROOT/'.toolchain/wp05-observer-v2/upstream'/row['path'])for row in b['source_files']],
  dependency_sha256=deps)
 write('input-manifest.json',inputs)
 files={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(OUT.rglob('*'))
  if p.is_file()and p.name not in('artifact-manifest.json','verification.json')}
 write('artifact-manifest.json',dict(schema='wp05-artifact-manifest-v1',files=files,
  excluded=['artifact-manifest.json','verification.json'],self_reference_avoided=True,
  includes_ROM=False,includes_emulator_binaries=False))
 v=dict(schema='wp05-final-readonly-verification-v1',status='passed',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  work_package='WP05',work_package_complete_with_declared_scope=True,
  actual_semantic_validation=pin(OUT/'flow-validation.json'),Native_validation=pin(OUT/'runtime/validation.json'),
  build_timeline=pin(OUT/'build-provenance-timeline.json'),
  frozen_preservation=pin(OUT/'frozen-after.json'),input_manifest=pin(OUT/'input-manifest.json'),artifact_manifest=pin(OUT/'artifact-manifest.json'),
  checks=dict(captured_artifact_hash_checks=checked,captured_dependency_paths=len(deps),
   producer_source_pins_current=True,active_observer_build_source_binary_ABI_match=True,
   actual_clean_and_final_link_present=True,touch_include_rebuild_full_binary_identical=True,
   actual_current_JSR_frames=7,actual_nonempty_officers=1,actual_BDB8_commits=1,actual_dummy_reads=1,
   actual_same_value_outcome_writes=1,true_BB39_PC_SP_return=True,all_captured_buffers_preserved=True,
   formal_old_pins=91929,old_source_validator_pins=596,old32_residue_files=2101,old32_residue_bytes=110119793,closure_files=16,all_frozen_bytes_unchanged=True),
  new_execution=dict(Native_first_original_frames=383,Native_all_control_frames=1532,Native_fresh_processes=4,
   Source_CPU_cases=0,independent_field_CPU_cases=0,additional_emulated_memory_writes=0),
  overall_reverse_engineering_complete=False,field_classification_changes=0,remaining_field_candidates=325,
  official_city_names=e['city_official_names'],unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
  limits=e['limits'],stop='Completed WP05 only; stop for parent assessment. No automatic next package or phase.')
 write('verification.json',v);print(json.dumps(dict(status='passed',work_package='WP05',artifacts=len(files),hash=sha(OUT/'verification.json'),new_execution=v['new_execution'])),flush=True)
if __name__=='__main__':main()
