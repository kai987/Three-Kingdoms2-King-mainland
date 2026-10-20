# 第十二轮：肖像、姓名、武将资料和精确文字服务

本轮补上普通攻击与战场资料页使用的远端UI服务：肖像OAM、姓名nametable包、十行武将资料，以及保留真实caller寄存器/栈的文字生产与消费。新增生产源码不执行原6502、不解释opcode/控制IR，也不安装原CPUfallback。原数据、CHR、模板、文本命令和REA/Ghidra档案仍可逐项复核。

- [交互证据：原画面、WAV、字段与源码](index.html)
- [最终字节、hash、原CPU与原核心总审计](verification.json)
- [普通攻击依赖发现和纯源码集成](dependencies/README.md)
- [两个原核心UI流程及其原起点](runtime/README.md)

## 四个新服务的实际职责

| 独立源码 | 原入口与作用 | 原CPU对照 | 单列guards |
|---|---|---:|---:|
| [PortraitUIServices](../../source/recovered/portrait_ui_services.py) | physical25 A000→26 CE1F，两层肖像OAM、左右CHR选择、嘴形/帧和原坐标处理；固定F1B7 | 5,869：5,867完整＋2严格前缀 | 6 |
| [OfficerUIServices](../../source/recovered/officer_ui_services.py) | physical29 A030/A03C姓名包及共同F308；另外A027/A02A/A033/A036 | 5,557完整 | 10 |
| [TextSceneServices](../../source/recovered/text_scene_services.py) | physical29 A000/A003/A006及真实文字生产/消费、32类游戏文本命令、早退和EE72 cadence | 1,306完整 | 7 |
| [OfficerDetailsUIServices](../../source/recovered/officer_details_ui_services.py) | physical25 A012→B2D7十行资料，真实busy/负row早退、数字/适性/装备字形与CHR shadow | 6,693完整 | 5 |

四模块小计**19,425项原CPU对照：19,423完整返回、2严格前缀；另28项源码guard**，均0失败。肖像两项前缀来自原循环descriptor，保留同一owner和调用栈等待，不算完整返回。源码侧原CPUhelper调用为0；原CPU只在独立验证器作为对照。

肖像、姓名与十行资料比较全部2KiB RAM（含自由栈残余）、8KiB SRAM、AXYPSPPC、银行和端口。精确文字比较RAM0000..013F及0200..07FF共1,856地址与全SRAM/寄存器/银行/端口，明确排除其自由栈残余；不能把四模块都称为全2KiB RAM相等。[各子目录回执](text/validation.json)保留具体地址和作用域。

## 姓名包与完整资料页的区别

29 A030/A03C只生成姓名包、设置007E.bit2。A030使用0000中的ID；A03C以0001为0/非0选择左右模板。共同F308将姓名数据窗切到physical16，写E1/E000、0000/1/2，返回原对齐值而非字符数。原模板跨度58B而下降复制循环读取59B，包括下一region首byte；源码保留这一CPU可观察写入。细节及六个真实EE07 callee输入见[姓名服务报告](officer-ui/README.md)。它们不代替Text.consume，也不构成武将属性卡。

战场main1/sub1的A244先调用25 A000肖像，再调用**25 A012→B2D7**资料producer。040D是0..9行游标，取0410[040C]中的武将ID，卡片目的地址是`[2400,2540,2680][040C%3]+32*row`，是三个相隔十行的资料槽。每次只请求一行：007E.bit2已置位时原样RTS；row9后才将游标写FF。源不会自动清请求位或递增到下一行。

十行中含姓名/标记、体/徳、等级/知/忠、平山水适性、兵/武/経、武器/防具与CHR shadow。兵的显示使用低10bit，経験按原u16乘2的显示步骤，通常等价floor(XP/50)，没有修改永久值；忠100用特殊原字形。适性编码3仍按原相邻bytes读取，未赋官方地形名。完整字段、FE/无效ID、装备及mode3行为见[资料服务报告](details/README.md)。25 A003、A006、A030分别是其它年月/势力、城市AI、金粮结转入口，不能因bank相同就称属性页。

## caller协议与攻击控制器整合

`SceneCoordinator`已在共享ServiceMemory中按真实PRG银行/目标地址分配这四个owner。固定F308由OfficerUIServices拥有，可接受其它pair的真实调用。每个pending服务保留同一generator和caller frame；没有种植合成0200返回栈。只有明确returned且PC/SP匹配才能推进。文字早退、包已请求、PPU消费完成和整页已画完分别处理。

```python
engine = GameEngine(service_memory, rom=original_rom, mapped=True)
coordinator = engine.readable_scene_rules()
result = engine.tick_readable_scene(actual_registers, scene=4)
if result['status'] == 'dependency':
    # 真实端口/待处理服务到达后续同一owner。
    result = engine.resume_readable_scene(scene=4)
```

[攻击集成回执](dependencies/source-integration.json)与[callee目录](dependencies/catalog.json)分别记录原helper依赖发现和纯源码对照。基础域是58合法主态/phase×三种按钮byte×A000/A069两个入口，348次；扩展域另加七种方向byte及AAEA scan=4/5，最终1,164次范围以该回执和总审计为准。最终回执为1,164项完整返回、1项另列guard、0失败；总审计只接受passed、exact AXYP和稳定source pins。

原依赖发现也执行这些入口和原helper，但不是第二套源码CPU比较，**不会与1,164重复相加**；helper数量单列。集成检查声明1,972个RAM地址、全8KiB SRAM、AXYPSPPC及银行/有序端口，排除inactive01B4..01FF；不等于穷尽每个输入byte、所有branch或自然可达性。source-only拒绝/续程guard另列，也不计入CPU比较数。

[附加资料页协调器对照](ui-integration.json)另有**45项原CPU：44完整返回、1严格前缀；1个scope guard**，不混入四模块或1,164攻击矩阵。它使用冻结原核心检查点的RAM/SRAM，再明确准备CPU caller/registers和实际mapper helper，比较同样1,972声明RAM/全SRAM/AXYPSPPC/银行与端口。覆盖25A012、战场A244/A000，以及EE53真实消费后再次生成资料行。frame31尚未初始化资料上下文的额外A244调用只到严格前缀；不是自然原核心多执行过一次A244的证明。native CPU寄存器未被观测，源码不靠原CPUhelper、完成stub或ready写入。

三类CPU验证合计**20,634项：20,631完整返回、3严格前缀；30项另列guard**。这是四模块＋攻击集成＋附加UI的相加，未包含原依赖发现执行、原核心帧或guard为额外CPU案例。

## 原核心两条流程

原Nestopia运行相同ROM，恢复源码没有安装到core。两条流程首跑**2,915帧**、双跑**5,830帧**；**46检查点、200非空产物、12正式JSON**重复一致。12份JSON包含在200产物中，不再重复加总。首跑WAV为48kHz双声道16bit PCM，共**2,328,166个stereo sample frames**；两次相同样本数合计4,656,332。空VRAM文件46份及目录metadata JSON排除。

| 流程 | 起点与真实操作 | 观察结果 |
|---|---|---|
| 战场武将资料，514帧 | 继承阶段11无注入冷启动后的battle-control-return；none30、B2/none240打开、A2/none240关闭 | battle1/sub1、040D=FF、ID131资料实际显示；回battle0/sub2 |
| 普通攻击返回，2,401帧 | 继承公开的邻敌坐标fixture；复放阶段11相同按钮/时长 | 原後退命令及确认/结算后回battle0/sub2；旧24检查点96份PNG/RAM/SRAM/state逐byte一致，新回放共有30检查点 |

此轮新增ROM/core RAM/SRAM、ready或结果写入数量均0。第一案继承自然旧起点；第二案保留之前敌slot0的X20→3、Y14→16明示准备，不称无准备自然战役。每帧UI控制、scratch、姓名包、文字队列、CHR/OAM及RAM/SRAM/RGB/PCM哈希可复核。虽帧结束观测包含行0..9与FF，也不据此声称录制了每条内部调用。它们是实际原核心RGB/PCM和帧字段，不是nativeCPU/NMI指令trace、恢复源码独立像素/波形合成或完整战争胜利。

冻结检查点名 `info-rows-complete` 实际对应**frame31**：刚进入资料页，040D=FF沿用旧值，此时尚未完成新卡，名称不能当作完成证据。实际0..9推进观测在frame32..42，使用**info-open（frame272）**作为全部十行已绘制且游标FF的正式完成画面。原文件名、bytes与hash保持原样；门户对这个历史名称另外解释。

## 复现与边界

```sh
python3 scripts/analyze_officer_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_officer_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_portrait_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_text_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_officer_details_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase12_attack_integration.py --rom '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/verify_phase12.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

总审计动态读取四模块、独立集成、原核心、当前第五至十一轮回归和浏览器回执；缺失/陈旧hash不能通过。源码与验证脚本、REA/母档/core artifact分别固定，文件偏移含16B头，重建镜像与原ROM逐byte一致。`--allow-pending`只生成缺文件的明确草稿，不能作为发布passed回执。最终打包验收以[总审计](verification.json)及浏览器回执为准。

本轮解除已观察的肖像/姓名/文字caller缺口并恢复战場十行资料。未将其它城市菜单、任意坏descriptor、每个异步时序、PPU/APU/N163硬件模拟器或原作者完整源码宣告完成；未知callee继续保留明确依赖。
