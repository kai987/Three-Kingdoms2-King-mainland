# 共殺、籠絡与连通范围计略

`source/recovered/tactic_area_conversion.py` 完整独立恢复5个 effect handler：7共殺、8籠絡、10連環、12水攻、14劫火。源码使用可读数组/循环和已恢复的兵损、经验、概率、忠诚纯算法，没有 IR 或原 ROM CPU fallback，没有图形或任务完成代用实现。

```python
area = AreaConversionTactics(memory, AreaConversionData.from_rom(rom_bytes))
result = area.apply(tactic_id)
```

入口合同是原 `$B02B` 已清 `$042C..$0434/$0544` 并选择对应 effect 后的处理体。`apply()` 不再清结果区、不扣 AP、不模拟菜单/动画/NMI。这样原重复累计损失的直接窗口和统一施放编排可以共享同一算法。结果记录成功 gate、候选顺序、每次实际损失、累计值及等级标记。

## 真实入口和作用域

| ID / 原名 | bank12 CPU / file | 完整作用 |
|---|---|---|
| 7 共殺 | `$B2CD / $192DD` | 一次共同 gate；中心火計兵损，左右上下四邻再分别兵损；最终 sub7 |
| 8 籠絡 | `$B31C / $1932C` | 转换 gate、战场计数/兵总迁移、unit转侧、cache/策略调整、忠诚 helper、sub++ |
| 10 連環 | `$B3D0 / $193E0` | 一次共同 gate、B8A1连通候选；真实class3目标逐次 RNG condition；最终 sub7 |
| 12 水攻 | `$B466 / $19476` | 一次共同 gate、连通候选；真实class3目标逐次乱水兵损/经验；最终 sub7 |
| 14 劫火 | `$B50C / $1951C` | 一次共同 gate、连通候选；非class5目标逐次劫火兵损/经验；sub++ |

失败路径全部是原 gate 失败后 `$0501++,$0544=FF`，不损兵、不展开候选、不消费后续伤害随机数。首 gate 正常按 actor/target原记录、range、`$050F/$6F02`、固定 RNG cursor `$50` 计算；范围目标后续不再逐个重复 gate，但各自伤害或 condition 会继续消费真实 RNG。

数据中的地形通过已装载的 `$A8/$A9` 四个 chunk IDs、原 pointer/bank/tile/class表求得，与真正 `$DB46` classifier字节一致；不接受测试预先传入的地形结果。≥6折成2，原tile≥128分支为0。四个chunk的有效域0..119，不能仅给城市ID就代替实际场景地图上下文。

## 共殺：与连通候选不同的查找

共殺先对中心执行 `$B070`，中心不在此 effect 体再次进行 side或terrain检查（正常UI已有目标资格检查）。之后每次重新从中心原坐标生成左、右、上、下：

- `$B643` 在 raw y等15时按中心y14/16越过空行，边界为 x<32、y<20。
- `$D6B6` 从slot19倒查到0，选择同坐标最高槽位；找到后才通过 `$DC4B` 判断敌方。最高槽位是友方时，不回头寻找较低槽的敌方。
- 命中的敌方再执行 `$B070`；每次保存/恢复原 `$0509`。原查找没有按officer ID去重，所以不同slots指向同一record会反复命中同一记录。
- 每个 `$B070` 先按当前 actor记录重新计算伤害，累计真实兵损，奖励经验并可改变 actor的等级/武力；最后统一把 `$0501` 设7。

因此相邻坐标、slot排序、共享record以及循环中的等级变化都是算法输入，不能用一次固定群伤公式或一组去重的officer IDs替代。

## B8A1连通候选：連環、水攻、劫火

`connected_candidates()` 完整实现 `$B8A1..$B949`：清20个候选为FF，无条件把中心slot放第一项；按右/左/下/上扩展，并沿新增slot继续广度优先处理。

邻居按 normalized y（raw≥16先减1）查找，从slot0升到19，找同坐标的第一个敌方slot；友方槽位会继续扫描。第一个敌方slot的真正地形为class5时直接阻断，不再找第二个重叠敌方。候选按slot去重，不按officer record去重。最大20项容量已用原地图上的非class5连通区域独立原CPU验证。

中心无条件入队，后续各effect仍分别检查其真正terrain：10/12只处理class3，14跳过class5。正常菜单限制目标资格；直接helper合同仍保留中心可友方/城砦的原行为，不能把容量fixture当作自然菜单选择证据。

連環每个class3候选执行一次 `$E862(A=2)` 的低nibble rejection sampling，写 `$0650=sample+3+(side负?1:0)`。水攻每个class3候选执行 `$B1E3`；劫火每个非class5候选执行 `$B55C`。循环始终恢复原target，候选顺序和RNG消费顺序不排序。

## 逐次兵损与经验

每个命中复用独立 `battle.strategy_damage_amount` 与 `battle.troop_loss`：masked10兵数饱和扣除、byte9按原损兵helper清掉upper6、16位累计值先wrap。经验奖励是**每次按新累计总损失再奖励一遍**，包括这次实际损失为0的命中；不能只在循环末奖励“总兵损的一半”。

actor/target record同址时，同一份记录同时扣兵和加经验。不同slot共享一个record时，后一个命中读前一个已经改过的兵数。每次重新读actor，所以前一个命中的升级可能改变下一次伤害。96个重复累计/等级阈值/record alias完整effect病例单独计数。

## 籠絡的即时转侧，及地址纠正

原 `$B3AD` 五字节是 `20 07 EE 06 A0`，logical `$2A` 调用 physical10 `$A006→bank11:$CF3F`，是**忠诚调整**。它不是 `$A01E`，也没有调用城市名册转移。证据和 `AreaConversionData.from_rom()` 的字节断言固定这点。

转换成功路径：

1. `$C886..$C91D` 用目标当前 `$0628&80` 选择donor，递减其 `$051E/F`、递增另一侧（均mod256）；donor raw16总兵 `$051A/B` 或 `$051C/D` 减目标masked10兵，不足归0；receiver raw16加同值并wrap。当前 `$0504` 不决定这段记账侧。
2. 翻目标 `$0628 ^=80`，结果 `$042C=officer ID`；两个cache引用匹配目标slot时只清slot，保留XY/ttl。
3. 目标策略 `$6FA1` 原FF变4，其余完整byte变FF，未保留high nibble。
4. 按翻转后的unit sign和 `$0507` 双方ruler nibbles读新/旧leader，写 `$30/$31/$32`，调用已有独立 `OfficerTransfer.loyalty_for_recruitment`。它的原 wrapped差值/clamp行为保留。
5. `$0501++` 返回。

`convert_accounting(slot)` 可单独执行这段迁移算法。转换不修改城市rosters、owner、officer byte5或byte11状态；本模块对全部8KiB SRAM逐字节比较，保证没有凭玩法常识加这些写入。后续战后归属结算由其他已恢复模块负责，应与即时战场转侧分开。

## 验证回执

最终 **1,406项通过、0失败**：1,392项真实原ROM CPU对照与14项本模块不支持ID的源码拒绝。

| 范围 | CPU病例 |
|---|---:|
| 五种完整effect，成功/失败、side、RNG、terrain、condition、record共享 | 640 |
| 重复累计经验和alias完整effect | 96 |
| 共殺最高友方遮挡、14/16空行、地图左右边界完整effect | 8 |
| 双方交替的三次连续籠絡 | 6 |
| C886完整helper，计数0/255、raw兵upper6、总数不足/相等/溢出 | 512 |
| B8A1完整helper，重叠/友敌/城砦/候选顺序 | 128 |
| B8A1整20-slot容量 | 2 |

共750个完整effect和642个完整helper；prefix CPU病例为0。每个原CPU调用都实际到达真实RTS返回，未用prefix替代完整效果。主640矩阵中7/10/12/14各89成功39失败，8为65成功63失败。

14个guard拒绝的是“此模块未实现的IDs”，其中有合法原游戏计略，只是应由别的模块处理；不能把它们称为原游戏非法ID。测试未执行这些guard对应的原效果体。

比较全部8KiB SRAM和 `DECLARED_RAM_RANGES`：共享 `$0012`、转换输入 `$30..$32`、RNG `$50`、结果区、cache、battle sub/target、双方计数总兵、unit sign/condition。原 CPU寄存器/stack/mapper/其余work pointers不属于此高层合同，独立CPU/控制器协议另有验证。

fixture底稿是只读原核心 `attack-intro-7` RAM/SRAM；slot/坐标/records/side/RNG/结果reset/计数等合成输入逐项明示于验证器。terrain来自原地图，未注入地形返回、任务完成、渲染ack或修改ROM字节。20-slot全敌方容量测试是helper合同测试，不声称自然场景可选20个敌方。

`evidence.json` 和19个 `.asm` 文件记录精确bank/CPU/file/raw bytes，EE07 word作为inline数据排除在指令外。`validation.json` 固定 `source_sha256`、`validator_sha256`、`evidence_sha256`、四个依赖源码hash和fixture RAM/SRAMhash；无IR program文件。

```sh
.venv-trace/bin/python scripts/analyze_tactic_area_conversion.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactic_area_conversion.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

原ROM SHA256仍为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。
