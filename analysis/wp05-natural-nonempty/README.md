# WP05 · 自然非空mode2战后分配

**本工作包已完成有界验收。** 新窗口实际生成非空名单，将武将67写入城市16第4个武将槽，并沿原调用栈返回BB39。完成后停止，等待父级评估；未启动WP06/08或下一阶段。

## 本次新增

| 项目 | 实际结果 |
|---|---|
| 输入/范围 | 从冻结32 day30第7610帧末态导入；172帧松键、A2、松键180、A2、松键27，共383帧，至旧路线7993 |
| 原模拟器复跑 | 原固定核与新被动核各两次独立进程：4fresh、383首跑帧、1532总控制帧 |
| 完整缓冲 | 每实际帧RAM/SRAM/RGB/PCM/full serialized state逐字节一致，不归一化；3461项非空产物复跑检查 |
| 原始观察 | 首观察运行265872事件、122完整2K/8K软件快照；独立复跑内容相同；溢出0 |
| 结果原写入 | local1 seq412，physical9:CF02实际STA0514，1→1，同值写仍明确捕获 |
| 非空收集 | local357，BDCD/BDF7生成[67,FF×20] |
| 名册写入 | local357 seq246991，physical8:BDB8，ptr6200/Y14(hex)，6214:FF→67 |
| dummy读取 | 前一seq246990同址6214读FF，是STA原dummy读，不当作字段逻辑消费 |
| 真实返回 | BD96/BDAA→BD91→BD95→BB39；SP EA→EC→EE，两层原始返回字及实际Push8留证 |
| 可选交换 | BE55实际执行Y0自交换，BE80/BE86两次67→67；不同槽位的非平凡交换未覆盖 |

完整断言见 [flow-validation.json](flow-validation.json)，原始事件、实际栈写和快照绑定见 [evidence.json](evidence.json)。源城16名单由[163,158,89,FF…]变为[163,158,89,67,FF…]。武将67原12字节保持484f4a545000e803e803281a；这是已有武将的战后归城分配。玩家131在local359由13:D4BA另写6171，随后同值写另列，未计入67分配。

## 来源与比较边界

母态内容链是31前五段80853帧＋冻结32前缀7610帧＝88463祖先单跑帧，排除后来segment07..10及141636帧duel母链。阶段14的零写入冷启、阶段22导入和相邻存档衔接另见 [祖先补充核验](ancestry-supplement.json)。本次四次均为导入态、0新增准备/内存写、无PC/ready/RNG/结果/名册注入；没有新冷启动或全战役fresh声明。

导入后、首次retro_run前，接口尚无RGB或音频回调；该边界只比较完整state及2K/8K，并记录RGB不可用、PCM为空。首个真实回调帧7611作为初始五缓冲视频边界，其后每帧五缓冲全量比较。软件快照不含即时N163/PPU/APU，不伪造初始图像。

终点global2/NMI2、city13/0，是全黑画面的城市调度/过渡边界；不宣称已回到可操作world0/1或完成随后city13事件。052C变化只由软件快照确认，本观察写域未捕获其BDB4总线写。完整原输入和捕获回执在 [runtime](runtime/evidence.json)；代表性原画面：[结算](runtime/natural-day31-nonempty/original-control/frame-00357.png)。

## 构建与交付

固定原核心SHA924191eb…a539a保持。新观察核SHAf886fefa…9b0a6，独立72u32 ABI；const backing快照、实际JSR/RTS/continuation与原Push8写记录。源码、官方commit、编译器、clean build、实际最终dylib链接及依赖重编逐字相同证明见 [构建回执](core-provenance/build.json)。初始v1构建未用于任何Native运行，保留为构建草稿；正式采用v2。旧32版本和哈希错配均未就地修复。

构建时点分开记录：初次旧builder完成clean/build，默认目标的依赖重编未证明最终链接；随后显式dylib目标实际重编并链接，完整二进制相同；当前builder是修订后的复现版本。初次v2 builder-at-run快照/hash未记录，保持null，没有倒填当前脚本SHA。源/补丁、真实链接、二进制和fresh运行等价证据独立成立。详见 [build-provenance-timeline.json](build-provenance-timeline.json)。

已有可读源码的函数与新证据对应见 [readable-source-map.md](readable-source-map.md)。本包Source案例0、独立字段CPU合同0、新玩法算法0；顺带保存的14份实际E066现场留待后续独立验收，不启动WP08。

最终只读校验见 [verification.json](verification.json)，输入/输出hash见 [input-manifest.json](input-manifest.json) 与 [artifact-manifest.json](artifact-manifest.json)。31全部91929依赖pins/596源码脚本pins、32全部2101残留及closure全部16文件保持不变。只有完整逐字比较之后才在新目录内硬链接去重；未重打历史大包，未包含或分发ROM。

字段账本仍1526=1201条件排除/80possible/245unknown，剩325；raw345独立，城市+1/+28..31正式名称仍null，整款闭包仍false。下一个建议包是WP02（B517当前JSR合同），此处只建议并停止，不自动执行。完成百分比、未知服务数、剩余轮数均null。
