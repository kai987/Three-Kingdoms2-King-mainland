#!/usr/bin/env python3
"""Offline actual-read roles for raw windows; never executes Source or CPU."""
from pathlib import Path
import collections,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/wp03-ee07-phase1-producer'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 scope=json.loads((OUT/'family-scope.json').read_text());raw=json.loads((OUT/'raw345-executability-ledger.json').read_text())['windows']
 rows=[json.loads(line)for line in(OUT/'run-01/cases.jsonl').open()];reads=collections.defaultdict(list)
 for row in rows:
  source=[x for x in row['Source']['packet_events']if x['kind']=='payload_read'];cpu=[x for x in row['CPU_packet_events']if x['kind']=='payload_read']
  for left,right in zip(cpu,source,strict=True):
   assert all(left[k]==right[k]for k in('address','bank','value','Y'))
   offset=16+left['bank']*8192+(left['address']&8191)
   reads[offset].append(dict(case=row['key'],zero_based_step=row['step'],CPU=left,Source=right))
 relations=[];unique=set();count=0
 for index,row in enumerate(raw):
  if row['phase22_executability_category']!='unresolved_raw_window_no_proved_control_entry':continue
  start=row['rom_offset'];values=bytes.fromhex(row['raw_hex'])
  if not all(start+i in reads for i in range(len(values))):continue
  evidence=[]
  for i,v in enumerate(values):
   matches=reads[start+i];assert all(m['CPU']['value']==v for m in matches);unique.add(start+i);count+=1
   evidence.append(dict(window_byte=i,ROM_offset=start+i,value=v,actual_per_side_read_records=matches))
  relations.append(dict(raw_id=f'W:{scope["ROM_SHA256"]}:b{row["physical_bank"]:02d}:off{row["bank_offset"]:04X}:rom{start:06X}',raw_locator=f'/windows/{index}',raw_hex=row['raw_hex'],
    typed_consumer_id=scope['selected_typed_id'],role='Payload data read by actual BCBF; raw start opcode execution or alternate entry exclusion not proved',
    byte_evidence=evidence,existing_category=row['phase22_executability_category'],classification_change=False,shared_semantic_root=None))
 assert[x['raw_locator']for x in relations]==['/windows/136','/windows/137','/windows/138','/windows/139']
 assert count==12 and len(unique)==10
 save('raw-payload-consumer-evidence.json',dict(schema='wp03-phase1-actual-raw-payload-roles-v1',relations=relations,
  window_count=4,window_byte_relations=12,unique_ROM_bytes=10,overlap_note='windows138/139 overlap2 bytes;12 window-byte relations do not mean12 unique byte reads.',
  actual_case_records_sha256=sha(OUT/'run-01/cases.jsonl'),raw_ledger_sha256=sha(OUT/'raw345-executability-ledger.json'),
  classification_changes=0,whole_raw_window_opcode_execution_proven=False,semantic_root_merge=None,Source_CPU_Native_executions=0))
 p=OUT/'README.md';text=p.read_text();anchor='## 固定账本与封存'
 addition='''## raw228的实际payload消费者

动态记录确认本轮实际读取4个raw窗口：`/windows/136`（b16 off08E4）、137（off09E7）、138（off0A62）、139（off0A63）。在16次序列中分别位于零起算step3/Y36..38、step7/Y39..41、step9/Y34..36与Y35..37；对应可读case key是step-04、step-08、step-10。每个字节都同时保留实际CPU BCBF读取与Source方法/行号记录。

138/139重叠2字节，共12条window-byte关系、10个唯一ROM字节；不能重复算作12个独立字节。它们得到payload数据角色证据，不证明raw起点opcode已执行、也不排除其他入口；raw分类及共同语义根保持原样。见[逐字节消费者证据](raw-payload-consumer-evidence.json)。

'''
 assert anchor in text and '## raw228的实际payload消费者'not in text;p.write_text(text.replace(anchor,addition+anchor))
 print(json.dumps(dict(status='verified_actual_raw_data_roles',windows=4,window_byte_relations=12,unique_ROM_bytes=10,Source_CPU_Native_executions=0)))
if __name__=='__main__':main()
