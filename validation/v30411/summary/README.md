# 三國大陸戰役 V3.0.4.1.1 验收

先看 [固定需求与实际扣粮](docs/fixed-state-acceptance.md)、[南方八城](docs/baxi-replay.md)、[剩余退化](docs/remaining-regressions.md) 和 [验收问题答复](docs/acceptance-answers.md)。

- [阶段准入](checks/stage-status.json)记录固定需求、资源对账、历史规则比对和性能门槛。
- [历史运队](docs/historical-transport-review.md)列出实际回放窗口、终止回执、期末在途及原先保留的证据。
- [技术检查](checks/technical-checks.json)记录运行结果和日志名称。
- [实验清单](checks/experiment-manifest.json)与[输入清单](checks/replay-inputs.json)记录源码、配置、原始存档哈希和随机种子。
- [文件索引](file-index.json)与 [SHA-256](SHA256SUMS.txt)可逐文件校验。分包和各自的校验记录放在[归档目录](../archives/)。

正式战役的运输统筹配置仍为默认关闭。此版验收在固定需求及历史运队阶段保留未达标结果，长期矩阵和新保留种子标为未执行。
