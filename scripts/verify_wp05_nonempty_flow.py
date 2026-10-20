#!/usr/bin/env python3
"""Root's read-only acceptance of the newly captured WP05 path. No emulation."""
from pathlib import Path
import ast,collections,hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp05-natural-nonempty'
RUNTIME=OUT/'runtime';CASE=RUNTIME/'natural-day31-nonempty';OBS=CASE/'observer'
ROM=Path('/Users/paulasmith/Downloads/三国志2超级版.nes')
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
def pin(p):p=Path(p);return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def write(p,d):assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 n=read(RUNTIME/'validation.json');assert n['status']=='passed'and n['fresh_process_runs']==4 and n['all_control_frames']==1532
 assert n['all_five_complete_buffers_equal_each_frame']and n['all_artifacts_repeat_exact']and not n['initial_pre_run_RGB_available']
 assert n['script_sha256']==sha(ROOT/'scripts/capture_native_wp05_nonempty.py')
 b=read(OUT/'core-provenance/build.json');assert b['explicit_final_link_proven']and b['include_touch_rebuild_byte_identical']
 assert sha(ROOT/b['observer']['path'])==b['observer']['sha256']
 rom=ROM.read_bytes();assert digest(rom)=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
 events=[];outcomes=[];total=0
 with(OBS/'events.jsonl').open()as f:
  for line in f:
   e=json.loads(line);total+=1;assert e['sequence']==total
   if e['day31_outcome_producer']:outcomes.append(e)
   if e['frame']==357:events.append(e)
 assert total==265872 and len(outcomes)==1
 outcome=outcomes[0];assert(outcome['frame'],outcome['opcode_PC'],outcome['address'],outcome['value'],outcome['storage_byte_before_write'])==(1,0xCF02,0x514,1,1)
 def opcode(e):return rom[e['rom_offset']]
 assert rom[outcome['rom_offset']:outcome['rom_offset']+3]==bytes.fromhex('8D 14 05')
 assert outcome['RAM0514_0517'][0]==1
 snapshots={r['event_sequence']:r for r in map(json.loads,(OBS/'snapshot-index.jsonl').read_text().splitlines())}
 def op(bank,pc,after=0):return next(e for e in events if e['kind']=='opcode_boundary'and e['physical_bank']==bank and e['opcode_PC']==pc and e['sequence']>after)
 def memory(e):
  row=snapshots[e['sequence']];r=(OBS/row['exported_RAM']).read_bytes();s=(OBS/row['exported_SRAM']).read_bytes()
  assert digest(r)==row['RAM_sha256']and digest(s)==row['SRAM_sha256']
  assert list(r[:48])==e['ZP_0000_002F'];return r,s,row
 def cite(e):
  return {k:e[k]for k in('sequence','frame','cycle','physical_bank','opcode_PC','SP','stack_top_word_raw','A','X','Y','P','full_snapshot_sequence')}
 calls=[]
 def jsr(call_pc,callee_bank,callee_pc,after=0,return_pc=None,rts_pc=None):
  call=op(8,call_pc,after);entry=op(callee_bank,callee_pc,call['sequence'])
  assert opcode(call)==0x20 and int.from_bytes(rom[call['rom_offset']+1:call['rom_offset']+3],'little')==callee_pc
  pushes=[e for e in events if call['sequence']<e['sequence']<entry['sequence']and e['original_selected_Push8_write']and e['opcode_PC']==call_pc]
  assert len(pushes)==2
  expected=[(0x100+call['SP'],(call_pc+2)>>8,(call['SP']-1)&255),(0x100+((call['SP']-1)&255),(call_pc+2)&255,(call['SP']-2)&255)]
  assert[(e['address'],e['value'],e['SP'])for e in pushes]==expected
  r,_,_=memory(call)
  assert[e['storage_byte_before_write']for e in pushes]==[r[e['address']]for e in pushes]
  assert entry['SP']==(call['SP']-2)&255 and entry['stack_top_word_raw']==call_pc+2
  reads=[e for e in events if call['sequence']<e['sequence']<entry['sequence']and e['kind']=='read'and e['opcode_PC']==call_pc and call_pc<=e['address']<=call_pc+2]
  assert[(e['address'],e['value'])for e in reads]==[(call_pc,0x20),(call_pc+1,callee_pc&255),(call_pc+2,callee_pc>>8)]
  assert reads[1]['sequence']<pushes[0]['sequence']<pushes[1]['sequence']<reads[2]['sequence']
  row=dict(current_frame_id=f"357:{call['sequence']}",actual_call=cite(call),actual_opcode_bytes=rom[call['rom_offset']:call['rom_offset']+3].hex(),
   original_operand_fetches=reads,actual_Push8_writes=pushes,actual_entry=cite(entry),
   observed_entry_cycle_delta=entry['cycle']-call['cycle'],return_stack_word_from_current_actual_JSR=True,
   transfer_source_inferred_from_ret_minus3=False)
  assert row['observed_entry_cycle_delta']==72
  if return_pc is not None:
   returned=op(8,return_pc,entry['sequence']);rts=op(callee_bank,rts_pc,entry['sequence'])if rts_pc else None
   assert returned['SP']==call['SP']
   if rts:
    assert rts['sequence']<returned['sequence']and opcode(rts)==0x60
    assert rts['stack_top_word_raw']==call_pc+2 and rts['SP']==entry['SP']
    row['actual_pre_RTS']=cite(rts);row['observed_RTS_to_continuation_cycle_delta']=returned['cycle']-rts['cycle'];assert row['observed_RTS_to_continuation_cycle_delta']==72
   row['derived_expected_return_PC']=call_pc+3;row['actual_continuation']=cite(returned);assert return_pc==call_pc+3
  calls.append(row);return call,entry,row
 root,bc46,rootcall=jsr(0xBB36,8,0xBC46,return_pc=0xBB39,rts_pc=0xBD95)
 dispatch,EADE,dispatchcall=jsr(0xBC49,31,0xEADE,after=bc46['sequence'])
 p1=op(31,0xEAE3,EADE['sequence']);p2=op(31,0xEAE6,p1['sequence']);jump=op(31,0xEAF4,p2['sequence']);mode2=op(8,0xBD67,jump['sequence'])
 assert opcode(p1)==opcode(p2)==0x68 and opcode(jump)==0x6C
 assert [p1['SP'],p2['SP'],jump['SP'],mode2['SP']]==[234,235,236,236]
 assert jump['ZP_0000_002F'][3:5]==[0x67,0xBD]and mode2['stack_top_word_raw']==0xBB38
 assert mode2['postbattle_mode_6F91']==2
 dispatchcall['completion_kind']='actual_two_PLA_consumed_JSR_frame_then_indirect_tail_dispatch_no_RTS_to_BC4C'
 dispatchcall['actual_PLA_boundaries']=[cite(p1),cite(p2)];dispatchcall['actual_indirect_JMP']=cite(jump);dispatchcall['actual_mode_target']=cite(mode2)
 _,collect_entry,_=jsr(0xBD67,8,0xBDCD,after=mode2['sequence']-1,return_pc=0xBD6A,rts_pc=0xBE54)
 collect_exit=op(8,0xBE54,collect_entry['sequence']);r0,s0,c0=memory(collect_entry);r1,s1,c1=memory(collect_exit)
 before=list(s0[0xFA1:0xFB6]);after=list(s1[0xFA1:0xFB6]);assert after==[67]+[255]*20 and before[0]==255
 generated=[e for e in events if collect_entry['sequence']<e['sequence']<collect_exit['sequence']and e['kind']=='write_attempt'and e['address']==0x6FA1 and e['value']==67]
 assert len(generated)==1 and generated[0]['opcode_PC']==0xBDF7
 _,priority_entry,_=jsr(0xBD6A,8,0xBE55,after=collect_exit['sequence'],return_pc=0xBD6D,rts_pc=0xBE89)
 selfswaps=[e for e in events if priority_entry['sequence']<e['sequence']<op(8,0xBE89,priority_entry['sequence'])['sequence']and e['kind']=='write_attempt'and e['opcode_PC']in(0xBE80,0xBE86)]
 assert[(e['opcode_PC'],e['address'],e['storage_byte_before_write'],e['value'],e['physical_storage_byte_after_event'])for e in selfswaps]==[(0xBE80,0x6FA1,67,67,67),(0xBE86,0x6FA1,67,67,67)]
 jsr(0xBD73,31,0xF2AF,after=priority_entry['sequence'],return_pc=0xBD76)
 _,fill_entry,_=jsr(0xBD8E,8,0xBD96,after=priority_entry['sequence'],return_pc=0xBD91,rts_pc=0xBDAA)
 jsr(0xBD99,31,0xF2AF,after=fill_entry['sequence'],return_pc=0xBD9C)
 site=op(8,0xBDB8,fill_entry['sequence']);rpre,spre,spre_meta=memory(site)
 stores=[e for e in events if e['BDB8_logical_store']];dummies=[e for e in events if e['BDB8_STA_dummy_read']]
 assert len(stores)==len(dummies)==1;store,dummy=stores[0],dummies[0]
 assert opcode(site)==0x91 and rom[site['rom_offset']+1]==0
 assert(site['A'],site['Y'],site['pointer_0000_0001'])==(67,20,0x6200)
 assert(store['address'],store['storage_byte_before_write'],store['value'],store['physical_storage_byte_after_event'])==(0x6214,255,67,67)
 assert(dummy['address'],dummy['value'])==(0x6214,255)and site['sequence']<dummy['sequence']<store['sequence']
 finish=op(8,0xBB39,store['sequence']);rpost,spost,post_meta=memory(finish)
 base=16*32;roster_before=list(spre[base+17:base+27]);roster_after=list(spost[base+17:base+27])
 assert roster_before==[163,158,89]+[255]*7 and roster_after==[163,158,89,67]+[255]*6
 changed=[0x6000+i for i,(a,z)in enumerate(zip(spre[:0x3C0],spost[:0x3C0]))if a!=z];assert changed==[0x6214]
 o=0x3C0+12*67;officer_before=spre[o:o+12];officer_after=spost[o:o+12]
 assert officer_before==officer_after==bytes.fromhex('484f4a545000e803e803281a')
 frames=read(CASE/'original-control/frame-services.json');assert len(frames)==383
 states=[];prev=None
 for row in frames:
  key=[row['global_007A'],row['NMI_0078'],*row['battle_0500_0501']]
  if key!=prev:states.append(dict(frame=row['frame'],parent_frame=7610+row['frame'],state=key));prev=key
 assert frames[-1]['global_007A']==2
 later=[]
 # The following player's return is retained and attributed separately.
 for line in(OBS/'events.jsonl').open():
  e=json.loads(line)
  if e['kind']=='write_attempt'and e['address']==0x6171 and e['value']==131 and e['frame']>357:later.append(e)
 player_returns=[e for e in later if e['physical_bank']==13 and e['opcode_PC']==0xD4BA]
 later_same_value_stores=[e for e in later if e not in player_returns]
 assert len(player_returns)==1 and player_returns[0]['storage_byte_before_write']==255
 assert[(e['physical_bank'],e['opcode_PC'],e['storage_byte_before_write'],e['physical_storage_byte_after_event'])for e in later_same_value_stores]==[(8,0xBC3C,131,131),(8,0xBC43,131,131)]
 source=ROOT/'source/recovered/postbattle_early_services.py';tree=ast.parse(source.read_text());methods={x.name:x.lineno for x in ast.walk(tree)if isinstance(x,ast.FunctionDef)}
 names=['allocate_defeated_attacker','collect_side_officers_and_captives','prioritize_original_commander','fill_pointed_city_roster']
 assert all(name in methods for name in names)
 source_map=[dict(path=str(source.relative_to(ROOT)),method=name,line=methods[name],sha256=sha(source),new_implementation=False)for name in names]
 e=dict(schema='wp05-actual-natural-nonempty-mode2-evidence-v1',status='passed_bounded_natural_route',
  ROM_sha256=digest(rom),native_validation=pin(RUNTIME/'validation.json'),core_build=pin(OUT/'core-provenance/build.json'),
  producer=pin(ROOT/'scripts/capture_native_wp05_nonempty.py'),case=pin(OUT/'case-spec.json'),ancestry=pin(OUT/'ancestry.json'),
  raw_events=pin(OBS/'bus-events.bin'),decoded_events=pin(OBS/'events.jsonl'),snapshot_index=pin(OBS/'snapshot-index.jsonl'),
  actual_outcome_writer=outcome,same_value_original_outcome_store=True,
  actual_call_frames=calls,temporary_roster=dict(before=before,after=after,nonempty_count=1,officer_ids=[67],
   actual_original_writer=generated[0],before_snapshot=pin(OBS/c0['exported_SRAM']),after_snapshot=pin(OBS/c1['exported_SRAM'])),
  priority=dict(actual_BE55_called=True,actual_swap_body_executed=True,actual_same_index_self_swap=True,
   actual_writes=selfswaps,nontrivial_two_different_slots_exchanged=False),
  allocation=dict(officer_id=67,city_index=16,raw_address=0x6214,city_offset=20,roster_slot_zero_based=3,
   city_roster_before=roster_before,city_roster_after=roster_after,actual_pre_store=cite(site),actual_dummy_read=dummy,actual_logical_store=store,
   dummy_and_store_address_coincide=True,access_kind_and_original_opcode_distinguish_them=True,
   officer_record_before_hex=officer_before.hex(),officer_record_after_hex=officer_after.hex(),officer_record_changed=False,
   city_changed_addresses_during_BD96_to_BB39=changed,actual_return=cite(finish),
   before_snapshot=pin(OBS/spre_meta['exported_SRAM']),after_snapshot=pin(OBS/post_meta['exported_SRAM'])),
  later_separate_player_return=player_returns[0],later_separate_same_value_city_stores=later_same_value_stores,
  state_transitions=states,readable_source_mapping=source_map,
  source_CPU_cases=0,new_gameplay_algorithms=0,
  observed_E066_contexts_saved=sum(1 for row in snapshots.values()if row['entry']==0xE066),
  uncovered=['Nontrivial BE55 exchange between different indices','Full-city / adjacent-city BE90 fallback','Other officer/city outcomes or arbitrary interrupt schedules','Human14 phases1..6 and full continuous Source UI'],
  fixed_field_ledger_unchanged=dict(denominator=1526,conditional_disjoint=1201,possible=80,unknown=245,remaining=325,raw345_separate=True),
  city_official_names={'1':None,'28':None,'29':None,'30':None,'31':None},
  whole_game_closure_proven=False,unknown_unique_services=None,completion_percentage=None,remaining_rounds_estimate=None,
  limits=['Raw observed native-mode2 allocation; it is not in-wild recruitment or a change of the raw officer12 record.',
   'Final global2/NMI2 city13/0 is a black-screen city scheduling/transition boundary, not proven operable world0/1 or completion of city13 events.',
   '052C is observed in software snapshots, but its BDB4 write is outside this observer write predicate; no bus-write capture is claimed for it.',
   'Before retro_run imported API has no RGB/audio callback. Exact state+2K/8K are compared there; first real callback frame is the initial five-buffer boundary.',
   'Historical six-segment lineage is original-only, not new coldboot/fresh repeat. New1532 control frames are the four383-frame processes only.',
   'No production CPU/IR fallback or new Source gameplay proof; existing readable code is mapped without modifying frozen files.'])
 write(OUT/'evidence.json',e)
 write(OUT/'flow-validation.json',dict(schema=e['schema'],status='passed',evidence=pin(OUT/'evidence.json'),
  actual_current_JSR_frames=len(calls),outcome_same_value_original_store=1,nonempty_officers=1,actual_BDB8_roster_commits=1,
  actual_BDB8_STA_dummy_reads=1,true_BB39_PC_SP_return=True,full_window_returns_global2=True,
  Native_first_original_frames=383,Native_all_control_frames=1532,Native_fresh_processes=4,
  Source_CPU_cases=0,independent_contract_CPU_cases=0,field_classification_changes=0,
  new_core_memory_writes=0,arbitrary_current_case_result_RNG_ready_PC_roster_injections=0))
 print(json.dumps(dict(status='passed',current_JSR_frames=len(calls),nonempty_officers=[67],city16_slot3=[255,67],BB39_SP=finish['SP'],outcome_514=[1,1],E066_saved=e['observed_E066_contexts_saved'],last_state=states[-1])),flush=True)
if __name__=='__main__':main()
