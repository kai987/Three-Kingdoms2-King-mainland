# 配兵原调用输入

四个D64A/D987入口输入由新被动观察核心在真实JSR入口直接复制2048B物理RAM、8192B物理SRAM，并记录AXYP/SP/PC、实际四个PRG页和已有返回栈；原游戏内存、寄存器、PC和返回帧未准备。该观察版另与固定原核心走同一路径逐帧五buffer严格相等，不能扩称全部运行下等价。

没有瞬时N163/PPU/APU副本。每个 `context.json` 明确 `N163_origin=explicit_shared_fixture_not_Native_snapshot`，Source/原CPU共同使用128B非零模型图、address127/autoincrementTrue，并验证完整不变。它是明示设备输入，不是原核心当时音频状态。模型端口输入及双手柄0另列；捕获RAM81保留真实左右按键。无新NMI/IRQ、无伪caller和数据ready。

这里只导出来源，不增加Source CPU案例。独立源码矩阵与Root调用层整合各自引用这些输入和声明scope；观察events是稀疏原机边界，而不是完整原核心逐指令录制。
