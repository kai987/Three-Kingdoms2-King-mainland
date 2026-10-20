# 第十五轮：字段、边界服务与长期战役

新增[记录字段](../../source/recovered/record_fields.py)、[精确音频场景](../../source/recovered/audio_scene_services.py)和[同一战役调用上下文](../../source/recovered/campaign_session.py)，通过GameEngine及SceneCoordinator接入可读源码。生产函数不运行原CPU、不解释控制IR，也没有假就绪/ack返回。原ROM只读，重建ROM逐字节相同；旧报告和v14版本ZIP保留。

[交互证据页](index.html)可读三份完整源码、四组原Nestopia画面/完整WAV、逐帧城市/君主/战场字段与准备清单。[最终审计](verification.json)分别统计原CPU对照、明确前缀、源码接口防护及原核心帧，不混计。

## 剩余字段的确认与保留

| 字段 | 本轮确认 |
|---|---|
| 全局`6F06` | 月事件检查锁；实际推进月份清0，真实文字/PPU空闲后原事件过程置1。月份索引3/9分别转阶段6/7。 |
| 城市`+27` | 不利城市事件候选冷却；合格扫描中减1，1→0当次不重新抽取，命中后写6。不能未经证明称六个月。 |
| 城市`+27`边界 | 十槽名册按非FF数量在`17+count`追加；满槽覆盖冷却，有空洞可能覆盖已有槽。人类菜单容量限制和该受控边界调用分开。 |
| 城市`+1` | 正式含义未决；原门槛读取`record[1] \| record[2]<<8`，后者同时是金低字节。保留重叠字读取，不改成正常金字段。 |
| 城市`+28..31` | 初始0/整条复制；本轮有界静态调查未确认专用消费者，不能据此声称全ROM未用。 |
| 武将`+5` | 在野/释放路径的地点用途，不能统一当任职城市；归属仍依据城市名册和君主。 |
| 兵数高六位、状态3、适性3 | 已确认原兵数数值溢出可产生高六位；未发现独立训练旗标。状态3按移除/体力/君主路径区分；适性3正式意义与自然生产者继续未决。 |

事件候选依据统治度0..19/20..29/30..39/40..49，分别要求原E862(A=100)返回字节小于50/30/10/5；50以上不抽取。原RNG有排列表/拒绝采样，不把阈值当独立无偏概率。年89且月索引<4或归属低四位7跳过。后续原损失路径涉及人口、金米、土地产业，官方灾害名与完整动画结算本轮不强命名。详见[字段报告](fields/README.md)、[新schema](fields/schema.json)及[原读写位置](fields/field-accesses.json)。

## 精确音频与待决服务

旧音序owner声明排除闲置栈；第十四轮继承续程首次整次NMI差异在`01EC`。已找到真实physical15 `DF92/DF93`两个PHA，`DF93`写`0x38`（56）；随后`DF9C/DFA8`的PLA供N163控制使用。新owner恢复这些栈操作，以14/15 `A003/D8D4`真实caller接入。20份受控原CPU实际F8CB音频callee上下文全部2048B匹配；这些不是原模拟器内部CPU trace。旧服务和旧v14证据页是历史范围，原图/声音/ZIP未改。详见[精确音频报告](audio-domain/README.md)。

`CampaignSession`保留同一寄存器对象、ServiceMemory、pending phase、ServiceCall和generator。每次显式接受的NMI/IRQ有独立owner，嵌套忙NMI可继续等真实IRQ；内层实际RTI恢复外层PC/SP后，原主调用才续程。软件reset到真实E066时退役旧上下文。API不自动产生按键、中断线、帧、RGB或PCM；未知callee仍停在真实边界。详见[API与矩阵](session/README.md)。

两个受控内政继承CPU父案例分别等待241/481次NMI2，由原`26:CBBF`写ack1后同一主调用到E066。所有722个内部阶段比较完整2048B RAM（含闲置栈）、8192B SRAM、AXYP/SP/PC、顺序端口/银行和N163寄存器图，无排除或人工ack。它们仅计2父案例，不等于722自然帧，也不能把Native战后君主结果强认成这一内政入口。

## 原CPU和源码验证

| 域 | CPU父案例 | 完成边界 | 严格前缀 | guard |
|---|---:|---:|---:|---:|
| 字段 | 3,137 | 688真实caller RTS | 2,449 | 10 |
| 精确音频body | 1,631 | 1,629真实caller RTS | 2 | 13 |
| 真实音频callee输入 | 20 | 20真实caller RTS | 0 | 0 |
| 战役Session | 51 | 21主E066 / 30实际RTI | 0 | 7 |
| 同一Session继承 | 2 | 2主E066 | 0 | 2 |
| 总计 | 4,841 | 2,390 | 2,451 | 32 |

新增对照0失败。字段前缀停在声明的门槛/月轮/插入边界，不代表完整母函数返回；两音频前缀分别是缺F25F fixture和有界无限音乐数据循环。完整局部调用与统一入口均逐字节核对全部RAM/SRAM、真实寄存器与栈、银行及顺序端口；原CPU只在独立py65对照侧执行。[53案例联合回执](source-integration.json)保留23个主E066和30个实际RTI。音频514个静态位置动态覆盖506，字段局部140加固定32位置；未走分支不伪称动态完成。

受新owner影响的phase5..14整合矩阵已实际重跑，旧总审计依据当前源码重新核对；旧原核心媒体与版本ZIP保持原样。第十四轮历史继承比较仍声明1976B，当前刷新不会把它改称全RAM；本轮新继承回执独立完成2048B比较。

## 原模拟器长期与连续流程

使用同一只读原ROM、原Nestopia 2.0.0 135dfa6，每案每次独立Python进程，从头重放原输入。源码未安装到原核心；实际RGB/PCM来自原ROM运行。四案首跑 **93,596帧**，双跑 **187,192帧**；**3,891份非空产物**和正式JSON重复一致，完整serializedstate不截断/不规范化。提供957个真实检查点与48kHz stereo完整声音。来源、准备及限制见[原核心报告](runtime/README.md)。

| 原流程 | 首跑帧 | 起点 | 本轮准备字节写次数 |
|---|---:|---|---:|
| cold-yearwrap | 58,186 | 冷启动普通操作 | 0 |
| consecutive-invasions-attack-return | 17,506 | 导入原存档；准备明列 | 2 |
| succession-heir | 8,952 | 导入原存档；准备明列 | 19 |
| succession-no-heir | 8,952 | 导入原存档；准备明列 | 26 |

- 自然长期战役：冷启动选曹操，36次原征兵/分配确认和12次月轮，189年1月到190年1月，0状态导入/0额外内存写入。满兵时原数量可能保持0但确认仍消耗行动，未把这些称36次有效补兵；原月事件消息也由普通确认操作继续。
- 连续战斗：同一实例连续两次出征并各自实际退却结算返回城市。第二战只准备2个敌坐标字节以形成相邻交锋，原普通攻击/前进/后退实际执行；袁绍兵1000→920、曹操1000→980，然后整场原退却返回预算1。不是两次胜利或全程自然相邻。
- 受控战后异常结算：导入原战场存档，仅准备真实武将能力/HP/AP/位置、资源与（无候选案）城市名册。四次实际ID1陥穽将四敌依次HP归0、状态3、槽清FF；原战后写袁绍君主8→候选9，或8→FF；原占领城4归属2并返回城市0/1。AP30、敌HP1等是明确实验输入，不称自然达成。

Native逐帧只给帧末字段。两继承案未观察到`6F8B`的FB/FC或ack1中间值，不能据最终leader9/FF断言其同帧执行或确认具体CA19/CB52内政链。原核心C API没有内部PC/寄存器trace；独立CPU受控继承证明另列。异常准备没有直接写主/子状态、死亡结果、ready或ack；每个实际改写都保留地址/旧值/新值/原因和完整准备前后RAM/SRAM。

## 继续未决范围

城市+1/+28..31与适性3正式语义、未动态覆盖分支、自然多势力完整灭亡/统一胜利及所有异常继承入口仍需后续证据。当前源码是恢复出的逻辑与软件控制，不是原作者工程，也没有独立PPU/APU/N163时序和RGB/PCM合成。逐字节重建与关键长流程验证不等于整款游戏完全源码化。

```sh
.venv-trace/bin/python scripts/verify_record_fields.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_campaign_session.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase15_succession_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/build_phase15_integration_receipt.py
python3 scripts/write_phase15_report.py
python3 scripts/build_phase15_browser.py --require-final
python3 scripts/verify_phase15.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/package_results.py
```

Native双跑命令和顺序见runtime报告。最终ZIP另做CRC、源码/证据hash及关键文件解压核验；不包含核心动态库、工具链、Python环境或探索结果。
