# Phase7：战场AI可读决策段

新增 `source/recovered/tactical_decisions.py` 是根据6502行为独立重写的玩法算法，并非原始源码。它与单独的完整CPU控制器分开：当前模块恢复扫描边界、两个轴方向的移动选择、相邻攻击、最近候选前缀及已部署持续效果的应用。

## API和验证边界

构造 `TacticalDecisions(shared_memory, TacticalData.from_rom(rom))`；同一64K内存被直接读写。`decision_state()` 返回提案和扫描字段。

| API | 原入口/终点 | 恢复范围 |
|---|---|---|
| `prepare_actor()` | A02D→A099/B933/RTS | 扫描前缀：跳过inactive、异侧、空武将；尝试计数，控制路由 |
| `finish_actor()` | A062→A099/RTS | 以真实现有6F8F结果计数、yield或rescan；不替调用者制造成功 |
| `plan_movement(x, normalized_y)` | A60C→RTS | 完整两个轴方向选择、地图/地形/AP报价、相邻占位、攻击fallback及提案写入 |
| `quote_direction(direction)` | A740→RTS | 完整坐标边界和报价；不扣AP |
| `adjacent_attack()` | A8A8→RTS | 完整AP>=2及上/下/左/右第一敌人提案 |
| `nearest_enemy(radius)` | A17B→A1A8/A1C0 | 候选前缀，动态核对原radius2分支；不含后续目标加载/fallback |
| `secondary_effect()` | B933→RTS | 完整缓存持续效果检查、实际扣兵、042C..042E及结束写回 |

原ROM差分 **2038 次**，另 **4 项**源输入guard。每例比较完整 **8,192B SRAM** 和RAM `0020..002F`、`042C..042E`。方向报价还比较有效报价的A/X/Y和NZVC；越界报价比较carry。其他API不声称寄存器/栈/mapper等价。原Oracle执行真实ROM的地图、随机及算术辅助函数，无成功替换、无ROM补丁。

## 扫描及提案协议

`6F8B=FF`直接返回，`=1`交B933第二阶段，其余值扫描。`6F94`是下一槽号，`6F96`是已尝试合格actor次数，`6F95`是返回status3次数。三计数保持u8回绕。扫描到20若两个计数不相等，三者归0重扫；相等则status3、cursor0、controlFF。非3结果立即controlFF，交上层消费，不视为下一actor。strategy表有8项；不能因`AND0F`而虚构16项。

status0将6F8D解释为方向，cost在6F97；status1将其解释为普通攻击目标槽。status2是旧ai.py已验证的计略ID/6F8E目标。移动提案不改坐标、不扣AP；其上层提交由根模块另行恢复。

## 必须保留的原实现行为

移动不是广度寻路：只比较朝目标的两个轴，较大位移优先，位移相等垂直优先；再按成本稳定排序。原SBC/BPL字节差不是普通整数绝对值。原来已经位于目标仍可能选择向下移动。反向记忆6FB5被复制至2F，但本段不读取2F参与选择。候选占位时只有完整strategy byte等于1或5才允许敌人fallback；fallback先写目标后检查AP，故失败status3仍可能改6F8D。condition0650非0阻止空位移动。

报价保留两次读取同一officer byte8的代码：byte8<3用第二表，否则第一表；byte9不参与。地形affinity3的原0成本保持为原编码边界，不能给它编造新能力。

B933的缓存组由当前side选0/4；B965先比较actorX，再用slot0/4的Y而非actorY。范围候选为0也拒绝。只有actor地形0继续。它先拒绝抽样到0..100，接受值及IQ差阈值随后被覆盖，但随机cursor消耗保留；再抽0..10。作用量为`floor(cachedIQ*(30+draw)/10)`加按整个packedbyte11执行的带carry字节倍率。扣兵针对10位，原byte9上6位保留。该孤立段称“已部署缓存效果”；[跨段来源证据](../secondary-origin.json)另确认它至少消费计略11「十面埋伏」建立的缓存，没有增加自然成功施放的验证范围。

## 可复现

```sh
.venv-trace/bin/python scripts/verify_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

`evidence.json`保存每段ROM偏移、原字节、SHA、前置条件及完整/前缀终点；`original-ranges.asm`保存原指令；`validation.json`为差分回执和源码hash；`executed-instructions.json`是实际执行地址，不等于全部静态控制器覆盖。地图数据只提取原表和tiles，玩法源码不会执行ROM或回退到ROMadapter。

本轮CPUfixtures明确控制actor、地图、occupancy、AP、RNG及缓存。未声称未修改的完整战役自然可达，也未声称画面/中断/硬件等价。全部8strategy编排、退却/士气/补给策略由完整CPU控制器继续执行；此模块尚未高层化这些整段策略。
