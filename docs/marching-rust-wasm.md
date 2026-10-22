# Rust／WASM 行軍核心

`crates/march-core/` 負責路徑搜尋、地形耗時、季風、特殊道路、減員與比例餘兵分配。Python 仍管理指令、亂數、行軍排程、戰鬥與存檔；瀏覽器透過 Worker 使用 WASM 預估，失敗可回到服務端報價。

```sh
python3 -B game/build_march_core.py
python3 -B game/build_march_core.py --check
node tests/march_wasm_parity.cjs
```

Rust 工具鏈鎖定 1.93.0，目標包含 `wasm32-unknown-unknown`。原生可執行檔與函式庫位於 `build/march-core/`，編譯快取位於 `build/march-core-target/`，Web 二進位及建置清單位於 `game/wasm/`。同宿主要求逐位元組重建一致；跨宿主由來源與產物雜湊及差分行為檢查驗證。

`MARCH_CORE_BACKEND=python` 使用 Python 參考計算，`rust` 要求原生核心，未明列時可自動選擇。後端切換不應改變目前路線報價、月份、兵員、亂數抽取或存檔內容。

計算函式不抽亂數；風暴嚴重度仍由戰役既有 xorshift32 決定。路徑預覽、語言切換與圖形縮放不影響 RNG。災害整數分配保留總數，不產生額外士兵。

目前只處理現行風險路網，不保留已移除的無風險舊劇本分支。測試覆蓋全路網月份／方向、最短路平手、敵我經過限制、探索、陰平、子午谷、季風和減員。現行待抵達隊伍也驗證跨後端存讀及下一步 RNG 一致。

使用 Rust 不等於整個遊戲已轉成 Rust，也不代表已證明全裝置加速。完整報價仍有 JSON 序列化與跨語言成本；需要用實際 HTTP／瀏覽器流程測量效能。
