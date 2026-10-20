# 战术AI的原核心回放与独立CPU调用

本目录验证一段原战场菜单之后的AI行动：原Nestopia完整核心接收普通按键，敌方槽位1连续移动四格，随后把行动权交回玩家方。ROM、RAM和SRAM均未注入或修改，也没有强制图形完成、消息确认或AI就绪字段。它验证一个已有原战场存档之后的自然输入片段，不代表从冷启动完成征战或整场自然战斗。

原ROM SHA256为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。[脚本](../../../scripts/capture_tactical_ai.py)固定了700帧输入和13个取样点；[整机回执](natural-turn/validation.json)、[逐帧字段](natural-turn/frame-fields.json)、[原核心存档检查点](natural-turn/checkpoints.json)保留可核查的原数据。

## 原存档与普通输入

父存档是 [attack-intro-7.state](../../runtime/phase3/attack-intro-7.state)，对应[原菜单画面](../../runtime/phase3/attack-intro-7.png)。该存档来自先前的原核心出征流程；本脚本导入它，不重新执行reset到战场的输入。父存档SHA256、核心版本／hash与原始读取值全部写在回执中。

输入顺序为：下12帧、松开35帧、右12帧、松开35帧、A2帧、松开300帧、A2帧、松开302帧，共700帧。[输入计划](natural-turn/input-plan.json)可直接复查。菜单索引3是「たいき」；第三行左侧的「たいきゃく」是退却，未选择它。第二次A由真实手柄轮询确认等待。RAM注入数0、SRAM注入数0，原ROM始终只读。

![等待确认的原核心画面](natural-turn/wait-confirmation.png)

## 实际观测的请求、移动和换方

以下frame均从导入父存档之后计数。保存时是完整核心一帧结束后的字段，不能据此声称录制了帧内每条指令或每次临时写入。

| frame | 原字段／作用 |
|---:|---|
| 94 | 已用下／右普通按键选到菜单索引3 |
| 95..396 | battle主7的等待／确认阶段；真实消息与手柄等待 |
| 429..431 | 本方符号128转0，活动AP变24；进入battle主8；431的6F8B=0，扫描正在进行 |
| 432 | 6F8B=FF，6F8C=1，6F8D=3，6F8E=0，6F8F=0；扫描cursor2、status3计数1、合格尝试数2 |
| 485 | 槽位1坐标(17,17)→(18,17)，battle主8/sub4 |
| 486..489 | 原移动控制主4消费该动作：AP24→21，之后回到battle主0 |
| 491..494 | 又一次phase0请求，随后FF提案；方向0、status0 |
| 507..508 | (18,17)→(18,16)，AP21→18 |
| 519..520 | (18,16)→(19,16)，AP18→15 |
| 540..541 | (19,16)→(20,16)，AP15→10 |
| 551 | 6F8B=FF、6F8F=3，status3计数4、合格尝试数4 |
| 563 | side0504转回128、round0506=2、活动AP26 |
| 665..700 | 原玩家回合消息仍在等待输入；没有继续整场战斗 |

所有700个frame结束样本的global007A都是4、NMI0078都是3。槽位1的武将ID为191；另四个有效槽位为0/ID8、2/ID51、3/ID167和10/ID131。活动余额及两方保留余额分别保存为0505与050C/050D；单位063C字段按既有原指令证据是兵量百位缓存。本回放没有仅凭数字图形重新确认这些字段语义。

![第一次坐标提交的原核心画面](natural-turn/first-coordinate-commit.png)

![第四次坐标提交的原核心画面](natural-turn/fourth-coordinate-commit.png)

本片段的成功提案全部为status0移动。方向3之后X加1、方向0之后Y减1，有明确的提案→原控制消费→坐标/AP提交→下一请求链。移动时6F8E仍为0，不把它解释为实际攻击目标0。050A在不同阶段被用于actor或scratch，日志保留原始字段名及数值，不在所有阶段把它统一称为当前AI单位。

取样只出现6F8B=0和FF，没有phase1、B933 secondary路径或成功status2计略提案。像素能够展示实际地图与移动结果；phase、策略编号、RNG cursor、内部提案和AP算式依据原RAM/SRAM及独立指令执行，不能由截图单独证明。

## 单列的原指令CPU调用

[CPU回执](cpu-call/validation.json)是另一个实验：使用frame431捕获的原RAM/SRAM与mapper银行 `[6,8,9,31]`，由py65和既有mapper19 Bus执行原bank8 `$A000→A02D`。原core保存的CPU寄存器payload一并记录，显式从A000开始，并在捕获SP上压入真实原caller返回地址E22C对应的E22B。它不是从保存的原native PC恢复CPU，也不是Nestopia指令录制。

该有界调用执行 **8,243条原指令、636个不同(bank,PC)**，回到E22C。没有替换CPU helper、手柄确认或AI返回值；没有生成NMI/video/APU/IRQ。没有I/O事件和被保护阻止的SRAM写入，F266的原mapper切换实际执行，8000窗口由6切到0。[每条实际指令](cpu-call/actual-cpu-instructions.json)含原bank、CPU/file offset、字节、汇编与寄存器。

调用中的原A099策略分派顺序为槽位2(raw策略3)、3(raw策略3)、0(raw策略0)、1(raw策略4)，可在 `decision_entry_events` 和实际轨迹中复核。父菜单的槽位1策略最初是2，但frame431取样时已经被原前序代码改为4；不能用旧菜单值代替当前CPU输入。轨迹还经过AAF8特殊计略选择及A95C基础计略选择，最终仍得到status0移动，不把经过选择入口等同于成功施放计略。

返回的6F8B、6F8C、6F8D、6F8E、6F8F、6F94、6F95、6F96共8个字段，与下一整机frame432全部相同。该比较只覆盖声明的提案／扫描字段；没有声称同步调用后的全部RAM、栈、视频和SRAM与下一完整视频帧完全相同。这是 **1个原CPU行为对照case**，8个字段不是8个独立case，指令数也不是case数。

## 重复一致性与范围

| 实验 | 原行为域 | 重复一致的非空文件 |
|---|---|---:|
| 完整Nestopia回放 | 700帧、13个原核心检查点、4次坐标提交 | [52项PNG/RAM/SRAM/state](natural-turn/repeat-validation.json) |
| 同步原CPU调用 | 1个显式A000调用，8个声明字段比对 | [3项指令轨迹／RAM／SRAM](cpu-call/repeat-validation.json) |

完整核心的两次700帧字段日志也逐字节一致。libretro memory-id3 VRAM导出是空文件，13个空导出明确排除在非空hash检查之外；完整原PPU／mapper状态保存在各native `.state` 文件。两个实验分开计数；重复运行不增加CPU案例域，不把55项文件hash检查加到CPUcase数或视频帧数。

试探选择错误菜单的材料保留在 `exploratory-wait/`，正确输入的初步长回放保留在 `exploratory-end-turn/`。它们未加入正式验证计数或用作新的独立覆盖域。

## 复现

在工作区根目录运行。完整核心使用已有 `.toolchain/nestopia/nestopia_libretro.dylib`、system Python的Pillow和父存档；同步CPU使用已有py65环境。

```sh
python3 scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase7/runtime/natural-turn-repeat --compare analysis/phase7/runtime/natural-turn
.venv-trace/bin/python scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --mode cpu --out analysis/phase7/runtime/cpu-call
.venv-trace/bin/python scripts/capture_tactical_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --mode cpu --out analysis/phase7/runtime/cpu-call-repeat --compare analysis/phase7/runtime/cpu-call
```

上述native存档与核心hash绑定，不声称物理NES硬件验证。后续要验证成功计略、secondary phase1或更多策略，需要另有明确输入与作用域的回放；本目录未通过补写ack/readiness使这些路径看似完成。
