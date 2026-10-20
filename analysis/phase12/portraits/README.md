# Phase12 肖像实际服务

physical25 `$A000`只跳转到physical26 `$CE1F`，实际构造两层绝对屏幕OAM肖像，不是数字属性资料卡。独立`PortraitUIServices`用具名Python函数/条件/循环和真实callerowned generator执行；运行时不解释opcode/IR、不读program.json、不调用原CPU或空renderer。原ROM只作immutable数据。

`0000`选择武将，`X&1`选择左/右CHR缓存B8/B9及tile加00/40，`000A`是Y，`04BC`是Xoverride（0→16，用后清0）。`A4`低3位选择帧，bit7强制普通嘴部；SRAM6FEA bit2强制帧3，bit3再强制帧4。主体14个sprite，再加嘴部6个；固定F1B7保留caller03tileoffset/04cutoff160/02attributeXOR，不能用F1AD的清03/04前序替代。unsigned坐标/索引/溢出、FF满OAM、80descriptor终止全部保留。

原F25F写E1=33及E000=33，mapper将33映射到physical1资料窗。237肖像分别映射62个1KiB CHR页；baseindex0/5/10/15与五个正规帧构成20pointer条目。B8/B9只是CHR缓存，真实IRQ之后才写9000/9800。此入口不请求palette、文本包、数字参数卡、OAM DMA或完成PPU绘制。父EE07的银行保存/恢复在callee之外，服务只消费原callee现有RTS帧。

普通嘴部与说话嘴部严格使用原谓词：A4bit7clear、7Ebit0set、0304非FF、0303为0、5Ebit3set。任何一个不成立使用普通图形。237..255字节ID原程序会读相邻data，源码保留这些行为但不把它们称作额外武将；低3frame5..7也可能读下一组/相邻bytes，不能称正式姿势。

最终5869原CPU病例（5867完整RTS、2真实循环prefix）和6单列guards，0失败。包含全部237身份×两槽×五帧×两嘴部、完整五谓词和6FEA覆盖顺序、signedA4、坐标/裁剪/溢出/OAM边界、相邻ID、F1B7任意caller参数，以及3个原attack CPU实际callee帧；后者保留原寄存器/SP/返回栈，无stack准备。这些原CPU捕获来自明示条件矩阵，不是native核心内部trace。生产外部原CPUhelper数=0。

逐字节对照全部2048RAM（含CPUstack残留）、8192SRAM、AXYP/SP/PC、mapper与端口序。缺失终止/无法饱和的原循环真正停pending并可同owner续跑，不fakeRTS；源码guard检查unknownentry、真实caller/mapper、pending重入和unknowncallee。图形的请求范围不等于一帧NES硬件执行。

```python
owner = PortraitUIServices(memory, PortraitData.from_rom(rom))
result = owner(actual_ServiceCall)  #真实caller register、SP、returnPC
# 或owner.run_entry(0xA000, actual_registers)
```

- [具名独立源码](../../../source/recovered/portrait_ui_services.py)
- [CPU回执/guards/pins](validation.json)
- [原bytes、CHR数据与REA来源](evidence.json)
- [代码与明确data反汇编](original-ranges.asm)
- [全部237身份、五帧及模板映射](identity-mappings.json)
- [姓名/肖像像素诊断图](portrait-identity-atlas.png)：原2bpp数据/模板灰度解码，不是真实截图、原palette或OCR；数字是ID/CHR页。

```sh
.venv-trace/bin/python scripts/verify_portrait_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_portrait_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
