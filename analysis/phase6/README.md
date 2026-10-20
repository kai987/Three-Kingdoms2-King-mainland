# 第六轮：城市归属、势力灭亡与全局／结局调度

本轮把城市归属事务、君主缺席与结束条件、固定银行全局／NMI控制接入[统一可读源码](../../source/README.md)。原ROM只读，原文件与重建ROM仍逐字节一致，SHA256为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。交付物是逆向复原的玩法规则和提升后的控制源码，不是原开发源码或已独立可玩的完整游戏。

[联合回执](verification.json)确认本轮主体 **18,194项实际原ROM CPU对照，0失败**，另有251项源模型拒绝检查。统一GameEngine入口另外完成55项检查；原Nestopia核心的三类受控回放保留了输入、准备字节、截图、RAM/SRAM、state及重复hash证据。CPU前缀、源模型检查、视频帧和文件一致性分别计数。

## 本轮确认的关键行为

- **城市变更必须保留具体写法。** 新增7个独立归属／名册事务，复查13个已发现玩法owner写点；`F8`、`F0`及整byte替换的高位效果不同。成功转属有删旧名册路径，不能再用忠诚函数代替。
- **失城、中立城和势力灭亡是不同条件。** 无继承人的FB事件及共同退场前缀只清leaderID；没有自动清全部owner、名册、驻城、controller或外交的统一交易。
- **两个结束判断不同。** 城市界面检查当前ruler是否占有全部30城；月轮还会在有效武将池少于30时提示全国统一不可能。后者不是城数，也不是本势力人数。
- **全局和NMI是两套分派。** `$007A&1F`有15个合法索引，`$0078&0F`有9个合法scene。结束控制有6个主模式、17个合法mode/sub组合；未恢复的硬件、图形和跨银行依赖继续明确报告。
- **原核心已走通受控统一结局入口。** 仅准备30个城市owner字节后，普通B/A输入由原代码生成评分75、选择mode1，经过global13进入global14／NMI8。此前征战与完整结局动画没有由这个fixture验证。

## 可读源码与统一接口

| 模块 | 已恢复内容 | 实际边界 |
|---|---|---|
| [city_ownership.py](../../source/recovered/city_ownership.py) | 7个新增直接事务及1个旧战后服务组合：占领、临战再安置、殖入、撤城、成功后单将转属、空城动作检查、单位退却 | 传入金额／基数、选择成功条件、AI预算／栈展开、BAE2政治响应、完整人事UI由上层负责 |
| [faction_lifecycle.py](../../source/recovered/faction_lifecycle.py) | leaderFF轮序、FB通知／真实ack后续、族灭／结束参数、30城判断、评分、名册展示缓冲、继续或复位；EndingControl | 不推断城市／外交整体清理；E46A显示初始化和真实NMI/reset外置 |
| [global_main_loop.py](../../source/recovered/global_main_loop.py) | 固定bank31的15个main索引、9个NMI callback索引、四种mapper协议、场景工作取消与NMI恢复／计数效果 | 合作调用窗口，不执行完整视频帧；缺失图形／音频／IRQ／banked helper明确停止 |
| [game_engine.py](../../source/recovered/game_engine.py) | 所有规则共用CPU地址空间；增加归属、势力、全局、NMI合作与ending入口 | 只绑定已证实的银行身份；没有original-ROM fallback或虚假完成显示 |

`GameEngine.city_ownership_rules()` 和 `faction_rules()` 返回共享内存的独立玩法算法。`tick_global(entry_banks=...)` 从E066执行到下一个E066或真实依赖；`tick_nmi_cooperation(entry_banks=...)` 从F862执行到F88D或依赖，前置硬件NMI栈、DMA及IRQ时序由caller负责。`tick_ending()`／NMI scene8的 `tick_scene()` 执行D693控制入口，仍不代替完整E46A初始化或NES帧。

全局桥接按**真实物理银行对＋CPU地址**识别函数：pair10/11 A000只接独立内政AI入口A00F；pair23/24 A01E只接EndingControl D693。原三字节JMP trampoline身份也核验。嵌套调用借用同一寄存器对象、实际SP及caller返回地址，`seed_return=False`，不会种入0200哨兵或覆盖无关栈内容。其他银行中的同址A000继续是外部依赖。

`nmi_bookkeeping_effects()` 只做F88D..F8AF的银行恢复／计数，不执行保存寄存器的pop或RTI。`cancel_scene_working_state()` 是原E4E9..E51C的RAM/OAM取消：0300/0304置FF表示取消旧工作，不表示已经把它画完。这些后缀不会在依赖发生后被自动调用来假推进。

## 城市归属和成员事务

| 原写入形式 | 代表路径 | 高位效果 |
|---|---|---|
| `(old&F8)\|ruler` | bank10 A90B、AC11、B354 | 保留高5位，替换低3位 |
| `(old&F8)\|7` | bank10 B429、旧删除BDFE | 保留高5位，中立化低3位 |
| `(old&F0)\|ruler` | 旧战后BBDD、退却BC90、旧分配D296 | 保留高4位，同时清bit3 |
| `byte0=ruler` | 旧分配BCD9 | 整字节替换 |
| `byte0=7` | 新BAE0、bank28 D181；旧C0D5/CC0F | 整字节中立化 |

成功后的单将转属 `$BA8D..BAE1` 实际追加目标名册、按新leader调整忠诚、删除旧城首个匹配项并压紧；旧城空时整byte写7，但武将状态／byte5及君主驻城在此段保留。新撤城保留word回绕、无最终目的资源封顶，返回AP成本而不自动消耗预算。临战再安置按原邻表顺序与容量判断；无去处时保留原放逐规则。单位退却清真实active数组与匹配缓存，slot0/10另写逃离跟踪052B/052C。

原查询／写入的同址别名、名册满时查FF走出10槽、首槽FF但后槽有人等效果均按机器行为保留。13个writer是**已发现并复查**的目录，不是完整ROM动态指针审计证明。完整范围、原寄存器输入与边界见[归属报告](ownership/README.md)及[原字节证据](ownership/evidence.json)。

## leaderFF、FB及族灭通知

无继承人的AI前缀 bank11 `$CA74..CA7E` 只写当前ruler的leaderID=FF和6F8B=FB。CA7F等待的值必须**恰好1**，不能把其他非负值当确认。桥接收到FB后排C3消息、进入sub12；原CB9D计时达到240次合作调用，由CBBF真正写1。sub11再接sub12需要480次调用，这些单位不是视频帧。

确认后 `$CA52` 调C98F：金米按原D105时机封顶，拥有的城可能交换首将；owner／controller／外交不在此段统一清理。高层服务止于CA58，后面的七君主外循环、D249与BEC7继续属于其他控制器。共同退场前缀C386的controller条件是 `(byte3&3)==3`，与AI的整个byte等于3不同。

月轮A041只按leaderID=FF跳过slot，不检查城市数或controller；跳过仍推进日历与月外交衰减。**全部七个leader都FF时，原代码继续循环，不返回。** 源模型只执行一个七slot周期，返回 `no_active_ruler_in_scan_period`，明确没有完成原循环。测试中40例是这种有界非返回前缀。

![原族灭通知fixture](runtime/messages/message-C3-zoom.png)

C3受控绘制的新行可读为曹操死亡、曹操一族灭亡；显示ID是明确准备的参数。文字不等同该原存档中真的死亡，更不能替owner／名册数据流补写。完整字段作用域见[势力报告](factions/README.md)。

## 有效武将池不足30的警告

bank25 `$A240..A295` 遍历237条武将：排除其他君主leaderID以及status低2位等于3的记录，剩余人数存0011。它包含status0/1/2、不查HP、城主或名册。少于30时排D5消息、0401=3；随后A186在0300/0304都FF并按A后跳原E000复位。

![原统一不可能提示](runtime/messages/message-D5-zoom.png)

清楚的新行是「もはや このニンズウでは」「ゼンコクトウイツは フカノウです」。这是武将池不足导致全国统一不可能的提示，不能叫“统一胜利”。父菜单残留行不计入转写。

## 30城统一、评分与结束场景

真实代码链如下，各地址的银行身份分开保留：

```text
bank27 A089 → bank28 DDBF：30城中 owner&7 == 当前6F03 的数量
数量恰好30 → city0400=15 → bank27 A075 → pair25/26 A01E → bank26 C435
C441评分／参数 → C606接受结果：global7A=13、0541=1/2/3
fixedE46A设置NMI78=8并初始化显示 → global7A=14
NMI FA53..FA85 → pair23/24 A01E → bank24 D693 ending controller
```

评分累计所有30城的治理byte11，以及每城全部10槽中非FF、非该leader的忠诚与人数；不按owner过滤，不查HP/status，不去重。忠诚和按word回绕，人数按byte回绕，零除及24位算术按原helper保留。最后分档只读评分0435的低byte：≥70→mode1、40..69→mode2、<40→mode3。人类无继承人的结束路径也进入global13，但为mode0。

原核心的统一fixture从 `analysis/runtime/city-commands.state` 开始，只把30个SRAM城市owner字节置为 `(old&F8)\|2`；包括两条值原本已经等于2的准备记录。RAM、ROM、显示ready及ack均不修改。正常B输入2帧＋空闲600帧后生成统一提示／评分；A输入2帧＋空闲600帧后进入结束scene，共1204帧。

![原统一提示](runtime/unification-ending/victory-summary.png)

此核心生成忠诚和4741、人数57、治理和3000。独立源码得三项83、43、100，`floor((83+43+100)/3)=75`，与原0435..0437一致。后续原代码选择mode1；日志记录global13→14及NMI8。

![原mode1结束画面](runtime/unification-ending/ending.png)

这条证据验证原代码从受控30城条件走到结局画面；没有重演此前30城征服、真实势力退场或完整结局动画／武将展示。完整准备字节与状态变化见[统一回放回执](runtime/unification-ending/validation.json)。

EndingControl的表范围为6个primary模式：0..3不分派0542，mode4有7个0542子状态，mode5有6个，共17组合。3张inline表保留原字节及紧接首handler的边界；[完整目录](factions/ending-controller.json)与[有界汇编](factions/ending-control.asm)可核验。mode0还按6F43区分A复位与恢复0400/0401=0472/0473、global1的继续分支，不恢复leader或城池。

## 全局与NMI控制的边界

主表 `$E07C..E099` 有15项，NMI表 `$F87B..F88C` 有9项；重复target仍按合法索引分开，不能称作15／9个不同函数。源模型在mask后超出已证明表域时拒绝，不让错误索引读取邻近数据。

| 原分派 | 作用／银行 |
|---|---|
| global7A=2 → E17D → pair10/11 A000 | 内政AI合作入口A00F |
| global7A=4 → E221 → pair8/9 A000 | 战场AI合作入口；与battle NMI控制不同 |
| NMI78=2 → F8EF → pair27/28 A000 | 城市界面 |
| NMI78=3/4 | pair12/13战斗、pair14/15普通攻击callback |
| NMI78=5 → pair23/24 A01B | 单挑B100 callback |
| NMI78=8 → pair23/24 A01E | 结束D693 callback |

新全局IR有1005条原指令，静态1005条逐字节核验，动态覆盖885条。四个mapper helpers的全部256个raw selector及栈／flags组合均有原CPU对照。严格PrgDataMemory遇到不支持的PPU／IRQ／音频／外部CPU函数会保留已发生副作用并报告dependency；验证端的原ROM helper只用于明确标记的oracle-assisted案例，不安装进源模型。

E05E是reset之后的有界入口，F800是需要真实硬件中断栈的NMI前缀；既没有宣称整个E000冷启动完成，也没有自动构造硬件栈。全表、跨银行handoff与诊断见[全局目录](global/state-catalog.json)、[全局汇编](global/global-control.asm)及[验证回执](global/validation.json)。

最终矩阵另加入274项NMI协议CPU对照：18项采用验证端明确的同步I/O契约执行前缀，256项用caller提供的保存寄存器／硬件中断栈帧检验F8AF后的恢复与RTI。它们分别验证前序和退出协议，不扩展 `tick_nmi_cooperation()` 的F862..F88D窗口，也不证明完整硬件NMI、IRQ时序或NES帧。

## 验证计数与作用域

| 矩阵 | 实际原CPU对照 | 单列检查／范围 |
|---|---:|---|
| [城市归属](ownership/validation.json) | 2,176 | 另3项源模型guard；全部SRAM＋声明的相关RAM／成本字段 |
| [势力／结束](factions/validation.json) | 9,699 | 9,631独立语义＋68 ending IR；全部SRAM／声明RAM，IR另比CPU／stack／mapper |
| [全局控制](global/validation.json) | 6,319 | 回执6,567项减去248非法索引source guard；包含有界前缀、helper、合作窗口与独立NMI协议检查 |
| **本轮主体合计** | **18,194，0失败** | **251项guard独立计数**，不是原CPU案例 |

Ending IR的68例覆盖全部17组合各4种fixture：65例返回，3例停在真正边界（mode0 reset、mode5/sub4 NMI、mode5/sub5 reset）；动态434/668。全局动态885/1005与静态表／字节完整性也分别记录。未动态执行的指令不声称逐条运行已验证，有界前缀不声称整路径完成。

[统一GameEngine回执](source-integration.json)的55项为：**53项原CPU对照**（30全局窗口、6嵌套ending、9 NMI窗口、4 bookkeeping、4归属字段），另1项原核心评分75一致检查、1项source bank guard。6个嵌套ending中3返回到真实caller地址FA88、3停在缺失renderer；无关栈字节保持一致。记录 `source_original_code_calls=0`，默认源接口没有原ROM执行器fallback。这55项另列，不并入18,194主体矩阵。

完整核心受控回放同样另列：

| 证据 | 核心帧／准备 | 重复一致的非空artifact |
|---|---|---:|
| [C3/D5/D8/D9消息](runtime/messages/evidence.json) | 4组，每组240帧；显式排消息与参数 | [20项](runtime/messages/repeat-validation.json) |
| [归属结算提交](runtime/ownership-commit/validation.json) | 63帧；只准备0500=15、0501=3、0514=0三RAM字节；原A输入 | [8项](runtime/ownership-commit/repeat-validation.json) |
| [统一→结束](runtime/unification-ending/validation.json) | 1204帧；只准备30个owner SRAM字节，原B/A输入 | [10项](runtime/unification-ending/repeat-validation.json) |

归属fixture验证city4 owner原1→2，并返回global2／NMI2；没有完成原战斗前序、分配、伤亡或补给阶段。消息D8/D9保留的是第一页／等待中的文字，不是完整结束流程。总38项重复artifact逐文件非空且hash一致，没有加进CPU数量，也不等同所有自然战役路径已经验收。

## 复现与保留材料

从工作区根目录执行，CPU验证使用已有py65环境：

```sh
.venv-trace/bin/python scripts/analyze_city_ownership.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_city_ownership.py
python3 scripts/analyze_faction_lifecycle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_faction_lifecycle.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_global_main_loop.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_global_main_loop.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase6_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/verify_phase6.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

原核心复现另依赖当前配置的 `.toolchain/nestopia/nestopia_libretro.dylib`、Python图像依赖与保留parent states：

```sh
python3 scripts/capture_faction_messages.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase6/runtime/messages-repeat
python3 scripts/capture_ownership_commit.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase6/runtime/ownership-commit-repeat
python3 scripts/capture_unification_ending.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase6/runtime/unification-ending-repeat
python3 scripts/verify_phase6.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

联合验证将ROM／重建文件、两份控制IR、dispatch原表、8段ownership／16段faction原字节、源文件与validator hashes、原core重复材料绑定。已有8组REA/Ghidra PRG银行对的load image仍逐组verified，保存在[REA目录](../rea/pairs)；它们是定位和辅助材料，不将候选伪C称作已验证原源码。初版错误的D8/D9参数尝试保留于exploratory，正式结论使用修正后的C386/C3DB参数布局与重复回放。

仍未恢复：完整人事／外交UI及成功条件、BAE2等后续政治响应、全部潜在动态owner写点、全局冷启动／主循环的全部外部helper、PPU／IRQ／音频时序、完整结局动画／credits及自然战役通关。现有模型会明确停在这些依赖；城市归属、势力字段、原CPU等价和原核心受控运行各自只证明上述已记录范围。
