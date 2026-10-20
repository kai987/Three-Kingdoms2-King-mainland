# 原核心计略施放与十面埋伏触发

两条受控原核心流程已完成：AI实际提出并部署ID11「十面埋伏」，随后玩家普通移动进入范围，原代码扣532兵、给施放者增加266经验，真实A键确认后清缓存槽；另一次玩家普通菜单施放ID2「虚兵」成功，AP扣4，目标条件码变3。

这些是从保留原战场存档开始的 **controlled fixtures**。原ROM只读，未注入成功结果、已部署缓存、请求返回、图形完成或确认字段；所有部署、效果、消息、经验和清除由原ROM代码生成。单位坐标、合法统计数值、AI启用与补给等起点准备逐地址列在回执中，不能称为自然战役可达性或整场战斗完成。

ROM SHA256为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。[脚本](../../../scripts/capture_tactical_effects.py)保存固定普通按键、完整原核心state、PNG、RAM/SRAM和逐帧字段。[汇总manifest](evidence.json)区分原核心、独立CPU调用及到期前缀，供本轮门户读取。

## 十面：真实status2、部署、移动和确认

父存档为 [attack-intro-7.state](../../runtime/phase3/attack-intro-7.state)。它已经处于原战场单位菜单，本脚本不重新执行reset到出征。准备共6个RAM字节和6个SRAM字节：

| 准备 | 原值→新值 | 原字段域与用途 |
|---|---|---|
| 0617：slot3 Y | 13→17 | AI武将167移动至(20,17)，实际地图class0；X仍20 |
| 060A／061E：slot10 X／Y | (2,16)→(24,17) | 玩家武将131置于合法空格class0；之后实际普通左移 |
| 050C：敌方保留AP | 24→10 | 原合法余额；让十面部署后仍走真实后续AI决策和等待 |
| 0524／0525：原回合资源word | 0→9999 | 父存档值0会在CD78扣减后走CDB0/CEAB败退路径；准备合法非零word使原收尾继续 |
| 6FA1..6FA3：slot0..2策略 | [0,2,3]→[FF,FF,FF] | 原inactive编码；单位仍存在，只有AI扫描跳过这些策略 |
| 6B9A／6B9B：武将167经验 | 1000→3500 | 原12字节记录+6/+7的u16经验 |
| 6B9F：武将167 packed byte11 | 12→32（hex） | 经验等级编码高nibble1→3，原低nibble2保持；并非把展示等级写成3 |

武将167的原知93、兵700、HP40保持原值。他属于原特殊计略白名单；等级编码3、AP10、actor地形0、当前方缓存为空满足ID11选择条件。目标玩家地形0不满足优先ID10的水地条件，原AI可继续选ID11。RNG初始状态原样保留，没有准备随机结果；原图形、ROM和消息队列未改。

[完整回执](ambush-chain/validation.json)列每个准备的CPU地址、old/new和说明；[按键计划](ambush-chain/input-plan.json)由普通「たいき」换边、真实A确认计略公告／结果、普通两次左移和真实A确认陷阱消息组成。2962帧与2962个帧结束字段都已保存。

| frame | 原代码生成的字段／阶段 |
|---:|---|
| 431 | AI提案status2、action11、actor3；cache仍空 |
| 506 | battle主8/sub8、真实C004→C1AF入口待部署；兵700 |
| 507 | 原B02B/B42A建cache[3,20,17,5]，施放者rawLE16兵700→600 |
| 508 | 回原battle主0；该AI专用ID11路径AP10→10，绕过普通C01E扣AP |
| 1030 | 原完整回合收尾产生cache TTL5→4，玩家方side128／round2 |
| 1837..1838 | 玩家第一次左移至(23,17)，范围外，兵仍1000 |
| 2460 | 玩家第二次左移至(22,17)；battle主4/sub3、cache[3,20,17,4]、兵1000、AP16 |
| 2461 | B933效果完成，兵1000→468，report042C..042E=[14,02,00] hex即532；cached167经验此时仍3500 |
| 2462 | 下一个NMI战斗消费阶段A535..A5BB完成：cached167经验3500→3766，玩家131经验仍1000 |
| 2760 | 原PPU消息已完成，显示敌方陷阱和兵减少532人；cache尚未清 |
| 2761 | 普通A键确认后原A5F5清缓存slot为FF，坐标20/17和TTL4保持 |
| 2962 | 返回battle主0/sub2；玩家兵468、经验1000，施放者经验3766 |

其中两次玩家移动的活动AP为26→21→16；这是玩家移动扣款。不能把AI部署AP未扣理解为玩家ID11也免费，玩家施放的费用由另一入口处理。触发经验也分两段：B933伤兵阶段不加经验，后续原战斗消费给缓存武将加 `floor(532/2)=266`。不能以伤兵帧或玩家记录不变推断整条链没有加经验。

![原AI status2提案的整机画面；具体ID与status读取对应RAM/SRAM](ambush-chain/status2-proposal.png)

![原PPU陷阱效果消息，兵减少532人](ambush-chain/trap-message.png)

截图不单独证明ID11、cache内容或经验算式；这些由原字段、原表／代码绑定和独立CPU执行共同支持。十面部署走AI专用入口时没有单独的计略公告画面；不把相邻的原ID5公告当成十面名称图。ID5是在部署之后原AI提出的另一计略，本样本经过真实A确认并返回失败结果，玩家兵在陷阱前仍1000。

## phase1在同一帧内被消费

2962个原帧结束样本没有捕获6F8B=1。原A51F在NMI中写1与actor0509，原global4随后在同帧执行A000/A02D→B933并返回FF，所以native2460是FF、native2461已经FF。不能把这两个帧结束状态标成录制到了phase1中间值，或称为Nestopia原生指令轨迹。

[独立CPU回执](cpu-call/validation.json)使用 **实际生成缓存之后** 的 `trigger-before.state`／RAM／SRAM：先在显式pair12/13下执行原A51F前缀至A534（RTS前停止），记录其真实写入1；随后切换显式pair8/9，从原A000执行到真实原caller地址E22C。两段原CPU代码共1249条指令，记录请求 **FF→1→FF**，12个声明字段与native2461相同，包括兵rawLE16／low10、报告532、cache、AP、battle主/sub与RNG cursor。

该调用不从保存的native PC恢复；原代码银行上下文和A000 caller栈种子明确列在回执中。没有替换helper或成功结果，也没有生成NMI/视频/音频/IRQ。它证明请求和B933的原协议以及声明字段parity，不能当作同一完整视频帧内每条实际指令的录制。指令数1249、12字段和1个同步CPU对照case分别计数。

## 普通菜单「虚兵」施放

父存档为 [battle-tactics-true.state](../../runtime/phase3/battle-tactics-true.state)，已经是原计略选择菜单。准备2个RAM坐标字节及5个SRAM统计字节：目标slot1由(17,17)移至合法class4格(5,16)，施放者131知89→99、经验1000→15000、packed byte11由16→76 hex（保持低nibble6），目标191知31→0。等级、原表数值和坐标均在记录域内，但这些并非自然培养过程；没有改计略ID、结果、条件码、AP、RNG或消息确认。

普通下键选择原菜单ID2「虚兵」，普通右键定位目标，真实A键确认施放。原核心动画和效果流程1206帧已完成：frame747为AP16／目标0651=0／0544=FF，frame748原代码生成AP12／0651=3／0544=0。目标兵仍800，施放者经验仍15000。frame1004原PPU显示目标暂时不能移动的成功消息，之后真实A返回战场。

![原虚兵目标确认画面](ordinary-cast/cast-confirmation.png)

![原PPU虚兵成功消息](ordinary-cast/success-message.png)

[普通施放回执](ordinary-cast/validation.json)、[检查点](ordinary-cast/checkpoints.json)和[逐帧字段](ordinary-cast/frame-fields.json)保留完整输入及状态。这个case是玩家实际选择并施放，不是AI status2提案；不能合并两种入口费用和成功判定。

## 到期验证单列为CPU前缀

原核心只观察了一次真实完整回合的TTL5→4，然后效果被踩中并确认清除，没有观察五个完整视频回合的自然到期。

[到期CPU回执](cpu-expiry/validation.json)取实际原B42A生成的 `deploy-after` 缓存，连续执行原bank9 CE20..CE3F五次，均在RTS之前停止，保留逐指令轨迹。TTL顺序5→4→3→2→1→0，最后仅slot变FF，坐标仍20/17；全部SRAM保持不变。这是5次原CPU计时前缀、87条实际指令的到期契约检查，外层月份／回合、供给、UI及硬件均未执行，不是5个完整视频回合或新增独立源码差分矩阵。

## 重复、非空导出与计数

| 域 | 检查范围 | 两次一致的非空文件 |
|---|---|---:|
| [十面原核心](ambush-chain/repeat-validation.json) | 2962帧、16检查点、原部署→移动→经验→确认 | 67 |
| [虚兵原核心](ordinary-cast/repeat-validation.json) | 1206帧、8检查点、原菜单→动画→效果→返回 | 35 |
| [同步请求链](cpu-call/repeat-validation.json) | 1 CPU field-parity case、12字段、1249指令 | 3 |
| [到期前缀](cpu-expiry/repeat-validation.json) | 5原计时前缀调用、87指令；源码差分case数0 | 3 |

两类原核心的全量逐帧字段日志也分别逐字节一致。总108项重复文件hash检查不是108个CPU案例，也不并入4168视频帧。24个空libretro memory-id3 VRAM导出明确标为available=false、bytes=0并排除；原PPU/mapper可在各非空native `.state` 内复查。各case额外保存未推进帧的prepared初始RAM/SRAM/state，这三个非空文件也计入一致性检查，不把旧父截图称为准备后的新画面。

`exploratory-*` 目录是试探材料，未加入正式计数。初版试跑的父补给word0导致原败退；未采用跳过收尾或写结果来修复。正式流程准备该word9999并由原代码继续正常回合。所有普通A确认都是手柄输入，没有人工ack/readiness。

## 复现

在工作区根目录执行。完整核心需要当前pinned Nestopia dylib、system Python的Pillow和保留父存档；CPU需要已有py65环境。

```sh
python3 scripts/capture_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/capture_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase8/runtime-repeat --compare analysis/phase8/runtime
.venv-trace/bin/python scripts/capture_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --mode cpu
.venv-trace/bin/python scripts/capture_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --mode cpu --out analysis/phase8/runtime-repeat --compare analysis/phase8/runtime
```

可用 `--case ambush-chain` 或 `--case ordinary-cast` 单独复现；输出根目录下仍使用该case子目录。native原存档绑定此核心hash，不声称物理NES硬件验收或完全独立可玩重制。
