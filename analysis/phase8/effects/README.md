# 计略施放编排、十面生命周期与退却记账

`source/recovered/tactical_effects.py` 是独立可读的高层游戏数据实现。它没有 IR 执行器或原 ROM fallback；复用的 `battle.py` 概率/兵损/经验、`game_algorithms.py` RNG 和 `TacticalDecisions.secondary_effect` 都是已有独立纯算法。ROM 仅读取经过 SHA256 固定的费用、消息、RNG 和地图资源。

本轮完整处理8个效果体：0火計、2虚兵、3要撃、4乱水、6偽撃転殺、11十面埋伏、13連弩、15奇門遁甲。原名与 ID 沿用已证明的菜单/分派绑定。其他1/5/7/8/9/10/12/14在清除结果区后返回其真正 effect 入口的显式依赖，不能把本模块说成16个效果/动画全部完成。

## 构造与声明范围

```python
effects = TacticalEffects(memory, EffectData.from_rom(rom_bytes))
```

`memory` 是共享 CPU 地址空间，支持按整数地址读写。纯算法比较范围是全部 SRAM `$6000..$7FFF` 和源码 `DECLARED_RAM_RANGES`。工作指针 `$0000..$0011`、CPU寄存器/flags/stack、mapper和硬件时序不在此高层合同内；`trigger()` 额外准确保留 `$0020..$002F`。普通 effect 的 `$0012` 已保留实际 B7E4/B812 scratch，未为了通过测试删除该声明字段。

这层 API 返回 `returned`、`waiting` 或具有具体 PC/service 的 `dependency`。方法名 `after_*` 明确表示真实显示/音频/文本确认前序已由调用方完成，不能拿它代替实际前序。队列请求准确写 RAM，但不会修改任务完成标志。源默认没有空的 renderer/IRQ/ack hook。

## status2 普通计略消费

真实 NMI 战场控制器 bank12/13 的 state8 使用 `$BF14` 表：status2→sub8 `$C004`。普通路径的游戏数据窗口按原程序拆分：

| API | 原入口/终点 | 实际作用或边界 |
|---|---|---|
| `prepare()` | `$C004..$C016` | 设置 `$0509=$6F8E`；到 bank29 `$A027` 目标资料绘制依赖 |
| `prepare_after_portrait()` | `$C01B..$C03D` | 扣 AI 费用、结果区写计略 ID、实际请求 A1 消息；到 E69B 音频请求65 |
| `advance_after_audio()` | `$C040..$C043` | 原音频请求已返回后推进 `$0501` |
| `cast_after_portrait()` | `$C083..$C0A7` | 原 DC36 绘制已返回；保存 ID/actor/target，清目标 condition，施放、刷新移动缓存；到 D6CC 图形请求 |
| `finish_after_graphics()` | `$C0AA..$C0FD` | 原 D6CC 已返回，选择成功/失败/特殊结果消息并排入队列；不完成消息 |

确认阶段 `$C054` 的 DC36/A1DE/DF27/DC63 和 `$81&3` 输入仍由真实 UI 层负责。没有通过清 `$0300/$0304/$007E` 来跳过这些等待。

`$EE07` 的 JSR 后有2字节 inline target，下一指令是 `$C01B`，不是 `$C01C`；同理 secondary 的 portrait 后恢复于 `$A5C0`，不是 `$A5C1`。汇编证据把这些 word 标成数据，并验证每个范围终点都是指令边界。

`dispatch()` 对照 `$B02B`：清 `$042C..$0434` 和 `$0544`，按 `$0543&15` 选 effect。已恢复普通效果真实调用共享成功 gate，并保留 RNG cursor：

- ID0/6、3、4、13的单目标兵损使用原六段中对应公式，随后饱和扣 masked10 兵数、更新累计显示值、奖励 actor 经验并检查等级/武力。此旧兵损 helper 的 byte9 会清掉 upper6；同 actor/target ID 的记录别名按同一地址处理。
- ID2成功把目标 `$0650` 写2或3（side符号决定）；失败不写该结果，`$0544=FF`。此处描述原始 condition 值，不猜测额外玩法。
- ID15成功取一次固定 RNG 的 `&3`，构造原始 high-nibble condition 码；没有改成 rejection sampling。失败沿原 gate 处理。

`supported_effect_outcomes` 明列每个效果实际对照中的成功/失败数量；成功的第一例原 CPU 对照在 `rows`。API恢复原 game-data effect，不输出完整攻击动画。

## 玩家施放前序与费用差异

`queue_player_animation_after_confirmation()` 对照 `$AA3F..$AA6B`，在真实文本/输入确认之后写 CHR 请求字段、清目标 condition、写 `$04C8=tactic+1`、请求原任务5并推进子状态。它没有清除 `$04C8`。

`player_cast_after_animation()` 对照 `$AA6C..$AAA6`：`$04C8!=0` 就返回 waiting；为0才保存 actor 的等级/武力前值，扣玩家费用，调用 effect，刷新 `$063C[20]` 并清 `$050B`。直接 CPU fixture 的不足 AP 保留原8位下溢；正常菜单先检查费用足够，不能把直接窗口测试说成自然菜单允许不足 AP。

| ID | 玩家 AP 表 `$ABC9` | AI AP 表 `$C044` / 真实路径 |
|---:|---:|---:|
| 0 | 6 | 6 |
| 2 | 4 | 4 |
| 3 | 6 | 6 |
| 4 | 7 | 7 |
| 6 | 8 | 8 |
| 11 | 10 | 专用分支不扣；表中15不会由此分支读取 |
| 13 | 8 | 15 |
| 15 | 10 | 20 |

其他 ID 的两张完整费用表仍在 `evidence.json`，不能把 AI/player 表混成同一张。

## 十面埋伏部署

`deploy()` 完整对照 bank12 `$B42A..$B465`：按 `$0504` 符号选择 own cache row，保存 `[actor_slot,x,y,ttl=5]`，然后 officer raw little-endian16兵字段减100、推进 `$0501`。没有概率门，也不在这里扣 AP。

| side | 缓存 |
|---|---|
| 正/0 | `$04D8=slot,$04D9=x,$04DA=y,$04DB=ttl` |
| 负/80 | `$04DC=slot,$04DD=x,$04DE=y,$04DF=ttl` |

玩家 `ambush_eligible(terrain_class)` 对照 `$AF73..$AFA0`：原 class0、raw16兵字≥100、own cache slot=FF。检查和部署都读取完整 byte9，未先 `&3`；低10兵不足100但 upper6非零的合成输入仍可通过这个原始判断。直接部署窗口没有再次检查并饱和，raw16<100会模65536下溢。部署减100可向 byte9 upper6借位；与后续触发保留 upper6 的兵损不同。

AI专用路径 `$C004` 比较 `$6F8D==11`，直接跳 `$C1AF`，把 actor 与 target 都设 `$6F8C` 并执行部署；绕过普通计略 AP 扣款。其后真实图形/光标请求两次：

1. `prepare()` 做部署和移动缓存刷新，停在 `$C1C8` 第一次 D6CC。
2. `finish_ambush_after_first_graphics()` 对照其后的 `$A1F7` 请求05消息，停在 `$A200` 第二次 D6CC。
3. `finish_ambush_after_second_graphics()` 对照 `$A203` 清 cursor 字段、真实 RTS→`$C1CE` JMP→`$C1F0` 清 battle main/sub/A4。8个连续原 CPU 栈链病例证明这条组合，不靠假 renderer 成功。

## 有效期、触发、经验和清除

`tick_expiry()` 只对应 bank9 `$CE20..$CE3F` 的计时尾段，尾端 RTS 到实际 caller；`$CE40` 是下一函数，不能作自然终点。调用关系是 bank12 `$BDC0` side0→80 时推进 `$0506` 并 farcall bank8 `$A00F→bank9:$CD78` 完整回合处理，其中到达 CE20。side80→0不调用这段，因此正常期限5指5次完整回合处理，不是5帧/5步。

两 cache 的 ttl FF 跳过；只有1→0清 slot，XY不清。零 ttl 会下溢为FF且不清 slot，以后跳过；原异常输入行为保留。模型没有推进真实时间。

`request_secondary_after_move()` 完整对应 `$A51F`：等待 `$6F8B==FF`，请求1、actor=`$0509`、推进子状态。下一次 global4 `$A02D` 因请求1进入 `$B933`。

`trigger()` 复用完整可读 `secondary_effect()`：反方 cache（side0读group4，side80读group0）、距离2候选、actor class0限制、原 B965错误使用 `$0614[group]`、先接受0..100后丢弃的 RNG 消耗，以及实际损失计算全部保留。实际扣兵 masked10并保留 byte9 upper6，写 `$042C/D` 损失和 status0/requestFF。没有立刻清 cache。

`consume_secondary()` 对照 `$A535..$A5BB`：pending request等待；status非0走真实取消窗口；status0用 cached officer奖励经验、保存原等级/武力、刷新20个移动 selector，设置后续 actor/target和 B8/B9消息，停在真实 portrait 绘制调用。`finish_secondary_after_portrait()` 从 `$A5C0` 原指令交换 actor/target。

真正清 cache 在文本/输入确认后的 `$A5F5`，`clear_triggered_cache_after_confirmation()` 只清反方 slot，保留 ttl/XY，然后到 cursor graphics 或 DEE9等级提示边界。不能用这方法代替 DC36、DF27与确认输入。

`clear_cached_slot()` 还恢复 B343/C82C/BC5E 的“清两组匹配slot”合同。`remove_unit()` 对照 bank9 D6CD：清6个单位数组和策略，随后只清第一组匹配的整个4B cache row；两个 row错误重复同 slot时，第二组仍保留，和普通引用清除不同。

## 退却前记账

`detach_unit_accounting(slot=None)` 完整恢复 bank13 `$C91E..$C98B`：从 `$0628[slot]&80` 选侧，不用当前 `$0504`；计数 `$051E/F` 模256递减（0→255）；侧总兵字 `$051A/B` 或 `$051C/D` 减 officer masked10兵并饱和0。它不改武将原字、AP、城市名册或缓存。

随后旧 `city_ownership.retreat_unit_to_city` 的 `$BC2D..$BC92` 才提交目的城名册/单位移除。根 GameEngine组合这两段；原 UI/撤退确认前序仍需要真实完成。本新函数不替它虚构确认，也不通过整轮 AI重新执行已提交的撤退。

## 验证回执与边界

`validation.json` **3,564项通过、0失败**：3,562项真正原 ROM CPU对照、2项非法slot源码guard。对照全部8KiB SRAM与声明RAM；没有声称寄存器、栈、mapper或整个CPU帧相等。另有17段精确原字节范围/inline调用证据。

主要矩阵包括512个raw16部署、192个玩家资格边界、1,024个8效果成功/失败/alias/RNG/经验病例、512个ttl全部byte边界、160个cache/unit移除、40个玩家施放和255个未完成动画等待、AI准备/扣费/施放/结果消息各窗口、64个完整B933触发、32个经验后缀、真实清除和等待后缀、8个连续第二图形返回栈链，以及512个退却侧别/low10/upper6/计数下溢/总数饱和病例。

未恢复的8个效果体分别在真正handler入口截断。所有after-service病例的起点和终点明列在验证器；原图形/音频/IRQ执行没有被空返回。原核心渲染、实际输入和部署→触发的完整帧证据由 `analysis/phase8/runtime/` 的独立核心回放提供，不能从本CPU fixture推断像素已渲染。

受控CPU底稿为只读原核心 `attack-intro-7` RAM/SRAM。注入内容在验证器逐项明示：合法actor/target/records、费用/预算、RNG、条件、cache输入及给定入口的前序完成条件。其中 `$04C8=0` 是直接 AA6C完成分支的声明输入，不是自然动画完成证明；255个非零输入确认源码不会清它。ROM/opcode未修改。

源码/验证器/证据的scalar hashes及3个纯算法依赖、fixture RAM/SRAM hashes都固定在回执；`source_uses_IR_or_original_CPU=false`、`graphics_audio_acknowledged=false` 明列。没有IR program文件，使用 `evidence_sha256`，不把原始证据误标成可执行IR。

```sh
.venv-trace/bin/python scripts/analyze_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_effects.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

原ROM SHA256仍为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。
