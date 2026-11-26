# 验收数据字典

| 字段或文件 | 口径 |
| --- | --- |
| unpaid_city_turns | 实付时有粮食缺口的城旬 |
| rations_missing | 本局所有实付粮缺口的累计粮量 |
| strategic_delivered | 最终目标战略净入仓量，中转首腿不重复计入 |
| timely_grain | 最终目标实到旬早于相关运单期限的粮 |
| comparable-dispatch-deadlines.csv | 分别以同旬最早预报缺口和运单截止日计算，保留同一净入仓量分母 |
| winter_timely_percent | 冬季军队申请粮中期限前计入的实际交付比例 |
| convoy_hunger_losses | 运输人员的口粮缺失减员 |
| small_faction_survival_percent | 旧版可比的小势力存续统计 |
| reserve_audit_errors | 战略订单、收据、储备余额和重复写入检查差异 |
| city_resource_mismatches | 原官仓金、粮、预备兵写入与阶段账户核对差异 |
| performance-state-parity.csv | 固定状态逐旬 SHA、随机数及详细观察排序对照 |
| source-convoy-limit-analysis.csv | 资格实际评估、限额命中、同城同旬去重 |
| escort-source-turns.csv | 按运行和旬，按所属势力和来源城去重。所有观测报价都排除该来源才记作 blocked_sources |
| escort-persistence-by-city.csv | 连续旬均有资格观测，且同城同旬全部观测均为无合资格押运，才计入持续缺人 |
| existing-delivery-coverage.csv | 历史任务排除与同旬预测，剩余报价为未采集 |
| residual-demand-comparison.csv | 候选计划内预测数值，重复评估保持原观测单位 |
| shortage-root-cause.csv | 逐条真实缺粮及观测到的共现事实 |
| spatial-grain-capability-funnel.csv | 固定起点的逐目标可调配粮。L5 是同起点真实续跑的期限前新运单实收，附对应收据 |
| top-city-turn-ledger.csv | 历史高缺口城的官仓流水，时间戳是命令开始 |
| reserve-overlap-audit.csv | 固定起点中真实库存与保护标签分账 |
| return-ration-replay.csv | 历史固定点真实运输对照和收据核验 |

数值 0 表示采集且适用。CSV 的 `null` 表示证据未采集、截止日前未知或不匹配。显式 `not_applicable` 表示实验没有对应机制。P90／P95 对缺粮或耗时按最近秩。警告按 S1 区域市场基准保留。同一分组实际终点不同时保留独立数据。
