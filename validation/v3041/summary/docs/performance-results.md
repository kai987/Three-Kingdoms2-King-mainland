# 固定状态性能

| 检查点 | 分组 | 观测 | 重复 | 回合 CPU p50 | 回合 CPU p95 | 路线批查询 |
| --- | --- | --- | --- | --- | --- | --- |
| yellow-late | T0 | false | 3 | 4.46 | 5.04 | 411 |
| yellow-late | T0 | true | 3 | 4.46 | 5.08 | 411 |
| yellow-late | T3 | false | 3 | 5.53 | 7.25 | 666 |
| yellow-late | T3 | true | 3 | 5.56 | 7.20 | 666 |
| chibi-late | T0 | false | 3 | 1.09 | 1.26 | 339 |
| chibi-late | T0 | true | 3 | 1.07 | 1.30 | 339 |
| chibi-late | T3 | false | 3 | 1.43 | 2.12 | 285 |
| chibi-late | T3 | true | 3 | 1.40 | 2.18 | 285 |
| multiple-shortages | T0 | false | 3 | 6.47 | 6.69 | 339 |
| multiple-shortages | T0 | true | 3 | 6.20 | 6.78 | 339 |
| multiple-shortages | T3 | false | 3 | 2.37 | 3.36 | 126 |
| multiple-shortages | T3 | true | 3 | 2.64 | 3.68 | 126 |
| convoys-in-transit | T0 | false | 3 | 0.61 | 0.76 | 9 |
| convoys-in-transit | T0 | true | 3 | 0.70 | 0.91 | 9 |
| convoys-in-transit | T3 | false | 3 | 0.88 | 1.20 | 39 |
| convoys-in-transit | T3 | true | 3 | 0.89 | 1.21 | 39 |
| north-snow | T0 | false | 3 | 0.61 | 0.72 | 24 |
| north-snow | T0 | true | 3 | 0.61 | 0.93 | 24 |
| north-snow | T3 | false | 3 | 0.99 | 2.38 | 93 |
| north-snow | T3 | true | 3 | 1.05 | 2.33 | 93 |

[逐次记录](../data/scheduler-performance-profile.csv)
