# 复算入口

运行时冻结提交见本目录的 `source-record.json`。先用游戏源树中的固定数据、地图及 Rust 核心构建。观战输出写到独立目录。相同种子、天气和终点下，详细观察开关、运行时间及后端同时记录。

```sh
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3021_experiments.py winter --groups G4
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3021_experiments.py dry --groups G4
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3021_experiments.py long --groups G4
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3021_experiments.py holdout --groups G0 G1 G4
```

`v3021_checkpoints.py` 支持用指定的只读运行时树重放固定存档。配对时逐一指定 G1 或 G2 树，其环境变量为 `TK2_OBSERVER_RUNTIME_ROOT`。`v3021_returns.py` 可用相同检查点复现一次运输，隔离新的节点检查。`v3021_capacity.py` 在真实存档上只读计算可调用粮，各阶段在同一最早缺口上比较。它另用从同一存档重新加载的战役推进至结束日，核对新发运粮的实际收据。入口参数为输出目录及一组 gzip 检查点。

`v3021_history.py` 读取 V3.0.2 已知的真实 `observed/` 流水。`v3021_report.py` 使用 V3.0.2 清单逐局核验配对，输出 CSV 和 JSON。`v3021_narrative.py` 更新验收、长期样本、已知问题和准入 Markdown。`v3021_package.py` 为每个 ZIP 写入映射与哈希，按归档成员重读核验。

历史 G0、G1 及 2034 复放的相对路径及哈希保留在新清单。[上一版归档](https://github.com/kai987/Three-Kingdoms2-King-mainland/tree/codex/v302-validation-archives/validation/v302)
