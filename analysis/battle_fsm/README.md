# 战场状态机恢复与范围

原 ROM SHA-256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。没有修改原 ROM。

`$0500` 为主状态，`$0501` 为子阶段。入口 bank12 `$A028` / file `$18038` 使用 `$A02E` 的16项表。16个主状态的本地表展开有98项；主状态15通过 far bank8 `$A006` → `$BAB3` 使用同一个 `$0501` 的四项外部表，因此全部合法主/子组合为 **101**。状态2与3共享同一4项入口表，状态15的4个组合共享本地 `$D4F0` 入口。

| 主状态 | 可证用途 | 子阶段数 |
|---:|---|---:|
|0|单位选择、行动菜单|5|
|1|单位信息|3|
|2|普通攻击目标选择|4|
|3|普通攻击确认（与2共用入口）|4|
|4|移动|7|
|5|计略菜单、目标、执行与反馈|11|
|6|退却|6|
|7|待機；也承载换方、胜败消息阶段|8|
|8|电脑方决策和战场表现的桥接|17|
|9|村落服务跨银行入口|1个本地bridge；bank9另有10个服务子状态|
|10|回合/初始单位准备|7|
|11|单挑返回后的经验、武力提升提示|4|
|12|战斗结果确认|6|
|13|败方武将转移或转为在野|7|
|14|胜方收容及超额武将转移|7|
|15|战后归属结算及返回城市（bank8委托）|4|

菜单名称由真实原ROM像素和 `$A1AC` 对齐：移动=4、攻击=3、计略=5、待機=7、退却=6。state13/14保留A/B命名，因为尚未将全部中文/Japanese消息文字与每种处置选择逐项验证；可执行分支、写回和数组操作已经完整列出。

## 可读源码

`source/recovered/battle_state_machine.py` 提供两层源码：

* `BattleStateMachine(memory, hooks).step()` 在自主 Python 控制/算术执行器中执行 `program.json` 的全部本地控制指令，返回 `before / after / events`。本地子程序也执行恢复后的代码；原ROM仅供外部hook验证，未用“整段原ROM调用”替代本地handler。缺少helper时抛出显式依赖异常。
* 高层玩法函数恢复 `commander_outcome`、`finish_side_turn`、`refresh_movement_selectors`、`restore_side_action_budgets`、`postbattle_city_losses`、`return_campaign_supplies`、`promote_city_leader`、`finalize_city_ownership`、`finalization_phase`。这些函数直接操作可读 gameplay 字段和数组；不声称复制6502 scratch、flags、stack或文字队列编码。

重要精确行为：

1. `commander_outcome` 对 slot0和slot10的缺席/阵营变更作胜败判断。`$052B!=FF`时进入12/0，否则按残余单位和君主控制码进入7/2或7/3；其两个PLA导致的非局部返回显式表示为 `abort_frame`。
2. `$063C[slot]` 为武将mask10bit兵数除100；空slot写FF。移动表的 `>=6` 分支在正常域对应兵数至少600。
3. 回合补给依两方兵数总和除1000索引，按 `[10,16,20,24,28,32,35,37,40,42,42,42,42]` 增行动力，cap为 `[20,26,32,36,42,46,51,53,58,60,60,60,60]`。8bit相加先溢出，再cap；不能改成普通无限整数相加。
4. 城市损耗保留原程序的16bit乘积截断及反向阈值比较：field2/4值 `<=501` 使用rate9，`>501`使用rate5。字段语义尚未给UI证明时保留numeric offset。
5. 军资归还先16bit wrap再cap9999。第二方归还只在逃出武将status为1/2时送到 `$052C` 城市；status0/3或FF走当前城市。
6. 最终阶段 `$0087` 为负时，城市所有权按 `$0514==0` 改为 `$0507` 高半字节，并将该城/相邻城君主交换到名册首位；之后写 `$007A=1,$0400=13,$0401=0`，确实回城市控制。

高层收尾的AI俘虏/武将处置 `$BC46`、NMI渲染barrier以及换方中的bank8 AI入口仍为命名依赖。它们不默认成功。

## 控制图、条件与证据

* [state-catalog.json](state-catalog.json)：全部101组合、准确bank/CPU/file、条件分支、状态写入、调用依赖、原始字节。
* [all-entries.md](all-entries.md)：每个合法入口的条件、作用及原始流程链接。
* `handlers/*.asm`：全部入口的完整可达本地控制图，包括共享退出路径。
* `program.json`：6403条独立可执行控制IR；`control-program.json`保留原始字节。
* `validation.json`：供总验证器读取的简明结果；`oracle-verification.json`：完整病例与覆盖证据。

EADE的内联地址表按数据解析；EE07内联2-byte目标使调用宽度为5；所有pair12/13内部直接JSR递归展开。未知本地表/未分类边为0。完整静态入口覆盖和动态指令执行覆盖是不同指标。

## 实测与差分验证

```sh
.venv-trace/bin/python scripts/analyze_battle_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

输入使用 `analysis/runtime/phase3/attack-intro-*.state` 对应的原始RAM/SRAM。这些基准来自未改ROM的完整NES执行。测试中的按钮、ready、邻接敌军、指挥官缺席修改为明确标记的合成边界输入，不冒充自然游玩轨迹。

额外限定恢复8个bank31 fixed入口：E850/E856/E862 RNG包装，EA7C/EAA5/EBE9算术，F2AF/F368指针；其精确原始字节与语义见 `fixed-helper-index.json` / `helpers/`。它们均由本地IR执行，E87A仍使用已验证shared CPU协议。新增4096独立fixed helper病例（每入口512），包括flags、stack、全部RAM/SRAM及异常除数0。E862输入bound0不终止，正常bound1..255被验证。

IR对照：101组合×8变体=808病例，另56次主入口tick，逐项比较最终A/X/Y/P/SP/PC、2KiB RAM、8KiB SRAM。外部helper由原ROM oracle执行；ECEE依赖NMI的barrier在两侧显式绕过。高层玩法函数与原ROM比较对应玩法字段/SRAM，3328病例。最终验证全部8288病例通过（808入口+56主tick+3328高层玩法+4096fixed helper），动态指令覆盖3560/6403。最终通过状态与精确动态覆盖以 `validation.json` 为准。

原ROM自然路径为：城市军事→侵略→目标→选曹操→结束→军资确认→战场行动菜单。普通攻击交出 `$007A=5` 进入NMI4攻击表现；真正单挑是后续攻击场景 `$0540=5` → bank15 `$CD43/$CD59` → `$007A=7` → NMI5。不能把战场攻击目标确认直接称作单挑。普通攻击场景由独立 `attack_state_machine.py` 恢复，单挑由 `duel_state_machine.py` 恢复。

## 尚未独立恢复的依赖

这里是完整的本地战场控制表和可执行恢复，不是脱离原NES环境的完整可玩游戏。6403条IR执行仍需静态ROM数据、fixed/跨bank服务、渲染、声音和输入。外部依赖有19个helper地址，其中2个在shared helpers独立恢复；EE07一个地址复用17个不同far selector/目标，因此实际剩余语义依赖是16个fixed服务+17个far目标=33。`validation.json`会保留这些计数；source实现新增后须重新审计。

不将入口测试通过称作100%分支覆盖，不将原ROM oracle hook称作独立重写，也不将等待动画结束当作自行推进了动画。

第四轮补充：state9的C1FC不是只有sub0的电脑目标更新；它转到bank9 C0BB的10项村落服务分派，详见[服务目录](../phase4/terrain/service-controller.json)。既有101组合是本地控制图/别名展开数，不涵盖这张外部服务表。main13/14及BC46的独立游戏效果见[战后报告](../phase4/postbattle/README.md)。
