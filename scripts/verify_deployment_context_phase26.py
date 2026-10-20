#!/usr/bin/env python3
"""Check the new focused context index, without CPU/core or Source execution."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,ast
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase26/context'
s=importlib.util.spec_from_file_location('phase26_context',ROOT/'scripts/analyze_deployment_context_phase26.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom');args=p.parse_args();rom=Path(args.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==m.ROM_SHA
 summary=read('analysis-summary.json');checks=[]
 def check(name,truth):assert truth,name;checks.append(dict(test=name,status='passed'))
 for key in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for path,h in summary[key].items():assert not any(x.startswith('exploratory')for x in Path(path).parts)and sha(ROOT/path)==h,path
 check('focused Source/current factory and frozen inputs all current; no exploratory dependencies',True)
 contract=read('owner-and-caller-chain.json');raw=contract['raw_original_positions']
 for row in raw:
  offset=m.original(row['physical_bank'],row['cpu']);values=bytes.fromhex(row['raw_hex']);assert offset==row['rom_offset']and rom[offset:offset+len(values)]==values
 check('all focused original instructions byteexact including16B header',bool(raw))
 for owner in contract['owners']:
  assert owner['phase25_route']['owners']==['BattleSetupAI']and owner['current26_route']['owners']==['DeploymentPointerServices']
 check('old25 owner and new exact26 owner are distinct declaration evidence',len(contract['owners'])==5)
 definitions={r['entry']:r for r in contract['current_method_definitions']}
 check('B1B0 existing named behavior inherited; two formation methods are new readable refactors',definitions[0xB1B0]['inherited_from_frozen_setup']and not definitions[0xB2AE]['inherited_from_frozen_setup']and not definitions[0xB312]['inherited_from_frozen_setup'])
 local={r['JSR_call_PC']:r for r in contract['local_calls']}
 check('actual local JSReturns preserve same-owner parent edges',set(local)=={0xB16B,0xB195,0xB25D,0xB263}and all(r['raw_return_word']+1==r['normal_return_PC']for r in local.values()))
 check('E18B excludes battle_main11 from this path;selector40decimal is28hex',contract['parent_branch']['excluded_value']==11 and contract['parent_branch']['selector_decimal']==40 and contract['parent_branch']['selector_hex']=='28')
 check('globalE18B end is mainE066 rather than ordinary RTS',contract['parent_branch']['setup_terminal_PC']==0xE066 and contract['parent_branch']['setup_terminal_kind']=='main_loop_boundary_not_caller_RTS')
 check('each side requires exact raw controller3 and retains original side-base',[(r['side_base'],r['required_raw_controller_value'])for r in contract['per_side_controller_gates']]==[(0,3),(10,3)])
 check('four original reads retained unknown at25 baseline; context creates no exclusions',len(contract['coordinate_reads'])==4 and all(r['classification']=='unresolved_pointer_or_index_contract'for r in contract['coordinate_reads'])and summary['new_exclusions_from_this_context_audit']==0)
 overlaps=read('owner-priority-checks.json');check('exact new5 public entries have no declared Tactical/Shop/Ruler entry intersection',len(overlaps['new_PUBLIC_ENTRIES'])==5 and all(not r['intersection']for r in overlaps['comparisons']))
 budget=read('stable-denominators.json');old=budget['existing_old_setup_validation']
 check('old2326CPU/1972RAM8192SRAM scope preserved as old evidence',old['old_CPU_cases']==2326 and old['declared_RAM_bytes']==1972 and old['declared_SRAM_bytes']==8192)
 dims=read('acceptance-delta-framework.json');check('all10 inherited acceptance dimensions retained without future pass',set(r['id']for r in dims['dimensions'])=={f'A{i:02d}'for i in range(1,11)}and dims['phase26_final_results_not_asserted'])
 completion=read('completion-contracts.json');check('wait prefix nonlocal reset andE066 boundary never merged with callerRTS',set(r['kind']for r in completion['not_normal_RTS'])=={'dependency_or_waiting','strict_prefix','nonlocal_return','main_E066_boundary','reset_boundary'})
 check('no new CPU Source or Native case from this read-only context',summary['Source_CPU_cases']==summary['original_CPU_cases']==summary['Native_runs']==0 and summary['natural_opcode_entry_capture_claim']is False)
 for path in('scripts/analyze_deployment_context_phase26.py','scripts/verify_deployment_context_phase26.py'):
  tree=ast.parse((ROOT/path).read_text())
  for n in ast.walk(tree):
   if isinstance(n,(ast.Import,ast.ImportFrom)):
    text=ast.unparse(n);assert not any(x in text for x in('py65','nes_runtime','source.recovered'))
   if isinstance(n,ast.Call)and isinstance(n.func,ast.Name):assert n.func.id not in('eval','exec','__import__')
 check('new scripts have no production Source/CPU/core import or evaluator execution',True)
 source=summary['source_and_validator_sha256']|{'scripts/verify_deployment_context_phase26.py':sha(__file__)}
 artifacts=summary['artifact_and_dependency_sha256']|{str(q.relative_to(ROOT)):sha(q)for q in sorted(OUT.glob('*'))if q.is_file()and q.name not in('verification.json','evidence.json')}
 result=dict(schema='phase26-focused-context-readonly-validation-v1',status='passed',ROM_sha256=m.ROM_SHA,Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,check_count=len(checks),checks=checks,original_byte_positions_verified=len(raw),source_and_validator_sha256=source,artifact_and_dependency_sha256=artifacts,scope='Read-only owner/caller/byte/pin audit; not fresh gameplay or new Source differential validation.')
 m.save('verification.json',result);m.save('evidence.json',dict(schema='phase26-focused-context-readonly-evidence-v1',status='passed',Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,analyzer_path='scripts/analyze_deployment_context_phase26.py',validator_path='scripts/verify_deployment_context_phase26.py',check_count=len(checks),source_and_validator_sha256=source,artifact_and_dependency_sha256=artifacts|{'analysis/phase26/context/verification.json':sha(OUT/'verification.json')}))
 print(json.dumps(dict(status='passed',checks=len(checks),Source_CPU_cases=0,original_CPU_cases=0,Native_runs=0)))
if __name__=='__main__':main()
