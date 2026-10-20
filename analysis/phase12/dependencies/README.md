# 第十二轮：普通攻击的真实依赖调查

本目录先把已经冻结的普通攻击控制器与原CPU的调用协议拆开复查，再用不带原CPU回调的 `GameEngine.readable_scene_rules()` 检查纯源码的返回或明确依赖。它不是额外的整机帧、自然玩法或图像证明。

## 原调用清单

原只读 ROM SHA256 为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。输入来自阶段3普通攻击菜单的既有受控快照，保留其明示相邻敌方坐标准备；另外明确准备主态、phase、buttons、对象索引/数组、参与武将、fade、RNG、队列状态、NMI场景和真实caller栈。它们不是未经修改的自然场景。

11主态的58个合法phase乘buttons0/1/2，共174种输入；分别从真实NMI4包装 `$A000` 和直接控制体 `$A069` 调用，基础组348个入口执行。另对全部58phase追加buttons4/8/16/32/64/128/255，共812例；再单列participant menu phase1、0548=4/5、两入口的4例。总计1164个有界调用，不再扩展随机环境或大量不可达fixture。255是明示的8位按钮边界，不宣称自然人手同时按下所有键。

依赖发现逐例比较完整2048B RAM（含栈）、8192B SRAM、AXYP/SP/PC、有序端口与银行，1164例均与独立原CPU完整返回一致。探针内部3378次原helper执行只属于验证器；这一层不宣称所有helper已经独立源码化。纯源码矩阵使用相同三组输入和独立原CPU比较侧，不复用探针CPU作为服务。

| 实际远端callee | 原调用次数 | 机械作用与负责范围 |
|---|---:|---|
| physical25 `$A000` | 784 | 原OAM肖像入口；不是完整数字属性资料页 |
| physical29 `$A003` | 582 | 原文字worker；AXYP/scratch由本轮独立精确服务恢复 |
| physical29 `$A03C` | 100 | 原姓名packet，根据0001选择模板 |
| physical29 `$A030` | 44 | 另一原姓名packet；不是单凭名称推断的资料页 |

静态19个EE07调用的前置LDY、真实内联word及文件offset/bytes/hash都在 `catalog.json`：selector39映射25/26、3D映射29/30。最终 **19/19个callsite实际命中**；`$AAEA` 由单列0548=4/5输入执行29A030。基础348组本身只观察18个callsite，不能用扩展组覆盖替换其原边界。24个固定目标全部保留；最终仍未动态走E57F/E683，不能删去或宣称其分支也被本矩阵验证。F09C已经由第十一轮背景服务处理，不新增虚构fixed成功stub。

`callee-inputs/` 是每个远端入口前3个实际原helper边界的RAM/SRAM与寄存器/银行JSON。它们源自上述受控CPU输入，不是Nestopia内部callee抓取。肖像样本给officer47/131、X0/1、A4=0、04BC0/208、OAMcursor0/80；更宽的portrait域应由其自身原CPU矩阵验证。

## 纯源码整合与等待

新验证脚本的整合侧只调用 `GameEngine` / `SceneCoordinator` 的独立源码，`external_callback=None`，没有原CPUhelper、原ROMfallback或默认RTS。缺失callee保留实际PC/SP/银行和服务owner，并验证不提供新输入时恢复同一owner不会改ready/内存或重复端口。真实原CPU在相同callee、栈、银行和端口边界停止后比较。

默认 `--register-contract exact` 比较AXYP/SP/PC。显式 `semantic` 选项仅用于诊断：仍严格比较所有声明RAM、8192B SRAM、真实PC/SP、有序端口与最终银行，但仅记录AXYP差异，不能声称等价。背景/图形请求和旧文字/动画服务的声明合同保持各自范围。

纯源码RAM合同为 `$0000..01B3`、`$0200..07FF`；空闲 `$01B4..01FF` 栈残留不比较，实际callerPC/SP仍逐例比较。硬件输入是显式交替80/00的PPUSTATUS样本和0值APU/手柄。源码不创建输入、画面帧、PCM、中断时钟或队列确认。源码依赖在矩阵前后hash若有变化，回执明确失败，避免将正在编辑的文件误pin为实际执行版本。

新的肖像、姓名packet和精确文字服务接入后，正式 `source-integration.json` 为 **1164个完整原CPU返回对照、1个未知callee拒绝guard、0失败**。分组为基础348、方向/按键字节812、AAEA完成扫描4；默认exact合同下AXYP/SP/PC、1972个声明RAM地址、8192B SRAM、有序端口和银行全部一致。执行前后源码依赖hash稳定，其原CPU只在独立比较侧运行，纯源码侧原CPUcallback为0。没有剩余prefix被假装计成完成。详细资料页25A012不在普通攻击的19个farcall集合内，它的独立恢复和原核心battle-info流程在本轮其他目录另证。

另有 [UI整合45例](../ui-integration.json) 与 [独立验证脚本](../../../scripts/verify_phase12_ui_integration.py)：原Native row0..9、完整页frame272与旧FFframe31的RAM/SRAM，分别调用25A012、battle A244、真实A000包装；另9例先实际执行EE53消费packet、再F237切回25调用下一行producer。44例完整返回，frame31尚未初始化的额外A244入口1例在selector37→physical23 A012真实图形依赖边界停下，另1项范围guard；它不是合法A000失败。此45例不并入1164主矩阵。CPU寄存器/已有EE4D caller frame为明示fixture，不声称从Native录制；F25F/F237真实重建bank上下文，不手改队列、mapper缓存或结果。

早期探索回执 `initial-full/source-integration.json` 保留348例的旧结果：201严格前缀、99完整返回精确一致，另外48例只AXYP不一致（41项carry、7项X），当时所有玩法RAM/SRAM/端口/银行均一致。它们都在真实A000包装调用文字worker后发生，本轮精确文字服务已闭合这些差异；**这份早期回执不是最终passed证据**。以正式 `source-integration.json` 的最新pins为准；`catalog_only` 仅表示依赖调查，不能作为纯源码矩阵通过。

```sh
# 只调查原helper与远端实际入口，明确不算纯源码闭合。
.venv-trace/bin/python scripts/verify_phase12_attack_integration.py --catalog-only
# 全1164入口的无原CPU回调整合；缺失或协议差异不会补成功。
.venv-trace/bin/python scripts/verify_phase12_attack_integration.py
# 原基础348范围，不含方向字节和AAEA额外输入。
.venv-trace/bin/python scripts/verify_phase12_attack_integration.py --base-only --out analysis/phase12/dependencies/base
# 120入口快速检查（基础buttons0与4个AAEA例）；另存目录。
.venv-trace/bin/python scripts/verify_phase12_attack_integration.py --quick --out analysis/phase12/dependencies/quick
```

- [新验证脚本](../../../scripts/verify_phase12_attack_integration.py)
- [原调用清单、字节与全部输入](catalog.json)
- [纯源码整合状态及精确范围](source-integration.json)
- [冻结普通攻击控制器证据](../../phase11/attack/README.md)

所有“完整返回”只描述这次有界函数调用，不代表所有数据分支、反复tick、全部普通攻击流程或独立NES仿真已经完成。
