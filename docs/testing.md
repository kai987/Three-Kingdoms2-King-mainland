# 遊戲驗證與回放

驗證分為規則／資料檢查、介面夾具、真實WASM回放、真實瀏覽器操作與長期戰役回放。各層檢查不同邊界：Node腳本通過不等於網頁已能操作，CI通過也不等於線上快取已更新或郵件已送達。下列命令均在專案根目錄執行，使用測試戰役，不連入玩家的本機服務、雲端帳號或存檔槽位。

## 規則、資料與輕量介面檢查

使用Python 3.10以上與Node.js；CI使用Python 3.13與Node.js 24。Rust原生與WASM差分另使用固定Rust 1.93.0及`wasm32-unknown-unknown`目標。

```sh
# 戰役來源與生成資料一致
python3 -B game/build_campaigns.py --check

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

## 真實WASM與CPU回放

```sh
npm ci --prefix tools/web-runtime --ignore-scripts
python3 -B game/build_web.py --output build/web
node tests/browser_engine_smoke.mjs build/web
```

這項檢查在Node中實際載入發布包的Pyodide與Python戰役核心，並與CPU參照重放相同命令；比對狀態、存檔與亂數。它也檢查完整／精簡視圖的還原結果。這是發布包的執行驗證，不是DOM頁面或完整多年戰役的測試。素材及執行環境必須先按[發布流程](web-deployment.md)建置。

## 真實瀏覽器操作

[瀏覽器驗收](../tests/browser_ui.spec.mjs)使用固定Playwright `1.64.1`與其對應的Chromium，在實際頁面載入同一份`build/web/`、Worker、Pyodide與戰役核心。桌面為1280×800，觸控模擬為390×844，循序執行以限制資源占用；觸控Chromium模擬不等同於已驗收實體手機或Safari。

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

截圖與報告寫入`build/browser-results/`及`build/browser-report/`；失敗時保留trace與video。CI依執行次數分開保留診斷檔7天，任務重跑不與先前報告衝突，便於檢查實際畫面與失敗步驟。啟動失敗案例的預期404與非預期錯誤分開判定，不把故意中斷一次下載當作一般場景的載入錯誤。

## 多劇本、多種子的跨年戰役

[長期回放工具](../tools/campaign-soak/run.py)使用普通`Campaign.command`交易、戰略／戰術AI、內政、運輸、事件、亂數與存讀服務。`HeadlessCampaign.view()`只省略回放未使用的介面目錄與路線回應，不直接修改城池、人物、資源、日期或天候收據。玩家策略固定為防守與內政管理，用於可重現地推進戰局，不代表最優玩家打法。

| 案例 | 劇本與玩家勢力 | 每種子的長度 | 自然年月路徑的檢查點 |
| --- | --- | --- | --- |
| `early` | 184年2月・黃巾 | 72旬，2年 | 張角退出與玩家繼承 |
| `middle` | 217年7月・魏 | 144旬，4年 | 曹操退出與玩家繼承、221年武昌建置 |
| `late` | 263年5月・吳 | 72旬，2年 | 孫休退出與玩家繼承 |

預設每個案例使用種子`3`與`2026`，逐一執行Python與Rust行軍後端。共6組案例／種子、每個後端合計576旬；兩個後端共1,152旬。這裡的「年」按本作每月3旬、每年36旬計算。

```sh
RUSTUP_TOOLCHAIN=1.93.0 python3 -B game/build_march_core.py --check
python3 -B tools/campaign-soak/run.py \
  --case early middle late --seeds 3 2026 \
  --output build/soak/report.json --progress
```

每旬檢查城池資源非負、99人容量、兵員守恆、名冊與年代校驗、AI旬期沒有重複或跳過。每月及繼承後執行JSON存檔往返，並在雙後端間比較完整存檔狀態、亂數狀態／抽取次數與命令軌跡。工具記錄經濟總量、前線缺員、運輸等待、勢力與城池歸屬等觀察資料；觀察告警用於發現需繼續調查的戰局，不把告警閾值或一組成功回放當作已證明平衡。

報告使用`tk2-campaign-soak-v1`格式，寫入Git忽略的`build/soak/`。遇到校驗、存讀、雙後端或階段推進失敗時，以非零狀態結束並在`failures`記錄案例和種子。自訂`--turns`會改變預設長度；例如以下只有局部冒煙檢查，沒有跨年與雙後端驗證能力：

```sh
python3 -B tools/campaign-soak/run.py \
  --case early --seeds 3 --turns 3 --backends rust \
  --output build/soak/smoke.json
```

## CI與發布門檻

[共用驗證流程](../.github/workflows/web-checks.yml)集中以下檢查，避免規則CI與發布各自重跑整套工作：

- Rust格式、lint、測試、可重現原生／WASM建置及差分；依賴工作使用同次執行產生的原生核心。
- Python與Rust兩個後端各跑完整戰役回歸；每個後端按測試檔案穩定拆成3片，合計6個並行工作，另有全集與無重疊檢查。各片安裝固定瀏覽器執行環境，避免發布邊界測試因缺少Pyodide而靜默跳過。
- 六組案例／種子的跨年回放並行執行，每組內對照Python與Rust，成功或失敗均保留診斷報告7天。
- 來源資料、語言、JavaScript介面夾具、固定雲端SDK與原版／補繪素材檢查。
- 一次靜態建置、真實WASM／CPU回放、桌面及觸控Chromium操作；通過後保留同一份發布包。

[主驗證入口](../.github/workflows/remake.yml)在`main`推送或PR時呼叫共用流程。同一分支的舊驗證可由較新提交取代。[Pages流程](../.github/workflows/pages.yml)只接受本倉庫`main`推送成功的精確commit與同次驗證產物；手動發布也先走同一組門檻，不跳過檢查。部署前核對目前`main`、`runtime/build.json`的commit、完整檔案清單、大小、逐檔SHA256及整體內容SHA，直接部署已測試的產物，不重新建置或執行下載包內的程式碼。較舊提交已被新`main`取代時不發布。

## 發布後的實際驗收

正式站使用獨立測試頁檢查啟動、劇本／勢力選擇、一次可見操作、存檔讀回與console／網路錯誤，並核對`runtime/build.json`的commit和實際資源。驗收過程保留玩家原本的分頁與戰役；若需雲端或郵件測試，另行取得對應操作授權，不以本機夾具結果宣稱已完成真實投遞。

[規則CI](../.github/workflows/remake.yml)與[Pages發布流程](../.github/workflows/pages.yml)記錄目前的自動檢查及發布門檻；每次發布應分別報告本機檢查、該commit的遠端CI、正式站檔案與實際操作結果。遊戲容量、旬期、素材數量的核對來源見[目前戰役規則](remake-campaign-rules.md)。
