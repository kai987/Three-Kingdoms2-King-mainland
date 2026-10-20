#!/usr/bin/env python3
"""Build-time structured decompilation of five-phase title intro graphics.

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
HEADER='"""Independent five-phase title intro graphics, physical23 A021.\n\nStatic original-byte provenance compiled to named Python if/while/calls.\nNo runtime opcode/IR/program.json or original-CPU fallback is used. Each\ncall genuinely returns to its caller, but a requested packet is not a\ncompleted PPU upload. Real busy queue bytes are never acknowledged here.\n"""\nfrom dataclasses import dataclass\nimport hashlib\nfrom .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall\nfrom .scene_shared_services import SceneSharedServices\nfrom .controller_helpers import ControlHelpers\nROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"\nC,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128\n@dataclass(frozen=True)\nclass TitleIntroData:\n    rom:bytes\n    @classmethod\n    def from_rom(cls,rom):\n        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError(\'Pinned original ROM required\')\n        return cls(bytes(rom))\nclass SourceBudget(RuntimeError):pass\nclass InvalidTitleIntroPhase(ValueError):pass\nclass TitleIntroGraphics(BattleNMIServices):\n    FIXED=()\n    def __init__(self,memory,data,services=None):\n        super().__init__(memory,callbacks=self._resolve_service)\n        self.data=data if isinstance(data,TitleIntroData)else TitleIntroData.from_rom(data)\n        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=self._resolve_service)\n        self.external_services=services;self.controls=ControlHelpers();self.source_locations=[];self.source_budget=100000;self._call_owner=None\n    def _mark(self,pc):\n        self.registers.pc=pc;self.source_locations.append(pc)\n        if len(self.source_locations)>self.source_budget:raise SourceBudget(\'Original title intro source operation budget exhausted\')\n    def _shift(self,address,kind):\n        old=self.memory[address];carry=int(bool(self.registers.p&C))\n        self.flag(C,bool(old&128)if kind in (\'asl\',\'rol\')else bool(old&1))\n        self.memory[address]=self.nz((old<<1)|carry if kind==\'rol\'else old<<1 if kind==\'asl\'else (old>>1)|(carry<<7)if kind==\'ror\'else old>>1)\n    def shift_a(self,kind):\n        old=self.registers.a;carry=int(bool(self.registers.p&C))\n        self.flag(C,bool(old&128)if kind in (\'asl\',\'rol\')else bool(old&1))\n        return self.a((old<<1)|carry if kind==\'rol\'else old<<1 if kind==\'asl\'else (old>>1)|(carry<<7)if kind==\'ror\'else old>>1)\n    def _resolve_service(self,call):\n        if call.target in self.shared.FIXED:result=self.shared(call)\n        elif self.external_services is not None:result=self.external_services(call)\n        else:return dict(status=\'dependency\',reason=\'No independent title intro helper owns this exact entry\',target=call.target)\n        if not isinstance(result,dict)or result.get(\'status\')!=\'returned\':return dict(status=\'dependency\',body=result)\n        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status=\'dependency\',reason=\'Title intro helper has not reached actual caller PC/SP\',body=result)\n        return result\n    def _service(self,target,kind=\'tail\',return_pc=None,expected_sp=None):\n        r=self.registers;r.pc=target\n        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535\n        if expected_sp is None:expected_sp=(r.sp+2)&255\n        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,\'banks\',())),expected_sp)\n    def call(self,pc,target,*,inline_return=None):\n        sp=self.registers.sp;word=pc+2;self.push(word>>8);self.push(word)\n        if target in self.LOCAL_ENTRIES:yield from self.routine(target)\n        else:yield from self._service(target,\'call\',inline_return or pc+3,sp)\n        if self.registers.pc!=(inline_return or pc+3)or self.registers.sp!=sp:raise RuntimeError(\'Title intro call has not returned to its real caller\')\n    def _dispatch(self,pc,targets,methods):\n        index=self.registers.a\n        if not 0<=index<len(targets):raise InvalidTitleIntroPhase(\'Only original five title-intro phases are proven\')\n        word=pc+2;self.push(word>>8);self.push(word);self.controls(self,0xEADE,targets[index],\'dispatch\')\n        yield from methods[index]()\n    def result(self,status,**extra):\n        value=super().result(status,**extra)\n        return dict(value,source_locations=list(self.source_locations),intro_phase=self.memory[0x541],intro_timer=self.memory[0x544],PPU_jobs=self.memory[0x7E],full_NES_frame=False,PPU_upload_completed=False)\n    def run_entry(self,entry=0xA021,registers=None,*,max_source_operations=100000):\n        if entry not in self.LOCAL_ENTRIES:raise ValueError(\'Entry is outside the original title intro closure\')\n        if self._program is not None:raise RuntimeError(\'A real title intro service is pending; resume it first\')\n        if registers is None:raise ValueError(\'Supply actual caller registers and existing RTS frame\')\n        if tuple(getattr(self.memory,\'banks\',())[1:3])!=(23,24):raise ValueError(\'Title intro requires actual physical23/24 pair\')\n        if entry in(0xA021,0xDE25)and self.memory[0x541]>=5:raise InvalidTitleIntroPhase(\'Legal title-intro phases are0..4\')\n        if (entry in(0xA021,0xDE25)and self.memory[0x541]==1 and not self.memory[0x81]&8 or entry==0xDE66)and self.memory[0x543]>=24:raise ValueError(\'Original intro sequence positions are0..23\')\n        if entry==0xDEFA and registers.a>=15:raise ValueError(\'Original intro frame IDs are0..14\')\n        self.source_locations=[];self.source_budget=max_source_operations\n        return self._start(lambda:self.routine(entry),registers,\'title_intro_graphics\')\n    def tick(self,registers=None):return self.run_entry(0xA021,registers)\n    def __call__(self,call):\n        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(23,24):return dict(status=\'dependency\',reason=\'No title intro body owns this exact pair/entry\')\n        if self._program is not None:\n            if self._call_owner is not call:return dict(status=\'dependency\',reason=\'Another caller owns pending title intro\')\n            result=self.resume()\n        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)\n        if result[\'status\']==\'returned\':\n            self._call_owner=None\n            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status=\'dependency\',reason=\'Title intro did not reach actualcaller PC/SP\',body=result)\n        return result\n'

def analyze(rom,out,generate):
 assert sha(rom)==SHA
 def get(pc):return rom[16+(23 if pc<0xC000 else 24)*8192+(pc&8191)]
 def word(pc):return get(pc)|get(pc+1)<<8
 tables={}
 for pc in range(0xDE25,0xDF15):
  if bytes(get(pc+i)for i in range(3))!=bytes.fromhex('20DEEA'):continue
  start=pc+3;p=start;bound=0xE000;targets=[]
  while p<bound and len(targets)<64:
   t=word(p)
   if not 0xDE25<=t<0xDF15:break
   targets.append(t)
   if t>=p+2:bound=min(bound,t)
   p+=2
  assert p==bound,(hex(pc),hex(p),hex(bound))
  tables[pc]=dict(pc=pc,start=start,end=p,targets=targets)
 assert len(tables[0xDE37]['targets'])==5
 names={0xA021:'public_title_intro',0xDE25:'title_intro_phase_dispatch',0xDE44:'intro_delay',0xDE66:'advance_intro_frames',0xDEB9:'hold_intro_frame',0xDEC7:'blacken_intro_palette',0xDED6:'finish_intro_sequence',0xDEFA:'draw_intro_frame'}
 notes={0xDE25:'start button forces original phase3, otherwise fivephase inline dispatch',0xDE44:'incrementtimer, after32ticks palette andtwoframe dwell',0xDE66:'advance24-entry originalframe sequence, play original audio atindex20',0xDEB9:'hold originalframe8 untiltimer reaches0',0xDEC7:'blacken three palette bytes andadvancephase',0xDED6:'advance0540, clearphase/timer/scratch andreset/request originalaudioB0',0xDEFA:'physical1 sprite descriptor lookup and realF1AD caller'}
 roots=set(names)|{x for t in tables.values()for x in t['targets']};items={};queue=deque(roots);data=[]
 while queue:
  pc=queue.popleft()
  while (0xDE25<=pc<0xDF15 or pc==0xA021) and pc not in items:
   op,raw_mode=OPS[get(pc)];size=SIZES[raw_mode];mode={'im':'imm','ab':'abs','zp':'zpg','i':'imp','a':'acc','ix':'inx','iy':'iny'}.get(raw_mode,raw_mode);assert op!='?',hex(pc)
   operand=sum(get(pc+i)<<(8*(i-1))for i in range(1,size));nxt=pc+size
   if op in BRANCH:operand=(pc+2+int.from_bytes(bytes((get(pc+1),)),signed=True))&65535
   item=dict(pc=pc,op=op,mode=mode,operand=operand,next=nxt)
   if pc in tables:item['op']='DISPATCH';item['targets']=tables[pc]['targets'];item['next']=None;queue.extend(item['targets'])
   elif op=='JSR'and operand==0xEE07:
    item['op']='FARCALL';item['target']=word(pc+3);item['next']=pc+5;data.append(dict(start=pc+3,end=pc+5,kind='inline_far_target'))
   elif op in ('JSR','JMP')and (0xDE25<=operand<0xDF15 or operand==0xA021):
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
 if generate:(ROOT/'source/recovered/title_intro_graphics.py').write_text(result)
 out.mkdir(parents=True,exist_ok=True)
 report=dict(rom_sha256=SHA,phase_count=5,dispatch_table_count=len(tables),dispatch_tables=list(tables.values()),routine_count=len(roots),routines=stats,structure_gaps=gaps,code_instruction_count=len(items),inline_words=data,source_SHA256=sha(result.encode()))
 (out/'static-control.json').write_text(json.dumps(report,indent=2)+'\n')
 listing=[]
 for pc,v in sorted(items.items()):
  bank=23 if pc<0xC000 else 24;off=16+bank*8192+(pc&8191)
  listing.append(f'{off:06X} b{bank}:${pc:04X} '+('DISPATCH '+','.join(f'${t:04X}'for t in v['targets'])if v['op']=='DISPATCH'else v['op']+' '+v['mode']+' '+f'${v["operand"]:04X}')+'\n')
 (out/'control-analysis.asm').write_text(''.join(listing))
 print(json.dumps(dict(routines=len(roots),instructions=len(items),gaps=gaps[:15],gap_count=len(gaps),source_bytes=len(result))))

def finalize(rom,out):
 from analyze_ui_graphics_initialization import finalize_bundle
 static=json.loads((out/'static-control.json').read_text());assert not static['structure_gaps']
 byte_positions={};locations=set()
 for line in(out/'control-analysis.asm').read_text().splitlines():
  bank=int(line.split()[1].split(':')[0][1:]);pc=int(line.split()[1].split(':$')[1],16);locations.add((bank,pc));size=SIZES[OPS[rom[16+bank*8192+(pc&8191)]][1]]
  for addr in range(pc,pc+size):byte_positions[(bank,addr)]=True
 regions=[];start=None;last=None;lastbank=None
 for bank,pc in sorted(byte_positions):
  if start is not None and(bank!=lastbank or pc!=last+1):regions.append((f'title_intro_code_{lastbank}_{start:04X}',lastbank,start,last+1,'code'));start=None
  if start is None:start=pc
  last=pc;lastbank=bank
 if start is not None:regions.append((f'title_intro_code_{lastbank}_{start:04X}',lastbank,start,last+1,'code'))
 for table in static['dispatch_tables']:regions.append(('five_phase_inline_pointer_table',24,table['start'],table['end'],'inline_pointer_data'))
 regions.extend([('original24_frame_sequence_andFF_terminator',24,0xDEA0,0xDEB9,'data'),('sprite_descriptor15_pointer_table',1,0x97EF,0x980D,'data')])
 descriptors=[]
 for frame in range(15):
  off=16+8192+(0x97EF&8191)+2*frame;p=int.from_bytes(rom[off:off+2],'little');cursor=p
  while True:
   offset=16+8192+(cursor&8191)
   if rom[offset]==128:break
   cursor+=4;assert cursor-p<1024
  regions.append((f'original_intro_sprite_frame{frame}',1,p,cursor+1,'sprite_data'))
  descriptors.append(dict(frame=frame,pointer=p,sprite_count=(cursor-p)//4,terminator=128))
 observed=set(json.loads((out/'source-executed-locations.json').read_text()));assert observed=={pc for b,pc in locations}
 contract=dict(APIs=['TitleIntroGraphics(memory,TitleIntroData.from_rom(rom),services=None)','run_entry(entry=A021,registers)','tick(registers)','__call__(ServiceCall)','resume()'],
  entry_mapping={'23A021':'4C25DE→24DE25','10D72A':'original titlemain0 caller,far selector37;0541 belongs this service'},
  phases=[dict(phase=i,entry=t,name=n)for i,(t,n)in enumerate(zip(static['dispatch_tables'][0]['targets'],['intro_delay','advance_intro_frames','hold_intro_frame','blacken_intro_palette','finish_intro_sequence']))],
  local_closure=dict(functions=8,original_code_locations=86,observed_code_locations=len(observed),structure_gaps=[]),original_sprite_descriptors=descriptors,
  inputs={'0081bit3':'originalStart skip requests phase3 before handling','0541':'phase0..4','0543':'frame sequence cursor0..23;not formal animation name','0544':'byte timer, including original increment/decrement wrap','007C':'actual OAM cursor;FF meansfull','data_window':'physical1 sprite pointer resources selected byF25F33 inphase1;caller retains data window forphase2'},
  effects=['phase0 increments0544; threshold32 writes0115=16,0116=30,0543=0,0544=2,phase++.','phase1 atindex20 requests62hex throughE693, mapsdata1, drawsDEA0[index]; timer0underflows255; reaching0 resets2/advancesindex. NextFF advancesphase2 andsets64tick hold.','phase2 decrements timer; nonzero drawsframe8; zero advancesphase3.','phase3 advancesphase thenwrites0115..0117=0F.','phase4 advances0540,clears0541/0544/0470/0471,setsCE=B0/D6=04,executesrealE57F resetandE673 B0hex request.'],
  audio={'E693(62hex)':'3consecutive descriptors98..100','E57F':'actual APU/N163 resetsand7descriptor requests','E673(B0hex)':'7consecutive descriptors176..182'},
  providers={'F1AD':'frozenSceneSharedServices/BattleGraphicsServices screenOAM producer; actualRTS frame isconsumed bysource adapter','F25F':'real mapper data window request','EADE':'exactControlHelpers inline dispatch and actualstack','E693/E57F/E673':'frozenAudioServices independentrequest/reset algorithms; body AXYP contract andactualSharedRTS'},
  RAM_scope='Fixed1972 addresses0000..01B3 plus0200..07FF,includingpalette0100..013F andunit01B0..01B3. Additionally every actual caller-owned stackbyte entrySP+1..1FF iscompared;2..12bytes inthismatrix,1974..1984total. Inactive stack01B4..entrySP residuals areexcluded underfrozenAudioServices semanticcontract.',
  boundaries='ExactAXYP/SP/PC,all8192SRAM,orderedAPU/N163/PRGports andfinalbanks. NoIRQ/frame timing, NMI execution,DMA,pixel/PPUupload,PCM synthesis orfake queue ack.')
 deps=['scripts/analyze_ui_graphics_initialization.py','source/recovered/scene_shared_services.py','source/recovered/audio_services.py','source/recovered/battle_graphics_services.py','source/recovered/battle_nmi_services.py','source/recovered/controller_helpers.py','source/recovered/service_memory.py']
 archives=[str(p.relative_to(ROOT))for p in(ROOT/'analysis/rea/pairs/pair-23/functions').glob('*')if p.stem in('0xde25','0xdefa')and p.suffix in('.asm','.c')]
 e,v=finalize_bundle(rom,out,'source/recovered/title_intro_graphics.py','scripts/verify_title_intro_graphics.py','scripts/analyze_title_intro_graphics.py',regions,deps,schema='phase13-title-intro-graphics-v1',contracts=contract,archives=archives)
 (out/'README.md').write_text(f'''# 阶段13：标题开场五阶段图形服务

原10D72A（titlemain0）经EE07 selector37调用physical23 `A021→24DE25`，原stub `4C25DE`。它是五阶段开场timer／OAM／palette／音频请求服务，不是整帧图形仿真。独立TitleIntroGraphics为8个具名函数、86个原指令位置、1个五项inline分派；全部本地位置动态执行86/86，静态结构缺口0。源码不解释opcode、IR或program.json，不执行原CPUfallback，也不调用未知callback假RTS。

|0541|原入口|作用|
|---:|---|---|
|0|DE44|0544递增，达到32后准备palette／cursor0／每帧停留2ticks|
|1|DE66|原24项frame序列；cursor20发E693(62hex)；F25F33／F1AD真实OAM；遇FF进入64ticks停留|
|2|DEB9|timer递减，非零继续frame8；零进3|
|3|DEC7|phase++，0115..0117变0F|
|4|DED6|0540++、清phase/timer等、真实E57Freset和E673(B0hex)请求|

0081bit3原Start使phase3先执行，且本调用结束后phase4；不能写成立即跳完全部初始化。原byte timer0的递减／FF的递增保持wrap。原序列是24个frame索引加FF终止，映射15个原sprite descriptor；每项4byte sprite（Y/tile/attribute/X）以80终止，本证据pin所有真实descriptor，而非根据屏幕猜动画名称。

复用已冻结SceneSharedServices、BattleGraphicsServices和AudioServices纯源码。F1AD构造OAM RAM，F25F写真实E000端口；E57F有原APU/N163复位写，E693从ID62hex请求3个连续descriptor，结束E673(B0hex)请求7个连续descriptor。请求／OAM并不等于硬件DMA、声音PCM或像素渲染完成。

最终{v['rom_cpu_case_count']}原CPU完整返回病例、另{v['source_guard_case_count']}sourceguards，0失败。覆盖5phase×3原button条件×8timer边界×24cursor、24cursor×7OAM容量、3真实SP／flags边界。准确比较范围为固定1972RAM地址`0000..01B3`和`0200..07FF`，包含palette0100..013F和单位缓冲；另逐字节比较实际调用方拥有的`entrySP+1..1FF`，本矩阵2..12bytes、合计1974..1984RAM。共享音频模块从phase10起已明确排除其inactive CPU stack残留，本服务保持该合同，不stamp残留来假装all2048。AXYP/SP/PC、8192SRAM、所有端口写序和mapper banks保持精确比较。

```python
owner = TitleIntroGraphics(memory, TitleIntroData.from_rom(rom))
result = owner(actual_ServiceCall) #actual23/24pair andrealRTS frame
```

- [独立完整具名源码](../../../source/recovered/title_intro_graphics.py)
- [原CPU矩阵、明确RAM地址与pins](validation.json)
- [code、inline／sequence／sprite data与服务合同](evidence.json)
- [原字节和明确data](original-ranges.asm)
- [原CPU实际执行位置](executed-instructions.json)
- [静态五phase闭包](static-control.json)

```sh
.venv-trace/bin/python scripts/verify_title_intro_graphics.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_title_intro_graphics.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

完整服务返回不等于完整NES帧；source硬件等待／未知callee仍须实际服务，不提供ready或IRQ虚假完成。
''')
 print(json.dumps(dict(status=v['status'],CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],source=v['source_sha256'],scope=contract['RAM_scope'])))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/title-intro');p.add_argument('--generate-source',action='store_true');p.add_argument('--evidence',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();analyze(rom,a.out,a.generate_source)
 if a.evidence:finalize(rom,a.out)
