# 独立重制版的模块盘点

目标是可玩的独立游戏。运行玩法时不读取ROM、不执行6502、不解释控制IR；原工程保留为规则证据。以下“可直接用”仅指表中具体的纯函数，不代表整个旧引擎可以直接使用。

| 玩法模块 | 分类 | 实际代码与已有成果 | 接入重制版需要处理的内容 |
| --- | --- | --- | --- |
| 地图与城际连接 | 可直接用 | `expansion/map/city-map-city-sea-plan-v42.json`、`city-map-city-sea-links-v42.json`，96城及海陆连接验证 | 用稳定城池键连接现代城市状态；世界横坐标与裁剪后的屏幕坐标相差136 |
| 武将人物库与年代 | 可直接用／需补齐 | `expansion/officers/data/roster-candidates.json`，1000个独立人物、10剧本 | 年代表是SAN14设定转录；五维能力尚缺，原237人只完成8个人物对照；不能把候选库全数当成已配置可玩人物 |
| 武将与城市运行状态 | 需补齐 | `source/recovered/officers.py`、`domestic_ai.py:CityRecord`、`game_engine.py` | 旧12字节／32字节、237人、30城、城内10槽及FF哨兵不可直接扩写；新建具名字段、20人名册和16位身份引用 |
| 战斗效果量与升级 | 可直接用 | `source/recovered/battle.py`的距离、成功率、兵损、体损、经验纯函数；`source/readable_c/game_recovered.c` | 只借用无ROM/IR的纯计算；以单次属性适配器隔离旧packed表示，不能截断新人物ID；保留同址兵损的特殊前提 |
| 地形与行动成本 | 可直接用／需补齐 | `game_enums.py`常量可用；`terrain_rules.py:movement_quote`通过ROM地图取格，不能直接接入独立运行时 | 新战场需自己的地形网格与纯报价接口，不能把96城世界底图当战场碰撞；保留平／山／水适性0..2 |
| 出征与部署 | 需补齐 | `battle_setup_ai.py:assign_strategies_and_positions`，两侧起点0／10；`battle_scene_controller.py:initialize_battle_arrays` | 保留每方10个战场槽、全场20槽；现代出征名单从城内20人中选择，不能同步扩成每方20；出征/驻城占位及归城规则单独维护 |
| 战斗、普通攻击、单挑控制器 | 需补齐 | `battle_scene_controller.py`、`attack_scene_controller.py`、`duel_scene_controller.py`已有具名控制正文 | 原控制器依赖寄存器、跨银行服务与内存协议，不整台接入新游戏；先用现代回合状态机串接纯规则，逐步补计略和单挑 |
| 16计略与战术AI | 可直接用／需补齐 | `ai.py`筛选与门槛，`tactical_strategy_ai.py`八策略，`tactical_effects_complete.py`等效果 | 迁移可分离的条件/效果；特定人物白名单改稳定人物键。完整旧AI调度与呈现仍需适配，不宣称已独立可运行 |
| 招募、转属、忠诚、继承 | 可直接用／需补齐 | `officer_transfer.py`三种忠诚算法、名册与继承正文，`faction_lifecycle.py` | 借用明确算式；名册必须原子检查20人容量，绝不越界覆盖；现代死亡状态与原移除码3分开 |
| 内政与年度/月度推进 | 可直接用／需补齐 | `domestic_ai.py`发展/税收/选择纯规则，`domestic_cooperation_controller.py`等 | 现代回合推进与每城行动账本；出生、出仕、死亡事件独立于总库，记录剧本来源和死亡年边界 |
| 城市归属与战后处置 | 可直接用／需补齐 | `city_ownership.py`、`postbattle.py`、`postbattle_*_services.py`、`player_extinction.py` | 提炼归属/资源/名册效果；先实现有限、明确的现代战后选择，满城、无继承人及势力灭亡不能静默丢人 |
| 画面、声音、输入与保存 | 允许重新设计 | 本地HTML/JS地图已有展示；旧`ServiceMemory`仅产出硬件请求 | 浏览器绘制、现代输入/声音、本地JSON存档；不需要继续逆向NMI或硬件时序才能先做可玩闭环 |
| 旧总引擎与主循环 | 需补齐 | `GameEngine`、`CampaignSession`、`SceneCoordinator`、`runtime_services.py`、`PrgDataMemory` | 含ROM表窗、逐op IR及原CPU协议依赖，不能整体当成独立重制版运行时。只保留作对照入口 |

盘点依据为当前实际文件，不把历史报告中的“原核心回放通过”视为新游戏测试。旧报告、源码和原机证据保持原样。
