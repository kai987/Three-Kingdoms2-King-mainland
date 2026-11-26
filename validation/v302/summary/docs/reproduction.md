# 复现

源码以区域经济 V3.0.1 基准 `dae702d60dc471803abe31bed2c3827cb3629920` 接续。观战清单记录实际用于运行的 Git SHA、地图和剧本 SHA、策略、天气种子、难度和全部实验开关。验收归档包含一次真实测试流水的完整记录。先比较资料包的 SHA-256，再查看其中的数据清单。

以下流程从仓库根目录执行。Python 与 Node 使用仓库固定版本，Rust 使用 1.93.0 及 wasm32-unknown-unknown。

```sh
RUSTUP_TOOLCHAIN=1.93.0 python3 -B game/build_march_core.py --check
MARCH_CORE_BACKEND=python python3 -B -m unittest discover -s tests -p 'test_remake_*.py'
MARCH_CORE_BACKEND=rust python3 -B -m unittest discover -s tests -p 'test_remake_*.py'
node --test tests/test_remake_*.cjs
node tests/march_wasm_parity.cjs
python3 -B tools/economy-balance/v302_backends.py --turns 18
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v302_experiments.py rapid long dry winter holdout smoke --groups S0 S1 S2 S3 S4 --workers 8 --output build/v302
python3 -B tools/economy-balance/v302_report.py build/v302 --prior /path/to/three-kingdoms-regional-economy-v301-validation-repacked.zip
```

首轮基准 S0沿用 R0。S1沿用 R2。S2只加储备及返程管理。S3加入主动调粮和有天气时的冬季储备。S4打开单站中转。保留种子2034与其他矩阵保持独立。研究样本以指定截止月或实际自然结束时间为准。

前端验收前安装固定 Runtime 和浏览器依赖，运行 `python3 -B game/build_web.py --output build/web`。用 `tests/browser_static_server.mjs` 提供同样的 GitHub Pages 子路径，在另一个终端用 `tests/browser_granary_smoke.mjs` 连续检查两个视口。浏览器受控存档和命令见归档的脚本及证据。
