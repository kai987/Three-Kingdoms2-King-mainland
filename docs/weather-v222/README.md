# 运输应急机制 V2.2.2

新战役可以单独启用运输应急。默认仍使用 AI 策略 211，天气和运输应急都关闭。启用运输应急时，原有无天气、22 或 221 气候规则仍可独立选择。实验中用 I3、J1、J2 和 J3 分别评估原规则、分段撤离、增加运队接济以及增加枯竭任务处理。

- [出发和撤离预算](emergency-ration-budget.md)
- [分段撤离与安全节点](staged-evacuation.md)
- [普通运队接济](ordinary-convoy-relief.md)
- [救济依赖和承诺](relief-dependency-safety.md)
- [结束收据与资源归属](convoy-terminal-resolution.md)
- [历史异常回放](convoy-77-root-cause.md)
- [数据字典和口径](transport-survival-metrics.md)
- [存档兼容](save-compatibility.md)
- [性能](performance-results.md)
- [专项和整局验证](validation-results.md)
- [长期平衡](long-term-balance-results.md)
- [已知限制](known-issues.md)
- [后续开发边界](regional-economy-readiness.md)

## 复算

在项目目录执行。先使用仓库固定的 Rust 1.93.0 和 Node 24。天气基准压缩包的绝对路径和 SHA-256 记在验收清单中。

```sh
python3 -B game/build_march_core.py --check
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v222_experiments.py focus paired long --workers 7
python3 -B tools/economy-balance/v222_report.py --output build/weather-v222 --previous /absolute/path/three-kingdoms-weather-v221-validation.zip --package
```

旧轨迹使用原版运行时复现，三条重点运队以原剧本、种子、来源、最初目的地和逐日流水核对，再从真实记录的检查点分支测试。工作中的检查点存档用于本地复算，交付包包含逐日记录的校验结论和检查点证据。
