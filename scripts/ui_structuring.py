"""Offline lowering of nested labelled continues to static Python exceptions.

This compiler helper is never imported by recovered production source. It
extends the pinned phase11 structurer without modifying historical code.
Each generated exception type is a statically named loop, not a runtime PC
dispatcher or instruction representation.
"""
import inspect,textwrap,re
from analyze_battle_scene_controller import Structurer,BRANCHES,MANUAL_PROCEDURES

def build_procedure():
 body=textwrap.dedent(inspect.getsource(Structurer.procedure))
 old="if pc!=active[-1]:raise ValueError(f'Outer loop transfer {entry:04X}:{pc:04X}')"
 assert body.count(old)==2
 body,n=re.subn(r"(?m)^([ \t]*)"+re.escape(old),lambda m:m[1]+"if pc!=active[-1]:\n"+m[1]+"    put(indent,f'raise _ContinueLoop_{pc:04X}');return False",body)
 assert n==2
 old=r"(?m)^([ \t]*)falls=emit_body\(pc,after,indent\+1,active\+\(pc,\),path,first=True\)\n\1if falls:put\(indent\+1,'break'\)"
 def loop(m):
  pad=m[1]
  return '\n'.join(pad+line for line in["put(indent+1,'try:')","falls=emit_body(pc,after,indent+2,active+(pc,),path,first=True)","if falls:put(indent+2,'break')","put(indent+1,f'except _ContinueLoop_{pc:04X}:')","put(indent+2,'continue')"])
 body,n=re.subn(old,loop,body);assert n==1
 namespace=dict(BRANCHES=BRANCHES,MANUAL_PROCEDURES=MANUAL_PROCEDURES)
 exec(compile(body,'<offline-labelled-loop-structurer>','exec'),namespace)
 return namespace['procedure']

labelled_procedure=build_procedure()
def loop_exception_source(stats):
 headers=sorted({h for s in stats for h in s.get('natural_loop_headers',[])})
 return ''.join(f'class _ContinueLoop_{h:04X}(Exception):pass\n'for h in headers)+'\n'
