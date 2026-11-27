# V2.3.1 验收数据字典

| 文件 | 粒度 | 字段和单位 |
| --- | --- | --- |
| scenario-scores、pairwise | 批次、剧本、种子、策略、组 | 观战月份、缺粮城旬与粮点、战斗、运输、存续百分比及每旬 CPU 秒 |
| balance-alerts | 每个配对和指标 | 实测值、变化百分比或百分点、警戒阈值及零基线警戒 |
| climate-forecast、route-*-error-comparison | 固定路线批次、模型、指标 | 有符号误差、平均绝对误差、P50、P90、低估率。口粮为路线权重 |
| monthly-weather-joint-distribution | 区域或河段、月及旬、寒潮配置 | 降雪、积雪或冰情的联合权重。样本数为逐日总数 |
| forecast-double-count-audit | 固定去回路线 | 天数四项、口粮四项、成本加总、当前冰封与未来风险 |
| military-grain-request-ledger | 军队连续需求段 | 请求粮、原始和更新期限、首次实际断粮 tick、补齐及未解决粮 |
| military-grain-receipt-ledger | 实际回执 | 实收、计入余额、渠道、时间、冬季需求和回执标记、原期限标记 |
| winter-order-timely-comparison | 实际军粮运队 | 发运、货粮及口粮、原需求 tick、原承诺抵达旬、实收旬 |
| military-planning-evaluations | 真实规划读取 | 需求、期限和当时所知的可靠在途量、未覆盖需求 |
| weather-cargo-loss-audit | 观战 | 基础路线货损、天气额外货损、独立事件货损、冰封等待、去返口粮、在途余额 |
| regional-grain-flow-account | 城池、过账月、势力、连续账段 | 实际写入的分类粮账。日期取发起结算的命令日期 |
| prior-nine-turn-city-* | 城池旬耗或逐笔过账 | 首次严重短缺前后的口粮、人口、驻军、市场、资源流及所属 |
| city-shortage-checkpoint-replay | 同一原状态和分组 | 原状态哈希、来源城库存、路线可用性、复放缺口 |
| agriculture-risk-preparation-* | 备粮及同初始配置配对 | 实际渠道备粮与情景差额 |
| forecast-performance-profile | 实际检查点和观测开关 | 三次计时、P50/P95、预测调用、缓存命中、候选和内存 |
| historical-transport-replay-index | 已登记的历史运队 | 本次实际重放或既有证据、文件及 SHA-256 |

数值 0 表示实际采集到零。CSV 的 null 表示未采集、无分母或机制不适用，结合对应行的来源及开关判断。旧 V2.3 正式结果标记为 v23_original。旧军粮量缺项保留为空。路线权重和实际仓库账粮点是不同单位。
