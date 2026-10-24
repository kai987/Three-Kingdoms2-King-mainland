# 原作UIの調査・スクリーンショット集

2026年10月24日、ローカルの OpenEmu／Nestopia で起動した「三国志2超级版」の実画面と、現在のWeb版を比較した資料です。

- [画像付きギャラリーと提案](index.html)
- [UI配置・素材差し替え案（繁體中文）](ui-replacement-plan.zh-Hant.md)
- [全キャプチャーの記録](capture-manifest.json)
- [切り抜き範囲と利用候補](asset-candidates.json)
- [確認結果](verification.json)

`screenshots/` は今回取得した全画面のPNG、`reference-crops/` は出典確認用の切り抜きです。原画像は保持しています。切り抜きはゲーム実装用の完成素材ではありません。ウィンドウ画像の倍率・シェーダーの影響があるため、実装時にはネイティブ解像度での再取得と確認が必要です。

調査対象はローカルの「超级版」です。市販版すべてに共通する仕様を証明する資料ではありません。図冊・調査計画・`verification.json`は先行する調査時点の記録です。その時点ではゲームの動作、数値、セーブデータ、公開サイトを変更していません。

その後、承認されたUI変更と素材の導入を実装しました。[現在の実装と素材の制限](../../../docs/original-ui.md)を参照してください。実行時に利用する14組の画像は、次のコマンドで元の裁片を保ったまま再生成・照合できます。

```sh
python3 art/original-ui-study/2026-10-24/export_runtime_assets.py --check
```

ギャラリーの再生成には Pillow が必要です：

```sh
python3 art/original-ui-study/2026-10-24/build_gallery.py
```
