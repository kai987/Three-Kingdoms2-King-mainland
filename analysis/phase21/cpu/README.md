# 保存点后的独立原CPU有效地址观察

本工具从实际保存的PC/SP/AXYP、实际MAP四银行和N163寄存器image开始，没有设置新PC、caller、RNG、request、ready或结果。3个上下文共执行101157条原指令，全部停在原请求FF。这里只是独立原CPU continuation；没有调度新增NMI/IRQ，不是原Nestopia内部CPU trace，也不把这些准备指令增加到源码差分case数。

原20正式10479保存点来自未改原核心；本轮10491/10492默认使用`runtime/original-control`的全冷原核心保存点。`observer-accept`同帧state与其字节相同，且观察核心/重建控制/原核心三组各fresh双跑的RGB、PCM、2K、8K和wholeState每帧一致，由runtime域另行证明。独立CPU使用明确硬件输入：PPUSTATUS=0、APUstatus=0、NamcoIRQ读127、两手柄无键；它不补硬件就绪中断。

观察保留全部7723次城市记录访问，而非只保留有意义的结果。每行有原physicalbank/PC/ROMoffset、实际有效地址、city归一偏移、读写前后值、Y、零页base、当前代各指针低/高字节producer与实际JSR链。保存点之前形成的指针writer为null，不猜前代来源。共5次辅助字段访问都来自10:BD97，实际20/21=6040、Y=1、city2 offset1读0；其LE16门槛的另一字节是city+2，不能据此命名+1。没有观察到28..31的专用访问，不据有限窗口宣称unused。

10491从PC C56A/X4继续1842条原指令后形成真正C71A入口caller，随后扫描237记录；10492保存点本来已在C724/X66，只剩171记录。后者不能计成另一个完整237扫描。三条独立continuation均未进入C732/E89A内部招募随机调用；原记录状态无status0在野将，不构成成功录用实证。

`actual-callers`共5个入口输入，用原前序形成的真实栈、RAM/SRAM/N163/寄存器和银行交给独立源码差分矩阵。它们不是人为seed-return。C71A输入来自本轮原核心10491点；A000/C5B9/C5D2/C6CC输入保持原20正式10479来源。源码比较另见`../recruitment/validation.json`，此域source cases为0。

```sh
.venv-trace/bin/python scripts/trace_city_auxiliary_runtime.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[轨迹摘要](runtime-trace.json) · [hash证据](evidence.json) · [完整原机观察](../runtime/README.md) · [具名源码差分](../recruitment/README.md)
