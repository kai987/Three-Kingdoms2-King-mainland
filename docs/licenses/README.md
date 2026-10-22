# 第三方來源與授權

OpenCC 轉換表與 Apache-2.0 授權在 `game/locales/opencc/`；雲端 SDK 與其授權在 `game/vendor/`；字型來源見 `game/assets/`。原版肖像的像素、色板與人物對應證據見[肖像說明](../officer-portraits.md)。

REA 與 Nestopia 的歷史研究授權文字仍保留於本資料夾作來源紀錄；其逆向工具及研究程式已移出目前遊戲。原 ROM、商業遊戲美術、音樂與資料不因本專案程式使用 MIT 而改變授權。

原版音樂來自使用者提供的ROM，以未修改的Nestopia核心錄製、切取原音序循環並作4毫秒接縫淡化，保留原權利人的權利，不歸入本專案MIT程式授權。`game/assets/audio/index.json` 記錄ROM、核心、場景狀態、原始PCM、輸出音訊及工具的雜湊。`tools/audio/capture_original.py` 只用於離線整理，原ROM、狀態及核心由本機另行提供。新增的合成配樂與互動音效由本作編寫。
