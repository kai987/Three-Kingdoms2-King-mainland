#!/usr/bin/env python3
"""Static/pin audit of the phase25 service index; zero CPU/core executions."""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase25/services'
spec=importlib.util.spec_from_file_location('phase25_readonly_service_index',ROOT/'scripts/analyze_service_gaps_phase25.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text())
def pointer(value,path):
 for part in path.strip('/').split('/')if path else[]:
  part=part.replace('~1','/').replace('~0','~');value=value[int(part)]if isinstance(value,list)else value[part]
 return value

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom');args=parser.parse_args();rom=Path(args.rom).read_bytes()
 summary=read('analysis-summary.json');assert summary['source_CPU_cases']==summary['original_CPU_cases']==summary['Native_runs']==0
 base=model.read(model.BASELINE);assert base['status']=='passed'and sha(ROOT/model.BASELINE)==summary['baseline_sha256']
 assert hashlib.sha256(rom).hexdigest()==base['ROM_sha256']
 checks=[]
 def check(name,truth):assert truth,name;checks.append(dict(test=name,status='passed'))
 for group in('source_and_validator_sha256','artifact_and_dependency_sha256'):
  for path,digest in summary[group].items():assert not any(x.startswith('exploratory')for x in Path(path).parts)and sha(ROOT/path)==digest,path
 check('all captured current source/receipt/atlas/acceptance pins current; no exploratory dependency',True)
 source_paths=[p for p in summary['source_and_validator_sha256']if p.startswith('source/recovered/')]
 for path in source_paths:
  if path in base['source_and_validator_sha256']:assert sha(ROOT/path)==base['source_and_validator_sha256'][path],path
 reg=model.Registry(source_paths,summary['frontdoor'])
 check('frozen phase24 source bytes preserved; only additional phase25 Source files separately indexed',len(source_paths)==summary['source_file_count'])
 check('EA7C arithmetic owner is declared current implementation',reg.resolve(0xEA7C,[2,27,28,31])['owners']==['IntegratedSceneInitialization'])
 check('ED19 menu has declared current implementation',reg.resolve(0xED19,[2,27,28,31])['owners']==['CityMenuNavigation'])
 check('same banked address in different physical mapping is not one service',model.context_key(0xA000,[2,25,26,31],'a')!=model.context_key(0xA000,[2,29,30,31],'b'))
 check('banked target without mapping never acquires a current owner',reg.resolve(0xA030,None)['status']=='mapping_unknown')
 check('fixed31 identity can share context but must not manufacture data8000 mapping',model.context_key(0xF283,[1,25,26,31],'a')==model.context_key(0xF283,[2,27,28,31],'b'))
 check('officer name packets route to actual OfficerUIServices owner',reg.resolve(0xA030,[2,29,30,31])['owners']==['OfficerUIServices'])
 saved=reg.cache.get(('PointerLifecycleServices','LOCAL_ENTRIES'),model.MISSING);reg.cache['PointerLifecycleServices','LOCAL_ENTRIES']=model.MISSING
 try:check('unparsed high-priority override must not fall through to a lower owner',reg.resolve(0xA000,[2,27,28,31])['status']=='conditional_route_unknown')
 finally:reg.cache['PointerLifecycleServices','LOCAL_ENTRIES']=saved
 check('unknown target does not turn into a fake returned owner',not reg.resolve(0x8BAD,[2,27,28,31])['owners'])
 events=read('receipt-observations.json')['observations'];services=read('observed-service-index.json')['services'];lookup={r['service_key']:r for r in services}
 check('all observation/context IDs exact and unique',len(lookup)==len(services)and len(events)==summary['observation_count'])
 receipts={}
 for i,row in enumerate(events):
  path=row['receipt']
  if path not in receipts:receipts[path]=model.read(path)
  original=pointer(receipts[path],row['json_pointer']);assert isinstance(original,dict)
  assert i in lookup[row['service_key']]['contexts']
  if row['address_kind']=='execution_stop_location_not_service_entry':
   assert row['service_key'].startswith('execution-location:')and row['current_route']['status']=='not_a_callee_identity'
   assert row['disposition']!='bounded_unresolved_route_requires_reproduction'
  else:
   assert model.context_key(row['target'],row['entry_banks'],path+'#'+row['json_pointer'])==row['service_key']
   assert reg.resolve(row['target'],row['entry_banks'])==row['current_route']
 for service in services:
  rows=[events[i]for i in service['contexts']]
  assert Counter(r['disposition']for r in rows)==service['disposition_counts']
  assert service['owner_candidates']==sorted({o for r in rows for o in r['current_route']['owners']})
 check('every receipt JSON pointer and service context preserved; no stopped-PC-as-callee conflation',True)
 check('intentionally removed division/menu owners are not unknown implementations',sum(r['disposition']=='intentional_dependency_fixture_not_missing_inventory'and r['receipt']=='analysis/phase24/lifecycle/validation.json'for r in events)==2)
 check('permanent boot F41E diagnostic is not an unimplemented service',all(r['disposition']=='implemented_permanent_diagnostic_not_missing_entry'for r in events if r['receipt']=='analysis/phase14/boot/validation.json'and r['target']==0xF41E))
 check('B78B reply wait is not promoted to missing callee',all(r['disposition']=='original_software_or_hardware_wait_not_missing_entry'for r in events if r['receipt']=='analysis/phase19/services/validation.json'and r['target']==0xB78B))
 check('counts are observation bookkeeping only, not new CPU cases',Counter(r['disposition']for r in events)==summary['observation_disposition_counts'])
 del receipts
 static=read('trusted-static-calls.json')['services'];raw_count=0
 for group in static:
  for row in group['trusted_callsites']:
   pc=row['cpu'];bank=row['physical_bank'];offset=16+bank*0x2000+(pc&0x1FFF);raw=bytes.fromhex(row['raw_hex'])
   assert offset==row['rom_offset']and rom[offset:offset+len(raw)]==raw
   assert raw[0]in(0x20,0x4C)and(raw[1]|raw[2]<<8)==group['target'];raw_count+=1
   expected=31 if group['target']>=0xE000 else bank if pc//0x2000==group['target']//0x2000 else None
   assert expected==group['logical_target_physical_bank']
   if group['target']<0xE000:assert not group['current_route']['owners']
 check('trusted opcode edges use original bytes/+16; same-window identity never invents other PRG pages',raw_count>0)
 calls,markers,catalog=model.syntax(reg);syn=read('source-syntax-boundaries.json')
 check('source AST call/dependency/entry inventories exactly regenerated without Source import',calls==syn['external_call_sites']and markers==syn['dependency_or_wait_markers']and catalog==syn['entry_catalog'])
 check('route model predicates and source line evidence current',read('owner-route-catalog.json')['rules']==[{k:v for k,v in r.items()if k!='test'}for r in reg.routes])
 captured,pins=model.captured_callers(reg);check('actual saved-caller identity/mapper scope retained separately',captured==read('captured-caller-index.json')['callers'])
 dimensions=read('acceptance-map.json')['dimensions'];check('all ten inherited acceptance dimensions retained',set(d['id']for d in dimensions)=={f'A{i:02d}'for i in range(1,11)})
 check('no numeric unknown total or whole-game closure/completion invented',summary['unknown_unique_services']is None and summary['whole_game_service_closure_proven']is False)
 for name in('analyze_service_gaps_phase25.py','verify_service_gaps_phase25.py'):
  tree=ast.parse((ROOT/'scripts'/name).read_text())
  for node in ast.walk(tree):
   if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('eval','exec','compile','__import__')
   if isinstance(node,(ast.Import,ast.ImportFrom)):
    module=node.module if isinstance(node,ast.ImportFrom)else' '.join(x.name for x in node.names)
    assert not any(x in(module or'')for x in('py65','nes_runtime','source.recovered'))
 check('new scripts statically read documents/AST only; no CPU/core/production imports',True)
 sourcepins=summary['source_and_validator_sha256']|{'scripts/verify_service_gaps_phase25.py':sha(__file__)}
 artifactpins=summary['artifact_and_dependency_sha256']|{str(p.relative_to(ROOT)):sha(p)for p in sorted(OUT.glob('*'))if p.is_file()and p.name not in('verification.json','evidence.json')}
 result=dict(schema='phase25-readonly-service-index-validation-v1',status='passed',source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,check_count=len(checks),checks=checks,
  unknown_unique_services=None,whole_game_service_closure_proven=False,source_file_count=summary['source_file_count'],receipt_file_count=summary['receipt_file_count'],observation_count=len(events),raw_original_callsite_count=raw_count,
  source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256=artifactpins,scope='Static/pin/index cross-check only. The counts describe existing evidence records and declarations, not new game execution or a missing-service total.')
 model.save('verification.json',result);model.save('evidence.json',dict(schema='phase25-readonly-service-index-evidence-v1',status='passed',source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,
  analyzer_path='scripts/analyze_service_gaps_phase25.py',validator_path='scripts/verify_service_gaps_phase25.py',source_and_validator_sha256=sourcepins,
  artifact_and_dependency_sha256=artifactpins|{'analysis/phase25/services/verification.json':sha(OUT/'verification.json')},unknown_unique_services=None,whole_game_service_closure_proven=False,check_count=len(checks)))
 print(json.dumps(dict(status='passed',checks=len(checks),source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,unknown_unique_services=None)))

if __name__=='__main__':main()
