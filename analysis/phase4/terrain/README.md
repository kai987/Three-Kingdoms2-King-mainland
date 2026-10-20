# 地形编码、村落服务与原菜单字形

本目录依据只读原 ROM 的字节、6502 执行结果和原 Nestopia renderer 整理，源码是复原模型，不是取得的原始游戏源码。ROM SHA-256 为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。所有下列 file offset 包含 16 字节 iNES 头。

[结构与原字节证据](evidence.json) · [全部合法格 CSV](all-legal-map-cells.csv) · [原 ROM 对照结果](validation.json) · [可读规则源码](../../../source/recovered/terrain_rules.py) · [服务控制入口](../../../source/recovered/map_service_machine.py)

## 120 个地图 chunk 的合法格

城市 ID 的原始域为 0..29，每个城市通过 bank24 `$DF4A`、file `0x031F5A` 的指针表取得四个 chunk，合计 120 个 chunk。移动边界是 `0≤x<31`、`0≤y<20`，并跳过 `y=15` 的属性行；下半地图的屏幕纵坐标使用 `16×(y−1)`。因此每城 589 格，全部 30 城共 **17,670 个合法格**。32×32 查表域中的属性/未使用数据单独计数，没有当成可玩地形。

原始查表入口为 bank8 `$B6EF`，file `0x0116FF`；chunk 指针在 `$B7CB` / `0x0117DB`，PRG bank 选择表在 `$B8BB` / `0x0118CB`，128 字节 tile→raw class 表在 `$B74B` / `0x01175B`。玩家 bank13 `$DB9E` / `0x01BBAE` 的分类表与此 128 字节逐字节相同。

| raw class | 合法格数 | 机械含义与名称置信度 |
|---|---:|---|
| 0 | 1,673 | 独立移动类别；森林为原画面支持的 strong inference |
| 1 | 335 | 独立移动类别；正式地形名称 **unresolved**，只观察到平滑土色外观 |
| 2 | 9,603 | 独立移动类别；平地为画面支持的 strong inference |
| 3 | 2,924 | 独立移动类别；水域为画面及水类计略条件支持的 strong inference |
| 4 | 3,048 | 独立移动类别；山地为画面及适性成本支持的 strong inference |
| 5 | 30 | 每城一个据点格；城/城砦为位置、画面及计略条件支持的 strong inference |
| 6 | 26 | **confirmed 合法事件标记编码**，对应 raw tile `$79` |
| 7 | 22 | **confirmed 合法事件标记编码**，对应 raw tile `$7A` |
| 8 | 9 | **confirmed 合法事件标记编码**，对应 raw tile `$7B` |

6/7/8 每类每城最多一格，57 格都在合法移动域。玩家 `$DB46` / file `0x01BB56` 与 AI `$B6E5` / `0x0116F5` **都将 raw≥6 折算为 class2**。它们不是三个新的移动地形。原 BG metatile 字典在固定 bank31 `$F477` / `0x03F487`，四个 8×8 tile 为一组；普通地面 `$39`、据点 `$61`、标记 `$79/$7A/$7B` 的 BG 四字节全部是 `22 23 32 33`。可见的建筑造型还依赖单独 sprite 绘制，不能只靠这个 BG 四元组给标记命名。

## 兵量缓存与适性作用域

bank13 `$DB03..DB45` 生成 `$063C[slot]`：有效单位为 `troops_low10 // 100`，空 `$0664[slot]=FF` 写 `FF`。`troops_low10` 只取武将记录 byte8 与 byte9 的低 2 位；不能将初始 raw LE16 兵数无条件解释为 10 bit。

bank12 `$A7E7` 以缓存 `≥6` 选第一移动成本表，否则第二表。正常非空单位等价于有效兵量达到 600，不是兵种或当前位置类别。武将 byte11 的中 2 位选择适性列，0/1/2 的原字形为「平/山/水」。编码3仍是未定义适性；表中零成本确实存在，但没有相应合法初始字段或正式名称，不能扩充成新能力。

`movement_quote()` 先按玩家规则折算 raw6/7/8，再返回 cost、8 位扣减结果和进位所代表的够不够行动点。该 API 拒绝属性行/未使用格。对照覆盖全部 9 个 raw 类、4 个适性编码、兵量边界 `0/599/600/1023/1024/FFFF` 与五种行动点，执行真实 `$DB03→DB46→A7E7` 流程。

## 村落触发与分类

服务类别来自 **另一张坐标表**：bank17 `$9BA4` / file `0x023BB4`，每城三组 XY，组序号为 0/1/2。原表有 67 个非 `FF FF` 点，全部合法；55 点恰好位于 raw6/7/8，另 12 点位于普通 class2。反向有两个标记没有精确匹配坐标：city12 的 raw8 在 `(19,19)`、服务表在 `(19,18)`；city21 的 raw6 在 `(5,11)`、服务表在 `(5,10)`。保留原字节，不猜测修正原因。因此 **不能将 raw6/7/8 逐一对应米屋/武器屋/病院**。

bank12 `$A4D6..A51C` 在移动终点检查三组 XY，模式 `$050F=3` 禁用。命中先写 `$0470=坐标组序号`、`$0012=1`，调用 `$D6CC` renderer，然后有明确原 opcode：

```text
CPU A512 / file 018522: A9 09       LDA #$09
CPU A514 / file 018524: 8D 00 05    STA $0500
CPU A517 / file 018527: 8D 01 05    STA $0501
CPU A51A / file 01852A: A9 A7       LDA #$A7
```

进入的是 **battle state9/sub9**，不是只写子状态。未命中递增 `$0501`。这一入口不写已访问/一次性消耗标记；稀有装备另有全局分配标志。高层 `service_at()` 要求合法移动格，防止把缺席的 `FF FF` 哨兵当设施；`enter_map_service()` 显式要求 renderer hook，对缺失依赖报错。

真实原文字及路由如下。截图由未修改 ROM 的完整核心绘制，RAM 初始化是有日志的受控 fixture，**不是自然 campaign 流程证据**。

| `$0470` | 原文字 | 效果语义 | 确认后子状态 |
|---:|---|---|---:|
| 0 | コメヤ（米屋） | 买卖粮食 | 0 |
| 1 | ブキヤ（武器屋） | 购买武器/防具 | 5 |
| 2 | ビョウイン（病院） | 50 金治疗 | 3 |

![原 ROM 服务提示](core-labels/message-atlas.png)

`$A7` 为「ムラにはいりますか」，`$A8` 为「ここはコメヤです なにをしますか」，`$AD` 为「ここはブキヤです なにをかいますか」，`$B1` 为「ここはビョウインです」，`$B2` 说明治疗需金50。`$DC/$DD` 分别为退却目的国和武将选择，`$DF` 说明一个国超过10名武将需移往其他国。图中 D7/DE/E5 使用的动态参数只用于 renderer fixture，不独立作为正式处置名称证据；在野「ざいや」另由[战后处置报告](../postbattle/README.md)确认。

最终截图取第240帧；12个消息/菜单的 `$0300` 和 `$0304` 都为 `FF`，详见[绘制完成记录](core-labels/message-completion-checks.json)。DF 的第二队列在原代码第202帧自行完成。每项 `*-fixture.json` 保留父 state、SHA-256、全部 RAM 变更；对应 PNG、state、RAM、SRAM 同目录保存。

## 跨银行服务控制器的十个子状态

已有 bank13 `$C1FC` 是 EE07 bridge，转 bank8 `$A009`，再到 bank9 `$C0BB`。真正服务入口读取 `$0501`，`$C0BE` 调用 EADE，inline table `$C0C1..C0D4` 正好十个 word，下一字节是首 handler `$C0D5`。这十个跨银行子状态单独计数，不把旧 pair12/13 的 state9 桥接入口当成完整服务状态体。

| sub | 入口 CPU（physical bank9） | 可证实行为 |
|---:|---|---|
| 0 | `$C0D5` | 米屋买/卖选择与报价 |
| 1 | `$C1EB` | 买粮数量输入及交易 |
| 2 | `$C2C0` | 卖粮数量输入及交易 |
| 3 | `$C392` | 病院原始体力检查 |
| 4 | `$C3E9` | 治疗确认、50金扣款、恢复体力 |
| 5 | `$C4B8` | 武器屋装备组选择 |
| 6 | `$C543` | 四项装备与价格绘制 |
| 7 | `$C62E` | 购买确认、稀有条件、装备写回 |
| 8 | `$C7B0` | 消息确认后回 battle0/0 |
| 9 | `$C7C8` | 进入村落确认及组序号路由 |

[完整目录](service-controller.json)记录每入口 bank/file、字段写入、状态写入、可达指令和 hooks；[汇编](service-controller.asm)将 inline word 与指令分开；[机器 IR](service-program.json)有799条指令。`MapServiceMachine.step()` 执行 `$C0BB`，`.phase(substate)` 设置 state9 与相应子状态。它复用6502控制/算术/flags/栈模型，局部 JSR 仍按真正调用执行，外部服务必须由明确 hooks 提供。薄 wrapper **不自行实现**父 EE07 的银行切换与返回协议。

## 服务效果的可读复原

- 买粮 `$C21B`：`cost=floor(amount*100/quote)` 取低16位，金不够时饱和减至0；粮先16位相加回绕再封顶9999。卖粮 `$C2F2`：粮饱和减，`gained=floor(amount*quote/100)` 取低16位，金先回绕再封顶9999。**买卖 quote 来自城市表不同位置、方向不同**，不统一标成“每100粮的金价”。零数量不做交易写入，UI数量上限的舍入另有路径。
- 治疗 `$C42C..C4A0`：确认且有50金时扣50；RNG低4位拒绝11..15，得到35..45恢复量。先8位加法，再按该武将初始体力比较、封顶并调整报告的恢复量；异常 HP 的回绕保持原代码行为。
- 装备 `$C6D5..C706`：item0..23写 byte10低5位武器，24..31写高3位防具，同时保留另一字段。
- 稀有条件 `$C73B`：item15只给ID38、item23只给ID153、item22要求武≥90、item30要求徳≥90；分别检查/设置 `$6FE1` 的 `02/04/08/10` 位。条件不满足消息48，已经分配消息49。姓名原图支持ID38=関羽、153=張飛，但判定代码本身使用数字ID。

这些条件不是所有游戏状态下的完整购买模型；完整付款、菜单与装备库存选择位于上面的十个子状态。`resource_trade()`、`map_service_heal()`、`equipment_permission()`、`pack_purchased_equipment()` 则复原各已明确的算术/位字段效果，并由相应原入口独立对照。

## 九个单挑动作的字形联接

bank23 `$B43C` 用 `$0012` 索引 `$B461` 的 `00..06` 表并写 `$04BF`；`$B46B` 七组光标坐标对应原画面逐项文字。战术子菜单 `$B59E..B5A6` 将 `$0012+7` 写 `$04BF`，因此两项是动作7/8。

| `$04BF` | 原菜单字形 | 对应含义 |
|---:|---|---|
| 0 | けんせい | 牵制 |
| 1 | たいきゃく | 退却 |
| 2 | こうげき | 攻击 |
| 3 | こうさん | 投降 |
| 4 | せんじゅつ | 战术子菜单 |
| 5 | データ | 数据 |
| 6 | すてみのこうげき | 舍身攻击 |
| 7 | せっとく | 说服 |
| 8 | ばとう | 辱骂 |

![全部九项原单挑字形](duel-menu-atlas.png)

主菜单使用[原核心注入 fixture](../../duel_fsm/runtime/injected-core/fixture-state-16.png)，子菜单使用[原代码绘制结果](core-labels/duel-tactics-submenu.png)。读取 `.state` 的真实 PPU nametable 和 mapper CHR 1KiB banks（主菜单 BG为8/9/6/12），逐字符提取原16字节、CHR file offset、PPU tile code和上方浊点。每个字符的原 CHR 像素与 screenshot 实际像素逐点相等，screen位移 `(0,-2)`；对应列表在 `evidence.json` 的 `duel_main_menu` / `duel_tactics_submenu`。这确认**菜单索引和正式字形**；伤害/退却/说服等算法由[独立单挑规则报告](../duel/README.md)对照。

16个战场计略的姓名/selector联接已在[前轮名称证据](../../names_terrain/README.md)完整保留，本轮不重复提取或凭系列经验新增名称。

## 对照范围与复现

**27,638例全部通过**，其中17,670例逐一覆盖全部合法地图格，120例覆盖十个服务子入口的按钮、双方、绘制忙/闲组合。服务IR动态执行655/799条；尚未动态覆盖的144条不声称已经每条执行验证。

| 类别 | 例数 |
|---|---:|
| 城市 chunk 设置 | 30 |
| 全部合法格原查表 | 17,670 |
| 玩家/AI折算 | 892 |
| 服务坐标扫描与禁用模式 | 1,270 |
| 服务确认路由（含完整 byte 组序号域） | 512 |
| 交易边界/随机 | 1,200 |
| 治疗回绕/初始上限 | 1,024 |
| 稀有装备条件 | 2,048 |
| 装备位字段 | 1,792 |
| 兵缓存→查地形→移动成本 | 1,080 |
| 十子状态完整入口 IR | 120 |

CPU oracle 使用原 ROM、合成 RAM；绘制/输入/数学/far-call等外部 hook **执行原 ROM 原 helper**，不是伪造成功。完整控制入口比较寄存器、flags、栈、全部RAM/SRAM及银行状态；高层效果函数比较其声明的字段作用域。未恢复的图形/硬件依赖仍显式暴露，不把这个对照当成独立整机模拟器或所有自然流程的验收。

```sh
python3 scripts/analyze_terrain_rules.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
# 额外重现原core受控绘制fixture（Pillow + 本项目Nestopia core）
python3 scripts/analyze_terrain_rules.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --render-core-labels
.venv-trace/bin/python scripts/verify_terrain_rules.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

未决项仍保留：class1 的正式名称、武将 byte9上6位的完整业务含义、status3在不同处置路径的永久语义。后两项由[战后状态报告](../postbattle/README.md)与已有字段记录继续按实际写入路径区分，不能以图像或人物数值填补结论。
