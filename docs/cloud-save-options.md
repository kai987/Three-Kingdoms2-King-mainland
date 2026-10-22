# 帳號式雲端存檔

遊戲以 Supabase Auth 登入，獨立資料表儲存私人存檔。每帳號有 5 個槽，可跨裝置保存、讀回與刪除。首次註冊需確認電子郵件；登入不自動上傳或替換戰役。網頁服務目前仍由本機啟動。

每次保存同時比對槽的 `save_id` 與 `revision`，防止其他裝置更新、刪除或重建後被舊操作覆蓋。衝突時重新整理列表再選擇；不自動重試寫入。資料表以使用者身分隔離，其他帳號不能讀取或改動。

傳輸保留原始存檔 JSON 與 SHA，不以瀏覽器重新序列化數值來改變 checksum。本機與雲端讀檔都要通過目前劇本 ID、資料 SHA、狀態 checksum、名冊、年代、兵員及 RNG 驗證。只支援目前資料，不做舊劇本遷移。

只有使用者明確按下保存／讀取／刪除時才操作對應槽。帳號切換或關閉對話框後的過期回應不會誤操作新帳號；遊戲狀態已變更時不會套用過期的讀檔請求。覆蓋、載入及刪除都有確認。

公開設定在 `game/config/cloud-save-public.json`，僅包含公開 URL 和 publishable key；本機服務會拒絕其他密鑰格式。自託管 SDK 在 `game/vendor/`。資料表與 RLS 定義在 `supabase/`，SDK 重建工具在 `tools/cloud-sdk/`。資料庫密鑰不放進前端。

測試使用實際 SDK 與受控 Auth／PostgREST 回應，覆蓋跨裝置、版本衝突、帳號隔離、離線、損壞存檔與原文傳輸；這不等於已代替玩家完成真實信箱註冊及確認。

## 確認信與郵件服務

2026-10-23 的唯讀排查已在本遊戲使用的 Supabase 專案控制台確認：`Enable custom SMTP` 未啟用，目前使用預設 SMTP。最近 Auth 日誌有 `/signup` HTTP 200 與 `/token` 的 `Invalid login credentials`，未找到 SMTP 錯誤紀錄；HTTP 200 只代表註冊請求被處理，不能證明郵件已送達，也不能單憑登入失敗判定密碼或信箱是否已確認。

同次唯讀統計顯示，最近24小時沒有新增帳號，既有帳號已完成信箱確認，沒有待確認帳號。重複註冊既有信箱的可能性仍需按玩家使用的實際帳號核對，不能單憑上述統計斷言是哪個信箱。已註冊者應使用原密碼登入；重複註冊不會變更密碼。界面提供此通用提示，不根據註冊回應洩漏帳號是否存在。

依 [Supabase 官方 SMTP 說明](https://supabase.com/docs/guides/auth/auth-smtp)，預設郵件服務只寄往專案所屬組織的團隊成員信箱，寄件量也受嚴格限制，且不保證送達。開放一般玩家以電子郵件註冊，需要設定自訂 SMTP、驗證寄件網域並確認供應商限制。此專案也供其他應用程式使用，因此 SMTP、信件範本與 redirect allowlist 的修改要一併評估其他應用程式。

遊戲提供明確的「重寄確認信」按鈕，使用 [Auth `resend({type:'signup',email})`](https://supabase.com/docs/reference/javascript/auth-resend)，不需要輸入密碼。註冊或重寄請求成功後需等待 60 秒才能再次重寄；服務端限流可能更久。按鈕不會自動發信、建立新帳號或改動存檔。畫面只顯示中性的請求結果，不宣稱郵件已送達，也不顯示原始服務錯誤中的收件者或其他私人資料。未授權的收件地址與停用註冊會顯示對應的設定問題，不再一律顯示密碼錯誤。

目前維持確認信完成後回到遊戲手動登入的流程，`detectSessionInUrl` 仍為 `false`。唯讀核對發現，共享專案的 Site URL 為 `https://kai987.github.io/n1-wrong-answer-site/`，allowlist 也只有該站的 `/**`；因此目前確認成功後可能返回另一個應用程式。沒有修改共享 Site URL／allowlist，本機 `http://127.0.0.1:8878/` 尚不能視為已核准的回跳網址。

公開設定可選填 `confirmationRedirectUrl`。只有管理者先在 Supabase allowlist 加入本遊戲的精確回跳網址後，才應填入；註冊和重寄會以 `options.emailRedirectTo` 傳入該網址。空值或未設定時保持原有行為，不從瀏覽器位置自動猜測。僅接受 HTTPS，或僅限 `localhost`／`127.0.0.1`／`[::1]` 的 HTTP，不接受帳號密碼或 fragment。此選項不會自行修改遠端 allowlist。

確認頁回跳問題與郵件送達是不同檢查項，應在自訂 SMTP 就緒後再用真實信箱驗收。保留電子郵件確認，不以停用驗證或人工確認帳號繞過寄件問題。

管理者接通步驟：

1. 在郵件供應商建立並驗證寄件地址／網域，取得 SMTP host、port、user、password。
2. 在 [SMTP 控制台](https://supabase.com/dashboard/project/flpmblfscgcbrprwwckz/auth/smtp) 啟用自訂 SMTP，填入寄件地址、顯示名稱及供應商資料；密碼僅在控制台輸入，不放進本專案或聊天紀錄。
3. 在 [URL Configuration](https://supabase.com/dashboard/project/flpmblfscgcbrprwwckz/auth/url-configuration) 的 Redirect URLs 加入本遊戲的精確網址。本機測試為 `http://127.0.0.1:8878/`；其他裝置需使用可連線的正式 HTTPS 網址。保留其他應用程式現有 Site URL 與 allowlist。
4. 在公開設定填入與 allowlist 一致的 `confirmationRedirectUrl`，重新啟動遊戲服務。由玩家主動重寄、檢查供應商投遞紀錄及收件匣，點選確認後回到遊戲登入，再驗證雲端槽位保存和跨裝置讀取。
