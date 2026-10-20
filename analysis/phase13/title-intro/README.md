# 阶段13：标题开场五阶段图形服务

原10D72A（titlemain0）经EE07 selector37调用physical23 `A021→24DE25`，原stub `4C25DE`。它是五阶段开场timer／OAM／palette／音频请求服务，不是整帧图形仿真。独立TitleIntroGraphics为8个具名函数、86个原指令位置、1个五项inline分派；全部本地位置动态执行86/86，静态结构缺口0。源码不解释opcode、IR或program.json，不执行原CPUfallback，也不调用未知callback假RTS。

|0541|原入口|作用|
|---:|---|---|
|0|DE44|0544递增，达到32后准备palette／cursor0／每帧停留2ticks|
|1|DE66|原24项frame序列；cursor20发E693(62hex)；F25F33／F1AD真实OAM；遇FF进入64ticks停留|
|2|DEB9|timer递减，非零继续frame8；零进3|
|3|DEC7|phase++，0115..0117变0F|
|4|DED6|0540++、清phase/timer等、真实E57Freset和E673(B0hex)请求|

0081bit3原Start使phase3先执行，且本调用结束后phase4；不能写成立即跳完全部初始化。原byte timer0的递减／FF的递增保持wrap。原序列是24个frame索引加FF终止，映射15个原sprite descriptor；每项4byte sprite（Y/tile/attribute/X）以80终止，本证据pin所有真实descriptor，而非根据屏幕猜动画名称。

复用已冻结SceneSharedServices、BattleGraphicsServices和AudioServices纯源码。F1AD构造OAM RAM，F25F写真实E000端口；E57F有原APU/N163复位写，E693从ID62hex请求3个连续descriptor，结束E673(B0hex)请求7个连续descriptor。请求／OAM并不等于硬件DMA、声音PCM或像素渲染完成。

最终3120原CPU完整返回病例、另6sourceguards，0失败。覆盖5phase×3原button条件×8timer边界×24cursor、24cursor×7OAM容量、3真实SP／flags边界。准确比较范围为固定1972RAM地址`0000..01B3`和`0200..07FF`，包含palette0100..013F和单位缓冲；另逐字节比较实际调用方拥有的`entrySP+1..1FF`，本矩阵2..12bytes、合计1974..1984RAM。共享音频模块从phase10起已明确排除其inactive CPU stack残留，本服务保持该合同，不stamp残留来假装all2048。AXYP/SP/PC、8192SRAM、所有端口写序和mapper banks保持精确比较。

```python
owner = TitleIntroGraphics(memory, TitleIntroData.from_rom(rom))
result = owner(actual_ServiceCall) #actual23/24pair andrealRTS frame
```

- [独立完整具名源码](../../../source/recovered/title_intro_graphics.py)
- [原CPU矩阵、明确RAM地址与pins](validation.json)
- [code、inline／sequence／sprite data与服务合同](evidence.json)
- [原字节和明确data](original-ranges.asm)
- [原CPU实际执行位置](executed-instructions.json)
- [静态五phase闭包](static-control.json)

```sh
.venv-trace/bin/python scripts/verify_title_intro_graphics.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_title_intro_graphics.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

完整服务返回不等于完整NES帧；source硬件等待／未知callee仍须实际服务，不提供ready或IRQ虚假完成。
