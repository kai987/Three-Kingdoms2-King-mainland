# 观战数据字典

每局保留 monthly、factions、cities、capture-recovery、shortages、supply-requests、convoys、troop-flows、battles、war-quotes、war-quote-groups、war-plans、route-changes、action-capacity 和 run.json。前三表用于固定观察点，其他表来自真实结算或规划调用。一趟运输按局内运单 ID 归并，数量来自原回执。

| 新流水 | 粒度与内容 |
| --- | --- |
| army-convoys.csv | 军队接济的发运、交付、天气、退运命令和真实返抵。含实装押运兵、粮袋、货粮、行军与等候日、预计返路及实际粮账 |
| army-requests.csv | 城市报价、同城交接、改道、主动取消。含需求 ID 与期限、候选、会合估计、阻塞原因、保护粮及实际交割 |
| war-recovery.csv | 每个恢复方案评估和实际选择暂缓的策略决策。含计划 ID、战线、真实损失、预计新损、未支付承诺、可补兵、金粮、时间与例外依据 |
| run.json | 版本、Git、剧本 SHA、开局规范化状态、种子、难度、寿命、实测时长、观测器配置、候选参数及性能 |

0 表示实测零值，not_collected 表示该历史观测没有对应字段，not_applicable 表示机制未启用或比例没有合法分母。事件 JSON 用 null 标记没有有效数值或日期，例如无可靠恢复期。真实返抵和退运命令分别记录，已结束任务与窗口内成功率分母分开计算。

比率表将期末在途货粮单列。观测开关按每旬真实状态校验值验证，战斗和运输粮由原结算事件核对。
