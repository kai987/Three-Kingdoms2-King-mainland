#!/usr/bin/env python3
"""Offline phase17 expansion of trusted code vectors and city field contracts.

The frozen phase16 atlas is an input, not an absence theorem. AllPRG raw calls
are inventoried, but bytes become code only through trusted control entrances.
Portable prior evidence is used directly; no excluded exploration tree is a
required dependency. Production modules do not import this analysis script.
"""
from pathlib import Path
from collections import Counter,deque
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES,instruction
import analyze_field_semantics as prior
from source.recovered.city_field_contracts import ROM_SHA256
OUT=ROOT/'analysis/phase17/fields';BASE=ROOT/'analysis/phase16/fields'
SOURCE=ROOT/'source/recovered/city_field_contracts.py'
PAIRS=(8,10,12,14,23,25,27,29)
AUX={1,28,29,30,31}
RANGES=[(31,0xF237,0xF26D,'explicit_mapper_pair_and_data_window_services'),
 (31,0xEE07,0xEE55,'far_call_real_inline_word_and_pair_restore'),
 (31,0xF2AF,0xF308,'fixed_city_and_officer_pointer_helpers'),
 (31,0xF368,0xF3BD,'ruler_and_original_record_pointer_boundaries'),
 (11,0xD105,0xD12D,'city_pointer_caps_and_owner'),(11,0xD283,0xD2D3,'two_officer_pointer_read_helpers'),
 (11,0xD69D,0xD6D0,'gold_grain_caps'),(10,0xBD95,0xBDA3,'overlapping_byte1_goldlow_gate'),
 (10,0xA442,0xA450,'unbounded_AI_insert_prefix'),(10,0xA208,0xA239,'war_transfer_goal_and_capacity_guard'),
 (10,0xB144,0xB177,'peace_transfer_goal_and_capacity_guard'),(11,0xD080,0xD0AA,'bounded_ruler_city_counts'),
 (11,0xD03A,0xD05D,'mean_occupancy_inputs'),(10,0xA303,0xA3C6,'AI_transfer_callers_and_after_each_transfer_count'),
 (27,0xA70C,0xA742,'normal_player_transfer_capacity_guard'),(27,0xAD41,0xADF2,'normal_same_owner_transfer'),
 (26,0xC1DB,0xC25D,'bounded_nomination_parent_and_ten_slot_callee')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(name,data):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def off(bank,pc):return 16+bank*8192+(pc&8191)
def raw_range(rom,bank,start,end,label=None):
 o=off(bank,start);return dict(physical_bank=bank,cpu=start,end_cpu_exclusive=end,rom_offset=o,raw_hex=rom[o:o+end-start].hex(' ').upper(),label=label)
def row(rom,bank,pc,origin):
 o=off(bank,pc);op,mode=OPS[rom[o]];size=SIZES[mode]
 return dict(physical_bank=bank,cpu=pc,rom_offset=o,size=size,op=op,mode=mode,operand=int.from_bytes(rom[o+1:o+size],'little'),raw_hex=rom[o:o+size].hex(' ').upper(),sources=[origin])
def context_selector(known,k):
 """Only a unique straight-line predecessor chain can prove the Y selector."""
 b,pc=k;history=[];at=pc
 for _ in range(12):
  found=[r for (bb,p),r in known.items()if bb==b and p+r['size']==at]
  if len(found)!=1:break
  r=found[0];history.append(r);at=r['cpu']
  if r['op']=='LDY':
   return (r['operand']if r['mode']=='im'else None),list(reversed(history))
  if r['op']in('TAY','INY','DEY','JSR','JMP','RTS','RTI')or r['mode']=='rel':break
 return None,list(reversed(history))
def expanded_graph(rom,baseline):
 known={(r['physical_bank'],r['cpu']):dict(r)for r in baseline['instructions']};vectors=[]
 for k,r in known.items():assert bytes.fromhex(r['raw_hex'])==rom[r['rom_offset']:r['rom_offset']+r['size']]
 for bank in PAIRS:
  pc=0xA000
  while rom[off(bank,pc)]==0x4C:
   r=row(rom,bank,pc,'legitimate_contiguous_export_vector');known[bank,pc]=r
   vectors.append(dict(**r,target_cpu=r['operand'],pair=[bank,bank+1]));pc+=3
 queue=deque(known);seen=set();edges={};barriers=[]
 def mapped(k,target):
  if target>=0xE000:return 31,target
  if not 0xA000<=target<0xE000:return None
  if k[0]==31:return None
  pair=k[0]-int(k[1]>=0xC000)
  return pair+int(target>=0xC000),target
 while queue:
  k=queue.popleft()
  if k in seen:continue
  seen.add(k);r=known[k];pc=r['cpu'];v=r['operand'];n=pc+r['size'];targets=[]
  if r['mode']=='rel':targets=[mapped(k,n),mapped(k,(pc+2+(v if v<128 else v-256))&65535)]
  elif r['op']=='JMP':
   if r['mode']=='ab':targets=[mapped(k,v)]
   else:barriers.append(dict(physical_bank=k[0],cpu=pc,kind='computed_JMP',raw_hex=r['raw_hex'],rom_offset=r['rom_offset']))
  elif r['op']=='JSR':
   if v in(0xEADE,0xB517):
    barriers.append(dict(physical_bank=k[0],cpu=pc,kind='inline_dispatch_requires_bounded_table_contract',raw_hex=r['raw_hex'],rom_offset=r['rom_offset']))
   elif v==0xEE07:
    targets=[mapped(k,n+2)];selector,context=context_selector(known,k)
    callee=int.from_bytes(rom[off(k[0],n):off(k[0],n)+2],'little')
    if selector is not None and(selector&31)in PAIRS and 0xA000<=callee<0xE000:
     pair=selector&31;targets.append((pair+int(callee>=0xC000),callee))
    else:barriers.append(dict(physical_bank=k[0],cpu=pc,kind='unresolved_far_selector_or_target',selector=selector,inline_target=callee,rom_offset=r['rom_offset'],raw_hex=rom[off(k[0],pc):off(k[0],pc)+5].hex(' ').upper()))
   else:
    targets=[mapped(k,n),mapped(k,v)]
    if k[0]==31 and 0xA000<=v<0xE000:
     barriers.append(dict(physical_bank=k[0],cpu=pc,kind='fixed_call_depends_on_actual_mapper_context',target_cpu=v,raw_hex=r['raw_hex'],rom_offset=r['rom_offset']))
  elif r['op']not in('RTS','RTI','BRK','?'):targets=[mapped(k,n)]
  targets=[t for t in targets if t is not None]
  for t in targets:
   if t not in known:
    rr=row(rom,*t,'new_trusted_vector_direct_CFG')
    if rr['op']in('?','BRK'):
     barriers.append(dict(physical_bank=k[0],cpu=pc,kind='unrecognized_or_BRK_on_direct_path',target=list(t),raw_hex=r['raw_hex'],rom_offset=r['rom_offset']));continue
    known[t]=rr
   queue.append(t)
  edges[k]=[t for t in targets if t in known]
 return known,edges,vectors,barriers

def analyze(rom):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 baseline=read(BASE/'all-bank-instruction-atlas.json');old=read(BASE/'city-tail-candidate-review.json')
 known,edges,vectors,barriers=expanded_graph(rom,baseline)
 # Increasing the byte-set join bound does not assume that a loop terminates.
 # A full0..255 Y domain remains a potentialauxiliary alias rather than None.
 original_zp,original_empty,original_union=prior.ZP,prior.EMPTY,prior.union
 prior.ZP=tuple(range(0x100));prior.EMPTY=(None,None,None,tuple(None for _ in prior.ZP))
 def byte_join(a,b):
  if a is None or b is None:return None
  value=a|b;return value if len(value)<=256 else None
 prior.union=byte_join
 try:refined,absolute,summaries,effects=prior.dataflow(known,edges,refined=True,rom=rom)
 finally:prior.ZP,prior.EMPTY,prior.union=original_zp,original_empty,original_union
 access={(r['physical_bank'],r['cpu']):r for r in refined}
 # Proof fragments deliberately retain their own control/input preconditions.
 # No extra officialresource or unused/reservedlabel is inferred from zeros.
 proof_specs=[
  ('two_side_roster_writeback',[(10,0xAA91),(10,0xAB21)],list(range(17,27)),[(10,0xAA80,0xAA99),(10,0xAB10,0xAB29)],'X starts0 and advances to10; Y starts17 and advances only when an occupiedslot is written'),
  ('bounded_source_roster_evacuate',[(10,0xB3FD),(10,0xB406)],list(range(17,27)),[(10,0xB3F1,0xB421)],'source cursor24 starts17 and is tested against27 aftereachiteration; destination cursor25 is independent and remains separately unresolved'),
  ('bounded_player_nomination',[(26,0xC231)],list(range(17,27)),[(26,0xC1E5,0xC1F7),(26,0xC21D,0xC25D)],'the only trustedlocalcaller C1F4 followsF2AF; copiedcitypointer02/03 survives F2D7 which writes00/01, and cursor4 is bounded17..26'),
  ('bounded_ruler_loyalty_sum',[(26,0xC480)],list(range(17,27)),[(26,0xC47C,0xC4AB)],'Y17 is preserved on the realPHA/PLA frame aroundofficerlookup; CPY27 bounds the ten citybytes'),
  ('capacity_guarded_join',[(25,0xAF42)],list(range(17,27)),[(25,0xAF1F,0xAF44)],'countX scans10slots; CPX10/BEQ rejectsfullroster, so17+X is atmost26'),
  ('bounded_city_menu_roster_copy',[(29,0xBA6C)],list(range(17,27)),[(29,0xBA62,0xBA7E)],'X0..9 and Y17..26; CPX10 boundscopy regardlessFF')]
 proofs=[];manual={}
 for label,sites,ys,ranges,reason in proof_specs:
  p=dict(id=label,sites=[{'physical_bank':b,'cpu':pc,'rom_offset':off(b,pc),'raw_hex':known[b,pc]['raw_hex']}for b,pc in sites],
    Y_values=ys,reason=reason,ranges=[raw_range(rom,b,s,e,label)for b,s,e in ranges],
    excludes_offsets=sorted(AUX),domain='Original localentry and explicittrustedcallers, not arbitraryexecution startingmid-instruction')
  proofs.append(p)
  for site in sites:manual[site]=p
 # Intrinsic officerpointer helpers can neveraddresscitySRAM for any byteID/Y.
 officer_proof=dict(id='intrinsic_officer_pointer_address_range',sites=[{'physical_bank':11,'cpu':pc,'rom_offset':off(11,pc),'raw_hex':known[11,pc]['raw_hex']}for pc in(0xD2A8,0xD2D0)],
  domain='All rawID0..255 andY0..255',formula='63C0+12*ID+Y',minimum_address=0x63C0,maximum_address=0x63C0+12*255+255,
  city_intersections=0,ranges=[raw_range(rom,11,0xD283,0xD2D3,'exact_officer_pointer_reads')])
 proofs.append(officer_proof)
 for pc in(0xD2A8,0xD2D0):manual[11,pc]=officer_proof
 # F368's raw sixteen-entry table includes codebytes. Do not assume7rulers:
 # enumerateevery16pointer and the exact finiteY domain at each provedcopy.
 ruler_pointers=[int.from_bytes(rom[off(31,0xF379)+2*i:off(31,0xF379)+2*i+2],'little')for i in range(16)]
 ruler_exclusions={}
 for r in refined:
  origins=r['pointer_producer_calls'];ys=r['Y_values']
  if not origins or ys is None or not all(p['callee']==0xF368 and p['pointer_role']in('ruler','ruler_table_or_adjacent_bytes')for p in origins):continue
  values=r['resolved_pointer_byte_values']
  if values is None:continue
  facts=[[ast.literal_eval(v)for v in part]for part in values]
  if not all(part and all(isinstance(v,tuple)and len(v)==5 and v[0]=='pointer'and v[1]in('ruler','ruler_table_or_adjacent_bytes')and v[2]==i for v in part)for i,part in enumerate(facts)):continue
  # The coarse lattice canjoinpointerbytes fromdifferentcallcontexts. Keep
  # everylow/highcross-product aswellas everyY; correlationis not assumed.
  lows={address&255 for address in ruler_pointers};highs={address>>8 for address in ruler_pointers}
  possible=sorted({((lo|(hi<<8))+y)&65535 for lo in lows for hi in highs for y in ys})
  if any(0x6000<=address<0x63C0 for address in possible):continue
  ruler_exclusions[r['physical_bank'],r['cpu']]=dict(id='raw_F368_table_plus_verified_Y_disjoint_city',
   raw_pointer_table=ruler_pointers,Y_values=ys,possible_effective_addresses=possible,
   low_high_byte_join_correlations_not_assumed=True,
   exact_pointer_producer_calls=origins,city_intersections=0,
   ranges=[raw_range(rom,31,0xF368,0xF399,'F368raw16pointertable_and_adjoining_bytes')],
   limitation='No legalrulerindex orpointerbytecorrelation assumption. Rawindex8 pairedpointer5F20 can aliascity whenY>=224; wider/coarsejoined address domains remain candidates')
  manual[r['physical_bank'],r['cpu']]=ruler_exclusions[r['physical_bank'],r['cpu']]
 tactic_pointers=[int.from_bytes(rom[off(9,0xD509)+2*i:off(9,0xD509)+2*i+2],'little')for i in range(8)]
 assert all(address>=0x8000 and address+255<=65535 for address in tactic_pointers)
 tactic_proof=dict(id='bounded_eight_tactic_ROM_lists',sites=[dict(physical_bank=9,cpu=0xD4F7,rom_offset=off(9,0xD4F7),raw_hex=known[9,0xD4F7]['raw_hex'])],
  pointer_table=tactic_pointers,Y_values=list(range(256)),city_intersections=0,
  selector_domain='Allrawlevel0..15 andknowledge0..255 mapto0..7 throughoriginalCMP/branch ladder',
  ranges=[raw_range(rom,9,0xD4A2,0xD509,'tactic_selector_branches_and_list_reader'),raw_range(rom,9,0xD509,0xD519,'eight_tactic_ROM_pointers')])
 proofs.append(tactic_proof);manual[9,0xD4F7]=tactic_proof
 oldrows=old['remaining_known_city_pointer_unknown_Y']+old['remaining_pointer_or_shifted_index_unresolved']
 excluded=[];remaining=[]
 for original in oldrows:
  k=original['physical_bank'],original['cpu'];r=access[k]
  other=r['pointer_kind']in('officer','initial_officer','ruler','ROM_window','ROM_names','non_city_RAM_or_IO')
  city_other=r['pointer_kind']=='city'and r['Y_values']is not None and not(AUX&set(r['Y_values']))
  if k in manual or other or city_other:
   excluded.append(dict(original_site={'physical_bank':k[0],'cpu':k[1]},classification='placeholder'))
  else:remaining.append(dict(**r,classification='remaining_possible_auxiliary_alias'))
 # Fill explicitproof labels separately so proofs are auditable, not magic tags.
 for e in excluded:
  k=e['original_site']['physical_bank'],e['original_site']['cpu'];r=access[k]
  e['classification']='proved_local_contract_other_offsets'if k in manual else'expanded_taint_proved_other_pointer_or_offsets'
  e['proof_id']=manual[k]['id']if k in manual else None;e['refined_access']=r
  if k in ruler_exclusions:e['exact_address_proof']=ruler_exclusions[k]
 # Standalone FF scans are genericroster algorithms, never dedicatedfieldnames.
 unbounded_sites=[]
 for r in remaining:
  k=(r['physical_bank'],r['cpu']);history=[known[k[0],pc]for pc in sorted(p for b,p in known if b==k[0]and k[1]-16<=p<k[1])]
  if r['pointer_kind']=='city'and any(q['op']=='LDY'and q['mode']=='im'and q['operand']in(16,17)for q in history):
   r['classification']='generic_roster_scan_with_unproved_sentinel_or_match_bound';unbounded_sites.append(r)
 prior_indirect={(r['physical_bank'],r['cpu'])for r in read(BASE/'pointer-taint-refinement.json')['accesses']}
 new_accesses=[];new_possible=[]
 for r in refined:
  k=r['physical_bank'],r['cpu']
  if k in prior_indirect:continue
  safe=r['pointer_kind']in('officer','initial_officer','ruler','ROM_window','ROM_names','non_city_RAM_or_IO')or k in manual
  if r['pointer_kind']=='city'and r['Y_values']is not None and not(AUX&set(r['Y_values'])):safe=True
  item=dict(**r,classification='proved_disjoint_or_other_record_access'if safe else 'still_possible_auxiliary_alias')
  if k in manual:item['exact_contract_or_address_proof']=manual[k]
  new_accesses.append(item)
  if not safe:new_possible.append(item)
 save('alias-refinement.json',dict(schema='phase17-city-alias-contract-refinement-v1',ROM_sha256=ROM_SHA256,
  prior_candidate_count=len(oldrows),excluded_prior_candidate_count=len(excluded),remaining_prior_candidate_count=len(remaining),
  excluded_candidates=excluded,remaining_candidates=remaining,proofs=proofs,
  new_indirect_access_count=len(new_accesses),new_indirect_accesses=new_accesses,new_possible_auxiliary_alias_count=len(new_possible),
  expanded_total_possible_alias_count=len(remaining)+len(new_possible),new_possible_auxiliary_aliases=new_possible,
  semantic_names=dict(city_byte1=None,city_bytes28_31=None),
  limitation='Resolvedcontracts excludeonly statedordinarycaller/indexdomains. Remainingaliases and computed-entrybarriers prevent a whole-ROM no-consumer or unused/padding theorem.'))
 save('pointer-accesses.json',dict(schema='phase17-expanded-record-pointer-accesses-v1',ROM_sha256=ROM_SHA256,accesses=refined,absolute_accesses=absolute,
  known_instruction_positions=len(known),indirect_access_count=len(refined),byte_set_join_limit=256,
  abstract_domain='Conservative forwardCFG with fixedrecordhelpers and maywritecallees; unknowncomputedcalls clobberfacts',
  limitation='Domains are sound coarse unions, not observedNativePCtrace; no totalprogramreachability theorem'))
 mapping_calls=[]
 for k,r in known.items():
  if r['op']=='JSR'and r['operand']in(0xEE07,0xF237,0xF24B):
   selector,context=context_selector(known,k)
   call=dict(physical_bank=k[0],cpu=k[1],rom_offset=r['rom_offset'],raw_hex=r['raw_hex'],callee=r['operand'],selector=selector,
    selector_context=[{key:q[key]for key in('physical_bank','cpu','rom_offset','raw_hex')}for q in context])
   if r['operand']==0xEE07:
    o=off(k[0],k[1]+3);call['inline_target']=int.from_bytes(rom[o:o+2],'little');call['inline_pointer']={'physical_bank':k[0],'cpu':k[1]+3,'rom_offset':o,'raw_hex':rom[o:o+2].hex(' ').upper()}
   mapping_calls.append(call)
 rawpatterns=[]
 for bank in range(32):
  data=rom[16+8192*bank:16+8192*(bank+1)]
  for i in range(8188):
   if data[i:i+3]==bytes([0x20,0x07,0xEE]):
    pc=(0x8000 if bank not in PAIRS and bank not in tuple(b+1 for b in PAIRS)and bank!=31 else 0xE000 if bank==31 else 0xA000 if bank in PAIRS else 0xC000)+i
    rawpatterns.append(dict(physical_bank=bank,bank_offset=i,rom_offset=16+8192*bank+i,
      trusted_instruction_position=(bank,pc)in known,raw_hex=data[i:i+5].hex(' ').upper(),
      classification='trusted_far_call'if(bank,pc)in known else'raw_syntactic_pattern_not_promoted_to_code'))
 inactive=tuple(range(8))+tuple(range(16,23))
 bankcounts=Counter(b for b,pc in known)
 save('dispatch-bank-inventory.json',dict(schema='phase17-trusted-control-bank-expansion-v1',ROM_sha256=ROM_SHA256,
  raw_PRG_bank_count=32,raw_PRG_byte_count=262144,prior_known_positions=baseline['instruction_positions'],new_known_positions=len(known),new_positions_added=len(known)-baseline['instruction_positions'],
  contiguous_export_vectors=vectors,mapping_calls=mapping_calls,raw_allbank_far_call_patterns=rawpatterns,
  code_bank_position_counts=dict(bankcounts),nonseeded_banks=list(inactive),trusted_control_entries_found_in_nonseeded_banks=sum(bankcounts[b]for b in inactive),
  known_direct_control_targets_below_A000=[r for r in known.values()if r['op']in('JSR','JMP')and r['mode']=='ab'and r['operand']<0xA000],
  immutable_read_only_data_evidence='Physical0..7/16..22 stillhave no trustedcodeentry throughthisresolvedexport/far/directCFG domain. Their bytes are included in allPRGpattern inventory, not declared absent executablecode for arbitraryexternalmapper/jumps.',
  computed_or_mapper_context_barriers=barriers,all32bank_first64bytes=[raw_range(rom,b,0x8000,0x8040,'physical_bank_first64_byte_sample_no_code_type_claim')for b in range(32)]))
 save('instruction-atlas.json',dict(schema='phase17-trusted-vector-expanded-instruction-atlas-v1',ROM_sha256=ROM_SHA256,instructions=list(known.values()),
  source_baseline_path='analysis/phase16/fields/all-bank-instruction-atlas.json',source_baseline_sha256=sha(BASE/'all-bank-instruction-atlas.json'),edges=[{'physical_bank':b,'cpu':pc,'targets':[list(t)for t in targets]}for(b,pc),targets in edges.items()]))
 ranges=[raw_range(rom,b,s,e,label)for b,s,e,label in RANGES]
 tables=[raw_range(rom,10,0xA3C6,0xA3D6,'two7entry_source_count_thresholds'),raw_range(rom,27,0xA46E,0xA471,'three_resource_offset_choices'),raw_range(rom,31,0xF379,0xF399,'seven_ruler_pointers_and_adjoining_machine_bytes')]
 save('static-catalog.json',dict(schema='phase17-city-field-contracts-static-v1',ROM_sha256=ROM_SHA256,ranges=ranges,tables=tables,
  callable_complete_entries={'fixed':[0xF2AF,0xF2D7,0xF368],'physical10_11':[0xD105,0xD69D,0xD283,0xD2AB],'physical25_26':[0xC21D]},
  explicit_prefix_entries={'physical10_11':[0xBD95,0xA442,0xB144],'physical27_28':[0xA71B]},
  no_official_byte1_or_tail_names=True))
 asm=[]
 for b,s,e,label in RANGES:
  asm.append(f'; physicalbank{b} {label}; original file+16')
  pc=s
  while pc<e:
   o=off(b,pc);n,text=instruction(rom,o,pc);asm.append(f'{b:02}:{pc:04X} file={o:06X} {rom[o:o+n].hex(" ").upper():<8} {text}');pc+=n
 (OUT/'raw.asm').write_text('\n'.join(asm)+'\n')
 schema=dict(schema='phase17-city-field-contract-overlay-v1',ROM_sha256=ROM_SHA256,
  city_byte1=dict(official_name=None,confirmed_dedicated_consumer='10BD97 within BD95..BDA1',mechanical_formula='LE16(city+1,city+2)>=300',
   city_byte2_also_gold_low=True,not_goldword='Gold isLE16(+2,+3), so originaloverlapgate can passgold255 and failgold256 whenbyte1=0',
   no_proven_dedicated_producer=True,ordinary_initial_template_byte1=0),
  city_bytes28_31=dict(official_name=None,raw_offsets=[28,29,30,31],generic_copy_clear_preserved=True,
   dedicated_consumer_or_producer_not_established=True,padding_or_unassigned_not_proved=True,
   raw_roster_scan_can_alias=True,normal_capacity_protection='Normalplayertransfer checksfull10 and clampsselectionbudget; twoAIcallers verifydestinationcountbelowgoal<=10 undervalidoccupancydomain',
   bounded_nomination='26C21D readsatmost17..26, includinglegalfull10 withoutFF',remaining_possible_aliases=len(remaining)),
  negative_scope='Whole32banks scanned for raw patterns; trustedCFG/vectors and fieldcontracts areboundedproof. No whole-ROM unused/officialpadding claim.')
 save('schema.json',schema)
 inputs=[BASE/'all-bank-instruction-atlas.json',BASE/'city-tail-candidate-review.json',BASE/'provenance/manifest.json']
 manifest=read(BASE/'provenance/manifest.json')
 inputs.extend(ROOT/item['portable_path']for item in manifest['copies'])
 sourcepins={str(p.relative_to(ROOT)):sha(p)for p in[SOURCE,Path(__file__),ROOT/'scripts/verify_city_field_contracts.py',ROOT/'scripts/analyze_field_semantics.py',ROOT/'scripts/inspect_game_data.py']}
 artifactpins={str(p.relative_to(ROOT)):sha(p)for p in inputs}
 for pair in PAIRS:
  for name in('image.bin','mapping.json'):
   p=ROOT/f'analysis/rea/pairs/pair-{pair:02d}/{name}';artifactpins[str(p.relative_to(ROOT))]=sha(p)
 for p in [OUT/'validation.json',OUT/'executed-instructions.json',OUT/'legal-full-roster-origin.json']:
  if p.exists():artifactpins[str(p.relative_to(ROOT))]=sha(p)
 assert not any(any(part.startswith('exploratory')for part in Path(p).parts)for p in artifactpins)
 save('evidence.json',dict(schema='phase17-city-field-contracts-evidence-v1',status='analyzed',ROM_sha256=ROM_SHA256,source_path=str(SOURCE.relative_to(ROOT)),source_sha256=sha(SOURCE),
  analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),source_and_validator_sha256=sourcepins,artifact_and_dependency_sha256=artifactpins,ranges=ranges,tables=tables,
  source_original_CPU_callbacks=0,source_control_IR_callbacks=0,wholebank_inventory_path='analysis/phase17/fields/dispatch-bank-inventory.json',alias_refinement_path='analysis/phase17/fields/alias-refinement.json',
  original647_remaining_after_local_contracts=len(remaining),excluded_prior_candidates=len(excluded),prior647_is_not_confirmed_consumers=True,
  complete_helpers=['31F2AF','31F2D7','31F368','11D105','11D69D','11D283','11D2AB','26C21D'],prefixes=['10BD95','10A442','10B144','27A71B'],
  official_semantics_unresolved=['city+1','city+28..31'],no_unused_padding_assertion=True))
 print(json.dumps(dict(instructions=len(known),new_positions=len(known)-baseline['instruction_positions'],export_vectors=len(vectors),mapping_calls=len(mapping_calls),raw_far_patterns=len(rawpatterns),indirect_accesses=len(refined),old647_excluded=len(excluded),old647_remaining=len(remaining),barriers=len(barriers))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();analyze(a.rom.read_bytes())
