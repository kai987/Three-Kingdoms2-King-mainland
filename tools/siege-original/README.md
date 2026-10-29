# 原版攻城畫面與小型資料表

`game/assets/siege-original/index.json` 保存固定原 ROM 與 Nestopia 核心的識別雜湊、兩次受控截幀的操作序列及記憶體修改清單。這是隔離測試狀態中的原核心影片輸出，並非自然進行戰役的紀錄；ROM未修改。原 ROM、核心、模擬器存態、RAM及個人路徑都不放入Web包。

保留完整原始截圖的原位元組為 `capture-*.png`；`witness-*.png` 為同像素的完整RGBA副本。背景及四個陣形圖示皆直接裁自原截圖，4倍版本為精確最近鄰放大，沒有重畫或推測新的細節。公開的 `capture-*-provenance.json` 將本機絕對路徑改為來源識別字；原始證據文件的雜湊與公開刪去路徑後文件的雜湊分開標記。

`native-tables.json` 只含原始小型資料表，沒有可執行ROM指令。資料記錄實際physical bank、CPU位址、檔案位置、原始hex與獨立雜湊：四種野戰陣形及兩種城內配置、等級與武力的兵種界線、步弓騎將行動順序、16×10城牆地形及其分類表。陣形與城內通道資料可由保留的小表離線重算。原始說明書38–43頁的URL與雜湊也一同記錄；不能從圖案推定額外城防加成或宣稱原版可自由拖曳部署兵卒。

保留的 `siege-formation-*` 及 `siege-piece-*` 背景差分候選混入原BG兵圖蓋掉城磚後留下的平底色像素。它們是來源研究的中間資料，明列 `runtime_eligible:false`、`clean_sprite_verified:false`，不能當成已驗證的透明兵卒。正式兵卒需有獨立可靠的原圖擷取證據；既有原版兵卒可作缺圖時的備用。候選資料不因哈希正確就能宣稱是乾淨原素材。

正式的 `native-sprite-{general,infantry,archer,cavalry}-{friendly,enemy}` 各為16×16，直接由原始CHR四個8×8片及原調色重建；每片的原位址、字節及雜湊均保留。先逐像素匹配原影片的完整不透明裁片，再僅將原背景圖樣索引透明化，沒有以RGB灰色去背，因此與背景同色的灰甲仍然保留。紅方步卒由既有原野戰畫面驗證，城內防方本來不產生步卒。全部八類都保留精確4倍的64×64 `sprite-{kind}-{side}-{0,1}`。目前每類可靠確認一個原姿勢，0與1鍵明示復用同一圖；部隊依正式位置移動，不將同圖聲稱為兩個已截取的進攻或防禦動作。

只用Python標準函式庫檢查全部PNG雜湊與尺寸、原截圖裁切像素、每個4倍像素、受控截幀證據及資料表一致性：

```sh
python3 -B tools/siege-original/check.py
python3 -B -m unittest discover -s tests -p 'test_remake_siege_assets.py' -v
```

以上驗證不讀ROM、研究檔案庫或模擬器。它驗證素材的來源與衍生操作；遊戲傷害、AI及兵士模式仍須另行驗證。


## 兵士算式與動作

新增`animation-provenance.json`記錄獨立核心中4個敵方前進命令位元組的受控改動，十張完整截圖、原OAM、調色板及像素證據。新增`native-sprite-*-move-*`以原CHR與OAM優先序重建兩個不同走格姿勢；灰／紅原調色板各有4倍衍生圖。`effect-melee`是原版命中閃光，`effect-arrow`是原箭矢；不將走格兩幀冒稱另有揮砍姿勢。舊靜止圖與來源截圖全部保留。checker逐opaque像素對照原影片，核對原CHR固定雜湊、透明索引、OAM翻轉及精確4倍像素。

`extract_soldier_rules.py`是可選離線研究工具，需`py65`與本人合法ROM，將原區段映射到NMOS6502並執行；只在E87A亂數邊界提供明示的0–8測試值，算術指令未改。以下可重建凍結數值：

```sh
python3 tools/siege-original/extract_soldier_rules.py /path/to/original.nes
python3 -B -m unittest discover -s tests -p 'test_remake_soldier_rules.py' -v
```

遊戲、Web包和CI不需要ROM、核心或`py65`，僅離線回歸讀取`soldier-rules-reference.json`裡的126組攻基與2080組傷害輸入輸出；沒有保存原機器碼。來源區段及runner雜湊可供獨立複核。完整公式、訓練度等本作後置規則與來源界線見[兵士戰說明](../../docs/soldier-combat.md)。
