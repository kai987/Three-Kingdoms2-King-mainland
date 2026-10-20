#!/usr/bin/env python3
"""Metadata-only decimal-bank padding correction; no execution or v1 rewrite."""
from pathlib import Path
import copy,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-ee07-return-family'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 original=json.loads((OUT/'known-direct-caller-inventory.json').read_text());canonical=copy.deepcopy(original);aliases=[]
 for i,(before,row)in enumerate(zip(original['callers'],canonical['callers'],strict=True)):
  old=row['id'];new=old.replace(f':b{row["bank"]}:',f':b{row["bank"]:02d}:')
  if old!=new:row['id']=new;aliases.append(dict(old=old,canonical=new,locator=f'/callers/{i}/id',bank=row['bank'],pc=row['pc'],rom_offset=row['rom_offset']))
 assert len(aliases)==8 and all(x['bank']==9 for x in aliases)
 canonical.update(schema='wp03-EE07-known-direct-callers-canonical-v2',original_inventory_sha256=sha(OUT/'known-direct-caller-inventory.json'),
                  convention='Two-digit decimal bank b09; CPU/ROM address digits are hexadecimal. No physical parameter or case changes.')
 save('known-direct-caller-inventory-v2.json',canonical)
 save('typed-ID-normalization.json',dict(original_inventory_sha256=sha(OUT/'known-direct-caller-inventory.json'),canonical_inventory_sha256=sha(OUT/'known-direct-caller-inventory-v2.json'),
  aliases=aliases,alias_count=8,original_execution_scope_unchanged=True,original_implementation_pins_unchanged=True,
  Source_CPU_Native_executions=0,physical_parameter_changes=0,field_classification_changes=0,raw_classification_changes=0,
  original_scope_sha256=sha(OUT/'family-scope.json'),original_acceptance_sha256=sha(OUT/'acceptance.json')))
 print(json.dumps(dict(status='metadata_only_canonical_v2',aliases=8,Source_CPU_Native_executions=0)))
if __name__=='__main__':main()
