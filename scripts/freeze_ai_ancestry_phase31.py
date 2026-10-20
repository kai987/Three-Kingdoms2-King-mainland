#!/usr/bin/env python3
"""Preserve the actual segmented ordinary-input ancestry; never run a core."""
from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from source.recovered.nestopia_context import NestopiaContext
OUT=ROOT/'analysis/phase31/ancestry/natural-AI-mode2'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SEGMENTS=[
 ('natural-AI-defence-search12','final',48681,'probe_ai_defence_phase31.py','search.json'),
 ('natural-defence-reveal','final',400,'probe_postbattle_continuity_phase31.py','probe.json'),
 ('natural-defence-place','final',1338,'probe_postbattle_continuity_phase31.py','probe.json'),
 ('natural-defence-confirm','final',302,'probe_postbattle_continuity_phase31.py','probe.json'),
 ('natural-defensive-all-notices','final',30132,'probe_defensive_wait_all_notices_phase31.py','probe.json'),
 ('natural-defensive-completion','final',45132,'probe_defensive_complete_notices_phase31.py','probe.json'),
 ('natural-defence-move-adjacent','final',922,'probe_postbattle_continuity_phase31.py','probe.json'),
 ('natural-defence-attack','final',1042,'probe_postbattle_continuity_phase31.py','probe.json'),
 ('natural-defence-normal-combat','final',12476,'probe_ordinary_defence_attack_phase31.py','probe.json'),
 ('natural-defence-duel-result','state-1211-4-3-11-0',1211,'probe_duel_result_phase31.py','probe.json')]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def pin(p):return dict(path=rel(p),sha256=sha(p),bytes=Path(p).stat().st_size)
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def clipped(plan,start,end):
 out=[]
 for i,s in enumerate(plan):
  lo=max(start,s['start_frame']);hi=min(end,s['start_frame']+s['frames'])
  if hi>lo:out.append(dict(s,start_frame=lo-start,frames=hi-lo,original_step=i,original_start_frame=s['start_frame']))
 assert sum(x['frames']for x in out)==end-start
 t=0
 for x in out:assert x['start_frame']==t;t+=x['frames'];assert set(x['buttons'])<=set(('a','b','start','select','up','down','left','right'))
 return out
def main():
 assert not OUT.exists();OUT.mkdir(parents=True);rows=[];pins={};previous=ROOT/'analysis/phase22/runtime/original-control/final.state';total=0
 for i,(name,label,frames,script,receipt_name)in enumerate(SEGMENTS):
  source=ROOT/'analysis/phase31/exploratory'/name;dest=OUT/f'segment-{i+1:02d}';dest.mkdir()
  receipt=json.loads((source/receipt_name).read_text());mother=Path(receipt['mother']['path']);mother=mother if mother.is_absolute()else ROOT/mother
  assert sha(mother)==receipt['mother']['sha256']==sha(previous)
  assert receipt['additional_core_memory_writes']==0 and receipt.get('new_preparation',[])==[]
  script_path=ROOT/'scripts'/script;assert sha(script_path)==receipt.get('script_sha256',receipt.get('producer_sha256'))
  fullplan=json.loads((source/'input-plan.json').read_text())if(source/'input-plan.json').exists()else receipt['plan']
  plan=clipped(fullplan,0,frames);write(dest/'input-plan.json',plan)
  logs=json.loads((source/'frame-services.json').read_text());assert len(logs)>=frames and [x['frame']for x in logs[:frames]]==list(range(1,frames+1))
  for k in('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256'):assert all(len(x[k])==64 for x in logs[:frames])
  end=source/(label+'.state');ctx=NestopiaContext.parse(end.read_bytes());r=source/(label+'-ram.bin');s=source/(label+'-sram.bin');assert ctx.ram==r.read_bytes()and ctx.sram==s.read_bytes()
  assert sha(r)==logs[frames-1]['RAM_sha256']and sha(s)==logs[frames-1]['SRAM_sha256']
  actual_state_key='state_sha256'if'state_sha256'in logs[frames-1]else'whole_serialized_state_sha256';assert sha(end)==logs[frames-1][actual_state_key]
  for original,newname in[(mother,'initial.state'),(end,'final.state'),(r,'final-ram.bin'),(s,'final-sram.bin'),(source/(label+'.png'),'final.png'),(source/receipt_name,'original-probe-receipt.json')]:shutil.copyfile(original,dest/newname)
  # Complete per-frame hashes preserve observations of each used prefix.
  write(dest/'frame-buffer-hashes.json',logs[:frames]);write(dest/'original-input-plan.json',fullplan)
  row=dict(index=i+1,name=name,frames=frames,state_import_at_start=True,new_preparation=[],additional_core_memory_writes=0,initial_state=pin(dest/'initial.state'),final_state=pin(dest/'final.state'),final_RAM=pin(dest/'final-ram.bin'),final_SRAM=pin(dest/'final-sram.bin'),input_plan=pin(dest/'input-plan.json'),complete_frame_hash_log=pin(dest/'frame-buffer-hashes.json'),source_script=pin(script_path),original_result=pin(dest/'original-probe-receipt.json'),observed_final_CPU_registers=ctx.registers,observed_final_PRG_banks=list(ctx.prg_banks))
  rows.append(row);total+=frames;previous=end
 mother_dir=OUT/'mother';mother_dir.mkdir();last=OUT/'segment-10'
 for old,new in [('final.state','AI-result-mother.state'),('final-ram.bin','AI-result-mother-ram.bin'),('final-sram.bin','AI-result-mother-sram.bin'),('final.png','AI-result-mother.png')]:shutil.copyfile(last/old,mother_dir/new)
 mother=mother_dir/'AI-result-mother.state';ctx=NestopiaContext.parse(mother.read_bytes());assert ctx.ram[0x514]==131 and(ctx.ram[0x7A],ctx.ram[0x78],ctx.ram[0x500],ctx.ram[0x501])==(4,3,11,0)
 # Replay the actual remaining duel/result inputs, then the observed ordinary
 # result acknowledgements; do not import the exploratory middle boundary.
 duel=json.loads((ROOT/'analysis/phase31/exploratory/natural-defence-duel-result/input-plan.json').read_text());post=json.loads((ROOT/'analysis/phase31/exploratory/natural-defence-postbattle/input-plan.json').read_text())
 plan=clipped(duel,1211,1528);tail=clipped(post,0,240)
 for x in tail:x['start_frame']+=317
 plan+=tail;assert sum(x['frames']for x in plan)==557;write(OUT/'formal-input-plan.json',plan)
 points=[dict(label='AI-result-mother',frame=1211,state='AI-result-mother.state',RAM='AI-result-mother-ram.bin',SRAM='AI-result-mother-sram.bin',image='AI-result-mother.png')];write(mother_dir/'checkpoints.json',points)
 for p in OUT.rglob('*'):
  if p.is_file():pins[rel(p)]=sha(p)
 for name in ['analysis/phase22/runtime/validation.json','analysis/phase22/runtime/evidence.json','analysis/phase22/runtime/original-control/validation.json','analysis/phase22/runtime/original-control/final.state','scripts/nes_runtime.py','scripts/nes_service_runtime.py','scripts/freeze_ai_ancestry_phase31.py']:pins[name]=sha(ROOT/name)
 value=dict(schema='phase31-natural-AI-ordinary-segmented-ancestry-v1',status='verified_content_lineage_not_fresh_repeat',ROM_sha256=ROM_SHA,natural_ordinary_input_route=True,controlled_ancestry=False,known_inherited_preparation_byte_writes=0,known_inherited_preparation=[],earlier_ancestor_cold_boot=True,additional_preparation=[],additional_core_memory_writes=0,new_case_state_imported=True,new_case_cold_boot=False,segments=rows,segmented_upstream_frames=total,upstream_original_core_runs=len(rows),upstream_fresh_repeat_claim=False,upstream_internal_CPU_trace=False,root_frozen_ancestor=pin(ROOT/'analysis/phase22/runtime/original-control/validation.json'),parent_checkpoints=pin(mother_dir/'checkpoints.json'),mother=pin(mother),input_sha256=pins,limits=['Ten actual ordinary-input segments with imports at their boundaries; no new emulated memory, PC, RNG, result or ready preparation.','Upstream original-core observations are single-run ancestry, not formal four-run Native evidence. Complete used-prefix frame hashes and actual boundary states are retained.','Deployment8,5 was an input intention; later actual RAM positions were Cao12,10 and AI27,10. Later movement actually produced14,10 and15,10.','Wait-command counters count openings/attempts; actual day and phase counters remain separately recorded.','The selected mother still has0514=131 from duel context. New war outcome must be established by actual DD72 write events.'])
 write(OUT/'ancestry.json',value)
 spec=dict(case='natural-AI-mode2',mother=rel(mother),mother_sha256=sha(mother),parent_frame=1211,frames=557,natural=True,ancestry_path=rel(OUT/'ancestry.json'),expected_initial=dict(global_007A=4,NMI_0078=3,battle_0500_0501=[11,0],outcome_0514=131),plan_source=rel(OUT/'formal-input-plan.json'),plan_sha256=sha(OUT/'formal-input-plan.json'),plan_start=0,plan_end=557,additional_core_memory_writes=0)
 write(OUT/'case-spec.json',spec);print(json.dumps(dict(status=value['status'],segments=len(rows),upstream_frames=total,mother=spec['mother'],mother_sha256=spec['mother_sha256'],formal_frames=557)))
if __name__=='__main__':main()
