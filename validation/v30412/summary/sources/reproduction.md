# 独立复算

固定入口使用开发分支上的 `tools/economy-balance/v30412_replays.py`。把上一轮按清单恢复的原始检查点作为 `INPUTS`，把 30411 归档的 `replay-inputs.json` 作为 `PREVIOUS_MANIFEST`。工具先用原归档 SHA-256 核对全部检查点。

```sh
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v30412_replays.py \
  fixed "$INPUTS" "$PREVIOUS_MANIFEST" evidence/fixed --group K0 K1 K2 L0 L1 L2
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v30412_replays.py \
  south "$INPUTS" "$PREVIOUS_MANIFEST" evidence/south --group K0 K1 K2 L0 L1 L2
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v30412_replays.py \
  performance "$INPUTS" "$PREVIOUS_MANIFEST" evidence/performance --group K0 K2 L0 L2
python3 -B tools/economy-balance/v30412_acceptance.py evidence summary/data all
```

北方积雪复放十次，每次三旬。其余检查点各三次、每次三旬。每次计时在单独工作进程中执行，关闭额外观测。原始单旬 CPU 值、路线查询次数、峰值内存和检查点来源均在原始分包中。

逐项等价 JSON 将最终干净源码重跑的全部 30 个固定窗口和本轮第一批窗口逐一对齐。消耗、实收、账目、领域状态哈希及 RNG 一致。时钟值和后来新增的“实际抵达终点”观测字段按其自身性质排除。原始业务记录可在 `fixed-clean` 分包中读取。

先解压各原始分包到同一目录。固定重放对比使用 `fixed-final` 和 `fixed-clean` 两个实际目录。观战阶段复算可用本目录的 `summarize_stages.py` 从已生成的逐局 CSV 和原始凭证重建阶段 JSON 及专项 CSV。`collect_technical.py` 记录了技术校验的证据收集范围。

仓库的测试命令使用正式战役、普通及紧凑存档载入器、同一款 Rust 和 WASM 核心、发布构建使用的 Pyodide，以及真实桌面和触控浏览器。

宏观观战入口为 `v30412_campaigns.py`，只接受同引擎且实际获准的上一阶段 JSON。复算命令为 `python3 -B tools/economy-balance/v30412_campaign_report.py OBSERVATIONS SUMMARY`。保留种子必须使用冻结后写出的准入 JSON。

`xuantu-control.py` 与 `weimieshu-control.py` 在仓库根目录运行。第一个参数为已完成观战的 `run-v3041.json`，第二个参数为输出目录。两者先重现原战役最终存档，验证原始 SHA，然后从指定的实际扣粮前存档切换调度做短窗复放。玄菟使用 L2 赤壁 211，魏灭蜀使用 K2 的 263-05 211。
