# 复现与校验

游戏引擎验收提交为 `d096f47a6ac212fb64a9d715889f5d60434d8111`。矩阵使用 [真实命令与配置](../data/simulation-manifest.json) 中的剧本、种子、规则版本和观察月数。

从源码运行 `tools/economy-balance/v3041_campaigns.py` 重放观战。配对输入保持相同种子、剧本、策略及月份。使用 `v3041_replays.py` 读入原始存档和上一轮数据，原始输入及引用见检查清单。

将对应观战 ZIP 解压到同一个目录后，可使用 `v3041_report.py` 重新汇总 CSV。在已有汇总目录中运行 `python3 -B summary/sources/v3041_verify_archive.py .` 检查 ZIP、文件 SHA-256、军粮比率及期末经济总数。
