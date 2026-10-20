# 可读源码与本次原机证据

复用冻结的 PostbattleEarlyServices；本包没有新增玩法算法，也没有新跑 Source。以下是实际 Native 链到既有可读函数的对应，不是单实例 Source 连续性验收。

| 可读函数 | 原代码 | 新证据 |
|---|---|---|
| [allocate_defeated_attacker](../../source/recovered/postbattle_early_services.py#L114) | BD67 | mode2实际分派、源城找空槽及真实返回 |
| [collect_side_officers_and_captives](../../source/recovered/postbattle_early_services.py#L160) | BDCD→BE54 | 真实生成[67,FF×20] |
| [prioritize_original_commander](../../source/recovered/postbattle_early_services.py#L202) | BE55→BE89 | Y0自交换两次67→67；非平凡重排未验 |
| [fill_pointed_city_roster](../../source/recovered/postbattle_early_services.py#L138) | BD96/BDB8→BDAA | 6214:FF→67；同址dummy读单列 |

实际链：BB36 JSR BC46 → BC49 JSR EADE（两PLA消费此层栈，EAF4间接JMP）→ BD67 → BDCD → BE54 RTS → BE55/BE89 → BD73/F2AF → BD8E JSR BD96 → BD99/F2AF → BDB8 → BDAA RTS → BD91 → BD95 RTS → BB39。

BDB8是BD96内部store标签，不是独立callee。BB39返回SP恢复EE；callee入口SP为EC，BD96入口EA。raw栈字与当前真实JSR两次Push8分别留证，未用ret−3猜实际调用者。

武将67的完整12字节和战场unit10未改变；这里只验证战后归城分配。玩家131随后由13:D4BA回city11，另有两次BC3C/BC43同值写；不能并入67的分配或在野招募。
