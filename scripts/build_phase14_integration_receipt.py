#!/usr/bin/env python3
"""Assemble passed child matrices, retaining completion kinds and row scopes.

This reads existing receipts only. It does not add tests, execute source/CPU,
replay Native or reinterpret a bounded E066 completion as an RTS.
"""
from pathlib import Path
from collections import Counter
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase14'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 pins={};artifacts={};rows=[];guards=[];limits=[];children=[];kinds=Counter();groups=Counter()
 for area,path in [('boot',OUT/'boot-integration.json'),('cooperation',OUT/'cooperation-integration.json')]:
  d=json.loads(path.read_text());assert d['status']=='passed'and not d['failed_count']and not d.get('quick',False)
  assert d['source_original_CPU_callbacks']==0 and not d['source_IR_interpretation']and not d['production_fallback']
  assert len(d['rows'])==d['rom_cpu_case_count']and len(d['guards'])==d['source_guard_case_count']
  for name,h in d['source_sha256'].items():
   assert sha(ROOT/name)==h,name
   assert name not in pins or pins[name]==h,name
   pins[name]=h
  for name,h in d.get('artifact_sha256',{}).items():
   assert sha(ROOT/name)==h,name;artifacts[name]=h
  artifacts[str(path.relative_to(ROOT))]=sha(path)
  for raw in d['rows']:
   row=dict(raw);old=row['comparison'];kind=row.get('completion_kind')
   if kind is None:
    kind='reset_E066_boundary'if old=='reset_E066_boundary'else'main_E066_boundary'if old=='complete_main_boundary'else old
   if old=='strict_prefix':kind='strict_prefix';comparison='strict_prefix'
   else:comparison='complete_return'
   row.update(comparison=comparison,completion_kind=kind,component=area,component_comparison=old)
   row['source_original_CPU_callbacks']=0
   rows.append(row);kinds[kind]+=1;groups[area+'/'+kind]+=1
  guards.extend(dict(component=area,body=g)for g in d['guards']);limits.extend(d['limits'])
  children.append(dict(component=area,path=str(path.relative_to(ROOT)),sha256=sha(path),CPU_cases=d['rom_cpu_case_count'],guards=d['source_guard_case_count'],preparation_CPU_comparisons_within_cases=d.get('preparation_CPU_comparisons_within_cases',0)))
 pins['scripts/build_phase14_integration_receipt.py']=sha(__file__)
 complete=sum(row['comparison']=='complete_return'for row in rows);prefix=sum(row['comparison']=='strict_prefix'for row in rows)
 result=dict(schema='phase14-pure-gameengine-integration-v1',status='passed',rom_sha256=d['rom_sha256'],rom_cpu_case_count=len(rows),complete_return_count=complete,strict_prefix_count=prefix,source_guard_case_count=len(guards),failed_count=0,failures=[],counts=dict(groups),completion_kinds=dict(kinds),
  reset_boundary_count=kinds['reset_E066_boundary'],main_boundary_count=kinds['main_E066_boundary'],actual_caller_return_count=kinds['actual_caller_RTS'],
  rows=rows,guards=guards,source_original_CPU_callbacks=0,source_IR_interpretation=False,production_fallback=False,native_internal_CPU_trace=False,source_sha256=pins,artifact_sha256=artifacts,children=children,
  preparation_CPU_comparisons_within_cases=sum(x['preparation_CPU_comparisons_within_cases']for x in children),
  comparison_scope='Per-row exact scope from child matrices; not a uniform native frame or PPU timing claim',
  limits=['Complete_return is the historical receipt category for a complete declared boundary. Completion_kinds identifies actual RTS versus reset E066 and ordinary main E066; neither E066 completion fabricates an RTS.',*dict.fromkeys(limits)])
 (OUT/'source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','completion_kinds')}))
if __name__=='__main__':main()
