# 驗收資料字典

| 檔案 | 單位及時點 |
|---|---|
| `climate-region-monthly-probability.csv` | 按開關分組、地區與月份列出每旬普通雪事件機率、強度及寒冷基準 |
| `city-climate-audit.csv` | 實際地圖城 ID、地理座標、地形、氣候區和農業觀測區 |
| 各季節氣候 CSV | 每組、地區或河段的完整遊戲冬春數據。機率為樣本比率 |
| `agricultural-climate-calibration.csv` | R 的 P75/P90/P97、P30–P70 雪量、P75 最後有雪相對日 |
| `agricultural-climate-holdout.csv` | 完整保留冬春樣本比例、月作用期間的平均乘數、12 個月等量基礎的變化 |
| `agricultural-production-comparison.csv` | 原常規、套用後常規、增減糧及入帳月份，使用真正已入帳的正向收入 |
| `agricultural-grain-account.csv` | 官倉已核對的實際分類糧食寫入，按增減方向 |
| `agricultural-repeated-risk.csv` | 完整冬季後連續降低常規產量的最長年數，按強度分列 |
| `harvest-bonus-comparison.csv` | 按城與年匯總實際入庫的內政加糧、9 月豐收獎勵 |
| `city-disaster-grain.csv` | 補充配對逐城的真實水災、旱災事件及直接扣糧 |
| `climate-market-supply-comparison.csv` | 逐城年內實際補入、溢出、月度供應量總和、月結存量及容量總和，另列該年最後一次補貨後的庫存和容量 |
| `market-price-comparison.csv` | 同劇本種子下，同城同月實際買入報價的配對均值 |
| `regional-climate-economic-balance.csv` | 共同比較期最後一個檢查點的地區人口、糧食庫存與累計缺糧城旬 |
| `scenario-scores.csv` | 每局末期的戰事、缺糧、糧倉、市場、運隊及 CPU |
| `pairwise.csv` | 同波次、同劇本、種子、策略的共同觀測月，不同自然終局先截到同月份 |
| `winter-army-supply-comparison.csv` | 應援出發、原承諾抵達旬、真實抵達或期末在途 |
| `campaign-weather-exposure.csv` | 每局的實際行程天氣、冰阻、延誤、運輸具體飢損 |
| `balance-alerts.csv` | 正式候選相對 W0 的各獨立警戒項 |
| `simulation-manifest.json` | 受控背景、種子、規則版本、出處、劇本與地圖 SHA-256 |
| `technical-gates.json` | 實際命令、截止位置、退出狀態與輸出證據 |

糧食數值均採引擎自身整數單位。零值代表有測量且結果為零。空欄或 JSON null 代表沒有同口徑樣本。市場溢出、產量影響、已入倉的豐收獎勵與災害扣款分別計量。獨立完整冬季的候選雪量及實際城池農業帳使用不同分母。

天氣氣候樣本中的 `melt_last_day` 以 11 月 1 日為第 1 日，最遲記到 6 月 30 日。0 表示未測得有地面積雪的日子。正常若能越冬完畢則結束後無雪。冰情日期按 240 天樣本計。

`mean_snow_depth` 以 11 月到 5 月的 210 日平均。水旱災害直接扣糧以官倉寫入分類為準。只有 `locality` 補充配對採集逐城逐事件扣糧，與相同觀戰的全國寫入合計比對。
