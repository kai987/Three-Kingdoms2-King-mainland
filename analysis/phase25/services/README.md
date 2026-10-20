# 服务缺口索引：入口、实际调用上下文与证据层次

本目录建立可追查的服务索引，不宣称已经得到“全游戏尚缺多少个函数”的答案。`unknown_unique_services` 仍为 `null`，整体服务闭包仍未证明。新的分析器和验证器只读取源码AST、冻结原指令账本、分项回执及已有输入来源，不执行恢复Source、原6502或Nestopia；本目录新增Source病例、原CPU病例、Native运行数均为0。

## 三种证据层和执行来源

| 层次 | 文件 | 能说明的范围 |
|---|---|---|
| 现有执行回执和实际caller来源 | `observed-service-index.json`、`receipt-observations.json`、`captured-caller-index.json` | 回执曾记录该调用、完成、等待或前缀；保留当时输入域和模式，不重新执行或扩大覆盖 |
| 可信有界静态发现 | `trusted-static-calls.json` | 原可信指令位置有对应JSR/JMP与原字节；不是本轮动态覆盖或整款游戏可达性证明 |
| 仅源码语法 | `source-syntax-boundaries.json` | AST中声明external、dependency/wait或entry；单凭声明不能认定某个函数尚未实现 |

执行记录另有来源子类，不能互相替代：

- `actual_Native_snapshot_originalCPU_reached_caller`：从真实Native保存点开始，独立原CPU继续执行到caller。续行没有新增中断时，概率或资源结果可能和连续Native不同；不能称固定原核内部已经观察到此入口。
- `passive_Native_callee_capture`：独立被动观察核心实际到达opcode入口并保存软件状态。原核心和观察核心仍须按声明路线核对；瞬时未捕获的硬件状态不能补称Native数据。
- `controlled_CPU_fixture`：受控数值、调用者或模式矩阵，不能升级为自然操作路线。
- `validator_with_original_helper_mode`：旧验证器包含原helper/oracle模式，保留模式和现有计数；其callback返回不是独立纯Source闭包证明。未记录来源的项明确保持未记录。

## 去重、当前owner与暂停状态

已知完整映射的banked入口按 `physical-bank:CPU-entry` 建键，固定入口按 `bank31:entry` 建键；每个键保留各自caller、映射、回执JSON pointer和执行模式。相同 `A000` 在不同物理银行不是同一个服务。缺少映射时保留上下文键，不把裸地址并成唯一未知函数。

`owner-route-catalog.json` 从实际协调器继承链、按顺序的路由谓词和入口集合生成有限静态模型。当前owner存在，只表示有对应路由和声明实现，不等于任意输入都能完成或其传递依赖已经闭合。高优先级谓词不能解析时会停为 `conditional_route_unknown`，不会跳过它再宣布较低优先级owner已负责。

静态指令所在物理银行只确定该8KiB窗口。跨窗口调用没有完整mapper来源时不猜另一窗口的银行；只有同窗口或固定31目标才在该静态索引中获得确定物理身份。

`closure-status-ledger.json` 将owner、等待/前缀、上下文不足和闭包未知分开。它没有把所有external当成缺失函数，也没有依据“已返回一次”宣布完整闭包：

- 阶段24的 `strict-no-division-owner` 和 `strict-no-menu-owner` 是故意不提供 `EA7C`、`ED19` 服务的夹具；当前分别有真实共享算术owner和菜单owner。
- `F41E` 是原诊断永久停留，不是未实现callee。
- `E00C` 的vblank等待与 `B78B` 的合作答复等待需要真实显式输入，不应通过写ack来消掉，也不应改叫未知函数。
- `stop_PC` 可能是现有函数内部的等待、预算或声明比较边界。没有实际callee证据时，索引把它列为执行位置，不冒充服务入口。
- 只有语法标记或不完整上下文的项继续保留，不能据此命名为 `unimplemented`。确认未实现的总数目前也为 `null`。

本索引读取94份阶段24冻结Source及2份阶段25新增Source，使用最新 `AppearancePointerSceneCoordinator` 工厂；97份旧回执与本轮已冻结45案整合回执只读列账。新63份opcode边界导出包括60份C5D2、2份D471和1份B431，逐项核原160字节父事件、寄存器、真实栈、PRG页与2K/8K快照。连同旧13域18份独立CPU续行上下文、旧24域4份实际导出，索引共85份上下文；这85项不是本轮原机85份稀疏快照的同一个集合，也不是85个新增验证病例。

## 整体验收与下一步

`acceptance-map.json` 完整保留阶段24的十个验收维度及其明确要求来源，并为本索引给出下一步验收方法。它没有新增用户未提出的重制义务：可读行为源码与原作者工程、从高级源码编译相同NES、独立音画硬件仿真属于不同的证明目标。

对真正需要补全的调用，应先取得实际bank/entry/caller及完整指针/硬件输入，再让最新owner在同一真实返回帧上执行，逐项比较PC/SP、RAM/SRAM、IO和mapper。原等待应由真实服务或输入推进；不能用人工ack、原CPU回退或一次静态命中替代。历史回执中的旧缺口若已由新owner实现，保留其历史范围而不重计为当前缺口。

索引是有界盘点：它读取分析器列出的回执集合和已冻结可信指令账本，并不包含整块ROM所有可能入口，也没有执行新的路径或穷尽中断交错。具体输入、当前工厂、观察数量和各层计数以 `analysis-summary.json` 为准，静态交叉检查以 `verification.json` 为准。

```sh
python3 scripts/analyze_service_gaps_phase25.py --frontdoor AppearancePointerSceneCoordinator
python3 scripts/verify_service_gaps_phase25.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

分析器只写本轮 `analysis/phase25/services/`；旧Source、脚本、回执、Native、HTML、ROM、核心和归档均保持原字节。当前源码/回执的哈希在新证据内固定，不能用更新旧hash代替真实游戏验证。
