# Phase9：陥穽、火箭、落石独立效果源码

三项实际 effect handler 的玩法逻辑已还原为 `IndividualTactics`，不解释 IR、不执行 ROM、不用图形空函数。它是重构源码，不是原作者源码。入口前提是 B02B 的真实结果区清零已经完成；目标资格、玩家/AI扣AP、消息与图形流程另有边界。玩家落石资格排除 terrain5，AI资格要求 terrain5，两者不影响共用 B3B6 的概率及效果体。

| ID | 原 bank12 入口 | 成功效果 |
|---:|---|---|
| 1 陥穽 | B0DD | B7BE概率；B0EB计算HP损失；存报告；sub++ |
| 5 火箭 | B243 | 对侧raw16军粮乘10..14%取整，加知力/5；饱和扣粮与报告；sub++ |
| 9 落石 | B3B6 | 先完整HP阶段，后以实时record计算兵损；最终sub=7 |

HP伤害的武力+知力先发生8bit回绕；死亡XP使用两者完整16bit和，不能混用。HP=0（包括0扣0）设record11|3；活分支完整RTS。死亡在 B615 调用真实 D6CC 前停止，返回 dependency。只有该 CALL 实际返回后显式调用 `after_death_graphics(map_refresh_returned=True)`，才计算杀将XP、报告死者ID、清槽和首个匹配缓存，并继续原handler。False/漏传不会推进；这不是异步任务确认。原D6CC仍未恢复为高层图形源码。

死亡路径没有 C91E 的阵营人数/总兵记账，也没有城市/君主/名册转属；尸体record兵字节不被HP阶段清除。落石的后续兵损在死亡清掉0664后按真实 F2D7(FF) 指向6FB4的AI工作SRAM，保留该原quirk；不把旧死者ID补回。同槽/同record与杀将升级后武力变化按原顺序保留。兵损读取low10并清byte9高6；火箭读取完整16bit军粮，不读取目标兵数。

最终 727 次原CPU比较、11 guards，0失败：445完整RTS例，141死亡前缀与141真实图形CALL后续分别计数。每例完整8KiB SRAM和validation声明RAM一致；不声明寄存器、flags、stack、mapper、arithmetic scratch或完整NMI等价。141次实际D6CC在这些输入中均未写SRAM或声明玩法RAM，仍由验证器真实执行并记录host字节差异，绝不假完成。自然核心施放证据在本阶段独立runtime报告，不由这组CPU fixture推导。

`original-ranges.asm`明确EE07后inline entry word和XP阈值表不是指令；`evidence.json`逐段固定ROM偏移/bytes/SHA与已读REA存档。`validation.json`固定本源码及validatorhash，`executed-instructions.json`列949个实际原指令位置，不表示所有分支动态覆盖。

```python
effects = IndividualTactics(shared_memory, IndividualData.from_rom(rom))
result = effects.apply(9)
# 如果result为dependency，host实际执行D6CC后：
result = effects.after_death_graphics(map_refresh_returned=True)
```

```sh
.venv-trace/bin/python scripts/verify_tactic_individual_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactic_individual_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
