#!/usr/bin/env python3
"""Read-only G106 caller/owner/meaning audit; write only new phase27/context.

No recovered module, CPU, core or historical producer is executed. The route
model is the frozen25 finite AST reader, applied to the exact frozen26 Source.
"""
from pathlib import Path
import argparse, ast, hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis/phase27/context'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
TARGETS = (0xBF74,0xBFA0,0xBFA6,0xBFDF,0xBFE9,0xBFEC,0xBFF2)
INPUTS = ('scripts/analyze_service_gaps_phase25.py','analysis/phase26/verification.json','analysis/phase26/fields-static/analysis-summary.json','analysis/phase26/fields-static/all-indirect-accesses.json','analysis/phase26/acceptance/requirements.json','analysis/phase25/services/verification.json','analysis/phase25/services/owner-route-catalog.json','analysis/phase18/control/instruction-atlas.json','analysis/battle_fsm/state-catalog.json','analysis/battle_fsm/validation.json','analysis/battle_fsm/README.md','analysis/phase5/domestic-ai/city-schema.json')
SOURCES = ('source/recovered/deployment_pointer_integration.py','source/recovered/deployment_pointer_services.py','source/recovered/scene_coordinator.py','source/recovered/battle_setup_ai.py','source/recovered/battle_scene_controller.py','source/recovered/tactical_cooperation_controller.py','source/recovered/battle_state_machine.py','source/recovered/game_engine.py','source/recovered/scene_shared_services.py','source/recovered/postbattle_resource_services.py','source/recovered/postbattle_resource_integration.py')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads((ROOT/p).read_text())
def save(name,d): OUT.mkdir(parents=True,exist_ok=True); (OUT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def offset(bank,cpu): return 16+8192*bank+(cpu&8191)
def node(path,name):
    tree=ast.parse((ROOT/path).read_text())
    return next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');a=p.parse_args();rom=Path(a.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
    baseline=read('analysis/phase26/verification.json');assert baseline['status']=='passed'
    paths=sorted(x for x in baseline['source_and_validator_sha256'] if x.startswith('source/recovered/'))
    for path in paths: assert sha(ROOT/path)==baseline['source_and_validator_sha256'][path],path
    spec=importlib.util.spec_from_file_location('frozen25_route_reader',ROOT/'scripts/analyze_service_gaps_phase25.py');idx=importlib.util.module_from_spec(spec);spec.loader.exec_module(idx)
    registry=idx.Registry(paths,'DeploymentPointerSceneCoordinator')
    entries=(0xA006,0xBAB3,0xBB93,0xBF0A,0xBF9E,0xBFB3,0xBFEC)
    routes=[dict(physical_pair=[8,9],target=x,target_hex=f'{x:04X}',route=registry.resolve(x,[None,8,9,31])) for x in entries]
    assert all(not x['route']['owners'] for x in routes)
    assert not set(entries)&set(registry.attr('TacticalCooperationController','LOCAL_ENTRIES'))
    assert not set(entries)&set(registry.attr('DeploymentPointerServices','PUBLIC_ENTRIES'))
    current=idx.Registry(paths+list(SOURCES[-2:]),'PostbattleResourceSceneCoordinator')
    new_entries=set(current.attr('PostbattleResourceServices','NEW_ENTRIES'));assert new_entries=={0xBF0A,0xBF9E,0xBFB3,0xBFEC}
    current_rows=[dict(physical_pair=[8,9],target=x,target_hex=f'{x:04X}',route=current.resolve(x,[None,8,9,31]))for x in entries]
    assert all(r['route']['owners']==(['PostbattleResourceServices']if r['target']in new_entries else[])for r in current_rows)
    deployment_rows=[dict(target=x,target_hex=f'{x:04X}',route=current.resolve(x,[None,8,9,31]))for x in(0xA003,0xB130,0xB1B0,0xB2AE,0xB312)]
    assert all(r['route']['owners']==['DeploymentPointerServices']for r in deployment_rows)
    assert not new_entries&set(current.attr('TacticalCooperationController','LOCAL_ENTRIES'))
    save('current27-owner-scope.json',dict(schema='phase27-G106-additive-owner-boundaries-v1',frontdoor='PostbattleResourceGameEngine / PostbattleResourceSceneCoordinator',NEW_ENTRIES=sorted(new_entries),routes=current_rows,frozen_deployment_owner_retained=deployment_rows,parent_A006_BAB3_BB93_unowned_in_bounded_model=True,parent_completion_claim=False,current_source_actual_execution_claim=False,scope='Static exact-pair/entry routing only. Four new callees do not close A006/BAB3/realECEE or prove a complete parent battle. New Source CPU receipts and Native routes are independent.',completion_rule='returned status plus actual PC/SP; pending dependency is not a return; nonlocal terminal reply preserves original caller identity; reset retires old caller owners.',Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0))
    atlas=read('analysis/phase18/control/instruction-atlas.json')['instructions'];by={(r['physical_bank'],r['cpu']):r for r in atlas}
    windows=((8,0xA006,0xA009),(8,0xBAB3,0xBBB8),(8,0xBF0A,0xC000),(9,0xC000,0xC015),(13,0xD4F0,0xD4FB),(31,0xF25F,0xF266),(31,0xF2AF,0xF2D7))
    raw=[]
    for r in sorted(atlas,key=lambda r:(r['physical_bank'],r['cpu'])):
        if any(r['physical_bank']==b and start<=r['cpu']<end for b,start,end in windows):
            o=offset(r['physical_bank'],r['cpu']);b=bytes.fromhex(r['raw_hex']);assert r['rom_offset']==o and rom[o:o+len(b)]==b
            raw.append({k:r[k]for k in ('physical_bank','cpu','rom_offset','op','mode','operand','raw_hex')})
    assert rom[offset(8,0xA006):offset(8,0xA009)]==bytes.fromhex('4C B3 BA')
    assert rom[offset(8,0xBB93):offset(8,0xBB9F)]==bytes.fromhex('20 EE EC 20 0A BF 20 27 C0 EE 01 05')
    assert rom[offset(13,0xD4F3):offset(13,0xD4FA)]==bytes.fromhex('A0 28 20 07 EE 06 A0')
    table=rom[offset(8,0xBAB9):offset(8,0xBAC1)];assert table==bytes.fromhex('C1 BA 3D BB 93 BB A0 BB')
    for pc in TARGETS: assert by[8,pc]['operand']==0x1A
    edges=[]
    for pc,callee,kind,return_pc,y in ((0xBB96,0xBF0A,'JSR',0xBB99,None),(0xBF34,0xBF9E,'JSR',0xBF37,6),(0xBF5E,0xBF9E,'JSR',0xBF61,8),(0xBF69,0xBF9E,'JSR',0xBF6C,14),(0xBF8E,0xBF9E,'JSR',0xBF91,2),(0xBF9B,0xBF9E,'tail_JMP',None,4),(0xBF81,0xBFB3,'JSR',0xBF84,11),(0xBF86,0xBFEC,'JSR',0xBF89,2),(0xBF93,0xBFEC,'JSR',0xBF96,4)):
        r=by[8,pc];assert r['operand']==callee and r['op']==('JMP'if kind=='tail_JMP'else'JSR')
        edges.append(dict(physical_bank=8,call_PC=pc,callee=callee,kind=kind,raw_return_word=pc+2 if kind=='JSR'else None,normal_return_PC=return_pc,Y_at_complete_BF0A_call=y,original=r))
    save('owner-and-caller-chain.json',dict(schema='phase27-G106-frozen26-owner-and-parent-v1',status='read_only_existing_evidence',ROM_sha256=ROM_SHA,frozen_frontdoor='DeploymentPointerGameEngine / DeploymentPointerSceneCoordinator',owner_routes=routes,actual_parent_chain=['battle12/13 state15 D4F0 return_to_city','13:D4F3 LDY#28; D4F5 EE07 inline A006','physical8:A006 JMP BAB3','0501 dispatcher4: BAC1/BB3D/BB93/BBA0','sub2 BB93 ECEE real render barrier','BB96 JSR BF0A','0514==0 resource branch; other values BF0F RTS'],dispatcher=dict(state_byte=0x0501,table_CPU=0xBAB9,count=4,raw_hex=table.hex(' ').upper(),targets=[0xBAC1,0xBB3D,0xBB93,0xBBA0],raw_substate_outside0_3_not_claimed=True),local_calls=edges,original_positions=raw,static_owner_limit='No declared exact owner in this bounded frozen26 route model, not a whole-program missing-service count. A semantic convenience method is not a ServiceCall CPU owner.',Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0))
    pointer_copy=rom[offset(8,0xBF15):offset(8,0xBF27)];assert pointer_copy==bytes.fromhex('AD 0E 05 20 AF F2 AD 00 00 8D 1A 00 AD 01 00 8D 1B 00')
    schema=read('analysis/phase5/domestic-ai/city-schema.json');fields={f['offset']:f for f in schema['fields']}
    semantics=[]
    for field,size,rate,reads,writes in ((6,2,'(E87A_draw&1)+1',[0xBFA0,0xBFA6],[0xBFDF,0xBFE9]),(8,2,'turn_rate',[0xBFA0,0xBFA6],[0xBFDF,0xBFE9]),(14,2,'turn_rate',[0xBFA0,0xBFA6],[0xBFDF,0xBFE9]),(11,1,'turn_rate',[0xBF74],[0xBFDF]),(2,2,'value>501 ? 5 : 9',[0xBFEC,0xBFF2,0xBFA0,0xBFA6],[0xBFDF,0xBFE9]),(4,2,'value>501 ? 5 : 9',[0xBFEC,0xBFF2,0xBFA0,0xBFA6],[0xBFDF,0xBFE9])):
        semantics.append(dict(city_offset=field,size=size,established_field_name=fields[field]['name'],established_UI_label=fields[field]['label'],field_name_source='analysis/phase5/domestic-ai/city-schema.json',rate=rate,read_PC=reads,write_PC=writes,formula='floor(((old*(10-rate))&0xFFFF)/10); byte11 writes only quotient low8'))
    per_site={0xBF74:[11],0xBFA0:[2,4,6,8,14],0xBFA6:[3,5,7,9,15],0xBFDF:[2,4,6,8,11,14],0xBFE9:[3,5,7,9,15],0xBFEC:[2,4],0xBFF2:[3,5]}
    contracts=[]
    for pc,ys in per_site.items():
        words=[0x6000+32*i for i in range(256)];addresses=sorted({(w+y)&65535 for w in words for y in ys});aux={0x6000+32*i+y for i in range(30)for y in (1,28,29,30,31)}
        assert not set(addresses)&aux
        contracts.append(dict(physical_bank=8,cpu=pc,raw_hex=by[8,pc]['raw_hex'],pointer_zero_page=0x1A,complete_caller_Y_values=ys,complete_caller_whole_pointer_values=words,calculated_logical_address_intersection=[],candidate_only_not_new_static_authority=True,required_scope='Complete BF0A 0514==0 path, intact real stack/pointer, no intervening interrupt/external write, complete exact helper return; bare suffix does not inherit this contract.'))
    data=[]
    for bank,pc,count,label in ((9,0xC015,5,'turn_rate'),(9,0xC01A,8,'ascending_threshold_words'),(9,0xC022,5,'threshold_rate')):
        b=rom[offset(bank,pc):offset(bank,pc)+count];data.append(dict(physical_bank=bank,cpu=pc,rom_offset=offset(bank,pc),raw_hex=b.hex(' ').upper(),label=label))
    save('pointer-and-field-context.json',dict(schema='phase27-G106-pointer-field-context-v1',pointer_factory=dict(entry=0xF2AF,input='raw city byte from050E',output='00/01=6000+32*rawcity; raw0..255 retained, not all legal cities',copy_to='1A/1B atBF1E/BF24',original_copy=dict(physical_bank=8,cpu=0xBF15,rom_offset=offset(8,0xBF15),raw_hex=pointer_copy.hex(' ').upper())),mapper=dict(call=0xBF12,target=0xF25F,raw_selector_hex='30',raw_selector_decimal=48,physical_data_bank=16,fixed_save_byte=0xE1,scope='F25F savesE1, notF266/DE; banked8/9 code remains unchanged. Immediate capture is needed for actual Native read mapping.'),authoritative_static_classification_unchanged=True,complete_caller_candidate_contracts=contracts,semantics=semantics,immutable_data_tables=data,writer_lifetime=dict(save_Y='BF9E TYA/PHA for words; BFB3 TYA/PHA for byte11',math_calls=[dict(cpu=0xBFBE,target=0xEBE9),dict(cpu=0xBFD7,target=0xEA7C)],restore='BFDA PLA / BFDB TAY',low_store=0xBFDF,skip_high_if_Y11=True,high_store=0xBFE9,bare_raw_Y_not_bounded=True,scope='A valid complete caller and non-aliased/intact hardware stack are hypotheses, not facts for a bare suffix or arbitraryZP fixture.'),competing_meanings=[dict(name='dedicated city+1/tail consumer',result='No such formal meaning follows from the complete caller offsets2..15. Bare1A/Y aliases remain independent counterexamples.'),dict(name='town resource loss',result='Already directly recovered named semantics and old512 SRAM cases; exact CPU caller/mapper/stack protocol may be a new scope.'),dict(name='arbitrary pointer write helper',result='True only for unconstrained barehelper input; not proof that a natural BF0A caller intentionally uses aux fields.')],logical_vs_dummy='Contract candidates describe logicalEA. STA IndY always performs an uncarried dummy read; LDA does so only on pagecross. A bus hit must be decoded separately.',Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0))
    old=read('analysis/battle_fsm/validation.json');assert old['status']=='passed' and old['semantic_counts']['postbattle_city_losses']==512
    funcs=[]
    for path,name in (('source/recovered/battle_state_machine.py','postbattle_city_losses'),('source/recovered/battle_state_machine.py','finalization_phase'),('source/recovered/game_engine.py','settlement_rules'),('source/recovered/battle_scene_controller.py','return_to_city')):
        n=node(path,name);funcs.append(dict(path=path,function=name,start_line=n.lineno,end_line=n.end_lineno))
    save('semantic-deduplication.json',dict(schema='phase27-G106-existing-semantic-credit-v1',functions=funcs,old_SRAM_effect_case_count=512,old_finalization_case_count=old['semantic_counts']['finalization_phase'],old_receipt='analysis/battle_fsm/validation.json',old_scope=old['scope'],new_CPU_case_count=0,new_Source_case_count=0,first_recovery_of_old_algorithm_claim=False,scope='Old semantic effects did not claim AXYP/SP/PC/free stack/orderedIO equivalence. ECEE was explicitly bypassed on both old CPU sides; do not label that natural hardware readiness.'))
    base=read('analysis/phase26/fields-static/analysis-summary.json');assert base['all_indirect_classification_counts']=={'proved_disjoint_auxiliary_address_domain':1191,'possible_city_auxiliary_alias':81,'unresolved_pointer_or_index_contract':254}
    prior=read('analysis/phase26/fields-static/all-indirect-accesses.json')['accesses'];selected=[r for r in prior if r['physical_bank']==8 and r['cpu']in TARGETS];assert len(selected)==7 and all(r['classification']=='unresolved_pointer_or_index_contract'for r in selected)
    dims=read('analysis/phase26/acceptance/requirements.json')['dimensions']
    save('stable-denominators-and-acceptance.json',dict(schema='phase27-G106-stable-denominators-v1',all_indirect_positions=1526,frozen26_classification=base['all_indirect_classification_counts'],frozen26_remaining=335,selected_group='G106',selected_positions=list(TARGETS),selected_prior_records=selected,raw_window_ledger=dict(total=345,operand=104,known_data=13,no_proven_control_entry=228),new_context_exclusions=0,new_context_CPU_cases=0,new_context_Source_cases=0,new_context_Native_runs=0,official_city_auxiliary_names={str(o):None for o in (1,28,29,30,31)},unknown_unique_services=None,completion_percentage=None,dimensions=[dict(id=d['id'],title=d['title'],frozen26_status=d['acceptance_status_zh'],frozen26_status_is_not_phase27_summary=True,phase27_delta='Pending final independent Source/static/Native receipts; this context records existing evidence only.',new_phase27_acceptance_status=None)for d in dims],completion_contracts=['Normal callerRTS requires returned status plus realPC/SP matching the real call; never seed a stack.','Dependency/wait is pending, not completion. ECEE must advance via real service/hardware input.','Strictprefix has its declared stop/scope only.','BF9B JMP BF9E reuses an existing return frame, not a nestedJSR.','Nonlocal/reset/main-loop boundaries stay separate from ordinaryRTS.','0514!=0 skip is a valid no-effect path, not evidence of resource processing or RNG consumption.'],limits=['Stable1526 is not all instruction/microcycle coverage. No new control-entry, dynamic coverage, unavailable-service total or formalfield name follows from grouping.','No natural-entry capture claimed before a formal original/observer receipt.','Do not relabel existing algorithms or512 old SRAM effects as first recovery.']))
    lines=['; phase27 G106 original trusted instructions; all file offsets include16-byte iNES header']
    for r in raw:lines.append(f"; bank{r['physical_bank']:02d} file ${r['rom_offset']:06X}\n${r['cpu']:04X}: {r['raw_hex']:<9} ; {r['op']} {r['mode']} ${r['operand']:04X}")
    (OUT/'original-ranges.asm').write_text('\n'.join(lines)+'\n')
    summary=dict(schema='phase27-G106-focused-context-summary-v1',status='indexed_read_only',ROM_sha256=ROM_SHA,focused_group='G106',selected_access_count=7,frozen_frontdoor='DeploymentPointerGameEngine',current27_frontdoor='PostbattleResourceGameEngine',baseline_remaining_candidates=335,context_new_static_exclusions=0,exact_baseline_owner_found=False,current27_new_owned_entries=4,parent_A006_BAB3_BB93_owner_found=False,existing_named_semantics=True,new_Source_first_recovery_claim=False,natural_capture_claim=False,unknown_unique_services=None,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,source_and_validator_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__),**{p:sha(ROOT/p)for p in SOURCES}},artifact_and_dependency_sha256={p:sha(ROOT/p)for p in INPUTS},limits=['Readonly finite AST/originalbytes audit, not CPU/core execution.','New27 four-callee owner does not close the unresolved A006/BAB3/realECEE parent.','Complete-caller candidate address domains are not substituted for the frozen26 static authority.'])
    save('analysis-summary.json',summary)
    (OUT/'README.md').write_text('''# G106：入口、城市指针与既有语义

本目录只读核对冻结26的frontdoor、原字节与现有回执，新增Source/CPU/Native均0。DeploymentPointerGameEngine继承的有限AST路由对physical8/9 A006/BAB3/BB93/BF0A/BF9E/BFB3/BFEC未找到明确CPU owner；这不是全程序缺失服务数量。TacticalCooperationController与DeploymentPointerServices的明确入口都不含这些地址，不能把另一bank同地址或某个syntaxexternal当作已匹配owner。

新27前门PostbattleResourceGameEngine/SceneCoordinator只对BF0A/BF9E/BFB3/BFEC四入口接新PostbattleResourceServices，26部署五入口继续旧owner。A006/BAB3/BB93未被接入，所以直callee对照即使完整返回，也不能宣称其父控制、真实ECEE或整场战斗Source已闭合。此路由表仍是静态身份核查，执行scope以新Source和Root整合自己的回执为准。

真正父链为battle bank13 D4F0 return_to_city，D4F5以selector28(hex) farcall8:A006→BAB3，按0501四word表分派。仅sub2到BB93，先调用真实ECEE屏障，BB96才调用BF0A。0514非0在BF0F立即RTS，不能把该无效果分支当成真实资源扣减；0514==0才F25F raw30→physical16，然后F2AF(050E)将完整6000+32*rawcity指针复制到1A/1B。F25F保存E1，不能沿用F266保存DE的说法。

BF9E有四个JSR caller：BF34(Y6)、BF5E(Y8)、BF69(Y14)、BF8E(Y2)，另BF9B(Y4)是尾JMP，没有额外returnframe。BF81以Y11调用BFB3单字节路径。两类入口都将原Y压到真实栈，EBE9乘法和EA7C除法后BFDA/DB恢复，BFDF写低字节；Y11跳过高字节，否则BFE9写下一字节。完整BF0A候选offset集合仅2..15中的资源字段；裸helper、损坏栈、任意1A/Y不能继承这些前提。

资源效果并非首次发现：冻结battle_state_machine.postbattle_city_losses已直接实现BF0A..C026，旧512案只比较SRAM；finalization_phase旧256案的ECEE在两侧显式bypass。GameEngine.settlement_rules是高层接口，不等于farcaller的完整CPU寄存器/栈/mapperowner。新阶段若补精确protocol是新scope，不重算整个算法恢复。六种字段是人口+6、土地+8、产业+14、统治+11、金+2、米+4，标签引用既有城市UI字段证据，不为+1/+28..31补名。

乘法先丢弃超过16bit的乘积，再除10；不要泛称所有raw输入为普通百分比。人口rate=(draw&1)+1；turn0506的rate表是1/2/3/4/6；金米原升序阈值比较方向保留，value>501用5，<=501用9。C027随后回补军粮/金，原机瞬时读写与帧末净值需要分开解释。

稳定分母1526：冻结26为1191条件不交、81可能、254未知，剩335；G106七处仍保留旧权威分类。此处完整caller候选域只用于复查链路，非新增排除，不能凭投影或有限负观测宣布字段unused。raw345保留104操作数字节/13已有数据/228未证入口。逻辑EA与6502dummy总线读各自解释；自然入口、实际bank/PC、Source对照、模型guards和字节重建都由独立正式回执说明。
''')
    print(json.dumps({k:summary[k]for k in ('status','selected_access_count','exact_baseline_owner_found','existing_named_semantics','Source_CPU_cases','original_CPU_cases','Native_runs')}))
if __name__=='__main__':main()
