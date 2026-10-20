# 第9阶段：剩余八种计略、玩家资格与完整效果结算

本阶段补齐 ID1/5/7/8/9/10/12/14 的独立玩法源码。与第八轮已有八项组合后，**16项计略效果均有可读实现**，并补上完整16项玩家目标资格、结果提示、死亡后续、经验升级与第二提示的控制窗口。原ROM保持只读、重建ROM逐字节一致；真实图形、音频和文本/输入等待仍有精确调用边界。

请打开 [交互证据页](index.html)、[完整效果入口](../../source/recovered/tactical_effects_complete.py)、[三项单目标效果](../../source/recovered/tactic_individual_effects.py)、[五项范围/转换效果](../../source/recovered/tactic_area_conversion.py)、[玩家资格源码](../../source/recovered/player_tactic_targeting.py)。GameEngine 的 `tactical_effect_rules()` 现在返回完整16项效果；`player_tactic_targeting_rules()` 共享同一RAM/SRAM，分别处理玩家目标检查。

新增模块有 **4,267项原ROM CPU对照、31项输入/模块范围guard，0失败**；统一接口及结算另有 **1,421项原CPU对照、12项原核心字段核对**。完整核心10组受控实验包括八种实际施放、一次死亡、一次升级：首跑18,809帧、两跑合计37,618帧，83个检查点、362项非空产物hash和10份全帧日志重复一致。83个空VRAM导出不计有效产物。不同证据域分别计数。

## 八个效果的实际逻辑

| ID / 正式名称 / bank12入口 | 成功效果与结算 |
|---|---|
| 1 陥穽 / B0DD | 即时扣目标体力：`floor((等级编码 + ((武+知)&255)//10) * (5+draw0..2) /10)&255`，实际损失按现体力饱和。体力归零触发死亡分支 |
| 5 火箭 / B243 | 扣当前0504相反侧的军粮word0522/0524：`floor(原粮*(10+draw0..4)/100)+floor(施放者知/5)`，按现粮饱和，042C/D报告实际损失；没有本效果经验奖励 |
| 7 共殺 / B2CD | 先伤中心，再按左/右/上/下四邻伤敌；坐标查找采用最高槽号先匹配，随后检查敌方；每次命中独立抽伤害量，并按新的累计损失反复奖励经验 |
| 8 籠絡 / B31C | 专用忠诚/距离概率门槛；成功后C886增减双方byte计数，以目标武将兵数low10作为迁移量；双方总兵字段仍是完整16位word，0628符号翻转、清匹配缓存槽、策略FF↔4，再用新君主的徳调整目标忠诚。即时阶段没有城市名册/驻城/status改写 |
| 9 落石 / B3B6 | 先执行陥穽的体力损失，再执行B188兵损，最后substate=7。致死后原程序仍继续兵损阶段，读取已变FF的0664，F2D7(FF)定位6FB4工作区；源码保留这个内部行为 |
| 10 連環 / B3D0 | 从中心沿敌军连通图扩展，处理地形类3的候选。各目标抽0..1，状态0650写 `draw+3+bool(0504 & 0x80)，即末项加0或1`，最终substate=7 |
| 12 水攻 / B466 | 同一连通候选图，只处理地形类3；逐目标B1E3兵损，逐次累计和经验结算，最后substate=7 |
| 14 劫火 / B50C | 同一连通候选图，处理地形类非5候选；逐目标B55C伤害 `floor(知*(30+draw0..5)/10)`，逐次累计和经验结算 |

所有byte/word运算、记录别名、RNG游标、同址先后写入、byte9高6位的路径差异均依原程序保留。当前说明使用原等级编码，即packedbyte11的高nibble；它不代替游戏界面的等级显示。

B8A1的范围规则是可执行的连通搜索：中心无条件入队，按右/左/下/上扩展；每个格子从低槽号起找第一个敌方匹配，同槽不重复入队，地形类5阻断。共殺四邻则从高槽号向下找坐标，然后再筛敌方；重叠友军可以遮住低槽敌军。这些顺序不能替成固定半径、稳定排序或武将record去重。

兵损累计不是每个目标各自归零。B68B在每次命中后用新的042C/D累计值奖励 `floor(累计/2)` 经验；因此施放者可以获得多次累积奖励，等级或武力在中途改变后也会影响后续伤害。源码按实时记录重新读取这些字段。

## 玩家资格、AI选择和施放概率

这三层分别恢复：玩家AD80资格决定目标是否适用；AI使用自己的16项选择条件；效果体的B7BE或B72B才决定成功。AP费用又在玩家AA96或AI消费窗口提交，资格API仅报价。

- **落石：**玩家要求施放者地形类4/5、正交相邻、目标类不等于5；AI却要求目标类5。这是原代码的两套规则。
- **籠絡：**玩家资格仅排除目标地形类5，AI另要求忠诚低于50；真正施放时B72B对忠诚至少71或距离至少6直接失败，其他档位才抽样。
- **奇門遁甲：**玩家只排除目标地形类3/5，没有AI的武知/兵数门槛；其效果体在第八轮已经恢复。

[完整16项玩家规则表](targeting/README.md)包含原入口、返回carry、地形/邻居/原始兵word/缓存条件与AP表。`eligible(id)` 对当前050A/0509执行AD80；`can_target(id,actor,target)` 加入cursor敌方和距离小于6的前缀，ID11按原逻辑以自己为目标。同侧失败保留旧0509。API不制造手柄输入、不扣AP、不施放。

B7BE保留字节加法与最终符号检查：知差、等级差、距离修正及050F/6F02奖励相加后，若结果符号位为负会归零，再夹至5..95。原模拟器试验中的相邻落石，知差99、等级差12、距离修正10、人方奖励10，总和131使门槛变为5；最终成功场景将目标知设置为10这一合法输入，使总和121、门槛95。没有改概率函数或成功结果。目标适用并不保证施放成功。

## 死亡与升级的完整数据后续

B5D8在HP归零时将record byte11低位OR3，停止于真实同步D6CC地图刷新调用。实际调用返回后，far14 A009→bank15 D8B0按死者武+知的完整16位和奖励施放者经验，再far8 A02A→bank9 D6CD清六组战场数组、策略及首个匹配的整个4字节缓存行。0432保存死者ID。

这个死亡路径没有调用退却用的C91E队伍/总兵记账，也没有即时清城市名册；死者原兵word仍保留。源码与原核死亡场景均检查这些差异。落石随后继续读取FF伪record的行为在原CPU前缀/后续对照中验证，未声称在本轮原核场景里另做了落石致死。

`CompleteTacticalEffects.after_death_map_refresh(map_refresh_returned=...)` 只在真实同步调用已经返回后继续结算；False保持pending且不改RAM/SRAM。这个参数不表示异步PPU绘制已完成。玩家/AI外层费用、刷新selector和返回数据后缀保留各自调用路径；不再次扣费。

共用玩家流程已经可读化：AAA7等待007E，逐单位调用真实图形服务；AAB9完成20槽扫描后选择成功/失败/死亡消息；AB32在真实文本就绪后读取真实A按键；DEE9完整比较原等级，计算武力byte增量并排升级消息。bank8 A018→bank9 D390只决定第二提示资格，按等级编码3/4/5/6使用原武将白名单，不在该helper中改装备或城市名册。音频重置/播放、文本绘制及后续真实确认保留明确依赖；无变化分支恢复046C保存的地图cursor。

## 原模拟器实际结果

各值是本轮具体受控场景的观察，不作为固定伤害或成功率。

| 实验 | AP | 实际效果 | 施放者经验 |
|---|---|---|---|
| [陥穽](runtime/tactic-01/validation.json) | 16→11 | HP99→86 | 15000不变 |
| [火箭](runtime/tactic-05/validation.json) | 16→8 | 敌粮9999→8681 | 15000不变 |
| [共殺](runtime/tactic-07/validation.json) | 16→8 | 中心和下邻敌军兵均1000→811 | 15000→15283 |
| [籠絡](runtime/tactic-08/validation.json) | 16→6 | 0628 1→129，忠0→79；双方计数/总兵迁移 | 15000不变 |
| [落石](runtime/tactic-09/validation.json) | 16→7 | HP99→86，兵1000→901 | 15000→15049 |
| [連環](runtime/tactic-10/validation.json) | 16→7 | 中心状态0→5，相邻水域目标也改变 | 15000不变 |
| [水攻](runtime/tactic-12/validation.json) | 16→6 | 中心兵1000→779，连通水域目标联动 | 15000→15341 |
| [劫火](runtime/tactic-14/validation.json) | 16→4 | 中心兵1000→694，连通目标联动 | 15000→15479 |
| [陥穽死亡](runtime/tactic-01-death/validation.json) | 16→11 | HP1→0、低2位为3、单位槽移除；原兵1000与城市记录保留 | 15000→15045 |
| [落石升级](runtime/tactic-09-levelup/validation.json) | 16→7 | 等级编码2→3，武62→67；普通A实际完成升级、第二提示、返回战场 | 3490→3539 |

原D3EE按准备后的真实武将字段生成菜单：9案为16项，升级案为10项，再由普通方向键/A选择、选目标、确认与等待动画。所有案例以原战场存档为起点，明确准备武将ID/属性、位置、兵数等条件；tactic-08/09/09-levelup还固定了随机游标。没有注入已选计略、结果、缓存、动画完成或确认标志，也没有补写成功或绕过概率函数。不是完整自然战役回放。

83张PNG均与各自RAM/SRAM和核心存档同源。[整机报告](runtime/README.md)、[统一manifest](runtime/evidence.json)和各案的 `repeat-validation.json` 保存旧/新准备字节、真实按键、逐帧字段、核心身份和两次hash。死亡图未完整转写的字形保持未转写；结算字段和真实队列已有证据。

## 差分、来源与整合范围

| 回执 | 原CPU对照 | 模块/输入guard | 合同比较范围 |
|---|---:|---:|---|
| [individual](individual/validation.json) | 727 | 11 | 445完整返回、141死亡前缀、141真实D6CC后续；全SRAM及声明RAM |
| [area-conversion](area-conversion/validation.json) | 1392 | 14 | 750完整效果、642完整helper；全SRAM及声明RAM |
| [targeting](targeting/validation.json) | 2148 | 6 | 2070完整资格、78真实cursor前缀；全SRAM、声明RAM和返回carry |
| [统一接口](source-integration.json) | 1421 | 3项续程再入保护 | 128项16效果分派、24项死亡caller链、玩家/AI提示、升级和10份真实confirmed资格上下文 |

统一接口另有12项原核字段投影核对：10案效果和2次升级确认。动画检查点早于真正效果；源模型明确从逐帧日志导入实际效果前的0050随机游标及0501子状态，未修改运行中的原核。比较原12字节记录、报告、单位/状态、军粮、计数/总兵、缓存与AP表差值，排除未执行的渲染/音频时序及caller的百兵selector刷新。死亡同步调用已返回是由原核完成死亡路径的后置条件与原控制流推导，不称原核逐指令跟踪。

REA既有pair12/13及相关银行证据用于入口定位和来源审阅；新增原字节范围、EADE表和EE07内联word另外核对；[共同结算来源](settlement/README.md)区分已恢复窗口与AB90原代码附加块。所有源码、验证器、依赖、原CPU输入、原核记录与浏览器hash固定在 [总验证回执](verification.json)。原ROM只提供不可变数据，新的游戏逻辑不调用原ROM执行器或解释控制IR。此前精确CPU协议模型与历史归档保留。

## 可读接口与复现

```python
from pathlib import Path
from source.recovered.game_engine import GameEngine

rom = Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes()
game = GameEngine.from_snapshot('analysis/phase9/runtime/tactic-09/cast-confirmation',
                                rom=rom, mapped=True, data_window_bank=6)
print(game.player_tactic_targeting_rules().eligible(9))
effects = game.tactical_effect_rules()
# dispatch() 对应B02B清结果区与16项分派的独立效果入口；完整玩家施放需真实动画前序。
# player_cast_after_animation() 会继续检查04C8，而不把动画改成完成。
```

```sh
.venv-trace/bin/python scripts/verify_tactic_individual_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactic_area_conversion.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_player_tactic_targeting.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase9_integration.py
python3 scripts/verify_phase9.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/build_phase9_browser.py
```

16项效果与资格的完成范围不代表原作者完整源码、NES图形/音频/IRQ或全场景初始化已重制完成。精确的真实服务边界继续存在，源码以当前验证合同为准。
