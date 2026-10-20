# 第十三轮：城市菜单、全局UI与图形初始化

本轮把城市16项主状态及子菜单、标题、君主选择、结局UI和固定银行主循环的正文整理成直接Python函数，接入同一GameEngine、ServiceMemory和SceneCoordinator。远端图形、开场动画、城市武将资料、新剧本初始化、菜单导航和报价/忠诚/算术依赖都有独立owner。生产路径不解释控制IR，也不调用原6502。

[交互证据页](index.html)可以切换源码、原画面、字段前后变化和两段完整WAV。[纯源码组合回执](source-integration.json)、[总审计](verification.json)及[源码入口](../../source/README.md#第十三轮城市菜单全局ui和远端初始化)分别提供可复现结果。源码是本次逆向重写，完整NES帧和声音仍由原核心合成。

## 城市与全局控制

| 原入口/字段 | 恢复行为 |
|---|---|
| 27A000→A00C | NMI场景2城市更新；0410名单、菜单状态和图形/文本请求 |
| 27A022表16项 | 0400主态：世界地图、命令栏、内政、军事、物资、街市及其他面板请求 |
| 27A298 / ADF5 / B75C / BFBA | 内政23、军事25、物资16、街市24项有界子表；原内联字节与全部目标保留 |
| 27CAE2 | 状态6中的18项子表；未由原画面确认的条目保持原地址命名 |
| 25A02A→BBDE | 年份/日期标题远端worker |
| 25A021→AFE5 | 5阶段城市武将资料驱动；不是25A012资料正文，也不是25A01B新人事件 |
| 0410[040C] | 当前选择的真实武将ID；Native曹操→于禁切换为索引1、ID5，不固定使用名单首项 |
| 10A003→D717 | 标题及子菜单控制，共26个合法主/子阶段组合 |
| 8A024→D70F | 君主选择的7个主阶段 |
| 23A01E→D693 | 结局6模式、最终文字6阶段、credits7阶段；17个合法组合 |
| E066 / 007A | 15项全局主循环分派；一次完成指到下一E066，保留caller SP，不伪造RTS或完整帧 |

原模拟器画面纠正了两个旧标签：城市main4是**物资输送／给予**，main5是**街市／店铺**。标题和君主选择使用0540/0541，结局使用0541/0542；城市使用0400/0401，0480不是统一UI状态。

AD41保留目标城名册追加、君主置首、源城移除与压紧；B859/B879保留出征名单删除、压紧和资源扣除。A1EB扫描30城的十个名单槽，A209递减七个君主记录的非零nibble，A240统计排除君主的可用武将。复原保留字节溢出、sentinel与caller flags，没有用现代业务规则替换原行为。

## 解除的服务依赖

23A012→A61C、A015→AEF0、A018→A983的图形初始化保留CHR/attribute/PPU请求；23A021保留五阶段开场图形。29A018→DD8B初始化6000..6FFF，保留6F43，复制原ROM的960字节城市/势力数据和2880字节武将数据。25A021复用phase12已恢复的姓名、肖像和十行资料正文。

8A01E→C851只产生四件装备ID与三字节价格，不代表已经购买或扣钱；10A006→CF3F保留忠诚字节的原算术与10..90夹限。EC22用24bit×16bit产生40bit结果，保留破坏性shift和scratch。

精确ED19..ED41菜单服务补上了原ED6B→EDDD局部调用。统一入口首次对照发现已退出调用的栈残留差异，本轮独立owner按原JSR帧修正；正式13例整合仍比较**全部2048RAM，包括完整stack**，没有排除差异字节。水平反向搜索只跳过FF，垂直搜索以signbit结束；缺sentinel仍是循环依赖。

## CPU与源码验证

| 模块 | 原CPU例 | 完整返回/有界出口 | 严格前缀 | source guard |
|---|---:|---:|---:|---:|
| [城市菜单](city/README.md) | 712 | 707 | 5 | 4 |
| [城市与君主面板](panels/README.md) | 533 | 530 | 3 | 4 |
| [全局/标题/君主选择/结局UI](global-ui/README.md) | 2,432 | 2,157 | 275 | 18 |
| [远端图形初始化](graphics/README.md) | 9,440 | 9,440 | 0 | 7 |
| [新剧本初始化](scenario/README.md) | 256 | 256 | 0 | 3 |
| [城市武将资料驱动](city-details/README.md) | 7,509 | 7,509 | 0 | 5 |
| [开场图形](title-intro/README.md) | 3,120 | 3,120 | 0 | 6 |
| [报价/忠诚桥接](action-bridges/README.md) | 2,005 | 2,005 | 0 | 5 |
| [40位乘法](arithmetic/README.md) | 512 | 512 | 0 | 1 |
| [精确菜单导航](menu-navigation/README.md) | 2,120 | 2,120 | 0 | 5 |
| 合计 | 28,639 | 28,356 | 283 | 58 |

完整与前缀均比较实际CPU寄存器、caller PC/SP、SRAM、端口顺序和bank；前缀只证明到声明依赖边界为止，不计成完成调用。图形、新剧本、资料驱动、城市/面板、动作桥接、乘法和精确菜单比较全2048RAM；开场与全局纯source组合使用1972个RAM位置加实际活动caller帧，旧服务的空闲栈残留不属于这些声明的范围。具体scope与各模式分开记录在各validation.json。

城市本地验证覆盖2905/6330原指令位置，面板覆盖2402/3841；静态收录不等于动态路径覆盖。面板49个无效或不终止的准备输入明确列在[排除清单](panels/unusable-fixtures.json)，不计入通过案例。

城市和面板的本地矩阵在validator内借原CPU执行外部helper，不能由此宣称helper源码完成；全局矩阵也分别列fixedCPU-helper和纯source两类。独立[13例城市统一入口组合](source-integration.json)使用Native不变RAM/SRAM快照，并在两侧实际执行F206/F25F/F237准备服务，再通过GameEngine更新城市。13例全部完整返回，source侧原CPU callback为0，全部2048RAM/8192SRAM/AXYP/SP/PC/有序ports/banks一致。AXYP和0200已有caller帧是公开的受控CPU输入，Native没有提供内部寄存器轨迹。前序helper属于这13个组合，不额外膨胀比较总数。

## 原模拟器完整流程

原Nestopia2.0.0 135dfa6、ROM与核心hash保持不变，两条新流程从phase11自然冷启动城市命令快照继续。没有新增core内存写入，也没有让新源码替换核心运行。

- 城市四菜单：命令栏→内政/武将选择→取消；军事→取消；物资→取消；街市/武器店武将选择→取消回命令栏；最后B返回世界/城市光标。
- 武将资料：城市命令栏→世界地图→曹操资料→下移为于禁→上移曹操→关闭→返回世界/城市光标。

首跑3,100帧，双跑6,200帧；47个PNG/RAM/SRAM检查点、204项非空重复产物（含12项正式JSON）完全一致。首跑48kHz stereo PCM为2,475,922采样帧。47项0B VRAM不作为像素或内存证据，snapshot metadata也不计入正式重复产物。

两案最终8192B SRAM与自然起点相同。这个回放验证菜单进入、选择、取消、资料和回归流程；购买、执行内政、结束回合及持久资源变化没有由本轮Native回放验证。标题/君主选择/结局的Native起点来自已归档旧阶段，其新正文验证见CPU矩阵，不夸称本轮全部重新整机运行。

## 使用与边界

```python
coordinator = game.readable_scene_rules()
# registers 与已有caller帧来自真实调用方或明确声明的CPU fixture。
result = game.tick_readable_scene(registers, scene=2)
result = game.tick_readable_main(registers, entry=0xE066)
# 依赖未完成时，保持其上下文，外部服务完成后 resume。
```

冷重启E000、可选启动F3BD、全局main2/4中尚未直接源码化的合作AI调用和硬件时钟/PCM仍保留声明边界；不能把旧IR入口的存在算作新纯source出口。图形请求、异步等待和队列flag不会由caller伪造完成。

复现脚本：各域README提供source生成和CPU validator命令；`verify_phase13_city_integration.py`验证纯组合，`capture_city_ui_flows.py`复现原核心两案，`build_phase13_browser.py --require-final`生成门户，`verify_phase13.py ROM`做只读证据审计，`package_results.py`校验旧阶段、hash与非空重复产物后归档。打包排除核心可执行文件、Python环境、REA/Ghidra运行时和exploratory结果；重建NES仍与原ROM逐字节相同。
