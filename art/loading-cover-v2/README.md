# 表紙用素材 v2

騎将と歩兵は、戦闘用の小さな2コマ画像に代わる、表紙専用の生成画像です。原版から抽出した画像や特定の武将の再現とは区別します。各4コマの歩行を共通の縮尺と足元位置で整え、128×128pxの論理キャンバスから最近傍法で4倍に拡大しています。公開図集は各2048×512px、1コマ512×512pxです。原画への加筆や補間による平滑化はしていません。

背景は旧表紙と実際の `game/assets/map-campaign.png` を参照し、山脈・河川・海岸・都市を城門の背後に描き込んだ新規生成画像です。地理と道路は表紙の装飾であり、実際の戦役地図や経路計算の代用にはしません。

- `march-source.png`、`cover-map-source.png`：生成時の画像をそのまま保存。
- `march-prompt.txt`、`background-prompt.txt`：生成指示と参照画像。
- `index.json`：原画、参照、公開画像の寸法・SHA-256・処理内容。
- `build.py`：透明部分で区切られたコマの登録、共通キャンバスへの整列、4倍図集の生成。

リポジトリ直下で、Pillowが入ったPython環境から実行します。

```sh
python3 art/loading-cover-v2/build.py
node tests/test_remake_loading_cover.cjs
```

CSSの4段階アニメーションだけで再生し、戦役・乱数・セーブには触れません。移動を減らすOS設定では最初のコマで静止します。旧 `art/loading-cover-v1/`、`game/assets/loading/cover.png` と原版由来の戦闘画像は保持しています。
