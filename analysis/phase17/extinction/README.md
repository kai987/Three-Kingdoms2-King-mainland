# 玩家无候选、灭亡反馈与mode0结局

[PlayerExtinction / PlayerLossEnding](../../../source/recovered/player_extinction.py)在冻结战后/结局控制器中替换六段具名直接规则。真正A00C/AD81父流程的self局部调用进入新方法，NMI8 A01E父流程调用新mode0方法；没有额外伪JSR，没有IR/原CPUfallback。原图形、文字、固定helper、全局13初始化和E000重启继续使用已恢复的独立源码。

BE2E只在0300/0304均FF且新A或B后扫描30城：city.owner低3位等于040A、名册首槽+17不是FF就足够。没有ownedcity和所有ownedcity首FF都会进入0471保存的无候选phase。首FF后仍有武将的hole也算无候选；首槽为原死亡/status3/HPFF武将仍算有候选城市。不能把该判定改成所有十槽、活着的武将数或任职地byte5。

C386仅把君主表leaderID写FF，城市owner、名册、控制器、驻城和外交均保留。初始ADAA/AE0D用整个controller==3分电脑/玩家；C386则用controller&3==3分通知，因此83/FF等raw边界不会被统一清洗。电脑C41E等待8bit调用计数wrap；玩家C3C2等待两文字job完成及A/B，构造日期/对方leader信息后进入global13、0541=0、04CA=0。C3C2中的040C是另一君主索引的作用域别名，不是此阶段的城市ID；它或对方leader为FF时，随后mode0请求D9，否则请求D8。

Global13 E46A设置NMI8并转global14。mode0 D6AA初始化palette/真实消息，文本完成后04CE逐次增一、查原D755 marker表。markerFE时只新A退出，B和无输入保留。6F43来自原标题人数选择0/1及新君主0543，不是实时剩余人类君主数量：0实际tailE000，抛弃旧caller栈并回E066启动边界；非0清6F43、0400/01←0472/73、0402=0、global1继续。不能把所有global13都称胜利或所有玩家灭亡都称整场结束。

新类保留actual caller AXYP/SP/PC和既有stackword；missing服务必须保持同一pending，不凭status字符串提前RTS，不写ready/ack，不制造NMI/IRQ。只读candidate_city_report解释BE2E的首槽门槛，不代替正式caller执行。

原CPU回执423案：416实际callerRTS、4原E000非局部reset边界、3严格prefix，另16源码guard。全2048B RAM（包括闲置栈）、8192B SRAM、AXYP/SP/PC、端口读写序、银行与N163图逐byte比较；源码原CPUcallback0。静态范围195位置，动态覆盖195，未执行位置逐项列evidence。受控原CPU输入和实际Native内存来源分别列在回执；不是Nestopia内部寄存器trace，也不是像素/PCM生成器。

其中28项使用正式三案冻结Native内存生成原caller：17项原27A000城市回调、3项A000真实cadence早退后的明示A01F dispatchsuffix、8项从声明E066寄存器接受原NMI，执行到FA85真实JSR A01E。FE上的额外新A只用于独立CPU夹具，经原E6C6读取显式手柄输入产生；不写按钮/ready/result/ack内存。准备过程不再加case，所有初始寄存器、实际returnword/banks与前序记录保存在[caller输入](actual-callee-inputs/)。完整reset夹具显式供PPUSTATUS80/00边沿；持续0则停原E00C等待，未知E000另保持原tail依赖。三条原模拟器视频/PCM流程和它们的准备字节见[正式Runtime](../runtime/README.md)。

```python
postbattle = PlayerExtinction(memory, rom, services=source_coordinator)
postbattle.run_entry(0xA00C, registers=actual_caller)
ending = PlayerLossEnding(memory, rom, services=source_coordinator)
ending.run_entry(0xA01E, registers=actual_caller)
```

```sh
python3 scripts/analyze_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

正式423项回执包含Native调用层，复现应给三次`--native-case analysis/phase17/runtime/目录`：`single-player-empty-rosters-reset`、`two-player-empty-rosters-continue`、`former-leader-only-candidate`。不带该参数仅运行395项有界核心矩阵；不得据此覆盖最终回执后仍引用423项声明。

[原汇编](original.asm) · [逐byte静态来源](static-catalog.json) · [CPU回执](validation.json) · [pins与未覆盖](evidence.json)
