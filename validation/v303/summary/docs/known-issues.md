# 已知限制

纯水容量收益取决于实际地图接入结构。对于因接入而成为混合的路线，保留陆路瓶颈。真实船队、仓库接驳和多段交割留给后续模块。

旧用户官渡档仍受目录摘要约束。历史长期滞留的运队继续使用真实原始粮袋和位置，容量试验本身没有变更基础耗粮或历史发运装载。

区域交易购入、发运和到货分列。来源城发运后的缺粮是观测关联，单次关联不能证明是某次运输造成。

## 实测警戒线

| 阶段 | 剧本 | 种子 | 策略 | 经济背景 | 对照 | 指标 | 实测变动 |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| five | 184-02 | 2026 | 211 | G1 | C0 | winter_timely_percent | 90.51 → 76.26 |
| five | 184-02 | 2026 | 212 | G1 | historical-G0 | rations_missing | 3,022 → 19,165 |
| five | 184-02 | 2026 | 212 | G1 | historical-G0 | unpaid_city_turns | 5 → 32 |
| five | 190-01 | 2027 | 211 | G1 | C0 | mean_turn_cpu | 0.70 → 1.14 |
| five | 190-01 | 2027 | 211 | G1 | C0 | rations_missing | 39,991 → 53,633 |
| five | 190-01 | 2027 | 211 | G1 | C0 | unpaid_city_turns | 112 → 155 |
| five | 190-01 | 2027 | 211 | G1 | historical-G0 | mean_turn_cpu | 0.64 → 1.14 |
| five | 190-01 | 2027 | 211 | G1 | historical-G0 | rations_missing | 33,021 → 53,633 |
| five | 190-01 | 2027 | 211 | G1 | historical-G0 | unpaid_city_turns | 77 → 155 |
| five | 190-01 | 2031 | 211 | G1 | historical-G0 | winter_timely_percent | 77.15 → 67.69 |
| five | 207-09 | 2034 | 211 | G1 | C0 | rations_missing | 25,936 → 65,137 |
| five | 207-09 | 2034 | 211 | G1 | C0 | unpaid_city_turns | 55 → 101 |
| five | 207-09 | 2034 | 211 | G1 | historical-G0 | unpaid_city_turns | 75 → 101 |
| five | 208-10 | 2026 | 211 | G1 | C0 | mean_turn_cpu | 0.89 → 1.43 |
| five | 208-10 | 2026 | 211 | G1 | C0 | rations_missing | 33,372 → 54,327 |
| five | 208-10 | 2026 | 211 | G1 | C0 | unpaid_city_turns | 95 → 123 |
| five | 208-10 | 2026 | 211 | G1 | historical-G0 | mean_turn_cpu | 0.77 → 1.43 |
| five | 208-10 | 2026 | 211 | G0 | C0 | mean_turn_cpu | 1.15 → 1.54 |
| five | 208-10 | 2026 | 211 | G1 | historical-G0 | rations_missing | 50,118 → 70,764 |
| five | 208-10 | 2026 | 212 | G4 | C0 | rations_missing | 13,745 → 69,566 |
| five | 208-10 | 2026 | 212 | G4 | C0 | unpaid_city_turns | 32 → 149 |
| five | 208-10 | 2026 | 212 | G4 | historical-G0 | unpaid_city_turns | 118 → 149 |
| five | 263-05 | 2026 | 211 | G1 | C0 | rations_missing | 40,452 → 143,970 |
| five | 263-05 | 2026 | 211 | G1 | C0 | unpaid_city_turns | 56 → 175 |
| holdout | 208-10 | 2038 | 212 | G1 | C0 | small_faction_survival_percent | 20.00 → 0.00 |
| holdout | 208-10 | 2038 | 212 | G1 | C0 | winter_timely_percent | 89.27 → 76.13 |
| long | 184-02 | 2026 | 211 | G1 | C0 | winter_timely_percent | 62.71 → 48.81 |
| long | 208-10 | 2026 | 211 | G1 | C0 | mean_turn_cpu | 2.19 → 3.11 |
| long | 208-10 | 2026 | 211 | G1 | C0 | rations_missing | 392,075 → 641,682 |
| long | 208-10 | 2026 | 211 | G1 | C0 | unpaid_city_turns | 1,158 → 1,813 |
| long | 208-10 | 2026 | 211 | G1 | historical-G0 | rations_missing | 496,090 → 641,682 |
| long | 208-10 | 2026 | 212 | G1 | C0 | winter_timely_percent | 79.22 → 72.84 |
| quick | 184-02 | 2026 | 212 | G1 | C0 | small_faction_survival_percent | 44.44 → 33.33 |
| quick | 208-10 | 2026 | 211 | G1 | C0 | mean_turn_cpu | 0.74 → 1.01 |
| quick | 208-10 | 2026 | 211 | G1 | C0 | rations_missing | 0 → 44 |
| quick | 208-10 | 2026 | 211 | G1 | C0 | unpaid_city_turns | 0 → 1 |
| quick | 263-05 | 2026 | 211 | G1 | C0 | mean_turn_cpu | 0.76 → 1.05 |
| quick | 263-05 | 2026 | 211 | G1 | C0 | winter_timely_percent | 97.64 → 90.61 |
