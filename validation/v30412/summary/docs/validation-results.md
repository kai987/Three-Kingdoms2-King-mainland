# 技术回归

最终游戏源码 `749967c2a7292b0d4c426216bdcfbcd67ba6f4a6`。开发分支在该提交之后增加验收工具和文档。浏览器构建、规则源码和自动测试文件均来自同一最终版本。

## 本地验证

- Python 全量规则测试 2,008 项通过，1 项按条件跳过。Rust 全量规则测试 2,009 项全部通过。28 项运输统筹专项覆盖旧规则、存档、真实补给、备用时间、负载验证及观测前后的随机数和存档相等。
- Node 的 66 项、Rust crate 的 16 项、Rust 格式与 Clippy 检查全部通过。固定工具链生成的原生及 WebAssembly 核心均通过构建校验。
- 发布版本使用的 Pyodide 314.0.7 执行真实 Worker，比较同一命令流在 CPU 和 WebAssembly 中的精确存档及随机数。另有 24,689 项 Rust/WASM 行军向量。
- 桌面和 390×844 触控浏览器均运行三组。首轮 113 项通过，1 项桌面用例的 Python 测试夹具超过原设定的 90 秒。用相同引擎和原超时配置单独复跑，同一项通过。失败记录、脱敏后的浏览器 trace、两次计时和截图均在技术分包。
- 繁体中文与日文均验证独立开局实验开关和运输账本。两种行军补给测试配置各通过 4 项，每种配置对不适用的 2 项按测试声明跳过。

[执行状态和计数](../checks/technical-checks.json) · [30 个最终源码固定窗口等价](../checks/final-source-fixed-equiv.json) · [原始日志和截图索引](../sources/raw-file-index.csv)

## 观测边界

真实口粮事件通过只读订阅采样。观测关闭和打开的领域状态、实际运输凭证和 RNG 对照已通过。复算脚本为价格、粮耗、结果和实际命令书各保留凭证。南方初次回放领先于新增终点观测字段，巴西的最终到达由最终源码另行复放。快速观战记录了二十四个月的真实运行，五年及其后阶段状态见独立的准入报告。

## GitHub Actions

首轮源码构建发现君主归属审计的日文消息哈希过期。更新该生成字段后，最终提交的全量 GitHub Actions 校验通过。公开下载的 17 个 ZIP 和内部 899 项文件均通过校验。

[首轮源代码检查](https://github.com/kai987/Three-Kingdoms2-King-mainland/actions/runs/46111379203/job/140875486491) · [最终 CI](https://github.com/kai987/Three-Kingdoms2-King-mainland/actions/runs/46111904255) · [GitHub 核对记录](../checks/github-verification.json)
