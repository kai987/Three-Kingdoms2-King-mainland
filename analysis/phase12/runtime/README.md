# 第十二轮原核心UI流程

**冻结标签说明：**`battle-officer-info/info-rows-complete` 实际是frame31进入资料页时继承的旧 `040D=FF`，当时还没有出现row0..9，名称不能作为“资料已绘制完毕”证据。真实完整资料画面与最终FF检查使用 `info-open`（frame272）；其间frame32..42观察row0..9。为保留原产物和hash，旧文件名、snapshot与JSON均不改。附加 [纯源码UI接口对照](../ui-integration.json) 也明确将旧FF例区分为early RTS及额外入口前缀，不算资料完成。

原RGB和48000Hz双声道16bit PCM由只读原ROM与锁定Nestopia libretro核心直接输出。恢复源码未安装到原核心；本回执没有源码CPU对照、内部CPU/NMItrace或源码独立波形合成的含义。两案只加载明确继承state再运行普通按钮，没有新增core RAM/SRAM、结果或ready写入。

首跑2915帧、两跑5830帧，46检查点；200份非空canonical产物逐项hash重复一致，另12份正式JSON计入其中。排除46份0B VRAM与目录路径metadata JSON。每帧完整RAM/SRAM/RGB/PCM哈希及完整WAV保留。

## 原战场武将资料：自然旧起点、B打开/A关闭

514帧，16检查点。起点：`analysis/phase11/runtime/cold-battle/battle-control-return.state`；准确继承来源：`analysis/phase11/runtime/cold-battle/validation.json`。

起点来自第十一轮无注入冷启动后的battle-control-return。none30、B2/none240打开原武将信息，真实battle1/sub1、040D=FF；A2/none240关闭，返回battle0/sub2。肖像和数字/姓名字段由原程序生成并消费，不注入packet或完成标志。逐帧040D仅是帧结束观测，未声称每个内部row都被观察到。

- [真实输入](battle-officer-info/input-plan.json)
- [逐帧UI/队列/字形/OAM与hash](battle-officer-info/frame-services.json)
- [图片检查点](battle-officer-info/checkpoints.json)
- [完整实际WAV](battle-officer-info/full-flow.wav)
- [首跑范围/原state来源](battle-officer-info/validation.json)
- [独立第二跑逐产物核对](battle-officer-info/repeat-validation.json)

## 普通攻击：旧明示起点、原後退输入返回

2401帧，30检查点。起点：`analysis/phase11/runtime/ordinary-attack-return/initial.state`；准确继承来源：`analysis/phase11/runtime/ordinary-attack-return/validation.json`。

起点继承第三轮唯一敌坐标准备的原state：0600敌X20→3、0614敌Y14→16；第十一轮只复制并公开来源。此轮使用完全相同普通输入/时长，所有旧检查点PNG/RAM/SRAM/state再次逐字节核对。命令设後退、原确认/结果后返回战场；不能称从自然战役无准备进入普通攻击。

- [真实输入](ordinary-attack-return/input-plan.json)
- [逐帧UI/队列/字形/OAM与hash](ordinary-attack-return/frame-services.json)
- [图片检查点](ordinary-attack-return/checkpoints.json)
- [完整实际WAV](ordinary-attack-return/full-flow.wav)
- [首跑范围/原state来源](ordinary-attack-return/validation.json)
- [独立第二跑逐产物核对](ordinary-attack-return/repeat-validation.json)

每帧额外记录040C..0417控制字节、0000..0012 scratch、0380..03BF packet、0310..0373队列、B8/B9肖像CHR页与完整0200..02FF OAM。packet可能在一帧内生产/消费，本目录不据帧结束字段推断不存在这些原步骤。母档载入与独立core内存poke明确区分，新增poke数量为0。

```sh
python3 scripts/capture_ui_service_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
```

[原核心汇总](validation.json) · [证据manifest](evidence.json)
