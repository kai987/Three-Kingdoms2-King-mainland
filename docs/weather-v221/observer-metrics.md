# 观测数据字典与复算

每局目录以 `observed/{wave}/{group}/{seed}/{months}/{scenario}/` 索引。各局 `run.json` 记录引擎、观测配置、规则版本、结果、种子和终点。天气、结算和粮账均来自同一真正游戏命令路径。原月末库存用于计算状态分布和逐阶段净变化。运队运输量、口粮和战斗来自实际流水。

| 文件 | 行单位及字段 |
|---|---|
| `monthly.csv` | 开局及各月世界状态，兵力、人口、金粮，累计缺粮城旬、缺口、实际会战、发运和损耗 |
| `factions.csv`、`cities.csv` | 同一观测期的单势力、单城池状态及流量 |
| `convoys.csv` | 同一运队的派遣、交割、下达返程、实际返抵或结束收据；`grain_loaded` 为货粮 |
| `transport-progress-daily.csv.gz` | 运队实际结算日和行程；`start_work`、`moved`、`end_work` 是工作单位；`person_days` 是当日押运口粮人数单位，含按百人折算的武将和运送预备兵；`rations_before`、`paid`、`supply`、`rations_after` 是粮袋；`cargo_before`、`route_loss`、`incident_loss`、`cargo_to_bag`、`cargo_after` 是货舱；`missing` 是引擎分母单位下的未满足口粮 |
| `ice-transport-events.csv` | 气候河段所致堵塞和解封事件，带起始日、索引及当时口粮和后续进度 |
| `regional-weather-daily.csv`、`river-ice-daily.csv` | 区域逐日气象和物理河段实测冰情，各日按固定地理 ID 记录 |
| `winter-military-actions.csv` | 游戏实际执行或评估的事件，采购和调粮由真实命令成功后发出；细节为 JSON |
| `route-changes.csv` | 改道前后路线、起点、目标、日期和预算；含军队及运队 |
| `supply-episodes.csv`、`supply-episodes-weather-aware.csv` | 同一战略军粮需求的历史期限和新增公开期限观测；`actual_shortage_tick` 仅在新增口径采集 |
| `action-capacity.csv` | 势力每旬是否符合失能观测口径，含持续旬数、原因和实际行动；普通休养按既有配置排除 |
| `war-plans.csv`、`battles.csv` | 独立军事计划和实际战斗收据；季节汇总按目标气候区和历月 |
| `performance-comparison.csv` | 每局实测的 CPU、墙钟、进程峰值内存、路线查询和缓存、区域及河段更新和重规划次数 |

空白、`null`、`not_applicable` 与 `not_collected` 表示不可用或未采集。数值 0 表示有该字段且实际事件数为零。需求分母为 0 时比率空缺。期末未结束事件保留在待处置中。

## 运输比率

交付率以已经结束的任务为分母，按有真实交付收据的运队计数。安全返抵率采用实际返抵入账。期末任务另列。运队减员同时以每万押运口粮人日及每万实际送达粮表达。冬季来自 11 月至 3 月发生的每日付款、减员和任务收据，全年数字从同一日志直接聚合。可检索普通运队及军队接济两类。

## 复算

在仓库根目录运行：

```sh
PYTHONPATH=source python3 -B tools/economy-balance/v221_report.py --root /path/to/extracted/validation
```

档案将分析脚本放在 `checks`，配合本项目的观测公共模块、场景目录和原始数据重新运行。CSV 使用 UTF-8，逐日运输以 gzip 保存，可用 `gzip -dc` 或 Python 的 `gzip.open` 直接读取。
