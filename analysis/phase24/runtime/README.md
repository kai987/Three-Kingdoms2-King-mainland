# 阶段24：原配兵界面的指针生命周期

本轮只选G086配兵链。导入阶段14自然冷启动案的`action1-allocation-ready.state`，祖先与本轮均零数值准备；这是存档续行，不冒称重新冷启动。普通无键等待、Down两次、Right、Left、Down至结束、A，182帧后原城市状态回到0/1。ID30兵800→900→800；工作预备兵9999→9899→9999。提交后工作缓冲另被复用，不能将其末值10115解释为城预备兵；完整城记录与原武将记录另存。

[总证据](evidence.json) · [回执](validation.json) · [指针实例](pointer-lifetimes.json) · [构建](core-provenance/build.json) · [独立补丁](core-provenance/observer.patch) · [脚本](../../../scripts/capture_native_pointer_lifecycle.py)

原ROM与固定原核心、阶段21核心未修改。独立阶段24核心只加被动hook与外部静态日志数组，没有改CPU/board对象布局；直接const复制物理RAM与WRAM，不触发额外仿真总线读取。两种核心各fresh进程双跑，逐帧完整RGB、48kHz PCM、2048B RAM、8192B SRAM和未归一化完整serialized API buffer相等。包括相同首次serialize查询时机与导入日程。`repeat-artifact-checks.json`保留全部非空复跑文件hash。只有新观察核心具内部事件，不能追认原核心有内部trace。

原NMI短暂映射physical27/28；帧末主循环通常已恢复16/10/11/31。因此每事件使用真实opcode PC及实际PRG页，另存bus时CPU.pc，不能从帧末银行推断事件银行。36-u32原始ABI逐条由公开decode_event解码并复核连续序号；完整布局见observer/event-schema.json。PokeRam/PokeBus覆盖物理镜像RAM00/01写，城市辅助总线访问与配兵范围SRAM总线访问分列；虚读与真实指针语义必须分别解释。

两次F2AF输入city11建立6160；Y=17+row2=19取原名册ID30，F2D7建立武将指针6528。D987先将00/01保存至10/11，再重用01/02作为除法参数，临时wholepair不是可用武将指针。EA7C本身不写00。D9F0前恢复6528，之后才访问武将+8/+9。两次实际D987入口/RTS前SP分别F1/F3，原返回word分别D839/D880，不注入哨兵栈。这里只证明两个实际实例。

D64A/D987入口稀疏保存完整2K/8K，与AXYP/SP/PC、4实际PRG页和原栈字节关联。`snapshots.bin`每条10240B，`snapshot-index.jsonl`与事件sequence交叉引用；四份action-bearing callee导出同名JSON/RAM/SRAM便于独立源码对照。未捕获瞬时N163/PPU/APU内部状态，不能补造该硬件上下文。Source/CPU验证另列，不计入本轮Native病例。

每个实际新帧保存state/RAM/SRAM；13张原256×240PNG与原48k立体声WAV可核，未生成替代图声。城市+1与尾4字段仍无正式命名；本短路线未观察到它们的专用写入，不能由零事件证明unused。本轮不重跑祖先长历史、不复制原ROM、不改任何旧阶段产物。
