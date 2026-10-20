# 第五轮：武将转属、内政AI与兵数/地形语义

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

[联合回执](verification.json)汇总 **83,702 个实际原ROM CPU差分案例、0失败**：转属6496、内政/调度6936、兵数33603、地形36667。其中调度13例明确停止在reset1例、PPU6例、NMI6例的明确边界，其余209个调度案例实际返回。不能把有界前缀或边界比较当作完整游戏帧。

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
