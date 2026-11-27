# V2.3 冬季氣候與農業

新戰役可在開局分別選擇原冬季天氣 V2.2.1 或冬季氣候與農業 V2.3。兩者皆是實驗選項。V2.3 以實際觀測的冬春天氣決定當年的糧食生產倍率。江南異常寒潮有獨立開關。

| 主題 | 文件 |
|---|---|
| 史料與地理校核 | [歷史依據](historical-climate-basis.md)、[氣候區與機率](climate-region-profiles.md) |
| 觀測、糧食與市場 | [年度農業與月度記帳](agricultural-climate-rules.md) |
| 九旬預測和備糧 | [AI 氣候預測](ai-climate-forecast.md) |
| 確定性和存檔 | [相容性與存讀](save-compatibility.md) |
| 觀戰和交付 | [驗收流程](validation-results.md)、[資料字典](data-dictionary.md)、[已知限制](known-issues.md) |

遊戲內使用抽象的積雪與寒冷指數。實際結算依遊戲中的 30 日制日曆、每旬事件及每日天氣，不援引未來日的隨機結果。

```sh
MARCH_CORE_BACKEND=python python3 -B tools/economy-balance/v23_climate.py calibrate --output build/winter-agriculture-v23/climate
MARCH_CORE_BACKEND=python python3 -B tools/economy-balance/v23_climate.py holdout --output build/winter-agriculture-v23/climate
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v23_observe.py quick five long holdout --workers 4
MARCH_CORE_BACKEND=rust python3 -B tools/economy-balance/v23_observe.py exceptional locality --workers 2
```

參數凍結採 W2 的種子 100000–100999。獨立冬春驗證採 200000–200999。真實觀戰的保留種子 2041、2042 與兩批氣候種子分離。
