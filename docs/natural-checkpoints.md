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

1. 逐将配置の途中、持続計略状態、兵士戦のformation/orders/combat、単挑の旧6分類と、下記の固定11細分類を読み取り、それぞれ最初の一件を保存します。最初の将を確定しても配置がすべて終わった場合は「途中」と数えません。
2. 次の実命令の直前にも、現在の保存が捕獲した保存と完全一致することを確認します。観測器を迂回した状態変更を許しません。
3. 通常の主軌跡がその命令を確定した後、捕獲JSONをfreshなPython/Rust Campaignに読み込み、同じ公開命令・payloadを各cloneの正しいrevisionで実行します。完全な保存、状態checksum、RNGを主軌跡の結果と比較します。
4. probeが主gameや元catalogを変えないこと、backend contextが元へ戻ることを確認します。cloneの命令をプレイヤーの実命令数へ加算しません。
5. 観測器offの同一方針baselineも独立に実行し、主命令集計、全命令の状態hash列、最終保存を比較します。probeの有無による実戦方針の差を見逃しません。

これは保存される状態と次命令の検証です。瞬間的な描画・アニメーションの同一性、原機の途中保存操作を検証したものではありません。

## v2の分類別保存と証拠数

v1は最初の`siege_formation/orders/combat`を保存すると、その後の同じ段階を保存しませんでした。この名前は野戦も含むため、最初が野戦なら、後に城砦戦へ入っても城砦の見証は残りません。同様に最初の`active_conditions`が虚兵なら、後の連環・奇門は数だけ増え、別の保存・次命令の証拠にはなりません。これは観測器の分類不足であり、城砦戦や計略が実際には発生しないという証明ではありません。

`tk2-natural-checkpoints-v2`は旧6分類の`observation_counts/checkpoints/unobserved/coverage_status`の意味を保ち、`strata`に独立した初回保存を追加します。既存v1の証拠ファイルは変更しません。v1に細分類がないことを、新しい未観測値や検証済み値へ勝手に変換しません。ゲームの保存形式は変更しません。

| 細分類 | 固定数 | 根拠 |
| --- | ---: | --- |
| `partial_placement`、`duel` | 2 | 従来どおりの公開状態 |
| `condition_phantom/chain/qimen` | 3 | 正のremainingを持つ実際の状態台帳。兵数0でも残る奇門を除外しない |
| `field_formation/orders/combat` | 3 | 実際の兵士戦receiptのmode=`field` |
| `fort_formation/orders/combat` | 3 | receiptのmode=`siege`。城の戦略地形や守備側という理由で推定しない |

分母は常に11で、交戦だけは6、持続計略だけは3です。出現したものだけを分母にしません。各分類の`observation_counts`は受理された命令後の状態ごとに1回で、連環の対象人数を掛けません。旧mode省略保存は実ゲームと同じ`siege`既定値を使い、`encounter_mode_source=legacy_default`を付けます。mode・fortの人物ID・map_id・cellは実際のreceiptから記録します。

同じ命令で旧分類と複数の細分類が初出になった場合、保存ファイルとPython/Rustの次命令probe各1回を共有します。`labels`はその保存で**新たに取得した分類名**であり、すべての活動中状態を列挙したものではありません。`condition_kinds`は保存時に活動中の計略種です。複数の行が同じ`file`を指しても、物理保存やprobeを水増ししません。実数は`physical_saves.captured/verified/verified_backend_commands`を使います。

`strata.coverage`と最上位の`detailed_coverage`は観測数と次命令検証済み数を分けます。旧分類が既に検証済みでも、新しい細分類が最後に現れて次命令がなければ`incomplete`です。最上位は実際に実行したobserver legの和集合であり、各主backendが独立に全分類を通ったという意味ではありません。その判断には各legの表と`verification_status/parity`も必要です。native呼出数だけは会計情報として両方の証拠配列で正規化し、全保存・状態・RNG・命令列の比較を維持します。

## 予算と判定

既定の`--max-seconds 300`と`--max-commands 2000`は**各独立replay legごと**です。既定の両backendではobserver/baselineがそれぞれ実行され、合計4 legになります。clone検証の時間は所属observer legの時間へ含めますが、clone命令数は主方針の命令予算と分けます。時間は公開命令の前とleg終了時に確認し、実行中の一つのtransactionを強制中断する硬いtimeoutではありません。

| 値 | 意味 |
| --- | --- |
| `verification_status=passed` | 指定した実行と保存・続行・baseline・源指紋の検査に合格 |
| `coverage_status=partial/unobserved` | 6分類の一部または全部が自然には未出現。0を成功へ置き換えない |
| `detailed_coverage.observed_status/verified_status` | 固定11分類の出現／次命令検証を別々に表示。交戦6、持続計略3の小計も保持 |
| `incomplete` | 命令／時間／実行予算に到達、または保存の次命令が未実行。CLIは非0終了 |
| `failed` | 状態、続行、方針、source指紋等の不一致。CLIは非0終了 |
| `campaign_outcome=unresolved` | 指定旬数まで進めたが戦役は進行中。統一や滅亡を意味しない |
| `parity=single_backend_only` | 主軌跡を片backendだけ指定した実行。二つの主戦役の一致とは呼ばない |

旬数の上限で通常終了した戦役は、検証に合格しても`unresolved`のままです。予算不足で止まった検証とは分けます。保存後の続行が未実施の項目も`pending_without_continuation`として残し、合格へ数えません。

## 先行v1の実測（固定した過去の結果）

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

公開前に完全CIが必要な場合、候補分岐の`workflow_dispatch`で`force_full=true`を要求できます。通常の工具単独範囲は変更せず、実際にアップロードされたplanのfull・全10群・全Python群・native/rules/soak/resupply・publish=falseと最終headを確認します。累積PR差分が既にfullを要求する場合は同時に重複実行を作りません。

## v2作業ツリーの実測（dc63を親とする検証器のみの変更）

旧分類の取りこぼしは、同じ実戦内で野戦から城砦へ進む受控回帰と、虚兵の後に連環・奇門を実際に支払って使う受控回帰で再現・修正しました。これは検証器の試験であり、自然な出現率や原機の戦果の証拠にはしません。

| 実行の性質 | 固定した条件 | 実測と境界 |
| --- | --- | --- |
| 既存Replayを変更しない自然観測 | 217年7月・曹操・seed2026・3旬、各leg最大600命令／120秒 | 虚兵とfield三段階の4/11分類を各主backendで観測・次命令検証。各主軌跡34命令、計8物理保存・16 clone命令。observer-off基線および主backend間の全保存・状態・RNG・命令列が一致。合計38.008秒、city段階、戦役未決 |
| 明示した合法操作方針 `directed-public-hold-camp-v1` | 公開newから184年2月・漢・seed2026。city/admin/敵AIは既存Replay、守将のみ合法な城砦配置で待機 | 董卓の安定→京兆の実到着後、original-08の城格class5 `(15,11)` へ敵735が守将665と接触。fort三段階を各主backendで保存・次命令検証。各軌跡24公開命令、計6物理保存instance・3種類の保存状態・12 clone命令。両主backendと同一定向方針のobserver-off基線4軌跡が完全一致。合計13.086秒、戦闘中で終了 |

定向経路はfixtureへの状態代入ではありませんが、既存Replayの戦術方針を変更しない「自然観測」とも呼びません。公開配置・待機・布陣・兵士命令だけで到達し、原AIを変えずに城砦戦へ入れることと、その保存の次命令を確認した範囲です。三つのfort分類だけを取り、戦闘勝利や天下統一は主張しません。両実行ともゲーム・catalogの源指紋は不変で、人物・物資・乱数の書換えはありません。

本機の新証拠は`/tmp/tk2-phase11-natural-217/report.json`と`/tmp/tk2-phase11-directed-fort/summary.{json,md}`、公開命令列・実保存を含む各ディレクトリです。旧v1証拠と別に保存します。固定分類と共有probeの回帰20項、範囲選別53項、関連回帰41項がローカル合格し、観測器＋関連の61項は明示Rust環境でも再実行・合格しました。これらも別母数で扱い、古い完全CIの合格を新HEADへ流用しません。

## 残る範囲

先行209年観測で持続計略は0でした。新しい217年の自然観測は虚兵、184年の定向公開経路は城砦の保存・次命令を確認しましたが、既存Replayを変えない自然な連環・奇門・城砦の途中保存は未観測です。v2の分類修正だけでは新しい自然状態が発生したことにはなりません。統一終局、追加年代／seed、同じ保存から数命令以上の分岐した続行も、この短期観測からは証明できません。[原作照合の台帳](original-parity-gaps.md)のV2/V3を別々に継続します。伏兵と接敵の新調査は[伏兵の原CPU境界](original-ambush-lifecycle.md)、[接敵推定の比較範囲](ai-contact-calibration.md)に記録し、今回のゲーム規則は変更していません。

## 繁體中文摘要

新增自然戰局觀測工具，只使用既有策略與公開命令。在首次出現的中間狀態存檔後，讓Python／Rust clone各執行主軌跡真正採取的下一命令，比對完整存檔、狀態和亂數；另跑關閉觀測器的基線，核對策略及命令序列未變。未出現記0，未完成續行或超出驗證預算記incomplete，戰役仍在進行則記unresolved。

v2保留舊6類統計，另設固定11類：途中布陣與單挑2類、虛兵／連環／奇門3類、野戰／城砦各3階段。先出現野戰或虛兵不再擋住後續城砦、連環或奇門的首次存檔。依實際receipt的mode、fort人物、map_id與cell記錄，不按城市地形或防守方猜測；缺mode的舊格式按遊戲既有siege預設處理並標示來源。

「已觀察」和「下一實際命令已驗證」分開計數，分母固定11（交戰6、狀態3），不按受計人數或只出現的類別縮分母。同一狀態的多個新標籤共用一份存檔和各後端一次probe，物理份數與邏輯分類數分開。最上層細分類是已執行leg的聯集，不能冒稱各主後端都完整覆蓋；末尾有任何新分類未續行，仍判incomplete。v1舊證據保留，不把缺少細分類解讀為新覆蓋；原遊戲規則及遊戲存檔格式均未改。

先行209年6月曹操觀測覆蓋途中布陣、field三階段及單挑，持續計略當時為0。新v2在217年7月曹操、seed2026、各3旬自然捕捉虛兵及field三階段4/11類：8份物理存檔、16次續行。另從公開new起始的184年漢勢力合法留守城砦路徑，真實接敵後捕捉fort三階段：6個物理存檔instance、3種狀態、12次續行；各主軌跡24公開命令。兩項分別核對同策略observer-off基線與兩主後端完整存檔、RNG、命令列，皆一致；分別耗時38.008秒、13.086秒。後者明確標為定向合法操作，不冒稱既有Replay的自然策略或fixture；自然連環／奇門／城砦及完整統一仍未覆蓋。預算按各leg計算，遊戲規則、AI、素材與正式長跑方案保留。
