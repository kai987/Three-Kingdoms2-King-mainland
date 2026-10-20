# 固定音频reset/request的真实caller协议

[ExactAudioRequests](../../../source/recovered/exact_audio_requests.py)独立恢复固定31 E57F reset、E590硬件配置、E609 descriptor载入及连续请求入口。生产是手写具名函数和循环，不执行原CPU/IR；旧AudioServices、SceneShared和phase15音序正文不改。原E5FA/E5FB/E5FF/E607的PHA/PLA和每次真实JSR留在原栈，包括原玩家战后反馈曾在01F5..01FB留下的字节。

E673载入连续7项、独立入口E67B为6项、E683为5项、E68B为4项、E693为3项、E69B为2项，E66B为8项；每次加1为原8bit wrap，最后真正tail E609。E57F先载入descriptor0..6再关闭全部11音槽、写APU及N163初始化数据，最后写A5/F800=4C。E609通过真实F25F选择physical2，读4B记录；已有active APUchannel0..3先清4015对应位，然后替换slotchannel/streampointer/state。N163寄存器图和端口请求都是真实软件写入；没有合成PCM或完成音乐。

唯一外部软件依赖为E60B→F25F，已有独立固定源码。API要求实际AXYP/SP/PC及既有callerword，不能seed返回；未知/未实际返回的F25F保持同一ServiceCall与generator。预算也保留真实位置，需显式正预算才能resume。

另[实际caller回执](actual-callers.json)保留19个原JSR音频入口，来自正式玩家Native内存的受控原CPU A00C前序，包括reset内部嵌套调用；原parent1137步仅为上下文生成，不另加Native父案或视频帧。它们不是Nestopia内部CPU trace，与主体矩阵单列。

原CPU矩阵 2767 例：2765完整真实callerRTS、2严格前缀，另10源码guard，失败0。全部2048B RAM（闲置栈也包括）、8192B SRAM、AXYP/SP/PC、银行、端口读写序与N163图逐byte一致。静态146位置、动态146，剩余位置在evidence列明。Descriptor0..182为已确认游戏数据；bytewrap扩展病例与正常音序入口范围分别列在回执，不由极值fixture声称自然曲目/音效。

```python
owner = ExactAudioRequests(memory, rom, services=exact_fixed_services)
owner.run_entry(0xE683, registers=actual_caller)
owner(actual_ServiceCall)
owner.resume()  # 同一真实caller，等待依赖完成
```

```sh
python3 scripts/analyze_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --genuine-only
python3 scripts/analyze_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[原汇编](original.asm) · [静态来源](static-catalog.json) · [CPU回执](validation.json) · [最终pins](evidence.json)
