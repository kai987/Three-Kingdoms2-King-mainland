# 第10阶段：战场图形请求与计略动画消费者

`BattleGraphicsServices` 独立恢复完整 physical13 D6CC地图刷新、D657光标、DC63/DC70高亮及固定F092/F1AD OAM构造。另补全真正的计略动画入口 physical25 A00F→26CFD6：16项计略映射到11个visual class，5个准备子状态、176次动画计数、真实portrait/sprite/palette命令与收尾音序。没有解释IR、执行原ROM opcode、图形空函数或自动ack；不是原作者源码。

## 调用与精确边界

```python
graphics = BattleGraphicsServices(shared_memory, GraphicsData.from_rom(rom))
result = graphics.map_refresh(GraphicsRegisters(a=17,x=23,y=31,p=32))
result = graphics.cursor()
result = graphics.highlight(alternate=False)
result = graphics.animation_tick()  # 真实NMI调用点的一次工作，无伪造frame
```

基础三个服务与两个renderer回传实际A/X/Y/P，供外层执行真实RTS/pop；没有改CPUstack、SP或PC。计略动画的内存/端口完整返回，最终CPU寄存器临时态明确不在合同；不能把它自动当作旧CPU控制器的寄存器等价hook。共享memory的真实io_write/普通索引记录PRG/APU/N163写入；没有默认硬件读。

D6CC只建立0380..038E的15B请求：两行各2tile、一个attribute byte和FF终止。原007E只OR4，不消费队列。先读当前chunk，odd camera横向拼缝时才合并邻chunk属性；reverse20槽叠加palette2，0012为0时跳过selectedunit。非零则按单位兵百位缓存0..10、所在ruler controller和0628适性生成4B单位背景图块。读取完整真实数据窗、更新E1与端口顺序，保持EE07的58..5D/E2/E3协议及rawselector别名。超视口早返亦复现寄存器/flags。

光标F092把世界坐标转换为屏幕OAM，含y借位16byte间隔、镜像预调整、负X少1的原公式和先写后裁剪的部分OAM。007C为FF会早返；分配回绕时world与screen路径最终flags不同，已独立核对。高亮先写0A/0C，再按5E.bit4闪烁跳过或追加屏幕sprite。没有4014DMA、PPU像素或frame时序合成。

## 真正的16项动画

NMI F93A调用physical23 A00F→AB53，是scroll属性更新；F937的23A00C→A387是scroll背景行/列命令。它们不读04C8，仍由独立scroll服务恢复，本文件不把它们标作动画或单位OAM。

真正动画在F945的selector39：25A00F→26CFD6。初始04C8=tactic+1保存原ID；准备80执行panel/数字/图块/调色板/音序五子状态，再进入81。16→11映射为 `[1, 8, 3, 4, 2, 1, 7, 4, 6, 10, 5, 4, 2, 9, 1, 0]`。11类都有独立可读handler，使用真实frame表与sprite records，并保持byte计数、双层sprite、颜色循环、portrait和OAMcursor。

0300或0304没有真实FF时直接等待；source不写FF完成它们。只有原04D0恰好达到B0的有效分支才清04C8，构造背景清除/标准palette/音序请求。这是原软件状态推进，未表示异步PPU或声音播放完成。音频调用复用独立`AudioServices.reset/request`，不调用旧RuntimeServices IR；结束标准palette用实际far3DA015→30DBB1的mode1数据复制。对应16动画序列每项191次原服务返回，15次准备+176次动画。

## 原CPU验证与来源

最终 **4596 次原CPU完整返回、4 source guards、0失败**。其中基础1520例严格比较A/X/Y/P；16条动画顺序共3056次返回，20例inactive/jobwait/init返回另列。完整8KiB SRAM、1828B RAM、bank映射和真实端口写序相等。RAM含全部非CPUstack字节，以及真正palette0100..011F和unit tile scratch01B0..01B3；其余CPUstack残余、SP/PC及animation寄存器排除。

顺序CPU输入每次将007C明确设0作为原NMI的OAM初始条件，0300/0304最初FF，不替软件确认。没有运行队列消费者、IRQ/NMI/video/PCM，也不把3056calls说成3056真实NESframes。全16路径、11visual类、起始/最终byte、常规和极值视口/翻转/裁剪/full OAM、ruler/适性/兵百位差异分别核对。

`evidence.json`固定原CPU范围、EE07/EADE内联数据、chunk/metatile/帧sprite及不可变ROM数据SHA；现有REA定位证据亦固定。`executed-instructions.json`的rom_offset明确包含16B iNES头，与原文件位置一致。validation固定源码与validator hash；不会把有限动态覆盖声称为所有分支证明。

```sh
.venv-trace/bin/python scripts/verify_battle_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_battle_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
