# V3.0.4.2 河陆接驳验收

[结论](summary/docs/v3042-review.md) · [固定样本](summary/docs/replay-findings.md) · [24 个月观战](summary/docs/economic-admission.md) · [复算说明](summary/docs/replay-and-fields.md) · [SHA-256](SHA256SUMS.txt)

`summary` 可直接查阅原数表、验收 Markdown、开关与 SHA 清单。`inputs` 保存与旧发布清单逐项同哈希的原始设施、历史运队、天气和军队检查点。`raw/mechanism` 保存三条真实操作证据与受控拒绝，`raw/probes` 保存额外同状态危险复放，`raw/technical` 保存操作截图，完整日志同时收在技术分包。

`bundles` 中每份 ZIP 均可独立解压，带同名 `.manifest.json`。清单含每个成员的路径、字节数及 SHA-256。解压时从 `validation/v3042` 执行，包内路径直达 `raw/` 下相应位置。旧试验和正式试验有独立目录。

- `v3042-fixed-final.zip` 和 `v3042-fixed-stable.zip` 为原始五份样本与未修改主分支的回放。
- `v3042-south.zip` 与 `v3042-historical.zip` 含八处城池及八个原始运队的逐旬数据。
- `v3042-quick-N0.zip` 至 `v3042-quick-N3.zip` 为最终 18 局的真实业务数据与期末存档。
- `v3042-preliminary.zip` 保存第一次运行，归档中的阶段结果以最终源码全面重跑的数据为准。
- `v3042-profile.zip` 和 `v3042-performance.zip` 包含独立运行的性能检查与原始采样。
- `v3042-technical.zip` 保留本地检查日志、失败及复测记录。

在代码工作树上复算。正式观战解包后，将汇总里的运行身份文件复制到对应的根目录。

```sh
for group in N0 N1 N2 N3; do
  unzip -q "$EVIDENCE/bundles/v3042-quick-$group.zip" -d "$EVIDENCE"
done
cp "$EVIDENCE/summary/checks/quick-plan.json" "$EVIDENCE/summary/checks/quick-completed.json" "$EVIDENCE/raw/quick/"
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v3042_experiments.py summarize "$EVIDENCE/raw/quick"
python3 -B tools/economy-balance/v3042_verify.py "$EVIDENCE" \
  --index SHA256SUMS.txt --lines raw/mechanism --streams raw/quick
```
