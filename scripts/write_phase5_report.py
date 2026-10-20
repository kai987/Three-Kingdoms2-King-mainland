#!/usr/bin/env python3
"""Write the phase5 reports from retained validation counts and explicit scopes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase5'

def main():
    proof = json.loads((OUT / 'verification.json').read_text())
    assert proof['status'] == 'passed'
    troops = '''# 兵数低10位、原始高6位与数值溢出

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
'''
    (OUT / 'troops/README.md').write_text(troops)
    report = f'''# 第五轮：武将转属、内政AI与兵数/地形语义

本轮将名册/继承、城市字段、内政发展与月轮调度接入[统一可读源码](../../source/README.md)及[交互浏览器](index.html)。原文件与重建ROM仍逐字节一致，SHA256 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。代码是逆向复原实现，不是原开发源码或已独立运行的完整游戏。

## 已确认的关键结果

- **转属不能只调用忠诚函数。** bank10 A006/A009/A00C仅写忠诚；真正名册写入分别位于bank27 ACF0/AD41、bank25 BDBB、bank26 C099。独立恢复16个招入、迁移、删除、放逐、城首与继承服务，保留电脑/玩家差异、同城别名及原程序 quirks。
- **内政AI与城市UI是不同调度。** 全局007A=2→fixedE17D→pair10/11 A00F；NMI0078=2→pair27/28城市UI。AI三策略、预算、目标/武将选择及城市发展已恢复；pair25/26补出月轮、回合事件、君主AI桥接37个合法主子组合（32个不同目标地址）。
- **城市+16是タカラ（宝物数）。** 原文字、生产与卖出路径共同验证；不是AI预算。人口+6以百人为单位；土地+8/产业+14的原始word、三位UI及税收低10位须分别保留。后备兵+12、防災+10、統治度+11已确认。
- **兵数高位能由数值溢出产生。** 原驻军分配999/9999→1098/9900，列表显示74。完整核心受控回放及第二次逐文件hash重跑一致；目前没有支持独立训练度/状态flag名称的证据。
- **地形1规则和图块已确认，正式名称仍未确认。** 全30城335个合法格、7种raw tile。AI移动成本选择器实际重复读取byte8并以>=3选表；玩家按063C百人cache>=6，不能统一为同一规则。

## 可读源码分层

| 模块 | 本轮恢复的内容 | 明确边界 |
|---|---|---|
| [officer_transfer.py](../../source/recovered/officer_transfer.py) | 16个独立高层名册/忠诚/继承服务 | FC/FB对话等待、完整人事UI与全部owner结算链外置 |
| [domestic_ai.py](../../source/recovered/domestic_ai.py) | 城市schema、概率/选择/发展/税收纯规则；5735条AI及3052条调度IR | 外部CPU hooks明确；没有伪造NMI/PPU完成 |
| [troop_fields.py](../../source/recovered/troop_fields.py) | 分路径兵损、补兵、groups、后备兵归一和原溢出 | 字段效果合同；前缀不包含后续显示/费用 |
| [terrain_semantics.py](../../source/recovered/terrain_semantics.py) | AI/玩家移动报价及原flags | 不恢复完整攻击renderer或全部计略效果 |
| [game_engine.py](../../source/recovered/game_engine.py) | 所有新模块使用同一份CPU寻址RAM/SRAM | 直接入口，不声称一次调用就是完整NES帧 |

高层玩法规则没有原ROM入口adapter或空渲染成功函数。控制IR不从ROM取opcode执行，但为保留字节回绕、CPU flags和栈，仍使用提升后的机器级形式。验证器在外部依赖处可明确调用原ROM adapter，这种差分验证不证明该helper已经独立复原。

## 转属和继承的程序差异

实际招入不从其他城市删除同ID；完整跨势力交易仍需上层协调。放逐清状态并写所在地，空城整byte0写7；删除路径OR3，空城保留byte0高5位。电脑继承的低忠诚离队清状态、写所在地，但保留名单ID；玩家路径实际删ID且不写所在地。AI没有继承人时只写君主FF并请求FB，不能由该前缀推断全部城池已经中立。

安装继承人请求FC，没有继承人请求FB；两者等待6F8B=1。模型返回待处理事件，不自动设置确认值；玩家D3/C2/D4对话也外置。统一入口另外验证了pair25/26桥接的原计时段：受控sub11的FC经480次调用、sub12的FB经240次调用，由CBBD..CBBF实际写1；共720次逐次匹配原ROM，没有注入ack。这是控制器调用次数，非视频帧；前置C7E0跨银行绘制依赖仍外置。详见[转属完整报告](transfer/README.md)。

## 内政与年度循环

发展城市游标先递增、30城回绕，第三次回绕结束AI轮。付款、随机游标、失败时已扣款与8/16/24位回绕均保留。AI预算为6F5D，初值读取明确20byte表；不把越界索引概括为普遍城数×10。

每7君主slot递增月，每12月递增year byte。仅monthindex3（四月）收金、9（十月）收米，非每月收入；治理率50/60/70/80/90/100按原阈值选择。原A540/A582均为真实RTS，没有替这份ROM补造工资/军粮扣除。土地/产业初始raw9999，UI999，收入低10位783；税收按原24位乘法、整除、低16位加法及最后封顶9999执行。详见[内政/调度报告](domestic-ai/README.md)与[城市schema](domestic-ai/city-schema.json)。

## 兵数与地形证据

[兵数报告](troops/README.md)包含原拨兵画面、输入计划、原字节范围和重复回放。这里只证明受控数值条件下的原程序行为，不声称已经自然游玩到该状态。

[地形报告](terrain/README.md)包含相机归零后的三个原核心战场与普通攻击背景；122个可见16×16地图格逐像素核对，攻击背景640个8×8tile独立核对。地形1的土色画面和成本不足以证明名称为道路/沙漠；`CLASS1_FORMAL_NAME=None`。首次相机64的错误坐标假设已标记为rejected诊断，未用作结论。

## 验证结果与复现

[联合回执](verification.json)汇总 **{proof['rom_differential_case_count']:,} 个实际原ROM CPU差分案例、0失败**：转属6496、内政/调度6936、兵数33603、地形36667。其中调度13例明确停止在reset1例、PPU6例、NMI6例的明确边界，其余209个调度案例实际返回。不能把有界前缀或边界比较当作完整游戏帧。

地形另有892项文件/图像检查，分开计数；完整核心兵数回放2050帧重复hash一致，不重复加到CPU案例总数。新统一入口验证见[source-integration.json](source-integration.json)：989项检查、0失败，其中982项原ROM对照、7项API契约。默认控制器134条完整返回，77条止于真实未恢复依赖；上述720次host计时调用单独计数，不加进83702的主矩阵。此前8个统一战斗/攻击/单挑案例也重新通过。

REA实际新增pair10与pair27分析，load image验证成功，分别159/90个候选函数；连同此前5组共7组760个候选函数，固定bank31另67个。候选伪C是辅助材料，不是已确认可编译源码。汇编/伪代码/evidence保留于[REA银行对目录](../rea/pairs)。

```sh
.venv-trace/bin/python scripts/verify_officer_transfer.py
.venv-trace/bin/python scripts/verify_domestic_ai.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
.venv-trace/bin/python scripts/verify_troop_fields.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
.venv-trace/bin/python scripts/verify_terrain_semantics.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
.venv-trace/bin/python scripts/verify_phase5_integration.py
python3 scripts/verify_phase5.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
python3 scripts/write_phase5_report.py
python3 scripts/make_phase5_portal.py
python3 scripts/package_results.py
```

各独立报告解释自己的fixture准备、比较范围和命令参数。归档包含源文件、报告、控制IR、原字节证据、资源和一致重建ROM；排除工具链、虚拟环境与exploratory。本轮仍有正式地形名称、城市byte1/+27..31、部分owner交易、外部图形/硬件依赖和完整主循环未恢复。直接AI flag1入口需要有效战后city/名册scratch；原菜单0038=222的字段不能当city。PrgDataMemory是逻辑内存模型，未模拟上半SRAM写保护；无效指针域的差异保留为诊断，未改oracle保护设置来掩盖。
'''
    (OUT / 'README.md').write_text(report)
    print('Wrote phase5 and troop reports')

if __name__ == '__main__':
    main()
