# 128×160武將畫像

畫像依已確認的諸葛亮版本製作。人物庫仍有1,023個穩定人物ID；原版共用肖像的關係保留，因此對應982張不同的源圖。原版237張與新增803張32×40畫像、13張新增畫像來源圖集均保留，沒有覆蓋或刪除。

## 美術與來源

- 原版肖像由32×40經Scale4x整理像素邊緣。帽冠原有的平直橙色端面、上方細小白色結構由各自源圖恢復，不把諸葛亮的座標套用到其他人物。
- 新增803張畫像從原先已分配的較高解析度畫格取回細節。以`portrait-generated.json`記錄的實際來源圖集、可見範圍與原縮圖配置範圍為準，包含原本已核對的備用格指派，不按名單順序重新猜測人物。
- 16張8×8工作圖集由內置imagegen逐張補充像素明暗，參考核准畫像的暖色高光、琥珀色陰影與灰白衣飾。圖集是明暗參考；產出的新臉形、眼睛或帽冠輪廓不直接匯入遊戲。
- 最終畫像將有限色階套回各人的來源材質與黑色線條範圍。保留黑色線條與透明度、眼白和中央棕色五官線條；每張不超過16色，仍為硬邊像素風格。新增明暗是美術強化，不表示還原史實容貌或32×40原圖未記錄的細節。
- 諸葛亮直接使用已核准的v8檔案，兩處白色結構與原圖一致。

## 遊戲綁定

`game/config/portrait-enhanced.json`以人物ID記錄新版路徑、128×160尺寸、原圖檔案雜湊、新版檔案與RGBA雜湊、圖集及檢查結果。`game/build_portrait_manifest.py`驗證後，為原索引項目增加`enhanced`欄位；原路徑與原版／新增來源標示保留。

人物資料、名冊、單挑和事件畫面優先使用新版。新版讀取失敗時載入該人物原圖。這是顯示資產變更，不改武將屬性、人物ID、戰役資料、亂數或存檔。繁體中文與日文來源標示同步更新。

本地服務只開放索引中與人物ID一致的新版PNG路徑，沒有新增目錄瀏覽或任意檔案存取。

## 檢查與重建

Node工具的PNG準備、檢查與對照頁不需第三方套件。明暗套用工具使用Playwright的Chrome canvas；需先在開發環境提供Playwright及Chrome。圖集生成使用內置imagegen，提示詞保留於`art/portraits/enhancement-v1/prompts/`。

```sh
node tools/portraits/prepare_enhanced.cjs --check
# 逐張產生工作圖集明暗參考後：
node tools/portraits/pack_enhanced.cjs atlas-01
# 其餘atlas-02至atlas-16同樣處理。
node tools/portraits/pack_enhanced.cjs --finalize
python3 game/build_portrait_manifest.py
node tools/portraits/verify_enhanced.cjs
node tools/portraits/build_enhanced_gallery.cjs
python3 game/build_portrait_manifest.py --check
```

`art/portraits/enhancement-v1/source-index.json`保留來源索引快照。準備工具會比對目前索引的原圖欄位與實際檔案，僅忽略後來加入的新版欄位，避免新版接入後失去來源可重建性。

對照頁位於`art/portraits/enhancement-v1/index.html`。自動驗證範圍涵蓋全部人物、原圖與來源圖集雜湊、尺寸、色數、黑線／透明度及綁定；自然度等美術判斷另以圖集與遊戲畫面檢查，不將自動檢查稱為逐人手工審美驗收。
