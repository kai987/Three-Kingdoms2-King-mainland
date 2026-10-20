#!/usr/bin/env python3
"""Focused G107 parent/owner audit from frozen25 inputs; no CPU/core run."""
from pathlib import Path
import ast,argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase26/context'
SPEC=importlib.util.spec_from_file_location('frozen25_owner_index',ROOT/'scripts/analyze_service_gaps_phase25.py');index=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(index)
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ACCESS_PC=(0xB272,0xB278,0xB290,0xB296)
INPUTS=('analysis/phase25/verification.json','analysis/phase25/services/verification.json','analysis/phase25/services/owner-route-catalog.json','analysis/phase25/services/analysis-summary.json','analysis/phase25/acceptance/requirements.json','analysis/phase25/fields-static/selection-comparison.json','analysis/phase25/fields-static/all-indirect-accesses.json','analysis/phase11/setup-ai/validation.json','analysis/phase11/setup-ai/evidence.json','analysis/phase11/initialization/validation.json','analysis/phase25/source-integration.json','analysis/phase18/control/instruction-atlas.json','analysis/phase11/runtime/cold-battle/supply-third.state','analysis/phase11/runtime/cold-battle/handoff-011-g03-n03.state')
SOURCES=('source/recovered/appearance_pointer_integration.py','source/recovered/pointer_lifecycle_integration.py','source/recovered/scene_coordinator.py','source/recovered/scene_initialization.py','source/recovered/battle_setup_ai.py','source/recovered/deployment_pointer_services.py','source/recovered/deployment_pointer_integration.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def save(n,v):OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def original(bank,pc):return 16+bank*0x2000+(pc&0x1FFF)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');args=p.parse_args();rom=Path(args.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 baseline=read('analysis/phase25/verification.json');assert baseline['status']=='passed'
 service=read('analysis/phase25/services/verification.json');paths=sorted(path for path in service['source_and_validator_sha256']if path.startswith('source/recovered/'))
 for path in paths:assert sha(ROOT/path)==service['source_and_validator_sha256'][path]
 registry=index.Registry(paths,'AppearancePointerSceneCoordinator');newpaths=paths+['source/recovered/deployment_pointer_services.py','source/recovered/deployment_pointer_integration.py'];current=index.Registry(newpaths,'DeploymentPointerSceneCoordinator');owners=[]
 for target in(0xA003,0xB130,0xB1B0,0xB2AE,0xB312):
  route=registry.resolve(target,[None,8,9,31]);assert route['owners']==['BattleSetupAI']
  newroute=current.resolve(target,[None,8,9,31]);assert newroute['owners']==['DeploymentPointerServices']
  owners.append(dict(physical_pair=[8,9],target=target,phase25_owner='BattleSetupAI',current26_owner='DeploymentPointerServices',phase25_route=route,current26_route=newroute,context='Explicit paired-code context for static route lookup;8000 data bank deliberately unknown. Not a new captured caller.'))
 tree=ast.parse((ROOT/'source/recovered/battle_setup_ai.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='BattleSetupAI');methods={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef)}
 helper_names={0xB1B0:'assign_strategies_and_positions',0xB2AE:'first_side_formation',0xB312:'second_side_formation'}
 for name in helper_names.values():assert name in methods
 local_calls=[]
 for method in methods.values():
  for call in ast.walk(method):
   if isinstance(call,ast.Call)and isinstance(call.func,ast.Attribute)and call.func.attr=='_local_call'and len(call.args)==3 and isinstance(call.args[0],ast.Attribute):
    pc=index.MISSING;ret=index.MISSING
    try:pc=ast.literal_eval(call.args[1]);ret=ast.literal_eval(call.args[2])
    except(ValueError,TypeError):pass
    if pc in(0xB16B,0xB195,0xB25D,0xB263):local_calls.append(dict(source_path='source/recovered/battle_setup_ai.py',source_line=call.lineno,parent_function=method.name,callee_function=call.args[0].attr,JSR_call_PC=pc,raw_return_word=pc+2,normal_return_PC=ret,same_owner_local_call=True))
 assert len(local_calls)==4
 atlas=read('analysis/phase18/control/instruction-atlas.json')['instructions'];by={(r['physical_bank'],r['cpu']):r for r in atlas}
 ranges=((31,0xE18B,0xE1BA),(8,0xA003,0xA006),(8,0xB130,0xB1B0),(8,0xB25A,0xB26A),(8,0xB2AE,0xB371),(31,0xF266,0xF26D))
 raw=[]
 for row in atlas:
  if any(row['physical_bank']==bank and start<=row['cpu']<stop for bank,start,stop in ranges):
   off=original(row['physical_bank'],row['cpu']);data=bytes.fromhex(row['raw_hex']);assert off==row['rom_offset']and rom[off:off+len(data)]==data;raw.append({k:row[k]for k in('physical_bank','cpu','rom_offset','op','mode','operand','raw_hex')})
 assert rom[original(8,0xA003):original(8,0xA006)]==bytes.fromhex('4C30B1')
 assert rom[original(31,0xE1B2):original(31,0xE1BA)]==bytes.fromhex('A0282037F22003A0')
 assert all(by[8,pc]['operand']==0xB1B0 for pc in(0xB16B,0xB195))
 assert by[8,0xB25D]['operand']==0xB2AE and by[8,0xB263]['operand']==0xB312
 for pc in ACCESS_PC:assert by[8,pc]['raw_hex'].replace(' ','').upper()=='B120'
 gates=[dict(side_base=0,packed_ruler_source='0507 low nibble',controller_pointer_call_PC=0xB150,controller_byte_offset=3,required_raw_controller_value=3,comparison_PC=0xB159,sort_call_PC=0xB163,deployment_call_PC=0xB16B,normal_return_PC=0xB16E),dict(side_base=10,packed_ruler_source='0507 high nibble',controller_pointer_call_PC=0xB178,controller_byte_offset=3,required_raw_controller_value=3,comparison_PC=0xB181,sort_call_PC=0xB18D,deployment_call_PC=0xB195,normal_return_PC=0xB198)]
 old=read('analysis/phase11/setup-ai/validation.json');old_init=read('analysis/phase11/initialization/validation.json');compare=read('analysis/phase25/fields-static/selection-comparison.json')
 root_samples=[dict(json_pointer='/samples/'+str(i),record=row)for i,row in enumerate(old_init['samples'])if row.get('entry')==0xE18B]
 selected=[r for r in read('analysis/phase25/fields-static/all-indirect-accesses.json')['accesses']if r['physical_bank']==8 and r['cpu']in ACCESS_PC]
 assert len(selected)==4 and all(r['classification']=='unresolved_pointer_or_index_contract'for r in selected)
 chain=dict(schema='phase26-focused-G107-existing-parent-and-owner-v1',status='read_only_existing_evidence',ROM_sha256=ROM_SHA,frontdoor25='AppearancePointerGameEngine / AppearancePointerSceneCoordinator',frontdoor26='DeploymentPointerGameEngine / DeploymentPointerSceneCoordinator',owners=owners,local_calls=local_calls,
  original_parent_chain=['fixed31:E18B','0500!=11 branch','fixed31:E1B2 LDY#28 (decimal40)','fixed31:E1B4 JSR F237','pair8/9;fixed31:E1B7 JSR8:A003','8:A003 JMP B130','controller byte3==3 per side','8:B16B or B195 JSR B1B0','8:B25D→B2AE or B263→B312','8:B272/B278/B290/B296 coordinate reads'],
  parent_branch=dict(battle_main_byte=0x0500,excluded_value=11,excluded_path='fixedE1A9 selector2C→pair12/13,E1AC A006 duel-outcome route; does not enter8A003 here',selector_decimal=40,selector_hex='28',setup_terminal_PC=0xE066,setup_terminal_kind='main_loop_boundary_not_caller_RTS'),
  per_side_controller_gates=gates,current_method_definitions=[dict(entry=entry,method=name,path=current.method('DeploymentPointerServices',name)[0],line=current.method('DeploymentPointerServices',name)[1].lineno,inherited_from_frozen_setup=current.method('DeploymentPointerServices',name)[0]=='source/recovered/battle_setup_ai.py')for entry,name in helper_names.items()],coordinate_reads=selected,raw_original_positions=sorted(raw,key=lambda r:(r['physical_bank'],r['cpu'])),
  entry_evidence=[dict(origin='existing_zero_preparation_Native_saved_context',path='analysis/phase11/runtime/cold-battle/supply-third.state',role='Recommended ordinary A continuation before fresh global battle setup; new26 passive entry capture is separate and not yet claimed here.'),dict(origin='actual_Native_snapshot_originalCPU_reached_caller_probe',path='analysis/phase25/fields-static/selection-comparison.json',json_pointer='/independent_original_CPU_probe/G107',record=compare['independent_original_CPU_probe']['G107'],role='Bounded no-interrupt negative at a possibly post-setup save; cannot infer G107 unreachability or a natural failed initialization.')],
  existing_Source_credit=dict(path='source/recovered/battle_setup_ai.py',methods={hex(k):v for k,v in helper_names.items()},first_named_phase=11,new_phase26_first_recovery_claim=False,old_total_instruction_positions=799,old_total_local_procedures=19,scope='799/19 describe the old full setup/NMI-aux module, not a new G107 denominator.'),
  old_full_setup_E18B_samples=root_samples,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)
 save('owner-and-caller-chain.json',chain)
 save('completion-contracts.json',dict(schema='phase26-G107-completion-classification-v1',normal_caller_RTS=dict(status='returned',required=['Actual current ServiceCall owner','Actual PC equals call.return_pc','Actual SP equals call.expected_sp','No seeded/fabricated caller frame'],scope='The source coordinator checks status and both PC/SP; standalone historical fixture defaults are not a Native protocol.'),
  not_normal_RTS=[dict(kind='dependency_or_waiting',meaning='Missing/unfinished explicit service or actual software/hardware input; keep pending. A changedPC/SP alone never authorizes continuation.'),dict(kind='strict_prefix',meaning='Only the declared same-prefix scope is proved. Original loops/budgets/unknown input remain explicit.'),dict(kind='nonlocal_return',meaning='Original control returned beyond the current caller or to another boundary; not an ordinary callee RTS.'),dict(kind='main_E066_boundary',meaning='Global E18B completes atE066, not via caller RTS; nested B1B0/B2AE/B312 can separately return normally.'),dict(kind='reset_boundary',meaning='Retire old owners through explicit reset protocol; not completion of a suspended G107 caller.')],
  mapper_contract=dict(first_side_selectors=[dict(raw_hex='30',decimal=48,physical_data_bank=16,call_PC=0xB2B0),dict(raw_hex='31',decimal=49,physical_data_bank=17,call_PC=0xB2D1,guard='Adjacency match branch only'),dict(raw_hex='26',decimal=38,physical_data_bank=6,call_PC=0xB2E6)],second_side_selectors=[dict(raw_hex='30',decimal=48,physical_data_bank=16,call_PC=0xB314),dict(raw_hex='26',decimal=38,physical_data_bank=6,call_PC=0xB345)],scope='Actual entry/read mapping still needs independent capture or exact complete original-call contract; no frame-end or general8000 assumption.'),
  raw_boundaries=['rawcity/ruler/profile/group byte domains must remain explicit; do not infer0..29/0..6/0..9 solely from field names.','No ordinal search-sentinel assumption can manufacture a total termination proof for malformed raw data.','Empty army count wraps; sparse lists/profile nibble aliasing are separate controlled inputs.','Logical coordinate reads and any6502 dummy bus reads are separate.','Historical11/25 prose says36 bytes for side2; original shifts/add use34*index modulo256, not36. No oldfile changed and no new-algorithm credit.']))
 budget=dict(schema='phase26-G107-stable-evidence-denominators-v1',context_new_CPU_cases=0,context_new_Native_runs=0,context_new_Source_cases=0,
  static_target_denominator=dict(trusted_indirect_positions=1526,baseline_disjoint=1187,baseline_possible=81,baseline_unknown=258,baseline_remaining=339,selected_group='G107',selected_accesses=4,selected_access_PC=list(ACCESS_PC),new_exclusion_count=None),
  Source_credit=dict(existing_named_entry_count=3,existing_methods=list(helper_names.values()),phase26_new_or_refactored_body_positions=None,phase26_raw_bytes=None,scope='Newly named/refactored helper scope must be independently measured. No first-recovery credit for the existing entire799-position module.'),
  existing_old_setup_validation=dict(path='analysis/phase11/setup-ai/validation.json',old_CPU_cases=old['rom_cpu_case_count'],old_source_guards=old['source_guard_case_count'],declared_RAM_bytes=old['compared_RAM_bytes'],declared_SRAM_bytes=old['all_SRAM_compared_bytes'],free_stack_scope='Old free-stack exclusion retained; new full2048 scopes must not retroactively relabel old cases.'),
  new_case_classes=['Source exact caller RTS','Source nonlocal or main-loop boundary','Source strict dependency prefix','Standalone originalCPU contract/prefix','Model guards','Original-core Native route/control frames','Passive observer event/snapshot provenance','Byte-identical ROM reconstruction'],
  forbidden_combination='Do not sum tests/positions/frames or byte identity into a completion percentage; nested helper calls are not extra parentcases.')
 save('stable-denominators.json',budget)
 save('historical-wording-erratum.json',dict(schema='phase26-historical-side2-stride-wording-erratum-v1',corrected_field='second_side_template_offset',first_side_formula='(32*rawtemplate)&255',second_side_formula='(34*rawtemplate)&255',mechanical_derivation='Four8bit ASL:16*t; CLC/ADC original t:17*t; ASL:34*t, preserving rawbyte wrap. Later coordinate-base addition is a separate16bit operation.',historical_prose_value=36,old_files_changed=False,new_algorithm_recovery_claim=False,source_path='source/recovered/battle_setup_ai.py',source_method='second_side_formation',scope='This corrects new explanations of the original arithmetic; it does not promise arbitrary raw template or city validity.'))
 dims=[]
 for d in read('analysis/phase25/acceptance/requirements.json')['dimensions']:
  dims.append(dict(id=d['id'],title=d['title'],inherited_status=d['acceptance_status'],phase26_context_verified_result={'A01':'Frozen25 Source/ROM references pinned; no byte-rebuild run in this audit.','A02':'G107 does not yet give city+1/tail official names.','A03':'Four target positions and complete parent/owner evidence separated from new dynamic coverage.','A04':'Existing owner and named methods identified; refactoring/protocol deltas get separate credit.','A05':'No standalone remake or high-level-source NES build claimed.','A06':'RTS, waits, strictprefix, nonlocal andE066 boundary have separate completion contracts.','A07':'Mapper/data-bank evidence must be immediate; hardware rendering still original core.','A08':'Natural saved-context route recommendation is separate from bounded CPU reachability and forthcoming passive captures.','A09':'Read-only new output/pins; no historical producer rerun.','A10':'No unknown-field or whole-game completion percentage inferred.'}[d['id']],future_new_evidence_required='Root will attach final phase26 Source/Native/static receipts and its actual outcome; this framework is not a prewritten pass.',new_phase26_completion_claim=None))
 save('acceptance-delta-framework.json',dict(schema='phase26-G107-ten-dimension-context-delta-framework-v1',dimensions=dims,context_Source_CPU_cases=0,context_original_CPU_cases=0,context_Native_runs=0,phase26_final_results_not_asserted=True))
 overlaps=[]
 public=current.attr('DeploymentPointerServices','PUBLIC_ENTRIES');assert set(public)=={0xA003,0xB130,0xB1B0,0xB2AE,0xB312}
 for cls,attr in(('TacticalCooperationController','LOCAL_ENTRIES'),('CityActionBridges','SHOP_ENTRIES'),('RulerSelectionUIController','PUBLIC_ENTRIES')):
  entries=current.attr(cls,attr);assert entries is not index.MISSING;hits=sorted(set(public)&set(entries));assert not hits;overlaps.append(dict(other_class=cls,entry_attribute=attr,intersection=hits))
 save('owner-priority-checks.json',dict(schema='phase26-exact-deployment-owner-overlap-v1',entry_pair=[8,9],new_PUBLIC_ENTRIES=sorted(public),comparisons=overlaps,scope='Only these declared same-pair entry sets. Empty intersections are not a whole-program closure proof.'))
 inputs={path:sha(ROOT/path)for path in INPUTS};sources={path:sha(ROOT/path)for path in SOURCES}
 summary=dict(schema='phase26-focused-G107-context-summary-v1',status='indexed_read_only',ROM_sha256=ROM_SHA,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,unknown_unique_services=None,focused_group='G107',target_access_count=4,phase25_owner='BattleSetupAI',current26_owner='DeploymentPointerServices',frontdoor25='AppearancePointerSceneCoordinator',frontdoor26='DeploymentPointerSceneCoordinator',old_Source_first_named_phase=11,
  owner_entry_addresses=[0xB1B0,0xB2AE,0xB312],baseline_remaining_candidates=339,new_exclusions_from_this_context_audit=0,natural_opcode_entry_capture_claim=False,source_and_validator_sha256={'scripts/analyze_deployment_context_phase26.py':sha(__file__),**sources},artifact_and_dependency_sha256=inputs,
  limitations=['Focused current route/caller/static byte audit only; no global syntax missing-service total.','Existing old Source coverage, new refactoring scope, independent originalCPU contracts and Native routes are separate.','Actual side selection and complete mapper/pointer lifetime require newly frozen26 evidence; this context audit does not pregrant them.'])
 save('analysis-summary.json',summary)
 (OUT/'README.md').write_text('''# G107：父入口、当前owner与完成边界

本目录是只读上下文核查，新Source病例、原CPU病例、Native运行数均为0。冻结25前门AppearancePointerGameEngine/Coordinator对8/9继续路由到BattleSetupAI；新26前门DeploymentPointerGameEngine/Coordinator只接管A003/B130/B1B0/B2AE/B312五个入口，由DeploymentPointerServices负责，继承25其它owner。此处是静态路由核查，不预先声明新Source执行已通过。B1B0、B2AE、B312已分别是assign_strategies_and_positions、first_side_formation、second_side_formation；后两者是父owner内的局部JSR，不能算新发现的三个缺失服务。

原全局链为E18B→0500!=11→LDY#28(十进制40)/F237→physical8/9的A003→B130→每侧ruler记录byte3==3门→B16B/B195调B1B0→B25D/B263调B2AE/B312。0500==11走12A006单挑后果分支，不能把所有E18B完成都视为G107命中。E18B最终到E066主循环边界，不是普通caller RTS。

现有自然supply-third母状态是普通A续行的合理起点；旧handoff-011的300000指令无中断CPU负probe可能已在初始化之后，只能说该保存点/预算未再命中，不能证明G107不可达。Native保存点后独立CPU续行不是固定原核内部捕获；新26被动opcode捕获和设备夹具仍须由自己的回执说明。

更正仅在本轮说明：冻结11README/25comparison所写第二侧36B不符原算式。原代码四次ASL得到16×，加原index得17×，再ASL得34×；offset保留8位回绕。第一侧五次ASL是32×。这是旧文档的更正，不是新算法发现，不修改旧文件。

稳定静态分母是G107四处B272/B278/B290/B296，归于全部1526项；25基线1187不交/81可能/258未知，剩339。上下文审计本身新增排除0，不预写26最终数。旧799位置/19过程是整个setup/NMI辅助模块，不能重计为26首次恢复；旧2326CPU/1972RAM及自由栈排除保持历史范围。新Source若改为全2048真实caller比较，是新增协议/范围证据，应另列。

normal RTS必须有真实caller、statusreturned与真实PC/SP同时匹配。waiting/dependency保持pending、strictprefix只证明前缀；nonlocal、reset和globalE066边界单列。不能人工ack、伪造栈，或把外层frameend银行当即时ROM坐标读银行。第一侧32×与第二侧34×(均按原8位offset算式)模板、rawbyte和裸alias域保持区分；不凭有限负观测给城市+1/+28..31命名。

owner-and-caller-chain.json保留原字节与含16B头偏移、真实局部JSR关系、旧证据定位；completion-contracts.json列mapper/caller前提；stable-denominators.json与acceptance-delta-framework.json给十维收口框架。新26 Source、Native和Root整合仍由各自回执验收，本目录不运行它们。
''',encoding='utf-8')
 print(json.dumps(dict(status='indexed_read_only',current_owner='DeploymentPointerServices',target_accesses=4,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)))
if __name__=='__main__':main()
