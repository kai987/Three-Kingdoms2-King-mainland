# F8 资格与真实保存点的原 CPU 诊断

此目录执行原 ROM 的有界 6502 代码。起点来自原 Nestopia `.state` 中实际保存的 PC、SP、AXYP、MAP/PRG 银行与 N163 状态；不把 RAM 的银行影子当实际映射，不预置 PC、随机游标、请求、回复或文字完成标志。这里的 CPU 指令序列是独立软件继续执行，**不是原模拟器内部逐指令录像**。完整原模拟器接受、拒绝与重复证据属于 `../runtime/`；本目录不增加独立可读源码差分的案例数。

## 原字节中的三层选择

| 位置（physical10） | 原条件 | 继续 F8 的要求 |
|---|---|---|
| `A19C..A1BC` | `$52` 游标样本的低四位，依三个 byte 权重分派 | 选择 index1 的名册/人事策略；当前实际权重 `8,6,12`，样本须在 `8..13` |
| `B49C..B4A9` | `$55` 样本 `&127`，拒绝 `>=50` | 最终接受值 `<10`，进入 `B5FC` |
| `B5FC..B60D` | `$54` 样本 `&127`，拒绝 `>=90` | 最终接受值 `60..89`，进入 `B619` |

完整 NMI 在 fixed31 `F8A1..F8A7` 同时递增 `$50/$52/$54/$55`。所以不安排新中断的独立 CPU 前缀会保留自己的游标进度；它的样本不能直接冒充后续原模拟器帧内取样。`original-f8-selection.asm` 与 `original-ranges.json` 保存原 bytes、含 16B iNES 头的文件偏移及 SHA256。`A1BF..A1C4` 被明确导出为三个内联指针字，不误作指令。

## B619 的非随机门槛

该体先在全部己方城市的十个名册槽中选非君主、忠诚最高的使者（相同值选后者），要求至少三位非 `FF` 君主、己方四个外交 byte 的逐次清 carry 加法结果为零、至少两个相邻的外国 owner。它在这些邻方中选城市最多的一方（相同城数选后者），要求 `target_count > own_count + 2`。

当前原自然扩城背景中，己方 ruler4 只有城市2，目标人类 ruler1 已有四城，邻方为0与1；使者为 ID38、忠诚99，活跃君主7人，外交 byte 均为零。城市2金9929、粮9999，足够报价。不是因为资源或城数条件失败而没有生成 F8。

四个目标城市给 `q=(4*30+70)//10=19`。金报价 `4q=76`，粮报价 `6q=114`；完整 word 用于足够资源检查，但提交缓存 `$003A/$003B` 原样复制报价低 byte 与零 `$0431`，不修复这个原程序的截断。目标 controller **整 byte** 恰为3则本地解决，其他值才产生 F8 并进入 `B78B` 等待。只有真实消费者写回复0才接受，其他非 F8 值拒绝。

## 已解释的负窗口与正窗口

phase19 正式自然扩城 `AI-ruler4-status00-frame10405.state` 的无新中断前缀中：三策略样本12选择 index1，随后原样本 `168&127=40` 进入普通整理，没有到 `B5FC`。普通确认延迟36/40的探索保存点在同类独立 CPU 前缀中均取三策略样本5，先进入军事策略，没有到 `B49C`。这些是具体前缀的失败原因，不能概括为整个月份从未满足外交资格。

原模拟器最终以普通确认延迟73帧、零数据写入真实生成 F8。实际请求保存点为 `PC=B790, SP=FD, A=F8, X=4, Y=3, P=27`，实际银行 `16/10/11/31`；主体 ruler4/君主222，收件人 ruler1/君主8，使者38，粮报价114、接收 controller0。原 `E188` caller 的返回字 `87/E1` 留在栈内。原 CPU 从此实际 PC 执行三条指令回同一等待位置，全部 RAM、SRAM、N163、银行和寄存器不变；没有代写回复。

正式 `natural-F8-accept` 的四个真实前序保存点均可重新生成 `STA $6F8B=F8`：

| 实际保存帧 | 原 CPU 前缀指令数 | 与原 Native F8 帧全部8192B SRAM差异 | RAM差异 |
|---|---:|---:|---:|
| 10496（前4帧） | 9242 | 0 | 37 |
| 10497（前3帧） | 6640 | 0 | 17 |
| 10498（前2帧） | 3972 | 0 | 33 |
| 10499（前1帧） | 1296 | 0 | 32 |

最早保存点的独立原 CPU 前缀实际接受 `133&127=5` 进入次级分支，随后拒绝 `105`、接受 `72` 进入 `B619`；所有非随机门槛真实执行。`pre-F8-native-parity.json` 保留完整 RAM 差异，寄存器也不相等。这里没有安排新中断，因此不能把 SRAM 相同扩大为完整 Native CPU 或时间线相同。

`eligibility.json` 是正式真实上下文的选择与等待诊断；`pre-F8-native-parity.json` 对其中相同四个前缀做另一种观察，**不另加四个源码案例**。`actual-callers.json` 从前4帧的同一前缀导出八个实际 callable 输入，位于 `actual-callers/entry-{B619,B7A2,B837,B85F,B898,B955,D080,D307}`；各有完整 RAM/SRAM/N163 和现存真实返回栈。B619 前缀67条、SPFD、父返回 E188。输入导出同样不是八次独立源码验证，后续源码比较由各自正式验证器计数。探索目录不作为完整 Native 流程的验收依据。

## 复现

在项目根目录运行 `.venv-trace/bin/python scripts/trace_f8_eligibility.py ROM --state PATH`。对真实 F8 等待点或确实生成 F8 的前缀加 `--require-F8`；用 `--compare-post-state NEXT_STATE` 比较一个未准备的前缀与后续真实帧，完整保留 RAM/SRAM 差异。默认输出为 `analysis/phase20/cpu/eligibility.json`。硬件读输入固定声明为 PPUSTATUS0、APUSTATUS0、Namco IRQ 读127、两手柄无键；没有新安排的 NMI/IRQ。未知硬件、真正等待和预算边界均保留。

例如完整 producer 前缀及可移植真实 caller 输入可复现为：

```sh
.venv-trace/bin/python scripts/trace_f8_eligibility.py '/Users/paulasmith/Downloads/三国志2超级版.nes' \
  --state analysis/phase20/runtime/natural-F8-accept/F8-previous-4-actual-frame.state \
  --capture-callers analysis/phase20/cpu/actual-callers --require-F8 \
  --out analysis/phase20/cpu/actual-callers.json
```
