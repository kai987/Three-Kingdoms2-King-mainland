# 可读的游戏逻辑源码

本目录包含从提供的 ROM 复原的 **Python 逻辑与状态控制模型**、**C11 计算库**，以及逐字节可重建的 `.byte` 源。它们是本次逆向整理的实现，不是原作者的源码，也不是已经独立运行的完整游戏。

| 文件 | 作用 |
|---|---|
| `recovered/city_field_contracts.py` | 城市+1错位门槛、原记录指针、10人容量与提名、明确无界扫描前缀及只读辅助字段 |
| `recovered/player_extinction.py` | 玩家首槽候选、无候选leaderFF、败亡mode0通知、单人E000重启/双人继续 |
| `recovered/extinction_scene_services.py` | 在既有全局UI/精确音频caller栈中替换败亡结局owner |
| `recovered/record_fields.py` | 月事件锁、城市事件冷却及名册边界；只读补充字段视图与声明的局部过程/前缀 |
| `recovered/audio_scene_services.py` | 14/15 A003/D8D4精确音序caller，保留真实PHA/PLA与全部闲置栈、N163请求 |
| `recovered/campaign_session.py` | 同一实际寄存器/主generator续程；每次接受NMI/IRQ的独立owner和实际RTI/reset交接 |
| `recovered/city_cooperation_ui_services.py` | 合作AI/君主反馈徽标OAM与两行标题producer，真实PPU任务消费和继承反馈另由NMI执行 |
| `recovered/boot_initialization.py` | E000软件初始化、F3BD条件probe/8KiB诊断、真实vblank等待及E066非返回交接 |
| `recovered/domestic_cooperation_controller.py` | main2银行10/11完整6,053位置闭包的直接函数，月轮内政、忠诚/继承及原合作等待 |
| `recovered/tactical_cooperation_controller.py` | main4银行8/9完整2,213位置闭包的直接函数，八策略、16资格、真实B517协议与资源副作用 |
| `recovered/game_engine.py` | 共享 RAM/SRAM；整合战斗/攻击/单挑、城市记录、转属、兵数、内政/月轮、归属/灭亡及全局/结局入口；第十轮连接显式呈现服务与NMI/IRQ |
| `recovered/service_memory.py` | 显式端口读输入、有序PPU/APU/N163/mapper写请求及可检查的寄存器图；不合成帧/声音/中断信号 |
| `recovered/battle_presentation_services.py` | 共享图形、文字、音序、NMI/IRQ和16计略；玩家battle5/sub5..10完整主体及明确controller callback |
| `recovered/tactic_presentation_effects.py` | 16项独立效果的原银行协议适配、真实地形窗与死亡刷新续程；不执行原6502或控制IR |
| `recovered/battle_graphics_services.py` | 地图刷新/光标/高亮/OAM构造，以及16项计略的11种动画类；生成原软件图形请求 |
| `recovered/audio_services.py` | reset/连续请求、183描述符、11槽/8channel音序驱动与原寄存器写序；不合成PCM |
| `recovered/battle_nmi_services.py` | F800完整NMI软件编排、9场景计划、忙重入、RTI、固定PPU/输入/mapper及FB2D IRQ软件主体 |
| `recovered/text_services.py` | 32个原文本数据命令、数字/姓名/城名与演员面板，实际文字/地图PPU消费者和readiness |
| `recovered/scroll_graphics_services.py` | 背景tile行/列与attribute滚屏请求；最终验证范围单列在第十轮回执 |
| `recovered/city_ownership.py` | 占领、殖入、撤城、劝诱转属、空城中立及退却收容；保留各路径不同掩码与名册副作用 |
| `recovered/faction_lifecycle.py` | 无继承人、灭亡事件、轮次跳过、30城统一、24位评分及6模式结局控制 |
| `recovered/global_main_loop.py` | 15项主循环、9项NMI合作窗口、4个银行缓存协议及RAM/OAM重置/正常NMI记账效果 |
| `recovered/tactical_ai_control.py` | 全局状态4调用的bank8完整有界战术控制IR；8策略、16计略条件及B517真实内联分派 |
| `recovered/tactical_decisions.py` | 独立扫描、两个轴的贪心移动/AP报价、相邻攻击、候选前缀及已部署缓存效果 |
| `recovered/tactical_exchange.py` | 战場提案路由、坐标/AP提交后缀与phase0/1请求；图形/消息前序另行执行 |
| `recovered/tactical_strategy_ai.py` | 八种策略的独立可读编排、完整合作扫描、退却、补给、治疗与普通/特殊计略选择 |
| `recovered/tactical_effects.py` | 施放协议及首批8项效果、十面埋伏；历史基础实现 |
| `recovered/tactic_individual_effects.py` | 陥穽、火箭、落石；体力/军粮、死亡前缀与真实图形返回后的清除/经验 |
| `recovered/tactic_area_conversion.py` | 共殺、籠絡、連環、水攻、劫火；相邻/连通扫描、阵营记账与忠诚 |
| `recovered/player_tactic_targeting.py` | 全部16项玩家目标资格及原坐标/地形读取，保留与AI不同的条件 |
| `recovered/tactical_effects_complete.py` | 全16项效果统一入口、玩家消息/确认/升级通知与显式服务续程 |
| `recovered/battle_state_machine.py` | 战斗16主状态、全部合法子分派与控制效果；高层胜败、城市归属/首将修复、战损及军粮资金归还 |
| `recovered/attack_state_machine.py` | 普通攻击场景11主状态、全部合法子分派；包含进入单挑和返回战斗的路径 |
| `recovered/duel_state_machine.py` | 单挑22主状态及控制效果；高层双方准备、行动路由、体力写回、胜败检查和返回战场 |
| `recovered/duel_logic.py` | 独立单挑AI、轮换、説得/罵倒、攻击、退却追击、投降及特殊装备奖励；高层游戏效果 |
| `recovered/postbattle.py` | main13/14完整语义控制器与BC46三种电脑名册分配；显式UI输入/事件 |
| `recovered/terrain_rules.py` | 30城地图、独立事件坐标表、双方地形归一、村落买卖/装备/治疗规则 |
| `recovered/map_service_machine.py` | 战斗main9背后的bank9十项村落服务控制器 |
| `recovered/runtime_services.py` / `mapped_memory.py` | 29个独立固定服务、只读PRG窗、RAM镜像与明确硬件请求 |
| `recovered/controller_helpers.py` | 独立恢复 EADE 内联分派、F2D7 武将寻址和4个随机数入口，保留 flags、scratch 和栈副作用 |
| `recovered/game_enums.py` | 16计略名称/ID/行动成本、状态码、地形查找与移动成本 |
| `recovered/officer_transfer.py` | 16个独立名册、忠诚、城首和继承服务，保留异址/同址写入与明确等待 |
| `recovered/domestic_ai.py` | 城市32字节schema、内政发展/选择/税收纯规则、5735条AI控制IR与3052条月轮调度IR |
| `recovered/troop_fields.py` | 分路径的低10位/全16位兵数读写、补兵、战损、后备兵归一及原溢出行为 |
| `recovered/terrain_semantics.py` | 地形1及其它合法类型的AI/玩家移动报价，保留不同selector与CPU flags |
| `recovered/officers.py` | 12字节武将记录、体/武/知/忠/徳、经验、兵、武器/防具、等级及原始位字段 |
| `recovered/battle.py` | 概率、距离、6项效果量、兵损、经验升级、单挑计算；入口已绑定计略名称 |
| `recovered/ai.py` | 候选筛选/排序、行动优先级、知阈值、特殊白名单、16项环境条件；结果可读名称 |
| `recovered/game_algorithms.py` | 寻址、16/24位除法、packed BCD、随机数 |
| `readable_c/game_recovered.c` / `.h` | 核心计算的可编译 C11 版本；兵损 API 限不同武将记录 |
| `byte-source/` | 全ROM `.byte` 表示，保证逐字节重建；不能作为语义恢复的证明 |

## 状态机的恢复范围

战斗的入口是 bank12 `$A028`，主/子状态为 `$0500/$0501`。单挑的入口是 bank23 `$B100`，主/子状态为 `$04A8/$04A9`。NMI 使用 `$0078` 场景选择推进它们；`$007A` 是另一层全局主循环状态，不能直接拿来代替战斗或单挑状态。

三台控制器读取 `analysis/battle_fsm/program.json`、`analysis/attack_fsm/program.json` 和 `analysis/duel_fsm/program.json` 中提升后的指令 IR，**不从 ROM 取控制指令执行，也不把每个状态体替换为原 ROM 入口调用**。全部合法 dispatch 表、内联数据边界、条件跳转和状态写入保留在各自 catalog 与逐状态汇编中。为了保持溢出、CPU flags、栈和同址写入行为，控制层仍保留机器级形式；算术、字段、计略/地形与场景整合层使用更高层的函数和类。

未独立恢复的跨银行语义作为显式 hook。缺少依赖会报出具体入口，不默认返回成功。第十轮的独立文本/图形/音序/NMI/IRQ服务另有语义和寄存器合同，不能把临时寄存器未比较的服务直接当成精确CPU控制层的等价hook。验证时可用 **实际 ROM helper adapter** 来比较旧控制层；这种测试不等于 helper 本身已经恢复为独立源码。普通攻击场景由 NMI mode4 推进 `$0540/$0541`；主状态5进入单挑，主状态4返回战斗。未知场景初始化及实际PPU硬件仍是独立依赖。

第四轮继续恢复了外部游戏语义：单挑与战后高层规则不再依赖原ROM入口调用，村落10子状态单独补上。此前101个战斗组合是本地控制图及结算别名数，并未包含外部村落表。第五轮补上内政AI与月轮调度，第六轮补上全局主循环和结局的有界控制图。第十轮新增完整NMI/IRQ软件前后和音序/图形/文本服务；PPU/APU/N163时序与像素/PCM合成、银行内未知场景主体及外部helper仍为明确依赖。各报告分别列明静态覆盖、执行覆盖和未恢复依赖。

## 使用真实战斗快照

```sh
python3 scripts/game_engine_demo.py
python3 scripts/game_engine_demo.py --tick
```

默认读取原ROM实际出征后捕获的 RAM/SRAM，输出5个活动单位、计略菜单、地形及记录。`--tick` 尝试单次控制器调用，缺少依赖时输出其地址；它不声称推进了一个完整 NES 视频帧。`GameEngine` 需要只读 ROM 数据供表读取，控制指令来自提升后的 IR。

调用方仍须提供进入控制器前的状态。原NMI会先把OAM计数 `$007C` 清零；源码的 `tick_scene()` 没有执行这段完整NMI前序。字段 `$0509/$050A` 的角色也随主状态变化，整合层使用原地址名，避免把移动流程的槽号误称攻击方/目标。

`$8000` 数据窗必须用 `data_window_bank` 显式提供；`$DE` 是NMI保存/恢复的银行，不能当控制器入口银行。三份已检查的原NMI入口上下文均观察为physical bank2；演示CLI为所附快照显式传2，没有把该观察硬编码为所有场景的规则。字段 `$063C` 的整合名称为 `hundred_troops_cache`。

```python
from pathlib import Path
from source.recovered.game_engine import GameEngine

rom = Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes()
game = GameEngine.from_snapshot('analysis/runtime/phase3/battle-tactics-true', rom=rom, data_window_bank=2, mapped=True)
print(game.control_state())
for unit in game.battle_units():
    print(unit.slot, unit.officer_id, unit.x, unit.y, unit.officer.troops_display)
```

计算示例使用真实初始记录与明确给定的演示坐标：

```sh
python3 scripts/game_model_demo.py --officer 38 --target 30 --rng-cursor 4
```

该例的效果入口 `$B188` 已确认对应「要撃」的效果量前缀；它没有执行全部计略动画/收尾，不是捕获的实战回合。

## 验证与重建

```sh
.venv-trace/bin/python scripts/verify_battle_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_attack_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_duel_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_names_terrain.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_controller_helpers.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/rebuild_rom.py
```

计算层的原验证见 `analysis/officer_fields/validation.json`、`analysis/battle/validation.json`、`analysis/ai/validation.json`。C11库可用原命令编译：

```sh
cc -std=c11 -Wall -Wextra -Werror -O2 -shared -fPIC \
  source/readable_c/game_recovered.c -o build/libgame_recovered.dylib
python3 scripts/verify_readable_c.py
```

本轮原 ROM 整机回放和 CPU 函数 fixture 分别保存；合成地形 RAM fixture 也单独注明。详见 `analysis/phase3/README.md`。

## 第四轮独立规则的使用

[第四轮报告](../analysis/phase4/README.md)分别列出控制IR、纯游戏效果、异步UI服务与整机像素的验证范围。

```python
# 以下读取原快照，不改保存的ROM/RAM/SRAM文件。
print(game.movement_quote(0, game.memory[0x600], game.memory[0x614]))

# 满足真实输入条件后调用：每项函数的地址/作用域见其docstring。
# DuelLogic 与 PostbattleEngine 始终使用同一份 game.memory。
duel = game.duel_rules()
postbattle = game.postbattle_rules()
# postbattle.step(text_ready=实际服务完成信号, cursor_index=实际控制器光标)
# duel.commit_confirmed_hp(queues_finished=实际队列完成信号, buttons=实际按键)
# game.process_ai_officers(mode)  # BC46 mode0/1/2
# game.settlement_rules(render_barrier=实际显示屏障)
```

`mapped=True`将ROM只用于不可变数据窗，并自动接入29个独立固定银行服务。`prepare_scene_callback()`显式应用已验证的入口银行、E1/E2/E3及OAM计数前提；不会执行NMI或完成图形/消息队列。`tick_scene()`是单次控制器调用。村落控制器以`tick_map_service()`直接进入bank9 C0BB，单独限定battle9/sub0..9；它不模拟父层EE07跨银行返回协议。未知硬件读写和未恢复helper均报错，APU4015只记录实际请求，不合成音频。

正式单挑类别0..8是けんせい、たいきゃく、こうげき、こうさん、せんじゅつ、データ、すてみのこうげき、せっとく、ばとう。结果码与武将status低2位分开：result2零体力随后进入移除处理，result3进入俘虏处理，result4进入转属；不能按同一数值互相替代。raw地形6/7/8在有效格存在，双方移动均按class2；服务类型用独立坐标表判定。

```sh
python3 scripts/game_engine_demo.py --mapped --tick
.venv-trace/bin/python scripts/verify_duel_logic.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_postbattle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_terrain_rules.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_runtime_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_source_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase4.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

## 第五轮统一入口

[第五轮报告](../analysis/phase5/README.md)记录转属/继承、城市字段、内政AI及兵数高位的新证据。`GameEngine.city()` 返回原始、显示和税收取值分开的城市记录；`transfer_rules()` 与 `troop_rules()` 操作同一份内存。`domestic_development()` 执行一个独立城市发展迭代，`choose_domestic_attack()` 选择目标。

`tick_domestic_ai()` 是 pair10/11 `$A00F` 的直接全局更新，`tick_ruler_turn('calendar'/'turn_events'/'ruler_ai_scene')` 是 pair25/26 的直接调度入口。它们要求 `mapped=True`、ROM和明确的 `data_window_bank`，不执行完整主循环前序；入口映射不自动同步E1/E2/E3银行缓存、OAM7C或renderer对象上下文，调用消费这些字段的hooks前须明确准备。全局 `$007A=2` 与NMI `$0078=2` 是两套分派：后者仍为城市UI，没有改为内政AI。安装继承人服务写FC，没有继承人路径写FB，均保持待确认；另恢复的调度计时段会按原代码阈值写1（FC受控sub11为480次调用、FB受控sub12为240次），不把调用次数当作完整视频帧。前置renderer/对话依赖仍明确。

```python
from pathlib import Path
from source.recovered.game_engine import GameEngine
rom = Path('/Users/paulasmith/Downloads/三国志2超级版.nes').read_bytes()
game = GameEngine.from_snapshot('analysis/phase5/runtime/city-info/menu-0',
                                rom=rom, mapped=True, data_window_bank=17)
city = game.city(11)
print(city.population_hundreds, city.displayed_population, city.treasures)
print(game.troop_rules().views(131))
```

转属API不擅自统一旧程序的行为：招入、删除、放逐、同城迁移以及电脑/玩家继承分别保留原作用范围。A006/A009/A00C只调忠诚。兵数 raw1098可由原分配程序产生，但列表低10位为74；`troops_upper_raw_bits` 是无语义命名的原高位视图。地形1正式名称仍为 `None`。

复现：`.venv-trace/bin/python scripts/verify_phase5_integration.py`，以及 `.venv-trace/bin/python scripts/verify_phase5.py "/Users/paulasmith/Downloads/三国志2超级版.nes"`。前者检查统一入口，后者核对机器码来源、独立回执、当前源码hash及未修改ROM身份。

直接AI flag1需要有效战后源城/目标城及名册scratch，不能直接保留菜单0038=222。逻辑SRAM模型尚未模拟上半区写保护；无效指针域不属于已验证的字段API合同，诊断见第五轮集成回执。

## 第六轮统一入口

[第六轮报告](../analysis/phase6/README.md)和[控制图浏览器](../analysis/phase6/index.html)给出城市归属、势力生命周期、主循环/NMI及结局的新证据。`city_ownership_rules()` 与 `faction_rules()` 共享现有内存；已恢复的灭亡提交只写君主ID为FF，不能自行补成清空城市、武将与外交的事务。`victory_entry_check()` 检查30城归属，D5人数警告则是另一个条件。评分保留16/24位溢出、零除和结局选择只看低字节的原行为。

```python
# 不改所加载的快照；以下先查看归属/势力，再执行有边界的控制更新。
ownership = game.city_ownership_rules()
factions = game.faction_rules()
print(factions.snapshot(game.memory[0x6F03]))
print(factions.count_owned_cities(game.memory[0x6F03]))

# 必须使用真实调用点的四个physical银行，末项固定31。
# 此参数只准备入口映射，不伪造RAM银行缓存/IRQ/消息完成。
result = game.tick_global(entry_banks=tuple(game.memory.banks))
print(result['status'])  # boundary / returned / dependency / budget
```

`tick_global()` 执行E066至下一次E066；`tick_nmi_cooperation()` 执行F862至F88D，包含NMI分派前LDA0，不执行F800真实中断前序、退出记账或RTI。`nmi_bookkeeping_effects()` 单独提供正常退出F88D..F8AF的内存/银行效果，只有实际到达此阶段才应调用；依赖中断后不得自动补尾。`cancel_scene_working_state()` 提供E4E9后的RAM/OAM取消效果，先行硬件/音序步骤仍未执行。

第六轮自动桥接physical10/11的A000→A00F内政入口、physical23/24的A01E→D693结局入口；第七轮另补physical8/9的A000→A02D战术AI。均保留原调用方寄存器、SP、返回地址，不向嵌套调用栈写0200哨兵。其他同地址函数必须先确认银行身份。`tick_ending()` 是直接的结局控制器调用；完整E46A/FA53画面初始化仍为外部依赖。F237保存NMI代码窗E2/E3，F24B保存主线程代码窗DF/E0，F25F保存NMI数据窗E1，F266保存主线程数据窗DE。

本轮18,194个有界原CPU对照、251项源码拒绝检查分别计数；整合层55项中53项对照原CPU、1项对照原core评分、1项源码合同。38项整机重复产物一致检查单列。静态控制IR为全局1005条和结局668条，静态全字节匹配不代表全部路径已动态执行。复现：

```sh
.venv-trace/bin/python scripts/verify_city_ownership.py
.venv-trace/bin/python scripts/verify_faction_lifecycle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_global_main_loop.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase6_integration.py
python3 scripts/verify_phase6.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

原模拟器中的30城统一案例只预置30个SRAM归属字段，再普通B/A输入1204帧；它观察到75分与mode1结局，证明受控入口之后的原代码/显示流程。它不是自然游玩达成统一，也不是可读源码已经恢复完整NES渲染与音频。

## 第七轮战术AI入口

[第七轮报告](../analysis/phase7/README.md)和[交互页](../analysis/phase7/index.html)展示完整有界控制器与独立高层规则的范围。`tick_global()` 在007A=4时按真实F24B银行切换进入A000→A02D，源桥接回到实际E22C。也可用 `tick_tactical_ai()` 直接调用A02D；直接测试默认使用0200返回fixture，不代表完整主循环或视频帧。

```python
game = GameEngine.from_snapshot('analysis/phase7/runtime/natural-turn/ai-request',
                               rom=rom, mapped=True, data_window_bank=6)
print(game.tactical_rules().decision_state())
result = game.tick_global(entry_banks=(6, 8, 9, 31))
print(result['status'])
print(game.tactical_bridge_rules().proposal())
```

这是明确的同步调用fixture：银行6来源于所附原存档，不当作全部战场的固定银行。`tactical_rules()` 返回共享内存的高层方法：`prepare_actor()`、`finish_actor()`、`plan_movement(x, normalized_y)`、`quote_direction(direction)`、`adjacent_attack()`、`nearest_enemy(radius)`、`secondary_effect()`。第七轮的高层模块覆盖这些段落；全部八策略的独立可读编排已在第八轮补齐，见下文。

`6F8B=0`或其他非1/FF值请求扫描，1进入B933持续效果，FF交还调用方。`6F8F=0`时6F8D是方向，=1是攻击目标槽，=2是计略ID，=3是不提交，=4是撤退目的城。移动报价只生成提案和6F97费用；坐标提交和扣AP是battle主状态8的不同后缀。`tactical_bridge_rules()` 提供这些内存后缀，必须由调用者先执行真实图形前序，不可自动套用来假推进NMI。

9,806项主体原CPU对照、255项源码guard分别通过。整合44项另列为43项全内存/寄存器/映射CPU对照及1项自然core坐标/AP字段对照。2213条控制IR全部核验原字节，动态1315条；未动态覆盖的898条不宣称逐条执行已验证。原核心无注入700帧只证明移动、AP与换方路径，phase1和成功计略的整机路径仍待捕获。

```sh
.venv-trace/bin/python scripts/verify_tactical_ai_control.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_exchange.py
.venv-trace/bin/python scripts/verify_phase7_integration.py
python3 scripts/verify_phase7.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

## 第八轮：八策略的独立可读源码与真实计略效果

`tactical_strategy_ai.py` 完整恢复策略0..7、A02D合作扫描、基础/特殊计略目标选择、退却、补给和治疗。它调用独立的玩法函数，没有解释IR或执行原ROM。对照合同是声明的玩法RAM及完整8KiB SRAM；任意CPU临时字节、寄存器、栈和mapper写入不属于该语义接口。旧 `tick_global()` / `tick_tactical_ai()` 继续保留精确CPU协议模型，新增 `tick_tactical_strategy()` 可直接运行完整可读决策。

```python
game = GameEngine.from_snapshot('analysis/phase7/runtime/natural-turn/ai-request',
                                rom=rom, data_window_bank=6, mapped=True)
print(game.tick_tactical_strategy())
print(game.tactical_bridge_rules().proposal())
# proposal只报价；移动坐标/AP、攻击和计略由真实消费流程提交。
```

`tactical_strategy_rules()` 还提供 `run_strategy(0..7)`、`retreat()`、`retreat_destination()`、`army_totals()`、`resupply()`、`heal()`、`plan_tactic(special=False)`。Mapped输入每个公开更新读取当前数据银行；flat输入在外部改变银行时要显式提供新值。补给保留现粮充足时的u16不足量下溢、总兵raw16和先除后乘；治疗先标记策略7，体力byte先回绕再封顶。它们在预计下一格到达时处理资源，坐标/AP提交仍有自己的真实前序。

第八轮的基础 `TacticalEffects` 提供8项效果（ID0/2/3/4/6/11/13/15）；第九轮 `tactical_effect_rules()` 已返回覆盖全部16项的组合实现，见下文。`after_*` 方法有精确的前序图形/音频/确认合同。等待04C8时继续返回waiting，绝不改标志冒充动画完成。

十面埋伏的原AI专用分支扣0AP，玩家扣10AP，两者部署均扣raw16兵100。部署TTL=5；真实round尾部更新两侧，1→0只清槽，0→FF下溢保留。踩中时先扣低10位兵且保留byte9高6位，之后给部署者结算经验，实际确认后才清槽。原核受控回放确实观察到1000→468、部署者经验3500→3766与确认后 `[FF,20,17,4]`；普通虚兵另有真实AP16→12及状态0→3。

`commit_tactical_retreat()` 读取已经选择好的0509槽与050B目的城，先执行C91E双方队伍数/低10位总兵记账，再组合旧BC2D收容名册/战场清除效果。选择、消息、输入和图形前序由调用方真实执行。它没有擅自把6F8D提案当作已确认的050B选择。

[第八轮报告](../analysis/phase8/README.md)、[交互页](../analysis/phase8/index.html)及[验证回执](../analysis/phase8/verification.json)分别记录5,779项主体原CPU对照、11项主体guard、统一接口46项原CPU对照与5项原核心字段核对。核心场景有明确的准备字段，原ROM及完成标志没有注入；A51F写1和B933回FF在同一帧消费，另外的同步CPU指令链不能当成Nestopia内部指令跟踪。

```sh
.venv-trace/bin/python scripts/verify_tactical_strategy_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase8_integration.py
python3 scripts/verify_phase8.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```


## 第九轮：全16项计略及结算

[本轮报告](../analysis/phase9/README.md)、[原核心证据页](../analysis/phase9/index.html)和[联合回执](../analysis/phase9/verification.json)记录剩余8项效果、完整16项玩家资格以及共同死亡/升级结算。新增模块只读取ROM数据表，不解释IR或调用原机器码。`GameEngine.tactical_effect_rules()` 现在返回 `CompleteTacticalEffects`，与已有战斗和AI共享内存。

```python
# 使用真实菜单确认时的快照；不是原视频帧推进器。
game = GameEngine.from_snapshot('analysis/phase9/runtime/tactic-09/cast-confirmation',
                                rom=rom, mapped=True, data_window_bank=6)
targeting = game.player_tactic_targeting_rules()
print(targeting.eligible(9))
effects = game.tactical_effect_rules()
# 后续调用须位于各API声明的真实前序之后：
# effects.player_cast_after_animation()  # 实际动画结束；04C8非零仍waiting
# effects.after_death_map_refresh(map_refresh_returned=真实D6CC返回信号)
# effects.player_confirm_after_text_ready()  # 实际文本服务和A键已到达
```

玩家资格、效果概率、AP扣费、效果计算和消息确认分别执行。玩家落石要求目标不是class5，AI条件却要求class5；籠絡资格没有AI的忠诚<50前筛选。概率保留有符号8位回绕，不能假定高智力一定提高成功率。

体力致死在原D6CC图形刷新边界停下，真实返回后才给经验和移除战场单位。它不改变城市名册、君主归属或队伍计数/总兵；原武将兵数字段仍保留。籠絡会翻转战场阵营、调整两军计数/总兵及忠诚，但调用的A006仅改忠诚，不等同于城市转属。共殺和连通计略保留原槽顺序、地形5阻挡、同址别名和重复经验副作用。

主体4,267项原CPU对照与31项源码guard、统一入口1,421项原CPU对照、12项原核心字段核对分别计数。原核心10例实际普通菜单选择、施放、消息确认和返回战场；其中3例明确准备随机游标，未注入成功结果、已选计略、完成缓存或动画确认。两次18,809帧回放的362份非空产物一致。受控输入和自然战役可达性是不同证据，详细准备字段随每例公开。

```sh
.venv-trace/bin/python scripts/verify_tactic_individual_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactic_area_conversion.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_player_tactic_targeting.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase9_integration.py
python3 scripts/verify_phase9.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

`after_*` 只恢复已声明服务返回后的数据步骤；没有自动完成渲染、音序或NMI。已恢复逻辑可单独审阅和执行，但工程仍不是独立运行的完整NES游戏。

## 第十轮：独立呈现服务与显式硬件输入

[本轮报告](../analysis/phase10/README.md)、[画面/实际WAV交互页](../analysis/phase10/index.html)和[统一接口回执](../analysis/phase10/source-integration.json)补上软件服务连接。新增 `BattleGraphicsServices`、`AudioServices`、`TextServices`、`BattleNMIServices` 和 `TacticPresentationEffects` 使用独立可读代码，读取原数据表/文本/音序数据，**不执行原6502、不解释控制IR、没有原CPU fallback**。旧battle/attack/duel等IR控制器继续单列，不能由这一结论推断全工程都已经脱离机器级模型。

`GameEngine.presentation_rules()` 返回共享内存的 `BattlePresentationServices`，持有 `graphics/audio/text/effects/nmi/irq/scroll`，并把 `tactical_effect_rules()` 接到带原银行协议的 `TacticPresentationEffects`。若旧效果尚有pending死亡刷新，必须先完成其真实续程，不能中途替换服务拥有者。`player_tactic_body()` 对应battle5/sub5..10的实际入口AA2E/AA6C/AAA7/AB2A/AB52/AB90，包含确认、动画后效果、死亡图形刷新、结果/演员面板、升级音序、第二通知及完整光标返回；它不替调用方选择计略或推进视频帧。

服务要求 `ServiceMemory`，可通过 `from_snapshot(..., mapped=True, service_io=...)` 创建。`service_io` 的 `read_ports` 是caller给出的硬件样本队列，`repeat_read_ports` 明确指定可复用样本；`controller_buttons=(pad1,pad2)` 的两个byte按bit0 A..bit7 Right真实串行读取。缺失端口输入保持依赖，不产生按钮、PPUSTATUS、IRQ信号或完成标志。`io_writes`、PPU命令字节、N163寄存器图和DMA请求可检查，但不是周期精确硬件核心。

```python
# Explicit host observations are inputs, not values manufactured by services.
game = GameEngine.from_snapshot(
    'analysis/phase9/runtime/tactic-09/cast-confirmation',
    rom=rom, mapped=True, data_window_bank=6,
    service_io={'read_ports': status_samples_by_port,
                'controller_buttons': (pad1, pad2)})
services = game.presentation_rules()
# At the declared battle5/sub5..10 entry:
result = services.player_tactic_body()
# For an explicitly accepted interrupt and its real registers/stack:
# result = game.tick_nmi_services(registers, hardware_entry=True,
#                                external_callback=actual_scene_owner)
# result = game.tick_irq_services(registers, hardware_entry=True)
# services.resume_nmi()  # only after the pending input/IRQ/service really returns
```

F800完整软件前序、9场景/8入口、FAD5忙重入、正常RNG/计数记账和RTI均已恢复；IRQ有13个分派位置。`hardware_entry=True` 只处理已经接受的中断压栈，不产生中断时钟。等待0062必须由真实IRQ服务清零后继续。生产callback只识别已恢复音序、文字、动画、滚屏和基础图形；未知controller仍返回具体dependency。文本/动画的临时A/X/Y/P不在语义合同，因此不能无条件接到旧精确CPU控制IR并声称所有寄存器相等。

五模块分别为图形4,596 CPU+4 guard、音序15,857 CPU+4 guard、NMI3,451 CPU+119 guard、文字893 CPU+7 guard、滚屏32,768 CPU+2 guard。其小计57,565 CPU+136 guard。音序含15,856完整返回和1项真实循环前缀，NMI另含严格前缀/等待，不能把五模块总数全称为完整返回。NMI验证器的61次原CPU callback仅属validator，生产源码没有调用它们。统一入口另有468 CPU+4 guard：448项玩家主体、12项完整NMI与8项滚屏callback完整回返；后12项的原CPU callback为0，未覆盖所有正常scene controller。地形descriptor另有40项完整DB46原CPU对照+2 guard，先捕获当前窗的chunk再切E000；此定向回归不保证任意旧descriptor在新银行仍有效。全文寄存器/栈比较排除及端口合同见第十轮报告。

原Nestopia原样重放第九轮10组受控母档/普通输入计划，新增核心内存写入与输入事件均为0。两跑37,618帧，392份非空canonical产物一致；其中332份PNG/RAM/SRAM/state与第九轮逐字节一致。完整WAV首跑含15,022,464个48kHz stereo样本对。图像与PCM来自原核心，PPU/APU/N163时序/波形合成仍由原核心完成；source回放没有这些输出能力，也没有录制Nestopia内部CPU指令trace。

```sh
.venv-trace/bin/python scripts/verify_battle_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_audio_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_nmi_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_text_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_scroll_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase10_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase10_terrain.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/build_phase10_browser.py
```

第九轮部分冻结执行清单的旧 `rom_offset` 漏加16B头，文件偏移须加0x10；[历史元数据说明](../analysis/phase10/README.md#历史偏移元数据更正)保留原文件/hash，CPU对照结果未改变。

## 第十一轮：具名场景控制器和真实初始化

[本轮报告](../analysis/phase11/README.md)、[原核心三流程交互证据](../analysis/phase11/index.html)和[统一入口回执](../analysis/phase11/source-integration.json)新增七个独立源码模块与一个组合器。`BattleSceneController`、`AttackSceneController`、`DuelSceneController` 分别恢复16、11、22个主态及其合法局部分派、真实NMI包装和局部调用；生产正文使用具名函数、直接分支、循环和generator，不读取 `program.json`、不解释opcode/IR、不执行原ROM。离线分析仍保留原IR与逐字节证据，旧API与冻结结果不变。

`SceneSharedServices` 恢复消息/菜单/RNG/数学、显示/淡出和跨银行服务；`SceneInitialization` 连接global3/5/7的真实初始化；`BattleSetupAI` 连接编队、AI配置、排序及部队显示；`BattleBackgroundInitialization` 从physical23 A009→A2FF构造31组初始背景行，调用真实EEE6并保留007E等待。默认只有新行请求时需62次消费；正文恢复相机，但把9C/9D都写90hex。fixedF09C保留调用者tile offset和纵向clip，包括原负X补码/部分OAM异常。

```python
# service_memory包含显式的硬件读样本与现有真实caller栈。
engine = GameEngine(service_memory, rom=rom, mapped=True)
coordinator = engine.readable_scene_rules()
result = engine.initialize_readable_scene(0xE18B, actual_registers)
if result['status'] == 'dependency':
    # 真实输入/待处理服务到达后，续同一owner；不改ready位冒充完成。
    result = coordinator.resume_setup()
# 已经位于真实NMI scene3/4/5 callback时：
# result = engine.tick_readable_scene(actual_registers, scene=3)
# result = engine.resume_readable_scene(scene=3)
# result = engine.tick_readable_nmi(actual_registers, hardware_entry=True)
```

`SceneCoordinator` 按实际PRG银行、callee入口和同一个共享 `ServiceMemory` 分配服务owner。每个pending调用保留自己的generator和调用地址，嵌套服务不能借父调用的恢复位置。只有明确 `status='returned'` 且真实PC/SP满足原return_pc/expected_sp才能继续；缺失、未知、错误、预算耗尽或尚未返回的服务均保留依赖。生产不默认植入0200哨兵，不制造视频帧、输入边沿、PPUSTATUS或队列确认。文字消费者合法early RTS与整个文字任务完成分别记录：例如文本只清007E低位1，尚存属性位10仍需真实EEE6消费。

统一入口26项原CPU对照分别为25完整返回、1普通攻击肖像callee处的严格前缀，另7项源码guard；这些组合病例没有原CPU callback。三个控制器各自的大矩阵可使用验证专用原helper，计数和范围在各自README中单列，不能把它们当作生产源码。背景另有227 CPU对照（224完整返回、3严格前缀）与3个续程检查；全部8KiB SRAM、声明RAM/真实栈、寄存器、银行和端口序的合同分别公开。所有合法状态入口均比较不等于全部数值/分支动态覆盖。

原Nestopia三条流程双跑22,870帧、91个检查点、387份非空产物及18份正式JSON重复一致，提供实际RGB及48kHz双声道PCM。没有新增ROM/core内存写入；普通攻击和单挑起点继承的明示fixture仍随案公开。单挑终点是battle11/sub3真实升级通知，不是完整战争胜利。原核心画面/音频不等于恢复源码独立合成；physical25 A000普通攻击肖像和其他未恢复远端UI/资料服务仍是明确dependency。

```sh
.venv-trace/bin/python scripts/verify_attack_scene_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_background_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_battle_background_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase11_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/verify_phase11.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

## 第十二轮：肖像、姓名、十行资料和精确文字caller

[本轮报告](../analysis/phase12/README.md)、[原核心UI证据页](../analysis/phase12/index.html)与[攻击集成回执](../analysis/phase12/dependencies/source-integration.json)补上四个独立UI owner。生产运行具名Python条件/循环与generator，不执行原6502、控制IR或原CPUfallback：

- [PortraitUIServices](recovered/portrait_ui_services.py)：physical25 A000→26 CE1F，两层肖像OAM、左右CHR和原嘴形/帧/坐标；不是属性卡。
- [OfficerUIServices](recovered/officer_ui_services.py)：29 A030/A03C姓名包、共同固定F308；保留真实数据窗/AXYP/scratch/栈副作用，不借Text.consume寄存器。58B模板原样读59B，含下一region首byte。
- [OfficerDetailsUIServices](recovered/officer_details_ui_services.py)：真正的25 A012→B2D7十行资料producer。040D为0..9行；busy/负row真实早退，007E.bit2只请求、不清除。兵低10bit、経显示原步骤、适性/装备字形与CHR缓存均按原数据处理。
- [TextSceneServices](recovered/text_scene_services.py)：29 A000/A003/A006的精确文字生产/消费和32类游戏数据命令；保持真实caller/AXYP及PPU端口序，合法early RTS不等于完成队列。旧语义TextServices保持原合同。

`SceneCoordinator`按真实pair/入口分配上述服务，F308可供其他pair的caller使用。所有等待仍由真实输入/consumer推进，同一pending owner可以resume，不能伪造ready或返回地址。已有GameEngine `tick_readable_scene`、`resume_readable_scene`与`tick_readable_nmi`接口接入这些owner，硬件视频/PCM仍是外部核心的职责。

四模块19,425原CPU对照＝19,423完整返回＋肖像2严格前缀，另28源码guard，0失败。肖像/姓名/资料比较全2048RAM（含自由栈）；文字比较1856声明RAM地址并明确排除其自由栈，全部均比较8KiBSRAM/AXYPSPPC/银行/端口。源码侧原CPUhelper调用为0。攻击集成另1,164完整返回＋1guard，声明1972RAM地址/全SRAM/精确寄存器与端口；原依赖发现及helper调用另列，不重复计入这1,164。

阶段11同26项统一入口在新增owner下重跑，现26完整返回、0前缀、7guard；上节25＋1描述保留初版scope，原肖像缺口本轮已恢复。其它未知远端菜单仍是dependency，不据有限矩阵宣告全部游戏已完成。

[附加资料页协调器矩阵](../analysis/phase12/ui-integration.json)另45项CPU（44完整＋1未初始化frame31 A244严格前缀）和1个scope guard。caller/寄存器是明确CPU fixture、RAM/SRAM来自冻结原核心点；不是native内部CPU trace。所有声明1972RAM/全SRAM/AXYPSPPC/银行/端口相等，源码无原CPUcallback或完成stub。四模块与两类整合共20,634CPU（20,631完整＋3前缀）、30单列guard，原依赖发现不重复计入。

原Nestopia两条UI流程双跑5830帧、46检查点、200非空产物一致（含12正式JSON），首跑48kHz stereo PCM为2,328,166 sample frames。战场信息起点继承无注入冷启动；普通攻击继承明示邻敌fixture且旧24检查点96文件逐byte相同。本轮新增core内存/ready/结果写入0，恢复源码未安装入原核心。历史文件名`info-rows-complete`是frame31继承旧FF，并非完成；正式完成画面是`info-open` frame272。原核心图像/PCM与独立源码CPU对照分开，均不称native指令trace或源码波形合成。

```sh
.venv-trace/bin/python scripts/verify_portrait_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_officer_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_text_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_officer_details_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase12_attack_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/verify_phase12.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```


## 第十三轮：城市菜单、全局UI和远端初始化

`GameEngine.tick_readable_scene(registers, scene=2)`现在通过同一`SceneCoordinator`执行城市控制正文；scene6/7/8分别是标题、君主选择、结局UI。`tick_readable_main(registers, entry=0xE066)`执行一个全局主循环分派，止于下一次E066，不能作为完整NES帧或RTS返回来理解。服务使用已有caller栈和显式硬件输入，未知、等待或非返回结果不继续。

| 源码 | 实际职责 |
|---|---|
| [city_ui_controller.py](recovered/city_ui_controller.py) | bank27/28城市16主态及其子表，地图、命令栏、内政/军事/物资/街市，调动名册和装备图形请求 |
| [city_panel_services.py](recovered/city_panel_services.py) | bank25/26君主/城市面板、年历、事件与出征准备；持久数据写入保留 |
| [global_ui_controller.py](recovered/global_ui_controller.py) | 城市辅助、标题、君主选择、结局UI；固定bank31的15项主循环可读分派 |
| [ui_graphics_initialization.py](recovered/ui_graphics_initialization.py) | 23A012/A015/A018的地图、属性、CHR与图形请求初始化 |
| [scenario_initialization.py](recovered/scenario_initialization.py) | 29A018→DD8B的新剧本SRAM与日期初始化，保留6F43 |
| [city_officer_details_controller.py](recovered/city_officer_details_controller.py) | 25A021→AFE5资料页驱动；选择ID取自0410[040C]，复用已恢复肖像和资料worker |
| [title_intro_graphics.py](recovered/title_intro_graphics.py) | 23A021的五阶段开场图形、计时和OAM请求 |
| [city_action_bridges.py](recovered/city_action_bridges.py) | 8A01E商店四项报价、10A006忠诚字节调整；不把报价当作完成购买 |
| [ui_arithmetic_services.py](recovered/ui_arithmetic_services.py) | EC22的24bit×16bit→40bit乘法与实际caller返回 |
| [city_menu_navigation.py](recovered/city_menu_navigation.py) | 固定菜单导航和EDDD取值，保留原局部调用的栈字节 |

城市main4已由原画面确认是物资输送／给予，main5是街市／店铺。菜单字段0400/0401、标题与君主选择0540/0541、结局0541/0542分别记录，不能将显示名单数据0480当作统一UI状态。

[第十三轮证据](../analysis/phase13/README.md)区分三层：带原CPU外部helper的本地控制对照、无CPU fallback的纯owner整合、原Nestopia音画回放。回放完成菜单进入、选择、取消、武将资料切换和返回；没有购买/结束回合效果的Native验证声明。PPU/APU/N163时序、完整RGB/PCM、冷重启E000及部分合作AI入口仍保留硬件或已声明边界。

## 第十四轮冷重启与全局合作AI

四份新源码使用原寄存器、caller栈及ServiceMemory，生产无IR或原CPUfallback。SceneCoordinator精确按bank/entry选择owner；main2/4经过真实RNG与mapper前序才进入A000。旧controlIR接口供历史比对保留，新可读主循环使用直接函数。

`game.initialize_readable_boot(actual_registers)`执行E000软件正文；缺失显式PPUSTATUS输入时保持原位等待，补充输入后用`game.resume_readable_boot()`续程。完成的`reset_boundary`是E066/SPFF非返回交接，退役旧待续UI/NMI/main对象；不是旧callerRTS。普通probe mismatch保留全部SRAM，newgame剧本初始化是另一服务。`game.tick_readable_main(actual_registers, entry=0xE066)`及现有readable NMI API继续使用同一共享bus。

[第十四轮报告](../analysis/phase14/README.md)、[整合回执](../analysis/phase14/source-integration.json)及[源码/原帧/实际WAV](../analysis/phase14/index.html)分别说明完整返回、E066交接、永久诊断和真实等待前缀。所有动态覆盖范围和硬件边界公开，不把完整静态闭包称成全分支或完整独立NES核心。

## 第十五轮字段和战役续程

`GameEngine.city_auxiliary_fields(city)`提供城市+1/+27/+28..31及名册插入的只读补充视图，不替换原CityRecord或已完整恢复的城市控制器。`6F06`确认是月事件检查锁；`+27`合格事件扫描减一并在命中时写6，满十槽追加还会覆盖它。`+1`正式语义继续未决，原重叠读取+1/+2必须保留；+28..31与适性3也不猜名称。详见[字段合同](../analysis/phase15/fields/README.md)。

`GameEngine.readable_campaign(actual_registers)`返回显式Session。同一原主调用等待期间，可接受明确的NMI/IRQ到达，每个中断独立拥有generator，真实RTI恢复中断前PC/SP后再resume；忙NMI嵌套等待也保留。`main()`只从E066进入，`resume()`核暂停PC/SP，非返回reset清退旧pending。此API不调度周期/帧，也不写ready/ack，调用次数不等于原核心视频帧。

SceneCoordinator在14/15 A003/D8D4优先使用精确AudioSceneServices，记录原音序临时PHA/PLA。两条受控继承链的新回执含完整2048B RAM，无旧1976B范围排除；实际原CBBF写ack再恢复同一ServiceCall/generator。旧AudioServices语义接口和v14冻结证据继续供历史对照。

[51项Session矩阵](../analysis/phase15/session/validation.json)与[2项继承](../analysis/phase15/succession-integration.json)合计53父CPU案例；内部722NMI不再加计。精确音频1631body加20实际callee输入、字段3137共4788项主域CPU；其2449字段前缀与2音频前缀不当完整母函数。自然跨年/连续战斗/受控战后继承使用原Nestopia验证，原核心提供RGB/PCM，源码仅核软件字段/寄存器/端口。[本轮报告](../analysis/phase15/README.md)分别声明全部边界。

## 第十六轮实际战后继承与依赖闭包

`battle_succession.py`恢复真正`25:A00C→AD81`城市13七阶段、玩家/AI/无候选流程；coordinator只接公开入口，局部matrix入口不自动路由。家族优先后取德最高、同德后遇者，连续名册到首FF；没有另加HP/status/byte5资格过滤。无候选只写leaderFF，原月轮跳过而空城owner可能保留，不自行补全全城中立事务。玩家HPFF/status3及选城/选将/确认按原值保留。

`postbattle_graphics.py`接实际29A01E年月packet；`postbattle_loyalty_bridge.py`将10A009真实JMP接到既有CF7C可读helper；`exact_audio_requests.py`恢复12个固定音频请求入口和真实caller栈。`integrated_scene_services.py`委托旧全局/初始化内部已有JSR帧，完整比较包括闲置栈，不增造调用帧。GameEngine提供三个新owner getter和只读`city_unresolved_fields(city)`。

`field_semantics.py`确认适性3在三项字形/阵形表外读取后续机器码；原资料页出现表外字形，没有官方第四能力名称。有效237初始英雄只有0/1/2，但原240条复制的额外ID237..239可含3。A796是caller-PHA后缀、B64D只到B663前缀，不能当独立普通JSR服务。城市+1/+2重叠word保留，+1正式名称及+28..31用途未决；647个未解指针/Y候选清单公开。

五域12660父CPU、实际音频19及统一入口24合计12703：12442完成、261明确前缀，另54guards；源码侧无原CPU/IR执行。两个同一Session原city13序列接受每案681显式NMI/3405IRQ，内部阶段不增加父案例或称视频帧。原Nestopia四案35162双跑帧、1076非空产物一致，9本轮准备写和45继承旧准备分开；RGB/PCM由原ROM核心提供。[本轮范围与复现](../analysis/phase16/README.md)、[最终审计](../analysis/phase16/verification.json)、[完整源码和原画面/声音](../analysis/phase16/index.html)。

## 第十七轮玩家无候选与城市字段合同

`PlayerExtinction`替换实际city13 A00C/AD81流程的BE2E、C386、C3C2及C41E；候选城市只检查所属和名册首槽，不补HP/status筛选。`PlayerLossEnding`恢复NMI8 A01E的mode0 D6AA；FE标记只新A退出，6F43原开局配置为0才走E000/SPFF/E066非返回重启，否则清flag并恢复0472/73保存的父流程；本次双人原流程随后由另一玩家继续。新组合`ExtinctionGlobalUI`保留既有实际音频JSR栈帧，旧模块不改。

GameEngine新增`player_extinction_rules()`、`player_loss_ending_rules()`、`city_field_contract(city)`与显式`city_field_services()`；`battle_succession_rules()`现在返回新战后owner。字段完整入口与BD95/A71B/A442/B144前缀分开，未知等待不自动路由为RTS。名册17..26合法满10可无FF，C21D有界；无界插入只在绕过容量边界的明确输入中证实尾字节别名。城市+1/+28..31正式名称仍未确认。

6,973原CPU父案例：5,307完成边界、5原E000/E066非局部重启、1,661严格前缀，另26guard。两项同一Session分别经449/579显式NMI及2240/2895 IRQ完成重启或另一玩家world，不将内部事件加为视频帧。原Nestopia三案双跑68,124帧、594检查点、2,429非空产物相等；33明确准备写，原像素/PCM仍由核心提供。详见[本轮报告](../analysis/phase17/README.md)、[完整源码与原流程](../analysis/phase17/index.html)、[独立源码组合](../analysis/phase17/source-integration.json)及[总审计](../analysis/phase17/verification.json)。
