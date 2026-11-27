# 技术门槛与存档验收

冻结运行源码为 `a8c854ac05d7691bb460fab9591f362ffee63637`。共完成 49/49 个要求的正式观战。城市资源边界不平衡数 0。冻结天气对照逐日检查 519 天，真实配对另核对 1320 条共享年度区域农业结算。

| 验证 | 退出码 | 实测计数 | 日志 |
| --- | --- | --- | --- |
| climate-browser | 0 | 见对应日志 | logs/climate-browser.log |
| disabled-v231-rust | 0 | 见对应日志 | logs/disabled-v231-rust.log |
| forecast-browser | 0 | 见对应日志 | logs/forecast-browser.log |
| forecast-performance | 0 | 见对应日志 | logs/forecast-performance.log |
| forecast-specialty | 0 | tests=7 | logs/forecast-specialty.log |
| full-browser | 130 | passed=87 | logs/full-browser.log |
| full-browser-final | 0 | passed=110, startTime=2026-11-27T12:58:12.686Z, duration=1116203.615, expected=110, skipped=0, unexpected=0, flaky=0 | logs/full-browser-final.log |
| historic-1860 | 0 | 见对应日志 | logs/historic-1860.log |
| legacy-v231-rust | 0 | 见对应日志 | logs/legacy-v231-rust.log |
| native-check | 0 | 见对应日志 | logs/native-check.log |
| node-tests | 0 | tests=66, passed=66 | logs/node-tests.log |
| prior-features | 0 | 见对应日志 | logs/prior-features.log |
| pyodide | 0 | 见对应日志 | logs/pyodide.log |
| python-campaign | 0 | tests=1977, skipped=1 | logs/python-campaign.log |
| resupply-browser | 0 | passed=4, skipped=2 | logs/resupply-browser.log |
| rust-campaign | 0 | tests=1977 | logs/rust-campaign.log |
| rust-crate | 0 | passed=0 | logs/rust-crate.log |
| rust-fmt | 0 | 见对应日志 | logs/rust-fmt.log |
| save-compatibility | 0 | 见对应日志 | logs/save-compatibility.log |
| shortage-replay | 0 | 见对应日志 | logs/shortage-replay.log |
| v231-read-python | 0 | 见对应日志 | logs/v231-read-python.log |
| v231-read-rust | 0 | 见对应日志 | logs/v231-read-rust.log |
| v231-write-python | 0 | 见对应日志 | logs/v231-write-python.log |
| v231-write-rust | 0 | 见对应日志 | logs/v231-write-rust.log |
| wasm-parity | 0 | tests=24689 | logs/wasm-parity.log |
| web-build | 0 | 见对应日志 | logs/web-build.log |

缺少门槛或证据为 无。失败门槛为 无。浏览器首轮在 macOS 同步子进程等待标准输入结束时中断。测试载入临时自动生成的存档文件后重跑完整浏览器套件。浏览器执行同一冻结游戏源码。旧存档兼容记录、历史运队与跨后端检查点见结构化结果。

[所有命令](../checks/technical-gates.json) · [存档兼容性](../checks/compatibility.json) · [历史运队索引](../data/historical-transport-replay-index.csv) · [观察器状态等价](../checks/observer-equivalence.json) · [同气候分组年度对照](../data/agricultural-weather-identity.csv)
