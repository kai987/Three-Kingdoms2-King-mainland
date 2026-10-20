#!/usr/bin/env python3
"""OriginalCPU G106 pointer/Y contracts; not Source cases or Native frames."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import analyze_unknown_pointer_phase27 as model
from py65.devices.mpu6502 import MPU
from verify_postbattle_resource_services import fixture
OUT=model.OUT;base=model.base
PARENT_Y={0xBF74:{11},0xBFA0:{2,4,6,8,14},0xBFA6:{3,5,7,9,15},0xBFDF:{2,4,6,8,11,14},0xBFE9:{3,5,7,9,15},0xBFEC:{2,4},0xBFF2:{3,5}}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
 e=model.Analysis(rom);proof=json.loads((OUT/'resource-pointer-lifetime-contract.json').read_text());assert proof==model.prove_helpers(e)
 canonical={(r['physical_bank'],r['cpu']):r for r in json.loads((OUT/'all-indirect-accesses.json').read_text())['accesses']};prefixes=[];parents=[];helpers=[];bare=[];checks=[];visits=Counter()
 def check(name,value):assert value,name;checks.append(dict(name=name,passed=True))
 def original(m,r,stop,watch=None,budget=5000):
  c=MPU(memory=m)
  for k,v in r.items():setattr(c,k,v)
  count=0
  while c.pc!=stop:
   bank=m.banks[(c.pc-0x8000)//8192];visits[bank,c.pc]+=1
   if watch:watch(c,m)
   c.step();count+=1;assert count<budget,(hex(c.pc),stop)
  return c,count
 def observation(c,m):
  ptr=m[0x1A]|m[0x1B]<<8;address=(ptr+c.y)&65535;candidate=(ptr&0xFF00)|((ptr+c.y)&255);op='STA'if c.pc in(0xBFDF,0xBFE9)else'LDA';cross=(ptr&255)+c.y>255
  return dict(cpu=c.pc,operation=op,pointer1A=ptr,Y=c.y,logical_address=address,value=c.a if op=='STA'else m[address],candidate_not_actual_dummy_address=candidate,page_cross=cross,dummy_read_required=op=='STA'or cross,conditional_required_dummy_address=candidate if op=='STA'or cross else None,dummy_scope='Address rule, not py65-observed extra bus event')
 # Real low/high copy follows an actual F2AF JSR and returns to the exact
 # prefix end. Prepared PC here is an explicit constructor-prefix fixture.
 for city in range(256):
  m,r=fixture(rom,city=city);r.update(pc=0xBF15,a=city,y=0);before=bytes(m.sram);c,n=original(m,r,0xBF27)
  ptr=m[0x1A]|m[0x1B]<<8;assert ptr==0x6000+32*city and m[0]|m[1]<<8==ptr and c.sp==r['sp']and bytes(m.sram)==before
  prefixes.append(dict(rawcity=city,entry=0xBF15,end_exclusive=0xBF27,output_pointer1A=ptr,original_instructions=n,comparison='complete_original_constructor_prefix'))
 # Full parent controls actual Y and all7 sites. Cover every raw city while
 # retaining typed hardware semantics: its offsets never reach PRG/IO.
 for city in range(256):
  for rounds in(0,6,11,16,21):
   for cursor in(0,1):
    value=(0,501,502,9999,65535)[rounds//6 if rounds<21 else 4];m,r=fixture(rom,city=city,rounds=rounds,cursor=cursor,value=value);before=bytes(m.sram);accesses=[]
    def watch(c,m):
     if(m.banks[(c.pc-0x8000)//8192],c.pc)in model.TARGETS:
      o=observation(c,m);contract=canonical[8,c.pc]['address_contract'];assert o['pointer1A']==0x6000+32*city and o['pointer1A']in contract['whole_pointer_values']and c.y in contract['Y_values']and c.y in PARENT_Y[c.pc]and o['logical_address']not in base.AUX;accesses.append(o)
    c,n=original(m,r,0xBB99,watch);ptr=0x6000+32*city;changed=[0x6000+i for i,(a,b)in enumerate(zip(before,m.sram))if a!=b]
    assert len(accesses)==26 and c.sp==(r['sp']+2)&255 and set(changed)<={ptr+y for y in(2,3,4,5,6,7,8,9,11,14,15)}
    parents.append(dict(rawcity=city,rounds=rounds,cursor=cursor,comparison='complete_original_BF0A_caller_RTS',original_instructions=n,final_PC=c.pc,final_SP=c.sp,changed_SRAM=changed,selected_accesses=accesses))
 # Bare helper Y is deliberately unrestricted. Its preserved typed pointer
 # is a separate theorem from the parent's finite field selection.
 for entry in(0xBF9E,0xBFB3):
  for y in range(256):
   for rate in(0,9,255):
    for value in(501,65535):
     m,r=fixture(rom,entry,field=y,rate=rate,value=value);x=r['x'];before=m[0x1A]|m[0x1B]<<8;stores=[]
     def watch(c,m):
      if c.pc in(0xBFDF,0xBFE9):stores.append(observation(c,m))
     c,n=original(m,r,0xBF37 if entry==0xBF9E else 0xBF84,watch);expected=y if y==11 else(y+1)&255
     assert c.sp==(r['sp']+2)&255 and c.y==expected and c.x==x and (m[0x1A]|m[0x1B]<<8)==before and len(stores)==(1 if y==11 else 2)
     helpers.append(dict(entry=entry,Y=y,rate=rate,value=value,final_Y=c.y,final_X=c.x,pointer1A_preserved=True,original_instructions=n,comparison='complete_original_typed_pointer_raw_Y_helper_RTS',selected_stores=stores))
 # Explicit one-opcode suffix inputs are counterexamples to applying the
 # full-parent theorem at a bare entry; they are not callers/Native paths.
 for pointer in(0x6001,0x601C,0x601F):
  m,r=fixture(rom,0xBFEC,field=0);m[0x1A]=pointer&255;m[0x1B]=pointer>>8;m[pointer]=73;r['pc']=0xBFEC;c=MPU(memory=m)
  for k,v in r.items():setattr(c,k,v)
  c.step();assert c.a==73 and c.pc==0xBFEE
  bare.append(dict(pointer=pointer,Y=0,logical_address=pointer,original_instructions=1,comparison='explicit_bare_access_counterexample_prefix',full_parent_contract_covered=False))
 check('all256 rawcity complete constructor prefixes',len(prefixes)==256)
 check('all256 rawcities five rounds two RNG cursor complete parents',len(parents)==2560)
 check('all7 parentselected sites actually executed',{o['cpu']for r in parents for o in r['selected_accesses']}=={p for b,p in model.TARGETS})
 check('allrawY helpers preserve typed pointer and X with original savedY',len(helpers)==3072)
 check('bare selected entry can read allthree representative cityaux addresses',len(bare)==3 and all(r['logical_address']in base.AUX for r in bare))
 prior={(r['physical_bank'],r['cpu']):r for r in json.loads((ROOT/'analysis/phase26/fields-static/all-indirect-accesses.json').read_text())['accesses']}
 for key,row in canonical.items():
  p=row['address_contract']
  if p:assert model.old.old.old.old.old.auxiliary_intersection(p)==p['possible_auxiliary_effective_addresses']
  if key not in model.TARGETS:assert row['classification']==prior[key]['classification']and p==prior[key]['address_contract']
 check('only7 selected authority rows change and all1526 intersections recomputed',{k for k,r in canonical.items()if r['newly_proved_disjoint']}==set(model.TARGETS))
 state=base.State();s=state
 for pc in(0xBF1B,0xBF1E,0xBF21,0xBF24):s=e.transfer((8,pc),s)
 check('copy entry without current fullpair cannot manufacture1A',0x1A not in s.pairs)
 state=base.State();state.pairs[0]=base.Pair(frozenset((0x6080,)));s=state
 for pc in(0xBF1B,0xBF1E,0xBF21,0xBF24):s=e.transfer((8,pc),s)
 check('complete current pair installs exactlysame wholepointer',s.pairs[0x1A].addresses==frozenset((0x6080,)))
 state=base.State();state.pairs[0]=base.Pair(frozenset((0x6080,)));s=e.transfer((8,0xBF24),state)
 check('bypassed lowhalf cannot install1A',0x1A not in s.pairs)
 for target in model.HELPERS:
  state=base.State();state.pairs[0x1A]=base.Pair(frozenset((0x001A,)));out=e.apply_call(state,target,(8,0xBF34));assert (out.pairs.get(0x1A)==state.pairs[0x1A] if target==(8,0xBFEC) else 0x1A not in out.pairs)
 check('bare aliaspointer receives no new scaling passthrough theorem; readonly BFEC retains generic preservation',True)
 check('full parent Y scopes finite and byte wrapped',all(set(canonical[8,pc]['Y_values'])==ys for pc,ys in PARENT_Y.items()))
 check('tailJMP does not add a callerframe',proof['tail_adds_new_caller_frame']is False and rom[base.original(8,0xBF9B):base.original(8,0xBF9E)]==bytes.fromhex('4C9EBF'))
 check('prior named arithmetic is not recredited as first semantic recovery',proof['new_semantic_first_recovery']is False)
 check('official auxiliary names stay unknown',all(v is None for v in json.loads((OUT/'analysis-summary.json').read_text())['official_target_field_names'].values()))
 # Address domain includes potential mapper writes for raw helper offsets.
 addressonly=[dict(pointer=p,Y=y,logical_address=(p+y)&65535,original_instructions_executed=0)for p in model.CITY_WORDS for y in range(256)if (p+y)&65535>=0x8000]
 check('typed rawhelper address theorem retains mapper boundary',bool(addressonly)and max(r['logical_address']for r in addressonly)==0x80DF)
 rawcount=0
 def walk(x):
  nonlocal rawcount
  if isinstance(x,dict):
   pc=x.get('cpu',x.get('cpu_start',x.get('cpu_address')))
   if pc is not None and all(k in x for k in('physical_bank','rom_offset','raw_hex')):
    raw=bytes.fromhex(x['raw_hex']);off=base.original(x['physical_bank'],pc);assert off==x['rom_offset']and rom[off:off+len(raw)]==raw;rawcount+=1
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 for p in OUT.glob('*.json'):
  if p.name not in('verification.json','evidence.json'):walk(json.loads(p.read_text()))
 check('all nested original bytes and offsets verified',rawcount>0)
 pins={str(p.relative_to(ROOT)):sha(p)for p in(ROOT/'source/recovered').glob('*.py')}
 for module in tuple(sys.modules.values()):
  p=Path(getattr(module,'__file__','')or'/nonexistent')
  if p.is_file()and p.is_relative_to(ROOT/'scripts'):pins[str(p.relative_to(ROOT))]=sha(p)
 pins[str(Path(__file__).relative_to(ROOT))]=sha(__file__);artifacts={str(p.relative_to(ROOT)):sha(p)for p in OUT.glob('*.json')if p.name not in('verification.json','evidence.json')};summary=json.loads((OUT/'analysis-summary.json').read_text());counts=dict(actual_caller_RTS=len(parents)+len(helpers),constructor_prefix=len(prefixes),bare_access_counterexample_prefix=len(bare))
 (OUT/'README.md').write_text(f'''# G106完整指针与索引生命周期合同

稳定1526个原间址位置，本轮只改变G106七处权威逻辑访问分类：BF74/BFA0/BFA6/BFDF/BFE9/BFEC/BFF2。阶段26为1191不交、81可能、254未知，阶段27为1198不交、81可能、247未知；候选335→328。没有把裸入口或未知中断环境排除，也没有重新扫描其他组来增加本轮数。正式城市辅助字段名称仍未知。

BF0A原0514==0分支在F2AF正常返回后，把当前完整00/01复制到1A/B。模型要求BF1B开始的must-builder仍活跃且BF24当前00完整typed；低半旁路、部分写与join不恢复旧代指针。只有此完整父链的Y域是有限字段：BF74=11，BFA0=2/4/6/8/14，BFA6=3/5/7/9/15，BFDF=2/4/6/8/11/14，BFE9=3/5/7/9/15，BFEC=2/4，BFF2=3/5。rawcity0..255保持6000+32×byte，不把30..255叫合法城市。

BF9E/BFB3保存原Y到真实栈，EBE9/EA7C全原闭包无stack操作、无X改写且写域低于1A；typed1A域的全部rawY store EA是6000..80DF，不会写ZP/内部RAM镜像/栈，因此normal/no-interrupt时1A保持。返回Y为原11则11、否则(rawY+1)&FF；BFEC只读，返回Y=(rawY+1)&FF。裸BFEC的旧通用readonly保存不是新增typed写安全合同。8000..80DF潜在mapper地址只列地址域，执行0条，不声称硬件无副作用。

原CPU独立合同共{sum(counts.values())}例：完整RTS {counts['actual_caller_RTS']}（2560完整BF0A父caller+3072 typedpointer/rawY helper）、256构造前缀、3裸单指令反例前缀，另{len(checks)}模型检查；Source案例0。裸6001/601C/601F可以直接读辅助字节；typedhelper的rawY也可直接写辅助偏移，不能把完整父链无命中扩成整个函数/ROM未用。Source全RAM差分和10个被动原机callee另计，不重复为静态案例。

logical-vs-dummy-bus-contracts单列表。LDA额外未修正页读取只在crosspage时存在，STA无条件有其dummy读取。这里py65只逻辑内存访问，不产生dummy周期；Native另外实捕11个STA dummy。构造与裸输入是明示CPU夹具，不伪称自然菜单可达，无新增IRQ/NMI、ack、ready。A006/BAB3完整父controller和ECEE依赖未由这些合同闭合。

复现：.venv-trace/bin/python scripts/analyze_unknown_pointer_phase27.py ROM；.venv-trace/bin/python scripts/verify_unknown_pointer_phase27.py ROM。仅写新phase27。
''')
 result=dict(schema='phase27-original-resource-pointer-contract-validation-v1',status='passed',failed_count=0,ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,original_contract_CPU_cases=sum(counts.values()),counts=counts,actual_caller_RTS_CPU_cases=counts['actual_caller_RTS'],constructor_prefix_CPU_cases=counts['constructor_prefix'],bare_access_counterexample_prefix_CPU_cases=len(bare),model_guard_check_count=len(checks),model_checks=checks,constructor_prefix_checks=prefixes,parent_caller_checks=parents,raw_Y_helper_checks=helpers,bare_counterexamples=bare,raw_mapper_address_only_examples=addressonly,address_only_examples_added_CPU_cases=0,source_and_validator_sha256=pins,artifact_sha256=artifacts,original_nested_byte_ranges_verified=rawcount,executed_instruction_positions=[dict(physical_bank=b,cpu=pc,count=n)for(b,pc),n in sorted(visits.items())],remaining_access_count=summary['remaining_access_count'],all_indirect_classification_counts=summary['all_indirect_classification_counts'],newly_proved_disjoint_all_count=summary['newly_proved_disjoint_all_count'],limits=proof['limits']+['Source cases0. OriginalCPU controlled constructor/helper/parent contracts are not original Native frames.','Full parent controls field Y, while bare typed/rawY helpers can access auxiliary offsets; neither is a natural eligibility theorem.','Extra dummy metadata is an address rule; py65 does not emit dummy cycles. Rawmapper-address examples execute zero instructions.'])
 model.save('verification.json',result);model.save('evidence.json',dict(schema='phase27-G106-static-CPU-contract-evidence-v1',**{k:result[k]for k in('status','ROM_sha256','source_CPU_cases','original_contract_CPU_cases','counts','model_guard_check_count','source_and_validator_sha256','remaining_access_count','all_indirect_classification_counts','newly_proved_disjoint_all_count','limits')},artifact_sha256=artifacts|{'analysis/phase27/fields-static/verification.json':sha(OUT/'verification.json')}));print(json.dumps({k:result[k]for k in('status','original_contract_CPU_cases','counts','model_guard_check_count','remaining_access_count')}))
if __name__=='__main__':main()
