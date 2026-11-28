# 复算说明

输入目录保留上一轮检查点、索引和两份原始危险状态的相对位置。此前发布的归档 SHA、地图、剧本及规则写在 `checks/protocol.json`。实际源代码、各阶段观测器和最后验证的源码身份写在 `checks/source-and-run-identity.json`。程序派生的战役档使用项目公开数据及种子生成。

- `data/map-directions.csv` 对 29 个开局的六个方向逐个报价。500 粮的报价通过表示在当时归属、路权、库存、人员和设施条件下可提交。实绩来自控制样本。
- `data/controlled-lines.csv` 的 `delivery` 是末端城市的实际交割，`target_transport_net` 另外扣除从目的城领取的返程口粮。货粮、口粮、返程、命令书、武将日及中转吞吐分别保留。R02 的拒绝报价没有实绩。
- `data/fixed-actual-consumption.csv` 取每个固定需求的原属、城池和原扣粮旬。应付、实付、人口和兵力只取该笔真实扣粮。混合库存的本地市场归因是可证下界。没有观察到原属目标扣粮时保留空值。
- `data/southern-checkpoints.csv` 包含实际扣粮和 282 号军队饥损，流向、候选和在途回合见 `raw/south/`。`data/historical-convoy-comparison.csv` 保留运队状态、合法接收、实际归队及损失。仍在途的记录保留观察末值，周期不会补上理论终点。
- `data/scenario-scores.csv` 和 `data/pairwise.csv` 仅比较真实完成的同剧本、种子、策略和相同月数的战役。实付率和及时率可由实际分子及分母复算。零分母的比率为空。新增负面绝对量单列。任务发运、最终收粮和设施作业分别统计。
- `raw/fixed-final/`、`raw/south/`、`raw/historical/`、`raw/probes/` 保留各原始回放及逐事件流。观战目录保存本轮耗粮事件、军事需求、发运、城市、势力及月度数据。性能分为禁用附加观测的逐旬 CPU 与开启统计时的候选／搜索计数。

## 验证归档和逐批账

将 `validation/v3042` 记为 `EVIDENCE`，由对应的代码工作树运行。

```sh
python3 -B tools/economy-balance/v3042_verify.py "$EVIDENCE" \
  --index SHA256SUMS.txt --lines raw/mechanism --streams raw/quick
```

复算脚本从实际事件逐笔恢复前后余额、批次父子关系和城市扣账。失败路径保留只读报价证据。设施交付按第一次真实目的城收粮的日期计一次。已发生的损耗、延期消耗和缴获仍计入同一链账。

## 在同引擎复放

将验证专用代码检出到记录的 SHA。主分支对照使用 `d8b507ec813cc50f890c74bafbdc9a1586738621` 的独立引擎工作树。原始输入及配置完全相同。无需玩家私人存档。

```sh
gzip -cd "$EVIDENCE/raw/fixed-stable/results.json.gz" > build/reference-main-v3042.json
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3042_experiments.py fixed build/fixed-v3042 \
  --inputs "$EVIDENCE/inputs" --reference "$EVIDENCE/summary/checks/replay-inputs.json" \
  --baseline build/reference-main-v3042.json
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3042_experiments.py south build/south-v3042 \
  --inputs "$EVIDENCE/inputs" --reference "$EVIDENCE/summary/checks/replay-inputs.json"
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3042_experiments.py historical build/convoys-v3042 \
  --inputs "$EVIDENCE/inputs" --reference "$EVIDENCE/summary/checks/replay-inputs.json"
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3042_experiments.py performance build/perf-v3042 \
  --inputs "$EVIDENCE/inputs" --reference "$EVIDENCE/summary/checks/replay-inputs.json"
```

固定组保留 221 天气，南方、性能及自然观战采用原回放或协议所指定的实际规则。运队 3634 原档已持久化物理容量与吞吐排行，复放保留这一背景，纯并发 D2 对照记为阻塞。正式观战只有在固定检查的两个背景分别准入后才执行。自然观战用原清单指定的五个稳定背景配对及四个 D2 背景配对。

```sh
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3042_experiments.py quick build/quick-v3042 \
  --gate "$EVIDENCE/summary/checks/quick-admission.json" --workers 4
```

正式观战目录复制到任意新路径均可重算。保持内部目录关系，再运行 `v3042_experiments.py summarize`。若从 ZIP 下载，先验证各包的 SHA-256，再按各包原路径解压。
