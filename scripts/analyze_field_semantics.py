#!/usr/bin/env python3
"""Offline whole-PRG instruction atlas, conservative CFG/Y/pointer field search.

All32 physical banks are inspected. Known instruction starts are gathered from
frozen static graphs and original-CPU execution catalogues; raw candidates are
separately labelled unclassified, never promoted to code just by matching bytes.
Negative findings apply only to the resolved instruction/dataflow domain.
"""
from pathlib import Path
from collections import Counter,deque
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES,instruction
from source.recovered.field_semantics import ROM_SHA256,affinity_code
OUT=ROOT/'analysis/phase16/fields';SOURCE=ROOT/'source/recovered/field_semantics.py'
PORTABLE=OUT/'provenance/manifest.json'
RANGES=[(25,0xB630,0xB647,'upper_affinity_glyph_complete'),(25,0xB64D,0xB663,'lower_affinity_glyph_prefix'),
 (12,0xA7E7,0xA823,'player_movement_quote'),(8,0xA796,0xA7CD,'AI_movement_quote_suffix'),
 (15,0xCB2F,0xCB59,'attack_terrain_affinity_suffix'),(15,0xD102,0xD1B0,'formation_parameters'),
 (13,0xDD2F,0xDD72,'unit_affinity_cache'),(13,0xDB03,0xDB46,'hundred_troop_cache'),
 (10,0xBD95,0xBDA3,'city_overlap_word_reference')]
TABLES=[(25,0xB647,6,'upper_three_glyph_pairs'),(25,0xB713,6,'lower_three_glyph_pairs'),
 (12,0xA823,28,'player_first_movement_table'),(12,0xA83F,28,'player_second_movement_table'),
 (8,0xA7CD,28,'AI_first_movement_table'),(8,0xA7E9,28,'AI_second_movement_table'),
 (15,0xCBE9,4,'terrain_match_first'),(15,0xCBED,4,'terrain_match_second'),
 (15,0xD1B0,24,'three_affinity_formation_rows'),(15,0xD1C8,16,'adjoining_formation_parameter_records')]
ZP=(0,1,2,3,0x10,0x11,0x20,0x21,0x22,0x23,0x40,0x41)
UNKNOWN=None;EMPTY=(None,None,None,tuple(None for _ in ZP))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,d): (OUT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def num(v):
 if isinstance(v,int):return v
 if isinstance(v,str):
  try:return int(v,16 if v.startswith(('0x','$'))or any(c in v.lower()for c in 'abcdef')else 10)
  except ValueError:return None
 return None
def objects(d):
 if isinstance(d,dict):
  yield d
  for v in d.values():yield from objects(v)
 elif isinstance(d,list):
  for v in d:yield from objects(v)
def original(bank,pc):return 16+bank*8192+(pc&8191)
def row(rom,bank,pc):
 off=original(bank,pc);op,mode=OPS[rom[off]];size=SIZES[mode];operand=int.from_bytes(rom[off+1:off+size],'little')
 return dict(physical_bank=bank,cpu=pc,rom_offset=off,op=op,mode=mode,size=size,operand=operand,raw_hex=rom[off:off+size].hex(' ').upper())
def inputs():
 manifest=json.loads(PORTABLE.read_text());origins={}
 assert manifest['copy_count']==len(manifest['copies'])
 for item in manifest['copies']:
  path=ROOT/item['portable_path']
  assert path.stat().st_size==item['bytes']and sha(path)==item['sha256']
  assert not any(p.startswith('exploratory')for p in path.relative_to(ROOT).parts)
  origins[path]=item['original_path']
 paths=set()
 for name in ('program.json','static-control.json','offline-control-graph.json','executed-instructions.json','static-catalog.json'):
  for p in (ROOT/'analysis').glob('phase*/*/'+name):
   if 'phase16'not in p.parts and not any(part.startswith('exploratory')for part in p.parts):paths.add(p)
  for p in (ROOT/'analysis').glob('*_fsm/'+name):paths.add(p)
 for pattern in ('*program*.json','*control*.json','*graph*.json'):
  for p in (ROOT/'analysis').glob('phase*/*/'+pattern):
   if 'phase16' not in p.parts and not any(part.startswith('exploratory')for part in p.parts):paths.add(p)
 for name in ('analysis/phase5/domestic-ai/program.json','analysis/phase6/global/program.json','analysis/phase6/factions/ending-program.json'):
  p=ROOT/name
  if p.exists():paths.add(p)
 paths.update(origins)
 # Retain the original seed ordering so this relocation changes provenance,
 # not the investigated CFG/taint domain or its conservative result.
 return sorted(paths,key=lambda p:origins.get(p,str(p.relative_to(ROOT))))
def atlas(rom):
 known={};provenance={};repairs=[];rejects=[]
 origins={item['portable_path']:item['original_path']for item in json.loads(PORTABLE.read_text())['copies']}
 for p in inputs():
  d=json.loads(p.read_text());added=0
  for item in objects(d):
   off=num(item.get('rom_offset',item.get('file')));pc=num(item.get('pc',item.get('cpu',item.get('cpu_address'))));bank=num(item.get('physical_bank',item.get('bank')))
   if off is None or pc is None or not 0x8000<=pc<=0xFFFF:continue
   if bank is None:bank=(off-16)//8192
   if not 0<=bank<32:continue
   canonical=original(bank,pc)
   raw=item.get('raw_hex');op,mode=OPS[rom[canonical]];size=SIZES[mode]
   if raw and len(bytes.fromhex(raw))!=size:continue # data/ranges are not instruction seeds
   if raw and bytes.fromhex(raw)!=rom[canonical:canonical+size]:
    rejects.append(dict(path=str(p.relative_to(ROOT)),bank=bank,pc=pc,reason='raw bytes do not match canonical physical address'));continue
   if op=='?':continue
   if off!=canonical:
    repairs.append(dict(path=str(p.relative_to(ROOT)),declared=off,canonical=canonical,bank=bank,pc=pc,reason='Physicalbank/CPU authoritative; old fileoffset retained only as metadata'))
   k=(bank,pc)
   if k not in known:known[k]=row(rom,bank,pc)
   known[k].setdefault('sources',set()).add(str(p.relative_to(ROOT)));added+=1
  portable_path=str(p.relative_to(ROOT))
  provenance[portable_path]=dict(sha256=sha(p),seed_rows=added,original_path=origins.get(portable_path,portable_path),
     relocated_exact_copy=portable_path in origins)
 # Direct flow holes are filled only from existing trusted instruction seeds.
 # Unknown computed jumps/EADE tables are barriers. No linear sweep of data.
 queue=deque(known);seen=set();edges={};unresolved=[]
 while queue:
  k=queue.popleft()
  if k in seen:continue
  seen.add(k);r=known[k];bank,pc=k;op,md,sz,v=r['op'],r['mode'],r['size'],r['operand'];nextpc=pc+sz
  targets=[]
  def mapped(target):
   if target>=0xE000:return(31,target)
   if bank==31:return None
   pair=bank if pc<0xC000 else bank-1
   if 0xA000<=target<0xE000:return(pair+int(target>=0xC000),target)
   if target<0xA000:return None # active8000 data window cannot be inferred
  if md=='rel':
   target=(pc+2+(v if v<128 else v-256))&65535;targets=[mapped(target),mapped(nextpc)]
  elif op=='JMP':
   if md=='ab':targets=[mapped(v)]
   else:unresolved.append(dict(bank=bank,pc=pc,reason='computed JMP'))
  elif op=='JSR':
   if v in(0xEADE,0xB517):unresolved.append(dict(bank=bank,pc=pc,reason='inline dispatch; audited seeds represent bounded targets'));targets=[]
   else:
    targets=[mapped(nextpc+(2 if v==0xEE07 else 0))]
    if v!=0xEE07:targets.append(mapped(v))
  elif op not in('RTS','RTI','BRK'):targets=[mapped(nextpc)]
  targets=[x for x in targets if x is not None and x[1]<0x10000]
  for t in targets:
   # Do not let a recognized inline word be entered by datafallthrough.
   if t not in known:
    rr=row(rom,*t)
    if rr['op']=='?'or rr['op']=='BRK':unresolved.append(dict(bank=bank,pc=pc,target=list(t),reason='unrecognized/BRK reachable byte'));continue
    rr['sources']={'derived_direct_CFG'};known[t]=rr
   queue.append(t)
  edges[k]=[t for t in targets if t in known]
 for r in known.values():r['sources']=sorted(r['sources'])
 return known,edges,provenance,repairs,rejects,unresolved

def union(a,b):
 if a is None or b is None:return None
 result=a|b;return result if len(result)<=64 else None

def merge(a,b):return tuple(union(x,y)for x,y in zip(a[:3],b[:3]))+(tuple(union(x,y)for x,y in zip(a[3],b[3])),)
def one(v):return frozenset((v,))
def mapset(v,fn):
 if v is None or any(not isinstance(x,int)for x in v):return None
 return frozenset(fn(x)&255 for x in v)

def pointer(state,z,refined=False):
 if z not in ZP or(z+1)not in ZP:return None
 lo,hi=state[3][ZP.index(z)],state[3][ZP.index(z+1)]
 if lo is None or hi is None:return None
 if all(isinstance(v,tuple)and len(v)>=3 and v[0]=='pointer'and v[2]==0 for v in lo)and all(isinstance(v,tuple)and len(v)>=3 and v[0]=='pointer'and v[2]==1 for v in hi):
  roles={v[1]for v in lo|hi}
  if len(roles)==1:
   role=next(iter(roles))
   return None if role=='ruler_table_or_adjacent_bytes'else role
 if len(lo)!=1 or len(hi)!=1:return None
 a,b=next(iter(lo)),next(iter(hi))
 if isinstance(a,tuple)and isinstance(b,tuple)and a[:2]==b[:2]and a[2:]==(0,)and b[2:]==(1,):return None if a[1]=='ruler_table_or_adjacent_bytes'else a[1]
 if isinstance(a,int)and isinstance(b,int):
  address=a|b<<8
  if 0x6000<=address<0x63C0 and (address-0x6000)%32==0:return 'city'
  if 0x63C0<=address<0x6EDC and (address-0x63C0)%12==0:return 'officer'
  if refined and address>=0x8000:return 'ROM_window'
  if refined and(address<0x5F00 or address>=0x63C0):return 'non_city_RAM_or_IO'
 return None

def callees_and_effects(known):
 """Offline conservative may-write summaries; unknown paths clobber all facts."""
 memo={};busy=set();allzp=set(ZP)
 def target(k,pc):
  if pc>=0xE000:return(31,pc)
  if k[0]==31:return None
  pair=k[0]-int(k[1]>=0xC000)
  return(pair+int(pc>=0xC000),pc)if 0xA000<=pc<0xE000 else None
 def effect(entry):
  if entry in memo:return memo[entry]
  if entry in busy or entry not in known:return(allzp,{'A','X','Y'},set(),['unknown_or_recursive_entry'])
  busy.add(entry);writes=set();regs=set();pcs=set();barriers=[];todo=[entry]
  while todo:
   k=todo.pop()
   if k in pcs:continue
   if k not in known:writes|=allzp;regs|={'A','X','Y'};barriers.append(f'missing{str(k)}');continue
   pcs.add(k);r=known[k];op,md,v=r['op'],r['mode'],r['operand'];pc=r['cpu'];following=pc+r['size']
   if op in('LDA','PLA','TXA','TYA','ADC','SBC','AND','ORA','EOR')or(op in('ASL','LSR','ROL','ROR')and md=='a'):regs.add('A')
   if op in('LDX','TAX','TSX','INX','DEX'):regs.add('X')
   if op in('LDY','TAY','INY','DEY'):regs.add('Y')
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('zp','ab')and v in ZP:writes.add(v)
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('zpx','zpy'):
    writes|=allzp;barriers.append(f'dynamic_zero_page_store@{k[0]}:{pc:04X}')
   if op=='STA'and md in('ix','iy'):
    # A context-free callee may point an indirect store into scratch. Without
    # a separate address proof, treating it as SRAM-only would be unsound.
    writes|=allzp;barriers.append(f'context_unknown_indirect_store@{k[0]}:{pc:04X}')
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('abx','aby')and(v<256 or v>0xFF00):
    writes|=allzp;barriers.append(f'possible_indexed_zero_page_store@{k[0]}:{pc:04X}')
   if op=='JSR':
    if v in(0xEADE,0xB517,0xEE07):
     writes|=allzp;regs|={'A','X','Y'};barriers.append(f'computed_or_far_call@{k[0]}:{pc:04X}')
     if v in(0xEADE,0xB517):continue
     following+=2
    else:
     w,g,_,b=effect(target(k,v));writes|=w;regs|=g;barriers.extend(b)
    t=target(k,following)
    if t is not None:todo.append(t)
   elif op=='JMP':
    t=target(k,v)if md=='ab'else None
    if t is None:writes|=allzp;regs|={'A','X','Y'};barriers.append(f'computed_jump@{k[0]}:{pc:04X}')
    else:todo.append(t)
   elif md=='rel':
    for pc2 in(following,(pc+2+(v if v<128 else v-256))&65535):
     t=target(k,pc2)
     if t is not None:todo.append(t)
   elif op not in('RTS','RTI','BRK'):
    t=target(k,following)
    if t is not None:todo.append(t)
  busy.remove(entry);memo[entry]=(writes,regs,pcs,sorted(set(barriers)));return memo[entry]
 return effect,memo,target

def dataflow(known,edges,refined=False,rom=None):
 # Calls have summary fallthrough; their callee paths also start independently.
 # Only explicit pointer producers establish record identity. Unknown helpers
 # discard scratch facts, so unresolved indirect sites remain in the output.
 summaries={(31,0xF2AF):(0,'city',0),(31,0xF2D7):(0,'officer',0),(31,0xF368):(0,'ruler_table_or_adjacent_bytes',None),(31,0xF387):(0,'initial_officer',0),(31,0xF308):(0,'ROM_names',None),
            (11,0xD105):(0x20,'city',0),(11,0xD283):(0x20,'officer','keep'),(11,0xD2AB):(0x22,'officer','keep'),(8,0xB491):(0x20,'officer',0)}
 states={};q=deque()
 effects,effect_memo,call_target=callees_and_effects(known)
 # Every trusted start can be an external entry, but initialize only roots.
 preds=Counter(t for targets in edges.values()for t in targets)
 roots=[k for k in known if not preds[k]]
 for k in roots:states[k]=EMPTY;q.append(k)
 def runq():
  while q:
   k=q.popleft();s=states[k];r=known[k];a,x,y,z=s;z=list(z);op,md,v=r['op'],r['mode'],r['operand']
   def zpval(addr):return z[ZP.index(addr)]if addr in ZP else None
   def immutable_value(address,mode):
    if not refined or rom is None:return None
    index=x if mode=='abx'else y if mode=='aby'else one(0)
    if index is None:index=frozenset(range(256))
    if any(not isinstance(n,int)for n in index):return None
    values=set()
    for n in index:
     target=(address+n)&65535
     if target>=0xE000:bank=31
     elif 0xA000<=target<0xE000 and k[0]!=31:bank=k[0]-int(k[1]>=0xC000)+int(target>=0xC000)
     else:return None # Switched8000window has no implicitbank assumption.
     values.add(rom[original(bank,target)])
    return frozenset(values)if len(values)<=64 else None
   if op in('LDA','LDX','LDY'):
    value=one(v)if md=='im'else zpval(v)if md in('zp','ab')and v<256 else immutable_value(v,md)if md in('ab','abx','aby')else None
    if op=='LDA':a=value
    elif op=='LDX':x=value
    else:y=value
   elif op in('STA','STX','STY')and md in('zp','ab')and v in ZP:z[ZP.index(v)]={'STA':a,'STX':x,'STY':y}[op]
   elif op in('INC','DEC','ASL','LSR','ROL','ROR')and md in('zp','ab')and v in ZP:
    old=z[ZP.index(v)]
    if refined and op in('INC','DEC','ASL','LSR'):
     z[ZP.index(v)]=mapset(old,lambda n:n+1 if op=='INC'else n-1 if op=='DEC'else n<<1 if op=='ASL'else n>>1)
    else:z[ZP.index(v)]=None
   elif op=='INY':y=mapset(y,lambda n:n+1)
   elif op=='DEY':y=mapset(y,lambda n:n-1)
   elif op=='INX':x=mapset(x,lambda n:n+1)
   elif op=='DEX':x=mapset(x,lambda n:n-1)
   elif op=='TAY':y=a
   elif op=='TAX':x=a
   elif op=='TYA':a=y
   elif op=='TXA':a=x
   elif op=='PLA':a=None
   elif op in('ADC','SBC'):
    if refined and a is not None and all(isinstance(n,int)for n in a):
     right=one(v)if md=='im'else zpval(v)if md in('zp','ab')and v<256 else None
     previous=known.get((k[0],k[1]-1))if preds[k]==1 and k in edges.get((k[0],k[1]-1),[])else None
     carry=(0,)if previous and previous['op']=='CLC'else(1,)if previous and previous['op']=='SEC'else(0,1)
     if right is not None and all(isinstance(n,int)for n in right):
      values=frozenset((left+r+c if op=='ADC'else left-r-(1-c))&255 for left in a for r in right for c in carry)
      a=values if len(values)<=64 else None
     else:a=None
    else:a=None
   elif op in('AND','ORA','EOR'):
    if refined and a is None and md=='im'and op=='AND':
     values=frozenset(n&v for n in range(256));a=values if len(values)<=64 else None
    else:a=mapset(a,lambda n:n&v if op=='AND'else n|v if op=='ORA'else n^v)if md=='im'else None
   elif op in('ASL','LSR','ROL','ROR')and md=='a':a=mapset(a,lambda n:n<<1 if op=='ASL'else n>>1)if op in('ASL','LSR')else None
   out=(a,x,y,tuple(z))
   for t in edges.get(k,[]):
    value=out
    if op=='JSR':
     # Callee edge starts with unknown state; return uses only proven summaries.
     following=r['cpu']+r['size']+(2 if v==0xEE07 else 0)
     if t[1]!=following:value=EMPTY
     else:
      target=(31,v)if v>=0xE000 else(k[0]if v<0xC000 else k[0]+1 if k[1]<0xC000 else k[0],v)
      if k[1]>=0xC000 and v<0xC000:target=(k[0]-1,v)
      summary=summaries.get(target);zz=[None for _ in ZP]
      registers_clobbered={'A','X','Y'}
      if refined:
       writes,registers_clobbered,_,_=effects(target)
       zz=[None if address in writes else value for address,value in zip(ZP,z)]
      if summary:
       p,role,newy=summary
       if refined and target==(31,0xF368)and a is not None and all(isinstance(n,int)and(n&15)<7 for n in a):
        role='ruler';newy='ruler_index'
       origin=(k[0],k[1])if refined else()
       zz[ZP.index(p)]=one(('pointer',role,0,*origin));zz[ZP.index(p+1)]=one(('pointer',role,1,*origin))
       return_a=zz[ZP.index(p+1)]if target in((31,0xF2AF),(31,0xF2D7),(31,0xF368),(31,0xF387),(8,0xB491))else None
       return_y=one(newy)if isinstance(newy,int)else y if newy=='keep'else frozenset((n&15)*2 for n in a)if newy=='ruler_index'else None
       value=(return_a,x if refined and 'X'not in registers_clobbered else None,return_y,tuple(zz))
      elif refined:value=(a if 'A'not in registers_clobbered else None,x if 'X'not in registers_clobbered else None,y if 'Y'not in registers_clobbered else None,tuple(zz))
      else:value=EMPTY
      if refined and target==(28,0xDC6B):
       # Original helper scans exactly ten offsets17..26. Phase15 tested every
       # occupancy mask; normal and fullcapacity values both remain included.
       value=(None,frozenset(range(11)),one(27),value[3])
    # Restrict common counted Y loops at immediate CPY branch, not by intuition.
    if op in('BCC','BCS','BEQ','BNE'):
     before=known.get((k[0],k[1]-2))
     reg_index={'CMP':0,'CPX':1,'CPY':2}.get(before['op'])if before else None
     if not refined and reg_index!=2:reg_index=None
     if before and reg_index is not None and before['mode']=='im'and value[reg_index]is not None and all(isinstance(n,int)for n in value[reg_index]):
      limit=before['operand'];taken=t[1]!=k[1]+2
      test={'BCC':lambda n:n<limit,'BCS':lambda n:n>=limit,'BEQ':lambda n:n==limit,'BNE':lambda n:n!=limit}[op]
      yy=frozenset(n for n in value[reg_index]if isinstance(n,int)and test(n)==taken)
      if not yy:continue
      values=list(value);values[reg_index]=yy
      if refined and reg_index==0:
       # Common INCcursor/LDAcursor/CMPbound/BCC loops also restrict the exact
       # scratch variable subsequently loaded into Y. Only an adjacent direct
       # LDA with no intervening store/call supplies this relation.
       for load_pc in(k[1]-4,k[1]-5):
        load=known.get((k[0],load_pc))
        if load and load['op']=='LDA'and load['mode']in('zp','ab')and load['operand']in ZP and load_pc+load['size']==before['cpu']:
         zz=list(values[3]);zz[ZP.index(load['operand'])]=yy;values[3]=tuple(zz)
      value=tuple(values)
    previous=states.get(t);new=value if previous is None else merge(previous,value)
    if new!=previous:states[t]=new;q.append(t)
 runq()
 # Disconnected computed-dispatch domains remain roots with unknown context.
 for k in known:
  if k not in states:states[k]=EMPTY;q.append(k);runq()
 indirect=[];absolute=[]
 for k,r in sorted(known.items()):
  s=states.get(k,EMPTY);md,v=r['mode'],r['operand'];op=r['op']
  if md in('iy','ix'):
   ys=sorted(s[2])if s[2]is not None and all(isinstance(n,int)for n in s[2])else None
   kind=pointer(s,v,refined)if md=='iy'else None
   origins=[]
   if refined and v in ZP and v+1 in ZP:
    for value in (s[3][ZP.index(v)]or frozenset())|(s[3][ZP.index(v+1)]or frozenset()):
     if isinstance(value,tuple)and len(value)==5:
      b,pc=value[3:];producer=known[(b,pc)]
      item=dict(physical_bank=b,cpu=pc,rom_offset=producer['rom_offset'],raw_hex=producer['raw_hex'],callee=producer['operand'],pointer_role=value[1])
      if item not in origins:origins.append(item)
   indirect.append(dict(**r,pointer_zero_page=v,pointer_kind=kind,Y_values=ys,
      field_access='write'if op=='STA'else'read',pointer_producer_calls=origins,
      context_original_bytes=[dict(cpu=pc,rom_offset=known[(k[0],pc)]['rom_offset'],raw_hex=known[(k[0],pc)]['raw_hex'])for pc in sorted(p for b,p in known if b==k[0]and k[1]-24<=p<k[1])]if refined else[],
      resolved_pointer_byte_values=[sorted(map(str,s[3][ZP.index(v)]or[])),sorted(map(str,s[3][ZP.index(v+1)]or[]))]if refined and v in ZP and v+1 in ZP else None,
      unresolved_reason=None if kind and ys is not None else'Pointer identity or dynamic index unresolved; this access prevents whole-ROM absence claims'))
  if md in('ab','abx','aby')and op not in('JSR','JMP')and 0x6000<=v<0x6EE0:
   absolute.append(dict(**r,base_operand=v,index_mode=md,index_values=sorted(s[1 if md=='abx'else 2])if md!='ab'and s[1 if md=='abx'else 2]is not None and all(isinstance(n,int)for n in s[1 if md=='abx'else 2])else None))
 return indirect,absolute,summaries,effect_memo

def analyze(rom):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 OUT.mkdir(parents=True,exist_ok=True)
 known,edges,provenance,repairs,rejects,barriers=atlas(rom)
 indirect,absolute,summaries,_=dataflow(known,edges)
 # Refinement also tracks non-pointer scratch variables feeding LDY; it does
 # not modify the narrower first-pass inventory or any production source.
 global ZP,EMPTY
 old_zp,old_empty=ZP,EMPTY;ZP=tuple(range(0x60));EMPTY=(None,None,None,tuple(None for _ in ZP))
 refined,refined_absolute,_,effects=dataflow(known,edges,refined=True,rom=rom)
 ZP,EMPTY=old_zp,old_empty
 # Numeric scratch/ROM pointers are disjoint from city SRAM in these bounded
 # offsets. Unknown shifted pointers are not excluded by Y alone.
 def classification(r):
  if r['pointer_kind']in('officer','initial_officer','ruler'):return 'proved_other_record_kind'
  if r['pointer_kind']=='ROM_window':return 'proved_ROM_window_pointer'
  if r['pointer_kind']=='ROM_names':return 'proved_ROM_window_pointer'
  if r['pointer_kind']=='non_city_RAM_or_IO':return 'proved_non_city_RAM_or_IO_pointer'
  if r['pointer_kind']=='city'and r['Y_values']is not None:
   return 'city_auxiliary_candidate'if any(y in(1,28,29,30,31)for y in r['Y_values'])else'proved_city_other_offsets'
  return 'remaining_possible_city_alias'
 save('pointer-taint-refinement.json',dict(schema='phase16-cross-callee-pointer-taint-v1',ROM_sha256=ROM_SHA256,
  conservative_initial_unknown_count=sum(r['pointer_kind']is None or r['Y_values']is None for r in indirect),
  refined_unknown_count=sum(r['pointer_kind']is None or r['Y_values']is None for r in refined),
  classification_counts=dict(Counter(classification(r)for r in refined)),
  accesses=[dict(**r,classification=classification(r))for r in refined],
  remaining_candidates=[r for r in refined if classification(r)=='remaining_possible_city_alias'],
  callee_may_write_summaries=[dict(physical_bank=k[0],cpu=k[1],tracked_zero_page_writes=sorted(writes),register_writes=sorted(regs),
    instruction_positions=len(pcs),barriers=barriers,original_positions=[dict(physical_bank=b,cpu=pc,rom_offset=known[(b,pc)]['rom_offset'],raw_hex=known[(b,pc)]['raw_hex'])for b,pc in sorted(pcs)])for k,(writes,regs,pcs,barriers)in sorted(effects.items())if k is not None],
  limitation='Unknown/calculated callees clobber all trackedfacts. Known callee footprints preserve only fields with no possible originalwrite. Numeric shifts and genericcopy/unknownY remain candidates, not absentconsumers.'))
 # Address proofs for unresolved bulk/graphic accesses: these are not field
 # meanings. Every derivation includes the exact original producer/body bytes.
 def proof_range(bank,start,end):
  o=original(bank,start);return dict(physical_bank=bank,cpu=start,end_cpu_exclusive=end,rom_offset=o,raw_hex=rom[o:o+end-start].hex(' ').upper(),byte_count=end-start)
 palette_table=original(30,0xDBCF)
 palette_addresses=[int.from_bytes(rom[palette_table+((a*2)&255):palette_table+((a*2)&255)+2],'little')for a in range(256)]
 assert not any(0x6000<=((p+y)&65535)<0x63C0 for p in palette_addresses for y in range(32))
 graphics_addresses=[0x946C+16*((3*a)&255)for a in range(256)]
 assert all(p>=0x8000 and p+47<=0xFFFF for p in graphics_addresses)
 address_proofs=[dict(site=[30,0xDBC4],classification='proved_non_city_palette_or_adjacent_pointer',
   domain='Every raw inputbyte0..255, ASL wraps index into even0..254; actualY0..31',
   formula='LE16(ROM30:DBCF + ((A*2)&255)) + Y',possible_pointer_addresses=sorted(set(palette_addresses)),
   city_auxiliary_intersections=0,ranges=[proof_range(30,0xDBB1,0xDBCF),proof_range(30,0xDBCF,0xDCCF)]),
  dict(site=[30,0xDD9A],classification='generic_whole_SRAM_clear',domain='All6000..6FFF, including city+1/+28..31',
       role='Whole4096Bzeroing, not dedicatedfield logic',ranges=[proof_range(30,0xDD8F,0xDDA9)]),
  dict(site=[30,0xDDED],classification='proved_ROM_source_bulk_city_initialization',domain='960 sourcebytes16:8C00..8FBF',
       role='Whole30×32 initial city template source',ranges=[proof_range(30,0xDDCD,0xDE12)]),
  dict(site=[30,0xDDEF],classification='generic_whole_city_record_copy',domain='6000..63BF including allcityauxiliarybytes',
       role='Whole30×32 rawcopy, not a dedicatedtailfield interpretation',ranges=[proof_range(30,0xDDCD,0xDE12)]),
  dict(site=[30,0xDE32],classification='proved_ROM_source_bulk_officer_initialization',domain='2880 sourcebytes17:8000..8B3F',
       role='237legalofficerrecords plus3adjacent data pseudorecords',ranges=[proof_range(30,0xDE12,0xDE57)]),
  dict(site=[30,0xDE34],classification='proved_non_city_destination_bulk_officer_initialization',domain='63C0..6EFF, disjoint fromcity6000..63BF',
       role='Includes extra3copiedpseudoslots with rawaffinity3; not threeadditional legitimateofficers',ranges=[proof_range(30,0xDE12,0xDE57)]),
  dict(site=[30,0xDEAE],classification='proved_ROM_source_graphics_record_copy',domain='Every rawAbyte0..255, actualY0..47',
       formula='946C + 16*((3*A)&255) + Y; original21 mapperselector datawindow',
       possible_pointer_addresses=sorted(set(graphics_addresses)),city_auxiliary_intersections=0,ranges=[proof_range(30,0xDE7E,0xDEB9)])]
 proof_map={tuple(p['site']):p for p in address_proofs}
 remaining=[r for r in refined if classification(r)=='remaining_possible_city_alias'and(r['physical_bank'],r['cpu'])not in proof_map]
 save('city-tail-candidate-review.json',dict(schema='phase16-city-tail-address-proof-review-v1',ROM_sha256=ROM_SHA256,
   address_proofs=address_proofs,remaining_possible_dedicated_alias_count=len(remaining),
   remaining_known_city_pointer_unknown_Y=[r for r in remaining if r['pointer_kind']=='city'],
   remaining_pointer_or_shifted_index_unresolved=[r for r in remaining if r['pointer_kind']!='city'],
   generic_city_bulk_operations=[p for p in address_proofs if p['classification'].startswith('generic_')],
   limitation='Still no all-ROM no-consumer theorem; explicitremaining rows are searchable bybank/CPU/file and carry rawcontext/producer facts. Bulkclear/copy are realauxiliaryaccesses, classifiedseparately rather than hidden.'))
 save('all-bank-instruction-atlas.json',dict(schema='phase16-original-instruction-atlas-v1',ROM_sha256=ROM_SHA256,
  instruction_positions=len(known),original_seed_provenance=provenance,metadata_offset_repairs=repairs,rejected_seed_rows=rejects,
  banks=[dict(bank=b,known_positions=sum(k[0]==b for k in known),known_instruction_bytes=sum(r['size']for k,r in known.items()if k[0]==b),PRG_bytes=8192)for b in range(32)],
  instructions=list(known.values()),limitations=['Direct CFG closure only; computeddispatch targets are included only through existing verified seeds','Unknown8000window mapping and remaining unclassified bytes prevent an exhaustive allcode proof']))
 save('pointer-field-accesses.json',dict(schema='phase16-conservative-CFG-pointer-field-access-v1',ROM_sha256=ROM_SHA256,
  pointer_producers=[dict(physical_bank=b,cpu=pc,pointer_zero_page=z,kind=role,Y_after=y)for(b,pc),(z,role,y)in summaries.items()],
  CFG_edge_count=sum(map(len,edges.values())),unresolved_flow_barriers=barriers,indirect_accesses=indirect,absolute_record_area_accesses=absolute,
  city_auxiliary_candidates=[r for r in indirect if r['pointer_kind']=='city'and r['Y_values']is not None and any(y in(1,28,29,30,31)for y in r['Y_values'])],
  officer_flags_candidates=[r for r in indirect if r['pointer_kind']=='officer'and(r['Y_values']is None or 11 in r['Y_values'])],
  unresolved_indirect_access_count=sum(r['pointer_kind']is None or r['Y_values']is None for r in indirect),
  limitations=['Unknowncalls conservatively discard all tracked scratch facts; lackofclassification is not lackofaccess','Pointer summaries are address-specific and validated against original bytes; directaliases are not granted officialfieldnames']))
 # Syntactic address pool across every physical bank, including data/unclassified.
 pool=[]
 for bank in range(32):
  for pos in range(8191):
   offset=16+bank*8192+pos;byte=rom[offset];op,md=OPS[byte]
   if (byte==0xA0 and rom[offset+1]in(1,11,27,28,29,30,31))or md in('iy','ix'):
    # membership uses physical offset independently of window aliases.
    pool.append(dict(physical_bank=bank,rom_offset=offset,raw_hex=rom[offset:offset+SIZES[md]].hex(' ').upper(),op=op,mode=md,
                     classification='known_instruction_start'if any((bank,base+pos)in known for base in(0x8000,0xA000,0xC000,0xE000))else'unclassified_or_data_candidate',
                     Y_immediate=rom[offset+1]if byte==0xA0 else None,pointer_zero_page=rom[offset+1]if md in('iy','ix')else None))
 save('all-PRG-address-pool.json',dict(schema='phase16-all-PRG-syntactic-pool-v1',bank_count=32,PRG_byte_count=262144,candidates=pool,
  limitation='Raw matches are not proof of instructions, pointer roles, natural producers or field consumers'))
 ranges=[];lines=[]
 for bank,start,end,name in RANGES:
  off=original(bank,start);ranges.append(dict(name=name,physical_bank=bank,cpu=start,end_cpu_exclusive=end,rom_offset=off,byte_count=end-start,raw_hex=rom[off:off+end-start].hex(' ').upper()))
  lines.append(f'; {name}; physical{bank}; all file offsets include16B header')
  pc=start
  while pc<end:
   r=row(rom,bank,pc);size,asm=instruction(rom,r['rom_offset'],pc);lines.append(f'{bank:02d}:{pc:04X} file0x{r["rom_offset"]:06X} {r["raw_hex"]:<9} {asm}');pc+=size
  assert pc==end
  lines.append('')
 tables=[dict(name=name,physical_bank=b,cpu=pc,rom_offset=original(b,pc),byte_count=n,raw_hex=rom[original(b,pc):original(b,pc)+n].hex(' ').upper())for b,pc,n,name in TABLES]
 (OUT/'raw.asm').write_text('\n'.join(lines)+'\n')
 save('static-catalog.json',dict(schema='phase16-field-semantics-static-v1',ROM_sha256=ROM_SHA256,ranges=ranges,tables=tables,
  source_path=str(SOURCE.relative_to(ROOT)),source_sha256=sha(SOURCE),analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__)))
 city=rom[0x20C10:0x20FD0];officers=rom[0x22010:0x22B2C]
 assert len(city)==960 and len(officers)==237*12
 save('initial-records.json',dict(ROM_sha256=ROM_SHA256,
  cities=[dict(id=i,rom_offset=0x20C10+i*32,raw_hex=city[i*32:(i+1)*32].hex(' ').upper(),byte1=city[i*32+1],tail28_31=list(city[i*32+28:(i+1)*32]))for i in range(30)],
  officers=[dict(id=i,rom_offset=0x22010+i*12,raw_hex=officers[i*12:(i+1)*12].hex(' ').upper(),flags11=officers[i*12+11],affinity=affinity_code(officers[i*12+11]))for i in range(237)],
  initial_affinity_counts=dict(Counter(affinity_code(officers[i*12+11])for i in range(237)))))
 initial_data=json.loads((OUT/'initial-records.json').read_text())
 initial_data['copied_adjacent_pseudo_slots']=[dict(id=i,valid_officer=False,rom_offset=0x22010+i*12,runtime_address=0x63C0+i*12,
   raw_hex=rom[0x22010+i*12:0x22010+(i+1)*12].hex(' ').upper(),flags11=rom[0x22010+i*12+11],affinity=affinity_code(rom[0x22010+i*12+11]),
   origin='Original2880Bcopier includes adjacentpointer/data aftervalid237records')for i in range(237,240)]
 save('initial-records.json',initial_data)
 # Manual record identity supplements deliberately conservative call summaries.
 # Each path has an existing byte-exact source recovery/original-CPU evidence.
 # These are seventeen named writer domains, not proof of all dynamic stores.
 writer_specs=[(10,0xAA79,0xAA7F,0x22,'(old & FC) | 03','status3'),
  (10,0xAC2F,0xAC33,0x22,'old & FC','status0'),
  (10,0xB0DF,0xB0E9,0x22,'(old & 0F) | tier_multiple_of_16','tier'),
  (11,0xC651,0xC65B,0x20,'(old & FC) | 02','status2'),
  (11,0xC765,0xC76F,0x22,'(old & FC) | 02','status2'),
  (11,0xCA45,0xCA4F,0x22,'(old & FC) | 03','status3'),
  (11,0xCBD9,0xCBE4,0x22,'old & FC','status0'),
  (12,0xB609,0xB611,0,'old | 03','status3'),
  (13,0xCDC8,0xCDD0,0,'old & FC','status0'),
  (13,0xCDE6,0xCDEE,0,'old | 03','status3'),
  (13,0xD21B,0xD223,0,'old & FC','status0'),
  (15,0xD880,0xD88B,0,'(old & 0F) | tier_multiple_of_16','tier'),
  (25,0xAF4A,0xAF54,0,'(old & FC) | 02','status2'),
  (25,0xBDC6,0xBDCE,0,'old | 03','status3'),
  (26,0xC099,0xC0A1,0,'old & FC','status0'),
  (26,0xC321,0xC329,0x22,'old & FC','status0'),
  (27,0xAD1A,0xAD27,0,'(old & FC) | 02','status2')]
 writers=[]
 for b,start,end,pointer_z,formula,kind in writer_specs:
  o=original(b,start)
  writers.append(dict(physical_bank=b,cpu=start,end_cpu_exclusive=end,rom_offset=o,raw_hex=rom[o:o+end-start].hex(' ').upper(),
    pointer_zero_page=pointer_z,record='live_officer',field_offset=11,operation=formula,role=kind,
    affinity_bits_preserved=True,producer_claim='Cannot create code3 from inputcodes0/1/2 within this verified writer domain',
    record_identity_evidence='Original F2D7/D283/D2AB or officer stride12 scan; source path and bounded prior evidence retained in atlas provenance'))
 save('officer-flag-writers.json',dict(schema='phase16-officer-affinity-writer-domains-v1',ROM_sha256=ROM_SHA256,writers=writers,
  initial237_affinity_codes=sorted(set(affinity_code(officers[i*12+11])for i in range(237))),
  generic_copy_and_initialization='Original2880Bcopy includes237validrecords codes0/1/2 and3adjacent pseudoslots237..239 withrawcode3; wholeSRAMclear produces0. Generic/boundary stores remain possiblealiases.',
  limitation='Seventeen verified update paths preservebits2..3; unresolvedindirect/dynamicindex/rawcode domains prevent an all-ROM no-natural-producer theorem'))
 save('schema.json',dict(schema='phase16-field-semantics-overlay-v1',ROM_sha256=ROM_SHA256,old_schemas_unchanged=True,
  city=[dict(offsets=[1],official_name=None,status='unresolved_semantic_name',mechanical='BD97/BD9D read LE16(+1,+2)>=300; +2 is also goldlow. No distinct resource is established'),
        dict(offsets=[28,29,30,31],official_name=None,status='unresolved',mechanical='Copied/cleared through whole-record/SRAM initialization; no resolved dedicated consumer in expanded CFG domain',
             no_unused_or_reserved_claim=True,unresolved_indirect_sites=sum(r['pointer_kind']is None or r['Y_values']is None for r in indirect))],
  officer_affinity=dict(field_offset=11,mask=12,codes=[dict(code=c,official_glyph={0:'平',1:'山',2:'水',3:None}[c],
      initial_count=sum(affinity_code(officers[i*12+11])==c for i in range(237)),
      upper_pair=list(rom[original(25,0xB647)+c*2:original(25,0xB647)+c*2+2]),
      lower_pair=list(rom[original(25,0xB713)+c*2:original(25,0xB713)+c*2+2]),
      first_movement_costs=[rom[original(12,0xA823)+t*4+c]for t in range(7)],
      second_movement_costs=[rom[original(12,0xA83F)+t*4+c]for t in range(7)],
      attack_terrain_matches=[rom[original(15,0xCBE9)+c],rom[original(15,0xCBED)+c]],
      formation_base_selectors=list(rom[original(15,0xD1B0)+c*8:original(15,0xD1B0)+c*8+8]),
      status='confirmed_mechanical_table_spill_no_official_name'if c==3 else'confirmed_glyph_and_mechanical_consumers')for c in range(4)],
      natural_producer_scope='Originalinitial237 excludes3 and allseventeen reliableflagupdates preservebits2..3; not a wholeROM negative proof')))
 tree=ast.parse(SOURCE.read_text());imports=[n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]
 assert not any(x and any(t in x for t in('py65','state_machine','structuring'))for x in imports)
 pins={str(p.relative_to(ROOT)):sha(p)for p in(SOURCE,Path(__file__),ROOT/'scripts/verify_field_semantics.py',ROOT/'source/recovered/global_ui_controller.py',ROOT/'source/recovered/scene_shared_services.py',ROOT/'source/recovered/service_memory.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'source/recovered/controller_helpers.py',ROOT/'source/recovered/battle_nmi_services.py')}
 artifacts={**{path:d['sha256']for path,d in provenance.items()}}
 artifacts[str(PORTABLE.relative_to(ROOT))]=sha(PORTABLE)
 for pair in(8,10,12,14,23,25,27,29):
  for name in('image.bin','mapping.json'):
   p=ROOT/f'analysis/rea/pairs/pair-{pair:02d}/{name}'
   if p.exists():artifacts[str(p.relative_to(ROOT))]=sha(p)
 for name in('analysis/phase13/scenario/evidence.json','analysis/phase13/scenario/validation.json','analysis/phase15/fields/validation.json'):
  p=ROOT/name;artifacts[name]=sha(p)
 for name in('source/recovered/scenario_initialization.py','scripts/verify_scenario_initialization.py'):
  p=ROOT/name
  if p.exists():pins[name]=sha(p)
 save('evidence.json',dict(schema='phase16-field-semantics-evidence-v1',ROM_sha256=ROM_SHA256,status='analyzed',source_path=str(SOURCE.relative_to(ROOT)),source_sha256=sha(SOURCE),
  analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),source_and_validator_sha256=pins,artifact_and_dependency_sha256=artifacts,
  ranges=ranges,tables=tables,verified_officer_flag_writer_domains=17,
  pointer_taint_refinement=dict(path='analysis/phase16/fields/pointer-taint-refinement.json',review_path='analysis/phase16/fields/city-tail-candidate-review.json',remaining_possible_dedicated_aliases=len(remaining),known_city_pointer_unknown_Y=sum(r['pointer_kind']=='city'for r in remaining),pointer_unresolved=sum(r['pointer_kind']!='city'for r in remaining),generic_city_bulk_operations=2),
  copied_adjacent_affinity3_pseudo_slots=[237,238,239],whole_PRG_search=dict(physical_banks=32,PRG_bytes=262144,known_instruction_positions=len(known),indirect_accesses=len(indirect),unresolved_indirect_accesses=sum(r['pointer_kind']is None or r['Y_values']is None for r in indirect),
   negative_claim='No whole-ROM no-producer/no-consumer claim. Original initial237 officers excludeaffinity3; resolved consumer tables spill or mechanicalzero behavior is confirmed.'),
  official_affinity_names={0:'平',1:'山',2:'水',3:None},source_original_CPU_callbacks=0,source_control_IR_callbacks=0,
  complete_helpers=['25B630','12A7E7','8A796 suffix withrealcallerPHA','15CB2F suffix','15D102','13DD2F+DB03'],explicit_prefixes=['25B64D endsB663 beforetroops rendering']))
 native_dir=ROOT/'analysis/phase16/runtime/affinity-pages'
 if (native_dir/'validation.json').exists():
  native=json.loads((native_dir/'validation.json').read_text())
  assert native['status']=='passed'and native['native_internal_CPU_trace']is False
  checkpoints=json.loads((native_dir/'checkpoints.json').read_text());bindings=[]
  for image in native['verified_effects']['affinity_glyph_regions']:
   c=image['code'];label=image['checkpoint'];point=next(p for p in checkpoints if p['label']==label)
   raw=(native_dir/point['SRAM']).read_bytes();flags=raw[0x63C0+12*131+11-0x6000]
   assert affinity_code(flags)==c and point['fields']['UI_row_040D']==255
   bindings.append(dict(code=c,officer=131,flags11=flags,frame=point['frame'],completed_after_real_rows0_9=True,
     PNG=str((native_dir/image['PNG']).relative_to(ROOT)),PNG_sha256=image['PNG_sha256'],
     RAM=str((native_dir/point['RAM']).relative_to(ROOT)),SRAM=str((native_dir/point['SRAM']).relative_to(ROOT)),
     glyph_box=image['box'],glyph_RGB_sha256=image['RGB_sha256'],
     upper_table_bytes=list(rom[original(25,0xB647)+2*c:original(25,0xB647)+2*c+2]),
     lower_table_bytes=list(rom[original(25,0xB713)+2*c:original(25,0xB713)+2*c+2]),
     official_name={0:'平',1:'山',2:'水',3:None}[c]))
  save('native-affinity-proof.json',dict(schema='phase16-native-affinity-consumer-binding-v1',native_validation_path=str((native_dir/'validation.json').relative_to(ROOT)),
   native_validation_sha256=sha(native_dir/'validation.json'),rows=bindings,
   provenance='OriginalNestopia ordinaryopen/close after fourdeclared flags11bitpreparations; source CPUcases and Nativeframes are independent evidence.',
   native_internal_CPU_trace=False,source_CPU_cases_in_native_receipt=0,no_fourth_official_affinity_name=True))
  evidence=json.loads((OUT/'evidence.json').read_text());evidence['native_affinity_proof']='analysis/phase16/fields/native-affinity-proof.json'
  for p in [native_dir/'validation.json',native_dir/'repeat-validation.json',native_dir/'checkpoints.json',ROOT/'analysis/phase16/runtime/evidence.json',
            *(native_dir/row['PNG'].split('/')[-1]for row in bindings),*(ROOT/row['RAM']for row in bindings),*(ROOT/row['SRAM']for row in bindings)]:
   evidence['artifact_and_dependency_sha256'][str(p.relative_to(ROOT))]=sha(p)
  save('evidence.json',evidence)
 print(json.dumps(dict(instructions=len(known),indirect=len(indirect),resolved=sum(r['pointer_kind']is not None and r['Y_values']is not None for r in indirect),city_candidates=sum(r['pointer_kind']=='city'and r['Y_values']is not None and any(y in(1,28,29,30,31)for y in r['Y_values'])for r in indirect),seed_files=len(provenance),raw_pool=len(pool))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();analyze(a.rom.read_bytes())
