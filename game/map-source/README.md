# 地形與道路渲染來源

目前使用已確認的 1352×1024 原風格底圖，五張既有 PNG 及道路修正版的雜湊固定在 `../config/map-source.json`。`../build_map_presentation.py` 驗證底圖及原版城標遮罩，再產生 `../assets/map-presentation.json`；不依賴已移出的歷史開發頁面或工具。城池名稱、地形外觀及戰役資源各自處理。

成都西側山地改用完整連片重繪，見 `../../art/map-western-range-v1/`。imagegen 以原生地形裁片為參考，統一三座原綠色山峰及相鄰山脊、山谷的岩面紋理。`build.cjs` 在一個連續的不規則山區內合成，產生 `../assets/map-western-range.png`；22,006個原河道、道路及城標保護像素與1,318,250個區外像素逐一核對一致。新圖維持1352×1024，原始PNG全數保留。

陰平附近與西南山腳兩處殘留的綠峰覆蓋，另以 `../../art/map-western-range-v2/` 的小範圍補繪移除，露出連續的紅棕山腳；`../../art/map-western-range-v3/` 保存之後批准的陰平棕色山腳與綠峰。v1、v2、v3 原始素材及紀錄全部保留，用於重現各歷史美術版本。

目前可玩版本的 `map-western-range.png` 由 `python3 -B game/build_terrain_art.py` 重建。它以當前 `map-road-centers.png` 為底，只合成批准山地範圍內的透明美術裁片，保護當前河流、河岸、道路及城池；不再用舊的整幅美術圖覆蓋新路網。`python3 -B game/build_terrain_art.py --check` 只讀驗證輸入、成品與紀錄。CI及 `build_web.py` 發布前都執行此檢查，來源變動而未重建時會明確失敗。

`../map-terrain.js` 預載並驗證新圖後，僅替換主地圖與事件插圖的直接底圖，並移除舊 `data-terrain-recolor="chengdu-west"` 色彩層；重繪後仍會套用同一完整山脈圖，下載或解碼失敗則保留完整舊地圖。`presentation.mountain_recolors` 的5,071像素歷史遮罩繼續留存作回退，正常新圖不再使用。這次美術替換未重建城池、道路、行軍時間或戰役資料，避免改變既有存檔的規則目錄身分。

臺灣島與海南島的地形以各自既有的接岸點為基準，沿長寬縮到75%。合成器從無城標、無陸路的 `hydrology-ground.png` 取地形，將原底圖中的城標與接岸道路像素留在原坐標。`terrain-art-render.json` 記錄兩島縮放前後的範圍與陸地像素數，路線仍按既有地圖幾何疊加。

呂宋島使用 `terrain-art.json` 記錄的 Natural Earth 海岸輪廓，島身往南延伸，東南方的比科爾半島由地圖底部自然裁切。島上山地保留原地圖的色盤，海側以每像素到岸線的距離平滑過渡，畫幅外的輪廓仍參與計算。地形建置器在無道路、城標及河道的外海生成島嶼，原有戰役城池及航路沿用各自的資料來源。

東北沿海裁片 `northeast-coast-art.png` 校準渤海灣、遼東半島、朝鮮半島與山東半島的相對位置，並保留渤海海峽。岩岸大形取自 Natural Earth 1:10m 陸地多邊形，渤海灣西岸及萊州灣採用程鵬等（2025）圖3a所載漢代古岸線，作為漢末至三國的近似。朝鮮半島按北朝上的經緯比例繪製，東側岸線在原畫幅邊緣裁切。岸線沿用原圖的像素網格、深色岸緣、碎紋和海陸色盤。`water-corrections.json` 記錄裁片原點、參考資料與輸入雜湊。先編譯新的水系底圖，再以修訂後的城池座標重建接岸道路與黃海、渤海航線。

可玩底圖的 `world_surface.py` 以 2px 網格重新渲染整張地圖的外海、岸緣和東北沿海地面。`northeast-coastline.png` 的紅、綠色通道分別記錄原有與修訂後的陸地輪廓。新露出的地面以固定座標生成像素紋理，向鄰接的原地形過渡。河流、海港、陸路和城標沿用目前的水系及道路圖層，航路仍由 `hydrology-ground.png` 的水陸輪廓計算。

現有閩粵海岸可追溯至 [v42 地圖構建記錄](https://github.com/kai987/Three-Kingdoms2-King-mainland/blob/c4329184c55d8fdeff85677dfb14585c30414e01/expansion/map/README.md)。v42 裁切並沿用了 v41 的地形，閩粵部分源自本專案較早期的生成地形稿。對現有 `road-ground.png` 中的閩粵岸線取樣後，新岸線採用很窄的深綠過渡、因位置而變化的近黑岸緣及緊湊的海藍過渡，並以零星深藍碎點延續原有海面的質感。海陸輪廓和航路仍分別取自水陸遮罩與導航資料。

`water-corrections.json` 的渭水上游由隴西北側山麓往東順谷地延伸，在扶風接回原有河線。黃土高原、遼東及朝鮮半島的主要河道沿用同一組原生藍色像素，依地理來源和遊戲岸線概化。洛東江只保留畫幅內的河段。新增河道顯示於地形底圖，原有的可航行河道仍由 `river-network.json` 定義。

既有道路已畫在底圖中，新增道路及海路再以執行時 SVG 疊加。`../config/road-centers.json` 保存已批准底圖的道路線形、33 個經核對屬於城池的偏心路口及 25 個需保留的獨立共用路口。`../road_centers.py` 只移動明列節點或替換經核對的局部路段，將長安、扶風至安定等道路直接接入城標中心；刪去收合後重複的短接線，保留其他城際道路使用的旁路。`../render_road_centers.cjs` 在原生解析度局部擦除、重畫，產生 `../assets/map-road-centers.png`；道路寬度、顏色、原版城標及其餘地形像素沿用原樣。

`road-ground.png` 是與目前底圖逐像素對照後提取的無道路地形來源，已包含原有五次移山與河流。它只供局部道路修復，不在遊戲中下載或覆蓋整張地圖。`road-centers-render.json` 固定配置、城池座標、原底圖、來源地形與輸出圖的 SHA-256；一般重建只驗證這些來源與輸出，不依賴瀏覽器。需要修改道路美術時，先在安裝 Playwright 的 Node 環境執行 `node game/render_road_centers.cjs`，檢視原生及放大效果後更新批准雜湊，再執行 `python3 -B game/build_map_presentation.py`。執行時僅以展示層別名載入修正版，路線可達性、隨機數與存檔格式維持原樣；行軍距離與時間由同源幾何重建，見 `../../docs/route-time-calibration.md`。

`../config/route-corridors.json` 統一襄平、樂浪、山陰原有港口接道及牂牁山道；`../build_navigation_geometry.cjs` 產生導航線形，`../build_campaigns.py` 再輸出各劇本。海港接道沿既有折線繪製，共用路段只畫一次。執行時道路有明確起終城池 ID 時，首尾固定使用該城池的當前中心；港口及共用岔口不作城池端點處理。其餘明列頂點僅在中心 3 像素內校正，途經城池的曲線在中心分段。沒有明列節點的鄰近城池不會自動增加連線。

`valley-ground.png` 為早期移山處理保留的來源，SHA-256 為 `c92c170d35c4bc0e17ec1bd4ae4bdb0cd9cbfbb96504486f1b95e43a1ce13d86`；目前不作整張地圖覆蓋，遊戲伺服器亦不開放此來源檔案。


水系修正來源為 `../config/water-corrections.json`、`terrain-under-water.png`、`historic-water.svg` 與 `sea-shadow.svg`。這些已從原場景提取並固定雜湊，重建時無須歷史開發目錄。原始 `road-ground.png` 和五張底圖均保留。`node game/render_water_corrections.cjs` 在 2px 水系網格上將渭水下游接至黃河 `[639,326]` 拐彎，截去五處入海口海中延長線，並產生清除舊深藍海路的逐行遮罩；移山區與其餘水系不重畫。接著執行 `node game/render_road_centers.cjs`、更新 `map-source.json` 的輸出圖雜湊，最後執行 `python3 -B game/build_map_presentation.py`。

新增的金沙江北延與涪江使用相同藍色的連續4px河線，邊緣維持2px網格。完整更新次序是水系渲染、道路渲染、批准道路圖雜湊、導航與道路幾何、29篇劇本、橋梁、地圖展示資料，最後重建 `build_terrain_art.py`，再建立Web版本。美術合成器也依賴當前道路幾何，因此應在幾何產生後執行。瀏覽器測試另讀取實際顯示底圖的像素，檢查涪江與金沙江北延確實可見，而非只檢查中間來源PNG。

`node game/build_map_bridges.cjs` 依修正後的 `hydrology-ground.png` 及前端實際 SVG 陸路曲線，以 0.5px 間隔掃描跨水段，產生 `../assets/map-bridges.json`。橋段延伸至兩岸，沿岸港口的末端水段不算跨河橋；共用橋去重後，在陸路與海路上方、城標下方繪製原版深棕及淺棕雙層橋面。所有劇本使用相同幾何來源，編譯器、地形、道路及劇本雜湊由展示層建置器核對；未改變戰役路網、行軍計算或存檔資料。
