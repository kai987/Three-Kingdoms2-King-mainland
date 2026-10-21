# 程式優化、開發資料清理與Rust遷移

本次維持原版像素畫面、25個劇本、161份存檔相容目錄、1023人身分與所有遊戲規則。原機研究資料與現行Web戰役分開管理。

## 已實作的優化

`CampaignSession.view()`原本每次重建161份不變的開局摘要；現在按Session快取，仍回傳獨立的清單、城市名稱、歸屬、勢力資源、人數與配色容器。目前月份、在籍名冊、資源及行軍資料繼續按實際狀態計算；不快取可變戰役或亂數結果。

以下為同一部本機、同一腳本、每場景12次暖態中位數，量的是Python的view組裝，不包括JSON序列化、網路、瀏覽器或整個回合：

| 場景 | 原本 | 優化後 | 耗時減少 |
| --- | ---: | ---: | ---: |
| 184年舊v5 | 23.25ms | 6.73ms | 71% |
| 217年蜀v13 | 55.18ms | 38.14ms | 31% |
| 263年魏v13 | 74.13ms | 60.69ms | 18% |

啟動時間約4.2秒，未見明顯變化。161份目錄與4種代表狀態的完整view／save canonical SHA256皆與優化前一致；新增測試檢查舊存檔、新開局、讀檔與回應容器隔離。

地圖城標改為一份SVG像素定義加每城的`use`實例，保留32×32原版輪廓、空城白色及勢力配色。三個桌面場景的SVG節點為3275→693、2774→691、2945→725，減少約75～79%。15次重畫的本機中位數有小幅改善，但不將節點減少比例當作FPS提升比例。190／225／263年完整畫面及城標對照、3倍與3.75倍視角均獲相同PNG；互動與手機另以瀏覽器驗證。

目前完整狀態JSON仍約10～19MB，序列化和瀏覽器處理仍有成本。測試gzip1可減少86～89%傳輸量，但每次增加約36～54ms壓縮CPU，因此本機版未直接加入；後續可量測一次載入不變目錄、只傳動態狀態的版本化API。

## 已完成的清理

[機器可讀清單](development-cleanup-20261022.json)記錄原因、大小與重建方式。

- 刪除17,504個開發檔案，合計439,173,138位元組：約439MB。包括REA的可重裝`node_modules`、3424個可重編譯中間`.o`、工作簿／報告驗收暫存、Python快取及過期`game/design/`。
- 原概念圖、提示詞及說明可從Git的`9bf4aea`恢復；REA來源、6502補丁、鎖檔、Ghidra來源與最終原生庫保留。
- 保留凍結清單逐檔記錄的phase32 observer物件、唯一原機證據、歷史ZIP、字型／OpenCC授權、武將能力來源及仍被v42渲染使用的v41地圖。
- 兩份1,395,099,758位元組的完全相同ZIP都被歷史驗證器引用。以APFS `clonefile`共享資料塊後，保留兩個可獨立寫入的普通檔案及原SHA；即時檔案系統可用空間增加1,395,699,712位元組（約1.396GB，含同期檔案系統變動）。沒有以hardlink或symlink代替。
- 根README與規則層README已改為目前Web遊戲入口，過去「732人德待評」等階段摘要移出現行說明。原分析報告與Git歷史保留。

清理不會縮短已發佈目錄或改寫存檔。上述快取日後可重新生成；需要原機重跑時按保留的來源與鎖檔重建對應依賴。

## 現行Web遊戲的Rust遷移評估

檢查基準：目前`source/remake/`的獨立戰役與`game/`的HTML／JavaScript介面，人物庫1023、最多115城；本次只做評估，未新增Rust執行碼，也未宣稱Rust已帶來效能提升。

## 建議結論

可以轉為Rust。最合適的是可獨立測試的規則與計算核心，長期以同一個Rust crate支援原生差分測試與瀏覽器WebAssembly。先處理目前視圖重複計算與大量DOM／傳輸成本，再依量測結果決定遷移範圍。把現有程式換語言不會自動縮小JSON回應或減少SVG節點。

| 優先 | 現有檔案／函式 | 遷移價值與邊界 |
| --- | --- | --- |
| 1 | `travel.py`：`_travel_path`、`_legacy_travel_path`、`_hazard_travel_view`；`route_hazards.py`：`route_allowed`、`evaluate_leg`、`allocate_survivors` | 地形、月份、單向路、季風、最短時間路徑及整數減員，輸入／輸出容易固定。一次批量報價，不要讓每個小算式各跨一次JS/Wasm邊界。舊與新目錄的路徑規則仍須分開保留。 |
| 2 | `campaign.py`：`SeedRng`、`_damage`；`campaign_expansion.py`：`_counter`、`_tactic`、`_duel_start`、`_duel_action`、`_battle_result` | 普攻、16計略與單挑可形成同一戰鬥核心。狀態、亂數及作用順序必須一起傳遞；避免Python與Rust各持有一份相互漂移的戰鬥狀態。單場最多20隊，不能在未量測前承諾肉眼可見的加速。 |
| 3 | `officers.py`：`year_state`、`initialize_officer`、`transfer_officers`、`select_deployment`、`advance_year`；`campaign_expansion.py`：招募、轉屬、`_reconcile_factions` | 型別與不變量收益較明確：穩定人物身分、16位以上執行期ID、每城30人、出戰10人、出生／出仕／死亡、名冊單一歸屬。史料與作者設定仍放資料檔。 |
| 4 | `campaign_expansion.py`：`_expanded_ai`；`travel.py`：`_resolve_ai_battle`、`_arrivals`；`campaign.py`：`command`、`validate`、年月推進 | 作為完整戰役狀態核心的後續階段。先確立前幾項規則與差分測試，再搬AI的招募／補兵／出征／調動／繼承及中斷續跑；可由JS Worker呼叫WASM，讓UI維持可操作。 |
| 保留 | `game/app.js`、`i18n.js`、`map-navigation.js`、HTML、CSS、SVG與雙語字典 | 以DOM、文字、本地存取、事件及瀏覽器繪圖為主。保留JS的工作成本低，Rust仍需JS／web-sys介面操作；目前先減少重複DOM建立、查找與傳輸。 |
| 保留 | `game/build_*.py`、史料來源、目錄JSON與離線審計 | 它們屬於資料建置與可追溯性，通常不在遊戲每回合熱路徑。是否改Rust應由建置時間／維護成本決定。 |

## 必須維持的相容契約

1. `SeedRng.next`是32位xorshift，狀態與`draws`均存檔。Rust使用明確`u32`語義，不能把平台`usize`當固定寬度，也不能因預覽或驗證而多抽一次亂數。
2. Python有負數向下整除：計略成功率含`(智差)//2`，單挑含`(武差)//6`；Rust有號整數`/`是向零截斷。正分母時可用`div_euclid`或明確floor實現，否則奇數負差值會改變判定。
3. 路徑平手要保留現有日數、距離、城市／序號與原邊順序規則；不能任由HashMap遍歷順序選路。陰平單向、子午谷7～9月、海陸接駁、季風方向與探索揭露時點逐項對照。
4. 一次航行只抽／結算一次暴風雨；整數餘兵採全軍總量與固定餘數順序分配，不能逐將向下取整造成額外死亡，也不能重讀滿城等待時再次扣兵。
5. `Campaign.command`先在副本執行並驗證，成功才提交；失敗應連同資源、RNG、名冊全部不變。`settle`和`ai`回執的冪等性、AI佇列／游標與玩家防守中斷需保留。
6. 舊存檔包含格式version1、scenario、原目錄位元組SHA、完整state和checksum。Python canonical是UTF-8、保留中文、字串鍵排序、緊湊JSON且拒絕NaN；路徑中的整值float另有`.0`正規化。不能假設serde_json的預設序列化就等同現有校驗。先保留Python存檔適配器，或明確版本化遷移。
7. 城市／兵員／年度事件與未來登場必須通過現有驗證：兵力守恆、每人單一名冊、不可復活、死亡年邊界與IF排除、總庫與當年登場分開。新增人物1023仍需支援非連續ID（保留1005空槽）。

## 建議工程順序

- 建立單一純Rust規則庫，先用原生單元測試對照目前Python的輸入／輸出，不接管正式存檔。
- 第一個垂直切片只搬路徑／風險批量報價與餘兵分配；通過差分後才在瀏覽器接入wasm-bindgen適配器，測量原生、WASM及序列化總耗時。
- 再加入整組戰鬥／計略／單挑，最後才是AI和完整狀態提交。成熟後可讓Web遊戲完全在瀏覽器運行；這是架構目標，尚未實作。
- HTML／CSS／SVG、語言、輸入、本地存取保持JS。可在Worker中保留WASM核心和已載入目錄，主執行緒只收必要的顯示資料，避免每次複製全庫。
- `wasm32-unknown-unknown`不提供一般主機檔案／執行緒能力；原Python HTTP伺服器不能原封不動編入瀏覽器WASM。接入時需檢查WASM MIME、CSP、載入失敗與存檔恢復路徑。

## 差分與驗收

沿用目前測試作為Python真值：`test_remake_route_hazards.py`、`test_remake_hazard_marches.py`、`test_remake_travel.py`、`test_remake_campaign.py`、`test_remake_officers.py`及高編號人物擴充測試。補充多種子逐指令重播、正負能力差、所有月份／方向、平手路徑、一次風暴、滿城／易主／死亡等待、AI玩家防守中斷及戰後回執。比較每一步狀態／RNG draws／資源和完整戰果，而非只比較畫面或最終輸贏。先驗原生差分，再驗瀏覽器WASM與JS互動。無現成基準能支持固定的加速倍數。

## 舊逆向工程的界線

`source/recovered/`與`source/readable_c/game_recovered.c`是原ROM的規則／位元行為證據；`RKOfficer`仍是12位元組原記錄，部分接口有8位元欄位和舊RNG。現行Web遊戲不載入它們。可以用作特定純函式的比對來源，不能把整個舊C／IR／CPU服務改成Rust就宣稱完成現行115城1023人Web戰役遷移。

## 已查閱的官方資料

- Rust WebAssembly目標與標準函式庫限制：https://doc.rust-lang.org/rustc/platform-support/wasm32-unknown-unknown.html
- wasm-bindgen的JS／WASM互通與型別適配：https://wasm-bindgen.github.io/wasm-bindgen/
- Rust整數溢位、有號整除與型別：https://doc.rust-lang.org/book/ch03-02-data-types.html
- WebAssembly官方列出的混合JS／HTML與計算核心部署方式：https://webassembly.org/docs/use-cases/

本機只讀確認有Rust 1.93.0／Cargo 1.93.0；現行遊戲目錄未有Cargo專案。工具鏈存在不代表WASM載入、效能或存檔相容已驗證。
