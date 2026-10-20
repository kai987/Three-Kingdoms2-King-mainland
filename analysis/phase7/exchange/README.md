# 战术提案与战场消费之间的内存协议

`source/recovered/tactical_exchange.py` 独立还原bank12的五段内存效果，与AI决策及完整NMI分开。构造 `TacticalBattleBridge(memory, TacticalExchangeData.from_rom(rom))`；GameEngine通过 `tactical_bridge_rules()` 共用相同RAM/SRAM。

| API | 原机器码范围 | 明确范围 |
|---|---|---|
| `request_decision()` | BEA6..BEB9 | 只在0087为负时写phase0与提案字段0、sub++；不强制0087 |
| `route_proposal()` | BF01..BF09 | 读取status0..4，真实路由表为3/5/8/12/13；止于BF0A，未排结束消息 |
| `commit_movement_coordinates()` | BF26..BF7B | 已请求图形之后的坐标后缀；写方向scratch、x/y及sub++，不扣AP |
| `apply_movement_cost()` | BF83..BF97 | 已请求图形之后的AP后缀；AP减6F97按byte回绕，转battle4/sub2 |
| `request_secondary()` | A51F..A534 | 等phaseFF后写phase1、actor=0509、sub++；不制造效果成功 |

`proposal()`只读解释6F8D/E/F。status0的6F8D是上/下/左/右方向，status1是普通攻击目标槽，status2是计略ID并使用6F8E目标，status3是不提交行动，status4是撤退目的城。同一raw数值不表示同一动作；例如status0/action3是右移，不能称为计略「要撃」。

坐标后缀保留u8回绕和存储Y跳过15的原行为。14向下到16，16向上到14；自造输入在Y15水平移动时原后缀也会将其变为16，不把这一边界当自然地图上的常规动作。

**655个原CPU对照、3项源码guard通过，0失败。** 每例比较全部2KiB RAM和全部8KiB SRAM，仅证明内存效果，不包含CPU寄存器/flags/栈合同。96个坐标例、42个AP例分别对照实际原后缀；256个0087请求例及256个phase请求例覆盖条件比较和byte回绕。5个路由例核对原表。源码拒绝的非法status/slot没有执行原表外读取。

图形前序BF1F/BF80、camera/input前序BEBA、消息后序BF0E仍由调用者真实执行；这些API不代用renderer，也不替调用者确认工作完成。自然整机frame485的坐标、486的AP由完整原核心实际推进，见[700帧回放](../runtime/README.md)。根整合只另核对三项最终字段，未把后缀调用算成原核心帧。

复现：`.venv-trace/bin/python scripts/verify_tactical_exchange.py`。原范围字节、SHA与完整回执见[validation.json](validation.json)。
