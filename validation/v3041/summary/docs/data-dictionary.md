# 观测数据字典

requested_grain 是真实军粮申请。timely_received_grain、timely_at_original_deadline 和 unresolved_grain 分别为当前期限前、首次期限前实收及未满足粮。

actual_received_grain 是实体运队实际交割量。officer_occupation_days 与 clerk_occupation_days 按调离至任务终止及释放的已观测时间核算。net_per_book 以实际发运操作计费，区域采购加入市场操作。

donor_stock 是势力他城实际库存。L2–L6 的空值表示证据不足。零值在观测到实际无交易或无货物时保留。初始没启用的机制按规则版本解释。

transport-demand-episodes 每个需求段只出现一次。及时报价取该段中观察到的最大单笔完整报价。同一来源提出的多笔候选仍需分配共同库存。实际到货按需求段和运队凭证入账。

source-safety-after-dispatch 记录发运当旬及后续八旬可观察到的减粮结算。记录缺粮表示发运后发生过缺粮，因果还需核对该城后续事件。

运输时间使用每旬十天和既有结算先后次序。货粮、独立押运口粮、金与预备兵使用引擎的实际单位。
