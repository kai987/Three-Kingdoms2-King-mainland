# 兵数低10位、原始高6位与数值溢出

原武将记录 `+8/+9` 是16位存储。列表读法为 `raw & 0x03FF`；`raw >> 10` 只命名为原高6位，不编造训练度或状态。源码：[troop_fields.py](../../../source/recovered/troop_fields.py)。

## 分路径读写

| 原入口 | 已恢复语义 |
|---|---|
| bank8 BA4E | 按低10位饱和扣兵，保留原高6位；写AI损失和结果缓冲 |
| bank12 B68B..B6C0 | 普通兵损前缀按低10位扣兵，清掉原高6位 |
| bank10 BF95前缀 | 招兵先 `u16(raw+increment)&1023`，再封顶999；increment=0也会规范化 |
| bank8 A54B..A555 | 出征补兵前缀直接写1000，清原高位；停止在后续费用/预算前 |
| bank15 CA72/CAB6 | 汇总10个攻击group，跳过FF，高byte=`oldHigh&FC OR sumHigh`；不擅自mask异常sum |
| bank11 CE75前缀 | 对全16位减去loss byte，再按高byte BPL做有符号裁剪 |
| bank26 D987 | 按全16位除100，处理余数与后备兵池；池封顶10000，保留原低byte溢出扣减规则 |
| bank26 D805..D8B3 | 驻军分配核心：右键拨入、左键归还；保留调用前的容量检查顺序 |

这份ROM初始237条记录的高6位全0；已观察的三个自然快照也未出现非零高位。这只能描述这些数据，不能证明游戏运行中永不出现高位。

## 原驻军流程能产生1098

原D805先检查当前兵数不大于999，随后D987尝试把兵数降到100的倍数。后备池接近10000时，余数无法全部归入；程序随后仍拨入100，未再次检查结果。

```text
输入：兵999、后备9999、右键
归一：兵998、后备10000
拨入：兵1098 (0x044A)、后备9900
列表：1098 & 1023 = 74；原高6位 = 1
```

这是原机器码的数值生产路径，说明高位至少可能是溢出的兵数。不同读写路径会保留、清除或按全16位运算；不能统一解释为独立flag，也不能把所有场合改成低10位算术。

## 完整核心的受控回放

[回放日志](core-fixture/validation.json)从原军政菜单存档开始，仅准备两个SRAM word（曹操兵1000→999、城市11后备9999→9899，共4byte），RAM与ROM均不改。随后普通手柄操作征100兵、进入拨兵界面、按右、确认退出；总计2050帧。

![原ROM拨兵界面显示1098](core-fixture/allocation-overflow.png)

第1766帧的画面显示1098，配对SRAM读回1098。第2050帧退出后的地图不显示兵数，但配对SRAM仍保留1098，城市后备为9900。退出后042C被其它流程复用，不能当作后备兵池继续解释。

独立重跑2050帧，三个检查点的PNG/RAM/SRAM/state共12个非空文件hash全部一致，见[重复核对](core-fixture/replay-validation.json)。完整核心回放与CPU案例分开计数。该证据是显式准备数值条件后的原程序行为，尚未证明自然战役可达性。核心不提供VRAM memory-region，本报告未声称直接读取VRAM。

## 验证与复现

[validation.json](validation.json)：33603个实际原ROM CPU差分案例、0失败。比较完整SRAM或每条纯函数声明的word/buffer；前缀在后续显示、付款或预算前明确停止。flags/完整栈等不属于这些高层字段API合同。

[evidence.json](evidence.json)保存8条真实入口范围、298条指令的原字节与hash。84条LDY8/9原始匹配只作为候选，不是全ROM完整引用覆盖证明。早期从任意位置线性解码及方向键试验已移到排除出归档的exploratory目录。

```sh
python3 scripts/analyze_troop_fields.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
.venv-trace/bin/python scripts/verify_troop_fields.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
python3 scripts/capture_troop_overflow.py --help
```

高位的独立旗标语义仍未确认；这轮明确确认了数值溢出来源，而非为全部6位赋予虚构名称。
