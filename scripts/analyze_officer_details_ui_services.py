#!/usr/bin/env python3
"""Build-time structured decompilation of the bounded ten-row officer card.

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
HEADER='"""Independent ten-row officer detail packet producer, physical25 A012.\n\nStatic original-byte provenance compiled to named Python if/while/calls.\nNo runtime opcode/IR/program.json or original-CPU fallback is used. Each\ncall genuinely returns to its caller, but a requested packet is not a\ncompleted PPU upload. Real busy queue bytes are never acknowledged here.\n"""\nfrom dataclasses import dataclass\nimport hashlib\nfrom .battle_nmi_services import BattleNMIServices,NMIRegisters,ServiceCall\nfrom .scene_shared_services import SceneSharedServices\nfrom .officer_ui_services import OfficerUIServices\nfrom .controller_helpers import ControlHelpers\nROM_SHA256="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"\nC,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128\n@dataclass(frozen=True)\nclass OfficerDetailsData:\n    rom:bytes\n    @classmethod\n    def from_rom(cls,rom):\n        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError(\'Pinned original ROM required\')\n        return cls(bytes(rom))\nclass SourceBudget(RuntimeError):pass\nclass InvalidDetailRow(ValueError):pass\nclass OfficerDetailsUIServices(BattleNMIServices):\n    FIXED=()\n    def __init__(self,memory,data,services=None):\n        super().__init__(memory,callbacks=self._resolve_service)\n        self.data=data if isinstance(data,OfficerDetailsData)else OfficerDetailsData.from_rom(data)\n        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=services)\n        self.names=OfficerUIServices(memory,self.data.rom,services=services)\n        self.external_services=services;self.controls=ControlHelpers();self.source_locations=[];self.source_budget=100000;self._call_owner=None\n    def _mark(self,pc):\n        self.registers.pc=pc;self.source_locations.append(pc)\n        if len(self.source_locations)>self.source_budget:raise SourceBudget(\'Original detail source operation budget exhausted\')\n    def _shift(self,address,kind):\n        old=self.memory[address];carry=int(bool(self.registers.p&C))\n        self.flag(C,bool(old&128)if kind in (\'asl\',\'rol\')else bool(old&1))\n        self.memory[address]=self.nz((old<<1)|carry if kind==\'rol\'else old<<1 if kind==\'asl\'else (old>>1)|(carry<<7)if kind==\'ror\'else old>>1)\n    def shift_a(self,kind):\n        old=self.registers.a;carry=int(bool(self.registers.p&C))\n        self.flag(C,bool(old&128)if kind in (\'asl\',\'rol\')else bool(old&1))\n        return self.a((old<<1)|carry if kind==\'rol\'else old<<1 if kind==\'asl\'else (old>>1)|(carry<<7)if kind==\'ror\'else old>>1)\n    def _resolve_service(self,call):\n        if call.target==0xF308:result=self.names(call)\n        elif call.target in self.shared.FIXED:result=self.shared(call)\n        elif self.external_services is not None:result=self.external_services(call)\n        else:return dict(status=\'dependency\',reason=\'No independent details helper owns this exact entry\',target=call.target)\n        if not isinstance(result,dict)or result.get(\'status\')!=\'returned\':return dict(status=\'dependency\',body=result)\n        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status=\'dependency\',reason=\'Details helper has not reached actual caller PC/SP\',body=result)\n        return result\n    def _service(self,target,kind=\'tail\',return_pc=None,expected_sp=None):\n        r=self.registers;r.pc=target\n        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535\n        if expected_sp is None:expected_sp=(r.sp+2)&255\n        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,\'banks\',())),expected_sp)\n    def call(self,pc,target,*,inline_return=None):\n        sp=self.registers.sp;word=pc+2;self.push(word>>8);self.push(word)\n        if target in self.LOCAL_ENTRIES:yield from self.routine(target)\n        else:yield from self._service(target,\'call\',inline_return or pc+3,sp)\n        if self.registers.pc!=(inline_return or pc+3)or self.registers.sp!=sp:raise RuntimeError(\'Details call has not returned to its real caller\')\n    def _dispatch(self,pc,targets,methods):\n        index=self.registers.a\n        if not 0<=index<len(targets):raise InvalidDetailRow(\'Only original ten row handlers are proven\')\n        word=pc+2;self.push(word>>8);self.push(word);self.controls(self,0xEADE,targets[index],\'dispatch\')\n        yield from methods[index]()\n    def result(self,status,**extra):\n        value=super().result(status,**extra)\n        return dict(value,source_locations=list(self.source_locations),detail_row=self.memory[0x40D],PPU_jobs=self.memory[0x7E],full_NES_frame=False,PPU_upload_completed=False)\n    def run_entry(self,entry=0xA012,registers=None,*,max_source_operations=100000):\n        if entry not in self.LOCAL_ENTRIES:raise ValueError(\'Entry is outside the original details closure\')\n        if self._program is not None:raise RuntimeError(\'A real details service is pending; resume it first\')\n        if registers is None:raise ValueError(\'Supply actual caller registers and existing RTS frame\')\n        if tuple(getattr(self.memory,\'banks\',())[1:3])!=(25,26):raise ValueError(\'Details requires actual physical25/26 pair\')\n        if entry in(0xA012,0xB2D7,0xB4BF)and not self.memory[0x7E]&4 and 10<=self.memory[0x40D]<128:raise InvalidDetailRow(\'Positive row is outside the legal0..9 domain\')\n        self.source_locations=[];self.source_budget=max_source_operations\n        return self._start(lambda:self.routine(entry),registers,\'officer_details\')\n    def tick(self,registers=None):return self.run_entry(0xA012,registers)\n    def __call__(self,call):\n        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(25,26):return dict(status=\'dependency\',reason=\'No details body owns this exact pair/entry\')\n        if self._program is not None:\n            if self._call_owner is not call:return dict(status=\'dependency\',reason=\'Another caller owns pending details\')\n            result=self.resume()\n        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)\n        if result[\'status\']==\'returned\':\n            self._call_owner=None\n            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status=\'dependency\',reason=\'Details did not reach actualcaller PC/SP\',body=result)\n        return result\n'

def analyze(rom,out,generate):
 assert sha(rom)==SHA
 def get(pc):return rom[16+25*8192+(pc&8191)]
 def word(pc):return get(pc)|get(pc+1)<<8
 tables={}
 for pc in range(0xB2D7,0xB7D9):
  if bytes(get(pc+i)for i in range(3))!=bytes.fromhex('20DEEA'):continue
  start=pc+3;p=start;bound=0xE000;targets=[]
  while p<bound and len(targets)<64:
   t=word(p)
   if not 0xB2D7<=t<0xB7D9:break
   targets.append(t)
   if t>=p+2:bound=min(bound,t)
   p+=2
  assert p==bound,(hex(pc),hex(p),hex(bound))
  tables[pc]=dict(pc=pc,start=start,end=p,targets=targets)
 assert len(tables[0xB4DC]['targets'])==10
 names={0xA012:'public_detail_row',0xB2D7:'produce_next_detail_row',0xB4BF:'populate_detail_values',0xB4F3:'refresh_equipment_CHR_shadows',0xB507:'empty_detail_row',0xB508:'name_diacritic_marks',0xB52D:'name_health_and_de',0xB5A6:'level_iq_loyalty',0xB630:'terrain_affinity_caption_top',0xB64D:'troop_strength_experience_values',0xB719:'put_BCD_high_nibble',0xB71D:'put_BCD_low_nibble',0xB727:'put_decimal_tile',0xB730:'equipment_top_row',0xB770:'equipment_bottom_row',0xB7A2:'copy_equipment_tiles',0xB7C1:'locate_equipment_resource'}
 notes={0xB2D7:'one real32tile request; busy7Ebit2/negative040D return; advance0..9 thenFF',0xB4BF:'selected0410[040C] officer guard<237 andtenrow inline dispatch',0xB508:'copyname39/3A marks withoutadvancingX',0xB52D:'nameglyphs andrecord0体/record4徳',0xB5A6:'record11high4+1 level,record2知,record3忠(100→two32tiles)',0xB630:'record11mid2 affinity captiontop',0xB64D:'affinitybottom,u10troops,record1武,and2*u16experience lowdecimaldigits',0xB730:'equipmenttoptiles/CHRcache',0xB770:'equipmentbottomtiles',0xB4F3:'0401!=3 copies040E/F→BC/BD'}
 roots=set(names)|{x for t in tables.values()for x in t['targets']};items={};queue=deque(roots);data=[]
 while queue:
  pc=queue.popleft()
  while (0xB2D7<=pc<0xB7D9 or pc==0xA012) and pc not in items:
   op,raw_mode=OPS[get(pc)];size=SIZES[raw_mode];mode={'im':'imm','ab':'abs','zp':'zpg','i':'imp','a':'acc','ix':'inx','iy':'iny'}.get(raw_mode,raw_mode);assert op!='?',hex(pc)
   operand=sum(get(pc+i)<<(8*(i-1))for i in range(1,size));nxt=pc+size
   if op in BRANCH:operand=(pc+2+int.from_bytes(bytes((get(pc+1),)),signed=True))&65535
   item=dict(pc=pc,op=op,mode=mode,operand=operand,next=nxt)
   if pc in tables:item['op']='DISPATCH';item['targets']=tables[pc]['targets'];item['next']=None;queue.extend(item['targets'])
   elif op=='JSR'and operand==0xEE07:
    item['op']='FARCALL';item['target']=word(pc+3);item['next']=pc+5;data.append(dict(start=pc+3,end=pc+5,kind='inline_far_target'))
   elif op in ('JSR','JMP')and (0xB2D7<=operand<0xB7D9 or operand==0xA012):
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
 if generate:(ROOT/'source/recovered/officer_details_ui_services.py').write_text(result)
 out.mkdir(parents=True,exist_ok=True)
 report=dict(rom_sha256=SHA,row_count=10,dispatch_table_count=len(tables),dispatch_tables=list(tables.values()),routine_count=len(roots),routines=stats,structure_gaps=gaps,code_instruction_count=len(items),inline_words=data,source_SHA256=sha(result.encode()))
 (out/'static-control.json').write_text(json.dumps(report,indent=2)+'\n')
 listing=[]
 for pc,v in sorted(items.items()):
  bank=25;off=16+bank*8192+(pc&8191)
  listing.append(f'{off:06X} b{bank}:${pc:04X} '+('DISPATCH '+','.join(f'${t:04X}'for t in v['targets'])if v['op']=='DISPATCH'else v['op']+' '+v['mode']+' '+f'${v["operand"]:04X}')+'\n')
 (out/'control-analysis.asm').write_text(''.join(listing))
 print(json.dumps(dict(routines=len(roots),instructions=len(items),gaps=gaps[:15],gap_count=len(gaps),source_bytes=len(result))))

def finalize(rom,out):
 static=json.loads((out/'static-control.json').read_text());v=json.loads((out/'validation.json').read_text());assert v['status']=='passed'and not v['quick']and v['failed_count']==0
 def pin(path):
  p=ROOT/path;return dict(path=path,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
 source=pin('source/recovered/officer_details_ui_services.py');validator=pin('scripts/verify_officer_details_ui_services.py')
 assert source['sha256']==v['source_sha256']==static['source_SHA256'];assert validator['sha256']==v['validator_sha256']
 def ranged(name,bank,start,end,kind='data'):
  offset=16+bank*8192+(start&8191);raw=rom[offset:offset+end-start]
  return dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=sha(raw),kind=kind)
 regions={};original_locations=[]
 for line in(out/'control-analysis.asm').read_text().splitlines():
  pc=int(line.split()[1].split(':$')[1],16);size=SIZES[OPS[rom[16+25*8192+(pc&8191)]][1]];original_locations.append(pc)
  for i in range(pc,pc+size):regions[i]='code'
 for t in static['dispatch_tables']:
  for i in range(t['start'],t['end']):assert i not in regions;regions[i]='inline_row_pointer_data'
 for start,end in((0xB385,0xB399),(0xB399,0xB4B9),(0xB4B9,0xB4BF),(0xB647,0xB64D),(0xB713,0xB719)):
  for i in range(start,end):assert i not in regions;regions[i]='immutable_detail_data'
 ranges=[ranged('public_A012_trampoline',25,0xA012,0xA015,'code')];start=0xB2D7;index=0
 while start<0xB7D9:
  kind=regions.get(start,'original_unreached_bytes');end=start+1
  while end<0xB7D9 and regions.get(end,'original_unreached_bytes')==kind:end+=1
  ranges.append(ranged(f'details_{kind}_{index:02d}',25,start,end,kind));start=end;index+=1
 tables=[ranged('row_template10_pointers',25,0xB385,0xB399),ranged('nine_original32tile_templates',25,0xB399,0xB4B9),
  ranged('mod3_card_slot_destinations',25,0xB4B9,0xB4BF),ranged('tenrow_inline_dispatch',25,0xB4DF,0xB4F3),
  ranged('three_affinity_top_glyph_pairs',25,0xB647,0xB64D),ranged('three_affinity_bottom_glyph_pairs',25,0xB713,0xB719),
  ranged('names237_tenbyte_records',16,0x901A,0x995C),ranged('equipment32_resource_pointers',16,0x9B12,0x9B52),ranged('equipment32_seventeenbyte_records',16,0x9B52,0x9D72),ranged('name_alignment9_values',31,0xF35F,0xF368)]
 context=[ranged('actual_battle_info_controller_and_far_words',12,0xA21B,0xA293,'caller_context'),ranged('fixed_F308_pure_provider',31,0xF308,0xF35F,'source_dependency_context')]
 fields=[
  dict(row=0,handler=0xB508,label='姓名浊点/半浊点',record_offsets=None,outputs=['038A+alignment'],behavior='F308 name codes39/3A; normal glyphs advanceX, marks do not.'),
  dict(row=1,handler=0xB52D,label='姓名／体／徳',record_offsets=[0,4],outputs=['038B+alignment','0398..0399','039E..039F'],behavior='Name skips39/3A marks; body andde each two decimaltiles; leadingtens blank.'),
  dict(row=2,handler=0xB507,label='模板空行',record_offsets=[],outputs=[],behavior='OriginalRTS; only32tiletemplate queued.'),
  dict(row=3,handler=0xB5A6,label='等级／知／忠',record_offsets=[11,2,3],outputs=['0391','0398..0399','039E..039F'],behavior='(byte11>>4)+1 displayedlowdecimaldigit; IQ two digits; loyalty100→twooriginaltile32, others two digits.'),
  dict(row=4,handler=0xB630,label='地形适性字形上半',record_offsets=[11],outputs=['038B..038C'],behavior='(byte11>>2)&3;0..2 formal平/山/水;code3 readsadjacentoriginalbytes andisnotnamed.'),
  dict(row=5,handler=0xB64D,label='地形适性下半／兵／武／経',record_offsets=[11,8,9,1,6,7],outputs=['038B..038C','0390..0393','0398..0399','039D..039F'],behavior='troops=byte8|((byte9&3)<<8), high6excluded;experience doubledas24bit then lowtwodecimaldigits omitted, equivalentfloor(u16XP/50).'),
  dict(row=6,handler=0xB730,label='武器／防具字形上半和CHR缓存准备',record_offsets=[10],outputs=['038E..0395','039A..03A1','040E','040F'],behavior='weapon=byte10&31, armor=(byte10>>5)+24. F25F48→physical16. Eachrecord byte0 CHRpage;top8glyphs offset1. Armortileoffset40 exceptblanktile01.'),
  dict(row=7,handler=0xB770,label='武器／防具字形下半',record_offsets=[10],outputs=['038E..0395','039A..03A1'],behavior='Same resourceoffset9, then originalselector49→physical17 datawindow restored.'),
  dict(row=8,handler=0xB4F3,label='资料装备CHR shadow提交',record_offsets=[],outputs=['00BC','00BD'],behavior='When0401!=3 copy040E/F→BC/BD; mode3 leaves shadows untouched. Originalblanktemplate stillqueued.'),
  dict(row=9,handler=0xB507,label='最后空行及终止',record_offsets=[],outputs=['040D'],behavior='Producer afterhandler increments040D from9to10 then storesFF. No PPU acknowledgement.'),
 ]
 deps=v['dependency_pins']+[pin('scripts/verify_officer_details_ui_services.py'),pin('scripts/analyze_officer_details_ui_services.py')]
 imported=[n.module for n in ast.walk(ast.parse((ROOT/source['path']).read_text()))if isinstance(n,ast.ImportFrom)]
 assert not any(p in('py65','runtime_services','battle_state_machine','duel_state_machine')for p in imported)
 observed=json.loads((out/'source-executed-locations.json').read_text());assert set(observed)<=set(original_locations)
 archives=[pin(str(p.relative_to(ROOT)))for p in(ROOT/'analysis/rea/pairs/pair-25/functions').glob('*')if p.stem in('0xb2d7','0xb4bf')and p.suffix in('.asm','.c')]
 listing=[]
 for item in ranges+tables+context:
  listing.append(f'; {item["name"]} b{item["physical_bank"]}:${item["cpu_start"]:04X} file0x{item["rom_offset"]:06X} {item["kind"]}\n')
  if item['kind']=='code':listing.append(disassemble(rom,25,0xA000,item['cpu_start'],item['cpu_end_exclusive']))
  else:
   raw=bytes.fromhex(item['raw_hex'])
   for i in range(0,len(raw),16):listing.append(f'{item["rom_offset"]+i:06X} ${item["cpu_start"]+i:04X} .byte '+','.join(f'${b:02X}'for b in raw[i:i+16])+'\n')
 (out/'original-ranges.asm').write_text(''.join(listing))
 evidence=dict(schema='phase12-officer-details-v1',rom_sha256=SHA,ROM_modified=False,ranges=ranges,tables=tables,caller_and_dependency_context=context,dependency_pins=deps,REA_archive=archives,disassembly_pin=pin(str((out/'original-ranges.asm').relative_to(ROOT))),
  APIs=['OfficerDetailsUIServices(memory,OfficerDetailsData.from_rom(rom),services=None)','run_entry(entry=A012,registers)','tick(registers)','__call__(ServiceCall)','resume()'],
  source_runtime_IR=False,source_runtime_CPU=False,source_runtime_opcode_decode=False,source_AST_imports=imported,source_original_CPU_callbacks=0,
  bounded_closure=dict(public_trampoline=0xA012,body_start=0xB2D7,end_exclusive=0xB7D9,functions=static['routine_count'],instruction_location_total=len(original_locations),instruction_location_observed=len(observed),unobserved_locations=sorted(set(original_locations)-set(observed)),structure_gaps=static['structure_gaps']),
  row_field_mapping=fields,input_fields={'040D':'signedproducerrow0..9;negativeearlyRTS','040C':'selectedindex into0410 list;indexmod3selects320byteNAMETablecard slot','0410+040C':'officerID;FE usesallblanktemplate;>=EDskipsdynamicfields','0401':'mode3preventsrow8CHRshadowcommit','007Ebit2':'realmapcommandpending;earlyRTSwithoutadvancerow'},
  packet_contract='One original32tile template;0380=20 command,0381/2=word base[2400,2540,2680][040C%3]+040D*32,0383..03A2 data,03A3=FF;007E|4 preservingotherbits.',
  sentinel_contract='040Dnegative leavespacket unchanged;busy7Ebit2 returnsbeforezeroing01. FE selectsblanktemplate for everyrow; otherinvalidIDs preservelabels butskiprecordoverlays. Positive040D10..127 unproven andsourceguardrejectswhennotbusy.',
  source_providers={'F308':'OfficerUIServices actualnamepointer/alignment andmapper/callerflags','EA7C/E9BA/F2D7/F25F':'SceneSharedServices actualpuredivision/packedBCD/recordpointer/mapper','EADE':'ControlHelpers exactinline pointer dispatch'},
  validation={k:v[k]for k in('status','rom_cpu_case_count','original_complete_case_count','original_prefix_case_count','source_guard_case_count','failed_count','counts','comparison','pure_recovered_helper_call_counts')},
  scope='Complete bounded tenrowproducer andlocalvalueclosure. Doesnot consume0380 requests, mutateofficerrecords, DMAOAM, uploadpalette, fabricatePPUcompletion or emulateframes.',
  native_status='Originalcore opens/details/return proof belongs separatephase12native capture; CPUfixturematrix isnot nativeframe trace.')
 (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');v['evidence_sha256']=sha((out/'evidence.json').read_bytes());v['dependency_pins']=deps;v['instruction_location_total']=len(original_locations);v['instruction_location_observed']=len(observed);(out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 rows=['| 原row | 真实入口 | 显示／作用 | recordbyte |','|---:|---|---|---|']+[f'|{f["row"]}|`${f["handler"]:04X}`|{f["label"]}|{f["record_offsets"]}|'for f in fields]
 readme=f'''# Phase12 十行武将资料实际服务

战场main1/sub1 `$A244`先经selector39调用25A000肖像，随后真正调用25A012→B2D7资料producer。25A003→A033是年月／势力controller；25A006→C773是AI城市指令分派；25A030→BB73是城市金粮等word结转，均不能称属性页。29A030/A03C是姓名包而不是完整参数卡。

`OfficerDetailsUIServices`是有界独立具名Python：17函数、439原指令位置、1个十项inline分派，全部静态structuregaps为空。运行时只执行普通if/while和具名sourcecall，不解释opcode/IR/program.json，不用原CPUfallback。F308委托独立OfficerUIServices真namepointer／alignment；EA7C、E9BA、F2D7、F25F委托SceneSharedServices精确puremath／mapper；EADE复用ControlHelpers。不是语义textcallback冒充AXYP。

{chr(10).join(rows)}

选择`0410[040C]`；`040D`是本卡的0..9行游标。目的地址是`[2400,2540,2680][040C%3]+32*040D`，即NAMETable中三个相隔十行的卡片资料槽，不按名称猜成水平三列。原0380命令20（32tiles）、0381/2地址、0383..03A2行内容、03A3=FF；007E只OR4并保留其他请求。若bit2已置位，直接真实RTS、不写row／packet；040D负值也真实早退。row9返回后游标存FF。源码不会清bit2、伪完成PPU或偷偷推进到下一行。

ID FE使所有行选原空白模板；ID≥ED跳过动态record叠加，其他无效ID仍可保留行标题。row0/1姓名用真正10byte原name记录、39/3Amarks及原alignment；与13byte汉字图身份表用途不同。知／忠／体／徳使用两十进制数字、首零留模板空白，忠100特殊输出两个原32tile；等级展示byte11high4+1的低十进制位。兵是低10bit字段，byte9high6不参与数字；経是原u16乘2后的高三位显示，等价floor(XP/50)，不改永久经验。

row4/5 affinity选择byte11mid2，前三编码原平／山／水，编码3读相邻原bytes不赋正式名。装备low5武器selector与high3防具selector+24，映射physical16的32个17byte资源record；byte0是CHR页、后16字节为上／下各8tiles，防具tile加40但空白01保持。row6准备040E/F，row8若0401!=3提交BC/BD；mode3不提交。row7已将数据窗恢复selector49→physical17。没有立即硬件CHR／palette上传。

最终{v['rom_cpu_case_count']}原CPU完整返回病例、另{v['source_guard_case_count']}sourceguards，0失败；动态观察{len(observed)}/{len(original_locations)}本地原指令位置，不等于全部输入组合或整个NES帧已验证。覆盖全部237武将×十行×真实busy／available、FE／FF与负row、mod3卡槽、原SP边界、100忠特殊值、u10high6／u16XP、全部packedbyte11／全部装备byte10、mode3缓存、全部17localentry。全部2048RAM（包括stack残留）、8192SRAM、AXYP/SP/PC、端口序与mapper对照，生产原CPU helper callback=0。fixture明确准备record／row／queue字节作CPU条件矩阵，不冒充普通原游戏输入。重复producer调用保留queuedrow的guard单列；源码不替代真实consumer。

```python
owner = OfficerDetailsUIServices(memory, OfficerDetailsData.from_rom(rom))
result = owner(actual_ServiceCall)  #actualphysical25/26 + existingcallerframe
# run_entry(0xA012,actual_registers)或tick(actual_registers)
```

- [独立完整具名源码](../../../source/recovered/officer_details_ui_services.py)
- [最终CPU矩阵／guards／pins](validation.json)
- [十行字段、完整原bytes和服务合同](evidence.json)
- [原code／明确data／callercontext](original-ranges.asm)
- [静态闭包与inline分派](static-control.json)
- [原CPU实际位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_officer_details_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_officer_details_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

`--generate`只在buildtime从原bytes重生source，之后必须重跑矩阵冻结pins。原core实际打开／返回／截图在单独native证据域，未包含于这里的CPU计数。
''';(out/'README.md').write_text(readme)
 print(json.dumps(dict(status='passed',CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],locations=f'{len(observed)}/{len(original_locations)}',source_sha256=source['sha256'],validator_sha256=validator['sha256'],evidence_sha256=v['evidence_sha256'])))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase12/details');p.add_argument('--generate',action='store_true');p.add_argument('--evidence',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();analyze(rom,a.out,a.generate)
 if a.evidence:finalize(rom,a.out)


