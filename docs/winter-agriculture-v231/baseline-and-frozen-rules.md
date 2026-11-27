# 冻结基准与观战配置

V2.3.1 从 V2.3 的合并提交开始。上一轮验收档保留原始 W0/W4 输出。 [V2.3 合并提交](https://github.com/kai987/Three-Kingdoms2-King-mainland/commit/e845f974521051dc6aa2a8ea7e65c9036124a760) · [V2.3 验收资料](https://github.com/kai987/Three-Kingdoms2-King-mainland/tree/codex/winter-agriculture-v23-validation-archives/validation/v23/summary)

降雪概率、积雪上限、融雪、冰封、异常寒潮及农业实际倍率继续由 V2.3 模块结算。候选使用 23 气候和独立的 231 预报字段。

| 分组 | 实际天气 | 季节预测 | 农业实际乘数 | 农业风险备粮 |
| --- | --- | --- | --- | --- |
| F0 | 221 | 原版 | 旧规则 | 旧规则 |
| F1 | 23 | V2.3 | 启用 | 关闭 |
| F2 | 23 | V2.3 | 启用 | 启用 |
| F3 | 23 | V2.3.1 | 启用 | 关闭 |
| F4 | 23 | V2.3.1 | 启用 | 启用 |
| W2 | 23 | 上一轮 W2 | 关闭 | 关闭 |
| dry | 无天气 | 无 | 常规 | 无 |

新观战采用农业经济 V2、市场 301、战略粮仓 302 G1、G2 路线性能优化、应急运输 222 和 D0 背景，关闭 V3.0.4 中转与额外寒潮。保留种子 2043 和 2044 在候选冻结后执行。2041 用于复查上一轮。

在仓库根目录从清单记载的冻结源码执行，首轮气候正常值和固定路线分别由 v231_normals.py 和 v231_routes.py 生成。独立汇总需要 V2.3 的只读汇总、前置气候及原版审计复跑目录和本轮观战目录。

```sh
RUSTUP_TOOLCHAIN=1.93.0 python3 -B game/build_march_core.py --check
MARCH_CORE_BACKEND=rust python3 -Bu tools/economy-balance/v231_observe.py quick five holdout --workers 4
MARCH_CORE_BACKEND=rust python3 -Bu tools/economy-balance/v231_observe.py long --workers 4
python3 -B tools/economy-balance/v231_normals.py --help
python3 -B tools/economy-balance/v231_routes.py --help
python3 -B tools/economy-balance/v231_replay.py --help
python3 -B tools/economy-balance/v231_report.py --help
python3 -B tools/economy-balance/v231_verify.py --help
```

候选固定路线地理与天气分配使用 300000 开始的种子，独立路线验证使用 400000 开始的种子。公开正常值的模拟分别从 100000 与 200000 开始。
