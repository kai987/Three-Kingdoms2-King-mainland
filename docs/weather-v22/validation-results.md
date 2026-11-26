# 验证与复现

本地隔离分支源自 `099b2ccc57590f6345fc41e5fb89688375051ed7`。每局保存运行时源树哈希、剧本哈希、游戏种子、独立天气种子、天气阶段和 AI 配置。原有五份基准压缩包按 SHA-256 引用。

## 规则和实现文件

| 范围 | 文件 |
|---|---|
| 气候与计算 | `source/remake/climate_regions.py`、`winter_weather.py`、`winter_travel.py`、`winter_strategy.py` |
| 战役和行军 | `source/remake/campaign.py`、`campaign_expansion.py`、`travel.py`、`march_preview.py`、`march_supply.py`、`battle_reinforcements.py` |
| 运输和供粮 | `source/remake/logistics.py`、`logistics_rules.py`、`army_relief.py`、`transfer_supply.py`、`staging_supply.py`、`grain_relief.py` |
| 战略和预算 | `source/remake/ai_core.py`、`strategic_ai.py`、`faction_economy.py`、`military_budget.py`、`war_recovery.py` |
| 浏览器界面 | `game/app.js`、`battle-supply.js`、`domestic.js`、`march-supply.js`、`style.css`、`build_message_locales.py`、`locales/messages-ja.json`、`locales/zh-hant.json` |
| 测试和观战 | `tests/test_remake_winter_weather.py`、`tests/browser_engine_smoke.mjs`、`tools/ci/test-groups.json`、`tools/economy-balance/observe.py`、`v22_experiments.py`、`v22_routes.py`、`v22_report.py` |
| 文档 | [V2.2 使用、规则、验证及限制](README.md) |

29 个剧本的路线验收包含 14,328 个方向与月份组合。24 个方向因原游戏单向限制保持不可通行。14,304 个合法组合各测试 8 种天气条件，共 114,432 条报价，348 条因完全冰封暂停通行。原有方向和时长也由 Python 与 Rust 后端分别核对。平原十日、10,000 兵和 1 将的标准报价为平常 2,525 粮、小雪 12 日及 3,277 粮、大雪 14 日及 4,472 粮。

高强度压力夹具令支持降雪的区域每旬产生暴雪并放慢融雪，覆盖积雪封顶、冻结河段禁航和紧凑存档重放。夹具在测试进程内注入。

## 复现命令

```sh
python3 -B game/build_march_core.py --check
MARCH_CORE_BACKEND=python python3 -B -m unittest discover -s tests -p 'test_remake_*.py'
MARCH_CORE_BACKEND=rust python3 -B -m unittest discover -s tests -p 'test_remake_*.py'
node tests/march_wasm_parity.cjs
node --test tests/test_remake_*.cjs
python3 -B tools/economy-balance/v22_routes.py
python3 -B tools/economy-balance/v22_experiments.py stages --hash-turns
python3 -B tools/economy-balance/v22_experiments.py matrix
python3 -B tools/economy-balance/v22_experiments.py long
python3 -B tools/economy-balance/v22_experiments.py holdout
python3 -B tools/economy-balance/v22_report.py --package
```

验收包使用真实运行流水与验证记录。浏览器用本地静态构建及 Chromium 执行，运行真实的 Pyodide Worker。历史官渡存档的匹配目录和回放范围见[存档兼容](save-compatibility.md)。

## 回归结果

| 验证范围 | 实际结果 |
|---|---|
| Python 后端全量发现 | 1,877 项，1 项按后端条件跳过。发现繁体离线资源重建与日文错误信息两项失败 |
| Rust 后端全量发现 | 1,877 项。报告同一日文错误信息失败 |
| 本地化修复复测 | 双后端资源重建和日文消息校验通过 |
| 最新天气与战术回归 | Python、Rust 各 41 项通过，包含实际行军进度、援军未到折返的存粮和存档校验 |
| Rust 单元和 ABI | 16 项通过，格式与 Clippy 通过 |
| Rust／WASM | 24,689 组 Python 参考向量一致 |
| Node 24 前端 | 66 项通过 |
| 浏览器运行时 | 实际 Pyodide 314.0.7 的 63 条请求与 CPU Python 重放一致，包含天气和策略 212 各推进三旬，普通与紧凑存档检查在专项测试中完成 |
| 浏览器界面 | 1440×1000、430×920 验证地图和城市天气，另验证繁体中文与日文切换 |

在分阶段、五年及二十年样本中，定期将实际紧凑存档导入独立引擎并核对原始导出。矩阵中的源树与配置见 `simulation-manifest.json` 和包内的 `checks/`。修复后的专项复测与原全量检测分别记录。

## 观战验收

共完成 118 局真实战役。W0–W5 各覆盖三个 12 个月用例。H0–H3 的五年矩阵覆盖七个剧本及种子 2026–2028，二十年矩阵覆盖黄巾与赤壁的种子 2026。独立种子 2031 在反董卓与赤壁执行四组配对。

G4a 使用 60%／55% 基准档。初期 55%／45% 试跑以正确档重跑后交付。G4a 的 221-07、种子 2026 曾在第 52 回合遇到雪天援军折返的工作量校验错误。修复后同一配置完成 180 回合。前 51 回合的月度、城市和势力记录一致，验证见 `checks/reinforcement-return-replay.json`。
