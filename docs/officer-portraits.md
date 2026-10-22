# 武將像素肖像

全1023名人物保留32×40原生像素肖像，並已增加128×160明暗強化版，按同一穩定的`person_id`綁定。人物庫、城內名冊、開局城市預覽、人物資料、戰鬥與單挑使用同一索引；繁中與日文來源說明可即時切換。顯示採黑底與清楚的像素邊緣，不使用瀏覽器平滑濾鏡。新版製作、來源保留與驗證見[128×160肖像說明](portrait-enhancement.md)，全部人物可在[原圖／新版對照頁](../art/portraits/enhancement-v1/index.html)查看。

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

## 803名新增繪製

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

## 存檔與邊界

`game/assets/portraits/index.json`是唯一正式顯示索引。Web端以`person_id`查圖；畫面上的數字ID先由目前劇本精確查出穩定ID；開局預覽使用所選劇本的人物表。

本次不修改人物庫、存檔結構、隨機數、年代或戰鬥規則。強化圖讀取失敗時改用同一人物原圖；原圖或索引亦不可用時顯示明確的缺圖框，不能借用其他武將頭像。原圖共用會如實保留，新繪803張逐一驗證像素互異。

HTTP服務僅公開部署索引列出的PNG及顯示腳本；ROM、原圖姓名證據、美術圖集與工具不對外服務。頁面來源標示分為「原版像素肖像」及「新增繪製肖像・非史實容貌」，日文同步顯示。

原版圖像保留來源權利；工程MIT授權不代表取得原遊戲美術或其他來源資料的再授權。
