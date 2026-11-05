# 原版戰場部署資料核查

本目錄只重建及檢查[30城部署參照](../../game/config/references/original-battle-deployment-v1.json)，不改遊戲執行規則，不啟動模擬器，不改ROM或存檔。來源是本機固定ROM，SHA256為`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。JSON記錄11段資料的原始位址、長度、位元組與SHA256，所有城池、區域、異常均由這些位元組重新推導。

```sh
python3 -B tools/battle-deployment-original/build.py --check
python3 -B -m unittest discover -s tests -p 'test_remake_battle_deployment_reference.py'
```

只有重建或與原檔比對才需要使用者本機ROM：

```sh
python3 -B tools/battle-deployment-original/build.py --rom /path/to/pinned-game.nes
python3 -B tools/battle-deployment-original/build.py --check --rom /path/to/pinned-game.nes
```

加上`--archive-source /path/to/research-archive/source`可重跑原恢復碼的受控對照：2048個`C447`邊界案例，以及2560個`C3CB`順序陣位案例。腳本先核對兩份來源檔的SHA256，再只提供`F25F`的資料bank切換服務；不代入隨機值，不呼叫硬體或圖形服務，不寫入研究目錄的bytecode。這是恢復函數核對，並非自然遊戲截圖或獨立CPU原指令實驗，CI的無ROM檢查也不會宣稱已執行此本機步驟。

## 已確認的資料意義

- 守方是原陣列`0..9`、`0507`低位；攻方是`10..19`、高位。恢復碼`first_side`／`second_side`描述陣列順序，不代表攻守先後。
- 先以目標城的`physical16:9D72`鄰接列尋找來源城；匹配欄位的`physical16:9E62`值選攻方邊緣區，`physical17:9AB4`值選守方中央區。這些值是目標城自己的表索引，**不是東南西北編碼**。
- 攻方預設點由`physical6:8000`指標表取得，每區34 bytes；合法矩形由`physical6:932E`取得。守方對應`physical6:8C52`、每區32 bytes及`physical6:94D6`。
- 原點是`[packed_y,x]`；矩形為`[min_y,min_x,max_y,max_x]`，上限不含。現行31×19可見圖略過原資料列15，原`packed_y16..19`顯示為`y15..18`。
- `C3CB`只跳過已占用點，**不套用**`C447`的矩形或本作可見邊界。完整表保留13個重複、越界或矩形外的記錄。不能為了讓資料看來整齊而刪掉來源異常。
- 91個攻方區、53個守方區；128條有向鄰接。守方主將在所有中央區的第一點都對上現有戰場圖的原城砦。原預設陣位包括山、水，不應沿用目前初始化排除這兩類地形的限制。

## 遊戲可採用的最小接入界面

`resolve_reference(reference,target_original_city_index,source_original_city_index)`回傳`attackers`及`defenders`的配對區，無原版鄰接時回傳`None`。也可直接從JSON的`cities['original-09'].neighbors`匹配來源城，再取對應`sides[side].zones[index]`。不要自行把索引改寫成NESW。

`safe_visible_points(zone)`是**明示的本作安全過濾**：依原順序去重、限制原矩形及現行可見區。它不改證據，且每個區至少仍有13個攻方／14個守方原點，足夠正常10將，不需虛構部署點。玩家及AI應使用相同條件；部署不扣機動力、不抽亂數。

115城的區域共用不是已證原版新城部署。建議當兩個原模板索引存在真實原版鄰接時採該配對，並保留區域重用標籤；否則用最後一段戰略路線的來向，選城砦朝該來向最接近的原攻方邊緣矩形，再以同一鄰接記錄配守方中央區。角度平手採最小原鄰城索引，無有效向量亦用這個明示fallback。這段是證據包整理時的適配提案；現已由獨立的[執行期部署模組](../../docs/directional-deployment.md)接入新戰局，不能宣稱是原版115城方向規則。原始證據JSON保留整理時的提案標記，不改原表。

只對新戰鬥套新部署。現有戰鬥存檔已保存的位置、行動方及機動力應保留；讀檔、換語言、看預覽不能重排或補滿。

## 日本語

固定ROMの30都市・128本の有向隣接から、攻撃側91区画と守備側53区画を抽出します。区画番号は都市固有の表番号で、方角コードではありません。守備側は配列0〜9、攻撃側は10〜19です。原順序の重複や表示外座標を証拠から消さず、安全な表示・矩形フィルターを本作の適応として分けています。115都市への方向推定は設計案であり、この参照を追加しただけではゲーム中の配置は変更されません。
