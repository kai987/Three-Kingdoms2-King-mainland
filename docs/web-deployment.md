# 線上遊戲與靜態發布

線上入口：<https://kai987.github.io/Three-Kingdoms2-King-mainland/>。

GitHub Pages 只提供靜態檔案。遊戲在瀏覽器的專用 Web Worker 裡執行與本機版相同的 Python 戰役規則；使用自託管 Pyodide，不依賴一台長期開機的本機伺服器。畫面、繁中／日文、地圖、音樂、肖像及 Rust 行軍 WASM 沿用目前發布的資源。

首次開啟需要下載 Python／WASM 核心及目前劇本，後續切換劇本按需下載。啟動介面依實際進度顯示版本清單、資料下載與執行環境準備、戰役初始化。累計遊戲資料讀取量不含Pyodide執行環境，不以計時器模擬完成比例；重試讀取的流量也會累計。請等候載入完成；這是可玩遊戲，不是專案說明頁。瀏覽器必須支援 WebAssembly、Web Worker、Fetch 及 gzip 解壓縮。不要直接以 `file://` 開啟建置結果。

## 啟動、失敗與重試

版本清單通過驗證後，Python程式包、主選單預覽、初始劇本與Pyodide執行環境並行準備；遊戲資料通過來源路徑、大小與SHA檢查，且執行環境就緒後，才初始化戰役。遊戲資料的網路下載最多嘗試3次，每次有逾時及大小上限；僅網路或408、429、5xx等暫時性錯誤重試，明確的不可用資源、資料超限或完整性不符不放寬接受。執行環境的準備狀態單獨顯示，不宣稱已量測其完整下載位元組。

首次引擎就緒前，載入失敗會保留可見錯誤與「重試載入」按鈕；重試會終止失敗的Worker並建立新的初始化流程。成功就緒後若執行中斷，不允許以該按鈕悄悄重建戰役，提示重新整理後讀取存檔。待處理操作會失敗返回，不自動重放命令、載入、保存或任何寫入；無法確定回應的操作不能靠重送取得成功畫面。

## 本機預覽發布包

```sh
npm ci --prefix tools/web-runtime --ignore-scripts
python3 -B game/build_web.py
python3 -m http.server 8890 --bind 127.0.0.1 --directory build
```

瀏覽 <http://127.0.0.1:8890/web/>。使用子目錄預覽能同時檢查 GitHub 專案網址的路徑邊界。原本的本機模式仍可透過 `python3 -I -S -B game/serve.py` 啟動；靜態建置不改寫 `game/index.html` 或本機執行中的戰役。

建置目錄預設為 Git 忽略的 `build/web/`，可用 `--output` 指定其他位置。工具只會替換帶有本工具 `runtime/build.json` 標記的非空目錄，拒絕覆寫來源及不明目錄。

## 發布內容及存檔相容

`game/build_web.py` 從 `game/serve.py` 的靜態允許清單與已驗證素材索引讀取公開資源。它不複製整個工作目錄，也不包含 ROM、模擬器狀態、歷史開發圖、SMTP 密碼、私人金鑰、`.env` 或雲端來源設定檔。單挑外觀的公開 JSON 是原本伺服器明確允許的例外；其他 `game/config/` 內容不發布。

所有 `game/data/campaigns/index.json` 列出的原始劇本以原始位元組 gzip 壓縮。`runtime/engine-manifest.json` 內的 `sha256` 及 `bytes` 指解壓後的原始資料，與本機 Catalog 身分完全相同。建置不執行 `build_campaigns.py`，不改格式、不重排 JSON、不變更劇本校驗值或亂數規則。原始戰役存檔的驗證仍由相同規則執行，過期或受損的存檔不會被靜態發布放寬接受。

引擎清單格式為 `tk2-browser-engine-v1`，包含：

- `pyodide_version`：固定 `314.0.7`。
- `python_bundle`：`runtime/python.zip` 的網址與 SHA256；其中保留 `source/remake/` 及 `game/assets/map-presentation.json` 的原始相對位置。
- `previews`：預編 `CampaignSession._scenario_previews()` 產物的網址與 SHA256，讓主選單不必載入所有劇本。
- `catalogs`：每個劇本的 `id`、壓縮檔網址、虛擬檔案系統路徑、原始 SHA256 與原始長度。
- `initial_scenario`：目前索引最後一個劇本，與本機 CampaignSession 的預設一致。

`runtime/build.json` 記錄發布 commit、每份程式及素材的 SHA256／長度，以及整體內容清單 SHA256，供部署後比較實際線上位元組。它不包含任何玩家進度。GitHub Pages 不提供伺服器端本機存檔；線上遊戲的進度保存在該瀏覽器／雲端槽位中，與本機伺服器記憶體中的進度互不覆寫。

## 顯示與傳輸的重用範圍

瀏覽器可選用`view_cache`傳輸協定，首次取得不變的人物基本資料、劇本預覽及地圖設定後，以內容token在同一分頁重用；人物目前的登場狀態、所屬、所在地及生存狀態仍更新。行軍報價以資料集、玩家、月份、有效城池及其歸屬、發現航路的組合判斷失效，不代表已省略所有路徑計算。完整視圖可由前端還原，未選用協定的呼叫保留原有完整回應。

視覺輸入相同的地圖保留原SVG與相機，避免編兵等命令重建路網及導航監聽器；歸屬、日期、地名、路線、顯示與目標高亮等變更仍重新繪製。這些是介面與唯讀資料的優化，不變更戰役規則、亂數或存檔JSON。

## 自動恢復與手動保存

新戰役、旬末、戰鬥結果／結算及載入後，瀏覽器另存最近3份本地自動恢復點，容量不足時會減少保留份數。恢復點保存原始JSON字串，與手動瀏覽器存檔和雲端5個槽位分開，不會自動上傳或覆蓋它們。在「讀取進度」中選擇恢復點並明確確認後，才交由原有存檔驗證載入；頁面開啟時不自動取代戰役。

自動保存失敗會顯示提示，不中止戰役。瀏覽器儲存可能被停用、清除或因配額失敗，重要進度仍應明確保存至JSON或雲端；關頁前請確認保存狀態。恢復點與傳輸快取不是發布包內容，也不會被部署流程帶到GitHub。

## Python 核心來源

Pyodide 使用精確版本的官方 npm 產物：

- 來源：<https://registry.npmjs.org/pyodide/-/pyodide-314.0.7.tgz>。
- `package-lock.json` 固定完整依賴、下載位址及 npm SHA512 integrity。
- 建置器再比對六個實際發布核心檔的固定 SHA256。
- 核心檔、Python 標準庫及鎖定清單都發布在 `vendor/pyodide/`；遊戲執行時不從 CDN 載入 Python 核心。
- MPL-2.0 授權來自官方 `pyodide/pyodide` commit `b1e4fcc2488962f6360a97f19b9982d6fdb5d16f` 的 `LICENSE`，本地副本及 SHA256 一起保留。

官方部署說明：<https://pyodide.org/en/stable/usage/downloading-and-deploying.html>；固定版本來源：<https://github.com/pyodide/pyodide/releases/tag/314.0.7>。

## 雲端登入與寄信

建置從既有驗證器 `public_config()` 取得公開 Supabase 網址及 publishable key，產生最小化的 `cloud-config.json`。它不發布原始設定檔，也不包含 SMTP／service-role 憑據。資料擁有權仍由雲端資料表的 RLS 驗證。

線上註冊確認與忘記密碼的精確回跳地址 `https://kai987.github.io/Three-Kingdoms2-King-mainland/` 已獲使用者批准，並已加入遠端認證白名單。發布器固定以此值產生 `confirmationRedirectUrl`，不根據瀏覽器網址或建置參數猜測認證目的地。本機來源設定中的 `http://127.0.0.1:8878/` 保持原樣，不會進入線上發布包；共享專案的 Site URL 與其他應用白名單也不由建置器改寫。已存在的帳號可直接登入並操作雲端槽位，新帳號確認及重設密碼則可返回本遊戲線上入口。

## GitHub Actions 與線上驗收

`.github/workflows/pages.yml` 在 `main` 更新或手動觸發後，先安裝鎖定核心，執行 Python／瀏覽器檢查並建置發布包，再透過 Pages 專用 artifact 部署。各 Action 以完整 commit SHA 固定；部署工作才獲得 `pages: write` 與 `id-token: write`。不需要把 Supabase 管理權限或私人憑據加入 Actions。

發布後仍須檢查正式網址實際載入、劇本選擇、勢力開戰、一次可見操作、存檔讀回及 console／網路錯誤。Actions 成功只表示建置與部署成功；正式環境的操作及資料校驗應另外驗收。可將線上 `runtime/build.json` 的 commit、內容清單與本機同一 commit 的發布包比較，避免只檢查到舊快取的首頁。
