#!/usr/bin/env python3
"""Root-only original-core ordinary-input probe; exploratory, not formal proof."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from nes_service_runtime import ServiceRuntime
from capture_native_postbattle_early import fields,serialized,ROM_SHA,CORE_SHA
from source.recovered.nestopia_context import NestopiaContext
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--mother',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 assert sha(a.rom)==ROM_SHA and a.end>a.start
 assert not a.out.exists();a.out.mkdir(parents=True)
 plan=[]
 for step in json.loads(a.plan.read_text()):
  lo=max(a.start,step['start_frame']);hi=min(a.end,step['start_frame']+step['frames'])
  if hi>lo:plan.append(dict(start_frame=lo-a.start,frames=hi-lo,buttons=step['buttons'],original_start=step['start_frame'],purpose=step.get('purpose')))
 assert sum(s['frames']for s in plan)==a.end-a.start
 r=ServiceRuntime(a.rom,a.out);rows=[];changes=[];last=None
 try:
  assert r.info['core_sha256']==CORE_SHA;r.load_state(a.mother)
  m=NestopiaContext.parse(a.mother.read_bytes());assert r.memory(2)==m.ram and r.memory(0)==m.sram
  def observe(rt):
   nonlocal last
   ram=rt.memory(2);sram=rt.memory(0);raw=serialized(rt);ctx=NestopiaContext.parse(raw);f=fields(ram,sram);pcm=rt.pcm_frame()
   sig=(ram[0x7A],ram[0x78],ram[0x500],ram[0x501],ram[0x400],ram[0x401])
   row=dict(frame=rt.frames,parent_route_frame=a.start+rt.frames,signature=list(sig),registers=ctx.registers,banks=list(ctx.prg_banks),fields=f,**{k+'_sha256':hashlib.sha256(v).hexdigest()for k,v in [('RAM',ram),('SRAM',sram),('RGB',rt.frame.tobytes()),('PCM',pcm),('state',raw)]})
   rows.append(row)
   if sig!=last:
    label=f'change-{rt.frames:05d}-'+ '-'.join(str(x)for x in sig);rt.snapshot(label);changes.append(dict(frame=rt.frames,parent_route_frame=a.start+rt.frames,signature=list(sig),state=label+'.state'));print(json.dumps(changes[-1]),flush=True);last=sig
  for s in plan:r.run(s['frames'],s['buttons'],observe)
  r.snapshot('final');r.save_wav(a.out/'full-audio.wav')
  value=dict(status='exploratory_observed_not_formal_double_run',ROM_sha256=ROM_SHA,core_sha256=CORE_SHA,mother=dict(path=str(a.mother),sha256=sha(a.mother)),original_plan=dict(path=str(a.plan),sha256=sha(a.plan)),start=a.start,end=a.end,frames=r.frames,new_memory_preparation=[],additional_core_memory_writes=0,cold_boot=False,state_imported=True,Source_CPU_cases=0,plan=plan,changes=changes,producer_sha256=sha(__file__))
  for name,obj in [('probe.json',value),('frame-services.json',rows)]: (a.out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 finally:r.close()
if __name__=='__main__':main()
