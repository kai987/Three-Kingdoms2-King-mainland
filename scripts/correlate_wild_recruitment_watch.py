#!/usr/bin/env python3
"""Bind the actual release/recruitment bus stream to every remaining site.

The pinned producer decodes its own unchanged ABI. This association does not
turn absence into an address exclusion or infer official city field names.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from capture_city_auxiliary_watchpoints import decode_event
OUT=ROOT/'analysis/phase22/access-runtime'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 base=ROOT/'analysis/phase22';path=base/'runtime/observer';native=read(base/'runtime/validation.json');assert native['status']=='passed'
 raw=(path/'bus-events.bin').read_bytes();events=[json.loads(s)for s in(path/'events.jsonl').read_text().splitlines()];assert len(raw)==72*len(events)
 static=read(base/'fields-static/all-indirect-accesses.json');old=read(base/'fields-static/phase21-remaining376-handling.json')
 by_pc=defaultdict(list);by_slot=defaultdict(list);dummy=[];page_dummy=[];dedicated=[];writes=[];boundaries=Counter();roles={};semantics=[]
 for i,e in enumerate(events):
  assert decode_event(raw[i*72:(i+1)*72],sequence=i+1)==e
  if e['opcode_PC']is not None:
   assert e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]==e['physical_bank']
   assert e['rom_offset']==16+e['physical_bank']*8192+(e['opcode_PC']&8191)
  if e['kind']=='opcode_boundary':boundaries[f"{e['physical_bank']}:{e['opcode_PC']:04X}"]+=1
  if e['target_type']!='city_auxiliary':continue
  assert e['city_index']in range(30)and e['city_offset']in(1,28,29,30,31)
  by_pc[e['physical_bank'],e['opcode_PC']].append(e);by_slot[e['city_index'],e['city_offset']].append(e)
  opcode=None if e['rom_offset']is None else rom[e['rom_offset']]
  effective=None;pointer=None
  if e['kind']=='read'and opcode in(0x91,0x99,0x9D):
   dummy.append(e);role='store_addressing_dummy_read'
  elif e['kind']=='read'and opcode==0xB1 and rom[e['rom_offset']+1]==0x22:
   pointer=e['pointer_0022_0023'];effective=(pointer+e['Y'])&65535
   if e['address']!=effective:
    assert(pointer&255)+e['Y']>=256 and e['address']==(effective-256)&65535
    page_dummy.append(e);role='load_indirect_Y_page_cross_dummy_read'
   else:dedicated.append(e);role='logical_effective_address_read'
  elif e['kind']in('read','word_read_low','word_read_high'):
   assert(e['physical_bank'],e['opcode_PC'],opcode)==(10,0xBD97,0xB1)
   dedicated.append(e);role='dedicated_city_plus1_load'
  else:
   assert e['kind']=='write_attempt'and e['WRAM_writable']and e['storage_byte_after_event']==e['value'];writes.append(e);role='committed_logical_write'
  roles[e['sequence']]=role
  semantics.append(dict(sequence=e['sequence'],frame=e['frame'],physical_bank=e['physical_bank'],cpu=e['opcode_PC'],address=e['address'],role=role,observed_pointer22=pointer,logical_effective_address=effective))
 rows=[]
 for s in static['accesses']:
  rawop=bytes.fromhex(s['raw_hex']);assert rom[s['rom_offset']:s['rom_offset']+len(rawop)]==rawop
  hits=by_pc.get((s['physical_bank'],s['cpu']),[]);contract=s['address_contract']or{}
  logical=[e for e in hits if'dummy'not in roles[e['sequence']]]
  rows.append(dict(physical_bank=s['physical_bank'],cpu=s['cpu'],rom_offset=s['rom_offset'],raw_hex=s['raw_hex'],classification=s['classification'],proof_basis=s['proof_basis'],newly_proved_disjoint=s['newly_proved_disjoint'],contract_representation='guarded_pointer_index_cases'if'address_cases'in contract else'flat_address_contract'if contract else'unknown',observed_city_bus_events=len(hits),observed_logical_effective_address_events=len(logical),observed_bus_roles=dict(Counter(roles[e['sequence']]for e in hits)),observed_kinds=dict(Counter(e['kind']for e in hits)),observed_offsets=sorted({e['city_offset']for e in hits}),sequences=[e['sequence']for e in hits],negative_observation_excludes_access=False))
 assert len(rows)==1526
 keys={(s['physical_bank'],s['cpu'])for s in old['accesses']};previous=[s for s in rows if(s['physical_bank'],s['cpu'])in keys];assert len(previous)==376
 trusted={(s['physical_bank'],s['cpu'])for s in rows};outside=[dict(physical_bank=k[0],cpu=k[1],sequences=[e['sequence']for e in es])for k,es in by_pc.items()if k not in trusted]
 conflicts=[s for s in rows if s['classification']=='proved_disjoint_auxiliary_address_domain'and s['observed_logical_effective_address_events']]
 assert not conflicts,('Observed target under conditional static exclusion; investigate the caller/interrupt premises',conflicts)
 # A successful scan is evidenced by actual observer opcodes and original
 # SRAM changes independently of any source comparison or supplied RNG.
 success=[e for e in events if e['kind']=='opcode_boundary'and(e['physical_bank'],e['opcode_PC'])==(11,0xC794)]
 assert success and boundaries['11:C732']>0 and boundaries['11:C735']>0
 schema=read(path/'event-schema.json');assert 'phase22' in schema['original_reference_case']
 OUT.mkdir(parents=True,exist_ok=True);write('all1526-association.json',rows);write('previous376-association.json',previous)
 write('actual-success-exits.json',success);write('actual-city-bus-semantics.json',semantics)
 slots=[dict(city_index=c,city_offset=o,counts=dict(Counter(e['kind']for e in es)),sequences=[e['sequence']for e in es])for(c,o),es in sorted(by_slot.items())];write('observed-field-slots.json',slots)
 value=dict(schema='phase22-native-wild-recruitment-static-correlation-v1',status='passed',raw_records=len(events),raw_bytes=len(raw),city_bus_events=sum(map(len,by_pc.values())),store_dummy_reads=len(dummy),load_indirect_Y_page_cross_dummy_reads=len(page_dummy),dedicated_or_logical_reads=len(dedicated),committed_writes=len(writes),all_static_accesses=1526,previous_candidates=376,newly_proved_disjoint=sum(s['newly_proved_disjoint']for s in previous),remaining_candidates=sum(s['classification']!='proved_disjoint_auxiliary_address_domain'for s in previous),actual_opcode_boundaries=dict(boundaries),actual_C794_success_exits=len(success),success_exits=success,positive_static_positions=[s for s in rows if s['observed_city_bus_events']],disjoint_logical_sites_with_actual_dummy_bus_hits=[s for s in rows if s['classification']=='proved_disjoint_auxiliary_address_domain'and s['observed_city_bus_events']],observed_sites_outside_static_indirect_inventory=outside,official_city_names={'+1':None,'+28':None,'+29':None,'+30':None,'+31':None},source_CPU_cases=0,limits=['This is a separately rebuilt observer core, with original-core full-flow controls elsewhere.','Absence on one declared route never becomes a static exclusion or unused-field proof.','Static contracts describe logical effective addresses. Store dummy reads and LDA indirect-Y page-cross dummy reads have separately computed bus addresses.','C73F pointer63FC+Y5 gives actual effective6401, while the original IndY_R reads6301 on its page-cross cycle; that bus read does not consume city24+1 as game data.','Destination ID30 (ざいや) is a postbattle UI selector; it is not the meaning of city-record offset+30.','C794 events are before the actual RTS; the original two PLA have executed. Exact returned PC/SP comes from the separately recorded CPU continuation and native later snapshots.'])
 write('evidence.json',value)
 deps=[Path(__file__),ROOT/'scripts/capture_city_auxiliary_watchpoints.py',ROOT/'scripts/capture_native_wild_recruitment.py',ROOT/'analysis/phase21/runtime/core-provenance/upstream/source/core/NstCpu.cpp',base/'runtime/validation.json',base/'runtime/evidence.json',path/'events.jsonl',path/'bus-events.bin',path/'event-schema.json',base/'fields-static/all-indirect-accesses.json',base/'fields-static/phase21-remaining376-handling.json']
 pins={str(p.relative_to(ROOT)):sha(p)for p in deps}
 for name in('all1526-association.json','previous376-association.json','actual-success-exits.json','actual-city-bus-semantics.json','observed-field-slots.json','evidence.json'):pins[str((OUT/name).relative_to(ROOT))]=sha(OUT/name)
 write('verification.json',dict(status='passed',failed_count=0,checks=dict(raw_decode_exact=len(events),original_indirect_opcode_checks=1526,all_previous_candidates=376,negative_observations_promoted_to_exclusion=0,source_CPU_cases=0),dependency_pins=pins));print(json.dumps({k:v for k,v in value.items()if isinstance(v,(int,str))}))
if __name__=='__main__':main()
