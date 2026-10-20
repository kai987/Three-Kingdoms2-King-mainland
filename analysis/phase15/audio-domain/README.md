# 音频场景的真实调用与闲置栈边界

新增[AudioSceneServices](../../../source/recovered/audio_scene_services.py)恢复physical14 `A003 → 15D8D4`，原可达514条指令。生产是具名Python函数、if/while、真实localJSR/PHA/PLA/RTS和byte/flag计算，运行时不执行ROM/IR、也没有原CPUfallback。音乐token属于游戏数据；解析它不等于解释6502指令。固定D8D6→F25F是唯一外部软件调用，已有独立源码；原AudioServices和Presentation均保持冻结。

## 01EC 的真实 writer

原physical15 DF92/DF93连续 `48 48`（两个PHA），file offsets01FFA2/01FFA3。DF7E读取 `0706+X`，将bit4左移后并入控制值；当 `07F5>=16` 转入N163分支，两次压栈保存同一字节。随后DF9C/DFA8的PLA分别恢复它来写音量和波形控制，最后正常RTS。闲置RAM没有自动清除，这是正常栈残余。

冻结phase14的两种控制输入重新由原CPU从E066进入CA7F/CB79等待，再给显式NMI2软件到达。真实F8CB→A003 callee输入有20份：两种上下文×10次NMI，保留实际AXYP/SP/PC、银行和既有returnframe，没有另外植入caller。两条链的NMI2和NMI10都实测DF93：A=38hex、SP=EC、X=DC（slot220）、0706+X=18hex、07F5=18hex，真实写01EC=38hex/56。NMI2随后其它调用覆盖该残余，因此旧phase14整次NMI第一个可见差异在NMI10；不能把第一次writer等同于第一次完整NMI差异。

旧AudioServices声明free-stack excluded，旧值A6hex/166保留在该接口之外；这是已有owner的协议范围，不能称为未知callee。新exactowner记录这些真实栈操作。[writer回执](writer-provenance.json)保留原写PC/bytes/value及旧语义层差异，新源码20个actualcallee均完整2048B匹配。这些是受控原CPU/NMI上下文，**不是Nestopia内部trace**，也没有新增核心帧。

## 验证与未覆盖范围

独立body矩阵1631比较：1629完整callerRTS、2严格prefix，13个guards，0失败；另20个真实NMI audio frame完整返回。共1651次CPU比较，sourceCPUcallbacks=0。全部2048B RAM（含inactive栈）、8192B SRAM、AXYP/SP/PC、orderedports/banks/reads和N163寄存器image均比较。

原183descriptor×4ticks、全部256callerSP、八channel的音符/音量/滑音/包络/循环/新header/pitch/tempo数据分支及duplicate-channel真实弹栈路径均有有界测试。另一个缺F25F prefix是测试故意不提供已有helper，之后同一caller以纯F25F恢复；B0无限音乐token循环只给原PC/flags/stack prefix，不假装音乐结束。缺registers、decimal、错误pair/entry、returnPC不匹配、无实际PC/SP的helper返回、无正预算的resume均严格拒绝或维持pending。

静态514位置，动态body矩阵覆盖506位置；余下8位置列于[evidence](evidence.json)。这些服务矩阵不宣称所有数据值、自然玩法或所有campaigncallee均覆盖。Scope调查确认两条既有继承链没有真正unowned callee；新服务补的是音频caller协议。它只发原APU/N163请求，不合成PCM、IRQ、帧时钟或ready/ack。完整主循环/NMI组合将在phase15新回执全2048B检查，phase14旧1976B报告原样保留。

```python
owner = AudioSceneServices(shared_memory, rom, services=exact_fixed_services)
owner.run_entry(0xA003, registers=actual_caller_registers)
owner(ServiceCall(...))  # exactphysical14/15 A003 orD8D4
owner.resume()          # same pendingcaller; requires realhelper completion
```

```sh
.venv-trace/bin/python scripts/analyze_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/trace_cooperation_audio_writer.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[原汇编](original.asm) · [静态字节](static-catalog.json) · [body验证](validation.json) · [实际caller与writer](writer-provenance.json) · [证据与hash](evidence.json)
