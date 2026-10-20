# 战后撤退、驻城与在野规则

本轮恢复 `bank8 $BC46` 的三个AI分配分支，以及战场主状态13/14的全部七个子阶段。实现位于 `source/recovered/postbattle.py`，是直接的 Python 玩法代码，不执行原ROM指令。原ROM保持只读，SHA256固定为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## API 与边界

```python
from source.recovered.postbattle import PostbattleData, PostbattleEngine, process_ai_officers

data = PostbattleData.from_rom(rom_bytes)  # 只读取邻接表和RNG排列两段数据
result = process_ai_officers(memory, mode, data=data)
engine = PostbattleEngine(memory, data=data)
frame = engine.step(text_ready=True, cursor_index=0)
```

`memory` 是CPU地址空间、64KiB数组或已有mapper Bus。`mode` 必须为0/1/2；双方君主编码的可证域为0..6。

`PostbattleEngine` 只处理 `$0500=13/14,$0501=0..6`。文字/动画是否完成由明确的 `text_ready` 输入提供；目的地/武将菜单位置由控制服务给出 `cursor_index`。缺失必要输入会抛出 `MissingPostbattleInput`。输出 `events` 请求绘制/消息队列，不把请求当作已完成渲染。

root集成可将旧收尾函数的依赖替换为：

```python
ai_officer_processing = lambda memory, mode: process_ai_officers(memory, mode, data=data)
```

这消除了BC46分配规则的原ROM执行依赖；6502 flags/stack、PPU、文字队列编码仍不属于这个高层API的承诺范围。

## 可证玩法

| 分支 | 直接行为 |
|---|---|
|AI mode0|先从当前城名册offset17填至26，再补同势力/中立邻城已有名册的空位，再使用空邻城，最后处理溢出武将。|
|AI mode1|失败守城方分配到邻城；不覆盖当前城名册。|
|AI mode2|失败出征方先使用来源城 `$052A` 的空位，再走邻城分配。|
|主13|选择撤退目的城和需要转移的武将；没有可用目的地时走自动在野/君主撤出分支。|
|主14|剩余武将不超过10人时全部入当前城；超过10人先挑出武将分配到其他城/在野，再将余下名单入当前城。|
|选项30|转为在野：清record.byte11低2位、随机选择8个邻接槽之一作为record.byte5；负值/FF回退当前城。UI禁止选择本方君主。|

分配到城市仅写城市名册并解除战斗/俘虏数组引用，不擅自把武将status设置为2，也不修改忠诚、势力君主表或装备。中立城接收时，AI空城分支把owner整byte写为君主ID；人工选城分支保留owner高4位。这两个实际行为没有合并。

`remove_battle_reference` 只删除第一个active匹配，若没有则删除第一个俘虏数组匹配；保留原程序的重复ID别名行为。它不会把所有同ID条目一次删除。`remove_inactive_unit_slot` 则对应死亡后的bank9 D6CD，清六个active数组、6FA1 slot与第一个匹配的四byte攻击缓存，操作范围与前者不同。

### 正式原文与现代中文

正式选项文字为 **「ざいや」**。现代中文功能说明为“转为在野/解除归属”。这不是原UI中的“招降”或“处刑”选项。

* [原ROM光标与文字](synthetic-ui/option30-cursor-fullframe-738bbeec98aa.png)：RAM `$0012=3`，`$042C[3]=30`。
* [完整光标帧3倍放大](synthetic-ui/option30-cursor-fullframe-x3-738bbeec98aa.png)：全256×240帧扩大为768×720，无裁切，菜单位于下栏右侧。
* [原字形放大](synthetic-ui/option30-glyph-zoom.png)：仅对原始像素做nearest-neighbor放大，首字浊点明确。
* [选项30确认正文](synthetic-ui/option30-confirmation-fullframe-7a61641ce1b6.png)：RAM `$0540=30`；原文字为「ざいやにかえすブショウをえらんでください」。
* 原消息DC为「どのクニに たいきゃくしますか」；主14超员消息DF为「このクニにはいるブショウが10にんをこえました ほかのクニへどうぞ」。这些文字的独立捕获位于 `../terrain/core-labels/`。D7是动态目的地列表，不称作固定处置动作名；DE是武将选择packet，不凭空补一个动作标题。

### 截图完整性核对

当前完整光标截图SHA256为 `738bbeec98aae9936f7feea2249ff8e417a69c94e1ab0eb27139f7516e3efcef`，对应core帧236与同名RAM；画面为曹操地图、下栏目的城列表、右下「ざいや」光标，底部曹操名。不是孙権资料页。放大字形逐像素等于此完整图crop(140,176,232,200)再nearest-neighbor×8。确认图core帧424与其放大图也逐像素一致。

上面的完整图使用内容hash命名，以避免浏览器同名资源缓存或路径映射混淆；原始无hash文件仍保留。完整配对、SHA、RAM状态与裁切检查见 [image-integrity.json](synthetic-ui/image-integrity.json)。若页面显示其他武将，应先核对实际img URL及响应hash；不能将该页面像素当作本帧的证据。

## status3 与原程序边界行为

`byte11 &3==3` 是移除/不可用编码，不能统一解释为“体力恰好为0”。

1. 战术伤害健康归0后，bank12 `$B60D` 设置低2=3；其后far bank8 A02A→bank9 `$D6CD` 清active officerID，所以正常此路径的死亡武将不再进入BDCD/D0E1的活动名单。
2. 主13无目的地分支 `$CDE6..CDEC` 将君主低2置3，其他名单成员置0并写当前城位置；此处不要求健康0。
3. AI溢出比较存在实际scratch别名：`$BD00` 前scratch02初始为君主ID；但一个非匹配武将被释放后，`$BD3E` 将02覆盖为 `(current_city*8)&FF`，此后比较的是这个行偏移值。后续匹配的非君主也会被OR3。验证中的明确合成例子officer88仍健康100而status变3；正常游玩是否自然出现该顺序尚未证明。
4. mode2来源城全满路径不清EADE留下的scratch04=`BD`，随后从6FA1[BD]取名单。源码保留该ROM异常；基于正常出征会腾出来源城名册空位的条件，其自然可达性未证明。未把它改成“合理”的从0开始。

清status到0的代码存在，不等于证明正常死亡可复活。正常健康0路径已先删除active引用；只有仍出现在活动/俘虏名单中的记录才会进入在野分配。没有把合成坏状态当作自然复活轨迹。

## 验证与复现

```sh
python3 scripts/analyze_postbattle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_postbattle.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --render-ui
.venv-trace/bin/python scripts/verify_postbattle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

`python3` 有Pillow；`.venv-trace` 有py65。`--render-ui` 使用已准备的完整Nestopia core。

最终矩阵9788病例全部通过：3个AI mode逐一512、高层名单/目的地/选择/接收/释放函数、14个状态阶段×64、32条人工连续分配链的1211帧、128次两方连续AI分配、512次active删除和status3特殊边界。32条人工链全部真正回到主15的父结算阶段。比较完整8KiB SRAM，以及每项声明的游戏状态/活动数组/俘虏/目的地/选中名单buffer；额外比对消息事件的ID及F283/F28B/F293队列入口。

人工状态机的CPU对照使用明确的UI服务边界：固定`text_ready`/菜单位置；drawing-only入口不执行绘图。所有改变游戏记录/城市/活动/俘虏数据的函数仍执行原ROM。高层API不声称复制CPU scratch、flags、bank寄存器、PPU与文字packet编码。

UI截图是 **明确的合成输入**：从自然 `attack-intro-7.state` 导入完整core，修改主13/sub1、处理方、当前城、一个单位sidebit、以及一个邻城owner/名册，以显示选择界面。全部输入补丁、按键/帧数和导入hash见 [provenance.json](synthetic-ui/provenance.json)。未修改ROM，未将这次捕获冒充自然败战。字段/算法的差分矩阵也标为合成边界输入。

[evidence.json](evidence.json) 给13个源码API入口、bank/CPU/file/rawbytes、1273个可达控制证据节点、记录写回与已确认原文；未分类静态边为0。[validation.json](validation.json) 保存逐函数计数、差异列表、32条连续链和AI顺序证据。静态图节点数不是Python动态分支覆盖率。
