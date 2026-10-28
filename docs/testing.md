# 遊戲驗證與回放

驗證分為規則／資料檢查、介面夾具、真實WASM回放、真實瀏覽器操作與長期戰役回放。各層檢查不同邊界：Node腳本通過不等於網頁已能操作，CI通過也不等於線上快取已更新或郵件已送達。下列命令均在專案根目錄執行，使用測試戰役，不連入玩家的本機服務、雲端帳號或存檔槽位。

## 規則、資料與輕量介面檢查

使用Python 3.10以上與Node.js；CI使用Python 3.13與Node.js 24。Rust原生與WASM差分另使用固定Rust 1.93.0及`wasm32-unknown-unknown`目標。

```sh
# 戰役來源與生成資料一致
python3 -B game/build_campaigns.py --check
python3 -B tools/scenario-history/audit.py --check
python3 -B tools/scenario-history/ruler_audit.py --check

# Python規則、名冊、事件、兵員守恆、存讀與API邊界
python3 -B -m unittest discover -s tests -p 'test_remake_*.py' -v

# JavaScript語法與受控介面／Worker／儲存夾具
for file in game/*.js; do node --check "$file"; done
for file in tests/test_remake_*.cjs; do node "$file"; done

# 固定Rust工具鏈、原生核心與WASM結果對照
RUSTUP_TOOLCHAIN=1.93.0 python3 -B game/build_march_core.py --check
node tests/march_wasm_parity.cjs
```

介面夾具可驗證人選排序、輸入上限、滿10人停選、路線合併、自動恢復、語言切換與延遲回應失效等程式行為，但不宣稱涵蓋真實瀏覽器的排版、焦點、觸控或資源載入。

君主歸屬核查以固定的`game/config/references/ruler-affiliation-review.json`為依據，逐一核對29個開局的67名君主人選、君主ID／旗標／本據所有者、全員配置集計與開放城池的資金、兵糧、兵員。`ruler_audit.py --check`同時檢查逐人報告未過期，已加入CI；`--write`只生成報告，不重寫固定決定表。負例測試確認誤改君主、城主、計數、兵員與年代資料會失敗。公孫康沒年、曹操與臧霸軍營的區域代理及假想例外均保留限定說明，不把結構一致當作所有駐地均有史料證明。

## 真實WASM與CPU回放

```sh
npm ci --prefix tools/web-runtime --ignore-scripts
python3 -B game/build_web.py --output build/web
node tests/browser_engine_smoke.mjs build/web
```

這項檢查在Node中實際載入發布包的Pyodide與Python戰役核心，並與CPU參照重放相同命令；比對狀態、存檔與亂數。它也檢查完整／精簡視圖的還原結果。這是發布包的執行驗證，不是DOM頁面或完整多年戰役的測試。素材及執行環境必須先按[發布流程](web-deployment.md)建置。

## 真實瀏覽器操作

[瀏覽器驗收](../tests/browser_ui.spec.mjs)使用固定Playwright `1.64.1`與其對應的Chromium，在實際頁面載入同一份`build/web/`、Worker、Pyodide與戰役核心。桌面為1280×800，觸控模擬為390×844；本機預設循序執行，CI則拆成兩個獨立工作，在相同發布包上並行驗收。觸控Chromium模擬不等同於已驗收實體手機或Safari。

```sh
# 先按前節建置build/web，再安裝鎖定的測試套件及瀏覽器
npm ci --prefix tools/browser-tests --ignore-scripts
node tools/browser-tests/install.mjs
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config tools/browser-tests/playwright.config.mjs
```

[設定檔](../tools/browser-tests/playwright.config.mjs)自動啟動[隔離靜態測試服務](../tests/browser_static_server.mjs)，只監聽`127.0.0.1:18917`，保留正式站的`/Three-Kingdoms2-King-mainland/`子路徑，不提供遊戲API。每項測試使用獨立瀏覽器環境，不接管玩家原有分頁、瀏覽器本地保存或雲端登入。

[安裝工具](../tools/browser-tests/install.mjs)使用鎖定套件的官方安裝命令。Linux先檢查完整Chromium的共享函式庫，缺少依賴才安裝系統套件；安裝後仍有缺漏會直接失敗，不跳過測試。macOS使用相同的固定瀏覽器安裝，不執行Linux的`ldd`或APT。驗收指定完整Chromium，與依賴檢查使用同一個執行檔。

檢查範圍包括開局圖文事件的確認與關閉、彈窗與即時繁中／日文切換、編兵輸入上限及最大值按鈕、確認後保留彈窗、手動存讀、自動恢復的確認／取消及匯出原始位元組比較、拒絕無效JSON、鍵盤選城、地圖100%–400%邊界、滑鼠與可信觸控拖移，以及版本清單首次失敗後的明確重試。戰役操作透過可見控制項執行，不注入城池、人物或存檔狀態；版面檢查包含窄螢幕無橫向溢出，並收集頁面與console錯誤。

都市規模篩選驗證主／巨／大／全／隱、跨劇本年代更新及繁中／日文切換。報告欄另外在1920×1080、1440×900、1280×800、1280×850、1024×768、1000×768、390×844及844×390切換尺寸，核對頂部不重疊、報告與按鈕唯一、地圖比例及底邊、窄屏回退、無橫向溢出，以及倍率和選城保留。

截圖與報告寫入`build/browser-results/`及`build/browser-report/`；失敗時保留trace與video。CI依執行次數分開保留診斷檔7天，任務重跑不與先前報告衝突，便於檢查實際畫面與失敗步驟。啟動失敗案例的預期404與非預期錯誤分開判定，不把故意中斷一次下載當作一般場景的載入錯誤。

分段補給另有[受控實際操作驗收](../tests/browser_resupply.spec.mjs)，透過[五城測試目錄](../tests/browser_resupply_fixture.py)啟動原本HTTP處理器及頁面，使用真實交易、日曆、AI、每日減員、運輸與存讀服務，沒有向瀏覽器注入狀態。桌面1280×900及觸控390×844各跑兩例：首段備糧→缺糧友城→運輸隊同城會合送糧→押運真實返原城，以及未救援時十日缺糧減員並開始撤退。另核對送糧數字上限、最大值、繁中／日文草稿、原城名冊、非即時交付及console錯誤；受控目錄不代表各歷史戰役都自然出現相同路徑。

```sh
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config tools/browser-tests/resupply.config.mjs
```

[補給驗收設定](../tools/browser-tests/resupply.config.mjs)自行啟閉`127.0.0.1:18919`測試服務，不使用玩家的8878服務；截圖與失敗trace保存在`build/resupply-browser-results/`。這項檢查驗證真實CPU服務與UI；前述靜態驗收仍負責發布包的Worker及Pyodide邊界。

## 多劇本、多種子的跨年戰役

[長期回放工具](../tools/campaign-soak/run.py)使用普通`Campaign.command`交易、戰略／戰術AI、內政、運輸、事件、亂數與存讀服務。`HeadlessCampaign.view()`只省略回放未使用的介面目錄與路線回應，不直接修改城池、人物、資源、日期或天候收據。玩家策略固定為防守與內政管理，用於可重現地推進戰局，不代表最優玩家打法。

| 案例 | 劇本與玩家勢力 | 每種子的長度 | 自然年月路徑的檢查點 |
| --- | --- | --- | --- |
| `early` | 184年2月・黃巾及漢廷，兩場獨立新戰役 | 黃巾最多72旬；漢廷必須完整72旬、2年 | 黃巾的真實玩家繼承，以及漢廷的持續跨年驗證 |
| `middle` | 217年7月・魏 | 144旬，4年 | 曹操退出與玩家繼承、221年武昌建置 |
| `late` | 263年5月・吳 | 72旬，2年 | 孫休退出與玩家繼承 |

預設每個案例使用種子`3`與`2026`，逐一執行Python與Rust行軍後端。共6組案例／種子，每個後端實際建立8場獨立戰役。漢廷、中期與後期的持續驗證合計必須完整576旬，另加兩場黃巾繼承回放的實際旬數，最多每個後端720旬、雙後端1,440旬。這裡的「年」按本作每月3旬、每年36旬計算；不同新戰役的時間不拼接為一場持續戰役。

`early`每個種子固定執行`huangjin_succession`與`han_continuity`兩段，各自從相同184年劇本透過`new`建立。黃巾可因正常勝敗自然結束，但必須通過全部守恆與存檔校驗、雙後端完整軌跡一致，並實際發生玩家繼承；早亡仍記為`early_finish`，例如35旬不會被寫成72旬。漢廷必須獨立完成全部72旬並跨年，不能用黃巾已完成的旬數補足。兩段都完成後才判定案例覆蓋，任一段的校驗、存讀或雙後端比較失敗都會阻斷；過程不更換玩家、不續接已結束戰役、不注入人員或資源。

```sh
RUSTUP_TOOLCHAIN=1.93.0 python3 -B game/build_march_core.py --check
python3 -B tools/campaign-soak/run.py \
  --case early middle late --seeds 3 2026 \
  --output build/soak/report.json --progress
```

每旬檢查城池資源非負、99人容量、兵員守恆、名冊與年代校驗、AI旬期沒有重複或跳過。每月及繼承後執行JSON存檔往返，並在雙後端間比較完整存檔狀態、亂數狀態／抽取次數與命令軌跡。工具記錄經濟總量、前線缺員、運輸等待、勢力與城池歸屬等觀察資料；觀察告警用於發現需繼續調查的戰局，不把告警閾值或一組成功回放當作已證明平衡。

報告使用`tk2-campaign-soak-v2`格式，寫入Git忽略的`build/soak/`。早期案例在`legs`分別保存兩場完整結果與觀察，`coverage`明列漢廷完成旬數和黃巾實際旬數、繼承次數，避免把獨立戰役混為一場。遇到校驗、存讀、雙後端或階段推進失敗時，以非零狀態結束並在`failures`記錄案例和種子。自訂`--turns`會改變預設長度，並將早期案例標為`smoke_only`；例如以下只有局部冒煙檢查，沒有跨年與雙後端驗證能力：

```sh
python3 -B tools/campaign-soak/run.py \
  --case early --seeds 3 --turns 3 --backends rust \
  --output build/soak/smoke.json
```

## 按影響範圍執行的CI

[範圍規劃器](../tools/ci/plan.py)在每次main推送或PR產生`tk2-test-plan-v1`計畫，摘要列明基準commit、修改檔案、選中的瀏覽器／Python組、劇本ID、必要工作及發布決定。未知路徑、缺少可信基準、改動範圍無法辨識或CI選擇器自身變更，都回退完整驗證。

| 改動 | 選擇的驗證 |
| --- | --- |
| 白名單內README、純說明Markdown | 空白、UTF-8與倉庫內聯相對連結；不建置或部署遊戲 |
| 獨立封面、圖標、音頻 | 全局輕量校驗、相關Node夾具、封面／音頻／開始入口／失敗重試／認證回跳／存讀恢復的8個視口用例 |
| 全局`app.js`、共用樣式或語言入口 | 全局輕量校驗、完整瀏覽器組；不因純UI改動執行規則矩陣及跨年AI |
| 單個`scenarios/*.json`的獨立開局資料 | 全29劇本身份／引用校驗、指定ID的生成位元組與真實開局、3旬正常命令、完整存檔／RNG雙後端對照、相關歷史及瀏覽器用例 |
| 共享武將／城池／道路／規則、構建器、CI基礎設施 | 完整驗證；劇本內覆寫公共規則也不視為局部開局變更 |

所有非純文檔改動都保留來源資料一致性、全部29劇本的基本身份／引用／容量／資源檢查、JS語法與現有Node夾具、固定SDK及素材校驗。單個劇本也可能更新全局來源指紋；這類生成物或存檔標識變化仍要檢查，不會以刪除SHA或RNG斷言來縮短測試。

Python與瀏覽器分別使用[`test-groups.json`](../tools/ci/test-groups.json)和[`cases.json`](../tools/browser-tests/cases.json)登記依賴。Python模組新增而未登記、瀏覽器用例未登記、計畫含未知組／未知ID，或篩選後沒有任何用例，都會失敗。`python_groups`與瀏覽器`groups`分開，避免全局UI測試意外拉入全部後端規則。瀏覽器仍保留現有24用例各兩個視口的完整48項模式；歷史專題按明列ID選入，其必要跨劇本比較保留，一般深度開局循環只使用指定ID。

行軍測試另拆成純向量／ABI矩陣與[真實存檔相容性](../tests/test_remake_march_save_compat.py)。局部劇本仍檢查8條原始存檔／RNG基線與雙向後端讀檔；大向量矩陣留在完整模式。只省略未被這些基線使用的昂貴UI視圖，生產規則、原金標、完整狀態與存檔摘要不變；實際視圖由WASM回放和瀏覽器檢查。

main推送以[上次實際成功部署](../tools/ci/published_base.py)的commit為基準，確認`github-pages`有效success狀態、同倉庫main、Pages工作流、成功的deploy工作及精確發布步驟；不使用`HEAD^`或僅看工作流綠燈。新推送因此包含尚未發布的累積改動，即使前一輪CI被取消也不會漏測。PR使用與目標分支的merge-base；新增／刪除／改ID讀取前後索引，不能只由檔名猜測。

`tools/ci/run_scoped_tests.py --plan PATH --list-only`只輸出選中的模組／劇本，不載入戰役或執行測試；去掉`--list-only`執行對應檢查，`--report PATH`保存結果。以下建立本機完整計畫，不要求查詢遠端部署：

```sh
mkdir -p build/ci
python3 -B tools/ci/plan.py --head HEAD --force-full > build/ci/full-plan.json
python3 -B tools/ci/run_scoped_tests.py --plan build/ci/full-plan.json --list-only
TK2_TEST_PLAN=build/ci/full-plan.json node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config tools/browser-tests/playwright.config.mjs --list
```

完整模式使用Python／Rust各6分片、6組跨年種子、Rust格式／lint／原生／WASM差分，以及全部現有素材與瀏覽器驗收；桌面／觸控各拆2分片，啟動前驗證各裝置的用例並集無缺漏、無重複。可在GitHub Actions的`Web campaign checks`手動選`force_full`；每天日本時間03:00另跑一次完整回歸，定期／手動驗證不取消main推送的發布CI，也不自動發布網站。

## CI發布門檻

命令書確認新增獨立桌面／觸控用例，逐步檢查城池、操作與實際本數，確認前保存完整狀態作對照；取消、Escape及語言切換均不扣書或物資。再以真實按鈕驗證徵兵接續配兵、最後1本後的多將配分及格式2存檔恢復。其餘既有流程會透過真正的確認按鈕同意新增提示，不直接呼叫遊戲交易或注入狀態。

戰場移動驗收觀察穩定舞台中的實際旗標中間像素，從名單焦點測試四方向及Enter，再比較移動前後機動力、亂數與完整存檔。普通交鋒須看到即時回擊，確認雙方兵力下降且只扣發起方2點；演出自然結束或略過後，不能再造成第二次傷害。另保留地圖圖片失敗時的同格點選與讀檔回歸。

[共用流程](../.github/workflows/web-checks.yml)只建置一次`candidate-web-SHA`，先驗真實WASM與CPU回放；桌面／觸屏在兩個獨立runner下載同一份候選包，各自檢查commit、檔案清單和內容SHA，再執行所需用例。物流／補給有獨立的條件工作。

[最終閘門](../tools/ci/gate.py)根據計畫核對每項必要工作，失敗、取消、意外跳過或缺失都拒絕；通過後再次驗證原候選包，才保留`verified-web-SHA`。按計畫不需要的工作可顯示skipped，不能冒充已測過。

[Pages流程](../.github/workflows/pages.yml)只接受本倉庫main推送的成功精確commit與同次計畫，純說明文檔的`publish=false`不發布。手動Pages發布明確要求完整驗證；所有發布都前後核對目前main與完整檔案SHA，直接部署通過測試的原產物，不重新建置、不執行下載包內的程式碼。較新推送可取代舊推送驗證，較舊commit不發布。

## 發布後的實際驗收

正式站使用獨立測試頁檢查啟動、劇本／勢力選擇、一次可見操作、存檔讀回與console／網路錯誤，並核對`runtime/build.json`的commit和實際資源。驗收過程保留玩家原本的分頁與戰役；若需雲端或郵件測試，另行取得對應操作授權，不以本機夾具結果宣稱已完成真實投遞。

[規則CI](../.github/workflows/remake.yml)與[Pages發布流程](../.github/workflows/pages.yml)記錄目前的自動檢查及發布門檻；每次發布應分別報告本機檢查、該commit的遠端CI、正式站檔案與實際操作結果。遊戲容量、旬期、素材數量的核對來源見[目前戰役規則](remake-campaign-rules.md)。
