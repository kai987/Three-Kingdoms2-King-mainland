#!/usr/bin/env python3
"""Read-only phase18 call/pointer-contract refinement of the frozen 589 sites.

This is an offline abstract analysis of original bytes, not gameplay source,
CPU execution or a proof that unresolved fields are unused. Frozen phase16/17
inputs are only read; all output is written beneath phase18/fields-static.
"""
from pathlib import Path
from collections import Counter,deque
import argparse,ast,bisect,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import analyze_field_semantics as prior
from source.recovered.city_field_contracts import ROM_SHA256
OUT=ROOT/'analysis/phase18/fields-static';BASE=ROOT/'analysis/phase17/fields'
ZP=tuple(range(256));EMPTY=(None,None,None,tuple(None for _ in ZP),())
one=prior.one;mapset=prior.mapset;pointer=prior.pointer
AUX={1,28,29,30,31}
DISPATCHES={}
FAR_TARGETS={}
INDEXED_TARGETS={}
DISJOINT_STACK_STORES=set()
RETURN_STATES={}
ORIGINAL_CONTEXTS={}
LOCAL_PREDECESSORS={}
BANK_POSITIONS={}
BALANCED_POINTER_HELPERS={(31,p)for p in(0xF2AF,0xF2D7,0xF368,0xF387,0xF308,0xF25F,0xF266)}|{(8,p)for p in(0xB469,0xB491,0xB4E1,0xB4C2)}|{(11,p)for p in(0xD105,0xD283,0xD2AB,0xD304,0xD319)}
DISPATCH_BASE={0xEADE:0,0xD494:0x20,0xB517:0x20}
def union(a,b):
 if a is b:return a
 if a is None or b is None:return None
 return a|b

def merge(a,b):return tuple(union(x,y)for x,y in zip(a[:3],b[:3]))+(tuple(union(x,y)for x,y in zip(a[3],b[3])),tuple(union(x,y)for x,y in zip(a[4],b[4]))if len(a[4])==len(b[4])else())
def original(bank,pc):return 16+bank*8192+(pc&8191)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(name,data):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def mapped(k,pc):
 if pc>=0xE000:return(31,pc)
 if k[0]==31:return None
 pair=k[0]-int(k[1]>=0xC000)
 return(pair+int(pc>=0xC000),pc)if 0xA000<=pc<0xE000 else None

def precise_effects(known,disjoint_stores):
 """Least fixed point of may-writes; recursion alone does not mean all writes.

Indirect stores are skipped ONLY at sites whose current all-path abstract
pointer/index domain proved their effective addresses disjoint from 0..255.
Unresolved/computed/far calls remain full barriers here. No stub return.
 """
 allzp=set(ZP);entries=set()
 for k,r in known.items():
  if r['op']=='JSR'and r['operand']not in(0xEE07,0xEADE,0xB517):entries.add(mapped(k,r['operand']))
 entries.update(tuple(target)for contract in DISPATCHES.values()for target in contract['mapped_targets']);entries.update(target for targets in FAR_TARGETS.values()for target in targets);entries.discard(None);local={}
 for entry in sorted(entries):
  writes=set();regs=set();pcs=set();barriers=[];deps=set();todo=[entry]
  while todo:
   k=todo.pop()
   if k in pcs:continue
   if k not in known:writes|=allzp;regs|={'A','X','Y'};barriers.append(f'missing{k}');continue
   pcs.add(k);r=known[k];op,md,v=r['op'],r['mode'],r['operand'];pc=r['cpu'];following=pc+r['size']
   if op in('LDA','PLA','TXA','TYA','ADC','SBC','AND','ORA','EOR')or(op in('ASL','LSR','ROL','ROR')and md=='a'):regs.add('A')
   if op in('LDX','TAX','TSX','INX','DEX'):regs.add('X')
   if op in('LDY','TAY','INY','DEY'):regs.add('Y')
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('zp','ab')and v<0x2000 and(v&0x7FF)<256:writes.add(v&255)
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('zpx','zpy'):
    writes.update(INDEXED_TARGETS.get(k,allzp));barriers.append(f'dynamic_zero_page_store@{k}')if k not in INDEXED_TARGETS else None
   if op=='STA'and md in('ix','iy')and k not in disjoint_stores:
    writes|=allzp;barriers.append(f'unproved_indirect_store@{k}')
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('abx','aby'):
    addresses={(v+i)&65535 for i in range(256)};writes.update(INDEXED_TARGETS.get(k,{address&255 for address in addresses if address<0x2000 and(address&0x7FF)<256}))
   if op=='JSR':
    if k in DISPATCHES:
     base=DISPATCH_BASE[v];writes.update(range(base,base+5));regs|={'A','Y'}
     deps.update(tuple(target)for target in DISPATCHES[k]['mapped_targets']);continue
    if v==0xEE07 and FAR_TARGETS.get(k):
     writes.update(range(0x58,0x5E));deps.update(FAR_TARGETS[k]);deps.add((31,0xF237));regs|={'A','Y'}
    elif v in(0xEADE,0xB517,0xEE07):
     writes|=allzp;regs|={'A','X','Y'};barriers.append(f'computed_or_far_call@{k}')
     if v in(0xEADE,0xB517):continue
     following+=2
    elif v!=0xEE07:
     target=mapped(k,v)
     if target is None or target not in known:writes|=allzp;regs|={'A','X','Y'};barriers.append(f'unknown_callee@{k}')
     else:deps.add(target)
    if v==0xEE07 and FAR_TARGETS.get(k):following+=2
    target=mapped(k,following)
    if target is not None:todo.append(target)
   elif op=='JMP':
    target=mapped(k,v)if md=='ab'else None
    if target is None:writes|=allzp;regs|={'A','X','Y'};barriers.append(f'computed_jump@{k}')
    else:todo.append(target)
   elif md=='rel':
    for pc2 in(following,(pc+2+(v if v<128 else v-256))&65535):
     target=mapped(k,pc2)
     if target is not None:todo.append(target)
   elif op not in('RTS','RTI','BRK'):
    target=mapped(k,following)
    if target is not None:todo.append(target)
  local[entry]=(writes,regs,pcs,barriers,deps)
 memo={k:(set(w),set(g),set(p),list(b))for k,(w,g,p,b,d)in local.items()}
 changed=True
 while changed:
  changed=False
  for k,(w,g,p,b,dependencies)in local.items():
   old=memo[k];ww=set(w);gg=set(g);pp=set(p);bb=set(b)
   for d in dependencies:
    if d not in memo:ww|=allzp;gg|={'A','X','Y'};bb.add(f'unknown_callee{d}')
    else:
     a,c,e,f=memo[d];ww|=a;gg|=c;pp|=e;bb.update(f)
   new=(ww,gg,pp,sorted(bb))
   if new!=old:memo[k]=new;changed=True
 def effect(entry):return memo.get(entry,(allzp,{'A','X','Y'},set(),['unknown_entry']))
 return effect,memo,mapped

def refined_dataflow(known,edges,rom,disjoint_stores):
 refined=True
 # Callee inputs are conservative caller unions. Return facts join every
 # audited local RTS exit; unknown computed tails get no return summary.
 # This finite refinement is not a proof of program reachability or termination.
 summaries={(31,0xF2AF):(0,'city',0),(31,0xF2D7):(0,'officer',0),(31,0xF368):(0,'ruler_table_or_adjacent_bytes',None),(31,0xF387):(0,'initial_officer',0),(31,0xF308):(0,'ROM_names',None),
            (11,0xD105):(0x20,'city',0),(11,0xD283):(0x20,'officer','keep'),(11,0xD2AB):(0x22,'officer','keep'),(8,0xB491):(0x20,'officer',0), (8,0xB469):(0x20,'city',0), (8,0xB4E1):(0x20,'initial_officer',0), (8,0xB4C2):(0x20,'ruler_table_or_adjacent_bytes','ruler_index'), (11,0xD319):(0x24,'ruler_table_or_adjacent_bytes','ruler_index'), (11,0xD304):(0x20,'city',None)}
 states={};q=deque()
 effects,effect_memo,call_target=precise_effects(known,disjoint_stores)
 # Every trusted start can be an external entry, but initialize only roots.
 preds=Counter(t for targets in edges.values()for t in targets)
 roots=[k for k in known if not preds[k]]
 for k in roots:states[k]=EMPTY;q.append(k)
 def runq():
  while q:
   k=q.popleft();s=states[k];r=known[k];a,x,y,z,stack=s;z=list(z);op,md,v=r['op'],r['mode'],r['operand']
   def zpval(addr):return z[ZP.index(addr)]if addr in ZP else None
   def numeric(values):
    if values is None:return None
    result=set()
    for fact in values:
     numbers=pointernums(fact,known,rom)
     if numbers is None:return None
     result.update(numbers)
    return frozenset(result)
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
    return frozenset(values)if len(values)<=256 else None
   if op in('LDA','LDX','LDY'):
    value=one(v)if md=='im'else zpval(v)if md in('zp','ab')and v<256 else immutable_value(v,md)if md in('ab','abx','aby')else None
    if op=='LDA':a=value
    elif op=='LDX':x=value
    else:y=value
   elif op in('STA','STX','STY')and md in('zp','ab')and v in ZP:z[ZP.index(v)]={'STA':a,'STX':x,'STY':y}[op]
   elif op in('INC','DEC','ASL','LSR','ROL','ROR')and md in('zp','ab')and v in ZP:
    old=numeric(z[ZP.index(v)])
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
   elif op=='PHA':stack=(stack+(a,))[-16:]
   elif op=='PHP':stack=(stack+(None,))[-16:]
   elif op=='PLA':a=stack[-1]if stack else None;stack=stack[:-1]
   elif op=='PLP':stack=stack[:-1]
   elif op=='TXS':stack=()
   elif op in('ADC','SBC'):
    a=numeric(a)
    if refined and a is not None and all(isinstance(n,int)for n in a):
     right=numeric(one(v)if md=='im'else zpval(v)if md in('zp','ab')and v<256 else None)
     previous=known.get((k[0],k[1]-1))if preds[k]==1 and k in edges.get((k[0],k[1]-1),[])else None
     carry=(0,)if previous and previous['op']=='CLC'else(1,)if previous and previous['op']=='SEC'else(0,1)
     if right is not None and all(isinstance(n,int)for n in right):
      values=frozenset((left+r+c if op=='ADC'else left-r-(1-c))&255 for left in a for r in right for c in carry)
      a=values if len(values)<=256 else None
     else:a=None
    else:a=None
   elif op in('AND','ORA','EOR'):
    a=numeric(a)
    if refined and a is None and md=='im'and op in('AND','ORA','EOR'):
     values=frozenset(n&v if op=='AND'else n|v if op=='ORA'else n^v for n in range(256));a=values
    else:a=mapset(a,lambda n:n&v if op=='AND'else n|v if op=='ORA'else n^v)if md=='im'else None
   elif op in('ASL','LSR','ROL','ROR')and md=='a':a=mapset(numeric(a),lambda n:n<<1 if op=='ASL'else n>>1)if op in('ASL','LSR')else None
   # An unknown indirect store can alias any zero-page byte or NES RAM mirror.
   # Previous stage did not model this inside a body; phase18 fails closed.
   if op=='STA'and md in('ix','iy')and k not in disjoint_stores:z=[None for _ in ZP]
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('zpx','zpy'):
    indices=x if md=='zpx'else y
    targets={(v+i)&255 for i in indices}if indices is not None and all(isinstance(i,int)for i in indices)else set(ZP)
    for address in targets:z[address]=None
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('abx','aby'):
    indices=x if md=='abx'else y
    indices=indices if indices is not None and all(isinstance(i,int)for i in indices)else range(256)
    for i in indices:
     address=(v+i)&65535
     if address<0x2000 and(address&0x7FF)<256:z[address&255]=None
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md=='ab'and 256<=v<0x2000 and(v&0x7FF)<256:z[v&255]=None
   if op=='STA'and md in('ix','iy')and k not in DISJOINT_STACK_STORES:stack=()
   if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('ab','abx','aby'):
    indices=range(256)if md!='ab'else(0,)
    if any((v+i)&65535<0x2000 and 256<=(((v+i)&65535)&0x7FF)<512 for i in indices):stack=()
   out=(a,x,y,tuple(z),stack)
   for t in edges.get(k,[]):
    value=out
    if op=='JSR':
     # Callee edge starts with unknown state; return uses only proven summaries.
     following=r['cpu']+r['size']+(2 if v==0xEE07 else 0)
     if k in DISPATCHES:
      contract=DISPATCHES[k];selectors=[i for i,target in enumerate(contract['mapped_targets'])if tuple(target)==t]
      if a is not None and all(isinstance(n,int)for n in a)and not set(selectors)&set(a):continue
      base=DISPATCH_BASE[v];zz=list(z);zz[base]=y
      zz[base+1]=one((r['cpu']+2)&255);zz[base+2]=one((r['cpu']+2)>>8)
      zz[base+3]=one(t[1]&255);zz[base+4]=one(t[1]>>8)
      value=(one(t[1]>>8),x,y,tuple(zz),stack)
     elif t!=mapped(k,following):
      if v==0xEE07:
       zz=list(z)
       for address in(*range(0x58,0x5E),*range(0xE0,0xE4)):zz[address]=None
       zz[0x5B]=one(t[1]&255);zz[0x5C]=one(t[1]>>8);zz[0x5D]=y
       value=(one(0x4C),x,y,tuple(zz),())
      else:value=(*out[:4],())
     else:
      target=(31,v)if v>=0xE000 else(k[0]if v<0xC000 else k[0]+1 if k[1]<0xC000 else k[0],v)
      if k[1]>=0xC000 and v<0xC000:target=(k[0]-1,v)
      summary=summaries.get(target);zz=[None for _ in ZP]
      registers_clobbered={'A','X','Y'}
      if refined:
       writes,registers_clobbered,_,_=effects(target)
       if v==0xEE07 and FAR_TARGETS.get(k):
        writes=set(range(0x58,0x5E));registers_clobbered={'A','Y'}
        for callee in [*FAR_TARGETS[k],(31,0xF237)]:
         ww,rr,_,_=effects(callee);writes|=ww;registers_clobbered|=rr
       returned=RETURN_STATES.get(target)if v!=0xEE07 else None
       zz=[returned[3][address]if returned is not None and address in writes else None if address in writes else value for address,value in zip(ZP,z)]
       if v==0xEE07 and FAR_TARGETS.get(k)and all(callee in RETURN_STATES for callee in FAR_TARGETS[k]):
        returns=[RETURN_STATES[callee]for callee in FAR_TARGETS[k]]
        joined=returns[0]
        for other in returns[1:]:joined=merge(joined,other)
        for address in writes:
         if address not in range(0x58,0x5E)and address not in range(0xE0,0xE4):zz[address]=joined[3][address]
      if summary:
       p,role,newy=summary
       if refined and target in((31,0xF368),(8,0xB4C2),(11,0xD319))and a is not None and all(isinstance(n,int)and(n&15)<7 for n in a):
        role='ruler';newy='ruler_index'
       origin=(k[0],k[1])if refined else()
       zz[ZP.index(p)]=one(('pointer',role,0,*origin));zz[ZP.index(p+1)]=one(('pointer',role,1,*origin))
       return_a=zz[ZP.index(p+1)]if target in((31,0xF2AF),(31,0xF2D7),(31,0xF368),(31,0xF387),(8,0xB491),(8,0xB469),(8,0xB4E1),(8,0xB4C2),(11,0xD319))else None
       return_y=one(newy)if isinstance(newy,int)else y if newy=='keep'else frozenset((n&15)*2 for n in a)if newy=='ruler_index'and a is not None and all(isinstance(n,int)for n in a)else None
       value=(return_a,x if refined and 'X'not in registers_clobbered else None,return_y,tuple(zz),stack if target in BALANCED_POINTER_HELPERS else())
       if target==(11,0xD105):value=(frozenset(range(8)),value[1],one(0),tuple(zz),stack)
       if target==(11,0xD304):value=(frozenset(range(11)),frozenset(range(11)),frozenset(range(17,28)),tuple(zz),stack)
      elif refined:
       returned=RETURN_STATES.get(target)if v!=0xEE07 else None
       regs=[a,x,y]
       for i,name in enumerate(('A','X','Y')):
        if name in registers_clobbered:regs[i]=returned[i]if returned is not None else None
       value=(*regs,tuple(zz),stack if target in BALANCED_POINTER_HELPERS else())
      else:value=EMPTY
      if refined and target==(28,0xDC6B):
       # Original helper scans exactly ten offsets17..26. Phase15 tested every
       # occupancy mask; normal and fullcapacity values both remain included.
       value=(None,frozenset(range(11)),one(27),value[3],())
    # Restrict common counted Y loops at immediate CPY branch, not by intuition.
    if op in('BCC','BCS','BEQ','BNE'):
     before=known.get((k[0],k[1]-2))
     reg_index={'CMP':0,'CPX':1,'CPY':2}.get(before['op'])if before else None
     if not refined and reg_index!=2:reg_index=None
     if ((k[1]+2+(r['operand']if r['operand']<128 else r['operand']-256))&65535)!=k[1]+2 and before and reg_index is not None and before['mode']=='im'and value[reg_index]is not None and all(isinstance(n,int)for n in value[reg_index]):
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
 indirect=[];absolute=[];indexed=[]
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
      context_original_bytes=ORIGINAL_CONTEXTS.get(k,[])if refined else[],
      resolved_pointer_byte_values=[sorted(map(str,s[3][ZP.index(v)]or[])),sorted(map(str,s[3][ZP.index(v+1)]or[]))]if refined and v in ZP and v+1 in ZP else None,
      unresolved_reason=None if kind and ys is not None else'Pointer identity or dynamic index unresolved; this access prevents whole-ROM absence claims'))
  if op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')and md in('zpx','zpy','abx','aby'):
   indices=s[1 if md in('zpx','abx')else 2];iv=sorted(indices)if indices is not None and all(isinstance(n,int)for n in indices)else None
   cpu_addresses={(v+i)&(255 if md in('zpx','zpy')else 65535)for i in(iv if iv is not None else range(256))}
   indexed.append(dict(**r,index_values=iv,physical_zero_page_targets=sorted({address&255 for address in cpu_addresses if address<0x2000 and(address&0x7FF)<256})))
  if md in('ab','abx','aby')and op not in('JSR','JMP')and 0x6000<=v<0x6EE0:
   absolute.append(dict(**r,base_operand=v,index_mode=md,index_values=sorted(s[1 if md=='abx'else 2])if md!='ab'and s[1 if md=='abx'else 2]is not None and all(isinstance(n,int)for n in s[1 if md=='abx'else 2])else None))
 return indirect,absolute,summaries,effect_memo,indexed,states

POINTER_SUMMARIES={
 (31,0xF2AF):(0,'city',0,'6000+32*raw_A'),
 (31,0xF2D7):(0,'officer',0,'63C0+12*raw_A'),
 (31,0xF387):(0,'initial_officer',0,'8000+12*raw_A'),
 (31,0xF308):(0,'ROM_names',None,'901A+10*raw_A'),
 (31,0xF368):(0,'ruler_table_or_adjacent_bytes','input_nibble*2','raw16_LE16_F379'),
 (8,0xB469):(0x20,'city',0,'6000+32*raw_A'),
 (8,0xB491):(0x20,'officer',0,'63C0+12*raw_A'),
 (8,0xB4E1):(0x20,'initial_officer',0,'8000+12*raw_A'),
 (8,0xB4C2):(0x20,'ruler_table_or_adjacent_bytes','input_nibble*2','raw16_LE16_B4D3'),
 (11,0xD105):(0x20,'city',0,'6000+32*raw_A; caps city2..5'),
 (11,0xD283):(0x20,'officer','keep','63C0+12*raw_A'),
 (11,0xD2AB):(0x22,'officer','keep','63C0+12*raw_A'),
 (11,0xD304):(0x20,'city','17..27','6000+32*raw_A; A/X prefix_count_before_first_FF0..10'),
 (11,0xD319):(0x24,'ruler_table_or_adjacent_bytes','input_nibble*2','raw16_LE16_D328')}

def pointernums(fact,known,rom):
 if isinstance(fact,int):return {fact}
 if not(isinstance(fact,tuple)and len(fact)==5 and fact[0]=='pointer'):return None
 _,role,part,b,pc=fact;r=known.get((b,pc))
 if r is None or r['op']!='JSR':return None
 target=mapped((b,pc),r['operand'])
 if role=='city':addresses={0x6000+32*i for i in range(256)}
 elif role=='officer':addresses={0x63C0+12*i for i in range(256)}
 elif role=='initial_officer':addresses={0x8000+12*i for i in range(256)}
 elif role=='ROM_names':addresses={0x901A+10*i for i in range(256)}
 elif role in('ruler','ruler_table_or_adjacent_bytes'):
  table={(31,0xF368):(31,0xF379),(8,0xB4C2):(8,0xB4D3),(11,0xD319):(11,0xD328)}.get(target)
  if table is None:return None
  offset=original(*table);addresses={int.from_bytes(rom[offset+2*i:offset+2*i+2],'little')for i in range(7 if role=='ruler'else 16)}
 else:return None
 return{(p>>8)&255 if part else p&255 for p in addresses}

def address_proof(access,known,rom):
 values=access.get('resolved_pointer_byte_values')
 if not values or not any(values):return None
 parts=[]
 for rawvalues in values:
  part=set()if rawvalues else set(range(256))
  for textvalue in rawvalues:
   value=ast.literal_eval(textvalue);numbers=pointernums(value,known,rom)
   if numbers is None:return None
   part.update(numbers)
  parts.append(part)
 bases={lo|(hi<<8)for lo in parts[0]for hi in parts[1]}
 ys=set(access['Y_values'])if access['Y_values']is not None else set(range(256))
 if access['mode']=='ix':return None # pre-indexing changes which pointerbytes are read
 if not bases or not ys:return None
 low_intersects=any(((address-y)&65535)in bases for first in(0,0x800,0x1000,0x1800)for address in range(first,first+256)for y in ys)if min(bases)<0x2000 or max(bases)>=0xFF01 else False
 stack_intersects=any(((address-y)&65535)in bases for first in(0x100,0x900,0x1100,0x1900)for address in range(first,first+256)for y in ys)if min(bases)<0x2000 or max(bases)>=0xFE01 else False
 aux_addresses={0x6000+city*32+offset for city in range(30)for offset in AUX}
 matches=sorted(address for address in aux_addresses if any(((address-y)&65535)in bases for y in ys))
 return dict(low_byte_values=sorted(parts[0]),high_byte_values=sorted(parts[1]),
   independent_low_high_cross_product=True,unknown_pointer_bytes=[i for i,v in enumerate(values)if not v],base_address_count=len(bases),base_address_min=min(bases),base_address_max=max(bases),
   Y_values=sorted(ys),Y_was_unknown=access['Y_values']is None,may_write_zero_page=low_intersects,may_write_stack_RAM_mirror=stack_intersects,
   possible_auxiliary_effective_addresses=matches,auxiliary_address_intersection_count=len(matches),
   pointer_producer_calls=access['pointer_producer_calls'])

def owners_and_callers(known,edges):
 callers={};entries=set();incoming=Counter(t for targets in edges.values()for t in targets)
 for k,r in known.items():
  if r['op']=='JSR'and r['operand']not in(0xEADE,0xB517,0xEE07):
   target=mapped(k,r['operand'])
   if target in known:entries.add(target);callers.setdefault(target,[]).append(k)
 entries.update(tuple(t)for contract in DISPATCHES.values()for t in contract['mapped_targets']);entries.update(k for k in known if not incoming[k])
 owners={}
 for entry in entries:
  todo=[entry];seen=set()
  while todo:
   k=todo.pop()
   if k in seen or k not in known:continue
   seen.add(k);owners.setdefault(k,set()).add(entry);r=known[k]
   if r['op']=='JSR':
    following=r['cpu']+r['size']+(2 if r['operand']==0xEE07 else 0)
    todo.extend(t for t in edges.get(k,[])if t==mapped(k,following))
   else:todo.extend(edges.get(k,[]))
 return owners,callers

def originalrow(known,k):
 r=known[k];return{key:r[key]for key in('physical_bank','cpu','rom_offset','raw_hex','op','mode','operand')}

def return_summaries(known,edges,states,effects):
 """Join all local RTS exits, excluding unknown computed/missing control tails.

A function's inputs are the conservative union of all audited callers and
external roots. Thus returned byte facts may be used as union summaries,
never as a value specific to just one call. Source does not use this engine.
 """
 results={};contracts=[]
 for entry in sorted(effects):
  todo=[entry];seen=set();exits=[];barriers=[]
  while todo:
   k=todo.pop()
   if k in seen:continue
   seen.add(k)
   if k not in known:barriers.append(['missing_instruction',list(k)]);continue
   r=known[k]
   if r['op']=='RTS':
    if k in states:exits.append(k)
    continue
   if r['op']in('RTI','BRK','?'):barriers.append(['non_RTS_boundary',list(k)]);continue
   targets=edges.get(k,[])
   if r['op']=='JSR'and k not in DISPATCHES:
    following=mapped(k,r['cpu']+r['size']+(2 if r['operand']==0xEE07 else 0))
    targets=[t for t in targets if t==following]
   if not targets:barriers.append(['unresolved_control_exit',list(k)]);continue
   todo.extend(targets)
  if barriers or not exits:continue
  joined=states[exits[0]]
  for k in exits[1:]:joined=merge(joined,states[k])
  results[entry]=joined
  facts={str(address):sorted(map(str,values))for address,values in enumerate(joined[3])if values is not None}
  contracts.append(dict(physical_bank=entry[0],cpu=entry[1],RTS_exits=[originalrow(known,k)for k in exits],
   return_zero_page_byte_facts=facts,register_value_domains=[sorted(map(str,v))if v is not None else None for v in joined[:3]],
   context='May-return union for audited original caller/root inputs; all declared local RTS exits included. Not a termination theorem.'))
 return results,contracts

def backward_contracts(known,edges,effects,site,pointer_z,disjoint_stores):
 """Diagnostic reaching-definition slices, never an exclusion proof.

The bound is explicit: an unfinished slice stays unresolved. Callee entry
edges are separated from return/fallthrough, and all writes retain raw bytes.
 """
 predecessors=LOCAL_PREDECESSORS
 result={}
 for variable in(pointer_z,(pointer_z+1)&255,'Y'):
  queue=deque(predecessors.get(site,[]));seen=set();events=[];truncated=False
  while queue:
   k=queue.popleft()
   if k in seen:continue
   if len(seen)>=512:truncated=True;break
   seen.add(k);r=known[k];op,md,v=r['op'],r['mode'],r['operand'];reason=None
   if op=='JSR':
    target=mapped(k,v)
    if k in DISPATCHES:
     base=DISPATCH_BASE[v]
     if variable!='Y'and variable in range(base,base+5):reason='actual_dispatcher_scratch_definition'
    elif target in POINTER_SUMMARIES and variable!='Y'and variable in(POINTER_SUMMARIES[target][0],POINTER_SUMMARIES[target][0]+1):reason='original_record_pointer_factory'
    else:
     effect=effects.get(target,(set(range(256)),{'A','X','Y'},set(),['unresolved_callee']))
     if(variable=='Y'and 'Y'in effect[1])or(variable!='Y'and variable in effect[0]):reason='callee_may_write_boundary'
   elif variable=='Y'and op in('LDY','TAY','INY','DEY'):reason='nearest_index_definition_or_update'
   elif variable!='Y'and op in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR'):
    if md in('zp','ab')and v<0x2000 and(v&0x7FF)==variable:reason='direct_byte_definition_or_update'
    elif md in('zpx','zpy','abx','aby')and variable in INDEXED_TARGETS.get(k,set(range(256))):reason='possible_indexed_byte_definition'
    elif md in('ix','iy')and k not in disjoint_stores:reason='possible_indirect_byte_alias_boundary'
   if reason:
    context=[originalrow(known,(k[0],pc))for pc in BANK_POSITIONS[k[0]][bisect.bisect_left(BANK_POSITIONS[k[0]],k[1]-12):bisect.bisect_left(BANK_POSITIONS[k[0]],k[1])]]
    events.append(dict(**originalrow(known,k),reason=reason,preceding_original_context=context));continue
   previous=predecessors.get(k,[])
   if not previous:events.append(dict(**originalrow(known,k),reason='external_or_unresolved_entry_input'))
   else:queue.extend(previous)
  result[str(variable)]=dict(events=events,visited_original_positions=len(seen),slice_limit=512,truncated=truncated,
   meaning='Diagnostic producer boundaries; not a claim that all actual inputs or external/interrupt paths were resolved.')
 return result

def mirror_inventory(known,indexed):
 index={(r['physical_bank'],r['cpu']):r for r in indexed};rows=[]
 for k,r in sorted(known.items()):
  if r['op']not in('STA','STX','STY','INC','DEC','ASL','LSR','ROL','ROR')or r['mode']not in('zp','zpx','zpy','ab','abx','aby'):continue
  md=r['mode'];v=r['operand'];values=range(256)if md in('zpx','zpy','abx','aby')else(0,)
  addresses={(v+i)&(255 if md in('zpx','zpy')else 65535)for i in values}
  raw={a for a in addresses if a<0x2000 and(a&0x7FF)<256}
  if not raw:continue
  proof=index.get(k)
  rows.append(dict(**originalrow(known,k),raw_index_domain='all0..255'if md in('zpx','zpy','abx','aby')else'no_index',
   raw_possible_CPU_addresses=sorted(raw),normalized_zero_page_bytes=sorted({a&255 for a in raw}),
   refined_index_contract=proof,normalization='CPU RAM address<2000 is mirrored modulo0800; zero-page iff normalized<0100. Effective indexed address wraps16bits.'))
 return dict(schema='phase18-original-RAM-mirror-write-inventory-v1',ROM_sha256=ROM_SHA256,
  direct_mirror_above_zero_page_count=sum(r['mode']in('ab','zp')and any(a>=256 for a in r['raw_possible_CPU_addresses'])for r in rows),
  indexed_may_write_zero_page_count=sum(r['mode']in('zpx','zpy','abx','aby')for r in rows),
  zero_page_indexed_store_instruction_count=sum(r['mode']in('zpx','zpy')for r in rows),writes=rows)

def main():
 p=argparse.ArgumentParser();p.add_argument('rom');p.add_argument('--passes',type=int,default=4);args=p.parse_args()
 rom=Path(args.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 global DISPATCHES,FAR_TARGETS,INDEXED_TARGETS,DISJOINT_STACK_STORES,RETURN_STATES,ORIGINAL_CONTEXTS,LOCAL_PREDECESSORS,BANK_POSITIONS
 control_path=ROOT/'analysis/phase18/control/control-contracts.json';control=read(control_path)
 atlas_path=ROOT/'analysis/phase18/control/instruction-atlas.json';atlas=read(atlas_path)
 for contract in control['bounded_dispatch_tables']:
  k=contract['call']['physical_bank'],contract['call']['cpu']
  DISPATCHES[k]=dict(**contract,mapped_targets=[list(mapped(k,target))for target in contract['targets']])
 old=read(BASE/'alias-refinement.json');baseline=read(BASE/'pointer-accesses.json')
 known={(r['physical_bank'],r['cpu']):r for r in atlas['instructions']}
 edges={(r['physical_bank'],r['cpu']):[tuple(t)for t in r['targets']]for r in atlas['edges']}
 FAR_TARGETS={k:[t for t in edges.get(k,[])if t!=mapped(k,r['cpu']+5)]for k,r in known.items()if r['op']=='JSR'and r['operand']==0xEE07}
 BANK_POSITIONS={bank:sorted(pc for b,pc in known if b==bank)for bank in range(32)}
 ORIGINAL_CONTEXTS={k:[dict(cpu=pc,rom_offset=known[k[0],pc]['rom_offset'],raw_hex=known[k[0],pc]['raw_hex'])for pc in BANK_POSITIONS[k[0]][bisect.bisect_left(BANK_POSITIONS[k[0]],k[1]-24):bisect.bisect_left(BANK_POSITIONS[k[0]],k[1])]]for k in known}
 for k,targets in edges.items():
  r=known[k]
  for target in targets:
   if r['op']=='JSR'and k not in DISPATCHES and target!=mapped(k,r['cpu']+r['size']+(2 if r['operand']==0xEE07 else 0)):continue
   LOCAL_PREDECESSORS.setdefault(target,[]).append(k)
 for r in known.values():assert rom[r['rom_offset']:r['rom_offset']+r['size']]==bytes.fromhex(r['raw_hex'])and r['rom_offset']==original(r['physical_bank'],r['cpu'])
 oldZP,oldEMPTY=prior.ZP,prior.EMPTY;prior.ZP=ZP;prior.EMPTY=EMPTY
 disjoint={};rounds=[];accesses=baseline['accesses'];effects={};indexed=[]
 try:
  for step in range(args.passes):
   if step==0:accesses=[] # bootstrap with no assumptions from the older taint
   for access in accesses:
    if access['op']!='STA':continue
    proof=address_proof(access,known,rom)
    if proof is not None and not proof['may_write_zero_page']:
     disjoint[access['physical_bank'],access['cpu']]=proof
   INDEXED_TARGETS={(r['physical_bank'],r['cpu']):set(r['physical_zero_page_targets'])for r in indexed}
   DISJOINT_STACK_STORES={k for k,proof in disjoint.items()if not proof['may_write_stack_RAM_mirror']}
   print('abstract round',step+1,'proved non-ZP stores',len(disjoint),flush=True)
   accesses,absolute,summaries,effects,indexed,states=refined_dataflow(known,edges,rom,disjoint)
   RETURN_STATES,return_contracts=return_summaries(known,edges,states,effects)
   index={(r['physical_bank'],r['cpu']):r for r in accesses}
   candidate_proofs=[address_proof(index[x['physical_bank'],x['cpu']],known,rom)for x in old['remaining_candidates']]
   safe=sum(proof is not None and proof['auxiliary_address_intersection_count']==0 for proof in candidate_proofs)
   rounds.append(dict(round=step+1,proved_non_zero_page_stores=len(disjoint),prior_candidates_with_disjoint_effective_address_domain=safe,
    all_indirect_accesses=len(accesses),known_pointer_accesses=sum(x['pointer_kind']is not None for x in accesses),local_return_summaries=len(RETURN_STATES)))
   print('589 disjoint',safe,flush=True)
 finally:prior.ZP,prior.EMPTY=oldZP,oldEMPTY
 owners,callers=owners_and_callers(known,edges)
 rows=[]
 for previous in old['remaining_candidates']:
  k=previous['physical_bank'],previous['cpu'];r=index[k];proof=address_proof(r,known,rom)
  row=dict(**r,backward_pointer_and_index_boundaries=backward_contracts(known,edges,effects,k,r['pointer_zero_page'],disjoint),prior_pointer_kind=previous['pointer_kind'],prior_Y_values=previous['Y_values'],
   classification='proved_disjoint_auxiliary_address_domain'if proof and not proof['auxiliary_address_intersection_count']else'possible_city_auxiliary_alias'if proof else'unresolved_pointer_or_index_contract',
   address_contract=proof,containing_procedure_entries=[dict(**originalrow(known,q),direct_callers=[originalrow(known,c)for c in callers.get(q,[])])for q in sorted(owners.get(k,set()))])
  rows.append(row)
 counts=Counter(r['classification']for r in rows)
 old_access_keys={(r['physical_bank'],r['cpu'])for r in baseline['accesses']}
 old_candidate_keys={(r['physical_bank'],r['cpu'])for r in old['remaining_candidates']}
 all_rows=[];new_rows=[];reopened=[]
 for r in accesses:
  k=r['physical_bank'],r['cpu'];proof=address_proof(r,known,rom)
  classification='proved_disjoint_auxiliary_address_domain'if proof and not proof['auxiliary_address_intersection_count']else'possible_city_auxiliary_alias'if proof else'unresolved_pointer_or_index_contract'
  item=dict(**r,classification=classification,address_contract=proof,
   phase17_instruction_access=k in old_access_keys,phase17_remaining_candidate=k in old_candidate_keys)
  all_rows.append(item)
  if k not in old_access_keys:
   item['containing_procedure_entries']=[originalrow(known,q)for q in sorted(owners.get(k,set()))];new_rows.append(item)
  elif k not in old_candidate_keys and classification!='proved_disjoint_auxiliary_address_domain':reopened.append(item)
 save('all-indirect-accesses.json',dict(schema='phase18-all-corrected-CFG-indirect-accesses-v1',ROM_sha256=ROM_SHA256,
  instruction_positions=len(known),indirect_access_count=len(all_rows),classification_counts=dict(Counter(r['classification']for r in all_rows)),accesses=all_rows,
  domain='All indirect modes in corrected trustedCFG, not arbitrary executable bytes or external mapper/selector states.'))
 save('new-indirect-accesses.json',dict(schema='phase18-new-corrected-CFG-indirect-accesses-v1',ROM_sha256=ROM_SHA256,
  phase17_indirect_access_count=len(old_access_keys),phase18_indirect_access_count=len(all_rows),new_indirect_access_count=len(new_rows),
  new_possible_auxiliary_alias_count=sum(r['classification']!='proved_disjoint_auxiliary_address_domain'for r in new_rows),
  classification_counts=dict(Counter(r['classification']for r in new_rows)),accesses=new_rows,
  prior_non_candidate_not_reproved_disjoint_count=len(reopened),prior_non_candidate_not_reproved_disjoint=reopened,
  limitation='Reopened coarse numeric domains are not discoveries of actual field use; stronger frozen local proofs may remain valid in their explicit domains.'))
 save('RAM-mirror-write-inventory.json',mirror_inventory(known,indexed))
 save('access-contracts.json',dict(schema='phase18-city-auxiliary-access-contracts-v1',ROM_sha256=ROM_SHA256,
  baseline_candidate_count=len(rows),classification_counts=dict(counts),abstract_rounds=rounds,accesses=rows,
  official_field_names=dict(city_byte1=None,city_bytes28_31=None),source_CPU_cases=0,
  limitation='Context unions cover the audited trusted originalCFG only. No totalcontrol-reachability or unused/reserved theorem. Rawruler indexes7..15 and unknownY remain conservative; all pointerbyte cross-products are independent.'))
 save('pointer-preserving-store-proofs.json',dict(schema='phase18-pointer-preserving-store-proofs-v1',ROM_sha256=ROM_SHA256,
  count=len(disjoint),stores=[dict(**originalrow(known,k),address_proof=v)for k,v in sorted(disjoint.items())]))
 save('local-return-contracts.json',dict(schema='phase18-local-original-return-contracts-v1',ROM_sha256=ROM_SHA256,contracts=return_contracts))
 save('indexed-store-proofs.json',dict(schema='phase18-original-indexed-store-footprints-v1',ROM_sha256=ROM_SHA256,stores=indexed))
 save('call-effect-summaries.json',dict(schema='phase18-original-callee-may-write-summaries-v1',ROM_sha256=ROM_SHA256,
  summaries=[dict(physical_bank=k[0],cpu=k[1],zero_page_may_write=sorted(v[0]),register_may_write=sorted(v[1]),
   instruction_count=len(v[2]),barriers=v[3])for k,v in sorted(effects.items())]))
 save('analysis-summary.json',dict(schema='phase18-city-auxiliary-static-summary-v1',status='analyzed',ROM_sha256=ROM_SHA256,
  instruction_count=len(known),baseline_candidate_count=len(rows),classification_counts=dict(counts),
  by_bank=dict(Counter(str(r['physical_bank'])for r in rows)),by_pointer_zero_page=dict(Counter(str(r['pointer_zero_page'])for r in rows)),
  abstract_rounds=rounds,source_CPU_cases=0,new_indirect_access_count=len(new_rows),new_possible_auxiliary_alias_count=sum(r['classification']!='proved_disjoint_auxiliary_address_domain'for r in new_rows),all_indirect_access_count=len(all_rows),
  all_indirect_classification_counts=dict(Counter(r['classification']for r in all_rows)),prior_non_candidate_not_reproved_disjoint_count=len(reopened),
  finite_refinement_round_count=args.passes,fixed_point_proven=False,
  analyzer_path='scripts/analyze_city_auxiliary_accesses.py',analyzer_sha256=sha(__file__),
  artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in(atlas_path,control_path,BASE/'instruction-atlas.json',BASE/'alias-refinement.json',BASE/'pointer-accesses.json',ROOT/'scripts/analyze_field_semantics.py')},
  limitations=['This is static originalbyte analysis, not a nativeCPUtrace or newproduction semanticservice.',
   'Declared noauxiliary address intersection is restricted to proved current pointer/Y contracts, not arbitraryjump or mapper entry.',
   'Officialmeaning remains unresolved when no dedicatedproducer/UIlabel hasbeen proved.']))
 print(json.dumps(dict(candidate_count=len(rows),classifications=dict(counts),rounds=rounds),ensure_ascii=False))
if __name__=='__main__':main()
