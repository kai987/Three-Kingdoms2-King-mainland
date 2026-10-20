#!/usr/bin/env python3
"""Compose phase20's report without changing historical evidence."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase20'
def read(p):return json.loads(Path(p).read_text())
def main():
 static=read(OUT/'fields-static/analysis-summary.json');service=read(OUT/'services/validation.json')
 runtime=read(OUT/'runtime/validation.json');qa=read(OUT/'browser-validation.json')
 counts=static['all_indirect_classification_counts'];left=static['remaining_access_count']
 assert service['original_CPU_parent_cases']==625 and runtime['original_F8_observed']
 text=f'''# 阶段二十：原机F8完整交涉与具名源码

**原Nestopia已真正产生F8，并完整验证玩家接受、拒绝、结算和AI续行。** 城市+1及+28..31的正式名称仍未取得足够证据；本轮进一步收紧了访问合同，不能宣称整个ROM已经逆向完成。

[交互证据页](index.html) · [机器审计](verification.json) · [原机流程](runtime/README.md) · [上一阶段](../phase19/index.html) · [v20整包](../../build/三国志2超级版-逆向分析-v20.zip)

## 城市+1和尾部四字节

正式名称继续为null，保留原偏移。已知原补兵选择读取`city[1] | (city[2]<<8)`并与300比较；正常金币是`city[2] | (city[3]<<8)`。两者交叠，不足以给city+1命名。+28..31尚未找到足以建立独立游戏含义的专用读写链。

新增完整字指针、同索引ROM字表、全返回路径callee合同及初始化bulk生产者分析。在冻结的48,754个指令位置中，全部1,526条间接访问现分为：

| 分类 | 条数 |
| --- | ---: |
| 在声明合同内与目标字段不相交 | {counts['proved_disjoint_auxiliary_address_domain']} |
| 仍可能覆盖目标字段 | {counts['possible_city_auxiliary_alias']} |
| 指针／索引上下文仍未知 | {counts['unresolved_pointer_or_index_contract']} |

上阶段401条剩余访问降至**{left}条**，新增排除{static['newly_proved_disjoint_all_count']}条。沿用旧窄域证明的访问保留原证明来源及SHA；本轮更宽候选域另列，不能当作“不相交”分类依据。可能访问、bulk覆盖和专用字段含义分别标记；此清单不是全ROM全部可达指令的证明，新具名服务原字节另有257位置目录。

原初始化先清整个6000..6FFF，继而从bank16 $8C00复制960B到6000..63BF，即30条完整城市记录；因此这些字节确实经过bulk初始化／整记录模板复制。初值0不构成“保留／未使用／padding”的证据。原武将模板另复制2880B到63C0..6EFF，与城市辅助字段不相交。

还识别出一个必须保守保留的上下文：11:C71A循环中的固定银行E89A调用会用随机游标重写X，随后INX/CPX #ED不是一个独立的固定237次计数。没有用这个错误边界强行排除潜在别名。

[逐项合同与模型边界](fields-static/README.md) · [全部访问](fields-static/all-indirect-accesses.json) · [剩余访问](fields-static/remaining-accesses.json) · [证明验证](fields-static/verification.json)

## 原模拟器F8完整流程

原ROM SHA256 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`，原Nestopia核心SHA256 `924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a`。按原提取块重建的ROM与原文件逐字节一致；这不是将恢复Python源码重新编译成NES。

两案均从原标题冷启动：选择袁紹，正常占领中立城0使城市3→4，两次0数量征兵耗卡，第二次分配结束前无键等待73帧再普通确认。73帧来自有限普通输入相位探索；正式回放重新冷启动，**不导入探索存档、不写随机数、策略权重、请求、回复、ready或PC**。

| 流程 | 首跑帧 | 检查点 | 核心数据写入／存档导入 |
| --- | ---: | ---: | --- |
| 接受 | 11,589 | 393 | 0／0 |
| 拒绝 | 11,645 | 394 | 0／0 |

两案各fresh-process复跑，首跑23,234帧、双跑46,468帧；787检查点，3,180份非空文件精确一致，含24份正式JSON。每帧保留RGB、PCM、RAM、SRAM、完整原state hash与观察字段；检查点保存原256×240图、2K RAM、8K SRAM和未裁剪原state。两份48kHz双声道WAV合计18,556,510个sample pair。

实际F8在10500帧产生：刘备侧ruler4／君主222，目标人类ruler1／君主8，使者38，粮食报价及提交缓存114。资格路径是己方1城、目标4城且有两个邻方，外交检查通过；这些资格此前已满足，未出现请求的旧窗口主要卡在多层随机策略选择。

接受时原UI选择0，10966帧原回复0，city2粮9999→9885、city4粮9999→10113；双方packed外交为ruler1 `[00,00,0A,00]`、ruler4 `[A0,00,00,00]`。10969帧原请求回FF，11036帧收粮城后来cap9999，11589帧返回玩家地图。

拒绝时通过原Right选择1，11022帧原回复1；回复当帧双方外交仍0、城2／4粮仍9999，11023帧请求回FF，11645帧返回玩家地图。后续AI其他资源变化不归因于此次交涉。

[接受原对话](runtime/natural-F8-accept/F8-original-choice-accept.png) · [拒绝原对话](runtime/natural-F8-reject/F8-original-choice-reject.png) · [输入与逐帧记录](runtime/evidence.json) · [完整复跑回执](runtime/validation.json)

## 可读游戏源码

新增 [negotiation_services.py](../../source/recovered/negotiation_services.py) 将十个辅助入口写成具名业务方法：使者选择、邻国统计、君主所在城、城市／名册计数、完整报价检查、提交缓存扣加与双方盟约写入。新增 [negotiation_integration.py](../../source/recovered/negotiation_integration.py) 接入冻结的campaign/main/NMI/IRQ/UI协调器；请求等待保留真实caller PC/SP与owner，后续仅由原消费者产生回复。

保留原边界：金模式0／非0粮、FF名册空洞与前缀统计的区别、同值选后者、完整报价与低byte提交缓存的区别、资源加法后暂超9999、外交nibble常量10。没有为了让流程“更合理”修改原游戏整数行为。

验证按来源分列：

| 验证 | 父case／序列 | 结果 |
| --- | ---: | --- |
| 受控原CPU边界矩阵 | 625 | 600 RTS、24真实等待、1严格缺依赖前缀 |
| 真实JSR上下文源码差分 | 8 | 7 RTS、1真实等待，未准备入口／返回栈 |
| 受控原UI消费者序列 | 4 | F8接受／拒绝、F9／FA通知均由原消费者回复后返回 |
| 真实Native F8上下文源码续行 | 2 | 接受／拒绝各85次显式NMI、425次IRQ后回原E188 |

每项源码差分比较完整2KiB RAM（含栈）、8KiB SRAM、AXYP/SP/PC、顺序IO、4页实际PRG及N163；生产源码原CPU回调0、IR解释false。上述639父比较含613 RTS、25等待和1前缀，不能全称639完整流程。新增原字节域257位置／549B均有动态命中，也不等于全输入／全硬件覆盖。

另有6个独立原CPU保存上下文诊断（79,933条原指令），用于解释选择条件，不增加源码case数。四个前序均真实生成F8，8K SRAM与原机10500帧一致；RAM分别差37／17／33／32字节，寄存器亦不同。因为没有安排原帧内新中断，明确不能扩大成整个Native时序或CPU状态相同。原机REG是边界快照，独立CPU轨迹不是原核内部trace。

[源码与API说明](services/README.md) · [受控矩阵](services/validation.json) · [真实调用差分](cpu/actual-caller-source-validation.json) · [真实F8续行](cpu/native-context-source-sequences.json) · [原CPU资格诊断](cpu/README.md)

## 证据页与复现

本地入口 `http://127.0.0.1:8765/analysis/phase20/index.html`。CUA验收原图、两案逐帧／检查点字段、完整源码、筛选／搜索／翻页与原WAV播放，控制台错误／警告为0；使用默认桌面视口{qa['viewport']['DOM_width']}×{qa['viewport']['DOM_height']}，未测试移动端。具体逐项结果以[浏览器回执](browser-validation.json)为准。

```sh
.venv-trace/bin/python scripts/verify_negotiation_services.py ROM.nes
.venv-trace/bin/python scripts/verify_phase20_actual_callers.py ROM.nes
.venv-trace/bin/python scripts/verify_phase20_negotiation_interleave.py ROM.nes
.venv-trace/bin/python scripts/verify_phase20_native_negotiation.py ROM.nes
python3 scripts/capture_f8_native_flows.py ROM.nes --case all --repeat
python3 scripts/verify_phase20.py ROM.nes
```

原机复跑会写本轮产物，冻结交付后复现请先复制目录。沿用REA原材料并新增原字节／原核证据，没有修改tools/rea。阶段1..19产物与v19 ZIP逐hash保留；v20在终验后打包。

仍待完成：城市辅助字段正式含义、{left}条可能／未知访问的进一步上下文、其他未动态验证分支与全ROM剩余控制形式及硬件边界。**本阶段F8已验证，不等于整个游戏已完全还原。**

![原机交涉证据页](browser-proof.jpg)
'''
 (OUT/'README.md').write_text(text)
 p=OUT/'investigation-checklist.json';check=read(p)
 statuses={'city-official-labels':'unconfirmed_no_official_label_inferred','remaining-accesses':f'refined_401_to_{left}_conservative_contracts_verified','Native-F8':'passed_original_core_full_cold_accept_reject_double_replay','readable-source':'passed_625_controlled_8_actual_callers_6_consumer_parent_sequences'}
 for q in check['questions']:q['status']=statuses[q['id']]
 p.write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(report='analysis/phase20/README.md',remaining_accesses=left,original_F8_verified=True)))
if __name__=='__main__':main()
