# 模組與驗證方式

| 功能 | 主要實作 |
| --- | --- |
| 分段、倍率、途耗 | `source/remake/logistics_rules.py` |
| 行軍糧袋、改道與收據 | `march_supply.py`、`travel.py`、`logistics.py` |
| 最低耗糧查找與預覽 | `transfer_supply.py`、`march_preview.py`、`session.py` |
| 戰場入糧、撤退與援軍 | `battle_supply.py`、`battle_reinforcements.py` |
| 城市預算、募兵、調糧和出征 | `military_budget.py`、`grain_relief.py`、`domestic.py`、`strategic_ai.py` |
| 瀏覽器與本地伺服器 | `game/app.js`、`game/domestic.js`、`game/events.js`、`game/serve.py`、`browser_runtime.py` |
| 存檔 | `campaign.py`、`campaign_expansion.py`、`compact_save.py` |

```sh
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/logistics_routes.py --output build/logistics-report
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/logistics_cases.py --output build/logistics-report
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/observe.py --group D --seed 2026 --months 60 --output build/logistics-report/observed/D/2026/60
python3 -B tools/economy-balance/logistics_observer_exports.py build/logistics-report/observed --output build/logistics-report --heads build/heads.json
```

運行分組使用各自 SHA 的工作樹。可把 `common.py` 和 `observe.py` 複製到比較組的 `tools/economy-balance/` 後在當地執行。全量路線先按物理路段和規則內容去重，再逐劇本核對年份、月份、城市啟用窗口及路線替代。每種配置只比較一組分段費用，重合劇本關聯保存在同一列。

在本次範圍內，版本化糧帳與搜尋由 Python 實作，瀏覽器透過 Pyodide 執行相同模組。Rust／WASM 保留既有腿段合法性、計時和風險原語。新糧帳以這些回傳的腿段產生確定性明細。獨立資料匯出腳本使用 Python 標準庫。
