# 阶段十八：城市辅助字节、真实补兵与访问合同

本阶段确认了城市+1会影响原内政AI的实际补兵资格，完成有界控制图修正和逐候选访问合同，并加入可读补兵源码与独立主循环整合入口。**城市+1单字节的正式名称及+28..31四字节的正式名称仍不能确认**；没有把它们命名为资源、扩展名册、unused或padding。

## 可以确认的城市字段行为

| 偏移 | 本阶段证据 | 源码命名与限制 |
| --- | --- | --- |
| +1 | physical10:BD95设Y1，BD97读取真正城市基址+1，BD9D读取+2；原比较`LE16(city+1)>=300`。D105确实建立6000+32×city，而非移位指针。 | `raw_byte1`；暴露`overlapping_AI_threshold_word`，不声称单字节有正式名称。 |
| +2..3 | 已知真正金币LE16位于+2/+3，因此上述比较重叠到金币低字节。 | 保留偏移交叠；阈值300是资格门，不是统一300金币费用。 |
| +17..26 | 真正有界十槽武将名单；完整十人名单可以不含FF。 | 继承已有合法容量合同；本阶段补兵会扫全部十槽、跳过FF hole。 |
| +28..31 | 本阶段仍未建立专用字段消费者；记录整体复制/清除和显式无界扫描可能访问这些地址。 | `raw_tail28_31`，正式名称为空；局部菜单对照未见影响，不能推出全ROM无用途。 |

## 原模拟器实际对照

AI两组使用同一自然全年回放frame34623母档，原calendar[89,6]为**189年7月**，request本来就是0，城4首槽为武将167。共同只准备三字节：金币9504→257两字节、167兵1000→900的低字节；保留天然预备兵9499。目标组额外将城市+1由0改44，共四字节。没有改RNG、策略权重、request、pointer、ready、结果、状态位或手柄控制器。

| 原核组 | 交叠word | 原补兵事件 | 整个原请求结束 |
| --- | --- | --- | --- |
| +1=0 | 0 + 1×256 = 256 | 未补兵；167保持900，预备兵9499 | 第26帧requestFF；金币229，预算3。 |
| +1=44 | 44 + 1×256 = 300 | 第20帧167兵900→1000、预备兵9499→9399；当时金币仍257、预算28 | 第27帧requestFF；金币239，预算1。 |

实际补兵事件确认阈值行为。后续原策略和消耗可以不同，因此原核最终金币229/239、预算3/1，与独立CPU“两次main更新”金币237、预算10/8分开记录，不能合成一条内部trace。

城市菜单三组分别为自然基线、仅+1=44、仅尾部四字节12/34/56/78(hex)。各2220帧沿用冻结原菜单／武将选择／取消输入。逐帧RGB、PCM、整个2KiB RAM、观察到的归属、十槽名单、金币、预备兵与武将记录相同；SRAM和完整serialized state保留准备差异。此结论仅适用于这一菜单周期。

正式原核五组：6713首跑帧、13426双跑帧，113检查点，547非空产物全文双跑一致；5份原48kHz双声道16bit WAV。共12个公开准备字节，5次自然母档导入、0继承准备、0ready或result注入。原核未安装恢复源码；原核API不提供CPU PC/寄存器内部trace。

[全部原核证据](runtime/evidence.json) · [逐组对照](runtime/cohort-comparison.json) · [原核说明](runtime/README.md)

## 剩余访问逐条跟踪

旧阶段589条候选全部保留原bank、PC、opcode、原bytes、ZP指针、Y域、指针生产者和包含它的原过程/调用点。新的摘要针对完整256个ZP字节，区分未知store、RAM mirror(0000/0800/1000/1800)和可证明不写ZP的store；不假定raw16君主表都指向合法七个君主，也不假定低/高指针字节相关。

当前分类：153条可证明有效地址域与目标辅助字节不相交，140条有界地址域仍可能交叠，296条指针或索引合同仍未知。后两类都不是已确认消费者。完整图共有1526处间接访问，较旧图1481新增45处，另在目录逐项列出；不把旧589当完整ROM全集。新增45处中19处可排除、8处地址域仍交叠、18处未知。完整1526分类为621不相交、504仍交叠、401未知；其中443处旧非候选访问在本次更保守的宽域里没有重新证明不相交，需参考原局部合同，不当作新增实际消费者。八轮属于有限精化，不宣称整个抽象系统已求到固定点。

D304在首个FF前返回，Y域17..27、A/X为前缀人数0..10；不能当恒定Y27的摘要。此次还保留各已知callee的may-write闭包和未知上下文的显式障碍。

[逐条访问合同](fields-static/access-contracts.json) · [摘要](fields-static/analysis-summary.json) · [callee写域](fields-static/call-effect-summaries.json) · [不改ZP的store证据](fields-static/pointer-preserving-store-proofs.json)

## 控制图数据／代码边界修正

新层校验102个内联有界跳转表和两个全局表，解析旧99处表调用障碍。10:A039和10:A1BC的D494调用后是3字表；旧图错误跟随其普通fallthrough，其中A1BF的C5 A1曾被当成CMP指令，实际是目标A1C5的低／高字节。旧证据保持原文件，新层明确删除这一误解码位置，新增787个原指令位置，总48754。

775个独立原CPU检查从明确寄存器和零RAM/SRAM fixture执行真实JSR/dispatcher，到原表目标停止，验证目标、Y/X/SP和bytes；这是**跳转目标边界**，不是callee RTS或恢复源码对照。剩余4处dispatcher本体需要实际returnword/far上下文，54处fixed-body banked调用需要实际mapper；raw越界selector不在合同内。

[新控制合同](control/control-contracts.json) · [新指令图](control/instruction-atlas.json) · [775原CPU目标检查](control/verification.json)

## 可读源码与主循环整合

新增[city_auxiliary_services.py](../../source/recovered/city_auxiliary_services.py)：具名B49C城市分配流程和BD7A补兵流程，保留两轮名册调配、原拒绝采样、首将评分100／其余武力评分、后出现的同分候选胜出、十槽FF hole、兵数低10位判断、补写完整03E8、预备兵缺额补买与预算非局部返回。无候选时复用原BEC7发展尾；sample<10按原B5FC次级策略继续。付款失败被原caller忽略、预备兵恰等需要仍买一块等边界按原行为保留，不擅自修游戏逻辑。

新增[city_auxiliary_integration.py](../../source/recovered/city_auxiliary_integration.py)：`CityAuxiliaryGameEngine`继承冻结GameEngine，提供`city_auxiliary_services()`和`city_auxiliary_record(city_id)`，其coordinator接管真实physical10/11已声明入口。使用现有`readable_campaign(registers)`、main/NMI/IRQ API，保留独立pending owner和真实caller PC/SP。旧phase1..17的GameEngine、SceneCoordinator与模块不改。

| 验证种类 | 完成范围 | 计数 |
| --- | --- | --- |
| 新服务独立源码差分 | 全部2048B RAM、8192B SRAM、A/X/Y/P/SP/PC、ordered IO、banks、N163 | 192例 = 191实际caller RTS + 1缺E8AA服务的严格前缀；9guards。 |
| 新主循环组合 | 原E066起点，真实callee调用、两次main、两次NMI与各10次IRQ软件序列 | 2序列／3guards；完成E066/RTI边界，不计作2个RTS。 |
| 原内联表控制合同 | 独立原CPU到原dispatcher目标 | 775目标边界，单列。 |
| 原模拟器 | Nestopia自己的时序、原RGB/PCM与内存 | 5组6713首跑帧，以上CPU病例不是原帧数。 |

新源码739个原指令位置中，192例动态执行267个位置，另472个位置仅有静态byte校验，不能声称全部策略路径已动态验证。生产源码CPU／IR fallback均为0。原CPU追踪用于独立验证，明确寄存器／中断输入不等于原核内部trace。旧phase17冻结回执、源码依赖和v17 ZIP保持SHA不变。

[服务回执](services/validation.json) · [组合回执](source-integration.json) · [可交互证据页](index.html) · [总审计](verification.json)

## 可复现入口

```sh
python3 scripts/analyze_city_control_reachability.py ROM.nes
.venv-trace/bin/python scripts/verify_city_control_reachability.py ROM.nes
python3 scripts/analyze_city_auxiliary_accesses.py ROM.nes
.venv-trace/bin/python scripts/verify_city_auxiliary_services.py ROM.nes
.venv-trace/bin/python scripts/verify_phase18_integration.py ROM.nes
python3 scripts/capture_city_auxiliary_fields.py ROM.nes --repeat
python3 scripts/build_phase18_browser.py
python3 scripts/verify_phase18.py ROM.nes
python3 scripts/package_phase18_results.py
```

运行环境、原核文件与py65验证环境均需本地安装；发布包包含证据／恢复源码／重建ROM，不包含toolchain或venv。捕获脚本要求新的空目录；正式已冻结结果不要覆盖。浏览器验收回执来自CUA实际交互，证据页仅阅读已冻结数据。
