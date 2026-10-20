# 战术 AI 主控制器

`source/recovered/tactical_ai_control.py` 独立执行全局主状态 4 调用的战术 AI 合作更新。全部可达控制体已恢复为 2,213 条 bank8 IR，内联 `$B517` 另有逐步 CPU 协议源码；唯一外部 CPU helper `$F266` 由既有 `RuntimeServices` 独立执行。源码不调用原 ROM 执行器，没有图形/IRQ 完成确认的代用实现。

这是完整的有界决策控制图；行动提案之后的坐标、AP、攻击、计略及显示效果由战场控制器消费。这里不执行 NMI，也不模拟 NES 帧。

## 入口、接口和 mapper 合同

原链：fixed31 `$E221` → RNG `$E87A` → `$F24B(Y=$28)` → physical8/9 `$A000`，bank8 文件 `$10010` 的 `4C 2D A0` tail JMP 到 `$A02D` / file `$1003D`。主调用 JSR 在 `$E229`，真实返回 PC `$E22C`。虽然调用方映射 pair8/9，本图实际只执行 bank8，没有可达 bank9 代码。

```python
controller = TacticalAIControl(memory)
result = controller.run_entry(
    0xA02D, registers=caller_registers,
    seed_return=False, return_pc=0xE22C,
)
```

必须共享真实寄存器对象/SP，调用栈已经由上层 JSR 写入。本接口借用既有 BSM 的独立 CPU/IR 执行逻辑；直接 `step()` 或默认 `run_entry()` 可使用历史 `$0200` sentinel 测试合同，默认会写 `$01FE/$01FF`，不能用于真实嵌套桥接。`phase()` 明确拒绝战场 `$0500/$0501` setter。

结果带 `status='returned'/'dependency'/'budget'`、`before/after`、`registers`、`events` 和指令数。依赖保留真实此前写入与栈状态；超出证明的内联表域抛出 `InvalidState`。没有自动应用提案或自动清理请求。

`memory` 需要原 CPU 地址空间的 RAM/SRAM、当前 PRG 页及 mapper 写入合同：代码 `$A000/$C000` 是 physical8/9，fixed31 位于 `$E000`。数据页 `$8000` 必须与实际上下文一致；例如自然请求为 physical6，代码中的 `$F266` 会按需要改为 physical0、6、16 或17等页。`$A8/$A9` 的地图页描述指针及所指 4 字节页号也是输入，不能只提供城市 ID。

## 控制字段和合作协议

| 地址 | 用途 |
|---|---|
| `$6F8B` | 请求：FF 直接返回；1 进入 `$B933` 二阶段；其他原始 byte 进入扫描 |
| `$6F8C` | 当前 actor slot |
| `$6F8D` | proposal 参数：方向、普通攻击目标、计略 ID 或撤退目的地，取决于 status |
| `$6F8E` | proposal target slot；计略分支使用 |
| `$6F8F` | proposal status：0 移动、1 普通攻击、2 计略、3 本次不提交行动、4 撤退 |
| `$6F92/$6F93` | 战术 RNG 游标及保存 X 的 scratch |
| `$6F94` | 下一扫描 slot，范围 0..20 的终点比较 |
| `$6F95` | `status3_count`：本扫描中 status3 的数量 |
| `$6F96` | `eligible_attempts`：本扫描中经过合法 actor 筛选的决策次数 |
| `$6F97` | 提案移动费用；后续战场阶段扣 AP |
| `$6FA1[20]` | 每 slot 策略/高位标记；FF 无策略，低4位选择表 |
| `$6FB5[20]` | 路径/候选临时工作数组 |
| `$6FC9[20]` | 候选 slot 工作数组与排序结果 |
| `$6FDD[4]` | 四邻工作数组 |

其余输入包括 `$0504` side 符号、`$0505` 行动力、`$0507` 双方势力 nibble、`$050E` 城市、`$0526..$052A` 侧资源/撤退字段、`$04D8[8]` 预备/隐藏单位组，以及 `$0600/$0614/$0628/$063C/$0650/$0664` 的 20 个单位数组。武将记录仍在 `$63C0+12*ID`，城市记录 `$6000+32*ID`，策略也读取原 data bank 内的城市连通、特殊坐标与初始武将上限。数值字段不会按游戏常识擅自屏蔽原高位。

`$A02D` 的实际扫描：

1. `$6F8B==FF` 返回；`==1` 直接跳 `$B933`。
2. 读取 `$6F94`；未到20则先递增，再读该 slot 的 `$6FA1`。FF 跳过；`$A944` 对比 `$0504` 与 `$0628[slot]` 的符号，不属当前 side 跳过；`$0664[slot]==FF` 跳过。
3. 合格 slot 递增 `$6F96`，保存 `$6F8C`，执行 `$A099` 的策略链。
4. 若结果 `$6F8F==3`，递增 `$6F95` 并继续扫描。其他 status 立即写请求 FF 并返回，交给战场控制器消费。
5. 到20时，若 `$6F96!=$6F95`，清三个扫描计数再扫描；两者相等时写 status3、清扫描游标并写请求 FF 返回。

重扫是原行为；源码预算仍可能停止不收敛的自造输入，不会更改算法把它强制变成成功。

## 两张内联表和完整入口目录

`$A09E JSR $B517` 后 `$A0A1..$A0B0` 恰有8个指针，结束处正是首 handler `$A0B1`。`$6FA1[slot]&$0F` 的8..15不在这张已证明表内；源码拒绝。合法表为：

| strategy | bank8 CPU | file |
|---:|---|---|
| 0 | `$A0B1` | `$100C1` |
| 1 | `$A105` | `$10115` |
| 2 | `$A166` | `$10176` |
| 3 | `$A210` | `$10220` |
| 4 | `$A2AD` | `$102BD` |
| 5 | `$A329` | `$10339` |
| 6 | `$A507` | `$10517` |
| 7 | `$A606` | `$10616` |

`$ACAB JSR $B517` 后 `$ACAE..$ACCD` 恰有16个计略 predicate 指针，结束处为 `$ACCE`。部分 ID 共用 handler（1/2/3、10/12），仍分别测试全部合法索引。原名绑定在前阶段 `analysis/names_terrain/tactics16.png`；策略0..7没有直接原菜单名称证据，保留编号。

`state-catalog.json` 列出4个控制入口、8个策略和16个 predicate，共28项，包括每项完整可达指令、条件跳转、控制字段写入及 helper 调用。`all-entries.md` 是相同范围的可读逐项索引；`control.asm` 保留每条 bank/CPU/file/raw bytes 和 pointer words。所有 pointer words 均排除在代码之外。递归审计没有发现可达 `$EADE` 或 `$EE07`；不是把其数据伪装成代码。

`TacticalDispatch` 对照 `$B517..$B535`：保存 Y 到 `$20`、ASL A 并设 carry、索引加1、弹出该 JSR 的实际返回 word 到 `$21/$22`、读目标 word 到 `$23/$24`、恢复 Y 并间接跳转。原 scratch、flags、stack 写入都保留；它没有假 RTS。

## 提案消费与二阶段调用关系

bank12 `$BEBA` 等请求 FF。`$BF01` 按 status0..4 的真实 bytes `[3,5,8,12,13]` 设置战场子阶段：

| status | proposal 消费路径 |
|---:|---|
| 0 | `$BF19` 应用方向到坐标；`$BF7C` 按 `$6F97` 扣 AP，转移动状态4/2 |
| 1 | `$BF98..$C000` 保存目标/actor并 `$A3D2` 准备普通攻击场景 |
| 2 | `$C004` 处理计略请求，`$C07D` 将 ID/actor/target 写 `$0543/$050A/$0509` 并调用 `$B02B`；ID11另走 `$C1AF` |
| 3 | `$C13B` 转回合结束；等待原文本任务完成 |
| 4 | `$C149..$C1AE` 显示撤退并调用 `$BC2A`；目的地来自 `$6F8D` |

这些消费路径属于已恢复的 `BattleStateMachine`，不是本 AI 执行器直接执行的效果。source `TacticalAIControl` 只完成实际主线程更新。

`$B933` 二阶段的真正请求来自 bank12 移动 state4/sub3 `$A51F`：等待 FF，`$A526..$A528` 写请求1，`$A52B..$A52E` 把 `$0509` 写入 actor，推进子阶段。下一次 global4 进入 `$B933`；移动 sub4 `$A535` 等请求 FF，只有 status0 才继续效果提示。此处对隐藏/预备单位的损失运算已经保留。高层独立决策说明与 oracle 在 `analysis/phase7/decisions/`；补充的[跨段生产—消费链](../secondary-origin.json)确认该缓存至少由计略11「十面埋伏」建立，未证明所有缓存来源或自然phase1施放。

## 验证和自然输入

最终 7,361 项通过：7,113 项原 ROM CPU 对照、248 项非法域源码 guard，0失败。所有2,213条 IR 原字节来源核验通过；动态执行1,315/2,213条。全部合法分派入口通过，不代表全部动态分支已执行；898条尚未由本控制器矩阵动态覆盖。高层决策验证是单独范围，不能把它的覆盖直接算作本执行器全部动态覆盖。

| 组别 | 数量 |
|---|---:|
| 请求的全部256原始 byte | 256 |
| B517全部24合法索引 × 全部256 SP，flags/Y随SP覆盖 | 6,144 |
| 非法策略低nibble8..15及非法predicate16..255源码拒绝 | 248 |
| 8策略 × 双side × 8个 AP 边界 × 4种坐标/状态输入 | 512 |
| 全部28公布入口体 × 4变体 | 112 |
| 连续扫描/多次请求，不代用行动完成 | 48 |
| B933二阶段 side/预备槽/坐标输入 | 32 |
| A000真实 E22C caller-owned 栈，8个 SP 边界 | 8 |
| 自然原核心请求的同步原 ROM/恢复源码调用 | 1 |

每个 CPU 对照比较全部2KiB RAM、全部8KiB SRAM、A/X/Y/P/SP/PC及物理 PRG banks。没有执行原代码的 source hook，也没有硬件/等待 ack。guard 是源码输入拒绝，不执行原表越界读取。

受控组以 `attack-intro-7` 原核心 RAM/SRAM 为底稿，明确注入请求/scan/strategy、side/AP/conditions、slot坐标、合法ID、scratch和真实返回栈；它们是 CPU fixture，不是自然游戏截图。所有注入具体值在验证器中，原 ROM 和 opcode 不变。

自然组使用 `analysis/phase7/runtime/natural-turn/ai-request-*` 的 frame431 RAM/SRAM，不修改游戏字段。使用捕获寄存器和明确压入的 E22B 真返回 word，同步入口 `$A000`，返回 `$E22C`。原 ROM执行8,243指令；恢复源码全部RAM/SRAM/寄存器/banks一致。8个请求、actor、提案、scan、status3_count、eligible_attempts字段还与frame432原核心记录一致。此同步调用不是 Nestopia 的逐指令录像，也没有执行完整NMI/下一帧；下一帧图形/坐标/AP等证据由原核心700帧回放单独提供。

`validation.json` 固定三个 scalar：`source_sha256`、`validator_sha256`、`program_sha256`，并固定catalog、四个共享源码依赖以及受控底稿/自然输入/外部CPU回执文件hash。自然字段比较明列于 `natural_core_field_comparisons`。

## 重跑

```sh
.venv-trace/bin/python scripts/analyze_tactical_ai_control.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_ai_control.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

第一条仅重建本目录IR/目录/汇编，第二条生成匹配当前源码和fixture的回执。原 ROM SHA256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。
