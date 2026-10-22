# Web 戰役規則層

獨立 Python 規則：25 個劇本、最多 115 城、每城 99 人、每方出戰 10 人及 1,023 名人物。只讀目前 `game/data/campaigns/`，不執行 ROM、原 CPU 或控制 IR，也不註冊歷史目錄。

| 模組 | 職責 |
| --- | --- |
| `campaign.py` | 戰役狀態、亂數、原子指令、兵員守恆、驗證與存檔 |
| `officers.py` | 屬性、出生／出仕／退場、名冊、忠誠、容量與出戰 |
| `campaign_expansion.py` | 招募、勸降、16 計略、單挑、戰後處理、AI 與簡化繼承 |
| `travel.py` | 當前路網、在途部隊、到達、探索航路及 AI 行軍 |
| `route_hazards.py`、`march_core.py` | 路線風險與 Python／Rust 行軍計算 |
| `session.py` | 當前劇本切換、存讀、預覽、勢力資源與人數 |
| `map_presentation.py` | 年代城名、原版城標與可辨識的勢力配色 |
| `garrison_postings.py` | 同勢力駐防分配工具 |
| `cloud_config.py` | 雲端存檔公開設定與內容安全策略 |

總庫與當年登場分開；非連續 ID 有效，1005 保留空槽，執行期容量 1200。指令在副本執行並驗證，成功才提交；失敗保持資源、人物、兵員、亂數與版本。存檔校驗目前劇本 ID、資料 SHA 與狀態 checksum，不做舊版本遷移。

地圖預覽、語言切換與資料查看不推進回合、不抽亂數。AI 是確定性的規則決策，詳見 [AI 與事件](../../docs/ai-and-events.md)；完整外交、逐格戰術移動及自動插畫事件仍未實作。
