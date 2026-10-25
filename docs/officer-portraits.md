# 武將像素肖像

全1030名人物均有32×40原生像素肖像和128×160顯示圖：初期1023名沿用明暗強化版，追加7名使用直接烘焙的128×160有限色補繪版，原32×40與舊最近鄰放大版均保留，按同一穩定的`person_id`綁定。人物庫、城內名冊、開局城市預覽、人物資料、戰鬥與單挑使用同一索引；繁中與日文來源說明可即時切換。顯示採黑底與清楚的像素邊緣，不使用瀏覽器平滑濾鏡。新版製作、來源保留與驗證見[128×160肖像說明](portrait-enhancement.md)，初期1023名可在[原圖／新版對照頁](../art/portraits/enhancement-v1/index.html)查看，追加7名的補繪來源與舊圖歸檔見[HD補繪計畫](../art/portraits/supplement-hd-v2/plan.json)。

## 原版整理與身分證據

- 原ROM有237個肖像ID，實際為183種不同像素圖，原版已共用部分圖像。
- 所有237張均保留在`game/assets/portraits/original/`，220名人物可確認綁定，共179種原圖。
- 17條姓名字形或同名身分尚待核對的原記錄僅作歸檔。其對應候選人物如需出場，使用獨立新繪圖，不作推測式原圖綁定。
- `game/config/portrait-identity-map.json`記錄原始13-byte姓名資料雜湊、字形證據及人工轉錄。證據圖在`game/assets/portraits/evidence/original-name-glyphs.png`。
- 特別核對原ID108為諸葛瞻、137為孫權；諸葛均及孫桓不與之誤綁。原版序號、三國志14來源序號和遊戲執行期數字ID不能互換。

原圖由指定ROM的靜態第0幀解碼，完整頭肩尺寸32×40。模式0色板來自ROM偏移`0x3DBFB`，NES索引`0F,20,27,17`；RGBA為透明、白`#FFFFFF`、橙`#F7A247`、棕`#9E4100`。RGB採本項目錄製的Nestopia royaltea色板，並非聲稱所有NES顯示器RGB都一致。原ID131與原模擬器截圖`art/portraits/reference/officer-info-native-witness.png`的`[16,175,48,215]`區域逐像素一致，包含原圖的不透明白色。

離線重提取需要本地ROM，Web遊戲不讀取ROM：

```sh
python3 tools/portraits/extract_original.py '/path/to/三国志2超级版.nes' --check
```

工具先檢查SHA256 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`，錯誤輸入不寫入資產。

## 810名新增繪製

使用內建`image_gen.imagegen`依原版圖作風格參考製作13張8×8圖集，再以離線工具切出803張互不相同的像素圖。保留原始來源圖集、每組提示詞、人物分配計畫、來源檔SHA256和格子索引：

- `art/portraits/source-atlases/new-01.png`至`new-13.png`
- `art/portraits/prompts.json`、`plan.json`及`reference-originals.png`
- `game/config/portrait-generated.json`

參考圖由原ID0、13、17、38、55、67、91、109、131、181、200、222以黑底4倍最近鄰排列。新增圖是本作人物美術設計，不是三國志14画像匯入、原NES未公開圖，也不是人物真實容貌復原。52名女性的美術方向為單獨人工標註；沒有據此改動來源資料的性別欄位、屬性或年代。

工具先依實際黑色行列間隔辨識8×8分區，再裁切每格可見範圍、等比最近鄰縮小至32×40並固定為原三色與二值透明；不以程式繪製人臉或加像素製造差異。一格最多分配一人。遇到重複像素只能取同美術分組未分配格並記錄，不能偷偷共用或修改散列；本批沒有使用此替換。來源與實際裁切框保留便於日後逐人手修。

重新烘焙需離線開發依賴Pillow；遊戲執行和索引驗證僅用Python標準庫：

```sh
python3 -m pip install -r tools/portraits/requirements.txt
python3 tools/portraits/build_generated.py --check
python3 game/build_portrait_manifest.py --check
python3 -m unittest discover -s tests -p 'test_remake_portraits.py' -v
node tests/test_remake_portraits.cjs
```

圖集原檔與提示詞保留可查證的生成過程；AI圖像生成不是確定性重建步驟，像素裁切及索引建置才是確定性的。

## 初次追加4名歷史人物

宋建、呂興、唐譜、李統分別綁定`historical-song-jian`、`historical-lu-xing`、`historical-tang-pu`、`historical-li-tong-jiaozhi`；執行期ID依序為1024～1027，未填入原有1005空缺，也未改動舊1023名身分。使用內建imagegen獨立繪製一張2×2來源圖，每格唯一，沒有借用其他人物。李統為交阯功曹，與魏將李通分開配置。

完整原圖、生成提示詞、來源與參考圖雜湊、每格指派及處理規則位於[`art/portraits/historical-additions-v1/plan.json`](../art/portraits/historical-additions-v1/plan.json)。`build_generated.py`可確定性重建這4張原生圖；其舊128×160最近鄰衍生圖另行歸檔，執行時改用後述HD補繪版。原圖及初期所有資產逐位元組保留。這些皆是本作人物形象，不聲稱史實容貌。

## 西北追加2名地方人物

北宮伯玉、李文侯分別綁定`historical-beigong-boyu`、`historical-li-wenhou`，執行期ID為1028、1029。另用imagegen製作獨立2×1來源圖，每格只對應一人；先前1027名的資料、原圖、增強圖與第一批4人來源圖均保留。

完整原圖、提示詞、生成記錄與分區計畫見[`northwest-rising-v1/plan.json`](../art/portraits/northwest-rising-v1/plan.json)，由`build_generated.py`確定性烘焙32×40原生圖；舊128×160精確4倍版保留於HD補繪計畫的歸檔路徑，現改用有限色128×160補繪版。來源標示區分單純放大與真正補繪。兩圖不借用原武將，也不是史實容貌復原。

## 邊章的獨立肖像

邊章原名邊允，以`historical-bian-zhang`、執行期ID1030綁定獨立新圖，不借用北宮伯玉、李文侯或其他武將。單人imagegen原圖、完整提示詞、生成記錄與1×1分區計畫保留在[`bian-zhang-v1/plan.json`](../art/portraits/bian-zhang-v1/plan.json)。32×40原生圖與舊128×160精確4倍版均保留。現改用同一人物的128×160有限色補繪圖，來源標示為本作新繪，不稱史實容貌；原有1029人的肖像身分綁定保留。

## 7人HD補繪與驗證

7人的正式顯示圖改以高解析度生成源直接取樣至128×160，再限制為5～16色硬邊像素。各自`redrawn128`記錄保留新源圖、提示詞、原native32×40及舊128×160檔案的SHA256。生成源與原圖不是同一檔案，二者都保留，不用改寫原圖來配合新雜湊。

驗證器除尺寸外，檢查相對最近鄰放大至少1,024個像素有變化，至少20個4×4區塊內存在更細像素，且QA必須與實際RGBA一致。人物相貌、帽飾與自然度另作目視驗收。完整規格見[128×160肖像說明](portrait-enhancement.md)及[HD補繪來源](../art/portraits/supplement-hd-v2/plan.json)。

## 存檔與邊界

`game/assets/portraits/index.json`是唯一正式顯示索引。Web端以`person_id`查圖；畫面上的數字ID先由目前劇本精確查出穩定ID；開局預覽使用所選劇本的人物表。

肖像顯示本身不修改存檔結構、隨機數、年代或戰鬥規則。強化圖讀取失敗時改用同一人物原圖；原圖或索引亦不可用時顯示明確的缺圖框，不能借用其他武將頭像。原圖共用會如實保留，新繪810張逐一驗證像素互異。

HTTP服務僅公開部署索引列出的PNG及顯示腳本；ROM、原圖姓名證據、美術圖集與工具不對外服務。頁面來源標示分為「原版像素肖像」及「新增繪製肖像・非史實容貌」，日文同步顯示。

原版圖像保留來源權利；工程MIT授權不代表取得原遊戲美術或其他來源資料的再授權。
