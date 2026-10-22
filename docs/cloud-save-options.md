# 帳號式雲端存檔

已依使用者選擇接入現有東京Supabase專案，為本遊戲單獨建立`public.tk2_cloud_saves`。遊戲頂欄「雲端存檔」支援電子郵件／密碼登入、註冊與每帳號5個存檔槽。註冊依該專案現有設定寄出確認信；完成信箱確認後，回到本遊戲登入。本遊戲不改共用專案的Auth設定、其他應用資料或確認信跳轉網址。

每個槽可命名、保存目前戰役、讀取及刪除。在另一部執行本遊戲的裝置登入同一帳號，即可取得相同存檔列表；目前遊戲服務仍只監聽本機，雲端存檔功能不等於遊戲網站已部署至公網。瀏覽器本機保存、JSON下載／匯入繼續可用。

## 進度與衝突

- 登入只恢復帳號會話，不自動上傳或取代戰役；玩家明確選擇保存／讀取。
- 覆蓋現有槽、讀入戰役、刪除雲檔均先顯示具體資料確認。讀檔確認使用剛取得的遠端快照，而不是舊列表的內容。
- 每次保存同時比對槽的`save_id`與`revision`。另一裝置更新、刪除或重建後，舊版本操作回傳衝突；不自動重試覆蓋。重新整理列表後再選擇。
- 網路失敗或20秒逾時不顯示保存成功，也不影響本機進度。若遠端已收到請求但回應丟失，須刷新確認結果。
- 登出只登出此遊戲在此裝置的會話；本機戰役與檔案保留。切換帳號清除上一帳號的列表、輸入草稿和遲到的網路結果。

## 存檔相容與隔離

`save_text`保存伺服器輸出的原始JSON文字，保留`315.0`、`-0.0`等表示。資料庫另算原文傳輸SHA-256；這不是遊戲checksum，也不會重算遊戲checksum來接受受損資料。讀取仍交由原本`/api/load`核對格式、目錄SHA、遊戲checksum、兵員與名冊約束；所有舊目錄繼續供已發佈存檔使用。

資料表對`authenticated`啟用owner RLS，僅`auth.uid() = user_id`的資料可讀寫，匿名角色沒有表權限。觸發器以呼叫者權限驗證文字格式、導出日期／劇本／hash，並阻止修改槽身分與跳過revision。沒有`SECURITY DEFINER`或新擴充。可執行結構來源在[SQL](../supabase/schema/tk2_cloud_saves.sql)。

現有東京專案已套用MCP遷移`20261022024933 / tk2_private_cloud_saves`；SQL來源與該次遷移一致。其他專案須先套用此結構並填入自己的公開設定。

`game/config/cloud-save-public.json`只包含可公開的URL與publishable key，不包含管理密鑰。伺服器拒絕secret/service-role金鑰與不符合Supabase網址規則的設定，CSP只允許目前專案的HTTPS連線。帳號憑證直接交給Supabase Auth，遊戲Python服務不接收密碼或token。會話由官方SDK管理，使用本遊戲獨立的瀏覽器storage key；請在信任的裝置上登入。

官方SDK固定為`@supabase/supabase-js 2.118.0`，使用`esbuild 0.28.2`建立自託管bundle；執行遊戲不從CDN下載腳本。來源、依賴鎖及重建流程見[SDK建置工具](../tools/cloud-sdk/README.md)。

## 驗證範圍

已對真實東京資料庫以`authenticated`與`anon`角色、兩個隨機UID執行RLS、非法歸屬、CAS、刪除重建ABA、原文hash及不可變欄位測試。所有資料在同一交易回滾，沒有建立Auth測試帳號、寄信或上傳玩家存檔。測試來源：[交易回滾測試](../tests/sql/tk2_cloud_saves_rls.sql)。真實HTTP匿名查詢被拒絕，資料表安全顧問沒有新增本遊戲相關問題。

瀏覽器驗證使用實際自託管SDK、兩個獨立遊戲服務與受控Auth／PostgREST回應，涵蓋跨裝置保存／讀回、舊版315.0行軍存檔、原checksum、衝突、離線、損壞存檔、繁中／日文、1500px桌面與390px手機。這項測試不代表已用真實信箱完成註冊確認與登入；首次真人帳號流程需要玩家自行操作，密碼不應貼入聊天。

```sh
python3 -m unittest discover -s tests -p test_remake_cloud_config.py -v
node tests/test_remake_cloud_save.cjs
node tests/test_remake_cloud_ui.cjs
npm ci --prefix tools/cloud-sdk --ignore-scripts
npm run check --prefix tools/cloud-sdk
```

設計依據：[Supabase密碼登入](https://supabase.com/docs/guides/auth/passwords)、[資料隔離](https://supabase.com/docs/guides/database/postgres/row-level-security)、[Data API權限](https://supabase.com/docs/guides/api/securing-your-api)、[PostgreSQL17 SHA-256](https://www.postgresql.org/docs/17/functions-binarystring.html)。
