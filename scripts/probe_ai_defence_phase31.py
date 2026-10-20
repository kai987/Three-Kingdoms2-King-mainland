#!/usr/bin/env python3
"""Root-only bounded ordinary-command search for an original AI attack."""
from pathlib import Path
import argparse,collections,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from capture_campaign_flows import Capture,ROM_SHA,CORE_SHA
from capture_native_postbattle_early import serialized
from source.recovered.nestopia_context import NestopiaContext
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class DefenseFound(Exception):pass
class Search(Capture):
 def patch(self,*a,**kw):raise AssertionError('No numerical preparation is permitted')
 def reset(self,*a,**kw):raise AssertionError('No reset is permitted')
 def observe(self,rt):
  r,s=rt.memory(2),rt.memory(0);pcm=rt.pcm_frame();raw=serialized(rt);ctx=NestopiaContext.parse(raw)
  self.rows.append(dict(frame=rt.frames,global_state=r[0x7A],NMI=r[0x78],city=list(r[0x400:0x404]),battle=list(r[0x500:0x508]),outcome=r[0x514],AI_request=s[0xF8B],calendar=list(s[0xF00:0xF07]),registers=ctx.registers,banks=list(ctx.prg_banks),**{k+'_sha256':hashlib.sha256(v).hexdigest()for k,v in [('RAM',r),('SRAM',s),('RGB',rt.frame.tobytes()),('PCM',pcm),('state',raw)]}))
  self.ring.append((rt.frames,raw))
  hi=r[0x507]>>4;lo=r[0x507]&15
  if r[0x7A]in(3,4)and r[0x78]==3 and hi<7 and lo<7 and s[0xF0A+8*hi]==3 and s[0xF0A+8*lo]!=3:
   self.snap('natural-AI-defence-trigger')
   for frame,state in self.ring:(self.out/f'pre-defence-frame-{frame:05d}.state').write_bytes(state)
   raise DefenseFound()
def main():
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--months',type=int,default=3);a=p.parse_args();assert not a.out.exists()
 c=Search(a.rom,a.out);c.ring=collections.deque(maxlen=8);stop='bounded_month_budget';error=None;completed=0;mother=ROOT/'analysis/phase22/runtime/original-control/final.state'
 try:
  c.inherit(mother)
  for month in range(a.months):
   for action in range(3):c.recruitment(month*3+action+1)
   c.next_player_message('month'+str(month+1)+'-next-player')
   c.press_ready('a',0,1,'month'+str(month+1)+'-world');completed+=1
 except DefenseFound:stop='actual_AI_attacker_player_defender_tactical_frame'
 except Exception as e:stop='actual_boundary_failure';error=repr(e)
 finally:
  if c.rt.frames:c.snap('final')
  # The interrupt may occur inside an8-frame run; retain only actually run inputs.
  c.plan=[dict(x,frames=min(x['frames'],c.rt.frames-x['start_frame']))for x in c.plan if x['start_frame']<c.rt.frames]
  c.finish();v=dict(schema='phase31-original-only-ordinary-AI-defence-search-v1',status='exploratory_not_formal_double_run',stop=stop,error=error,requested_months=a.months,completed_months=completed,frames=c.rt.frames,mother=dict(path=str(mother.relative_to(ROOT)),sha256=sha(mother)),ROM_sha256=ROM_SHA,core_sha256=CORE_SHA,new_preparation=[],additional_core_memory_writes=0,state_imported=True,cold_boot=False,natural_ancestry=True,Source_CPU_cases=0,script_sha256=sha(__file__),inherited_readonly_scripts={n:sha(ROOT/n)for n in ['scripts/capture_campaign_flows.py','scripts/capture_boot_cooperation_flows.py']},limits=['Bounded route search only, not proof of global unreachability.','No internal CPU trace; a real BB36 JS R still requires the separate passive observer.'])
  (c.out/'search.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps(v),flush=True);c.close()
if __name__=='__main__':main()
