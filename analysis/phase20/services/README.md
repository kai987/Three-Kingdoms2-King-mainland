# 具名交涉服务与游戏源码整合

新增 [negotiation_services.py](../../../source/recovered/negotiation_services.py) 和 [negotiation_integration.py](../../../source/recovered/negotiation_integration.py)，继承冻结的阶段19内政服务及campaign/main/NMI/IRQ协调器。这里是保持原机器整数、寄存器和实际返回栈的可读恢复源码；没有生产用6502执行器或控制IR回退。

| 原物理银行:入口 | 可读方法 | 原行为 |
| --- | --- | --- |
| 10:B7A2 | `check_full_quoted_resource` | 查己方君主所在城，检查完整16位金／粮报价，返回原carry |
| 10:B7CE | `transfer_committed_resource` | 扣己城、加目标君主所在城；使用原提交缓存，保留先检查城市上限、后相加的顺序 |
| 10:B837 / B85F | `choose_negotiation_envoy` / `consider_city_envoys` | 扫30城各10槽，跳FF空槽和君主，选最高忠诚；同值选后遇者 |
| 10:B898 | `collect_neighboring_rulers` | 从原银行地图的8邻接槽收集外国owner，去重；忽略中立7与己方 |
| 10:B90A / B923 | `set_reciprocal_alliance_nibbles` / `set_target_alliance_nibble` | 双向packed外交字段写入；保留完整raw A路径，不自行限制成0..6 |
| 10:B955 | `find_leaders_city` | 按owner低3位及10个名册槽寻找该君主所在城；缺失返回FF/carry0 |
| 11:D080 / D307 | `count_owned_cities_and_prefix_officers` / `count_current_city_prefix` | 城数与每城首个FF之前的名册数量；与使者扫描跳过空洞的行为有别 |

继承的B619资格链保持：至少3位非FF君主、外交字节原逐次8位清carry加法结果为0、至少两个邻方、选城市最多邻方且target城市数大于own+2。报价由目标城数算出；目标controller整byte等于3才本地解决，其他值产生F8等待原UI消费者。接受必须回复0，其他非F8值拒绝。

原报价完整word使用042F/0430，但提交缓存003A/003B取低byte及零0431；本轮没有把原截断改成“更合理”的16位复制。模式0为金，非0为粮；原城市指针服务自身有资源cap副作用。原机接受案实际先收粮10113，后来cap9999，不能用最终值倒推没有入账。

## 验证分列

- [受控边界矩阵](validation.json)：625父case，600实际夹具caller RTS、24原循环等待、1严格缺依赖前缀。完整2KiB RAM（含栈）、8KiB SRAM、AXYP/SP/PC、顺序IO、实际4页PRG及N163一致。受控数值/调用帧不当作自然可达证据。
- [真实callee输入差分](../cpu/actual-caller-source-validation.json)：从正式原核10496帧实际保存的PC继续原字节到8个真实JSR输入；7个RTS、1个真实等待，零新PC/返回栈/数据准备，比较范围同上。该原CPU前序不是原核内部trace。
- [受控消费者序列](../cpu/consumer-sequences.json)：4个父序列，F8接受/拒绝、F9/FA通知，原消费者产生回复后原暂停调用返回。中断到达和手柄端口为显式软件输入。
- [真实F8保存上下文续行](../cpu/native-context-source-sequences.json)：2个父序列，初始F8来自原Nestopia真正产生的请求，实际B790经原CPU前序1条到B78B后源码等待；真实原UI服务在显式NMI/IRQ下回复0/1，原caller E188返回。每案85NMI/425IRQ；零准备字节、零代写reply/ready。
- [原字节目录](static-catalog.json)：本轮三个新增域共257个指令位置／549B，257个位置都被上述矩阵实际执行。位置覆盖不等于全部输入或硬件时序覆盖。
- [原Nestopia完整回放](../runtime/README.md)：接受/拒绝各真冷启动双跑，零数据写入与存档导入；该录像与CPU软件序列分别计数。

## 使用

```python
from source.recovered.negotiation_integration import NegotiationGameEngine

game, saved_registers = NegotiationGameEngine.from_nestopia_state(
    rom_bytes, original_state_bytes,
    read_ports={0x2002: 0, 0x4015: 0, 0x5800: 127},
    repeat_read_ports=(0x2002, 0x4015, 0x5800),
    controller_buttons=(0, 0),
)
services = game.negotiation_services()
# 仅在已确认的受支持入口开始。任意保存PC不自动成为一个可读调用边界。
# services.run_entry(entry, registers=registers)
# 按结果的真实等待/依赖合同，通过协调器处理后续NMI/IRQ后resume。
```

保存上下文构造器不执行ROM。PRG映射使用存档中的实际页；N163按原核127→0回绕。未恢复PPU/APU/时序，硬件输入必须公开。城市+1/+28..31保持正式名未知；旧模块、旧报告和历史IR均冻结保留，新增具名模块不等于全游戏已经全部可读化。
