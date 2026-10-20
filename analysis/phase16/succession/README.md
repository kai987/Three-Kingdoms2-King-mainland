# 原战后继承：城市13消费者与灭亡反馈

[BattleSuccession](../../../source/recovered/battle_succession.py)独立恢复physical25/26 A00C→AD81的7阶段、玩家8子阶段、电脑6子阶段、无继承3子阶段。生产为具名直接Python函数、分支/循环/generator，没有ROM/IR执行或原CPUfallback。四项核心扫描/首将swap/脱离名单为手写可读循环，保留原flags、scratch、实际JSR/PHA/PLA/RTS、同址写序。旧CityPanel和Domestic模块不改。

## 实际入口和phase15内政链的区别

冻结原Nestopia记录中：袁紹8死亡后battle12/15结束，转global1/NMI2 city13/0；电脑候选9或空名单最终分别写9/FF，玩家失败则city13/4选择所属城及新君主。本轮以这些原RAM/SRAM从原27A000回调生成真实27A067 EE07→25A00C的callerframe，另一个frame6253依原A000 cadence早退，明示使用A01F合法dispatchsuffix。AXYP/前置固定调用是CPU fixture，不是Nestopia内部寄存器/指令trace；不能把这些输入称完整硬件帧。

Native战后候选不是phase15受控DomesticCA19/CB52链。实际ADAA按0507低nibble检查败方；AE0D按高nibble检查另一方。只有leader.status低2==3才触发继承；此时controller整个byte==3走电脑C132，其余controller走玩家BE01。未触发则进入后续检查/返回。Native候选9的byte5=0仍合格，原码没有从它推断任职地。

| 0401 | 函数 | 作用/真实门槛 |
|---:|---|---|
| 0 | prepare_postbattle_city / $AD95 | 清04E4，请求29A01E年月packet，回返后phase++ |
| 1 | check_defeated_ruler / $ADAA | 等7E==0，查败方leader/status，设置玩家或电脑继承入口 |
| 2 | check_winning_ruler / $AE0D | 查胜方leader/status，同样保留原controller分支 |
| 3 | restore_city_or_ai_turn / $AE51 | 按当前EE/EF控制器恢复人类城市/驻城光标或AI回合 |
| 4 | player_succession_tick / $BE01 | 玩家选择所属城市→原武将名单→确认→忠诚和可能脱离 |
| 5 | computer_succession_tick / $C132 | 通知→8bit计时→家族→德fallback→写回→通知等待→followers |
| 6 | retirement_tick / $C37A | 无候选：通知/leaderFF；人类输入进入ending或电脑8bit计时返回 |

## 候选、写回与原差异

- 电脑先按26C342每君主8B家族名单的既定次序查找；所属城条件只有city.owner&7==040A。名单遇第一FF停止；家族命中先于FF检查。候选HP、状态、byte5都不是资格字段。
- 家族无候选后C1DB遍历30城，C21D对各城紧凑前缀按武将+4徳选择；原CMP的carry包括等号，所以同值后来的候选替换前者。没有过滤死亡/在野状态，也没有按bodyHP取代名单资格。
- C25D电脑提交只写affectedruler.byte0和城市首将swap；不写ruler驻城byte1或候选byte5。确认后候选忠诚100；家族候选跳过followers调整。
- 玩家原地图必须选owner&7匹配的城，再选原名单并确认。BF2F写新leader、EE/EF+1驻城，再首将swap。低忠诚非新leader可能脱离：玩家C01E清status低2并写byte5=city，空名单的owner整个byte写7；电脑C318清status低2/紧凑名单，保留byte5和owner。这些不统一为相同转属事务。
- 无候选C386只写affectedruler.byte0=FF，保留controller/外交/城市归属/其余名单。此处controller按低2位==3分通知分支，和ADAA/AE0D对整个byte==3的测试不同。电脑C41E在04D0原8bit增一计时的256调用wrap后回0472/0473；人类C3C2必须真实文字完成和A/B输入才进入global13。调用不是视频帧。
- raw兵数字节与高6位不改；边界病例包括F123完整word，源和原CPU全8KiB SRAM比较。battle死亡、战胜占领、败退和俘虏数组等在前序已发生，本消费者不能据leaderFF再补一遍统一清理。

## 服务/调用合同

PUBLIC仅(A00C,AD81)、PAIR25/26；LOCAL38入口供独立原CPU定向fixture，不抢其它panel。run_entry要求实际registers和已有returnword，无seed参数；ServiceCall只有status returned且原PC/SP真实返回才继续。四dispatch索引严格限定7/8/6/3，非法fixture只做源码guard，不执行原表外code。

真正依赖为固定record/message/menu/RNG，29A01E年月producer、27A006候选城市资料、10A009→CF7C忠诚及固定E57F/E673/E683音频请求。根协调器现接独立exact owners，源码侧原CPUhelper调用0。文字、城市资料与PPU状态由真实consumer推进；正文不写ready或ack，不自动制造按钮/NMI/IRQ。

## 验证范围

原CPU 336 项：334完整实际callerRTS、2严格prefix（刻意缺recordhelper及显式零预算）；另15源码guard。全部2048B RAM（含闲置栈）、8192B SRAM、AXYP/SP/PC、端口读写序/映射银行/N163图相同，失败0。
其中22个原Native输入callee：21由原A000回调产生，1明示A01F suffix；准备步骤不再计新增case。覆盖全合法dispatch索引、7君主family/noheir、HP/condition/byte5边界、firstFF/tie、首将swap、31忠诚/20RNG门槛、玩家/电脑脱离、raw兵和计时wrap。
原静态877位置，动态754，尚未动态覆盖123位置逐项列evidence；完整静态正文不等于所有分支/数据值/自然战役已验证。Native原画面/声音由原核心生成，另见phase16 runtime，不能由本软件比较声称硬件像素/PCM等价。

```python
owner = BattleSuccession(memory, rom, services=exact_source_coordinator)
owner.run_entry(0xA00C, registers=actual_caller)
owner(actual_ServiceCall)
owner.resume()  # 同一真实pending，等待外部服务返回
```

```sh
python3 scripts/analyze_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[原汇编](original.asm) · [静态catalog](static-catalog.json) · [原CPU回执](validation.json) · [真实caller输入](actual-callee-inputs/) · [完整pins/未覆盖](evidence.json)
