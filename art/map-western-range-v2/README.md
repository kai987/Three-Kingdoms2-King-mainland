# 陰平與西南山腳：移除兩座遮擋高山的綠色山峰

此版只修正使用者圈出的兩座綠山，露出相鄰紅棕色高山及山腳。整張地圖仍為 1352×1024，所有城市、路網、河道、行軍時間、戰役目錄與存檔規則資料保持不變。

## 保留的來源

- `before-map.png`：修改前已發布的 v1 成品原始位元組，SHA 固定於建構腳本；重建不依賴 Git，也不讀取已覆寫的成品作輸入。
- `generated-range-first-pass.png`：內建 imagegen 的完整山區編輯結果，1024×1536；本版只取下方目標的小範圍，未採用其餘地形變化。
- `north-reference.png`：上項圖片在 `(650,210)` 擷取的 320×220 北側參考裁片。
- `generated-north.png`：內建 imagegen 對該北側參考的精確編輯結果，移除殘留綠峰，保留紅棕山腳與草地。原工具輸出檔名為 `exec-cbb03d0b-d968-4401-8312-954a26f8ff1e.png`。
- `before-north.png`、`after-north.png`、`before-south.png`、`after-south.png`：固定視窗、最近鄰放大 5 倍的修改前後近景。
- `north-grass-reference.png`：僅供北側新草地填補使用的原圖 16×21 紋理，最近鄰放大 10 倍供檢查；岩面與黑色山谷仍取 imagegen 輸出。

生成編輯的要求是移除兩座指定綠峰，以相鄰紅棕山體與自然山腳補齊，不新增河流、道路、城市、標註或其他山峰。原版與 v1 的全部素材保留。

## 可重現合成

```sh
NODE_PATH=/path/to/node_modules node art/map-western-range-v2/build.cjs
node tests/test_remake_map_terrain.cjs
```

建構使用 `sharp` 與 `pngjs`，請將上述 `NODE_PATH` 換為兩套件所在的 `node_modules` 目錄。來源以最近鄰縮回原生地圖像素，再套用 `manifest.json` 記載的兩個緊密不規則遮罩，不使用透明混色。原本正確的棕色山脊與明亮草地優先保留；北側新增草地使用相鄰原地圖 `(268,353)` 的 16×21 草地紋理，以原生像素間距補齊，避免生成圖的偏亮色塊和粗點紋理。只填補新的草地，imagegen 恢復的紅棕岩面與黑色山谷不變。

原道路與城標保護根據 `map-road-centers.png` 與 `hydrology-ground.png` 的差異建立；原藍色河道另含兩像素河岸保護。綠色山體本身不作保護。每次重建均逐像素檢查：兩個遮罩以外，以及所有保護像素，必須與 `before-map.png` 完全一致。來源、成品 SHA、遮罩座標及精確像素統計均寫入 `manifest.json`。
