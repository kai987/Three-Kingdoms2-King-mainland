# 原完整核心：第10轮图形、音频与服务状态回放

从第9轮10案已披露的 `initial.state` 和完整普通按键计划原样重放，仅观察原Nestopia的RGB与PCM输出。本轮没有新增核心内存写入或输入事件。武将ID、数值、坐标与三个RNG游标准备全部继承前轮受控起点，**不是自然战役流程**；旧/新字节逐案链接保存在 [evidence.json](evidence.json)。ROM不可变。

两次原核心回放均通过。首跑 **18,809帧**、两跑 **37,618帧**、**83检查点**；**392份非空canonical产物**双跑逐字节hash相同，其中332份PNG/RAM/SRAM/state还与第9轮原文件逐字节相同。20份WAV与40份正式JSON另纳入重复检查。83份包含不同输出路径的snapshotJSON不作重复一致声明；83个空VRAM导出明确排除。

10份完整回放音频累计 **15,022,464个stereo sample frames（左右声道样本对）**，即30,044,928个单声道标量样本、60,089,856字节16bit stereo PCM，采样率48,000Hz。两跑完整PCM样本对总数30,044,928。10份施放/结果excerpt来自完整音频裁切，覆盖片段重叠，不能再加到完整PCM总数。每帧PCM段及每个libretro audio callback的hash均按原WAV字节重新验证。

| 正式场景 | 计略 | 帧数 | 检查点 | 双跑产物 | 完整PCM样本对 | 秒 |
|---|---|---:|---:|---:|---:|---:|
| [tactic-01](tactic-01/validation.json) | 陥穽 | 1715 | 8 | 38 | 1369745 | 28.536 |
| [tactic-05](tactic-05/validation.json) | 火箭 | 1809 | 8 | 38 | 1444821 | 30.100 |
| [tactic-07](tactic-07/validation.json) | 共殺 | 1856 | 8 | 38 | 1482359 | 30.882 |
| [tactic-08](tactic-08/validation.json) | 籠絡 | 1856 | 8 | 38 | 1482359 | 30.882 |
| [tactic-09](tactic-09/validation.json) | 落石 | 1809 | 8 | 38 | 1444821 | 30.100 |
| [tactic-10](tactic-10/validation.json) | 連環 | 1856 | 8 | 38 | 1482359 | 30.882 |
| [tactic-12](tactic-12/validation.json) | 水攻 | 1903 | 8 | 38 | 1519897 | 31.665 |
| [tactic-14](tactic-14/validation.json) | 劫火 | 1997 | 8 | 38 | 1594974 | 33.229 |
| [tactic-01-death](tactic-01-death/validation.json) | 陥穽 | 1715 | 8 | 38 | 1369745 | 28.536 |
| [tactic-09-levelup](tactic-09-levelup/validation.json) | 落石 | 2293 | 11 | 50 | 1831384 | 38.154 |

每案 `full-flow.wav` 包含完整菜单、施放及返回音序；`cast-and-result.wav` 是effect-before前30帧到result-message的原PCM片段。它们来自 **原Nestopia**，不声称已复原源码合成了相同声波。

`frame-services.json` 逐帧记录原RGB / RAM / SRAM / PCM hash、global7A、NMI78、battle500/501、AP、tactic543、result544、动画04C8、PPU工作位007E、NMI忙007B、IRQ标志0062，以及0300/0304/0310文字队列原字段。0700..07FF音序RAM和0100..011F palette保留hex；不替未验证临时字段赋新语义，也不把队列字段当百分比。

这是帧末观测，**native_internal_CPU_trace=False，source_CPU_comparisons_in_this_receipt=0**。帧内置位/消费可能同帧完成，不能从帧末0值断言没有运行NMI或IRQ。PPU命令排队、同步软件CALL返回、实际PNG出现和PCM播放分别有自己的证据合同。源码CPU对照属于各graphics/audio/nmi/text/scroll回执，不并入本回放统计。

在工作区根目录复跑既有捕获器（不修改它）：

```sh
python3 scripts/capture_service_flow.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
python3 scripts/build_phase10_browser.py
```

母档、准备回执、核心版本、输入计划、raw文件、WAV、重复hash与排除列表均在各案validation/repeat-validation和本 [汇总回执](validation.json) 内。源码是寄存器/命令编排，PPU/N163/APU的物理时序与PCM合成仍由原核心完成；不扩大为完整硬件或整场自然战役验证。
