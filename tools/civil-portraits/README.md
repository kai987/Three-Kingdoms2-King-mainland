# 地方文吏128×160像素肖像

保留3張原始32×40文吏PNG，以已核准的諸葛亮v8及武將增強流程為風格基準。內置imagegen分別為3張原圖製作暖色明暗參考；生成圖只是色調參考，新的臉形、眼睛、帽冠、線條或背景不直接匯入。

`build.cjs`重用武將肖像工具的原圖Scale4x與帽頂／細白結構保護，僅在原有材質範圍套用有限色階。透明區域表示原圖的黑色細節，與原五官線條、眼白一併保護；遊戲以黑底呈現。最終每張為128×160、最多16色，原圖不覆寫。

```sh
node tools/civil-portraits/build.cjs --check
NODE_PATH=/absolute/path/to/node_modules node tools/civil-portraits/build.cjs
```

離線檢查只需Node標準函式庫。重建使用既有Playwright與Chrome進行色調參考取樣，不需要ROM、模擬器、網路或重新生成圖片。原始生成參考與精確提示詞保存在`art/civil-portraits/enhancement-v1/`，出貨PNG與來源／提示詞／工具雜湊及檢查數據保存在`game/assets/civil-staff/enhanced/index.json`。

這仍是3種共用文吏形象，不是每個生成角色各有一張獨立容貌。戰役中保存的`clerk-...`身分與`clerk-1/2/3`樣式鍵保持不變。卡片、名冊、人物、事件及戰場優先載入增強圖，失敗時退回相同樣式的原圖；兩者皆不可讀時顯示缺圖標記，不重抽或更換人物。
