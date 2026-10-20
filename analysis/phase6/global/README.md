# 全局主循环与 NMI 控制窗口

本目录恢复 fixed bank 31 的全局调度、场景准备和有界 NMI 前序/退出控制。原 ROM 只读；恢复源码读取分发表和资源数据，执行独立 IR 与已恢复的源码 helper。原 6502 执行器只在验证脚本中用于对照。这里的一次调用是合作更新或明确的控制窗口，不代表完整 NES 帧。

## 可用接口与边界

`source/recovered/global_main_loop.py` 提供 `GlobalMainLoop(memory, hooks=None, program=None)`：

| 接口 | 起点与正常边界 | 调用方必须提供 |
|---|---|---|
| `step(registers=...)` | `$E066` → 下次 `$E066` | 当前 `$007A`、真实 PRG 映射、CPU 寄存器与栈 |
| `cold_post_reset(registers=...)` | `$E05E` → `$E066` | 原 RAM reset 已完成；未恢复 `$F3BD` 保留依赖 |
| `nmi_step(registers=...)` | `$F862` → `$F88D` | 真正 `$F800` 前序后的上下文、NMI 映射、忙标志与栈 |
| `nmi_prefix(registers=...)` | `$F800` → `$F88D` 或忙分支 `$F8AF` | 硬件已压入的中断返回栈；PPU/IRQ 等硬件服务 |
| `run_window(entry, stop_pcs=..., return_pc=..., registers=...)` | 显式起点、边界或真实返回 PC | 与该入口匹配的全部 CPU 上下文 |
| `run_entry(...)` | 转发到上述有界窗口 | `seed_return=True` 明确拒绝；不写假返回地址 |

返回值包括 `status`、`before/after`、`registers`、`instructions`、`events`；依赖返回还带 `dependency`。`boundary` 表示命中约定的控制边界；`returned` 表示用真实栈到达调用方指定的返回 PC；`dependency` 保留此前所有写入和寄存器变化；`budget` 表示指令预算耗尽。超出分发表合法域的索引抛出 `InvalidGlobalIndex`。继承的战场 `phase()` 在此明确拒绝，避免修改错误的状态字段。

外部 hook 的合同是 `(context, target, return_pc, kind)`。真正 JSR 已经把 `call_pc+2` 压栈；hook 必须使用当前物理 PRG bank、共享的寄存器/SP 和真实返回协议。相同 CPU `$A000` 在不同 bank 是不同函数。源码不把渲染、音频、IRQ 等缺失服务当作成功返回。

默认 `PrgDataMemory` 对三处 PRG mapper 写入和 `$4015` 请求有明确支持；PPU、Namco `$F800`、完整 SRAM 保护和时序仍是边界。所有游戏记录写入经过该内存对象；本模块没有追加硬件模拟器。

## 两张真实分发表

主循环 `$E066` 使用 `$007A & $1F`，在 `$E07C..$E099` 读 15 个 little-endian 指针，ROM 文件偏移 `$3E08C`。NMI 使用 `$0078 & $0F`，在 `$F87B..$F88C` 读 9 个指针，文件偏移 `$3F88B`。物理 bank 31 的地址换算为 `file = $3E010 + CPU - $E000`。

下表的名称是现代功能说明，入口与操作由原字节证明；名称不冒充原游戏文字。

| `$007A` | bank31 CPU | 作用和控制转移 |
|---:|---|---|
| 0 | `$E09A` | 初始化硬件请求、音序和 bank 缓存；正常写主状态 9 |
| 1 | `$E0DA` | 城市场景准备，写 NMI 模式 2；完成后主状态加到 2 |
| 2 | `$E17D` | RNG `$E87A` → `$F24B(Y=$2A)` → physical10/11 `$A000→A00F` 内政 AI 一次更新 → 主循环 |
| 3 | `$E18B` | 战场初始化/恢复，写 NMI 模式 3；`$0500==11` 时用 pair12 `$A006`，否则 pair8 `$A003`；完成后到 4 |
| 4 | `$E221` | RNG → `$F24B(Y=$28)` → physical8/9 `$A000→A02D` 战术 AI 一次更新 → 主循环 |
| 5 | `$E22F` | 普通攻击场景准备，NMI 模式 4、profile=`$0544+2`；完成后到 6 |
| 6 | `$E2E2` | RNG 更新后回主循环；场景由 NMI 推进 |
| 7 | `$E2E8` | 单挑场景准备，NMI 模式 5、profile `$0A`；完成后到 8 |
| 8 | `$E36A` | RNG 更新后回主循环；场景由 NMI 推进 |
| 9 | `$E37C` | 标题/开始/剧本选择场景准备，NMI 模式 6；完成后到 10 |
| 10 | `$E3EB` | 空闲，直接跳回主循环 |
| 11 | `$E3EE` | 新游戏/君主选择场景准备，NMI 模式 7；完成后到 12 |
| 12 | `$E3EB` | 与 10 同一空闲入口 |
| 13 | `$E46A` | 结局场景准备，NMI 模式 8；`$0541=0` 与非零选择不同音频请求；完成后到 14 |
| 14 | `$E3EB` | 与 10/12 同一空闲入口 |

主状态 2 和 4 的 banked AI 可能自行修改游戏状态，其后续行为由该下层源码合同决定，不能由固定循环的指针表推断。主状态 13 的 `$0541=0` 是无继承人结局入口；`1..3` 是评分结局类别。此模块没有虚构类别的原文字形名。

| `$0078` | bank31 callback | 下层映射协议与作用 |
|---:|---|---|
| 0、1 | `$FA97` | 通用 callback，共享同一入口 |
| 2 | `$F8B5` | 城市 UI：logical `$3B` → physical27/28 `$A000` |
| 3 | `$F8FE` | 战场：`$F94D` logical `$2C` → physical12/13 `$A000` |
| 4 | `$F96A` | 普通攻击：`$F994` logical `$2E` → physical14/15 `$A000` |
| 5 | `$F9A0` | 单挑：`$F9CD` logical `$37` → physical23/24 `$A01B` |
| 6 | `$F9E4` | 标题/开始选择：`$FA04` logical `$2A` → physical10/11 `$A003` |
| 7 | `$FA13` | 新游戏/君主选择：`$FA44` logical `$28` → physical8/9 `$A024→bank9:$D70F` |
| 8 | `$FA53` | 结局：`$FA85` logical `$37` → physical23/24 `$A01E→bank24:$D693` |

因此 main2 的内政 AI 与 NMI2 的城市 UI 有不同入口和 bank 协议；main4 的战术 AI 与 NMI3 的战场控制器也分属两个更新窗口。NMI8 是结局控制器。

## 前序、bank 缓存与真实退出

正常 NMI `$F800` 前序保存 A/X/Y，并执行原样的 PPU/DMA 请求、忙标志和 bank 切换。`$F83E` 使用 `$E1/$E2/$E3` 激活 callback 的 `$8000/$A000/$C000` 窗口；`$F862` 清 `$007C` 后分发。callback 中 `$EE53` 是 PPU 待处理工作分发器。每次 callback 的音频帧更新为 physical14/15 `$A003→bank15:$D8D4`，核心合成仍是显式外部依赖。

四个 mapper helper 的区别已覆盖全部原始 selector 字节：

| helper | 保存的 logical shadow | 映射 |
|---|---|---|
| `$F237` | `$E2/$E3` | NMI callback 的代码 pair 到 `$A000/$C000` |
| `$F24B` | `$DF/$E0` | 主线程的代码 pair 到 `$A000/$C000` |
| `$F25F` | `$E1` | NMI callback 数据页到 `$8000` |
| `$F266` | `$DE` | 主线程数据页到 `$8000` |

此 ROM 中 physical bank=`(logical & $3F) % 32`。pair helper 通过原 PHA/PLA 保持 A，最终 NZ 来自 A；验证包含 X/Y/P/SP、真实栈和全部 shadows。

正常 `$F88D..$F8AF`：`DEC $007B`；按 `$DE/$DF/$E0` 恢复主线程映射；递增 RNG 游标 `$50/$52/$54/$55`；递增 16 位 `$5E/$5F`；随后 `$F8AF` 恢复 Y/X/A 并 RTI。忙 NMI `$007B!=0` 走 `$FAD5`，另存 `$E3/$E2/$E1` 并在音频更新后恢复，直接接 `$F8AF`；不会执行正常 RNG/计数器递增。

`$FB28` 轮询 `$0062`。若该 flag 非零，独立合作窗口返回 `irq_wait` 依赖；不会伪造 IRQ 完成。`$E768` 先修改 `$008B` 后在 `$E770` 请求写 PPU `$2000`；默认严格总线就在该真实写入处停止。

两段高层可读函数另有独立内存合同：

- `reset_scene_working_state(memory)` 对照 `$E4E9..$E51C→$E823`，清工作字段、把旧任务 `$0300/$0304` 设 FF、隐藏 256 字节 OAM；这是取消旧场景工作，不是完成新渲染。此前的硬件关闭、音频 reset、nametable 操作仍需真正执行。
- `finish_nmi_bookkeeping(memory)` 对照 `$F88D..$F8AF` 前段，恢复映射和更新计数；不包含保存寄存器弹栈、RTI 或真实时间推进。

## 验证回执

`validation.json` 最终 6,567 项通过、0 失败：6,319 项原 ROM CPU/内存对照，以及 248 项非法域拒绝的源码 guard。所有 15 个合法主状态和 9 个合法 NMI 模式均进入原 ROM 对照；120/144 个有合法目标的 masked aliases 单独覆盖。

| 组别 | 数量 | 验证范围 |
|---|---:|---|
| 主/NMI masked dispatch aliases | 120 + 144 | 原指针、寄存器、栈、全部 RAM/SRAM、bank 到达准确入口 |
| 非法主/NMI 索引源码 guard | 136 + 112 | 源码拒绝，未执行原 ROM 越界指针 |
| 严格主状态 | 60 | 40 次真实依赖前缀、20 次主循环边界 |
| 严格 NMI window/prefix 与 reset 入口 | 18 + 18 + 1 | 全部在真实缺失边界停止且前缀一致 |
| 有同步 IO 合同的 NMI 前序 | 18 | 验证器总线的明确 PPU status 样本和记录，不模拟完整帧 |
| 带原始外部 helper 的合作更新 | 52 | main26 boundary/6 dependency；NMI20 boundary |
| 4 个 mapper helper 原始 selector/flags | 4,096 | 真返回、寄存器/flags/SP、所有 RAM/SRAM、映射 |
| 可读场景工作状态 reset | 512 | 全部 RAM/SRAM 内存效果 |
| 可读正常 NMI bookkeeping | 1,024 | 全部 RAM/SRAM、映射效果 |
| 已保存寄存器弹栈与 RTI | 256 | 所有 SP 值；调用方提供真实 6 字节栈帧，到指定返回 PC |

IR 共 1,005 条，1,005/1,005 原字节来源准确；这些测试动态执行 885/1,005 条 IR。合法入口覆盖、静态字节来源、动态指令覆盖是不同度量，不能把合法入口全部测试称为动态指令 100%。可读语义函数的原 CPU 位置另外计入 `native_instruction_locations_including_semantic_oracles`。

52 次 oracle-assisted 测试仅在验证器中执行真正的外部 6502 字节，helper 限制 20,000 指令；等待、未知 opcode、预算均保留依赖。它们证明固定控制图在真实下层代码返回条件下的行为，不证明独立源码已经恢复完整音频/显示。严格生产总线测试保留这些缺口。RTI 测试只验证退出栈协议，根集成的 `tick_nmi` 仍是 callback 窗口，不是完整 NMI/帧。

fixtures 使用已有真实核心 RAM/SRAM：战场、普通攻击、单挑、城市信息、标题和君主选择。`typed_fixture_sources` 和 `fixture_source_sha256` 固定原文件；验证器明确覆盖 `$007A/$0078`、bank shadows、RNG、工作任务等初始化字段，主3设置 `$0500=0/11` 两条恢复分支，结局 `$0541=0..3`。`fixtures` 保存每次严格或带外部 helper 的实际目标、bank、状态、寄存器、依赖与 helper 返回链。这些是受控 CPU 输入，不冒充自然按键到达的全部场景。

回执的三个 scalar `source_sha256`、`validator_sha256`、`program_sha256` 分别固定源码、验证器和控制 IR；并保留 catalog、共享依赖源码及 fixture RAM/SRAM hashes。原 ROM SHA256 仍为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## 重跑

```sh
.venv-trace/bin/python scripts/analyze_global_main_loop.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_global_main_loop.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

第一条只重新生成本目录的 IR、状态目录和汇编证据；第二条重新生成与当前源码、验证器、IR 对应的验证回执。没有修改 ROM，也没有增加未恢复音频/PPU/IRQ 的默认成功实现。
