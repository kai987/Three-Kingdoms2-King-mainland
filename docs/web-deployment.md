# 線上遊戲與靜態發布

線上入口：<https://kai987.github.io/Three-Kingdoms2-King-mainland/>。

GitHub Pages 只提供靜態檔案。遊戲在瀏覽器的專用 Web Worker 裡執行與本機版相同的 Python 戰役規則；使用自託管 Pyodide，不依賴一台長期開機的本機伺服器。畫面、繁中／日文、地圖、音樂、肖像及 Rust 行軍 WASM 沿用目前發布的資源。

首次開啟需要下載 Python／WASM 核心及目前劇本，後續切換劇本按需下載。請等候載入完成；這是可玩遊戲，不是專案說明頁。瀏覽器必須支援 WebAssembly、Web Worker、Fetch 及 gzip 解壓縮。不要直接以 `file://` 開啟建置結果。

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
