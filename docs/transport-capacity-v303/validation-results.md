# 本地复算

`tools/economy-balance/v303_experiments.py` 负责候选分组，从源代码工作区运行。五年、二十年和保留种子的真实流水按实验组保存。

```sh
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v303_experiments.py quick --groups C0 C1 C2 C2p C3 C4
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v303_capacity_audit.py census build/transport-capacity-v303/audits
```

固定复放需要归档中的输入 CSV、游戏检查点和相同的地图与剧本。通过 `--help` 查询 `v303_capacity_audit.py`、`v303_replay_checks.py` 与 `v303_report.py` 的参数。汇总验证目录包含场景配对、账务对照、来源城阻塞、容量利用率、历史收据及每个文件的哈希。

固定复放的原始需求表与返程样本表位于汇总中的 `sources/v3021-fixed-inputs/`。五份同初态检查点位于容量复放包的 `checkpoints/`，历史运队检查点可单独用 `v303_replay_checks.py history` 读取。复用的历史经济对照由 `baseline-verification.csv` 和来源清单指向原数据，使用当前运行记录的前缀校验和同存档状态校验核对。

解压汇总包后，可以用 Python 3.11 以上版本单独校验 SHA-256 并复算重点指标。从 `validation/v303/` 运行以下命令。

```sh
python3 summary/sources/v303_recalculate.py summary
```
