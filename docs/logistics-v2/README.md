# 軍事後勤 V2.0

新戰役按地形、分段時間和部隊規模計算行軍口糧。運輸隊的貨糧另外按途耗入帳。出征、調動、輸送和援軍保留實際可用的路線，並以相同的糧帳標出省糧方案。開局前版本存檔保持原後勤規則。

| 主題 | 文件 |
| --- | --- |
| 行軍、待機、戰鬥與返程口糧 | [行軍糧食規則](march-supply-rules.md) |
| 貨物、途中消耗、損耗與交割 | [運輸貨糧規則](cargo-attrition-rules.md) |
| 可通行、可補給的路線比較 | [最低耗糧選路](minimum-grain-route-planning.md) |
| 募兵、出征、戰後補充與市場 | [AI 後勤預算](ai-logistics-budget.md) |
| 城市定位、庫存和運量 | [戰略儲糧與調糧](strategic-grain-reserves.md) |
| 普通與緊湊存檔 | [存檔兼容](save-compatibility.md) |
| 實作、數據格式和重現 | [模組與驗證方式](implementation-dependencies.md) |
| 後續天氣資料接入 | [天氣擴展介面](weather-extension-design.md) |
| 已執行的檢查 | [驗證結果](logistics-v2-validation-results.md) |
| 全路網與戰場案例 | [V1/V2 比較](logistics-v1-v2-comparison.md) |
| 真實觀戰、多種子與長期平衡 | [長期觀戰](long-term-observer-results.md) |
| 實作與證據範圍 | [已知限制](known-issues.md) |

驗證包的資料單位、起始版本及種子列於包內的資料索引和 JSON 清單。長期觀戰使用原遊戲指令與存檔檢查，控制案例及公式演算各自標記適用前提。
