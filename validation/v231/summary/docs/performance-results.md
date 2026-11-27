# 同一状态的预报性能

从四份真实检查点各重复三次。每次从固定存档开始并清空预报路线缓存，观测开关各独立测试。输出全旬 CPU 与墙钟分位数、新预报调用、缓存命中、搜路次数、候选数和进程峰值内存。开关观察的同一策略核对最终游戏状态与随机数。

| 检查点 | 剧本 | 观察 | 组 | CPU P50 秒 | CPU P95 秒 | 预报调用 | 缓存命中 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| terminal-save.json.gz | 184-02 | false | F2 | 3.834 | 4.402 | 0 | 0 |
| terminal-save.json.gz | 184-02 | true | F2 | 3.847 | 4.846 | 0 | 0 |
| terminal-save.json.gz | 184-02 | false | F4 | 4.007 | 4.586 | 2268 | 423 |
| terminal-save.json.gz | 184-02 | true | F4 | 3.824 | 4.667 | 2268 | 423 |
| terminal-save.json.gz | 208-10 | false | F2 | 1.441 | 1.840 | 0 | 0 |
| terminal-save.json.gz | 208-10 | true | F2 | 1.569 | 1.887 | 0 | 0 |
| terminal-save.json.gz | 208-10 | false | F4 | 1.465 | 1.758 | 2217 | 465 |
| terminal-save.json.gz | 208-10 | true | F4 | 1.551 | 2.040 | 2217 | 465 |
| north-snow.json.gz | 184-02 | false | F2 | 0.609 | 0.788 | 0 | 0 |
| north-snow.json.gz | 184-02 | true | F2 | 0.609 | 0.660 | 0 | 0 |
| north-snow.json.gz | 184-02 | false | F4 | 0.594 | 0.673 | 135 | 9 |
| north-snow.json.gz | 184-02 | true | F4 | 0.615 | 0.660 | 135 | 9 |
| cross-month-convoy.json.gz | 184-02 | false | F2 | 0.711 | 0.815 | 0 | 0 |
| cross-month-convoy.json.gz | 184-02 | true | F2 | 0.728 | 0.827 | 0 | 0 |
| cross-month-convoy.json.gz | 184-02 | false | F4 | 0.681 | 0.905 | 57 | 3 |
| cross-month-convoy.json.gz | 184-02 | true | F4 | 0.706 | 0.888 | 57 | 3 |

[逐指标](../data/forecast-performance-profile.csv) · [重复数据](../checks/forecast-performance.json)
