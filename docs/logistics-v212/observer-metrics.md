# 观战数据字典

日期使用剧本年月日。旬为 10 个游戏日。事件表的日序从本战役首日开始，作用域为同一剧本、种子、参数组。城池、势力、武将和部队字段用游戏内部标识。not_collected 表示原观测没有该字段，not_applicable 表示此分组没有该规则或指标无分母，null 表示单条记录缺少可用值，数字 0 表示已观测的零。

| 文件 | 一行的含义 |
| --- | --- |
| monthly、factions、cities | 当月、势力或城市真实状态快照 |
| shortages、capture-recovery | 缺粮当旬的粮食和伤亡，或攻占后的实际城市记录 |
| supply-requests、convoys、route-changes | 调拨请求、运输实况与道路改道 |
| troop-flows、battles | 已结算兵员流动、战斗与口粮 |
| war-quotes、war-quote-groups、war-plans | 单次报价、独立作战候选与真实计划 |
| army-requests、army-convoys | 接济报价、集合、改道、货粮交付和运队阶段 |
| action-capacity | 势力旬是否在行动、休养或连续受阻 |
| escort-availability、escort-assignments | 城池人员报价及实际轻装调整和转调 |
| supply-episodes | 独立需求的原始量、增加量、期限和实际粮袋交割 |
| war-recovery、multi-front-commitments | 同一时点的恢复评分和多线承诺量 |
| pre-expedition-supply-plans | 实际节点预留、释放、领粮、采购或调粮 |
| occupation-recovery、occupation-garrison-budget | 新占城市同一时点的驻防威胁、实际粮食和预算状态 |
| run.json | 本局版本、配置、种子、结束条件及性能计数 |

scenario-scores.csv 每局一行。pairwise.csv 每个可比指标一行，差值为候选减 F3。distributions.csv 使用完成的 21 对五年结果。holdout-comparison.csv 和 long-term-economy-comparison.csv 按各自实验期限出具。

simulation-manifest.json 使用成员相对路径和 SHA-256。标记 archive_member 的流引用 V2.1.1 验收包，打开对照前应核对整包 SHA-256，再核对成员。新增观测与数据字典随本包交付。一条供粮记录只可依真实交割进入需求满足率。
