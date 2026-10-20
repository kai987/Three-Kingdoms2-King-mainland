# Phase10 独立音频请求与逐tick驱动

`AudioServices`恢复固定31 E57F reset、E609与连续request包装，以及physical14 A003→15 D8D4完整11槽音序驱动。它读取原183个descriptor、bank2/3音乐命令和bank15数据表，不解释6502/IR、不调用原CPU、没有原ROM执行fallback。输出是精确APU/N163/mapper写请求与玩法RAM；它不合成波形/PCM、音频播放、时间或IRQ。真实Nestopia的WAV属于根线程另行捕获的原核心证据。

E6C6是4016/4017双手柄读取与0081/82新按键计算；E70E是palette2007上传。两者的原bytes在本目录明确作为context，而没有冒名为音频tick。真实NMI尾FAE6选择logical2E，FAE9调用A003；驱动将数据window映射physical2/3。

183个4B描述符包含slot offset、logicalchannel、指针low/highMinus40；E609替换该槽时会按旧APU类型更新07F6/4015。E66B/E673/E67B/E683/E68B/E693/E69B依次请求8/7/6/5/4/3/2个连续descriptor，E609请求1个。原table边界以第一个真实音乐header82DC确定；源拒绝将后续音乐byte假装descriptor。

驱动使用11个22B优先级槽，8种logicalchannel：2pulse、triangle、noise与4个N163。活动槽推进tempo/duration、volume slide、vibrato、envelope、word命令、循环与note/rest；07F2抑制后续同channel端口输出，不抹掉已更新状态。reset保留原11槽两字段清理顺序、APU寄存器请求、64零字节/32wave字节/4N163长度字段/音量字段上传与最终A5/F800=4C。

原quirks保留：B计数到0仍重建F0/F1；AD0重入scan后额外合并末槽mask（末槽inactive也会）；AD非0改F1但保留F0，可能读取RAM；N163 octave借位与上档shift5不修；0712缓存clamp发生在原periodlow已写端口之后。DCD8振音没有N163端口特判，会请求4012/4016/401A/401E；4018..401F只记录原写入，不编造其音效意义。

计略16ID通过26 D549选择11种visualclass，再查D751音序：88→E683/5、95→E693/3、8D或91→E68B/4，均先reset。等级提示12 AB49请求7B/E68B/4；后续12 AB67及动画结尾26 D416恢复1D/E673/7。数字是原请求ID，不是假定正式曲名。完整映射和原偏移在[evidence.json](evidence.json)。

最终 15857 原CPU比较 = 15856 完整返回 + 1 真实B0循环前缀；另 4 源码guards，0失败。原183序列各40tick、5组多channel各128tick、全部160 note/rest byte×8channel×2变体、14种显式RAM控制命令连续8tick、5入口×所有256 SP，以及重复channel优先级冲突均检验。比较全部非栈2KiB RAM、完整8KiB SRAM、写端口顺序、N163128B寄存器图与AXYP/bodySP。显式RAM音乐fixture不是自然战役可达证明；原ROM未改。原CPU自由栈残留字节与周期/PCM不在该语义合同。服务静态663条指令地址中动态观察663条，不等于所有值域/分支组合、曲目长度或完整NES帧均已验证。

`registers=`可传现有a/x/y/p/sp对象：末值在实际caller RTS之前，源不植入0200返回、不弹callerframe。reset末A4C/X7F/Y3/NVZC=40；request末A/X为原X、Y3、flags按真实最后ADC/PLA；tick末AF2/XDC/Y末channel/NVZC=03。真实caller返回仍由调用方保持协议。验证用decimal-cleared py65上下文，源码按NES2A03二进制算术。budget前缀明确无returned registers、无假note/end/ack。

```python
audio = AudioServices(memory, AudioData.from_rom(rom))
audio.reset(registers=registers)
audio.request(0x1D, entry=0xE673, registers=registers)
result = audio.tick(registers=registers, command_budget=4096)
```

- [独立可读源码](../../../source/recovered/audio_services.py)
- [原CPU回执与最终pins](validation.json)
- [逐段原bytes及数据表](original-ranges.asm)
- [实际执行指令位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_audio_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_audio_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
