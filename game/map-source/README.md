# 地形與道路渲染來源

目前使用已確認的 1352×1024 原風格底圖，五張既有 PNG 及道路修正版的雜湊固定在 `../config/map-source.json`。`../build_map_presentation.py` 驗證底圖及原版城標遮罩，再產生 `../assets/map-presentation.json`；不依賴已移出的歷史開發頁面或工具。城池名稱、地形外觀及戰役資源各自處理。

成都西側三座山只調整顏色。`presentation.mountain_recolors` 記錄三組原圖綠色山面及向外 6 像素內綠色輪廓的逐行遮罩，共 5,071 像素，補齊原先漏出的綠色山緣；前端以裁切的 SVG 色彩矩陣映射為棕橙色。原山體輪廓、黑色陰影、位置和全部底圖 PNG 均不修改，河道、道路、城標及遮罩外像素沿用原圖。整張生成參考圖未替換進遊戲。

既有道路已畫在底圖中，新增道路及海路再以執行時 SVG 疊加。`../config/road-centers.json` 保存已批准底圖的道路線形、33 個經核對屬於城池的偏心路口及 25 個需保留的獨立共用路口。`../road_centers.py` 只移動明列節點，將長安、扶風至安定等道路直接接入城標中心；刪去收合後重複的短接線，保留其他城際道路使用的旁路。`../render_road_centers.cjs` 在原生解析度局部擦除、重畫，產生 `../assets/map-road-centers.png`；道路寬度、顏色、原版城標及其餘地形像素沿用原樣。

`road-ground.png` 是與目前底圖逐像素對照後提取的無道路地形來源，已包含原有五次移山與河流。它只供局部道路修復，不在遊戲中下載或覆蓋整張地圖。`road-centers-render.json` 固定配置、城池座標、原底圖、來源地形與輸出圖的 SHA-256；一般重建只驗證這些來源與輸出，不依賴瀏覽器。需要修改道路美術時，先在安裝 Playwright 的 Node 環境執行 `node game/render_road_centers.cjs`，檢視原生及放大效果後更新批准雜湊，再執行 `python3 -B game/build_map_presentation.py`。執行時僅以展示層別名載入修正版，劇本資料、路線可達性、行軍時間、隨機數與存檔格式均不變。

`../config/route-corridors.json` 統一襄平、樂浪、山陰原有港口接道及牂牁山道；`../build_navigation_geometry.cjs` 產生導航線形，`../build_campaigns.py` 再輸出各劇本。海港接道沿既有折線繪製，共用路段只畫一次。執行時道路有明確起終城池 ID 時，首尾固定使用該城池的當前中心；港口及共用岔口不作城池端點處理。其餘明列頂點僅在中心 3 像素內校正，途經城池的曲線在中心分段。沒有明列節點的鄰近城池不會自動增加連線。

`valley-ground.png` 為早期移山處理保留的來源，SHA-256 為 `c92c170d35c4bc0e17ec1bd4ae4bdb0cd9cbfbb96504486f1b95e43a1ce13d86`；目前不作整張地圖覆蓋，遊戲伺服器亦不開放此來源檔案。
