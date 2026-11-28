# 统计字段和证据

| 口径 | 数据 | 定义 |
| --- | --- | --- |
| 实际城市伙食 | `actual-demand-coverage`、`actual-city-consumption-comparison`、`scenario-scores` | `resident_due` 与 `garrison_due` 合计为真实应付。仓库执行一次合并扣粮，实付或缺口无法再唯一分摊给居民和驻军。 |
| 扣粮快照 | 安定、东莱及原始实际流水 | `settlement_tick` 是结算日；一旬等于十日。保留人口、在城兵、预备兵、扣前和扣后货粮，以及应付和实付。 |
| 实付率 | `actual_payment_rate`、`urban_food_payment_rate` | 实付／应付。两张表均保存分子、分母。应付为零时缺少适用的比率。 |
| 原期限 | `transport-demand-episodes`、`military-grain-request-ledger` | 每次真实需求的首次期限保持不变。重新报价或转移目标与后续期限分开记录。 |
| 及时实体到货 | `fixed-physical-freight-comparison` | 按真实入仓事件。足额和上限分别使用原始目标缺口；返程货物和归队用粮保持独立。 |
| 市场和实体消费归因 | `effective-supply-channel-attribution` | 保守算出必须来自指定来源的已付款粮，可混用库存采用最保守结果。同一批粮的购买、到货及最终实付分别留凭证。 |
| 行军粮与伤亡 | `transit-march-safety-comparison`、`transit-refill-denial-ledger` | 逐日计算真实应付、实耗和损失。累计按军队合计，保留路线、节点、已承诺补给、剩余粮和实际终点。 |
| 预留 | `transit-commitment-settlement` | 节点、承诺归属、有效期、已扣数量和状态来自已观测的结算操作；受保护粮仍在合法库存中。 |
| 资源安全 | `resource-safety` | 窗口内逐笔平衡、买卖、交接、押运占用、命令书凭证和单旬同城发运核对。 |
| 全渠道命令书 | `all-grain-security-command-efficiency`、`grain_security_books` | 记录成功操作实际扣书。包含本地和区域交易、实体发运，以及发生的直接接济等可证实操作。未发生的命令没有消耗记录。 |
| 运输周转效率 | `transport-efficiency-by-purpose`、`small-load-transport-audit` | 用实际净交付和已观察到的占用时长计算，仍在途的运队单列。用途来源于发运凭证。 |
| 天气重新报价 | `forecast-requote-results` | 后程口粮调整后实际产生的合法报价事件。重复评估可能产生多笔同类事件，发运和到货不能由该事件确认。 |
| 计时 | `scheduler-performance-profile`、原始运行 JSON | 每旬进程 CPU，单位秒。保留各旬样本、峰值内存、路线调用量和每组重复次数。 |

CSV 中的 `0` 表示可以观察且数量为零。`null` 表示不适用或缺少可确定的证据，字段适用条件由各表及阶段 JSON 共同给出。未执行阶段只有状态和原因，没有填充五年、二十年及保留种子的零记录。D0 或 D2 的运队对照各有相同代码和随机种子作为基准。原始样本复用时保留检查点 SHA，用于识别同存档或重复观测。
