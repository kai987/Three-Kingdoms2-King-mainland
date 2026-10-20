# 势力缺席、全国统一判定与结束场景

本目录分析原ROM SHA256 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`，原文件只读。[faction_lifecycle.py](../../../source/recovered/faction_lifecycle.py) 是独立复原的字段算法和提升后的结束控制源码，不是原开发源码或完整独立游戏。

## 势力清理不是统一事务

以下条件在程序中分开使用：君主记录 `leaderID=FF`、城市 `owner low3=7`、武将 status3、`6F8B=FB` 通知，以及 `7A=13` 结束场景。不能看到其中一个就替其余字段补写。

君主记录有7条，地址 `$6F07+8*ruler`；byte0是leaderID，byte1是驻城，byte3是controller，byte4..7为外交nibble。原始范围、CPU/file地址与逐字节内容在[evidence.json](evidence.json)。

| 路径 | 实际效果 | 保留边界 |
|---|---|---|
| bank11 `$CA74..CA7E` | 继承选择已失败后，仅写当前ruler leaderID=FF、6F8B=FB | `$CA7F` 等待 **恰好1**；不清owner、名册、驻城、controller或外交 |
| bank26 `$C91B..C939` | 桥接收到FB后排C3消息，设置0401=12/040C=0 | 先前C7E0跨银行绘制外置；这里只准备通知 |
| bank26 `$CB9D..CBC2` | 040C byte递增，达到240后原CBBF写6F8B=1、0401=1 | 单独sub12需240次调用；sub11再接sub12需480次。不是视频帧数 |
| bank11 `$CA52..CA57` | 真实ack后调用C98F修正首将；D105仍对金米封顶9999 | `repair_after_successor_ack()` 复用独立[首将服务](../../phase5/transfer/README.md)，止CA58；后续7君主外循环/D249/BEC7属于其他控制器 |
| bank26 `$C386..C3BA` | 排C3通知、保存旧leader到042C、仅清ruler leaderID；按controller低2位选下个0402 | `(byte3&3)==3` 与AI前缀的 `byte3==3` **不同**；owner/名册/外交保留 |

丢失最后一城的owner writer由[城市归属报告](../ownership/README.md)独立恢复。该写入本身不构成上述leader/外交清理。常规controller先后还会查leader状态、候选继承人或其他名册；目前没有证据支持新增一个“一次性消灭势力”的统一交易。也不宣称只剩leaderID=FF而仍有旧owner的受控记录必然可由自然游玩产生。

`select_next_active_ruler()` 对应 bank25 `$A041..A090`：只按leaderID=FF跳过该slot，**没有**城市数量或controller条件。跳过仍会推进日期，并在月回绕时衰减外交nibble。5种原顺序表各7个有效slot、stride8，位于 `$A104` / file `0x032114`。如果7个leader全FF，原代码继续循环且推进日历，没有返回分支；高层API只执行一个7-slot周期并返回 `no_active_ruler_in_scan_period`，不假称回合结束。

## 有效武将池少于30的终止条件

bank25 `$A240..A295` / file `0x032250` 复制7个leaderID到042C列表，将当前ruler项置FF，然后扫描全部237条武将记录：排除其他leaderID，以及 `byte11&3 == 3` 的记录，其余计入0011。它包括status0/1/2；不查HP、所属城或城内名册。

`$A094` 比较0011与30：少于30排D5消息，设置0401=3；之后 `$A186` 仅在0300/0304均FF且A按键有效时跳原reset `$E000`。这不是“当前势力少于30名武将”，也不是城池统计。

![原D5提示](../runtime/messages/message-D5-zoom.png)

原核心受控绘制中清楚的新行是「もはや このニンズウでは」「ゼンコクトウイツは フカノウです」：这一人数已使全国统一不可能。画面残留的父菜单行不纳入转写。原消息fixture的参数、输入state与ROM/core/artifact hashes见[消息证据](../runtime/messages/evidence.json)；这是明确排队的显示fixture，不是自然残局事件。

![原C3通知](../runtime/messages/message-C3-zoom.png)

C3样例清楚显示曹操死亡、曹操一族灭亡。此处ID为受控显示参数；文字叙事不能代替真实HP/status/owner链，也不证明该存档中曹操实际死亡。

## 全30城统一与结局评分

bank27 `$A089..A0AF` 调 bank28 `$DDBF` 扫描30城，数 `owner&7 == 6F03`。**恰好30城**时写0400=15；它不查leader是否FF，也不自动清0401。原主表第15项是A075，farcall selector39→pair25/26 A01E→bank26 C435。此入口的正常caller为city main0/sub0；直接高层前缀保留任何既存0401，不掩盖错误上下文。

bank26 `$C441..C599` 读取EE/EF指向的君主记录，将leader作为042C。它累计所有30城治理byte11，及每城全部10槽中的非FF、非该leader项：不按owner筛选，不查HP/status，不去重。

```text
L = u16(所有参与名单项的忠诚总和)
N = u8(参与名单项数)
G = u16(30城治理总和)
loyaltyPart = floor(L / N)；N=0时原16bit除法返回65535
rosterPart = floor(N * 100 / 130)
governancePart = floor(G / 30)
score24 = floor(u24(loyaltyPart + rosterPart + governancePart) / 3)
```

原数据写到0435..0437。`$C606..C624` 在原输入/消息gate之后请求7A=13，并且只看 **0435低byte**：≥70→0541=1；40..69→2；<40→3。上两byte不参与这个分档。`best_intellect_for_summary()` 原 `$C626` 另在当前owner的30城/10槽中选最大知，相同值取后项；空集合保留ID0/value0。这些异常行为都保留，没有改成通用安全评分。

人类无继承人路径 `$C3DB..C41D` 同样进入7A=13，但设置0541=0。参数布局是：042C旧leader、042D原初君主名表值；042E为040C指定君主的当前leader，或FF；042F/430=`yearByte+100`、431=0；0432/433=`monthIndex+1`、434=0。Ending mode0首次初始化在042E为FF时请求D9，否则D8。

## 结束场景控制器

真实外层链为：global7A=13→fixed `$E46A`，设置NMI78=8并进行图形初始化；NMI `$FA53..FA85` 映射pair23/24并调 A01E→bank24 `$D693`。新的 `EndingControl` 只执行D693控制入口，**不执行或假完成E46A的PPU/NMI初始化**。D693内部F25F selector26实际把 `$8000` 数据窗选为physical bank6。

| 0541模式 | 原入口 | 有界子状态 |
|---:|---|---|
| 0 | `$D6AA` | 损失/族灭通知与等待；不使用0542分派 |
| 1 | `$D79B` | 初始评分低byte≥70路线；不使用0542分派 |
| 2 | `$D83A` | 初始评分40..69路线；不使用0542分派 |
| 3 | `$D8C9` | 初始评分<40路线；不使用0542分派 |
| 4 | `$D9CA` | 0542=0..6，7项武将列表/展示子状态 |
| 5 | `$D920` | 0542=0..5，6项最终消息/复位子状态 |

共6个primary模式，**17个合法mode/sub组合**，3张原inline指针表、668条提升IR；表结尾都恰好紧接首handler，字节边界保存在[ending-controller.json](ending-controller.json)，完整有界汇编见[ending-control.asm](ending-control.asm)。这是控制表完整性，不能代替全部分支动态覆盖。

mode0达到动画标记FE后，A按键且6F43=0才跳reset；6F43非零时原代码清该byte，恢复0400/0401=0472/0473、0402=0、global7A=1。这是原继续分支，不恢复leader、城市或武将。mode5/sub5也在0087为负时跳reset。所有reset/NMI屏障是明确停止边界。

武将展示缓冲 `$D9DE..DA40` 以FE、leader开头，然后扫30×10槽并追加非FF/非当前0411项，末尾FE/FF。索引是byte、没有300项容量检查，密集重复的受控名册可以回绕并覆盖原leader替换值0411及其他RAM；高层代码按原动态别名执行，没有擅自去重或扩容。此异常fixture不证明自然可达。

## 原ROM对照

[最终回执](validation.json)：**9,699例通过、0失败**。

- 独立高层源码9,631例：城数/30城前缀；5种轮序与leaderFF；全237武将池/阈值/复位gate；FB仅清leader与精确ack；真实计时；通知与controller低2位；ack后首将/资源修正；人类结束参数；评分零除/byte/word回绕；知最大值平手；仅低byte分档；展示缓冲别名；继续或复位。
- 结束控制IR68例：全部17合法组合各4种有记录fixture，65例原入口返回，3例停于真实边界：mode0复位、mode5/sub4 NMI、mode5/sub5复位。动态覆盖434/668条，未动态执行的指令仍只声称静态恢复。
- 全部7leaderFF的40例是一个7-slot周期的**原非返回路径前缀**，已经包含在高层数中，不称为完整返回。

独立高层比较全部SRAM及每个入口声明的RAM字段，不声称CPU寄存器/栈等价。结束IR比较全部CPU寄存器/flags/stack、2KiB RAM、8KiB SRAM及物理PRG窗；外部helper在此验证器中明确执行原ROM，因此不能宣称那些renderer/farbank/helper也已独立复原。高层算法自身不执行原6502。

```sh
python3 scripts/analyze_faction_lifecycle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_faction_lifecycle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

```python
from source.recovered.faction_lifecycle import FactionTables, FactionLifecycle, EndingControl

tables = FactionTables.from_rom(rom_bytes)
rules = FactionLifecycle(shared_cpu_memory, tables)
view = rules.snapshot(ruler=2)
score = rules.victory_score()  # caller必须提供真实EE/EF君主记录指针
wait = rules.repair_after_successor_ack(ruler=2)  # 不注入ack；未收到1就等待
ending = EndingControl(mapped_cpu_memory, hooks=explicit_services)
result = ending.step()  # pair23/24、E1..E3/OAM与renderer context由caller准备
```

Missing hooks会报具体依赖；`ending.step()` 返回自己的mode0541/sub0542/04C9..CE/6F43诊断。银行映射、显示队列完成、真实NMI和一次“视频帧”是不同接口责任。原C3/D5/D8/D9画面及重复hash验证是外置消息绘制证据，不能把直接CPU fixture升级为已自然通关。
