# 观测与数据字典

所有统计来自对应的战略命令、库存记账、运输实际时点和战场结算，通过只读观察回调获取。预览的单独回归核对游戏随机数、当前状态和重复路径查询。对于需要同日反复读状态的计算，使用该旬托管状态下的本地缓存。

## 数据粒度及单位

| 文件 | 每行粒度 | 数值和口径 |
| --- | --- | --- |
| city-economic-regions | 都市 | 都市所属市场区及目录名称 |
| regional-market-network | 路段和方向 | 名义距离为千米，日数为对应月份基础方向报价 |
| market-price-cases | 固定向量 | 价格单位金／千粮，到岸参考成本用百分之一金 |
| market-price-distribution | 运行、区域、买卖价与档位 | 城市旬初价格样本数 |
| market-stock-flow | 运行、都市、渠道 | 实际买卖粮与金、补货量、溢出、最终库存。最终库存为重复账面快照 |
| regional-supply-demand | 运行、区域、月初 | 月初库存、供应、价格和在途货粮。购销和官仓粮缺口按自然月的真实回执统计，并保留近三自然月购销 |
| regional-procurement-comparison | 运行 | 购入、发运、到货、失败、到期前到货和路线评估次数 |
| regional-trade-comparison | 运行 | 观战中的商业订单、成交、净现金和守门原因 |
| landed-cost-comparison | 活动订单 | 估价所用费用、实际净粮及口粮。实际机会成本需保存原参考价和运输终结回执 |
| commodity-grain-flow | 活动订单 | 区域货物每一步的真实数量。总体运输到货量已包含其中 |
| regional-market-shortages | 运行和区域 | 库存为零、低于四分之一供应、达到两倍供应的城市旬样本 |
| trade-profit-comparison | 商业订单 | 已支付金、实际销售、净现金、未出售份额。受控验证单独标为 `controlled` |
| gold-inflation-comparison | 运行 | 期初期末官仓金、实际市场金钱交换与商业净金 |
| convoy-hunger-comparison | 运行 | 护送和运送预备兵的实际饥损，最长停滞与损失最大的单支运队 |
| winter-army-supply-comparison | 运行 | 依实际到货回执重新核算的及时补给粮。比率是及时粮／当期申请粮 |
| scenario-scores、pairwise | 运行或相同场景配对 | 期末存量、全年累计量、候选减基线、相对变化百分比及警戒线 |
| long-term-economy-comparison | 二十年运行 | 固定同一观测截止状态的对照 |
| performance-comparison | 运行 | CPU 和实耗秒数、进程峰值字节、路径评估及缓存统计 |
| warehouse-resource-account | 运行 | 精确入账观测范围、市场流水和军需运送明细 |
| baseline-verification | 运行、旧包成员、文件 | 摘要 SHA-256 与一致性 |

所有库存和粮耗使用游戏粮点，人口及兵力按人数。 `0` 表示已采得零值。 `not_applicable` 表示规则当时不存在或关闭。 `not_collected` 表示该运行未记录对应结算。 `null` 表示分母为零、损益所需凭证未产生、或者记录在截止时仍在途。仓库生产的实际入账根据日志范围标明，以免将月初公开的生产率当作精确市场注入。

原始库存流水见各局 `market-stock-flow.csv.gz`。同目录保留价格、补货、逐旬城市与区域库存、战斗、缺粮、运输、冬季及区域订单。旧探针的购买事件曾暂用失败状态占位。以同一订单后续发运或失败回执识别结果。
