# 三國・大陸戰役

[日本語（主文件）](README.md) · **繁體中文** · [線上遊玩](https://kai987.github.io/Three-Kingdoms2-King-mainland/)

原版像素風格的 Web 戰略遊戲：25 個劇本、最多 115 城、每城歷史武將與文吏合計 99 人、每方出戰 10 人、1,023 名歷史人物，繁體中文／日本語切換。每旬10日，城池與人物按年月登場，開局資源依劇本配置；四種主要場景使用原版配樂。

線上版在每個瀏覽器分頁的 Worker 中執行相同戰役規則，無需開啟本機伺服器。首次需下載 Python／WASM 與劇本；關閉或重新整理前，請明確保存至瀏覽器、JSON 檔案或雲端槽位。新戰役建立、旬末、戰鬥結算及載入後，另在本瀏覽器保留最近3份自動恢復點；空間不足時可能減少份數。「讀取進度」可選擇恢復點，確認後才取代目前戰役。自動恢復點不覆寫手動存檔、不自動傳到雲端，並保留原始JSON存檔格式。靜態建置與部署方式見[線上發布](docs/web-deployment.md)。

靜態Web版顯示實際啟動階段與已讀取的遊戲資料位元組數（不含執行環境），獨立資源並行下載，一時性錯誤採有限重試。只有引擎首次就緒前能以重試按鈕重建Worker；遊玩中的中斷不自動重開戰役或重送寫入命令。

地圖視覺未變時復用SVG與相機，歸屬、日期、城名、路線或高亮等變化仍安全重建。瀏覽器的可選`view_cache`協定不重傳已知且不變的人物與劇本資料；行軍報價按資料集、玩家、月份、有效城池歸屬與發現航路失效，不改規則、亂數或存檔，也不代表所有路線計算均已快取。

地圖支援滑鼠拖曳、滾輪及觸控移動／縮放，倍率為100～400%。上方保留主要存讀操作，語言、勢力內政、人物庫、事件回顧、規則與音樂集中至「更多」；右側按劇本選擇／城池命令分組，小螢幕改為上下排列。陰平西側紅棕山腳與陰平—成都間綠峰的素材、修改範圍及原圖見[地形素材記錄](art/map-western-range-v3/README.md)。

```sh
python3 -B game/build_march_core.py
python3 -I -S -B game/serve.py --port 8878
```

開啟 http://127.0.0.1:8878/ 。需要 Python 3.10+；建置行軍核心需要 Rust 1.93.0 與 wasm32-unknown-unknown。遊戲執行不讀取 ROM 或模擬器。

- [操作、存檔與規則](game/README.md)
- [目前 AI 與事件畫面](docs/ai-and-events.md)
- [原版風格戰場、兵陣與單挑演出](docs/battle-scenes.md)
- [地方文吏的候選、雇用、薪俸與獨立身分](docs/civil-staff.md)
- [兩名內政官、共用自動人事與前線運輸](docs/domestic-delegation.md)
- [武將歸城與登場統計](docs/officer-placement-audit.md)
- [原版德、SAN14能力與經驗欄位來源](docs/officer-attribute-sources.md)
- [雲端帳號存檔](docs/cloud-save-options.md)
- [本機服務安全邊界與效能](docs/runtime-safety.md)
- [原版像素肖像與來源](docs/officer-portraits.md)
- [128×160肖像強化、原圖保留與檢查](docs/portrait-enhancement.md) · [1,023人原圖／新版對照](art/portraits/enhancement-v1/index.html)
- [特殊道路、季風與減員](docs/hazardous-travel.md)
- [Rust／WASM 行軍核心](docs/marching-rust-wasm.md)

目前只維護一套戰役資料，不載入舊版劇本或遷移歷史存檔。人物能力、歸城依據、原典與遊戲推定保留；舊版逐級生成器與相容目錄已移除。存檔仍驗證目前劇本、資料 SHA、狀態校驗和及回合版本，失敗不覆寫正在遊玩的戰役。

地方文吏使用 `clerk-000001` 類獨立 ID，不占1,023名歷史人物的 ID；雇用後可編兵、出戰、單挑、轉屬與繼承。玩家與 AI 共用民政官／軍備官委任、自動登用／勧誘、募兵訓練與真實前線運輸，遵守同一城市行動、費用、地形風險與亂數規則。都市情報顯示武、知、德、忠、經及體力；共34類圖文事件包含內政摘要與運輸出發、抵達、返程及災害。

戰場以1024×960畫布呈現，維持原版256×240的顯示比例。單挑提供12類兵器、13類坐騎外觀，27位具名人物另有來源或本作演繹設定；這些外觀不增加裝備性能。旗標通常顯示姓名首字，同一陣營有同姓武將時，僅該陣營該姓的旗標改顯示姓名末字；敵我分開判定，名單和情報保留全名。城池「訓練度」是駐軍訓練指標，與原版暫時戰術「士気向上」分開處理。

| 路徑 | 用途 |
| --- | --- |
| `source/remake/` | Python 戰役、人物、戰鬥、AI、交易與存檔 |
| `crates/march-core/` | Rust 路徑、地形、季風與減員計算 |
| `game/` | 畫面、地圖、肖像、語言與本地／雲端存檔介面 |
| `game/config/campaigns/` | 唯一的劇本來源：共享人物、地圖資料與逐劇本差異 |
| `game/data/campaigns/` | 25 份目前可玩的生成資料 |
| `game/config/references/` | 原典任職、年代、能力及遊戲參考資料 |
| `game/config/map-source.json` | 已批准地圖、城標與座標來源 |
| `art/portraits/`、`tools/portraits/` | 肖像素材、來源證據及離線處理工具 |
| `supabase/`、`tools/cloud-sdk/` | 私人雲存檔資料表、帳號整合與固定版本 SDK |
| `tests/` | 目前玩法、存讀、語言、介面及 Python/Rust/WASM 差分測試 |

```sh
python3 -B game/build_campaigns.py --check
```

修改人物時使用穩定 `person_id`。`people.json` 保存共同人物，`scenarios/*.json` 只記錄各劇本差異；`build_campaigns.py` 完全離線，無須先生成任何舊版。共享資料及差異格式見 [建置說明](game/README.md)。

規則、介面夾具、真實WASM、瀏覽器操作與跨年戰役的命令及驗證邊界統一見[遊戲驗證與回放](docs/testing.md)。長期回放以184、217、263年三個劇本、各兩個種子對照Python／Rust後端，每月與繼承後核對存讀、亂數及兵員守恆；經濟成長、前線缺員及運輸停滯屬觀察資料，通過回放不等於已證明玩法平衡。

程式採 MIT 授權；第三方程式、字型、轉換表及原遊戲圖像、音樂的來源與授權各自列明，見 [授權說明](docs/licenses/README.md)。
