# 武将追加後の行軍互換性確認（2026-10-27）

1052名の確定カタログで、行軍の数式・経路・損耗計算とPython／Rust間の厳密なセーブ互換性を確認した。`source/`、`crates/march-core/`、行軍コア／セーブ互換テスト本体は基準コミットから変更していない。

- 基準：`f65d3abae2c2c50293c5cf08d07f49413d60cbf6`。そのsourceと217年カタログを隔離し、既存の`campaign_result`をPythonで8件再生。旧fixtureと全項目が完全一致した。
- 確定217-07 JSON SHA256：`066f2dfb4abbd415c0baa3a5c6a2ea2f5a60508a24a72ce3431ed1e20b7673d4`。
- 旧fixture SHA256：`86b3cf3344e6d183149062269557f6ce0116f93a27bc5b468e8264a6b13e6246`。
- 新fixture SHA256：`dc3a7ba7e399c276ae6bce0eadc7b8464a5535fdd567968fbd625746efc48715`。
- 互換性の範囲は、同じ確定カタログを使用するPython／Rust間の相互読込。カタログSHA・セーブchecksum照合を厳密に維持する。

## 8件の固定行軍

`before`・`preview`・`queued`・`arrived`のstate/saveハッシュ64箇所だけを更新した。quote全体（経路・区間・日数・季風・損耗率・兵糧見積り）、主RNG、総兵数、turn、到着時の各武将兵数は旧fixtureと完全一致する。ハッシュ項目を削除したり、比較時に正規化する処理は追加していない。

| ケース | 日数 | 到着時の主RNG draws | 新到着state SHA256 | 新到着save SHA256 |
|---|---:|---:|---|---|
| plain | 14 | 0 | `a26fbf04c1090af17cb3b67567d807da2b8423b928af2675e6ffe23e3420430b` | `ece13224aceae8ac2f4bcec66f233279fe69b0668a74e32e26b86bfd7da210e1` |
| yinping | 32 | 0 | `5c51688ad7bfd569758351602b2fc49cc8350d7fd2b85ac2e9089292ddaa881f` | `606d2806eca1f4a9cbbac0e07333c95af61fd31754ab7898ecc930fc2dcc2561` |
| ziwu-rain | 48 | 0 | `c9ae7cd95e86b7648fb0c2a6f8fb50a15aed4963b6f166ac37a334759c214957` | `1431b7da9ddd9fef3e7848b02a4aed18bd0e269e48c66c564784e9c793dc2c32` |
| ziwu-dry | 24 | 0 | `2f8902a783aca610dce6281b0467775e25250777bd418205acbfcdedddcc2ade` | `9559da1c6fe0f458fe133d3cd531d9ecfba874b23f813c60ea05fc07fda995be` |
| sea-tail | 8 | 1 | `66574a148bb8f70cfc325e09e59b2ac25ba34bfa7c862094b03d15024df59893` | `c3a00063e8967889da65289ae1275ee164e22ddc9440296f1321e57196c70def` |
| sea-head | 32 | 1 | `2ba9fd8ea910ce02b57b0cd331095b69b9815aef20e2f0f1b59ff3d0a9d11b29` | `b5f83a22c03bc4b4463e31c685dc27addfec9ceb8aac74bd04de8d56fa7eeb2d` |
| sea-calm | 9 | 0 | `4bc0e8559c03444aec80e7e7f5c37c9acf173deb74300c7bb6a86fb77c407fe5` | `9759d752a4f9c9a2ec3308d1b2e9e05675ef295073cd1e6663ed7cdde56faf48` |
| explore | 18 | 1 | `d0497c7f9ab6d250dbe0e1c02eebb2823d348288bf3984318a22697575b0c92d` | `1bab649e2b3e410da60b98404c6fbfd183081a03ef1c5cdefa6fb2e6d908b79a` |

完全な4検査点の値と経路は[固定fixture](../tests/fixtures/march-python-baseline.json)に保存する。速度・地形・季風・河川・損耗・路線データは基準と同じで、`travel_rules`の差は再生成した出典を示す`geometry_sha256`だけである。

## state/saveハッシュが変わる理由

217年の実在局では、旧418人から424人へ増える。在籍369人・在野55人で、追加または復帰する人物は程銀、孫康、徐翕、毛暉、陽儀、錢博。補員分を都市の予備兵から移し、既存の成公英・楊秋の駐城修正も反映する。固定行軍の旧来存在する各武将のruntime属性は、4検査点すべてで同一だった。

差分は、都市の名簿／予備兵、追加人物、在野所在地、装備初期化済みID、担当官の再選出、文吏候補とその関連イベントに限る。saveには新カタログSHAと変更後のstateが含まれる。都市のお金・兵糧や行軍ルールを変えてハッシュを合わせてはいない。

文吏の独立RNGは、補員によって人材不足と判定される都市が変わるため、次の3件では自然に変わる。このRNGもstateとsaveに含めたまま検証する。

| ケース | 検査点 | 文吏RNG draws（旧→新） |
|---|---|---:|
| ziwu-dry | queued | 2→1 |
| ziwu-dry | arrived | 3→1 |
| sea-tail | queued | 3→1 |
| sea-tail | arrived | 3→1 |
| sea-calm | queued | 3→1 |
| sea-calm | arrived | 3→1 |

## 自然AIと旧人物の保全

同じ入力の9コマンドで217年8月上旬まで自然進行させると、名簿・採用対象・前線配置に応じてAIの行動と主RNG消費が変わる。旧AI結果を強制せず、新配置同士のPython／Rustを各コマンド後に比較した。

| コマンド | 主RNG draws（旧→新） |
|---|---:|
| 1: new | 0→0 |
| 2: end_turn | 0→0 |
| 3: ai | 20→16 |
| 4: end_turn | 20→16 |
| 5: ai | 41→39 |
| 6: arrivals | 169→141 |
| 7: end_turn | 169→141 |
| 8: ai | 298→267 |
| 9: arrivals | 349→327 |

29劇本をf65の実データと逐人比較し、未記載の帰属変更は0件。旧1030人のcanonicalオブジェクトと順序、全初期装備、都市所有者、君主ID、お金・兵糧・総兵数（帯同兵＋予備兵）は維持した。編纂済み人物の年表変更は、記録された曲演・成公英・程銀・梁興の卒年と説明だけである。前後とも在籍する旧将の相対順序も29/29で一致する。

[retainer参照](../game/config/references/retainer-affiliation-review.json)のbefore/afterに一致する変更だけを旧名簿の検証用に戻し、f65の旧hashをそのまま残す。同時に、現在の1052人全体の属性・名簿hashも固定する。行軍parityの入力・state・saveは一切戻さない。旧1030人の初期装備hashは`9a8b24cfca5812d2e0ccc038626a8aec8ca7d7672a6b7927d9dfc9ce8f906601`。

## 実行結果

```sh
MARCH_CORE_BACKEND=rust python3 -B tests/test_remake_march_save_compat.py -v
python3 -B tests/test_remake_han_sui_if.py -v
node tests/test_remake_library_status.cjs
node tests/test_remake_portraits.cjs
```

- 行軍互換：3/3。8件のPython／Rust相互セーブ読込と自然AI3旬について、各コマンドのstate・save・revision・journal・RNGが完全一致。
- 韓遂／IF：8/8。旧hashを保持し、現行hash、物資保存、旧人物・初期装備の保全を確認。
- Library／Portraitの両CJS：成功。1052人、未来候補の未登場分類、王建の体力42と所属文脈を限定する忠誠初期化、原版221／生成831の画像IDを確認。
