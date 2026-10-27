# 128×160武將畫像

目前1,052名人物均有128×160版：原版肖像身分綁定221人、補繪831人；原237格仍有16格未確認人物身分，不以近似容貌補配。此處的人數與原版共用畫格的張數分開計算。

初期1,023名畫像依已確認的諸葛亮版本製作，當時對應982張不同源圖；先追加宋建、呂興、唐譜、李統，再追加北宮伯玉、李文侯及邊章後，該階段為1,030名、989種不同畫像，其中補繪810人。這些是保留的歷史快照，並非目前全庫人數。原版237張、初期新增803張32×40畫像及13張來源圖集均保留，沒有覆蓋或刪除。

追加7人（宋建、呂興、唐譜、李統、北宮伯玉、李文侯、邊章）改用imagegen補繪的高解析度來源，直接烘焙成128×160有限色像素圖。來源以各自舊肖像與原版風格為參考，沒有先縮回32×40再放大。這是本作美術補繪，不聲稱史實容貌復原。完整人物綁定、原圖／舊放大版雜湊、新生成源圖、提示詞與像素檢查見[`supplement-hd-v2/plan.json`](../art/portraits/supplement-hd-v2/plan.json)。

每人的原32×40檔案和先前128×160最近鄰放大版均保留；舊放大圖另存於[`original-enhanced/`](../art/portraits/supplement-hd-v2/original-enhanced/)。最初三批生成源圖及分區計畫仍位於[`historical-additions-v1`](../art/portraits/historical-additions-v1/plan.json)、[`northwest-rising-v1`](../art/portraits/northwest-rising-v1/plan.json)、[`bian-zhang-v1`](../art/portraits/bian-zhang-v1/plan.json)。遊戲仍以原有`person_id`綁定，新版失敗時退回同一人的32×40原圖。

## 本次22名配下人物

本次從原1,030人追加22人，使用既有補繪來源圖集的16個未指派畫格、5張本作新繪，以及1張保留原版11號王建身分的重繪。這16個製作畫格與原NES尚未綁定身分的16格是不同來源，不表示把未知原版人物猜配給新將。21人加入補繪庫，因此目前為831人；王建列入原像綁定的221人。

王建原生32×40仍使用逐位元組保留的[`original/011.png`](../game/assets/portraits/original/011.png)，128×160版另存；原圖不被補繪覆蓋。其身分依原版姓名字形、原表遼東語境及正史仕履審核，不依頭像相似度或武知數值推定。這是保留既定身分的遊戲美術重繪，不聲稱還原史實面貌。

22人的[`plan.json`](../art/portraits/retainer-additions-v1/plan.json)、[原生檔與裁切記錄](../art/portraits/retainer-additions-v1/native-records.json)、[128×160記錄](../art/portraits/retainer-additions-v1/enhanced-records.json)保留人物ID、來源圖、提示詞、原始檔案及輸出雜湊。既有1,030人的素材與綁定保持不變；新22人的素材與[年代／配下配置](retainer-affiliation-audit-20261027.md)共用同一人物ID，圖片不決定其陣營或出場年。

## 地方文吏的128×160共用肖像

地方文吏的3張共用模板另提供128×160增強版，位於`game/assets/civil-staff/enhanced/clerk-1.png`至`clerk-3.png`。原本3張32×40檔案逐位元組保留；歷史人物庫與文吏ID不變，每個文吏仍依生成時固定的`portrait`值綁定同一模板，候選、雇用、轉屬與繼承都不重抽。

這3張使用內置imagegen逐張製作明暗參考，再沿用已認可的Scale4x及原材質蒙版處理。新增明暗只作用於原有膚色與衣帽色塊，原透明區域、黑線及五官結構保留；最終分別使用11、13、13色。這是3張共用形象的美術增強，不表示為每名架空文吏製作獨立或史實肖像。

[增強版索引及來源雜湊](../game/assets/civil-staff/enhanced/index.json)、[3份完整提示詞](../art/civil-portraits/enhancement-v1/prompts/)、[3張生成明暗參考](../art/civil-portraits/enhancement-v1/studies/)均隨程式保留。卡片、名冊、事件及戰場優先使用新版，載入失敗則退回同款原圖；全部不可讀時顯示明確佔位。像素畫面沿用黑底，避免透明黑色細節遺失。

`node tools/civil-portraits/build.cjs --check`只需Node標準函式庫，可檢查尺寸、來源及輸出雜湊、原圖保留、色數與透明／黑線不變。完整重建使用同一工具、不加`--check`，沿用現有Playwright／Chrome環境；不連線重生圖片、不改原圖或存檔。

## 美術與來源

- 原版肖像由32×40經Scale4x整理像素邊緣。帽冠原有的平直橙色端面、上方細小白色結構由各自源圖恢復，不把諸葛亮的座標套用到其他人物。
- 初期新增803張畫像從原先已分配的較高解析度畫格取回細節。以`portrait-generated.json`記錄的實際來源圖集、可見範圍與原縮圖配置範圍為準，包含原本已核對的備用格指派，不按名單順序重新猜測人物。
- 16張8×8工作圖集由內置imagegen逐張補充像素明暗，參考核准畫像的暖色高光、琥珀色陰影與灰白衣飾。圖集是明暗參考；產出的新臉形、眼睛或帽冠輪廓不直接匯入遊戲。
- 最終畫像將有限色階套回各人的來源材質與黑色線條範圍。保留黑色線條與透明度、眼白和中央棕色五官線條；每張不超過16色，仍為硬邊像素風格。新增明暗是美術強化，不表示還原史實容貌或32×40原圖未記錄的細節。
- 諸葛亮直接使用已核准的v8檔案，兩處白色結構與原圖一致。

## 遊戲綁定

`game/config/portrait-enhanced.json`以人物ID記錄新版路徑、128×160尺寸、原圖檔案雜湊、新版檔案與RGBA雜湊、圖集及檢查結果。`game/build_portrait_manifest.py`驗證後，為原索引項目增加`enhanced`欄位；原路徑與原版／新增來源標示保留。

人物資料、名冊、單挑和事件畫面優先使用新版。新版讀取失敗時載入該人物原圖。肖像顯示不改武將屬性、人物ID、戰役資料、亂數或存檔。繁體中文與日文來源標示同步更新。

本地服務只開放索引中與人物ID一致的新版PNG路徑，沒有新增目錄瀏覽或任意檔案存取。

## 檢查與重建

以下是初期1,023人與先行7人版本保留的處理流程。Node工具的PNG準備、檢查與對照頁不需第三方套件。明暗套用工具使用Playwright的Chrome canvas；需先在開發環境提供Playwright及Chrome。圖集生成使用內置imagegen，提示詞保留於`art/portraits/enhancement-v1/prompts/`。本次22人的核對指令另列於後。

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

`art/portraits/enhancement-v1/source-index.json`保留初期1023人的來源索引快照。準備工具逐一比對這些既有綁定、執行期ID及實際檔案；後加7人的原生圖由三份原始計畫重建，128×160補繪版另依supplement-hd-v2計畫烘焙，合併新版索引時再檢查全庫精確覆蓋，避免更新時遺失追加人物或改動舊來源。

本次22人由上述retainer計畫接入生成流程，可只讀核對來源、身份及現有輸出：

```sh
python3 -B tools/portraits/build_generated.py --check
python3 -B game/build_portrait_manifest.py --check
python3 -B -m unittest discover -s tests -p test_remake_retainer_portraits.py
```

初期1023人對照頁位於`art/portraits/enhancement-v1/index.html`，其既有黑線與透明度檢查維持不變。追加7人的新版逐張檢查128×160尺寸、二值透明度、5～16色調色板、相較原32×40最近鄰放大至少1,024個像素改變，且至少20個4×4區塊含有更細的像素變化。這些門檻同時與實際解碼結果核對，不能只填寫QA數字或替大色塊換色。

新生成源圖、提示詞、原生圖與舊128×160歸檔檔案均按雜湊綁定同一人物。尺寸、色數及差異門檻是完整性檢查；同一人相貌、帽飾、自然度與畫面可讀性仍須目視驗收，不將數字通過稱為畫質已通過。
