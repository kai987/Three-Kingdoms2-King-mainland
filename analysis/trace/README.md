# 有界 6502 启动执行证据

本目录提供基于原 ROM 字节的可复跑执行记录。它是 **6502 同步执行模型**，不是完整 NES 模拟器；没有游戏画面、真实帧时间或完整游戏行为验证。原始 ROM 只读。

输入文件 SHA-256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## 重跑

在项目根目录执行：

```sh
python3 -m venv .venv-trace
.venv-trace/bin/python -m pip install -r analysis/trace/requirements.txt
.venv-trace/bin/python scripts/trace_startup.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/trace_startup.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --entry-case sram-init --out analysis/trace/sram_init_harness
.venv-trace/bin/python scripts/trace_startup.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --ppustatus zero --out analysis/trace/blocked_ppustatus
```

## 默认复位路径结果

执行 51,045 条指令、596 个唯一指令起点、1,376 个唯一指令字节；py65 累积周期数 181,226（不包含真实 PPU/DMA 时序）。执行过的物理 PRG bank 为 23、29、30、31。

| 观察点 | 本次执行证据 |
| --- | --- |
| Reset | 固定 bank 31 的 `$E000`，`SEI; CLD` 后关闭 PPU 控制/显示 |
| PPU 等待 | `$E00C`、`$E011` 和 `$E032`、`$E037` 轮询 `$2002` 的 vblank 位 |
| RAM 清理 | `$E04D` 实际把 `$0004..$07FF` 共 2,044 字节写零；不能称所有 2 KiB 均由该循环清零。`$0001/$0002` 是清理指针，结束时为 `$00/$08`；`$0000/$0003` 的零值来自模型初始假设 |
| `$F3BD` 检查 | 无按键输入下，控制器比较在 `$F3ED` 分支到 `$F421 RTS`，返回启动代码。后面的 SRAM 检查及 `$F41E` 停机循环未执行 |
| 主状态分派 | `$007A & $1F` 经 `$E07C` 指针表跳转；观察到状态 `0 → 9 → 10`，对应 `$E09A → $E37C → $E3EB` |
| 银行映射 | 原始 selector 在 `mapper_writes.json` 的 `value` 保留；物理 bank 使用低六位，再对 32 取余 |
| NMI 开启 | 执行至 `$E770` 写 `$2000=$90`，之后进入状态 10 的分派循环 |
| 停止边界 | 模型不注入 NMI；状态 10 的 `$E3EB JMP $E066` 重复 2,000 次后停止。`stop_pc=$E06D` 是重复检测触发后的下一个 PC，不代表真实硬件停机 |

默认启动中，切换窗口第一次 ROM 读取之前均已收到相应 PRG bank 寄存器写入；`switchable_prg_reads_before_register_initialization=0`。因此本次启动指令结果没有依赖任意设定的初始切换 bank。默认启动没有写外部 SRAM，也没有执行下面的数据复制例程。

## 隔离 SRAM 初始化例程验证

`sram_init_harness/` 是单独的受控函数调用：从物理 bank 30 的 `$DD8B` 开始，预设切换 bank 为 `[0,29,30,31]`、SRAM 写保护寄存器值为 `$4C`、SRAM 填 `$A5`（`$6F43` 填 `$37`），并设返回地址 `$0200`。**这不能证明真实复位已经调用该例程。**

执行 55,256 条指令后，例程正常 `RTS` 返回。写了 SRAM `$6000..$6FFF` 共 4,096 个唯一地址，`$6F43` 保留 `$37`。以下两段输出均逐字节等于原始 ROM；SHA-256 和比较结果保存在该目录 `summary.json`。

| raw selector | 物理 bank | ROM 源范围 | SRAM 目标范围 | 长度 |
| --- | --- | --- | --- | --- |
| `$30` | 16 | CPU `$8C00..$8FBF`，PRG offset `$20C00..$20FBF` | `$6000..$63BF` | 960 字节 |
| `$31` | 17 | CPU `$8000..$8B3F`，PRG offset `$22000..$22B3F` | `$63C0..$6EFF` | 2,880 字节 |

这为数据表复制边界提供运行佐证；记录格式是否为 `30 × 32`、`240 × 12` 以及字段语义还需要数据分析证据。

## 文件说明

- `summary.json`：运行参数、停止理由、状态变化、分派目标、假设和最后 64 条指令。
- `executed_instructions.json` / `.csv`：按物理 bank 和 CPU PC 排序的唯一已执行指令；JSON 含 `physical_bank`、`cpu_address`、`prg_offset`、`rom_offset`、`size`、`bytes`、首次执行时 bank 映射及次数，可用作反汇编种子。
- `entry_seeds.json`：执行观察到的调用/跳转/中断返回后入口。它们只反映本模型覆盖，不等于完整函数列表。
- `executed_byte_ranges.json`：已执行指令字节的 PRG offset 闭区间。
- `control_flow_edges.csv`：实际相邻执行位置及重复次数。
- `mapper_writes.json`：PRG/CHR/nametable、保护/声音地址、IRQ 寄存器写入；CHR 和 IRQ 只记录，不仿真时钟/渲染。
- `io_writes.json`：PPU 控制/显示及 APU/控制器寄存器写入。
- `rom_read_ranges.json`：包含指令取指和数据读取的 bank offset 闭区间；不能直接当作纯数据表范围。
- `final_ram.bin`、`final_sram.bin`、`final_n163_internal_ram.bin`：本模型结束时的内存快照。
- `blocked_ppustatus/`：令 `$2002` 恒为零的对照，证明默认结果依赖人工解除 vblank 等待；该对照停在第一段等待，不能进入后续初始化。

## 模型边界与依据

Mapper 19 的 CPU bank 窗口、三组 bank 寄存器及外部 RAM 保护逻辑按 [NESdev Namco 163](https://www.nesdev.org/wiki/Namco_163) 实现；内部 128 字节 RAM 端口按 [Namco 163 audio](https://www.nesdev.org/wiki/Namco_163_audio) 的地址与自增规则处理。CPU 核心为 [py65](https://github.com/mnaberez/py65) 1.2.0。

默认 `$2002` 每次读取交替返回 `$80/$00`，只为让启动等待继续；不是测得的 vblank 周期。没有 PPU 渲染、CHR/nametable 映射、PPU 读缓存、NMI/IRQ 注入、DMA 时序和声音合成。APU 状态和手柄数据返回零。RAM 初值为零；隔离 SRAM 例程另有明确预设。py65 为文档化 NMOS 6502 指令核，非 2A03 专用核；本路径执行 `CLD`，没有观察到十进制运算或未支持指令。后续逆向应将这些覆盖视为有假设的执行证据，不能升级为真实整机验证。
