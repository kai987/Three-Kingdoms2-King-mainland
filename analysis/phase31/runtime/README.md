# 第31轮原模拟器：连续玩家处置与真实AI败退入口

正式回执：[validation.json](validation.json)、[evidence.json](evidence.json)、[逐产物重复核验](repeat-artifact-checks.json)。四条窗口均导入已披露保存点，以普通输入继续；本轮没有新冷启动或额外核心内存写入。固定原核心和独立31观察核心分别以新Python进程执行两次。全部完整初始缓冲及逐帧2 KiB RAM、8 KiB SRAM、256×240 RGB、48 kHz双声道16位PCM和完整序列化state逐字一致；没有裁剪、补零或归一化state。

| 路线 | 本轮首跑帧 | 祖先范围与实际覆盖 |
|---|---:|---|
| [natural13-continuous](natural13-continuous/original-control/checkpoints.json) | 1551 | 冻结22自然母档6116，原普通输入计划6116..7667；连续经历人类13的七阶段、15/1至15/3和城市返回。祖先已知数值准备0，本轮新增0。 |
| [controlled14-direct](controlled14-direct/original-control/checkpoints.json) | 32 | 冻结15母档8048；继承19个公开数值准备字节，较早legacy准备仍未完整确定。人类14/0直接返回，非14七阶段交互全覆盖。本轮新增0。 |
| [all-AI-Start-bypass](all-AI-Start-bypass/original-control/checkpoints.json) | 64 | 冻结14真实冷启动祖先game-start母档；普通A+Start 8帧、无键56帧。观察到D7C3绕过人类控制器赋值，7个controller保持3，最后global2/NMI2；不擅称官方观战模式。早先600帧仅为探索。 |
| [natural-AI-mode2](natural-AI-mode2/original-control/checkpoints.json) | 557 | 从单挑局部1211真实母档继续317帧，再连续240帧战后输入，中途不导入存档。母档0514=131，须靠本轮实际writer和调用栈证明新战果。其上游10段141636帧为固定原核心单跑祖先，不是这557帧的四跑范围。 |

四条首原核路线合计2204帧，16个fresh进程合计8816帧。18639个非空产物重复检查包含4408个PNG对照和8个完整WAV对照；这些是对照对数量，不能再与相同的重复路径加为新案例。首观察流共1376552条事件、297份完整软件快照。固定原核心本身不带新增内部跟踪。

## 实际mode2与连续性

[natural-AI-mode2/observations.json](natural-AI-mode2/observations.json) 保留以下原事件，而非由最终模式或返回字倒推：

- seq2091／本地帧4：physical13 DD9E的原`STA $0514`将131写为1。
- seq339514／帧502：physical8 BB36真实JSR边界，SP237；seq339518为BC46入口，SP235，已有栈word为BB38。
- seq339530：BD67真实mode2目标；seq340685：实际返回BB39，SP恢复237。

本次mode2临时名单为空，BE4C仅有21次FF→FF。该BC46调用没有城市或BDB8写入，不能称为非空分配或完整BD96地址合同的Native证明。之后BB4D同值写6F44、D4BA写6171 FF→131及BC3C／BC43同值写属于后续步骤，原事件保持分列。模式0／1在另两条窗口真实观察，受控CPU矩阵与本轮Native覆盖仍是不同范围。

自然13的帧末阶段首见为本地1／2／241／545／787／820／1277；CD16及具名阶段函数在随后一次真实NMI调用进入，不能把帧末阶段值当成同一时刻的callee。它在1519回15/1、1520至15/2、1521至15/3，最终global2/NMI2。该新1551帧自身的四跑相等不等于旧22／29历史PCM与state字节复现。

## 祖先、实际软件现场与设备边界

[自然AI祖先](../ancestry/natural-AI-mode2/ancestry.json) 保存10段实际输入、逐帧五缓冲哈希、段首末state和终态RAM／SRAM；段间是公开的state imports。上游普通征兵及兵力分配／月轮、布阵、待机提示确认、移动、普通攻击与单挑均保留原计划。错误菜单探查不作为成功祖先。独立[输入来源补证](../ancestry/natural-AI-mode2/ancestry-proof-inputs.json) 仅复制原plan用于557帧拼接核对，不新增核心执行。

独立观察核心实际SHA为`21bb820cb4884f00f53b7be86ddc30cd4de484f68d93ea08d6e2e961100c380e`，固定原核心SHA为`924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a`。源码、补丁、官方135dfa6提交及依赖重编日志见[core-provenance/build.json](core-provenance/build.json)。新ABI为72个u32（288字节）；原`events.jsonl`、`bus-events.bin`和快照均完整保留，溢出会失败。

软件现场来自独立观察核心的const backing copy，包括2K／8K、实际AXYP/SP/PC、已有栈和实际四PRG页。没有瞬时N163、PPU或APU设备快照；后续Source／原CPU对照所用共同设备夹具必须另列。A000／A028的首次阶段样本不是自动完整的entry／return配对。BB39／BB8F只有真实opcode事件及SP核验后才列为已观察返回。

自然13的一个城市辅助总线命中是D243 `STA (00),Y`的dummy读：00/01=63FC、Y5，逻辑EA6401，而虚读地址6301。它不是城市+1的新增逻辑消费者。零命中也不能证明字段unused。城市+1和+28..31的正式名称仍未知。

## 存储和媒体核验

[storage-deduplication.json](storage-deduplication.json) 记录仅新31产物的完整逐字比较后hardlink去重。37278条捕获文件路径、9663152518逻辑字节保持原路径与SHA；唯一inode逻辑字节4664766163，重复逻辑字节4998386355。这是存储节省，不是缓冲归一化，也不改变每个fresh进程已经实际执行的事实。旧30及更早文件没有被替换或链接。

[media-static-validation.json](media-static-validation.json) 只读检查原PNG和WAV容器／PCM数据，另列人工视觉核对点；没有生成替代截图或声音，也没有新增Native帧。Source差分、独立原CPU合同、静态模型、浏览器验收和Native帧各自计数。完成31后停止，不自动启动32。
