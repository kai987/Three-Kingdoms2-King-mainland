# 实际保存点到门槛调用的独立原CPU前序

[trace.json](trace.json) 从阶段23六组正式 `original-control/actual-frame-003.state` 的实际 REG/MAP/N163 开始，每组无新增中断地执行原ROM，导出 24 个真实已到达调用输入：每组 BD7A、BD90返回点的D105、其D126返回点的D69D，以及真实D36F支付入口。原始输入在 `actual-callers/entry-*`，每个目录保存 context、完整RAM/SRAM/N163。

自然组4输入的 origin 为 `actual_Native_snapshot_originalCPU_reached_caller`；其余20输入为 `diagnostic_Native_snapshot_originalCPU_reached_caller`，明确继承 Native 金额/不明+1准备。`additional_CPU_prepared_numeric_bytes=[]`，新NMI/IRQ数0；没有构造caller、PC、RNG、request或ready。硬件端口输入明确固定 PPUSTATUS0/APUstatus0/NamcoIRQ127/双手柄0，为独立原CPU软件观察条件。

六组首个城市2 BD97 均在前序第2528指令；BD7A在第2381指令。过门槛组再次评估并实际补到兵1000、库存7799。原CPU后续预算18（拒绝组20），而原核心帧5刚补兵时预算28；两者终点不同。独立原CPU没有后续NMI/RNG时序，因此例如天然组最终金8853与原核心8850不同。只声明门槛及补兵效果对应，不声明整个request/帧/最终金一致。原核心 +1 读取有被动观察证据，瞬时 +2 解释同时依赖原字节与独立CPU，不能将它冒充同一原核心bus观测。

这里 Source CPU比较案数0，非 Native 内部逐指令trace。24个输入在独立 [Source验证](../threshold/validation.json) 中逐案做完整服务差分；前序指令数、导出数及Native双跑均不重复计入 Source父案。

来源固定为阶段23正式runtime六组；自然母档继承阶段22实际野外录用后兵700的保存点。未修改旧阶段、原ROM或原核心。
