# Phase8：完整8项战术策略的独立可读源码

`source/recovered/tactical_strategy_ai.py` 用独立玩法算法恢复策略0..7及A02D合作扫描，完整退却、资源补给、体力治疗、基础/特殊计略选择与目标筛选。没有执行/解释IR、原ROM CPUfallback、图形空hook或自动ack。它不是原始游戏源码，CPU寄存器/stack/flags/mapper协议仍由旧完整IR控制器提供独立参考。

## 接口与输入合同

```python
ai = TacticalStrategyAI(shared_memory, StrategyData.from_rom(rom))
result = ai.step()
result = ai.run_strategy(4)
```

构造和调用可传 `data_window_bank`。MappedMemory入口每次读当前`banks[0]`，一次完整update内部独立跟踪原F266引起的数据read窗口；不写真实mapper。Flat64K没有bank元数据，外部host改窗口时必须明确传新的bank，不能依赖旧缓存。ROM地址的A8/A9地图描述必须有已知data bank。四项descriptor限定原RAM/SRAM/8000..9FFF数据窗，chunk0..119；不读取表外代码。真实native snapshots的descriptor在RAM00AA，12项另外的完整策略fixture核对了ROM描述数据及内部银行变化。

`step()`是完整合作更新，`run_strategy(0..7)`是完整单项策略。另公开`retreat()`、`retreat_destination()`、`army_totals()`、`resupply()`、`heal()`及`plan_tactic(special=False)`。`maximum_strategy_calls=0`会停止在真实下一strategy边界，返回budget与已发生写入，不伪造完成。

源码共享RAM/SRAM，声明玩法RAM为042C..042E、04D8..04DF、0500..0677，完整比较8KiB SRAM。2F排序输入及6F93保存X副作用保留；其他CPU临时scratch、寄存器/flags/栈和真实mapper写入不在高层等价合同内。无需静默猜入口X：0..4先经AF0D原LDX0504；治疗draw前固定sideoffset0/2；basicdraw前predicate建立X；其余完整路径按真实次序传播。

## 8项策略次序

| ID | 原bank8入口 | 独立恢复的实际优先次序 |
|---:|---|---|
| 0 | A0B1 | 退却→特殊计略；非负side基础计略；负side相邻攻击→基础计略→low2 RNG决定不行动或朝slot0移动 |
| 1 | A105 | 退却→特殊计略→AP>=2且邻接对侧首槽攻击→对侧首槽/城市原base坐标移动 |
| 2 | A166 | 退却→特殊计略→相邻攻击→actor radius2第一最近敌移动；无候选对侧首槽/base坐标移动 |
| 3 | A210 | 退却→特殊计略→相邻攻击→本侧首槽radius2第一最近敌；其邻居存在友军非首槽则基础计略否则靠近；无候选基础计略后本侧首槽移动 |
| 4 | A2AD | 退却→特殊计略→相邻攻击→actor radius3第一最近敌移动；无候选基础计略后本侧首槽移动 |
| 5 | A329 | 原service0坐标移动→预测下一原坐标命中后markstrategy7→资源word预算/缺粮/报价分支 |
| 6 | A507 | 原service2坐标移动→预测命中后markstrategy7→资源>=50先扣50→拒绝抽low4<11加35→u8加体力后按初始体封顶 |
| 7 | A606 | 直接status3 |

“首槽”为0/10；表有8项，低nibble8..15非法。strategy是现代行为编号，不是正式原菜单名称。普通计略ID和移动方向编码分开。提案status0/1/2/3/4依旧由战场消费者解释；本策略源不会替施放统一扣AP（尤其AIID11的原消费路径另有合同）。

## 精确选择、退却和作用顺序

基础计略按知力分档1/3/5/7/9，radius5候选按raw16兵数降序排序；等值也swap，排序pass使用原2F而不假定无限完整sort。优先6(tier6/AP8/目标有兵)、5(tier5/AP8)、8(tier8/AP10)、9(tier9/AP9/有兵)、7(tier7/AP8/有兵)。随后predicate1通过才抽low2：0拒绝、3且目标无兵也拒绝；3→action3(tier3/AP6)、1→action2(tier2/目标conditionlow4=0/AP4)、2→action1(AP5)。接受抽样但对应门槛失败也结束该随机分支；再尝试4(tier4/有兵/AP7)、0(有兵/AP6)。所有16项地形/邻接/武知忠/预备槽谓词都独立执行实际规则，没有接受值stub。

特殊入口要求知>=92、byte11high4>=3。原21项白名单level3尝试10(condlow4=0/AP9)后11(AP10)；白名单suffix11 level4且目标有兵尝试12(AP10)/13(AP8)；suffix17 level5有兵尝试14(AP12)；仅ID109 level6且目标condhigh4=0尝试15(AP10)。每项仍需真实谓词。成功提案写6F8D/6F8E/6F8F=2；失败门槛和未找到目标保留原先写入次序。

退却使用完整raw16兵数。君主record：兵<301且体<51；非君主首槽：本军总兵<1757且本军+3499<敌军时强制，否则兵<101且体<41；其他武将：兵<201且体<100，再抽0..99<70。负侧目的地052A；正侧扫描8个邻城，第一个同owner且10项名册中有FF的城市优先，否则最后中立城。不假定中立城名册必空，最终负号目的地失败。

补给预测下一原XY到service0，先把策略低nibble改7，再算资源。需求先`floor(4*本军raw16总兵/1000)`，再乘`(30-round)&255`取low16；预算`floor(gold*7/10)`；缺粮为u16回绕减法，不能clamp零。成本按城市实际quote计算；不足预算分支把全部budget换粮。全部资源加减保持u16回绕。

治疗预测到service2亦先mark7，gold<50仍保留该写入；足额先扣50，再拒绝抽low4>=11，得到35..45治疗。HP先u8加法回绕，之后才按原初始体力封顶。两个service预测都没有实际coordinatecommit的row15跳跃；不得因“合理路径”补修原算法。

## 原ROM差分与范围

最终 **2217 原CPU例、9项source guards，0失败**。其中完整原例2215，明确budgetprefix 2另列。CPUfixture包含完整策略、退却threshold角色、rawwordwrap、资源不足、治疗、全部requestbyte、basic/special真实pipeline、平局/passcounter和13个nativecheckpoint复用输入。每例完整8KiB SRAM与声明RAM一致；不声称CPU寄存器/mapper等价、自然玩法可达、完整frame执行或所有分支动态覆盖。

`validation.json`固定源码/validatorhash；`evidence.json`固定22段原bytes与immutabletables/共享源码依赖；`original-ranges.asm`明确两张inline表不是指令；`executed-instructions.json`列实际Oracle地址。原ROM保持pinSHA，只在验证脚本由py65执行原instructions。

```sh
.venv-trace/bin/python scripts/verify_tactical_strategy_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactical_strategy_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
