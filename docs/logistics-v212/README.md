# 军事后勤 V2.1.2

本轮继续沿用农业 V2.0、市场 V2.0、加权行军与运输，以及 V2.1.1 整趟押运口粮。实验策略 212 可保存并恢复。当前普通新战役仍采用策略 211，平衡验收见[验证结果](validation-results.md)。

| 主题 | 文档 |
| --- | --- |
| 人员 | [武将可用性](escort-availability.md) · [后勤人员安排](logistics-officer-planning.md) |
| 粮食 | [出发前补给](pre-expedition-supply.md) · [需求及覆盖率](supply-demand-coverage.md) |
| 战略 | [恢复参数](recovery-parameter-experiments.md) · [新占城市](occupation-recovery-budget.md) · [扩张](strategic-expansion-balance.md) · [外交](diplomacy-defense.md) |
| 证据 | [数据字典](observer-metrics.md) · [存档](save-compatibility.md) · [性能](performance-results.md) · [长期结果](long-term-balance-results.md) |
| 下一阶段 | [待解决项](known-issues.md) · [天气开发判断](weather-system-readiness.md) |

观战统一通过 new 和 observe_turn 命令运行。F3 使用开工时的策略 211 提交 bd74da1873ebda78d1f3cce6d86f089ef80b8cfb。原项目工作目录有独立的未提交改动，实验在 codex/logistics-v212 工作树完成。所有运行的实际 Git SHA、剧本 SHA-256、种子和规则版本保存在验收包的 data/simulation-manifest.json 中。

仓库的 tools/economy-balance/v212_experiments.py 运行各组配对，v212_report.py 核对并打包观测数据。group G4al 对应 G4a 60%／55%，G3l 对应 G3 60%／55%。
