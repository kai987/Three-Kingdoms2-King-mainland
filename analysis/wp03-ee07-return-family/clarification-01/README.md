# EE07 已封存结果的证据口径补充

本说明追加于最终封存之后；不修改原34项artifact manifest、原verification、执行输入、脚本或任何测试结果。不新增 Source、CPU 或 Native 执行。

1. 初态中当前调用之外的栈字节只是已声明公式生成的 fixture。没有另行构造或消费外层返回帧，也没有验证它们来自真实上层 caller，不能称已确认真实 outer return。当前 A06F/A077 的 JSR 帧、EE07 五字节 far frame 则确由本轮原 ROM 指令构造；Source 独立复现同一协议。终点仍是 EE52 RTS 后、A074/A07C 首条指令之前。
2. “2次缺 callee”是受控回归测试：测试程序故意扣留已经恢复的精确 Source owner，再提供仅声称 returned 的结果，检查它不能越过真实 PC/SP 合同，最后恢复真正 owner 各执行一次。它们不是本轮发现的真实未知 WP07 服务；选定窗口没有因此产生 WP07 语义缺包。
3. 动态断言仅确认同一个 pending callee ServiceCall 对象。没有额外宣称同 owner、同 generator 或其指令位置的对象身份已被动态断言。

结果保持：656个Source/CPU父案例（主路径328、busy分支328，扣留测试包含其中），54,120条原CPU指令，三个阶段双方分别保存完整2K RAM+8K SRAM；外层RTS与新Native均0，字段和raw分类均零迁移，正式城市字段名仍为null。

原始来源：[预锁初态与矩阵](../case-matrix.json)、[执行器与Source pins](../run-01/execution-inputs.json)、[Root逐案结果](../run-01/cases.jsonl)、[严格callee恢复测试](../strict-callee-resume-evidence.json)、[原最终封存](../verification.json)。本说明只澄清证据范围，不增加执行信用。
