# WP08：真实调用者续程与SP00反例

本包完成一个有界验证：从完整的原模拟器E066软件快照出发，声明一次软件NMI，经过原入口和城市场景调度，真实执行 `F8B5→EE53、F8B8→F206、F8BB→FB0B→EAF7、F8BE→EC67`，停在F8C1首条指令之前。另从旧SP00夹具的真实palette返回处续行，得到实际非本地返回0FC1并停机，没有修PC或SP。

3个有限案例、14对原JSR/RTS（13正常、1非本地）、1241条原ROM CPU指令、6次Source推进通过对照。8次成功2002读取；1次bit6等待、2次无输入且无状态进展的续程，其中1次严格保留整个generator链位置。56对完整保存点覆盖2K RAM、8K SRAM、16K原始PPU sink及设备/REG/银行JSON。新Native运行0；本包不声称全NMI/RTI或整局游戏完成。

## SP00从哪里来

SP00来自早期EE07矩阵 `all_SP_values/0000` 的显式测试轴，RAM/SRAM由公式生成。它沿phase0→phase1 step01→WP07第一次palette返回保留下来，是受控fixture，不是自然原机栈。当前导入WP07 offset79872的完整26KiB状态，SHA256 `fa808f7eec2b44045cfe3ed8e27a3fead6edd44601ce9a771549fb20fb0901cb`；PC原本就是F8B8，未取此前第二次跳回F8B5的后态。

该状态实际执行F8BE JSR EC67时，返回高F8写入0100、低C0写入01FF。EC67重算palette的ECB9又把0100写成0F；ECBE真正RTS消费C0/0F，实际目的为0FC1、SP00。Source和独立原ROM CPU一致，停在0FC1执行前。这只说明该人工栈上下文不适合继续这一调色路径，不能称为Native游戏故障。

## 完整来源及证据等级

所查WP05的122份完整软件快照和265872条选定总线事件，没有保存F8B5/F8B8/FB22/EC67的同一瞬间完整scene2现场。此结果只限观察hook的选择范围，不能当成这些指令从未运行。旧WP08 run05属于scene3；其EC67选定寄存器检查点没有同一时刻完整RAM/SRAM，不能拼接来替换SP。

采用WP05 frame383的 `callee-0122-E066`：全10KiB SHA256 `a92e590d49aa56de45a66f5751200fe306515a11ebc9fee9523d146042c74a9b`；REG E066/A90/X00/Y00/PE4/SPFF、PRG[2,29,30,31]，global2/NMI2、7D/7E=01/00。所有软件内存、寄存器和银行完整保留。它与旧64B待传queue不同，未移植任何旧queue或SP。

每个正例显式触发一次软件NMI：原PC/P三字节中断帧、F800保存AXY三字节均真实形成，scene基准SPF9；原指针00/01=F8B5后，以可读源码补足F878 JMP($0000)语义。后续每一调用都要求实际PC恰在原callsite，并核真实返回PC/SP。EC67的计时器8A由4减至3，走提前返回，真正RTS到F8C1/SPF9。NMI外层仍在栈上，未执行F8C1或后续恢复/RTI。

证据等级是“Native完整软件快照→明示软件NMI派生→原调用链”，不是捕获到的自然F8B5现场或真实硬件NMI时序。

## FB22等待与设备合同

FB22是BIT $2002，FB25是BVS回FB22，检查bit6，保留A并设置N/V/Z。80虽有bit7置位但bit6清，正常退出；40会等待。等待案例在真实BIT+BVS返回FB22后对齐Source暂停；下一读缺样本时停在BIT之前。第一次由sprite-hit等待转为缺输入等待只声明无模拟状态进展；第二次重试还核同owner、整条generator及位置不变。只追加预锁80样本后，在同对象续行并真实返回。

复用既有ServiceMemory，有序保存PPU/CHR/nametable/mapper/N163计数器命令。4014记录完整256字节DMA请求和OAMADDR；不因此获得实际OAM传输、DMA停顿或周期信用。fresh设备状态另行声明，未捕获的PPU/APU/N163瞬态未由软件快照补造。缺少vblank产生/读后清bit7、开放总线、物理镜像、6位palette掩码、周期、IRQ调度和渲染/音频模型。

新适配器只补F878控制流语义、严格调用者校验和观察；所有业务算法仍来自既有battle_nmi_services.py的nmi_body、pending_ppu/palette_upload、chr_banks、nametable_banks/scroll_control、palette_fade。旧生产源码未改，无CPU/IR作为Source回调。

## 验证材料

- [可读续程源码](continuation_adapter.py)、[来源链](source-provenance.json)、[有限来源搜索](finite-source-search.json)
- [预锁范围](family-scope.json)、[3案矩阵](case-matrix.json)、[设备合同](device-contract.json)、[验收pins](acceptance.json)
- [执行输入及hash](run-01/execution-inputs.json)、[运行结果](run-01/validation.json)、[逐指令与调用证据](run-01/parents.jsonl)、[完整保存点索引](run-01/points.jsonl)
- [独立离线前缀重建](semantic-validation.json)、[实际返回证据](actual-continuation-evidence.json)、[工作包增量](work-package-delta.json)、[最终封存](verification.json)

离线审计从初态和实际软件/端口写前缀重建全部保存点，复核真实压栈、BIT flags、RTS目标和完整DMA bytes；该审计没有再次执行Source、CPU或Native。

## 仍未闭合

本包增加scene2相邻调用、bit6等待恢复及SP00非本地返回的明确证据。它没有替换此前同一个64B包的受控PC重入，也没有连接旧queue到新Native122上下文。该路线仍有3项明确前提：旧64B queue与兼容的实际/派生NMI入口；F8C1之后直到下一消费者的真实scene/NMI续程；兼容设备现场和时序。3是本路线前提数，不是全局未知服务数或剩余轮数。

分类账1526=1203/80/243、remaining323，raw345=104/13/228均不变；城市+1及+28..31正式字段名仍null。155个已知EE07 caller、跨包覆盖2个、外部153的口径不变。239563旧路径前后冻结。未发布、推送或分发ROM；完成此包后停止，完整WP08和整游戏仍未完成。
