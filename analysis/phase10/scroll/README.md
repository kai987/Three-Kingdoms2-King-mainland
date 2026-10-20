# Phase10 地图行列滚屏请求

独立可读 `ScrollGraphicsServices` 恢复 physical23 A00C→A387 与 A00F→AB53。前者构造 BG tile 行/列请求，后者构造 attribute 行/列请求。源码不解释原6502/IR，不回退原CPU执行，不消费PPU队列，不绘制像素、不完成DMA/IRQ/NMI，也不清除等待标志。根线程的原核心画面与服务集成属于另外的证据层。

原NMI战场路径 fixed31 F923 检查 `0500<12`、`008F==0`，选择logical37/physical23/24，F937调用A00C，F93A调用A00F。本模块调用从这两个合法入口的函数体开始；外部bankcall映射与真实callerRTS由调用方维持。

tile服务比较相机X/Y的8像素缓存；X为FE/FF时先+2回绕。原代码先写0093/0092缓存，即使007E bit7/bit6已忙也不撤销缓存。一次调用可构造列和行。列取16个metatile、行取17个；初始半tile按原分支跳过，旧缓冲尾未写部分保留。跨垂直packed row15边界会额外推进unitY并切换真实E000数据bank；横向列15边界保留原nibble回绕。

attribute服务先算 `(cameraX-6)&FF >>3`，列变化优先并立即返回；只有列未变时才检查Y的16像素缓存。属性helper没有tile busy检查。8/9字节路径保留第九项合并回首字节的顺序、0002的临时mask，以及primary/secondary两个地图块属性的混合。secondary pointer读表不再写mapper，原当前window语义保留。009C bit6=1选当前primary列，bit6=0交换primary邻列；bit4=1选当前row，bit4=0选垂直前沿+A0与原F0 gap处理。

单位坐标按slot19→0扫描，同坐标最后保留较小slot；原代码不额外检查officer-ID或擅自过滤inactive。BG单位4tile复用已冻结 `BattleGraphicsServices.unit_tiles`；按原controller/strength/affinity取字形，且保存00/01指针。palette覆盖保留原四quadrant palette2及跨缝查找。header奇偶两分支原来都用20/23，本源码保留而不替ROM修正。A8FD/A91E单位路线在原CPU实际弹出两层return再进入对应quad绘制；高层源码恢复该分支的作用，空闲栈残留不属于合同。

最终 32768 个完整原CPU返回对照、另 2 个源域guard，0失败。矩阵覆盖27个X、24个Y、6方向组合、tile/attribute两入口、列/行/两者/不变、20unit同格覆盖；另所有256 busy值及连续camera/待处理请求。fixture明确在RAM0400放256个合法原chunkID描述符、相机/方向/单位配置由固定种子生成；它是受控CPU数据输入，不能称自然游戏可达。连续序列里每三步清007E是验证输入中的显式队列状态，不是源码假ack。原ROM始终只读。

对照完整8KiB SRAM、1940个声明RAM地址（全部非栈RAM，加0100..011F原palette区域与0140..01B3真实滚屏缓冲/单位tile数据）、有序E000端口请求、四PRGbank、AXYP及bodySP与原RTS后的SP关系。默认原CPUfixture SPFD，使真实调用栈不覆盖data缓冲；空闲栈残留与硬件周期不在合同。动态观察1164/1236个服务指令地址，是指令位置覆盖，不宣称所有值域/分支、PPU消费或完整NES帧。

```python
scroll = ScrollGraphicsServices(memory, GraphicsData.from_rom(rom))
result = scroll.tile_scroll(registers=registers)
result = scroll.attribute_scroll(registers=registers)
```

`registers=`接受a/x/y/p/sp对象，原AXYP末值会同步写回，SP不变。结果 `registers` 与 `contract_registers` 均是AXYP字典；`status='returned'`表示函数体完成，实际callerRTS尚由外层处理。`requests`列出本次构造请求；`PPU_queue_consumed=False`明确保留消费者责任。无动作/忙等待仍是原合法RTS返回；invalid chunk/单位数据域抛出明确异常，不替其构造成功。

- [独立源码](../../../source/recovered/scroll_graphics_services.py)
- [冻结验证与pins](validation.json)
- [机核原bytes证据](evidence.json)
- [原范围反汇编与数据表](original-ranges.asm)
- [观察到的执行指令位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_scroll_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_scroll_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
