# 第十轮：战斗呈现服务——图形、音序与 NMI/IRQ

本轮把已恢复的计略玩法接到独立的图形请求、计略动画、文字队列、音序驱动和 NMI/IRQ 软件服务。新增模块**不执行原6502指令，不解释控制IR，也没有原CPU回退路径**；读取的是原ROM的数据表、文本数据命令、图块和音序数据。此前提升为IR的战斗/单挑等控制器继续保留自己的接口，不能把新增服务的独立实现范围扩大为整个工程。

请先打开[交互证据页](index.html)：可选择10个正式场景、切换前后检查点，并试听完整回放或施放/结果片段。源代码入口见[源码说明](../../source/README.md)、[GameEngine](../../source/recovered/game_engine.py)及[共享呈现服务](../../source/recovered/battle_presentation_services.py)。原ROM全程只读，SHA-256仍为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## 独立源码及其实际范围

| 模块 | 已恢复的软件行为 | 来源与回执 |
|---|---|---|
| [battle_graphics_services.py](../../source/recovered/battle_graphics_services.py) | 完整bank13 D6CC地图刷新请求、D657光标、DC63/DC70高亮、固定OAM构造；physical25 A00F→26 CFD6的16项计略动画 | [说明](graphics/README.md)、[原字节/数据](graphics/evidence.json)、[对照](graphics/validation.json) |
| [audio_services.py](../../source/recovered/audio_services.py) | 固定E57F reset、连续音序请求包装、physical14 A003→15 D8D4的11槽驱动；APU/N163/mapper寄存器写序 | [说明](audio/README.md)、[原字节/数据](audio/evidence.json)、[对照](audio/validation.json) |
| [battle_nmi_services.py](../../source/recovered/battle_nmi_services.py) | F800完整软件前序、9场景调用计划、FAD5忙重入、正常尾部与RTI；EE53固定PPU消费者、输入、OAM尾隐藏、CHR/PRG切换、FB2D IRQ软件主体 | [说明](nmi/README.md)、[调用计划](nmi/scene-call-plans.json)、[对照](nmi/validation.json) |
| [text_services.py](../../source/recovered/text_services.py) | bank29文本生产/PPU消费、32个合法文本数据命令80..9F、数字/姓名/城名、演员面板、地图命令消费及真实readiness | [原字节/数据](text/evidence.json)、[对照](text/validation.json) |
| [service_memory.py](../../source/recovered/service_memory.py) | 共享RAM/SRAM与只读PRG窗，显式端口读输入和有序写请求、可检查的PPU/N163寄存器图与OAM DMA请求 | [整合对照](source-integration.json)；这是服务总线，不能产生硬件时钟或完成信号 |
| [tactic_presentation_effects.py](../../source/recovered/tactic_presentation_effects.py) | 复用16项独立玩法算法，补上它们实际的银行调用/恢复协议、地形数据访问与死亡刷新续程 | [整合对照](source-integration.json) |
| [battle_presentation_services.py](../../source/recovered/battle_presentation_services.py) | 上述服务与GameEngine共享内存；玩家battle5/sub5..10的确认、动画后效果、报告、升级通知及光标返回主体 | [468项接口对照](source-integration.json) |
| [scroll_graphics_services.py](../../source/recovered/scroll_graphics_services.py) | physical23 A00C→A387的tile行/列滚屏、A00F→AB53的attribute滚屏；原camera缓存/拼缝/单位覆盖及PPU任务请求 | [说明](scroll/README.md)、[15段原范围/5张表](scroll/evidence.json)、[完整返回对照](scroll/validation.json) |

滚屏两入口生成tile列/行与attribute列/行请求，保留camera索引、8/16/32像素拼缝、四象限chunk切换和单位覆盖。tile路径会先更新camera缓存再检查007E忙位；attribute路径不会套用该busy检查。源返回原body A/X/Y/P及caller RTS之前的SP，不合成PPU像素或假消费任务。32,768项完整CPU对照覆盖31,104项camera/方向/重叠、1,536项busy/cache顺序、128项连续调用；连续fixture中明确提供队列忙位输入，不是源码自动完成队列。

图形D6CC建立 `0380..038E` 的15字节命令并设置 `007E|4`，它没有同时把图块写到PPU。光标和高亮修改OAM RAM，实际DMA请求由NMI另行发出。16项计略映射到11种visual class；每条完整验证序列包括15次准备返回和176次动画返回，**191次服务调用不是191个原核心视频帧**。动画确实按原计数清 `04C8`，没有直接注入ready。

音频使用183个原描述符、11个优先级槽和8种logical channel，恢复tempo、duration、volume slide、vibrato、envelope、note/rest、循环和优先级处理。其输出是寄存器请求，未合成PCM。E6C6是4016/4017双手柄读取；E70E是palette上传，二者都不是音频tick。真正NMI音序调用为logical2E、physical14/15 A003→D8D4。

文本80..9F是游戏的数据命令，不是6502/控制IR。生产缓冲、队列、PPU消费以及 `DF27` readiness分别执行；后者要求 `0304` 和 `0300` 都为FF。仅结束脚本、排队命令或收到软件CALL返回，不能被写成已显示完画面。

## NMI/IRQ 的完整软件前后

源端恢复了F800保存A/X/Y、读取显式PPUSTATUS、设置Namco IRQ计数请求、切换PRG/nametable、OAMADDR/DMA/PPUMASK请求和清OAM计数，随后按 `0078&0F` 分派。原表只有**9项、8个不同入口**，index0/1共用FA97；9..15不会被当作合法指针读取。九场景的真实调用地址、bank和条件见[调用计划](nmi/scene-call-plans.json)。

正常尾F88D恢复主线程银行，递增四个RNG游标及16位计数器，恢复寄存器后RTI。FAD5忙重入另行执行固定CHR/scroll/nametable和音序服务，恢复被打断银行，等待IRQ，再RTI；它不执行正常尾RNG记账。OAM DMA使用请求当时的0200..02FF，不把后续OAM更新倒算为已经上传的像素。

IRQ有13个原分派位置，全部256个原mode与4个row状态已对照。0062等待只在真实恢复的IRQ最终服务写0后才能继续，**不自动清ready**。`5800&127!=127` 的原自循环、非法OAM游标的原非终止循环及缺失端口输入均保留显式边界。10条完整CPU链验证 `NMI等待→明确接受IRQ→原IRQ软件操作→IRQ RTI→恢复NMI→NMI RTI`，但不证明扫描线/CPU周期或Namco计数时钟。

`hardware_entry=True` 表示caller明确给出已经接受的中断，源码复原PC/P压栈；它不生成NMI/IRQ信号。嵌套中断使用独立服务对象并共享当前内存和寄存器，子中断真实RTI后才恢复外层。未知场景controller仍需callback，未提供会停在具体入口。callback必须维持真实返回PC/SP、传入寄存器和bank上下文；没有默许成功的空函数。

## GameEngine 的连接方式与合同

`GameEngine.from_snapshot(..., mapped=True, service_io=...)` 使用 `ServiceMemory`。`service_io` 可明确提供 `read_ports` 样本序列、需重复的 `repeat_read_ports` 与两个 `controller_buttons` 字节（bit0 A..bit7 Right）。未提供的硬件状态读取会明确报依赖；这些输入不能被当作源码已经产生的硬件状态。

- `game.presentation_rules()` 返回共享的 `BattlePresentationServices`，含 `graphics/audio/text/effects/nmi/irq/scroll`。
- `services.player_tactic_body()` 执行battle5/sub5..10的精确主体入口AA2E/AA6C/AAA7/AB2A/AB52/AB90；不替外层控制器选择计略，也不是视频帧推进器。
- `game.tick_nmi_services(registers, hardware_entry=..., external_callback=...)` 执行完整已恢复NMI编排；`services.resume_nmi()` 恢复同一等待边界。
- `game.tick_irq_services(registers, hardware_entry=...)` 执行已接受IRQ的独立软件主体。

默认callback只连接已识别的独立音序、文字、动画、滚屏和基础图形服务。未知controller继续返回dependency；可由其实际拥有者提供callback，不能以该接口存在推断所有场景都已独立完成。文本和动画的临时A/X/Y/P不在它们的语义合同，集成层明确保留此限制，不能把它们无条件当作旧精确CPU控制IR的等价寄存器hook。

[接口回执](source-integration.json) 共**468项原CPU对照、4项单列源码边界检查，0失败**：32项菜单确认、128项全16效果/死亡刷新、192项结果扫描/演员面板、96项确认/升级音序/完整光标返回、12项完整NMI，以及8项滚屏callback完整回返。比较声明的玩法RAM、全部8KiB SRAM、bank和端口写序；计略主体排除CPU scratch/栈，滚屏callback另比较返回A/X/Y/P。12项完整NMI比较返回寄存器，运行的是scene0/1或忙重入所到达的独立软件callback，**原CPU callback次数为0**。不把这12项扩大为九个正常场景controller全部独立运行。4项guard另检查源输入域、未知controller保持真实caller栈，以及半行文本缺PPUSTATUS时暂停、真实续程返回且不重复PPU写入。

地形银行协议另有[40项定向回归](terrain-validation.json)和2项源码guard：24项RAM descriptor与16项只读ROM descriptor的完整DB46调用。源必须先在进入时的真实数据窗读取chunk，再执行切窗；不能在E000已改变后重读旧descriptor。比较返回地形值、声明RAM/全部SRAM、bank及写序，不宣称源X/Y/P/SP/PC合同。ROM descriptor是明确的类型fixture，不能当成实际地图观察；无效chunk120/255拒绝之前可能已有pair选择端口写入，guard不保证原子回滚。

## 原CPU对照与统计边界

以下数字来自各最终回执；guard是源码接口/域拒绝检查，不是执行原CPU的案例。

| 对照域 | 原CPU对照 | 单列guard | 实際边界 |
|---|---:|---:|---|
| [图形](graphics/validation.json) | 4,596 | 4 | 全部完整服务返回；含16动画连续序列3,056次调用 |
| [音序](audio/validation.json) | 15,857 | 4 | 15,856次完整返回，另1例真实B0循环budget前缀 |
| [NMI/IRQ/固定PPU/输入](nmi/validation.json) | 3,451 | 119 | 完整服务、严格前缀、显式等待及IRQ恢复分别计数 |
| [文字](text/validation.json) | 893 | 7 | 声明的队列/缓冲/port合同；83项来自原快照的CPU fixture，不是新增83个整机帧 |
| [滚屏](scroll/validation.json) | 32,768 | 2 | 全部完整返回；声明的1,940B RAM、8KiB SRAM、AXYP/body SP/映射/端口写序 |
| 五模块小计 | **57,565** | **136** | 全部0失败；音序循环前缀与NMI严格前缀/等待另列，不能称全为完整返回 |
| [统一接口](source-integration.json) | **468** | **4** | 不并入主体模块，不与原核心帧或像素字段混计 |
| [地形descriptor定向回归](terrain-validation.json) | **40** | **2** | 完整DB46；与前两项统计独立，不扩大为完整地图值域覆盖 |

图形普通helper比较A/X/Y/P，但动画最终临时寄存器、SP/PC及大部分自由栈残余排除；palette0100..011F与01B0..01B3是真实数据，明确比较。音序比较AXYP、caller RTS之前的body SP及完整有序写端口/N163寄存器图；源码不自行弹出callerframe。文字排除算术scratch、临时寄存器和栈。NMI模块比较全2KiB RAM、全8KiB SRAM、AXYPSPPC、PRG映射及端口读写顺序。各模块不同合同不能合并成“所有CPU临时状态皆等价”。

NMI模块的完整banked场景验证使用**61次验证器专用原CPU callback**，回执另列、没有stub callback。它们只证明独立NMI编排与真实外部机器码组合的协议；生产源码没有执行这些原CPU callback。上述统一接口的12项完整NMI则由已恢复的独立源码服务完成，两种证据有不同范围。

静态原字节、执行地址、不可变数据与源码/验证器hash保存在每个模块 `evidence.json` / `validation.json`。有限动态覆盖不等于全部值域、曲目时长或每条图形分支已经穷尽。

## 原 Nestopia：真实 RGB 与 48kHz PCM

本轮将第九轮的10个受控 `initial.state` 和普通手柄输入计划原样重放，**新增核心内存写入0、新增输入事件0**。准备的武将、数值、坐标及3例RNG游标保持公开；不是自然campaign、完整自然battle或源码重制的视频。没有写已选计略/成功结果/动画完成/cache/ack来代替原服务。完整母档、旧→新准备和计划见[原核清单](runtime/evidence.json)及[回放说明](runtime/README.md)。

两次原核心共**37,618帧**，每次18,809帧；首跑83个检查点。**392份非空canonical产物双跑hash一致**：332份PNG/RAM/SRAM/state，20份WAV，40份正式JSON。其中332份检查点原生文件还与第九轮逐字节相同。含不同输出目录的83份snapshotJSON不作canonical一致声明，83个空VRAM导出明确排除。

10份完整WAV首跑累计**15,022,464个左右声道样本对**，48,000Hz、16bit stereo，等于30,044,928个单声道标量样本和60,089,856字节PCM；两跑完整样本对为30,044,928。10份 `cast-and-result.wav` 是完整音频裁片，与完整WAV重叠，不重复累加总样本。每帧PCM段和每次libretro audio callback均有按原WAV字节核验的hash。[重复及音频回执](runtime/validation.json)与每例validation/repeat-validation链接可直接复查。

`frame-services.json` 记录原RGB/RAM/SRAM/PCM hash、global7A、NMI78、battle500/501、AP、tactic543/result544、动画04C8、文字0300/0304/0310、PPU jobs007E、NMI busy007B和IRQ pending0062；音序RAM0700..07FF与palette0100..011F保留原hex。它是帧末观测，**没有Nestopia内部CPU指令trace，原核回执的source_CPU_cases为0**。同帧置位/消费不可从帧末0值否认，原CPU同步对照也不能冒名为原核心内部指令跟踪。

真实PNG/PCM证明原核心在这些受控输入下推进画面、动画、文本、声音和返回；PPU/APU/N163的时序及波形合成仍由原核心完成。独立服务只恢复软件算法/队列/寄存器请求，当前工程仍不是独立运行的NES重制版。

## 历史偏移元数据更正

第九轮部分冻结的 `executed-instructions.json` 中，`rom_offset` 使用了PRG数据起点而漏加16字节iNES头。读取这些旧执行清单时应加 `0x10` 才是文件偏移；bank、CPU地址、指令字节和原CPU对照结果不受影响。此处只更正历史列含义，**不改写冻结文件或旧hash**。本轮新原字节证据使用包含头的文件位置：`file_offset = 0x10 + physical_bank*0x2000 + (CPU_address & 0x1FFF)`，必须先明确该CPU窗的物理bank。

## 复现

在项目根目录，py65验证使用已配置的 `.venv-trace`；普通原核心捕获/证据页使用具备Pillow的 `python3`：

```sh
.venv-trace/bin/python scripts/verify_battle_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_audio_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_nmi_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_text_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_scroll_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase10_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase10_terrain.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/capture_service_flow.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
python3 scripts/build_phase10_browser.py
```

原核心捕获会重放全部正式场景并写新回执；检查已保存证据不必再次运行它。证据页生成器只读取已有文件，核验hash、WAV、PNG和链接，不执行玩法公式、原CPU或控制IR。
