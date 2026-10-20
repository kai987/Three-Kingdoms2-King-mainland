# 唯一验收对象和待证依赖

这些对象用于去重和安排验收，不代表已知的唯一语义缺陷总数；该总数仍为null。每条原始访问/窗口都保留独立ID。

| ID | 对象 | 原行数 | 依赖 | 下一步 |
|---|---|---:|---|---|
| G-ACCESS-CONTRACTS | 剩余间接访问的指针、入口和索引合同 | 323 | 无前置包 | 按96个历史分工容器排查，首先选择具有完整producer/caller证据的合同；未知容器不推断为共同owner。 |
| G-B517 | B517真实当前JSR帧及inline dispatch合同 | 2 | 无前置包 | 审阅当前脚本的实际代际覆盖和合同域，再另行授权运行；本次不修、不运行静态草稿。 |
| G-RAW-ENTRY | 228个原字节窗口的可信执行入口 | 228 | 无前置包 | 从可达分派目标和声明ROM数据来源追踪入口；不进行无边界随机扫测。 |
| G-CITY-01 | 城市+1正式字段含义 | 0 | G-ACCESS-CONTRACTS, G-B517, G-RAW-ENTRY | 利用上述合同和入口工作包筛出真实消费者，再做有判别力的受控/自然验证。 |
| G-CITY-28 | 城市+28正式字段含义 | 0 | G-ACCESS-CONTRACTS, G-B517, G-RAW-ENTRY | 利用上述合同和入口工作包筛出真实消费者，再做有判别力的受控/自然验证。 |
| G-CITY-29 | 城市+29正式字段含义 | 0 | G-ACCESS-CONTRACTS, G-B517, G-RAW-ENTRY | 利用上述合同和入口工作包筛出真实消费者，再做有判别力的受控/自然验证。 |
| G-CITY-30 | 城市+30正式字段含义 | 0 | G-ACCESS-CONTRACTS, G-B517, G-RAW-ENTRY | 利用上述合同和入口工作包筛出真实消费者，再做有判别力的受控/自然验证。 |
| G-CITY-31 | 城市+31正式字段含义 | 0 | G-ACCESS-CONTRACTS, G-B517, G-RAW-ENTRY | 利用上述合同和入口工作包筛出真实消费者，再做有判别力的受控/自然验证。 |
| G-NONEMPTY-MODE2 | 自然非空mode2完整战后分配与返回 | 0 | 无前置包 | 先审定32 producer与observer版本配套；从7610前缀前的合法母档建立有界结算窗口。 |
| G-HUMAN14 | 自然human14 phase1..6完整多人交互 | 0 | 无前置包 | 先建立合法战斗编组和俘虏来源，再固定有限按钮计划；自然前提不存在时停止并保留缺口。 |
| G-SOURCE-CONTINUITY | 单Source实例跨主循环与中断的完整连续流程 | 0 | G-NONEMPTY-MODE2, G-HUMAN14 | 先取得真实E066现场，跑最短完整路线再扩展；复用既有玩法owner，不新增臆造算法。 |
| G-SERVICE-CLOSURE | 全局可达服务依赖闭包 | 0 | 无前置包 | 按当前依赖库存定位真实未闭合前门，优先阻塞连续UI的服务；不把整个IR或原CPU当生产fallback。 |
| G-INTERRUPT-BOUNDARIES | 关键等待、NMI/IRQ、reset与非局部返回边界 | 0 | G-SOURCE-CONTINUITY, G-SERVICE-CLOSURE | 从现有ECEE/EE07副作用回归扩展有判别力边界；不做无限随机测试。 |
| G-DEVICE-BOUNDARY | 显式设备输入与完整画面/音频合成的验收边界 | 0 | 无前置包 | 将每条Source计划的显式设备夹具和Native五buffer回执并列引用，保持证据边界。 |

B517两行共享已识别的current-JSR验证依赖；其他行真实语义根因未证时保留null。raw104/13按现有有界重叠分类映射gap=null，不推断全局不可能存在替代入口。

每对象的来源路径、hash、阶段、观察/推导类型、影响、验收条件和下一步详见 [JSON清单](unique-gap-register.json)。
