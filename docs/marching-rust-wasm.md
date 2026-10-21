# 行軍Rust／WASM核心

同一份`crates/march-core/`負責路徑、地形／月份時長、陰平與子午谷、季風及整數餘兵分配。它編譯為伺服器原生庫與瀏覽器WASM；戰役指令、亂數、資源提交及存檔仍使用原來的Python層。

## 建置與啟動

需要Rust1.93.0、`wasm32-unknown-unknown`目標及Python3.10以上：

```sh
rustup toolchain install 1.93.0 --profile minimal --component clippy,rustfmt --target wasm32-unknown-unknown
RUSTUP_TOOLCHAIN=1.93.0 python3 game/build_march_core.py
MARCH_CORE_BACKEND=rust python3 -I -S -B game/serve.py --port 8878
```

`build/march-core/`內的原生庫與CLI依作業系統重建，不加入Git；`game/wasm/`保存已編譯的WASM與來源／二進位SHA256清單。鎖定依賴、編譯器及路徑重映射，使CI可用`--check`逐位元組核對WASM。不得用重新產生劇本來「修正」相容性測試。

預設`auto`在有原生庫時使用Rust；缺少原生庫時使用保留的Python實作。`MARCH_CORE_BACKEND=rust`要求原生庫存在且ABI正確，否則明確失敗；`python`可供差分重播。切換不寫入存檔，也不影響目錄校驗值。`GET /api/march-status`供本機驗證實際後端與呼叫次數。

## 遊戲內的接線

- 伺服器的路徑查詢、批量路線報價、方向／季節判定和抵達時的整數減員，透過`source/remake/march_core.py`呼叫原生核心。JSON只包含計算輸入；共享ABI由鎖保護，原生上下文快取有上限。
- 瀏覽器從唯讀的`/api/march-config?scenario=...`取得不可變路網，在Worker中載入同一核心的WASM。路線選擇及行軍預估使用該批量結果；視圖改變後丟棄過時的回應。
- 風險預覽以選中部隊計算最少／最多餘兵，不抽亂數。瀏覽器不支援WASM、載入失敗或逾時時，路線介面沿用伺服器報價。
- 出征／抵達仍由伺服器驗證並原子提交；不接受瀏覽器傳來的時長、傷亡或路徑作為權威結果。現有存取流程及地圖呈現維持原樣。

## 相容契約

1. 陰平到成都維持單向、平地基準時間2倍、最終餘兵三分之一。子午谷7～9月時間4倍／損失50%，其他月份時間2倍／損失20%。
2. 季風以原地理座標計算方向：順風速度為平地4倍、逆風為四分之一；陸地接駁與登船時間分開計。4月沿用原平靜海況。
3. 一整段航程的風暴仍只由Python抽一次原有亂數。不同海段合併成一次風暴，固定險道按原順序結算；抵達等待、重讀和回執不重複扣兵。
4. 減員以全軍總量向下取整，再依餘數及原武將順序分配，保留整數兵力守恆。Rust不持有RNG，也不新增任何隨機來源。
5. 保留原路徑平手規則：標量直連路線按日數、距離、ID選擇；批量直連報價維持原邊順序。友軍連通、敵城只准直接進攻、探索與揭露時點不變。
6. 舊目錄維持原浮點數表示，新險道目錄維持整值數字正規化、Python的一位小數捨入；存檔仍是version1、原目錄原始位元組SHA及原canonical checksum。

## 驗證入口

```sh
cargo fmt --manifest-path crates/march-core/Cargo.toml --check
cargo clippy --manifest-path crates/march-core/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path crates/march-core/Cargo.toml --locked
python3 game/build_march_core.py --check
node tests/march_wasm_parity.cjs
node tests/test_remake_march_worker.cjs
MARCH_CORE_BACKEND=rust PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_remake_*.py' -v
```

差分測試比較Python、原生Rust與實際WASM；戰役重播則比較每步完整狀態、保存資料、checksum與RNG狀態／抽取次數。Worker另測過時回應、上下文重用、載入失敗和逾時。瀏覽器驗收須實際操作出征及抵達，僅有WASM檔案或編譯成功不表示整條遊戲流程已驗證。

本次未搬動戰鬥、計略、單挑、人物年代、完整AI或HTTP服務；也未將整個遊戲改為離線純瀏覽器執行。未以語言替換本身宣稱固定加速倍數。

## 2026-10-22驗收記錄

- 原生Rust通過15,712組Python canonical JSON對照；WASM通過15,711組，另以原生保留只有Python可表達的整數／浮點拼寫差異。涵蓋所有現行路段、雙向、12個月、5種選路、舊路網、平手與非法輸入。
- 9種遷移前行軍基準的完整狀態、存檔checksum與RNG皆一致；Python與Rust可互讀尚未抵達的行軍存檔。三個月自然AI戰役逐指令比較狀態、保存資料、亂數、revision與journal亦相同。
- 227項完整Python回歸通過，再補上的自然AI對照測試獨立通過；Rust10項測試、fmt、Clippy、Worker生命週期／故障測試、語系及地圖操作檢查通過。WASM5,000次呼叫的緩衝區回收檢查通過。
- 桌面與390px手機使用實際Chrome／Worker。217年7月吳軍300兵探索珠官→夷洲，預覽30～60兵；確認只新增一次風暴亂數，8月抵達後剩33兵並揭露航路。切換語言、取消預覽及WASM故障回退不改保存資料。
- 本機8878服務已使用Rust後端；重啟時以當下存檔恢復184年4月、第3回合，重啟前後保存資料完全一致。184份既有目錄／地圖資產保持逐位元組相同。
- 從另一份含空格路徑的專案副本重建，WASM及manifest完全相同。WASM為343,022位元組，SHA256：`97d1aaf6607b6fb9d9bcd8f1df039825e6381f0058262b5aaa3d3f01c8a19316`。

## 目前的效能界線

本次先確立跨後端的相同結果，**尚未取得行軍視圖加速**。本機217年魏、seed2026、每種後端2次`_travel_view`的中位數：v9為Python2341ms／原生Rust3965ms，v13為Python61ms／原生Rust242ms。兩組完整報價分別約7.24MB及8.43MB；目前JSON ABI必須再次建立、編碼及解碼這些重複的路段資料。首次Rust樣本含上下文註冊，量測與其他測試同時進行，不能當成所有裝置的固定速度比。

瀏覽器計算已放入Worker，但原生適配器仍有上述額外成本。後續應先將批量報價改為共用路段表與索引、縮小跨語言傳輸，再以完整HTTP／瀏覽器流程量測；不能僅憑Rust／WASM編譯成功宣稱提速。現有伺服器報價API仍保留，讓舊客戶端與載入失敗時的介面相容。
