# 城市门槛、资源上限与支付辅助服务

本轮新增独立手写 [CityThresholdServices](../../../source/recovered/city_threshold_services.py)，恢复 physical11 的 D105..D12C、D36F..D3A8、D69D..D6CF，共 149 字节、85 个指令位置。已有 physical10 BD7A 完整补兵/发展消费者继续复用阶段18具名源码，不计为本轮新增恢复。

| 入口 | 具名方法 | 精确作用 |
| --- | --- | --- |
| D105 | `city_pointer_and_resource_caps` | 用 raw8 A 构建 `6000+32*A`，先限制金/粮到9999，再返回 owner低3位；后续归属检查失败也不撤销上限写入。 |
| D69D | `cap_city_word` | 顺序检查 +2/+3 金、+4/+5 粮；>=10000 时写9999，低字节先写，金先于粮；不写 +1。 |
| D36F | `pay_city_gold` | 原真实调用帧、可选随机加费、16位费用回绕、扣金或 CLC 拒绝；拒绝保留先前上限/RNG/费用/临时区效果。BD7A 父流程忽略该 carry。 |

`run_entry(entry, registers=actual_registers)` 保留已有真实 caller，未提供服务时停在真实依赖处，不种植返回地址或确认信号。PUBLIC 沿用 CityRecruitmentServices 并增加上述三个入口。`threshold_snapshot(city)` 是仅供实际城市0..29的只读检查接口，不声称 CPU 寄存器/栈/mapper 合同。

原 BD8D 调 D105 后，20/21 是城市原基址，并未偏移1。BD97 比较 `LE16(city+1,city+2)>=300`，其中 +2 是实际金的低字节。精确条件是上限处理后的金低字节>=2，或低字节==1且不明 +1>=44；低字节0总拒绝。金高字节不直接参与该比较，但在更早 D105 的资源上限中有作用。+1 的正式名称仍未知，不能将该判定改称金>=300，也不能称支付300。

完整父消费者保留全部10槽、FF洞跳过、low10兵数、首将固定评分100与后遇相同评分优先、库存相等仍进入购买、8位购买费/16位库存回绕、付款失败 carry 被忽略、raw1000写回与随后预算扣2的实际顺序。原库存足够的 Native 过门槛组不在此补兵时扣金；后续发展付款单列。

验证 [validation.json](validation.json) 实际通过 3161 原CPU父案：3160 RTS、1 严格缺 E88A 的 RNG 依赖前缀，另 5 个源码 guard。逐案比较全部2048 RAM（含闲置栈）、8192 SRAM、AXYP/SP/PC、顺序端口读写、四个实际PRG页与N163 RAM/地址/自增；Source 原CPU callback=0。受控 raw城市30..255、栈回绕、全部NZCV、费用不足/回绕、上限影响后续门槛等仅是明确的软件CPU数值边界，不是 Native UI 可达性证明。只读公式另做65536输入模型检查，计入 Source CPU案数0。

新增85个静态位置中动态命中 85 个；位置命中不等于全部路径或输入已证明。全部原字节/含16字节头的ROM偏移在 [static-catalog.json](static-catalog.json) 与 [original.asm](original.asm)。

正式 Native 六组由独立原核心/观察核心双跑提供，1组天然金额8888/+1=0，5组明确准备金币257/258/512或 +1=43/44。新导出24个独立原CPU调用输入（4自然、20诊断），使用真实保存PC/MAP/N163，无新NMI/IRQ、PC/RNG/request/ready写入。详见 [调用来源](../cpu-threshold/README.md)。它们支持相同门槛和补兵效果，不声称后续随机付款/最终金的整帧 Native 等价。未确认专用 +1 producer；有限未观察写入不能证明字段无用。

可复现本轮命令（不运行旧生成器）：

```sh
.venv-trace/bin/python scripts/analyze_city_threshold_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --capture-native
.venv-trace/bin/python scripts/verify_city_threshold_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_threshold_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
