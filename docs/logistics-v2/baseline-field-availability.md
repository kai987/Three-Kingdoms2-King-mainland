# 基准补充包的缺失及不适用字段

## 原始采集

种子 2027 和 2028 的各 7 局五年观战，以及种子 2026 的 184-02 和 208-10 两局二十年观战，在原包只有月度、势力、城池状态、攻占恢复记录和运行元数据。实际逐日粮袋、运单、战场粮账及兵员流水没有保留。补充包依据同版本的逐日执行、结算委任、战斗回执和运输账本重新采集。

原包中种子 2026 已有较完整指标的 7 局五年观战可继续引用。原包没有 V2.1 的逐条观测表。补充包也未为原包中的 B、C、D 组添加逐条观测数据。

## A 组不适用的 V2 列

| 范围 | `not_applicable` 字段 |
| --- | --- |
| V2 运输规则 | `convoy_route_grain_loss`、`convoy_minimum_grain_departures` |
| V2 军事预算 | `ai_sortie_quotes`、`ai_sortie_quote_blocked`、`ai_recruit_quotes`、`ai_recruit_quote_capped`、`ai_recruit_quote_rejected`、`ai_emergency_recruit_quotes` |
| V2 战略储粮 | `ai_reserve_purchases`、`strategic_reserve_target`、`strategic_reserve_met`、`strategic_reserve_observed` |

天气、运输货粮转口粮、断粮减员、普通路线模式、战场口粮和火攻毁粮属于 A 组可观测机制。它们在相应期间没有发生时记录 `0`。

## 详细流水的覆盖

- A 组仍可观测路网找不到路线、路线时间或风险超限、去程粮检查和已排定出征撤销。没有 V2 预算的行，预算明细为空。`war-quotes.csv` 的通用观测次数和 V2 汇总字段 `ai_sortie_quotes` 粒度不同。
- V2.0 的出征报价包含应急粮缓冲、返程、留守、战后补兵等实际门槛。出征代码没有额外独立的战略储粮拦截。因此不能把应急缓冲归为独立的战略储粮挡关。若后续 V2.1 接入该规则，需要记录正式门槛与相应原因。
- `can_arrive_before_zero_grain` 在调度器真正评估运量时有值，或在当时已到零时为 `0`。调度提前返回且没有候选评估时标记 `not_collected`。部分请求会因为没有合格押运、命令书、路线等条件在上游返回，记录能从执行边界确定的最具体原因。
- 运队尚在途中时没有交付日和实际交付量。政治转属或到年限退场造成的无直接交接记录不能按库存计算运输。手动募兵在纯观战局没有调用，相关流水计数为 `0`。
- `checks/field-coverage.csv` 逐局列出新旧三张快照表中每列的采集状态、与原包 D 组的共有情况和各标记的单元格数。详细流水是否有记录可查每局的 `run.json`。
