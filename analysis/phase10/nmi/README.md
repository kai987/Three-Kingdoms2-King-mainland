# 第10轮：可读 NMI / IRQ 编排、PPU 与输入固定服务

[battle_nmi_services.py](../../../source/recovered/battle_nmi_services.py) 独立复原 bank31 的 `$F800` NMI 前序、9 项场景调用计划、`$FAD5` 忙重入、正常尾部记账和 RTI，并恢复 PPU 工作队列消费者、双手柄输入、OAM 尾隐藏、CHR / PRG 切换及完整 `$FB2D` IRQ 软件分派。它不执行原 ROM 指令，不解释控制 IR；ROM 只作为不可变数据供原 IRQ 延迟表等读取。

最终 [validation.json](validation.json) 为 **3,451 个原 CPU 对照、119 个单列边界检查，0 失败**。比较完整 2 KiB RAM / 8 KiB SRAM、A/X/Y/P/SP/PC、PRG 映射、显式端口读写顺序和 PPU 命令字节。8 段原字节范围共 **2,969 字节**存于 [evidence.json](evidence.json)，对应 [原汇编](original-ranges.asm)。这些是软件 / 寄存器合同验证，没有新增 Nestopia 整机帧、像素或 PCM 证据。

## NMI 的实际流程

入口 `$F800`（文件 `$03F810`）保存 A/X/Y，读取 `$2002`，按 `$0068/$0069` 写 Namco IRQ 计数请求，并将 `$0069→$0062`、`$0061→$0060`。随后 CLI，设置四个 nametable bank 请求，再检查 `$007B` 忙标志。

正常路径按 `$E1/$E2/$E3` 切换 PRG 窗口，写 OAMADDR=0、忙标志=1、DMA page=2、PPUMASK=`$008C`，清 `$007C` 后按 `$0078&15` 选择场景。源端只允许原指针表可证明的 index0..8；9..15 保持显式依赖，不读表后指令当成地址。144 种合法 masked alias 的表边界由既有全局证据证明，本回执不重复将它们算成整机帧。

正常尾 `$F88D` 递减忙标志，按 `$DE/$DF/$E0` 恢复主线程 PRG 窗口，递增 `$0050/$0052/$0054/$0055` 四个 RNG 游标和 `$005E/$005F` 16 位计数器，最后恢复 Y/X/A 并 RTI。忙重入先运行 CHR / scroll / nametable 固定服务，另外保存 `$E3/$E2/$E1`，切音频 pair14/15 并调用 A003，恢复 Namco 地址选择与三个 PRG 窗口，等待 IRQ，直接恢复寄存器 / RTI；**不执行正常 RNG / 计数器记账**。

OAM DMA 请求发生在本次绘图服务之前，捕获的是当时 RAM `$0200..$02FF`；后续 OAM 修改不能被报告成同一时刻已上传的像素。服务总线记录 DMA 请求和字节，不制造实际 PPU 时序。

## 九个场景的调用计划

`$F87B..$F88C` 是 9 个指针、8 个不同入口；index0/1 共用 `$FA97`。完整源调用 / bank / 端口顺序保存在 [scene-call-plans.json](scene-call-plans.json)，包含九个正常场景以及两条忙重入计划。下表列场景特有的主要 banked 调用，固定前后也按原顺序执行：

| index | 原入口 | 主要 banked 调用与条件 |
|---:|---|---|
| 0 / 1 | FA97 | 无 banked callback：FB0B、F206、E6C6、FF62、FB28 |
| 2 | F8B5 | 音频 logical2E A003；logical3D A003 / A009 / A00F / A03F；logical3B A000 |
| 3 | F8FE | 音频2E A003；`0500<12 且008F=0` 时 logical37 A00C / A00F；logical39 A00F；logical2C A000；logical3D A003 |
| 4 | F96A | 音频2E A003；logical2E A000 普通攻击场景 controller |
| 5 | F9A0 | 音频2E A003；logical37 A01B 单挑 controller；logical3D A003 |
| 6 | F9E4 | 音频2E A003；logical2A A003 |
| 7 | FA13 | 音频2E A003；logical3D A003；logical28 A024 |
| 8 | FA53 | 音频2E A003；清新按键0081；logical3D A003；再读双手柄；logical37 A01E ending controller |

logical selector 的低 6 位按原 PRG 窗口协议写入，例如 2E→physical14/15、2C→12/13、37→23/24、3D→29/30。源调用保持真实 JSR 返回栈、传入寄存器和当前 data window；不会以 RAM `$DE` 冒充入口数据银行。需要 controller 的场景必须提供真实 callback，未提供时停止在该服务入口。

## PPU 工作队列与固定服务

**E6C6 是双手柄输入，E70E 是调色板上传；两者都不是音频 tick。**真正帧音频入口是 logical2E pair14/15 A003，具体音频模块由独立音频源码处理。

| 入口 | 已恢复的原软件行为 |
|---|---|
| E6C6 | 写4016 strobe1→0，交替读4016/4017八次，按 `(sample&3)>=1` 的 carry 旋入0083/0085；0084/0086保存旧输入，0081/0082为新按键边沿 |
| E70E | 设置PPUCTRL水平增量，清007D，上传0100..011F的32个palette字节，按原序重写2006地址 |
| EC67 | 原palette fade计数 / 饱和字节减法；改0100..011F并写007D请求，下次消费时才上传 |
| F206 | AE..B5八个CHR选择字节按8000 / 8800 / … / B800的原顺序写入 |
| EAF7 / FB0B | 原scroll两次2005、PPUCTRL低位更新；E6..E9四个nametable bank写入；BIT2002等待bit6清除 |
| FF62 / FF9B | 根据0097/0098准备0099..009B与EA/EC的原split地址数据；两个入口保留不同写入范围 |
| E830 | 从007C起每4字节仅隐藏OAM Y字节，写F0；FF sentinel直接返回；非4倍数游标保留原非终止循环依赖 |
| F237 / F24B / F25F / F266 | 所有256个原selector的bank/shadow/flags/栈协议；source不把selector预先夹成physical bank |
| FAA9 / FABF / F077 | 双手柄交换及scroll变化标记，包含原scratch / PHA字节写入 |

`EE53` 每次最多消费一项：先看007D非零，否则从007E最高 bit7 到 bit0 取任务。无任务也走 **E70E palette upload**，不是音频分派。

| 007E bit | 原目的地址 | 固定消费者范围 |
|---:|---|---|
| 7 | EF0B | 30字节tile列；按原header计算跨界分段，保留byte计数下溢行为 |
| 6 | EF71 | 32字节tile行；跨行分段和2006地址重置 |
| 5 | EFC0 | 8字节attribute列；地址每次加8 |
| 4 | F028 | 8字节attribute行；跨界分段 |
| 3 | logical3D A00C | 清bit3后真实tail callback |
| 2 | logical3D A006 | 清bit2后真实tail callback |
| 1 | logical3D A012 | 清bit1后真实tail callback |
| 0 | logical3D A000 | EE53本身不清bit0，具体消费者仍是callback依赖 |

bit7/6 保留原 PHA / PLA 对 A 和栈的影响；`EEE6` 只检查 bit7..4，其无任务路径直接返回。4 个 bank29/30 消费者本轮未冒充已恢复，只验证 15 个严格原指令前缀和 bank / queue / stack 边界。

## IRQ 与真实等待恢复

IRQ `$FB2D`（文件 `$03FB3D`）也保存 A/X/Y，读取 `$5800&127`。若不等于127，原程序进入 `$FB3C` 自循环，不会再次读取计数值；源端保留这个不可由后续样本释放的依赖，绝不补写 ready。

`$0060` 的0..12有13个原分派位置，其中1/3共享入口；13..255走原停止计数后缀。全部256个原byte mode、4个`$0063`行状态已对照。中间IRQ按6A起的计数行重新arm，切换四组CHR，递增 / 清零0063，部分路径改变0060后直接RTI；最终显示 / 停止路径执行SEI，实际写0062=0、5000=0、5800=0后才恢复 / RTI。C700等原镜像写保留其实际地址和顺序。

`FB28` 检查软件标志0062；非零保持依赖。10条原CPU完整链验证了 `NMI等待 → 显式接受IRQ → 原IRQ软件操作 → IRQ RTI → NMI恢复 → NMI RTI`，含总共4/5次IRQ、经过中间CHR切换后才到最终清除的序列。没有为NMI等待直接赋0062=0。IRQ调用的时间由验证器显式给出，`$5800=127`也是明确硬件输入；**这些链不证明实际扫描线、CPU周期或IRQ计数时钟**。在IRQ尚未回到暂停NMI的PC/SP时，源resume仍保持依赖。

## 接口、callback 与复现

```python
from source.recovered.battle_nmi_services import BattleNMIServices, NMIRegisters
from source.recovered.service_memory import ServiceMemory

# Hardware samples/buttons must come from an explicit caller contract.
memory = ServiceMemory(rom, ram, sram, banks=(6,12,13,31),
                       read_ports={0x2002: status_samples, 0x5800: counter_samples},
                       controller_buttons=(pad1, pad2))
services = BattleNMIServices(memory, callbacks=actual_services)
result = services.run_nmi(NMIRegisters(pc=interrupted_pc, sp=sp, p=status),
                          hardware_entry=True)
```

`hardware_entry=True` 明确复原**已接受中断**的PC / P压栈前序，不生成NMI/IRQ信号，不建CPU周期时钟。`False` 则要求caller已经提供真实硬件中断栈。`run_irq()` 同样处理已接受IRQ的软件主体；`run_service(entry, registers)` 则要求既有真实JSR返回栈。寄存器保持6502软件状态表示，B/U常量位按独立CPU oracle的可观察状态比较，不把B称为物理寄存器锁存位。

`callbacks(ServiceCall)` 接收 `target / return_pc / kind / registers / memory / entry_banks / expected_sp`。callback须实际执行其服务，只有PC和SP到真实caller才继续；dependency / failed / budget或未返回均停下。`resume()` / `resume_nmi()` 重试同一边界。每个对象保存一个活跃中断上下文；真实嵌套NMI或IRQ使用另一个对象，共享memory与当前registers，子中断RTI后再resume原对象。新增完整原CPU对照证明了活跃NMI的banked服务边界被忙NMI打断、忙路径RTI、原caller随后完成；不会覆盖原生成器帧。缺少PPUSTATUS或手柄样本可由caller显式供应后resume；不会制造按键、图形完成、音频完成或IRQ完成标志。

验证器的7个完整banked场景与2个忙重入案例使用 **verification-only 原CPU callback**；61次真实外部函数执行另列在回执内。生产源码没有调用原CPU。这证明固定源编排与真实外部服务组合后的合同；不能把它写成“所有banked图形 / 音频都已经独立源码化”。没有使用stub callback。场景0/1不需要banked callback，可由已恢复固定源码加显式端口输入完成；其他controller可由根任务已有真实控制器或服务模块接入。

在工作区根目录：

```sh
.venv-trace/bin/python scripts/analyze_battle_nmi_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_nmi_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

回执的3,451原CPU对照分为：640固定函数、65合法OAM尾、272固定PPU队列、128扩展手柄原样本、15banked队列严格前缀、1024 mapper selector、1024 IRQ mode / row、256纯固定scene0/1 NMI、7实际外部callback正常NMI、2忙重入、7严格callback暂停 / 真执行恢复、10 IRQ恢复链、1真正嵌套忙NMI后继续原caller。119边界检查单列：112个越界masked scene、3缺失输入后显式供应、1 PPU bit6等待、1原IRQtrap、1原OAM非终止循环、1 IRQ尚未RTI时禁止提前恢复NMI。原ROM不可变，当前来源及依赖hash固定在回执中。
