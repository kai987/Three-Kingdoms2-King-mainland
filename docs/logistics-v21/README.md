# 軍事後勤 V2.1

V2.1 为势力 AI 增加逐旬粮食预测、三级储粮、运输与军粮预算，以及驻军供养评估。玩家仍在所在地使用真实官仓与市场。城内市场和战场米屋继续共用库存。

- [玩法、预算与执行边界](rules.md)
- [观战字段与统计口径](observer-data.md)
- [实验方法与验收结果](validation.md)
- [待改善的行为和数据限制](known-issues.md)

新战役写入独立策略版本 21。新版引擎读取没有该版本号的旧档时沿用原来的策略。农业、市场、行军配给和兵粮刻度各按各自的存档字段识别。本次没有存档升级按钮。

从仓库根目录运行联调。相同的测试工具和版本记录也收录于验收包。

```sh
PYTHONPATH=tests python3 -B -m unittest test_remake_logistics_v21
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/run_v21_experiments.py pilot --output build/logistics-v21
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/run_v21_experiments.py paired --missing-only --output build/logistics-v21
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/run_v21_experiments.py long --missing-only --output build/logistics-v21
```

把两种策略放在同一份游戏数据上配对。D 组使用 V2.0 策略。E1 增加势力预算和救济。E2 增加更远期运输、时效判断和两种合法路径比较。E3 增加驻军供养、募兵和编兵预算。E4 增加战斗备粮、返程、补兵规划以及局部恢复优先级。组别由工具选择，存档使用生产用策略标记。
