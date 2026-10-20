#!/usr/bin/env python3
"""Static follow-on premise from saved first returns; no Source/CPU run."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp07-palette-packet-consumer';RUN=OUT/'run-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 scope=json.loads((OUT/'family-scope.json').read_text());points=[json.loads(l)for l in(RUN/'points.jsonl').open()];buf=(RUN/'CPU-snapshots.bin').read_bytes();examples=[]
 for p in points:
  if '/call1-'not in p['label']or not(p['label'].endswith('advance1-returned')or p['label'].endswith('real-resume-return')):continue
  ram=buf[p['offset']:p['offset']+2048];assert ram[0x87:0x8B]==bytes.fromhex('5c7996b3')
  assert p['CPU']['registers']['pc']==0xF8B8 and ram[0x7D:0x7F]==bytes((0,5))
  examples.append(dict(point=p['label'],snapshot_offset=p['offset'],actual_87_88_89_8A=[ram[a]for a in range(0x87,0x8B)],actual_7D_7E=[ram[0x7D],ram[0x7E]]))
 assert len(examples)==5
 rom=Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==scope['ROM_SHA256']
 start=16+31*8192+(0xF8B8&8191);raw=rom[start:start+9];assert raw==bytes.fromhex('2006f2200bfb2067ec')
 source=ROOT/'source/recovered/battle_nmi_services.py';a=json.loads((OUT/'acceptance.json').read_text());assert sha(source)==a['implementation_pins']['source/recovered/battle_nmi_services.py']
 result=dict(schema='WP07-unexecuted-continuation-static-premise-v1',actual_first_returns=examples,
  next_original_calls=[dict(PC=0xF8B8,target=0xF206),dict(PC=0xF8BB,target=0xFB0B),dict(PC=0xF8BE,target=0xEC67)],original_bytes=raw.hex(),
  F206_role='Existing CHR configuration:8 register writes;notpalette_fade anddoesnot reassert7D',
  additional_status_gate=dict(PC=0xFB22,instruction='BIT2002/BVS',condition='Repeatwhilebit6 set',input_contract_declared_in_this_package=False,return_assumed=False),
  palette_write_stack_premise='EC67 also writes active0100..011F;SP00 frame alias and actualreturn remain unexecuted andmustbe checked,notassumed.',
  Source_method='BattleNMIServices.palette_fade',Source_sha256=sha(source),
  conditional_static_derivation='If actual continuation reaches EC67 with these fields unchanged:8A B3->B2 negative, reload8A=96;7D=1;87 nonzero makes88 79->7A,>=4 sets87=FF. Then existing palette loop runs.',
  predicted_fields_before_palette_loop={'87':0xFF,'88':0x7A,'89':0x96,'8A':0x96,'7D':1},
  actual_continuation_executed=False,Source_CPU_Native_executions=0,consequence='Controlled second entry intentionally bypasses this unexecuted continuation. Natural nextEE53 is not proved to choosebit2;palette priority may be reasserted.',
  required_next_scope='Real F8B8->F206->FB0B->EC67 scheduling with its explicit hardware inputs and incoming context, before any natural nextconsumer claim.')
 target=OUT/'continuation-preconditions.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 p=OUT/'README.md';text=p.read_text();marker='packet A132/A13A/A140/A146是全账本1405..1408'
 addition='''首个palette返回的实际87..8A仍为 `5C 79 96 B3`。真实F8B8的下一条是F206（已有CHR配置，发8个CHR写），随后FB0B在FB22的BIT2002/BVS按bit6等待，需要本包未声明的新位置有限样本，不能预言它必定返回。只有FB0B实际返回后才到EC67；本包第二次直接重入F8B5，跳过了这些未执行的continuation。仅按冻结Source静态推导：若后续到达EC67且这些字段未变，8A从B3减为B2后为负，便重装96、重新置7D=1，88变7A并使87变FF，再执行palette更新。F206本身不会重新置7D，palette_fade属于EC67。因此自然下次EE53不保证选择bit2；该调度必须另包验证。EC67还会写活动palette区，SP00的frame别名与实际返回同样不能预设成功。本条是静态剩余前提，未执行或增加测试信用。见[continuation前提](continuation-preconditions.json)。

'''
 assert marker in text and addition not in text;p.write_text(text.replace(marker,addition+marker))
 p=OUT/'work-package-delta.json';delta=json.loads(p.read_text());delta['WP08']['specific_unexecuted_scheduling_premise']=result['consequence'];delta['WP08']['continuation_static_evidence']='continuation-preconditions.json';p.write_text(json.dumps(delta,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(status='static_follow_on_premise_recorded',actual_first_returns=5,Source_CPU_Native_executions=0)))
if __name__=='__main__':main()
