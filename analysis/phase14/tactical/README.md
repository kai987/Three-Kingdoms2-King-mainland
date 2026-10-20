# 战术合作控制器：直接源码与真实调用协议

原main4入口8 A000 `4C 2D A0`跳至A02D，physical8/9。全部可达正文2213个原指令位置现离线按原ROM重建为160个具名Python函数、350个if、34个自然loop。生产只使用直接函数/条件/循环和独立byte/flag/stack算术，不读取旧phase7的program.json，不解释IR、opcode或PC指令字典，不执行原CPU。函数名是现代说明，8策略编号不宣称为正式游戏菜单名。

## 请求与字段

6F8B=FF立即返回；=1进入B933已有对侧埋伏缓存消费；其余raw byte进入演员扫描。6F94是原scan cursor；跳过6FA1[slot]=FF、异side或0664[slot]=FF，合格尝试增加6F96。策略返回6F8F=3才增加6F95并继续扫描，其他提案将request置FF交还调用方。扫描完计数不相等时重置94/95/96重扫，相等则status3、scan0、requestFF。计数保持u8回绕。

演员slot=6F8C；6F8D按status代表移动方向、攻击/计略编码或退却城市，6F8E为目标slot，6F8F状态由另一个战场消费者解释。普通计略ID与移动方向是不同编码。RNG使用6F92并把当时原X保存到6F93，保留拒绝抽样、废弃抽样及调用次序。

## 八策略与十六资格路由

| 策略 | 原入口 | 具名控制的优先次序 |
| ---: | --- | --- |
| 0 | A0B1 | 退却→特殊计略→side分支的基础计略/邻接攻击→抽样后移动或不行动 |
| 1 | A105 | 退却→特殊计略→对侧首槽邻接攻击→对侧首槽/原城市base坐标移动 |
| 2 | A166 | 退却→特殊计略→邻接攻击→actor半径2候选；无候选对侧首槽/base移动 |
| 3 | A210 | 退却→特殊计略→邻接攻击→本侧首槽半径2候选/友军情况→基础计略或靠近 |
| 4 | A2AD | 退却→特殊计略→邻接攻击→actor半径3候选；无候选基础计略/本侧首槽移动 |
| 5 | A329 | service0路线预测、标策略7、原资源word预算与补给写入 |
| 6 | A507 | service2路线预测、标策略7、资源扣50、原RNG/byte回绕治疗写入 |
| 7 | A606 | 直接提案status3 |

A09E只有8个合法B517索引；ACAB有16个计略资格索引。每个原inline word与其别名目标全部保留，表字节从原代码收集中剔除。B517真实协议保留scratch20..24、ASL/carry、原Y和弹栈，独立实现31字节原helper的作用。非法表外索引由source guard拒绝，原CPU不执行其表外字节。

基础/特殊候选排序、白名单、目标资格、两轴greedy移动、退却、raw16军队合计、24/16bit除法、24×8乘法、地图数据窗和费用读取均是本闭包的实际函数；已有[高层规则说明](../../phase8/strategies/README.md)可读对应玩法计算。新控制器另包含全部scratch、flags、局部JSR残余、callerRTS及F266真实mapper写入，补上旧高层API没有声明的CPU协议。F266使用主线程DE/E000数据窗。

该body除了提案也有真实副作用：策略5/6可能提前修改资源、HP和策略标志；B933消费至少由十面埋伏ID11建立的对侧缓存，扣low10兵并保留byte9高6位。原B965读取0614[group0/4]的quirk、discarded RNG与余下副作用保持。全部缓存producer没有由该名字链证明，Native输入也不等于新自然触发验证。实际坐标/APcommit、普通攻击、施放动画/结果与后续埋伏报告/经验仍由另外的原消费者执行，本body不清任何ready/IRQ/message等待。

## 原 CPU 矩阵与边界

正式1477次原CPU比较：1026完整RTS、451严格prefix、15source guards，0失败。prefix中448例只到B517所选策略/资格入口，2例为显式block预算暂停，1例为缺F266的真实call边界；这3组暂停后另外计完整续行对照。比较全部2048RAM（含完整inactive栈）、8192SRAM、AXYP/SP/PC、有序ports/banks；source侧原CPUcallback=0。

矩阵覆盖全部256requestbytes、八策略×两side×AP/位置条件、28功能入口、连续扫描、对侧缓存、补给/治疗资源边界、E22C真实caller、多种SP与B517全部256SP/24合法索引的组合。13个冻结phase7原机RAM/SRAM仅复用为同步CPU输入，没有增加Native帧或原机内部trace。静态2213正文位置，动态命中1669，其余544位置明确列在evidence；静态完整收集不表示所有分支/值组合都动态验证。

```python
controller = TacticalCooperationController(memory, rom, services=actual_source_services)
result = controller.run_entry(0xA000, registers=actual_caller_registers)
# 有真实F266服务后恢复同一调用；预算暂停需显式正预算。
result = controller.resume(max_blocks=10000)
```

registers必须由调用方提供，返回PC/SP从其已有栈读取，无默认seed。`__call__(ServiceCall)`仅接受physical8/9与已恢复local入口。services必须明确返回status=returned并实际恢复callee PC/SP才继续。缺服务的resume、缺预算的resume保持原prefix；显式续预算不是游戏ack。max_blocks计源码control checkpoints，不计原CPU指令。

```sh
.venv-trace/bin/python scripts/analyze_tactical_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactical_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[新源码](../../../source/recovered/tactical_cooperation_controller.py) · [回执](validation.json) · [原字节/依赖/位置](evidence.json) · [原汇编](original-ranges.asm) · [离线原ROM目录](static-catalog.json) · [具名源码结构](source-catalog.json)
