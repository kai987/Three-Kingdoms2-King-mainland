# 复算与复现

从 `data/simulation-manifest.json` 定位每局的 Git SHA、工作树及规则。 `sources/` 保存入账探针和各批次执行时使用的文件哈希。包里的脚本依赖对应源码提交和仓库原有观战工具，请在该源码的仓库根目录运行。全部数据使用原有地图目录和实际随机种子。

```sh
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v301_experiments.py long initial winter holdout --groups R0 R1
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v301_experiments.py long initial winter holdout --groups R2 R3 --output build/regional-economy-v301/final-candidates
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v301_experiments.py initial --groups R0 R2 --scenarios 208-10 --output build/regional-economy-v301/warehouse-account
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v301_commercial_fixture.py --output build/regional-economy-v301/checks/commercial-fixture.json
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v301_replay_1706.py --output build/regional-economy-v301/replay-1706
python3 -B tools/economy-balance/v301_report.py --package
```

报告使用 `checks/prior-archives.json` 的已验证上一阶段路径。打包时同一模拟身份可选择后续重放采到更完整的同输入收据。每个来源单独留存文件哈希和日期。解压后标准 `shasum -a 256 -c SHA256SUMS.txt` 核验完整性。
