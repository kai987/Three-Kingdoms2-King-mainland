# 第十一轮：独立的战斗场景控制源码

[battle_scene_controller.py](../../../source/recovered/battle_scene_controller.py) 将原bank12/13战斗流程整理为具名Python过程、状态/阶段函数、直接条件分支与自然循环。生产运行**不读取旧IR，不解码6502，不用PC→指令字典，不调用旧BattleStateMachine或原CPUfallback**。离线分析器可读取冻结的旧图并核对原ROM；这是构建证据，不是运行依赖。旧源码、图与回执均未改写。

这是有边界的结构化控制源码，仍保留可观察的寄存器、flags、scratch和原地址；多数局部过程由离线CFG结构化产生，A05E的控制选择另外人工整理。它不是所有游戏算法都已经人工重写为业务公式，更不是独立NES硬件核心。指令周期、逐指令异步中断、视频帧与PCM不在本模块合同。

## 实际入口与新增闭包

| 入口 | 原位置 | 新函数/行为 |
|---|---|---|
| A000→A009 | physical12，文件018010/018019 | 真实NMI3场景包装：DF88→logical28 A012→A021→A028→DF39→logical28 A015→RTS |
| A003→DC99 | physical12 stub / physical13主体，文件018013/01BCA9 | 战场数组初始化：camera初值、AP/队伍数/低10位总兵临时字段、候选名册、20单位坐标/side/适性/condition和百兵缓存 |
| A006→C766 | physical12 stub / physical13主体，文件018016/01A776 | 单挑结果消费：刷新百兵缓存、按双方officer-ID找slot，按结果低3位分派；C787表有8项 |
| A028 | physical12，文件018038 | 16主状态的局部合作分派；不是整个NMI包装 |
| DF39 / DF88 | physical13，文件01BF49 / 01BF98 | 战斗IRQ布局请求与camera低byte相关延迟选择；不产生IRQ时钟 |

旧A028图有6,403个指令位置，遗漏上述公共包装/初始化/单挑结果及显示布局闭包。新分析器直接核对原字节补入269个位置，合计**6,672个原指令位置、253个局部过程**。补充时正确跳过EE07内联word和C787的16字节数据表；没有把表字节当作指令。原字节、文件偏移与离线operation标签见[evidence.json](evidence.json)及[listing](original-instructions.asm)。文件偏移均包含16字节头。

源端恢复**74处自然循环、1,501处结构化条件区域**；后者是离线结构化区域数，包含共享路径展开，不等于原独立branch指令数。源码还含caller/pending合同的检查，不能把AST总if数与原CPU动态执行次数混用。公开入口只在启动时通过静态if/elif选择一次，运行中不会反复查PC表推进控制。

## 16主状态与阶段函数

| 主状态 | 原入口 | 源函数 | 合法阶段/范围 |
|---:|---|---|---|
| 0 | A04E | `unit_selection` | 5：控制者/AP检查、cursor刷新等待、单位选择、行动菜单与确认 |
| 1 | A21B | `unit_information` | 3：开启、导航、关闭信息 |
| 2 / 3 | A293 | `attack_target` / `attack_confirmation` | 各4；两者原本共用同一主体和表，不伪造不同机器码 |
| 4 | A44D | `movement` | 7：移动输入、事件格、phase1埋伏请求/消费及消息确认 |
| 5 | A87C | `tactics` | 11：列表、菜单/目标、确认、动画等待、效果、报告/升级通知与无效目标确认 |
| 6 | B94A | `withdrawal` | 6：退却及目的地选择/提交/确认 |
| 7 | BC93 | `wait_action` | 8：等待选择、side通知、逐单位刷新、策略通知及换方 |
| 8 | BE7E | `computer_action` | 17：AI请求、提案路由、移动/攻击/计略/撤退与回交 |
| 9 | C1FC | `village_service` | 一个本地bridge；bank8/9的十项村落服务仍是另外的跨银行责任 |
| 10 | C204 | `next_side` | 7：资源/控制者/次将处理及返回单位选择 |
| 11 | C691 | `duel_result` | 4：双方单挑后的显示/升级通知；A006另有真实结果处置入口 |
| 12 | C98C | `battle_result` | 6：总结、文字/PPU等待、结果面板及处置选择 |
| 13 | CD16 | `defeated_roster` | 7：败方名册、目的地/在野选择和转移确认 |
| 14 | D2CD | `victor_roster` | 7：胜方名册、超额成员选择和转移确认 |
| 15 | D4F0 | `return_to_city` | 一个本地bridge；旧表列出的4个bank8结算阶段不冒充4个本地主体 |

[catalog.json](catalog.json) 保留原16状态、101个旧组合标签及其bank/CPU/file地址，追加 `recovered_function`。旧101组合包含98个本地展开标签及3个额外跨bank别名，不是101个不同函数；共享入口及另外的村落子表必须分开读。新局部C787单挑结果表按0..7有效，5..7有原共享尾部，未按游戏常识另编结果意义。

字段名称直接绑定原地址：`STATE/PHASE=0500/0501`、`SIDE=0504`、`AP=0505`、`ROUND=0506`、`RULERS=0507`、`SELECTED_SLOT/ACTOR_SLOT=0509/050A`、`CITY=050E`、`CONTROLLER=050F`、`TACTIC/TACTIC_FAILED=0543/0544`。0509/050A的角色随状态变化，不能统一称为攻击者和目标。`ANIMATION=04C8`、文字0300/0304、PPU jobs007E保持真实等待，不由控制器写ready替代服务。

A05E先执行commander outcome，再按controller3及AP进入电脑请求；human等待真实文字ready后进入选择，AP为0或符号负值则tail-call换方。DC99是战斗专属数组初始化，不能把它描述为完整global/NMI/PPU初始化。DF39按0518请求0/1选择两套IRQ软件参数后写FF；DF88只在61=5时按8E<16选择68=72/74。

## 服务、caller栈与等待

```python
from source.recovered.battle_scene_controller import BattleSceneController

controller = BattleSceneController(memory, rom, services=actual_scene_services)
# NMI已经真实调用12A000，caller frame由外层保留：
result = controller.tick(registers=call.registers,
                         seed_return=False, return_pc=call.return_pc)
# 或明确调用公共入口：controller.run_entry(0xA003, ...)
# 缺失服务保持dependency；真实服务推进后重试同一边界：
# result = controller.resume()
```

`run_entry()` 默认不种植合成返回栈；直接CPU fixture才明确用 `seed_return=True`、return0200。`services(call)` 遵循既有 `ServiceCall(target,return_pc,kind,registers,memory,entry_banks,expected_sp)`。JSR、tail、EE07各保留真实栈及返回地址，EE07的inlineword有独立来源。callback没有到真实PC/SP，即便报告returned也不能推进。重复resume不会重新压栈；未完成的shared服务必须保持同一个call拥有者。

当前默认services为空。bank8 A012/A021/A015已由另一个独立的 [BattleSetupAI](../../../source/recovered/battle_setup_ai.py) 补齐，可由协调器按真实bank/caller协议连接。村落/归属结算及其它未被服务拥有者恢复的跨银行调用仍明确pending；不能把完成本地结构化恢复说成所有远端UI主体也已经恢复。固定message/input/mapper/RNG等可接本轮 `SceneSharedServices`，phase10呈现服务另有自己的合同。文本/动画临时AXYP、音序自由栈残余未全部比较的接口，不能无条件替代精确寄存器callback并声称全CPU状态相等。

## 原CPU差分及实际范围

[validation.json](validation.json) 为**2,745项原CPU对照：2,232项完整返回、513项严格前缀，另10项源码guard；0失败/0未解决fixture**。使用不可变ROM直接执行原CPU，对照新独立控制源码；旧BattleStateMachine没有参与。验证器专用原CPU callback共3,356次单列，源码侧纯shared八例callback的原CPU调用为0。ECEE同步边界**没有被替换为no-op**；未执行时两侧停在同一真实前缀。

最终统计以该回执为准：主体包含101个旧组合的4个输入variant、253个发现的局部过程直接fixture、16主态真实A000包装、12项初始化、64项双方低3位单挑结果、512项原byte显示布局与1,024项固定math/RNG边界/随机输入。另8项真正使用独立 `SceneSharedServices` callback，源码侧没有原CPU执行。直接调用局部函数的fixture不代表该函数都可由自然游戏操作单独进入。

对照全部2KiB RAM、8KiB SRAM、AXYPSPPC、bank与有序端口读写。含原CPU callback的完整案例只证明本地控制代码与这些外部body组合的协议，callback没有因此变成生产源码。源码侧纯shared八例另外标记；实际原核心视频、声音、扫描线及自然campaign证明由根报告另列，不能由本回执推断。

10项source-only guard检查主/子分派越界、未知入口、D=1域拒绝、缺失服务重复resume保持caller栈，以及假returned不能自行pop。新增waiting/error/blocked/None四项即使将寄存器PC/SP改成caller值，也不能恢复控制流程。它们不是10项原CPU执行；拒绝前可能已有真实prefix写入，不保证原子回滚。

复现命令：

```sh
python3 scripts/analyze_battle_scene_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_scene_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

分析器会重生成独占新源码与证据，不修改冻结历史文件。[static-validation.json](static-validation.json) 检查生产模块不加载IR/原CPU/旧executor，结构化源、原字节与依赖hash分别固定在证据/回执。有限输入对照不能当作所有字节值域/每种服务时序已经穷尽。
