# 第三方來源與授權

OpenCC 轉換表與 Apache-2.0 授權在 `game/locales/opencc/`；雲端 SDK 與其授權在 `game/vendor/`；字型來源見 `game/assets/`。原版肖像的像素、色板與人物對應證據見[肖像說明](../officer-portraits.md)。

REA 與 Nestopia 的歷史研究授權文字仍保留於本資料夾作來源紀錄；其逆向工具及研究程式已移出目前遊戲。原 ROM、商業遊戲美術、音樂與資料不因本專案程式使用 MIT 而改變授權。

原版音樂來自使用者提供的ROM，以未修改的Nestopia核心錄製、切取原音序循環並作4毫秒接縫淡化，保留原權利人的權利，不歸入本專案MIT程式授權。`game/assets/audio/index.json` 記錄ROM、核心、場景狀態、原始PCM、輸出音訊及工具的雜湊。`tools/audio/capture_original.py` 只用於離線整理，原ROM、狀態及核心由本機另行提供。

原版短音效亦保留原權利人的權利。`tools/audio/capture_effects.py` 用受控CPU／RAM呼叫原音訊驅動與NMI錄製，未修改ROM或模擬器程式；這是隔離錄製，並非自然遊玩操作證明。`game/assets/audio/effects.json` 記錄兩次重錄的PCM及軌跡雜湊、原呼叫點、計略音效表，以及本作復用原音效的操作對應。細節見[原版音效](../original-sound-effects.md)。本作編寫的合成配樂與後備音效另與原版錄音區分。

原版戰場地形、兵卒及單挑騎將保留原權利人的權利。`game/assets/battle-original/index.json` 記錄原ROM、Nestopia核心、調色盤、畫面來源、裁切及出貨圖片雜湊；`tools/battle-original/build.py` 為離線整理工具。原ROM、模擬器核心與研究存態不隨Web遊戲提供。畫面取樣與本作補充像素效果的區分見[戰鬥畫面](../battle-scenes.md)。
