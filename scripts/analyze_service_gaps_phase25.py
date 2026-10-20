#!/usr/bin/env python3
"""Read-only source/receipt service index. No recovered code, CPU or core runs.

Only this phase25/services output directory is written. A declared owner is
not a proof of its whole closure, and a wait is not an unimplemented service.
"""
from collections import Counter, defaultdict
from pathlib import Path
import argparse,ast,hashlib,json,re,sys,struct
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/phase25/services'
BASELINE='analysis/phase24/verification.json'
REQUIREMENTS='analysis/phase24/acceptance/requirements.json'
ATLAS='analysis/phase18/control/instruction-atlas.json'
MISSING=object()


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def phase(path):return int(re.search(r'/phase(\d+)/','/'+str(path)).group(1))
def evidence(path,pointer='',**extra):return dict(path=str(path),sha256=digest(ROOT/path),json_pointer=pointer,**extra)


class Registry:
 """Finite AST literals and route predicates only; never imports Source."""
 def __init__(self,paths,frontdoor='PointerLifecycleSceneCoordinator'):
  self.frontdoor=frontdoor
  self.modules={};self.classes={};self.cache={}
  for path in paths:
   tree=ast.parse((ROOT/path).read_text());module=Path(path).stem;self.modules[module]=(path,tree)
   for node in tree.body:
    if isinstance(node,ast.ClassDef):
     if node.name not in self.classes:self.classes[node.name]=(path,node)
  self.routes=self.route_rules()
 def parents(self,name):
  if name not in self.classes:return []
  return [n.id for n in self.classes[name][1].bases if isinstance(n,ast.Name)]
 def lineage(self,name,seen=None):
  seen=set()if seen is None else seen
  if name in seen or name not in self.classes:return []
  seen.add(name);return [name]+[x for p in self.parents(name)for x in self.lineage(p,seen)]
 def method(self,cls,name):
  for owner in self.lineage(cls):
   path,node=self.classes[owner]
   for item in node.body:
    if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef))and item.name==name:return path,item
  return None
 def attr(self,cls,name,depth=0):
  if depth>256:return MISSING
  key=cls,name
  if key in self.cache:return self.cache[key]
  self.cache[key]=MISSING
  for owner in self.lineage(cls):
   path,node=self.classes[owner]
   for item in node.body:
    if isinstance(item,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in item.targets):
     value=self.value(item.value,owner=owner,depth=depth+1)
     if value is not MISSING:self.cache[key]=value
     return value
  return MISSING
 def value(self,node,env=None,owner=None,depth=0):
  env={}if env is None else env
  if depth>256:return MISSING
  v=lambda x:self.value(x,env,owner,depth+1)
  if node is None:return None
  if isinstance(node,ast.Constant):return node.value
  if isinstance(node,ast.Name):
   if node.id in env:return env[node.id]
   if owner:
    found=self.attr(owner,node.id,depth+1)
    if found is not MISSING:return found
   return MISSING
  if isinstance(node,ast.Attribute):
   if isinstance(node.value,ast.Name)and node.value.id in self.classes:return self.attr(node.value.id,node.attr,depth+1)
   if isinstance(node.value,ast.Name)and node.value.id=='call':return env.get(node.attr,MISSING)
   return MISSING
  if isinstance(node,(ast.Tuple,ast.List,ast.Set)):
   out=[]
   for x in node.elts:
    value=v(x.value if isinstance(x,ast.Starred)else x)
    if value is MISSING:return MISSING
    out.extend(value)if isinstance(x,ast.Starred)else out.append(value)
   return set(out)if isinstance(node,ast.Set)else tuple(out)
  if isinstance(node,ast.UnaryOp):
   a=v(node.operand)
   if a is MISSING:return MISSING
   if isinstance(node.op,ast.Not):return not a
   if isinstance(node.op,ast.USub):return -a
  if isinstance(node,ast.BinOp):
   a,b=v(node.left),v(node.right)
   if a is MISSING or b is MISSING:return MISSING
   if isinstance(node.op,ast.Add):return a+b
   if isinstance(node.op,ast.BitOr):return a|b
  if isinstance(node,ast.Subscript):
   a=v(node.value)
   if a is MISSING:return MISSING
   if isinstance(node.slice,ast.Slice):
    lo=v(node.slice.lower)if node.slice.lower else None;hi=v(node.slice.upper)if node.slice.upper else None
    return a[lo:hi]if lo is not MISSING and hi is not MISSING else MISSING
   b=v(node.slice)
   try:return a[b]if b is not MISSING else MISSING
   except(IndexError,KeyError,TypeError):return MISSING
  if isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id in('tuple','set','frozenset','list')and len(node.args)==1:
   return v(node.args[0])
  if isinstance(node,ast.BoolOp):
   parts=[v(x)for x in node.values]
   if isinstance(node.op,ast.And):return False if any(x is False for x in parts)else MISSING if MISSING in parts else all(parts)
   return True if any(x is True for x in parts)else MISSING if MISSING in parts else any(parts)
  if isinstance(node,ast.Compare):
   vals=[v(node.left)]+[v(x)for x in node.comparators]
   if any(x is MISSING for x in vals):return MISSING
   for a,op,b in zip(vals,node.ops,vals[1:]):
    if isinstance(op,ast.Eq):r=a==b
    elif isinstance(op,ast.NotEq):r=a!=b
    elif isinstance(op,ast.In):r=a in b
    elif isinstance(op,ast.NotIn):r=a not in b
    elif isinstance(op,ast.Lt):r=a<b
    else:return MISSING
    if not r:return False
   return True
  return MISSING
 def entry_values(self,cls):
  out=set()
  for attr in('PUBLIC_ENTRIES','LOCAL_ENTRIES','ENTRIES','FIXED'):
   vals=self.attr(cls,attr)
   if vals is not MISSING and isinstance(vals,(tuple,list,set,frozenset)):out.update(x for x in vals if type(x)is int)
  method=self.method(cls,'_entry')
  if method:
   for node in ast.walk(method[1]):
    if isinstance(node,ast.Compare)and isinstance(node.left,ast.Name)and node.left.id=='entry'and len(node.ops)==1 and isinstance(node.ops[0],ast.Eq):
     val=self.value(node.comparators[0]);
     if type(val)is int:out.add(val)
  return out
 def route_rules(self):
  out=[]
  # This exact factory is the phase24 named frontdoor. No synthetic instantiation.
  for cls in self.lineage(self.frontdoor):
   method=self.method(cls,'_resolve_call')
   if not method:continue
   path,fn=method
   if path!=self.classes[cls][0]:continue
   # Additive owners use an early "not my pair/entry -> super" guard.
   if cls!='SceneCoordinator':
    guard=next((n for n in fn.body if isinstance(n,ast.If)and any(isinstance(x,ast.Return)and isinstance(x.value,ast.Call)and isinstance(x.value.func,ast.Attribute)and x.value.func.attr=='_resolve_call'for x in n.body)),None)
    owners=[n.value.func.id for n in ast.walk(fn)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='owner'for t in n.targets)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id in self.classes]
    if guard and owners:out.append(dict(owner=owners[0],coordinator=cls,path=path,line=guard.lineno,predicate=ast.unparse(guard.test),test=guard.test,inverse=True,entry_check=False))
   else:
    for node in ast.walk(fn):
     if not isinstance(node,ast.If):continue
     assign=next((x for x in node.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='owner'for t in x.targets)),None)
     if not assign:continue
     value=assign.value;owner=None;special=None
     if isinstance(value,ast.Call)and isinstance(value.func,ast.Name)and value.func.id in self.classes:owner=value.func.id
     elif isinstance(value,ast.IfExp):owner='BattleSetupAI';special='setup_or_battle'
     elif isinstance(value,ast.Call)and isinstance(value.func,ast.Attribute)and value.func.attr=='_new_controller':
      owner={3:'BattleSceneController',4:'AttackSceneController',5:'DuelSceneController'}.get(self.value(value.args[0]))
     if owner:out.append(dict(owner=owner,coordinator=cls,path=path,line=node.lineno,predicate=ast.unparse(node.test),test=node.test,inverse=False,entry_check=special is not None or owner in('AttackSceneController','BattleSceneController'),special=special))
  return out
 def resolve(self,target,banks=None):
  if type(target)is not int:return dict(status='identity_unknown',owners=[],reason='Target is not a static or captured address')
  pair=tuple(banks[1:3])if banks and len(banks)==4 else None
  # A fixed service does not need an invented data8000 mapping. Evaluate all
  # supported pair domains and require an identical declared owner.
  if pair is None and target>=0xE000:
   options=[self.resolve(target,[None,*p,31])for p in((8,9),(10,11),(12,13),(14,15),(23,24),(25,26),(27,28),(29,30))]
   names={tuple(x['owners'])for x in options}
   if len(names)==1 and next(iter(names)):return {**options[0],'bank_scope':'fixed31; identical owner over declared pair domains; data8000 unknown'}
   return dict(status='mapping_or_route_unknown',owners=[],reason='No unique owner without captured mapping')
  if pair is None:return dict(status='mapping_unknown',owners=[],reason='Banked target requires actual pair; address alone is not service identity')
  env=dict(pair=pair,target=target,entry_banks=tuple(banks))
  for rule in self.routes:
   yes=self.value(rule['test'],env)
   if rule['inverse']:yes=not yes if yes is not MISSING else MISSING
   if yes is MISSING:return dict(status='conditional_route_unknown',owners=[],possible_owner=rule['owner'],route_path=rule['path'],route_line=rule['line'],reason='A higher-priority route predicate is outside the finite AST model; do not silently fall through to a lower owner')
   if yes is not True:continue
   owner='BattleSceneController'if rule.get('special')=='setup_or_battle'and pair==(12,13)else rule['owner']
   if rule['entry_check']and target not in self.entry_values(owner):continue
   return dict(status='declared_current_owner',owners=[owner],route_path=rule['path'],route_line=rule['line'],predicate=rule['predicate'],owner_source=self.classes[owner][0],owner_scope='Static route declaration; does not prove this entry/caller completes or full transitive closure')
  # Exact fallback banked_graphics method dictionary is separately visible.
  method=self.method('SceneInitialization','banked_graphics')
  if method:
   for node in ast.walk(method[1]):
    if isinstance(node,ast.Dict):
     for key,value in zip(node.keys,node.values):
      if self.value(key)==pair and isinstance(value,ast.Dict)and target in[self.value(x)for x in value.keys]:
       return dict(status='declared_current_owner',owners=['SceneInitialization'],route_path=method[0],route_line=node.lineno,owner_source=self.classes['SceneInitialization'][0],owner_scope='Exact declared banked_graphics fallback; input readiness not assumed')
  method=self.method('SceneCoordinator','_presentation_owns')
  if method:
   ret=next((n for n in method[1].body if isinstance(n,ast.Return)),None)
   if ret and self.value(ret.value,env)is True:return dict(status='declared_semantic_presentation_owner',owners=['BattlePresentationServices'],route_path=method[0],route_line=ret.lineno,owner_source=self.classes['BattlePresentationServices'][0],owner_scope='Semantic facade may exclude transient CPU registers; not exact-controller equivalence')
  return dict(status='no_declared_owner_in_bounded_route_model',owners=[],reason='Bounded AST model found no matching route; not a whole-program unimplemented proof')


def context_key(target,banks,caller):
 if type(target)is not int:return 'unresolved:'+caller
 if target>=0xE000:return f'bank31:{target:04X}'
 if banks and len(banks)==4:
  physical=banks[(target-0x8000)//0x2000]if 0x8000<=target<0x10000 else None
  if physical is not None:return f'bank{physical:02d}:{target:04X}'
 return f'mapping-unresolved:{target:04X}:{caller}'


def receipt_inputs():
 out=[]
 for p in(ROOT/'analysis').glob('phase*/**/*.json'):
  rel=str(p.relative_to(ROOT))
  if phase(rel)>24 or p.name not in('validation.json','source-integration.json','integration.json','cooperation-integration.json','ui-integration.json','boot-integration.json'):continue
  if any(x.startswith('exploratory')for x in p.parts)or any(x in p.parts for x in('runtime','runtime-repeat','regression','fields-static','core-provenance')):continue
  if p.stat().st_size<=20000000:out.append(rel)
 extra='analysis/phase25/source-integration.json'
 if(ROOT/extra).exists()and read(extra).get('status')=='passed':out.append(extra)
 return sorted(out)


def observations(reg,paths):
 services={};events=[];scanned=[]
 def add(path,ptr,node,ctx,kind):
  target=node.get('target',node.get('stop_PC'))
  if target is None and isinstance(node.get('final_registers'),dict):target=node['final_registers'].get('pc')
  banks=node.get('banks',node.get('entry_banks',node.get('stop_banks',node.get('final_banks',ctx.get('banks')))))
  if not(isinstance(banks,(tuple,list))and len(banks)==4):banks=None
  if type(target)is not int:target=None
  source_case=ctx.get('case',ctx.get('name',ctx.get('entry')))
  provenance=node.get('provenance',{})if isinstance(node.get('provenance'),dict)else{}
  origin=node.get('origin',provenance.get('origin',ctx.get('origin')))
  domain=node.get('domain',ctx.get('domain'))
  mode=node.get('mode',ctx.get('mode'))
  subtype='actual_Native_snapshot_originalCPU_reached_caller'if origin=='actual_Native_snapshot_originalCPU_reached_caller'else'passive_Native_callee_capture'if'passive'in str(origin or domain)else'controlled_CPU_fixture'if'controlled'in str(domain)else'validator_with_original_helper_mode'if mode in('external_CPU','original_fixed_helpers')else'origin_not_recorded_in_this_row'
  caller=node.get('call_pc',node.get('caller_call_PC'));record=f'{path}#{ptr}'
  has_target=type(node.get('target'))is int
  lastcall=next((r for r in reversed(node.get('calls',[]))if isinstance(r,dict)and r.get('target')==target),None)
  if lastcall is not None:has_target=True;caller=lastcall.get('call_pc',caller)
  address_kind='actual_callee_target'if has_target else'execution_stop_location_not_service_entry'
  route=reg.resolve(target,banks)if has_target else dict(status='not_a_callee_identity',owners=[],reason='A stopped PC may be inside an implemented service; it is not automatically a missing callee entry')
  comparison=node.get('comparison',ctx.get('comparison'));status=node.get('source_status',node.get('status',comparison))
  intentional=node.get('domain')in('strict_dependency_fixture','strict_missing_dependency_fixture')or any(s in str(source_case).lower()for s in('strict-no-','no-services','no_services','unowned','missing-owner'))
  if not has_target and (status=='waiting'or node.get('pending')or'wait'in str(node.get('group',''))):disposition='original_software_or_hardware_wait_not_missing_entry'
  elif not has_target and'permanent_halt'in str(node.get('group','')):disposition='implemented_permanent_diagnostic_not_missing_entry'
  elif not has_target and not intentional:disposition='execution_prefix_location_requires_callee_context'
  elif intentional:disposition='intentional_dependency_fixture_not_missing_inventory'
  elif kind=='callback'and status in('returned','reset_boundary','nonlocal_return'):disposition='observed_callback_completion_not_closure_proof'
  elif route['owners']and status=='waiting':disposition='implemented_owner_waiting_for_explicit_input'
  elif route['owners']:disposition='prefix_has_current_declared_owner_not_unimplemented'
  elif target is None or banks is None and target<0xE000:disposition='insufficient_identity_or_mapper_context'
  else:disposition='bounded_unresolved_route_requires_reproduction'
  key=context_key(target,banks,record)if has_target else f'execution-location:{path}:{target}'
  evt=dict(service_key=key,evidence_level='existing_validation_execution_record',record_kind=kind,address_kind=address_kind,stop_location_owner_candidate=reg.resolve(target,banks)if not has_target else None,receipt=path,json_pointer=ptr,receipt_phase=phase(path),case=source_case,
   target=target,entry_banks=banks,caller_call_PC=caller,source_entry=ctx.get('entry'),status=status,comparison=comparison,
   validation_mode=mode,controlled_domain=domain,origin=origin,execution_origin_subtype=subtype,original_helper_calls_in_parent=ctx.get('external_CPU_calls',ctx.get('original_fixed_helper_calls')),pending=node.get('pending'),helper_owner_counts=node.get('helper_owner_counts'),disposition=disposition,current_route=route,
   scope='Existing receipt observation only; no new Source/CPU/Native run. A controlled fixture or original-helper mode is not promoted to a natural production route.')
  events.append(evt)
  row=services.setdefault(key,dict(service_key=key,index_key_kind='service_identity'if has_target and not key.startswith(('unresolved:','mapping-unresolved:'))else'execution_or_mapping_context_group_not_unique_service',target=target,physical_bank=31 if target is not None and target>=0xE000 else banks[(target-0x8000)//0x2000]if target is not None and banks and 0x8000<=target<=0xFFFF else None,owner_candidates=[],contexts=[],disposition_counts=Counter()))
  row['owner_candidates']=sorted(set(row['owner_candidates'])|set(route['owners']));row['contexts'].append(len(events)-1);row['disposition_counts'][disposition]+=1
 for path in paths:
  data=read(path);scanned.append(dict(path=path,sha256=digest(ROOT/path),status=data.get('status'),schema=data.get('schema')))
  def walk(v,ptr='',ctx=None):
   ctx={}if ctx is None else ctx
   if isinstance(v,dict):
    local=dict(ctx)
    for key in('case','name','entry','mode','comparison','domain','origin','external_CPU_calls','original_fixed_helper_calls'):
     if key in v and not isinstance(v[key],(dict,list)):local[key]=v[key]
    for key in('banks','entry_banks','stop_banks'):
     if isinstance(v.get(key),list)and len(v[key])==4:local['banks']=v[key]
    cmp=v.get('comparison','');st=v.get('source_status',v.get('status'))
    prefix=isinstance(cmp,str)and any(s in cmp for s in('prefix','waiting','dependency'))
    if prefix or st in('dependency','waiting','blocked','unimplemented'):
     add(path,ptr,v,local,'pause_or_prefix');return
    if type(v.get('target'))is int and st in('returned','dependency','waiting','reset_boundary','nonlocal_return')and('banks'in v or 'kind'in v):
     add(path,ptr,v,local,'callback');return
    for key,child in v.items():
     if key not in('guards','model_checks','checks','failures','source_sha256','source_and_validator_sha256','artifact_sha256','artifact_and_dependency_sha256'):walk(child,ptr+'/'+str(key).replace('~','~0').replace('/','~1'),local)
   elif isinstance(v,list):
    for i,child in enumerate(v):walk(child,ptr+'/'+str(i),ctx)
  walk(data)
 return sorted(services.values(),key=lambda r:r['service_key']),events,scanned


def syntax(reg):
 calls=[];markers=[];catalog=[]
 for module,(path,tree)in reg.modules.items():
  def walk(node,cls=None,fn=None):
   if isinstance(node,ast.ClassDef):cls=node.name
   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):fn=node.name
   if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and node.func.attr in('_external','_service','_hook','_scene_service'):
    vals=[reg.value(arg)for arg in node.args];pc=vals[0]if len(vals)>=3 and type(vals[0])is int else None;target=vals[1]if len(vals)>=3 and type(vals[1])is int else vals[0]if vals and type(vals[0])is int else None
    calls.append(dict(syntax_key=f'{path}:{node.lineno}:{cls or "module"}.{fn or "module"}',path=path,line=node.lineno,class_name=cls,function=fn,call_PC=pc,target=target,expression=ast.unparse(node)[:700],evidence_level='syntax_only',state='not_classified_as_unimplemented',scope='AST declaration only. Literal target is not a mapper/caller reachability proof.'))
   if isinstance(node,ast.Return)and isinstance(node.value,ast.Dict):
    vals={reg.value(k):reg.value(v)for k,v in zip(node.value.keys,node.value.values)if k is not None}
    if vals.get('status')in('dependency','waiting','unimplemented','blocked'):
     markers.append(dict(syntax_key=f'{path}:{node.lineno}:{cls or "module"}.{fn or "module"}',path=path,line=node.lineno,class_name=cls,function=fn,declared_status=vals['status'],expression=ast.unparse(node)[:1000],evidence_level='syntax_only',state='generic_guard_or_boundary_not_missing_count'))
   for child in ast.iter_child_nodes(node):walk(child,cls,fn)
  walk(tree)
 for cls,(path,node)in reg.classes.items():
  entries=reg.entry_values(cls)
  if entries:catalog.append(dict(class_name=cls,path=path,line=node.lineno,entry_addresses=sorted(entries),evidence_level='syntax_only_entry_declaration',scope='Entry declaration or literal _entry branch, not universal routing/closure proof'))
 return calls,markers,catalog


def static_calls(reg):
 atlas=read(ATLAS);groups={}
 for row in atlas['instructions']:
  if row['op']not in('JSR','JMP')or row['mode']not in('ab',):continue
  target=row['operand'];bank=row['physical_bank'];cpu=row['cpu']
  same_window=(cpu//0x2000)==(target//0x2000)
  physical=31 if target>=0xE000 else bank if same_window else None
  key=f'bank{physical:02d}:{target:04X}'if physical is not None else f'static-crosswindow-unresolved:{bank}:{cpu:04X}:{target:04X}'
  route=reg.resolve(target,None)
  item=groups.setdefault(key,dict(service_key=key,target=target,logical_target_physical_bank=physical,current_route=route,trusted_callsites=[],evidence_level='bounded_trusted_static_discovery',state='local_or_service_call_static_only',scope='Trusted original opcode. Only a fixed31 or same mapped8KiB window target has a physical identity here. The source physical bank does not establish the other PRG windows. Local calls may execute within an existing owner; no current dynamic coverage or whole-caller completion is claimed.'))
  item['trusted_callsites'].append({k:row[k]for k in('physical_bank','cpu','rom_offset','raw_hex','op','operand')})
 return sorted(groups.values(),key=lambda r:r['service_key'])


def captured_callers(reg):
 path='analysis/phase13/dependencies/inventory.json';data=read(path);rows=[];pins={path:digest(ROOT/path)}
 for i,row in enumerate(data['actual_farcallee_boundaries']):
  target=row['CPU'];banks=row['banks'];rows.append(dict(service_key=context_key(target,banks,path+str(i)),target=target,physical_bank=row['physical_bank'],entry_banks=banks,caller_call_PC=row['caller_call_PC'],evidence_level='existing_validation_execution_record',execution_origin_subtype='actual_Native_snapshot_originalCPU_reached_caller',evidence=evidence(path,'/actual_farcallee_boundaries/'+str(i)),current_route=reg.resolve(target,banks),scope='Native saved point followed by independent originalCPU continuation without new interrupts; not a captured original-core internal entry. Current static owner is separate from a new source-return proof.'))
 path='analysis/phase24/cpu-lifecycle/evidence.json';data=read(path);pins[path]=digest(ROOT/path)
 for rel in sorted(data['artifact_sha256']):
  if not rel.endswith('/context.json'):continue
  context=read(rel);r=context.get('registers',{});banks=context.get('physical_banks');target=r.get('pc')
  if type(target)is not int or not banks:continue
  pins[rel]=digest(ROOT/rel)
  rows.append(dict(service_key=context_key(target,banks,rel),target=target,entry_banks=banks,caller_call_PC=None,evidence_level='existing_validation_execution_record',execution_origin_subtype='passive_Native_callee_capture',evidence=evidence(rel),current_route=reg.resolve(target,banks),scope='Actual software state and real stack. N163 is an explicit shared CPU/Source fixture, not captured Native device state; no new replay.'))
 path='analysis/phase25/runtime/evidence.json'
 if(ROOT/path).exists():
  data=read(path);assert data['status']=='passed';pins[path]=digest(ROOT/path)
  for directory in(ROOT/'analysis/phase25/runtime/natural-appearance-pointer/observer',ROOT/'analysis/phase25/runtime/natural-nonzero-reserve-submit/observer'):
   _captured_phase25_directory(reg,directory,rows,pins)
 return rows,pins


def _captured_phase25_directory(reg,directory,rows,pins):
  schema=json.loads((directory/'event-schema.json').read_text())
  assert schema['words']==40 and schema['bytes_per_record']==160
  raw=(directory/'bus-events.bin').read_bytes();snapshots=(directory/'snapshots.bin').read_bytes()
  for name in('event-schema.json','bus-events.bin','snapshots.bin','snapshot-index.jsonl'):
   rel=str((directory/name).relative_to(ROOT));pins[rel]=digest(ROOT/rel)
  for q in sorted(directory.glob('callee-*.json')):
   context=json.loads(q.read_text());target=context['entry'];assert target in(0xC5D2,0xD471,0xB431)
   banks=context['actual_PRG_banks'];registers=context['actual_registers'];offset=(context['event_sequence']-1)*160;event=struct.unpack_from('<40I',raw,offset)
   assert event[0]==context['event_sequence']and event[1]==context['frame']and event[4]==target and event[31]==context['snapshot_sequence']
   assert list(event[8:13])==[registers[k]for k in('a','x','y','p','sp')]
   assert list(event[13].to_bytes(4,'little'))==banks and banks[(target-0x8000)//0x2000]==context['physical_bank']
   full=snapshots[context['byte_offset']:context['byte_offset']+context['bytes']];assert len(full)==10240 and hashlib.sha256(full).hexdigest()==context['sha256']
   ram,sram=full[:2048],full[2048:];sp=registers['sp'];stack=ram[0x100+((sp+1)&255)]|ram[0x100+((sp+2)&255)]<<8
   assert stack==context['stack_top_word_raw']==event[30]&65535
   for key,buf in(('exported_RAM',ram),('exported_SRAM',sram)):
    file=directory/context[key];assert file.read_bytes()==buf;pins[str(file.relative_to(ROOT))]=digest(file)
   rel=str(q.relative_to(ROOT));pins[rel]=digest(q)
   candidates=sorted(cls for cls in reg.classes if target in reg.entry_values(cls))
   rows.append(dict(service_key=context_key(target,banks,rel),target=target,entry_banks=banks,caller_call_PC=None,actual_return_word_raw=stack,evidence_level='existing_validation_execution_record',execution_origin_subtype='passive_Native_callee_capture',evidence=evidence(rel),actual_parent_event_sequence=context['event_sequence'],actual_snapshot_sequence=context['snapshot_sequence'],current_route=reg.resolve(target,banks),local_entry_declarations=candidates,invocation_scope='Observed local or exported original entry; a local call may execute within a parent owner without passing the external resolver.',scope='New phase25 observer exact opcode boundary, registers/real stack/PRG mapping/full2K8K verified against raw parent event and sparse snapshot; original-control five-buffer comparison is in its separate Native manifest. No instantaneous device-state claim.'))


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--frontdoor',default='PointerLifecycleSceneCoordinator');args=parser.parse_args()
 baseline=read(BASELINE);assert baseline['status']=='passed'
 paths=sorted(p for p in baseline['source_and_validator_sha256']if p.startswith('source/recovered/')and p.endswith('.py'))
 for path in paths:assert digest(ROOT/path)==baseline['source_and_validator_sha256'][path],path
 additional=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py')if str(p.relative_to(ROOT))not in paths)
 paths+=additional
 reg=Registry(paths,args.frontdoor);assert args.frontdoor in reg.classes;receipts=receipt_inputs();services,events,scanned=observations(reg,receipts);calls,markers,catalog=syntax(reg);static=static_calls(reg);captured,captured_pins=captured_callers(reg)
 dimensions=read(REQUIREMENTS)['dimensions']
 dimension_rows=[]
 for dim in dimensions:
  identity=dim.get('id',dim.get('dimension_id'));item=dict(dim);item['index_evidence_scope']='Inherited phase24 acceptance requirement; no new gameplay execution.'
  item['next_acceptance_method']={'A01':'Read-only hash/byte rebuild and input identity check.','A02':'Require producer, consumer, distinguishing behavior or actual label; raw field names stay unknown.','A03':'Resolve complete mapper/entry/caller and logical/dummy addresses before narrowing.','A04':'Use exact service key and actual caller stack; run current owner to return/wait/prefix without CPU fallback.','A05':'Separate requested readable-source delivery from optional independently playable remake.','A06':'Replay explicit NMI/IRQ inputs and return ownership; never write an ack to advance.','A07':'Compare declared software IO separately from original-core RGB/PCM hardware synthesis.','A08':'Record natural/imported/controlled preparation and exact outcomes by route.','A09':'Verify frozen pins, explicit incremental dependencies, CRC/extracted bytes.','A10':'Report requirement-specific bounded evidence and remaining gaps; no unified completion percentage.'}.get(identity,'Use the inherited explicit acceptance method.')
  item['service_index_links']=['observed-service-index.json','receipt-observations.json','trusted-static-calls.json','source-syntax-boundaries.json']if identity in('A03','A04','A06','A07','A09','A10')else[]
  dimension_rows.append(item)
 pinned={**captured_pins,BASELINE:digest(ROOT/BASELINE),REQUIREMENTS:digest(ROOT/REQUIREMENTS),ATLAS:digest(ROOT/ATLAS),**{p:digest(ROOT/p)for p in receipts}}
 save('captured-caller-index.json',dict(schema='phase25-readonly-captured-caller-owner-index-v1',callers=captured,caller_context_count=len(captured),origin_subtype_counts=dict(Counter(r['execution_origin_subtype']for r in captured)),new_phase25_opcode_context_count=sum(r['evidence']['path'].startswith('analysis/phase25/')for r in captured),scope='Context rows are not new CPU/Source/Native cases;85 total index rows must not be confused with85 new Native sparse snapshots.',source_CPU_cases=0,Native_runs=0))
 closure=[]
 for service in services:
  counts=service['disposition_counts'];identity=service['index_key_kind']=='service_identity'
  state='not_a_unique_service_identity'if not identity else'owner_exists_closure_unproven'if service['owner_candidates']else'unknown_owner_or_bounded_model_gap'
  closure.append(dict(service_key=service['service_key'],closure_state=state,known_owner_candidates=service['owner_candidates'],confirmed_unimplemented=None,evidence_observation_indices=service['contexts'],disposition_counts=counts,acceptance_dimensions=['A03','A04','A06','A09','A10'],next_acceptance='Recover complete actual bank/entry/caller and explicit inputs; run the latest declared owner, compare real PC/SP and state/IO, and distinguish original wait from absent implementation. No artificial ack.'))
 save('closure-status-ledger.json',dict(schema='phase25-contextual-closure-status-ledger-v1',entries=closure,unknown_unique_services=None,scope='A completed observed caller is not a whole transitive service-closure proof; syntax-only candidates are in their separate inventory.'))
 save('observed-service-index.json',dict(schema='phase25-contextual-existing-receipt-service-index-v1',services=services,service_key_count=len(services),unknown_unique_services=None,source_CPU_cases=0,Native_runs=0))
 save('receipt-observations.json',dict(schema='phase25-readonly-existing-receipt-observations-v1',observations=events,observation_count=len(events),receipt_inputs=scanned,source_CPU_cases=0,Native_runs=0))
 save('trusted-static-calls.json',dict(schema='phase25-bounded-trusted-static-call-index-v1',input=ATLAS,services=static,unique_contextual_call_target_count=len(static),source_CPU_cases=0,Native_runs=0))
 save('source-syntax-boundaries.json',dict(schema='phase25-source-AST-only-boundaries-v1',source_files=paths,external_call_sites=calls,dependency_or_wait_markers=markers,entry_catalog=catalog,scope='Syntax only; no declaration is counted as a uniquely missing service.'))
 save('owner-route-catalog.json',dict(schema='phase25-bounded-current-owner-route-AST-v1',frontdoor=args.frontdoor,frontdoor_path=reg.classes[args.frontdoor][0],rules=[{k:v for k,v in row.items()if k!='test'}for row in reg.routes],unsupported_class_attributes=[{'class_name':key[0],'attribute':key[1]}for key,value in sorted(reg.cache.items())if value is MISSING],static_class_entry_catalog=catalog,scope='Finite AST model of explicit route guards and entry sets; does not instantiate or execute production Source.'))
 save('acceptance-map.json',dict(schema='phase25-service-index-ten-dimension-acceptance-v1',dimensions=dimension_rows,unknown_unique_services=None,whole_game_service_closure_proven=False))
 save('analysis-summary.json',dict(schema='phase25-readonly-service-gap-inventory-summary-v1',status='inventoried',unknown_unique_services=None,whole_game_service_closure_proven=False,source_CPU_cases=0,original_CPU_cases=0,Native_runs=0,
  baseline_path=BASELINE,baseline_sha256=digest(ROOT/BASELINE),source_file_count=len(paths),phase24_frozen_source_files=len(paths)-len(additional),additional_current_source_files=additional,frontdoor=args.frontdoor,captured_context_count=len(captured),new_phase25_opcode_context_count=sum(r['evidence']['path'].startswith('analysis/phase25/')for r in captured),receipt_file_count=len(receipts),observation_count=len(events),index_context_key_count=len(services),identified_service_key_count=sum(x['index_key_kind']=='service_identity'for x in services),
  observation_disposition_counts=dict(Counter(r['disposition']for r in events)),trusted_static_context_target_count=len(static),syntax_external_call_site_count=len(calls),syntax_dependency_or_wait_marker_count=len(markers),
  source_and_validator_sha256={'scripts/analyze_service_gaps_phase25.py':digest(__file__),**{p:digest(ROOT/p)for p in paths}},artifact_and_dependency_sha256=pinned,
  limitations=['Three evidence levels remain separate: existing production-receipt records, bounded trusted static calls, syntax-only declarations.','A current owner declaration does not establish transitive closure or this caller return; old unowned marks are not promoted to current missing services.','Service keys use fixed physical bank or captured paired mapping, never a bare banked address; unknown mapping stays contextual and unresolved.','Local static calls may be handled inside a source owner and are not necessarily external services.','No new Source/CPU/Native execution or historical producer output was performed.']))
 print(json.dumps(dict(source_files=len(paths),receipts=len(receipts),observations=len(events),dispositions=dict(Counter(r['disposition']for r in events)),unknown_unique_services=None)))

if __name__=='__main__':main()
