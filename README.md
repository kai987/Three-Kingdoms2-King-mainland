> **当前Web版：最多115城、每城30人、13个年代开局、千人属性齐全。** v11新增单向阴平险道、子午谷季节损耗、季风航速与海路探索，右栏显示势力钱粮和预备兵。[启动与玩法](game/README.md) · [险道与航海规则](docs/hazardous-travel.md)。运行 `python3 -I -S -B game/serve.py --port 8878`，打开 http://127.0.0.1:8878/ 。旧存档保持原规则，新规则需新开v11战役。
>
> GitHub源码与开发资料已整理：请先查看[仓库范围与使用说明](docs/repository-scope.md)。
>
> 最新交付：[96城地图 v42](expansion/map/README.md)、[地图与千人武将交互页](expansion/officers/index.html)、[候选名单与29项字段映射](expansion/officers/README.md)。候选人物1000位、姓名文本994种；净新增人数仍待原237人的身份对照。
>
> 下文保留原阶段说明。第18至31轮的文档及WP工作包另见`analysis/`；完整原机证据、封存ZIP、ROM及工具链在本地保留，不随Git提交。历史音画链接可能依赖这些外部资料。工程尚未成为独立可运行的完整游戏。

# 三国志2超级版：整体逆向分析工程

**第十七轮已更新：**补全玩家无候选后的势力退出与败亡结局：单人A软件重启，双人按原开局模式交另一玩家继续，原B退出负例和死亡曹操仍被名册接受的边界均有原模拟器证据。6,973项原CPU对照通过（5,307完成边界、5非局部重启、1,661严格前缀），另26项guard；原Nestopia三案双跑68,124帧、2,429份非空产物一致。城市+1确认错位16位门槛，+28..31仅确认显式无界扫描可别名访问，正式名称仍未决；合法十人名册的提名不会读尾。请看[本轮报告](analysis/phase17/README.md)、[完整源码与三组原流程](analysis/phase17/index.html)、[同一Session对照](analysis/phase17/source-integration.json)及[总审计](analysis/phase17/verification.json)。

**第十六轮已更新：**恢复真正的city13战后继承控制器、玩家败北后的选城/选君主、无候选势力退出月轮，以及年月图形、精确音频请求和忠诚桥。12,703项原CPU对照通过（12,442完成边界、261严格前缀），另54项guard。原Nestopia四案双跑35,162帧，1,076份非空产物一致。适性3已确认是三项表外读取和机器码字形，不能命名第四能力；城市+1正式名称及+28..31用途仍未决。无候选leaderFF后空城owner仍可保留。请看[本轮报告](analysis/phase16/README.md)、[五个源码域与原模拟器流程](analysis/phase16/index.html)、[24项整合对照](analysis/phase16/source-integration.json)及[总审计](analysis/phase16/verification.json)。

**第十五轮已更新：**确认月事件锁`6F06`、城市`+27`事件冷却及满名册覆盖边界，恢复精确音频caller栈，并新增同一战役Session的主循环/NMI/IRQ续程。新增4,841项原CPU对照及32项接口防护通过，严格前缀和真实完成边界分列。请看[本轮报告](analysis/phase15/README.md)、[三份源码与四组原核心流程](analysis/phase15/index.html)及[53项联合对照](analysis/phase15/source-integration.json)。原核心验证包括自然12个月跨年、同一实例连续出征/普通攻击/两次退却，以及明确准备的战后继承/无候选结算；自然和受控证据分别公开，城市未决字段及硬件合成边界继续保留。

**第十四轮已更新：**冷启动/软件重启及全局 main2 内政合作 AI、main4 战术合作 AI 已接入独立可读函数。重启在真实 E066/SPFF 边界退役旧 caller；原等待与未知服务保留。请看[本轮报告](analysis/phase14/README.md)、[四份源码与原模拟器完整音画](analysis/phase14/index.html)和[统一入口对照](analysis/phase14/source-integration.json)。原 Nestopia 三案双跑 41,316 帧，864 份非空产物一致：普通输入耗尽行动并完成六位 AI 君主月更新到189年2月，原retro_reset保留全部8KiB电池SRAM，标题演示超时走软件重启。硬件时序/波形合成仍依赖原核心，源码函数及前缀边界分别公开。

**第十三轮已更新：**城市16主态、内政/军事/物资/街市菜单、城市武将资料驱动，以及标题、君主选择、结局UI和真实全局主循环已接入可读源码。远端图形初始化、开场动画、新剧本SRAM初始化、商店报价和菜单算术由独立owner处理。请看[本轮报告](analysis/phase13/README.md)、[源码、原画面与完整WAV](analysis/phase13/index.html)和[统一城市入口对照](analysis/phase13/source-integration.json)。原Nestopia两条城市回放双跑6,200帧，204项非空产物一致，终点SRAM与自然起点相同；本轮回放未验证购买、内政执行或结束回合的效果。各源码的完整返回、严格前缀、栈范围及硬件边界分别记在回执中。

**第十二轮已更新：**补上独立肖像、姓名包、真正十行武将资料与保留AXYP/栈的精确文字caller。请看[本轮报告](analysis/phase12/README.md)、[原核心资料页/攻击UI和实际WAV](analysis/phase12/index.html)与[1,164项纯源码攻击集成](analysis/phase12/dependencies/source-integration.json)。四模块19,425项原CPU对照（19,423完整、2真实循环前缀）及28项guard通过，生产无原CPUfallback。原核心两流程双跑5,830帧、200非空产物一致，本轮无新增core内存写入；资料完成使用info-open(frame272)，历史名info-rows-complete(frame31)只是继承旧FF。此前阶段11肖像依赖已由新owner解除，其26项集成当前全部完整返回；其它未恢复菜单与硬件合成边界继续保留。

**第十一轮已更新：**将战场16主态、普通攻击11主态、单挑22主态和真实NMI外层还原为具名Python函数，补全global3/5/7初始化、编队/AI配置、31组战场背景行与真实PPU消费。七个新模块通过 `SceneCoordinator` 与同一GameEngine/ServiceMemory连接，生产不解释IR或执行原ROM；未知服务仍明确暂停。请看[本轮报告](analysis/phase11/README.md)、[三条原核心回放与实际WAV](analysis/phase11/index.html)和[统一入口26项CPU对照](analysis/phase11/source-integration.json)（25完整返回、1肖像依赖前缀，另7项guard）。原核心双跑22,870帧、387份非空产物重复一致；已有起点fixture来源公开，没有本轮新增core内存写入，硬件帧/PCM合成仍依赖原核心。

**第十轮已更新：**新增独立图形/16项动画、文本队列、音序驱动及完整NMI/IRQ软件编排，与16项计略和GameEngine共享内存连接。请先看[本轮报告](analysis/phase10/README.md)、[图形与音频交互证据页](analysis/phase10/index.html)及[468项接口对照](analysis/phase10/source-integration.json)。新增服务不执行原6502或控制IR；10个受控原核心场景双跑共37,618帧，392份非空canonical产物hash一致，提供真实RGB及48kHz stereo PCM。PPU/APU/N163时序与波形合成仍靠原核心，未知场景controller仍是明确依赖。

**第九轮已更新：**补齐陥穽、火箭、共殺、籠絡、落石、連環、水攻、劫火八种计略，覆盖全部16项效果、玩家目标资格、成功判定及死亡/升级后的结算。请先看[本轮报告](analysis/phase9/README.md)、[交互式证据页](analysis/phase9/index.html)和[可读源码](source/README.md)。原Nestopia核心完成10个受控施放/结算场景，首跑18,809帧，两次回放362份非空产物完全一致；独立模块4,267项原CPU对照、统一入口1,421项原CPU对照及12项原核心字段核对通过。此前十面埋伏、八策略和自然AI行动证据保留。

上一轮的主要武将属性、战斗与AI计算结果见 [第二轮报告](analysis/phase2/README.md) 和 [237条解码属性](analysis/officer_fields/officers-decoded.csv)：57,031个函数级CPU对照样本通过，C11库另有14,080个与Python对照。

这份工程已对所提供的 ROM 完成**整体结构调查、全部原始字节与图形提取、关键代码和数据表恢复**。使用的是指定的 [morluto/rea](https://github.com/morluto/rea) 项目，并在本地补了 6502 原始映像适配，通过真实 Ghidra 后端取得汇编、伪代码和 REA Evidence。

**这不是完整原始源码恢复，也不是已经重制好的游戏。** 全部字节已保留且可一致重建；已恢复有边界的战斗/普通攻击/单挑、全局及战术AI控制图和八策略的完整玩法编排。16项独立计略效果，以及图形/音序/文本/固定PPU/NMI/IRQ软件服务已恢复到各自声明的边界；三类战斗场景控制、初始化及已列出的肖像/姓名/武将资料已进一步独立源码化，城市与全局UI控制正文已在第十三轮进一步恢复；冷重启与两个合作AI主控已进一步源码化；部分未动态覆盖分支、边界事件及字段正式语义仍有缺口。完整视频帧、PPU/APU/N163时序及PCM合成仍依赖原核心。下文保留第一轮调查数据，新增源码与字段解释以第二至第十七轮报告为准。

## 先看这些文件

- [第十七轮玩家无候选与城市字段报告](analysis/phase17/README.md) / [完整源码与三组原流程](analysis/phase17/index.html) / [同一Session对照](analysis/phase17/source-integration.json) / [总审计](analysis/phase17/verification.json)。

- [第十六轮实际战后继承与适性报告](analysis/phase16/README.md) / [源码与四组原流程](analysis/phase16/index.html) / [联合对照](analysis/phase16/source-integration.json) / [总审计](analysis/phase16/verification.json)。

- [第十五轮字段与长期战役报告](analysis/phase15/README.md) / [四组原流程与三份源码](analysis/phase15/index.html) / [联合对照](analysis/phase15/source-integration.json) / [总审计](analysis/phase15/verification.json)。

- [第十四轮冷重启与合作AI报告](analysis/phase14/README.md) / [三条原流程和可读源码](analysis/phase14/index.html) / [联合入口对照](analysis/phase14/source-integration.json) / [总审计](analysis/phase14/verification.json)。

- [第十三轮城市与全局UI报告](analysis/phase13/README.md) / [完整音画和可读源码](analysis/phase13/index.html) / [原CPU整合回执](analysis/phase13/source-integration.json) / [总审计](analysis/phase13/verification.json)。

- [第十二轮UI报告](analysis/phase12/README.md) / [原核心两流程与WAV](analysis/phase12/index.html) / [精确攻击集成](analysis/phase12/dependencies/source-integration.json) / [总审计](analysis/phase12/verification.json)。
- [第十一轮场景控制报告](analysis/phase11/README.md) / [原核心三流程音画](analysis/phase11/index.html) / [严格组合回执](analysis/phase11/source-integration.json)。
- [具名场景源码与统一API](source/README.md#第十一轮具名场景控制器和真实初始化)：既有caller栈、独立服务owner、真实等待与未恢复依赖。
- [第十轮呈现服务报告](analysis/phase10/README.md) / [前后画面与实际WAV](analysis/phase10/index.html) / [原核心重复回执](analysis/phase10/runtime/validation.json)。
- [独立呈现服务源码说明](source/README.md#第十轮独立呈现服务与显式硬件输入)：GameEngine、计略银行协议适配、图形/文本/音序与NMI/IRQ共享服务。
- [可浏览的分析入口](analysis/index.html)：237 条武将记录与姓名图联接，支持 ID/已转写名字/原始字节筛选。
- [全部图形浏览器](analysis/assets/index.html) / [237 张姓名图](analysis/assets/names/index.html)。
- [代码和数据的详细中文报告](analysis/game_data/README.md)。
- [REA 导出的固定银行伪代码](analysis/rea/mcp/fixed-bank-pseudocode.c) / [函数索引](analysis/rea/mcp/procedure-index.json) / [完整证据包](analysis/rea/mcp/evidence-bundle.json)。
- [启动执行说明](analysis/trace/README.md) / [联合验证](analysis/verification.json)。
- [算法复原实现](source/recovered/game_algorithms.py)。
- [重建的 NES 文件](build/三国志2超级版.rebuilt.nes)：SHA-256 与输入一致。
- [逆向分析归档包](build/三国志2超级版-逆向分析.zip)：报告、CSV/JSON、资源、代码、适配补丁与重建 ROM。

## 输入身份和内存映射

分析日期：2026-10-14（Asia/Tokyo）。输入：`/Users/paulasmith/Downloads/三国志2超级版.nes`，全程只读。

```text
长度      524304 bytes = 16-byte header + 256 KiB PRG + 256 KiB CHR
SHA-256   26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82
header    4E 45 53 1A 10 20 32 10 00 00 00 00 00 00 00 00
格式      legacy iNES / Mapper 19 / battery flag set / no trainer
PRG       文件 0x000010..0x04000F
CHR       文件 0x040010..0x08000F
```

所有 ROM 文件偏移从文件首字节计数，**包含 16 字节头**；CPU 地址另用 `$xxxx` 表示。CPU 地址在切换窗口内时，必须同时给出物理 bank 和 mapper 状态。第九轮部分冻结执行清单的旧 `rom_offset` 列漏加16字节头，读取时须加0x10；[第十轮报告](analysis/phase10/README.md#历史偏移元数据更正)只更正该历史元数据含义，未改旧文件或验证结果。

| CPU 窗口 | 映射 |
|---|---|
| `$8000..$9FFF` | `$E000` bank 寄存器选择的 8 KiB PRG |
| `$A000..$BFFF` | `$E800` 选择的 8 KiB PRG |
| `$C000..$DFFF` | `$F000` 选择的 8 KiB PRG |
| `$E000..$FFFF` | 固定末页 bank31；文件 `0x03E010..0x04000F` |

本 ROM 有 32 个物理 PRG bank。代码中原始 selector `$30/$31` 等在本文件中别名为 bank16/17，日志同时保留原值与物理 bank。header 的 mapper 编号不能单独证明实际 PCB 型号；Mapper 19 的规范背景见 [NESdev Namco163](https://www.nesdev.org/wiki/Namco_163)。

## 代码发现

| 内容 | CPU 地址 | ROM 偏移 | 已确认行为 |
|---|---|---|---|
| RESET | `$E000` | `0x03E010` | `SEI; CLD`，禁用显示，等待 vblank，初始化 RAM/银行 |
| NMI | `$F800` | `0x03F810` | 保存/恢复状态，推进随机游标，提交 OAM，显示相关控制 |
| IRQ | `$FB2D` | `0x03FB3D` | 检查 mapper IRQ，分派 CHR/显示银行切换 |
| 主状态分派 | `$E066` | `0x03E076` | `state=$007A & $1F`，从 `$E07C` 读指针后间接跳转 |
| 跨银行调用 | `$EE07` | `0x03EE17` | 读取 JSR 后内联 `.word` 目标，切换 bank；返回 `$EE4D` 恢复 bank |
| 内联跳转表 | `$EADE` | `0x03EAEE` | 按 A 从 JSR 后指针表取目标，尾跳转，无普通 fallthrough |
| 第一记录寻址 | `$F2AF` | `0x03F2BF` | `$6000 + 32*A` |
| 武将记录寻址 | `$F2D7` | `0x03F2E7` | `$63C0 + 12*A` |

vector 表位于文件 `0x04000A..0x04000F`，其字节为 `00 F8 00 E0 2D FB`。

主状态指针表实际有 **15 项**，范围 CPU `$E07C..$E099`，后面立即是代码。`AND #$1F` 不能用来断言存在 32 项。状态目标为：

```text
0 E09A   1 E0DA   2 E17D   3 E18B   4 E221
5 E22F   6 E2E2   7 E2E8   8 E36A   9 E37C
10 E3EB  11 E3EE  12 E3EB  13 E46A  14 E3EB
```

[固定银行控制流 listing](analysis/disassembly/fixed-bank.asm) 由确认的入口及直接调用/跳转出发，得到 **1,420 条候选指令、3,390 个代码候选字节**，无解码重叠。它不是所有银行的完整控制流。REA/Ghidra 最终导出 **67 个候选函数**；银行外目标和内联调用约定尚未在 Ghidra 中全部建模，因此这些不是 67 个已人工确认的完整函数，生成的 `.c` 也不是可编译的游戏源码。

## 数据表与姓名

| 表 | 文件位置 | 记录数 × 大小 | SRAM 位置 | 结论 |
|---|---|---:|---|---|
| 第一表 | `0x020C10`，bank16 `$8C00` | 30 × 32B | `$6000` 起 | 城市结构及主要字段已由第五轮UI/读写路径确认；+1与+27..31仍有缺口 |
| 武将表 | `0x022010`，bank17 `$8000` | 237 × 12B | `$63C0` 起 | 武将身份及主要属性、装备、等级字段已确认，位字段限制见第二轮 schema |
| 姓名字形 | `0x022DC4`，bank17 `$8DB4` | 237 × 13B | 用 CHR/OAM 绘制 | 全部姓名图片已还原；未自动 OCR 全部姓名 |

初始化复制第二表时复制 2,880B，相当于 240 个槽；有效武将数是 237，最后三个槽已是相邻指针数据，单独放在 `copied_extra_slots.csv`，不计作武将。

237 张姓名图包含 214 个两字名、23 个三字名，共 497 个字形位置。四 tile 的原始 64 字节按 SHA-256 去重得到 318 种模式。直接观察的样本包括 ID0 阿会喃、ID2 伊籍、ID38 関羽、ID47 甘寧、ID55 姜維；其余保持图形形式，未凭近似 OCR 写入文字。

关羽 ID38 的 12 字节为 `61 61 54 63 58 00 E8 03 BC 02 2C 1A`。第二轮已确认前五项为 `体97、武97、知84、忠99、徳88`；`+6` 为经验 raw1000、列表显示20，`+8` 为兵700。保留第一轮 raw CSV 的字节列用于证据，同时另提供解码 CSV 和新版浏览器。byte5及部分状态/地形语义仍有推断项。

第一表六组 LE16 全部为 9999，部分单字节为 99/100。可以确认这份文件的初始高数值分布；由于没有原版 ROM 对照，不能精确归因哪些字节属于“超级版”补丁。

## 资源提取

CHR 的全部 256 KiB 已提取：64 个 4 KiB 展示分组，16,384 个 8×8 二位平面 tile。Mapper 的实际页大小为 1 KiB；展示分组不是硬件 bank 大小。已生成 706 个可解码 PNG，包括字库、名称与图形总览。

标题“超级版”、菜单文字、集中字库和士兵小精灵可从 tile 图直接看到；头像/地图区域仍标注候选。版权图形可读到 NAMCOT、RIGHTS RESERVED、1992，只能作为文件内图形线索。灰度是诊断配色，不等于游戏实际颜色；完整画面还需调色板、nametable、OAM 和 IRQ/CHR 银行状态。

## 验证结果与边界

- 全部 PRG/CHR 提取与原文件逐字节一致；97 个 `.byte` 分块重建 524,304B，SHA-256 与原 ROM 相同。
- REA 6502 适配构建成功；相关 27 个测试通过，`git diff --check` 通过。
- REA `inspect_native_load_image` 为 **verified**：bank31 的完整 8 KiB source、mapping、language、entry 与原始提取字节一致，零页/栈是 Ghidra 的未初始化块。
- 8 类复原算法共 **3,699 个样本**与实际 ROM 指令一致，另对静态 decoder 的全部 151 个官方 opcode 核对名称和长度。包括寻址、16/16 除法、24/16 除法、packed BCD、排列随机数、有界拒绝采样。
- 另 15 个用实际 ROM helper 与人工调用端构成的测试，验证跨银行调用返回、跨页边界、银行恢复及内联跳转表的尾跳转协议。
- 6502 同步启动模型执行 **51,045 条指令**，覆盖 bank23/29/30/31，观察到状态 **0→9→10**；未注入 NMI，在重复分派处结束。它不是整机 NES 仿真。
- 独立 SRAM 初始化 harness 从 bank30 `$DD8B` 调用，逐字节验证 960B 和 2,880B 复制。**不能把此隔离调用说成复位流程已实际执行它。**
- PPUSTATUS 使用人工交替值解除等待，恒零对照会停在首个 vblank 等待；没有真实帧时序、画面、声音或完整游戏流程验证。

完整性验证不代表完整语义恢复。第二/三/四轮已恢复主要武将字段、多段战斗/单挑计算、战斗AI及三层状态控制图；剩余包括少量位字段、第一表城市完整结构、外部helper、完整战役/内政AI、场景资源组合、音序/音色、存档与实际补丁差异。无原版输入时，补丁差异无法通过当前文件单独证明。

## REA 的本地适配及复现

上游克隆位于 `tools/rea`，基准 commit 为 `0043d9b134c0a353e8bf85c0bde4492275f1f720`，package version 6.4.0。原版 raw-binary 入口仅提供 x86/ARM；本地 [6502 适配补丁](analysis/rea/6502-adapter.patch) 补充 `6502:LE:16:default`、16-bit 映射边界和 Ghidra 零页/栈的加载验证。此补丁未提交到上游，不能声称上游已经支持 NES。

Ghidra 12.1.4 安装在 `.toolchain`，Java 使用本机已安装的 24.0.1。发行包缺少 macOS arm64 decompiler，因此用其附带源文件构建了 native component，记录在 `analysis/rea/ghidra-native-build.log`。没有改动全局 Codex MCP 配置；[MCP 脚本](scripts/rea_analysis.mjs) 建立并关闭工作区内的临时分析会话。

在当前工作区执行：

```sh
.venv-trace/bin/python scripts/analyze_rom.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/inspect_game_data.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --extract-tables analysis/game_data
python3 scripts/extract_assets.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --output analysis/assets
.venv-trace/bin/python scripts/verify_recovered_algorithms.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/rebuild_rom.py
python3 scripts/make_portal.py
python3 scripts/verify_analysis.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

REA MCP 分析（使用符合上游要求的 Node 24.18.0）：

```sh
/Users/paulasmith/.nvm/versions/node/v24.18.0/bin/node scripts/rea_analysis.mjs
```

Python 依赖为 `py65==1.2.0` 和 Pillow；`analysis/trace/requirements.txt` 及 `requirements.txt` 保留版本。`.byte` 重建只需 Python 标准库。

首次适配失败日志 `analysis/rea/first-import-failure.json` 保留了 Ghidra 默认零页块导致 `getMinAddress()` 不等于 ROM 基址的原因，随后已按实际文件映射修复。独立复查还纠正了“mask32即32条状态表”的推断；旧探索结果仅位于 `analysis/rea/exploratory`，不作为本报告结论依据。

归档包不含大型 toolchain/node_modules、Python 环境与旧探索结果；在新目录重跑 REA 需克隆上述 commit、应用补丁、安装锁定依赖并构建，然后提供 Ghidra。当前工作区已准备好。原 ROM 未被替换，也没有执行上传或发布。
