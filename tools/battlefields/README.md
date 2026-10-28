# 原版の都市別戦場データ

`game/assets/battlefields/` は、ユーザー提供の『三国志2 超級版』ROM に含まれる **30 個の異なる戦場背景**を、オフラインで復元したものです。従来の `battle-original/tactical.png` は 1 戦場の 256×160 の表示窓でした。既存素材は上書きしていません。

各 PNG は **496×304（31×19 マス、1 マス16×16）**です。原画の画素を維持し、Web 側で nearest-neighbor により4倍で描画します。AI による描き直し、汎用パレットへの置換、他都市の地形の貼り合わせは行いません。

## 検証

```sh
python3 tools/battlefields/build.py --check
python3 -m unittest discover -s tests -p test_remake_battlefields.py
```

Python 標準ライブラリのみで実行できます。ROM・研究アーカイブ・Pillow・エミュレーター・ゲームのセーブデータは不要です。

チェックは次を確認します。

- 30 個の descriptor、120 個の chunk、CHR と attribute から、全17,670マスと全PNG画素を再計算する。
- 各地図の SHA-256、実寸、異なる30布局、raw tile / class / palette / camp / service 座標を照合する。
- 同梱した実際の Nestopia 画面（原 ID 5・6・9）に対し、背景 CHR・attribute・**120,832 画素**を完全一致で比較する。原作の部隊等で nametable が置換されたマス、および OAM と重なる画素は比較対象外にする。
- 全地図で使用する6色が、実際に比較した画素にすべて含まれることを確認する。未確認の色を「原版」として補わない。

`index.json` 内に、復元に必要な小さなデータ表と各抽出ブロックの ROM ファイル位置・SHA-256 を保存しています。ROM 全体やエミュレーター状態は同梱しません。`tools/battlefields/evidence/` の画面3枚は検証専用であり、ゲームの公開アセットには登録しません。

## オフラインで再抽出する場合

```sh
python3 tools/battlefields/build.py \
  --rom /path/to/user-provided-original.nes \
  --evidence-root /path/to/read-only-research-archive
```

ROM の SHA-256 は `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82` に固定しています。不一致なら出力を書き込みません。元の ROM・画面・状態を読み取るだけで、OpenEmu を起動したり、ユーザーのゲームやセーブデータを変更したりしません。

原版のデータ表は以下です（iNES ヘッダーを含むファイル位置）。

| データ | 位置 | 内容 |
|---|---:|---|
| 城市 descriptor pointer | `0x31F5A` | 30 little-endian pointers |
| 移動用 tile pointer / bank | `0x117DB` / `0x118CB` | 120 chunks |
| 描画用 tile pointer / bank | `0x2E652` / `0x2E832` | 移動用の表との完全一致を確認 |
| Attribute pointer | `0x2E742` | 各 tile pointer の64バイト前 |
| Raw tile → class | `0x1175B` | 128 entries |
| 16×16 → 8×8 BG tile | `0x3F487` | TL・TR・BL・BR の128組 |
| 戦場施設の座標 | `0x23BB4` | 30城市×3組の XY |

4 chunk の順番は各原 ID `i` に対し `[4i, 4i+2, 4i+1, 4i+3]`。原作の packed Y=15 は attribute 行なので除き、visual Y=15 を packed Y=16 に対応させます。下側 chunk の未使用領域は戦場を広げるために使いません。

## 原版で確認できた範囲と制限

固定 CHR フレームは `[139,137,138,136]`、色は実際の native capture の `royaltea`。原作は scanline ごとにバンクを切り替え、川にもフレーム差があるため、これは**確認済みの静止背景フレーム**の復元です。PPU の終了時バンクだけから画面全体を復元したものではありません。

原 ID 5・6・9 の比較画面は、元ROMを変更せず、既存の独立テスト状態の城市IDとカメラだけを変更して元コアで描画した研究fixtureです。自然進行のプレイ画面であるとの主張はしません。変更箇所と元画面・状態・RAM・capture metadata のハッシュを記録しています。

`classes` は0～5です。

| class | 表示用キー | 確認範囲 |
|---:|---|---|
| 0 | forest | 原画と回復済みの処理から森林と推定 |
| 1 | special_ground | 滑らかな土色。正式名称は未確認で、「道路」「砂漠」と断定しない |
| 2 | plain | 平地。raw6/7/8の施設マーカーも移動時には2になる |
| 3 | water | 原画・計略条件と整合 |
| 4 | mountain | 原画・適性別の移動費用と整合 |
| 5 | camp | 原作の拠点／占領処理と整合 |

原版では適性0～2の移動費用は正数です。これらの class のどれかを「絶対に通れない壁」と扱う根拠にはしません。`raw_classes` の6・7・8は追加の移動地形ではありません。施設の種類は別の城市別 XY 表で判定するので、raw class 値から武器屋等へ直接変換しません。

各地図の `camps` は1個です。`camps` と `markers` は visual / packed の両座標、`services` は米屋・武器屋・病院の元座標と存在有無を持ちます。原版は建物や部隊を別レイヤーで描くため、**PNG は背景レイヤーだけ**です。建物を実際に復元するまでは、地面の上に元の建物画像まで存在するとは主張しません。

`source_city_label` は既存の攻略表の表記をそのまま保管した参照名です。ROM 字形を全件照合した都市名ではなく、特に「西安阳」「予州」「涪陵」「永晶」等は未解決の表記を含みます。原 ID と新地図の115都市の同一性を自動的に認定せず、別の明示的な対応表で管理します。

元ゲームの画像・データの権利は原権利者に帰属します。コード用の MIT ライセンスで再許諾するものではありません。
