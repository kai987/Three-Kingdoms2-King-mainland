#!/usr/bin/env python3
"""Associate passive bus evidence with every static candidate; never infer names."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from capture_city_auxiliary_watchpoints import decode_event
OUT=ROOT/'analysis/phase21/access-runtime'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 rom=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(rom).hexdigest()=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 base=ROOT/'analysis/phase21';native=read(base/'runtime/validation.json');assert native['status']=='passed'
 path=base/'runtime/observer-accept';raw=(path/'bus-events.bin').read_bytes();events=[json.loads(x)for x in(path/'events.jsonl').read_text().splitlines()]
 assert len(raw)==72*len(events)==236088
 by_pc=defaultdict(list);by_slot=defaultdict(list);dummy=[];semantic=[];writes=[]
 for i,e in enumerate(events):
  assert decode_event(raw[i*72:(i+1)*72],sequence=i+1)==e
  assert e['actual_PRG_banks'][(e['opcode_PC']-0x8000)//8192]==e['physical_bank']
  assert e['rom_offset']==16+8192*e['physical_bank']+(e['opcode_PC']&8191)
  if e['target_type']!='city_auxiliary':continue
  assert e['city_index'] in range(30)and e['city_offset']in(1,28,29,30,31)
  by_pc[(e['physical_bank'],e['opcode_PC'])].append(e);by_slot[(e['city_index'],e['city_offset'])].append(e)
  opcode=rom[e['rom_offset']]
  if e['kind']=='read'and opcode==0x91:
   nxt=events[i+1];assert nxt['kind']=='write_attempt'and all(nxt[k]==e[k]for k in('frame','opcode_PC','physical_bank','address','cycle'))
   dummy.append(e)
  elif e['kind']=='read':
   assert(e['physical_bank'],e['opcode_PC'],opcode)==(10,0xBD97,0xB1);semantic.append(e)
  else:
   assert e['kind']=='write_attempt'and opcode==0x91 and e['WRAM_writable']and e['storage_byte_after_event']==e['value'];writes.append(e)
 assert(len(dummy),len(semantic),len(writes),len(by_slot))==(300,12,300,150)
 static=read(base/'fields-static/all-indirect-accesses.json');remaining20=read(base/'fields-static/phase20-remaining380-handling.json')
 rows=[]
 for s in static['accesses']:
  b=bytes.fromhex(s['raw_hex']);assert rom[s['rom_offset']:s['rom_offset']+len(b)]==b
  hits=by_pc.get((s['physical_bank'],s['cpu']),[])
  if hits:assert s['classification']!='proved_disjoint_auxiliary_address_domain',s
  rows.append(dict(physical_bank=s['physical_bank'],cpu=s['cpu'],rom_offset=s['rom_offset'],raw_hex=s['raw_hex'],classification=s['classification'],newly_proved_disjoint=s['newly_proved_disjoint'],observed_city_bus_events=len(hits),observed_kinds=dict(Counter(e['kind']for e in hits)),observed_offsets=sorted({e['city_offset']for e in hits}),sequences=[e['sequence']for e in hits],negative_observation_excludes_access=False))
 assert len(rows)==1526 and sum(r['observed_city_bus_events']for r in rows)==612
 keys={(s['physical_bank'],s['cpu'])for s in remaining20['accesses']};old=[r for r in rows if(r['physical_bank'],r['cpu'])in keys];assert len(old)==380
 positive=[r for r in rows if r['observed_city_bus_events']];assert len(positive)==3
 OUT.mkdir(parents=True,exist_ok=True)
 write('all1526-association.json',rows);write('previous380-association.json',old)
 slots=[dict(city_index=c,city_offset=o,counts=dict(Counter(e['kind']for e in es)),semantic_read_sequences=[e['sequence']for e in es if e in semantic],dummy_read_sequences=[e['sequence']for e in es if e in dummy],write_sequences=[e['sequence']for e in es if e['kind']=='write_attempt'])for(c,o),es in sorted(by_slot.items())]
 write('all150-field-slots.json',slots)
 evidence=dict(schema='phase21-runtime-static-city-correlation-v1',status='passed',raw_records=len(events),raw_bytes=len(raw),city_bus_events=612,STA_indirect_Y_dummy_reads=300,dedicated_load_reads=12,committed_bulk_writes=300,field_slots=150,all_static_accesses=1526,previous_candidates=380,newly_proved_disjoint=4,remaining_candidates=376,positive_static_positions=positive,official_names={'+1':None,'+28':None,'+29':None,'+30':None,'+31':None},bounded_recruitment_observation=native['bounded_recruitment_observation'],limits=['Absent bus events on this one route do not exclude an access or prove an unused field.','300 store dummy reads do not consume field data in game logic.','City+1 has 12 dedicated loads at 10:BD97 in the LE16(+1,+2)>=300 predicate; official meaning remains unknown.','All tail bytes are bulk initialized and copied; no dedicated tail consumer observed on this route.','Observer is a separately rebuilt instrumented core; original binary equivalence was checked only on the six declared runs.','No native successful unaffiliated recruitment was observed; all three scans contained no eligible status0 officer.'],source_CPU_cases=0)
 write('evidence.json',evidence)
 dependencies=[Path(__file__),ROOT/'scripts/capture_city_auxiliary_watchpoints.py',base/'runtime/evidence.json',base/'runtime/validation.json',path/'bus-events.bin',path/'events.jsonl',path/'event-schema.json',base/'runtime/core-provenance/observer.patch',base/'runtime/core-provenance/build.json',base/'fields-static/all-indirect-accesses.json',base/'fields-static/phase20-remaining380-handling.json']
 pins={str(p.relative_to(ROOT)):sha(p)for p in dependencies}
 for name in('all1526-association.json','previous380-association.json','all150-field-slots.json','evidence.json'):pins[str((OUT/name).relative_to(ROOT))]=sha(OUT/name)
 write('verification.json',dict(status='passed',failed_count=0,checks=dict(raw_decode_exact=len(events),static_opcode_byte_matches=1526,all_previous_candidates=380,all_field_slots=150,negative_observations_promoted_to_exclusion=0,source_CPU_cases=0),dependency_pins=pins));print(json.dumps({k:v for k,v in evidence.items()if isinstance(v,(int,str))}))
if __name__=='__main__':main()
