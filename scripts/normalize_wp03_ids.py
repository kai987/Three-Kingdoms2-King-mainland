#!/usr/bin/env python3
"""Offline canonical-ID correction. Original scope/run/producer stay intact."""
from pathlib import Path
import copy,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-shared-entry-family'
ROM='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(n,x):
    p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    original=read(OUT/'family-scope.json');scope=copy.deepcopy(original);pairs=[]
    closure=read(ROOT/'analysis/closure-audit-20261018/unique-gap-register.json')
    canonical={x['rom_offset']:x['source_row_id']for x in closure['instruction_row_mapping']}
    for index,row in enumerate(scope['selected_prior_records']):
        old=scope['selected_typed_ids'][index];new=canonical[row['rom_offset']]
        assert new==f'I:{ROM}:b{row["physical_bank"]:02d}:cpu{row["cpu"]:04X}:rom{row["rom_offset"]:06X}'
        pairs.append(dict(executed_scope_v1_alias=old,canonical_ID=new,physical_bank=row['physical_bank'],cpu=row['cpu'],rom_offset=row['rom_offset']))
        scope['selected_typed_ids'][index]=new
    scope['schema']='wp03-EADE-family-scope-v2-canonical-IDs';scope['original_execution_scope_sha256']=sha(OUT/'family-scope.json')
    scope['revision_scope']='Only ID string normalization after run-01; all numerical scope/matrix inputs unchanged.'
    save('family-scope-v2.json',scope)
    cross=read(OUT/'cross-ledger-relations.json');cross['selected_instruction_ids']=scope['selected_typed_ids'];raw=[]
    for row in cross['operand_byte_relations']:
        old=row['raw_id'];parts=old.split(':');bank=int(parts[2][1:],16);new=old.replace(parts[2],f'b{bank:02d}',1)
        raw.append(dict(executed_scope_v1_alias=old,canonical_ID=new,physical_bank=bank));row['raw_id']=new
    cross['schema']='wp03-cross-ledger-relations-v2-canonical-IDs';save('cross-ledger-relations-v2.json',cross)
    save('typed-ID-normalization.json',dict(schema='wp03-offline-ID-namespace-correction-v1',
        original_scope_sha256=sha(OUT/'family-scope.json'),canonical_scope_sha256=sha(OUT/'family-scope-v2.json'),
        original_run_receipt_sha256=sha(OUT/'run-01/validation.json'),instruction_aliases=pairs,raw_operand_aliases=raw,
        canonical_bank_format='Decimal two-digit bank, matching frozen closure row IDs; CPU/offset hex unchanged.',
        CPU_Source_Native_executions=0,no_physical_bank_address_case_or_byte_change=True,
        old_scope_producer_and_executed_hashes_preserved=True))
    print(json.dumps(dict(status='canonical_IDs_normalized_without_reexecution',selected_IDs=scope['selected_typed_ids'],aliases=len(pairs)+len(raw))))
if __name__=='__main__':main()
