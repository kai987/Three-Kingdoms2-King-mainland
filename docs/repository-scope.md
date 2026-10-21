# 倉庫範圍與本機資料

本倉庫目前包含可玩的Web重製戰役、離線資料建置與來源，以及原NES的歷史逆向程式和選取證據。入口與目前功能以根目錄 [README](../README.md) 及 [遊戲說明](../game/README.md) 為準。

## 現行遊戲

- `game/serve.py`與`source/remake/`：Python標準函式庫執行，不需要ROM或原模擬器。
- `game/`的HTML／JavaScript、地圖、字型與雙語資料：瀏覽器介面。
- `game/data/`：161份可校驗戰役目錄，25份最新版。保留舊目錄是存檔相容需求，不能只因版本舊就刪除。
- `game/config/`、`game/build_*.py`及`expansion/`：離線劇本、人物和地圖建置；v41地圖及人物來源快照仍被現有建置使用。

目前最多115城、每城30人、1023名人物；開局依年代開放城池與人物，史實、IF及本作推定分開記錄。屬性齊全不代表當年已在籍，完整駐軍與歷史事件仍有待考範圍。

## 歷史逆向研究

`source/recovered/`、C11純函式庫、`scripts/`和選取的`analysis/`資料保留原機行為與恢復邊界。大型逐幀軌跡、原始音畫、模擬器存檔、Ghidra／REA工具鏈及歷次唯一封存ZIP在本機保留，未隨Git提交。克隆倉庫可執行現行Web遊戲，無法單憑公開檔案重跑全部原機審計。

原ROM：524304位元組、Mapper19、SHA-256 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。原輸入保持唯讀；歷史回執中的絕對路徑是當時證據，不表示其他電腦可直接使用。

REA上游基準為 `0043d9b134c0a353e8bf85c0bde4492275f1f720`，來源 [morluto/rea](https://github.com/morluto/rea)。本機6502適配補丁、來源和鎖檔保留；已清除的`tools/rea/node_modules`可按鎖檔重新安裝。這不是現行Web遊戲的執行依賴。

`docs/repository-files.txt`及`publication-inventory.json`為早期發布清單與大型證據盤點；目前追蹤路徑以`git ls-files`為準。舊音畫／原機證據連結可能只在保留完整本機資料時可用。

## 2026-10-22清理

刪除可再生的REA安裝依賴、非凍結編譯中間檔、驗收暫存與Python快取，以及不再被引用的早期介面概念圖。唯一原機證據、素材／能力來源、授權及目錄均保留。兩個固定引用的重複ZIP使用APFS寫入時複製共享資料塊，保留各自可獨立寫入的普通檔案、路徑及SHA。

明細與重建方式見 [清理記錄](development-cleanup-20261022.json)，效能與Rust評估見 [優化說明](code-optimization-and-rust.md)。

## 授權

MIT適用於本工程原創程式。原遊戲與參考素材、官方人物資料、第三方年表、字型及OpenCC依各自來源／授權；來源快照、哈希、許可文件及未確定項保持可追溯。
