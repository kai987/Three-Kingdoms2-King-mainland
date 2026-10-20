# 第7阶段：global4战术AI主控制器、可读决策和战场提交

本阶段补上了原ROM的global4战术AI调用：完整可达决策控制图、若干独立高层玩法算法，以及提案消费中的真实内存前缀/后缀。新增源码不调用原ROM执行器，也不替图形、消息或手柄等待制造完成信号。原ROM只读，SHA256为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

当前模块矩阵有 **9,806次原ROM CPU对照、255项源码非法域guard，0失败**；统一GameEngine另有 **43次原CPU集成对照及1项原核心字段集成检查**。原Nestopia在已有原战场存档之后，接受普通输入自然运行700帧，观测到4次移动和AP24→10。上述CPU案例、非法域拒绝、视频帧及文件hash是不同证据域，分别计数。

## 三个新增源码层和统一接口

| 源文件 | 已恢复范围 | 明确边界 |
|---|---|---|
| [tactical_ai_control.py](../../source/recovered/tactical_ai_control.py) | A000/A02D全部可达bank8控制图，8项strategy、16项predicate、扫描、退却/资源/持续效果分支；2,213条独立IR | 完整有界决策控制图；不是逐周期NES仿真，也不执行行动动画/NMI |
| [tactical_decisions.py](../../source/recovered/tactical_decisions.py) | 独立可读actor扫描前/后缀、两轴贪心移动、AP报价、相邻攻击、最近目标前缀、完整B933持续效果 | 高层源码尚未覆盖全部8strategy编排、退却及补给策略；这些由完整IR控制器处理 |
| [tactical_exchange.py](../../source/recovered/tactical_exchange.py) | 原BEA6请求、BF01路由前缀、BF26坐标提交后缀、BF83 AP提交后缀、A51F持续效果请求 | 图形前序和其真实等待外置；不是整段NMI或完整行动渲染 |

[GameEngine](../../source/recovered/game_engine.py) 的 `tick_tactical_ai()` 直接运行A02D控制更新；`tactical_rules()` 和 `tactical_bridge_rules()` 共享同一个64K地址空间，分别返回可读决策及提交算法。`tick_global()` 的global4真实bank8/9 A000调用已接入恢复源码。原链为fixed31 E221→E87A→F24B→bank8 A000 (`4C 2D A0`)→A02D；E229的JSR真实返回E22C。桥接借用实际寄存器/SP和caller栈，使用 `seed_return=False`，不会向真实嵌套调用补写0200测试哨兵。

控制器的唯一外部CPU辅助F266由既有独立 `RuntimeServices` 完成。F266选择8000数据窗，保存主线程缓存DE并写E000；F25F保存的是NMI数据窗缓存E1。代码映射pair8/9，但本控制体可达代码全部在bank8。数据窗仍需真实当前页，以及A8/A9所指四项地图chunk描述；仅给城市ID不足以建立完整CPU上下文。

## actor扫描、握手和提案编码

| 原地址 | 已确认用途 |
|---|---|
| 6F8B | FF直接返回；1进入B933二阶段；其他原始byte进入actor扫描 |
| 6F8C | actor slot；有效活动单位域0..19 |
| 6F8D | status0方向、status1普通攻击目标、status2计略ID、status4退却目的地 |
| 6F8E | status2计略目标slot；移动时不得把残留值当攻击目标 |
| 6F8F | 0移动、1普通攻击、2计略、3本次无行动、4退却；二阶段FF表示未应用 |
| 6F92/6F93 | AI随机cursor/保存X的scratch |
| 6F94 | 下一扫描slot |
| 6F95/6F96 | 本扫描status3次数/已尝试的合格actor次数；均保留u8回绕 |
| 6F97 | 移动提案费用，后续由战场提交阶段扣除 |
| 6FA1[20] | strategy整byte；FF跳过，低4位在已证明的8项表内分派 |
| 6FB5[20] | 工作数组；移动段保存反向方向，并复制到2F，当前A60C段未用2F判定 |
| 6FC9[20]/6FDD[4] | 候选/排序工作区和上、下、左、右邻居 |

A02D先递增6F94，再跳过strategyFF、异侧符号和officerIDFF。合格actor递增6F96并写6F8C。strategy返回status3时递增6F95继续扫描；其他结果立即写6F8B=FF并返回，交上层消费提案。扫描到20，两个计数不等就清6F94/95/96重扫；相等才返回status3并清cursor。源码保留真实重扫和预算停止，不把自造的不收敛输入改成成功。

bank12 BEA6在0087符号位满足原条件后写phase0请求；BEBA等待6F8B=FF。BF01的真实状态路由表为 `[3,5,8,12,13]`，分别对应移动、普通攻击、计略、结束本方行动、退却。phase7提交源码只恢复指定内存边界；旧 `BattleStateMachine` 继续负责其余行动/消息流程。

AP报价、提案、坐标提交及AP扣除是不同阶段：A740报价不扣AP；A60C写方向/费用；BF26在真实图形前序之后改单位坐标并处理Y=15缺口；BF83按u8减6F97，再设置battle主4/sub2。源码后缀不能用来声称前序图形任务已完成。

持续效果请求来自移动state4/sub3 A51F：等待6F8B==FF，写1并将0509写入6F8C；下一次global4执行B933。A535等待回到FF，仅status0进入效果提示。这条请求链由真实原指令建立；700帧自然片段尚未观测phase1。

## 8项strategy入口及实际决策次序

以下是依据原字节的现代行为说明，未给8项策略编造正式菜单名称。完整可达指令、分支、字段写入和helper调用见 [state-catalog.json](controller/state-catalog.json)、[all-entries.md](controller/all-entries.md)、[control.asm](controller/control.asm)。

| ID | bank8 CPU / ROM文件偏移 | 原代码可确认的编排 |
|---:|---|---|
| 0 | A0B1 / 100C1 | 先AF0D退却判定、AAF8特殊计略。0504非负随后直接基础计略A95C；负侧还先检查相邻攻击、基础计略，失败后用AI随机低2位决定status3或向slot0坐标贪心移动 |
| 1 | A105 / 10115 | 先退却/特殊计略；AP>=2时检查四邻是否有对侧首槽0/10并提议普通攻击，否则向对侧首槽坐标或A1E5城市坐标数据移动 |
| 2 | A166 / 10176 | 先退却/特殊计略/相邻攻击；以actor为中心radius2取第一最近敌候选并靠近；无候选转对侧首槽或城市坐标数据 |
| 3 | A210 / 10220 | 先退却/特殊计略/相邻攻击；以本侧首槽0/10为中心radius2选择敌候选；检查其四邻友方槽后选择基础计略或靠近；无候选尝试基础计略再靠近本侧首槽 |
| 4 | A2AD / 102BD | 先退却/特殊计略/相邻攻击；以actor为中心radius3取第一最近敌候选并靠近；无候选尝试基础计略，再靠近本侧首槽 |
| 5 | A329 / 10339 | 向城市6-byte特殊坐标表第一点移动；原服务索引0已有资源买卖证据。预计下一步命中该点时保留高nibble、把strategy低nibble置7，并按双方0522/0526资源word、城市原报价数据执行补给/交易算术 |
| 6 | A507 / 10517 | 向同表第三点移动；原服务索引2已有体力治疗证据。预计命中后strategy低nibble置7；检查侧资源word>=50、扣50、抽0..10加35治疗，byte加法回绕后才按初始record体力封顶 |
| 7 | A606 / 10616 | 直接写status3并返回 |

策略表位于A0A1..A0B0，只有8项；A09C的AND0F不证明8..15合法。计略predicate表ACAE..ACCD有16项；24个合法B517索引全部核对，非法策略8..15和predicate16..255仅做源码guard，不运行原表外代码。

status2的计略ID使用前阶段已由原菜单/CHR确认的16项名字：火計、陥穽、虚兵、要撃、乱水、火箭、偽撃転殺、共殺、籠絡、落石、連環、十面埋伏、水攻、連弩、劫火、奇門遁甲。对应证据是 [tactics16.png](../names_terrain/tactics16.png) 及既有 `game_enums.py`。status0的0..3是方向编码，不能套用计略名称。经过AAF8/A95C选择入口不等于成功status2施放。

## 高层算法必须保留的字节行为

A60C不是一般路径搜索：只报价朝目标的两个轴方向，较大位移优先，位移相等垂直优先，成本相等保留该次序。目标和单位的差使用SBC/BPL字节符号，不能替换成不回绕的整数abs。相同XY时，原代码仍可能保留向下方向；这属于原算法行为，不能修成“不移动”来通过验证。四邻有重复单位坐标时，第一个有效slot胜出；最近距离相等也保留第一候选。需要占位攻击fallback时，检查的是完整strategy byte恰等于1或5，高nibble标记会改变结果。fallback先写攻击目标再检查AP，最终status3仍可能留下改变的6F8D。

A7AA/A7AF连续读officer byte8，第一轮减59h后第二轮再次读取同一byte、带carry减2。成本表选择实际是byte8<3用第二表，其余用第一表；不是完整兵数阈值，也不是player的063C百位缓存规则。两张7×4表和原affinity3零成本编码保留。报价的u8 AP减法、carry和NZVC已按原CPU核对。

B933保留缓存组0/4与B965读取组索引Y而非actorY的特殊行为。半径候选为0也拒绝，actor地形必须0。原IQ差+10和第一次接受的0..100随机值随后被覆盖，但这组抽样仍消耗cursor。作用量由第二组0..10抽样及整个packedbyte11的带carry字节倍率计算；不简化成10×经验等级。扣兵只处理10位，officer byte9上6位原样保留。

另补的[缓存生产—消费证据](secondary-origin.json)确认B933至少读取由计略11「十面埋伏」建立的缓存：C004识别ID11→C1AF写0543=11→B02B的B042表第11项B42A，按本侧组0/4写04D8槽号、04D9/DA坐标、04DB=5并扣100兵；B933读取相反侧的同一组。这个静态关联补足孤立地址的名称来源，不证明所有缓存生产者均是该计略，也不增加自然phase1或成功施放的整机证据。

## 差分矩阵、静态来源和动态覆盖

| 独立模块回执 | 原ROM CPU cases | 源码guards | 比较范围 |
|---|---:|---:|---|
| [controller/validation.json](controller/validation.json) | 7,113 | 248 | 全2KiB RAM、8KiB SRAM、A/X/Y/P/SP/PC和物理PRG banks |
| [decisions/validation.json](decisions/validation.json) | 2,038 | 4 | 完整8KiB SRAM及0020..002F、042C..042E；有效报价另核对A/X/Y/NZVC |
| [exchange/validation.json](exchange/validation.json) | 655 | 3 | 全2KiB RAM、8KiB SRAM玩法写入；排除CPU寄存器/flags/stack和图形前序 |
| 模块合计 | **9,806** | **255** | guards不混入原ROM案例 |

决策2,038例分为1,728完整routine和310明确前缀/后缀；不是全部完整global更新。提交655例含原BF01路由前缀以及已完成前序后的BF26/BF83后缀。所有相关代码、数据偏移、原bytes、hash、前置输入和终点均在各目录回执列出。

完整控制器2,213条IR的原字节来源全部吻合；本控制器矩阵动态执行 **1,315/2,213条**，另 **898条未动态覆盖**。28个公布入口和所有合法表索引均通过，不等于全部分支动态通过。高层算法的714个执行地址不直接加成完整控制器动态覆盖。实际原F266 CPU执行仅在验证Oracle；游戏源码使用恢复的服务，不通过ROMfallback返回结果。

[统一集成回执](source-integration.json)另外检查43次完整CPU路径：13个原核心checkpoint直接调用、相同13个checkpoint通过global4桥接、8策略×2个受控AP上下文的16例、1次记录的原CPU调用/共享栈路径。第44项把原核心第一次移动坐标/AP字段与源码提交后缀对齐；只比较声明玩法字段，排除图形前序、实际NMI/IRQ和动画。集成44项不混入上述9,806模块矩阵。

## 原核心自然片段与单列同步CPU实验

[运行证据](runtime/evidence.json) 导入已有原 [attack-intro-7.state](../runtime/phase3/attack-intro-7.state)，通过下12、松35、右12、松35、A2、松300、A2、松302，共700帧普通输入选择「たいき」。没有RAM/SRAM注入，也没有补写readiness/ack；这验证原存档之后的片段，不声称从冷启动完整运行至此。

| 原核心frame | 已观测字段 |
|---:|---|
| 431 | global4/NMI3，phase0请求，AP24；该原RAM/SRAM用作单独同步CPU输入 |
| 432 | controlFF、actor1、direction3、status0、cursor2、无行动计数1、尝试数2 |
| 485/486 | slot1 (17,17)→(18,17)，下一阶段AP24→21 |
| 507/508 | (18,17)→(18,16)，AP21→18 |
| 519/520 | (18,16)→(19,16)，AP18→15 |
| 540/541 | (19,16)→(20,16)，AP15→10 |
| 551/563 | status3结束扫描；随后side回128、round2、AP26 |
| 665..700 | 原玩家回合消息继续等待输入；没有完成整场自然战斗 |

自然片段只观测phase0/FF及成功status0移动。**phase1、B933作用、成功status2计略尚未在该自然原核心片段观测。** 截图证明实际显示和移动结果；内部策略、cursor及提案机制还须由原RAM/SRAM和指令证据判断。

单独的 [cpu-call/validation.json](runtime/cpu-call/validation.json) 使用frame431原数据，由py65执行实际A000→A02D并压入显式E22B返回word，执行 **8,243条原CPU指令、636个不同指令起点**，回到E22C。该实验不是从保存的native PC逐条续跑，也不是Nestopia逐指令录制。其8个提案/扫描字段与下一完整core frame432相同；没有宣称全部RAM/视频/栈与下一帧等价。1次CPU调用和8个字段比对均已按同一行为域处理，未重复增加案例数。

两次完整核心回放的700帧字段日志一致；13个checkpoint的PNG/RAM/SRAM/state共 **52项非空文件hash** 相同。独立CPU调用重复的轨迹/RAM/SRAM为 **3项**，合计 **55项产物一致性检查**，独立于CPUcase与帧数。VRAM memory-id3的13个空导出排除在有效文件检查之外，PPU/mapper原状态保存在native `.state`。试探材料保留，但不加入正式计数。

## 可复现命令

在工作区根目录执行；原ROM始终只读。CPU用既有py65环境，完整核心用system Python/Pillow和已固定hash的Nestopia dylib。

```sh
.venv-trace/bin/python scripts/analyze_tactical_ai_control.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_ai_control.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_exchange.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase7_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase7/runtime/natural-turn-repeat --compare analysis/phase7/runtime/natural-turn
.venv-trace/bin/python scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --mode cpu --out analysis/phase7/runtime/cpu-call
.venv-trace/bin/python scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --mode cpu --out analysis/phase7/runtime/cpu-call-repeat --compare analysis/phase7/runtime/cpu-call
python3 scripts/verify_phase7.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

各receipt固定ROM、源码、IR/data和fixture hash。后续聚合脚本可以重新检查当前文件与这些pins；它不把静态来源、受控fixture、自然原核心观察合并成“完整游戏全部验证”。
