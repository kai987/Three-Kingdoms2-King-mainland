#!/usr/bin/env python3
"""Pin readable secondary source, original bytes, coverage and reply provenance.

This is a read-only originalROM analyzer. It neither generates production code
nor turns unexecuted instructions into dynamic validation claims.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import instruction
from source.recovered.domestic_secondary_services import DomesticSecondaryServices,ROM_SHA256
OUT=ROOT/'analysis/phase19/services';CPU=ROOT/'analysis/phase19/cpu'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def pos(rows):return{(x['physical_bank'],x['cpu_address'])for x in rows}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 oldcat=json.loads((ROOT/'analysis/phase18/services/static-catalog.json').read_text());oldreceipt=json.loads((ROOT/'analysis/phase18/services/validation.json').read_text());receipt=json.loads((OUT/'validation.json').read_text());seq=json.loads((CPU/'consumer-sequences.json').read_text());discovery=json.loads((CPU/'actual-callers/discovery.json').read_text())
 assert receipt['status']==seq['status']=='passed'and not receipt['quick']
 inherited={ (x['bank'],x['pc']):x for x in oldcat['instructions']};body={k:x for k,x in inherited.items()if 0xB5FC<=x['pc']<0xBD7A}
 assert len(inherited)==739 and len(body)==523
 for(bank,pc),x in inherited.items():
  raw=bytes.fromhex(x['raw_hex']);assert x['file']==16+bank*8192+(pc&8191)and rom[x['file']:x['file']+len(raw)]==raw
 old=pos(oldreceipt['executed_instruction_positions']);matrix=pos(receipt['executed_instruction_positions']);consumer=pos(seq['executed_instruction_positions']);target=set(inherited);gap=target-old;now=matrix|consumer
 remain=sorted(target-old-now);assert len(gap)==472 and remain==[(10,0xBCDC)]
 ranges=[]
 for bank,pc,size,name in((10,0xBA81,12,'recruit_probability_3rows_4bytes_lastcell_unused'),(10,0xBCAB,3,'loyalty_probability_3difficultybytes')):
  offset=16+bank*8192+(pc&8191);raw=rom[offset:offset+size];ranges.append(dict(physical_bank=bank,cpu_address=pc,rom_offset=offset,size=size,name=name,raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
 catalog=dict(schema='phase19-domestic-secondary-byte-catalog-v1',rom_sha256=ROM_SHA256,physical_pair=[10,11],public_entries=list(DomesticSecondaryServices.PUBLIC_ENTRIES),local_wait_entries=list(DomesticSecondaryServices.LOCAL_ENTRIES),new_body_instruction_count=len(body),instructions=sorted(body.values(),key=lambda x:x['pc']),new_body_instruction_bytes_sha256=hashlib.sha256(bytes.fromhex(''.join(x['raw_hex']for _,x in sorted(body.items())))).hexdigest(),data_ranges=ranges,source_method_entries={'B5FC':'secondary_assignment_strategy','B619':'neighbor_alliance_offer','B6C5':'quote_alliance_offer','B78B':'await_alliance_reply','B98B':'recruit_low_loyalty_foreign_officer','BA07':'foreign_recruitment_probability','BA8D':'commit_foreign_recruitment','BB40':'await_recruitment_notice','BBB2':'reduce_foreign_officer_loyalty','BCAE':'commit_loyalty_reduction','BD36':'await_loyalty_notice'},reused_source='CityAuxiliaryServices/DomesticCooperationController shared pointer/math/neighbor/roster helpers and BEC7development, unchanged')
 dump(OUT/'static-catalog.json',catalog);lines=[]
 for(bank,pc),x in sorted(body.items()):
  _,text=instruction(rom,x['file'],pc);lines.append(f'{x["file"]:06X} b{bank:02d}:${pc:04X} {x["raw_hex"]:<14} {text}')
 for x in ranges:lines.append(f'{x["rom_offset"]:06X} b{x["physical_bank"]:02d}:${x["cpu_address"]:04X} {x["raw_hex"]} ; {x["name"]}')
 (OUT/'original.asm').write_text('\n'.join(lines)+'\n')
 clamp=inherited[10,0xBCDC];prior_select=[inherited[10,p]for p in(0xBC4C,0xBC4E,0xBC50,0xBC52,0xBCB3,0xBCC0,0xBCC2,0xBCC6,0xBCD7,0xBCDA,0xBCDC)]
 proof=dict(schema='phase19-unexecuted-clamp-valid-entry-bound-v1',physical_bank=10,CPU_PC=0xBCDC,rom_offset=clamp['file'],raw_hex=clamp['raw_hex'],not_dynamically_tested=True,entry_scope='Complete BBB2 body, valid byte-valued officer fields, no external mutation between selection and commit.',selected_target_loyalty_minimum=50,selected_target_loyalty_maximum=89,maximum_own_IQ_byte=255,maximum_division_quotient=255//20,maximum_original_random_increment=7,maximum_loyalty_reduction=255//20+7,integer_inequality='floor(255/20)+7 =19 <50 <= selected_target_loyalty; SBC cannot borrow.',consequence='BCDA BCS always takes BCDE under these preconditions; BCDC LDA0 is a retained defensive raw continuation branch.',not_claimed=['Not a claim that arbitrary PC entry or asynchronous external record mutation cannot reach this instruction.','No fabricated raw local-entry case is counted as normal eligible gameplay.'],original_gate_and_update_bytes=prior_select)
 dump(OUT/'unexecuted-clamp-proof.json',proof)
 coverage=dict(schema='phase19-old-phase18-gap-coverage-v1',target_previous_static_positions=739,previous_dynamic_positions_in_target=len(old&target),previous_unexecuted_positions=len(gap),new_secondary_static_positions=len(body),new_secondary_dynamic_matrix_positions=len(set(body)&matrix),new_secondary_dynamic_consumer_positions=len(set(body)&consumer),new_secondary_dynamic_union_positions=len(set(body)&now),matrix_dynamic_positions_in_previous_target=len(target&matrix),matrix_new_positions_in_previous_gap=len(gap&matrix),consumer_additional_positions_after_matrix=len((gap&consumer)-matrix),new_union_positions_in_previous_gap=len(gap&now),combined_previous_and_new_dynamic_positions=len(target&(old|now)),remaining_unexecuted_positions=[dict(physical_bank=b,cpu_address=pc,rom_offset=inherited[b,pc]['file'],raw_hex=inherited[b,pc]['raw_hex'],qualification='valid-entry integer bound; retained unexecuted')for b,pc in remain],previous_gap_positions=[dict(physical_bank=b,cpu_address=pc)for b,pc in sorted(gap)],newly_executed_previous_gap_positions=[dict(physical_bank=b,cpu_address=pc)for b,pc in sorted(gap&now)],limits=['Counts are explicit set intersections of original physical-bank/PC positions.','Instruction coverage is not complete path, inputspace, timing or Native gameplay verification.','Consumer positions count from four parent sequences, not from one test per interrupt.'])
 dump(OUT/'coverage.json',coverage)
 files=['source/recovered/domestic_secondary_services.py','source/recovered/city_auxiliary_services.py','source/recovered/domestic_cooperation_controller.py','source/recovered/domestic_secondary_integration.py','source/recovered/nestopia_context.py','source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py','scripts/verify_domestic_secondary_services.py','scripts/verify_domestic_secondary_interleave.py','scripts/trace_domestic_secondary_callers.py','scripts/analyze_domestic_secondary_services.py']
 artifacts=[OUT/'validation.json',OUT/'coverage.json',OUT/'static-catalog.json',OUT/'original.asm',OUT/'unexecuted-clamp-proof.json',CPU/'consumer-sequences.json',CPU/'actual-callers/discovery.json',ROOT/'analysis/phase18/services/static-catalog.json',ROOT/'analysis/phase18/services/validation.json']
 evidence=dict(schema='phase19-named-domestic-secondary-evidence-v1',status='passed',rom_sha256=ROM_SHA256,source_file=files[0],source_sha256={p:sha(ROOT/p)for p in files},production_original_CPU_callbacks=0,production_IR_interpretation=False,validation=dict(path=str((OUT/'validation.json').relative_to(ROOT)),sha256=sha(OUT/'validation.json'),rom_cpu_case_count=receipt['rom_cpu_case_count'],actual_caller_RTS_count=receipt['actual_caller_RTS_count'],original_loop_wait_count=receipt['original_loop_wait_count'],strict_prefix_count=receipt['strict_prefix_count'],source_guard_case_count=receipt['source_guard_case_count']),consumer_sequences=dict(path=str((CPU/'consumer-sequences.json').relative_to(ROOT)),sha256=sha(CPU/'consumer-sequences.json'),rom_cpu_sequence_count=seq['rom_cpu_sequence_count'],cases=[dict(case=x['case'],NMI=x['explicit_NMI_arrivals'],IRQ=x['explicit_IRQ_arrivals'],reply=x['actual_response']['value'])for x in seq['rows']],initial_inputs='Explicit controlled campaign/owner/controller and actual RTS-frame fixtures; no request prepared.',postentry_inputs='Only normal controller port bytes plus explicit NMI/IRQ arrivals; real software writes every request/reply/ready.',Native_video_frame_equivalence=False),coverage=coverage,actual_callers=dict(path=str((CPU/'actual-callers/discovery.json').relative_to(ROOT)),contexts_examined=discovery['contexts_examined'],entries=list(discovery['captured_original_callers']),source_comparisons=3,independent_original_prefixes_are_not_extra_source_cases=True,Native_internal_CPU_trace=False),waits=[dict(pc=0xB78B,generated_request=248,predicate='request!=F8',accepted_value=0,consumer='26C7E0->C9AE->CC89/CC8C->CD6F'),dict(pc=0xBB40,generated_request=250,predicate='request==0',mutation='roster move already committed',consumer='26C7E0->C93D->CBC3/CD6F'),dict(pc=0xBD36,generated_request=249,predicate='request==0',mutation='loyalty already reduced',consumer='26C7E0->C97D->CC26/CD6F')],semantics=dict(alliance='A thirdband offer from most-city neighbor; own packed diplomacybyte sum==0, >=3leaders, >=2foreign neighbors, targetcitycount>owncount+2, messenger!=leader. Exactcontroller3 local; allotherbytes requestF8.',offer_word_quirk='Check full042F/0430 quote4q or6q, but copy3A=042F and3B=0431zero; committed resource transfer uses only lowbyte. Proven quote316/474 versuscommit60/218.',recruit='Own shortest prefix city with<10slots; foreign lowest loyalty<70. Append firstFF, adjust targetloyalty, remove source, wholebyte owner7 if empty; no HP/status/residence/troops write. IQ+virtue ADC discarded before virtue/20 division in original.',loyalty='Foreign city prefix>=6, exactcontroller!=3; maxprefix tieslater. Candidate loyalty50..89 acrossall10slots. Chance includes clamped ownbestIQ-targetIQ +difficultybyte; reduction floor(ownIQ/20)+random1..7.',auxiliary='No new official city+1/tail28..31 names. Dedicated secondary accesses usecity0/2..5/17..26; shared helpers and proved address windows remain separately scoped.'),native_limit='Formal zero-write cold expansion/monthly window did not observe F8; CPUfixture consumer success must not be described as NativeF8 evidence.',artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in artifacts})
 dump(OUT/'evidence.json',evidence)
 (OUT/'README.md').write_text(f'''# 内政次级策略：具名源码、等待与真实消费者

[DomesticSecondaryServices](../../../source/recovered/domestic_secondary_services.py) 用具名直接 Python 替换上一轮复制控制形态的 B5FC 次级分支。新body锁定 physical10 的523个原指令位置；B49C两轮分配、BD7A补兵与共享指针/整数/RNG/邻接/名册 helper复用冻结源码。生产不运行原 CPU、IR或动态程序表。原 phase1..18 代码、回执和原核心证据保持冻结。

## 三个分支及作用顺序

B5FC调用E89A，取返回值低7位，拒绝>=90；0..29走BBB2降忠，30..59走B98B招揽，60..89走B619邻国资源交涉。主B49C的E8AA仍先拒绝>=50，只有0..9进入此B5FC；原始采样和cursor推进全部保留。

B619先选本势力非leader最高忠诚使者（平分后者），要求至少3个leader不为FF、本ruler四个外交byte的8bit和为0、至少两个其他owner邻居。它在邻居中选城最多者（平分后者），并要求目标城数严格大于本方城数+2。q=floor((目标城数×30+70)/10)，原随机选择金或粮，完整报价为4q/6q。原 affordability 用042F/0430完整word，但提交缓存3A取042F、3B却取始终为0的0431，因此实际资源转移截为低byte；24城边界原CPU已对照报价316/474、提交60/218，资金255会在fullword检查处失败。目标controller整个byte恰好3直接写双向外交nibble A并转资源，其余byte先发F8再等待回复，不能把low2==3当整个byte==3。

B98B选择本方prefix人数最少且小于10的城市（平分首个），再全外方名册选忠诚最低且<70的武将（平分首个）。成功后依次追加到目标首FF、重新计算忠诚、在原城删除并压缩名册；原城无prefix武将时将owner整个byte写7。随后才对非controller3方发FA通知。它不写武将HP、status、驻城byte5或兵数。概率中有原始 quirks：读取IQ并做IQ+徳的ADC后，该A被覆盖，除法实际只用先前21中存的徳；等级差按8bit符号处理，不改写为通常的有符号公式。

BBB2先找本势力最高IQ，然后选非本方且controller整个byte不等于3的最大prefix名册城市，必须至少6人（平分后城）。在其十个槽中收集忠诚50..89的候选，再原随机挑选。成功概率含max(0,本方最高IQ−目标IQ)+难度表byte，所有加法保留8bit。先把目标忠诚扣去 floor(本方最高IQ/20)+原随机1..7，再发F9通知。兵数高位、HP、status和驻城字段不因此重写。

## 等待保持同一 caller

F8在B78B等request!=F8，且只有回复0接受；F9/FA分别在BD36/BB40等request==0。`SecondaryRequestWait`保留原SP和同一个generator；resume重复观察，不写请求/ready/result或假RTS。缺fixed服务同样停在真实callee帧，非returned状态即使伪装PC/SP也不能通过。

真实城市消费者是NMI2的26C7E0：F8进入city9/phase16三级询问，F9/FA分别进入phase15/14通知。原文字消费者完成队列，原按键/菜单最终令CD6F把040C写回request；不是测试程序替它确认。四个长序列分别为接受0/拒绝1各85显式NMI+425IRQ，FA/F9通知各61NMI+305IRQ；每序列只计一个父case，最终恢复原暂停controller并RTS至真实caller E188。起始资格和地缘/controller是明确CPUfixture；这些事件不是视频帧时序，更不是Native F8实机记录。后续输入只有普通controller ports与显式中断，没有ready/ack注入。

## 验证及覆盖

正式矩阵 {receipt['rom_cpu_case_count']} 次原CPU对照：{receipt['actual_caller_RTS_count']} 实际caller RTS、{receipt['original_loop_wait_count']} 原循环等待、{receipt['strict_prefix_count']} 缺服务前缀；另 {receipt['source_guard_case_count']} 个源码guard。另四个消费者父序列单列，不重复加嵌套中断/callee准备数量。每个边界比较全部2048B RAM（含free-stack）、8192B SRAM、AXYP/SP/PC、有序IO、四PRG银行、N163全部128B/地址/自增。新phase19总线按官方原核心实现127→0回绕；旧冻结ServiceMemory的饱和行为不用于本轮比较。source CPUcallbacks=0。

真实 Native 保存格式现在可解出REG七字节、实际MAP/PRG/BNK与N63/SND/RAM；原CPU发现从这些真实捕获上下文开始，使用实际银行而非DE..E0影子。83个冻结母点的有界、无新增NMI/IRQ原CPU前序捕获了B5FC/B98B/BBB2三个真实callee入口（B5FC和B98B来自同一母点不同边界）；这些入口对应3次source比较，原prefix steps不额外计case。未捕获B619的自然入口，未把任意PC/修改RNG当自然发现。独立原CPU续行仍不是原核心内部逐指令trace，也不还原之后的硬件时钟。

以 phase18 static739 的物理bank/PC集合为固定目标：原动态267，旧缺口472；新矩阵补到其中{coverage['matrix_new_positions_in_previous_gap']}，四consumer再补{coverage['consumer_additional_positions_after_matrix']}，合计{coverage['new_union_positions_in_previous_gap']}。联合旧证据共738/739；剩BCDC LDA0没有动态覆盖。其正常入口界限是目标忠诚>=50、最大byte IQ255/20+7=19，故SBC不会借位，BCDA必走BCDE。保留该原始防御分支和字节证明，不用绕过资格的局部fixture冒充正常可达。指令位置覆盖不等于全部路径/输入空间/时序已验证。

城市+1与tail28..31在这里没有获得新的正式名称；原真正重叠门槛和其他访问仍按前轮明确合同记录。本轮正式原核心零写入扩城/月轮窗口未观察F8，不能用CPU受控成功淡化这个缺口。

## API与复现

```python
rules = DomesticSecondaryServices(memory, rom, services=readable_services)
rules.run_entry(0xB5FC, registers=actual_caller_registers)
rules(service_call)  # exactphysical10/11与PUBLIC入口
rules.resume()      # 原等待未得到真实reply则继续waiting
```

PUBLIC=A000/A00F/B49C/BD7A/B5FC/B619/B98B/BBB2；LOCAL只公开给明确局部CPU测试B78B/BB40/BD36。Root新增DomesticSecondaryGameEngine/SceneCoordinator路由和真实context factory，不改旧GameEngine。B5FC三个算法均直接具名函数，不在运行时读取program.json、opcode或PC字典。

```sh
.venv-trace/bin/python scripts/trace_domestic_secondary_callers.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_secondary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_secondary_interleave.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_domestic_secondary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原汇编](original.asm) · [原字节目录](static-catalog.json) · [完整矩阵](validation.json) · [覆盖交集](coverage.json) · [未覆盖界限](unexecuted-clamp-proof.json) · [四消费者交错](../cpu/consumer-sequences.json) · [实际caller](../cpu/actual-callers/discovery.json) · [原核心](../runtime/README.md) · [证据hash](evidence.json)
''')
 print(json.dumps(dict(status='passed',CPU=receipt['rom_cpu_case_count'],guards=receipt['source_guard_case_count'],consumer_parentcases=seq['rom_cpu_sequence_count'],static_new_body=523,new_oldgap=coverage['new_union_positions_in_previous_gap'],combined_dynamic=coverage['combined_previous_and_new_dynamic_positions'],remaining=remain,source_sha256=evidence['source_sha256'][files[0]])))
if __name__=='__main__':main()
