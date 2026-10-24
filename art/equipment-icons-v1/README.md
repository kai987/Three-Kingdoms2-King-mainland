# 装備アイコンの制作記録

武器29種と防具8種を、ゲームの固定 `slot:itemID` ごとに制作します。各画像は built-in imagegen の独立した生成結果です。原作で確認した共通分類アイコンを残しながら、個別商品の見分けや購入後の更新に使う重制素材を追加しています。原作ROMから取得した個別商品画像ではありません。

`weapon-{id}-source.png` / `armor-{id}-source.png` は生成原図のバイト列をそのまま保存したものです。各JSONには正確なプロンプト、生成元、寸法、処理方法、SHA-256を記録します。原図を上書きしません。

- [武器29種のプロンプト](weapon-prompts.json)
- [防具8種のプロンプト](prompts/armor.json)

配信用PNGは [game/assets/equipment-icons](../../game/assets/equipment-icons/) にあります。nearest-neighborで128×128に縮小し、黒 `#000000`、橙 `#f89800`、桃 `#f8c0a8`、白 `#ffffff`、灰 `#b0b0b0`、赤 `#c02020` の最近傍RGBに揃えます。アルファは128以上を255、それ以外を0とし、透明部分のRGBは0にします。ゲーム内は28〜40px枠で表示します。

manifestは全37点のカタログID、名称、配信用パス、原図と配信用PNGのSHA-256を検査して作成します。

```sh
python3 tools/equipment-icons/build_manifest.py
python3 tools/equipment-icons/build_manifest.py --check
python3 -B -m unittest discover -s tests -p test_remake_equipment_icons.py
```

配信対象は128×128 PNGとmanifestのみです。生成原図・制作プロンプトは公開ゲームの配信対象に含めません。
