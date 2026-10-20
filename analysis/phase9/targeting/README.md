# Phase9：玩家16项计略目标资格

`PlayerTacticTargeting` 独立恢复 bank12 AD80 完整地形前序、16项分派和所有实际资格分支到RTS，没有解释IR、原ROM fallback或自动确认。资格和施放成功概率分开；它是重构源码，不是原作者源码。

| ID | 正式名称 | 原入口 | 原玩家资格，C=1成立 | 玩家AP表报价 |
|---:|---|---|---|---:|
| 0 | 火計 | ADCC | 目标class0或2 | 6 |
| 1 | 陥穽 | ADD8 | 目标class0或4 | 5 |
| 2 | 虚兵 | ADD8 | 目标class0或4 | 4 |
| 3 | 要撃 | ADD8 | 目标class0或4 | 6 |
| 4 | 乱水 | ADE4 | 目标class3 | 7 |
| 5 | 火箭 | ADEE | 目标槽0或10 | 8 |
| 6 | 偽撃転殺 | ADFB | 目标class5且施放者与目标正交相邻 | 8 |
| 7 | 共殺 | AE68 | 目标class0/4且有任一对施放侧的敌方正交邻格单位 | 8 |
| 8 | 籠絡 | AEC4 | 目标class≠5（没有AI忠诚判定） | 10 |
| 9 | 落石 | AECE | 施放者class4/5且正交相邻，目标class≠5（与AI相反） | 9 |
| 10 | 連環 | AF0A | 目标class3且有敌方正交邻格单位class3 | 9 |
| 11 | 十面埋伏 | AF73 | 施放者class0、完整raw16兵>=100、本侧缓存slot==FF | 10 |
| 12 | 水攻 | AF0A | 目标class3且有敌方正交邻格单位class3 | 10 |
| 13 | 連弩 | AFA1 | 施放者class5且正交相邻 | 8 |
| 14 | 劫火 | AFD3 | 目标class≠5且有敌方正交邻格单位class≠5 | 12 |
| 15 | 奇門遁甲 | B01D | 目标class≠3且≠5（没有AI武知/兵判定） | 10 |

`eligible(id)` 对当前050A/0509执行完整AD80资格；`eligibility_suffix(id,target_terrain,actor_terrain)` 适用于真实地形前序已执行的ADA4后缀。`can_target(id,actor,target)` 增加cursor敌方和距离<6前缀，ID11实际以自己为目标且绕过敌方筛选。该便利API明确选择050A/0543，敌方检查失败保留原0509；不输入按键、不排消息、不扣AP、不执行effect。菜单学会/可选条件是另一个前序。

玩家落石要求施放者class4/5、正交相邻、目标class≠5；AI落石恰好要求目标class5。玩家籠絡只有class≠5，没有AI忠诚条件；玩家奇門遁甲只有class≠3/5，没有AI武知/兵门槛。不能用 `ai.action_predicate`替代本表。B7BE的概率阈值有signed8回绕与夹5..95，强知力差可能回绕成5；选中合法目标不保证成功。本模块不会抽RNG或改变结果。

邻接先把raw y>=16减1；格子查询把normalized y15转raw16。原D6B6从19倒序找第一个坐标匹配，未检查0664是否FF；重叠的高slot友军会遮住低slot敌军。ID11的兵>=100读取完整raw16，byte9非零即通过，不把兵高6清掉；缓存只检查slotFF，不检查TTL。AP表只报价，真正扣费位于后续AA96；AI11绕过该消费表的差异由effects模块负责。

地图数据来自pinROM静态chunk/terrain表。ROM descriptor需明确当前data_window_bank或mappedmemory.banks[0]；一次资格内部按实际F266改变逻辑数据窗口，不写真实mapper。RAM/SRAM四字节descriptor和chunk0..119有guard。共享memory可与统一GameEngine直接复用。

最终 **2148原CPU、6 source guards、0失败**，分为2070完整资格RTS和78明确cursor前缀。完整8KiB SRAM、声明RAM0A/0B、10/11、0509/050A、0543及原返回carry一致；其他flags/registers/stack/mapper/CPU工作字节不在高层合同。覆盖全部16项、有效和极值classes、同坐标/正交/间隔、最高槽优先、双方side、raw16兵临界与缓存、ROMdescriptor上下文。实验表外ID不运行原ROM表外代码。

另复用正式native10case（8个计略以及陥穽death/落石levelup）的target-cursor/cast-confirmation RAM/SRAM作为20次CPU输入，全部通过；每个headerJSON、RAM和SRAM SHA固定。cursor样本只把已经正式confirmed的目标作为原AA03选择输入，未称它是快照当时已经选中的0509。独立原core回放/图形成功证据由runtime报告提供，这20次不新增nativeframes或自然可达主张。未引用exploratory文件。

`evidence.json`固定7段原bytes、inline16项地址表、AP报价、mapchunk和依赖hash；`original-ranges.asm`把EADE表和EE07内联word标为数据。`executed-instructions.json`列523个实际地址，不代表每个分支的动态覆盖。

```python
targeting = PlayerTacticTargeting(shared_memory, TargetingData.from_rom(rom))
result = targeting.eligible(9)  # completeAD80资格
result = targeting.can_target(9, 10, 1)  # cursor玩法检查，无UI或施放
```

```sh
.venv-trace/bin/python scripts/verify_player_tactic_targeting.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_player_tactic_targeting.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
