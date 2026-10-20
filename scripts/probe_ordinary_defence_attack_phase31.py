#!/usr/bin/env python3
"""Continue the actual normal-attack UI with ordinary default commands only."""
from pathlib import Path
import argparse,hashlib,json,sys,collections
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from probe_defensive_complete_notices_phase31 import Battle,ROM_SHA,CORE_SHA,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--mother',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();c=Battle(a.rom,a.out);c.ring=collections.deque(maxlen=8);stop='bounded_ordinary_attack_400_pulses';error=None
 try:
  c.inherit(a.mother)
  for i in range(400):
   r=c.rt.memory(2)
   if r[0x7A]!=6:stop='actual_normal_attack_scene_return';c.step(240,(),'Observe original battle outcome consumer');break
   c.pulse('a',90,'Original default formation/forward combat command and real result acknowledgment')
 except Exception as e:stop='actual_boundary_failure';error=repr(e)
 finally:
  c.snap('final');c.finish();v=dict(schema='phase31-original-ordinary-attack-probe-v1',status='exploratory_not_formal_double_run',stop=stop,error=error,frames=c.rt.frames,mother=dict(path=str(a.mother),sha256=sha(a.mother)),ROM_sha256=ROM_SHA,core_sha256=CORE_SHA,new_preparation=[],additional_core_memory_writes=0,cold_boot=False,state_imported=True,Source_CPU_cases=0,script_sha256=sha(__file__),final_fields=c.current());(c.out/'probe.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v[k]for k in ('stop','error','frames')}),flush=True);c.close()
if __name__=='__main__':main()
