#!/usr/bin/env python3
"""Independent originalCPU name-pointer contracts; Source/Native cases0."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import analyze_unknown_pointer_phase30 as model
from py65.devices.mpu6502 import MPU
OUT=model.OUT
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class ContractBus:
 """Explicit RAM/SRAM/PRG mapping only; no hardware values or acknowledgements."""
 def __init__(self,rom,ram=None,sram=None,banks=(0,12,13,31)):
  self.rom=rom;self.ram=bytearray(2048)if ram is None else bytearray(ram);self.sram=bytearray(8192)if sram is None else bytearray(sram);self.banks=list(banks);self.mapper_writes=[]
  assert len(self.ram)==2048 and len(self.sram)==8192 and self.banks[1:]==[12,13,31]
 def __len__(self):return 65536
 def __getitem__(self,a):
  a&=65535
  if a<8192:return self.ram[a&2047]
  if 0x6000<=a<0x8000:return self.sram[a-0x6000]
  if a>=0x8000:return self.rom[16+8192*self.banks[(a-0x8000)//8192]+(a&8191)]
  raise RuntimeError(f'Explicit hardware input unavailable:{a:04X}')
 def __setitem__(self,a,v):
  a&=65535;v&=255
  if a<8192:self.ram[a&2047]=v;return
  if 0x6000<=a<0x8000:self.sram[a-0x6000]=v;return
  if a in(0xE000,0xE800,0xF000):
   window={0xE000:0,0xE800:1,0xF000:2}[a];self.banks[window]=v&31;self.mapper_writes.append(dict(address=a,value=v,physical_bank=v&31));return
  raise RuntimeError(f'Unsupported hardware/ROM write:{a:04X}')
def fixture(rom,entry,*,ruler=0,leader=0,other=3,other_leader=236,order=0,side=0,oam=0):
 m=ContractBus(rom,banks=(17 if entry==0xCC6D else 2,12,13,31));m[0x507]=(ruler<<4)|other;m[0x5E]=order;m[0x7C]=oam
 m[0x6F07+8*ruler]=leader;m[0x6F07+8*other]=other_leader
 # When both packed indices coincide, the live single record is decisive.
 m[0x0A]=side*12;m[0x0B]=0x80 if side else 0x40;m[0x0C]=0x70 if side else 0
 ret=0xCC57 if entry==0xCC6D else 0xD4F3;sp=253;m[0x100+((sp+1)&255)]=(ret-1)&255;m[0x100+((sp+2)&255)]=(ret-1)>>8
 return m,dict(a=ruler,x=91,y=57,p=0x20,sp=sp,pc=entry),ret
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==model.ROM_SHA
 summary=json.loads((OUT/'analysis-summary.json').read_text());proof=json.loads((OUT/'name-pointer-lifecycle-contract.json').read_text());rows=json.loads((OUT/'all-indirect-accesses.json').read_text())['accesses'];by={(r['physical_bank'],r['cpu']):r for r in rows}
 for group in('source_and_validator_sha256','artifact_sha256'):
  for path,value in summary[group].items():assert sha(ROOT/path)==value,('stale analyzer/input',path)
 assert sha(ROOT/'analysis/phase29/verification.json')==model.BASE_AUDIT
 observations=[];visits=Counter();checks=[];inputs={};counts=Counter()
 def check(name,test):assert test,name;checks.append(dict(name=name,passed=True))
 def original(m,r,stop,expected,tag,comparison,origin):
  cpu=MPU(memory=m)
  for k,v in r.items():setattr(cpu,k,v)
  before=bytes(m.sram);selected=[]
  for steps in range(10000):
   if steps and cpu.pc==stop:break
   assert cpu.pc>=0x8000,(tag,cpu.pc)
   bank=m.banks[(cpu.pc-0x8000)//8192];visits[bank,cpu.pc]+=1
   if(bank,cpu.pc)in model.TARGETS:
    ptr=m[6]|m[7]<<8;address=(ptr+cpu.y)&65535;c=by[bank,cpu.pc]['address_contract']
    assert m.banks[0]==17 and cpu.y==0 and ptr in c['whole_pointer_values']and address not in model.AUX,(tag,hex(cpu.pc),hex(ptr),cpu.y)
    selected.append(dict(cpu=cpu.pc,pointer06=ptr,Y=cpu.y,logical_address=address,data_physical_bank=m.banks[0],value=m[address]))
   cpu.step()
  else:raise RuntimeError((tag,'CPU budget',hex(cpu.pc)))
  assert [(x['cpu'],x['logical_address'])for x in selected]==expected,(tag,selected,expected)
  assert bytes(m.sram)==before and m.banks==[17,12,13,31]
  expected_sp=r['sp']if comparison=='actual_D4F0_before_farcall_prefix'else(r['sp']+2)&255
  assert cpu.sp==expected_sp,(tag,cpu.sp,expected_sp)
  counts[comparison]+=1
  observations.append(dict(case=tag,origin=origin,entry=r['pc'],stop_PC=cpu.pc,final_SP=cpu.sp,comparison=comparison,original_instructions=steps,selected_reads=selected,SRAM_all8192_unchanged=True,declared_RAM_bytes=2048,Source_compared=False,mapper_writes=m.mapper_writes))
 def packet(leader):
  base=0x8DB4+13*leader
  return[(0xCC92,base)]+[(0xCCAC,base+i)for i in range(1,13)]
 # A typed direct callee is a constructor fixture, not a discovered caller.
 for ruler in range(7):
  for leader in range(256):
   for side in(0,1):
    m,r,stop=fixture(rom,0xCC6D,ruler=ruler,leader=leader,other=(ruler+1)%7,side=side,oam=(leader*4)&255)
    original(m,r,stop,packet(leader),f'typed-CC6D/ruler{ruler}/leader{leader}/side{side}','actual_typed_CC6D_callee_RTS','explicit_constructor_caller_and_selected_data_bank17_fixture')
 # Complete CC29 performs its own mapper selection from a different page.
 for ruler in range(7):
  for leader in range(256):
   for order in(0,1):
    other=(ruler+3)%7;m,r,stop=fixture(rom,0xCC29,ruler=ruler,leader=leader,other=other,other_leader=(leader*73+17)&255,order=order,oam=252 if leader&1 else 0)
    ordered=[ruler,other]if order==0 else[other,ruler];expected=sum((packet(m[0x6F07+8*i])for i in ordered),[])
    original(m,r,stop,expected,f'full-CC29/ruler{ruler}/leader{leader}/order{order}','actual_complete_CC29_caller_RTS','explicit_full_CC29_caller_fixture; no IRQ/NMI')
 # Reuse8 frozen29 software input states without new PC,stack or numeric writes.
 for path in sorted((ROOT/'analysis/phase29/cpu-completion/actual-callers').glob('entry-*/context.json')):
  ctx=json.loads(path.read_text());entry=ctx['registers']['pc']
  if entry not in(0xCC29,0xD4F0):continue
  folder=path.parent
  for f in(path,folder/'input-ram.bin',folder/'input-sram.bin'):inputs[str(f.relative_to(ROOT))]=sha(f)
  m=ContractBus(rom,(folder/'input-ram.bin').read_bytes(),(folder/'input-sram.bin').read_bytes(),ctx['physical_banks']);r=dict(ctx['registers']);assert not r['p']&8
  hi,lo=m[0x507]>>4,m[0x507]&15;assert hi<7 and lo<7;order=m[0x5E]&1;ordered=[hi,lo]if order==0 else[lo,hi];expected=sum((packet(m[0x6F07+8*i])for i in ordered),[])
  stop=ctx['existing_return_PC']if entry==0xCC29 else 0xD4F3
  original(m,r,stop,expected,'frozen29/'+folder.name,'actual_captured_CC29_caller_RTS'if entry==0xCC29 else'actual_D4F0_before_farcall_prefix',ctx['origin'])
 # BareCCAA has no prior producer constraint; execute LDY0 and its read only.
 bare=[]
 for ptr in(0x6001,0x601C,0x601F):
  m,r,_=fixture(rom,0xCC29);m[6]=ptr&255;m[7]=ptr>>8;m[ptr]=73;r['pc']=0xCCAA;cpu=MPU(memory=m)
  for k,v in r.items():setattr(cpu,k,v)
  visits[13,cpu.pc]+=1;cpu.step();assert cpu.pc==0xCCAC and cpu.y==0;visits[13,cpu.pc]+=1;cpu.step();assert cpu.pc==0xCCAE and cpu.a==73
  bare.append(dict(entry=0xCCAA,pointer06=ptr,Y=0,logical_address=ptr,read_PC=0xCCAC,original_instructions=2,comparison='explicit_bare_CCAA_counterexample_prefix',full_CC29_contract_applies=False));counts['explicit_bare_CCAA_counterexample_prefix']+=1
 # Execute all raw invalid F368 prefixes, then stop before reading their target.
 raw=[]
 for ruler in range(7,16):
  m,r,_=fixture(rom,0xCC6D,ruler=0);r['a']=ruler;cpu=MPU(memory=m)
  for k,v in r.items():setattr(cpu,k,v)
  steps=0
  while cpu.pc!=0xCC72:
   visits[m.banks[(cpu.pc-0x8000)//8192],cpu.pc]+=1;cpu.step();steps+=1;assert steps<40
  pointer=m[0]|m[1]<<8;assert pointer==proof['raw16_ruler_words'][ruler]
  raw.append(dict(raw_ruler=ruler,entry=0xCC6D,stop_PC=0xCC72,ruler_pointer=pointer,original_instructions=steps,read_not_executed=True,normal_contract_applies=False,comparison='raw_ruler_factory_prefix_before_unprovided_read'));counts['raw_ruler_factory_prefix_before_unprovided_read']+=1
 check('3584typedCC6Dconstructor_callees_all256leader7ruler2sides',counts['actual_typed_CC6D_callee_RTS']==3584)
 check('3584completeCC29_callers_all256leader7ruler2orders',counts['actual_complete_CC29_caller_RTS']==3584)
 check('frozen29_actual_draw4RTS_and_fullcaller4prefix_notnewNative',counts['actual_captured_CC29_caller_RTS']==counts['actual_D4F0_before_farcall_prefix']==4)
 check('all13_packet_reads_match_original_factory_and_increment',all(len(r['selected_reads'])in(13,26)for r in observations))
 check('selected_Y0_logical_addresses_not_city_aux',all(v['Y']==0 and v['logical_address']not in model.AUX for r in observations for v in r['selected_reads']))
 check('bare_CCAA_three_auxiliary_reads_are_real_counterexamples',len(bare)==3 and all(v['logical_address']in model.AUX for v in bare))
 check('raw7to15_prefixes_all_original_words_not_clamped',len(raw)==9 and raw[1]['ruler_pointer']==0x5F20)
 valid=dict(root=0xCC29,pair=[12,13],complete_CC29=True,F25F31_executed=True,data_bank=17,rulers=[0,6],interrupted=False,binary=True,middle_entry=False)
 check('complete_current_lifecycle_accepts_typed_context',model.admissible_context(valid))
 for key,value in(('root',0xCCAA),('pair',[8,9]),('complete_CC29',False),('F25F31_executed',False),('data_bank',16),('rulers',[0,8]),('interrupted',True),('binary',False),('middle_entry',True)):
  ctx=dict(valid);ctx[key]=value;check('reject_missing_premise:'+key,not model.admissible_context(ctx))
 prior={(r['physical_bank'],r['cpu']):r for r in model.read('analysis/phase27/fields-static/all-indirect-accesses.json')['accesses']}
 for r in rows:
  key=r['physical_bank'],r['cpu'];p=r['address_contract']
  if key in model.TARGETS:
   expected=model.address_contract(key[1]);assert p==expected and r['whole_pointer_values']==p['whole_pointer_values']and r['Y_values']==p['Y_values'];assert not({model.normal((w+y)&65535)for w in p['whole_pointer_values']for y in p['Y_values']}&model.AUX)
  else:assert r['classification']==prior[key]['classification']and p==prior[key]['address_contract']
 check('only2authority_rows_change_and_top_projection_matches',sum(r['newly_proved_disjoint']for r in rows)==2 and len(rows)==1526)
 check('raw345_ledger_exact_not_new_reachability',json.loads((OUT/'raw345-executability-ledger.json').read_text())==model.read('analysis/phase23/fields-static/raw345-executability-ledger.json'))
 check('official_auxiliary_names_remain_null',all(v is None for v in summary['official_target_field_names'].values()))
 for r in proof['original_instructions']+proof['explicit_data']:
  o=model.off(r['physical_bank'],r['cpu']);bs=bytes.fromhex(r['raw_hex']);assert r['rom_offset']==o and rom[o:o+len(bs)]==bs
 check('all_original_instruction_and_data_bytes_plus16',True)
 sourcepins={str(Path(__file__).relative_to(ROOT)):sha(__file__),str(Path(model.__file__).relative_to(ROOT)):sha(model.__file__)}
 artifacts={**summary['artifact_sha256'],**inputs,**{str(p.relative_to(ROOT)):sha(p)for p in OUT.iterdir()if p.is_file()and p.name not in('verification.json','evidence.json','README.md')}}
 complete=sum(n for k,n in counts.items()if k.endswith('_RTS'));prefix=sum(counts.values())-complete
 (OUT/'README.md').write_text(f'''# CC29完整姓名指针：两个条件不交合同

本轮只迁移13:CC92、CCAC两处，冻结1526分母由1198/81/247变为1200条件不交/81可能/245未知，328候选→326。城市+1/+28..31正式含义仍未知；条件不交不是所有裸入口、所有CPU总线或全ROM未使用证明。

完整CC29先F25F31选physical17，再以0507高/低ruler索引经F368取首将byte。合同限正常ruler0..6，保留全部rawleader0..255；237..255超出已识别237条姓名表但不能截断原算法。EBE9真乘13、完整加8DB4后CC92以Y0读首byte，原12次CCAA/CCDF读后12byte。原指针域8DB4..9AB3仍在ROM窗。所有postconstructor写已盘点：只有CCDF递增06/07，OAM绝对X写0200..0302不触指针。无中断前提明确，不把瞬间低半更新称为硬件原子，也不按同callPC关联不同动态代。

 CC6D本身不选择data bank；其直接矩阵为显式选bank17的typed构造caller，不能泛化为所有裸CC6D。原完整CC29矩阵从另一data页开始，实际执行F25F。每个正常ruler覆盖全部256个当前leader和两方次序；另一方取固定循环ruler及rawleader置换，并非穷举全部双leader笛卡尔组合。结构证明按当前单包因子化：构造前重设00..03，乘法重设04..09，前一包不改ruler SRAM；因此不能仅用采样量代替完整写域／调用链依据。裸CCAA以06/07=6001/601C/601F真实读辅助字节的三个前缀反例保留；rawruler7..15只执行F368前缀后在CC72前停止，8的5F20硬件值没有伪造。

新增独立原CPU合同{sum(counts.values())}案：{complete}正常RTS、{prefix}明确前缀；其中冻结29软件输入8份重新CPU续行（CC29四完整RTS，D4F0四案仅到D4F3），不是新Native捕获或Source对照。模型/字节检查{len(checks)}项单列。生产Source病例0、Native帧0。全部固定helper执行原指令，无helperRTS替身；Bus只含2K RAM/8K SRAM/PRG和真实mapper写，其余硬件读拒绝。逐案核所有8K SRAM不变、读取顺序与完整地址域；没有假称对另一Source全2K/寄存器差分。

逻辑EA与dummy分开。这里两种IndY读均Y0，没有额外跨页dummy读；py65仍不是完整微周期总线观察核。raw345账本逐项继承104操作数/13数据/228未证控制，不增加动态覆盖或未使用名称。

复现：`python3 scripts/analyze_unknown_pointer_phase30.py ROM`；`.venv-trace/bin/python scripts/verify_unknown_pointer_phase30.py ROM`。仅写新phase30目录，不运行旧producer，旧Source/Native/归档不改。
''')
 artifacts['analysis/phase30/fields-static/README.md']=sha(OUT/'README.md')
 result=dict(schema='phase30-original-name-pointer-contract-validation-v1',status='passed',failed_count=0,ROM_sha256=model.ROM_SHA,source_CPU_cases=0,Native_frames=0,original_contract_CPU_cases=sum(counts.values()),counts=dict(counts),actual_caller_RTS_CPU_cases=complete,explicit_prefix_CPU_cases=prefix,model_guard_check_count=len(checks),model_checks=checks,case_rows=observations,bare_counterexamples=bare,raw_ruler_prefixes=raw,actual_frozen29_input_count=8,new_Native_captures=0,source_original_CPU_callbacks=0,source_and_validator_sha256=sourcepins,artifact_sha256=artifacts,executed_instruction_positions=[dict(physical_bank=b,cpu=pc,count=n)for(b,pc),n in sorted(visits.items())],remaining_access_count=326,all_indirect_classification_counts=summary['all_indirect_classification_counts'],newly_proved_disjoint_all_count=2,comparison_scope='OriginalCPU logical-read/order/address/postcondition oracle only; no Source comparison, hardware synthesis or dummy-cycle capture.',limits=proof['limits'])
 model.save('verification.json',result);model.save('evidence.json',dict(schema='phase30-CC29-pointer-contract-evidence-v1',**{k:result[k]for k in('status','ROM_sha256','source_CPU_cases','Native_frames','original_contract_CPU_cases','counts','actual_caller_RTS_CPU_cases','explicit_prefix_CPU_cases','model_guard_check_count','source_and_validator_sha256','remaining_access_count','all_indirect_classification_counts','newly_proved_disjoint_all_count','limits')},artifact_sha256=artifacts|{'analysis/phase30/fields-static/verification.json':sha(OUT/'verification.json')}))
 print(json.dumps({k:result[k]for k in('status','original_contract_CPU_cases','counts','model_guard_check_count','remaining_access_count')}))
if __name__=='__main__':main()
