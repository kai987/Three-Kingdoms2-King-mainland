# WP08 最短连续源码子包

从 WP05 实际捕获的 E066 现场出发，正常路线与 ECEE 服务暂缺恢复路线均已到达 global1/E066 返回点。此次完成这个有界子包后停止；完整 WP08、整款游戏以及城市字段正式命名仍未完成。

正式执行与验收以 [run-05](run-05/validation.json)、[最终核验](verification.json) 和 [离线语义核验](semantic-validation.json) 为准。前四次尝试完整保留，身份与失败原因见 [执行履历](execution-ledger.json)；run-02 失败、run-03 缺少总回执，没有把它们回填为通过。

## 连续执行的结果

| 项目 | 正常案 | ECEE 暂缺恢复案 |
|---|---:|---:|
| 预先声明的周期上限 | 27 | 27 |
| 实际消费的松键软件周期 | 24 | 24 |
| main / fresh NMI / IRQ / resume | 24 / 24 / 24 / 24 | 24 / 24 / 24 / 25 |
| 与独立原指令 CPU 比较的执行边界 | 96 | 97 |
| 另行核验的假返回、不推进检查 | 0 | 2 |
| 原指令 CPU 实际执行数 | 81,364 | 81,364 |
| 最终位置 | global1 / E066 / SP=FF | global1 / E066 / SP=FF |

两案合计 193 个执行边界及另外 2 次假返回检查，比较了 579 对完整 RAM/SRAM/PPU sink 输出。每个执行边界同时核对全部寄存器、实际四个 PRG 页、逻辑 IO 顺序、PPU/DMA 请求及声明的设备状态。每案只初始化一次 Source 与独立 CPU，各自保留同一 game、coordinator、memory、register、session；没有导入后续 Native 快照。

实际经过 15/0 → 15/1 → human14/0 → 15/2 → 15/3，最后清空 pending 与内层 owner，返回 global1。写 0500 和 0501 之间暂时出现的 14/1 仅列入瞬态写日志，没有执行 human14/1；human14 的 1..6 阶段仍待真实路线验证。终点不是 global2 或可操作的城市界面。

## 新整合的源码入口

新增 [ActualE066PostbattleContinuity](../../source/recovered/postbattle_continuity_wp08.py) 核对真实入口的 REG、四页 PRG 及 2K/8K 内存摘要，然后交给已有的可读游戏逻辑。它不包含 CPU/IR 解释器、原模拟器调用、后续快照加载或准备完成标志注入。本次新增的是实际入口保护及连续性整合，没有重写已有玩法算法。

| 原位置 / 行为 | 现有可读函数 | 本次证据 |
|---|---|---|
| BB36 → BC46 → BD67 | `PostbattleEarlyServices.allocate_AI_officers` / `allocate_defeated_attacker` | 同一 Source NMI 沿真实栈调用 |
| BDCD..BE54 | `collect_side_officers_and_captives` | 自然生成 `[67, FF×20]` |
| BD96..BDB8 | `fill_pointed_city_roster` | 6214 实际 FF→67，城市16的第4个名册槽 |
| BD91/BD95 → BB39 | 上述分配函数的 `_local_call` / `_rts` | BB38、BD90 两组实际压栈字与独立 CPU 一致；本软件策略下 BB39 的 SP=F0 |
| D4F0 / EE07 | `PostbattleReturnBridge.finish_return_after_draw` 及 Shared 远程桥 | 依照最初 call.entry_banks 恢复代码页 12/13；保留原 E1 和数据页副作用 |
| ECEE | Shared 调色板请求服务 | 同步真实返回 BB96 一次 |
| BBA0 / BBB8 | `PostbattleCompletionServices.complete_after_palette_transition` / `finalize_current_city_and_neighbor_chiefs` | 20 次新 NMI 实际读取 87，值为 `01×19, FF`，随后 global1 |

源码分别位于 [早期结算](../../source/recovered/postbattle_early_services.py)、[远程父调用](../../source/recovered/postbattle_parent_integration.py)、[结算完成](../../source/recovered/postbattle_completion_services.py)。Source 与 CPU 的此处栈深相同；此前 WP05 Native 在 BB39 的 SP=EE 属于另一中断时序，不能拿来声称逐帧时序相等。

EE07 原调用入口为 `[17,12,13,31]`，完成后为 `[16,12,13,31]`，E1 实际 49→48。暂缺恢复案重入审计的“当前页”曾为 `[17,8,9,31]`，这是暂停位置，不是原调用入口。恢复页判断使用真实 call.entry_banks，未把 E1 解释为不变。

## 暂缺服务的恢复

恢复案同样从实际 E066 起点自然运行到 ECEE；没有建立合成的 stage2 场景。两次测试返回仅声称 returned，原 PC/SP 没有真正返回，因此已有 owner 坚持 dependency。两次检查均保持原 phase、call、owner、generator 身份，外/内 generator 指令位置不变；Source/CPU 的 RAM/SRAM 写入计数均保持 3499，完整读写日志、内存、REG、映射、设备及逻辑 IO 指纹不变。随后恢复真实 Shared 一次，再以新的 NMI 完成 stage3。

原始证据在 [fake-return-checks](run-05/withheld-ECEE-same-actual-origin/fake-return-checks.json)、[身份日志](run-05/withheld-ECEE-same-actual-origin/identity-journal.json)、[调用审计](run-05/withheld-ECEE-same-actual-origin/source-call-audit.json)。本路线没有遇到新的真实未知服务，不触发 WP02 备用工作包。

## 实际来源与设备边界

唯一起点为 WP05 的 `callee-0012-E066`，local356、原始事件245099、snapshot12：REG A=FF/X=05/Y=28/P=27/SP=FF/PC=E066，实际 PRG `[3,8,9,31]`。读取原 2K/8K，摘要及元数据由 [spec-v2](spec-v2.json) 锁定。frame-00356.state 的 PC 是 E889，未替代这个软件现场。CF02 结果写发生在此起点之前，本 Source 续程继承其结果，没有重新触发 CF02，也没有证明在野招募成功。

[input-plan-v2](input-plan-v2.json) 在本次执行前写入、实际读取和锁定哈希；execution-inputs 的 27 项是预展开上限，每案实际消费前 24 项。每周期为 main 后 fresh NMI；仅等待真实软件 IRQ 标志时按声明策略送 IRQ 并恢复同一个 NMI。即时 PPU/APU/N163/控制器内部状态并未由原快照捕获，本次明确采用共同软件设备夹具：2002/4015 读0、5800读127、预声明128字节N163、空16K PPU sink与控制器内部初态。保留并核验实际后续读写副作用。

这是明确设备策略下的源码/原指令 CPU 对照。新 Native 执行与帧数均为0；既有 WP05 的原模拟器非空归城证据独立保留。未声称 RGB/PCM、扫描线/中断到达时序、每条原子服务的中间 AXYP 或全 RAM 微周期总线等价。

完整 RAM 写日志每案 CPU 为21,230条、Source为21,224条，差6条来自 F2D7 指针换算对00/01的中间清零、移位写；Source直接写最终指针。选定的完整事件边界、IO、栈协议和最终指针保持一致。这些日志完整保留，不能把本次结果扩大为逐opcode或任意指令位置可中断的轨迹等价。

## 冻结与尚未完成的工作

运行前后核对全部 101,066 个旧预期路径：31 的 91,929 产物 pins/596源码脚本 pins、32 的2,101残留文件、closure 的16文件、WP05 的7,000 manifest文件及其当前6脚本/6C++源/2核心二进制均保持不变。见 [frozen-before](frozen-before.json)、[frozen-after](frozen-after.json)、[输入哈希](input-manifest.json)、[输出哈希](artifact-manifest.json)。本包保留前四次探索执行的原脚本身份，不用当前脚本倒填旧执行哈希；未分发 ROM。

字段账本仍为 1,526=1,201条件排除/80possible/245unknown，剩325；raw345独立统计。城市+1和+28..31正式名称仍为 null。本次不迁移字段候选、不声称剩余376条已逐项解决；在野武将招募成功完整流程仍待单独实际触发。未知服务总数、完成百分比及剩余轮数均保持 null。

建议下一子包是 WP02 的 B517 current-JSR 合同和逐条候选迁移复核；这里只建议并停止，不自动执行。
