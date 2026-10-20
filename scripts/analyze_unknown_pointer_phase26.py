#!/usr/bin/env python3
"""One G107 deployment-constructor contract; older authority is unchanged."""
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase26/fields-static'
spec=importlib.util.spec_from_file_location('frozen25_pointer_model',ROOT/'scripts/analyze_unknown_pointer_phase25.py');old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
base=old.base;DISJOINT=old.DISJOINT;TARGETS=frozenset((8,pc)for pc in(0xB272,0xB278,0xB290,0xB296))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def byte(rom,bank,pc):return rom[base.original(bank,pc)]
def pointer_words(rom,entry):
 table,stride=(0x8C52,32)if entry==0xB2AE else(0x8000,34)
 raw_bases=[byte(rom,6,table+2*i)|byte(rom,6,table+2*i+1)<<8 for i in range(128)]
 offsets=sorted({stride*i&255 for i in range(256)})
 words=frozenset((p+offset)&65535 for p in raw_bases for offset in offsets)
 return table,stride,raw_bases,offsets,words
class Analysis(old.Analysis):
 def __init__(self,rom):
  super().__init__(rom);self.formation_contracts={}
  for entry,end,final_A in((0xB2AE,0xB30D,20),(0xB312,0xB36C,28)):
   table,stride,bases,offsets,words=pointer_words(rom,entry);ident=max(self.factory_ids)+1
   d=dict(id=ident,entry=(8,entry),marker=None,end=end,base=0x20,kind='complete_deployment_formation_pointer',addresses=words,writes=frozenset((0x20,0x21,0x22,0x23,0x24,0x25,0xDE)),regs=frozenset(('A','Y')),returns_high=False,prologue=frozenset())
   self.factories[8,entry]=d;self.factory_ids[ident]=d
   self.formation_contracts[entry]=dict(entry=entry,normal_RTS=end,table=table,byte_stride=stride,raw_base_words=bases,offset_bytes=offsets,whole_pointer_values=sorted(words),final_A=final_A,final_Y=4,X_preserved=True)
 def apply_call(self,state,target,key,far=False):
  result=super().apply_call(state,target,key,far)
  if target and target[0]==8 and target[1]in getattr(self,'formation_contracts',{}):
   d=self.formation_contracts[target[1]];result.numbers=(frozenset((d['final_A'],)),state.numbers[1],frozenset((4,)))
  return result
def prove_constructors(e):
 out=[]
 for entry,expected in((0xB2AE,48),(0xB312,44)):
  f=e.function_structure((8,entry));assert not f['barriers']and f['calls']=={(31,0xF266)}and len(f['nodes'])==expected
  d=e.formation_contracts[entry];table=d['table'];nodes=f['nodes'];writes=[];calls=[]
  for key in sorted(nodes):
   row=e.known[key]
   if row['op']=='JSR':assert row['operand']==0xF266;calls.append(e.raw(key))
   if row['op']in base.WRITES and row['mode']!='a':
    addresses=old.old.direct_addresses(row);assert addresses is not None
    if row['mode']=='aby':assert row['operand']==0x22;addresses=frozenset(range(0x22,0x26))
    assert set(addresses)<={0x20,0x21,0x22,0x23,0x24,0x25}
    writes.append(dict(instruction=e.raw(key),complete_effective_addresses=sorted(addresses),bounded_Y0_3_original_loop=row['mode']=='aby'))
  mapper=e.function_structure((31,0xF266));assert len(mapper['nodes'])==3 and not mapper['calls']and not mapper['barriers']
  assert e.rom[base.original(31,0xF266):base.original(31,0xF26D)]==bytes.fromhex('8CDE008C00E060')
  # Pin the complete scalar arithmetic that creates the byte offset and
  # then reconstructs a full low/high pointer with carry.
  if entry==0xB2AE:
   assert e.rom[base.original(8,0xB2DC):base.original(8,0xB2E1)]==b'\x0A'*5
   prefix=(0xB2E9,0xB300);selectors=[0x30,0x31,0x26];groups=[2,8,12,20]
  else:
   assert e.rom[base.original(8,0xB337):base.original(8,0xB340)]==bytes.fromhex('0A0A0A0A186D20000A')
   prefix=(0xB348,0xB35F);selectors=[0x30,0x26];groups=[2,12,22,28]
  read=e.rom[base.original(8,prefix[0]):base.original(8,prefix[1])]
  assert read==bytes.fromhex('AD0E050AA8B9'+f'{table&255:02X}{table>>8:02X}'+'186D20008D2000B9'+f'{(table+1)&255:02X}{(table+1)>>8:02X}'+'69008D2100')
  table_values=[byte(e.rom,8,(0xB30E if entry==0xB2AE else 0xB36D)+i)for i in range(4)];assert table_values==groups
  # Data tables are immutable ROM and the only callee writes DE/E000.
  # The low-byte city index is doubled modulo256, not a guessed city<30.
  words=set(d['whole_pointer_values']);addresses={(p+y)&65535 for p in words for y in range(256)};assert not addresses&base.AUX
  ports=sorted(a for a in addresses if 0x2000<=a<0x6000);assert set(ports)<=set(range(0x2000,0x200F))
  scan=[byte(e.rom,16,0x9D72+i)for i in range(256)];assert any(v&128 for v in scan)
  # Both copies end at Y4 and only22..25 are stored by the original loop.
  loop=0xB302 if entry==0xB2AE else 0xB361
  assert e.rom[base.original(8,loop):base.original(8,loop+12)]==bytes.fromhex('B9'+f'{(loop+12)&255:02X}{(loop+12)>>8:02X}'+'992200C8C00490F560')
  out.append(dict(**d,original_entry=e.raw((8,entry)),original_instructions=[e.raw(k)for k in sorted(nodes)],complete_direct_write_inventory=writes,mapper_calls=calls,mapper_raw_selectors_in_execution_order=selectors,conditional_mapper_selector='31 only for a first-side exact neighbor match'if entry==0xB2AE else None,physical_data_bank_at_return=6,code_windows_preserved=[8,9,31],mapper_original_instructions=[e.raw(k)for k in sorted(mapper['nodes'])],complete_pointer_prefix_raw=dict(physical_bank=8,cpu_start=prefix[0],rom_offset=base.original(8,prefix[0]),raw_hex=read.hex(' ').upper()),group_offsets=groups,neighbor_byte_index='(city*8)&255 then INY wraps; first negative sentinel or exact052A match',termination_bound='Pinned256-byte neighbor window contains a negative sentinel; any raw start reaches one within256 reads if no earlier match, no interrupt/external mutation',normal_city_domain=list(range(30)),raw_city_domain=list(range(256)),coordinate_table_index='(2*rawcity)&255;128 complete words retained',offset_domain_scope='Conservative all256 possible template bytes; multiplication by32/34 wraps byte. Actual immutable direction tables can narrow but are not needed to exclude cityaux.',logical_address_count=len(addresses),raw_alias_examples=[dict(raw_city=i,base_word=p)for i,p in enumerate(d['raw_base_words'])if p<0x8000][:5],normal_city_all_Y_is_bank6_ROM=True,all_raw_domain_excludes_city_SRAM=True,all_raw_domain_excludes_ports=not ports,potential_IO_logical_addresses=ports,binary_no_interrupt_normal_RTS_contract=True))
 # The two callsites form a cut between the original B1B0 entry and all4
 # reads. There are no external calls or20/21 stores after that cut.
 f=e.function_structure((8,0xB1B0));assert f['calls']=={(8,0xB2AE),(8,0xB312)}
 cut={(8,0xB25D),(8,0xB263)};todo=[(8,0xB1B0)];seen=set()
 while todo:
  k=todo.pop()
  if k in seen or k in cut:continue
  seen.add(k);row=e.known[k]
  if row['op']=='JSR':todo.append(base.mapped(k,row['cpu']+row['size']))
  else:todo.extend(e.edges.get(k,()))
 assert not seen&TARGETS
 return dict(schema='phase26-complete-deployment-pointer-postconditions-v1',formations=out,inherited_B1B0_original_instruction_positions=len(f['nodes']),formation_caller_cut=[e.raw(k)for k in sorted(cut)],selected_reads=[e.raw(k)for k in sorted(TARGETS)],formation_return_required_before_selected_reads=True,source_CPU_cases=0,
  credit=dict(inherited_prior_named_B1B0_behavior=True,formation_prior_generated_direct_Source=True,new_semantic_first_recovery=False,new_readable_refactoring_original_positions=92,new_contract='Exact whole-word construction/mapper/real-caller/stack protocol and logical-vs-dummy read domains'),
  limits=['Complete formation call and ordinary no-interrupt binary execution; bare B272/B278/B290/B296 never get a manufactured pointer.','Normalcity0..29 coordinates read bank6 ROM. Raw30..255 are mechanical aliases; some point to mirrored internal RAM, not city records or new legal cities.','Allrawcity words, alltemplate byte offsets and Y0..255 stay in the proof. No capacity/strategy/menu legality is inferred from disjointness.','The conservative second-side raw domain includes2000..200E IO; only address contracts are claimed there, not successful reads, absent effects or legal gameplay. Missing hardware inputs must stop CPU/Source before that read.'])
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 e=Analysis(rom);proof=prove_constructors(e);save('deployment-pointer-postconditions.json',proof)
 for n in range(3):
  e.prove_returns();e.steps=0;e.states={};e.queue=deque();e.scheduled=set();roots,fallback=e.run();added=e.refine_write_effects()if n<2 else None
  e.refinement_rounds.append(dict(round=n+1,original_instruction_transfers=e.steps,new_non_ZP_store_proofs=added,return_contract_count=len(e.return_contracts)))
  if not added:break
 previous_path=ROOT/'analysis/phase25/fields-static/all-indirect-accesses.json';prior=json.loads(previous_path.read_text())['accesses'];rows=[]
 for oldrow in prior:
  key=oldrow['physical_bank'],oldrow['cpu'];authority=e.contract(key)if key in TARGETS else oldrow['address_contract'];row=dict(oldrow);row.update(phase25_classification=oldrow['classification'],newly_proved_disjoint=False)
  if key in TARGETS:
   assert authority is not None and not old.old.old.old.auxiliary_intersection(authority)
   authority['required_execution_contract']=dict(normal_no_interrupt_binary_execution=True,complete_formation_return_required=True,formation_entries=[0xB2AE,0xB312],ordinary_B1B0_call_cut=[0xB25D,0xB263],all_raw_city_bytes_retained=True,all_raw_Y_bytes_retained=True,bare_selected_access_entry_covered=False,physical_data_bank_after_complete_formation=6)
   row.update(classification=DISJOINT,address_contract=authority,whole_pointer_values=sorted(old.old.old.old.projection_words(authority)),Y_values=authority['Y_values'],newly_proved_disjoint=oldrow['classification']!=DISJOINT,proof_basis='phase26_complete_formation_return_pointer_and_mapper',authoritative_contract_origin=None,candidate_contract_is_authoritative=False,authoritative_pointer_representation='complete_joint_address_set')
  rows.append(row)
 for name,data in(('all-indirect-accesses.json',rows),('remaining-accesses.json',[r for r in rows if r['classification']!=DISJOINT]),('selected-accesses.json',[r for r in rows if(r['physical_bank'],r['cpu'])in TARGETS])):
  save(name,dict(schema='phase26-one-G107-pointer-contracts-v1',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,access_count=len(data),classification_counts=dict(Counter(r['classification']for r in data)),newly_proved_disjoint_count=sum(r['newly_proved_disjoint']for r in data),accesses=data))
 dummy=[]
 for r in rows:
  p=r['address_contract'];hits=old.old.old.old.dummy_auxiliary_intersection(p,r['op'])if p else None
  dummy.append(dict(physical_bank=r['physical_bank'],cpu=r['cpu'],operation=r['op'],logical_classification=r['classification'],conditional_dummy_auxiliary_bus_addresses=hits,scope='LDA IndY extra read only on page crossing; stores use their separate unconditional rule. Domain theorem, not py65-observed bus cycles.'))
 save('logical-vs-dummy-bus-contracts.json',dict(access_count=1526,accesses=dummy))
 inputs=['scripts/analyze_unknown_pointer_phase25.py','analysis/phase25/fields-static/all-indirect-accesses.json','analysis/phase25/fields-static/verification.json','analysis/phase11/setup-ai/evidence.json']
 summary=dict(schema='phase26-G107-deployment-pointer-summary-v1',status='analyzed',ROM_sha256=base.ROM_SHA256,analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(__file__),artifact_sha256={p:sha(ROOT/p)for p in inputs},source_CPU_cases=0,selected_group='G107',all_indirect_access_count=1526,all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),previous_candidate_count=339,remaining_access_count=sum(r['classification']!=DISJOINT for r in rows),pre_phase26_unknown_access_count=258,remaining_unknown_access_count=sum(r['classification']=='unresolved_pointer_or_index_contract'for r in rows),newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint']for r in rows),finite_refinement_rounds=e.refinement_rounds,complete_analysis_fixed_point_proven=False,official_target_field_names=dict(city_plus1=None,city_plus28=None,city_plus29=None,city_plus30=None,city_plus31=None),limits=proof['limits'])
 save('analysis-summary.json',summary)
 (OUT/'README.md').write_text('''# G107部署指针合同

仅四读B272/B278/B290/B296新增完整producer/return合同。稳定分母1526：1191不交、81可能、254未知；候选339→335、unknown258→254。其它第25阶段权威合同及分类原样继承。B1B0/B2AE/B312算法与数据含义已经存在，本轮不声称首次发现，不同时扩展另一条链。

两formation仅有固定F266这个callee，原数据窗最后真实选raw26→physical6，8/9/31代码窗不变。first先raw30→16查byte邻接窗口，匹配时raw31→17查template（negative fallback不走17），offset=32×byte mod256；second邻接/template均在16，offset=34×byte mod256。读取bank6表完整low/high word，以真实carry加offset；原city左移一位索引按byte截断，因此256城市原始字节都保留，表共128word。22..25为单独组游标，20/21被重新构造，不能保存旧profile/city类型。

正常city0..29，两表基址和所有byte索引均为bank6 ROM。完整raw域也保留：first564完整word，second4606完整word，含内部RAM镜像；second保守offset/Y域有2000..200E潜在IO。它们只作地址合同，未给硬件输入不执行该读、不声称无副作用/合法城市。四读logicalEA与6000..63BF城市aux不交仍成立，不意味着raw数据有正常坐标意义。

静态postcondition在完整formation普通二进制无中断返回后建立pointer20；两个真实callsiteB25D/B263构成B1B0至四读的必经cut，后续不写20/21。不从裸B272等中段造指针。三个bare读city+1/+28/+31原CPU反例保留，证明单看同一个读PC不够。第一侧真实Native来源只旁证一条路径，不是所有raw输入均可达的定理。

独立原CPU合同36443（Source0）：1024个完整rawformationcaller RTS、600个完整typed B1B0 RTS、34816个完整low/high构造prefix、3个裸访问反例prefix。prefix不是callee返回；raw IO地址枚举执行0指令且不加入CPUcase。另13个模型guard。完整表/真实原字节与producer/caller写清单可复查，不凭名字或Y独立投影拼接不真实word。

LDA IndY仅跨页才额外读未进位页；dummy公式在无跨页时只是候选，py65本身不发该读。逻辑地址与条件dummy域独立计算，和Native STA的无条件dummy规则分开。本轮没有赋予城市+1/+28..31正式名称，也没有unused/padding结论。
''')
 print(json.dumps({k:summary[k]for k in('all_indirect_classification_counts','remaining_access_count','newly_proved_disjoint_all_count')},ensure_ascii=False))
if __name__=='__main__':main()
