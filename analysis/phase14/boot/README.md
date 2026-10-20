# 冷启动、软件重启与条件诊断的直接源码

本轮恢复固定 bank31 `$E000` 的复位后软件流程，以及 `$F3BD/$F422/$F43F/$F458/$F468` 的条件诊断和 SRAM 模式辅助函数。生产模块直接使用具名函数、byte 运算、原寄存器与显式端口输入；不执行原6502、控制 IR，不生成 vblank，也不模拟硬件 RESET 微序列或周期时序。

[生产源码](../../../source/recovered/boot_initialization.py) · [原字节/REA证据](evidence.json) · [原 CPU 对照](validation.json) · [实际执行位置](executed-instructions.json)

ROM SHA256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。ROM 保持只读；所有 file offset 包含16字节 iNES 头。两段原范围为 `$E000..E065` / file `0x03E010` 和 `$F3BD..F476` / `0x03F3CD`，共 **288个原 byte、127个静态指令位置**；原 CPU 对照实际执行其中126个，剩余`F41E`永久JMP为停止边界。这不是作者函数数，也不把原资料中的 ROM 数据读当成 opcode 执行。

## `$E000` 软件流程及真正的停止边界

入口先 `SEI/CLD`，关闭 PPU，进行原 `$2002` 握手，再设置 `$4010/$4015/$4017` 和 PPU。第一组 Y=2 的 decrement/sign 循环实际等待 **3次置位→清位**，第二组 Y=4 实际等待 **5次**；没有改成通常的2/4次等待。端口样本由调用者提供；输入尚未达到条件时保留原 PC/SP 并待机。

之后 `LDX #FF / TXS` 替换原栈，地址指针从4开始，把 **`$0004..07FF` 共2,044 byte** 写0。`$0000/$0003` 不在这个清零范围；在普通 probe-mismatch 路径保持原输入。`$0001/$0002` 则是地址指针工作位，随后 `$F3BD` 又用 `$0001` 保存探测 bit，所以不能声称前4个 byte都原样保留。清零后的 `JSR $F3BD` 还会把返回字 `$E060` 写到 `$01FE/$01FF`，因此最终截图的整个清零范围不必全零。

普通 `$F3BD` 返回后将 `$007A=0`，到达真实 **`$E066` 下一次主循环分派边界、SP=FF**。这是替换旧调用栈后的初始化出口，**不是 RTS 回旧 UI caller，也不是一个完整 NES 帧**。GameEngine 可以据此退出旧调用上下文；不能通过伪造旧 caller 的返回地址表示复位完成。

## `$F3BD` 的70 bit条件探测

原代码设置 IRQ/CHR 相关寄存器，然后逐次读取 `$F3BD+X` 的原 ROM byte低bit，写 `$4016`，从 `$4017` 读取后取反其 bit1并比较，最多70次。ROM 中这些机器码 byte在此被**当作探测数据**读取；生产源码不会把它们解释成指令。

任一 mismatch 就正常返回，保留 SRAM；Native 冷启动和复位流程观察属于此普通路径。只有70次全部匹配时才进入条件诊断：

1. 通过原 `$F800=40` 选择可写 SRAM 环境，比较完整8KiB模式。
2. 模式匹配取调色值1；不匹配则先写整个模式、重新检查，成功取55(`37`)；重查仍失败取22(`16`)。
3. 对 `$3F00` 起的32个 palette byte写这个值，然后到达 **`$F41E JMP $F41E` 永久循环**。

源码把这一原永久循环表示为 `ServiceWait('terminal_boot_diagnostic',...)`。它没有软件 acknowledgment，不是未知 helper，也没有暗中写 ready 来退出。三种颜色表示代码分支，具体硬件诊断意图只作行为推断；第三个验证案例明确使用“单一 SRAM 地址写失败”的测试环境，并非观察到真实硬件故障。

## SRAM模式算法与辅助入口

`F458` 从 SRAM `$6000`、byte种子`AA`准备模式；`F468` 以 byte算术更新 `v = (5*v+1)&FF`，若0则重复到非零。`F422` 按原顺序检查完整 `$6000..7FFF`，在首个 mismatch停止；`F43F` 写相同完整模式。入口保留原 scratch/flags/实际 caller栈，不改成只返回一个 Python布尔值的替代函数。

```python
from source.recovered.boot_initialization import BootInitialization

boot = BootInitialization(memory, rom)
result = boot.run_reset(actual_registers)       # E000 → reset_boundary at E066
result = boot.run_service(0xF3BD, actual_registers)  # 使用实际caller frame
# 缺端口输入时待机；提供真实输入且恢复PC/SP后可 boot.resume()。
```

也支持真实 `ServiceCall` owner。入口要求实际寄存器；辅助函数要求原二进制运算上下文和已存在的 caller frame。暂停期间另一 caller不能接管同一 probe，修改 PC/SP后也不能继续原待机。

## 原 CPU 差分与回执范围

最终 **856个原 CPU 对照 +6个源码边界检查通过，0失败**。完整分类以 `completion_kinds/group_case_counts` 为准：

| 分类 | 数量 | 准确含义 |
|---|---:|---|
| `reset_E066_boundary` | 304 | 到达原初始化出口，真实 SP=FF；不是 RTS |
| `actual_caller_RTS` | 549 | 探测 mismatch 或局部辅助函数真实返回caller |
| `permanent_F41E_diagnostic` | 3 | 三个诊断分支到原永久循环前缀，不伪称整个程序返回 |

回执的 `complete_return_count=853` 历史统计键包括304初始化边界和549 RTS；不能把853概括成“全部函数返回”。`rows` 只保留每组最多12个代表样本，56行不等于856案例，完整数量由两个分类计数表核对。

所有案例比较 **全部2,048 RAM、8,192 SRAM、A/X/Y/P/SP/PC、完整栈残留、原端口读写顺序及 mapper banks**。覆盖12种准备×5种SP×5种flags的300复位案例、4种 vblank等待延迟、70个探测 mismatch位置×4种SP、256个模式递推输入、真实caller准备、首 mismatch位置、模式写入及三种诊断。

显式 `$2002/$4017` 输入是双方一致的 CPU实验条件，不是 Native 内部端口/指令 trace。直接 SRAM辅助实验声明整个8KiB可写；整个诊断分支则包含原真实 `$F800=40`。6个源码 guards单列，不混入原 CPU 成功数量。生产原 CPU callback和控制 IR数量均为0。

```sh
.venv-trace/bin/python scripts/verify_boot_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

原 Nestopia 普通冷启动、`retro_reset` 保留全SRAM、标题完整16位计时`0B58`超时后软件重启，是本阶段独立[Native证据](../runtime/README.md)。原核的 RGB/48kHz PCM与模拟硬件效果不能由本模块的软件差分代替；反之，逐帧字段也不证明 Native 内部执行了某条特定指令。
