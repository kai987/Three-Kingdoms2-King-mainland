# 成都西側連片高山

使用內建 imagegen 編輯原地形裁片，將三座孤立的綠山連同周圍棕橙高山一起重畫。採用同一山脈區域的不規則邊界，統一山脊、黑色山谷和山腳紋理。原底圖、城市與路線資料保留。

- `context-original.png`：從原生無道路地形擷取的288×432參考，地圖位置`x=0,y=280`。
- `generated-range.png`：內建 imagegen 的完整輸出，原始生成檔另行保留。
- `before.png`／`after.png`：合成前後的原生裁片；before是原綠山底圖，遊戲舊版另有三山變色濾鏡。
- `manifest.json`：來源SHA、連片範圍、保護像素與輸出SHA。
- `build.cjs`：將生成美術縮回原生像素網格並合成，河流、道路及城標使用原圖像素；區外保持逐像素一致。需要Node.js、sharp與pngjs。
- 遊戲成品：`../../game/assets/map-western-range.png`。

重建範例（將NODE_PATH指向提供sharp與pngjs的環境）：

```sh
node art/map-western-range-v1/build.cjs
node tests/test_remake_map_terrain.cjs
```

合成只修改展示PNG，不重新產生地形規則、路網距離、行軍時間或25個戰役目錄。新圖載入與舊濾鏡停用由`game/map-terrain.js`負責，主地圖與事件插圖共用。

## 最終生成提示

方法：內建 imagegen；`precise-object-edit`；參考圖為`context-original.png`。

Redraw the entire connected western orange-brown high mountain range as one coherent continuous region. Integrate the three isolated green mountains on its eastern edge into the adjacent high peaks; rebuild ridgelines, shaded valleys and foothills together rather than recoloring three symbols. Match the existing orange, vermilion and ochre highlights, dark brown and black crevices, hard NES pixel edges and small dithering. Preserve the overall mountain footprint, all original river courses and the open green basin to the east. Blend irregular mountain feet into surrounding speckled green terrain. No circular orange bases, rectangular boundaries, separate patches, smooth gradients, painterly textures, roads, cities, labels, UI or annotations. Same vertical 2:3 framing.
