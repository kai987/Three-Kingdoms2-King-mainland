#!/usr/bin/env python3
"""Root-only ordinary defensive play; no memory/ready/PC preparation."""
from pathlib import Path
import argparse,hashlib,json,sys,collections
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from capture_campaign_flows import Capture,ROM_SHA,CORE_SHA
from capture_native_postbattle_early import serialized
from source.recovered.nestopia_context import NestopiaContext
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class Battle(Capture):
 def patch(self,*a,**kw):raise AssertionError('No memory preparation')
 def reset(self,*a,**kw):raise AssertionError('No reset')
 def observe(self,rt):
  r,s=rt.memory(2),rt.memory(0);raw=serialized(rt);ctx=NestopiaContext.parse(raw);pcm=rt.pcm_frame()
  self.rows.append(dict(frame=rt.frames,global_state=r[0x7A],NMI=r[0x78],battle=list(r[0x500:0x508]),ordinary=list(r[0x540:0x544]),outcome=r[0x514],AI_request=s[0xF8B],mode=s[0xF91],registers=ctx.registers,banks=list(ctx.prg_banks),units=[dict(slot=i,ID=r[0x664+i],x=r[0x600+i],y=r[0x614+i],side=r[0x628+i])for i in(0,10)],**{k+'_sha256':hashlib.sha256(v).hexdigest()for k,v in [('RAM',r),('SRAM',s),('RGB',rt.frame.tobytes()),('PCM',pcm),('state',raw)]}))
  self.ring.append((rt.frames,raw))
  sig=(r[0x7A],r[0x78],r[0x500],r[0x501])
  if sig!=self.last:
   self.transitions.append(dict(frame=rt.frames,signature=sig));self.last=sig
   if sig[2]in(13,14,15)or len(self.transitions)<5:self.snap('state-'+str(rt.frames)+'-'+'-'.join(map(str,sig)))
  if sig[0]==4 and sig[2]==15:
   for f,b in self.ring:(self.out/f'pre-result-frame-{f:05d}.state').write_bytes(b)
 def pulse(self,key,release=180,purpose='Original defensive battle input'):self.press(key,release,purpose)
def main():
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--mother',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--limit',type=int,default=30000);a=p.parse_args();assert not a.out.exists();c=Battle(a.rom,a.out);c.ring=collections.deque(maxlen=8);stop='bounded_frame_limit';error=None;waits=0
 try:
  c.inherit(a.mother)
  while c.rt.frames<a.limit:
   r=c.rt.memory(2)
   if r[0x7A]==4 and r[0x500]==15:stop='actual_postbattle15_observed';c.step(40,(),'Observe real postbattle processing');break
   if r[0x7A]==4 and list(r[0x500:0x502])==[0,2]:
    # A opens the actual command grid; Down twice then Right selects wait.
    c.pulse('a',180,'Open original commander command menu')
    rr=c.rt.memory(2)
    if list(rr[0x500:0x502])==[0,3]:
     c.pulse('down',35,'Select second row of original command grid');c.pulse('down',35,'Select bottom row of original command grid');c.pulse('right',35,'Select original wait command');c.pulse('a',220,'Open original wait confirmation');waits+=1
    else:c.step(8,(),'Observe original command transition')
   elif r[0x7A]==4 and r[0x500]in(7,10):
    if r[0x300]==255 and r[0x304]==255:c.pulse('a',180,'Acknowledge original side/wait notice')
    else:c.step(8,(),'Await real text completion')
   elif r[0x7A]in(6,7):c.pulse('a',90,'Original combat scene default command/result continuation')
   elif r[0x7A]==4 and r[0x500]in(11,12):c.pulse('a',180,'Acknowledge original combat summary')
   else:c.step(8,(),'Observe actual AI tactical progression')
 except Exception as e:stop='actual_boundary_failure';error=repr(e)
 finally:
  if c.rt.frames:c.snap('final')
  c.finish();v=dict(schema='phase31-original-defensive-battle-probe-v1',status='exploratory_not_formal_double_run',stop=stop,error=error,frames=c.rt.frames,wait_commands=waits,mother=dict(path=str(a.mother),sha256=sha(a.mother)),ROM_sha256=ROM_SHA,core_sha256=CORE_SHA,new_preparation=[],additional_core_memory_writes=0,cold_boot=False,state_imported=True,Source_CPU_cases=0,script_sha256=sha(__file__),final_fields=c.current());(c.out/'probe.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v[k]for k in ['stop','error','frames','wait_commands']}),flush=True);c.close()
if __name__=='__main__':main()
