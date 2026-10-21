# 三國・大陸戰役

原版像素風格的Web戰略遊戲：**最多115城、每城30人、25個劇本、1023名人物，繁體中文／日本語切換**。現有開局依年代開放109～114城，後續新城按年月開放；每方出戰最多10人。

```sh
# 已安裝Rust1.93.0與wasm32-unknown-unknown目標時，先建置原生核心
python3 game/build_march_core.py
python3 -I -S -B game/serve.py --port 8878
```

開啟 [本機遊戲](http://127.0.0.1:8878/)。需要Python3.10以上，無需原ROM或原模擬器；目前只監聽本機。已建置的原生行軍核心會自動啟用；沒有Rust工具鏈時可直接執行第二行，以Python相容後端啟動。瀏覽器的行軍預覽使用隨附WASM，失敗時採用伺服器報價。

載入頁面先預覽最新劇本地圖，確認開始後才建立新戰役；可繼續原存檔。地圖支援滑鼠／觸控拖曳及1～4倍縮放，勢力配色、城名與介面可即時切換語言。

- [啟動、操作、存取與規則](game/README.md)
- [城市年代資源與存檔相容](docs/scenario-economy-v14.md)
- [武將逐劇本安置審計](docs/officer-placement-audit.md)
- [本機與雲端存檔方式](docs/cloud-save-options.md)
- [人物擴充、任職名冊與待考範圍](docs/officer-expansion-v13.md)
- [劇本日期與配置來源](docs/dlc-scenarios.md)
- [行軍Rust／WASM建置、相容契約與驗證](docs/marching-rust-wasm.md)
- [程式優化、清理結果與Rust遷移順序](docs/code-optimization-and-rust.md)

## 程式與資料

| 路徑 | 用途 |
| --- | --- |
| `source/remake/` | Python戰役、人物、戰鬥、計略、單挑、AI、存檔及Rust行軍適配器 |
| `crates/march-core/`、`game/wasm/` | 共用Rust行軍核心、WASM及可重現建置清單 |
| `game/app.js`、`i18n.js`、`map-navigation.js` | HTML／SVG介面、繁中／日文、地圖手勢 |
| `game/serve.py` | 本機HTTP服務，僅公開明列的遊戲資產與API |
| `game/data/` | 186份戰役目錄；25份最新版，其餘供舊存檔驗證 |
| `game/config/`、`game/build_*.py` | 人物、年代、城池、道路與劇本的離線建置 |
| `game/assets/`、`game/locales/` | 地圖、原版城標定義、字型、翻譯及來源／授權 |
| `expansion/` | 地圖源場景、人物來源快照與早期匯入工具；部分仍為建置輸入 |

人物身分、當年登場、開局在籍、在野及待考分開處理。武知與德的來源／本作設計值可在人物庫查閱；人物資料沿用v13，年代資源用於新開v14戰役，舊存檔保留原目錄與規則。

## 驗證

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_remake_*.py' -v
node tests/test_remake_i18n_runtime.cjs
node tests/test_remake_map_navigation.cjs
```

GitHub Actions另會重建劇本、地圖顯示定義與雙語資料，確認已發佈資料沒有意外改寫。效能數字是指定本機場景的量測，不代表所有裝置的遊戲速度。

## 歷史逆向資料

`source/recovered/`、`source/readable_c/`、`scripts/`與`analysis/`保留原NES逆向程式、規則證據與有邊界的驗證資料；Web遊戲使用獨立的`source/remake/`，不執行控制IR或原CPU。完整原機硬體與所有流程仍未全部恢復。

歷史閱讀入口見 [恢復源碼說明](source/README.md) 與 [倉庫範圍](docs/repository-scope.md)。大型原機證據、ROM、工具鏈和封存ZIP為本機研究資料，未隨Git提交。過時概念圖與可再生快取的清理記錄見 [清理清單](docs/development-cleanup-20261022.json)。

MIT適用於本工程原創程式；遊戲參考素材、來源資料、字型與OpenCC依各自的權利及授權保留來源。
