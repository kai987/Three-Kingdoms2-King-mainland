# 城市归属变更：有界事务、原指令与字段副作用

ROM SHA256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。原文件只读，未修改。

新增 `source/recovered/city_ownership.py` 是手工恢复的独立玩法源码，不是原开发源码，也不执行原ROM或包装CPU入口。7个新增直接事务覆盖电脑占领写回、临战武将再安置、空城殖入、撤城、成功后的单武将跨城转属、空城动作结束检查、单位退却。另组合1个此前已恢复的纯Python战后归属/城首函数，并明确保留其原范围。

## byte0的三种规则不能合并

| 写入形式 | 实际入口/条件 | 高位行为 |
|---|---|---|
| `(old&F8)\|ruler` | AI A90B、AC11、B354 | 保留高5位，替换低3位 |
| `(old&F8)\|7` | AI撤城B429、旧删除BDFE | 保留高5位，中立化低3位 |
| `(old&F0)\|ruler` | 旧战后BBDD、退却BC90、旧分配D296 | 保留高4位，同时清bit3 |
| `byte0=ruler` | 旧AI分配BCD9填入空邻城 | 整字节替换，清除所有高位 |
| `byte0=7` | 新BAE0/D181；旧C0D5/CC0F | 整字节替换，清除所有高位 |

高5位仍按原始位保存，没有赋予未证明的旗标名称。多数比较用owner低3位；旧BC00城首函数读低4位，常规已证明域要求该路径bit3为0。现有13个已发现并复查的玩法写点全部列于 `evidence.json:owner_writers`，既包含本轮新增，也包含旧模块中的写入。该名单不是完整ROM指针数据流审计的证明。

## 新增高层服务

| 方法 | 实际原函数范围 | 输入/已恢复作用 | 明确停止边界 |
|---|---|---|---|
| `commit_ai_capture` | bank10 A8FC..A90C | 0038城、6F03君主；必须来自6F8C零分支；D105的金/粮9999上限也保留；F8写城主 | A90D的D249驻城搜索与CA19继承检查外置 |
| `relocate_after_ai_battle` | ABA3..AC66 | 先选自己名下且首FF人数最少、未满10的邻城；平手先项；否则选最后一个中立邻城。插入首FF、F8写城主；0042=0才调忠诚 | 返回caller，旧名册/active slot删除与状态2/驻城更新不由此段完成 |
| `colonize_city` | B287..B356 | 按传入金/粮全word回绕扣/加、按D105时机夹9999；搬`0037-2`位随员；从源槽18..26挑忠诚最高，平手后项；源首槽17不参与，目的名单从17覆盖；源名单压紧；目标F8写城主 | 先前选空城、选择金额、判断足额不在此核心 |
| `withdraw_city` | B3B1..B42A | 合并钱粮全word、回绕后**没有最终目的上限夹取**；清源钱粮；搬源名单直到首FF；目标逐次搜索FF；源F8置7；返回原AP成本4+2×人数 | B42B预算扣减/栈展开与B17D继续周期外置 |
| `transfer_persuaded_officer` | BA8D..BAE1 | 目标城追加、按新君主徳调忠诚、从原城删首个匹配并压紧；原城空则整byte7；保留武将状态/byte5及君主驻城 | BAE2起原君主反应/外交处理外置；此前成功条件、正式菜单名未在本轮证明 |
| `finish_empty_city_action` | bank28 D16B..D182 | 0473动作码=2且0471城首槽17为FF时整byte7；后来槽仍有人也照写7 | 更早的UI/input/D568与D183光标尾段外置；不擅自把0471称迁移源城 |
| `retreat_unit_to_city` | bank12 BC2D..BC92 | 首FF插入（满时偏移27）；清6个战场数组、匹配的04D8/04DC缓存；slot0/10保存逃离记录052B/052C；目的城低3位7时F0写当前side君主 | BC2A先调用的C91E helper外置；武将状态、钱粮、首将和君主驻城没有在此段改写 |

`transfer_persuaded_officer` 的名称表达成功后跨城名册变化的代码推断；没有把未经字形联接的计略菜单名称当成正式名称。它是完整的**有界成员交易**，区别于此前仅调忠诚的bank10 A006/A00C，也区别于bank27 ACF0只招入而不删除旧名册的核心。

新增事务均没有直接改君主byte1驻城；只有逃离跟踪052B/052C、名册首槽或owner变化。`finalize_battle_ownership` 组合此前bank8 BBB8纯源码：0514==0时F0写被攻城归属，再修正本城/邻城首槽君主；并不把首槽交换等同君主驻城写回。

## 需保留的边界行为

- AI临战再安置先扫描自己空位，最后才使用中立城，不优先“最近”。扫描D105会对被拒绝城也夹钱粮9999。中立候选保留最后一个，未检查其名单空满；查FF可走出10槽，原Y按8位回绕。
- 无去处时状态低2位清0。E89A使用游标54，`RNG&7=0`留本城，1..7选择邻表0..6；邻表7永远不会由此放逐分支抽中。抽到高位终止码才重抽。这和旧战后随机8邻分配不同。
- 殖入第一槽直接覆盖，忠诚排序无HP/状态过滤，源首将不参与。本API已验证传入0037为3..10且源后续槽有足够记录；0037是上层计算的分配基数，不是源城现有人数，原B168另读D304人数判断是否需要先补援；额外测试同址/金额异常的有界算术，不声称上层允许这些操作。
- 撤城目标FF扫描无容量边界，会走出名单；原程序按字节Y搜索，而非Python列表append。测试包含满目标和同城源/目标别名，保持顺序写入结果。
- 撤城仅返回AP成本，未默许D152预算和栈展开成功。新单武将转属也未默许后面的原君主反应完成。
- 城市中立化不等于势力消灭。leaderFF、controller、外交清理、胜利条件由独立 `faction_lifecycle` 研究范围处理。

## API

```python
from source.recovered.city_ownership import CityOwnership, OwnershipData

rules = CityOwnership(memory_64k, OwnershipData.from_rom(rom_bytes))
rules.commit_ai_capture(4, 2, branch_zero=True)
result = rules.withdraw_city(3, 4)
# result['pending_ai_budget_cost']由上层明确处理
```

所有方法使用同一64K地址空间。常规验证域：城市0..29、君主0..6、武将0..236、战场槽0..19。金额用原16位值。`branch_zero`、`adjust_capture_loyalty`、金额/分配基数、`action_mode` 均需明确传入。CPU flags、所有临时指针、stack/mapper准备不由这些语义API冒充。

## 验证与覆盖限制

`validation.json`：**2,176个实际原ROM CPU差分案例，0失败**，另3项源模型域检查单独列出。每例比较全部8192B SRAM；另对相关战场6数组、缓存、逃离字段、游标54、6F73缓冲、0037计数及AP成本做比较。

有界入口中B3B1开始前A必须已经是目标城（原B3A9加载），不能只设0038后默认A=0。脚本明确提供这一CPU前提。金/粮极端word、8位忠诚平手、城byte0高位、同址别名、目标容量溢出遍历、首槽FF但后槽有人均有实际执行案例。算法调用旧纯Python忠诚/压紧服务，没有在源码中安装original-ROM adapter；原6502只用作验证端。

```sh
.venv-trace/bin/python scripts/analyze_city_ownership.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
.venv-trace/bin/python scripts/verify_city_ownership.py
```

`evidence.json` 保存8段原字节/摘要、13个writer的位置与原字节、输入和边界；`original-ranges.asm` 可逐条复查。

未覆盖：完整空城殖入/撤城目标选择和付费决策、完整外交/人事/迁移UI控制、BAE2外交响应、D249/CA19后续、全部动态指针/未播种代码中的潜在owner写入。旧BCD9/D296/BDFE/C0D5/CC0F继续由此前源码负责；CC0F的空名单分支虽静态明确，正常完整名单离队仍保留ID，因此本轮未把该分支算成有效常规动态覆盖。启动模板复制属于初始化，未计入13个玩法writer。

本轮没有新增完整核心中的自然占领/退却/外交导航实证，也没有把CPU oracle当视频帧或PPU验证。
