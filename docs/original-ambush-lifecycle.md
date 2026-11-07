# 十面埋伏：帰城・戦後処理・移動境界の原CPU監査

本資料は[原作照合台帳のM2](original-parity-gaps.md)を補う、利用者所有ROMの読み取り専用調査です。**ID11の現行ゲーム実装は変更していません。** 現在の簡略trapを原作と同じ両軍別台帳・100兵支出・期限・発動順へ置き換えたという報告ではありません。

調査開始時のローカルcommitは`94f813e`。原ROM、研究Archive、エミュレーター、利用者の保存状態を変更せず、新しい証拠は本機の`/tmp/tk2-phase10-ambush/`にだけ作成しました。原CPU証拠と、本作の試験・自然戦役の実績は別に数えます。

## 570例の範囲

各例は入力を明示したRAM/SRAMの呼出境界実験です。原ROMの命令・固定bank helperを実行し、最上位の復帰確認にRAMのRTS sentinelだけを使います。helperの戻り値、描画完了、入力確認、NMI完了を偽造していません。

| 証拠群 | 例数 | 実行した範囲・入力域 |
| --- | ---: | --- |
| `cpu-evidence.json`：帰城commit | 32 | 両側×開始兵100/101/700/1000×友好／無所属の帰城先×期限前／5走査後。実B42A支払から、C91E・BC11/F2AFを含むBC2A全体の復帰まで |
| 同：戦果名簿分配 | 12 | BC46の3 mode×両側byte×期限前／後。全て制御した空き枠・所有者を使う。交差した側／modeの入力も含み、12本の自然な勝敗UIではない |
| 同：raw byte11 | 512 | 両施計側×raw byte11の全256値。原森林マスと私有乱数cursor0を使うB933。上位tier・適性code3・状態3なども含む生byte域の試験 |
| `settlement-evidence.json` | 8 | 勝った守方／攻方・敗れた守方／攻方の4役割×期限前／後。BC46、別の正式phase2入力によるBB93、未準備のBBA0、独立したBBB8本体 |
| `movement-evidence.json` | 6 | 両施計側×命中／半径外／trapなし。実1マス移動の描画後suffixから発動と経験処理を通り、次の実描画依存点まで |

**新570例は全て合格**。従来の41例とは別の追加母数で、連続した自然プレイ611例とは数えません。32帰城例の兵wordは全て通常の10bit兵数域で、上位6bitは0です。512例のraw byte11全域や算術carryを、兵wordの上位bit／数値overflow試験と混同しません。

## 原資料の固定と命令位置

ROM全体SHA-256は`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`です。以下は元ROMの範囲pinで、終端はexclusive。Archiveの復元Pythonは原作者のソースではなく、照合用の読みやすい記述です。

| physical bank：CPU範囲 | ROM位置 | SHA-256 |
| --- | --- | --- |
| 12：B42A–B466 | `0x1943A` | `753088ae7f79bcce7618eabac5a60e65d5e5e03bab30c6395bc25bf86b5fe449` |
| 12：BC11–BC93 | `0x19C21` | `f816a8537f2fb0db9e0ea81d5153b48095fc9aa9d0b4fbafea8058175d382fee` |
| 13：C91E–C98C | `0x1A92E` | `a3ae7c1e622a31389c7376b1a8018870e506dc9509c456ced06eef6589b00bea` |
| 8：BC46–BEF4 | `0x11C56` | `f412e040ab9c5a6208fa80df05e5925a77d36918662f78165f360b4f1616436d` |
| 8：B933–BAB3 | `0x11943` | `7396f3e1f2197d90cd144e08ca4b7a7ac1a63540fbb95a638b13b7c631f1a028` |
| 9：CE20–CE40 | `0x12E30` | `81c7c0bb16b4a9c832aef0d934433f72734acafc5d81e25fc55f1eadbf5cc42e` |

入力はArchiveの`analysis/runtime/phase3/attack-intro-7-{ram,sram}.bin`。RAMのSHAは`9fa774acb5028728a51d9164c8cf9c213546a81131037b1d9f0813478813e201`、SRAMは`59cb62b5d2f4411d7cabfdb87b182907d27c12d77f8135b30aa10e67d1382a7b`です。基礎Oracleは`scripts/verify_battle.py`（SHA `307642a98e13f4787794d38659fcfb65f58b58f6859af869637b35019283b625`）。全10ファイルの調査前後pinとrunner SHAは各JSONに保存し、変化はありません。

byte11の既存字段監査`analysis/officer_fields/fields.json`のSHAは`2f00a847eaecc48f086556d364b47334b483accff85aa5c65e1608c4fec020be`。状態2への所属遷移はROM位置`0x032F4F`、平／山／水の抽出・表示は`0x033640/0x03365D`、tier抽出は`0x0335B6`に根拠があります。字段名と解釈の確度は次の通りです。

| byte11の部分 | 確認できる内容 | 残す解釈上の境界 |
| --- | --- | --- |
| bits4..7 | `p >> 4`の経験tier、通常0..7 | 本作の固定能力・既存tier契約を変更する根拠にはしない |
| bits2..3 | `(p >> 2) & 3`、原表示の平／山／水glyphは確認済み | 「地形適性」という行動全体の意味づけは既存監査のstrong inferenceを保持。code3を普通の兵種と呼ばない |
| bits0..1 | `p & 3`、城名簿へ入れて2にする遷移は確認済み | 0/1の名称はstrong inference。3は除去・使用不可を含み、永久死亡とは限らない |

## 完全なbyte11による損害

physical8 B9BA–B9BEは元人物のbyte11全体を0024へ読みます。B9EC/B9ED/B9EEは**ASL**、B9EFのCLCは一度だけで、B9F0/B9F3のADCは最初の加算carryを保持します。

```text
a = (p << 3) & 255
u = a + p
packed_term = (u + p + (1 if u > 255 else 0)) & 255
```

施計者の知80・私有cursor0・対象1000兵では、実際に受理した乱数による基礎損害が248で、合計は`248 + packed_term`。両側の全256値で一致し、私有6F92は0→12、四つのglobal cursorは不変です。raw p2は20／268、p18は180／428、p26は4／252（補正／損害）。p31はcarryにより55となり54ではありません。

p2/p18/p26はそれぞれtier0／平／状態2、tier1／平／状態2、tier1／水／状態2の組合せです。原損害をtierだけで置き換えることはできません。一方、本作の現在tier・実効適性・在籍状態からnative byteを合成する方針は未決であり、生成文吏も含めた対応は将来の明示的な適応です。

## 100兵と戦後書き戻し

開始700兵なら実B42Aが600へ書き換え、その後のBC2Aは実C91EとBC11を呼び、最初の空き城名簿枠へ人物IDを入れ、軍の実slotと対応trap IDを消してBC92から復帰します。人物兵数は600のままです。無所属城では元の高nibbleを保ちつつ所有者も設定します。

旧側集計が700→100となるのは、C91Eが実残兵600を引くためです。その残った100を人物へ返す命令は、この完走した帰城処理にありません。「伏兵の預かり兵100」とは解釈しません。期限前／後、開始100→0・101→1を含む32例で、城に戻った兵数は常に開始−100でした。

戦果分配BC46では、通常役割の勝方は対象城5、敗守方は原隣接城7、敗攻方は出発城6へ戻る入力例を観測しました。別の8例はこれら4役割と期限前／後に限定し、BB93へ入る時点の0501=2を明示した独立call境界です。実ECEEがfadeを要求して87=1にし、資源損失／返却後0501は3になります。BBA0は本当に未準備として復帰し、palette完了を捏造しません。

その後にBBB8の所有者・城首整理**本体を独立実行**しても600兵のままです。これはBBA0が自然にBBB8へ進んだ証明ではありません。以上の実行済み帰城・名簿分配・資源返却・城整理本体に100兵返還はありませんが、全逃走・俘虜・満員overflow・自然UI終局の全分岐までは一般化しません。

## 1マス移動と次の依存点

6例は原森林マスの組を用い、描画後境界BF26で右へ1マス、BF83で入力済み移動費3を実際に10→7へ引き、A51Fがsecondaryを要求し、B933が実効果を処理します。3はこのsuffixへ渡す費用入力であり、地形費用の生産側を再検証した数字ではありません。

命中例は対象に268損害、設伏者に134経験が入り、実helperを通ってA535からportrait依存点A5BBへ到達します。その時点では位置は1マス分、APは7、trapはまだ残っています。半径外／trapなしは損害・経験なしでcursor描画依存点A200へ到達します。どちらも二つ目の座標commitをしていません。

これは「1マス→secondary→次のUI依存点」の実測です。原proposalは一方向を表すので、本作の複数マスrouteの残りを再開する命令とは読み替えません。portrait、本文、確認、任意のlevelpopup、描画復帰、次の実入力は未実行です。将来route各格で判定し最初の発動で停止するなら、実行prefixのAP・演出・占拠順は別に定める必要があります。

## 再現と証拠の所在

本機のArchiveは`/Users/paulasmith/Documents/Codex/Three-Kingdoms2-Research-Archive/2026-10-22-web-cleanup`。既存`.venv-trace/bin/python -B`で次の三つを実行します。これらは本機の一時runnerで、公開パッケージの機能ではありません。

```sh
python -B /tmp/tk2-phase10-ambush/audit.py
python -B /tmp/tk2-phase10-ambush/settlement.py
python -B /tmp/tk2-phase10-ambush/movement.py
```

全ての入力・書込・停止PC・pinは同directoryの`cpu-evidence.json`、`settlement-evidence.json`、`movement-evidence.json`。`summary.json/summary.md`と各`.log`が索引です。初期のLSR仮説の棄却ログと、phase2入力を明確化する前の観測も別名で保持し、最終570へ混ぜていません。ROM、snapshot、約28MBの原CPU出力は本リポジトリへ同梱していません。

## 繁體中文摘要

本輪新增570個受控原CPU例：32歸城、12原mode／側位分配、512 raw byte11、8正常攻守勝敗資源結算、6一步移動邊界；全部通過，10個ROM／Archive／輸入pin前後相同。通常兵數與raw byte全域分開計數，不把異常byte稱為一般可玩人物。

已執行的歸城名冊、資源返還與獨立城首整理中，700扣100後始終600，沒有返100兵；舊集計剩100不是託管兵。傷害確用整個byte11及ASL／ADC carry，不能只映射等級。8例明列獨立phase2輸入，沒有假造87完成；6例僅到原圖文依賴，不證明原多格路線續行。

自然完整UI、原生存讀、全部逃走／俘虜／滿員分支、NMI與確認後續鏈仍未閉合。**ID11現行簡化實作未修改**，不因研究新增便宣稱玩家／AI已接入原版伏兵。後續範圍回到[原作差異台帳](original-parity-gaps.md)管理。
