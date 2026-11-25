# 天气系统 V2.2.1

这次修订修复普通运队的目的地易主校验及重复退运，并把剩余口粮、冰封风险和已承诺的补给纳入同一条结算链。普通新战役使用 AI 策略 211，冬季天气默认关闭。勾选冬季天气时使用规则 221。既有天气 22 存档继续按原版天气规则恢复，天气 22 与 221 共用同一气候随机流。

[根因复现](convoy-root-cause-analysis.md) · [运输进度](dynamic-transport-progress.md) · [剩余口粮](dynamic-ration-safety.md) · [合法返程](safe-return-rules.md) · [冰封](ice-blocked-transport.md) · [公开预测](seasonal-weather-forecast.md)

[季节准备](autumn-grain-preparation.md) · [补给节点](winter-supply-node-planning.md) · [需求期限](weather-aware-supply-deadlines.md) · [观测口径](observer-metrics.md) · [气候区复核](climate-mapping-review.md)

[存档兼容](save-compatibility.md) · [性能](performance-results.md) · [回归](validation-results.md) · [长期平衡](long-term-balance-results.md) · [已知限制](known-issues.md) · [发布判断](weather-release-readiness.md)

## 试验配置

| 组别 | AI 策略 | 冬季天气 | 运输安全修正 | 季节准备修正 |
|---|---:|---|---|---|
| H0 | 211 | 关闭 | 通用修正 | 无 |
| H1 | 211 | 22 | 原天气运输 | 原天气备粮 |
| H2 | 212 | 关闭 | 通用修正 | 无 |
| H3 | 212 | 22 | 原天气运输 | 原天气备粮 |
| I1 | 211／212 | 221 | 开 | 原天气备粮 |
| I2 | 211／212 | 221 | 原天气运输 | 开 |
| I3 | 211／212 | 221 | 开 | 开 |

212 使用 G4al 的补兵覆盖门槛 60%／55%。策略来自观战配置，221 仅表示天气规则。
