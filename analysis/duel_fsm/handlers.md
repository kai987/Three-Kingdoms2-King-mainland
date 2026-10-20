# 单挑主/子状态逐项目录

功能名称结合实际字节读写；退却/投降/説得/罵倒对应已验证的原菜单字形，见phase4/terrain及phase4/duel报告。条件的精确分支目标与全部作用见同条的CFG地址、写入及外部依赖；`handlers.asm`和`program.json`保留每条可执行操作。

| 主状态 | 类别 | 入口 | 有效子状态 | 行为 |
|---:|---|---|---|---|
| 0 | control | `$B144` | 0..7 | 读取记录及初始化场景 |
| 1 | control | `$B34F` | 0..5 | 轮换行动者与玩家/电脑入口 |
| 2 | control | `$B5C8` | 0..4 | 电脑动作选择 |
| 3 | control | `$B8C7` | 0..2 | 普通扣体及确认写回 |
| 4 | control | `$BA6D` | 0..9 | 退却、追击与永久体力扣减 |
| 5 | control | `$BC3B` | 0..2 | 显示双方武将资料 |
| 6 | control | `$BCE9` | 0..5 | 投降结果动画 |
| 7 | control | `$BE78` | 0..3 | 説得候选结果 |
| 8 | control | `$C08A` | 忽略子状态，一次性函数 | 罵倒及04B5持续状态 |
| 9 | control | `$C116` | 0..3 | 双方对白及控制回调 |
| 10 | initialization_alias | `$B144` | 0..7 | 初始化别名0 |
| 11 | initialization_alias | `$B144` | 0..7 | 初始化别名0 |
| 12 | initialization_alias | `$B144` | 0..7 | 初始化别名0 |
| 13 | animation | `$C21C` | 0..3 | 零体力表现 |
| 14 | result_return | `$C2F6` | 0..3 | 结果与装备奖励、回战斗 |
| 15 | result_return | `$C464` | 0..1 | 结果淡出、回普通攻击场景 |
| 16 | animation | `$C498` | 0..6 | 动作类别0移动表现 |
| 17 | animation | `$C689` | 0..7 | 动作类别2移动表现 |
| 18 | animation | `$C949` | 0..7 | 动作类别6移动表现 |
| 19 | animation | `$CB9E` | 0..2 | 移动归位与恢复保存状态 |
| 20 | animation | `$CC87` | 0..2 | 向外移动及恢复状态 |
| 21 | animation | `$CD3C` | 0..2 | 向内移动及恢复状态 |

## 主状态 0：读取记录及初始化场景

### 子状态 0 / `$B15A`

等待0087 bit7；从两条永久记录读取体力到04B1/B2，按武器ID分动画类；请求左侧精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B15D` BMI→`$B160`，`$B178` BCC→`$B165`，`$B190` BCC→`$B197`，`$B199` BCC→`$B1A0`

绝对地址写入：`$B160` INC `$04A9`(abs)，`$B16F` STA `$04B1`(abx)，`$B17C` STA `$0000`(abs)，`$B1A2` STA `$04AF`(abx)

外部依赖：$CDFD, $F2D7

### 子状态 1 / `$B1A6`

等待007E&4清零；请求第一组背景精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1AB` BNE→`$B1BA`

绝对地址写入：`$B1AF` STA `$0000`(abs)，`$B1B7` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 2 / `$B1BB`

等待007E&4清零；请求右侧武器精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1C0` BNE→`$B1D3`

绝对地址写入：`$B1C4` STA `$0000`(abs)，`$B1D0` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 3 / `$B1D4`

等待007E&4清零；请求第二组背景精灵，暂置actor=1

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1D9` BNE→`$B1ED`

绝对地址写入：`$B1DD` STA `$0000`(abs)，`$B1E5` INC `$04A9`(abs)，`$B1EA` STA `$04AA`(abs)

外部依赖：$CDFD

### 子状态 4 / `$B1EE`

排队双方名称，标记显示更新待处理

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B1F7` STA `$0003`(abs)，`$B202` STA `$0003`(abs)，`$B20D` STA `$0380`(abx)，`$B210` INC `$04A9`(abs)，`$B218` STA `$007E`(abs)

外部依赖：$CFA3, $F25F

### 子状态 5 / `$B21C`

D060写回双方体力并排队显示；设置007E bit2

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B221` STA `$0380`(abx)，`$B224` INC `$04A9`(abs)，`$B22C` STA `$007E`(abs)

外部依赖：$D060

### 子状态 6 / `$B230`

由体力、武力及武器/防具修正生成04B3/B4，随机比较选择actor；清04C0

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B29C` BCS→`$B295`，`$B2A7` BNE→`$B232`，`$B2B1` BCS→`$B2B4`

绝对地址写入：`$B23C` STA `$0010`(abs)，`$B247` STA `$0011`(abs)，`$B24F` STA `$0010`(abs)，`$B256` STA `$0010`(abs)，`$B263` STA `$0010`(abs)，`$B26A` STA `$0002`(abs)，`$B275` STA `$0001`(abs)，`$B27A` STA `$0002`(abs)，`$B27D` STA `$0004`(abs)，`$B282` STA `$0003`(abs)，`$B292` STA `$04B3`(abx)，`$B2A1` STA `$04BD`(abx)，`$B2B4` STX `$04AA`(abs)，`$B2B9` STA `$04C0`(abs)，`$B2BC` INC `$04A9`(abs)

外部依赖：$E87A, $EA7C, $F2D7

### 子状态 7 / `$B2E0`

按双方武器动画类读9项表设置04C5/C6，准备双边对白后去state9

可能控制转移：`$B33A`写`$04A8`=9；`$B33F`写`$04A9`=0

条件分支：无

绝对地址写入：`$B2E6` STA `$0000`(abs)，`$B2EF` STA `$0001`(abs)，`$B302` STA `$04C5`(abs)，`$B315` STA `$04C6`(abs)，`$B31A` STA `$04C3`(abs)，`$B31D` STA `$04C4`(abs)，`$B326` STA `$042C`(abs)，`$B32B` STA `$04BD`(abs)，`$B330` STA `$04BE`(abs)，`$B335` STA `$04BF`(abs)，`$B33A` STA `$04A8`(abs)，`$B33F` STA `$04A9`(abs)

外部依赖：无


## 主状态 1：轮换行动者与玩家/电脑入口

### 子状态 0 / `$B361`

处理04C0，轮换actor；更新04B5持续状态与04C3；依04AB/AC决定玩家或电脑

可能控制转移：`$B39B`写`$04A8`=2

条件分支：`$B364` BNE→`$B36E`，`$B376` BCC→`$B37B`，`$B389` BEQ→`$B391`，`$B397` BPL→`$B39F`，`$B3B7` BEQ→`$B3BB`，`$B3CF` BCS→`$B3C8`，`$B3DA` BCC→`$B3C8`，`$B3E4` BCC→`$B3E7`

绝对地址写入：`$B36B` STA `$04AA`(abs)，`$B36E` INC `$04C0`(abs)，`$B380` STA `$04AA`(abs)，`$B38E` STA `$04B5`(aby)，`$B39B` STA `$04A8`(abs)，`$B3A5` STA `$0000`(abs)，`$B3BB` STA `$00A4`(abs)，`$B3BE` INC `$04A9`(abs)，`$B3D4` STA `$04BD`(abx)，`$B3E7` STX `$04AA`(abs)，`$B3EC` STA `$04C0`(abs)

外部依赖：$E87A, $F26D；farcall `$B3AA`→`$A030`（Y指定银行）

### 子状态 1 / `$B3F0`

等待名称/对白队列完成，画主菜单

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B3F6` BCC→`$B406`

绝对地址写入：`$B3FA` STA `$0424`(abs)，`$B3FD` STA `$0425`(abs)，`$B400` INC `$04A9`(abs)

外部依赖：$D166, $D17C, $D299

### 子状态 2 / `$B407`

读取方向/确认键；动作4「せんじゅつ」进入戦術子菜单或退回

可能控制转移：`$B45D`写`$04A9`=2

条件分支：`$B43A` BCC→`$B460`，`$B447` BNE→`$B460`，`$B451` BNE→`$B45B`

绝对地址写入：`$B40C` STA `$0010`(abs)，`$B411` STA `$0011`(abs)，`$B416` STA `$0012`(abs)，`$B41E` STA `$0010`(abs)，`$B423` STA `$0011`(abs)，`$B428` STA `$0000`(abs)，`$B42D` STA `$0001`(abs)，`$B43C` INC `$04A9`(abs)，`$B442` STA `$04BF`(abs)，`$B453` INC `$04A9`(abs)，`$B45D` STA `$04A9`(abs)

外部依赖：$D166, $ED1E, $EDF5, $F26D

### 子状态 3 / `$B47E`

按04BF分派到4/5/6/7/8或16/17/18；动作3受D262君主条件限制

可能控制转移：`$B48F`写`$04A8`=16；`$B494`写`$04A9`=0；`$B4AB`写`$04A8`=4；`$B4B0`写`$04A9`=0；`$B4C8`写`$04A8`=17；`$B4CD`写`$04A9`=0；`$B4ED`写`$04A8`=6；`$B4F2`写`$04A9`=0；`$B500`写`$04A8`=5；`$B505`写`$04A9`=0；`$B522`写`$04A8`=18；`$B527`写`$04A9`=0；`$B53E`写`$04A8`=7；`$B543`写`$04A9`=0；`$B549`写`$04A8`=8；`$B54E`写`$04A9`=0

条件分支：`$B481` BNE→`$B4A5`，`$B4A7` BNE→`$B4B8`，`$B4BA` BNE→`$B4DE`，`$B4E0` BNE→`$B4FA`，`$B4E5` BCC→`$B4EB`，`$B4FC` BNE→`$B512`，`$B514` BNE→`$B538`，`$B53A` BNE→`$B547`

绝对地址写入：`$B485` STA `$04BD`(abs)，`$B48A` STA `$04BE`(abs)，`$B48F` STA `$04A8`(abs)，`$B494` STA `$04A9`(abs)，`$B49D` STA `$042C`(abs)，`$B4AB` STA `$04A8`(abs)，`$B4B0` STA `$04A9`(abs)，`$B4BE` STA `$04BD`(abs)，`$B4C3` STA `$04BE`(abs)，`$B4C8` STA `$04A8`(abs)，`$B4CD` STA `$04A9`(abs)，`$B4D6` STA `$042C`(abs)，`$B4E7` DEC `$04A9`(abs)，`$B4ED` STA `$04A8`(abs)，`$B4F2` STA `$04A9`(abs)，`$B500` STA `$04A8`(abs)，`$B505` STA `$04A9`(abs)，`$B50B` STA `$04BE`(abs)，`$B50E` STA `$04BF`(abs)，`$B518` STA `$04BD`(abs)，`$B51D` STA `$04BE`(abs)，`$B522` STA `$04A8`(abs)，`$B527` STA `$04A9`(abs)，`$B530` STA `$042C`(abs)，`$B53E` STA `$04A8`(abs)，`$B543` STA `$04A9`(abs)，`$B549` STA `$04A8`(abs)，`$B54E` STA `$04A9`(abs)

外部依赖：$D262, $F28B

### 子状态 4 / `$B552`

等待对白后画戦術菜单

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B558` BCC→`$B568`

绝对地址写入：`$B55A` INC `$04A9`(abs)，`$B55F` STA `$0424`(abs)，`$B562` STA `$0425`(abs)

外部依赖：$D166, $D17C, $D299

### 子状态 5 / `$B569`

戦術菜单「せっとく」「ばとう」确认写04BF=选项+7回sub3；取消回sub1

可能控制转移：`$B5A9`写`$04A9`=3；`$B5B2`写`$04A9`=1

条件分支：`$B59C` BCC→`$B5AD`，`$B5AE` BCC→`$B5BA`

绝对地址写入：`$B56E` STA `$0010`(abs)，`$B573` STA `$0011`(abs)，`$B578` STA `$0012`(abs)，`$B580` STA `$0010`(abs)，`$B585` STA `$0011`(abs)，`$B58A` STA `$0000`(abs)，`$B58F` STA `$0001`(abs)，`$B5A4` STA `$04BF`(abs)，`$B5A9` STA `$04A9`(abs)，`$B5B2` STA `$04A9`(abs)

外部依赖：$D166, $ED1E, $EDF5, $F26D


## 主状态 2：电脑动作选择

### 子状态 0 / `$B5D8`

以当前体力、原始体力一半、对手体力及君主条件尝试动作3；跳过或前进

可能控制转移：`$B7AA`写`$04A8`=1；`$B7AF`写`$04A9`=3

条件分支：`$B5FE` BCS→`$B61F`，`$B603` BCS→`$B622`，`$B608` BCS→`$B622`，`$B610` BCS→`$B622`，`$B615` BEQ→`$B622`

绝对地址写入：`$B5E1` STA `$0010`(abs)，`$B5F2` STA `$0011`(abs)，`$B619` STA `$04BF`(abs)，`$B61F` INC `$04A9`(abs)，`$B622` INC `$04A9`(abs)，`$B7AA` STA `$04A8`(abs)，`$B7AF` STA `$04A9`(abs)，`$B7B9` STA `$0010`(abs)

外部依赖：$D262, $F2D7, $F387

### 子状态 1 / `$B626`

以双方体力差及B7DD随机门槛尝试动作6

可能控制转移：`$B7AA`写`$04A8`=1；`$B7AF`写`$04A9`=3

条件分支：`$B63E` BCS→`$B655`，`$B646` BCS→`$B655`，`$B64B` BEQ→`$B655`，`$B7F4` BCC→`$B7F9`，`$B80C` BPL→`$B810`

绝对地址写入：`$B62F` STA `$0010`(abs)，`$B64F` STA `$04BF`(abs)，`$B655` INC `$04A9`(abs)，`$B7AA` STA `$04A8`(abs)，`$B7AF` STA `$04A9`(abs)，`$B7EA` STA `$0010`(abs)，`$B7F6` STA `$0010`(abs)，`$B803` STA `$0010`(abs)，`$B810` STA `$0010`(abs)

外部依赖：$E843, $F2D7

### 子状态 2 / `$B659`

低体力条件及B816随机门槛尝试动作2（保留原字节/寄存器行为）

可能控制转移：`$B7AA`写`$04A8`=1；`$B7AF`写`$04A9`=3

条件分支：`$B661` BCS→`$B685`，`$B66E` BCC→`$B685`，`$B676` BCS→`$B685`，`$B67B` BEQ→`$B685`，`$B83A` BPL→`$B83E`，`$B847` BPL→`$B84B`

绝对地址写入：`$B67F` STA `$04BF`(abs)，`$B685` INC `$04A9`(abs)，`$B7AA` STA `$04A8`(abs)，`$B7AF` STA `$04A9`(abs)，`$B826` STA `$0010`(abs)，`$B83E` STA `$0010`(abs)，`$B84B` STA `$0010`(abs)

外部依赖：$E843, $F2D7

### 子状态 3 / `$B689`

比较双方知/武与04B5状态，分别尝试动作7、动作8

可能控制转移：`$B7AA`写`$04A8`=1；`$B7AF`写`$04A9`=3

条件分支：`$B691` BEQ→`$B696`，`$B6B6` BCS→`$B6CD`，`$B6BE` BCS→`$B6CD`，`$B6C3` BEQ→`$B6CD`，`$B6F0` BCC→`$B715`，`$B6F8` BCS→`$B715`，`$B700` BMI→`$B715`，`$B70B` BNE→`$B715`，`$B891` BPL→`$B895`，`$B8B6` BCS→`$B8BA`，`$B8BD` BPL→`$B8C1`

绝对地址写入：`$B6A0` STA `$0010`(abs)，`$B6C7` STA `$04BF`(abs)，`$B6DA` STA `$0010`(abs)，`$B70F` STA `$04BF`(abs)，`$B715` INC `$04A9`(abs)，`$B7AA` STA `$04A8`(abs)，`$B7AF` STA `$04A9`(abs)，`$B85E` STA `$0010`(abs)，`$B869` STA `$0010`(abs)，`$B870` STA `$0011`(abs)，`$B887` STA `$0011`(abs)，`$B895` STA `$0010`(abs)，`$B8AB` STA `$0010`(abs)，`$B8C1` STA `$0010`(abs)

外部依赖：$E843, $F2D7

### 子状态 4 / `$B719`

按双方体力三个区间和R(8)查B760动作表；回state1/sub3

可能控制转移：`$B7AA`写`$04A8`=1；`$B7AF`写`$04A9`=3

条件分支：`$B726` BCC→`$B730`，`$B72C` BCC→`$B730`，`$B738` BCC→`$B74B`，`$B744` BCC→`$B74B`

绝对地址写入：`$B74E` STA `$0000`(abs)，`$B75A` STA `$04BF`(abs)，`$B7AA` STA `$04A8`(abs)，`$B7AF` STA `$04A9`(abs)

外部依赖：$E856


## 主状态 3：普通扣体及确认写回

### 子状态 0 / `$B8D3`

调用BA15伤害参数，应用类别与04B5效果、判定命中/反伤/零伤；修改临时HP，排队结果对白

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B8E1` BEQ→`$B909`，`$B8FC` BCC→`$B909`，`$B90C` BNE→`$B92B`，`$B913` BCC→`$B918`，`$B92D` BNE→`$B962`，`$B934` BCS→`$B940`，`$B947` BCS→`$B909`，`$B958` BPL→`$B95C`，`$B96B` BCS→`$B9A0`，`$B970` BEQ→`$B99B`，`$B972` BMI→`$B99B`，`$B981` BCS→`$B985`，`$BA26` BEQ→`$BA2A`，`$BA56` BCS→`$BA4F`，`$BA65` BPL→`$BA69`

绝对地址写入：`$B8D3` INC `$04A9`(abs)，`$B8E9` STA `$0010`(abs)，`$B8F4` STA `$0002`(abs)，`$B900` STA `$0002`(abs)，`$B903` INC `$0001`(abs)，`$B91A` STA `$0003`(abs)，`$B91F` STA `$0002`(abs)，`$B922` STA `$0004`(abs)，`$B93A` STA `$0001`(abs)，`$B94B` STA `$0000`(abs)，`$B95C` STA `$04B1`(aby)，`$B985` STA `$04B1`(aby)，`$B98B` STA `$042C`(abs)，`$B990` STA `$042D`(abs)，`$B993` STA `$042E`(abs)，`$BA18` STA `$0010`(abs)，`$BA2D` STA `$0001`(abs)，`$BA38` STA `$0001`(abs)，`$BA42` STA `$0002`(abs)，`$BA4C` STA `$0001`(abs)，`$BA5B` STA `$0002`(abs)，`$BA69` STA `$0001`(abs)

外部依赖：$E843, $E87A, $EA7C, $F26D, $F28B

### 子状态 1 / `$B9A5`

等待双对白队列完成及A/B确认；D060将双方临时HP写入永久记录，等待显示更新

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B9A8` BCC→`$B9C7`，`$B9B2` BEQ→`$B9C7`

绝对地址写入：`$B9B9` STA `$0380`(abx)，`$B9BC` INC `$04A9`(abs)，`$B9C4` STA `$007E`(abs)

外部依赖：$D060, $D13D, $D299

### 子状态 2 / `$B9C8`

等待007E bit2清零；优先检查当前actor体力，其次另一方；继续state1或结果2进入state13

可能控制转移：`$B9E4`写`$04A8`=1；`$B9E9`写`$04A9`=0；`$BA0C`写`$04A8`=13；`$BA11`写`$04A9`=0

条件分支：`$B9CD` BNE→`$B9EC`，`$B9D5` BEQ→`$B9ED`，`$B9E0` BEQ→`$B9ED`，`$B9F8` BNE→`$B9FC`

绝对地址写入：`$B9E4` STA `$04A8`(abs)，`$B9E9` STA `$04A9`(abs)，`$B9ED` STY `$04AA`(abs)，`$B9F3` STA `$042C`(abs)，`$B9FE` STA `$0515`(aby)，`$BA07` STA `$0515`(aby)，`$BA0C` STA `$04A8`(abs)，`$BA11` STA `$04A9`(abs)

外部依赖：无


## 主状态 4：退却、追击与永久体力扣减

### 子状态 0 / `$BA87`

等待对白；请求当前武将肖像及消息29

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BA8A` BCC→`$BAA4`

绝对地址写入：`$BA8C` INC `$04A9`(abs)，`$BA95` STA `$0000`(abs)

外部依赖：$D299, $F26D；farcall `$BA9A`→`$A030`（Y指定银行）

### 子状态 1 / `$BAA5`

等待确认；排队消息0

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BAAB` BCC→`$BABF`，`$BAB5` BEQ→`$BABF`

绝对地址写入：`$BAB7` INC `$04A9`(abs)

外部依赖：$D13D, $D166, $D299, $F28B

### 子状态 2 / `$BAC0`

等待对白；保存返回4/sub3，去state20

可能控制转移：`$BAD1`写`$04A8`=20；`$BAD6`写`$04A9`=0

条件分支：`$BAC3` BCC→`$BAD9`

绝对地址写入：`$BAC7` STA `$04BD`(abs)，`$BACC` STA `$04BE`(abs)，`$BAD1` STA `$04A8`(abs)，`$BAD6` STA `$04A9`(abs)

外部依赖：$D299

### 子状态 3 / `$BADA`

轮换actor，请求另一方肖像及消息2A

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BADD` BCC→`$BB02`

绝对地址写入：`$BAE4` STA `$04AA`(abs)，`$BAEB` STA `$0000`(abs)，`$BAF7` STA `$00A4`(abs)，`$BAFA` INC `$04A9`(abs)

外部依赖：$D299, $F26D；farcall `$BAF0`→`$A030`（Y指定银行）

### 子状态 4 / `$BB03`

确认后以另一方04B3*2与R100比较，去sub9或sub5

可能控制转移：`$BB30`写`$04A9`=9

条件分支：`$BB0C` BCC→`$BB40`，`$BB16` BEQ→`$BB40`，`$BB2C` BCS→`$BB38`

绝对地址写入：`$BB23` STA `$0011`(abs)，`$BB30` STA `$04A9`(abs)，`$BB38` INC `$04A9`(abs)

外部依赖：$D13D, $D166, $D299, $E843, $F26D, $F28B

### 子状态 5 / `$BB41`

等待对白；保存返回4/sub6，去state21

可能控制转移：`$BB52`写`$04A8`=21；`$BB57`写`$04A9`=0

条件分支：`$BB44` BCC→`$BB5A`

绝对地址写入：`$BB48` STA `$04BD`(abs)，`$BB4D` STA `$04BE`(abs)，`$BB52` STA `$04A8`(abs)，`$BB57` STA `$04A9`(abs)

外部依赖：$D299

### 子状态 6 / `$BB5B`

对另一方永久记录体力扣R(10)+5，按SBC/BPL裁剪，排队消息3D

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BB85` BPL→`$BB89`

绝对地址写入：`$BB63` STA `$042F`(abs)，`$BB68` STA `$0430`(abs)，`$BB6B` STA `$0431`(abs)，`$BB77` STA `$042C`(abs)，`$BB8B` INC `$04A9`(abs)

外部依赖：$E862, $F28B, $F2D7

### 子状态 7 / `$BB93`

确认后读受击永久体力；非零转BC16；零则排队消息26去sub8

可能控制转移：`$BC32`写`$04A8`=15；`$BC37`写`$04A9`=0

条件分支：`$BB96` BCC→`$BBBF`，`$BBA0` BEQ→`$BBBF`，`$BBB2` BEQ→`$BBB7`，`$BC1E` BEQ→`$BC22`

绝对地址写入：`$BBB7` INC `$04A9`(abs)，`$BC1B` STA `$04AA`(abs)，`$BC24` STA `$0515`(aby)，`$BC2D` STA `$0515`(aby)，`$BC32` STA `$04A8`(abs)，`$BC37` STA `$04A9`(abs)

外部依赖：$D13D, $D299, $F28B, $F2D7

### 子状态 8 / `$BBC0`

确认后写另一方结果2，当前方0；去state14，04C0=FF

可能控制转移：`$BBF2`写`$04A8`=14；`$BBF7`写`$04A9`=0

条件分支：`$BBC3` BCC→`$BBCF`，`$BBCD` BNE→`$BBD0`，`$BBDE` BNE→`$BBE2`

绝对地址写入：`$BBD9` STA `$042C`(abs)，`$BBE4` STA `$0515`(aby)，`$BBED` STA `$0515`(aby)，`$BBF2` STA `$04A8`(abs)，`$BBF7` STA `$04A9`(abs)，`$BBFC` STA `$04C0`(abs)

外部依赖：$D13D, $D299

### 子状态 9 / `$BC00`

等待确认；BC16轮换actor并据控制条件回state1或state2

可能控制转移：`$BC32`写`$04A8`=15；`$BC37`写`$04A9`=0

条件分支：`$BC09` BCC→`$BC15`，`$BC13` BNE→`$BC16`，`$BC1E` BEQ→`$BC22`

绝对地址写入：`$BC1B` STA `$04AA`(abs)，`$BC24` STA `$0515`(aby)，`$BC2D` STA `$0515`(aby)，`$BC32` STA `$04A8`(abs)，`$BC37` STA `$04A9`(abs)

外部依赖：$D13D, $D166, $D299


## 主状态 5：显示双方武将资料

### 子状态 0 / `$BC47`

清040C/040D，选定0410武将ID并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$BC47` INC `$04A9`(abs)，`$BC4C` STA `$040C`(abs)，`$BC4F` STA `$040D`(abs)，`$BC58` STA `$0410`(abs)

外部依赖：无

### 子状态 1 / `$BC5C`

显示面板、farcall武将资料；040D=FF才推进并更新窗口参数

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BC77` BNE→`$BC8B`

绝对地址写入：`$BC5F` STA `$04AA`(abs)，`$BC68` STA `$04AA`(abs)，`$BC7B` STA `$00BB`(abs)，`$BC7E` INC `$04A9`(abs)，`$BC83` STA `$0098`(abs)，`$BC88` STA `$0097`(abs)

外部依赖：$D166；farcall `$BC6D`→`$A012`（Y指定银行）

### 子状态 2 / `$BC8C`

040D负时，按钮位4/5切换双方并回sub0；B按钮回state1/sub2，恢复原actor及窗口参数

可能控制转移：`$BCBB`写`$04A9`=0；`$BCC1`写`$04A8`=1；`$BCC6`写`$04A9`=2

条件分支：`$BC9E` BPL→`$BCBE`，`$BCA8` BNE→`$BCBF`，`$BCAF` BEQ→`$BCBE`

绝对地址写入：`$BC8F` STA `$04AA`(abs)，`$BC98` STA `$04AA`(abs)，`$BCA3` STA `$0010`(abs)，`$BCB6` STA `$04BE`(abs)，`$BCBB` STA `$04A9`(abs)，`$BCC1` STA `$04A8`(abs)，`$BCC6` STA `$04A9`(abs)，`$BCCC` STA `$04AA`(abs)，`$BCD1` STA `$00BB`(abs)，`$BCD6` STA `$00BC`(abs)，`$BCDB` STA `$00BD`(abs)，`$BCE0` STA `$0097`(abs)，`$BCE5` STA `$0098`(abs)

外部依赖：$D166


## 主状态 6：投降结果动画

### 子状态 0 / `$BCFB`

等待对白，请求武将肖像及消息27

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BCFE` BCC→`$BD1D`

绝对地址写入：`$BD00` INC `$04A9`(abs)，`$BD09` STA `$0000`(abs)，`$BD15` STA `$00A4`(abs)

外部依赖：$D299, $F26D；farcall `$BD0E`→`$A030`（Y指定银行）

### 子状态 1 / `$BD1E`

等待对白确认，设置声音/调色并排队消息0

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BD24` BCC→`$BD5C`，`$BD2E` BEQ→`$BD5C`

绝对地址写入：`$BD30` INC `$04A9`(abs)

外部依赖：$D13D, $D166, $D299, $E57F, $E683, $F28B

### 子状态 2 / `$BD40`

等待对白，推进并请求行动方起始精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BD43` BCC→`$BD5C`，`$BD50` BEQ→`$BD57`

绝对地址写入：`$BD45` INC `$04A9`(abs)，`$BD4A` STA `$0000`(abs)，`$BD54` STA `$0000`(abs)

外部依赖：$CDFD, $D299

### 子状态 3 / `$BD5D`

设04B8计时及04BB位置、调色并请求投降表现精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BD98` BEQ→`$BDA4`

绝对地址写入：`$BD5F` STA `$00C6`(abs)，`$BD62` STA `$00CE`(abs)，`$BD65` STA `$00D6`(abs)，`$BD6A` STA `$00C7`(abs)，`$BD6D` STA `$00CF`(abs)，`$BD70` STA `$00D7`(abs)，`$BD75` STA `$00C8`(abs)，`$BD78` STA `$00D0`(abs)，`$BD7B` STA `$00D8`(abs)，`$BD80` STA `$04B8`(abs)，`$BD85` STA `$04BA`(abs)，`$BD88` INC `$04A9`(abs)，`$BD8D` STA `$04BB`(abs)，`$BD92` STA `$0000`(abs)，`$BD9C` STA `$04BB`(abs)，`$BDA1` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 4 / `$BDA9`

按04B8>>5的帧索引绘制；帧5排队消息28并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$BDB8` BNE→`$BDCB`，`$BDD4` BNE→`$BDDF`，`$BE21` BCC→`$BE3E`，`$BE27` BEQ→`$BE2B`

绝对地址写入：`$BDA9` INC `$04B8`(abs)，`$BDBA` INC `$04A9`(abs)，`$BDC3` STA `$042C`(abs)，`$BDCB` STA `$0010`(abs)，`$BDCE` STA `$0011`(abs)，`$BDDC` STA `$0010`(abs)，`$BDE1` STA `$0002`(abs)，`$BDF3` STA `$0002`(abs)，`$BDFC` STA `$0000`(abs)，`$BE14` STA `$0010`(abs)，`$BE19` STA `$0002`(abs)，`$BE2B` STY `$0000`(abs)

外部依赖：$CEA5, $F28B

### 子状态 5 / `$BE3F`

等待对白和确认；actor结果3、另一方0；04C0=80，去state14

可能控制转移：`$BE6F`写`$04A8`=14；`$BE74`写`$04A9`=0

条件分支：`$BDD4` BNE→`$BDDF`，`$BE21` BCC→`$BE3E`，`$BE27` BEQ→`$BE2B`，`$BE47` BCC→`$BE77`，`$BE51` BEQ→`$BE77`，`$BE56` BEQ→`$BE5A`

绝对地址写入：`$BDCB` STA `$0010`(abs)，`$BDCE` STA `$0011`(abs)，`$BDDC` STA `$0010`(abs)，`$BDE1` STA `$0002`(abs)，`$BDF3` STA `$0002`(abs)，`$BDFC` STA `$0000`(abs)，`$BE14` STA `$0010`(abs)，`$BE19` STA `$0002`(abs)，`$BE2B` STY `$0000`(abs)，`$BE5C` STA `$0515`(aby)，`$BE65` STA `$0515`(aby)，`$BE6A` STA `$04C0`(abs)，`$BE6F` STA `$04A8`(abs)，`$BE74` STA `$04A9`(abs)

外部依赖：$CEA5, $D13D, $D299


## 主状态 7：説得候选结果

### 子状态 0 / `$BE86`

用对手忠/体及actor知+徳三档索引BFB2表，写04BF和双方对白编号，去state9

可能控制转移：`$BF3A`写`$04A8`=9；`$BF3F`写`$04A9`=0

条件分支：`$BEC2` BCS→`$BED5`，`$BECE` BCS→`$BED5`，`$BEDA` BCS→`$BEED`，`$BEE6` BCS→`$BEED`，`$BEF2` BCS→`$BF05`，`$BEFE` BCS→`$BF05`，`$BF2B` BCS→`$BF38`

绝对地址写入：`$BE96` STA `$0010`(abs)，`$BE9D` STA `$0011`(abs)，`$BEAD` STA `$0012`(abs)，`$BEB8` STA `$0012`(abs)，`$BF08` STA `$0010`(abs)，`$BF14` STA `$04BF`(abs)，`$BF1A` STA `$04BE`(abs)，`$BF23` STA `$04BD`(abs)，`$BF35` STA `$04C3`(aby)，`$BF3A` STA `$04A8`(abs)，`$BF3F` STA `$04A9`(abs)

外部依赖：$E856, $F2D7

### 子状态 1 / `$BF43`

另一方结果1、当前方0；去state15

可能控制转移：`$BF5D`写`$04A8`=15；`$BF62`写`$04A9`=0

条件分支：`$BF49` BEQ→`$BF4D`

绝对地址写入：`$BF4F` STA `$0515`(aby)，`$BF58` STA `$0515`(aby)，`$BF5D` STA `$04A8`(abs)，`$BF62` STA `$04A9`(abs)

外部依赖：无

### 子状态 2 / `$BF66`

双方结果0，04C0=FF；去state14

可能控制转移：`$BF70`写`$04A8`=14；`$BF75`写`$04A9`=0

条件分支：无

绝对地址写入：`$BF68` STA `$0515`(abs)，`$BF6B` STA `$0517`(abs)，`$BF70` STA `$04A8`(abs)，`$BF75` STA `$04A9`(abs)，`$BF7A` STA `$04C0`(abs)

外部依赖：无

### 子状态 3 / `$BF7E`

等待对白确认；另一方结果4、当前方0，04C0=FF；去state14

可能控制转移：`$BFA4`写`$04A8`=14；`$BFA9`写`$04A9`=0

条件分支：`$BF81` BCC→`$BFB1`，`$BF8B` BEQ→`$BFB1`，`$BF90` BEQ→`$BF94`

绝对地址写入：`$BF96` STA `$0515`(aby)，`$BF9F` STA `$0515`(aby)，`$BFA4` STA `$04A8`(abs)，`$BFA9` STA `$04A9`(abs)，`$BFAE` STA `$04C0`(abs)

外部依赖：$D13D, $D299


## 主状态 8：罵倒及04B5持续状态

### 子状态 0 / `$C08A`

一次性处理：actor04B5=80；知+徳与对手知差的u8运算、R10和110门槛决定对手04B5持续值，准备双边对白，去state9

可能控制转移：`$C10A`写`$04A8`=9；`$C10F`写`$04A9`=0

条件分支：`$C0BF` BCS→`$C0C3`，`$C0CE` BCS→`$C0C9`，`$C0D5` BCS→`$C0DF`，`$C0E5` BEQ→`$C0DF`

绝对地址写入：`$C08F` STA `$04B5`(aby)，`$C0A0` STA `$0011`(abs)，`$C0B0` STA `$0010`(abs)，`$C0C3` STA `$0010`(abs)，`$C0C6` INC `$0010`(abs)，`$C0D9` STA `$04BE`(abs)，`$C0E2` STA `$0010`(abs)，`$C0E7` INC `$0010`(abs)，`$C0EA` INC `$0010`(abs)，`$C0F6` STA `$04B5`(aby)，`$C0FB` STA `$04C3`(aby)，`$C100` STA `$04BE`(abs)，`$C105` STA `$04BD`(abs)，`$C10A` STA `$04A8`(abs)，`$C10F` STA `$04A9`(abs)，`$C112` STA `$04BF`(abs)

外部依赖：$E850, $E85C, $F2D7


## 主状态 9：双方对白及控制回调

### 子状态 0 / `$C124`

等待双队列完成；请求第一武将肖像

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C127` BCC→`$C139`

绝对地址写入：`$C129` INC `$04A9`(abs)，`$C12F` STA `$0000`(abs)

外部依赖：$D299；farcall `$C134`→`$A030`（Y指定银行）

### 子状态 1 / `$C13A`

请求第二肖像并按04BD排队双方对白

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$C13A` INC `$04A9`(abs)

外部依赖：$D283；farcall `$C13F`→`$A033`（Y指定银行）

### 子状态 2 / `$C14A`

绘制双方动作参数；等待对白和确认，轮换actor并用04BE排队对方回应

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C162` BCC→`$C186`，`$C16C` BEQ→`$C186`

绝对地址写入：`$C150` STA `$0010`(aby)，`$C159` STA `$0010`(aby)，`$C16E` INC `$04A9`(abs)，`$C176` STA `$04AA`(abs)，`$C17D` STA `$042C`(abs)，`$C1E4` STA `$000A`(abs)，`$C1EC` STA `$0000`(abs)，`$C1F2` STA `$00A4`(abs)，`$C200` STA `$04BC`(abs)，`$C206` STA `$0000`(abs)，`$C20C` STA `$00A4`(abs)，`$C218` STA `$04BC`(abs)

外部依赖：$D13D, $D283, $D299；farcall `$C1F7`→`$A000`（Y指定银行）, `$C211`→`$A000`（Y指定银行）

### 子状态 3 / `$C187`

等待回应及确认，轮换actor；04BF>=2回state7/sub(04BF-1)，否则回state1并清04C3/C4

可能控制转移：`$C1BA`写`$04A9`=动态A寄存器；`$C1C2`写`$04A8`=7；`$C1D3`写`$04A8`=1；`$C1D8`写`$04A9`=0

条件分支：`$C19F` BCC→`$C1E1`，`$C1A9` BEQ→`$C1E1`，`$C1B8` BCC→`$C1D1`，`$C1CA` BNE→`$C1E1`

绝对地址写入：`$C18D` STA `$0010`(aby)，`$C196` STA `$0010`(aby)，`$C1B0` STA `$04AA`(abs)，`$C1BA` STA `$04A9`(abs)，`$C1BD` DEC `$04A9`(abs)，`$C1C2` STA `$04A8`(abs)，`$C1D3` STA `$04A8`(abs)，`$C1D8` STA `$04A9`(abs)，`$C1DB` STA `$04C3`(abs)，`$C1DE` STA `$04C4`(abs)，`$C1E4` STA `$000A`(abs)，`$C1EC` STA `$0000`(abs)，`$C1F2` STA `$00A4`(abs)，`$C200` STA `$04BC`(abs)，`$C206` STA `$0000`(abs)，`$C20C` STA `$00A4`(abs)，`$C218` STA `$04BC`(abs)

外部依赖：$D13D, $D299, $F28B；farcall `$C1F7`→`$A000`（Y指定银行）, `$C211`→`$A000`（Y指定银行）


## 主状态 10：初始化别名0

### 子状态 0 / `$B15A`

等待0087 bit7；从两条永久记录读取体力到04B1/B2，按武器ID分动画类；请求左侧精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B15D` BMI→`$B160`，`$B178` BCC→`$B165`，`$B190` BCC→`$B197`，`$B199` BCC→`$B1A0`

绝对地址写入：`$B160` INC `$04A9`(abs)，`$B16F` STA `$04B1`(abx)，`$B17C` STA `$0000`(abs)，`$B1A2` STA `$04AF`(abx)

外部依赖：$CDFD, $F2D7

### 子状态 1 / `$B1A6`

等待007E&4清零；请求第一组背景精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1AB` BNE→`$B1BA`

绝对地址写入：`$B1AF` STA `$0000`(abs)，`$B1B7` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 2 / `$B1BB`

等待007E&4清零；请求右侧武器精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1C0` BNE→`$B1D3`

绝对地址写入：`$B1C4` STA `$0000`(abs)，`$B1D0` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 3 / `$B1D4`

等待007E&4清零；请求第二组背景精灵，暂置actor=1

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1D9` BNE→`$B1ED`

绝对地址写入：`$B1DD` STA `$0000`(abs)，`$B1E5` INC `$04A9`(abs)，`$B1EA` STA `$04AA`(abs)

外部依赖：$CDFD

### 子状态 4 / `$B1EE`

排队双方名称，标记显示更新待处理

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B1F7` STA `$0003`(abs)，`$B202` STA `$0003`(abs)，`$B20D` STA `$0380`(abx)，`$B210` INC `$04A9`(abs)，`$B218` STA `$007E`(abs)

外部依赖：$CFA3, $F25F

### 子状态 5 / `$B21C`

D060写回双方体力并排队显示；设置007E bit2

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B221` STA `$0380`(abx)，`$B224` INC `$04A9`(abs)，`$B22C` STA `$007E`(abs)

外部依赖：$D060

### 子状态 6 / `$B230`

由体力、武力及武器/防具修正生成04B3/B4，随机比较选择actor；清04C0

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B29C` BCS→`$B295`，`$B2A7` BNE→`$B232`，`$B2B1` BCS→`$B2B4`

绝对地址写入：`$B23C` STA `$0010`(abs)，`$B247` STA `$0011`(abs)，`$B24F` STA `$0010`(abs)，`$B256` STA `$0010`(abs)，`$B263` STA `$0010`(abs)，`$B26A` STA `$0002`(abs)，`$B275` STA `$0001`(abs)，`$B27A` STA `$0002`(abs)，`$B27D` STA `$0004`(abs)，`$B282` STA `$0003`(abs)，`$B292` STA `$04B3`(abx)，`$B2A1` STA `$04BD`(abx)，`$B2B4` STX `$04AA`(abs)，`$B2B9` STA `$04C0`(abs)，`$B2BC` INC `$04A9`(abs)

外部依赖：$E87A, $EA7C, $F2D7

### 子状态 7 / `$B2E0`

按双方武器动画类读9项表设置04C5/C6，准备双边对白后去state9

可能控制转移：`$B33A`写`$04A8`=9；`$B33F`写`$04A9`=0

条件分支：无

绝对地址写入：`$B2E6` STA `$0000`(abs)，`$B2EF` STA `$0001`(abs)，`$B302` STA `$04C5`(abs)，`$B315` STA `$04C6`(abs)，`$B31A` STA `$04C3`(abs)，`$B31D` STA `$04C4`(abs)，`$B326` STA `$042C`(abs)，`$B32B` STA `$04BD`(abs)，`$B330` STA `$04BE`(abs)，`$B335` STA `$04BF`(abs)，`$B33A` STA `$04A8`(abs)，`$B33F` STA `$04A9`(abs)

外部依赖：无


## 主状态 11：初始化别名0

### 子状态 0 / `$B15A`

等待0087 bit7；从两条永久记录读取体力到04B1/B2，按武器ID分动画类；请求左侧精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B15D` BMI→`$B160`，`$B178` BCC→`$B165`，`$B190` BCC→`$B197`，`$B199` BCC→`$B1A0`

绝对地址写入：`$B160` INC `$04A9`(abs)，`$B16F` STA `$04B1`(abx)，`$B17C` STA `$0000`(abs)，`$B1A2` STA `$04AF`(abx)

外部依赖：$CDFD, $F2D7

### 子状态 1 / `$B1A6`

等待007E&4清零；请求第一组背景精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1AB` BNE→`$B1BA`

绝对地址写入：`$B1AF` STA `$0000`(abs)，`$B1B7` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 2 / `$B1BB`

等待007E&4清零；请求右侧武器精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1C0` BNE→`$B1D3`

绝对地址写入：`$B1C4` STA `$0000`(abs)，`$B1D0` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 3 / `$B1D4`

等待007E&4清零；请求第二组背景精灵，暂置actor=1

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1D9` BNE→`$B1ED`

绝对地址写入：`$B1DD` STA `$0000`(abs)，`$B1E5` INC `$04A9`(abs)，`$B1EA` STA `$04AA`(abs)

外部依赖：$CDFD

### 子状态 4 / `$B1EE`

排队双方名称，标记显示更新待处理

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B1F7` STA `$0003`(abs)，`$B202` STA `$0003`(abs)，`$B20D` STA `$0380`(abx)，`$B210` INC `$04A9`(abs)，`$B218` STA `$007E`(abs)

外部依赖：$CFA3, $F25F

### 子状态 5 / `$B21C`

D060写回双方体力并排队显示；设置007E bit2

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B221` STA `$0380`(abx)，`$B224` INC `$04A9`(abs)，`$B22C` STA `$007E`(abs)

外部依赖：$D060

### 子状态 6 / `$B230`

由体力、武力及武器/防具修正生成04B3/B4，随机比较选择actor；清04C0

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B29C` BCS→`$B295`，`$B2A7` BNE→`$B232`，`$B2B1` BCS→`$B2B4`

绝对地址写入：`$B23C` STA `$0010`(abs)，`$B247` STA `$0011`(abs)，`$B24F` STA `$0010`(abs)，`$B256` STA `$0010`(abs)，`$B263` STA `$0010`(abs)，`$B26A` STA `$0002`(abs)，`$B275` STA `$0001`(abs)，`$B27A` STA `$0002`(abs)，`$B27D` STA `$0004`(abs)，`$B282` STA `$0003`(abs)，`$B292` STA `$04B3`(abx)，`$B2A1` STA `$04BD`(abx)，`$B2B4` STX `$04AA`(abs)，`$B2B9` STA `$04C0`(abs)，`$B2BC` INC `$04A9`(abs)

外部依赖：$E87A, $EA7C, $F2D7

### 子状态 7 / `$B2E0`

按双方武器动画类读9项表设置04C5/C6，准备双边对白后去state9

可能控制转移：`$B33A`写`$04A8`=9；`$B33F`写`$04A9`=0

条件分支：无

绝对地址写入：`$B2E6` STA `$0000`(abs)，`$B2EF` STA `$0001`(abs)，`$B302` STA `$04C5`(abs)，`$B315` STA `$04C6`(abs)，`$B31A` STA `$04C3`(abs)，`$B31D` STA `$04C4`(abs)，`$B326` STA `$042C`(abs)，`$B32B` STA `$04BD`(abs)，`$B330` STA `$04BE`(abs)，`$B335` STA `$04BF`(abs)，`$B33A` STA `$04A8`(abs)，`$B33F` STA `$04A9`(abs)

外部依赖：无


## 主状态 12：初始化别名0

### 子状态 0 / `$B15A`

等待0087 bit7；从两条永久记录读取体力到04B1/B2，按武器ID分动画类；请求左侧精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B15D` BMI→`$B160`，`$B178` BCC→`$B165`，`$B190` BCC→`$B197`，`$B199` BCC→`$B1A0`

绝对地址写入：`$B160` INC `$04A9`(abs)，`$B16F` STA `$04B1`(abx)，`$B17C` STA `$0000`(abs)，`$B1A2` STA `$04AF`(abx)

外部依赖：$CDFD, $F2D7

### 子状态 1 / `$B1A6`

等待007E&4清零；请求第一组背景精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1AB` BNE→`$B1BA`

绝对地址写入：`$B1AF` STA `$0000`(abs)，`$B1B7` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 2 / `$B1BB`

等待007E&4清零；请求右侧武器精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1C0` BNE→`$B1D3`

绝对地址写入：`$B1C4` STA `$0000`(abs)，`$B1D0` INC `$04A9`(abs)

外部依赖：$CDFD

### 子状态 3 / `$B1D4`

等待007E&4清零；请求第二组背景精灵，暂置actor=1

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B1D9` BNE→`$B1ED`

绝对地址写入：`$B1DD` STA `$0000`(abs)，`$B1E5` INC `$04A9`(abs)，`$B1EA` STA `$04AA`(abs)

外部依赖：$CDFD

### 子状态 4 / `$B1EE`

排队双方名称，标记显示更新待处理

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B1F7` STA `$0003`(abs)，`$B202` STA `$0003`(abs)，`$B20D` STA `$0380`(abx)，`$B210` INC `$04A9`(abs)，`$B218` STA `$007E`(abs)

外部依赖：$CFA3, $F25F

### 子状态 5 / `$B21C`

D060写回双方体力并排队显示；设置007E bit2

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$B221` STA `$0380`(abx)，`$B224` INC `$04A9`(abs)，`$B22C` STA `$007E`(abs)

外部依赖：$D060

### 子状态 6 / `$B230`

由体力、武力及武器/防具修正生成04B3/B4，随机比较选择actor；清04C0

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$B29C` BCS→`$B295`，`$B2A7` BNE→`$B232`，`$B2B1` BCS→`$B2B4`

绝对地址写入：`$B23C` STA `$0010`(abs)，`$B247` STA `$0011`(abs)，`$B24F` STA `$0010`(abs)，`$B256` STA `$0010`(abs)，`$B263` STA `$0010`(abs)，`$B26A` STA `$0002`(abs)，`$B275` STA `$0001`(abs)，`$B27A` STA `$0002`(abs)，`$B27D` STA `$0004`(abs)，`$B282` STA `$0003`(abs)，`$B292` STA `$04B3`(abx)，`$B2A1` STA `$04BD`(abx)，`$B2B4` STX `$04AA`(abs)，`$B2B9` STA `$04C0`(abs)，`$B2BC` INC `$04A9`(abs)

外部依赖：$E87A, $EA7C, $F2D7

### 子状态 7 / `$B2E0`

按双方武器动画类读9项表设置04C5/C6，准备双边对白后去state9

可能控制转移：`$B33A`写`$04A8`=9；`$B33F`写`$04A9`=0

条件分支：无

绝对地址写入：`$B2E6` STA `$0000`(abs)，`$B2EF` STA `$0001`(abs)，`$B302` STA `$04C5`(abs)，`$B315` STA `$04C6`(abs)，`$B31A` STA `$04C3`(abs)，`$B31D` STA `$04C4`(abs)，`$B326` STA `$042C`(abs)，`$B32B` STA `$04BD`(abs)，`$B330` STA `$04BE`(abs)，`$B335` STA `$04BF`(abs)，`$B33A` STA `$04A8`(abs)，`$B33F` STA `$04A9`(abs)

外部依赖：无


## 主状态 13：零体力表现

### 子状态 0 / `$C22A`

准备零体力姿势/调色与当前方精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C24A` BEQ→`$C253`

绝对地址写入：`$C234` STA `$00CC`(abs)，`$C237` STA `$00D4`(abs)，`$C23A` STA `$00DC`(abs)，`$C23D` INC `$04A9`(abs)，`$C242` STA `$0000`(abs)，`$C24E` STA `$0000`(abs)

外部依赖：$CDFD, $E57F, $E683

### 子状态 1 / `$C256`

设置表现计时及双方位置

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C27D` BEQ→`$C28B`

绝对地址写入：`$C258` STA `$00C6`(abs)，`$C25B` STA `$00CE`(abs)，`$C25E` STA `$00D6`(abs)，`$C263` STA `$04B8`(abs)，`$C268` STA `$04BA`(abs)，`$C26B` INC `$04A9`(abs)，`$C270` STA `$04BB`(abs)，`$C275` STA `$0000`(abs)，`$C281` STA `$04BB`(abs)，`$C286` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 2 / `$C28E`

04B8循环到指定帧后排队消息26

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C29B` BNE→`$C2CC`，`$C2D2` BEQ→`$C2DD`

绝对地址写入：`$C28E` INC `$04B8`(abs)，`$C2A2` INC `$04A9`(abs)，`$C2CC` STA `$0010`(abs)，`$C2DA` STA `$0010`(abs)，`$C2E3` STA `$0002`(abs)

外部依赖：$CEA5, $F28B

### 子状态 3 / `$C2AA`

继续绘制；对白完成及确认后去state14，清04C0

可能控制转移：`$C2C0`写`$04A8`=14；`$C2C5`写`$04A9`=0

条件分支：`$C2B2` BCC→`$C2CB`，`$C2BC` BEQ→`$C2CB`，`$C2D2` BEQ→`$C2DD`

绝对地址写入：`$C2C0` STA `$04A8`(abs)，`$C2C5` STA `$04A9`(abs)，`$C2C8` STA `$04C0`(abs)，`$C2CC` STA `$0010`(abs)，`$C2DA` STA `$0010`(abs)，`$C2E3` STA `$0002`(abs)

外部依赖：$CEA5, $D13D, $D299


## 主状态 14：结果与装备奖励、回战斗

### 子状态 0 / `$C30E`

将双方ID保存到0514/0516；任一结果2去sub2，否则请求淡出并到sub1

可能控制转移：`$C337`写`$04A9`=2

条件分支：`$C321` BEQ→`$C332`，`$C32A` BEQ→`$C332`

绝对地址写入：`$C311` STA `$0514`(abs)，`$C317` STA `$0516`(abs)，`$C32C` INC `$04A9`(abs)，`$C332` STY `$04BD`(abs)，`$C337` STA `$04A9`(abs)

外部依赖：$ECEE

### 子状态 1 / `$C33B`

等待0087 bit7；battle0500=11/sub0，global7A=3，恢复050F控制代码并调用ECBF

可能控制转移：`$C356`写`$007A`=3

条件分支：`$C33E` BPL→`$C35C`，`$C34F` BEQ→`$C354`

绝对地址写入：`$C342` STA `$0500`(abs)，`$C347` STA `$0501`(abs)，`$C351` STA `$6F44`(abs)，`$C356` STA `$007A`(abs)

外部依赖：$ECBF

### 子状态 2 / `$C35D`

结果2对应武将的特殊ID/事件标志奖励分支，可改变胜方武器/防具并排队对白，或直接请求淡出

可能控制转移：`$C3A6`写`$04A9`=1

条件分支：`$C365` BNE→`$C36A`，`$C36C` BNE→`$C371`，`$C373` BNE→`$C378`，`$C37A` BNE→`$C37F`，`$C384` BNE→`$C3A4`，`$C395` BNE→`$C39A`，`$C3A2` BCC→`$C38B`，`$C3B1` BCS→`$C3A4`，`$C3D4` BCS→`$C3A4`，`$C3EA` BCS→`$C3A4`

绝对地址写入：`$C388` STA `$0010`(abs)，`$C39A` INC `$0010`(abs)，`$C3A6` STA `$04A9`(abs)，`$C3B5` STA `$0010`(abs)，`$C3BA` STA `$0011`(abs)，`$C3D8` STA `$0010`(abs)，`$C3DD` STA `$0011`(abs)，`$C3F1` STA `$6FE1`(abs)，`$C3F6` STA `$0010`(abs)，`$C3FB` STA `$0011`(abs)，`$C403` STA `$0010`(abs)，`$C408` STA `$0011`(abs)，`$C414` STA `$042C`(abs)，`$C425` INC `$04A9`(abs)，`$C437` STA `$042C`(abs)，`$C447` INC `$04A9`(abs)

外部依赖：$E862, $F28B, $F2D7, $F368

### 子状态 3 / `$C44F`

等待奖励对白及确认；请求淡出回sub1

可能控制转移：`$C460`写`$04A9`=1

条件分支：`$C452` BCC→`$C463`，`$C45C` BEQ→`$C463`

绝对地址写入：`$C460` STA `$04A9`(abs)

外部依赖：$D13D, $D299


## 主状态 15：结果淡出、回普通攻击场景

### 子状态 0 / `$C46E`

保存双方ID到0514/0516，推进并请求淡出

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：无

绝对地址写入：`$C471` STA `$0514`(abs)，`$C477` STA `$0516`(abs)，`$C47A` INC `$04A9`(abs)

外部依赖：$ECEE

### 子状态 1 / `$C480`

等待0087 bit7；global7A=5，恢复050F控制代码并调用ECBF（回普通攻击场景）

可能控制转移：`$C491`写`$007A`=5

条件分支：`$C483` BPL→`$C497`，`$C48A` BEQ→`$C48F`

绝对地址写入：`$C48C` STA `$6F44`(abs)，`$C491` STA `$007A`(abs)

外部依赖：$ECBF


## 主状态 16：动作类别0移动表现

### 子状态 0 / `$C4AC`

请求行动方起始精灵并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C4B7` BEQ→`$C4BE`

绝对地址写入：`$C4AC` INC `$04A9`(abs)，`$C4B1` STA `$0000`(abs)，`$C4BB` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 1 / `$C4C3`

初始化04B8/04BB位置并请求武器精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C4D8` BEQ→`$C4E4`

绝对地址写入：`$C4C5` STA `$04B8`(abs)，`$C4C8` INC `$04A9`(abs)，`$C4CD` STA `$04BB`(abs)，`$C4D2` STA `$0000`(abs)，`$C4DC` STA `$04BB`(abs)，`$C4E1` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 2 / `$C4E9`

更新横坐标直到接触阈值；等待精灵工作后推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C4EC` BEQ→`$C4F8`，`$C4F3` BEQ→`$C513`，`$C4FD` BEQ→`$C513`，`$C505` BEQ→`$C50D`，`$C519` BEQ→`$C525`

绝对地址写入：`$C502` STA `$0011`(abs)，`$C507` DEC `$04BB`(abs)，`$C50D` INC `$04BB`(abs)，`$C513` INC `$04A9`(abs)，`$C51D` STA `$0000`(abs)，`$C527` STA `$0000`(abs)，`$C531` STA `$03B7`(abs)，`$C536` STA `$03B8`(abs)，`$C53B` STA `$03B9`(abs)，`$C546` STA `$03BA`(abs)，`$C54D` STA `$03BB`(abs)，`$C552` STA `$03BC`(abs)

外部依赖：$CDFD, $CEE1

### 子状态 3 / `$C55A`

设置接触姿势/调色及计时后推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C58C` BEQ→`$C595`

绝对地址写入：`$C55C` STA `$00C7`(abs)，`$C55F` STA `$00CF`(abs)，`$C562` STA `$00D7`(abs)，`$C567` STA `$00C8`(abs)，`$C56A` STA `$00D0`(abs)，`$C56D` STA `$00D8`(abs)，`$C572` STA `$04B8`(abs)，`$C577` STA `$04B9`(abs)，`$C57C` STA `$04BA`(abs)，`$C57F` INC `$04A9`(abs)，`$C584` STA `$0000`(abs)，`$C590` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 4 / `$C598`

设置对侧姿势/调色并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C5B4` BEQ→`$C5C4`

绝对地址写入：`$C59A` STA `$00CC`(abs)，`$C59D` STA `$00D4`(abs)，`$C5A0` STA `$00DC`(abs)，`$C5A3` INC `$04A9`(abs)，`$C5AF` STA `$0001`(abs)，`$C5B8` STA `$0000`(abs)，`$C5C6` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 5 / `$C5D2`

按04B8计时演示攻击帧及音效；指定帧后请求精灵并写03B7..03BC

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C5EC` BNE→`$C622`，`$C5F9` BNE→`$C600`，`$C62A` BNE→`$C636`，`$C62F` BEQ→`$C636`，`$C639` BEQ→`$C644`，`$C660` BNE→`$C66A`

绝对地址写入：`$C5DB` STA `$0012`(abs)，`$C5DE` INC `$04B8`(abs)，`$C5EE` INC `$04A9`(abs)，`$C5F3` STA `$0000`(abs)，`$C5FD` STA `$0000`(abs)，`$C607` STA `$03B7`(abs)，`$C60C` STA `$03B8`(abs)，`$C611` STA `$03B9`(abs)，`$C616` STA `$03BA`(abs)，`$C619` STA `$03BB`(abs)，`$C61E` STA `$03BC`(abs)，`$C624` STA `$0010`(abs)，`$C627` STA `$0011`(abs)，`$C641` STA `$0010`(abs)，`$C64A` STA `$0002`(abs)，`$C664` STA `$0010`(abs)

外部依赖：$CDFD, $CEA5, $D235, $E693

### 子状态 6 / `$C66B`

去state19/sub0归位，请求归位精灵

可能控制转移：`$C66D`写`$04A8`=19；`$C672`写`$04A9`=0

条件分支：`$C67D` BEQ→`$C684`

绝对地址写入：`$C66D` STA `$04A8`(abs)，`$C672` STA `$04A9`(abs)，`$C677` STA `$0000`(abs)，`$C681` STA `$0000`(abs)

外部依赖：$CDFD


## 主状态 17：动作类别2移动表现

### 子状态 0 / `$C69F`

请求行动方起始精灵并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C6AA` BEQ→`$C6B1`

绝对地址写入：`$C69F` INC `$04A9`(abs)，`$C6A4` STA `$0000`(abs)，`$C6AE` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 1 / `$C6B6`

初始化位置及计时

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C6CB` BEQ→`$C6D7`

绝对地址写入：`$C6B8` STA `$04B8`(abs)，`$C6BB` INC `$04A9`(abs)，`$C6C0` STA `$04BB`(abs)，`$C6C5` STA `$0000`(abs)，`$C6CF` STA `$04BB`(abs)，`$C6D4` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 2 / `$C6DC`

按方向移动到接触阈值

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C6DF` BEQ→`$C6EB`，`$C6E6` BNE→`$C719`，`$C6F0` BNE→`$C719`，`$C703` BEQ→`$C70F`，`$C71F` BEQ→`$C727`

绝对地址写入：`$C6F4` STA `$00CC`(abs)，`$C6F7` STA `$00D4`(abs)，`$C6FA` STA `$00DC`(abs)，`$C6FD` INC `$04A9`(abs)，`$C707` STA `$0000`(abs)，`$C711` STA `$0000`(abs)，`$C71C` STA `$0011`(abs)，`$C721` DEC `$04BB`(abs)，`$C727` INC `$04BB`(abs)

外部依赖：$CDFD, $CEE1

### 子状态 3 / `$C72D`

设置类别2动作参数/计时并请求精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C73E` BEQ→`$C74B`，`$C767` BEQ→`$C770`

绝对地址写入：`$C72F` STA `$00C9`(abs)，`$C732` STA `$00D1`(abs)，`$C735` STA `$00D9`(abs)，`$C742` STA `$00C6`(abs)，`$C745` STA `$00CE`(abs)，`$C748` STA `$00D6`(abs)，`$C74D` STA `$04B8`(abs)，`$C752` STA `$04B9`(abs)，`$C757` STA `$04BA`(abs)，`$C75A` INC `$04A9`(abs)，`$C75F` STA `$0000`(abs)，`$C76B` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 4 / `$C773`

持续帧计时和精灵/音效请求

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C78B` BNE→`$C7B3`，`$C79A` BNE→`$C7B3`，`$C7A7` BNE→`$C7AE`，`$C7B8` BNE→`$C7C4`，`$C7BD` BEQ→`$C7C4`，`$C7C7` BNE→`$C7D2`

绝对地址写入：`$C77B` STA `$0012`(abs)，`$C77E` INC `$04B8`(abs)，`$C78F` STA `$04B8`(abs)，`$C792` INC `$04B9`(abs)，`$C79C` INC `$04A9`(abs)，`$C7A1` STA `$0000`(abs)，`$C7AB` STA `$0000`(abs)，`$C7B3` STA `$0010`(abs)，`$C7CF` STA `$0010`(abs)，`$C7D4` STA `$0002`(abs)，`$C7E6` STA `$0002`(abs)，`$C7F8` STA `$0011`(abs)

外部依赖：$CDFD, $CEA5, $E609

### 子状态 5 / `$C809`

初始化后半段计时/调色并请求精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C826` BNE→`$C833`，`$C83E` BNE→`$C845`

绝对地址写入：`$C80B` STA `$04B8`(abs)，`$C810` STA `$04BA`(abs)，`$C815` STA `$00C6`(abs)，`$C818` STA `$00CE`(abs)，`$C81B` STA `$00D6`(abs)，`$C82A` STA `$00C9`(abs)，`$C82D` STA `$00D1`(abs)，`$C830` STA `$00D9`(abs)，`$C833` INC `$04A9`(abs)，`$C838` STA `$0000`(abs)，`$C842` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 6 / `$C84A`

设置对侧姿势后推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C866` BEQ→`$C876`

绝对地址写入：`$C84C` STA `$00CC`(abs)，`$C84F` STA `$00D4`(abs)，`$C852` STA `$00DC`(abs)，`$C855` INC `$04A9`(abs)，`$C861` STA `$0001`(abs)，`$C86A` STA `$0000`(abs)，`$C878` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 7 / `$C884`

计时完成后去state19/sub0归位；否则演示后半段精灵/音效

可能控制转移：`$C8A4`写`$04A8`=19；`$C8A9`写`$04A9`=0

条件分支：`$C89C` BCC→`$C8AF`，`$C8A0` BCC→`$C8AD`，`$C8B7` BNE→`$C8C3`，`$C8BC` BEQ→`$C8C3`，`$C8C6` BNE→`$C8D1`，`$C8E3` BNE→`$C8EA`，`$C91C` BEQ→`$C930`，`$C923` BNE→`$C930`，`$C935` BNE→`$C948`

绝对地址写入：`$C88C` STA `$0012`(abs)，`$C88F` INC `$04B8`(abs)，`$C8A4` STA `$04A8`(abs)，`$C8A9` STA `$04A9`(abs)，`$C8AF` STA `$0010`(abs)，`$C8B2` STA `$0011`(abs)，`$C8CE` STA `$0010`(abs)，`$C8D3` STA `$0002`(abs)，`$C8D8` STA `$0001`(abs)，`$C8E7` STA `$0001`(abs)，`$C8FA` STA `$0002`(abs)，`$C903` STA `$0001`(abs)，`$C927` STA `$00C9`(abs)，`$C92A` STA `$00D1`(abs)，`$C92D` STA `$00D9`(abs)，`$C942` STA `$0010`(abs)

外部依赖：$CEA5, $D235, $E609


## 主状态 18：动作类别6移动表现

### 子状态 0 / `$C95F`

请求行动方起始精灵并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C96A` BNE→`$C971`

绝对地址写入：`$C95F` INC `$04A9`(abs)，`$C964` STA `$0000`(abs)，`$C96E` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 1 / `$C976`

初始化位置及计时

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C98B` BNE→`$C997`

绝对地址写入：`$C978` STA `$04B8`(abs)，`$C97B` INC `$04A9`(abs)，`$C980` STA `$04BB`(abs)，`$C985` STA `$0000`(abs)，`$C98F` STA `$04BB`(abs)，`$C994` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 2 / `$C99C`

按方向移动到接触阈值

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$C99F` BEQ→`$C9AB`，`$C9A6` BNE→`$C9D9`，`$C9B0` BNE→`$C9D9`，`$C9C3` BEQ→`$C9CF`，`$C9DF` BEQ→`$C9E7`

绝对地址写入：`$C9B4` STA `$00CC`(abs)，`$C9B7` STA `$00D4`(abs)，`$C9BA` STA `$00DC`(abs)，`$C9BD` INC `$04A9`(abs)，`$C9C7` STA `$0000`(abs)，`$C9D1` STA `$0000`(abs)，`$C9DC` STA `$0011`(abs)，`$C9E1` DEC `$04BB`(abs)，`$C9E7` INC `$04BB`(abs)

外部依赖：$CDFD, $CEE1

### 子状态 3 / `$C9ED`

类别6接触动画和帧计时

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CA44` BEQ→`$CA4D`

绝对地址写入：`$C9EF` STA `$04BA`(abs)，`$C9F4` STA `$00BE`(abs)，`$C9F7` STA `$00C6`(abs)，`$C9FA` STA `$00CE`(abs)，`$C9FD` STA `$00D6`(abs)，`$CA02` STA `$00BF`(abs)，`$CA05` STA `$00C7`(abs)，`$CA08` STA `$00CF`(abs)，`$CA0B` STA `$00D7`(abs)，`$CA10` STA `$00C0`(abs)，`$CA13` STA `$00C8`(abs)，`$CA16` STA `$00D0`(abs)，`$CA19` STA `$00D8`(abs)，`$CA1E` STA `$00C1`(abs)，`$CA21` STA `$00C9`(abs)，`$CA24` STA `$00D1`(abs)，`$CA27` STA `$00D9`(abs)，`$CA2C` STA `$04B8`(abs)，`$CA2F` STA `$04B9`(abs)，`$CA32` INC `$04A9`(abs)，`$CA3C` STA `$0000`(abs)，`$CA48` STA `$0000`(abs)

外部依赖：$CDFD, $E609

### 子状态 4 / `$CA50`

类别6连续动画及声音/精灵请求

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CA5C` BEQ→`$CA7A`，`$CA6E` BNE→`$CA75`，`$CA80` BNE→`$CA8B`

绝对地址写入：`$CA50` INC `$04B8`(abs)，`$CA60` STA `$04B8`(abs)，`$CA63` INC `$04A9`(abs)，`$CA68` STA `$0000`(abs)，`$CA72` STA `$0000`(abs)，`$CA7A` STA `$0010`(abs)，`$CA88` STA `$0010`(abs)，`$CA8D` STA `$0002`(abs)，`$CAA0` STA `$0002`(abs)，`$CAA6` STA `$0001`(abs)

外部依赖：$CDFD, $CEA5

### 子状态 5 / `$CAB8`

动作计时继续并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CAC8` BNE→`$CACF`

绝对地址写入：`$CABA` STA `$04B8`(abs)，`$CABD` INC `$04A9`(abs)，`$CAC2` STA `$0000`(abs)，`$CACC` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 6 / `$CAD4`

完成动作表现并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CAF0` BEQ→`$CB00`

绝对地址写入：`$CAD6` STA `$00CC`(abs)，`$CAD9` STA `$00D4`(abs)，`$CADC` STA `$00DC`(abs)，`$CADF` INC `$04A9`(abs)，`$CAEB` STA `$0001`(abs)，`$CAF4` STA `$0000`(abs)，`$CB02` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 7 / `$CB0E`

准备归位state19及精灵位置

可能控制转移：`$CB2C`写`$04A8`=19；`$CB31`写`$04A9`=0

条件分支：`$CB28` BNE→`$CB35`，`$CB37` BNE→`$CB45`，`$CB3C` BEQ→`$CB45`，`$CB47` BCC→`$CB4B`，`$CB54` BNE→`$CB5F`，`$CB93` BNE→`$CB9D`

绝对地址写入：`$CB17` STA `$0012`(abs)，`$CB1A` INC `$04B8`(abs)，`$CB2C` STA `$04A8`(abs)，`$CB31` STA `$04A9`(abs)，`$CB4B` STA `$0010`(abs)，`$CB4E` STA `$0011`(abs)，`$CB5C` STA `$0010`(abs)，`$CB65` STA `$0002`(abs)，`$CB6E` STA `$0001`(abs)，`$CB82` STA `$0002`(abs)，`$CB97` STA `$0010`(abs)

外部依赖：$CEA5, $D235, $E609


## 主状态 19：移动归位与恢复保存状态

### 子状态 0 / `$CBAA`

设置归位精灵/调色，初始化04B8并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CBEC` BEQ→`$CBFC`

绝对地址写入：`$CBAC` STA `$00C6`(abs)，`$CBAF` STA `$00CE`(abs)，`$CBB2` STA `$00D6`(abs)，`$CBB7` STA `$00C7`(abs)，`$CBBA` STA `$00CF`(abs)，`$CBBD` STA `$00D7`(abs)，`$CBC2` STA `$00C8`(abs)，`$CBC5` STA `$00D0`(abs)，`$CBC8` STA `$00D8`(abs)，`$CBCD` STA `$00C9`(abs)，`$CBD0` STA `$00D1`(abs)，`$CBD3` STA `$00D9`(abs)，`$CBD8` STA `$04B8`(abs)，`$CBDB` INC `$04A9`(abs)，`$CBE7` STA `$0001`(abs)，`$CBF0` STA `$0000`(abs)，`$CBFE` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 1 / `$CC0A`

朝本方起点移动，04BB达18或A8才推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CC0D` BEQ→`$CC19`，`$CC14` BNE→`$CC49`，`$CC1E` BNE→`$CC49`，`$CC30` BEQ→`$CC3C`，`$CC54` BEQ→`$CC5C`

绝对地址写入：`$CC20` INC `$04A9`(abs)，`$CC25` STA `$0000`(abs)，`$CC2A` STA `$0001`(abs)，`$CC34` STA `$0000`(abs)，`$CC39` STA `$0001`(abs)，`$CC4E` STA `$0011`(abs)，`$CC56` INC `$04BB`(abs)，`$CC5C` DEC `$04BB`(abs)

外部依赖：$CDFD, $CEE1

### 子状态 2 / `$CC62`

从04BD/04BE恢复主/子state，请求对侧武器精灵

可能控制转移：`$CC65`写`$04A8`=读取$04BD；`$CC6B`写`$04A9`=读取$04BE

条件分支：`$CC71` BEQ→`$CC7D`

绝对地址写入：`$CC65` STA `$04A8`(abs)，`$CC6B` STA `$04A9`(abs)，`$CC75` STA `$0000`(abs)，`$CC7F` STA `$0000`(abs)

外部依赖：$CDFD


## 主状态 20：向外移动及恢复状态

### 子状态 0 / `$CC93`

请求行动方精灵并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CC9E` BNE→`$CCA5`

绝对地址写入：`$CC93` INC `$04A9`(abs)，`$CC98` STA `$0000`(abs)，`$CCA2` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 1 / `$CCAA`

初始化04B8及04BB，画外移精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CCBF` BNE→`$CCCB`

绝对地址写入：`$CCAC` STA `$04B8`(abs)，`$CCAF` INC `$04A9`(abs)，`$CCB4` STA `$04BB`(abs)，`$CCB9` STA `$0000`(abs)，`$CCC3` STA `$04BB`(abs)，`$CCC8` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 2 / `$CCD0`

位置向外移动；达08或B8恢复04BD/04BE；按OAM字节计数隐藏越界精灵

可能控制转移：`$CCE9`写`$04A8`=读取$04BD；`$CCEF`写`$04A9`=读取$04BE

条件分支：`$CCD3` BEQ→`$CCDF`，`$CCDA` BNE→`$CCF3`，`$CCE4` BNE→`$CCF3`，`$CCFE` BEQ→`$CD06`，`$CD13` BEQ→`$CD3B`，`$CD1B` BEQ→`$CD25`，`$CD20` BMI→`$CD33`，`$CD2A` BCS→`$CD33`，`$CD2C` BPL→`$CD33`

绝对地址写入：`$CCE9` STA `$04A8`(abs)，`$CCEF` STA `$04A9`(abs)，`$CCF8` STA `$0011`(abs)，`$CD00` INC `$04BB`(abs)，`$CD06` DEC `$04BB`(abs)，`$CD30` STA `$0200`(aby)

外部依赖：$CEE1


## 主状态 21：向内移动及恢复状态

### 子状态 0 / `$CD48`

请求行动方精灵并推进

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CD53` BNE→`$CD5A`

绝对地址写入：`$CD48` INC `$04A9`(abs)，`$CD4D` STA `$0000`(abs)，`$CD57` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 1 / `$CD5F`

初始化04B8及04BB，画内移精灵

可能控制转移：没有直接主/子状态STA；可能INC/DEC子状态或调用外部依赖。

条件分支：`$CD74` BNE→`$CD80`

绝对地址写入：`$CD61` STA `$04B8`(abs)，`$CD64` INC `$04A9`(abs)，`$CD69` STA `$04BB`(abs)，`$CD6E` STA `$0000`(abs)，`$CD78` STA `$04BB`(abs)，`$CD7D` STA `$0000`(abs)

外部依赖：$CDFD

### 子状态 2 / `$CD85`

位置向内移动；达B8或08恢复04BD/04BE；按OAM字节计数隐藏越界精灵

可能控制转移：`$CD9E`写`$04A8`=读取$04BD；`$CDA4`写`$04A9`=读取$04BE

条件分支：`$CD88` BEQ→`$CD94`，`$CD8F` BNE→`$CDA8`，`$CD99` BNE→`$CDA8`，`$CDB1` BNE→`$CDB9`，`$CDC6` BEQ→`$CDFC`，`$CDCE` BEQ→`$CDDF`，`$CDD5` BCC→`$CDF4`，`$CDDA` BMI→`$CDEF`，`$CDE4` BCC→`$CDEA`，`$CDE8` BCC→`$CDF4`，`$CDED` BMI→`$CDF4`

绝对地址写入：`$CD9E` STA `$04A8`(abs)，`$CDA4` STA `$04A9`(abs)，`$CDAB` STA `$0011`(abs)，`$CDB3` INC `$04BB`(abs)，`$CDB9` DEC `$04BB`(abs)，`$CDF1` STA `$0200`(aby)

外部依赖：$CEE1

