# 验证包数据字典

粮和金均为游戏库存单位，兵力与人口是人数，行军与战场时间以日计。战略层一旬等于 10 日，月等于三旬。原验证包的 `null` 同时用于无适用值和未采集值。基准补充包使用 `0` 表示实测为零、`not_collected` 表示缺少可验证的观测、`not_applicable` 表示该规则组没有相应机制。逐事件表里的 `null` 表示这条记录没有该信息，例如发运当时尚无实际抵达日。

| 文件 | 内容和记录粒度 |
| --- | --- |
| `travel-routes-v1-v2.csv` | 物理路线或发现路线的配置去重键，含来源剧本与季节开放约束 |
| `route-seasonal-costs-v1-v2.csv` | 路线键 × 方向 × 月份，四种兵员组合分别给出 V1 基础、V2 额外及总粮。不可走方向没有粮费。闭锁月份和各剧本可用性见 `scenarios_with_open_window`。`cargo_delivered` 是 100,000 单位的纯途耗报价 |
| `river-segment-supply-v2.csv` | 分段的实际行进顺序、细分时间、费率和途耗基点。1,000 个时间份等于 1 日，1 基点等于 0.01% |
| `march-supply-cases-v2.csv`、`cargo-attrition-cases-v2.csv` | 明示输入的算术案例，无天气或途中临时补给。途耗计量精度为千万分之一粮 |
| `transport-conservation-v2.csv` | 实际派遣、送达、返还的隔离对局和被货量上限拒绝的案例。控制变量有出发库存、单程货量、押运兵数及海路权限 |
| `minimum-grain-route-cases.csv` | 同一地图下最快和省粮方案，含预计路耗和返程。`opening_roster_can_dispatch` 标注开局是否可直接使用配置中的武将 |
| `strategic-grain-reserves.csv` | 所有剧本的开局已归属城市，列出库存、固定支出、产粮、市场额度、实际在途和目标储备 |
| `war-budget-v2.csv`、`ai-expedition-budget-cases.csv` | 同一组实引擎出征报价，用于战争成本及 AI 决策两个入口。库存和兵力是受控输入，`can_depart` 是按该输入判断的后勤许可 |
| `ai-recruitment-budget-cases.csv` | 声明正常／直接受威胁的输入、现有库存、最大可募量及不计潜在采购的预算 |
| `battles/*`、`battles-baseline/*` | 七种兵力配比、每种 30 个固定种子。实际战术对局控制地形、战力与初始随军粮。独立验证相同输入下的战斗与经验 |
| `observed/*` | 组别／随机种子／指定月数／剧本；保留每月、势力、逐城市、攻占恢复与实际结束状态 |
| `long-term-*-comparison.csv` | 真实观战摘要，按相同剧本、种子、观测月对基准 A 计算差值 |
| `simulation-manifest.json`、`validation-manifest.json` | 组别提交、剧本 SHA-256、运行参数、起止日期、每次结果、源文件及包内文件摘要 |

小势力定义为开局实有 1–3 城，到观测月仍有城计为存续。开局中立或未登场集团不计。攻占恢复是该城攻占后官仓首次回到至少一个月居民与驻军口粮，按月采样。人均、每城旬和每势力年化指标使用观察到的分母。城旬分母包含观测中立城，欠粮城旬只计在结算时未足额支付居民和驻军口粮的已归属城。养兵工资单独统计。送达率按窗口内已装载、已交付的总量计算，期末在途粮可影响此比例。

路线的每个方向、月份和规则指纹都使用实际可读配置。路线 CSV 中的货耗是公式预测。实运收据、真实战术回放和跨年度观战逐项区分存储。

## 基准补充包

路径 `data/observed/A/<seed>/<requested_months>/<scenario>/` 内含原有表与新流水。`monthly.csv` 每局每个采样回合一行，`factions.csv` 增加势力键，`cities.csv` 增加城池键。开局 `elapsed_turns=0`，每三旬采样。库存、兵力、人口和城镇等级为采样时的值。连续缺粮以已完成扣粮的旬为单位。其他累计数从开局起累计。`capture-recovery.csv` 使用原验证包的采样规则。`run.json` 记录止期、种子、剧本哈希、规则版本、Rust 后端与每张流水的行数。

| 补齐字段 | 统计口径 |
| --- | --- |
| `town` | 町等级的实际存档值，或该城没有运行期设施记录时引擎采用的开局町等级 |
| `monthly_fixed_grain` | 采样时按现有人口、实驻现役兵、城中预备兵和当期薪饷算出的月固定粮支。排除行军与战场粮、交易和临时支出 |
| `food_shortage_streak`、`max_food_shortage_streak` | 居民与驻军口粮连续不足的当前旬数及从开局起的最大旬数。足额或中立时当前连续数归零 |
| `march_rations`、`march_base_rations`、`march_days` | 战略行军口粮实际扣减、其中对应的基础费率口粮，以及发生口粮结算的累计队伍日。A 组行军全部按基础费率，包含消费口粮的等待日 |
| `march_food_missing_days`、`march_hunger_losses` | 战略行军实际断粮队伍日与由此减员，不含天气与战斗伤亡 |
| `convoy_rations`、`convoy_days`、`convoy_hunger_losses` | 实际运输途中队伍口粮扣减、运输队伍日、因途中断粮减员，包含护送和随车预备兵。口粮可以来自随队粮袋、沿途补给及货粮 |
| `convoy_dispatched`、`convoy_arrived` | 发运与交付的实际回执次数。送至军队也计入交付 |
| `convoy_returned`、`convoy_failed` | 沿用 D 组的回执口径。前者累计 `transport_returned`，一支队可能发出返程指令和入城两次回执。后者是其中尚未完成交付的回执次数。按队伍统计结局时使用 `convoys.csv` 的终态并按 `convoy_id` 去重 |
| `convoy_grain_sent`、`convoy_grain_arrived` | 离城时装载的货粮及实际交割的货粮。粮袋口粮分开记。两个累计值可能覆盖不同的队伍，因为月末可仍在途中 |
| `convoy_cargo_rations`、`convoy_weather_grain_loss` | 货粮账本的转入口粮与天气损失。前者计入粮袋后经消耗才计入口粮支出，勿和 `convoy_rations` 相加 |
| `convoy_land_departures`、`convoy_river_departures`、`convoy_sea_departures` | 发运路线包含相应方式的队数。混合路线可以同时计入多列 |
| `convoy_late_arrivals` | 沿用 D 组口径。交付发生时，目标城仍处在当轮再次测得的连续断粮中。预计与实际日期应从 `convoys.csv` 比较 |
| `battle_days`、`battle_grain_rations`、`battle_grain_burned` | 结算时读取战场粮账的已完成天数、双方消耗粮和火攻毁粮 |
| `battle_retreats` | 延续 D 组口径。战果码为 `retreat` 或 `defeat` 的战斗数。单次战果码可查 `battles.csv` |
| `ai_sorties` | 战略 AI 实际报告出征的次数 |
| `strategic_aid_transports` | 成功发出的战略 AI 补给运输次数 |
| `requested_aid_refused` | 盟友外交援粮请求未获同意的次数 |

新流水的字段、时点和统计限制见 [V2.1 观测说明](observer-v21.md)。结构性不适用项目见 [字段覆盖说明](baseline-field-availability.md)。
