#!/usr/bin/env python3
"""Build-time structured decompilation of the bounded five-phase city officer card.

Runtime source executes named Python only; original bytes/CFG work occurs here.
"""
from pathlib import Path
from collections import deque
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES,disassemble
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
BRANCH={'BCC':('C',False),'BCS':('C',True),'BEQ':('Z',True),'BNE':('Z',False),'BMI':('N',True),'BPL':('N',False),'BVC':('V',False),'BVS':('V',True)}
def sha(b):return hashlib.sha256(b).hexdigest()
HEADER='"""Independent five-phase city officer detail controller, physical25 A021.\n\nStatic original-byte provenance compiled to named Python if/while/calls.\nNo runtime opcode/IR/program.json or original-CPU fallback is used. Each\ncall genuinely returns to its caller, but a requested packet is not a\ncompleted PPU upload. Real busy queue bytes are never acknowledged here.\n"""\nfrom dataclasses import dataclass\nimport hashlib\nfrom .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall\nfrom .scene_shared_services import SceneSharedServices\nfrom .officer_details_ui_services import OfficerDetailsUIServices\nfrom .portrait_ui_services import PortraitUIServices\nfrom .scene_initialization import SceneInitialization\nfrom .controller_helpers import ControlHelpers\nROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"\nC,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128\n@dataclass(frozen=True)\nclass CityOfficerData:\n    rom:bytes\n    @classmethod\n    def from_rom(cls,rom):\n        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError(\'Pinned original ROM required\')\n        return cls(bytes(rom))\nclass SourceBudget(RuntimeError):pass\nclass InvalidCityCardPhase(ValueError):pass\nclass CityOfficerDetailsController(BattleNMIServices):\n    FIXED=()\n    def __init__(self,memory,data,services=None):\n        super().__init__(memory,callbacks=self._resolve_service)\n        self.data=data if isinstance(data,CityOfficerData)else CityOfficerData.from_rom(data)\n        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=self._resolve_service)\n        self.detail_worker=OfficerDetailsUIServices(memory,self.data.rom,services=services)\n        self.portrait_worker=PortraitUIServices(memory,self.data.rom,services=services)\n        self.initialization=SceneInitialization(memory,self.data.rom,callbacks=services)\n        self.external_services=services;self.controls=ControlHelpers();self.source_locations=[];self.source_budget=100000;self._call_owner=None\n    def _mark(self,pc):\n        self.registers.pc=pc;self.source_locations.append(pc)\n        if len(self.source_locations)>self.source_budget:raise SourceBudget(\'Original city card source operation budget exhausted\')\n    def _shift(self,address,kind):\n        old=self.memory[address];carry=int(bool(self.registers.p&C))\n        self.flag(C,bool(old&128)if kind in (\'asl\',\'rol\')else bool(old&1))\n        self.memory[address]=self.nz((old<<1)|carry if kind==\'rol\'else old<<1 if kind==\'asl\'else (old>>1)|(carry<<7)if kind==\'ror\'else old>>1)\n    def shift_a(self,kind):\n        old=self.registers.a;carry=int(bool(self.registers.p&C))\n        self.flag(C,bool(old&128)if kind in (\'asl\',\'rol\')else bool(old&1))\n        return self.a((old<<1)|carry if kind==\'rol\'else old<<1 if kind==\'asl\'else (old>>1)|(carry<<7)if kind==\'ror\'else old>>1)\n    def _resolve_service(self,call):\n        pair=tuple(call.entry_banks[1:3])\n        if pair==(25,26) and call.target==0xB2D7:result=self.detail_worker(call)\n        elif pair==(25,26) and call.target==0xCE1F:result=self.portrait_worker(call)\n        elif pair==(29,30) and call.target in(0xA015,0xDBB1):result=self.initialization.banked_graphics(call)\n        elif call.target in self.shared.FIXED:result=self.shared(call)\n        elif self.external_services is not None:result=self.external_services(call)\n        else:return dict(status=\'dependency\',reason=\'No independent city-card helper owns this exact entry\',target=call.target)\n        if not isinstance(result,dict)or result.get(\'status\')!=\'returned\':return dict(status=\'dependency\',body=result)\n        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status=\'dependency\',reason=\'City card helper has not reached actual caller PC/SP\',body=result)\n        return result\n    def _service(self,target,kind=\'tail\',return_pc=None,expected_sp=None):\n        r=self.registers;r.pc=target\n        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535\n        if expected_sp is None:expected_sp=(r.sp+2)&255\n        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,\'banks\',())),expected_sp)\n    def call(self,pc,target,*,inline_return=None):\n        sp=self.registers.sp;word=pc+2;self.push(word>>8);self.push(word)\n        if target in self.LOCAL_ENTRIES:yield from self.routine(target)\n        else:yield from self._service(target,\'call\',inline_return or pc+3,sp)\n        if self.registers.pc!=(inline_return or pc+3)or self.registers.sp!=sp:raise RuntimeError(\'City card call has not returned to its real caller\')\n    def _dispatch(self,pc,targets,methods):\n        index=self.registers.a\n        if not 0<=index<len(targets):raise InvalidCityCardPhase(\'Only original five city-card phases are proven\')\n        word=pc+2;self.push(word>>8);self.push(word);self.controls(self,0xEADE,targets[index],\'dispatch\')\n        yield from methods[index]()\n    def result(self,status,**extra):\n        value=super().result(status,**extra)\n        return dict(value,source_locations=list(self.source_locations),city_card_phase=self.memory[0x401],detail_row=self.memory[0x40D],PPU_jobs=self.memory[0x7E],full_NES_frame=False,PPU_upload_completed=False)\n    def run_entry(self,entry=0xA021,registers=None,*,max_source_operations=100000):\n        if entry not in self.LOCAL_ENTRIES:raise ValueError(\'Entry is outside the original city card closure\')\n        if self._program is not None:raise RuntimeError(\'A real city card service is pending; resume it first\')\n        if registers is None:raise ValueError(\'Supply actual caller registers and existing RTS frame\')\n        if tuple(getattr(self.memory,\'banks\',())[1:3])!=(25,26):raise ValueError(\'City card requires actual physical25/26 pair\')\n        if entry in(0xA021,0xAFE5)and self.memory[0x401]>=5:raise InvalidCityCardPhase(\'Legal city-card phases are0..4\')\n        self.source_locations=[];self.source_budget=max_source_operations\n        return self._start(lambda:self.routine(entry),registers,\'city_officer_details\')\n    def tick(self,registers=None):return self.run_entry(0xA021,registers)\n    def __call__(self,call):\n        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(25,26):return dict(status=\'dependency\',reason=\'No city card body owns this exact pair/entry\')\n        if self._program is not None:\n            if self._call_owner is not call:return dict(status=\'dependency\',reason=\'Another caller owns pending city card\')\n            result=self.resume()\n        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)\n        if result[\'status\']==\'returned\':\n            self._call_owner=None\n            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status=\'dependency\',reason=\'City card did not reach actualcaller PC/SP\',body=result)\n        return result\n'

def analyze(rom,out,generate):
 assert sha(rom)==SHA
 def get(pc):return rom[16+25*8192+(pc&8191)]
 def word(pc):return get(pc)|get(pc+1)<<8
 tables={}
 for pc in range(0xAFE5,0xB2D7):
  if bytes(get(pc+i)for i in range(3))!=bytes.fromhex('20DEEA'):continue
  start=pc+3;p=start;bound=0xE000;targets=[]
  while p<bound and len(targets)<64:
   t=word(p)
   if not 0xAFE5<=t<0xB2D7:break
   targets.append(t)
   if t>=p+2:bound=min(bound,t)
   p+=2
  assert p==bound,(hex(pc),hex(p),hex(bound))
  tables[pc]=dict(pc=pc,start=start,end=p,targets=targets)
 assert len(tables[0xAFE8]['targets'])==5
 names={0xA021:'public_city_card',0xAFE5:'city_card_phase_dispatch',0xAFF5:'initialize_city_cards',0xB041:'produce_initial_detail_rows',0xB086:'show_selected_card_and_inputs',0xB09F:'confirm_or_cancel_card',0xB136:'produce_adjacent_card',0xB155:'animate_card_transition',0xB1FF:'portrait_for_roster_slot',0xB209:'begin_previous_or_next_card',0xB260:'advance_card_animation',0xB285:'update_card_scroll_and_chr'}
 notes={0xAFF5:'palette0, compact ten city officers, begin ten-row packet producer',0xB041:'advance original producer until040D==FF then configure original split/scroll',0xB086:'selected officer portrait and real directional/button state',0xB09F:'panel readiness0140 and original confirm/cancel handling',0xB136:'real adjacent card rows and portrait; next phase only when040D==FF',0xB155:'two portrait positions, scroll direction, eighty pixel transition',0xB209:'previous/next roster boundaries, initialize next card row and scroll direction',0xB260:'clear81 during animation, two-pixel increments and actual index change',0xB285:'CHR cache copy at original offset64/16 and 240-pixel scroll wrap'}
 roots=set(names)|{x for t in tables.values()for x in t['targets']};items={};queue=deque(roots);data=[]
 while queue:
  pc=queue.popleft()
  while (0xAFE5<=pc<0xB2D7 or pc==0xA021) and pc not in items:
   op,raw_mode=OPS[get(pc)];size=SIZES[raw_mode];mode={'im':'imm','ab':'abs','zp':'zpg','i':'imp','a':'acc','ix':'inx','iy':'iny'}.get(raw_mode,raw_mode);assert op!='?',hex(pc)
   operand=sum(get(pc+i)<<(8*(i-1))for i in range(1,size));nxt=pc+size
   if op in BRANCH:operand=(pc+2+int.from_bytes(bytes((get(pc+1),)),signed=True))&65535
   item=dict(pc=pc,op=op,mode=mode,operand=operand,next=nxt)
   if pc in tables:item['op']='DISPATCH';item['targets']=tables[pc]['targets'];item['next']=None;queue.extend(item['targets'])
   elif op=='JSR'and operand==0xEE07:
    item['op']='FARCALL';item['target']=word(pc+3);item['next']=pc+5;data.append(dict(start=pc+3,end=pc+5,kind='inline_far_target'))
   elif op in ('JSR','JMP')and (0xAFE5<=operand<0xB2D7 or operand==0xA021):
    queue.append(operand)
    if op=='JSR':roots.add(operand)
   elif op in BRANCH:queue.append(operand)
   items[pc]=item
   if item['op']=='DISPATCH'or op in ('JMP','RTS','RTI','BRK'):break
   pc=item['next']
 for pc in roots:names.setdefault(pc,'local_'+format(pc,'04x'))
 # All routine entries are compile-time names, not a runtime instruction map.
 source=[HEADER];stats=[];gaps=[]
 def target_expr(v):
  n=v['operand'];mode=v['mode']
  if mode=='imm':return f'0x{n:02X}'
  if mode in ('zpg','abs'):a=f'0x{n:04X}'
  elif mode in ('zpx','zpy'):a=f'(0x{n:02X}+r.{"x"if mode=="zpx"else"y"})&255'
  elif mode in ('abx','aby'):a=f'(0x{n:04X}+r.{"x"if mode=="abx"else"y"})&65535'
  elif mode=='iny':a=f'(self.memory[0x{n:02X}]|(self.memory[0x{(n+1)&255:02X}]<<8))+r.y&65535'
  elif mode=='inx':a=f'self.memory[(0x{n:02X}+r.x)&255]|(self.memory[(0x{n+1:02X}+r.x)&255]<<8)'
  else:raise ValueError((v,mode))
  return 'm['+a+']'
 def assignment(v):return target_expr(v)[2:-1]
 def statement(v):
  op=v['op'];value=target_expr(v)if v['mode']not in('imp','acc','rel')else None
  if op in ('LDA','LDX','LDY'):return [f'self.{op[-1].lower()}({value})']
  if op in ('STA','STX','STY'):return [f'{value}=r.{op[-1].lower()}']
  if op in ('INC','DEC'):return [f'self.inc({assignment(v)}{",-1"if op=="DEC"else""})']
  if op in ('INX','DEX','INY','DEY'):return [f'self.{op[-1].lower()}(r.{op[-1].lower()}{"+1"if op.startswith("IN")else"-1"})']
  if op in ('ADC','SBC'):return [f'self.add({value}{",subtract=True"if op=="SBC"else""})']
  if op in ('CMP','CPX','CPY'):return [f'self.cmp(r.{"a"if op=="CMP"else op[-1].lower()},{value})']
  if op in ('AND','ORA','EOR'):return [f'self.a(r.a{{"AND":"&","ORA":"|","EOR":"^"}}["{op}"]{value})'.replace(f'{{"AND":"&","ORA":"|","EOR":"^"}}["{op}"]',{'AND':'&','ORA':'|','EOR':'^'}[op])]
  if op in ('ASL','LSR','ROL','ROR'):return [f'self.shift_a("{op.lower()}")'if v['mode']=='acc'else f'self._shift({assignment(v)},"{op.lower()}")']
  if op in ('CLC','SEC','CLI','SEI','CLD','SED','CLV'):return [f'self.flag({{"CLC":"C","SEC":"C","CLI":"I","SEI":"I","CLD":"D","SED":"D","CLV":"V"}}["{op}"],{op.startswith("SE")})'.replace(f'{{"CLC":"C","SEC":"C","CLI":"I","SEI":"I","CLD":"D","SED":"D","CLV":"V"}}["{op}"]',{'CLC':'C','SEC':'C','CLI':'I','SEI':'I','CLD':'D','SED':'D','CLV':'V'}[op])]
  if op in ('TAX','TAY','TXA','TYA'):return [f'self.{op[-1].lower()}(r.{op[1].lower()})']
  if op=='TXS':return ['r.sp=r.x']
  if op=='TSX':return ['self.x(r.sp)']
  if op=='PHA':return ['self.push(r.a)']
  if op=='PLA':return ['self.a(self.pop())']
  if op=='PHP':return ['self.push(r.p|B|U)']
  if op=='PLP':return ['r.p=self.pop()|B|U']
  if op=='BIT':return [f'self.flag(Z,not(r.a&{value}))',f'self.flag(N,{value}&128)',f'self.flag(V,{value}&64)']
  if op=='JSR':return [f'yield from self.call(0x{v["pc"]:04X},0x{v["operand"]:04X})']
  if op=='FARCALL':return [f'yield from self.call(0x{v["pc"]:04X},0xEE07,inline_return=0x{v["next"]:04X}) # inline target${v["target"]:04X}, Y selector']
  if op=='NOP':return []
  raise ValueError((hex(v['pc']),op))
 for entry in sorted(roots):
  graph={};q=[entry];exits={};END=-1
  while q:
   pc=q.pop()
   if pc in graph:continue
   if pc!=entry and pc in roots:graph[pc]=[END];exits[pc]=('local',names[pc]);continue
   if pc not in items:graph[pc]=[END];exits[pc]=('external',pc);continue
   v=items[pc];op=v['op']
   if op in ('RTS','RTI','DISPATCH'):edges=[END]
   elif op=='JMP':edges=[v['operand']]
   elif op in BRANCH:edges=[v['operand'],v['next']]
   else:edges=[v['next']]
   graph[pc]=edges;q.extend(n for n in edges if n!=END)
  graph[END]=[];nodes=set(graph);pred={n:set()for n in nodes}
  for n,edges in graph.items():
   for e in edges:pred[e].add(n)
  dom={n:({entry}if n==entry else set(nodes))for n in nodes};changed=True
  while changed:
   changed=False
   for n in nodes-{entry}:
    p=pred[n];new={n}|(set.intersection(*(dom[x]for x in p))if p else set())
    if new!=dom[n]:dom[n]=new;changed=True
  loops={}
  for n,edges in graph.items():
   for head in edges:
    if head==END or head not in dom[n]:continue
    region={head,n};todo=[n]
    while todo:
     x=todo.pop()
     for p in pred[x]:
      if p not in region:region.add(p);todo.append(p)
    loops.setdefault(head,set()).update(region)
  post={n:({END}if n==END else set(nodes))for n in nodes};changed=True
  while changed:
   changed=False
   for n in nodes-{END}:
    new={n}|set.intersection(*(post[x]for x in graph[n]))
    if new!=post[n]:post[n]=new;changed=True
  def join(a,b):
   common=post[a]&post[b]
   return max(common,key=lambda x:len(post[x]))if common else END
  lines=[];used=set()
  def emit(pc,stop,indent,loop_stack=(),trail=()):
   prefix=' '*indent
   while pc!=stop and pc!=END:
    if loop_stack:
     head,region,exitpc=loop_stack[-1]
     if pc==head and pc in trail:lines.append(prefix+'continue');return
     if pc==exitpc:lines.append(prefix+'break');return
    if pc in trail:raise ValueError(f'unstructured cycle {pc:04X}')
    if pc in loops and all(pc!=h for h,_,_ in loop_stack):
     region=loops[pc];outs={x for n in region for x in graph[n]if x not in region}
     if not outs:raise ValueError(f'loop{pc:04X} has no bounded exit')
     common=set.intersection(*(post[x]for x in outs))
     exitpc=max(common,key=lambda x:len(post[x]));lines.append(prefix+'while True:')
     emit(pc,exitpc,indent+4,loop_stack+((pc,region,exitpc),),())
     pc=exitpc;continue
    used.add(pc)
    if pc in exits:
     kind,target=exits[pc]
     lines.append(prefix+(f'yield from self.{target}()'if kind=='local'else f'yield from self._service(0x{target:04X})'))
     lines.append(prefix+'return');return
    v=items[pc];op=v['op'];lines.append(prefix+f'self._mark(0x{pc:04X})')
    if op=='DISPATCH':
     t=v['targets'];lines.append(prefix+f'yield from self._dispatch(0x{pc:04X},('+','.join(f'0x{x:04X}'for x in t)+',),('+','.join('self.'+names[x]for x in t)+',))');lines.append(prefix+'return');return
    if op=='RTS':lines.extend((prefix+'self.rts()',prefix+'return'));return
    if op=='RTI':lines.extend((prefix+'self.rti()',prefix+'return'));return
    if op=='JMP':trail=trail+(pc,);pc=v['operand'];continue
    if op in BRANCH:
     a,b=graph[pc];j=join(a,b)
     # Back-edge/exit are structured continue/break inside natural loops.
     if loop_stack:
      h,region,exitpc=loop_stack[-1]
      if a in(h,exitpc)or b in(h,exitpc):j=b if a in(h,exitpc)else a
     bit,positive=BRANCH[op];cond=f'bool(r.p&{bit})'if positive else f'not(r.p&{bit})'
     if a==j:
      lines.append(prefix+f'if not({cond}):');emit(b,j,indent+4,loop_stack,trail+(pc,))
     elif b==j:
      lines.append(prefix+f'if {cond}:');emit(a,j,indent+4,loop_stack,trail+(pc,))
     else:
      lines.append(prefix+f'if {cond}:');emit(a,j,indent+4,loop_stack,trail+(pc,));lines.append(prefix+'else:');emit(b,j,indent+4,loop_stack,trail+(pc,))
     pc=j;continue
    lines.extend(prefix+s for s in statement(v));trail=trail+(pc,);pc=v['next']
   if loop_stack and pc==stop and stop==loop_stack[-1][2]:lines.append(prefix+'break')
  try:
   emit(entry,END,8)
   body=['    def '+names[entry]+'(self):',f'        """Original ${entry:04X}: {notes.get(entry,names[entry])}."""','        r=self.registers;m=self.memory','        yield from () # coroutine carrier; no service completion implied']+lines+['']
  except Exception as exc:
   gaps.append(dict(entry=entry,name=names[entry],error=str(exc)))
   body=['    def '+names[entry]+'(self):',f'        """Explicit unresolved structure at original${entry:04X}."""',f'        yield from self._service(0x{entry:04X},"unresolved_local_structure")','']
  source.append('\n'.join(body));stats.append(dict(entry=entry,name=names[entry],nodes=len(graph)-1,source_locations=sorted(used),gap=any(g['entry']==entry for g in gaps)))
 source.append('    LOCAL_ENTRIES=('+','.join(f'0x{x:04X}'for x in sorted(roots))+',)\n')
 source.append('    def routine(self,entry):\n        methods={'+','.join(f'0x{x:04X}:self.{names[x]}'for x in sorted(roots))+'}\n        yield from methods[entry]()\n')
 result='\n'.join(source);ast.parse(result)
 if generate:(ROOT/'source/recovered/city_officer_details_controller.py').write_text(result)
 out.mkdir(parents=True,exist_ok=True)
 report=dict(rom_sha256=SHA,phase_count=5,dispatch_table_count=len(tables),dispatch_tables=list(tables.values()),routine_count=len(roots),routines=stats,structure_gaps=gaps,code_instruction_count=len(items),inline_words=data,source_SHA256=sha(result.encode()))
 (out/'static-control.json').write_text(json.dumps(report,indent=2)+'\n')
 listing=[]
 for pc,v in sorted(items.items()):
  bank=25;off=16+bank*8192+(pc&8191)
  listing.append(f'{off:06X} b{bank}:${pc:04X} '+('DISPATCH '+','.join(f'${t:04X}'for t in v['targets'])if v['op']=='DISPATCH'else v['op']+' '+v['mode']+' '+f'${v["operand"]:04X}')+'\n')
 (out/'control-analysis.asm').write_text(''.join(listing))
 print(json.dumps(dict(routines=len(roots),instructions=len(items),gaps=gaps[:15],gap_count=len(gaps),source_bytes=len(result))))

def finalize(rom,out):
 from analyze_ui_graphics_initialization import finalize_bundle
 static=json.loads((out/'static-control.json').read_text());assert not static['structure_gaps']
 byte_positions=set();locations=set()
 for line in(out/'control-analysis.asm').read_text().splitlines():
  pc=int(line.split()[1].split(':$')[1],16);locations.add(pc);size=SIZES[OPS[rom[16+25*8192+(pc&8191)]][1]];byte_positions.update(range(pc,pc+size))
 regions=[];start=None;last=None
 for pc in sorted(byte_positions):
  if start is not None and pc!=last+1:regions.append((f'city_card_code_{start:04X}',25,start,last+1,'code'));start=None
  if start is None:start=pc
  last=pc
 if start is not None:regions.append((f'city_card_code_{start:04X}',25,start,last+1,'code'))
 for table in static['dispatch_tables']:regions.append(('five_phase_inline_pointer_table',25,table['start'],table['end'],'inline_pointer_data'))
 for word in static['inline_words']:regions.append(('palette_farcall_inline_target',25,word['start'],word['end'],'inline_far_target_data'))
 observed=set(json.loads((out/'source-executed-locations.json').read_text()));assert observed<=locations
 archives=[str(p.relative_to(ROOT))for p in(ROOT/'analysis/rea/pairs/pair-25/functions').glob('*')if p.stem in('0xafe5','0xb041','0xb086')and p.suffix in('.asm','.c')]
 contracts=dict(APIs=['CityOfficerDetailsController(memory,CityOfficerData.from_rom(rom),services=None)','run_entry(entry=A021,registers)','tick(registers)','__call__(ServiceCall)','resume()'],entry_mapping={'25A021':'4CE5AF→25AFE5','25A01B':'4C64B9→B964, different officer scan and not this UI'},
  phase_table=[dict(phase=i,entry=t,name=n)for i,(t,n)in enumerate(zip(static['dispatch_tables'][0]['targets'],['initialize_city_cards','produce_initial_detail_rows','show_selected_card_and_inputs','produce_adjacent_card','animate_card_transition']))],
  local_closure=dict(start=0xAFE5,end_exclusive=0xB2D7,named_functions=static['routine_count'],original_instruction_locations=len(locations),observed_instruction_locations=len(observed),unobserved=sorted(locations-observed),structure_gaps=[]),
  inputs={'0401':'five phases0..4','0402':'cityID0..29 used to compact original32B city record roster','0408':'selected portrait/list index; changes only at animation completion','040C':'detail producer selected index; may already point at next card while0408 still old','0410..0419':'compact ten officer list; FF empty; actual portrait is0410[0408], row record is0410[040C]','040D':'real ten-row producer cursor0..9,FF complete, busy007E bit2 means no advancement','0081/0083':'actual button/direction bytes; no simulated controller read or ack','0140/0150':'real panel jobs; nonzero0140 postpones notification handling','0409/040A':'two-pixel transition progress and direction','040E/F':'pending equipment CHR shadows committed at original scroll offsets64/16'},
  effects=['phase0 copies palette0 via real inline farcall29A015, compacts city roster17..26 withoutFF slots, initializes row0.',
   'phase1 calls actualB2D7 producer; only040D==FF installs original IRQ/scroll shadows and advances phase2.',
   'phase2 draws selected portrait; up/down initiate next card with original first/last/empty guards; A/B return0400/0401 from0470/0471 when original condition allows.',
   'phase3 calls actual row producer and selected portrait; onlyFF advances phase4.',
   'phase4 positions old/new portraits, advances2pixels, at80 changes0408 and returns phase2. CHR/scroll shadows keep original wrap and timing.',
   '0140/0150 pending message jobs and all007E bits remain real; no fake consumption or PPU completion.'],
  pure_providers={'B2D7':'frozen OfficerDetailsUIServices ten-row producer','CE1F':'frozen PortraitUIServices exact portrait caller','29A015/DBB1':'frozen SceneInitialization real palette copy','EADE':'ControlHelpers exact dispatch stack protocol','F2AF/EE07':'SceneSharedServices exact city pointer/farcall mapper/caller protocol'},
  comparison='All2048RAM including stack residue, all8192SRAM, AXYP/SP/PC, ordered ports,banks; no CPU helper callback or IR fallback.',
  scope='One cooperative city details update, not full frame/PPU upload; original phase11/12 data and services are reused without modifying frozen files.')
 deps=['scripts/analyze_ui_graphics_initialization.py','source/recovered/officer_details_ui_services.py','source/recovered/portrait_ui_services.py','source/recovered/scene_initialization.py','source/recovered/scene_shared_services.py','source/recovered/officer_ui_services.py','source/recovered/battle_nmi_services.py','source/recovered/controller_helpers.py','source/recovered/service_memory.py']
 e,v=finalize_bundle(rom,out,'source/recovered/city_officer_details_controller.py','scripts/verify_city_officer_details_controller.py','scripts/analyze_city_officer_details_controller.py',regions,deps,schema='phase13-city-officer-controller-v1',contracts=contracts,archives=archives)
 assert e['local_instruction_location_total']==len(locations)
 (out/'README.md').write_text(f'''# 阶段13：城市武将资料完整五阶段控制器

真实citymain12从27A04D经selector39 inline21A0调用physical25 `A021→AFE5`。原stub是`4CE5AF`；`A01B→B964`属于其他武将扫描路径，不是本资料UI。源码为12个具名函数、307个原指令位置、5阶段／1个inline分派，静态结构缺口0。不执行ROM、IR或opcode，不借原CPUfallback。

|0401|真实phase|作用|
|---:|---|---|
|0|AFF5|真实palette0、压紧城市10项名册、准备首张卡的row0|
|1|B041|每调用一次真实B2D7 ten-row producer；040D==FF后配置split／scroll进入2|
|2|B086|画当前肖像、上下切换／确认返回、原0140／0150通知任务处理|
|3|B136|画当前肖像并生成相邻资料卡；rowFF后进入4|
|4|B155|旧／新两肖像按方向移动、每次2pixels；80后更新选中index并回2|

portrait索引是`0410[0408]`，资料producer索引是`0410[040C]`。切页动画前后这两个index可不同：040C已指新卡时，0408仍指旧肖像，直到80pixel完成才递增／减。`0410`本身一直是列表第一项，不能把每帧0410直接标成当前显示武将。city32B record的17..26共10槽压紧时跳过FF；上下边界及下一项FF严格依原bytes处理。0083的10/20方向触发两种原切页；左右没有因此自动换武将。

原十行worker是25 `A012→B2D7`，不是AD81。复用冻结OfficerDetailsUIServices全部字段／blank／equipment请求；CE1F复用实际portrait caller；palette0通过真实EE07 farcall／mapper／stack进入29A015→30DBB1。等待007E bit2／0140是原软件状态，源码不清ready。所有PPU／IRQ／CHR变化是原shadow或queue请求，consumer及帧调度由其他真实服务执行。

最终{v['rom_cpu_case_count']}原CPU完整返回病例，另{v['source_guard_case_count']}source guards，0失败；本地执行位置{len(observed)}/{len(locations)}。包括5phase×所有256button bytes×busy状态、全部237武将／关键rows／selected portrait、30城空／稀疏／满名册、10slot首末／空下一项、双向0..80transition／所有关键卡rows、notification0/1/2/9/10/11/127/128/FF与真实panel busy。全部2048RAM（含stack残留）、8192SRAM、AXYP/SP/PC、写端口序与banks比较，source原CPUhelper callback=0。fixture确实准备caller/cache/queue/record条件矩阵，不是native ordinary input证明。

```python
owner = CityOfficerDetailsController(memory, CityOfficerData.from_rom(rom))
result = owner(actual_ServiceCall) #actualphysical25/26 and realRTS frame
# run_entry(0xA021,registers) / tick(registers) are one cooperative update.
```

- [完整具名源码](../../../source/recovered/city_officer_details_controller.py)
- [原CPU矩阵与最终pins](validation.json)
- [原bytes、phase表、字段与合同](evidence.json)
- [原code和明确inlineDATA](original-ranges.asm)
- [静态闭包／5phase](static-control.json)
- [真实原CPU动态位置](executed-instructions.json)
- [冻结十行worker证据](../../phase12/details/evidence.json)
- [冻结肖像服务证据](../../phase12/portraits/evidence.json)

```sh
.venv-trace/bin/python scripts/verify_city_officer_details_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_city_officer_details_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

`--generate-source`只在buildtime重生具名source，之后必须重跑原CPU矩阵。native城市打开／上下切换／返回在独立阶段13runtime域，不计入本模块CPU数；本模块不宣称整帧、完整NES或原始作者源码。
''')
 print(json.dumps(dict(status=v['status'],CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],source=v['source_sha256'],source_locations=f'{len(observed)}/{len(locations)}')))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/city-details');p.add_argument('--generate-source',action='store_true');p.add_argument('--evidence',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();analyze(rom,a.out,a.generate_source)
 if a.evidence:finalize(rom,a.out)
