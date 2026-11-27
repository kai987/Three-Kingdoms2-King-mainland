# V3.0.3 水陆运输容量与周转

V3.0.3 在同一套运输账与实体运队上增加两项实验机制。来源城可以让两支实际运队同时在途，每旬默认发运一次。货粮和独立口粮共用实际路线的总装载容量。

| 自变量 | C0 | C1 | C2 | C2p | C3 | C4 |
| --- | --- | --- | --- | --- | --- | --- |
| 活动运队上限为 2 | | ✓ | | | ✓ | ✓ |
| 逐段物理容量 | | | ✓ | ✓ | ✓ | ✓ |
| AI 路线方针 | | | | ✓ | ✓ | ✓ |
| 周转排序 | | | | | | ✓ |

C1b 单独将发运次数提高到每旬两次。G0 为区域市场，G1 加原 302 战略粮仓，G4 使用 3021 的协调和返程规则。开局默认继续使用 C0。状态、数据字典和结果以对应验收归档的报告为准。

- [原有运输参数](baseline-transport-rules.md) · [粮食单位](grain-unit-semantics.md) · [共同发运资格](origin-concurrency.md)
- [陆路](land-transport-capacity.md) · [河路](river-transport-capacity.md) · [海路](sea-transport-capacity.md) · [瓶颈](mixed-route-capacity.md)
- [资源对账](cargo-and-ration-accounting.md) · [人员周转](escort-turnover.md) · [AI 报价](ai-transport-ranking.md)
- [固定样本](capacity-counterfactual.md) · [历史复放](historical-transport-regressions.md) · [性能](performance-results.md)
- [存档](save-compatibility.md) · [观测](observer-metrics.md) · [复算](validation-results.md)
