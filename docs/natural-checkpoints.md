# 自然な戦局の途中保存と続行検証

既存の`campaign-soak Replay`が実際に到達した保存可能な状態を観測し、その**次に実行した公開命令**をPython/Rustの独立した読込先でも実行します。ゲームの規則、AI方針、配置、人物、物資、乱数を変更する機能ではありません。月次・継承時の保存だけでは確認できなかった途中状態を、別の検証単位として扱います。

## 実行方法

通常の開発環境とビルド済みのnative march coreが必要です。明示したRust実行にPythonへの自動フォールバックはありません。単一の主backendを指定しても、捕獲した保存の続行probeは常に両backendで実行するため、native coreは必要です。

```sh
python3 -B tools/campaign-checkpoints/run.py \
  --scenario 209-06 --faction wei --seed 2026 --turns 3 \
  --backends python rust \
  --output-dir /tmp/tk2-checkpoints-209-2026
```

出力先は本リポジトリ外の新規または空のディレクトリを明示します。symlink解決後にリポジトリ内を指す場所、空でない既存の証拠ディレクトリは拒否します。再実行には別の空ディレクトリを指定してください。劇本は正規・生成indexの両方に一致するID、勢力は当該catalogの実在IDに限ります。

`report.json`、各backendの最終保存、初回観測時の`*.save.json`を出力します。受理された公開命令後だけを観測し、AI処理の内部で一時的に現れて消える状態は数えません。

## 保存と次命令の契約

1. 逐将配置の途中、持続計略状態、兵士戦のformation/orders/combat、単挑の各分類を読み取り、最初の一件だけをJSON保存します。最初の将を確定しても配置がすべて終わった場合は「途中」と数えません。
2. 次の実命令の直前にも、現在の保存が捕獲した保存と完全一致することを確認します。観測器を迂回した状態変更を許しません。
3. 通常の主軌跡がその命令を確定した後、捕獲JSONをfreshなPython/Rust Campaignに読み込み、同じ公開命令・payloadを各cloneの正しいrevisionで実行します。完全な保存、状態checksum、RNGを主軌跡の結果と比較します。
4. probeが主gameや元catalogを変えないこと、backend contextが元へ戻ることを確認します。cloneの命令をプレイヤーの実命令数へ加算しません。
5. 観測器offの同一方針baselineも独立に実行し、主命令集計、全命令の状態hash列、最終保存を比較します。probeの有無による実戦方針の差を見逃しません。

これは保存される状態と次命令の検証です。瞬間的な描画・アニメーションの同一性、原機の途中保存操作を検証したものではありません。

## 予算と判定

既定の`--max-seconds 300`と`--max-commands 2000`は**各独立replay legごと**です。既定の両backendではobserver/baselineがそれぞれ実行され、合計4 legになります。clone検証の時間は所属observer legの時間へ含めますが、clone命令数は主方針の命令予算と分けます。時間は公開命令の前とleg終了時に確認し、実行中の一つのtransactionを強制中断する硬いtimeoutではありません。

| 値 | 意味 |
| --- | --- |
| `verification_status=passed` | 指定した実行と保存・続行・baseline・源指紋の検査に合格 |
| `coverage_status=partial/unobserved` | 6分類の一部または全部が自然には未出現。0を成功へ置き換えない |
| `incomplete` | 命令／時間／実行予算に到達、または保存の次命令が未実行。CLIは非0終了 |
| `failed` | 状態、続行、方針、source指紋等の不一致。CLIは非0終了 |
| `campaign_outcome=unresolved` | 指定旬数まで進めたが戦役は進行中。統一や滅亡を意味しない |
| `parity=single_backend_only` | 主軌跡を片backendだけ指定した実行。二つの主戦役の一致とは呼ばない |

旬数の上限で通常終了した戦役は、検証に合格しても`unresolved`のままです。予算不足で止まった検証とは分けます。保存後の続行が未実施の項目も`pending_without_continuation`として残し、合格へ数えません。

## 今回の実測

基準はローカル`94f813e`のゲーム規則です。209年6月、曹操、seed2026、各backend3旬を進め、209年7月1日のcity段階で終了しました。各主軌跡はそれぞれのobserver-off baselineと完全一致し、Python/Rust間でも全状態・保存・RNG・命令hash列が一致しました。

| 自然に観測した分類 | 各主軌跡の観測回数 | 最初の保存に続く実命令 |
| --- | ---: | --- |
| 逐将配置の途中 | 11 | `battle_place`。初回は1/3人確定 |
| 兵士戦formation | 10 | `siege_form` |
| 兵士戦orders | 55 | `siege_orders` |
| 兵士戦combat | 62 | `siege_step` |
| 単挑 | 7 | `duel_action` |
| 持続計略状態 | **0** | 未観測、続行未検証 |

保存した初回証拠は5分類×2主backendの10件、続行probeは各2backendで計20件です。今回の兵士戦はfieldモードで、城壁戦の自然checkpointを新たに実測した意味ではありません。主軌跡には13回の逐将確定、10回の陣形決定、55回ずつの兵士命令／巡行、7回ずつの単挑／計略等があり、観測器はそれを変更していません。Python主軌跡のnative呼出は0、Rust主軌跡は31,439回で、実行backendを区別しています。

本機の実測は`/tmp/tk2-phase10-validation-audit/natural-209-06-2026/report.json`と同ディレクトリの実保存、単位試験と独立reviewは`/tmp/tk2-phase10-natural-unit.log`、`/tmp/tk2-phase10-contact-audit/observer-review/`に記録しています。小さいcontrolled-catalog試験は検証器の故障検出用であり、上表の自然観測には加算しません。

関連回帰は、新しい14項をPython/Rustの各環境で計28実行、既存soak／balance／保存互換37項ずつ、CI helper22項、CI範囲52項の計176実行が合格しました。初回のCI計画試験では、既存のnative互換fixtureが217年IDを選ぶ契約を見落とした期待値を修正し、52項を完全再実行しています。元の不合格ログを残し、既存の互換性検査を省く例外は追加していません。

ゲーム・画像・既存方針・workflowの2,968ファイルは開始時の94f813eと内容が同じです。Browser scope／起動境界のCJSも確認し、画面の新実行数は0と区別します。再生成Web全体の比較ではbuild commit metadataだけを正規化し、以前のdesktop/touch受入済み内容と同じことを確認します。以前の2,882項や10画面を、本輪で再実行した項数へ加算しません。最終のcommit・構築比較と関連試験の記録は本機`/tmp/tk2-phase10-proof.json`に保存します。

CIはこの観測器単独の変更ではnative参照、互換性・関連helper検査と既存217年fixtureを維持し、全件長期soakや公開は選びません。CI選別器自体を変える場合は従来どおり保守的なfull分類です。このツールの実行が既存の正式soak期間やseedを置き換えることはありません。

## 残る範囲

持続計略が自然に残った時点と城壁戦のcheckpoint、追加年代／seed、同じ保存から数命令以上の分岐した続行は未完です。原版30城の終了画面や本作の全活動都市を統一する自然な全戦役も、この3旬からは証明できません。[原作照合の台帳](original-parity-gaps.md)のV2/V3を別々に継続します。伏兵と接敵の新調査は[伏兵の原CPU境界](original-ambush-lifecycle.md)、[接敵推定の比較範囲](ai-contact-calibration.md)に記録し、今回のゲーム規則は変更していません。

## 繁體中文摘要

新增自然戰局觀測工具，只使用既有策略與公開命令。在首次出現的中間狀態存檔後，讓Python／Rust clone各執行主軌跡真正採取的下一命令，比對完整存檔、狀態和亂數；另跑關閉觀測器的基線，核對策略及命令序列未變。未出現記0，未完成續行或超出驗證預算記incomplete，戰役仍在進行則記unresolved。

209年6月曹操、seed2026、兩後端各3旬，實際覆蓋途中布陣、field兵士戰三階段及單挑：10份自然存檔、20次跨後端續行全部一致。持續計略狀態沒有自然出現，城壁戰及完整天下終局也仍未完成。預算是每個observer／baseline leg各自計算，不是整個CLI共用300秒硬上限。遊戲規則、AI方針、原素材與正式長跑方案均保留。
